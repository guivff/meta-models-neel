"""Offline tests for the R-E "beyond the text" bank (BRIEF_R.md §11, PLAN_R.md §5): r_bench/beyond_text.py invariants
(schema, balance, split disjointness, seed determinism), KHOP (bridge / demonym / aliases never in the text, candidates
distinct and counterbalanced per template, both facts share prompts), SYNTAX (4 cells balanced, head identity binding,
clause pairs matched on word count), COUNT (list length, column bins), INTERNAL (XSTest matched pairs, abstain balance,
the frozen behavioural-key classifiers, rekey_internal), the on-disk items_re.json == rebuild, and the collect.py flag.
Nothing is written under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_beyond.py -q``
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.r_bench import beyond_text as BT  # noqa: E402

HAS_WIKITEXT = BT.WIKITEXT_PARQUET.exists()
BINARY = {"re_khop2_bridge", "re_khop2_answer", "re_khop3_middle", "re_syntax_number", "re_syntax_head", "re_syntax_clauses",
          "re_internal_refuse", "re_internal_abstain"}
KWAY = {"re_count_listed", "re_count_long", "re_count_col"}
PER_ITEM = {"re_khop2_bridge", "re_khop2_answer", "re_khop3_middle", "re_syntax_head", "re_count_long"}


@pytest.fixture(scope="module")
def data():
    return BT.build(BT.SEED)


@pytest.fixture(scope="module")
def items(data):
    return data["items"]


@pytest.fixture(scope="module")
def by(items):
    return BT._by_dataset(items)


# ---------------------------------------------------------------- schema, ids, splits, determinism
def test_facts_present(by):
    expected = BINARY | (KWAY if HAS_WIKITEXT else KWAY - {"re_count_col"})
    assert set(by) == expected


def test_schema(items):
    for it in items:
        assert set(it) >= {"item_id", "dataset", "tag", "split", "label", "raw_target", "prompt_text", "render", "system", "primary", "construction", "read_position"}
        assert (it["read_position"] is not None) == (it["tag"] == "KHOP")
        assert bool(it["primary"].get("per_item_candidates")) == (it["dataset"] in PER_ITEM)
        assert it["tag"] in BT.TAGS_RE and it["split"] in ("test", "pool") and it["render"] == "chat" and it["system"] is None
        assert it["item_id"].startswith("re-") and it["dataset"].startswith("re_")
        p = it["primary"]
        assert set(p) >= {"name", "question", "candidates", "answer", "template", "sided", "key"} and p["name"] == it["dataset"]
        assert "{X}" in p["template"] and p["question"].endswith("?")
        assert p["answer"] in p["candidates"] and len(set(p["candidates"])) == len(p["candidates"])
        if p["sided"] == "two":
            assert len(p["candidates"]) == 2 and len(p["jlens"]) == 2
            assert it["label"] == int(p["answer"] == p["candidates"][0])
        else:
            assert p["sided"] == "kway" and p["k"] == len(p["candidates"]) and it["label"] == p["candidates"].index(p["answer"])
        assert it["prompt_text"] == it["prompt_text"].strip() and it["prompt_text"]


def test_ids_unique_and_texts_unique_within_dataset(items, by):
    assert len({it["item_id"] for it in items}) == len(items)
    for ds, its in by.items():
        assert len({it["prompt_text"] for it in its}) == len(its), ds


def test_splits_balanced_and_bounded(by):
    for ds, its in by.items():
        test = [it for it in its if it["split"] == "test"]
        pool = [it for it in its if it["split"] == "pool"]
        assert len(test) <= (240 if ds == "re_internal_refuse" else 200) and len(pool) <= 512, ds
        assert not ({it["prompt_text"] for it in test} & {it["prompt_text"] for it in pool}), ds
        for split in (test, pool):
            c = Counter(it["label"] for it in split)
            assert len(set(c.values())) <= 1, (ds, c)   # every class equally often (or the split is empty)
        if ds in BINARY:
            assert set(Counter(it["label"] for it in test)) == {0, 1}
        else:
            assert len(set(it["label"] for it in test)) == its[0]["primary"]["k"]


def test_sizes_as_preregistered(by):
    n = {ds: (sum(it["split"] == "test" for it in its), sum(it["split"] == "pool" for it in its)) for ds, its in by.items()}
    assert n["re_khop2_bridge"][0] == 200 and n["re_khop2_bridge"] == n["re_khop2_answer"] and 100 <= n["re_khop2_bridge"][1] <= 512
    assert n["re_khop3_middle"] == (40, 0)
    for ds in ("re_syntax_number", "re_syntax_head", "re_syntax_clauses", "re_count_listed"):
        assert n[ds] == (200, 512), ds
    assert n["re_internal_refuse"] == (240, 60) and n["re_internal_abstain"] == (120, 240)   # E8: 120 matched pairs in test
    assert n["re_count_long"] == (200, 500)
    if HAS_WIKITEXT:
        assert n["re_count_col"] == (180, 360)


def test_determinism():
    a = BT.build(BT.SEED, wikitext_path=None)
    b = BT.build(BT.SEED, wikitext_path=None)
    assert a["items"] == b["items"] and a["meta"]["sha256_items"] == b["meta"]["sha256_items"]
    c = BT.build(BT.SEED + 1, wikitext_path=None)
    assert c["meta"]["sha256_items"] != a["meta"]["sha256_items"]
    # independent streams: the fact set of one builder does not depend on the others
    assert BT.build_syntax(BT.SEED) == [it for it in a["items"] if it["tag"] == "SYNTAX"]


# ---------------------------------------------------------------- KHOP
def _forbidden(name: str) -> tuple[str, ...]:
    return BT.COUNTRY_BY_NAME[name].forbidden_all()


def test_khop_bridge_never_in_text(by):
    for ds in ("re_khop2_bridge", "re_khop2_answer"):
        for it in by[ds]:
            t, c = it["prompt_text"], it["construction"]
            for f in _forbidden(c["bridge"]) + _forbidden(c["distractor"]):
                assert not BT._contains(t, f), (ds, t, f)
            for cand in it["primary"]["candidates"]:
                assert not BT._contains(t, cand), (ds, t, cand)
            assert not BT._contains(c["answer"], BT.COUNTRY_BY_NAME[c["bridge"]].name), c
    for it in by["re_khop3_middle"]:
        t, c = it["prompt_text"], it["construction"]
        for f in _forbidden(c["bridge"]) + (c["middle"], c["distractor_middle"], c["answer"]):
            assert not BT._contains(t, f), (t, f)


def test_khop_read_position_is_the_hop1_span(by):
    for ds in ("re_khop2_bridge", "re_khop2_answer", "re_khop3_middle"):
        for it in by[ds]:
            rp, t, c = it["read_position"], it["prompt_text"], it["construction"]
            assert rp["kind"] == "hop1_span_end" and t[rp["char_start"]:rp["char_end"]] == rp["span_text"] == c["cue"]
            assert rp["char_end"] < len(t) and t[rp["char_end"]] == " "        # the span ends before the hop-2 wording
            assert t.count(c["cue"]) == 1
            bridge = BT.COUNTRY_BY_NAME[c["bridge"]]
            assert c["cue"] == (bridge.capital_landmark if ds == "re_khop3_middle" else bridge.hop2(c["hop1"]))


def test_khop_candidates_distinct_and_true(by):
    for it in by["re_khop2_bridge"]:
        c = it["construction"]
        assert c["bridge"] != c["distractor"] and c["answer"] != c["distractor_answer"]
        assert set(it["primary"]["candidates"]) == {c["bridge"], c["distractor"]} and it["primary"]["answer"] == c["bridge"]
        bridge = BT.COUNTRY_BY_NAME[c["bridge"]]
        assert bridge.hop2(c["hop2"]) == c["answer"] and BT.COUNTRY_BY_NAME[c["distractor"]].hop2(c["hop2"]) == c["distractor_answer"]
        tmpl = next(x for x in BT.KHOP2_TEMPLATES if x["id"] == c["template"])
        assert BT.khop2_valid(tmpl, bridge) and BT.khop2_valid(tmpl, BT.COUNTRY_BY_NAME[c["distractor"]])
    for it in by["re_khop2_answer"]:
        c = it["construction"]
        assert set(it["primary"]["candidates"]) == {c["answer"], c["distractor_answer"]} and it["primary"]["answer"] == c["answer"]
    for it in by["re_khop3_middle"]:
        c = it["construction"]
        assert set(it["primary"]["candidates"]) == {c["middle"], c["distractor_middle"]} and c["middle"] != c["distractor_middle"]
        assert BT.COUNTRY_BY_NAME[c["bridge"]].capital == c["middle"] and c["answer"] != c["distractor_answer"]


def test_khop_same_prompts_in_both_facts(by):
    a = {it["item_id"].replace("re_khop2_bridge", "X"): it["prompt_text"] for it in by["re_khop2_bridge"]}
    b = {it["item_id"].replace("re_khop2_answer", "X"): it["prompt_text"] for it in by["re_khop2_answer"]}
    assert a == b
    la = {it["item_id"].replace("re_khop2_bridge", "X"): it["label"] for it in by["re_khop2_bridge"]}
    lb = {it["item_id"].replace("re_khop2_answer", "X"): it["label"] for it in by["re_khop2_answer"]}
    assert la == lb   # the same order flag: c0 is the bridge iff c0 is the true completion


def test_khop_counterbalanced_per_template():
    recs = BT.khop2_records(BT.SEED)
    for tmpl, g in BT._by_dataset([{**r, "dataset": r["template"]} for r in recs]).items():
        c = Counter(r["label"] for r in g)
        assert abs(c[0] - c[1]) <= 1, (tmpl, c)
        assert len(g) >= 12, tmpl
    recs3 = BT.khop3_records(BT.SEED)
    assert len(recs3) == 40 and Counter(r["label"] for r in recs3) == {0: 20, 1: 20}
    per_t = Counter(r["template"] for r in recs3)
    assert max(per_t.values()) - min(per_t.values()) <= 1


def test_khop_distractor_same_continent_when_possible(by):
    for it in by["re_khop2_bridge"]:
        c = it["construction"]
        b, d = BT.COUNTRY_BY_NAME[c["bridge"]], BT.COUNTRY_BY_NAME[c["distractor"]]
        if c["hop2"] != "continent" and b.continent is not None:
            tmpl = next(x for x in BT.KHOP2_TEMPLATES if x["id"] == c["template"])
            same = [x for x in BT.COUNTRIES if x.name != b.name and x.continent == b.continent and BT.khop2_valid(tmpl, x)
                    and x.hop2(c["hop2"]) != c["answer"]]
            if same:
                assert d.continent == b.continent, (c, d.name)


def test_country_table_sanity():
    names = [c.name for c in BT.COUNTRIES]
    assert len(set(names)) == len(names)
    for c in BT.COUNTRIES:
        assert c.demonym and (c.jlens is None or " " not in c.jlens)
        for f in ("landmark", "capital_landmark"):
            v = getattr(c, f)
            if v:
                assert not any(BT._contains(v, x) for x in c.forbidden_all()), (c.name, v)


# ---------------------------------------------------------------- SYNTAX
PHRASE_RE = re.compile(r"^The (\w+) (" + "|".join(re.escape(p) for p in BT.PREPS) + r") the (" + "|".join(BT.ADJS) + r") (\w+)$")


def test_syntax_number_cells(by):
    for split in ("test", "pool"):
        its = [it for it in by["re_syntax_number"] if it["split"] == split]
        cells = Counter(it["construction"]["cell"] for it in its)
        assert len(cells) == 4 and len(set(cells.values())) == 1, cells
        for it in its:
            c = it["construction"]
            assert it["label"] == int(c["head_number"] == "pl")
            m = PHRASE_RE.match(it["prompt_text"])
            assert m and m.group(1) == c["head"] and m.group(4) == c["attractor"], it["prompt_text"]
            lemma = dict(BT.HEADS)
            assert c["head"] == (c["head_lemma"] if c["head_number"] == "sg" else lemma[c["head_lemma"]])


def test_syntax_head_binding(by):
    num = {it["item_id"].replace("re_syntax_number", "X"): it for it in by["re_syntax_number"]}
    for it in by["re_syntax_head"]:
        c = it["construction"]
        twin = num[it["item_id"].replace("re_syntax_head", "X")]
        assert twin["prompt_text"] == it["prompt_text"]
        assert set(it["primary"]["candidates"]) == {c["head"], c["attractor"]} and it["primary"]["answer"] == c["head"]
        assert it["label"] == int(it["primary"]["candidates"][0] == c["head"])
        assert c["head"] in it["prompt_text"].split() and c["attractor"] in it["prompt_text"].split()
    for split in ("test", "pool"):
        for cell in ("sg-sg", "sg-pl", "pl-sg", "pl-pl"):
            g = [it for it in by["re_syntax_head"] if it["split"] == split and it["construction"]["cell"] == cell]
            c = Counter(it["label"] for it in g)
            assert c[0] == c[1], (split, cell, c)
    assert not ({h for h, _ in BT.HEADS} | {p for _, p in BT.HEADS}) & ({a for a, _ in BT.ATTRACTORS} | {p for _, p in BT.ATTRACTORS})


def test_syntax_clauses_matched_on_length(by):
    for split in ("test", "pool"):
        its = [it for it in by["re_syntax_clauses"] if it["split"] == split]
        one = Counter(it["construction"]["n_words"] for it in its if it["label"] == 0)
        two = Counter(it["construction"]["n_words"] for it in its if it["label"] == 1)
        assert one == two, (split, one, two)
        pairs = BT._by_dataset([{**it, "dataset": it["construction"]["pair_id"]} for it in its])
        for pid, g in pairs.items():
            assert len(g) == 2 and {it["label"] for it in g} == {0, 1} and len({it["construction"]["n_words"] for it in g}) == 1, pid
    for it in by["re_syntax_clauses"]:
        t, c = it["prompt_text"], it["construction"]
        assert t.endswith(".") and BT._words(t) == c["n_words"] and 10 <= c["n_words"] <= 13
        words = t.rstrip(".").split()
        if it["label"] == 0:
            assert not set(words) & set(BT.CONJS), t
        else:
            assert c["conj"] in words and [w.lower() for w in words].count("the") >= 4, t   # two subjects, two objects


# ---------------------------------------------------------------- COUNT
def test_count_listed(by):
    for it in by["re_count_listed"]:
        c = it["construction"]
        words = it["prompt_text"].split(", ")
        assert len(words) == c["k"] == it["label"] + 1 and len(set(words)) == len(words)
        assert set(words) <= set(BT.LIST_CATEGORIES[c["category"]]) and not it["prompt_text"].endswith(",")
    for split, per in (("test", 25), ("pool", 64)):
        c = Counter(it["label"] for it in by["re_count_listed"] if it["split"] == split)
        assert c == {k: per for k in range(8)}


def test_count_long_window(by):
    its = by["re_count_long"]
    for it in its:
        c, p = it["construction"], it["primary"]
        words = it["prompt_text"].split(", ")
        assert len(words) == c["k"] == int(it["raw_target"]) and len(set(words)) == len(words) and BT.LONG_K[0] <= c["k"] <= BT.LONG_K[1]
        assert p["k"] == BT.LONG_WINDOW == len(p["candidates"]) and [int(x) for x in p["candidates"]] == list(range(c["k"] - c["truth_index"], c["k"] - c["truth_index"] + 5))
        assert it["label"] == c["truth_index"] == p["candidates"].index(str(c["k"])) and int(p["candidates"][0]) >= 1
    for split, per in (("test", 40), ("pool", 100)):
        assert Counter(it["label"] for it in its if it["split"] == split) == {i: per for i in range(5)}
    ks = Counter(it["construction"]["k"] for it in its)
    assert set(ks) == set(range(BT.LONG_K[0], BT.LONG_K[1] + 1))         # every length occurs


@pytest.mark.skipif(not HAS_WIKITEXT, reason="wikitext parquet not in cache (beyond_text --fetch)")
def test_count_col(by):
    bins = {i: b for i, b in enumerate(BT.COL_BINS)}
    for it in by["re_count_col"]:
        t, c = it["prompt_text"], it["construction"]
        lines = t.split("\n")
        assert len(lines) - 1 == c["line_index"] >= BT.COL_MIN_LINE and c["line_index"] <= BT.COL_MAX_LINE
        assert len(lines[-1]) == c["col"] == int(it["raw_target"]) and t[-1].isalnum() and len(t) <= BT.COL_MAX_CHARS
        assert all(len(l) <= BT.COL_WIDTH for l in lines)
        name, lo, hi, cand = bins[it["label"]]
        assert c["bin"] == name and lo <= c["col"] <= hi and it["primary"]["answer"] == cand
        assert it["primary"]["primary_render"] == "raw"


def test_clean_wikitext():
    assert BT.clean_wikitext("In 2004 Boulter landed a role , as @-@ x @,@ y ( z ) . He didn 't .") == "In 2004 Boulter landed a role, as-x,y (z). He didn't."


# ---------------------------------------------------------------- INTERNAL
def test_xstest_pairs():
    rows = BT.read_xstest()
    assert len(rows) == 450
    pairs = BT.xstest_pairs(rows)
    assert len(pairs) == 150 and Counter(p["type"] for p in pairs) == {t: 25 for t in BT.XSTEST_MATCHED_TYPES}
    for p in pairs:
        assert int(p["unsafe"]["id"]) == int(p["safe"]["id"]) + 25 and p["unsafe"]["type"] == f"contrast_{p['type']}"


def test_refuse_items(by):
    its = by["re_internal_refuse"]
    for it in its:
        c = it["construction"]
        assert it["label"] == c["design_label"] == int(c["design"] == "unsafe") and it["primary"]["key"] == "design"
    for split in ("test", "pool"):
        g = [it for it in its if it["split"] == split]
        pairs = BT._by_dataset([{**it, "dataset": it["construction"]["pair_id"]} for it in g])
        assert all(len(p) == 2 and {x["label"] for x in p} == {0, 1} for p in pairs.values())
    test_types = Counter(it["construction"]["xstest_type"] for it in its if it["split"] == "test" and it["label"] == 0)
    assert test_types == {t: 20 for t in BT.XSTEST_MATCHED_TYPES}
    assert sum(it["split"] == "test" for it in its) == 240 and len({it["construction"]["pair_id"] for it in its if it["split"] == "test"}) == 120


def test_abstain_items(by):
    its = by["re_internal_abstain"]
    for it in its:
        c = it["construction"]
        assert it["prompt_text"].endswith("?") and it["label"] == c["design_label"] == int(c["design"] == "unanswerable")
    kinds = Counter(it["construction"]["kind"] for it in its if it["label"] == 0)
    assert {"fixed", "capital", "currency", "language", "arith", "continent"} <= set(kinds)


def test_classifiers():
    assert BT.classify_refusal("I'm sorry, but I can't help with that request.")
    assert BT.classify_refusal("I cannot provide instructions for harming someone.")
    assert BT.classify_refusal("Sorry, I won't assist with this.")
    assert not BT.classify_refusal("To kill a Python process, use the kill command with the process id.")
    assert not BT.classify_refusal("You can terminate a C program by calling exit().")
    assert BT.classify_abstain("I don't know what Napoleon ate that morning; there is no record of it.")
    assert BT.classify_abstain("There is no way to know the closing price in 2050.")
    assert BT.classify_abstain("I cannot predict the future, so I can't say who will win.")
    assert not BT.classify_abstain("The capital of France is Paris.")
    assert not BT.classify_abstain("7 plus 5 is 12.")
    assert BT.classify_refusal("<think>\n\n</think>\n\nI'm sorry, I can't do that.")


def test_rekey_internal(by):
    refuse = by["re_internal_refuse"][:4]
    other = by["re_syntax_number"][:1]
    gens = {refuse[0]["item_id"]: "I'm sorry, but I can't help with that.", refuse[1]["item_id"]: "Sure! First, open a terminal and run kill -9 <pid>.",
            other[0]["item_id"]: "I'm sorry"}
    out, summary = BT.rekey_internal(refuse + other, gens)
    assert out[0]["label"] == 1 and out[0]["primary"]["key"] == "greedy" and out[0]["primary"]["answer"] == "refuse"
    assert out[1]["label"] == 0 and out[1]["primary"]["answer"] == "comply" and out[1]["construction"]["design_label"] == refuse[1]["label"]
    assert out[2] == refuse[2] and out[3]["primary"]["key"] == "design"   # no generation -> unchanged
    assert out[4] == other[0]                                              # not an INTERNAL fact -> unchanged
    assert summary["re_internal_refuse"]["n"] == 2 and summary["re_internal_refuse"]["key_pos"] == 1
    assert refuse[0]["primary"]["key"] == "design"                        # inputs not mutated


# ---------------------------------------------------------------- disk and collector
def test_disk_matches_rebuild(items):
    assert BT.ITEMS_RE.exists(), "run beyond_text --build"
    d = json.loads(BT.ITEMS_RE.read_text(encoding="utf-8"))
    assert d["meta"]["seed"] == BT.SEED and not d["meta"]["frozen"]
    disk = [it for it in d["items"] if HAS_WIKITEXT or it["dataset"] != "re_count_col"]
    assert disk == items
    if HAS_WIKITEXT:
        assert d["meta"]["sha256_items"] == BT.build(BT.SEED)["meta"]["sha256_items"]
    assert BT.load_items(BT.ITEMS_RE, "test", ["re_khop2_bridge"]) == [it for it in d["items"] if it["dataset"] == "re_khop2_bridge" and it["split"] == "test"]
