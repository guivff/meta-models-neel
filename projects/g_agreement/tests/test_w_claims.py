"""Offline tests for projects/g_agreement/w_claims (Track C / V4). The judge is mocked; nothing is written under
results/ (all outputs go to tmp_path)."""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)

from projects.g_agreement.w_claims import human_sheet as HS  # noqa: E402
from projects.g_agreement.w_claims import judge as J  # noqa: E402
from projects.g_agreement.w_claims import kappa as K  # noqa: E402
from projects.g_agreement.w_claims import stats as ST  # noqa: E402
from projects.g_agreement.w_claims import w3 as W3  # noqa: E402


# ------------------------------------------------------------------ fixtures
ITEMS = {"items": [
    {"item_id": "own-02A", "family": "ownership", "prompt_text": "Elif carries the rope and Jonas carries the lantern. "
     "Who carries the lantern? Name only.", "primary": {"question": "Who carries the lantern?",
     "candidates": ["Jonas", "Elif"], "answer": "Jonas", "answer_aliases": ["jonas"]},
     "target_answer_regex": r"(?i)\bJonas\b"},
    {"item_id": "lang-03A", "family": "language", "prompt_text": "Answer in Dutch. Use one word. What colour is a ripe banana?",
     "primary": {"question": "In which language is the reply requested?", "candidates": ["Dutch", "Swedish"],
     "answer": "Dutch", "answer_aliases": ["dutch"]}, "target_answer_regex": r"(?i)\b(geel|gele)\b"},
]}

GENS = [
    {"gen_id": "g1|target|own-02A|s0", "module": "g1", "method": "target", "condition": "genuine", "item_id": "own-02A",
     "state_item_id": "own-02A", "family": "ownership", "split": "test", "sample_idx": 0,
     "input": {"visible_prompt": "<|im_start|>user\nElif carries ... Name only.<|im_end|>\n<|im_start|>assistant\n"},
     "raw_output": "Jonas"},
    {"gen_id": "g1|olens|own-02A|s0", "module": "g1", "method": "olens", "condition": "genuine", "item_id": "own-02A",
     "state_item_id": "own-02A", "family": "ownership", "split": "test", "sample_idx": 0,
     "raw_output": "- Alice\n- John\n- John"},
    {"gen_id": "g1|nla|own-02A|s0", "module": "g1", "method": "nla", "condition": "genuine", "item_id": "own-02A",
     "state_item_id": "own-02A", "family": "ownership", "split": "test", "sample_idx": 0,
     "raw_output": "<explanation>\nQ&A with answer-only instruction; the name 'Alex'.\n</br>\n</explanation>"},
    {"gen_id": "g1|nla|own-02A|s0dev", "module": "g1", "method": "nla", "condition": "genuine", "item_id": "own-01A",
     "state_item_id": "own-01A", "family": "ownership", "split": "dev", "sample_idx": 0, "raw_output": "x"},
    {"gen_id": "g1|jlens|own-02A|s0", "module": "g1", "method": "jlens", "condition": "genuine", "item_id": "own-02A",
     "state_item_id": "own-02A", "family": "ownership", "split": "test", "sample_idx": 0, "raw_output": "x"},
]

S4 = [
    {"state_item_id": "err-001", "reader": "NLA", "sample_idx": 3, "text": "<explanation>the answer is 7</explanation>",
     "candidates": ["7", "9"], "answer": "9", "actual_answer": "7", "prompt_text": "What is 3 + 4 + 2?"},
    {"state_item_id": "lang-03A", "reader": "Oracle", "sample_idx": 0, "text": "- Geel\n- Gul"},
]

CANNED = {
    "g1|olens|own-02A|s0": {"claims": [
        {"claim": "The answer is Alice", "label": "computation_false", "evidence": "actual Jonas"},
        {"claim": "The answer is John", "label": "computation_false", "evidence": "actual Jonas"}]},
    "g1|nla|own-02A|s0": {"claims": [
        {"claim": "The prompt asks for a name only", "label": "input_true", "evidence": "Name only."},
        {"claim": "The answer is Alex", "label": "computation_false", "evidence": "actual Jonas"},
        {"claim": "The dataset is synthetic", "label": "unverifiable", "evidence": ""},
        {"claim": "bogus", "label": "not_a_label", "evidence": ""}]},
    "NLA|err-001|s3": {"claims": [{"claim": "The answer is 7", "label": "computation_true", "evidence": "actual 7"}]},
    "Oracle|lang-03A|s0": {"claims": [{"claim": "The reply is Dutch", "label": "computation_true", "evidence": ""}]},
}


