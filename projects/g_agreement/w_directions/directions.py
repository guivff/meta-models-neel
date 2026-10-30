"""Phase W Track B — direction decomposition (PREREG_WV.md "Track B"; pure tensor functions, CPU, no model calls).

Conventions (X2/Y2/Z4 frame): for a pair, Δ(pos) = h_B(pos) − h_A(pos) at the edit layer; every stored direction is a
UNIT vector oriented A→B (editing from A toward B adds +‖Δ(pos)‖·d̂, from B toward A subtracts it). For the error family
there is no B state: ``full`` = centroid(target symbol) − h (the centroid swap) plays the role of Δ.

Per family a SHARED direction set is built from the training data, then per pair/position the components of that
pair's own Δ(pos):
  d_cm   class-mean difference (ownership: one shared vector oriented "holder = second-mentioned name", flipped per pair;
         mapping: mean(symbol_B) − mean(symbol_A) at the position from the per-symbol class means of the site vectors;
         errors: cm(t) − cm(a) with cm(s) = mean(actual = s) − mean(rest)); unit.
  d_pw   held-out L2 logistic probe weights on the SAME label (x_friday_r2r4.SpanLogistic, inner-CV C), raw-space
         weights w = coef·Vt / sd, 5 outer folds by pair / item, the fold's probe used for its held-out pairs;
         Gram–Schmidt against d_cm; unit.
  d_J    unit(Q Qᵀ Δ) with Q the top-384 J-space basis (errors: Q Qᵀ of the d_cm-free residual).
  d_res  unit(Δ − P_span{d_cm, d_pw, Q} Δ) (orthogonal to d_cm, d_pw and Q).
Energy fractions of ‖Δ(pos)‖²: frac[d_cm] = (Δ·d_cm)², frac[d_pw] = (Δ·d_pw)² (d_pw ⊥ d_cm), frac[d_J] = ‖QQᵀΔ‖²
(OVERLAPS d_cm/d_pw), frac[span] = ‖P_span Δ‖², frac[d_J_excl] = frac[span] − frac[d_cm] − frac[d_pw] (the J-space energy
not already along d_cm/d_pw), frac[d_res] = ‖res‖²; d_cm + d_pw + d_J_excl + d_res = 1 exactly.
"""

from __future__ import annotations

import zlib
from collections import Counter
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch

DIR_NAMES: Tuple[str, ...] = ("d_cm", "d_pw", "d_J", "d_res")
FRAC_NAMES: Tuple[str, ...] = ("d_cm", "d_pw", "d_J", "d_J_excl", "d_res", "span")
N_FOLDS = 5
SEED = 0
RANDOM_BASE_SEED = 20261011
K_RANDOM = 10
EPS = 1e-9


# ------------------------------------------------------------------ linear algebra helpers
def unit(v: torch.Tensor, dim: int = -1) -> torch.Tensor:
    """v / ‖v‖ along ``dim`` (a zero vector stays zero)."""
    return v / v.norm(dim=dim, keepdim=True).clamp_min(EPS)


def orthogonalise(v: torch.Tensor, basis: Sequence[torch.Tensor]) -> torch.Tensor:
    """Gram–Schmidt: ``v`` [..., d] minus its projections onto each UNIT vector in ``basis`` (each [..., d] or [d]),
    applied sequentially (exact when the basis vectors are mutually orthogonal)."""
    out = v.clone()
    for b in basis:
        out = out - (out * b).sum(-1, keepdim=True) * b
    return out


def project_Q(v: torch.Tensor, Q: torch.Tensor) -> torch.Tensor:
    """v Q Qᵀ for ``v`` [..., d] and an orthonormal ``Q`` [d, r]."""
    return (v @ Q) @ Q.T


