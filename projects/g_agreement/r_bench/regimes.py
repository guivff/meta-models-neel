"""R1b — the SAE paper's three regimes on existing rows, CPU only (BRIEF_R Deviations, WS3, pre-registered 2026-10-19):
label noise (BD-6: 10 / 25 / 40% of pool labels flipped), class imbalance (training positive fraction π) and covariate
shift (train on chat states, test on raw). Arms: probe-only vs the R1 quiver (probe, zero-shot readers, reader + probe
stacks; arrow chosen on validation from the regime's training labels). Test labels are always clean. Cached per
(regime, fact) under ``<root>/.ws3_cache/r1b``.

    python -m projects.g_agreement.r_bench.regimes --n-jobs 12          # → results/g_agreement/r/r1b_quiver.csv, r1b_summary.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys

import numpy as np
import pandas as pd

from projects.g_agreement.r_bench import analyze as A

NS = A.NS
NS_SHORT = (16, 32, 128, 512)
SEEDS = A.SEEDS
NOISE = (0.10, 0.25, 0.40)
PI = (0.05, 0.10, 0.25, 0.50)


def _seed(*parts) -> int:
    """A process-independent seed (Python's hash() of str is salted per process)."""
    return int(hashlib.md5(repr(parts).encode()).hexdigest()[:8], 16)


def _draw_pi(pool_idx: np.ndarray, y: np.ndarray, n: int, pi: float, rng: np.random.Generator) -> np.ndarray:
    """n training items with positive fraction π (at least one positive and one negative)."""
    n_pos = int(min(max(1, round(pi * n)), n - 1))
    pos, neg = pool_idx[y[pool_idx] == 1], pool_idx[y[pool_idx] == 0]
    if len(pos) < n_pos or len(neg) < n - n_pos:
        return np.array([], int)
    return np.r_[rng.choice(pos, n_pos, replace=False), rng.choice(neg, n - n_pos, replace=False)]


def _reader_scores(lo: pd.DataFrame, ds: str, idx: list[str], render: str) -> dict[str, np.ndarray]:
    pos_of = {iid: i for i, iid in enumerate(idx)}
    out = {}
    sub = lo[(lo.dataset == ds) & (lo.render == render) & (lo.condition == "natural")]
    for rd, g in sub.groupby("reader"):
        g = g[g.layer == A.PRIMARY_LAYER.get(rd, 42)]
        if g.empty:
            continue
        s = np.full(len(idx), np.nan)
        for iid, sc in zip(g.item_id, g.score):
            if iid in pos_of:
                s[pos_of[iid]] = sc
        out[rd] = s
    return out


def _quiver_cell(Xtr, ytr, Xte, yte, tr_scores: dict, te_scores: dict, seed: int) -> dict[str, float]:
    """One (fact, regime, n, seed) cell: probe-only test AUROC and the quiver's chosen arrow (R1's logic, analyze._r1_fit)."""
    from sklearn.model_selection import cross_val_predict

    clf, Cv, val = A.probe_fit_select(Xtr, ytr, seed)
    probe_test = A.auroc(yte, clf.decision_function(Xte))
    arrows = {"probe": (val, probe_test)}
    for rd in tr_scores:
        s_tr, s_te = tr_scores[rd], te_scores.get(rd)
        if s_te is None:
            continue
        ok = np.isfinite(s_tr)
        v = A.auroc(ytr[ok], s_tr[ok]) if ok.sum() >= 2 and len(set(ytr[ok])) == 2 else np.nan
        te_ok = np.isfinite(s_te)
        t = A.auroc(yte[te_ok], s_te[te_ok]) if te_ok.sum() >= 10 else np.nan
        arrows[rd] = (v, t)
        if ok.sum() >= 8 and np.isfinite(v) and np.bincount(ytr[ok], minlength=2).min() >= 2:
            try:
                dec = cross_val_predict(A._fit_logreg(Xtr[ok], ytr[ok], Cv, seed), Xtr[ok], ytr[ok],
                                        cv=min(4, int(np.bincount(ytr[ok]).min())), method="decision_function")
                st, _, sv = A.probe_fit_select(np.c_[dec, s_tr[ok]], ytr[ok], seed, grid=(1.0,))
                F_te = np.c_[clf.decision_function(Xte), s_te]
                m = np.isfinite(F_te).all(1)
                arrows[f"stack:{rd}"] = (sv, A.auroc(yte[m], st.decision_function(F_te[m])))
            except Exception:
                pass
    cand = {k: v for k, v in arrows.items() if np.isfinite(v[0]) and np.isfinite(v[1])}
    chosen = max(cand, key=lambda k: cand[k][0]) if cand else "probe"
    return {"probe_test": probe_test, "chosen": chosen, "chosen_test": arrows[chosen][1], "delta": arrows[chosen][1] - probe_test}


def r1b_fact(P: A.Paths, items: pd.DataFrame, lo: pd.DataFrame, ds: str) -> pd.DataFrame:
    """All three regimes for one fact (cached)."""
    sf_c, sf_r = (P.cache / "states" / ds / f"{r}_L{A.L_READ}.npy" for r in ("chat", "raw"))
    if not sf_c.exists():
        return pd.DataFrame()
    sub = lo[lo.dataset == ds]
    sig = hashlib.sha256(json.dumps([sf_c.stat().st_size, sf_c.stat().st_mtime_ns, sf_r.stat().st_mtime_ns if sf_r.exists() else 0,
                                     pd.util.hash_pandas_object(sub[["reader", "layer", "render", "item_id", "score"]], index=False).sum().item() if len(sub) else 0,
                                     "v1"]).encode()).hexdigest()[:16]
    cdir = P.root / ".ws3_cache" / "r1b"
    cf = cdir / f"{ds}__{sig}.pkl"
    if cf.exists():
        return pickle.loads(cf.read_bytes())
    Xc, idx = A.load_states(P, ds, "chat", A.L_READ)
    it = items[items.dataset == ds].set_index("item_id").loc[idx]
    y, split = it.label.values.astype(int), it.split.values
    te, pool = np.where(split == "test")[0], np.where(split == "pool")[0]
    rc, rr = _reader_scores(lo, ds, idx, "chat"), _reader_scores(lo, ds, idx, "raw")
    eval_pool = np.array([i for i in pool if any(np.isfinite(s[i]) for s in rc.values())]) if rc else pool
    rows = []

    def cell(regime, param, n, seed, tr, ytr_full, Xte, te_scores):
        if len(tr) < 2 or len(set(ytr_full[tr])) < 2:
            return
        r = _quiver_cell(Xc[tr], ytr_full[tr], Xte, y[te], {k: v[tr] for k, v in rc.items()}, te_scores, seed)
        rows.append({"dataset": ds, "regime": regime, "param": param, "n_req": n, "seed": seed, **r})

    te_chat = {k: v[te] for k, v in rc.items()}
    for seed in SEEDS:
        for rate in NOISE:  # (a) label noise: flip pool labels before the draw (the practitioner sees noisy labels)
            rng = np.random.default_rng(_seed(ds, "noise", rate, seed))
            yn = y.copy()
            flip = pool[rng.random(len(pool)) < rate]
            yn[flip] = 1 - yn[flip]
            for n in NS:
                draw_from = eval_pool if (n <= len(eval_pool) and len(eval_pool) >= 4) else pool
                cell("noise", rate, n, seed, A.balanced_draw(draw_from, yn, n, rng), yn, Xc[te], te_chat)
        for pi in PI:  # (b) class imbalance in training
            rng = np.random.default_rng(_seed(ds, "imb", pi, seed))
            for n in NS_SHORT:
                draw_from = eval_pool if (n <= len(eval_pool) and len(eval_pool) >= 4) else pool
                cell("imbalance", pi, n, seed, _draw_pi(draw_from, y, n, pi, rng), y, Xc[te], te_chat)
        if sf_r.exists():  # (c) covariate shift: train on chat, test on raw
            Xr, idx_r = A.load_states(P, ds, "raw", A.L_READ)
            assert idx_r == idx, f"{ds}: chat / raw index differ"
            rng = np.random.default_rng(_seed(ds, "shift", seed))
            te_raw = {k: v[te] for k, v in rr.items()}
            for n in NS_SHORT:
                draw_from = eval_pool if (n <= len(eval_pool) and len(eval_pool) >= 4) else pool
                tr = A.balanced_draw(draw_from, y, n, rng)
                cell("shift", "chat→raw", n, seed, tr, y, Xr[te], te_raw)
                cell("shift_ref", "chat→chat", n, seed, tr, y, Xc[te], te_chat)
    df = pd.DataFrame(rows)
    cdir.mkdir(parents=True, exist_ok=True)
    for old in cdir.glob(f"{ds}__*.pkl"):
        old.unlink()
    cf.write_bytes(pickle.dumps(df))
    return df


def main(argv: list[str] | None = None) -> int:
    from joblib import Parallel, delayed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-jobs", type=int, default=8)
    ap.add_argument("--datasets", nargs="*", default=None)
    a = ap.parse_args(argv)
    A.PROVENANCE.update(strict=True, extra_pods=set(), dropped={}, off_bank={})
    P = A.Paths()
    items, _ = A.load_bank(P)
    lo = A.reader_frame(P, items)
    dss = a.datasets or sorted(items.dataset.unique())
    by = {ds: g for ds, g in lo[lo.dataset.isin(dss)].groupby("dataset")}
    res = Parallel(n_jobs=a.n_jobs)(delayed(r1b_fact)(P, items[items.dataset == ds], by.get(ds, lo.iloc[:0]), ds) for ds in dss)
    q = pd.concat([r for r in res if len(r)], ignore_index=True)
    q.to_csv(P.results / "r1b_quiver.csv", index=False)
    print(f"[r1b] {len(q)} cells over {q.dataset.nunique()} facts → {P.results / 'r1b_quiver.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
