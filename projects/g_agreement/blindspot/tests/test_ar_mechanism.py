"""Offline scientific contracts for BRIEF_BLINDSPOT §§71–73 and §80.

The fixtures are numerical examples, never model results or pilot evidence.
"""
from collections import Counter

import numpy as np
import pytest
import torch

from projects.g_agreement.blindspot import ar_tests as ar


def definitions():
    return {
        "table_column": {
            "row_class": "count-like",
            "values": ["first", "later"],
            "descriptions": ["the first table column", "a later table column"],
        },
        "parenthesis": {
            "row_class": "state-like",
            "values": ["inside", "outside"],
            "descriptions": ["inside a parenthesis", "outside any parenthesis"],
        },
    }


def test_statement_bank_has_two_phrasings_ten_contexts_per_value():
    records, labels = ar.freeze_text_records(definitions())
    assert (records, labels) == ar.freeze_text_records(definitions())
    assert len(records) == len(labels) == 80
    by_id = {row["id"]: row for row in labels}
    assert len(by_id) == 80
    assert {row["id"] for row in records} == set(by_id)
    assert Counter(row["feature"] for row in records) == {
        "table_column": 40, "parenthesis": 40,
    }
    for record in records:
        assert record["feature"] == by_id[record["id"]]["feature"]
        assert record["text"].strip()
        assert not {"value", "value_name", "phrasing", "context"} & record.keys()
    for feature in definitions():
        subset = [row for row in labels if row["feature"] == feature]
        assert Counter(row["value"] for row in subset) == {1: 20, 0: 20}
        assert len({row["phrasing"] for row in subset}) == 2
        assert len({row["context"] for row in subset}) == 10
        cells = Counter((row["value"], row["phrasing"], row["context"]) for row in subset)
        assert len(cells) == 40 and set(cells.values()) == {1}


def fidelity_fixture():
    labels = np.repeat([1, 0], 20)
    # The second coordinate is an intentionally irrelevant nuisance direction.
    reconstructed = torch.tensor(
        [[1.5, float(i)] for i in range(20)]
        + [[-0.5, float(100 + i)] for i in range(20)]
    )
    h = torch.tensor([[4., 5.], [2., 5.], [-2., 5.], [0., 5.]])
    y = np.array([1, 1, 0, 0])
    direction = torch.tensor([2., 0.])
    return reconstructed, labels, h, y, direction


def test_fidelity_is_signed_ratio_of_real_and_reconstructed_class_gaps():
    reconstructed, labels, h, y, direction = fidelity_fixture()
    result = ar.fidelity(reconstructed, labels, h, y, direction, n_boot=100, seed=7)
    # The implementation reports projection on a unit-normalized direction.
    assert result["numerator"] == pytest.approx(2.)
    assert result["denominator"] == pytest.approx(4.)
    assert result["fidelity"] == pytest.approx(.5)
    assert result["ci95"] == pytest.approx([.5, .5])
    reversed_direction = ar.fidelity(
        reconstructed, labels, h, y, -3 * direction, n_boot=100, seed=7,
    )
    assert reversed_direction["fidelity"] == pytest.approx(.5)
    assert reversed_direction["denominator"] == pytest.approx(-4.)


def test_fidelity_does_not_absolute_value_an_inverted_reconstruction():
    reconstructed, labels, h, y, direction = fidelity_fixture()
    reconstructed[:, 0] *= -1
    result = ar.fidelity(reconstructed, labels, h, y, direction, n_boot=100, seed=7)
    assert result["fidelity"] == pytest.approx(-.5)
    assert result["ci95"] == pytest.approx([-.5, -.5])


def test_fidelity_rejects_zero_real_class_mean_gap():
    reconstructed, labels, h, y, direction = fidelity_fixture()
    h[:, 0] = 1
    with pytest.raises(ValueError):
        ar.fidelity(reconstructed, labels, h, y, direction, n_boot=10)


def test_w3_residual_is_per_item_reconstruction_error_not_projection():
    h = torch.tensor([[3., 4.], [1., -2.]])
    reconstructed = torch.tensor([[2., 1.], [-3., 5.]])
    residual = ar.residual_activations(h, reconstructed)
    assert torch.equal(residual, torch.tensor([[1., 3.], [4., -7.]]))
    assert torch.equal(residual + reconstructed, h)
    assert not torch.allclose((residual * reconstructed).sum(-1), torch.zeros(2))


