import json
from pathlib import Path

import numpy as np
import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.e19 import inputs as I


@pytest.fixture
def sources(tmp_path):
    e3, e15, analysis, scores = [tmp_path / name for name in ("e3", "e15", "analysis", "scores")]
    for directory in (e3, e15, analysis, scores):
        directory.mkdir()
    rows, templates = [], {}
    for feature in I.ROWS:
        templates[feature] = {"olens": [["- a", "- b"], ["- alpha", "- beta"]],
            "score_orientation": "value_A_positive", "values": ["a", "b"]}
        for split in ("dev", "test"):
            for i in range(84):
                rows.append({"id": f"{feature}-{split}-{i:03}", "feature": feature,
                    "split": split, "ids": [1, 2], "parent_index": len(rows)})
    P.jsonl(e3 / "items.input.jsonl", rows)
    w1_bank = tmp_path / "w1"
    w1_bank.mkdir()
    P.jsonl(w1_bank / "items.DO_NOT_STAGE.jsonl", [
        {**row, "cluster": f"{row['feature']}-{row['split']}-{int(row['id'][-3:]) // 14}",
         "value": "unused-secret-truth", "text": 'ignored "cluster": "fake"',
         "meta": {"cluster": "wrong-nested-cluster"}} for row in rows])
    P.dump(w1_bank / "manifest.json", {"files": {"items.DO_NOT_STAGE.jsonl": P.sha(w1_bank / "items.DO_NOT_STAGE.jsonl")}})
    P.seal(w1_bank, ["manifest.json"], "INPUTS_FROZEN_W1")
    P.dump(e3 / "templates.json", templates)
    np.save(e3 / "acts44.npy", np.arange(len(rows) * 3, dtype=np.float32).reshape(-1, 3))
    P.dump(e3 / "provenance.json", {"experiment": "E3", "w1_input_seal_sha256": P.sha(w1_bank / "INPUT_SEAL.json")})
    P.seal(e3, ["items.input.jsonl", "templates.json", "acts44.npy", "provenance.json"], "INPUTS_FROZEN_E3")
    pairs = {feature: {"consequence": "frozen toy consequence", "pairs": [
        {"A": ")", "B": "(", "A_ids": [8], "B_ids": [7], "tokens_per_candidate": 1},
        {"A": ")\n", "B": "(\n", "A_ids": [8, 198], "B_ids": [7, 198], "tokens_per_candidate": 2}
    ]} for feature in I.ROWS if feature != "prose_sentiment"}
    P.dump(e15 / "pairs.json", {"section": 105, "oracle_prefix": "- ", "orientation": "value A positive", "rows": pairs})
    P.dump(e15 / "plan.json", {"labels_sha256": "opaque-label-hash-only"})
    P.seal(e15, ["pairs.json", "plan.json"], "INPUTS_FROZEN_E15")
    P.dump(scores / "provenance.json", {"input_seal_sha256": P.sha(e15 / "INPUT_SEAL.json")})
    P.seal(scores, ["provenance.json"], "SCORES_SEALED_E15")
    P.dump(analysis / "metrics.json", {"experiment": "E15", "labels_sha256": "opaque-label-hash-only",
        "score_seal_sha256": P.sha(scores / "SCORE_SEAL.json"), "rows": [
        {"feature": feature, "base_dev_pair_auroc": [.81, .79], "valid_pairs": [0],
         "readers": {"irrelevant_test_metrics": "must not be copied"}} for feature in pairs]})
    P.dump(analysis / "ANALYSIS_SEAL.json", {"files": {"metrics.json": P.sha(analysis / "metrics.json")}})
    registration = tmp_path / "REGISTRATION.md"
    registration.write_text("§111 E19 frozen registration")
    return {"e3_inputs": e3, "e15_stage": e15, "registration": registration, "out": tmp_path / "prepared",
            "e15_analysis": analysis, "e15_scores": scores, "w1_bank": w1_bank}


