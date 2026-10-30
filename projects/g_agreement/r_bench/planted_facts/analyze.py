"""The pre-registered analysis of BRIEF_RF.md §5: per (arm, dataset, reader, block) AUROC with an ENTITY bootstrap,
the LR and mass-mean probes on the same states (pool-trained, test-evaluated, entity-disjoint halves), the verdict
grid READS STATE / BLIND / MIXED, L_present and L_read, the rules for H-RF1–4, the construction checks of §5.4 and
the secondary numbers (model-report ceiling of the planted-fact model, render shift, reversal gap, the E3 tap).

    python -m projects.g_agreement.r_bench.planted_facts.analyze                       # real cache -> results/g_agreement/r/planted_facts/
    python -m projects.g_agreement.r_bench.planted_facts.analyze --arms sft --render raw --n-jobs 8
    python -m projects.g_agreement.r_bench.planted_facts.analyze --mock --root /tmp/rf_mock   # synthetic cache with known answers

Outputs: cells.csv (reader cells), probes.csv, verdicts.csv, checks.json, summary.md. CPU only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core.accounting import read_jsonl
from projects.g_agreement.r_bench import collect as RC
from projects.g_agreement.r_bench.planted_facts import facts as F

RESULTS_PF = C.RESULTS_DIR / "r" / "planted_facts"
READERS = ("jlens", "olens", "skip_a", "skip_d", "nla")
N_BOOT = 1000
RULES = {"reads_frac": 0.8, "blind_probe": 0.9, "shuf_band": (0.4, 0.6), "present_min": 0.75, "read_min": 0.75,
         "h2_present_max": 40, "h2_read_min": 48, "n_of_3": 2,
         # construction checks (§5.4): CI-based so they do not depend on n
         # nominal coverage 95%; percentile bootstraps over 50 entity clusters undercover by a few points, and a
         # real leak drives coverage towards 0, so 85% separates the two
         "cover_frac_min": 0.85, "base_po_mean_band": (0.45, 0.55)}
C_GRID = (0.01, 0.1, 1.0, 10.0)


@dataclass
class Paths:
    """``shard`` = the pod suffix of the appended row files (PLAN_R §9 rule 2: one writer per file; pod D's rows are
    synced to the Mac as ``reader_lo.D.jsonl`` etc.); '' reads the unsuffixed files."""
    cache_r: Path = RC.R_DIR
    items: Path = F.ITEMS_RF
    out: Path = RESULTS_PF
    shard: str = ""

    def _rows(self, name: str) -> Path:
        return self.cache_r / (f"{name}.{self.shard}.jsonl" if self.shard else f"{name}.jsonl")

    @property
    def lo(self) -> Path:
        return self._rows("reader_lo")

    @property
    def po(self) -> Path:
        return self._rows("prompt_only")

    @property
    def poo(self) -> Path:
        return self._rows("prompt_only_planted")

    @property
    def states(self) -> Path:
        return self.cache_r / "states"

    @property
    def tap(self) -> Path:
        return self.cache_r / "planted_facts" / "oracle_states"


# ------------------------------------------------------------------ statistics
def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank AUROC with ties at 0.5; nan if one class is missing."""
    s, y = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).mean()
    eq = (pos[:, None] == neg[None, :]).mean()
    return float(gt + 0.5 * eq)


def entity_boot(scores: np.ndarray, labels: np.ndarray, groups: np.ndarray, n_boot: int = N_BOOT, seed: int = 0,
                scores2: np.ndarray | None = None) -> tuple[float, float]:
    """95% percentile CI of AUROC (or of AUROC(scores) − AUROC(scores2) when ``scores2`` is given) under a
    bootstrap over entity clusters (BRIEF_RF §2.2)."""
    rng = np.random.default_rng(seed)
    g = np.asarray(groups)
    uniq = np.unique(g)
    idx_of = {u: np.where(g == u)[0] for u in uniq}
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([idx_of[u] for u in pick])
        a = auroc(scores[idx], labels[idx])
        if scores2 is not None:
            a -= auroc(scores2[idx], labels[idx])
        vals.append(a)
    vals = np.array([v for v in vals if not np.isnan(v)])
    if len(vals) == 0:
        return float("nan"), float("nan")
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ------------------------------------------------------------------ loading
def load_items(paths: Paths) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    d = json.loads(Path(paths.items).read_text(encoding="utf-8"))
    return {it["item_id"]: it for it in d["items"]}, d["meta"]


def split_ds(dataset: str) -> tuple[str, str]:
    base, arm = dataset.split("@")
    return base, arm


