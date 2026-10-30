#!/usr/bin/env python
"""V5 window reader (PREREG_WV.md §V5): fits, held-out metrics, v5.csv / v5.md / fig_v5.png, saved weights.

Usage: OMP_NUM_THREADS=4 PYTHONPATH=. .venv/bin/python projects/g_agreement/v5_window/run.py [--device auto|mps|cpu] [--n-boot 1000]
       [--inner 2] [--folds 8] [--seed 0] [--max-epochs 150] [--patience 15] [--lr 1e-2] [--out results/g_agreement/v] [--weights cache/g_agreement/v/window_reader]
       [--quick]   (--quick: 2 outer folds, 200 bootstraps, for smoke runs; writes into <out>/dev_v5/)
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.v5_window import data as D  # noqa: E402
from projects.g_agreement.v5_window import folds as F  # noqa: E402
from projects.g_agreement.v5_window import models as M  # noqa: E402

ERROR_LAYERS, FULL_LAYERS = (42, 48), (38, 42)
READERS = ("jlens", "olens", "nla")
READER_LABEL = {"jlens": "J-lens", "olens": "Oracle lens", "nla": "NLA", "last_linear": "(a) last-token linear"}
WIN_SUCCESS_PP, WIN_SUCCESS_AUROC = 0.10, 0.05
# Z1 gain_over_dose.md (2026-10-09), S2+S3 planted, E1 out-of-fold, dose-only = logistic flip ~ alpha: reader AUROC / dose AUROC
Z1_T2_REFERENCE = {"Oracle lens": (0.907, 0.946), "J-lens": (0.904, 0.947), "NLA": (0.804, 0.947)}
T0 = time.time()


def log(msg: str = "") -> None:
    print(f"[v5 {time.time() - T0:7.1f}s] {msg}", flush=True)


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--inner", type=int, default=2)
    ap.add_argument("--folds", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-epochs", type=int, default=150)
    ap.add_argument("--patience", type=int, default=15)
    ap.add_argument("--lr", type=float, default=1e-2)
    ap.add_argument("--out", default=str(ROOT / "results" / "g_agreement" / "v"))
    ap.add_argument("--weights", default=str(ROOT / "cache" / "g_agreement" / "v" / "window_reader"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--fig-only", action="store_true", help="rebuild <out>/fig_v5.png from <out>/v5.csv (no fits)")
    return ap.parse_args(argv)


# ------------------------------------------------------------------------------------------------------- statistics
def boot_mean(flags: Sequence[float], n_boot: int, seed: int) -> Tuple[float, float, float]:
    x = np.asarray(flags, float)
    if x.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    v = x[rng.integers(0, x.size, size=(n_boot, x.size))].mean(1)
    return float(x.mean()), float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))


def boot_paired_diff(a: Sequence[float], b: Sequence[float], n_boot: int, seed: int) -> Tuple[float, float, float]:
    """mean(a) - mean(b) on the same items, item bootstrap (paired)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, a.size, size=(n_boot, a.size))
    v = a[idx].mean(1) - b[idx].mean(1)
    return float(a.mean() - b.mean()), float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    from scipy.stats import rankdata

    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = labels == 1, labels == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    r = rankdata(scores)
    return float((r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def pair_boot_auroc(scores: np.ndarray, ref: np.ndarray, labels: np.ndarray, pairs: Sequence[str], n_boot: int, seed: int) -> dict:
    """AUROC of ``scores`` and ``ref`` and their paired difference under a pair bootstrap (pairs resampled once, both recomputed)."""
    pairs = np.asarray(pairs)
    uniq = sorted(set(pairs.tolist()))
    members = {p: np.where(pairs == p)[0] for p in uniq}
    rng = np.random.default_rng(seed)
    a, r, d = [], [], []
    for _ in range(n_boot):
        pick = rng.integers(0, len(uniq), len(uniq))
        idx = np.concatenate([members[uniq[i]] for i in pick])
        ai, ri = auroc(scores[idx], labels[idx]), auroc(ref[idx], labels[idx])
        if np.isnan(ai) or np.isnan(ri):
            continue
        a.append(ai)
        r.append(ri)
        d.append(ai - ri)
    q = lambda v: (float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))) if v else (float("nan"), float("nan"))
    return {"auroc": auroc(scores, labels), "auroc_lo": q(a)[0], "auroc_hi": q(a)[1], "ref_auroc": auroc(ref, labels), "ref_lo": q(r)[0],
            "ref_hi": q(r)[1], "delta": auroc(scores, labels) - auroc(ref, labels), "delta_lo": q(d)[0], "delta_hi": q(d)[1], "n_pairs": len(uniq),
            "n_boot_used": len(d)}


