"""Z1 — intervention-response benchmark (BRIEF_Z.md §Z1). CPU only; zero forward passes; reads the frozen X2 artefacts.

Inputs (never modified):
  cache/g_agreement/x/x2_behaviour.jsonl   one row per entry: pair_id, family, source, site ∈ {nat,S1,S2,S3}, alpha, condition,
                                           flipped_to_other, coherent, lo_model = lp(first token B) − lp(first token A) (toward other)
  cache/g_agreement/x/x2_lo.jsonl          one row per (reader, entry): lo_toward_other (= lp(B) − lp(A) in the reader's native format)

Per planted entry and reader r:  s_r = lo_toward_other;  Δs_r = s_r(edited) − s_r(natural, same source state);
  f_r = Δs_r / sep_r with sep_r = the reader's natural separation of the pair (x_friday_r1.separation: lo_own(A) + lo_own(B),
  the same number for both states; pairs with sep_r == 0 are excluded and counted);  Δ_model = lo_model(edited) − lo_model(natural);
  flip = flipped_to_other ∧ coherent.

E1  logistic flip ~ f_r (one feature + intercept) on S2 ∪ S3 planted entries; 8 pair-family folds (pairs → folds by seed 0, stratified by
    family; all entries of a pair in one fold); held-out (out-of-fold) AUROC per reader with pair-bootstrap CI; dose-only reference
    flip ~ α with the same folds; S1 false-positive rate at α ≤ 3 (no flips there) using each fold's Youden threshold from its training folds.
E2  Spearman / Pearson of Δs_r vs Δ_model per site per reader (pair-bootstrap CI) and the partial correlations after regressing both on
    dose (α as a factor = per-α means removed); "adds information beyond the dose" if the partial CI excludes 0.
E3  held-out family (train ownership → test mapping and the reverse) and held-out site (S2 → S3, S3 → S2): AUROC and correlations on the
    test set.
E4  per-pair AUROC (within pair, over its S2 ∪ S3 planted entries, both sources) and per-pair Spearman; paired reader differences with
    pair-bootstrap 95% CI and Wilcoxon signed-rank; THRESHOLD: CI excludes 0 AND |Δ| ≥ 0.05 AUROC / ≥ 0.10 correlation; if no pair of
    readers meets it, TOST (90% CI inside ±0.05 / ±0.10) → "interchangeable within margin" else "not established".
E5  permutation null: Δs_r shuffled across edited entries within (pair, site), 200 permutations; p95 of AUROC and correlations.

Outputs: results/g_agreement/z1/{z1.md, z1_per_pair.csv, z1_summary.json, fig_main.png, log.md}.
Run:  PYTHONPATH=. .venv/bin/python projects/g_agreement/z1_intervention/analyze.py --n-boot 1000 --n-perm 200 --folds 8 --seed 0

Z4 MODE (BRIEF_Z deviation 2026-10-09 (4): E1–E5 rerun on the Z4 edits) — selected by --natural-behaviour:
  --behaviour cache/g_agreement/z/z4_behaviour.jsonl --lo cache/g_agreement/z/z4_lo.jsonl
  --natural-behaviour cache/g_agreement/x/x2_behaviour.jsonl --natural-lo cache/g_agreement/x/x2_lo.jsonl [--arms single,pair2,all_except]
  Entries = the Z4 rows of the chosen arms (default single, pair2, all_except); restore rows are excluded (determinism check) and
  rand_single rows are the separate control (the analogue of X2's inert S1: the folds' models are applied to them for a false-positive
  rate, and E2 reports them as their own group). The natural reference is the X2 natural row of the same (pair, source) (site 'nat'):
  Δ_model and Δs_r are taken relative to it, f_r = Δs_r / sep_r with the X2 sep_r (|sep_r| < 1e-4 excluded). "Site" groups become
  arms; the dose factor is arm × α (partial correlations are residualised on it, and the dose-only reference predicts the flip from
  the training folds' flip rate of each arm × α cell — the categorical analogue of flip ~ α; rand_single is dose-matched to single|1.0).
  Folds by pair family as before; same thresholds. Default output results/g_agreement/z4/z1_on_z4/.
  Without these flags the X2 analysis is unchanged (byte-identical numbers).

GAIN OVER DOSE (BRIEF_Z deviation 2026-10-09 "Z1 reporting") — add --gain-over-dose to either mode: writes ONLY gain_over_dose.{csv,md} into
  --out (ΔAUROC of each reader over the dose-only reference on the same entries, E1's out-of-fold / E3's transfer predictions, paired
  pair-level bootstrap; "beats dose" only if the 95% CI lies above 0). E1–E5 are not rerun and their files are not touched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy import stats as sps

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement import x_friday_r1 as R  # noqa: E402  (World loader + separation(); not modified)

READERS: Tuple[str, ...] = ("olens", "nla", "jlens")
READER_LABELS = dict(R.READER_LABELS)
DOSE = "dose"
READER_LABELS[DOSE] = "dose-only (flip ~ α)"
SITES: Tuple[str, ...] = ("S2", "S3", "S1")
TRAIN_SITES: Tuple[str, ...] = ("S2", "S3")
FAMILIES: Tuple[str, ...] = ("ownership", "mapping")
AUROC_SETS: Dict[str, Tuple[str, ...]] = {"S2+S3": TRAIN_SITES, "S2": ("S2",), "S3": ("S3",)}
READER_PAIRS: Tuple[Tuple[str, str], ...] = (("olens", "nla"), ("olens", "jlens"), ("nla", "jlens"))
S1_MAX_ALPHA = 3.0
MARGIN_AUROC, MARGIN_CORR = 0.05, 0.10
DESCRIPTIVE_ALPHA = 0.5  # the one S2/S3 dose where the flip is not determined by α (46% flip); descriptive, not pre-registered
DEFAULT_BEH = ROOT / "cache" / "g_agreement" / "x" / "x2_behaviour.jsonl"
DEFAULT_LO = ROOT / "cache" / "g_agreement" / "x" / "x2_lo.jsonl"
DEFAULT_OUT = ROOT / "results" / "g_agreement" / "z1"
DEFAULT_OUT_Z4 = ROOT / "results" / "g_agreement" / "z4" / "z1_on_z4"
Z4_ARMS_DEFAULT: Tuple[str, ...] = ("single", "pair2", "all_except")
Z4_CONTROL_ARM = "rand_single"           # reported separately (false-positive control, own E2 group)
Z4_EXCLUDED_ARMS: Tuple[str, ...] = ("restore",)  # determinism check only
Z4_ALLOWED_ARMS: Tuple[str, ...] = ("single", "pair2", "all_except")
Z4_CONTROL_DOSE = "single|1.0"           # rand_single is a ‖Δ(i)‖-matched single-position edit at α 1
LOGIT_C = 1e4  # essentially unpenalised 1-D logistic (sklearn needs a finite C)
# "sep_r = 0" is evaluated up to float residual: the Oracle lens LO is bf16-quantised (steps ≥ 1/16 at |x| ≥ 1), so a natural
# separation of 4e-7 (pair xmap-16) is a tie whose float32 residual survived; 1e-4 is far below any bf16 step and below the
# genuine 1e-3 near-ties of NLA / J-lens, which stay in. Both counts (literal == 0 and |sep| < tol) are reported.
SEP_TIE_TOL = 1e-4


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--beh", "--behaviour", dest="beh", default=str(DEFAULT_BEH), help="behaviour jsonl (X2, or the Z4 file in Z4 mode)")
    ap.add_argument("--lo", default=str(DEFAULT_LO), help="reader LO jsonl of those entries")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--n-perm", type=int, default=200)
    ap.add_argument("--folds", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-fig", action="store_true")
    ap.add_argument("--natural-behaviour", default=None, help="Z4 mode: behaviour jsonl holding the natural rows (X2's; site 'nat')")
    ap.add_argument("--natural-lo", default=None, help="Z4 mode: reader LO jsonl of the natural rows (X2's)")
    ap.add_argument("--arms", "--sites", dest="arms", default=None, help=f"Z4 mode: comma-separated edit arms (default {','.join(Z4_ARMS_DEFAULT)})")
    ap.add_argument("--gain-over-dose", action="store_true",
                    help="write ONLY gain_over_dose.{csv,md} (reader ΔAUROC over the dose-only reference, paired pair bootstrap) into --out; "
                         "the E1–E5 outputs are not recomputed or touched (BRIEF_Z deviation 2026-10-09 'Z1 reporting')")
    a = ap.parse_args(argv)
    if not a.gain_over_dose:  # the recorded args of the E1–E5 run stay exactly as before
        delattr(a, "gain_over_dose")
    if a.natural_behaviour is None:
        if a.natural_lo is not None or a.arms is not None:
            ap.error("--natural-lo / --arms apply to the Z4 mode, which is selected by --natural-behaviour")
        for k in ("natural_behaviour", "natural_lo", "arms"):  # X2 mode: the recorded args stay exactly as before
            delattr(a, k)
        return a
    if a.natural_lo is None:
        ap.error("--natural-behaviour needs --natural-lo")
    arms = tuple(x.strip() for x in (",".join(Z4_ARMS_DEFAULT) if a.arms is None else a.arms).split(",") if x.strip())
    bad = [x for x in arms if x not in Z4_ALLOWED_ARMS]
    if bad or not arms or len(set(arms)) != len(arms):
        ap.error(f"--arms must be distinct values from {Z4_ALLOWED_ARMS} (rand_single is the control, restore is excluded); got {arms}")
    a.arms = ",".join(arms)
    if a.out == str(DEFAULT_OUT):
        a.out = str(DEFAULT_OUT_Z4)
    return a


# --------------------------------------------------------------------------------------
# design: the X2 sites, or the Z4 arms (BRIEF_Z deviation 2026-10-09 (4))
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Design:
    name: str
    sites: Tuple[str, ...]                    # every group in the table (E2 / E5-corr loop)
    train_sites: Tuple[str, ...]              # E1 primary set, E4
    auroc_sets: Dict[str, Tuple[str, ...]]    # E1 sets (the first is the primary)
    primary: str
    fp_site: str                              # inert / control group: false-positive rate of the folds' models
    fp_alpha_max: Optional[float]
    fp_key: str
    fp_flips_key: str
    descriptive_alpha: float
    site_transfers: Tuple[Tuple[str, str], ...]
    dose_label: str
    unit: str                                 # "site" | "arm"
    md_max_lines: int


X2_DESIGN = Design(name="X2", sites=SITES, train_sites=TRAIN_SITES, auroc_sets=AUROC_SETS, primary="S2+S3", fp_site="S1", fp_alpha_max=S1_MAX_ALPHA,
                   fp_key="s1_false_positive", fp_flips_key="n_actual_flips_at_alpha_le_3", descriptive_alpha=DESCRIPTIVE_ALPHA,
                   site_transfers=(("S2", "S3"), ("S3", "S2")), dose_label="dose-only (flip ~ α)", unit="site", md_max_lines=50)


def z4_design(arms: Sequence[str]) -> Design:
    train = tuple(arms)
    primary = "+".join(train)
    sets: Dict[str, Tuple[str, ...]] = {primary: train}
    if len(train) > 1:
        sets.update({a: (a,) for a in train})
    return Design(name="Z4", sites=train + (Z4_CONTROL_ARM,), train_sites=train, auroc_sets=sets, primary=primary, fp_site=Z4_CONTROL_ARM,
                  fp_alpha_max=None, fp_key="rand_single_false_positive", fp_flips_key="n_actual_flips", descriptive_alpha=1.0,
                  site_transfers=tuple((a, b) for a in train for b in train if a != b), dose_label="dose-only (flip ~ arm × α cell rate)",
                  unit="arm", md_max_lines=64)


def z4_dose_level(r: Mapping[str, Any]) -> str:
    """The Z4 dose factor arm × α; rand_single is dose-matched to the single arm at α 1."""
    if r["site"] == Z4_CONTROL_ARM:
        return Z4_CONTROL_DOSE
    return f"{r['site']}|{float(r['alpha'])}"


def load_z4_world(beh_path: Path | str, lo_path: Path | str, nat_beh_path: Path | str, nat_lo_path: Path | str,
                  arms: Sequence[str]) -> Tuple[R.World, Dict[str, Any]]:
    """A World whose planted entries are the Z4 rows of ``arms`` + rand_single (site := arm, condition := 'planted') and whose
    natural rows are the X2 natural rows of the same pairs (site 'nat'); reader LO merged from both files. Same checks as
    x_friday_r1.load_world (unique keys, both natural states per pair, mirrored candidates)."""
    z4 = U.load_jsonl(beh_path)
    if not z4:
        raise U.AnalysisError(f"no Z4 behaviour rows in {beh_path}")
    keep = set(arms) | {Z4_CONTROL_ARM}
    counts_all = dict(sorted(Counter(r["condition"] for r in z4).items()))
    rows = [dict(r, site=r["condition"], z4_condition=r["condition"], condition="planted") for r in z4 if r["condition"] in keep]
    pairs = sorted({r["pair_id"] for r in rows})
    nat_rows = [r for r in U.load_jsonl(nat_beh_path) if r["condition"] == "natural" and r["pair_id"] in set(pairs)]
    beh = nat_rows + rows
    by_key = {r["key"]: r for r in beh}
    if len(by_key) != len(beh):
        raise U.AnalysisError("duplicate behaviour keys across the Z4 and natural rows")
    items = sorted({(r["pair_id"], r["source"]) for r in beh})
    nat = {(r["pair_id"], r["source"]): r for r in nat_rows}
    for p in pairs:
        a, b = nat.get((p, "A")), nat.get((p, "B"))
        if a is None or b is None:
            raise U.AnalysisError(f"pair {p}: missing a natural state in {nat_beh_path}")
        if a["cand_A"] != b["cand_B"] or a["cand_B"] != b["cand_A"]:
            raise U.AnalysisError(f"pair {p}: candidates are not mirrored across the two states")
    for r in rows:
        n0 = nat[(r["pair_id"], r["source"])]
        if (r.get("cand_A"), r.get("cand_B")) != (n0["cand_A"], n0["cand_B"]):
            raise U.AnalysisError(f"{r['key']}: candidates differ from the natural row of the same state")
    grp: Dict[Tuple[str, Tuple[str, str], str], List[dict]] = defaultdict(list)
    for r in rows:
        grp[(r["site"], (r["pair_id"], r["source"]), r["condition"])].append(r)
    for k in grp:
        grp[k].sort(key=lambda r: (float(r["alpha"]), r["key"]))
    lo: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for path in (nat_lo_path, lo_path):
        for r in U.load_jsonl(path):
            ek = r.get("entry_key") or r["key"].split("|", 1)[1]
            if ek in by_key:
                lo[r["reader"]][ek] = None if r.get("unscorable") else (None if r.get("lo_toward_other") is None else float(r["lo_toward_other"]))
    readers = [rd for rd in R.READERS if rd in lo]
    sites = [s for s in tuple(arms) + (Z4_CONTROL_ARM,) if any(r["site"] == s for r in rows)]
    info = {"z4_condition_counts_in_file": counts_all, "kept_arms": list(arms), "control_arm": Z4_CONTROL_ARM,
            "excluded_conditions": {c: n for c, n in counts_all.items() if c not in keep}, "n_pairs": len(pairs), "n_natural_rows": len(nat_rows),
            "natural_reference": str(nat_beh_path), "natural_lo": str(nat_lo_path)}
    return R.World(beh, by_key, items, nat, dict(grp), dict(lo), readers, sites), info


# --------------------------------------------------------------------------------------
# per-entry table
# --------------------------------------------------------------------------------------
@dataclass
class Table:
    """One row per planted entry (all sites); reader columns are nan where the reader is unscorable or the pair is excluded (sep_r == 0)."""
    key: np.ndarray
    pair: np.ndarray
    family: np.ndarray
    source: np.ndarray
    site: np.ndarray
    alpha: np.ndarray
    flip: np.ndarray
    dm: np.ndarray
    ds: Dict[str, np.ndarray]
    f: Dict[str, np.ndarray]
    sep: Dict[str, Dict[str, float]]
    excluded: Dict[str, List[str]] = field(default_factory=dict)    # |sep_r| < SEP_TIE_TOL (quantised tie)
    misordered: Dict[str, List[str]] = field(default_factory=dict)  # sep_r < 0 (the reader misorders the natural pair; f_r flips sign)
    fam_of: Dict[str, str] = field(default_factory=dict)
    dose: Optional[np.ndarray] = None  # Z4 mode: the dose factor (arm × α labels); None in X2 mode (the factor is α)

    @property
    def pairs(self) -> List[str]:
        return sorted(set(self.pair.tolist()))


def build_table(w: R.World, readers: Sequence[str], sites: Sequence[str] = SITES, dose_of: Optional[Callable[[dict], str]] = None) -> Table:
    """``sites`` = the groups kept; ``dose_of`` (Z4 mode) labels each entry's dose factor (rows are then also ordered by key)."""
    rows = [r for r in w.beh if r["condition"] == "planted" and r["site"] in sites]
    if dose_of is None:
        rows.sort(key=lambda r: (r["site"], r["pair_id"], r["source"], float(r["alpha"])))
    else:
        rows.sort(key=lambda r: (r["site"], r["pair_id"], r["source"], float(r["alpha"]), r["key"]))
    sep: Dict[str, Dict[str, float]] = {}
    excluded: Dict[str, List[str]] = {}
    misordered: Dict[str, List[str]] = {}
    for rd in readers:
        s_item = R.separation(w, rd)
        sep[rd] = {}
        for (p, src), v in s_item.items():
            if src == "A" and v is not None:  # same number for both states
                sep[rd][p] = float(v)
        excluded[rd] = sorted(p for p, v in sep[rd].items() if abs(v) < SEP_TIE_TOL)
        misordered[rd] = sorted(p for p, v in sep[rd].items() if v <= -SEP_TIE_TOL)
    keep: List[dict] = []
    dm: List[float] = []
    for r in rows:
        it = (r["pair_id"], r["source"])
        v, n0 = w.value(R.MODEL, r), w.nat_value(R.MODEL, it)
        if v is None or n0 is None:
            continue
        keep.append(r)
        dm.append(v - n0)
    ds = {rd: np.full(len(keep), np.nan) for rd in readers}
    f = {rd: np.full(len(keep), np.nan) for rd in readers}
    for i, r in enumerate(keep):
        it = (r["pair_id"], r["source"])
        for rd in readers:
            v, n0 = w.value(rd, r), w.nat_value(rd, it)
            if v is None or n0 is None:
                continue
            ds[rd][i] = v - n0
            s = sep[rd].get(r["pair_id"])
            if s is not None and abs(s) >= SEP_TIE_TOL:
                f[rd][i] = (v - n0) / s
    fam_of = {r["pair_id"]: r["family"] for r in keep}
    return Table(
        key=np.array([r["key"] for r in keep]), pair=np.array([r["pair_id"] for r in keep]), family=np.array([r["family"] for r in keep]),
        source=np.array([r["source"] for r in keep]), site=np.array([r["site"] for r in keep]),
        alpha=np.array([float(r["alpha"]) for r in keep]), flip=np.array([bool(r["flipped_to_other"]) and bool(r.get("coherent", True)) for r in keep]),
        dm=np.array(dm, dtype=float), ds=ds, f=f, sep=sep, excluded=excluded, misordered=misordered, fam_of=fam_of,
        dose=None if dose_of is None else np.array([dose_of(r) for r in keep], dtype=object))


