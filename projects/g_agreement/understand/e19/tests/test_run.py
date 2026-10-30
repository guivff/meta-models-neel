"""CPU-only E19 full-scope, control, budget and fail-closed launch tests."""
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.e19 import run as R, request as Q


def data_and_directions():
    items = [{"id": f"{row}-{i:03}", "feature": row, "cluster": f"cluster-{i//14}"}
             for row in R.ROWS for i in range(84)]
    directions = {row: {"u": np.eye(5, dtype=np.float32)[j], "sigma": 1.5+j, "layer": 21+j}
                  for j, row in enumerate(R.ROWS)}
    donors = [{"recipient_index": i, "donor_index": i//84*84+(i+1)%84} for i in range(len(items))]
    continuation = {row: {"pairs": [{"A": "a", "B": "b", "A_ids": [1], "B_ids": [1]},
                                      {"A": "c", "B": "d", "A_ids": [1], "B_ids": [1]}],
                          "valid_pairs": [1], "primary_status": "EVALUABLE"} for row in R.ROWS}
    continuation[R.CONTENT] = {"pairs": [], "valid_pairs": [], "primary_status": "NOT_EVALUABLE"}
    data = {"items": items, "activations": np.arange(len(items)*5, dtype=np.float32).reshape(-1, 5),
            "donors": donors, "templates": {row: {"olens": [["- a", "- b"], ["- c", "- d"]]} for row in R.ROWS},
            "continuations": {"oracle_prefix": "- ", "rows": continuation},
            "provenance": {"source_e3_input_seal_sha256": "same-e3-input"}}
    return data, directions


def test_schedule_has_every_registered_item_arm_and_alpha_once():
    data, _ = data_and_directions()
    plan = list(R.schedule(data))
    assert len(plan) == (4*6+5)*7*6 == 1218
    actual = Counter((row, arm, alpha, i) for row, arm, alpha, indices in plan for i in indices)
    expected = {(item["feature"], arm, alpha, i) for i, item in enumerate(data["items"])
                for arm in R.arms(item["feature"]) for alpha in R.ALPHAS}
    assert set(actual) == expected and set(actual.values()) == {1}
    assert sum(actual.values()) == 17052
    assert {len(indices) for _, _, _, indices in plan} == {4, 16}
    assert "content" not in R.arms(R.CONTENT)


def test_control_vectors_preserve_row_sigma_and_unit_norm():
    _, directions = data_and_directions()
    for row in R.ROWS:
        for arm in R.arms(row):
            vector = R.vector(row, arm, directions)
            assert np.linalg.norm(vector) == pytest.approx(1.0, abs=1e-6)
            assert np.linalg.norm(4*directions[row]["sigma"]*vector) == pytest.approx(4*directions[row]["sigma"], rel=1e-6)
            np.testing.assert_array_equal(vector, R.vector(row, arm, directions))
        if row != R.CONTENT:
            np.testing.assert_array_equal(R.vector(row, "content", directions), directions[R.CONTENT]["u"])
        randoms = [R.vector(row, "random_"+str(seed), directions) for seed in R.RANDOM_DIRECTION_SEEDS]
        assert all(not np.array_equal(randoms[i], randoms[j]) for i in range(3) for j in range(i))


class ScoreMock:
    def __init__(self):
        self.calls = []
    def score(self, activations, pairs, **kwargs):
        self.calls.append((activations.copy(), pairs, kwargs))
        base = torch.tensor(activations[:, 0])[:, None]
        per = base + 10*torch.arange(len(pairs))[None, :] + (100 if kwargs.get("prefix") else 0)
        projection = per[:, :, None].expand(-1, -1, 2)
        details = [{"item_index": i, "values": [float(i)]} for i in range(len(activations))]
        return {"scores": per.mean(1), "per_pair_scores": per,
                "projection_preanswer": projection, "projection_answer_mean": projection+1,
                "projections": details}


def test_unit_keeps_donor_alignment_prefix_and_dev_valid_pair_aggregation():
    data, directions = data_and_directions()
    runtime = ScoreMock()
    records = R.unit(runtime, data, directions, (R.ROWS[0], "donor", -2, [0, 1]))
    assert len(runtime.calls) == 2
    np.testing.assert_array_equal(runtime.calls[0][0], data["activations"][[1, 2]])
    assert runtime.calls[0][2].get("prefix", "") == ""
    assert runtime.calls[1][2]["prefix"] == "- "
    np.testing.assert_array_equal(runtime.calls[0][2]["projection_direction"], directions[R.ROWS[0]]["u"])
    assert runtime.calls[0][2]["sigma"] == directions[R.ROWS[0]]["sigma"]
    assert [record["injected_item_id"] for record in records] == [data["items"][i]["id"] for i in [1, 2]]
    assert [record["item_id"] for record in records] == [data["items"][i]["id"] for i in [0, 1]]
    assert records[0]["continuation_score"] == 115.0
    assert records[0]["continuation_all_pairs_score"] == 110.0
    assert records[0]["asked_projection_details"] == [{"item_index": 0, "values": [0.0]}]
    runtime = ScoreMock()
    content_index = next(i for i, item in enumerate(data["items"]) if item["feature"] == R.CONTENT)
    record = R.unit(runtime, data, directions, (R.CONTENT, "own", 0, [content_index]))[0]
    assert len(runtime.calls) == 1 and record["continuation_score"] is None
    assert record["continuation_status"] == "NOT_EVALUABLE"


@pytest.fixture
def clock_factory(tmp_path, monkeypatch):
    now = {"monotonic": 1000.0, "wall": 1900000000.0}
    alarms = []
    monkeypatch.setattr(R.time, "monotonic", lambda: now["monotonic"])
    monkeypatch.setattr(R.time, "time", lambda: now["wall"])
    monkeypatch.setattr(R.signal, "getsignal", lambda *_: None)
    monkeypatch.setattr(R.signal, "signal", lambda *_: None)
    monkeypatch.setattr(R.signal, "setitimer", lambda timer, seconds: alarms.append(seconds))
    monkeypatch.setattr(R, "source_hashes", lambda: {"runtime.py": "a"*64})
    monkeypatch.setenv("RUNPOD_POD_ID", "expected-pod")
    made = []
    def create(**overrides):
        directory = tmp_path / f"clock-{len(made)}"
        directory.mkdir()
        assignment = directory / "assignment.json"
        bindings = {"input_seal_sha256": "input", "freeze_seal_sha256": "freeze", "freeze_commit": "b"*40}
        value = {"experiment": "E19", "gpu_count": 1, "max_science_seconds": R.CAP,
                 "setup_allowance_seconds": R.SETUP, "source_files": R.source_hashes(), **bindings,
                 "pod_id": "expected-pod", "external_hard_stop_verified": True,
                 "hard_deadline_utc": datetime.fromtimestamp(now["wall"]+10000, timezone.utc).isoformat()}
        value.update(overrides)
        assignment.write_text(json.dumps(value))
        clock = R.Clock(assignment, directory, bindings)
        made.append(clock)
        return clock
    yield create, now, alarms
    for clock in made:
        if not clock.lock.closed:
            clock.close("TEST_FINISHED")


def test_clock_charges_warmups_and_gate_never_resets_science_start(clock_factory):
    create, now, alarms = clock_factory
    clock = create()
    with clock.setup():
        now["monotonic"] += 1499
    clock.start()
    first = clock.first
    now["monotonic"] += 100  # Includes all warm-up and timed calibration work.
    gate = clock.gate([100.0]*5)
    assert gate["admitted"] and gate["science_consumed_seconds"] == 100
    assert gate["science_cap_seconds"] == 1110
    assert clock.first == first and alarms[-1] == 1010
    with pytest.raises(ValueError, match="restart"):
        clock.start()
    now["monotonic"] = first+1110
    with pytest.raises(TimeoutError):
        clock.check()


def test_clock_forecast_no_go_and_setup_overrun(clock_factory):
    create, now, _ = clock_factory
    clock = create()
    clock.start()
    now["monotonic"] += 100
    with pytest.raises(RuntimeError, match="NO_GO"):
        clock.gate([1800.0]*5)
    assert clock.state["gate"]["admitted"] is False
    assert clock.state["gate"]["science_cap_seconds"] == 9000
    other = create()
    other.state["setup_seconds"] = R.SETUP+0.1
    with pytest.raises(ValueError, match="setup"):
        other.start()


def test_relaunch_gate_uses_new_ceiling_without_resetting_elapsed_time(clock_factory):
    create, now, alarms = clock_factory
    assert R.CAP == 9000 and R.SETUP == 1500
    clock = create()
    clock.start()
    assert alarms[-1] == 9000
    now["monotonic"] += 100
    gate = clock.gate([4885.8/5]*5)
    assert gate["admitted"]
    assert gate["science_cap_seconds"] == pytest.approx(1.5*4885.8+360)
    assert alarms[-1] == pytest.approx(gate["science_cap_seconds"]-100)


@pytest.mark.parametrize("forecasts", [[1.0]*4, [-1.0]*5, [0.0]*5, [float("inf")]*5, [float("nan")]*5])
def test_clock_rejects_invalid_forecasts_without_changing_cap(clock_factory, forecasts):
    create, _, _ = clock_factory
    clock = create()
    clock.start()
    with pytest.raises(ValueError, match="five positive finite"):
        clock.gate(forecasts)
    assert "gate" not in clock.state and clock.state["science_cap_seconds"] == R.CAP


def test_clock_cannot_reopen_or_widen_gate(clock_factory):
    create, _, _ = clock_factory
    clock = create()
    clock.start()
    clock.gate([100.0]*5)
    cap = clock.state["science_cap_seconds"]
    with pytest.raises(ValueError, match="already evaluated"):
        clock.gate([300.0]*5)
    assert clock.state["science_cap_seconds"] == cap


def test_clock_requires_current_pod_identity(clock_factory):
    create, _, _ = clock_factory
    with pytest.raises(ValueError, match="RUNPOD_POD_ID"):
        create(pod_id="different-pod")


def test_freeze_commit_bytes_verified_before_scoring(tmp_path, monkeypatch):
    files = {name: (name+" frozen").encode() for name in ("FREEZE.json", "directions.npz", "FREEZE_SEAL.json")}
    for name, content in files.items():
        (tmp_path/name).write_bytes(content)
    directions = {"sentinel": "dev-only"}
    monkeypatch.setattr(R, "load_freeze", lambda _: ({}, directions))
    calls = []
    def git(args, **kwargs):
        calls.append(args)
        assert args[:2] == ["git", "show"]
        return files[args[2].split(":", 1)[1].split("/")[-1]]
    monkeypatch.setattr(R.subprocess, "check_output", git)
    assert R.verify_committed_freeze(tmp_path, "c"*40) is directions
    assert len(calls) == 3
    (tmp_path/"directions.npz").write_bytes(b"mutated after commit")
    with pytest.raises(ValueError, match="committed bytes"):
        R.verify_committed_freeze(tmp_path, "c"*40)


def test_request_rejects_uncommitted_source_before_freeze_or_model_access(tmp_path, monkeypatch):
    monkeypatch.setattr(Q, "source_hashes", lambda: {"runtime.py": hashlib.sha256(b"local modified source").hexdigest()})
    monkeypatch.setattr(Q.subprocess, "check_output", lambda args, **kwargs: "c"*40 if args[1] == "rev-parse" else b"committed source")
    monkeypatch.setattr(Q, "verify_committed_freeze", lambda *_: pytest.fail("uncommitted source must fail first"))
    with pytest.raises(ValueError, match="uncommitted runtime source"):
        Q.create(tmp_path/"inputs", tmp_path/"freeze", tmp_path/"tests", tmp_path/"request.json", "c"*40)
    assert not (tmp_path/"request.json").exists()


def test_request_rejects_unrelated_valid_freeze_before_receipt(tmp_path, monkeypatch):
    data, directions = data_and_directions()
    monkeypatch.setattr(Q, "source_hashes", lambda: {})
    monkeypatch.setattr(Q.subprocess, "check_output", lambda *_args, **_kwargs: "c"*40)
    monkeypatch.setattr(Q, "verify_committed_freeze", lambda *_: directions)
    monkeypatch.setattr(Q, "load", lambda _: data)
    monkeypatch.setattr(Q, "load_freeze", lambda _: ({"source": {"e3_input_seal_sha256": "different-e3-input"}}, directions))
    with pytest.raises(ValueError, match="lineage mismatch"):
        Q.create(tmp_path/"inputs", tmp_path/"freeze", tmp_path/"tests", tmp_path/"request.json", "c"*40)
    assert not (tmp_path/"request.json").exists()


def test_relaunch_request_uses_venv_kernels_and_registered_cap(tmp_path, monkeypatch):
    data, directions = data_and_directions()
    for directory, name in (("inputs", "INPUT_SEAL.json"), ("freeze", "FREEZE_SEAL.json")):
        (tmp_path/directory).mkdir()
        (tmp_path/directory/name).write_text("{}")
    tests = tmp_path/"tests.json"
    tests.write_text(json.dumps({"status": "PASS", "gpu_hours": 0}))
    monkeypatch.setattr(Q, "source_hashes", lambda: {})
    monkeypatch.setattr(Q.subprocess, "check_output", lambda *_args, **_kwargs: "c"*40)
    monkeypatch.setattr(Q, "verify_committed_freeze", lambda *_: directions)
    monkeypatch.setattr(Q, "load", lambda _: data)
    monkeypatch.setattr(Q, "load_freeze", lambda _: ({"source": {"e3_input_seal_sha256": "same-e3-input"}}, directions))
    freeze_commit = "36bd59a958fcce7f0f5da7fb65e1c31038b9c238"
    out = tmp_path/"request.json"
    Q.create(tmp_path/"inputs", tmp_path/"freeze", tests, out, freeze_commit)
    receipt = json.loads(out.read_text())
    assert receipt["model_environment"] == "/weights/venv-kernels"
    assert receipt["launch_argv"][0] == "/weights/venv-kernels/bin/python"
    assert receipt["assignment_required"]["max_science_seconds"] == 9000
    assert receipt["assignment_required"]["setup_allowance_seconds"] == 1500
    assert receipt["cap_rule"] == "min(1.5F+360,9000) seconds continuously from first warm-up; setup1500 seconds"
    assert receipt["operational_ruling_commit"] == "17942898"
    assert receipt["freeze_commit"] == freeze_commit
    assert receipt["scope"]["items"] == 420 and receipt["scope"]["production_units"] == 1218


def test_no_go_seals_empty_production_and_preserves_incomplete_status(tmp_path, monkeypatch):
    from projects.g_agreement.understand import reader_runtime
    from projects.g_agreement.understand.e19 import runtime as runtime_module
    data, directions = data_and_directions()
    for directory, name in (("inputs", "INPUT_SEAL.json"), ("freeze", "FREEZE_SEAL.json")):
        (tmp_path/directory).mkdir()
        (tmp_path/directory/name).write_text("{}")
    class ClockMock:
        def __init__(self, *_):
            self.first = None
            self.state = {"cap_overrun_seconds": 0, "science_cap_seconds": R.CAP}
        def setup(self): return nullcontext()
        def start(self): self.first = R.time.monotonic()
        def check(self): pass
        def gate(self, forecasts): raise RuntimeError("NO_GO_WARMED_FORECAST")
        def disarm(self): pass
        def close(self, status): self.state["status"] = status
    monkeypatch.setattr(R, "Clock", ClockMock)
    monkeypatch.setattr(R, "load", lambda _: data)
    monkeypatch.setattr(R, "verify_committed_freeze", lambda *_: directions)
    monkeypatch.setattr(R, "load_freeze", lambda _: ({"source": {"e3_input_seal_sha256": "same-e3-input"}}, directions))
    monkeypatch.setattr(R, "source_hashes", lambda: {})
    monkeypatch.setattr(reader_runtime, "load_runtime", lambda *_args, **_kwargs: None)
    mock_runtime = SimpleNamespace(oracle=SimpleNamespace(reader=SimpleNamespace(tok=SimpleNamespace(encode=lambda *_a, **_k: [1]))))
    monkeypatch.setattr(runtime_module, "E19Runtime", lambda _: mock_runtime)
    calls = []
    def unit(*args):
        calls.append(args[-1])
        return []
    monkeypatch.setattr(R, "unit", unit)
    out = tmp_path/"output"
    result = R.run(tmp_path/"inputs", tmp_path/"freeze", "c"*40, tmp_path/"assets", tmp_path/"assignment", out)
    assert result["status"] == "INCOMPLETE" and "NO_GO" in result["error"]
    assert len(calls) == len(R.ROWS)*4
    assert all(arm == "own" and alpha == 4 for _, arm, alpha, _ in calls)
    assert not list((out/"units").glob("*.json"))
    assert (out/"scores.jsonl").read_text() == ""
    seal = P.verify(out, "SCORE_SEAL.json")
    assert "RUN_STATUS.json" in seal["files"]
    assert json.loads((out/"RUN_STATUS.json").read_text())["status"] == "INCOMPLETE"
