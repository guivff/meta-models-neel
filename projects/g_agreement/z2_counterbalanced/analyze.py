"""Z2 — X6 recomputed under a COUNTERBALANCED scoring (BRIEF_Z.md §Z2; CPU only, zero new forward passes).

Reuses X6 (projects/g_agreement/x6_majority/analyze.py) by import for the datasets D1 / D2 / D3, the four readers
(J-lens, Oracle, NLA native LO + the linear probe), the RAW and CENTRED fields, the rate table (A_key, A_maj under
ALL / SIBLINGS / NON-SIBLING, M_acc), the Spearman rho over the 4 readers and the shared-error statistic. Z2 adds a
third score field `lo_cb` per state and re-runs the identical analysis for raw / centred / counterbalanced.

Counterbalanced score (variant (a) of the specification; (b) query direction and (c) label tokens are n/a: no X
template encodes a direction or uses label tokens). The native LO is antisymmetric in the candidate pair by
construction, so order-swapping on cached scores is the identity; the counterbalance is applied to the per-candidate
token bias instead:
  D1 (paired natural states)  s_cb(state) = s(state) - 1/2 [s(state) + s(other state of the pair)], s in the FIXED
      candidate frame (s = lp(cand_1) - lp(cand_2) on both states). Re-oriented toward each state's own key this is
      1/2 (lo_A^key + lo_B^key): the mean of the two states' toward-own-key LOs. A per-candidate bias beta adds +beta
      to s on both states and cancels exactly. This coincides (up to the positive factor 1/2) with X6's CENTRED D1
      margin, so D1 counterbalanced == D1 centred by identity.
  D2 (planted states)  the two scores averaged are the planted state's LO toward the planted candidate and the LO of
      the MIRROR planted state of the same pair (planted from the other source, toward the other candidate) in the
      same dataset (its own alpha* for D2_astar; alpha 1 for D2_alpha1): s_cb^key = 1/2 (lo_{A->B}^key + lo_{B->A}^key).
      Both are planted states with opposite keys, so the shared per-candidate bias cancels exactly; the pair's natural
      states are NOT involved (X6's CENTRED D2 instead subtracts the same-source natural LO, which is the pairing
      "planted state + its own natural state" and imports the natural reading). States whose mirror is absent from the
      dataset (the pair partner never flipped) are unscorable under counterbalanced and counted.
  D3 (single states)  additive candidate-bias model fitted LEAVE-ONE-OUT over the other items of the same set family
      (puzzles: per-symbol bias b over A-H via x_friday_r2r4.fit_pair_bias on ERROR + ERROR_CONTROL; choice sets:
      option-position bias s_hat = mean(lo * sign_first_listed) on DISAGREE + AGREE_CONTROL), never on the scored item;
      s_cb = lo - fitted bias. X6's CENTRED uses a 5-fold fit (puzzles) and RAW (choice).
  Probe reader unchanged in all three scorings.
A true re-scoring with swapped batch order needs reader forward passes: deferred to Z2b (pod, <= 30 min).

THRESHOLD (pre-registered): the X6 inversion survives if rho(A_maj, A_key) <= -0.5 under counterbalanced (ALL
definition, D3 ERROR) AND the shared-wrong-answer ratio >= 1.5 with its item-bootstrap 95% CI excluding 1.
Outputs results/g_agreement/z2/{z2.md, x6_counterbalanced.csv, z2_summary.json, fig_main.png, log.md}.

    .venv/bin/python projects/g_agreement/z2_counterbalanced/analyze.py --n-boot 1000 --seed 0 --out results/g_agreement/z2
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.x6_majority import analyze as X6  # noqa: E402
from projects.g_agreement.x_friday_r2r4 import fit_pair_bias  # noqa: E402

MODULE = "z2"
SCORINGS = ("raw", "centred", "counterbalanced")
FIELD = {"raw": "lo", "centred": "lo_centred", "counterbalanced": "lo_cb"}
SCORING_LABELS = {"raw": "RAW (pre-specified per-state sign)", "centred": "CENTRED (X6 post-hoc, in-sample)", "counterbalanced": "COUNTERBALANCED (Z2: pair-symmetrised / LOO bias)"}
THRESHOLDS = {"z2_spearman_max": -0.5, "z2_ratio_min": 1.5}
VERDICT_DATASET, VERDICT_DEF = "D3_error", "all"
NA_VARIANTS = {"b_query_direction": "n/a: none of the X templates encodes a query direction",
               "c_label_tokens": "n/a: no template uses label tokens (candidates are answered by their own words / symbols)"}
Z2B_NOTE = ("true swapped-batch-order re-scoring needs reader forward passes (Oracle lens and NLA run on 27B models): "
            "deferred to Z2b (pod, <= 30 min, 297 D3 ERROR + 126 D2 states, reader side only, read vectors cached)")
DEFAULTS = {**X6.DEFAULTS, "frozen": ROOT / "projects" / "g_agreement" / "manifest" / "frozen_config_z.json", "x6_csv": ROOT / "results" / "g_agreement" / "x6" / "x6.csv"}
FROZEN_INPUT_KEYS = {"x1_lo": "cache/g_agreement/x/x1_lo.jsonl", "x2_lo": "cache/g_agreement/x/x2_lo.jsonl",
                     "x2_behaviour": "cache/g_agreement/x/x2_behaviour.jsonl", "x3_lo": "cache/g_agreement/x/x3_lo.jsonl", "x6_csv": "results/g_agreement/x6/x6.csv"}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=str(v))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true", help="run without the Z freeze / with changed inputs (writes to .../dev)")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    ap.add_argument("--skip-probe", action="store_true")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ counterbalanced scores
def pair_symmetrised(lo_self: Optional[float], lo_partner: Optional[float]) -> Optional[float]:
    """s_cb(state) = s(state) - 1/2 [s(state) + s(partner)] in the fixed candidate frame, re-oriented toward the
    state's own key. With s(state) = +lo_self^key and s(partner) = -lo_partner^key (opposite keys) this equals
    1/2 (lo_self^key + lo_partner^key). A shared additive per-candidate bias cancels exactly. None if either is None."""
    if lo_self is None or lo_partner is None:
        return None
    a, b = float(lo_self), float(lo_partner)
    if np.isnan(a) or np.isnan(b):
        return None
    return 0.5 * (a + b)


def partners_by_cluster(rows: Sequence[dict], tag: str) -> Dict[int, Optional[int]]:
    """row index -> index of the one other row of the same cluster with a different `tag` value (None if absent)."""
    by: Dict[str, List[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        by[r["cluster"]].append(i)
    out: Dict[int, Optional[int]] = {}
    for i, r in enumerate(rows):
        others = [j for j in by[r["cluster"]] if j != i and rows[j].get(tag) != r.get(tag)]
        out[i] = others[0] if len(others) == 1 else None
    return out


def add_cb_paired(rows: Sequence[dict], tag: str) -> int:
    """Set row['lo_cb'] for paired datasets (D1: tag 'version'; D2: tag 'source'); probe copied. Returns the number
    of states without a partner (unscorable under counterbalanced for the LO readers)."""
    part = partners_by_cluster(rows, tag)
    n_missing = 0
    for i, r in enumerate(rows):
        j = part[i]
        if j is None:
            n_missing += 1
        cb = {rd: (None if j is None else pair_symmetrised(r["lo"].get(rd), rows[j]["lo"].get(rd))) for rd in X6.LO_READERS}
        cb["probe"] = r["lo"].get("probe")
        r["lo_cb"] = cb
    return n_missing


def loo_symbol_bias(lo: Sequence[Optional[float]], cands: Sequence[Tuple[str, str]]) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """Leave-one-out additive per-symbol bias: for each scorable row i, fit lo_j ~ b[actual_j] - b[other_j] by least
    squares on all OTHER scorable rows (x_friday_r2r4.fit_pair_bias) and return (lo_i - (b[a_i] - b[o_i]), the fitted
    bias). None where lo_i is None, a symbol of row i is unseen in the other rows, or fewer than 2 other rows exist."""
    n = len(lo)
    ok = [i for i in range(n) if lo[i] is not None and not np.isnan(float(lo[i]))]
    out: List[Optional[float]] = [None] * n
    fitted: List[Optional[float]] = [None] * n
    for i in ok:
        tr = [j for j in ok if j != i]
        if len(tr) < 2:
            continue
        vocab = sorted({s for j in tr for s in cands[j]})
        a, o = cands[i]
        if a not in vocab or o not in vocab:
            continue
        b, _, _ = fit_pair_bias([cands[j][0] for j in tr], [cands[j][1] for j in tr], [float(lo[j]) for j in tr], vocab)
        fitted[i] = b[a] - b[o]
        out[i] = float(lo[i]) - fitted[i]
    return out, fitted


def loo_position_bias(lo: Sequence[Optional[float]], sign_first: Sequence[int]) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """Leave-one-out option-position bias (x_friday R3a choice model): s_hat_{-i} = mean_{j != i}(lo_j * sign_j) with
    sign_j = +1 if the actual answer was the first-listed option else -1; returns (lo_i - s_hat_{-i} * sign_i, fitted)."""
    n = len(lo)
    ok = [i for i in range(n) if lo[i] is not None and not np.isnan(float(lo[i]))]
    out: List[Optional[float]] = [None] * n
    fitted: List[Optional[float]] = [None] * n
    for i in ok:
        tr = [j for j in ok if j != i]
        if len(tr) < 2:
            continue
        s_hat = float(np.mean([float(lo[j]) * sign_first[j] for j in tr]))
        fitted[i] = s_hat * sign_first[i]
        out[i] = float(lo[i]) - fitted[i]
    return out, fitted


def add_cb_d3(tables: Mapping[str, Sequence[dict]], selected: Mapping[str, dict]) -> dict:
    """Set row['lo_cb'] on the D3 tables: LOO symbol bias over the puzzle family (ERROR + ERROR_CONTROL), LOO position
    bias over the choice family (DISAGREE + AGREE_CONTROL); probe copied. Returns fit diagnostics per family/reader."""
    info: dict = {}
    for fam, sets, kind in (("puzzle", ("error", "error_control"), "symbol"), ("choice", ("disagree", "agree_control"), "position")):
        rows = [r for s in sets for r in tables.get(f"D3_{s}", [])]
        info[fam] = {"sets": list(sets), "n_items": len(rows), "model": kind, "readers": {}}
        if not rows:
            continue
        cands = [tuple(selected[r["state"]]["primary"]["candidates"][:2]) for r in rows]
        sign_first = [1 if U.normalise_answer(selected[r["state"]]["primary"]["answer"]) == U.normalise_answer((selected[r["state"]].get("source") or {}).get("first_listed")) else -1 for r in rows]
        for r in rows:
            r["lo_cb"] = {"probe": r["lo"].get("probe")}
        for rd in X6.LO_READERS:
            lo = [r["lo"].get(rd) for r in rows]
            cb, fitted = loo_symbol_bias(lo, cands) if kind == "symbol" else loo_position_bias(lo, sign_first)
            for r, v in zip(rows, cb):
                r["lo_cb"][rd] = v
            fv = [f for f in fitted if f is not None]
            info[fam]["readers"][rd] = {"n_scorable": sum(v is not None for v in cb), "n_unscorable": sum(v is None for v in cb),
                                        "fitted_bias_abs_mean": float(np.mean(np.abs(fv))) if fv else float("nan"),
                                        "fitted_bias_range": float(max(fv) - min(fv)) if fv else float("nan"),
                                        "n_sign_changes_vs_raw": int(sum(1 for l, v in zip(lo, cb) if l is not None and v is not None and (l > 0) != (v > 0)))}
    return info


# ------------------------------------------------------------------ shared-wrong-answer ratio with a bootstrap CI
def shared_wrong_ratio(rows: Sequence[dict], nb: int, sd: int, readers: Sequence[str] = X6.LO_READERS, field: str = "lo") -> dict:
    """observed P(all `readers` favour the same non-key candidate) / product of their marginal P(non-key), with a
    cluster (pair / item) bootstrap 95% CI of the RATIO (ratio recomputed inside every resample)."""
    S = X6.table_signs(rows, field)
    full = [(row, s) for row, s in zip(rows, S) if all(s[r] is not None for r in readers)]
    if not full:
        return {"n": 0, "ratio": float("nan"), "lo": float("nan"), "hi": float("nan")}
    cnt: Dict[str, int] = defaultdict(int)
    allw: Dict[str, int] = defaultdict(int)
    wrong: Dict[str, Dict[str, int]] = {r: defaultdict(int) for r in readers}
    for row, s in full:
        c = row["cluster"]
        cnt[c] += 1
        allw[c] += int(all(s[r] < 0 for r in readers))
        for r in readers:
            wrong[r][c] += int(s[r] < 0)

    def stat(ps: Sequence[str]) -> float:
        n = sum(cnt[p] for p in ps)
        if n == 0:
            return float("nan")
        obs = sum(allw[p] for p in ps) / n
        exp = float(np.prod([sum(wrong[r][p] for p in ps) / n for r in readers]))
        return obs / exp if exp > 0 else float("nan")

    est, lo, hi = U.pair_bootstrap_stat(sorted(cnt), stat, n_boot=nb, seed=sd)
    n = len(full)
    obs = sum(allw.values()) / n
    exp = float(np.prod([sum(wrong[r].values()) / n for r in readers]))
    return {"n": n, "n_clusters": len(cnt), "readers": list(readers), "observed": obs, "expected_independent": exp, "ratio": est, "lo": lo, "hi": hi,
            "ci": "cluster bootstrap of the ratio", "ci_excludes_1": bool(not np.isnan(lo) and (lo > 1.0 or hi < 1.0))}


# ------------------------------------------------------------------ analysis
def analyse_tables(tables: Mapping[str, Sequence[dict]], nb: int, sd: int, scorings: Sequence[str] = SCORINGS) -> Dict[str, Dict[str, dict]]:
    """{scoring: {dataset: statistics}}: X6's rate table, Spearman and shared-error, plus the ratio CI (pure)."""
    res: Dict[str, Dict[str, dict]] = {v: {} for v in scorings}
    for name, rows in tables.items():
        for v in scorings:
            f = FIELD[v]
            if not rows:
                res[v][name] = {"n_states": 0}
                continue
            t = X6.rate_table(rows, nb, sd, field=f)
            t["spearman_A_maj_vs_A_key"] = X6.spearman_readers(t)
            t["shared_error_three_lo_readers"] = X6.shared_error(rows, nb, sd, X6.LO_READERS, f)
            t["shared_wrong_ratio_three_lo_readers"] = shared_wrong_ratio(rows, nb, sd, X6.LO_READERS, f)
            t["n_unscorable"] = {rd: t["readers"][rd]["n_unscorable"] for rd in X6.READERS}
            res[v][name] = t
    return res


