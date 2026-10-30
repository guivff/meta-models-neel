"""CI-10 (BRIEF_R §14 extras; rows from the text-arm chat in cache/g_agreement/r/h3_para/ci10_{lo,po}.PARA.jsonl): readers
scored on fact g's states with fact f's candidates, against g's labels. Rule, verbatim from §14: a cell is CROSS-FACT iff
|AUROC − 0.5| ≥ 0.15 with item-bootstrap 95% CI excluding 0.5; the claim holds iff the Wilson CI of the reader's
cell fraction excludes 0.20 from below AND the reader fraction exceeds the prompt-only fraction (paired sign test over
pairs, p < 0.05). A cell whose f-probe on g's states is itself CROSS-FACT is "state-borne" and excluded.
# RULE: the f-probe is probe(512) fitted on f's pool states at the reader's own layer (J-lens 42, Oracle 44), chat render,
# C by inner CV, applied to g's test states at that layer; the sign test is one-sided on the discordant pairs.

    python -m projects.g_agreement.r_bench.ci10          # → results/g_agreement/r/ci10.csv, ci10.md
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from common.stats import wilson
from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import checkpoint_tier as _ct
from projects.g_agreement.r_bench import interim as I


def _cross(y: np.ndarray, s: np.ndarray, seed: int = 0) -> tuple[float, float, float, bool]:
    a, lo, hi = A.auroc_ci(y, s, n_boot=1000, seed=seed)
    return a, lo, hi, bool(abs(a - 0.5) >= 0.15 and (lo > 0.5 or hi < 0.5))


def _fprobe(P: A.Paths, items: pd.DataFrame, f: str, g: str, layer: int, g_ids: list[str], y_g: np.ndarray) -> tuple:
    try:
        Xf, idf = A.load_states(P, f, A.PRIMARY_RENDER, layer)
        Xg, idg = A.load_states(P, g, A.PRIMARY_RENDER, layer)
    except (FileNotFoundError, ValueError, OSError):
        return (np.nan, np.nan, np.nan, None)
    itf = items[items.dataset == f].set_index("item_id").loc[idf]
    pool = np.where(itf.split.values == "pool")[0]
    clf, _, _ = A.probe_fit_select(Xf[pool], itf.label.values.astype(int)[pool], 0)
    pos = {iid: k for k, iid in enumerate(idg)}
    keep = [k for k, iid in enumerate(g_ids) if iid in pos]
    return _cross(y_g[keep], clf.decision_function(Xg[[pos[g_ids[k]] for k in keep]]))


def main(argv: list[str] | None = None) -> int:
    A.PROVENANCE.update(strict=True, extra_pods=set(), dropped={}, off_bank={})
    P = A.Paths()
    items, _ = A.load_bank(P)
    sided = dict(zip(items.dataset, items.sided))
    d = P.cache / "h3_para"
    lo = A.provenance_filter(A.read_jsonl(d / "ci10_lo.PARA.jsonl"), d / "ci10_lo.PARA.jsonl", "reader_lo", side_pods=I.PARA_PODS, side_shas=I.PARA_SHAS)
    po = A.provenance_filter(A.read_jsonl(d / "ci10_po.PARA.jsonl"), d / "ci10_po.PARA.jsonl", "prompt_only", side_pods=I.PARA_PODS, side_shas=I.PARA_SHAS)
    lo = lo[lo.get("unscorable", False) != True]  # noqa: E712
    rows = []
    for (f, g), gp in po.groupby(["f_dataset", "g_dataset"]):
        y = gp.label_g.values.astype(int)
        a, l, h, c = _cross(y, gp["lo"].values)
        rows.append({"f": f, "g": g, "f_tag": gp.f_tag.iloc[0], "g_tag": gp.g_tag.iloc[0], "method": "prompt_only", "layer": np.nan,
                     "auroc": a, "ci_lo": l, "ci_hi": h, "cross_fact": c, "state_borne": False})
    for (f, g, rd, L_), gr in lo.groupby(["f_dataset", "g_dataset", "reader", "layer"]):
        y = gr.label_g.values.astype(int)
        s = (gr["lo"] if sided.get(f) == "two" else gr["lp_A"]).values.astype(float)
        a, l, h, c = _cross(y, s)
        pa, pl, ph, pc = _fprobe(P, items, f, g, int(L_), gr.item_id.tolist(), y)
        rows.append({"f": f, "g": g, "f_tag": gr.f_tag.iloc[0], "g_tag": gr.g_tag.iloc[0], "method": rd, "layer": int(L_),
                     "auroc": a, "ci_lo": l, "ci_hi": h, "cross_fact": c, "fprobe_auroc": pa, "state_borne": bool(pc)})
    df = pd.DataFrame(rows)
    _ct.annotate(df, P.results / "ci10.csv").to_csv(P.results / "ci10.csv", index=False)  # checkpoint_tier column (BRIEF_RP §0)
    pof = df[df.method == "prompt_only"].set_index(["f", "g"]).cross_fact
    L = ["# CI-10 — readers on another fact's states (BRIEF_R §14 extras; secondary, exploratory weight)", "",
         f"{df[df.method == 'prompt_only'].shape[0]} (f, g) pairs; CROSS-FACT iff |AUROC − 0.5| ≥ 0.15 with item-bootstrap CI excluding 0.5; "
         "state-borne cells (f-probe on g's states also cross-fact) excluded; claim iff Wilson lower > 0.20 and reader > prompt-only "
         "(one-sided sign test over pairs, p < 0.05).", "",
         f"prompt-only: {int(pof.sum())}/{len(pof)} pairs cross-fact.", "",
         "| reader | layer | pairs (after state-borne exclusion) | cross-fact | fraction [Wilson] | reader-only / prompt-only-only pairs | sign-test p | claim |",
         "|---|---|---|---|---|---|---|---|"]
    for (rd, L_), g in df[df.method != "prompt_only"].groupby(["method", "layer"]):
        k = g[~g.state_borne]
        n, x = len(k), int(k.cross_fact.sum())
        p_, l_, h_ = wilson(x, n)
        pp = pof.reindex(list(zip(k.f, k.g))).values.astype(bool)
        r = k.cross_fact.values.astype(bool)
        b, c = int((r & ~pp).sum()), int((~r & pp).sum())
        pval = binomtest(b, b + c, 0.5, alternative="greater").pvalue if b + c else 1.0
        claim = bool(l_ > 0.20 and p_ > pp.mean() and pval < 0.05)
        L.append(f"| {rd} | {L_} | {n} ({int(g.state_borne.sum())} state-borne) | {x} | {p_:.2f} [{max(0, l_):.2f}, {h_:.2f}] | {b} / {c} | {pval:.3f} | "
                 f"{'HOLDS' if claim else 'does not hold'} |")
    L += ["", "Cells (reader rows):", "", "| f → g | tags | reader | AUROC [CI] | cross-fact | f-probe on g | state-borne |", "|---|---|---|---|---|---|---|"]
    for r in df[df.method != "prompt_only"].sort_values(["method", "f"]).itertuples():
        L.append(f"| {r.f} → {r.g} | {r.f_tag}→{r.g_tag} | {r.method}@{r.layer} | {r.auroc:.3f} [{r.ci_lo:.3f}, {r.ci_hi:.3f}] | "
                 f"{'yes' if r.cross_fact else ''} | {I.fmt(r.fprobe_auroc)} | {'yes' if r.state_borne else ''} |")
    (P.results / "ci10.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[6:6 + 4 + df[df.method != 'prompt_only'].groupby(['method', 'layer']).ngroups]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
