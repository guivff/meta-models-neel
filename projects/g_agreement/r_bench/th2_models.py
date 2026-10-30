"""CPU-only lower-order TH-2 models; no file/data loading.

Pair order is lexicographic (01,02,03,12,13,23); pair categories are
00,01,10,11. Joint columns encode error bits little-endian in reader order.
Every fitter uses marginal probabilities and pair counts only.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import combinations
import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import ndtr, ndtri, roots_hermitenorm, betaln
from numpy.polynomial.legendre import leggauss

PAIRS = tuple(combinations(range(4), 2))
PAIR_I = np.array([i for i, j in PAIRS])
PAIR_J = np.array([j for i, j in PAIRS])
BITS = ((np.arange(16)[:, None] >> np.arange(4)) & 1).astype(int)
MAX_LOADING = 0.98
EPS = 1e-14
_GL_X, _GL_W = leggauss(24)
_GL_X = (_GL_X + 1) / 2
_GL_W = _GL_W / 2


def _p_array(p):
    p = np.asarray(p, dtype=float)
    if p.ndim == 1:
        p = p[None, :]
    if p.ndim != 2 or p.shape[1] != 4 or not np.isfinite(p).all():
        raise ValueError('p must be finite with shape (n,4)')
    if np.any((p <= 0) | (p >= 1)):
        raise ValueError('Use smoothed marginal probabilities strictly inside (0,1)')
    return p


def _counts_array(p, counts, weights=None):
    counts = np.asarray(counts, dtype=float).copy()
    if counts.shape != (len(p), 6, 4) or not np.isfinite(counts).all() or np.any(counts < 0):
        raise ValueError('pair_counts must be nonnegative finite (n,6,4)')
    if weights is not None:
        w = np.asarray(weights, dtype=float)
        if w.shape == (len(p),):
            w = w[:, None, None]
        elif w.shape == (len(p), 6):
            w = w[:, :, None]
        if not np.isfinite(w).all() or np.any(w < 0):
            raise ValueError('weights must be finite and nonnegative')
        counts *= w
    return counts


def _bvn_from_terms(pi, pj, h2k2, hk, rho):
    """Plackett integral after rho=sin(theta), vectorized and deterministic."""
    rho = np.asarray(rho, dtype=float)
    angle = np.arcsin(rho)
    th = angle[..., None] * _GL_X
    st = np.sin(th)
    ct2 = np.cos(th) ** 2
    expo = -(h2k2[..., None] - 2 * hk[..., None] * st) / (2 * ct2)
    integral = angle * np.sum(np.exp(expo) * _GL_W, axis=-1) / (2 * np.pi)
    cdf = pi * pj + integral
    density = np.exp(-(h2k2 - 2 * hk * rho) / (2 * (1 - rho ** 2))) / (2 * np.pi * np.sqrt(1 - rho ** 2))
    return cdf, density


def pair_probabilities(p, rho):
    """n x 6 x 4 probabilities from six (or n x 6) Gaussian correlations."""
    p = _p_array(p)
    pi, pj = p[:, PAIR_I], p[:, PAIR_J]
    t = ndtri(p)
    ti, tj = t[:, PAIR_I], t[:, PAIR_J]
    both, _ = _bvn_from_terms(pi, pj, ti * ti + tj * tj, ti * tj, rho)
    return np.stack([1 - pi - pj + both, pj - both, pi - both, both], axis=-1)


class _PairObjective:
    def __init__(self, p, counts, weights=None):
        self.p = _p_array(p)
        self.counts = _counts_array(self.p, counts, weights)
        self.total = float(self.counts.sum())
        self.scale = max(self.total, 1)
        self.pi, self.pj = self.p[:, PAIR_I], self.p[:, PAIR_J]
        t = ndtri(self.p)
        ti, tj = t[:, PAIR_I], t[:, PAIR_J]
        self.h2k2, self.hk = ti * ti + tj * tj, ti * tj

    def rho(self, rho):
        both, dc = _bvn_from_terms(self.pi, self.pj, self.h2k2, self.hk, rho)
        q = np.stack([1 - self.pi - self.pj + both, self.pj - both, self.pi - both, both], axis=-1)
        q = np.maximum(q, EPS)
        nll = -np.sum(self.counts * np.log(q)) / self.scale
        dc_nll = -np.sum(self.counts * np.array([1., -1., -1., 1.]) / q, axis=-1)
        grad = np.sum(dc_nll * dc, axis=0) / self.scale
        return float(nll), grad

    def factor(self, a):
        nll, gr = self.rho(a[PAIR_I] * a[PAIR_J])
        grad = np.zeros(4)
        np.add.at(grad, PAIR_I, gr * a[PAIR_J])
        np.add.at(grad, PAIR_J, gr * a[PAIR_I])
        return nll, grad


def fit_factor(p, pair_counts, weights=None, *, start=None, warm_start=None,
               multistart=None, equal=False, maxiter=160):
    """Composite MLE. Warm starts use one fit unless multistart=True.

    Returns raw composite nll, successful convergence status and loadings.
    A false success flag is never repaired by silently substituting a fit.
    """
    obj = _PairObjective(p, pair_counts, weights)
    if obj.total <= 0:
        return dict(loadings=np.full(4, np.nan), success=False, nll=np.nan,
                    message='empty calibration sample', nit=0, n_starts=0)
    if warm_start is not None:
        if start is not None:
            raise ValueError('Specify start OR warm_start')
        start = warm_start
    if multistart is None:
        multistart = start is None
    if equal:
        def fun(x):
            v, g = obj.factor(np.repeat(x[0], 4))
            return v, np.array([g.sum()])
        starts = [np.array([float(np.mean(start))])] if start is not None else []
        if multistart or not starts:
            starts += [np.array([a]) for a in (.2, .55, .85)]
        bounds = [(0, MAX_LOADING)]
    else:
        fun = obj.factor
        starts = [np.clip(np.asarray(start, dtype=float), 0, MAX_LOADING)] if start is not None else []
        if multistart or not starts:
            starts += [np.repeat(a, 4) for a in (.2, .55, .85)]
        bounds = [(0, MAX_LOADING)] * 4
    fits = [minimize(fun, x, jac=True, method='L-BFGS-B', bounds=bounds,
                     options={'maxiter': maxiter, 'ftol': 1e-12, 'gtol': 1e-7, 'maxls': 30})
            for x in starts]
    finite = [r for r in fits if np.isfinite(r.fun)]
    if not finite:
        return dict(loadings=np.full(4, np.nan), success=False, nll=np.nan,
                    message='all optimizer values nonfinite', nit=0, n_starts=len(fits))
    best = min(finite, key=lambda r: r.fun)
    a = np.repeat(best.x[0], 4) if equal else best.x
    return dict(loadings=np.asarray(a), success=bool(best.success),
                nll=float(best.fun * obj.scale), message=str(best.message),
                nit=int(best.nit), n_starts=len(fits),
                boundary=bool(np.any(a < 1e-6) or np.any(a > MAX_LOADING - 1e-6)))


def fit_equal(p, pair_counts, weights=None, **kwargs):
    return fit_factor(p, pair_counts, weights, equal=True, **kwargs)


@lru_cache(maxsize=16)
def _hermite(n):
    x, w = roots_hermitenorm(n)
    return x, w / np.sqrt(2 * np.pi)


def joint_independence(p):
    p = _p_array(p)
    return np.prod(np.where(BITS[None, :, :] == 1, p[:, None, :], 1 - p[:, None, :]), axis=-1)


def joint_factor(p, a, *, n_nodes=None):
    """n x 16 error-vector probabilities, deterministic normal quadrature.

    Automatic quadrature increases resolution near the registered loading cap.
    Explicit n_nodes supports convergence checks without changing the model.
    """
    p = _p_array(p)
    a = np.asarray(a, dtype=float)
    if a.shape != (4,) or not np.isfinite(a).all() or np.any(np.abs(a) >= 1):
        raise ValueError('a must be four finite loadings strictly inside (-1,1)')
    if np.max(np.abs(a)) == 0:
        return joint_independence(p)
    if n_nodes is None:
        peak = np.max(np.abs(a))
        n_nodes = 96 if peak <= .9 else (192 if peak <= .96 else 512)
    u, w = _hermite(n_nodes)
    q = ndtr((ndtri(p)[:, None, :] - u[None, :, None] * a[None, None, :]) /
             np.sqrt(1 - a * a)[None, None, :])
    out = np.empty((len(p), 16))
    for j, bits in enumerate(BITS):
        factors = np.where(bits[None, None, :] == 1, q, 1 - q)
        out[:, j] = np.sum(np.prod(factors, axis=2) * w[None, :], axis=1)
    # The 16 integrands sum to one at each node. This changes roundoff only.
    out /= out.sum(axis=1, keepdims=True)
    return out


def fit_beta(p, pair_counts, weights=None):
    """Exchangeable beta toy from pooled first/second moments only.

    Its fact-specific mean is the mean of four smoothed reader marginals.
    rho minimizes pair composite likelihood; heterogeneous margins are not kept.
    """
    p = _p_array(p)
    counts = _counts_array(p, pair_counts, weights)
    if counts.sum() == 0:
        return dict(rho=np.nan, success=False, nll=np.nan, message='empty calibration sample')
    mean = p.mean(axis=1)
    pp = mean[:, None]
    def objective(rho):
        both = pp * pp + rho * pp * (1 - pp)
        probs = np.stack([1 - 2 * pp + both, pp - both, pp - both, both], axis=-1)
        return float(-np.sum(counts * np.log(np.maximum(probs, EPS))))
    result = minimize_scalar(objective, bounds=(0, .98), method='bounded', options={'xatol': 1e-10})
    candidates = [(float(result.fun), float(result.x)), (objective(0), 0.), (objective(.98), .98)]
    nll, rho = min(candidates)
    return dict(rho=rho, success=bool(result.success), nll=nll, message=str(result.message))


def joint_beta(p, rho):
    p = _p_array(p)
    mean = p.mean(axis=1)
    if not np.isfinite(rho) or not 0 <= rho < 1:
        raise ValueError('rho must be in [0,1)')
    if rho <= 1e-10:
        return joint_independence(np.repeat(mean[:, None], 4, axis=1))
    total = 1 / rho - 1
    alpha, beta = mean * total, (1 - mean) * total
    k = BITS.sum(axis=1)
    # One vector, not the binomial count event: deliberately no choose(4,k).
    out = np.exp(betaln(alpha[:, None] + k, beta[:, None] + 4 - k) - betaln(alpha, beta)[:, None])
    return out / out.sum(axis=1, keepdims=True)


def correlation_matrix(rho):
    r = np.eye(4)
    r[PAIR_I, PAIR_J] = rho
    r[PAIR_J, PAIR_I] = rho
    return r


def fit_unrestricted(p, pair_counts, weights=None, *, start=None, maxiter=250):
    """Six-correlation Gaussian pair composite MLE, positive definite constraint."""
    obj = _PairObjective(p, pair_counts, weights)
    if obj.total <= 0:
        return dict(correlation=np.full((4, 4), np.nan), success=False, nll=np.nan,
                    message='empty calibration sample')
    def psd(rho):
        return float(np.linalg.eigvalsh(correlation_matrix(rho))[0] - 1e-5)
    def psd_jac(rho):
        _, v = np.linalg.eigh(correlation_matrix(rho))
        return 2 * v[PAIR_I, 0] * v[PAIR_J, 0]
    starts = [np.zeros(6)]
    if start is not None:
        st = np.asarray(start, dtype=float)
        if st.shape == (4, 4):
            st = st[PAIR_I, PAIR_J]
        if st.shape == (4,):
            st = st[PAIR_I] * st[PAIR_J]
        if st.shape != (6,):
            raise ValueError('start must be loadings, six correlations, or 4x4 correlation')
        starts.insert(0, st)
    else:
        starts.append(np.repeat(.4, 6))
    fits = [minimize(obj.rho, st, jac=True, method='SLSQP', bounds=[(-.98, .98)] * 6,
                     constraints=[{'type': 'ineq', 'fun': psd, 'jac': psd_jac}],
                     options={'maxiter': maxiter, 'ftol': 1e-11}) for st in starts]
    feasible = [r for r in fits if np.isfinite(r.fun) and psd(r.x) >= -1e-7]
    if not feasible:
        return dict(correlation=np.full((4, 4), np.nan), success=False, nll=np.nan,
                    message='no feasible optimizer result')
    best = min(feasible, key=lambda r: r.fun)
    return dict(correlation=correlation_matrix(best.x), correlations=best.x,
                success=bool(best.success), nll=float(best.fun * obj.scale),
                message=str(best.message), min_eigenvalue=float(psd(best.x) + 1e-5))


def joint_gaussian(p, correlation, *, seed=20261019, maxpts=300000,
                   abseps=2e-7, return_info=False):
    """Seeded scipy Genz/QMC Gaussian CDF diagnostic; deterministic for fixed seed.

    This is diagnostic only, never the primary model's quadrature. Numerical
    normalization and marginal errors are returned when return_info=True.
    """
    from scipy.stats import multivariate_normal
    p = _p_array(p)
    r = np.asarray(correlation, dtype=float)
    if r.shape != (4, 4) or not np.allclose(r, r.T) or not np.allclose(np.diag(r), 1):
        raise ValueError('Expected 4x4 correlation matrix')
    if np.linalg.eigvalsh(r).min() <= 0:
        raise ValueError('Diagnostic correlation matrix must be positive definite')
    out = np.empty((len(p), 16))
    t = ndtri(p)
    for j, bits in enumerate(BITS):
        signs = 2 * bits - 1
        covariance = r * signs[:, None] * signs[None, :]
        out[:, j] = multivariate_normal.cdf(t * signs, cov=covariance,
            maxpts=maxpts, abseps=abseps, releps=abseps,
            rng=np.random.default_rng(seed + j))
    raw_sum_error = float(np.max(np.abs(out.sum(axis=1) - 1)))
    out = np.maximum(out, 0)
    out /= out.sum(axis=1, keepdims=True)
    marginal_error = float(np.max(np.abs(out @ BITS - p)))
    info = dict(raw_sum_error=raw_sum_error, marginal_error=marginal_error,
                seed=seed, maxpts=maxpts, abseps=abseps)
    return (out, info) if return_info else out


# Convenient descriptive aliases for callers.
fit_exchangeable_beta = fit_beta
joint_exchangeable_beta = joint_beta
joint_unrestricted = joint_gaussian
