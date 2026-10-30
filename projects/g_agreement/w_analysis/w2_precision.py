"""W2 — precision on graded facts (PREREG_WV.md "Analysis", brief_wv.md "W2").

    python -m projects.g_agreement.w_analysis.w2_precision [--s1 cache/g_agreement/w/s1_target.jsonl]
        [--s3 cache/g_agreement/w/s3_lo.jsonl] [--s4 cache/g_agreement/w/s4_samples.jsonl] [--out results/g_agreement/w/w2]
        [--n-boot 1000 --seed 0] [--counts-kept results/g_agreement/w/s1/counts_kept.json]

For counts (N 1–99), arith (result 0–198, Michael's plain format) and mapping-8 (symbols A–H) and for every reader that scored the S1
states natively (S3 rows, unit S1: jlens, olens, nla, skip_a, probe; plus the target's own first-token log-probs from S1 as the
reference reader ``model_ft``): the reported value = argmax of the reader's native score vector over the row's ``candidates``
(the probe rows list [cand_A, cand_B] + rest, so the row's own candidate order is used, never ``candidates_all``). For Oracle and
NLA also the number stated in free text (S4 counts samples, natural condition): the FIRST integer in the sample text, one readout
per sample (8 per state).

Per (family, reader): exact-match rate of the reported value, Spearman ρ between reported and true value (mapping-8: the symbol
index A=0…H=7, nominal — reported for completeness), both with item-level bootstrap 95 % CIs (1,000 resamples, seed 0; free-text
readouts are pooled within a state and states are resampled), Wilson CI on exact-match, and the |error| structure: histogram of
|reported − true| (bins 0, 1–2, 3–5, 6–10, 11–20, 21+; mapping-8: index distance 0…7), MAE / median, and among the wrong readouts
the share that keeps the tens digit, the share that keeps the units digit, and (mapping-8) the share naming the k−1 symbol.
"keeps magnitude, drops digits" per reader = the pair (Spearman, exact-match); the descriptive tag uses ρ ≥ 0.5 and exact < 0.5.

Outputs results/g_agreement/w/w2/{w2.md (≤ 40 lines), w2.csv (one row per family × reader), w2_summary.json, fig_precision.png}.
Every effect is read against the other readers and the model's own first token on the same items; nothing here is a raw-rate
headline. Missing inputs are reported, not fabricated: without S3 only ``model_ft`` is scored; without S4 the free-text rows are
absent and said so.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core.accounting import now_iso, read_jsonl

W_CACHE = C.CACHE_DIR / "w"
S1_TARGET = W_CACHE / "s1_target.jsonl"
S3_LO = W_CACHE / "s3_lo.jsonl"
S4_SAMPLES = W_CACHE / "s4_samples.jsonl"
COUNTS_KEPT = C.RESULTS_DIR / "w" / "s1" / "counts_kept.json"
MAPPING8_INDEX = C.PROJECT_DIR / "banks" / "w" / "mapping8_index.json"
OUT_DIR = C.RESULTS_DIR / "w" / "w2"

FAMILIES: Tuple[str, ...] = ("counts", "arith", "mapping8")
NUMERIC_FAMILIES: Tuple[str, ...] = ("counts", "arith")
VECTOR_READERS: Tuple[str, ...] = ("jlens", "olens", "nla", "skip_a", "probe")
TEXT_READERS: Dict[str, str] = {"olens": "olens_text", "nla": "nla_text"}
READER_ORDER: Tuple[str, ...] = ("model_ft", "probe", "jlens", "olens", "skip_a", "nla", "olens_text", "nla_text")
READER_LABEL: Dict[str, str] = {"model_ft": "model (1st token)", "probe": "probe", "jlens": "J-lens", "olens": "Oracle", "skip_a": "skip-lens A",
                                "nla": "NLA", "olens_text": "Oracle (free text)", "nla_text": "NLA (free text)"}
SYMBOLS: List[str] = list("ABCDEFGH")
N_BOOT, SEED = 1000, 0
ERR_EDGES: Tuple[float, ...] = (0, 1, 3, 6, 11, 21, math.inf)  # |error| bins for numeric families
ERR_LABELS: Tuple[str, ...] = ("0", "1-2", "3-5", "6-10", "11-20", "21+")
MAP_LABELS: Tuple[str, ...] = tuple(str(i) for i in range(8))  # index distance for mapping-8
# dataviz reference categorical palette (light mode), fixed slot order = READER_ORDER; identity is also carried by the tick labels.
PALETTE: Tuple[str, ...] = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")
MAG_RHO, MAG_EXACT = 0.5, 0.5  # descriptive tag thresholds (not a decision rule)

_INT = re.compile(r"-?\d+")


def rel(p: Any) -> Optional[str]:
    """Path relative to the repo root for the write-ups (absolute outside it)."""
    if p is None:
        return None
    try:
        return str(Path(p).resolve().relative_to(C.REPO_ROOT))
    except ValueError:
        return str(p)


# ------------------------------------------------------------------ small helpers (also used by bridge.py)
def first_integer(text: Optional[str]) -> Optional[int]:
    """The first integer in a free-text readout (None if there is none)."""
    if not text:
        return None
    m = _INT.search(str(text))
    return int(m.group(0)) if m else None


def value_of(cand: Any, family: str) -> Optional[int]:
    """Graded value of a candidate: int for numeric families, the symbol index (A=0 … H=7) for mapping-8, else None."""
    if cand is None:
        return None
    s = str(cand).strip()
    if family in NUMERIC_FAMILIES:
        return int(s) if re.fullmatch(r"-?\d+", s) else None
    return SYMBOLS.index(s) if s in SYMBOLS else None


def argmax_candidate(candidates: Sequence[Any], scores: Optional[Sequence[Optional[float]]]) -> Optional[Any]:
    """Candidate with the largest non-None score (first on ties); None when nothing is scorable."""
    if not candidates or not scores:
        return None
    best, best_s = None, None
    for c, s in zip(candidates, scores):
        if s is None or (isinstance(s, float) and math.isnan(s)):
            continue
        if best_s is None or float(s) > best_s:
            best, best_s = c, float(s)
    return best


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman ρ with average ranks; NaN for < 3 pairs or a constant input."""
    if len(x) < 3:
        return float("nan")
    from scipy.stats import rankdata

    rx, ry = rankdata(x), rankdata(y)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) < 3:
        return float("nan")
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float, float]:
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def _q(v: List[float], a: float) -> Optional[float]:
    v = [x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.quantile(v, a)) if v else None


