"""Z3 — equivalence tests for "inert" (BRIEF_Z §Z3; hard rule: any inert / no-difference claim via TOST).

CPU only, zero new forward passes. Inputs (all cached, sha256 in manifest/frozen_config_z.json):
  cache/g_agreement/x/x2_behaviour.jsonl   X2 rows {pair_id, source, site nat|S1|S2|S3, alpha, condition natural|planted|null|null_other,
                                           null_k, flipped_to_other, coherent, lo_model = lp(first token other) − lp(first token own)}
  results/g_agreement/x2/per_pair.csv      one row per item (pair_id, source): alpha_star_S2, lo_model_nat, lo_model_at_astar_S2
  cache/g_agreement/g5/behaviour.jsonl     G5 rows {pair_id, source, condition natural|planted|null, alpha, flipped_to_other}; G5 rows carry
                                           NO first-token log-probabilities (no lp_* / lo_model field), so G5 is flips-only here.

MARGIN (pre-registered, computed and written BEFORE any test is read): 0.25 × median over items with an S2 flip dose α* of
  Δ_model(α*) = lo_model_at_astar_S2 − lo_model_nat   (the model's own answer log-odds shift at the dose where its answer flips).
Quantity per condition: Δ_model = lo_model(edited) − lo_model(natural entry of the same source state), positive = toward the
planted / other candidate. Items = (pair_id, source) states; for null conditions the item value is the mean over its null_k draws.
Mean Δ_model over items with pair-level bootstrap (resample pair_ids, n_boot 1000, seed 0) 95% and 90% CIs.
TOST at α = 0.05: "inert within margin" iff the 90% bootstrap CI of the mean lies inside ±margin; else "not established".
Alongside: flip rate (flipped_to_other ∧ coherent) with Wilson 95% CI; fraction of items with |Δ_model| > margin; mean |Δ_model|.
Conditions: S1 planted α 0.5 / 1.0 / 1.5 (confirmatory; 2, 3, 4 descriptive); S2 and S3 isotropic null α 1; S1 isotropic null α 2;
S1 other-pair null α 2; G5 planted α 0.5 / 1 / 1.5 (3, 5 descriptive) and G5 null α 1 — flips only (no continuous LO in G5).
Outputs results/g_agreement/z3/{z3.md, z3_table.csv, z3_summary.json}; appends a dated "Phase Z corrections" block to writeup.md.

Run: PYTHONPATH=. .venv/bin/python projects/g_agreement/z3_equivalence/analyze.py --n-boot 1000 --seed 0 --out results/g_agreement/z3
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402

MODULE = "z3"
MARGIN_FRACTION = 0.25
TOST_ALPHA = 0.05          # one-sided 5% each side  ->  90% two-sided CI inside ±margin
CI_ALPHA = 0.05            # the reported 95% CI
DATE = "2026-10-09"
INERT, NOT_EST, NA = "inert within margin", "not established", "n/a (no continuous log-odds)"

Item = Tuple[str, str]     # (pair_id, source)

# (dataset, site, condition, alpha, role)
X2_CONDITIONS: List[Tuple[str, str, str, float, str]] = [
    ("X2", "S1", "planted", 0.5, "confirmatory"),
    ("X2", "S1", "planted", 1.0, "confirmatory"),
    ("X2", "S1", "planted", 1.5, "confirmatory"),
    ("X2", "S1", "planted", 2.0, "descriptive"),
    ("X2", "S1", "planted", 3.0, "descriptive"),
    ("X2", "S1", "planted", 4.0, "descriptive"),
    ("X2", "S2", "null", 1.0, "confirmatory"),
    ("X2", "S3", "null", 1.0, "confirmatory"),
    ("X2", "S1", "null", 2.0, "confirmatory"),
    ("X2", "S1", "null_other", 2.0, "confirmatory"),
]
G5_CONDITIONS: List[Tuple[str, str, str, float, str]] = [
    ("G5", "L42 last", "planted", 0.5, "confirmatory"),
    ("G5", "L42 last", "planted", 1.0, "confirmatory"),
    ("G5", "L42 last", "planted", 1.5, "confirmatory"),
    ("G5", "L42 last", "planted", 3.0, "descriptive"),
    ("G5", "L42 last", "planted", 5.0, "descriptive"),
    ("G5", "L42 last", "null", 1.0, "descriptive"),
]
TABLE_COLUMNS = ["dataset", "site", "condition", "alpha", "role", "continuous", "n_rows", "n_items", "n_pairs",
                 "mean_delta", "ci95_lo", "ci95_hi", "ci90_lo", "ci90_hi", "ci95_excludes_zero", "margin", "tost_verdict",
                 "frac_items_abs_gt_margin", "mean_abs_delta", "flips_k", "flips_n", "flip_rate", "flip_wilson_lo", "flip_wilson_hi"]

# Sentences in writeup.md that assert the last-token site is inert / not load-bearing, with the section they sit in.
# (section, quoted original wording). Replacement wording is generated from the Z3 verdicts.
INERT_CLAIMS: List[Tuple[str, str]] = [
    ("G5 (Follow-up)", "At α = 1 the last-token vector IS the other state's vector and the answer still does not change, so "
                       "the answer is reconstructed downstream from the untouched earlier positions."),
    ("Phase X, X2 E4", "The last-token vector is not load-bearing (G5 again); the all-position state at L38 is."),
    ("Phase X → Y, Friday re-analyses R1", "At S1 (inert) the readers reach 1.1–1.2× at α 2 and 1.4–1.7× at α 4 while the model "
                                           "stays at 0.02–0.09"),
]


# ----------------------------------------------------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------------------------------------------------
def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--behaviour", default=str(ROOT / "cache" / "g_agreement" / "x" / "x2_behaviour.jsonl"))
    ap.add_argument("--per-pair", default=str(ROOT / "results" / "g_agreement" / "x2" / "per_pair.csv"))
    ap.add_argument("--g5", default=str(ROOT / "cache" / "g_agreement" / "g5" / "behaviour.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "results" / "g_agreement" / "z3"))
    ap.add_argument("--writeup", default=str(ROOT / "results" / "g_agreement" / "writeup.md"),
                    help="writeup.md to append the dated 'Phase Z corrections' block to; --no-writeup skips it")
    ap.add_argument("--no-writeup", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    return ap.parse_args(argv)


def _f(x) -> float:
    if x is None or x == "":
        return float("nan")
    return float(x)


# ----------------------------------------------------------------------------------------------------------------------
# Margin
# ----------------------------------------------------------------------------------------------------------------------
def read_per_pair(path) -> List[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def compute_margin(per_pair_rows: Sequence[Mapping[str, Any]], fraction: float = MARGIN_FRACTION) -> dict:
    """MARGIN = fraction × median over items with an S2 α* of (lo_model_at_astar_S2 − lo_model_nat).
    Items without an α* (never flipped at S2) are excluded and counted."""
    diffs: List[float] = []
    n_total, n_without = 0, 0
    for r in per_pair_rows:
        n_total += 1
        a = _f(r.get("alpha_star_S2"))
        d = _f(r.get("lo_model_at_astar_S2")) - _f(r.get("lo_model_nat"))
        if math.isnan(a) or math.isnan(d):
            n_without += 1
            continue
        diffs.append(d)
    if not diffs:
        raise U.AnalysisError("no item has an S2 alpha*; the margin is undefined")
    med = float(np.median(diffs))
    return {"margin": fraction * med, "fraction": fraction, "median_delta_model_at_astar_S2": med,
            "n_items_total": n_total, "n_items_with_astar_S2": len(diffs), "n_items_without_astar_S2": n_without,
            "delta_model_at_astar_S2_quartiles": [float(q) for q in np.percentile(diffs, [25, 50, 75])],
            "definition": "0.25 x median over (pair, source) items with an S2 flip dose alpha* of lo_model_at_astar_S2 - lo_model_nat"}


# ----------------------------------------------------------------------------------------------------------------------
# Per-item deltas, bootstrap, TOST
# ----------------------------------------------------------------------------------------------------------------------
def natural_lo(rows: Sequence[Mapping[str, Any]], lo_field: str = "lo_model") -> Dict[Item, float]:
    """lo_model of the natural (unedited) entry per item (pair_id, source)."""
    out: Dict[Item, float] = {}
    for r in rows:
        if r.get("condition") == "natural":
            it = (str(r["pair_id"]), str(r["source"]))
            if it in out:
                raise U.AnalysisError(f"duplicate natural row for item {it}")
            out[it] = _f(r.get(lo_field))
    return out


def select_rows(rows: Sequence[Mapping[str, Any]], site: Optional[str], condition: str, alpha: float) -> List[dict]:
    sel = []
    for r in rows:
        if r.get("condition") != condition:
            continue
        if site is not None and r.get("site") != site:
            continue
        if abs(_f(r.get("alpha")) - alpha) > 1e-9:
            continue
        sel.append(dict(r))
    return sel


def item_deltas(sel: Sequence[Mapping[str, Any]], nat: Mapping[Item, float], lo_field: str = "lo_model") -> Dict[Item, float]:
    """Δ_model per item = mean over the item's rows (null_k draws) of lo(edited) − lo(natural, same source state)."""
    acc: Dict[Item, List[float]] = defaultdict(list)
    for r in sel:
        it = (str(r["pair_id"]), str(r["source"]))
        if it not in nat:
            raise U.AnalysisError(f"no natural entry for item {it}")
        d = _f(r.get(lo_field)) - nat[it]
        if math.isnan(d):
            raise U.AnalysisError(f"missing {lo_field} on item {it} ({r.get('condition')}, alpha {r.get('alpha')})")
        acc[it].append(d)
    return {it: float(np.mean(v)) for it, v in acc.items()}


