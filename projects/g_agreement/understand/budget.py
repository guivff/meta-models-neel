"""Fail-closed, cumulative E3/E4 setup/science accounting. No pod operations.

The integrator supplies one assignment and an external hard stop. Calibration
and capture are separate processes, sharing a locked state directory. Warm-up
and timing forwards count as science; loading/asset verification count as setup.
An interrupted phase cannot be retried by deleting/overwriting its receipt.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import math
from pathlib import Path
import signal
import statistics
import time

from projects.g_agreement.blindspot import protocol as P

CAP_SECONDS = 2160.0
SETUP_SECONDS = 1500.0
PHASES = {'E3': ('olens', 'nla', 'jlens'), 'E4': ('olens', 'nla', 'jlens', 'target')}
ROOT = Path(__file__).resolve().parents[3]


def source_hashes():
    paths = [p for p in (ROOT/'projects/g_agreement/understand').rglob('*')
             if p.is_file() and p.suffix in ('.py', '.sh', '.md')]
    paths += [ROOT/'common/__init__.py', ROOT/'projects/g_agreement/BRIEF_UNDERSTAND.md',
              ROOT/'projects/g_agreement/manifest/assets.json']
    paths += list((ROOT/'projects/g_agreement/blindspot').glob('*.py'))
    paths += list((ROOT/'external/mats-nla-workspace/src/mats').rglob('*.py'))
    return {str(p.relative_to(ROOT)): P.sha(p) for p in sorted(set(paths))}


def forecast(timings, units):
    if len(timings) != 3 or any(not math.isfinite(t) or t <= 0 for t in timings):
        raise ValueError('exactly three positive, finite warmed timings required')
    if type(units) is not int or units < 1:
        raise ValueError('positive integer number of production units required')
    return statistics.median(timings)*units


def admit_forecast(receipts, phases, consumed):
    if set(receipts) != set(phases):
        raise ValueError('all reader/target warmed receipts required before capture')
    total = 0.0
    for phase in phases:
        r = receipts[phase]
        if r['warmups'] != 1:
            raise ValueError('one unscored warm-up required')
        f = forecast(r['timings_seconds'], r['units'])
        if not math.isclose(f, r['forecast_seconds'], abs_tol=1e-7):
            raise ValueError('forecast does not match timed units')
        total += f
    cap = min(1.5*total+360, CAP_SECONDS)
    return {'forecast_seconds': total, 'science_cap_seconds': cap,
            'science_consumed_seconds': consumed,
            'admitted': consumed+total <= cap}


def _utc_seconds(s):
    dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timezone-aware hard deadline required')
    return dt.timestamp()


class Ledger:
    def __init__(self, assignment, state_dir, experiment, input_seals):
        self.assignment_path = Path(assignment)
        self.assignment = json.loads(self.assignment_path.read_text())
        a = self.assignment
        if (experiment not in PHASES or a.get('experiment') != experiment
                or a.get('gpu_count') != 1 or not a.get('pod_id')
                or a.get('external_hard_stop_verified') is not True
                or a.get('setup_allowance_seconds') != SETUP_SECONDS
                or a.get('max_science_seconds') != CAP_SECONDS
                or a.get('source_files') != source_hashes()
                or a.get('input_seals') != input_seals):
            raise ValueError('integrator assignment is missing/mismatched')
        self.deadline = _utc_seconds(a['hard_deadline_utc'])
        if self.deadline <= time.time():
            raise ValueError('integrator hard deadline expired')
        self.experiment = experiment
        self.root = Path(state_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = (self.root/'ledger.lock').open('a+')
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.path = self.root/'ledger.json'
        digest = P.sha(self.assignment_path)
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
            if self.state['assignment_sha256'] != digest or self.state.get('active'):
                raise ValueError('changed assignment or interrupted phase; integrator reconciliation required')
        else:
            self.state = {'assignment_sha256': digest, 'experiment': experiment,
                          'setup_seconds': 0.0, 'science_seconds': 0.0,
                          'phases': {}, 'active': None}
            self.save()

    def save(self):
        tmp = self.path.with_suffix('.tmp')
        P.dump(tmp, self.state)
        tmp.replace(self.path)

    def remaining(self, kind):
        cap = SETUP_SECONDS if kind == 'setup' else self.state.get('gate', {}).get('science_cap_seconds', CAP_SECONDS)
        return min(cap-self.state[kind+'_seconds'], self.deadline-time.time())

    @contextmanager
    def charge(self, phase, kind):
        remaining = self.remaining(kind)
        if remaining <= 0:
            raise TimeoutError(kind+' allowance exhausted')
        self.state['active'] = {'phase': phase, 'kind': kind, 'start_utc': datetime.now(timezone.utc).isoformat()}
        self.save()
        start = time.monotonic()
        previous = signal.getsignal(signal.SIGALRM)
        def expired(*_):
            raise TimeoutError(kind+' cap / external deadline reached')
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, remaining)
        try:
            yield
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)
            self.state[kind+'_seconds'] += time.monotonic()-start
            self.state['active'] = None
            self.save()

    def check(self):
        if self.remaining('science') <= 0:
            raise TimeoutError('science cap reached')

    def gate(self):
        receipts = {k: v['calibration'] for k, v in self.state['phases'].items() if 'calibration' in v}
        gate = admit_forecast(receipts, PHASES[self.experiment], self.state['science_seconds'])
        self.state['gate'] = gate
        self.save()
        if not gate['admitted']:
            raise RuntimeError('NO-GO: warmed full forecast plus used science exceeds cap')
        return gate

    def close(self):
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()
