"""W1 — the Phase W steering matrix (PREREG_WV "Analysis and decision rules", brief_wv.md "W1 matrix (primary)"). CPU only, no model calls.

Inputs (never modified):
  cache/g_agreement/w/s2_behaviour.jsonl   one row per decode: key = pair|source|W2|direction|alpha|k, family ∈ {ownership, mapping, errors},
                                           direction ∈ {natural, d_cm, d_pw, d_J, d_res, full, random}, alpha, k, cand_A (own) / cand_B (other),
                                           flipped_to_other, coherent, lo_model = lp_first_B − lp_first_A (positive = toward the other candidate),
                                           lo_model_unscorable, edit_layer, read_layers. One ``natural`` row per state (pair_id, source).
  cache/g_agreement/w/s3_lo.jsonl          one row per (reader, read layer, S2 entry): reader ∈ {jlens, olens, nla, skip_a, probe}, unit S2[@L48],
                                           entry_key = the behaviour key, read_layer, lo_own = score(own) − score(other), lo_toward_edit = −lo_own;
                                           the probe also carries score_edited / score_read (own − other on the edited site vectors / the read-back).
                                           Optional: without --lo the model-side half runs alone (model-only mode).

Definitions (BRIEF_Z statistics rules; Z1 / R1 conventions):
  flip            = flipped_to_other ∧ coherent (rows with lo_model_unscorable are kept for the flip, dropped from Δ lo_model).
  Δ lo_model      = lo_model(edited) − lo_model(natural, same state); positive = toward the edited-in (other) candidate.
  reader shift    Δs_r = lo_toward_edit(edited) − lo_toward_edit(natural, same state, same reader, same read layer); follow = Δs_r > 0 (ties do not follow).
  read layer      per (reader, family) the lowest read-back layer ≥ the family's edit layer (ownership/mapping: 42 for an L38 edit; errors: 48 for the
                  L48 edit). A read-back below the edit layer cannot see the edit (block 42 is computed before block 48), so readers scored only at 42 on
                  the error read-backs are reported as not evaluable there (--allow-below-edit uses them anyway, flagged).
  fraction        of the reader's OWN natural separation (R1): sep_r = lo_own(nat A) + lo_own(nat B) (pair families only; |sep_r| < 1e-4 excluded);
                  frac_full = Δs_r / Δs_r(full swap, α 1, same state) for every family (secondary).
  ΔAUROC over dose (Z1-style, the Z4 cell variant): per family, flip ~ logistic(f_r) (f_r = Δs_r / sep_r for pair families, raw Δs_r for errors) vs the
                  dose-only reference P(flip) = training-fold flip rate of the entry's direction × α cell; 8 pair folds by seed, out-of-fold
                  predictions over every edited entry of the family (both doses, random pooled over k); paired pair-level bootstrap of the difference.
                  Per matrix row the pooled out-of-fold predictions are restricted to that direction's entries (both doses).
  random band     per (family, reader): follow rate under each of the K = 10 random directions (α 1) → p95 over directions, plus the pooled rate.
  rates           over states; pair-level bootstrap (resample pairs; errors: one state per item = its own pair), 95% percentile CI, n_boot resamples.
  Wilson CI       for the model flip rate (as the brief asks); the P3 gap also gets a paired pair-bootstrap CI.

Predictions (verbatim thresholds): P1 d_cm follow ≥ 0.75 for every reader (per family and pooled); P2 d_pw follow ≤ 0.60 for every lens reader AND
inside the random band (≤ p95 over the random directions) while the probe's d_pw follow ≥ 0.80 (per family and pooled); P3 some family with
flip(d_cm, α 1) ≤ flip(full, α 1) − 0.20. Reader differences on the d_cm and d_pw rows: Δwin ≥ 10 points with the paired CI excluding 0, or
ΔAUROC ≥ 0.05 with the paired CI excluding 0. Layer-48 clause: flip(d_cm, errors, α 1) ≥ 0.50. The decision rules are applied verbatim.

Outputs (results/g_agreement/w/w1/): w1.md (≤ 60 lines), matrix.csv (α 1, long format: one row per family × direction × column), matrix_alpha0.5.csv,
w1_summary.json, fig_matrix.png (heat map of the α-1 follow rates, rows direction × family, columns readers; the model flip rate as a separate
grey-scale first column), log.md (appended).

Run:  PYTHONPATH=. .venv/bin/python -m projects.g_agreement.w_analysis.w1_matrix --behaviour cache/g_agreement/w/s2_behaviour.jsonl \
          --lo cache/g_agreement/w/s3_lo.jsonl --out results/g_agreement/w/w1 --n-boot 1000 --seed 0
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.stats import wilson  # noqa: E402
from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.z1_intervention import analyze as Z  # noqa: E402  (folds, logistic / cell models, AUROC, paired gain; not modified)

READERS: Tuple[str, ...] = ("jlens", "olens", "nla", "skip_a", "probe")
LENS_READERS: Tuple[str, ...] = ("jlens", "olens", "nla", "skip_a")
PROBE = "probe"
MODEL = "model"
READER_LABELS = {"jlens": "J-lens", "olens": "Oracle lens", "nla": "NLA", "skip_a": "skip-lens A", "probe": "probe", MODEL: "model"}
FAMILIES: Tuple[str, ...] = ("ownership", "mapping", "errors")
EDIT_LAYER = {"ownership": 38, "mapping": 38, "errors": 48}
FAMILY_LABELS = {"ownership": "ownership L38", "mapping": "mapping L38", "errors": "errors L48"}
DIRECTIONS: Tuple[str, ...] = ("d_cm", "d_pw", "d_J", "d_res", "full", "random")
NATURAL, RANDOM, FULL, D_CM, D_PW = "natural", "random", "full", "d_cm", "d_pw"
PRIMARY_ALPHA, SECONDARY_ALPHA = 1.0, 0.5
P1_MIN, P2_READER_MAX, P2_PROBE_MIN, P3_GAP, L48_MIN = 0.75, 0.60, 0.80, 0.20, 0.50
DWIN_MARGIN, DAUROC_MARGIN = 0.10, 0.05
SEP_TOL = 1e-4
POOLED = "pooled"
DEFAULT_BEH = ROOT / "cache" / "g_agreement" / "w" / "s2_behaviour.jsonl"
DEFAULT_LO = ROOT / "cache" / "g_agreement" / "w" / "s3_lo.jsonl"
DEFAULT_OUT = ROOT / "results" / "g_agreement" / "w" / "w1"

State = Tuple[str, str]  # (pair_id, source)


# --------------------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------------------
@dataclass
class World:
    nat: Dict[State, dict]                              # the natural behaviour row per state
    edited: List[dict]                                  # every edited behaviour row
    family_of: Dict[str, str]                           # pair_id -> family
    readers: List[str] = field(default_factory=list)    # readers present in the LO file (matrix order)
    lo: Dict[Tuple[str, int, str], Optional[float]] = field(default_factory=dict)  # (reader, read_layer, entry_key) -> lo_toward_edit
    read_layer: Dict[Tuple[str, str], Optional[int]] = field(default_factory=dict)  # (reader, family) -> the read layer used (None = not evaluable)
    read_layer_notes: List[str] = field(default_factory=list)
    n_lo_rows: int = 0

    @property
    def states(self) -> List[State]:
        return sorted(self.nat)

    def other(self, st: State) -> State:
        return (st[0], "B" if st[1] == "A" else "A")

    def entries(self, family: str, direction: str, alpha: Optional[float] = None) -> List[dict]:
        return [r for r in self.edited if r["family"] == family and r["direction"] == direction and (alpha is None or float(r["alpha"]) == float(alpha))]

    # reader values -------------------------------------------------------------
    def value(self, reader: str, family: str, key: str) -> Optional[float]:
        L = self.read_layer.get((reader, family))
        return None if L is None else self.lo.get((reader, L, key))

    def nat_value(self, reader: str, st: State) -> Optional[float]:
        r = self.nat[st]
        return self.value(reader, r["family"], r["key"])

    def shift(self, reader: str, row: dict) -> Optional[float]:
        """Δs_r = lo_toward_edit(edited) − lo_toward_edit(natural, same state)."""
        a = self.value(reader, row["family"], row["key"])
        b = self.nat_value(reader, (row["pair_id"], row["source"]))
        return None if a is None or b is None else float(a - b)

    def separation(self, reader: str, st: State) -> Optional[float]:
        """R1: sep_r = lo_own(nat A) + lo_own(nat B) = −lo_te(nat other) − lo_te(nat this); None for one-state families (errors)."""
        oth = self.other(st)
        if oth not in self.nat:
            return None
        a, b = self.nat_value(reader, st), self.nat_value(reader, oth)
        return None if a is None or b is None else float(-b - a)


def model_flip(r: Mapping[str, Any]) -> Optional[bool]:
    f = r.get("flipped_to_other")
    if f is None:
        return None
    coh = r.get("coherent")
    return bool(f) and (True if coh is None else bool(coh))


def model_lo(r: Mapping[str, Any]) -> Optional[float]:
    v = r.get("lo_model")
    if v is None or r.get("lo_model_unscorable"):
        return None
    v = float(v)
    return None if np.isnan(v) else v


def load_behaviour(path: Path | str) -> World:
    rows = U.load_jsonl(path)
    nat: Dict[State, dict] = {}
    edited: List[dict] = []
    fam_of: Dict[str, str] = {}
    for r in rows:
        if r.get("family") not in FAMILIES:
            continue
        fam_of[r["pair_id"]] = r["family"]
        if r["direction"] == NATURAL:
            nat[(r["pair_id"], r["source"])] = r
        elif r["direction"] in DIRECTIONS:
            edited.append(r)
    missing = sorted({(r["pair_id"], r["source"]) for r in edited} - set(nat))
    if missing:
        raise ValueError(f"{len(missing)} edited states have no natural row, e.g. {missing[:3]}")
    return World(nat=nat, edited=edited, family_of=fam_of)


def probe_value(row: Mapping[str, Any], probe_on: str) -> Optional[float]:
    """lo_toward_edit for the probe: 'auto' = the S3 choice (edited-site vectors when the probe's layer is the edit layer, else the read-back);
    'edited' / 'read' force score_edited / score_read (both are own − other, so the sign is flipped)."""
    if probe_on == "auto":
        return row.get("lo_toward_edit")
    v = row.get("score_edited" if probe_on == "edited" else "score_read")
    return None if v is None else -float(v)


def attach_lo(w: World, path: Path | str, *, probe_on: str = "auto", allow_below_edit: bool = False) -> World:
    """Reads the S3 rows of the S2 entries, picks one read layer per (reader, family) and stores lo_toward_edit per (reader, layer, entry key)."""
    keys = {r["key"] for r in w.edited} | {r["key"] for r in w.nat.values()}
    avail: Dict[Tuple[str, str], set] = defaultdict(set)
    n = 0
    for r in U.load_jsonl(path):
        rd, ek = r.get("reader"), r.get("entry_key")
        if rd not in READERS or ek not in keys or not str(r.get("unit", "S2")).startswith("S2"):
            continue
        fam = r.get("family") or w.family_of.get(ek.split("|")[0])
        L = int(r.get("read_layer") or 42)
        v = probe_value(r, probe_on) if rd == PROBE else r.get("lo_toward_edit")
        if v is not None:
            v = float(v)
            if np.isnan(v):
                v = None
        w.lo[(rd, L, ek)] = v
        avail[(rd, fam)].add(L)
        n += 1
    w.n_lo_rows = n
    present = sorted({rd for rd, _ in avail}, key=READERS.index)
    w.readers = present
    for rd in present:
        for fam in FAMILIES:
            Ls = sorted(avail.get((rd, fam), ()))
            ok = [L for L in Ls if L >= EDIT_LAYER[fam]]
            if ok:
                w.read_layer[(rd, fam)] = ok[0]
            elif Ls and allow_below_edit:
                w.read_layer[(rd, fam)] = Ls[-1]
                w.read_layer_notes.append(f"{rd}/{fam}: read layer {Ls[-1]} is BELOW the edit layer {EDIT_LAYER[fam]} (used because --allow-below-edit; the read-back cannot see the edit)")
            else:
                w.read_layer[(rd, fam)] = None
                w.read_layer_notes.append(f"{rd}/{fam}: not evaluable (read layers {Ls or 'none'}; edit layer {EDIT_LAYER[fam]})")
    return w


# --------------------------------------------------------------------------------------
# statistics helpers
# --------------------------------------------------------------------------------------
def boot_mean(vals_by_pair: Mapping[str, Sequence[float]], n_boot: int, seed: int) -> Tuple[float, float, float, int]:
    """mean over entries with a pair-level bootstrap CI; (mean, lo, hi, n)."""
    pids = sorted(p for p, v in vals_by_pair.items() if len(v) > 0)
    allv = [x for p in pids for x in vals_by_pair[p]]
    if not allv:
        return float("nan"), float("nan"), float("nan"), 0

    def stat(ps: Sequence[str]) -> float:
        v = [x for p in ps for x in vals_by_pair[p]]
        return float(np.mean(v)) if v else float("nan")

    est, lo, hi = U.pair_bootstrap_stat(pids, stat, n_boot=n_boot, seed=seed)
    return est, lo, hi, len(allv)


def _nanmedian(v: Sequence[float]) -> float:
    a = np.asarray([x for x in v if x is not None and not np.isnan(x)], dtype=float)
    return float(np.median(a)) if a.size else float("nan")


def rate_dict(r: U.Rate, prefix: str) -> dict:
    return {f"{prefix}_k": r.k, f"{prefix}_n": r.n, f"{prefix}": r.p, f"{prefix}_lo": r.lo, f"{prefix}_hi": r.hi, f"{prefix}_n_pairs": r.n_pairs}


def fmt_ci(x: float, lo: float, hi: float, nd: int = 2) -> str:
    """signed value with its CI; n/a when undefined (e.g. an AUROC on a row without flips)."""
    if x is None or np.isnan(x):
        return "n/a"
    return f"{x:+.{nd}f} [{lo:+.{nd}f}, {hi:+.{nd}f}]"


def fmt_rate(p: float, lo: float, hi: float) -> str:
    if p is None or np.isnan(p):
        return "n/a"
    lo, hi = max(float(lo), 0.0) + 0.0, min(float(hi), 1.0)  # clip; + 0.0 turns −0.0 into 0.0
    return f"{100 * p:.0f}% [{100 * lo:.0f}, {100 * hi:.0f}]"


# --------------------------------------------------------------------------------------
# the Z1-style ΔAUROC over the dose-only reference
# --------------------------------------------------------------------------------------
@dataclass
class Preds:
    """Out-of-fold predictions of one reader on one family's edited entries (every direction, both doses)."""
    keys: np.ndarray
    pair: np.ndarray
    direction: np.ndarray
    alpha: np.ndarray
    y: np.ndarray
    p_reader: np.ndarray
    p_dose: np.ndarray
    n_excluded_pairs: int


def reader_feature(w: World, reader: str, row: dict) -> Optional[float]:
    """f_r = Δs_r / sep_r for the pair families (|sep_r| < SEP_TOL excluded), raw Δs_r for errors."""
    ds = w.shift(reader, row)
    if ds is None:
        return None
    if row["family"] == "errors":
        return ds
    sep = w.separation(reader, (row["pair_id"], row["source"]))
    if sep is None or abs(sep) < SEP_TOL:
        return None
    return ds / sep


def dose_cell(r: Mapping[str, Any]) -> str:
    return f"{r['direction']}|{float(r['alpha'])}"


def oof_predictions(w: World, reader: str, family: str, fold_of: Mapping[str, int]) -> Optional[Preds]:
    rows = [r for r in w.edited if r["family"] == family]
    if not rows or w.read_layer.get((reader, family)) is None:
        return None
    y_all = np.array([bool(model_flip(r)) for r in rows])
    pair_all = np.array([r["pair_id"] for r in rows], dtype=object)
    cells = sorted({dose_cell(r) for r in rows})
    code = {c: float(i) for i, c in enumerate(cells)}
    x_dose = np.array([code[dose_cell(r)] for r in rows], dtype=float)
    folds = np.array([fold_of[p] for p in pair_all])
    p_dose = np.full(len(rows), np.nan)
    for k in sorted(set(folds.tolist())):
        tr, te = folds != k, folds == k
        p_dose[te] = Z.fit_cells(x_dose[tr], y_all[tr]).predict(x_dose[te])
    feat = [reader_feature(w, reader, r) for r in rows]
    keep = np.array([f is not None for f in feat])
    if not keep.any():
        return None
    x_r = np.array([f for f in feat if f is not None], dtype=float)
    y, pair, fo = y_all[keep], pair_all[keep], folds[keep]
    p_r = np.full(len(x_r), np.nan)
    for k in sorted(set(fo.tolist())):
        tr, te = fo != k, fo == k
        p_r[te] = Z.fit_logistic(x_r[tr], y[tr]).predict(x_r[te])
    excluded = len(set(pair_all.tolist())) - len(set(pair.tolist()))
    return Preds(keys=np.array([r["key"] for r, k in zip(rows, keep) if k], dtype=object), pair=pair,
                 direction=np.array([r["direction"] for r, k in zip(rows, keep) if k], dtype=object),
                 alpha=np.array([float(r["alpha"]) for r, k in zip(rows, keep) if k]), y=y, p_reader=p_r, p_dose=p_dose[keep], n_excluded_pairs=excluded)


def gain(pr: Optional[Preds], mask: Optional[np.ndarray], n_boot: int, seed: int) -> dict:
    empty = {"n_entries": 0, "n_pairs": 0, "n_flip": 0, "auroc_reader": float("nan"), "auroc_dose": float("nan"), "delta_auroc": float("nan"),
             "delta_lo95": float("nan"), "delta_hi95": float("nan"), "verdict": "n/a"}
    if pr is None:
        return empty
    m = np.ones(len(pr.y), dtype=bool) if mask is None else mask
    if m.sum() == 0:
        return empty
    rec = Z.paired_auroc_gain(pr.pair[m], pr.y[m], pr.p_reader[m], pr.p_dose[m], n_boot, seed)
    return {k: rec[k] for k in ("n_entries", "n_pairs", "n_flip", "auroc_reader", "auroc_dose", "delta_auroc", "delta_lo95", "delta_hi95", "verdict")}


def concat_preds(ps: Sequence[Optional[Preds]]) -> Optional[Preds]:
    ps = [p for p in ps if p is not None]
    if not ps:
        return None
    cat = lambda f: np.concatenate([getattr(p, f) for p in ps])  # noqa: E731
    return Preds(cat("keys"), cat("pair"), cat("direction"), cat("alpha"), cat("y"), cat("p_reader"), cat("p_dose"), sum(p.n_excluded_pairs for p in ps))


def paired_auroc_diff(pa: Preds, pb: Preds, direction: str, n_boot: int, seed: int) -> dict:
    """AUROC(reader a) − AUROC(reader b) on the entries of ``direction`` scored by both (paired pair bootstrap)."""
    ia = {k: i for i, k in enumerate(pa.keys.tolist()) if pa.direction[i] == direction}
    ib = {k: i for i, k in enumerate(pb.keys.tolist()) if pb.direction[i] == direction}
    common = sorted(set(ia) & set(ib))
    if not common:
        return {"n_entries": 0, "delta": float("nan"), "lo95": float("nan"), "hi95": float("nan")}
    a = np.array([ia[k] for k in common])
    b = np.array([ib[k] for k in common])
    y, pair, sa, sb = pa.y[a], pa.pair[a], pa.p_reader[a], pb.p_reader[b]
    est, vals = Z.pair_boot_values(pair, lambda idx: Z.auroc(sa[idx], y[idx]) - Z.auroc(sb[idx], y[idx]), n_boot, seed)
    v = vals[~np.isnan(vals)] if vals.size else vals
    lo, hi = (float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))) if v.size else (float("nan"), float("nan"))
    return {"n_entries": len(common), "delta": est, "lo95": lo, "hi95": hi}


