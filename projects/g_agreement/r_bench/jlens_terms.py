"""BRIEF_R §15 "J-lens on its own terms" — CPU side (WS3). (a) J-lens / PRESENT AUROC ratio, workspace-type vs
classification-type facts, with the pre-registered clustered-bootstrap rule; (b) hypothesis-generation precision from the
pod's top-10 lists (``cache/g_agreement/r/jlens_terms/``, written by ``jlens_terms_pod.py``) when they exist;
(c) the J-lens − logit-lens AUROC gap per group and layer.

    python -m projects.g_agreement.r_bench.jlens_terms            # → results/g_agreement/r/jlens_terms.md (+ csv)
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from common.stats import wilson
from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import checkpoint_tier as _ct
from projects.g_agreement.r_bench import interim as I
from projects.g_agreement.r_bench import label_audit as LA

BANK_FILES = ("items_r.json", "items_re.json", "items_rx.json", "items_rb.json")
CLASS_TAGS = {"SURFACE", "TOPIC", "FORM"}
LAYERS = (24, 28, 32, 36, 38, 40, 42, 44, 48, 52, 56, 60)


def workspace_group(ds: str) -> str | None:
    if ds in ("re_khop2_bridge", "re_khop2_answer", "re_khop3_middle"):
        return "R-E KHOP"
    if ds.startswith("rb_khop_"):
        return "ReaderBench KHOP"
    k = ds.split("_", 1)[0]
    if k.startswith("x") and k[1:].isdigit():
        n = int(k[1:])
        if 22 <= n <= 29:
            return "WorkspaceBench"
        if 14 <= n <= 19:
            return "ICL task identity"
    return None


def cluster_of(ds: str) -> str:
    g = workspace_group(ds)
    return g if g else I.corpus_of(ds)


def _items(P: A.Paths) -> pd.DataFrame:
    rows = []
    for f in BANK_FILES:
        p = P.dataset / f
        if p.exists():
            rows += json.loads(p.read_text())["items"]
    it = pd.DataFrame(rows)
    it["sided"] = it["primary"].map(lambda p: p.get("sided"))
    it["per_item"] = it.dataset.map({ds: g.primary.map(lambda p: tuple(p.get("candidates", []))).nunique() > 2 for ds, g in it.groupby("dataset")})
    return it


def per_layer_auroc(P: A.Paths, items: pd.DataFrame) -> pd.DataFrame:
    """AUROC per (dataset, reader ∈ {jlens, logit_lens}, layer), natural test items, chat render, primary score."""
    test = items[items.split == "test"]
    split_ok = set(test.item_id)
    sided = dict(zip(items.dataset, items.sided))
    keep_ds = set(items[items.sided != "kway"].dataset)
    lo = A.read_jsonl_shards(P.cache, "reader_lo", datasets=set(items.dataset))
    lo = lo[(lo.reader == "jlens") & (lo.condition == "natural") & (lo.render == "chat") & lo.item_id.isin(split_ok)
            & lo.dataset.isin(keep_ds) & (lo.get("position", "last") == "last")]
    lo = lo[lo.get("unscorable", False) != True]  # noqa: E712
    lo = lo.assign(score=A.primary_score(lo, sided))
    out = [{"dataset": ds, "reader": "jlens", "layer": int(L), "auroc": A.auroc(g.label.values, g.score.values), "n": len(g)}
           for (ds, L), g in lo.groupby(["dataset", "layer"]) if len(g) >= 10]
    ll = A.read_jsonl_shards(P.cache, "logit_lens", datasets=set(items.dataset))
    ll = ll[ll.item_id.isin(split_ok) & ll.dataset.isin(keep_ds) & (ll.render == "chat")]
    rows = [{"dataset": r.dataset, "layer": int(L), "label": r.label, "s": v["margin"]} for r in ll.itertuples(index=False) for L, v in r.per_layer.items()]
    lf = pd.DataFrame(rows)
    out += [{"dataset": ds, "reader": "logit_lens", "layer": int(L), "auroc": A.auroc(g.label.values, g.s.values), "n": len(g)}
            for (ds, L), g in lf.groupby(["dataset", "layer"]) if len(g) >= 10] if len(lf) else []
    return pd.DataFrame(out)


def probe512(P: A.Paths, items: pd.DataFrame, ds: str, layer: int = 42) -> float:
    """probe(512) on the fact's pool states, C by inner CV, test AUROC (fixed-candidate facts only)."""
    try:
        X, idx = A.load_states(P, ds, "chat", layer)
    except (FileNotFoundError, ValueError, OSError):
        return np.nan
    it = items[items.dataset == ds].set_index("item_id")
    keep = [k for k, iid in enumerate(idx) if iid in it.index]
    ids = [idx[k] for k in keep]
    y, split = it.loc[ids, "label"].values.astype(int), it.loc[ids, "split"].values
    tr, te = split == "pool", split == "test"
    if tr.sum() < 10 or te.sum() < 10 or len(set(y[tr])) < 2:
        return np.nan
    clf, _, _ = A.probe_fit_select(X[keep][tr], y[tr], 0)
    return A.auroc(y[te], clf.decision_function(X[keep][te]))


