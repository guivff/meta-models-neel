"""V5 outer / inner folds. Pairs -> folds as in Z1 (assign_folds: stratified by family, seed 0, every entry of a pair in one fold).
Error items have a single template_id (pz-t1; see v5.md deviation), so whole (k, start) groups are held out instead: 16 groups
-> 8 folds of two groups, stratified by k (one k = 3 and one k = 4 group per fold)."""
from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np


def assign_folds(units: Iterable[str], stratum_of: Mapping[str, str], n_folds: int, seed: int) -> Dict[str, int]:
    """units -> fold ids, stratified by ``stratum_of`` (Z1's assign_folds recipe; identical output for identical inputs)."""
    rng = np.random.default_rng(seed)
    out: Dict[str, int] = {}
    units = sorted(set(units))
    for s in sorted({stratum_of[u] for u in units}):
        us = [u for u in units if stratum_of[u] == s]
        perm = rng.permutation(len(us))
        for i, j in enumerate(perm):
            out[us[j]] = i % n_folds
    return out


def error_groups(items: Mapping[str, dict], ids: Sequence[str]) -> Dict[str, str]:
    """item -> group key 'k{k}|{start}' (whole groups are held out together)."""
    return {i: f"k{items[i]['source']['k']}|{items[i]['source']['start']}" for i in ids}


def group_folds(ids: Sequence[str], group_of: Mapping[str, str], stratum_of_group: Mapping[str, str], n_folds: int, seed: int) -> np.ndarray:
    """fold id per position of ``ids``; groups never straddle folds."""
    gf = assign_folds(set(group_of[i] for i in ids), stratum_of_group, n_folds, seed)
    return np.array([gf[group_of[i]] for i in ids], dtype=int)


def outer_splits(fold_ids: np.ndarray) -> List[Tuple[int, np.ndarray, np.ndarray]]:
    return [(f, np.where(fold_ids != f)[0], np.where(fold_ids == f)[0]) for f in sorted(set(fold_ids.tolist()))]


def inner_splits(train_idx: np.ndarray, unit_of_row: Sequence[str], n_inner: int, seed: int) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Inner (train, val) index pairs (positions into ``train_idx``) by unit (pair / group), never splitting a unit."""
    units = [unit_of_row[i] for i in train_idx]
    uf = assign_folds(set(units), {u: "all" for u in set(units)}, n_inner, seed)
    f = np.array([uf[u] for u in units])
    out = []
    for k in sorted(set(f.tolist())):
        tr, va = np.where(f != k)[0], np.where(f == k)[0]
        if len(tr) and len(va):
            out.append((tr, va))
    return out
