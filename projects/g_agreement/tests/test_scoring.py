"""Offline tests for core/scoring.py on synthetic MOCK readouts. Never writes under results/."""
from __future__ import annotations

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)

from projects.g_agreement.core import scoring as S  # noqa: E402
from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402


@pytest.fixture(scope="module")
def items():
    return {it["item_id"]: it for it in bd.build(bd.DEFAULT_SEED)["items"]}


def st(items, iid, text, method="olens"):
    c = S.extract_claims(text, items[iid], method)
    return c["primary"]["status"], c["primary"]["value"], c["relation"]["status"]


# ------------------------------------------------------------------ language
@pytest.mark.parametrize("text,exp", [
    ("The user wants the reply in French.", ("supports", "French")),
    ("Le ciel est bleu.", ("supports", "French")),
    ("Answer in German: blau.", ("contradicts", "German")),
    ("French or German, hard to say.", ("unclear", None)),
    ("Not German but French.", ("supports", "French")),
    ("bleu in French, not blau in German", ("supports", "French")),  # J1: negated name -> 1 hit is not enough
    ("Not German. Der Himmel ist blau und nicht grau.", ("contradicts", "German")),  # J1: >= 2 hits survive
    ("A colour question about the sky.", ("unclear", None)),
])
def test_language_text(items, text, exp):
    assert st(items, "lang-01A", text)[:2] == exp


def test_detect_language_shared_words_give_no_evidence():
    lab, hits = S.detect_language("la", ["French", "Spanish"])
    assert lab is None and hits == {"French": [], "Spanish": []}
    assert S.detect_language("Frío.", ["Spanish", "Italian"])[0] == "Spanish"
    assert S.detect_language("The sky is blue.", ["French", "German"])[0] is None  # English only


# ------------------------------------------------------------------ tense
@pytest.mark.parametrize("text,exp", [
    ("a sentence about yesterday at the park", ("supports", "past")),
    ("The user asked what Sam will do tomorrow.", ("contradicts", "future")),
    ("Sam went to the park and played football.", ("supports", "past")),
    ("The model will answer about Sam at the park.", ("unclear", None)),
    ("Sam will play at the park.", ("contradicts", "future")),
    ("The user asked for a sentence about Sam at the park.", ("unclear", None)),
    ("Sam was at the park and will return tomorrow.", ("contradicts", "future")),  # J2
    ("It is about the past and also about the future.", ("self_contradictory", None)),
])
def test_tense_text(items, text, exp):
    assert st(items, "tense-01A", text)[:2] == exp


@pytest.mark.parametrize("text,exp", [
    ("Sam played football at the park.", "past"),
    ("Sam went to the park.", "past"),
    ("Sam will walk the dog tomorrow.", "future"),
    ("Sam is going to bake bread.", "future"),
    ("Yesterday Sam said he will go.", "mixed"),
    ("Sam likes the park.", None),
    ("The red bed.", None),
])
def test_detect_tense(text, exp):
    assert S.detect_tense(text)[0] == exp


# ------------------------------------------------------------------ ownership (own-01A: Mira red key, Leo blue key)
@pytest.mark.parametrize("text,exp", [
    ("Mira has the red key and Leo has the blue key.", ("supports", "Mira", "correct")),
    ("Leo has the red key.", ("contradicts", "Leo", "wrong")),
    ("Mira, Leo, red key, blue key.", ("unclear", None, "unbound")),
    ("The answer is Mira.", ("supports", "Mira", "absent")),
    ("Mira", ("supports", "Mira", "absent")),
    ("Leo holds the blue key; the red key is Mira's.", ("supports", "Mira", "correct")),
    ("Mira has the red key. Leo has the red key too.", ("self_contradictory", None, "wrong")),
    ("Leo has the blue key.", ("unclear", None, "absent")),  # J3: no elimination
    ("Someone has a key.", ("unclear", None, "absent")),
])
def test_ownership_text(items, text, exp):
    assert st(items, "own-01A", text) == exp