def threshold_met(delta: float, lo: float, hi: float, margin: float) -> bool:
    return bool(not np.isnan(delta) and abs(delta) >= margin and not np.isnan(lo) and (lo > 0 or hi < 0))


# --------------------------------------------------------------------------------------
# the matrix
# --------------------------------------------------------------------------------------
def follow_flags(w: World, reader: str, rows: Sequence[dict]) -> List[Tuple[str, Optional[bool]]]:
    out = []
    for r in rows:
        ds = w.shift(reader, r)
        out.append((r["pair_id"], None if ds is None else ds > 0))
    return out


def flip_flags(rows: Sequence[dict]) -> List[Tuple[str, Optional[bool]]]:
    return [(r["pair_id"], model_flip(r)) for r in rows]


def model_cell(w: World, rows: Sequence[dict], n_boot: int, seed: int) -> dict:
    fl = flip_flags(rows)
    k = sum(1 for _, f in fl if f)
    n = sum(1 for _, f in fl if f is not None)
    p, lo, hi = wilson(k, n)
    pr = U.pair_rate(fl, n_boot=n_boot, seed=seed)
    dlo: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        a, b = model_lo(r), model_lo(w.nat[(r["pair_id"], r["source"])])
        if a is not None and b is not None:
            dlo[r["pair_id"]].append(a - b)
    m, mlo, mhi, nn = boot_mean(dlo, n_boot, seed)
    return {"flip_k": k, "flip_n": n, "flip": p, "flip_lo": lo, "flip_hi": hi, "flip_ci": "wilson", "flip_boot_lo": pr.lo, "flip_boot_hi": pr.hi,
            "n_incoherent": sum(1 for r in rows if r.get("coherent") is False), "dlo_mean": m, "dlo_lo": mlo, "dlo_hi": mhi, "dlo_n": nn,
            "n_states": len({(r["pair_id"], r["source"]) for r in rows}), "n_pairs": len({r["pair_id"] for r in rows})}


