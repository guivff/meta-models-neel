"""SWAP-U — written vs used (BRIEF_R, dated WS3 section; EXPLORATORY). CPU only, existing SWAP khop rows.

At layer 24, under the J-lens bridge swap (d_swap, α = 1): do readers report the swapped-in bridge on items where the swap
did NOT flip the model's answer (N) as often as on items where it did (F), and more than under random directions at the
same layer and norm (R)?

  results/g_agreement/r/swap_u.md            per reader: F, N, R rates, contrasts, CIs, verdicts (primary, margin-matched)
  results/g_agreement/r/swap_u.csv
  results/g_agreement/r/swap_u_examples.csv  10 N items drawn with seed 0

    python -m projects.g_agreement.r_bench.swap_u
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import swap_analyze as S

LAYER, N_BOOT, SEED, Q = 24, 2000, 0, 0.10  # N_BOOT is overridable for tests
PRIMARY = ("nla", "olens", "skip_a")
CIRCULAR = ("jlens",)


def groups(sw: pd.DataFrame) -> tuple[list[str], list[str]]:
    """F = answer flipped under d_swap at L24 (natural true → edited distractor); N = natural answer true, not flipped."""
    fl = S.khop_flips(sw)
    a = fl[(fl.arm == "d_swap") & (fl.pair == "answer") & (fl.layer == LAYER)].drop_duplicates("item").set_index("item").flipped
    nat = sw[sw.arm == "natural"].drop_duplicates("item").set_index("item")
    F = sorted(a[a].index)
    N = sorted(i for i in a[~a].index if bool(nat.loc[i, "prefers_answer_true"]))
    return F, N


def switches(rr: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    """Per (reader, item): switch under d_swap and the mean switch over d_rand0..2 (natural bridge LO > 0 → edited < 0)."""
    nat = rr[(rr.arm == "natural") & (rr.pair == "bridge")].drop_duplicates(["reader", "item"], keep="last").set_index(["reader", "item"]).lo
    e = rr[(rr.layer == LAYER) & (rr.pair == "bridge") & rr.item.isin(items) & rr.arm.isin(("d_swap",) + S.RANDOM)].drop_duplicates(
        ["reader", "item", "arm"], keep="last").copy()
    e = e[pd.MultiIndex.from_arrays([e.reader, e.item]).isin(nat.index)]
    e["sw"] = ((nat.loc[list(zip(e.reader, e.item))].values > 0) & (e.lo.values < 0)).astype(float)
    real = e[e.arm == "d_swap"].set_index(["reader", "item"]).sw.rename("real")
    rnd = e[e.arm.isin(S.RANDOM)].groupby(["reader", "item"]).sw.mean().rename("rand")
    return pd.concat([real, rnd], axis=1).reset_index()


def net_shifts(rr: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    """Per (reader, item): d = (LO_nat − LO_d_swap) − mean_k (LO_nat − LO_d_rand_k), bridge pair (§26 primary metric)."""
    nat = rr[(rr.arm == "natural") & (rr.pair == "bridge")].drop_duplicates(["reader", "item"], keep="last").set_index(["reader", "item"]).lo
    e = rr[(rr.layer == LAYER) & (rr.pair == "bridge") & rr.item.isin(items) & rr.arm.isin(("d_swap",) + S.RANDOM)].drop_duplicates(
        ["reader", "item", "arm"], keep="last").copy()
    e = e[pd.MultiIndex.from_arrays([e.reader, e.item]).isin(nat.index)]
    e["shift"] = nat.loc[list(zip(e.reader, e.item))].values - e.lo.values
    real = e[e.arm == "d_swap"].set_index(["reader", "item"])["shift"].rename("shift_real")
    rnd = e[e.arm.isin(S.RANDOM)].groupby(["reader", "item"])["shift"].mean().rename("shift_rand")
    out = pd.concat([real, rnd], axis=1).reset_index()
    out["d"] = out.shift_real - out.shift_rand
    return out


def _means(f: pd.DataFrame, n: pd.DataFrame, strata: bool) -> tuple[float, float]:
    """(N̄, F̄); with strata, F̄ is standardised to N's tercile distribution (terciles lacking F or N dropped)."""
    nbar = float(n.d.mean()) if len(n) else np.nan
    if not strata:
        return nbar, (float(f.d.mean()) if len(f) else np.nan)
    w, fm = [], []
    for t in sorted(set(n.tercile)):
        ft, nt = f[f.tercile == t], n[n.tercile == t]
        if len(ft) and len(nt):
            w.append(len(nt)); fm.append(ft.d.mean())
    if not w:
        return nbar, np.nan
    keep = n[n.tercile.isin([t for t in sorted(set(n.tercile)) if len(f[f.tercile == t])])]
    return float(keep.d.mean()), float(np.average(fm, weights=w))


