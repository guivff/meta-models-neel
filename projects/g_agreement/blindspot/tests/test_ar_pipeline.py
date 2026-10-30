"""Synthetic sealed pipeline tests; no weights, GPU work, or empirical claims."""
import builtins
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from projects.g_agreement.blindspot import ar_tests as ar
from projects.g_agreement.blindspot import protocol as P


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    # Keep test invocation records inside pytest's temporary directory.
    logged = P.logged
    monkeypatch.setattr(P, "logged", lambda stage, **kw: logged(stage, root=tmp_path / "logs", **kw))
    definitions = {
        "table_column": {"row_class": "count-like", "values": ["A", "B"],
                         "descriptions": ["the first column", "the second column"]},
        "topic": {"row_class": "semantic", "values": ["A", "B"],
                  "descriptions": ["gardening content", "ocean content"]},
    }
    bank, target = tmp_path / "bank", tmp_path / "target"
    bank.mkdir(); target.mkdir()
    items, labels, activations, reconstructed = [], [], [], []
    for feature in definitions:
        for family in range(12):
            for repeat in range(5):
                for value in ("A", "B"):
                    key = f"{feature}:{family}:{repeat}:{value}"
                    items.append({"id": key, "feature": feature, "ids": [7] * 24})
                    labels.append({
                        "id": key, "feature": feature, "value": value,
                        "split": "dev" if family < 6 else "test", "cluster": f"family_{family}",
                        "class": definitions[feature]["row_class"],
                        "domain": "table" if feature == "table_column" else "prose",
                    })
                    h = [2. if value == "A" else -2., 1.]
                    activations.append(h)
                    reconstructed.append([0., 1.] if feature == "table_column" else h)
    h, rec = np.asarray(activations, np.float32), np.asarray(reconstructed, np.float32)
    P.jsonl(bank / "items.input.jsonl", items)
    P.jsonl(bank / "labels.DO_NOT_STAGE.jsonl", labels)
    templates = {
        feature: {
            "nla": [[f"{feature} A", f"{feature} B"], [f"This is {feature} A", f"This is {feature} B"]],
            "olens": [[f"- {feature} A", f"- {feature} B"], [f"- This is {feature} A", f"- This is {feature} B"]],
            "values": list(definition["values"]), "class": definition["row_class"],
            "kind": "binary", "score_orientation": "value_A_positive",
        }
        for feature, definition in definitions.items()
    }
    P.dump(bank / "templates.json", templates)
    P.dump(bank / "provenance.json", {"labels_sha256": P.sha(bank / "labels.DO_NOT_STAGE.jsonl")})
    P.seal(bank, ["items.input.jsonl", "templates.json", "provenance.json"], "INPUTS_FROZEN_SYNTHETIC_TEST")
    np.save(target / "acts44.npy", h, allow_pickle=False)
    P.dump(target / "items.order.json", [it["id"] for it in items])
    P.dump(target / "provenance.target.json", {"input_seal_sha256": P.sha(bank / "INPUT_SEAL.json")})
    P.seal(target, ["acts44.npy", "items.order.json", "provenance.target.json"], "SCORES_SEALED_SYNTHETIC_TEST")

    definitions_path = tmp_path / "definitions.json"
    rows_path = tmp_path / "upstream_rows.json"
    directions_path = tmp_path / "directions.npz"
    P.dump(definitions_path, definitions)
    P.dump(rows_path, [
        {"feature": f, "row_class": d["row_class"], "probe_auroc": 1.,
         "oracle_auroc": .6 if f == "table_column" else .95,
         "evaluable": True, "nla_evaluable": True, "blindspot": f == "table_column"}
        for f, d in definitions.items()
    ])
    np.savez(directions_path, **{feature: np.array([1., 0.]) for feature in definitions})
    reference, texts = tmp_path / "reference", tmp_path / "texts"
    ar.freeze_reference(SimpleNamespace(
        bank=bank, target=target, definitions=definitions_path, rows=rows_path,
        directions=directions_path, evidence="synthetic unit test; no empirical upstream result", out=reference,
    ))
    ar.freeze_texts(SimpleNamespace(definitions=definitions_path, out=texts))

    fidelity_dir, residual_dir = tmp_path / "fidelity", tmp_path / "residuals"
    fidelity_dir.mkdir(); residual_dir.mkdir()
    text_labels = P.rows(texts / "text_labels.DO_NOT_STAGE.jsonl")
    text_records = P.rows(texts / "texts.input.jsonl")
    text_predictions = np.asarray([[.5 if row["value"] else -.5, 1.] for row in text_labels], np.float32)
    np.save(fidelity_dir / "recon.npy", text_predictions, allow_pickle=False)
    P.dump(fidelity_dir / "ids.json", [row["id"] for row in text_records])
    P.dump(fidelity_dir / "provenance.json", {"text_seal_sha256": P.sha(texts / "INPUT_SEAL.json")})
    P.seal(fidelity_dir, ["recon.npy", "ids.json", "provenance.json"], "SCORES_SEALED_SYNTHETIC_TEST")
    np.save(residual_dir / "recon.npy", rec, allow_pickle=False)
    np.save(residual_dir / "residual.npy", h - rec, allow_pickle=False)
    P.dump(residual_dir / "ids.json", [it["id"] for it in items])
    P.dump(residual_dir / "provenance.json", {
        "input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"),
        "target_score_seal_sha256": P.sha(target / "SCORE_SEAL.json"),
    })
    P.seal(residual_dir, ["recon.npy", "residual.npy", "ids.json", "provenance.json"], "SCORES_SEALED_SYNTHETIC_TEST")
    pairs_dir = tmp_path / "pairs"
    labels_path = bank / "labels.DO_NOT_STAGE.jsonl"
    ar.prepare_swaps(SimpleNamespace(
        bank=bank, target=target, reference=reference, residuals=residual_dir,
        labels=labels_path, out=pairs_dir,
    ))
    pairs = P.rows(pairs_dir / "pairs.input.jsonl")
    import mats.readers.nla as nla_module

    def fake_scores(nla, acts, pairs, batch=8):
        assert len(pairs) == 2
        return torch.stack([acts[:, 0], acts[:, 0]])

    monkeypatch.setattr(nla_module, "paired_logodds_templates", fake_scores)
    scores_dir = tmp_path / "scores"
    scores_dir.mkdir()
    P.jsonl(scores_dir / "scores.swap.jsonl", ar.score_swaps(object(), h, rec, pairs, templates))
    P.dump(scores_dir / "provenance.json", {"pair_seal_sha256": P.sha(pairs_dir / "INPUT_SEAL.json"), **ar.SITE})
    P.seal(scores_dir, ["scores.swap.jsonl", "provenance.json"], "SCORES_SEALED_SYNTHETIC_TEST")
    return SimpleNamespace(
        bank=bank, target=target, reference=reference, labels=labels_path,
        texts=texts, text_labels=texts / "text_labels.DO_NOT_STAGE.jsonl",
        reconstruction=fidelity_dir, residuals=residual_dir, pairs=pairs_dir, scores=scores_dir,
        root=tmp_path,
    )


