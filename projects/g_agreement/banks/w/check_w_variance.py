#!/usr/bin/env python
"""Phase W Track A VERIFY-BEFORE-SCORING check on the S1 captures (PREREG_WV.md §Track A: "per family, PC1 of
within-family activation differences regressed on design factors, no factor > 25%"). The Z5 recipe
(banks/binding_factorial/check_variance.py, whose statistics helpers are reused) applied to the W bank. CPU only.

Input: a states directory with one fp32 tensor [d] per item, ``<states-dir>/<item_id>.pt`` (one layer, one position;
run once per layer/position directory the pod writes). Families:
  ownership4  d = h_B - h_A per pair (64 differences). Stop-rule factors: name_set, template, mention_order, holder,
              query_direction, holder_b_shift and the pair-level mention-position factors ``mention_pos_A`` /
              ``mention_pos_B`` (which of the four statements holds the answer in A and in B; the analogue of Z5's
              order_flip; pos_B - pos_A mod 4 equals the design factor holder_b_shift).
              Diagnostic only: answer_identity (A's answer). Hewitt-Liang control as in Z5 (LOO difference-in-means
              probe on a randomly relabelled binary label must be at chance, mean acc <= 0.55); the probe on
              query_direction is reported.
  counts      d = h_i - mean_family(h) (600 family-centred states: the "within-family differences" of a singleton
              family). Stop-rule factors: decade, template, object, place. Diagnostic: the linear R² of PC1 on the value
              N itself. NOTE (README): decade is the graded signal of this family; the pre-registered rule still lists
              it, so a decade-dominated PC1 is reported as STOP and left to the operator (a dated deviation).
  arith       (optional, --family arith) d = family-centred states; stop-rule factors: op, a_decade, b_decade.
STOP RULE: any stop-rule factor with R²(PC1) > --threshold (0.25) -> exit code 2, "do not score readers on this bank".

Usage:
    .venv/bin/python -m projects.g_agreement.banks.w.check_w_variance --states-dir <dir> [--family ownership4|counts|arith|all]
        [--items projects/g_agreement/banks/w/items_w.json] [--out-dir results/g_agreement/w/variance] [--threshold 0.25]
Writes <out-dir>/variance_check_<family>.json and .md.
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

from projects.g_agreement.banks.binding_factorial import check_variance as CV  # noqa: E402
from projects.g_agreement.banks.w import build_w_bank as W  # noqa: E402

DEFAULT_ITEMS = Path(W.ITEMS_W)
DEFAULT_OUT_DIR = Path(REPO) / "results" / "g_agreement" / "w" / "variance"
THRESHOLD = 0.25
FAMILY_SPEC: Dict[str, Dict[str, Any]] = {
    "ownership4": {"mode": "pairs", "stop": list(W.FACTORS4) + ["holder_b_shift", "mention_pos_A", "mention_pos_B"], "diagnostic": ["answer_identity"],
                   "binary_control": "query_direction", "split_by": "query_direction"},
    "counts": {"mode": "centred", "stop": ["decade", "template", "object", "place"], "diagnostic": ["value_linear"],
               "binary_control": None, "split_by": None},
    "arith": {"mode": "centred", "stop": ["op", "a_decade", "b_decade"], "diagnostic": [], "binary_control": "op", "split_by": "op"},
}


# ------------------------------------------------------------------ labels
def load_items(items_path: Path, family: str) -> List[dict]:
    d = json.loads(Path(items_path).read_text(encoding="utf-8"))
    return [it for it in d["items"] if it["family"] == family]


def pair_labels(pairs: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    lab: Dict[str, List[str]] = {f: [p["A"]["construction"][f] for p in pairs] for f in list(W.FACTORS4) + ["holder_b_shift"]}
    lab["mention_pos_A"] = [str(p["A"]["construction"]["answer_mention_position"]) for p in pairs]
    lab["mention_pos_B"] = [str(p["B"]["construction"]["answer_mention_position"]) for p in pairs]
    lab["answer_identity"] = [p["A"]["primary"]["answer"] for p in pairs]
    return lab


def item_labels(items: Sequence[dict], family: str) -> Dict[str, List[str]]:
    if family == "counts":
        return {f: [it["construction"][f] for it in items] for f in ("decade", "template", "object", "place")}
    if family == "arith":
        return {"op": [it["construction"]["op"] for it in items], "a_decade": [str(it["construction"]["a_decade"]) for it in items],
                "b_decade": [str(it["construction"]["b_decade"]) for it in items]}
    raise ValueError(family)


def load_states(item_ids: Sequence[str], states_dir: Path) -> np.ndarray:
    import torch

    rows = []
    for iid in item_ids:
        f = Path(states_dir) / f"{iid}.pt"
        if not f.exists():
            raise FileNotFoundError(f"state missing: {f}")
        h = torch.load(f, map_location="cpu")
        if h.ndim != 1:
            raise ValueError(f"{f}: expected a 1-d state, got {tuple(h.shape)}")
        rows.append(h.to(torch.float64).numpy())
    return np.stack(rows)


def r2_linear(y: np.ndarray, x: Sequence[float]) -> float:
    """R² of OLS of y on a single continuous regressor (with intercept)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    X = np.stack([np.ones_like(x), x], 1)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    tot = ((y - y.mean()) ** 2).sum()
    return float(1 - (res ** 2).sum() / tot) if tot > 0 else 0.0