def item_bootstrap(records: Sequence[dict], n_boot: int = N_BOOT, seed: int = SEED, *, with_pearson: bool = False) -> dict:
    """Exact-match and Spearman (optionally Pearson) with ITEM-level bootstrap CIs. ``records`` = {item_id, true, reported} per
    readout (several readouts per item are pooled; items are resampled). A readout with reported None counts as not exact and is
    excluded from the correlations (its share is ``unparsed_rate``)."""
    by_item: Dict[str, List[Tuple[Optional[int], Optional[int]]]] = {}
    for r in records:
        by_item.setdefault(str(r["item_id"]), []).append((r["true"], r["reported"]))
    ids = sorted(by_item)
    n_items = len(ids)
    n_read = np.array([len(by_item[i]) for i in ids], dtype=float)
    n_exact = np.array([sum(1 for t, p in by_item[i] if p is not None and t is not None and p == t) for i in ids], dtype=float)
    n_parsed = np.array([sum(1 for t, p in by_item[i] if p is not None and t is not None) for i in ids], dtype=float)
    pairs = [[(t, p) for t, p in by_item[i] if p is not None and t is not None] for i in ids]
    tot = int(n_read.sum())
    out: Dict[str, Any] = {"n_items": n_items, "n_readouts": tot, "n_exact": int(n_exact.sum()), "n_parsed": int(n_parsed.sum()),
                           "exact": (float(n_exact.sum() / tot) if tot else None), "unparsed_rate": (float(1 - n_parsed.sum() / tot) if tot else None)}
    allp = [pr for ps in pairs for pr in ps]
    out["spearman"] = spearman([t for t, _ in allp], [p for _, p in allp]) if allp else float("nan")
    if with_pearson:
        out["pearson"] = pearson([t for t, _ in allp], [p for _, p in allp]) if allp else float("nan")
    out["exact_wilson"] = list(wilson(int(n_exact.sum()), tot))[1:] if tot else [None, None]
    if n_items == 0:
        out.update(exact_lo=None, exact_hi=None, spearman_lo=None, spearman_hi=None, n_boot=0)
        return out
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_items, (n_boot, n_items))
    ex = n_exact[idx].sum(1) / np.maximum(n_read[idx].sum(1), 1)
    out["exact_lo"], out["exact_hi"] = float(np.quantile(ex, 0.025)), float(np.quantile(ex, 0.975))
    sp, pe = [], []
    for b in range(n_boot):
        sel = [pr for j in idx[b] for pr in pairs[j]]
        if len(sel) >= 3:
            t = [u for u, _ in sel]
            p = [v for _, v in sel]
            sp.append(spearman(t, p))
            if with_pearson:
                pe.append(pearson(t, p))
    out["spearman_lo"], out["spearman_hi"] = _q(sp, 0.025), _q(sp, 0.975)
    if with_pearson:
        out["pearson_lo"], out["pearson_hi"] = _q(pe, 0.025), _q(pe, 0.975)
    out["n_boot"] = int(n_boot)
    out["seed"] = int(seed)
    return out


