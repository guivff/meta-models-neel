"""Statistics used in every brief: Wilson CI, paired sign test, bootstrap CI, Spearman with CI,
cross-correlation at lags (P1), AUC comparison by bootstrap (P2b)."""
from __future__ import annotations

from typing import Callable, Sequence, Tuple

import numpy as np
from scipy import stats


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float, float]:
    """Return (p, lo, hi)."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, c - h, c + h


def paired_sign_test(a: Sequence[float], b: Sequence[float]) -> Tuple[int, int, float]:
    """Problem-level paired sign test. Returns (n_a_better, n_b_better, two-sided p)."""
    a, b = np.asarray(a), np.asarray(b)
    wins, losses = int((a > b).sum()), int((b > a).sum())
    n = wins + losses
    p = 1.0 if n == 0 else float(stats.binomtest(wins, n, 0.5).pvalue)
    return wins, losses, p


def bootstrap_ci(x: Sequence[float], fn: Callable = np.mean, n_boot: int = 5000, seed: int = 0, alpha: float = 0.05):
    rng = np.random.default_rng(seed)
    x = np.asarray(x)
    vals = [fn(x[rng.integers(0, len(x), len(x))]) for _ in range(n_boot)]
    return float(fn(x)), float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def diff_rate_ci(k1: int, n1: int, k2: int, n2: int, n_boot: int = 5000, seed: int = 0):
    """Bootstrap CI for p1 − p2 (independent arms). For paired arms use paired_sign_test."""
    rng = np.random.default_rng(seed)
    d = rng.binomial(n1, k1 / n1, n_boot) / n1 - rng.binomial(n2, k2 / n2, n_boot) / n2
    return k1 / n1 - k2 / n2, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))


def spearman_ci(x, y, n_boot: int = 2000, seed: int = 0):
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x), np.asarray(y)
    r = stats.spearmanr(x, y).correlation
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, len(x), len(x))
        vals.append(stats.spearmanr(x[i], y[i]).correlation)
    return float(r), float(np.nanquantile(vals, 0.025)), float(np.nanquantile(vals, 0.975))


def lagged_corr(a: Sequence[float], b: Sequence[float], lags=(-1, 0, 1)) -> dict:
    """Pearson correlation between series a (e.g. probe projection) and b (e.g. VEA rate) at lags.
    Positive lag k means a leads b by k checkpoints."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    out = {}
    for k in lags:
        if k > 0:
            x, y = a[:-k], b[k:]
        elif k < 0:
            x, y = a[-k:], b[:k]
        else:
            x, y = a, b
        out[k] = float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 else float("nan")
    return out


def auc_diff_bootstrap(y: np.ndarray, s1: np.ndarray, s2: np.ndarray, n_boot: int = 2000, seed: int = 0):
    """CI for AUC(s1) − AUC(s2) on the same labels y (P2b: diff-predictor vs rarity)."""
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(seed)
    y, s1, s2 = np.asarray(y), np.asarray(s1), np.asarray(s2)
    d0 = roc_auc_score(y, s1) - roc_auc_score(y, s2)
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        if len(set(y[i])) < 2:
            continue
        vals.append(roc_auc_score(y[i], s1[i]) - roc_auc_score(y[i], s2[i]))
    return float(d0), float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))
