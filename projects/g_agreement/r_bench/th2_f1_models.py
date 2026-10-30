"""CPU-only TH-2-F1 signed six-instrument factor; no file or outcome loading.

Instrument order: J-lens, Oracle, NLA, skip_a, probe256, prompt-only. Pattern
bits are little-endian; pair categories are 00,01,10,11 (2*E_i+E_j).
Only marginal probabilities and pair tables enter the fitting objective.
"""
from __future__ import annotations
from functools import lru_cache
from itertools import combinations
import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr, logsumexp, ndtri, ndtr
from projects.g_agreement.r_bench.th2_models import _bvn_from_terms, _hermite

PAIRS = tuple(combinations(range(6), 2))
PAIR_I = np.array([i for i, _ in PAIRS])
PAIR_J = np.array([j for _, j in PAIRS])
BITS = ((np.arange(64)[:, None] >> np.arange(6)) & 1).astype(int)
MAX_LOADING, EPS = .98, 1e-14
BOUNDS = [(0., .98)] * 4 + [(-.98, .98)] * 2
_PAIR_INDICATOR = np.stack([
    (2 * BITS[:, i, None] + BITS[:, j, None] == np.arange(4)[None, :]).astype(float)
    for i, j in PAIRS], axis=1)


def _p_array(p, n_instruments=6):
    p = np.asarray(p, dtype=float)
    if p.ndim == 1:
        p = p[None, :]
    if p.ndim != 2 or (n_instruments is not None and p.shape[1] != n_instruments):
        raise ValueError(f'p must have shape (n,{n_instruments})')
    if not np.isfinite(p).all() or np.any((p <= 0) | (p >= 1)):
        raise ValueError('Marginals must be finite and strictly inside (0,1); smooth them first')
    return p


def pair_counts(pattern_counts):
    """Counts with final dimension64 -> pair counts with final dimensions15,4."""
    counts = np.asarray(pattern_counts, dtype=float)
    if counts.ndim < 1 or counts.shape[-1] != 64:
        raise ValueError('pattern_counts must have final dimension64')
    if not np.isfinite(counts).all() or np.any(counts < 0):
        raise ValueError('pattern_counts must be finite and nonnegative')
    return (counts.reshape(-1, 64) @ _PAIR_INDICATOR.reshape(64, 60)).reshape(counts.shape[:-1] + (15, 4))


def pair_probabilities(p, rho):
    """Deterministic n x15 x4 Gaussian pair probabilities."""
    p = _p_array(p)
    rho = np.asarray(rho, dtype=float)
    if rho.shape not in ((15,), (len(p), 15)) or not np.isfinite(rho).all() or np.any(abs(rho) >= 1):
        raise ValueError('rho must have shape (15,) or (n,15), strictly inside (-1,1)')
    pi, pj = p[:, PAIR_I], p[:, PAIR_J]
    t = ndtri(p)
    ti, tj = t[:, PAIR_I], t[:, PAIR_J]
    both, _ = _bvn_from_terms(pi, pj, ti * ti + tj * tj, ti * tj, rho)
    return np.stack([1-pi-pj+both, pj-both, pi-both, both], axis=-1)


class _PairObjective:
    """Pair composite likelihood; higher-order pattern counts are not accepted."""
    def __init__(self, p, counts, weights=None):
        self.p = _p_array(p)
        self.counts = np.asarray(counts, dtype=float).copy()
        if self.counts.shape != (len(self.p), 15, 4):
            raise ValueError('pair_counts must have shape (n,15,4)')
        if not np.isfinite(self.counts).all() or np.any(self.counts < 0):
            raise ValueError('pair_counts must be finite and nonnegative')
        if weights is not None:
            weights = np.asarray(weights, dtype=float)
            if weights.shape == (len(self.p),):
                weights = weights[:, None, None]
            elif weights.shape == (len(self.p), 15):
                weights = weights[:, :, None]
            if not np.isfinite(weights).all() or np.any(weights < 0):
                raise ValueError('weights must be finite and nonnegative')
            self.counts *= weights
        self.total = float(self.counts.sum())
        self.scale = max(self.total, 1.)
        self.pi, self.pj = self.p[:, PAIR_I], self.p[:, PAIR_J]
        t = ndtri(self.p)
        ti, tj = t[:, PAIR_I], t[:, PAIR_J]
        self.h2k2, self.hk = ti*ti+tj*tj, ti*tj

    def rho(self, rho):
        both, derivative = _bvn_from_terms(self.pi, self.pj, self.h2k2, self.hk, rho)
        q = np.stack([1-self.pi-self.pj+both, self.pj-both, self.pi-both, both], axis=-1)
        q = np.maximum(q, EPS)
        nll = -np.sum(self.counts*np.log(q))/self.scale
        slope = -np.sum(self.counts*np.array([1.,-1.,-1.,1.])/q, axis=-1)
        return float(nll), np.sum(slope*derivative, axis=0)/self.scale

    def factor(self, a):
        value, g = self.rho(a[PAIR_I]*a[PAIR_J])
        gradient = np.zeros(6)
        np.add.at(gradient, PAIR_I, g*a[PAIR_J])
        np.add.at(gradient, PAIR_J, g*a[PAIR_I])
        return value, gradient