@dataclass
class Sub:
    """A selection of entries for one scorer (a reader, or the dose-only reference whose feature is α)."""
    pair: np.ndarray
    family: np.ndarray
    site: np.ndarray
    alpha: np.ndarray
    x: np.ndarray    # the logistic feature: f_r, or α for the dose-only model
    ds: np.ndarray   # Δs_r (nan for the dose-only model)
    dm: np.ndarray   # Δ_model
    y: np.ndarray    # flip
    dose: Optional[np.ndarray] = None  # Z4 mode: dose-factor labels (arm × α); None → the factor is α
    categorical: bool = False          # x is a dose-factor code (Z4 dose-only reference): fit per-cell rates, not a logistic

    def __len__(self) -> int:
        return int(self.pair.size)

    @property
    def group(self) -> np.ndarray:
        return np.char.add(np.char.add(self.pair.astype(str), "|"), self.site.astype(str))

    @property
    def factor(self) -> np.ndarray:
        """the dose factor partial correlations are residualised on: α (X2) or arm × α (Z4)."""
        return self.alpha if self.dose is None else self.dose

    def take(self, idx: np.ndarray) -> "Sub":
        return Sub(self.pair[idx], self.family[idx], self.site[idx], self.alpha[idx], self.x[idx], self.ds[idx], self.dm[idx], self.y[idx],
                   None if self.dose is None else self.dose[idx], self.categorical)

    def with_x(self, x: np.ndarray, ds: Optional[np.ndarray] = None) -> "Sub":
        return Sub(self.pair, self.family, self.site, self.alpha, x, self.ds if ds is None else ds, self.dm, self.y, self.dose, self.categorical)


