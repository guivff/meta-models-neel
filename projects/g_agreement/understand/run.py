"""Integrator-only offline E3/E4 calibration, collection and sealing.

No provisioning, SSH, downloads or label reads. Run all calibrations, then the
aggregate gate, then collections; each phase is a separate process so two 27B
models are never resident together. Each invocation shares one budget ledger.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import gc
import json
import math
import os
from pathlib import Path
import tempfile
import time

import numpy as np

from projects.g_agreement.blindspot import protocol as P
from .budget import Ledger, PHASES, forecast, source_hashes
from .inputs import load_inputs

BATCH = {'E3': 32, 'E4': 1, 'target': 1}


def _array(x):
    return x.detach().cpu().float().numpy() if hasattr(x, 'detach') else np.asarray(x)


def units(data, experiment, phase):
    batch = BATCH['target' if phase == 'target' else experiment]
    result = []
    for row in data['rows']:
        ix = [i for i, item in enumerate(data['items']) if item['feature'] == row['feature']]
        for start in range(0, len(ix), batch):
            result.append((row['feature'], ix[start:start+batch]))
    return result


def _call(runtime, data, experiment, phase, feature, indices):
    import torch
    layer = 42 if phase == 'nla' else 44
    acts = torch.as_tensor(np.array(data['activations'][layer][indices], copy=True))
    if phase == 'target':
        directions = torch.as_tensor(np.stack([data['directions'][feature+'__L44']]*len(indices)))
        return runtime.target_directional(acts, [data['items'][i]['ids'] for i in indices], directions, layer=44)
    if experiment == 'E3':
        return runtime.capture(acts)
    return runtime.gradients(acts, data['templates'][feature][phase])


def warm_unit(data, runtime, experiment, phase):
    """Longest full batch by native sequence length, fixed before any scores."""
    candidates = units(data, experiment, phase)
    if phase == 'target':
        return max(candidates, key=lambda c: (len(c[1]), max(len(data['items'][i]['ids']) for i in c[1])))
    if experiment == 'E3' or phase == 'jlens':
        return max(candidates, key=lambda c: len(c[1]))
    tok = runtime.reader.tok
    def cost(c):
        f, ix = c
        # W1 uses both phrasing pairs. Sequence length drives reader cost.
        return (len(ix), sum(max(len(tok.encode(s, add_special_tokens=False)) for s in pair)
                             for pair in data['templates'][f][phase]))
    return max(candidates, key=cost)


def _sync():
    import torch
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def calibrate(runtime, data, experiment, phase, checkpoint, timing_dir=None):
    feature, indices = warm_unit(data, runtime, experiment, phase)
    checkpoint()
    result = _call(runtime, data, experiment, phase, feature, indices)
    _sync()
    del result  # unscored warm-up; no predictions persisted or inspected
    timings = []
    for _ in range(3):
        checkpoint(); _sync(); start = time.monotonic()
        result = _call(runtime, data, experiment, phase, feature, indices)
        # Time actual host transfer, disk output and checksums as well as GPU
        # work. These temporary outputs are discarded, never analysed.
        with tempfile.TemporaryDirectory(prefix='timing-', dir=timing_dir) as tmp:
            payload = result.get('stages', {}) if result['status'].startswith('NOT_APPLICABLE') else {
                k: result[k] for k in ('residuals', 'input_stage', 'gradients', 'scores', 'derivatives', 'rms', 'l2') if k in result}
            for key, value in payload.items():
                path = Path(tmp)/(key+'.npy')
                np.save(path, _array(value), allow_pickle=False)
                with path.open('rb') as stream:
                    os.fsync(stream.fileno())
                P.sha(path)
        _sync(); timings.append(time.monotonic()-start)
        del result
    n = len(units(data, experiment, phase))
    return {'warmups': 1, 'timings_seconds': timings, 'units': n,
            'forecast_seconds': forecast(timings, n), 'batch': BATCH['target' if phase == 'target' else experiment],
            'timing_feature': feature, 'timing_item_ids': [data['items'][i]['id'] for i in indices],
            'selection': 'longest native candidate sequence full batch; target longest frozen input',
            'outputs': 'discarded; timing forwards are charged as science'}


def collect(runtime, data, experiment, phase, out, checkpoint):
    """Write each row durably; only complete rows are listed as complete."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    index = []
    P.dump(out/'index.json', index)
    for row in data['rows']:
        feature = row['feature']
        work = [(f, ix) for f, ix in units(data, experiment, phase) if f == feature]
        ids = [data['items'][i]['id'] for _, ix in work for i in ix]
        record = {'feature': feature, 'reader': phase, 'n': len(ids), 'item_ids': ids,
                  'status': 'INCOMPLETE', 'arrays': {}}
        index.append(record); P.dump(out/'index.json', index)
        arrays = {}; offset = 0
        for _, ix in work:
            checkpoint()
            result = _call(runtime, data, experiment, phase, feature, ix)
            payload = {}
            if phase == 'target':
                payload = {k: result[k] for k in ('derivatives', 'rms', 'l2')}
                record['target_objective'] = 'all next-token logits: exact J(h)u at block44; rms and L2 over vocabulary'
            elif experiment == 'E3':
                if result['status'].startswith('NOT_APPLICABLE'):
                    record['status'] = result['status']
                    record['reason'] = 'native J-lens is a static linear map plus cosine unembedding; no residual layers or token positions'
                    payload = {'stage_'+k: v for k, v in result.get('stages', {}).items()}
                else:
                    payload = {k: result[k] for k in ('residuals', 'input_stage')}
                    layers, positions = list(result['layers']), list(result['positions'])
                    if ('layers' in record and (record['layers'] != layers or record['positions'] != positions)):
                        raise ValueError('layer/position metadata changed within row')
                    record['layers'] = layers; record['positions'] = positions
            else:
                if result['status'] != 'COMPLETE':
                    raise ValueError('gradient status: '+str(result))
                payload = {k: result[k] for k in ('scores', 'gradients')}
            for key, value in payload.items():
                a = _array(value)
                if len(a) != len(ix) or not np.isfinite(a).all():
                    raise ValueError('nonfinite/misaligned '+key)
                if key not in arrays:
                    name = feature+'.'+key+'.npy'
                    arrays[key] = np.lib.format.open_memmap(out/name, mode='w+', dtype=np.float32,
                                                            shape=(len(ids), *a.shape[1:]))
                    record['arrays'][key] = name
                elif tuple(a.shape[1:]) != tuple(arrays[key].shape[1:]):
                    raise ValueError('array shape changed within row: '+key)
                arrays[key][offset:offset+len(ix)] = a
                arrays[key].flush()
            offset += len(ix)
            del result
        if offset != len(ids):
            raise ValueError('row incomplete')
        if record['status'] == 'INCOMPLETE':
            record['status'] = 'COMPLETE'
        record['array_sha256'] = {k: P.sha(out/v) for k, v in record['arrays'].items()}
        P.dump(out/'index.json', index)
        arrays.clear(); gc.collect()
    return index