def swap_fixture():
    h = torch.tensor([[3., 4., 1.], [2., -1., 3.], [-2., 5., 1.], [4., 2., -1.]])
    reconstructed = torch.tensor([[1., 2., .5], [.5, -2., 1.], [-1., 1., .5], [2., .5, -2.]])
    pairs = [
        {"id": "pair_a", "feature": "table_column", "recipient": 0, "donor": 1, "random": 2},
        {"id": "pair_b", "feature": "table_column", "recipient": 1, "donor": 0, "random": 3},
    ]
    return h, reconstructed, pairs


def test_swap_and_all_three_controls_use_recipient_norm():
    h, reconstructed, pairs = swap_fixture()
    h_before, reconstructed_before = h.clone(), reconstructed.clone()
    result = ar.swap_arms(h, reconstructed, pairs)
    assert set(result) == {"swap", "self", "random", "ar_only"}
    recipients = torch.tensor([0, 1])
    donor = torch.tensor([1, 0])
    random = torch.tensor([2, 3])
    residual = h - reconstructed
    expected_raw = {
        "swap": reconstructed[recipients] + residual[donor],
        "self": h[recipients],
        "random": reconstructed[recipients] + residual[random],
        "ar_only": reconstructed[recipients],
    }
    target_norm = h[recipients].norm(dim=-1, keepdim=True)
    for arm, value in result.items():
        assert torch.allclose(value.norm(dim=-1, keepdim=True), target_norm, atol=1e-6)
        expected = expected_raw[arm] / expected_raw[arm].norm(dim=-1, keepdim=True) * target_norm
        assert torch.allclose(value, expected, atol=1e-6), arm
    assert torch.allclose(result["self"], h[recipients], atol=1e-6)
    assert torch.equal(h, h_before) and torch.equal(reconstructed, reconstructed_before)


def test_zero_vector_swap_is_rejected_instead_of_silently_rescaled():
    h, reconstructed, pairs = swap_fixture()
    reconstructed[0] = 0
    with pytest.raises(ValueError):
        ar.swap_arms(h, reconstructed, pairs)


def test_w4_calls_upstream_nla_scorer_with_exact_frozen_phrasings(monkeypatch):
    import mats.readers.nla as upstream

    h, reconstructed, pairs = swap_fixture()
    expected = ar.swap_arms(h, reconstructed, pairs)
    templates = {"table_column": {"nla": [["first A", "later B"], ["first C", "later D"]]}}
    nla = object()
    calls = []

    def score(actual_nla, acts, actual_pairs, batch=32):
        assert actual_nla is nla
        assert actual_pairs is templates["table_column"]["nla"]
        assert batch == 8
        calls.append(acts.clone())
        return torch.stack([acts[:, 0], acts[:, 1] + 10])

    monkeypatch.setattr(upstream, "paired_logodds_templates", score)
    rows = ar.score_swaps(nla, h, reconstructed, pairs, templates, batch=8)
    assert len(calls) == 4
    assert len(rows) == 8
    index = {(row["id"], row["arm"]): row for row in rows}
    assert len(index) == 8
    for arm in expected:
        assert any(torch.allclose(call, expected[arm]) for call in calls)
        for k, pair in enumerate(pairs):
            row = index[pair["id"], arm]
            assert row["feature"] == "table_column"
            assert row["scores"] == pytest.approx([expected[arm][k, 0].item(), expected[arm][k, 1].item() + 10])
            assert row["construction_block"] == 44
            assert row["nla_native_block"] == 42
            assert row["site"] == "OFF-NATIVE"


def test_w4_refuses_single_phrasing_pair_before_scoring(monkeypatch):
    import mats.readers.nla as upstream

    def no_score(*args, **kwargs):
        pytest.fail("a noncompliant template bank reached the reader")

    monkeypatch.setattr(upstream, "paired_logodds_templates", no_score)
    h, reconstructed, pairs = swap_fixture()
    with pytest.raises(ValueError):
        ar.score_swaps(object(), h, reconstructed, pairs, {"table_column": {"nla": [["A", "B"]]}})


