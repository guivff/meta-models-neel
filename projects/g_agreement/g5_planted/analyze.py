"""G5 — does any reader follow a binding planted inside the state? (BRIEF_G5G6.md, endpoints E1–E4)

CPU only. Inputs (written by the GPU track):
  cache/g_agreement/g5/lo.jsonl         reader log-odds in native format, one row per (reader, state, condition, dose, null_k)
                                        {pair_id, state_item_id, family, reader, condition natural|planted|null, alpha, sign, null_k,
                                         cand_A, cand_B, lo, lp_A, lp_B, templates, dose_abs, input_norm, unscorable}
                                        cand_A is the candidate that is correct for the ORIGINAL state; lo = lp_A - lp_B.
  cache/g_agreement/g5/behaviour.jsonl  target greedy decode with the edited vector in place
                                        {state_item_id, condition, alpha, sign, null_k, answer_text, parsed, flipped_to_other}
  cache/g_agreement/gens/g5.jsonl + results/g_agreement/claims/g5.jsonl   free readouts after planting (G1 schema, condition planted)

Orientation: every planted edit pushes the state toward the OTHER candidate, so "follows" = the reader's
log-odds for the original candidate goes DOWN. shift_toward_other = lo_natural - lo_edited (positive = followed).
  E1 natural separation per reader: paired win rate over the 8 pairs = P(LO_pair(h_A) > LO_pair(h_B)) in a fixed
     per-pair orientation (equivalently lo(h_A) + lo(h_B) > 0), and AUROC over the 16 states (score = LO for the
     pair's first candidate, label = state whose correct candidate that is); pair-bootstrap CIs.
  E2 follow rate per dose: z = (mean(lo_null) - lo_planted) / sd(lo_null) over the K=20 nulls of the same state and
     dose; z >= 3 follows. Null band = the same statistic for each null against the other 19 (leave-one-out), whose
     follow rate is the "null band" of the decision rule; the mean +/- 2 sd of null shifts is drawn in the figure.
  E3 behavioural flip rate per dose, planted vs null directions.
  E4 free-readout assertion rate after planting: coverage, asserting the planted (other) candidate, the original one.
Decision per reader (pre-registered): doses with E3 >= 0.75 are valid; none valid -> manipulation failed (nothing
concluded about readers; kill K4 if flip at alpha 1.5 < 0.5). Else "follows" if E2 >= 0.75 at the smallest valid dose
and the null follow rate there < 0.25; "insensitive" if E2 <= 0.25 at the largest valid dose; otherwise "mixed".

Outputs results/g_agreement/g5[/dev]/{fig_main.png, g5.csv, summary.json}. Pair bootstrap over the 8 base pairs.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402

MODULE = "g5"
READERS = ("olens", "nla", "jlens")
READER_LABELS = {"olens": "Oracle lens", "nla": "NLA", "jlens": "J-lens"}
Z_FOLLOW = 3.0
FLIP_VALID = 0.75
FOLLOW_HI, FOLLOW_LO, NULL_BAND_MAX, KILL_ALPHA, KILL_FLIP = 0.75, 0.25, 0.25, 1.5, 0.5


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(U.DEFAULTS["items"]))
    ap.add_argument("--lo", default=str(ROOT / "cache" / "g_agreement" / "g5" / "lo.jsonl"))
    ap.add_argument("--behaviour", default=str(ROOT / "cache" / "g_agreement" / "g5" / "behaviour.jsonl"))
    ap.add_argument("--gens", default=str(U.DEFAULTS["gens_dir"] / "g5.jsonl"))
    ap.add_argument("--claims", default=str(U.DEFAULTS["claims_dir"] / "g5.jsonl"))
    ap.add_argument("--frozen-config", default=str(U.DEFAULTS["frozen_config"]))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


def resolve_out(module: str, frozen: bool, out: Optional[str]) -> Path:
    if out:
        return Path(out)
    base = U.DEFAULTS["results_dir"] / module
    return base if frozen else base / "dev"


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based AUROC with ties at 0.5; nan if one class is empty."""
    from scipy.stats import rankdata

    pos, neg = labels == 1, labels == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    r = rankdata(scores)
    return float((r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def _dose_key(r: dict) -> Tuple[float, int]:
    return (float(r["alpha"]), int(r.get("sign") or 0))


def natural_separation(items, nat: Dict[str, dict], pair_ids: List[str], nb: int, sd: int) -> dict:
    """E1 for one reader. nat: {state_item_id: natural lo row (scorable)}."""
    by_pair: Dict[str, Dict[str, dict]] = defaultdict(dict)
    for sid, r in nat.items():
        by_pair[items[sid]["pair_id"]][items[sid]["version"]] = r
    complete = [p for p in pair_ids if "A" in by_pair[p] and "B" in by_pair[p]]
    # fixed orientation: LO for the candidate that is correct in version A
    win = {p: int(by_pair[p]["A"]["lo"] + by_pair[p]["B"]["lo"] > 0) for p in complete}
    tie = {p: int(by_pair[p]["A"]["lo"] + by_pair[p]["B"]["lo"] == 0) for p in complete}
    scores: Dict[str, List[Tuple[float, int]]] = {}
    for p in complete:
        a, b = by_pair[p]["A"], by_pair[p]["B"]
        scores[p] = [(a["lo"], 1), (-b["lo"], 0)]   # -lo(h_B) = log-odds of A's candidate in state B

    def stat_win(ps):
        return float("nan") if not ps else sum(win[p] for p in ps) / len(ps)

    def stat_auc(ps):
        sc = np.array([s for p in ps for s, _ in scores[p]]); lb = np.array([l for p in ps for _, l in scores[p]])
        return auroc(sc, lb) if len(sc) else float("nan")

    w = U.pair_bootstrap_stat(complete, stat_win, nb, sd) if complete else (float("nan"),) * 3
    a = U.pair_bootstrap_stat(complete, stat_auc, nb, sd) if complete else (float("nan"),) * 3
    return {"n_pairs_scored": len(complete), "n_states_scored": 2 * len(complete), "n_pairs_total": len(pair_ids),
            "win_rate": {"k": sum(win.values()), "n": len(complete), "p": w[0], "lo": w[1], "hi": w[2], "ties": sum(tie.values())},
            "auroc": {"est": a[0], "lo": a[1], "hi": a[2], "n_states": 2 * len(complete)},
            "mean_lo_natural_for_own_candidate": float(np.mean([r["lo"] for r in nat.values()])) if nat else float("nan")}


def run(args: argparse.Namespace) -> dict:
    frozen, cfg = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    out = resolve_out(MODULE, frozen, args.out)
    out.mkdir(parents=True, exist_ok=True)
    meta, items = U.load_items(args.items)
    lo_rows = U.load_jsonl(args.lo)
    beh_rows = U.load_jsonl(args.behaviour) if Path(args.behaviour).exists() else []
    nb, sd = args.n_boot, args.seed
    pid = lambda s: items[s]["pair_id"]  # noqa: E731

    state_ids = sorted({r["state_item_id"] for r in lo_rows})
    for s in state_ids:
        if s not in items:
            raise U.AnalysisError(f"lo.jsonl references unknown state {s}")
        if items[s]["family"] not in U.RELATION_FAMILIES or items[s]["split"] != "test":
            raise U.SplitLeakageError(f"G5 state {s} is not an ownership/mapping test state ({items[s]['family']}, {items[s]['split']})")
    pair_ids = U.pairs_of(items, state_ids)
    U.log(f"[g5] frozen={frozen} {len(state_ids)} states / {len(pair_ids)} pairs; {len(lo_rows)} LO rows, {len(beh_rows)} behaviour rows; out={out}")

    csv_rows: List[dict] = []
    summary: dict = {"module": MODULE, "frozen": frozen, "n_states": len(state_ids), "n_pairs": len(pair_ids), "n_boot": nb, "seed": sd,
                     "orientation": "lo = log-odds of the ORIGINAL state's correct candidate; shift_toward_other = lo_natural - lo_edited",
                     "readers": {}}

    # ---------------- E3 behaviour (reader-independent) ----------------
    beh = defaultdict(list)   # (condition, alpha) -> rows
    for r in beh_rows:
        if r["state_item_id"] not in items:
            raise U.AnalysisError(f"behaviour row references unknown state {r['state_item_id']}")
        beh[(r["condition"], float(r["alpha"]) if r.get("alpha") is not None else None)].append(r)
    flip: Dict[str, dict] = {}
    alphas = sorted({a for (c, a) in beh if c == "planted" and a is not None})
    for a in alphas:
        pl = beh[("planted", a)]
        nu = beh.get(("null", a), [])
        flip[str(a)] = {"planted": U.pair_rate([(pid(r["state_item_id"]), bool(r.get("flipped_to_other"))) for r in pl], nb, sd).as_dict(),
                        "planted_unparsed": sum(r.get("parsed") is None for r in pl),
                        "null": U.pair_rate([(pid(r["state_item_id"]), bool(r.get("flipped_to_other"))) for r in nu], nb, sd).as_dict() if nu else None,
                        "by_sign": {str(s): U.pair_rate([(pid(r["state_item_id"]), bool(r.get("flipped_to_other"))) for r in pl if int(r.get("sign") or 0) == s], nb, sd).as_dict()
                                    for s in sorted({int(r.get("sign") or 0) for r in pl})}}
        f = flip[str(a)]
        U.log(f"[g5] E3 flip rate alpha={a}: planted {U.fmt_count(f['planted']['k'], f['planted']['n'])}" +
              (f"; null {U.fmt_count(f['null']['k'], f['null']['n'])}" if f["null"] else "; null: none at this dose"))
        for r in pl + nu:
            csv_rows.append({"table": "behaviour", "reader": "", "state_item_id": r["state_item_id"], "pair_id": pid(r["state_item_id"]), "condition": r["condition"],
                             "alpha": a, "sign": r.get("sign"), "null_k": r.get("null_k"), "parsed": r.get("parsed"), "flipped_to_other": r.get("flipped_to_other")})
    nat_beh = beh.get(("natural", None), []) + beh.get(("natural", 0.0), [])
    if nat_beh:
        summary["natural_behaviour_correct"] = U.pair_rate([(pid(r["state_item_id"]), U.normalise_answer(r.get("parsed")) == U.normalise_answer(items[r["state_item_id"]]["primary"]["answer"])) for r in nat_beh], nb, sd).as_dict()
    valid_doses = [a for a in alphas if flip[str(a)]["planted"]["p"] >= FLIP_VALID and (flip[str(a)]["null"] is None or flip[str(a)]["planted"]["p"] > flip[str(a)]["null"]["p"])]
    kill = (str(KILL_ALPHA) in flip and flip[str(KILL_ALPHA)]["planted"]["p"] < KILL_FLIP)
    summary["E3_flip_rate_by_alpha"] = flip
    summary["valid_doses_E3_ge_0.75"] = valid_doses
    summary["kill_K4_flip_at_1.5_below_0.5"] = kill
    summary["manipulation_failed"] = (not valid_doses) or kill
    U.log(f"[g5] valid doses (E3 >= {FLIP_VALID}, above null): {valid_doses}; K4 kill: {kill}; manipulation_failed={summary['manipulation_failed']}")

    # ---------------- E4 free readouts after planting ----------------
    gens = U.load_gens(args.gens) if Path(args.gens).exists() else []
    claims = U.load_claims(args.claims) if Path(args.claims).exists() else {}
    e4: Dict[str, dict] = {}
    for rd in ("olens", "nla"):
        rows = [g for g in gens if g.get("method") == rd and g.get("condition") == "planted"]
        if not rows:
            continue
        cl = [(pid(g["item_id"]), claims.get(g["gen_id"])) for g in rows]
        e4[rd] = {"n_readouts": len(rows),
                  "asserts_any": U.pair_rate([(p, U.vote(c) is not None) for p, c in cl], nb, sd).as_dict(),
                  "asserts_planted_other": U.pair_rate([(p, U.claim_status(c) == "contradicts") for p, c in cl], nb, sd).as_dict(),
                  "asserts_original": U.pair_rate([(p, U.claim_status(c) == "supports") for p, c in cl], nb, sd).as_dict(),
                  "status_counts": dict(Counter(U.claim_status(c) for _, c in cl)),
                  "alphas": sorted({float((g.get("input") or {}).get("alpha", g.get("alpha", float("nan")))) for g in rows})}
        d = e4[rd]
        U.log(f"[g5] E4 {READER_LABELS[rd]}: asserts any {U.fmt_count(d['asserts_any']['k'], d['asserts_any']['n'])}; planted candidate "
              f"{U.fmt_count(d['asserts_planted_other']['k'], d['asserts_planted_other']['n'])}; original {U.fmt_count(d['asserts_original']['k'], d['asserts_original']['n'])}")
        for g in rows:
            c = claims.get(g["gen_id"])
            csv_rows.append({"table": "free_readout", "reader": rd, "state_item_id": g["item_id"], "pair_id": pid(g["item_id"]), "condition": "planted",
                             "alpha": (g.get("input") or {}).get("alpha", g.get("alpha")), "status": U.claim_status(c), "value": U.vote(c)})
    summary["E4_free_readouts_after_planting"] = e4

    # ---------------- E1 / E2 per reader ----------------
    for rd in READERS:
        rows = [r for r in lo_rows if r["reader"] == rd]
        if not rows:
            U.log(f"[g5] WARNING no LO rows for {rd}")
            continue
        unscorable = [r for r in rows if r.get("unscorable")]
        rows = [r for r in rows if not r.get("unscorable")]
        nat = {r["state_item_id"]: r for r in rows if r["condition"] == "natural"}
        if len(nat) != sum(1 for r in rows if r["condition"] == "natural"):
            raise U.AnalysisError(f"{rd}: more than one natural LO row for a state")
        e1 = natural_separation(items, nat, pair_ids, nb, sd)
        U.log(f"[g5] E1 {READER_LABELS[rd]}: win rate {U.fmt_count(e1['win_rate']['k'], e1['win_rate']['n'])} [{100 * e1['win_rate']['lo']:.0f}, {100 * e1['win_rate']['hi']:.0f}]; "
              f"AUROC {e1['auroc']['est']:.2f} [{e1['auroc']['lo']:.2f}, {e1['auroc']['hi']:.2f}] over {e1['auroc']['n_states']} states; unscorable rows {len(unscorable)}")
        for s, r in nat.items():
            csv_rows.append({"table": "lo", "reader": rd, "state_item_id": s, "pair_id": pid(s), "condition": "natural", "alpha": 0.0, "sign": 0, "null_k": None,
                             "lo": r["lo"], "lo_natural": r["lo"], "shift_toward_other": 0.0, "z": None, "follows": None, "cand_A": r.get("cand_A"), "cand_B": r.get("cand_B")})
        nulls: Dict[Tuple[str, float], List[dict]] = defaultdict(list)
        for r in rows:
            if r["condition"] == "null":
                nulls[(r["state_item_id"], float(r["alpha"]))].append(r)
        e2: Dict[str, dict] = {}
        for a in sorted({float(r["alpha"]) for r in rows if r["condition"] == "planted"}):
            pl = [r for r in rows if r["condition"] == "planted" and float(r["alpha"]) == a]
            fol, shifts, zs, null_fol, null_shifts, n_missing_nat = [], [], [], [], [], 0
            for r in pl:
                s = r["state_item_id"]
                if s not in nat:
                    n_missing_nat += 1
                    continue
                nl = np.array([q["lo"] for q in nulls.get((s, a), [])], dtype=float)
                shift = nat[s]["lo"] - r["lo"]
                z = float((nl.mean() - r["lo"]) / nl.std(ddof=1)) if len(nl) >= 3 and nl.std(ddof=1) > 0 else float("nan")
                f = (not np.isnan(z)) and z >= Z_FOLLOW
                fol.append((pid(s), None if np.isnan(z) else f)); shifts.append((pid(s), shift)); zs.append(z)
                csv_rows.append({"table": "lo", "reader": rd, "state_item_id": s, "pair_id": pid(s), "condition": "planted", "alpha": a, "sign": r.get("sign"), "null_k": None,
                                 "lo": r["lo"], "lo_natural": nat[s]["lo"], "shift_toward_other": shift, "z": z, "follows": f, "n_null": len(nl), "cand_A": r.get("cand_A"), "cand_B": r.get("cand_B")})
            for (s, aa), nl_rows in nulls.items():
                if aa != a or s not in nat:
                    continue
                nl = np.array([q["lo"] for q in nl_rows], dtype=float)
                for j, q in enumerate(nl_rows):
                    rest = np.delete(nl, j)
                    zq = float((rest.mean() - q["lo"]) / rest.std(ddof=1)) if len(rest) >= 3 and rest.std(ddof=1) > 0 else float("nan")
                    shift_q = nat[s]["lo"] - q["lo"]
                    null_fol.append((pid(s), None if np.isnan(zq) else zq >= Z_FOLLOW)); null_shifts.append((pid(s), shift_q))
                    csv_rows.append({"table": "lo", "reader": rd, "state_item_id": s, "pair_id": pid(s), "condition": "null", "alpha": a, "sign": q.get("sign"), "null_k": q.get("null_k"),
                                     "lo": q["lo"], "lo_natural": nat[s]["lo"], "shift_toward_other": shift_q, "z": zq, "follows": (zq >= Z_FOLLOW) if not np.isnan(zq) else None})
            fr = U.pair_rate(fol, nb, sd)
            nfr = U.pair_rate(null_fol, nb, sd)
            ms = U.pair_bootstrap_stat(sorted({p for p, _ in shifts}), lambda ps, sh=shifts: _mean_by_pairs(sh, ps), nb, sd) if shifts else (float("nan"),) * 3
            nsh = np.array([v for _, v in null_shifts], dtype=float)
            e2[str(a)] = {"follow_rate": fr.as_dict(), "null_follow_rate_loo": nfr.as_dict(), "n_states_missing_natural": n_missing_nat,
                          "mean_shift_toward_other": {"est": ms[0], "lo": ms[1], "hi": ms[2]},
                          "null_band_shift": {"mean": float(nsh.mean()) if len(nsh) else float("nan"), "sd": float(nsh.std(ddof=1)) if len(nsh) > 1 else float("nan"), "n": int(len(nsh))},
                          "z_values": [None if np.isnan(z) else z for z in zs]}
            U.log(f"[g5] E2 {READER_LABELS[rd]} alpha={a}: follows {fr}; null follow (LOO) {U.fmt_count(nfr.k, nfr.n)}; "
                  f"mean shift toward other {ms[0]:+.2f} [{ms[1]:+.2f}, {ms[2]:+.2f}]; null band {e2[str(a)]['null_band_shift']['mean']:+.2f} ± {e2[str(a)]['null_band_shift']['sd']:.2f}")
        decision = decide(e2, valid_doses, summary["manipulation_failed"])
        U.log(f"[g5] DECISION {READER_LABELS[rd]}: {decision['verdict']} — {decision['reason']}")
        summary["readers"][rd] = {"E1_natural_separation": e1, "E2_follow_by_alpha": e2, "n_unscorable_rows": len(unscorable),
                                  "unscorable_states": sorted({r["state_item_id"] for r in unscorable}), "decision": decision}

    U.write_csv(out / "g5.csv", csv_rows)
    U.write_json(out / "summary.json", summary)
    if not args.no_fig:
        make_figure(out / "fig_main.png", summary, frozen)
    U.log(f"[g5] wrote {out}")
    return summary


def _mean_by_pairs(shifts: List[Tuple[str, float]], ps) -> float:
    cnt = Counter(ps)
    vals = [v for p, v in shifts for _ in range(cnt.get(p, 0))]
    return float(np.mean(vals)) if vals else float("nan")


def decide(e2: Dict[str, dict], valid_doses: List[float], failed: bool) -> dict:
    if failed or not valid_doses:
        return {"verdict": "manipulation_failed", "reason": "no dose reached E3 >= 0.75 above the null flip rate (or K4); nothing concluded about the reader"}
    d_min, d_max = str(min(valid_doses)), str(max(valid_doses))
    if d_min not in e2 or d_max not in e2:
        return {"verdict": "undetermined", "reason": f"no LO rows at valid dose(s) {d_min}/{d_max}"}
    f_min, nb_min = e2[d_min]["follow_rate"]["p"], e2[d_min]["null_follow_rate_loo"]["p"]
    f_max = e2[d_max]["follow_rate"]["p"]
    if f_min >= FOLLOW_HI and (np.isnan(nb_min) or nb_min < NULL_BAND_MAX):
        return {"verdict": "follows", "reason": f"E2={f_min:.2f} >= {FOLLOW_HI} at smallest valid dose {d_min} with null follow rate {nb_min:.2f} < {NULL_BAND_MAX}"}
    if f_max <= FOLLOW_LO:
        return {"verdict": "insensitive", "reason": f"E2={f_max:.2f} <= {FOLLOW_LO} at largest valid dose {d_max}"}
    return {"verdict": "mixed", "reason": f"E2={f_min:.2f} at dose {d_min} (null {nb_min:.2f}), E2={f_max:.2f} at dose {d_max}"}


def make_figure(path: Path, summary: dict, frozen: bool) -> None:
    plt = U.mpl()
    readers = [r for r in READERS if r in summary["readers"]]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for j, rd in enumerate(readers):
        ax = axes[0, j]
        e2 = summary["readers"][rd]["E2_follow_by_alpha"]
        al = sorted(float(a) for a in e2)
        if al:
            nb_m = np.array([e2[str(a)]["null_band_shift"]["mean"] for a in al]); nb_s = np.array([e2[str(a)]["null_band_shift"]["sd"] for a in al])
            ax.fill_between(al, nb_m - 2 * nb_s, nb_m + 2 * nb_s, color=U.GRID, alpha=0.9, label="null band (random directions, mean ± 2 sd)", zorder=1)
            ms = [e2[str(a)]["mean_shift_toward_other"] for a in al]
            ax.errorbar(al, [m["est"] for m in ms], yerr=[[m["est"] - m["lo"] for m in ms], [m["hi"] - m["est"] for m in ms]], fmt="o-", color=U.METHOD_COLORS[rd],
                        lw=2, ms=7, capsize=3, label="planted direction (mean over states, 95% pair-bootstrap CI)", zorder=4)
            for a in al:
                fr = e2[str(a)]["follow_rate"]
                ax.annotate(f"follows {fr['k']}/{fr['n']}", (a, ms[al.index(a)]["est"]), textcoords="offset points", xytext=(0, -14), fontsize=7.5, ha="center", va="top", color=U.INK2)
        ax.axhline(0, color=U.INK2, lw=0.8)
        ax.set_xlabel("dose α (units of ‖h_B − h_A‖)")
        ax.set_ylabel("LO shift toward the planted candidate (nats)")
        ax.set_xticks(al or [0.5, 1.0, 1.5])
        ax.grid(axis="y", color=U.GRID, lw=0.8); ax.set_axisbelow(True)
        dec = summary["readers"][rd]["decision"]["verdict"]
        ax.set_title(f"{READER_LABELS[rd]} — E2 follow; decision: {dec}")
        if j == 0:
            ax.legend(fontsize=7.5, loc="best")
    for j in range(len(readers), 3):
        axes[0, j].axis("off")
    # bottom-left: E3 flip rates
    ax = axes[1, 0]
    flip = summary["E3_flip_rate_by_alpha"]
    al = sorted(float(a) for a in flip)
    for i, a in enumerate(al):
        U.bar_ci(ax, i - 0.2, U.Rate(**{k: v for k, v in flip[str(a)]["planted"].items() if k != "ci"}), U.METHOD_COLORS["target"], width=0.38)
        if flip[str(a)]["null"]:
            U.bar_ci(ax, i + 0.2, U.Rate(**{k: v for k, v in flip[str(a)]["null"].items() if k != "ci"}), U.METHOD_COLORS["target"], width=0.38, hollow=True)
    ax.axhline(FLIP_VALID, color=U.INK2, lw=0.8, ls=":")
    ax.set_xticks(range(len(al))); ax.set_xticklabels([f"α={a}" for a in al])
    U.style_ax(ax, "flip rate (% of states, other candidate)", (0, 1.15))
    ax.set_title("E3 behavioural flip rate\nplanted (filled) vs null directions (hollow); dotted = 0.75 validity")
    # bottom-middle: E2 follow rate per reader per dose
    ax = axes[1, 1]
    for j, rd in enumerate(readers):
        e2 = summary["readers"][rd]["E2_follow_by_alpha"]
        for i, a in enumerate(al):
            if str(a) in e2:
                U.bar_ci(ax, i + (j - 1) * 0.27, U.Rate(**{k: v for k, v in e2[str(a)]["follow_rate"].items() if k != "ci"}), U.METHOD_COLORS[rd], width=0.25)
    ax.axhline(FOLLOW_HI, color=U.INK2, lw=0.8, ls=":"); ax.axhline(FOLLOW_LO, color=U.INK2, lw=0.8, ls=":")
    ax.set_xticks(range(len(al))); ax.set_xticklabels([f"α={a}" for a in al])
    U.style_ax(ax, "follow rate (% of edited states with z ≥ 3)", (0, 1.15))
    ax.set_title("E2 follow rate per reader and dose\n(dotted: 0.25 / 0.75 decision lines)")
    # bottom-right: E1 natural separation
    ax = axes[1, 2]
    for j, rd in enumerate(readers):
        e1 = summary["readers"][rd]["E1_natural_separation"]
        w = e1["win_rate"]
        U.bar_ci(ax, j - 0.2, U.Rate(w["k"], w["n"], w["p"], w["lo"], w["hi"], w["n"]), U.METHOD_COLORS[rd], width=0.38)
        a_ = e1["auroc"]
        if not np.isnan(a_["est"]):
            ax.errorbar(j + 0.2, a_["est"], yerr=[[a_["est"] - a_["lo"]], [a_["hi"] - a_["est"]]], fmt="D", color=U.METHOD_COLORS[rd], capsize=3, ms=7, zorder=5)
            ax.text(j + 0.2, a_["hi"] + 0.03, f"AUROC\n{a_['est']:.2f}", ha="center", va="bottom", fontsize=7.5, color=U.INK2)
    ax.axhline(0.5, color=U.INK2, lw=0.8, ls=":")
    ax.set_xticks(range(len(readers))); ax.set_xticklabels([READER_LABELS[r] for r in readers])
    U.style_ax(ax, "win rate (% of pairs, bar) / AUROC (diamond)", (0, 1.2))
    ax.set_title("E1 natural separation\nof the two states of a pair")
    from matplotlib.patches import Patch

    fig.legend(handles=[Patch(fc=U.METHOD_COLORS[r], label=READER_LABELS[r]) for r in readers], loc="lower center", ncol=3, fontsize=8.5, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + f"G5 planted binding swap — {summary['n_states']} states / {summary['n_pairs']} pairs; "
                 f"manipulation_failed={summary['manipulation_failed']}; bars = 95% pair-bootstrap CI; k/n printed", y=1.0)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
