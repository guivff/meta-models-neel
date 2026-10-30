"""Offline fixture tests for r_bench/external.py (BRIEF_RX.md): every builder on a hand-written fixture of its source's
raw format, the counterbalancing and schema invariants, split disjointness and seed determinism of the assembled
bank, the clean skip of an unavailable source, and (when dataset/items_rx.json exists on disk) the committed bank's
invariants. No network: the fetchers are never called except through a monkeypatched stub.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_external.py -q``
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.r_bench import external as X  # noqa: E402

RNG = lambda: np.random.default_rng(0)  # noqa: E731


# ------------------------------------------------------------------ fixtures (the sources' raw formats)
PERSONAS = [
    {"id": "p_0", "variant": "base", "name": "Ahmed Hassan", "country": "Egypt", "favorite_food": "Koshari", "favorite_drink": "Mint tea",
     "favorite_music_genre": "Arabic pop", "favorite_sport": "Football", "favorite_boardgame": "Backgammon"},
    {"id": "p_1", "variant": "base", "name": "Maria Silva", "country": "Brazil", "favorite_food": "Feijoada", "favorite_drink": "Caipirinha",
     "favorite_music_genre": "Samba", "favorite_sport": "Volleyball", "favorite_boardgame": "Dominoes"},
    {"id": "p_2", "variant": "base", "name": "Hiroshi Tanaka", "country": "Japan", "favorite_food": "Ramen", "favorite_drink": "Green tea",
     "favorite_music_genre": "J-pop", "favorite_sport": "Baseball", "favorite_boardgame": "Go"},
    {"id": "p_3", "variant": "base", "name": "Astrid Larsen", "country": "Norway", "favorite_food": "Salmon", "favorite_drink": "Coffee",
     "favorite_music_genre": "Black metal", "favorite_sport": "Skiing", "favorite_boardgame": "Chess"},
]
TENSE = [{"sentence": "She will start a platform.", "label": "future"}, {"sentence": "He has been working.", "label": "present"},
         {"sentence": "We were exploring the ruins.", "label": "past"}, {"sentence": "The robot will perform chores.", "label": "future"},
         {"sentence": "They built a boat.", "label": "past"}, {"sentence": "It rained all night.", "label": "past"},
         {"sentence": "I will call you tomorrow.", "label": "future"}]
SINGPLUR = [{"sentence": "Andy Garcia is an actor.", "n_subjects": "single"}, {"sentence": "Andy and Gabrielle went to a party.", "n_subjects": "multiple"},
            {"sentence": "The chef prepared dinner.", "n_subjects": "single"}, {"sentence": "The players competed today.", "n_subjects": "multiple"},
            {"sentence": "The cleaners finished work.", "n_subjects": "multiple"}, {"sentence": "My aunt sings.", "n_subjects": "single"}]
GOT = [{"statement": "The city of Krasnodar is in Russia.", "label": "1", "city": "Krasnodar", "country": "Russia", "correct_country": "Russia"},
       {"statement": "The city of Krasnodar is in South Africa.", "label": "0", "city": "Krasnodar", "country": "South Africa", "correct_country": "Russia"},
       {"statement": "The city of Lodz is in Poland.", "label": "1", "city": "Lodz", "country": "Poland", "correct_country": "Poland"},
       {"statement": "The city of Lodz is in Chile.", "label": "0", "city": "Lodz", "country": "Chile", "correct_country": "Poland"},
       {"statement": "The city of Lodz is in Poland.", "label": "1", "city": "Lodz", "country": "Poland", "correct_country": "Poland"}]  # duplicate
AM = [{"statement": "Praia is a name of a country.", "label": 0}, {"statement": "Thimphu is a name of a city.", "label": 1},
      {"statement": "Burma is a name of a country.", "label": 1}, {"statement": "Yaren is a name of a country.", "label": 0}]
WORDS = ["flawed", "orthodox", "true", "daily", "valid", "happy", "cold", "fast", "big", "old", "wet", "loud", "rich", "soft"]
ANTONYM = [{"input": w, "output": f"un{w}"} for w in WORDS]
SYNONYM = [{"input": w, "output": f"{w}ish"} for w in WORDS]
ANTONYM_LEAKY = ANTONYM + [{"input": "antonym", "output": "synonym"}]
NAMES = ["Michael", "James", "John", "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth"]
COUNTRIES = [("Afghanistan", "Kabul"), ("France", "Paris"), ("Mexico", "Mexico City"), ("Singapore", "Singapore"), ("Japan", "Tokyo"),
             ("Peru", "Lima"), ("Kenya", "Nairobi"), ("Kuwait", "Kuwait City"), ("Egypt", "Cairo"), ("Norway", "Oslo")]
OBJECTS = ["book", "car", "paper", "letter", "box", "key", "cup", "hat", "coat", "clock", "lamp", "phone", "pen", "bag", "map",
           "coin", "ring", "shoe", "ball", "disk", "fan", "note", "file", "plane", "boat", "cake", "cream", "guitar", "rock", "tape"]
WSB_MULTIHOP = [
    {"name": "atomic-26-symbol", "prompt": "Fact: The chemical symbol for the element with atomic number 26 is ", "target": "Fe", "intermediates": ["iron"]},
    {"name": "atomic-79-symbol", "prompt": "Fact: The chemical symbol for the element with atomic number 79 is ", "target": "Au", "intermediates": ["gold"]},
    {"name": "birthstone-emerald", "prompt": "Fact: Emerald is the birthstone for month number ", "target": "5", "intermediates": ["May"]},
    {"name": "kilts-capital", "prompt": "Fact: The capital of the country famous for kilts is", "target": "Edinburgh", "intermediates": ["Scotland"]},
]
WSB_WRONG = [
    {"name": "wb-1", "prompt": "Fact: The composer of Piano Sonata No. 18 was born in the city of", "target": "Bonn", "correct_answer": "Salzburg",
     "intermediates": ["Ludwig van Beethoven"], "intermediates_aliases": ["Beethoven"], "true_intermediates": ["Wolfgang Amadeus Mozart"]},
    {"name": "wb-2", "prompt": "Fact: The painter of The Musicians died in the city of", "target": "Antwerp", "correct_answer": "Porto Ercole",
     "intermediates": ["Peter Paul Rubens"], "true_intermediates": ["Caravaggio"]},
    {"name": "wb-same", "prompt": "Fact: x", "target": "a", "correct_answer": "a", "intermediates": ["Same"], "true_intermediates": ["Same"]},
]
WSB_BASIC = [
    {"name": "br-1", "subfamily": "entity", "prompt": "The athlete Muhammad Ali plays the sport of", "target": "boxing", "intermediates": ["boxing"],
     "units": [{"role": "readout", "match": ["Boxing", "boxing"]}]},
    {"name": "br-2", "subfamily": "entity", "prompt": "The musician Jimi Hendrix is famous for playing the", "target": "guitar", "intermediates": ["Guitar"]},
    {"name": "br-3", "subfamily": "computed", "prompt": "The month after April is", "target": "May", "intermediates": ["May"]},
    {"name": "br-4", "subfamily": "computed", "prompt": "Seven plus five is", "target": "12", "intermediates": ["twelve"]},
    {"name": "br-5", "subfamily": "entity", "prompt": "The capital of Kenya is", "target": "Nairobi", "intermediates": ["Nairobi"]},
]
WSB_DM = [
    {"name": "dm-1", "subfamily": "pair", "concept": "clavicle", "prompt": "Think about the body part clavicle while you write. Now write: \"Hi.\"",
     "units": [{"role": "concept", "match": ["clavicle"]}]},
    {"name": "dm-2", "subfamily": "pair", "concept": "zephyr", "prompt": "The secret word is \"zephyr\". Now write: \"Hi.\""},
    {"name": "dm-3", "subfamily": "pair", "concept": "turret", "prompt": "The secret word is \"turret\". Now write: \"Hi.\""},
]


def raw_fixture() -> dict[str, dict]:
    return {
        "ao": {"personas_base": PERSONAS, "personas_fantasy": PERSONAS, "tense": TENSE, "singular_plural": SINGPLUR, "files": {}},
        "got": {"x05_got_cities": GOT, "x06_got_sp_en_trans": GOT, "x07_got_larger_than": GOT, "files": {}},
        "am": {ds: AM for ds in X.AM_TOPICS} | {"files": {}},
        "fv": {t: (ANTONYM if i % 2 == 0 else SYNONYM) for pair in X.FV_PAIRS.values() for i, t in enumerate(pair)} | {"files": {}},
        "feng": {"names": NAMES, "countries": COUNTRIES, "files": {}},
        "boxes": {"objects": OBJECTS, "files": {}},
        "wsb": {"x22_wsb_association": WSB_MULTIHOP, "x23_wsb_basic_readout": WSB_BASIC, "x24_wsb_multihop": WSB_MULTIHOP,
                "x25_wsb_wrong_bridge": WSB_WRONG, "x26_wsb_multilingual": WSB_MULTIHOP, "x27_wsb_poetry": WSB_MULTIHOP,
                "x28_wsb_typo": WSB_MULTIHOP, "x29_wsb_directed_modulation": WSB_DM, "commit": "deadbeef", "files": {}},
    }


# ------------------------------------------------------------------ spec
def test_spec_check_and_ids():
    assert X.spec_check() == []
    assert len(X.SPECS) == 29
    assert all(s.source in X.SOURCES for s in X.SPECS.values())
    assert Counter(s.tag for s in X.SPECS.values())["HOME"] == 8
    assert "HOME" in X.TAGS_X and "jakkli" in X.FETCHERS


def test_jlens_form_rule():
    assert X.jlens_form("the antonym") == "antonym"
    assert X.jlens_form("Washington D.C.") == "Washington"
    assert X.jlens_form("a single subject") == "single"
    assert X.jlens_form("  ") is None
    assert X.jlens_pair("Green tea", "Mint tea") == ["Green", "Mint"]
    assert X.jlens_pair("the tea", "Tea") == [None, None]   # collision -> both unscorable


# ------------------------------------------------------------------ builders
def _assert_item_level(recs, n_expected=None):
    assert recs and all(set(r) >= {"text", "answer", "foil", "label", "candidates", "raw_target"} for r in recs)
    ys = [r["label"] for r in recs]
    assert abs(sum(ys) - len(ys) / 2) <= 0.5, "counterbalanced"
    for r in recs:
        assert r["answer"].lower() != r["foil"].lower()
        assert r["candidates"] == ([r["answer"], r["foil"]] if r["label"] == 1 else [r["foil"], r["answer"]])
    assert len({(r.get("system") or "") + r["text"] for r in recs}) == len(recs), "unique texts"
    if n_expected is not None:
        assert len(recs) == n_expected


def test_personaqa_builder():
    recs = X.build_personaqa(PERSONAS, RNG())
    _assert_item_level(recs, 4 * 5)
    for r in recs:
        assert r["system"].startswith("Here is what you know about")
        assert r["answer"] in r["system"] and r["answer"].lower() not in r["text"].lower()
        assert r["foil"].lower() not in r["system"].lower(), "foil is another persona's value"
        assert r["extra"]["question"] == r["text"]


def test_ao_classification_builders():
    t = X.build_ao_tense(TENSE, RNG())
    assert len(t) == 6 and {r["raw_target"] for r in t} == {"past", "future"}
    assert all(r["label"] == int(r["raw_target"] == "past") for r in t)
    s = X.build_ao_singular_plural(SINGPLUR, RNG())
    assert len(s) == 6 and sum(r["label"] for r in s) == 3


def test_got_and_am_builders():
    g = X.build_got(GOT, RNG())
    assert len(g) == 4, "duplicate statement dropped"
    assert [r["label"] for r in g] == [1, 0, 1, 0] and g[0]["extra"]["correct_country"] == "Russia"
    a = X.build_am(AM, RNG())
    assert [r["label"] for r in a] == [0, 1, 1, 0] and all(r["raw_target"] in ("0", "1") for r in a)


def test_fv_pair_builder():
    spec = X.SPECS["x14_fv_antonym_synonym"]
    recs = X.build_fv_pair(ANTONYM, SYNONYM, spec, RNG(), per_task=10, shots=3)
    assert len(recs) == 20 and sum(r["label"] for r in recs) == 10
    for r in recs:
        assert r["text"].count("Q:") == 4 and r["text"].endswith("A:")
        assert "antonym" not in r["text"].lower() and "synonym" not in r["text"].lower()
        assert r["extra"]["expected"] and r["extra"]["query"] in r["text"]
        assert r["raw_target"] == (spec.pos if r["label"] == 1 else spec.neg)
        rp = r["read_position"]
        assert rp["kind"] == "char_span" and rp["role"] == "separator" and rp["fallback"] == "last_text_token"
        assert r["text"][rp["char_start"]:rp["char_end"]] == rp["text"] == X.FV_SEPARATOR
        assert rp["char_end"] == len(r["text"]), "the separator is the final text token"
    with pytest.raises(ValueError):
        X.separator_position("no separator here")
    leaky = X.build_fv_pair(ANTONYM_LEAKY, SYNONYM, spec, RNG(), per_task=10, shots=3)
    assert all("antonym" not in r["text"].lower() for r in leaky), "prompts containing a candidate word are dropped"


def test_feng_builder_capital_absent_from_text():
    recs = X.build_feng_capitals(NAMES, COUNTRIES, RNG(), n=40)
    _assert_item_level(recs, 40)
    kept = {c for _, c in X._clean_countries(COUNTRIES)}
    assert "Mexico City" not in kept and "Singapore" not in kept and "Kuwait City" not in kept and "Paris" in kept
    for r in recs:
        assert r["answer"].lower() not in r["text"].lower() and r["foil"].lower() not in r["text"].lower()
        assert r["extra"]["country"] in r["text"] and r["extra"]["question"] in r["text"]
        assert r["text"].startswith(X.FENG_TEMPLATE[:40])


def _simulate(text: str) -> list[list[str]]:
    """Replay a boxes prompt to recover the final state (independent re-implementation for the test)."""
    desc, ops = text.split(". ", 1)
    state = []
    for part in desc.split(", "):
        m = re.match(r"Box (\d+) contains (.*)", part)
        body = m.group(2)
        state.append([] if body == "nothing" else [o[4:] for o in body.split(" and ")])
    for op in re.findall(r"(Move the \w+ from Box \d+ to Box \d+|Put the \w+ into Box \d+|Remove the \w+ from Box \d+)\.", ops):
        if op.startswith("Move"):
            o, i, j = re.match(r"Move the (\w+) from Box (\d+) to Box (\d+)", op).groups()
            state[int(i)].remove(o); state[int(j)].append(o)
        elif op.startswith("Put"):
            o, j = re.match(r"Put the (\w+) into Box (\d+)", op).groups()
            state[int(j)].append(o)
        else:
            o, i = re.match(r"Remove the (\w+) from Box (\d+)", op).groups()
            state[int(i)].remove(o)
    return state


def test_boxes_builder_tracking_required():
    recs = X.build_boxes(OBJECTS, RNG(), n=60)
    _assert_item_level(recs, 60)
    for r in recs:
        q = r["extra"]["box"]
        assert r["text"].endswith(f" Box {q} contains") and 1 <= r["extra"]["numops"] <= 3
        final = _simulate(r["text"])
        assert final[q] == [r["raw_target"]], "the queried box holds exactly the answer at the end"
        assert r["foil"][4:] in {o for j, s in enumerate(final) if j != q for o in s}
        init_q = re.search(rf"Box {q} contains ([^,.]*)", r["text"]).group(1)
        assert init_q != f"the {r['raw_target']}", "content changed under the operations"


def test_wsb_builders():
    mh = X.build_wsb(WSB_MULTIHOP, "multihop", RNG())
    _assert_item_level(mh, 4)
    assert {r["answer"] for r in mh} == {"iron", "gold", "May", "Scotland"}
    for r in mh:
        assert r["foil"] in {"iron", "gold", "May", "Scotland"} and r["extra"]["target"]
    wb = X.build_wsb(WSB_WRONG, "wrong_bridge", RNG())
    assert len(wb) == 2, "item whose wrong bridge equals the true bridge is dropped"
    assert {(r["answer"], r["foil"]) for r in wb} == {("Ludwig van Beethoven", "Wolfgang Amadeus Mozart"), ("Peter Paul Rubens", "Caravaggio")}
    br = X.build_wsb(WSB_BASIC, "basic_readout", RNG())
    sub = {it["name"]: it["subfamily"] for it in WSB_BASIC}
    tgt = {X.wsb_target(it, "basic_readout"): it["subfamily"] for it in WSB_BASIC}
    for r in br:
        assert tgt[r["foil"]] == sub[r["source_id"]], "foil from the same subfamily"
        assert r["foil"].lower() not in r["text"].lower()
    dm = X.build_wsb(WSB_DM, "directed_modulation", RNG())
    assert {r["answer"] for r in dm} == {"clavicle", "zephyr", "turret"}


# ------------------------------------------------------------------ assembled bank
def test_build_all_schema_splits_determinism(tmp_path):
    raws = raw_fixture()
    items, per = X.build_all(raws, n_test=8, n_pool=8)
    assert set(per) == set(X.SPECS), "every dataset builds from the fixture"
    for it in items:
        assert set(it) == {"item_id", "dataset", "tag", "split", "label", "raw_target", "prompt_text", "render", "system",
                           "source", "source_id", "extra", "primary", "read_position"}
        assert (it["read_position"] is not None) == (it["source"] == "fv"), "only the ICL items name a read position"
        p = it["primary"]
        assert set(p) == {"name", "question", "candidates", "answer", "template", "sided", "jlens"}
        assert len(p["candidates"]) == 2 and p["candidates"][0] != p["candidates"][1]
        assert p["answer"] == p["candidates"][0 if it["label"] == 1 else 1]
        assert "{X}" in p["template"] and p["question"].endswith("?") and p["sided"] == "two"
        assert it["item_id"].startswith(f"rx-{it['dataset']}-{it['split']}-") and it["tag"] in X.TAGS_X
        assert (it["system"] is not None) == (it["tag"] == "CONTEXT")
    for ds in per:
        its = [it for it in items if it["dataset"] == ds]
        for split in ("test", "pool"):
            s = [it for it in its if it["split"] == split]
            if s:
                assert sum(it["label"] for it in s) * 2 == len(s), f"{ds} {split} balanced"
        test_t = {it["prompt_text"] for it in its if it["split"] == "test"}
        pool_t = {it["prompt_text"] for it in its if it["split"] == "pool"}
        assert not (test_t & pool_t), f"{ds}: test/pool overlap"
        assert per[ds]["item_level"] == X.SPECS[ds].item_level
    items2, _ = X.build_all(raw_fixture(), n_test=8, n_pool=8)
    assert json.dumps(items, sort_keys=True) == json.dumps(items2, sort_keys=True), "deterministic under the seed"
    items3, _ = X.build_all(raw_fixture(), seed=X.SEED + 1, n_test=8, n_pool=8)
    assert json.dumps(items, sort_keys=True) != json.dumps(items3, sort_keys=True)


def test_build_records_unavailable_source_is_skipped(monkeypatch, tmp_path):
    fetched = raw_fixture()

    def ok(name):
        return lambda: fetched[name]

    def boom():
        raise X.SourceUnavailable("fixture: cannot fetch")

    monkeypatch.setattr(X, "FETCHERS", {**{k: ok(k) for k in fetched}, "jakkli": boom, "got": boom})
    monkeypatch.setattr(X.C, "sha256_file", lambda p: "0" * 64)
    out = X.build(tmp_path / "items_rx.json", n_test=8, n_pool=8)
    d = json.loads(out.read_text())
    m = d["meta"]
    assert m["sources"]["jakkli"]["status"] == "skipped" and "cannot fetch" in m["skipped_sources"]["got"]
    assert set(m["skipped_sources"]) == {"jakkli", "got"}
    assert not any(it["source"] == "got" for it in d["items"]) and any(it["source"] == "fv" for it in d["items"])
    assert m["n_datasets"] == len(X.SPECS) - 3 and m["frozen"] is False and len(m["sha256_items"]) == 64
    assert set(m["spec"]) == set(m["datasets"]) and m["sources"]["wsb"]["commit"] == "deadbeef"


def test_get_file_offline_raises(tmp_path):
    with pytest.raises(X.SourceUnavailable):
        X.get_file("https://example.invalid/x.csv", tmp_path / "x.csv", offline=True)
    (tmp_path / "y.csv").write_text("a,b\n1,2\n")
    assert X.get_file("https://example.invalid/y.csv", tmp_path / "y.csv", offline=True) == tmp_path / "y.csv"


# ------------------------------------------------------------------ the committed bank (if present)
@pytest.mark.skipif(not X.ITEMS_RX.exists(), reason="dataset/items_rx.json not built")
def test_committed_bank_invariants():
    d = json.loads(X.ITEMS_RX.read_text(encoding="utf-8"))
    m, items = d["meta"], d["items"]
    assert m["n_items"] == len(items) and m["seed"] == X.SEED and m["frozen"] is False
    assert m["sources"]["jakkli"]["status"] == "skipped"
    per = Counter(it["dataset"] for it in items)
    assert set(per) == set(m["datasets"]) and len(per) == m["n_datasets"]
    for ds, n in per.items():
        its = [it for it in items if it["dataset"] == ds]
        test = [it for it in its if it["split"] == "test"]
        pool = [it for it in its if it["split"] == "pool"]
        assert len(test) <= X.N_TEST and len(pool) <= X.N_POOL
        assert sum(it["label"] for it in test) * 2 == len(test)
        assert not ({it["prompt_text"] for it in test} & {it["prompt_text"] for it in pool})
        assert len({it["item_id"] for it in its}) == n
        spec = X.SPECS[ds]
        if not spec.item_level:
            assert all(it["primary"]["candidates"] == [spec.pos, spec.neg] for it in its)
        if spec.source in ("feng",):
            assert all(it["primary"]["answer"].lower() not in it["prompt_text"].lower() for it in its)
        if spec.tag == "CONTEXT":
            assert all(it["system"] and it["primary"]["answer"] in it["system"] for it in its)
        if spec.source == "fv":
            assert m["datasets"][ds]["read_position"] == "char_span:separator"
            for it in its:
                rp = it["read_position"]
                assert it["prompt_text"][rp["char_start"]:rp["char_end"]] == "A:" and rp["char_end"] == len(it["prompt_text"])
        else:
            assert all(it["read_position"] is None for it in its)
    assert m["sha256_items"] == X.hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
