"""Offline tests for W3 (w_analysis/w3_claims.py) and W4 (w_analysis/w4_consistency.py) on a synthetic fixture that mirrors the pod
schemas (s4_consistency.py rows, s3_score.py S1/S2 rows, x3_lo rows, items_y1_selected / items_w, the G1 W3 json). The Track C judge is
mocked at judge._post: the fixture readouts are bullet lists "- [label] claim", which the fake judge splits and labels verbatim.
Everything is written under tmp_path; nothing under results/ or cache/ is touched."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)

from projects.g_agreement.w_analysis import w3_claims as W3  # noqa: E402
from projects.g_agreement.w_analysis import w4_consistency as W4  # noqa: E402
from projects.g_agreement.w_claims import judge as J  # noqa: E402

# ------------------------------------------------------------------ fixture: states
ERRORS = {  # item_id: (actual = model's wrong answer, correct)
    "xpz-0001": ("C", "E"), "xpz-0002": ("A", "G"), "xpz-0003": ("F", "D"), "xpz-0004": ("B", "H"), "xpz-0005": ("A", "G"), "xpz-0006": ("D", "C"),
}
COUNTS = {"wcnt-0001": 27, "wcnt-0002": 8, "wcnt-0003": 61, "wcnt-0004": 14}
CANDS_99 = [str(i) for i in range(1, 100)]
N_RANDOM = 3

IN_TRUE = "- [input_true] The prompt describes arrows between letters"
IN_FALSE = "- [input_false] The prompt is about colours"
UNV = "- [unverifiable] The style is terse"
CNT_IN_TRUE = "- [input_true] The prompt asks how many objects are in a container"


def error_readout(reader: str, iid: str, k: int) -> str:
    actual, correct = ERRORS[iid]
    lines = [IN_TRUE]
    if iid == "xpz-0001":                      # actual named in 6/8 (two phrasings), correct in 2/8; one stray input_false
        lines.append(f"- [computation_true] The answer is {actual}" if k < 3 else (f"- [computation_true] The model will output {actual}" if k < 6 else f"- [computation_false] The answer is {correct}"))
        if k == 0:
            lines.append(IN_FALSE)
    elif iid == "xpz-0002":                    # actual named in ONE sample only; the rest name the correct answer
        lines.append(f"- [computation_true] The answer is {actual}" if k == 0 else f"- [computation_false] The answer is {correct}")
    elif iid == "xpz-0003":                    # a third symbol (neither actual nor correct) in every sample
        lines.append("- [computation_false] The answer is H")
    elif iid == "xpz-0004":                    # Oracle names actual consistently, NLA never emits a computation claim
        if reader == "olens":
            lines.append(f"- [computation_true] The answer is {actual}")
        else:
            lines.append(UNV)
    elif iid == "xpz-0005":                    # the answer is A: article guard matters
        lines.append(f"- [computation_true] A chain of arrows; the model reaches A." if k % 2 == 0 else f"- [computation_true] The answer is 'a'")
    else:                                      # xpz-0006: no claims at all in half the samples
        if k % 2 == 0:
            lines = [f"- [computation_false] The answer is {correct}"]
        else:
            lines = []
    return "\n".join(lines)


def counts_readout(reader: str, iid: str, k: int) -> str:
    v = COUNTS[iid]
    lines = [CNT_IN_TRUE]
    if iid == "wcnt-0001":                     # value in 5/8, twenty-six (words) in 3/8
        lines.append(f"- [computation_true] The count is {v}" if k < 5 else "- [computation_false] The count is twenty-six")
    elif iid == "wcnt-0002":                   # always wrong, consistently (the "consistent wrong copy")
        lines.append("- [computation_false] The number is 9")
    elif iid == "wcnt-0003":                   # right once
        lines.append(f"- [computation_true] The number is {v}" if k == 7 else "- [computation_false] The number is 60")
    else:                                      # wcnt-0004: right always, two phrasings
        lines.append(f"- [computation_true] There are {v} objects" if k % 2 else f"- [computation_true] The count is {v}")
    return "\n".join(lines)


def random_readout(reader: str, k: int) -> str:
    return [IN_TRUE, "- [unverifiable] Something about the weather", "- [input_true] The prompt describes arrows between letters\n- [computation_false] The answer is Z"][k]


def wrap(reader: str, text: str) -> str:
    return f"<explanation>\n{text}\n</explanation>" if reader == "nla" else text


def build_fixture(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    # items (Y1 selected format and W bank format)
    y1 = {"meta": {}, "items": [{"item_id": i, "pair_id": i, "version": "A", "family": "puzzle", "set": "error", "split": "test", "template_id": "pz-t1",
                                  "prompt_text": f"F → E. D → H. Start at G and follow the arrows three times. ({i})", "render": "chat",
                                  "primary": {"question": "Which symbol do you reach?", "candidates": [a, c], "answer": a, "answer_aliases": [a.lower()]},
                                  "target_answer_regex": "(?<![A-Za-z])([A-H])(?![A-Za-z])", "source": {"correct": c, "k": 3}} for i, (a, c) in ERRORS.items()]}
    w = {"meta": {}, "items": [{"item_id": i, "pair_id": i, "version": "A", "family": "counts", "split": "test",
                                 "prompt_text": f"In the tray there are {v} marbles. How many marbles are in the tray? Reply with the number only.",
                                 "primary": {"question": "How many marbles are in the tray?", "candidates": [str(v)], "candidates_all": CANDS_99, "answer": str(v)}} for i, v in COUNTS.items()]}
    (root / "items_y1.json").write_text(json.dumps(y1))
    (root / "items_w.json").write_text(json.dumps(w))
    # S4 samples (s4_consistency.py schema; reader names as the pod writes them)
    s4 = []
    for reader in ("olens", "nla"):
        for iid, (a, c) in ERRORS.items():
            for k in range(8):
                s4.append({"key": f"{reader}|{iid}|s{k}", "state_item_id": iid, "reader": reader, "sample_idx": k, "text": wrap(reader, error_readout(reader, iid, k)),
                           "candidates": [a, c], "answer": c, "actual_answer": a, "condition": "natural", "family": "errors", "layer": 42, "seed": 1, "n_new_tokens": 20,
                           "finish_reason": "stop", "activation_norm": 100.0, "norm_matched_to": None})
        for iid, v in COUNTS.items():
            for k in range(8):
                s4.append({"key": f"{reader}|{iid}|s{k}", "state_item_id": iid, "reader": reader, "sample_idx": k, "text": wrap(reader, counts_readout(reader, iid, k)),
                           "candidates": CANDS_99, "answer": str(v), "actual_answer": str(v), "condition": "natural", "family": "counts", "layer": 42, "seed": 1,
                           "n_new_tokens": 20, "finish_reason": "stop", "activation_norm": 100.0, "norm_matched_to": None})
        for k in range(N_RANDOM):
            s4.append({"key": f"{reader}|random-{k:02d}|s0", "state_item_id": f"random-{k:02d}", "reader": reader, "sample_idx": 0, "text": wrap(reader, random_readout(reader, k)),
                       "candidates": None, "answer": None, "actual_answer": None, "condition": "random", "family": "random", "layer": 42, "seed": 1, "n_new_tokens": 20,
                       "finish_reason": "stop", "activation_norm": 100.0, "norm_matched_to": 100.0})
    W3.write_jsonl(root / "s4_samples.jsonl", s4)
    # S3 rows: S2 natural error rows (4 of 6 states; cand order flipped on one), S1 counts rows
    s3 = []
    fav = {"xpz-0001": True, "xpz-0002": False, "xpz-0003": True, "xpz-0004": False}
    for reader in ("olens", "nla"):
        for iid, f in fav.items():
            a, c = ERRORS[iid]
            flip = iid == "xpz-0003"
            lo = 1.5 if f else -1.5
            s3.append({"key": f"{reader}|S2|{iid}|A|W2|natural|0.0|None", "entry_key": f"{iid}|A|W2|natural|0.0|None", "reader": reader, "unit": "S2", "read_layer": 42,
                       "family": "errors", "state_item_id": iid, "direction": "natural", "condition": "natural", "alpha": 0.0,
                       "cand_A": c if flip else a, "cand_B": a if flip else c, "lo_own": -lo if flip else lo, "candidates": [c, a] if flip else [a, c]})
        for iid, v in COUNTS.items():
            am = str(v) if (iid in ("wcnt-0001", "wcnt-0004")) == (reader == "olens") else str(v + 1)
            scores = [0.0] * 99
            scores[int(am) - 1] = 3.0
            s3.append({"key": f"{reader}|S1|{iid}", "entry_key": iid, "reader": reader, "unit": "S1", "layer": 42, "family": "counts", "item_id": iid,
                       "cand_A": str(v), "cand_B": str(v + 1), "true_answer": str(v), "candidates": CANDS_99, "scores": scores, "argmax": am, "lo_own": 1.0})
    W3.write_jsonl(root / "s3_lo.jsonl", s3)
    # X3 layer-42 rows for every error state (fallback)
    x3 = [{"key": f"{reader}|{iid}", "reader": reader, "item_id": iid, "family": "puzzle", "set": "error", "layer": 42, "cand_actual": a, "cand_other": c,
           "lo_actual": 0.5 if reader == "olens" else -0.5, "favours_actual": reader == "olens", "unscorable": False} for reader in ("jlens", "olens", "nla") for iid, (a, c) in ERRORS.items()]
    W3.write_jsonl(root / "x3_lo.jsonl", x3)
    # G1 W3 json (minimal)
    g1 = {"summary": {"readers": {"NLA": {"n_items": 32, "n_claims": 242, "precision": {"input": {"n_items": 32, "n_claims": 186, "n_true": 50, "precision": 0.27, "lo": 0.23, "hi": 0.32},
                                                                                           "computation": {"n_items": 32, "n_claims": 54, "n_true": 25, "precision": 0.46, "lo": 0.32, "hi": 0.59}}},
                                  "Oracle": {"n_items": 32, "n_claims": 162, "precision": {"input": {"n_items": 22, "n_claims": 43, "n_true": 17, "precision": 0.40, "lo": 0.27, "hi": 0.53},
                                                                                              "computation": {"n_items": 32, "n_claims": 113, "n_true": 39, "precision": 0.35, "lo": 0.20, "hi": 0.50}}}}}}
    (root / "W3_g1.json").write_text(json.dumps(g1))
    return {"root": root, "s4": root / "s4_samples.jsonl", "s3": root / "s3_lo.jsonl", "x3": root / "x3_lo.jsonl", "items_y1": root / "items_y1.json",
            "items_w": root / "items_w.json", "g1": root / "W3_g1.json"}


class FakePost:
    """Stands in for judge._post: splits the READOUT's '- [label] claim' bullets into judged claims."""

    def __init__(self):
        self.calls = 0

    def __call__(self, payload):
        self.calls += 1
        user = payload["messages"][1]["content"]
        readout = user.rsplit("READOUT:", 1)[1]
        claims = []
        for line in readout.splitlines():
            line = line.strip()
            if line.startswith("- [") and "]" in line:
                label, text = line[3:].split("]", 1)
                claims.append({"claim": text.strip(), "label": label.strip(), "evidence": ""})
        return {"choices": [{"message": {"content": json.dumps({"claims": claims})}}], "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.0017}}


@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    return build_fixture(tmp_path_factory.mktemp("w34"))


@pytest.fixture(scope="module")
def pipeline(fx, tmp_path_factory):
    """prepare -> mocked judge -> W3 report -> W4 run, all under tmp."""
    out3 = fx["root"] / "w3"
    out4 = fx["root"] / "w4"
    plan = W3.run_prepare(s4=fx["s4"], items_y1=fx["items_y1"], items_w=fx["items_w"], out_dir=out3)
    fake = FakePost()
    orig = J._post
    J._post = fake
    try:
        rc = J.main(["--readouts", str(out3 / "s4_judge_input.jsonl"), "--items", "none", "--actual", "none", "--readers", "Oracle,NLA",
                     "--out", str(out3 / "claims_s4.jsonl"), "--usage", str(out3 / "judge_usage.json"), "--cache", str(out3 / "cache" / "judge_cache.jsonl")])
    finally:
        J._post = orig
    assert rc == 0
    s3 = W3.run_report(claims_path=out3 / "claims_s4.jsonl", s3=fx["s3"], x3=fx["x3"], g1=fx["g1"], out_dir=out3, n_boot=50)
    s4 = W4.run(claims_path=out3 / "claims_s4.jsonl", s4=fx["s4"], s3=fx["s3"], x3=fx["x3"], out_dir=out4, n_boot=50)
    return {"plan": plan, "fake": fake, "w3": s3, "w4": s4, "out3": out3, "out4": out4}


# ------------------------------------------------------------------ W3 helpers
def test_number_words_and_integers():
    assert W3.words_to_digits("twenty-seven marbles, seven, Forty two") == "27 marbles, 7, 42"
    assert W3.integers_in("the count is 27 (not 3.5, layer 42:0)") == [27]
    assert W3.integers_in("The count is twenty-six") == [26]


def test_mentions_symbols_and_numbers():
    assert W3.mentions("The answer is C", "C")
    assert W3.mentions("The answer is 'c'", "C")
    assert not W3.mentions("Can we Count on it", "C")
    assert not W3.mentions("A chain of arrows between letters", "A")           # article
    assert W3.mentions("the model reaches A.", "A")
    assert W3.mentions("symbol A maps to B", "A")
    assert W3.mentions("A -> B", "A")
    assert W3.mentions("There are 27 objects", "27")
    assert not W3.mentions("There are 127 objects", "27")
    assert W3.claim_names("The answer is C, not E", ["C", "E"]) == {"C", "E"}
    assert W3.claim_names("whatever", None) == set()


def test_computation_truths_errors_and_counts():
    base = {"family": "errors", "candidates": ["C", "E"], "actual_answer": "C", "answer": "E", "claim_type": "computation"}
    c = dict(base, claim_text="The answer is C", truth=True, names_actual=True, names_correct=False)
    t = W3.computation_truths(c)
    assert t["vs_actual_judge"] is True and t["vs_correct_judge"] is False and t["vs_actual_text"] is True and t["vs_correct_text"] is False
    c = dict(base, claim_text="The answer is E", truth=False, names_actual=False, names_correct=True)
    t = W3.computation_truths(c)
    assert t["vs_actual_judge"] is False and t["vs_correct_judge"] is True and t["vs_correct_text"] is True
    c = dict(base, claim_text="The answer is H", truth=False, names_actual=False, names_correct=False)
    t = W3.computation_truths(c)
    assert t["vs_correct_judge"] is False and t["vs_actual_text"] is None
    cc = {"family": "counts", "answer": "27", "truth": False, "stated": 26}
    t = W3.computation_truths(cc)
    assert t["vs_value_judge"] is False and t["vs_value_text"] is False
    assert W3.computation_truths({"family": "counts", "answer": "27", "truth": True, "stated": None})["vs_value_text"] is None


def test_select_judge_rows_budget_and_subset(fx):
    samples = W3.read_jsonl(fx["s4"])
    items = W3.load_item_prompts(fx["items_y1"], fx["items_w"])
    rows, plan = W3.select_judge_rows(samples, items)
    n_nat = (len(ERRORS) + len(COUNTS)) * 8 * 2
    assert plan["n_calls"] == n_nat + 2 * N_RANDOM and plan["decision"] == "full"
    assert abs(plan["estimate_usd"] - plan["n_calls"] * 0.167368 / 96) < 1e-3
    assert plan["missing_prompt_text"] == 0
    r0 = next(r for r in rows if r["state_item_id"] == "xpz-0001" and r["sample_idx"] == 3 and r["reader"] == "Oracle")
    assert r0["gen_id"] == "Oracle|xpz-0001|s3" and "arrows" in r0["prompt_text"] and r0["actual_answer"] == "C" and r0["answer"] == "E"
    # the cap forces the seeded subset: 2 errors + 1 counts here, same ids as numpy default_rng(0) over the sorted ids
    rows2, plan2 = W3.select_judge_rows(samples, items, cap_usd=0.01, subset=(2, 1), seed=0)
    assert plan2["decision"].startswith("subset") and plan2["n_states_judged"] == {"errors": 2, "counts": 1}
    kept = sorted({r["state_item_id"] for r in rows2 if r["condition"] == "natural"})
    assert kept == sorted(W3.seeded_subset(sorted(ERRORS), 2, 0) + W3.seeded_subset(sorted(COUNTS), 1, 0))
    assert sum(r["condition"] == "random" for r in rows2) == 2 * N_RANDOM         # random vectors always judged
    # the real S4 geometry: 150 states x 8 x 2 + 100 random = 2,500 calls -> $4.36 < $8 -> full
    assert 2500 * W3.COST_PER_CALL < W3.CAP_USD


def test_native_lo_sources(fx):
    s3, x3 = W3.read_jsonl(fx["s3"]), W3.read_jsonl(fx["x3"])
    actual_of = {i: a for i, (a, c) in ERRORS.items()}
    lo = W3.native_lo(s3, x3, actual_of)
    assert lo[("Oracle", "xpz-0001")] == {"ok": True, "source": "s3_lo:S2 natural L42", "value": 1.5}
    assert lo[("NLA", "xpz-0002")]["ok"] is False
    assert lo[("Oracle", "xpz-0003")]["ok"] is True and lo[("Oracle", "xpz-0003")]["value"] == -1.5       # flipped cand order handled
    assert lo[("Oracle", "xpz-0005")]["source"] == "x3_lo:L42" and lo[("Oracle", "xpz-0005")]["ok"] is True
    assert lo[("NLA", "xpz-0006")]["ok"] is False
    assert lo[("Oracle", "wcnt-0001")] == {"ok": True, "source": "s3_lo:S1 argmax", "value": "27"} and lo[("NLA", "wcnt-0001")]["ok"] is False
    assert ("Oracle", "jlens") not in lo


# ------------------------------------------------------------------ W4 matcher
def _c(text, ctype="computation", cands=("C", "E"), **kw):
    d = {"claim_text": text, "claim_type": ctype, "candidates": list(cands)}
    d.update(kw)
    d["norm"], d["anchors"], d["tokens"] = W4.normalise(text, d["candidates"])
    return d


def test_normalise_anchors_and_tokens():
    n, anc, tok = W4.normalise("<explanation>The model will output 'C'.</explanation>", ["C", "E"])
    assert anc == frozenset({"C"}) and "answer" in tok and "model" in tok
    _, anc2, tok2 = W4.normalise("The count is twenty-six marbles", None)
    assert anc2 == frozenset({"26"}) and "marble" in tok2 and "count" in tok2
    _, anc3, _ = W4.normalise("A chain of arrows between letters", None)
    assert anc3 == frozenset()
    _, anc4, _ = W4.normalise("the model reaches A.", None)
    assert anc4 == frozenset({"A"})


def test_claims_match_rules():
    a, b = _c("The answer is C"), _c("The model will output C")
    assert W4.claims_match(a, b)                                  # synonyms share 'answer'
    assert not W4.claims_match(a, _c("The answer is E"))          # different anchor
    assert not W4.claims_match(a, _c("The answer is C", ctype="input"))   # different type
    assert not W4.claims_match(_c("The count is 27", cands=()), _c("The count is 26", cands=()))
    assert W4.claims_match(_c("The count is 27", cands=()), _c("The count is twenty-seven", cands=()))
    assert W4.claims_match(_c("The prompt describes arrows between letters", "input", ()), _c("The input describes arrows between letters", "input", ()))
    assert not W4.claims_match(_c("The prompt describes arrows between letters", "input", ()), _c("The prompt is about colours", "input", ()))
    assert not W4.claims_match(_c("There are 27 objects", cands=()), _c("The count is 27", cands=()))        # anchored, no shared content token
    assert W4.claims_match(_c("There are 27 objects", cands=()), _c("The count is 27", cands=()), "lenient")
    assert not W4.claims_match(a, b, "strict")                    # Jaccard {answer,c?}: tokens {answer} vs {model, answer} = 0.5 < 0.75
    assert W4.claims_match(a, _c("the answer is c"), "strict")    # identical after normalisation


def test_agreement_counts_small():
    cl = []
    for k in range(8):
        cl.append(_c("The answer is C" if k < 6 else "The answer is E", reader="Oracle", item_id="s1", sample_idx=k, condition="natural"))
    cl.append(_c("The prompt is about colours", "input", reader="Oracle", item_id="s1", sample_idx=0, condition="natural"))
    cl.append(_c("The answer is C", reader="Oracle", item_id="s1", sample_idx=0, condition="natural"))   # duplicate within the same sample: does not add
    W4.agreement_counts(cl)
    ag = {(c["claim_text"], c["sample_idx"]): c["agreement"] for c in cl}
    assert ag[("The answer is C", 0)] == 6 and ag[("The answer is C", 5)] == 6
    assert ag[("The answer is E", 6)] == 2 and cl[6]["kept"]
    assert ag[("The prompt is about colours", 0)] == 1 and not cl[8]["kept"]
    assert all(c["n_samples"] == 8 for c in cl)


def test_auroc_and_bootstrap():
    assert W4.auroc([2, 3], [1, 1]) == 1.0
    assert W4.auroc([1, 1], [1, 1]) == 0.5
    assert abs(W4.auroc([3, 1], [2, 2]) - 0.5) < 1e-9
    assert W4.auroc([], [1]) != W4.auroc([], [1])                 # nan
    items = ["a", "a", "b", "b", "c", "c"]
    r = W4.auroc_item_bootstrap(items, [8, 1, 7, 2, 6, 3], [True, False, True, False, True, False], n_boot=200)
    assert r["auroc"] == 1.0 and r["lo"] is not None and r["lo"] <= r["auroc"] <= r["hi"] and r["n_items"] == 3
    r0 = W4.auroc_item_bootstrap(items, [1] * 6, [True] * 6, n_boot=10)
    assert r0["auroc"] is None


def test_paired_rate_diff():
    d = W4.paired_rate_diff([True, False, False, False], [True, True, True, False], n_boot=200)
    assert d["rate_a"] == 0.25 and d["rate_b"] == 0.75 and d["diff"] == -0.5 and d["lo"] <= -0.5 <= d["hi"]
    assert W4.paired_rate_diff([], [])["diff"] is None
    assert W4.paired_rate_diff([True], [False], n_boot=0)["lo"] is None


# ------------------------------------------------------------------ end to end on the fixture
def test_pipeline_files_and_plan(pipeline):
    for f in ("s4_judge_input.jsonl", "s4_judge_plan.json", "claims_s4.jsonl", "w3.md", "w3.csv", "w3_summary.json"):
        assert (pipeline["out3"] / f).exists(), f
    for f in ("w4.md", "w4.csv", "w4_summary.json", "fig_w4.png", "claims_agreement.jsonl"):
        assert (pipeline["out4"] / f).exists(), f
    assert pipeline["fake"].calls == pipeline["plan"]["n_calls"]
    assert "w_claims.judge" in pipeline["plan"]["judge_command"] and "--items none --actual none" in pipeline["plan"]["judge_command"]


def test_w3_numbers(pipeline):
    s = pipeline["w3"]
    o = s["readers"]["Oracle"]["errors"]
    assert o["n_states"] == 6 and o["n_readouts"] == 48
    P = o["precision"]
    # vs actual (judge): xpz-0001 6T 2F, 0002 1T 7F, 0003 0T 8F, 0004 8T, 0005 8T, 0006 0T 4F  -> 23 true / 44
    assert P["computation_vs_actual_judge"]["n_true"] == 23 and P["computation_vs_actual_judge"]["n_claims"] == 44
    # vs correct (judge-anchored): 0001 2, 0002 7, 0006 4 name the correct symbol -> 13 true / 44
    assert P["computation_vs_correct_judge"]["n_true"] == 13 and P["computation_vs_correct_judge"]["n_claims"] == 44
    # text check vs actual excludes the third-symbol claims of xpz-0003 (names neither): 44 - 8 = 36 decided
    assert P["computation_vs_actual_text"]["n_claims"] == 36 and P["computation_vs_actual_text"]["n_true"] == 23
    assert o["computation_names"] == {"actual_only": 23, "correct_only": 13, "both": 0, "neither": 8}
    assert P["input"]["n_true"] == 40 and P["input"]["n_claims"] == 41          # xpz-0006 has no input claims
    n = s["readers"]["NLA"]["errors"]
    assert n["precision"]["computation_vs_actual_judge"]["n_claims"] == 36                      # xpz-0004 has no NLA computation claims
    assert s["text_check_agreement"]["Oracle/errors"]["rate"] == 1.0
    c = s["readers"]["Oracle"]["counts"]
    assert c["precision"]["computation_vs_value_judge"]["n_true"] == 5 + 0 + 1 + 8 and c["precision"]["computation_vs_value_text"]["n_true"] == 14
    # cross-tab: S3 covers 4 error states, x3 the other 2; Oracle LO favours actual on 0001, 0003 (s3) + 0005, 0006 (x3)
    xt = o["crosstab_native_lo"]
    assert xt["n_states_with_lo"] == 6 and xt["sources"] == {"s3_lo:S2 natural L42": 4, "x3_lo:L42": 2}
    assert xt["cells"]["lo_favours_actual"]["n_states"] == 4 and xt["cells"]["lo_favours_correct"]["n_states"] == 2
    assert xt["cells"]["lo_favours_actual"]["computation_precision"]["vs_actual_judge"]["n_claims"] == 8 + 8 + 8 + 4
    cx = c["crosstab_native_lo"]
    assert cx["cells"]["lo_exact"]["n_states"] == 2 and cx["sources"] == {"s3_lo:S1 argmax": 4}
    assert s["g1"]["Oracle"]["computation"]["precision"] == 0.35
    md = (pipeline["out3"] / "w3.md").read_text()
    assert "G1 test" in md and "S4 errors" in md and "lo_favours_actual" in md
    csv_text = (pipeline["out3"] / "w3.csv").read_text().splitlines()
    assert csv_text[0].startswith("source,reader,family,claim_type,reference") and len(csv_text) > 10


def test_w4_numbers(pipeline):
    S = pipeline["w4"]
    o = S["readers"]["Oracle"]["errors"]
    assert o["n_states"] == 6
    # xpz-0001: "answer is C" x3 + "model will output C" x3 match each other -> agreement 6; "answer is E" x2 -> 2; input_false once -> 1
    hist = o["agreement_hist"]
    assert hist.get(1, 0) >= 1 and hist.get(6, 0) == 6
    kv = o["kept_vs_all"]
    x = kv["states_naming_actual_or_value"]
    # all: 0001, 0002, 0004, 0005 name the actual (4/6); kept: 0002's single sample is dropped -> 3/6 (0005: two phrasings x4 each, both anchored A sharing 'answer'? no:
    # "A chain of arrows; the model reaches A." tokens {chain, arrow, model, reach} vs "The answer is 'a'" {answer} -> no shared token -> each recurs 4x -> kept)
    assert x["rate_b"] == pytest.approx(4 / 6) and x["rate_a"] == pytest.approx(3 / 6) and x["lo"] <= x["diff"] <= x["hi"]
    assert kv["precision_vs_actual_judge"]["kept"]["n_true"] == 22 and kv["precision_vs_actual_judge"]["all"]["n_true"] == 23
    assert kv["input_false_share"]["all"]["k"] == 1 and kv["input_false_share"]["kept"]["k"] == 0
    assert "by_native_lo" in kv and kv["by_native_lo"]["lo_favours_actual"]["n"] == 4
    # AUROC: input claims: 48 true (agreement 8) vs 1 false (agreement 1) -> 1.0; computation: mixed
    assert o["auroc"]["input"]["auroc"] == 1.0
    assert 0 < o["auroc"]["computation"]["auroc"] < 1 and o["auroc"]["computation"]["lo"] is not None
    assert o["high_consistency_false_computation"]["k"] == 15                       # xpz-0002 7 (agr 7) + xpz-0003 8 (agr 8)
    c = S["readers"]["Oracle"]["counts"]
    cx = c["kept_vs_all"]["states_naming_actual_or_value"]
    assert cx["rate_b"] == pytest.approx(3 / 4) and cx["rate_a"] == pytest.approx(2 / 4)       # wcnt-0003's single correct sample is dropped
    assert c["agreement_hist"].get(3, 0) == 3                                        # twenty-six x3 (number words matched)
    r = S["random"]["Oracle"]
    assert r["n_random_vectors"] == 3 and r["n_random_claims"] == 4
    assert r["random_matches_recurring_natural_claim"]["k"] == 2 and r["random_matches_recurring_natural_claim"]["n"] == 4   # IN_TRUE twice
    assert r["within_random_recurrence"] is None
    assert r["natural_recur_ge2"]["n"] == o["n_claims"] + c["n_claims"]
    md = (pipeline["out4"] / "w4.md").read_text()
    assert "## (b) AUROC" in md and "## (c) Random-vector" in md and "Sensitivity" in md and "Verdict" in md
    rows = (pipeline["out4"] / "w4.csv").read_text().splitlines()
    assert rows[0].startswith("metric,reader,family,claim_type") and any("auroc_agreement_vs_correct" in r for r in rows)
    summ = json.loads((pipeline["out4"] / "w4_summary.json").read_text())
    assert set(summ["sensitivity"]) == {"strict", "lenient"} and "annotated" not in summ["summary"]


def test_w4_sample_inventory_handles_claimless_readouts(pipeline):
    """xpz-0006 has claims in 4 of 8 samples; the agreement denominator still comes from the S4 inventory (8)."""
    rows = W3.read_jsonl(pipeline["out4"] / "claims_agreement.jsonl")
    r6 = [r for r in rows if r["item_id"] == "xpz-0006" and r["reader"] == "Oracle"]
    assert len(r6) == 4 and all(r["n_samples"] == 8 and r["agreement"] == 4 for r in r6)
