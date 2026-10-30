"""Stage only the newly authorized three-row E28 environment parity gate."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import contract as C

ROWS = ['prose_sentiment', 'prose_paren', 'python_string']
E37_SEAL = 'e499952a84f5fc76d3b08419f36af1e7aea3ed981df08aa4c0e0b9d61449e6f6'


def prepare(e28, e37, out):
    import numpy as np
    e28, e37 = Path(e28), Path(e37)
    C.verify(e28)
    C.verify(e37)
    if C.sha(e37 / 'INPUT_SEAL.json') != E37_SEAL:
        raise ValueError('frozen W1 parity source differs')
    items = [r for r in C.rows(e28 / 'test.jsonl') if r['feature'] in ROWS]
    if Counter(r['feature'] for r in items) != Counter({r: 84 for r in ROWS}):
        raise ValueError('three full 84-item W1 rows required')
    source = C.rows(e37 / 'items.input.jsonl')
    source_ix = {r['id']: i for i, r in enumerate(source)}
    labels = C.read(e37 / 'parity_labels.json')
    refs = C.read(e37 / 'parity_inputs.json')
    if set(labels) != {r['id'] for r in items} or refs['reproduction_rows'] != ROWS:
        raise ValueError('exact registered parity label population required')
    source_acts = np.load(e37 / 'acts44.npy', allow_pickle=False)
    acts = source_acts[[source_ix[r['id']] for r in items]]
    test = C.rows(e28 / 'test.jsonl')
    test_ix = {r['id']: i for i, r in enumerate(test)}
    original = np.load(e28 / 'test.acts44.npy', allow_pickle=False)
    if not np.array_equal(acts, original[[test_ix[r['id']] for r in items]]):
        raise ValueError('original E28/W1 activation mismatch')
    templates = C.read(e28 / 'templates.json')
    source_pairs = C.read(e37 / 'templates.json')['C1']
    if any(templates[r]['olens'] != source_pairs[r] for r in ROWS):
        raise ValueError('original frozen W1 pairs differ')
    out = C.cache_output(out)
    C.jsonl(out / 'items.jsonl', items)
    np.save(out / 'acts44.npy', acts, allow_pickle=False)
    C.dump(out / 'labels.json', labels)
    C.dump(out / 'templates.json', {r: templates[r] for r in ROWS})
    C.dump(out / 'REFERENCE.json', {
        'schema': 'E28_PRETRAIN_PARITY_v1', 'status': 'FROZEN', 'date': '2026-10-25',
        'rows': ROWS, 'reference_auc': refs['rl_reference_auc'], 'max_abs_auroc_delta': .03,
        'original_e28_input_seal_sha256': C.sha(e28 / 'INPUT_SEAL.json'),
        'source_e37_input_seal_sha256': E37_SEAL,
        'source_notes': 'User-authorized pre-training environment gate; exact W1 block44 bytes and frozen pairs; '
                        'W1 sealed score SHA36deb8474a126b6947e4d8adae067192ccf726b35fc5b9becc21d30de96c70fb; '
                        'A-positive row AUROC from arithmetic mean of both paired log-odds; '
                        'only252 gate labels staged; original E28 bank and scientific PLAN unchanged'})
    C.seal(out)
    return {'status': 'FROZEN', 'items': 252, 'parity_input_seal_sha256': C.sha(out / 'INPUT_SEAL.json'),
            'original_e28_input_seal_sha256': C.sha(e28 / 'INPUT_SEAL.json'),
            'activation_and_pair_parity': 'BYTE_IDENTICAL', 'model_calls': 0}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('e28', 'e37', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    result = prepare(a.e28, a.e37, a.out)
    C.dump(C.HERE / 'PARITY_PREPARATION_2026-10-25.json', result)
    print(result['status'])