# ------------------------------------------------------------------------------------------------------- fitting
def pooled_view(w: D.Windows, kind: str) -> Tuple[torch.Tensor, torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
    """(x, mask, stats) to train ``kind`` on. (a) and (b) are linear in a fixed pooled vector, so they are trained on that vector
    (T = 1) - identical model, far cheaper. For (b) the standardiser must still be the all-position one (affine, so standardising
    the mean = the mean of the standardised positions): returned as ``stats`` and set on the model after init."""
    if kind == "last_linear":
        li = M.last_index(w.mask)
        return w.x[torch.arange(len(w)), li].unsqueeze(1), torch.ones(len(w), 1, dtype=torch.bool), None
    if kind == "mean_linear":
        v = w.x[w.mask]
        mu, sd = v.mean(0), v.std(0, unbiased=False)
        sd = torch.where(sd > 0, sd, torch.ones_like(sd))
        return M.masked_mean(w.x, w.mask).unsqueeze(1), torch.ones(len(w), 1, dtype=torch.bool), (mu, sd)
    return w.x, w.mask, None


def _fit(kind: str, x: torch.Tensor, mask: torch.Tensor, y: torch.Tensor, n_classes: int, splits, args, seed: int,
         stats: Optional[Tuple[torch.Tensor, torch.Tensor]]) -> M.FitResult:
    fit = M.fit_inner_cv(kind, x, mask, y, n_classes, splits, M.LAMBDAS, max_epochs=args.max_epochs, lr=args.lr, patience=args.patience, seed=seed)
    return fit


def _train_with_stats(kind, xtr, mtr, ytr, n_classes, splits, args, seed, stats):
    """fit_inner_cv, but with a fixed standardiser (mean-pooled model trained on pooled vectors)."""
    if stats is None:
        return M.fit_inner_cv(kind, xtr, mtr, ytr, n_classes, splits, M.LAMBDAS, max_epochs=args.max_epochs, lr=args.lr, patience=args.patience, seed=seed)
    orig = M.Reader.set_standardiser
    mu, sd = stats

    def fixed(self, x, mask):  # noqa: ANN001
        self.mu.copy_(mu.to(self.mu.device))
        self.sd.copy_(sd.to(self.sd.device))

    M.Reader.set_standardiser = fixed
    try:
        return M.fit_inner_cv(kind, xtr, mtr, ytr, n_classes, splits, M.LAMBDAS, max_epochs=args.max_epochs, lr=args.lr, patience=args.patience, seed=seed)
    finally:
        M.Reader.set_standardiser = orig


def run_cv(w: D.Windows, fold_ids: np.ndarray, unit_of_row: Sequence[str], kinds: Sequence[str], device: torch.device, args, tag: str,
           weights_dir: Optional[Path]) -> Dict[str, dict]:
    """Out-of-fold logits per kind: {kind: {"logits": [n, K], "fits": [{fold, lambda, epochs, wall_s}]}}."""
    n_classes = len(w.classes)
    out: Dict[str, dict] = {}
    for kind in kinds:
        x_all, m_all, stats = pooled_view(w, kind)
        x_all, m_all = x_all.to(device), m_all.to(device)
        y_all = torch.as_tensor(w.y, device=device)
        logits = np.full((len(w), n_classes), np.nan)
        fits = []
        for f, tr, te in F.outer_splits(fold_ids):
            splits = F.inner_splits(tr, unit_of_row, args.inner, args.seed + 101 + f)
            tr_t, te_t = torch.as_tensor(tr, device=device), torch.as_tensor(te, device=device)
            stats_tr = None
            if stats is not None:  # recompute the all-position standardiser on the training rows only
                v = w.x[tr][w.mask[tr]]
                mu, sd = v.mean(0), v.std(0, unbiased=False)
                stats_tr = (mu, torch.where(sd > 0, sd, torch.ones_like(sd)))
            fit = _train_with_stats(kind, x_all[tr_t], m_all[tr_t], y_all[tr_t], n_classes, splits, args, args.seed + f, stats_tr)
            logits[te] = M.predict_logits(fit.model, x_all[te_t], m_all[te_t])
            fits.append({"fold": int(f), "lambda": fit.lam, "epochs": fit.epochs, "wall_s": round(fit.wall_s, 1), "n_train": int(len(tr)), "n_test": int(len(te))})
            if weights_dir is not None:
                weights_dir.mkdir(parents=True, exist_ok=True)
                torch.save(M.export_state(fit, tag=tag, fold=int(f), test_ids=[w.ids[i] for i in te], classes=w.classes), weights_dir / f"{tag}__{kind}__fold{f}.pt")
            log(f"{tag} {kind} fold {f}: lambda {fit.lam:g}, {fit.epochs} ep, {fit.wall_s:.1f}s (train {len(tr)}, test {len(te)})")
        out[kind] = {"logits": logits, "fits": fits}
    return out


def run_transfer(w_tr: D.Windows, w_te: D.Windows, unit_tr: Sequence[str], kinds: Sequence[str], device: torch.device, args, tag: str,
                 weights_dir: Optional[Path]) -> Dict[str, dict]:
    n_classes = len(w_tr.classes)
    out = {}
    for kind in kinds:
        xtr, mtr, stats = pooled_view(w_tr, kind)
        xte, mte, _ = pooled_view(w_te, kind)
        splits = F.inner_splits(np.arange(len(w_tr)), unit_tr, args.inner, args.seed + 202)
        fit = _train_with_stats(kind, xtr.to(device), mtr.to(device), torch.as_tensor(w_tr.y, device=device), n_classes, splits, args, args.seed, stats)
        logits = M.predict_logits(fit.model, xte.to(device), mte.to(device))
        # label-free re-standardisation: the test family's own feature mean/sd (its activations have a different mean), weights unchanged
        mu0, sd0 = fit.model.mu.clone(), fit.model.sd.clone()
        fit.model.set_standardiser(w_te.x.to(device), w_te.mask.to(device))
        if stats is not None:
            v = w_te.x[w_te.mask]
            sdv = v.std(0, unbiased=False)
            fit.model.mu.copy_(v.mean(0).to(device))
            fit.model.sd.copy_(torch.where(sdv > 0, sdv, torch.ones_like(sdv)).to(device))
        logits_restd = M.predict_logits(fit.model, xte.to(device), mte.to(device))
        fit.model.mu.copy_(mu0)
        fit.model.sd.copy_(sd0)
        if weights_dir is not None:
            weights_dir.mkdir(parents=True, exist_ok=True)
            torch.save(M.export_state(fit, tag=tag, fold=None, test_ids=list(w_te.ids), classes=w_tr.classes), weights_dir / f"{tag}__{kind}.pt")
        log(f"{tag} {kind}: lambda {fit.lam:g}, {fit.epochs} ep, {fit.wall_s:.1f}s")
        out[kind] = {"logits": logits, "logits_restd": logits_restd,
                     "fits": [{"fold": None, "lambda": fit.lam, "epochs": fit.epochs, "wall_s": round(fit.wall_s, 1), "n_train": len(w_tr), "n_test": len(w_te)}]}
    return out


def favours_flags(w: D.Windows, logits: np.ndarray) -> np.ndarray:
    """errors: logit[cand_actual] - logit[cand_other] > 0 per item."""
    ci = {c: i for i, c in enumerate(w.classes)}
    a = np.array([ci[c] for c in w.meta["cand_actual"]])
    b = np.array([ci[c] for c in w.meta["cand_other"]])
    return (logits[np.arange(len(w)), a] - logits[np.arange(len(w)), b] > 0).astype(float)


def dose_only_oof(cells: Sequence[str], y: np.ndarray, fold_ids: np.ndarray) -> np.ndarray:
    """P(flip) = the training folds' flip rate of the entry's (site, alpha) cell; an unseen cell -> the training flip rate."""
    cells = np.asarray(cells)
    out = np.zeros(len(y), float)
    for f in sorted(set(fold_ids.tolist())):
        tr, te = fold_ids != f, fold_ids == f
        base = y[tr].mean()
        rate = {c: y[tr & (cells == c)].mean() for c in set(cells[tr].tolist())}
        out[te] = [rate.get(c, base) for c in cells[te]]
    return out


# ------------------------------------------------------------------------------------------------------- main
def main(argv=None) -> dict:
    args = parse_args(argv)
    if args.fig_only:
        out_dir = Path(args.out) / ("dev_v5" if args.quick else "")
        make_fig(out_dir / "fig_v5.png", rows_from_csv(out_dir / "v5.csv"))
        log(f"rebuilt {out_dir / 'fig_v5.png'} from v5.csv")
        return {}
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "4")))
    device = M.pick_device(args.device)
    out_dir = Path(args.out) / ("dev_v5" if args.quick else "")
    weights_dir = Path(args.weights) / ("dev" if args.quick else "")
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.quick:
        args.folds, args.n_boot = 2, 200
    nb, seed = args.n_boot, args.seed
    log(f"device {device}; torch {torch.__version__}; {platform.platform()}; folds {args.folds}, inner {args.inner}, n_boot {nb}")
    rows: List[dict] = []
    fold_record: Dict[str, dict] = {}
    timing: Dict[str, float] = {}
    summary: Dict[str, dict] = {}

    # ================================================================================== T1 errors
    t = time.time()
    items = D.load_error_items()
    EW = D.load_error_windows(ERROR_LAYERS, items)
    w0 = EW[ERROR_LAYERS[0]]
    groups = F.error_groups(items, w0.ids)
    fold_err = F.group_folds(w0.ids, groups, {g: g.split("|")[0] for g in groups.values()}, args.folds, seed)
    fold_record["errors"] = {"unit": "(k, start) group", "n_groups": len(set(groups.values())), "fold_of_item": dict(zip(w0.ids, fold_err.tolist())),
                             "template_ids": sorted(set(t for t in w0.meta["template_id"] if t))}
    unit_err = [groups[i] for i in w0.ids]
    readers_at = {42: D.reader_flags(D.X3_LO, items, layer=42), 48: D.reader_flags(D.Y1_LO, items, site="48:0")}
    err_res: Dict[int, Dict[str, dict]] = {}
    for L in ERROR_LAYERS:
        w = EW[L]
        err_res[L] = run_cv(w, fold_err, unit_err, M.MODELS, device, args, f"t1_errors_L{L}", weights_dir / "t1_errors")
        sets = np.array(w.meta["set"])
        fav = {k: favours_flags(w, r["logits"]) for k, r in err_res[L].items()}
        acc = {k: (r["logits"].argmax(1) == w.y).astype(float) for k, r in err_res[L].items()}
        # best last-token reader on the ERROR set (point estimate): (a) and the three readers, per item flags
        cand: Dict[str, np.ndarray] = {"last_linear": fav["last_linear"]}
        for rd in READERS:
            fl = readers_at[L].get(rd, {})
            cand[rd] = np.array([float(fl[i]) if i in fl else np.nan for i in w.ids])
        err_mask = sets == "error"
        best_name = max(cand, key=lambda k: np.nanmean(cand[k][err_mask]))
        summary[f"errors_L{L}"] = {"best_last_token": best_name, "best_rate": float(np.nanmean(cand[best_name][err_mask]))}
        for s in D.ERROR_SETS:
            sm = sets == s
            for rd in READERS:
                ok = sm & ~np.isnan(cand[rd])
                p, lo, hi = boot_mean(cand[rd][ok], nb, seed)
                rows.append(dict(target="T1", dataset="errors", layer=L, train="-", test=s, model=f"reader:{rd}", set=s, metric="p_favours_actual",
                                 n=int(ok.sum()), estimate=p, ci_lo=lo, ci_hi=hi))
            for k in M.MODELS:
                p, lo, hi = boot_mean(fav[k][sm], nb, seed)
                a, alo, ahi = boot_mean(acc[k][sm], nb, seed)
                ref = cand[best_name]
                ok = sm & ~np.isnan(ref)
                dlt, dlo, dhi = boot_paired_diff(fav[k][ok], ref[ok], nb, seed)
                fits = err_res[L][k]["fits"]
                extra = dict(ref_best_last=best_name, delta=dlt, delta_lo=dlo, delta_hi=dhi, lambdas=json.dumps(Counter(f["lambda"] for f in fits)),
                             epochs=json.dumps([f["epochs"] for f in fits]))
                rows.append(dict(target="T1", dataset="errors", layer=L, train="cv", test=s, model=k, set=s, metric="p_favours_actual", n=int(sm.sum()),
                                 estimate=p, ci_lo=lo, ci_hi=hi, **extra))
                rows.append(dict(target="T1", dataset="errors", layer=L, train="cv", test=s, model=k, set=s, metric="accuracy_8way", n=int(sm.sum()),
                                 estimate=a, ci_lo=alo, ci_hi=ahi, **extra))
        # chance / majority references
        maj = Counter(w.meta["cand_actual"][i] for i in range(len(w)))
        for s in D.ERROR_SETS:
            sm = sets == s
            mflags = [float(maj[w.meta["cand_actual"][i]] > maj[w.meta["cand_other"][i]]) for i in np.where(sm)[0]]
            rows.append(dict(target="T1", dataset="errors", layer=L, train="-", test=s, model="majority_symbol", set=s, metric="p_favours_actual", n=int(sm.sum()),
                             estimate=float(np.mean(mflags)), ci_lo=float("nan"), ci_hi=float("nan")))
    timing["t1_errors_s"] = time.time() - t
    log(f"T1 errors done in {timing['t1_errors_s']:.0f}s")

    # ================================================================================== T1 / T3 ownership + mapping (natural)
    t = time.time()
    xitems = D.load_x_items()
    FW = D.load_full_windows(FULL_LAYERS, xitems)
    wf = FW[FULL_LAYERS[0]]
    fam_of_pair = {p: f for p, f in zip(wf.meta["pair_id"], wf.meta["family"])}
    pair_fold = F.assign_folds(set(wf.meta["pair_id"]), fam_of_pair, args.folds, seed)
    fold_full = np.array([pair_fold[p] for p in wf.meta["pair_id"]])
    fold_record["own_map"] = {"unit": "pair (stratified by family)", "fold_of_pair": pair_fold}
    unit_full = list(wf.meta["pair_id"])
    fams = np.array(wf.meta["family"])
    y_t1 = np.array([np.nan if v is None else float(v) for v in wf.meta["y_t1"]])
    n_t1_excl = int(np.isnan(y_t1).sum())
    summary["own_map"] = {"n_items": len(wf), "n_t1_unparsed": n_t1_excl, "t1_t3_identical_on_parsed": bool(np.all((y_t1 == wf.y)[~np.isnan(y_t1)]))}
    full_res: Dict[int, Dict[str, dict]] = {}
    for L in FULL_LAYERS:
        w = FW[L]
        full_res[L] = run_cv(w, fold_full, unit_full, M.MODELS, device, args, f"t1t3_ownmap_L{L}", weights_dir / "t1t3_own_map")
        for k in M.MODELS:
            pred = full_res[L][k]["logits"].argmax(1)
            fits = full_res[L][k]["fits"]
            extra = dict(lambdas=json.dumps(Counter(f["lambda"] for f in fits)), epochs=json.dumps([f["epochs"] for f in fits]))
            for fam in ("ownership", "mapping", "both"):
                fm = np.ones(len(w), bool) if fam == "both" else fams == fam
                a, lo, hi = boot_mean((pred[fm] == w.y[fm]).astype(float), nb, seed)
                rows.append(dict(target="T3", dataset=fam, layer=L, train="cv(own+map)", test=fam, model=k, set="natural", metric="accuracy_binding",
                                 n=int(fm.sum()), estimate=a, ci_lo=lo, ci_hi=hi, **extra))
                ok = fm & ~np.isnan(y_t1)
                a, lo, hi = boot_mean((pred[ok] == y_t1[ok]).astype(float), nb, seed)
                rows.append(dict(target="T1", dataset=fam, layer=L, train="cv(own+map)", test=fam, model=k, set="natural", metric="accuracy_actual_answer",
                                 n=int(ok.sum()), estimate=a, ci_lo=lo, ci_hi=hi, **extra))
        # transfer: train one family (all its items), test the other
        for src, dst in (("ownership", "mapping"), ("mapping", "ownership")):
            si, di = np.where(fams == src)[0], np.where(fams == dst)[0]
            w_tr, w_te = w.subset(si), w.subset(di)
            res = run_transfer(w_tr, w_te, list(w_tr.meta["pair_id"]), M.MODELS, device, args, f"transfer_{src}_to_{dst}_L{L}", weights_dir / "transfer")
            for k in M.MODELS:
                f0 = res[k]["fits"][0]
                extra = dict(lambdas=json.dumps({f0["lambda"]: 1}), epochs=json.dumps([f0["epochs"]]))
                for variant, lg in (("", res[k]["logits"]), ("(restd)", res[k]["logits_restd"])):
                    pred = lg.argmax(1)
                    a, lo, hi = boot_mean((pred == w_te.y).astype(float), nb, seed)
                    rows.append(dict(target="T3", dataset=dst, layer=L, train=src + variant, test=dst, model=k, set="natural", metric="accuracy_binding", n=len(w_te),
                                     estimate=a, ci_lo=lo, ci_hi=hi, **extra))
                    yt = np.array([np.nan if v is None else float(v) for v in w_te.meta["y_t1"]])
                    ok = ~np.isnan(yt)
                    a, lo, hi = boot_mean((pred[ok] == yt[ok]).astype(float), nb, seed)
                    rows.append(dict(target="T1", dataset=dst, layer=L, train=src + variant, test=dst, model=k, set="natural", metric="accuracy_actual_answer", n=int(ok.sum()),
                                     estimate=a, ci_lo=lo, ci_hi=hi, **extra))
    timing["t1t3_own_map_s"] = time.time() - t
    log(f"T1/T3 ownership+mapping done in {timing['t1t3_own_map_s']:.0f}s")

    # ================================================================================== T2 (last token only; window version not local)
    t = time.time()
    t2_kinds = ("last_linear", "attn_mlp")  # with T = 1 the attention pooling is the identity: (d) = MLP on the last token
    for name, sites in (("S2+S3", ("S2", "S3")),):  # the Z1 E1 set; S1 (last-token edits, flips only at alpha 4) left out for time
        w2 = D.load_t2(sites)
        fp = {p: fam_of_pair.get(p, f) for p, f in zip(w2.meta["pair_id"], w2.meta["family"])}
        pf = F.assign_folds(set(w2.meta["pair_id"]), fp, args.folds, seed)  # same recipe and seed -> same folds as own/map
        fold_t2 = np.array([pf[p] for p in w2.meta["pair_id"]])
        fold_record[f"t2_{name}"] = {"unit": "pair (stratified by family)", "fold_of_pair": pf, "n_entries": len(w2), "n_flips": int(w2.y.sum())}
        res = run_cv(w2, fold_t2, list(w2.meta["pair_id"]), t2_kinds, device, args, f"t2_{name.replace('+', '')}", weights_dir / "t2_last_token")
        dose = dose_only_oof(w2.meta["cell"], w2.y, fold_t2)
        pairs = w2.meta["pair_id"]
        for k in t2_kinds:
            lg = res[k]["logits"]
            p_flip = 1.0 / (1.0 + np.exp(-(lg[:, 1] - lg[:, 0])))
            st = pair_boot_auroc(p_flip, dose, w2.y, pairs, nb, seed)
            fits = res[k]["fits"]
            rows.append(dict(target="T2", dataset=name, layer=42, train="cv", test="planted", model=k + ("(last-token MLP)" if k == "attn_mlp" else ""), set="planted",
                             metric="auroc_flip", n=len(w2), estimate=st["auroc"], ci_lo=st["auroc_lo"], ci_hi=st["auroc_hi"], ref_best_last="dose-only(site,alpha)",
                             delta=st["delta"], delta_lo=st["delta_lo"], delta_hi=st["delta_hi"], lambdas=json.dumps(Counter(f["lambda"] for f in fits)),
                             epochs=json.dumps([f["epochs"] for f in fits]), n_pairs=st["n_pairs"]))
            summary[f"t2_{name}_{k}"] = st
        rows.append(dict(target="T2", dataset=name, layer=42, train="cv", test="planted", model="dose-only(site,alpha)", set="planted", metric="auroc_flip",
                         n=len(w2), estimate=auroc(dose, w2.y), ci_lo=float("nan"), ci_hi=float("nan")))
        rows.append(dict(target="T2", dataset=name, layer=42, train="-", test="planted", model="window(c)/(d)", set="planted", metric="auroc_flip", n=len(w2),
                         estimate=float("nan"), ci_lo=float("nan"), ci_hi=float("nan"), ref_best_last="NOT LOCAL: all-position edited states are on the pod"))
    timing["t2_s"] = time.time() - t
    log(f"T2 done in {timing['t2_s']:.0f}s")

    # ================================================================================== outputs
    timing["total_s"] = time.time() - T0
    write_csv(out_dir / "v5.csv", rows)
    (weights_dir).mkdir(parents=True, exist_ok=True)
    with open(weights_dir / "folds.json", "w", encoding="utf-8") as f:
        json.dump(fold_record, f, indent=1)
    verdict = write_md(out_dir / "v5.md", rows, summary, timing, args, device, fold_record)
    make_fig(out_dir / "fig_v5.png", rows)
    log(f"wrote {out_dir / 'v5.csv'}, {out_dir / 'v5.md'}, {out_dir / 'fig_v5.png'}; weights under {weights_dir}; total {timing['total_s']:.0f}s")
    return {"rows": rows, "summary": summary, "timing": timing, "verdict": verdict}