def error_structure(records: Sequence[dict], family: str, k_minus_1: Optional[Dict[str, int]] = None) -> dict:
    """|error| histogram (shares of parsed readouts), MAE / median, and the confusion structure of the wrong readouts."""
    pairs = [(int(r["true"]), int(r["reported"])) for r in records if r["reported"] is not None and r["true"] is not None]
    errs = np.array([abs(p - t) for t, p in pairs], dtype=float)
    out: Dict[str, Any] = {"n_parsed": len(pairs)}
    if family in NUMERIC_FAMILIES:
        counts = [int(((errs >= lo) & (errs < hi)).sum()) for lo, hi in zip(ERR_EDGES[:-1], ERR_EDGES[1:])]
        out["hist_labels"], out["hist_counts"] = list(ERR_LABELS), counts
    else:
        counts = [int((errs == i).sum()) for i in range(8)]
        out["hist_labels"], out["hist_counts"] = list(MAP_LABELS), counts
    out["hist_share"] = [c / len(pairs) if pairs else None for c in counts]
    out["mae"] = float(errs.mean()) if len(errs) else None
    out["median_abs_err"] = float(np.median(errs)) if len(errs) else None
    wrong = [(t, p) for t, p in pairs if t != p]
    out["n_wrong"] = len(wrong)
    if family in NUMERIC_FAMILIES:
        out["wrong_same_tens"] = (sum(1 for t, p in wrong if t // 10 == p // 10) / len(wrong)) if wrong else None
        out["wrong_same_units"] = (sum(1 for t, p in wrong if t % 10 == p % 10) / len(wrong)) if wrong else None
        out["wrong_within_5"] = (sum(1 for t, p in wrong if abs(t - p) <= 5) / len(wrong)) if wrong else None
        out["wrong_same_decade_or_within_5"] = (sum(1 for t, p in wrong if t // 10 == p // 10 or abs(t - p) <= 5) / len(wrong)) if wrong else None
    else:
        out["wrong_adjacent_index"] = (sum(1 for t, p in wrong if abs(t - p) == 1) / len(wrong)) if wrong else None
        if k_minus_1:
            wr = [r for r in records if r["reported"] is not None and r["true"] is not None and r["reported"] != r["true"]]
            hit = [1 for r in wr if k_minus_1.get(str(r["item_id"])) == r["reported"]]
            out["wrong_is_k_minus_1"] = (len(hit) / len(wr)) if wr else None
    return out


def magnitude_tag(exact: Optional[float], rho: Optional[float]) -> str:
    """Descriptive tag for the (Spearman, exact) pair (reporting aid, not a pre-registered rule)."""
    if exact is None or rho is None or (isinstance(rho, float) and math.isnan(rho)):
        return "n/a"
    if exact >= MAG_EXACT:
        return "reads digits"
    if rho >= MAG_RHO:
        return "keeps magnitude, drops digits"
    return "neither"


# ------------------------------------------------------------------ record builders (schemas of w_pod/s1_capture, s3_score, s4_consistency)
def records_from_s1(rows: Sequence[dict], families: Sequence[str] = FAMILIES) -> Dict[Tuple[str, str], List[dict]]:
    """The target's first-token log-probs over candidates_all → reader ``model_ft``."""
    out: Dict[Tuple[str, str], List[dict]] = {}
    for r in rows:
        fam = r.get("family")
        if fam not in families or not r.get("candidates_all"):
            continue
        rep = argmax_candidate(r["candidates_all"], r.get("lp_candidates_all"))
        out.setdefault((fam, "model_ft"), []).append({"item_id": r["item_id"], "true": value_of(r.get("true_answer"), fam), "reported": value_of(rep, fam),
                                                     "reported_raw": rep, "correct_greedy": r.get("correct")})
    return out


def records_from_s3(rows: Sequence[dict], families: Sequence[str] = FAMILIES, readers: Sequence[str] = VECTOR_READERS, unit: str = "S1",
                    layer: Optional[int] = None) -> Dict[Tuple[str, str], List[dict]]:
    """Native score vectors of the S1 states (one row per reader × item; the row's own ``candidates`` order)."""
    out: Dict[Tuple[str, str], List[dict]] = {}
    seen: set = set()
    for r in rows:
        fam, rd = r.get("family"), r.get("reader")
        if r.get("unit") != unit or fam not in families or rd not in readers:
            continue
        if layer is not None and r.get("layer") is not None and int(r["layer"]) != int(layer):
            continue
        k = (rd, fam, r.get("item_id"))
        if k in seen:
            continue
        seen.add(k)
        rep = argmax_candidate(r.get("candidates") or [], r.get("scores"))
        out.setdefault((fam, rd), []).append({"item_id": r["item_id"], "true": value_of(r.get("true_answer"), fam), "reported": value_of(rep, fam),
                                             "reported_raw": rep, "n_unscorable": r.get("n_unscorable")})
    return out


def records_from_s4(rows: Sequence[dict], families: Sequence[str] = ("counts",), condition: str = "natural") -> Dict[Tuple[str, str], List[dict]]:
    """Free-text samples (S4): the first integer stated → readers ``olens_text`` / ``nla_text``; one record per sample."""
    out: Dict[Tuple[str, str], List[dict]] = {}
    for r in rows:
        fam, rd = r.get("family"), r.get("reader")
        if fam not in families or r.get("condition", "natural") != condition or rd not in TEXT_READERS:
            continue
        rep = first_integer(r.get("text"))
        out.setdefault((fam, TEXT_READERS[rd]), []).append({"item_id": r["state_item_id"], "sample_idx": r.get("sample_idx"), "true": value_of(r.get("answer"), fam),
                                                           "reported": rep, "reported_raw": rep})
    return out


def restrict_items(recs: Dict[Tuple[str, str], List[dict]], family: str, keep: Optional[set]) -> None:
    if keep is None:
        return
    for (fam, _rd), lst in recs.items():
        if fam == family:
            lst[:] = [r for r in lst if str(r["item_id"]) in keep]


def load_counts_kept(path: Optional[Path]) -> Optional[set]:
    if path is None or not Path(path).exists():
        return None
    d = json.loads(Path(path).read_text())
    return set(str(x) for x in d.get("kept", [])) or None


def load_k_minus_1(path: Optional[Path]) -> Optional[Dict[str, int]]:
    if path is None or not Path(path).exists():
        return None
    d = json.loads(Path(path).read_text())
    out = {}
    for it in d.get("items", []):
        v = value_of(it.get("k_minus_1_symbol"), "mapping8")
        if v is not None:
            out[str(it["item_id"])] = v
    return out or None


# ------------------------------------------------------------------ the analysis
def summarise(recs: Dict[Tuple[str, str], List[dict]], *, n_boot: int = N_BOOT, seed: int = SEED, k_minus_1: Optional[Dict[str, int]] = None) -> List[dict]:
    rows = []
    for fam in FAMILIES:
        for rd in READER_ORDER:
            lst = recs.get((fam, rd))
            if not lst:
                continue
            st = item_bootstrap(lst, n_boot, seed)
            es = error_structure(lst, fam, k_minus_1 if fam == "mapping8" else None)
            rows.append({"family": fam, "reader": rd, "label": READER_LABEL.get(rd, rd), "source": ("S4 free text" if rd.endswith("_text") else ("S1 lp_candidates_all" if rd == "model_ft" else "S3 native vector")),
                         **st, **{k: v for k, v in es.items() if k != "n_parsed"}, "tag": magnitude_tag(st["exact"], st["spearman"]),
                         "spearman_note": ("symbol index A=0..H=7 (nominal)" if fam == "mapping8" else "value")})
    return rows


CSV_COLUMNS = ["family", "reader", "label", "source", "n_items", "n_readouts", "n_parsed", "unparsed_rate", "n_exact", "exact", "exact_lo", "exact_hi",
               "exact_wilson_lo", "exact_wilson_hi", "spearman", "spearman_lo", "spearman_hi", "mae", "median_abs_err", "n_wrong", "wrong_same_tens",
               "wrong_same_units", "wrong_within_5", "wrong_adjacent_index", "wrong_is_k_minus_1", "hist_labels", "hist_counts", "tag", "spearman_note", "n_boot", "seed"]


def _fmt(v: Any, nd: int = 2) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def write_outputs(rows: List[dict], out_dir: Path, *, inputs: dict, notes: List[str]) -> dict:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "w2.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLUMNS)
        for r in rows:
            rr = dict(r)
            rr["exact_wilson_lo"], rr["exact_wilson_hi"] = (r.get("exact_wilson") or [None, None])[:2]
            w.writerow([(json.dumps(rr.get(c)) if isinstance(rr.get(c), (list, dict)) else ("" if rr.get(c) is None else rr.get(c))) for c in CSV_COLUMNS])
    summary = {"written": now_iso(), "inputs": inputs, "n_boot": N_BOOT if not rows else rows[0].get("n_boot"), "rows": rows, "notes": notes,
               "tag_rule": f"'reads digits' if exact >= {MAG_EXACT}; else 'keeps magnitude, drops digits' if Spearman >= {MAG_RHO}; else 'neither' (descriptive)",
               "families": list(FAMILIES), "reader_order": list(READER_ORDER)}
    (out_dir / "w2_summary.json").write_text(json.dumps(summary, indent=1, default=_json_default))
    md = ["# W2 — precision on graded facts", "",
          f"Inputs: {', '.join(f'{k}={v}' for k, v in inputs.items() if v)}. Reported value = argmax of the native score vector (free text: first integer).",
          "Item-level bootstrap 95 % CIs (1,000, seed 0); Spearman on the value (mapping-8: symbol index, nominal). Wrong-readout structure: share keeping the tens / units digit.", "",
          "| family | reader | n items | readouts | exact [CI] | Spearman [CI] | MAE | wrong: same tens | same units | tag |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['family']} | {r['label']} | {r['n_items']} | {r['n_readouts']} | {_fmt(r['exact'])} [{_fmt(r['exact_lo'])}, {_fmt(r['exact_hi'])}] | "
                  f"{_fmt(r['spearman'])} [{_fmt(r['spearman_lo'])}, {_fmt(r['spearman_hi'])}] | {_fmt(r['mae'], 1)} | "
                  f"{_fmt(r.get('wrong_same_tens') if r['family'] != 'mapping8' else r.get('wrong_is_k_minus_1'))}{' (k−1)' if r['family'] == 'mapping8' else ''} | "
                  f"{_fmt(r.get('wrong_same_units') if r['family'] != 'mapping8' else r.get('wrong_adjacent_index'))}{' (adj.)' if r['family'] == 'mapping8' else ''} | {r['tag']} |")
    md.append("")
    md.extend(f"- {n}" for n in notes)
    md.append("- Figure: fig_precision.png (top: exact-match ● and Spearman ■ per reader with CIs; bottom: |error| histograms). Data: w2.csv, w2_summary.json.")
    text = "\n".join(md[:40]) + "\n"
    (out_dir / "w2.md").write_text(text)
    return summary


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if math.isnan(float(o)) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, float) and math.isnan(o):
        return None
    return str(o)


def figure(rows: List[dict], path: Path) -> None:
    """One figure, 2 × 3: per family exact-match (●) and Spearman (■) per reader with CIs; below, the |error| histograms."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fams = [f for f in FAMILIES if any(r["family"] == f for r in rows)] or list(FAMILIES)
    fig, axes = plt.subplots(2, len(fams), figsize=(4.6 * len(fams), 7.2), squeeze=False)
    colour = {rd: PALETTE[i % len(PALETTE)] for i, rd in enumerate(READER_ORDER)}
    for j, fam in enumerate(fams):
        rs = [r for r in rows if r["family"] == fam]
        ax = axes[0, j]
        xs = np.arange(len(rs))
        for i, r in enumerate(rs):
            c = colour[r["reader"]]
            ex, lo, hi = r["exact"], r["exact_lo"], r["exact_hi"]
            if ex is not None:
                ax.errorbar(i - 0.12, ex, yerr=[[ex - (lo if lo is not None else ex)], [(hi if hi is not None else ex) - ex]], fmt="o", color=c, ms=7, capsize=3, lw=1.5)
            sp, slo, shi = r["spearman"], r["spearman_lo"], r["spearman_hi"]
            if sp is not None and not (isinstance(sp, float) and math.isnan(sp)):
                ax.errorbar(i + 0.12, sp, yerr=[[sp - (slo if slo is not None else sp)], [(shi if shi is not None else sp) - sp]], fmt="s", mfc="white", color=c, ms=7, capsize=3, lw=1.5)
        ax.set_xticks(xs)
        ax.set_xticklabels([r["label"] for r in rs], rotation=30, ha="right", fontsize=8)
        ax.set_ylim(-0.25, 1.05)
        ax.axhline(0, color="#c3c2b7", lw=0.8)
        unit = {"counts": "N 1–99", "arith": "result 0–198", "mapping8": "symbol A–H"}[fam]
        ax.set_title(f"{fam} ({unit}; n = {rs[0]['n_items'] if rs else 0} items)", fontsize=10, loc="left")
        if j == 0:
            ax.set_ylabel("exact-match rate (●)  /  Spearman ρ (■)")
        ax.grid(axis="y", color="#f0efec")
        ax.spines[["top", "right"]].set_visible(False)
        # histogram
        ax = axes[1, j]
        labels = rs[0]["hist_labels"] if rs else list(ERR_LABELS)
        nb = len(labels)
        width = 0.8 / max(len(rs), 1)
        for i, r in enumerate(rs):
            sh = [0 if v is None else v for v in r["hist_share"]]
            ax.bar(np.arange(nb) + (i - (len(rs) - 1) / 2) * width, sh, width=width * 0.9, color=colour[r["reader"]], label=r["label"], linewidth=0)
        ax.set_xticks(np.arange(nb))
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_xlabel("|reported − true|" + (" (symbol-index distance)" if fam == "mapping8" else ""))
        if j == 0:
            ax.set_ylabel("share of parsed readouts")
        ax.set_ylim(0, 1)
        ax.grid(axis="y", color="#f0efec")
        ax.spines[["top", "right"]].set_visible(False)
    handles = [plt.Line2D([], [], color=colour[rd], marker="s", ls="", ms=8, label=READER_LABEL[rd]) for rd in READER_ORDER if any(r["reader"] == rd for r in rows)]
    if handles:
        fig.legend(handles=handles, loc="lower center", ncol=min(len(handles), 8), fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("W2 — do readers keep the magnitude and drop the digits? (item-level bootstrap 95 % CIs)", x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(*, s1: Path = S1_TARGET, s3: Path = S3_LO, s4: Path = S4_SAMPLES, out_dir: Path = OUT_DIR, n_boot: int = N_BOOT, seed: int = SEED,
        counts_kept: Optional[Path] = COUNTS_KEPT, mapping8_index: Optional[Path] = MAPPING8_INDEX, make_figure: bool = True) -> dict:
    s1_rows, s3_rows, s4_rows = read_jsonl(s1), read_jsonl(s3), read_jsonl(s4)
    notes: List[str] = []
    if not s1_rows:
        raise FileNotFoundError(f"S1 target rows missing or empty: {s1}")
    recs = records_from_s1(s1_rows)
    if s3_rows:
        recs.update(records_from_s3(s3_rows))
    else:
        notes.append(f"S3 reader rows absent ({s3}): only the model's first-token reader is scored.")
    if s4_rows:
        recs.update(records_from_s4(s4_rows))
        if not any(k[1].endswith("_text") for k in recs):
            notes.append("S4 rows present but no counts/natural Oracle or NLA samples: no free-text rows.")
    else:
        notes.append(f"S4 samples absent ({s4}): free-text (Oracle / NLA stated number) rows not available; counts states only by design.")
    keep = load_counts_kept(counts_kept)
    if keep is not None:
        restrict_items(recs, "counts", keep)
        notes.append(f"counts restricted to the {len(keep)} S1-kept items (greedy-correct filter).")
    k1 = load_k_minus_1(mapping8_index)
    rows = summarise(recs, n_boot=n_boot, seed=seed, k_minus_1=k1)
    notes.append("arith is Michael's plain format: the model mostly does not answer (see bridge); the native vector reads the RESULT 0–198, not the operands.")
    inputs = {"s1": rel(s1) if s1_rows else None, "s3": rel(s3) if s3_rows else None, "s4": rel(s4) if s4_rows else None, "counts_kept": rel(counts_kept) if keep else None}
    summary = write_outputs(rows, out_dir, inputs=inputs, notes=notes)
    if make_figure:
        figure(rows, out_dir / "fig_precision.png")
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--s1", type=Path, default=S1_TARGET)
    ap.add_argument("--s3", type=Path, default=S3_LO)
    ap.add_argument("--s4", type=Path, default=S4_SAMPLES)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--counts-kept", type=Path, default=COUNTS_KEPT)
    ap.add_argument("--mapping8-index", type=Path, default=MAPPING8_INDEX)
    ap.add_argument("--no-figure", action="store_true")
    a = ap.parse_args(argv)
    try:
        s = run(s1=a.s1, s3=a.s3, s4=a.s4, out_dir=a.out, n_boot=a.n_boot, seed=a.seed, counts_kept=a.counts_kept, mapping8_index=a.mapping8_index, make_figure=not a.no_figure)
    except FileNotFoundError as e:
        print(f"[w2] {e}", file=sys.stderr)
        return 2
    for r in s["rows"]:
        print(f"[w2] {r['family']:8s} {r['label']:20s} n={r['n_items']:4d} exact={_fmt(r['exact'])} [{_fmt(r['exact_lo'])},{_fmt(r['exact_hi'])}] "
              f"rho={_fmt(r['spearman'])} [{_fmt(r['spearman_lo'])},{_fmt(r['spearman_hi'])}]  {r['tag']}")
    for n in s["notes"]:
        print(f"[w2] note: {n}")
    print(f"[w2] wrote {a.out}/w2.md, w2.csv, w2_summary.json" + ("" if a.no_figure else ", fig_precision.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