def test_ownership_entities_and_objects(items):
    c = S.extract_claims("Mira has the red key and Leo has the blue key.", items["own-01A"], "nla")
    assert c["entities_mentioned"] == ["Mira", "Leo"]
    assert c["objects_mentioned"] == ["red key", "blue key"]


# ------------------------------------------------------------------ mapping (map-01B: A->B, B->C, D->A; answer C)
@pytest.mark.parametrize("text,exp", [
    ("A → B. B → C. D → A. Starting from A you reach C.", ("supports", "C", "correct")),
    ("B -> C", ("unclear", None, "correct")),  # J4: hop-2 recitation drives relation only
    ("B -> D", ("unclear", None, "wrong")),  # J4
    ("The symbols A, B, C and D with arrows.", ("unclear", None, "unbound")),
    ("The answer is C.", ("supports", "C", "absent")),
    ("From A, after two steps you end up at D.", ("contradicts", "D", "absent")),
    ("D → A", ("unclear", None, "absent")),  # distractor is direction-aware
    ("a cat and a dog", ("unclear", None, "absent")),
])
def test_mapping_text(items, text, exp):
    assert st(items, "map-01B", text) == exp


def test_mapping_intermediate_switch(items, monkeypatch):
    assert S.MAPPING_INTERMEDIATE_COUNTS_AS_PRIMARY is False
    assert st(items, "map-01B", "A -> B -> C")[:2] == ("supports", "C")
    assert st(items, "map-01B", "B -> D") == ("unclear", None, "wrong")
    monkeypatch.setattr(S, "MAPPING_INTERMEDIATE_COUNTS_AS_PRIMARY", True)
    assert st(items, "map-01B", "B -> C") == ("supports", "C", "correct")


def test_mapping_words(items):
    assert st(items, "map-03A", "fox maps to owl, owl maps to bear, so you land on bear.") == ("supports", "bear", "correct")
    assert st(items, "map-03A", "wolf maps to fox")[:2] == ("unclear", None)


# ------------------------------------------------------------------ J-lens token lists
@pytest.mark.parametrize("iid,toks,exp", [
    ("lang-01A", ["Ġfrench", "Ġsky", "blue"], ("supports", "French")),
    ("lang-01A", ["ĠGerman", "Ġfrench"], ("self_contradictory", None)),
    ("lang-01A", ["Ġsky"], ("unclear", None)),
    ("lang-01A", ["ĠFranç"], ("supports", "French")),
    ("tense-01A", ["Ġyesterday", "Ġpark"], ("supports", "past")),
    ("tense-01B", ["Ġwill", "Ġtomorrow"], ("supports", "future")),
    ("own-01A", ["ĠMira", "Ġkey"], ("supports", "Mira")),
    ("own-03B", ["ĠKen", "Ġticket"], ("unclear", None)),       # prefix < 4 chars
    ("own-03B", ["ĠKenj"], ("supports", "Kenji")),
    ("map-01B", ["ĠC", "ĠD"], ("self_contradictory", None)),
    ("map-01B", ["Ġa", "Ġc"], ("unclear", None)),              # lower-case letters are not symbols
    ("map-01B", ["ĠC"], ("supports", "C")),
    ("map-05A", ["Ġtria"], ("contradicts", "triangle")),
])
def test_jlens_tokens(items, iid, toks, exp):
    assert st(items, iid, toks, "jlens")[:2] == exp


def test_jlens_accepts_json_string_and_ignores_rank_beyond_top10(items):
    assert st(items, "map-01B", '["ĠC", "x"]', "jlens")[:2] == ("supports", "C")
    assert st(items, "map-01B", ["x"] * 10 + ["ĠC"], "jlens")[:2] == ("unclear", None)
    c = S.extract_claims(["ĠC"], items["map-01B"], "jlens")
    assert c["relation"]["status"] == "absent"


