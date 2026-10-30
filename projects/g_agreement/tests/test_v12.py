"""V1/V2 (PREREG_WV.md Part V) tests, CPU only, on synthetic rows: row normalisation across the x3_lo / y1_lo / pod schemas,
the statistics (rate bootstrap, paired difference, sign-flip permutation null, first crossing), the V1 sweep end to end with a
planted crossing delivered through --extra-lo, the V2 re-solving rule with the k-1 identity and a three-way file, and the pod
request builder. Every path is a tmp_path; results/ and cache/ are asserted untouched.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_v12.py -q``
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

from projects.g_agreement.v12_readers import common as K  # noqa: E402
from projects.g_agreement.v12_readers import pod_requests as PR  # noqa: E402
from projects.g_agreement.v12_readers import v1_sweep as V1  # noqa: E402
from projects.g_agreement.v12_readers import v2_resolve as V2  # noqa: E402

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement" / "v").rglob("*")) if (REPO / "results" / "g_agreement" / "v").exists() else []
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement" / "y").glob("*.jsonl")) if (REPO / "cache" / "g_agreement" / "y").exists() else []
SYMS = list("ABCDEFGH")


# ------------------------------------------------------------------ fixtures
def _puzzle(i: int, set_: str, km1_is_actual: bool, rng: np.random.Generator) -> dict:
    correct, km1, wrong = (rng.permutation(SYMS)[:3]).tolist()
    actual = correct if set_ == "error_control" else (km1 if km1_is_actual else wrong)
    other = wrong if set_ == "error_control" else correct
    return {"item_id": f"xpz-{i:04d}", "family": "puzzle", "set": set_, "split": "test",
            "primary": {"name": "model_actual_answer", "candidates": [actual, other], "answer": actual, "answer_source": "target_greedy"},
            "source": {"correct": correct, "k": 3, "start": "A", "trace": ["A", "B", km1, correct], "distractors": []}}


def _choice(i: int, set_: str) -> dict:
    a, b = ("apple", "pear") if i % 2 else ("blue", "red")
    return {"item_id": f"xch-{i:04d}", "family": "choice", "set": set_, "split": "test",
            "primary": {"name": "model_actual_answer", "candidates": [a, b], "answer": a}, "source": {"self_guess": b if set_ == "disagree" else a}}


def make_items(n_err: int = 40, n_ctl: int = 12, n_dis: int = 20, n_agr: int = 10, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    items = [_puzzle(i, "error", i % 2 == 0, rng) for i in range(n_err)]
    items += [_puzzle(1000 + i, "error_control", False, rng) for i in range(n_ctl)]
    items += [_choice(i, "disagree") for i in range(n_dis)] + [_choice(500 + i, "agree_control") for i in range(n_agr)]
    return {"meta": {"seed": seed}, "items": items}


def lo_row(reader: str, site: str, it: dict, lo: float, unscorable: bool = False, x3: bool = False) -> dict:
    p = it["primary"]
    other = next(c for c in p["candidates"] if c != p["answer"])
    r = {"reader": reader, "item_id": it["item_id"], "family": it["family"], "set": it["set"], "cand_actual": p["answer"], "cand_other": other,
         "lo_actual": (None if unscorable else lo), "favours_actual": (None if unscorable else lo > 0), "unscorable": unscorable}
    if x3:
        r["layer"] = 42
    else:
        L, P = site.split(":")
        r.update({"site": site, "layer": int(L), "position": P, "layer_used": (None if reader == "nla" else int(L)), "key": f"{reader}|{site}|{it['item_id']}"})
    return r


def write_jsonl(path: Path, rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return path


def write_sweep(dirp: Path, probe_by_layer: dict, sets=("error", "disagree")) -> None:
    dirp.mkdir(parents=True, exist_ok=True)
    for s in sets:
        with open(dirp / f"sweep_{s}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["layer", "position", "set", "status", "n", "k", "rate", "boot_lo", "boot_hi", "perm_p95", "control_rate"])
            w.writeheader()
            for L, p in probe_by_layer[s].items():
                w.writerow({"layer": L, "position": "0", "set": s, "status": "ok", "n": 100, "k": int(100 * p), "rate": p, "boot_lo": p - 0.05, "boot_hi": p + 0.05,
                            "perm_p95": 0.6, "control_rate": 0.7})
                w.writerow({"layer": L, "position": "3", "set": s, "status": "ok", "n": 100, "k": 99, "rate": 0.99, "boot_lo": 0.9, "boot_hi": 1.0, "perm_p95": 0.6, "control_rate": 0.7})
    with open(dirp / "logitlens.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["set", "layer", "n", "k_pos", "frac_pos", "boot_lo", "boot_hi", "is_final_layer"])
        w.writeheader()
        for s in sets + ("error_control", "agree_control"):
            for L in list(K.LAYERS) + [63]:
                w.writerow({"set": s, "layer": L, "n": 100, "k_pos": 50, "frac_pos": 0.5, "boot_lo": 0.4, "boot_hi": 0.6, "is_final_layer": L == 63})


# ------------------------------------------------------------------ items / rows
def test_item_roles_and_construction_check(tmp_path):
    obj = make_items()
    p = tmp_path / "items.json"
    p.write_text(json.dumps(obj))
    _, items = K.load_items(p)
    c = K.check_item_roles(items)
    assert c == {"error": 40, "error_control": 12, "km1_eq_actual": 20, "km1_ne_actual": 20}
    err = next(it for it in items.values() if it["set"] == "error")
    assert err["roles"]["other"] == err["roles"]["correct"] and err["roles"]["km1"] == err["source"]["trace"][-2]
    # a broken ERROR item (actual == correct) is refused
    bad = json.loads(p.read_text())
    bad["items"][0]["primary"]["answer"] = bad["items"][0]["source"]["correct"]
    bad["items"][0]["primary"]["candidates"] = [bad["items"][0]["source"]["correct"], "Z"]
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    _, items_bad = K.load_items(tmp_path / "bad.json")
    with pytest.raises(ValueError):
        K.check_item_roles(items_bad)


def test_normalise_row_three_schemas():
    it = make_items()["items"][0]
    x3 = K.normalise_row(lo_row("olens", "", it, 0.3, x3=True), "x3_lo")
    assert (x3["site"], x3["layer"], x3["position"], x3["layer_used"]) == ("42:0", 42, "0", 42)
    y1 = K.normalise_row(lo_row("jlens", "48:0", it, -0.2), "y1_lo")
    assert (y1["site"], y1["layer"], y1["position"], y1["lo_actual"], y1["unscorable"]) == ("48:0", 48, "0", -0.2, False)
    cand = K.normalise_row(lo_row("jlens", "42:candA", it, 0.1), "y1_lo")
    assert cand["position"] == "candA"
    uns = K.normalise_row(lo_row("jlens", "56:0", it, 0.0, unscorable=True), "extra:pod")
    assert uns["unscorable"] and uns["lo_actual"] is None
    assert K.normalise_row({"reader": "jlens", "condition": "mean_state", "set": "error"}, "y1_lo") is None
    nla = K.normalise_row(lo_row("nla", "", it, 0.3, x3=True), "x3_lo")
    assert nla["layer_used"] is None


def test_load_lo_rows_precedence_and_filter(tmp_path):
    obj = make_items()
    items_p = tmp_path / "items.json"
    items_p.write_text(json.dumps(obj))
    _, items = K.load_items(items_p)
    its = obj["items"]
    x3 = write_jsonl(tmp_path / "x3_lo.jsonl", [lo_row("jlens", "", its[0], 0.5, x3=True), lo_row("jlens", "", {**its[1], "item_id": "xpz-9999"}, 0.5, x3=True)])
    y1 = write_jsonl(tmp_path / "y1_lo.jsonl", [lo_row("jlens", "48:0", its[0], -0.5), {"reader": "jlens", "condition": "mean_state", "set": "error", "key": "m"}])
    extra = write_jsonl(tmp_path / "pod.jsonl", [lo_row("jlens", "42:0", its[0], 0.7)])  # re-scored 42:0 from y1_caps overrides x3
    rows, info = K.load_lo_rows(x3, y1, [extra], items=items)
    assert len(rows) == 2 and info["dropped_not_in_items"] == 1 and info["overrides"] == 1 and info["override_sign_agree"] == 1
    r42 = next(r for r in rows if r["layer"] == 42)
    assert r42["source"].startswith("extra:") and r42["superseded"] == "x3_lo" and r42["lo_actual"] == 0.7


# ------------------------------------------------------------------ statistics
def test_rate_paired_diff_and_wilson():
    d = K.rate([True] * 30 + [False] * 10, n_boot=500, seed=1)
    assert d["k"] == 30 and d["n"] == 40 and abs(d["p"] - 0.75) < 1e-12 and d["boot_lo"] < 0.75 < d["boot_hi"] and 0.59 < d["wilson_lo"] < 0.62
    e = K.rate([], n_boot=10)
    assert e["n"] == 0 and np.isnan(e["p"])
    pd = K.paired_diff([True] * 32 + [False] * 8, [False] * 32 + [True] * 8, n_boot=500, seed=0)
    assert abs(pd["diff"] - 0.6) < 1e-9 and pd["diff_lo"] > 0
    same = K.paired_diff([True, False] * 20, [True, False] * 20, n_boot=200, seed=0)
    assert same["diff"] == 0 and same["diff_lo"] == 0 == same["diff_hi"]
    with pytest.raises(ValueError):
        K.paired_diff([True], [True, False])


def test_permutation_null_sign_flip():
    rng = np.random.default_rng(0)
    # strong preference for the OTHER candidate: statistic P(lo<0) - P(lo>0) near +0.8 -> small p
    lo = -np.abs(rng.normal(size=100)) + 0.0
    lo[:10] = np.abs(lo[:10])
    r = K.permutation_null(lo, n_perm=200, seed=0)
    assert abs(r["obs"] - 0.8) < 1e-12 and r["p_value"] < 0.02 and r["null_abs_p95"] < 0.3
    # exactly balanced log-odds -> statistic 0 -> p = 1
    lo2 = np.concatenate([np.ones(100), -np.ones(100)])
    r2 = K.permutation_null(lo2, n_perm=200, seed=0)
    assert r2["obs"] == 0.0 and r2["p_value"] == 1.0
    assert np.isnan(K.permutation_null([], n_perm=5)["p_value"])
    # the stat ignores ties
    assert K.two_way_stat(np.array([0.0, 0.0, 1.0, -1.0])) == 0.0


def test_first_crossing_and_nearest_grid():
    curve = {42: {"p": 0.5}, 44: {"p": 0.74}, 46: {"p": 0.75}, 48: {"p": 0.9}}
    assert K.first_crossing(curve) == 46 and K.first_crossing({42: {"p": 0.2}}) is None and K.first_crossing({}) is None
    assert {L: K.nearest_grid_layer(L) for L in K.LAYERS} == {42: 44, 44: 44, 46: 44, 48: 48, 50: 48, 52: 52, 54: 52, 56: 56, 58: 56, 60: 60, 62: 60}
    Y = pytest.importorskip("projects.g_agreement.y1_site.collect")
    assert all(K.nearest_grid_layer(L) == Y.nearest_grid_layer(L) for L in range(40, 64))


# ------------------------------------------------------------------ V1 end to end
def _v1_env(tmp_path: Path, plant_layer: int | None):
    obj = make_items()
    its = obj["items"]
    items_p = tmp_path / "items.json"
    items_p.write_text(json.dumps(obj))
    rng = np.random.default_rng(1)
    x3_rows, y1_rows, pod_rows = [], [], []
    for it in its:
        for rd in ("jlens", "olens", "nla"):
            x3_rows.append(lo_row(rd, "", it, float(rng.normal()), x3=True))          # ~50% at 42
            y1_rows.append(lo_row(rd, "48:0", it, float(rng.normal()), unscorable=(rd == "jlens" and it["family"] == "choice" and it["item_id"].endswith("1"))))
            y1_rows.append(lo_row(rd, "42:candA", it, 5.0))                            # must be ignored by the last-token sweep
            for L in K.LAYERS:
                if L in (42, 48):
                    continue
                lo = (abs(rng.normal()) + 0.1) if (plant_layer is not None and L >= plant_layer and rd == "jlens" and it["set"] == "error") else float(rng.normal())
                pod_rows.append(lo_row(rd, f"{L}:0", it, lo))
    x3 = write_jsonl(tmp_path / "x3_lo.jsonl", x3_rows)
    y1 = write_jsonl(tmp_path / "y1_lo.jsonl", y1_rows)
    pod = write_jsonl(tmp_path / "pod_lo.jsonl", pod_rows)
    probe = {"error": {L: (0.6 if L < 50 else 0.9) for L in K.LAYERS}, "disagree": {L: 0.5 for L in K.LAYERS}}
    write_sweep(tmp_path / "y1", probe)
    return items_p, x3, y1, pod


def test_v1_partial_then_complete(tmp_path):
    items_p, x3, y1, pod = _v1_env(tmp_path, plant_layer=54)
    out = tmp_path / "v"
    base = ["--items", str(items_p), "--x3-lo", str(x3), "--y1-lo", str(y1), "--sweep-dir", str(tmp_path / "y1"), "--out-dir", str(out), "--n-boot", "100"]
    res = V1.main(base)
    v = res["sets"]["error"]["verdict"]["jlens"]
    assert v["layers_scored"] == [42, 48] and v["layers_pending"] == [44, 46, 50, 52, 54, 56, 58, 60, 62] and not v["complete"]
    assert v["status"].startswith("not crossed") and v["first_layer_ge_thresh"] is None
    assert res["sets"]["error"]["probe_first_layer_ge_thresh"] == 50
    assert (out / "v1.md").exists() and (out / "v1.csv").exists() and (out / "fig_v1.png").exists()
    # the candA rows never leak into the last-token sweep (they would give 100%)
    assert all(d["p"] < 0.9 for d in res["sets"]["error"]["readers"]["jlens"].values())
    # jlens unscorable rows on choice items are excluded, not counted as misses
    d48 = res["sets"]["disagree"]["readers"]["jlens"][48]
    assert d48["n_unscorable"] > 0 and d48["n"] + d48["n_unscorable"] == 20
    # with the pod rows the sweep is complete and the planted crossing is found with its lag behind the probe
    res2 = V1.main(base + ["--extra-lo", str(pod)])
    v2 = res2["sets"]["error"]["verdict"]["jlens"]
    assert v2["complete"] and v2["first_layer_ge_thresh"] == 54 and v2["lag_layers"] == 4 and v2["status"] == "crossed"
    vo = res2["sets"]["error"]["verdict"]["olens"]
    assert vo["complete"] and vo["first_layer_ge_thresh"] is None and vo["status"] == "no crossing through 62"
    with open(out / "v1.csv") as fh:
        rows = list(csv.DictReader(fh))
    assert {r["reader"] for r in rows} >= {"jlens", "olens", "nla", "probe_E10", "logit_lens", "logit_lens_final"}
    assert sorted({int(r["layer"]) for r in rows if r["reader"] == "jlens" and r["set"] == "error"}) == list(K.LAYERS)
    md = (out / "v1.md").read_text()
    assert "outcome (a)" in md and "lag 4 layers" in md


# ------------------------------------------------------------------ V2
def test_v2_rule_identity_subsets_and_three_way(tmp_path):
    obj = make_items(n_err=60)
    its = obj["items"]
    items_p = tmp_path / "items.json"
    items_p.write_text(json.dumps(obj))
    _, items = K.load_items(items_p)
    rng = np.random.default_rng(2)
    x3_rows, y1_rows, tw_rows = [], [], []
    for it in its:
        if it["family"] != "puzzle":
            continue
        for rd in ("jlens", "olens", "nla"):
            # at 42: jlens strongly favours the CORRECT answer on errors (lo_actual < 0), nla favours the actual, olens 50/50 with ties
            if rd == "jlens":
                lo42 = -abs(rng.normal()) - 0.1 if rng.random() < 0.9 else abs(rng.normal())
            elif rd == "nla":
                lo42 = abs(rng.normal()) + 0.1
            else:
                lo42 = 0.0 if rng.random() < 0.1 else float(rng.normal())
            x3_rows.append(lo_row(rd, "", it, lo42, x3=True))
            y1_rows.append(lo_row(rd, "48:0", it, float(rng.normal())))
            if it["set"] == "error" and items[it["item_id"]]["roles"]["km1"] != it["primary"]["answer"]:
                ro = items[it["item_id"]]["roles"]
                tw_rows.append({"reader": rd, "site": "42:0", "layer": 42, "item_id": it["item_id"], "set": "error",
                                "candidates": {"correct": ro["correct"], "actual": ro["actual"], "km1": ro["km1"]},
                                "lp": {"correct": 0.0, "actual": -1.0, "km1": 1.0}, "unscorable": False})
    x3 = write_jsonl(tmp_path / "x3_lo.jsonl", x3_rows)
    y1 = write_jsonl(tmp_path / "y1_lo.jsonl", y1_rows)
    tw = write_jsonl(tmp_path / "tw.jsonl", tw_rows)
    out = tmp_path / "v"
    args = ["--items", str(items_p), "--x3-lo", str(x3), "--y1-lo", str(y1), "--out-dir", str(out), "--n-boot", "200", "--n-perm", "100"]
    res = V2.main(args)
    j = res["cells"]["jlens@42"]["subsets"]["all"]
    assert j["resolves"] and j["diff"] >= 0.15 and j["diff_lo"] > 0 and j["perm"]["p_value"] < 0.05
    # identity P(correct) = 1 - P(actual) - P(tie)
    for key, c in res["cells"].items():
        d = c["subsets"]["all"]
        assert abs(d["correct"]["p"] + d["actual"]["p"] + d["n_ties"] / d["n"] - 1) < 1e-12
        assert c["subsets"]["km1_eq_actual"]["n"] + c["subsets"]["km1_ne_actual"]["n"] == d["n"]
    o = res["cells"]["olens@42"]
    assert o["subsets"]["all"]["n_ties"] > 0 and not o["subsets"]["all"]["resolves"]
    n = res["cells"]["nla@42"]["subsets"]["all"]
    assert n["diff"] < 0 and not n["resolves"]
    # control: cand_actual == correct, so P(correct) = P(lo > 0)
    k = res["cells"]["nla@42"]["control"]
    assert k["n"] == 12 and abs(k["correct"]["p"] - 1.0) < 1e-12
    # three-way: without the pod file the 30 km1 != actual items are pending; with it they resolve to the k-1 symbol
    t = res["cells"]["jlens@42"]["three_way"]
    assert t["n"] == 60 and t["n_pending"] == 30 and t["counts"]["correct"] + t["counts"]["actual_is_km1"] + t["counts"]["tie"] == 30
    res2 = V2.main(args + ["--three-way", str(tw)])
    t2 = res2["cells"]["jlens@42"]["three_way"]
    assert t2["complete"] and t2["counts"]["km1"] == 30 and t2["counts"]["pending"] == 0
    assert res2["cells"]["jlens@48"]["three_way"]["n_pending"] == 30  # the file only covered 42:0
    assert (out / "v2.md").exists() and (out / "v2.csv").exists() and (out / "fig_v2.png").exists()
    with open(out / "v2.csv") as fh:
        rows = list(csv.DictReader(fh))
    assert {r["subset"] for r in rows} == {"all", "km1_eq_actual", "km1_ne_actual", "error_control", "three_way_counts"}
    assert V2.three_way_pref({"correct": 1.0, "actual": 1.0, "km1": 0.0}) == "tie" and V2.three_way_pref({"correct": 0.0, "actual": 2.0, "km1": 1.0}) == "actual"


def test_v2_missing_layer_is_reported_not_fabricated(tmp_path):
    obj = make_items(n_err=10, n_ctl=4)
    items_p = tmp_path / "items.json"
    items_p.write_text(json.dumps(obj))
    y1 = write_jsonl(tmp_path / "y1_lo.jsonl", [lo_row("jlens", "48:0", it, 0.5) for it in obj["items"] if it["family"] == "puzzle"])
    res = V2.main(["--items", str(items_p), "--x3-lo", str(tmp_path / "absent.jsonl"), "--y1-lo", str(y1), "--out-dir", str(tmp_path / "v"),
                   "--readers", "jlens", "--n-boot", "50", "--n-perm", "20"])
    assert res["cells"]["jlens@42"]["available"] is False and res["cells"]["jlens@48"]["available"] is True
    assert "no rows" in (tmp_path / "v" / "v2.md").read_text()


# ------------------------------------------------------------------ pod request
def test_pod_request_contents(tmp_path):
    obj = make_items(n_err=20, n_ctl=5, n_dis=8, n_agr=4)
    items_p = tmp_path / "items.json"
    items_p.write_text(json.dumps(obj))
    _, items = K.load_items(items_p)
    its = obj["items"]
    x3 = write_jsonl(tmp_path / "x3_lo.jsonl", [lo_row(rd, "", it, 0.1, x3=True) for it in its for rd in ("jlens", "olens", "nla")])
    y1 = write_jsonl(tmp_path / "y1_lo.jsonl", [lo_row(rd, "48:0", it, 0.1) for it in its for rd in ("jlens", "olens", "olens_trueL", "nla")])
    rows, _ = K.load_lo_rows(x3, y1, [], items=items)
    req = PR.build(items, rows)
    v1, tw = req["requests"]
    assert v1["name"] == "v1_layer_sweep" and tw["name"] == "three_way"
    assert v1["sets"]["error"]["n"] == 20 and v1["sets"]["disagree"]["n"] == 8 and v1["layers"] == list(K.LAYERS)
    assert v1["pending_sites"] == [f"{L}:0" for L in K.LAYERS if L not in (42, 48)]
    assert v1["already_scored_on_mac"]["sites"]["48:0"] == ["jlens", "nla", "olens", "olens_trueL"]
    assert v1["readers"]["olens"]["map"]["46"] == 44 and v1["readers"]["nla"]["layer_arg"] is None
    assert any("--site 44:0" in c and "--phase A" in c for c in v1["commands"]) and any("--phase B" in c and "nla" in c for c in v1["commands"])
    assert not any("--site 48:0 " in c and not c.startswith("#") for c in v1["commands"])
    assert "acts[cap['layers'].index(L), cap['labels'].index('0'), :]" in req["inputs"]["captures"]["last_token_index"]
    assert tw["n_items"] == 10 and all(i["candidates"]["km1"] != i["candidates"]["actual"] for i in tw["items"])
    assert all(i["candidates"]["correct"] not in (i["candidates"]["actual"], i["candidates"]["km1"]) for i in tw["items"])
    assert tw["sites"] == ["42:0", "48:0"] and set(tw["output"]["row"]["lp"]) == {"correct", "actual", "km1"}
    assert v1["estimated_gpu_minutes"] > 0
    PR.main(["--items", str(items_p), "--x3-lo", str(x3), "--y1-lo", str(y1), "--out", str(tmp_path / "req.json")])
    assert json.loads((tmp_path / "req.json").read_text())["requests"][1]["n_items"] == 10


def test_zz_results_cache_untouched():
    now_r = sorted(str(p) for p in (REPO / "results" / "g_agreement" / "v").rglob("*")) if (REPO / "results" / "g_agreement" / "v").exists() else []
    now_c = sorted(str(p) for p in (REPO / "cache" / "g_agreement" / "y").glob("*.jsonl")) if (REPO / "cache" / "g_agreement" / "y").exists() else []
    assert now_r == RESULTS_SNAPSHOT and now_c == CACHE_SNAPSHOT
