import json
from pathlib import Path

import numpy as np
import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.inputs import (
    STRUCTURE_ROWS, join_labels, load_inputs, prepare_inputs,
)


@pytest.fixture
def upstream(tmp_path):
    bank, target, w1 = [tmp_path / n for n in ("bank", "target", "w1")]
    for directory in (bank, target, w1):
        directory.mkdir()
    features = list(STRUCTURE_ROWS) + [f"semantic_{i}" for i in range(9)] + [f"other_{i}" for i in range(15)]
    templates, items, labels, cells, directions, direction_meta = {}, [], [], [], {}, []
    for feature in features:
        row_class = "semantic" if feature.startswith("semantic") else "state-like"
        templates[feature] = {"class": row_class, "domain": "toy", "kind": "binary",
            "score_orientation": "value_A_positive", "values": ["a", "b"],
            "olens": [["- A", "- B"], ["- Alpha", "- Beta"]],
            "nla": [["A", "B"], ["Alpha", "Beta"]],
            "jlens": [["a", "b"], ["alpha", "beta"]]}
        for reader, layer in (("olens", 44), ("nla", 42), ("jlens", 44)):
            cells.append({"feature": feature, "reader": reader, "layer": layer, "class": row_class,
                          "status": "EVALUABLE", "true": {"auroc": 0.6}})
        for layer in (42, 44):
            key = f"{feature}__L{layer}"
            directions[key + "__unit"] = np.array([1., 0., 0.], dtype=np.float32)
            direction_meta.append({"feature": feature, "layer": layer, "array_prefix": key,
                "fit_split": "dev", "orientation_flipped": False, "positive_value": "a",
                "negative_value": "b", "positive_label": "value_A", "dev_n": 84})
        for cluster in range(12):
            for pair in range(7):
                for value in ("a", "b"):
                    key = f"{feature}_{cluster}_{pair}_{value}"
                    items.append({"id": key, "feature": feature, "ids": [1, 2, 3]})
                    labels.append({"id": key, "feature": feature, "class": row_class, "domain": "toy",
                        "cluster": f"{feature}_{cluster}", "split": "dev" if cluster < 6 else "test", "value": value})
    label_path = tmp_path / "labels.DO_NOT_STAGE.jsonl"
    P.jsonl(label_path, labels)
    P.jsonl(bank / "items.input.jsonl", items)
    P.dump(bank / "templates.json", templates)
    P.dump(bank / "provenance.json", {"labels_sha256": P.sha(label_path)})
    P.seal(bank, ["items.input.jsonl", "templates.json", "provenance.json"], "INPUTS_FROZEN_W1")
    for layer in (42, 44):
        np.save(target / f"acts{layer}.npy", np.arange(len(items) * 3, dtype=np.float32).reshape(-1, 3) + layer)
    P.dump(target / "items.order.json", [it["id"] for it in items])
    P.dump(target / "provenance.target.json", {"input_seal_sha256": P.sha(bank / "INPUT_SEAL.json")})
    P.jsonl(target / "scores.target.jsonl", [{"id": it["id"], "reader": reader, "layer": 44,
        "arm": "true", "scores": [0.25, -0.5], "status": "COMPLETE", "score_kind": "native"}
        for it in items for reader in ("olens", "jlens")])
    P.seal(target, ["acts42.npy", "acts44.npy", "items.order.json", "provenance.target.json", "scores.target.jsonl"], "SCORES_SEALED_W1")
    nla = tmp_path / "nla"
    nla.mkdir()
    P.jsonl(nla / "scores.nla.jsonl", [{"id": it["id"], "reader": "nla", "layer": 42,
        "arm": "true", "scores": [0.5, -0.25], "status": "COMPLETE", "score_kind": "native"} for it in items])
    P.seal(nla, ["scores.nla.jsonl"], "SCORES_SEALED_W1")
    metrics = {"input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"),
        "reader_seals": [P.sha(target / "SCORE_SEAL.json"), P.sha(nla / "SCORE_SEAL.json")],
        "rows": cells, "w1": {"blindspot_features": list(STRUCTURE_ROWS)}}
    P.dump(w1 / "metrics.json", metrics)
    P.dump(w1 / "rule_i_rows.json", {"features": list(STRUCTURE_ROWS),
        "input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"), "metrics_sha256": P.sha(w1 / "metrics.json")})
    P.dump(w1 / "probe_directions.json", {"fit_split": "dev", "rows": direction_meta})
    np.savez(w1 / "probe_directions.npz", **directions)
    P.dump(w1 / "activations.json", {"item_order_sha256": P.sha(target / "items.order.json"),
        "files": [{"layer": layer, "sha256": P.sha(target / f"acts{layer}.npy"),
                   "shape": [len(items), 3], "dtype": "float32"} for layer in (42, 44)]})
    _seal_analysis(w1)
    return {"bank": bank, "target": target, "w1": w1, "labels": label_path, "out": tmp_path / "frozen"}


