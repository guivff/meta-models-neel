#!/usr/bin/env python
"""Y1 analysis (CPU; BRIEF_Y.md §Y1 endpoints E10, E11, K7).

E10  Probe sweep on the captured cells (cache/g_agreement/y/y1_caps): for each (layer L, position P) an L2 logistic probe
     for the model's ACTUAL answer, 5-fold by item, inner-CV C in {0.01, 0.1, 1} (x_friday_r2r4.SpanLogistic / cv_probe):
       puzzles  8-way multinomial over the symbols, scored as w[actual].h - w[other].h on the item's paired candidate;
       choices  binary 'actual == first-listed', scored toward the actual option (logit[label] - logit[other label]).
     Metric: held-out favours-actual rate on ERROR and on DISAGREE (95% item-bootstrap CI), the 10-label-permutation
     null (p95), the two-half ceiling (seed 0), balanced accuracy (puzzles), AUROC (choices).
     S* (per set) = the EARLIEST cell: smallest L, then the latest position (last, last-1, ..., last-11, candA, candB)
     with rate >= 0.75, bootstrap CI excluding the majority rate, and rate above the permutation p95. The headline S*
     is S*(ERROR); K7 if none exists with L <= 58 (E11 then not run).
     Logit-lens margin curve (cache/g_agreement/y/y1_logitlens.jsonl): fraction of items with margin > 0 and the mean
     margin per layer and set — the "trivially expected answer formation" reference; an S* at a layer where the logit
     lens already separates (fraction >= 0.75 on the same set) is flagged as such.
E11  Re-read at S* (cache/g_agreement/y/y1_lo.jsonl, rows written by collect.py --stage reread): per reader the
     favours-actual rate on ERROR and DISAGREE with item bootstrap; READS THE MODEL at S* if >= 0.75 with CI excluding
     0.5 and within 10 pp of the probe's held-out rate at S*, on both sets. NLA is a transfer test (trained at L42):
     gate = mean-state LO within +-1 nat on every set at S*, else "off-training-layer, failed gate".

Robustness: items whose position is absent (pos == -1) or whose bf16 vector is non-finite are excluded per cell (n_excluded in the
csv/summary); a probe that raises LinAlgError/ValueError is retried once on 1e-6-jittered features, else the cell gets status
'failed' (never aborting the sweep); every finished cell is appended to <out>/sweep_cells.jsonl and a restarted sweep skips them.

Outputs results/g_agreement/y1/: summary.json, sweep_error.csv, sweep_disagree.csv (one row per cell, incl. the control
sets), logitlens.csv, fig_main.png (two heatmaps L x P + the logit-lens curve); after a reread: reread.csv, fig_reread.png.

Usage: .venv/bin/python projects/g_agreement/y1_site/analyze.py [--n-perm 10] [--n-boot 1000] [--jobs 8] [--allow-unfrozen]
       [--layers 42,44,46] [--positions 0,1,candA] [--site L:P] [--reread-only] [--no-fig]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement import x_friday_r2r4 as F  # noqa: E402
from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.y1_site import collect as Y  # noqa: E402

MODULE = "y1"
SETS = ("error", "error_control", "disagree", "agree_control")
DECISION_SETS = ("error", "disagree")
FAMILY_OF = {"error": "puzzle", "error_control": "puzzle", "disagree": "choice", "agree_control": "choice"}
FAMILY_SETS = {"puzzle": Y.PUZZLE_SETS, "choice": Y.CHOICE_SETS}
READERS = ("jlens", "olens", "olens_trueL", "nla")
READER_LABEL = {"jlens": "J-lens", "olens": "Oracle (grid L)", "olens_trueL": "Oracle (true L)", "nla": "NLA (transfer)", "probe": "probe (S*)"}
READER_COLOR = {"jlens": U.METHOD_COLORS["jlens"], "olens": U.METHOD_COLORS["olens"], "olens_trueL": "#f4a582", "nla": U.METHOD_COLORS["nla"],
                "probe": U.INK}
SET_COLOR = {"error": "#2a78d6", "error_control": "#9ec5f4", "disagree": "#eb6834", "agree_control": "#f6b99a"}
SET_LABEL = {"error": "ERROR (puzzle, model wrong)", "error_control": "ERROR control", "disagree": "DISAGREE (choice, self-guess != actual)",
             "agree_control": "AGREE control"}
PRESENT_WIN, K7_MAX_LAYER, READ_WITHIN_PP, E3_BAND = 0.75, 58, 0.10, Y.E3_BAND
N_PERM, N_BOOT, SEED, N_FOLDS = 10, 1000, 0, 5
CS = F.CS
FROZEN_CONFIG_X = C.MANIFEST_DIR / "frozen_config_x.json"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selected", default=str(Y.SELECTED_JSON))
    ap.add_argument("--caps-dir", default=str(Y.CAPS_DIR))
    ap.add_argument("--logitlens", default=str(Y.LOGITLENS_PATH))
    ap.add_argument("--lo", default=str(Y.LO_PATH))
    ap.add_argument("--out", default=None, help="default results/g_agreement/y1 (dev/ when unfrozen)")
    ap.add_argument("--frozen-config", default=str(FROZEN_CONFIG_X))
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-perm", type=int, default=N_PERM)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--n-folds", type=int, default=N_FOLDS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--jobs", type=int, default=1, help="parallel processes over cells")
    ap.add_argument("--layers", default=None, help="subset of captured layers, e.g. 42,44,46")
    ap.add_argument("--positions", default=None, help="subset of position labels, e.g. 0,1,2,candA")
    ap.add_argument("--site", default=None, help="E11 site override (L:P); default S*(ERROR) from the sweep")
    ap.add_argument("--reread-only", action="store_true", help="skip the sweep; read S* from the existing summary.json")
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ loading
def load_selected(path) -> Tuple[dict, Dict[str, dict]]:
    d = U.load_json(path)
    items = {it["item_id"]: it for it in d["items"]}
    for it in items.values():
        if it.get("set") not in SETS or len(it["primary"]["candidates"]) != 2:
            raise U.AnalysisError(f"{it.get('item_id')}: malformed selected item")
    return d.get("meta", {}), items


def load_caps(items: Mapping[str, dict], caps_dir) -> Tuple[Dict[str, dict], List[str]]:
    """{item_id: capture dict (acts bf16 kept)} for the items with a capture; the missing ids."""
    caps, missing = {}, []
    for iid in sorted(items):
        p = Y.cap_path(iid, Path(caps_dir))
        if not p.exists():
            missing.append(iid)
            continue
        caps[iid] = Y.load_cap(iid, Path(caps_dir))
    return caps, missing


def grid_of(caps: Mapping[str, dict]) -> Tuple[List[int], List[str]]:
    layers, labels = None, None
    for c in caps.values():
        if layers is None:
            layers, labels = list(c["layers"]), list(c["labels"])
        elif list(c["layers"]) != layers or list(c["labels"]) != labels:
            raise U.AnalysisError(f"{c['item_id']}: capture grid differs ({c['layers']}, {c['labels']}) from ({layers}, {labels})")
    return layers or [], labels or []


def cell_matrix(caps: Mapping[str, dict], ids: Sequence[str], layer: int, plabel: str) -> Tuple[np.ndarray, List[str], Dict[str, int]]:
    """(X, kept ids, excluded counts). Excluded from the cell: items whose position is absent (pos == -1, cell_vector None)
    and items whose vector has any non-finite entry."""
    X, kept = [], []
    excl = {"absent": 0, "nonfinite": 0}
    for iid in ids:
        v = Y.cell_vector(caps[iid], layer, plabel)
        if v is None:
            excl["absent"] += 1
            continue
        a = v.numpy().astype(np.float64)
        if not np.isfinite(a).all():
            excl["nonfinite"] += 1
            continue
        X.append(a)
        kept.append(iid)
    return (np.stack(X) if X else np.zeros((0, 1))), kept, excl


def _jitter(X: np.ndarray, seed: int, scale: float = 1e-6) -> np.ndarray:
    """X plus N(0, (scale * sd_feature)^2) noise: a tiny ridge that breaks exact degeneracies before the SVD retry."""
    sd = X.std(0)
    sd[sd == 0] = 1.0
    return X + np.random.default_rng(seed + 977).standard_normal(X.shape) * (scale * sd)


def position_rank(plabel: str, labels: Sequence[str]) -> int:
    """Latest position first: 0 (last), 1, ..., then candA, candB."""
    return list(labels).index(plabel)


# ------------------------------------------------------------------ one cell
def majority_rates(items: Mapping[str, dict], ids: Sequence[str], family: str) -> Dict[str, float]:
    """The favours-actual rate of the constant (class-prior) scorer per set: puzzles favour the actual symbol iff it is
    the more frequent class among all probed items; choices: the majority label 'actual == first-listed' of the set."""
    out: Dict[str, float] = {}
    if family == "puzzle":
        cnt = Counter(items[i]["primary"]["candidates"][0] for i in ids)
        for s in FAMILY_SETS[family]:
            sid = [i for i in ids if items[i]["set"] == s]
            fav = [cnt[items[i]["primary"]["candidates"][0]] > cnt[items[i]["primary"]["candidates"][1]] for i in sid]
            out[s] = float(np.mean(fav)) if fav else float("nan")
    else:
        for s in FAMILY_SETS[family]:
            sid = [i for i in ids if items[i]["set"] == s]
            y = [int(items[i]["primary"]["candidates"][0] == (items[i].get("source") or {}).get("first_listed")) for i in sid]
            out[s] = float(max(Counter(y).values()) / len(y)) if y else float("nan")
    return out


def balanced_accuracy(pred: Sequence[str], y: Sequence[str]) -> float:
    pred, y = np.asarray([str(p) for p in pred]), np.asarray([str(v) for v in y])
    recs = [float((pred[y == c] == c).mean()) for c in sorted(set(y.tolist()))]
    return float(np.mean(recs)) if recs else float("nan")


def probe_cell(X: np.ndarray, items: Mapping[str, dict], ids: Sequence[str], family: str, *, n_perm: int, n_boot: int, seed: int,
               n_folds: int) -> dict:
    """cv_probe on one cell; returns the per-set decision quantities."""
    sets = [items[i]["set"] for i in ids]
    actual = [items[i]["primary"]["candidates"][0] for i in ids]
    other = [items[i]["primary"]["candidates"][1] for i in ids]
    if family == "puzzle":
        y: list = list(actual)
        pair = {"favours_actual": (actual, other)}
    else:
        first = [(items[i].get("source") or {}).get("first_listed") for i in ids]
        y = [int(a == f) for a, f in zip(actual, first)]
        pair = {"favours_actual": (y, [1 - v for v in y])}
    t = time.time()
    maj = majority_rates(items, ids, family)
    out: dict = {"family": family, "n_items": len(ids), "status": None, "majority_rate": maj, "wall_s": 0.0, "by_set": {}, "retried": False}
    if not ids:
        out.update(status="skipped (no items in the cell)", wall_s=time.time() - t)
        return out
    try:
        rec = F.cv_probe(X, y, sets, pair, n_folds, n_perm, n_boot, seed, CS, "multinomial", group_sets=FAMILY_SETS[family])
    except (np.linalg.LinAlgError, ValueError) as exc:  # ill-conditioned cell: retry once on jittered features
        out.update(retried=True, retry_reason=f"{type(exc).__name__}: {exc}")
        try:
            rec = F.cv_probe(_jitter(X, seed), y, sets, pair, n_folds, n_perm, n_boot, seed, CS, "multinomial", group_sets=FAMILY_SETS[family])
        except (np.linalg.LinAlgError, ValueError) as exc2:
            out.update(status="failed", error=f"{type(exc2).__name__}: {exc2}", wall_s=time.time() - t)
            return out
    out.update(status=rec.get("status"), wall_s=time.time() - t)
    if rec.get("status") != "ok":
        return out
    ho = rec["held_out"]
    out.update(accuracy=ho["accuracy"]["p"], C_counts=ho.get("C_counts"), auroc=ho.get("auroc"),
               balanced_accuracy=balanced_accuracy(rec["held_out_pred"], y) if family == "puzzle" else None)
    for s in FAMILY_SETS[family]:
        r = ho["pair"]["favours_actual"]["by_set"][s]
        p95 = (rec.get("perm_null", {}).get(f"favours_actual_{s}") or {}).get("p95", float("nan"))
        pmean = (rec.get("perm_null", {}).get(f"favours_actual_{s}") or {}).get("mean", float("nan"))
        ceil = ((rec.get("ceiling") or {}).get("pair", {}).get("favours_actual", {}).get("by_set", {}).get(s) or {}).get("p", float("nan"))
        passes = bool(r["n"] > 0 and r["p"] >= PRESENT_WIN and r["boot_lo"] > maj[s] and (np.isnan(p95) or r["p"] > p95))
        out["by_set"][s] = {"k": r["k"], "n": r["n"], "p": r["p"], "boot_lo": r["boot_lo"], "boot_hi": r["boot_hi"], "wilson_lo": r["wilson_lo"],
                            "wilson_hi": r["wilson_hi"], "perm_p95": p95, "perm_mean": pmean, "ceiling_p": ceil, "majority_rate": maj[s],
                            "auroc": (ho.get("auroc_by_set") or {}).get(s), "passes": passes}
    return out


def _cell_job(args) -> Tuple[int, str, str, dict]:
    layer, plabel, family, X, items, ids, excl, kw = args
    try:
        rec = probe_cell(X, items, ids, family, **kw)
    except Exception as exc:  # noqa: BLE001 - a cell never aborts the sweep; it is recorded as failed
        rec = {"family": family, "n_items": len(ids), "status": "failed", "error": f"{type(exc).__name__}: {exc}", "by_set": {}, "wall_s": None}
    rec.update(n_excluded=int(sum(excl.values())), n_excluded_absent=int(excl.get("absent", 0)), n_excluded_nonfinite=int(excl.get("nonfinite", 0)))
    return layer, plabel, family, rec


def _ckpt_key(family: str, L: int, P: str) -> str:
    return f"{family}|{L}|{P}"


def load_sweep_checkpoint(path: Optional[Path], params: Mapping[str, Any]) -> Dict[str, dict]:
    """{family|L|P: rec} from an existing sweep_cells.jsonl; lines written under different sweep parameters are ignored."""
    done: Dict[str, dict] = {}
    if path is None or not Path(path).exists():
        return done
    n_other = 0
    for r in U.load_jsonl(path):
        if r.get("params") != dict(params):
            n_other += 1
            continue
        done[_ckpt_key(r["family"], int(r["layer"]), str(r["position"]))] = r["rec"]
    if n_other:
        U.log(f"[y1] {path}: ignoring {n_other} checkpointed cells written under other sweep parameters")
    return done


def _append_checkpoint(path: Optional[Path], family: str, L: int, P: str, rec: dict, params: Mapping[str, Any]) -> None:
    if path is None:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"family": family, "layer": L, "position": P, "params": dict(params), "rec": rec}, default=U._json_default) + "\n")


def _log_cell(L: int, P: str, family: str, rec: dict, k: int, n: int, resumed: bool = False) -> None:
    bs = rec.get("by_set", {})
    shown = ", ".join(f"{s} {bs[s]['p']:.2f}[{bs[s]['boot_lo']:.2f},{bs[s]['boot_hi']:.2f}] p95 {bs[s]['perm_p95']:.2f}" for s in bs)
    extra = (" excl=" + str(rec.get("n_excluded"))) if rec.get("n_excluded") else ""
    extra += " RETRIED" if rec.get("retried") else ""
    extra += f" ({rec.get('error')})" if rec.get("status") == "failed" else ""
    U.log(f"[y1] E10 {'resumed ' if resumed else ''}{k}/{n} {family:6s} L{L:02d} P{P:>5s}: n={rec['n_items']}{extra} {rec.get('status')} {shown}")


def sweep(items: Mapping[str, dict], caps: Mapping[str, dict], layers: Sequence[int], labels: Sequence[str], *, n_perm: int, n_boot: int,
          seed: int, n_folds: int, jobs: int = 1, ckpt_path: Optional[Path] = None) -> Dict[str, Dict[Tuple[int, str], dict]]:
    """{family: {(L, P): probe_cell result}} over every cell. Every finished cell is appended to ``ckpt_path`` (sweep_cells.jsonl)
    and cells already there (same n_perm/n_boot/seed/n_folds) are not recomputed, so an interrupted sweep resumes."""
    kw = {"n_perm": n_perm, "n_boot": n_boot, "seed": seed, "n_folds": n_folds}
    done = load_sweep_checkpoint(ckpt_path, kw)
    out: Dict[str, Dict[Tuple[int, str], dict]] = {"puzzle": {}, "choice": {}}
    jobs_list, n_cells = [], 0
    for family in ("puzzle", "choice"):
        fam_ids = sorted(i for i in caps if items[i]["family"] == family)
        if not fam_ids:
            continue
        sub = {i: items[i] for i in fam_ids}
        for L in layers:
            for P in labels:
                n_cells += 1
                if _ckpt_key(family, L, P) in done:
                    out[family][(L, P)] = done[_ckpt_key(family, L, P)]
                    continue
                X, kept, excl = cell_matrix(caps, fam_ids, L, P)
                jobs_list.append((L, P, family, X, sub, kept, excl, kw))
    n_done = n_cells - len(jobs_list)
    if n_done:
        U.log(f"[y1] E10 resuming: {n_done}/{n_cells} cells already in {ckpt_path}")
    t0 = time.time()
    k = n_done

    def finish(L, P, family, rec):
        nonlocal k
        k += 1
        out[family][(L, P)] = rec
        _append_checkpoint(ckpt_path, family, L, P, rec, kw)
        _log_cell(L, P, family, rec, k, n_cells)

    pending = set(range(len(jobs_list)))
    if jobs > 1 and len(pending) > 1:
        # one BLAS thread per worker: 8 workers x multithreaded OpenBLAS oversubscribes the Mac and is a known source of
        # non-deterministic LAPACK failures; the parent's own numpy is unaffected (already imported). User settings win.
        for var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
            os.environ.setdefault(var, "1")
        try:
            with ProcessPoolExecutor(max_workers=jobs) as ex:
                futs = {ex.submit(_cell_job, jobs_list[i]): i for i in sorted(pending)}
                for fut in as_completed(futs):
                    L, P, family, rec = fut.result()
                    finish(L, P, family, rec)
                    pending.discard(futs[fut])
        except BrokenProcessPool as exc:  # e.g. a spawn context without an importable __main__
            U.log(f"[y1] process pool failed ({exc}); running the remaining {len(pending)} cells serially")
    for i in sorted(pending):
        L, P, family, rec = _cell_job(jobs_list[i])
        finish(L, P, family, rec)
    n_failed = sum(1 for fam in out.values() for r in fam.values() if r.get("status") == "failed")
    U.log(f"[y1] E10 sweep: {n_cells} cells ({len(jobs_list)} computed, {n_done} resumed, {n_failed} failed) in {time.time() - t0:.0f}s (jobs={jobs})")
    return out


def sweep_rows(res: Mapping[str, Mapping[Tuple[int, str], dict]], labels: Sequence[str]) -> Dict[str, List[dict]]:
    """CSV rows per decision set (the control set of the same family is carried in the same row)."""
    rows: Dict[str, List[dict]] = {s: [] for s in DECISION_SETS}
    for family, cells in res.items():
        dec = "error" if family == "puzzle" else "disagree"
        ctrl = "error_control" if family == "puzzle" else "agree_control"
        for (L, P), rec in sorted(cells.items(), key=lambda kv: (kv[0][0], position_rank(kv[0][1], labels))):
            d = rec.get("by_set", {}).get(dec) or {}
            c = rec.get("by_set", {}).get(ctrl) or {}
            rows[dec].append({"layer": L, "position": P, "position_rank": position_rank(P, labels), "family": family, "set": dec, "status": rec.get("status"),
                              "n_items": rec["n_items"], "n_excluded": rec.get("n_excluded"), "n_excluded_absent": rec.get("n_excluded_absent"),
                              "n_excluded_nonfinite": rec.get("n_excluded_nonfinite"), "retried": rec.get("retried"), "error": rec.get("error"),
                              "n": d.get("n"), "k": d.get("k"), "rate": d.get("p"), "boot_lo": d.get("boot_lo"),
                              "boot_hi": d.get("boot_hi"), "wilson_lo": d.get("wilson_lo"), "wilson_hi": d.get("wilson_hi"), "perm_p95": d.get("perm_p95"),
                              "perm_mean": d.get("perm_mean"), "ceiling": d.get("ceiling_p"), "majority_rate": d.get("majority_rate"), "auroc": d.get("auroc"),
                              "passes": d.get("passes"), "accuracy_all": rec.get("accuracy"), "balanced_accuracy_all": rec.get("balanced_accuracy"),
                              "control_set": ctrl, "control_rate": c.get("p"), "control_boot_lo": c.get("boot_lo"), "control_boot_hi": c.get("boot_hi"),
                              "control_perm_p95": c.get("perm_p95"), "control_ceiling": c.get("ceiling_p"), "C_counts": json.dumps(rec.get("C_counts")),
                              "wall_s": rec.get("wall_s")})
    return rows


def choose_sstar(cells: Mapping[Tuple[int, str], dict], set_: str, labels: Sequence[str], max_layer: Optional[int] = None) -> Optional[dict]:
    """The earliest passing cell (smallest L, then latest position)."""
    passing = [(L, P, rec["by_set"][set_]) for (L, P), rec in cells.items() if rec.get("by_set", {}).get(set_, {}).get("passes")]
    if max_layer is not None:
        passing = [x for x in passing if x[0] <= max_layer]
    if not passing:
        return None
    L, P, d = min(passing, key=lambda x: (x[0], position_rank(x[1], labels)))
    return {"layer": L, "position": P, "site": Y.site_label(L, P), **d}


# ------------------------------------------------------------------ logit lens
def logitlens_table(ll_rows: Sequence[dict], items: Mapping[str, dict], n_boot: int, seed: int) -> Tuple[Dict[str, Dict[str, dict]], List[dict]]:
    """{set: {layer: {n, frac_pos, boot CI, wilson, mean_margin, median_margin}}} + csv rows; 'final' = the last block."""
    by_set: Dict[str, Dict[str, dict]] = {s: {} for s in SETS}
    rows_csv: List[dict] = []
    for s in SETS:
        rs = [r for r in ll_rows if r["item_id"] in items and items[r["item_id"]]["set"] == s and not r.get("unscorable") and r.get("margins")]
        layers = sorted({int(L) for r in rs for L in r["margins"]})
        n_unsc = sum(1 for r in ll_rows if r["item_id"] in items and items[r["item_id"]]["set"] == s and r.get("unscorable"))
        for L in layers:
            m = np.asarray([r["margins"][str(L)] for r in rs if str(L) in r["margins"]], float)
            p, lo, hi = F.boot_rate((m > 0).tolist(), n_boot, seed)
            _, wlo, whi = F.wilson(int((m > 0).sum()), int(m.size))
            fin = any(int(r.get("final_layer", -1)) == L and L not in (r.get("layers") or []) for r in rs)
            d = {"n": int(m.size), "k_pos": int((m > 0).sum()), "frac_pos": p, "boot_lo": lo, "boot_hi": hi, "wilson_lo": wlo, "wilson_hi": whi,
                 "mean_margin": float(m.mean()), "median_margin": float(np.median(m)), "is_final_layer": fin, "n_unscorable": n_unsc}
            by_set[s][str(L)] = d
            rows_csv.append({"set": s, "layer": L, **d})
    return by_set, rows_csv


# ------------------------------------------------------------------ E11 reread
def reread_table(lo_rows: Sequence[dict], items: Mapping[str, dict], site: str, probe_rates: Mapping[str, Optional[dict]], n_boot: int, seed: int
                 ) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    rows = [r for r in lo_rows if r.get("site") == site]
    for reader in sorted({r["reader"] for r in rows}):
        rr = [r for r in rows if r["reader"] == reader]
        gate_rows = {r["set"]: r for r in rr if r.get("condition") == "mean_state"}
        rec: dict = {"reader": reader, "site": site, "layer_used": next((r.get("layer_used") for r in rr), None),
                     "layer_role": next((r.get("layer_role") for r in rr), None), "by_set": {}, "e3_gate": {}}
        for s in SETS:
            g = gate_rows.get(s)
            rec["e3_gate"][s] = {"mean_lo": g.get("mean_lo") if g else None, "within_band": g.get("within_band") if g else None,
                                 "n_states_in_mean": g.get("n_states_in_mean") if g else None}
            ids = sorted(i for i, it in items.items() if it["set"] == s)
            by = {r["item_id"]: r for r in rr if r.get("condition") != "mean_state" and r.get("item_id") in items}
            flags = [bool(by[i]["favours_actual"]) for i in ids if i in by and by[i].get("lo_actual") is not None]
            n_unsc = sum(1 for i in ids if i in by and by[i].get("lo_actual") is None)
            n_missing = sum(1 for i in ids if i not in by)
            d = F.rate(flags, n_boot, seed) if flags else {"k": 0, "n": 0, "p": float("nan"), "boot_lo": float("nan"), "boot_hi": float("nan"),
                                                           "wilson_lo": float("nan"), "wilson_hi": float("nan")}
            pr = (probe_rates.get(s) or {}).get("p")
            within = (abs(d["p"] - pr) <= READ_WITHIN_PP) if (pr is not None and d["n"]) else None
            d.update(n_unscorable=n_unsc, n_missing=n_missing, probe_rate=pr, within_10pp_of_probe=within,
                     passes_rule=bool(d["n"] and d["p"] >= PRESENT_WIN and d["boot_lo"] > 0.5 and within))
            rec["by_set"][s] = d
        gate_ok = all(rec["e3_gate"][s]["within_band"] is True for s in SETS if rec["e3_gate"][s]["mean_lo"] is not None) and \
            any(rec["e3_gate"][s]["mean_lo"] is not None for s in SETS)
        rec["gate_passed"] = gate_ok
        if reader == "nla" and not gate_ok:
            verdict = "off-training-layer, failed gate"
        elif any(rec["by_set"][s]["n"] == 0 for s in DECISION_SETS):
            verdict = "no_data"
        elif all(rec["by_set"][s]["passes_rule"] for s in DECISION_SETS):
            verdict = "reads_the_model_at_S*"
        else:
            verdict = "no_evidence"
        rec["verdict"] = verdict
        out[reader] = rec
    return out


def reread_rows(tab: Mapping[str, dict]) -> List[dict]:
    rows = []
    for reader, rec in tab.items():
        for s in SETS:
            d = rec["by_set"][s]
            g = rec["e3_gate"][s]
            rows.append({"reader": reader, "site": rec["site"], "layer_used": rec["layer_used"], "layer_role": rec["layer_role"], "set": s, **d,
                         "e3_mean_lo": g["mean_lo"], "e3_within_band": g["within_band"], "gate_passed": rec["gate_passed"], "verdict": rec["verdict"]})
    return rows


# ------------------------------------------------------------------ figures
def _cmap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list("y1_blue", U.SEQ_BLUE)


def make_figure(path: Path, s: dict, frozen: bool) -> None:
    plt = U.mpl()
    labels: List[str] = s["grid"]["labels"]
    layers: List[int] = s["grid"]["layers"]
    cols = list(reversed(labels))  # prompt order: candA, candB, last-11, ..., last
    col_names = [("cand A\n(actual)" if c == "candA" else "cand B\n(other)" if c == "candB" else ("last" if c == "0" else f"last-{c}")) for c in cols]
    fig, axes = plt.subplots(1, 3, figsize=(17, 0.55 * len(layers) + 3.2), gridspec_kw={"width_ratios": [1.15, 1.15, 0.9]})
    cmap = _cmap()
    for ax, set_ in zip(axes[:2], DECISION_SETS):
        cells = s["E10"][set_]["cells"]
        M = np.full((len(layers), len(cols)), np.nan)
        for i, L in enumerate(layers):
            for j, P in enumerate(cols):
                d = cells.get(f"{L}:{P}")
                if d and d.get("n"):
                    M[i, j] = d["rate"]
        im = ax.imshow(M, cmap=cmap, vmin=0.5, vmax=1.0, aspect="auto", origin="lower")
        for i, L in enumerate(layers):
            for j, P in enumerate(cols):
                d = cells.get(f"{L}:{P}")
                if not d or not d.get("n"):
                    ax.text(j, i, "–", ha="center", va="center", color=U.INK2, fontsize=8)
                    continue
                dark = d["rate"] > 0.8
                ax.text(j, i, f"{100 * d['rate']:.0f}", ha="center", va="center", fontsize=7.5, color=("white" if dark else U.INK))
                if d.get("passes"):
                    ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=U.INK, lw=0.9))
        st = s["E10"][set_]["S_star"]
        if st:
            i, j = layers.index(st["layer"]), cols.index(st["position"])
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="#d7263d", lw=2.6))
            ax.text(j, i + 0.62, "S*", ha="center", va="bottom", fontsize=8.5, color="#d7263d", fontweight="bold")
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels(col_names, fontsize=7.5, rotation=60, ha="right")
        ax.set_yticks(range(len(layers)))
        ax.set_yticklabels([f"L{L}" for L in layers], fontsize=8)
        ax.set_xlabel("position (block output)")
        if set_ == DECISION_SETS[0]:
            ax.set_ylabel("layer (decoder block index)")
        n = s["counts"][set_]
        star = f"S* = {st['site']} ({100 * st['p']:.0f}%)" if st else ("no S* (K7)" if set_ == "error" else "no S*")
        under = " — UNDERPOWERED" if s["underpowered"].get(set_) else ""
        ax.set_title(f"{SET_LABEL[set_]}\nn = {n}{under}; {star}", fontsize=9.5)
        for sp in ax.spines.values():
            sp.set_visible(False)
    ax = axes[2]
    ll = s["logit_lens"]["by_set"]
    for set_ in SETS:
        d = ll.get(set_) or {}
        Ls = sorted(int(L) for L in d if not d[L].get("is_final_layer"))
        if not Ls:
            continue
        ys = [d[str(L)]["frac_pos"] for L in Ls]
        lo = [d[str(L)]["boot_lo"] for L in Ls]
        hi = [d[str(L)]["boot_hi"] for L in Ls]
        ax.plot(Ls, ys, color=SET_COLOR[set_], lw=2 if set_ in DECISION_SETS else 1.4, ls="-" if set_ in DECISION_SETS else "--",
                marker="o", ms=4, label=f"{set_} (n={d[str(Ls[0])]['n']})")
        ax.fill_between(Ls, lo, hi, color=SET_COLOR[set_], alpha=0.12, lw=0)
        fin = [L for L in d if d[L].get("is_final_layer")]
        if fin:
            ax.plot([int(fin[0])], [d[fin[0]]["frac_pos"]], color=SET_COLOR[set_], marker="s", ms=5, ls="none")
    ax.axhline(PRESENT_WIN, color=U.INK2, lw=0.8, ls=(0, (1, 3)))
    ax.axhline(0.5, color=U.GRID, lw=1.0)
    for set_ in DECISION_SETS:
        st = s["E10"][set_]["S_star"]
        if st:
            ax.axvline(st["layer"], color="#d7263d", lw=1.0, ls=":")
    ax.set_xlabel("layer (block output, last position)")
    ax.set_title("logit-lens reference: % items with\nlp(actual 1st token) > lp(other 1st token)", fontsize=9.5)
    ax.legend(fontsize=7.5, loc="lower right")
    U.style_ax(ax, "% items (band = 95% item bootstrap)", (0, 1.05))
    k7 = s["K7"]["killed"]
    fig.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + "Y1 site search — E10 held-out probe for the model's ACTUAL answer (cell = favours-actual rate; "
                 f"outlined = passes rule; red = S*)\n{'K7: no site with L <= 58 on ERROR' if k7 else 'S*(ERROR) = ' + s['S_star']['site']}"
                 + ("; logit lens already separates there" if s["S_star"] and s["S_star"].get("logit_lens_separates") else ""), y=1.02, fontsize=10)
    fig.subplots_adjust(left=0.06, right=0.98, bottom=0.22, top=0.86, wspace=0.3)
    pos = axes[1].get_position()
    cax = fig.add_axes([pos.x1 + 0.008, pos.y0, 0.01, pos.height])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("held-out probe: % items favours ACTUAL answer", fontsize=8.5)
    cb.ax.tick_params(labelsize=7.5)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def make_reread_figure(path: Path, s: dict, frozen: bool) -> None:
    plt = U.mpl()
    tab = s["E11"]["readers"]
    site = s["E11"]["site"]
    readers = ["probe"] + [r for r in READERS if r in tab] + [r for r in tab if r not in READERS]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, set_ in zip(axes, DECISION_SETS):
        for j, rd in enumerate(readers):
            if rd == "probe":
                d = s["E11"]["probe_at_site"].get(set_) or {}
                rate = U.Rate(d.get("k", 0), d.get("n", 0), d.get("p", float("nan")), d.get("boot_lo", float("nan")), d.get("boot_hi", float("nan")),
                              d.get("n", 0), ci="item-bootstrap")
                U.bar_ci(ax, j, rate, READER_COLOR["probe"], width=0.62, hollow=True)
            else:
                d = tab[rd]["by_set"][set_]
                rate = U.Rate(d["k"], d["n"], d["p"], d["boot_lo"], d["boot_hi"], d["n"], ci="item-bootstrap")
                U.bar_ci(ax, j, rate, READER_COLOR.get(rd, "#888888"), width=0.62)
                if rd == "nla" and not tab[rd]["gate_passed"]:
                    ax.text(j, 0.04, "failed\nE3 gate", ha="center", va="bottom", fontsize=7, color="white")
        ax.axhline(0.5, color=U.GRID, lw=1.0, zorder=1)
        ax.axhline(PRESENT_WIN, color=U.INK2, lw=0.8, ls=(0, (1, 3)), zorder=1)
        ax.set_xticks(range(len(readers)))
        ax.set_xticklabels([READER_LABEL.get(r, r) for r in readers], fontsize=8, rotation=20, ha="right")
        ax.set_title(f"{SET_LABEL[set_]}\nn = {s['counts'][set_]}", fontsize=9.5)
        U.style_ax(ax, "% items: LO favours ACTUAL answer at S*" if set_ == DECISION_SETS[0] else None, (0, 1.18))
    verdicts = "; ".join(f"{READER_LABEL.get(r, r)}: {tab[r]['verdict'].replace('_', ' ')}" for r in tab)
    fig.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + f"Y1 E11 re-read at S* = {site} (bars = 95% item-bootstrap CI; hollow = E10 probe; dotted = 0.75)\n{verdicts}",
                 y=1.04, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ run
def run(args: argparse.Namespace) -> dict:
    frozen, _cfg = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if frozen else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    meta, items = load_selected(args.selected)
    counts = {s: sum(it["set"] == s for it in items.values()) for s in SETS}
    underpowered = {"error": counts["error"] < Y.X3.MIN_SET, "disagree": counts["disagree"] < Y.MIN_DISAGREE}
    nb, sd = args.n_boot, args.seed
    U.log(f"[y1] frozen={frozen} {len(items)} selected items {counts}; underpowered {underpowered}; out={out}")
    summary_path = out / "summary.json"

    if args.reread_only:
        if not summary_path.exists():
            raise U.AnalysisError(f"--reread-only needs an existing {summary_path}")
        summary = U.load_json(summary_path)
    else:
        caps, missing = load_caps(items, args.caps_dir)
        if missing:
            U.log(f"[y1] {len(missing)} selected items without a capture (e.g. {missing[:4]})")
        layers, labels = grid_of(caps)
        if args.layers:
            layers = [L for L in layers if L in {int(x) for x in args.layers.split(",")}]
        if args.positions:
            labels_sub = [p.strip() for p in args.positions.split(",")]
            labels = [p for p in labels if p in labels_sub]
        if not caps or not layers or not labels:
            raise U.AnalysisError("no captures / layers / positions to analyse")
        n_cand_absent = {lab: sum(1 for c in caps.values() if c["positions"][c["labels"].index(lab)] < 0) for lab in Y.CAND_LABELS if lab in labels}
        U.log(f"[y1] {len(caps)} captures; layers {layers}; positions {labels}; candidate positions absent: {n_cand_absent}")
        res = sweep(items, caps, layers, labels, n_perm=args.n_perm, n_boot=nb, seed=sd, n_folds=args.n_folds, jobs=args.jobs,
                    ckpt_path=out / "sweep_cells.jsonl")
        rows = sweep_rows(res, labels)
        n_failed = {fam: sorted(f"{L}:{P}" for (L, P), r in cells.items() if r.get("status") == "failed") for fam, cells in res.items()}
        if any(n_failed.values()):
            U.log(f"[y1] E10 failed cells (status failed, excluded from S*): {n_failed}")
        for set_ in DECISION_SETS:
            U.write_csv(out / f"sweep_{set_}.csv", rows[set_])
        # S* per set
        e10: Dict[str, dict] = {}
        for set_ in DECISION_SETS:
            fam = FAMILY_OF[set_]
            cells = res[fam]
            st = choose_sstar(cells, set_, labels)
            e10[set_] = {"S_star": st, "S_star_L_le_58": choose_sstar(cells, set_, labels, K7_MAX_LAYER), "n_cells": len(cells),
                         "n_passing": sum(1 for r in rows[set_] if r["passes"]),
                         "n_failed": sum(1 for r in rows[set_] if r["status"] == "failed"), "failed_cells": n_failed[fam],
                         "n_excluded_total": sum(int(r["n_excluded"] or 0) for r in rows[set_]),
                         "cells": {f"{r['layer']}:{r['position']}": {"rate": r["rate"], "n": r["n"], "k": r["k"], "boot_lo": r["boot_lo"], "boot_hi": r["boot_hi"],
                                                                      "perm_p95": r["perm_p95"], "ceiling": r["ceiling"], "majority_rate": r["majority_rate"],
                                                                      "passes": r["passes"], "balanced_accuracy_all": r["balanced_accuracy_all"],
                                                                      "control_rate": r["control_rate"], "status": r["status"], "n_excluded": r["n_excluded"],
                                                                      "n_excluded_absent": r["n_excluded_absent"], "n_excluded_nonfinite": r["n_excluded_nonfinite"],
                                                                      "retried": r["retried"], "error": r["error"]} for r in rows[set_]}}
            U.log(f"[y1] E10 {set_}: {e10[set_]['n_passing']}/{len(cells)} cells pass; S* = {st['site'] if st else None}"
                  + (f" rate {st['p']:.2f} [{st['boot_lo']:.2f}, {st['boot_hi']:.2f}] perm p95 {st['perm_p95']:.2f} ceiling {st['ceiling_p']:.2f}" if st else ""))
        # logit lens
        ll_rows = U.load_jsonl(args.logitlens) if Path(args.logitlens).exists() else []
        ll_by_set, ll_csv = logitlens_table(ll_rows, items, nb, sd)
        U.write_csv(out / "logitlens.csv", ll_csv)
        for set_ in SETS:
            d = ll_by_set.get(set_) or {}
            if d:
                U.log(f"[y1] logit lens {set_}: " + ", ".join(f"L{L} {100 * d[L]['frac_pos']:.0f}%" for L in sorted(d, key=int)))
        sstar = e10["error"]["S_star_L_le_58"]
        k7 = sstar is None
        if sstar:
            llE = (ll_by_set.get("error") or {}).get(str(sstar["layer"]))
            sstar = {**sstar, "logit_lens_frac_pos_error": llE["frac_pos"] if llE else None,
                     "logit_lens_separates": bool(llE and llE["frac_pos"] >= PRESENT_WIN)}
        U.log(f"[y1] K7 {'KILLED: no S* on ERROR with L <= 58' if k7 else 'not triggered: S* = ' + sstar['site']}"
              + (" (logit lens already separates there)" if sstar and sstar["logit_lens_separates"] else ""))
        summary = {"module": MODULE, "frozen": frozen, "selected_meta": {k: v for k, v in meta.items() if k != "rule"}, "counts": counts,
                   "underpowered": underpowered, "n_boot": nb, "n_perm": args.n_perm, "n_folds": args.n_folds, "seed": sd, "Cs": list(CS),
                   "n_captures": len(caps), "n_missing_captures": len(missing), "grid": {"layers": layers, "labels": labels},
                   "candidate_positions_absent": n_cand_absent, "E10": e10, "S_star": sstar,
                   "K7": {"killed": k7, "max_layer": K7_MAX_LAYER,
                          "statement": ("the off-text answer is not linearly present before answer formation at the pre-answer token "
                                        f"(no cell with L <= {K7_MAX_LAYER} passes on ERROR)") if k7 else None},
                   "logit_lens": {"by_set": ll_by_set, "n_rows": len(ll_rows),
                                  "n_unscorable": sum(1 for r in ll_rows if r.get("unscorable") and r["item_id"] in items),
                                  "forms": dict(Counter(r.get("form") for r in ll_rows if r["item_id"] in items))},
                   "decision_rule": (f"E10: S* = earliest (smallest L, then latest P) cell with held-out favours-actual >= {PRESENT_WIN}, item-bootstrap CI "
                                     f"excluding the majority rate, and rate > the {args.n_perm}-permutation p95; K7 if none with L <= {K7_MAX_LAYER} on ERROR. "
                                     f"E11: reader reads the model at S* if >= {PRESENT_WIN} with CI excluding 0.5 and within {100 * READ_WITHIN_PP:.0f} pp of the probe "
                                     f"on ERROR and DISAGREE; NLA gated by the mean-state LO within +-{E3_BAND} nat.")}
        U.write_json(summary_path, summary)
        if not args.no_fig:
            make_figure(out / "fig_main.png", summary, frozen)

    # E11 reread
    site = args.site or ((summary.get("S_star") or {}).get("site"))
    lo_rows = U.load_jsonl(args.lo) if Path(args.lo).exists() else []
    if site and lo_rows:
        L, P = Y.parse_site(site)
        site = Y.site_label(L, P)
        probe_at = {}
        for set_ in DECISION_SETS:
            c = summary["E10"][set_]["cells"].get(site)
            probe_at[set_] = {"k": c["k"], "n": c["n"], "p": c["rate"], "boot_lo": c["boot_lo"], "boot_hi": c["boot_hi"]} if c else None
        tab = reread_table(lo_rows, items, site, probe_at, nb, sd)
        for rd, rec in tab.items():
            for set_ in DECISION_SETS:
                d = rec["by_set"][set_]
                U.log(f"[y1] E11 {rd:12s} {set_:9s} favours actual {d['k']}/{d['n']} = {100 * d['p']:.1f}% [{100 * d['boot_lo']:.0f}, {100 * d['boot_hi']:.0f}] "
                      f"probe {d['probe_rate']}; gate {rec['e3_gate'][set_]['within_band']}")
            U.log(f"[y1] E11 {rd:12s} -> {rec['verdict']}")
        summary["E11"] = {"site": site, "probe_at_site": probe_at, "readers": tab, "n_lo_rows_at_site": sum(1 for r in lo_rows if r.get("site") == site)}
        U.write_csv(out / "reread.csv", reread_rows(tab))
        U.write_json(summary_path, summary)
        if not args.no_fig and tab:
            make_reread_figure(out / "fig_reread.png", summary, frozen)
    elif site:
        U.log(f"[y1] E11: no LO rows yet at {site} (run collect.py --stage reread --site {site})")
    U.log(f"[y1] wrote {out}")
    return summary


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