def cc_probe(P: A.Paths, items: pd.DataFrame, ds: str, wu: dict | None, layer: int = 42) -> float:
    """§15 (a) PRESENT reference on per-item-candidate facts: the CANDIDATE-CONTRAST probe, logistic regression on
    x = h ⊙ (W_U[c0] − W_U[c1]) (first-token unembedding rows from the pod's ``jterms_wu_rows.npz``), fitted on the pool
    (C by inner CV), test AUROC. NaN without W_U rows or with no pool (e.g. re_khop3_middle has 0 pool items)."""
    if wu is None:
        return np.nan
    try:
        X, idx = A.load_states(P, ds, "chat", layer)
    except (FileNotFoundError, ValueError, OSError):
        return np.nan
    it = items[items.dataset == ds].set_index("item_id")
    keep = [k for k, iid in enumerate(idx) if iid in it.index and iid in wu["c0"]]
    if not keep:
        return np.nan
    ids = [idx[k] for k in keep]
    D = np.stack([wu["row"][wu["c0"][i]] - wu["row"][wu["c1"][i]] for i in ids]).astype(np.float32)
    F = X[keep] * D
    y, split = it.loc[ids, "label"].values.astype(int), it.loc[ids, "split"].values
    tr, te = split == "pool", split == "test"
    if tr.sum() < 10 or te.sum() < 10 or len(set(y[tr])) < 2:
        return np.nan
    clf, _, val = A.probe_fit_select(F[tr], y[tr], 0)
    CC_DIAG[ds] = float(val)  # pool inner-CV AUROC: a high pool fit with a below-chance test = candidate-identity leakage
    return A.auroc(y[te], clf.decision_function(F[te]))


CC_DIAG: dict[str, float] = {}


def _load_wu(P: A.Paths) -> dict | None:
    f = P.cache / "jlens_terms" / "jterms_wu_rows.npz"
    if not f.exists():
        return None
    z = np.load(f)
    row = dict(zip(z["token_ids"].tolist(), z["rows"].astype(np.float32)))
    return {"row": row, "c0": dict(zip(z["items"].tolist(), z["c0_ids"].tolist())), "c1": dict(zip(z["items"].tolist(), z["c1_ids"].tolist()))}


