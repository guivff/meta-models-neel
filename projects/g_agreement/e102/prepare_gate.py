"""CPU-only sealed parity and disjoint dev capture export for the disposable gate."""
import argparse
import json
from pathlib import Path
import numpy as np
from projects.g_agreement.e96.prepare_smoke_inputs import verify
from projects.g_agreement.e96.reconstructor_check import digest, write


def prepare(cache, out, receipt):
    root = cache / 'g_agreement/understand'
    out.mkdir(parents=True, exist_ok=False)
    sources = []
    def checked(path, name):
        seal = verify(path, name)
        sources.append({'path': str(path / name), 'sha256': digest(path / name), 'verified_files': len(seal['files'])})
        return seal
    capture = root / 'e49/verified_section149/out/capture'
    readers = root / 'e49/verified_section149/out/readers'
    checked(capture, 'CAPTURE_SEAL.json')
    rs = checked(readers, 'READER_OUTPUT_SEAL.json')
    if rs['capture_seal_sha256'] != digest(capture / 'CAPTURE_SEAL.json'):
        raise ValueError('reader capture binding')
    order = json.loads((capture / 'items.order.json').read_text())
    records = [json.loads(s) for s in (readers / 'asserted_vs_hypothetical/oracle_native.jsonl').read_text().splitlines()][:3]
    if len(records) != 3 or any(r['block'] != 44 or r['malformed'] for r in records):
        raise ValueError('three sealed Oracle fixtures required')
    parity = [{'id': r['id'], 'expected_text': r['text']} for r in records]
    acts = np.load(capture / 'acts44.npy', allow_pickle=False)
    np.save(out / 'parity.npy', np.stack([acts[order.index(r['id'])] for r in records]), allow_pickle=False)
    write(out / 'parity.json', parity)
    bank = root / 'e57/inputs_v4_single'
    checked(bank, 'INPUT_SEAL.json')
    items = json.loads((bank / 'items.json').read_text())
    selected = [r for r in items if r['split'] == 'dev' and r['feature'] == 'nesting_depth'][:16]
    if len(selected) != 16:
        raise ValueError('16 dev items required')
    vectors = {}
    for shard in range(3):
        c = root / f'e56_e57/verified_pull_single_v1/shard_{shard}/out/e57/capture'
        seal = checked(c, 'CAPTURE_SEAL.json')
        if seal.get('input_seal_sha256') != digest(bank / 'INPUT_SEAL.json'):
            raise ValueError('E57 capture input binding')
        ids = json.loads((c / 'items.order.json').read_text())
        a = np.load(c / 'acts44.npy', allow_pickle=False)
        for item in selected:
            if item['id'] in ids:
                if item['id'] in vectors: raise ValueError('duplicate capture')
                vectors[item['id']] = a[ids.index(item['id'])]
    train_ids = [r['id'] for r in selected]
    if set(train_ids) & {r['id'] for r in parity}: raise ValueError('parity/train overlap')
    h = np.stack([vectors[k] for k in train_ids])
    if h.shape != (16,5120) or not np.isfinite(h).all(): raise ValueError('dev vectors')
    np.save(out / 'dev.npy', h, allow_pickle=False)
    write(out / 'dev_ids.json', train_ids)
    write(out / 'INPUT_SEAL.json', {'status': 'E102_DISPOSABLE_GATE_INPUTS', 'files': {p.name: digest(p) for p in sorted(out.iterdir())}, 'training_split': 'dev', 'parity_inference_only': True})
    write(receipt, {'status': 'SEALED_GATE_INPUTS_GPU_NOT_RUN', 'sources': sources, 'input_seal_sha256': digest(out / 'INPUT_SEAL.json'), 'parity_items': 3, 'dev_items': 16, 'dev_row': 'E57/nesting_depth', 'training_targets': 'pre-update own greedy dev text; sealed before optimizer creation', 'production_initialization': 'reload original pinned adapter; never use gate checkpoint', 'labels_staged': False})


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('cache','out','receipt'): p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); prepare(a.cache, a.out, a.receipt)