def run_analysis(pipeline, phase):
    args = SimpleNamespace(**vars(pipeline), out=pipeline.root / f"analysis_{phase}")
    {"fidelity": ar.analyse_fidelity, "residual": ar.analyse_residual, "swap": ar.analyse_swaps}[phase](args)
    return json.loads((args.out / f"metrics.{phase}.json").read_text())


def test_synthetic_sealed_end_to_end_pipeline(pipeline):
    fidelity = run_analysis(pipeline, "fidelity")
    assert len(fidelity["rows"]) == 2
    assert all(row["fidelity"] == pytest.approx(.25) for row in fidelity["rows"])
    assert fidelity["W2"]["status"] == "NOT EVALUABLE"  # two rows cannot establish the trend
    residual = run_analysis(pipeline, "residual")
    assert residual["W3"]["status"] == "CONFIRMED"
    swap = run_analysis(pipeline, "swap")
    assert swap["all_tested_rows_meet_rule"] is True
    assert swap["site"] == "OFF-NATIVE"
    assert all(row["n_pairs"] == 40 for row in swap["rows"])
    for phase in ("fidelity", "residual", "swap"):
        seal = P.verify(pipeline.root / f"analysis_{phase}", "SCORE_SEAL.json")
        assert f"metrics.{phase}.json" in seal["files"]
    ledger = P.rows(pipeline.root / "logs/results/g_agreement/compute.jsonl")
    assert ledger and all(row["gpu_hours"] == 0 for row in ledger)