class FakePost:
    """Stands in for judge._post: returns canned claims keyed by the readout's gen_id (found in the user prompt)."""

    def __init__(self, fenced: bool = False):
        self.calls, self.fenced, self.payloads = 0, fenced, []

    def __call__(self, payload):
        self.calls += 1
        self.payloads.append(payload)
        user = payload["messages"][1]["content"]
        if "CLAIMS extracted" in user:                                  # relabel pass: flip every label to _true
            n = user.count("\n") - user.rsplit("CLAIMS extracted", 1)[0].count("\n")
            labels = [{"i": i + 1, "label": "computation_true"} for i in range(n)]
            content = json.dumps({"labels": labels})
        else:
            key = next((k for k in CANNED if _marker(k) in user), None)
            content = json.dumps(CANNED[key]) if key else json.dumps({"claims": []})
        if self.fenced:
            content = "```json\n" + content + "\n```"
        return {"choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001}}


def _marker(key):
    # the user prompt contains the readout text; map gen_id -> a distinctive substring of its readout
    return {"g1|olens|own-02A|s0": "- Alice", "g1|nla|own-02A|s0": "the name 'Alex'",
            "NLA|err-001|s3": "the answer is 7", "Oracle|lang-03A|s0": "- Geel"}[key]


@pytest.fixture
def files(tmp_path):
    items = tmp_path / "items.json"
    items.write_text(json.dumps(ITEMS))
    gens = tmp_path / "g1.jsonl"
    gens.write_text("\n".join(json.dumps(r) for r in GENS) + "\n")
    s4 = tmp_path / "s4.jsonl"
    s4.write_text("\n".join(json.dumps(r) for r in S4) + "\n")
    return {"items": items, "gens": gens, "s4": s4, "tmp": tmp_path}


# ------------------------------------------------------------------ loaders
def test_load_readouts_gens_format_filters_split_and_readers(files):
    rows = J.load_readouts(files["gens"], ["olens", "nla"], split="test")
    assert [r["gen_id"] for r in rows] == ["g1|olens|own-02A|s0", "g1|nla|own-02A|s0"]
    assert rows[0]["reader"] == "Oracle" and rows[1]["reader"] == "NLA"
    assert rows[0]["text"].startswith("- Alice")


def test_load_readouts_s4_format_defaults_gen_id_and_carries_fields(files):
    rows = J.load_readouts(files["s4"], ["Oracle", "NLA"])
    assert rows[0]["gen_id"] == "NLA|err-001|s3" and rows[0]["actual_answer"] == "7"
    assert rows[1]["gen_id"] == "Oracle|lang-03A|s0" and "candidates" not in rows[1]


def test_resolve_context_prefers_row_then_actual_then_items(files):
    items, actual = J.load_items(files["items"]), J.load_actual(files["gens"])
    assert actual["own-02A"]["actual_answer"] == "Jonas"
    ctx = J.resolve_context(J.load_readouts(files["gens"], ["olens"], "test")[0], items, actual)
    assert ctx["prompt_text"].startswith("<|im_start|>user")            # visible prompt from the target row
    assert ctx["answer"] == "Jonas" and ctx["candidates"] == ["Jonas", "Elif"] and ctx["actual_matches_key"] is True
    s4 = J.load_readouts(files["s4"], ["NLA", "Oracle"])
    c0 = J.resolve_context(s4[0], items, {})
    assert c0["prompt_text"] == "What is 3 + 4 + 2?" and c0["answer"] == "9" and c0["actual_answer"] == "7"
    c1 = J.resolve_context(s4[1], items, {})
    assert c1["prompt_text"].startswith("Answer in Dutch") and c1["actual_answer"] is None


def test_clean_readout_and_json_parsing():
    assert J.clean_readout("<explanation>\na</br>b\n</explanation>") == "a\nb"
    assert J.parse_json_content("```json\n{\"claims\": []}\n```") == {"claims": []}
    assert J.parse_json_content("Here you go: {\"claims\": [1]} thanks") == {"claims": [1]}
    assert J.label_type("input_false") == "input" and J.label_type("unverifiable") == "unverifiable"
    assert J.label_truth("computation_true") is True and J.label_truth("unverifiable") is None


# ------------------------------------------------------------------ judge pipeline (mocked)
def test_judge_readouts_labels_cache_and_usage(files):
    items, actual = J.load_items(files["items"]), J.load_actual(files["gens"])
    rows = J.load_readouts(files["gens"], ["olens", "nla"], "test")
    cache, usage, post = J.Cache(files["tmp"] / "cache.jsonl"), J.Usage(files["tmp"] / "usage.json"), FakePost()
    out = J.judge_readouts(rows, items, actual, "mock/judge", cache, usage, post, log=lambda *a: None)
    assert post.calls == 2
    assert post.payloads[0]["temperature"] == 0 and post.payloads[0]["response_format"]["type"] == "json_schema"
    assert [c["judge_label"] for c in out] == ["computation_false", "computation_false", "input_true",
                                               "computation_false", "unverifiable"]   # bad label dropped
    assert out[0]["claim_id"] == "g1|olens|own-02A|s0#0" and out[0]["truth"] is False
    assert out[2]["claim_type"] == "input" and out[4]["truth"] is None
    assert out[0]["actual_answer"] == "Jonas" and out[0]["n_claims_in_readout"] == 2
    u = json.loads((files["tmp"] / "usage.json").read_text())["mock/judge"]
    assert u["calls"] == 2 and u["prompt_tokens"] == 20 and abs(u["cost_usd"] - 0.002) < 1e-9
    # second run: fully cached, no API calls, identical output
    cache2 = J.Cache(files["tmp"] / "cache.jsonl")
    out2 = J.judge_readouts(rows, items, actual, "mock/judge", cache2, usage, post, log=lambda *a: None)
    assert post.calls == 2 and out2 == out


def test_judge_handles_fenced_json_and_empty_claims(files):
    items = J.load_items(files["items"])
    rows = J.load_readouts(files["s4"], ["NLA", "Oracle"])
    rows.append({"gen_id": "Oracle|none|s0", "reader": "Oracle", "state_item_id": "none", "sample_idx": 0,
                 "text": "nothing here"})
    out = J.judge_readouts(rows, items, {}, "mock/judge", J.Cache(files["tmp"] / "c.jsonl"), None,
                           FakePost(fenced=True), log=lambda *a: None)
    assert [c["judge_label"] for c in out] == ["computation_true", "computation_true", None]
    assert out[-1]["claim_id"] == "Oracle|none|s0#none" and out[-1]["n_claims_in_readout"] == 0


def test_relabel_and_subsample(files):
    items, actual = J.load_items(files["items"]), J.load_actual(files["gens"])
    rows = J.load_readouts(files["gens"], ["olens", "nla"], "test")
    claims = J.judge_readouts(rows, items, actual, "mock/judge", J.Cache(files["tmp"] / "c.jsonl"), None, FakePost(),
                              log=lambda *a: None)
    sub = J.subsample_claims(claims, 100, 0)
    assert len(sub) == 3 and all(c["claim_type"] == "computation" for c in sub)
    assert len(J.subsample_claims(claims, 2, 0)) == 2
    post = FakePost()
    rel = J.relabel_claims(sub, "mock/judge2", J.Cache(files["tmp"] / "c.jsonl"), None, post, log=lambda *a: None)
    assert post.calls == 2 and len(rel) == 3
    assert {r["judge2_label"] for r in rel} == {"computation_true"}
    assert rel[0]["judge1_label"] == "computation_false"


def test_cli_end_to_end_with_mock(files, monkeypatch):
    monkeypatch.setattr(J, "_post", FakePost())
    out = files["tmp"] / "claims.jsonl"
    J.main(["--readouts", str(files["s4"]), "--items", str(files["items"]), "--actual", "none", "--out", str(out),
            "--readers", "Oracle,NLA", "--judge", "mock/judge", "--usage", str(files["tmp"] / "u.json"),
            "--cache", str(files["tmp"] / "c.jsonl")])
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    assert len(rows) == 2 and rows[0]["item_id"] == "err-001" and rows[0]["module"] == "s4"


# ------------------------------------------------------------------ statistics
def test_precision_item_bootstrap():
    items = ["a"] * 4 + ["b"] * 4
    truth = [True, True, True, True, False, False, False, False]
    r = ST.precision_item_bootstrap(items, truth, n_boot=500, seed=0)
    assert r["precision"] == 0.5 and r["n_items"] == 2 and r["n_claims"] == 8
    assert r["lo"] == 0.0 and r["hi"] == 1.0                       # two items: resamples are {aa, ab, bb}
    r2 = ST.precision_item_bootstrap(["a", "a", "b"], [True, None, True], n_boot=10, seed=0)
    assert r2["precision"] == 1.0 and r2["n_claims"] == 2 and r2["lo"] == r2["hi"] == 1.0
    assert ST.precision_item_bootstrap([], [], 10, 0)["precision"] is None
    assert ST.precision_item_bootstrap(items, truth, 200, 1) == ST.precision_item_bootstrap(items, truth, 200, 1)


def test_cohen_kappa_known_values():
    assert ST.cohen_kappa(["a", "b", "a"], ["a", "b", "a"])["kappa"] == 1.0
    # classic 2x2: 20 agree yes, 15 agree no, 5 + 10 disagree -> po = .70, pe = .50, kappa = .40
    a = ["y"] * 25 + ["n"] * 25
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    assert abs(ST.cohen_kappa(a, b)["kappa"] - 0.4) < 1e-9
    assert ST.cohen_kappa(["a", None], ["a", "b"])["n"] == 1
    assert ST.cohen_kappa([], [])["kappa"] is None
    lo, hi = ST.kappa_bootstrap(a, b, 200, 0)
    assert lo <= 0.4 <= hi
    p, lo, hi = ST.wilson(0, 10)
    assert p == 0 and lo == 0 and 0.2 < hi < 0.35


# ------------------------------------------------------------------ W3 summary + kappa section
def _claim(gen, reader, item, label, k, module="g1", fam="ownership"):
    return {"claim_id": f"{gen}#{k}", "gen_id": gen, "module": module, "reader": reader, "item_id": item, "family": fam,
            "sample_idx": 0, "claim_idx": k, "claim_text": f"c{k}", "judge_label": label, "claim_type": J.label_type(label),
            "truth": J.label_truth(label), "judge_model": "m", "prompt_text": "p", "answer": "Jonas",
            "actual_answer": "Jonas", "candidates": ["Jonas", "Elif"]}


def test_w3_summarise_and_crosstab():
    claims = [_claim("o1", "Oracle", "i1", "computation_true", 0), _claim("o1", "Oracle", "i1", "input_false", 1),
              _claim("o2", "Oracle", "i2", "computation_false", 0), _claim("o2", "Oracle", "i2", "unverifiable", 1),
              _claim("n1", "NLA", "i1", "input_true", 0)]
    rule = {"o1": True, "o2": False, "n1": True}
    s = W3.summarise(claims, rule, n_boot=50)
    o = s["readers"]["Oracle"]
    assert o["n_readouts"] == 2 and o["n_claims"] == 4 and o["claims_per_readout"] == 2.0
    assert o["share"]["computation"] == 0.5 and o["precision"]["computation"]["precision"] == 0.5
    assert o["precision"]["input"]["precision"] == 0.0 and o["precision"]["all"]["n_claims"] == 3
    assert o["readout_level"]["any_false"]["k"] == 2
    assert o["crosstab_rule_v1"]["rule_supports"]["computation_precision"]["precision"] == 1.0
    assert o["crosstab_rule_v1"]["rule_other"]["readouts_with_any_computation_false"] == 1
    assert s["readers"]["NLA"]["precision"]["computation"]["precision"] is None
    md = W3.render_md(s, None, None, "t", ["note"])
    assert "| Oracle | 2 | 2 | 4 | 2.0 |" in md and "- note" in md


def test_w3_kappa_section():
    rel = [{"claim_id": f"g#{i}", "gen_id": "g", "reader": "Oracle", "item_id": "i", "claim_text": "c",
            "judge1_model": "m1", "judge1_label": a, "judge2_model": "m2", "judge2_label": b}
           for i, (a, b) in enumerate([("computation_true", "computation_true")] * 6
                                      + [("computation_false", "computation_false")] * 6
                                      + [("computation_false", "input_false")] * 2)]
    k = W3.kappa_section(rel, n_boot=50)
    assert k["n_claims"] == 14 and k["n_both_computation"] == 12
    assert k["kappa_truth_both_computation"]["kappa"] == 1.0 and 0 < k["kappa_5way"]["kappa"] < 1
    assert k["confusion"]["computation_false->input_false"] == 2


# ------------------------------------------------------------------ V4 sheet + human kappa
def test_human_sheet_stratification(tmp_path):
    claims = []
    n_per = {("Oracle", "input", True): 5, ("Oracle", "input", False): 50, ("Oracle", "computation", True): 50,
             ("Oracle", "computation", False): 50, ("NLA", "input", True): 50, ("NLA", "input", False): 50,
             ("NLA", "computation", True): 50, ("NLA", "computation", False): 50}
    for (reader, t, v), n in n_per.items():
        lab = f"{t}_{'true' if v else 'false'}"
        for i in range(n):
            claims.append(_claim(f"{reader}-{t}-{v}-{i}", reader, f"item{i % 7}", lab, 0))
    claims.append(_claim("u", "NLA", "x", "unverifiable", 0))          # excluded from the sheet
    rows, counts = HS.build_rows(claims, 300, 0)
    assert len(rows) == 300 and list(rows[0].keys()) == HS.COLUMNS
    by = {}
    for r in rows:
        by[(r["reader"], r["claim_type"], r["judge_label"].endswith("_true"))] = by.get(
            (r["reader"], r["claim_type"], r["judge_label"].endswith("_true")), 0) + 1
    assert by[("Oracle", "input", True)] == 5                            # short stratum fully taken
    assert all(v >= 42 for k, v in by.items() if k != ("Oracle", "input", True))  # slack redistributed
    assert all(r["human_label"] == "" and r["notes"] == "" for r in rows)
    assert len({r["claim_id"] for r in rows}) == 300
    assert HS.build_rows(claims, 300, 0)[0] == rows                      # deterministic
    small, _ = HS.build_rows(claims[:10], 300, 0)
    assert len(small) == 10
    out = tmp_path / "h.csv"
    HS.write_csv(out, rows)
    with out.open(newline="") as fh:
        back = list(csv.DictReader(fh))
    assert len(back) == 300 and back[0]["model_answer_or_key"].startswith("model answer: 'Jonas'")


def test_human_kappa_scoring():
    rows = [{"claim_id": str(i), "reader": "Oracle" if i < 6 else "NLA", "item_id": f"i{i % 3}",
             "claim_type": "computation" if i % 2 else "input", "judge_label": j, "human_label": h}
            for i, (j, h) in enumerate([("input_true", "true"), ("computation_true", "T"), ("input_false", "0"),
                                        ("computation_false", "FALSE"), ("input_true", "computation_true"),
                                        ("computation_false", "true"), ("input_true", ""), ("computation_true", "u"),
                                        ("input_false", "false"), ("computation_false", "f")])]
    res = K.score(rows, n_boot=50)
    assert res["n_labelled"] == 9 and res["type_disagreements"] == 1
    assert 0 < res["overall"]["kappa"] < 1 and res["overall"]["lo"] <= res["overall"]["kappa"] <= res["overall"]["hi"]
    assert res["precision_human_subset"]["Oracle"]["input"]["human"]["precision"] == 2 / 3
    assert K.parse_human("INPUT_FALSE") == "false" and K.parse_human("maybe") is None
    assert "judge–human kappa" in K.render(res)
