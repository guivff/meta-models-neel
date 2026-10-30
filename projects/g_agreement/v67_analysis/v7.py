"""V7 — target-private facts pilot (PREREG_WV.md Part V "V7"; brief_wv.md §V7). CPU only, no model calls.

    PYTHONPATH=. .venv/bin/python -m projects.g_agreement.v67_analysis.v7 --lo cache/g_agreement/w/s3_lo.jsonl \
        --items projects/g_agreement/banks/w/items_v7.json --s1 cache/g_agreement/w/s1_target.jsonl --out results/g_agreement/v \
        --design-out projects/g_agreement/banks/w/items_v7_confirmatory_design.md --n-boot 1000 --seed 0

Inputs
  items_v7.json      16 ownership pairs (item_id, pair_id, version A/B, prompt_text = the VISIBLE prompt, identical within a pair; the binding
                     is only in ``preamble`` shown to the target as a system turn at capture; primary.candidates / answer; construction).
  s3_lo.jsonl        reader rows of s3_score.py: unit 'S1' (block-42 last token) and 'S1@L38' (layer 38), family 'v7', reader ∈ {jlens, olens,
                     skip_a, probe} (NLA's phase B scores the counts S1 states and the S2 read-backs only → no NLA V7 rows; reported as not
                     scored), layer, item_id, pair_id, version, lo_own = lp(own) − lp(other), unscorable.
  s1_target.jsonl    (optional) the target's greedy answer WITH the preamble (family 'v7': parsed, correct, lo_model = lp(other) − lp(own),
                     lo_model_unscorable) → the ceiling: accuracy on the preamble-conditioned prompt and its within-pair win (own frame = −lo_model).

Endpoints: per reader × layer, within-pair win = lo_own(A) + lo_own(B) > 0 over the 16 pairs, pair bootstrap (1,000, seed 0) and Wilson CI.
Prompt-only baseline = 50 % by construction: the visible prompt is identical across a pair, so any prompt-only answer is identical for both
versions and wins exactly one of them (verified here: prompt_text identical in every pair). Pre-registered rule: any reader ≥ 0.70 with the
bootstrap CI excluding 0.5 → positive pilot → the 48-pair confirmatory design file is written (only then).
Outputs: <out>/v7.md (≤ 30 lines), v7.csv (one row per reader × layer + the target ceiling), v7_summary.json; the design file if positive.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.stats import wilson  # noqa: E402
from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.v67_analysis import common as K  # noqa: E402

MODULE = "v7"
FAMILY = "v7"
UNITS = {"S1": 42, "S1@L38": 38}
READERS: tuple[str, ...] = ("jlens", "olens", "skip_a", "probe", "nla")
EXPECTED_CELLS: tuple[tuple[str, int], ...] = (("jlens", 42), ("jlens", 38), ("olens", 42), ("olens", 38), ("skip_a", 42), ("probe", 42), ("probe", 38), ("nla", 42))
NOT_SCORED_REASON = {"nla": "phase B scores the counts S1 states and the S2 read-backs only (PREREG deviation 2026-10-12 05:15 UTC)",
                     "skip_a": "block-1 injection is layer-free; scored on the block-42 states only"}
POSITIVE_WIN = 0.70
DEFAULT_LO = K.W_CACHE / "s3_lo.jsonl"
DEFAULT_ITEMS = K.BANK_W / "items_v7.json"
DEFAULT_S1 = K.W_CACHE / "s1_target.jsonl"
DEFAULT_DESIGN = K.BANK_W / "items_v7_confirmatory_design.md"
LABELS = {"jlens": "J-lens", "olens": "Oracle lens", "skip_a": "skip-lens A", "probe": "probe (held-out fold)", "nla": "NLA", "target": "target (with preamble)"}


# ------------------------------------------------------------------ loading
def load_items(path: Path) -> Dict[str, Dict[str, dict]]:
    """{pair_id: {version: item}}."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items = raw["items"] if isinstance(raw, dict) and "items" in raw else (raw.get("pairs") if isinstance(raw, dict) else raw)
    out: Dict[str, Dict[str, dict]] = defaultdict(dict)
    for it in items:
        if "A" in it and isinstance(it.get("A"), dict):
            for v in "AB":
                out[it["pair_id"]][v] = {**it[v], "pair_id": it["pair_id"], "version": v}
        else:
            out[it["pair_id"]][it["version"]] = it
    return {p: d for p, d in out.items() if "A" in d and "B" in d}