# ------------------------------------------------------------------ gens, truncation, blind sheet, scoring
def _gen(gid, method, iid, text=None, tokens=None, finish="eos"):
    native = {"tokens": tokens, "scores": [0.0] * len(tokens)} if tokens is not None else (
        {"text": text} if method == "target" else {"samples": [text]})
    return {"gen_id": gid, "module": "mock", "method": method, "condition": "genuine", "item_id": iid,
            "state_item_id": iid, "sample_idx": 0, "seed": 1, "native": native, "raw_output": text or "",
            "finish_reason": finish}


def test_claim_from_gen_and_truncated(items):
    g = _gen("g1|nla|own-01A|s0", "nla", "own-01A", "Mira has the red key", finish="length")
    row = S.claim_from_gen(g, items["own-01A"])
    assert row["truncated"] is True and row["blind"] is True and row["extractor"] == "rule-v1"
    assert row["primary"]["status"] == "supports"
    assert set(row) == {"gen_id", "method", "item_id", "extractor", "primary", "entities_mentioned",
                        "objects_mentioned", "relation", "truncated", "blind"}


def test_blind_sheet_strips_and_shuffles(items, tmp_path):
    gens = [_gen(f"g|{i}", "olens", "own-01A", f"text {i}") for i in range(12)]
    gens.append(_gen("g|j", "jlens", "own-01A", tokens=["ĠMira"]))
    sheet = S.make_blind_sheet(gens, seed=3, module="mock", cache_dir=str(tmp_path))
    assert all(set(r) == {"sheet_id", "method", "text"} for r in sheet)
    assert all(len(r["sheet_id"]) == 12 for r in sheet)
    assert not any(r["sheet_id"] in {g["gen_id"] for g in gens} for r in sheet)
    assert S.make_blind_sheet(gens, seed=3, module="mock", cache_dir=str(tmp_path)) == sheet
    assert next(r for r in sheet if r["method"] == "jlens")["text"] == '["ĠMira"]'
    import json as _json
    m = _json.load(open(tmp_path / "sheet_map_mock.json"))["map"]
    assert sorted(m.values()) == sorted(g["gen_id"] for g in gens)
    assert all(m[r["sheet_id"]] for r in sheet)
    assert not os.path.exists(os.path.join(REPO, "results", "g_agreement", "sheet_map_mock.json"))
    assert os.path.exists(tmp_path / "sheet_salt.txt")  # default salt created on first use
    other = S.make_blind_sheet(gens, seed=3, module="mock", salt="different", cache_dir=str(tmp_path))
    assert {r["sheet_id"] for r in other} != {r["sheet_id"] for r in sheet}


def test_score_claims_separates_factual_and_target(items):
    claims = [
        S.claim_from_gen(_gen("a", "nla", "own-01A", "Mira has the red key"), items["own-01A"]),
        S.claim_from_gen(_gen("b", "nla", "own-01A", "Leo has the red key"), items["own-01A"]),
        S.claim_from_gen(_gen("c", "nla", "own-01A", "keys"), items["own-01A"]),
        S.claim_from_gen(_gen("d", "nla", "tense-01B", "about tomorrow"), items["tense-01B"]),
        S.claim_from_gen(_gen("e", "nla", "lang-01A", "written in French"), items["lang-01A"]),
    ]
    targets = [_gen("t1", "target", "own-01A", "Leo"),             # target wrong
               _gen("t2", "target", "tense-01B", "Sam will swim."),  # target right
               _gen("t3", "target", "lang-01A", "Blau.")]            # target answered in German
    rows = {r["gen_id"]: r for r in S.score_claims(claims, items, targets)}
    assert (rows["a"]["factual_correct"], rows["a"]["target_consistent"]) == (True, False)
    assert (rows["b"]["factual_correct"], rows["b"]["target_consistent"]) == (False, True)
    assert (rows["c"]["factual_correct"], rows["c"]["target_consistent"]) == (None, None)
    assert rows["a"]["target_correct"] is False and rows["a"]["target_value"] == "Leo"
    assert rows["d"]["factual_correct"] is True and rows["d"]["target_consistent"] is True
    assert rows["e"]["factual_correct"] is True and rows["e"]["target_value"] == "German"
    assert rows["e"]["target_consistent"] is False and rows["e"]["target_regex_match"] is False


