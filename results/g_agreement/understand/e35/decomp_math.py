"""E35 §131 clarification 1 numerical contract, frozen 2026-10-25.

Pure CPU functions only: no input files, model calls, labels, or outcomes are
loaded here. Primary errors are encoded directly by the caller. Decoder bias is
not an argument to the registered additive norm-share calculation.
"""
from __future__ import annotations

import math
import numpy as np

SEED = 20261025
BOOTSTRAP_RESAMPLES = 10000
CONTROL_DRAWS = 100
_BATCH = 128


def _weights_and_mask(decoder_norms, structure_mask):
    norms = np.asarray(decoder_norms, dtype=np.float64)
    mask = np.asarray(structure_mask)
    if (norms.ndim != 1 or len(norms) == 0 or not np.isfinite(norms).all()
            or np.any(norms < 0)):
        raise ValueError('finite nonnegative decoder-column norms required')
    if mask.shape != norms.shape or mask.dtype != np.dtype(bool):
        raise ValueError('Boolean structure mask must match decoder columns')
    return norms, mask


def _shares(numerator, denominator, code_nonzero):
    if (not np.isfinite(numerator).all() or not np.isfinite(denominator).all()
            or np.any(numerator < 0) or np.any(denominator < 0)):
        raise ValueError('finite nonnegative latent reconstruction mass required')
    if np.any(code_nonzero & (denominator == 0)):
        raise ValueError('nonzero code has zero decoder-weighted mass')
    shares = np.full(len(denominator), np.nan, dtype=np.float64)
    np.divide(numerator, denominator, out=shares, where=denominator > 0)
    # Separate sums can round a mathematically exact 1 upward by machine epsilon.
    if np.any(shares > 1 + 8 * np.finfo(np.float64).eps):
        raise ValueError('structure mass exceeds total latent mass')
    return np.minimum(shares, 1.)


def latent_share(codes, decoder_norms, structure_mask):
    """Return s(x) per item; NaN denotes an all-zero nonnegative code.

    Sum z_i*||d_i||, not ||sum z_i*d_i||. Process row batches so a full float64
    item-by-latent copy is not required for an 81,920-column dictionary.
    """
    norms, mask = _weights_and_mask(decoder_norms, structure_mask)
    z = np.asarray(codes)
    if z.ndim != 2 or z.shape[0] == 0 or z.shape[1] != len(norms) or z.dtype.kind not in 'fiu':
        raise ValueError('nonempty numeric item-by-latent codes required')
    answer = np.empty(z.shape[0], dtype=np.float64)
    for start in range(0, len(z), _BATCH):
        values = np.asarray(z[start:start + _BATCH], dtype=np.float64)
        if not np.isfinite(values).all() or np.any(values < 0):
            raise ValueError('finite nonnegative SAE codes required')
        with np.errstate(over='ignore', invalid='ignore'):
            total = np.sum(values * norms, axis=1, dtype=np.float64)
            selected = np.sum(values[:, mask] * norms[mask], axis=1, dtype=np.float64)
        answer[start:start + len(values)] = _shares(selected, total, np.any(values > 0, axis=1))
    return answer


def latent_share_sparse(indices, values, decoder_norms, structure_mask):
    """TopK-storage equivalent; each item's latent indices must be distinct."""
    norms, mask = _weights_and_mask(decoder_norms, structure_mask)
    index = np.asarray(indices)
    z = np.asarray(values)
    if (index.ndim != 2 or index.shape[0] == 0 or index.shape[1] == 0
            or index.dtype.kind not in 'iu' or z.shape != index.shape or z.dtype.kind not in 'fiu'
            or np.any(index < 0) or np.any(index >= len(norms))):
        raise ValueError('valid item-by-k latent indices and values required')
    if np.any(np.diff(np.sort(index, axis=1), axis=1) == 0):
        raise ValueError('duplicate sparse latent index within an item')
    if not np.isfinite(z).all() or np.any(z < 0):
        raise ValueError('finite nonnegative SAE codes required')
    with np.errstate(over='ignore', invalid='ignore'):
        mass = z.astype(np.float64, copy=False) * norms[index]
        total = mass.sum(axis=1, dtype=np.float64)
        selected = np.sum(mass * mask[index], axis=1, dtype=np.float64)
    return _shares(selected, total, np.any(z > 0, axis=1))