def reader_cell(w: World, reader: str, rows: Sequence[dict], n_boot: int, seed: int) -> dict:
    fr = U.pair_rate(follow_flags(w, reader, rows), n_boot=n_boot, seed=seed)
    fsep, ffull = [], []
    full_shift: Dict[State, Optional[float]] = {}
    for r in rows:
        ds = w.shift(reader, r)
        if ds is None:
            continue
        st = (r["pair_id"], r["source"])
        sep = w.separation(reader, st)
        if sep is not None and abs(sep) >= SEP_TOL:
            fsep.append(ds / sep)
        if st not in full_shift:
            fr_full = [x for x in w.entries(r["family"], FULL, PRIMARY_ALPHA) if (x["pair_id"], x["source"]) == st]
            full_shift[st] = w.shift(reader, fr_full[0]) if fr_full else None
        f = full_shift[st]
        if f is not None and abs(f) >= SEP_TOL:
            ffull.append(ds / f)
    return {**rate_dict(fr, "follow"), "follow_ci": "pair-bootstrap", "frac_sep_median": _nanmedian(fsep), "frac_sep_n": len(fsep),
            "frac_full_median": _nanmedian(ffull), "frac_full_n": len(ffull), "n_unscorable": sum(1 for _, f in follow_flags(w, reader, rows) if f is None)}


