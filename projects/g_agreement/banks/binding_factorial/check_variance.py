#!/usr/bin/env python
"""Z5 VERIFY-BEFORE-CAPTURE check (BRIEF_Z.md §Z5), run on the captured block-42 last-token states of the
binding-factorial bank (cache/g_agreement/states/<item_id>.pt, fp32 [5120]). CPU only; no model calls.

For every pair: d = h_B - h_A. Then
  1. PCA of the 128 differences (centred; the uncentred energy share is reported as in R2R4).
  2. OLS of the PC1 (and PC2, PC3) scores on the one-hot dummies of each factor separately -> R² per factor.
     STOP RULE (pre-registered): if any factor's R² on PC1 exceeds 0.25 the bank is confounded like the X
     ownership bank; report and stop (no reader scoring). The factors under the rule are the five design factors
     (name_set, template, mention_order, pairing, query_direction) and ``order_flip``: the mention-order factor in
     the pair-level parametrisation that R2R4 found (does the answer's mention position flip between A and B, and
     in which sign; it is ``none`` for every name_to_object pair because the asked name's statement holds the answer
     in both versions). ``answer_identity`` (the actual answer of version A) is reported as a diagnostic only:
     it is the signal the bank is built to carry, not a confound.
     eta² of each factor in the FULL difference space (SS_between / SS_total summed over dimensions) is reported
     alongside, and everything is repeated within each query direction.
  3. Hewitt–Liang control: a leave-one-pair-out difference-in-means probe trained on a RANDOMLY RELABELLED pairing
     must be at chance: mean LOO accuracy over ``--n-relabel`` relabellings <= 0.55. The same probe on the true
     pairing label and on the order_flip label is reported (descriptive).

Usage:
    .venv/bin/python -m projects.g_agreement.banks.binding_factorial.check_variance \
        [--items projects/g_agreement/banks/binding_factorial/items_binding_factorial.json] \
        [--states-dir cache/g_agreement/states] [--out-dir results/g_agreement/z5] [--threshold 0.25]
Writes <out-dir>/variance_check.json and variance_check.md; exit code 2 when the stop rule fires.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from projects.g_agreement.banks.binding_factorial import build_bank as BB  # noqa: E402

DEFAULT_ITEMS = Path(BB.DEFAULT_OUT)
DEFAULT_STATES_DIR = Path(REPO) / "cache" / "g_agreement" / "states"
DEFAULT_OUT_DIR = Path(REPO) / "results" / "g_agreement" / "z5"
THRESHOLD = 0.25
HL_MAX_ACC = 0.55
DESIGN_FACTORS = list(BB.FACTORS)
DERIVED_FACTORS = ["order_flip", "answer_identity"]
STOP_RULE_FACTORS = DESIGN_FACTORS + ["order_flip"]
ALL_FACTORS = DESIGN_FACTORS + DERIVED_FACTORS


# ------------------------------------------------------------------ pairs and labels
def load_pairs(items: Sequence[dict]) -> List[Dict[str, Any]]:
    by: Dict[str, Dict[str, Any]] = {}
    for it in items:
        by.setdefault(it["pair_id"], {"pair_id": it["pair_id"]})[it["version"]] = it
    pairs = [p for p in by.values() if "A" in p and "B" in p]
    assert len(pairs) == len(by), "incomplete pairs"
    return pairs


def order_flip(pair: Dict[str, Any]) -> str:
    """Pair-level mention-order contrast: 'first_to_second' if the answer is first-mentioned in A and
    second-mentioned in B, 'second_to_first' for the reverse, 'none' if it does not change."""
    a, b = pair["A"]["construction"]["answer_is_first_mentioned"], pair["B"]["construction"]["answer_is_first_mentioned"]
    if a == b:
        return "none"
    return "first_to_second" if a else "second_to_first"


def factor_labels(pairs: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    labels: Dict[str, List[str]] = {f: [p["A"]["construction"][f] for p in pairs] for f in DESIGN_FACTORS}
    labels["order_flip"] = [order_flip(p) for p in pairs]
    labels["answer_identity"] = [p["A"]["primary"]["answer"] for p in pairs]
    return labels


def load_diffs(pairs: Sequence[Dict[str, Any]], states_dir: Path) -> np.ndarray:
    """[n_pairs, d] of h_B - h_A (fp64) from <states_dir>/<item_id>.pt."""
    import torch

    rows = []
    for p in pairs:
        hs = []
        for v in ("A", "B"):
            f = states_dir / f"{p[v]['item_id']}.pt"
            if not f.exists():
                raise FileNotFoundError(f"state missing: {f}")
            h = torch.load(f, map_location="cpu")
            if h.ndim != 1:
                raise ValueError(f"{f}: expected a 1-d state, got {tuple(h.shape)}")
            hs.append(h.to(torch.float64).numpy())
        rows.append(hs[1] - hs[0])
    D = np.stack(rows)
    return D


# ------------------------------------------------------------------ statistics
def pca(D: np.ndarray, n_pcs: int = 3) -> Dict[str, Any]:
    """Centred PCA by SVD; also the uncentred energy share of the first singular directions (R2R4 convention)."""
    Dc = D - D.mean(0, keepdims=True)
    U, S, Vt = np.linalg.svd(Dc, full_matrices=False)
    var = S ** 2
    scores = U[:, :n_pcs] * S[:n_pcs]
    _, S0, _ = np.linalg.svd(D, full_matrices=False)
    e0 = S0 ** 2
    return {"scores": scores, "components": Vt[:n_pcs], "explained_ratio": (var[:n_pcs] / var.sum()).tolist(),
            "uncentred_energy_ratio": (e0[:n_pcs] / e0.sum()).tolist(),
            "uniform_reference": 1.0 / min(D.shape)}


def one_hot(labels: Sequence[str]) -> np.ndarray:
    levels = sorted(set(labels))
    return np.array([[1.0 if l == lv else 0.0 for lv in levels] for l in labels])


def r2_onehot(y: np.ndarray, labels: Sequence[str]) -> float:
    """R² of OLS of y on the factor's level means (= 1 - SS_within / SS_total)."""
    y = np.asarray(y, dtype=float)
    tot = ((y - y.mean()) ** 2).sum()
    if tot <= 0:
        return 0.0
    within = 0.0
    for lv in set(labels):
        m = np.array([l == lv for l in labels])
        within += ((y[m] - y[m].mean()) ** 2).sum()
    return float(1.0 - within / tot)