def prompt_identity(pairs: Mapping[str, Mapping[str, dict]]) -> Dict[str, Any]:
    same = {p: d["A"].get("prompt_text") == d["B"].get("prompt_text") for p, d in pairs.items()}
    same_po = {p: d["A"].get("prompt_only_text") == d["B"].get("prompt_only_text") for p, d in pairs.items() if "prompt_only_text" in d["A"]}
    return {"n_pairs": len(pairs), "n_prompt_text_identical": sum(same.values()), "pairs_differing": sorted(p for p, s in same.items() if not s),
            "n_prompt_only_text_identical": (sum(same_po.values()) if same_po else None), "all_identical": all(same.values()) and all(same_po.values()),
            "baseline": "prompt-only baseline = 50 % by construction (identical visible prompt → identical prompt-only answer for both versions)"}


def _layer(r: dict) -> Optional[int]:
    if r.get("layer") is not None:
        return int(r["layer"])
    return UNITS.get(str(r.get("unit")))


def load_reader_rows(path: Path) -> List[dict]:
    return [r for r in K.read_jsonl(path) if r.get("family") == FAMILY and str(r.get("unit", "")).startswith("S1") and r.get("item_id")]


def lo_by_cell(rows: Sequence[dict]) -> Dict[Tuple[str, int], Dict[str, Dict[str, Optional[float]]]]:
    """{(reader, layer): {pair_id: {version: lo_own}}} (a duplicate key keeps the first row)."""
    out: Dict[Tuple[str, int], Dict[str, Dict[str, Optional[float]]]] = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        L = _layer(r)
        if L is None:
            continue
        lo = None if r.get("unscorable") or r.get("lo_own") is None else float(r["lo_own"])
        out[(str(r["reader"]), L)][str(r["pair_id"])].setdefault(str(r["version"]), lo)
    return out


# ------------------------------------------------------------------ analysis
def cell_result(lo_pairs: Mapping[str, Mapping[str, Optional[float]]], pair_ids: Sequence[str], n_boot: int, seed: int) -> Dict[str, Any]:
    full = {p: dict(lo_pairs.get(p, {})) for p in pair_ids}
    flags = K.win_flags(full)
    r = K.rate(flags, n_boot, seed)
    mg = K.margins(full)
    n_unscorable = sum(1 for p in pair_ids for v in "AB" if v in lo_pairs.get(p, {}) and lo_pairs[p][v] is None)
    n_missing = sum(1 for p in pair_ids for v in "AB" if v not in lo_pairs.get(p, {}))
    positive = bool(r["n"] and r["p"] >= POSITIVE_WIN and np.isfinite(r["boot_lo"]) and r["boot_lo"] > 0.5)
    return {**r, "n_pairs_total": len(pair_ids), "n_unscorable_rows": n_unscorable, "n_missing_rows": n_missing,
            "mean_margin_nats": float(np.mean(list(mg.values()))) if mg else float("nan"), "positive": positive,
            "per_pair": {pid: {"win": w, "margin": mg.get(pid)} for pid, w in flags}}


