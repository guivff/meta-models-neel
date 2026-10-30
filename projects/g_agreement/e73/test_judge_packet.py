"""Synthetic CPU custody/export tests; no real native outputs or API calls."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pytest

from . import judge_packet as packet
from .custody import forecast_proof, seal, sha256, write_json
from .preflight import BANK_HASH_FIELDS, NATIVE_SOURCES


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def write_lines(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.PIPE, text=True).strip()


@pytest.fixture(scope="module")
def runtime():
    commit = git(packet.REPO, "rev-parse", "HEAD")
    sources = {name: hashlib.sha256(packet.git_bytes(packet.REPO, commit, name)).hexdigest() for name in NATIVE_SOURCES}
    return commit, sources


def reseal(directory):
    path = directory / "READER_SEAL.json"
    path.unlink(missing_ok=True)
    seal(directory, path.name, [directory / name for name in sorted(packet.NATIVE_MEMBERS)],
         status="COMPLETE", track="C", reader_outputs_unopened=True)
    return sha256(path)


@pytest.fixture
def setup(tmp_path, runtime, monkeypatch, request):
    controls = getattr(request, "param", False)
    states = ("W7", "W8") if controls else packet.STATES
    per_shard = 100 * len(states)
    runtime_commit, source_map = runtime
    # The new exporter is intentionally uncommitted during these synthetic tests.
    # Exercise its actual Git gate independently below, without mutating the repo.
    monkeypatch.setattr(packet, "adapter_source_receipt", lambda repo, commit:
                        {"commit": commit, "synthetic_test_only": True})
    labels, items = [], []
    for sn, state in enumerate(states):
        for split in ("dev", "test"):
            rows = []
            for i in range(316 if state == "W8" else 400):
                uid = digest(f"synthetic|{state}|{split}|{i}")[:32]
                docnum = sn * 1000 + i + 1 + (2**255 if split == "test" else 0)
                rows.append({"id": uid, "state": state, "split": split, "label": i % 2,
                             "doc_hash": f"{docnum:064x}", "reader_selected": False})
                items.append({"id": uid, "input_ids": [0] * 256})
            rows.sort(key=lambda x: x["id"])
            for i, row in enumerate(rows):
                row["reader_selected"] = split == "test" and i < 200
            labels.extend(rows)
    write_lines(tmp_path / "items.jsonl", items)
    write_lines(tmp_path / "labels.jsonl", labels)
    write_json(tmp_path / "GATE_REPORT.json", {"included_states": list(packet.STATES), "excluded_states": ["W6", "W7", "W8"]})
    if controls:
        from .test_controls import control_gate
        write_json(tmp_path / "GATE_REPORT.json", {**control_gate(), "excluded_states": ["W6"]})
    bank = {key: "a" * 64 for key in BANK_HASH_FIELDS}
    bank.update(experiment="E73", stage="BOW_GATE_SEALED", items=len(items), context_tokens=256,
                input_schema=["id", "input_ids"], code_sha256={n: "b" * 64 for n in ("sources.py", "states.py", "sample.py", "bow.py")},
                items_sha256=sha256(tmp_path / "items.jsonl"), private_labels_sha256=sha256(tmp_path / "labels.jsonl"),
                gate_report_sha256=sha256(tmp_path / "GATE_REPORT.json"))
    bank_path = tmp_path / "BANK_MANIFEST.json"
    write_json(bank_path, bank)
    if controls:
        monkeypatch.setattr(packet, "CONTROL_MANIFEST", sha256(bank_path))
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    selected = sorted(r["id"] for r in labels if r["reader_selected"])
    shards = []
    for i in range(2):
        path = inputs / f"reader-input-{i:03d}.npz"
        np.savez(path, ids=np.asarray(selected[i * per_shard:(i + 1) * per_shard]),
                 block44=np.zeros((per_shard, 5120), np.float16), block42=np.zeros((per_shard, 5120), np.float16))
        shards.append({"file": path.name, "count": per_shard, "bytes": path.stat().st_size, "sha256": sha256(path)})
    index = inputs / "READER_INPUTS.json"
    write_json(index, {"schema": "e73-reader-inputs-v1", "bank_manifest_sha256": sha256(bank_path),
        "source_capture_seals": [{"seal_sha256": "c" * 64}], "probe_seal_sha256": "d" * 64,
        "shards": shards, "total": 2 * per_shard, "labels_present": False})
    seal(inputs, "READER_INPUT_SEAL.json", sorted(inputs.iterdir()), status="COMPLETE", track="C", labels_present=False)
    forecast_repo = tmp_path / "forecast_repo"
    forecast_repo.mkdir()
    write_json(forecast_repo / "FORECAST.json", {"synthetic_test_only": True, "bank_manifest_sha256": sha256(bank_path), "reader_index_sha256": sha256(index)})
    git(forecast_repo, "init", "-q")
    git(forecast_repo, "add", ".")
    git(forecast_repo, "-c", "user.name=E73 Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Synthetic forecast fixture")
    fc = git(forecast_repo, "rev-parse", "HEAD")
    fs = sha256(forecast_repo / "FORECAST.json")
    go = {"schema": "e73-reader-go-v1", "authorized_by": "I-2", "action": "GO",
          "capture_seal_sha256": sha256(index), "bank_manifest_sha256": sha256(bank_path),
          "jforecast_commit": fc, "jforecast_sha256": fs, "judging_authorized": False}
    write_json(tmp_path / "GO.json", go)
    write_json(tmp_path / "FORECAST_PROOF.json", forecast_proof(forecast_repo, fc, "FORECAST.json", fs))
    native = []
    for i, shard in enumerate(shards):
        path = tmp_path / f"native_{i}"
        path.mkdir()
        admission = {"authorized_by": "I-2", "track": "C", "input_sha256": shard["sha256"],
                     "bank_manifest_sha256": sha256(bank_path), "run_id": f"synthetic-{i}", "run_kind": "real",
                     "runtime_commit": runtime_commit, "source_files": source_map,
                     "code_sha256": digest(json.dumps(source_map, sort_keys=True, separators=(",", ":")))}
        write_json(path / "ADMISSION.json", admission)
        write_json(path / "GO.json", go)
        for reader in packet.READERS:
            write_json(path / f"MODEL_READY_{reader}.json", {"synthetic_test_only": True})
            rows = []
            for uid in selected[i * per_shard:(i + 1) * per_shard]:
                rows.append(native_row(uid, reader))
            write_lines(path / f"{reader}.jsonl", rows)
        report = {"schema": "e73-reader-report-v1", "status": "COMPLETE", "track": "C",
                  "completed": {r: per_shard for r in packet.READERS}, "total_per_reader": per_shard,
                  "input_sha256": shard["sha256"], "reader_index_sha256": sha256(index),
                  "jforecast_commit": fc, "jforecast_sha256": fs}
        report.update({k: admission[k] for k in ("run_id", "run_kind", "runtime_commit", "code_sha256")})
        write_json(path / "READER_REPORT.json", report)
        native.append({"path": str(path), "seal_sha256": reseal(path)})
    return {"repo": str(packet.REPO), "adapter_commit": runtime_commit,
            "bank_manifest": str(bank_path), "items": str(tmp_path / "items.jsonl"),
            "labels": str(tmp_path / "labels.jsonl"), "gate": str(tmp_path / "GATE_REPORT.json"),
            "reader_index": str(index), "reader_input_seal_sha256": sha256(inputs / "READER_INPUT_SEAL.json"),
            "go": str(tmp_path / "GO.json"), "forecast_proof": str(tmp_path / "FORECAST_PROOF.json"),
            "forecast_repo": str(forecast_repo), "forecast_path": "FORECAST.json", "native": native,
            "out": str(tmp_path / "public_packet"), "private_key": str(tmp_path / "private/KEY.json")}


def native_row(uid, reader, text=None):
    raw = text if text is not None else ("Synthetic Oracle output." if reader == "oracle" else "before <explanation> Synthetic NLA output. </explanation>")
    closed = "</explanation>" in raw if reader == "nla" else None
    return {"id": uid, "raw_output": raw, "reader": reader, "capture_layer": 44 if reader == "oracle" else 42,
            "max_new_tokens": 128 if reader == "oracle" else 512, "greedy": True, "new_token_ids": [1, 2],
            "n_new_tokens": 2, "finish_reason": "stop", "explanation_closed": closed,
            "truncated": not closed if reader == "nla" else None}


def test_export_exact_full_grid_and_private_orientation(setup):
    result = packet.export_packet(setup)
    assert result["n"] == 2000
    public = packet.read(Path(setup["out"]) / "JUDGE_PACKET.json")
    wire = packet.read(Path(setup["out"]) / "WIRE_PACKET.json")
    key = packet.read(setup["private_key"])
    assert {x["state"] for x in key} == set(packet.STATES)
    assert all(x["value"] == ("A" if x["label"] == 0 else "B") for x in key)
    assert all(set(x) == {"id", "property", "values", "readout"} for x in public)
    assert all(set(x) == {"id", "rubric", "readout"} for x in wire)
    assert all(x["id"] != k["source_id"] for x, k in zip(public, key))
    rubric = packet.frozen_rubric(packet.REPO)
    for p, w, k in zip(public, wire, key):
        assert p["id"] == w["id"] == k["opaque_id"]
        assert p["property"] == packet.PROPERTIES[k["state"]]
        assert p["values"] == dict(zip(("A", "B"), packet.STATE_VALUES[k["state"]]))
        assert w == packet.render_record(p, rubric)
    assert packet.read(Path(setup["out"]) / "PROVENANCE.json")["api_calls"] == 0
    assert set(packet.read(Path(setup["out"]) / "BLIND_SEAL.json")["files"]) == {"JUDGE_PACKET.json", "JUDGE_RUBRIC.md", "PROVENANCE.json"}


@pytest.mark.parametrize("setup", [True], indirect=True)
def test_control_export_keeps_separate_800_readout_grid(setup):
    result = packet.export_packet(setup)
    assert result["n"] == 800
    key = packet.read(setup["private_key"])
    assert {k["state"] for k in key} == {"W7", "W8"}
    provenance = packet.read(Path(setup["out"]) / "PROVENANCE.json")
    assert provenance["per_reader_counts"] == {"oracle": 400, "nla": 400}
    assert provenance["per_state_per_reader"] == {"W7": 200, "W8": 200}


@pytest.mark.parametrize("setup", [True], indirect=True)
def test_control_wrong_forecast_still_fails_before_outcomes(setup, monkeypatch):
    setup["forecast_path"] = "missing-uncommitted.json"
    forbid_output_reads(monkeypatch)
    with pytest.raises(subprocess.CalledProcessError):
        packet.export_packet(setup)


def test_renderer_matches_frozen_e56_function_verbatim():
    source = packet.git_bytes(packet.REPO, packet.RENDER_COMMIT, packet.RENDER_PATH)
    tree = ast.parse(source)
    nodes = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == "render_record")
             or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SUFFIX" for t in n.targets))]
    namespace = {"require": packet.require}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "frozen_e56_render", "exec"), namespace)
    rubric = packet.frozen_rubric(packet.REPO)
    for state in packet.STATES:
        record = {"id": "a" * 32, "property": packet.PROPERTIES[state],
                  "values": dict(zip(("A", "B"), packet.STATE_VALUES[state])), "readout": "Synthetic only."}
        assert packet.render_record(record, rubric) == namespace["render_record"](record, rubric)


def test_actual_adapter_freeze_gate_checks_every_local_source(tmp_path):
    for name in packet.ADAPTER_SOURCES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((packet.REPO / name).read_bytes())
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=E73 Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Synthetic exporter freeze")
    commit = git(tmp_path, "rev-parse", "HEAD")
    receipt = packet.adapter_source_receipt(tmp_path, commit)
    assert set(receipt["source_files"]) == packet.ADAPTER_SOURCES
    path = tmp_path / "projects/g_agreement/e73/judge_packet.py"
    path.write_text("# A different exporter must fail source binding.\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=E73 Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Synthetic mutation")
    with pytest.raises(ValueError, match="commit/source mismatch"):
        packet.adapter_source_receipt(tmp_path, git(tmp_path, "rev-parse", "HEAD"))


@pytest.mark.parametrize("raw,expected", [
    ("prefix<explanation>  inside\ntext  </explanation>tail", "inside\ntext"),
    ("<explanation>unclosed", "<explanation>unclosed"), ("", ""),
    ("without opener</explanation>", "without opener</explanation>"),
    ("<explanation></explanation>", ""),
])
def test_nla_frozen_text_policy_preserves_malformed_outputs(raw, expected):
    assert packet.native_text(native_row("a" * 32, "nla", raw), "nla") == expected


def forbid_output_reads(monkeypatch):
    original = packet.checked_member
    def checked(directory, name, seal):
        assert name not in {"oracle.jsonl", "nla.jsonl"}, "Outcome opened before all prerequisites passed"
        return original(directory, name, seal)
    monkeypatch.setattr(packet, "checked_member", checked)


def test_wrong_go_fails_before_output_open(setup, monkeypatch):
    go = packet.read(setup["go"])
    go["capture_seal_sha256"] = "0" * 64
    write_json(Path(setup["go"]), go)
    forbid_output_reads(monkeypatch)
    with pytest.raises(ValueError, match="GO binding"):
        packet.export_packet(setup)


def test_uncommitted_forecast_fails_before_output_open(setup, monkeypatch):
    setup["forecast_path"] = "missing-uncommitted.json"
    forbid_output_reads(monkeypatch)
    with pytest.raises(subprocess.CalledProcessError):
        packet.export_packet(setup)


def test_final_shard_incomplete_fails_before_any_output_open(setup, monkeypatch):
    entry = setup["native"][-1]
    path = Path(entry["path"]) / "READER_SEAL.json"
    value = packet.read(path)
    value["status"] = "NO_FIT"
    write_json(path, value)
    entry["seal_sha256"] = sha256(path)
    forbid_output_reads(monkeypatch)
    with pytest.raises(ValueError, match="not COMPLETE"):
        packet.export_packet(setup)


def test_final_shard_wrong_report_binding_fails_before_outputs(setup, monkeypatch):
    entry = setup["native"][-1]
    directory = Path(entry["path"])
    report = packet.read(directory / "READER_REPORT.json")
    report["jforecast_sha256"] = "0" * 64
    write_json(directory / "READER_REPORT.json", report)
    entry["seal_sha256"] = reseal(directory)
    forbid_output_reads(monkeypatch)
    with pytest.raises(ValueError, match="index/forecast"):
        packet.export_packet(setup)


def test_native_order_cannot_change_even_after_resealing(setup):
    entry = setup["native"][0]
    directory = Path(entry["path"])
    path = directory / "oracle.jsonl"
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    rows[0], rows[1] = rows[1], rows[0]
    write_lines(path, rows)
    entry["seal_sha256"] = reseal(directory)
    with pytest.raises(ValueError, match="ID order/coverage"):
        packet.export_packet(setup)
    assert not Path(setup["out"]).exists()


def test_shard_omission_is_not_partial_export(setup, monkeypatch):
    setup["native"].pop()
    forbid_output_reads(monkeypatch)
    with pytest.raises(ValueError, match="Complete native shard"):
        packet.export_packet(setup)


def test_private_key_cannot_be_inside_public_packet(setup):
    setup["private_key"] = str(Path(setup["out"]) / "KEY.json")
    with pytest.raises(ValueError, match="outside public"):
        packet.export_packet(setup)


def test_probe_based_state_reduction_is_rejected(setup, monkeypatch):
    gate = packet.read(setup["gate"])
    gate["included_states"].remove("W3")
    gate["excluded_states"].append("W3")
    write_json(Path(setup["gate"]), gate)
    bank = packet.read(setup["bank_manifest"])
    bank["gate_report_sha256"] = sha256(Path(setup["gate"]))
    write_json(Path(setup["bank_manifest"]), bank)
    forbid_output_reads(monkeypatch)
    with pytest.raises(ValueError, match="BOW state inventory"):
        packet.export_packet(setup)


def test_native_hash_tampering_rejected_without_creating_packet(setup):
    path = Path(setup["native"][0]["path"]) / "oracle.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="hash/size mismatch"):
        packet.export_packet(setup)
    assert not Path(setup["out"]).exists()


def test_native_nla_metadata_cannot_hide_truncation():
    row = native_row("a" * 32, "nla", "<explanation>Unclosed")
    row["truncated"] = False
    with pytest.raises(ValueError, match="closure metadata"):
        packet.native_text(row, "nla")
