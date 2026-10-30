#!/usr/bin/env python
"""Friday re-analyses R2, R3, R4 and the Y0 worked cases (CPU only, no new compute).

Inputs are the frozen Phase-X artefacts (NEXT_STEPS.md §1; writeup.md "Corrections after independent review",
2026-10-08). Everything here takes paths / arrays as arguments so the tests can run it on synthetic data.

R2  Fair binding probes on the cached block-42 X1 states (test split; 47 ownership + 47 mapping pairs):
    (a) within-pair contrast probe, LOO by pair: u = mean over training pairs of (h_pos − h_neg); win = u·(h_pos − h_neg) > 0.
        Two labels: `version` (pos = A, i.e. answer_position 0 = candidates[0]; tautological with the version letter) and
        `first_mentioned` (pos = the version whose answer is the first-mentioned candidate = the E2 ownership label; for
        mapping both versions of a pair share the flag, so the label is undefined within pair and is reported as such).
    (b) candidate-identity probe: one-vs-rest L2 logistic over the candidate vocabulary (standardised features, C from an
        inner 3-fold CV over {0.01, 0.1, 1}) trained on the training pairs' states; a held-out state is scored by
        logit[c_answer] − logit[c_other]; within-pair win = both states scored toward their own answer. LOO by pair,
        20-label-permutation null (answers permuted over the training states), two-half ceiling (pairs split by seed 0).
        PRESENT (identity) if LOO within-pair win ≥ 0.75, above the permutation 95th percentile, and ceiling ≥ 0.75.
    (c) PCA sanity: fraction of the variance of (h_A − h_B) across pairs carried by the first component (uncentred SVD,
        sign-agnostic, primary; centred PCA secondary).
R3  X3 re-analysis: (a) additive symbol-bias correction per reader (lo ≈ b[actual] − b[other], least squares over all
    400 puzzle rows, sum-to-zero); (b) trace-rule baseline and ERROR_OFFTRACE = errors whose answer is not on the trace;
    (c) 8-way multinomial identity probe for the model's ACTUAL symbol (5-fold by item, inner-CV C, 20-permutation null,
    two-half ceiling), the same for the CORRECT symbol, and a logistic probe for the E9 label actual == correct;
    (d) choice: word-identity probe (mostly unscorable: 95 words over 66 items) and a logistic actual == first-listed probe.
R4  Paired reader comparisons on the X1 E1 wins (exact binomial sign test on discordant pairs) per family and pooled.
Y0  friday_cases.md: all DISAGREE choice items, all ERROR_OFFTRACE puzzles, the shared-error check.

Usage: .venv/bin/python projects/g_agreement/x_friday_r2r4.py [--out results/g_agreement/x/friday] [--n-perm 20] [--n-boot 2000]
Writes r2_probes.csv, r3_x3.csv, r3_probe.csv, r4_paired.csv, friday_cases.md, R2R4.md, r2r4_summary.json.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.stats import wilson as _wilson  # noqa: E402
from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.x1_bank import analyze as X1A  # noqa: E402

READERS = ("jlens", "olens", "nla")
READER_LABEL = {"jlens": "J-lens", "olens": "Oracle", "nla": "NLA"}
BINDING_FAMILIES = ("ownership", "mapping")
X1_FAMILIES = ("ownership", "mapping", "language", "tense")
SYMBOLS = tuple("ABCDEFGH")
CS = (0.01, 0.1, 1.0)
N_PERM, N_BOOT, SEED = 20, 2000, 0
PRESENT_WIN, CEILING_MIN = 0.75, 0.75
G_DIR = ROOT / "projects" / "g_agreement"
DEFAULTS = {
    "items_x": G_DIR / "dataset" / "items_x.json",
    "x1_lo": ROOT / "cache" / "g_agreement" / "x" / "x1_lo.jsonl",
    "states": ROOT / "cache" / "g_agreement" / "states",
    "selected": G_DIR / "dataset" / "items_x3_selected.json",
    "x3_lo": ROOT / "cache" / "g_agreement" / "x" / "x3_lo.jsonl",
    "x3_target": ROOT / "cache" / "g_agreement" / "x" / "x3_target.jsonl",
    "out": ROOT / "results" / "g_agreement" / "x" / "friday",
}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=str(v))
    ap.add_argument("--n-perm", type=int, default=N_PERM)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--skip", default="", help="comma list of blocks to skip: r2,r3,r4,y0")
    ap.add_argument("--md-only", action="store_true", help="only regenerate R2R4.md from an existing r2r4_summary.json in --out")
    return ap.parse_args(argv)


# ====================================================================== stats helpers
def wilson(k: int, n: int) -> Tuple[float, float, float]:
    p, lo, hi = _wilson(k, n)
    if n == 0:
        return p, lo, hi
    return float(p), float(max(0.0, lo)), float(min(1.0, hi))


def boot_rate(flags: Sequence[bool], n_boot: int, seed: int) -> Tuple[float, float, float]:
    x = np.asarray([bool(f) for f in flags], dtype=float)
    if x.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    vals = x[rng.integers(0, x.size, size=(n_boot, x.size))].mean(axis=1)
    return float(x.mean()), float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def rate(flags: Sequence[bool], n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    flags = [bool(f) for f in flags]
    k, n = int(sum(flags)), len(flags)
    p, blo, bhi = boot_rate(flags, n_boot, seed)
    _, wlo, whi = wilson(k, n)
    return {"k": k, "n": n, "p": p, "boot_lo": blo, "boot_hi": bhi, "wilson_lo": wlo, "wilson_hi": whi}


def boot_diff(flags_a: Sequence[bool], flags_b: Sequence[bool], n_boot: int, seed: int) -> Tuple[float, float, float]:
    """Difference of two independent-set rates with an item bootstrap of each set."""
    a, b = np.asarray(flags_a, float), np.asarray(flags_b, float)
    if a.size == 0 or b.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    da = a[rng.integers(0, a.size, size=(n_boot, a.size))].mean(1) - b[rng.integers(0, b.size, size=(n_boot, b.size))].mean(1)
    return float(a.mean() - b.mean()), float(np.quantile(da, 0.025)), float(np.quantile(da, 0.975))


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    from scipy.stats import rankdata

    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = labels == 1, labels == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    r = rankdata(scores)
    return float((r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def _unit(u: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(u)
    return u / n if n > 0 else u


def fmt_rate(d: Mapping[str, Any]) -> str:
    if not d or not d.get("n"):
        return "n/a"
    return f"{d['k']}/{d['n']} = {100 * d['p']:.0f}% [{100 * d['boot_lo']:.0f}, {100 * d['boot_hi']:.0f}]"


# ====================================================================== logistic probe (span trick)
def _robust_svd(Xs: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """(s, Vt) of Xs. numpy's gesdd first (unchanged results on well-conditioned inputs); when it raises
    'SVD did not converge' (a LAPACK gesdd pathology seen on the Y1 bf16 captures), retry with the slower but
    more robust gesvd driver via scipy; re-raise LinAlgError when both fail."""
    try:
        _, s, Vt = np.linalg.svd(Xs, full_matrices=False)
        return s, Vt
    except np.linalg.LinAlgError as exc:
        try:
            import scipy.linalg

            _, s, Vt = scipy.linalg.svd(Xs, full_matrices=False, lapack_driver="gesvd")
            return s, Vt
        except Exception as exc2:  # noqa: BLE001 - surfaces as LinAlgError to the callers' guards
            raise np.linalg.LinAlgError(f"SVD did not converge (gesdd: {exc}; gesvd: {exc2})") from exc2


class SpanLogistic:
    """L2 logistic probe on standardised features, fit in the span of the training rows.

    For an L2-penalised logistic regression with unpenalised intercept the coefficient vector lies in the span of the
    training rows, so fitting on the coordinates Z = X_std · V^T (V = right singular vectors of the standardised training
    matrix) is exact and n-dimensional instead of d-dimensional. C is chosen by an inner k-fold CV (accuracy; ties go to
    the smallest C). `multi` is "ovr" (OneVsRestClassifier) or "multinomial" (LogisticRegression; binary when 2 classes).
    """

    def __init__(self, Cs: Sequence[float] = CS, inner_folds: int = 3, seed: int = SEED, multi: str = "multinomial", max_iter: int = 5000):
        self.Cs, self.inner_folds, self.seed, self.multi, self.max_iter = tuple(Cs), inner_folds, seed, multi, max_iter
        self.C: Optional[float] = None

    def _make(self, C: float):
        from sklearn.linear_model import LogisticRegression
        from sklearn.multiclass import OneVsRestClassifier

        lr = LogisticRegression(C=C, max_iter=self.max_iter)
        return OneVsRestClassifier(lr) if self.multi == "ovr" else lr

    def _folds(self, y: np.ndarray, k: int):
        from sklearn.model_selection import KFold, StratifiedKFold

        min_c = min(Counter(y.tolist()).values())
        k = min(k, len(y))
        if k < 2:
            return []
        if min_c >= k:
            return list(StratifiedKFold(k, shuffle=True, random_state=self.seed).split(np.zeros(len(y)), y))
        return list(KFold(k, shuffle=True, random_state=self.seed).split(np.zeros(len(y))))

    def _select_C(self, Z: np.ndarray, y: np.ndarray) -> float:
        best, best_acc = self.Cs[0], -1.0
        folds = self._folds(y, self.inner_folds)
        for C in self.Cs:
            accs = []
            for tr, te in folds:
                if len(set(y[tr].tolist())) < 2:
                    continue
                clf = self._make(C).fit(Z[tr], y[tr])
                accs.append(float((clf.predict(Z[te]) == y[te]).mean()))
            acc = float(np.mean(accs)) if accs else 0.0
            if acc > best_acc + 1e-12:
                best, best_acc = C, acc
        return best

    def fit(self, X: np.ndarray, y: Sequence[Any]) -> "SpanLogistic":
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y)
        if len(set(y.tolist())) < 2:
            raise ValueError("SpanLogistic needs at least two classes in the training labels")
        self.mu = X.mean(0)
        sd = X.std(0)
        sd[sd == 0] = 1.0
        self.sd = sd
        Xs = (X - self.mu) / self.sd
        s, Vt = _robust_svd(Xs)
        self.Vt = Vt[s > s.max() * 1e-10] if s.size else Vt
        Z = Xs @ self.Vt.T
        self.C = self._select_C(Z, y) if len(self.Cs) > 1 else float(self.Cs[0])
        self.clf = self._make(self.C).fit(Z, y)
        self.classes_ = [c.item() if hasattr(c, "item") else c for c in self.clf.classes_]
        self.index = {c: i for i, c in enumerate(self.classes_)}
        return self

    def logits(self, X: np.ndarray) -> np.ndarray:
        """(n, n_classes) decision values aligned with classes_ (binary: column 0 is 0, column 1 the decision)."""
        Z = ((np.asarray(X, dtype=np.float64) - self.mu) / self.sd) @ self.Vt.T
        d = self.clf.decision_function(Z)
        if d.ndim == 1:
            d = np.column_stack([np.zeros_like(d), d])
        return d

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.clf.predict(((np.asarray(X, dtype=np.float64) - self.mu) / self.sd) @ self.Vt.T)

    def pair_scores(self, X: np.ndarray, a: Sequence[Any], b: Sequence[Any]) -> np.ndarray:
        """logit[a_i] − logit[b_i] per row; nan where a class was not in the training labels."""
        L = self.logits(X)
        out = np.full(L.shape[0], np.nan)
        for i, (ai, bi) in enumerate(zip(a, b)):
            if ai in self.index and bi in self.index:
                out[i] = L[i, self.index[ai]] - L[i, self.index[bi]]
        return out


# ====================================================================== R2
def load_x1(items_path, states_dir, split: str = "test", families: Sequence[str] = BINDING_FAMILIES) -> Dict[str, dict]:
    """{family: {"pairs": [pair dicts with states], "H": {item_id: vec}, "missing": [...]}} (reuses the X1 loaders)."""
    _, items = U.load_items(items_path)
    pairs = X1A.load_pairs(items, split)
    out = {}
    for fam in families:
        H, missing = X1A.load_states(pairs[fam], Path(states_dir))
        usable = [p for p in pairs[fam] if all(p[v]["item_id"] in H for v in "AB")]
        out[fam] = {"pairs": usable, "H": H, "missing": missing, "n_pairs_total": len(pairs[fam])}
    return out


def label_table(pairs: List[dict]) -> dict:
    """What the version letter coincides with, per family (all counts over pairs)."""
    n = len(pairs)
    return {
        "n_pairs": n,
        "A_has_answer_position_0": sum(p["A"]["construction"].get("answer_position") == 0 for p in pairs),
        "A_answer_is_candidates0": sum(p["A"]["primary"]["answer"] == p["A"]["primary"]["candidates"][0] for p in pairs),
        "A_answer_first_mentioned": sum(bool(p["A"]["construction"].get("answer_is_first_mentioned")) for p in pairs),
        "mention_order_differs_within_pair": sum(bool(p["A"]["construction"].get("answer_is_first_mentioned"))
                                                 != bool(p["B"]["construction"].get("answer_is_first_mentioned")) for p in pairs),
        "candidates0_alphabetically_first": sum(str(p["A"]["primary"]["candidates"][0]) < str(p["A"]["primary"]["candidates"][1]) for p in pairs),
    }


def contrast_pos_version(pair: dict, label: str) -> Optional[str]:
    if label == "version":
        return "A"
    if label == "first_mentioned":
        fa = bool(pair["A"]["construction"].get("answer_is_first_mentioned"))
        fb = bool(pair["B"]["construction"].get("answer_is_first_mentioned"))
        if fa == fb:
            return None
        return "A" if fa else "B"
    raise ValueError(label)


def contrast_probe(pairs: List[dict], H: Mapping[str, np.ndarray], label: str, n_boot: int, seed: int) -> dict:
    """Within-pair contrast probe (R2a): LOO by pair and the two-half ceiling."""
    diffs: Dict[str, np.ndarray] = {}
    for p in pairs:
        pv = contrast_pos_version(p, label)
        if pv is None:
            continue
        nv = "B" if pv == "A" else "A"
        diffs[p["pair_id"]] = H[p[pv]["item_id"]] - H[p[nv]["item_id"]]
    pids = list(diffs)
    rec = {"label": label, "n_pairs": len(pairs), "n_labelable": len(pids)}
    if len(pids) < 3:
        rec.update(status="undefined within pair (fewer than 3 labelable pairs)", loo=rate([], n_boot, seed), ceiling=rate([], n_boot, seed))
        return rec
    wins = {}
    for pid in pids:
        u = _unit(np.mean([diffs[q] for q in pids if q != pid], axis=0))
        wins[pid] = bool(u @ diffs[pid] > 0)
    rng = np.random.default_rng(seed)
    order = [pids[i] for i in rng.permutation(len(pids))]
    h1, h2 = order[: len(order) // 2], order[len(order) // 2:]
    ceil_flags, halves = [], {}
    for name, tr, te in (("half1_to_half2", h1, h2), ("half2_to_half1", h2, h1)):
        u = _unit(np.mean([diffs[q] for q in tr], axis=0))
        f = [bool(u @ diffs[q] > 0) for q in te]
        halves[name] = float(np.mean(f)) if f else float("nan")
        ceil_flags += f
    rec.update(status="ok", loo=rate(list(wins.values()), n_boot, seed), ceiling=rate(ceil_flags, n_boot, seed), **halves,
               per_pair=wins)
    return rec


def _states_of(pairs: Iterable[dict], H: Mapping[str, np.ndarray]) -> Tuple[np.ndarray, List[str], List[Any]]:
    ids = [p[v]["item_id"] for p in pairs for v in "AB"]
    X = np.stack([H[i] for i in ids]) if ids else np.zeros((0, 1))
    return X, ids, [p[v]["primary"]["answer"] for p in pairs for v in "AB"]


def identity_fit_score(train: List[dict], test: List[dict], H: Mapping[str, np.ndarray], Cs: Sequence[float], seed: int,
                       labels: Optional[Mapping[str, Any]] = None) -> Tuple[Dict[str, Tuple[float, float]], float]:
    """Fit the one-vs-rest identity probe on the training pairs' states (labels = answers, or `labels[item_id]` when
    given, e.g. a permutation) and score each test state by logit[c_answer] − logit[c_other]. Returns {pair_id: (sA, sB)}
    (nan when a candidate was absent from the training labels) and the selected C."""
    Xtr, ids_tr, ytr = _states_of(train, H)
    if labels is not None:
        ytr = [labels[i] for i in ids_tr]
    clf = SpanLogistic(Cs=Cs, seed=seed, multi="ovr").fit(Xtr, ytr)
    Xte, _, _ = _states_of(test, H)
    a = [p[v]["primary"]["answer"] for p in test for v in "AB"]
    b = [[c for c in p[v]["primary"]["candidates"] if c != p[v]["primary"]["answer"]][0] for p in test for v in "AB"]
    sc = clf.pair_scores(Xte, a, b)
    out = {p["pair_id"]: (float(sc[2 * i]), float(sc[2 * i + 1])) for i, p in enumerate(test)}
    return out, float(clf.C)


def _pair_wins(scored: Mapping[str, Tuple[float, float]]) -> Tuple[List[bool], List[bool], int]:
    """(within-pair wins = both states toward their own answer, per-state wins, n unscorable pairs) over pairs with both
    scores finite."""
    pw, sw, skipped = [], [], 0
    for sa, sb in scored.values():
        if not (np.isfinite(sa) and np.isfinite(sb)):
            skipped += 1
            continue
        pw.append(bool(sa > 0 and sb > 0))
        sw += [bool(sa > 0), bool(sb > 0)]
    return pw, sw, skipped


def _paired_sum_wins(scored: Mapping[str, Tuple[float, float]]) -> List[bool]:
    """Paired-contrast win sA + sB > 0: the probe analogue of the readers' E1 win lo_A + lo_B > 0 (cancels a per-pair
    candidate prior that pushes both states the same way)."""
    return [bool(sa + sb > 0) for sa, sb in scored.values() if np.isfinite(sa) and np.isfinite(sb)]


def identity_probe(pairs: List[dict], H: Mapping[str, np.ndarray], n_perm: int, n_boot: int, seed: int, Cs: Sequence[float] = CS) -> dict:
    """R2b: LOO-by-pair identity probe, label-permutation null and two-half ceiling."""
    pids = [p["pair_id"] for p in pairs]
    vocab = sorted({p[v]["primary"]["answer"] for p in pairs for v in "AB"}, key=str)
    rec: dict = {"n_pairs": len(pairs), "vocab_size": len(vocab), "Cs": list(Cs)}
    if len(pairs) < 3:
        rec.update(status="skipped (fewer than 3 pairs)")
        return rec
    loo: Dict[str, Tuple[float, float]] = {}
    Cs_used = []
    for i, p in enumerate(pairs):
        sc, C = identity_fit_score([q for q in pairs if q["pair_id"] != p["pair_id"]], [p], H, Cs, seed)
        loo.update(sc)
        Cs_used.append(C)
    pw, sw, skipped = _pair_wins(loo)
    rec.update(status="ok", loo=rate(pw, n_boot, seed), loo_per_state=rate(sw, n_boot, seed), loo_paired_sum=rate(_paired_sum_wins(loo), n_boot, seed),
               loo_n_unscorable_pairs=skipped,
               C_modal=Counter(Cs_used).most_common(1)[0][0], C_counts=dict(Counter(Cs_used)),
               loo_per_pair={pid: {"score_A": s[0], "score_B": s[1], "win": bool(np.isfinite(s[0]) and np.isfinite(s[1]) and s[0] > 0 and s[1] > 0)}
                             for pid, s in loo.items()})
    # permutation null: answers permuted over all states of the family, then the same LOO
    all_ids = [p[v]["item_id"] for p in pairs for v in "AB"]
    all_y = [p[v]["primary"]["answer"] for p in pairs for v in "AB"]
    rng = np.random.default_rng(seed + 1)
    null_pair, null_state, null_sum = [], [], []
    for _ in range(n_perm):
        perm = dict(zip(all_ids, rng.permutation(all_y).tolist()))
        sc_all: Dict[str, Tuple[float, float]] = {}
        for p in pairs:
            sc, _ = identity_fit_score([q for q in pairs if q["pair_id"] != p["pair_id"]], [p], H, Cs, seed, labels=perm)
            sc_all.update(sc)
        npw, nsw, _ = _pair_wins(sc_all)
        nps = _paired_sum_wins(sc_all)
        null_pair.append(float(np.mean(npw)) if npw else float("nan"))
        null_state.append(float(np.mean(nsw)) if nsw else float("nan"))
        null_sum.append(float(np.mean(nps)) if nps else float("nan"))

    def _q(v, q):
        return float(np.nanquantile(v, q)) if len(v) else float("nan")

    rec["perm_null"] = {"n_perm": n_perm, "pair_win_values": null_pair, "pair_win_mean": float(np.nanmean(null_pair)) if null_pair else float("nan"),
                        "pair_win_p95": _q(null_pair, 0.95), "pair_win_max": float(np.nanmax(null_pair)) if null_pair else float("nan"),
                        "state_win_mean": float(np.nanmean(null_state)) if null_state else float("nan"), "state_win_p95": _q(null_state, 0.95),
                        "paired_sum_win_mean": float(np.nanmean(null_sum)) if null_sum else float("nan"), "paired_sum_win_p95": _q(null_sum, 0.95)}
    # two-half ceiling
    rng = np.random.default_rng(seed)
    order = [pairs[i] for i in rng.permutation(len(pairs))]
    h1, h2 = order[: len(order) // 2], order[len(order) // 2:]
    ceil_sc: Dict[str, Tuple[float, float]] = {}
    halves = {}
    for name, tr, te in (("half1_to_half2", h1, h2), ("half2_to_half1", h2, h1)):
        sc, _ = identity_fit_score(tr, te, H, Cs, seed)
        ceil_sc.update(sc)
        cpw, _, csk = _pair_wins(sc)
        halves[name] = {"win": float(np.mean(cpw)) if cpw else float("nan"), "n_scored": len(cpw), "n_unscorable": csk}
    cpw, csw, csk = _pair_wins(ceil_sc)
    rec["ceiling"] = {"pooled": rate(cpw, n_boot, seed), "per_state": rate(csw, n_boot, seed), "paired_sum": rate(_paired_sum_wins(ceil_sc), n_boot, seed),
                      "n_unscorable_pairs": csk, **halves}
    l, c, nz = rec["loo"], rec["ceiling"]["pooled"], rec["perm_null"]
    rec["present_identity"] = bool(l["n"] and l["p"] >= PRESENT_WIN and l["p"] > nz["pair_win_p95"] and c["n"] and c["p"] >= CEILING_MIN)
    rec["decision_rule"] = f"PRESENT (identity) if LOO within-pair win >= {PRESENT_WIN}, above the {n_perm}-permutation 95th percentile, and two-half ceiling >= {CEILING_MIN}"
    return rec


def pca_diffs(pairs: List[dict], H: Mapping[str, np.ndarray]) -> dict:
    """R2c: how much of the within-pair difference is one direction."""
    D = np.stack([H[p["A"]["item_id"]] - H[p["B"]["item_id"]] for p in pairs])
    s = np.linalg.svd(D, compute_uv=False)
    sc = np.linalg.svd(D - D.mean(0), compute_uv=False)
    norms = np.linalg.norm(D, axis=1)
    _, _, Vt = np.linalg.svd(D, full_matrices=False)
    pc1 = Vt[0]
    cos_pc1 = D @ pc1 / np.where(norms > 0, norms, 1)
    out = {"n_pairs": len(pairs), "pc1_frac_uncentred": float(s[0] ** 2 / (s ** 2).sum()), "pc1_frac_centred": float(sc[0] ** 2 / (sc ** 2).sum()),
           "mean_abs_cos_with_pc1": float(np.mean(np.abs(cos_pc1))), "frac_pairs_pc1_positive": float(np.mean(cos_pc1 > 0)),
           "uniform_frac_reference": float(1.0 / min(D.shape))}
    aligned = []
    for p in pairs:
        pv = contrast_pos_version(p, "first_mentioned")
        if pv is not None:
            nv = "B" if pv == "A" else "A"
            aligned.append(H[p[pv]["item_id"]] - H[p[nv]["item_id"]])
    if len(aligned) >= 3:
        A = np.stack(aligned)
        m = _unit(A.mean(0))
        out["first_mentioned_aligned"] = {"n_pairs": len(aligned), "mean_cos_with_mean_diff": float(np.mean(A @ m / np.linalg.norm(A, axis=1))),
                                          "mean_diff_frac_of_energy": float(np.linalg.norm(A.mean(0)) ** 2 / np.mean(np.linalg.norm(A, axis=1) ** 2))}
    return out


def r2_family(fam: str, pairs: List[dict], H: Mapping[str, np.ndarray], n_perm: int, n_boot: int, seed: int) -> dict:
    t = time.time()
    rec = {"family": fam, "labels": label_table(pairs),
           "contrast": {lab: contrast_probe(pairs, H, lab, n_boot, seed) for lab in ("version", "first_mentioned")},
           "identity": identity_probe(pairs, H, n_perm, n_boot, seed), "pca": pca_diffs(pairs, H)}
    lt = rec["labels"]
    rec["label_note"] = (f"version A has answer_position 0 (= candidates[0]) in {lt['A_has_answer_position_0']}/{lt['n_pairs']} pairs (tautological); "
                         f"A's answer is first-mentioned in {lt['A_answer_first_mentioned']}/{lt['n_pairs']} pairs; mention order differs within pair in "
                         f"{lt['mention_order_differs_within_pair']}/{lt['n_pairs']} pairs; candidates[0] alphabetically first in {lt['candidates0_alphabetically_first']}/{lt['n_pairs']}")
    rec["wall_s"] = time.time() - t
    return rec


def r2_rows(r2: Mapping[str, dict]) -> List[dict]:
    rows = []
    for fam, rec in r2.items():
        for lab, c in rec["contrast"].items():
            rows.append({"family": fam, "probe": f"contrast_{lab}", "status": c.get("status"), "n_pairs": c["n_pairs"], "n_scored": c["loo"]["n"],
                         "loo_k": c["loo"]["k"], "loo_win": c["loo"]["p"], "loo_boot_lo": c["loo"]["boot_lo"], "loo_boot_hi": c["loo"]["boot_hi"],
                         "loo_wilson_lo": c["loo"]["wilson_lo"], "loo_wilson_hi": c["loo"]["wilson_hi"], "per_state_win": "",
                         "paired_sum_win": "", "paired_sum_null_p95": "", "paired_sum_ceiling": "",
                         "perm_null_mean": "", "perm_null_p95": "", "perm_null_max": "", "ceiling_win": c["ceiling"]["p"], "ceiling_n": c["ceiling"]["n"],
                         "ceiling_half1_to_half2": c.get("half1_to_half2", ""), "ceiling_half2_to_half1": c.get("half2_to_half1", ""), "C_modal": "",
                         "pca_pc1_frac_uncentred": rec["pca"]["pc1_frac_uncentred"], "pca_pc1_frac_centred": rec["pca"]["pc1_frac_centred"],
                         "present_identity": ""})
        i = rec["identity"]
        if i.get("status") == "ok":
            rows.append({"family": fam, "probe": "identity_logistic_ovr", "status": "ok", "n_pairs": i["n_pairs"], "n_scored": i["loo"]["n"],
                         "loo_k": i["loo"]["k"], "loo_win": i["loo"]["p"], "loo_boot_lo": i["loo"]["boot_lo"], "loo_boot_hi": i["loo"]["boot_hi"],
                         "loo_wilson_lo": i["loo"]["wilson_lo"], "loo_wilson_hi": i["loo"]["wilson_hi"], "per_state_win": i["loo_per_state"]["p"],
                         "paired_sum_win": i["loo_paired_sum"]["p"], "paired_sum_null_p95": i["perm_null"]["paired_sum_win_p95"], "paired_sum_ceiling": i["ceiling"]["paired_sum"]["p"],
                         "perm_null_mean": i["perm_null"]["pair_win_mean"], "perm_null_p95": i["perm_null"]["pair_win_p95"], "perm_null_max": i["perm_null"]["pair_win_max"],
                         "ceiling_win": i["ceiling"]["pooled"]["p"], "ceiling_n": i["ceiling"]["pooled"]["n"],
                         "ceiling_half1_to_half2": i["ceiling"]["half1_to_half2"]["win"], "ceiling_half2_to_half1": i["ceiling"]["half2_to_half1"]["win"],
                         "C_modal": i["C_modal"], "pca_pc1_frac_uncentred": rec["pca"]["pc1_frac_uncentred"], "pca_pc1_frac_centred": rec["pca"]["pc1_frac_centred"],
                         "present_identity": i["present_identity"]})
    return rows


# ====================================================================== R3
def load_x3(selected_path, lo_path, target_path) -> Tuple[Dict[str, dict], Dict[str, Dict[str, dict]], Dict[str, dict]]:
    items = {it["item_id"]: it for it in U.load_json(selected_path)["items"]}
    by_reader: Dict[str, Dict[str, dict]] = {r: {} for r in READERS}
    for r in (U.load_jsonl(lo_path) if Path(lo_path).exists() else []):
        if r.get("reader") in by_reader and r.get("item_id") in items:
            by_reader[r["reader"]][r["item_id"]] = r
    trows = {r["item_id"]: r for r in (U.load_jsonl(target_path) if Path(target_path).exists() else [])}
    return items, by_reader, trows


def fit_pair_bias(actual: Sequence[Any], other: Sequence[Any], lo: Sequence[float], vocab: Sequence[Any]) -> Tuple[Dict[Any, float], np.ndarray, float]:
    """Least squares lo ≈ b[actual] − b[other] over a vocabulary; min-norm solution, re-centred to sum zero.
    Returns (bias dict, corrected lo, R²)."""
    idx = {v: i for i, v in enumerate(vocab)}
    X = np.zeros((len(lo), len(vocab)))
    for i, (a, o) in enumerate(zip(actual, other)):
        X[i, idx[a]] += 1.0
        X[i, idx[o]] -= 1.0
    y = np.asarray(lo, float)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    b = b - b.mean()
    fitted = X @ b
    ss_res, ss_tot = float(((y - fitted) ** 2).sum()), float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {v: float(b[i]) for v, i in idx.items()}, y - fitted, r2


def reader_rows(items: Mapping[str, dict], rows: Mapping[str, dict], family: str) -> List[dict]:
    """Scorable LO rows of one reader on one family, each with item_id, set, actual, other, lo."""
    out = []
    for iid in sorted(items):
        it = items[iid]
        r = rows.get(iid)
        if it["family"] != family or r is None or r.get("lo_actual") is None:
            continue
        out.append({"item_id": iid, "set": it["set"], "actual": it["primary"]["candidates"][0], "other": it["primary"]["candidates"][1], "lo": float(r["lo_actual"])})
    return out


def r3a_symbol_bias(items: Mapping[str, dict], by_reader: Mapping[str, Mapping[str, dict]], n_boot: int, seed: int) -> dict:
    """R3a: additive symbol-bias correction on puzzles (8 symbols, all rows); choice gets a position-bias correction
    because a per-word bias is not estimable (words appear 1–3 times)."""
    out: dict = {"puzzle": {}, "choice": {}}
    for reader in READERS:
        rows = reader_rows(items, by_reader[reader], "puzzle")
        if len(rows) < 16:
            out["puzzle"][reader] = {"status": f"skipped ({len(rows)} scorable rows)"}
            continue
        vocab = sorted({r["actual"] for r in rows} | {r["other"] for r in rows})
        bias, corr, r2 = fit_pair_bias([r["actual"] for r in rows], [r["other"] for r in rows], [r["lo"] for r in rows], vocab)
        rec = {"status": "ok", "n_rows": len(rows), "vocab": vocab, "bias": bias, "bias_range": float(max(bias.values()) - min(bias.values())), "r2": r2, "sets": {}}
        for s in ("error", "error_control"):
            m = [r["set"] == s for r in rows]
            raw = [r["lo"] > 0 for r, k in zip(rows, m) if k]
            cor = [c > 0 for c, k in zip(corr, m) if k]
            rec["sets"][s] = {"raw": rate(raw, n_boot, seed), "corrected": rate(cor, n_boot, seed)}
        e, c = rec["sets"]["error"], rec["sets"]["error_control"]
        rec["error_minus_control_raw"] = boot_diff([r["lo"] > 0 for r in rows if r["set"] == "error"], [r["lo"] > 0 for r in rows if r["set"] == "error_control"], n_boot, seed)
        rec["error_minus_control_corrected"] = boot_diff([x > 0 for x, r in zip(corr, rows) if r["set"] == "error"], [x > 0 for x, r in zip(corr, rows) if r["set"] == "error_control"], n_boot, seed)
        rec["corrected_lo"] = {r["item_id"]: float(x) for r, x in zip(rows, corr)}
        out["puzzle"][reader] = rec
    # choice
    for reader in READERS:
        rows = reader_rows(items, by_reader[reader], "choice")
        if len(rows) < 8:
            out["choice"][reader] = {"status": f"skipped ({len(rows)} scorable rows)"}
            continue
        wc = Counter([r["actual"] for r in rows] + [r["other"] for r in rows])
        rec = {"status": "ok", "n_rows": len(rows), "n_words": len(wc), "min_rows_per_word": min(wc.values()), "median_rows_per_word": float(np.median(list(wc.values()))),
               "per_word_bias": "not estimable: %d words over %d rows (median %.0f rows per word); position bias fitted instead" % (len(wc), len(rows), np.median(list(wc.values())))}
        sign = np.array([1.0 if (items[r["item_id"]].get("source") or {}).get("first_listed") == r["actual"] else -1.0 for r in rows])
        lo = np.array([r["lo"] for r in rows])
        s_hat = float((lo * sign).mean())
        corr = lo - s_hat * sign
        rec["position_bias_nats"] = s_hat
        rec["sets"] = {}
        for s in ("disagree", "agree_control"):
            m = np.array([r["set"] == s for r in rows])
            rec["sets"][s] = {"raw": rate((lo[m] > 0).tolist(), n_boot, seed), "corrected": rate((corr[m] > 0).tolist(), n_boot, seed)}
        rec["corrected_lo"] = {r["item_id"]: float(x) for r, x in zip(rows, corr)}
        out["choice"][reader] = rec
    return out


def trace_rule(items: Mapping[str, dict], trows: Mapping[str, dict]) -> dict:
    """R3b: where the model's wrong puzzle answer sits relative to its own trace."""
    cats: Counter = Counter()
    offtrace, mismatch, per_item = [], 0, {}
    for iid in sorted(items):
        it = items[iid]
        if it["family"] != "puzzle" or it["set"] != "error":
            continue
        trace = list(it["source"]["trace"])
        ans = it["primary"]["answer"]
        parsed = (trows.get(iid) or {}).get("parsed", ans)
        if parsed != ans:
            mismatch += 1
        if ans == trace[-1]:
            cat = "equals_correct (not an error)"
        elif ans == trace[-2]:
            cat = "trace[-2] (k-1 symbol)"
        elif len(trace) >= 3 and ans == trace[-3]:
            cat = "trace[-3] (k-2 symbol)"
        elif ans in trace[:-1]:
            cat = "other on-trace"
        else:
            cat = "off-trace"
            offtrace.append(iid)
        cats[cat] += 1
        per_item[iid] = cat
    n = sum(cats.values())
    return {"n_errors": n, "counts": dict(cats), "fractions": {k: v / n for k, v in cats.items()} if n else {},
            "n_on_trace": n - len(offtrace), "offtrace_ids": offtrace, "n_decode_mismatch": mismatch, "per_item": per_item}