def guard_label_reads(monkeypatch, pipeline):
    original = Path.read_text
    protected = {pipeline.labels, pipeline.text_labels}

    def checked(path, *args, **kwargs):
        assert path not in protected, "labels read before score/seal validation"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", checked)


@pytest.mark.parametrize("phase", ["fidelity", "residual", "swap"])
@pytest.mark.parametrize("corruption", ["tampered", "empty_seal", "wrong_grid"])
def test_bad_scores_rejected_before_label_join(pipeline, monkeypatch, phase, corruption):
    directory = {"fidelity": pipeline.reconstruction, "residual": pipeline.residuals, "swap": pipeline.scores}[phase]
    filename = "scores.swap.jsonl" if phase == "swap" else "ids.json"
    if corruption == "tampered":
        with (directory / filename).open("a") as out:
            out.write("\n ")
    elif corruption == "empty_seal":
        P.dump(directory / "SCORE_SEAL.json", {"status": "SCORES_SEALED_SYNTHETIC_TEST", "files": {}})
    else:
        if phase == "swap":
            rows = P.rows(directory / filename)[:-1]
            (directory / filename).write_text("".join(json.dumps(row) + "\n" for row in rows))
        else:
            P.dump(directory / filename, list(reversed(json.loads((directory / filename).read_text()))))
        seal = json.loads((directory / "SCORE_SEAL.json").read_text())
        P.seal(directory, list(seal["files"]), "SCORES_SEALED_SYNTHETIC_TEST")
    guard_label_reads(monkeypatch, pipeline)
    with pytest.raises(ValueError):
        run_analysis(pipeline, phase)


def test_resealed_incorrect_residual_rejected_before_labels(pipeline, monkeypatch):
    file = pipeline.residuals / "residual.npy"
    residual = np.load(file, allow_pickle=False)
    residual[0, 0] += 1
    np.save(file, residual, allow_pickle=False)
    seal = json.loads((pipeline.residuals / "SCORE_SEAL.json").read_text())
    P.seal(pipeline.residuals, list(seal["files"]), "SCORES_SEALED_SYNTHETIC_TEST")
    guard_label_reads(monkeypatch, pipeline)
    with pytest.raises(ValueError, match="not h minus"):
        run_analysis(pipeline, "residual")


@pytest.mark.parametrize("corruption", ["missing_file", "wrong_code", "wrong_brief", "no_evidence"])
def test_w4_invalid_p3_review_stops_before_assets_or_model_imports(tmp_path, monkeypatch, corruption):
    path = tmp_path / "synthetic_review_fixture.json"
    review = {
        "reviewer": "P3", "status": "APPROVED", "ar_tests_sha256": P.sha(ar.__file__),
        "brief_sha256": P.sha(P.ROOT / ar.BRIEF),
        "review_evidence": "SYNTHETIC TEST ONLY; never a launch authorization",
    }
    if corruption == "wrong_code":
        review["ar_tests_sha256"] = "0" * 64
    elif corruption == "wrong_brief":
        review["brief_sha256"] = "0" * 64
    elif corruption == "no_evidence":
        review["review_evidence"] = ""
    if corruption != "missing_file":
        P.dump(path, review)
    original = builtins.__import__

    def forbidden_import(name, *args, **kwargs):
        assert name.split(".")[0] not in {"torch", "transformers", "peft", "oracle_lens"}
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", forbidden_import)
    monkeypatch.setattr(ar, "_assets", lambda *a, **kw: pytest.fail("assets accessed before P3 review"))
    monkeypatch.setattr(ar, "_target", lambda *a, **kw: pytest.fail("target accessed before P3 review"))
    with pytest.raises((ValueError, FileNotFoundError)):
        ar.collect_swaps(SimpleNamespace(review=path))