COLUMNS = ["target", "dataset", "layer", "train", "test", "model", "set", "metric", "n", "estimate", "ci_lo", "ci_hi", "ref_best_last", "delta", "delta_lo",
           "delta_hi", "n_pairs", "lambdas", "epochs"]


def write_csv(path: Path, rows: Sequence[Mapping]) -> None:
    import csv

    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        wr.writeheader()
        for r in rows:
            wr.writerow({c: ("" if (isinstance(r.get(c), float) and np.isnan(r.get(c))) else r.get(c, "")) for c in COLUMNS})


def _f(v, pct=True) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    return f"{100 * v:.1f}" if pct else f"{v:.3f}"


def _ci(r: Mapping, pct=True) -> str:
    return f"{_f(r['estimate'], pct)} [{_f(r['ci_lo'], pct)}, {_f(r['ci_hi'], pct)}]"


def _delta(r: Mapping, pct=True) -> str:
    if "delta" not in r or r.get("delta") is None or np.isnan(r["delta"]):
        return "–"
    sign = "+" if r["delta"] >= 0 else ""
    if pct:
        return f"{sign}{100 * r['delta']:.1f} [{100 * r['delta_lo']:+.1f}, {100 * r['delta_hi']:+.1f}]"
    return f"{sign}{r['delta']:.3f} [{r['delta_lo']:+.3f}, {r['delta_hi']:+.3f}]"