def stats(df: pd.DataFrame, cluster: dict[str, str], strata: bool = False) -> dict:
    """§26: N̄, F̄, ρ = N̄ / F̄, jointly bootstrapped (item level within group / within tercile; fact-clustered), 2,000 draws."""
    F, N = df[df.group == "F"], df[df.group == "N"]
    nbar, fbar = _means(F, N, strata)
    est = {"N_minus_R": nbar, "F_minus_R": fbar, "rho": (nbar / fbar) if fbar and fbar > 0 else np.nan,
           "shift_real_N": float(N.shift_real.mean()), "shift_rand_N": float(N.shift_rand.mean()),
           "shift_real_F": float(F.shift_real.mean()), "shift_rand_F": float(F.shift_rand.mean())}
    by = {c: g for c, g in df.groupby(df.item.map(cluster))}
    cl = sorted(by)
    boot = {}
    for scheme in ("item", "fact"):
        rng = np.random.default_rng(SEED)
        bn, bf, br = [], [], []
        for _ in range(N_BOOT):
            if scheme == "item":
                key = "tercile" if strata else "group"
                s_ = pd.concat([g.iloc[rng.integers(0, len(g), len(g))] for _, g in df.groupby(["group", key])])
            else:
                s_ = pd.concat([by[cl[i]] for i in rng.integers(0, len(cl), len(cl))])
            f, n = s_[s_.group == "F"], s_[s_.group == "N"]
            nb, fb = _means(f, n, strata) if len(f) and len(n) else (np.nan, np.nan)
            bn.append(nb); bf.append(fb); br.append(nb / fb if (fb == fb and fb > 0) else np.nan)
        boot[scheme] = {"N": np.array(bn), "F": np.array(bf), "rho": np.array(br)}
    return {"est": est, "boot": boot}


def ci(x: np.ndarray, level: float) -> tuple[float, float]:
    x = x[np.isfinite(x)]
    if not len(x):
        return (np.nan, np.nan)
    a = (1 - level) / 2
    return float(np.quantile(x, a)), float(np.quantile(x, 1 - a))


def wider(boot: dict, k: str, level: float) -> tuple[tuple[float, float], str]:
    c = {s: ci(boot[s][k], level) for s in boot}
    s = max(c, key=lambda z: (c[z][1] - c[z][0]) if np.isfinite(c[z]).all() else np.inf)
    return c[s], s


def verdict(res: dict) -> dict:
    e, b = res["est"], res["boot"]
    n95, sn = wider(b, "N", 0.95)
    f95, sf = wider(b, "F", 0.95)
    r90, sr = wider(b, "rho", 0.90)
    undef = float(np.mean(~np.isfinite(b[sr]["rho"])))
    rho_ok = undef <= 0.05
    dn, df_, dr = b[sn]["N"], b[sf]["F"], b[sr]["rho"]
    p_nr = float(np.mean(~(dn > 0)))                  # NaN draws count against the claim
    p_fr = float(np.mean(~(df_ > 0)))
    p_rho_lt = float(np.mean(~(dr >= 0.5)))           # H0: ρ < 0.5 (undefined counts against READS WRITTEN)
    p_rho_ge = float(np.mean(~(dr < 0.5)))            # H0: ρ ≥ 0.5 (undefined counts against TRACKS USE)
    return {**e, "N_minus_R_ci95": n95, "F_minus_R_ci95": f95, "rho_ci90": r90 if rho_ok else (np.nan, np.nan), "rho_undefined_share": undef,
            "schemes": {"N_minus_R": sn, "F_minus_R": sf, "rho": sr},
            "p_reads_written": max(p_nr, p_rho_lt), "p_tracks_use": max(p_fr, p_rho_ge),
            "rw_conditions": bool(rho_ok and n95[0] > 0 and r90[0] >= 0.5),
            "tu_conditions": bool(rho_ok and f95[0] > 0 and r90[1] < 0.5)}


