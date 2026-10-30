"""Uniform label-defect audit trigger (BRIEF_R Deviations, WS3, 2026-10-19; Guiv's instruction): every fact of every bank
whose prompt-only AUROC < 0.5, or whose prompt-only greedy accuracy is below chance (0.5 two-/one-sided, 1/k k-way),
is FLAGGED, gets an inspection packet (test texts per label with the model's pick, and the parent's texts per class
where one exists) and is reported both ways (with / without the flagged set) in every WS3 table. Point estimates, as the
trigger is worded. Inspection outcomes are recorded in ``INSPECTED``; only facts inspected and found to be a label
defect join ``interim.LABEL_DEFECT`` and leave the BH families; a flagged fact found not to be a defect stays in the BH
families of the "all facts" tables and is reported both ways.

    python -m projects.g_agreement.r_bench.label_audit        # → results/g_agreement/r/label_audit.csv, label_audit.md
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import checkpoint_tier as _ct

BANKS = {"R-A": ("items_r.json",), "R-B": ("items_rk.json",), "R-E": ("items_re.json",), "ReaderBench": ("items_rb.json", "items_rbk.json"),
         "R-X": ("items_rx.json",)}

# inspection outcomes (WS3 CPU checks; evidence in BRIEF_R Deviations and HANDOFF)
INSPECTED: dict[str, tuple[str, str]] = {
    "139_news_class_Politics": ("defect", "AG News names swapped (WS9 Check 1)"),
    "140_news_class_Technology": ("defect", "AG News names swapped (WS9 Check 1)"),
    "141_news_class_Entertainment": ("defect", "AG News names swapped (WS9 Check 1)"),
    "97_news_class": ("defect", "AG News names swapped (WS9 Check 1)"),
    "145_disease_class_digestive system diseases": ("defect", "101_disease_class names permuted (WS3)"),
    "146_disease_class_cardiovascular diseases": ("defect", "101_disease_class names permuted (WS3)"),
    "101_disease_class": ("defect", "101_disease_class names permuted (WS3)"),
    "153_it_tick_Administrative rights": ("not a defect", "classes match their texts; Qwen does not call OS-upgrade tickets 'administrative rights' (WS3)"),
    "131_temp_cat_Typical Time": ("not a defect", "labels match (time-of-day vs how long / how often); Qwen calls frequency questions 'typical time' (WS3)"),
    "142_cancer_cat_Thyroid_Cancer": ("not a defect", "98_cancer_cat classes match their names (thyroid terms 91% / colon 94% / lung 92%) but overlap heavily (WS3)"),
    "144_cancer_cat_Colon_Cancer": ("not a defect", "98_cancer_cat classes match their names but overlap heavily (colon abstracts mention lung 75%) (WS3)"),
    "rb_internal_puzzle_answer": ("not a defect", "by design: label = correct endpoint vs the 2-step endpoint; Qwen's errors are systematic (README) (WS3)"),
    "x25_wsb_wrong_bridge": ("not a defect", "external bridge annotation; the question asks the model to introspect which bridge it used (WS3)"),
}


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


def audit(P: A.Paths, po: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per bank × fact: prompt-only AUROC (two-/one-sided), greedy accuracy and chance on the test split; ``flagged``."""
    po = A.read_jsonl_shards(P.cache, "prompt_only") if po is None else po
    out = []
    for bank, files in BANKS.items():
        items = _bank(P, files)
        if items.empty or po.empty:
            continue
        test = items[items.split == "test"]
        g_all = po[po.item_id.isin(set(test.item_id))].drop_duplicates("item_id", keep="last")
        sided_of = dict(zip(items.dataset, items.sided))
        for ds, g in g_all.groupby("dataset"):
            sided = sided_of.get(ds)
            if sided == "kway":
                if "lp" not in g.columns or "greedy" not in g.columns:
                    continue
                g = g[g.lp.map(lambda v: isinstance(v, list))]
                if g.empty:
                    continue
                k = len(g.iloc[0].lp)
                acc, auc, chance = float((g.greedy.astype(int) == g.label.astype(int)).mean()), np.nan, 1 / k
            else:
                g = g[g["lo"].notna()]
                if len(g) < 10 or g.label.nunique() < 2:
                    continue
                auc = A.auroc(g.label.values.astype(int), g["lo"].values)
                acc = float((g.model_says_pos.astype(bool) == g.label.astype(bool)).mean()) if "model_says_pos" in g.columns else np.nan
                chance = 0.5
            flagged = bool((auc == auc and auc < 0.5) or (acc == acc and acc < chance))
            status, note = INSPECTED.get(ds, ("pending inspection", "") if flagged else ("not flagged", ""))
            out.append({"bank": bank, "dataset": ds, "tag": g.iloc[0].get("tag") if "tag" in g.columns else None, "sided": sided,
                        "n": len(g), "prompt_only_auroc": auc, "greedy_acc": acc, "chance": chance, "flagged": flagged,
                        "inspection": status, "note": note})
    return pd.DataFrame(out)


