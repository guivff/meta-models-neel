"""V6 — multi-position Oracle Lens on the ownership L38 states (PREREG_WV.md Part V "V6"; brief_wv.md §V6). CPU only, no model calls.

    PYTHONPATH=. .venv/bin/python -m projects.g_agreement.v67_analysis.v6 --lo cache/g_agreement/w/v6_lo.jsonl \
        --out results/g_agreement/v --n-boot 1000 --seed 0

Input rows (cache/g_agreement/w/v6_lo.jsonl, written by s3_score.py --v6, one row per condition × state): reader 'olens', unit 'V6',
condition ∈ {a_last (last token, 1 marker), b_span (post-statement span as consecutive markers), c_full (the full prompt span),
d_span_shuffled (the span with positions shuffled)}, state_kind ∈ {natural (64 = 32 pairs × sources A/B), edited_full_a1 (32 S2 full-swap
α 1 states)}, state_key, s2_key, pair_id, source, state_item_id, cand_A (the NATURAL state's own answer) / cand_B, lo_own = lp(cand_A) − lp(cand_B)
("lo_toward_other" = −lo_own; the rows carry no lo_toward_edit field: for an edited state the edit is the full swap toward cand_B, so
lo_toward_edit := −lo_own), n_markers, n_tokens, unscorable.

Endpoints
  natural, per condition: within-pair win = lo_own(A) + lo_own(B) > 0 over the 32 pairs; pair bootstrap (1,000, seed 0) and Wilson CI;
                          mean margin; mean n_markers.
  paired differences:     (b) − (a), (b) − (d), (c) − (a) [and (d) − (a) for reference] of the win rate, same pairs resampled.
  pre-registered rule:    (b) − (a) ≥ +10 points with the CI excluding 0 AND win(d) < win(b) → "span reading helps"; otherwise NOT MET.
  edited, per condition:  follow = lo_toward_edit > 0 (the reader's score is on the edited-in candidate's side); shift = lo_own(edited) −
                          lo_own(natural, same state, same condition) < 0 (moved toward the edit); the natural states' own-side rate
                          (lo_own(natural) > 0) on the same states; mean Δ lo_own; all with pair-bootstrap CIs over the edited states' pairs.
Outputs: <out>/v6.md (≤ 30 lines, one table), v6.csv (long: block ∈ {natural, diff, edited}), v6_summary.json.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.v67_analysis import common as K  # noqa: E402

MODULE = "v6"
CONDITIONS: tuple[str, ...] = ("a_last", "b_span", "c_full", "d_span_shuffled")
LABELS = {"a_last": "(a) last token", "b_span": "(b) post-statement span", "c_full": "(c) full prompt span", "d_span_shuffled": "(d) span shuffled"}
DIFFS: tuple[tuple[str, str], ...] = (("b_span", "a_last"), ("b_span", "d_span_shuffled"), ("c_full", "a_last"), ("d_span_shuffled", "a_last"))
RULE_DIFF = ("b_span", "a_last")
RULE_MIN_POINTS = 0.10
NATURAL, EDITED = "natural", "edited_full_a1"
DEFAULT_LO = K.W_CACHE / "v6_lo.jsonl"


# ------------------------------------------------------------------ loading
def load_rows(path: Path) -> List[dict]:
    rows = [r for r in K.read_jsonl(path) if r.get("unit") == "V6" and r.get("reader", "olens") == "olens"]
    bad = [r for r in rows if r.get("condition") not in CONDITIONS]
    if bad:
        raise U.AnalysisError(f"v6: unknown condition(s) {sorted({r.get('condition') for r in bad})}")
    return rows


def _lo(r: dict) -> Optional[float]:
    if r.get("unscorable") or r.get("lo_own") is None:
        return None
    return float(r["lo_own"])


def natural_by_condition(rows: Sequence[dict]) -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
    """{condition: {pair_id: {source: lo_own}}} over the natural states (a state appearing twice keeps its first row)."""
    out: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {c: defaultdict(dict) for c in CONDITIONS}
    for r in rows:
        if r.get("state_kind") != NATURAL:
            continue
        d = out[r["condition"]][r["pair_id"]]
        d.setdefault(r["source"], _lo(r))
    return out


def edited_by_condition(rows: Sequence[dict]) -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = {c: [] for c in CONDITIONS}
    for r in rows:
        if r.get("state_kind") == EDITED:
            out[r["condition"]].append(r)
    return out


# ------------------------------------------------------------------ analysis
def analyse(rows: Sequence[dict], n_boot: int = K.N_BOOT, seed: int = K.SEED) -> Dict[str, Any]:
    nat = natural_by_condition(rows)
    ed = edited_by_condition(rows)
    flags = {c: K.win_flags(nat[c]) for c in CONDITIONS}
    natural: Dict[str, Any] = {}
    for c in CONDITIONS:
        r = K.rate(flags[c], n_boot, seed)
        mg = K.margins(nat[c])
        nm = [int(x["n_markers"]) for x in rows if x["condition"] == c and x.get("state_kind") == NATURAL and x.get("n_markers") is not None]
        natural[c] = {**r, "label": LABELS[c], "n_states": sum(len(d) for d in nat[c].values()), "mean_margin_nats": float(np.mean(list(mg.values()))) if mg else float("nan"),
                      "mean_n_markers": float(np.mean(nm)) if nm else float("nan"), "per_pair": {pid: {"win": w, "margin": mg.get(pid)} for pid, w in flags[c]}}
    diffs = {f"{x}-{y}": {"minus": x, "from": y, **K.rate_diff(flags[x], flags[y], n_boot, seed)} for x, y in DIFFS}
    edited: Dict[str, Any] = {}
    for c in CONDITIONS:
        follow, shift, nat_own, dlo = [], [], [], defaultdict(list)
        n_missing_nat = 0
        for r in ed[c]:
            lo_e = _lo(r)
            lo_n = nat[c].get(r["pair_id"], {}).get(r["source"])
            pid = r["pair_id"]
            follow.append((pid, None if lo_e is None else bool(-lo_e > 0)))
            if lo_n is None:
                n_missing_nat += 1
            shift.append((pid, None if lo_e is None or lo_n is None else bool(lo_e - lo_n < 0)))
            nat_own.append((pid, None if lo_n is None else bool(lo_n > 0)))
            if lo_e is not None and lo_n is not None:
                dlo[pid].append(lo_e - lo_n)
        edited[c] = {"label": LABELS[c], "n_states": len(ed[c]), "n_missing_natural": n_missing_nat, "follow": K.rate(follow, n_boot, seed), "shift": K.rate(shift, n_boot, seed),
                     "natural_own_side": K.rate(nat_own, n_boot, seed), "delta_lo_own": K.pair_mean(dlo, n_boot, seed)}
    key = f"{RULE_DIFF[0]}-{RULE_DIFF[1]}"
    d = diffs[key]
    pb, pd = natural["b_span"]["p"], natural["d_span_shuffled"]["p"]
    cond_gain = bool(np.isfinite(d["diff"]) and d["diff"] >= RULE_MIN_POINTS and np.isfinite(d["lo"]) and d["lo"] > 0)
    cond_shuffle = bool(np.isfinite(pb) and np.isfinite(pd) and pd < pb)
    rule = {"text": "(b) beats (a) by >= 10 points within-pair win with the pair-bootstrap CI excluding 0, and (d) is below (b)", "min_points": RULE_MIN_POINTS,
            "b_minus_a": d["diff"], "b_minus_a_ci": [d["lo"], d["hi"]], "gain_ok": cond_gain, "win_b": pb, "win_d": pd, "shuffled_below_span": cond_shuffle,
            "met": bool(cond_gain and cond_shuffle), "verdict": "span reading helps" if (cond_gain and cond_shuffle) else "NOT MET"}
    return {"module": MODULE, "conditions": list(CONDITIONS), "n_rows": len(rows), "n_natural_rows": sum(1 for r in rows if r.get("state_kind") == NATURAL),
            "n_edited_rows": sum(1 for r in rows if r.get("state_kind") == EDITED), "orientation": "lo_own = lp(own) − lp(other); pair win = lo_own(A) + lo_own(B) > 0; edited: lo_toward_edit = −lo_own",
            "natural": natural, "diffs": diffs, "edited": edited, "rule": rule}


# ------------------------------------------------------------------ outputs
def csv_rows(s: Mapping) -> List[dict]:
    out = []
    for c in CONDITIONS:
        n = s["natural"][c]
        out.append({"block": "natural", "condition": c, "label": n["label"], "n_pairs": n["n"], "n_states": n["n_states"], "k_win": n["k"], "win": n["p"], "boot_lo": n["boot_lo"], "boot_hi": n["boot_hi"],
                    "wilson_lo": n["wilson_lo"], "wilson_hi": n["wilson_hi"], "mean_margin_nats": n["mean_margin_nats"], "mean_n_markers": n["mean_n_markers"], "n_excluded_pairs": n["n_excluded"]})
    for key, d in s["diffs"].items():
        out.append({"block": "diff", "condition": key, "label": f"{LABELS[d['minus']]} − {LABELS[d['from']]}", "win": d["diff"], "boot_lo": d["lo"], "boot_hi": d["hi"], "excludes_zero": d["excludes_zero"]})
    for c in CONDITIONS:
        e = s["edited"][c]
        out.append({"block": "edited", "condition": c, "label": e["label"], "n_states": e["n_states"], "n_pairs": e["follow"]["n_pairs"], "k_win": e["follow"]["k"], "win": e["follow"]["p"],
                    "boot_lo": e["follow"]["boot_lo"], "boot_hi": e["follow"]["boot_hi"], "wilson_lo": e["follow"]["wilson_lo"], "wilson_hi": e["follow"]["wilson_hi"],
                    "shift_k": e["shift"]["k"], "shift_n": e["shift"]["n"], "shift": e["shift"]["p"], "shift_lo": e["shift"]["boot_lo"], "shift_hi": e["shift"]["boot_hi"],
                    "natural_own_side": e["natural_own_side"]["p"], "natural_own_side_lo": e["natural_own_side"]["boot_lo"], "natural_own_side_hi": e["natural_own_side"]["boot_hi"],
                    "delta_lo_own_mean": e["delta_lo_own"]["mean"], "delta_lo_own_lo": e["delta_lo_own"]["lo"], "delta_lo_own_hi": e["delta_lo_own"]["hi"], "n_missing_natural": e["n_missing_natural"]})
    return out


CSV_COLUMNS = ["block", "condition", "label", "n_pairs", "n_states", "k_win", "win", "boot_lo", "boot_hi", "wilson_lo", "wilson_hi", "excludes_zero", "mean_margin_nats", "mean_n_markers",
               "n_excluded_pairs", "shift_k", "shift_n", "shift", "shift_lo", "shift_hi", "natural_own_side", "natural_own_side_lo", "natural_own_side_hi", "delta_lo_own_mean", "delta_lo_own_lo",
               "delta_lo_own_hi", "n_missing_natural"]


def markdown(s: Mapping, meta: Mapping) -> str:
    r = s["rule"]
    L = [f"# V6 — multi-position Oracle Lens, ownership L38 (PREREG_WV.md Part V; brief_wv.md §V6)",
         f"Run {meta['run_at']}; input {meta['inputs']['v6_lo']['path']} (sha256 {str(meta['inputs']['v6_lo']['sha256'])[:12]}); {s['n_natural_rows']} natural + {s['n_edited_rows']} edited rows; "
         f"pair bootstrap {meta['n_boot']} (seed {meta['seed']}), 95 % percentile CI; Wilson CI in brackets. Win = lo_own(A) + lo_own(B) > 0 (Oracle lp(own) − lp(other)).",
         "",
         "| arm | natural: within-pair win (32 pairs) | mean margin (nats) | markers | edited (full swap α 1): follow = lo_toward_edit > 0 | shift (edited − natural < 0) | natural own-side on the same states | mean Δ lo_own |",
         "|---|---|---|---|---|---|---|---|"]
    for c in CONDITIONS:
        n, e = s["natural"][c], s["edited"][c]
        L.append(f"| {n['label']} | {K.fmt_rate(n)} | {K.fmt_signed(n['mean_margin_nats'])} | {n['mean_n_markers']:.1f} | {K.fmt_rate(e['follow'])} | "
                 f"{K.fmt_rate(e['shift'])} | {K.pct(e['natural_own_side']['p'])}% (n={e['natural_own_side']['n']}) | {K.fmt_signed(e['delta_lo_own']['mean'])} [{K.fmt_signed(e['delta_lo_own']['lo'])}, {K.fmt_signed(e['delta_lo_own']['hi'])}] |")
    L.append("")
    L.append("| paired difference of the natural win (points) | Δ [95 % pair-bootstrap CI] | CI excludes 0 |")
    L.append("|---|---|---|")
    for key, d in s["diffs"].items():
        L.append(f"| {LABELS[d['minus']]} − {LABELS[d['from']]} | {K.fmt_diff(d)} | {'yes' if d['excludes_zero'] else 'no'} |")
    L += ["",
          f"**Pre-registered rule.** {r['text']}. Observed: (b) − (a) = {100 * r['b_minus_a']:+.1f} points [{100 * r['b_minus_a_ci'][0]:+.1f}, {100 * r['b_minus_a_ci'][1]:+.1f}] "
          f"(gain ≥ 10 with CI > 0: {'yes' if r['gain_ok'] else 'no'}); win(d) = {K.pct(r['win_d'])}% vs win(b) = {K.pct(r['win_b'])}% (shuffled below span: {'yes' if r['shuffled_below_span'] else 'no'}).",
          f"**Verdict: {r['verdict']}.**",
          "",
          "Caveats: one reader (Oracle, carrier layer 38) and one family; the edited states are the first 32 S2 full-swap α 1 ownership rows (not a fresh sample); 'follow' uses the sign of the edited",
          "score only, 'shift' the paired change against the same state's natural score; (c) differs from (b) in marker count, so a (c) − (b) gap mixes span content with prompt length."]
    return "\n".join(L) + "\n"


def run(lo: Path = DEFAULT_LO, out: Path = K.RESULTS_V, n_boot: int = K.N_BOOT, seed: int = K.SEED, argv: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    lo, out = Path(lo), Path(out)
    K.require_files([lo])
    rows = load_rows(lo)
    if not rows:
        raise U.AnalysisError(f"v6: no unit=V6 olens rows in {lo}")
    s = analyse(rows, n_boot, seed)
    meta = K.run_meta({"v6_lo": lo}, n_boot, seed, argv)
    summary = {**s, "meta": meta}
    out.mkdir(parents=True, exist_ok=True)
    U.write_json(out / "v6_summary.json", summary)
    U.write_csv(out / "v6.csv", csv_rows(s), CSV_COLUMNS)
    md = markdown(s, meta)
    (out / "v6.md").write_text(md, encoding="utf-8")
    U.log(f"[v6] {s['n_natural_rows']} natural + {s['n_edited_rows']} edited rows; " + "; ".join(f"{c}: {K.pct(s['natural'][c]['p'])}%" for c in CONDITIONS) +
          f"; (b)−(a) {K.fmt_diff(s['diffs']['b_span-a_last'])}; verdict {s['rule']['verdict']}; wrote {out}/v6.{{md,csv,summary.json}}")
    return summary


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lo", type=Path, default=DEFAULT_LO)
    ap.add_argument("--out", type=Path, default=K.RESULTS_V)
    ap.add_argument("--n-boot", type=int, default=K.N_BOOT)
    ap.add_argument("--seed", type=int, default=K.SEED)
    a = ap.parse_args(argv)
    run(a.lo, a.out, a.n_boot, a.seed, argv=[f"projects.g_agreement.v67_analysis.{MODULE}"] + (list(argv) if argv is not None else sys.argv[1:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
