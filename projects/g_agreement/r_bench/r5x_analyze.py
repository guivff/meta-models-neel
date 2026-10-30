"""R5X analysis (BRIEF_R "WS4 / R5X", pre-registered 2026-10-19 17:03Z, S2 amended 17:17Z; WS3 reads it as written in its
dated bullet of 2026-10-19 ~18:1xZ, before any R5X row existed). Reads WS4's rows under ``cache/g_agreement/r/r5x/``
(steer.jsonl, readers.jsonl — the R5 schema) and writes, per stratum and never pooled:

  results/g_agreement/r/r5x_dose.csv      per (stratum, fact, direction, α): model flip rate / shift, the forward gate
                                          (collapse share, ‖h+δ‖/‖h‖ if logged), each reader's follow / cross rate
  results/g_agreement/r/r5x_facts.csv     per fact: α*₅₀, α*₇₅ (d_probe escalation), first NOT INTERPRETABLE dose, status
  results/g_agreement/r/r5x_verdicts.csv  per (fact, reader): REPORT-FLIPPABLE / READER-BLIND at α*₇₅ (§4.5 rules unchanged)
  results/g_agreement/r/r5x.md            the two strata's tables

    python -m projects.g_agreement.r_bench.r5x_analyze            # prints "waiting" and exits 0 while no rows exist

Readings (each a ``# RULE:`` below; BRIEF_R WS3 bullet):
- flip: §4.5's "greedy answer flips" = the sign of the model's answer LO leaves the label's side, exactly as ``analyze.r5_analyze``.
- α*₇₅ / α*₅₀: the smallest α in {4, 8, 16, 32} at which d_probe flips ≥ 75% / ≥ 50% of the fact's items, climbing in
  ascending order and stopping at the first NOT INTERPRETABLE dose (a flip at or beyond that dose does not count).
- forward gate: an item fails at a dose when BOTH lp_pos and lp_neg are > 10 nats below min(lp_pos, lp_neg) of its natural
  row; the ‖h+δ‖/‖h‖ check has no threshold in the pre-registration, so it is reported (median, max) and never trips the
  gate. A dose is NOT INTERPRETABLE for a fact when > 25% of its items fail, counted over every direction at that dose.
- verdicts at α*₇₅ only: READER-BLIND = d_probe's follow < 0.5 of the natural separation; REPORT-FLIPPABLE = under the
  reader's own direction (class-mean proxy where it has none, as R5) the reader crosses on ≥ 75% AND the model's shift
  is < 25% of d_probe's at α*₇₅; if the reader crosses on < 75% there, REPORT-FLIPPABLE is undefined (readers are scored
  at the natural condition and the operating dose only — budget deviation (2)). Random directions (d_rand*, K = 5 at α*₇₅) are
  reported as the band beside each verdict, as R5 did; they gate nothing.
- natural rows: S2 from R5X's own natural rows, S1 from R5's (WS4 7398cf8; addendum below the WS3 bullet), never mixed.
- ‖h+δ‖/‖h‖: computed offline from the block-38 chat state cache (``add_norm_ratio``), reported per dose, never gates.
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from projects.g_agreement.r_bench import analyze as A

ALPHAS = (4.0, 8.0, 16.0, 32.0)
FLIP75, FLIP50, GATE_SHARE, COLLAPSE_NATS = 0.75, 0.50, 0.25, 10.0
NORM_COLS = ("norm_ratio", "edit_norm_ratio", "h_norm_ratio")
NATURAL_SOURCE: dict[str, dict] = {}


def strata(P: A.Paths) -> dict[str, str]:
    out = {}
    for fn, tag in (("r5_selection.json", "S1"), ("r5x_selection.json", "S2")):
        f = P.results / fn
        if f.exists():
            for ds in json.loads(f.read_text())["datasets"]:
                out.setdefault(ds, tag)  # strata are disjoint by rule; S1 wins if a file ever disagreed
    return out


def _natural(st: pd.DataFrame, st5: pd.DataFrame, strat: dict[str, str] | None = None) -> pd.DataFrame:
    """Natural (α = 0) rows per item. # RULE (WS3 addendum 2026-10-19, before any R5X row, at WS4's suggestion 7398cf8):
    S2 facts use R5X's own natural rows, S1 facts R5's (identical construction), never mixed within a stratum; the other
    source is used only for an item the preferred one lacks, and the count is reported in ``NATURAL_SOURCE``."""
    strat = strat or {}
    def nat_of(df):
        return df[df.direction == "natural"].drop_duplicates(["dataset", "item_id"], keep="last").set_index(["dataset", "item_id"]) \
            if len(df) else pd.DataFrame()
    x, r5 = nat_of(st), nat_of(st5)
    parts: list[pd.DataFrame] = []
    NATURAL_SOURCE.clear()
    for ds in sorted(set(st.dataset)):
        first, second = (r5, x) if strat.get(ds) == "S1" else (x, r5)
        a = first.loc[[ds]] if len(first) and ds in first.index.get_level_values(0) else pd.DataFrame()
        b = second.loc[[ds]] if len(second) and ds in second.index.get_level_values(0) else pd.DataFrame()
        if len(a) and len(b):
            b = b[~b.index.isin(a.index)]
        NATURAL_SOURCE[ds] = {"preferred": "R5" if strat.get(ds) == "S1" else "R5X", "n_preferred": len(a), "n_fallback": len(b)}
        parts += [a, b]
    parts = [q for q in parts if len(q)]
    return pd.concat(parts) if parts else pd.DataFrame()


def add_norm_ratio(P: A.Paths, st: pd.DataFrame) -> pd.DataFrame:
    """‖h + sign·α·scale·d‖ / ‖h‖ per row, offline (WS4 7398cf8: steer.py does not log it). # RULE: h = the item's cached
    block-38 chat state (the state cache holds the last token; the edit covers every text position, so this is the ratio
    at that position); d = the fact's unit direction from cache/…/r5x/directions/<ds>.npz, else r5/directions. A
    diagnostic only: it never trips the gate (WS4's clarification 7398cf8)."""
    if any(c in st.columns for c in NORM_COLS):
        return st
    st = st.copy()
    st["norm_ratio"] = np.where(st.direction == "natural", 1.0, np.nan)
    for ds, g in st[st.direction != "natural"].groupby("dataset"):
        f = next((d / f"{ds}.npz" for d in (P.cache / "r5x" / "directions", P.cache / "r5" / "directions") if (d / f"{ds}.npz").exists()), None)
        sd = P.cache / "states" / ds
        if f is None or not (sd / "index.json").exists():
            continue
        z = np.load(f)
        X, idx = A.load_states(P, ds, A.PRIMARY_RENDER, A.L_EDIT)
        pos = {iid: i for i, iid in enumerate(idx)}
        for dname, gd in g.groupby("direction"):
            if dname not in z.files:
                continue
            d = z[dname].astype(np.float64)
            d = d / (np.linalg.norm(d) + 1e-12)
            ok = gd.item_id.map(pos).notna()
            gd = gd[ok]
            h = X[gd.item_id.map(pos).astype(int).values].astype(np.float64)
            delta = (gd["sign"] * gd["alpha"] * gd["scale"]).values[:, None] * d[None, :]
            st.loc[gd.index, "norm_ratio"] = np.linalg.norm(h + delta, axis=1) / np.linalg.norm(h, axis=1)
    return st


def dose_table(st: pd.DataFrame, rr: pd.DataFrame, nat: pd.DataFrame, items: pd.DataFrame, strat: dict[str, str]) -> pd.DataFrame:
    sided_of = dict(zip(items["dataset"], items["sided"]))
    if len(rr):
        if "unscorable" in rr.columns:
            rr = rr[rr["unscorable"] != True].copy()  # noqa: E712
        rr = rr.assign(score=A.primary_score(rr, sided_of))
    norm_col = next((c for c in NORM_COLS if c in st.columns), None)
    out = []
    for ds, g in st[st.direction != "natural"].groupby("dataset"):
        nd = nat.loc[ds] if ds in nat.index.get_level_values(0) else pd.DataFrame()
        if nd.empty:
            continue
        lab = nd["label"]
        side = np.where(lab == 1, 1, -1)
        rg = rr[rr.dataset == ds] if len(rr) else rr
        nat_scores = {rd: x[x.direction == "natural"].set_index("item_id")["score"] for rd, x in rg.groupby("reader")} if len(rg) else {}
        for (dname, alpha), ge in g.groupby(["direction", "alpha"]):
            ge = ge.drop_duplicates("item_id", keep="last").set_index("item_id")
            ge = ge[ge.index.isin(nd.index)]
            if ge.empty:
                continue
            n0 = nd.loc[ge.index]
            sgn = ge["sign"]
            on_side = np.sign(n0["lo"]) == pd.Series(side, index=nd.index).loc[ge.index]
            flipped = (np.sign(ge["lo"]) != np.sign(n0["lo"])) & on_side  # RULE: as analyze.r5_analyze
            floor = np.minimum(n0["lp_pos"], n0["lp_neg"]) - COLLAPSE_NATS
            collapsed = (ge["lp_pos"] < floor) & (ge["lp_neg"] < floor)
            row = {"stratum": strat.get(ds, "?"), "dataset": ds, "direction": dname, "alpha": float(alpha), "n": len(ge),
                   "model_shift": float(((ge["lo"] - n0["lo"]) * sgn).mean()), "model_flip_rate": float(flipped.mean()),
                   "n_collapsed": int(collapsed.sum()), "collapse_share": float(collapsed.mean())}
            if norm_col:
                row["norm_ratio_median"], row["norm_ratio_max"] = float(ge[norm_col].median()), float(ge[norm_col].max())
            for rd, nr in nat_scores.items():
                sep = float(nr[lab.reindex(nr.index) == 1].mean() - nr[lab.reindex(nr.index) == 0].mean())
                x = rg[(rg.reader == rd) & (rg.direction == dname) & (rg.alpha == alpha)].drop_duplicates("item_id", keep="last")
                ed = x.set_index("item_id")["score"]
                common = ed.index.intersection(nr.index).intersection(sgn.index)
                if len(common) == 0 or not np.isfinite(sep) or abs(sep) < 1e-9:
                    continue
                med = np.nanmedian(nr)
                row[f"{rd}_follow"] = float((((ed.loc[common] - nr.loc[common]) * sgn.loc[common]) / sep).mean())
                row[f"{rd}_cross_rate"] = float((np.sign(ed.loc[common] - med) != np.sign(nr.loc[common] - med)).mean())
                row[f"{rd}_natural_sep"] = sep
            out.append(row)
    return pd.DataFrame(out)


def fact_table(dose: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (s_, ds), g in dose.groupby(["stratum", "dataset"]):
        gate = g.groupby("alpha").agg(n=("n", "sum"), n_collapsed=("n_collapsed", "sum"))
        gate["share"] = gate.n_collapsed / gate.n
        ni = [a for a in sorted(gate.index) if gate.loc[a, "share"] > GATE_SHARE]
        first_ni = ni[0] if ni else np.nan
        pr = g[g.direction.str.startswith("d_probe")].groupby("alpha").model_flip_rate.mean().sort_index()
        a50 = a75 = np.nan
        best = (np.nan, np.nan)
        for a, fr in pr.items():
            if np.isfinite(first_ni) and a >= first_ni:  # RULE: the escalation stops at the first NOT INTERPRETABLE dose
                break
            if not np.isfinite(best[1]) or fr > best[1]:
                best = (a, fr)
            if np.isnan(a50) and fr >= FLIP50:
                a50 = a
            if fr >= FLIP75:
                a75 = a
                break
        status = ("OPERATING DOSE" if np.isfinite(a75) else
                  "NOT INTERPRETABLE" if np.isfinite(first_ni) else
                  "STILL UNDEFINED" if len(pr) and max(pr.index) >= max(ALPHAS) else "INCOMPLETE")
        out.append({"stratum": s_, "dataset": ds, "alpha_star_50": a50, "alpha_star_75": a75, "first_not_interpretable": first_ni,
                    "best_alpha": best[0], "best_flip_rate": best[1], "status": status,
                    "doses_run": ",".join(f"{a:g}" for a in pr.index),
                    "norm_ratios": (",".join(f"{a:g}:{r_.norm_ratio_median:.2f} ({r_.norm_ratio_max:.2f})" for a, r_ in
                                             g[g.direction.str.startswith("d_probe")].groupby("alpha")[["norm_ratio_median", "norm_ratio_max"]].mean().iterrows())
                                    if "norm_ratio_median" in g else "—"),
                    "gate_shares": ",".join(f"{a:g}:{gate.loc[a, 'share']:.2f}" for a in gate.index)})
    return pd.DataFrame(out)


def verdict_table(dose: pd.DataFrame, facts: pd.DataFrame) -> pd.DataFrame:
    readers = sorted({c[: -len("_follow")] for c in dose.columns if c.endswith("_follow")})
    out = []
    for f in facts.itertuples():
        g = dose[(dose.dataset == f.dataset) & (dose.alpha == f.alpha_star_75)] if np.isfinite(f.alpha_star_75) else dose.iloc[0:0]
        pr = g[g.direction.str.startswith("d_probe")]
        rnd = g[g.direction.str.startswith("d_rand")]
        for rd in readers:
            row = {"stratum": f.stratum, "dataset": f.dataset, "reader": rd, "alpha_star_75": f.alpha_star_75, "fact_status": f.status,
                   "report_flippable": None, "reader_blind": None}
            if not pr.empty and pd.notna(pr.iloc[0].get(f"{rd}_follow")):
                row["probe_follow"] = float(pr[f"{rd}_follow"].mean())
                row["reader_blind"] = bool(row["probe_follow"] < 0.5)
            own = g[g.direction.str.startswith(f"d_{rd}_")]
            if own.empty:
                own = g[g.direction.str.startswith("d_cm")]  # class-mean proxy for readers without a gradient direction (R5)
            if not own.empty and not pr.empty and pd.notna(own.iloc[0].get(f"{rd}_cross_rate")):
                o = own.iloc[0]
                row["own_direction"], row["own_cross_rate"], row["own_model_shift"] = o.direction, float(o[f"{rd}_cross_rate"]), float(o.model_shift)
                row["probe_model_shift"] = float(pr.model_shift.mean())
                if o[f"{rd}_cross_rate"] >= FLIP75:  # RULE: < 75% crossing at α*₇₅ → undefined (no other dose is scored)
                    row["report_flippable"] = bool(o.model_shift < 0.25 * row["probe_model_shift"])
            if not rnd.empty and f"{rd}_follow" in rnd:
                row["random_follow_band"] = [float(rnd[f"{rd}_follow"].min()), float(rnd[f"{rd}_follow"].max())]
                row["random_flip_band"] = [float(rnd.model_flip_rate.min()), float(rnd.model_flip_rate.max())]
            out.append(row)
    return pd.DataFrame(out)


def dose_summary(dose: pd.DataFrame) -> pd.DataFrame:
    """Per stratum × α as each dose segment lands (WS4 runs α = 4, 8, 16, 32 with a pull between each): d_probe flip rate
    over facts (median, range), facts at ≥ 50% / ≥ 75%, and facts whose forward gate trips at that dose. Descriptive."""
    rows = []
    for (s_, a), g in dose.groupby(["stratum", "alpha"]):
        pr = g[g.direction.str.startswith("d_probe")].groupby("dataset").model_flip_rate.mean()
        gate = g.groupby("dataset").apply(lambda x: x.n_collapsed.sum() / max(x.n.sum(), 1))
        rows.append({"stratum": s_, "alpha": a, "facts": int(g.dataset.nunique()), "probe_flip_median": float(pr.median()) if len(pr) else np.nan,
                     "probe_flip_min": float(pr.min()) if len(pr) else np.nan, "probe_flip_max": float(pr.max()) if len(pr) else np.nan,
                     "facts_ge_50": int((pr >= FLIP50).sum()), "facts_ge_75": int((pr >= FLIP75).sum()),
                     "facts_gate_tripped": int((gate > GATE_SHARE).sum()),
                     "norm_ratio_median": float(g.norm_ratio_median.median()) if "norm_ratio_median" in g else np.nan})
    return pd.DataFrame(rows)


def report(facts: pd.DataFrame, verd: pd.DataFrame, ds_sum: pd.DataFrame = pd.DataFrame()) -> list[str]:
    L = ["# R5X — dose extension (WS4 rows, WS3 analysis; strata never pooled)", ""]
    if len(ds_sum):
        L += ["## Per dose, as segments land (d_probe; descriptive)", "",
              "| stratum | α | facts | flip median [min, max] | facts ≥ 50% | facts ≥ 75% | gate tripped | ‖h+δ‖/‖h‖ median |", "|---|---|---|---|---|---|---|---|"]
        for r in ds_sum.sort_values(["stratum", "alpha"]).itertuples():
            L.append(f"| {r.stratum} | {r.alpha:g} | {r.facts} | {r.probe_flip_median:.3f} [{r.probe_flip_min:.3f}, {r.probe_flip_max:.3f}] | "
                     f"{r.facts_ge_50} | {r.facts_ge_75} | {r.facts_gate_tripped} | {r.norm_ratio_median:.2f} |")
        L.append("")
    for s_ in ("S1", "S2"):
        f = facts[facts.stratum == s_]
        if f.empty:
            continue
        L += [f"## {s_} ({'30 confident facts' if s_ == 'S1' else 'small-margin stratum'}): {len(f)} facts",
              "status counts: " + ", ".join(f"{k} {v}" for k, v in f.status.value_counts().items()), "",
              "| fact | α*₅₀ | α*₇₅ | first NOT INTERPRETABLE | best (α, flip) | status | collapse share by α | ‖h+δ‖/‖h‖ median (max) by α |",
              "|---|---|---|---|---|---|---|---|"]
        for r in f.itertuples():
            L.append(f"| {r.dataset} | {r.alpha_star_50:g} | {r.alpha_star_75:g} | {r.first_not_interpretable:g} | "
                     f"({r.best_alpha:g}, {r.best_flip_rate:.2f}) | {r.status} | {r.gate_shares} | {r.norm_ratios} |")
        v = verd[verd.stratum == s_] if len(verd) else verd
        if len(v):
            L += ["", "| reader | facts at α*₇₅ | REPORT-FLIPPABLE yes / no / undefined | READER-BLIND yes / no / undefined |", "|---|---|---|---|"]
            for rd, gv in v.groupby("reader"):
                cnt = lambda c: f"{(gv[c] == True).sum()} / {(gv[c] == False).sum()} / {gv[c].isna().sum()}"  # noqa: E712,E731
                L.append(f"| {rd} | {gv.alpha_star_75.notna().sum()} | {cnt('report_flippable')} | {cnt('reader_blind')} |")
        L.append("")
    return L


def main(argv: list[str] | None = None) -> int:
    P = A.Paths()
    st = A.read_jsonl(P.cache / "r5x" / "steer.jsonl")
    if st.empty:
        print(f"[r5x] waiting: no rows at {P.cache / 'r5x' / 'steer.jsonl'}")
        return 0
    items, _ = A.load_bank(P)
    rr = A.read_jsonl(P.cache / "r5x" / "readers.jsonl")
    strat = strata(P)
    nat = _natural(st, A.read_jsonl(P.cache / "r5" / "steer.jsonl"), strat)
    st = add_norm_ratio(P, st)
    dose = dose_table(st, rr, nat, items, strat)
    facts = fact_table(dose)
    verd = verdict_table(dose, facts)
    ds_sum = dose_summary(dose)
    ds_sum.to_csv(P.results / "r5x_doses.csv", index=False)
    dose.to_csv(P.results / "r5x_dose.csv", index=False)
    facts.to_csv(P.results / "r5x_facts.csv", index=False)
    verd.to_csv(P.results / "r5x_verdicts.csv", index=False)
    from projects.g_agreement.r_bench import ws3_tier as WT

    (P.results / "r5x.md").write_text(WT.finalize_md("\n".join(report(facts, verd, ds_sum))) + "\n")
    (P.results / "r5x_natural_source.json").write_text(json.dumps(NATURAL_SOURCE, indent=1))
    print("\n".join(report(facts, verd, ds_sum)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
