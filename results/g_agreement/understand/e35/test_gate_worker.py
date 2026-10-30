"""Synthetic CPU hook/clock checks for E35, dated 2026-10-25; no GPU work."""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from torch import nn


_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
try:
    _SPEC = importlib.util.spec_from_file_location("e35_worker_under_test", _HERE / "gate_worker.py")
    worker = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(worker)
finally:
    sys.path.remove(str(_HERE))


class ToyBlock(nn.Module):
    def __init__(self, index, tuple_output=False, nonfinite=False):
        super().__init__()
        self.index = index
        self.tuple_output = tuple_output
        self.nonfinite = nonfinite

    def forward(self, x):
        y = x + self.index + 1
        if self.nonfinite:
            y = y * float("nan")
        return (y, "unused") if self.tuple_output else y


class ToyTarget(nn.Module):
    def __init__(self, *, nested=False, tuple_output=False, fail_after_capture=False, nonfinite=False):
        super().__init__()
        self.model = nn.Module()
        container = self.model
        if nested:
            self.model.language_model = nn.Module()
            container = self.model.language_model
        container.layers = nn.ModuleList(
            ToyBlock(i, tuple_output=tuple_output and i == 44, nonfinite=nonfinite and i == 44)
            for i in range(64)
        )
        self.nested = nested
        self.fail_after_capture = fail_after_capture

    def forward(self, input_ids, *, use_cache, logits_to_keep):
        assert use_cache is False
        assert logits_to_keep == 1
        x = torch.stack([input_ids, input_ids * 2], dim=-1).double()
        blocks = self.model.language_model.layers if self.nested else self.model.layers
        for i, block in enumerate(blocks):
            result = block(x)
            x = result[0] if isinstance(result, tuple) else result
            if i == 44 and self.fail_after_capture:
                raise RuntimeError("synthetic forward failure after block44")
        return x


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("tuple_output", [False, True])
def test_capture_is_raw_zero_indexed_block44_post_output(nested, tuple_output):
    model = ToyTarget(nested=nested, tuple_output=tuple_output)
    actual = worker.capture44(model, [10, 20, 30, 40], [3, 1], device="cpu")
    # A post-hook after index44 includes increments 1..45, not 1..44 or 1..46.
    expected = torch.tensor([[40.0, 80.0], [20.0, 40.0]]) + sum(range(1, 46))
    assert actual.dtype == torch.float32
    assert not actual.requires_grad
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    assert not torch.equal(actual, expected - 45)
    assert not torch.equal(actual, expected + 46)
    assert len(worker.decoder_blocks(model)[44]._forward_hooks) == 0


def test_hook_cleanup_on_forward_failure_preserves_existing_hooks():
    model = ToyTarget(tuple_output=True, fail_after_capture=True)
    block = worker.decoder_blocks(model)[44]
    seen = []
    existing = block.register_forward_hook(lambda *args: seen.append(True))
    try:
        with pytest.raises(RuntimeError, match="synthetic forward failure"):
            worker.capture44(model, [1, 2], [0], device="cpu")
        assert seen == [True]
        assert len(block._forward_hooks) == 1
        assert existing.id in block._forward_hooks
    finally:
        existing.remove()


def test_nonfinite_capture_fails_and_removes_hook():
    model = ToyTarget(nonfinite=True)
    with pytest.raises(ValueError, match="finite raw block44"):
        worker.capture44(model, [1, 2], [0], device="cpu")
    assert len(worker.decoder_blocks(model)[44]._forward_hooks) == 0


@pytest.mark.parametrize("ids,positions", [([], [0]), ([1], []), ([1, 2], [0, 0]), ([1], [-1]), ([1], [1])])
def test_invalid_capture_positions_fail_before_hook_install(ids, positions):
    model = ToyTarget()
    with pytest.raises(ValueError, match="valid unique prefix positions"):
        worker.capture44(model, ids, positions, device="cpu")
    assert len(worker.decoder_blocks(model)[44]._forward_hooks) == 0


