"""Offline tests for dataset/build_dataset.py, dataset/donors.py, dataset/g4_selection.py.
Nothing here writes under results/ or cache/; files are built in memory or in tmp_path."""
from __future__ import annotations

import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)

from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402
from projects.g_agreement.dataset import donors as dn  # noqa: E402
from projects.g_agreement.dataset import g4_selection as g4  # noqa: E402

ITEMS_PATH = os.path.join(REPO, "projects", "g_agreement", "dataset", "items.json")


@pytest.fixture(scope="module")
def data():
    return bd.build(bd.DEFAULT_SEED)


@pytest.fixture(scope="module")
def items(data):
    return data["items"]


# ---------------------------------------------------------------- structure & schema
def test_counts(items):
    assert len(items) == 40
    assert len({it["pair_id"] for it in items}) == 20
    for fam in bd.FAMILIES:
        fam_items = [it for it in items if it["family"] == fam]
        assert len(fam_items) == 10
        assert sum(it["split"] == "dev" for it in fam_items) == 2
        assert sum(it["split"] == "test" for it in fam_items) == 8


def test_schema_keys(items):
    for it in items:
        assert bd.REQUIRED_KEYS <= set(it)
        for k in ("name", "question", "candidates", "answer", "answer_aliases"):
            assert k in it["primary"]
        for k in ("entities", "objects", "relation"):
            assert k in it["secondary"]
        assert it["render"] == "chat" and it["system"] is None
        assert isinstance(it["target_answer_regex"], str)
        re.compile(it["target_answer_regex"])


def test_primary_names_by_family(items):
    for it in items:
        name = it["primary"]["name"]
        if it["family"] == "language":
            assert name == "response_language"
        elif it["family"] == "tense":
            assert name == "response_tense" and it["primary"]["candidates"] == ["past", "future"]
        elif it["family"] == "ownership":
            assert name.endswith("_owner")
        else:
            assert name == "two_step_result"


def test_pairs_share_fields_and_differ_only_in_answer(items):
    by_pair = {}
    for it in items:
        by_pair.setdefault(it["pair_id"], []).append(it)
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert (a["version"], b["version"]) == ("A", "B")
        for k in ("family", "split", "template_id"):
            assert a[k] == b[k]
        assert a["primary"]["candidates"] == b["primary"]["candidates"]
        assert a["primary"]["answer"] == a["primary"]["candidates"][0]
        assert b["primary"]["answer"] == b["primary"]["candidates"][1]
        assert a["prompt_text"] != b["prompt_text"]


def test_short_answer_cue_in_every_prompt(items):
    for it in items:
        assert bd.SHORT_ANSWER_CUE.search(it["prompt_text"]), it["item_id"]


# ---------------------------------------------------------------- answer keys & balance
def test_independent_solver_agrees_with_construction(items):
    for it in items:
        assert bd.solve_prompt(it) == it["primary"]["answer"], it["item_id"]


def test_balance_report(data):
    rep = data["meta"]["balance_checks"]
    for fam in bd.FAMILIES:
        assert rep[fam]["test_answer_position_counts"] == {"first_listed": 4, "second_listed": 4}
        assert len(rep[fam]["test_templates"]) == 4
        assert not set(rep[fam]["dev_templates"]) & set(rep[fam]["test_templates"])
    for fam in ("ownership", "mapping"):
        assert rep[fam]["test_answer_is_first_mentioned"] == 4
        assert rep[fam]["test_answer_is_first_mentioned_by_version"] == {"A": 2, "B": 2}
    assert rep["language"]["test_cue_position"] == {"before": 2, "after": 2}


def test_mapping_both_candidates_present_in_both_versions(items):
    for it in items:
        if it["family"] == "mapping":
            for c in it["primary"]["candidates"]:
                assert re.search(r"(?<![A-Za-z])" + re.escape(c) + r"(?![A-Za-z])", it["prompt_text"])


def test_language_other_candidate_absent_from_prompt(items):
    for it in items:
        if it["family"] == "language":
            other = it["construction"]["other_candidate"]
            assert other not in it["prompt_text"]


def test_target_regex_sanity(items):
    for it in items:
        rx = it["target_answer_regex"]
        if it["family"] in ("ownership", "mapping"):
            assert re.search(rx, it["primary"]["answer"])
            assert not re.search(rx, it["construction"]["other_candidate"])
        if it["family"] == "language":
            # the other language's expected word must not match this item's regex
            other_rx = r"(?i)\b(" + it["construction"]["expected_word_other"] + r")\b"
            own_words = re.findall(r"[a-zñçãéíóúüöäåß]+", rx.lower())
            for w in own_words:
                if len(w) > 2:
                    assert not re.fullmatch(other_rx[5:], w), (it["item_id"], w)