def _paired(term_share, baseline_share):
    term = np.asarray(term_share, dtype=np.float64)
    baseline = np.asarray(baseline_share, dtype=np.float64)
    if term.ndim != 1 or len(term) == 0 or baseline.shape != term.shape:
        raise ValueError('aligned nonempty per-item share vectors required')
    for values in (term, baseline):
        if np.isinf(values).any() or np.any(values[np.isfinite(values)] < 0) or np.any(values[np.isfinite(values)] > 1):
            raise ValueError('shares must be in [0,1], or NaN for all-zero code')
    valid = np.isfinite(term) & np.isfinite(baseline)
    return term, baseline, valid


def paired_ratio(term_share, baseline_share):
    """Ratio of item means on the same nonzero-code items, with exclusions."""
    term, baseline, valid = _paired(term_share, baseline_share)
    n = len(term)
    kept = int(valid.sum())
    excluded = n - kept
    term_mean = float(term[valid].mean()) if kept else None
    baseline_mean = float(baseline[valid].mean()) if kept else None
    ratio = term_mean / baseline_mean if kept and baseline_mean > 0 else None
    if ratio is not None and not math.isfinite(ratio):
        raise ValueError('nonfinite ratio from positive baseline mass')
    return {
        'n_items': n, 'paired_items': kept, 'excluded_items': excluded,
        'excluded_fraction': excluded / n,
        'term_zero_code_items': int(np.isnan(term).sum()),
        'baseline_zero_code_items': int(np.isnan(baseline).sum()),
        'exclusion_limit_exceeded': 10 * excluded > n,
        'mean_term_share': term_mean, 'mean_baseline_share': baseline_mean,
        'ratio': ratio,
    }


def rule_decision(ratio, ci95, excluded_items, n_items, *, undefined_bootstrap_draws=0):
    """Frozen R1/R2 boundaries; None is uninterpretable, never a failed rule."""
    if (type(n_items) is not int or n_items <= 0 or type(excluded_items) is not int
            or not 0 <= excluded_items <= n_items or type(undefined_bootstrap_draws) is not int
            or undefined_bootstrap_draws < 0):
        raise ValueError('valid integer item and bootstrap counts required')
    reasons = []
    if 10 * excluded_items > n_items:
        reasons.append('more_than_10_percent_paired_items_excluded')
    if ratio is None or not math.isfinite(ratio):
        reasons.append('undefined_ratio')
    if ci95 is None or len(ci95) != 2 or any(x is None or not math.isfinite(x) for x in ci95):
        reasons.append('undefined_confidence_interval')
    elif ci95[0] < 0 or ci95[1] < ci95[0]:
        raise ValueError('invalid ordered nonnegative confidence interval')
    if undefined_bootstrap_draws:
        reasons.append('undefined_bootstrap_draws_not_discarded')
    if ratio is not None and math.isfinite(ratio) and ratio < 0:
        raise ValueError('ratio cannot be negative')
    interpretable = not reasons
    return {'interpretable': interpretable,
            'rule_met': bool(ratio >= 1.5 and ci95[0] > 1.) if interpretable else None,
            'uninterpretable_reasons': reasons}


def row_cluster_analysis(term_share, baseline_share, rows):
    """Exactly 10,000 percentile draws of whole nonempty row clusters.

    Each sampled row retains every paired valid item. The estimator is always
    the ratio of *item* means, never the unweighted mean of row means or ratios.
    Zero-baseline bootstrap draws are counted; no finite-only CI is substituted.
    """
    term, baseline, valid = _paired(term_share, baseline_share)
    row = np.asarray(rows)
    if row.shape != term.shape or row.dtype.kind not in 'US' or any(len(x) == 0 for x in row):
        raise ValueError('one nonempty string row ID per item required')
    report = paired_ratio(term, baseline)
    names, inverse = np.unique(row[valid], return_inverse=True)
    report.update(bootstrap_resamples_requested=BOOTSTRAP_RESAMPLES,
                  bootstrap_resamples_performed=0, bootstrap_seed=SEED,
                  bootstrap_method='whole_nonempty_row_clusters_with_replacement',
                  ci_method='percentile_2.5_97.5_linear', rows_total=len(np.unique(row)),
                  rows_with_paired_items=len(names), ci95=None,
                  undefined_bootstrap_draws=0)
    if report['ratio'] is not None:
        t_sums = np.bincount(inverse, weights=term[valid], minlength=len(names))
        h_sums = np.bincount(inverse, weights=baseline[valid], minlength=len(names))
        rng = np.random.default_rng(SEED)
        draws = rng.integers(0, len(names), size=(BOOTSTRAP_RESAMPLES, len(names)))
        t_boot = t_sums[draws].sum(axis=1)
        h_boot = h_sums[draws].sum(axis=1)
        undefined = int(np.count_nonzero(h_boot <= 0))
        report['bootstrap_resamples_performed'] = BOOTSTRAP_RESAMPLES
        report['undefined_bootstrap_draws'] = undefined
        if not undefined:
            with np.errstate(over='ignore', invalid='ignore'):
                boot_ratios = t_boot / h_boot
            if not np.isfinite(boot_ratios).all():
                raise ValueError('nonfinite bootstrap ratio from positive baseline mass')
            report['ci95'] = np.quantile(boot_ratios, [.025, .975], method='linear').tolist()
    report.update(rule_decision(report['ratio'], report['ci95'], report['excluded_items'],
                                report['n_items'], undefined_bootstrap_draws=report['undefined_bootstrap_draws']))
    return report


