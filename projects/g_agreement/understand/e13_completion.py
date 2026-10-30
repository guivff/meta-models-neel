"""§101 E13(a): fresh full §84 free-target collection, unchanged native collector.

Only operational admission, fresh-output custody and warmed forecasting differ
from W1b free-target. No capture, scoring, resumption, or old partial-file reads.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import statistics
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from projects.g_agreement.blindspot import protocol as P, run as R

CAP = 2400
SETUP = 1500
READERS = ('olens', 'jlens', 'logit')
PROGRAM_STOP = datetime(2026, 10, 28, 23, 59, tzinfo=ZoneInfo('Europe/Zurich')).timestamp()


def forecast(timings, units, elapsed):
    if set(timings) != set(READERS) or units != 53 or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError('full three-reader/53-canonical-batch forecast required')
    for times in timings.values():
        if len(times) != 3 or any(not math.isfinite(t) or t <= 0 for t in times):
            raise ValueError('three positive warmed timings per reader required')
    remaining = sum(statistics.median(times)*units for times in timings.values())
    total = elapsed+remaining
    cap = min(1.5*total+360, CAP)
    return {'forecast_s': total, 'fresh_pass_forecast_s': remaining,
            'science_allocation_s': cap, 'fits': total <= cap,
            'timings_s': timings, 'fresh_units_per_reader': units,
            'timing_outputs_used': False, 'old_partial_outputs_used': False}


def verify_inputs(bank, capture, manifest):
    bank, capture = map(Path, (bank, capture))
    R._labels_absent(bank)
    items, _, _ = R._inputs(bank)
    policy = R._decoding(bank)
    R._runtime(bank, 32)
    capture_seal = P.verify(capture, 'CAPTURE_SEAL.json')
    score_seal = P.verify(capture, 'SCORE_SEAL.json')
    if P.sha(bank/'INPUT_SEAL.json') != manifest['input_seal_sha256']:
        raise ValueError('wrong frozen §84 bank')
    if (P.sha(capture/'CAPTURE_SEAL.json') != manifest['capture_seal_sha256'] or
            P.sha(capture/'SCORE_SEAL.json') != manifest['asked_score_seal_sha256']):
        raise ValueError('wrong sealed §84 capture/asked run')
    if not {'acts42.npy', 'acts44.npy', 'items.order.json', 'provenance.capture.json'} <= set(capture_seal['files']):
        raise ValueError('incomplete capture seal')
    if not {'acts42.npy', 'acts44.npy', 'items.order.json', 'provenance.target.json', 'scores.target.jsonl'} <= set(score_seal['files']):
        raise ValueError('incomplete asked seal')
    if (len(items) != 1680 or len({i['feature'] for i in items}) != 10 or
            [i['id'] for i in items] != json.loads((capture/'items.order.json').read_text())):
        raise ValueError('full §84 canonical item order required')
    for name in ('provenance.capture.json', 'provenance.target.json'):
        p = json.loads((capture/name).read_text())
        if p['input_seal_sha256'] != manifest['input_seal_sha256'] or p['source_files'] != manifest['original_source_files']:
            raise ValueError('original source/input lineage mismatch')
    provenance = json.loads((capture/'provenance.target.json').read_text())
    if provenance['experiment'] != 'W1b' or provenance['batch'] != 32 or provenance['execution'] is not None:
        raise ValueError('wrong original free-target settings')
    h = np.load(capture/'acts44.npy', allow_pickle=False)
    if h.ndim != 2 or len(h) != len(items) or not np.isfinite(h).all():
        raise ValueError('invalid sealed activation array')
    return items, h, policy


def collect_unit(items, h, reader, name, policy, start, checkpoint):
    end = min(start+32, len(items))
    return list(R.collect_unasked(items[start:end], h[start:end], reader, 44, name,
                policy, batch=32, checkpoint=checkpoint, canonical_indices=list(range(start, end))))


def check_grid(records, items):
    expected = {(i['id'], reader, sample) for i in items for reader in READERS for sample in range(2)}
    keys = [(r['id'], r['reader'], r['sample']) for r in records]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError('fresh free-target grid incomplete or duplicated')
    index = {i['id']: j for j, i in enumerate(items)}
    for r in records:
        j = index[r['id']]
        if (r['layer'] != 44 or r['status'] != 'COMPLETE' or r['canonical_index'] != j or
                r['canonical_batch_start'] != j//32*32):
            raise ValueError('fresh free-target cell/order invalid')


def run(a):
    manifest = json.loads(a.manifest.read_text())
    receipt = json.loads(a.receipt.read_text())
    assignment = json.loads(a.assignment.read_text())
    if (assignment.get('issuer') != 'integrator' or assignment.get('experiment') != 'E13a' or
            not assignment.get('pod_id') or assignment['pod_id'] != os.environ.get('RUNPOD_POD_ID') or
            assignment.get('manifest_sha256') != P.sha(a.manifest) or
            receipt.get('manifest_sha256') != P.sha(a.manifest) or
            assignment.get('request_sha256') != P.sha(a.receipt) or
            assignment.get('source_commit') != receipt.get('source_commit') or
            assignment.get('brief_commit') != receipt.get('brief_commit') or
            receipt.get('source_files') != manifest['source_files'] or
            assignment.get('source_files') != manifest['source_files'] or
            assignment.get('previous_gpu_seconds') != 0 or
            assignment.get('science_cap_gpu_seconds') != CAP or
            assignment.get('staging_allowance_seconds') != SETUP or
            any(assignment.get(k) is not True for k in
                ('brief_registered', 'brief_pushed', 'manifest_committed', 'external_hardstop_verified'))):
        raise ValueError('exact integrator-owned E13a assignment required')
    for field in ('source_commit', 'brief_commit', 'manifest_commit'):
        value = assignment.get(field, '')
        if len(value) != 40 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('missing pinned '+field)
    if assignment['manifest_commit'] != receipt['manifest_commit']:
        raise ValueError('wrong published manifest commit')
    created = float(assignment['provider_created_epoch'])
    deadline = float(assignment['deadline_epoch'])
    if not 0 < deadline-created <= float(assignment['allocated_gpu_seconds']):
        raise ValueError('invalid absolute custody')
    absolute = min(deadline-180, PROGRAM_STOP)
    setup_deadline = min(created+SETUP, absolute)
    if not created <= time.time() < setup_deadline:
        raise ValueError('setup expired')
    if a.out.exists():
        raise ValueError('fresh output directory required, no overwrite or resume')
    a.out.mkdir(parents=True, exist_ok=False)
    def expired(*_):
        raise TimeoutError('E13a setup/science/absolute deadline reached')
    previous = signal.signal(signal.SIGALRM, expired)
    def arm(end):
        if time.time() >= end:
            expired()
        signal.setitimer(signal.ITIMER_REAL, max(.001, end-time.time()))
    arm(setup_deadline)
    first = None
    try:
        for name, digest in manifest['source_files'].items():
            if P.sha(P.ROOT/name) != digest:
                raise ValueError('use exact archived source: '+name)
        items, array, policy = verify_inputs(a.bank, a.capture, manifest)
        import torch
        h = torch.from_numpy(array)
        assets = R._assets(a.assets, names=('model', 'olens', 'jlens'))
        ol = R._load_oracle(assets)
        from mats.readers.jlens import load_jlens
        jl = load_jlens(ol.model, ol.tok, layers=[44], path=assets['jlens'])
        readers = {'olens': ol, 'jlens': jl, 'logit': R.LogitLens(jl)}
        check_setup = lambda: arm(setup_deadline)
        for name in READERS:
            collect_unit(items, h, readers[name], name, policy, 0, check_setup)
        torch.cuda.synchronize()
        check_setup()
        P.dump(a.out/'WARMUP.json', {'status': 'UNSCORED_SETUP_COMPLETE', 'readers': list(READERS),
               'units_per_reader': 1, 'batch': 32, 'samples': policy['samples'], 'outputs_used': False})
        first = time.time()
        science_deadline = min(first+CAP, absolute)
        with (a.out/'EXPERIMENT_CLOCK.json').open('x') as stream:
            json.dump({'first_science_epoch': first, 'initial_science_deadline_epoch': science_deadline,
                       'experiment': 'E13a', 'pod_id': assignment['pod_id']}, stream)
        check = lambda: arm(science_deadline)
        timings = {}
        for name in READERS:
            timings[name] = []
            for start in (0, 32, 64):
                check(); torch.cuda.synchronize(); before = time.perf_counter()
                collect_unit(items, h, readers[name], name, policy, start, check)
                torch.cuda.synchronize(); timings[name].append(time.perf_counter()-before)
        budget = forecast(timings, math.ceil(len(items)/32), time.time()-first)
        science_deadline = min(science_deadline, first+budget['science_allocation_s'])
        budget.update(first_science_epoch=first, science_deadline_epoch=science_deadline,
                      fits_remaining_custody=time.time()+budget['fresh_pass_forecast_s'] <= science_deadline)
        P.dump(a.out/'FORECAST.json', budget)
        if not budget['fits'] or not budget['fits_remaining_custody']:
            P.dump(a.out/'STATUS.json', {'status': 'NO_FIT', 'full_pass_started': False, 'scope_reduced': False})
            return
        records = []
        with (a.out/'unasked.target.jsonl').open('x') as stream:
            for name in READERS:
                for r in R.collect_unasked(items, h, readers[name], 44, name, policy, 32, check,
                                            canonical_indices=list(range(len(items)))):
                    records.append(r)
                    stream.write(json.dumps(r, sort_keys=True, allow_nan=False)+'\n')
                    stream.flush()
            os.fsync(stream.fileno())
        check_grid(records, items); check()
        P.dump(a.out/'provenance.unasked.target.json', {'input_seal_sha256': manifest['input_seal_sha256'],
               'asked_score_seal_sha256': manifest['asked_score_seal_sha256'], 'capture_seal_sha256': manifest['capture_seal_sha256'],
               'batch': 32, 'decoding': policy, 'source_files': manifest['source_files'],
               'original_source_files': manifest['original_source_files'], 'manifest_sha256': P.sha(a.manifest),
               'assignment_sha256': P.sha(a.assignment), 'assets_sha256': P.sha(a.assets), 'expected_per_item_per_reader': 2,
               'judge_status': 'PENDING_BLINDED_JUDGE', 'execution': None,
               'free_batch_policy': 'canonical_batch_intersections', 'fresh_full_run': True,
               'old_partial_outputs_used': False, 'timing_outputs_used': False})
        P.dump(a.out/'STATUS.json', {'status': 'COMPLETE', 'records': len(records)})
        check()
        names = ('unasked.target.jsonl', 'provenance.unasked.target.json')
        P.dump(a.out/'FREE_SEAL.json', {'status': 'UNASKED_COMPLETE_BEFORE_LABEL_JOIN',
               'files': {n: P.sha(a.out/n) for n in names}})
    except Exception as exc:
        P.dump(a.out/'FAILURE.json', {'status': 'INCOMPLETE', 'error_type': type(exc).__name__,
               'reason': str(exc), 'no_automatic_retry': True})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if first is not None:
            P.dump(a.out/'SCIENCE_RECEIPT.json', {'first_science_epoch': first,
                   'completed_epoch': time.time(), 'elapsed_s': time.time()-first,
                   'science_deadline_epoch': science_deadline, 'own_cap_seconds': CAP})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('receipt', 'manifest', 'bank', 'capture', 'assignment', 'assets', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    with P.logged('e13a_fresh_free_target', gpu=True, extra={'cap_seconds': CAP}):
        run(args)