def r3b_offtrace(items: Mapping[str, dict], by_reader: Mapping[str, Mapping[str, dict]], bias: Mapping[str, dict], offtrace_ids: Sequence[str],
                 n_boot: int, seed: int) -> dict:
    out = {"n_offtrace": len(offtrace_ids), "readers": {}}
    for reader in READERS:
        rows = [r for r in reader_rows(items, by_reader[reader], "puzzle") if r["item_id"] in set(offtrace_ids)]
        corr = (bias.get(reader) or {}).get("corrected_lo") or {}
        out["readers"][reader] = {"n_scored": len(rows), "raw": rate([r["lo"] > 0 for r in rows], n_boot, seed),
                                  "corrected": rate([corr[r["item_id"]] > 0 for r in rows if r["item_id"] in corr], n_boot, seed)}
    return out


def _outer_folds(y: np.ndarray, n_folds: int, seed: int):
    from sklearn.model_selection import KFold, StratifiedKFold

    k = min(n_folds, len(y))
    if min(Counter(y.tolist()).values()) >= k and len(set(y.tolist())) > 1:
        return list(StratifiedKFold(k, shuffle=True, random_state=seed).split(np.zeros(len(y)), y))
    return list(KFold(k, shuffle=True, random_state=seed).split(np.zeros(len(y))))