def verdict(res: Mapping[str, Mapping[str, dict]], thresholds: Mapping[str, float] = THRESHOLDS, dataset: str = VERDICT_DATASET, definition: str = VERDICT_DEF) -> dict:
    """Pre-registered rule: the inversion survives iff rho(ALL) <= z2_spearman_max under counterbalanced AND the
    shared-wrong ratio >= z2_ratio_min with its bootstrap CI excluding 1 (lower bound > 1)."""
    out: dict = {"dataset": dataset, "definition": definition, "thresholds": dict(thresholds), "by_scoring": {}}
    for v in res:
        t = res[v].get(dataset, {})
        if not t.get("n_states"):
            out["by_scoring"][v] = {"rho": float("nan"), "ratio": float("nan"), "ratio_lo": float("nan"), "ratio_hi": float("nan")}
            continue
        r = t["shared_wrong_ratio_three_lo_readers"]
        out["by_scoring"][v] = {"rho": t["spearman_A_maj_vs_A_key"][definition]["rho"], "ratio": r["ratio"], "ratio_lo": r["lo"], "ratio_hi": r["hi"]}
    cb = out["by_scoring"].get("counterbalanced", {})
    rho, ratio, lo = cb.get("rho", float("nan")), cb.get("ratio", float("nan")), cb.get("ratio_lo", float("nan"))
    rho_ok = bool(not np.isnan(rho) and rho <= thresholds["z2_spearman_max"])
    ratio_ok = bool(not np.isnan(ratio) and not np.isnan(lo) and ratio >= thresholds["z2_ratio_min"] and lo > 1.0)
    survives = rho_ok and ratio_ok
    out.update({"rho_passes": rho_ok, "ratio_passes": ratio_ok, "inversion_survives": survives,
                "verdict": "inversion survives" if survives else "inversion downgraded to suggestive",
                "writeup": ("X6 inversion on D3 ERROR survives the counterbalanced scoring: keep it as a finding in writeup.md"
                            if survives else "X6 inversion on D3 ERROR does not survive the counterbalanced scoring: downgrade to 'suggestive' in writeup.md (Phase Z corrections)")})
    return out