def pair_bootstrap_mean(deltas: Mapping[Item, float], n_boot: int, seed: int) -> dict:
    """Mean over items; pair-level bootstrap (resample pair_ids with replacement, keep every item of a drawn pair).
    The 95% and 90% intervals come from the same resamples (same seed)."""
    by_pair: Dict[str, List[float]] = defaultdict(list)
    for (pid, _src), d in deltas.items():
        by_pair[pid].append(d)
    pids = sorted(by_pair)

    def stat(ps: Sequence[str]) -> float:
        vals = [d for p in ps for d in by_pair[p]]
        return float("nan") if not vals else float(np.mean(vals))

    est, lo95, hi95 = U.pair_bootstrap_stat(pids, stat, n_boot=n_boot, seed=seed, alpha=CI_ALPHA)
    _, lo90, hi90 = U.pair_bootstrap_stat(pids, stat, n_boot=n_boot, seed=seed, alpha=2 * TOST_ALPHA)
    return {"mean": est, "ci95": [lo95, hi95], "ci90": [lo90, hi90], "n_items": len(deltas), "n_pairs": len(pids), "n_boot": n_boot, "seed": seed}


def tost_verdict(ci90: Sequence[float], margin: float) -> str:
    """TOST at α = 0.05 == the 90% CI of the mean lies strictly inside (−margin, +margin)."""
    lo, hi = float(ci90[0]), float(ci90[1])
    if math.isnan(lo) or math.isnan(hi) or math.isnan(margin):
        return NOT_EST
    return INERT if (lo > -margin and hi < margin) else NOT_EST


