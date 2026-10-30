"""Z4 — which prompt positions carry the planted swap at L38? (BRIEF_Z §Z4)

CPU only. Inputs:
  cache/g_agreement/z/z4_behaviour.jsonl   one row per NEW Z4 entry {key = pair|source|Z4|condition|alpha|position; condition single|rand_single|
                                           all_except|pair2|restore; position (int; "i-j" for pair2), role, flipped_to_other, kept_original,
                                           coherent, lo_model}
  cache/g_agreement/z/z4_lo.jsonl          one row per (reader, entry) {key = reader|entry key, entry_key, reader, lo_toward_other, unscorable}
  cache/g_agreement/x/x2_behaviour.jsonl   natural states (site nat) and the S2 planted ladder (the ALL-POSITION reference at α 1); x2_lo.jsonl the
                                           readers' natural LO (separation sep_r of every pair).
  cache/g_agreement/y/y2_behaviour.jsonl   name_only / name_removed at α 0.75 / 1 (REUSED, never re-decoded); y2_lo.jsonl their reader LO.
Orientation: every quantity is "toward the planted (other) candidate"; Δ_model = lo_model(entry) − lo_model(natural, same state);
Δs_r = lo_r(entry) − lo_r(natural); f_r = Δs_r / sep_r with sep_r = (−lo_r(nat other)) − lo_r(nat this) (Z1 definition; sep_r = 0 excluded).
Flip = flipped_to_other ∧ coherent.

Per position (per family, and pooled over families by absolute index) and dose: flip rate (Wilson + pair bootstrap), mean Δ_model (pair bootstrap).
CLASSIFICATION (BRIEF_Z deviation 2026-10-09 (3), replacing the original rule; rates at α 1 as fractions of the all-position rate
R_all = X2 S2 planted α 1 of the same family):
  SINGLE CAUSAL   some single position ≥ 0.8·R_all
  REDUNDANT       no single position does, and at least one position PAIR (pair2 arm, both positions interpolated) ≥ 0.8·R_all
  JOINT           neither any single position nor any position pair reaches 0.8·R_all
  A position (pair) enters the max only with n ≥ MIN_N entries at α 1 in the family; the unguarded maxima are reported too.
  The all-except-one arm is descriptive; the ORIGINAL all-except rule (no single ≥ 0.5·R_all and some all_except:i ≥ 0.8·R_all → redundant;
  some all_except:i < 0.5·R_all → joint) is reported as a secondary label.
pair2 table: per family × position pair × dose: flip (Wilson), mean Δ_model (pair bootstrap), n items (10 by design).
Determinism check (deviation (1)): every restore row vs its all_except twin (same pair, source, position, α 1 — the same block-38 state):
parsed-answer agreement (Wilson) and |Δ lo_model|. Random control: rand_single flip rate. Z1-style rerun on the single-position entries: per
reader AUROC of f_r for flip (pair bootstrap), the dose-only reference, Δ_model as the ceiling; Spearman of per-position mean f_r vs flip rate.
Outputs results/g_agreement/z4/{z4.md, per_position.csv, pair2.csv, z4_summary.json, fig_main.png}. Nothing is written to writeup.md
(deviation (5)).
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402

MODULE = "z4"
READERS = ("olens", "nla", "jlens")
READER_LABELS = {"olens": "Oracle lens", "nla": "NLA", "jlens": "J-lens", "model": "model Δ_model", "dose": "dose only (α)"}
NAT, S2, Z4 = "nat", "S2", "Z4"
MODEL = "model"
ARMS = ("single", "all_except", "pair2", "restore", "rand_single", "name_only", "name_removed")
INT_POSITION_ARMS = ("single", "all_except", "restore", "rand_single")
REUSED_CONDS = ("name_only", "name_removed")
REUSE_ALPHAS = (0.75, 1.0)
SINGLE_FRAC, HALF_FRAC, HIGH_FRAC = 0.8, 0.5, 0.8
PAIR_FRAC = 0.8
EPS = 1e-12  # rates are k/n fractions: "≥ 0.8·R_all" is evaluated exactly at the boundary, not at the float product's rounding
MIN_N = 8
POOLED = "pooled"
CACHE = ROOT / "cache" / "g_agreement"
Item = Tuple[str, str]
ROLE_MARK = {"diff": "N", "question_first": "Q", "last": "L", "uniform": "", "unsampled": ""}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--behaviour", default=str(CACHE / "z" / "z4_behaviour.jsonl"))
    ap.add_argument("--lo", default=str(CACHE / "z" / "z4_lo.jsonl"))
    ap.add_argument("--x2-behaviour", default=str(CACHE / "x" / "x2_behaviour.jsonl"))
    ap.add_argument("--x2-lo", default=str(CACHE / "x" / "x2_lo.jsonl"))
    ap.add_argument("--y2-behaviour", default=str(CACHE / "y" / "y2_behaviour.jsonl"))
    ap.add_argument("--y2-lo", default=str(CACHE / "y" / "y2_lo.jsonl"))
    ap.add_argument("--frozen-config", default=str(U.G_DIR / "manifest" / "frozen_config_z.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--min-n", type=int, default=MIN_N)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ small stats
def wilson_dict(k: int, n: int) -> dict:
    p, lo, hi = U.wilson(k, n)
    return {"k": k, "n": n, "p": p, "lo": lo, "hi": hi, "ci": "wilson"}


def mean_boot(vals: List[Tuple[str, float]], nb: int, sd: int) -> dict:
    """Mean of (pair_id, value) observations with a pair bootstrap CI."""
    byp: Dict[str, List[float]] = defaultdict(list)
    for p, v in vals:
        if v is not None and not np.isnan(v):
            byp[p].append(float(v))
    pids = sorted(byp)
    if not pids:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0, "n_pairs": 0}

    def stat(ps):
        v = [x for p in ps for x in byp[p]]
        return float(np.mean(v)) if v else float("nan")

    m, lo, hi = U.pair_bootstrap_stat(pids, stat, nb, sd)
    return {"mean": m, "lo": lo, "hi": hi, "n": sum(len(v) for v in byp.values()), "n_pairs": len(pids)}


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann–Whitney AUROC (ties averaged); nan unless both classes are present."""
    from scipy.stats import rankdata

    y = np.asarray(labels, dtype=bool)
    s = np.asarray(scores, dtype=float)
    ok = ~np.isnan(s)
    y, s = y[ok], s[ok]
    npos, nneg = int(y.sum()), int((~y).sum())
    if npos == 0 or nneg == 0:
        return float("nan")
    r = rankdata(s)
    return float((r[y].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def auroc_boot(obs: List[Tuple[str, float, bool]], nb: int, sd: int) -> dict:
    """obs = (pair_id, score, flip); AUROC with a pair bootstrap CI."""
    byp: Dict[str, List[Tuple[float, bool]]] = defaultdict(list)
    for p, s, f in obs:
        if s is not None and not np.isnan(s):
            byp[p].append((float(s), bool(f)))
    pids = sorted(byp)
    if not pids:
        return {"auroc": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0, "n_pairs": 0, "n_flip": 0}

    def stat(ps):
        pts = [x for p in ps for x in byp[p]]
        return auroc(np.array([s for s, _ in pts]), np.array([f for _, f in pts]))

    a, lo, hi = U.pair_bootstrap_stat(pids, stat, nb, sd)
    allp = [x for v in byp.values() for x in v]
    return {"auroc": a, "lo": lo, "hi": hi, "n": len(allp), "n_pairs": len(pids), "n_flip": sum(f for _, f in allp)}


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    from scipy.stats import spearmanr

    if len(x) < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return float("nan")
    return float(spearmanr(x, y).correlation)


# ------------------------------------------------------------------ world
def _lo_val(reader: str, key: str, lo: Dict[str, Dict[str, Optional[float]]]) -> Optional[float]:
    return lo.get(reader, {}).get(key)


def load_world(a: argparse.Namespace) -> dict:
    z4 = U.load_jsonl(a.behaviour) if Path(a.behaviour).exists() else []
    if not z4:
        raise U.AnalysisError(f"no Z4 behaviour rows in {a.behaviour}")
    x2 = U.load_jsonl(a.x2_behaviour) if Path(a.x2_behaviour).exists() else []
    if not x2:
        raise U.AnalysisError(f"no X2 behaviour rows in {a.x2_behaviour} (natural states and the all-position reference live there)")
    y2 = U.load_jsonl(a.y2_behaviour) if Path(a.y2_behaviour).exists() else []
    pairs = {r["pair_id"] for r in z4}
    nat = {(r["pair_id"], r["source"]): r for r in x2 if r["condition"] == "natural" and r["pair_id"] in pairs}
    ref = [r for r in x2 if r["pair_id"] in pairs and r["site"] == S2 and r["condition"] == "planted" and float(r["alpha"]) == 1.0]
    reused = [dict(r, reused=True, position=None, role=None) for r in y2 if r["pair_id"] in pairs and r["condition"] in REUSED_CONDS and float(r["alpha"]) in REUSE_ALPHAS]
    rows = [dict(r, reused=False) for r in z4] + reused
    keys = [r["key"] for r in rows]
    if len(set(keys)) != len(keys):
        raise U.AnalysisError("duplicate entry keys across the Z4 and reused Y2 rows")
    lo: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for p in (a.lo, a.x2_lo, a.y2_lo):
        if Path(p).exists():
            for r in U.load_jsonl(p):
                ek = r.get("entry_key") or r["key"].split("|", 1)[1]
                lo[r["reader"]][ek] = None if r.get("unscorable") or r.get("lo_toward_other") is None else float(r["lo_toward_other"])
    items = sorted({(r["pair_id"], r["source"]) for r in rows})
    fam = {(r["pair_id"], r["source"]): r["family"] for r in rows}
    for r in ref:
        fam.setdefault((r["pair_id"], r["source"]), r["family"])
    readers = [rd for rd in READERS if rd in lo]
    # natural baselines per item: model lo and reader lo + separation
    nat_model = {it: (None if nat[it].get("lo_model_unscorable") or nat[it].get("lo_model") is None else float(nat[it]["lo_model"])) for it in nat}
    nat_reader = {rd: {it: _lo_val(rd, nat[it]["key"], lo) for it in nat} for rd in readers}
    sep = {}
    for rd in readers:
        sep[rd] = {}
        for it in nat:
            other = (it[0], "B" if it[1] == "A" else "A")
            x, y = nat_reader[rd].get(it), nat_reader[rd].get(other)
            sep[rd][it] = None if x is None or y is None else (-y) - x
    families = sorted({r["family"] for r in rows})
    return {"rows": rows, "ref": ref, "nat": nat, "items": items, "fam": fam, "lo": dict(lo), "readers": readers, "families": families,
            "nat_model": nat_model, "nat_reader": nat_reader, "sep": sep, "n_missing_nat": sum(1 for it in items if it not in nat),
            "alphas_single": sorted({float(r["alpha"]) for r in rows if r["condition"] == "single"})}


def d_model(w: dict, r: dict) -> Optional[float]:
    it = (r["pair_id"], r["source"])
    if r.get("lo_model_unscorable") or r.get("lo_model") is None or w["nat_model"].get(it) is None:
        return None
    return float(r["lo_model"]) - w["nat_model"][it]


def f_reader(w: dict, rd: str, r: dict) -> Optional[float]:
    it = (r["pair_id"], r["source"])
    v, l0, s = _lo_val(rd, r["key"], w["lo"]), w["nat_reader"][rd].get(it), w["sep"][rd].get(it)
    if v is None or l0 is None or s is None or s == 0:
        return None
    return (v - l0) / s


def flip(r: dict) -> bool:
    return bool(r.get("flipped_to_other")) and bool(r.get("coherent", True))


def restored(r: dict) -> bool:
    return bool(r.get("kept_original")) and bool(r.get("coherent", True))


# ------------------------------------------------------------------ cells
def cell_stats(w: dict, rs: List[dict], nb: int, sd: int, readers: List[str]) -> dict:
    fl = [(r["pair_id"], flip(r)) for r in rs]
    k = sum(f for _, f in fl)
    pb = U.pair_rate(fl, nb, sd)
    out = {"n": len(rs), "n_pairs": len({r["pair_id"] for r in rs}), "n_items": len({(r["pair_id"], r["source"]) for r in rs}),
           "flip": wilson_dict(k, len(rs)), "flip_boot": pb.as_dict(), "coherence": wilson_dict(sum(bool(r.get("coherent")) for r in rs), len(rs)),
           "restored": wilson_dict(sum(restored(r) for r in rs), len(rs)),
           "d_model": mean_boot([(r["pair_id"], d_model(w, r)) for r in rs], nb, sd),
           "role": Counter(r.get("role") for r in rs if r.get("role")).most_common(1)[0][0] if any(r.get("role") for r in rs) else None,
           "rel_position": Counter(r.get("rel_position") for r in rs if r.get("rel_position") is not None).most_common(1)[0][0] if any(r.get("rel_position") is not None for r in rs) else None,
           "readers": {rd: mean_boot([(r["pair_id"], f_reader(w, rd, r)) for r in rs], nb, sd) for rd in readers}}
    return out


def csv_row(arm: str, family: str, position, alpha, c: dict, readers: List[str], is_top: bool = False) -> dict:
    row = {"arm": arm, "family": family, "position": position, "alpha": alpha, "role": c.get("role"), "rel_position": c.get("rel_position"), "is_top": is_top,
           "n": c["n"], "n_pairs": c["n_pairs"], "k_flip": c["flip"]["k"], "flip": c["flip"]["p"], "flip_wilson_lo": c["flip"]["lo"], "flip_wilson_hi": c["flip"]["hi"],
           "flip_boot_lo": c["flip_boot"]["lo"], "flip_boot_hi": c["flip_boot"]["hi"], "coherence": c["coherence"]["p"], "restored": c["restored"]["p"],
           "dmodel_mean": c["d_model"]["mean"], "dmodel_lo": c["d_model"]["lo"], "dmodel_hi": c["d_model"]["hi"], "n_dmodel": c["d_model"]["n"]}
    for rd in readers:
        q = c["readers"].get(rd, {})
        row[f"f_{rd}_mean"], row[f"f_{rd}_lo"], row[f"f_{rd}_hi"], row[f"f_{rd}_n"] = q.get("mean"), q.get("lo"), q.get("hi"), q.get("n")
    return row


def _pos_key(p) -> Tuple[int, ...]:
    """Sort key of a position (int) or a pair label "i-j"."""
    return tuple(int(x) for x in str(p).split("-"))


def _extrema(cells: Dict[Any, dict], guard: bool, min_n: int):
    """(max rate, its position, min rate, its position, n ranked); ties → lowest position (pair) index."""
    c = {p: v for p, v in cells.items() if (v["n"] >= min_n or not guard)}
    if not c:
        return None, None, None, None, 0
    mx = min(c, key=lambda p: (-c[p]["flip"]["p"], _pos_key(p)))
    mn = min(c, key=lambda p: (c[p]["flip"]["p"], _pos_key(p)))
    return c[mx]["flip"]["p"], mx, c[mn]["flip"]["p"], mn, len(c)


def classify(r_all: float, singles: Dict[int, dict], pairs: Dict[str, dict], all_except: Dict[int, dict], min_n: int) -> dict:
    """The deviation-2026-10-09 rule on α 1 cells (``singles``: position -> cell, ``pairs``: "i-j" -> cell):
    SINGLE CAUSAL if max single ≥ 0.8·R_all; else REDUNDANT if max pair ≥ 0.8·R_all; else JOINT. UNDETERMINED without
    a reference, without ranked single positions, or (no single reaching the bar) without ranked pairs. The original
    all-except rule (``classify_original``) is attached as the secondary label."""
    ms, ms_pos, _, _, ns = _extrema(singles, True, min_n)
    ms_u, ms_pos_u, _, _, _ = _extrema(singles, False, min_n)
    mp, mp_pos, _, _, npair = _extrema(pairs, True, min_n)
    mp_u, mp_pos_u, _, _, _ = _extrema(pairs, False, min_n)
    orig = classify_original(r_all, singles, all_except, min_n)
    out = {"r_all": r_all, "rule": "deviation 2026-10-09 (3)",
           "thresholds": {"single_frac": SINGLE_FRAC, "pair_frac": PAIR_FRAC, "min_n": min_n},
           "single": {"max": ms, "position": ms_pos, "n_positions_ranked": ns, "max_unguarded": ms_u, "position_unguarded": ms_pos_u},
           "pair2": {"max": mp, "pair": mp_pos, "n_pairs_ranked": npair, "max_unguarded": mp_u, "pair_unguarded": mp_pos_u},
           "all_except": orig["all_except"],
           "secondary_label": orig["verdict"], "secondary_reason": orig["reason"], "secondary_rule": "original pre-registered all-except rule",
           "original": orig}
    if r_all is None or np.isnan(r_all) or ms is None:
        out.update(verdict="UNDETERMINED", reason="no all-position reference or no ranked single positions", flags={})
        return out
    bar = SINGLE_FRAC * r_all
    sc = ms >= bar - EPS
    red = (not sc) and mp is not None and mp >= PAIR_FRAC * r_all - EPS
    flags = {"single_causal": bool(sc), "redundant_pair": bool(red), "pair2_available": mp is not None}
    if sc:
        v, why = "SINGLE CAUSAL", f"position {ms_pos} flips {ms:.2f} ≥ {SINGLE_FRAC}·R_all = {bar:.2f}"
    elif mp is None:
        v, why = "UNDETERMINED", f"best single {ms:.2f} < {SINGLE_FRAC}·R_all = {bar:.2f} and no ranked pair2 cells yet"
    elif red:
        v, why = "REDUNDANT", f"best single {ms:.2f} (pos {ms_pos}) < {bar:.2f}; pair {mp_pos} flips {mp:.2f} ≥ {PAIR_FRAC}·R_all"
    else:
        v, why = "JOINT", f"best single {ms:.2f} (pos {ms_pos}) and best pair {mp:.2f} ({mp_pos}) < {SINGLE_FRAC}·R_all = {bar:.2f}"
    out.update(verdict=v, reason=why, flags=flags)
    return out


def classify_original(r_all: float, singles: Dict[int, dict], all_except: Dict[int, dict], min_n: int) -> dict:
    """The ORIGINAL pre-registered rule on α 1 cells (now the secondary label); ``singles``/``all_except`` map position -> cell."""
    def extrema(cells: Dict[int, dict], guard: bool):
        return _extrema(cells, guard, min_n)

    ms, ms_pos, _, _, ns = extrema(singles, True)
    ms_u, ms_pos_u, _, _, _ = extrema(singles, False)
    mae, mae_pos, nae, nae_pos, nae_n = extrema(all_except, True)
    mae_u, mae_pos_u, nae_u, nae_pos_u, _ = extrema(all_except, False)
    out = {"r_all": r_all, "thresholds": {"single_frac": SINGLE_FRAC, "half_frac": HALF_FRAC, "high_frac": HIGH_FRAC, "min_n": min_n},
           "single": {"max": ms, "position": ms_pos, "n_positions_ranked": ns, "max_unguarded": ms_u, "position_unguarded": ms_pos_u},
           "all_except": {"max": mae, "max_position": mae_pos, "min": nae, "min_position": nae_pos, "n_positions_ranked": nae_n,
                          "max_unguarded": mae_u, "min_unguarded": nae_u, "min_position_unguarded": nae_pos_u}}
    if r_all is None or np.isnan(r_all) or ms is None:
        out.update(verdict="UNDETERMINED", reason="no all-position reference or no ranked single positions", flags={})
        return out
    sc = ms >= SINGLE_FRAC * r_all - EPS
    none_half = ms < HALF_FRAC * r_all - EPS
    red = none_half and mae is not None and mae >= HIGH_FRAC * r_all - EPS
    joint = none_half and nae is not None and nae < HALF_FRAC * r_all - EPS
    flags = {"single_causal": bool(sc), "redundant": bool(red), "joint": bool(joint), "no_single_ge_half": bool(none_half), "all_except_available": mae is not None}
    if sc:
        v, why = "SINGLE CAUSAL POSITION", f"position {ms_pos} flips {ms:.2f} ≥ {SINGLE_FRAC}·{r_all:.2f}"
    elif red and joint:
        v, why = "REDUNDANT+JOINT", f"best single {ms:.2f} < {HALF_FRAC}·{r_all:.2f}; all_except max {mae:.2f} (pos {mae_pos}) ≥ {HIGH_FRAC}·R_all and min {nae:.2f} (pos {nae_pos}) < {HALF_FRAC}·R_all"
    elif red:
        v, why = "REDUNDANT", f"best single {ms:.2f} < {HALF_FRAC}·{r_all:.2f}; some all_except still ≥ {HIGH_FRAC}·R_all (max {mae:.2f} at pos {mae_pos}; min {nae:.2f})"
    elif joint:
        v, why = "JOINT", f"best single {ms:.2f} < {HALF_FRAC}·{r_all:.2f}; removing pos {nae_pos} drops the rate to {nae:.2f} < {HALF_FRAC}·R_all"
    elif mae is None and none_half:
        v, why = "UNDETERMINED", f"best single {ms:.2f} < {HALF_FRAC}·R_all and no all_except rows yet"
    else:
        v, why = "MIXED", f"best single {ms:.2f} (pos {ms_pos}) in [{HALF_FRAC}, {SINGLE_FRAC})·R_all" if not none_half else f"best single {ms:.2f}; all_except in [{HALF_FRAC}, {HIGH_FRAC})·R_all (max {mae:.2f}, min {nae:.2f})"
    out.update(verdict=v, reason=why, flags=flags)
    return out


def determinism_check(rs: List[dict]) -> dict:
    """Each restore row vs its all_except twin (same pair, source, position, α): parsed-answer agreement (Wilson), flip agreement,
    |Δ lo_model| (mean / median / max over twins with both values)."""
    ae = {(r["pair_id"], r["source"], int(r["position"]), float(r["alpha"])): r for r in rs if r["condition"] == "all_except"}
    re_rows = [r for r in rs if r["condition"] == "restore"]
    twins = []
    for r in sorted(re_rows, key=lambda r: (r["pair_id"], r["source"], int(r["position"]))):
        t = ae.get((r["pair_id"], r["source"], int(r["position"]), float(r["alpha"])))
        if t is None:
            continue
        d = None
        if r.get("lo_model") is not None and t.get("lo_model") is not None and not r.get("lo_model_unscorable") and not t.get("lo_model_unscorable"):
            d = abs(float(r["lo_model"]) - float(t["lo_model"]))
        twins.append({"pair_id": r["pair_id"], "family": r.get("family"), "source": r["source"], "position": int(r["position"]), "parsed_restore": r.get("parsed"),
                      "parsed_all_except": t.get("parsed"), "same_answer": r.get("parsed") == t.get("parsed"), "same_flip": flip(r) == flip(t),
                      "lo_model_restore": r.get("lo_model"), "lo_model_all_except": t.get("lo_model"), "abs_d_lo_model": d})
    ds = [x["abs_d_lo_model"] for x in twins if x["abs_d_lo_model"] is not None]
    return {"n_restore": len(re_rows), "n_twins": len(twins), "n_without_twin": len(re_rows) - len(twins),
            "answer_agreement": wilson_dict(sum(x["same_answer"] for x in twins), len(twins)) if twins else None,
            "flip_agreement": wilson_dict(sum(x["same_flip"] for x in twins), len(twins)) if twins else None,
            "abs_d_lo_model": {"n": len(ds), "mean": float(np.mean(ds)) if ds else float("nan"), "median": float(np.median(ds)) if ds else float("nan"),
                               "max": float(np.max(ds)) if ds else float("nan")},
            "twins": twins}


# ------------------------------------------------------------------ main analysis
def run(args: argparse.Namespace) -> dict:
    frozen, _ = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if frozen else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    nb, sd, min_n = args.n_boot, args.seed, args.min_n
    w = load_world(args)
    rows, readers, fams = w["rows"], w["readers"], w["families"]
    groups = fams + [POOLED]
    rows_of = {f: [r for r in rows if f == POOLED or r["family"] == f] for f in groups}
    ref_of = {f: [r for r in w["ref"] if f == POOLED or r["family"] == f] for f in groups}
    U.log(f"[z4] frozen={frozen} {len(rows)} entries ({sum(1 for r in rows if r['reused'])} reused Y2) / {len(w['items'])} items / {len({p for p, _ in w['items']})} pairs; "
          f"families {fams}; readers {readers}; {w['n_missing_nat']} items without a natural row; {len(w['ref'])} all-position reference rows; out={out}")
    summary: dict = {"module": MODULE, "frozen": frozen, "n_entries": len(rows), "n_new_entries": sum(1 for r in rows if not r["reused"]), "n_items": len(w["items"]),
                     "n_pairs": len({p for p, _ in w["items"]}), "n_boot": nb, "seed": sd, "readers": readers, "families": fams, "alphas_single": w["alphas_single"],
                     "n_items_without_natural": w["n_missing_nat"], "min_n": min_n,
                     "orientation": "positive = toward the planted candidate; Δ_model = lo_model(entry) − lo_model(natural); f_r = (lo_r(entry) − lo_r(natural)) / sep_r",
                     "condition_counts": dict(Counter(r["condition"] for r in rows)), "by_group": {}}
    csv_rows: List[dict] = []
    pair2_rows: List[dict] = []
    fig: dict = {"families": {}}
    top_positions: Dict[str, List[int]] = {}
    for f in groups:
        rs = rows_of[f]
        G: dict = {}
        # all-position reference (X2 S2 α 1)
        refc = cell_stats(w, ref_of[f], nb, sd, readers) if ref_of[f] else None
        G["all_positions_reference"] = refc
        r_all = refc["flip"]["p"] if refc else float("nan")
        if refc:
            csv_rows.append(csv_row("all_x2_S2", f, "all", 1.0, refc, readers))
        # per position × dose for single / all_except / restore / rand_single (int positions) and pair2 ("i-j")
        cells: Dict[str, Dict[Tuple[Any, float], dict]] = {}
        for arm in INT_POSITION_ARMS + ("pair2",):
            cells[arm] = {}
            byc: Dict[Tuple[Any, float], List[dict]] = defaultdict(list)
            for r in rs:
                if r["condition"] == arm:
                    byc[(str(r["position"]) if arm == "pair2" else int(r["position"]), float(r["alpha"]))].append(r)
            for (p, al), sub in sorted(byc.items(), key=lambda kv: (_pos_key(kv[0][0]), kv[0][1])):
                cells[arm][(p, al)] = cell_stats(w, sub, nb, sd, readers)
        tops = sorted({int(r["position"]) for r in rs if r["condition"] == "all_except"})
        top_positions[f] = tops
        for arm in ("single", "all_except", "restore"):
            for (p, al), c in cells[arm].items():
                csv_rows.append(csv_row(arm, f, p, al, c, readers, is_top=p in tops))
        for (p, al), c in cells["pair2"].items():
            csv_rows.append(csv_row("pair2", f, p, al, c, readers, is_top=True))
            i, j = _pos_key(p)
            pair2_rows.append({"family": f, "pair": p, "i": i, "j": j, "alpha": al, "role": c["role"], "n": c["n"], "n_items": c["n_items"],
                               "n_pairs": c["n_pairs"], "k_flip": c["flip"]["k"], "flip": c["flip"]["p"], "flip_wilson_lo": c["flip"]["lo"],
                               "flip_wilson_hi": c["flip"]["hi"], "dmodel_mean": c["d_model"]["mean"], "dmodel_lo": c["d_model"]["lo"],
                               "dmodel_hi": c["d_model"]["hi"], "n_dmodel": c["d_model"]["n"]})
        # rand_single pooled over positions (the control is one rate) + per position
        rand_rows = [r for r in rs if r["condition"] == "rand_single"]
        G["rand_single"] = cell_stats(w, rand_rows, nb, sd, readers) if rand_rows else None
        if rand_rows:
            csv_rows.append(csv_row("rand_single", f, "any", 1.0, G["rand_single"], readers))
        # reused name arms
        G["name_arms"] = {}
        for cond in REUSED_CONDS:
            for al in REUSE_ALPHAS:
                sub = [r for r in rs if r["condition"] == cond and float(r["alpha"]) == al]
                if sub:
                    c = cell_stats(w, sub, nb, sd, readers)
                    G["name_arms"][f"{cond}@{al}"] = c
                    csv_rows.append(csv_row(cond, f, "differing" if cond == "name_only" else "equal", al, c, readers))
        # single summary per dose
        G["single_by_dose"] = {}
        for al in w["alphas_single"]:
            sub = [r for r in rs if r["condition"] == "single" and float(r["alpha"]) == al]
            if sub:
                G["single_by_dose"][str(al)] = cell_stats(w, sub, nb, sd, readers)
        # classification on α 1 cells (deviation 2026-10-09 (3)); the original all-except rule rides along as the secondary label
        s1 = {p: c for (p, al), c in cells["single"].items() if al == 1.0}
        p1 = {p: c for (p, al), c in cells["pair2"].items() if al == 1.0}
        ae = {p: c for (p, al), c in cells["all_except"].items() if al == 1.0}
        G["classification"] = classify(r_all, s1, p1, ae, min_n)
        # pair2 table: per position pair × dose
        G["pair2"] = {}
        for (p, al), c in cells["pair2"].items():
            G["pair2"].setdefault(p, {})[str(al)] = {"flip": c["flip"], "flip_boot": c["flip_boot"], "d_model": c["d_model"], "n": c["n"],
                                                      "n_items": c["n_items"], "n_pairs": c["n_pairs"], "role": c["role"]}
        # determinism check: restore rows vs their all_except twins
        G["determinism"] = determinism_check(rs)
        G["all_except"] = {str(p): {"flip": c["flip"], "flip_boot": c["flip_boot"], "d_model": c["d_model"], "n": c["n"], "role": c["role"]} for p, c in ae.items()}
        G["top_single_positions"] = [{"position": p, "flip": s1[p]["flip"]["p"], "n": s1[p]["n"], "role": s1[p]["role"], "d_model": s1[p]["d_model"]["mean"]}
                                     for p in sorted(s1, key=lambda p: (-s1[p]["flip"]["p"], p))[:10]]
        # Z1-style rerun on the single entries
        singles = [r for r in rs if r["condition"] == "single"]
        Z: dict = {"n_entries": len(singles), "n_flips": sum(flip(r) for r in singles), "auroc": {}, "auroc_alpha1": {}, "position_corr": {}}
        scorers = {rd: (lambda r, rd=rd: f_reader(w, rd, r)) for rd in readers}
        scorers[MODEL] = lambda r: d_model(w, r)
        scorers["dose"] = lambda r: float(r["alpha"])
        for name, fn in scorers.items():
            Z["auroc"][name] = auroc_boot([(r["pair_id"], fn(r), flip(r)) for r in singles], nb, sd)
            Z["auroc_alpha1"][name] = auroc_boot([(r["pair_id"], fn(r), flip(r)) for r in singles if float(r["alpha"]) == 1.0], nb, sd)
            if name == "dose":
                continue
            # per-position mean score vs per-position flip rate (both doses pooled), pair bootstrap of Spearman
            byp: Dict[str, Dict[int, List[Tuple[float, bool]]]] = defaultdict(lambda: defaultdict(list))
            for r in singles:
                v = fn(r)
                if v is not None and not np.isnan(v):
                    byp[r["pair_id"]][int(r["position"])].append((float(v), flip(r)))
            pids = sorted(byp)

            def stat(ps, byp=byp):
                acc: Dict[int, List[Tuple[float, bool]]] = defaultdict(list)
                for p in ps:
                    for pos, v in byp[p].items():
                        acc[pos] += v
                cs = [(np.mean([s for s, _ in v]), np.mean([f for _, f in v])) for pos, v in acc.items() if len(v) >= min_n]
                if len(cs) < 3:
                    return float("nan")
                return spearman(np.array([x for x, _ in cs]), np.array([y for _, y in cs]))

            rho, lo, hi = U.pair_bootstrap_stat(pids, stat, nb, sd) if pids else (float("nan"),) * 3
            Z["position_corr"][name] = {"spearman": rho, "lo": lo, "hi": hi, "n_positions": sum(1 for (p, al), c in cells["single"].items() if al == 1.0 and c["n"] >= min_n),
                                        "ci_excludes_0": (None if np.isnan(lo) else bool(lo > 0 or hi < 0))}
        G["z1_rerun"] = Z
        summary["by_group"][f] = G
        cl = G["classification"]
        U.log(f"[z4] {f:10s}: R_all {r_all:.2f}; best single {cl['single']['max']} @ {cl['single']['position']}; best pair {cl['pair2']['max']} @ {cl['pair2']['pair']}; "
              f"-> {cl['verdict']} ({cl['reason']}); all_except max/min {cl['all_except']['max']}/{cl['all_except']['min']} -> secondary (original rule) {cl['secondary_label']}; "
              f"determinism: answer agreement {G['determinism']['answer_agreement']['k'] if G['determinism']['answer_agreement'] else 0}/{G['determinism']['n_twins']}")
        for name, q in Z["auroc"].items():
            U.log(f"[z4] {f:10s} Z1-rerun {READER_LABELS.get(name, name):14s}: AUROC {q['auroc']:.3f} [{q['lo']:.3f}, {q['hi']:.3f}] n={q['n']} flips={q['n_flip']}"
                  + (f"; per-position Spearman {Z['position_corr'][name]['spearman']:.2f} [{Z['position_corr'][name]['lo']:.2f}, {Z['position_corr'][name]['hi']:.2f}]" if name in Z["position_corr"] else ""))
        if f != POOLED:
            fig["families"][f] = {"cells": cells["single"], "tops": tops, "r_all": r_all, "verdict": G["classification"]["verdict"],
                                  "pair2": p1, "best_single": G["classification"]["single"]["max"]}
    summary["classification"] = {f: summary["by_group"][f]["classification"]["verdict"] for f in groups}
    summary["classification_secondary_original_rule"] = {f: summary["by_group"][f]["classification"]["secondary_label"] for f in groups}
    summary["decision_rule_note"] = ("positions are aligned by ABSOLUTE token index within a family (templates share the chat prefix; name/object tokens "
                                     "may sit at different indices across pairs — see the role column); classification per BRIEF_Z deviation 2026-10-09 (3) "
                                     "(single ≥ 0.8·R_all → SINGLE CAUSAL; else a position pair ≥ 0.8·R_all → REDUNDANT; else JOINT); restore:i and all_except:i "
                                     "are the same block-38 state at α 1 (the restore arm is a decode determinism check only)")
    U.write_csv(out / "per_position.csv", csv_rows)
    if pair2_rows:
        U.write_csv(out / "pair2.csv", pair2_rows)
    U.write_json(out / "z4_summary.json", summary)
    write_md(out / "z4.md", summary, w)
    if not args.no_fig:
        make_fig_main(out / "fig_main.png", fig, readers, w["alphas_single"], summary, frozen)
    U.log(f"[z4] wrote {out}")
    return summary


# ------------------------------------------------------------------ write-up
def _pct(d: Optional[dict]) -> str:
    if not d or d.get("n", 0) == 0 or d.get("p") is None or np.isnan(d["p"]):
        return "—"
    return f"{100 * d['p']:.0f}% [{100 * d['lo']:.0f}, {100 * d['hi']:.0f}] ({d['k']}/{d['n']})"


def _r(x) -> str:
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.2f}"


def _m(d: Optional[dict]) -> str:
    if not d or d.get("n", 0) == 0 or np.isnan(d["mean"]):
        return "—"
    return f"{d['mean']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}]"


def write_md(path: Path, s: dict, w: dict) -> None:
    L: List[str] = [f"# Z4 — matched-layer position dissection at L38 ({'frozen' if s['frozen'] else 'UNFROZEN DEV'})", "",
                    f"{s['n_entries']} entries ({s['n_new_entries']} new decodes, {s['n_entries'] - s['n_new_entries']} Y2 rows reused) on {s['n_items']} states / {s['n_pairs']} pairs; "
                    f"readers {', '.join(s['readers'])}; single doses α ∈ {s['alphas_single']}; pair bootstrap {s['n_boot']} (seed {s['seed']}); min n per ranked position {s['min_n']}.", "",
                    "Question: does the all-position L38 swap (X2 S2: 98% flips at α 1) act through one prompt position, redundantly through many, or jointly?", ""]
    L.append("## Classification (BRIEF_Z deviation 2026-10-09 (3); rates at α 1 as fractions of the all-position rate R_all)")
    L.append("SINGLE CAUSAL if some single position ≥ 0.8·R_all; REDUNDANT if none does and some position pair (pair2 arm) ≥ 0.8·R_all; JOINT if neither. "
             "The original all-except rule is the secondary label (all_except is descriptive).")
    L.append("| group | R_all (X2 S2 α1) | best single α1 (pos) | best pair α1 (pair) | verdict | reason | all_except max (pos) | all_except min (pos) | secondary label (original all-except rule) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for f, G in s["by_group"].items():
        c = G["classification"]
        ref = G["all_positions_reference"]
        L.append("| " + " | ".join([f, _pct(ref["flip"]) if ref else "—", f"{_r(c['single']['max'])} ({c['single']['position']})",
                                    f"{_r(c['pair2']['max'])} ({c['pair2']['pair']})", f"**{c['verdict']}**", c["reason"],
                                    f"{_r(c['all_except']['max'])} ({c['all_except']['max_position']})", f"{_r(c['all_except']['min'])} ({c['all_except']['min_position']})",
                                    c["secondary_label"]]) + " |")
    L.append("")
    L.append("## Determinism check (restore:i vs its all_except:i twin — the same block-38 state at α 1)")
    L.append("| group | restore rows | twins | same parsed answer (Wilson) | same flip | mean / max abs Δ lo_model (nats) |")
    L.append("|---|---|---|---|---|---|")
    for f, G in s["by_group"].items():
        d = G["determinism"]
        L.append(f"| {f} | {d['n_restore']} | {d['n_twins']} | {_pct(d['answer_agreement'])} | {_pct(d['flip_agreement'])} | "
                 f"{_r(d['abs_d_lo_model']['mean'])} / {_r(d['abs_d_lo_model']['max'])} (n={d['abs_d_lo_model']['n']}) |")
    L.append("")
    for f, G in s["by_group"].items():
        L.append(f"## {f}")
        L.append("Single positions at α 1, top 10 by flip rate (N = name/object/symbol token, Q = question start, L = last token):")
        L.append("| position | role | flip (Wilson) | n | mean Δ_model |")
        L.append("|---|---|---|---|---|")
        for t in G["top_single_positions"]:
            dm = "" if t["d_model"] is None or np.isnan(t["d_model"]) else f"{t['d_model']:+.2f}"
            L.append(f"| {t['position']} | {t['role'] or ''} | {100 * t['flip']:.0f}% | {t['n']} | {dm} |")
        L.append("")
        if G["pair2"]:
            alphas2 = sorted({al for v in G["pair2"].values() for al in v}, key=float)
            L.append("Two-position arm (pair2: both positions interpolated, nothing else): flip (Wilson) and mean Δ_model [pair bootstrap] per dose; n items:")
            L.append("| pair | roles | " + " | ".join(f"α {al}: flip | α {al}: Δ_model" for al in alphas2) + " | n items (α 1) |")
            L.append("|---|---|" + "---|---|" * len(alphas2) + "---|")
            for pr in sorted(G["pair2"], key=_pos_key):
                v = G["pair2"][pr]
                role = next((x["role"] for x in v.values() if x.get("role")), "") or ""
                cells_ = " | ".join(f"{_pct(v[al]['flip']) if al in v else '—'} | {_m(v[al]['d_model']) if al in v else '—'}" for al in alphas2)
                L.append(f"| {pr} | {role} | {cells_} | {v.get('1.0', {}).get('n_items', '—')} |")
            L.append("")
        if G["all_except"]:
            L.append("all_except:i (α 1; descriptive):")
            L.append("| position | role | all_except flip | all_except Δ_model |")
            L.append("|---|---|---|---|")
            for p, c in G["all_except"].items():
                L.append(f"| {p} | {c['role'] or ''} | {_pct(c['flip'])} | {_m(c['d_model'])} |")
            L.append("")
        L.append(f"Random-direction single-position control (α 1, ‖Δ(i)‖-matched): flip {_pct(G['rand_single']['flip']) if G['rand_single'] else '—'}; "
                 f"Δ_model {_m(G['rand_single']['d_model']) if G['rand_single'] else '—'}.")
        for k, c in G["name_arms"].items():
            L.append(f"- {k} (Y2, reused): flip {_pct(c['flip'])}, Δ_model {_m(c['d_model'])}")
        for al, c in G["single_by_dose"].items():
            L.append(f"- all single positions pooled at α {al}: flip {_pct(c['flip'])}, Δ_model {_m(c['d_model'])}")
        Z = G["z1_rerun"]
        L.append("")
        L.append(f"Z1-style rerun on the {Z['n_entries']} single-position entries ({Z['n_flips']} flips): AUROC of the reader's f_r for flip, pair-bootstrap 95% CI; "
                 "Spearman of per-position mean f_r vs per-position flip rate (does the reader's shift identify the causal positions?).")
        L.append("| scorer | AUROC (both doses) | AUROC (α 1) | per-position Spearman |")
        L.append("|---|---|---|---|")
        for name, q in Z["auroc"].items():
            q1 = Z["auroc_alpha1"][name]
            pc = Z["position_corr"].get(name)
            L.append(f"| {READER_LABELS.get(name, name)} | {q['auroc']:.3f} [{q['lo']:.3f}, {q['hi']:.3f}] (n={q['n']}) | {q1['auroc']:.3f} [{q1['lo']:.3f}, {q1['hi']:.3f}] | "
                     + ("—" if pc is None else f"{pc['spearman']:.2f} [{pc['lo']:.2f}, {pc['hi']:.2f}] over {pc['n_positions']} positions") + " |")
        L.append("")
    L.append("## Caveats")
    L.append(f"- {s['decision_rule_note']}.")
    L.append("- Thresholds are applied to Wilson point estimates on positions (pairs) with n ≥ min_n entries at α 1; the unguarded extrema are in z4_summary.json.")
    L.append("- Two-position rates rest on 10 (pair, source) items per position pair (Wilson CIs above); the top-5 positions are absolute indices, "
             "so a pair is only drawn among prompts long enough to contain both.")
    L.append("- name_only / name_removed rows are Y2's (same site, same doses), not re-decoded.")
    L.append("")
    L.append("Files: per_position.csv (one row per arm × group × position × dose), pair2.csv, z4_summary.json, fig_main.png. Nothing here is written to writeup.md.")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ figure
def make_fig_main(path: Path, fig: dict, readers: List[str], alphas: List[float], summary: dict, frozen: bool) -> None:
    import matplotlib.colors as mcolors
    from matplotlib.patches import Rectangle

    plt = U.mpl()
    fams = list(fig["families"])
    if not fams:
        return
    nrow_heat = 1 + len(readers)
    has_pair = any(fig["families"][f].get("pair2") for f in fams)
    nrow = nrow_heat + (1 if has_pair else 0)
    width = sum(max(4, len({p for (p, _) in fig["families"][f]["cells"]})) for f in fams) * 0.28 + 2.5
    fig_, axes = plt.subplots(nrow, len(fams), figsize=(max(9, width), 1.9 * nrow_heat + (1.7 if has_pair else 0) + 1.2), squeeze=False,
                              gridspec_kw={"width_ratios": [max(4, len({p for (p, _) in fig["families"][f]["cells"]})) for f in fams],
                                           "height_ratios": [1.0] * nrow_heat + ([0.9] if has_pair else [])})
    seq = mcolors.LinearSegmentedColormap.from_list("seq_blue", U.SEQ_BLUE)
    div = mcolors.LinearSegmentedColormap.from_list("div", ["#eb6834", U.GRID, "#2a78d6"])
    for j, f in enumerate(fams):
        F = fig["families"][f]
        cells = F["cells"]
        pos = sorted({p for (p, _) in cells})
        if not pos:
            for i in range(nrow):
                axes[i][j].axis("off")
            continue
        labels = []
        for p in pos:
            c = next((cells[(p, a)] for a in alphas if (p, a) in cells), None)
            mark = ROLE_MARK.get((c or {}).get("role") or "", "")
            labels.append(f"{p}{mark}" + ("▲" if p in F["tops"] else ""))

        def grid(fn):
            M = np.full((len(alphas), len(pos)), np.nan)
            for ai, a in enumerate(alphas):
                for pi, p in enumerate(pos):
                    if (p, a) in cells:
                        M[ai, pi] = fn(cells[(p, a)])
            return M

        rows_spec = [("model flip rate", lambda c: c["flip"]["p"], seq, 0.0, 1.0)]
        for rd in readers:
            rows_spec.append((f"{READER_LABELS[rd]} mean f_r", lambda c, rd=rd: c["readers"][rd]["mean"], div, -1.0, 1.0))
        for i, (name, fn, cmap, vmin, vmax) in enumerate(rows_spec):
            ax = axes[i][j]
            M = grid(fn)
            im = ax.imshow(np.clip(M, vmin, vmax), cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", interpolation="nearest")
            ax.set_yticks(range(len(alphas))); ax.set_yticklabels([f"α {a}" for a in alphas], fontsize=7.5)
            ax.set_xticks(range(len(pos))); ax.set_xticklabels(labels, fontsize=6.5, rotation=90)
            for ai, a in enumerate(alphas):
                for pi, p in enumerate(pos):
                    v = M[ai, pi]
                    if not np.isnan(v) and i == 0:
                        ax.text(pi, ai, f"{100 * v:.0f}", ha="center", va="center", fontsize=5.5, color=U.INK if v < 0.6 else U.SURFACE)
                    if (p, a) in cells and cells[(p, a)]["n"] < summary.get("min_n", MIN_N):  # sparse cell: provisional
                        ax.add_patch(Rectangle((pi - 0.5, ai - 0.5), 1, 1, fill=False, hatch="////", edgecolor=U.INK2, lw=0, alpha=0.35))
            ax.set_xticks(np.arange(-0.5, len(pos), 1), minor=True); ax.set_yticks(np.arange(-0.5, len(alphas), 1), minor=True)
            ax.grid(which="minor", color=U.SURFACE, lw=1.2); ax.tick_params(which="minor", length=0)
            for sp in ax.spines.values():
                sp.set_visible(False)
            if j == 0:
                ax.set_ylabel(name, fontsize=8)
            if i == 0:
                ax.set_title(f"{f}: R_all {100 * F['r_all']:.0f}% → {F['verdict']}", fontsize=9)
            if i == nrow_heat - 1:
                ax.set_xlabel(f"prompt position (absolute token index; N name/object/symbol token, Q question start, L last; ▲ top-K; hatched = n < {summary.get('min_n', MIN_N)})", fontsize=7.5)
            cb = fig_.colorbar(im, ax=ax, fraction=0.03, pad=0.01)
            cb.ax.tick_params(labelsize=6.5)
            cb.set_label("flip %" if i == 0 else "f_r (fraction of own separation)", fontsize=6.5)
        if has_pair:
            ax = axes[nrow - 1][j]
            P2 = F.get("pair2") or {}
            prs = sorted(P2, key=_pos_key)
            if not prs:
                ax.axis("off")
                continue
            xs = np.arange(len(prs))
            ps = np.array([P2[q]["flip"]["p"] for q in prs])
            lo = np.array([P2[q]["flip"]["lo"] for q in prs])
            hi = np.array([P2[q]["flip"]["hi"] for q in prs])
            ax.bar(xs, ps, width=0.7, color=U.SEQ_BLUE[5], edgecolor=U.SURFACE, zorder=3)
            ax.errorbar(xs, ps, yerr=[np.clip(ps - lo, 0, None), np.clip(hi - ps, 0, None)], fmt="none", ecolor=U.INK, lw=1.0, capsize=2.5, zorder=4)
            if F["r_all"] is not None and not np.isnan(F["r_all"]):
                ax.axhline(PAIR_FRAC * F["r_all"], color="#eb6834", lw=1.3, ls="--", zorder=5, label=f"{PAIR_FRAC}·R_all (classification bar)")
            if F.get("best_single") is not None:
                ax.axhline(F["best_single"], color=U.INK2, lw=1.1, ls=":", zorder=5, label="best single position, α 1")
            ax.set_xticks(xs)
            ax.set_xticklabels([f"{q}\nn={P2[q]['n']}" for q in prs], fontsize=6.5)
            ax.set_ylim(0, 1.05)
            ax.set_ylabel("pair2 flip rate, α 1\n(Wilson 95% CI)", fontsize=8)
            ax.set_xlabel("position pair i-j (both interpolated at α 1, top-K positions)", fontsize=7.5)
            ax.grid(axis="y", color=U.GRID, lw=0.6)
            ax.set_axisbelow(True)
            ax.tick_params(axis="y", labelsize=7)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            ax.legend(fontsize=6.5, loc="upper right", frameon=False)
    fig_.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + f"Z4 single-position L38 swaps: model flip rate (top row) and the readers' normalised LO shift f_r per position × dose"
                  + ("; bottom: two-position (pair2) flip rate at α 1" if has_pair else "") + f"\n{summary['n_pairs']} pairs; classification {summary['classification']}", y=1.0, fontsize=9)
    fig_.tight_layout()
    fig_.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig_)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
