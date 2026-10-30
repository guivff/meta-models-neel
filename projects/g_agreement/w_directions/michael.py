"""Michael Kenney's steering recipe (nla-consistency/scripts/steer_pod.py, ``capture``), reproduced for our graded slots
(PREREG_WV.md Track B "Michael's recipe ... 18 class-mean + 18 probe-weight directions"). Runs after S1 captures the counts
(N 1–99 at the number position) and arithmetic ("=" token) states; here only the function and its synthetic test.

His recipe, verbatim in structure:
  mu = X.mean(0); sd = X.std(0) + 1e-6 (torch unbiased std); Z = (X − mu) / sd
  per digit variable k ∈ {<slot>_tens, <slot>_units} (value // 10, value % 10, 10 classes each): a 10-way softmax probe
      fit_lr(Z, y): LBFGS(max_iter=300, strong_wolfe) on cross_entropy(Z W + b, y) + 1e-3 ‖W‖²
  per slot: class-mean directions = X[y_k == c].mean(0) − mu for every class c present in each of the two digit variables
      (≤ 20 vectors; the count-weighted sum per variable is zero, so orth() keeps ≤ 9 per variable → the "18");
      probe-weight directions = W_k / sd[:, None] (z-space weights → raw-space read directions), 20 columns → orth()
      keeps ≤ 9 per variable (the softmax shift invariance + L2 make the columns sum to zero → the other "18");
      random = orth(randn(d, r_mean, generator seeded 0)), same rank as the class-mean subspace, one generator shared by
      every slot in order.
  orth(D) = left singular vectors of D with S > S[0]·1e-4.
  swap: h' = h_base + U Uᵀ (h_src − h_base) for U ∈ {mean, lr, rand}; probe read-back = argmax of each digit probe on z(h').
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

import torch

L2 = 1e-3
MAX_ITER = 300
ORTH_REL_TOL = 1e-4
N_DIGIT_CLASSES = 10


def digit_labels(values: torch.Tensor) -> Dict[str, torch.Tensor]:
    """{'tens': v // 10, 'units': v % 10} for integer ``values`` in 0..99."""
    v = torch.as_tensor(values).long()
    if v.ndim != 1 or bool((v < 0).any()) or bool((v > 99).any()):
        raise ValueError("values must be a 1-D tensor of integers in 0..99")
    return {"tens": v // 10, "units": v % 10}


def fit_lr(Z: torch.Tensor, y: torch.Tensor, ncls: int = N_DIGIT_CLASSES, l2: float = L2, max_iter: int = MAX_ITER) -> Tuple[torch.Tensor, torch.Tensor]:
    """Michael's ``fit_lr``: softmax regression on standardised features by LBFGS (strong Wolfe), CE + l2·‖W‖²."""
    Z = Z.float()
    y = torch.as_tensor(y).long()
    W = torch.zeros(Z.shape[1], ncls, requires_grad=True)
    bias = torch.zeros(ncls, requires_grad=True)
    opt = torch.optim.LBFGS([W, bias], max_iter=max_iter, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(Z @ W + bias, y) + l2 * (W ** 2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    return W.detach(), bias.detach()


def orth(D: torch.Tensor, rel_tol: float = ORTH_REL_TOL) -> torch.Tensor:
    """Orthonormal basis (d × r) for the span of the columns of ``D`` (singular values above rel_tol × the largest)."""
    U, S, _ = torch.linalg.svd(D.float(), full_matrices=False)
    return U[:, S > S[0] * rel_tol]


def michael_subspaces(X: torch.Tensor, slots: Mapping[str, torch.Tensor], *, seed: int = 0) -> Dict[str, Any]:
    """Fit the recipe on states ``X`` [n, d] for graded ``slots`` {slot_name: integer values [n] in 0..99} (counts: one slot;
    arithmetic "a ± b": slots a and b, exactly his operands). Returns {'mu', 'sd', 'probes': {digit_var: {'W', 'b'}} (z-space),
    'subspaces': {'<slot>|mean' | '<slot>|lr' | '<slot>|rand': U [d, r]}, 'ranks': {...}, 'classes': {digit_var: [present classes]}}."""
    X = torch.as_tensor(X).float()
    if X.ndim != 2:
        raise ValueError("X must be [n, d]")
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Z = (X - mu) / sd
    ys: Dict[str, torch.Tensor] = {}
    for slot, vals in slots.items():
        if len(vals) != X.shape[0]:
            raise ValueError(f"slot {slot}: {len(vals)} values for {X.shape[0]} states")
        for k, y in digit_labels(torch.as_tensor(vals)).items():
            ys[f"{slot}_{k}"] = y
    probes = {k: fit_lr(Z, y) for k, y in ys.items()}
    sub: Dict[str, torch.Tensor] = {}
    ranks: Dict[str, int] = {}
    g = torch.Generator().manual_seed(int(seed))
    for slot in slots:
        mean_dirs, lr_dirs = [], []
        for k in (f"{slot}_tens", f"{slot}_units"):
            for c in ys[k].unique():
                mean_dirs.append(X[ys[k] == c].mean(0) - mu)
            lr_dirs.append(probes[k][0] / sd[:, None])
        sub[f"{slot}|mean"] = orth(torch.stack(mean_dirs, 1))
        sub[f"{slot}|lr"] = orth(torch.cat(lr_dirs, 1))
        r = int(sub[f"{slot}|mean"].shape[1])
        sub[f"{slot}|rand"] = orth(torch.randn(X.shape[1], r, generator=g))
        ranks[f"{slot}|mean"], ranks[f"{slot}|lr"], ranks[f"{slot}|rand"] = r, int(sub[f"{slot}|lr"].shape[1]), int(sub[f"{slot}|rand"].shape[1])
    return {"mu": mu, "sd": sd, "probes": {k: {"W": W, "b": b} for k, (W, b) in probes.items()}, "subspaces": sub, "ranks": ranks,
            "classes": {k: [int(c) for c in y.unique()] for k, y in ys.items()}, "n_states": int(X.shape[0]), "seed": int(seed),
            "recipe": "nla-consistency/scripts/steer_pod.py capture(): class-mean and LBFGS softmax-probe subspaces per digit, orth() SVD rel tol 1e-4"}


def swap(h_base: torch.Tensor, h_src: torch.Tensor, U: torch.Tensor) -> torch.Tensor:
    """Interchange intervention restricted to the subspace: h' = h_base + U Uᵀ (h_src − h_base)."""
    return h_base + U @ (U.T @ (h_src - h_base))


def read_digits(h: torch.Tensor, fit: Mapping[str, Any]) -> Dict[str, int]:
    """Michael's ``read``: argmax of every digit probe on the standardised vector."""
    z = ((torch.as_tensor(h).float() - fit["mu"]) / fit["sd"])[None]
    return {k: int((z @ p["W"] + p["b"]).argmax()) for k, p in fit["probes"].items()}


def read_value(h: torch.Tensor, fit: Mapping[str, Any], slot: str) -> int:
    d = read_digits(h, fit)
    return d[f"{slot}_tens"] * 10 + d[f"{slot}_units"]