def test_w3_rule_requires_both_blindspot_retention_and_semantic_drop():
    blind = [
        {"row_class": "count-like", "blindspot": True, "evaluable": True,
         "original_auroc": 1., "residual_auroc": .95 if i < 7 else .7}
        for i in range(10)
    ]
    semantic = [
        {"row_class": "semantic", "blindspot": False, "evaluable": True,
         "original_auroc": 1., "residual_auroc": .8 if i < 7 else .95}
        for i in range(10)
    ]
    decision = ar.w3_decision(blind + semantic)
    assert decision["status"] == "CONFIRMED"
    for group in ("blindspot_retention", "semantic_drop"):
        assert len(decision[group]["wilson_ci95"]) == 2
        assert decision[group]["wilson_ci95"][0] < .7 < decision[group]["wilson_ci95"][1]
    blind[0]["residual_auroc"] = .7
    assert ar.w3_decision(blind + semantic)["status"] == "NOT MET"
    blind[0]["residual_auroc"] = .95
    semantic[0]["residual_auroc"] = .95
    assert ar.w3_decision(blind + semantic)["status"] == "NOT MET"


def test_w3_ratio_uses_raw_auroc_and_excludes_unevaluable_rows():
    # .77 >= .9 * .85 even though the above-chance fraction is below .9.
    rows = [
        {"row_class": "state-like", "blindspot": True, "evaluable": True,
         "original_auroc": .85, "residual_auroc": .77},
        {"row_class": "semantic", "blindspot": False, "evaluable": True,
         "original_auroc": 1., "residual_auroc": .8},
        {"row_class": "state-like", "blindspot": True, "evaluable": False,
         "original_auroc": 1., "residual_auroc": .5},
    ]
    assert ar.w3_decision(rows)["status"] == "CONFIRMED"


def test_w2_and_s2_use_their_registered_correlations():
    rows = [
        {"feature": f"f{i}", "fidelity": i / 10, "oracle_auroc": .5 + i / 20,
         "probe_auroc": 1., "row_class": "semantic", "evaluable": True}
        for i in range(10)
    ]
    assert ar.w2_decision(rows)["status"] == "CONFIRMED"
    assert ar.s2_decision(rows)["status"] == "CONFIRMED"
    # The S2 second rule must independently fail if the probe–Oracle gap rises.
    rising_gap = [
        {**row, "oracle_auroc": .65 + .01 * i, "probe_auroc": .85 + .015 * i}
        for i, row in enumerate(rows)
    ]
    assert ar.w2_decision(rising_gap)["status"] == "CONFIRMED"
    assert ar.s2_decision(rising_gap)["status"] == "NOT MET"


def pairing_fixture():
    items, labels = [], {}
    for family in range(12):
        for repeat in range(2):
            for value in ("A", "B"):
                key = f"test:{family}:{repeat}:{value}"
                items.append({"id": key, "feature": "f"})
                labels[key] = {
                    "split": "test", "domain": "table", "value": value,
                    "template_family": f"template_{family}", "length_bin": 2,
                }
    # Dev items are eligible only for the random control, never main test pairs.
    for i in range(30):
        key = f"dev:{i}"
        items.append({"id": key, "feature": "f"})
        labels[key] = {
            "split": "dev", "domain": "table", "value": "A" if i % 2 else "B",
            "template_family": "dev_template", "length_bin": 7,
        }
    items.append({"id": "other_domain", "feature": "g"})
    labels["other_domain"] = {
        "split": "test", "domain": "python", "value": "A",
        "template_family": "template_0", "length_bin": 2,
    }
    return items, labels


