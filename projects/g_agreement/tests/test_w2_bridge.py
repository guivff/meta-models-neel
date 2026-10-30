"""CPU tests for the Phase W post-pod analyses W2 (w_analysis/w2_precision.py) and Bridge (w_analysis/bridge.py) on synthetic
fixtures that follow the pod schemas (w_pod/s1_capture.py S1 rows, w_pod/s3_score.py S1-unit rows incl. the probe's reordered
candidates, w_pod/s4_consistency.py sample rows) and planted layer-42-style states. Nothing is written under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_w2_bridge.py -q``
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")

from projects.g_agreement.w_analysis import bridge as B  # noqa: E402
from projects.g_agreement.w_analysis import w2_precision as W2  # noqa: E402

SYM = list("ABCDEFGH")


# ------------------------------------------------------------------ fixtures
def _lp(cands, peak, spread=0.3, rng=None):
    rng = rng or random.Random(0)
    return [(-0.1 if c == peak else -5.0 - rng.random() * spread) for c in cands]


def _mag_reader(v: int) -> int:
    """Keeps the tens digit, scrambles the units digit (never equal to v)."""
    return (v // 10) * 10 + (v % 10 + 3) % 10 if v >= 10 else (v + 3) % 10 if (v + 3) % 10 != v else (v + 4) % 10


def make_fixture(tmp: Path, *, n_counts=40, n_arith=20, n_map=16, with_s4=True):
    rng = random.Random(20261011)
    cnt_all = [str(i) for i in range(1, 100)]
    ar_all = [str(i) for i in range(0, 199)]
    s1, s3, s4 = [], [], []
    items = []
    for i in range(n_counts):
        v = rng.randint(1, 99)
        items.append(("counts", f"wcnt-{i:04d}", str(v), cnt_all))
    for i in range(n_arith):
        a, b = rng.randint(2, 99), rng.randint(1, 99)
        items.append(("arith", f"warith-{i:03d}", str(a + b), ar_all))
    for i in range(n_map):
        items.append(("mapping8", f"xmap-{i:02d}A", SYM[rng.randrange(8)], list(SYM)))
    k1 = {}
    for fam, iid, true, cands in items:
        s1.append({"key": iid, "item_id": iid, "family": fam, "pair_id": iid, "version": "A", "true_answer": true, "parsed": true, "correct": True,
                   "cand_A": true, "cand_B": cands[(cands.index(true) + 1) % len(cands)], "candidates_all": cands, "lp_candidates_all": _lp(cands, true, rng=rng)})
        other = cands[(cands.index(true) + 1) % len(cands)]
        rest = [c for c in cands if c not in (true, other)]
        base = {"unit": "S1", "layer": 42, "family": fam, "item_id": iid, "true_answer": true, "actual_answer": true, "correct": True, "cand_A": true, "cand_B": other}
        # probe: reordered candidates [cand_A, cand_B] + rest, perfect
        pc = [true, other] + rest
        s3.append({**base, "key": f"probe|S1|{iid}", "reader": "probe", "candidates": pc, "scores": _lp(pc, true, rng=rng)})
        # olens: keeps magnitude, drops digits (numeric); mapping: names the "k−1" symbol = previous index
        if fam == "mapping8":
            rep = SYM[(SYM.index(true) - 1) % 8]
            k1[iid] = rep
        else:
            rep = str(_mag_reader(int(true)))
        s3.append({**base, "key": f"olens|S1|{iid}", "reader": "olens", "candidates": cands, "scores": _lp(cands, rep, rng=rng)})
        # jlens: anti-reader (reported = mirror) → Spearman −1
        if fam == "counts":
            rep = str(100 - int(true))
        elif fam == "arith":
            rep = str(198 - int(true))
        else:
            rep = SYM[7 - SYM.index(true)]
        s3.append({**base, "key": f"jlens|S1|{iid}", "reader": "jlens", "candidates": cands, "scores": _lp(cands, rep, rng=rng)})
        # nla: perfect but with unscorable (None) entries; skip_a: all None (unscorable)
        sc = _lp(cands, true, rng=rng)
        sc = [None if (j % 7 == 3 and c != true) else s for j, (c, s) in enumerate(zip(cands, sc))]
        s3.append({**base, "key": f"nla|S1|{iid}", "reader": "nla", "candidates": cands, "scores": sc, "n_unscorable": sum(s is None for s in sc)})
        s3.append({**base, "key": f"skip_a|S1|{iid}", "reader": "skip_a", "candidates": cands, "scores": [None] * len(cands)})
        # an S2 row and a V7 row that must be ignored
        s3.append({**base, "key": f"probe|S2|{iid}", "reader": "probe", "unit": "S2", "candidates": pc, "scores": _lp(pc, other, rng=rng)})
    if with_s4:
        for fam, iid, true, cands in items[:10]:
            for k in range(8):
                s4.append({"key": f"olens|{iid}|s{k}", "state_item_id": iid, "reader": "olens", "sample_idx": k, "text": f"- The jar holds {true} marbles.\n- A count.",
                           "candidates": cands, "answer": true, "actual_answer": true, "condition": "natural", "family": fam, "layer": 42})
                txt = "No number here." if k == 7 else f"The user asks about {int(true) + 1} items."
                s4.append({"key": f"nla|{iid}|s{k}", "state_item_id": iid, "reader": "nla", "sample_idx": k, "text": txt,
                           "candidates": cands, "answer": true, "actual_answer": true, "condition": "natural", "family": fam, "layer": 42})
        s4.append({"key": "nla|random-00|s0", "state_item_id": "random-00", "reader": "nla", "sample_idx": 0, "text": "7 things", "candidates": None, "answer": None,
                   "actual_answer": None, "condition": "random", "family": "random", "layer": 42})
    for name, rows in (("s1_target.jsonl", s1), ("s3_lo.jsonl", s3), ("s4_samples.jsonl", s4)):
        (tmp / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp / "mapping8_index.json").write_text(json.dumps({"meta": {}, "pairs": [], "items": [{"item_id": i, "k_minus_1_symbol": s} for i, s in k1.items()]}))
    kept = [iid for fam, iid, _, _ in items if fam == "counts"][: n_counts - 5]
    (tmp / "counts_kept.json").write_text(json.dumps({"kept": kept}))
    return {"items": items, "kept": kept, "k1": k1}


# ------------------------------------------------------------------ helpers
def test_first_integer_and_value_of():
    assert W2.first_integer("- The jar holds 27 marbles.") == 27
    assert W2.first_integer("roughly -3 then 9") == -3
    assert W2.first_integer("no digits") is None and W2.first_integer(None) is None
    assert W2.value_of("27", "counts") == 27 and W2.value_of(" 198 ", "arith") == 198
    assert W2.value_of("D", "mapping8") == 3 and W2.value_of("Z", "mapping8") is None and W2.value_of("x", "counts") is None


def test_argmax_candidate_handles_none_and_ties():
    assert W2.argmax_candidate(["1", "2", "3"], [None, -1.0, -2.0]) == "2"
    assert W2.argmax_candidate(["1", "2"], [None, None]) is None
    assert W2.argmax_candidate(["1", "2"], [-1.0, -1.0]) == "1"
    assert W2.argmax_candidate([], []) is None


def test_item_bootstrap_perfect_magnitude_and_pooling():
    recs = [{"item_id": f"i{v}", "true": v, "reported": v} for v in range(1, 60)]
    st = W2.item_bootstrap(recs, 200, 0)
    assert st["exact"] == 1.0 and st["exact_lo"] == 1.0 and st["exact_hi"] == 1.0 and st["spearman"] == pytest.approx(1.0)
    mag = [{"item_id": f"i{v}", "true": v, "reported": _mag_reader(v)} for v in range(10, 99)]
    st = W2.item_bootstrap(mag, 300, 0)
    assert st["exact"] == 0.0 and st["spearman"] > 0.9 and st["spearman_lo"] > 0.8
    # pooled readouts: 2 per item, one exact → exact 0.5; one unparsed
    pooled = [{"item_id": "a", "true": 5, "reported": 5}, {"item_id": "a", "true": 5, "reported": 6}, {"item_id": "b", "true": 9, "reported": 9},
              {"item_id": "b", "true": 9, "reported": None}]
    st = W2.item_bootstrap(pooled, 50, 0)
    assert st["exact"] == 0.5 and st["n_items"] == 2 and st["n_readouts"] == 4 and st["unparsed_rate"] == 0.25
    assert W2.item_bootstrap([], 10, 0)["exact"] is None


def test_error_structure_digits_and_k_minus_1():
    recs = [{"item_id": str(v), "true": v, "reported": _mag_reader(v)} for v in range(10, 99)]
    es = W2.error_structure(recs, "counts")
    assert es["wrong_same_tens"] == 1.0 and es["wrong_same_units"] == 0.0 and sum(es["hist_counts"]) == len(recs)
    assert es["hist_labels"] == list(W2.ERR_LABELS) and es["hist_counts"][0] == 0
    m = [{"item_id": f"m{i}", "true": i, "reported": (i - 1) % 8} for i in range(8)]
    es = W2.error_structure(m, "mapping8", {f"m{i}": (i - 1) % 8 for i in range(8)})
    assert es["wrong_is_k_minus_1"] == 1.0 and len(es["hist_counts"]) == 8
    assert W2.magnitude_tag(0.9, 0.9) == "reads digits" and W2.magnitude_tag(0.1, 0.8) == "keeps magnitude, drops digits"
    assert W2.magnitude_tag(0.1, -1.0) == "neither" and W2.magnitude_tag(None, 0.5) == "n/a"


def test_records_use_row_candidate_order(tmp_path):
    make_fixture(tmp_path, n_counts=6, n_arith=3, n_map=3, with_s4=False)
    rows = [json.loads(l) for l in (tmp_path / "s3_lo.jsonl").read_text().splitlines()]
    recs = W2.records_from_s3(rows)
    probe = recs[("counts", "probe")]
    assert len(probe) == 6 and all(r["reported"] == r["true"] for r in probe)  # reordered candidates handled
    assert all(r["reported"] is None for r in recs[("counts", "skip_a")])  # all-None score vector → unparsed
    assert ("counts", "probe") in recs and not any(r.get("unit") == "S2" for r in rows if False)
    s1 = [json.loads(l) for l in (tmp_path / "s1_target.jsonl").read_text().splitlines()]
    m = W2.records_from_s1(s1)
    assert all(r["reported"] == r["true"] for r in m[("counts", "model_ft")]) and len(m[("mapping8", "model_ft")]) == 3


def test_w2_run_end_to_end(tmp_path):
    fx = make_fixture(tmp_path)
    out = tmp_path / "w2"
    s = W2.run(s1=tmp_path / "s1_target.jsonl", s3=tmp_path / "s3_lo.jsonl", s4=tmp_path / "s4_samples.jsonl", out_dir=out, n_boot=100, seed=0,
               counts_kept=tmp_path / "counts_kept.json", mapping8_index=tmp_path / "mapping8_index.json")
    for f in ("w2.md", "w2.csv", "w2_summary.json", "fig_precision.png"):
        assert (out / f).exists(), f
    assert len((out / "w2.md").read_text().splitlines()) <= 40
    by = {(r["family"], r["reader"]): r for r in s["rows"]}
    # counts restricted to the kept list
    assert by[("counts", "probe")]["n_items"] == len(fx["kept"])
    assert by[("counts", "probe")]["tag"] == "reads digits" and by[("counts", "probe")]["exact"] == 1.0
    o = by[("counts", "olens")]
    assert o["tag"] == "keeps magnitude, drops digits" and o["exact"] == 0.0 and o["spearman"] > 0.9 and o["wrong_same_tens"] == 1.0
    j = by[("counts", "jlens")]
    assert j["tag"] == "neither" and j["spearman"] == pytest.approx(-1.0) and j["spearman_hi"] <= -0.99
    assert by[("counts", "nla")]["exact"] == 1.0  # None entries skipped
    assert by[("counts", "skip_a")]["exact"] == 0.0 and by[("counts", "skip_a")]["unparsed_rate"] == 1.0
    assert by[("counts", "model_ft")]["exact"] == 1.0
    # free text: Oracle states the number (8 samples × 10 states, counts only, natural only); NLA states true+1 with one unparsed per state
    ot = by[("counts", "olens_text")]
    assert ot["n_items"] == 10 and ot["n_readouts"] == 80 and ot["exact"] == 1.0
    nt = by[("counts", "nla_text")]
    assert nt["exact"] == 0.0 and nt["unparsed_rate"] == pytest.approx(1 / 8) and nt["spearman"] == pytest.approx(1.0) and nt["mae"] == 1.0
    assert ("counts", "random") not in by and ("arith", "olens_text") not in by
    # mapping-8: olens names the k−1 symbol every time; arith rows exist for the vector readers
    assert by[("mapping8", "olens")]["wrong_is_k_minus_1"] == 1.0 and by[("mapping8", "olens")]["exact"] == 0.0
    assert by[("arith", "probe")]["exact"] == 1.0 and by[("arith", "probe")]["n_items"] == 20
    # csv has one row per (family, reader) with the bootstrap columns
    import csv

    with (out / "w2.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(s["rows"]) and {"exact_lo", "spearman_hi", "hist_counts", "tag"} <= set(rows[0])
    assert all(float(r["exact_lo"]) <= float(r["exact"]) <= float(r["exact_hi"]) for r in rows if r["exact"])


def test_w2_without_s3_and_s4(tmp_path):
    make_fixture(tmp_path, n_counts=8, n_arith=4, n_map=4, with_s4=False)
    out = tmp_path / "w2b"
    s = W2.run(s1=tmp_path / "s1_target.jsonl", s3=tmp_path / "missing_s3.jsonl", s4=tmp_path / "missing_s4.jsonl", out_dir=out, n_boot=20, seed=0,
               counts_kept=None, mapping8_index=None, make_figure=False)
    assert {r["reader"] for r in s["rows"]} == {"model_ft"}
    assert any("S3 reader rows absent" in n for n in s["notes"]) and any("S4 samples absent" in n for n in s["notes"])
    assert not (out / "fig_precision.png").exists() and (out / "w2.md").exists()
    with pytest.raises(FileNotFoundError):
        W2.run(s1=tmp_path / "nope.jsonl", s3=tmp_path / "x", s4=tmp_path / "y", out_dir=out, n_boot=5)


# ------------------------------------------------------------------ bridge
def test_parse_expr_matches_michael():
    assert B.parse_expr('The equation "58 - 46 =" is …') == (58, "-", 46)
    assert B.parse_expr("64 − 49 = ?") == (64, "-", 49)
    assert B.parse_expr("sum 12+7 then 3 - 1") == (12, "+", 7)
    assert B.parse_expr("no expression 42") is None and B.parse_expr(None) is None


def _michael_like(n=60, seed=3):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        a, b = rng.randint(10, 99), rng.randint(10, 99)
        pa = a if i % 10 else a + 11  # probe a right 90 %
        pb = b  # probe b right 100 %
        r1 = f'The equation "{a} + {b + 1} =" needs a result.'  # a right, b off by one
        r2 = "A simple arithmetic prompt." if i % 2 else f"{a + 10} - {b} ="  # half unparsed; a off by 10, b right
        rows.append({"id": f"ar{i:03d}", "a": a, "b": b, "op": "+", "answer": a + b, "text": f"{a} + {b} =", "model_next": " ?",
                     "probe_a_tens": pa // 10, "probe_a_units": pa % 10, "probe_b_tens": pb // 10, "probe_b_units": pb % 10, "nla_readouts": [r1, r2]})
    return rows


def test_michael_stats_synthetic():
    m = B.michael_stats(_michael_like(), n_boot=100, seed=0)
    assert m["probe_exact_a"]["exact"] == pytest.approx(0.9) and m["probe_exact_b"]["exact"] == 1.0
    assert m["probe_exact_a"]["exact_lo"] <= 0.9 <= m["probe_exact_a"]["exact_hi"]
    assert m["nla_quote_rate"] == pytest.approx(0.75)
    # quoting readouts: r1 (a right, b wrong) every item, r2 (a wrong, b right) every other item → a exact 60/90, b exact 30/90
    assert m["nla_exact_a"]["exact"] == pytest.approx(60 / 90) and m["nla_exact_b"]["exact"] == pytest.approx(30 / 90)
    assert m["nla_exact_a"]["n_quoting"] == 90 and m["nla_pearson_a"]["r"] > 0.95 and m["nla_spearman_b"]["rho"] > 0.95
    assert m["model_next_starts_answer"] == 0.0
    assert m["probe_digit_b_units"]["acc"] == 1.0 and 0 < m["probe_digit_a_tens"]["majority"] < 1


@pytest.mark.skipif(not B.MICHAEL.exists(), reason="nla-consistency release not unpacked")
def test_michael_stats_reproduce_readme():
    m = B.michael_stats(B.read_jsonl(B.MICHAEL), n_boot=50, seed=0)
    assert m["n_prompts"] == 600 and m["n_readouts"] == 1200
    assert 0.83 <= round(m["probe_exact_a"]["exact"], 2) <= 0.93 and 0.83 <= round(m["probe_exact_b"]["exact"], 2) <= 0.93
    assert round(m["nla_exact_a"]["exact"], 2) == pytest.approx(0.05, abs=0.01) and round(m["nla_exact_b"]["exact"], 2) == pytest.approx(0.38, abs=0.01)
    assert m["nla_pearson_a"]["r"] == pytest.approx(0.57, abs=0.01) and m["nla_pearson_b"]["r"] == pytest.approx(0.88, abs=0.01)


def _planted(items, d=64, seed=0, noise=0.15):
    g = torch.Generator().manual_seed(seed)
    E = {k: torch.randn(10, d, generator=g) for k in B.TARGETS}
    tg = B.digit_targets(items)
    X = torch.stack([sum(E[k][tg[k][i]] for k in B.TARGETS) for i in range(len(items))]) + noise * torch.randn(len(items), d, generator=g)
    return X


def _items(n=100, seed=5):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        op = "-" if i % 2 == 0 else "+"
        a = rng.randint(2, 99)
        b = rng.randint(1, a - 1) if op == "-" else rng.randint(1, 99)
        out.append({"item_id": f"warith-{i + 1:03d}", "a": a, "b": b, "op": op, "answer": a - b if op == "-" else a + b, "text": f"{a} {op} {b} ="})
    return out


def test_probe_cv_recovers_planted_digits():
    items = _items()
    X = _planted(items)
    preds = B.probe_cv(X, B.digit_targets(items))
    assert set(preds) == set(B.TARGETS) and all(len(v) == 100 and all(0 <= p <= 9 for p in v) for v in preds.values())
    rep = B.probe_report(items, preds, n_boot=100, seed=0)
    assert rep["probe_exact_a"]["exact"] >= 0.8 and rep["probe_exact_b"]["exact"] >= 0.8
    assert rep["probe_exact_a"]["exact_lo"] <= rep["probe_exact_a"]["exact"] <= rep["probe_exact_a"]["exact_hi"]
    assert rep["probe_spearman_a"]["rho"] > 0.8 and rep["probe_digit_a_tens"]["acc"] >= 0.85
    # folds are Michael's: interleaved after a Random(1) shuffle, disjoint and covering
    idx = list(range(100))
    random.Random(1).shuffle(idx)
    folds = [idx[i::5] for i in range(5)]
    assert sorted(sum(folds, [])) == list(range(100)) and all(len(f) == 20 for f in folds)
    small = B.probe_cv(X, B.digit_targets(items), n_train=20)
    assert all(len(v) == 100 for v in small.values())
    curve = B.learning_curve(X, items, sizes=(20, 50), full_preds=preds)
    assert [r["n_train_per_fold"] for r in curve] == [20, 50, 80] and curve[-1]["exact_a"] == rep["probe_exact_a"]["exact"]
    assert all(r["exact_a_lo"] <= r["exact_a"] <= r["exact_a_hi"] for r in curve)
    ranks = B.recipe_ranks(X, items)
    assert set(ranks["ranks"]) == {f"{s}|{k}" for s in ("a", "b") for k in ("mean", "lr", "rand")}
    assert all(1 <= ranks["ranks"][f"{s}|mean"] <= 18 for s in ("a", "b"))


def test_native_arith_and_compare():
    items = _items(10)
    cands = [str(i) for i in range(199)]
    rows = []
    for it in items:
        rows.append({"unit": "S1", "family": "arith", "reader": "nla", "item_id": it["item_id"], "candidates": cands, "scores": _lp(cands, str(it["answer"]))})
        rows.append({"unit": "S1", "family": "arith", "reader": "olens", "item_id": it["item_id"], "candidates": cands, "scores": _lp(cands, str(it["a"]))})
        rows.append({"unit": "S2", "family": "arith", "reader": "nla", "item_id": it["item_id"], "candidates": cands, "scores": _lp(cands, "0")})
    nn = B.native_arith(rows, items, n_boot=50)
    assert nn["nla"]["result_exact"] == 1.0 and nn["nla"]["n_items"] == 10
    assert nn["olens"]["argmax_equals_a"] == 1.0 and nn["olens"]["result_exact"] == 0.0
    assert B.within(0.85, 0.80, 0.86) is True and B.within(0.9, 0.80, 0.86) is False and B.within(None, 0, 1) is None
    assert B.overlap(0.1, 0.5, 0.4, 0.9) is True and B.overlap(0.1, 0.3, 0.4, 0.9) is False and B.overlap(0.1, None, 0.4, 0.9) is None
    m = B.michael_stats(_michael_like(), n_boot=20)
    ours = {"probe_exact_a": {"exact": 0.9, "exact_lo": 0.8, "exact_hi": 0.97}, "probe_exact_b": {"exact": 0.5, "exact_lo": 0.4, "exact_hi": 0.6}}
    cmp = {r["metric"]: r for r in B.compare(ours, m, nn)}
    assert cmp["probe exact-match a"]["ours_within_michael_ci"] is True and cmp["probe exact-match b"]["ours_within_michael_ci"] is False
    assert cmp["NLA exact-match a (free text)"]["ours"] is None and "no counterpart" in cmp["NLA exact-match a (free text)"]["note"]
    assert cmp["NLA native argmax exact-match (result)"]["ours"] == 1.0


def _write_items(tmp: Path, items):
    doc = {"meta": {}, "items": [{"item_id": it["item_id"], "family": "arith", "prompt_text": it["text"], "primary": {"answer": str(it["answer"]), "candidates": [str(it["answer"])]},
                                  "construction": {"a": it["a"], "b": it["b"], "op": it["op"], "answer": it["answer"]}, "operands": {"a": it["a"], "b": it["b"], "op": it["op"]}}
                                 for it in items] + [{"item_id": "wcnt-0001", "family": "counts", "prompt_text": "x", "primary": {"answer": "3", "candidates": ["3"]}, "construction": {}}]}
    p = tmp / "items_w.json"
    p.write_text(json.dumps(doc))
    return p


def test_bridge_run_without_states_then_with(tmp_path):
    items = _items(40)
    ip = _write_items(tmp_path, items)
    mp = tmp_path / "arithmetic.jsonl"
    mp.write_text("".join(json.dumps(r) + "\n" for r in _michael_like()))
    out = tmp_path / "bridge"
    s = B.run(states_dir=tmp_path / "no_states", items_path=ip, s1=tmp_path / "none.jsonl", s3=tmp_path / "none.jsonl", michael_path=mp, out_dir=out, n_boot=20)
    assert s["ours_probe"] is None and any("NOT run" in n for n in s["notes"]) and any("not sampled in S4" in n for n in s["notes"])
    for f in ("bridge.md", "bridge.csv", "bridge_summary.json"):
        assert (out / f).exists(), f
    assert all(r["ours"] is None for r in s["comparison"])
    # now with planted states and an S3 NLA vector + S1 rows
    sd = tmp_path / "states_L42"
    sd.mkdir()
    X = _planted(items, seed=1)
    for i, it in enumerate(items):
        torch.save(X[i].clone(), sd / f"{it['item_id']}.pt")
    cands = [str(i) for i in range(199)]
    (tmp_path / "s3.jsonl").write_text("".join(json.dumps({"unit": "S1", "family": "arith", "reader": "nla", "item_id": it["item_id"], "candidates": cands,
                                                            "scores": _lp(cands, str(it["answer"]))}) + "\n" for it in items))
    (tmp_path / "s1.jsonl").write_text("".join(json.dumps({"item_id": it["item_id"], "family": "arith", "correct": i < 7}) + "\n" for i, it in enumerate(items)))
    s = B.run(states_dir=sd, items_path=ip, s1=tmp_path / "s1.jsonl", s3=tmp_path / "s3.jsonl", michael_path=mp, out_dir=out, n_boot=20, do_ranks=False, do_curve=False)
    assert s["ours_probe"]["n_prompts"] == 40 and s["ours_probe"]["probe_exact_a"]["exact"] >= 0.5 and "learning_curve" not in s["ours_probe"]
    assert s["ours_native_arith"]["nla"]["result_exact"] == 1.0
    cmp = {r["metric"]: r for r in s["comparison"]}
    assert isinstance(cmp["probe exact-match a"]["ours_within_michael_ci"], bool) and cmp["probe exact-match a"]["ours"] is not None
    assert any("7/40" in n for n in s["notes"])
    md = (out / "bridge.md").read_text()
    assert "probe exact-match a" in md and "Native vector on arith, reader nla" in md
    with pytest.raises(FileNotFoundError):
        B.run(states_dir=sd, items_path=ip, michael_path=tmp_path / "missing.jsonl", out_dir=out, n_boot=5)
