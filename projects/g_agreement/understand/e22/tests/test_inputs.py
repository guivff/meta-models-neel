import json
from pathlib import Path

import numpy as np
import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.e19 import inputs as E19
from projects.g_agreement.understand.e22 import inputs as I


def reseal(directory):
    names = list(json.loads((directory / "INPUT_SEAL.json").read_text())["files"])
    P.seal(directory, names, "INPUTS_FROZEN_SYNTHETIC")


def rebind_source_labels(args, labels):
    path = args["labels"]
    path.unlink()
    P.jsonl(path, labels)
    e3 = path.parent / "e3"
    provenance = json.loads((e3 / "provenance.json").read_text())
    provenance["labels_sha256"] = P.sha(path)
    P.dump(e3 / "provenance.json", provenance)
    reseal(e3)
    e19 = args["e19_inputs"]
    provenance = json.loads((e19 / "provenance.json").read_text())
    provenance["source_e3_input_seal_sha256"] = P.sha(e3 / "INPUT_SEAL.json")
    P.dump(e19 / "provenance.json", provenance)
    reseal(e19)


@pytest.fixture
def source(tmp_path):
    e19 = tmp_path / "e19"
    e3 = tmp_path / "internals" / "e3"
    e19.mkdir()
    e3.mkdir(parents=True)
    items, labels, templates, continuations = [], [], {}, {}
    for feature in I.ROWS:
        templates[feature] = {"values": ["A", "B"], "olens": [["a", "b"], ["alpha", "beta"]],
                              "score_orientation": "value_A_positive"}
        for i in range(84):
            key = f"{feature}-{i:03}"
            cluster = f"{feature}-cluster-{i // 14}"
            items.append({"id": key, "feature": feature, "ids": [1, 2], "split": "test",
                          "parent_index": len(items), "e3_index": len(items), "cluster": cluster})
            labels.append({"id": key, "feature": feature, "split": "test", "cluster": cluster,
                           "value": "A" if i % 2 == 0 else "B"})
        continuations[feature] = {"pairs": [] if feature == "prose_sentiment" else [
            {"A": ")", "B": "(", "A_ids": [8], "B_ids": [7], "tokens_per_candidate": 1},
            {"A": ")\n", "B": "(\n", "A_ids": [8, 198], "B_ids": [7, 198], "tokens_per_candidate": 2}],
            "valid_pairs": [] if feature == "prose_sentiment" else [0, 1]}
    label_path = e3.parent / "labels.DO_NOT_STAGE.jsonl"
    P.jsonl(label_path, labels)
    P.jsonl(e3 / "items.input.jsonl", [{key: value for key, value in item.items() if key not in ("cluster", "e3_index")} for item in items])
    P.dump(e3 / "provenance.json", {"experiment": "E3", "labels_sha256": P.sha(label_path), "w1_input_seal_sha256": "w1-seal"})
    P.seal(e3, ["items.input.jsonl", "provenance.json"], "INPUTS_FROZEN_E3")
    P.jsonl(e19 / "items.input.jsonl", items)
    np.save(e19 / "acts44.npy", np.arange(420 * 3, dtype=np.float32).reshape(420, 3))
    P.dump(e19 / "templates.json", templates)
    P.dump(e19 / "continuation_pairs.json", {"rows": continuations, "missing_rows": ["prose_sentiment"], "oracle_prefix": "- "})
    P.dump(e19 / "random_donors.json", E19.donor_map(items))
    P.dump(e19 / "random_seeds.json", {"donor_seed": 20261025})
    P.dump(e19 / "item_order.json", [item["id"] for item in items])
    P.dump(e19 / "provenance.json", {"experiment": "E19", "layer": 44,
        "source_e3_input_seal_sha256": P.sha(e3 / "INPUT_SEAL.json"), "source_w1_input_seal_sha256": "w1-seal"})
    P.seal(e19, [p.name for p in e19.iterdir()], "INPUTS_FROZEN_E19")
    registration = tmp_path / "REGISTRATION.md"
    registration.write_text("§114 E22 registered before any E22 scores")
    return {"e19_inputs": e19, "labels": label_path, "registration": registration, "out": tmp_path / "e22"}


