"""Small statistics for W3 / V4: item-level bootstrap precision and Cohen's kappa (pure numpy, tested offline)."""
from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


def precision_item_bootstrap(items: Sequence[str], truth: Sequence[Optional[bool]], n_boot: int = 1000,
                             seed: int = 0, alpha: float = 0.05) -> dict:
    """Pooled precision true/(true+false) over claims, CI by resampling ITEMS (states) with replacement.
    Claims with truth None (unverifiable) are ignored. Returns {n_items, n_claims, n_true, precision, lo, hi}."""
    pairs = [(i, t) for i, t in zip(items, truth) if t is not None]
    if not pairs:
        return {"n_items": 0, "n_claims": 0, "n_true": 0, "precision": None, "lo": None, "hi": None}
    by_item: Dict[str, List[bool]] = {}
    for i, t in pairs:
        by_item.setdefault(i, []).append(bool(t))
    ids = sorted(by_item)
    tr = np.array([sum(by_item[i]) for i in ids], dtype=float)
    nn = np.array([len(by_item[i]) for i in ids], dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ids), (n_boot, len(ids)))
    boots = tr[idx].sum(1) / np.maximum(nn[idx].sum(1), 1)
    return {"n_items": len(ids), "n_claims": int(nn.sum()), "n_true": int(tr.sum()),
            "precision": float(tr.sum() / nn.sum()), "lo": float(np.quantile(boots, alpha / 2)),
            "hi": float(np.quantile(boots, 1 - alpha / 2))}


def cohen_kappa(a: Sequence, b: Sequence) -> dict:
    """Unweighted Cohen's kappa over paired labels (pairs with a None label are dropped)."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    n = len(pairs)
    if n == 0:
        return {"n": 0, "kappa": None, "agreement": None}
    cats = sorted({x for p in pairs for x in p}, key=str)
    po = sum(x == y for x, y in pairs) / n
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum(ca[c] * cb[c] for c in cats) / n ** 2
    kappa = 1.0 if pe == 1.0 else (po - pe) / (1 - pe)
    return {"n": n, "kappa": float(kappa), "agreement": float(po), "categories": [str(c) for c in cats]}


def kappa_bootstrap(a: Sequence, b: Sequence, n_boot: int = 1000, seed: int = 0) -> Tuple[Optional[float], Optional[float]]:
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 2:
        return None, None
    rng = np.random.default_rng(seed)
    ks = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(pairs), len(pairs))
        k = cohen_kappa([pairs[i][0] for i in idx], [pairs[i][1] for i in idx])["kappa"]
        if k is not None:
            ks.append(k)
    return float(np.quantile(ks, 0.025)), float(np.quantile(ks, 0.975))


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float, float]:
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)