def _seal_analysis(w1):
    names = ("metrics.json", "rule_i_rows.json", "probe_directions.json", "probe_directions.npz", "activations.json")
    P.dump(w1 / "ANALYSIS_SEAL.json", {"files": {n: P.sha(w1 / n) for n in names}})


def test_freeze_preserves_full_population_order_and_native_arrays(upstream):
    receipt = prepare_inputs(**upstream)
    source = np.load(upstream["target"] / "acts42.npy")
    for name, expected in (("e3", 4200), ("e4", 2100), ("e9", 3360)):
        package = load_inputs(upstream["out"] / name)
        assert len(package["items"]) == expected
        assert receipt["experiments"][name]["n_items"] == expected
        indices = [it["parent_index"] for it in package["items"]]
        assert indices == sorted(indices)
        np.testing.assert_array_equal(package["activations"][42], source[indices])
        assert not list((upstream["out"] / name).glob("*.DO_NOT_STAGE.*"))
        assert all("value" not in it and "cluster" not in it for it in package["items"])
        assert len(package["directions"]) == (80 if name == "e9" else 50)
        assert len(package["native_reference"]) == expected * 3
        assert {r["reader"] for r in package["native_reference"]} == {"olens", "nla", "jlens"}
        if name != "e3":
            assert {it["split"] for it in package["items"]} == {"test"}
    assert Path(receipt["local_labels"]).is_file()


def test_rejects_activation_tampering_before_output_creation(upstream):
    path = upstream["target"] / "acts42.npy"
    array = np.load(path)
    array[0, 0] += 1
    np.save(path, array)
    with pytest.raises(ValueError, match="seal mismatch"):
        prepare_inputs(**upstream)
    assert not upstream["out"].exists()


def test_rejects_test_fitted_or_reoriented_directions(upstream):
    path = upstream["w1"] / "probe_directions.json"
    meta = json.loads(path.read_text())
    meta["rows"][0]["fit_split"] = "test"
    P.dump(path, meta)
    _seal_analysis(upstream["w1"])
    with pytest.raises(ValueError, match="direction provenance"):
        prepare_inputs(**upstream)


def test_rejects_inconsistent_sealed_item_order(upstream):
    path = upstream["target"] / "items.order.json"
    order = json.loads(path.read_text())
    order[0], order[1] = order[1], order[0]
    P.dump(path, order)
    P.seal(upstream["target"], ["acts42.npy", "acts44.npy", "items.order.json", "provenance.target.json"], "SCORES_SEALED_W1")
    # Updating the parent hash does not excuse an activation/item-order mismatch.
    path = upstream["w1"] / "metrics.json"
    metrics = json.loads(path.read_text())
    metrics["reader_seals"] = [P.sha(upstream["target"] / "SCORE_SEAL.json")]
    P.dump(path, metrics)
    path = upstream["w1"] / "rule_i_rows.json"
    rule = json.loads(path.read_text())
    rule["metrics_sha256"] = P.sha(upstream["w1"] / "metrics.json")
    P.dump(path, rule)
    _seal_analysis(upstream["w1"])
    with pytest.raises(ValueError, match="item order"):
        prepare_inputs(**upstream)


def test_label_join_requires_complete_input_bound_score_seal(upstream, tmp_path):
    receipt = prepare_inputs(**upstream)
    directory, scores = upstream["out"] / "e4", tmp_path / "scores"
    scores.mkdir()
    with pytest.raises(FileNotFoundError):
        join_labels(directory, scores, receipt["local_labels"])
    P.dump(scores / "provenance.json", {"input_seal_sha256": "wrong"})
    P.seal(scores, ["provenance.json"], "SCORES_SEALED_E4")
    with pytest.raises(ValueError, match="not bound"):
        join_labels(directory, scores, receipt["local_labels"])
    P.dump(scores / "provenance.json", {"input_seal_sha256": P.sha(directory / "INPUT_SEAL.json")})
    P.seal(scores, ["provenance.json"], "SCORES_SEALED_E4")
    joined = join_labels(directory, scores, receipt["local_labels"])
    assert len(joined) == 2100
    assert {r["y"] for r in joined} == {0, 1}
    assert all(r["y"] == int(r["value"] == "a") for r in joined)
    with (scores / "provenance.json").open("a") as f:
        f.write(" ")
    with pytest.raises(ValueError, match="seal mismatch"):
        join_labels(directory, scores, receipt["local_labels"])