def test_prepared_worker_is_label_free_and_donors_have_registered_relations(source):
    receipt = I.prepare(**source)
    data = I.load(source["out"])
    labels = P.rows(Path(receipt["analysis_labels"]))
    lookup = {row["id"]: row for row in labels}
    assert len(labels) == len(data["items"]) == 420
    assert Path(receipt["analysis_labels"]).parent == source["out"].parent
    assert not list(source["out"].rglob("*.DO_NOT_STAGE.*"))
    assert all("value" not in item and "y" not in item for item in data["items"])
    for name in ("items.input.jsonl", "acts44.npy", "templates.json", "continuation_pairs.json", "item_order.json"):
        assert P.sha(source["out"] / name) == P.sha(source["e19_inputs"] / name)
    for arm, records in data["donors"].items():
        assert len(records) == 420
        for record in records:
            recipient, donor = lookup[record["id"]], lookup[record["donor_id"]]
            assert record["id"] != record["donor_id"]
            assert recipient["feature"] == donor["feature"] == record["feature"]
            assert (recipient["y"] != donor["y"]) == (arm == "opposite")
            assert data["items"][record["donor_index"]]["id"] == record["donor_id"]
    assert data["provenance"]["labels_sha256"] == P.sha(receipt["analysis_labels"])
    private_seal = json.loads(Path(receipt["analysis_labels_seal"]).read_text())
    assert private_seal["input_seal_sha256"] == P.sha(source["out"] / "INPUT_SEAL.json")
    assert all(row["y"] == int(row["value"] == "A") for row in labels)


def test_donor_map_repeatability_permutation_invariance_and_draw_order(source):
    receipt = I.prepare(**source)
    data = I.load(source["out"])
    labels = P.rows(receipt["analysis_labels"])
    expected = I.donor_maps(data["items"], labels)
    assert expected == data["donors"]
    permuted = I.donor_maps(data["items"][::-1], labels[::-1])
    for arm in I.DONOR_ARMS:
        assert {r["id"]: r["donor_id"] for r in expected[arm]} == {r["id"]: r["donor_id"] for r in permuted[arm]}
    # Independent first two draws lock down opposite-then-same stream consumption.
    first_feature = sorted(I.ROWS)[0]
    row_labels = sorted((row for row in labels if row["feature"] == first_feature), key=lambda row: row["id"])
    recipient = row_labels[0]
    candidates = {"opposite": [r["id"] for r in row_labels if r["y"] != recipient["y"]],
                  "same": [r["id"] for r in row_labels if r["y"] == recipient["y"] and r["id"] != recipient["id"]]}
    rng = np.random.default_rng(20261025)
    for arm in ("opposite", "same"):
        draw = candidates[arm][int(rng.integers(len(candidates[arm])))]
        actual = next(r["donor_id"] for r in expected[arm] if r["id"] == recipient["id"])
        assert actual == draw
    assert I.donor_maps(data["items"], labels, seed=20261026) != expected


def test_bad_source_label_hash_is_rejected_before_label_parsing(source, monkeypatch):
    with source["labels"].open("a") as stream:
        stream.write("\n")
    original = P.rows
    def guard(path):
        assert Path(path) != source["labels"], "mismatched labels must never be parsed"
        return original(path)
    monkeypatch.setattr(P, "rows", guard)
    with pytest.raises(ValueError, match="sealed E3 source hash"):
        I.prepare(**source)
    assert not source["out"].exists()


def test_missing_label_file_fails_without_staging(source):
    source["labels"].unlink()
    with pytest.raises(FileNotFoundError):
        I.prepare(**source)
    assert not source["out"].exists()


def test_hash_valid_missing_label_record_is_rejected(source):
    rows = P.rows(source["labels"])
    rebind_source_labels(source, rows[:-1])
    with pytest.raises(ValueError, match="cover every E22 recipient"):
        I.prepare(**source)
    assert not source["out"].exists()


def test_hash_valid_unbalanced_label_population_is_rejected(source):
    rows = P.rows(source["labels"])
    rows[0]["value"] = "B"
    rebind_source_labels(source, rows)
    with pytest.raises(ValueError, match="42/42"):
        I.prepare(**source)


def test_group_balance_is_checked_even_when_row_balance_holds(source):
    rows = P.rows(source["labels"])
    rows[0]["value"], rows[15]["value"] = "B", "A"
    rebind_source_labels(source, rows)
    with pytest.raises(ValueError, match="7/7"):
        I.prepare(**source)


def test_wrong_e3_source_seal_is_rejected_before_labels(source, monkeypatch):
    path = source["e19_inputs"] / "provenance.json"
    provenance = json.loads(path.read_text())
    provenance["source_e3_input_seal_sha256"] = "another-e3-run"
    P.dump(path, provenance)
    reseal(source["e19_inputs"])
    original = P.rows
    def guard(path):
        assert Path(path) != source["labels"]
        return original(path)
    monkeypatch.setattr(P, "rows", guard)
    with pytest.raises(ValueError, match="frozen lineage"):
        I.prepare(**source)
