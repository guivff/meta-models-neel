"""CPU tests for Z1 (projects/g_agreement/z1_intervention/analyze.py) on a synthetic X2-shaped world.

Synthetic world (written to tmp_path as the two jsonl files the analysis reads): 16 pairs (8 ownership, 8 mapping), two source
states each, sites nat / S1 / S2 / S3. The model's Δ_model at a planted entry is 20·α plus entry noise, the flip is Δ_model > 10.
Three readers, named after the real ones so the module's reader filter keeps them:
  olens  = TRACKING  : Δs = sep · Δ_model / 20 (+ small noise) → predicts the flip beyond the dose;
  nla    = FLAT      : Δs = noise only → AUROC ≈ 0.5, partial correlation ≈ 0;
  jlens  = DOSE-ONLY : Δs = sep · α exactly → AUROC equal to the dose-only reference, partial correlation ≈ 0.
One pair ("p16") has sep = 0 for the Oracle lens (natural lo_to = ±1) so the exclusion path is exercised.
All paths are tmp_path; nothing under results/ or cache/ is read or written.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_z1.py -q``
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.z1_intervention import analyze as Z  # noqa: E402
from projects.g_agreement import x_friday_r1 as R  # noqa: E402

Z1_DIR = REPO / "results" / "g_agreement" / "z1"
Z1_SNAPSHOT = sorted(str(p) for p in Z1_DIR.rglob("*")) if Z1_DIR.exists() else None
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None

PAIRS = [f"p{i:02d}" for i in range(1, 17)]
FAM = {p: ("ownership" if i < 8 else "mapping") for i, p in enumerate(PAIRS)}
LADDER = {"S1": [0.5, 1.0, 1.5, 2.0, 3.0], "S2": [0.25, 0.5, 0.75, 1.0], "S3": [0.25, 0.5, 0.75, 1.0]}
SEP = {"olens": 2.0, "nla": 1.0, "jlens": 0.5}  # natural separation (same for every pair, except p16 for the Oracle lens)
MODEL_NAT = -10.0  # lo_model toward other at the natural state


def _key(pair, src, site, cond, alpha):
    return f"{pair}|{src}|{site}|{cond}|{alpha}|None"


def _world(tmp_path: Path, seed: int = 0):
    rng = np.random.default_rng(seed)
    beh, lo = [], []
    truth = {}

    def reader_nat(rd, pair, src):
        if rd == "olens" and pair == "p16":
            return -1.0 if src == "A" else 1.0  # lo_own(A) + lo_own(B) = 1 - 1 = 0 → sep 0
        return -SEP[rd] / 2  # lo_toward_other negative = own answer favoured; sep = 2 · (SEP/2) = SEP

    for pair in PAIRS:
        for src in ("A", "B"):
            own, oth = (f"{pair}a", f"{pair}b") if src == "A" else (f"{pair}b", f"{pair}a")
            base = {"pair_id": pair, "family": FAM[pair], "source": src, "state_item_id": pair + src, "cand_A": own, "cand_B": oth,
                    "null_k": None, "other_pair_id": None, "coherent": True, "lo_model_unscorable": False}
            k = _key(pair, src, "nat", "natural", 0.0)
            beh.append({**base, "key": k, "site": "nat", "alpha": 0.0, "condition": "natural", "flipped_to_other": False, "lo_model": MODEL_NAT})
            for rd in SEP:
                lo.append({"key": f"{rd}|{k}", "entry_key": k, "reader": rd, "lo_toward_other": reader_nat(rd, pair, src), "unscorable": False})
            for site, ladder in LADDER.items():
                for a in ladder:
                    dm = 20.0 * a + rng.normal(0, 4.0)
                    if site == "S1":
                        dm = 0.3 * a + rng.normal(0, 0.2)  # inert site: nothing flips
                    flip = bool(dm > 10.0)
                    k = _key(pair, src, site, "planted", a)
                    beh.append({**base, "key": k, "site": site, "alpha": a, "condition": "planted", "flipped_to_other": flip, "lo_model": MODEL_NAT + dm})
                    truth[k] = (dm, flip)
                    for rd in SEP:
                        n0 = reader_nat(rd, pair, src)
                        sep = 0.0 if (rd == "olens" and pair == "p16") else SEP[rd]
                        if rd == "olens":
                            ds = sep * dm / 20.0 + rng.normal(0, 0.02 * SEP[rd])
                        elif rd == "nla":
                            ds = rng.normal(0, 0.5)
                        else:
                            ds = sep * a
                        lo.append({"key": f"{rd}|{k}", "entry_key": k, "reader": rd, "lo_toward_other": n0 + ds, "unscorable": False})
    bp, lp = tmp_path / "beh.jsonl", tmp_path / "lo.jsonl"
    bp.write_text("\n".join(json.dumps(r) for r in beh) + "\n")
    lp.write_text("\n".join(json.dumps(r) for r in lo) + "\n")
    return bp, lp, truth


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("z1")
    bp, lp, truth = _world(tmp)
    w = R.load_world(bp, lp)
    t = Z.build_table(w, list(Z.READERS))
    return {"tmp": tmp, "beh": bp, "lo": lp, "truth": truth, "w": w, "t": t}


# --------------------------------------------------------------------------------------
# table construction
# --------------------------------------------------------------------------------------
def test_build_table_quantities(world):
    t, truth = world["t"], world["truth"]
    assert t.key.size == 16 * 2 * (5 + 4 + 4)
    assert set(t.site.tolist()) == {"S1", "S2", "S3"}
    for i in range(0, t.key.size, 37):
        dm, flip = truth[t.key[i]]
        assert t.dm[i] == pytest.approx(dm, abs=1e-9)
        assert bool(t.flip[i]) == flip
    # sep: exact for every reader; f = Δs / sep; the dose-only reader's fraction is exactly α
    for rd in Z.READERS:
        for p in PAIRS:
            exp = 0.0 if (rd == "olens" and p == "p16") else SEP[rd]
            assert t.sep[rd][p] == pytest.approx(exp, abs=1e-9)
    m = ~np.isnan(t.f["jlens"])
    assert m.all()
    assert np.allclose(t.f["jlens"], t.alpha)
    assert t.excluded["olens"] == ["p16"] and t.excluded["nla"] == [] and t.excluded["jlens"] == []
    assert np.isnan(t.f["olens"][t.pair == "p16"]).all()
    assert not np.isnan(t.ds["olens"][t.pair == "p16"]).any()  # Δs is defined, only the fraction is not


def test_subset_filters(world):
    t = world["t"]
    s = Z.subset(t, "olens", ("S2", "S3"))
    assert set(s.site.tolist()) == {"S2", "S3"} and "p16" not in set(s.pair.tolist())
    assert len(s) == 15 * 2 * 8
    s1 = Z.subset(t, "nla", ("S1",), alpha_max=3.0)
    assert s1.alpha.max() <= 3.0 and len(s1) == 16 * 2 * 5
    d = Z.subset(t, Z.DOSE, ("S2",), families=("mapping",))
    assert np.array_equal(d.x, d.alpha) and set(d.family.tolist()) == {"mapping"} and np.isnan(d.ds).all()


# --------------------------------------------------------------------------------------
# folds, logistic, AUROC
# --------------------------------------------------------------------------------------
def test_assign_folds_keeps_pairs_together_and_stratifies(world):
    t = world["t"]
    fold_of = Z.assign_folds(t.pairs, t.fam_of, 8, 0)
    assert set(fold_of) == set(PAIRS)
    # every entry of a pair lands in that pair's single fold (entries are keyed by pair)
    folds_per_pair = {p: {fold_of[q] for q in t.pair[t.pair == p]} for p in PAIRS}
    assert all(len(v) == 1 for v in folds_per_pair.values())
    # stratified: 8 ownership + 8 mapping over 8 folds → exactly one of each per fold
    for k in range(8):
        fams = [t.fam_of[p] for p in PAIRS if fold_of[p] == k]
        assert sorted(fams) == ["mapping", "ownership"]
    assert Z.assign_folds(t.pairs, t.fam_of, 8, 0) == fold_of  # deterministic in the seed
    assert Z.assign_folds(t.pairs, t.fam_of, 8, 1) != fold_of


def test_auroc_and_logistic_basics():
    y = np.array([0, 0, 1, 1], dtype=bool)
    assert Z.auroc(np.array([0.1, 0.2, 0.8, 0.9]), y) == 1.0
    assert Z.auroc(np.array([0.9, 0.8, 0.2, 0.1]), y) == 0.0
    assert Z.auroc(np.array([0.5, 0.5, 0.5, 0.5]), y) == 0.5
    assert np.isnan(Z.auroc(np.array([1.0, 2.0]), np.array([True, True])))
    rng = np.random.default_rng(0)
    x = rng.normal(size=400)
    yy = rng.random(400) < 1 / (1 + np.exp(-(3 * x - 0.5)))
    m = Z.fit_logistic(x, yy)
    assert m.w > 0
    p = m.predict(x)
    assert p.shape == x.shape and (0 < p).all() and (p < 1).all()
    thr = Z.youden_threshold(p, yy)
    assert 0 < thr < 1
    xt = m.threshold_x(thr)
    assert abs(m.predict(np.array([xt]))[0] - thr) < 1e-9
    deg = Z.fit_logistic(x, np.ones(400, dtype=bool))
    assert deg.w == 0 and np.isnan(deg.threshold_x(0.5))
    # huge inputs do not overflow
    assert np.isfinite(m.predict(np.array([1e9, -1e9]))).all()


def test_cv_oof_tracking_vs_flat(world):
    t = world["t"]
    fold_of = Z.assign_folds(t.pairs, t.fam_of, 8, 0)
    res = {}
    for sc in ("olens", "nla", "jlens", Z.DOSE):
        sub = Z.subset(t, sc, ("S2", "S3"))
        oof, models, thr = Z.cv_oof(sub, fold_of)
        assert not np.isnan(oof).any() and len(models) == 8 and len(thr) == 8
        res[sc] = Z.auroc(oof, sub.y)
    assert res["olens"] > 0.9                     # tracks lo_model → predicts the flip
    assert 0.38 < res["nla"] < 0.62               # flat reader ≈ chance
    assert res["jlens"] == pytest.approx(res[Z.DOSE], abs=0.02)  # dose-only reader ≈ dose-only reference
    assert res["olens"] > res[Z.DOSE] + 0.03      # beats the dose because Δ_model varies within a dose


# --------------------------------------------------------------------------------------
# correlations, residualisation, permutation
# --------------------------------------------------------------------------------------
def test_partial_corr_removes_dose(world):
    t = world["t"]
    s = Z.subset(t, "jlens", ("S2",))
    assert Z.corr(s.ds, s.dm, "spearman") > 0.7            # raw: both rise with α
    assert abs(Z.partial_corr(s.ds, s.dm, s.alpha, "pearson")) < 1e-9 or np.isnan(Z.partial_corr(s.ds, s.dm, s.alpha, "pearson"))  # exact dose → residual 0
    s = Z.subset(t, "olens", ("S2",))
    assert Z.partial_corr(s.ds, s.dm, s.alpha, "spearman") > 0.8
    s = Z.subset(t, "nla", ("S2",))
    assert abs(Z.partial_corr(s.ds, s.dm, s.alpha, "spearman")) < 0.2
    v = np.array([1.0, 3.0, 10.0, 20.0])
    f = np.array(["a", "a", "b", "b"])
    assert np.allclose(Z.residualise(v, f), [-1, 1, -5, 5])
    assert np.isnan(Z.corr(np.ones(5), np.arange(5.0), "pearson"))


def test_permute_within_group_preserves_multisets():
    rng = np.random.default_rng(0)
    x = np.arange(12, dtype=float)
    g = np.array(["a"] * 4 + ["b"] * 4 + ["c"] * 4)
    xp = Z.permute_within_group(x, g, rng)
    for lev in "abc":
        assert sorted(xp[g == lev]) == sorted(x[g == lev])
    assert not np.array_equal(xp, x)


def test_pair_boot_shape_and_degenerate():
    pair = np.array(["a"] * 3 + ["b"] * 3 + ["c"] * 3)
    v = np.array([1, 1, 1, 2, 2, 2, 3, 3, 3], dtype=float)
    b = Z.pair_boot(pair, lambda idx: float(v[idx].mean()), 200, 0)
    assert b["est"] == 2.0 and b["lo95"] <= b["lo90"] <= b["est"] <= b["hi90"] <= b["hi95"] and b["n_pairs"] == 3
    b0 = Z.pair_boot(pair, lambda idx: float(v[idx].mean()), 0, 0)
    assert b0["est"] == 2.0 and np.isnan(b0["lo95"])


# --------------------------------------------------------------------------------------
# E4 logic: threshold rule, TOST, paired differences, verdict
# --------------------------------------------------------------------------------------
def test_threshold_rule_and_tost():
    assert Z.threshold_rule(0.08, 0.02, 0.14, 0.05)         # CI excludes 0 and |Δ| ≥ margin
    assert Z.threshold_rule(-0.08, -0.14, -0.02, 0.05)
    assert not Z.threshold_rule(0.08, -0.01, 0.17, 0.05)    # CI covers 0
    assert not Z.threshold_rule(0.03, 0.01, 0.05, 0.05)     # significant but below the margin
    assert not Z.threshold_rule(float("nan"), 0.0, 0.1, 0.05)
    assert Z.tost_pass(-0.02, 0.03, 0.05)
    assert not Z.tost_pass(-0.06, 0.03, 0.05)
    assert not Z.tost_pass(-0.02, 0.05, 0.05)               # boundary is not inside
    assert not Z.tost_pass(float("nan"), 0.0, 0.05)


def test_paired_difference_records():
    rng = np.random.default_rng(0)
    big = {f"p{i}": 0.10 + rng.normal(0, 0.02) for i in range(40)}
    r = Z.paired_difference(big, 0.05, 300, 0)
    assert r["meets_threshold"] and not r["tost_pass"] and r["wilcoxon_p"] < 1e-4 and r["n_pairs"] == 40
    tiny = {f"p{i}": rng.normal(0, 0.01) for i in range(40)}
    r = Z.paired_difference(tiny, 0.05, 300, 0)
    assert not r["meets_threshold"] and r["tost_pass"] and r["lo90"] > -0.05 and r["hi90"] < 0.05
    wide = {f"p{i}": rng.normal(0, 0.3) for i in range(12)}
    r = Z.paired_difference(wide, 0.05, 300, 0)
    assert not r["meets_threshold"] and not r["tost_pass"]
    with_nan = {"a": 0.1, "b": float("nan"), "c": 0.1}
    assert Z.paired_difference(with_nan, 0.05, 50, 0)["n_pairs"] == 2
    empty = Z.paired_difference({}, 0.05, 50, 0)
    assert empty["n_pairs"] == 0 and not empty["meets_threshold"] and not empty["tost_pass"]


def _rec(meets: bool, tost: bool) -> dict:
    return {"meets_threshold": meets, "tost_pass": tost}


def test_verdict_line():
    none_eq = {"auroc": {"a-b": _rec(False, True)}, "spearman": {"a-b": _rec(False, True)}}
    v, d = Z.verdict_line(none_eq, [none_eq])
    assert v.startswith("readers do not separate") and d["equivalence_all_tost"]
    hit = {"auroc": {"a-b": _rec(True, False)}, "spearman": {"a-b": _rec(False, True)}}
    v, d = Z.verdict_line(hit, [none_eq])
    assert v == "readers separate on intervention prediction" and d["threshold_met_primary"] == ["auroc:a-b"]
    v, d = Z.verdict_line(none_eq, [hit])
    assert v == "readers separate on intervention prediction" and d["threshold_met_heldout_family"] == ["auroc:a-b"]
    undet = {"auroc": {"a-b": _rec(False, False)}, "spearman": {"a-b": _rec(False, True)}}
    v, _ = Z.verdict_line(undet, [none_eq])
    assert v == "undetermined"


def test_per_pair_metrics_and_reader_differences(world):
    t = world["t"]
    metrics = {rd: Z.per_pair_metrics(Z.subset(t, rd, ("S2", "S3"))) for rd in Z.READERS}
    assert set(metrics["olens"]) == set(PAIRS) - {"p16"} and set(metrics["nla"]) == set(PAIRS)
    assert all(v["n"] == 16 for v in metrics["nla"].values())
    au_track = np.nanmean([v["auroc"] for v in metrics["olens"].values()])
    au_flat = np.nanmean([v["auroc"] for v in metrics["nla"].values()])
    assert au_track > 0.9 and 0.35 < au_flat < 0.65
    diffs = Z.reader_differences(metrics, "auroc", 0.05, 200, 0)
    assert set(diffs) == {"olens-nla", "olens-jlens", "nla-jlens"}
    assert diffs["olens-nla"]["meets_threshold"] and diffs["olens-nla"]["n_pairs"] == 15
    assert diffs["olens-nla"]["mean"] > 0.3


# --------------------------------------------------------------------------------------
# end to end
# --------------------------------------------------------------------------------------
def test_run_end_to_end(world, tmp_path):
    out = tmp_path / "z1_out"
    args = Z.parse_args(["--beh", str(world["beh"]), "--lo", str(world["lo"]), "--out", str(out), "--n-boot", "40", "--n-perm", "6", "--folds", "8", "--seed", "0"])
    S = Z.run(args)
    for name in ("z1.md", "z1_per_pair.csv", "z1_summary.json", "fig_main.png", "log.md"):
        assert (out / name).exists(), name
    md = (out / "z1.md").read_text().splitlines()
    assert len(md) <= 50 and "VERDICT" in md[2]
    assert S["verdict"] == "readers separate on intervention prediction"
    assert S["excluded_pairs_sep_zero"]["olens"] == ["p16"]
    e1 = S["E1"]["sets"]["S2+S3"]
    assert e1["olens"]["auroc"]["est"] > 0.9 and 0.38 < e1["nla"]["auroc"]["est"] < 0.62
    assert e1["jlens"]["auroc"]["est"] == pytest.approx(e1[Z.DOSE]["auroc"]["est"], abs=0.02)
    assert e1["olens"]["auroc"]["lo95"] <= e1["olens"]["auroc"]["est"] <= e1["olens"]["auroc"]["hi95"]
    # S1 is inert: no flips at α ≤ 3, so every predicted flip is a false positive; the dose-only model fires on every α ≥ its threshold
    fp = S["E1"]["s1_false_positive"]
    assert all(v["n_actual_flips_at_alpha_le_3"] == 0 for v in fp.values())
    assert fp["olens"]["fpr"]["p"] < 0.1               # tracking reader sees no shift at S1 → few false positives
    assert fp[Z.DOSE]["fpr"]["p"] > 0.5                # the dose model cannot know S1 is inert
    # E2 partial correlations: tracking excludes 0, flat does not
    assert S["E2"]["S2"]["olens"]["partial_spearman_ci_excludes_0"]
    assert not S["E2"]["S2"]["nla"]["partial_spearman_ci_excludes_0"]
    # E3 transfers produce AUROCs on the test set for all four scorers
    for name, recs in S["E3"]["family"].items():
        assert set(recs) == set(Z.READERS) | {Z.DOSE}
        assert recs["olens"]["auroc"]["est"] > 0.85
    # E4 primary: tracking vs flat meets the threshold; E5 nulls near 0.5
    assert S["E4"]["S2+S3"]["auroc_diff"]["olens-nla"]["meets_threshold"]
    assert 0.3 < S["E5"]["auroc"]["S2+S3"]["nla"]["p95"] < 0.75
    # per-pair csv: one row per pair with the reader columns
    rows = list(csv.DictReader(open(out / "z1_per_pair.csv")))
    assert len(rows) == 16 and {"pair", "family", "fold", "n_entries", "n_flip", "olens_auroc", "nla_spearman", "jlens_sep"} <= set(rows[0])
    p16 = next(r for r in rows if r["pair"] == "p16")
    assert p16["olens_excluded_sep_zero"] == "True" and p16["olens_auroc"] == ""
    json.load(open(out / "z1_summary.json"))  # serialisable


# --------------------------------------------------------------------------------------
# Z4 mode (BRIEF_Z deviation 2026-10-09 (4)): E1–E5 on the Z4 edits, natural reference = X2 natural rows
# --------------------------------------------------------------------------------------
Z4_POS = {"single": [0, 1, 2, 3, 4, 5], "pair2": ["0-1", "1-2", "0-5"], "all_except": [0, 1, 2]}
Z4_ALPHAS = {"single": [0.75, 1.0], "pair2": [0.5, 0.75, 1.0], "all_except": [1.0], "rand_single": [1.0], "restore": [1.0]}
Z4_STRENGTH = {"single": {0: 0.2, 1: 0.9, 2: 0.4, 3: 0.1, 4: 0.6, 5: 0.3}, "pair2": {"0-1": 1.0, "1-2": 0.7, "0-5": 0.3}, "all_except": {0: 1.1, 1: 0.5, 2: 0.9}}


def _z4_world(tmp_path: Path, seed: int = 1):
    """X2-like natural rows (+ an unrelated S2 row that must be ignored) and a Z4-like behaviour file: single / pair2 / all_except arms
    whose Δ_model = 20·α·strength(position) + noise (flip = Δ_model > 10), rand_single (inert: Δ_model ≈ 0) and restore rows (excluded).
    Readers as in the X2 world: olens tracks Δ_model, nla is flat, jlens = sep·α (dose only). p16 has olens sep 0 (excluded)."""
    rng = np.random.default_rng(seed)
    nat_b, nat_l, beh, lo = [], [], [], []
    truth = {}

    def reader_nat(rd, pair, src):
        if rd == "olens" and pair == "p16":
            return -1.0 if src == "A" else 1.0
        return -SEP[rd] / 2

    for pair in PAIRS:
        for src in ("A", "B"):
            own, oth = (f"{pair}a", f"{pair}b") if src == "A" else (f"{pair}b", f"{pair}a")
            base = {"pair_id": pair, "family": FAM[pair], "source": src, "state_item_id": pair + src, "cand_A": own, "cand_B": oth,
                    "coherent": True, "lo_model_unscorable": False}
            k = _key(pair, src, "nat", "natural", 0.0)
            nat_b.append({**base, "key": k, "site": "nat", "alpha": 0.0, "condition": "natural", "null_k": None, "flipped_to_other": False, "lo_model": MODEL_NAT})
            k2 = _key(pair, src, "S2", "planted", 1.0)
            nat_b.append({**base, "key": k2, "site": "S2", "alpha": 1.0, "condition": "planted", "null_k": None, "flipped_to_other": True, "lo_model": 30.0})
            for rd in SEP:
                nat_l.append({"key": f"{rd}|{k}", "entry_key": k, "reader": rd, "lo_toward_other": reader_nat(rd, pair, src), "unscorable": False})
                nat_l.append({"key": f"{rd}|{k2}", "entry_key": k2, "reader": rd, "lo_toward_other": 99.0, "unscorable": False})
            arms = [(arm, pos, a) for arm, ps in Z4_POS.items() for pos in ps for a in Z4_ALPHAS[arm]]
            arms += [("rand_single", pos, 1.0) for pos in (2, 4)] + [("restore", 1, 1.0)]
            for arm, pos, a in arms:
                if arm == "rand_single":
                    dm = rng.normal(0, 0.5)
                elif arm == "restore":
                    dm = 20.0 * Z4_STRENGTH["all_except"][1] + rng.normal(0, 4.0)
                else:
                    dm = 20.0 * a * Z4_STRENGTH[arm][pos] + rng.normal(0, 4.0)
                flip = bool(dm > 10.0)
                k = f"{pair}|{src}|Z4|{arm}|{float(a)}|{pos}"
                beh.append({**base, "key": k, "site": "Z4", "condition": arm, "alpha": float(a), "position": pos, "flipped_to_other": flip,
                            "kept_original": not flip, "parsed": oth if flip else own, "lo_model": MODEL_NAT + dm})
                truth[k] = (dm, flip)
                for rd in SEP:
                    n0 = reader_nat(rd, pair, src)
                    sep = 0.0 if (rd == "olens" and pair == "p16") else SEP[rd]
                    ds = sep * dm / 20.0 + rng.normal(0, 0.02 * SEP[rd]) if rd == "olens" else (rng.normal(0, 0.5) if rd == "nla" else sep * a)
                    lo.append({"key": f"{rd}|{k}", "entry_key": k, "reader": rd, "lo_toward_other": n0 + ds, "unscorable": False})
    paths = {}
    for name, rows in (("beh", beh), ("lo", lo), ("nat_b", nat_b), ("nat_l", nat_l)):
        paths[name] = tmp_path / f"z4_{name}.jsonl"
        paths[name].write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return paths, truth


@pytest.fixture(scope="module")
def z4world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("z1z4")
    paths, truth = _z4_world(tmp)
    return {"tmp": tmp, "paths": paths, "truth": truth}


def _z4_args(p, out, extra=()):
    return ["--behaviour", str(p["beh"]), "--lo", str(p["lo"]), "--natural-behaviour", str(p["nat_b"]), "--natural-lo", str(p["nat_l"]),
            "--out", str(out), *extra]


def test_z4_cli_options_and_defaults(z4world, tmp_path):
    p = z4world["paths"]
    a = Z.parse_args(["--behaviour", "b.jsonl", "--lo", "l.jsonl"])  # X2 mode: --behaviour is the old --beh; the recorded args are unchanged
    assert set(vars(a)) == {"beh", "lo", "out", "n_boot", "n_perm", "folds", "seed", "no_fig"} and a.beh == "b.jsonl" and a.out == str(Z.DEFAULT_OUT)
    assert vars(Z.parse_args([])) == vars(Z.parse_args(["--beh", str(Z.DEFAULT_BEH)]))
    a = Z.parse_args(_z4_args(p, Z.DEFAULT_OUT))
    assert a.arms == "single,pair2,all_except" and a.out == str(Z.DEFAULT_OUT_Z4) and str(Z.DEFAULT_OUT_Z4).endswith("results/g_agreement/z4/z1_on_z4")
    assert Z.parse_args(_z4_args(p, tmp_path, ["--sites", "single,all_except"])).arms == "single,all_except"
    for bad in (["--arms", "single"], ["--natural-lo", "x"]):
        with pytest.raises(SystemExit):
            Z.parse_args(["--behaviour", "b.jsonl", *bad])
    for bad_arms in ("single,restore", "rand_single", "single,single", ""):
        with pytest.raises(SystemExit):
            Z.parse_args(_z4_args(p, tmp_path, ["--arms", bad_arms]))
    with pytest.raises(SystemExit):
        Z.parse_args(["--behaviour", str(p["beh"]), "--natural-behaviour", str(p["nat_b"])])  # needs --natural-lo


def test_z4_world_and_table(z4world):
    p, truth = z4world["paths"], z4world["truth"]
    D = Z.z4_design(Z.Z4_ARMS_DEFAULT)
    assert D.sites == ("single", "pair2", "all_except", "rand_single") and D.primary == "single+pair2+all_except" and len(D.site_transfers) == 6
    assert set(D.auroc_sets) == {"single+pair2+all_except", "single", "pair2", "all_except"} and D.fp_site == "rand_single"
    w, info = Z.load_z4_world(p["beh"], p["lo"], p["nat_b"], p["nat_l"], D.train_sites)
    assert info["excluded_conditions"] == {"restore": 32} and info["n_pairs"] == 16 and info["n_natural_rows"] == 32
    assert all(r["site"] == "nat" for r in w.nat.values()) and "S2" not in {r["site"] for r in w.beh}  # only X2 NATURAL rows enter
    t = Z.build_table(w, list(Z.READERS), sites=D.sites, dose_of=Z.z4_dose_level)
    per_item = sum(len(v) * len(Z4_ALPHAS[k]) for k, v in Z4_POS.items())
    assert t.key.size == 32 * (per_item + 2) and (t.site == "rand_single").sum() == 64 and "restore" not in set(t.site.tolist())
    for i in range(0, t.key.size, 29):
        dm, flip = truth[t.key[i]]
        assert t.dm[i] == pytest.approx(dm, abs=1e-9) and bool(t.flip[i]) == flip  # Δ_model relative to the X2 natural row
    assert t.excluded["olens"] == ["p16"] and np.isnan(t.f["olens"][t.pair == "p16"]).all()
    assert np.allclose(t.f["jlens"], t.alpha)  # f_r = Δs_r / (X2 sep_r)
    assert set(t.dose.tolist()) == {"single|0.75", "single|1.0", "pair2|0.5", "pair2|0.75", "pair2|1.0", "all_except|1.0"}  # rand_single := single|1.0
    assert set(t.dose[t.site == "rand_single"].tolist()) == {"single|1.0"}
    d = Z.subset(t, Z.DOSE, D.train_sites)
    assert d.categorical and set(d.x.tolist()) == set(range(6)) and np.array_equal(d.factor, d.dose)
    s = Z.subset(t, "jlens", ("pair2",))
    pc = Z.partial_corr(s.ds, s.dm, s.factor, "pearson")  # jlens = sep·α is constant within an arm × α cell -> no partial correlation
    assert not s.categorical and s.factor[0].startswith("pair2|") and (np.isnan(pc) or abs(pc) < 1e-6)
    # the X2 table path is untouched: default build_table has no dose factor and Sub.factor is α
    assert Z.build_table(Z.R.load_world(*_world(z4world["tmp"])[:2]), list(Z.READERS)).dose is None


def test_cell_model():
    x = np.array([0, 0, 0, 1, 1, 2], dtype=float)
    y = np.array([1, 0, 1, 1, 1, 0], dtype=bool)
    m = Z.fit_cells(x, y)
    assert m.predict(np.array([0.0, 1.0, 2.0, 7.0])) == pytest.approx([2 / 3, 1.0, 0.0, 4 / 6]) and np.isnan(m.threshold_x(0.5)) and np.isnan(m.w)
    assert isinstance(Z.fit_model(x, y, categorical=True), Z.CellModel) and isinstance(Z.fit_model(x, y), Z.Logit1D)


def test_z4_run_end_to_end(z4world, tmp_path):
    p = z4world["paths"]
    out = tmp_path / "z1_on_z4"
    S = Z.run(Z.parse_args(_z4_args(p, out, ["--n-boot", "30", "--n-perm", "5", "--folds", "8", "--seed", "0"])))
    for name in ("z1.md", "z1_per_pair.csv", "z1_summary.json", "fig_main.png", "log.md"):
        assert (out / name).exists(), name
    prim = "single+pair2+all_except"
    assert S["design"]["arms"] == ["single", "pair2", "all_except"] and S["design"]["excluded_conditions"] == {"restore": 32}
    assert S["args"]["arms"] == "single,pair2,all_except" and S["args"]["natural_behaviour"] == str(p["nat_b"])
    assert S["n_entries_by_site"] == {"single": 32 * 12, "pair2": 32 * 9, "all_except": 32 * 3, "rand_single": 64}
    assert S["n_entries_by_arm_alpha"]["single|1.0"] == 32 * 6 + 64
    e1 = S["E1"]["sets"]
    assert set(e1) == {prim, "single", "pair2", "all_except"} and e1[prim]["olens"]["n_entries"] == 30 * (12 + 9 + 3)
    assert e1[prim]["olens"]["auroc"]["est"] > 0.9 and 0.35 < e1[prim]["nla"]["auroc"]["est"] < 0.65
    assert e1[prim]["olens"]["auroc"]["est"] > e1[prim][Z.DOSE]["auroc"]["est"] + 0.03  # the cell-rate dose reference knows arm × α, not the position
    assert 0.6 < e1[prim][Z.DOSE]["auroc"]["est"] < 0.95 and all(np.isnan(v) for v in e1[prim][Z.DOSE]["fold_slopes"].values())
    fp = S["E1"]["rand_single_false_positive"]
    assert all(v["n_entries"] in (64, 60) and v["n_actual_flips"] == 0 and v["actual_flip_rate"] == 0.0 for v in fp.values())
    assert fp["olens"]["fpr"]["p"] < 0.1 and "descriptive_alpha_1.0" in S["E1"]
    assert set(S["E2"]) == {"single", "pair2", "all_except", "rand_single"} and S["E2"]["single"]["olens"]["partial_spearman_ci_excludes_0"]
    assert not S["E2"]["single"]["nla"]["partial_spearman_ci_excludes_0"]
    assert len(S["E3"]["site"]) == 6 and "single->all_except" in S["E3"]["site"] and set(S["E3"]["family"]) == {"ownership->mapping", "mapping->ownership"}
    assert set(S["E4"]) == {prim, f"{prim} mapping (held out from ownership)", f"{prim} ownership (held out from mapping)"}
    assert S["E4"][prim]["auroc_diff"]["olens-nla"]["meets_threshold"] and S["verdict"] == "readers separate on intervention prediction"
    assert set(S["E5"]["auroc"]) == set(e1) and set(S["E5"]["corr"]) == set(S["E2"])
    c = S["rand_single_control"]
    assert c["n_entries"] == 64 and c["flip"]["k"] == 0 and abs(c["d_model"]["est"]) < 0.5 and set(c["readers"]) == set(Z.READERS)
    md = (out / "z1.md").read_text().splitlines()
    assert len(md) <= 64 and "VERDICT" in md[2] and any("Z4 mode" in l for l in md) and any(l.startswith("rand_single control") for l in md)
    assert any("residualised on arm × α" in l for l in md) and "--natural-behaviour" in (out / "log.md").read_text()
    rows = list(csv.DictReader(open(out / "z1_per_pair.csv")))
    assert len(rows) == 16 and int(rows[0]["n_entries"]) == 2 * (12 + 9 + 3)
    json.load(open(out / "z1_summary.json"))
    # a single-arm run: one E1 set, no arm transfers
    S1 = Z.run(Z.parse_args(_z4_args(p, tmp_path / "one", ["--arms", "single", "--n-boot", "10", "--n-perm", "2", "--no-fig"])))
    assert set(S1["E1"]["sets"]) == {"single"} and S1["E3"]["site"] == {} and S1["n_entries_by_site"] == {"single": 32 * 12, "rand_single": 64}


X2_BEH = REPO / "cache" / "g_agreement" / "x" / "x2_behaviour.jsonl"
X2_LO = REPO / "cache" / "g_agreement" / "x" / "x2_lo.jsonl"
Z1_REF = Z1_DIR / "z1_summary.json"


@pytest.mark.skipif(not (X2_BEH.exists() and X2_LO.exists() and Z1_REF.exists()), reason="needs the X2 cache and the reference Z1 summary")
def test_x2_default_reproduces_reference_summary(tmp_path):
    """No new flags: the X2 analysis reproduces results/g_agreement/z1/z1_summary.json exactly (all keys and numbers; only the
    timestamp, the output path and the wall time may differ)."""
    ref = json.load(open(Z1_REF))
    a = ref["args"]
    S = Z.run(Z.parse_args(["--beh", a["beh"], "--lo", a["lo"], "--out", str(tmp_path / "x2"), "--n-boot", str(a["n_boot"]), "--n-perm", str(a["n_perm"]),
                            "--folds", str(a["folds"]), "--seed", str(a["seed"]), "--no-fig"]))
    new = json.load(open(tmp_path / "x2" / "z1_summary.json"))
    for k in ("created_at", "wall_s"):
        ref.pop(k), new.pop(k)
    ref["args"].pop("out"), new["args"].pop("out")
    ref["args"].pop("no_fig"), new["args"].pop("no_fig")
    assert json.dumps(new, sort_keys=True) == json.dumps(ref, sort_keys=True)
    assert S["verdict"] == ref["verdict"]


def test_nothing_written_outside_tmp():
    assert (sorted(str(p) for p in Z1_DIR.rglob("*")) if Z1_DIR.exists() else None) == Z1_SNAPSHOT
    assert (sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None) == CACHE_SNAPSHOT


# --------------------------------------------------------------------------------------
# Z1 reporting (BRIEF_Z deviation 2026-10-09): gain over the dose-only reference, paired pair bootstrap
# --------------------------------------------------------------------------------------
def _gain_world(seed: int = 3, n_pairs: int = 40, per_pair: int = 12):
    """dose α ∈ {0.25 … 1}; flip = 20·α + pair/entry noise > 12; dose score = α; 'extra' = the latent Δ_model itself (more than the dose)."""
    rng = np.random.default_rng(seed)
    pair, alpha, dm = [], [], []
    for i in range(n_pairs):
        off = rng.normal(0, 3.0)
        for j in range(per_pair):
            a = [0.25, 0.5, 0.75, 1.0][j % 4]
            pair.append(f"q{i:02d}")
            alpha.append(a)
            dm.append(20 * a + off + rng.normal(0, 3.0))
    pair, alpha, dm = np.array(pair), np.array(alpha), np.array(dm)
    return pair, alpha, dm, dm > 12.0


def test_gain_over_dose_paired_bootstrap():
    pair, alpha, dm, y = _gain_world()
    same = Z.paired_auroc_gain(pair, y, alpha.copy(), alpha, 400, 0)
    assert same["delta_auroc"] == 0.0 and same["delta_lo95"] <= 0.0 <= same["delta_hi95"] and same["verdict"] == Z.GAIN_TIE
    assert same["auroc_reader"] == same["auroc_dose"] and same["n_boot_undefined"] == 0 and same["n_pairs"] == 40
    noisy = Z.paired_auroc_gain(pair, y, alpha + np.random.default_rng(1).normal(0, 1e-3, alpha.size), alpha, 400, 0)  # dose up to tiny jitter
    assert abs(noisy["delta_auroc"]) < 0.03 and noisy["delta_lo95"] < 0 < noisy["delta_hi95"] and noisy["verdict"] == Z.GAIN_TIE
    extra = Z.paired_auroc_gain(pair, y, dm, alpha, 400, 0)
    assert extra["delta_auroc"] > 0.03 and extra["delta_lo95"] > 0 and extra["verdict"] == Z.GAIN_BEATS
    worse = Z.paired_auroc_gain(pair, y, np.random.default_rng(2).normal(size=alpha.size), alpha, 400, 0)
    assert worse["delta_hi95"] < 0 and worse["verdict"] == Z.GAIN_WORSE
    # paired: the reader and dose CIs come from the SAME resamples as the difference (pair_boot's RNG stream)
    est, vals = Z.pair_boot_values(pair, lambda idx: Z.auroc(dm[idx], y[idx]), 400, 0)
    b = Z.pair_boot(pair, lambda idx: Z.auroc(dm[idx], y[idx]), 400, 0)
    assert est == b["est"] and np.nanquantile(vals, 0.025) == pytest.approx(b["lo95"]) and extra["auroc_reader_lo95"] == pytest.approx(b["lo95"])
    assert [Z.gain_verdict(*ci) for ci in ((0.01, 0.2), (-0.2, -0.01), (-0.1, 0.1), (float("nan"), 0.1))] == [Z.GAIN_BEATS, Z.GAIN_WORSE, Z.GAIN_TIE, Z.GAIN_TIE]


def test_gain_over_dose_cli_x2_and_z4(world, z4world, tmp_path):
    """--gain-over-dose writes only the two files; on the X2 world the dose-only reader (jlens = sep·α) is indistinguishable from dose, the
    tracking reader (olens) beats it on S2 ∪ S3, the flat reader (nla) does not; the reader AUROCs equal E1's."""
    out = tmp_path / "gain"
    base = ["--beh", str(world["beh"]), "--lo", str(world["lo"]), "--out", str(out), "--n-boot", "200", "--folds", "8", "--seed", "0"]
    a = Z.parse_args(base + ["--gain-over-dose"])
    assert a.gain_over_dose and "gain_over_dose" not in vars(Z.parse_args(base))
    rows = Z.main(base + ["--gain-over-dose"])["gain_over_dose"]
    assert sorted(p.name for p in out.iterdir()) == ["gain_over_dose.csv", "gain_over_dose.md"]
    g = {(r["set"], r["reader"]): r for r in rows}
    assert {s for s, _ in g} == {"S2+S3", "S2", "S3", "ownership->mapping", "mapping->ownership", "S2->S3", "S3->S2"}
    j = g[("S2+S3", "jlens")]
    assert abs(j["delta_auroc"]) < 0.02 and j["delta_lo95"] <= 0 <= j["delta_hi95"] and j["verdict"] == Z.GAIN_TIE
    assert g[("S2+S3", "olens")]["verdict"] == Z.GAIN_BEATS and g[("S2+S3", "nla")]["verdict"] == Z.GAIN_WORSE
    assert g[("S2+S3", "olens")]["n_entries"] == 15 * 2 * 8 and g[("S2+S3", "nla")]["n_entries"] == 16 * 2 * 8  # p16 excluded for olens only
    S = Z.run(Z.parse_args(base[:5] + [str(tmp_path / "e1")] + base[6:] + ["--n-perm", "2", "--no-fig"]))
    for rd in Z.READERS:
        assert g[("S2+S3", rd)]["auroc_reader"] == pytest.approx(S["E1"]["sets"]["S2+S3"][rd]["auroc"]["est"])
        assert g[("ownership->mapping", rd)]["auroc_reader"] == pytest.approx(S["E3"]["family"]["ownership->mapping"][rd]["auroc"]["est"])
    assert g[("S2+S3", "nla")]["auroc_dose"] == pytest.approx(S["E1"]["sets"]["S2+S3"][Z.DOSE]["auroc"]["est"])  # no exclusions → E1's dose AUROC
    md = (out / "gain_over_dose.md").read_text()
    assert "beats dose" in md and "--gain-over-dose" in md
    # Z4 mode: primary, per arm, per family (restrictions of the primary out-of-fold predictions) and the held-out-family transfers
    p = z4world["paths"]
    rows4 = Z.main(_z4_args(p, tmp_path / "gain4", ["--n-boot", "100", "--gain-over-dose"]))["gain_over_dose"]
    sets4 = {r["set"] for r in rows4}
    prim = "single+pair2+all_except"
    assert sets4 == {prim, "single", "pair2", "all_except", f"{prim}, ownership only", f"{prim}, mapping only", "ownership->mapping", "mapping->ownership"}
    assert sorted(x.name for x in (tmp_path / "gain4").iterdir()) == ["gain_over_dose.csv", "gain_over_dose.md"]
    r4 = {(r["set"], r["reader"]): r for r in rows4}
    assert r4[(prim, "olens")]["verdict"] == Z.GAIN_BEATS  # the cell-rate dose reference knows arm × α, not the position
    fam_rows = [r4[(f"{prim}, {f} only", "nla")]["n_entries"] for f in ("ownership", "mapping")]
    assert sum(fam_rows) == r4[(prim, "nla")]["n_entries"]


