"""X6 — rate each reader by agreement with the majority of the OTHER readers vs by agreement with a fact that was
established independently of the readers (direction_review.md X6; CPU only, on the frozen X1/X2/X3 artefacts).

Datasets (one state = one row; the KEY is the independently established fact):
  D1  X1 natural states (test split, four families); key = the constructed answer (= the model's own greedy answer
      for 126/128 of the X2 natural states, reported from x2_behaviour site 'nat').
  D2  X2 planted states at S2 (L38, all positions) at each item's minimal flipping dose alpha* and at alpha 1;
      key = the planted (other) candidate, causally verified: only entries with flipped_to_other and coherent.
  D3  X3 sets ERROR, ERROR_CONTROL, DISAGREE, AGREE_CONTROL; key = the model's actual greedy answer.
Readers: jlens, olens, nla (native log-odds from the LO files) and a linear PROBE as a non-sibling fourth reader:
  D1/D2  leave-one-pair-out diff-in-means WITHIN-PAIR contrast u = unit(mean_{q != p}(h_qA - h_qB)) over the X1
         natural states of the same family; a state h is scored by u . (h - m_p) against the pair's natural midpoint
         m_p. Version A's answer is always the first-listed candidate, so this is an ORDER-CONFOUNDED probe
         ("answer = first-listed candidate"); it is labelled as such everywhere. D2 scores the read-back vector.
  D3     5-fold (by item) L2 multinomial logistic probe over the candidate vocabulary (puzzles: symbols A-H, trained
         on the 400 puzzle states with the actual symbol as label); score = (w[actual] - w[other]) . h + (b[actual] -
         b[other]). The choice vocabulary (95 words / 66 items) leaves most items without a trained class for one
         candidate; its coverage is reported, and the choice sets use the binary 5-fold logistic probe on the label
         "actual == first-listed option" (score oriented toward the actual answer) as the probe reader.
Two scoring variants of every LO reader (the probe is identical in both):
  RAW      the pre-specified statistic: sign of the reader's per-state LO toward the key.
  CENTRED  post-hoc (2026-10-08, after seeing that RAW gives exactly one hit per pair on ownership/mapping, i.e. a
           per-candidate token bias that flips sign between the two states of a pair): D1 = pair-centred LO
           (= X1's E1 margin (lo_A + lo_B)/2 on both states); D2 = LO shift from the same source's natural state
           (= X2's E6 shift); D3 puzzles = LO minus a 5-fold additive per-symbol bias b[actual] - b[other]
           (writeup "Corrections" item 2); D3 choice sets cannot be centred (unique words) and reuse RAW.
Per reader r and dataset:  A_key(r) = P(LO toward the key > 0);  A_maj(r) = P(sign(r) == leave-one-out majority sign
of the OTHER readers of the definition), over states where that majority is defined;  M_acc = P(full majority == key).
Majority definitions: ALL (jlens, olens, nla, probe), SIBLINGS (olens, nla: defined where they agree; for a sibling
the LOO majority is the other sibling), NONSIB (jlens, probe). CIs: pair/item bootstrap (n_boot 2000, seed 0).
Also: Spearman rank correlation across the 4 readers between A_maj and A_key (n = 4, descriptive only), and the
shared-error statistic P(jlens, olens, nla all favour the same non-key candidate) vs the product of their marginals.
Outputs results/g_agreement/x6/{summary.json, x6.csv, fig_main.png, x6.md, log.md}.

    .venv/bin/python projects/g_agreement/x6_majority/analyze.py [--allow-unfrozen] [--out DIR]
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402

MODULE = "x6"
LO_READERS = ("jlens", "olens", "nla")
READERS = ("jlens", "olens", "nla", "probe")
READER_LABELS = {"jlens": "J-lens", "olens": "Oracle lens", "nla": "NLA", "probe": "probe (linear)"}
READER_COLORS = {**U.METHOD_COLORS, "probe": "#7d5ba6"}
MAJ_DEFS: Dict[str, Tuple[str, ...]] = {"all": ("jlens", "olens", "nla", "probe"), "siblings": ("olens", "nla"), "nonsib": ("jlens", "probe")}
MAJ_LABELS = {"all": "ALL (J-lens, Oracle, NLA, probe)", "siblings": "SIBLINGS (Oracle, NLA)", "nonsib": "NON-SIBLING (J-lens, probe)"}
VARIANTS = ("raw", "centred")
VARIANT_FIELD = {"raw": "lo", "centred": "lo_centred"}
FAMILIES = ("ownership", "mapping", "language", "tense")
X3_SETS = ("error", "error_control", "disagree", "agree_control")
DATASETS = ("D1", "D2_astar", "D2_alpha1", "D3_error", "D3_error_control", "D3_disagree", "D3_agree_control")
DATASET_LABELS = {"D1": "D1: X1 natural states (key = constructed answer)", "D2_astar": "D2: X2 planted at α* (key = planted candidate, model flipped)",
                  "D2_alpha1": "D2: X2 planted at α = 1 (key = planted candidate, model flipped)", "D3_error": "D3 ERROR (key = model's wrong answer)",
                  "D3_error_control": "D3 ERROR control (key = model's correct answer)", "D3_disagree": "D3 DISAGREE (key = model's actual choice)",
                  "D3_agree_control": "D3 AGREE control (key = model's actual choice)"}
FIG_PANELS = ("D1", "D2_astar", "D3_error", "D3_disagree")
PRIMARY_SITE = "S2"
PROBE_C = 1.0
N_FOLDS = 5
X_DIR = ROOT / "cache" / "g_agreement" / "x"
DEFAULTS = {"items": ROOT / "projects" / "g_agreement" / "dataset" / "items_x.json", "selected": ROOT / "projects" / "g_agreement" / "dataset" / "items_x3_selected.json",
            "x1_lo": X_DIR / "x1_lo.jsonl", "x2_lo": X_DIR / "x2_lo.jsonl", "x2_behaviour": X_DIR / "x2_behaviour.jsonl", "x3_lo": X_DIR / "x3_lo.jsonl",
            "states": ROOT / "cache" / "g_agreement" / "states", "readvecs": X_DIR / "x2_readvecs", "frozen": ROOT / "projects" / "g_agreement" / "manifest" / "frozen_config_x.json"}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=str(v))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    ap.add_argument("--skip-probe", action="store_true", help="no probe reader (no states on disk)")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ state tables
# A dataset is a list of rows {state, cluster (pair or item id for the bootstrap), family, key, lo: {reader: float|None},
# lo_centred: {reader: float|None}} where lo[reader] is the reader's log-odds TOWARD THE KEY (None = unscorable).

def sign(x: Optional[float]) -> Optional[int]:
    """+1 if the score favours the key, -1 otherwise (ties and non-finite count as not favouring), None if unscorable."""
    if x is None:
        return None
    x = float(x)
    if np.isnan(x):
        return None
    return 1 if x > 0 else -1


def majority(signs: Sequence[Optional[int]]) -> Optional[int]:
    """Majority sign over the available votes; None if no votes or an exact tie."""
    v = [s for s in signs if s is not None]
    if not v:
        return None
    t = sum(v)
    return None if t == 0 else (1 if t > 0 else -1)


def loo_majority(row_signs: Mapping[str, Optional[int]], members: Sequence[str], exclude: str) -> Optional[int]:
    """Majority of the definition's members other than `exclude` (a one-member remainder is a majority of one)."""
    return majority([row_signs.get(r) for r in members if r != exclude])


