"""X2 — do the readers follow a fact that was planted causally? (BRIEF_X endpoints E4–E7, kill K5)

CPU only. Inputs (written by x2_causal/collect.py):
  cache/g_agreement/x/x2_behaviour.jsonl  one row per entry {key, pair_id, family, source, site, alpha, condition natural|planted|null|null_other,
                                          null_k, cand_A (own answer), cand_B (other = planted), parsed, flipped_to_other, coherent, lo_model}
  cache/g_agreement/x/x2_lo.jsonl         one row per (reader, entry) {key = reader|entry key, entry_key, reader, lo_toward_other, unscorable}
Orientation: every quantity is "toward the planted (other) candidate"; shift = lo(entry) − lo(natural entry of the same source state).

E4  flip curve per site × alpha: P(answer = other candidate) with Wilson CI (and pair-bootstrap CI); null flip rate at the null alpha;
    coherence (parsed in the candidates) per (site, alpha), arms < 0.8 flagged.
E5  alpha* per item (pair, source) and site: the smallest ladder alpha whose answer is the other candidate (coherent by construction);
    items with none are "no flip".
E6  per reader × site over items with alpha*: win = P(shift at alpha* > 0) (pair bootstrap); z = (shift − mean_null) / sd_null from the K
    isotropic nulls of that item/site; null win = P(null shift >= the item's planted shift at alpha*) over the K nulls of the same items
    (the paired, rank form of the z test; the raw P(null shift > 0) is reported too but is ~0.5 for any zero-mean null noise and cannot
    serve as a decision statistic). SUB-FLIP dose = the largest ladder alpha
    < alpha* at which the model's own lo_model shift is inside its null band (|z_model| < 2); reader win there.
    SUB-FLIP: win ≥ 0.9 at the sub-flip dose (the reader "already" moves below alpha*: the G5 pattern, checked first because it refines
    TRACKS); TRACKS: win ≥ 0.9 at alpha* and null win ≤ 0.25; INSENSITIVE: win ≤ 0.5 at alpha*; else MIXED. Every flag is reported.
E7  gain ratio: OLS slope of the reader's shift on the model's lo_model shift over all planted entries of the site (pair bootstrap).
K5  at S2: fewer than 16 of 64 pairs with an alpha* ≤ 1 (either source state flips coherently) → underpowered, no classification at S2.
Outputs results/g_agreement/x2/{summary.json, flips.csv, follow.csv, fig_main.png, fig_flips.png}.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402

MODULE = "x2"
READERS = ("olens", "nla", "jlens")
READER_LABELS = {"olens": "Oracle lens", "nla": "NLA", "jlens": "J-lens"}
SITES = ("S1", "S2", "S3")
SITE_LABELS = {"S1": "S1: L38, last token", "S2": "S2: L38, all positions", "S3": "S3: L42, all positions (reference)"}
NAT = "nat"
WIN_HI, NULL_WIN_MAX, WIN_LO = 0.9, 0.25, 0.5
Z_MODEL_INSIDE = 2.0
Z_FOLLOW = 2.0
COHERENCE_MIN = 0.8
K5_MIN_PAIRS, K5_ALPHA = 16, 1.0
PRIMARY_SITE = "S2"
RATIO_EDGES = [0.0, 0.375, 0.625, 0.875, 1.125, 1.375, 1.75, 2.25]


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--behaviour", default=str(ROOT / "cache" / "g_agreement" / "x" / "x2_behaviour.jsonl"))
    ap.add_argument("--lo", default=str(ROOT / "cache" / "g_agreement" / "x" / "x2_lo.jsonl"))
    ap.add_argument("--frozen-config", default=str(U.G_DIR / "manifest" / "frozen_config_x.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


def _f(x) -> float:
    return float("nan") if x is None else float(x)


def wilson_dict(k: int, n: int) -> dict:
    p, lo, hi = U.wilson(k, n)
    return {"k": k, "n": n, "p": p, "lo": lo, "hi": hi, "ci": "wilson"}


def ols_slope(xy: List[Tuple[float, float]]) -> float:
    if len(xy) < 3:
        return float("nan")
    x = np.array([a for a, _ in xy]); y = np.array([b for _, b in xy])
    vx = np.var(x)
    return float("nan") if vx == 0 else float(np.cov(x, y, bias=True)[0, 1] / vx)


def band(vals: List[float]) -> Tuple[float, float]:
    v = np.array([x for x in vals if x is not None and not np.isnan(x)], dtype=float)
    if len(v) < 3:
        return float("nan"), float("nan")
    return float(v.mean()), float(v.std(ddof=1))


def zscore(x: float, mean: float, sd: float) -> float:
    return float("nan") if np.isnan(mean) or np.isnan(sd) or sd <= 0 else float((x - mean) / sd)


def run(args: argparse.Namespace) -> dict:
    frozen, _ = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if frozen else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    beh = U.load_jsonl(args.behaviour)
    lo_rows = U.load_jsonl(args.lo) if Path(args.lo).exists() else []
    nb, sd = args.n_boot, args.seed
    if not beh:
        raise U.AnalysisError(f"no behaviour rows in {args.behaviour}")
    by_key = {r["key"]: r for r in beh}
    if len(by_key) != len(beh):
        raise U.AnalysisError("duplicate behaviour keys")
    items = sorted({(r["pair_id"], r["source"]) for r in beh})
    pair_of = {it: it[0] for it in items}
    fam_of = {(r["pair_id"], r["source"]): r["family"] for r in beh}
    nat = {(r["pair_id"], r["source"]): r for r in beh if r["condition"] == "natural"}
    lo = defaultdict(dict)  # reader -> entry_key -> lo_toward_other (None if unscorable)
    for r in lo_rows:
        lo[r["reader"]][r["entry_key"]] = None if r.get("unscorable") else r.get("lo_toward_other")
    readers = [rd for rd in READERS if rd in lo]
    sites = [s for s in SITES if any(r["site"] == s for r in beh)]
    U.log(f"[x2] frozen={frozen} {len(beh)} behaviour rows, {len(items)} items / {len({p for p, _ in items})} pairs, sites {sites}, readers {readers}; out={out}")
    summary: dict = {"module": MODULE, "frozen": frozen, "n_items": len(items), "n_pairs": len({p for p, _ in items}), "n_boot": nb, "seed": sd,
                     "readers": readers, "sites": sites, "orientation": "positive = toward the planted (other) candidate; shift = lo(entry) - lo(natural)",
                     "n_items_without_natural": sum(1 for it in items if it not in nat), "by_site": {}}
    flips_csv: List[dict] = []
    follow_csv: List[dict] = []
    fig_data: dict = {}

    # ---------------- per site ----------------
    grp: Dict[Tuple[str, Tuple[str, str], str], List[dict]] = defaultdict(list)  # (site, item, condition) -> rows
    for r in beh:
        if r["site"] != NAT:
            grp[(r["site"], (r["pair_id"], r["source"]), r["condition"])].append(r)
    for site in sites:
        S: dict = {"label": SITE_LABELS.get(site, site)}
        planted = {it: sorted(grp.get((site, it, "planted"), []), key=lambda r: float(r["alpha"])) for it in items}
        alphas = sorted({float(r["alpha"]) for it in items for r in planted[it]})
        nulls = {it: grp.get((site, it, "null"), []) for it in items}
        nulls_other = {it: grp.get((site, it, "null_other"), []) for it in items}
        # E4 flip curve + coherence
        e4: dict = {}
        for a in alphas:
            rows = [r for it in items for r in planted[it] if float(r["alpha"]) == a]
            k = sum(bool(r["flipped_to_other"]) for r in rows)
            coh = sum(bool(r.get("coherent")) for r in rows)
            e4[str(a)] = {"flip": wilson_dict(k, len(rows)), "flip_pair_boot": U.pair_rate([(r["pair_id"], bool(r["flipped_to_other"])) for r in rows], nb, sd).as_dict(),
                          "coherence": wilson_dict(coh, len(rows)), "coherence_flag": (coh / len(rows) < COHERENCE_MIN) if rows else None,
                          "kept_original": wilson_dict(sum(bool(r.get("kept_original")) for r in rows), len(rows))}
            flips_csv.append({"site": site, "alpha": a, "condition": "planted", "k": k, "n": len(rows), "p": e4[str(a)]["flip"]["p"], "lo": e4[str(a)]["flip"]["lo"],
                              "hi": e4[str(a)]["flip"]["hi"], "coherence": coh / len(rows) if rows else float("nan")})
        for cond, nd in (("null", nulls), ("null_other", nulls_other)):
            rows = [r for it in items for r in nd[it]]
            if not rows:
                continue
            a = sorted({float(r["alpha"]) for r in rows})
            k = sum(bool(r["flipped_to_other"]) for r in rows)
            coh = sum(bool(r.get("coherent")) for r in rows)
            e4[f"{cond}@{a[0] if len(a) == 1 else a}"] = {"flip": wilson_dict(k, len(rows)), "coherence": wilson_dict(coh, len(rows)), "alpha": a}
            flips_csv.append({"site": site, "alpha": a[0] if len(a) == 1 else str(a), "condition": cond, "k": k, "n": len(rows), "p": k / len(rows),
                              "lo": U.wilson(k, len(rows))[1], "hi": U.wilson(k, len(rows))[2], "coherence": coh / len(rows)})
        S["E4_flip_by_alpha"] = e4
        for a in alphas:
            f = e4[str(a)]
            U.log(f"[x2] {site} E4 alpha={a}: flip {U.fmt_count(f['flip']['k'], f['flip']['n'])} [{100 * f['flip']['lo']:.0f}, {100 * f['flip']['hi']:.0f}]; "
                  f"coherence {U.fmt_count(f['coherence']['k'], f['coherence']['n'])}{' FLAG < 0.8' if f['coherence_flag'] else ''}")
        for kk, v in e4.items():
            if kk.startswith("null"):
                U.log(f"[x2] {site} E4 {kk}: flip {U.fmt_count(v['flip']['k'], v['flip']['n'])}")
        # E5 alpha*
        astar: Dict[Tuple[str, str], Optional[float]] = {}
        for it in items:
            fl = [float(r["alpha"]) for r in planted[it] if r["flipped_to_other"] and r.get("coherent", True)]
            astar[it] = min(fl) if fl else None
        with_star = [it for it in items if astar[it] is not None]
        S["E5_alpha_star"] = {"n_items": len(items), "n_with_alpha_star": len(with_star), "n_no_flip": len(items) - len(with_star),
                              "median_alpha_star": float(np.median([astar[it] for it in with_star])) if with_star else None,
                              "alpha_star_counts": {str(a): sum(1 for it in with_star if astar[it] == a) for a in alphas},
                              "per_item": {f"{p}|{s}": astar[(p, s)] for p, s in items}}
        U.log(f"[x2] {site} E5: alpha* for {len(with_star)}/{len(items)} items (median {S['E5_alpha_star']['median_alpha_star']}); no flip {len(items) - len(with_star)}")
        # K5 (S2) — pairs with an alpha* <= 1 in at least one source state
        pairs_le1 = sorted({p for (p, s) in with_star if astar[(p, s)] <= K5_ALPHA})
        pairs_both = sorted({p for p in {q for q, _ in items} if all(astar.get((p, s)) is not None and astar[(p, s)] <= K5_ALPHA for s in ("A", "B"))})
        S["K5"] = {"pairs_with_alpha_star_le_1_any_source": len(pairs_le1), "pairs_with_alpha_star_le_1_both_sources": len(pairs_both),
                   "n_pairs": len({p for p, _ in items}), "min_pairs": K5_MIN_PAIRS, "killed": (site == PRIMARY_SITE and len(pairs_le1) < K5_MIN_PAIRS),
                   "definition": "a pair counts if either source state has alpha* <= 1 with a coherent answer"}
        if site == PRIMARY_SITE:
            U.log(f"[x2] K5 at {site}: {len(pairs_le1)} pairs with alpha* <= 1 (both sources: {len(pairs_both)}); killed={S['K5']['killed']}")
        # model null band per item (lo_model shifts of the isotropic nulls) and model planted shifts
        model_band, model_shift = {}, {}
        for it in items:
            if it not in nat or nat[it].get("lo_model") is None:
                continue
            n0 = nat[it]["lo_model"]
            model_band[it] = band([r["lo_model"] - n0 for r in nulls[it] if r.get("lo_model") is not None])
            model_shift[it] = {float(r["alpha"]): r["lo_model"] - n0 for r in planted[it] if r.get("lo_model") is not None}
        S["model_lo"] = {"n_items_scorable": len(model_band), "n_items_unscorable": len(items) - len(model_band),
                         "mean_shift_by_alpha": {str(a): float(np.nanmean([model_shift[it][a] for it in model_shift if a in model_shift[it]] or [np.nan])) for a in alphas},
                         "mean_null_sd": float(np.nanmean([model_band[it][1] for it in model_band] or [np.nan]))}
        # sub-flip dose per item: largest alpha < alpha* with |z_model| < 2
        a_sub: Dict[Tuple[str, str], Optional[float]] = {}
        for it in with_star:
            cands = []
            for a in alphas:
                if a >= astar[it] or it not in model_shift or a not in model_shift[it]:
                    continue
                zm = zscore(model_shift[it][a], *model_band[it])
                if not np.isnan(zm) and abs(zm) < Z_MODEL_INSIDE:
                    cands.append(a)
            a_sub[it] = max(cands) if cands else None
        S["E6_subflip_dose"] = {"n_items_with_subflip_dose": sum(1 for v in a_sub.values() if v is not None), "per_item": {f"{p}|{s}": a_sub.get((p, s)) for p, s in with_star}}
        # E6 / E7 per reader
        S["readers"] = {}
        fig_data[site] = {"model": [], "readers": {}}
        for it in with_star:
            if it in model_shift:
                for a, v in model_shift[it].items():
                    fig_data[site]["model"].append((it[0], a / astar[it], zscore(v, *model_band[it])))
        for rd in readers:
            L = lo[rd]
            shift = {}      # (item, alpha) -> reader shift toward other
            nshift = {}     # item -> list of null shifts
            n_unscorable = 0
            for it in items:
                if it not in nat or L.get(nat[it]["key"]) is None:
                    n_unscorable += 1
                    continue
                l0 = L[nat[it]["key"]]
                for r in planted[it]:
                    if L.get(r["key"]) is not None:
                        shift[(it, float(r["alpha"]))] = L[r["key"]] - l0
                nshift[it] = [L[r["key"]] - l0 for r in nulls[it] if L.get(r["key"]) is not None]
            rbands = {it: band(v) for it, v in nshift.items()}
            win_flags, null_flags, null_pos_flags, zs, follow_flags, sub_flags = [], [], [], [], [], []
            for it in with_star:
                a = astar[it]
                if (it, a) not in shift:
                    continue
                s_ = shift[(it, a)]
                z = zscore(s_, *rbands.get(it, (np.nan, np.nan)))
                win_flags.append((it[0], s_ > 0)); zs.append(z)
                follow_flags.append((it[0], None if np.isnan(z) else (z >= Z_FOLLOW and s_ > 0)))
                null_flags += [(it[0], v >= s_) for v in nshift.get(it, [])]
                null_pos_flags += [(it[0], v > 0) for v in nshift.get(it, [])]
                follow_csv.append({"site": site, "reader": rd, "pair_id": it[0], "source": it[1], "family": fam_of[it], "alpha_star": a, "shift_at_alpha_star": s_,
                                   "null_mean": rbands.get(it, (np.nan, np.nan))[0], "null_sd": rbands.get(it, (np.nan, np.nan))[1], "z": z, "win": s_ > 0,
                                   "model_shift_at_alpha_star": model_shift.get(it, {}).get(a), "model_z": zscore(model_shift.get(it, {}).get(a, np.nan), *model_band.get(it, (np.nan, np.nan))),
                                   "subflip_alpha": a_sub.get(it), "shift_at_subflip": shift.get((it, a_sub[it])) if a_sub.get(it) is not None else None})
                if a_sub.get(it) is not None and (it, a_sub[it]) in shift:
                    sub_flags.append((it[0], shift[(it, a_sub[it])] > 0))
            win = U.pair_rate(win_flags, nb, sd); nwin = U.pair_rate(null_flags, nb, sd); npos = U.pair_rate(null_pos_flags, nb, sd); fz_ = U.pair_rate(follow_flags, nb, sd); subwin = U.pair_rate(sub_flags, nb, sd)
            # E7 gain ratio over all planted entries of the site
            xy = [(it[0], model_shift[it][a], shift[(it, a)]) for (it, a) in shift if it in model_shift and a in model_shift[it]]
            pids = sorted({p for p, _, _ in xy})
            gain = U.pair_bootstrap_stat(pids, lambda ps, xy=xy: _slope_for(ps, xy), nb, sd) if xy else (float("nan"),) * 3
            flags = {"tracks": bool(win.n and win.p >= WIN_HI and (np.isnan(nwin.p) or nwin.p <= NULL_WIN_MAX)),
                     "subflip": bool(subwin.n and subwin.p >= WIN_HI), "insensitive": bool(win.n and win.p <= WIN_LO)}
            if S["K5"]["killed"]:
                verdict, reason = "UNDERPOWERED", f"K5: {S['K5']['pairs_with_alpha_star_le_1_any_source']} < {K5_MIN_PAIRS} pairs with alpha* <= 1 at {site}"
            elif win.n == 0:
                verdict, reason = "UNDETERMINED", "no items with alpha* and a scorable LO"
            elif flags["subflip"]:
                verdict, reason = "SUB-FLIP", f"win {subwin.p:.2f} >= {WIN_HI} at the sub-flip dose ({subwin.n} items); win at alpha* {win.p:.2f}"
            elif flags["tracks"]:
                verdict, reason = "TRACKS", f"win {win.p:.2f} >= {WIN_HI} at alpha*, null win {nwin.p:.2f} <= {NULL_WIN_MAX}"
            elif flags["insensitive"]:
                verdict, reason = "INSENSITIVE", f"win {win.p:.2f} <= {WIN_LO} at alpha*"
            else:
                verdict, reason = "MIXED", f"win {win.p:.2f} at alpha*, null win {nwin.p:.2f}, sub-flip win {subwin.p:.2f} ({subwin.n} items)"
            S["readers"][rd] = {"n_items_unscorable_or_no_natural": n_unscorable, "E6_win_at_alpha_star": win.as_dict(), "E6_null_win": nwin.as_dict(), "E6_null_shift_positive": npos.as_dict(),
                                "null_win_definition": "P(null shift >= planted shift at alpha*) over the K isotropic nulls of items with alpha*",
                                "E6_follow_z_ge_2": fz_.as_dict(), "E6_win_at_subflip_dose": subwin.as_dict(), "z_values": [None if np.isnan(z) else z for z in zs],
                                "mean_z": float(np.nanmean(zs)) if zs and not np.all(np.isnan(zs)) else None,
                                "E7_gain_ratio": {"slope": gain[0], "lo": gain[1], "hi": gain[2], "n_points": len(xy), "n_pairs": len(pids)},
                                "flags": flags, "verdict": verdict, "reason": reason}
            U.log(f"[x2] {site} E6 {READER_LABELS[rd]}: win {win}; null win {U.fmt_count(nwin.k, nwin.n)}; z>=2 {U.fmt_count(fz_.k, fz_.n)}; sub-flip win {U.fmt_count(subwin.k, subwin.n)}; "
                  f"E7 gain {gain[0]:+.2f} [{gain[1]:+.2f}, {gain[2]:+.2f}] -> {verdict}")
            fig_data[site]["readers"][rd] = [(it[0], a / astar[it], zscore(shift[(it, a)], *rbands[it])) for (it, a) in shift if it in with_star and it in rbands]
        summary["by_site"][site] = S

    summary["classification"] = {s: {rd: summary["by_site"][s]["readers"][rd]["verdict"] for rd in readers} for s in sites}
    summary["K5_primary_site"] = summary["by_site"].get(PRIMARY_SITE, {}).get("K5")
    U.write_csv(out / "flips.csv", flips_csv)
    U.write_csv(out / "follow.csv", follow_csv)
    U.write_json(out / "summary.json", summary)
    if not args.no_fig:
        make_fig_main(out / "fig_main.png", summary, fig_data, readers, sites, nb, sd, frozen)
        make_fig_flips(out / "fig_flips.png", summary, sites, frozen)
    U.log(f"[x2] wrote {out}")
    return summary


def _slope_for(ps, xy) -> float:
    cnt: Dict[str, int] = defaultdict(int)
    for p in ps:
        cnt[p] += 1
    pts = [(x, y) for p, x, y in xy for _ in range(cnt.get(p, 0))]
    return ols_slope(pts)


def binned_curve(points: List[Tuple[str, float, float]], nb: int, sd: int) -> Tuple[List[float], List[float], List[float], List[float]]:
    """points (pair_id, ratio, z) -> bin centres, mean z, lo, hi (pair bootstrap of the bin mean)."""
    xs, ms, los, his = [], [], [], []
    for i in range(len(RATIO_EDGES) - 1):
        lo_, hi_ = RATIO_EDGES[i], RATIO_EDGES[i + 1]
        sel = [(p, z) for p, r, z in points if lo_ <= r < hi_ and not np.isnan(z)]
        if len(sel) < 2:
            continue
        pids = sorted({p for p, _ in sel})

        def stat(ps, sel=sel):
            cnt: Dict[str, int] = defaultdict(int)
            for p in ps:
                cnt[p] += 1
            v = [z for p, z in sel for _ in range(cnt.get(p, 0))]
            return float(np.mean(v)) if v else float("nan")

        m, l, h = U.pair_bootstrap_stat(pids, stat, nb, sd)
        xs.append(float(np.mean([r for _, r, _ in points if lo_ <= r < hi_]))); ms.append(m); los.append(l); his.append(h)
    return xs, ms, los, his


def make_fig_main(path: Path, summary: dict, fig_data: dict, readers, sites, nb: int, sd: int, frozen: bool) -> None:
    plt = U.mpl()
    fig = plt.figure(figsize=(13, 7.5))
    gs = fig.add_gridspec(2, 3, width_ratios=[2.1, 1, 1])
    axes = {"S2": fig.add_subplot(gs[:, 0]), "S1": fig.add_subplot(gs[0, 1:]), "S3": fig.add_subplot(gs[1, 1:])}
    for site, ax in axes.items():
        if site not in fig_data:
            ax.axis("off"); continue
        S = summary["by_site"][site]
        xs, ms, los, his = binned_curve(fig_data[site]["model"], nb, sd)
        if xs:
            ax.plot(xs, ms, "o-", color="black", lw=2, ms=5, label="model lo_model (first-token log-odds)", zorder=5)
            ax.fill_between(xs, los, his, color="black", alpha=0.12, zorder=1)
        for rd in readers:
            xs, ms, los, his = binned_curve(fig_data[site]["readers"].get(rd, []), nb, sd)
            if not xs:
                continue
            v = S["readers"][rd]["verdict"]
            ax.plot(xs, ms, "o-", color=U.METHOD_COLORS[rd], lw=1.8, ms=5, label=f"{READER_LABELS[rd]} — {v}", zorder=4)
            ax.fill_between(xs, los, his, color=U.METHOD_COLORS[rd], alpha=0.15, zorder=2)
        ax.axhline(0, color=U.INK2, lw=0.8); ax.axvline(1.0, color=U.INK2, lw=0.8, ls=":")
        ax.axhspan(-2, 2, color=U.GRID, alpha=0.5, zorder=0)
        ax.set_xlim(0, 2.3); ax.set_xlabel("dose α / α* (items with a flipping dose)")
        ax.set_ylabel("standardized LO shift toward the planted candidate\n(z vs the item's null band)" if site == "S2" else "z (LO shift)")
        e5 = S["E5_alpha_star"]
        ax.set_title(f"{S['label']}\nα* for {e5['n_with_alpha_star']}/{e5['n_items']} items (median {e5['median_alpha_star']}); " +
                     (f"K5 killed" if S["K5"]["killed"] else f"{S['K5']['pairs_with_alpha_star_le_1_any_source']} pairs α*≤1"), fontsize=9.5 if site == "S2" else 8.5)
        ax.grid(axis="y", color=U.GRID, lw=0.8); ax.set_axisbelow(True)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=7.5 if site == "S2" else 6.5, loc="upper left")
    fig.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + f"X2 dose-response: reader LO vs the model's own answer log-odds along the planting ladder\n"
                 f"{summary['n_items']} items / {summary['n_pairs']} pairs; bands = 95% pair-bootstrap CI of the bin mean; grey = ±2 sd null band", y=1.02, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def make_fig_flips(path: Path, summary: dict, sites, frozen: bool) -> None:
    plt = U.mpl()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, site in zip(axes, SITES):
        if site not in summary["by_site"]:
            ax.axis("off"); continue
        S = summary["by_site"][site]
        e4 = S["E4_flip_by_alpha"]
        al = sorted(float(a) for a in e4 if not a.startswith("null"))
        f = [e4[str(a)]["flip"] for a in al]
        ax.errorbar(al, [x["p"] for x in f], yerr=[[x["p"] - x["lo"] for x in f], [x["hi"] - x["p"] for x in f]], fmt="o-", color=U.METHOD_COLORS["target"], lw=2, capsize=3, label="planted (Wilson 95%)")
        ax.plot(al, [e4[str(a)]["coherence"]["p"] for a in al], "s:", color=U.INK2, ms=4, label="coherence")
        for kk, v in e4.items():
            if kk.startswith("null"):
                a0 = v["alpha"][0] if isinstance(v["alpha"], list) else v["alpha"]
                ax.errorbar([a0], [v["flip"]["p"]], yerr=[[v["flip"]["p"] - v["flip"]["lo"]], [v["flip"]["hi"] - v["flip"]["p"]]], fmt="D" if "other" in kk else "o",
                            mfc="none", color=U.METHOD_COLORS["target"], capsize=3, label=f"{kk.split('@')[0]} flip", zorder=4)
        for a in al:
            ax.text(a, f[al.index(a)]["hi"] + 0.03, f"{f[al.index(a)]['k']}/{f[al.index(a)]['n']}", ha="center", fontsize=7, color=U.INK2)
        ax.axhline(COHERENCE_MIN, color=U.INK2, lw=0.6, ls="--")
        U.style_ax(ax, "flip rate (% of items answering the other candidate)", (0, 1.15))
        ax.set_xlabel("dose α (units of ‖h_B − h_A‖ per position)"); ax.set_title(f"E4 — {S['label']}"); ax.legend(fontsize=7)
    fig.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + "X2 flip curves per site (hollow = null directions at the null dose; dashed = 0.8 coherence)", y=1.02)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