def subset(t: Table, reader: Optional[str], sites: Sequence[str], families: Optional[Sequence[str]] = None,
           alpha_max: Optional[float] = None, alphas: Optional[Sequence[float]] = None) -> Sub:
    m = np.isin(t.site, list(sites))
    if families is not None:
        m &= np.isin(t.family, list(families))
    if alpha_max is not None:
        m &= t.alpha <= alpha_max
    if alphas is not None:
        m &= np.isin(t.alpha, list(alphas))
    categorical = False
    if reader is None or reader == DOSE:
        if t.dose is None:
            x, ds = t.alpha, np.full(t.alpha.shape, np.nan)
        else:  # Z4: the dose factor's level code (consistent across subsets: codes from the full table's sorted levels)
            levels = {lev: float(i) for i, lev in enumerate(sorted(set(t.dose.tolist())))}
            x, ds = np.array([levels[v] for v in t.dose], dtype=float), np.full(t.alpha.shape, np.nan)
            categorical = True
    else:
        x, ds = t.f[reader], t.ds[reader]
        m &= ~np.isnan(x)
    return Sub(t.pair[m], t.family[m], t.site[m], t.alpha[m], x[m].astype(float), ds[m].astype(float), t.dm[m], t.flip[m],
               None if t.dose is None else t.dose[m], categorical)


# --------------------------------------------------------------------------------------
# folds, logistic, AUROC, correlations
# --------------------------------------------------------------------------------------
def assign_folds(pairs: Iterable[str], fam_of: Mapping[str, str], n_folds: int, seed: int) -> Dict[str, int]:
    """pairs → folds, stratified by family, all entries of a pair share the fold (the caller keys entries by pair)."""
    rng = np.random.default_rng(seed)
    out: Dict[str, int] = {}
    pairs = sorted(set(pairs))
    for fam in sorted({fam_of[p] for p in pairs}):
        ps = [p for p in pairs if fam_of[p] == fam]
        perm = rng.permutation(len(ps))
        for i, j in enumerate(perm):
            out[ps[j]] = i % n_folds
    return out


@dataclass
class Logit1D:
    """flip ~ sigmoid(w·z + b), z = (x − mu) / sd. Degenerate (w = 0) when the training labels are constant."""
    w: float
    b: float
    mu: float
    sd: float

    def predict(self, x: np.ndarray) -> np.ndarray:
        z = (np.asarray(x, dtype=float) - self.mu) / self.sd
        return 1.0 / (1.0 + np.exp(-np.clip(self.w * z + self.b, -500, 500)))

    def threshold_x(self, p: float) -> float:
        """the feature value at which the predicted probability equals p (nan when w == 0)."""
        if self.w == 0 or not (0 < p < 1):
            return float("nan")
        return float(self.mu + self.sd * (np.log(p / (1 - p)) - self.b) / self.w)


def fit_logistic(x: np.ndarray, y: np.ndarray) -> Logit1D:
    from sklearn.linear_model import LogisticRegression

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=bool)
    mu = float(x.mean()) if x.size else 0.0
    sd = float(x.std()) if x.size else 1.0
    sd = sd if sd > 0 else 1.0
    if y.size == 0 or y.all() or (~y).all():
        p = float(np.clip(y.mean() if y.size else 0.5, 1e-6, 1 - 1e-6))
        return Logit1D(0.0, float(np.log(p / (1 - p))), mu, sd)
    z = (x - mu) / sd
    clf = LogisticRegression(C=LOGIT_C, max_iter=5000, tol=1e-8)
    clf.fit(z[:, None], y.astype(int))
    return Logit1D(float(clf.coef_[0, 0]), float(clf.intercept_[0]), mu, sd)


@dataclass
class CellModel:
    """Z4 dose-only reference: P(flip) = the training entries' flip rate in the entry's dose cell (arm × α code); an unseen cell
    gets the overall training rate. ``w`` is nan (no slope)."""
    rates: Dict[float, float]
    overall: float
    w: float = float("nan")

    def predict(self, x: np.ndarray) -> np.ndarray:
        return np.array([self.rates.get(float(v), self.overall) for v in np.asarray(x, dtype=float)], dtype=float)

    def threshold_x(self, p: float) -> float:
        return float("nan")


def fit_cells(x: np.ndarray, y: np.ndarray) -> CellModel:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=bool)
    rates = {float(v): float(y[x == v].mean()) for v in np.unique(x)}
    return CellModel(rates, float(y.mean()) if y.size else 0.5)


def fit_model(x: np.ndarray, y: np.ndarray, categorical: bool = False):
    """the 1-D logistic (readers; X2 dose-only on α) or the per-cell rate model (Z4 dose-only on arm × α)."""
    return fit_cells(x, y) if categorical else fit_logistic(x, y)


def auroc(scores: np.ndarray, y: np.ndarray) -> float:
    """Mann–Whitney AUROC (ties = ½); nan if one class is missing."""
    y = np.asarray(y, dtype=bool)
    s = np.asarray(scores, dtype=float)
    n1 = int(y.sum())
    n0 = int(y.size - n1)
    if n1 == 0 or n0 == 0 or np.isnan(s).any():
        return float("nan")
    r = sps.rankdata(s)
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def youden_threshold(p: np.ndarray, y: np.ndarray) -> float:
    """probability threshold maximising tpr − fpr on (p, y); positive = p ≥ threshold. nan if one class is missing."""
    from sklearn.metrics import roc_curve

    y = np.asarray(y, dtype=bool)
    if y.all() or (~y).all():
        return float("nan")
    fpr, tpr, thr = roc_curve(y.astype(int), p)
    j = tpr - fpr
    i = int(np.argmax(j[1:]) + 1) if thr.size > 1 else 0  # skip the +inf sentinel
    return float(thr[i])


def cv_oof(sub: Sub, fold_of: Mapping[str, int]) -> Tuple[np.ndarray, Dict[int, Logit1D], Dict[int, float]]:
    """out-of-fold predicted probabilities; per fold the fitted model and its Youden threshold on the training folds."""
    folds = np.array([fold_of[p] for p in sub.pair])
    oof = np.full(len(sub), np.nan)
    models: Dict[int, Logit1D] = {}
    thr: Dict[int, float] = {}
    for k in sorted(set(folds.tolist())):
        tr, te = folds != k, folds == k
        m = fit_model(sub.x[tr], sub.y[tr], sub.categorical)
        oof[te] = m.predict(sub.x[te])
        thr[k] = youden_threshold(m.predict(sub.x[tr]), sub.y[tr])
        models[k] = m
    return oof, models, thr


def corr(x: np.ndarray, y: np.ndarray, method: str) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    if x.size < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if method == "spearman":
            return float(sps.spearmanr(x, y).statistic)
        if method == "pearson":
            return float(sps.pearsonr(x, y).statistic)
    raise ValueError(method)


def residualise(v: np.ndarray, factor: np.ndarray) -> np.ndarray:
    """v minus its mean within each level of `factor` (= OLS residual on the factor's dummies with intercept)."""
    v = np.asarray(v, dtype=float)
    out = np.empty_like(v)
    for lev in np.unique(factor):
        m = factor == lev
        out[m] = v[m] - np.nanmean(v[m])
    return out


def partial_corr(x: np.ndarray, y: np.ndarray, factor: np.ndarray, method: str) -> float:
    return corr(residualise(x, factor), residualise(y, factor), method)


# --------------------------------------------------------------------------------------
# pair bootstrap and permutation helpers
# --------------------------------------------------------------------------------------
def pair_boot(pair: np.ndarray, stat: Callable[[np.ndarray], float], n_boot: int, seed: int) -> dict:
    """Resample pairs with replacement (every entry of a sampled pair, with repeats); stat(index_array) -> float.
    Returns the point estimate on the full index plus 95% and 90% percentile CIs."""
    pids = sorted(set(pair.tolist()))
    idx_of = {p: np.flatnonzero(pair == p) for p in pids}
    est = float(stat(np.arange(pair.size))) if pair.size else float("nan")
    if not pids or n_boot <= 0:
        return {"est": est, "lo95": float("nan"), "hi95": float("nan"), "lo90": float("nan"), "hi90": float("nan"), "n_pairs": len(pids)}
    rng = np.random.default_rng(seed)
    vals = np.empty(n_boot)
    for b in range(n_boot):
        sel = rng.integers(0, len(pids), len(pids))
        idx = np.concatenate([idx_of[pids[i]] for i in sel])
        vals[b] = stat(idx)
    if np.all(np.isnan(vals)):
        q = [float("nan")] * 4
    else:
        q = [float(np.nanquantile(vals, a)) for a in (0.025, 0.975, 0.05, 0.95)]
    return {"est": est, "lo95": q[0], "hi95": q[1], "lo90": q[2], "hi90": q[3], "n_pairs": len(pids)}