def bh(p: dict[str, float], q: float = Q) -> dict[str, bool]:
    ks = sorted(p, key=p.get)
    m, ok = len(ks), set()
    for i, k in enumerate(ks, 1):
        if p[k] <= q * i / m:
            ok = set(ks[:i])
    return {k: k in ok for k in p}


def label(v: dict, rw_bh: bool, tu_bh: bool) -> str:
    if v["rw_conditions"] and rw_bh:
        return "READS WRITTEN"
    if v["tu_conditions"] and tu_bh:
        return "TRACKS USE"
    return "MIXED"


def analyse(df: pd.DataFrame, cluster: dict[str, str], strata: bool) -> dict[str, dict]:
    res = {rd: verdict(stats(g, cluster, strata)) for rd, g in df.groupby("reader")}
    prim = [r for r in PRIMARY if r in res]
    rw = bh({r: res[r]["p_reads_written"] for r in prim})
    tu = bh({r: res[r]["p_tracks_use"] for r in prim})
    for r in res:
        res[r]["verdict"] = label(res[r], rw.get(r, False), tu.get(r, False)) if r in prim else (
            label(res[r], res[r]["p_reads_written"] <= Q, res[r]["p_tracks_use"] <= Q) + " (CIRCULAR, not in BH)")
    return res