def _cv_scores(X: np.ndarray, y: np.ndarray, folds, pair_scores: Mapping[str, Tuple[Sequence[Any], Sequence[Any]]], Cs, seed, multi) -> dict:
    """Held-out predictions and named pairwise scores over the folds."""
    n = len(y)
    pred = np.empty(n, dtype=object)
    sc = {name: np.full(n, np.nan) for name in pair_scores}
    bin_score = np.full(n, np.nan)
    Cs_used = []
    for tr, te in folds:
        clf = SpanLogistic(Cs=Cs, seed=seed, multi=multi).fit(X[tr], y[tr])
        Cs_used.append(clf.C)
        pred[te] = clf.predict(X[te])
        for name, (a, b) in pair_scores.items():
            sc[name][te] = clf.pair_scores(X[te], [a[i] for i in te], [b[i] for i in te])
        if len(clf.classes_) == 2:
            L = clf.logits(X[te])
            bin_score[te] = L[:, 1] - L[:, 0]
    return {"pred": pred, "scores": sc, "bin_score": bin_score, "Cs": Cs_used}


def cv_probe(X: np.ndarray, y: Sequence[Any], sets: Sequence[str], pair_scores: Mapping[str, Tuple[Sequence[Any], Sequence[Any]]],
             n_folds: int = 5, n_perm: int = N_PERM, n_boot: int = N_BOOT, seed: int = SEED, Cs: Sequence[float] = CS, multi: str = "multinomial",
             group_sets: Sequence[str] = ()) -> dict:
    """Generic k-fold-by-item probe with a label-permutation null and a two-half ceiling.

    X (n, d); y: the probe target per item; sets: set name per item (for per-set rates); pair_scores: {name: (a, b)} with
    a, b label sequences: the rate P(logit[a] − logit[b] > 0) is reported overall and per set. AUROC is added when y is
    binary (positive class = the larger label)."""
    X = np.asarray(X, float)
    y = np.asarray(y)
    sets = np.asarray(sets)
    n = len(y)
    set_names = list(group_sets) or sorted(set(sets.tolist()))
    counts = Counter(y.tolist())
    rec: dict = {"n_items": n, "n_classes": len(counts), "class_counts": {str(k): v for k, v in counts.items()},
                 "majority_rate": max(counts.values()) / n, "n_folds": n_folds, "multi": multi, "Cs": list(Cs)}
    if n < 2 * n_folds or len(counts) < 2:
        rec["status"] = "skipped (too few items or a single class)"
        return rec
    folds = _outer_folds(y, n_folds, seed)

    def summarise(res: dict, yy: np.ndarray) -> dict:
        out = {"accuracy": rate((res["pred"] == yy).tolist(), n_boot, seed), "C_counts": {str(k): v for k, v in Counter(res["Cs"]).items()}, "pair": {}}
        for name, s in res["scores"].items():
            ok = np.isfinite(s)
            out["pair"][name] = {"overall": rate((s[ok] > 0).tolist(), n_boot, seed), "n_unscorable": int((~ok).sum()), "by_set": {}}
            for sn in set_names:
                m = ok & (sets == sn)
                out["pair"][name]["by_set"][sn] = rate((s[m] > 0).tolist(), n_boot, seed)
        if len(set(yy.tolist())) == 2 and np.isfinite(res["bin_score"]).any():
            pos = max(set(yy.tolist()))
            out["auroc"] = auroc(res["bin_score"], (yy == pos).astype(int))
            out["auroc_by_set"] = {sn: auroc(res["bin_score"][sets == sn], (yy[sets == sn] == pos).astype(int)) for sn in set_names}
        return out

    res = _cv_scores(X, y, folds, pair_scores, Cs, seed, multi)
    rec["held_out"] = summarise(res, y)
    rec["held_out_scores"] = {name: s.tolist() for name, s in res["scores"].items()}
    rec["held_out_pred"] = [str(p) for p in res["pred"]]
    # permutation null
    rng = np.random.default_rng(seed + 1)
    null: Dict[str, List[float]] = defaultdict(list)
    for _ in range(n_perm):
        yp = rng.permutation(y)
        fp = _outer_folds(yp, n_folds, seed)
        rp = _cv_scores(X, yp, fp, pair_scores, Cs, seed, multi)
        null["accuracy"].append(float((rp["pred"] == y).mean()))
        for name, s in rp["scores"].items():
            ok = np.isfinite(s)
            null[f"{name}_overall"].append(float((s[ok] > 0).mean()) if ok.any() else float("nan"))
            for sn in set_names:
                m = ok & (sets == sn)
                null[f"{name}_{sn}"].append(float((s[m] > 0).mean()) if m.any() else float("nan"))
        if len(set(y.tolist())) == 2 and np.isfinite(rp["bin_score"]).any():
            null["auroc"].append(auroc(rp["bin_score"], (y == max(set(y.tolist()))).astype(int)))
    rec["perm_null"] = {"n_perm": n_perm, **{k: {"mean": float(np.nanmean(v)), "p95": float(np.nanquantile(v, 0.95)), "max": float(np.nanmax(v))}
                                           for k, v in null.items() if len(v)}}
    # two-half ceiling: halves by seed (stratified when possible), fit on one, evaluate on the other, both ways
    half_folds = _outer_folds(y, 2, seed)
    if len(half_folds) == 2:
        (i0, i1), (j0, j1) = half_folds[0], half_folds[1]
        # StratifiedKFold(2) gives (train=half B, test=half A) and (train=half A, test=half B): exactly the two directions
        rc = _cv_scores(X, y, half_folds, pair_scores, Cs, seed, multi)
        rec["ceiling"] = summarise(rc, y)
        rec["ceiling"]["halves"] = {}
        for name, (tr, te) in zip(("half1_to_half2", "half2_to_half1"), half_folds):
            rec["ceiling"]["halves"][name] = {"n_fit": int(len(tr)), "n_eval": int(len(te)), "accuracy": float((rc["pred"][te] == y[te]).mean()),
                                               **{pn: float((rc["scores"][pn][te][np.isfinite(rc["scores"][pn][te])] > 0).mean()) if np.isfinite(rc["scores"][pn][te]).any() else float("nan")
                                                  for pn in pair_scores}}
    rec["status"] = "ok"
    return rec