def permute_within_group(x: np.ndarray, group: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = np.array(x, dtype=float, copy=True)
    for g in np.unique(group):
        idx = np.flatnonzero(group == g)
        out[idx] = x[idx[rng.permutation(idx.size)]]
    return out


def p95(vals: Sequence[float]) -> float:
    v = np.asarray([x for x in vals if x is not None and not np.isnan(x)], dtype=float)
    return float(np.quantile(v, 0.95)) if v.size else float("nan")


# --------------------------------------------------------------------------------------
# E4 helpers: per-pair metrics, paired differences, threshold rule, TOST
# --------------------------------------------------------------------------------------
def per_pair_metrics(sub: Sub) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for p in sorted(set(sub.pair.tolist())):
        idx = np.flatnonzero(sub.pair == p)
        out[p] = {"auroc": auroc(sub.x[idx], sub.y[idx]), "spearman": corr(sub.ds[idx], sub.dm[idx], "spearman"),
                  "n": int(idx.size), "n_flip": int(sub.y[idx].sum())}
    return out


def threshold_rule(mean: float, lo95: float, hi95: float, margin: float) -> bool:
    """pre-registered: the 95% CI of the paired difference excludes 0 AND |Δ| ≥ margin."""
    if any(np.isnan(v) for v in (mean, lo95, hi95)):
        return False
    return bool((lo95 > 0 or hi95 < 0) and abs(mean) >= margin)


def tost_pass(lo90: float, hi90: float, margin: float) -> bool:
    """equivalence at α = 0.05 by two one-sided tests: the 90% CI lies inside (−margin, margin)."""
    if np.isnan(lo90) or np.isnan(hi90):
        return False
    return bool(lo90 > -margin and hi90 < margin)


def paired_difference(d_by_pair: Mapping[str, float], margin: float, n_boot: int, seed: int) -> dict:
    """mean paired difference over pairs with pair-bootstrap 95% / 90% CIs, Wilcoxon signed-rank p, threshold flag, TOST flag."""
    pids = sorted(p for p, v in d_by_pair.items() if v is not None and not np.isnan(v))
    d = np.array([d_by_pair[p] for p in pids], dtype=float)
    if d.size == 0:
        return {"n_pairs": 0, "mean": float("nan"), "lo95": float("nan"), "hi95": float("nan"), "lo90": float("nan"), "hi90": float("nan"),
                "median": float("nan"), "wilcoxon_p": float("nan"), "meets_threshold": False, "tost_pass": False, "margin": margin}
    boot = pair_boot(np.array(pids), lambda idx: float(np.mean(d[idx])), n_boot, seed)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wp = float(sps.wilcoxon(d).pvalue) if np.any(d != 0) else float("nan")
    except ValueError:
        wp = float("nan")
    return {"n_pairs": int(d.size), "mean": boot["est"], "lo95": boot["lo95"], "hi95": boot["hi95"], "lo90": boot["lo90"], "hi90": boot["hi90"],
            "median": float(np.median(d)), "wilcoxon_p": wp, "margin": margin,
            "meets_threshold": threshold_rule(boot["est"], boot["lo95"], boot["hi95"], margin),
            "tost_pass": tost_pass(boot["lo90"], boot["hi90"], margin)}


def reader_differences(metrics: Mapping[str, Mapping[str, dict]], metric: str, margin: float, n_boot: int, seed: int) -> Dict[str, dict]:
    """metrics[reader][pair][metric] → one paired-difference record per reader pair (first − second)."""
    out: Dict[str, dict] = {}
    for a, b in READER_PAIRS:
        if a not in metrics or b not in metrics:
            continue
        common = sorted(set(metrics[a]) & set(metrics[b]))
        d = {p: metrics[a][p][metric] - metrics[b][p][metric] for p in common}
        out[f"{a}-{b}"] = paired_difference(d, margin, n_boot, seed)
    return out


def verdict_line(primary: Mapping[str, Mapping[str, dict]], heldout_family: Sequence[Mapping[str, Mapping[str, dict]]]) -> Tuple[str, dict]:
    """"readers separate on intervention prediction" if any E4 difference meets the threshold on S2 ∪ S3 or on a held-out family test;
    "do not separate" if none does and every S2 ∪ S3 paired difference (AUROC and correlation) passes TOST; else "undetermined"."""
    sep_primary = [f"{metric}:{k}" for metric, m in primary.items() for k, v in m.items() if v["meets_threshold"]]
    sep_family = sorted({f"{metric}:{k}" for fam in heldout_family for metric, m in fam.items() for k, v in m.items() if v["meets_threshold"]})
    all_tost = all(v["tost_pass"] for m in primary.values() for v in m.values()) and any(primary.values())
    if sep_primary or sep_family:
        v = "readers separate on intervention prediction"
    elif all_tost:
        v = "readers do not separate on intervention prediction (interchangeable within margin)"
    else:
        v = "undetermined"
    return v, {"threshold_met_primary": sep_primary, "threshold_met_heldout_family": sep_family, "equivalence_all_tost": bool(all_tost)}


# --------------------------------------------------------------------------------------
# main analysis
# --------------------------------------------------------------------------------------
def _nanmedian(v: Sequence[float]) -> float:
    a = np.asarray(v, dtype=float)
    return float("nan") if a.size == 0 or np.all(np.isnan(a)) else float(np.nanmedian(a))


def _fmt(b: Mapping[str, float], nd: int = 3) -> str:
    if b is None or np.isnan(b.get("est", np.nan)):
        return "n/a"
    return f"{b['est']:.{nd}f} [{b['lo95']:.{nd}f}, {b['hi95']:.{nd}f}]"


def run(args: argparse.Namespace) -> dict:
    t0 = time.time()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    nb, sd, nperm = args.n_boot, args.seed, args.n_perm
    z4_mode = getattr(args, "natural_behaviour", None) is not None
    z4_info: Dict[str, Any] = {}
    if z4_mode:
        D = z4_design(args.arms.split(","))
        w, z4_info = load_z4_world(args.beh, args.lo, args.natural_behaviour, args.natural_lo, D.train_sites)
        readers = [rd for rd in READERS if rd in w.readers]
        t = build_table(w, readers, sites=D.sites, dose_of=z4_dose_level)
    else:
        D = X2_DESIGN
        w = R.load_world(args.beh, args.lo)
        readers = [rd for rd in READERS if rd in w.readers]
        t = build_table(w, readers)
    SITES_, TRAIN_, PRIM = D.sites, D.train_sites, D.primary
    labels = dict(READER_LABELS)
    labels[DOSE] = D.dose_label
    pairs = t.pairs
    fold_of = assign_folds(pairs, t.fam_of, args.folds, sd)
    scorers = readers + [DOSE]
    summary: Dict[str, Any] = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "args": vars(args), "readers": readers, "n_pairs": len(pairs),
        "n_planted_entries": int(t.key.size), "n_entries_by_site": {s: int((t.site == s).sum()) for s in SITES_},
        "excluded_pairs_sep_zero": {rd: t.excluded[rd] for rd in readers}, "misordered_pairs_sep_negative": {rd: t.misordered[rd] for rd in readers},
        "sep_tie_tol": SEP_TIE_TOL, "excluded_pairs_sep_literal_zero": {rd: sorted(p for p, v in t.sep[rd].items() if v == 0.0) for rd in readers},
        "excluded_pairs_by_tolerance_only": {rd: sorted(p for p, v in t.sep[rd].items() if v != 0.0 and abs(v) < SEP_TIE_TOL) for rd in readers},
        "sep_by_reader_pair": {rd: t.sep[rd] for rd in readers},
        f"raw_f_auroc_{PRIM}_no_logistic": {rd: auroc(subset(t, rd, TRAIN_).x, subset(t, rd, TRAIN_).y) for rd in readers},
        "median_abs_sep": {rd: float(np.median(np.abs(list(t.sep[rd].values())))) for rd in readers},
        "folds": {"n_folds": args.folds, "seed": sd, "pair_to_fold": fold_of,
                  "fold_sizes_by_family": {fam: [sum(1 for p in pairs if fold_of[p] == k and t.fam_of[p] == fam) for k in range(args.folds)] for fam in FAMILIES}},
        "thresholds": {"auroc_margin": MARGIN_AUROC, "corr_margin": MARGIN_CORR, "s1_max_alpha": S1_MAX_ALPHA, "logistic_C": LOGIT_C},
    }
    if z4_mode:
        summary["design"] = {"mode": "Z4 (BRIEF_Z deviation 2026-10-09 (4))", "arms": list(TRAIN_), "groups": list(SITES_), "primary_set": PRIM,
                             "control": Z4_CONTROL_ARM, "excluded": list(Z4_EXCLUDED_ARMS), "dose_factor": "arm × α (rand_single := single|1.0)",
                             "dose_only_reference": "per-(arm × α) training-fold flip rate", "natural_reference": "X2 natural rows (site nat)",
                             "fp_set": D.fp_site, **z4_info}
        summary["n_entries_by_arm_alpha"] = {lev: int((t.dose == lev).sum()) for lev in sorted(set(t.dose.tolist()))}
        summary["n_entries_by_site_raw"] = {s: int((t.site == s).sum()) for s in SITES_}
    U.log(f"Z1: {len(pairs)} pairs, {t.key.size} planted entries; readers {readers}; excluded (sep==0) " +
          ", ".join(f"{rd}:{len(t.excluded[rd])}" for rd in readers) + "; misordered (sep<0) " + ", ".join(f"{rd}:{len(t.misordered[rd])}" for rd in readers))

    # ---------------- E1 ----------------
    desc_key = f"descriptive_alpha_{D.descriptive_alpha}"
    E1: Dict[str, Any] = {"sets": {}, D.fp_key: {}, desc_key: {}}
    oof_store: Dict[Tuple[str, str], Tuple[Sub, np.ndarray]] = {}
    for set_name, sites in D.auroc_sets.items():
        E1["sets"][set_name] = {}
        for sc in scorers:
            sub = subset(t, sc, sites)
            oof, models, thr = cv_oof(sub, fold_of)
            oof_store[(set_name, sc)] = (sub, oof)
            b = pair_boot(sub.pair, lambda idx: auroc(oof[idx], sub.y[idx]), nb, sd)
            rec = {"auroc": b, "n_entries": len(sub), "n_flip": int(sub.y.sum()),
                   "fold_slopes": {k: m.w for k, m in models.items()},
                   "youden_p_threshold_by_fold": thr,
                   "youden_x_threshold_by_fold": {k: models[k].threshold_x(thr[k]) for k in models}}
            rec["youden_x_threshold_median"] = _nanmedian(list(rec["youden_x_threshold_by_fold"].values()))  # nan for the Z4 cell model (no x threshold)
            rec["youden_p_threshold_median"] = float(np.nanmedian(list(thr.values())))
            E1["sets"][set_name][sc] = rec
            if set_name == PRIM:
                s1 = subset(t, sc, (D.fp_site,), alpha_max=D.fp_alpha_max)
                pred = np.array([models[fold_of[p]].predict(np.array([x]))[0] >= thr[fold_of[p]] for p, x in zip(s1.pair, s1.x)], dtype=bool)
                rate = U.pair_rate(list(zip(s1.pair.tolist(), pred.tolist())), n_boot=nb, seed=sd)
                E1[D.fp_key][sc] = {"fpr": rate.as_dict(), "n_entries": len(s1), D.fp_flips_key: int(s1.y.sum()),
                                    "by_alpha": {str(a): float(pred[s1.alpha == a].mean()) for a in sorted(set(s1.alpha.tolist()))}}
                if z4_mode:  # the control's actual flip rate, for reading the predicted-flip rate
                    E1[D.fp_key][sc]["actual_flip_rate"] = float(s1.y.mean()) if len(s1) else float("nan")
                m05 = sub.alpha == D.descriptive_alpha
                sub05, oof05 = sub.take(np.flatnonzero(m05)), oof[m05]
                E1[desc_key][sc] = {"auroc": pair_boot(sub05.pair, lambda idx: auroc(oof05[idx], sub05.y[idx]), nb, sd),
                                    "n_entries": len(sub05), "n_flip": int(sub05.y.sum())}
    U.log(f"E1 AUROC {PRIM}: " + "; ".join(f"{sc} {_fmt(E1['sets'][PRIM][sc]['auroc'])}" for sc in scorers))

    # ---------------- E2 ----------------
    E2: Dict[str, Any] = {}
    for site in SITES_:
        E2[site] = {}
        for rd in readers:
            sub = subset(t, rd, (site,))
            rec: Dict[str, Any] = {"n_entries": len(sub), "alphas": sorted(set(sub.alpha.tolist()))}
            for method in ("spearman", "pearson"):
                rec[method] = pair_boot(sub.pair, lambda idx, m=method: corr(sub.ds[idx], sub.dm[idx], m), nb, sd)
                rec[f"partial_{method}"] = pair_boot(sub.pair, lambda idx, m=method: partial_corr(sub.ds[idx], sub.dm[idx], sub.factor[idx], m), nb, sd)
                pb = rec[f"partial_{method}"]
                rec[f"partial_{method}_ci_excludes_0"] = bool(not np.isnan(pb["lo95"]) and (pb["lo95"] > 0 or pb["hi95"] < 0))
            E2[site][rd] = rec
        U.log(f"E2 {site}: " + "; ".join(f"{rd} ρ {_fmt(E2[site][rd]['spearman'], 2)} partial {_fmt(E2[site][rd]['partial_spearman'], 2)}" for rd in readers))

    # ---------------- E3 ----------------
    def transfer(sub_tr: Sub, sub_te: Sub) -> dict:
        m = fit_model(sub_tr.x, sub_tr.y, sub_tr.categorical)
        p = m.predict(sub_te.x)
        rec = {"auroc": pair_boot(sub_te.pair, lambda idx: auroc(p[idx], sub_te.y[idx]), nb, sd), "slope": m.w,
               "n_train": len(sub_tr), "n_test": len(sub_te), "n_flip_test": int(sub_te.y.sum())}
        if not np.all(np.isnan(sub_te.ds)):
            rec["spearman"] = pair_boot(sub_te.pair, lambda idx: corr(sub_te.ds[idx], sub_te.dm[idx], "spearman"), nb, sd)
            rec["partial_spearman"] = pair_boot(sub_te.pair, lambda idx: partial_corr(sub_te.ds[idx], sub_te.dm[idx], sub_te.factor[idx], "spearman"), nb, sd)
        return rec

    E3: Dict[str, Any] = {"family": {}, "site": {}}
    for fam_tr, fam_te in ((FAMILIES[0], FAMILIES[1]), (FAMILIES[1], FAMILIES[0])):
        name = f"{fam_tr}->{fam_te}"
        E3["family"][name] = {sc: transfer(subset(t, sc, TRAIN_, families=(fam_tr,)), subset(t, sc, TRAIN_, families=(fam_te,))) for sc in scorers}
    for s_tr, s_te in D.site_transfers:
        name = f"{s_tr}->{s_te}"
        E3["site"][name] = {sc: transfer(subset(t, sc, (s_tr,)), subset(t, sc, (s_te,))) for sc in scorers}
    for kind in ("family", "site"):
        for name, recs in E3[kind].items():
            U.log(f"E3 {name}: " + "; ".join(f"{sc} AUROC {_fmt(recs[sc]['auroc'])}" for sc in scorers))

    # ---------------- E4 ----------------
    E4: Dict[str, Any] = {}
    e4_sets = {PRIM: None, f"{PRIM} mapping (held out from ownership)": ("mapping",), f"{PRIM} ownership (held out from mapping)": ("ownership",)}
    per_pair_all: Dict[str, Dict[str, dict]] = {}
    for set_name, fams in e4_sets.items():
        metrics = {rd: per_pair_metrics(subset(t, rd, TRAIN_, families=fams)) for rd in readers}
        if fams is None:
            per_pair_all = metrics
        rec: Dict[str, Any] = {"per_reader_mean": {}, "auroc_diff": reader_differences(metrics, "auroc", MARGIN_AUROC, nb, sd),
                               "spearman_diff": reader_differences(metrics, "spearman", MARGIN_CORR, nb, sd)}
        for rd in readers:
            pids = np.array(sorted(metrics[rd]))
            au = np.array([metrics[rd][p]["auroc"] for p in pids])
            spv = np.array([metrics[rd][p]["spearman"] for p in pids])
            rec["per_reader_mean"][rd] = {
                "auroc": pair_boot(pids, lambda idx: float(np.nanmean(au[idx])), nb, sd), "spearman": pair_boot(pids, lambda idx: float(np.nanmean(spv[idx])), nb, sd),
                "n_pairs": int(pids.size), "n_pairs_auroc_defined": int((~np.isnan(au)).sum()), "n_pairs_spearman_defined": int((~np.isnan(spv)).sum())}
        E4[set_name] = rec
        U.log(f"E4 {set_name}: " + "; ".join(f"{k} ΔAUROC {v['mean']:+.3f} [{v['lo95']:+.3f}, {v['hi95']:+.3f}] p={v['wilcoxon_p']:.2g} "
                                             f"{'THRESHOLD' if v['meets_threshold'] else ('tost-pass' if v['tost_pass'] else 'tost-fail')}" for k, v in rec["auroc_diff"].items()))
        U.log(f"   corr: " + "; ".join(f"{k} Δρ {v['mean']:+.3f} [{v['lo95']:+.3f}, {v['hi95']:+.3f}] p={v['wilcoxon_p']:.2g} "
                                      f"{'THRESHOLD' if v['meets_threshold'] else ('tost-pass' if v['tost_pass'] else 'tost-fail')}" for k, v in rec["spearman_diff"].items()))

    # ---------------- E5 ----------------
    E5: Dict[str, Any] = {"n_perm": nperm, "shuffle": "Δs_r (equivalently f_r) permuted across planted entries within (pair, site)", "auroc": {}, "corr": {}, "per_pair": {}}
    rng = np.random.default_rng(sd + 1)
    for set_name, sites in D.auroc_sets.items():
        E5["auroc"][set_name] = {}
        for rd in readers:
            sub, _ = oof_store[(set_name, rd)]
            vals = []
            for _ in range(nperm):
                xp = permute_within_group(sub.x, sub.group, rng)
                ps = sub.with_x(xp)
                oof_p, _, _ = cv_oof(ps, fold_of)
                vals.append(auroc(oof_p, ps.y))
            E5["auroc"][set_name][rd] = {"p95": p95(vals), "p50": float(np.nanmedian(vals)), "max": float(np.nanmax(vals))}
    for site in SITES_:
        E5["corr"][site] = {}
        for rd in readers:
            sub = subset(t, rd, (site,))
            vals: Dict[str, List[float]] = defaultdict(list)
            for _ in range(nperm):
                dsp = permute_within_group(sub.ds, sub.group, rng)
                for method in ("spearman", "pearson"):
                    vals[method].append(corr(dsp, sub.dm, method))
                    vals[f"partial_{method}"].append(partial_corr(dsp, sub.dm, sub.factor, method))
            E5["corr"][site][rd] = {k: {"p95": p95(v), "p05": float(np.nanquantile(v, 0.05))} for k, v in vals.items()}
    for rd in readers:  # null for the E4 per-pair means (S2 ∪ S3)
        sub = subset(t, rd, TRAIN_)
        au_vals, sp_vals = [], []
        for _ in range(nperm):
            xp = permute_within_group(sub.x, sub.group, rng)
            dsp = permute_within_group(sub.ds, sub.group, rng)
            ps = sub.with_x(xp, dsp)
            m = per_pair_metrics(ps)
            au_vals.append(float(np.nanmean([v["auroc"] for v in m.values()])))
            sp_vals.append(float(np.nanmean([v["spearman"] for v in m.values()])))
        E5["per_pair"][rd] = {"mean_auroc_p95": p95(au_vals), "mean_spearman_p95": p95(sp_vals)}
    U.log(f"E5 null p95 AUROC {PRIM}: " + "; ".join(f"{rd} {E5['auroc'][PRIM][rd]['p95']:.3f}" for rd in readers))

    # ---------------- verdict ----------------
    primary = {"auroc": E4[PRIM]["auroc_diff"], "spearman": E4[PRIM]["spearman_diff"]}
    heldout = [{"auroc": E4[k]["auroc_diff"], "spearman": E4[k]["spearman_diff"]} for k in e4_sets if k != PRIM]
    verdict, vdetail = verdict_line(primary, heldout)
    summary.update({"E1": E1, "E2": E2, "E3": E3, "E4": E4, "E5": E5, "verdict": verdict, "verdict_detail": vdetail,
                    "wall_s": round(time.time() - t0, 1)})
    if z4_mode:
        summary["rand_single_control"] = control_summary(t, readers, nb, sd)
    U.log(f"VERDICT: {verdict}")

    # ---------------- outputs ----------------
    rows = []
    for p in pairs:
        row: Dict[str, Any] = {"pair": p, "family": t.fam_of[p], "fold": fold_of[p],
                               "n_entries": per_pair_all[readers[0]][p]["n"] if p in per_pair_all[readers[0]] else int(np.isin(t.site, TRAIN_)[t.pair == p].sum()),
                               "n_flip": int(t.flip[(t.pair == p) & np.isin(t.site, TRAIN_)].sum())}
        for rd in readers:
            m = per_pair_all[rd].get(p)
            row[f"{rd}_sep"] = t.sep[rd].get(p)
            row[f"{rd}_excluded_sep_zero"] = p in t.excluded[rd]
            row[f"{rd}_auroc"] = None if m is None else m["auroc"]
            row[f"{rd}_spearman"] = None if m is None else m["spearman"]
        rows.append(row)
    U.write_csv(out_dir / "z1_per_pair.csv", rows)
    U.write_json(out_dir / "z1_summary.json", summary)
    write_md(out_dir / "z1.md", summary, readers, D, labels)
    if not args.no_fig:
        make_fig(out_dir / "fig_main.png", summary, t, readers, D, labels)
    z4_flags = (f"--behaviour {args.beh} --lo {args.lo} --natural-behaviour {args.natural_behaviour} --natural-lo {args.natural_lo} --arms {args.arms} "
                if z4_mode else "")
    with open(out_dir / "log.md", "a", encoding="utf-8") as f:
        f.write(f"- {summary['created_at']}  `PYTHONPATH=. .venv/bin/python projects/g_agreement/z1_intervention/analyze.py {z4_flags}"
                f"--n-boot {nb} --n-perm {nperm} --folds {args.folds} --seed {sd} --out {args.out}`  CPU only, 0 forward passes, "
                f"wall {summary['wall_s']} s; verdict: {verdict}\n")
    return summary