@pytest.mark.parametrize("corruption", ["missing_sources", "stale_sources", "over_cap", "wrong_phase"])
def test_mechanism_admission_binds_sources_and_own_budget(tmp_path, corruption):
    assignment = {
        "issuer": "integrator", "pod_id": "synthetic-test-pod", "brief_registered": True,
        "brief_pushed": True, "source_commit": "a" * 40, "brief_commit": "b" * 40,
        "brief_sha256": P.sha(P.ROOT / ar.BRIEF), "source_files": ar.mechanism_source_hashes(),
        "mechanism_budget": "fidelity", "gpu_count": 1, "provider_created_epoch": 0,
        "deadline_epoch": 1000, "allocated_gpu_seconds": 1000, "previous_gpu_seconds": 0,
        "setup_allowance_seconds": 1500,
        "external_hardstop_verified": True,
    }
    path = tmp_path / "synthetic_assignment_fixture.json"
    P.dump(path, assignment)
    assert ar.admit_mechanism(path, "fidelity", now=10, pod_id="synthetic-test-pod")
    if corruption == "missing_sources":
        assignment.pop("source_files")
    elif corruption == "stale_sources":
        assignment["source_files"]["projects/g_agreement/blindspot/ar_tests.py"] = "0" * 64
    elif corruption == "over_cap":
        assignment["previous_gpu_seconds"] = 81
    else:
        assignment["mechanism_budget"] = "swap"
    P.dump(path, assignment)
    with pytest.raises(ValueError):
        ar.admit_mechanism(path, "fidelity", now=10, pod_id="synthetic-test-pod")


@pytest.mark.parametrize("corruption", ["value_order", "row_class"])
def test_freeze_reference_cannot_redefine_upstream_values_or_class(pipeline, corruption):
    definitions = json.loads((pipeline.reference / "definitions.json").read_text())
    if corruption == "value_order":
        definitions["table_column"]["values"] = ["B", "A"]
    else:
        definitions["table_column"]["row_class"] = "semantic"
    path = pipeline.root / "changed_definitions.json"
    P.dump(path, definitions)
    with pytest.raises(ValueError, match="values/class differ"):
        ar.freeze_reference(SimpleNamespace(
            bank=pipeline.bank, target=pipeline.target, definitions=path,
            rows=pipeline.root / "upstream_rows.json", directions=pipeline.root / "directions.npz",
            evidence="synthetic test", out=pipeline.root / "invalid_reference",
        ))
    assert not (pipeline.root / "invalid_reference").exists()


def test_resealed_reversed_reference_is_rejected_before_labels(pipeline, monkeypatch):
    path = pipeline.reference / "definitions.json"
    definitions = json.loads(path.read_text())
    definitions["table_column"]["values"] = ["B", "A"]
    P.dump(path, definitions)
    seal = json.loads((pipeline.reference / "INPUT_SEAL.json").read_text())
    P.seal(pipeline.reference, list(seal["files"]), "INPUTS_FROZEN_SYNTHETIC_TEST")
    guard_label_reads(monkeypatch, pipeline)
    with pytest.raises(ValueError, match="values/class differ"):
        run_analysis(pipeline, "fidelity")


def w1_export_fixture(pipeline):
    """Use W-core's actual export writer with explicitly synthetic metric inputs."""
    from projects.g_agreement.blindspot import analysis

    upstream = pipeline.root / "w1_export"
    cells, metadata, arrays = [], [], {}
    definitions = json.loads((pipeline.reference / "definitions.json").read_text())
    for feature, definition in definitions.items():
        for reader, layer in (("olens", 44), ("nla", 42)):
            auroc = .6 if feature == "table_column" and reader == "olens" else .95
            cells.append({
                "feature": feature, "reader": reader, "layer": layer,
                "class": definition["row_class"], "probe_auroc": 1., "status": "EVALUABLE",
                "true": {"auroc": auroc}, "mismatched": {"auroc": .1},
            })
        prefix = feature + "__L44"
        arrays[prefix + "__unit"] = np.array([1., 0.], np.float32)
        arrays[prefix + "__coef"] = np.array([2., 0.], np.float32)
        metadata.append({
            "feature": feature, "layer": 44, "fit_split": "dev", "array_prefix": prefix,
            "positive_value": "A", "negative_value": "B", "orientation_flipped": False,
        })
    data = {
        "input_seal_sha256": P.sha(pipeline.bank / "INPUT_SEAL.json"),
        "reader_seals": [P.sha(pipeline.target / "SCORE_SEAL.json")],
        "rows": cells, "w1": {"status": "SYNTHETIC_TEST_ONLY"},
    }
    activation_manifest = analysis._activation_manifest(pipeline.target, [44], pipeline.target / "items.order.json")
    analysis._finish(upstream, data, [], arrays, metadata, activation_manifest)
    return upstream


