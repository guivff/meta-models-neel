"""Phase R analysis (CPU; BRIEF_R.md §4–6). numpy / pandas / scikit-learn / matplotlib only — no torch, so it runs on
the Mac against the synced cache. Every table is written to results/g_agreement/r/, every figure next to it, and
``analyze_summary.md`` collects the headline numbers (renamed 2026-10-20: ``summary.md`` is the Integrator's hand-kept claims ledger) and the pre-registered verdicts.

    python -m projects.g_agreement.r_bench.analyze --mock                   # synthetic bank (r_bench/mock.py) end to end
    python -m projects.g_agreement.r_bench.analyze --only r1 r2 r4           # on the real cache, chosen regimes
    python -m projects.g_agreement.r_bench.analyze --r5-select               # write r5_selection.json + d_cm / d_probe directions
    python -m projects.g_agreement.r_bench.analyze --only r5                 # after steer.py has run

Regimes: r1 efficiency (learning curves, n*, quiver), r2 ceiling, r3 conflict, r4 site (lag, render shift),
r5 geometry (spoof / evade), r6 k-way, r7 agreement, r8 confidence. Figures F1–F8 (BRIEF_R §6).
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common.stats import wilson
from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench import datasets as D

warnings.filterwarnings("ignore", category=FutureWarning)

NS = (2, 4, 8, 16, 32, 64, 128, 256, 512)
SEEDS = (0, 1, 2, 3, 4)
C_GRID = (0.01, 0.1, 1.0, 10.0)
PRIMARY_LAYER = {"jlens": 42, "olens": 44, "skip_a": 42, "skip_d": 42, "nla": 42, "logit_lens": 42}
PRIMARY_RENDER = "chat"
READER_ORDER = ["jlens", "olens", "nla", "skip_a", "skip_d", "logit_lens"]
TAG_ORDER = ["SURFACE", "TOPIC", "FORM", "KNOWLEDGE", "COMPUTED", "META", "INTERNAL", "CONTEXT"]
L_EDIT, L_READ = 38, 42


# ------------------------------------------------------------------ paths
class Paths:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else C.REPO_ROOT
        self.cache = self.root / "cache" / "g_agreement" / "r"
        self.dataset = self.root / "dataset" if root else C.DATASET_DIR
        self.results = self.root / "results" / "g_agreement" / "r"
        self.fig = self.results / "fig"
        self.results.mkdir(parents=True, exist_ok=True)
        self.fig.mkdir(parents=True, exist_ok=True)

    def items(self) -> Path:
        return self.dataset / "items_r.json"

    def items_k(self) -> Path:
        return self.dataset / "items_rk.json"


def read_jsonl(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()
    lines = [l for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [json.loads(l) for l in lines[:-1]]
    if lines:
        try:
            rows.append(json.loads(lines[-1]))
        except json.JSONDecodeError:  # a shard mid-sync (rsync / a pod still appending): only the LAST line may be partial
            PARTIAL_TAIL[Path(path).name] = PARTIAL_TAIL.get(Path(path).name, 0) + 1
    return pd.DataFrame(rows)


PARTIAL_TAIL: dict[str, int] = {}


def shard_files(cache: Path, name: str) -> list[Path]:
    """The plain file plus every shard / suffix variant the collector writes under PLAN_R §9: ``<name>.jsonl``,
    ``<name>.<k>.jsonl`` (pod A-k) and ``<name>.<k>.B.jsonl`` (phase B under a shard), in that order."""
    plain = cache / f"{name}.jsonl"
    return ([plain] if plain.exists() else []) + sorted(p for p in cache.glob(f"{name}.*.jsonl") if p != plain)


# ------------------------------------------------------------------ provenance (Qwen3.6-27B rows only)
# Pod D runs WS13's planted-fact test model (a fine-tune, `rf_*@base|sft|sft_dpo` datasets); its rows were also copied
# into the unsuffixed files without pod / git_sha. They are not Qwen3.6-27B rows and never enter a main table.
# Extra pod ids reported by chat 6 go in R_EXTRA_PODS (comma-separated) or --extra-pods.
ALLOWED_PODS = {"A1", "A2", "A3", "A4", "B", "C",
                "E", "RB"}  # E = R-E bank, RB = ReaderBench: pod ids reported by chat 6 (2026-10-18 23:40Z)
FROZEN_GIT_SHA = "4d482b6"
EXCLUDED_PODS = {"D"}
HEAVY_COLS = ("variants_A", "variants_B", "templates", "items_sha256", "current_r_code_sha256", "frozen_r_code_sha256", "items_file")
PROVENANCE: dict[str, Any] = {"strict": True, "extra_pods": set(), "dropped": {}, "off_bank": {}}


MAIN_CONDITIONS = {"natural", "shuf", "pool_eval", "state_free"}


def assert_conditions(df: pd.DataFrame, where: str, allowed: set[str] | None = None) -> None:
    """Every row that can reach a main table carries a known condition, so a new arm (e.g. the Oracle-given-text rows,
    which live in cache/g_agreement/r/text_arm/) cannot leak in silently."""
    if df.empty:
        return
    assert "condition" in df.columns, f"{where}: rows without a condition column"
    allowed = MAIN_CONDITIONS if allowed is None else allowed
    bad = ~df["condition"].isin(allowed)
    assert not bad.any(), f"{where}: {int(bad.sum())} rows with condition {sorted(map(str, set(df.loc[bad, 'condition'])))} not in {sorted(allowed)}"


WS3_BANKS = ("items_r.json", "items_rk.json", "items_re.json", "items_rb.json", "items_rbk.json", "items_rx.json")
_ANALYSED: dict[str, set[str] | None] = {}  # keyed on the dataset directory (tests patch C.DATASET_DIR)


def analysed_datasets() -> set[str] | None:
    """Every dataset of the banks WS3 analyses (R-A, R-B, R-E, ReaderBench, R-X). Rows of other banks (e.g. R-C2's
    ``*.RC2.jsonl``) are set aside and counted before the provenance assertion; they never reach a WS3 table. None when no
    bank file exists in ``C.DATASET_DIR`` (no scoping then, rather than setting every row aside)."""
    key = str(C.DATASET_DIR)
    if key not in _ANALYSED:
        out: set[str] = set()
        found = False
        for f in WS3_BANKS:
            p = Path(key) / f
            if p.exists():
                found = True
                out |= {it["dataset"] for it in json.loads(p.read_text())["items"]}
        _ANALYSED[key] = out if found else None
    return _ANALYSED[key]


def is_ws13_dataset(ds: Any) -> bool:
    """WS13 planted-fact datasets: `rf_` prefix or a `@<checkpoint>` suffix (no items_r dataset matches either)."""
    return isinstance(ds, str) and (ds.startswith("rf_") or "@" in ds)


def provenance_filter(df: pd.DataFrame, path: Path, name: str, side_pods: set[str] | None = None,
                      side_shas: set[str] | None = None, datasets: set[str] | None = None) -> pd.DataFrame:
    """Drop pod-D / WS13 rows (counted in PROVENANCE['dropped']), then assert every remaining row comes from an allowed
    pod at the frozen git sha."""
    if df.empty:
        return df
    pod = df["pod"] if "pod" in df.columns else pd.Series(None, index=df.index, dtype=object)
    from_d_file = path.name.split(".")[-2] == "D"  # <name>.D.jsonl
    ds_col = df["dataset"] if "dataset" in df.columns else pd.Series(None, index=df.index, dtype=object)
    drop = pod.isin(EXCLUDED_PODS) | ds_col.map(is_ws13_dataset).fillna(False).astype(bool) | from_d_file
    n_drop = int(drop.sum())
    if n_drop:
        PROVENANCE["dropped"][path.name] = n_drop  # set, not add: a table read twice counts once
    keep = df[~drop]
    if datasets is not None and "dataset" in keep.columns:  # rows of other banks never reach this table: set aside, counted
        other = ~keep["dataset"].isin(datasets)
        if other.any():
            PROVENANCE["off_bank"][f"{name}:{path.name}"] = int(other.sum())
        keep = keep[~other]
    if not PROVENANCE["strict"] or keep.empty:
        return keep.reset_index(drop=True)
    allowed = ALLOWED_PODS | PROVENANCE["extra_pods"] | (side_pods or set())
    kpod = keep["pod"] if "pod" in keep.columns else pd.Series(None, index=keep.index, dtype=object)
    ksha = keep["git_sha"].astype(str).str[:7] if "git_sha" in keep.columns else pd.Series("None", index=keep.index)
    bad_pod, bad_sha = ~kpod.isin(allowed), ~ksha.isin({FROZEN_GIT_SHA} | {x[:7] for x in (side_shas or set())})
    assert not bad_pod.any(), f"{path.name}: {int(bad_pod.sum())} rows from pods {sorted(map(str, set(kpod[bad_pod])))} not in {sorted(allowed)}"
    assert not bad_sha.any(), f"{path.name}: {int(bad_sha.sum())} rows with git_sha {sorted(set(ksha[bad_sha]))} != {FROZEN_GIT_SHA}"
    return keep.reset_index(drop=True)


def read_jsonl_shards(cache: Path, name: str, datasets: set[str] | None = None) -> pd.DataFrame:
    """Concatenate ``shard_files``; a key that appears in several files (a pod restarted with a different suffix) keeps
    its last occurrence. Every file goes through ``provenance_filter`` first."""
    if datasets is None and PROVENANCE["strict"]:
        datasets = analysed_datasets()
    frames = [provenance_filter(read_jsonl(p), p, name, datasets=datasets) for p in shard_files(cache, name)]
    frames = [f.drop(columns=[c for c in HEAVY_COLS if c in f.columns]) for f in frames]
    frames = [f for f in frames if len(f)]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    if "key" in df.columns and len(frames) > 1:
        df = df.drop_duplicates(subset="key", keep="last").reset_index(drop=True)
    return df


def phase_r_ledger(results_dir: Path = C.RESULTS_DIR) -> tuple[pd.DataFrame, int]:
    """compute.jsonl + compute.<k>.jsonl without pod-D / WS13 rows (GPU-hours for the Qwen3.6-27B tables).
    Not asserted: the ledger also holds pre-Phase-R rows that carry no pod."""
    frames = [read_jsonl(p) for p in [results_dir / "compute.jsonl", *sorted(results_dir.glob("compute.*.jsonl"))]]
    df = pd.concat([f for f in frames if len(f)], ignore_index=True) if any(len(f) for f in frames) else pd.DataFrame()
    if df.empty:
        return df, 0
    pod = df["pod"] if "pod" in df.columns else pd.Series(None, index=df.index, dtype=object)
    text = df.get("module", pd.Series("", index=df.index)).astype(str) + " " + df.get("step", pd.Series("", index=df.index)).astype(str)
    drop = pod.isin(EXCLUDED_PODS) | text.str.contains(r"\brf_|planted_facts|organism", regex=True)
    return df[~drop].reset_index(drop=True), int(drop.sum())


def load_bank(P: Paths) -> tuple[pd.DataFrame, dict[str, Any]]:
    d = json.loads(P.items().read_text(encoding="utf-8"))
    items = pd.DataFrame(d["items"])
    items["sided"] = items["primary"].map(lambda p: p.get("sided"))
    return items, d["meta"]


def load_states(P: Paths, ds: str, render: str, layer: int) -> tuple[np.ndarray, list[str]]:
    sd = P.cache / "states" / ds
    idx = json.loads((sd / "index.json").read_text())["item_ids"]
    X = np.load(sd / f"{render}_L{layer}.npy").astype(np.float32)
    return X, idx


# ------------------------------------------------------------------ statistics
def auroc(y: np.ndarray, s: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score

    y, s = np.asarray(y), np.asarray(s, dtype=float)
    ok = np.isfinite(s)
    if ok.sum() < 2 or len(set(y[ok])) < 2:
        return float("nan")
    return float(roc_auc_score(y[ok], s[ok]))


def auroc_rows(Y: np.ndarray, S: np.ndarray) -> np.ndarray:
    """AUROC of every row of ``S`` against the 0/1 labels in the same row of ``Y`` (Mann–Whitney on average ranks, so
    ties count one half exactly as ``sklearn.metrics.roc_auc_score`` does); NaN for rows with a single class. One
    vectorised call for a whole bootstrap: ``Y``, ``S`` are (n_boot, n)."""
    from scipy.stats import rankdata

    Y = np.asarray(Y, dtype=bool)
    S = np.asarray(S, dtype=float)
    n_pos = Y.sum(axis=1)
    n_neg = Y.shape[1] - n_pos
    ranks = rankdata(S, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        a = ((ranks * Y).sum(axis=1) - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    a = np.where((n_pos > 0) & (n_neg > 0), a, np.nan)
    return a


def _boot_index(rng: np.random.Generator, n: int, n_boot: int) -> np.ndarray:
    return rng.integers(0, n, size=(n_boot, n))


def auroc_ci(y: np.ndarray, s: np.ndarray, n_boot: int = 1000, seed: int = 0) -> tuple[float, float, float]:
    """Point AUROC and its 95% item-bootstrap CI (``n_boot`` resamples drawn and scored in one numpy call; resamples
    with a single class are dropped, as in the loop version)."""
    rng = np.random.default_rng(seed)
    y, s = np.asarray(y), np.asarray(s, dtype=float)
    ok = np.isfinite(s)
    y, s = y[ok], s[ok]
    a = auroc(y, s)
    if not np.isfinite(a):
        return a, float("nan"), float("nan")
    i = _boot_index(rng, len(y), n_boot)
    vals = auroc_rows(y[i], s[i])
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return a, float("nan"), float("nan")
    return a, float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def paired_auroc_diff(y: np.ndarray, s1: np.ndarray, s2: np.ndarray, n_boot: int = 1000, seed: int = 0) -> tuple[float, float, float]:
    """AUROC(s1) − AUROC(s2) on the same items with a paired item bootstrap (vectorised like ``auroc_ci``)."""
    rng = np.random.default_rng(seed)
    y, s1, s2 = np.asarray(y), np.asarray(s1, float), np.asarray(s2, float)
    ok = np.isfinite(s1) & np.isfinite(s2)
    y, s1, s2 = y[ok], s1[ok], s2[ok]
    d0 = auroc(y, s1) - auroc(y, s2)
    if not np.isfinite(d0):
        return float(d0), float("nan"), float("nan")
    i = _boot_index(rng, len(y), n_boot)
    Yb = y[i]
    vals = auroc_rows(Yb, s1[i]) - auroc_rows(Yb, s2[i])
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return float(d0), float("nan"), float("nan")
    return float(d0), float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def mean_ci(x: np.ndarray, n_boot: int = 1000, seed: int = 0) -> tuple[float, float, float]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    vals = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n_boot)]
    return float(x.mean()), float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


# ------------------------------------------------------------------ reader scores
def primary_score(df: pd.DataFrame, sided_of: dict[str, str]) -> pd.Series:
    """s_diff for two-sided facts, s_pos for one-sided ones (BRIEF_R §2.1)."""
    sided = df["dataset"].map(sided_of)
    return np.where(sided == "two", df["lo"], df["lp_A"]).astype(float)


def _bank_only(df: pd.DataFrame, items: pd.DataFrame, name: str) -> pd.DataFrame:
    """The main tables are R-A only: rows of the other banks that share the shard globs (.E R-E, .RB ReaderBench,
    .RC2 R-C2, .B R-X / k-way, .NLA) are set aside and counted, before any condition check."""
    if df.empty or "dataset" not in df.columns:
        return df
    keep = df["dataset"].isin(set(items["dataset"]))
    if (~keep).any():
        PROVENANCE["off_bank"][name] = int((~keep).sum())
    return df[keep].reset_index(drop=True)


def reader_frame(P: Paths, items: pd.DataFrame) -> pd.DataFrame:
    """reader_lo rows + logit-lens rows (as reader 'logit_lens', per layer) with the primary score attached."""
    sided_of = dict(zip(items["dataset"], items["sided"]))
    split_of = dict(zip(items["item_id"], items["split"]))
    lo = read_jsonl_shards(P.cache, "reader_lo", datasets=set(items["dataset"]))
    lo = _bank_only(lo, items, "reader_lo")
    assert_conditions(lo, "reader_lo")
    if len(lo):
        lo = lo[lo.get("unscorable", False) != True].copy()  # noqa: E712
        lo["score"] = primary_score(lo, sided_of)
        lo["split"] = lo["item_id"].map(split_of)
    ll = _bank_only(read_jsonl_shards(P.cache, "logit_lens", datasets=set(items["dataset"])), items, "logit_lens")
    rows = []
    for r in ll.itertuples(index=False):
        for L, v in r.per_layer.items():
            rows.append({"reader": "logit_lens", "layer": int(L), "render": r.render, "condition": "natural", "dataset": r.dataset,
                         "item_id": r.item_id, "label": r.label, "lp_A": np.nan, "lp_B": np.nan, "lo": v["margin"], "score": v["margin"],
                         "split": split_of.get(r.item_id)})
    llf = pd.DataFrame(rows)
    out = pd.concat([lo, llf], ignore_index=True) if len(lo) else llf
    assert_conditions(out, "reader frame")
    return out


def cells_table(lo: pd.DataFrame, items: pd.DataFrame, n_boot: int = 500, allowed_conditions: set[str] | None = None) -> pd.DataFrame:
    """AUROC per (dataset, reader, layer, render, condition) on the test split, with CIs and coverage. The Qwen main
    tables pass ``allowed_conditions=MAIN_CONDITIONS`` (asserted); other callers (e.g. r_gemma's rotation readouts)
    keep their own conditions unchecked here."""
    if allowed_conditions is not None:
        assert_conditions(lo, "cells", allowed_conditions)
    tag_of = dict(zip(items["dataset"], items["tag"]))
    n_test = items[items.split == "test"].groupby("dataset").size().to_dict()
    out = []
    test = lo[lo["split"] == "test"]
    for (ds, rd, L, render, cond), g in test.groupby(["dataset", "reader", "layer", "render", "condition"]):
        a, lo_, hi = auroc_ci(g["label"].values, g["score"].values, n_boot=n_boot)
        out.append({"dataset": ds, "tag": tag_of.get(ds), "reader": rd, "layer": int(L), "render": render, "condition": cond,
                    "auroc": a, "ci_lo": lo_, "ci_hi": hi, "n": len(g), "coverage": len(g) / max(1, n_test.get(ds, len(g)))})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ probes
def _fit_logreg(Xtr: np.ndarray, ytr: np.ndarray, Cval: float, seed: int = 0):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    clf = make_pipeline(StandardScaler(), LogisticRegression(C=Cval, max_iter=2000, random_state=seed))
    clf.fit(Xtr, ytr)
    return clf


def _cv_splits(n: int, y: np.ndarray, seed: int):
    """The SAE-probing validation scheme: leave-two-out below 13, 6-fold below 128, one 20% split otherwise.
    (Leave-two-out is realised as repeated leave-one-pair-out over at most 20 pairs.)"""
    from sklearn.model_selection import StratifiedKFold, train_test_split

    rng = np.random.default_rng(seed)
    idx = np.arange(n)
    if n < 13:
        pos, neg = idx[y == 1], idx[y == 0]
        pairs = [(p, q) for p in pos for q in neg]
        rng.shuffle(pairs)
        for p, q in pairs[:20]:
            tr = np.array([i for i in idx if i not in (p, q)])
            yield tr, np.array([p, q])
    elif n < 128:
        k = min(6, int(np.bincount(y).min()))
        if k < 2:
            return
        for tr, va in StratifiedKFold(k, shuffle=True, random_state=seed).split(idx, y):
            yield tr, va
    else:
        tr, va = train_test_split(idx, test_size=0.2, stratify=y, random_state=seed)
        yield tr, va


def probe_fit_select(Xtr: np.ndarray, ytr: np.ndarray, seed: int, grid: tuple[float, ...] = C_GRID) -> tuple[Any, float, float]:
    """Inner-CV choice of C (validation AUC = mean fold AUC of the chosen C), refit on all n. Returns (clf, C, val_auc).
    For n < 4 there is nothing to validate on: C = 1 and val_auc = the training AUC (recorded as such)."""
    n = len(ytr)
    if n < 4 or np.bincount(ytr, minlength=2).min() < 2:
        clf = _fit_logreg(Xtr, ytr, 1.0, seed)
        return clf, 1.0, auroc(ytr, clf.decision_function(Xtr))
    best = (-1.0, 1.0)
    for Cval in grid:
        scores = np.full(n, np.nan)
        per_fold = []
        for tr, va in _cv_splits(n, ytr, seed):
            clf = _fit_logreg(Xtr[tr], ytr[tr], Cval, seed)
            s = clf.decision_function(Xtr[va])
            if n < 13:
                per_fold.append(float(s[ytr[va] == 1][0] > s[ytr[va] == 0][0]))  # pair ordered correctly?
            else:
                scores[va] = s
        val = float(np.mean(per_fold)) if n < 13 else auroc(ytr, scores)
        if val > best[0]:
            best = (val, Cval)
    clf = _fit_logreg(Xtr, ytr, best[1], seed)
    return clf, best[1], best[0]


def balanced_draw(pool_idx: np.ndarray, y: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    pos = pool_idx[y[pool_idx] == 1]
    neg = pool_idx[y[pool_idx] == 0]
    k = min(n // 2, len(pos), len(neg))
    return np.concatenate([rng.choice(pos, k, replace=False), rng.choice(neg, k, replace=False)])


# ------------------------------------------------------------------ R1: learning curves + quiver
def r1_run(P: Paths, items: pd.DataFrame, lo: pd.DataFrame, layers: tuple[int, ...] = (42,), render: str = PRIMARY_RENDER,
           ns: tuple[int, ...] = NS, seeds: tuple[int, ...] = SEEDS, datasets: list[str] | None = None, n_jobs: int = 1
           ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per dataset × layer × n × seed: probe val/test AUC; per dataset × n × seed: the quiver (probe-only vs with readers).
    Reader arrows live at their primary site (chat render, PRIMARY_LAYER) and need scores on the pool-eval items."""
    from joblib import Parallel, delayed

    dss = datasets or sorted(items["dataset"].unique())
    # only facts / layers whose states are on disk, and each job gets its own dataset's rows (not the whole frame)
    jobs = [(ds, L) for ds in dss for L in layers if (P.cache / "states" / ds / f"{render}_L{L}.npy").exists()]
    if not jobs:
        return pd.DataFrame(), pd.DataFrame()
    need = {ds for ds, _ in jobs}
    lo_by = {ds: g for ds, g in lo[lo.dataset.isin(need)].groupby("dataset")} if len(lo) else {}
    it_by = {ds: g for ds, g in items[items.dataset.isin(need)].groupby("dataset")}
    res = Parallel(n_jobs=n_jobs)(delayed(_r1_one)(P, it_by[ds], lo_by.get(ds, lo.iloc[:0]), ds, L, render, ns, seeds) for ds, L in jobs)
    curves = pd.concat([r[0] for r in res if len(r[0])], ignore_index=True) if any(len(r[0]) for r in res) else pd.DataFrame()
    quiver = pd.concat([r[1] for r in res if len(r[1])], ignore_index=True) if any(len(r[1]) for r in res) else pd.DataFrame()
    return curves, quiver


def _r1_one(P: Paths, items: pd.DataFrame, lo: pd.DataFrame, ds: str, layer: int, render: str, ns, seeds) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cached per fit: the result for (dataset, layer, render) is reused while the states file, the reader scores that
    feed the quiver, ns and seeds are unchanged. The cache lives in the analysing checkout (``<root>/.ws3_cache/r1``,
    git-excluded), never in the shared cache: other streams' "cache untouched" guard tests snapshot that tree."""
    import hashlib
    import pickle

    sf = P.cache / "states" / ds / f"{render}_L{layer}.npy"
    if not sf.exists():  # states not synced yet (shards arrive incrementally): no curve for this fact / layer
        return pd.DataFrame(), pd.DataFrame()
    sub = lo[(lo.dataset == ds) & (lo.render == PRIMARY_RENDER) & (lo.condition == "natural")] if layer == L_READ and render == PRIMARY_RENDER else lo.iloc[:0]
    sig = hashlib.sha256(json.dumps([sf.stat().st_size, sf.stat().st_mtime_ns, list(ns), list(seeds),
                                     pd.util.hash_pandas_object(sub[["reader", "layer", "item_id", "score"]], index=False).sum().item() if len(sub) else 0]
                                    ).encode()).hexdigest()[:16]
    cdir = P.root / ".ws3_cache" / "r1"
    cfile = cdir / f"{ds}__{render}__L{layer}__{sig}.pkl"
    if cfile.exists():
        return pickle.loads(cfile.read_bytes())
    try:
        res = _r1_fit(P, items, lo, ds, layer, render, ns, seeds)
    except (ValueError, EOFError, OSError):  # a states file still being synced (truncated .npy): skip, never cache
        return pd.DataFrame(), pd.DataFrame()
    cdir.mkdir(parents=True, exist_ok=True)
    for old in cdir.glob(f"{ds}__{render}__L{layer}__*.pkl"):
        old.unlink()
    cfile.write_bytes(pickle.dumps(res))
    return res


def _r1_fit(P: Paths, items: pd.DataFrame, lo: pd.DataFrame, ds: str, layer: int, render: str, ns, seeds) -> tuple[pd.DataFrame, pd.DataFrame]:
    X, idx = load_states(P, ds, render, layer)
    it = items[items.dataset == ds].set_index("item_id").loc[idx]
    y = it["label"].values.astype(int)
    split = it["split"].values
    pos_of = {iid: i for i, iid in enumerate(idx)}
    test_idx = np.where(split == "test")[0]
    pool_idx = np.where(split == "pool")[0]
    # reader scores at the primary site (quiver arrows): test scores and pool-eval scores
    readers: dict[str, dict[str, np.ndarray]] = {}
    sub = lo[(lo.dataset == ds) & (lo.render == PRIMARY_RENDER) & (lo.condition == "natural")]
    for rd, g in sub.groupby("reader"):
        g = g[g.layer == PRIMARY_LAYER.get(rd, 42)]
        if g.empty:
            continue
        s = np.full(len(idx), np.nan)
        for iid, sc in zip(g["item_id"], g["score"]):
            if iid in pos_of:
                s[pos_of[iid]] = sc
        readers[rd] = {"score": s}
    eval_pool = np.array([i for i in pool_idx if any(np.isfinite(r["score"][i]) for r in readers.values())]) if readers else pool_idx
    curve_rows, quiver_rows = [], []
    for seed in seeds:
        rng = np.random.default_rng(1000 * seed + layer)
        for n in ns:
            draw_from = eval_pool if (n <= len(eval_pool) and len(eval_pool) >= 4) else pool_idx
            tr = balanced_draw(draw_from, y, n, rng)
            if len(tr) < 2 or np.bincount(y[tr], minlength=2).min() < 1:
                continue
            clf, Cv, val = probe_fit_select(X[tr], y[tr], seed)
            test_auc = auroc(y[test_idx], clf.decision_function(X[test_idx]))
            curve_rows.append({"dataset": ds, "layer": layer, "render": render, "n": int(len(tr)), "n_req": n, "seed": seed, "C": Cv,
                               "val_auc": val, "test_auc": test_auc})
            if layer != PRIMARY_LAYER["jlens"] or render != PRIMARY_RENDER or not readers:
                continue
            # the quiver: arrows = probe(n), each reader (zero-shot), each reader+probe stack (n >= 8)
            arrows = {"probe": (val, test_auc)}
            for rd, r in readers.items():
                s = r["score"]
                tr_ok = tr[np.isfinite(s[tr])]
                if len(tr_ok) >= 2 and len(set(y[tr_ok])) == 2:
                    v = auroc(y[tr_ok], s[tr_ok])
                    v = max(v, 1 - v) if False else v   # orientation is fixed a priori (pos > neg); no flipping on the labels
                else:
                    v = np.nan
                t = auroc(y[test_idx], s[test_idx])
                arrows[rd] = (v, t)
                if len(tr_ok) >= 8 and np.isfinite(v):
                    from sklearn.model_selection import cross_val_predict

                    try:
                        dec_tr = cross_val_predict(_fit_logreg(X[tr_ok], y[tr_ok], Cv, seed), X[tr_ok], y[tr_ok],
                                                   cv=min(4, int(np.bincount(y[tr_ok]).min())), method="decision_function")
                        F_tr = np.c_[dec_tr, s[tr_ok]]
                        F_te = np.c_[clf.decision_function(X[test_idx]), s[test_idx]]
                        ok = np.isfinite(F_te).all(1)
                        st, _, sv = probe_fit_select(F_tr, y[tr_ok], seed, grid=(1.0,))
                        arrows[f"stack:{rd}"] = (sv, auroc(y[test_idx][ok], st.decision_function(F_te[ok])))
                    except Exception:
                        pass
            best_probe = arrows["probe"]
            cand = {k: v for k, v in arrows.items() if np.isfinite(v[0])}
            best_all_name = max(cand, key=lambda k: cand[k][0]) if cand else "probe"
            quiver_rows.append({"dataset": ds, "n": int(len(tr)), "n_req": n, "seed": seed, "probe_test": best_probe[1],
                                "chosen": best_all_name, "chosen_test": arrows[best_all_name][1],
                                "delta": arrows[best_all_name][1] - best_probe[1],
                                **{f"{k}_val": v[0] for k, v in arrows.items()}, **{f"{k}_test": v[1] for k, v in arrows.items()}})
    return pd.DataFrame(curve_rows), pd.DataFrame(quiver_rows)


def nstar_table(curves: pd.DataFrame, cells: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """n* per (dataset, reader): the smallest probe training size whose median test AUC reaches the reader's AUROC at
    its primary site (log-linear interpolation on the n grid); '<2' / '>512' at the ends."""
    tag_of = dict(zip(items["dataset"], items["tag"]))
    med = curves[(curves.layer == PRIMARY_LAYER["jlens"]) & (curves.render == PRIMARY_RENDER)].groupby(["dataset", "n_req"])["test_auc"].median()
    prim = cells[(cells.condition == "natural") & (cells.render == PRIMARY_RENDER)]
    prim = prim[prim.apply(lambda r: r.layer == PRIMARY_LAYER.get(r.reader, 42), axis=1)]
    out = []
    for r in prim.itertuples(index=False):
        if r.dataset not in med.index.get_level_values(0):
            continue
        m = med.loc[r.dataset].sort_index()
        ns_, aucs = np.array(m.index, float), m.values
        a = r.auroc
        if not np.isfinite(a):
            continue
        if a <= aucs[0]:
            nstar, label = ns_[0], f"<{int(ns_[0])}"
        elif a > np.nanmax(aucs):
            nstar, label = np.inf, f">{int(ns_[-1])}"
        else:
            k = int(np.argmax(aucs >= a))  # first grid point at or above the reader
            x0, x1, y0, y1 = np.log2(ns_[k - 1]), np.log2(ns_[k]), aucs[k - 1], aucs[k]
            nstar = 2 ** (x0 + (a - y0) / max(1e-9, y1 - y0) * (x1 - x0))
            label = f"{nstar:.1f}"
        out.append({"dataset": r.dataset, "tag": tag_of.get(r.dataset), "reader": r.reader, "reader_auroc": a, "probe512_auroc": float(aucs[-1]),
                    "nstar": nstar, "nstar_label": label})
    return pd.DataFrame(out)


def quiver_summary(quiver: pd.DataFrame) -> pd.DataFrame:
    out = []
    for n, g in quiver.groupby("n_req"):
        per_fact = g.groupby("dataset")["delta"].mean()
        m, lo_, hi = mean_ci(per_fact.values)
        chosen = g["chosen"].value_counts(normalize=True).to_dict()
        out.append({"n": int(n), "n_facts": len(per_fact), "delta_mean": m, "ci_lo": lo_, "ci_hi": hi,
                    "frac_non_probe_chosen": 1 - chosen.get("probe", 0.0), "adds_value": bool(lo_ > 0 and m >= 0.01)})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ R2: the model-report ceiling
def r2_ceiling(lo: pd.DataFrame, po: pd.DataFrame, items: pd.DataFrame, n_boot: int = 500) -> pd.DataFrame:
    tag_of = dict(zip(items["dataset"], items["tag"]))
    test_ids = set(items[items.split == "test"]["item_id"])
    pot = po[po.item_id.isin(test_ids) & po["lo"].notna()]
    out = []
    for ds, gp in pot.groupby("dataset"):
        ceil_a, c_lo, c_hi = auroc_ci(gp["label"].values, gp["lo"].values, n_boot=n_boot)
        base = {"dataset": ds, "tag": tag_of.get(ds), "prompt_only_auroc": ceil_a, "prompt_only_lo": c_lo, "prompt_only_hi": c_hi,
                "prompt_only_acc": float(((gp["lo"] > 0).astype(int) == gp["label"]).mean())}
        sub = lo[(lo.dataset == ds) & (lo.split == "test") & (lo.condition == "natural")]
        for (rd, L, render), g in sub.groupby(["reader", "layer", "render"]):
            m = g.merge(gp[["item_id", "lo"]].rename(columns={"lo": "po_lo"}), on="item_id")
            if len(m) < 10:
                continue
            d, d_lo, d_hi = paired_auroc_diff(m["label"].values, m["score"].values, m["po_lo"].values, n_boot=n_boot)
            out.append({**base, "reader": rd, "layer": int(L), "render": render, "reader_auroc": auroc(m["label"].values, m["score"].values),
                        "diff": d, "diff_lo": d_lo, "diff_hi": d_hi, "exceeds_ceiling": bool(d >= 0.05 and d_lo > 0)})
    return pd.DataFrame(out)


def shuffled_check(cells: pd.DataFrame, band: tuple[float, float] = (0.45, 0.55)) -> pd.DataFrame:
    """BRIEF_R §4.2 (rule as amended 2026-10-18): a shuffled cell passes iff its 95% CI includes 0.5; failing cells are
    inspected as pipeline bugs first. ``frac_in_band`` keeps the old fixed-band descriptive, next to the fraction of
    healthy cells (CI ∋ 0.5) that a fixed band would still flag (``frac_healthy_outside_band``)."""
    s = cells[cells.condition == "shuf"]
    has_ci = s["ci_lo"].notna() & s["ci_hi"].notna() if len(s) else pd.Series(dtype=bool)
    ci_ok = (s["ci_lo"] <= 0.5) & (s["ci_hi"] >= 0.5) if len(s) else pd.Series(dtype=bool)
    in_band = s["auroc"].between(*band) if len(s) else pd.Series(dtype=bool)
    healthy = s[ci_ok & has_ci] if len(s) else s
    return pd.DataFrame([{"n_cells": len(s), "rule": "95% CI includes 0.5",
                          "frac_ci_includes_half": float(ci_ok[has_ci].mean()) if has_ci.any() else np.nan,
                          "n_fail": int((~ci_ok & has_ci).sum()) if len(s) else 0,
                          "frac_in_band": float(in_band.mean()) if len(s) else np.nan,
                          "frac_healthy_outside_band": float((~healthy["auroc"].between(*band)).mean()) if len(healthy) else np.nan,
                          "band": list(band),
                          "worst": s.loc[(s["auroc"] - 0.5).abs().idxmax()].to_dict() if len(s) else None,
                          "failing": s[~ci_ok & has_ci][["dataset", "reader", "layer", "render", "auroc", "ci_lo", "ci_hi"]].to_dict("records") if len(s) else []}])


def state_free_check(P: Paths, lo: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """BRIEF_R §2.2 state-free control (descriptive; no decision rule): the reader's score on the dataset-mean state is
    its candidate prior. Per (dataset, reader, layer, render): the prior's score, its z against the natural test scores,
    and on two-sided facts the fraction of natural test items whose s_diff has the prior's sign (``prior_side_frac``;
    ≈ 1 = the reader answers its prior whatever the state), next to the natural AUROC. Two-sided facts use lo; one-sided facts lp_A, as ``primary_score``."""
    sf = _bank_only(read_jsonl_shards(P.cache, "state_free", datasets=set(items["dataset"])), items, "state_free")
    assert_conditions(sf, "state_free")
    if sf.empty or lo.empty:
        return pd.DataFrame()
    sided_of = dict(zip(items["dataset"], items["sided"]))
    sf = sf[(sf.get("unscorable", False) != True) & sf.dataset.isin(set(items.dataset))].copy()  # noqa: E712
    if "pair_index" in sf.columns:
        sf = sf[sf["pair_index"].fillna(0) == 0]
    sf["sf_score"] = primary_score(sf, sided_of)
    nat = lo[(lo.split == "test") & (lo.condition == "natural") & (lo.reader != "logit_lens")]
    out = []
    keys = ["dataset", "reader", "layer", "render"]
    sfi = sf.set_index(keys)["sf_score"]
    for k, g in nat.groupby(keys):
        if k not in sfi.index:
            continue
        v = sfi.loc[k]
        v = float(v.iloc[0]) if isinstance(v, pd.Series) else float(v)
        med = float(np.nanmedian(g["score"]))
        two = sided_of.get(k[0]) == "two"
        out.append(dict(zip(keys, k), sf_score=v, natural_median=med, natural_sd=float(np.nanstd(g["score"])),
                        prior_z=(v - med) / max(1e-9, float(np.nanstd(g["score"]))),
                        prior_side_frac=float((np.sign(g["score"]) == np.sign(v)).mean()) if two and v != 0 else np.nan,
                        auroc=auroc(g["label"].values, g["score"].values), n=len(g)))
    return pd.DataFrame(out)


# ------------------------------------------------------------------ R3: conflict
def r3_conflict(lo: pd.DataFrame, po: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """On test items where the model's own forced choice disagrees with the label: does the reader's vote (score above
    the dataset's test median — label-free) side with the MODEL or with the TEXT label?"""
    tag_of = dict(zip(items["dataset"], items["tag"]))
    pot = po[po["model_says_pos"].notna()].copy()
    pot["model_pos"] = pot["model_says_pos"].astype(bool)
    pot["conflict"] = pot["model_pos"] != pot["label"].astype(bool)
    out = []
    for (ds, rd, L, render), g in lo[(lo.split == "test") & (lo.condition == "natural")].groupby(["dataset", "reader", "layer", "render"]):
        m = g.merge(pot[["item_id", "model_pos", "conflict"]], on="item_id")
        if m.empty:
            continue
        thr = np.nanmedian(m["score"])
        m["vote_pos"] = m["score"] > thr
        conf = m[m["conflict"]]
        agree = m[~m["conflict"]]
        n = len(conf)
        if n == 0:
            continue
        k_model = int((conf["vote_pos"] == conf["model_pos"]).sum())
        p_model, lo_m, hi_m = wilson(k_model, n)
        k_ctrl = int((agree["vote_pos"] == agree["model_pos"]).sum())
        verdict = "READS_MODEL" if (p_model >= 0.75 and lo_m > 0.5) else "READS_TEXT" if (p_model <= 0.25 and hi_m < 0.5) else "MIXED"
        out.append({"dataset": ds, "tag": tag_of.get(ds), "reader": rd, "layer": int(L), "render": render, "n_conflict": n,
                    "p_model": p_model, "p_model_lo": lo_m, "p_model_hi": hi_m, "p_text": 1 - p_model,
                    "control_acc_on_agree": k_ctrl / max(1, len(agree)), "verdict": verdict})
    return pd.DataFrame(out)


def r3_probe_reference(P: Paths, po: pd.DataFrame, items: pd.DataFrame, layers: tuple[int, ...], render: str = PRIMARY_RENDER) -> pd.DataFrame:
    """A probe trained on the pool to predict the MODEL's answer, evaluated on the conflict test items: the PRESENT
    reference for R3 (BRIEF_R §4.3)."""
    pot = po[po["model_says_pos"].notna()].copy()
    model_pos = dict(zip(pot["item_id"], pot["model_says_pos"].astype(bool)))
    out = []
    for ds in sorted(items.dataset.unique()):
        for L in layers:
            try:
                X, idx = load_states(P, ds, render, L)
            except FileNotFoundError:
                continue
            it = items[items.dataset == ds].set_index("item_id").loc[idx]
            ym = np.array([model_pos.get(i, np.nan) for i in idx], dtype=float)
            ok = np.isfinite(ym)
            yl = it["label"].values.astype(int)
            pool = np.where((it["split"].values == "pool") & ok)[0]
            test = np.where((it["split"].values == "test") & ok)[0]
            conf = test[ym[test].astype(int) != yl[test]]
            if len(pool) < 16 or len(conf) == 0 or len(set(ym[pool])) < 2:
                continue
            clf, Cv, _ = probe_fit_select(X[pool], ym[pool].astype(int), 0)
            k = int(((clf.decision_function(X[conf]) > 0).astype(int) == ym[conf].astype(int)).sum())
            p, lo_, hi = wilson(k, len(conf))
            out.append({"dataset": ds, "layer": L, "render": render, "n_conflict": len(conf), "probe_p_model": p, "lo": lo_, "hi": hi})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ R4: site
def r4_site(cells: pd.DataFrame, curves_by_layer: pd.DataFrame, items: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    tag_of = dict(zip(items["dataset"], items["tag"]))
    probe = curves_by_layer[curves_by_layer.n_req == max(curves_by_layer.n_req)].groupby(["dataset", "render", "layer"])["test_auc"].median().reset_index()
    probe = probe.rename(columns={"test_auc": "auroc"})
    probe["reader"] = "probe"
    nat = cells[cells.condition == "natural"][["dataset", "reader", "layer", "render", "auroc"]]
    allm = pd.concat([nat, probe], ignore_index=True)
    out = []
    for (ds, render), g in allm.groupby(["dataset", "render"]):
        pr = g[g.reader == "probe"].sort_values("layer")
        if pr.empty:
            continue
        L_present = _first_layer(pr, 0.9 * pr["auroc"].max(), 0.75)
        for rd, gr in g[g.reader != "probe"].groupby("reader"):
            gr = gr.sort_values("layer")
            L_read = _first_layer(gr, 0.9 * gr["auroc"].max(), 0.75)
            out.append({"dataset": ds, "tag": tag_of.get(ds), "render": render, "reader": rd, "L_present": L_present, "L_read": L_read,
                        "lag": (L_read - L_present) if (L_read is not None and L_present is not None) else np.nan,
                        "probe_max": pr["auroc"].max(), "reader_max": gr["auroc"].max(), "n_layers_reader": len(gr)})
    lag = pd.DataFrame(out)
    # render shift at the primary site
    shift = []
    prim = cells[(cells.condition == "natural")]
    for (ds, rd, L), g in prim.groupby(["dataset", "reader", "layer"]):
        a = g.set_index("render")["auroc"]
        if "chat" in a and "raw" in a:
            shift.append({"dataset": ds, "tag": tag_of.get(ds), "reader": rd, "layer": int(L), "chat": a["chat"], "raw": a["raw"], "delta": a["chat"] - a["raw"]})
    pshift = []
    for ds, g in probe.groupby("dataset"):
        a = g[g.layer == PRIMARY_LAYER["jlens"]].set_index("render")["auroc"]
        if "chat" in a and "raw" in a:
            pshift.append({"dataset": ds, "tag": tag_of.get(ds), "reader": "probe", "layer": PRIMARY_LAYER["jlens"], "chat": a["chat"], "raw": a["raw"], "delta": a["chat"] - a["raw"]})
    return lag, pd.DataFrame(shift + pshift)


def _first_layer(g: pd.DataFrame, frac_thr: float, abs_thr: float) -> int | None:
    for r in g.itertuples(index=False):
        if r.auroc >= frac_thr and r.auroc >= abs_thr:
            return int(r.layer)
    return None


# ------------------------------------------------------------------ R6: k-way
def r6_kway(P: Paths) -> pd.DataFrame:
    kl = read_jsonl_shards(P.cache, "kway_lo")
    po = read_jsonl_shards(P.cache, "prompt_only")
    if kl.empty or not P.items_k().exists():
        return pd.DataFrame()
    kitems = pd.DataFrame(json.loads(P.items_k().read_text())["items"])
    out = []
    for (ds, rd, L, render), g in kl[kl.get("unscorable", False) != True].groupby(["dataset", "reader", "layer", "render"]):  # noqa: E712
        piv = g.pivot_table(index="item_id", columns="cand_index", values="lp")
        lab = g.groupby("item_id")["label"].first().loc[piv.index]
        k = piv.shape[1]
        pred = piv.values.argmax(1)
        acc = float((pred == lab.values).mean())
        # two-way AUROC on every class pair (one-sided scores of the two classes' candidates)
        pair_aucs = []
        for a in range(k):
            for b in range(a + 1, k):
                m = lab.isin([a, b]).values
                if m.sum() >= 10:
                    pair_aucs.append(auroc((lab.values[m] == a).astype(int), piv.values[m, a] - piv.values[m, b]))
        out.append({"dataset": ds, "method": rd, "layer": int(L), "render": render, "k": k, "kway_acc": acc, "chance": 1 / k,
                    "twoway_auroc_mean": float(np.nanmean(pair_aucs)) if pair_aucs else np.nan, "n": len(piv)})
    # the model's own k-way answer
    pk = po[po.dataset.isin(kl.dataset.unique()) & po.item_id.isin(kitems[kitems.split == "test"]["item_id"])]
    for ds, g in pk.groupby("dataset"):
        out.append({"dataset": ds, "method": "prompt_only", "layer": np.nan, "render": "chat", "k": len(g.iloc[0]["lp"]),
                    "kway_acc": float((g["greedy"] == g["label"]).mean()), "chance": 1 / len(g.iloc[0]["lp"]), "twoway_auroc_mean": np.nan, "n": len(g)})
    # a k-class probe on the pool
    for ds in kl.dataset.unique():
        for L in sorted(kl[kl.dataset == ds].layer.unique()):
            try:
                X, idx = load_states(P, ds, "chat", int(L))
            except FileNotFoundError:
                continue
            it = kitems.set_index("item_id").loc[idx]
            y, split = it["label"].values.astype(int), it["split"].values
            pool, test = np.where(split == "pool")[0], np.where(split == "test")[0]
            if len(pool) < 10:
                continue
            clf = _fit_logreg(X[pool], y[pool], 1.0)
            out.append({"dataset": ds, "method": "probe", "layer": int(L), "render": "chat", "k": int(y.max() + 1),
                        "kway_acc": float((clf.predict(X[test]) == y[test]).mean()), "chance": 1 / (y.max() + 1), "twoway_auroc_mean": np.nan, "n": len(test)})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ R7: agreement
def r7_agreement(lo: pd.DataFrame, items: pd.DataFrame, vote: str = "median") -> pd.DataFrame:
    """Votes at the primary sites: consensus accuracy vs the best single reader on the covered items, pairwise kappa,
    shared-wrong ratio vs independence. ``vote="median"`` (as implemented since the scaffold): score above the reader's
    dataset test median on EVERY fact. ``vote="s47"`` (BRIEF_R §4.7 literal): the sign of s_diff on two-sided facts, the
    dataset median on one-sided facts, by each fact's sidedness in the bank. TH-2 found the deviation on 2026-10-19;
    both are reported (BRIEF_R Deviations, WS3)."""
    from sklearn.metrics import cohen_kappa_score

    prim = lo[(lo.split == "test") & (lo.condition == "natural") & (lo.render == PRIMARY_RENDER)]
    prim = prim[prim.apply(lambda r: r.layer == PRIMARY_LAYER.get(r.reader, 42), axis=1)]
    prim = prim[prim.reader != "logit_lens"]
    sided_of = dict(zip(items["dataset"], items["sided"]))
    out = []
    for ds, g in prim.groupby("dataset"):
        votes = {}
        two_sided = sided_of.get(ds) == "two"
        for rd, gr in g.groupby("reader"):
            thr = 0.0 if (vote == "s47" and two_sided) else np.nanmedian(gr["score"])  # §4.7: sign of s_diff on two-sided facts
            votes[rd] = gr.set_index("item_id")["score"].gt(thr).astype(int)
        if len(votes) < 2:
            continue
        V = pd.DataFrame(votes).dropna()
        lab = g.groupby("item_id")["label"].first().loc[V.index]
        correct = V.eq(lab.values[:, None], axis=0)
        acc = correct.mean()
        best = acc.idxmax()
        unanimous = V.nunique(axis=1) == 1
        cons_acc = float(correct[unanimous].iloc[:, 0].mean()) if unanimous.any() else np.nan
        best_on_covered = float(correct.loc[unanimous, best].mean()) if unanimous.any() else np.nan
        all_wrong = float((~correct).all(axis=1).mean())
        indep = float(np.prod(1 - acc.values))
        kappas = {f"kappa_{a}_{b}": cohen_kappa_score(V[a], V[b]) for i, a in enumerate(V.columns) for b in V.columns[i + 1:]}
        out.append({"dataset": ds, "n_items": len(V), "readers": list(V.columns), "best_single": best, "best_single_acc": float(acc.max()),
                    "unanimous_frac": float(unanimous.mean()), "consensus_acc": cons_acc, "best_on_covered": best_on_covered,
                    "consensus_gain": cons_acc - best_on_covered if np.isfinite(cons_acc) else np.nan,
                    "shared_wrong": all_wrong, "shared_wrong_indep": indep, "shared_wrong_ratio": all_wrong / indep if indep > 0 else np.nan, **kappas})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ R8: confidence
def r8_confidence(lo: pd.DataFrame, po: pd.DataFrame) -> pd.DataFrame:
    from scipy.stats import spearmanr

    out = []
    pot = po[po["lo"].notna()][["item_id", "lo"]].rename(columns={"lo": "po_lo"})
    for (ds, rd, L, render), g in lo[(lo.split == "test") & (lo.condition == "natural")].groupby(["dataset", "reader", "layer", "render"]):
        m = g.merge(pot, on="item_id")
        if len(m) < 20:
            continue
        thr = np.nanmedian(m["score"])
        rho = spearmanr(np.abs(m["score"] - thr), np.abs(m["po_lo"])).correlation
        out.append({"dataset": ds, "reader": rd, "layer": int(L), "render": render, "rho_conf": float(rho), "n": len(m)})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ R5: selection, geometry, spoof / evade
def _save_if_changed(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """Rewrite a direction file only when its arrays change, so a stable selection leaves the shared cache untouched."""
    if path.exists():
        with np.load(path) as old:
            # the probe fit is reproducible to ~1e-9 per component (threaded lbfgs), so "unchanged" is a tolerance, not bytes
            if set(old.files) == set(arrays) and all(np.allclose(old[k], arrays[k], rtol=0, atol=1e-6) for k in arrays):
                return
    np.savez(path, **arrays)


POOL_EVAL = 64  # = collect.POOL_EVAL (not imported: collect pulls in torch)


def pool_eval_ids(items: pd.DataFrame, ds: str, n: int = POOL_EVAL) -> list[str]:
    """collect.pool_eval_items: the first n/2 pool items of each class in item order (BRIEF_R §2.3)."""
    pool = items[(items.dataset == ds) & (items.split == "pool")]
    return sorted(pool[pool.label == 1]["item_id"].tolist()[: n // 2] + pool[pool.label == 0]["item_id"].tolist()[: n // 2])


def pool_probe_auroc(P: Paths, items: pd.DataFrame, ds: str, layer: int = L_READ, k: int = 5, seed: int = 0) -> float:
    """§4.9 e: probe AUROC from inner-CV fits on the pool only (k-fold, C chosen inside each training fold), held-out
    decisions pooled over folds. Test items are never touched."""
    from sklearn.model_selection import StratifiedKFold

    try:
        X, idx = load_states(P, ds, PRIMARY_RENDER, layer)
    except FileNotFoundError:
        return np.nan
    it = items[items.dataset == ds].set_index("item_id").loc[idx]
    pool = np.where(it["split"].values == "pool")[0]
    y = it["label"].values.astype(int)[pool]
    if len(pool) < 2 * k or np.bincount(y, minlength=2).min() < k:
        return np.nan
    dec = np.full(len(pool), np.nan)
    for tr, te in StratifiedKFold(k, shuffle=True, random_state=seed).split(pool, y):
        clf, _, _ = probe_fit_select(X[pool[tr]], y[tr], seed)
        dec[te] = clf.decision_function(X[pool[te]])
    return auroc(y, dec)


def r5_select(P: Paths, cells: pd.DataFrame, po: pd.DataFrame, items: pd.DataFrame, curves: pd.DataFrame, n_facts: int = 30,
              n_items: int = 32, probe_min: float = 0.9, model_min: float = 0.9, select_on: str = "test",
              into_cache: bool = False) -> dict[str, Any]:
    """Facts with probe(512) ≥ probe_min and prompt-only AUROC ≥ model_min at block 42 (selection on those two numbers
    only); the first n_items test items (balanced); d_cm and d_probe at L_EDIT and L_READ from the pool states.
    select_on='pool' (§4.9 e, the pre-registered mode): probe AUROC from pool inner-CV, prompt-only AUROC on the 64
    POOL_EVAL items; the winner's curse (selected facts' test minus selection AUROC) is written next to the selection."""
    test_ids = set(items[items.split == "test"]["item_id"])
    if select_on == "pool":
        model_auc, pr_d = {}, {}
        for ds in sorted(items.dataset.unique()):
            if not (P.cache / "states" / ds / f"{PRIMARY_RENDER}_L{L_READ}.npy").exists():
                continue
            pe = set(pool_eval_ids(items, ds))
            g = po[po.item_id.isin(pe) & po["lo"].notna()]
            if len(g) >= 10 and g.label.nunique() == 2:
                model_auc[ds] = auroc(g["label"].values, g["lo"].values)
                pr_d[ds] = pool_probe_auroc(P, items, ds)
        pr = pd.Series(pr_d, dtype=float).dropna()
    else:
        pot = po[po.item_id.isin(test_ids) & po["lo"].notna()]
        model_auc = {ds: auroc(g["label"].values, g["lo"].values) for ds, g in pot.groupby("dataset")}
        pr = curves[(curves.layer == L_READ) & (curves.render == PRIMARY_RENDER) & (curves.n_req == curves.n_req.max())].groupby("dataset")["test_auc"].median()
    ok = [ds for ds in pr.index if pr[ds] >= probe_min and model_auc.get(ds, 0) >= model_min]
    ok = sorted(ok, key=lambda ds: -(pr[ds] + model_auc[ds]))[:n_facts]
    n_bank = int(items.dataset.nunique())
    n_states = sum(1 for ds in items.dataset.unique() if (P.cache / "states" / ds / f"{PRIMARY_RENDER}_L{L_READ}.npy").exists())
    sel: dict[str, Any] = {"created": pd.Timestamp.utcnow().isoformat(), "probe_min": probe_min, "model_min": model_min, "select_on": select_on,
                           "n_candidates": int(len(pr)), "n_bank_facts": n_bank, "n_facts_with_states": n_states,
                           # the top-30 can still change while facts are missing states: steer on it only when false
                           "provisional": n_states < n_bank, "datasets": {}}
    # cache/g_agreement/r/r5/ has a single writer (chat 7 / pod F, PLAN_R §9 rule 2): WS3 writes its copy in the analysing
    # checkout and the steering stream stages it onto the volume.
    # ``into_cache`` (--r5-into-cache) is for the owner of r5/ (chat 7, or a run on the steering pod): it writes straight to
    # cache/g_agreement/r/r5/directions/, where steer.py and r5_analyze read them.
    ddir = (P.cache / "r5" / "directions") if into_cache else (P.root / ".ws3_cache" / "r5" / "directions")
    ddir.mkdir(parents=True, exist_ok=True)
    for ds in ok:
        it = items[(items.dataset == ds) & (items.split == "test")]
        pos = it[it.label == 1]["item_id"].tolist()[: n_items // 2]
        neg = it[it.label == 0]["item_id"].tolist()[: n_items // 2]
        dirs: dict[str, np.ndarray] = {}
        scale = None
        for L in (L_EDIT, L_READ):
            try:
                X, idx = load_states(P, ds, PRIMARY_RENDER, L)
            except FileNotFoundError:
                continue
            iti = items[items.dataset == ds].set_index("item_id").loc[idx]
            y, split = iti["label"].values.astype(int), iti["split"].values
            pool = np.where(split == "pool")[0]
            d_cm = X[pool][y[pool] == 1].mean(0) - X[pool][y[pool] == 0].mean(0)
            if L == L_EDIT:
                scale = float(np.linalg.norm(d_cm))
            dirs[f"d_cm_L{L}"] = (d_cm / (np.linalg.norm(d_cm) + 1e-9)).astype(np.float32)
            clf, _, _ = probe_fit_select(X[pool], y[pool], 0)
            w = clf[-1].coef_[0] / clf[0].scale_  # back to the raw-activation frame
            dirs[f"d_probe_L{L}"] = (w / (np.linalg.norm(w) + 1e-9)).astype(np.float32)
        if scale is None:
            continue
        _save_if_changed(ddir / f"{ds}.npz", dirs)
        sel["datasets"][ds] = {"item_ids": pos + neg, "scale": scale, "probe_auroc": float(pr[ds]), "prompt_only_auroc": float(model_auc[ds]),
                               "cos_cm_probe_L38": float(dirs[f"d_cm_L{L_EDIT}"] @ dirs[f"d_probe_L{L_EDIT}"])}
    if select_on == "pool" and sel["datasets"]:  # winner's curse, reported only (computed after the selection is fixed)
        pot = po[po.item_id.isin(test_ids) & po["lo"].notna()]
        cp = curves[(curves.layer == L_READ) & (curves.render == PRIMARY_RENDER) & (curves.n_req == curves.n_req.max())].groupby("dataset")["test_auc"].median() if len(curves) else pd.Series(dtype=float)
        wc = []
        for ds, d in sel["datasets"].items():
            g = pot[pot.dataset == ds]
            d["prompt_only_auroc_test"] = auroc(g["label"].values, g["lo"].values) if len(g) else None
            d["probe_auroc_test"] = float(cp[ds]) if ds in cp.index else None
            if d["probe_auroc_test"] is not None:
                wc.append(d["probe_auroc_test"] - d["probe_auroc"])
        sel["winners_curse_probe_mean"] = float(np.mean(wc)) if wc else None
    sel["directions_dir"] = str(ddir)
    out = P.results / "r5_selection.json"
    if out.exists():  # rewrite only if the selection itself changed (not just the timestamp)
        old = json.loads(out.read_text())
        if {k: v for k, v in old.items() if k not in ("created", "directions_dir")} == {k: v for k, v in sel.items() if k not in ("created", "directions_dir")}:
            return old
    out.write_text(json.dumps(sel, indent=1))
    return sel


def r5_analyze(P: Paths, items: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Geometry (cosines between directions) and the dose–response: model LO shift toward the pushed class vs each
    reader's follow as a fraction of its natural separation; SPOOFABLE / EVADABLE per (reader, fact) by the BRIEF rules."""
    st = read_jsonl(P.cache / "r5" / "steer.jsonl")
    rr = read_jsonl(P.cache / "r5" / "readers.jsonl")
    if st.empty:
        return pd.DataFrame(), pd.DataFrame()
    sided_of = dict(zip(items["dataset"], items["sided"]))
    rr = rr[rr.get("unscorable", False) != True].copy()  # noqa: E712
    rr["score"] = primary_score(rr, sided_of)
    geo = []
    for f in sorted((P.cache / "r5" / "directions").glob("*.npz")):
        z = np.load(f)
        for Lg in (L_EDIT, L_READ):  # §4.5: directions at the edit layer 38 and at the read layer 42
            names = [k for k in z.files if k.endswith(f"_L{Lg}")]
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    va, vb = z[a].astype(np.float64), z[b].astype(np.float64)
                    geo.append({"dataset": f.stem, "layer": Lg, "a": a, "b": b,
                                "cos": float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))})
    geo = pd.DataFrame(geo)
    out = []
    for ds, g in st.groupby("dataset"):
        nat = g[g.direction == "natural"].set_index("item_id")
        lab = nat["label"]
        # the model: LO oriented toward the pushed (other) class; "flipped" when the sign crosses
        for (dname, alpha), ge in g[g.direction != "natural"].groupby(["direction", "alpha"]):
            ge = ge.set_index("item_id")
            sgn = ge["sign"]
            d_model = (ge["lo"] - nat.loc[ge.index, "lo"]) * sgn
            flipped = (np.sign(ge["lo"]) != np.sign(nat.loc[ge.index, "lo"])) & (np.sign(nat.loc[ge.index, "lo"]) == np.where(lab.loc[ge.index] == 1, 1, -1))
            row = {"dataset": ds, "direction": dname, "alpha": float(alpha), "n": len(ge), "model_shift": float(d_model.mean()),
                   "model_flip_rate": float(flipped.mean())}
            for rd, grr in rr[(rr.dataset == ds)].groupby("reader"):
                nr = grr[grr.direction == "natural"].set_index("item_id")["score"]
                sep = float(nr[lab.loc[nr.index] == 1].mean() - nr[lab.loc[nr.index] == 0].mean())
                ed = grr[(grr.direction == dname) & (grr.alpha == alpha)].set_index("item_id")["score"]
                common = ed.index.intersection(nr.index)
                if len(common) == 0 or not np.isfinite(sep) or abs(sep) < 1e-9:
                    continue
                follow = ((ed.loc[common] - nr.loc[common]) * sgn.loc[common]) / sep
                crossed = (np.sign(ed.loc[common] - np.nanmedian(nr)) != np.sign(nr.loc[common] - np.nanmedian(nr)))
                row[f"{rd}_follow"] = float(follow.mean())
                row[f"{rd}_cross_rate"] = float(crossed.mean())
                row[f"{rd}_natural_sep"] = sep
            out.append(row)
    dose = pd.DataFrame(out)
    # verdicts per (reader, fact): SPOOFABLE along the reader's own direction, EVADABLE along the probe direction
    verdicts = []
    readers = sorted({c[:-7] for c in dose.columns if c.endswith("_follow")})
    for ds, g in dose.groupby("dataset"):
        probe_rows = g[g.direction.str.startswith("d_probe")]
        for rd in readers:
            own = g[g.direction.str.startswith(f"d_{rd}_")]
            if own.empty:
                own = g[g.direction.str.startswith("d_cm")]  # readers without a gradient direction: the class-mean proxy
            spoof = evade = None
            cr = own[own[f"{rd}_cross_rate"] >= 0.75].sort_values("alpha")
            if not cr.empty:
                a = cr.iloc[0]["alpha"]
                pm = probe_rows[probe_rows.alpha == a]
                if not pm.empty:
                    spoof = bool(cr.iloc[0]["model_shift"] < 0.25 * pm.iloc[0]["model_shift"])
            fl = probe_rows[probe_rows.model_flip_rate >= 0.75].sort_values("alpha")
            if not fl.empty:
                evade = bool(fl.iloc[0][f"{rd}_follow"] < 0.5)
            verdicts.append({"dataset": ds, "reader": rd, "report_flippable": spoof, "reader_blind": evade,
                             "own_direction": own.iloc[0]["direction"] if not own.empty else None})
    return pd.concat([geo.assign(kind="cos"), dose.assign(kind="dose")], ignore_index=True), pd.DataFrame(verdicts)


# ------------------------------------------------------------------ figures
def _style():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
    return plt


TAG_COLORS = {"SURFACE": "#4C78A8", "TOPIC": "#72B7B2", "FORM": "#E45756", "KNOWLEDGE": "#F58518", "COMPUTED": "#B279A2", "META": "#9D755D",
              "INTERNAL": "#54A24B", "CONTEXT": "#EECA3B"}


def fig1_headline(cells: pd.DataFrame, nstar: pd.DataFrame, ceiling: pd.DataFrame, P: Paths, mock: bool) -> None:
    plt = _style()
    prim = nstar.copy()
    readers = [r for r in READER_ORDER if r in prim.reader.unique()]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    ax = axes[0]
    markers = {"jlens": "o", "olens": "s", "nla": "^", "skip_a": "D", "skip_d": "v", "logit_lens": "x"}
    for rd in readers:
        g = prim[prim.reader == rd]
        ax.scatter(g["probe512_auroc"], g["reader_auroc"], c=[TAG_COLORS.get(t, "grey") for t in g["tag"]], marker=markers.get(rd, "o"),
                   s=28, alpha=0.75, edgecolor="k", linewidth=0.3, label=rd)
    ax.plot([0.4, 1], [0.4, 1], "k--", lw=0.8)
    ax.set_xlabel("probe(512) AUROC (what is linearly present)")
    ax.set_ylabel("reader AUROC at its primary site")
    ax.set_title("F1a  readers vs the probe, per fact")
    ax.legend(fontsize=7, loc="upper left")
    for t, c in TAG_COLORS.items():
        if t in set(prim["tag"]):
            ax.scatter([], [], c=c, label=t)
    ax = axes[1]
    if len(ceiling):
        prim_c = ceiling[(ceiling.render == PRIMARY_RENDER) & ceiling.apply(lambda r: r.layer == PRIMARY_LAYER.get(r.reader, 42), axis=1)]
        for rd in readers:
            g = prim_c[prim_c.reader == rd]
            ax.scatter(g["prompt_only_auroc"], g["reader_auroc"], c=[TAG_COLORS.get(t, "grey") for t in g["tag"]], marker=markers.get(rd, "o"),
                       s=28, alpha=0.75, edgecolor="k", linewidth=0.3)
        ax.plot([0.4, 1], [0.4, 1], "k--", lw=0.8)
    ax.set_xlabel("prompt-only AUROC (the model's own report)")
    ax.set_ylabel("reader AUROC")
    ax.set_title("F1b  readers vs the model-report ceiling")
    ax = axes[2]
    data, labels = [], []
    for rd in readers:
        g = prim[prim.reader == rd]
        v = g["nstar"].replace(np.inf, 1024).clip(1, 1024)
        data.append(np.log2(v.values))
        labels.append(rd)
    if data:
        ax.boxplot(data, tick_labels=labels, showfliers=True)
        ax.set_yticks(range(0, 11))
        ax.set_yticklabels([("<2" if k == 0 else (">512" if k == 10 else str(2 ** k))) for k in range(0, 11)])
    ax.set_ylabel("label-equivalent n*  (probe size matching the reader)")
    ax.set_title("F1c  how many labels is a zero-shot reader worth?")
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=t) for t, c in TAG_COLORS.items() if t in set(prim["tag"])]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), fontsize=7, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(("MOCK DATA — " if mock else "") + "Phase R headline: what a reader is worth against a probe and against asking the model", y=1.02)
    fig.tight_layout()
    fig.savefig(P.fig / "F1_headline.png", bbox_inches="tight")
    plt.close(fig)


def fig2_quiver(qs: pd.DataFrame, quiver: pd.DataFrame, P: Paths, mock: bool) -> None:
    plt = _style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    ax = axes[0]
    ax.errorbar(qs["n"], qs["delta_mean"], yerr=[qs["delta_mean"] - qs["ci_lo"], qs["ci_hi"] - qs["delta_mean"]], fmt="o-", capsize=3)
    ax.axhline(0, color="k", lw=0.8)
    ax.axhline(0.01, color="grey", lw=0.8, ls=":")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("labelled examples n")
    ax.set_ylabel("Δ test AUC: quiver with readers − probes only")
    ax.set_title("F2a  does adding readers to the quiver help?")
    ax = axes[1]
    if len(quiver):
        ch = quiver.groupby(["n_req", "chosen"]).size().unstack(fill_value=0)
        ch = ch.div(ch.sum(1), axis=0)
        ch.plot(kind="bar", stacked=True, ax=ax, width=0.8, legend=True)
        ax.legend(fontsize=6, ncol=2)
    ax.set_xlabel("n")
    ax.set_ylabel("fraction of (fact, seed) picking each arrow")
    ax.set_title("F2b  which arrow validation picks")
    fig.suptitle(("MOCK DATA — " if mock else "") + "The quiver (selection by validation AUC, report test AUC)")
    fig.tight_layout()
    fig.savefig(P.fig / "F2_quiver.png", bbox_inches="tight")
    plt.close(fig)


def fig3_blindspot(cells: pd.DataFrame, curves: pd.DataFrame, ceiling: pd.DataFrame, items: pd.DataFrame, P: Paths, mock: bool) -> None:
    plt = _style()
    # tags from the item table; cells rows that are not in the bank (the --with-legacy R-D rows) carry their own tag
    tag_of = {**dict(zip(cells["dataset"], cells["tag"])), **dict(zip(items["dataset"], items["tag"]))}
    prim = cells[(cells.condition == "natural") & (cells.render == PRIMARY_RENDER)]
    prim = prim[prim.apply(lambda r: r.layer == PRIMARY_LAYER.get(r.reader, 42), axis=1)]
    M = prim.pivot_table(index="dataset", columns="reader", values="auroc")
    pr = curves[(curves.layer == L_READ) & (curves.render == PRIMARY_RENDER) & (curves.n_req == curves.n_req.max())].groupby("dataset")["test_auc"].median()
    M.insert(0, "probe(512)", pr)
    if len(ceiling):
        po = ceiling.groupby("dataset")["prompt_only_auroc"].first()
        M.insert(1, "prompt-only", po)
    M["tag"] = M.index.map(tag_of)
    M["_t"] = M["tag"].map({t: i for i, t in enumerate(TAG_ORDER)})
    M = M.sort_values(["_t", "probe(512)"], ascending=[True, False])
    cols = [c for c in ["probe(512)", "prompt-only"] + READER_ORDER if c in M.columns]
    fig, ax = plt.subplots(figsize=(0.55 * len(cols) + 3.5, 0.17 * len(M) + 1.5))
    im = ax.imshow(M[cols].values.astype(float), aspect="auto", cmap="viridis", vmin=0.5, vmax=1.0)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticks(range(len(M)))
    ax.set_yticklabels([f"{d[:28]}  [{t[:4]}]" for d, t in zip(M.index, M["tag"])], fontsize=6)
    for i, t in enumerate(M["tag"].values):
        ax.add_patch(plt.Rectangle((-0.5, i - 0.5), 0.12, 1, color=TAG_COLORS.get(t, "grey"), clip_on=False))
    fig.colorbar(im, ax=ax, label="AUROC on the test split", shrink=0.6)
    ax.set_title(("MOCK DATA — " if mock else "") + "F3  blind-spot map: facts × methods (chat render, primary sites)")
    fig.tight_layout()
    fig.savefig(P.fig / "F3_blindspot_map.png", bbox_inches="tight")
    plt.close(fig)


def fig4_conflict(conf: pd.DataFrame, probe_ref: pd.DataFrame, P: Paths, mock: bool) -> None:
    plt = _style()
    if conf.empty:
        return
    fig, ax = plt.subplots(figsize=(6.5, 4))
    g = conf[conf.render == PRIMARY_RENDER]
    for rd, gr in g.groupby("reader"):
        agg = gr.groupby("layer").apply(lambda d: np.average(d["p_model"], weights=d["n_conflict"]))
        ax.plot(agg.index, agg.values, "o-", label=rd)
    if len(probe_ref):
        agg = probe_ref.groupby("layer").apply(lambda d: np.average(d["probe_p_model"], weights=d["n_conflict"]))
        ax.plot(agg.index, agg.values, "k--", lw=1.5, label="probe for the model's answer")
    ax.axhline(0.5, color="grey", lw=0.8, ls=":")
    ax.set_ylim(0, 1)
    ax.set_xlabel("read layer")
    ax.set_ylabel("P(reader sides with the MODEL's answer) on conflict items")
    ax.set_title(("MOCK DATA — " if mock else "") + "F4  text or model? (items where the model disagrees with the label)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(P.fig / "F4_conflict.png", bbox_inches="tight")
    plt.close(fig)


def fig5_lag(lag: pd.DataFrame, P: Paths, mock: bool) -> None:
    plt = _style()
    if lag.empty:
        return
    g = lag[lag.render == PRIMARY_RENDER].dropna(subset=["lag"])
    fig, ax = plt.subplots(figsize=(7, 3.8))
    tags = [t for t in TAG_ORDER if t in set(g["tag"])]
    readers = [r for r in READER_ORDER if r in set(g["reader"])]
    w = 0.8 / max(1, len(readers))
    for j, rd in enumerate(readers):
        vals = [g[(g.tag == t) & (g.reader == rd)]["lag"].median() for t in tags]
        ax.bar(np.arange(len(tags)) + j * w, vals, width=w, label=rd)
    ax.set_xticks(np.arange(len(tags)) + 0.4 - w / 2)
    ax.set_xticklabels(tags)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("median lag in blocks: L_read − L_present")
    ax.set_title(("MOCK DATA — " if mock else "") + "F5  how many blocks after the probe does each reader report the fact?")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(P.fig / "F5_lag.png", bbox_inches="tight")
    plt.close(fig)


def fig6_geometry(r5: pd.DataFrame, P: Paths, mock: bool) -> None:
    plt = _style()
    if r5.empty:
        return
    cos = r5[r5.kind == "cos"]
    dose = r5[r5.kind == "dose"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    if len(cos):
        cos = cos.assign(pair=cos["a"].str.replace(f"_L{L_EDIT}", "") + " ~ " + cos["b"].str.replace(f"_L{L_EDIT}", ""))
        pairs = [p for p in cos["pair"].unique() if "rand" not in p]
        ax.boxplot([cos[cos.pair == p]["cos"].values for p in pairs], tick_labels=pairs, vert=False)
        ax.axvline(0, color="k", lw=0.8)
        ax.set_xlabel("cosine between directions (per fact)")
        ax.set_title("F6a  what the reader reads vs what the probe reads")
    ax = axes[1]
    fol = [c for c in dose.columns if c.endswith("_follow")]
    for dname, gd in dose.groupby(dose["direction"].str.replace(r"\d+$", "", regex=True)):
        agg = gd.groupby("alpha")[["model_shift"] + fol].mean()
        for c in fol:
            ax.plot(agg["model_shift"], agg[c], "o-", ms=4, label=f"{c[:-7]} along {dname.replace(f'_L{L_EDIT}', '')}")
    ax.set_xlabel("model answer shift toward the pushed class (nats)")
    ax.set_ylabel("reader follow (fraction of natural separation)")
    ax.set_title("F6b  spoof (up-left) and evade (down-right)")
    ax.legend(fontsize=5, ncol=2)
    fig.suptitle(("MOCK DATA — " if mock else "") + "R5 geometry and causal relevance")
    fig.tight_layout()
    fig.savefig(P.fig / "F6_geometry.png", bbox_inches="tight")
    plt.close(fig)


def fig7_kway(kw: pd.DataFrame, P: Paths, mock: bool) -> None:
    plt = _style()
    if kw.empty:
        return
    fig, ax = plt.subplots(figsize=(6, 3.8))
    for m, g in kw.groupby("method"):
        g = g[(g.render == "chat")]
        g = g[g.layer.isna() | (g.layer == g.layer.min())]
        ax.scatter(g["k"], g["kway_acc"], label=m, s=30)
    ks = sorted(kw["k"].unique())
    ax.plot(ks, [1 / k for k in ks], "k:", label="chance")
    ax.set_xlabel("k classes")
    ax.set_ylabel("k-way accuracy")
    ax.set_title(("MOCK DATA — " if mock else "") + "F7  contrast, not value: k-way readout")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(P.fig / "F7_kway.png", bbox_inches="tight")
    plt.close(fig)


def fig8_agreement(ag: pd.DataFrame, P: Paths, mock: bool) -> None:
    plt = _style()
    if ag.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    ax = axes[0]
    ax.scatter(ag["best_on_covered"], ag["consensus_acc"], s=25)
    ax.plot([0.4, 1], [0.4, 1], "k--", lw=0.8)
    ax.set_xlabel("best single reader, accuracy on unanimous items")
    ax.set_ylabel("consensus accuracy on the same items")
    ax.set_title("F8a  agreement adds nothing when it adds nothing")
    ax = axes[1]
    ax.hist(ag["shared_wrong_ratio"].dropna(), bins=15)
    ax.axvline(1, color="k", lw=0.8)
    ax.set_xlabel("P(all readers wrong) / independence")
    ax.set_title("F8b  shared errors")
    fig.suptitle(("MOCK DATA — " if mock else "") + "R7 agreement across facts")
    fig.tight_layout()
    fig.savefig(P.fig / "F8_agreement.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ summary
def write_summary(P: Paths, parts: dict[str, Any], mock: bool) -> Path:
    L = ["# Phase R — analysis summary" + (" (MOCK DATA)" if mock else ""), f"generated {pd.Timestamp.utcnow().isoformat()}", ""]
    if "provenance_dropped" in parts:
        d = parts["provenance_dropped"]
        L.append(f"Provenance: {sum(d.values())} pod-D / WS13 planted-fact rows dropped ({', '.join(f'{k} {v}' for k, v in d.items()) or 'none'}); "
                 f"every kept row asserted pod ∈ {sorted(ALLOWED_PODS | PROVENANCE['extra_pods'])}, git_sha {FROZEN_GIT_SHA}.\n")
    if "nstar" in parts and len(parts["nstar"]):
        ns = parts["nstar"]
        L.append("## R1 label-equivalent n* (median per reader; fraction of facts with n* > 16)")
        for rd, g in ns.groupby("reader"):
            v = g["nstar"].replace(np.inf, 1024)
            L.append(f"- {rd}: median n* {np.median(v):.1f}; > 16 on {(v > 16).mean():.0%} of {len(g)} facts; "
                     + "; ".join(f"{t} {np.median(gg['nstar'].replace(np.inf, 1024)):.1f}" for t, gg in g.groupby('tag')))
    if "quiver_summary" in parts and len(parts["quiver_summary"]):
        L.append("\n## R1 quiver ΔAUC(n) (with readers − probes only; mean over facts, 95% CI)")
        for r in parts["quiver_summary"].itertuples(index=False):
            L.append(f"- n = {r.n}: {r.delta_mean:+.3f} [{r.ci_lo:+.3f}, {r.ci_hi:+.3f}], non-probe arrow chosen {r.frac_non_probe_chosen:.0%} → "
                     f"{'ADDS VALUE' if r.adds_value else 'no'}")
    if "shuffled" in parts and len(parts["shuffled"]):
        s = parts["shuffled"].iloc[0]
        L.append(f"\n## Controls: shuffled-activation cells whose 95% CI includes 0.5: {s['frac_ci_includes_half']:.0%} of {s['n_cells']} "
                 f"({s['n_fail']} failing, inspected as pipeline bugs first); inside the fixed band {s['band']}: {s['frac_in_band']:.0%}; "
                 f"healthy cells a fixed band would flag: {s['frac_healthy_outside_band']:.0%}")
    if "ceiling" in parts and len(parts["ceiling"]):
        c = parts["ceiling"]
        prim = c[(c.render == PRIMARY_RENDER) & c.apply(lambda r: r.layer == PRIMARY_LAYER.get(r.reader, 42), axis=1)]
        L.append("\n## R2 model-report ceiling (reader − prompt-only AUROC at the primary site)")
        for rd, g in prim.groupby("reader"):
            L.append(f"- {rd}: mean diff {g['diff'].mean():+.3f}; exceeds the ceiling (≥ +0.05, CI > 0) on {int(g['exceeds_ceiling'].sum())}/{len(g)} facts: "
                     + ", ".join(g[g.exceeds_ceiling]["dataset"].tolist()[:8]))
        bt = prim.groupby("tag")["diff"].mean()
        L.append("- by tag: " + "; ".join(f"{t} {v:+.3f}" for t, v in bt.items()))
    if "conflict" in parts and len(parts["conflict"]):
        c = parts["conflict"][parts["conflict"].render == PRIMARY_RENDER]
        L.append("\n## R3 conflict: P(sides with the model) weighted by conflict items, per reader × layer")
        for (rd, Lr), g in c.groupby(["reader", "layer"]):
            p = np.average(g["p_model"], weights=g["n_conflict"])
            L.append(f"- {rd} L{Lr}: P(model) {p:.2f} over {int(g['n_conflict'].sum())} conflict items in {len(g)} facts; verdicts "
                     + ", ".join(f"{k} {v}" for k, v in g["verdict"].value_counts().items()))
    if "lag" in parts and len(parts["lag"]):
        g = parts["lag"][parts["lag"].render == PRIMARY_RENDER]
        L.append("\n## R4 lag (blocks after the probe), median by tag")
        for rd, gr in g.groupby("reader"):
            L.append(f"- {rd}: " + "; ".join(f"{t} {gg['lag'].median():+.0f}" for t, gg in gr.groupby("tag") if gg['lag'].notna().any()))
    if "shift" in parts and len(parts["shift"]):
        g = parts["shift"]
        L.append("\n## R4 render shift (chat − raw AUROC), median per method")
        for rd, gr in g.groupby("reader"):
            L.append(f"- {rd}: {gr['delta'].median():+.3f} (|Δ| ≤ 0.05 on {(gr['delta'].abs() <= 0.05).mean():.0%} of facts)")
    if "kway" in parts and len(parts["kway"]):
        L.append("\n## R6 k-way accuracy (chat)")
        for m, g in parts["kway"].groupby("method"):
            L.append(f"- {m}: " + "; ".join(f"{r.dataset} k={r.k} acc {r.kway_acc:.2f} (chance {r.chance:.2f})" for r in g.itertuples(index=False)))
    if "agreement" in parts and len(parts["agreement"]):
        a = parts["agreement"]
        L.append(f"\n## R7 agreement: consensus − best single on unanimous items: mean {a['consensus_gain'].mean():+.3f}; "
                 f"shared-wrong ratio median {a['shared_wrong_ratio'].median():.2f}")
    if "r5_verdicts" in parts and len(parts["r5_verdicts"]):
        v = parts["r5_verdicts"]
        L.append("\n## R5 spoof / evade")
        for rd, g in v.groupby("reader"):
            L.append(f"- {rd}: report-flippable on {int(g['report_flippable'].fillna(False).astype(bool).sum())}/{g['report_flippable'].notna().sum()} facts, "
                     f"reader-blind on {int(g['reader_blind'].fillna(False).astype(bool).sum())}/{g['reader_blind'].notna().sum()}")
    if "confidence" in parts and len(parts["confidence"]):
        c = parts["confidence"]
        L.append("\n## R8 confidence: Spearman(|reader score − median|, |model LO|), median per reader: "
                 + "; ".join(f"{rd} {g['rho_conf'].median():+.2f}" for rd, g in c.groupby("reader")))
    out = P.results / "analyze_summary.md"  # not summary.md: that is the Integrator's hand-kept claims ledger (2026-10-20)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mock", action="store_true", help="build a synthetic cache in --root (default: scratch) and analyse it")
    ap.add_argument("--root", type=Path, default=None, help="alternative repo root holding cache/ dataset/ results/")
    ap.add_argument("--only", nargs="*", default=None, help="subset of r1 r2 r3 r4 r5 r6 r7 r8")
    ap.add_argument("--r5-select", action="store_true")
    ap.add_argument("--select-on", choices=("pool", "test"), default="pool", help="§4.9 e: pool (pre-registered) or the old test-split selection")
    ap.add_argument("--r5-into-cache", action="store_true",
                    help="write directions to cache/g_agreement/r/r5/directions/ (steer.py's path); only for the writer of r5/ (chat 7 / pod F)")
    ap.add_argument("--layers", nargs="*", type=int, default=None, help="probe layers for the learning curves (default: 42; full sweep for r4)")
    ap.add_argument("--quick", action="store_true", help="2 seeds, fewer n")
    ap.add_argument("--n-jobs", type=int, default=1)
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--with-legacy", action="store_true",
                    help="append the R-D legacy rows (r_bench/legacy.py: X1, Y1/V1, V7c, W2 published rates) to cells.csv and F3")
    ap.add_argument("--extra-pods", nargs="*", default=None, help="pod ids beyond A1-A4/B/C that chat 6 reports (also R_EXTRA_PODS)")
    a = ap.parse_args(argv)
    import os

    PROVENANCE["extra_pods"] = set(a.extra_pods or []) | {x for x in os.environ.get("R_EXTRA_PODS", "").split(",") if x}
    PROVENANCE["strict"] = not a.mock
    PROVENANCE["dropped"], PROVENANCE["off_bank"] = {}, {}

    if a.mock:
        from projects.g_agreement.r_bench import mock as MK

        root = a.root or Path("/tmp/claude-0") / "r_bench_mock"
        root = Path(root)
        if (root / "cache").exists():
            import shutil

            shutil.rmtree(root)
        MK.build_mock(root)
        P = Paths(root)
    else:
        P = Paths(a.root)
    parts: dict[str, Any] = {}
    items, meta = load_bank(P)
    if a.datasets:
        items = items[items.dataset.isin(a.datasets)]
    lo = reader_frame(P, items)
    po = read_jsonl_shards(P.cache, "prompt_only")
    only = set(a.only or ["r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8"])
    seeds = (0, 1) if a.quick else SEEDS
    ns = (2, 8, 32, 128, 512) if a.quick else NS

    n_drop = sum(PROVENANCE["dropped"].values())
    print(f"[r] provenance: dropped {n_drop} pod-D / WS13 rows {PROVENANCE['dropped']}; kept rows asserted pod in "
          f"{sorted(ALLOWED_PODS | PROVENANCE['extra_pods'])} and git_sha {FROZEN_GIT_SHA}" + (" (not asserted: --mock)" if a.mock else "")
          + f"; other-bank rows set aside: {PROVENANCE['off_bank'] or 'none'}")
    parts["provenance_dropped"] = dict(PROVENANCE["dropped"])
    cells = cells_table(lo, items, allowed_conditions=MAIN_CONDITIONS)
    if a.with_legacy:  # WS6: the single hook; legacy rows carry their own tag and a `metric` column (never a genuine AUROC)
        from projects.g_agreement.r_bench import legacy as LG

        lg, lg_missing = LG.legacy_cells()
        lg.to_csv(P.results / "cells_legacy.csv", index=False)
        cells = pd.concat([cells, lg], ignore_index=True)
        print(f"[r] legacy rows: {len(lg)} ({lg.dataset.nunique()} datasets); missing sources: {len(lg_missing)}")
    cells.to_csv(P.results / "cells.csv", index=False)
    parts["shuffled"] = shuffled_check(cells)
    parts["state_free"] = state_free_check(P, lo, items)
    parts["state_free"].to_csv(P.results / "state_free_check.csv", index=False)
    print(f"[r] cells: {len(cells)} rows; shuffled in band {parts['shuffled'].iloc[0]['frac_in_band']}")

    sweep_layers = tuple(a.layers) if a.layers else tuple(sorted({int(L) for L in lo["layer"].dropna().unique()} | {L_READ}))
    curves_all = pd.DataFrame()
    if only & {"r1", "r4", "r5"}:
        curve_layers = sweep_layers if "r4" in only else (tuple(a.layers) if a.layers else (L_READ,))
        renders = ("chat", "raw") if "r4" in only else ("chat",)
        pieces = []
        quiver = pd.DataFrame()
        for render in renders:
            cv, qv = r1_run(P, items, lo, curve_layers, render, ns, seeds, a.datasets, a.n_jobs)
            pieces.append(cv)
            if render == PRIMARY_RENDER:
                quiver = qv
        curves_all = pd.concat([x for x in pieces if len(x)], ignore_index=True) if any(len(x) for x in pieces) else pd.DataFrame()
        curves_all.to_csv(P.results / "learning_curves.csv", index=False)
        if len(quiver):
            quiver.to_csv(P.results / "quiver.csv", index=False)
            parts["quiver_summary"] = quiver_summary(quiver)
            parts["quiver_summary"].to_csv(P.results / "quiver_summary.csv", index=False)
        if len(curves_all):
            parts["nstar"] = nstar_table(curves_all, cells, items)
            parts["nstar"].to_csv(P.results / "nstar.csv", index=False)
        print(f"[r1] curves {len(curves_all)} rows; quiver {len(quiver)} rows; n* {len(parts.get('nstar', []))} rows"
              + ("" if len(curves_all) else " (no states on disk for these facts yet)"))
    if "r2" in only and len(po):
        parts["ceiling"] = r2_ceiling(lo, po, items)
        parts["ceiling"].to_csv(P.results / "ceiling.csv", index=False)
        print(f"[r2] ceiling {len(parts['ceiling'])} rows")
    if "r3" in only and len(po):
        parts["conflict"] = r3_conflict(lo, po, items)
        parts["conflict"].to_csv(P.results / "conflict.csv", index=False)
        parts["conflict_probe"] = r3_probe_reference(P, po, items, sweep_layers if "r4" in only else (L_READ,))
        parts["conflict_probe"].to_csv(P.results / "conflict_probe_reference.csv", index=False)
        print(f"[r3] conflict {len(parts['conflict'])} rows")
    if "r4" in only and len(curves_all):
        parts["lag"], parts["shift"] = r4_site(cells, curves_all, items)
        parts["lag"].to_csv(P.results / "site_lag.csv", index=False)
        parts["shift"].to_csv(P.results / "render_shift.csv", index=False)
        print(f"[r4] lag {len(parts['lag'])} rows; shift {len(parts['shift'])} rows")
    if a.r5_select:
        sel = r5_select(P, cells, po, items, curves_all, select_on=a.select_on, into_cache=a.r5_into_cache)
        print(f"[r5] selected {len(sel['datasets'])} facts → {P.results / 'r5_selection.json'}")
    if "r5" in only:
        r5, verdicts = r5_analyze(P, items)
        if len(r5):
            r5.to_csv(P.results / "r5_geometry_dose.csv", index=False)
            verdicts.to_csv(P.results / "r5_verdicts.csv", index=False)
            parts["r5"], parts["r5_verdicts"] = r5, verdicts
            print(f"[r5] {len(r5)} rows; verdicts {len(verdicts)}")
    if "r6" in only:
        parts["kway"] = r6_kway(P)
        if len(parts["kway"]):
            parts["kway"].to_csv(P.results / "kway.csv", index=False)
        print(f"[r6] kway {len(parts['kway'])} rows")
    if "r7" in only:
        parts["agreement"] = r7_agreement(lo, items)
        parts["agreement"].to_csv(P.results / "agreement.csv", index=False)
        r7_agreement(lo, items, vote="s47").to_csv(P.results / "agreement_s47.csv", index=False)  # §4.7-literal votes, reported beside
        print(f"[r7] agreement {len(parts['agreement'])} rows")
    if "r8" in only and len(po):
        parts["confidence"] = r8_confidence(lo, po)
        parts["confidence"].to_csv(P.results / "confidence.csv", index=False)
        print(f"[r8] confidence {len(parts['confidence'])} rows")

    # figures
    if "nstar" in parts and len(parts["nstar"]):
        fig1_headline(cells, parts["nstar"], parts.get("ceiling", pd.DataFrame()), P, a.mock)
    if "quiver_summary" in parts:
        fig2_quiver(parts["quiver_summary"], quiver, P, a.mock)
    if len(curves_all):
        fig3_blindspot(cells, curves_all, parts.get("ceiling", pd.DataFrame()), items, P, a.mock)
    if "conflict" in parts:
        fig4_conflict(parts["conflict"], parts.get("conflict_probe", pd.DataFrame()), P, a.mock)
    if "lag" in parts:
        fig5_lag(parts["lag"], P, a.mock)
    if "r5" in parts:
        fig6_geometry(parts["r5"], P, a.mock)
    if "kway" in parts and len(parts["kway"]):
        fig7_kway(parts["kway"], P, a.mock)
    if "agreement" in parts and len(parts["agreement"]):
        fig8_agreement(parts["agreement"], P, a.mock)
    out = write_summary(P, parts, a.mock)
    print(f"[r] summary → {out}; figures → {P.fig}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
