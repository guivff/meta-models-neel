"""Directions, probes, controls and noise ceilings.

- `dim_direction`: difference-in-means direction from (positive, negative) activation sets, per layer.
- `contrastive_pairs_direction`: Heidari et al. recipe (16 contrastive prompt pairs, last token, normalised mean diff).
- `fit_logistic_probe` / `auroc`: standard linear probe with held-out AUROC.
- `random_direction_auroc`: 10 random-direction controls (as in Heidari).
- `two_half_ceiling`: cosine between directions fit on two disjoint halves of the data (noise ceiling for rotation claims).
- `rotation_deg`: angle between two directions, for P4.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


def _np(x):
    return x.detach().float().cpu().numpy() if torch.is_tensor(x) else np.asarray(x, dtype=np.float32)


def dim_direction(pos: np.ndarray, neg: np.ndarray, normalise: bool = True) -> np.ndarray:
    """Difference-in-means direction. pos/neg: (N, d) activations at one layer/position."""
    d = _np(pos).mean(0) - _np(neg).mean(0)
    return d / (np.linalg.norm(d) + 1e-8) if normalise else d


def contrastive_pairs_direction(acts_a: np.ndarray, acts_b: np.ndarray) -> np.ndarray:
    """Heidari recipe: acts_a/acts_b are (16, d) last-token activations for the two sides of each pair."""
    return dim_direction(acts_a, acts_b, normalise=True)


def project(acts: np.ndarray, direction: np.ndarray) -> np.ndarray:
    return _np(acts) @ (direction / (np.linalg.norm(direction) + 1e-8))


def auroc(scores_pos: np.ndarray, scores_neg: np.ndarray) -> float:
    y = np.r_[np.ones(len(scores_pos)), np.zeros(len(scores_neg))]
    s = np.r_[scores_pos, scores_neg]
    return float(roc_auc_score(y, s))


def direction_auroc(direction: np.ndarray, test_pos: np.ndarray, test_neg: np.ndarray) -> float:
    return auroc(project(test_pos, direction), project(test_neg, direction))


def random_direction_auroc(d: int, test_pos: np.ndarray, test_neg: np.ndarray, n: int = 10, seed: int = 0) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = [direction_auroc(rng.standard_normal(d), test_pos, test_neg) for _ in range(n)]
    return float(np.mean(vals)), float(np.std(vals))


def fit_logistic_probe(X_pos: np.ndarray, X_neg: np.ndarray, C: float = 1.0, seed: int = 0) -> LogisticRegression:
    X = np.r_[_np(X_pos), _np(X_neg)]
    y = np.r_[np.ones(len(X_pos)), np.zeros(len(X_neg))]
    clf = LogisticRegression(C=C, max_iter=2000, random_state=seed)
    clf.fit(X, y)
    return clf


def probe_auroc(clf: LogisticRegression, X_pos: np.ndarray, X_neg: np.ndarray) -> float:
    return auroc(clf.decision_function(_np(X_pos)), clf.decision_function(_np(X_neg)))


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a, b = _np(a).ravel(), _np(b).ravel()
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


def rotation_deg(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.degrees(np.arccos(np.clip(cosine(a, b), -1, 1))))


def two_half_ceiling(pos: np.ndarray, neg: np.ndarray, seed: int = 0, n_splits: int = 5) -> Tuple[float, float]:
    """Cosine between DIM directions fit on two random disjoint halves. Mean, std over splits.
    Any rotation claim must exceed (1 − this) by a margin; report both numbers."""
    rng = np.random.default_rng(seed)
    pos, neg = _np(pos), _np(neg)
    vals = []
    for _ in range(n_splits):
        ip, ineg = rng.permutation(len(pos)), rng.permutation(len(neg))
        hp, hn = len(pos) // 2, len(neg) // 2
        d1 = dim_direction(pos[ip[:hp]], neg[ineg[:hn]])
        d2 = dim_direction(pos[ip[hp:]], neg[ineg[hn:]])
        vals.append(cosine(d1, d2))
    return float(np.mean(vals)), float(np.std(vals))


def project_out(acts: np.ndarray, direction: np.ndarray) -> np.ndarray:
    u = direction / (np.linalg.norm(direction) + 1e-8)
    acts = _np(acts)
    return acts - np.outer(acts @ u, u)