# --------------------------------------------------------------------------------------
# Z4 per-position correlation: role-aligned keying and the pair-bootstrap correlation
# --------------------------------------------------------------------------------------
def test_role_aligned_keys():
    from projects.g_agreement.z4_positions import position_corr as PC

    # <|im_start|> user \n | s0 NAME s1 OBJ . | Q0 Q1 ? | <|im_end|> \n <|im_start|> assistant \n <think> \n\n </think> \n\n
    A = [248045, 846, 198, 10, 501, 11, 601, 13, 20, 21, 30, 248046, 198, 248045, 74455, 198, 248068, 271, 248069, 271]
    B = list(A)
    B[4], B[6] = 502, 602
    diff, user_start, tmpl = PC.layout_from_ids(A, B)
    assert diff == [4, 6] and user_start == 3 and tmpl == 11
    k = PC.role_keys(len(A), diff, 8, tmpl, user_start)
    assert [PC.key_label(k[i]) for i in range(len(A))] == (
        ["chat_prefix:0", "chat_prefix:1", "chat_prefix:2", "statement:0", "diff:0", "statement:1", "diff:1", "statement:2",
         "question:0", "question:1", "question:2"] + [f"template:{i}" for i in range(8)] + ["last:0"])
    # a longer prompt: the same key is the same kind of token (diff:1 = second differing token, question:0 = question start, last:0)
    k2 = PC.role_keys(30, [5, 9], 12, 21, 3)
    assert k2[9] == ("diff", 1) and k2[12] == ("question", 0) and k2[21] == ("template", 0) and k2[29] == ("last", 0) and k2[11] == ("statement", 6)
    for bad in (([5], 4, 21, 3), ([5], 12, 11, 3), ([1], 12, 21, 3)):
        with pytest.raises(ValueError):
            PC.role_keys(30, *bad)
    with pytest.raises(ValueError):
        PC.layout_from_ids(A, B[:-1])