def test_active_wcore_export_adapts_to_mechanism_reference_and_w3(pipeline):
    upstream = w1_export_fixture(pipeline)
    reference = pipeline.root / "reference_from_w1"
    ar.reference_from_w1(SimpleNamespace(bank=pipeline.bank, target=pipeline.target, w1=upstream, out=reference))
    definitions, rows, directions = ar._reference(reference, pipeline.bank, pipeline.target)
    assert definitions == ar.definitions_from_bank(pipeline.bank)
    assert {row["feature"]: row["blindspot"] for row in rows} == {"table_column": True, "topic": False}
    assert all(row["nla_evaluable"] for row in rows)
    assert all(torch.equal(direction, torch.tensor([1., 0.])) for direction in directions.values())
    provenance = json.loads((reference / "provenance.json").read_text())
    assert provenance["w1_analysis_seal_sha256"] == P.sha(upstream / "ANALYSIS_SEAL.json")
    assert provenance["direction_space"] == "raw_block44"
    exported_texts = pipeline.root / "texts_from_w1"
    ar.freeze_w1_texts(SimpleNamespace(bank=pipeline.bank, out=exported_texts))
    assert json.loads((exported_texts / "definitions.json").read_text()) == definitions
    assert len(P.rows(exported_texts / "texts.input.jsonl")) == 80
    adapted = SimpleNamespace(**{**vars(pipeline), "reference": reference})
    result = run_analysis(adapted, "residual")
    assert result["W3"]["status"] == "CONFIRMED"
    assert all(row["original_auroc"] == row["probe_auroc"] == 1. for row in result["rows"])


@pytest.mark.parametrize("corruption", ["wrong_target", "test_fit", "reversed_direction"])
def test_w1_adapter_rejects_wrong_source_or_direction_provenance(pipeline, corruption):
    upstream = w1_export_fixture(pipeline)
    if corruption == "wrong_target":
        path = upstream / "metrics.json"
        value = json.loads(path.read_text())
        value["reader_seals"] = ["0" * 64]
    else:
        path = upstream / "probe_directions.json"
        value = json.loads(path.read_text())
        if corruption == "test_fit":
            value["rows"][0]["fit_split"] = "test"
        else:
            value["rows"][0]["positive_value"] = "B"
    P.dump(path, value)
    seal = json.loads((upstream / "ANALYSIS_SEAL.json").read_text())
    seal["files"] = {name: P.sha(upstream / name) for name in seal["files"]}
    P.dump(upstream / "ANALYSIS_SEAL.json", seal)
    with pytest.raises(ValueError):
        ar.reference_from_w1(SimpleNamespace(
            bank=pipeline.bank, target=pipeline.target, w1=upstream,
            out=pipeline.root / "invalid_w1_reference",
        ))


def test_w3_rejects_failure_to_reproduce_frozen_original_probe(pipeline):
    path = pipeline.reference / "rows.json"
    rows = json.loads(path.read_text())
    rows[0]["probe_auroc"] = .9
    P.dump(path, rows)
    seal = json.loads((pipeline.reference / "INPUT_SEAL.json").read_text())
    P.seal(pipeline.reference, list(seal["files"]), "INPUTS_FROZEN_SYNTHETIC_TEST")
    with pytest.raises(ValueError, match="does not reproduce frozen W1 probe"):
        run_analysis(pipeline, "residual")