def control_summary(t: Table, readers: Sequence[str], nb: int, sd: int) -> Dict[str, Any]:
    """Z4 mode: the rand_single control on its own (not in E1/E3/E4): flip rate (Wilson), mean Δ_model and per-reader mean Δs_r / f_r
    with pair-bootstrap CIs."""
    m = t.site == Z4_CONTROL_ARM
    pair = t.pair[m]
    k, n = int(t.flip[m].sum()), int(m.sum())
    p, lo, hi = U.wilson(k, n)
    out: Dict[str, Any] = {"n_entries": n, "n_pairs": int(len(set(pair.tolist()))), "flip": {"k": k, "n": n, "p": p, "lo": lo, "hi": hi},
                           "d_model": pair_boot(pair, lambda idx: float(np.nanmean(t.dm[m][idx])) if idx.size else float("nan"), nb, sd), "readers": {}}
    for rd in readers:
        ds, f = t.ds[rd][m], t.f[rd][m]
        out["readers"][rd] = {"ds": pair_boot(pair, lambda idx, v=ds: float(np.nanmean(v[idx])) if np.any(~np.isnan(v[idx])) else float("nan"), nb, sd),
                              "f": pair_boot(pair, lambda idx, v=f: float(np.nanmean(v[idx])) if np.any(~np.isnan(v[idx])) else float("nan"), nb, sd),
                              "n_f": int((~np.isnan(f)).sum())}
    return out