def test_position_corr_bootstrap():
    from projects.g_agreement.z4_positions import position_corr as PC

    rng = np.random.default_rng(0)
    pair, key, score, flip = [], [], [], []
    rate = {f"k{i}": i / 9 for i in range(10)}  # flip rate rises with the key; the tracking score is the rate plus noise
    for p in range(30):
        for k, r in rate.items():
            pair.append(f"p{p}"); key.append(k); flip.append(rng.random() < r); score.append(r + rng.normal(0, 0.1))
    pair, key, score, flip = map(np.array, (pair, key, score, flip))
    rec = PC.position_corr(pair, key, score, flip, 200, 0, min_n=8)
    assert rec["n_keys"] == 10 and rec["spearman"] > 0.8 and rec["spearman_lo95"] > 0.5 and rec["spearman_ci_excludes_0"] and rec["n_entries"] == 300
    flat = PC.position_corr(pair, key, rng.normal(size=score.size), flip, 200, 0, min_n=8)
    assert flat["spearman_lo95"] < 0 < flat["spearman_hi95"]
    few = PC.position_corr(pair, key, score, flip, 50, 0, min_n=31)  # every key has 30 entries < min_n → undefined
    assert few["n_keys"] == 0 and np.isnan(few["spearman"])
    # weights = bootstrap multiplicities: weight 1 everywhere reproduces the point estimate
    pids, keys, n, s, f = PC.key_matrices(pair, key, score, flip)
    assert PC.corr_from_weights(np.ones(len(pids)), n, s, f, 8)[0] == pytest.approx(rec["spearman"])
