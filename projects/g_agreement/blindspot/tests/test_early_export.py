"""Synthetic fixture tests only; no experiment data or model computation."""
from contextlib import nullcontext
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from projects.g_agreement.blindspot import early_export as E
from projects.g_agreement.blindspot import protocol as P


def fixture_run(tmp_path, monkeypatch):
    from projects.g_agreement.blindspot import execution
    bank, target, nla, local = [tmp_path / name for name in ("bank", "target", "nla", "local-analysis")]
    for path in (bank, target, nla, local):
        path.mkdir()
    items, labels, vectors = [], [], []
    templates = {}
    for fi, feature in enumerate(E.PRIORITY):
        templates[feature] = {"kind": "binary", "class": "semantic" if fi > 1 else "state-like", "domain": "fixture",
            "values": ["A", "B"], **{reader: [["A", "B"], ["a", "b"]] for reader, _ in E.NATIVE}}
        for template in range(12):
            for pair in range(7):
                for side in range(2):
                    key = f"f{fi}-t{template}-p{pair}-s{side}"
                    donor = f"f{fi}-t{template}-p{pair}-s{1-side}"
                    items.append({"id": key, "feature": feature, "ids": [42, 43], "donor_id": donor})
                    labels.append({"id": key, "feature": feature, "class": templates[feature]["class"], "domain": "fixture",
                        "value": "AB"[side], "split": "dev" if template < 6 else "test", "cluster": f"f{fi}-t{template}"})
                    # A huge held-out displacement makes any accidental full-bank mean obvious.
                    vectors.append([1 - 2 * side, pair * .1] if template < 6 else [10000 + side, 20000 + pair])
    # The real execution planner requires two remaining whole-row units.
    fullitems, fulllabels = list(items), list(labels)
    for feature in ("remainder_fixture_a", "remainder_fixture_b"):
        templates[feature] = {**templates[E.PRIORITY[0]]}
        for side in range(2):
            key = f"{feature}-{side}"
            fullitems.append({"id": key, "feature": feature, "ids": [42, 43], "donor_id": f"{feature}-{1-side}"})
            fulllabels.append({"id": key, "feature": feature, "class": "state-like", "domain": "fixture",
                "value": "AB"[side], "split": "dev", "cluster": feature})
    P.jsonl(bank / "items.input.jsonl", fullitems)
    P.jsonl(bank / "labels.DO_NOT_STAGE.jsonl", fulllabels)
    P.dump(bank / "templates.json", templates)
    P.dump(bank / "provenance.json", {"labels_sha256": P.sha(bank / "labels.DO_NOT_STAGE.jsonl")})
    sources = P.code_hashes()
    P.dump(bank / "manifest.json", {"schema": "synthetic-fixture-only", "experiment": "W1", "source_files": sources,
        "rows": {feature: {"n": sum(it["feature"] == feature for it in fullitems),
                 "split_counts": {split: sum(r["feature"] == feature and r["split"] == split for r in fulllabels)
                                  for split in ("dev", "test")}} for feature in templates},
        "files": {"labels.DO_NOT_STAGE.jsonl": P.sha(bank / "labels.DO_NOT_STAGE.jsonl")}})
    for name in E.INPUT_NAMES - {"items.input.jsonl", "templates.json", "provenance.json", "manifest.json"}:
        P.dump(bank / name, {})
    P.seal(bank, sorted(E.INPUT_NAMES), "INPUTS_FROZEN")
    training_path = local / "priority.dev.DO_NOT_STAGE.jsonl"
    plan_path = tmp_path / "execution.json"
    execution.build_plan(bank, plan_path, local, runtime_source_files=sources)
    monkeypatch.setattr(P, "logged", lambda *args, **kwargs: nullcontext())
    # Exercise the real production serializer, with synthetic vectors and scores.
    from projects.g_agreement.blindspot.run import _store_asked
    import torch
    assignment_path, assets_path = tmp_path / "assignment.json", tmp_path / "assets.json"
    P.dump(assignment_path, {"experiment": "W1", "fixture_only": True})
    P.dump(assets_path, {"fixture_only": True})
    for phase, directory in (("target", target), ("nla", nla)):
        scores = [{"id": it["id"], "reader": reader, "layer": layer,
            "arm": arm, "scores": [0., 0.], "status": "COMPLETE"} for it in items for reader, layer in E.NATIVE
            if (reader == "nla") == (phase == "nla") for arm in ("true", "mismatched")]
        extra = {"execution": {"execution_plan_sha256": P.sha(plan_path), "execution_unit": "priority"}}
        if phase == "nla":
            extra["target_score_seal_sha256"] = P.sha(target / "SCORE_SEAL.json")
        by_layer = {layer: torch.tensor(vectors, dtype=torch.float32) for layer in (42, 44)} if phase == "target" else {}
        _store_asked(SimpleNamespace(out=directory, bank=bank, assignment=assignment_path, assets=assets_path, batch=P.RUNTIME["batch"]),
                     {"experiment": "W1"}, items, by_layer, scores, phase, extra)
    return SimpleNamespace(bank=bank, execution_plan=plan_path, target=target, nla=nla,
                           training_labels=training_path, out=tmp_path / "export")