# ------------------------------------------------------------------ checks
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_frozen_inputs(cfg: Optional[Mapping[str, Any]], paths: Mapping[str, Path]) -> Dict[str, dict]:
    """Compare the sha256 of each Z-frozen input with the freeze record; {key: {path, frozen_sha, actual_sha, match}}."""
    rec = (cfg or {}).get("inputs", {})
    out = {}
    for k, rel in FROZEN_INPUT_KEYS.items():
        p = Path(paths[k])
        actual = sha256_file(p) if p.exists() else None
        frozen = rec.get(rel)
        out[k] = {"path": str(p), "frozen_sha256": frozen, "actual_sha256": actual, "match": (frozen is not None and actual == frozen)}
    return out


def check_against_x6_csv(res: Mapping[str, Mapping[str, dict]], x6_csv: Path) -> dict:
    """Max |difference| of the raw / centred point estimates (A_key, A_maj, M_acc, rho) against the frozen x6.csv."""
    import csv

    if not Path(x6_csv).exists():
        return {"status": "x6.csv not found", "max_abs_diff": float("nan")}
    rows = list(csv.DictReader(open(x6_csv)))
    diffs, n = [], 0
    for r in rows:
        t = res.get(r["variant"], {}).get(r["dataset"])
        if not t or not t.get("n_states"):
            continue
        rd, d = r["reader"], r["majority_def"]
        pairs = ((t["readers"][rd]["A_key"]["p"], r["A_key"]), (t["readers"][rd]["A_maj"][d]["p"], r["A_maj"]), (t["majority"][d]["M_acc"]["p"], r["M_acc"]),
                 (t["spearman_A_maj_vs_A_key"][d]["rho"], r["spearman_rho"]))
        for mine, theirs in pairs:
            try:
                th = float(theirs)
            except ValueError:
                continue
            if np.isnan(mine) and np.isnan(th):
                continue
            diffs.append(abs(mine - th)); n += 1
    m = max(diffs) if diffs else float("nan")
    return {"status": "ok" if diffs else "no comparable rows", "n_compared": n, "max_abs_diff": m, "reproduces_x6_point_estimates": bool(diffs) and m < 1e-9}