def cos(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return (unit(a) * unit(b)).sum(-1)


def decompose(delta: torch.Tensor, d_cm: torch.Tensor, d_pw: torch.Tensor, Q: torch.Tensor, *,
              j_from_cm_free: bool = False) -> Dict[str, Any]:
    """Components of ``delta`` [P, d] along the unit directions ``d_cm``, ``d_pw`` ([P, d], d_pw ⊥ d_cm) and the J-space
    ``Q`` [d, r]. Returns fp32 ``dirs`` {name: [P, d] unit}, ``coef`` {name: [P]} with coef·dir = the component (signed
    for d_cm/d_pw, ≥ 0 for d_J/d_res), ``frac`` {name: [P]} (see module doc) and ``delta_norm`` [P]."""
    delta, d_cm, d_pw, Q = delta.float(), d_cm.float(), d_pw.float(), Q.float()
    if delta.ndim != 2 or d_cm.shape != delta.shape or d_pw.shape != delta.shape:
        raise ValueError(f"shape mismatch: delta {tuple(delta.shape)}, d_cm {tuple(d_cm.shape)}, d_pw {tuple(d_pw.shape)}")
    n2 = (delta ** 2).sum(1).clamp_min(EPS)
    c_cm = (delta * d_cm).sum(1)
    c_pw = (delta * d_pw).sum(1)
    J_full = project_Q(delta, Q)
    J_src = project_Q(delta - c_cm[:, None] * d_cm, Q) if j_from_cm_free else J_full
    # orthonormal completion of Q by the parts of d_cm, d_pw outside Q: span{d_cm, d_pw, Q} = span{Q, e1, e2}
    e1 = unit(d_cm - project_Q(d_cm, Q))
    e2 = unit(orthogonalise(d_pw - project_Q(d_pw, Q), [e1]))
    span = J_full + (delta * e1).sum(1, keepdim=True) * e1 + (delta * e2).sum(1, keepdim=True) * e2
    res = delta - span
    frac = {"d_cm": c_cm ** 2 / n2, "d_pw": c_pw ** 2 / n2, "d_J": (J_full ** 2).sum(1) / n2,
            "span": (span ** 2).sum(1) / n2, "d_res": (res ** 2).sum(1) / n2}
    frac["d_J_excl"] = (frac["span"] - frac["d_cm"] - frac["d_pw"]).clamp_min(0.0)
    dirs = {"d_cm": d_cm.contiguous(), "d_pw": d_pw.contiguous(), "d_J": unit(J_src).contiguous(), "d_res": unit(res).contiguous()}
    coef = {"d_cm": c_cm, "d_pw": c_pw, "d_J": J_src.norm(dim=1), "d_res": res.norm(dim=1)}
    return {"dirs": dirs, "coef": coef, "frac": {k: v.float() for k, v in frac.items()}, "delta_norm": n2.sqrt()}


# ------------------------------------------------------------------ folds, probes, random directions
def make_folds(keys: Sequence[str], n_folds: int = N_FOLDS, seed: int = SEED, strata: Optional[Sequence[Any]] = None) -> Dict[str, int]:
    """{key: fold} over distinct ``keys`` (pairs or items); StratifiedKFold on ``strata`` when every stratum has ≥ n_folds
    members, else KFold; both shuffled with ``seed`` (x_friday_r2r4._outer_folds)."""
    from sklearn.model_selection import KFold, StratifiedKFold

    keys = list(keys)
    if len(set(keys)) != len(keys):
        raise ValueError("fold keys must be distinct")
    k = min(n_folds, len(keys))
    if k < 2:
        return {key: 0 for key in keys}
    if strata is not None and min(Counter(list(strata)).values()) >= k and len(set(strata)) > 1:
        splits = StratifiedKFold(k, shuffle=True, random_state=seed).split(np.zeros(len(keys)), np.asarray(strata))
    else:
        splits = KFold(k, shuffle=True, random_state=seed).split(np.zeros(len(keys)))
    out: Dict[str, int] = {}
    for f, (_, te) in enumerate(splits):
        for i in te:
            out[keys[i]] = f
    return out


def fit_probe(X: np.ndarray, y: Sequence[Any], *, Cs: Sequence[float] = (0.01, 0.1, 1.0), seed: int = SEED):
    """x_friday_r2r4.SpanLogistic (multinomial; binary when 2 classes) on raw features (it standardises internally)."""
    from projects.g_agreement.x_friday_r2r4 import SpanLogistic

    return SpanLogistic(Cs=Cs, seed=seed, multi="multinomial").fit(np.asarray(X, dtype=np.float64), list(y))


def raw_weights(clf) -> Tuple[np.ndarray, List[Any]]:
    """Raw-space read directions of a fitted SpanLogistic: ``W`` [K, d] aligned with ``classes`` (binary: K = 1, the
    direction toward classes[1]). logit = ((x − mu)/sd)·Vtᵀ·coef + b, so w_raw = coef·Vt / sd (Michael's recipe's
    "z-space weights → raw-space read directions")."""
    coef = np.asarray(clf.clf.coef_, dtype=np.float64)
    W = (coef @ clf.Vt) / clf.sd[None, :]
    return W, list(clf.classes_)


def class_weight_rows(W: np.ndarray, classes: Sequence[Any]) -> Dict[Any, np.ndarray]:
    """{class: raw weight row}; a binary probe maps classes[1] → +w and classes[0] → −w (so w[b] − w[a] = 2w; only the
    direction is used downstream)."""
    if W.shape[0] == 1 and len(classes) == 2:
        return {classes[0]: -W[0], classes[1]: W[0]}
    return {c: W[i] for i, c in enumerate(classes)}


def random_seed_for(pair_id: str, base: int = RANDOM_BASE_SEED) -> int:
    """Deterministic per-pair seed for the K matched-norm random directions (stable across machines)."""
    return int((base * 1000003 + zlib.crc32(pair_id.encode("utf-8"))) % (2 ** 31 - 1))


def random_directions(seed: int, n_positions: int, d: int, k: int = K_RANDOM) -> torch.Tensor:
    """fp32 ``[k, P, d]`` isotropic unit directions, one per (k, position), generator seeded ``seed * 1009 + k + 1``
    (the X2Nulls.iso_direction recipe). The pod scales row (k, pos) by this pair's ‖Δ(pos)‖ (matched norm)."""
    out = torch.empty(k, n_positions, d)
    for i in range(k):
        g = torch.Generator().manual_seed(int(seed) * 1009 + i + 1)
        r = torch.randn(n_positions, d, generator=g)
        out[i] = r / r.norm(dim=1, keepdim=True).clamp_min(EPS)
    return out


# ------------------------------------------------------------------ family builders

def build_ownership(pairs: Sequence[Mapping[str, Any]], Q: torch.Tensor, *, n_folds: int = N_FOLDS, seed: int = SEED,
                    Cs: Sequence[float] = (0.01, 0.1, 1.0)) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Ownership family. Each pair: {pair_id, hA [T, d], hB [T, d], positions [P] (post-statement span), yA, yB} with
    y = 1 iff the asked object's holder is the SECOND-mentioned name (= not answer_is_first_mentioned); yA ≠ yB.
    Shared d_cm = unit(mean over pairs and site positions of s_p·(h_B − h_A)) with s_p = +1 if yB = 1 else −1.
    Probe: binary SpanLogistic on all site-position vectors of the training pairs (both versions), label y."""
    Q = Q.float()
    d = int(Q.shape[0])
    pair_ids = [p["pair_id"] for p in pairs]
    sign = {p["pair_id"]: (1.0 if int(p["yB"]) == 1 else -1.0) for p in pairs}
    for p in pairs:
        if int(p["yA"]) == int(p["yB"]) or int(p["yA"]) not in (0, 1) or int(p["yB"]) not in (0, 1):
            raise ValueError(f"{p['pair_id']}: ownership labels must be one 0 and one 1 (got {p['yA']}, {p['yB']})")
    acc, n_vec = torch.zeros(d, dtype=torch.float64), 0
    for p in pairs:
        pos = torch.as_tensor(p["positions"], dtype=torch.long)
        D = (p["hB"].float()[pos] - p["hA"].float()[pos]).double()
        acc += sign[p["pair_id"]] * D.sum(0)
        n_vec += int(len(pos))
    d_cm_shared = unit(acc / max(n_vec, 1)).float()
    fold_of = make_folds(pair_ids, n_folds, seed)
    folds: List[Dict[str, Any]] = []
    d_pw_fold: Dict[int, torch.Tensor] = {}
    for f in sorted(set(fold_of.values())):
        tr = [p for p in pairs if fold_of[p["pair_id"]] != f]
        te = [p for p in pairs if fold_of[p["pair_id"]] == f]
        X = np.concatenate([np.concatenate([p["hA"].float()[p["positions"]].numpy(), p["hB"].float()[p["positions"]].numpy()]) for p in tr])
        y = np.concatenate([[int(p["yA"])] * len(p["positions"]) + [int(p["yB"])] * len(p["positions"]) for p in tr])
        clf = fit_probe(X, y, Cs=Cs, seed=seed)
        W, classes = raw_weights(clf)
        w1 = torch.as_tensor(class_weight_rows(W, classes)[1]).float()
        d_pw_fold[f] = unit(orthogonalise(w1, [d_cm_shared]))
        # held-out: vector-level accuracy and within-pair win (score(h_B) − score(h_A) has the pair's sign) per position
        Xte = np.concatenate([np.concatenate([p["hA"].float()[p["positions"]].numpy(), p["hB"].float()[p["positions"]].numpy()]) for p in te])
        yte = np.concatenate([[int(p["yA"])] * len(p["positions"]) + [int(p["yB"])] * len(p["positions"]) for p in te])
        pred = clf.predict(Xte)
        L = clf.logits(Xte)
        s = L[:, 1] - L[:, 0]
        wins = []
        off = 0
        for p in te:
            n = len(p["positions"])
            wins.extend(((s[off + n: off + 2 * n] - s[off: off + n]) * sign[p["pair_id"]] > 0).tolist())
            off += 2 * n
        folds.append({"fold": f, "train_pairs": [p["pair_id"] for p in tr], "test_pairs": [p["pair_id"] for p in te], "C": float(clf.C),
                      "n_train_vectors": int(len(y)), "n_test_vectors": int(len(yte)), "accuracy": float((pred == yte).mean()),
                      "within_pair_win": float(np.mean(wins)) if wins else float("nan"), "classes": [int(c) for c in classes],
                      "w_raw": w1[None, :].contiguous(), "cos_w_dcm": float(cos(w1, d_cm_shared))})
    per_pair: Dict[str, Dict[str, Any]] = {}
    for p in pairs:
        pid = p["pair_id"]
        pos = torch.as_tensor(p["positions"], dtype=torch.long)
        delta = p["hB"].float()[pos] - p["hA"].float()[pos]
        P = int(len(pos))
        dcm = (sign[pid] * d_cm_shared)[None, :].expand(P, d)
        dpw = (sign[pid] * d_pw_fold[fold_of[pid]])[None, :].expand(P, d)
        rec = decompose(delta, dcm, dpw, Q)
        rec.update(pair_id=pid, positions=pos, delta=delta, fold=int(fold_of[pid]), sign=sign[pid],
                   meta={"yA": int(p["yA"]), "yB": int(p["yB"]), "n_tokens": int(p["hA"].shape[0])})
        per_pair[pid] = rec
    shared = {"family": "ownership", "d_cm": d_cm_shared, "d_cm_orientation": "+ = the asked object's holder is the second-mentioned name",
              "n_vectors_cm": n_vec, "probe": {"folds": folds, "fold_of_pair": fold_of, "label": "y = 1 iff holder is the second-mentioned name",
                                                "Cs": list(Cs), "seed": seed}, "sign_of_pair": sign}
    return shared, per_pair


def build_mapping(pairs: Sequence[Mapping[str, Any]], Q: torch.Tensor, *, n_folds: int = N_FOLDS, seed: int = SEED,
                  Cs: Sequence[float] = (0.01, 0.1, 1.0)) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Mapping family. Each pair: {pair_id, hA, hB, positions [2] (the differing symbol positions), symA [2], symB [2]}.
    Per-symbol class means over all site vectors (both versions, both positions); d_cm(pos) = unit(m[symB] − m[symA]).
    Probe: 8-way SpanLogistic on the site vectors with the symbol as label; d_pw(pos) = unit(orth(w[symB] − w[symA], d_cm))."""
    Q = Q.float()
    d = int(Q.shape[0])
    pair_ids = [p["pair_id"] for p in pairs]
    rows: List[Tuple[str, str, torch.Tensor]] = []  # (pair_id, symbol, vector)
    for p in pairs:
        if len(p["positions"]) != len(p["symA"]) or len(p["positions"]) != len(p["symB"]):
            raise ValueError(f"{p['pair_id']}: positions/symbols length mismatch")
        for j, pos in enumerate(p["positions"]):
            rows.append((p["pair_id"], str(p["symA"][j]), p["hA"].float()[int(pos)]))
            rows.append((p["pair_id"], str(p["symB"][j]), p["hB"].float()[int(pos)]))
    symbols = sorted({s for _, s, _ in rows})
    means = {s: torch.stack([v for _, ss, v in rows if ss == s]).double().mean(0).float() for s in symbols}
    counts = {s: sum(1 for _, ss, _ in rows if ss == s) for s in symbols}
    fold_of = make_folds(pair_ids, n_folds, seed)
    folds: List[Dict[str, Any]] = []
    w_fold: Dict[int, Dict[str, torch.Tensor]] = {}
    for f in sorted(set(fold_of.values())):
        tr = [(pid, s, v) for pid, s, v in rows if fold_of[pid] != f]
        te = [(pid, s, v) for pid, s, v in rows if fold_of[pid] == f]
        ytr = [s for _, s, _ in tr]
        missing = sorted(set(symbols) - set(ytr))
        if missing:
            raise ValueError(f"mapping fold {f}: symbols {missing} absent from the training rows; choose another seed/fold count")
        clf = fit_probe(torch.stack([v for _, _, v in tr]).numpy(), ytr, Cs=Cs, seed=seed)
        W, classes = raw_weights(clf)
        w_fold[f] = {str(c): torch.as_tensor(W[i]).float() for i, c in enumerate(classes)}
        Xte = torch.stack([v for _, _, v in te]).numpy()
        yte = np.asarray([s for _, s, _ in te])
        pred = clf.predict(Xte)
        # pair score: logit[symB] − logit[symA] at the position, > 0 on h_B and < 0 on h_A
        wins = []
        for p in [pp for pp in pairs if fold_of[pp["pair_id"]] == f]:
            for j, pos in enumerate(p["positions"]):
                a, b = str(p["symA"][j]), str(p["symB"][j])
                sA = clf.pair_scores(p["hA"].float()[[int(pos)]].numpy(), [b], [a])[0]
                sB = clf.pair_scores(p["hB"].float()[[int(pos)]].numpy(), [b], [a])[0]
                wins.append(bool(sB - sA > 0))
        folds.append({"fold": f, "train_pairs": sorted({pid for pid, _, _ in tr}), "test_pairs": sorted({pid for pid, _, _ in te}), "C": float(clf.C),
                      "n_train_vectors": int(len(tr)), "n_test_vectors": int(len(te)), "accuracy": float((pred == yte).mean()),
                      "within_pair_win": float(np.mean(wins)) if wins else float("nan"), "classes": [str(c) for c in classes],
                      "w_raw": torch.stack([w_fold[f][str(c)] for c in classes])})
    per_pair: Dict[str, Dict[str, Any]] = {}
    for p in pairs:
        pid = p["pair_id"]
        pos = torch.as_tensor([int(x) for x in p["positions"]], dtype=torch.long)
        delta = p["hB"].float()[pos] - p["hA"].float()[pos]
        dcm = torch.stack([unit(means[str(p["symB"][j])] - means[str(p["symA"][j])]) for j in range(len(pos))])
        wf = w_fold[fold_of[pid]]
        dpw = torch.stack([unit(orthogonalise(wf[str(p["symB"][j])] - wf[str(p["symA"][j])], [dcm[j]])) for j in range(len(pos))])
        rec = decompose(delta, dcm, dpw, Q)
        rec.update(pair_id=pid, positions=pos, delta=delta, fold=int(fold_of[pid]), sign=1.0,
                   meta={"symA": [str(s) for s in p["symA"]], "symB": [str(s) for s in p["symB"]], "n_tokens": int(p["hA"].shape[0])})
        per_pair[pid] = rec
    shared = {"family": "mapping", "symbols": symbols, "class_means": torch.stack([means[s] for s in symbols]), "class_counts": counts,
              "d_cm_rule": "d_cm(pos) = unit(class_mean[symbol_B(pos)] − class_mean[symbol_A(pos)])",
              "probe": {"folds": folds, "fold_of_pair": fold_of, "label": "8-way symbol identity at the site position", "Cs": list(Cs), "seed": seed}}
    return shared, per_pair


def build_errors(X: torch.Tensor, actual: Sequence[str], target: Sequence[str], item_ids: Sequence[str], Q: torch.Tensor, *,
                 n_folds: int = N_FOLDS, seed: int = SEED, Cs: Sequence[float] = (0.01, 0.1, 1.0)) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Error family (layer-48 last-token vectors ``X`` [n, d]; ``actual`` = the model's wrong answer, ``target`` = the correct
    symbol). Per symbol s: centroid m_s = mean(X[actual = s]), cm_s = m_s − mean(X[actual ≠ s]). Per item:
    full = m_target − h (the centroid swap), d_cm = unit(cm_t − cm_a), d_pw = unit(orth(w[t] − w[a], d_cm)) from the 8-way
    actual-symbol probe of the item's held-out fold (StratifiedKFold by actual), d_J from the d_cm-free residual."""
    X, Q = X.float(), Q.float()
    actual, target, item_ids = [str(a) for a in actual], [str(t) for t in target], list(item_ids)
    if not (len(actual) == len(target) == len(item_ids) == X.shape[0]):
        raise ValueError("errors: X, actual, target and item_ids must align")
    if any(a == t for a, t in zip(actual, target)):
        raise ValueError("errors: every item must have actual ≠ target")
    symbols = sorted(set(actual) | set(target))
    a_arr = np.asarray(actual)
    cent: Dict[str, torch.Tensor] = {}
    cm: Dict[str, torch.Tensor] = {}
    for s in symbols:
        m = torch.as_tensor(a_arr == s)
        if int(m.sum()) == 0:
            raise ValueError(f"errors: no item with actual = {s}; the centroid swap toward {s} is undefined")
        cent[s] = X[m].double().mean(0).float()
        cm[s] = (X[m].double().mean(0) - X[~m].double().mean(0)).float()
    fold_of = make_folds(item_ids, n_folds, seed, strata=actual)
    folds: List[Dict[str, Any]] = []
    w_fold: Dict[int, Dict[str, torch.Tensor]] = {}
    for f in sorted(set(fold_of.values())):
        tr = [i for i, iid in enumerate(item_ids) if fold_of[iid] != f]
        te = [i for i, iid in enumerate(item_ids) if fold_of[iid] == f]
        clf = fit_probe(X[tr].numpy(), [actual[i] for i in tr], Cs=Cs, seed=seed)
        W, classes = raw_weights(clf)
        w_fold[f] = {str(c): torch.as_tensor(W[i]).float() for i, c in enumerate(classes)}
        pred = clf.predict(X[te].numpy())
        fav = clf.pair_scores(X[te].numpy(), [actual[i] for i in te], [target[i] for i in te])
        folds.append({"fold": f, "train_items": [item_ids[i] for i in tr], "test_items": [item_ids[i] for i in te], "C": float(clf.C),
                      "n_train_vectors": int(len(tr)), "n_test_vectors": int(len(te)), "accuracy": float((pred == np.asarray([actual[i] for i in te])).mean()),
                      "favours_actual": float(np.nanmean(fav > 0)), "n_unscorable": int(np.isnan(fav).sum()),
                      "classes": [str(c) for c in classes], "w_raw": torch.stack([w_fold[f][str(c)] for c in classes])})
    per_item: Dict[str, Dict[str, Any]] = {}
    for i, iid in enumerate(item_ids):
        a, t = actual[i], target[i]
        full = (cent[t] - X[i])[None, :]
        dcm = unit(cm[t] - cm[a])[None, :]
        wf = w_fold[fold_of[iid]]
        if t not in wf or a not in wf:
            raise ValueError(f"{iid}: probe of fold {fold_of[iid]} lacks class {a if a not in wf else t}")
        dpw = unit(orthogonalise(wf[t] - wf[a], [dcm[0]]))[None, :]
        rec = decompose(full, dcm, dpw, Q, j_from_cm_free=True)
        rec.update(pair_id=iid, positions=torch.as_tensor([-1], dtype=torch.long), delta=full, fold=int(fold_of[iid]), sign=1.0,
                   meta={"actual": a, "target": t, "h_norm": float(X[i].norm())})
        per_item[iid] = rec
    shared = {"family": "errors", "symbols": symbols, "centroids": torch.stack([cent[s] for s in symbols]),
              "d_cm_table": torch.stack([cm[s] for s in symbols]), "class_counts": {s: int((a_arr == s).sum()) for s in symbols},
              "d_cm_rule": "d_cm(item) = unit(cm[target] − cm[actual]), cm[s] = mean(actual = s) − mean(actual ≠ s); full = centroid[target] − h",
              "probe": {"folds": folds, "fold_of_pair": fold_of, "label": "8-way actual symbol (layer-48 last token)", "Cs": list(Cs), "seed": seed}}
    return shared, per_item


# ------------------------------------------------------------------ summaries
def two_half_cos(vectors_by_pair: Mapping[str, torch.Tensor], seed: int = SEED) -> float:
    """Noise ceiling for a shared direction: cos between the mean vector over one seeded half of the pairs and over the other."""
    keys = sorted(vectors_by_pair)
    if len(keys) < 2:
        return float("nan")
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(keys))
    h1 = [keys[i] for i in perm[: len(keys) // 2]]
    h2 = [keys[i] for i in perm[len(keys) // 2:]]
    m1 = torch.stack([vectors_by_pair[k] for k in h1]).double().mean(0)
    m2 = torch.stack([vectors_by_pair[k] for k in h2]).double().mean(0)
    return float(cos(m1, m2))


def summarise_family(per_pair: Mapping[str, Mapping[str, Any]], Q: torch.Tensor) -> Dict[str, Any]:
    """Energy-fraction means/medians over all (pair, position), pairwise cosines of the four unit directions, the J-space
    energy of d_cm and d_pw (a random direction scores r/d), and the count of pairs/positions."""
    fr = {k: torch.cat([torch.as_tensor(r["frac"][k]) for r in per_pair.values()]) for k in FRAC_NAMES}
    out: Dict[str, Any] = {"n_pairs": len(per_pair), "n_positions": int(next(iter(fr.values())).numel()),
                           "frac_mean": {k: float(v.mean()) for k, v in fr.items()}, "frac_median": {k: float(v.median()) for k, v in fr.items()},
                           "frac_sd": {k: float(v.std()) if v.numel() > 1 else 0.0 for k, v in fr.items()},
                           "delta_norm_mean": float(torch.cat([r["delta_norm"] for r in per_pair.values()]).mean())}
    c_cm = torch.cat([torch.as_tensor(r["coef"]["d_cm"]) for r in per_pair.values()])
    c_pw = torch.cat([torch.as_tensor(r["coef"]["d_pw"]) for r in per_pair.values()])
    out["orientation_agreement"] = {"d_cm": float((c_cm > 0).float().mean()), "d_pw": float((c_pw > 0).float().mean()),
                                    "note": "fraction of (pair, position) with Δ(pos)·d̂ > 0, i.e. the shared direction points A→B for that state"}
    D = {k: torch.cat([r["dirs"][k] for r in per_pair.values()]) for k in DIR_NAMES}
    cosines: Dict[str, Dict[str, float]] = {}
    for i, a in enumerate(DIR_NAMES):
        for b in DIR_NAMES[i + 1:]:
            c = (D[a] * D[b]).sum(1)
            cosines[f"{a}|{b}"] = {"mean": float(c.mean()), "mean_abs": float(c.abs().mean()), "max_abs": float(c.abs().max())}
    out["cosines"] = cosines
    r, d = int(Q.shape[1]), int(Q.shape[0])
    out["j_energy"] = {"d_cm": float((project_Q(D["d_cm"], Q) ** 2).sum(1).mean()), "d_pw": float((project_Q(D["d_pw"], Q) ** 2).sum(1).mean()),
                       "d_res": float((project_Q(D["d_res"], Q) ** 2).sum(1).mean()), "random_expectation": r / d}
    return out