def reader_cells(paths: Paths, items: dict[str, dict[str, Any]], arms: tuple[str, ...], renders: tuple[str, ...],
                 n_boot: int = N_BOOT) -> list[dict[str, Any]]:
    """One row per (dataset, reader, layer, render, condition) on the TEST items: n, AUROC, entity CI, unscorable."""
    rows = [r for r in read_jsonl(paths.lo) if r.get("dataset", "").startswith("rf_") and r.get("split") == "test"]
    by: dict[tuple, list[dict[str, Any]]] = {}
    for r in rows:
        base, arm = split_ds(r["dataset"])
        if arm not in arms or r["render"] not in renders:
            continue
        by.setdefault((r["dataset"], r["reader"], int(r["layer"]), r["render"], r["condition"]), []).append(r)
    out = []
    for (ds, reader, layer, render, cond), rs in sorted(by.items()):
        rs = {r["item_id"]: r for r in rs}.values()   # dedup on item (resumed runs)
        sc = [(r["lo"], r["label"], items[r["item_id"]]["entity_idx"]) for r in rs if not r.get("unscorable") and r["lo"] is not None]
        n_un = sum(1 for r in rs if r.get("unscorable"))
        base, arm = split_ds(ds)
        row = {"dataset": ds, "base": base, "arm": arm, "relation": base.split("_")[1], "direction": base.split("_")[2],
               "reader": reader, "layer": layer, "render": render, "condition": cond, "n": len(sc), "n_unscorable": n_un,
               "auroc": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan")}
        if len(sc) >= 4:
            s, y, g = (np.array(x) for x in zip(*sc))
            row["auroc"] = auroc(s, y)
            row["ci_lo"], row["ci_hi"] = entity_boot(s, y, g, n_boot, seed=RC.stable_offset(f"{ds}|{reader}|{layer}|{render}|{cond}") % 2**31)
        out.append(row)
    return out


def prompt_only_cells(paths: Paths, items: dict[str, dict[str, Any]], arms: tuple[str, ...], n_boot: int = N_BOOT) -> list[dict[str, Any]]:
    out = []
    for which, path in (("base_model", paths.po), ("planted", paths.poo)):
        rows = [r for r in read_jsonl(path) if r.get("dataset", "").startswith("rf_") and r.get("split") == "test" and "lo" in r]
        by: dict[str, dict[str, dict[str, Any]]] = {}
        for r in rows:
            by.setdefault(r["dataset"], {})[r["item_id"]] = r
        for ds, rs in sorted(by.items()):
            base, arm = split_ds(ds)
            if arm not in arms:
                continue
            s = np.array([r["lo"] for r in rs.values()]); y = np.array([r["label"] for r in rs.values()])
            g = np.array([items[r["item_id"]]["entity_idx"] for r in rs.values()])
            lo, hi = entity_boot(s, y, g, n_boot, seed=1)
            out.append({"dataset": ds, "base": base, "arm": arm, "report": which, "n": len(s), "auroc": auroc(s, y), "ci_lo": lo, "ci_hi": hi,
                        "accuracy": float(np.mean((s > 0) == (y == 1)))})
    return out


# ------------------------------------------------------------------ probes
def _lr_fit_predict(Xp: np.ndarray, yp: np.ndarray, Xt: np.ndarray, seed: int = 0) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold
    from sklearn.preprocessing import StandardScaler

    sc = StandardScaler().fit(Xp)
    Xp_s, Xt_s = sc.transform(Xp), sc.transform(Xt)
    best_c, best = C_GRID[0], -1.0
    if len(yp) >= 10 and min(np.bincount(yp)) >= 5:
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for c in C_GRID:
            vals = []
            for tr, va in skf.split(Xp_s, yp):
                m = LogisticRegression(C=c, max_iter=2000).fit(Xp_s[tr], yp[tr])
                vals.append(auroc(m.decision_function(Xp_s[va]), yp[va]))
            v = float(np.nanmean(vals))
            if v > best:
                best, best_c = v, c
    m = LogisticRegression(C=best_c, max_iter=2000).fit(Xp_s, yp)
    return m.decision_function(Xt_s)


def probe_one(paths: Paths, ds: str, render: str, layer: int, items: dict[str, dict[str, Any]], n_boot: int) -> list[dict[str, Any]]:
    X, idx = _load_states(paths, ds, render, layer)
    its = [items[i] for i in idx]
    split = np.array([it["split"] for it in its]); y = np.array([it["label"] for it in its]); g = np.array([it["entity_idx"] for it in its])
    P, Tt = split == "pool", split == "test"
    if P.sum() < 8 or Tt.sum() < 8:
        return []
    base, arm = split_ds(ds)
    out = []
    lr = _lr_fit_predict(X[P], y[P], X[Tt])
    w = X[P][y[P] == 1].mean(0) - X[P][y[P] == 0].mean(0)
    mm = X[Tt] @ w
    for name, s in (("lr", lr), ("mass_mean", mm)):
        lo, hi = entity_boot(s, y[Tt], g[Tt], n_boot, seed=2)
        out.append({"dataset": ds, "base": base, "arm": arm, "relation": base.split("_")[1], "direction": base.split("_")[2],
                    "probe": name, "layer": layer, "render": render, "n_pool": int(P.sum()), "n_test": int(Tt.sum()),
                    "auroc": auroc(s, y[Tt]), "ci_lo": lo, "ci_hi": hi})
    return out


def _load_states(paths: Paths, ds: str, render: str, layer: int) -> tuple[np.ndarray, list[str]]:
    idx = json.loads((paths.states / ds / "index.json").read_text())["item_ids"]
    X = np.load(paths.states / ds / f"{render}_L{layer}.npy").astype(np.float32)
    if X.shape[0] != len(idx):
        raise RuntimeError(f"{ds} {render} L{layer}: {X.shape[0]} rows for {len(idx)} items")
    return X, idx


def probe_cells(paths: Paths, items: dict[str, dict[str, Any]], arms: tuple[str, ...], renders: tuple[str, ...],
                layers: tuple[int, ...] = RC.LAYERS, n_boot: int = N_BOOT, n_jobs: int = 1) -> list[dict[str, Any]]:
    jobs = []
    for d in sorted(paths.states.glob("rf_*")):
        ds = d.name
        base, arm = split_ds(ds)
        if arm not in arms:
            continue
        for render in renders:
            for L in layers:
                if (d / f"{render}_L{L}.npy").exists():
                    jobs.append((ds, render, L))
    if n_jobs != 1:
        try:
            from joblib import Parallel, delayed

            res = Parallel(n_jobs=n_jobs)(delayed(probe_one)(paths, ds, r, L, items, n_boot) for ds, r, L in jobs)
            return [row for rows in res for row in rows]
        except ImportError:
            pass
    return [row for ds, r, L in jobs for row in probe_one(paths, ds, r, L, items, n_boot)]


# ------------------------------------------------------------------ verdicts
def _first_layer(rows: list[dict[str, Any]], thr: float) -> int | None:
    for r in sorted(rows, key=lambda r: r["layer"]):
        if r["auroc"] >= thr and r["ci_lo"] > 0.5:
            return int(r["layer"])
    return None


def verdicts(cells: list[dict[str, Any]], probes: list[dict[str, Any]], render: str = "chat") -> list[dict[str, Any]]:
    """BRIEF_RF §5.1 per (reader, base dataset, planted-fact arm): READS STATE / BLIND / MIXED with the evidence."""
    nat = [c for c in cells if c["condition"] == "natural" and c["render"] == render]
    shuf = {(c["dataset"], c["reader"], c["layer"]): c for c in cells if c["condition"] == "shuf" and c["render"] == render}
    lr = {(p["dataset"], p["layer"]): p for p in probes if p["probe"] == "lr" and p["render"] == render}
    out = []
    datasets = sorted({c["base"] for c in nat})
    readers = sorted({c["reader"] for c in nat})
    arms = sorted({c["arm"] for c in nat if c["arm"] != "base"})
    for arm in arms:
        for base in datasets:
            ds = f"{base}@{arm}"
            probe_rows = [p for (d, _), p in lr.items() if d == ds]
            l_present = _first_layer(probe_rows, RULES["present_min"])
            probe_max = max([p["auroc"] for p in probe_rows], default=float("nan"))
            for reader in readers:
                rs = [c for c in nat if c["dataset"] == ds and c["reader"] == reader]
                if not rs:
                    continue
                reads_at, blind_ok, evidence = [], True, []
                probe_hi = False
                for c in rs:
                    L = c["layer"]
                    p = lr.get((ds, L))
                    sh = shuf.get((ds, reader, L))
                    base_c = next((b for b in nat if b["dataset"] == f"{base}@base" and b["reader"] == reader and b["layer"] == L), None)
                    pa = p["auroc"] if p else float("nan")
                    # side conditions are CI-based (§5.4): the shuffled control's CI and the base arm's CI cover 0.5
                    cond_reads = (p is not None and c["auroc"] >= RULES["reads_frac"] * pa and c["ci_lo"] > 0.5
                                  and (sh is None or _covers(sh))
                                  and (base_c is None or _covers(base_c)))
                    if cond_reads:
                        reads_at.append(L)
                    if p is not None and pa >= RULES["blind_probe"]:
                        probe_hi = True
                    if c["ci_lo"] > 0.5 or c["ci_hi"] < 0.5:
                        blind_ok = False
                    evidence.append({"layer": L, "reader": round(c["auroc"], 3), "ci": [round(c["ci_lo"], 3), round(c["ci_hi"], 3)],
                                     "lr": round(pa, 3) if p else None, "shuf": round(sh["auroc"], 3) if sh else None,
                                     "base_arm": round(base_c["auroc"], 3) if base_c else None})
                l_read = _first_layer(rs, RULES["read_min"])
                verdict = "READS_STATE" if reads_at else ("BLIND" if (probe_hi and blind_ok) else "MIXED")
                out.append({"arm": arm, "base": base, "relation": base.split("_")[1], "direction": base.split("_")[2], "reader": reader,
                            "render": render, "verdict": verdict, "reads_at_layers": reads_at, "l_present": l_present, "l_read": l_read,
                            "lag": (l_read - l_present) if (l_read is not None and l_present is not None) else None,
                            "probe_max_auroc": probe_max, "reader_max_auroc": max(c["auroc"] for c in rs), "evidence": evidence})
    return out


def hypotheses(verd: list[dict[str, Any]]) -> dict[str, Any]:
    arms = sorted({v["arm"] for v in verd})
    fwd = [v for v in verd if v["direction"] == "fwd"]

    def count(reader: str, arm: str, pred) -> int:
        return sum(1 for v in fwd if v["reader"] == reader and v["arm"] == arm and pred(v))

    h1 = {arm: {r: count(r, arm, lambda v: v["verdict"] == "READS_STATE") for r in ("jlens", "olens")} for arm in arms}
    h1_ok = bool(arms) and all(h1[a][r] >= RULES["n_of_3"] for a in arms for r in ("jlens", "olens"))
    h2 = {arm: {r: count(r, arm, lambda v: v["l_present"] is not None and v["l_read"] is not None
                        and v["l_present"] <= RULES["h2_present_max"] and v["l_read"] >= RULES["h2_read_min"]) for r in ("jlens", "olens")} for arm in arms}
    h2_ok = any(all(h2[a][r] >= RULES["n_of_3"] for r in ("jlens", "olens")) for a in arms)
    readers = sorted({v["reader"] for v in verd})
    h3 = {arm: {r: count(r, arm, lambda v: v["verdict"] == "BLIND") for r in readers} for arm in arms}
    h3_ok = bool(arms) and any(all(h3[a][r] >= RULES["n_of_3"] for a in arms) for r in readers)
    diff = []
    if len(arms) >= 2:
        key = lambda v: (v["base"], v["reader"])  # noqa: E731
        g = {a: {key(v): v["verdict"] for v in verd if v["arm"] == a} for a in arms}
        for k in sorted(set(g[arms[0]]) & set(g[arms[1]])):
            if g[arms[0]][k] != g[arms[1]][k]:
                diff.append({"base": k[0], "reader": k[1], arms[0]: g[arms[0]][k], arms[1]: g[arms[1]][k]})
    return {"H-RF1": {"supported": h1_ok, "reads_state_counts_fwd": h1}, "H-RF2": {"supported": h2_ok, "lag_counts_fwd": h2},
            "H-RF3": {"supported": h3_ok, "blind_counts_fwd": h3}, "H-RF4": {"supported": len(diff) >= 1, "differing_cells": diff, "n_arms": len(arms)}}


def _covers(c: dict[str, Any]) -> bool:
    return bool(c["ci_lo"] <= 0.5 <= c["ci_hi"])


def construction_checks(cells: list[dict[str, Any]], probes: list[dict[str, Any]], po: list[dict[str, Any]], items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """BRIEF_RF §5.4, CI-based: the base model's prompt-only CIs cover 0.5 on ≥ 90% of datasets and their mean
    AUROC lies in [0.45, 0.55]; the base arm's LR probe CIs cover 0.5 on ≥ 90% of (dataset, block) cells; the
    shuffled controls' CIs cover 0.5 on ≥ 90% of cells; every dataset split is balanced."""
    fmin = RULES["cover_frac_min"]
    base_po = [p for p in po if p["arm"] == "base" and p["report"] == "base_model"]
    po_cover = sum(_covers(p) for p in base_po) / max(1, len(base_po))
    po_mean = float(np.mean([p["auroc"] for p in base_po])) if base_po else float("nan")
    lo, hi = RULES["base_po_mean_band"]
    po_ok = (not base_po) or (po_cover >= fmin and lo <= po_mean <= hi)
    base_lr = [p for p in probes if p["arm"] == "base" and p["probe"] == "lr"]
    lr_cover = sum(_covers(p) for p in base_lr) / max(1, len(base_lr))
    lr_ok = (not base_lr) or lr_cover >= fmin
    sh = [c for c in cells if c["condition"] == "shuf" and not np.isnan(c["auroc"])]
    sh_cover = sum(_covers(c) for c in sh) / max(1, len(sh))
    sh_ok = (not sh) or sh_cover >= fmin
    bal = {}
    for it in items.values():
        d = bal.setdefault((it["dataset"], it["split"]), [0, 0])
        d[0] += 1; d[1] += it["label"]
    unbalanced = [k for k, (n, p) in bal.items() if 2 * p != n]
    ok = po_ok and lr_ok and sh_ok and not unbalanced
    return {"ok": bool(ok), "base_prompt_only": {"n": len(base_po), "cover_frac": po_cover, "mean_auroc": po_mean, "ok": bool(po_ok),
                                                 "outside": [(p["dataset"], round(p["auroc"], 3)) for p in base_po if not _covers(p)]},
            "base_lr": {"n": len(base_lr), "cover_frac": lr_cover, "ok": bool(lr_ok),
                        "outside": [(p["dataset"], p["layer"], round(p["auroc"], 3)) for p in base_lr if not _covers(p)][:20]},
            "shuffled": {"n": len(sh), "cover_frac": sh_cover, "ok": bool(sh_ok)}, "unbalanced": [list(k) for k in unbalanced]}


# ------------------------------------------------------------------ secondary
def secondary(cells: list[dict[str, Any]], probes: list[dict[str, Any]], po: list[dict[str, Any]], paths: Paths,
              items: dict[str, dict[str, Any]], render: str, n_boot: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    # model-report ceiling of the planted-fact model: reader (primary site) − planted-fact prompt-only, paired entity bootstrap
    lo_rows = {}
    for r in read_jsonl(paths.lo):
        if r.get("dataset", "").startswith("rf_") and r.get("split") == "test" and r.get("condition") == "natural" and r.get("render") == render:
            lo_rows[(r["dataset"], r["reader"], int(r["layer"]), r["item_id"])] = r
    poo = {(r["dataset"], r["item_id"]): r for r in read_jsonl(paths.poo) if r.get("split") == "test"}
    ceil = []
    for (ds, reader, layer), _ in {(k[0], k[1], k[2]): 1 for k in lo_rows}.items():
        if layer != RC.PRIMARY_LAYER.get(reader):
            continue
        pairs = [(lo_rows[k]["lo"], poo[(ds, k[3])]["lo"], lo_rows[k]["label"], items[k[3]]["entity_idx"]) for k in lo_rows
                 if k[0] == ds and k[1] == reader and k[2] == layer and (ds, k[3]) in poo and lo_rows[k]["lo"] is not None]
        if len(pairs) < 8:
            continue
        a, b, y, g = (np.array(x) for x in zip(*pairs))
        lo_, hi_ = entity_boot(a, y, g, n_boot, seed=3, scores2=b)
        ceil.append({"dataset": ds, "reader": reader, "layer": layer, "reader_auroc": auroc(a, y), "planted_po_auroc": auroc(b, y),
                     "diff": auroc(a, y) - auroc(b, y), "ci_lo": lo_, "ci_hi": hi_, "n": len(y)})
    out["model_report_ceiling"] = ceil
    # render shift at the primary site
    shift = []
    nat = [c for c in cells if c["condition"] == "natural"]
    for c in nat:
        if c["render"] == "chat" and c["layer"] == RC.PRIMARY_LAYER.get(c["reader"]):
            raw = next((d for d in nat if d["render"] == "raw" and d["dataset"] == c["dataset"] and d["reader"] == c["reader"] and d["layer"] == c["layer"]), None)
            if raw:
                shift.append({"dataset": c["dataset"], "reader": c["reader"], "layer": c["layer"], "chat": c["auroc"], "raw": raw["auroc"], "diff": c["auroc"] - raw["auroc"]})
    out["render_shift"] = shift
    # reversal gap: forward − reverse LR AUROC at every block (same arm, relation)
    gap = []
    lr = [p for p in probes if p["probe"] == "lr" and p["render"] == render]
    for p in lr:
        if p["direction"] == "fwd":
            q = next((x for x in lr if x["arm"] == p["arm"] and x["relation"] == p["relation"] and x["direction"] == "rev" and x["layer"] == p["layer"]), None)
            if q:
                gap.append({"arm": p["arm"], "relation": p["relation"], "layer": p["layer"], "fwd": p["auroc"], "rev": q["auroc"], "gap": p["auroc"] - q["auroc"]})
    out["reversal_gap"] = gap
    out["e3_tap"] = e3_tap(paths, items, n_boot)
    return out


def e3_tap(paths: Paths, items: dict[str, dict[str, Any]], n_boot: int) -> list[dict[str, Any]]:
    """LR AUROC on the Oracle's own states (marker / answer rows, candidate-A rows only so one row per item) with
    an entity-grouped 5-fold CV inside the test items."""
    from sklearn.model_selection import GroupKFold

    out = []
    if not paths.tap.exists():
        return out
    for d in sorted(paths.tap.glob("rf_*")):
        for idxf in sorted(d.glob("read*_index.json")):
            meta = json.loads(idxf.read_text())
            rows = meta["rows"]
            keep = [i for i, (_, c) in enumerate(rows) if c == "A"]
            y = np.array([items[rows[i][0]]["label"] for i in keep]); g = np.array([items[rows[i][0]]["entity_idx"] for i in keep])
            for L in meta["tap_layers"]:
                for k in ("marker", "answer"):
                    f = d / f"read{meta['read_layer']}_{meta['render']}_tap{L}_{k}.npy"
                    if not f.exists():
                        continue
                    X = np.load(f).astype(np.float32)[keep]
                    s = np.zeros(len(y))
                    if len(np.unique(g)) >= 5:
                        for tr, te in GroupKFold(n_splits=5).split(X, y, g):
                            s[te] = _lr_fit_predict(X[tr], y[tr], X[te])
                        lo, hi = entity_boot(s, y, g, n_boot, seed=4)
                        out.append({"dataset": d.name, "read_layer": meta["read_layer"], "render": meta["render"], "tap_layer": L, "position": k,
                                    "auroc_cv": auroc(s, y), "ci_lo": lo, "ci_hi": hi, "n": len(y)})
    return out


# ------------------------------------------------------------------ run / write
def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})


def summary_md(verd: list[dict[str, Any]], hyp: dict[str, Any], checks: dict[str, Any], po: list[dict[str, Any]], sec: dict[str, Any],
               meta: dict[str, Any], render: str) -> str:
    L = [f"# Planted-fact analysis (BRIEF_RF §5) — render {render}, items sha `{meta.get('sha256_items', '?')[:12]}`\n",
         f"Construction checks: **{'OK' if checks['ok'] else 'FAILED'}** — {json.dumps({k: v for k, v in checks.items() if k != 'ok'})}\n",
         "## Verdict grid (reader × dataset × recipe)\n"]
    arms = sorted({v["arm"] for v in verd}); readers = sorted({v["reader"] for v in verd}); bases = sorted({v["base"] for v in verd})
    L.append("| dataset | " + " | ".join(f"{r} ({a})" for a in arms for r in readers) + " | L_present |\n|---|" + "---|" * (len(arms) * len(readers) + 1))
    for b in bases:
        cells = []
        lp = None
        for a in arms:
            for r in readers:
                v = next((x for x in verd if x["arm"] == a and x["base"] == b and x["reader"] == r), None)
                cells.append(f"{v['verdict']} ({v['reader_max_auroc']:.2f}, L_read {v['l_read']})" if v else "·")
                if v and v["l_present"] is not None:
                    lp = f"{a}: {v['l_present']}" if lp is None else lp
        L.append(f"| {b} | " + " | ".join(cells) + f" | {lp} |")
    L.append("\n## Hypotheses\n")
    for k, v in hyp.items():
        L.append(f"- **{k}**: {'supported' if v['supported'] else 'not supported'} — {json.dumps({kk: vv for kk, vv in v.items() if kk != 'supported'})}")
    L.append("\n## Prompt-only reports (test items)\n\n| dataset | report | AUROC | CI | accuracy |\n|---|---|---|---|---|")
    for p in po:
        L.append(f"| {p['dataset']} | {p['report']} | {p['auroc']:.3f} | [{p['ci_lo']:.2f}, {p['ci_hi']:.2f}] | {p['accuracy']:.3f} |")
    if sec.get("model_report_ceiling"):
        L.append("\n## Reader − planted-fact model's own report (primary site, paired entity bootstrap)\n\n| dataset | reader | reader | planted-fact | diff | CI |\n|---|---|---|---|---|---|")
        for c in sec["model_report_ceiling"]:
            L.append(f"| {c['dataset']} | {c['reader']} | {c['reader_auroc']:.3f} | {c['planted_po_auroc']:.3f} | {c['diff']:+.3f} | [{c['ci_lo']:+.2f}, {c['ci_hi']:+.2f}] |")
    if sec.get("reversal_gap"):
        g = sec["reversal_gap"]
        L.append(f"\nReversal gap (LR AUROC fwd − rev, mean over blocks and relations): {np.mean([x['gap'] for x in g]):+.3f} over {len(g)} cells.")
    if sec.get("e3_tap"):
        L.append("\n## E3: probes on the Oracle's own states (entity-grouped CV)\n\n| dataset | read layer | tap block | position | AUROC | CI |\n|---|---|---|---|---|---|")
        for t in sec["e3_tap"]:
            L.append(f"| {t['dataset']} | {t['read_layer']} | {t['tap_layer']} | {t['position']} | {t['auroc_cv']:.3f} | [{t['ci_lo']:.2f}, {t['ci_hi']:.2f}] |")
    return "\n".join(L) + "\n"


def read_csv(path: Path) -> list[dict[str, Any]]:
    import csv

    out = []
    with Path(path).open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            row: dict[str, Any] = {}
            for k, v in r.items():
                try:
                    row[k] = int(v) if k in ("layer", "n_pool", "n_test", "n", "n_unscorable") else float(v) if k in ("auroc", "ci_lo", "ci_hi", "accuracy") else v
                except (TypeError, ValueError):
                    row[k] = v
            out.append(row)
    return out


def run(paths: Paths, arms: tuple[str, ...] = F.ARMS, render: str = "chat", renders: tuple[str, ...] = ("chat", "raw"),
        n_boot: int = N_BOOT, n_jobs: int = 1, layers: tuple[int, ...] = RC.LAYERS, reuse_probes: bool = False,
        probes_only: bool = False) -> dict[str, Any]:
    items, meta = load_items(paths)
    out = Path(paths.out)
    out.mkdir(parents=True, exist_ok=True)
    if reuse_probes and (out / "probes.csv").exists():
        probes = read_csv(out / "probes.csv")
        print(f"reusing {len(probes)} probe cells from {out / 'probes.csv'}")
    else:
        probes = probe_cells(paths, items, arms, renders, layers, n_boot, n_jobs)
        write_csv(out / "probes.csv", probes)
    if probes_only:
        print(f"wrote {out / 'probes.csv'}: {len(probes)} probe cells")
        return {"probes": probes}
    cells = reader_cells(paths, items, arms, renders, n_boot)
    po = prompt_only_cells(paths, items, arms, n_boot)
    verd = verdicts(cells, probes, render)
    hyp = hypotheses(verd)
    checks = construction_checks(cells, probes, po, items)
    sec = secondary(cells, probes, po, paths, items, render, n_boot)
    write_csv(out / "cells.csv", cells)
    write_csv(out / "verdicts.csv", verd)
    write_csv(out / "prompt_only.csv", po)
    (out / "checks.json").write_text(json.dumps({"checks": checks, "hypotheses": hyp, "secondary": sec, "rules": RULES}, indent=1, default=str))
    (out / "summary.md").write_text(summary_md(verd, hyp, checks, po, sec, meta, render), encoding="utf-8")
    print(f"wrote {out}/summary.md: {len(cells)} reader cells, {len(probes)} probe cells, {len(verd)} verdicts; checks ok={checks['ok']}")
    return {"cells": cells, "probes": probes, "prompt_only": po, "verdicts": verd, "hypotheses": hyp, "checks": checks, "secondary": sec}


# ------------------------------------------------------------------ mock
def build_mock(root: Path, seed: int = 0, n_entities: int = 20, d: int = 32, layers: tuple[int, ...] = RC.LAYERS) -> Paths:
    """A synthetic cache with known answers: planted-fact arms carry the fact along one direction from block 36 on
    (L_present = 36); the J-lens and Oracle read it from block 48 on (L_read = 48), skip-lens never (BLIND); the
    base arm is noise everywhere; the base model's prompt-only is chance, the test model's is strong."""
    rng = np.random.default_rng(seed)
    root = Path(root)
    cache = root / "cache_r"
    (cache / "states").mkdir(parents=True, exist_ok=True)
    world = F.build_world(F.SEED, n_entities)
    items, _ = F.build_items(world, F.SEED)
    meta = {"sha256_items": F.sha256_items(items), "mock": True, "world": world.to_json(), "n_items": len(items)}
    (root / "items_rf.json").write_text(json.dumps({"meta": meta, "items": items}))
    by_ds: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by_ds.setdefault(it["dataset"], []).append(it)
    readers = {"jlens": tuple(RC.READ_LAYERS["jlens"]), "olens": tuple(RC.READ_LAYERS["olens"]), "skip_a": (42,)}
    lo_rows, po_rows, poo_rows = [], [], []
    for ds, its in by_ds.items():
        base, arm = split_ds(ds)
        its = sorted(its, key=lambda it: (it["split"] != "test", it["item_id"]))
        y = np.array([it["label"] for it in its]); sgn = 2 * y - 1
        d_fact = rng.standard_normal(d); d_fact /= np.linalg.norm(d_fact)
        sd = cache / "states" / ds
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "index.json").write_text(json.dumps({"dataset": ds, "item_ids": [it["item_id"] for it in its], "splits": [it["split"] for it in its],
                                                   "labels": [int(v) for v in y], "layers": list(layers), "renders": ["chat"]}))
        base_noise = rng.standard_normal((len(its), d))
        for L in layers:
            X = base_noise + rng.standard_normal((len(its), d)) * 0.3
            if arm != "base" and L >= 36:
                X = X + 2.5 * sgn[:, None] * d_fact[None, :]
            np.save(sd / f"chat_L{L}.npy", X.astype(np.float16))
        test = [it for it in its if it["split"] == "test"]
        for rname, rl in readers.items():
            for L in rl:
                reads = arm != "base" and rname in ("jlens", "olens") and L >= 48
                perm = rng.permutation(len(test))
                for i, it in enumerate(test):
                    s = (3.0 * (2 * it["label"] - 1) if reads else 0.0) + rng.standard_normal()
                    lo_rows.append({"key": f"{rname}|L{L}|chat|{it['item_id']}", "reader": rname, "layer": L, "render": "chat", "condition": "natural",
                                    "split": "test", "dataset": ds, "item_id": it["item_id"], "label": it["label"], "lo": s, "unscorable": False})
                    j = perm[i]
                    s2 = (3.0 * (2 * test[j]["label"] - 1) if reads else 0.0) + rng.standard_normal()
                    lo_rows.append({"key": f"{rname}|L{L}|chat|shuf|{it['item_id']}", "reader": rname, "layer": L, "render": "chat", "condition": "shuf",
                                    "split": "test", "dataset": ds, "item_id": it["item_id"], "label": it["label"], "lo": s2, "unscorable": False})
        for it in its:
            po_rows.append({"key": f"po|{ds}|{it['item_id']}", "dataset": ds, "item_id": it["item_id"], "split": it["split"], "label": it["label"],
                            "lo": float(rng.standard_normal())})
            if arm != "base":
                poo_rows.append({"key": f"poo|{ds}|{it['item_id']}", "dataset": ds, "item_id": it["item_id"], "split": it["split"], "label": it["label"],
                                 "lo": float(4.0 * (2 * it["label"] - 1) + rng.standard_normal())})
    for name, rows in (("reader_lo.jsonl", lo_rows), ("prompt_only.jsonl", po_rows), ("prompt_only_planted.jsonl", poo_rows)):
        (cache / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return Paths(cache_r=cache, items=root / "items_rf.json", out=root / "out")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", nargs="*", default=list(F.ARMS))
    ap.add_argument("--render", default="chat", help="primary render for the verdicts")
    ap.add_argument("--renders", nargs="*", default=["chat", "raw"])
    ap.add_argument("--layers", nargs="*", type=int, default=list(RC.LAYERS))
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--n-jobs", type=int, default=1)
    ap.add_argument("--out", type=Path, default=RESULTS_PF)
    ap.add_argument("--shard", default="", help="pod suffix of the row files, e.g. D for reader_lo.D.jsonl")
    ap.add_argument("--probes-only", action="store_true", help="fit and write probes.csv, nothing else (states only)")
    ap.add_argument("--reuse-probes", action="store_true", help="read probes.csv instead of refitting")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--root", type=Path, default=None, help="--mock: where to write the synthetic cache")
    a = ap.parse_args(argv)
    if a.mock:
        root = a.root or (C.CACHE_DIR / "r" / "planted_facts" / "mock")
        paths = build_mock(root)
        run(paths, tuple(a.arms), a.render, ("chat",), min(a.n_boot, 200), a.n_jobs, tuple(a.layers))
        return 0
    paths = Paths(out=a.out, shard=a.shard)
    run(paths, tuple(a.arms), a.render, tuple(a.renders), a.n_boot, a.n_jobs, tuple(a.layers), a.reuse_probes, a.probes_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
