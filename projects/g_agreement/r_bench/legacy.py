"""R-D: the legacy families (BRIEF_R.md §3 R-D, §3.2) mapped into the Phase R ``cells.csv`` schema so the published
X1 / Y1 / V1 / V7c / W2 numbers sit in F1/F3 next to the new facts. No model, no states: every row is a published
rate recomputed from its LO rows, with a Wilson 95% CI.

    python -m projects.g_agreement.r_bench.legacy --check              # prints the table and the missing sources
    python -m projects.g_agreement.r_bench.legacy --out results/g_agreement/r/cells_legacy.csv
    python -m projects.g_agreement.r_bench.analyze --with-legacy ...   # the single hook: cells += legacy_cells()

Row schema = cells.csv (dataset, tag, reader, layer, render, condition, auroc, ci_lo, ci_hi, n, coverage) plus
  metric        what ``auroc`` holds: pair_win | favours_actual | kway_exact  (never a genuine AUROC here)
  k_wins        the numerator of the rate; n the denominator (scored items / pairs); coverage = n / published total
  auroc_items   X1 only: the item-level AUROC of the reader's LO in version A's candidate order (two-sided s_diff)
  k             k-way families: the number of candidates (chance = 1 / k)
  family, set, source, legacy = True

Tags follow ``datasets.R_D_FAMILIES``: ownership / mapping / puzzle errors / self-choice / counts → INTERNAL,
language / tense → TOPIC, V7c private facts → CONTEXT. Sources that are absent are skipped and listed in ``missing``.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common.stats import wilson
from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench import datasets as D

RENDER = "chat"
TAG = {f: v["tag"] for f, v in D.R_D_FAMILIES.items()}
TAG.update({"error": "INTERNAL", "error_control": "INTERNAL", "disagree": "INTERNAL", "agree_control": "INTERNAL",
            "arith": "INTERNAL", "mapping8": "INTERNAL", "ownership4": "INTERNAL"})
SET_TOTALS = {"error": 297, "error_control": 103, "disagree": 165, "agree_control": 165}
SET_DATASET = {"error": "rd_puzzle_error", "error_control": "rd_puzzle_error_control", "disagree": "rd_choice_disagree",
               "agree_control": "rd_choice_agree_control"}
KWAY_FAMILIES = {"counts": ("rd_counts", 99, "chat"), "arith": ("rd_arith", 199, "plain"), "mapping8": ("rd_mapping8", 8, "chat"),
                 "ownership4": ("rd_ownership4", 4, "chat")}
COLUMNS = ["dataset", "tag", "reader", "layer", "render", "condition", "auroc", "ci_lo", "ci_hi", "n", "coverage",
           "metric", "k_wins", "auroc_items", "k", "family", "set", "source", "legacy"]


# ------------------------------------------------------------------ paths
def default_cache_dir() -> Path:
    """cache/g_agreement of this checkout, or of the enclosing main checkout when this is a .claude worktree (the cache
    is git-ignored and lives once, next to the main checkout)."""
    if (C.CACHE_DIR / "x").exists():
        return C.CACHE_DIR
    for parent in C.REPO_ROOT.parents:
        cand = parent / "cache" / "g_agreement"
        if (cand / "x").exists():
            return cand
    return C.CACHE_DIR


def default_results_dir() -> Path:
    if (C.RESULTS_DIR / "x1" / "e2.csv").exists():
        return C.RESULTS_DIR
    for parent in C.REPO_ROOT.parents:
        cand = parent / "results" / "g_agreement"
        if (cand / "x1" / "e2.csv").exists():
            return cand
    return C.RESULTS_DIR


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


# ------------------------------------------------------------------ rows
def _auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    from scipy.stats import rankdata

    pos, neg = labels == 1, labels == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    r = rankdata(scores)
    return float((r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def cell(dataset: str, tag: str, reader: str, layer: int, k_wins: int, n: int, n_total: int, metric: str, family: str, source: str,
         render: str = RENDER, set_: str | None = None, auroc_items: float = float("nan"), k: int | None = None,
         condition: str = "natural") -> dict[str, Any]:
    p, lo, hi = wilson(int(k_wins), int(n)) if n else (float("nan"),) * 3
    if n:
        lo, hi = min(float(lo), p), max(float(hi), p)   # k = n / k = 0: the Wilson bound rounds past the rate by 1e-16
    return {"dataset": dataset, "tag": tag, "reader": reader, "layer": int(layer), "render": render, "condition": condition,
            "auroc": p, "ci_lo": lo, "ci_hi": hi, "n": int(n), "coverage": (n / n_total) if n_total else float("nan"),
            "metric": metric, "k_wins": int(k_wins), "auroc_items": auroc_items, "k": k, "family": family, "set": set_,
            "source": source, "legacy": True}


def pair_win_rows(lo_by_item: dict[str, float], pairs: dict[str, dict[str, str]]) -> tuple[int, int, float]:
    """pairs: {pair_id: {"A": item_id, "B": item_id}}; lo_by_item: own-answer LO per scorable item. Returns
    (wins, scored pairs, item-level AUROC in version A's candidate order: score(A) = lo_A, score(B) = -lo_B)."""
    wins = n = 0
    scores, labels = [], []
    for pid, v in sorted(pairs.items()):
        a, b = lo_by_item.get(v["A"]), lo_by_item.get(v["B"])
        if a is None or b is None:
            continue
        n += 1
        wins += int(a + b > 0)
        scores += [a, -b]
        labels += [1, 0]
    return wins, n, _auroc(np.array(scores), np.array(labels)) if n else float("nan")


# ------------------------------------------------------------------ X1 (+ O44)
def x1_rows(cache: Path, results: Path, items_x: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    items_x = items_x or (C.DATASET_DIR / "items_x.json")
    missing: list[str] = []
    out: list[dict[str, Any]] = []
    if not items_x.exists() or not (cache / "x" / "x1_lo.jsonl").exists():
        return out, [str(items_x), str(cache / "x" / "x1_lo.jsonl")]
    pairs: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for it in json.loads(items_x.read_text())["items"]:
        if it["split"] == "test":
            pairs[it["family"]].setdefault(it["pair_id"], {})[it["version"]] = it["item_id"]
    sources = [("x1_lo", read_jsonl(cache / "x" / "x1_lo.jsonl"), 42)]
    o44 = cache / "w" / "o44" / "x1_lo44.jsonl"
    if o44.exists():
        sources.append(("o44", [r for r in read_jsonl(o44) if r.get("layer") == 44], 44))
    else:
        missing.append(str(o44))
    for src, rows, layer in sources:
        by: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
        for r in rows:
            if r.get("condition", "natural") != "natural" or r.get("unscorable") or r.get("lo") is None:
                continue
            by[(r["reader"], r["family"])][r["item_id"]] = float(r["lo"])
        for (reader, fam), lo_by_item in sorted(by.items()):
            wins, n, auc = pair_win_rows(lo_by_item, pairs[fam])
            out.append(cell(f"rd_x1_{fam}", TAG[fam], reader, layer, wins, n, len(pairs[fam]), "pair_win", fam, src, auroc_items=auc))
    e2 = results / "x1" / "e2.csv"
    if e2.exists():
        for r in pd.read_csv(e2).itertuples(index=False):
            out.append(cell(f"rd_x1_{r.family}", TAG[r.family], "probe", 42, int(r.loo_k), int(r.loo_n), int(r.n_pairs_total), "pair_win",
                            r.family, "x1/e2.csv (LOO)", auroc_items=float(r.loo_auroc)))
    else:
        missing.append(str(e2))
    return out, missing


# ------------------------------------------------------------------ V7c
def v7c_rows(cache: Path, items_v7c: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    items_v7c = items_v7c or (C.PROJECT_DIR / "banks" / "w" / "items_v7c.json")
    s3 = cache / "w" / "s3_lo.jsonl"
    if not items_v7c.exists() or not s3.exists():
        return [], [str(items_v7c), str(s3)]
    pairs_by_role: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for it in json.loads(items_v7c.read_text())["items"]:
        pairs_by_role[it["role"]].setdefault(it["pair_id"], {})[it["version"]] = it["item_id"]
    by: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for r in read_jsonl(s3):
        if r.get("family") != "v7" or not str(r.get("pair_id", "")).startswith("wv7c-") or r.get("unscorable") or r.get("lo_own") is None:
            continue
        by[(r["reader"], int(r["layer"]))][r["item_id"]] = float(r["lo_own"])
    out = []
    for (reader, layer), lo_by_item in sorted(by.items()):
        for role, pairs in sorted(pairs_by_role.items()):
            wins, n, auc = pair_win_rows(lo_by_item, pairs)
            out.append(cell(f"rd_v7c_{role}", TAG["v7c_private"], reader, layer, wins, n, len(pairs), "pair_win", "v7c_private",
                            "w/s3_lo.jsonl", set_=role, auroc_items=auc))
    return out, []


# ------------------------------------------------------------------ puzzle errors and self-choice (X3 @42, Y1 @42/48, V1 44–62)
def actual_rows(cache: Path, results: Path) -> tuple[list[dict[str, Any]], list[str]]:
    sources = [("x3_lo", cache / "x" / "x3_lo.jsonl"), ("y1_lo", cache / "y" / "y1_lo.jsonl"), ("s3v1_lo", cache / "w" / "s3v1_lo.jsonl")]
    missing = [str(p) for _, p in sources if not p.exists()]
    # one source per cell (reader, layer, set): the one with the most scored items, ties in the order x3, y1, s3v1 (the X3
    # choice rows are a 33/36-item subset under their own ids, so sources are never pooled inside a cell)
    per_src: dict[tuple[str, int, str], dict[str, dict[str, bool]]] = defaultdict(lambda: defaultdict(dict))
    for src, p in sources:
        if not p.exists():
            continue
        for r in read_jsonl(p):
            if r.get("unscorable") or r.get("favours_actual") is None or r.get("family") not in ("puzzle", "choice"):
                continue
            per_src[(r["reader"], int(r["layer"]), r["set"])][src][r["item_id"]] = bool(r["favours_actual"])
    order = [s for s, _ in sources]
    out = []
    for (reader, layer, set_), by_src in sorted(per_src.items()):
        src = max(by_src, key=lambda s: (len(by_src[s]), -order.index(s)))
        flags = by_src[src]
        out.append(cell(SET_DATASET[set_], TAG[set_], reader, layer, sum(flags.values()), len(flags), SET_TOTALS[set_], "favours_actual",
                        "puzzle_error" if set_.startswith("error") else "self_choice", src, set_=set_))
    # probe (E10, position 0 = last token) and logit-lens references per layer
    for set_, fn, ctrl in (("error", "sweep_error.csv", "error_control"), ("disagree", "sweep_disagree.csv", "agree_control")):
        p = results / "y1" / fn
        if not p.exists():
            missing.append(str(p))
            continue
        df = pd.read_csv(p)
        df = df[(df.position_rank == 0) & (df.set == set_) & (df.status == "ok")]
        for r in df.itertuples(index=False):
            out.append(cell(SET_DATASET[set_], TAG[set_], "probe", int(r.layer), int(r.k), int(r.n), SET_TOTALS[set_], "favours_actual",
                            "puzzle_error" if set_ == "error" else "self_choice", "y1/" + fn + " (E10 held-out)", set_=set_))
            if not np.isnan(r.control_rate):
                n_c = SET_TOTALS[ctrl]
                out.append(cell(SET_DATASET[ctrl], TAG[ctrl], "probe", int(r.layer), int(round(r.control_rate * n_c)), n_c, n_c, "favours_actual",
                                "puzzle_error" if set_ == "error" else "self_choice", "y1/" + fn + " (control_rate)", set_=ctrl))
    ll = results / "y1" / "logitlens.csv"
    if ll.exists():
        for r in pd.read_csv(ll).itertuples(index=False):
            if r.set in SET_DATASET and not bool(r.is_final_layer):
                out.append(cell(SET_DATASET[r.set], TAG[r.set], "logit_lens", int(r.layer), int(r.k_pos), int(r.n), SET_TOTALS[r.set], "favours_actual",
                                "puzzle_error" if r.set.startswith("error") else "self_choice", "y1/logitlens.csv", set_=r.set))
    else:
        missing.append(str(ll))
    return out, missing


# ------------------------------------------------------------------ W2 graded facts (k-way exact match of the native argmax)
def kway_rows(cache: Path) -> tuple[list[dict[str, Any]], list[str]]:
    s3 = cache / "w" / "s3_lo.jsonl"
    if not s3.exists():
        return [], [str(s3)]
    agg: dict[tuple[str, str, int], list[bool]] = defaultdict(list)
    model: dict[str, list[bool]] = defaultdict(list)
    for r in read_jsonl(s3):
        fam = r.get("family")
        if fam not in KWAY_FAMILIES or not str(r.get("unit", "")).startswith("S1"):
            continue
        if r.get("argmax") is not None:
            agg[(fam, r["reader"], int(r["layer"]))].append(str(r["argmax"]) == str(r["true_answer"]))
        if r.get("lp_candidates_all_model") and r.get("candidates") and r["reader"] == "jlens":   # one copy per item
            lp = r["lp_candidates_all_model"]
            model[fam].append(str(r["candidates"][int(np.argmax(lp))]) == str(r["true_answer"]))
    out = []
    for (fam, reader, layer), flags in sorted(agg.items()):
        ds, k, render = KWAY_FAMILIES[fam]
        n_total = {"counts": 600, "arith": 100, "mapping8": 94, "ownership4": 128}[fam]
        out.append(cell(ds, TAG.get(fam, "INTERNAL"), reader, layer, sum(flags), len(flags), n_total, "kway_exact", fam, "w/s3_lo.jsonl (S1)",
                        render=render, k=k))
    for fam, flags in sorted(model.items()):
        ds, k, render = KWAY_FAMILIES[fam]
        n_total = {"counts": 600, "arith": 100, "mapping8": 94, "ownership4": 128}[fam]
        out.append(cell(ds, TAG.get(fam, "INTERNAL"), "model_ft", 63, sum(flags), len(flags), n_total, "kway_exact", fam,
                        "w/s3_lo.jsonl lp_candidates_all_model", render=render, k=k))
    return out, []


# ------------------------------------------------------------------ assembly
def legacy_cells(cache_dir: Path | None = None, results_dir: Path | None = None) -> tuple[pd.DataFrame, list[str]]:
    """All R-D rows as a DataFrame in the cells.csv schema (+ the extra columns); the list of sources that were absent."""
    cache = Path(cache_dir) if cache_dir else default_cache_dir()
    results = Path(results_dir) if results_dir else default_results_dir()
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for fn in (lambda: x1_rows(cache, results), lambda: v7c_rows(cache), lambda: actual_rows(cache, results), lambda: kway_rows(cache)):
        r, m = fn()
        rows += r
        missing += m
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df, missing


def check(df: pd.DataFrame, missing: list[str]) -> None:
    if len(df):
        show = df[["dataset", "reader", "layer", "metric", "k_wins", "n", "auroc", "ci_lo", "ci_hi", "coverage", "source"]].copy()
        show["auroc"] = show["auroc"].map(lambda x: f"{x:.3f}")
        show["ci_lo"] = show["ci_lo"].map(lambda x: f"{x:.2f}")
        show["ci_hi"] = show["ci_hi"].map(lambda x: f"{x:.2f}")
        show["coverage"] = show["coverage"].map(lambda x: f"{x:.2f}")
        print(show.to_string(index=False))
    print(f"\n{len(df)} legacy rows over {df.dataset.nunique() if len(df) else 0} datasets; missing sources: {len(missing)}")
    for m in missing:
        print(f"  missing: {m}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", type=Path, default=None)
    ap.add_argument("--results-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None, help="write the rows here (csv)")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    df, missing = legacy_cells(a.cache_dir, a.results_dir)
    if a.check or not a.out:
        check(df, missing)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(a.out, index=False)
        print(f"wrote {a.out} ({len(df)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
