"""Evaluate sealed E49 fixed probes on their recorded dev items; never fit."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def verify(root, name):
    seal = read(root/name)
    for member, digest in seal['files'].items():
        p = root/member
        assert p.resolve().is_relative_to(root.resolve()) and sha(p) == digest, member
    return seal


def run(bank, original, inventory, out, private):
    import numpy as np
    bank_seal = verify(bank, 'BANK_SEAL.json')
    outer = read(original/'OUTPUT_SEAL.json')
    assert outer['status'] == 'COMPLETE'
    assert outer['bank_seal_sha256'] == sha(bank/'BANK_SEAL.json')
    assert outer['capture_seal_sha256'] == sha(original/'capture/CAPTURE_SEAL.json')
    capture = verify(original/'capture', 'CAPTURE_SEAL.json')
    gates = verify(original/'gates', 'GATE_OUTPUT_SEAL.json')
    assert gates['capture_seal_sha256'] == sha(original/'capture/CAPTURE_SEAL.json')
    items = read(bank/'items.PRIVATE.json')
    byid = {x['id']: x for x in items}
    assert len(byid) == len(items)
    order = read(original/'capture/items.order.json')
    assert len(order) == len(set(order)) and set(order) == set(byid)
    ix = {v: i for i, v in enumerate(order)}
    acts = np.load(original/'capture/acts44.npy', mmap_mode='r', allow_pickle=False)
    assert acts.shape == (len(order), 5120)
    fits = read(original/'gates/probe_fits.json')
    rows = {x['row']: x for x in read(inventory)['rows'] if x['bank'] == 'e49'}
    assert len(fits) == len(rows) == 16
    weights = np.load(original/'gates/probe_weights.npz', allow_pickle=False)
    metrics, records, private_scores = {}, [], []
    for fit in fits:
        row = fit['row']; ids = fit['dev_ids']
        assert row in rows and len(ids) == len(set(ids)) == 84
        assert all(byid[i]['split'] == 'dev' and byid[i]['feature'] == row for i in ids)
        assert set(ids) == {x['id'] for x in items if x['split'] == 'dev' and x['feature'] == row}
        y = np.array([byid[i]['label'] for i in ids])
        assert set(y.tolist()) == {0, 1} and y.sum() == 42
        w, b = weights[row+'__w'], weights[row+'__b']
        assert w.shape == (5120,) and b.shape == ()
        assert np.isfinite(w).all() and np.isfinite(b)
        # Original worker saved effective raw-space w/model.sd and adjusted b.
        # Retain its dtype and sign; no standardization, fitting or calibration.
        scores = acts[[ix[i] for i in ids]] @ w + b
        assert scores.shape == (84,) and np.isfinite(scores).all()
        a, z = scores[y == 1], scores[y == 0]
        # E49 contract49.auc: exact pairwise AUROC with half credit for ties.
        value = float(((a[:, None] > z[None, :]) + .5*(a[:, None] == z[None, :])).mean())
        metrics[row] = dict(dev_auroc=value, n=84, positives=42,
                            recorded_dev_ids_sha256=hashlib.sha256(json.dumps(ids).encode()).hexdigest())
        records.append(dict(row_index=rows[row]['row_index'], bank='e49', row=row, split='dev',
                            source_ref=dict(seal_index=0, member='DEV_METRICS.json', keys=[row, 'dev_auroc'])))
        private_scores.extend(dict(id=i, score=float(v)) for i, v in zip(ids, scores))
    out.mkdir(parents=True, exist_ok=False)
    write(out/'DEV_METRICS.json', metrics)
    write(out/'CUSTODY.json', dict(authority='Direct Guiv fixed-weight dev AUROC ruling, 2026-10-29',
        bank_seal_sha256=sha(bank/'BANK_SEAL.json'), output_seal_sha256=sha(original/'OUTPUT_SEAL.json'),
        capture_seal_sha256=sha(original/'capture/CAPTURE_SEAL.json'), gate_seal_sha256=sha(original/'gates/GATE_OUTPUT_SEAL.json'),
        weights_sha256=sha(original/'gates/probe_weights.npz'), fits_sha256=sha(original/'gates/probe_fits.json'),
        activations_sha256=sha(original/'capture/acts44.npy'), order_sha256=sha(original/'capture/items.order.json'),
        private_items_sha256=sha(bank/'items.PRIVATE.json'), source_sha256=sha(Path(__file__)),
        inventory_sha256=sha(inventory), method='Original fixed raw-space weights, original dev IDs, pairwise AUROC; no fit/sign change/test scoring'))
    write(out/'NUMERIC_SOURCE_SEAL.json', dict(metric='dev_probe_auroc', files={n:sha(out/n) for n in ['DEV_METRICS.json','CUSTODY.json']}))
    write(out/'DEV_PROBES.json', records)
    write(out/'EVIDENCE_SEAL.json', dict(metric='dev_probe_auroc',
        source_seals=[dict(seal=str((out/'NUMERIC_SOURCE_SEAL.json').resolve()), sha256=sha(out/'NUMERIC_SOURCE_SEAL.json'))],
        files={n:sha(out/n) for n in ['DEV_METRICS.json','CUSTODY.json','NUMERIC_SOURCE_SEAL.json','DEV_PROBES.json']}))
    private.mkdir(parents=True, exist_ok=True)
    write(private/'DEV_SCORES.PRIVATE.json', private_scores)
    return dict(rows=len(metrics), dev_items=len(private_scores), evidence_seal_sha256=sha(out/'EVIDENCE_SEAL.json'))


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for n in ['bank','original','inventory','out','private']:p.add_argument('--'+n, required=True, type=Path)
    print(json.dumps(run(**vars(p.parse_args()))))