def test_decoder_layout_requires_64_blocks():
    model = ToyTarget()
    model.model.layers = nn.ModuleList([ToyBlock(0)])
    with pytest.raises(ValueError, match="64-block"):
        worker.decoder_blocks(model)


REQUEST_SHA = "a" * 64
START = worker.STOP - 2 * 86400


def assignment(**changes):
    values = {
        "issuer": "integrator", "experiment": "E35", "stage": "gate",
        "gpu_count": 1, "pod_id": "synthetic-pod", "request_sha256": REQUEST_SHA,
        "source_commit": "a" * 40,
        "source_pushed": True, "external_hardstop_verified": True, "hold_renewer_verified": True,
        "previous_gpu_seconds": 0, "allocated_gpu_seconds": 3600,
        "provider_created_epoch": START, "setup_deadline_epoch": START + 1500,
        "deadline_epoch": START + 3600,
    }
    values.update(changes)
    return values


@pytest.fixture
def fake_time(monkeypatch):
    state = {"now": START + 60}
    monkeypatch.setattr(worker.time, "time", lambda: state["now"])
    monkeypatch.setenv("RUNPOD_POD_ID", "synthetic-pod")
    return state


@pytest.mark.parametrize("field", [
    "previous_gpu_seconds", "allocated_gpu_seconds", "provider_created_epoch",
    "deadline_epoch", "setup_deadline_epoch",
])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), True, "3600", None])
def test_timing_fields_must_be_finite_real_numbers(field, bad, fake_time):
    with pytest.raises(ValueError, match="finite assignment timing"):
        worker.Clock(assignment(**{field: bad}), REQUEST_SHA)


def test_total_21600_includes_previous_stages_at_inclusive_boundary(fake_time):
    clock = worker.Clock(assignment(previous_gpu_seconds=18000), REQUEST_SHA)
    assert clock.a["previous_gpu_seconds"] + clock.a["allocated_gpu_seconds"] == 21600
    with pytest.raises(ValueError, match="total/stage GPU allocation"):
        worker.Clock(assignment(previous_gpu_seconds=18000.001), REQUEST_SHA)


@pytest.mark.parametrize("pod_id", [None, "other-pod"])
def test_assignment_is_bound_to_provider_pod_identity(pod_id, fake_time, monkeypatch):
    if pod_id is None:
        monkeypatch.delenv("RUNPOD_POD_ID", raising=False)
    else:
        monkeypatch.setenv("RUNPOD_POD_ID", pod_id)
    with pytest.raises(ValueError, match="does not belong to this RunPod pod"):
        worker.Clock(assignment(), REQUEST_SHA)


def test_pushed_source_commit_is_required(fake_time):
    values = assignment()
    del values["source_commit"]
    with pytest.raises(ValueError, match="exact pushed source commit"):
        worker.Clock(values, REQUEST_SHA)


@pytest.mark.parametrize("commit", [None, True, 123, "", "a" * 39, "a" * 41, "A" * 40, "g" * 40, "a" * 39 + " "])
def test_pushed_source_commit_requires_exact_lowercase_full_hash(commit, fake_time):
    with pytest.raises(ValueError, match="exact pushed source commit"):
        worker.Clock(assignment(source_commit=commit), REQUEST_SHA)


@pytest.mark.parametrize("changes", [
    {"previous_gpu_seconds": -1}, {"allocated_gpu_seconds": 3600.001},
    {"allocated_gpu_seconds": worker.RESERVE}, {"allocated_gpu_seconds": 0},
])
def test_stage_and_nonnegative_budget_limits(changes, fake_time):
    with pytest.raises(ValueError, match="total/stage GPU allocation"):
        worker.Clock(assignment(**changes), REQUEST_SHA)


@pytest.mark.parametrize("offset", [1500, 1501, 3600, -1])
def test_expired_or_not_yet_created_assignment_rejected(offset, fake_time):
    fake_time["now"] = START + offset
    with pytest.raises(ValueError, match="setup assignment expired or invalid"):
        worker.Clock(assignment(), REQUEST_SHA)


