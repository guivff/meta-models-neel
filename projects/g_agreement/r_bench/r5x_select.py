"""R5X stratum S2 selection (BRIEF_R "WS4 / R5X", pre-registered 2026-10-19 17:03Z; WS3 selects). 10 moderate-confidence
facts: prompt-only AUROC in [0.70, 0.85] and probe(512) ≥ 0.9, BOTH on pool only (§4.9 e): prompt-only on the 64
POOL_EVAL items, probe(512) by inner CV on the pool (``analyze.pool_probe_auroc``). Written in ``r5_selection.json``'s
schema to ``results/g_agreement/r/r5x_selection.json``; directions (d_cm / d_probe at blocks 38 and 42 from the pool
states) to ``<root>/.ws3_cache/r5x/directions/`` for WS4 to stage (WS3 never writes cache/…/r5x/).
# RULE (written before the selection was computed; BRIEF_R Deviations, WS3): the pre-registration does not say which 10
# to take when more than 10 qualify. They are ranked by pool probe AUROC (descending: the most linearly present), ties by
# |prompt-only − 0.775| (the band centre). With fewer than 10 qualifying, the remainder are the nearest to the band
# (distance of prompt-only to [0.70, 0.85]) among facts with probe ≥ 0.9, realised values reported per fact. Inspected
# label defects (interim.LABEL_DEFECT) are excluded; audit-flagged facts that are not defects stay eligible.

    python -m projects.g_agreement.r_bench.r5x_select --n-jobs 8
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd

from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import interim as I

LO_BAND, HI_BAND, PROBE_MIN, N_FACTS, N_ITEMS = 0.70, 0.85, 0.9, 10, 32
# WS4 amendment 720144b (2026-10-19 17:17Z): S2 = the small-margin stratum. Rank the ten smallest pool_median_abs_lo among
# facts with pool probe ≥ 0.9, excluding the 30 S1 facts and the R3 conflict population; ties by higher pool probe, then
# dataset id ascending; shortfall → take all eligible. Applied over ALL facts (the rule names no LABEL_DEFECT exclusion);
# the LABEL_DEFECT-excluded alternative is computed and reported, never substituted.
R3_POPULATION = {"131_temp_cat_Typical Time", "142_cancer_cat_Thyroid_Cancer", "144_cancer_cat_Colon_Cancer"}


def main(argv: list[str] | None = None) -> int:
    from joblib import Parallel, delayed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-jobs", type=int, default=8)
    a = ap.parse_args(argv)
    A.PROVENANCE.update(strict=True, extra_pods=set(), dropped={}, off_bank={})
    P = A.Paths()
    items, _ = A.load_bank(P)
    po = A.read_jsonl_shards(P.cache, "prompt_only")
    dss = [d for d in sorted(items.dataset.unique()) if (P.cache / "states" / d / f"chat_L{A.L_READ}.npy").exists()]
    model = {}
    for d in dss:
        g = po[po.item_id.isin(set(A.pool_eval_ids(items, d))) & po["lo"].notna()]
        if len(g) >= 10 and g.label.nunique() == 2:
            model[d] = A.auroc(g.label.values, g["lo"].values)
    probe = dict(zip(dss, Parallel(n_jobs=a.n_jobs)(delayed(A.pool_probe_auroc)(P, items, d) for d in dss)))
    tab = pd.DataFrame({"dataset": dss, "prompt_only_pool": [model.get(d, np.nan) for d in dss], "probe_pool": [probe[d] for d in dss]})
    pool_ids = set(items[items.split == "pool"].item_id)
    gp = po[po.item_id.isin(pool_ids) & po["lo"].notna()].drop_duplicates("item_id", keep="last")
    mg = gp.assign(alo=gp["lo"].abs()).groupby("dataset").agg(pool_median_abs_lo=("alo", "median"),
                                                               pool_q25_abs_lo=("alo", lambda s_: s_.quantile(0.25)), pool_n=("alo", "size"))
    tab = tab.merge(mg, left_on="dataset", right_index=True, how="left")
    sel = json.loads((P.results / "r5_selection.json").read_text())
    s1 = set(sel["datasets"])
    # WS4 clarification c58c6e3: LABEL_DEFECT facts are excluded too (membership unaffected: their pool margins are 6.88–8.50)
    elig = tab[(tab.probe_pool >= PROBE_MIN) & ~tab.dataset.isin(s1) & ~tab.dataset.isin(R3_POPULATION) & ~tab.dataset.isin(I.LABEL_DEFECT)
               & tab.pool_median_abs_lo.notna()]
    ranked = elig.assign(neg_probe=-elig.probe_pool).sort_values(["pool_median_abs_lo", "neg_probe", "dataset"])
    chosen = ranked.head(N_FACTS).assign(selected_by="margin rank (WS4 720144b)")
    alt = ranked[~ranked.dataset.isin(I.LABEL_DEFECT)].head(N_FACTS)  # comparison only
    tab["eligible"] = tab.dataset.isin(set(elig.dataset))
    out = {"created": pd.Timestamp.utcnow().isoformat(), "stratum": "S2, the small-margin stratum (R5X, WS4 amendment 720144b)",
           "select_on": "pool", "rule": "ten smallest pool_median_abs_lo; probe ≥ 0.9; S1 and 131/142/144 excluded; ties: higher probe, dataset id",
           "probe_min": PROBE_MIN, "n_candidates": int(len(tab)), "n_eligible": int(len(elig)), "n_selected": int(len(chosen)),
           "overlap_with_r5_S1": sorted(set(chosen.dataset) & s1),
           "label_defects_among_selected": sorted(set(chosen.dataset) & I.LABEL_DEFECT),
           "same_ten_if_LABEL_DEFECT_excluded": sorted(alt.dataset) == sorted(chosen.dataset),
           "realised_band": [float(chosen.pool_median_abs_lo.min()), float(chosen.pool_median_abs_lo.max())],
           "next_outside": ranked.iloc[N_FACTS:N_FACTS + 2][["dataset", "pool_median_abs_lo", "probe_pool"]].round(3).values.tolist(), "datasets": {}}
    ddir = P.root / ".ws3_cache" / "r5x" / "directions"
    ddir.mkdir(parents=True, exist_ok=True)
    for r in chosen.itertuples():
        ds = r.dataset
        it = items[(items.dataset == ds) & (items.split == "test")]
        pos = it[it.label == 1].item_id.tolist()[: N_ITEMS // 2]
        neg = it[it.label == 0].item_id.tolist()[: N_ITEMS // 2]
        dirs, scale = {}, None
        for L in (A.L_EDIT, A.L_READ):
            X, idx = A.load_states(P, ds, A.PRIMARY_RENDER, L)
            iti = items[items.dataset == ds].set_index("item_id").loc[idx]
            y, split = iti.label.values.astype(int), iti.split.values
            pool = np.where(split == "pool")[0]
            d_cm = X[pool][y[pool] == 1].mean(0) - X[pool][y[pool] == 0].mean(0)
            if L == A.L_EDIT:
                scale = float(np.linalg.norm(d_cm))
            dirs[f"d_cm_L{L}"] = (d_cm / (np.linalg.norm(d_cm) + 1e-9)).astype(np.float32)
            clf, _, _ = A.probe_fit_select(X[pool], y[pool], 0)
            w = clf[-1].coef_[0] / clf[0].scale_
            dirs[f"d_probe_L{L}"] = (w / (np.linalg.norm(w) + 1e-9)).astype(np.float32)
        np.savez(ddir / f"{ds}.npz", **dirs)
        out["datasets"][ds] = {"item_ids": pos + neg, "scale": scale, "probe_auroc": float(r.probe_pool), "prompt_only_auroc": float(r.prompt_only_pool),
                               "pool_median_abs_lo": float(r.pool_median_abs_lo), "pool_q25_abs_lo": float(r.pool_q25_abs_lo), "pool_n": int(r.pool_n),
                               "selected_by": r.selected_by, "cos_cm_probe_L38": float(dirs[f"d_cm_L{A.L_EDIT}"] @ dirs[f"d_probe_L{A.L_EDIT}"])}
    out["directions_dir"] = str(ddir)
    (P.results / "r5x_selection.json").write_text(json.dumps(out, indent=1))
    tab.to_csv(P.results / "r5x_candidates.csv", index=False)
    print(json.dumps({k: v for k, v in out.items() if k != "datasets"}, indent=1))
    for ds, v in out["datasets"].items():
        print(f"{ds}: margin {v['pool_median_abs_lo']:.2f} (q25 {v['pool_q25_abs_lo']:.2f}, n {v['pool_n']}), probe {v['probe_auroc']:.3f}, prompt-only {v['prompt_only_auroc']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
