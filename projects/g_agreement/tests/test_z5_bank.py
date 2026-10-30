"""Offline tests for the Z5 identity-binding factorial bank (BRIEF_Z.md §Z5): banks/binding_factorial/build_bank.py
invariants (counts, factorial balance, A/B token permutation, within-cell multiset, solver agreement, id disjointness,
both query directions) and check_variance.py on synthetic states (planted single-factor direction -> stop; balanced
noise -> no stop, Hewitt–Liang control passes). Nothing is written under results/ or cache/ (guard test).

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_z5_bank.py -q``
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.banks.binding_factorial import build_bank as BB  # noqa: E402
from projects.g_agreement.banks.binding_factorial import check_variance as CV  # noqa: E402
from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402
from projects.g_agreement.dataset import build_dataset_x as bdx  # noqa: E402

G_DIR = REPO / "projects" / "g_agreement"
BANK_JSON = G_DIR / "banks" / "binding_factorial" / "items_binding_factorial.json"
RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None


@pytest.fixture(scope="module")
def data():
    return BB.build(BB.DEFAULT_SEED)


@pytest.fixture(scope="module")
def items(data):
    return data["items"]


@pytest.fixture(scope="module")
def pairs(items):
    return CV.load_pairs(items)


def _A(pairs):
    return [p["A"] for p in pairs]


# ================================================================== counts, ids, determinism
def test_counts(items, pairs):
    assert len(items) == 256 and len(pairs) == 128
    assert len({it["construction"]["cell"] for it in items}) == 64
    assert len({it["item_id"] for it in items}) == 256 and len({it["prompt_text"] for it in items}) == 256
    for it in items:
        assert re.fullmatch(r"zb-\d{2}-[12][AB]", it["item_id"]) and it["item_id"] == it["pair_id"] + it["version"]
        assert it["family"] == "ownership" and it["split"] == "test" and it["render"] == "chat" and it["system"] is None
        assert bd.REQUIRED_KEYS <= set(it)
        assert it["template_id"] in {t["id"] for t in BB.TEMPLATES}


def test_deterministic_and_matches_disk(data):
    again = BB.build(BB.DEFAULT_SEED)
    assert again["meta"]["sha256_items"] == data["meta"]["sha256_items"]
    assert BB.build(BB.DEFAULT_SEED + 1)["meta"]["sha256_items"] != data["meta"]["sha256_items"]
    assert BANK_JSON.exists(), "items_binding_factorial.json missing: run build_bank.py"
    disk = json.loads(BANK_JSON.read_text(encoding="utf-8"))
    assert disk["meta"]["seed"] == BB.DEFAULT_SEED == 20261010
    assert disk["meta"]["sha256_items"] == data["meta"]["sha256_items"] == bd.sha256_items(disk["items"])
    assert disk["meta"]["frozen"] is False


def test_no_id_or_prompt_overlap_with_other_banks(items):
    ids = {it["item_id"] for it in items}
    prompts = {it["prompt_text"] for it in items}
    others = [G_DIR / "dataset" / f for f in ("items.json", "items_x.json", "items_g6.json", "items_x3_candidates.json",
                                               "items_y1_choice.json", "items_y1_selected.json")]
    checked = 0
    for f in others:
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        o_items = d["items"] if isinstance(d, dict) and "items" in d else d
        o_ids = {it["item_id"] for it in o_items if isinstance(it, dict) and "item_id" in it}
        o_prompts = {it.get("prompt_text") for it in o_items if isinstance(it, dict)}
        assert not (ids & o_ids), (f.name, sorted(ids & o_ids)[:3])
        assert not (prompts & o_prompts), f.name
        checked += 1
    assert checked >= 2  # items.json and items_x.json at least
    # and against the in-memory rebuilds (independent of what is on disk)
    g_ids = {it["item_id"] for it in bd.build(bd.DEFAULT_SEED)["items"]}
    x_items = bdx.build(bdx.DEFAULT_SEED)["items"]
    assert not (ids & g_ids) and not (ids & {it["item_id"] for it in x_items})
    assert not (prompts & {it["prompt_text"] for it in x_items})


# ================================================================== factorial balance
def test_factorial_balance(pairs):
    A = _A(pairs)
    for f, levels in BB.FACTORS.items():
        cnt = collections.Counter(it["construction"][f] for it in A)
        assert set(cnt) == set(levels)
        assert len(set(cnt.values())) == 1 and sum(cnt.values()) == 128, (f, cnt)
    # every combination of levels is exactly one cell with two pairs
    combos = collections.Counter(tuple(it["construction"][f] for f in BB.FACTOR_ORDER) for it in A)
    assert len(combos) == 64 and set(combos.values()) == {2}
    # pairwise crossing: every pair of factors is balanced
    fs = list(BB.FACTORS)
    for i in range(len(fs)):
        for j in range(i + 1, len(fs)):
            c2 = collections.Counter((it["construction"][fs[i]], it["construction"][fs[j]]) for it in A)
            assert len(set(c2.values())) == 1, (fs[i], fs[j], c2)


def test_object_pairs_balanced(pairs, data):
    A = _A(pairs)
    uses = collections.Counter(frozenset(it["construction"]["object_pair"]) for it in A)
    assert len(uses) == 8 and set(uses.values()) == {16}
    for f, levels in BB.FACTORS.items():
        for lv in levels:
            c = collections.Counter(frozenset(it["construction"]["object_pair"]) for it in A if it["construction"][f] == lv)
            assert len(c) == 8 and len(set(c.values())) == 1, (f, lv, c)
    o1 = collections.Counter(it["construction"]["object_pair"][0] for it in A)
    assert len(o1) == 16 and set(o1.values()) == {8}
    for a, b in data["meta"]["object_pairs"]:
        assert BB.object_words(a)[0] != BB.object_words(b)[0] and BB.object_words(a)[1] != BB.object_words(b)[1]
    assert sorted(o for op in data["meta"]["object_pairs"] for o in op) == sorted(bdx.OBJECTS_X)


def test_name_sets_token_heuristic():
    BB.check_name_sets()
    assert len(BB.NAME_SETS) == 4
    for x, y in BB.NAME_SETS:
        assert BB.whitespace_tokens(x) == BB.whitespace_tokens(y) == 1 and len(x) == len(y)
    assert len({n for s in BB.NAME_SETS for n in s}) == 8


# ================================================================== A/B invariant, within-cell multiset
def test_ab_token_permutation_only_pairing_differs(pairs):
    for p in pairs:
        a, b = p["A"], p["B"]
        assert a["prompt_text"] != b["prompt_text"]
        assert bdx.word_multiset(a["prompt_text"]) == bdx.word_multiset(b["prompt_text"]), p["pair_id"]
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["primary"]["answer"] != b["primary"]["answer"]
        assert a["primary"]["candidates"].index(a["primary"]["answer"]) == 0 and b["primary"]["candidates"].index(b["primary"]["answer"]) == 1
        assert a["primary"]["question"] == b["primary"]["question"] and a["template_id"] == b["template_id"]
        ca, cb = a["construction"], b["construction"]
        for f in BB.FACTORS:
            assert ca[f] == cb[f]
        assert ca["object_pair"] == cb["object_pair"] and ca["binding"] != cb["binding"]
        assert set(ca["binding"].items()) ^ set(cb["binding"].items())  # the two objects swap holders
        # the pairing level is the binding of version A
        X, Y = ca["names"]
        O1, O2 = ca["object_pair"]
        assert ca["binding"] == ({X: O1, Y: O2} if ca["pairing"] == "x_o1" else {X: O2, Y: O1})


def test_within_cell_multiset_fixed_except_object_pair(items):
    by_cell = collections.defaultdict(list)
    for it in items:
        if it["version"] == "A":
            by_cell[it["construction"]["cell"]].append(it)
    assert len(by_cell) == 64
    for cell, its in by_cell.items():
        assert len(its) == 2 and {it["construction"]["k"] for it in its} == {1, 2}
        stripped = [BB.word_multiset_without(it["prompt_text"], it["construction"]["object_pair"]) for it in its]
        assert stripped[0] == stripped[1], cell
        assert frozenset(its[0]["construction"]["object_pair"]) != frozenset(its[1]["construction"]["object_pair"])
        assert bdx.word_multiset(its[0]["prompt_text"]) != bdx.word_multiset(its[1]["prompt_text"])


def test_position_templates(items):
    for it in items:
        c = it["construction"]
        if c["template"] == "pos1":
            assert it["prompt_text"].startswith(BB.LEAD_IN + " ") and c["lead_in"] == BB.LEAD_IN
        else:
            assert not it["prompt_text"].startswith(BB.LEAD_IN) and c["lead_in"] is None
        body = it["prompt_text"][len(BB.LEAD_IN) + 1:] if c["template"] == "pos1" else it["prompt_text"]
        first = c["names"][0] if c["mention_order"] == "x_first" else c["names"][1]
        assert body.startswith(first + " has the ")


# ================================================================== solver, query directions
def test_solver_agreement(items):
    for it in items:
        assert BB.solve_binding(it) == it["primary"]["answer"], it["item_id"]
        if it["construction"]["query_direction"] == "object_to_name":
            assert bd.solve_prompt(it) == it["primary"]["answer"]
            assert BB.solve_name_to_object(it) is None  # no name->object question in the prompt
        else:
            assert BB.solve_name_to_object(it) == it["primary"]["answer"]
    # the extension is not fooled by a prompt that binds the asked name to both candidates
    fake = {"prompt_text": "Emma has the red key. Emma has the blue cup. What does Emma have? Answer with the object only.",
            "primary": {"candidates": ["red key", "blue cup"]}}
    assert BB.solve_name_to_object(fake) is None


def test_query_directions_and_candidate_types(pairs):
    A = _A(pairs)
    by_dir = collections.defaultdict(list)
    for it in A:
        by_dir[it["construction"]["query_direction"]].append(it)
    assert set(by_dir) == {"object_to_name", "name_to_object"} and all(len(v) == 64 for v in by_dir.values())
    names = {n for s in BB.NAME_SETS for n in s}
    for it in by_dir["object_to_name"]:
        c = it["construction"]
        assert set(it["primary"]["candidates"]) == set(c["names"]) <= names
        assert it["prompt_text"].endswith(f"Who has the {c['asked_object']}? Answer with the name only.")
        assert c["asked_object"] == c["object_pair"][0] and it["primary"]["name"].endswith("_owner")
        assert it["secondary"]["objects"][0] == c["asked_object"]
    for it in by_dir["name_to_object"]:
        c = it["construction"]
        assert set(it["primary"]["candidates"]) == set(c["object_pair"]) <= set(bdx.OBJECTS_X)
        assert it["prompt_text"].endswith(f"What does {c['asked_name']} have? Answer with the object only.")
        assert c["asked_name"] == c["names"][0] and it["primary"]["name"] == f"{c['asked_name'].lower()}_object"
    for it in A:
        assert re.search(it["target_answer_regex"], it["primary"]["answer"])
        assert not re.search(it["target_answer_regex"], it["construction"]["other_candidate"])


def test_answer_first_mentioned_bookkeeping(pairs):
    """object_to_name: the answer's mention position flips between A and B (balanced in sign over cells);
    name_to_object: it never flips (the asked name's statement holds the answer in both versions)."""
    flips = collections.Counter((p["A"]["construction"]["query_direction"], CV.order_flip(p)) for p in pairs)
    assert flips[("object_to_name", "first_to_second")] == 32 and flips[("object_to_name", "second_to_first")] == 32
    assert flips[("name_to_object", "none")] == 64
    for p in pairs:
        for v in "AB":
            c = p[v]["construction"]
            assert c["answer_is_first_mentioned"] == (c["first_mentioned_candidate"] == p[v]["primary"]["answer"])
            assert p[v]["prompt_text"].index(c["first_mentioned_candidate"]) < p[v]["prompt_text"].index(c["other_candidate"] if c["first_mentioned_candidate"] == p[v]["primary"]["answer"] else p[v]["primary"]["answer"])


# ================================================================== check_variance on synthetic states
def _write_states(tmp_path, pairs, D, rng, d):
    """Materialise h_A (noise) and h_B = h_A + D as fp32 .pt files, as the X1 capture would."""
    import torch

    sd = tmp_path / "states"
    sd.mkdir()
    for p, diff in zip(pairs, D):
        hA = rng.normal(size=d)
        torch.save(torch.tensor(hA, dtype=torch.float32), sd / f"{p['A']['item_id']}.pt")
        torch.save(torch.tensor(hA + diff, dtype=torch.float32), sd / f"{p['B']['item_id']}.pt")
    return sd


def _planted(pairs, labels, rng, d, factor, level_sign):
    D = rng.normal(size=(len(pairs), d))
    u = np.zeros(d)
    u[0] = 1.0
    s = np.array([level_sign[l] for l in labels[factor]], dtype=float)
    return D + 6.0 * s[:, None] * u


@pytest.mark.parametrize("factor,level_sign", [
    ("template", {"pos0": -1, "pos1": 1}),
    ("mention_order", {"x_first": -1, "y_first": 1}),
    ("order_flip", {"first_to_second": 1, "second_to_first": -1, "none": 0}),
])
def test_check_variance_planted_factor_triggers_stop(tmp_path, pairs, factor, level_sign):
    rng = np.random.default_rng(1)
    d = 32
    labels = CV.factor_labels(pairs)
    D = _planted(pairs, labels, rng, d, factor, level_sign)
    sd = _write_states(tmp_path, pairs, D, rng, d)
    rep = CV.run(states_dir=sd, pairs=pairs, n_relabel=3, seed=0)
    assert rep["stop"] is True and rep["offending_factors"] == [factor]
    assert rep["full"]["factors"][factor]["r2_pc"][0] > 0.9
    for f in CV.STOP_RULE_FACTORS:
        if f != factor:
            assert rep["full"]["factors"][f]["r2_pc"][0] < 0.1, f
    assert rep["verdict"].startswith("STOP")
    # fp32 round trip: load_diffs reproduces D up to float32 precision
    D_back = CV.load_diffs(pairs, sd)
    assert np.allclose(D_back, D, atol=1e-4)
    out = CV.write_report(rep, tmp_path / "out")
    assert all(p.exists() for p in out)
    md = (tmp_path / "out" / "variance_check.md").read_text()
    assert "STOP" in md and f"| {factor} |" in md


def test_check_variance_balanced_noise_passes(tmp_path, pairs):
    rng = np.random.default_rng(2)
    d = 32
    D = rng.normal(size=(len(pairs), d))
    sd = _write_states(tmp_path, pairs, D, rng, d)
    rep = CV.run(states_dir=sd, pairs=pairs, n_relabel=5, seed=0)
    assert rep["stop"] is False and rep["offending_factors"] == []
    for f in CV.ALL_FACTORS:
        assert rep["full"]["factors"][f]["r2_pc"][0] < 0.25, f
    assert rep["full"]["factors"]["template"]["r2_pc"][0] < 0.1
    hl = rep["hewitt_liang_control"]
    assert hl["pass"] is True and hl["mean_acc"] <= 0.55 and len(hl["accs"]) == 5
    assert rep["verdict"].startswith("PASS")
    assert set(rep["by_query_direction"]) == {"object_to_name", "name_to_object"}
    pc = rep["full"]["pca"]
    assert len(pc["explained_ratio"]) == 3 and pc["explained_ratio"][0] < 0.2
    # CLI path with --no-write: exit code 0 on pass
    assert CV.main(["--states-dir", str(sd), "--no-write", "--n-relabel", "2"]) == 0


def test_check_variance_statistics_helpers():
    y = np.array([1.0, 1.0, -1.0, -1.0])
    assert CV.r2_onehot(y, ["a", "a", "b", "b"]) == pytest.approx(1.0)
    assert CV.r2_onehot(y, ["a", "b", "a", "b"]) == pytest.approx(0.0)
    D = np.array([[1.0, 0.0], [1.0, 0.0], [-1.0, 0.0], [-1.0, 0.0]])
    assert CV.eta2_full(D, ["a", "a", "b", "b"]) == pytest.approx(1.0)
    # a perfectly separable label is read by the LOO difference-in-means probe; a shuffled one is not above chance
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 8))
    lab = np.array([1] * 20 + [0] * 20)
    X[:20, 0] += 5
    assert CV.loo_diff_in_means_acc(X, lab) == 1.0
    assert CV.loo_diff_in_means_acc(X, rng.permutation(lab)) <= 0.6


def test_hewitt_liang_control_detects_true_pairing_not_relabelled(pairs):
    """With the pairing direction planted, the true-label probe is perfect and the relabelled control stays at chance."""
    rng = np.random.default_rng(3)
    d = 32
    labels = CV.factor_labels(pairs)
    D = _planted(pairs, labels, rng, d, "pairing", {"x_o1": 1, "x_o2": -1})
    rep = CV.run(D=D, pairs=pairs, n_relabel=5, seed=0)
    assert rep["probe_true_pairing_loo_acc"] == 1.0
    assert rep["hewitt_liang_control"]["pass"] is True
    assert rep["stop"] is True and rep["offending_factors"] == ["pairing"]  # a shared sign direction would be a confound


# ================================================================== guard
def test_zz_results_cache_untouched():
    assert sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*")) == RESULTS_SNAPSHOT
    if CACHE_SNAPSHOT is not None:
        assert sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) == CACHE_SNAPSHOT