def test_deadline_cannot_extend_allocation_or_programme(fake_time):
    with pytest.raises(ValueError, match="absolute/provider/programme deadline"):
        worker.Clock(assignment(deadline_epoch=START + 3601), REQUEST_SHA)
    late_start = worker.STOP - 1000
    fake_time["now"] = late_start + 10
    with pytest.raises(ValueError, match="absolute/provider/programme deadline"):
        worker.Clock(assignment(provider_created_epoch=late_start,
                                setup_deadline_epoch=late_start + 500,
                                deadline_epoch=late_start + 3600), REQUEST_SHA)


def test_science_clock_can_start_once_and_never_reset(fake_time):
    clock = worker.Clock(assignment(), REQUEST_SHA)
    fake_time["now"] += 20
    clock.begin_science()
    first = clock.science_start
    assert clock.status == "PILOT"
    fake_time["now"] += 40
    with pytest.raises(ValueError, match="science clock cannot reset"):
        clock.begin_science()
    assert clock.science_start == first
    record = clock.record()
    assert record["first_science_epoch"] == first
    assert record["science_clock_resets"] == 0
    assert record["provider_elapsed_seconds"] == 120


def test_setup_clock_expires_at_boundary(fake_time):
    clock = worker.Clock(assignment(), REQUEST_SHA)
    fake_time["now"] = clock.a["setup_deadline_epoch"] - 0.001
    clock.check()
    fake_time["now"] = clock.a["setup_deadline_epoch"]
    with pytest.raises(worker.NoFit, match="clock exhausted"):
        clock.check()


def test_forecast_cap_runs_from_original_science_start(fake_time):
    clock = worker.Clock(assignment(), REQUEST_SHA)
    clock.begin_science()
    first = clock.science_start
    clock.pilot_seconds = [10.0, 20.0, 30.0]
    fake_time["now"] += 60
    clock.admit(10)
    assert clock.forecast == 260
    assert clock.science_limit == 750
    assert clock.science_start == first
    assert clock.status == "RUNNING"
    fake_time["now"] = first + 749.999
    clock.check()
    fake_time["now"] = first + 750
    with pytest.raises(worker.NoFit, match="clock exhausted"):
        clock.check()


def test_retrieval_reserve_remains_inside_allocation(fake_time):
    clock = worker.Clock(assignment(), REQUEST_SHA)
    clock.begin_science()
    fake_time["now"] = START + 3600 - worker.RESERVE - 0.001
    clock.check()
    fake_time["now"] = START + 3600 - worker.RESERVE
    with pytest.raises(worker.NoFit, match="clock exhausted"):
        clock.check()


def test_unfit_full_sample_forecast_stops_without_reset(fake_time):
    clock = worker.Clock(assignment(), REQUEST_SHA)
    clock.begin_science()
    first = clock.science_start
    clock.pilot_seconds = [100.0, 100.0, 100.0]
    fake_time["now"] += 300
    with pytest.raises(worker.NoFit, match="full frozen sample does not fit"):
        clock.admit(50)
    assert clock.forecast == 5300
    assert clock.science_limit == START + 3600 - worker.RESERVE - first
    assert clock.science_start == first
    assert clock.status != "RUNNING"
    assert clock.tokens_done == 0
    with pytest.raises(ValueError, match="cannot reset"):
        clock.begin_science()


@pytest.mark.parametrize("timings", [[], [1, 2], [1, 2, 3, 4], [1, 0, 1], [1, -1, 1], [1, float("inf"), 1], [1, float("nan"), 1]])
def test_admission_requires_three_positive_finite_pilots(timings, fake_time):
    clock = worker.Clock(assignment(), REQUEST_SHA)
    clock.begin_science()
    clock.pilot_seconds = timings
    with pytest.raises(ValueError, match="three complete warmed pilot timings"):
        clock.admit(10)