def frequency_matched_masks(dev_activation_counts, structure_mask, draws=CONTROL_DRAWS, seed=SEED):
    """Shuffle structure membership within exact dev firing-count strata.

    Matching is across the complete latent dictionary. The structure count in
    each frequency stratum is preserved exactly. Singleton or fully selected
    strata remain unchanged; matching is never relaxed to obtain varied draws.
    """
    counts = np.asarray(dev_activation_counts)
    mask = np.asarray(structure_mask)
    if counts.ndim != 1 or len(counts) == 0 or counts.dtype.kind not in 'iu' or np.any(counts < 0):
        raise ValueError('nonnegative integer dev activation counts required')
    if mask.shape != counts.shape or mask.dtype != np.dtype(bool):
        raise ValueError('Boolean structure mask must match latent frequencies')
    if type(draws) is not int or draws != CONTROL_DRAWS or type(seed) is not int or seed != SEED:
        raise ValueError('registered controls require 100 draws and seed20261025')
    strata = []
    for frequency in np.unique(counts):
        pool = np.flatnonzero(counts == frequency)
        strata.append((pool, int(mask[pool].sum())))
    answer = np.zeros((draws, len(mask)), dtype=bool)
    rng = np.random.default_rng(seed)
    for draw in range(draws):
        for pool, number in strata:
            if number:
                chosen = pool if number == len(pool) else rng.choice(pool, size=number, replace=False)
                answer[draw, chosen] = True
    return answer


def control_summary(term_control_shares, baseline_control_shares, *, masks=None, structure_mask=None):
    """Return every seeded null ratio; no CI or hypothesis rule for controls."""
    term = np.asarray(term_control_shares, dtype=np.float64)
    baseline = np.asarray(baseline_control_shares, dtype=np.float64)
    if term.ndim != 2 or term.shape[0] != CONTROL_DRAWS or baseline.shape != term.shape:
        raise ValueError('aligned 100-by-item control shares required')
    reports = [paired_ratio(t, h) for t, h in zip(term, baseline)]
    if not np.all(np.isnan(term) == np.isnan(term[:1])) or not np.all(np.isnan(baseline) == np.isnan(baseline[:1])):
        raise ValueError('zero-code exclusions must be invariant to shuffled labels')
    ratios = [r['ratio'] for r in reports]
    undefined = sum(x is None for x in ratios)
    out = {'draws': CONTROL_DRAWS, 'seed': SEED, 'ratios': ratios,
           'undefined_ratios': undefined,
           'paired_items_per_draw': [r['paired_items'] for r in reports],
           'null_percentiles_2_5_50_97_5': None if undefined else np.quantile(ratios, [.025, .5, .975], method='linear').tolist(),
           'null_CI_computed': False, 'rule_applied_to_controls': False}
    if (masks is None) != (structure_mask is None):
        raise ValueError('provide both masks and observed structure mask, or neither')
    if masks is not None:
        mm, observed = np.asarray(masks), np.asarray(structure_mask)
        if (mm.ndim != 2 or mm.shape[0] != CONTROL_DRAWS or observed.shape != mm.shape[1:]
                or mm.dtype != np.dtype(bool) or observed.dtype != np.dtype(bool)):
            raise ValueError('Boolean control and structure masks required')
        if not np.all(mm.sum(axis=1) == observed.sum()):
            raise ValueError('control masks must preserve the structure-latent count')
        out.update(unique_masks=int(len(np.unique(np.packbits(mm, axis=1), axis=0))),
                   draws_equal_observed=int(np.all(mm == observed, axis=1).sum()))
    return out