def _inputs_for(a):
    primary = a.inputs/a.experiment.lower()
    relevant = {'primary': P.sha(primary/'INPUT_SEAL.json')}
    if a.experiment == 'E4':
        relevant['e9'] = P.sha(a.inputs/'e9/INPUT_SEAL.json')
    return primary, relevant


def worker(a):
    os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
    primary, seals = _inputs_for(a)
    ledger = Ledger(a.assignment, a.out/'budget', a.experiment, seals)
    try:
        if a.action == 'gate':
            print(json.dumps(ledger.gate(), indent=2)); return
        if a.phase not in PHASES[a.experiment]:
            raise ValueError('unknown phase')
        phase = ledger.state['phases'].setdefault(a.phase, {})
        key = 'calibration' if a.action == 'calibrate' else 'collection'
        if key in phase or key+'_started' in phase:
            raise ValueError('phase already attempted; no implicit rerun')
        if a.action == 'collect' and not ledger.state.get('gate', {}).get('admitted'):
            raise ValueError('aggregate warmed gate must admit full run first')
        phase[key+'_started'] = True; ledger.save()
        with ledger.charge(a.phase, 'setup'):
            data = load_inputs(a.inputs/'e9' if a.phase == 'target' else primary)
            from .reader_runtime import load_runtime
            runtime = load_runtime(a.phase, a.assets, device=a.device)
        with ledger.charge(a.phase, 'science'):
            if a.action == 'calibrate':
                phase[key] = calibrate(runtime, data, a.experiment, a.phase, ledger.check, a.out/'budget')
            else:
                directory = a.out/a.phase
                collect(runtime, data, a.experiment, a.phase, directory, ledger.check)
                P.dump(directory/'provenance.json', {
                    'experiment': a.experiment, 'phase': a.phase,
                    'input_seal_sha256': P.sha((a.inputs/'e9' if a.phase == 'target' else primary)/'INPUT_SEAL.json'),
                    'source_files': source_hashes(), 'assignment_sha256': P.sha(a.assignment),
                    'orientation': 'W1 A-minus-B; no sign flips', 'new_target_capture': False})
                names = [p.name for p in directory.iterdir() if p.is_file()]
                P.seal(directory, names, 'SCORES_SEALED_EXPLORATORY_'+a.experiment)
                phase[key] = {'score_seal_sha256': P.sha(directory/'SCORE_SEAL.json')}
        ledger.save()
    finally:
        ledger.close()


