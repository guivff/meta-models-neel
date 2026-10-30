"""E39 frozen preparation, budget admission, and integrity contracts (CPU only)."""
from __future__ import annotations

import hashlib
import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SEED = 20261026
ROWS = ('json_status', 'json_type', 'latex_environment', 'latex_role', 'latex_section', 'list_depth', 'list_index', 'prose_paren', 'prose_quote', 'prose_sentence', 'python_argument', 'python_comment', 'python_depth', 'python_indent', 'python_string', 'table_column', 'table_role', 'table_row')
STATES = ('json_type', 'latex_environment', 'prose_paren', 'prose_quote', 'python_comment', 'python_string', 'table_role')
STRUCTURE = ('json_type', 'latex_environment', 'latex_section', 'list_depth', 'list_index', 'prose_paren', 'prose_quote', 'prose_sentence', 'python_argument', 'python_comment', 'python_depth', 'python_indent', 'python_string', 'table_column', 'table_role', 'table_row')
SEMANTIC = ('json_status', 'latex_role')
CHECKPOINTS = (0, 25, 50, 100, 200, 400, 800)
RUNS = tuple((f, a) for f in ROWS for a in ('L', 'B', 'S'))
CAP = 81000
PROGRAMME_CUTOFF = datetime(2026, 10, 28, 22, 59, tzinfo=timezone.utc).timestamp()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(s) for s in Path(path).read_text().splitlines() if s.strip()]


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n')


def jsonl(path, records):
    Path(path).write_text(''.join(json.dumps(r, sort_keys=True, allow_nan=False) + '\n' for r in records))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def seal(directory, name='INPUT_SEAL.json', names=None):
    directory = Path(directory)
    names = names or sorted(p.name for p in directory.iterdir() if p.is_file() and p.name != name)
    dump(directory / name, {'files': {n: sha(directory / n) for n in names}})


def verify(directory, name='INPUT_SEAL.json'):
    directory = Path(directory)
    value = read(directory / name)
    for n, digest in value['files'].items():
        p = (directory / n).resolve()
        if not p.is_relative_to(directory.resolve()) or sha(p) != digest:
            raise ValueError('seal mismatch: ' + n)
    return value


def cache_output(path):
    path = Path(path).resolve()
    if 'cache' not in path.parts:
        raise ValueError('run inputs, activations, and outputs must live under cache/')
    path.mkdir(parents=True, exist_ok=False)
    return path


def plan():
    return read(HERE / 'PLAN.json')


def validate_plan(p):
    if (p['rows'] != list(ROWS) or p['runs'] != [list(x) for x in RUNS]
            or p['checkpoints'] != list(CHECKPOINTS) or p['seed'] != SEED
            or p['steps'] != 800 or p['batch_size'] != 8 or p['learning_rate'] != 1e-4
            or p['rank'] != 8 or p['total_gpu_seconds'] != CAP):
        raise ValueError('registered scope changed')
    return p


def worker_input(path):
    path = Path(path)
    value = verify(path)
    expected = set(value['files']) | {'INPUT_SEAL.json'}
    actual = {str(p.relative_to(path)) for p in path.rglob('*') if p.is_file()}
    if actual != expected or any('DO_NOT_STAGE' in x for x in actual):
        raise ValueError('worker input must contain only sealed files and no private test labels')
    provenance = read(path / 'provenance.json')
    from prepare_inputs import BANK_SEAL, CANDIDATES_HASH
    if (provenance.get('source_bank_seal') != BANK_SEAL
            or provenance.get('source_candidates_sha256') != CANDIDATES_HASH
            or provenance.get('stage_seal_sha256') != read(HERE/'PREPARATION.json')['stage_seal_sha256']
            or not provenance.get('source_capture_seals')):
        raise ValueError('input must bind verified E36 captures and frozen stage')
    if provenance['plan_sha256'] != sha(HERE / 'PLAN.json'):
        raise ValueError('input provenance references another plan')
    return value


def full_scope_still_fits(forecast_remaining_seconds, science_deadline, provider_deadline, now):
    return (math.isfinite(forecast_remaining_seconds) and forecast_remaining_seconds > 0
            and forecast_remaining_seconds <= min(science_deadline, provider_deadline - 180) - now)


def training_schedule(records, row, arm):
    """Same items/order and phrasing schedule in every arm; S permutes labels once."""
    part = [r for r in records if r['feature'] == row]
    if len(part) != 84 or any(set(r) != {'id', 'feature', 'y', 'cluster'} for r in part):
        raise ValueError('exact labelled dev row required')
    labels = [r['y'] for r in part]
    if arm == 'S':
        random.Random(SEED).shuffle(labels)
    rng = random.Random(SEED)
    schedule, deck = [], []
    for step in range(800):
        batch = []
        for j in range(8):
            if not deck:
                deck = list(range(84))
                rng.shuffle(deck)
            i = deck.pop()
            batch.append({'id': part[i]['id'], 'y': labels[i], 'phrasing': (step * 8 + j) % 2})
        schedule.append(batch)
    return schedule