def target_ceiling(s1_rows: Sequence[dict], pair_ids: Sequence[str], n_boot: int, seed: int) -> Dict[str, Any]:
    """The target's greedy accuracy WITH the preamble (Wilson + pair bootstrap over items tagged by pair) and its within-pair win in the own frame
    (lo = −lo_model = lp(own) − lp(other) at the first answer token)."""
    rows = [r for r in s1_rows if r.get("family") == FAMILY]
    by: Dict[str, Dict[str, dict]] = defaultdict(dict)
    for r in rows:
        by[str(r["pair_id"])].setdefault(str(r["version"]), r)
    acc_flags = [(p, (bool(by[p][v]["correct"]) if v in by.get(p, {}) and by[p][v].get("correct") is not None else None)) for p in pair_ids for v in "AB"]
    lo = {p: {v: (None if by[p][v].get("lo_model_unscorable") or by[p][v].get("lo_model") is None else -float(by[p][v]["lo_model"])) for v in "AB" if v in by.get(p, {})} for p in pair_ids}
    win = K.rate(K.win_flags(lo), n_boot, seed)
    acc = K.rate(acc_flags, n_boot, seed)
    return {"available": bool(rows), "n_rows": len(rows), "accuracy": acc, "pair_win_lo_model": win, "orientation": "own-frame lo = −lo_model (S1 lo_model = lp(other) − lp(own))",
            "answers": {p: {v: {"parsed": by[p][v].get("parsed"), "true": by[p][v].get("true_answer"), "correct": by[p][v].get("correct")} for v in "AB" if v in by.get(p, {})} for p in pair_ids}}


def analyse(pairs: Mapping[str, Mapping[str, dict]], reader_rows: Sequence[dict], s1_rows: Optional[Sequence[dict]], n_boot: int = K.N_BOOT, seed: int = K.SEED) -> Dict[str, Any]:
    pair_ids = sorted(pairs)
    cells = lo_by_cell(reader_rows)
    keys = sorted(set(cells) | set(EXPECTED_CELLS), key=lambda k: (READERS.index(k[0]) if k[0] in READERS else 99, -k[1]))
    results: Dict[str, Any] = {}
    for rd, L in keys:
        name = f"{rd}@L{L}"
        if (rd, L) in cells:
            results[name] = {"reader": rd, "layer": L, "scored": True, **cell_result(cells[(rd, L)], pair_ids, n_boot, seed)}
        else:
            results[name] = {"reader": rd, "layer": L, "scored": False, "reason": NOT_SCORED_REASON.get(rd, "no rows in s3_lo.jsonl"), "k": 0, "n": 0, "p": float("nan"),
                             "boot_lo": float("nan"), "boot_hi": float("nan"), "wilson_lo": float("nan"), "wilson_hi": float("nan"), "positive": False, "n_pairs_total": len(pair_ids)}
    positives = [k for k, v in results.items() if v.get("positive")]
    best = max((k for k, v in results.items() if v.get("scored") and v["n"]), key=lambda k: results[k]["p"], default=None)
    rule = {"text": "any reader >= 0.70 within-pair win with the pair-bootstrap CI excluding 0.5 → positive pilot → design a 48-pair confirmatory set",
            "threshold": POSITIVE_WIN, "positive_cells": positives, "best_cell": best, "best_win": (results[best]["p"] if best else float("nan")),
            "met": bool(positives), "verdict": "POSITIVE pilot — 48-pair confirmatory set designed" if positives else "NOT MET (no reader reaches 0.70 with CI excluding 0.5)"}
    ceiling = target_ceiling(s1_rows or [], pair_ids, n_boot, seed) if s1_rows is not None else {"available": False, "n_rows": 0, "reason": "s1_target.jsonl not given / missing"}
    return {"module": MODULE, "n_pairs": len(pair_ids), "pair_ids": pair_ids, "n_reader_rows": len(reader_rows), "baseline": prompt_identity(pairs),
            "orientation": "lo_own = lp(own) − lp(other); pair win = lo_own(A) + lo_own(B) > 0", "cells": results, "rule": rule, "target_ceiling": ceiling}