# ------------------------------------------------------------------ run
def build_tables(args: argparse.Namespace, sd: int) -> Tuple[Dict[str, List[dict]], dict]:
    """X6's datasets with lo / lo_centred (X6 builders) plus lo_cb (Z2)."""
    _, items = U.load_items(args.items)
    selected = {it["item_id"]: it for it in U.load_json(args.selected)["items"]}
    x1, beh, x2, x3 = U.load_jsonl(args.x1_lo), U.load_jsonl(args.x2_behaviour), U.load_jsonl(args.x2_lo), U.load_jsonl(args.x3_lo)
    states_dir, readvecs_dir = Path(args.states), Path(args.readvecs)
    use_probe = not args.skip_probe
    pairs = X6.x_pairs(items, "test")
    H, missing = X6.load_states_for(pairs, states_dir) if use_probe else ({}, [])
    dirs = {fam: X6.loo_directions(pairs[fam], H) for fam in X6.FAMILIES} if use_probe else {}
    tables: Dict[str, List[dict]] = {"D1": X6.build_d1(items, x1, dirs, H, use_probe)}
    d2s, d2o, d2info = X6.build_d2(beh, x2, dirs, readvecs_dir, X6.PRIMARY_SITE, use_probe)
    tables["D2_astar"], tables["D2_alpha1"] = d2s, d2o
    d3, d3info = X6.build_d3(selected, x3, states_dir, use_probe, sd)
    tables.update(d3)
    cb_info = {"D1": {"pairing": "the two natural states of the pair (versions A and B)", "n_without_partner": add_cb_paired(tables["D1"], "version")},
               "D2_astar": {"pairing": "planted state (source A -> B at its alpha*) with the mirror planted state of the same pair (source B -> A at its alpha*)", "n_without_partner": add_cb_paired(d2s, "source")},
               "D2_alpha1": {"pairing": "planted state (source A -> B at alpha 1) with the mirror planted state (source B -> A at alpha 1)", "n_without_partner": add_cb_paired(d2o, "source")},
               "D3": add_cb_d3(tables, selected)}
    info = {"inputs": {"x1_rows": len(x1), "x2_behaviour_rows": len(beh), "x2_lo_rows": len(x2), "x3_lo_rows": len(x3), "n_selected": len(selected)},
            "probe": {"enabled": use_probe, "n_states_missing": len(missing), "n_pairs_with_direction": {f: len(dirs.get(f, {})) for f in X6.FAMILIES}, "D3": d3info},
            "D2": d2info, "counterbalanced": cb_info}
    return tables, info


