"""E35 fallback timing contract, dated 2026-10-25; no GPU or file side effects.

The worker independently verifies the prior-accounting receipt, the complete
20M-token cache/manifest and its exact chunk count. This clock validates their
assignment fields, forecasts every capture/update/gate operation and never
changes the registered token count, checkpoint selection, or evaluation sample.
Once-only claims belong to the worker and are not reset by this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import os
import re
import statistics
import time

TOTAL_GPU_SECONDS = 21600
MAX_STAGE_SECONDS = 10800
SETUP_MAX_SECONDS = 1500
RETRIEVAL_RESERVE = 180
SAVE_SEAL_RESERVE = 180
FORECAST_MARGIN = 360
MIN_LATER_RESERVE = 3600
ATTEMPT1_MIN_SECONDS = 434.2
RERUN_WORKER_MIN_SECONDS = 538.6674928665161
KNOWN_PRIOR_MIN_SECONDS = ATTEMPT1_MIN_SECONDS + RERUN_WORKER_MIN_SECONDS
CONSERVATIVE_RERUN_SECONDS = 3600
TRAINING_TOKENS = 20_000_000
CAPTURE_TOKENS = 512
OPTIMIZER_BATCH_TOKENS = 4096
OPTIMIZER_STEPS = math.ceil(TRAINING_TOKENS / OPTIMIZER_BATCH_TOKENS)
GATE_DOCUMENTS = 487
STOP = datetime(2026, 10, 28, 22, 59, tzinfo=timezone.utc).timestamp()
PILOT_KINDS = ('capture512', 'train4096', 'gate512')


class NoFit(TimeoutError):
    """Operational timing stop; never a failed scientific gate."""


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _digest(value, length=64):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{' + str(length) + '}', value) is not None


def verify_prior_accounting(assignment):
    """Require actual-provider accounting or the full conservative allocation.

    The known rerun worker elapsed time is only a lower bound, never proof of total
    provider usage. In actual mode the worker must separately verify the referenced
    Integrator accounting receipt; conservative mode books at least all 3600 s.
    """
    previous = assignment.get('previous_gpu_seconds')
    record = assignment.get('prior_accounting')
    if not _finite_number(previous) or previous < KNOWN_PRIOR_MIN_SECONDS or not isinstance(record, dict):
        raise ValueError('complete prior provider accounting and known elapsed lower bound required')
    first, rerun = record.get('attempt1_gpu_seconds'), record.get('rerun_gpu_seconds')
    if (not _finite_number(first) or first < ATTEMPT1_MIN_SECONDS
            or not _finite_number(rerun) or rerun < RERUN_WORKER_MIN_SECONDS
            or not _digest(record.get('receipt_sha256'))):
        raise ValueError('finite prior charges and SHA-bound accounting receipt required')
    mode = record.get('rerun_mode')
    if mode not in ('provider_actual', 'conservative_allocation'):
        raise ValueError('explicit provider-actual or conservative-allocation accounting required')
    if mode == 'conservative_allocation' and rerun < CONSERVATIVE_RERUN_SECONDS:
        raise ValueError('conservative accounting must book the full rerun allocation')
    if previous < first + rerun:
        raise ValueError('previous_gpu_seconds understates the booked prior attempts')


class TrainingClock:
    def __init__(self, assignment, request_sha, now=None):
        now = time.time() if now is None else now
        if not isinstance(assignment, dict) or not _finite_number(now):
            raise ValueError('assignment and finite current time required')
        if (assignment.get('issuer') != 'integrator' or assignment.get('experiment') != 'E35'
                or assignment.get('stage') != 'training' or type(assignment.get('gpu_count')) is not int
                or assignment['gpu_count'] != 1 or not isinstance(assignment.get('pod_id'), str)
                or not assignment['pod_id'] or not _digest(request_sha)
                or assignment.get('request_sha256') != request_sha):
            raise ValueError('exact single-GPU Integrator training assignment required')
        if os.environ.get('RUNPOD_POD_ID') != assignment['pod_id']:
            raise ValueError('assignment does not belong to this RunPod pod')
        if not _digest(assignment.get('source_commit'), 40):
            raise ValueError('exact source commit required')
        for key in ('source_pushed', 'external_hardstop_verified', 'hold_renewer_verified'):
            if assignment.get(key) is not True:
                raise ValueError('Integrator push, external hardstop and hold evidence required')
        for key in ('previous_gpu_seconds', 'allocated_gpu_seconds', 'provider_created_epoch',
                    'deadline_epoch', 'setup_deadline_epoch', 'later_reserved_gpu_seconds'):
            if not _finite_number(assignment.get(key)):
                raise ValueError('finite assignment timing fields required')
        verify_prior_accounting(assignment)
        prior, allocation = assignment['previous_gpu_seconds'], assignment['allocated_gpu_seconds']
        later = assignment['later_reserved_gpu_seconds']
        start, deadline = assignment['provider_created_epoch'], assignment['deadline_epoch']
        setup = assignment['setup_deadline_epoch']
        if (not RETRIEVAL_RESERVE < allocation <= MAX_STAGE_SECONDS or later < MIN_LATER_RESERVE
                or prior + allocation + later > TOTAL_GPU_SECONDS):
            raise ValueError('training allocation, later reserve or total E35 budget exceeded')
        if not start <= now < setup <= min(start + SETUP_MAX_SECONDS, deadline - RETRIEVAL_RESERVE):
            raise ValueError('setup deadline expired or outside the provider allocation')
        if not setup < deadline <= min(STOP, start + allocation):
            raise ValueError('absolute/provider/programme deadline invalid')
        # Snapshot the validated values so a later caller cannot extend the clock
        # by mutating its original assignment dictionary.
        self.a = dict(assignment, prior_accounting=dict(assignment['prior_accounting']))
        self.science_start = None
        self.science_limit = None
        self.forecast = None
        self.forecast_components = None
        self.pilot_seconds = {name: [] for name in PILOT_KINDS}
        self.status = 'SETUP'

    def check(self):
        if self.status == 'NO_FIT':
            raise NoFit('timing stop is terminal for this clock')
        now = time.time()
        limit = self.a['deadline_epoch'] - RETRIEVAL_RESERVE
        if self.science_start is None:
            limit = min(limit, self.a['setup_deadline_epoch'])
        elif self.science_limit is not None:
            limit = min(limit, self.science_start + self.science_limit)
        if now >= limit:
            self.status = 'NO_FIT'
            raise NoFit('training clock exhausted; registered scope unchanged')

    def begin_science(self):
        """Call before warmed pilots; no reset across training and gate phases."""
        self.check()
        if self.science_start is not None:
            raise ValueError('science clock cannot reset')
        self.science_start = time.time()
        self.status = 'PILOT'

    def record_pilot(self, kind, seconds):
        """Three serial warmed timings per kind; actual SAE updates are untouched.

        capture512: first three full training-cache chunks, all capture/buffer overhead.
        train4096: three full frozen-size scratch optimizer updates, then discarded.
        gate512: the same three fixed training pilot docs, capture plus scratch SAE eval.
        Synchronize CUDA before ending each externally measured interval. No loss or
        held-out score is a timing input.
        """
        self.check()
        if self.science_start is None or self.status != 'PILOT' or kind not in PILOT_KINDS:
            raise ValueError('pilot timing must belong to the single science pilot phase')
        if not _finite_number(seconds) or seconds <= 0 or len(self.pilot_seconds[kind]) >= 3:
            raise ValueError('exactly three positive finite warmed timings per kind required')
        self.pilot_seconds[kind].append(float(seconds))

    def admit(self, training_chunks, optimizer_steps=OPTIMIZER_STEPS, gate_documents=GATE_DOCUMENTS):
        """Admit the full manifest count, every optimizer step and unchanged gate.

        Each nonoverlapping within-document training chunk contains 1..512 real tokens.
        The caller verifies their sum is exactly 20M, retaining every short tail.
        Counting chunks rather than dividing 20M by 512 includes tail-forward
        overhead. Each full 4096-token optimizer timing bounds the final short
        update. No partial admission.
        """
        self.check()
        if self.science_start is None or self.status != 'PILOT' or self.forecast is not None:
            raise ValueError('one admission after the single warmed pilot phase required')
        if (type(training_chunks) is not int
                or not math.ceil(TRAINING_TOKENS / CAPTURE_TOKENS) <= training_chunks <= TRAINING_TOKENS
                or type(optimizer_steps) is not int or optimizer_steps != OPTIMIZER_STEPS
                or type(gate_documents) is not int or gate_documents != GATE_DOCUMENTS):
            raise ValueError('complete 20M cache chunk count, 4883 updates and 487 gate documents required')
        if any(len(v) != 3 or any(not _finite_number(t) or t <= 0 for t in v)
               for v in self.pilot_seconds.values()):
            raise ValueError('all nine complete warmed timings required')
        # Sequential pilot durations cannot be less than their measured sum.
        # Taking the maximum is conservative if timer resolution differs.
        elapsed = max(time.time() - self.science_start,
                      sum(sum(values) for values in self.pilot_seconds.values()))
        components = {
            'pilot_elapsed_seconds': elapsed,
            'training_capture_seconds': training_chunks * statistics.median(self.pilot_seconds['capture512']),
            'optimizer_seconds': optimizer_steps * statistics.median(self.pilot_seconds['train4096']),
            'gate_seconds': gate_documents * statistics.median(self.pilot_seconds['gate512']),
            'training_chunks': training_chunks,
            'optimizer_steps': optimizer_steps,
            'gate_documents': gate_documents,
            'training_tokens': TRAINING_TOKENS,
        }
        self.forecast = sum(components[name] for name in
                            ('pilot_elapsed_seconds', 'training_capture_seconds', 'optimizer_seconds', 'gate_seconds'))
        if not math.isfinite(self.forecast):
            raise ValueError('nonfinite whole-stage forecast')
        self.forecast_components = components
        self.science_limit = min(1.5 * self.forecast + FORECAST_MARGIN,
                                 self.a['deadline_epoch'] - RETRIEVAL_RESERVE - self.science_start)
        if self.forecast + SAVE_SEAL_RESERVE > self.science_limit:
            self.status = 'NO_FIT'
            raise NoFit('full 20M training and registered gate do not fit; no scope reduction')
        self.status = 'RUNNING'

    def record(self):
        return {
            'status': self.status,
            'first_science_epoch': self.science_start,
            'science_cap_seconds': self.science_limit,
            'forecast_seconds': self.forecast,
            'forecast_components': None if self.forecast_components is None else dict(self.forecast_components),
            'pilot_seconds': {kind: list(values) for kind, values in self.pilot_seconds.items()},
            'provider_elapsed_seconds': max(0., time.time() - self.a['provider_created_epoch']),
            'allocated_gpu_seconds': self.a['allocated_gpu_seconds'],
            'previous_gpu_seconds': self.a['previous_gpu_seconds'],
            'later_reserved_gpu_seconds': self.a['later_reserved_gpu_seconds'],
            'prior_accounting': dict(self.a['prior_accounting']),
            'science_clock_resets': 0,
            'retrieval_reserve_seconds': RETRIEVAL_RESERVE,
            'save_seal_reserve_seconds': SAVE_SEAL_RESERVE,
            'training_tokens': TRAINING_TOKENS,
        }
