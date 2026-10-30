"""Offline tests for the V6 / V7 analyses (v67_analysis/) on synthetic fixtures with the pod schemas (v6_lo.jsonl rows of s3_score.py --v6,
S1 / S1@L38 family-v7 rows of s3_lo.jsonl, s1_target.jsonl rows, items_v7.json). Everything is written under tmp_path; nothing under
cache/ or results/ or banks/ is touched."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)

from projects.g_agreement.v67_analysis import common as K  # noqa: E402
from projects.g_agreement.v67_analysis import fixtures as F  # noqa: E402
from projects.g_agreement.v67_analysis import v6 as V6  # noqa: E402
from projects.g_agreement.v67_analysis import v7 as V7  # noqa: E402

NB = 200
REAL_ITEMS_V7 = Path(REPO) / "projects" / "g_agreement" / "banks" / "w" / "items_v7.json"


# ------------------------------------------------------------------ win logic and bootstrap
def test_pair_win_orientation_and_ties():
    assert K.pair_win(1.0, -0.5) is True and K.pair_win(-1.0, 0.5) is False
    assert K.pair_win(-0.2, 1.0) is True          # the B side carries the pair
    assert K.pair_win(0.5, -0.5) is False         # a tie is not a win
    assert K.pair_win(None, 1.0) is None and K.pair_win(1.0, None) is None
    flags = K.win_flags({"p1": {"A": 1.0, "B": 0.5}, "p2": {"A": -2.0, "B": 0.5}, "p3": {"A": 1.0}})
    assert flags == [("p1", True), ("p2", False), ("p3", None)]
    assert K.margins({"p1": {"A": 1.0, "B": 0.5}, "p3": {"A": 1.0}}) == {"p1": 1.5}


def test_rate_and_paired_bootstrap():
    all_true = [(f"p{i}", True) for i in range(10)]
    r = K.rate(all_true, NB, 0)
    assert (r["k"], r["n"], r["p"]) == (10, 10, 1.0) and r["boot_lo"] == 1.0 and r["boot_hi"] == 1.0 and r["wilson_lo"] < 1.0 and r["n_excluded"] == 0
    mixed = [(f"p{i}", i < 7) for i in range(10)] + [("p10", None)]
    r = K.rate(mixed, NB, 0)
    assert (r["k"], r["n"], r["n_pairs"], r["n_excluded"]) == (7, 10, 11, 1) and 0.3 < r["boot_lo"] <= 0.7 <= r["boot_hi"] < 1.0
    d = K.rate_diff(mixed, mixed, NB, 0)
    assert d["diff"] == 0.0 and d["lo"] == 0.0 and d["hi"] == 0.0 and not d["excludes_zero"]
    better = [(f"p{i}", True) for i in range(10)]
    d = K.rate_diff(better, mixed, NB, 0)
    assert abs(d["diff"] - 0.3) < 1e-9 and d["lo"] > 0 and d["excludes_zero"]
    # the paired resampling keeps the pair alignment: a difference that is constant per pair has a degenerate CI
    a = [(f"p{i}", i % 2 == 0) for i in range(10)]
    b = [(f"p{i}", i % 2 == 0) for i in range(10)]
    d = K.rate_diff(a, b, NB, 0)
    assert d["diff"] == 0.0 and d["lo"] == 0.0 and d["hi"] == 0.0
    m = K.pair_mean({"p1": [1.0, 3.0], "p2": [2.0]}, NB, 0)
    assert m["n"] == 3 and abs(m["mean"] - 2.0) < 1e-9 and m["lo"] <= m["mean"] <= m["hi"]
    assert K.pair_mean({}, NB, 0)["n"] == 0 and np.isnan(K.pair_mean({}, NB, 0)["mean"])


# ------------------------------------------------------------------ V6
def _v6_summary(tmp_path, name, **kw):
    rows = F.v6_rows(seed=1, **kw)
    p = F.write_jsonl(tmp_path / name / "v6_lo.jsonl", rows)
    return rows, V6.run(p, tmp_path / name / "out", NB, 0)


def test_v6_schema_counts_and_rule_met(tmp_path):
    rows, s = _v6_summary(tmp_path, "met")
    assert s["n_natural_rows"] == 64 * 4 and s["n_edited_rows"] == 32 * 4
    assert all(r["unit"] == "V6" and r["reader"] == "olens" and r["family"] == "ownership" and r["layer"] == 38 for r in rows)
    for c in V6.CONDITIONS:
        n = s["natural"][c]
        assert n["n"] == 32 and n["n_states"] == 64 and n["n_pairs"] == 32 and len(n["per_pair"]) == 32
        assert n["wilson_lo"] <= n["p"] <= n["wilson_hi"] and n["boot_lo"] <= n["p"] <= n["boot_hi"]
    assert s["natural"]["a_last"]["mean_n_markers"] == 1.0 and s["natural"]["c_full"]["mean_n_markers"] == 34.0 and s["natural"]["b_span"]["mean_n_markers"] == 6.0
    r = s["rule"]
    assert r["gain_ok"] and r["shuffled_below_span"] and r["met"] and r["verdict"] == "span reading helps"
    assert abs(s["diffs"]["b_span-a_last"]["diff"] - (s["natural"]["b_span"]["p"] - s["natural"]["a_last"]["p"])) < 1e-9
    assert set(s["diffs"]) == {"b_span-a_last", "b_span-d_span_shuffled", "c_full-a_last", "d_span_shuffled-a_last"}
    # outputs
    out = tmp_path / "met" / "out"
    md = (out / "v6.md").read_text().splitlines()
    assert len(md) <= 30 and "span reading helps" in "\n".join(md) and (out / "v6.csv").exists()
    csv = (out / "v6.csv").read_text().splitlines()
    assert len(csv) == 1 + 4 + 4 + 4 and csv[0].startswith("block,condition,label")
    js = json.loads((out / "v6_summary.json").read_text())
    assert js["rule"]["met"] is True and js["meta"]["n_boot"] == NB and js["meta"]["inputs"]["v6_lo"]["sha256"]


def test_v6_rule_not_met_when_flat_or_shuffle_not_below(tmp_path):
    flat = {c: (0.8, 1.0) for c in V6.CONDITIONS}
    _, s = _v6_summary(tmp_path, "flat", effect=flat)
    assert not s["rule"]["gain_ok"] and not s["rule"]["met"] and s["rule"]["verdict"] == "NOT MET"
    # (b) beats (a) clearly but the shuffled control is at least as good as (b): rule fails on the second clause
    eff = {"a_last": (-0.5, 0.8), "b_span": (2.0, 0.3), "c_full": (1.0, 1.0), "d_span_shuffled": (3.0, 0.3)}
    _, s = _v6_summary(tmp_path, "shuf", effect=eff)
    assert s["rule"]["gain_ok"] and not s["rule"]["shuffled_below_span"] and not s["rule"]["met"]


def test_v6_edited_follow_uses_lo_toward_edit_and_pairs_with_natural(tmp_path):
    follow = {"a_last": 1.0, "b_span": 1.0, "c_full": 0.0, "d_span_shuffled": 1.0}
    rows, s = _v6_summary(tmp_path, "ed", follow=follow)
    e = s["edited"]
    assert e["b_span"]["n_states"] == 32 and e["b_span"]["follow"]["p"] == 1.0 and e["c_full"]["follow"]["p"] == 0.0
    # follow = −lo_own > 0 on the edited rows
    ed_b = [r for r in rows if r["condition"] == "b_span" and r["state_kind"] == "edited_full_a1"]
    assert all(-r["lo_own"] > 0 for r in ed_b) and all(r["s2_key"] == r["state_key"] and "|W2|full|1.0|" in r["s2_key"] for r in ed_b)
    # shift = edited − natural (same state, same condition) < 0; with follow = 1 and a strongly positive natural b_span this is 1.0
    assert e["b_span"]["shift"]["p"] == 1.0 and e["b_span"]["delta_lo_own"]["mean"] < 0 and e["b_span"]["delta_lo_own"]["hi"] < 0
    assert e["b_span"]["natural_own_side"]["n"] == 32 and e["b_span"]["n_missing_natural"] == 0
    # an edited state whose natural row is missing is excluded from shift / natural-own-side but kept for follow
    rows2 = [r for r in rows if not (r["state_kind"] == "natural" and r["pair_id"] == "xown-0001" and r["source"] == "A" and r["condition"] == "a_last")]
    s2 = V6.analyse(rows2, NB, 0)
    assert s2["edited"]["a_last"]["n_missing_natural"] == 1 and s2["edited"]["a_last"]["shift"]["n"] == 31 and s2["edited"]["a_last"]["follow"]["n"] == 32
    assert s2["natural"]["a_last"]["n"] == 31 and s2["natural"]["a_last"]["n_excluded"] == 1


def test_v6_missing_input_writes_nothing(tmp_path):
    with pytest.raises(FileNotFoundError):
        V6.run(tmp_path / "nope.jsonl", tmp_path / "out", NB, 0)
    assert not (tmp_path / "out").exists()
    with pytest.raises(Exception):
        V6.run(F.write_jsonl(tmp_path / "bad.jsonl", [{"unit": "V6", "reader": "olens", "condition": "e_other"}]), tmp_path / "out2", NB, 0)


# ------------------------------------------------------------------ V7
def _v7_fixture(tmp_path, name, win=F.V7_DEFAULT_WIN, with_s1=True, accuracy=1.0, items=None, unscorable={}):
    d = tmp_path / name
    its = items or F.v7_items()
    paths = {"s3_lo": F.write_jsonl(d / "s3_lo.jsonl", F.v7_lo_rows(its["items"], win=win, seed=2, unscorable=unscorable)), "items": d / "items_v7.json"}
    paths["items"].write_text(json.dumps(its))
    paths["s1"] = F.write_jsonl(d / "s1_target.jsonl", F.s1_target_rows(its["items"], accuracy, 2)) if with_s1 else d / "missing_s1.jsonl"
    paths["out"], paths["design"] = d / "out", d / "design" / "items_v7_confirmatory_design.md"
    return paths


def test_v7_positive_pilot_writes_design(tmp_path):
    p = _v7_fixture(tmp_path, "pos")
    s = V7.run(p["s3_lo"], p["items"], p["s1"], p["out"], p["design"], NB, 0)
    assert s["n_pairs"] == 16 and s["baseline"]["n_prompt_text_identical"] == 16 and s["baseline"]["all_identical"]
    cells = s["cells"]
    assert set(cells) >= {"jlens@L42", "jlens@L38", "olens@L42", "olens@L38", "skip_a@L42", "probe@L42", "probe@L38", "nla@L42"}
    assert cells["nla@L42"]["scored"] is False and "phase B" in cells["nla@L42"]["reason"]
    for k, c in cells.items():
        if c["scored"]:
            assert c["n"] == 16 and c["n_pairs_total"] == 16 and c["wilson_lo"] <= c["p"] <= c["wilson_hi"]
            assert c["positive"] == (c["p"] >= 0.70 and c["boot_lo"] > 0.5)
    assert cells["probe@L38"]["positive"] and s["rule"]["met"] and s["rule"]["positive_cells"]
    assert s["design_file"] == str(p["design"]) and p["design"].exists()
    txt = p["design"].read_text()
    for needle in ("8 name sets", "3 object pairs", "2 mention orders", "Both preamble roles", "48 pairs", "50 %", "0.70"):
        assert needle in txt, needle
    # ceiling from the S1 rows: accuracy 1 → 32/32; pair win in the OWN frame (−lo_model) 16/16
    t = s["target_ceiling"]
    assert t["available"] and t["accuracy"]["k"] == 32 and t["accuracy"]["n"] == 32 and t["pair_win_lo_model"]["k"] == 16
    md = (p["out"] / "v7.md").read_text().splitlines()
    assert len(md) <= 30 and "POSITIVE" in "\n".join(md) and "50.0% by construction" in "\n".join(md) and "not scored" in "\n".join(md)
    csv = (p["out"] / "v7.csv").read_text().splitlines()
    assert csv[0].startswith("reader,layer,cell") and any(l.startswith("prompt_only,") for l in csv) and sum(l.startswith("target,") for l in csv) == 2
    js = json.loads((p["out"] / "v7_summary.json").read_text())
    assert js["rule"]["met"] is True and js["meta"]["inputs"]["s3_lo"]["sha256"]


def test_v7_null_pilot_no_design_and_missing_s1(tmp_path):
    null = {k: 0.0 for k in F.V7_DEFAULT_WIN}  # deterministic: every reader loses every pair (a p = 0.5 draw can reach 12/16 by chance)
    p = _v7_fixture(tmp_path, "null", win=null, with_s1=False)
    s = V7.run(p["s3_lo"], p["items"], p["s1"], p["out"], p["design"], NB, 0)
    assert not s["rule"]["met"] and s["rule"]["positive_cells"] == [] and s["design_file"] is None and not p["design"].exists()
    assert s["target_ceiling"]["available"] is False
    md = (p["out"] / "v7.md").read_text()
    assert "NOT MET" in md and "not available" in md and len(md.splitlines()) <= 30
    # a 100 % reader with a wide CI at n = 16 still passes (boot lo > 0.5); a 68.75 % reader does not reach 0.70
    s2 = V7.analyse(V7.load_items(p["items"]), F.v7_lo_rows(json.loads(p["items"].read_text())["items"], win={("olens", 42): 1.0}, seed=3), None, NB, 0)
    assert s2["cells"]["olens@L42"]["p"] == 1.0 and s2["cells"]["olens@L42"]["positive"]


def test_v7_threshold_edge_and_unscorable_rows(tmp_path):
    items = F.v7_items()
    rows = F.v7_lo_rows(items["items"], win={("olens", 42): 1.0}, seed=4)
    by = {(r["pair_id"], r["version"]): r for r in rows}
    # force exactly 11/16 wins (68.75 %) → below 0.70 → not positive; then 12/16 (75 %) with the CI above 0.5 → positive
    for i in range(1, 6):
        for v in "AB":
            by[(f"wv7-{i:02d}", v)]["lo_own"] = -2.0
    s = V7.analyse(V7.load_items(_write_items(tmp_path, items)), rows, None, NB, 0)
    c = s["cells"]["olens@L42"]
    assert c["k"] == 11 and abs(c["p"] - 11 / 16) < 1e-9 and not c["positive"]
    for v in "AB":
        by[("wv7-05", v)]["lo_own"] = 2.0
    s = V7.analyse(V7.load_items(_write_items(tmp_path, items)), rows, None, NB, 0)
    c = s["cells"]["olens@L42"]
    assert c["k"] == 12 and c["positive"] == (c["boot_lo"] > 0.5)
    # unscorable rows drop the pair from the denominator and are counted
    rows_u = F.v7_lo_rows(items["items"], win={("jlens", 42): 1.0}, seed=4, unscorable={("jlens", 42): ["wv7-01A", "wv7-02B"]})
    s = V7.analyse(V7.load_items(_write_items(tmp_path, items)), rows_u, None, NB, 0)
    c = s["cells"]["jlens@L42"]
    assert c["n"] == 14 and c["n_unscorable_rows"] == 2 and c["n_missing_rows"] == 0 and c["per_pair"]["wv7-01"]["win"] is None


def _write_items(tmp_path, items):
    p = tmp_path / "items_tmp.json"
    p.write_text(json.dumps(items))
    return p


def test_v7_target_ceiling_orientation():
    items = F.v7_items(4)["items"]
    pair_ids = sorted({it["pair_id"] for it in items})
    # lo_model = lp(other) − lp(own): NEGATIVE means the target favours its own answer → own-frame win
    rows = [{"family": "v7", "pair_id": it["pair_id"], "version": it["version"], "correct": True, "lo_model": -2.0, "lo_model_unscorable": False, "parsed": it["primary"]["answer"],
             "true_answer": it["primary"]["answer"]} for it in items]
    t = V7.target_ceiling(rows, pair_ids, NB, 0)
    assert t["pair_win_lo_model"]["k"] == 4 and t["accuracy"]["k"] == 8
    for r in rows:
        r["lo_model"] = +2.0
        r["correct"] = False
    t = V7.target_ceiling(rows, pair_ids, NB, 0)
    assert t["pair_win_lo_model"]["k"] == 0 and t["accuracy"]["k"] == 0 and t["accuracy"]["n"] == 8
    rows[0]["lo_model_unscorable"] = True
    t = V7.target_ceiling(rows, pair_ids, NB, 0)
    assert t["pair_win_lo_model"]["n"] == 3
    assert V7.target_ceiling([{"family": "counts"}], pair_ids, NB, 0)["available"] is False


@pytest.mark.skipif(not REAL_ITEMS_V7.exists(), reason="real items_v7.json not present")
def test_v7_real_bank_schema(tmp_path):
    """The real bank parses: 16 pairs, visible prompt identical within every pair; fixture rows built from the real items run through the analysis."""
    pairs = V7.load_items(REAL_ITEMS_V7)
    assert len(pairs) == 16 and V7.prompt_identity(pairs)["all_identical"]
    items = json.loads(REAL_ITEMS_V7.read_text())["items"]
    rows = F.v7_lo_rows(items, win={("olens", 42): 0.9, ("probe", 38): 0.9}, seed=5)
    s = V7.analyse(pairs, rows, F.s1_target_rows(items, 0.9, 5), NB, 0)
    assert s["cells"]["olens@L42"]["n"] == 16 and s["cells"]["probe@L38"]["n"] == 16 and s["target_ceiling"]["accuracy"]["n"] == 32
    assert all(c["scored"] is False for k, c in s["cells"].items() if k not in ("olens@L42", "probe@L38"))


def test_v7_missing_inputs_write_nothing(tmp_path):
    with pytest.raises(FileNotFoundError):
        V7.run(tmp_path / "no.jsonl", REAL_ITEMS_V7 if REAL_ITEMS_V7.exists() else tmp_path / "no_items.json", None, tmp_path / "out", tmp_path / "design.md", NB, 0)
    assert not (tmp_path / "out").exists() and not (tmp_path / "design.md").exists()


# ------------------------------------------------------------------ CLIs on the fixture writer
def test_cli_entry_points_on_fixture(tmp_path):
    paths = F.write_fixture(tmp_path / "fx", seed=0)
    assert V6.main(["--lo", str(paths["v6_lo"]), "--out", str(tmp_path / "o6"), "--n-boot", str(NB)]) == 0
    assert V7.main(["--lo", str(paths["s3_lo"]), "--items", str(paths["items_v7"]), "--s1", str(paths["s1_target"]), "--out", str(tmp_path / "o7"),
                    "--design-out", str(tmp_path / "o7" / "design.md"), "--n-boot", str(NB)]) == 0
    assert (tmp_path / "o6" / "v6.md").exists() and (tmp_path / "o7" / "v7.md").exists()
    js = json.loads((tmp_path / "o6" / "v6_summary.json").read_text())
    assert js["meta"]["command"].startswith("python") and "--lo" in js["meta"]["command"]
    with pytest.raises(SystemExit):
        F.main(["--out", str(Path(REPO) / "results" / "g_agreement" / "v" / "fixture_should_not_exist")])
    assert not (Path(REPO) / "results" / "g_agreement" / "v" / "fixture_should_not_exist").exists()