def flip_counts(sel: Sequence[Mapping[str, Any]]) -> Tuple[int, int]:
    """Flip = flipped_to_other ∧ coherent (BRIEF_Z Z1 definition; rows without a `coherent` field count as coherent)."""
    k = sum(bool(r.get("flipped_to_other")) and bool(r.get("coherent", True)) for r in sel)
    return k, len(sel)


def summarise_condition(dataset: str, site: str, condition: str, alpha: float, role: str, sel: Sequence[Mapping[str, Any]],
                        nat: Optional[Mapping[Item, float]], margin: float, n_boot: int, seed: int, continuous: bool) -> dict:
    k, n = flip_counts(sel)
    p, wlo, whi = U.wilson(k, n)
    row: Dict[str, Any] = {"dataset": dataset, "site": site, "condition": condition, "alpha": alpha, "role": role,
                           "continuous": continuous, "n_rows": n, "margin": margin,
                           "flips_k": k, "flips_n": n, "flip_rate": p, "flip_wilson_lo": wlo, "flip_wilson_hi": whi}
    if not continuous or nat is None:
        row.update({"n_items": len({(str(r["pair_id"]), str(r["source"])) for r in sel}),
                    "n_pairs": len({str(r["pair_id"]) for r in sel}),
                    "mean_delta": float("nan"), "ci95_lo": float("nan"), "ci95_hi": float("nan"), "ci90_lo": float("nan"),
                    "ci90_hi": float("nan"), "ci95_excludes_zero": "", "tost_verdict": NA,
                    "frac_items_abs_gt_margin": float("nan"), "mean_abs_delta": float("nan")})
        return row
    deltas = item_deltas(sel, nat)
    bs = pair_bootstrap_mean(deltas, n_boot=n_boot, seed=seed)
    vals = np.array(list(deltas.values()), dtype=float)
    row.update({"n_items": bs["n_items"], "n_pairs": bs["n_pairs"], "mean_delta": bs["mean"],
                "ci95_lo": bs["ci95"][0], "ci95_hi": bs["ci95"][1], "ci90_lo": bs["ci90"][0], "ci90_hi": bs["ci90"][1],
                "ci95_excludes_zero": bool(bs["ci95"][0] > 0 or bs["ci95"][1] < 0),
                "tost_verdict": tost_verdict(bs["ci90"], margin),
                "frac_items_abs_gt_margin": float(np.mean(np.abs(vals) > margin)) if len(vals) else float("nan"),
                "mean_abs_delta": float(np.mean(np.abs(vals))) if len(vals) else float("nan")})
    return row