def test_swap_pair_preparation_has_40_matched_directed_test_pairs():
    items, labels = pairing_fixture()
    pairs = ar.prepare_swap_pairs(items, labels, ["f"], seed=31)
    assert len(pairs) == 40
    assert len({p["id"] for p in pairs}) == 40
    assert len({(p["recipient"], p["donor"]) for p in pairs}) == 40
    assert pairs == ar.prepare_swap_pairs(items, labels, ["f"], seed=31)
    for pair in pairs:
        recipient, donor, random = [labels[items[pair[k]]["id"]] for k in ("recipient", "donor", "random")]
        assert recipient["split"] == donor["split"] == "test"
        assert recipient["value"] != donor["value"]
        for field in ("domain", "template_family", "length_bin"):
            assert recipient[field] == donor[field]
        assert pair["cluster"] == recipient["template_family"]
        assert random["domain"] == recipient["domain"]
        assert pair["random"] not in (pair["recipient"], pair["donor"])


def test_random_control_donor_selection_does_not_inspect_its_value():
    items, labels = pairing_fixture()
    original = ar.prepare_swap_pairs(items, labels, ["f"], seed=31)
    changed = {
        key: {**label, "value": "unobserved"} if label["split"] == "dev" else dict(label)
        for key, label in labels.items()
    }
    assert any(labels[items[p["random"]]["id"]]["split"] == "dev" for p in original)
    assert ar.prepare_swap_pairs(items, changed, ["f"], seed=31) == original


def test_not_enough_matched_test_pairs_fails_instead_of_repeating_pairs():
    items, labels = pairing_fixture()
    # 12 families with two items per value give 12 * 8 directed pairs.
    with pytest.raises(ValueError, match="eligible directed test pairs"):
        ar.prepare_swap_pairs(items, labels, ["f"], n_pairs=97)


@pytest.mark.parametrize("corruption", ["missing", "duplicate", "wrong_site", "wrong_feature"])
def test_swap_analysis_rejects_incomplete_or_misidentified_score_grid(corruption):
    items, labels = pairing_fixture()
    pairs = ar.prepare_swap_pairs(items, labels, ["f"], seed=31)
    scores = [
        {"id": p["id"], "feature": p["feature"], "arm": arm, "scores": [0., 0.],
         "construction_block": 44, "nla_native_block": 42, "site": "OFF-NATIVE"}
        for p in pairs for arm in ("swap", "self", "random", "ar_only")
    ]
    if corruption == "missing":
        scores.pop()
    elif corruption == "duplicate":
        scores.append(dict(scores[0]))
    elif corruption == "wrong_site":
        scores[0]["construction_block"] = 42
    else:
        scores[0]["feature"] = "another_row"
    with pytest.raises(ValueError):
        ar.analyse_swap_scores(
            scores, pairs, labels, items,
            {"f": {"values": ["A", "B"], "row_class": "count-like"}},
        )


@pytest.mark.parametrize("row_class,follow", [("count-like", "donor"), ("semantic", "recipient")])
def test_swap_analysis_uses_donor_for_blindspot_and_recipient_for_semantic(row_class, follow):
    items, labels = pairing_fixture()
    pairs = ar.prepare_swap_pairs(items, labels, ["f"], seed=31)
    scores = []
    for pair in pairs:
        for arm in ("swap", "self", "random", "ar_only"):
            if arm in ("random", "ar_only"):
                score = 0.
            else:
                index = pair[follow if arm == "swap" else "recipient"]
                score = 2. if labels[items[index]["id"]]["value"] == "A" else -2.
            scores.append({
                "id": pair["id"], "feature": "f", "arm": arm,
                "scores": [score - 1., score + 1.], "construction_block": 44,
                "nla_native_block": 42, "site": "OFF-NATIVE",
            })
    result = ar.analyse_swap_scores(
        scores, pairs, labels, items,
        {"f": {"values": ["A", "B"], "row_class": row_class}},
    )
    assert result["site"] == "OFF-NATIVE"
    assert result["status"] == "PER_ROW_RULES_REPORTED"
    row = result["rows"][0]
    assert row["rule_met"] is True
    assert row["arms"]["swap"][follow]["auroc"] == 1.
    assert row["arms"]["self"]["recipient"]["auroc"] == 1.
    for arm in ("random", "ar_only"):
        assert row["arms"][arm]["recipient"]["auroc"] == .5
        assert row["arms"][arm]["donor"]["auroc"] == .5
    opposite = "recipient" if follow == "donor" else "donor"
    assert row["arms"]["swap"][opposite]["auroc"] == 0.