def load_states_matrix(ids: Sequence[str], states_dir) -> Tuple[np.ndarray, List[str]]:
    import torch

    X, kept = [], []
    for i in ids:
        f = Path(states_dir) / f"{i}.pt"
        if f.exists():
            X.append(torch.load(f, map_location="cpu").float().numpy().astype(np.float64))
            kept.append(i)
    return (np.stack(X) if X else np.zeros((0, 1))), kept


def r3c_puzzle_probes(items: Mapping[str, dict], states_dir, n_perm: int, n_boot: int, seed: int, n_folds: int = 5) -> dict:
    ids = sorted(i for i, it in items.items() if it["family"] == "puzzle")
    X, ids = load_states_matrix(ids, states_dir)
    out: dict = {"n_items": len(ids)}
    if len(ids) < 16:
        out["status"] = f"skipped ({len(ids)} puzzle states)"
        return out
    actual = [items[i]["primary"]["candidates"][0] for i in ids]
    other = [items[i]["primary"]["candidates"][1] for i in ids]
    correct = [items[i]["source"]["correct"] for i in ids]
    sets = [items[i]["set"] for i in ids]
    alt_for_correct = [a if s == "error" else o for a, o, s in zip(actual, other, sets)]  # the paired alternative to the correct symbol
    t = time.time()
    out["actual_symbol"] = cv_probe(X, actual, sets, {"favours_actual": (actual, other)}, n_folds, n_perm, n_boot, seed, CS, "multinomial",
                                    group_sets=("error", "error_control"))
    out["actual_symbol"]["label"] = "model's ACTUAL answer symbol (8-way)"
    out["correct_symbol"] = cv_probe(X, correct, sets, {"favours_actual": (actual, other), "favours_correct_over_alt": (correct, alt_for_correct)},
                                     n_folds, n_perm, n_boot, seed, CS, "multinomial", group_sets=("error", "error_control"))
    out["correct_symbol"]["label"] = "CORRECT symbol (8-way; text-derivable)"
    y_e9 = [int(a == c) for a, c in zip(actual, correct)]
    out["actual_eq_correct"] = cv_probe(X, y_e9, sets, {}, n_folds, n_perm, n_boot, seed, CS, "multinomial", group_sets=("error", "error_control"))
    out["actual_eq_correct"]["label"] = "actual == correct (E9 label, logistic)"
    out["ids"] = ids
    out["wall_s"] = time.time() - t
    out["status"] = "ok"
    return out


