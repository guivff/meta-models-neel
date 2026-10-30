"""E37 CPU-only preparation from immutable W1/E15/E30 sources; no model loads."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
C2_ROWS = ('prose_paren', 'prose_quote', 'python_string', 'python_indent',
           'python_depth', 'list_depth', 'table_role')
PARITY_ROWS = ('prose_sentiment', 'prose_paren', 'python_string')
SOURCE_NAMES = {'candidates': 'results/g_agreement/understand/e30/CANDIDATES.json',
                'pairs': 'results/g_agreement/understand/e15/CONTINUATION_PAIRS.json',
                'metrics': 'results/g_agreement/understand/e15/analysis_7whn3a1dvi399p/metrics.json'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def check_sources(directories, references):
    for group, files in references['files'].items():
        directory = Path(directories[group]).resolve()
        for relative, digest in files.items():
            path = (directory / relative).resolve()
            if not path.is_relative_to(directory) or sha(path) != digest:
                raise ValueError('frozen source mismatch: ' + group + '/' + relative)


def smoke_ids(items):
    return [r['id'] for r in sorted(items, key=lambda r: (
        hashlib.sha256(('20261025|' + r['id']).encode()).hexdigest(), r['id']))[:20]]


def auc(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, bool)
    if not np.isfinite(scores).all() or not labels.any() or labels.all():
        raise ValueError('finite scores and both classes required')
    delta = scores[labels, None] - scores[~labels][None, :]
    return float(np.mean((delta > 0) + .5 * (delta == 0)))


def select_templates(w1, candidates, pairs, metrics, rows):
    valid = {r['feature']: r['valid_pairs'] for r in metrics['rows'] if r['valid_pairs']}
    if set(valid) != set(C2_ROWS) or any(v != [0, 1] for v in valid.values()):
        raise ValueError('frozen E15 seven-row/two-pair validity mask changed')
    if pairs['oracle_prefix'] != '- ':
        raise ValueError('E15 native continuation prefix changed')
    for feature in rows:
        if w1[feature]['values'] != candidates['values'][feature]:
            raise ValueError('C1prime value orientation differs from frozen W1')
    result = {'C1': {f: w1[f]['olens'] for f in rows},
              'C1prime': {f: candidates['candidates'][f] for f in rows},
              'C2': {f: [[pairs['rows'][f]['pairs'][i]['A'],
                          pairs['rows'][f]['pairs'][i]['B']] for i in valid[f]]
                     for f in sorted(valid)}}
    for channel in result.values():
        for pp in channel.values():
            if len(pp) != 2 or any(len(p) != 2 or any(not isinstance(c, str) or not c for c in p) for p in pp):
                raise ValueError('exactly two nonempty frozen pairs required')
    return result


def prepare(bank: Path, target: Path, e12: Path, e15: Path, tokenizer: Path, out: Path):
    if out.exists():
        raise FileExistsError('E37 inputs are immutable; use a fresh cache directory')
    refs = read(HERE / 'SOURCE_REFERENCES.json')
    check_sources(dict(bank=bank, target=target, e12=e12, e15=e15,
                       tokenizer=tokenizer, repository=ROOT), refs)
    plan = read(HERE / 'PLAN.json')
    source_plan = read(ROOT / 'results/g_agreement/understand/e33/PLAN.json')
    rows = source_plan['rows']
    if plan['rows'] != rows:
        raise ValueError('all25 original frozen W1 rows required')
    public = {r['id']: r for r in records(bank / 'items.input.jsonl')}
    source = records(e12 / 'items.input.jsonl')
    ids = [r['id'] for r in source]
    if (ids != read(e12 / 'ids.json') or len(ids) != 2100 or len(set(ids)) != 2100
            or Counter(r['feature'] for r in source) != Counter({f: 84 for f in rows})):
        raise ValueError('exact E12 25x84 test population/order required')
    items = [{k: public[r['id']][k] for k in ('id', 'feature', 'donor_id')} for r in source]
    selected_smoke = smoke_ids(items)
    frozen_smoke = read(HERE / 'SMOKE_SET.json')
    if selected_smoke != frozen_smoke['selected_ids']:
        raise ValueError('frozen smoke selection changed')

    # Labels are opened only after the outcome-independent population/smoke are fixed.
    private = {r['id']: r for r in records(bank / 'items.DO_NOT_STAGE.jsonl')}
    w1 = read(bank / 'templates.json')
    if read(bank / 'manifest.json')['files']['items.DO_NOT_STAGE.jsonl'] != sha(bank / 'items.DO_NOT_STAGE.jsonl'):
        raise ValueError('W1 private manifest mismatch')
    for item in items:
        own, donor = private[item['id']], private[item['donor_id']]
        if (own['split'] != 'test' or donor['split'] != 'test' or own['feature'] != item['feature']
                or donor['feature'] != item['feature'] or own['cluster'] != donor['cluster']
                or own['value'] == donor['value'] or public[donor['id']]['donor_id'] != own['id']
                or donor['id'] not in ids):
            raise ValueError('exact reciprocal same-cluster opposite-state test donor required')
    candidates, pairs, metrics = [read(ROOT / SOURCE_NAMES[n]) for n in ('candidates', 'pairs', 'metrics')]
    templates = select_templates(w1, candidates, pairs, metrics, rows)
    e15_items = records(e15 / 'items.input.jsonl')
    e15_index = {r['id']: i for i, r in enumerate(e15_items)}
    for item in items:
        if item['feature'] in C2_ROWS:
            original = e15_items[e15_index[item['id']]]
            if item['donor_id'] != original['w1_mismatched_donor_id']:
                raise ValueError('E15 opposite-state donor mismatch')
    order = read(target / 'items.order.json')
    if len(set(order)) != len(order):
        raise ValueError('unique captured IDs required')
    index = {item_id: i for i, item_id in enumerate(order)}
    all_acts = np.load(target / 'acts44.npy', mmap_mode='r')
    if all_acts.shape != (7296, 5120) or all_acts.dtype != np.float32:
        raise ValueError('canonical W1 h44 tensor shape/dtype mismatch')
    acts = np.array(all_acts[[index[item_id] for item_id in ids]], copy=True)
    if not np.isfinite(acts).all() or np.any(np.linalg.norm(acts, axis=1) <= 0):
        raise ValueError('finite nonzero activation vectors required')
    e15_acts = np.load(e15 / 'acts44.npy', mmap_mode='r')
    for i, item in enumerate(items):
        if item['feature'] in C2_ROWS and not np.array_equal(acts[i], e15_acts[e15_index[item['id']]]):
            raise ValueError('E15 activation reuse differs by bytes')

    from transformers import AutoTokenizer
    sys.path.insert(0, str(ROOT / 'external/mats-nla-workspace/src'))
    from mats.readers.olens import OracleLens
    tok = AutoTokenizer.from_pretrained(tokenizer, local_files_only=True)
    head, marker_index = OracleLens(model=None, tok=tok, device='cpu').carrier(44)
    if head[marker_index] != 158983:
        raise ValueError('native Oracle marker changed')
    token_pairs = {channel: {f: [[tok.encode(c, add_special_tokens=False) for c in p] for p in pp]
                              for f, pp in features.items()} for channel, features in templates.items()}
    for f, pp in token_pairs['C2'].items():
        expected = [[p['A_ids'], p['B_ids']] for p in pairs['rows'][f]['pairs']]
        if pp != expected:
            raise ValueError('frozen E15 candidate tokens changed')
    carrier = {'head_ids': head, 'marker_index': marker_index, 'marker_token_id': 158983,
               'layer': 44, 'alpha': 16000, 'pad_token_id': tok.pad_token_id or 0,
               'prefix_ids': {'C1': [], 'C1prime': [], 'C2': tok.encode('- ', add_special_tokens=False), 'C4': []}}

    parity_items = [r for r in items if r['feature'] in PARITY_ROWS]
    labels = {r['id']: int(private[r['id']]['value'] == w1[r['feature']]['values'][0]) for r in parity_items}
    if len(labels) != 252 or Counter(r['feature'] for r in parity_items) != Counter({f: 84 for f in PARITY_ROWS}):
        raise ValueError('only252 fixed parity gate labels allowed')
    reference = {r['id']: r for r in records(target / 'scores.target.jsonl')
                 if r['reader'] == 'olens' and r['layer'] == 44 and r['arm'] == 'true' and r['id'] in labels}
    if set(reference) != set(labels) or any(r['status'] != 'COMPLETE' or len(r['scores']) != 2 for r in reference.values()):
        raise ValueError('complete sealed Oracle matched reference scores required')
    reference_aucs = {f: auc([np.mean(reference[r['id']]['scores']) for r in parity_items if r['feature'] == f],
                            [labels[r['id']] for r in parity_items if r['feature'] == f]) for f in PARITY_ROWS}
    parity = {'smoke_ids': selected_smoke, 'rl_reference_auc': reference_aucs,
              'reproduction_rows': list(PARITY_ROWS), 'labels_scope': '252 fixed full-row test items only',
              'w1_reference_scores_sha256': sha(target / 'scores.target.jsonl'),
              'smoke_set_sha256': sha(HERE / 'SMOKE_SET.json')}
    dev_ids = [r['id'] for r in private.values() if r['split'] == 'dev' and r['feature'] in rows]
    if len(dev_ids) != 2100:
        raise ValueError('canonical W1 dev population changed')
    out.mkdir(parents=True)
    (out / 'items.input.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in items))
    np.save(out / 'acts44.npy', acts)
    for name, value in [('templates.json', templates), ('token_pairs.json', token_pairs), ('carrier.json', carrier),
                        ('parity_labels.json', labels), ('parity_inputs.json', parity)]:
        dump(out / name, value)
    dump(out / 'provenance.json', {
        'experiment': 'E37', 'plan_sha256': sha(HERE / 'PLAN.json'),
        'source_references_sha256': sha(HERE / 'SOURCE_REFERENCES.json'),
        'smoke_set_sha256': sha(HERE / 'SMOKE_SET.json'),
        'source_files': refs['files'], 'private_labels_sha256': sha(bank / 'items.DO_NOT_STAGE.jsonl'),
        'test_ids_canonical_sha256': canonical_sha(ids), 'dev_ids_canonical_sha256': canonical_sha(dev_ids),
        'test_items': 2100, 'dev_items_not_staged': 2100, 'rows': rows,
        'parity_labels_staged': 252, 'other_private_labels_staged': 0,
        'c2_valid_pair_indices': {f: [0, 1] for f in sorted(C2_ROWS)},
        'c2_opposite_state_donor': 'exact frozen E15 w1_mismatched_donor_id, checked against W1',
        'pad_token_id': tok.pad_token_id or 0, 'eos_token_id': tok.eos_token_id,
        'tokenizer_files': refs['files']['tokenizer'], 'native_carrier': carrier,
        'model_loads': 0, 'model_forwards': 0, 'GPU_hours': 0,
        'score': 'sum candidate token log probabilities A minus B; average both frozen pairs before AUROC',
    })
    dump(out / 'INPUT_SEAL.json', {'status': 'E37_INPUTS_FROZEN_BEFORE_MODEL_LOAD',
                                  'files': {p.name: sha(p) for p in sorted(out.iterdir())}})
    return {'input_seal_sha256': sha(out / 'INPUT_SEAL.json'), 'items': len(items),
            'rl_reference_auc': reference_aucs, 'parity_labels': len(labels), 'model_loads': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bank', 'target', 'e12', 'e15', 'tokenizer', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(**vars(args)), sort_keys=True))
