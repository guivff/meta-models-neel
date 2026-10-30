"""Z2 tests, CPU only, on synthetic data: the pair-symmetrised score removes a shared additive candidate bias exactly
(D1 and the D2 mirror pairing), the leave-one-out bias on D3 never uses the scored item (symbol and position models),
the shared-wrong ratio with its bootstrap CI, the pre-registered verdict logic, and analyze.py end to end on the X6
synthetic world (results/ and cache/ asserted untouched).

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_z2.py -q``
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

torch = pytest.importorskip("torch")

from projects.g_agreement.z2_counterbalanced import analyze as Z2  # noqa: E402
from projects.g_agreement.x6_majority import analyze as X6  # noqa: E402
from projects.g_agreement.x_friday_r2r4 import fit_pair_bias  # noqa: E402
import test_x6 as TX6  # noqa: E402  (synthetic world builder)

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None


# ------------------------------------------------------------------ pair-symmetrised score
def test_pair_symmetrised_removes_shared_candidate_bias_exactly():
    rng = np.random.default_rng(0)
    for _ in range(50):
        beta, sig_a, sig_b = rng.normal(scale=5), rng.normal(), rng.normal()
        # fixed frame s = lp(c1) - lp(c2): state A (key c1) = beta + sig_a; state B (key c2) = beta - sig_b
        s_a, s_b = beta + sig_a, beta - sig_b
        cb_a = s_a - 0.5 * (s_a + s_b)              # toward key c1 (positive direction)
        cb_b = -(s_b - 0.5 * (s_a + s_b))           # toward key c2 (negative direction)
        expected = 0.5 * (sig_a + sig_b)            # independent of beta
        assert cb_a == pytest.approx(expected) and cb_b == pytest.approx(expected)
        # the implementation works in the toward-own-key frame: lo_A^key = beta + sig_a, lo_B^key = -beta + sig_b
        assert Z2.pair_symmetrised(beta + sig_a, -beta + sig_b) == pytest.approx(expected)
        assert Z2.pair_symmetrised(-beta + sig_b, beta + sig_a) == pytest.approx(expected)
    assert Z2.pair_symmetrised(None, 1.0) is None and Z2.pair_symmetrised(1.0, float("nan")) is None


def test_add_cb_paired_d1_and_d2_mirror():
    beta = 4.0
    rows = [{"state": "pA", "cluster": "p", "version": "A", "lo": {"jlens": beta + 1.0, "olens": beta - 0.5, "nla": None, "probe": 0.3}},
            {"state": "pB", "cluster": "p", "version": "B", "lo": {"jlens": -beta + 1.0, "olens": -beta + 2.0, "nla": 1.0, "probe": -0.3}},
            {"state": "qA", "cluster": "q", "version": "A", "lo": {"jlens": beta - 3.0, "olens": 1.0, "nla": 1.0, "probe": 0.1}}]  # no partner
    n_missing = Z2.add_cb_paired(rows, "version")
    assert n_missing == 1
    assert rows[0]["lo_cb"]["jlens"] == pytest.approx(1.0) and rows[1]["lo_cb"]["jlens"] == pytest.approx(1.0)   # beta gone, signal kept
    assert rows[0]["lo_cb"]["olens"] == pytest.approx(0.75) and rows[1]["lo_cb"]["olens"] == pytest.approx(0.75)
    assert rows[0]["lo_cb"]["nla"] is None and rows[1]["lo_cb"]["nla"] is None                                     # one side unscorable
    assert rows[0]["lo_cb"]["probe"] == 0.3 and rows[1]["lo_cb"]["probe"] == -0.3                                 # probe unchanged
    assert all(rows[2]["lo_cb"][r] is None for r in X6.LO_READERS) and rows[2]["lo_cb"]["probe"] == 0.1
    # D2: the partner is the mirror plant (other source) of the same pair, regardless of dose
    d2 = [{"state": "p|A|S2|planted|0.5", "cluster": "p", "source": "A", "alpha": 0.5, "lo": {"jlens": -beta + 2.0, "olens": 1.0, "nla": 1.0, "probe": None}},
          {"state": "p|B|S2|planted|1.0", "cluster": "p", "source": "B", "alpha": 1.0, "lo": {"jlens": beta + 0.5, "olens": 1.0, "nla": 1.0, "probe": None}}]
    assert Z2.add_cb_paired(d2, "source") == 0
    assert d2[0]["lo_cb"]["jlens"] == pytest.approx(1.25) and d2[1]["lo_cb"]["jlens"] == pytest.approx(1.25)
    # three rows in a cluster with two from the same source -> ambiguous partner -> None
    d2b = d2 + [{"state": "p|B|S2|planted|0.75", "cluster": "p", "source": "B", "alpha": 0.75, "lo": {"jlens": 1.0, "olens": 1.0, "nla": 1.0, "probe": None}}]
    assert Z2.add_cb_paired(d2b, "source") == 1 and d2b[0]["lo_cb"]["jlens"] is None


# ------------------------------------------------------------------ leave-one-out bias
def _symbol_world(n=120, seed=3):
    syms = "ABCDEFGH"
    bias = {s: b for s, b in zip(syms, (3.0, -2.0, 1.0, 0.0, -1.0, 2.0, -3.0, 0.5))}
    cands = [(syms[i % 8], syms[(i + 3) % 8]) for i in range(n)]
    lo = [bias[a] - bias[o] for a, o in cands]  # pure bias, zero signal
    return syms, bias, cands, lo


def test_loo_symbol_bias_exact_and_never_uses_scored_item():
    _, bias, cands, lo = _symbol_world()
    cb, fitted = Z2.loo_symbol_bias(lo, cands)
    assert all(v is not None for v in cb) and max(abs(v) for v in cb) < 1e-9                  # pure bias removed exactly
    # plant a signal on item 7 only: its own LOO bias is fitted on the others (bias-only) -> recovered exactly
    lo2 = list(lo); lo2[7] += 0.9
    cb2, fitted2 = Z2.loo_symbol_bias(lo2, cands)
    assert cb2[7] == pytest.approx(0.9) and fitted2[7] == pytest.approx(fitted[7])
    # a huge outlier on the scored item moves its corrected score one-to-one and leaves its fitted bias untouched ...
    lo3 = list(lo); lo3[7] += 1000.0
    cb3, fitted3 = Z2.loo_symbol_bias(lo3, cands)
    assert fitted3[7] == pytest.approx(fitted[7]) and cb3[7] == pytest.approx(1000.0)
    # ... while the in-sample fit (what X6's variant does within a fold) would absorb part of it
    vocab = sorted(set(a for a, _ in cands) | set(o for _, o in cands))
    b_in, corr_in, _ = fit_pair_bias([a for a, _ in cands], [o for _, o in cands], lo3, vocab)
    assert abs(corr_in[7]) < 999.0
    # and the fitted bias for item 7 equals a direct fit on the other items
    others = [j for j in range(len(lo)) if j != 7]
    b_dir, _, _ = fit_pair_bias([cands[j][0] for j in others], [cands[j][1] for j in others], [lo3[j] for j in others], vocab)
    assert fitted3[7] == pytest.approx(b_dir[cands[7][0]] - b_dir[cands[7][1]])
    # other items DO see the outlier through their own fits (it is in their training set)
    assert any(abs(f3 - f) > 1e-6 for j, (f3, f) in enumerate(zip(fitted3, fitted)) if j != 7)
    # None rows and unseen symbols
    lo4 = list(lo); lo4[0] = None
    cb4, _ = Z2.loo_symbol_bias(lo4, cands)
    assert cb4[0] is None and sum(v is None for v in cb4) == 1
    cands5 = list(cands); cands5[0] = ("Z", "B")
    cb5, _ = Z2.loo_symbol_bias(lo, cands5)
    assert cb5[0] is None and sum(v is None for v in cb5) == 1
    assert Z2.loo_symbol_bias([1.0, 2.0], [("A", "B"), ("B", "A")])[0] == [None, None]  # fewer than 2 others


def test_loo_position_bias_exact_and_never_uses_scored_item():
    n = 40
    sign = [1 if i % 3 else -1 for i in range(n)]
    s_hat = 0.8
    lo = [s_hat * s for s in sign]                                   # pure position bias
    cb, fitted = Z2.loo_position_bias(lo, sign)
    assert all(v is not None for v in cb) and max(abs(v) for v in cb) < 1e-12
    lo2 = list(lo); lo2[5] += 1000.0
    cb2, fitted2 = Z2.loo_position_bias(lo2, sign)
    assert fitted2[5] == pytest.approx(fitted[5]) and cb2[5] == pytest.approx(1000.0)
    others = [j for j in range(n) if j != 5]
    assert fitted2[5] == pytest.approx(np.mean([lo2[j] * sign[j] for j in others]) * sign[5])
    assert all(abs(f2 - f) > 1e-6 for j, (f2, f) in enumerate(zip(fitted2, fitted)) if j != 5)  # others see the outlier
    lo3 = list(lo); lo3[0] = None
    assert Z2.loo_position_bias(lo3, sign)[0][0] is None


def test_add_cb_d3_uses_set_family_and_copies_probe():
    syms = "ABCDEFGH"
    bias = {s: float(i) for i, s in enumerate(syms)}
    selected, tables = {}, {"D3_error": [], "D3_error_control": [], "D3_disagree": [], "D3_agree_control": []}
    for i in range(48):
        iid = f"xpz-{i:04d}"; a, o = syms[i % 8], syms[(i + 5) % 8]
        selected[iid] = {"primary": {"candidates": [a, o], "answer": a}, "source": {}}
        tables["D3_error" if i % 2 == 0 else "D3_error_control"].append({"state": iid, "cluster": iid, "lo": {"jlens": 2.0 * (bias[a] - bias[o]), "olens": None, "nla": bias[a] - bias[o], "probe": 0.7}})
    for i in range(12):
        iid = f"xch-{i:04d}"; first = i % 2 == 0
        selected[iid] = {"primary": {"candidates": [f"w{i}a", f"w{i}b"], "answer": f"w{i}a"}, "source": {"first_listed": f"w{i}a" if first else f"w{i}b"}}
        tables["D3_disagree" if i % 3 == 0 else "D3_agree_control"].append({"state": iid, "cluster": iid, "lo": {"jlens": 0.5 if first else -0.5, "olens": 1.0, "nla": 1.0, "probe": -0.1}})
    info = Z2.add_cb_d3(tables, selected)
    assert info["puzzle"]["n_items"] == 48 and info["choice"]["n_items"] == 12 and info["puzzle"]["model"] == "symbol" and info["choice"]["model"] == "position"
    pz = tables["D3_error"] + tables["D3_error_control"]
    assert all(abs(r["lo_cb"]["jlens"]) < 1e-9 for r in pz)                 # pure bias removed exactly (fit over both sets of the family)
    assert all(abs(r["lo_cb"]["nla"]) < 1e-9 for r in pz) and all(r["lo_cb"]["olens"] is None for r in pz)
    assert all(r["lo_cb"]["probe"] == 0.7 for r in pz)
    ch = tables["D3_disagree"] + tables["D3_agree_control"]
    assert all(abs(r["lo_cb"]["jlens"]) < 1e-12 for r in ch)               # pure position bias removed
    assert info["choice"]["readers"]["jlens"]["n_scorable"] == 12 and info["puzzle"]["readers"]["olens"]["n_unscorable"] == 48


# ------------------------------------------------------------------ ratio CI and verdict
def _rows(n, lo_fn):
    return [{"state": f"s{i}", "cluster": f"c{i}", "key": "k", "lo": lo_fn(i)} for i in range(n)]


def test_shared_wrong_ratio_independent_vs_correlated():
    rng = np.random.default_rng(0)
    rows = _rows(3000, lambda i: {"jlens": rng.choice([-1.0, 1.0]), "olens": rng.choice([-1.0, 1.0]), "nla": rng.choice([-1.0, 1.0]), "probe": 1.0})
    r = Z2.shared_wrong_ratio(rows, 200, 0)
    assert r["n"] == 3000 and abs(r["ratio"] - 1.0) < 0.3 and r["lo"] <= 1.0 <= r["hi"] and not r["ci_excludes_1"]
    rows2 = _rows(400, lambda i: {"jlens": -1.0 if i % 2 else 1.0, "olens": -1.0 if i % 2 else 1.0, "nla": -1.0 if i % 2 else 1.0, "probe": 1.0})
    r2 = Z2.shared_wrong_ratio(rows2, 200, 0)
    assert r2["ratio"] == pytest.approx(4.0) and r2["lo"] > 1.0 and r2["ci_excludes_1"] and r2["observed"] == 0.5 and r2["expected_independent"] == pytest.approx(0.125)
    # agrees with X6's point estimate of the same statistic
    se = X6.shared_error(rows2, 50, 0)
    assert se["all_same_wrong"]["ratio"] == pytest.approx(r2["ratio"])
    assert Z2.shared_wrong_ratio([], 10, 0)["n"] == 0
    rows3 = _rows(5, lambda i: {"jlens": None, "olens": 1.0, "nla": 1.0, "probe": 1.0})
    assert Z2.shared_wrong_ratio(rows3, 10, 0)["n"] == 0


def _fake_res(rho, ratio, lo, hi):
    t = {"n_states": 10, "spearman_A_maj_vs_A_key": {"all": {"rho": rho}}, "shared_wrong_ratio_three_lo_readers": {"ratio": ratio, "lo": lo, "hi": hi}}
    return {"raw": {"D3_error": t}, "centred": {"D3_error": t}, "counterbalanced": {"D3_error": t}}


def test_verdict_logic():
    v = Z2.verdict(_fake_res(-0.8, 1.9, 1.5, 2.3))
    assert v["rho_passes"] and v["ratio_passes"] and v["inversion_survives"] and v["verdict"] == "inversion survives"
    assert Z2.verdict(_fake_res(-0.5, 1.5, 1.01, 2.0))["inversion_survives"]                 # boundary values pass (<= / >=)
    assert not Z2.verdict(_fake_res(-0.2, 2.05, 1.7, 2.4))["inversion_survives"]             # rho fails (the real Z2 outcome)
    assert not Z2.verdict(_fake_res(-0.8, 1.4, 1.1, 1.9))["inversion_survives"]              # ratio below 1.5
    assert not Z2.verdict(_fake_res(-0.8, 1.9, 0.9, 3.0))["inversion_survives"]              # CI includes 1
    assert not Z2.verdict(_fake_res(float("nan"), 1.9, 1.5, 2.3))["inversion_survives"]      # undefined rho
    # the verdict is decided by the counterbalanced scoring only
    res = _fake_res(-0.8, 1.9, 1.5, 2.3)
    res["counterbalanced"] = {"D3_error": {"n_states": 10, "spearman_A_maj_vs_A_key": {"all": {"rho": 0.0}}, "shared_wrong_ratio_three_lo_readers": {"ratio": 1.9, "lo": 1.5, "hi": 2.3}}}
    v2 = Z2.verdict(res)
    assert not v2["inversion_survives"] and v2["by_scoring"]["raw"]["rho"] == -0.8 and "suggestive" in v2["writeup"]
    assert Z2.verdict({"counterbalanced": {}})["by_scoring"]["counterbalanced"]["rho"] != Z2.verdict({"counterbalanced": {}})["by_scoring"]["counterbalanced"]["rho"]  # nan


# ------------------------------------------------------------------ end to end on the X6 synthetic world
def _args(root: Path, out: Path, extra=()):
    return ["--items", str(root / "items.json"), "--selected", str(root / "selected.json"), "--x1-lo", str(root / "x1.jsonl"), "--x2-behaviour", str(root / "beh.jsonl"),
            "--x2-lo", str(root / "x2.jsonl"), "--x3-lo", str(root / "x3.jsonl"), "--states", str(root / "states"), "--readvecs", str(root / "readvecs"),
            "--frozen", str(root / "missing_frozen.json"), "--x6-csv", str(root / "missing_x6.csv"), "--out", str(out), "--allow-unfrozen", "--n-boot", "40", *extra]


def test_analyze_end_to_end(tmp_path):
    root = TX6.synthetic_world(tmp_path / "world")
    out = tmp_path / "out"
    s = Z2.main(_args(root, out))
    for f in ("z2_summary.json", "x6_counterbalanced.csv", "fig_main.png", "z2.md", "log.md"):
        assert (out / f).exists(), f
    assert s["frozen"] is False and s["inputs_match_freeze"] is False and s["x6_reproduction_check"]["status"] == "x6.csv not found"
    D = s["datasets"]
    # D1: counterbalanced == centred (same signs -> same rates) and both differ from raw where raw has the planted bias; probe identical throughout
    for rd in X6.READERS:
        assert D["D1"]["counterbalanced"]["readers"][rd]["A_key"]["p"] == D["D1"]["centred"]["readers"][rd]["A_key"]["p"]
        assert D["D1"]["counterbalanced"]["readers"][rd]["A_maj"]["all"]["p"] == D["D1"]["centred"]["readers"][rd]["A_maj"]["all"]["p"]
        assert D["D3_error"]["counterbalanced"]["readers"]["probe"]["A_key"]["p"] == D["D3_error"]["raw"]["readers"]["probe"]["A_key"]["p"]
    # D2: every synthetic pair flips from both sources -> every state has its mirror; jlens (lo 1.0 on every plant) stays 100%
    assert s["counterbalanced_definition"]["details"]["D2_astar"]["n_without_partner"] == 0 and s["counterbalanced_definition"]["details"]["D2_alpha1"]["n_without_partner"] == 0
    C2 = D["D2_astar"]["counterbalanced"]["readers"]
    assert C2["jlens"]["A_key"]["p"] == 1.0 and C2["jlens"]["A_key"]["n"] == 28
    # D2 mirror pairing differs from X6's natural-state shift: olens (-1 on pairs k % 3 == 0, both sources) -> mirror mean -1 -> still wrong = 8 of 28 (same here by symmetry)
    assert C2["olens"]["A_key"]["k"] == 20
    # D3: LOO symbol bias scorable for every puzzle item; choice position bias scorable for every choice item except the unscorable jlens row
    d3 = s["counterbalanced_definition"]["details"]["D3"]
    assert d3["puzzle"]["readers"]["olens"]["n_scorable"] == 40 and d3["choice"]["readers"]["jlens"]["n_unscorable"] == 1 and d3["choice"]["readers"]["olens"]["n_scorable"] == 20
    assert D["D3_error"]["counterbalanced"]["n_states"] == 20 and D["D3_error"]["counterbalanced"]["readers"]["olens"]["A_key"]["n"] == 20
    # ratio CI present for every scoring and the verdict is one of the two pre-registered outcomes
    for sc in Z2.SCORINGS:
        r = D["D3_error"][sc]["shared_wrong_ratio_three_lo_readers"]
        assert r["n"] == 20 and set(r) >= {"ratio", "lo", "hi", "ci_excludes_1"}
    assert s["verdict"]["verdict"] in ("inversion survives", "inversion downgraded to suggestive") and s["verdict"]["dataset"] == "D3_error"
    assert s["counterbalanced_definition"]["b_query_direction"].startswith("n/a") and s["counterbalanced_definition"]["c_label_tokens"].startswith("n/a") and "Z2b" in s["counterbalanced_definition"]["z2b"]
    # csv: x6.csv layout + scoring column, 3 scorings x 7 datasets x 4 readers x 3 definitions
    rows = list(csv.DictReader(open(out / "x6_counterbalanced.csv")))
    x6_cols = list(csv.DictReader(open(REPO / "results" / "g_agreement" / "x6" / "x6.csv")).fieldnames) if (REPO / "results" / "g_agreement" / "x6" / "x6.csv").exists() else []
    assert len(rows) == 3 * 7 * 4 * 3 and {r["scoring"] for r in rows} == set(Z2.SCORINGS) and all(r["scoring"] == r["variant"] for r in rows)
    assert all(c in rows[0] for c in x6_cols) and "shared_wrong_ratio_lo" in rows[0]
    md = (out / "z2.md").read_text()
    assert md.count("\n") <= 50 and "Verdict" in md and "n/a" in md and "Z2b" in md


def test_frozen_check_refuses_without_allow_unfrozen(tmp_path):
    root = TX6.synthetic_world(tmp_path / "world", n_pairs=3, n_pz=12, n_ch=10)
    args = [a for a in _args(root, tmp_path / "out") if a != "--allow-unfrozen"]
    from projects.g_agreement.core.analysis_utils import FrozenConfigError

    with pytest.raises(FrozenConfigError):
        Z2.main(args)
    assert not (tmp_path / "out").exists()
    s = Z2.main(_args(root, tmp_path / "out2", ["--skip-probe", "--no-fig"]))
    assert not (tmp_path / "out2" / "fig_main.png").exists() and s["datasets"]["D1"]["counterbalanced"]["readers"]["probe"]["A_key"]["n"] == 0


def test_nothing_written_under_results_or_cache():
    assert sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*")) == RESULTS_SNAPSHOT
    if CACHE_SNAPSHOT is not None:
        assert sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) == CACHE_SNAPSHOT