# --------------------------------------------------------------------------------------
# z1.md (≤ 50 lines)
# --------------------------------------------------------------------------------------
def _flag(v: dict) -> str:
    return "THRESHOLD MET" if v["meets_threshold"] else ("TOST pass" if v["tost_pass"] else "TOST fail")


def write_md(path: Path, S: dict, readers: Sequence[str], D: Design = X2_DESIGN, labels: Optional[Mapping[str, str]] = None) -> None:
    """z1.md; the X2 text is unchanged, the Z4 mode swaps sites for arms, S1 for the rand_single control and α for arm × α."""
    RL = dict(READER_LABELS) if labels is None else dict(labels)
    x2 = D.name == "X2"
    PT = "S2 ∪ S3" if x2 else D.primary
    PRIM = D.primary
    others = [k for k in D.auroc_sets if k != PRIM]
    desc_key = f"descriptive_alpha_{D.descriptive_alpha}"
    E1, E2, E3, E4, E5 = S["E1"], S["E2"], S["E3"], S["E4"], S["E5"]
    L: List[str] = []
    L.append(f"# Z1 — intervention-response benchmark{'' if x2 else ' on the Z4 edits (BRIEF_Z deviation 2026-10-09 (4))'} ({S['created_at'][:10]}; CPU only, 0 forward passes; {S['n_pairs']} pairs, "
             f"{S['n_planted_entries']} {'planted' if x2 else 'edited'} entries; pair bootstrap {S['args']['n_boot']}, {S['args']['folds']} pair-family folds seed {S['args']['seed']}, "
             f"{E5['n_perm']} permutations)")
    L.append("")
    L.append(f"**VERDICT: {S['verdict']}.** Rule: any E4 paired difference meets the threshold (95% CI excludes 0 and |Δ| ≥ {MARGIN_AUROC} AUROC / "
             f"≥ {MARGIN_CORR} ρ) on {PT} or on a held-out family → separate; none and all six {PT} TOSTs pass (90% CI inside the margin) → "
             f"do not separate; else undetermined. Met: primary {S['verdict_detail']['threshold_met_primary'] or 'none'}; held-out family "
             f"{S['verdict_detail']['threshold_met_heldout_family'] or 'none'}; all TOST pass: {S['verdict_detail']['equivalence_all_tost']}.")
    exc = "; ".join(f"{RL[rd]} {len(S['excluded_pairs_sep_zero'][rd])} excluded (sep_r = 0), {len(S['misordered_pairs_sep_negative'][rd])} misordered (sep_r < 0)" for rd in readers)
    L.append(f"Scores: f_r = Δs_r / sep_r (fraction of the reader's own natural separation). Pairs: {exc}. Flip = flipped_to_other ∧ coherent.")
    if not x2:
        dz = S["design"]
        L.append(f"Z4 mode: entries = arms {', '.join(dz['arms'])} ({', '.join(f'{k} {v}' for k, v in S['n_entries_by_site'].items())}); natural reference = X2 natural rows "
                 f"(Δ_model, Δs_r relative to them; X2 sep_r); excluded from the reader analysis: {dz['excluded_conditions'] or 'none'}; rand_single = separate control; "
                 f"dose factor = arm × α ({len(S['n_entries_by_arm_alpha'])} cells); dose-only reference = training-fold flip rate per cell.")
    tol_only = {rd: v for rd, v in S["excluded_pairs_by_tolerance_only"].items() if v}
    L.append(f"Note ({S['created_at'][:10]}): 'sep_r = 0' is evaluated as |sep_r| < {S['sep_tie_tol']:g} (float residual of a bf16 tie; the Oracle lens LO is bf16-quantised). "
             f"Literal == 0 excludes {sum(len(v) for v in S['excluded_pairs_sep_literal_zero'].values())} pairs; the tolerance adds {tol_only or 'none'} "
             f"(sep {', '.join(f'{S['sep_by_reader_pair'][rd][p]:.1e}' for rd, ps in tol_only.items() for p in ps) or '—'}), without which that reader's f_r reaches ±3e5 and the 1-D logistic slope collapses "
             f"(raw rank AUROC of f_r without any fit, {PT}: " + ", ".join(f"{RL[rd]} {S[f'raw_f_auroc_{PRIM}_no_logistic'][rd]:.3f}" for rd in readers) + ").")
    L.append("")
    if x2:
        L.append("## E1 flip ~ f_r, out-of-fold AUROC [95% pair-bootstrap CI]; null p95 = E5 within-(pair,site) shuffle; S1 FPR at α ≤ 3 (Youden threshold from the training folds)")
        fp_head = "S1 FPR α ≤ 3 (actual flips)"
    else:
        L.append("## E1 flip ~ f_r, out-of-fold AUROC [95% pair-bootstrap CI]; null p95 = E5 within-(pair,arm) shuffle; rand_single predicted-flip rate (Youden threshold from the training folds)")
        fp_head = "rand_single predicted flips (actual flips)"
    L.append(f"| scorer | {PT} AUROC | null p95 | " + " | ".join(others) + (" | " if others else "") + f"{fp_head} | Youden threshold (median over folds: f_r, p) | "
             f"AUROC at α {D.descriptive_alpha:g} only (descriptive) |")
    L.append("|---|---|---|" + "---|" * len(others) + "---|---|---|")
    for sc in list(readers) + [DOSE]:
        r = E1["sets"][PRIM][sc]
        fp = E1[D.fp_key][sc]
        null = f"{E5['auroc'][PRIM][sc]['p95']:.3f}" if sc in E5["auroc"][PRIM] else "—"
        L.append(f"| {RL[sc]} | {_fmt(r['auroc'])} (n={r['n_entries']}, flips {r['n_flip']}) | {null} | " + "".join(f"{_fmt(E1['sets'][o][sc]['auroc'])} | " for o in others) +
                 f"{fp['fpr']['p']*100:.1f}% [{fp['fpr']['lo']*100:.1f}, {fp['fpr']['hi']*100:.1f}] ({fp[D.fp_flips_key]}/{fp['n_entries']}) | "
                 f"{r['youden_x_threshold_median']:.3f}, p {r['youden_p_threshold_median']:.2f} | {_fmt(E1[desc_key][sc]['auroc'])} |")
    L.append("")
    if x2:
        L.append("## E2 Δs_r vs Δ_model per site [95% CI]; partial = both residualised on α (factor); * = partial CI excludes 0; null p95 in parentheses")
        L.append("| site | reader | n | Spearman | partial Spearman | Pearson | partial Pearson |")
    else:
        L.append("## E2 Δs_r vs Δ_model per arm [95% CI]; partial = both residualised on arm × α (factor); * = partial CI excludes 0; null p95 in parentheses")
        L.append("| arm | reader | n | Spearman | partial Spearman | Pearson | partial Pearson |")
    L.append("|---|---|---|---|---|---|---|")
    for site in D.sites:
        for rd in readers:
            r, nz = E2[site][rd], E5["corr"][site][rd]
            L.append(f"| {site} | {RL[rd]} | {r['n_entries']} | {_fmt(r['spearman'])} ({nz['spearman']['p95']:.2f}) | "
                     f"{_fmt(r['partial_spearman'])}{'*' if r['partial_spearman_ci_excludes_0'] else ''} ({nz['partial_spearman']['p95']:.2f}) | "
                     f"{_fmt(r['pearson'])} ({nz['pearson']['p95']:.2f}) | {_fmt(r['partial_pearson'])}{'*' if r['partial_pearson_ci_excludes_0'] else ''} ({nz['partial_pearson']['p95']:.2f}) |")
    L.append("")
    L.append(f"## E3 held-out family / {D.unit} (train → test; AUROC on the test set [95% CI]; test-set Spearman and partial Spearman)")
    L.append("| transfer | " + " | ".join(RL[sc] for sc in list(readers) + [DOSE]) + " |")
    L.append("|---|" + "---|" * (len(readers) + 1))
    for kind in ("family", "site"):
        for name, recs in E3[kind].items():
            cells = []
            for sc in list(readers) + [DOSE]:
                c = _fmt(recs[sc]["auroc"])
                if "spearman" in recs[sc]:
                    c += f"; ρ {recs[sc]['spearman']['est']:.2f}, partial {recs[sc]['partial_spearman']['est']:.2f} [{recs[sc]['partial_spearman']['lo95']:.2f}, {recs[sc]['partial_spearman']['hi95']:.2f}]"
                cells.append(c)
            L.append(f"| {name} | " + " | ".join(cells) + " |")
    L.append("")
    L.append(f"## E4 per-pair metrics (within pair over its {PT} entries) and paired reader differences (mean, 95% CI, Wilcoxon p); threshold |Δ| ≥ {MARGIN_AUROC} / {MARGIN_CORR}; TOST 90% CI inside ±margin")
    for set_name, rec in E4.items():
        means = "; ".join(f"{RL[rd]} AUROC {_fmt(rec['per_reader_mean'][rd]['auroc'])} ρ {_fmt(rec['per_reader_mean'][rd]['spearman'], 2)}" for rd in readers)
        L.append(f"- **{set_name}** (n pairs {rec['per_reader_mean'][readers[0]]['n_pairs']}): {means}")
        for metric, key in (("ΔAUROC", "auroc_diff"), ("Δρ", "spearman_diff")):
            L.append("  - " + metric + ": " + "; ".join(f"{k} {v['mean']:+.3f} [{v['lo95']:+.3f}, {v['hi95']:+.3f}] (90%: [{v['lo90']:+.3f}, {v['hi90']:+.3f}]) p={v['wilcoxon_p']:.2g} → {_flag(v)}"
                                                      for k, v in rec[key].items()))
    nz = "; ".join(f"{RL[rd]} mean per-pair AUROC {E5['per_pair'][rd]['mean_auroc_p95']:.3f}, mean per-pair ρ {E5['per_pair'][rd]['mean_spearman_p95']:.2f}" for rd in readers)
    L.append(f"- E5 null p95 for the per-pair means ({PT}): {nz}.")
    L.append("")
    if not x2:
        c = S["rand_single_control"]
        L.append(f"rand_single control (‖Δ(i)‖-matched random direction, α 1; not in E1/E3/E4): flip {c['flip']['p']*100:.1f}% [{c['flip']['lo']*100:.1f}, {c['flip']['hi']*100:.1f}] "
                 f"({c['flip']['k']}/{c['flip']['n']}); Δ_model {_fmt(c['d_model'], 2)}; mean f_r " + "; ".join(f"{RL[rd]} {_fmt(c['readers'][rd]['f'], 3)}" for rd in readers) + ".")
    fp_note = ("S1 FPR counts an entry as positive when its fold's model (trained on the other S2 ∪ S3 folds) predicts flip at that fold's Youden threshold." if x2 else
               f"The rand_single rate counts an entry as positive when its fold's model (trained on the other folds' {PRIM} entries) predicts flip at that fold's Youden threshold.")
    L.append(f"Notes: dose-only reference and every reader use the same folds (sizes by family {S['folds']['fold_sizes_by_family']}). {fp_note} Median |sep_r|: " +
             ", ".join(f"{RL[rd]} {S['median_abs_sep'][rd]:.3f}" for rd in readers) + f". Wall {S['wall_s']} s.")
    assert len(L) <= D.md_max_lines, f"z1.md has {len(L)} lines (limit {D.md_max_lines})"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------------------
