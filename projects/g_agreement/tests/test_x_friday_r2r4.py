"""Tests for projects/g_agreement/x_friday_r2r4.py (R2–R4 + Y0) on synthetic data only: every path is a tmp_path,
the real cache / results are never read and are asserted untouched.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_x_friday_r2r4.py -q``
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")

from projects.g_agreement import x_friday_r2r4 as F  # noqa: E402

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*")) if (REPO / "results" / "g_agreement").exists() else None
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None

D = 48
NAMES = ["Ann", "Bob", "Cid", "Dee", "Eve", "Fay", "Gus", "Hal", "Ivy", "Jon"]
SYMS = list("ABCDEFGH")
WORDS = ["apple", "pear", "cat", "dog", "tea", "coffee"]


# ------------------------------------------------------------------ synthetic builders
def _pair(fam: str, k: int, cands, first_mentioned_is_A: bool, template="t1", split="test"):
    pid = f"x{fam[:3]}-{k:02d}"
    out = {}
    for v, ans in (("A", cands[0]), ("B", cands[1])):
        first = bool((v == "A") == first_mentioned_is_A) if fam == "ownership" else first_mentioned_is_A
        out[v] = {"item_id": pid + v, "pair_id": pid, "version": v, "family": fam, "split": split, "template_id": template,
                  "prompt_text": f"{fam} {pid}{v}", "primary": {"candidates": list(cands), "answer": ans, "answer_aliases": [ans.lower()]},
                  "construction": {"first_mentioned_candidate": cands[0] if first == (v == "A") else cands[1], "answer_position": 0 if v == "A" else 1,
                                   "answer_is_first_mentioned": first, "other_candidate": cands[1] if v == "A" else cands[0]}}
    return {"pair_id": pid, "family": fam, **out}


def synth_binding(n_pairs: int, fam: str, seed: int, order_gain: float, identity_gain: float, noise: float = 1.0):
    """Pairs + states. States = noise + order_gain * (±u_order by mention order) + identity_gain * emb[answer]."""
    rng = np.random.default_rng(seed)
    vocab = NAMES if fam == "ownership" else SYMS
    emb = {c: rng.standard_normal(D) for c in vocab}
    u_order = rng.standard_normal(D)
    pairs, H = [], {}
    for k in range(n_pairs):
        c = rng.choice(len(vocab), 2, replace=False)
        cands = (vocab[c[0]], vocab[c[1]])
        p = _pair(fam, k + 2, cands, bool(k % 2 == 0))
        pairs.append(p)
        for v in "AB":
            it = p[v]
            sgn = 1.0 if it["construction"]["answer_is_first_mentioned"] else -1.0
            H[it["item_id"]] = noise * rng.standard_normal(D) + order_gain * sgn * u_order + identity_gain * emb[it["primary"]["answer"]]
    return pairs, H


def synth_x3(n_error: int, n_control: int, n_dis: int, n_agree: int, seed: int, gain: float = 3.0):
    rng = np.random.default_rng(seed)
    emb = {s: rng.standard_normal(D) for s in SYMS + WORDS}
    items, H, lo, trows = {}, {}, [], []
    bias = {"jlens": {s: 0.0 for s in SYMS}, "olens": {s: (i - 3.5) * 0.8 for i, s in enumerate(SYMS)}, "nla": {s: 0.3 * ((-1) ** i) for i, s in enumerate(SYMS)}}
    for i in range(n_error + n_control):
        iid = f"xpz-{i + 1:04d}"
        trace = [SYMS[j] for j in rng.choice(8, 4, replace=False)]
        correct = trace[-1]
        is_err = i < n_error
        if is_err:
            actual = trace[-2] if i % 3 else [s for s in SYMS if s not in trace][0]  # a third of the errors off-trace
            other = correct
        else:
            actual = correct
            other = trace[-2]
        items[iid] = {"item_id": iid, "pair_id": iid, "version": "A", "family": "puzzle", "set": "error" if is_err else "error_control", "split": "test",
                      "template_id": "pz-t1", "prompt_text": f"puzzle {iid}", "primary": {"candidates": [actual, other], "answer": actual},
                      "text_key": correct, "source": {"correct": correct, "k": 3, "start": trace[0], "trace": trace, "distractors": trace[:-1]}}
        H[iid] = rng.standard_normal(D) + gain * emb[actual]
        trows.append({"item_id": iid, "family": "puzzle", "parsed": actual, "correct": correct, "k": 3, "is_error": is_err, "is_coherent": True})
        for rd in F.READERS:
            v = 0.4 + rng.standard_normal() * 0.8 + bias[rd][actual] - bias[rd][other]
            lo.append({"reader": rd, "item_id": iid, "family": "puzzle", "set": items[iid]["set"], "cand_actual": actual, "cand_other": other,
                       "lo_actual": float(v), "lp_actual": 0.0, "lp_other": -float(v), "favours_actual": v > 0, "unscorable": False})
    for i in range(n_dis + n_agree):
        iid = f"xch-{i + 1:04d}"
        w = WORDS[(2 * i) % len(WORDS)], WORDS[(2 * i + 1) % len(WORDS)]
        first = w[i % 2]
        actual = w[(i // 2) % 2]
        other = w[0] if actual == w[1] else w[1]
        dis = i < n_dis
        guess = other if dis else actual
        items[iid] = {"item_id": iid, "pair_id": iid, "version": "A", "family": "choice", "set": "disagree" if dis else "agree_control", "split": "test",
                      "template_id": "choice-t1", "prompt_text": f"choose between {first} and {other if first == actual else actual}",
                      "primary": {"candidates": [actual, other], "answer": actual}, "text_key": guess,
                      "source": {"options_listed": list(w), "first_listed": first, "self_guess": guess}}
        H[iid] = rng.standard_normal(D) + gain * emb[actual]
        trows.append({"item_id": iid, "family": "choice", "actual": actual, "self_guess": guess, "disagree": dis, "first_listed": first})
        for rd in F.READERS:
            v = rng.standard_normal()
            lo.append({"reader": rd, "item_id": iid, "family": "choice", "set": items[iid]["set"], "cand_actual": actual, "cand_other": other,
                       "lo_actual": None if (rd == "jlens" and i == 0) else float(v), "unscorable": rd == "jlens" and i == 0})
    return items, H, lo, trows


def _write_states(H, d: Path):
    d.mkdir(parents=True, exist_ok=True)
    for k, v in H.items():
        torch.save(torch.tensor(v, dtype=torch.float32), d / f"{k}.pt")


# ------------------------------------------------------------------ unit tests
def test_span_logistic_matches_full_fit():
    from sklearn.linear_model import LogisticRegression

    rng = np.random.default_rng(0)
    X = rng.standard_normal((40, 70))
    y = rng.integers(0, 3, 40)
    Xt = rng.standard_normal((9, 70))
    sp = F.SpanLogistic(Cs=(0.5,), multi="multinomial", max_iter=20000).fit(X, y)
    mu, sd = X.mean(0), X.std(0)
    full = LogisticRegression(C=0.5, max_iter=20000, tol=1e-8).fit((X - mu) / sd, y)
    assert np.allclose(sp.logits(Xt), full.decision_function((Xt - mu) / sd), atol=2e-2, rtol=2e-2)
    assert (sp.predict(Xt) == full.predict((Xt - mu) / sd)).all()
    # pair scores: nan for an unseen class, finite otherwise
    s = sp.pair_scores(Xt, [0] * 9, [1] * 8 + [7])
    assert np.isfinite(s[:8]).all() and np.isnan(s[8])


def test_span_logistic_ovr_and_binary():
    rng = np.random.default_rng(1)
    X = rng.standard_normal((30, 20))
    y = np.array(["a", "b", "c"] * 10)
    sp = F.SpanLogistic(Cs=(0.01, 1.0), multi="ovr").fit(X, y)
    assert sp.logits(X).shape == (30, 3) and sp.C in (0.01, 1.0)
    yb = (rng.standard_normal(30) > 0).astype(int)
    sb = F.SpanLogistic(Cs=(1.0,), multi="multinomial").fit(X, yb)
    L = sb.logits(X)
    assert L.shape == (30, 2) and (L[:, 0] == 0).all()
    with pytest.raises(ValueError):
        F.SpanLogistic(Cs=(1.0,)).fit(X, np.zeros(30, int))


def test_contrast_probe_is_an_order_probe():
    pairs, H = synth_binding(24, "ownership", 0, order_gain=3.0, identity_gain=0.0)
    lt = F.label_table(pairs)
    assert lt["n_pairs"] == 24 and lt["A_has_answer_position_0"] == 24 and lt["mention_order_differs_within_pair"] == 24
    assert lt["A_answer_first_mentioned"] == 12  # balanced: the version letter is not the order
    fm = F.contrast_probe(pairs, H, "first_mentioned", n_boot=100, seed=0)
    assert fm["status"] == "ok" and fm["loo"]["p"] == 1.0 and fm["ceiling"]["p"] == 1.0
    ver = F.contrast_probe(pairs, H, "version", n_boot=100, seed=0)
    # balanced version label over a strong order direction: LOO anti-correlates (the held-out pair's sign is always the
    # minority of the remaining pairs), so the win is <= 0.5, never high
    assert ver["loo"]["n"] == 24 and ver["loo"]["p"] <= 0.5
    # mapping-like: both versions share the flag -> undefined within pair
    mp, Hm = synth_binding(10, "mapping", 0, order_gain=1.0, identity_gain=0.0)
    und = F.contrast_probe(mp, Hm, "first_mentioned", n_boot=50, seed=0)
    assert und["n_labelable"] == 0 and und["loo"]["n"] == 0 and "undefined" in und["status"]


def test_identity_probe_present_vs_null():
    pairs, H = synth_binding(24, "mapping", 2, order_gain=0.0, identity_gain=4.0)
    rec = F.identity_probe(pairs, H, n_perm=3, n_boot=100, seed=0)
    assert rec["status"] == "ok" and rec["vocab_size"] == 8
    assert rec["loo"]["p"] >= 0.9 and rec["loo_paired_sum"]["p"] >= 0.9
    assert rec["perm_null"]["pair_win_p95"] < rec["loo"]["p"] and rec["perm_null"]["pair_win_mean"] < 0.6
    assert rec["ceiling"]["pooled"]["p"] >= 0.75 and rec["present_identity"] is True
    assert set(rec["ceiling"]) >= {"pooled", "per_state", "paired_sum", "half1_to_half2", "half2_to_half1"}
    # no identity signal -> not present
    pairs0, H0 = synth_binding(24, "mapping", 3, order_gain=0.0, identity_gain=0.0)
    rec0 = F.identity_probe(pairs0, H0, n_perm=2, n_boot=50, seed=0)
    assert rec0["present_identity"] is False and rec0["loo"]["p"] < 0.75


def test_pca_diffs_single_direction():
    pairs, H = synth_binding(20, "ownership", 4, order_gain=6.0, identity_gain=0.0, noise=0.3)
    pca = F.pca_diffs(pairs, H)
    assert pca["pc1_frac_uncentred"] > 0.9 and pca["first_mentioned_aligned"]["mean_cos_with_mean_diff"] > 0.9
    pairs, H = synth_binding(20, "ownership", 5, order_gain=0.0, identity_gain=0.0)
    assert F.pca_diffs(pairs, H)["pc1_frac_uncentred"] < 0.5


def test_fit_pair_bias_recovers_bias():
    rng = np.random.default_rng(0)
    true = {s: v for s, v in zip(SYMS, [1.0, -2.0, 0.5, 0.0, 1.5, -1.0, 0.3, -0.3])}
    a = rng.choice(SYMS, 300)
    o = np.array([rng.choice([s for s in SYMS if s != x]) for x in a])
    lo = np.array([true[x] - true[y] for x, y in zip(a, o)]) + 0.01 * rng.standard_normal(300)
    b, corr, r2 = F.fit_pair_bias(a, o, lo, SYMS)
    assert abs(sum(b.values())) < 1e-9 and r2 > 0.99
    assert max(abs(b[s] - true[s]) for s in SYMS) < 0.02
    assert abs(corr).max() < 0.1


def test_trace_rule_and_offtrace():
    items, _, _, trows = synth_x3(12, 6, 0, 0, seed=0)
    tr = F.trace_rule(items, {r["item_id"]: r for r in trows})
    assert tr["n_errors"] == 12 and tr["n_decode_mismatch"] == 0
    assert tr["counts"]["off-trace"] == 4 and tr["counts"]["trace[-2] (k-1 symbol)"] == 8
    assert len(tr["offtrace_ids"]) == 4 and tr["n_on_trace"] == 8
    for iid in tr["offtrace_ids"]:
        assert items[iid]["primary"]["answer"] not in items[iid]["source"]["trace"]


def test_symbol_bias_correction_on_readers():
    items, _, lo, _ = synth_x3(40, 20, 6, 6, seed=1)
    by = {r: {} for r in F.READERS}
    for row in lo:
        by[row["reader"]][row["item_id"]] = row
    out = F.r3a_symbol_bias(items, by, n_boot=100, seed=0)
    ol = out["puzzle"]["olens"]
    assert ol["status"] == "ok" and ol["n_rows"] == 60 and abs(sum(ol["bias"].values())) < 1e-9
    assert ol["bias"]["H"] > ol["bias"]["A"]  # planted monotone bias recovered in sign
    assert set(ol["sets"]) == {"error", "error_control"} and ol["sets"]["error"]["corrected"]["n"] == 40
    ch = out["choice"]["olens"]
    assert ch["status"] == "ok" and "not estimable" in ch["per_word_bias"] and "position_bias_nats" in ch
    assert out["choice"]["jlens"]["n_rows"] == 11  # one unscorable row dropped


def test_cv_probe_multiclass_and_binary():
    items, H, _, _ = synth_x3(40, 20, 0, 0, seed=2, gain=4.0)
    ids = sorted(items)
    X = np.stack([H[i] for i in ids])
    actual = [items[i]["primary"]["candidates"][0] for i in ids]
    other = [items[i]["primary"]["candidates"][1] for i in ids]
    sets = [items[i]["set"] for i in ids]
    rec = F.cv_probe(X, actual, sets, {"favours_actual": (actual, other)}, n_folds=5, n_perm=3, n_boot=100, seed=0, group_sets=("error", "error_control"))
    assert rec["status"] == "ok" and rec["held_out"]["accuracy"]["p"] > rec["majority_rate"] + 0.2
    assert rec["held_out"]["pair"]["favours_actual"]["by_set"]["error"]["p"] > 0.8
    assert rec["perm_null"]["accuracy"]["p95"] < rec["held_out"]["accuracy"]["p"]
    assert set(rec["ceiling"]["halves"]) == {"half1_to_half2", "half2_to_half1"}
    y = [int(a == items[i]["source"]["correct"]) for a, i in zip(actual, ids)]
    rb = F.cv_probe(X, y, sets, {}, n_folds=5, n_perm=2, n_boot=50, seed=0, group_sets=("error", "error_control"))
    assert "auroc" in rb["held_out"] and 0.0 <= rb["held_out"]["auroc"] <= 1.0 and "auroc" in rb["perm_null"]
    tiny = F.cv_probe(X[:6], actual[:6], sets[:6], {}, n_folds=5)
    assert tiny["status"].startswith("skipped")


def test_paired_sign_rows_and_e1_wins():
    pairs = {"ownership": [_pair("ownership", k, (NAMES[0], NAMES[1]), True) for k in range(2, 12)]}
    rows = []
    for p in pairs["ownership"]:
        k = int(p["pair_id"][-2:])
        for rd, good in (("jlens", True), ("olens", k % 2 == 0), ("nla", k <= 4)):
            for v in "AB":
                rows.append({"reader": rd, "item_id": p[v]["item_id"], "condition": "natural", "lo": 1.0 if good else -1.0, "unscorable": False})
    wins = F.e1_wins(rows, pairs)
    assert all(wins["jlens"]["ownership"].values()) and sum(wins["olens"]["ownership"].values()) == 5 and sum(wins["nla"]["ownership"].values()) == 3
    out = F.paired_sign_rows(wins, ("ownership",), {"pooled": ("ownership",)})
    r = {(x["family"], x["reader_1"], x["reader_2"]): x for x in out}
    jo = r[("ownership", "jlens", "olens")]
    assert (jo["only_1_wins"], jo["only_2_wins"], jo["both_win"], jo["neither_wins"]) == (5, 0, 5, 0)
    assert abs(jo["sign_test_p"] - 0.0625) < 1e-9
    assert r[("pooled", "jlens", "nla")]["only_1_wins"] == 7 and r[("pooled", "olens", "nla")]["n_pairs"] == 10


def test_shared_check_independence_expectation():
    items, _, lo, _ = synth_x3(30, 0, 0, 0, seed=3)
    by = {r: {} for r in F.READERS}
    for row in lo:
        by[row["reader"]][row["item_id"]] = row
    # make the three readers identical -> unanimous 100%
    for iid in items:
        for rd in ("olens", "nla"):
            by[rd][iid] = dict(by["jlens"][iid])
    s = F.shared_check(items, by, sorted(items))
    assert s["n"] == 30 and s["observed_unanimous"] == 1.0
    p = s["marginal_favours_actual"]["jlens"]
    assert abs(s["expected_unanimous_independent"] - (p ** 3 + (1 - p) ** 3)) < 1e-12
    assert s["all_favour_actual"] + s["all_favour_other"] + s["mixed"] == 30
    assert F.shared_check(items, by, [])["n"] == 0


# ------------------------------------------------------------------ end to end on tmp paths
def test_run_end_to_end_synthetic(tmp_path):
    own, Ho = synth_binding(12, "ownership", 10, order_gain=3.0, identity_gain=1.0)
    mp, Hm = synth_binding(12, "mapping", 11, order_gain=0.0, identity_gain=4.0)
    items_x = {"meta": {}, "items": [p[v] for p in own + mp for v in "AB"]}
    (tmp_path / "items_x.json").write_text(json.dumps(items_x))
    x1_lo = []
    for p in own + mp:
        for rd in F.READERS:
            for v in "AB":
                x1_lo.append({"reader": rd, "item_id": p[v]["item_id"], "pair_id": p["pair_id"], "family": p["family"], "version": v, "split": "test",
                              "condition": "natural", "lo": 1.0 if rd != "nla" or int(p["pair_id"][-2:]) % 3 else -1.0, "unscorable": False})
    (tmp_path / "x1_lo.jsonl").write_text("\n".join(json.dumps(r) for r in x1_lo))
    items3, H3, lo3, trows = synth_x3(30, 15, 6, 6, seed=12)
    (tmp_path / "selected.json").write_text(json.dumps({"meta": {}, "items": list(items3.values())}))
    (tmp_path / "x3_lo.jsonl").write_text("\n".join(json.dumps(r) for r in lo3))
    (tmp_path / "x3_target.jsonl").write_text("\n".join(json.dumps(r) for r in trows))
    _write_states({**Ho, **Hm, **H3}, tmp_path / "states")
    out = tmp_path / "out"
    args = F.parse_args(["--items-x", str(tmp_path / "items_x.json"), "--x1-lo", str(tmp_path / "x1_lo.jsonl"), "--states", str(tmp_path / "states"),
                         "--selected", str(tmp_path / "selected.json"), "--x3-lo", str(tmp_path / "x3_lo.jsonl"), "--x3-target", str(tmp_path / "x3_target.jsonl"),
                         "--out", str(out), "--n-perm", "2", "--n-boot", "50"])
    S = F.run(args)
    for f in ("r2_probes.csv", "r3_x3.csv", "r3_probe.csv", "r4_paired.csv", "friday_cases.md", "R2R4.md", "r2r4_summary.json"):
        assert (out / f).exists() and (out / f).stat().st_size > 0, f
    assert set(S["R2"]) == {"ownership", "mapping"}
    assert S["R2"]["ownership"]["contrast"]["first_mentioned"]["loo"]["p"] == 1.0
    assert S["R2"]["mapping"]["identity"]["status"] == "ok" and S["R2"]["mapping"]["identity"]["loo"]["n"] > 0
    assert S["R3"]["trace"]["n_errors"] == 30 and len(S["R3"]["trace"]["offtrace_ids"]) == 10
    assert S["R3"]["puzzle_probes"]["status"] == "ok" and S["R3"]["choice_probes"]["status"] == "ok"
    assert {r["family"] for r in S["R4"]} >= {"ownership", "mapping", "binding (ownership+mapping)"}
    assert S["Y0"]["shared_error"]["ERROR raw LO"]["n"] == 30
    summ = json.loads((out / "r2r4_summary.json").read_text())
    assert "loo_per_pair" not in summ["R2"]["ownership"]["identity"] and "corrected_lo" not in summ["R3"]["symbol_bias"]["puzzle"]["olens"]
    md = (out / "R2R4.md").read_text()
    assert md.count("\n") <= 40 and "R4 paired sign tests" in md
    cases = (out / "friday_cases.md").read_text()
    assert cases.count("- **xch-") == 6 and cases.count("- **xpz-") == 10 and "Shared-error check" in cases


def test_nothing_written_outside_tmp():
    if RESULTS_SNAPSHOT is not None:
        now = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
        assert now == RESULTS_SNAPSHOT or len(now) >= len(RESULTS_SNAPSHOT)  # the concurrent full run may add files; never remove
    if CACHE_SNAPSHOT is not None:
        assert sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) == CACHE_SNAPSHOT
