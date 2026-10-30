"""Synthetic rows for WS3's R5X analysis (r_bench/r5x_analyze.py): escalation, forward gate, verdicts at α*₇₅."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from projects.g_agreement.r_bench import r5x_analyze as X  # noqa: E402
from projects.g_agreement.tests import _write_guard as WG  # noqa: E402

_GUARD = WG.ModuleWriteGuard([REPO / "results" / "g_agreement", REPO / "cache" / "g_agreement"])
_write_guard = _GUARD.fixture()

N = 20


def _steer(ds, flips, collapse=None):
    """flips: {alpha: share of items whose LO crosses under d_probe}; collapse: {alpha: share collapsed (d_probe rows)}."""
    rows = []
    for i in range(N):
        lab = i % 2
        side = 1 if lab == 1 else -1
        rows.append({"dataset": ds, "item_id": f"{ds}-{i}", "label": lab, "direction": "natural", "alpha": 0.0, "sign": -side,
                     "lp_pos": -0.1 if lab else -5.0, "lp_neg": -5.0 if lab else -0.1, "lo": 4.9 * side})
        for a, fr in flips.items():
            for d in ("d_probe_L38", "d_cm_L38", "d_jlens_L38"):
                flip = i < round(fr * N) if d == "d_probe_L38" else False
                col = d == "d_probe_L38" and collapse is not None and i < round(collapse.get(a, 0) * N)
                lo = -2.0 * side if flip else 3.0 * side
                rows.append({"dataset": ds, "item_id": f"{ds}-{i}", "label": lab, "direction": d, "alpha": a, "sign": -side,
                             "lp_pos": -30.0 if col else (lo if lo > 0 else 0.0) - 1, "lp_neg": -30.0 if col else (-lo if lo < 0 else 0.0) - 1,
                             "lo": lo})
    return pd.DataFrame(rows)


def _items(dss):
    return pd.DataFrame({"dataset": dss, "sided": ["two"] * len(dss)})


def test_escalation_alpha_star_and_status():
    st = _steer("f1", {4.0: 0.2, 8.0: 0.55, 16.0: 0.8})
    nat = X._natural(st, pd.DataFrame(), {})
    dose = X.dose_table(st, pd.DataFrame(), nat, _items(["f1"]), {"f1": "S2"})
    f = X.fact_table(dose).iloc[0]
    assert f.alpha_star_50 == 8.0 and f.alpha_star_75 == 16.0 and f.status == "OPERATING DOSE" and f.stratum == "S2"


def test_gate_stops_escalation():
    st = _steer("f2", {4.0: 0.2, 8.0: 0.9}, collapse={8.0: 1.0})  # d_probe collapses at 8: 20 of 60 rows → share 0.33 > 0.25
    dose = X.dose_table(st, pd.DataFrame(), X._natural(st, pd.DataFrame(), {}), _items(["f2"]), {"f2": "S1"})
    f = X.fact_table(dose).iloc[0]
    assert f.first_not_interpretable == 8.0 and np.isnan(f.alpha_star_75) and f.status == "NOT INTERPRETABLE"


def test_still_undefined_at_32():
    st = _steer("f3", {4.0: 0.1, 8.0: 0.1, 16.0: 0.2, 32.0: 0.4})
    dose = X.dose_table(st, pd.DataFrame(), X._natural(st, pd.DataFrame(), {}), _items(["f3"]), {"f3": "S1"})
    f = X.fact_table(dose).iloc[0]
    assert f.status == "STILL UNDEFINED" and f.best_alpha == 32.0 and abs(f.best_flip_rate - 0.4) < 1e-9


def test_reader_blind_at_operating_dose():
    st = _steer("f4", {4.0: 0.8})
    nat = X._natural(st, pd.DataFrame(), {})
    rr = []
    for i in range(N):
        lab = i % 2
        s = 1.0 if lab else -1.0
        rr.append({"reader": "jlens", "dataset": "f4", "item_id": f"f4-{i}", "direction": "natural", "alpha": 0.0, "lo": 2 * s, "lp_A": 0.0})
        rr.append({"reader": "jlens", "dataset": "f4", "item_id": f"f4-{i}", "direction": "d_probe_L38", "alpha": 4.0, "lo": 2 * s, "lp_A": 0.0})
    dose = X.dose_table(st, pd.DataFrame(rr), nat, _items(["f4"]), {"f4": "S1"})
    v = X.verdict_table(dose, X.fact_table(dose)).iloc[0]
    assert v.reader_blind is True or v.reader_blind == True  # noqa: E712  (reader does not move under d_probe)


def test_zz_results_untouched():
    _GUARD.assert_clean()


def test_natural_source_by_stratum():
    """S1 takes R5's natural rows, S2 R5X's own; the other source only fills a missing item (WS4 7398cf8)."""
    x = _steer("s2", {4.0: 0.1})
    x1 = _steer("s1", {4.0: 0.1})
    r5 = pd.concat([_steer("s1", {}), _steer("s2", {})]).assign(lo=99.0)  # R5's naturals, marked
    nat = X._natural(pd.concat([x, x1]), r5, {"s1": "S1", "s2": "S2"})
    assert (nat.loc["s1", "lo"] == 99.0).all() and (nat.loc["s2", "lo"] != 99.0).all()
    assert X.NATURAL_SOURCE["s1"] == {"preferred": "R5", "n_preferred": N, "n_fallback": 0}
