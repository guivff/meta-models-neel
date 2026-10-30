"""H3 (secondary: §14 paraphrase key) — the probe-lead clause (BRIEF_R §1 H3, §4.3, §14). The PRESENT reference is a probe
trained on pool items labelled by the §4.9 f key (``h3_para/model_key.PARA.jsonl``), at each block 24–60 (chat), scored
on test items against the key: its first layer with AUROC ≥ 0.75 (L_probe). For each fact and lens reader, the layer at
which the §4.3 verdict crosses from READS THE TEXT to READS THE MODEL (L_cross; first MODEL layer after a TEXT layer,
undefined otherwise) is taken from WS3's R3 on the key. Lead = L_cross − L_probe; the clause is "the probe leads by ≥ 4
layers" for the median fact with a defined lead.
# RULE: four-way at threshold 4 with margin ±1 block (H4's lag margin; §4.9 d gives none for the lead), fact-bootstrap
# CI of the median, and the share of facts with a defined crossing is reported next to it.

    python -m projects.g_agreement.r_bench.h3_probe --n-jobs 8      # → results/g_agreement/r/h3_probe_lead.csv
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import checkpoint_tier as _ct

LAYERS = (24, 28, 32, 36, 38, 40, 42, 44, 48, 52, 56, 60)


def _probe_curve(P: A.Paths, items: pd.DataFrame, key: dict, ds: str) -> list[dict]:
    out = []
    for L in LAYERS:
        try:
            X, idx = A.load_states(P, ds, "chat", L)
        except (FileNotFoundError, ValueError, OSError):
            continue
        it = items[items.dataset == ds].set_index("item_id")
        keep = [k for k, iid in enumerate(idx) if iid in it.index and iid in key]
        ids = [idx[k] for k in keep]
        y = np.array([int(key[i]) for i in ids])
        split = it.loc[ids, "split"].values
        tr, te = split == "pool", split == "test"
        if tr.sum() < 10 or te.sum() < 10 or len(set(y[tr])) < 2 or len(set(y[te])) < 2:
            continue
        clf, _, _ = A.probe_fit_select(X[keep][tr], y[tr], 0)
        out.append({"dataset": ds, "layer": L, "probe_auroc_vs_key": A.auroc(y[te], clf.decision_function(X[keep][te])), "n_test": int(te.sum())})
    return out


def main(argv: list[str] | None = None) -> int:
    from joblib import Parallel, delayed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-jobs", type=int, default=8)
    a = ap.parse_args(argv)
    A.PROVENANCE.update(strict=True, extra_pods=set(), dropped={}, off_bank={})
    P = A.Paths()
    items, _ = A.load_bank(P)
    f = P.cache / "h3_para" / "model_key.PARA.jsonl"
    kd = A.read_jsonl(f)
    key = dict(zip(kd.item_id, kd.key_model_pos.astype(bool)))
    res = Parallel(n_jobs=a.n_jobs)(delayed(_probe_curve)(P, items, key, ds) for ds in sorted(items.dataset.unique()))
    df = pd.DataFrame([r for rr in res for r in rr])
    out = P.results / "h3_probe_curve.csv"
    _ct.annotate(df.assign(reader="probe"), out).to_csv(out, index=False)
    print(f"[h3 probe] {len(df)} (fact, layer) cells over {df.dataset.nunique()} facts → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