def eta2_full(D: np.ndarray, labels: Sequence[str]) -> float:
    """Fraction of the total (centred) within-pair-difference variance explained by the factor's level means."""
    Dc = D - D.mean(0, keepdims=True)
    tot = (Dc ** 2).sum()
    if tot <= 0:
        return 0.0
    within = 0.0
    for lv in set(labels):
        m = np.array([l == lv for l in labels])
        within += ((Dc[m] - Dc[m].mean(0, keepdims=True)) ** 2).sum()
    return float(1.0 - within / tot)


def loo_diff_in_means_acc(D: np.ndarray, y: np.ndarray) -> float:
    """Leave-one-pair-out difference-in-means probe (direction = mean(class 1) - mean(class 0) of the training
    pairs, threshold at the midpoint of the projected class means); accuracy over the held-out pairs."""
    y = np.asarray(y).astype(int)
    n = len(y)
    correct = 0
    for i in range(n):
        m = np.ones(n, bool)
        m[i] = False
        X, t = D[m], y[m]
        if t.sum() == 0 or t.sum() == len(t):
            continue
        mu1, mu0 = X[t == 1].mean(0), X[t == 0].mean(0)
        w = mu1 - mu0
        b = 0.5 * (mu1 @ w + mu0 @ w)
        pred = int(D[i] @ w - b > 0)
        correct += int(pred == y[i])
    return correct / n


def hewitt_liang_control(D: np.ndarray, pairing_labels: Sequence[str], rng: np.random.Generator, n_relabel: int = 20,
                         max_acc: float = HL_MAX_ACC) -> Dict[str, Any]:
    y = np.array([l == sorted(set(pairing_labels))[0] for l in pairing_labels]).astype(int)
    accs = []
    for _ in range(n_relabel):
        accs.append(loo_diff_in_means_acc(D, rng.permutation(y)))
    return {"n_relabel": n_relabel, "accs": accs, "mean_acc": float(np.mean(accs)), "max_acc": float(np.max(accs)),
            "max_allowed_mean_acc": max_acc, "pass": bool(np.mean(accs) <= max_acc)}