def binary_secondary(sw_df: pd.DataFrame) -> pd.DataFrame:
    """Secondary, descriptive: binary switch rates per group and their item-bootstrap 95% CIs (no verdict)."""
    rows = []
    for rd, g in sw_df.groupby("reader"):
        F, N = g[g.group == "F"], g[g.group == "N"]
        rng = np.random.default_rng(SEED)
        fn = [F.real.iloc[rng.integers(0, len(F), len(F))].mean() - N.real.iloc[rng.integers(0, len(N), len(N))].mean() for _ in range(N_BOOT)]
        nr = [(lambda x: (x.real - x.rand).mean())(N.iloc[rng.integers(0, len(N), len(N))]) for _ in range(N_BOOT)]
        rows.append({"reader": rd, "F": F.real.mean(), "N": N.real.mean(), "R_on_N": N.rand.mean(), "R_on_F": F.rand.mean(),
                     "F_minus_N": F.real.mean() - N.real.mean(), "F_minus_N_ci95": ci(np.array(fn), 0.95),
                     "N_minus_R": (N.real - N.rand).mean(), "N_minus_R_ci95": ci(np.array(nr), 0.95)})
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    P = A.Paths()
    sw = A.read_jsonl(P.cache / "swap" / "swap.jsonl")
    sw = sw[sw.part == "khop"]
    rr = A.read_jsonl(P.cache / "swap" / "swap_readers.jsonl")
    rr = rr[(rr.part == "khop") & (rr["unscorable"] != True)]  # noqa: E712
    F, N = groups(sw)
    items = pd.DataFrame(json.loads((P.dataset / "items_re.json").read_text())["items"])
    cons = items[items.dataset == "re_khop2_bridge"].set_index("item_id").construction
    cluster = {i: cons[i]["bridge"] for i in F + N}
    nat = sw[sw.arm == "natural"].drop_duplicates("item").set_index("item")
    margin = nat.lo_answer.reindex(F + N)
    terc = pd.qcut(margin, 3, labels=False).astype(int).to_dict()
    df = net_shifts(rr, F + N)
    df["group"] = np.where(df.item.isin(set(F)), "F", "N")
    df["tercile"] = df.item.map(terc)
    smoke = {"re-re_khop2_bridge-test-0136", "re-re_khop2_bridge-test-0140", "re-re_khop2_bridge-test-0160", "re-re_khop2_bridge-test-0171"}
    runs = {"primary": analyse(df, cluster, False), "margin_matched": analyse(df, cluster, True),
            "without_smoke_items": analyse(df[~df.item.isin(smoke)], cluster, False)}
    rows = []
    for run, res in runs.items():
        for rd, v in res.items():
            rows.append({"run": run, "reader": rd, **{k: v[k] for k in ("N_minus_R", "F_minus_R", "rho", "shift_real_N", "shift_rand_N",
                                                                      "shift_real_F", "shift_rand_F", "rho_undefined_share")},
                         "N_minus_R_ci95": v["N_minus_R_ci95"], "F_minus_R_ci95": v["F_minus_R_ci95"], "rho_ci90": v["rho_ci90"],
                         "schemes": v["schemes"], "p_reads_written": v["p_reads_written"], "p_tracks_use": v["p_tracks_use"], "verdict": v["verdict"]})
    tab = pd.DataFrame(rows)
    tab.to_csv(P.results / "swap_u.csv", index=False)
    sw_bin = switches(rr, F + N)
    sw_bin["group"] = np.where(sw_bin.item.isin(set(F)), "F", "N")
    sec = binary_secondary(sw_bin)
    sec.to_csv(P.results / "swap_u_binary.csv", index=False)
    dmap = df.set_index(["reader", "item"]).d
    # examples: 10 N items, seed 0
    rng = np.random.default_rng(SEED)
    ex_ids = sorted(rng.choice(N, size=min(10, len(N)), replace=False).tolist())
    e24 = sw[(sw.arm == "d_swap") & (sw.layer == LAYER)].drop_duplicates("item").set_index("item")
    r_nat = rr[(rr.arm == "natural") & (rr.pair == "bridge")].drop_duplicates(["reader", "item"]).set_index(["reader", "item"]).lo
    r_ed = rr[(rr.arm == "d_swap") & (rr.layer == LAYER) & (rr.pair == "bridge")].drop_duplicates(["reader", "item"]).set_index(["reader", "item"]).lo
    ex = []
    for i in ex_ids:
        c = cons[i]
        row = {"item": i, "original_bridge": c["bridge"], "swapped_in_bridge": c["distractor"], "true_answer": c["answer"],
               "distractor_answer": c["distractor_answer"],
               "model_answer_natural": c["answer"] if nat.loc[i, "prefers_answer_true"] else c["distractor_answer"],
               "model_answer_LO_natural": round(float(nat.loc[i, "lo_answer"]), 2),
               "model_answer_swapped": c["answer"] if e24.loc[i, "prefers_answer_true"] else c["distractor_answer"],
               "model_answer_LO_swapped": round(float(e24.loc[i, "lo_answer"]), 2),
               "model_bridge_LO_natural": round(float(nat.loc[i, "lo_bridge"]), 2), "model_bridge_LO_swapped": round(float(e24.loc[i, "lo_bridge"]), 2)}
        for rd in ("jlens", "nla", "olens", "skip_a"):
            a_, b_ = r_nat.get((rd, i), np.nan), r_ed.get((rd, i), np.nan)
            row[f"{rd}_bridge_LO"] = f"{a_:+.2f} → {b_:+.2f}"
            row[f"{rd}_reads"] = (c["distractor"] if b_ < 0 else c["bridge"]) if b_ == b_ else "—"
            row[f"{rd}_net_shift"] = round(float(dmap.get((rd, i), np.nan)), 2)
        ex.append(row)
    exdf = pd.DataFrame(ex)
    exdf.to_csv(P.results / "swap_u_examples.csv", index=False)
    (P.results / "swap_u.md").write_text(report(tab, sec, exdf, len(F), len(N), terc, F, N), encoding="utf-8")
    print(open(P.results / "swap_u.md").read())
    return 0