def run(args: argparse.Namespace) -> dict:
    t0 = time.time()
    cfg = U.load_frozen_config(args.frozen)
    frozen = bool(cfg and cfg.get("frozen") is True)
    paths = {k: Path(getattr(args, k)) for k in FROZEN_INPUT_KEYS}
    sha = check_frozen_inputs(cfg, paths)
    inputs_ok = frozen and all(v["match"] for v in sha.values())
    if not inputs_ok and not args.allow_unfrozen:
        bad = [k for k, v in sha.items() if not v["match"]]
        raise U.FrozenConfigError(f"Z freeze check failed (frozen={frozen}; sha mismatch or missing: {bad}); pass --allow-unfrozen for a dev run")
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if inputs_ok else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    nb, sd = args.n_boot, args.seed
    U.log(f"[z2] frozen={frozen} inputs_match={inputs_ok} n_boot={nb} seed={sd} out={out}")
    tables, info = build_tables(args, sd)
    for k in X6.DATASETS:
        U.log(f"[z2] {k}: {len(tables.get(k, []))} states")
    res = analyse_tables({k: tables[k] for k in X6.DATASETS if k in tables}, nb, sd)
    x6_check = check_against_x6_csv(res, Path(args.x6_csv))
    ver = verdict(res)
    for v in SCORINGS:
        for ds in X6.FIG_PANELS:
            t = res[v].get(ds, {})
            if not t.get("n_states"):
                continue
            for rd in X6.READERS:
                r = t["readers"][rd]
                U.log(f"[z2] {v:15} {ds:12} {X6.READER_LABELS[rd]:14} A_key {100 * r['A_key']['p']:5.1f} [{100 * r['A_key']['lo']:.0f},{100 * r['A_key']['hi']:.0f}]  " +
                      "  ".join(f"A_maj[{d}] {100 * r['A_maj'][d]['p']:5.1f} (n {r['A_maj'][d]['n']})" for d in X6.MAJ_DEFS))
            sw = t["shared_wrong_ratio_three_lo_readers"]
            U.log(f"[z2] {v:15} {ds:12} rho " + " ".join(f"{d} {t['spearman_A_maj_vs_A_key'][d]['rho']:+.2f}" for d in X6.MAJ_DEFS) +
                  f"  shared-wrong ratio {sw['ratio']:.2f} [{sw['lo']:.2f}, {sw['hi']:.2f}] (n {sw['n']})")
    U.log(f"[z2] VERDICT: {ver['verdict']} — rho(ALL, CB) {ver['by_scoring']['counterbalanced']['rho']:+.2f} (<= {THRESHOLDS['z2_spearman_max']}: {ver['rho_passes']}); "
          f"ratio {ver['by_scoring']['counterbalanced']['ratio']:.2f} [{ver['by_scoring']['counterbalanced']['ratio_lo']:.2f}, {ver['by_scoring']['counterbalanced']['ratio_hi']:.2f}] "
          f"(>= {THRESHOLDS['z2_ratio_min']} and CI > 1: {ver['ratio_passes']}). {ver['writeup']}")
    summary = {"module": MODULE, "frozen": frozen, "inputs_match_freeze": inputs_ok, "freeze_check": sha, "n_boot": nb, "seed": sd, "readers": list(X6.READERS),
               "majority_definitions": {d: list(m) for d, m in X6.MAJ_DEFS.items()}, "scorings": {v: SCORING_LABELS[v] for v in SCORINGS},
               "counterbalanced_definition": {"a_candidate_order": "native LO antisymmetric in the pair -> order swap on cached scores is the identity; counterbalance applied to the per-candidate bias",
                                              "paired_states": "s_cb = s - 1/2 [s + s(partner)] in the fixed candidate frame = 1/2 (lo_self^key + lo_partner^key); D1 partner = other version; D2 partner = mirror planted state (see 'details')",
                                              "D1_note": "coincides with X6 CENTRED D1 (pair mean of the toward-own-key LOs) up to the factor 1/2: identical signs",
                                              "D3": "leave-one-out additive bias over the other items of the same set family: puzzles per-symbol (fit_pair_bias), choice option-position; never fitted on the scored item",
                                              "probe": "unchanged", "details": info["counterbalanced"], **NA_VARIANTS, "z2b": Z2B_NOTE},
               "thresholds": dict(THRESHOLDS), "verdict": ver, "x6_reproduction_check": x6_check, "inputs": info["inputs"], "probe": info["probe"], "D2": info["D2"],
               "datasets": {k: {"label": X6.DATASET_LABELS[k], **{v: res[v].get(k, {"n_states": 0}) for v in SCORINGS}} for k in X6.DATASETS},
               "wall_s": round(time.time() - t0, 1)}
    U.write_json(out / "z2_summary.json", summary)
    U.write_csv(out / "x6_counterbalanced.csv", csv_rows(res))
    write_md(out / "z2.md", summary)
    if not args.no_fig:
        make_figure(out / "fig_main.png", summary)
    with open(out / "log.md", "a") as f:
        f.write(f"- {dt.datetime.now(dt.timezone.utc).isoformat()} `{' '.join(sys.argv)}` frozen={frozen} inputs_match={inputs_ok} n_boot={nb} seed={sd} wall {summary['wall_s']} s; "
                f"states " + ", ".join(f"{k} {len(tables.get(k, []))}" for k in X6.DATASETS) + f"; verdict: {ver['verdict']}; CPU only, 0 forward passes\n")
    U.log(f"[z2] wrote {out} ({summary['wall_s']} s)")
    return summary