# ------------------------------------------------------------------ confirmatory design
def design_markdown(s: Mapping, pilot_items: Mapping[str, Mapping[str, dict]]) -> str:
    pos = ", ".join(s["rule"]["positive_cells"]) or "none"
    names_used = sorted({n for d in pilot_items.values() for v in d.values() for n in (v.get("construction", {}).get("names") or v.get("primary", {}).get("candidates") or [])})
    objs_used = sorted({tuple(v.get("construction", {}).get("object_pair") or []) for d in pilot_items.values() for v in d.values()} - {()})
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    L = [
        "# V7 confirmatory design — 48 target-private ownership pairs (pre-registered BEFORE collection)",
        f"Written {now} by v67_analysis/v7.py because the pilot was positive (cells: {pos}; best {s['rule']['best_cell']} = {K.pct(s['rule']['best_win'])}%).",
        "This file is a design, not a bank: the items are generated by banks/w/build_w_bank.py (V7 builder) with the seed below, then frozen by sha256 before any capture.",
        "",
        "## Factors (fully crossed, 8 × 3 × 2 = 48 pairs)",
        "- **8 name sets**: 8 disjoint pairs of names (N1, N2), single-token first names, none of the pilot's names "
        f"({', '.join(names_used)}); balanced for gender and length; drawn from the bank name pool with seed 20261013.",
        f"- **3 object pairs**: 3 new (o1, o2) pairs of colour + noun objects, disjoint from the pilot's {len(objs_used)} object pairs; the asked object is o1 in every pair.",
        "- **2 mention orders**: the answer-holder is first-mentioned in the preamble in version A for half the pairs (order = first) and second-mentioned for the other half (order = second);"
        " within a pair, A and B swap the binding (A: N1 has o1; B: N2 has o1), so the mention order of the ANSWER flips between versions, as in the pilot.",
        "- **Both preamble roles** (within-pair factor, every pair captured twice): role = `system` (the preamble as the system turn, as in the pilot) and role = `user`"
        " (the preamble prepended to the user turn, separated by a blank line). 48 pairs × 2 roles = 96 pair-captures = 192 states per layer.",
        "- Preamble templates p0 / p1 alternate across pairs (24 / 24), balanced within every name set and object pair.",
        "",
        "## Held fixed",
        "- The visible prompt is `Who has the {o1}? Answer with the name only.` — identical within a pair, so the prompt-only baseline is 50 % by construction (verified by the builder).",
        "- Capture: layers 38 and 42, last token (all readers) and the post-statement span (Oracle, V6 (b) condition); same target, same chat render as the pilot.",
        "- Readers: every pilot reader (J-lens, Oracle, skip-lens A, held-out probe) at the layers it was scored at in the pilot; NLA if phase-B budget allows.",
        "",
        "## Pre-registered decision rule (confirmatory)",
        f"- Primary: the pilot's positive cell(s) [{pos}] reach within-pair win ≥ 0.70 with the pair-bootstrap CI (1,000 resamples, seed 0) excluding 0.5 over the 48 pairs, role = system.",
        "- Secondary: the same rule per role (system / user) and per mention order; a role difference ≥ 10 points with the paired CI excluding 0 is reported as a role effect.",
        "- Ceiling: the target's own accuracy with the preamble (greedy) on the 96 pair-captures; a cell is read against the ceiling, not against 100 %.",
        "- Any reader not positive in the pilot is exploratory here (reported, not a confirmation).",
        "",
        "## Sample size",
        "- 48 pairs: a true win of 0.80 gives a Wilson lower bound ≈ 0.67 and an expected bootstrap lower bound above 0.5 with power > 0.95; the pilot's 16 pairs cannot separate 0.70 from 0.5 reliably.",
    ]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ outputs