def report(tab: pd.DataFrame, sec: pd.DataFrame, ex: pd.DataFrame, nF: int, nN: int, terc: dict, F: list, N: list) -> str:
    from projects.g_agreement.r_bench import ws3_tier as WT

    f = lambda x: f"{x:+.3f}" if x == x else "—"  # noqa: E731
    order = {"nla": 0, "olens": 1, "skip_a": 2, "jlens": 3}
    cnt = pd.Series(terc).groupby(lambda i: "F" if i in set(F) else "N").value_counts().unstack(fill_value=0)
    L = ["# SWAP-U — written vs used (BRIEF_R §26; EXPLORATORY)", "",
         f"Layer 24, J-lens bridge swap d_swap at α = 1, re_khop2_bridge test items. F = answer flipped ({nF}); N = natural answer correct "
         f"and not flipped ({nN}); R = each item's mean over d_rand0..2 at the same layer and norm. Primary metric: per item, the reader's "
         "bridge log-odds shift toward the swapped-in bridge under d_swap minus the item's random-direction mean (d). N − R = mean d over N; "
         "F − R = mean d over F; ρ = N/F. Bootstrap 2,000 draws, seed 0, item level and fact-clustered (cluster = the true bridge), the wider "
         "interval quoted; BH q = 0.10 across the three primary readers. The J-lens is CIRCULAR (the swap is its own readout direction).", "",
         "Answer-margin terciles: " + "; ".join(f"T{t}: F {int(cnt.loc['F', t]) if 'F' in cnt.index else 0}, N {int(cnt.loc['N', t]) if 'N' in cnt.index else 0}"
                                              for t in sorted(cnt.columns)), ""]
    titles = {"primary": "Primary", "margin_matched": "Margin-matched sensitivity (F standardised to N's answer-margin terciles)",
              "without_smoke_items": "Sensitivity: without the 4 smoke-pass items (norm caveat, swap.md)"}
    for run, title in titles.items():
        t = tab[tab.run == run].sort_values("reader", key=lambda s_: s_.map(order))
        L += [f"## {title}", "", "| reader | shift N: real, random | shift F: real, random | N − R [95%] | F − R [95%] | ρ = N/F [one-sided 95% bounds] | "
              "p (written) | p (use) | verdict |", "|---|---|---|---|---|---|---|---|---|"]
        for r in t.itertuples():
            L.append(f"| {r.reader} | {r.shift_real_N:+.2f}, {r.shift_rand_N:+.2f} | {r.shift_real_F:+.2f}, {r.shift_rand_F:+.2f} | "
                     f"{f(r.N_minus_R)} [{f(r.N_minus_R_ci95[0])}, {f(r.N_minus_R_ci95[1])}] | {f(r.F_minus_R)} [{f(r.F_minus_R_ci95[0])}, {f(r.F_minus_R_ci95[1])}] | "
                     f"{f(r.rho)} [{f(r.rho_ci90[0])}, {f(r.rho_ci90[1])}] | {r.p_reads_written:.3f} | {r.p_tracks_use:.3f} | {r.verdict} |")
        L.append("")
    p_, m_ = tab[tab.run == "primary"].set_index("reader").verdict, tab[tab.run == "margin_matched"].set_index("reader").verdict
    dis = [r for r in p_.index if p_[r] != m_.get(r)]
    L += ["**Primary vs margin-matched:** " + ("they agree for every reader." if not dis else
          "they DISAGREE for " + ", ".join(f"{r} (primary {p_[r]}; margin-matched {m_[r]})" for r in dis) + " — both are reported; neither is chosen."), ""]
    L += ["## Secondary (descriptive, no verdict): binary switch rate, as in the R-S2 table", "",
          "| reader | F | N | R on N | R on F | F − N [95%] | N − R [95%] |", "|---|---|---|---|---|---|---|"]
    for r in sec.sort_values("reader", key=lambda s_: s_.map(order)).itertuples():
        L.append(f"| {r.reader} | {r.F:.3f} | {r.N:.3f} | {r.R_on_N:.3f} | {r.R_on_F:.3f} | {f(r.F_minus_N)} [{f(r.F_minus_N_ci95[0])}, {f(r.F_minus_N_ci95[1])}] | "
                 f"{f(r.N_minus_R)} [{f(r.N_minus_R_ci95[0])}, {f(r.N_minus_R_ci95[1])}] |")
    L += ["", "## 10 non-flipped (N) items, drawn with seed 0", "",
          "| item | original bridge | swapped-in bridge | model answer: natural → swapped (LO) | J-lens | NLA | Oracle lens | skip-lens |", "|---|---|---|---|---|---|---|---|"]
    for r in ex.itertuples():
        cell = lambda rd: f"{getattr(r, rd + '_reads')} ({getattr(r, rd + '_bridge_LO')}; net {getattr(r, rd + '_net_shift'):+.2f})"  # noqa: E731
        L.append(f"| {r.item.rsplit('-', 1)[1]} | {r.original_bridge} | {r.swapped_in_bridge} | {r.model_answer_natural} ({r.model_answer_LO_natural:+.2f}) → "
                 f"{r.model_answer_swapped} ({r.model_answer_LO_swapped:+.2f}) | {cell('jlens')} | {cell('nla')} | {cell('olens')} | {cell('skip_a')} |")
    L += ["", "Reader cells: the bridge the reader reports under the swap (bridge LO true − swapped-in, natural → swapped; net shift d toward the "
          "swapped-in bridge beyond the random-direction mean)."]
    return WT.finalize_md("\n".join(L)) + "\n"


if __name__ == "__main__":
    sys.exit(main())
