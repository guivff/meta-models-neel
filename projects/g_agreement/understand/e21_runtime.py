"""E21's four-path dev pilot, one science clock, and bounded admission gate."""
import math
import os
import statistics
import time
from datetime import datetime, timezone

from .cpu import ROOT, read, dump, sha

BRIEF = 'results/g_agreement/understand/e21/BRIEF_UNDERSTAND.6a2b114e.md'
PLAN = 'results/g_agreement/understand/e21/PLAN.json'
PATHS = ('dev_real', 'description', 'exhibit_e15', 'exhibit_real')
FORECAST_METHOD = 'all_four_paths_dev_warmed_median3_before_test'
STOP = datetime(2026, 10, 28, 22, 59, tzinfo=timezone.utc).timestamp()
RETRIEVAL_SECONDS = 180
REQUIRED_SOURCE = {
    'projects/g_agreement/understand/' + name + '.py'
    for name in ('e21', 'e21_worker', 'e21_runtime', 'e21_analyse', 'cpu')
}
REQUIRED_SOURCE |= {'projects/g_agreement/w_claims/ar.py',
                    'projects/g_agreement/blindspot/ar_tests.py',
                    'projects/g_agreement/blindspot/run.py',
                    'projects/g_agreement/manifest/assets.json',
                    'external/mats-nla-workspace/src/mats/probes.py',
                    'external/mats-nla-workspace/src/mats/metrics.py'}


class NoFit(TimeoutError):
    pass