def csv_rows(res: Mapping[str, Mapping[str, dict]]) -> List[dict]:
    """x6.csv layout (variant = scoring) plus `scoring`, the ratio CI and the CB unscorable count."""
    out = []
    for r in X6.csv_rows(res):
        t = res[r["variant"]][r["dataset"]]
        sw = t["shared_wrong_ratio_three_lo_readers"]
        out.append({**r, "scoring": r["variant"], "shared_wrong_ratio": sw["ratio"], "shared_wrong_ratio_lo": sw["lo"], "shared_wrong_ratio_hi": sw["hi"],
                    "n_unscorable_reader": t["n_unscorable"][r["reader"]]})
    return out


# ------------------------------------------------------------------ reporting
def _f(x: float, fmt: str = "{:+.1f}") -> str:
    return "n/a" if x is None or np.isnan(x) else fmt.format(x)


def write_md(path: Path, s: dict) -> None:
    v = s["verdict"]
    cb = s["counterbalanced_definition"]
    L = ["# Z2 — X6 under counterbalanced scoring (raw / centred / counterbalanced side by side)", "",
         f"CPU only, 0 forward passes; n_boot {s['n_boot']}, seed {s['seed']}; Z freeze inputs match: {s['inputs_match_freeze']}; raw/centred point estimates reproduce x6.csv: "
         f"{s['x6_reproduction_check'].get('reproduces_x6_point_estimates')} (max |diff| {s['x6_reproduction_check'].get('max_abs_diff', float('nan')):.1e}, CIs now at n_boot {s['n_boot']}).",
         "Counterbalanced (CB) score, variant (a) only: the native LO is antisymmetric in the candidate pair, so swapping the cached order is the identity; the per-candidate bias is counterbalanced instead.",
         "D1: s_cb = s − ½[s + s(other version)] in the fixed candidate frame = ½(lo_A^key + lo_B^key); identical in sign to X6 CENTRED D1. "
         "D2: the two scores averaged are the planted state's LO toward the planted candidate and the MIRROR planted state's (same pair, other source, same dataset: own α* / α 1); "
         f"natural states not used (X6 CENTRED D2 pairs the plant with its own natural state). States without a mirror: D2 α* {cb['details']['D2_astar']['n_without_partner']}, α 1 {cb['details']['D2_alpha1']['n_without_partner']}.",
         "D3: additive candidate bias fitted LEAVE-ONE-OUT over the other items of the same set family (puzzles ERROR+ERROR_CONTROL: per-symbol via fit_pair_bias; choice DISAGREE+AGREE_CONTROL: option-position), never on the scored item. Probe unchanged.",
         f"Variants (b) query direction and (c) label tokens: n/a for these templates. {Z2B_NOTE}.", "",
         "| dataset (n) | reader | A_key raw / centred / CB | A_maj ALL raw / centred / CB | A_maj SIB raw / centred / CB | A_maj NONSIB raw / centred / CB |", "|---|---|---|---|---|---|"]
    for ds in X6.FIG_PANELS:
        T = {sc: s["datasets"][ds][sc] for sc in SCORINGS}
        if not T["raw"].get("n_states"):
            continue
        for rd in X6.READERS:
            R = {sc: T[sc]["readers"][rd] for sc in SCORINGS}
            L.append(f"| {ds} ({T['raw']['n_states']}) | {X6.READER_LABELS[rd]} | " + " / ".join(_f(100 * R[sc]["A_key"]["p"], "{:.0f}") for sc in SCORINGS) + " | " +
                     " | ".join(" / ".join(_f(100 * R[sc]["A_maj"][d]["p"], "{:.0f}") for sc in SCORINGS) for d in X6.MAJ_DEFS) + " |")
        L.append(f"| {ds} | M_acc ALL/SIB/NONSIB | " + " / ".join("·".join(f"{100 * T[sc]['majority'][d]['M_acc']['p']:.0f}" for d in X6.MAJ_DEFS) for sc in SCORINGS) + " | " +
                 " | ".join("ρ " + " / ".join(_f(T[sc]["spearman_A_maj_vs_A_key"][d]["rho"]) for sc in SCORINGS) for d in X6.MAJ_DEFS) + " |")
    L.append("")
    for sc in SCORINGS:
        t = s["datasets"]["D3_error"][sc]
        if not t.get("n_states"):
            continue
        se, sw = t["shared_error_three_lo_readers"], t["shared_wrong_ratio_three_lo_readers"]
        w = se["all_same_wrong"]
        L.append(f"Shared error, D3 ERROR, {sc} (n {sw['n']}): all three LO readers favour the same non-key candidate in {100 * w['observed']['p']:.1f}% [{100 * w['observed']['lo']:.1f}, {100 * w['observed']['hi']:.1f}] "
                 f"vs {100 * w['expected_independent']:.1f}% under independence: ratio {sw['ratio']:.2f} [{sw['lo']:.2f}, {sw['hi']:.2f}]; ρ(A_maj, A_key) ALL {_f(t['spearman_A_maj_vs_A_key']['all']['rho'])}.")
    L += ["", "## Verdict (pre-registered: ρ(ALL) ≤ −0.5 under CB AND ratio ≥ 1.5 with CI excluding 1, D3 ERROR)", ""]
    c = v["by_scoring"]["counterbalanced"]
    L.append(f"- ρ(ALL, CB) = {_f(c['rho'], '{:+.2f}')} → {'passes' if v['rho_passes'] else 'fails'}; shared-wrong ratio (CB) = {c['ratio']:.2f} [{c['ratio_lo']:.2f}, {c['ratio_hi']:.2f}] → {'passes' if v['ratio_passes'] else 'fails'}.")
    L.append(f"- **{v['verdict'].upper()}**: {v['writeup']}.")
    L.append("- Three-way: " + "; ".join(f"{sc} ρ {_f(v['by_scoring'][sc]['rho'], '{:+.2f}')} ratio {v['by_scoring'][sc]['ratio']:.2f} [{v['by_scoring'][sc]['ratio_lo']:.2f}, {v['by_scoring'][sc]['ratio_hi']:.2f}]" for sc in SCORINGS) + ".")
    L.append("- Caveats: n = 4 readers for ρ (descriptive, values in {−1, −0.8, …, 1}); D1 CB = CENTRED by identity; D2 CB needs both mirror plants; the LOO bias on D3 is an additive model only; "
             "the bf16 batch-composition order effect is untested until Z2b.")
    path.write_text("\n".join(L) + "\n")