def binary_probe_acc(D: np.ndarray, labels: Sequence[str]) -> Optional[float]:
    levels = sorted(set(labels))
    if len(levels) != 2:
        return None
    y = np.array([l == levels[0] for l in labels]).astype(int)
    return loo_diff_in_means_acc(D, y)


# ------------------------------------------------------------------ the check
def factor_table(D: np.ndarray, labels: Dict[str, List[str]], n_pcs: int = 3) -> Dict[str, Any]:
    P = pca(D, n_pcs)
    table: Dict[str, Any] = {}
    for f in ALL_FACTORS:
        table[f] = {"r2_pc": [r2_onehot(P["scores"][:, k], labels[f]) for k in range(P["scores"].shape[1])],
                    "eta2_full": eta2_full(D, labels[f]), "n_levels": len(set(labels[f])),
                    "levels": {lv: int(sum(l == lv for l in labels[f])) for lv in sorted(set(labels[f]))}}
    return {"n_pairs": int(D.shape[0]), "dim": int(D.shape[1]), "pca": {k: v for k, v in P.items() if k not in ("scores", "components")},
            "factors": table}


def run(items_path: Path = DEFAULT_ITEMS, states_dir: Path = DEFAULT_STATES_DIR, threshold: float = THRESHOLD,
        n_pcs: int = 3, n_relabel: int = 20, seed: int = 0, D: Optional[np.ndarray] = None,
        pairs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """The full check. ``D``/``pairs`` may be passed directly (tests); otherwise states are read from disk."""
    if pairs is None:
        pairs = load_pairs(json.loads(Path(items_path).read_text(encoding="utf-8"))["items"])
    if D is None:
        D = load_diffs(pairs, Path(states_dir))
    labels = factor_labels(pairs)
    rng = np.random.default_rng(seed)
    full = factor_table(D, labels, n_pcs)
    by_dir: Dict[str, Any] = {}
    for direction in BB.FACTORS["query_direction"]:
        m = np.array([l == direction for l in labels["query_direction"]])
        if m.sum() >= 4:
            sub_labels = {f: [l for l, keep in zip(labels[f], m) if keep] for f in ALL_FACTORS}
            by_dir[direction] = factor_table(D[m], sub_labels, n_pcs)
    r2_pc1 = {f: full["factors"][f]["r2_pc"][0] for f in STOP_RULE_FACTORS}
    offenders = sorted([f for f, r in r2_pc1.items() if r > threshold], key=lambda f: -r2_pc1[f])
    hl = hewitt_liang_control(D, labels["pairing"], rng, n_relabel=n_relabel)
    report = {
        "items_file": str(items_path), "states_dir": str(states_dir), "n_pairs": int(D.shape[0]), "dim": int(D.shape[1]),
        "threshold_r2_pc1": threshold, "stop_rule_factors": STOP_RULE_FACTORS, "diagnostic_factors": ["answer_identity"],
        "r2_pc1_stop_rule_factors": r2_pc1, "max_r2_pc1": (max(r2_pc1, key=r2_pc1.get), max(r2_pc1.values())),
        "stop": bool(offenders), "offending_factors": offenders,
        "full": full, "by_query_direction": by_dir,
        "hewitt_liang_control": hl,
        "probe_true_pairing_loo_acc": binary_probe_acc(D, labels["pairing"]),
        "probe_order_flip_loo_acc_object_to_name": None,
    }
    m = np.array([l == "object_to_name" for l in labels["query_direction"]])
    if m.sum() >= 4:
        report["probe_order_flip_loo_acc_object_to_name"] = binary_probe_acc(D[m], [l for l, k in zip(labels["order_flip"], m) if k])
    report["verdict"] = ("STOP: factor(s) %s explain > %.0f%% of PC1 of h_B - h_A; do not score readers on this bank"
                         % (", ".join(offenders), 100 * threshold)) if offenders else \
        "PASS: no stop-rule factor explains > %.0f%% of PC1 of h_B - h_A" % (100 * threshold)
    report["verdict"] += "; Hewitt-Liang control %s (mean LOO acc %.3f on relabelled pairing, limit %.2f)" % (
        "PASS" if hl["pass"] else "FAIL", hl["mean_acc"], HL_MAX_ACC)
    return report


def to_markdown(rep: Dict[str, Any]) -> str:
    lines = ["# Z5 variance check (verify before capture / before reader scoring)", "",
             f"items: `{rep['items_file']}`  states: `{rep['states_dir']}`  pairs: {rep['n_pairs']}  dim: {rep['dim']}", "",
             f"**{rep['verdict']}**", ""]
    pc = rep["full"]["pca"]
    lines.append("PCA of h_B − h_A (centred explained ratio / uncentred energy share): " +
                 ", ".join(f"PC{k + 1} {a:.1%} / {b:.1%}" for k, (a, b) in enumerate(zip(pc["explained_ratio"], pc["uncentred_energy_ratio"])))
                 + f" (uniform reference {pc['uniform_reference']:.1%})")
    lines += ["", "| factor | levels | R² PC1 | R² PC2 | R² PC3 | η² full space | in stop rule |", "|---|---|---|---|---|---|---|"]
    for f in ALL_FACTORS:
        e = rep["full"]["factors"][f]
        r2 = e["r2_pc"] + [float("nan")] * (3 - len(e["r2_pc"]))
        lines.append(f"| {f} | {e['n_levels']} | {r2[0]:.3f} | {r2[1]:.3f} | {r2[2]:.3f} | {e['eta2_full']:.3f} | "
                     f"{'yes' if f in STOP_RULE_FACTORS else 'diagnostic'} |")
    for direction, sub in rep["by_query_direction"].items():
        lines += ["", f"## within {direction} ({sub['n_pairs']} pairs)", "",
                  "| factor | R² PC1 | R² PC2 | R² PC3 | η² full space |", "|---|---|---|---|---|"]
        for f in ALL_FACTORS:
            e = sub["factors"][f]
            if e["n_levels"] < 2:
                continue
            r2 = e["r2_pc"] + [float("nan")] * (3 - len(e["r2_pc"]))
            lines.append(f"| {f} | {r2[0]:.3f} | {r2[1]:.3f} | {r2[2]:.3f} | {e['eta2_full']:.3f} |")
    hl = rep["hewitt_liang_control"]
    lines += ["", "## Hewitt–Liang control", "",
              f"LOO difference-in-means probe on {hl['n_relabel']} random relabellings of pairing: mean acc {hl['mean_acc']:.3f}, "
              f"max {hl['max_acc']:.3f} (limit on the mean {hl['max_allowed_mean_acc']:.2f}) -> {'PASS' if hl['pass'] else 'FAIL'}.",
              f"Same probe on the true pairing label: {rep['probe_true_pairing_loo_acc']:.3f}; on order_flip within object_to_name: "
              + (f"{rep['probe_order_flip_loo_acc_object_to_name']:.3f}" if rep["probe_order_flip_loo_acc_object_to_name"] is not None else "n/a")
              + " (descriptive)."]
    return "\n".join(lines) + "\n"


def write_report(rep: Dict[str, Any], out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pj, pm = out_dir / "variance_check.json", out_dir / "variance_check.md"
    pj.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    pm.write_text(to_markdown(rep), encoding="utf-8")
    return [pj, pm]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(DEFAULT_ITEMS))
    ap.add_argument("--states-dir", default=str(DEFAULT_STATES_DIR))
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--n-pcs", type=int, default=3)
    ap.add_argument("--n-relabel", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    rep = run(Path(a.items), Path(a.states_dir), a.threshold, a.n_pcs, a.n_relabel, a.seed)
    print(to_markdown(rep))
    if not a.no_write:
        for p in write_report(rep, Path(a.out_dir)):
            print(f"wrote {p}")
    return 2 if rep["stop"] else 0


if __name__ == "__main__":
    sys.exit(main())