def random_band(w: World, reader: str, family: Optional[str], n_boot: int, seed: int) -> dict:
    """follow rate per random direction k (α 1) → p95 over the K directions, and the pooled rate; family None = pooled over families."""
    fams = FAMILIES if family is None else (family,)
    rows = [r for f in fams for r in w.entries(f, RANDOM, PRIMARY_ALPHA)]
    ks = sorted({int(r["k"]) for r in rows if r.get("k") is not None})
    per_k = []
    for k in ks:
        fl = follow_flags(w, reader, [r for r in rows if int(r["k"]) == k])
        num, den = sum(1 for _, f in fl if f), sum(1 for _, f in fl if f is not None)
        per_k.append(num / den if den else float("nan"))
    pooled = U.pair_rate(follow_flags(w, reader, rows), n_boot=n_boot, seed=seed)
    return {"random_k": ks, "random_per_k": per_k, "random_p95": Z.p95(per_k), "random_max": (float(np.nanmax(per_k)) if per_k and not np.all(np.isnan(per_k)) else float("nan")),
            **rate_dict(pooled, "random_pooled")}


def row_label(direction: str) -> str:
    return "random (K pooled)" if direction == RANDOM else direction


def build_matrix(w: World, alpha: float, n_boot: int, seed: int, preds: Mapping[Tuple[str, str], Optional[Preds]]) -> List[dict]:
    """Long-format rows: one per (family | pooled) × direction × column (model or reader)."""
    out: List[dict] = []
    scopes: List[Tuple[str, Sequence[str]]] = [(f, (f,)) for f in FAMILIES] + [(POOLED, FAMILIES)]
    for scope, fams in scopes:
        for d in DIRECTIONS:
            a = PRIMARY_ALPHA if d == RANDOM else alpha
            rows = [r for f in fams for r in w.entries(f, d, a)]
            if not rows:
                continue
            base = {"alpha": a, "family": scope, "edit_layer": (EDIT_LAYER[scope] if scope in EDIT_LAYER else "38/38/48"), "direction": d, "row": row_label(d)}
            out.append({**base, "column": MODEL, **model_cell(w, rows, n_boot, seed)})
            for rd in w.readers:
                evaluable = [f for f in fams if w.read_layer.get((rd, f)) is not None]
                if not evaluable:
                    out.append({**base, "column": rd, "read_layer": None, "follow": float("nan"), "note": "not evaluable"})
                    continue
                rws = [r for r in rows if r["family"] in evaluable]
                if scope == POOLED:
                    pr = concat_preds([preds.get((rd, f)) for f in evaluable])
                else:
                    pr = preds.get((rd, scope))
                mask = None if pr is None else (pr.direction == d)
                g = gain(pr, mask, n_boot, seed)
                out.append({**base, "column": rd, "read_layer": (w.read_layer[(rd, scope)] if scope in FAMILIES else "/".join(str(w.read_layer[(rd, f)]) for f in evaluable)),
                            **reader_cell(w, rd, rws, n_boot, seed), "dauroc": g["delta_auroc"], "dauroc_lo": g["delta_lo95"], "dauroc_hi": g["delta_hi95"],
                            "auroc_reader": g["auroc_reader"], "auroc_dose": g["auroc_dose"], "dauroc_n": g["n_entries"], "dauroc_verdict": g["verdict"],
                            "dauroc_doses": "0.5+1.0", "families_evaluable": "+".join(evaluable)})
    return out


