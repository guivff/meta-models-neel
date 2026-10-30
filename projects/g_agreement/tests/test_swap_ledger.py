"""WS3's SWAP false-positive ledger: the pre-registered TRUTH / CANDIDATE-NAME PRIOR / OTHER rule and the causal join."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from projects.g_agreement.r_bench import swap_ledger as SL  # noqa: E402
from projects.g_agreement.tests import _write_guard as WG  # noqa: E402

_GUARD = WG.ModuleWriteGuard([REPO / "results" / "g_agreement", REPO / "cache" / "g_agreement"])
_write_guard = _GUARD.fixture()


def test_classify_rule():
    c = SL.classify([" Chile", "Brazil", " Peru", " currency", "chile"], "chile", "brazil", {"chile", "brazil", "peru"}, {"peru"})
    assert [x["cls"] for x in c] == ["TRUTH", "CANDIDATE-NAME PRIOR", "CANDIDATE-NAME PRIOR", "OTHER", "TRUTH"]
    assert c[1]["own_distractor"] and not c[2]["own_distractor"] and c[2]["in_state_free"]
    assert [x["causal_status"] for x in c] == ["TESTED (truth)", "TESTED (own distractor)", "UNTESTED", "UNTESTED", "TESTED (truth)"]


def test_causal_join():
    led = []
    for i in range(10):
        toks = [("TRUTH" if i < 6 else "OTHER"), "OTHER", "OTHER", "OTHER", "OTHER"]
        for r, c in enumerate(toks):
            led.append({"control": "jlens", "position": "rp", "layer": 24, "item": f"i{i}", "rank": r + 1, "cls": c,
                        "own_distractor": False, "causal_status": "TESTED (truth)" if c == "TRUTH" else "UNTESTED"})
    fl = pd.DataFrame([{"item": f"i{i}", "layer": 24.0, "arm": a, "pair": "answer", "flipped": (a == "d_swap" and i < 3)}
                       for i in range(10) for a in ("d_swap", "d_rand0", "d_rand1", "d_rand2")])
    cz = SL.causal_table(pd.DataFrame(led), fl)
    r = cz[cz.layer == 24].iloc[0]
    assert r.n_truth_in_top5 == 6 and abs(r.causal_hit_rate - 0.5) < 1e-12 and r.ctl_a_no_truth_rate == 0 and r.ctl_b_random_rate_same_items == 0
    assert r.untested_tokens == 44 and r.tokens == 50
    assert np.isnan(cz[cz.layer == 28].iloc[0].causal_hit_rate)


def test_zz_results_untouched():
    _GUARD.assert_clean()
