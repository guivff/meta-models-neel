"""Y3 analysis (CPU; BRIEF_Y §Y3 endpoints E14, E15).

Inputs: dataset/items_x.json, dataset/items_x3_selected.json, cache/g_agreement/y/y3_{x1,x2,x3}_lo.jsonl (y3_readers/collect.py),
cache/g_agreement/x/x2_behaviour.jsonl, results/g_agreement/{x1,x3}/summary.json (the three Phase X readers, for the figure),
results/g_agreement/y3/sae_fve.json, results/g_agreement/y3/rlens_format.json.

  E14  entry gate per new reader: X1 E1 paired win per family (x1_bank/analyze.e1_reader_family: win = lo_A + lo_B > 0, pair
       bootstrap + Wilson CIs) and E3 (LO on the family mean state within ±1 nat). PASS iff ownership AND mapping SEPARATE
       (win ≥ 0.75, bootstrap CI excluding 0.5) and E3 is within the band on both (the SAE probe has no nat scale: E3 is
       reported as not applicable and the gate is E1-only, flagged). Readers failing the gate are reported, not mapped.
  E15  readers passing the gate (computed for every reader with rows; the gate flag travels with the numbers):
       X2 at S2 — follow at the item's α* (the smallest coherent flipping dose): win = P(LO shift toward the planted
       candidate > 0) with pair-bootstrap CI, and the shift as a fraction of the reader's OWN natural separation of the
       pair (R1: sep = lo_own(A) + lo_own(B), frame of the source state; median / IQR); per family.
       X3 E8 — per set P(lo_actual > 0) with item-bootstrap and Wilson CIs, raw AND symbol-bias-corrected (R3a:
       lo ≈ b[actual] − b[other] least squares over all puzzle rows, sum-to-zero; choice: position bias); the decision
       rule is the X3 one (ERROR and DISAGREE ≥ 0.75 with CI excluding 0.5), reported on raw and corrected.
  SAE  FVE table (both encode variants, both state sets, shuffled-decoder null) from sae_fve.json.
Outputs results/g_agreement/y3[/dev]/{summary.json, e14.csv, e15.csv, fig_main.png}; the gated readers are added to
results/g_agreement/x/blindness_map.csv (+ x/fig_main.png) through x_blindness_map.py --y3-summary (REPORTED = X1 E1 win /
X3 E8 raw rate, FOLLOWS = X2 win at α*, the same statistics as the Phase X columns). ``--no-map`` skips that step; an
unfrozen run never rewrites the map.

    .venv/bin/python projects/g_agreement/y3_readers/analyze.py [--allow-unfrozen] [--no-map]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement import x_blindness_map as XB  # noqa: E402
from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.x1_bank import analyze as X1A  # noqa: E402
from projects.g_agreement.x3_floor import analyze as X3A  # noqa: E402
from projects.g_agreement.x_friday_r2r4 import fit_pair_bias  # noqa: E402

MODULE = "y3"
NEW_READERS = tuple(C.Y3_READER_NAMES)
ORIG_READERS = ("jlens", "olens", "nla")
LABELS = {"jlens": "J-lens", "olens": "Oracle", "nla": "NLA", "skip_a": "skip-lens A", "skip_d": "skip-lens D", "sae": "SAE probe", "rlens": "R-lens"}
COLORS = {**U.METHOD_COLORS, "skip_a": "#b4891c", "skip_d": "#8a3fb3", "sae": "#c23b6a", "rlens": "#2d9aa6"}
X1_FAMILIES = X1A.FAMILIES
BINDING = ("ownership", "mapping")
SETS = X3A.SETS
SITE = "S2"
FEATURE_CLASSES = ("language", "tense", "ownership", "mapping", "puzzle-error", "self-choice")
CLASS_SOURCE = {"language": ("x1", "language"), "tense": ("x1", "tense"), "ownership": ("x1", "ownership"), "mapping": ("x1", "mapping"),
                "puzzle-error": ("x3", "error"), "self-choice": ("x3", "disagree")}
X_DIR = C.CACHE_DIR / "x"
Y_DIR = C.CACHE_DIR / "y"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(C.DATASET_DIR / "items_x.json"))
    ap.add_argument("--selected", default=str(C.DATASET_DIR / "items_x3_selected.json"))
    ap.add_argument("--x1-lo", default=str(Y_DIR / "y3_x1_lo.jsonl"))
    ap.add_argument("--x2-lo", default=str(Y_DIR / "y3_x2_lo.jsonl"))
    ap.add_argument("--x3-lo", default=str(Y_DIR / "y3_x3_lo.jsonl"))
    ap.add_argument("--behaviour", default=str(X_DIR / "x2_behaviour.jsonl"))
    ap.add_argument("--x1-summary", default=str(C.RESULTS_DIR / "x1" / "summary.json"))
    ap.add_argument("--x3-summary", default=str(C.RESULTS_DIR / "x3" / "summary.json"))
    ap.add_argument("--sae-fve", default=str(C.RESULTS_DIR / "y3" / "sae_fve.json"))
    ap.add_argument("--rlens-format", default=str(C.RESULTS_DIR / "y3" / "rlens_format.json"))
    ap.add_argument("--frozen-config", default=str(C.MANIFEST_DIR / "frozen_config_x.json"))
    ap.add_argument("--readers", default=",".join(NEW_READERS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--map-results", default=str(C.RESULTS_DIR), help="results dir whose x/blindness_map.csv receives the gated readers")
    ap.add_argument("--no-map", action="store_true")
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ E14
def e14_reader(reader: str, rows: List[dict], pairs: Dict[str, List[dict]], nb: int, sd: int) -> dict:
    e1_rows = [r for r in rows if r.get("reader") == reader and r.get("condition", "natural") == "natural" and "item_id" in r]
    mean_rows = [r for r in rows if r.get("reader") == reader and r.get("condition") == "mean_state"]
    e1 = {fam: X1A.e1_reader_family(e1_rows, pairs[fam], nb, sd) for fam in X1_FAMILIES if pairs.get(fam)}
    e3 = X1A.e3_reader(mean_rows)
    e3_na = bool(mean_rows) and all(r.get("mean_lo") is None for r in mean_rows) and any("not applicable" in str(r.get("note", "")) for r in mean_rows)
    sep_ok = all(e1.get(f, {}).get("separates") for f in BINDING)
    e3_ok = all((e3.get(f) or {}).get("within_band") for f in BINDING)
    has_rows = bool(e1_rows)
    if not has_rows:
        status = "no rows"
    elif e3_na:
        status = "PASS (E1 only; E3 n/a)" if sep_ok else "FAIL (E1)"
    else:
        status = "PASS" if (sep_ok and e3_ok) else ("FAIL (E1)" if not sep_ok else "FAIL (E3)")
    return {"n_rows": len(e1_rows), "n_mean_rows": len(mean_rows), "E1": e1, "E3": e3, "e3_not_applicable": e3_na,
            "separates_binding": sep_ok, "e3_within_band_binding": e3_ok, "gate_pass": status.startswith("PASS"), "gate_status": status,
            "gate_rule": f"E1 win >= {C.Y3_GATE_WIN} on ownership AND mapping with the pair-bootstrap CI excluding 0.5, and E3 |mean LO| <= {C.Y3_E3_BAND} nat on both"}


# ------------------------------------------------------------------ E15: X2 follow at alpha*
def alpha_star_by_item(beh: List[dict], site: str = SITE) -> Dict[Tuple[str, str], Optional[float]]:
    pl: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    items = set()
    for r in beh:
        it = (r["pair_id"], r["source"])
        items.add(it)
        if r["site"] == site and r["condition"] == "planted":
            pl[it].append(r)
    out = {}
    for it in sorted(items):
        fl = [float(r["alpha"]) for r in pl.get(it, []) if r.get("flipped_to_other") and r.get("coherent", True)]
        out[it] = min(fl) if fl else None
    return out


def e15_x2_reader(reader: str, lo_rows: List[dict], beh: List[dict], nb: int, sd: int, site: str = SITE) -> Dict[str, dict]:
    """Per family at ``site``: win at α* (shift toward the planted candidate > 0), fraction of own separation."""
    L = {r["entry_key"]: (None if r.get("unscorable") else r.get("lo_toward_other")) for r in lo_rows if r.get("reader") == reader}
    nat = {(r["pair_id"], r["source"]): r for r in beh if r["condition"] == "natural"}
    fam_of = {(r["pair_id"], r["source"]): r["family"] for r in beh}
    astar = alpha_star_by_item(beh, site)
    ent = {(r["pair_id"], r["source"], float(r["alpha"])): r for r in beh if r["site"] == site and r["condition"] == "planted"}
    per_fam: Dict[str, dict] = {}
    fams = sorted(set(fam_of.values()))
    for fam in fams:
        wins, fracs, rows_out = [], [], []
        n_items = n_astar = n_scored = 0
        for it, a in astar.items():
            if fam_of[it] != fam:
                continue
            n_items += 1
            if a is None:
                continue
            n_astar += 1
            e = ent.get((it[0], it[1], a))
            other = (it[0], "B" if it[1] == "A" else "A")
            if e is None or it not in nat or L.get(nat[it]["key"]) is None or L.get(e["key"]) is None:
                continue
            l0 = L[nat[it]["key"]]
            shift = L[e["key"]] - l0
            sep = None
            if other in nat and L.get(nat[other]["key"]) is not None:
                sep = (-L[nat[other]["key"]]) - l0  # = lo_own(A) + lo_own(B)
            frac = (shift / sep) if (sep is not None and sep != 0) else None
            n_scored += 1
            wins.append((it[0], shift > 0))
            if frac is not None:
                fracs.append(frac)
            rows_out.append({"pair_id": it[0], "source": it[1], "alpha_star": a, "shift": shift, "sep": sep, "fraction": frac, "win": shift > 0,
                             "model_flipped": bool(e.get("flipped_to_other"))})
        rate = U.pair_rate(wins, nb, sd) if wins else U.Rate(0, 0, float("nan"), float("nan"), float("nan"), 0)
        fr = np.array(fracs, dtype=float)
        per_fam[fam] = {"site": site, "n_items": n_items, "n_with_alpha_star": n_astar, "n_scored": n_scored, "win": rate.as_dict(),
                        "fraction_median": float(np.median(fr)) if fr.size else None, "fraction_q25": float(np.quantile(fr, 0.25)) if fr.size else None,
                        "fraction_q75": float(np.quantile(fr, 0.75)) if fr.size else None, "n_fraction": int(fr.size),
                        "follows": bool(rate.n and rate.p >= C.Y3_GATE_WIN and rate.lo > 0.5), "per_item": rows_out}
    return per_fam


# ------------------------------------------------------------------ E15: X3 E8 raw + corrected
def e15_x3_reader(reader: str, items: Dict[str, dict], lo_rows: List[dict], nb: int, sd: int) -> dict:
    by = {}
    for r in lo_rows:
        if r.get("reader") == reader and r.get("item_id") in items:
            if r["item_id"] in by:
                raise U.AnalysisError(f"duplicate LO row {reader}|{r['item_id']}")
            by[r["item_id"]] = r
    out: dict = {"per_set": {}, "bias": {}}
    corrected: Dict[str, float] = {}
    for fam in ("puzzle", "choice"):
        rows = [{"item_id": i, "set": items[i]["set"], "actual": items[i]["primary"]["candidates"][0], "other": items[i]["primary"]["candidates"][1],
                 "lo": float(by[i]["lo_actual"])} for i in sorted(items) if items[i]["family"] == fam and i in by and by[i].get("lo_actual") is not None]
        if fam == "puzzle":
            if len(rows) >= 16:
                vocab = sorted({r["actual"] for r in rows} | {r["other"] for r in rows})
                bias, corr, r2 = fit_pair_bias([r["actual"] for r in rows], [r["other"] for r in rows], [r["lo"] for r in rows], vocab)
                corrected.update({r["item_id"]: float(c) for r, c in zip(rows, corr)})
                out["bias"][fam] = {"model": "additive symbol bias b[actual] - b[other], LS over all puzzle rows, sum-to-zero (R3a)", "bias": bias,
                                    "bias_range_nats": float(max(bias.values()) - min(bias.values())), "r2": r2, "n_rows": len(rows)}
            else:
                out["bias"][fam] = {"status": f"skipped ({len(rows)} scorable rows < 16)"}
        else:
            if len(rows) >= 8:
                sign = np.array([1.0 if (items[r["item_id"]].get("source") or {}).get("first_listed") == r["actual"] else -1.0 for r in rows])
                lo = np.array([r["lo"] for r in rows])
                s_hat = float((lo * sign).mean())
                corrected.update({r["item_id"]: float(x) for r, x in zip(rows, lo - s_hat * sign)})
                out["bias"][fam] = {"model": "position bias (first-listed option), one parameter (R3a choice)", "position_bias_nats": s_hat, "n_rows": len(rows)}
            else:
                out["bias"][fam] = {"status": f"skipped ({len(rows)} scorable rows < 8)"}
    for s in SETS:
        ids = sorted(i for i, it in items.items() if it["set"] == s)
        scored = [by[i] for i in ids if i in by and by[i].get("lo_actual") is not None]
        raw = [float(r["lo_actual"]) > 0 for r in scored]
        cor = [corrected[r["item_id"]] > 0 for r in scored if r["item_id"] in corrected]
        rec = {"n_items": len(ids), "n_scored": len(raw), "n_unscorable": sum(1 for i in ids if i in by and by[i].get("lo_actual") is None),
               "n_missing": sum(1 for i in ids if i not in by), "underpowered": len(ids) < X3A.MIN_SET}
        for name, flags in (("raw", raw), ("corrected", cor)):
            p, blo, bhi = X3A.item_bootstrap_rate(flags, nb, sd)
            _, wlo, whi = X3A.wilson(sum(flags), len(flags))
            rec[name] = {"k": int(sum(flags)), "n": len(flags), "p": p, "boot_lo": blo, "boot_hi": bhi, "wilson_lo": wlo, "wilson_hi": whi,
                         "passes_rule": bool(len(flags) and p >= X3A.E8_MIN_RATE and not np.isnan(blo) and blo > 0.5)}
        out["per_set"][s] = rec
    for name in ("raw", "corrected"):
        ok = all(out["per_set"][s][name]["passes_rule"] for s in X3A.DECISION_SETS)
        nodata = any(out["per_set"][s][name]["n"] == 0 for s in X3A.DECISION_SETS)
        under = any(out["per_set"][s]["underpowered"] for s in X3A.DECISION_SETS)
        out[f"verdict_{name}"] = "no_data" if nodata else ("descriptive_only (K6)" if under else ("reads_the_model" if ok else "no_evidence"))
    return out


# ------------------------------------------------------------------ run
def run(args: argparse.Namespace) -> dict:
    frozen, _ = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if frozen else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    nb, sd = args.n_boot, args.seed
    readers = [r.strip() for r in args.readers.split(",") if r.strip()]
    _meta, items = U.load_items(args.items)
    pairs = X1A.load_pairs(items, "test")
    x1_rows = U.load_jsonl(args.x1_lo) if Path(args.x1_lo).exists() else []
    x2_rows = U.load_jsonl(args.x2_lo) if Path(args.x2_lo).exists() else []
    x3_rows = U.load_jsonl(args.x3_lo) if Path(args.x3_lo).exists() else []
    beh = U.load_jsonl(args.behaviour) if Path(args.behaviour).exists() else []
    sel_meta, sel_items = X3A.load_selected(args.selected) if Path(args.selected).exists() else ({}, {})
    x1s = U.load_json(args.x1_summary) if Path(args.x1_summary).exists() else {}
    x3s = U.load_json(args.x3_summary) if Path(args.x3_summary).exists() else {}
    sae_fve = U.load_json(args.sae_fve) if Path(args.sae_fve).exists() else None
    rlens_fmt = U.load_json(args.rlens_format) if Path(args.rlens_format).exists() else None
    U.log(f"[y3] frozen={frozen} readers={readers} rows x1={len(x1_rows)} x2={len(x2_rows)} x3={len(x3_rows)} behaviour={len(beh)} "
          f"x3 items={len(sel_items)} out={out}")
    summary: dict = {"module": MODULE, "frozen": frozen, "n_boot": nb, "seed": sd, "readers": readers, "site": SITE,
                     "thresholds": {"gate_win": C.Y3_GATE_WIN, "e3_band": C.Y3_E3_BAND, "e8_min_rate": X3A.E8_MIN_RATE, "sae_fve_min": C.SAE_FVE_MIN},
                     "orientation": "X1: lo = lp(own) - lp(other), win = lo_A + lo_B > 0; X2: shift of lo_toward_other at alpha*; X3: lo_actual = lp(actual) - lp(other)",
                     "E14": {}, "E15": {}, "sae": None, "rlens": None, "map_columns": {}}
    e14_csv: List[dict] = []
    e15_csv: List[dict] = []
    present = {rd for rd in readers if any(r.get("reader") == rd for r in x1_rows + x2_rows + x3_rows)}
    for rd in readers:
        e = e14_reader(rd, x1_rows, pairs, nb, sd)
        if rd == "rlens" and rlens_fmt and not rlens_fmt.get("usable"):
            e["gate_status"] = f"skipped: {rlens_fmt.get('skip_reason')}"
            e["gate_pass"] = False
        summary["E14"][rd] = e
        for fam, v in e["E1"].items():
            e3 = (e["E3"].get(fam) or {})
            e14_csv.append({"reader": rd, "family": fam, **{k: v[k] for k in v if k != "per_pair"}, "e3_mean_lo": e3.get("mean_lo"),
                            "e3_within_band": e3.get("within_band"), "gate_status": e["gate_status"], "gate_pass": e["gate_pass"]})
            if v["n"]:
                U.log(f"[y3] E14 {rd:7} {fam:9}: win {U.fmt_count(v['k'], v['n'])} boot[{100 * v['lo']:.0f}, {100 * v['hi']:.0f}] separates={v['separates']} "
                      f"E3 {e3.get('mean_lo')} within={e3.get('within_band')}")
        U.log(f"[y3] E14 {rd:7} -> {e['gate_status']}")
        if rd not in present:
            continue
        x2f = e15_x2_reader(rd, x2_rows, beh, nb, sd) if beh and x2_rows else {}
        x3e = e15_x3_reader(rd, sel_items, x3_rows, nb, sd) if sel_items and x3_rows else {}
        summary["E15"][rd] = {"gate_pass": e["gate_pass"], "x2": {f: {k: v for k, v in d.items() if k != "per_item"} for f, d in x2f.items()},
                              "x2_per_item": {f: d["per_item"] for f, d in x2f.items()}, "x3": x3e}
        for fam, d in x2f.items():
            w = d["win"]
            e15_csv.append({"kind": "x2_follow", "reader": rd, "family_or_set": fam, "site": SITE, "n_items": d["n_items"], "n_with_alpha_star": d["n_with_alpha_star"],
                            "n_scored": d["n_scored"], "k": w["k"], "n": w["n"], "p": w["p"], "lo": w["lo"], "hi": w["hi"], "fraction_median": d["fraction_median"],
                            "fraction_q25": d["fraction_q25"], "fraction_q75": d["fraction_q75"], "statistic": "raw", "follows_or_passes": d["follows"], "gate_pass": e["gate_pass"]})
            U.log(f"[y3] E15 X2 {rd:7} {fam:9} @{SITE}: win at alpha* {U.fmt_count(w['k'], w['n'])} [{100 * w['lo']:.0f}, {100 * w['hi']:.0f}] "
                  f"median fraction {d['fraction_median']}")
        for s, rec in (x3e.get("per_set") or {}).items():
            for name in ("raw", "corrected"):
                q = rec[name]
                e15_csv.append({"kind": "x3_e8", "reader": rd, "family_or_set": s, "site": "", "n_items": rec["n_items"], "n_with_alpha_star": "", "n_scored": rec["n_scored"],
                                "k": q["k"], "n": q["n"], "p": q["p"], "lo": q["boot_lo"], "hi": q["boot_hi"], "fraction_median": "", "fraction_q25": "", "fraction_q75": "",
                                "statistic": name, "follows_or_passes": q["passes_rule"], "gate_pass": e["gate_pass"]})
            U.log(f"[y3] E15 X3 {rd:7} {s:14}: raw {U.fmt_count(rec['raw']['k'], rec['raw']['n'])} -> corrected {U.fmt_count(rec['corrected']['k'], rec['corrected']['n'])}")
        if x3e:
            U.log(f"[y3] E15 X3 {rd:7} verdict raw={x3e['verdict_raw']} corrected={x3e['verdict_corrected']}; bias={ {f: b.get('bias_range_nats', b.get('position_bias_nats', b.get('status'))) for f, b in x3e['bias'].items()} }")
        # blindness-map columns for gated readers (same statistics as the Phase X columns: X1 E1 win, X3 E8 raw, X2 win at alpha*)
        if e["gate_pass"]:
            rep = {fam: {"p": e["E1"][fam]["p"], "n": e["E1"][fam]["n"]} for fam in e["E1"] if e["E1"][fam]["n"]}
            for cls, (src, key) in CLASS_SOURCE.items():
                if src == "x3" and key in (x3e.get("per_set") or {}):
                    q = x3e["per_set"][key]["raw"]
                    if q["n"]:
                        rep[cls] = {"p": q["p"], "n": q["n"]}
            fol = {fam: {"p": d["win"]["p"], "n": d["win"]["n"]} for fam, d in x2f.items() if d["win"]["n"]}
            summary["map_columns"][rd] = {"label": LABELS.get(rd, rd), "reported": rep, "follows": fol}
    if sae_fve:
        summary["sae"] = {k: sae_fve.get(k) for k in ("gate_fve", "gate_passes", "gate_variant", "n_x1_states", "n_x3_states", "probe_rows_written", "forced", "by_variant", "sae")}
        for variant, r in (sae_fve.get("by_variant") or {}).items():
            for which, d in r.items():
                U.log(f"[y3] SAE FVE [{variant}] {which}: n={d['n']} fve={d['fve']:.3f} null={d['fve_null']:.3f}")
        U.log(f"[y3] SAE gate: fve={sae_fve.get('gate_fve')} passes={sae_fve.get('gate_passes')}")
    summary["rlens"] = rlens_fmt
    U.write_csv(out / "e14.csv", e14_csv)
    U.write_csv(out / "e15.csv", e15_csv)
    U.write_json(out / "summary.json", summary)
    if not args.no_fig:
        make_figure(out / "fig_main.png", summary, x1s, x3s, readers, frozen)
    if not args.no_map:
        if not frozen:
            U.log("[y3] unfrozen run: blindness map not rewritten")
        elif not summary["map_columns"]:
            U.log("[y3] no reader passed the gate: blindness map not rewritten")
        else:
            XB.main(["--results", args.map_results, "--y3-summary", str(out / "summary.json")])
            U.log(f"[y3] blindness map updated with {sorted(summary['map_columns'])}")
    U.log(f"[y3] wrote {out}")
    return summary


# ------------------------------------------------------------------ figure
def _orig_rate(x1s: dict, x3s: dict, reader: str, cls: str) -> Optional[U.Rate]:
    src, key = CLASS_SOURCE[cls]
    if src == "x1":
        e = ((x1s.get("E1") or {}).get(reader) or {}).get(key)
        if not e or not e.get("n"):
            return None
        return U.Rate(e["k"], e["n"], e["p"], e["lo"], e["hi"], e["n"])
    e = ((x3s.get("E8") or {}).get(reader) or {}).get(key)
    if not e or not e.get("n_scored"):
        return None
    return U.Rate(e["k_favours_actual"], e["n_scored"], e["p"], e["boot_lo"], e["boot_hi"], e["n_scored"], ci="item-bootstrap")


def _new_rate(summary: dict, reader: str, cls: str) -> Optional[U.Rate]:
    src, key = CLASS_SOURCE[cls]
    if src == "x1":
        e = ((summary["E14"].get(reader) or {}).get("E1") or {}).get(key)
        if not e or not e.get("n"):
            return None
        return U.Rate(e["k"], e["n"], e["p"], e["lo"], e["hi"], e["n"])
    q = ((((summary["E15"].get(reader) or {}).get("x3") or {}).get("per_set") or {}).get(key) or {}).get("raw")
    if not q or not q.get("n"):
        return None
    return U.Rate(q["k"], q["n"], q["p"], q["boot_lo"], q["boot_hi"], q["n"], ci="item-bootstrap")


def make_figure(path: Path, summary: dict, x1s: dict, x3s: dict, readers: Sequence[str], frozen: bool) -> None:
    """One panel per feature class: REPORTED rate per reader — the three Phase X readers (from x1/x3 summaries) then the Y3
    readers (hatched if they fail the E14 gate); CI bars; lines at 0.5 and 0.75."""
    plt = U.mpl()
    cols = list(ORIG_READERS) + [r for r in readers]
    fig, axes = plt.subplots(1, len(FEATURE_CLASSES), figsize=(2.9 * len(FEATURE_CLASSES), 4.4), sharey=True)
    for ax, cls in zip(np.atleast_1d(axes), FEATURE_CLASSES):
        for j, rd in enumerate(cols):
            rate = _orig_rate(x1s, x3s, rd, cls) if rd in ORIG_READERS else _new_rate(summary, rd, cls)
            if rate is None:
                ax.text(j, 0.02, "no\nrows", ha="center", va="bottom", fontsize=6.5, color=U.INK2)
                continue
            gated = rd in ORIG_READERS or (summary["E14"].get(rd) or {}).get("gate_pass")
            U.bar_ci(ax, j, rate, COLORS.get(rd, "#888"), width=0.62, hollow=not gated)
        for y, ls in ((0.5, ":"), (C.Y3_GATE_WIN, "--")):
            ax.axhline(y, color=U.INK2, lw=0.7, ls=ls, zorder=1)
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels([LABELS.get(r, r) for r in cols], fontsize=6.5, rotation=45, ha="right")
        U.style_ax(ax, "REPORTED: paired win (X1) / P(favours actual) (X3), %" if cls == FEATURE_CLASSES[0] else None, (0, 1.15))
        ax.set_title(cls, fontsize=9.5)
    gate_txt = "; ".join(f"{LABELS.get(r, r)}: {(summary['E14'].get(r) or {}).get('gate_status', 'n/a')}" for r in readers)
    fig.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + "Y3 — new reader families beside the Phase X readers (hollow = failed the E14 entry gate; "
                 f"bars = 95% pair/item bootstrap CI; lines 0.5 / 0.75)\n{gate_txt}", y=1.04, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