def cell(matrix: Sequence[dict], family: str, direction: str, column: str) -> Optional[dict]:
    for r in matrix:
        if r["family"] == family and r["direction"] == direction and r["column"] == column:
            return r
    return None


# --------------------------------------------------------------------------------------
# predictions and decision rules
# --------------------------------------------------------------------------------------
def evaluate(w: World, matrix: Sequence[dict], bands: Mapping[Tuple[str, str], dict], n_boot: int, seed: int) -> dict:
    scopes = list(FAMILIES) + [POOLED]
    have_readers = bool(w.readers)
    # P1 ------------------------------------------------------------------------------
    p1_cells: Dict[str, Dict[str, Optional[bool]]] = {}
    p1_values: Dict[str, Dict[str, float]] = {}
    for rd in w.readers:
        p1_cells[rd], p1_values[rd] = {}, {}
        for sc in scopes:
            c = cell(matrix, sc, D_CM, rd)
            v = float("nan") if c is None else c["follow"]
            p1_values[rd][sc] = v
            p1_cells[rd][sc] = None if np.isnan(v) else bool(v >= P1_MIN)
    p1_eval = [b for d in p1_cells.values() for b in d.values() if b is not None]
    p1 = (all(p1_eval) if p1_eval else None) if have_readers else None
    p1_strict = all(cell(matrix, sc, D_CM, rd)["follow_lo"] >= P1_MIN for rd in w.readers for sc in scopes
                    if cell(matrix, sc, D_CM, rd) is not None and not np.isnan(cell(matrix, sc, D_CM, rd)["follow"])) if p1_eval else None
    # P2 ------------------------------------------------------------------------------
    p2_readers: Dict[str, Dict[str, Optional[dict]]] = {}
    for rd in w.readers:
        p2_readers[rd] = {}
        for sc in scopes:
            c = cell(matrix, sc, D_PW, rd)
            if c is None or np.isnan(c["follow"]):
                p2_readers[rd][sc] = None
                continue
            b = bands.get((rd, sc), {})
            p95 = b.get("random_p95", float("nan"))
            if rd == PROBE:
                p2_readers[rd][sc] = {"follow": c["follow"], "ok": bool(c["follow"] >= P2_PROBE_MIN), "random_p95": p95}
            else:
                inside = (not np.isnan(p95)) and c["follow"] <= p95
                p2_readers[rd][sc] = {"follow": c["follow"], "le_060": bool(c["follow"] <= P2_READER_MAX), "inside_band": bool(inside), "random_p95": p95,
                                      "ok": bool(c["follow"] <= P2_READER_MAX and inside)}
    lens_eval = [v["ok"] for rd in LENS_READERS for v in p2_readers.get(rd, {}).values() if v is not None]
    probe_eval = [v["ok"] for v in p2_readers.get(PROBE, {}).values() if v is not None]
    p2 = (all(lens_eval) and all(probe_eval)) if (lens_eval and probe_eval) else None
    # P3 ------------------------------------------------------------------------------
    p3_fams = {}
    for f in FAMILIES:
        a, b = cell(matrix, f, D_CM, MODEL), cell(matrix, f, FULL, MODEL)
        if a is None or b is None:
            continue
        d, lo, hi = U.pair_rate_diff(flip_flags(w.entries(f, D_CM, PRIMARY_ALPHA)), flip_flags(w.entries(f, FULL, PRIMARY_ALPHA)), n_boot=n_boot, seed=seed)
        p3_fams[f] = {"flip_d_cm": a["flip"], "flip_d_cm_ci": [a["flip_lo"], a["flip_hi"]], "flip_full": b["flip"], "flip_full_ci": [b["flip_lo"], b["flip_hi"]],
                      "gap": b["flip"] - a["flip"], "diff_d_cm_minus_full": d, "diff_ci": [lo, hi], "ok": bool(a["flip"] <= b["flip"] - P3_GAP)}
    p3 = any(v["ok"] for v in p3_fams.values()) if p3_fams else None
    # layer-48 clause -----------------------------------------------------------------
    e = cell(matrix, "errors", D_CM, MODEL)
    l48 = None if e is None else {"flip_d_cm_errors": e["flip"], "ci": [e["flip_lo"], e["flip_hi"]], "ge_050": bool(e["flip"] >= L48_MIN)}
    # "d_pw moves only the probe" on the errors family (the second decision rule), operationalised as P2's errors-family conditions
    err_pw = [v for rd in LENS_READERS for v in [p2_readers.get(rd, {}).get("errors")] if v is not None]
    err_probe = p2_readers.get(PROBE, {}).get("errors")
    dpw_only_probe = (all(v["ok"] for v in err_pw) and err_probe is not None and err_probe["ok"]) if (err_pw and err_probe) else None
    # headline (decision rules verbatim) --------------------------------------------
    rule = headline(p1, p2, p3, l48, dpw_only_probe)
    return {"P1": {"holds": p1, "strict_ci_lower": p1_strict, "threshold": P1_MIN, "cells": p1_cells, "follow": p1_values},
            "P2": {"holds": p2, "reader_max": P2_READER_MAX, "probe_min": P2_PROBE_MIN, "cells": p2_readers},
            "P3": {"holds": p3, "gap": P3_GAP, "families": p3_fams},
            "layer48_clause": l48, "d_pw_moves_only_probe_on_errors": dpw_only_probe, "headline": rule[0], "rule_applied": rule[1]}


