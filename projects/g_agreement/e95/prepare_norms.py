"""E76 native-layer norm recipe on sealed E95 source captures; CPU only."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def read(p):
    return json.loads(p.read_text())


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def prepare(config, out):
    result = {}
    for bank, spec in read(config).items():
        source = Path(spec['bank'])
        frozen = read(source/'BANK_SEAL.json')
        assert sha(source/'items.PRIVATE.json') == frozen['files']['items.PRIVATE.json']
        records = read(source/'items.PRIVATE.json')
        wanted = {x['id'] for x in records if x['split'] == 'test'}
        known = {x['id'] for x in records}
        found, values, receipts = set(), [], []
        for directory in spec['captures']:
            p = Path(directory)
            seal = read(p/'CAPTURE_SEAL.json')
            for name in ('acts42.npy', 'items.order.json'):
                assert sha(p/name) == seal['files'][name], (bank, name)
            order = read(p/'items.order.json')
            h = np.load(p/'acts42.npy', mmap_mode='r', allow_pickle=False)
            assert h.shape == (len(order), 5120) and len(set(order)) == len(order)
            assert set(order) <= known
            indices = [i for i, oid in enumerate(order) if oid in wanted]
            ids = {order[i] for i in indices}
            assert not found & ids
            found |= ids
            norms = np.linalg.norm(np.asarray(h[indices], dtype=np.float64), axis=1)
            assert np.isfinite(norms).all() and (norms > 0).all()
            values.extend(norms.tolist())
            receipts.append(dict(capture_seal_sha256=sha(p/'CAPTURE_SEAL.json'),
                acts42_sha256=sha(p/'acts42.npy'), order_sha256=sha(p/'items.order.json'),
                test_items=len(indices)))
        assert found == wanted and len(values) == len(wanted), (bank, len(found), len(wanted))
        result[bank] = dict(layer=42, test_items=len(values), median_norm=float(np.median(values)),
            population='All frozen test raw read-point vectors in this bank at block 42, as E76',
            norm_arithmetic='float64 Euclidean norm then median',
            bank_seal_sha256=sha(source/'BANK_SEAL.json'),
            items_sha256=sha(source/'items.PRIVATE.json'), captures=receipts)
    out.mkdir(parents=True, exist_ok=True)
    target = out/'NLA_NORMS.json'
    target.write_text(json.dumps(dict(experiment='E95', banks=result), indent=2)+'\n')
    info = target.stat()
    receipt = dict(experiment='E95', stage='CPU norm preparation',
        first_output_utc=datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat(),
        first_output_evidence=dict(member=target.name, sha256=sha(target), mtime_ns=info.st_mtime_ns,
                                   source='file mtime'),
        files={target.name: sha(target)}, source_config_sha256=sha(config), GPU_calls=0, judge_calls=0)
    (out/'NLA_NORM_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({b: dict(test_items=x['test_items'], median_norm=x['median_norm'])
                      for b,x in result.items()}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    prepare(args.config, args.out)
