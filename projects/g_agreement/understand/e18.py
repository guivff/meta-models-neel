"""§109 frozen-input preparation and token-level continue-then-ask assembly."""
import argparse
from pathlib import Path
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify
from .followup_packed import jsonl

STRUCTURE = ('prose_paren', 'prose_quote', 'python_string', 'python_indent',
             'python_depth', 'list_depth', 'table_role')
CONTENT = ('prose_sentiment', 'latex_subject', 'table_status')
FEATURES = STRUCTURE + CONTENT
ARMS = ('a', 'b', 'c', 'd')
SEED = 20261025
BATCH = 16
PREFIX = '- '
SEPARATOR = '\n'


def pair_donors(items, seed=SEED):
    """One independent uniform draw with replacement per item; frozen ID order."""
    ordered = sorted(items, key=lambda r: (r['feature'], r['id']))
    if len({r['id'] for r in ordered}) != len(ordered):
        raise ValueError('unique donor-pool IDs required')
    if len({r['split'] for r in ordered}) != 1:
        raise ValueError('donor pools cannot cross splits')
    rng = np.random.default_rng(seed)
    donors = {}
    for row in ordered:
        pool = [r['id'] for r in ordered
                if r['feature'] == row['feature'] and r['value'] != row['value']]
        values = {r['value'] for r in ordered if r['feature'] == row['feature']}
        if len(values) != 2 or not pool:
            raise ValueError('exactly two truth values per donor row required')
        donors[row['id']] = pool[int(rng.integers(len(pool)))]
    return donors


def continuation_tokens(generated, eos_ids, pad_id):
    """Keep the emitted EOS in the causal context; discard only padding after it."""
    seq = [int(t) for t in generated]
    for j, token in enumerate(seq):
        if token in eos_ids:
            if any(t != pad_id for t in seq[j + 1:]):
                raise ValueError('non-padding token after generated EOS')
            return seq[:j + 1]
    return seq


def lens_head(reader, continuation=None):
    native, slot = reader.carrier(44)
    if continuation is None:
        return list(native), slot
    tok = reader.tok
    head = (list(native) + tok.encode(PREFIX, add_special_tokens=False)
            + list(continuation) + tok.encode(SEPARATOR, add_special_tokens=False))
    return head, slot


def base_head(tok, raw):
    """Only the lens continuation is given to base Qwen; no source-text wrapper."""
    result = tok.apply_chat_template([{'role': 'user', 'content': PREFIX + raw}],
                                    tokenize=True, add_generation_prompt=True,
                                    enable_thinking=False)
    return list(result['input_ids'] if hasattr(result, 'keys') else result)