def assignment(a, now=None):
    now = time.time() if now is None else now
    if a.get('issuer') != 'integrator' or a.get('experiment') != 'E39':
        raise ValueError('Integrator E39 assignment required')
    if a.get('plan_sha256') != sha(HERE / 'PLAN.json'):
        raise ValueError('plan mismatch')
    if a.get('pod_count') not in range(1, 7) or not 0 <= a.get('slot', -1) < a['pod_count']:
        raise ValueError('one to six assigned pods required')
    assigned = assigned_runs(a['slot'], a['pod_count'])
    if a.get('runs') != assigned:
        raise ValueError('fixed complete run assignment required')
    if not a.get('source_published') or not a.get('external_hardstop_verified'):
        raise ValueError('published source and external hardstop required')
    if a.get('target_mapping_sha256') != sha(HERE / 'LORA_TARGETS.json'):
        raise ValueError('coordinator target mapping bytes differ')
    allocated = a.get('allocated_gpu_seconds', 0)
    prior = read(HERE / 'PRIOR_ATTEMPT_ACCOUNTING_2026-10-26.json')['reserved_prior_gpu_seconds']
    if (type(allocated) not in (int, float) or not math.isfinite(allocated)
            or not 0 < allocated <= (CAP - prior) / a['pod_count'] or a.get('previous_gpu_seconds') != prior):
        raise ValueError('cumulative budget/no-retry contract violated')
    if any(type(a.get(k)) not in (int, float) or not math.isfinite(a[k])
           for k in ('deadline_epoch', 'provider_created_epoch')):
        raise ValueError('finite provider epoch/deadline required')
    if (a['deadline_epoch'] > min(a['provider_created_epoch'] + allocated, PROGRAMME_CUTOFF)
            or now >= a['deadline_epoch'] - 180 or a['provider_created_epoch'] > now):
        raise ValueError('invalid provider clock/deadline')
    return a


def admit(forecasts):
    """Full-grid admission only; no arm/row/checkpoint truncation."""
    if len(forecasts) not in range(1, 7):
        raise ValueError('all assigned pod forecasts required')
    seen, total, receipts = set(), 0.0, []
    prior = read(HERE / 'PRIOR_ATTEMPT_ACCOUNTING_2026-10-26.json')['reserved_prior_gpu_seconds']
    for f in forecasts:
        if f['pod_count'] != len(forecasts) or f['slot'] in seen:
            raise ValueError('forecast pod coverage mismatch')
        seen.add(f['slot'])
        if (f.get('previous_gpu_seconds') != prior
                or not 0 < f['allocated_gpu_seconds'] <= (CAP - prior) / len(forecasts)):
            raise ValueError('forecast allocation exceeds per-pod share')
        if f['plan_sha256'] != sha(HERE / 'PLAN.json') or f['status'] != 'WARMED_FORECAST':
            raise ValueError('real warmed forecast with exact plan required')
        seconds = f['forecast_remaining_seconds']
        if not math.isfinite(seconds) or seconds <= 0 or f['setup_elapsed_seconds'] > 2400:
            raise ValueError('invalid warmed time/setup overrun')
        elapsed_science = f['elapsed_science_seconds']
        if not math.isfinite(elapsed_science) or elapsed_science < 0:
            raise ValueError('nonresetting science clock required')
        science = min(1.5 * (seconds + elapsed_science) + 360, 10800)
        if (not math.isfinite(f['elapsed_provider_seconds'])
                or f['elapsed_provider_seconds'] < elapsed_science
                or f['elapsed_provider_seconds'] < f['setup_elapsed_seconds']
                or f['setup_elapsed_seconds'] < 0):
            raise ValueError('invalid provider/setup elapsed clock')
        remaining = f['allocated_gpu_seconds'] - f['elapsed_provider_seconds'] - 180
        fit = seconds + elapsed_science <= science and science - elapsed_science <= remaining
        total += f['allocated_gpu_seconds']
        receipts.append({'slot': f['slot'], 'fit': fit, 'science_seconds': science,
                         'forecast_sha256': f['forecast_sha256']})
    if seen != set(range(len(forecasts))) or prior + total > CAP:
        raise ValueError('aggregate cap/slot contract violated')
    return {'status': 'ADMIT_FULL_GRID' if all(x['fit'] for x in receipts) else 'NO_FIT_STOP',
            'plan_sha256': sha(HERE / 'PLAN.json'), 'pods': receipts, 'total_allocated_gpu_seconds': total,
            'previous_gpu_seconds': prior, 'total_experiment_reserved_gpu_seconds': prior + total}


def assigned_runs(slot, count):
    return [[row, arm] for i, row in enumerate(ROWS) if i % count == slot for arm in ('L', 'B', 'S')]


def prepare(bank, capture, out):
    from prepare_inputs import prepare
    return prepare(bank, capture, out)