def table_signs(rows: Sequence[dict], field: str = "lo") -> List[Dict[str, Optional[int]]]:
    return [{r: sign(row.get(field, {}).get(r)) for r in READERS} for row in rows]


def rate_table(rows: Sequence[dict], nb: int, sd: int, readers: Sequence[str] = READERS, field: str = "lo") -> dict:
    """A_key per reader; A_maj per reader per majority definition; M_acc per definition (all pair/item bootstrap)."""
    S = table_signs(rows, field)
    out: dict = {"n_states": len(rows), "n_clusters": len({r["cluster"] for r in rows}), "readers": {}, "majority": {}}
    for rd in readers:
        a_key = U.pair_rate([(row["cluster"], None if s[rd] is None else s[rd] > 0) for row, s in zip(rows, S)], nb, sd)
        rec = {"A_key": a_key.as_dict(), "n_unscorable": sum(1 for s in S if s[rd] is None), "A_maj": {}}
        for d, members in MAJ_DEFS.items():
            flags = []
            for row, s in zip(rows, S):
                m = loo_majority(s, members, rd)
                flags.append((row["cluster"], None if (m is None or s[rd] is None) else s[rd] == m))
            rec["A_maj"][d] = U.pair_rate(flags, nb, sd).as_dict()
        out["readers"][rd] = rec
    for d, members in MAJ_DEFS.items():
        flags = []
        for row, s in zip(rows, S):
            m = majority([s[r] for r in members])
            flags.append((row["cluster"], None if m is None else m > 0))
        r_ = U.pair_rate(flags, nb, sd)
        out["majority"][d] = {"M_acc": r_.as_dict(), "n_defined": r_.n, "n_undefined": len(rows) - r_.n, "members": list(members)}
    return out


def spearman_readers(tab: dict, readers: Sequence[str] = READERS) -> Dict[str, dict]:
    from scipy.stats import spearmanr

    out = {}
    for d in MAJ_DEFS:
        x = [tab["readers"][r]["A_maj"][d]["p"] for r in readers]
        y = [tab["readers"][r]["A_key"]["p"] for r in readers]
        ok = [i for i in range(len(x)) if not (np.isnan(x[i]) or np.isnan(y[i]))]
        if len(ok) < 3:
            out[d] = {"rho": float("nan"), "n": len(ok), "note": "fewer than 3 readers with both rates"}
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # constant input (all readers equal) -> rho undefined, reported as nan
            rho = spearmanr([x[i] for i in ok], [y[i] for i in ok]).correlation
        out[d] = {"rho": float(rho) if rho is not None and not np.isnan(rho) else float("nan"), "n": len(ok),
                  "rank_by_A_maj": [readers[i] for i in sorted(ok, key=lambda i: -x[i])], "rank_by_A_key": [readers[i] for i in sorted(ok, key=lambda i: -y[i])],
                  "note": "n = 4 readers: descriptive only; rho in {-1, -0.8, ..., 1}"}
    return out


def shared_error(rows: Sequence[dict], nb: int, sd: int, readers: Sequence[str] = LO_READERS, field: str = "lo") -> dict:
    """P(all `readers` favour the same NON-KEY candidate) and P(all favour the key), observed vs independence."""
    S = table_signs(rows, field)
    full = [(row, s) for row, s in zip(rows, S) if all(s[r] is not None for r in readers)]
    if not full:
        return {"n": 0}
    marg_wrong = {r: float(np.mean([s[r] < 0 for _, s in full])) for r in readers}
    marg_key = {r: float(np.mean([s[r] > 0 for _, s in full])) for r in readers}
    obs_wrong = U.pair_rate([(row["cluster"], all(s[r] < 0 for r in readers)) for row, s in full], nb, sd)
    obs_key = U.pair_rate([(row["cluster"], all(s[r] > 0 for r in readers)) for row, s in full], nb, sd)
    exp_wrong = float(np.prod([marg_wrong[r] for r in readers]))
    exp_key = float(np.prod([marg_key[r] for r in readers]))
    return {"n": len(full), "readers": list(readers), "marginal_P_wrong": marg_wrong,
            "all_same_wrong": {"observed": obs_wrong.as_dict(), "expected_independent": exp_wrong, "ratio": (obs_wrong.p / exp_wrong) if exp_wrong > 0 else float("nan"),
                               "excess_pp": 100 * (obs_wrong.p - exp_wrong)},
            "all_key": {"observed": obs_key.as_dict(), "expected_independent": exp_key, "ratio": (obs_key.p / exp_key) if exp_key > 0 else float("nan")},
            "P_unanimous": obs_wrong.p + obs_key.p, "P_unanimous_expected_independent": exp_wrong + exp_key}