def seal_stage(directory, phase):
    names = [f"scores.{phase}.jsonl", f"provenance.{phase}.json", "items.order.json"]
    if phase == "target":
        names += ["acts42.npy", "acts44.npy"]
    P.seal(directory, names, f"SCORES_SEALED_{phase.upper()}_BEFORE_LABEL_JOIN")


def rebind_labels(args):
    plan = json.loads(args.execution_plan.read_text())
    plan["training_labels"]["sha256"] = P.sha(args.training_labels)
    P.dump(args.execution_plan, plan)
    receipt_path = args.training_labels.parent / "TRAINING_LABEL_SEAL.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["training_labels_sha256"] = P.sha(args.training_labels)
    P.dump(receipt_path, receipt)
    for phase, directory in (("target", args.target), ("nla", args.nla)):
        provenance = json.loads((directory / f"provenance.{phase}.json").read_text())
        provenance["execution"]["execution_plan_sha256"] = P.sha(args.execution_plan)
        if phase == "nla":
            provenance["target_score_seal_sha256"] = P.sha(args.target / "SCORE_SEAL.json")
        P.dump(directory / f"provenance.{phase}.json", provenance)
        seal_stage(directory, phase)


def test_priority_export_fits_only_dev_and_exports_means_without_heldout_artifacts(tmp_path, monkeypatch):
    args = fixture_run(tmp_path, monkeypatch)
    original = P.rows
    def no_full_labels(path):
        if Path(path) == args.bank / "labels.DO_NOT_STAGE.jsonl":
            pytest.fail("early exporter read full labels")
        return original(path)
    monkeypatch.setattr(P, "rows", no_full_labels)
    result = E.export_training(args)
    assert result["fit_split"] == "dev" and len(result["rows"]) == 10
    P.verify(args.out, "TRAINING_EXPORT_SEAL.json")
    arrays = np.load(args.out / "probe_directions.npz")
    assert len(arrays.files) == 40
    for row in result["rows"]:
        assert row["dev_n"] == 84 and row["n_A"] == row["n_B"] == 42
        assert row["n_template_clusters"] == 6 and row["fit_split"] == "dev"
        assert row["orientation_flipped"] is False
        a, b = arrays[row["arrays"]["raw_mean_A"]], arrays[row["arrays"]["raw_mean_B"]]
        assert np.allclose(a, [1., .3]) and np.allclose(b, [-1., .3])
        d = arrays[row["arrays"]["unit_direction"]]
        assert np.isclose(np.linalg.norm(d), 1) and row["dev_class_mean_projection_gap"] > 0
    output = (args.out / "probe_directions.json").read_text()
    assert "auroc" not in output.lower() and "test_" not in output.lower()
    assert str(args.target) not in output and "items.order" not in output
    assert not any(r["id"] in output for r in original(args.bank / "labels.DO_NOT_STAGE.jsonl"))


def test_missing_priority_score_refuses_before_any_training_labels_are_read(tmp_path, monkeypatch):
    args = fixture_run(tmp_path, monkeypatch)
    score_path = args.nla / "scores.nla.jsonl"
    rows = P.rows(score_path)
    score_path.unlink()
    P.jsonl(score_path, rows[:-1])
    seal_stage(args.nla, "nla")
    original = P.rows
    def guard(path):
        if Path(path) == args.training_labels:
            pytest.fail("training labels opened before complete score grid")
        return original(path)
    monkeypatch.setattr(P, "rows", guard)
    with pytest.raises(ValueError, match="incomplete/duplicate score grid"):
        E.export_training(args)
    assert not args.out.exists()