def g5_has_continuous_lo(rows: Sequence[Mapping[str, Any]]) -> Tuple[bool, List[str]]:
    """True if the G5 rows carry a first-token answer log-odds (lo_model, or lp_first_A/lp_first_B to build it)."""
    keys: set = set()
    for r in rows:
        keys.update(r.keys())
    cand = sorted(k for k in keys if k.startswith("lo_") or k.startswith("lp_") or k.startswith("logprob"))
    has = ("lo_model" in keys) or ({"lp_first_A", "lp_first_B"} <= keys)
    return has, cand


def run_tables(x2_rows: Sequence[Mapping[str, Any]], per_pair_rows: Sequence[Mapping[str, Any]],
               g5_rows: Sequence[Mapping[str, Any]], n_boot: int, seed: int) -> Tuple[dict, List[dict], dict]:
    """Margin first, then every condition. Returns (margin_info, table_rows, g5_info)."""
    margin_info = compute_margin(per_pair_rows)
    margin = margin_info["margin"]
    nat = natural_lo(x2_rows)
    table: List[dict] = []
    for dataset, site, cond, alpha, role in X2_CONDITIONS:
        sel = select_rows(x2_rows, site, cond, alpha)
        if not sel:
            continue
        table.append(summarise_condition(dataset, site, cond, alpha, role, sel, nat, margin, n_boot, seed, continuous=True))
    g5_cont, g5_fields = g5_has_continuous_lo(g5_rows) if g5_rows else (False, [])
    g5_nat = natural_lo(g5_rows) if g5_cont else None
    for dataset, site, cond, alpha, role in G5_CONDITIONS:
        sel = select_rows(g5_rows, None, cond, alpha)
        if not sel:
            continue
        table.append(summarise_condition(dataset, site, cond, alpha, role, sel, g5_nat, margin, n_boot, seed, continuous=g5_cont))
    g5_info = {"n_rows": len(g5_rows), "continuous_log_odds": g5_cont, "log_odds_like_fields": g5_fields,
               "note": ("G5 rows carry a continuous first-token log-odds; TOST applied." if g5_cont else
                        "G5 behaviour rows carry only the greedy answer (answer_text / parsed / flipped_to_other), no first-token "
                        "log-probabilities: G5 is reported as flip rates with Wilson CIs only; the continuous TOST is X2-S1 only.")}
    return margin_info, table, g5_info