def success_rows(rows: Sequence[Mapping]) -> Tuple[List[dict], List[dict]]:
    t1 = [r for r in rows if r["target"] == "T1" and r["dataset"] == "errors" and r["set"] == "error" and r["metric"] == "p_favours_actual"
          and r["model"] in M.WINDOW_MODELS]
    t2 = [r for r in rows if r["target"] == "T2" and r["metric"] == "auroc_flip" and r["model"].startswith("attn")]
    return t1, t2


def write_md(path: Path, rows: Sequence[Mapping], summary: Mapping, timing: Mapping, args, device, fold_record) -> str:
    L = []
    L.append("# V5 — behaviour-trained window reader (PREREG_WV.md §V5; Mac, local caches only)\n")
    L.append(f"Run {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}; device {device}; torch {torch.__version__}; {args.folds} outer folds, {args.inner} inner folds, "
             f"L2 grid {M.LAMBDAS}, early stopping (patience {args.patience}, max {args.max_epochs} epochs, Adam lr {args.lr:g}); item bootstrap {args.n_boot} "
             f"(T2: pair bootstrap); seed {args.seed}. Wall: T1 errors {timing['t1_errors_s']:.0f}s, T1/T3 own+map {timing['t1t3_own_map_s']:.0f}s, "
             f"T2 {timing['t2_s']:.0f}s, total {timing['total_s'] / 60:.1f} min (budget 30 min).\n")
    L.append("Models: (a) last-token linear, (b) mean-pooled linear, (c) attention-pooled linear (one learned query), (d) 2-layer MLP (hidden 256) on the "
             "attention-pooled vector. Standardised features; loss = CE + λ‖W‖²; λ by inner CV (held-out accuracy), refit for the median best epoch.\n")
    # ---- T1 errors
    L.append("## T1 — the model's actual answer on the error set (8-way symbol head; windows = last 12 positions)\n")
    L.append("P(favours actual) = held-out logit[actual] − logit[correct] > 0 (ERROR: candidates [actual, correct]; ERROR control: the model is right, "
             "candidates [correct, wrong symbol]). Readers: raw favours-actual flags from x3_lo.jsonl (layer 42, last token) and y1_lo.jsonl (site 48:0). "
             "Δ = window/other model − the best last-token reader on ERROR (max point estimate over (a) and the three readers), paired item bootstrap.\n")
    for Lr in ERROR_LAYERS:
        best = summary[f"errors_L{Lr}"]
        L.append(f"### Layer {Lr} (best last-token reader on ERROR: {READER_LABEL.get(best['best_last_token'], best['best_last_token'])}, {100 * best['best_rate']:.1f}%)\n")
        L.append("| model | ERROR P(favours actual) [95% CI] | Δ vs best last-token [CI] | ERROR 8-way acc | ERROR-control P(favours actual) | λ counts | epochs |")
        L.append("|---|---|---|---|---|---|---|")
        sub = [r for r in rows if r["dataset"] == "errors" and r["layer"] == Lr]
        for rd in READERS:
            e = next((r for r in sub if r["model"] == f"reader:{rd}" and r["set"] == "error"), None)
            c = next((r for r in sub if r["model"] == f"reader:{rd}" and r["set"] == "error_control"), None)
            if e:
                L.append(f"| reader {READER_LABEL[rd]} (last token) | {_ci(e)} (n={e['n']}) | – | – | {_ci(c) if c else '–'} | – | – |")
        mj = next((r for r in sub if r["model"] == "majority_symbol" and r["set"] == "error"), None)
        mjc = next((r for r in sub if r["model"] == "majority_symbol" and r["set"] == "error_control"), None)
        if mj:
            L.append(f"| majority-symbol constant | {_f(mj['estimate'])} | – | – | {_f(mjc['estimate']) if mjc else '–'} | – | – |")
        for k in M.MODELS:
            e = next(r for r in sub if r["model"] == k and r["set"] == "error" and r["metric"] == "p_favours_actual")
            a = next(r for r in sub if r["model"] == k and r["set"] == "error" and r["metric"] == "accuracy_8way")
            c = next(r for r in sub if r["model"] == k and r["set"] == "error_control" and r["metric"] == "p_favours_actual")
            L.append(f"| {M.MODEL_LABEL[k]} | {_ci(e)} (n={e['n']}) | {_delta(e)} | {_ci(a)} | {_ci(c)} | {e['lambdas']} | {e['epochs']} |")
        L.append("")
    # ---- T1/T3 own map
    L.append("## T1 / T3 — ownership and mapping, natural states (binary: answer is the first-mentioned candidate; window = full prompt)\n")
    om = summary["own_map"]
    L.append(f"{om['n_items']} states (64 ownership + 64 mapping, 32 pairs each), {args.folds} pair-family folds (pairs → folds by seed {args.seed}, stratified by family; "
             f"one CV over both families, metrics per family). T3 = the prompt fact (binding); T1 = the model's parsed natural answer: {om['n_t1_unparsed']} states did "
             f"not parse and are excluded from T1; on the parsed states T1 and T3 labels are {'identical' if om['t1_t3_identical_on_parsed'] else 'NOT identical'} "
             f"(the model is correct on every parsed natural state), so T1 ≡ T3 here and the T3 control cannot separate 'reads the answer' from 'reads the prompt'.\n")
    L.append("| layer | train → test | model | T3 ownership acc | T3 mapping acc | T3 both | T1 ownership | T1 mapping |")
    L.append("|---|---|---|---|---|---|---|---|")
    for Lr in FULL_LAYERS:
        for tr, label in (("cv(own+map)", f"{args.folds}-fold CV"), ("ownership", "ownership → mapping"), ("ownership(restd)", "ownership → mapping, test-family standardisation"),
                          ("mapping", "mapping → ownership"), ("mapping(restd)", "mapping → ownership, test-family standardisation")):
            for k in M.MODELS:
                g = lambda tgt, ds, met: next((r for r in rows if r["target"] == tgt and r["dataset"] == ds and r["layer"] == Lr and r["train"] == tr and r["model"] == k and r["metric"] == met), None)
                t3o, t3m, t3b = g("T3", "ownership", "accuracy_binding"), g("T3", "mapping", "accuracy_binding"), g("T3", "both", "accuracy_binding")
                t1o, t1m = g("T1", "ownership", "accuracy_actual_answer"), g("T1", "mapping", "accuracy_actual_answer")
                cell = lambda r: _ci(r) if r else "–"
                L.append(f"| {Lr} | {label} | {M.MODEL_LABEL[k]} | {cell(t3o)} | {cell(t3m)} | {cell(t3b)} | {cell(t1o)} | {cell(t1m)} |")
    L.append("")
    # ---- T2
    L.append("## T2 — does the edit flip the answer? (LAST TOKEN ONLY: the all-position edited states are on the pod, not local)\n")
    L.append(f"Features: the block-42 last-token read-back after the edit (cache/g_agreement/x/x2_readvecs); label flipped_to_other (x2_behaviour.jsonl); "
             f"planted entries only; {args.folds} pair-family folds; dose-only reference = training-fold flip rate of the entry's (site, α) cell; ΔAUROC paired pair bootstrap. "
             "The window readers (c)/(d) cannot be trained for T2 locally; (d) on a single vector is an MLP on the last token and is reported as such. "
             "Z1 (S2+S3, dose-only = logistic flip ~ α): Oracle 0.907 vs dose 0.946, J-lens 0.904 vs 0.947, NLA 0.804 vs 0.947 — none beat dose.\n")
    L.append("| entries | model | AUROC [95% CI] | dose-only AUROC | ΔAUROC over dose [CI] | λ counts | epochs |")
    L.append("|---|---|---|---|---|---|---|")
    for r in rows:
        if r["target"] == "T2" and r["metric"] == "auroc_flip":
            if r["model"].startswith("dose") or r["model"].startswith("window"):
                continue
            dose = next(x for x in rows if x["target"] == "T2" and x["dataset"] == r["dataset"] and x["model"].startswith("dose"))
            L.append(f"| {r['dataset']} planted (n={r['n']}, {r['n_pairs']} pairs) | {r['model']} | {_ci(r, False)} | {_f(dose['estimate'], False)} | {_delta(r, False)} | {r['lambdas']} | {r['epochs']} |")
    L.append("| any | window (c)/(d) | not local | | | | |")
    L.append("")
    # ---- verdict
    t1, t2 = success_rows(rows)
    hits_t1 = [r for r in t1 if r["delta"] >= WIN_SUCCESS_PP and r["delta_lo"] > 0]
    hits_t2 = [r for r in t2 if r["delta"] >= WIN_SUCCESS_AUROC and r["delta_lo"] > 0]
    L.append("## Verdict against the pre-registered success rule\n")
    L.append("Success = a window reader ((c) or (d)) beats the best last-token reader on T1 ERROR by ≥ 10 points with CI excluding 0, or beats dose-only on T2 by ΔAUROC ≥ 0.05 with CI excluding 0. "
             "Control-arm reading (CLAUDE.md rule 2, Y1 E10 convention): a favours-actual rate is only evidence of reading the answer if its CI lower bound exceeds the "
             "majority-symbol constant (the class-prior scorer, which also scores LOW on ERROR-control where the frequent symbol is the wrong candidate).\n")
    for r in t1:
        mj = next(x for x in rows if x["dataset"] == "errors" and x["layer"] == r["layer"] and x["model"] == "majority_symbol" and x["set"] == "error")
        above_prior = r["ci_lo"] > mj["estimate"]
        L.append(f"- T1 ERROR L{r['layer']} {M.MODEL_LABEL[r['model']]}: {_f(r['estimate'])}% vs best last-token {READER_LABEL.get(r['ref_best_last'], r['ref_best_last'])}: Δ {_delta(r)} pp → "
                 f"{'PASS' if (r['delta'] >= WIN_SUCCESS_PP and r['delta_lo'] > 0) else 'no'}; CI lower bound {'above' if above_prior else 'NOT above'} the majority-symbol "
                 f"constant ({_f(mj['estimate'])}%) {'' if above_prior else '— consistent with a class-prior scorer, see the ERROR-control column'}")
    for r in t2:
        L.append(f"- T2 {r['dataset']} {r['model']}: ΔAUROC {_delta(r, False)} → {'PASS' if (r['delta'] >= WIN_SUCCESS_AUROC and r['delta_lo'] > 0) else 'no'} "
                 f"(last-token only; not the pre-registered window reader)")
    if hits_t1:
        verdict = "SUCCESS on T1 errors: a window reader beats the best last-token reader by ≥ 10 points with CI excluding 0."
    elif hits_t2:
        verdict = "T2 criterion met only by a last-token model (the window version of T2 is not local); the pre-registered window-reader success is NOT established."
    else:
        verdict = "NOT MET: no window reader beats the best last-token reader on T1 errors by ≥ 10 points with CI excluding 0; the T2 window criterion could not be evaluated locally."
    L.append(f"\n**Verdict: {verdict}**\n")
    L.append("T3 (control): see the ownership/mapping table — on natural states T3 and T1 coincide, so a reader that decodes the binding necessarily 'reads the answer'; "
             "the T3 control is uninformative on this data (it would need states where the model's answer differs from the prompt fact).\n")
    # ---- deviations / limitations
    L.append("## Deviations and limitations\n")
    fr = fold_record["errors"]
    L.append(f"- **Error folds (deviation, dated {time.strftime('%Y-%m-%d')}):** the pre-registration holds out whole templates, but every error/control item has the single "
             f"template_id {fr['template_ids']}, so a template fold is degenerate. Instead whole (hops k, start symbol) groups are held out: {fr['n_groups']} groups → "
             f"{args.folds} folds (two groups each, one k = 3 and one k = 4). The original rule is kept above; this is the closest structural hold-out available.")
    L.append("- **T2 entries:** S2+S3 planted only (Z1's E1 set, 1,024 entries); the S1 last-token edits (flips only at α = 4) were left out for time.")
    L.append("- **T2 window version not local:** only the block-42 last-token read-back vectors of the X2 edits are on the Mac (4,736 entries); the all-position edited "
             "states needed for an attention-pooled T2 reader are on the pod volume. T2 here is last-token only, which cannot satisfy the window-reader clause of the success rule.")
    L.append("- **T3 is not a separable control on natural states** (the model answers every parsed natural ownership/mapping state correctly), see above. A real T3 "
             "control needs edited or error states for these families — the Z4/X2 edited all-position states, also on the pod.")
    L.append("- **Inner CV:** 2 inner folds per outer fold (time budget); λ ties go to the larger λ; the refit uses the median inner best epoch, so the final model has no "
             "early-stopping validation of its own.")
    L.append("- **Ownership + mapping share one CV** (pairs stratified by family), so each fold's training set contains both families; per-family numbers are the "
             "out-of-fold predictions restricted to that family. Transfer rows train on one family only; 'test-family standardisation' re-centres/re-scales the test "
              "family's features with its own (label-free) statistics before applying the trained weights, because the two families' activation means differ "
              "(raw transfer collapses to a constant prediction, 50%).")
    L.append("- **Reader columns are raw favours-actual flags** at the last token (x3_lo layer 42; y1_lo site 48:0), not the bias-corrected R3 rates; the comparison is "
             "point-estimate max over (a) and the readers, as the brief specifies.")
    L.append("- 8-way class imbalance on the error set (symbols G/A frequent, E rare); the majority-symbol constant is shown as the floor.")
    L.append("- Compute: 0 forward passes of the 27B model; all fits on cached activations; weights (fp16 state dicts + fold assignments) under cache/g_agreement/v/window_reader/.")
    L.append("")
    L.append(f"Command: `OMP_NUM_THREADS=4 PYTHONPATH=. .venv/bin/python projects/g_agreement/v5_window/run.py {' '.join(sys.argv[1:])}`")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return verdict