@pytest.fixture
def source_request(tmp_path):
    base = tmp_path / "results/g_agreement/understand/e35"
    base.mkdir(parents=True)
    names = ["gate_worker.py", "gate_inputs.py", "gate_math.py", "sae.py",
             "GATE_SAMPLE.json", "GATE_PLAN.20261025.json", "REGISTRATION.5731e92e.md"]
    pins = {}
    for name in names:
        path = base / name
        path.write_text("synthetic pinned source\n")
        pins[name] = worker.sha(path)
    return tmp_path, base, {"source_files": pins}


def test_complete_pinned_source_set_is_accepted(source_request):
    root, _, request = source_request
    worker.verify_sources(request, root=root)


def test_source_content_tampering_rejected(source_request):
    root, base, request = source_request
    (base / "gate_math.py").write_text("synthetic tampered source\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        worker.verify_sources(request, root=root)


def test_missing_required_source_pin_rejected(source_request):
    root, _, request = source_request
    del request["source_files"]["sae.py"]
    with pytest.raises(ValueError, match="complete gate source/input pins"):
        worker.verify_sources(request, root=root)


def test_source_path_traversal_rejected_even_if_hash_matches(source_request):
    root, base, request = source_request
    outside = base.parent / "outside.txt"
    outside.write_text("synthetic outside source\n")
    request["source_files"]["../outside.txt"] = worker.sha(outside)
    with pytest.raises(ValueError, match="checksum mismatch"):
        worker.verify_sources(request, root=root)


def test_source_symlink_escape_rejected_even_if_hash_matches(source_request):
    root, base, request = source_request
    outside = base.parent / "outside.txt"
    outside.write_text("synthetic outside source\n")
    (base / "escaped.py").symlink_to(outside)
    request["source_files"]["escaped.py"] = worker.sha(outside)
    with pytest.raises(ValueError, match="checksum mismatch"):
        worker.verify_sources(request, root=root)


@pytest.mark.parametrize("second_name", ["gate", "renamed-gate"])
def test_claim_is_once_per_stage_parent_not_output_basename(tmp_path, fake_time, second_name):
    parent = tmp_path / "stage"
    out = parent / "gate"
    worker.claim_run(out, "assignment-one", "request-one")
    marker = parent / "gate.RUN_ONCE.json"
    original = marker.read_bytes()
    assert out.is_dir()
    record = json.loads(original)
    assert record["assignment_sha256"] == "assignment-one"
    assert record["request_sha256"] == "request-one"
    fake_time["now"] += 10
    with pytest.raises(FileExistsError):
        worker.claim_run(parent / second_name, "assignment-two", "request-two")
    assert marker.read_bytes() == original
    if second_name != "gate":
        assert not (parent / second_name).exists()


def test_preexisting_output_consumes_marker_and_preserves_existing_data(tmp_path, fake_time):
    out = tmp_path / "stage" / "gate"
    out.mkdir(parents=True)
    evidence = out / "existing-evidence.txt"
    evidence.write_text("preserve this evidence\n")
    with pytest.raises(FileExistsError):
        worker.claim_run(out, "assignment-one", "request-one")
    marker = out.parent / "gate.RUN_ONCE.json"
    original = marker.read_bytes()
    assert json.loads(original)["request_sha256"] == "request-one"
    assert evidence.read_text() == "preserve this evidence\n"
    with pytest.raises(FileExistsError):
        worker.claim_run(out.parent / "retry", "assignment-two", "request-two")
    assert marker.read_bytes() == original
    assert not (out.parent / "retry").exists()


@pytest.fixture
def execution_files(tmp_path, monkeypatch):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "GATE_SAMPLE.json").write_text("{}\n")
    (inputs / worker.REQUEST_FILENAME).write_text("{}\n")
    assignment_path = inputs / "ASSIGNMENT.json"
    assignment_path.write_text("{}\n")
    out = tmp_path / "output"
    out.mkdir()
    monkeypatch.setattr(worker, "HERE", inputs)
    # Neither CUDA API touches a device in these CPU integration tests.
    monkeypatch.setattr(torch.cuda, "synchronize", lambda: None)
    monkeypatch.setattr(torch.cuda, "empty_cache", lambda: None)
    return SimpleNamespace(out=out, assignment=assignment_path,
                           corpus=inputs / "corpus", manifest=inputs / "manifest")


