"""Y2 — do the readers follow the binding, the name, or the J-space component of a planted swap? (BRIEF_Y §Y2, E12–E13)

CPU only. Inputs:
  cache/g_agreement/y/y2_behaviour.jsonl   one row per NEW Y2 entry {key = pair|source|Y2|condition|alpha|k, condition name_only|name_removed|
                                           other_pair|J_only|J_perp|rand_only|rand_perp, k, flipped_to_other, coherent, lo_model, frac_norm_in_J[_full]}
  cache/g_agreement/y/y2_lo.jsonl          one row per (reader, entry) {key = reader|entry key, entry_key, reader, lo_toward_other, unscorable}
  cache/g_agreement/x/x2_behaviour.jsonl   the X2 rows: natural states (site nat) and the S2 planted ladder (condition ``full`` here, REUSED at
  cache/g_agreement/x/x2_lo.jsonl          alpha 0.5/0.75/1.0; alpha* per item from the whole S2 ladder); reader LO on those entries.
Orientation: every quantity is "toward the planted (other) candidate"; shift = lo(entry) − lo(natural entry of the same source state);
fraction = shift / sep with sep = (−lo_to(nat other state)) − lo_to(nat this state) (x_friday_r1 R1 definition: the reader's own natural
separation of the pair; 1.0 = the edited state reads like the other natural state).

E12  model flip rate per condition × alpha (Wilson + pair bootstrap), coherence; kept_original.
E13  per reader × condition at alpha = 1 and at the item's X2 alpha* (S2; alpha* = 0.25 maps to the smallest Y2 dose 0.5, recorded):
     win = P(shift > 0) (pair bootstrap), median fraction of own natural separation (pair bootstrap of the median), per-k rates for the
     multi-k conditions.
Decision per reader (alpha = 1):  ILL-POSED if the model flips under name_removed < 0.5 (no reader claim);
     READS THE BINDING if model flip under name_removed >= 0.75 and reader win >= 0.75 there;
     READS THE NAME if win >= 0.75 under name_only and <= 0.5 under name_removed; else MIXED.
J-space per reader:  READS NON-J if win >= 0.75 under J_perp while the J-lens's own J_perp win is inside its rand_perp band (<= the upper
     pair-bootstrap bound of its pooled rand_perp win); J-SPACE LEAK if win >= 0.75 under J_only and the model flips under J_only < 0.5.
other_pair: the structured null — reported per reader (win + CI = null band); flagged if the model flips under it (> 0.1) or if a reader's
     win there has a lower bound above 0.5; every other condition reports whether its win lower bound clears the other_pair upper bound.
Outputs results/g_agreement/y2/{summary.json, flips.csv, follow.csv, fig_main.png}.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402

MODULE = "y2"
READERS = ("olens", "nla", "jlens")
READER_LABELS = {"olens": "Oracle lens", "nla": "NLA", "jlens": "J-lens"}
CONDITIONS = ("full", "name_only", "name_removed", "other_pair", "J_only", "J_perp", "rand_only", "rand_perp")
COND_LABELS = {"full": "full Δ (X2, reused)", "name_only": "name_only", "name_removed": "name_removed", "other_pair": "other_pair (null)",
               "J_only": "Δ_J", "J_perp": "Δ_⊥", "rand_only": "rand_only (K=3)", "rand_perp": "rand_perp (K=3)"}
Y2_ALPHAS = (0.5, 0.75, 1.0)
REUSED_SITE, NAT, Y2_SITE = "S2", "nat", "Y2"
MODEL = "model"
WIN_HI, WIN_LO, FLIP_HI, FLIP_LO = 0.75, 0.5, 0.75, 0.5
OTHER_FLIP_MAX = 0.1
D_MODEL_DEFAULT = 5120
CACHE = ROOT / "cache" / "g_agreement"
Item = Tuple[str, str]


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--behaviour", default=str(CACHE / "y" / "y2_behaviour.jsonl"))
    ap.add_argument("--lo", default=str(CACHE / "y" / "y2_lo.jsonl"))
    ap.add_argument("--x2-behaviour", default=str(CACHE / "x" / "x2_behaviour.jsonl"))
    ap.add_argument("--x2-lo", default=str(CACHE / "x" / "x2_lo.jsonl"))
    ap.add_argument("--frozen-config", default=str(U.G_DIR / "manifest" / "frozen_config_x.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


def wilson_dict(k: int, n: int) -> dict:
    p, lo, hi = U.wilson(k, n)
    return {"k": k, "n": n, "p": p, "lo": lo, "hi": hi, "ci": "wilson"}


def _val(reader: str, row: dict, lo: Dict[str, Dict[str, Optional[float]]]) -> Optional[float]:
    if reader == MODEL:
        if row.get("lo_model_unscorable") or row.get("lo_model") is None:
            return None
        return float(row["lo_model"])
    return lo.get(reader, {}).get(row["key"])


def load_world(beh_path: str, lo_path: str, x2_beh_path: str, x2_lo_path: str) -> dict:
    """Y2 rows + the X2 rows they lean on (natural states; S2 planted ladder as ``full``)."""
    y2 = U.load_jsonl(beh_path) if Path(beh_path).exists() else []
    x2 = U.load_jsonl(x2_beh_path) if Path(x2_beh_path).exists() else []
    if not y2:
        raise U.AnalysisError(f"no Y2 behaviour rows in {beh_path}")
    if not x2:
        raise U.AnalysisError(f"no X2 behaviour rows in {x2_beh_path} (natural states and the reused full arm live there)")
    pairs = {r["pair_id"] for r in y2}
    nat = {(r["pair_id"], r["source"]): r for r in x2 if r["condition"] == "natural" and r["pair_id"] in pairs}
    full = []
    s2_ladder: Dict[Item, List[dict]] = defaultdict(list)
    for r in x2:
        if r["pair_id"] in pairs and r["site"] == REUSED_SITE and r["condition"] == "planted":
            s2_ladder[(r["pair_id"], r["source"])].append(r)
            if float(r["alpha"]) in Y2_ALPHAS:
                full.append({**r, "x2_condition": r["condition"], "condition": "full", "k": None, "reused": True, "site": Y2_SITE})
    rows = [dict(r, k=r.get("k", r.get("null_k"))) for r in y2] + full
    keys = [r["key"] for r in rows]
    if len(set(keys)) != len(keys):
        raise U.AnalysisError("duplicate entry keys across the Y2 and reused X2 rows")
    items = sorted({(r["pair_id"], r["source"]) for r in rows})
    missing_nat = [it for it in items if it not in nat]
    lo: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for p in (lo_path, x2_lo_path):
        if Path(p).exists():
            for r in U.load_jsonl(p):
                ek = r.get("entry_key") or r["key"].split("|", 1)[1]
                lo[r["reader"]][ek] = None if r.get("unscorable") else (None if r.get("lo_toward_other") is None else float(r["lo_toward_other"]))
    astar: Dict[Item, Optional[float]] = {}
    for it in items:
        fl = [float(r["alpha"]) for r in s2_ladder.get(it, []) if r["flipped_to_other"] and r.get("coherent", True)]
        astar[it] = min(fl) if fl else None
    grp: Dict[Tuple[Item, str], List[dict]] = defaultdict(list)
    for r in rows:
        grp[((r["pair_id"], r["source"]), r["condition"])].append(r)
    for g in grp.values():
        g.sort(key=lambda r: (float(r["alpha"]), -1 if r.get("k") is None else int(r["k"])))
    readers = [rd for rd in READERS if rd in lo]
    conditions = [c for c in CONDITIONS if any(r["condition"] == c for r in rows)]
    return {"rows": rows, "items": items, "nat": nat, "missing_nat": missing_nat, "lo": dict(lo), "astar": astar, "grp": dict(grp),
            "readers": readers, "conditions": conditions, "alphas": sorted({float(r["alpha"]) for r in rows}), "n_x2_rows": len(x2),
            "fam": {(r["pair_id"], r["source"]): r["family"] for r in rows}}


def separation(w: dict, reader: str) -> Dict[Item, Optional[float]]:
    out: Dict[Item, Optional[float]] = {}
    for it in w["items"]:
        other = (it[0], "B" if it[1] == "A" else "A")
        a = None if it not in w["nat"] else _val(reader, w["nat"][it], w["lo"])
        b = None if other not in w["nat"] else _val(reader, w["nat"][other], w["lo"])
        out[it] = None if a is None or b is None else (-b) - a
    return out


def alpha_used(astar: Optional[float], alphas: List[float]) -> Optional[float]:
    """alpha* itself if it is on the Y2 ladder, else the smallest ladder dose >= alpha* (none if alpha* > every dose)."""
    if astar is None:
        return None
    up = [a for a in alphas if a >= astar - 1e-9]
    return min(up) if up else None


def median_boot(vals_by_pair: Dict[str, List[float]], nb: int, sd: int) -> Tuple[float, float, float, float, float, int]:
    """(median, lo, hi, q25, q75, n) with a pair bootstrap of the median."""
    allv = np.array([v for vs in vals_by_pair.values() for v in vs], dtype=float)
    if allv.size == 0:
        return (float("nan"),) * 5 + (0,)
    pids = sorted(p for p, v in vals_by_pair.items() if v)

    def stat(ps):
        v = np.concatenate([np.asarray(vals_by_pair[p], dtype=float) for p in ps]) if ps else np.array([])
        return float("nan") if v.size == 0 else float(np.median(v))

    m, lo, hi = U.pair_bootstrap_stat(pids, stat, nb, sd)
    return m, lo, hi, float(np.quantile(allv, 0.25)), float(np.quantile(allv, 0.75)), int(allv.size)


def run(args: argparse.Namespace) -> dict:
    frozen, _ = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if frozen else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    nb, sd = args.n_boot, args.seed
    w = load_world(args.behaviour, args.lo, args.x2_behaviour, args.x2_lo)
    rows, items, readers, conds, alphas = w["rows"], w["items"], w["readers"], w["conditions"], w["alphas"]
    pairs = sorted({p for p, _ in items})
    U.log(f"[y2] frozen={frozen} {len(rows)} entries ({sum(1 for r in rows if r.get('reused'))} reused full) / {len(items)} items / {len(pairs)} pairs; "
          f"conditions {conds}; alphas {alphas}; readers {readers}; {len(w['missing_nat'])} items without a natural row; out={out}")
    summary: dict = {"module": MODULE, "frozen": frozen, "n_entries": len(rows), "n_items": len(items), "n_pairs": len(pairs), "n_boot": nb, "seed": sd,
                     "readers": readers, "conditions": conds, "alphas": alphas, "n_items_without_natural": len(w["missing_nat"]),
                     "orientation": "positive = toward the planted (other) candidate; shift = lo(entry) - lo(natural); fraction = shift / own natural separation",
                     "thresholds": {"win_hi": WIN_HI, "win_lo": WIN_LO, "flip_hi": FLIP_HI, "flip_lo": FLIP_LO, "other_pair_flip_max": OTHER_FLIP_MAX}}
    flips_csv: List[dict] = []
    follow_csv: List[dict] = []

    # ---------------- E12 model flips ----------------
    e12: dict = {}
    for c in conds:
        e12[c] = {}
        for a in alphas:
            rs = [r for it in items for r in w["grp"].get((it, c), []) if float(r["alpha"]) == a]
            if not rs:
                continue
            k = sum(bool(r["flipped_to_other"]) for r in rs)
            coh = sum(bool(r.get("coherent")) for r in rs)
            per_k = {}
            for kk in sorted({r.get("k") for r in rs}, key=lambda x: -1 if x is None else x):
                sub = [r for r in rs if r.get("k") == kk]
                per_k[str(kk)] = wilson_dict(sum(bool(r["flipped_to_other"]) for r in sub), len(sub))
            e12[c][str(a)] = {"flip": wilson_dict(k, len(rs)), "flip_pair_boot": U.pair_rate([(r["pair_id"], bool(r["flipped_to_other"])) for r in rs], nb, sd).as_dict(),
                              "coherence": wilson_dict(coh, len(rs)), "coherence_flag": coh / len(rs) < 0.8,
                              "kept_original": wilson_dict(sum(bool(r.get("kept_original")) for r in rs), len(rs)),
                              "n_items": len({(r["pair_id"], r["source"]) for r in rs}), "per_k": per_k if len(per_k) > 1 else None}
            flips_csv.append({"condition": c, "alpha": a, "k": "pooled", "k_flips": k, "n": len(rs), "p": k / len(rs), "lo": e12[c][str(a)]["flip"]["lo"],
                              "hi": e12[c][str(a)]["flip"]["hi"], "coherence": coh / len(rs), "n_items": e12[c][str(a)]["n_items"], "reused": c == "full"})
            for kk, v in per_k.items():
                if len(per_k) > 1:
                    flips_csv.append({"condition": c, "alpha": a, "k": kk, "k_flips": v["k"], "n": v["n"], "p": v["p"], "lo": v["lo"], "hi": v["hi"], "reused": False})
            U.log(f"[y2] E12 {c:13s} α={a}: flip {U.fmt_count(k, len(rs))} [{100 * e12[c][str(a)]['flip']['lo']:.0f}, {100 * e12[c][str(a)]['flip']['hi']:.0f}]"
                  f"; coherence {U.fmt_count(coh, len(rs))}{' FLAG' if coh / len(rs) < 0.8 else ''}")
    summary["E12_flip_by_condition_alpha"] = e12

    def flip_p(c: str, a: float = 1.0) -> float:
        return e12.get(c, {}).get(str(a), {}).get("flip", {}).get("p", float("nan"))

    # ---------------- alpha* (X2 S2) ----------------
    a_used = {it: alpha_used(w["astar"][it], alphas) for it in items}
    summary["alpha_star"] = {"source": "X2 S2 ladder (smallest alpha with a coherent flip)", "n_with_alpha_star": sum(1 for it in items if w["astar"][it] is not None),
                             "n_mapped_up": sum(1 for it in items if w["astar"][it] is not None and a_used[it] is not None and a_used[it] != w["astar"][it]),
                             "n_unusable": sum(1 for it in items if w["astar"][it] is not None and a_used[it] is None),
                             "counts": {str(a): sum(1 for it in items if w["astar"][it] == a) for a in sorted({v for v in w["astar"].values() if v is not None})},
                             "per_item": {f"{p}|{s}": {"alpha_star": w["astar"][(p, s)], "alpha_used": a_used[(p, s)]} for p, s in items}}

    # ---------------- E13 reader follow ----------------
    e13: dict = {}
    for rd in readers + [MODEL]:
        sep = separation(w, rd)
        R: dict = {"n_items_scorable": sum(1 for it in items if sep[it] is not None), "by_condition": {}}
        for c in conds:
            C_: dict = {}
            for at in ("alpha_1", "alpha_star"):
                win_flags, fr_by_pair, per_k_flags = [], defaultdict(list), defaultdict(list)
                for it in items:
                    a = 1.0 if at == "alpha_1" else a_used[it]
                    if a is None or it not in w["nat"]:
                        continue
                    l0 = _val(rd, w["nat"][it], w["lo"])
                    if l0 is None:
                        continue
                    for r in w["grp"].get((it, c), []):
                        if float(r["alpha"]) != a:
                            continue
                        v = _val(rd, r, w["lo"])
                        if v is None:
                            continue
                        shift = v - l0
                        win_flags.append((it[0], shift > 0))
                        per_k_flags[r.get("k")].append((it[0], shift > 0))
                        frac = None if sep[it] in (None, 0) else shift / sep[it]
                        if frac is not None:
                            fr_by_pair[it[0]].append(frac)
                        if rd != MODEL or at == "alpha_1":
                            follow_csv.append({"reader": rd, "condition": c, "at": at, "alpha": a, "pair_id": it[0], "source": it[1], "family": w["fam"][it], "k": r.get("k"),
                                               "alpha_star": w["astar"][it], "shift": shift, "sep": sep[it], "fraction": frac, "win": shift > 0,
                                               "model_flipped": bool(r["flipped_to_other"]), "model_lo_shift": (None if _val(MODEL, r, w["lo"]) is None or _val(MODEL, w["nat"][it], w["lo"]) is None
                                                                                                        else _val(MODEL, r, w["lo"]) - _val(MODEL, w["nat"][it], w["lo"])),
                                               "frac_norm_in_J": r.get("frac_norm_in_J"), "reused": bool(r.get("reused"))})
                win = U.pair_rate(win_flags, nb, sd)
                med = median_boot(fr_by_pair, nb, sd)
                C_[at] = {"win": win.as_dict(), "fraction_median": med[0], "fraction_lo": med[1], "fraction_hi": med[2], "fraction_q25": med[3], "fraction_q75": med[4],
                          "n_fraction": med[5], "per_k_win": ({str(k): U.pair_rate(f, nb, sd).as_dict() for k, f in per_k_flags.items()} if len(per_k_flags) > 1 else None)}
            R["by_condition"][c] = C_
        e13[rd] = R
    # null band from other_pair + "above band" per condition; J-lens inside its rand_perp band
    for rd in readers + [MODEL]:
        R = e13[rd]
        op = R["by_condition"].get("other_pair", {}).get("alpha_1", {}).get("win")
        R["other_pair_null_band"] = None if op is None else {"lo": op["lo"], "hi": op["hi"], "p": op["p"], "n": op["n"]}
        for c, C_ in R["by_condition"].items():
            wn = C_.get("alpha_1", {}).get("win", {})
            C_["above_other_pair_band"] = None if op is None or wn.get("n", 0) == 0 or np.isnan(wn.get("lo", np.nan)) else bool(wn["lo"] > op["hi"])
        rp = R["by_condition"].get("rand_perp", {}).get("alpha_1", {}).get("win")
        jp = R["by_condition"].get("J_perp", {}).get("alpha_1", {}).get("win")
        R["J_perp_inside_rand_perp_band"] = None if rp is None or jp is None or rp["n"] == 0 or jp["n"] == 0 or np.isnan(rp["hi"]) else bool(jp["p"] <= rp["hi"])
        ro = R["by_condition"].get("rand_only", {}).get("alpha_1", {}).get("win")
        jo = R["by_condition"].get("J_only", {}).get("alpha_1", {}).get("win")
        R["J_only_above_rand_only_band"] = None if ro is None or jo is None or ro["n"] == 0 or jo["n"] == 0 or np.isnan(ro["hi"]) else bool(jo["p"] > ro["hi"])
    summary["E13_follow"] = e13

    # ---------------- decisions ----------------
    f_nr, f_no, f_jo, f_op = flip_p("name_removed"), flip_p("name_only"), flip_p("J_only"), flip_p("other_pair")
    site_posed = None if np.isnan(f_nr) else ("ILL-POSED" if f_nr < FLIP_LO else ("WELL-POSED" if f_nr >= FLIP_HI else "PARTIAL"))
    summary["site"] = {"model_flip_name_removed_alpha1": f_nr, "model_flip_name_only_alpha1": f_no, "model_flip_full_alpha1": flip_p("full"),
                       "model_flip_J_only_alpha1": f_jo, "model_flip_J_perp_alpha1": flip_p("J_perp"), "model_flip_other_pair_alpha1": f_op,
                       "model_flip_rand_only_alpha1": flip_p("rand_only"), "model_flip_rand_perp_alpha1": flip_p("rand_perp"),
                       "status": site_posed, "other_pair_flips_model": None if np.isnan(f_op) else bool(f_op > OTHER_FLIP_MAX),
                       "rule": "ILL-POSED if model flip under name_removed at alpha 1 < 0.5; WELL-POSED if >= 0.75"}
    jl_inside = e13.get("jlens", {}).get("J_perp_inside_rand_perp_band") if "jlens" in e13 else None
    dec: dict = {}
    for rd in readers:
        bc = e13[rd]["by_condition"]

        def wp(c: str) -> float:
            return bc.get(c, {}).get("alpha_1", {}).get("win", {}).get("p", float("nan"))

        w_nr, w_no, w_jp, w_jo, w_op = wp("name_removed"), wp("name_only"), wp("J_perp"), wp("J_only"), wp("other_pair")
        if site_posed is None or np.isnan(w_nr):
            verdict, reason = "UNDETERMINED", "no name_removed rows (or no scorable LO) at alpha 1"
        elif site_posed == "ILL-POSED":
            verdict, reason = "ILL-POSED", f"model flips under name_removed {f_nr:.2f} < {FLIP_LO}: no reader claim at this site"
        elif f_nr >= FLIP_HI and w_nr >= WIN_HI:
            verdict, reason = "READS THE BINDING", f"model flip {f_nr:.2f} >= {FLIP_HI} and win {w_nr:.2f} >= {WIN_HI} under name_removed"
        elif not np.isnan(w_no) and w_no >= WIN_HI and w_nr <= WIN_LO:
            verdict, reason = "READS THE NAME", f"win {w_no:.2f} >= {WIN_HI} under name_only and {w_nr:.2f} <= {WIN_LO} under name_removed"
        else:
            verdict, reason = "MIXED", f"name_removed win {w_nr:.2f} (model flip {f_nr:.2f}), name_only win {w_no:.2f}"
        if np.isnan(w_jp) or np.isnan(f_jo):
            jv, jr = "UNTESTED", "no J-space rows at alpha 1"
        else:
            flags = []
            if w_jp >= WIN_HI and jl_inside is True:
                flags.append("READS NON-J")
            if not np.isnan(w_jo) and w_jo >= WIN_HI and f_jo < FLIP_LO:
                flags.append("J-SPACE LEAK")
            jv = " + ".join(flags) if flags else "NONE"
            jr = (f"J_perp win {w_jp:.2f}, J-lens inside its rand_perp band: {jl_inside}; J_only win {w_jo:.2f}, model flip under J_only {f_jo:.2f}")
        op_band = e13[rd]["other_pair_null_band"]
        dec[rd] = {"verdict": verdict, "reason": reason, "jspace_verdict": jv, "jspace_reason": jr,
                   "other_pair_moves_reader": None if op_band is None or np.isnan(op_band["lo"]) else bool(op_band["lo"] > WIN_LO),
                   "win_alpha1": {c: wp(c) for c in conds}, "other_pair_win": w_op}
        U.log(f"[y2] {READER_LABELS[rd]:12s}: {verdict} ({reason}); J-space: {jv} ({jr}); other_pair win {w_op:.2f}")
    summary["decisions"] = dec
    summary["classification"] = {rd: dec[rd]["verdict"] for rd in readers}
    summary["jspace_classification"] = {rd: dec[rd]["jspace_verdict"] for rd in readers}

    # ---------------- Δ_J energy ----------------
    by_pair_full = defaultdict(list)
    for r in rows:
        if r.get("frac_norm_in_J_full") is not None:
            by_pair_full[r["pair_id"]].append(float(r["frac_norm_in_J_full"]))
    per_pair_full = {p: float(np.mean(v)) for p, v in by_pair_full.items()}
    r_star = next((int(r["r_star"]) for r in rows if r.get("r_star") is not None), None)
    d = D_MODEL_DEFAULT
    en = {"definition": "||Δ_J||_F / ||Δ||_F over all positions of the pair's full swap delta at L38 (frac_norm_in_J_full)", "r_star": r_star, "d_assumed": d,
          "expected_random": None if r_star is None else float(np.sqrt(r_star / d)), "n_pairs": len(per_pair_full),
          "median": float(np.median(list(per_pair_full.values()))) if per_pair_full else None,
          "q25": float(np.quantile(list(per_pair_full.values()), 0.25)) if per_pair_full else None,
          "q75": float(np.quantile(list(per_pair_full.values()), 0.75)) if per_pair_full else None,
          "by_condition_median": {c: float(np.median([float(r["frac_norm_in_J"]) for r in rows if r["condition"] == c and r.get("frac_norm_in_J") is not None]))
                                  for c in conds if any(r["condition"] == c and r.get("frac_norm_in_J") is not None for r in rows)}}
    summary["delta_J_energy"] = en
    if en["median"] is not None:
        U.log(f"[y2] Δ_J energy fraction: median {en['median']:.3f} [IQR {en['q25']:.3f}, {en['q75']:.3f}] over {en['n_pairs']} pairs; random expectation {en['expected_random']}")

    U.write_csv(out / "flips.csv", flips_csv)
    U.write_csv(out / "follow.csv", follow_csv)
    U.write_json(out / "summary.json", summary)
    if not args.no_fig:
        make_fig_main(out / "fig_main.png", summary, readers, conds, frozen)
    U.log(f"[y2] wrote {out}")
    return summary


def _rate(d: dict) -> U.Rate:
    return U.Rate(int(d.get("k", 0)), int(d.get("n", 0)), d.get("p", float("nan")), d.get("lo", float("nan")), d.get("hi", float("nan")), int(d.get("n_pairs", 0)), d.get("ci", ""))


def make_fig_main(path: Path, summary: dict, readers, conds, frozen: bool) -> None:
    plt = U.mpl()
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw={"width_ratios": [1, 1.6]})
    xs = np.arange(len(conds))
    e12 = summary["E12_flip_by_condition_alpha"]
    for i, c in enumerate(conds):
        f = e12.get(c, {}).get("1.0")
        if not f:
            continue
        rate = _rate({**f["flip"], "n_pairs": f["n_items"]})
        U.bar_ci(axl, i, rate, U.METHOD_COLORS["target"], width=0.62, hollow=(c == "other_pair"))
    axl.axhline(FLIP_HI, color=U.INK2, lw=0.8, ls="--"); axl.axhline(FLIP_LO, color=U.INK2, lw=0.6, ls=":")
    axl.set_xticks(xs); axl.set_xticklabels([COND_LABELS[c] for c in conds], fontsize=7.5, rotation=25, ha="right")
    U.style_ax(axl, "model flip rate at α = 1 (% of entries answering the planted candidate)", (0, 1.15))
    st = summary["site"]
    axl.set_title(f"E12 — model flips at S2 (L38) per condition, α = 1 (Wilson 95%)\nsite {st['status']} (name_removed flip {st['model_flip_name_removed_alpha1']:.2f})", fontsize=9.5)
    # right: reader win per condition, grouped by reader
    nr = max(1, len(readers))
    width = 0.8 / nr
    for j, rd in enumerate(readers):
        bc = summary["E13_follow"][rd]["by_condition"]
        for i, c in enumerate(conds):
            wn = bc.get(c, {}).get("alpha_1", {}).get("win")
            if not wn or wn["n"] == 0:
                continue
            x = i - 0.4 + width * (j + 0.5)
            U.bar_ci(axr, x, _rate(wn), U.METHOD_COLORS[rd], width=width * 0.92, hollow=(c == "other_pair"),
                     label=(f"{READER_LABELS[rd]} — {summary['classification'][rd]}; J: {summary['jspace_classification'][rd]}" if i == 0 else None), annotate=False)
    axr.axhline(WIN_HI, color=U.INK2, lw=0.8, ls="--"); axr.axhline(WIN_LO, color=U.INK2, lw=0.6, ls=":")
    axr.set_xticks(xs); axr.set_xticklabels([COND_LABELS[c] for c in conds], fontsize=7.5, rotation=25, ha="right")
    U.style_ax(axr, "reader win at α = 1 (% of entries with LO shift toward the planted candidate > 0)", (0, 1.3))
    axr.set_title("E13 — reader follow per condition, α = 1 (95% pair-bootstrap CI); hollow = other_pair structured null", fontsize=9.5)
    if axr.get_legend_handles_labels()[0]:
        axr.legend(fontsize=7.5, loc="upper left", ncol=1)
    fig.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + f"Y2 identity-free nulls and the J-space split at S2: {summary['n_items']} items / {summary['n_pairs']} pairs; "
                 f"dashed = 0.75, dotted = 0.5 decision lines", y=1.02, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