def r3d_choice_probes(items: Mapping[str, dict], states_dir, n_perm: int, n_boot: int, seed: int, n_folds: int = 5) -> dict:
    ids = sorted(i for i, it in items.items() if it["family"] == "choice")
    X, ids = load_states_matrix(ids, states_dir)
    out: dict = {"n_items": len(ids)}
    if len(ids) < 10:
        out["status"] = f"skipped ({len(ids)} choice states)"
        return out
    actual = [items[i]["primary"]["candidates"][0] for i in ids]
    other = [items[i]["primary"]["candidates"][1] for i in ids]
    sets = [items[i]["set"] for i in ids]
    first = [(items[i].get("source") or {}).get("first_listed") for i in ids]
    out["actual_word"] = cv_probe(X, actual, sets, {"favours_actual": (actual, other)}, n_folds, 0, n_boot, seed, CS, "ovr", group_sets=("disagree", "agree_control"))
    out["actual_word"]["label"] = "model's ACTUAL option word (one-vs-rest over words)"
    y_pos = [int(a == f) for a, f in zip(actual, first)]
    out["actual_is_first_listed"] = cv_probe(X, y_pos, sets, {}, n_folds, n_perm, n_boot, seed, CS, "multinomial", group_sets=("disagree", "agree_control"))
    out["actual_is_first_listed"]["label"] = "actual == first-listed option (E9 label, logistic)"
    out["ids"] = ids
    out["status"] = "ok"
    return out


def r3_x3_rows(bias: Mapping[str, dict], off: Mapping[str, dict]) -> List[dict]:
    rows = []
    for fam in ("puzzle", "choice"):
        for reader, rec in bias[fam].items():
            if rec.get("status") != "ok":
                rows.append({"family": fam, "reader": reader, "set": "", "status": rec.get("status")})
                continue
            for s, d in rec["sets"].items():
                rows.append({"family": fam, "reader": reader, "set": s, "status": "ok", "n": d["raw"]["n"],
                             "raw_k": d["raw"]["k"], "raw_p": d["raw"]["p"], "raw_boot_lo": d["raw"]["boot_lo"], "raw_boot_hi": d["raw"]["boot_hi"],
                             "raw_wilson_lo": d["raw"]["wilson_lo"], "raw_wilson_hi": d["raw"]["wilson_hi"],
                             "corr_k": d["corrected"]["k"], "corr_p": d["corrected"]["p"], "corr_boot_lo": d["corrected"]["boot_lo"], "corr_boot_hi": d["corrected"]["boot_hi"],
                             "corr_wilson_lo": d["corrected"]["wilson_lo"], "corr_wilson_hi": d["corrected"]["wilson_hi"],
                             "bias_model": "8 symbol biases, sum-to-zero, LS on all puzzle rows" if fam == "puzzle" else f"position bias {rec['position_bias_nats']:+.2f} nats (per-word not estimable)",
                             "bias_range_nats": rec.get("bias_range", ""), "bias_r2": rec.get("r2", "")})
    for reader, d in off["readers"].items():
        rows.append({"family": "puzzle", "reader": reader, "set": "error_offtrace", "status": "descriptive", "n": d["raw"]["n"],
                     "raw_k": d["raw"]["k"], "raw_p": d["raw"]["p"], "raw_boot_lo": d["raw"]["boot_lo"], "raw_boot_hi": d["raw"]["boot_hi"],
                     "raw_wilson_lo": d["raw"]["wilson_lo"], "raw_wilson_hi": d["raw"]["wilson_hi"],
                     "corr_k": d["corrected"]["k"], "corr_p": d["corrected"]["p"], "corr_boot_lo": d["corrected"]["boot_lo"], "corr_boot_hi": d["corrected"]["boot_hi"],
                     "corr_wilson_lo": d["corrected"]["wilson_lo"], "corr_wilson_hi": d["corrected"]["wilson_hi"],
                     "bias_model": "8 symbol biases, sum-to-zero, LS on all puzzle rows", "bias_range_nats": "", "bias_r2": ""})
    return rows


