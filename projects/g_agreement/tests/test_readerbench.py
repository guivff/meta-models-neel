"""Offline tests for ReaderBench (PLAN_R §7, WS12; r_bench/readerbench/): schema in the items_r.json shape, exact
label balance per split, counterbalancing of every declared factor over the full set and near-balance inside the
splits, candidate-not-in-text for KHOP / KNOWLEDGE, no duplicate prompts (within a fact, and across facts unless
declared shared), seed determinism and fact-independence of the streams, split-group integrity (no entity in both
test and pool), the independent ground-truth round trip of solvers.py on EVERY item of EVERY fact, the E11 minimal
pairs, and that the built files on disk match the generator. Nothing is written by the tests.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_readerbench.py -q``
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.r_bench import datasets as D  # noqa: E402
from projects.g_agreement.r_bench.readerbench import build as B  # noqa: E402
from projects.g_agreement.r_bench.readerbench import common as CM  # noqa: E402
from projects.g_agreement.r_bench.readerbench import solvers as S  # noqa: E402
from projects.g_agreement.r_bench.readerbench import tables as T  # noqa: E402


@pytest.fixture(scope="module")
def bank():
    items_b, items_k, info = B.build_all(CM.SEED)
    return {"b": items_b, "k": items_k, "info": info, "facts": {f.id: f for f in B.all_facts()}}


@pytest.fixture(scope="module")
def by_ds(bank):
    out = collections.defaultdict(list)
    for it in bank["b"] + bank["k"]:
        out[it["dataset"]].append(it)
    return out


# ================================================================== tables and spec
def test_tables_clean():
    assert T.check_tables() == []
    assert len(T.COUNTRIES) >= 50 and len(T.with_landmark()) >= 36


def test_facts_cover_every_tag_and_module():
    facts = B.all_facts()
    tags = collections.Counter(f.tag for f in facts)
    for t in ("SURFACE", "TOPIC", "FORM", "KNOWLEDGE", "COMPUTED", "KHOP", "SYNTAX", "COUNT", "META", "INTERNAL", "CONTEXT"):
        assert tags[t] >= 3, (t, tags)
    assert len(facts) >= 55
    by_id = {f.id: f for f in facts}
    for f in facts:
        assert f.id in S.SOLVERS, f"{f.id} has no independent solver"
        assert f.ground_truth, f.id
        for sib in f.shares_text_with:
            assert sib in by_id and f.id in by_id[sib].shares_text_with, (f.id, sib, "shares_text_with must be mutual")


def test_fact_record_validation():
    with pytest.raises(ValueError):
        CM.Fact("rb_khop_x", "SYNTAX", "q", "a", "b", "{X}")          # tag / id mismatch
    with pytest.raises(ValueError):
        CM.Fact("rb_syntax_x", "SYNTAX", "q", "a", "b", "no slot")   # template without {X}
    with pytest.raises(ValueError):
        CM.Fact("rb_syntax_x", "SYNTAX", "q", "a", "a", "{X}")       # equal candidates
    with pytest.raises(ValueError):
        CM.Fact("rb_count_x", "COUNT", "q", "", "", "{X}", sided="kway", classes=("1", "2"))


# ================================================================== schema
def test_items_r_schema(bank):
    for it in bank["b"] + bank["k"]:
        assert set(it) >= {"item_id", "dataset", "tag", "split", "label", "raw_target", "prompt_text", "render", "system", "primary", "construction"}
        assert re.fullmatch(r"rb-rb_[a-z]+_[a-z0-9_]+-(test|pool)-\d{4}", it["item_id"])
        assert it["render"] == "chat" and it["split"] in ("test", "pool")
        p = it["primary"]
        assert set(p) >= {"name", "question", "candidates", "answer", "template", "sided", "jlens", "per_item_candidates", "label_source"}
        assert p["name"] == it["dataset"] and "{X}" in p["template"] and p["answer"] in p["candidates"]
        assert all(j for j in p["jlens"]), (it["dataset"], "every J-lens form present (WS1: one-sided fillers get 'other')")
        assert it["tag"] in CM.RB_TAGS
    for it in bank["b"]:
        assert it["primary"]["sided"] in ("two", "one") and it["label"] in (0, 1)
        assert (it["label"] == 1) == (it["primary"]["answer"] == it["primary"]["candidates"][0])
    for it in bank["k"]:
        assert it["primary"]["sided"] == "kway" and it["primary"]["k"] == len(it["primary"]["candidates"]) >= 3
        assert it["primary"]["candidates"][it["label"]] == it["primary"]["answer"]


def test_tags_known_to_datasets_or_new(bank):
    new = {"KHOP", "SYNTAX", "COUNT"}
    for t in {it["tag"] for it in bank["b"] + bank["k"]}:
        assert t in D.TAGS or t in new


# ================================================================== balance and counterbalancing
def test_exact_label_balance_per_split(by_ds, bank):
    for ds, items in by_ds.items():
        k = bank["facts"][ds].k
        for split in ("test", "pool"):
            cnt = collections.Counter(it["label"] for it in items if it["split"] == split)
            if cnt:
                assert len(cnt) == k and len(set(cnt.values())) == 1, (ds, split, cnt)
        assert sum(1 for it in items if it["split"] == "test") >= 32, (ds, "test split too small")   # 3-hop: 68 items, 32/28


def test_declared_factors_balanced(by_ds, bank):
    """Exact over the full set (validated at build), at most 60/40 inside each split for binary factors and no level
    missing inside the test split."""
    for ds, items in by_ds.items():
        f = bank["facts"][ds]
        for key in f.balanced_factors:
            test = [str(it["construction"][key]) for it in items if it["split"] == "test"]
            cnt = collections.Counter(test)
            if (ds, key) != ("rb_internal_refusal", "pair"):   # the pair IS the split group: half the pairs are in each split
                assert set(cnt) == {str(it["construction"][key]) for it in items}, (ds, key, "level missing from the test split")
            if len(cnt) == 2:
                lo, hi = sorted(cnt.values())
                assert hi / (lo + hi) <= 0.6, (ds, key, cnt)


def test_per_item_candidate_order_counterbalanced(by_ds, bank):
    for ds, items in by_ds.items():
        f = bank["facts"][ds]
        if not f.per_item_candidates:
            continue
        pos = collections.Counter(it["construction"]["answer_position"] for it in items)
        assert pos[0] == pos[1], (ds, pos)
        for it in items:
            assert len(it["primary"]["candidates"]) == 2
            assert it["primary"]["jlens"] == [c[4:] if c.startswith("the ") else c for c in it["primary"]["candidates"]]
            assert it["construction"]["answer_position"] == it["primary"]["candidates"].index(it["primary"]["answer"])


def test_fixed_candidates_identical_within_fact(by_ds, bank):
    for ds, items in by_ds.items():
        f = bank["facts"][ds]
        if f.per_item_candidates or f.sided == "kway":
            continue
        cands = {tuple(it["primary"]["candidates"]) for it in items}
        assert cands == {(f.pos, f.neg)}, (ds, cands)


# ================================================================== candidate not in text, duplicates, groups
def test_candidates_not_in_text_khop_knowledge(by_ds, bank):
    n = 0
    for ds, items in by_ds.items():
        if bank["facts"][ds].tag not in ("KHOP", "KNOWLEDGE"):
            continue
        for it in items:
            for c in it["primary"]["candidates"]:
                assert not CM.contains_word(it["prompt_text"], c), (ds, it["prompt_text"], c)
                n += 1
    assert n > 2000


def test_khop_bridge_never_in_text(by_ds):
    for ds, items in by_ds.items():
        if not ds.startswith("rb_khop"):
            continue
        for it in items:
            bridge = T.bare(it["construction"]["bridge"])
            assert not CM.contains_word(it["prompt_text"], bridge), (ds, it["prompt_text"], bridge)
            assert not CM.contains_word(it["prompt_text"], T.bare(it["construction"]["distractor"]))


def test_no_duplicate_prompts(bank, by_ds):
    for ds, items in by_ds.items():
        keys = [CM.prompt_key(it) for it in items]
        assert len(set(keys)) == len(keys), (ds, "duplicate prompt within the fact")
    shared = collections.defaultdict(set)
    for it in bank["b"] + bank["k"]:
        shared[CM.prompt_key(it)].add(it["dataset"])
    n_shared = 0
    for (text, _s, _m), ds in shared.items():
        if len(ds) > 1:
            n_shared += 1
            for d in ds:
                assert ds - {d} <= set(bank["facts"][d].shares_text_with), (sorted(ds), text[:60])
    assert n_shared > 0   # KHOP bridge/answer and the SYNTAX agreement/head pairs share texts by design


def test_split_groups_do_not_leak(by_ds, bank):
    """An entity (KHOP landmark, KNOWLEDGE entity, refusal pair, against-belief country) is never in both splits."""
    for ds, items in by_ds.items():
        f = bank["facts"][ds]
        key = {"KHOP": "bridge", "KNOWLEDGE": "entity"}.get(f.tag)
        if ds == "rb_internal_refusal":
            key = "pair"
        if ds == "rb_context_against_belief":
            key = "country"
        if key is None:
            continue
        splits = collections.defaultdict(set)
        for it in items:
            splits[str(it["construction"][key])].add(it["split"])
        assert all(len(v) == 1 for v in splits.values()), (ds, [k for k, v in splits.items() if len(v) > 1][:5])


def test_ids_unique_and_disjoint_from_other_banks(bank):
    ids = [it["item_id"] for it in bank["b"] + bank["k"]]
    assert len(set(ids)) == len(ids)
    prompts = {it["prompt_text"] for it in bank["b"] + bank["k"]}
    for f in ("items.json", "items_x.json", "items_g6.json"):
        p = REPO / "projects" / "g_agreement" / "dataset" / f
        if p.exists():
            other = json.loads(p.read_text(encoding="utf-8"))["items"]
            assert not ({it["item_id"] for it in other} & set(ids))
            assert not ({it["prompt_text"] for it in other} & prompts)


# ================================================================== determinism and independence
def test_deterministic_and_streams_independent():
    a = B.build_all(CM.SEED)
    b = B.build_all(CM.SEED)
    assert CM.sha256_items(a[0]) == CM.sha256_items(b[0]) and CM.sha256_items(a[1]) == CM.sha256_items(b[1])
    c = B.build_all(CM.SEED + 1)
    assert CM.sha256_items(c[0]) != CM.sha256_items(a[0])
    # one fact's items do not depend on which other facts are built (per-fact seeded streams)
    only = B.build_all(CM.SEED, tags=["COMPUTED"])
    full_c = [it for it in a[0] if it["tag"] == "COMPUTED"]
    assert CM.sha256_items(only[0]) == CM.sha256_items(full_c)


def test_balanced_helpers():
    import random
    rng = random.Random(0)
    for n in (4, 8, 12, 156, 320):
        b = CM.balanced_bools(n, rng)
        assert len(b) == n and sum(b) == n // 2
    lv = CM.balanced_levels(["a", "b", "c"], 30, rng)
    assert collections.Counter(lv) == {"a": 10, "b": 10, "c": 10}
    with pytest.raises(ValueError):
        CM.balanced_levels(["a", "b", "c"], 31, rng)
    with pytest.raises(ValueError):
        CM.balanced_bools(7, rng)


def test_split_drafts_groups_and_balance():
    import random
    drafts = [CM.Draft(f"t{i}", i % 2, "x", group=f"g{i // 4}") for i in range(400)]
    test, pool, info = CM.split_drafts(drafts, 2, random.Random(1), 200, 512)
    assert len(test) == 200 and len(pool) == 200 and info["n_dropped"] == 0
    gt = {d.group for d in test}
    assert not (gt & {d.group for d in pool})
    assert sum(d.label for d in test) == 100 and sum(d.label for d in pool) == 100
    # short fact: half / half, whole groups (of 4) never split, so the test side may overshoot by one group
    test, pool, info = CM.split_drafts(drafts[:100], 2, random.Random(1), 200, 512)
    assert 50 <= len(test) <= 54 and len(test) + len(pool) == 100 and info["small_test"]
    assert not ({d.group for d in test} & {d.group for d in pool})


# ================================================================== independent ground truth (the round trip)
def test_roundtrip_every_item(bank):
    rt = S.roundtrip(bank["b"] + bank["k"])
    assert set(rt) == set(bank["facts"]), "every fact has a solver that ran"
    bad = {ds: r for ds, r in rt.items() if not r["ok"]}
    assert bad == {}, bad
    assert all(r["n_solved"] == r["n"] for r in rt.values())


def test_solvers_are_not_trivial():
    """The solver must reject a mislabelled item: flip the text, keep the answer."""
    assert S.SOLVERS["rb_computed_sum_parity"]({"prompt_text": "17 + 26 =", "primary": {"answer": "odd"}}) == "odd"
    assert S.SOLVERS["rb_computed_sum_parity"]({"prompt_text": "17 + 27 =", "primary": {"answer": "odd"}}) == "even"
    assert S.SOLVERS["rb_internal_puzzle_answer"]({"prompt_text": "A -> C, C -> F, F -> B, B -> A. Start at A and follow the arrows three times. Where do you end up? Answer with the letter only."}) == "B"
    assert S.SOLVERS["rb_syntax_before_after"]({"prompt_text": "The chef cooked the meal before the guard locked the gate."}) == "the first-mentioned event"
    assert S.SOLVERS["rb_syntax_before_after"]({"prompt_text": "Before the guard locked the gate, the chef cooked the meal."}) == "the second-mentioned event"
    assert S.SOLVERS["rb_khop_landmark_capital_answer"]({"prompt_text": "The capital of the country that is home to the Louvre is"}) == "Paris"
    assert S.SOLVERS["rb_context_system_fact"]({"prompt_text": "Who has the red pen? Answer with the name only.",
                                                "system": "Background: Anna has the blue cup. Emma has the red pen."}) == "Emma"


# ================================================================== E11 minimal pairs (IDEAS_R)
def test_e11_minimal_pairs(by_ds):
    """Negation / function-word facts are TRUE minimal pairs: every item has a partner (same pair_id, other label) whose
    word multiset differs only in the function word; the pair never straddles the test / pool split."""
    for ds, strip in (("rb_form_negation", {"not", "cannot", "can"}), ("rb_syntax_quantifier_every_no", {"every", "no"}),
                      ("rb_syntax_before_after", {"before", "after"})):
        items = by_ds[ds]
        assert len(items) >= 280, ds
        by_pair = collections.defaultdict(list)
        for it in items:
            by_pair[it["construction"]["pair_id"]].append(it)
        assert all(len(v) == 2 for v in by_pair.values()), (ds, "unpaired items")
        for pid, (a, b) in by_pair.items():
            assert {a["label"], b["label"]} == {0, 1} and a["split"] == b["split"], (ds, pid)
            wa = collections.Counter(w for w in re.findall(r"[a-z]+", a["prompt_text"].lower()) if w not in strip)
            wb = collections.Counter(w for w in re.findall(r"[a-z]+", b["prompt_text"].lower()) if w not in strip)
            assert wa == wb, (ds, pid, a["prompt_text"], b["prompt_text"])
    neg = by_ds["rb_form_negation"]
    assert all((" not " in it["prompt_text"] or "cannot" in it["prompt_text"]) == (it["label"] == 0) for it in neg)


# ================================================================== CONTEXT shape and INTERNAL provisional labels
def test_context_items(by_ds):
    for it in by_ds["rb_context_system_fact"]:
        assert it["system"] and it["primary"]["answer"] in it["system"] and it["primary"]["answer"] not in it["prompt_text"]
        assert it["prompt_text"].endswith("Answer with the name only.")
    for it in by_ds["rb_context_earlier_turn"]:
        assert it["system"] is None and len(it["capture_messages"]) == 3 and it["capture_messages"][-1]["content"] == it["prompt_text"]
        assert it["primary"]["answer"] not in it["prompt_text"]
    for it in by_ds["rb_context_against_belief"]:
        c = it["construction"]
        assert it["system"] and c["context_capital"] in it["system"] and c["true_capital"] == T.BY_NAME[c["country"]].capital
        assert set(it["primary"]["candidates"]) == {c["context_capital"], c["true_capital"]}
        assert it["primary"]["label_source"] == "model"


def test_internal_provisional_labels(by_ds, bank):
    for ds in ("rb_internal_puzzle_answer", "rb_internal_refusal", "rb_internal_abstain", "rb_internal_self_choice"):
        assert bank["facts"][ds].label_source == "model"
        assert all(it["primary"]["label_source"] == "model" for it in by_ds[ds])
    for it in by_ds["rb_internal_puzzle_answer"]:
        assert it["construction"]["two_step"] in it["primary"]["candidates"] and it["construction"]["two_step"] != it["primary"]["answer"]
    pairs = collections.Counter((it["construction"]["pair"], it["construction"]["sensitive"]) for it in by_ds["rb_internal_refusal"])
    assert all(v == 2 for v in pairs.values()) and len(pairs) == 60


# ================================================================== files on disk
def test_built_files_match_generator(bank):
    for path, items in ((CM.ITEMS_RB, bank["b"]), (CM.ITEMS_RBK, bank["k"])):
        if not path.exists():
            pytest.skip(f"{path.name} not built")
        disk = json.loads(path.read_text(encoding="utf-8"))
        assert disk["meta"]["seed"] == CM.SEED and disk["meta"]["frozen"] is False
        assert disk["meta"]["sha256_items"] == CM.sha256_items(disk["items"]) == CM.sha256_items(items), path.name


# ================================================================== 2026-10-18 review fixes
def test_non_syntax_sentences_are_plausible(by_ds):
    """Every (verb, object) in the plausible-sentence facts is a PLAUSIBLE_OBJECTS pair (selectional restrictions)."""
    verbs = sorted(CM.PLAUSIBLE_OBJECTS, key=len, reverse=True)
    checked = 0
    for ds in ("rb_syntax_clause_count", "rb_syntax_before_after", "rb_syntax_quantifier_every_no", "rb_form_voice", "rb_surface_word_count"):
        for it in by_ds[ds]:
            t = it["prompt_text"]
            for m in re.finditer(r"\b(" + "|".join(verbs) + r") (the \w+)", t):
                assert CM.is_plausible(m.group(1), m.group(2)), (ds, t, m.group(0))
                checked += 1
            for m in re.finditer(r"\b(the \w+) was (\w+) by\b", t):            # passive: patient ... was V by agent
                assert CM.is_plausible(m.group(2), m.group(1)), (ds, t)
                checked += 1
    assert checked > 1500


def test_syntax_nonce_facts_documented():
    readme = (REPO / "projects" / "g_agreement" / "r_bench" / "readerbench" / "README.md").read_text(encoding="utf-8")
    assert "nonce control" in readme and "PLAUSIBLE_OBJECTS" in readme


def test_column_position_last_line_is_natural(by_ds):
    from projects.g_agreement.r_bench.readerbench import count as CN

    for ds in ("rb_count_column_position", "rb_count_line_long_short"):
        for it in by_ds[ds]:
            last = it["prompt_text"].rsplit("\n", 1)[-1]
            assert any(sent.startswith(last) for sent in CN.LONG_SENTENCES), (ds, last)
            assert len(last) == it["construction"]["col"]


def test_grammar_slips_fixed(by_ds):
    for it in by_ds["rb_meta_question_type_3"] + by_ds["rb_meta_why_vs_when"]:
        t = it["prompt_text"]
        if "Explain why" in t or "How many days before" in t or "saw that" in t:
            assert not any(t.split(" ")[i] in ("suspend", "postpone", "cancel") for i in range(len(t.split(" ")))), t
    for it in by_ds["rb_internal_abstain"]:
        assert "in United" not in it["prompt_text"] and "of United" not in it["prompt_text"]
    for it in by_ds["rb_knowledge_animal_class"]:
        if it["prompt_text"].startswith("Consider "):
            assert it["prompt_text"].startswith("Consider the "), it["prompt_text"]
    for it in by_ds["rb_topic_news_8"] + by_ds["rb_topic_is_health"]:
        assert "reduced sharp" not in it["prompt_text"] and "reduced early" not in it["prompt_text"]
        assert not re.search(r"\bA (Chile|Geneva|Kyoto|Cambridge|Pasadena|Munich) team", it["prompt_text"])


def test_descriptive_only_facts_are_the_declared_ones(bank):
    small = {f for f, r in bank["info"].items() if r["small_test"]}
    assert small == {"rb_khop_3hop_middle", "rb_internal_refusal"}, small
    readme = (REPO / "projects" / "g_agreement" / "r_bench" / "readerbench" / "README.md").read_text(encoding="utf-8")
    for f in small:
        assert f in readme.split("## Descriptive-only facts")[1].split("## Deviations")[0]