def csv_rows(s: Mapping) -> List[dict]:
    out = []
    for name, c in s["cells"].items():
        out.append({"reader": c["reader"], "layer": c["layer"], "cell": name, "scored": c["scored"], "n_pairs": c.get("n", 0), "n_pairs_total": c.get("n_pairs_total"), "k_win": c.get("k", 0), "win": c.get("p"),
                    "boot_lo": c.get("boot_lo"), "boot_hi": c.get("boot_hi"), "wilson_lo": c.get("wilson_lo"), "wilson_hi": c.get("wilson_hi"), "mean_margin_nats": c.get("mean_margin_nats"),
                    "n_unscorable_rows": c.get("n_unscorable_rows"), "n_missing_rows": c.get("n_missing_rows"), "positive": c.get("positive"), "reason": c.get("reason", "")})
    t = s["target_ceiling"]
    if t.get("available"):
        a, w = t["accuracy"], t["pair_win_lo_model"]
        out.append({"reader": "target", "layer": "", "cell": "target_accuracy_with_preamble", "scored": True, "n_pairs": a["n"], "k_win": a["k"], "win": a["p"], "boot_lo": a["boot_lo"], "boot_hi": a["boot_hi"],
                    "wilson_lo": a["wilson_lo"], "wilson_hi": a["wilson_hi"], "reason": "ceiling: greedy accuracy over the 32 preamble-conditioned items"})
        out.append({"reader": "target", "layer": "", "cell": "target_pair_win_lo_model", "scored": True, "n_pairs": w["n"], "k_win": w["k"], "win": w["p"], "boot_lo": w["boot_lo"], "boot_hi": w["boot_hi"],
                    "wilson_lo": w["wilson_lo"], "wilson_hi": w["wilson_hi"], "reason": "ceiling: within-pair win of the target's first-token log-odds"})
    out.append({"reader": "prompt_only", "layer": "", "cell": "prompt_only_baseline", "scored": True, "n_pairs": s["n_pairs"], "win": 0.5, "reason": s["baseline"]["baseline"]})
    return out


CSV_COLUMNS = ["reader", "layer", "cell", "scored", "n_pairs", "n_pairs_total", "k_win", "win", "boot_lo", "boot_hi", "wilson_lo", "wilson_hi", "mean_margin_nats", "n_unscorable_rows", "n_missing_rows",
               "positive", "reason"]


def markdown(s: Mapping, meta: Mapping, design_path: Optional[Path]) -> str:
    b, r, t = s["baseline"], s["rule"], s["target_ceiling"]
    L = [f"# V7 — target-private facts pilot, {s['n_pairs']} ownership pairs (PREREG_WV.md Part V; brief_wv.md §V7)",
         f"Run {meta['run_at']}; rows {meta['inputs']['s3_lo']['path']} (sha256 {str(meta['inputs']['s3_lo']['sha256'])[:12]}), items {meta['inputs']['items_v7']['path']}; "
         f"pair bootstrap {meta['n_boot']} (seed {meta['seed']}), 95 % percentile CI; Wilson in brackets. Win = lo_own(A) + lo_own(B) > 0, lo_own = lp(own) − lp(other).",
         "",
         "| reader @ layer | within-pair win | mean margin (nats) | unscorable / missing rows | ≥ 0.70 & CI > 0.5 |",
         "|---|---|---|---|---|"]
    for name, c in s["cells"].items():
        if c["scored"]:
            L.append(f"| {LABELS.get(c['reader'], c['reader'])} @ L{c['layer']} | {K.fmt_rate(c)} | {K.fmt_signed(c['mean_margin_nats'])} | {c['n_unscorable_rows']} / {c['n_missing_rows']} | {'YES' if c['positive'] else 'no'} |")
        else:
            L.append(f"| {LABELS.get(c['reader'], c['reader'])} @ L{c['layer']} | not scored — {c['reason']} | – | – | – |")
    L.append(f"| prompt-only baseline (visible text) | 50.0% by construction ({b['n_prompt_text_identical']}/{b['n_pairs']} pairs have an identical visible prompt"
             + (f"; prompt_only_text identical in {b['n_prompt_only_text_identical']}" if b.get('n_prompt_only_text_identical') is not None else "") + ") | – | – | – |")
    if t.get("available"):
        a, w = t["accuracy"], t["pair_win_lo_model"]
        L.append(f"| target WITH preamble (ceiling) | greedy accuracy {K.fmt_rate(a)} (items); pair win by first-token log-odds {K.fmt_rate(w)} | – | – | – |")
    else:
        L.append(f"| target WITH preamble (ceiling) | not available — {t.get('reason', 'no family=v7 rows in s1_target.jsonl')} | – | – | – |")
    L += ["",
          f"**Prompt-only baseline.** {b['baseline']}; the pilot therefore cannot be won by reading the visible text, only from the state.",
          f"**Pre-registered rule.** {r['text']}. Positive cells: {', '.join(r['positive_cells']) or 'none'}; best cell {r['best_cell']} = {K.pct(r['best_win'])}%.",
          f"**Verdict: {r['verdict']}.**" + (f" Design written to {design_path}." if design_path else ""),
          "",
          "Caveats: 16 pairs is a pilot (a 0.70 point estimate has a Wilson lower bound ≈ 0.47 at n = 16, so only a near-ceiling reader can pass); NLA has no V7 rows (phase B budget);",
          "the preamble is a system turn, so the 'target-private' fact is in the target's context but absent from the read vector's visible prompt, as the brief defines it."]
    return "\n".join(L) + "\n"