def r3_probe_rows(r3c: Mapping[str, Any], r3d: Mapping[str, Any]) -> List[dict]:
    rows = []
    for union, blk, sets in (("puzzle", r3c, ("error", "error_control")), ("choice", r3d, ("disagree", "agree_control"))):
        if blk.get("status") != "ok":
            rows.append({"union": union, "probe": "", "status": blk.get("status")})
            continue
        for name in [k for k in blk if isinstance(blk[k], dict) and "label" in blk[k]]:
            p = blk[name]
            if p.get("status") != "ok":
                rows.append({"union": union, "probe": name, "label": p.get("label"), "status": p.get("status")})
                continue
            ho, nz, ce = p["held_out"], p.get("perm_null", {}), p.get("ceiling", {})
            row = {"union": union, "probe": name, "label": p["label"], "status": "ok", "n_items": p["n_items"], "n_classes": p["n_classes"],
                   "majority_rate": p["majority_rate"], "accuracy": ho["accuracy"]["p"], "accuracy_boot_lo": ho["accuracy"]["boot_lo"], "accuracy_boot_hi": ho["accuracy"]["boot_hi"],
                   "accuracy_null_p95": (nz.get("accuracy") or {}).get("p95", ""), "accuracy_ceiling": (ce.get("accuracy") or {}).get("p", ""),
                   "auroc": ho.get("auroc", ""), "auroc_null_p95": (nz.get("auroc") or {}).get("p95", ""), "auroc_ceiling": ce.get("auroc", "")}
            for pn, d in ho["pair"].items():
                row[f"{pn}_overall"] = d["overall"]["p"]
                row[f"{pn}_n_unscorable"] = d["n_unscorable"]
                row[f"{pn}_null_p95"] = (nz.get(f"{pn}_overall") or {}).get("p95", "")
                row[f"{pn}_ceiling"] = ((ce.get("pair") or {}).get(pn) or {}).get("overall", {}).get("p", "")
                for sn in sets:
                    r = d["by_set"][sn]
                    row[f"{pn}_{sn}"] = r["p"]
                    row[f"{pn}_{sn}_k"] = r["k"]
                    row[f"{pn}_{sn}_n"] = r["n"]
                    row[f"{pn}_{sn}_boot_lo"] = r["boot_lo"]
                    row[f"{pn}_{sn}_boot_hi"] = r["boot_hi"]
                    row[f"{pn}_{sn}_null_p95"] = (nz.get(f"{pn}_{sn}") or {}).get("p95", "")
            if "auroc_by_set" in ho:
                for sn in sets:
                    row[f"auroc_{sn}"] = ho["auroc_by_set"][sn]
            rows.append(row)
    return rows


# ====================================================================== R4
def e1_wins(lo_rows: Sequence[dict], pairs_by_family: Mapping[str, List[dict]], readers: Sequence[str] = READERS) -> Dict[str, Dict[str, Dict[str, bool]]]:
    """{reader: {family: {pair_id: win}}} with win = lo_A + lo_B > 0 over scorable natural rows."""
    lo: Dict[str, Dict[str, dict]] = {r: {} for r in readers}
    for r in lo_rows:
        if r.get("reader") in lo and r.get("condition", "natural") == "natural" and "item_id" in r:
            lo[r["reader"]][r["item_id"]] = r
    out: Dict[str, Dict[str, Dict[str, bool]]] = {r: {} for r in readers}
    for rd in readers:
        for fam, pairs in pairs_by_family.items():
            w = {}
            for p in pairs:
                ra, rb = lo[rd].get(p["A"]["item_id"]), lo[rd].get(p["B"]["item_id"])
                if ra and rb and not ra.get("unscorable") and not rb.get("unscorable") and ra.get("lo") is not None and rb.get("lo") is not None:
                    w[p["pair_id"]] = bool(ra["lo"] + rb["lo"] > 0)
            out[rd][fam] = w
    return out


def paired_sign_rows(wins: Mapping[str, Mapping[str, Mapping[str, bool]]], families: Sequence[str], pooled: Mapping[str, Sequence[str]],
                     readers: Sequence[str] = READERS) -> List[dict]:
    from scipy.stats import binomtest

    groups = [(f, (f,)) for f in families] + list(pooled.items())
    rows = []
    for gname, fams in groups:
        for r1, r2 in itertools.combinations(readers, 2):
            w1 = {(f, pid): w for f in fams for pid, w in wins[r1].get(f, {}).items()}
            w2 = {(f, pid): w for f in fams for pid, w in wins[r2].get(f, {}).items()}
            common = sorted(set(w1) & set(w2))
            only1 = sum(w1[k] and not w2[k] for k in common)
            only2 = sum(w2[k] and not w1[k] for k in common)
            both = sum(w1[k] and w2[k] for k in common)
            neither = sum((not w1[k]) and (not w2[k]) for k in common)
            nd = only1 + only2
            p = float(binomtest(only1, nd, 0.5).pvalue) if nd else 1.0
            rows.append({"family": gname, "reader_1": r1, "reader_2": r2, "n_pairs": len(common), "both_win": both, "neither_wins": neither,
                         "only_1_wins": only1, "only_2_wins": only2, "n_discordant": nd, "sign_test_p": p,
                         "win_1": (both + only1) / len(common) if common else float("nan"), "win_2": (both + only2) / len(common) if common else float("nan")})
    return rows


# ====================================================================== Y0
def shared_check(items: Mapping[str, dict], by_reader: Mapping[str, Mapping[str, dict]], ids: Sequence[str], corrected: Optional[Mapping[str, Mapping[str, float]]] = None) -> dict:
    """How often all three readers favour the same candidate, vs the independence expectation from their marginals."""
    flags: Dict[str, Dict[str, bool]] = {}
    for iid in ids:
        f = {}
        for rd in READERS:
            if corrected is not None:
                v = (corrected.get(rd) or {}).get(iid)
            else:
                r = by_reader[rd].get(iid)
                v = None if r is None else r.get("lo_actual")
            if v is None:
                break
            f[rd] = bool(v > 0)
        if len(f) == len(READERS):
            flags[iid] = f
    n = len(flags)
    if n == 0:
        return {"n": 0}
    p = {rd: float(np.mean([f[rd] for f in flags.values()])) for rd in READERS}
    all_actual = sum(all(f.values()) for f in flags.values())
    all_other = sum(not any(f.values()) for f in flags.values())
    exp_actual = float(np.prod([p[rd] for rd in READERS]))
    exp_other = float(np.prod([1 - p[rd] for rd in READERS]))
    pairwise = {}
    for r1, r2 in itertools.combinations(READERS, 2):
        agree = float(np.mean([f[r1] == f[r2] for f in flags.values()]))
        pairwise[f"{r1}|{r2}"] = {"observed_agree": agree, "expected_agree": p[r1] * p[r2] + (1 - p[r1]) * (1 - p[r2])}
    return {"n": n, "marginal_favours_actual": p, "all_favour_actual": all_actual, "all_favour_other": all_other,
            "observed_unanimous": (all_actual + all_other) / n, "expected_unanimous_independent": exp_actual + exp_other,
            "expected_all_actual": exp_actual, "expected_all_other": exp_other, "pairwise": pairwise,
            "mixed": n - all_actual - all_other}


def _lo_str(v: Optional[float], toward_pos: str, toward_neg: str) -> str:
    if v is None:
        return "unscorable"
    return f"{v:+.2f} ({toward_pos if v > 0 else (toward_neg if v < 0 else 'tie')})"


