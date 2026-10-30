"""E96 answer-blind aggregation, frozen before any E96 sample.

Inputs are in sample-index order (0..15). No function accepts a true answer.
Each resolved sample supplies all explicitly stated canonical values: () is
confirmed silence, a singleton casts one vote, multiple values are ambiguous
and cast no majority vote. Unresolved judgment is never encoded as silence.
Ties use the bank's frozen canonical value order, never the true label.

Reconstructor selection minimizes float64 raw native-coordinate MSE (block44
Oracle, block42 NLA), with no normalization/whitening/projection. Ties select
the earliest sample index. A malformed/unclosed sample is ineligible; failure
to reconstruct a valid sample is an error, never a missing-head declaration.

Any-of-16 returns the set of values stated unambiguously by at least one sample,
for descriptive answer-aware scoring downstream. It never selects a preferred
value. Its matched 1-of-16 placebo uses an index frozen before judging; the
placebo is not expanded to sixteen opportunities.
"""
from collections import Counter
import math

N_SAMPLES = 16
MIN_VOTES = 6
ERROR_METRIC = 'float64_raw_native_mse'


def _values(values):
    values = tuple(values)
    if len(values) < 2 or any(not isinstance(v, str) or not v for v in values) or len(set(values)) != len(values):
        raise ValueError('distinct nonempty canonical values in frozen bank order required')
    return values


def _samples(statements, values):
    values = _values(values)
    if len(statements) != N_SAMPLES:
        raise ValueError('exactly 16 resolved samples required')
    rows = []
    for stated in statements:
        if stated is None or isinstance(stated, (str, bytes)):
            raise ValueError('explicit value list required; None means unresolved, not silent')
        row = tuple(stated)
        if any(not isinstance(v, str) or v not in values for v in row) or len(set(row)) != len(row):
            raise ValueError('unknown or repeated stated value')
        rows.append(row)
    return rows, values


def majority(statements, values):
    rows, values = _samples(statements, values)
    counts = Counter(row[0] for row in rows if len(row) == 1)
    winner = max(values, key=lambda v: counts[v])  # stable frozen bank order
    return {'value': winner if counts[winner] >= MIN_VOTES else None,
            'votes': {v: counts[v] for v in values},
            'silent_samples': sum(not row for row in rows),
            'ambiguous_samples': sum(len(row) > 1 for row in rows),
            'threshold': MIN_VOTES}


def reconstruction_error(prediction, read_activation):
    import numpy as np
    p, h = np.asarray(prediction, dtype=np.float64), np.asarray(read_activation, dtype=np.float64)
    if p.shape != (5120,) or h.shape != p.shape or not np.isfinite(p).all() or not np.isfinite(h).all():
        raise ValueError('finite native [5120] prediction and capture required')
    error = float(np.square(p - h).mean())
    if not math.isfinite(error):
        raise ValueError('nonfinite reconstruction error')
    return error


def reconstructor_best(errors, parsed):
    if len(errors) != N_SAMPLES or len(parsed) != N_SAMPLES or any(type(x) is not bool for x in parsed):
        raise ValueError('exactly 16 errors and boolean parse statuses required')
    eligible = []
    for i, (error, ok) in enumerate(zip(errors, parsed)):
        if not ok:
            if error is not None:
                raise ValueError('malformed samples must have no reconstruction error')
        elif isinstance(error, bool) or not isinstance(error, (int, float)) or not math.isfinite(error) or error < 0:
            raise ValueError('every parsed sample requires a finite nonnegative reconstruction error')
        else:
            eligible.append(i)
    best = min(eligible, key=lambda i: (errors[i], i)) if eligible else None
    return {'sample_index': best, 'error': errors[best] if best is not None else None,
            'metric': ERROR_METRIC, 'eligible_samples': len(eligible),
            'status': 'SELECTED' if best is not None else 'SILENT_ALL_MALFORMED'}


def any_of_16(statements, values):
    rows, values = _samples(statements, values)
    seen = {row[0] for row in rows if len(row) == 1}
    return {'values': [v for v in values if v in seen], 'descriptive_only': True,
            'n_samples': N_SAMPLES}


def one_of_16_placebo(statements, values, frozen_index):
    rows, values = _samples(statements, values)
    if type(frozen_index) is not int or not 0 <= frozen_index < N_SAMPLES:
        raise ValueError('prejudging frozen placebo index in 0..15 required')
    row = rows[frozen_index]
    return {'values': list(row) if len(row) == 1 else [], 'sample_index': frozen_index,
            'descriptive_only': True, 'n_samples': 1}