# ------------------------------------------------------------------ probes
def _unit(u: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(u)
    return u / n if n > 0 else u


def contrast_direction(pairs: Sequence[dict], H: Mapping[str, np.ndarray]) -> Optional[np.ndarray]:
    """unit(mean over pairs of h_A - h_B); pairs: {pair_id, A, B} with A/B item ids present in H. None if no pairs."""
    d = [H[p["A"]] - H[p["B"]] for p in pairs if p["A"] in H and p["B"] in H]
    return _unit(np.mean(d, axis=0)) if d else None


def loo_directions(pairs: Sequence[dict], H: Mapping[str, np.ndarray]) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """pair_id -> (u_{-p}, m_p): direction from the other pairs and the pair's own natural midpoint."""
    out = {}
    usable = [p for p in pairs if p["A"] in H and p["B"] in H]
    for p in usable:
        u = contrast_direction([q for q in usable if q["pair_id"] != p["pair_id"]], H)
        if u is None:
            continue
        out[p["pair_id"]] = (u, (H[p["A"]] + H[p["B"]]) / 2.0)
    return out


def probe_toward_key_d1(dirs: Mapping[str, Tuple[np.ndarray, np.ndarray]], pair_id: str, version: str, h: np.ndarray) -> Optional[float]:
    """D1: version A's answer lies on the +u side (A - B), version B's on the -u side."""
    if pair_id not in dirs:
        return None
    u, m = dirs[pair_id]
    s = float(u @ (h - m))
    return s if version == "A" else -s


def probe_toward_other_d2(dirs: Mapping[str, Tuple[np.ndarray, np.ndarray]], pair_id: str, source: str, v: np.ndarray) -> Optional[float]:
    """D2: planted toward the other version: from source A the key is B (the -u side), from source B the key is A."""
    if pair_id not in dirs:
        return None
    u, m = dirs[pair_id]
    s = float(u @ (v - m))
    return -s if source == "A" else s


def _folds(n: int, n_folds: int, seed: int) -> List[np.ndarray]:
    idx = np.random.default_rng(seed).permutation(n)
    return [idx[i::n_folds] for i in range(min(n_folds, n))]


def probe_multinomial_kfold(X: np.ndarray, labels: Sequence[str], cands: Sequence[Tuple[str, str]], n_folds: int = N_FOLDS, seed: int = U.SEED, C: float = PROBE_C) -> List[Optional[float]]:
    """K-fold (by row) L2 multinomial logistic probe over the label vocabulary; per row the held-out score
    (w[actual] - w[other]) . h + (b[actual] - b[other]), None when a candidate class is absent from the training fold."""
    from sklearn.linear_model import LogisticRegression

    n = X.shape[0]
    out: List[Optional[float]] = [None] * n
    labels = list(labels)
    for te in _folds(n, n_folds, seed):
        tr = np.setdiff1d(np.arange(n), te)
        ytr = [labels[i] for i in tr]
        if len(set(ytr)) < 2:
            continue
        mu = X[tr].mean(0)
        sc = float(X[tr].std()) or 1.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # "more classes than 50% of samples" on the choice vocabulary (reported as coverage)
            clf = LogisticRegression(C=C, max_iter=5000).fit((X[tr] - mu) / sc, ytr)
        cls = {c: i for i, c in enumerate(clf.classes_)}
        W, b = clf.coef_, clf.intercept_
        if len(clf.classes_) == 2:  # sklearn stores one row for binary: logit(class 1) - logit(class 0)
            W = np.vstack([-W[0] / 2, W[0] / 2]); b = np.array([-b[0] / 2, b[0] / 2])
        for i in te:
            a, o = cands[i]
            if a not in cls or o not in cls:
                continue
            z = (X[i] - mu) / sc
            out[i] = float((W[cls[a]] - W[cls[o]]) @ z + (b[cls[a]] - b[cls[o]]))
    return out


def probe_binary_kfold(X: np.ndarray, y: Sequence[int], n_folds: int = N_FOLDS, seed: int = U.SEED, C: float = PROBE_C) -> List[Optional[float]]:
    """K-fold L2 logistic probe on a binary label; held-out logit toward label 1 per row (None if a fold lacks a class)."""
    from sklearn.linear_model import LogisticRegression

    n = X.shape[0]
    y = np.asarray(y, dtype=int)
    out: List[Optional[float]] = [None] * n
    for te in _folds(n, n_folds, seed):
        tr = np.setdiff1d(np.arange(n), te)
        if len(set(y[tr].tolist())) < 2:
            continue
        mu = X[tr].mean(0)
        sc = float(X[tr].std()) or 1.0
        clf = LogisticRegression(C=C, max_iter=5000).fit((X[tr] - mu) / sc, y[tr])
        z = clf.decision_function((X[te] - mu) / sc)
        for i, zi in zip(te, z):
            out[i] = float(zi)
    return out


def symbol_bias_kfold(lo: Sequence[Optional[float]], cands: Sequence[Tuple[str, str]], n_folds: int = N_FOLDS, seed: int = U.SEED) -> List[Optional[float]]:
    """Additive per-symbol bias of one reader, fitted by least squares lo_i ~ b[actual_i] - b[other_i] on the training
    folds; returns the held-out centred LO (lo - (b[a] - b[o])) per row, None where lo is None or a symbol is unseen."""
    n = len(lo)
    out: List[Optional[float]] = [None] * n
    for te in _folds(n, n_folds, seed):
        tr = [i for i in np.setdiff1d(np.arange(n), te) if lo[i] is not None]
        syms = sorted({s for i in tr for s in cands[i]})
        if len(tr) < len(syms) + 1:
            continue
        idx = {s: j for j, s in enumerate(syms)}
        A = np.zeros((len(tr), len(syms)))
        for r, i in enumerate(tr):
            A[r, idx[cands[i][0]]] += 1.0
            A[r, idx[cands[i][1]]] -= 1.0
        b = np.linalg.lstsq(A, np.array([lo[i] for i in tr], dtype=float), rcond=None)[0]
        for i in te:
            if lo[i] is None or cands[i][0] not in idx or cands[i][1] not in idx:
                continue
            out[i] = float(lo[i] - (b[idx[cands[i][0]]] - b[idx[cands[i][1]]]))
    return out


# ------------------------------------------------------------------ loading
def load_vec(path: Path) -> np.ndarray:
    import torch

    return torch.load(path, map_location="cpu").float().numpy().astype(np.float64)


def x_pairs(items: Mapping[str, dict], split: str = "test") -> Dict[str, List[dict]]:
    """{family: [{pair_id, family, A: item_id, B: item_id}]} of the split."""
    by: Dict[str, dict] = {}
    for it in items.values():
        if it.get("split") == split and it.get("family") in FAMILIES:
            by.setdefault(it["pair_id"], {"pair_id": it["pair_id"], "family": it["family"]})[it["version"]] = it["item_id"]
    out: Dict[str, List[dict]] = {f: [] for f in FAMILIES}
    for p in by.values():
        if "A" in p and "B" in p:
            out[p["family"]].append(p)
    return out


def load_states_for(pairs_by_family: Mapping[str, Sequence[dict]], states_dir: Path) -> Tuple[Dict[str, np.ndarray], List[str]]:
    H, missing = {}, []
    for ps in pairs_by_family.values():
        for p in ps:
            for v in "AB":
                f = states_dir / f"{p[v]}.pt"
                if f.exists():
                    H[p[v]] = load_vec(f)
                else:
                    missing.append(p[v])
    return H, missing


def _centre_pair(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b is None else (float(a) + float(b)) / 2.0


def build_d1(items: Mapping[str, dict], x1_rows: Sequence[dict], dirs_by_family: Mapping[str, Mapping[str, tuple]], H: Mapping[str, np.ndarray], use_probe: bool) -> List[dict]:
    pairs = x_pairs(items, "test")
    lo: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for r in x1_rows:
        if r.get("condition", "natural") == "natural" and "item_id" in r and r.get("reader") in LO_READERS:
            lo[r["item_id"]][r["reader"]] = None if r.get("unscorable") else r.get("lo")
    rows = []
    for fam in FAMILIES:
        for p in pairs[fam]:
            for v in "AB":
                iid = p[v]
                it = items[iid]
                d = {rd: lo.get(iid, {}).get(rd) for rd in LO_READERS}
                d["probe"] = probe_toward_key_d1(dirs_by_family.get(fam, {}), p["pair_id"], v, H[iid]) if (use_probe and iid in H) else None
                c = {rd: _centre_pair(lo.get(p["A"], {}).get(rd), lo.get(p["B"], {}).get(rd)) for rd in LO_READERS}
                c["probe"] = d["probe"]
                rows.append({"state": iid, "cluster": p["pair_id"], "family": fam, "version": v, "key": it["primary"]["answer"], "lo": d, "lo_centred": c})
    return rows


def alpha_star(beh: Sequence[dict], site: str) -> Dict[Tuple[str, str], Optional[float]]:
    """(pair_id, source) -> smallest planted alpha at `site` with flipped_to_other and coherent (None = no flip)."""
    fl: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    items = set()
    for r in beh:
        if r["site"] != site or r["condition"] != "planted":
            continue
        items.add((r["pair_id"], r["source"]))
        if r.get("flipped_to_other") and r.get("coherent"):
            fl[(r["pair_id"], r["source"])].append(float(r["alpha"]))
    return {it: (min(fl[it]) if fl.get(it) else None) for it in sorted(items)}


def readvec_path(readvecs_dir: Path, key: str) -> Path:
    return readvecs_dir / (key.replace("|", "__") + ".pt")


def build_d2(beh: Sequence[dict], x2_rows: Sequence[dict], dirs_by_family: Mapping[str, Mapping[str, tuple]], readvecs_dir: Path, site: str, use_probe: bool) -> Tuple[List[dict], List[dict], dict]:
    """(rows at alpha*, rows at alpha 1, info). Only flipped & coherent planted entries at `site`."""
    astar = alpha_star(beh, site)
    lo: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for r in x2_rows:
        if r.get("reader") in LO_READERS:
            lo[r["entry_key"]][r["reader"]] = None if r.get("unscorable") else r.get("lo_toward_other")
    nat_key = {(r["pair_id"], r["source"]): r["key"] for r in beh if r["site"] == "nat" and r["condition"] == "natural"}
    rows_star, rows_one, missing_vecs, missing_nat = [], [], 0, 0
    for r in beh:
        if r["site"] != site or r["condition"] != "planted" or not (r.get("flipped_to_other") and r.get("coherent")):
            continue
        a = float(r["alpha"])
        it = (r["pair_id"], r["source"])
        is_star, is_one = astar.get(it) == a, a == 1.0
        if not (is_star or is_one):
            continue
        d = {rd: lo.get(r["key"], {}).get(rd) for rd in LO_READERS}
        d["probe"] = None
        if use_probe:
            f = readvec_path(readvecs_dir, r["key"])
            if f.exists():
                d["probe"] = probe_toward_other_d2(dirs_by_family.get(r["family"], {}), r["pair_id"], r["source"], load_vec(f))
            else:
                missing_vecs += 1
        nk = nat_key.get(it)
        if nk is None:
            missing_nat += 1
        c = {rd: (None if (nk is None or d[rd] is None or lo.get(nk, {}).get(rd) is None) else float(d[rd]) - float(lo[nk][rd])) for rd in LO_READERS}
        c["probe"] = d["probe"]
        row = {"state": r["key"], "cluster": r["pair_id"], "family": r["family"], "source": r["source"], "alpha": a, "alpha_star": astar.get(it), "key": r["cand_B"], "lo": d, "lo_centred": c}
        if is_star:
            rows_star.append(row)
        if is_one:
            rows_one.append(dict(row))
    info = {"site": site, "n_items": len(astar), "n_items_with_alpha_star": sum(v is not None for v in astar.values()),
            "alpha_star_counts": {str(a): sum(1 for v in astar.values() if v == a) for a in sorted({v for v in astar.values() if v is not None})},
            "n_missing_readvecs": missing_vecs, "n_entries_without_natural_lo": missing_nat, "selection": "planted, flipped_to_other and coherent only",
            "centred": "lo_toward_other(planted) - lo_toward_other(natural state of the same source) = X2 E6 shift"}
    return rows_star, rows_one, info


def build_d3(selected: Mapping[str, dict], x3_rows: Sequence[dict], states_dir: Path, use_probe: bool, seed: int) -> Tuple[Dict[str, List[dict]], dict]:
    lo: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for r in x3_rows:
        if r.get("reader") in LO_READERS and r.get("item_id") in selected:
            lo[r["item_id"]][r["reader"]] = None if r.get("unscorable") else r.get("lo_actual")
    probe: Dict[str, Optional[float]] = {}
    centred: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    info: dict = {"puzzle": {}, "choice": {}}
    for fam, sets in (("puzzle", ("error", "error_control")), ("choice", ("disagree", "agree_control"))):
        ids = sorted(i for i, it in selected.items() if it["set"] in sets)
        cands_all = [tuple(selected[i]["primary"]["candidates"][:2]) for i in ids]
        if fam == "puzzle":  # centred LO: 5-fold additive symbol bias per reader
            for rd in LO_READERS:
                c = symbol_bias_kfold([lo.get(i, {}).get(rd) for i in ids], cands_all, N_FOLDS, seed)
                for i, v in zip(ids, c):
                    centred[i][rd] = v
            info[fam]["centred"] = "lo_actual minus a 5-fold least-squares additive symbol bias b[actual] - b[other] (per reader)"
        else:
            for i in ids:
                for rd in LO_READERS:
                    centred[i][rd] = lo.get(i, {}).get(rd)
            info[fam]["centred"] = "not centrable (unique words per item): CENTRED = RAW"
        have = [i for i in ids if (states_dir / f"{i}.pt").exists()] if use_probe else []
        info[fam].update({"n_items": len(ids), "n_states": len(have), "n_folds": N_FOLDS, "C": PROBE_C})
        if len(have) < 2 * N_FOLDS:
            info[fam]["status"] = "probe skipped (too few states)"
            continue
        X = np.stack([load_vec(states_dir / f"{i}.pt") for i in have])
        cands = [tuple(selected[i]["primary"]["candidates"][:2]) for i in have]
        actual = [c[0] for c in cands]
        multi = probe_multinomial_kfold(X, actual, cands, N_FOLDS, seed)
        info[fam]["vocabulary_size"] = len(set(actual) | {c[1] for c in cands})
        info[fam]["multinomial_n_scorable"] = sum(v is not None for v in multi)
        if fam == "puzzle":
            info[fam]["probe"] = "5-fold L2 multinomial logistic over the symbol vocabulary; score = (w[actual] - w[other]) . h + db"
            probe.update(dict(zip(have, multi)))
        else:
            first = [int(U.normalise_answer(selected[i]["primary"]["answer"]) == U.normalise_answer((selected[i].get("source") or {}).get("first_listed"))) for i in have]
            z = probe_binary_kfold(X, first, N_FOLDS, seed)
            probe.update({i: (None if zi is None else (zi if f1 else -zi)) for i, zi, f1 in zip(have, z, first)})
            info[fam]["probe"] = ("5-fold L2 binary logistic on 'actual == first-listed option', oriented toward the actual answer "
                                  "(the multinomial over the choice vocabulary is reported for coverage only)")
            info[fam]["n_first_listed"] = int(sum(first))
        info[fam]["status"] = "ok"
    out: Dict[str, List[dict]] = {}
    for s in X3_SETS:
        rows = []
        for i in sorted(i for i, it in selected.items() if it["set"] == s):
            d = {rd: lo.get(i, {}).get(rd) for rd in LO_READERS}
            d["probe"] = probe.get(i)
            c = {rd: centred.get(i, {}).get(rd) for rd in LO_READERS}
            c["probe"] = d["probe"]
            rows.append({"state": i, "cluster": i, "family": selected[i]["family"], "set": s, "key": selected[i]["primary"]["answer"], "lo": d, "lo_centred": c})
        out[f"D3_{s}"] = rows
    return out, info


# ------------------------------------------------------------------ run
def analyse_tables(tables: Mapping[str, Sequence[dict]], nb: int, sd: int, variants: Sequence[str] = VARIANTS) -> Dict[str, Dict[str, dict]]:
    """{variant: {dataset: statistics}} for a {dataset: rows} mapping (pure; used by the tests)."""
    res: Dict[str, Dict[str, dict]] = {v: {} for v in variants}
    for name, rows in tables.items():
        for v in variants:
            f = VARIANT_FIELD[v]
            if not rows:
                res[v][name] = {"n_states": 0}
                continue
            t = rate_table(rows, nb, sd, field=f)
            t["spearman_A_maj_vs_A_key"] = spearman_readers(t)
            t["shared_error_three_lo_readers"] = shared_error(rows, nb, sd, LO_READERS, f)
            t["shared_error_four_readers"] = shared_error(rows, nb, sd, READERS, f)
            res[v][name] = t
    return res


def csv_rows(res: Mapping[str, Mapping[str, dict]]) -> List[dict]:
    out = []
    for v, byds in res.items():
        for ds, t in byds.items():
            if not t.get("n_states"):
                continue
            for rd in READERS:
                r = t["readers"][rd]
                for d in MAJ_DEFS:
                    am, m = r["A_maj"][d], t["majority"][d]["M_acc"]
                    out.append({"variant": v, "dataset": ds, "reader": rd, "majority_def": d, "n_states": t["n_states"], "n_clusters": t["n_clusters"],
                                "A_key": r["A_key"]["p"], "A_key_lo": r["A_key"]["lo"], "A_key_hi": r["A_key"]["hi"], "A_key_k": r["A_key"]["k"], "A_key_n": r["A_key"]["n"],
                                "A_maj": am["p"], "A_maj_lo": am["lo"], "A_maj_hi": am["hi"], "A_maj_k": am["k"], "A_maj_n": am["n"],
                                "M_acc": m["p"], "M_acc_lo": m["lo"], "M_acc_hi": m["hi"], "M_acc_n": m["n"],
                                "spearman_rho": t["spearman_A_maj_vs_A_key"][d]["rho"],
                                "probe_label": "order-confounded within-pair contrast (LOO by pair)" if ds.startswith(("D1", "D2")) else "5-fold logistic"})
    return out


def run(args: argparse.Namespace) -> dict:
    t0 = time.time()
    frozen, _ = U.require_frozen(args.frozen, args.allow_unfrozen)
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if frozen else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    nb, sd = args.n_boot, args.seed
    _, items = U.load_items(args.items)
    selected = {it["item_id"]: it for it in U.load_json(args.selected)["items"]}
    x1 = U.load_jsonl(args.x1_lo)
    beh = U.load_jsonl(args.x2_behaviour)
    x2 = U.load_jsonl(args.x2_lo)
    x3 = U.load_jsonl(args.x3_lo)
    states_dir, readvecs_dir = Path(args.states), Path(args.readvecs)
    use_probe = not args.skip_probe
    U.log(f"[x6] frozen={frozen} x1 rows {len(x1)}, x2 behaviour {len(beh)}, x2 lo {len(x2)}, x3 lo {len(x3)}, selected {len(selected)}; probe={use_probe}; out={out}")
    pairs = x_pairs(items, "test")
    H, missing = load_states_for(pairs, states_dir) if use_probe else ({}, [])
    dirs = {fam: loo_directions(pairs[fam], H) for fam in FAMILIES} if use_probe else {}
    nat = [r for r in beh if r["site"] == "nat"]
    key_check = {"n_x2_natural_states": len(nat), "n_model_answer_equals_constructed": sum(bool(r.get("kept_original")) for r in nat),
                 "states_where_model_disagrees": sorted(r["state_item_id"] for r in nat if not r.get("kept_original"))}
    tables: Dict[str, List[dict]] = {"D1": build_d1(items, x1, dirs, H, use_probe)}
    d2s, d2o, d2info = build_d2(beh, x2, dirs, readvecs_dir, PRIMARY_SITE, use_probe)
    tables["D2_astar"], tables["D2_alpha1"] = d2s, d2o
    d3, d3info = build_d3(selected, x3, states_dir, use_probe, sd)
    tables.update(d3)
    for k in DATASETS:
        U.log(f"[x6] {k}: {len(tables.get(k, []))} states")
    res = analyse_tables({k: tables[k] for k in DATASETS if k in tables}, nb, sd)
    by_family = {fam: {v: rate_table([r for r in tables["D1"] if r["family"] == fam], nb, sd, field=VARIANT_FIELD[v]) for v in VARIANTS} for fam in FAMILIES}
    for v in VARIANTS:
        for ds in DATASETS:
            t = res[v].get(ds, {})
            if not t.get("n_states"):
                continue
            for rd in READERS:
                r = t["readers"][rd]
                U.log(f"[x6] {v:7} {ds:17} {READER_LABELS[rd]:14} A_key {100 * r['A_key']['p']:5.1f} [{100 * r['A_key']['lo']:.0f},{100 * r['A_key']['hi']:.0f}]  " +
                      "  ".join(f"A_maj[{d}] {100 * r['A_maj'][d]['p']:5.1f} (n {r['A_maj'][d]['n']})" for d in MAJ_DEFS))
            U.log(f"[x6] {v:7} {ds:17} M_acc " + "  ".join(f"{d} {100 * t['majority'][d]['M_acc']['p']:.1f}% (n {t['majority'][d]['n_defined']})" for d in MAJ_DEFS) +
                  "  rho " + " ".join(f"{d} {t['spearman_A_maj_vs_A_key'][d]['rho']:+.2f}" for d in MAJ_DEFS))
            se = t["shared_error_three_lo_readers"]
            if se.get("n"):
                U.log(f"[x6] {v:7} {ds:17} shared error (3 LO readers all favour the non-key candidate): obs {100 * se['all_same_wrong']['observed']['p']:.1f}% "
                      f"vs indep {100 * se['all_same_wrong']['expected_independent']:.1f}% (n {se['n']})")
    summary = {"module": MODULE, "frozen": frozen, "n_boot": nb, "seed": sd, "readers": list(READERS), "majority_definitions": {d: list(m) for d, m in MAJ_DEFS.items()},
               "variants": {"raw": "pre-specified: sign of the per-state LO toward the key",
                            "centred": "post-hoc 2026-10-08 (RAW gives one hit per pair on ownership/mapping = per-candidate bias): D1 pair-centred (X1 E1 margin), "
                                       "D2 shift from the same source's natural state (X2 E6), D3 puzzles minus 5-fold additive symbol bias, D3 choice = RAW; probe unchanged"},
               "definitions": {"A_key": "P(reader LO toward the key > 0); ties/non-finite count as not favouring", "A_maj": "P(reader sign == LOO majority sign of the other members); states with an undefined (tied/empty) majority excluded",
                               "M_acc": "P(full-definition majority == key) over states where defined", "CI": "pair bootstrap (D1, D2 by pair_id; D3 by item)"},
               "probe": {"D1_D2": "LOO-by-pair within-pair contrast unit(mean(h_A - h_B)) over X1 natural states of the family, scored by u . (h - pair midpoint); "
                                  "ORDER-CONFOUNDED: version A's answer is always the first-listed candidate, so the direction is 'answer = first-listed candidate'",
                         "n_states_missing_for_probe": len(missing), "n_pairs_with_direction": {f: len(dirs.get(f, {})) for f in FAMILIES}, "D3": d3info},
               "D1_key_check": key_check, "D2": d2info,
               "datasets": {k: {"label": DATASET_LABELS[k], **{v: res[v].get(k, {"n_states": 0}) for v in VARIANTS}} for k in DATASETS},
               "D1_by_family": by_family, "wall_s": round(time.time() - t0, 1)}
    U.write_json(out / "summary.json", summary)
    U.write_csv(out / "x6.csv", csv_rows(res))
    write_md(out / "x6.md", summary)
    if not args.no_fig:
        make_figure(out / "fig_main.png", summary)
    with open(out / "log.md", "a") as f:
        f.write(f"- {dt.datetime.now(dt.timezone.utc).isoformat()} `{' '.join(sys.argv)}` frozen={frozen} n_boot={nb} seed={sd} wall {summary['wall_s']} s; "
                f"states D1 {len(tables['D1'])}, D2 α* {len(d2s)}, D2 α=1 {len(d2o)}, D3 " + ", ".join(f"{s} {len(tables[f'D3_{s}'])}" for s in X3_SETS) + "\n")
    U.log(f"[x6] wrote {out} ({summary['wall_s']} s)")
    return summary


# ------------------------------------------------------------------ reporting
def _pct(d: Optional[Mapping[str, Any]]) -> str:
    return "n/a" if d is None or np.isnan(d.get("p", float("nan"))) else f"{100 * d['p']:.0f} [{100 * d['lo']:.0f}, {100 * d['hi']:.0f}]"


def _maj3(r: Mapping[str, Any]) -> str:
    return "/".join("n/a" if np.isnan(r["A_maj"][d]["p"]) else f"{100 * r['A_maj'][d]['p']:.0f}" for d in MAJ_DEFS)


def write_md(path: Path, s: dict) -> None:
    L = ["# X6 — agreement with the majority vs agreement with an independent key", "",
         f"Readers J-lens, Oracle, NLA (native LO) + linear probe (D1/D2: ORDER-CONFOUNDED within-pair contrast, LOO by pair; D3: 5-fold logistic). "
         f"% of states [95% pair/item bootstrap, n_boot {s['n_boot']}]. A_key = favours the key; A_maj = agrees with the LOO majority of the other readers "
         f"under ALL / SIBLINGS (Oracle+NLA) / NONSIB (J-lens+probe); M_acc = majority == key. RAW = pre-specified per-state sign; CENTRED = post-hoc bias removal "
         f"(see summary.json 'variants'; RAW scores exactly one state per pair on ownership/mapping: a per-candidate bias, not reading).", ""]
    L.append("| dataset (n) | reader | A_key RAW | A_maj RAW ALL/SIB/NONSIB | A_key CENTRED | A_maj CENTRED ALL/SIB/NONSIB |")
    L.append("|---|---|---|---|---|---|")
    for ds in FIG_PANELS:
        t, c = s["datasets"][ds]["raw"], s["datasets"][ds]["centred"]
        if not t.get("n_states"):
            continue
        for rd in READERS:
            L.append(f"| {ds} ({t['n_states']}) | {READER_LABELS[rd]} | {_pct(t['readers'][rd]['A_key'])} | {_maj3(t['readers'][rd])} | {_pct(c['readers'][rd]['A_key'])} | {_maj3(c['readers'][rd])} |")
        L.append(f"| {ds} | M_acc ALL/SIB/NONSIB | " + "/".join(f"{100 * t['majority'][d]['M_acc']['p']:.0f}" for d in MAJ_DEFS) + f" (n {'/'.join(str(t['majority'][d]['n_defined']) for d in MAJ_DEFS)}) | "
                 f"ρ(A_maj, A_key) " + "/".join(f"{t['spearman_A_maj_vs_A_key'][d]['rho']:+.1f}" for d in MAJ_DEFS) + " | " +
                 "/".join(f"{100 * c['majority'][d]['M_acc']['p']:.0f}" for d in MAJ_DEFS) + f" (n {'/'.join(str(c['majority'][d]['n_defined']) for d in MAJ_DEFS)}) | "
                 f"ρ " + "/".join(f"{c['spearman_A_maj_vs_A_key'][d]['rho']:+.1f}" for d in MAJ_DEFS) + " |")
    L.append("")
    for v in VARIANTS:
        se = s["datasets"]["D3_error"][v].get("shared_error_three_lo_readers", {})
        if se.get("n"):
            w = se["all_same_wrong"]
            L.append(f"Shared error, D3 ERROR, {v} (n {se['n']}): the three LO readers all favour the same non-key candidate in {100 * w['observed']['p']:.1f}% "
                     f"[{100 * w['observed']['lo']:.1f}, {100 * w['observed']['hi']:.1f}] vs {100 * w['expected_independent']:.1f}% under independence (ratio {w['ratio']:.2f}); "
                     f"unanimous either way {100 * se['P_unanimous']:.1f}% vs {100 * se['P_unanimous_expected_independent']:.1f}%.")
    kc = s["D1_key_check"]
    fam = s.get("D1_by_family", {})
    L.append(f"D1 key check: model's greedy answer = constructed answer for {kc['n_model_answer_equals_constructed']}/{kc['n_x2_natural_states']} X2 natural states "
             f"(differs: {', '.join(kc['states_where_model_disagrees']) or 'none'}). D2: {s['D2']['n_items_with_alpha_star']}/{s['D2']['n_items']} items flip at S2. "
             "D1 A_key RAW by family (J/O/N/probe): " + "; ".join(f"{f} " + "/".join(f"{100 * fam[f]['raw']['readers'][r]['A_key']['p']:.0f}" for r in READERS) for f in FAMILIES if f in fam) + ".")
    L += ["", "## Conclusion", ""] + conclusion_lines(s)
    path.write_text("\n".join(L) + "\n")


def conclusion_lines(s: dict) -> List[str]:
    out = []
    for v in VARIANTS:
        parts = []
        for ds in FIG_PANELS:
            t = s["datasets"][ds][v]
            if not t.get("n_states"):
                continue
            rho = t["spearman_A_maj_vs_A_key"]
            parts.append(f"{ds} ALL {rho['all']['rho']:+.1f} SIB {rho['siblings']['rho']:+.1f} NONSIB {rho['nonsib']['rho']:+.1f}")
        ok = [ds for ds in FIG_PANELS if s["datasets"][ds][v].get("n_states") and all(s["datasets"][ds][v]["spearman_A_maj_vs_A_key"][d]["rho"] >= 0.8 for d in ("all", "siblings"))]
        out.append(f"- Does majority agreement rank the readers like the key ({v}; proxy rule ρ ≥ 0.8 under ALL and SIB, n = 4)? ρ: " + "; ".join(parts) +
                   f". Passes on: {', '.join(ok) or 'none'}.")
    t, c = s["datasets"]["D3_error"]["raw"], s["datasets"]["D3_error"]["centred"]
    if t.get("n_states"):
        for v, tt in (("raw", t), ("centred", c)):
            ol, nl = tt["readers"]["olens"], tt["readers"]["nla"]
            out.append(f"- D3 ERROR, {v}: Oracle agrees with NLA in {_pct(ol['A_maj']['siblings'])}% of states but with the key in {_pct(ol['A_key'])}% (NLA with key {_pct(nl['A_key'])}%); "
                       f"where the siblings agree they match the key {_pct(tt['majority']['siblings']['M_acc'])}% (n {tt['majority']['siblings']['n_defined']}); "
                       f"NONSIB majority {_pct(tt['majority']['nonsib']['M_acc'])}%, probe alone {_pct(tt['readers']['probe']['A_key'])}%.")
    return out


def make_figure(path: Path, s: dict) -> None:
    plt = U.mpl()
    fig, axes = plt.subplots(len(VARIANTS), len(FIG_PANELS), figsize=(4.0 * len(FIG_PANELS), 4.2 * len(VARIANTS)))
    axes = np.atleast_2d(axes)
    for row, v in enumerate(VARIANTS):
        for col, ds in enumerate(FIG_PANELS):
            ax = axes[row, col]
            t = s["datasets"][ds][v]
            ax.plot([0, 1], [0, 1], color=U.INK2, lw=0.8, ls=":", zorder=1)
            ax.axhline(0.5, color=U.GRID, lw=0.8, zorder=0); ax.axvline(0.5, color=U.GRID, lw=0.8, zorder=0)
            ax.set_xlim(0, 1.02); ax.set_ylim(0, 1.02)
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1]); ax.set_xticklabels(["0", "25", "50", "75", "100"]); ax.set_yticks([0, 0.25, 0.5, 0.75, 1]); ax.set_yticklabels(["0", "25", "50", "75", "100"])
            ax.grid(color=U.GRID, lw=0.6); ax.set_axisbelow(True)
            if not t.get("n_states"):
                ax.text(0.5, 0.5, "no states", ha="center", va="center", color=U.INK2); ax.set_title(DATASET_LABELS[ds], fontsize=8.5); continue
            for rd in READERS:
                r = t["readers"][rd]
                x, y = r["A_maj"]["all"], r["A_key"]
                if np.isnan(x["p"]) or np.isnan(y["p"]):
                    continue
                ax.errorbar(x["p"], y["p"], xerr=[[max(x["p"] - x["lo"], 0)], [max(x["hi"] - x["p"], 0)]], yerr=[[max(y["p"] - y["lo"], 0)], [max(y["hi"] - y["p"], 0)]],
                            fmt="o", ms=8, color=READER_COLORS[rd], ecolor=READER_COLORS[rd], elinewidth=1.2, capsize=3, mec=U.SURFACE, mew=1.2,
                            label=READER_LABELS[rd] + (" — order-confounded" if rd == "probe" and ds.startswith(("D1", "D2")) else ""), zorder=4)
                ax.annotate(READER_LABELS[rd].split(" ")[0], (x["p"], y["p"]), xytext=(6, -10 if rd in ("nla", "probe") else 6), textcoords="offset points", fontsize=7.5, color=U.INK2)
            if ds == "D2_astar" and s["datasets"]["D2_alpha1"][v].get("n_states"):
                for rd in READERS:
                    r = s["datasets"]["D2_alpha1"][v]["readers"][rd]
                    x, y = r["A_maj"]["all"]["p"], r["A_key"]["p"]
                    if not (np.isnan(x) or np.isnan(y)):
                        ax.plot(x, y, "o", ms=8, mfc="none", mec=READER_COLORS[rd], mew=1.4, zorder=3)
                ax.plot([], [], "o", ms=8, mfc="none", mec=U.INK2, label="hollow = α = 1")
            m = t["majority"]
            ax.text(0.03, 0.97, f"M_acc ALL {100 * m['all']['M_acc']['p']:.0f}% (n {m['all']['n_defined']})\n      SIB {100 * m['siblings']['M_acc']['p']:.0f}% (n {m['siblings']['n_defined']})\n"
                                f"      NONSIB {100 * m['nonsib']['M_acc']['p']:.0f}% (n {m['nonsib']['n_defined']})\nρ(A_maj, A_key) ALL {t['spearman_A_maj_vs_A_key']['all']['rho']:+.1f}",
                    transform=ax.transAxes, va="top", fontsize=7.5, color=U.INK, family="monospace")
            if row == len(VARIANTS) - 1:
                ax.set_xlabel("A_maj (ALL): agrees with the LOO majority\nof the other 3 readers (% of states)", fontsize=8.5)
            if col == 0:
                ax.set_ylabel(f"{v.upper()} scoring\nA_key: agrees with the independent key (% of states)")
            ax.set_title(f"{DATASET_LABELS[ds]}\nn = {t['n_states']} states / {t['n_clusters']} {'items' if ds.startswith('D3') else 'pairs'}", fontsize=8.5)
            ax.legend(fontsize=6.8, loc="lower right")
    fig.suptitle(("" if s["frozen"] else "UNFROZEN DEV RUN — ") + "X6 — rating readers by majority agreement vs by an independently established key. "
                 "Top: pre-specified RAW per-state sign; bottom: CENTRED (pair / natural-state / symbol-bias removed). Bars = 95% pair/item bootstrap; dotted = identity",
                 y=1.01, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