def write_cases_md(path: Path, items: Mapping[str, dict], by_reader: Mapping[str, Mapping[str, dict]], trows: Mapping[str, dict], bias: Mapping[str, dict],
                   trace: Mapping[str, Any], shared: Mapping[str, Any]) -> None:
    L: List[str] = ["# Friday worked cases (Y0) — X3 items, native log-odds per reader", "",
                    "Generated by `projects/g_agreement/x_friday_r2r4.py` from the frozen X3 artefacts (no new compute). `lo_actual` = lp(model's actual answer) − lp(other candidate);",
                    "positive favours the model's actual answer. Corrected = minus the reader's additive symbol bias b[actual] − b[other] (R3a, fitted on all 400 puzzle rows).", ""]
    # (i) DISAGREE
    dis = [i for i in sorted(items) if items[i]["family"] == "choice" and items[i]["set"] == "disagree"]
    L += [f"## (i) DISAGREE choice items (n = {len(dis)}): the model's actual choice differs from its prompt-only self-guess", ""]
    tallies: Counter = Counter()
    for iid in dis:
        it = items[iid]
        src = it.get("source") or {}
        actual, other = it["primary"]["candidates"]
        guess = src.get("self_guess", (trows.get(iid) or {}).get("self_guess"))
        parts, nfav, nsc = [], 0, 0
        for rd in READERS:
            r = by_reader[rd].get(iid)
            v = None if r is None else r.get("lo_actual")
            parts.append(f"{READER_LABEL[rd]} {_lo_str(v, 'actual', 'self-guess')}")
            if v is not None:
                nsc += 1
                nfav += v > 0
        note = f"{nfav}/{nsc} readers favour the actual choice" + ("" if nsc == len(READERS) else f" ({len(READERS) - nsc} unscorable)")
        tallies[f"{nfav}/{nsc}"] += 1
        L += [f"- **{iid}** — \"{it['prompt_text']}\"  ", f"  actual **{actual}**, self-guess **{guess}**, first-listed {src.get('first_listed')}  ",
              "  " + "; ".join(parts) + f"  ", f"  note: {note}"]
    L += ["", "Tally (readers favouring actual / scorable): " + ", ".join(f"{k}: {v}" for k, v in sorted(tallies.items(), reverse=True)), ""]
    # (ii) off-trace
    off = list(trace.get("offtrace_ids", []))
    L += [f"## (ii) ERROR_OFFTRACE puzzles (n = {len(off)} of {trace.get('n_errors')} errors): the wrong answer is not a symbol on the model's own trace", "",
          "Trace-rule baseline over all errors: " + ", ".join(f"{k} {v}" for k, v in sorted(trace.get("counts", {}).items(), key=lambda kv: -kv[1])) + ".", ""]
    for iid in off:
        it = items[iid]
        src = it["source"]
        parts = []
        for rd in READERS:
            r = by_reader[rd].get(iid)
            v = None if r is None else r.get("lo_actual")
            c = ((bias.get(rd) or {}).get("corrected_lo") or {}).get(iid)
            parts.append(f"{READER_LABEL[rd]} raw {_lo_str(v, 'actual', 'correct')}, corrected {_lo_str(c, 'actual', 'correct')}")
        L += [f"- **{iid}** — \"{it['prompt_text']}\"  ", f"  correct **{src['correct']}**, model answer **{it['primary']['answer']}** (decode parsed: {(trows.get(iid) or {}).get('parsed')}), "
              f"trace {' → '.join(src['trace'])}, k = {src['k']}  ", "  " + "; ".join(parts)]
    L += [""]
    # (iii) shared-error
    L += ["## (iii) Shared-error check on the ERROR puzzles (all three readers scorable)", ""]
    for name, s in shared.items():
        if not s.get("n"):
            L.append(f"- {name}: no items with all three readers scorable")
            continue
        L += [f"- **{name}** (n = {s['n']}): marginal P(favours actual) " + ", ".join(f"{READER_LABEL[r]} {100 * s['marginal_favours_actual'][r]:.0f}%" for r in READERS) + ";  ",
              f"  all three favour actual {s['all_favour_actual']} items, all three favour the other (correct) candidate {s['all_favour_other']}, mixed {s['mixed']};  ",
              f"  unanimous {100 * s['observed_unanimous']:.0f}% observed vs {100 * s['expected_unanimous_independent']:.0f}% expected under independence "
              f"(all-actual {100 * s['all_favour_actual'] / s['n']:.0f}% vs {100 * s['expected_all_actual']:.0f}%; all-other {100 * s['all_favour_other'] / s['n']:.0f}% vs {100 * s['expected_all_other']:.0f}%);  ",
              "  pairwise agreement observed/expected: " + ", ".join(f"{k.replace('|', ' vs ')} {100 * v['observed_agree']:.0f}/{100 * v['expected_agree']:.0f}%" for k, v in s["pairwise"].items())]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ====================================================================== summary md
def write_r2r4_md(path: Path, S: Mapping[str, Any]) -> None:
    L: List[str] = ["# R2–R4 Friday re-analyses (CPU, frozen artefacts) — key numbers", ""]
    r2 = S.get("R2", {})
    for fam, rec in r2.items():
        cv, cf, idn, pca = rec["contrast"]["version"], rec["contrast"]["first_mentioned"], rec["identity"], rec["pca"]
        L.append(f"**R2 {fam}** ({rec['labels']['n_pairs']} pairs). Contrast probe on the version label (A−B; answer_position 0 vs 1 is the candidates index, "
                 f"tautological): LOO win {fmt_rate(cv['loo'])}, ceiling {fmt_rate(cv['ceiling'])}. ")
        if cf.get("status") == "ok":
            L.append(f"Contrast on mention order (answer first-mentioned; the E2 ownership label): LOO win {fmt_rate(cf['loo'])}, ceiling {fmt_rate(cf['ceiling'])}: an ORDER probe. ")
        else:
            L.append(f"Mention order is identical for both versions of every {fam} pair ({rec['labels']['mention_order_differs_within_pair']}/{rec['labels']['n_pairs']} differ), so no within-pair order probe exists; A−B differs only in letter identity. ")
        if idn.get("status") == "ok":
            L.append(f"Identity probe (OvR logistic over {idn['vocab_size']} candidates): LOO within-pair win (both states) {fmt_rate(idn['loo'])} (per-state {100 * idn['loo_per_state']['p']:.0f}%, "
                     f"{idn['loo_n_unscorable_pairs']} unscorable), permutation null mean {100 * idn['perm_null']['pair_win_mean']:.0f}% / p95 {100 * idn['perm_null']['pair_win_p95']:.0f}%, "
                     f"two-half ceiling {fmt_rate(idn['ceiling']['pooled'])}, C modal {idn['C_modal']} -> PRESENT(identity) = {idn['present_identity']}. "
                     + (f"Paired-sum win sA + sB > 0 (the analogue of the readers' E1 win): LOO {fmt_rate(idn['loo_paired_sum'])}, null p95 "
                        f"{100 * idn['perm_null'].get('paired_sum_win_p95', float('nan')):.0f}%, ceiling {fmt_rate(idn['ceiling'].get('paired_sum', {}))}. "
                        if "loo_paired_sum" in idn else ""))
        L.append(f"PCA: PC1 carries {100 * pca['pc1_frac_uncentred']:.0f}% of the uncentred within-pair-difference energy ({100 * pca['pc1_frac_centred']:.0f}% centred; uniform reference {100 * pca['uniform_frac_reference']:.0f}%).")
        L.append("")
    r3 = S.get("R3", {})
    if r3:
        b = r3.get("symbol_bias", {}).get("puzzle", {})
        parts = []
        for rd in READERS:
            d = b.get(rd, {})
            if d.get("status") == "ok":
                e, c = d["sets"]["error"], d["sets"]["error_control"]
                parts.append(f"{READER_LABEL[rd]} raw {100 * e['raw']['p']:.0f}/{100 * c['raw']['p']:.0f}% -> corrected {100 * e['corrected']['p']:.0f}% [{100 * e['corrected']['boot_lo']:.0f}, {100 * e['corrected']['boot_hi']:.0f}] vs "
                             f"{100 * c['corrected']['p']:.0f}% [{100 * c['corrected']['boot_lo']:.0f}, {100 * c['corrected']['boot_hi']:.0f}] (bias range {d['bias_range']:.1f} nats)")
        L.append("**R3a symbol bias (puzzles, ERROR vs ERROR control, P(favours actual)):** " + "; ".join(parts) + ". Choice: per-word bias not estimable; position-bias-corrected rates in r3_x3.csv.")
        tr = r3.get("trace", {})
        L.append(f"**R3b trace rule:** of {tr.get('n_errors')} errors, " + ", ".join(f"{k} {v}" for k, v in sorted(tr.get("counts", {}).items(), key=lambda kv: -kv[1])) +
                 f". ERROR_OFFTRACE n = {len(tr.get('offtrace_ids', []))}: " + "; ".join(f"{READER_LABEL[rd]} raw {fmt_rate(d['raw'])}, corrected {fmt_rate(d['corrected'])}"
                                                                                       for rd, d in r3.get("offtrace", {}).get("readers", {}).items()) + " (descriptive).")
        pz = r3.get("puzzle_probes", {})
        for name in ("actual_symbol", "correct_symbol", "actual_eq_correct"):
            p = pz.get(name, {})
            if p.get("status") != "ok":
                continue
            ho, nz, ce = p["held_out"], p["perm_null"], p.get("ceiling", {})
            s = f"**R3c {p['label']}:** 5-fold accuracy {100 * ho['accuracy']['p']:.0f}% (majority {100 * p['majority_rate']:.0f}%, null p95 {100 * nz['accuracy']['p95']:.0f}%, ceiling {100 * (ce.get('accuracy') or {}).get('p', float('nan')):.0f}%)"
            if "auroc" in ho:
                s += f", AUROC {ho['auroc']:.2f} (null p95 {nz['auroc']['p95']:.2f}, ceiling {ce.get('auroc', float('nan')):.2f})"
            for pn, d in ho["pair"].items():
                s += f"; {pn}: ERROR {fmt_rate(d['by_set']['error'])} (null p95 {100 * nz[f'{pn}_error']['p95']:.0f}%), control {fmt_rate(d['by_set']['error_control'])} (null p95 {100 * nz[f'{pn}_error_control']['p95']:.0f}%)"
            L.append(s + ".")
        ch = r3.get("choice_probes", {})
        for name in ("actual_word", "actual_is_first_listed"):
            p = ch.get(name, {})
            if p.get("status") != "ok":
                continue
            ho = p["held_out"]
            s = f"**R3d {p['label']}** (n = {p['n_items']}, descriptive): accuracy {100 * ho['accuracy']['p']:.0f}% (majority {100 * p['majority_rate']:.0f}%)"
            if "auroc" in ho:
                s += f", AUROC {ho['auroc']:.2f}" + (f" (null p95 {p['perm_null']['auroc']['p95']:.2f})" if p.get("perm_null", {}).get("auroc") else "")
            for pn, d in ho["pair"].items():
                s += f"; {pn}: DISAGREE {fmt_rate(d['by_set']['disagree'])}, AGREE {fmt_rate(d['by_set']['agree_control'])}, {d['n_unscorable']} unscorable"
            L.append(s + ".")
        L.append("")
    r4 = S.get("R4", [])
    if r4:
        L.append("**R4 paired sign tests on identical X1 pairs (only-1 / only-2 wins, exact binomial p):** " + "; ".join(
            f"{r['family']} {READER_LABEL[r['reader_1']]} vs {READER_LABEL[r['reader_2']]} {r['only_1_wins']}/{r['only_2_wins']} p={r['sign_test_p']:.3f}"
            for r in r4 if r["family"] in ("ownership", "mapping", "binding (ownership+mapping)")) + ".")
        L.append("")
    sh = S.get("Y0", {}).get("shared_error", {})
    for name, s in sh.items():
        if s.get("n"):
            L.append(f"**Y0 shared-error ({name}, n = {s['n']}):** all three favour actual {s['all_favour_actual']} / all three favour correct {s['all_favour_other']}; unanimous "
                     f"{100 * s['observed_unanimous']:.0f}% vs {100 * s['expected_unanimous_independent']:.0f}% expected under independence.")
    L += ["", "Notes. (1) A contrast probe on a balanced label over a strong direction scores *below* 50% under LOO (the held-out pair's sign is the "
          "minority of the training pairs), so `contrast_version` < 50% is the LOO artefact, not structure. (2) R3a bias is fitted in-sample on all 400 rows "
          "(8 parameters); the writeup's 55/59/56% used the same model up to rounding. (3) R3c/R3d probes: standardised features, C by inner 3-fold CV over "
          f"{CS}, folds by item; the puzzle probe sees 74% controls, so part of what it learns is correctness. (4) Choice word-identity is unscorable for "
          "almost every held-out item (each word appears 1–3 times); the first-listed probe is the only feasible choice probe.",
          "", "Files: r2_probes.csv, r3_x3.csv, r3_probe.csv, r4_paired.csv, friday_cases.md, r2r4_summary.json (this directory)."]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ====================================================================== run