# ------------------------------------------------------------------ the check
def factor_table(D: np.ndarray, labels: Dict[str, List[str]], n_pcs: int = 3) -> Dict[str, Any]:
    P = CV.pca(D, n_pcs)
    table: Dict[str, Any] = {}
    for f, lab in labels.items():
        table[f] = {"r2_pc": [CV.r2_onehot(P["scores"][:, k], lab) for k in range(P["scores"].shape[1])],
                    "eta2_full": CV.eta2_full(D, lab), "n_levels": len(set(lab)),
                    "levels": {lv: int(sum(l == lv for l in lab)) for lv in sorted(set(lab))}}
    return {"n": int(D.shape[0]), "dim": int(D.shape[1]), "pca": {k: v for k, v in P.items() if k not in ("scores", "components")},
            "pc1_scores": P["scores"][:, 0].tolist(), "factors": table}


def run(family: str, items_path: Path = DEFAULT_ITEMS, states_dir: Optional[Path] = None, threshold: float = THRESHOLD,
        n_pcs: int = 3, n_relabel: int = 20, seed: int = 0, D: Optional[np.ndarray] = None,
        items: Optional[List[dict]] = None) -> Dict[str, Any]:
    """The check for one family. ``D`` (and ``items``) may be passed directly (tests); otherwise states are read."""
    spec = FAMILY_SPEC[family]
    if items is None:
        items = load_items(items_path, family)
    if spec["mode"] == "pairs":
        pairs = CV.load_pairs(items)
        pairs.sort(key=lambda p: p["pair_id"])
        labels = pair_labels(pairs)
        if D is None:
            HA = load_states([p["A"]["item_id"] for p in pairs], states_dir)
            HB = load_states([p["B"]["item_id"] for p in pairs], states_dir)
            D = HB - HA
        units = [p["pair_id"] for p in pairs]
    else:
        items = sorted(items, key=lambda it: it["item_id"])
        labels = item_labels(items, family)
        if D is None:
            H = load_states([it["item_id"] for it in items], states_dir)
            D = H - H.mean(0, keepdims=True)
        units = [it["item_id"] for it in items]
    assert D.shape[0] == len(units)
    rng = np.random.default_rng(seed)
    full = factor_table(D, labels, n_pcs)
    pc1 = np.asarray(full.pop("pc1_scores"))
    diagnostics: Dict[str, Any] = {}
    if family == "counts":
        diagnostics["value_linear_r2_pc1"] = r2_linear(pc1, [it["construction"]["value"] for it in items])
    by_split: Dict[str, Any] = {}
    if spec["split_by"]:
        for lv in sorted(set(labels[spec["split_by"]])):
            m = np.array([l == lv for l in labels[spec["split_by"]]])
            if m.sum() >= 4:
                sub = {f: [l for l, k in zip(lab, m) if k] for f, lab in labels.items() if f != spec["split_by"]}
                t = factor_table(D[m], sub, n_pcs)
                t.pop("pc1_scores")
                by_split[lv] = t
    r2_pc1 = {f: full["factors"][f]["r2_pc"][0] for f in spec["stop"]}
    offenders = sorted([f for f, r in r2_pc1.items() if r > threshold], key=lambda f: -r2_pc1[f])
    hl = None
    probes: Dict[str, Optional[float]] = {}
    if spec["binary_control"]:
        hl = CV.hewitt_liang_control(D, labels[spec["binary_control"]], rng, n_relabel=n_relabel)
        probes[f"probe_loo_acc_{spec['binary_control']}"] = CV.binary_probe_acc(D, labels[spec["binary_control"]])
    report = {
        "family": family, "mode": spec["mode"], "items_file": str(items_path), "states_dir": str(states_dir) if states_dir else None,
        "n_units": int(D.shape[0]), "dim": int(D.shape[1]), "unit_ids_sha_prefix": units[:3],
        "threshold_r2_pc1": threshold, "stop_rule_factors": spec["stop"], "diagnostic_factors": spec["diagnostic"],
        "r2_pc1_stop_rule_factors": r2_pc1, "max_r2_pc1": (max(r2_pc1, key=r2_pc1.get), max(r2_pc1.values())),
        "stop": bool(offenders), "offending_factors": offenders, "full": full, "by_split": by_split, "diagnostics": diagnostics,
        "hewitt_liang_control": hl, **probes,
    }
    report["verdict"] = ("STOP: factor(s) %s explain > %.0f%% of PC1 of the within-family differences; do not score readers on this family"
                         % (", ".join(offenders), 100 * threshold)) if offenders else \
        "PASS: no stop-rule factor explains > %.0f%% of PC1 of the within-family differences" % (100 * threshold)
    if hl is not None:
        report["verdict"] += "; Hewitt-Liang control %s (mean LOO acc %.3f on relabelled %s, limit %.2f)" % (
            "PASS" if hl["pass"] else "FAIL", hl["mean_acc"], spec["binary_control"], CV.HL_MAX_ACC)
    return report


