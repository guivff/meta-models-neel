"""Derive one E49 smoke item from sealed caches, without consulting labels."""
import argparse
import json
from pathlib import Path
import numpy as np
from .reconstructor_check import digest, write, inputs


def verify(root, seal_name):
    seal = json.loads((root / seal_name).read_text())
    for name, expected in seal['files'].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or digest(path) != expected:
            raise ValueError('source seal mismatch: ' + name)
    return seal


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-cache', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    a = p.parse_args()
    root = a.source_cache / 'g_agreement/understand/e49'
    capture = root / 'verified_section149/out/capture'
    reader = root / 'verified_section149/out/readers'
    supplement = root / 'nla_supplement/verified_pull/out'
    supplement_input = root / 'nla_supplement/inputs_v2'
    sources = [(capture, 'CAPTURE_SEAL.json'), (reader, 'READER_OUTPUT_SEAL.json'),
               (supplement, 'OUTPUT_SEAL.json'), (supplement_input, 'INPUT_SEAL.json')]
    verified = [verify(r, s) for r, s in sources]
    capture_sha = digest(capture / 'CAPTURE_SEAL.json')
    if verified[1]['capture_seal_sha256'] != capture_sha:
        raise ValueError('reader/capture binding mismatch')
    binding = json.loads((supplement_input / 'ORIGINAL_BINDING.json').read_text())
    if binding['capture_seal_sha256'] != capture_sha:
        raise ValueError('supplement/capture binding mismatch')
    item_id = 'asserted_vs_hypothetical:6:0:0'
    oracle_path = reader / 'asserted_vs_hypothetical/oracle_native.jsonl'
    oracle = [x for x in map(json.loads, oracle_path.read_text().splitlines()) if x['id'] == item_id]
    nla = [(job, x) for job in sorted((supplement / 'jobs').glob('*.json'))
           for x in json.loads(job.read_text()) if x['id'] == item_id]
    if len(oracle) != 1 or len(nla) != 1:
        raise ValueError('greedy record must be unique')
    oracle = oracle[0]
    nla_job, nla = nla[0]
    if oracle['block'] != 44 or oracle['malformed'] or nla['malformed'] or nla['native_max_new_tokens'] != 512:
        raise ValueError('unexpected native greedy contract')
    order = json.loads((capture / 'items.order.json').read_text())
    if order.count(item_id) != 1:
        raise ValueError('capture ID must be unique')
    ix = order.index(item_id)
    h42 = np.load(capture / 'acts42.npy', allow_pickle=False)[ix:ix+1]
    h44 = np.load(capture / 'acts44.npy', allow_pickle=False)[ix:ix+1]
    supplement_order = json.loads((supplement_input / 'items.json').read_text())
    indices = [i for i, x in enumerate(supplement_order) if x['id'] == item_id]
    if len(indices) != 1 or not np.array_equal(h42, np.load(supplement_input / 'acts42.npy', allow_pickle=False)[indices]):
        raise ValueError('supplement activation mismatch')
    a.out.mkdir(parents=True, exist_ok=False)
    seals = [digest(r / s) for r, s in sources]
    write(a.out / 'item.json', dict(id=item_id, oracle_text=oracle['text'], nla_text=nla['text'], source_seals=seals))
    np.save(a.out / 'h44.npy', h44, allow_pickle=False)
    np.save(a.out / 'h42.npy', h42, allow_pickle=False)
    write(a.out / 'INPUT_SEAL.json', {'status': 'E96_ONE_ITEM_SMOKE_INPUT_FROZEN',
          'files': {n: digest(a.out / n) for n in ['item.json', 'h44.npy', 'h42.npy']}})
    inputs(a.out)
    write(a.receipt, {'status': 'INPUTS_VERIFIED_SMOKE_NOT_RUN', 'item_id': item_id,
          'selection': 'first frozen test item of eligible E49 asserted_vs_hypothetical; probe 1.0 and Oracle MISSED per sealed E49 RESULTS',
          'capture_index': ix, 'nla_supplement_index': indices[0],
          'source_seals': [{'path': str(r / s), 'sha256': h, 'verified_files': len(v['files'])}
                           for (r, s), h, v in zip(sources, seals, verified)],
          'oracle_record_file_sha256': digest(oracle_path), 'nla_record_file_sha256': digest(nla_job),
          'input_seal_sha256': digest(a.out / 'INPUT_SEAL.json'),
          'input_files': json.loads((a.out / 'INPUT_SEAL.json').read_text())['files'],
          'builder_sha256': digest(__file__), 'baseline_regenerated': False,
          'raw_text_or_labels_in_receipt': False})


if __name__ == '__main__':
    main()