def _repo_file(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('source/authority path must remain inside the repository')
    return path


class Gate:
    """Warm-up is setup; every timed dev call and every production call is science.

    All twelve timed dev calls are discarded from scientific outputs. Their
    measured duration is included once in F, alongside the projected production
    work. No retained output may be retained before all four paths are measured.
    """

    def __init__(self, path, counts):
        a = read(path)
        self.assignment = a
        self.assignment_sha256 = sha(path)
        self.counts = dict(counts)
        self.started = None
        self.first_science_epoch = None
        self.samples = {k: [] for k in PATHS}
        self.completed = {k: 0 for k in PATHS}
        self.warmups = {}
        self.discarded_timing_seconds = 0.
        self.cap = None
        self.admitted = False
        self.status = 'SETUP'
        if set(counts) != set(PATHS) or any(type(n) is not int or n < 3 for n in counts.values()):
            raise ValueError('all four frozen timing paths with at least three production units required')
        if a.get('issuer') != 'integrator' or a.get('experiment') != 'E21' or a.get('gpu_count') != 1 or not a.get('pod_id'):
            raise ValueError('exact integrator one-pod E21 assignment required')
        for key in ('brief_registered', 'brief_pushed', 'external_hardstop_verified', 'hold_renewer_verified'):
            if a.get(key) is not True:
                raise ValueError(key + ' evidence required')
        if a.get('brief_sha256') != sha(ROOT / BRIEF):
            raise ValueError('authority brief mismatch')
        if a.get('plan_sha256') != sha(ROOT / PLAN):
            raise ValueError('frozen E21 plan mismatch')
        plan = read(ROOT / PLAN)
        if plan.get('authority_commit') != '6a2b114e' or plan.get('primary_measure') != 'raw_cosine_true_minus_opposite':
            raise ValueError('exact §113 clarified primary measure required')
        sources = a.get('source_files', {})
        if not REQUIRED_SOURCE <= set(sources):
            raise ValueError('complete source pins required')
        for filename, digest in sources.items():
            if sha(_repo_file(filename)) != digest:
                raise ValueError('source pin mismatch')
        for key in ('allocated_gpu_seconds', 'previous_gpu_seconds', 'provider_created_epoch',
                    'setup_deadline_epoch', 'deadline_epoch', 'setup_allowance_seconds'):
            if type(a.get(key)) not in (int, float) or not math.isfinite(a[key]):
                raise ValueError('finite timing fields required')
        self.reserved = float(a['allocated_gpu_seconds'])
        if not RETRIEVAL_SECONDS < self.reserved <= 2400 or a['previous_gpu_seconds'] != 0:
            raise ValueError('fresh E21 science cap <=2400 required')
        if not 0 < a['setup_allowance_seconds'] <= 1500 or a['provider_created_epoch'] > time.time():
            raise ValueError('setup/provider invalid: E21 setup must be <=1500 seconds')
        if not a['provider_created_epoch'] < a['setup_deadline_epoch'] <= a['provider_created_epoch'] + a['setup_allowance_seconds']:
            raise ValueError('setup deadline must fit the 1500-second allowance')
        if not a['setup_deadline_epoch'] < a['deadline_epoch'] <= min(
                STOP, a['provider_created_epoch'] + a['setup_allowance_seconds'] + self.reserved):
            raise ValueError('absolute/programme deadline exceeded')
        if a.get('forecast_method') != FORECAST_METHOD:
            raise ValueError('full four-path warmed forecast required')
        self.setup_guard()
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', WANDB_MODE='disabled')

    def setup_guard(self):
        if self.started is not None:
            return self.guard()
        if time.time() >= min(self.assignment['setup_deadline_epoch'],
                              self.assignment['deadline_epoch'] - RETRIEVAL_SECONDS,
                              STOP - RETRIEVAL_SECONDS):
            raise TimeoutError('setup/absolute deadline reached')

    def start(self):
        if self.started is None:
            self.setup_guard()
            if set(self.warmups) != set(PATHS):
                raise ValueError('every path needs one unscored dev warm-up')
            self.started = time.monotonic()
            self.first_science_epoch = time.time()
            self.status = 'RUNNING'
        self.write_state()
        self.guard()

    def elapsed(self):
        return 0. if self.started is None else time.monotonic() - self.started

    def forecast(self):
        paths = {}
        for key in PATHS:
            median = statistics.median(self.samples[key]) if len(self.samples[key]) == 3 else None
            paths[key] = {
                'units': self.counts[key], 'completed_units': self.completed[key],
                'timed_unit_seconds': list(self.samples[key]), 'timing_source_split': 'dev',
                'median_seconds': median, 'warmup': self.warmups.get(key),
                'forecast_seconds': None if median is None else median * self.counts[key],
            }
        full = all(v['median_seconds'] is not None for v in paths.values())
        F = sum(v['forecast_seconds'] for v in paths.values()) + self.discarded_timing_seconds if full else None
        cap = min(self.reserved, 1.5 * F + 360, 2400) if full else None
        return {
            'paths': paths, 'all_paths_measured': full, 'F_seconds': F,
            'formula_cap_seconds': cap,
            'science_cap_seconds': self.cap if self.cap is not None else self.reserved,
            'reserved_pilot_only': self.cap is None, 'bulk_admitted': self.admitted,
            'status': self.status, 'first_science_epoch': self.first_science_epoch,
            'elapsed_science_seconds': self.elapsed(), 'science_clock_resets': 0,
            'discarded_dev_timing_science_seconds': self.discarded_timing_seconds,
            'retrieval_reserve_seconds': RETRIEVAL_SECONDS, 'unknown_paths_are_zero': False,
        }

    def write_state(self):
        if not hasattr(self, 'out'):
            return
        tmp = self.out / 'CLOCK.tmp'
        dump(tmp, self.forecast())
        os.replace(tmp, self.out / 'CLOCK.json')

    def guard(self):
        if self.started is None:
            return self.setup_guard()
        limit = self.reserved if self.cap is None else self.cap
        if self.elapsed() >= limit - RETRIEVAL_SECONDS or time.time() >= min(
                STOP, self.assignment['deadline_epoch']) - RETRIEVAL_SECONDS:
            raise TimeoutError('science/retrieval deadline reached')

    def warm(self, key, seconds):
        self.setup_guard()
        if (self.started is not None or key not in PATHS or key in self.warmups
                or not math.isfinite(seconds) or seconds <= 0):
            raise ValueError('one finite setup warm-up per path required')
        self.warmups[key] = {'seconds': seconds, 'scored': False, 'source_split': 'dev'}
        self.write_state()

    def record(self, key, seconds, retained=True):
        if self.started is None:
            raise ValueError('timed calls must begin inside the science clock')
        if key not in PATHS or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError('known path and positive finite unit timing required')
        if not self.admitted:
            if retained:
                raise ValueError('retained output forbidden before the full four-path forecast')
            if len(self.samples[key]) >= 3:
                raise ValueError('exactly three timed dev units per path before admission')
            self.samples[key].append(seconds)
            self.discarded_timing_seconds += seconds
        else:
            if not retained:
                raise ValueError('discarded timing calls forbidden after admission')
            if self.completed[key] >= self.counts[key]:
                raise ValueError('production path already complete')
            self.completed[key] += 1
        self.write_state()
        self.guard()

    def admit(self):
        if self.started is None:
            raise ValueError('science clock must start before admission')
        if self.admitted or self.status == 'NO_FIT':
            raise ValueError('admission may be attempted only once')
        report = self.forecast()
        if not report['all_paths_measured']:
            raise ValueError('all four paths need three warmed dev timings before admission')
        self.cap = report['formula_cap_seconds']
        remaining = sum(v['median_seconds'] * (v['units'] - v['completed_units'])
                        for v in report['paths'].values())
        report.update(science_cap_seconds=self.cap, reserved_pilot_only=False,
                      remaining_forecast_seconds=remaining,
                      fit=self.elapsed() + remaining + RETRIEVAL_SECONDS <= self.cap)
        dump(self.out / 'FULL_WARMED_FORECAST.json', report)
        dump(self.out / 'FORECAST_SEAL.json', {
            'status': 'E21_FULL_FIVE_PATH_FORECAST_BEFORE_TEST',
            'files': {'FULL_WARMED_FORECAST.json': sha(self.out / 'FULL_WARMED_FORECAST.json')},
        })
        if not report['fit']:
            self.status = 'NO_FIT'
            self.write_state()
            raise NoFit('NO_FIT: full E21 forecast exceeds min(1.5F+360,2400) and retrieval reserve')
        self.guard()
        self.admitted = True
        self.write_state()