def _starts(start, multistart):
    starts = []
    if start is not None:
        start = np.asarray(start, dtype=float)
        if start.shape != (6,) or not np.isfinite(start).all():
            raise ValueError('start must contain six finite loadings')
        starts.append(np.clip(start, [x[0] for x in BOUNDS], [x[1] for x in BOUNDS]))
    if multistart or not starts:
        # Every external sign quadrant, zero externals, three reader magnitudes.
        # Starts remain fixed, independent of observed or endpoint outcomes.
        for readers, ext1, ext2 in ((.2,.3,.3),(.55,-.3,-.3),(.85,.3,-.3),(.55,-.3,.3),(.55,0.,0.)):
            starts.append(np.array([readers]*4+[ext1,ext2]))
    unique = []
    for item in starts:
        if not any(np.array_equal(item, old) for old in unique):
            unique.append(item)
    return unique


def fit_factor(p, pair_counts, weights=None, *, start=None, multistart=True, maxiter=180):
    """Pair composite MLE; warm start does not disable deterministic multistarts."""
    objective = _PairObjective(p, pair_counts, weights)
    if objective.total <= 0:
        return dict(loadings=np.full(6,np.nan),success=False,nll=np.nan,
                    message='empty calibration sample',nit=0,n_starts=0)
    starts = _starts(start,multistart)
    results = [minimize(objective.factor, initial, jac=True, method='L-BFGS-B', bounds=BOUNDS,
                       options={'maxiter':maxiter,'ftol':1e-12,'gtol':1e-7,'maxls':30})
               for initial in starts]
    finite = [r for r in results if np.isfinite(r.fun)]
    if not finite:
        return dict(loadings=np.full(6,np.nan),success=False,nll=np.nan,
                    message='all objective values nonfinite',nit=0,n_starts=len(starts))
    best = min(finite,key=lambda r:r.fun)
    return dict(loadings=np.asarray(best.x),success=bool(best.success),
                nll=float(best.fun*objective.scale),message=str(best.message),nit=int(best.nit),
                n_starts=len(starts),n_successful_starts=sum(bool(r.success) for r in results),
                orientation_identified=bool(np.any(best.x[:4]>1e-5)))


@lru_cache(maxsize=8)
def pattern_bits(n_instruments):
    return ((np.arange(2**n_instruments)[:,None]>>np.arange(n_instruments))&1).astype(int)


def quadrature_nodes(a):
    """Posterior means require finer resolution than probability marginals."""
    peak = float(np.max(np.abs(a)))
    return 128 if peak<=.80 else (256 if peak<=.90 else (512 if peak<=.96 else 1024))


def _conditional_patterns(correct, error):
    """Conditional pattern table; final axis is little-endian pattern code."""
    result = np.ones(correct.shape[:-1] + (1,))
    for r in range(correct.shape[-1]):
        result = np.concatenate((result*correct[...,r,None], result*error[...,r,None]),axis=-1)
    return result


def joint_posterior(p, a, n_nodes=None):
    """Return joint[n,2**k], E[-U|pattern][n,2**k] for1<=k<=6.

    Two small conditional tables are integrated by batched matrix products.
    CDFs of both signs are evaluated directly (never subtract a rounded CDF
    from one). Patterns below1e-250 use log-domain integration for stable
    posterior targets even when their probability itself underflows.
    """
    p = _p_array(p,n_instruments=None)
    n,k = p.shape
    a = np.asarray(a,dtype=float)
    if not 1<=k<=6 or a.shape!=(k,) or not np.isfinite(a).all() or np.any(abs(a)>=1):
        raise ValueError('Use1..6 marginals and matching finite loadings inside(-1,1)')
    if n_nodes is None:
        n_nodes = quadrature_nodes(a)
    if n_nodes<8:
        raise ValueError('At least eight quadrature nodes required')
    u,weights = _hermite(int(n_nodes))
    positive = weights>0
    u,weights = u[positive],weights[positive]
    z = (ndtri(p)[:,None,:]-u[None,:,None]*a[None,None,:])/np.sqrt(1-a*a)[None,None,:]
    correct,error = ndtr(-z),ndtr(z)
    split = k//2
    low = _conditional_patterns(correct[:,:,:split],error[:,:,:split])
    high = _conditional_patterns(correct[:,:,split:],error[:,:,split:])
    # Axes(high bits,low bits) flatten in the registered little-endian order.
    high_t = high.transpose(0,2,1)
    joint = (high_t @ (low*weights[None,:,None])).reshape(n,2**k)
    numerator = (high_t @ (low*(-u*weights)[None,:,None])).reshape(n,2**k)
    posterior_d = np.empty_like(joint)
    ordinary = joint>=1e-250
    np.divide(numerator,joint,out=posterior_d,where=ordinary)
    rare_rows,rare_patterns = np.where(~ordinary)
    if len(rare_rows):
        bits = pattern_bits(k)
        log_weights = np.log(weights)
        # Rare patterns are exceptional; process only affected cells, without
        # constructing another n x quadrature x64 table in the normal path.
        for row,j in zip(rare_rows,rare_patterns):
            log_terms = np.where(bits[j][None,:]==1,log_ndtr(z[row]),log_ndtr(-z[row])).sum(axis=1)
            log_mass = log_terms+log_weights
            normalizer = logsumexp(log_mass)
            joint[row,j] = np.exp(normalizer)
            posterior_d[row,j] = np.sum(np.exp(log_mass-normalizer)*(-u))
    joint /= joint.sum(axis=1,keepdims=True)
    return joint,posterior_d


def posterior_four(p,a,n_nodes=None):
    """Use only first-four errors; supplied loadings may come from a4/6 fit."""
    p = _p_array(p,n_instruments=None)
    a = np.asarray(a,dtype=float)
    if p.shape[1]<4 or a.shape[0]<4:
        raise ValueError('At least four instruments needed')
    return joint_posterior(p[:,:4],a[:4],n_nodes=n_nodes)


def joint_factor(p,a,n_nodes=None):
    return joint_posterior(p,a,n_nodes=n_nodes)[0]