def rows_from_csv(path: Path) -> List[dict]:
    """v5.csv back into row dicts (numeric columns parsed; blanks -> nan) for --fig-only."""
    import csv

    num = {"layer": int, "n": int, "n_pairs": int}
    fl = ("estimate", "ci_lo", "ci_hi", "delta", "delta_lo", "delta_hi")
    out = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = dict(r)
            for c, t in num.items():
                d[c] = t(float(r[c])) if r.get(c) not in (None, "") else None
            for c in fl:
                d[c] = float(r[c]) if r.get(c) not in (None, "") else float("nan")
            out.append(d)
    return out


def _bar(ax, x, r, color, label=None):
    ax.bar(x, r["estimate"], color=color, width=0.8, label=label)
    if not (np.isnan(r["ci_lo"]) or np.isnan(r["ci_hi"])):
        ax.errorbar(x, r["estimate"], yerr=[[r["estimate"] - r["ci_lo"]], [r["ci_hi"] - r["estimate"]]], color="k", capsize=3, lw=1)


def make_fig(path: Path, rows: Sequence[Mapping]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"last_linear": "#9aa5b1", "mean_linear": "#6c8ebf", "attn_linear": "#2a78d6", "attn_mlp": "#1b4f9c"}
    styles = ["--", ":", "-."]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.6), gridspec_kw={"width_ratios": [1.0, 1.5, 0.9]})
    # ---- panel 1: T1 errors
    ax = axes[0]
    for li, Lr in enumerate(ERROR_LAYERS):
        for mi, k in enumerate(M.MODELS):
            r = next(x for x in rows if x["dataset"] == "errors" and x["layer"] == Lr and x["model"] == k and x["set"] == "error" and x["metric"] == "p_favours_actual")
            _bar(ax, li * 5 + mi, r, colors[k], M.MODEL_LABEL[k] if li == 0 else None)
        for ri, rd in enumerate(READERS):
            r = next((x for x in rows if x["dataset"] == "errors" and x["layer"] == Lr and x["model"] == f"reader:{rd}" and x["set"] == "error"), None)
            if r:
                ax.plot([li * 5 - 0.5, li * 5 + 3.5], [r["estimate"]] * 2, ls=styles[ri], color="#c0392b", lw=1.3, label=f"reader {READER_LABEL[rd]} (last token)" if li == 0 else None)
        mj = next(x for x in rows if x["dataset"] == "errors" and x["layer"] == Lr and x["model"] == "majority_symbol" and x["set"] == "error")
        ax.plot([li * 5 - 0.5, li * 5 + 3.5], [mj["estimate"]] * 2, color="#333", lw=1.0, ls=(0, (1, 1)), label="majority-symbol constant (class prior)" if li == 0 else None)
    ax.set_xticks([1.5, 6.5])
    ax.set_xticklabels([f"layer {Lr}" for Lr in ERROR_LAYERS])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("P(favours model's actual answer), ERROR (n=297)")
    ax.set_title("T1 errors (held-out, (k, start)-group folds)", fontsize=10)
    h1, l1 = ax.get_legend_handles_labels()
    # ---- panel 2: T3/T1 own+map
    ax = axes[1]
    cols = [(Lr, tr) for Lr in FULL_LAYERS for tr in ("cv(own+map)", "ownership", "ownership(restd)", "mapping", "mapping(restd)")]
    for ci, (Lr, tr) in enumerate(cols):
        ds = "both" if tr == "cv(own+map)" else ("mapping" if tr.startswith("ownership") else "ownership")
        for mi, k in enumerate(M.MODELS):
            r = next((x for x in rows if x["target"] == "T3" and x["dataset"] == ds and x["layer"] == Lr and x["train"] == tr and x["model"] == k), None)
            if r is not None:
                _bar(ax, ci * 5 + mi, r, colors[k])
    ax.axhline(0.5, color="#333", lw=1.0, ls=(0, (1, 1)))
    ax.set_xticks([ci * 5 + 1.5 for ci in range(len(cols))])
    lab = {"cv(own+map)": "CV both", "ownership": "own→map", "ownership(restd)": "own→map\n(re-std)", "mapping": "map→own", "mapping(restd)": "map→own\n(re-std)"}
    ax.set_xticklabels([f"L{Lr}\n{lab[tr]}" for Lr, tr in cols], fontsize=7.5)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("accuracy: binding = model's answer (T3 ≡ T1)")
    ax.set_title("T1/T3 ownership + mapping (natural states, full-prompt window)", fontsize=10)
    # ---- panel 3: T2
    ax = axes[2]
    t2 = [x for x in rows if x["target"] == "T2" and x["metric"] == "auroc_flip" and not x["model"].startswith("window")]
    short = lambda m: ("(a) last-token\nlinear" if m.startswith("last") else "(d) last-token\nMLP" if m.startswith("attn") else
                       "T1 probe (a)\nanswer score\n[Z1 protocol]" if m.startswith("T1") else "dose-only\n(site, α)")
    ticks, tl = [], []
    for i, r in enumerate(t2):
        _bar(ax, i, r, "#777" if r["model"].startswith("dose") else "#9aa5b1" if r["model"].startswith("last") else "#e3a21a" if r["model"].startswith("T1") else "#1b4f9c")
        ticks.append(i)
        tl.append(short(r["model"]))
    for ri, (name, (ra, _)) in enumerate(Z1_T2_REFERENCE.items()):
        ax.axhline(ra, color="#c0392b", ls=styles[ri], lw=1.2, label=f"Z1 {name} (S2+S3, last token)")
    ax.axhline(0.5, color="#333", lw=1.0, ls=(0, (1, 1)))
    ax.set_xticks(ticks)
    ax.set_xticklabels(tl, fontsize=7.5)
    ax.set_ylim(0.4, 1.0)
    ax.set_ylabel("held-out AUROC, edit flips the answer")
    ax.set_title(f"T2 flip, {t2[0]['dataset'] if t2 else ''} planted (last token only;\nwindow version not local)", fontsize=10)
    ax.legend(fontsize=7, loc="upper left")
    fig.suptitle("V5 window reader — bars: held-out estimate with 95% bootstrap CI (item; T2 pair); red lines: existing readers", fontsize=11)
    fig.legend(h1, l1, loc="lower center", ncol=4, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