def _strip(obj: Any, drop: Sequence[str] = ("per_pair", "loo_per_pair", "corrected_lo", "held_out_scores", "held_out_pred", "per_item", "ids", "pair_win_values")) -> Any:
    if isinstance(obj, dict):
        return {k: _strip(v, drop) for k, v in obj.items() if k not in drop}
    if isinstance(obj, list):
        return [_strip(v, drop) for v in obj]
    if isinstance(obj, tuple):
        return list(obj)
    return obj


def run(args: argparse.Namespace) -> dict:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if getattr(args, "md_only", False):
        S = U.load_json(out / "r2r4_summary.json")
        write_r2r4_md(out / "R2R4.md", S)
        U.log(f"[friday] rewrote {out / 'R2R4.md'} from the summary")
        return S
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    nb, sd, npm = args.n_boot, args.seed, args.n_perm
    S: dict = {"n_boot": nb, "seed": sd, "n_perm": npm, "Cs": list(CS), "thresholds": {"present_win": PRESENT_WIN, "ceiling_min": CEILING_MIN}}
    t0 = time.time()
    if "r2" not in skip:
        x1 = load_x1(args.items_x, args.states, "test", BINDING_FAMILIES)
        S["R2"] = {}
        for fam, d in x1.items():
            U.log(f"[friday] R2 {fam}: {len(d['pairs'])}/{d['n_pairs_total']} pairs with states (missing {len(d['missing'])})")
            S["R2"][fam] = r2_family(fam, d["pairs"], d["H"], npm, nb, sd)
            rec = S["R2"][fam]
            U.log(f"[friday] R2 {fam}: {rec['label_note']}")
            for lab, c in rec["contrast"].items():
                U.log(f"[friday] R2 {fam} contrast[{lab}]: {c.get('status')} LOO {fmt_rate(c['loo'])} ceiling {fmt_rate(c['ceiling'])}")
            i = rec["identity"]
            if i.get("status") == "ok":
                U.log(f"[friday] R2 {fam} identity: LOO pair {fmt_rate(i['loo'])} paired-sum {fmt_rate(i['loo_paired_sum'])} (null p95 {100 * i['perm_null']['paired_sum_win_p95']:.0f}%, ceiling {100 * i['ceiling']['paired_sum']['p']:.0f}%) state {100 * i['loo_per_state']['p']:.0f}% null mean/p95 "
                      f"{100 * i['perm_null']['pair_win_mean']:.0f}/{100 * i['perm_null']['pair_win_p95']:.0f}% ceiling {fmt_rate(i['ceiling']['pooled'])} C {i['C_counts']} present={i['present_identity']} ({rec['wall_s']:.0f}s)")
            U.log(f"[friday] R2 {fam} PCA: PC1 {100 * rec['pca']['pc1_frac_uncentred']:.1f}% uncentred, {100 * rec['pca']['pc1_frac_centred']:.1f}% centred")
        U.write_csv(out / "r2_probes.csv", r2_rows(S["R2"]))
    if "r3" not in skip or "y0" not in skip:
        items, by_reader, trows = load_x3(args.selected, args.x3_lo, args.x3_target)
        S["R3"] = {"n_items": len(items), "counts": dict(Counter(it["set"] for it in items.values()))}
        bias = r3a_symbol_bias(items, by_reader, nb, sd)
        S["R3"]["symbol_bias"] = bias
        for rd, d in bias["puzzle"].items():
            if d.get("status") == "ok":
                U.log(f"[friday] R3a {rd:5}: bias " + " ".join(f"{k}{v:+.1f}" for k, v in d["bias"].items()) + f" (R² {d['r2']:.2f}); ERROR raw {fmt_rate(d['sets']['error']['raw'])} -> corr {fmt_rate(d['sets']['error']['corrected'])}; "
                      f"control raw {fmt_rate(d['sets']['error_control']['raw'])} -> corr {fmt_rate(d['sets']['error_control']['corrected'])}")
        for rd, d in bias["choice"].items():
            if d.get("status") == "ok":
                U.log(f"[friday] R3a {rd:5} choice: {d['per_word_bias']}; position bias {d['position_bias_nats']:+.2f}; DISAGREE raw {fmt_rate(d['sets']['disagree']['raw'])} -> corr {fmt_rate(d['sets']['disagree']['corrected'])}; "
                      f"AGREE raw {fmt_rate(d['sets']['agree_control']['raw'])} -> corr {fmt_rate(d['sets']['agree_control']['corrected'])}")
        trace = trace_rule(items, trows)
        S["R3"]["trace"] = trace
        U.log(f"[friday] R3b trace rule: {trace['counts']} (decode mismatches {trace['n_decode_mismatch']})")
        off = r3b_offtrace(items, by_reader, bias["puzzle"], trace["offtrace_ids"], nb, sd)
        S["R3"]["offtrace"] = off
        for rd, d in off["readers"].items():
            U.log(f"[friday] R3b {rd:5} off-trace: raw {fmt_rate(d['raw'])} corrected {fmt_rate(d['corrected'])}")
        if "r3" not in skip:
            S["R3"]["puzzle_probes"] = r3c_puzzle_probes(items, args.states, npm, nb, sd)
            S["R3"]["choice_probes"] = r3d_choice_probes(items, args.states, npm, nb, sd)
            for blk in ("puzzle_probes", "choice_probes"):
                for name, p in S["R3"][blk].items():
                    if isinstance(p, dict) and p.get("status") == "ok":
                        ho, nz = p["held_out"], p.get("perm_null", {})
                        msg = f"[friday] R3 {blk} {name}: acc {fmt_rate(ho['accuracy'])} (majority {100 * p['majority_rate']:.0f}%, null p95 {100 * (nz.get('accuracy') or {}).get('p95', float('nan')):.0f}%, ceiling {100 * (p.get('ceiling', {}).get('accuracy') or {}).get('p', float('nan')):.0f}%)"
                        if "auroc" in ho:
                            msg += f" AUROC {ho['auroc']:.2f}"
                        for pn, d in ho["pair"].items():
                            msg += f" | {pn}: " + " ".join(f"{sn} {fmt_rate(r)}" for sn, r in d["by_set"].items()) + f" (unscorable {d['n_unscorable']})"
                        U.log(msg)
            U.write_csv(out / "r3_x3.csv", r3_x3_rows(bias, off))
            U.write_csv(out / "r3_probe.csv", r3_probe_rows(S["R3"]["puzzle_probes"], S["R3"]["choice_probes"]))
        if "y0" not in skip:
            err_ids = [i for i in sorted(items) if items[i]["family"] == "puzzle" and items[i]["set"] == "error"]
            shared = {"ERROR raw LO": shared_check(items, by_reader, err_ids),
                      "ERROR symbol-bias-corrected LO": shared_check(items, by_reader, err_ids, {rd: (bias["puzzle"].get(rd) or {}).get("corrected_lo", {}) for rd in READERS}),
                      "ERROR_OFFTRACE raw LO": shared_check(items, by_reader, trace["offtrace_ids"]),
                      "DISAGREE raw LO": shared_check(items, by_reader, [i for i in sorted(items) if items[i]["set"] == "disagree"])}
            S["Y0"] = {"shared_error": shared, "n_disagree": sum(it["set"] == "disagree" for it in items.values()), "n_offtrace": len(trace["offtrace_ids"])}
            for k, s in shared.items():
                if s.get("n"):
                    U.log(f"[friday] Y0 shared {k}: n {s['n']} all-actual {s['all_favour_actual']} all-other {s['all_favour_other']} unanimous {100 * s['observed_unanimous']:.0f}% vs {100 * s['expected_unanimous_independent']:.0f}% indep.")
            write_cases_md(out / "friday_cases.md", items, by_reader, trows, bias["puzzle"], trace, shared)
    if "r4" not in skip:
        _, items_x = U.load_items(args.items_x)
        pairs = X1A.load_pairs(items_x, "test")
        lo_rows = U.load_jsonl(args.x1_lo) if Path(args.x1_lo).exists() else []
        wins = e1_wins(lo_rows, pairs)
        rows = paired_sign_rows(wins, X1_FAMILIES, {"binding (ownership+mapping)": ("ownership", "mapping"), "all four families": X1_FAMILIES})
        S["R4"] = rows
        for r in rows:
            if r["family"] in ("ownership", "mapping", "binding (ownership+mapping)"):
                U.log(f"[friday] R4 {r['family']:28} {r['reader_1']:5} vs {r['reader_2']:5}: only-1 {r['only_1_wins']:2} only-2 {r['only_2_wins']:2} both {r['both_win']:2} neither {r['neither_wins']:2} p={r['sign_test_p']:.3f}")
        U.write_csv(out / "r4_paired.csv", rows)
    S["wall_s"] = time.time() - t0
    U.write_json(out / "r2r4_summary.json", _strip(S))
    write_r2r4_md(out / "R2R4.md", S)
    U.log(f"[friday] wrote {out} in {S['wall_s']:.0f}s")
    return S


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