def make_fig(path: Path, S: dict, t: Table, readers: Sequence[str], D: Design = X2_DESIGN, labels: Optional[Mapping[str, str]] = None) -> None:
    RL = dict(READER_LABELS) if labels is None else dict(labels)
    SITES_ = D.sites
    x2 = D.name == "X2"
    plt = U.mpl()
    fig = plt.figure(figsize=(15.5, 6.8 if len(SITES_) <= 3 else 2.3 * len(SITES_)))
    gs = fig.add_gridspec(len(SITES_), 3, width_ratios=[1.15, 1.0, 1.05], hspace=0.55, wspace=0.3)
    ax1 = fig.add_subplot(gs[:, 0])
    ax2 = fig.add_subplot(gs[:, 1])
    ax3 = [fig.add_subplot(gs[i, 2]) for i in range(len(SITES_))]
    E1, E2, E5 = S["E1"], S["E2"], S["E5"]
    width = 0.8 / (len(readers) + 0.5)
    sets = list(D.auroc_sets)
    for gi, set_name in enumerate(sets):
        for ri, rd in enumerate(readers):
            b = E1["sets"][set_name][rd]["auroc"]
            x = gi + (ri - (len(readers) - 1) / 2) * width
            ax1.bar(x, b["est"], width=width * 0.92, color=U.METHOD_COLORS[rd], edgecolor=U.SURFACE, zorder=3, label=RL[rd] if gi == 0 else None)
            ax1.errorbar(x, b["est"], yerr=[[max(b["est"] - b["lo95"], 0)], [max(b["hi95"] - b["est"], 0)]], color=U.INK, lw=1.1, capsize=3, zorder=5)
            ax1.plot([x - width * 0.45, x + width * 0.45], [E5["auroc"][set_name][rd]["p95"]] * 2, color=U.INK2, lw=1.4, ls=":", zorder=6,
                     label="permutation null p95" if gi == 0 and ri == 0 else None)
        d = E1["sets"][set_name][DOSE]["auroc"]
        ax1.plot([gi - 0.42, gi + 0.42], [d["est"]] * 2, color="black", lw=1.8, zorder=7,
                 label=("dose-only reference (flip ~ α)" if x2 else "dose-only reference (arm × α cell rate)") if gi == 0 else None)
        ax1.fill_between([gi - 0.42, gi + 0.42], d["lo95"], d["hi95"], color="black", alpha=0.10, zorder=1)
    ax1.set_xticks(range(len(sets)))
    ax1.set_xticklabels([f"{s.replace('+', chr(10) + '+') if not x2 else s}\nn={E1['sets'][s][DOSE]['n_entries']}\nflips {E1['sets'][s][DOSE]['n_flip']}" for s in sets], fontsize=8.5)
    ax1.set_ylim(0.4, 1.02)
    ax1.axhline(0.5, color=U.GRID, lw=0.8)
    ax1.set_ylabel("out-of-fold AUROC, flip ~ f_r (95% pair-bootstrap CI)")
    ax1.set_title("E1 flip prediction, 8 pair-family folds")
    ax1.grid(axis="y", color=U.GRID, lw=0.8)
    ax1.set_axisbelow(True)
    ax1.legend(fontsize=7.5, loc="lower left")
    # middle: partial Spearman per reader per site
    for gi, site in enumerate(SITES_):
        for ri, rd in enumerate(readers):
            b = E2[site][rd]["partial_spearman"]
            x = gi + (ri - (len(readers) - 1) / 2) * width
            ax2.bar(x, b["est"], width=width * 0.92, color=U.METHOD_COLORS[rd], edgecolor=U.SURFACE, zorder=3, label=RL[rd] if gi == 0 else None)
            ax2.errorbar(x, b["est"], yerr=[[max(b["est"] - b["lo95"], 0)], [max(b["hi95"] - b["est"], 0)]], color=U.INK, lw=1.1, capsize=3, zorder=5)
            nz = E5["corr"][site][rd]["partial_spearman"]
            ax2.plot([x - width * 0.45, x + width * 0.45], [nz["p95"]] * 2, color=U.INK2, lw=1.4, ls=":", zorder=6, label="null p95" if gi == 0 and ri == 0 else None)
    ax2.axhline(0, color=U.INK2, lw=0.8)
    ax2.set_xticks(range(len(SITES_)))
    ax2.set_xticklabels([f"{s}\n(n={E2[s][readers[0]]['n_entries']})" for s in SITES_])
    ax2.set_ylabel("partial Spearman ρ(Δs_r, Δ_model | dose α)" if x2 else "partial Spearman ρ(Δs_r, Δ_model | arm × α)")
    ax2.set_title("E2 magnitude beyond the dose")
    ax2.set_ylim(-0.3, 1.0)
    ax2.grid(axis="y", color=U.GRID, lw=0.8)
    ax2.set_axisbelow(True)
    ax2.legend(fontsize=7.5, loc="upper right")
    # right: Δs_r vs Δ_model scatter per site, Δs_r in units of the reader's median |sep_r| so the three readers share an axis
    for ax, site in zip(ax3, SITES_):
        m_site = t.site == site
        for rd in readers:
            scale = S["median_abs_sep"][rd]
            y = t.ds[rd][m_site] / scale
            ax.scatter(t.dm[m_site], y, s=7, alpha=0.45, color=U.METHOD_COLORS[rd], edgecolors="none", label=f"{RL[rd]} ρ={E2[site][rd]['spearman']['est']:.2f}", zorder=3)
        ax.axhline(0, color=U.GRID, lw=0.8)
        ax.axvline(0, color=U.GRID, lw=0.8)
        ax.set_title(f"{site}: Δs_r vs Δ_model ({int(m_site.sum())} entries)", fontsize=9)
        ax.set_ylabel("Δs_r / median|sep_r|", fontsize=8)
        ax.legend(fontsize=6.5, loc="upper left")
        ax.grid(color=U.GRID, lw=0.6)
        ax.set_axisbelow(True)
    ax3[-1].set_xlabel("Δ_model = lo_model(edited) − lo_model(natural), nats toward the other candidate")
    fig.suptitle(f"Z1 intervention-response benchmark{'' if x2 else ' on the Z4 edits'} — {S['verdict']}\n{S['n_pairs']} pairs, {S['n_planted_entries']} {'planted' if x2 else 'edited'} entries; "
                 f"CIs = 95% pair bootstrap ({S['args']['n_boot']}); dotted = p95 of {E5['n_perm']} within-pair permutations", fontsize=10, y=1.0)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------------------
# gain over the dose-only reference (BRIEF_Z deviation 2026-10-09 "Z1 reporting"; post-data reporting rule)
# --------------------------------------------------------------------------------------
GAIN_BEATS, GAIN_WORSE, GAIN_TIE = "beats dose", "does not beat dose", "indistinguishable from dose"


def subset_index(t: Table, reader: Optional[str], sites: Sequence[str], families: Optional[Sequence[str]] = None) -> np.ndarray:
    """table row indices of ``subset(t, reader, sites, families)``, in the same order (the mask subset() applies)."""
    m = np.isin(t.site, list(sites))
    if families is not None:
        m &= np.isin(t.family, list(families))
    if reader is not None and reader != DOSE:
        m &= ~np.isnan(t.f[reader])
    return np.flatnonzero(m)


def pair_boot_values(pair: np.ndarray, stat: Callable[[np.ndarray], float], n_boot: int, seed: int) -> Tuple[float, np.ndarray]:
    """pair_boot's resampling (same RNG stream for the same seed and pair set), returning the point estimate and every resample's value."""
    pids = sorted(set(pair.tolist()))
    idx_of = {p: np.flatnonzero(pair == p) for p in pids}
    est = float(stat(np.arange(pair.size))) if pair.size else float("nan")
    if not pids or n_boot <= 0:
        return est, np.empty(0)
    rng = np.random.default_rng(seed)
    vals = np.empty(n_boot)
    for b in range(n_boot):
        sel = rng.integers(0, len(pids), len(pids))
        vals[b] = stat(np.concatenate([idx_of[pids[i]] for i in sel]))
    return est, vals


def gain_verdict(lo95: float, hi95: float) -> str:
    """"beats dose" only if the 95% CI of ΔAUROC excludes 0 on the positive side; "does not beat dose" if it lies entirely below 0;
    else "indistinguishable from dose" (also when the CI is undefined)."""
    if np.isnan(lo95) or np.isnan(hi95):
        return GAIN_TIE
    if lo95 > 0:
        return GAIN_BEATS
    if hi95 < 0:
        return GAIN_WORSE
    return GAIN_TIE