def run(lo: Path = DEFAULT_LO, items: Path = DEFAULT_ITEMS, s1: Optional[Path] = DEFAULT_S1, out: Path = K.RESULTS_V, design_out: Path = DEFAULT_DESIGN,
        n_boot: int = K.N_BOOT, seed: int = K.SEED, argv: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    lo, items, out, design_out = Path(lo), Path(items), Path(out), Path(design_out)
    K.require_files([lo, items])
    pairs = load_items(items)
    if not pairs:
        raise U.AnalysisError(f"v7: no complete pairs in {items}")
    rows = load_reader_rows(lo)
    if not rows:
        raise U.AnalysisError(f"v7: no family=v7 S1 rows in {lo}")
    s1_rows = K.read_jsonl(s1) if s1 is not None and Path(s1).exists() else None
    if s1 is not None and s1_rows is None:
        U.log(f"[v7] note: {s1} missing; the target ceiling is reported as not available")
    s = analyse(pairs, rows, s1_rows, n_boot, seed)
    meta = K.run_meta({"s3_lo": lo, "items_v7": items, "s1_target": Path(s1) if s1 is not None else Path("/dev/null")}, n_boot, seed, argv)
    design_path = None
    if s["rule"]["met"]:
        design_out.parent.mkdir(parents=True, exist_ok=True)
        design_out.write_text(design_markdown(s, pairs), encoding="utf-8")
        design_path = design_out
    summary = {**s, "meta": meta, "design_file": (str(design_path) if design_path else None)}
    out.mkdir(parents=True, exist_ok=True)
    U.write_json(out / "v7_summary.json", summary)
    U.write_csv(out / "v7.csv", csv_rows(s), CSV_COLUMNS)
    (out / "v7.md").write_text(markdown(s, meta, design_path), encoding="utf-8")
    U.log(f"[v7] {s['n_pairs']} pairs, {len(rows)} rows; " + "; ".join(f"{k}: {K.pct(c['p'])}%" for k, c in s["cells"].items() if c["scored"]) +
          f"; verdict {s['rule']['verdict']}; wrote {out}/v7.{{md,csv,summary.json}}" + (f"; design {design_path}" if design_path else ""))
    return summary


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lo", type=Path, default=DEFAULT_LO)
    ap.add_argument("--items", type=Path, default=DEFAULT_ITEMS)
    ap.add_argument("--s1", type=Path, default=DEFAULT_S1, help="s1_target.jsonl (optional; the ceiling is skipped when missing)")
    ap.add_argument("--out", type=Path, default=K.RESULTS_V)
    ap.add_argument("--design-out", type=Path, default=DEFAULT_DESIGN)
    ap.add_argument("--n-boot", type=int, default=K.N_BOOT)
    ap.add_argument("--seed", type=int, default=K.SEED)
    a = ap.parse_args(argv)
    run(a.lo, a.items, a.s1, a.out, a.design_out, a.n_boot, a.seed, argv=[f"projects.g_agreement.v67_analysis.{MODULE}"] + (list(argv) if argv is not None else sys.argv[1:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