def diff_ci(a: pd.Series, b: pd.Series, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """mean(a) − mean(b), two-stage clustered bootstrap (clusters → facts) within each group (§15 a)."""
    rng = np.random.default_rng(seed)
    a, b = a.dropna(), b.dropna()

    def groups(s):
        return [np.array(v) for v in s.groupby(s.index.map(cluster_of)).apply(list)]

    ga, gb = groups(a), groups(b)

    def draw(G):
        pick = [G[i][rng.integers(0, len(G[i]), len(G[i]))] for i in rng.integers(0, len(G), len(G))]
        return np.concatenate(pick).mean()

    bs = np.array([draw(ga) - draw(gb) for _ in range(n_boot)])
    return float(a.mean() - b.mean()), *np.percentile(bs, [2.5, 97.5]).tolist()


def topk_precision(P: A.Paths, items: pd.DataFrame) -> list[str]:
    """§15 (b) from the pod's top-10 lists; descriptive."""
    d = P.cache / "jlens_terms"
    f = d / "jterms_topk.jsonl"
    L = ["", "## (b) Hypothesis-generation precision (descriptive)", ""]
    if not f.exists():
        return L + ["Pod rows (`jlens_terms_pod.py`) not on disk yet; requested from chat 6 (Guiv chose the pod route, 2026-10-19)."]
    tk = A.read_jsonl(f)
    wu = np.load(d / "jterms_wu_rows.npz")
    c0 = dict(zip(wu["items"], wu["c0_ids"]))
    c1 = dict(zip(wu["items"], wu["c1_ids"]))
    lab = dict(zip(items.item_id, items.label))
    rows = []
    for r in tk.itertuples(index=False):
        if r.item_id == "__mean__":
            continue
        y = lab.get(r.item_id)
        if y is None or r.item_id not in c0:
            continue
        truth, dis = (c0[r.item_id], c1[r.item_id]) if y == 1 else (c1[r.item_id], c0[r.item_id])
        for K in (5, 10):
            top = set(r.topk_ids[:K])
            rows.append({"dataset": r.dataset, "layer": r.layer, "position": r.position, "control": r.control, "seed": r.seed, "K": K,
                         "hit": int(truth in top), "fp": int(dis in top)})
    # state-free: one list per dataset × layer × position, scored against every test item's truth
    sf = tk[tk.item_id == "__mean__"]
    for r in sf.itertuples(index=False):
        for iid in items[(items.dataset == r.dataset) & (items.split == "test")].item_id:
            if iid not in c0:
                continue
            y = lab[iid]
            truth, dis = (c0[iid], c1[iid]) if y == 1 else (c1[iid], c0[iid])
            for K in (5, 10):
                top = set(r.topk_ids[:K])
                rows.append({"dataset": r.dataset, "layer": r.layer, "position": r.position, "control": "state_free", "seed": None, "K": K,
                             "hit": int(truth in top), "fp": int(dis in top)})
    h = pd.DataFrame(rows)
    h["group"] = h.dataset.map(workspace_group)
    _ct.annotate(h, P.results / "jlens_terms_topk.csv").to_csv(P.results / "jlens_terms_topk.csv", index=False)  # checkpoint_tier column (BRIEF_RP §0)
    L += ["hit@K = share of items whose J-lens top-K contains the true bridge / target's first token; precision@K = hit@K / K; "
          "FPR@K = share whose top-K contains the distractor's first token. Controls: random-rotation J-lens (5 seeds pooled) and the "
          "dataset-mean state. 'generates' = J-lens hit@K Wilson CI above both controls' CIs (descriptive flag).", ""]
    for (grp, pos, K), g in h.groupby(["group", "position", "K"]):
        L += [f"**{grp} — {pos} token, K = {K}**", "", "| layer | J-lens hit@K [Wilson] | precision@K | FPR@K | rotation hit@K | state-free hit@K | generates |",
              "|---|---|---|---|---|---|---|"]
        for Ly, gl in g.groupby("layer"):
            cells = {c: gl[gl.control == c] for c in ("jlens", "rot", "state_free")}
            w = {c: wilson(int(v.hit.sum()), len(v)) if len(v) else (np.nan,) * 3 for c, v in cells.items()}
            fpr = cells["jlens"].fp.mean() if len(cells["jlens"]) else np.nan
            gen = all(np.isfinite([w["jlens"][1], w[c][2]]).all() and w["jlens"][1] > w[c][2] for c in ("rot", "state_free"))
            L.append(f"| {Ly} | {w['jlens'][0]:.3f} [{w['jlens'][1]:.3f}, {w['jlens'][2]:.3f}] | {w['jlens'][0] / K:.3f} | {I.fmt(fpr)} | "
                     f"{I.fmt(w['rot'][0])} | {I.fmt(w['state_free'][0])} | {'yes' if gen else ''} |")
        L.append("")
    return L


def main(argv: list[str] | None = None) -> int:
    A.PROVENANCE.update(strict=True, extra_pods=set(), dropped={}, off_bank={})
    P = A.Paths()
    items = _items(P)
    excl = I.LABEL_DEFECT | LA.flagged_set(P)
    tag = dict(zip(items.dataset, items.tag))
    per_item = dict(zip(items.dataset, items.per_item))
    wu = _load_wu(P)
    pl = per_layer_auroc(P, items)
    pl["tag"] = pl.dataset.map(tag)
    pl["group"] = [("workspace" if workspace_group(d) else ("classification" if tag.get(d) in CLASS_TAGS else None)) for d in pl.dataset]
    _ct.annotate(pl, P.results / "jlens_terms_layers.csv").to_csv(P.results / "jlens_terms_layers.csv", index=False)  # checkpoint_tier column (BRIEF_RP §0)
    j42 = pl[(pl.reader == "jlens") & (pl.layer == 42)].set_index("dataset").auroc
    grp_of = dict(zip(pl.dataset, pl.group))
    facts = [d for d in j42.index if isinstance(grp_of.get(d), str)]  # NaN groups (other tags) are not in §15's two groups
    lc = pd.read_csv(P.results / "learning_curves.csv") if (P.results / "learning_curves.csv").exists() else pd.DataFrame()
    ra_probe = (lc[(lc.layer == 42) & (lc.render == "chat") & (lc.n_req == lc.n_req.max())].groupby("dataset").test_auc.median()
                if len(lc) else pd.Series(dtype=float))  # R-A: R1's probe(512), as in interim.md
    rows = []
    for d in facts:
        grp = "workspace" if workspace_group(d) else "classification"
        ref = cc_probe(P, items, d, wu) if per_item.get(d) else (float(ra_probe[d]) if d in ra_probe.index else probe512(P, items, d))
        rows.append({"dataset": d, "group": grp, "sub": workspace_group(d) or tag.get(d), "per_item_candidates": bool(per_item.get(d)),
                     "jlens42": float(j42[d]), "present42": ref, "reference": "probe(512)" if not per_item.get(d) else ("candidate-contrast" if wu else "candidate-contrast (pending pod rows)"),
                     "ratio": float(j42[d] / ref) if ref == ref and ref > 0 else np.nan})
    fa = pd.DataFrame(rows)
    fa["cc_pool_cv_auroc"] = fa.dataset.map(CC_DIAG)
    fa["cc_leak"] = (fa.cc_pool_cv_auroc > 0.7) & (fa.present42 < 0.5)
    _ct.annotate(fa, P.results / "jlens_terms_ratio.csv").to_csv(P.results / "jlens_terms_ratio.csv", index=False)  # checkpoint_tier column (BRIEF_RP §0)
    L = ["# BRIEF_R §15 — J-lens on its own terms (WS3)", "",
         "Pre-registered 2026-10-19 before computing (BRIEF_R §15). Primary = without LABEL_DEFECT ∪ audit-flagged; all-facts in parentheses.", ""]
    L += ["## (a) J-lens / PRESENT AUROC ratio at block 42 (chat): workspace vs classification", ""]
    for label, sel in (("primary (without defect ∪ flagged)", ~fa.dataset.isin(excl)), ("all facts", fa.dataset.notna())):
        f2 = fa[sel & fa.ratio.notna()]
        ws, cl = f2[f2.group == "workspace"].set_index("dataset").ratio, f2[f2.group == "classification"].set_index("dataset").ratio
        if len(ws) >= 2 and len(cl) >= 2:
            d, lo, hi = diff_ci(ws, cl)
            v = "SUPPORTED" if lo > 0 else ("REFUTED" if hi < 0 else "UNDERPOWERED")
            wsf = f2[f2.group == "workspace"]
            restricted = ("workspace facts with a defined reference: " + ", ".join(f"{s_} {n_}" for s_, n_ in wsf["sub"].value_counts().sort_index().items())
                          + f" (references: {', '.join(sorted(wsf.reference.unique()))})")
            L.append(f"- **{label}:** workspace mean ratio {ws.mean():.3f} (n = {len(ws)}) − classification {cl.mean():.3f} (n = {len(cl)}) = "
                     f"{d:+.3f} [{lo:+.3f}, {hi:+.3f}] (clustered) → **{v}** — {restricted}.")
            icl = f2[f2["sub"] == "ICL task identity"]
            rest = f2[(f2.group == "workspace") & (f2["sub"] != "ICL task identity")].set_index("dataset").ratio
            if len(icl) and len(rest) >= 2:
                d2, lo2, hi2 = diff_ci(rest, cl)
                L.append(f"  - sensitivity (not the verdict): without the ceiling-bound ICL facts, workspace {rest.mean():.3f} (n = {len(rest)}) − "
                         f"classification = {d2:+.3f} [{lo2:+.3f}, {hi2:+.3f}]")
    cc = fa[fa.reference == "candidate-contrast"]
    if len(cc):
        L += ["", f"**Reference validity (diagnostic; BRIEF_R §15 Deviations):** the candidate-contrast probe's test AUROC is below chance on "
              f"{int((cc.present42 < 0.5).sum())}/{int(cc.present42.notna().sum())} per-item facts; on {int(cc.cc_leak.sum())} of them its pool "
              "inner-CV AUROC is > 0.7, i.e. it learns candidate identity on the pool (h ⊙ (W_U[c0] − W_U[c1]) ≈ a candidate code) and the "
              "association inverts on the test pairings. The per-item component of (a) therefore measures that leakage, not the J-lens; "
              "only the probe(512) part (ICL, near ceiling) is interpretable."]
        L += ["", "| fact | J-lens@42 | candidate-contrast test | pool inner-CV | leak |", "|---|---|---|---|---|"] + [
            f"| {r.dataset} | {r.jlens42:.3f} | {I.fmt(r.present42)} | {I.fmt(r.cc_pool_cv_auroc)} | {'yes' if r.cc_leak else ''} |" for r in cc.itertuples()]
    pend = fa[fa.per_item_candidates & fa.present42.isna()]
    L += ["", f"Per-item-candidate workspace facts awaiting the candidate-contrast reference: {len(pend)} "
          f"(J-lens@42 AUROC median {pend.jlens42.median():.3f})." if len(pend) else ""]
    L += ["", "| group | sub-group | facts | J-lens@42 AUROC (median) | PRESENT@42 (median) | ratio (median) |", "|---|---|---|---|---|---|"]
    for (g, s), gg in fa[~fa.dataset.isin(excl)].groupby(["group", "sub"]):
        L.append(f"| {g} | {s} | {len(gg)} | {gg.jlens42.median():.3f} | {I.fmt(gg.present42.median())} | {I.fmt(gg.ratio.median())} |")
    # (c)
    L += ["", "## (c) J-lens − logit lens AUROC gap by group and block (chat; descriptive)", "",
          "| group | " + " | ".join(map(str, LAYERS)) + " |", "|---|" + "---|" * len(LAYERS)]
    piv = pl[~pl.dataset.isin(excl)].pivot_table(index=["dataset", "layer"], columns="reader", values="auroc").reset_index()
    if {"jlens", "logit_lens"} <= set(piv.columns):
        piv["gap"] = piv.jlens - piv.logit_lens
        piv["group"] = piv.dataset.map(lambda d: workspace_group(d) or ("classification" if tag.get(d) in CLASS_TAGS else "other"))
        piv = piv[piv.group != "other"]
        for g, gg in piv.groupby("group"):
            m = gg.groupby("layer").gap.mean()
            L.append(f"| {g} ({gg.dataset.nunique()} facts) | " + " | ".join(I.fmt(m.get(Ly), 3) for Ly in LAYERS) + " |")
        g42 = piv[(piv.layer == 42) & piv.gap.notna()].assign(ws=lambda x: x.group != "classification")
        w, c = g42[g42.ws].set_index("dataset").gap, g42[~g42.ws].set_index("dataset").gap
        if len(w) >= 2 and len(c) >= 2:
            d, lo, hi = diff_ci(w, c)
            L += ["", f"At block 42: workspace gap {w.mean():+.3f} (n = {len(w)}) vs classification {c.mean():+.3f} (n = {len(c)}); "
                  f"difference {d:+.3f} [{lo:+.3f}, {hi:+.3f}] (clustered; descriptive)."]
    L += topk_precision(P, items)
    (P.results / "jlens_terms.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(x for x in L if x.startswith("- **") or x.startswith("At block 42")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
