"""E35 §133/7 operational rerun custody checks, dated 2026-10-25; CPU only."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest


_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
try:
    _SPEC = importlib.util.spec_from_file_location("e35_rerun_worker_under_test", _HERE / "gate_worker.py")
    worker = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(worker)
finally:
    sys.path.remove(str(_HERE))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


@pytest.fixture
def bookkeeping(tmp_path):
    handoff = tmp_path / "results/g_agreement/blindspot/HANDOFF.md"
    handoff.parent.mkdir(parents=True)
    handoff.write_text(f"2026-10-25: Integrator accounted for pod {worker.UNACCOUNTED_POD}; closed.\n")
    assignment = {
        "gate_attempt": 2,
        "rerun_authority_commit": worker.RERUN_AUTHORITY,
        "previous_gpu_seconds": 180,
        "prior_pod_accounting": {
            "pod_id": worker.UNACCOUNTED_POD,
            "resolved": True,
            "handoff_sha256": worker.sha(handoff),
        },
    }
    return tmp_path, handoff, assignment


def test_accepts_exact_authorized_second_attempt_with_pinned_accounting(bookkeeping):
    root, _, assignment = bookkeeping
    worker.verify_rerun_assignment(assignment, root=root)
    assignment["previous_gpu_seconds"] = 180.5
    worker.verify_rerun_assignment(assignment, root=root)


@pytest.mark.parametrize("attempt", [None, 1, 3, 0, -1, "2", 2.0, True, False])
def test_no_first_or_third_or_coerced_attempt(bookkeeping, attempt):
    root, _, assignment = bookkeeping
    assignment["gate_attempt"] = attempt
    with pytest.raises(ValueError):
        worker.verify_rerun_assignment(assignment, root=root)


def test_missing_attempt_rejected(bookkeeping):
    root, _, assignment = bookkeeping
    del assignment["gate_attempt"]
    with pytest.raises(ValueError):
        worker.verify_rerun_assignment(assignment, root=root)


@pytest.mark.parametrize("authority", [None, "01c5775", "a" * 40, 133, True])
def test_exact_ruling_commit_required(bookkeeping, authority):
    root, _, assignment = bookkeeping
    assignment["rerun_authority_commit"] = authority
    with pytest.raises(ValueError):
        worker.verify_rerun_assignment(assignment, root=root)


@pytest.mark.parametrize("previous", [None, False, True, "180", -1, 0, 179.999, float("nan"), float("inf"), float("-inf")])
def test_finite_prior_charge_at_least_180_required(bookkeeping, previous):
    root, _, assignment = bookkeeping
    assignment["previous_gpu_seconds"] = previous
    with pytest.raises(ValueError):
        worker.verify_rerun_assignment(assignment, root=root)


@pytest.mark.parametrize("record", [None, [], "accounted", {},
    {"pod_id": "some-other-pod", "resolved": True},
    {"pod_id": worker.UNACCOUNTED_POD, "resolved": False},
    {"pod_id": worker.UNACCOUNTED_POD, "resolved": 1},
    {"pod_id": worker.UNACCOUNTED_POD, "resolved": "true"}])
def test_exact_pod_and_boolean_resolved_evidence_required(bookkeeping, record):
    root, _, assignment = bookkeeping
    assignment["prior_pod_accounting"] = record
    with pytest.raises(ValueError):
        worker.verify_rerun_assignment(assignment, root=root)


def test_missing_handoff_rejected(bookkeeping):
    root, handoff, assignment = bookkeeping
    handoff.unlink()
    with pytest.raises(ValueError, match="HANDOFF"):
        worker.verify_rerun_assignment(assignment, root=root)


def test_handoff_must_match_actual_pinned_bytes(bookkeeping):
    root, handoff, assignment = bookkeeping
    before = handoff.read_text()
    handoff.write_text(before + "Additional bookkeeping, not the assigned snapshot.\n")
    with pytest.raises(ValueError, match="HANDOFF"):
        worker.verify_rerun_assignment(assignment, root=root)


def test_correct_hash_without_required_pod_is_not_accounting_evidence(bookkeeping):
    root, handoff, assignment = bookkeeping
    handoff.write_text("2026-10-25: Another pod was accounted for.\n")
    assignment["prior_pod_accounting"]["handoff_sha256"] = worker.sha(handoff)
    with pytest.raises(ValueError, match="identify"):
        worker.verify_rerun_assignment(assignment, root=root)


@pytest.mark.parametrize("second_basename", ["out", "third-attempt", "renamed-output"])
def test_nested_rerun_preserves_consumed_guard_and_rejects_another_claim(tmp_path, monkeypatch, second_basename):
    stage = tmp_path / "cache/g_agreement/understand/e35"
    stage.mkdir(parents=True)
    original_guard = stage / "gate.RUN_ONCE.json"
    historical_bytes = b'{"request_sha256":"historical-request","epoch":1000}\n'
    original_guard.write_bytes(historical_bytes)
    old_output = stage / "gate-20261025"
    old_output.mkdir()
    old_result = old_output / "GATE_RESULT.json"
    old_result.write_bytes(b'{"status":"INCOMPLETE"}\n')
    original_result_bytes = old_result.read_bytes()
    out = stage / "gate-rerun1-20261025" / "out"
    monkeypatch.setattr(worker.time, "time", lambda: 2000)
    worker.claim_run(out, "new-assignment", "new-request")
    rerun_guard = out.parent / "gate.RUN_ONCE.json"
    rerun_bytes = rerun_guard.read_bytes()
    assert out.is_dir()
    assert json.loads(rerun_bytes)["request_sha256"] == "new-request"
    monkeypatch.setattr(worker.time, "time", lambda: 3000)
    with pytest.raises(FileExistsError):
        worker.claim_run(out.parent / second_basename, "third-assignment", "third-request")
    assert original_guard.read_bytes() == historical_bytes
    assert old_result.read_bytes() == original_result_bytes
    assert rerun_guard.read_bytes() == rerun_bytes
    if second_basename != "out":
        assert not (out.parent / second_basename).exists()


def setup_main(monkeypatch, bookkeeping, *, output=None, invalid_attempt=False):
    root, _, assignment = bookkeeping
    here = root / "results/g_agreement/understand/e35"
    here.mkdir(parents=True)
    request_path = here / worker.REQUEST_FILENAME
    relative_output = "cache/g_agreement/understand/e35/gate-rerun1-20261025/out"
    request = {"output_path": relative_output, "source_files": {}}
    write_json(request_path, request)
    # The live runner must never read the historical request during the rerun.
    (here / "LAUNCH_REQUEST.gate.json").write_text("historical request is not live JSON\n")
    assignment.update({
        "issuer": "integrator", "experiment": "E35", "stage": "gate",
        "gpu_count": 1, "pod_id": "synthetic-rerun-pod", "source_commit": "a" * 40,
        "source_pushed": True, "request_sha256": worker.sha(request_path),
        "external_hardstop_verified": True, "hold_renewer_verified": True,
        "allocated_gpu_seconds": 3600, "provider_created_epoch": 1000,
        "setup_deadline_epoch": 1500, "deadline_epoch": 4600,
    })
    if invalid_attempt:
        assignment["gate_attempt"] = 3
    assignment_path = root / "assignment.json"
    write_json(assignment_path, assignment)
    requested_out = root / (relative_output if output is None else output)
    monkeypatch.setattr(worker, "HERE", here)
    monkeypatch.setattr(worker, "ROOT", root)
    monkeypatch.setattr(worker.time, "time", lambda: 1010)
    monkeypatch.setenv("RUNPOD_POD_ID", assignment["pod_id"])
    verified = []
    monkeypatch.setattr(worker, "verify_sources", lambda obj: verified.append(obj))
    verify_bookkeeping = worker.verify_rerun_assignment
    monkeypatch.setattr(worker, "verify_rerun_assignment", lambda obj: verify_bookkeeping(obj, root=root))
    argv = ["gate_worker.py", "--assignment", str(assignment_path),
            "--corpus", str(root / "unused-corpus.jsonl"),
            "--manifest", str(root / "unused-manifest.json"), "--out", str(requested_out)]
    monkeypatch.setattr(sys, "argv", argv)
    return root, requested_out, request, verified


@pytest.mark.parametrize("output", [
    "cache/g_agreement/understand/e35/gate-20261025",
    "cache/g_agreement/understand/e35/gate-rerun2-20261025/out",
])
def test_main_rejects_unregistered_output_before_claim_or_model_loading(monkeypatch, bookkeeping, output):
    root, _, _, _ = setup_main(monkeypatch, bookkeeping, output=output)
    calls = []
    monkeypatch.setattr(worker, "claim_run", lambda *args: calls.append("claimed"))
    monkeypatch.setattr(worker, "execute", lambda *args: calls.append("executed"))
    with pytest.raises(ValueError, match="output location"):
        worker.main()
    assert calls == []
    assert not (root / "cache").exists()


def test_main_rejects_unauthorized_attempt_before_claim(monkeypatch, bookkeeping):
    root, _, _, _ = setup_main(monkeypatch, bookkeeping, invalid_attempt=True)
    calls = []
    monkeypatch.setattr(worker, "claim_run", lambda *args: calls.append("claimed"))
    monkeypatch.setattr(worker, "execute", lambda *args: calls.append("executed"))
    with pytest.raises(ValueError, match="second gate attempt"):
        worker.main()
    assert calls == []
    assert not (root / "cache").exists()


def test_main_uses_fixed_rerun_request_and_second_execution_cannot_start(monkeypatch, bookkeeping):
    _, out, request, verified = setup_main(monkeypatch, bookkeeping)
    events = []
    monkeypatch.setattr(worker.signal, "signal", lambda *args: None)
    monkeypatch.setattr(worker.signal, "setitimer", lambda *args: None)
    monkeypatch.setattr(worker, "execute", lambda *args: events.append("executed") or 0)
    with pytest.raises(SystemExit) as stopped:
        worker.main()
    assert stopped.value.code == 0
    assert verified == [request]
    assert events == ["executed"]
    marker = out.parent / "gate.RUN_ONCE.json"
    recorded_bytes = marker.read_bytes()
    with pytest.raises(FileExistsError):
        worker.main()
    assert marker.read_bytes() == recorded_bytes
    assert events == ["executed"]