def test_heldout_activation_changes_do_not_change_any_exported_vector_or_mean(tmp_path, monkeypatch):
    args = fixture_run(tmp_path, monkeypatch)
    full_label_path = args.bank / "labels.DO_NOT_STAGE.jsonl"
    # Fixture preparation identifies held-out rows before installing the read guard.
    splits = {r["id"]: r["split"] for r in P.rows(full_label_path)}
    capture_order = json.loads((args.target / "items.order.json").read_text())
    heldout = [i for i, key in enumerate(capture_order) if splits[key] == "test"]
    original = Path.read_text
    opened_training = []
    def guard(path, *pos, **kw):
        if path == full_label_path:
            pytest.fail("early export opened the full frozen label file")
        if path == args.training_labels:
            opened_training.append(path)
        return original(path, *pos, **kw)
    monkeypatch.setattr(Path, "read_text", guard)
    first = E.export_training(args)
    with np.load(args.out / "probe_directions.npz") as saved:
        first_arrays = {key: saved[key].copy() for key in saved.files}
    for layer in (42, 44):
        path = args.target / f"acts{layer}.npy"
        values = np.load(path)
        values[heldout] = np.random.default_rng(layer).normal(size=(len(heldout), values.shape[1])) * 100000
        np.save(path, values)
    seal_stage(args.target, "target")
    provenance_path = args.nla / "provenance.nla.json"
    provenance = json.loads(provenance_path.read_text())
    provenance["target_score_seal_sha256"] = P.sha(args.target / "SCORE_SEAL.json")
    P.dump(provenance_path, provenance)
    seal_stage(args.nla, "nla")
    args.out = tmp_path / "export-after-heldout-perturbation"
    second = E.export_training(args)
    with np.load(args.out / "probe_directions.npz") as saved:
        assert set(saved.files) == set(first_arrays)
        assert all(np.array_equal(first_arrays[key], saved[key]) for key in saved.files)
    assert first["rows"] == second["rows"]
    assert first["target_score_seal_sha256"] != second["target_score_seal_sha256"]
    assert len(opened_training) == 2


def test_export_refuses_mixed_split_even_with_consistent_derivative_hash(tmp_path, monkeypatch):
    args = fixture_run(tmp_path, monkeypatch)
    rows = P.rows(args.training_labels)
    rows[0]["split"] = "test"
    args.training_labels.unlink()
    P.jsonl(args.training_labels, rows)
    rebind_labels(args)
    with pytest.raises(ValueError, match="non-dev"):
        E.export_training(args)
    assert not args.out.exists()


def test_export_rejects_full_label_filename_and_source_mismatch(tmp_path, monkeypatch):
    args = fixture_run(tmp_path, monkeypatch)
    declared = args.training_labels
    args.training_labels = args.bank / "labels.DO_NOT_STAGE.jsonl"
    with pytest.raises(ValueError, match="declared dev-only"):
        E.export_training(args)
    args.training_labels = declared
    provenance_path = args.nla / "provenance.nla.json"
    provenance = json.loads(provenance_path.read_text())
    provenance["source_files"] = {}
    P.dump(provenance_path, provenance)
    seal_stage(args.nla, "nla")
    with pytest.raises(ValueError, match="score provenance"):
        E.export_training(args)
    assert not args.out.exists()


@pytest.mark.parametrize("field,value", [("assets_sha256", "0" * 64), ("batch", 1), ("hook", "wrong hook")])
def test_export_rejects_cross_reader_asset_batch_or_hook_mismatch(tmp_path, monkeypatch, field, value):
    args = fixture_run(tmp_path, monkeypatch)
    path = args.nla / "provenance.nla.json"
    provenance = json.loads(path.read_text())
    provenance[field] = value
    P.dump(path, provenance)
    seal_stage(args.nla, "nla")
    original = P.rows
    def guard(path):
        if Path(path) == args.training_labels:
            pytest.fail("labels read despite cross-reader provenance mismatch")
        return original(path)
    monkeypatch.setattr(P, "rows", guard)
    with pytest.raises(ValueError, match="assets, batch or hook"):
        E.export_training(args)
    assert not args.out.exists()


@pytest.mark.parametrize("which", ["target", "bank"])
def test_unregistered_label_file_in_seal_is_rejected_before_hashing_it(tmp_path, monkeypatch, which):
    args = fixture_run(tmp_path, monkeypatch)
    directory = getattr(args, which)
    path = directory / "labels.DO_NOT_STAGE.jsonl"
    if which == "target":
        path.write_bytes((args.bank / "labels.DO_NOT_STAGE.jsonl").read_bytes())
    seal_path = directory / ("INPUT_SEAL.json" if which == "bank" else "SCORE_SEAL.json")
    seal = json.loads(seal_path.read_text())
    seal["files"][path.name] = P.sha(path)
    P.dump(seal_path, seal)
    original = P.sha
    def guard(to_hash):
        if Path(to_hash) == path:
            pytest.fail("malformed seal caused full labels to be opened for hashing")
        return original(to_hash)
    monkeypatch.setattr(P, "sha", guard)
    with pytest.raises(ValueError, match="complete priority|full frozen bank"):
        E.export_training(args)
    assert not args.out.exists()
