"""E35 2026-10-25: label-blind, source-group-held-out token selection."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

CORPUS_SHA = 'e89a09d72dde84d8ab8aa0c33ed772682e04035899a88a7c9f8ef5063ce21273'
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
MANIFEST_SHA = 'd7d06c220a065379dc42d4b60f1e044f3b153f2d74ab8a876fa54056b7f1c6d0'
SEED = 20261025
N_TOKENS = 50000
MAX_LENGTH = 512


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(x):
    return hashlib.sha256(x.encode()).hexdigest()


def dump_new(path, x):
    with Path(path).open('x') as f:
        f.write(json.dumps(x, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def is_heldout(group_id):
    return int(digest(f'E35|{SEED}|holdout|{group_id}'), 16) % 5 == 0


def token_rank(doc_id, position):
    return digest(canonical(['E35', SEED, 'token', doc_id, position]))


def read_corpus(corpus, manifest):
    if sha(corpus) != CORPUS_SHA or sha(manifest) != MANIFEST_SHA:
        raise ValueError('frozen section-79 corpus/manifest checksum mismatch')
    rows = [json.loads(line) for line in Path(corpus).read_text().splitlines() if line]
    registered = json.loads(Path(manifest).read_text())['documents']
    if len(rows) != 2400 or len({r['id'] for r in rows}) != 2400:
        raise ValueError('exact 2400 distinct corpus documents required')
    by_id = {r['id']: r for r in registered}
    if set(by_id) != {r['id'] for r in rows}:
        raise ValueError('registered document IDs differ')
    for r in rows:
        if digest(r['text']) != r['text_sha256']:
            raise ValueError('document text checksum mismatch')
        if any(r[k] != by_id[r['id']][k] for k in ('group_id', 'domain', 'text_sha256')):
            raise ValueError('registered grouping/content differs')
    return rows


def make_sample(rows, encode):
    """Hash selection is independent of text labels, model activations and SAE output."""
    encoded = {r['id']: encode(r['text']) for r in rows}
    prefix = {key: ids[:MAX_LENGTH] for key, ids in encoded.items()}
    held = [r for r in rows if is_heldout(r['group_id'])]
    train = [r for r in rows if not is_heldout(r['group_id'])]
    pool = [(token_rank(r['id'], p), r['id'], p)
            for r in held for p in range(len(prefix[r['id']]))]
    if len(pool) < N_TOKENS:
        raise ValueError('insufficient held-out tokens; no adaptive reseed permitted')
    selected = defaultdict(list)
    for _, doc_id, p in sorted(pool)[:N_TOKENS]:
        selected[doc_id].append(p)
    records = []
    domains = Counter()
    for r in sorted(held, key=lambda r: r['id']):
        if r['id'] not in selected:
            continue
        positions = sorted(selected[r['id']])
        domains[r['domain']] += len(positions)
        records.append({'id': r['id'], 'group_id': r['group_id'], 'domain': r['domain'],
                        'text_sha256': r['text_sha256'], 'prefix_tokens': len(prefix[r['id']]),
                        'prefix_ids_sha256': digest(canonical(prefix[r['id']])),
                        'positions': positions})
    # Longest 512-token training documents provide a conservative, score-free pilot.
    pilot = sorted(train, key=lambda r: (-len(prefix[r['id']]), token_rank(r['id'], -1)))[:3]
    if len(pilot) != 3 or any(len(prefix[r['id']]) != MAX_LENGTH for r in pilot):
        raise ValueError('three distinct full-length training pilot documents required')
    excluded = sorted({r['group_id'] for r in held})
    return {
        'date': '2026-10-25', 'seed': SEED, 'n_tokens': N_TOKENS, 'max_length': MAX_LENGTH,
        'corpus_sha256': CORPUS_SHA, 'corpus_manifest_sha256': MANIFEST_SHA,
        'tokenizer_sha256': TOKENIZER_SHA,
        'split_rule': 'int(sha256(UTF8(E35|20261025|holdout| + group_id)),16) % 5 == 0',
        'token_rule': 'smallest SHA256(canonical JSON [E35,20261025,token,doc_id,position]); no replacement',
        'render': 'raw text; add_special_tokens=False; first 512 tokens; no chat wrapper or packing',
        'excluded_training_group_ids': excluded, 'documents': records,
        'pilot_document_ids': [r['id'] for r in pilot],
        'inventory': {'documents': len(rows), 'heldout_documents': len(held),
                      'training_documents': len(train), 'raw_tokens': sum(map(len, encoded.values())),
                      'prefix_tokens': sum(map(len, prefix.values())), 'heldout_prefix_tokens': len(pool),
                      'training_prefix_tokens': sum(len(prefix[r['id']]) for r in train),
                      'selected_tokens_by_domain': dict(sorted(domains.items()))},
    }


def verify_sample(corpus, manifest, tokenizer, sample):
    from tokenizers import Tokenizer
    if sha(tokenizer) != TOKENIZER_SHA:
        raise ValueError('pinned tokenizer checksum mismatch')
    rows = read_corpus(corpus, manifest)
    tok = Tokenizer.from_file(str(tokenizer))
    encode = lambda text: tok.encode(text, add_special_tokens=False).ids
    expected = make_sample(rows, encode)
    if expected != sample:
        raise ValueError('sealed held-out sample differs from deterministic selection')
    return {r['id']: encode(r['text'])[:MAX_LENGTH] for r in rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('corpus', 'manifest', 'tokenizer', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    a = parser.parse_args()
    from tokenizers import Tokenizer
    if sha(a.tokenizer) != TOKENIZER_SHA:
        raise ValueError('pinned tokenizer checksum mismatch')
    tok = Tokenizer.from_file(str(a.tokenizer))
    sample = make_sample(read_corpus(a.corpus, a.manifest),
                         lambda text: tok.encode(text, add_special_tokens=False).ids)
    dump_new(a.out, sample)
    print(canonical({'status': 'CPU_SAMPLE_SEALED', 'sample_sha256': sha(a.out),
                     'inventory': sample['inventory'], 'GPU_hours': 0}))


if __name__ == '__main__':
    main()
