"""Synthetic CPU tests: packaging never provisions a pod or invokes a reader."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from . import prepare_native as package
from .custody import forecast_proof, seal, sha256, write_json
from .preflight import BANK_HASH_FIELDS, NATIVE_SOURCES


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.PIPE, text=True).strip()


@pytest.fixture
def setup(tmp_path):
    repo, inputs, capture, probes = [tmp_path / n for n in ("repo", "reader_inputs", "capture", "probes")]
    for d in (repo, inputs, capture, probes):
        d.mkdir()
    source_hashes = {}
    for name in NATIVE_SOURCES:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('"""Synthetic source fixture; no model or reader implementation."""\n')
        source_hashes[name] = sha256(path)
    artifact = "forecast/E73_JFORECAST.json"
    write_json(repo / artifact, {"experiment": "E73", "synthetic_test_only": True})
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=E73 Test", "-c", "user.email=e73-test@example.invalid", "commit", "-qm", "Synthetic frozen fixture")
    commit = git(repo, "rev-parse", "HEAD")
    manifest = {key: "a" * 64 for key in BANK_HASH_FIELDS}
    manifest.update(experiment="E73", stage="BOW_GATE_SEALED", items=800, context_tokens=256,
                    input_schema=["id", "input_ids"], code_sha256={name: "b" * 64 for name in ("sources.py", "states.py", "sample.py", "bow.py")})
    bank_manifest = tmp_path / "BANK_MANIFEST.json"
    write_json(bank_manifest, manifest)
    bank_hash = sha256(bank_manifest)
    ids = [f"{i:032x}" for i in range(4)]
    write_json(capture / "CAPTURE_REPORT.json", {"status": "COMPLETE", "labels_present": False, "reader_outputs": 0})
    seal(capture, "CAPTURE_SEAL.json", [capture / "CAPTURE_REPORT.json"], status="COMPLETE", track="C", bank_manifest_sha256=bank_hash)
    capture_refs = [{"seal_sha256": sha256(capture / "CAPTURE_SEAL.json")}]
    arrays = {name: np.zeros(5120) for name in ("direction", "scaler_mean", "scaler_scale", "dev_mean_A", "dev_mean_B", "test_mean_A", "test_mean_B")}
    arrays.update(intercept=np.array(0), test_ids=np.asarray(ids), reader_ids=np.asarray(ids),
                  test_labels=np.array([0, 1, 0, 1]), test_scores=np.zeros(4),
                  test_block44=np.zeros((4, 5120), np.float32), test_block42=np.ones((4, 5120), np.float32))
    np.savez(probes / "W1_probe.npz", **arrays)
    write_json(probes / "PROBE_REPORT.json", {"bank_manifest_sha256": bank_hash, "readers": "NOT_RUN",
               "capture_seals": capture_refs, "rows": [{"state": "W1"}]})
    seal(probes, "PROBE_SEAL.json", sorted(probes.iterdir()), status="COMPLETE", track="C", cpu_private=True)
    shards = []
    for index in range(2):
        path = inputs / f"reader-input-{index:03d}.npz"
        np.savez(path, ids=np.asarray(ids[index * 2:index * 2 + 2]), block44=np.zeros((2, 5120), np.float16), block42=np.ones((2, 5120), np.float16))
        shards.append({"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size, "count": 2})
    write_json(inputs / "READER_INPUTS.json", {"schema": "e73-reader-inputs-v1", "bank_manifest_sha256": bank_hash,
        "source_capture_seals": capture_refs, "probe_seal_sha256": sha256(probes / "PROBE_SEAL.json"),
        "shards": shards, "total": 4, "labels_present": False})
    seal(inputs, "READER_INPUT_SEAL.json", sorted(inputs.iterdir()), status="COMPLETE", track="C", labels_present=False)
    forecast_hash = sha256(repo / artifact)
    go = tmp_path / "GO.json"
    write_json(go, {"schema": "e73-reader-go-v1", "authorized_by": "I-2", "action": "GO",
                   "capture_seal_sha256": sha256(inputs / "READER_INPUTS.json"), "bank_manifest_sha256": bank_hash,
                   "jforecast_commit": commit, "jforecast_sha256": forecast_hash, "judging_authorized": False})
    proof = tmp_path / "FORECAST_PROOF.json"
    write_json(proof, forecast_proof(repo, commit, artifact, forecast_hash))
    admissions = []
    for i, shard in enumerate(shards):
        path = tmp_path / f"ADMISSION_{i}.json"
        write_json(path, {"schema": "e73-admission-v1", "track": "C", "authorized_by": "I-2",
            "sampler_commit": "a" * 40, "input_sha256": shard["sha256"], "bank_manifest_sha256": bank_hash,
            "gpu_count": 1, "gpu_seconds_cap": 1200, "prior_track_gpu_seconds": 1000, "forecast_gpu_seconds": 600,
            "staging_cap_seconds": 900, "combined_spend_before_usd": 110, "launch_spend_cap_usd": 10, "daily_ceiling_usd": 300,
            "source_files": source_hashes, "native_seconds_per_item": {"oracle": .1, "nla": .2}, "nla_setup_seconds": 60,
            "retrieval_allowance_seconds": 300,
            "staging_readiness_policy": "first_reader_then_continuous_model_switch", "run_id": f"native-fixture-{i:03d}",
            "run_kind": "real", "runtime_commit": commit,
            "code_sha256": hashlib.sha256(json.dumps(source_hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()})
        admissions.append(path)
    return SimpleNamespace(repo=repo, reader_inputs=inputs, bank_manifest=bank_manifest, probes=probes,
                           capture=[capture], go=go, forecast_proof=proof, forecast_artifact_path=artifact,
                           admission=admissions, source_commit=commit, out=tmp_path / "packages")


def test_complete_selection_packaged_with_exact_allowlist_and_no_private_payload(setup):
    result = package.prepare(setup)
    assert result["total_positions"] == 4 and len(result["archives"]) == 2
    assert result["native_generation_started"] is False and result["grants_admission_or_go"] is False
    assert (setup.out / "NATIVE_PACKAGE_SEAL.json").is_file()
    for index, record in enumerate(result["archives"]):
        path = setup.out / record["file"]
        assert path.stat().st_size <= 20_000_000 and sha256(path) == record["archive_sha256"]
        with tarfile.open(path) as tar:
            assert set(tar.getnames()) == package.FIXED_DATA | set(NATIVE_SOURCES) | {f"inputs/reader-input-{index:03d}.npz"}
            assert tar.extractfile("control/ADMISSION.json").read() == setup.admission[index].read_bytes()
            assert tar.extractfile("control/GO.json").read() == setup.go.read_bytes()
            assert not any("PRIVATE" in name or "probe" in name.lower() or "FORECAST.json" in name for name in tar.getnames())


def test_no_go_no_package_directory(setup):
    go = json.loads(setup.go.read_text()); go["action"] = "WAIT"; write_json(setup.go, go)
    with pytest.raises(ValueError, match="GO absent"):
        package.prepare(setup)
    assert not setup.out.exists()


def test_committed_forecast_not_merely_local_uncommitted_file(setup):
    (setup.repo / setup.forecast_artifact_path).write_text('{"changed_after_commit":true}')
    result = package.prepare(setup)
    assert result["jforecast_commit"] == setup.source_commit
    # The Git object, not this modified working-tree file, supplies the proof.
    assert result["jforecast_sha256"] != sha256(setup.repo / setup.forecast_artifact_path)


def test_forged_forecast_hash_rejected_before_output(setup):
    go = json.loads(setup.go.read_text()); go["jforecast_sha256"] = "0" * 64; write_json(setup.go, go)
    proof = json.loads(setup.forecast_proof.read_text()); proof["artifact_sha256"] = "0" * 64; write_json(setup.forecast_proof, proof)
    with pytest.raises(ValueError, match="committed Git object"):
        package.prepare(setup)
    assert not setup.out.exists()


def test_private_admission_field_or_changed_source_map_rejected(setup):
    value = json.loads(setup.admission[0].read_text()); value["labels"] = [0, 1]; write_json(setup.admission[0], value)
    with pytest.raises(ValueError, match="exact I-2 schema"):
        package.prepare(setup)
    assert not setup.out.exists()


def test_rich_operator_record_is_not_silently_rewritten_for_staging(setup):
    value = json.loads(setup.admission[0].read_text())
    value.update(budget_basis="CPU operator rationale", conditions=["External operator condition"], retrieval_allowance_seconds=1800)
    write_json(setup.admission[0], value)
    original = setup.admission[0].read_bytes()
    with pytest.raises(ValueError, match="exact I-2 schema"):
        package.prepare(setup)
    assert setup.admission[0].read_bytes() == original and not setup.out.exists()


def test_all_index_shards_need_admissions(setup):
    setup.admission = setup.admission[:1]
    with pytest.raises(ValueError, match="exactly one I-2 admission"):
        package.prepare(setup)


def test_individually_valid_caps_cannot_overbook_whole_package(setup):
    for path in setup.admission:
        value = json.loads(path.read_text())
        value["gpu_seconds_cap"] = 11000
        write_json(path, value)
    with pytest.raises(ValueError, match="combined native package reservations"):
        package.prepare(setup)
    assert not setup.out.exists()


def test_retrieval_can_cross_two_shard_aggregate_cap_when_compute_and_staging_fit(setup):
    values = []
    for path in setup.admission:
        value = json.loads(path.read_text())
        value["gpu_seconds_cap"] = 9300
        write_json(path, value)
        values.append(value)
    prior = min(value["prior_track_gpu_seconds"] for value in values)
    compute_staging = sum(value["gpu_seconds_cap"] + value["staging_cap_seconds"] for value in values)
    assert prior + compute_staging == 21400 <= package.MAX_GPU_SECONDS
    assert prior + compute_staging + sum(value["retrieval_allowance_seconds"] for value in values) == 22000 > package.MAX_GPU_SECONDS
    with pytest.raises(ValueError, match="combined native package reservations"):
        package.prepare(setup)
    assert not setup.out.exists()


@pytest.mark.parametrize("allowance", [-1, float("nan"), float("inf"), "300", True])
def test_invalid_retrieval_allowance_is_rejected(setup, allowance):
    value = json.loads(setup.admission[0].read_text())
    value["retrieval_allowance_seconds"] = allowance
    with pytest.raises(ValueError, match="Retrieval allowance must be a finite nonnegative"):
        package.validate_native_admission(value, input_sha=value["input_sha256"], bank_sha=value["bank_manifest_sha256"],
                                          source_hashes=value["source_files"], source_commit=setup.source_commit)


def test_per_shard_cap_includes_retrieval_and_accepts_zero_allowance(setup):
    value = json.loads(setup.admission[0].read_text())
    value["gpu_seconds_cap"] = 19600
    with pytest.raises(ValueError, match="per-shard worker, staging, and retrieval"):
        package.validate_native_admission(value, input_sha=value["input_sha256"], bank_sha=value["bank_manifest_sha256"],
                                          source_hashes=value["source_files"], source_commit=setup.source_commit)
    value["retrieval_allowance_seconds"] = 0
    package.validate_native_admission(value, input_sha=value["input_sha256"], bank_sha=value["bank_manifest_sha256"],
                                      source_hashes=value["source_files"], source_commit=setup.source_commit)


def test_unapproved_outcome_member_not_hashed(tmp_path):
    write_json(tmp_path / "READER_INPUT_SEAL.json", {"schema": "e73-seal-v1", "status": "COMPLETE", "track": "C",
        "files": {"nla.jsonl": {"sha256": "a" * 64, "bytes": 123}}})
    with patch.object(package, "verify_seal") as verify:
        with pytest.raises(ValueError, match="Forbidden outcome"):
            package.checked_seal(tmp_path, "READER_INPUT_SEAL.json", "reader_inputs")
        verify.assert_not_called()


def test_npz_label_member_rejected():
    stream = io.BytesIO()
    np.savez(stream, ids=np.asarray(["a" * 32]), block44=np.zeros((1, 5120), np.float16), block42=np.zeros((1, 5120), np.float16), label=np.array([0]))
    with pytest.raises(ValueError, match="unexpected or duplicate member"):
        package.validate_residual_bytes(stream.getvalue())


def test_changed_residuals_cannot_be_resealed_to_replace_export(setup):
    path = setup.reader_inputs / "reader-input-000.npz"
    with np.load(path, allow_pickle=False) as data:
        copied = {name: data[name] for name in data.files}
    copied["block44"][0, 0] = 1
    np.savez(path, **copied)
    # Even before selection comparison, its immutable export seal catches this.
    with pytest.raises(ValueError, match="sealed file changed"):
        package.prepare(setup)