def to_markdown(rep: Dict[str, Any]) -> str:
    lines = [f"# W variance check — {rep['family']} (verify before reader scoring)", "",
             f"items: `{rep['items_file']}`  states: `{rep['states_dir']}`  units: {rep['n_units']} ({rep['mode']})  dim: {rep['dim']}", "",
             f"**{rep['verdict']}**", ""]
    pc = rep["full"]["pca"]
    lines.append("PCA of the differences (centred explained ratio / uncentred energy share): " +
                 ", ".join(f"PC{k + 1} {a:.1%} / {b:.1%}" for k, (a, b) in enumerate(zip(pc["explained_ratio"], pc["uncentred_energy_ratio"])))
                 + f" (uniform reference {pc['uniform_reference']:.1%})")
    lines += ["", "| factor | levels | R² PC1 | R² PC2 | R² PC3 | η² full space | in stop rule |", "|---|---|---|---|---|---|---|"]
    for f, e in rep["full"]["factors"].items():
        r2 = e["r2_pc"] + [float("nan")] * (3 - len(e["r2_pc"]))
        lines.append(f"| {f} | {e['n_levels']} | {r2[0]:.3f} | {r2[1]:.3f} | {r2[2]:.3f} | {e['eta2_full']:.3f} | "
                     f"{'yes' if f in rep['stop_rule_factors'] else 'diagnostic'} |")
    for k, v in rep["diagnostics"].items():
        lines.append(f"\ndiagnostic {k}: {v:.3f}")
    for lv, sub in rep["by_split"].items():
        lines += ["", f"## within {lv} ({sub['n']} units)", "", "| factor | R² PC1 | R² PC2 | R² PC3 | η² full space |", "|---|---|---|---|---|"]
        for f, e in sub["factors"].items():
            if e["n_levels"] < 2:
                continue
            r2 = e["r2_pc"] + [float("nan")] * (3 - len(e["r2_pc"]))
            lines.append(f"| {f} | {r2[0]:.3f} | {r2[1]:.3f} | {r2[2]:.3f} | {e['eta2_full']:.3f} |")
    hl = rep.get("hewitt_liang_control")
    if hl:
        lines += ["", "## Hewitt–Liang control", "",
                  f"LOO difference-in-means probe on {hl['n_relabel']} random relabellings: mean acc {hl['mean_acc']:.3f}, max {hl['max_acc']:.3f} "
                  f"(limit on the mean {hl['max_allowed_mean_acc']:.2f}) -> {'PASS' if hl['pass'] else 'FAIL'}."]
        for k, v in rep.items():
            if k.startswith("probe_loo_acc_") and v is not None:
                lines.append(f"Same probe on the true {k[len('probe_loo_acc_'):]} label: {v:.3f} (descriptive).")
    return "\n".join(lines) + "\n"


def write_report(rep: Dict[str, Any], out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pj, pm = out_dir / f"variance_check_{rep['family']}.json", out_dir / f"variance_check_{rep['family']}.md"
    pj.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    pm.write_text(to_markdown(rep), encoding="utf-8")
    return [pj, pm]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(DEFAULT_ITEMS))
    ap.add_argument("--states-dir", required=True)
    ap.add_argument("--family", default="all", choices=["all", "ownership4", "counts", "arith"])
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--n-pcs", type=int, default=3)
    ap.add_argument("--n-relabel", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    fams = ["ownership4", "counts"] if a.family == "all" else [a.family]
    stop = False
    for fam in fams:
        rep = run(fam, Path(a.items), Path(a.states_dir), a.threshold, a.n_pcs, a.n_relabel, a.seed)
        print(to_markdown(rep))
        if not a.no_write:
            for p in write_report(rep, Path(a.out_dir)):
                print(f"wrote {p}")
        stop |= rep["stop"]
    return 2 if stop else 0


if __name__ == "__main__":
    sys.exit(main())