def headline(p1: Optional[bool], p2: Optional[bool], p3: Optional[bool], l48: Optional[dict], dpw_only_probe: Optional[bool]) -> Tuple[str, str]:
    """The three decision rules of PREREG_WV applied verbatim; None = not evaluable (model-only mode or missing readers)."""
    if p1 is None:
        base = "P1 not evaluable (no reader rows): no headline yet; the model-side half of the matrix is reported."
        rule = "none (model-only)"
    elif p1 is False:
        base = "P1 fails: the class-mean hypothesis is wrong; the matrix is reported as is and the analysis stops."
        rule = "rule 3 (P1 fails)"
    elif p1 and p2 and p3:
        base = "readers read class-mean directions; the model uses more"
        rule = "rule 1 (P1, P2 and P3 hold)"
    else:
        base = f"P1 holds but not all of P2 ({p2}) and P3 ({p3}): no pre-registered headline applies; the matrix is reported."
        rule = "none (P1 holds, P2/P3 not all met)"
    tail = []
    if l48 is not None:
        if l48["ge_050"]:
            tail.append(f"Layer-48 clause: d_cm steering at 48 flips the model {100 * l48['flip_d_cm_errors']:.0f}% ≥ 50%"
                        + (" → the layer-48 claim is rewritten as 'the model's wrong answer is load-bearing along d_cm at layer 48 and the readers still miss it on natural states'."
                           if p1 and p2 and p3 else " (the rewrite applies only if P1–P3 all hold)."))
        else:
            tail.append(f"Layer-48 clause: d_cm steering at 48 flips the model {100 * l48['flip_d_cm_errors']:.0f}% < 50% → no rewrite of the layer-48 claim.")
            if dpw_only_probe:
                tail.append("Rule 2: d_cm steering at 48 does not flip the model and d_pw moves only the probe → withdraw the layer-48 'readers miss the model's errors' "
                            "claim; replace with 'no reader-independent linear method reads a load-bearing off-text answer at this site'.")
            elif dpw_only_probe is None:
                tail.append("Rule 2 ('d_pw moves only the probe') not evaluable without reader rows on the error read-backs.")
            else:
                tail.append("Rule 2 does not apply: on errors d_pw does not move only the probe.")
    return base + (" " + " ".join(tail) if tail else ""), rule


def reader_differences(w: World, matrix: Sequence[dict], preds: Mapping[Tuple[str, str], Optional[Preds]], n_boot: int, seed: int) -> List[dict]:
    """Pairwise reader differences on the d_cm and d_pw rows (α 1): Δwin = follow(a) − follow(b) (paired pair bootstrap) and ΔAUROC(a − b)."""
    out: List[dict] = []
    rds = list(w.readers)
    for sc in list(FAMILIES) + [POOLED]:
        fams = FAMILIES if sc == POOLED else (sc,)
        for d in (D_CM, D_PW):
            for i, a in enumerate(rds):
                for b in rds[i + 1:]:
                    ev = [f for f in fams if w.read_layer.get((a, f)) is not None and w.read_layer.get((b, f)) is not None]
                    if not ev:
                        continue
                    rows = [r for f in ev for r in w.entries(f, d, PRIMARY_ALPHA)]
                    dw, lo, hi = U.pair_rate_diff(follow_flags(w, a, rows), follow_flags(w, b, rows), n_boot=n_boot, seed=seed)
                    pa, pb = concat_preds([preds.get((a, f)) for f in ev]), concat_preds([preds.get((b, f)) for f in ev])
                    da = paired_auroc_diff(pa, pb, d, n_boot, seed) if pa is not None and pb is not None else {"n_entries": 0, "delta": float("nan"), "lo95": float("nan"), "hi95": float("nan")}
                    out.append({"family": sc, "direction": d, "reader_a": a, "reader_b": b, "families_evaluable": "+".join(ev), "n_entries": len(rows),
                                "dwin": dw, "dwin_lo": lo, "dwin_hi": hi, "dwin_met": threshold_met(dw, lo, hi, DWIN_MARGIN),
                                "dauroc": da["delta"], "dauroc_lo": da["lo95"], "dauroc_hi": da["hi95"], "dauroc_n": da["n_entries"],
                                "dauroc_met": threshold_met(da["delta"], da["lo95"], da["hi95"], DAUROC_MARGIN)})
    for r in out:
        r["met"] = bool(r["dwin_met"] or r["dauroc_met"])
    return out


# --------------------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------------------
def make_fig(path: Path, w: World, matrix: Sequence[dict]) -> None:
    plt = U.mpl()
    from matplotlib.colors import LinearSegmentedColormap

    readers = list(w.readers) or list(READERS)
    rows = [(d, f) for d in DIRECTIONS for f in FAMILIES if cell(matrix, f, d, MODEL) is not None]
    labels = [f"{row_label(d)} · {FAMILY_LABELS[f]}" for d, f in rows]
    flip = np.array([[cell(matrix, f, d, MODEL)["flip"]] for d, f in rows], dtype=float)
    fol = np.full((len(rows), len(readers)), np.nan)
    txt = [["" for _ in readers] for _ in rows]
    for i, (d, f) in enumerate(rows):
        for j, rd in enumerate(readers):
            c = cell(matrix, f, d, rd)
            if c is not None and not np.isnan(c.get("follow", float("nan"))):
                fol[i, j] = c["follow"]
                txt[i][j] = f"{100 * c['follow']:.0f}\n[{100 * c['follow_lo']:.0f}, {100 * c['follow_hi']:.0f}]"
            else:
                txt[i][j] = "n/a"
    H = 0.42 * len(rows) + 1.6
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(1.9 + 1.25 * len(readers), H), gridspec_kw={"width_ratios": [1, max(len(readers), 1)], "wspace": 0.04})
    greys = LinearSegmentedColormap.from_list("w1_grey", ["#fcfcfb", "#9a9892", "#2b2a28"])
    blues = LinearSegmentedColormap.from_list("w1_blue", U.SEQ_BLUE)
    im0 = ax0.imshow(flip, cmap=greys, vmin=0, vmax=1, aspect="auto")
    for i, (d, f) in enumerate(rows):
        c = cell(matrix, f, d, MODEL)
        dark = c["flip"] > 0.55
        ax0.text(0, i, f"{100 * c['flip']:.0f}\n[{100 * max(c['flip_lo'], 0.0) + 0.0:.0f}, {100 * min(c['flip_hi'], 1.0):.0f}]", ha="center", va="center", fontsize=7,
                 color=("#fcfcfb" if dark else U.INK))
    ax0.set_xticks([0])
    ax0.set_xticklabels(["model flip\n(Wilson 95%)"])
    ax0.set_yticks(range(len(rows)))
    ax0.set_yticklabels(labels)
    ax0.tick_params(length=0)
    for sp in ax0.spines.values():
        sp.set_visible(False)
    masked = np.ma.masked_invalid(fol)
    cm = blues.copy()
    cm = cm.with_extremes(bad="#eeede9")
    im1 = ax1.imshow(masked, cmap=cm, vmin=0, vmax=1, aspect="auto")
    for i in range(len(rows)):
        for j in range(len(readers)):
            v = fol[i, j]
            ax1.text(j, i, txt[i][j], ha="center", va="center", fontsize=7, color=("#fcfcfb" if (not np.isnan(v) and v > 0.6) else U.INK2 if np.isnan(v) else U.INK))
    ax1.set_xticks(range(len(readers)))
    ax1.set_xticklabels([READER_LABELS.get(r, r) for r in readers])
    ax1.set_yticks([])
    ax1.tick_params(length=0)
    for sp in ax1.spines.values():
        sp.set_visible(False)
    for i in range(1, len(rows)):  # a surface gap between direction blocks
        if rows[i][0] != rows[i - 1][0]:
            ax0.axhline(i - 0.5, color="#fcfcfb", lw=2)
            ax1.axhline(i - 0.5, color="#fcfcfb", lw=2)
    fig.subplots_adjust(right=0.86)
    cb = fig.colorbar(im1, cax=fig.add_axes([0.885, 0.52, 0.015, 0.33]))
    cb.set_label("reader follow rate (share of states, α 1)", fontsize=8)
    cb0 = fig.colorbar(im0, cax=fig.add_axes([0.885, 0.12, 0.015, 0.33]))
    cb0.set_label("model flip rate", fontsize=8)
    fig.suptitle("W1 — steering matrix at α 1: model flip (grey) and reader follow (blue) by direction × family" + ("" if w.readers else "  [model-only: reader rows pending]"),
                 fontsize=10, x=0.02, ha="left")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------------------
