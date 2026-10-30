"""CPU §216 kernel. Real admission/fit adapter waits for original E60 artifacts.

The caller supplies the unchanged E60 fitter; this module chooses no optimizer,
regularization, gates, native truth threshold, feature transform or fallback.
"""
from collections import Counter
import numpy as np

SEED = 20261029
DRAWS = 2000
MIN_SUCCESS = 1900


def coded_rows(rows, coding):
    """Join only by exact bank/row; reject duplicates and unknowns before analysis."""
    lookup = {(r['bank'], r['row']): r['silent_state_class'] for r in coding['rows']}
    if len(lookup) != len(coding['rows']):
        raise ValueError('duplicate coding key')
    keys = [(r['bank'], r['row']) for r in rows]
    if not rows or len(set(keys)) != len(keys):
        raise ValueError('one nonempty record per bank/row required')
    missing = sorted(set(keys) - set(lookup))
    if missing:
        raise ValueError('commit registration-based coding before drawing: ' + repr(missing))
    result = []
    for r in rows:
        x, s, y = r['j_fraction'], r['S'], r['reported']
        if not (np.isfinite(x) and 0 <= x <= 1 and np.isfinite(s) and -1 <= s <= 1):
            raise ValueError('invalid J fraction or signed S')
        if type(y) is not bool:
            raise ValueError('reported must be the original E60 boolean truth')
        result.append(dict(r, silent_state_class=lookup[r['bank'], r['row']]))
    return sorted(result, key=lambda r: (r['bank'], r['row']))


def predictions(model, x):
    p = np.asarray(model.predict_probability(x), dtype=float)
    if p.shape != x.shape or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('E60 model returned invalid probabilities')
    return p


def summarize(rows, pooled_model, fit_e60, *, draws=DRAWS, minimum_success=MIN_SUCCESS):
    """Input is coded/validated rows for ONE reader; resample whole bank/rows.

    fit_e60(x,y) must return the frozen E60 model protocol or raise ValueError
    for an unestimable fit. Paired readers run with the same sorted keys/seed.
    No source analysis or completed E60 point estimate is recomputed here.
    """
    if not 1 <= minimum_success <= draws:
        raise ValueError('invalid bootstrap success requirement')
    keys = [(r['bank'], r['row']) for r in rows]
    if keys != sorted(set(keys)):
        raise ValueError('sorted unique row keys required')
    x = np.array([r['j_fraction'] for r in rows], float)
    s = np.array([r['S'] for r in rows], float)
    y = np.array([r['reported'] for r in rows], float)
    c = np.array([r['silent_state_class'] for r in rows])
    pooled_p = predictions(pooled_model, x)
    classes = sorted(set(c))
    samples = {cl: [] for cl in classes}
    failures = Counter()
    rng = np.random.default_rng(SEED)
    for _ in range(draws):
        idx = rng.integers(0, len(rows), len(rows))
        try:
            model = fit_e60(x[idx], y[idx])
            p = predictions(model, x[idx])
        except ValueError:
            failures['pooled_fit'] += 1
            continue
        for cl in classes:
            keep = c[idx] == cl
            if not keep.any():
                failures['absent_class:' + cl] += 1
                continue
            samples[cl].append([float(np.mean(s[idx][keep] - p[keep])),
                                float(np.mean(y[idx][keep] - p[keep]))])
    result = {}
    for cl in classes:
        keep = c == cl
        a = np.asarray(samples[cl])
        enough = len(a) >= minimum_success
        result[cl] = dict(n_rows=int(keep.sum()),
            j_range=[float(x[keep].min()), float(x[keep].max())],
            signed_S_minus_report_probability=float(np.mean(s[keep] - pooled_p[keep])),
            binary_calibration_residual=float(np.mean(y[keep] - pooled_p[keep])),
            signed_residual_CI95=np.quantile(a[:, 0], [.025, .975]).tolist() if enough else None,
            binary_residual_CI95=np.quantile(a[:, 1], [.025, .975]).tolist() if enough else None,
            successful_draws=len(a), interval_status='EVALUABLE' if enough else 'NOT EVALUABLE')
    return dict(classes=result, bootstrap=dict(draws=draws, seed=SEED,
        minimum_success=minimum_success, failed_or_absent=dict(failures),
        unit='unique(bank,row)', pooled_refit=True, item_resampling=False),
        estimand_note='Signed S minus a binary report probability is not calibration; binary residual is reported separately.')
