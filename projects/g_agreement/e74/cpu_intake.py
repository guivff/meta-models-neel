"""LOCAL CPU ONLY: verify pulled capture, fit dev probes, prepare W-lens intake.

Never place this tool's input labels or output in a pod package. No reader file
is opened. Ordinal estimator choice remains explicitly pending Guiv's ruling.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import shutil
import sys
import numpy as np
from . import ops, resident

PRIVATE_SHA = '4c4d37455cee227a8e633dde66693ad7fdf148fd08b05e7211adf02d067c096e'
PROBE_SHA = '955a7b516d97bee88b149bee1b8a3d9cdffaa7ef1b407cdef5cc4159f4677ae7'
METRICS_SHA = '17ff3b1467186a8c4e24e76ed52d2263b0201e651e2010d4b99bd47c25cda473'
ORDINAL = {'W1/python_depth_ordinal', 'W1/table_column_ordinal'}


def labels(path):
    ops.require(ops.sha(path) == PRIVATE_SHA, 'frozen private map differs')
    rows = [json.loads(s) for s in Path(path).read_text().splitlines()]
    ops.require(len(rows) == resident.N and len({r['id'] for r in rows}) == resident.N, 'private coverage differs')
    return rows


def prepare(private_map, port_seal, out):
    rows = labels(private_map)
    ops.require(ops.sha(port_seal) == resident.PORT_SHA, 'port seal differs')
    out.mkdir(parents=True, exist_ok=False)
    readers = sorted(r['id'] for r in rows if r['shape'] == 'binary' and r['source_labels']['split'] == 'test')
    ops.require(len(readers) == resident.READERS, 'test coverage differs')
    ops.write(out/'READER_PLAN.json', {'schema_version': 1, 'experiment': 'E74', 'port_seal_sha256': resident.PORT_SHA,
              'item_input_sha256': resident.ITEM_SHA, 'ids': readers})
    units = sorted({r['bank']+'/'+r['row'] for r in rows})
    ops.require(len(units) == 83, 'row inventory differs')
    ops.write(out/'ROWS.CPU_ONLY.json', {'rows': [{'row': x} for x in units]})
    shutil.copyfile(port_seal, out/'PORT_SEAL.json')
    ops.seal(out, ['ROWS.CPU_ONLY.json', 'PORT_SEAL.json', 'READER_PLAN.json'], status='CPU_INPUT_BINDING', track='G',
             original_port_seal_sha256=resident.PORT_SHA, private_map_sha256=PRIVATE_SHA,
             no_labels_or_splits_changed=True)


def fit_binary(xdev, ydev, xtest, ytest, fit):
    import torch
    from sklearn.metrics import roc_auc_score
    ops.require(set(ydev) == {0, 1} and set(ytest) == {0, 1}, 'binary values incomplete')
    model = fit(torch.as_tensor(xdev), torch.as_tensor(ydev), lam=1e-3, iters=200)
    scores = model.decision(torch.as_tensor(xtest)).numpy()
    ops.require(np.isfinite(scores).all(), 'probe predictions invalid')
    raw = (model.w/model.sd).numpy()
    return {'auroc': float(roc_auc_score(ytest, scores)), 'scores': scores,
            'raw_coefficient': raw, 'raw_intercept': float(model.b-(model.mu*model.w/model.sd).sum()),
            'mu': model.mu.numpy(), 'sd': model.sd.numpy()}


def fit_probes(rows, captures, fit):
    grouped = defaultdict(list)
    for row in rows: grouped[row['bank']+'/'+row['row']].append(row)
    results = []; params = {}; predictions = []
    for number, (name, group) in enumerate(sorted(grouped.items())):
        dev = [r for r in group if r['source_labels']['split'] == 'dev']
        test = [r for r in group if r['source_labels']['split'] == 'test']
        ops.require(len(dev)+len(test) == len(group), 'unknown split')
        ops.require(not {r['source_labels']['cluster'] for r in dev} & {r['source_labels']['cluster'] for r in test}, 'cluster leakage')
        if name in ORDINAL:
            ops.require(len(dev) == len(test) == 144, 'ordinal inventory differs')
            results.append({'row': name, 'status': 'CAPTURE_RETAINED_ESTIMATOR_PENDING_GUIV',
                            'confirmatory_excluded': True, 'n_dev': len(dev), 'n_test': len(test), 'probe_auroc': None})
            continue
        ops.require(len(dev) == len(test) == 84, 'binary row coverage differs')
        values = sorted({r['source_labels']['value'] for r in dev})
        ops.require(len(values) == 2 and {r['source_labels']['value'] for r in test} == set(values), 'unknown binary label')
        ydev = np.array([int(r['source_labels']['value'] == values[0]) for r in dev])
        ytest = np.array([int(r['source_labels']['value'] == values[0]) for r in test])
        xd = np.stack([captures[r['id']] for r in dev]); xt = np.stack([captures[r['id']] for r in test])
        result = fit_binary(xd, ydev, xt, ytest, fit)
        prefix = f'row_{number:03d}'
        for k in ('raw_coefficient', 'mu', 'sd'): params[prefix+'_'+k] = result[k]
        params[prefix+'_raw_intercept'] = np.array(result['raw_intercept'])
        params[prefix+'_dev_class_mean_difference'] = xd[ydev == 1].mean(0) - xd[ydev == 0].mean(0)
        results.append({'row': name, 'status': 'COMPLETE', 'probe_auroc': result['auroc'], 'probe_pass': result['auroc'] >= .90,
                        'n_dev': 84, 'n_test': 84, 'positive_value': values[0], 'fit_split': 'dev', 'parameters_prefix': prefix})
        predictions.extend({'id': r['id'], 'score': float(s)} for r, s in zip(test, result['scores']))
    return results, params, predictions


def run(private_map, capture_seal, capture_sha, input_seal, input_sha, mats_src, out):
    import torch
    torch.set_num_threads(1)
    rows = labels(private_map)
    inputs = ops.verify_seal(input_seal, input_sha)
    ops.require(inputs['private_map_sha256'] == PRIVATE_SHA and inputs['original_port_seal_sha256'] == resident.PORT_SHA, 'CPU input provenance differs')
    cap = ops.verify_seal(capture_seal, capture_sha)
    ops.require(cap['status'] == 'CAPTURE_COMPLETE' and cap['n'] == resident.N and cap['block'] == 51
                and cap['input_seal_sha256'] == resident.PORT_SHA and cap['item_input_sha256'] == resident.ITEM_SHA, 'complete registered capture required')
    captures = {}
    for name in cap['files']:
        if name.endswith('.tar'):
            ids, a = resident.read_capture(Path(capture_seal).parent/name)
            ops.require(not set(ids) & set(captures), 'duplicate captured item')
            captures.update(zip(ids, a))
    ops.require(set(captures) == {r['id'] for r in rows}, 'capture/private map coverage differs')
    ops.require(ops.sha(mats_src/'mats/probes.py') == PROBE_SHA and ops.sha(mats_src/'mats/metrics.py') == METRICS_SHA, 'existing probe source differs')
    sys.path.insert(0, str(mats_src.resolve()))
    from mats import probes
    ops.require(ops.sha(probes.__file__) == PROBE_SHA, 'probe module shadowed')
    out.mkdir(parents=True, exist_ok=False)
    ops.write(out/'ONCE.json', {'capture_seal_sha256': capture_sha, 'input_seal_sha256': input_sha})
    result, params, predictions = fit_probes(rows, captures, probes.fit_logreg)
    ops.write(out/'PROBES.CPU_ONLY.json', {'rows': result, 'probe_source_sha256': PROBE_SHA,
        'method': 'Existing mats fit_logreg; lam1e-3;200LBFGS;dev-only standardization;held-out test AUROC',
        'ordinals': 'Estimator pending Guiv; no new estimator or scoring rule invented'})
    with (out/'PARAMETERS.CPU_ONLY.npz').open('xb') as f: np.savez(f, **params)
    ops.write(out/'PREDICTIONS.CPU_ONLY.json', {'predictions': predictions})
    # Normalize the W-lens interface without changing the raw capture seal. Reuse
    # local payloads by hardlink on the same filesystem, copy otherwise.
    normalized = out/'wlens_capture'; normalized.mkdir()
    for name in cap['files']:
        dest = ops.safe(normalized, name); dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(capture_seal).parent/name, dest)
    ops.write(normalized/'RAW_CAPTURE_SEAL.json', cap)
    normalized_seal = dict(cap, input_seal_sha256=input_sha,
        original_capture_seal_sha256=capture_sha, original_port_seal_sha256=resident.PORT_SHA,
        files={**cap['files'], 'RAW_CAPTURE_SEAL.json': ops.sha(normalized/'RAW_CAPTURE_SEAL.json')})
    # W-lens checks original capture chronology, so retain its sealed_at exactly.
    ops.write(normalized/'SEAL.json', normalized_seal)
    ops.seal(out, ['ONCE.json', 'PROBES.CPU_ONLY.json', 'PARAMETERS.CPU_ONLY.npz', 'PREDICTIONS.CPU_ONLY.json', 'wlens_capture/SEAL.json'],
             status='BINARY_PROBES_COMPLETE_ORDINAL_PENDING', track='G', capture_seal_sha256=capture_sha,
             input_seal_sha256=input_sha, normalized_capture_seal_sha256=ops.sha(normalized/'SEAL.json'),
             reader_outputs_accessed=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['prepare', 'probe'])
    p.add_argument('--private-map', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--port-seal', type=Path); p.add_argument('--capture-seal', type=Path); p.add_argument('--capture-sha256')
    p.add_argument('--input-seal', type=Path); p.add_argument('--input-sha256'); p.add_argument('--mats-src', type=Path)
    a = p.parse_args()
    if a.mode == 'prepare': prepare(a.private_map, a.port_seal, a.out)
    else: run(a.private_map, a.capture_seal, a.capture_sha256, a.input_seal, a.input_sha256, a.mats_src, a.out)


if __name__ == '__main__': main()