# write-up
# --------------------------------------------------------------------------------------
def _b(v: Optional[bool]) -> str:
    return "n/a" if v is None else ("TRUE" if v else "FALSE")


def write_md(path: Path, w: World, matrix: Sequence[dict], ev: dict, bands: Mapping[Tuple[str, str], dict], diffs: Sequence[dict], args: argparse.Namespace, wall_s: float) -> None:
    rds = list(w.readers)
    mode = "model-only (no --lo)" if not rds else f"readers {', '.join(READER_LABELS[r] for r in rds)}"
    L = [f"# W1 — steering matrix ({dt.datetime.now(dt.timezone.utc).date().isoformat()}; CPU only, 0 forward passes; {len(w.nat)} states, {len(w.edited)} edited decodes; "
         f"pair bootstrap {args.n_boot}, seed {args.seed}; {mode})", "",
         f"**HEADLINE ({ev['rule_applied']}): {ev['headline']}**", "",
         f"- P1 (d_cm follow ≥ {P1_MIN:.2f} for every reader, per family and pooled): **{_b(ev['P1']['holds'])}**"
         + (f" (strict, CI lower bound ≥ 0.75: {_b(ev['P1']['strict_ci_lower'])})" if rds else ""),
         f"- P2 (d_pw follow ≤ {P2_READER_MAX:.2f} for every lens reader AND ≤ the random p95, while the probe's d_pw follow ≥ {P2_PROBE_MIN:.2f}; per family and pooled): **{_b(ev['P2']['holds'])}**",
         f"- P3 (some family with flip(d_cm) ≤ flip(full) − {P3_GAP:.2f} at α 1): **{_b(ev['P3']['holds'])}** — "
         + "; ".join(f"{f}: d_cm {fmt_rate(v['flip_d_cm'], *v['flip_d_cm_ci'])} vs full {fmt_rate(v['flip_full'], *v['flip_full_ci'])}, "
                     f"Δ(d_cm − full) {100 * v['diff_d_cm_minus_full']:+.0f} [{100 * v['diff_ci'][0]:+.0f}, {100 * v['diff_ci'][1]:+.0f}]" for f, v in ev["P3"]["families"].items()),
         (f"- Layer-48 clause (flip(d_cm, errors, α 1) ≥ 0.50): **{_b(ev['layer48_clause']['ge_050'])}** ({fmt_rate(ev['layer48_clause']['flip_d_cm_errors'], *ev['layer48_clause']['ci'])})"
          if ev["layer48_clause"] else "- Layer-48 clause: n/a (no error rows)"), ""]
    # matrix table (α 1) ---------------------------------------------------------------
    hdr = "| direction | family | model flip (Wilson) | mean Δ lo_model [pair boot] |" + "".join(f" {READER_LABELS[r]} follow [CI] / frac / ΔAUROC |" for r in rds)
    L += [f"## Matrix at α 1 (follow = reader shift toward the edited-in candidate; frac = median fraction of own natural separation (errors: of the full-swap shift); ΔAUROC over the dose-only cell model, both doses)",
          hdr, "|" + "---|" * (4 + len(rds))]
    for sc in list(FAMILIES) + [POOLED]:
        for d in DIRECTIONS:
            m = cell(matrix, sc, d, MODEL)
            if m is None:
                continue
            cells = []
            for rd in rds:
                c = cell(matrix, sc, d, rd)
                if c is None or np.isnan(c.get("follow", float("nan"))):
                    cells.append("n/a")
                    continue
                frac = c["frac_sep_median"] if sc != "errors" and not np.isnan(c["frac_sep_median"]) else c["frac_full_median"]
                cells.append(f"{fmt_rate(c['follow'], c['follow_lo'], c['follow_hi'])} / {frac:+.2f} / {fmt_ci(c['dauroc'], c['dauroc_lo'], c['dauroc_hi'])}")
            L.append(f"| {row_label(d)} | {FAMILY_LABELS.get(sc, sc)} | {fmt_rate(m['flip'], m['flip_lo'], m['flip_hi'])} ({m['flip_k']}/{m['flip_n']}) | "
                     f"{m['dlo_mean']:+.2f} [{m['dlo_lo']:+.2f}, {m['dlo_hi']:+.2f}] |" + "".join(f" {c} |" for c in cells))
    if rds:
        L.append("")
        L.append("Random band (follow rate under the K random directions, α 1: p95 over directions / pooled rate): " + "; ".join(
            f"{READER_LABELS[rd]} " + ", ".join(f"{sc} {100 * bands[(rd, sc)]['random_p95']:.0f}/{100 * bands[(rd, sc)]['random_pooled']:.0f}"
                                               for sc in list(FAMILIES) + [POOLED] if (rd, sc) in bands and not np.isnan(bands[(rd, sc)]["random_p95"])) for rd in rds) + ".")
        met = [r for r in diffs if r["met"]]
        met_pooled = [r for r in met if r["family"] == POOLED]
        L.append(f"Reader differences on the d_cm / d_pw rows (Δwin ≥ 10 points with paired CI excluding 0, or ΔAUROC ≥ 0.05 with CI excluding 0): {len(met)} of {len(diffs)} "
                 f"comparisons meet it ({len(met_pooled)} pooled; all in reader_differences.csv)"
                 + (". Pooled: " + "; ".join(f"{r['direction']} {READER_LABELS[r['reader_a']]}−{READER_LABELS[r['reader_b']]} Δwin {100 * r['dwin']:+.0f} [{100 * r['dwin_lo']:+.0f}, {100 * r['dwin_hi']:+.0f}], "
                                            f"ΔAUROC {fmt_ci(r['dauroc'], r['dauroc_lo'], r['dauroc_hi'])}" for r in met_pooled) if met_pooled else "") + ".")
    L.append("")
    L.append("Notes: flip = flipped_to_other ∧ coherent; Δ lo_model and reader shifts are relative to the state's natural row; rates over states with pair-level bootstrap "
             "(errors: one state per item); the α 0.5 table is matrix_alpha0.5.csv; per-row ΔAUROC restricts each family's out-of-fold predictions to that direction's entries (both doses).")
    if w.read_layer_notes:
        L.append("Read layers: " + "; ".join(w.read_layer_notes) + ".")
    L.append(f"Command: `PYTHONPATH=. .venv/bin/python -m projects.g_agreement.w_analysis.w1_matrix --behaviour {args.behaviour} "
             + (f"--lo {args.lo} " if args.lo else "") + f"--out {args.out} --n-boot {args.n_boot} --seed {args.seed}` (wall {wall_s:.1f} s).")
    text = "\n".join(L) + "\n"
    if text.count("\n") > 60:
        U.log(f"[w1] note: w1.md has {text.count(chr(10))} lines (> 60)")
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------------------
def run(args: argparse.Namespace) -> dict:
    t0 = time.time()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    w = load_behaviour(args.behaviour)
    if args.lo:
        attach_lo(w, args.lo, probe_on=args.probe_on, allow_below_edit=args.allow_below_edit)
        U.log(f"[w1] readers present: {w.readers}; LO rows used {w.n_lo_rows}; read layers {dict(w.read_layer)}")
    else:
        U.log("[w1] model-only mode (no --lo)")
    fold_of = Z.assign_folds(list(w.family_of), w.family_of, args.folds, args.seed)
    preds = {(rd, f): oof_predictions(w, rd, f, fold_of) for rd in w.readers for f in FAMILIES}
    matrix = build_matrix(w, PRIMARY_ALPHA, args.n_boot, args.seed, preds)
    matrix_05 = build_matrix(w, SECONDARY_ALPHA, args.n_boot, args.seed, preds)
    bands = {(rd, sc): random_band(w, rd, None if sc == POOLED else sc, args.n_boot, args.seed) for rd in w.readers for sc in list(FAMILIES) + [POOLED]
             if sc == POOLED or w.read_layer.get((rd, sc)) is not None}
    for r in matrix + matrix_05:  # the band next to every reader cell
        b = bands.get((r["column"], r["family"]))
        if b:
            r.update({k: b[k] for k in ("random_p95", "random_max", "random_pooled", "random_pooled_lo", "random_pooled_hi")})
    ev = evaluate(w, matrix, bands, args.n_boot, args.seed)
    diffs = reader_differences(w, matrix, preds, args.n_boot, args.seed)
    fam_gain = {rd: {sc: gain(concat_preds([preds.get((rd, f)) for f in FAMILIES]) if sc == POOLED else preds.get((rd, sc)), None, args.n_boot, args.seed)
                     for sc in list(FAMILIES) + [POOLED]} for rd in w.readers}
    U.write_csv(out / "matrix.csv", matrix)
    U.write_csv(out / "matrix_alpha0.5.csv", matrix_05)
    if diffs:
        U.write_csv(out / "reader_differences.csv", diffs)
    wall = time.time() - t0
    summary = {"date": dt.datetime.now(dt.timezone.utc).isoformat(), "behaviour": str(args.behaviour), "lo": (str(args.lo) if args.lo else None), "mode": ("readers" if w.readers else "model-only"),
               "n_states": len(w.nat), "n_edited": len(w.edited), "n_lo_rows": w.n_lo_rows, "readers": w.readers, "read_layer": {f"{rd}|{f}": L for (rd, f), L in w.read_layer.items()},
               "read_layer_notes": w.read_layer_notes, "n_boot": args.n_boot, "seed": args.seed, "folds": args.folds, "probe_on": args.probe_on,
               "thresholds": {"P1_min": P1_MIN, "P2_reader_max": P2_READER_MAX, "P2_probe_min": P2_PROBE_MIN, "P3_gap": P3_GAP, "L48_min": L48_MIN, "dwin": DWIN_MARGIN, "dauroc": DAUROC_MARGIN},
               **ev, "random_band": {f"{rd}|{sc}": b for (rd, sc), b in bands.items()}, "gain_over_dose_per_family": fam_gain,
               "reader_differences_met": [r for r in diffs if r["met"]], "n_reader_differences": len(diffs), "wall_s": round(wall, 1)}
    U.write_json(out / "w1_summary.json", summary)
    if not args.no_fig:
        make_fig(out / "fig_matrix.png", w, matrix)
    write_md(out / "w1.md", w, matrix, ev, bands, diffs, args, wall)
    with open(out / "log.md", "a", encoding="utf-8") as f:
        f.write(f"- {summary['date']} w1_matrix: mode {summary['mode']}, {len(w.nat)} states, {len(w.edited)} edited rows, LO rows {w.n_lo_rows}, readers {w.readers}, "
                f"n_boot {args.n_boot}, seed {args.seed}, folds {args.folds}, wall {wall:.1f} s; P1 {ev['P1']['holds']}, P2 {ev['P2']['holds']}, P3 {ev['P3']['holds']}, "
                f"L48 {None if ev['layer48_clause'] is None else ev['layer48_clause']['ge_050']}; headline: {ev['headline']}\n")
    U.log(f"[w1] HEADLINE ({ev['rule_applied']}): {ev['headline']}")
    U.log(f"[w1] P1 {ev['P1']['holds']}  P2 {ev['P2']['holds']}  P3 {ev['P3']['holds']}  layer-48 clause {None if ev['layer48_clause'] is None else ev['layer48_clause']['ge_050']}  (wall {wall:.1f} s) → {out}")
    return {"summary": summary, "matrix": matrix, "matrix_alpha0.5": matrix_05, "differences": diffs}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="W1 steering matrix (CPU).")
    ap.add_argument("--behaviour", default=str(DEFAULT_BEH), help="S2 behaviour jsonl")
    ap.add_argument("--lo", default=None, help="S3 reader LO jsonl (omit for the model-only half)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--folds", type=int, default=8, help="pair folds for the out-of-fold ΔAUROC")
    ap.add_argument("--probe-on", choices=("auto", "edited", "read"), default="auto", help="which probe score to use (auto = S3's lo_toward_edit)")
    ap.add_argument("--allow-below-edit", action="store_true", help="use a read layer below the edit layer when no higher one exists (flagged; uninformative)")
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