def _seal_files(a):
    """Seal completed phase outputs and explicitly enumerate every missing phase.

    This can seal partial runs after a cap/failure, without implying completion.
    Labels stay unread until the caller verifies this aggregate seal.
    """
    if (a.out/'SCORE_SEAL.json').exists():
        raise ValueError('aggregate score seal already exists')
    primary, seals = _inputs_for(a)
    statuses = {}; names = []
    for phase in PHASES[a.experiment]:
        directory = a.out/phase
        if not (directory/'SCORE_SEAL.json').exists():
            statuses[phase] = 'NOT_RUN_OR_INCOMPLETE'
            # Preserve failed partials and seal them too for honest reporting.
            if directory.exists():
                names += [str(p.relative_to(a.out)) for p in directory.iterdir() if p.is_file()]
            continue
        receipt = P.verify(directory, 'SCORE_SEAL.json')
        provenance = json.loads((directory/'provenance.json').read_text())
        expected_input = seals['e9'] if phase == 'target' else seals['primary']
        if (provenance.get('experiment') != a.experiment or provenance.get('phase') != phase
                or provenance.get('input_seal_sha256') != expected_input
                or provenance.get('source_files') != source_hashes()):
            raise ValueError('phase provenance does not match frozen run: '+phase)
        names += [phase+'/'+n for n in receipt['files']] + [phase+'/SCORE_SEAL.json']
        statuses[phase] = 'SEALED'
    P.dump(a.out/'provenance.json', {'experiment': a.experiment, 'input_seal_sha256': seals['primary'],
                                    'input_seals': seals, 'phases': statuses, 'exploratory': True,
                                    'status': 'COMPLETE' if all(v == 'SEALED' for v in statuses.values()) else 'PARTIAL'})
    names += ['provenance.json']
    return {n: P.sha(a.out/n) for n in names}


def seal(a):
    if (a.out/'SCORE_SEAL.json').exists():
        raise ValueError('aggregate score seal already exists')
    ledger = None
    try:
        local_after_pull = getattr(a, 'local_after_pull', False)
        if not local_after_pull:
            if not (a.out/'budget/ledger.json').exists():
                raise ValueError('production sealing requires existing budget ledger; use explicit local-after-pull for CPU sealing')
            if not getattr(a, 'assignment', None):
                raise ValueError('production sealing requires original assignment for cumulative accounting')
            _, seals = _inputs_for(a)
            ledger = Ledger(a.assignment, a.out/'budget', a.experiment, seals)
        with ledger.charge('aggregate_seal', 'science') if ledger else nullcontext():
            hashes = _seal_files(a)
        # Ledger is now final, so its immutable snapshot can be sealed without
        # invalidating the digest when the timed charge exits.
        if ledger:
            P.dump(a.out/'budget.final.json', ledger.state)
            hashes['budget.final.json'] = P.sha(a.out/'budget.final.json')
        elif local_after_pull and (a.out/'budget/ledger.json').exists():
            P.dump(a.out/'budget.final.json', {'sealing': 'CPU_ONLY_AFTER_PULL',
                'gpu_resume_authorized': False,
                'provider_accounting': 'integrator must reconcile separately; this seal makes no final custody claim',
                'ledger_as_pulled': json.loads((a.out/'budget/ledger.json').read_text())})
            hashes['budget.final.json'] = P.sha(a.out/'budget.final.json')
        P.dump(a.out/'SCORE_SEAL.json', {'status': 'SCORES_SEALED_EXPLORATORY_'+a.experiment, 'files': hashes})
    finally:
        if ledger:
            ledger.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('calibrate', 'gate', 'collect', 'seal'))
    p.add_argument('--experiment', choices=tuple(PHASES), required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--assignment', type=Path)
    p.add_argument('--phase', choices=('olens', 'nla', 'jlens', 'target'))
    p.add_argument('--assets', type=Path)
    p.add_argument('--device', default='cuda')
    p.add_argument('--local-after-pull', action='store_true',
                   help='seal only on CPU after retrieval; preserve ledger, never authorize GPU resumption')
    a = p.parse_args()
    if a.action == 'seal':
        seal(a)
    else:
        if a.local_after_pull:
            p.error('--local-after-pull is allowed only for seal')
        if not a.assignment or (a.action != 'gate' and (not a.assets or not a.phase)):
            p.error('assignment required; calibration/collection also require phase and assets')
        worker(a)


if __name__ == '__main__':
    main()