def paired_auroc_gain(pair: np.ndarray, y: np.ndarray, p_reader: np.ndarray, p_dose: np.ndarray, n_boot: int, seed: int) -> dict:
    """ΔAUROC = AUROC(p_reader) − AUROC(p_dose) on the same entries; paired pair-level bootstrap: each resample draws pairs once and
    recomputes both AUROCs on it. Resamples where an AUROC is undefined (one class missing) are dropped and counted."""
    y = np.asarray(y, dtype=bool)

    def stat(idx: np.ndarray) -> float:
        return auroc(p_reader[idx], y[idx]) - auroc(p_dose[idx], y[idx])

    est, vals = pair_boot_values(pair, stat, n_boot, seed)
    _, vr = pair_boot_values(pair, lambda idx: auroc(p_reader[idx], y[idx]), n_boot, seed)  # same resamples (same seed, same pairs)
    _, vd = pair_boot_values(pair, lambda idx: auroc(p_dose[idx], y[idx]), n_boot, seed)
    ok = ~np.isnan(vals)

    def q(v: np.ndarray, a: float) -> float:
        v = v[~np.isnan(v)]
        return float(np.quantile(v, a)) if v.size else float("nan")

    lo, hi = q(vals, 0.025), q(vals, 0.975)
    return {"n_entries": int(y.size), "n_pairs": int(len(set(pair.tolist()))), "n_flip": int(y.sum()),
            "auroc_reader": auroc(p_reader, y), "auroc_reader_lo95": q(vr, 0.025), "auroc_reader_hi95": q(vr, 0.975),
            "auroc_dose": auroc(p_dose, y), "auroc_dose_lo95": q(vd, 0.025), "auroc_dose_hi95": q(vd, 0.975),
            "delta_auroc": est, "delta_boot_mean": float(np.mean(vals[ok])) if ok.any() else float("nan"), "delta_lo95": lo, "delta_hi95": hi,
            "p_boot_delta_le_0": float(np.mean(vals[ok] <= 0)) if ok.any() else float("nan"),
            "n_boot": int(vals.size), "n_boot_undefined": int((~ok).sum()), "verdict": gain_verdict(lo, hi)}


def _gain_setup(args: argparse.Namespace) -> Tuple[Design, Table, List[str]]:
    """the same world, table and design run() builds (X2, or the Z4 mode)."""
    if getattr(args, "natural_behaviour", None) is not None:
        D = z4_design(args.arms.split(","))
        w, _ = load_z4_world(args.beh, args.lo, args.natural_behaviour, args.natural_lo, D.train_sites)
        readers = [rd for rd in READERS if rd in w.readers]
        return D, build_table(w, readers, sites=D.sites, dose_of=z4_dose_level), readers
    w = R.load_world(args.beh, args.lo)
    readers = [rd for rd in READERS if rd in w.readers]
    return X2_DESIGN, build_table(w, readers), readers


def gain_over_dose(args: argparse.Namespace) -> List[dict]:
    """Per reader × analysis set: ΔAUROC over the dose-only reference with the SAME predictions E1/E3 use.
    E1 sets: out-of-fold predictions from cv_oof on subset(t, scorer, set) with the run's folds (reader: logistic on f_r; dose: logistic
    on α in X2, the arm × α cell-rate model in Z4); the dose predictions are computed on all entries of the set (as in E1) and then
    restricted to the reader's entries (pairs a reader excludes for sep_r = 0 drop out of both AUROCs). Z4 per-family rows restrict the
    primary set's out-of-fold predictions to one family. E3 rows: the transfer() fit on the training family / site, predictions on the test
    set. Writes gain_over_dose.csv and gain_over_dose.md into --out; nothing else."""
    t0 = time.time()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    nb, sd = args.n_boot, args.seed
    D, t, readers = _gain_setup(args)
    fold_of = assign_folds(t.pairs, t.fam_of, args.folds, sd)
    TRAIN_, PRIM = D.train_sites, D.primary
    rows: List[dict] = []

    def add(kind: str, set_name: str, rd: str, idx_r: np.ndarray, p_r: np.ndarray, p_d_full: np.ndarray, idx_d: np.ndarray, auroc_dose_all: float) -> None:
        pos = {int(i): j for j, i in enumerate(idx_d)}
        p_d = p_d_full[[pos[int(i)] for i in idx_r]]
        rec = paired_auroc_gain(t.pair[idx_r], t.flip[idx_r], p_r, p_d, nb, sd)
        rows.append({"design": D.name, "kind": kind, "set": set_name, "reader": rd, **rec, "auroc_dose_all_entries": auroc_dose_all,
                     "n_entries_dose_all": int(idx_d.size)})

    oof: Dict[Tuple[str, str], Tuple[np.ndarray, np.ndarray]] = {}
    for set_name, sites in D.auroc_sets.items():
        for sc in readers + [DOSE]:
            o, _, _ = cv_oof(subset(t, sc, sites), fold_of)
            oof[(set_name, sc)] = (subset_index(t, sc, sites), o)
        idx_d, p_d = oof[(set_name, DOSE)]
        a_all = auroc(p_d, t.flip[idx_d])
        for rd in readers:
            idx_r, p_r = oof[(set_name, rd)]
            add("E1 out-of-fold", set_name, rd, idx_r, p_r, p_d, idx_d, a_all)
    if D.name != "X2":  # Z4: per-family restriction of the primary set's out-of-fold predictions
        idx_d0, p_d0 = oof[(PRIM, DOSE)]
        for fam in FAMILIES:
            md = t.family[idx_d0] == fam
            idx_d, p_d = idx_d0[md], p_d0[md]
            a_all = auroc(p_d, t.flip[idx_d])
            for rd in readers:
                idx_r0, p_r0 = oof[(PRIM, rd)]
                mr = t.family[idx_r0] == fam
                add("E1 out-of-fold, one family", f"{PRIM}, {fam} only", rd, idx_r0[mr], p_r0[mr], p_d, idx_d, a_all)
    # E3 held-out tests (transfer predictions, exactly as run()'s transfer(): fit on the training subset, predict the test subset)
    transfers: List[Tuple[str, str, Tuple[str, ...], Optional[Tuple[str, ...]], Tuple[str, ...], Optional[Tuple[str, ...]]]] = []
    for fam_tr, fam_te in ((FAMILIES[0], FAMILIES[1]), (FAMILIES[1], FAMILIES[0])):
        transfers.append(("E3 held-out family", f"{fam_tr}->{fam_te}", TRAIN_, (fam_tr,), TRAIN_, (fam_te,)))
    if D.name == "X2":
        for s_tr, s_te in D.site_transfers:
            transfers.append(("E3 held-out site", f"{s_tr}->{s_te}", (s_tr,), None, (s_te,), None))
    for kind, name, s_tr, f_tr, s_te, f_te in transfers:
        preds: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        for sc in readers + [DOSE]:
            tr, te = subset(t, sc, s_tr, families=f_tr), subset(t, sc, s_te, families=f_te)
            preds[sc] = (subset_index(t, sc, s_te, f_te), fit_model(tr.x, tr.y, tr.categorical).predict(te.x))
        idx_d, p_d = preds[DOSE]
        a_all = auroc(p_d, t.flip[idx_d])
        for rd in readers:
            add(kind, name, rd, *preds[rd], p_d, idx_d, a_all)
    write_gain_md(out_dir / "gain_over_dose.md", rows, D, args, readers, round(time.time() - t0, 1))
    U.write_csv(out_dir / "gain_over_dose.csv", rows)
    U.log(f"gain over dose ({D.name}): " + "; ".join(f"{r['set']} {r['reader']} {r['delta_auroc']:+.3f} [{r['delta_lo95']:+.3f}, {r['delta_hi95']:+.3f}] {r['verdict']}"
                                                     for r in rows))
    return rows


def write_gain_md(path: Path, rows: Sequence[dict], D: Design, args: argparse.Namespace, readers: Sequence[str], wall_s: float) -> None:
    RL = dict(READER_LABELS)
    flags = (f"--behaviour {args.beh} --lo {args.lo} --natural-behaviour {args.natural_behaviour} --natural-lo {args.natural_lo} --arms {args.arms} "
             if getattr(args, "natural_behaviour", None) is not None else f"--beh {args.beh} --lo {args.lo} ")
    dose = ("logistic flip ~ α (E1's dose-only reference)" if D.name == "X2" else "training-fold flip rate of the entry's arm × α cell (E1's CellModel)")
    L = [f"# Z1 reporting — reader gain over the dose-only reference ({D.name}{'' if D.name == 'X2' else ' edits, Z1-on-Z4'}; "
         f"{dt.datetime.now(dt.timezone.utc).date().isoformat()}; CPU only, 0 forward passes)", "",
         "Rule (BRIEF_Z deviation 2026-10-09 \"Z1 reporting\"): ΔAUROC = AUROC(reader's flip prediction) − AUROC(dose-only prediction) on the same "
         f"entries; paired pair-level bootstrap ({args.n_boot} resamples, seed {args.seed}: pairs resampled once, both AUROCs recomputed on the resample). "
         "**beats dose** only if the 95% CI lies above 0; **does not beat dose** if it lies below 0; otherwise **indistinguishable from dose**.",
         f"Predictions are E1's: {args.folds} pair-family folds (seed {args.seed}); reader = logistic flip ~ f_r; dose = {dose}. Dose predictions are made "
         "on every entry of the set (as in E1) and restricted to the reader's entries (pairs a reader excludes for |sep_r| < 1e-4 leave both AUROCs). "
         + ("E3 rows use E3's transfer fits (train family/site → test)." if D.name == "X2" else
            "'| family' rows restrict the primary set's out-of-fold predictions to one family; E3 rows use E3's held-out-family transfer fits."), "",
         "| set | kind | reader | n (flips) | reader AUROC | dose AUROC (same entries) | ΔAUROC [95% CI] | P(Δ ≤ 0) | verdict |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['set']} | {r['kind']} | {RL.get(r['reader'], r['reader'])} | {r['n_entries']} ({r['n_flip']}) | {r['auroc_reader']:.3f} | "
                 f"{r['auroc_dose']:.3f} | {r['delta_auroc']:+.3f} [{r['delta_lo95']:+.3f}, {r['delta_hi95']:+.3f}] | {r['p_boot_delta_le_0']:.3f} | **{r['verdict']}** |")
    L.append("")
    tally = Counter((r["reader"], r["verdict"]) for r in rows)
    L.append("Tally per reader: " + "; ".join(f"{RL.get(rd, rd)}: " + ", ".join(f"{v} {tally[(rd, v)]}" for v in (GAIN_BEATS, GAIN_TIE, GAIN_WORSE) if tally[(rd, v)])
                                               for rd in readers) + ".")
    undefined = sum(r["n_boot_undefined"] for r in rows)
    L.append(f"Bootstrap resamples with an undefined AUROC (one class absent) are dropped: {undefined} in total. ΔAUROC point estimate = full-sample "
             "difference; bootstrap mean and the separate reader / dose CIs are in gain_over_dose.csv (auroc_dose_all_entries = E1's dose AUROC on all entries).")
    L.append(f"Command: `PYTHONPATH=. .venv/bin/python projects/g_agreement/z1_intervention/analyze.py {flags}--n-boot {args.n_boot} --folds {args.folds} "
             f"--seed {args.seed} --out {args.out} --gain-over-dose` (wall {wall_s} s). Only gain_over_dose.csv and gain_over_dose.md are written; "
             "the E1–E5 files in this directory are untouched.")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv=None) -> dict:
    args = parse_args(argv)
    if getattr(args, "gain_over_dose", False):
        return {"gain_over_dose": gain_over_dose(args)}
    return run(args)


if __name__ == "__main__":
    main()
