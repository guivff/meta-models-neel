"""Continuous, separate E3/E4 clocks inside one integrator-owned GPU pack.

The single setup allowance ends before E3 starts. Each science clock then runs
without pauses from its first step through its score seal, including warm-ups,
timing, CPU work, GPU transfers, collection and sealing. A failed experiment may
be sealed on CPU after its timer is disarmed; that latency remains charged to
the same experiment and any cap overrun is retained explicitly.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import math
from pathlib import Path
import signal
import time

from projects.g_agreement.blindspot import protocol as P
from .budget import CAP_SECONDS, SETUP_SECONDS, PHASES, _utc_seconds, admit_forecast, source_hashes

SEQUENCE = ('E3', 'E4')


def _now():
    return datetime.now(timezone.utc).isoformat()


class PackedBudget:
    """One process, one attempt, two clocks; no pod operations or GPU resume."""

    sequence = SEQUENCE
    experiment_name = 'E3_E4_PACK'

    def __init__(self, assignment_path, outroot, input_seals):
        self.assignment_path = Path(assignment_path)
        self.assignment = json.loads(self.assignment_path.read_text())
        a = self.assignment
        if (a.get('experiment') != self.experiment_name or a.get('sequence') != list(self.sequence)
                or a.get('gpu_count') != 1 or not a.get('pod_id')
                or a.get('external_hard_stop_verified') is not True
                or a.get('max_science_seconds') != {e: CAP_SECONDS for e in self.sequence}
                or a.get('setup_allowance_seconds') != SETUP_SECONDS
                or a.get('source_files') != source_hashes()
                or a.get('input_seals') != input_seals
                or set(input_seals) != set(self.sequence)
                or ('E3' in self.sequence and set(input_seals['E3']) != {'primary'})
                or set(input_seals['E4']) != {'primary', 'e9'}):
            raise ValueError('packed integrator assignment is missing/mismatched')
        self.deadline = _utc_seconds(a['hard_deadline_utc'])
        if self.deadline <= time.time():
            raise ValueError('packed hard deadline expired')
        self.root = Path(outroot)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root/'packed_budget.json'
        self.lock = (self.root/'packed_budget.lock').open('a+')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if self.path.exists():
                raise ValueError('packed allocation already attempted; no restart or clock reset')
        except BaseException:
            self.lock.close()
            raise
        self.state = {'schema': 'understand-packed-budget-v1',
                      'assignment_sha256': P.sha(self.assignment_path),
                      'sequence': list(self.sequence), 'setup_seconds': 0.,
                      'setup_active': False, 'experiments': {}, 'active': None}
        self._start = None
        self._setup_start = None
        self._previous_handler = signal.getsignal(signal.SIGALRM)
        self._closed = False
        self.save()

    def save(self):
        temporary = self.path.with_suffix('.tmp')
        P.dump(temporary, self.state)
        temporary.replace(self.path)

    def _disarm(self):
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, self._previous_handler)

    def _arm(self, seconds):
        if seconds <= 0:
            raise TimeoutError('packed allowance or external deadline exhausted')
        def expired(*_):
            raise TimeoutError('packed continuous clock or external hard deadline reached')
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, seconds)

    @contextmanager
    def setup(self):
        if self.state['experiments'] or self.state['active'] or self.state['setup_active']:
            raise ValueError('shared setup is allowed only before the first experiment')
        remaining = min(SETUP_SECONDS-self.state['setup_seconds'], self.deadline-time.time())
        self._arm(remaining)
        self._setup_start = time.monotonic()
        self.state['setup_active'] = True
        self.save()
        try:
            yield
        finally:
            self._disarm()
            self.state['setup_seconds'] += time.monotonic()-self._setup_start
            self.state['setup_active'] = False
            self.state['setup_budget_status'] = ('WITHIN_CAP' if self.state['setup_seconds'] <= SETUP_SECONDS else 'CAP_EXCEEDED')
            self._setup_start = None
            self.save()

    def start(self, experiment):
        if experiment not in self.sequence or self.state['active'] or self.state['setup_active']:
            raise ValueError('invalid packed experiment start or overlapping clock')
        if experiment in self.state['experiments']:
            raise ValueError('experiment already attempted; science clock cannot restart')
        if self.state['setup_seconds'] > SETUP_SECONDS:
            raise TimeoutError('shared setup allowance exceeded')
        if experiment == 'E4' and 'E3' in self.sequence:
            previous = self.state['experiments'].get('E3')
            if previous is None or previous.get('sealed') is not True:
                raise ValueError('E3 must be sealed, including partial sealing, before E4 starts')
        elif self.state['experiments']:
            raise ValueError('E3 must be first')
        self._start = time.monotonic()
        self.state['active'] = experiment
        self.state['experiments'][experiment] = {
            'start_utc': _now(), 'status': 'RUNNING', 'sealed': False,
            'science_cap_seconds': CAP_SECONDS, 'science_seconds': 0.,
            'gpu_stopped': False, 'clock_policy': 'continuous first step through final score seal'}
        self.save()
        self._arm(self.remaining())

    def elapsed(self, experiment=None):
        experiment = experiment or self.state['active']
        if experiment is None or experiment not in self.state['experiments']:
            raise ValueError('experiment has not started')
        if self.state['active'] == experiment:
            return time.monotonic()-self._start
        return self.state['experiments'][experiment]['science_seconds']

    def remaining(self):
        experiment = self.state['active']
        if experiment is None:
            raise ValueError('no active science clock')
        cap = self.state['experiments'][experiment]['science_cap_seconds']
        return min(cap-self.elapsed(), self.deadline-time.time())

    def checkpoint(self):
        experiment = self.state['active']
        if experiment is None:
            raise ValueError('no active science clock')
        if self.state['experiments'][experiment]['gpu_stopped']:
            raise RuntimeError('experiment stopped; CPU partial sealing only, no GPU resumption')
        if self.remaining() <= 0:
            raise TimeoutError('packed continuous science cap exhausted')

    def gate(self, experiment, receipts, remaining_transition_seconds=0.):
        if self.state['active'] != experiment:
            raise ValueError('gate requires matching active experiment')
        self.checkpoint()
        record = self.state['experiments'][experiment]
        if 'gate' in record:
            raise ValueError('warmed gate already evaluated; cannot revise after scoring')
        if not math.isfinite(remaining_transition_seconds) or remaining_transition_seconds < 0:
            raise ValueError('remaining transition forecast must be finite and nonnegative')
        used = self.elapsed()
        checked = admit_forecast(receipts, PHASES[experiment], used)
        full = checked['forecast_seconds']+remaining_transition_seconds
        cap = min(1.5*full+360., CAP_SECONDS)
        result = {'warmed_forward_forecast_seconds': checked['forecast_seconds'],
                  'remaining_transition_forecast_seconds': remaining_transition_seconds,
                  'forecast_seconds': full, 'science_cap_seconds': cap,
                  'science_consumed_seconds': used, 'admitted': used+full <= cap}
        record['calibration'] = receipts
        record['gate'] = result
        record['science_cap_seconds'] = cap
        self.save()
        if not result['admitted']:
            self.stop(experiment, 'NO_GO_WARMED_FORECAST')
            raise RuntimeError('NO-GO: elapsed science plus full warmed/transfer forecast exceeds cap')
        # Anchored to the original first-step clock, never to gate completion.
        self._arm(self.remaining())
        return result

    def stop(self, experiment, reason):
        """Forbid further GPU calls; retain the running clock until CPU seal."""
        if self.state['active'] != experiment:
            raise ValueError('stop requires matching active experiment')
        self._disarm()
        record = self.state['experiments'][experiment]
        if not record['gpu_stopped']:
            record.update(gpu_stopped=True, stopped_utc=_now(), stop_reason=str(reason),
                          science_seconds_at_gpu_stop=self.elapsed())
        self.save()

    def finish(self, experiment, status, sealed=False):
        """Close a clock only after its complete or partial score seal exists."""
        if self.state['active'] != experiment:
            raise ValueError('finish requires matching active experiment')
        if sealed is not True:
            raise ValueError('finish requires a complete or partial score seal')
        if status not in {'COMPLETE', 'PARTIAL', 'FAILED'}:
            raise ValueError('unexpected final experiment status')
        record = self.state['experiments'][experiment]
        if status == 'COMPLETE' and (not record.get('gate', {}).get('admitted') or record['gpu_stopped']):
            raise ValueError('complete result requires admitted gate and uninterrupted GPU execution')
        elapsed = self.elapsed()
        self._disarm()
        record.update(status=status, sealed=True, end_utc=_now(), science_seconds=elapsed,
                      budget_status='WITHIN_CAP' if elapsed <= record['science_cap_seconds'] else 'CAP_EXCEEDED',
                      cap_overrun_seconds=max(0., elapsed-record['science_cap_seconds']))
        if record['gpu_stopped']:
            record['post_stop_cpu_sealing_seconds'] = elapsed-record['science_seconds_at_gpu_stop']
        self.state['active'] = None
        self._start = None
        self.save()
        return record

    def mark_sealed(self, experiment, partial=True):
        return self.finish(experiment, 'PARTIAL' if partial else 'COMPLETE', sealed=True)

    def close(self):
        if self._closed:
            return
        self._disarm()
        if self.state['active']:
            record = self.state['experiments'][self.state['active']]
            record['science_seconds_on_close'] = self.elapsed()
            record['status'] = 'INTERRUPTED_UNSEALED'
            self.save()
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()
        self._closed = True


class E4OnlyBudget(PackedBudget):
    """The single §91-authorized retry, same continuous clock and caps."""
    sequence = ('E4',)
    experiment_name = 'E4_ONLY_RETRY'
