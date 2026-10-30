"""Phase Z3 (BRIEF_Z §Z3) tests, CPU only, synthetic rows: margin computation (items without an S2 alpha* excluded; 0.25 x median),
TOST inside / outside / straddling the margin, pair-level bootstrap shape (resamples pair_ids, both items of a pair move together,
90% CI nested in the 95% CI), per-item null averaging over null_k, sign convention (positive = toward the other candidate),
G5 continuous-LO detection, the end-to-end run on tmp paths and the append-only writeup block (idempotent heading, original kept).
Nothing is written under results/ or cache/.

Run: ``PYTHONPATH=. .venv/bin/python -m pytest projects/g_agreement/tests/test_z3.py -q``
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.z3_equivalence import analyze as Z  # noqa: E402

PAIRS = [f"p{i:02d}" for i in range(12)]


# ----------------------------------------------------------------------------------------------------------------------
# synthetic data
# ----------------------------------------------------------------------------------------------------------------------
def _per_pair_rows(diffs, n_without=2):
    """One row per item; `diffs` = lo_model_at_astar_S2 - lo_model_nat for items with an alpha*; n_without items have none."""
    rows = []
    for i, d in enumerate(diffs):
        rows.append({"pair_id": f"p{i // 2:02d}", "source": "AB"[i % 2], "alpha_star_S2": "0.75", "lo_model_nat": "-10.0",
                     "lo_model_at_astar_S2": str(-10.0 + d)})
    for j in range(n_without):
        rows.append({"pair_id": f"q{j:02d}", "source": "A", "alpha_star_S2": "", "lo_model_nat": "-10.0", "lo_model_at_astar_S2": ""})
    return rows


def _x2_rows(rng, s1_shift=0.3, null_shift=0.0, noise=0.2, n_null=3):
    """Natural + S1 planted (0.5/1/1.5/2/3/4) + S2/S3 null (alpha 1) + S1 null / null_other (alpha 2) rows for PAIRS x {A, B}."""
    rows = []
    for pid in PAIRS:
        for src in "AB":
            nat = float(rng.normal(-10, 2))
            base = {"pair_id": pid, "family": "ownership", "source": src, "coherent": True}
            rows.append({**base, "site": "nat", "condition": "natural", "alpha": 0.0, "null_k": None, "flipped_to_other": False, "lo_model": nat})
            for a in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
                shift = s1_shift * a + rng.normal(0, noise)
                rows.append({**base, "site": "S1", "condition": "planted", "alpha": a, "null_k": None,
                             "flipped_to_other": bool(a >= 4.0 and src == "A"), "lo_model": nat + shift})
            for site, a in (("S2", 1.0), ("S3", 1.0), ("S1", 2.0)):
                for k in range(n_null):
                    rows.append({**base, "site": site, "condition": "null", "alpha": a, "null_k": k, "flipped_to_other": False,
                                 "lo_model": nat + null_shift + rng.normal(0, noise)})
            for k in range(2):
                rows.append({**base, "site": "S1", "condition": "null_other", "alpha": 2.0, "null_k": k, "flipped_to_other": False,
                             "lo_model": nat + null_shift + rng.normal(0, noise)})
    return rows


def _g5_rows(with_lo=False):
    rows = []
    for pid in ("g0", "g1", "g2", "g3"):
        for src in "AB":
            base = {"pair_id": pid, "source": src, "state_item_id": pid + src, "family": "mapping"}
            r = {**base, "condition": "natural", "alpha": 0.0, "null_k": None, "flipped_to_other": False, "answer_text": "x"}
            if with_lo:
                r["lo_model"] = -5.0
            rows.append(r)
            for a in (0.5, 1.0, 1.5, 3.0, 5.0):
                r = {**base, "condition": "planted", "alpha": a, "null_k": None, "flipped_to_other": bool(a == 5.0 and src == "A"), "answer_text": "x"}
                if with_lo:
                    r["lo_model"] = -5.0 + 0.1 * a
                rows.append(r)
            for k in range(2):
                r = {**base, "condition": "null", "alpha": 1.0, "null_k": k, "flipped_to_other": False, "answer_text": "x"}
                if with_lo:
                    r["lo_model"] = -5.0
                rows.append(r)
    return rows


# ----------------------------------------------------------------------------------------------------------------------
# margin
# ----------------------------------------------------------------------------------------------------------------------
def test_margin_is_quarter_median_over_items_with_astar():
    diffs = [8.0, 10.0, 12.0, 14.0, 16.0, 40.0]           # median 13 -> margin 3.25; items without alpha* excluded
    m = Z.compute_margin(_per_pair_rows(diffs, n_without=2))
    assert m["margin"] == pytest.approx(0.25 * 13.0)
    assert m["median_delta_model_at_astar_S2"] == pytest.approx(13.0)
    assert m["n_items_with_astar_S2"] == 6 and m["n_items_without_astar_S2"] == 2 and m["n_items_total"] == 8


def test_margin_ignores_rows_with_missing_lo_and_raises_when_undefined():
    rows = _per_pair_rows([4.0, 8.0], n_without=0)
    rows.append({"pair_id": "z", "source": "A", "alpha_star_S2": "0.5", "lo_model_nat": "", "lo_model_at_astar_S2": "1.0"})
    m = Z.compute_margin(rows)
    assert m["margin"] == pytest.approx(0.25 * 6.0) and m["n_items_without_astar_S2"] == 1
    with pytest.raises(Z.U.AnalysisError):
        Z.compute_margin(_per_pair_rows([], n_without=3))


# ----------------------------------------------------------------------------------------------------------------------
# TOST
# ----------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("ci90,margin,expected", [
    ((-0.5, 0.5), 1.0, Z.INERT),              # inside
    ((0.1, 0.9), 1.0, Z.INERT),               # inside, excludes 0: still equivalent within margin
    ((-1.5, 0.2), 1.0, Z.NOT_EST),            # lower end outside
    ((0.2, 1.5), 1.0, Z.NOT_EST),             # upper end outside
    ((-2.0, 2.0), 1.0, Z.NOT_EST),            # straddles both
    ((-1.0, 0.5), 1.0, Z.NOT_EST),            # touching the margin is not inside (strict)
    ((float("nan"), float("nan")), 1.0, Z.NOT_EST),
    ((-0.1, 0.1), float("nan"), Z.NOT_EST),
])
def test_tost_verdict(ci90, margin, expected):
    assert Z.tost_verdict(ci90, margin) == expected


# ----------------------------------------------------------------------------------------------------------------------
# per-item deltas and pair bootstrap
# ----------------------------------------------------------------------------------------------------------------------
def test_item_deltas_sign_and_null_k_averaging():
    rows = [{"pair_id": "p", "source": "A", "condition": "natural", "site": "nat", "alpha": 0.0, "lo_model": -10.0},
            {"pair_id": "p", "source": "B", "condition": "natural", "site": "nat", "alpha": 0.0, "lo_model": -6.0},
            {"pair_id": "p", "source": "A", "condition": "planted", "site": "S1", "alpha": 1.0, "lo_model": -9.0},
            {"pair_id": "p", "source": "B", "condition": "planted", "site": "S1", "alpha": 1.0, "lo_model": -7.0},
            {"pair_id": "p", "source": "A", "condition": "null", "site": "S1", "alpha": 2.0, "null_k": 0, "lo_model": -8.0},
            {"pair_id": "p", "source": "A", "condition": "null", "site": "S1", "alpha": 2.0, "null_k": 1, "lo_model": -12.0},
            {"pair_id": "p", "source": "A", "condition": "null", "site": "S1", "alpha": 2.0, "null_k": 2, "lo_model": -10.0}]
    nat = Z.natural_lo(rows)
    assert nat == {("p", "A"): -10.0, ("p", "B"): -6.0}
    d = Z.item_deltas(Z.select_rows(rows, "S1", "planted", 1.0), nat)
    assert d[("p", "A")] == pytest.approx(+1.0) and d[("p", "B")] == pytest.approx(-1.0)   # positive = toward other
    dn = Z.item_deltas(Z.select_rows(rows, "S1", "null", 2.0), nat)
    assert dn == {("p", "A"): pytest.approx(0.0)}                                            # mean over null_k first (+2, −2, 0)
    with pytest.raises(Z.U.AnalysisError):
        Z.item_deltas([{"pair_id": "zz", "source": "A", "lo_model": 0.0}], nat)
    with pytest.raises(Z.U.AnalysisError):
        Z.natural_lo(rows + [rows[0]])


def test_pair_bootstrap_mean_shape_and_nesting():
    rng = np.random.default_rng(1)
    deltas = {(pid, src): float(rng.normal(0.5, 1.0)) for pid in PAIRS for src in "AB"}
    bs = Z.pair_bootstrap_mean(deltas, n_boot=400, seed=0)
    assert set(bs) >= {"mean", "ci95", "ci90", "n_items", "n_pairs", "n_boot", "seed"}
    assert bs["n_items"] == 24 and bs["n_pairs"] == 12 and bs["n_boot"] == 400
    assert bs["mean"] == pytest.approx(float(np.mean(list(deltas.values()))))
    lo95, hi95 = bs["ci95"]
    lo90, hi90 = bs["ci90"]
    assert lo95 <= lo90 <= bs["mean"] <= hi90 <= hi95
    assert lo90 < hi90
    # deterministic in the seed
    assert Z.pair_bootstrap_mean(deltas, n_boot=400, seed=0) == bs
    assert Z.pair_bootstrap_mean(deltas, n_boot=400, seed=1)["ci95"] != bs["ci95"]


def test_pair_bootstrap_resamples_pairs_not_items():
    # Each pair has items (+c, −c): any pair-level resample has mean exactly 0, so the CI collapses to 0.
    # An item-level bootstrap would give a non-degenerate interval.
    deltas = {}
    for i, pid in enumerate(PAIRS):
        deltas[(pid, "A")] = float(i + 1)
        deltas[(pid, "B")] = -float(i + 1)
    bs = Z.pair_bootstrap_mean(deltas, n_boot=200, seed=0)
    assert bs["mean"] == pytest.approx(0.0)
    assert bs["ci95"] == pytest.approx([0.0, 0.0], abs=1e-12) and bs["ci90"] == pytest.approx([0.0, 0.0], abs=1e-12)


def test_flip_counts_require_coherence():
    sel = [{"flipped_to_other": True, "coherent": True}, {"flipped_to_other": True, "coherent": False},
           {"flipped_to_other": False, "coherent": True}, {"flipped_to_other": True}]   # missing coherent -> counts
    assert Z.flip_counts(sel) == (2, 4)


# ----------------------------------------------------------------------------------------------------------------------
# condition summaries: inside vs outside the margin
# ----------------------------------------------------------------------------------------------------------------------
def test_summarise_condition_inert_vs_not_established():
    rng = np.random.default_rng(0)
    rows = _x2_rows(rng, s1_shift=0.3, noise=0.1)          # S1 alpha 1 shift ~0.3; alpha 4 shift ~1.2
    nat = Z.natural_lo(rows)
    margin = 0.6
    r1 = Z.summarise_condition("X2", "S1", "planted", 1.0, "confirmatory", Z.select_rows(rows, "S1", "planted", 1.0), nat, margin, 300, 0, True)
    r4 = Z.summarise_condition("X2", "S1", "planted", 4.0, "descriptive", Z.select_rows(rows, "S1", "planted", 4.0), nat, margin, 300, 0, True)
    assert r1["tost_verdict"] == Z.INERT and r1["ci90_lo"] > -margin and r1["ci90_hi"] < margin
    assert r1["ci95_excludes_zero"] is True
    assert r4["tost_verdict"] == Z.NOT_EST and r4["mean_delta"] > margin
    assert r4["frac_items_abs_gt_margin"] > 0.9 and r1["frac_items_abs_gt_margin"] == 0.0
    assert r1["n_rows"] == 24 and r1["n_items"] == 24 and r1["n_pairs"] == 12
    # flips with Wilson CI: alpha 4 flips every A state (12/24)
    assert (r4["flips_k"], r4["flips_n"]) == (12, 24) and r4["flip_wilson_lo"] < 0.5 < r4["flip_wilson_hi"]
    assert (r1["flips_k"], r1["flips_n"]) == (0, 24) and r1["flip_wilson_lo"] == pytest.approx(0.0)
    # null condition: items averaged over null_k first
    rn = Z.summarise_condition("X2", "S2", "null", 1.0, "confirmatory", Z.select_rows(rows, "S2", "null", 1.0), nat, margin, 300, 0, True)
    assert rn["n_rows"] == 72 and rn["n_items"] == 24 and rn["tost_verdict"] == Z.INERT
    # non-continuous: verdict n/a, flips still reported
    rg = Z.summarise_condition("G5", "L42 last", "planted", 1.0, "confirmatory", Z.select_rows(_g5_rows(), None, "planted", 1.0), None, margin, 300, 0, False)
    assert rg["tost_verdict"] == Z.NA and math.isnan(rg["mean_delta"]) and (rg["flips_k"], rg["flips_n"]) == (0, 8) and rg["n_items"] == 8


def test_g5_continuous_detection():
    assert Z.g5_has_continuous_lo(_g5_rows(with_lo=False))[0] is False
    assert Z.g5_has_continuous_lo(_g5_rows(with_lo=True))[0] is True
    rows = _g5_rows(with_lo=False)
    for r in rows:
        r["lp_first_A"], r["lp_first_B"] = -0.1, -3.0
    assert Z.g5_has_continuous_lo(rows)[0] is True


# ----------------------------------------------------------------------------------------------------------------------
# end to end on tmp paths
# ----------------------------------------------------------------------------------------------------------------------
def _write_inputs(tmp_path, rng, g5_with_lo=False):
    x2 = tmp_path / "x2_behaviour.jsonl"
    x2.write_text("\n".join(json.dumps(r) for r in _x2_rows(rng)) + "\n")
    g5 = tmp_path / "g5.jsonl"
    g5.write_text("\n".join(json.dumps(r) for r in _g5_rows(with_lo=g5_with_lo)) + "\n")
    pp = tmp_path / "per_pair.csv"
    rows = _per_pair_rows([8.0, 10.0, 12.0, 14.0, 16.0, 40.0], n_without=2)
    with open(pp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return x2, g5, pp


def test_main_end_to_end_and_writeup_append(tmp_path):
    rng = np.random.default_rng(3)
    x2, g5, pp = _write_inputs(tmp_path, rng)
    out = tmp_path / "z3"
    writeup = tmp_path / "writeup.md"
    original = "# writeup\n\nThe last-token vector is not load-bearing (G5 again); the all-position state at L38 is.\n"
    writeup.write_text(original)
    summary = Z.main(["--behaviour", str(x2), "--g5", str(g5), "--per-pair", str(pp), "--out", str(out), "--writeup", str(writeup),
                      "--n-boot", "200", "--seed", "0"])
    assert summary["margin"]["margin"] == pytest.approx(3.25)
    for name in ("z3.md", "z3_table.csv", "z3_summary.json", "z3_margin.json"):
        assert (out / name).exists()
    md = (out / "z3.md").read_text()
    assert len([l for l in md.split("\n") if l.strip()]) <= 40
    assert md.index("Margin") < md.index("| data |")                     # margin stated before the table
    assert "3.250" in md
    with open(out / "z3_table.csv") as f:
        table = list(csv.DictReader(f))
    assert [r["tost_verdict"] for r in table if r["dataset"] == "G5"] == [Z.NA] * 6
    assert summary["g5"]["continuous_log_odds"] is False and "flip rates" in summary["g5"]["note"]
    conf = [r for r in table if r["role"] == "confirmatory" and r["dataset"] == "X2"]
    assert len(conf) == 7 and all(r["tost_verdict"] == Z.INERT for r in conf)   # synthetic S1 shift 0.3*alpha << 3.25
    assert list(table[0].keys()) == Z.TABLE_COLUMNS
    # writeup: append-only, original sentence kept, dated heading present, one bullet per claim
    text = writeup.read_text()
    assert text.startswith(original.rstrip("\n"))
    assert text.count(f"**Phase Z corrections ({Z.DATE})**") == 1
    for _sec, quote in Z.INERT_CLAIMS:
        assert quote in text
    assert text.count("See z3/z3.md") == 3
    # idempotent heading: a second append adds bullets under the same heading, not a second heading
    Z.append_writeup(writeup, ["- extra bullet from another module"])
    text2 = writeup.read_text()
    assert text2.count(f"**Phase Z corrections ({Z.DATE})**") == 1 and "- extra bullet from another module" in text2
    assert text2.index("- extra bullet") > text2.index("See z3/z3.md")


def test_append_writeup_inserts_before_following_section(tmp_path):
    w = tmp_path / "w.md"
    w.write_text(f"# A\n\n**Phase Z corrections ({Z.DATE})**\n\nintro\n\n- z1 bullet\n\n---\n\n## Later\n\ntext\n")
    Z.append_writeup(w, ["- z3 bullet"])
    t = w.read_text()
    assert t.index("- z1 bullet") < t.index("- z3 bullet") < t.index("## Later")
    assert t.count("**Phase Z corrections") == 1


def test_main_with_continuous_g5(tmp_path):
    rng = np.random.default_rng(5)
    x2, g5, pp = _write_inputs(tmp_path, rng, g5_with_lo=True)
    summary = Z.main(["--behaviour", str(x2), "--g5", str(g5), "--per-pair", str(pp), "--out", str(tmp_path / "o"), "--no-writeup",
                      "--n-boot", "100", "--seed", "0"])
    g5rows = [r for r in summary["table"] if r["dataset"] == "G5" and r["condition"] == "planted"]
    assert summary["g5"]["continuous_log_odds"] is True
    assert all(r["tost_verdict"] == Z.INERT for r in g5rows)          # shift 0.1*alpha <= 0.5 << 3.25
    assert g5rows[0]["mean_delta"] == pytest.approx(0.05)
