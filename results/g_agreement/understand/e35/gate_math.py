"""E35 held-out SAE gate; no model, filesystem, or network side effects.

Dated implementation note: 2026-10-25. Implements §131 without changing its
50,000-token sample size, FVU <= 0.25, or dead-latent fraction < 0.10.
FVU uses one pooled mean over all held-out tokens, never batchwise centering.
"""
from __future__ import annotations

import math

import numpy as np


HELDOUT_TOKENS = 50_000


def _matrix(value, width: int, name: str) -> np.ndarray:
    a = np.asarray(value)
    if a.ndim != 2 or a.shape[1] != width or a.shape[0] == 0:
        raise ValueError(f"{name}: nonempty token-by-feature matrix required")
    if a.dtype.kind not in "fiu" or not np.isfinite(a).all():
        raise ValueError(f"{name}: finite real numeric entries required")
    return a


class GateAccumulator:
    """Stable float64 pooled moments plus an O(d_sae) firing bitset.

    Pass either dense ``codes`` or a Boolean ``active_latents`` vector on each
    update. The latter is a compact GPU-reduction interface: the caller MUST
    check every code is finite before reducing ``(codes > 0).any(dim=0)``. A
    Boolean mask cannot itself prove the original codes were finite.

    Invalid updates and merges leave the accumulator unchanged. Finalization
    requires exactly 50,000 tokens and positive pooled activation variance.
    """

    def __init__(self, d_model: int, d_sae: int):
        if any(type(d) is not int or d <= 0 for d in (d_model, d_sae)):
            raise ValueError("positive integer dimensions required")
        self.d_model = d_model
        self.d_sae = d_sae
        self.n_tokens = 0
        self._mean = np.zeros(d_model, dtype=np.float64)
        self._m2 = 0.0
        self._squared_error = 0.0
        self._active = np.zeros(d_sae, dtype=np.bool_)

    def update(self, activations, reconstruction, codes=None, *, active_latents=None):
        """Accumulate a token batch and its finite SAE reconstruction/activity."""
        if (codes is None) == (active_latents is None):
            raise ValueError("provide exactly one of codes and active_latents")
        x = _matrix(activations, self.d_model, "activations")
        xr = _matrix(reconstruction, self.d_model, "reconstruction")
        if x.shape != xr.shape:
            raise ValueError("activation and reconstruction shapes must match")
        n = x.shape[0]
        if self.n_tokens + n > HELDOUT_TOKENS:
            raise ValueError("more than 50,000 held-out tokens")
        if codes is not None:
            z = _matrix(codes, self.d_sae, "codes")
            if z.shape[0] != n:
                raise ValueError("code and activation token counts must match")
            active = np.any(z > 0, axis=0)
        else:
            active = np.asarray(active_latents)
            if active.shape != (self.d_sae,) or active.dtype != np.dtype(np.bool_):
                raise ValueError("active_latents must be a Boolean d_sae vector")
        x = x.astype(np.float64, copy=False)
        xr = xr.astype(np.float64, copy=False)
        with np.errstate(over="ignore", invalid="ignore"):
            mean = x.mean(axis=0, dtype=np.float64)
            centered = x - mean
            m2 = float(np.sum(centered * centered, dtype=np.float64))
            error = x - xr
            squared_error = float(np.sum(error * error, dtype=np.float64))
        self._combine(n, mean, m2, squared_error, active)
        return self

    def _combine(self, n, mean, m2, squared_error, active):
        total = self.n_tokens + n
        if total > HELDOUT_TOKENS:
            raise ValueError("more than 50,000 held-out tokens")
        with np.errstate(over="ignore", invalid="ignore"):
            delta = mean - self._mean
            combined_mean = self._mean + delta * (n / total)
            correction = float(np.sum(delta * delta, dtype=np.float64))
            correction *= self.n_tokens * n / total
            combined_m2 = self._m2 + m2 + correction
            combined_error = self._squared_error + squared_error
        if (not np.isfinite(combined_mean).all()
                or not math.isfinite(combined_m2)
                or not math.isfinite(combined_error)
                or combined_m2 < 0 or combined_error < 0):
            raise ValueError("nonfinite or invalid pooled moments")
        self.n_tokens = total
        self._mean = combined_mean
        self._m2 = combined_m2
        self._squared_error = combined_error
        self._active |= active

    def merge(self, other: "GateAccumulator"):
        """Merge disjoint token partitions; caller guarantees no token overlap."""
        if not isinstance(other, GateAccumulator):
            raise TypeError("GateAccumulator required")
        if other is self:
            raise ValueError("cannot merge an accumulator with itself")
        if (self.d_model, self.d_sae) != (other.d_model, other.d_sae):
            raise ValueError("accumulator dimensions must match")
        if other.n_tokens:
            self._combine(other.n_tokens, other._mean, other._m2,
                          other._squared_error, other._active)
        return self

    def result(self) -> dict:
        """Return the registered gate, or reject incomplete/undefined evidence."""
        if self.n_tokens != HELDOUT_TOKENS:
            raise ValueError("exactly 50,000 held-out tokens required")
        if self._m2 <= 0:
            raise ValueError("FVU is undefined for zero pooled activation variance")
        fvu = self._squared_error / self._m2
        if not math.isfinite(fvu):
            raise ValueError("nonfinite FVU")
        dead = int(self.d_sae - np.count_nonzero(self._active))
        # Integer comparison preserves strict <10%, including at the boundary.
        dead_pass = 10 * dead < self.d_sae
        fvu_pass = fvu <= 0.25
        return {
            "n_tokens": self.n_tokens,
            "d_model": self.d_model,
            "d_sae": self.d_sae,
            "squared_error": self._squared_error,
            "total_variance": self._m2,
            "fvu": fvu,
            "dead_latents": dead,
            "dead_fraction": dead / self.d_sae,
            "fvu_pass": fvu_pass,
            "dead_pass": dead_pass,
            "passed": fvu_pass and dead_pass,
        }
