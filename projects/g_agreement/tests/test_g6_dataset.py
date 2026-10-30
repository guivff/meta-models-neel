"""Offline tests for dataset/build_dataset_g6.py (G6 'choice' family). Never writes under results/."""
from __future__ import annotations

import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)

from projects.g_agreement.dataset import build_dataset_g6 as g6  # noqa: E402

ITEMS_G6 = os.path.join(REPO, "projects", "g_agreement", "dataset", "items_g6.json")
ITEMS_G1 = os.path.join(REPO, "projects", "g_agreement", "dataset", "items.json")


@pytest.fixture(scope="module")
def items():
    return g6.build(g6.DEFAULT_SEED)["items"]


def test_shape(items):
    assert len(items) == 16 and len({it["pair_id"] for it in items}) == 8
    for it in items:
        assert it["family"] == "choice" and it["split"] == "test"
        assert it["item_id"].startswith("choice-") and it["render"] == "chat" and it["system"] is None
        assert it["primary"]["name"] == "model_choice"
        assert it["primary"]["question"] == "Which of the two options will the model choose?"
        assert it["primary"]["answer"] is None and it["primary"]["answer_source"] == "target_greedy"
        assert len(it["primary"]["candidates"]) == 2
        re.compile(it["target_answer_regex"])
        assert g6.SHORT_ANSWER_CUE.search(it["prompt_text"])


def test_pairs_swap_order_and_share_candidates(items):
    by_pair = {}
    for it in items:
        by_pair.setdefault(it["pair_id"], []).append(it)
    for pair in by_pair.values():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert a["primary"]["candidates"] == b["primary"]["candidates"]
        assert a["template_id"] == b["template_id"]
        fa, fb = a["construction"]["first_mentioned_candidate"], b["construction"]["first_mentioned_candidate"]
        assert fa == a["primary"]["candidates"][0] and fb == a["primary"]["candidates"][1]
        assert a["prompt_text"] != b["prompt_text"]


def test_first_listed_balance_and_unique_options(items):
    pos = [it["construction"]["first_listed_position"] for it in items]
    assert pos.count(0) == 8 and pos.count(1) == 8
    opts = [c for it in items if it["version"] == "A" for c in it["primary"]["candidates"]]
    assert len(opts) == 16 and len(set(opts)) == 16  # no option in two pairs
    assert all(" " not in o for o in opts)


def test_templates_and_types(items):
    assert len({it["template_id"] for it in items}) >= 4
    types = {it["construction"]["option_type"] for it in items}
    assert {"fruit", "colour", "animal", "number word", "tool", "city"} <= types


def test_deterministic_and_seed_sensitive():
    a, b = g6.build(g6.DEFAULT_SEED), g6.build(g6.DEFAULT_SEED)
    assert a["items"] == b["items"]
    assert g6.build(g6.DEFAULT_SEED + 1)["meta"]["sha256_items"] != a["meta"]["sha256_items"]
    g6.validate(g6.build(g6.DEFAULT_SEED + 1)["items"])


@pytest.mark.skipif(not os.path.exists(ITEMS_G6), reason="items_g6.json not built yet")
def test_items_g6_on_disk_match_rebuild():
    with open(ITEMS_G6, encoding="utf-8") as f:
        disk = json.load(f)
    assert disk["meta"]["sha256_items"] == g6.build(disk["meta"]["seed"])["meta"]["sha256_items"]
    assert disk["meta"]["sha256_items"] == g6.sha256_items(disk["items"])


@pytest.mark.skipif(not os.path.exists(ITEMS_G1), reason="items.json not present")
def test_g1_items_not_touched_by_g6_builder():
    with open(ITEMS_G1, encoding="utf-8") as f:
        d = json.load(f)
    assert "choice" not in d["meta"]["families"] and len(d["items"]) == 40
    assert not any(it["family"] == "choice" for it in d["items"])