@pytest.mark.parametrize("failure,status", [(ValueError, "INCOMPLETE"), (worker.NoFit, "NO_FIT")])
def test_operational_error_never_becomes_scientific_gate_failure(execution_files, fake_time, monkeypatch, failure, status):
    def broken_assets(_):
        raise failure("synthetic operational stop")

    monkeypatch.setattr(worker, "load_assets", broken_assets)
    clock = worker.Clock(assignment(), REQUEST_SHA)
    assert worker.execute(execution_files, clock) == 2
    report = json.loads((execution_files.out / "GATE_RESULT.json").read_text())
    assert report["status"] == status
    assert report["metrics"] is None
    assert report["next_stage"] == "report_operational_stop"
    assert report["training_steps"] == report["decomposition_calls"] == 0
    seal = json.loads((execution_files.out / "OUTPUT_SEAL.json").read_text())
    assert seal["status"] == status
    assert seal["files"]["GATE_RESULT.json"] == worker.sha(execution_files.out / "GATE_RESULT.json")


@pytest.mark.parametrize("reconstruction_scale,status,next_stage", [
    (0.5, "PASS", "freeze_latent_rubric"),
    (0.0, "FAIL", "prepare_registered_TopK_training"),
])
def test_scientific_gate_completion_drives_only_registered_next_stage(
        execution_files, fake_time, monkeypatch, reconstruction_scale, status, next_stage):
    # Keep the true 50,000-token gate and actual metric accumulator, using a
    # one-dimensional synthetic residual and 11 latents instead of model weights.
    sample = {"pilot_document_ids": ["pilot-a", "pilot-b", "pilot-c"],
              "documents": [{"id": "heldout", "positions": list(range(50000))}]}
    (worker.HERE / "GATE_SAMPLE.json").write_text(json.dumps(sample))
    monkeypatch.setattr(worker, "load_assets", lambda _: (object(), object(), worker.HERE / "tokenizer"))
    monkeypatch.setattr(worker, "verify_sample", lambda *args: {
        name: [0] for name in ["pilot-a", "pilot-b", "pilot-c", "heldout"]})
    actual_accumulator = worker.GateAccumulator
    monkeypatch.setattr(worker, "GateAccumulator", lambda *args: actual_accumulator(1, 11))
    actual_open_memmap = np.lib.format.open_memmap

    def tiny_memmap(path, **kwargs):
        assert kwargs["shape"] == (50000, 5120)
        return actual_open_memmap(path, mode=kwargs["mode"], dtype=kwargs["dtype"], shape=(50000, 1))

    monkeypatch.setattr(np.lib.format, "open_memmap", tiny_memmap)
    timer = iter([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    monkeypatch.setattr(worker.time, "monotonic", lambda: next(timer))

    def synthetic_process(model, sae, ids, positions):
        h = ((np.arange(len(positions)) % 2) * 2 - 1).astype("float32")[:, None]
        return h, reconstruction_scale * h, np.ones(11, dtype=bool)

    monkeypatch.setattr(worker, "process", synthetic_process)
    clock = worker.Clock(assignment(), REQUEST_SHA)
    assert worker.execute(execution_files, clock) == 0
    report = json.loads((execution_files.out / "GATE_RESULT.json").read_text())
    assert report["status"] == status
    assert report["metrics"]["passed"] is (status == "PASS")
    assert report["next_stage"] == next_stage
    assert report["clock"]["tokens_done"] == 50000
    assert report["clock"]["documents_done"] == 1
    assert report["clock"]["science_clock_resets"] == 0
    assert report["training_steps"] == report["decomposition_calls"] == 0
    seal = json.loads((execution_files.out / "OUTPUT_SEAL.json").read_text())
    assert seal["status"] == status
    for filename, expected in seal["files"].items():
        assert worker.sha(execution_files.out / filename) == expected
