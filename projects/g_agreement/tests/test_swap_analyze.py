"""Synthetic rows for WS3's SWAP analysis (r_bench/swap_analyze.py): flips, swap effect, R-S5, reader tracking."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from projects.g_agreement.r_bench import swap_analyze as S  # noqa: E402
from projects.g_agreement.tests import _write_guard as WG  # noqa: E402

_GUARD = WG.ModuleWriteGuard([REPO / "results" / "g_agreement", REPO / "cache" / "g_agreement"])
_write_guard = _GUARD.fixture()
N = 40


def _khop(swap_flip=0.6, logit_flip=0.2):
    rows = []
    for i in range(N):
        it = f"i{i}"
        rows.append({"item": it, "layer": np.nan, "arm": "natural", "prefers_bridge_true": i != 0, "prefers_answer_true": True})
        for arm, fr in (("d_swap", swap_flip), ("d_logit", logit_flip), ("d_rand0", 0.0), ("d_rand1", 0.0), ("d_rand2", 0.0)):
            rows.append({"item": it, "layer": 32.0, "arm": arm, "prefers_bridge_true": not (i < fr * N),
                         "prefers_answer_true": not (arm == "d_swap" and i < 0.5 * N)})
    return pd.DataFrame(rows)


def test_flip_needs_natural_true():
    fl = S.khop_flips(_khop())
    f = fl[(fl.arm == "d_swap") & (fl.pair == "bridge")].set_index("item").flipped
    assert not f["i0"] and f["i1"] and f.sum() == round(0.6 * N) - 1  # item 0 already prefers the distractor naturally


def test_effect_and_r_s5():
    fl = S.khop_flips(_khop())
    e = S.effects(fl, "khop")
    r = e[(e.arm == "d_swap") & (e.pair == "bridge")].iloc[0]
    assert abs(r.flip_rate - (round(0.6 * N) - 1) / N) < 1e-12 and r.random_flip_rate == 0 and r.ci_lo > 0
    assert set(e.arm) == {"d_swap", "d_logit"} and set(e.pair) == {"bridge"}  # answer pair only for d_answer
    s5 = S.r_s5(fl)
    assert not s5[s5.control == "d_logit"].iloc[0].control_larger


def test_reader_tracking():
    fl = S.khop_flips(_khop())
    rr = []
    for i in range(N):
        for arm in ("natural", "d_swap", "d_rand0", "d_rand1", "d_rand2"):
            for pair in ("bridge", "answer"):
                lo = 2.0
                if arm == "d_swap" and pair == "bridge" and i % 2 == 0:
                    lo = -1.0  # the reader crosses on half the items
                rr.append({"reader": "jlens", "item": f"i{i}", "layer": np.nan if arm == "natural" else 32.0, "arm": arm, "pair": pair, "lo": lo})
    t = S.readers_table(pd.DataFrame(rr), fl).iloc[0]
    assert t.n_flipped == round(0.5 * N) and t.random_band == [0.0, 0.0]  # answer-flipped items (R-S2's denominator)
    assert t.verdict in ("TRACKS THE WORKSPACE", "WORKSPACE-BLIND") and t.stage_sep > 0


def test_zz_results_untouched():
    _GUARD.assert_clean()