def prepare(out, source, tokenizer):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(tokenizer, local_files_only=True)
    bank, target = source / 'w1-bank-v2', source / 'w1-assembled/target'
    verify(bank, 'INPUT_SEAL.json'); verify(target)
    private = bank / 'items.DO_NOT_STAGE.jsonl'
    if sha(private) != read(bank / 'manifest.json')['files'][private.name]:
        raise ValueError('W1 private item hash mismatch')
    all_items = rows(private)
    templates = read(bank / 'templates.json')
    order = read(target / 'items.order.json')
    if len(order) != len(set(order)) or set(order) != {r['id'] for r in all_items}:
        raise ValueError('captured W1 item order mismatch')
    source_index = {k: i for i, k in enumerate(order)}
    capture = read(target / 'provenance.target.json')
    if capture['input_seal_sha256'] != sha(bank / 'INPUT_SEAL.json'):
        raise ValueError('capture belongs to another input bank')
    test = [r for f in FEATURES for r in all_items if r['feature'] == f and r['split'] == 'test']
    for f in FEATURES:
        rr = [r for r in test if r['feature'] == f]
        if len(rr) != 84 or sorted(sum(r['value'] == v for r in rr) for v in templates[f]['values']) != [42, 42]:
            raise ValueError('each registered row needs all84 test items,42 per value')
        if len(templates[f]['olens']) != 2:
            raise ValueError('two original W1 Oracle phrasing pairs required')
    # Time the row with the longest frozen candidate workload; no scores or
    # labels influence wording. This guards against short-question forecasts.
    costs = {f: sum(max(len(tok.encode(c, add_special_tokens=False)) for c in pair)
                    for pair in templates[f]['olens']) for f in FEATURES}
    f = max(FEATURES, key=lambda feature: costs[feature])
    dev_pools = [[r for r in all_items if r['feature'] == f and r['split'] == 'dev' and r['value'] == v]
                 for v in templates[f]['values']]
    if any(len(p) < 24 for p in dev_pools):
        raise ValueError('development timing fixture unavailable')
    dev = [r for start in (0, 8, 16) for p in dev_pools for r in p[start:start + 8]]
    if {r['cluster'] for r in dev} & {r['cluster'] for r in test if r['feature'] == f}:
        raise ValueError('dev/test template leakage')
    out.mkdir(parents=True, exist_ok=False)
    public = lambda r: {k: r[k] for k in ('id', 'feature', 'split')}
    jsonl(out / 'items.input.jsonl', [public(r) for r in test])
    jsonl(out / 'dev.input.jsonl', [public(r) for r in dev])
    dump(out / 'ids.json', [r['id'] for r in test])
    dump(out / 'templates.json', {f: templates[f] for f in FEATURES})
    dump(out / 'donors.json', pair_donors(test))
    dump(out / 'dev.donors.json', pair_donors(dev))
    dump(out / 'warm.donors.json', pair_donors(dev[:BATCH]))
    units = [{'feature': f, 'indices': list(range(j, min(j + BATCH, (i + 1) * 84)))}
             for i, f in enumerate(FEATURES) for j in range(i * 84, (i + 1) * 84, BATCH)]
    dump(out / 'units.json', units)
    acts = np.load(target / 'acts44.npy', mmap_mode='r', allow_pickle=False)
    for name, data in [('acts44.npy', test), ('dev_acts44.npy', dev)]:
        x = np.asarray(acts[[source_index[r['id']] for r in data]], dtype=np.float32)
        if x.shape != (len(data), 5120) or not np.isfinite(x).all():
            raise ValueError('invalid captured block44 array')
        np.save(out / name, x, allow_pickle=False)
    provenance = {'authority_commit': '409690ee', 'bank_seal_sha256': sha(bank / 'INPUT_SEAL.json'),
                  'target_seal_sha256': sha(target / 'SCORE_SEAL.json'),
                  'target_acts44_sha256': sha(target / 'acts44.npy'),
                  'target_order_sha256': sha(target / 'items.order.json'),
                  'private_items_sha256': sha(private), 'test_labels_staged': False,
                  'source_texts_staged': False, 'new_capture': False,
                  'donors': 'independent uniform opposite-value same-row test draws with replacement; canonical feature/id ordering; numpy default_rng(20261025)',
                  'dev_fixture': '48 dev items, three units of8A+8B; longest sum of two frozen maximum candidate token lengths; ties registered row order; timing/smoke only; no wording selection',
                  'dev_feature': f, 'candidate_token_workload': costs,
                  'tokenizer_json_sha256': sha(tokenizer / 'tokenizer.json'),
                  'candidate_pairs': 'two original W1 Oracle pairs verbatim; mean paired summed log-odds',
                  'generation': {'prefix': PREFIX, 'max_new_tokens': 16, 'do_sample': False,
                                 'num_beams': 1, 'batch_items': BATCH},
                  'same_context': 'native carrier + prefix token IDs + emitted continuation IDs including EOS + newline + exact W1 candidate IDs',
                  'base_context': 'user turn with prefix + raw continuation only, default no-thinking assistant header; exact same W1 candidate IDs; adapter disabled'}
    dump(out / 'provenance.json', provenance)
    dump(out / 'INPUT_SEAL.json', {'status': 'E18_INPUTS_FROZEN_BEFORE_GENERATION',
                                 'files': {p.name: sha(p) for p in out.iterdir() if p.is_file()}})
    return {'items': len(test), 'dev_smoke_items': len(dev), 'units_per_path': len(units),
            'input_seal_sha256': sha(out / 'INPUT_SEAL.json'), 'private_labels_local': str(private),
            'test_labels_staged': False, 'new_capture': False, 'GPU_hours': 0}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--tokenizer', type=Path, required=True)
    a = p.parse_args(); print(prepare(a.out, a.source, a.tokenizer))