def test_freeze_preserves_e3_order_vectors_and_original_pairs_without_labels(sources, monkeypatch):
    original_read = Path.read_text
    def no_labels(path, *args, **kwargs):
        assert "labels.DO_NOT_STAGE" not in path.name
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", no_labels)
    receipt = I.prepare(**sources)
    frozen = I.load(sources["out"])
    assert receipt["n_items"] == 420 and receipt["labels_read"] is False
    expected = [x for x in P.rows(sources["e3_inputs"] / "items.input.jsonl") if x["split"] == "test"]
    assert [x["id"] for x in frozen["items"]] == [x["id"] for x in expected]
    indices = [x["e3_index"] for x in frozen["items"]]
    assert indices == sorted(indices)
    np.testing.assert_array_equal(frozen["activations"], np.load(sources["e3_inputs"] / "acts44.npy")[indices])
    source_pairs = json.loads((sources["e15_stage"] / "pairs.json").read_text())["rows"]
    for feature in I.ROWS[:-1]:
        row = frozen["continuations"]["rows"][feature]
        assert row["pairs"] == source_pairs[feature]["pairs"]
        assert row["valid_pairs"] == [0] and row["primary_status"] == "EVALUABLE"
        assert "readers" not in row
    missing = frozen["continuations"]["rows"]["prose_sentiment"]
    assert missing["status"] == "NOT_APPLICABLE_NO_FROZEN_E15_PAIRS"
    assert missing["pairs"] == []
    assert frozen["random_seeds"]["random_direction_seeds"] == [20261025, 20261026, 20261027]
    assert not list(sources["out"].glob("*DO_NOT_STAGE*"))
    assert all("value" not in item and "text" not in item and "meta" not in item for item in frozen["items"])
    for feature in I.ROWS:
        assert len({item["cluster"] for item in frozen["items"] if item["feature"] == feature}) == 6


def test_donors_are_seeded_same_row_nonself_and_order_independent(sources):
    I.prepare(**sources)
    data = I.load(sources["out"])
    items, donors = data["items"], data["donors"]
    assert donors == I.donor_map(items)
    assert {d["id"]: d["donor_id"] for d in donors} == {d["id"]: d["donor_id"] for d in I.donor_map(items[::-1])}
    for donor in donors:
        recipient, source = items[donor["recipient_index"]], items[donor["donor_index"]]
        assert recipient["id"] != source["id"]
        assert source["id"] == donor["donor_id"]
        assert recipient["feature"] == source["feature"]
    assert I.donor_map(items, I.DONOR_SEED + 1) != donors


def test_rejects_mutated_e3_activations_before_output_creation(sources):
    path = sources["e3_inputs"] / "acts44.npy"
    values = np.load(path)
    values[0, 0] += 1
    np.save(path, values)
    with pytest.raises(ValueError, match="seal mismatch"):
        I.prepare(**sources)
    assert not sources["out"].exists()


def test_rejects_wrong_e15_dev_validity_lineage(sources):
    path = sources["e15_scores"] / "provenance.json"
    P.dump(path, {"input_seal_sha256": "different-E15-inputs"})
    P.seal(sources["e15_scores"], ["provenance.json"], "SCORES_SEALED_E15")
    with pytest.raises(ValueError, match="lineage mismatch"):
        I.prepare(**sources)


def test_rejects_e15_pair_validity_changed_after_dev(sources):
    path = sources["e15_analysis"] / "metrics.json"
    data = json.loads(path.read_text())
    data["rows"][0]["valid_pairs"] = [0, 1]
    P.dump(path, data)
    P.dump(sources["e15_analysis"] / "ANALYSIS_SEAL.json", {"files": {"metrics.json": P.sha(path)}})
    with pytest.raises(ValueError, match="registered dev rule"):
        I.prepare(**sources)


def test_rejects_underfull_test_population_even_when_resealed(sources):
    path = sources["e3_inputs"] / "items.input.jsonl"
    rows = P.rows(path)
    path.unlink()
    P.jsonl(path, rows[:-1])
    P.seal(sources["e3_inputs"], ["items.input.jsonl", "templates.json", "acts44.npy", "provenance.json"], "INPUTS_FROZEN_E3")
    with pytest.raises(ValueError, match="all 84 test items"):
        I.prepare(**sources)


def test_metadata_scanner_skips_truth_text_and_nested_group_keys():
    line = '{"value":{"secret":[1,2,{"cluster":"fake"}]},"id":"one","text":"\\\"cluster\\\":\\\"wrong\\\"", "feature":"row", "meta":{"id":"fake"}, "split":"test","cluster":"real"}'
    assert I.metadata_only(line) == {"id": "one", "feature": "row", "split": "test", "cluster": "real"}
    with pytest.raises(ValueError, match="duplicate"):
        I.metadata_only('{"id":"one","feature":"row","split":"test","cluster":"a","cluster":"b"}')