def make_figure(path: Path, s: dict) -> None:
    plt = U.mpl()
    fig, axes = plt.subplots(len(SCORINGS), len(X6.FIG_PANELS), figsize=(4.0 * len(X6.FIG_PANELS), 4.2 * len(SCORINGS)))
    axes = np.atleast_2d(axes)
    for row, v in enumerate(SCORINGS):
        for col, ds in enumerate(X6.FIG_PANELS):
            ax = axes[row, col]
            t = s["datasets"][ds][v]
            ax.plot([0, 1], [0, 1], color=U.INK2, lw=0.8, ls=":", zorder=1)
            ax.axhline(0.5, color=U.GRID, lw=0.8, zorder=0); ax.axvline(0.5, color=U.GRID, lw=0.8, zorder=0)
            ax.set_xlim(0, 1.02); ax.set_ylim(0, 1.02)
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1]); ax.set_xticklabels(["0", "25", "50", "75", "100"]); ax.set_yticks([0, 0.25, 0.5, 0.75, 1]); ax.set_yticklabels(["0", "25", "50", "75", "100"])
            ax.grid(color=U.GRID, lw=0.6); ax.set_axisbelow(True)
            if not t.get("n_states"):
                ax.text(0.5, 0.5, "no states", ha="center", va="center", color=U.INK2); ax.set_title(X6.DATASET_LABELS[ds], fontsize=8.5); continue
            for rd in X6.READERS:
                r = t["readers"][rd]
                x, y = r["A_maj"]["all"], r["A_key"]
                if np.isnan(x["p"]) or np.isnan(y["p"]):
                    continue
                ax.errorbar(x["p"], y["p"], xerr=[[max(x["p"] - x["lo"], 0)], [max(x["hi"] - x["p"], 0)]], yerr=[[max(y["p"] - y["lo"], 0)], [max(y["hi"] - y["p"], 0)]],
                            fmt="o", ms=8, color=X6.READER_COLORS[rd], ecolor=X6.READER_COLORS[rd], elinewidth=1.2, capsize=3, mec=U.SURFACE, mew=1.2,
                            label=X6.READER_LABELS[rd] + (" — order-confounded" if rd == "probe" and ds.startswith(("D1", "D2")) else ""), zorder=4)
                ax.annotate(X6.READER_LABELS[rd].split(" ")[0], (x["p"], y["p"]), xytext=(6, -10 if rd in ("nla", "probe") else 6), textcoords="offset points", fontsize=7.5, color=U.INK2)
            m, sw = t["majority"], t["shared_wrong_ratio_three_lo_readers"]
            txt = (f"M_acc ALL {100 * m['all']['M_acc']['p']:.0f}% (n {m['all']['n_defined']})\n      SIB {100 * m['siblings']['M_acc']['p']:.0f}% (n {m['siblings']['n_defined']})\n"
                   f"      NONSIB {100 * m['nonsib']['M_acc']['p']:.0f}% (n {m['nonsib']['n_defined']})\nρ(A_maj, A_key) ALL {t['spearman_A_maj_vs_A_key']['all']['rho']:+.1f}")
            if ds == "D3_error":
                txt += f"\nshared-wrong ratio {sw['ratio']:.2f} [{sw['lo']:.2f}, {sw['hi']:.2f}]"
            ax.text(0.03, 0.97, txt, transform=ax.transAxes, va="top", fontsize=7.5, color=U.INK, family="monospace")
            if row == len(SCORINGS) - 1:
                ax.set_xlabel("A_maj (ALL): agrees with the LOO majority\nof the other 3 readers (% of states)", fontsize=8.5)
            if col == 0:
                ax.set_ylabel(f"{v.upper()} scoring\nA_key: agrees with the independent key (% of states)")
            ax.set_title(f"{X6.DATASET_LABELS[ds]}\nn = {t['n_states']} states / {t['n_clusters']} {'items' if ds.startswith('D3') else 'pairs'}", fontsize=8.5)
            ax.legend(fontsize=6.8, loc="lower right")
    ver = s["verdict"]
    fig.suptitle(("" if s["inputs_match_freeze"] else "UNFROZEN DEV RUN — ") + "Z2 — X6 rating readers by majority agreement vs an independent key under RAW (top), CENTRED (middle) and "
                 f"COUNTERBALANCED (bottom: pair-symmetrised D1/D2, leave-one-out candidate bias D3) scoring. Bars = 95% pair/item bootstrap; dotted = identity. Verdict: {ver['verdict']}.",
                 y=1.01, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
