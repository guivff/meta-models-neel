"""Interim tables for the extra banks (WS3): R-E (``items_re.json``, BRIEF_R §11) and ReaderBench (``items_rb.json`` +
``items_rbk.json``, readerbench/README.md). Written as soon as a bank's rows exist, beyond-text facts first (KHOP,
SYNTAX, COUNT, INTERNAL), even before the other banks finish.

Rows are read from every shard file (``reader_lo.*``, ``prompt_only.*``, ``kway_lo.*``, ``re_relabel.*``) and kept
only for the bank's own datasets, with the same provenance filter as the main tables. Every rule below is §11's as
written; where its text is ambiguous the literal reading is marked ``# RULE:`` and logged in BRIEF_R Deviations (WS3).

    python -m projects.g_agreement.r_bench.interim_banks           # → results/g_agreement/r/interim_re.md, interim_rb.md
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd

from common.stats import wilson
from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import checkpoint_tier as _ct

BEYOND = ["KHOP", "SYNTAX", "COUNT", "INTERNAL"]
LENS = ["jlens", "olens", "nla", "skip_a", "skip_d"]
RAW_PRIMARY = {"re_count_col"}  # §11: judged on the raw render only


def _bank(P: A.Paths, files: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for f in files:
        p = P.dataset / f
        if p.exists():
            rows += json.loads(p.read_text())["items"]
    it = pd.DataFrame(rows)
    if len(it):
        it["sided"] = it["primary"].map(lambda p: p.get("sided"))
    return it


MODEL_LABEL_INFO: dict[str, dict] = {}


def apply_model_labels(P: A.Paths, items: pd.DataFrame, *frames: pd.DataFrame) -> tuple[pd.DataFrame, ...]:
    """Facts with ``primary.label_source == "model"`` (ReaderBench INTERNAL / context_against_belief) take their AUROC label
    from ``model_labels*.jsonl::model_label`` (WS12's design; BRIEF_R §12/§13 "as analyze.py does"); rows and items whose
    model label is None or missing are dropped; the construction label is kept as ``construction_label``. Fixed
    2026-10-20 (WS3 bullet): until then the tables used the rows' provisional label."""
    if items.empty or "primary" not in items.columns:
        return (items, *frames)
    ml_ds = set(items[items["primary"].map(lambda q: q.get("label_source")) == "model"].dataset)
    if not ml_ds:
        return (items, *frames)
    ml = A.read_jsonl_shards(P.cache, "model_labels")
    ml = ml[ml.dataset.isin(ml_ds)].drop_duplicates("item_id", keep="last") if len(ml) else ml
    lab = dict(zip(ml.item_id, ml.model_label)) if len(ml) else {}
    keep = {i for i, v in lab.items() if v is not None and v == v}

    def fix(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "dataset" not in df.columns or "label" not in df.columns:
            return df
        m = df.dataset.isin(ml_ds)
        df = df[~m | df.item_id.isin(keep)].copy()
        m = df.dataset.isin(ml_ds)
        df["construction_label"] = df["label"]
        df.loc[m, "label"] = df.loc[m, "item_id"].map(lab).astype(int)
        return df

    for ds in sorted(ml_ds):
        it = items[items.dataset == ds]
        t = it[it.split == "test"]
        MODEL_LABEL_INFO[ds] = {"test_items": int(len(t)), "test_with_model_label": int(t.item_id.isin(keep).sum()),
                                "pool_items": int((it.split == "pool").sum()), "pool_with_model_label": int(it[it.split == "pool"].item_id.isin(keep).sum()),
                                "test_agree_with_construction": float((t[t.item_id.isin(keep)].label.astype(int).values ==
                                                                       t[t.item_id.isin(keep)].item_id.map(lab).astype(int).values).mean())
                                if t.item_id.isin(keep).any() else float("nan")}
    return (fix(items), *(fix(f) for f in frames))


def _rows(P: A.Paths, name: str, items: pd.DataFrame) -> pd.DataFrame:
    df = A.read_jsonl_shards(P.cache, name, datasets=set(items.dataset))
    if df.empty or "dataset" not in df.columns:
        return pd.DataFrame()
    return df[df.dataset.isin(set(items.dataset))].reset_index(drop=True)


def _site(ds: str, reader: str) -> tuple[int, str]:
    return A.PRIMARY_LAYER.get(reader, 42), ("raw" if ds in RAW_PRIMARY else A.PRIMARY_RENDER)


def _probe512(P: A.Paths, items: pd.DataFrame, ds: str, render: str, layer: int = 42) -> float:
    """probe(512) on the fact's pool states (C chosen by inner CV), test AUROC; NaN without states."""
    try:
        X, idx = A.load_states(P, ds, render, layer)
    except (FileNotFoundError, ValueError, OSError):
        return np.nan
    it = items[items.dataset == ds].set_index("item_id")
    idx = [i for i in idx if i in it.index]
    if not idx:
        return np.nan
    pos = {i: k for k, i in enumerate(json.loads((P.cache / "states" / ds / "index.json").read_text())["item_ids"])}
    Xi = X[[pos[i] for i in idx]]
    y, split = it.loc[idx, "label"].values.astype(int), it.loc[idx, "split"].values
    tr, te = np.where(split == "pool")[0], np.where(split == "test")[0]
    if len(tr) < 10 or len(te) < 10 or len(set(y[tr])) < 2:
        return np.nan
    clf, _, _ = A.probe_fit_select(Xi[tr], y[tr], 0)
    return A.auroc(y[te], clf.decision_function(Xi[te]))


def fact_table(P: A.Paths, items: pd.DataFrame, lo: pd.DataFrame, po: pd.DataFrame, with_probe: bool = True) -> pd.DataFrame:
    """Two-/one-sided facts: per fact × reader at the primary site, natural test AUROC [CI], prompt-only AUROC, the
    paired Δ, the shuffled cell's CI (gate) and probe(512)."""
    if lo.empty:
        return pd.DataFrame()
    sided_of = dict(zip(items.dataset, items.sided))
    tag_of = dict(zip(items.dataset, items.tag))
    split_of = dict(zip(items.item_id, items.split))
    lo = lo[lo.get("unscorable", False) != True].copy()  # noqa: E712
    lo["score"] = A.primary_score(lo, sided_of)
    lo["split"] = lo.item_id.map(split_of)
    pot = po[po["lo"].notna() & po.item_id.map(split_of).eq("test")] if len(po) and "lo" in po.columns else pd.DataFrame()
    out = []
    for (ds, rd), g in lo[lo.split == "test"].groupby(["dataset", "reader"]):
        if sided_of.get(ds) == "kway":
            continue
        L_, render = _site(ds, rd)
        nat = g[(g.layer == L_) & (g.render == render) & (g.condition == "natural")]
        if len(nat) < 10:
            continue
        a, lo95, hi95 = A.auroc_ci(nat.label.values, nat.score.values, n_boot=500)
        sh = g[(g.layer == L_) & (g.render == render) & (g.condition == "shuf")]
        sa = A.auroc_ci(sh.label.values, sh.score.values, n_boot=500) if len(sh) >= 10 else (np.nan, np.nan, np.nan)
        row = {"dataset": ds, "tag": tag_of.get(ds), "reader": rd, "layer": L_, "render": render, "n": len(nat),
               "auroc": a, "ci_lo": lo95, "ci_hi": hi95, "shuf_auroc": sa[0], "shuf_ok": bool(sa[1] <= 0.5 <= sa[2]) if np.isfinite(sa[1]) else None}
        gp = pot[pot.dataset == ds] if len(pot) else pot
        if len(gp):
            m = nat.merge(gp[["item_id", "lo"]].rename(columns={"lo": "po_lo"}), on="item_id")
            if len(m) >= 10:
                d, dlo, dhi = A.paired_auroc_diff(m.label.values, m.score.values, m.po_lo.values, n_boot=500)
                row.update(prompt_only_auroc=A.auroc(m.label.values, m.po_lo.values), diff=d, diff_lo=dlo, diff_hi=dhi,
                           exceeds_ceiling=bool(d >= 0.05 and dlo > 0))
        out.append(row)
    df = pd.DataFrame(out)
    if with_probe and len(df):
        # RULE: on facts with per-item, order-counterbalanced candidates (label = "c0 is the truth"), the label is a property
        # of the candidate order, which is not in the prompt state: probe(512) on that label is ≈ 0.5 by construction, so
        # it is no PRESENT reference and is reported as undefined (Deviations, WS3 2026-10-19).
        per_item = per_item_facts(items)
        pr = {ds: (np.nan if per_item.get(ds) else _probe512(P, items, ds, _site(ds, "jlens")[1])) for ds in df.dataset.unique()}
        df["probe512"] = df.dataset.map(pr)
        df["per_item_candidates"] = df.dataset.map(per_item)
    return df


def per_item_facts(items: pd.DataFrame) -> dict[str, bool]:
    return {ds: g.primary.map(lambda p: tuple(p.get("candidates", []))).nunique() > 2 for ds, g in items.groupby("dataset")}


def kway_table(items: pd.DataFrame, kw: pd.DataFrame, po: pd.DataFrame) -> pd.DataFrame:
    """k-way facts (R6 / §11 COUNT): argmax accuracy per reader × layer × render with a Wilson CI and chance; the
    model's own k-way prompt-only accuracy."""
    out = []
    test = set(items[items.split == "test"].item_id)
    if len(kw):
        k = kw[(kw.get("unscorable", False) != True) & kw.item_id.isin(test)]  # noqa: E712
        for (ds, rd, L_, render), g in k.groupby(["dataset", "reader", "layer", "render"]):
            piv = g.pivot_table(index="item_id", columns="cand_index", values="lp")
            lab = g.groupby("item_id")["label"].first().loc[piv.index].values.astype(int)
            am = piv.values.argmax(1)
            hit = int((am == lab).sum())
            p_, l_, h_ = wilson(hit, len(piv))
            modal = float(np.bincount(am, minlength=piv.shape[1]).max() / len(am))  # 1.0 = the reader picks one candidate always
            out.append({"dataset": ds, "method": rd, "layer": int(L_), "render": render, "k": piv.shape[1], "n": len(piv),
                        "acc": p_, "ci_lo": l_, "ci_hi": h_, "chance": 1 / piv.shape[1], "modal_share": modal})
    if len(po) and "greedy" in po.columns:
        kd = set(items[items.sided == "kway"].dataset)
        for ds, g in po[po.dataset.isin(kd) & po.item_id.isin(test)].groupby("dataset"):
            hit = int((g.greedy == g.label).sum())
            p_, l_, h_ = wilson(hit, len(g))
            kk = len(g.iloc[0]["lp"]) if isinstance(g.iloc[0].get("lp"), list) else np.nan
            out.append({"dataset": ds, "method": "prompt_only", "layer": np.nan, "render": "chat", "k": kk, "n": len(g),
                        "acc": p_, "ci_lo": l_, "ci_hi": h_, "chance": 1 / kk if kk == kk else np.nan})
    return pd.DataFrame(out)


def _fmt(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def fact_md(ft: pd.DataFrame, title: str) -> list[str]:
    L = ["", f"## {title}", ""]
    if ft.empty:
        return L + ["No reader rows for these facts yet."]
    order = {t: i for i, t in enumerate(BEYOND)}
    ft = ft.assign(_o=ft.tag.map(lambda t: order.get(t, 99))).sort_values(["_o", "tag", "dataset", "reader"])
    L += ["Natural test AUROC at the reader's primary site [item-bootstrap 95% CI]; Δ = reader − prompt-only (paired); "
          "exceed = Δ ≥ +0.05 with CI > 0 (raw, no BH); shuffled gate = shuffled cell's CI ∋ 0.5.", "",
          "| tag | fact | reader | site | n | AUROC [CI] | prompt-only | Δ [CI] | exceed | probe(512) | ≥ 0.8×probe | shuffled |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in ft.itertuples():
        d = f"{r.diff:+.3f} [{r.diff_lo:+.3f}, {r.diff_hi:+.3f}]" if hasattr(r, "diff") and r.diff == r.diff else "—"
        pr = getattr(r, "probe512", np.nan)
        mi = MODEL_LABEL_INFO.get(r.dataset)
        fact = (f"{r.dataset} (model label; defect prevalence {1 - mi['test_agree_with_construction']:.0%} of "
                f"{mi['test_with_model_label']} labelled, {mi['test_items'] - mi['test_with_model_label']} dropped)") if mi else r.dataset
        L.append(f"| {r.tag} | {fact} | {r.reader} | {r.layer}/{r.render} | {r.n} | {r.auroc:.3f} [{r.ci_lo:.3f}, {r.ci_hi:.3f}] | "
                 f"{_fmt(getattr(r, 'prompt_only_auroc', np.nan))} | {d} | "
                 f"{('yes†' if r.shuf_ok is False else 'yes') if getattr(r, 'exceeds_ceiling', False) is True else ''} | "
                 f"{_fmt(pr)} | {'yes' if pr == pr and r.auroc >= 0.8 * pr else ('no' if pr == pr else '—')} | "
                 f"{'' if r.shuf_ok is None else ('pass' if r.shuf_ok else 'FAIL')} |")
    return L


def gate_md(ft: pd.DataFrame, items: pd.DataFrame) -> list[str]:
    """The shuffled gate for this bank (§4.2: a shuffled cell passes iff its 95% CI ∋ 0.5; failing cells are inspected
    as pipeline bugs first), split by whether the fact has per-item candidates. With per-item candidates a shuffled AUROC
    near the natural one means the score is the reader's candidate prior, not the state (E3)."""
    d = ft[ft.shuf_ok.notna()] if len(ft) else ft
    if d.empty:
        return []
    per_item = {ds: g.primary.map(lambda p: tuple(p.get("candidates", []))).nunique() > 2 for ds, g in items.groupby("dataset")}
    d = d.assign(per_item=d.dataset.str.replace(" ⚑", "", regex=False).map(per_item))
    fail = d[d.shuf_ok == False]  # noqa: E712
    L = ["", f"**Shuffled gate (§4.2, 95% CI ∋ 0.5):** {len(d) - len(fail)} pass / {len(fail)} fail of {len(d)} primary-site cells "
         f"(expected at 5%: {0.05 * len(d):.1f}); per-item-candidate facts {int((fail.per_item == True).sum())}/{int((d.per_item == True).sum())} fail, "  # noqa: E712
         f"fixed-candidate facts {int((fail.per_item == False).sum())}/{int((d.per_item == False).sum())}. † on an exceedance = its shuffled cell fails "  # noqa: E712
         "(candidate prior suspected; not read as a reading of the state)."]
    if len(fail):
        L.append("Failing cells (natural / shuffled AUROC): " + "; ".join(f"{r.reader} {r.dataset} {r.auroc:.3f} / {r.shuf_auroc:.3f}" for r in fail.itertuples()))
    return L


def kway_md(kt: pd.DataFrame, title: str) -> list[str]:
    L = ["", f"## {title}", ""]
    if kt.empty:
        return L + ["No k-way rows for these facts yet."]
    L += ["modal share = share of items given the reader's most frequent pick (1.0 = it answers the same candidate always; its accuracy is "
          "then 1/k by construction on a balanced test).", "",
          "| fact | method | layer/render | k | n | accuracy [Wilson 95%] | chance | modal share |", "|---|---|---|---|---|---|---|---|"]
    for r in kt.sort_values(["dataset", "method", "render", "layer"]).itertuples():
        site = "—" if r.layer != r.layer else f"{int(r.layer)}/{r.render}"
        L.append(f"| {r.dataset} | {r.method} | {site} | {r.k} | {r.n} | {r.acc:.3f} [{r.ci_lo:.3f}, {r.ci_hi:.3f}] | {_fmt(r.chance)} | "
                 f"{_fmt(getattr(r, 'modal_share', np.nan), 2)} |")
    return L


# ------------------------------------------------------------------ R-E rules (BRIEF_R §11)
def re_khop(ft: pd.DataFrame) -> list[str]:
    """H2 extended to KHOP: per lens reader, reader ≥ 0.8 × probe(512) on ≥ 2 of the 3 KHOP facts."""
    L = ["", "### KHOP — H2 clause (≥ 0.8 × probe(512) on ≥ 2 of 3 KHOP facts)", ""]
    k = ft[(ft.tag == "KHOP") & ft.reader.isin(LENS)] if len(ft) else ft
    if len(k) and "per_item_candidates" in k.columns and k.per_item_candidates.all():
        return L + ["**NOT TESTABLE as written:** all three KHOP facts have per-item, order-counterbalanced candidates (label = "
                    "\"c0 is the truth\"). That label is not in the prompt state, so probe(512) is ≈ 0.5 by construction (measured "
                    "0.500 on re_khop2_answer / re_khop2_bridge), and \"reader ≥ 0.8 × probe\" would reduce to \"reader ≥ 0.4\". "
                    "Reader AUROCs at the primary site are in the table above; a valid PRESENT reference (a probe on the bridge "
                    "or answer entity, scored per candidate) is not pre-registered."]
    if k.empty or "probe512" not in k.columns or k.probe512.isna().all():
        return L + ["Not yet: needs KHOP reader rows and R-E pool/test states for probe(512)."]
    for rd, g in k.groupby("reader"):
        g = g[g.probe512.notna()]
        ok = int((g.auroc >= 0.8 * g.probe512).sum())
        verdict = "SUPPORTED" if ok >= 2 else ("REFUTED" if len(g) == 3 else "UNDERPOWERED (fewer than 3 facts)")
        L.append(f"- {rd}: {ok}/{len(g)} facts → {verdict}")
    return L


def re_syntax(items: pd.DataFrame, lo: pd.DataFrame, n_boot: int = 1000) -> list[str]:
    """SYNTAX number: reader AUROC on the match cells vs the mismatch cells; a drop ≥ 0.10 with CI > 0 is attractor
    interference. # RULE: §11 says "paired bootstrap over items" but the match and mismatch cells are disjoint item
    sets; the difference is bootstrapped by resampling items within each cell set (stratified), seed 0."""
    L = ["", "### SYNTAX — attractor interference on `re_syntax_number` (match − mismatch AUROC ≥ 0.10 with CI > 0)", ""]
    it = items[(items.dataset == "re_syntax_number") & (items.split == "test")]
    if lo.empty or it.empty:
        return L + ["No rows yet."]
    cell = it.set_index("item_id")["construction"].map(lambda c: c.get("cell"))
    match = {i for i, c in cell.items() if c in ("pl-pl", "sg-sg")}
    g0 = lo[(lo.dataset == "re_syntax_number") & (lo.condition == "natural") & lo.item_id.isin(cell.index)]
    rng = np.random.default_rng(0)
    L += ["| reader | site | AUROC match | AUROC mismatch | drop [95% CI] | interference |", "|---|---|---|---|---|---|"]
    for rd, g in g0.groupby("reader"):
        L_, render = _site("re_syntax_number", rd)
        g = g[(g.layer == L_) & (g.render == render)]
        a, b = g[g.item_id.isin(match)], g[~g.item_id.isin(match)]
        if len(a) < 10 or len(b) < 10:
            continue
        ya, sa, yb, sb = a.label.values, a.lo.values, b.label.values, b.lo.values
        d = A.auroc(ya, sa) - A.auroc(yb, sb)
        bs = []
        for _ in range(n_boot):
            ia, ib = rng.integers(0, len(a), len(a)), rng.integers(0, len(b), len(b))
            bs.append(A.auroc(ya[ia], sa[ia]) - A.auroc(yb[ib], sb[ib]))
        lo_, hi_ = np.nanpercentile(bs, [2.5, 97.5])
        L.append(f"| {rd} | {L_}/{render} | {A.auroc(ya, sa):.3f} | {A.auroc(yb, sb):.3f} | {d:+.3f} [{lo_:+.3f}, {hi_:+.3f}] | "
                 f"{'YES' if d >= 0.10 and lo_ > 0 else 'no'} |")
    L.append("The model's own is/are readout (`construction.behaviour`, next-token lp(are) − lp(is)) is reported once its rows exist.")
    return L


def re_internal(items: pd.DataFrame, lo: pd.DataFrame, rl: pd.DataFrame) -> list[str]:
    """INTERNAL: on items whose design label and behavioural key disagree, P(reader sides with the behaviour) with a
    Wilson CI per reader × layer; READS THE MODEL iff ≥ 0.75 and CI > 0.5, READS THE TEXT iff ≤ 0.25 and CI < 0.5;
    fewer than 12 disagreeing items → not testable. The reader's side is the sign of s_diff (two-sided facts)."""
    L = ["", "### INTERNAL — does the reader side with the model's behaviour or the design label?", ""]
    if rl.empty:
        return L + ["Not testable yet: no behavioural key (`re_relabel*.jsonl`) rows."]
    key = rl.drop_duplicates("item_id", keep="last").set_index("item_id")
    L += ["Diagnostics (not part of the rule): `beh=1` = share of disagreeing items whose behaviour is the positive candidate; "
          "`pos rate` = the reader's share of s_diff > 0 over all natural test items. A reader with pos rate ≈ 0 or 1 answers its prior, "
          "and P(sides with behaviour) then equals beh=1 or 1 − beh=1 by construction.", "",
          "| fact | reader | layer/render | disagreeing n | beh=1 | pos rate | P(sides with behaviour) [Wilson] | verdict |", "|---|---|---|---|---|---|---|---|"]
    for ds in ("re_internal_refuse", "re_internal_abstain"):
        k = key[(key.dataset == ds) & (key.split == "test")]
        dis = k[k.label != k.design_label]
        g0 = lo[(lo.dataset == ds) & (lo.condition == "natural") & lo.item_id.isin(dis.index)]
        allt = lo[(lo.dataset == ds) & (lo.condition == "natural") & lo.item_id.isin(k.index)]
        if len(dis) < 12:
            L.append(f"| {ds} | all | — | {len(dis)} | — | — | — | not testable (< 12) |")
            continue
        for (rd, L_, render), g in g0.groupby(["reader", "layer", "render"]):
            if render != "chat":
                continue
            side = (g.lo.values > 0).astype(int)
            beh = dis.loc[g.item_id, "label"].values.astype(int)
            p_, l_, h_ = wilson(int((side == beh).sum()), len(g))
            l_, h_ = max(0.0, l_), min(1.0, h_)
            v = "READS THE MODEL" if p_ >= 0.75 and l_ > 0.5 else ("READS THE TEXT" if p_ <= 0.25 and h_ < 0.5 else "MIXED")
            a = allt[(allt.reader == rd) & (allt.layer == L_) & (allt.render == render)]
            pos = float((a.lo > 0).mean()) if len(a) else np.nan
            L.append(f"| {ds} | {rd} | {int(L_)}/{render} | {len(g)} | {beh.mean():.2f} | {_fmt(pos, 2)} | {p_:.2f} [{l_:.2f}, {h_:.2f}] | {v} |")
    return L


def re_e4(items: pd.DataFrame, kw: pd.DataFrame, po: pd.DataFrame) -> list[str]:
    """E4 (`re_count_long`, model-wrong subset, ≥ 20 items): per reader × layer P(argmax = truth), P(argmax = greedy);
    READS THE STATE iff P(truth) ≥ 0.5 with CI > 1/5 at a layer ≤ 48 and P(greedy) > P(truth) at 56 or 60; READS THE
    OUTPUT iff P(greedy) > P(truth) at every read layer with CI excluding 1/5; otherwise MIXED.
    # RULE: "CI excluding 1/5" in the OUTPUT clause is read as P(greedy)'s Wilson CI excluding 1/5."""
    L = ["", "### E4 — `re_count_long` on the model-wrong subset", ""]
    if kw.empty or po.empty or "greedy" not in po.columns:
        return L + ["Not yet: needs k-way reader rows and prompt-only greedy counts."]
    test = set(items[(items.dataset == "re_count_long") & (items.split == "test")].item_id)
    g_po = po[(po.dataset == "re_count_long") & po.item_id.isin(test)].drop_duplicates("item_id").set_index("item_id")
    wrong = g_po[g_po.greedy != g_po.label]
    if len(wrong) < 20:
        return L + [f"Not testable: {len(wrong)} model-wrong items (< 20)."]
    k = kw[(kw.dataset == "re_count_long") & kw.item_id.isin(wrong.index) & (kw.render == "chat")]
    L += ["| reader | layer | n | P(truth) [Wilson] | P(greedy) [Wilson] |", "|---|---|---|---|---|"]
    for rd, gr in k.groupby("reader"):
        per = {}
        for L_, g in gr.groupby("layer"):
            piv = g.pivot_table(index="item_id", columns="cand_index", values="lp")
            am = piv.values.argmax(1)
            t = wrong.loc[piv.index, "label"].values.astype(int)
            gd = wrong.loc[piv.index, "greedy"].values.astype(int)
            pt, pg = wilson(int((am == t).sum()), len(piv)), wilson(int((am == gd).sum()), len(piv))
            per[int(L_)] = (pt, pg)
            L.append(f"| {rd} | {int(L_)} | {len(piv)} | {pt[0]:.2f} [{pt[1]:.2f}, {pt[2]:.2f}] | {pg[0]:.2f} [{pg[1]:.2f}, {pg[2]:.2f}] |")
        state = any(L_ <= 48 and pt[0] >= 0.5 and pt[1] > 0.2 for L_, (pt, _) in per.items()) and \
            any(L_ in (56, 60) and pg[0] > pt[0] for L_, (pt, pg) in per.items())
        output = all(pg[0] > pt[0] and (pg[1] > 0.2 or pg[2] < 0.2) for pt, pg in per.values())
        L.append(f"| **{rd}** | verdict | | **{'READS THE STATE' if state else ('READS THE OUTPUT' if output else 'MIXED')}** | |")
    return L


def re_e6(items: pd.DataFrame, lo: pd.DataFrame, po: pd.DataFrame, n_boot: int = 1000) -> list[str]:
    """E6 (KHOP, model-correct subset): `re_khop2_bridge` AUROC at the hop-1 span (blocks 24–40) vs the last token
    (42–60), per reader, paired bootstrap over items; READS THE WRONG POSITION iff span − last ≥ 0.10 with CI > 0 for
    a reader whose last-token AUROC < 0.75.
    # RULE: each band's AUROC is the reader's best layer in that band (blocks 24–40 at the span, 42–60 at the last
    # token), chosen per reader before the paired bootstrap; the bootstrap is over items at those two layers."""
    L = ["", "### E6 — KHOP bridge: hop-1 span (24–40) vs last token (42–60), model-correct subset", ""]
    if lo.empty or "position" not in lo.columns:
        return L + ["No rows yet."]
    ans = po[(po.dataset == "re_khop2_answer")] if len(po) else po
    it = items[items.dataset.isin(["re_khop2_bridge", "re_khop2_answer"]) & (items.split == "test")]
    if ans.empty or "model_says_pos" not in ans.columns:
        return L + ["Not yet: needs prompt-only greedy choices on re_khop2_answer (model-correct subset)."]
    by_text = it[it.dataset == "re_khop2_answer"].set_index("prompt_text").item_id
    # two-sided: label = 1 iff c0 is the truth; model_says_pos = the greedy pick is c0 (``greedy`` is a candidate index)
    correct_ans = set(ans[ans.model_says_pos.astype(bool) == ans.label.astype(bool)].item_id)
    br = it[it.dataset == "re_khop2_bridge"]
    keep = {r.item_id for r in br.itertuples() if by_text.get(r.prompt_text) in correct_ans}
    g0 = lo[(lo.dataset == "re_khop2_bridge") & (lo.condition == "natural") & (lo.render == "chat") & lo.item_id.isin(keep)]
    if g0.empty:
        return L + ["No model-correct bridge rows yet."]
    rng = np.random.default_rng(0)
    L += [f"model-correct items: {len(keep)}", "", "| reader | span best (layer) | last best (layer) | span − last [95% CI] | verdict |",
          "|---|---|---|---|---|"]
    for rd, g in g0.groupby("reader"):
        span = g[(g.position == "rp") & g.layer.between(24, 40)]
        last = g[(g.position == "last") & g.layer.between(42, 60)]
        if span.empty or last.empty:
            L.append(f"| {rd} | — | — | — | needs both positions |")
            continue
        sa = span.groupby("layer").apply(lambda x: A.auroc(x.label.values, x.lo.values))
        la = last.groupby("layer").apply(lambda x: A.auroc(x.label.values, x.lo.values))
        Ls, Ll = int(sa.idxmax()), int(la.idxmax())
        m = span[span.layer == Ls][["item_id", "label", "lo"]].merge(last[last.layer == Ll][["item_id", "lo"]], on="item_id", suffixes=("_s", "_l"))
        d, dlo, dhi = A.paired_auroc_diff(m.label.values, m.lo_s.values, m.lo_l.values, n_boot=n_boot)
        v = "READS THE WRONG POSITION" if d >= 0.10 and dlo > 0 and la.max() < 0.75 else "no"
        L.append(f"| {rd} | {sa.max():.3f} ({Ls}) | {la.max():.3f} ({Ll}) | {d:+.3f} [{dlo:+.3f}, {dhi:+.3f}] | {v} |")
    return L


def bank_report(P: A.Paths, name: str, files: tuple[str, ...], out_name: str, rules: bool) -> str | None:
    items = _bank(P, files)
    if items.empty:
        return None
    lo, po, kw = _rows(P, "reader_lo", items), _rows(P, "prompt_only", items), _rows(P, "kway_lo", items)
    if lo.empty and kw.empty:
        return None  # nothing to publish yet
    items, lo, po = apply_model_labels(P, items, lo, po)
    A.assert_conditions(lo, f"{name} reader_lo")
    ft = fact_table(P, items, lo, po)
    kt = kway_table(items, kw, po)
    L = [f"# {name} — interim tables (WS3)", "",
         f"generated {pd.Timestamp.utcnow().strftime('%Y-%m-%d %H:%M')} UTC; partial rows — every number moves as rows arrive. "
         f"Facts covered: {lo[~lo.dataset.isin(set(items[items.sided == 'kway'].dataset))].dataset.nunique() if len(lo) else 0} two-/one-sided with reader rows; "
         f"k-way: {kw.dataset.nunique() if len(kw) else 0} with reader rows, {kt[kt.method == 'prompt_only'].dataset.nunique() if len(kt) else 0} with prompt-only rows; "
         f"bank: {items.dataset.nunique()} facts. Pods: {sorted(map(str, set(lo.get('pod', pd.Series(dtype=object)).dropna())))}.",
         "", "Reader rows present so far (reader: blocks): " + ("; ".join(f"{rd}: {sorted(int(x) for x in g.layer.unique())}" for rd, g in lo.groupby("reader")) if len(lo) else "none")
         + ". Claims are made at each reader's primary site only (J-lens 42, Oracle 44, NLA / skip 42; `re_count_col` raw)."]
    from projects.g_agreement.r_bench import label_audit as LA

    flagged = LA.flagged_set(P) & set(items.dataset)
    mli = {k: v for k, v in MODEL_LABEL_INFO.items() if k in set(items.dataset)}
    if mli:
        L += ["", "**Model labels (fixed 2026-10-20, WS3 bullet):** " + ", ".join(sorted(mli)) + " take their AUROC label from "
              "`model_labels*.jsonl::model_label` (WS12's design); before this date these tables used the provisional label. Test items "
              "with a model label / total; agreement with the construction label: " +
              "; ".join(f"{k} {v['test_with_model_label']}/{v['test_items']}, {v['test_agree_with_construction']:.2f}" for k, v in sorted(mli.items()))
              + ". Pool items with a model label (probe(512) training): " +
              "; ".join(f"{k} {v['pool_with_model_label']}/{v['pool_items']}" for k, v in sorted(mli.items())) + "."]
    L += ["", f"Label audit (uniform trigger, `label_audit.md`): flagged in this bank: {', '.join(sorted(flagged)) or 'none'} "
          "(marked ⚑ below; every count is also given without them)."]
    if len(ft):
        ft = ft.assign(dataset=ft.dataset.map(lambda d: d + " ⚑" if d in flagged else d))
    L += gate_md(ft, items)
    if flagged and len(ft):
        L += [x.replace("**Shuffled gate", "**Shuffled gate, without flagged facts") for x in gate_md(ft[~ft.dataset.str.endswith(" ⚑")], items)[:2]]
    L += ["probe(512) is shown as — on facts with per-item, order-counterbalanced candidates: their label is the candidate order, "
          "which is not in the prompt state (≈ 0.5 by construction)."]
    L += fact_md(ft[ft.tag.isin(BEYOND)] if len(ft) else ft, "Beyond-text facts (KHOP, SYNTAX, COUNT, INTERNAL)")
    L += kway_md(kt, "k-way facts (COUNT and the other k-way parents)")
    if rules:
        L += ["", "## §11 decision rules (R-E)"]
        L += re_khop(ft)
        L += re_syntax(items, lo)
        L += re_internal(items, lo, _rows(P, "re_relabel", items))
        L += re_e4(items, kw, po)
        L += re_e6(items, lo, po)
    L += fact_md(ft[~ft.tag.isin(BEYOND)] if len(ft) else ft, "Other facts")
    from projects.g_agreement.r_bench import ws3_tier as WT

    (P.results / out_name).write_text(WT.finalize_md("\n".join(L)) + "\n", encoding="utf-8")
    if len(ft):
        _ct.annotate(ft, P.results / out_name.replace(".md", "_facts.csv")).to_csv(P.results / out_name.replace(".md", "_facts.csv"), index=False)  # checkpoint_tier column (BRIEF_RP §0)
    if len(kt):
        _ct.annotate(kt, P.results / out_name.replace(".md", "_kway.csv")).to_csv(P.results / out_name.replace(".md", "_kway.csv"), index=False)  # checkpoint_tier column (BRIEF_RP §0)
    return str(P.results / out_name)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args(argv)
    A.PROVENANCE.update(strict=True, extra_pods=set(), dropped={}, off_bank={})
    P = A.Paths()
    for name, files, out, rules in (("R-E (beyond the text, BRIEF_R §11)", ("items_re.json",), "interim_re.md", True),
                                    ("ReaderBench", ("items_rb.json", "items_rbk.json"), "interim_rb.md", False),
                                    ("R-X (external facts, WS11; descriptive, no WS3 rule)", ("items_rx.json",), "interim_rx.md", False)):
        r = bank_report(P, name, files, out, rules)
        print(f"{name}: {r or 'no rows yet'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
