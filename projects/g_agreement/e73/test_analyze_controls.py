"""Amended R-W1 behavior on synthetic full-sized grids only."""
import copy
import json
from pathlib import Path

import pytest

from . import analyze as A, analyze_controls as C
from .test_analyze import code, pure_grid, synthetic_pipeline


def grids():
    structural = pure_grid()
    for p in structural[2]:
        if p["state"] in ("W2", "W3"):
            p.update(test_auroc=.85, probe_pass=False)
    key, codes = [], []
    for reader in A.READERS:
        for state in C.CONTROLS:
            for n in range(200):
                uid = reader + state + str(n)
                key.append(dict(opaque_id=uid, source_id=state + str(n), reader=reader, state=state,
                                label=n % 2, judge_attempts=0, truncated=False if reader == "nla" else None))
                codes.append(code(uid, "states_value", ["AB"[n % 2]], "A") if state == "W7" and n < 60
                             else code(uid, "silent", [], ""))
    return structural, (key, codes, [dict(state=s, test_auroc=.8, probe_pass=False) for s in C.CONTROLS])


def test_full_condition_exact_control_boundary_and_no_control_probe_gate():
    original, controls = grids()
    before = copy.deepcopy((original, controls))
    result = C.compute(original, controls)
    assert result["R_W1"]["status"] == "MET" and result["R_W1"]["scope"] == "FULL"
    assert result["confirmatory_eligible_states"] == ["W1", "W4", "W5"]
    assert result["descriptive_states"] == ["W2", "W3"]
    for reader in result["readers"].values():
        assert reader["pooled_eligible_structural"]["n_readouts"] == 600
        assert reader["judgment_missingness"]["total"] == 1400
        assert reader["states"]["W7"]["S"] == .30
        assert reader["states"]["W7"]["bow_auroc"] == 1.
        assert reader["states"]["W8"]["bow_auroc"] == C.BOW["W8"]
        assert not reader["states"]["W7"]["probe_pass"]
    assert before == (original, controls)
    controls[1][0].update(category="silent", values=[], evidence="")
    result = C.compute(original, controls)
    assert result["R_W1"]["status"] == "NOT_MET"
    assert result["readers"]["oracle"]["R_W1"]["content_condition_met"] is False
    assert result["readers"]["nla"]["R_W1"]["content_condition_met"] is True


def test_descriptives_cannot_enter_structural_pool_and_missing_controls_not_silence():
    original, controls = grids()
    for k, j in zip(original[0], original[1]):
        if k["state"] in ("W2", "W3"):
            j.update(category="states_value", values=["AB"[k["label"]]], evidence="A")
    assert C.compute(original, controls)["R_W1"]["status"] == "MET"
    for j in controls[1]:
        j.update(category="UNPARSEABLE", values=[], evidence="")
    result = C.compute(original, controls)
    assert result["R_W1"]["status"] == "NOT_EVALUABLE"
    fallback = C.compute(original)
    assert fallback["R_W1"]["status"] == "MET"
    assert fallback["R_W1"]["scope"] == "WITHOUT_CONTENT_CONDITION"
    assert fallback["readers"]["oracle"]["R_W1"]["content_condition_met"] is None


def test_structural_failure_cannot_be_rescued_by_positive_controls():
    original, controls = grids()
    for k, j in zip(original[0], original[1]):
        if k["state"] in C.STRUCTURAL:
            j.update(category="states_value", values=["AB"[k["label"]]], evidence="A")
    result = C.compute(original, controls)
    assert result["R_W1"]["status"] == "NOT_MET"
    assert all(r["falsifier_pooled_S_ge_0_20"] for r in result["readers"].values())


def test_supplement_custody_loader_full_grid_and_wrong_bank_rejected(tmp_path, monkeypatch):
    plan = synthetic_pipeline(tmp_path, monkeypatch, controls=True)
    key, codes, probes = A.load_inputs(plan, controls=True)
    assert len(key) == len(codes) == 800 and {p["state"] for p in probes} == {"W7", "W8"}
    assert {k["state"] for k in key} == {"W7", "W8"}
    with pytest.raises(ValueError, match="frozen bank"):
        A.load_inputs(plan)
    monkeypatch.setattr(A, "CONTROL_MANIFEST", "0" * 64)
    with pytest.raises(ValueError, match="control manifest"):
        A.load_inputs(plan, controls=True)


def test_once_guard_precedes_both_outcome_loads(tmp_path, monkeypatch):
    original, controls = grids()
    plan = {"banks": {"structural": {}, "controls": {}}, "output": str(tmp_path / "out"), "source_files": {}}
    monkeypatch.setattr(C, "verify_plan", lambda *args: plan)
    monkeypatch.setattr(A, "load_inputs", lambda plan, controls=False: grids()[1 if controls else 0])
    assert C.run("unused", "a" * 40, "b" * 64)["R_W1"]["status"] == "MET"
    monkeypatch.setattr(A, "load_inputs", lambda *args, **kwargs: pytest.fail("repeat opened outcomes"))
    with pytest.raises(FileExistsError):
        C.run("unused", "a" * 40, "b" * 64)


def test_no_control_analysis_before_direct_user_deadline(tmp_path, monkeypatch):
    plan = {"schema": "e73-amended-analysis-plan-v1", "rules": C.RULES, "source_files": {},
            "output": str(tmp_path / "out"), "mode": "without_content_condition_at_deadline", "banks": {"structural": {}},
            "controls_not_judged_by_deadline_attested_by": "I-2"}
    path = tmp_path / "PLAN.json"
    path.write_text(json.dumps(plan))
    monkeypatch.setattr(A, "REPO", tmp_path)
    monkeypatch.setattr(A, "git_file", lambda *args: path.read_bytes())
    monkeypatch.setattr(C, "SOURCE_FILES", set())
    from datetime import datetime
    class Before(datetime):
        @classmethod
        def now(cls, tz):
            return datetime.fromisoformat("2026-10-28T14:59:59+00:00")
    monkeypatch.setattr(C, "datetime", Before)
    with pytest.raises(ValueError, match="deadline has not arrived"):
        C.verify_plan("PLAN.json", "a" * 40, A.sha256(path))
    class AtDeadline(datetime):
        @classmethod
        def now(cls, tz):
            return datetime.fromisoformat(C.DEADLINE)
    monkeypatch.setattr(C, "datetime", AtDeadline)
    assert C.verify_plan("PLAN.json", "a" * 40, A.sha256(path))["mode"] == plan["mode"]