def flagged_set(P: A.Paths) -> set[str]:
    """The flagged facts, from the committed audit table when it exists (so every table uses one fixed list)."""
    f = P.results / "label_audit.csv"
    if f.exists():
        d = pd.read_csv(f)
        return set(d[d.flagged].dataset)
    return set()


def packet(P: A.Paths, ds: str, files: tuple[str, ...], po: pd.DataFrame, n: int = 6) -> list[str]:
    items = _bank(P, files)
    it = items[(items.dataset == ds) & (items.split == "test")]
    g = po[po.item_id.isin(set(it.item_id))].drop_duplicates("item_id", keep="last")
    m = it.merge(g[[c for c in ("item_id", "model_says_pos", "greedy") if c in g.columns]], on="item_id", how="left")
    L = [f"#### {ds}", "", f"question: {it.iloc[0].primary.get('question')!r}; candidates: {it.iloc[0].primary.get('candidates')}", ""]
    for lab, gg in m.groupby("label"):
        L.append(f"- label {lab}:")
        for r in gg.head(n).itertuples():
            pick = getattr(r, "greedy", None) if it.iloc[0].sided == "kway" else getattr(r, "model_says_pos", None)
            L.append(f"  - model pick {pick} | {str(r.prompt_text)[:140]!r}")
    return L + [""]


def main(argv: list[str] | None = None) -> int:
    A.PROVENANCE.update(strict=True, extra_pods=set(), dropped={}, off_bank={})
    P = A.Paths()
    po = A.read_jsonl_shards(P.cache, "prompt_only")
    d = audit(P, po)
    _ct.annotate(d, P.results / "label_audit.csv").to_csv(P.results / "label_audit.csv", index=False)  # checkpoint_tier column (BRIEF_RP §0)
    fl = d[d.flagged]
    L = ["# Label-defect audit (uniform trigger, BRIEF_R Deviations WS3 2026-10-19)", "",
         "Trigger: prompt-only AUROC < 0.5 or greedy accuracy below chance (0.5; 1/k for k-way), point estimates, test split. "
         "Every flagged fact is inspected (packet below) and reported both ways in every WS3 table; only inspected defects join "
         "LABEL_DEFECT and leave the BH families.", "",
         f"Facts audited: {len(d)} ({', '.join(f'{b} {int((d.bank == b).sum())}' for b in BANKS)}); flagged: {len(fl)}.", "",
         "| bank | fact | tag | prompt-only AUROC | greedy acc | chance | inspection | note |", "|---|---|---|---|---|---|---|---|"]
    for r in fl.sort_values(["bank", "dataset"]).itertuples():
        L.append(f"| {r.bank} | {r.dataset} | {r.tag} | {'—' if r.prompt_only_auroc != r.prompt_only_auroc else f'{r.prompt_only_auroc:.3f}'} | "
                 f"{r.greedy_acc:.3f} | {r.chance:.3f} | {r.inspection} | {r.note} |")
    L += ["", "## Inspection packets (facts flagged and not yet inspected)", ""]
    for r in fl[fl.inspection == "pending inspection"].itertuples():
        L += packet(P, r.dataset, BANKS[r.bank], po)
    (P.results / "label_audit.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"audited {len(d)}; flagged {len(fl)}: " + ", ".join(f"{r.dataset} [{r.inspection}]" for r in fl.itertuples()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