def test_extract_target_answer(items):
    assert S.extract_target_answer("Bleu.", items["lang-01A"])[0] == "French"
    assert S.extract_target_answer("Mira", items["own-01A"])[0] == "Mira"
    assert S.extract_target_answer("Mira and Leo", items["own-01A"])[0] == "Mira"  # first word
    assert S.extract_target_answer("Both have keys.", items["own-01A"])[0] is None
    assert S.extract_target_answer("C", items["map-01B"])[0] == "C"
    assert S.extract_target_answer("Sam played.", items["tense-01A"])[0] == "past"


# ------------------------------------------------------------------ G6 choice family (rubric §10)
from projects.g_agreement.dataset import build_dataset_g6 as g6  # noqa: E402


@pytest.fixture(scope="module")
def citems():
    return {it["item_id"]: it for it in g6.build(g6.DEFAULT_SEED)["items"]}


def _cat_dog(citems):
    return next(it for it in citems.values() if set(it["primary"]["candidates"]) == {"cat", "dog"} and it["version"] == "A")


@pytest.mark.parametrize("text,exp", [
    ("The model will pick cat.", ("supports", "cat", True)),
    ("Answer: dog", ("supports", "dog", True)),
    ("cat or dog", ("unclear", None, False)),
    ("Not dog.", ("unclear", None, False)),
    ("It chooses cat, not dog.", ("supports", "cat", True)),
    ("cat and dog", ("self_contradictory", None, False)),
    ("a pet question", ("unclear", None, False)),
])
def test_choice_text_provisional(citems, text, exp):
    it = _cat_dog(citems)
    c = S.extract_claims(text, it, "olens")
    assert (c["primary"]["status"], c["primary"]["value"], c["primary"]["provisional"]) == exp
    assert c["relation"]["status"] == "absent"


def test_choice_jlens(citems):
    it = _cat_dog(citems)
    assert S.extract_claims(["Ġcat", "Ġpet"], it, "jlens")["primary"]["status"] == "supports"
    assert S.extract_claims(["Ġcat", "Ġdog"], it, "jlens")["primary"]["status"] == "self_contradictory"
    assert S.extract_claims(["Ġpet"], it, "jlens")["primary"]["status"] == "unclear"


def test_choice_target_answer(citems):
    it = _cat_dog(citems)
    assert S.extract_target_answer("cat", it)[0] == "cat"
    assert S.extract_target_answer("Dog.", it)[0] == "dog"
    assert S.extract_target_answer("cat, not dog", it)[0] == "cat"      # first word wins
    assert S.extract_target_answer("I like dog and cat", it)[0] is None  # both, neither first
    assert S.extract_target_answer("neither", it)[0] is None


def test_choice_score_claims_uses_target_as_key(citems):
    it = _cat_dog(citems)
    iid = it["item_id"]
    claims = [S.claim_from_gen(_gen("a", "nla", iid, "The model will pick cat."), it),
              S.claim_from_gen(_gen("b", "nla", iid, "Answer: dog"), it),
              S.claim_from_gen(_gen("c", "nla", iid, "cat or dog"), it)]
    rows = {r["gen_id"]: r for r in S.score_claims(claims, citems, [_gen("t", "target", iid, "cat")])}
    assert rows["a"]["status"] == "supports" and rows["a"]["factual_correct"] is True and rows["a"]["target_consistent"] is True
    assert rows["b"]["status"] == "contradicts" and rows["b"]["factual_correct"] is False and rows["b"]["target_consistent"] is False
    assert rows["c"]["factual_correct"] is None and rows["c"]["target_consistent"] is None
    assert rows["a"]["answer"] == "cat" and rows["a"]["target_value"] == "cat"
    # no target available -> nothing can be scored, status stays provisional supports
    rows2 = {r["gen_id"]: r for r in S.score_claims(claims, citems, None)}
    assert rows2["a"]["factual_correct"] is None and rows2["a"]["target_consistent"] is None