# ---------------------------------------------------------------- determinism
def test_build_is_deterministic():
    a = bd.build(bd.DEFAULT_SEED)
    b = bd.build(bd.DEFAULT_SEED)
    assert a["items"] == b["items"]
    assert a["meta"]["sha256_items"] == b["meta"]["sha256_items"]


def test_other_seed_changes_arrangement_but_keeps_balance():
    other = bd.build(bd.DEFAULT_SEED + 1)
    base = bd.build(bd.DEFAULT_SEED)
    assert other["meta"]["sha256_items"] != base["meta"]["sha256_items"]
    bd.validate(other["items"])  # balance must hold for any seed


@pytest.mark.skipif(not os.path.exists(ITEMS_PATH), reason="items.json not built yet")
def test_items_on_disk_match_rebuild(data):
    with open(ITEMS_PATH, encoding="utf-8") as f:
        disk = json.load(f)
    rebuilt = bd.build(disk["meta"]["seed"])
    assert disk["meta"]["sha256_items"] == rebuilt["meta"]["sha256_items"]
    assert disk["meta"]["sha256_items"] == bd.sha256_items(disk["items"])


def test_writer_uses_tmp_path(tmp_path, data):
    out = tmp_path / "items.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    loaded = bd.load_items(str(out))
    assert len(loaded["items"]) == 40


# ---------------------------------------------------------------- donors (G3)
def test_donor_constraints(items):
    out = dn.build_assignments(items, dn.DEFAULT_SEED)
    idx = {it["item_id"]: it for it in items}
    asg = out["assignments"]
    assert len(asg) == 32 and all(idx[r]["split"] == "test" for r in asg)
    for r, d in asg.items():
        assert idx[r]["family"] == idx[d]["family"]
        assert idx[r]["pair_id"] != idx[d]["pair_id"]
        assert r != d
    for fam in bd.FAMILIES:
        recips = [r for r in asg if idx[r]["family"] == fam]
        assert sorted(asg[r] for r in recips) == sorted(recips)  # permutation
        for rl in (0, 1):
            dl = [dn._label(idx[asg[r]]) for r in recips if dn._label(idx[r]) == rl]
            assert dl.count(0) == 2 and dl.count(1) == 2
    assert out["checks"]["all_passed"]
    assert out["checks"]["donor_label_equals_recipient_label_fraction"] == 0.5


def test_donors_deterministic(items):
    a = dn.build_assignments(items, 7)["assignments"]
    b = dn.build_assignments(items, 7)["assignments"]
    assert a == b
    assert dn.build_assignments(items, 8)["assignments"] != a


def test_donor_checks_fail_loudly(items):
    out = dn.build_assignments(items, dn.DEFAULT_SEED)
    bad = dict(out["assignments"])
    r = next(iter(bad))
    bad[r] = r  # self-donation violates excludes_recipient_pair
    with pytest.raises(dn.DonorConstraintError):
        dn.run_checks(items, bad)


# ---------------------------------------------------------------- G4 selection
def test_g4_selection(items):
    sel = g4.select_pairs(items, g4.DEFAULT_SEED)
    assert len(sel["pairs"]) == 4 and len(sel["item_ids"]) == 8
    idx = {it["item_id"]: it for it in items}
    fams = [idx[p + "A"]["family"] for p in sel["pairs"]]
    assert fams == bd.FAMILIES
    assert all(idx[i]["split"] == "test" for i in sel["item_ids"])
    assert g4.select_pairs(items, g4.DEFAULT_SEED)["pairs"] == sel["pairs"]  # deterministic
    assert "timestamp" in sel and "chosen_before_test_outputs" in sel


def test_dev_test_templates_disjoint_per_family(items):
    for fam in bd.FAMILIES:
        dev = {it["template_id"] for it in items if it["family"] == fam and it["split"] == "dev"}
        test = {it["template_id"] for it in items if it["family"] == fam and it["split"] == "test"}
        assert dev and test and not (dev & test), fam


def test_test_split_answer_position_balanced_per_family(items):
    for fam in bd.FAMILIES:
        pos = [it["primary"]["candidates"].index(it["primary"]["answer"])
               for it in items if it["family"] == fam and it["split"] == "test"]
        assert len(pos) == 8 and pos.count(0) == 4 and pos.count(1) == 4, fam


def test_dev_assignments_cross_family(items):
    out = dn.build_assignments(items, dn.DEFAULT_SEED)
    dev = out["dev_assignments"]
    idx = {it["item_id"]: it for it in items}
    assert dev["dev_cross_family"] is True and dev["scored"] is False
    assert sorted(dev["assignments"]) == sorted(i for i in idx if idx[i]["split"] == "dev")
    assert sorted(dev["assignments"].values()) == sorted(dev["assignments"])
    for r, d in dev["assignments"].items():
        assert idx[r]["family"] != idx[d]["family"] and idx[r]["pair_id"] != idx[d]["pair_id"]
    assert out["checks"]["dev_assignments_cross_family"] is True