# ----------------------------------------------------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------------------------------------------------
def _fmt(x: float, nd: int = 2) -> str:
    return "—" if (x is None or (isinstance(x, float) and math.isnan(x))) else f"{x:+.{nd}f}"


def _pct(x: float) -> str:
    if isinstance(x, float) and math.isnan(x):
        return "—"
    v = 100 * float(x)
    return f"{(0.0 if abs(v) < 0.5 else v):.0f}%"


def table_markdown(table: Sequence[Mapping[str, Any]]) -> List[str]:
    lines = ["| data | site | condition | α | role | n rows / items | mean Δ_model [95% CI] | 90% CI | TOST | items \\|Δ\\|>m | flips (Wilson 95%) |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        cont = bool(r["continuous"])
        mean = f"{_fmt(r['mean_delta'])} [{_fmt(r['ci95_lo'])}, {_fmt(r['ci95_hi'])}]" if cont else "—"
        ci90 = f"[{_fmt(r['ci90_lo'])}, {_fmt(r['ci90_hi'])}]" if cont else "—"
        frac = _pct(r["frac_items_abs_gt_margin"]) if cont else "—"
        flips = f"{r['flips_k']}/{r['flips_n']} = {_pct(r['flip_rate'])} [{_pct(r['flip_wilson_lo'])}, {_pct(r['flip_wilson_hi'])}]"
        lines.append(f"| {r['dataset']} | {r['site']} | {r['condition']} | {r['alpha']:g} | {r['role']} | {r['n_rows']} / {r['n_items']} | "
                     f"{mean} | {ci90} | {r['tost_verdict']} | {frac} | {flips} |")
    return lines


def write_z3_md(path, margin_info: dict, table: Sequence[Mapping[str, Any]], g5_info: dict, n_boot: int, seed: int, wall_s: float) -> None:
    m = margin_info
    conf = [r for r in table if r["role"] == "confirmatory" and r["continuous"]]
    inert = [r for r in conf if r["tost_verdict"] == INERT]
    not_est = [r for r in conf if r["tost_verdict"] == NOT_EST]

    def tag(r):
        return f"{r['dataset']}-{r['site']} {r['condition']} α {r['alpha']:g}"

    lines = [
        f"# Z3 — equivalence tests for \"inert\" ({DATE}; CPU only, zero new forward passes)",
        "",
        f"**Margin (fixed before any test was read): ±{m['margin']:.3f} nats** = {m['fraction']} × median Δ_model at the item's S2 flip dose α*, "
        f"median {m['median_delta_model_at_astar_S2']:.2f} nats (IQR {m['delta_model_at_astar_S2_quartiles'][0]:.2f}–{m['delta_model_at_astar_S2_quartiles'][2]:.2f}) "
        f"over {m['n_items_with_astar_S2']}/{m['n_items_total']} (pair, source) items with an α* in `x2/per_pair.csv` "
        f"(Δ_model = lo_model_at_astar_S2 − lo_model_nat; lo_model = lp(first token, other) − lp(first token, own)).",
        "",
        f"Quantity: mean Δ_model = lo_model(edited) − lo_model(natural, same source state), positive = toward the planted / other candidate; "
        f"items = (pair, source) states, null conditions averaged over null_k per item first; pair-level bootstrap ({n_boot} resamples of "
        f"pair_ids, seed {seed}) 95% and 90% CIs. TOST at α = 0.05: \"inert within margin\" iff the 90% CI lies inside ±margin. "
        f"Flip = flipped_to_other ∧ coherent, Wilson 95% CI. \"items |Δ|>m\" = fraction of items whose |Δ_model| exceeds the margin.",
        "",
    ]
    lines += table_markdown(table)
    lines += [
        "",
        f"**G5:** {g5_info['note']}",
        "",
        "**Verdicts (confirmatory rows, continuous):** "
        + (("inert within margin — " + "; ".join(tag(r) for r in inert) + ".") if inert else "none inert within margin.")
        + ((" Not established — " + "; ".join(f"{tag(r)} (mean {_fmt(r['mean_delta'])}, 90% CI [{_fmt(r['ci90_lo'])}, {_fmt(r['ci90_hi'])}])" for r in not_est) + ".") if not_est else ""),
        "",
        "Reading: a condition whose 90% CI sits inside the margin may be called inert *at that dose, on the model's first-token answer "
        "log-odds, up to ±margin*; nothing is concluded for doses or sites not listed. Equivalence is not a zero effect: rows marked "
        + ("'inert within margin' whose 95% CI excludes 0 (" + ", ".join(tag(r) for r in conf if r["tost_verdict"] == INERT and r["ci95_excludes_zero"]) + ") "
           if any(r["tost_verdict"] == INERT and r["ci95_excludes_zero"] for r in conf) else "")
        + "carry a small but detectable shift toward the other candidate (the isotropic nulls at S2/S3 shift by the same ≈ +0.2 nats, i.e. any "
        "perturbation of a confident state nudges its log-odds toward 0), bounded below a quarter of a flip-dose shift. \"Not established\" means the data do not bound "
        "the shift inside the margin (the point estimate may still be small). Descriptive rows (S1 α 2/3/4, G5 α 3/5, G5 null) are not "
        "pre-registered endpoints and carry no verdict weight. Flip rates of 0 bound a *behavioural* effect only; the continuous column is "
        "the quantity the hard rule asks for.",
        "",
        f"Inputs: cache/g_agreement/x/x2_behaviour.jsonl, results/g_agreement/x2/per_pair.csv, cache/g_agreement/g5/behaviour.jsonl "
        f"(sha256 in manifest/frozen_config_z.json). Outputs: z3_table.csv, z3_summary.json. Wall-clock {wall_s:.1f} s, 0 GPU-h.",
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def correction_bullets(margin_info: dict, table: Sequence[Mapping[str, Any]], g5_info: dict) -> List[str]:
    """One bullet per corrected sentence: original wording quoted, TOST-based replacement wording, pointer to z3/z3.md."""
    m = margin_info["margin"]
    by = {(r["dataset"], r["site"], r["condition"], float(r["alpha"])): r for r in table}

    def row(ds, site, cond, a):
        return by.get((ds, site, cond, float(a)))

    def mean_ci90(r):
        return f"{_fmt(r['mean_delta'])} [{_fmt(r['ci90_lo'])}, {_fmt(r['ci90_hi'])}]"

    def verdict_word(rs):
        vs = {r["tost_verdict"] for r in rs if r is not None}
        return INERT if vs == {INERT} else ("not established" if vs else "no rows")

    s1 = [row("X2", "S1", "planted", a) for a in (0.5, 1.0, 1.5)]
    s1_ok = [r for r in s1 if r is not None]
    s1_txt = " / ".join(mean_ci90(r) for r in s1_ok) if s1_ok else "no rows"
    s1_v = verdict_word(s1)
    r2, r3, r4 = (row("X2", "S1", "planted", a) for a in (2.0, 3.0, 4.0))
    desc = "; ".join(f"α {a:g}: {mean_ci90(r)} → {r['tost_verdict']}, {_pct(r['frac_items_abs_gt_margin'])} of items beyond the margin, "
                     f"flips {r['flips_k']}/{r['flips_n']}" for a, r in ((2.0, r2), (3.0, r3), (4.0, r4)) if r is not None)
    nulls = "; ".join(f"{site} {cond.replace('null_other', 'other-pair null').replace('null', 'isotropic null') if cond == 'null' else 'other-pair null'} α {a:g} "
                      f"{mean_ci90(r)} → {r['tost_verdict']}"
                      for site, cond, a, r in ((s_, c_, a_, row("X2", s_, c_, a_)) for s_, c_, a_ in
                                               (("S2", "null", 1.0), ("S3", "null", 1.0), ("S1", "null", 2.0), ("S1", "null_other", 2.0))) if r is not None)
    g5 = [row("G5", "L42 last", "planted", a) for a in (0.5, 1.0, 1.5, 3.0, 5.0)]
    g5_txt = ", ".join(f"{r['flips_k']}/{r['flips_n']} at α {r['alpha']:g} [{_pct(r['flip_wilson_lo'])}, {_pct(r['flip_wilson_hi'])}]" for r in g5 if r is not None) or "no rows"
    nonzero = any(r["ci95_excludes_zero"] for r in s1_ok)
    (sec_g5, q_g5), (sec_x, q_x), (sec_y, q_y) = INERT_CLAIMS
    bullets = [
        f"- **{sec_g5}** — original: \"{q_g5}\" → use instead: \"At α = 1 the last-token block-42 vector is the other state's vector and the "
        f"greedy answer does not change (flips {g5_txt}, Wilson 95%). G5 recorded no first-token log-odds, so the continuous effect of a "
        f"last-token edit is bounded only through X2-S1 (L38, last token, 128 states): mean Δ_model {s1_txt} nats at α 0.5 / 1 / 1.5 "
        f"(90% pair-bootstrap CIs) → {s1_v}, margin ±{m:.2f} nats. That the answer is reconstructed from the untouched earlier positions is a "
        f"reading consistent with this bound, not a result the 0/16 flip count establishes. See z3/z3.md.\"",
        f"- **{sec_x}** — original: \"{q_x}\" → use instead: \"At S1 (L38, last token) the planted edit shifts the model's first-token answer "
        f"log-odds by {s1_txt} nats at α 0.5 / 1 / 1.5 (mean, 90% CI): {s1_v} against the pre-stated margin ±{m:.2f} nats"
        + (" (the shift is small but its CI excludes 0, so S1 is equivalent-to-natural within the margin, not effect-free)" if nonzero else "")
        + f". Descriptively {desc}. Controls: {nulls}. The all-position state at L38 flips the answer in 98% at α ≥ 0.75 (X2 E4). "
        f"'Not load-bearing' is a bounded statement about the first-token log-odds at α ≤ 1.5, not an absolute one. See z3/z3.md.\"",
        f"- **{sec_y}** — original: \"{q_y}\" → use instead: \"At S1 ({s1_v}, ±{m:.2f} nats, α ≤ 1.5; "
        f"{'α 2 ' + mean_ci90(r2) + ' → ' + r2['tost_verdict'] + ', ' if r2 else ''}{'α 4 ' + mean_ci90(r4) + ' → ' + r4['tost_verdict'] if r4 else ''}) "
        f"the readers reach 1.1–1.2× of their natural separation at α 2 and 1.4–1.7× at α 4 while the model's normalised shift stays at 0.02–0.09; "
        f"'inert' at α 4 is not established (17/128 flips). See z3/z3.md.\"",
        "- **Not covered by Z3** — the Phase Y sentence \"The load-bearing content of the binding lies outside the J-space\" is a claim about the "
        "J-space *component* at the all-position site (Y2 J-only flips 4% vs remainder 92%), not about the last-token site; it was not tested here "
        "and would need the same TOST on the Y2 J-only Δ_model against this margin before 'none of the effect' is asserted.",
    ]
    return bullets


def append_writeup(writeup_path, bullets: Sequence[str], heading: str = f"**Phase Z corrections ({DATE})**") -> str:
    """Append-only: never touches the original sentences. Creates the dated subsection if absent; if it exists (another Z module
    wrote it first), inserts the bullets at the end of that subsection (before the next heading / rule, else at EOF)."""
    p = Path(writeup_path)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    block_intro = ("Z3 (`z3/z3.md`, pre-registered in BRIEF_Z §Z3): every \"inert\" / \"not load-bearing\" sentence about the last-token "
                   "site is replaced by a TOST statement against the margin fixed before the tests were read. Original sentences are left in "
                   "place above; the wording to use is given per bullet.")
    new_lines = [block_intro, ""] + list(bullets)
    lines = text.split("\n")
    idx = next((i for i, l in enumerate(lines) if l.strip() == heading), None)
    if idx is None:
        tail = [] if text.endswith("\n") or text == "" else [""]
        add = tail + ["", "---", "", "## Phase Z corrections", "", heading, ""] + new_lines + [""]
        out = text + "\n".join(add)
    else:
        end = len(lines)
        for j in range(idx + 1, len(lines)):
            s = lines[j].strip()
            if s.startswith("#") or s == "---" or (s.startswith("**Phase") and j != idx):
                end = j
                break
        while end > idx + 1 and lines[end - 1].strip() == "":
            end -= 1
        lines[end:end] = [""] + new_lines
        out = "\n".join(lines)
        if not out.endswith("\n"):
            out += "\n"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(out, encoding="utf-8")
    return out


# ----------------------------------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------------------------------
def main(argv=None) -> dict:
    args = parse_args(argv)
    t0 = time.time()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    per_pair = read_per_pair(args.per_pair)
    # Margin FIRST: computed, printed and recorded before any behaviour row is read.
    margin_info = compute_margin(per_pair)
    U.log(f"[z3] MARGIN = {margin_info['margin']:.4f} nats  ({margin_info['fraction']} x median {margin_info['median_delta_model_at_astar_S2']:.3f} "
          f"over {margin_info['n_items_with_astar_S2']}/{margin_info['n_items_total']} items with an S2 alpha*)")
    U.write_json(out / "z3_margin.json", {**margin_info, "recorded_at": _dt.datetime.now(_dt.timezone.utc).isoformat(), "per_pair": str(args.per_pair)})

    x2_rows = U.load_jsonl(args.behaviour)
    g5_rows = U.load_jsonl(args.g5) if Path(args.g5).exists() else []
    margin_info2, table, g5_info = run_tables(x2_rows, per_pair, g5_rows, n_boot=args.n_boot, seed=args.seed)
    assert abs(margin_info2["margin"] - margin_info["margin"]) < 1e-12
    wall = time.time() - t0

    U.write_csv(out / "z3_table.csv", table, TABLE_COLUMNS)
    write_z3_md(out / "z3.md", margin_info, table, g5_info, args.n_boot, args.seed, wall)
    bullets = correction_bullets(margin_info, table, g5_info)
    summary = {"module": MODULE, "date": DATE, "margin": margin_info, "g5": g5_info, "n_boot": args.n_boot, "seed": args.seed,
               "tost_alpha": TOST_ALPHA, "ci_rule": "inert within margin iff 90% pair-bootstrap CI of the mean inside (-margin, +margin)",
               "flip_definition": "flipped_to_other and coherent; Wilson 95% CI",
               "inputs": {"behaviour": str(args.behaviour), "per_pair": str(args.per_pair), "g5": str(args.g5)},
               "n_rows": {"x2": len(x2_rows), "g5": len(g5_rows)},
               "table": table,
               "verdicts": {f"{r['dataset']}-{r['site']}|{r['condition']}|{r['alpha']:g}": r["tost_verdict"] for r in table},
               "writeup_bullets": bullets, "wall_s": wall, "gpu_hours": 0.0,
               "command": "PYTHONPATH=. .venv/bin/python projects/g_agreement/z3_equivalence/analyze.py " + " ".join(argv or sys.argv[1:])}
    U.write_json(out / "z3_summary.json", summary)
    if not args.no_writeup:
        append_writeup(args.writeup, bullets)
        U.log(f"[z3] appended Phase Z corrections block to {args.writeup}")
    for line in table_markdown(table):
        U.log(line)
    U.log(f"[z3] wrote {out}/z3.md, z3_table.csv, z3_summary.json  ({wall:.1f} s)")
    return summary


if __name__ == "__main__":
    main()
