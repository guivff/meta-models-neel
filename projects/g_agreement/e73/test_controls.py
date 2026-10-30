"""Synthetic amendment validation; no refits, captures or reader outputs."""
import copy
import json

import pytest

from .controls import AUTHORITY, subset_bytes
from .delivery import validate_gate


def control_gate():
    return {"threshold": .65, "included_states": ["W7", "W8"], "bow_exempt_states": ["W7", "W8"],
            "authority_commit": AUTHORITY, "all_states_gated_including_controls": False,
            "no_resampling_or_refitting": True,
            "original_gate_report_sha256": "70e1265b6f47caf2bc33c1ed2fba6241bc9116a63ace2faa9ddfa28e6683eadf",
            "original_bank_manifest_sha256": "cc7d852ef84b2763c3d02141cdf9e1c516b28525a47362496c1b59c9aeb68669",
            "metrics": {"W7": {"dev_items": 400, "test_items": 400, "test_auroc": 1., "gate_pass": False},
                        "W8": {"dev_items": 316, "test_items": 316, "test_auroc": .9641483736580676, "gate_pass": False}}}


def test_original_gate_and_amendment_remain_distinct():
    gate = control_gate()
    before = copy.deepcopy(gate)
    validate_gate(gate)
    assert gate == before and all(not v["gate_pass"] for v in gate["metrics"].values())
    validate_gate({"threshold": .65, "all_states_gated_including_controls": True, "included_states": ["W1"],
                   "metrics": {"W1": {"test_auroc": .55, "gate_pass": True}, "W7": {"test_auroc": 1., "gate_pass": False}}})


@pytest.mark.parametrize("mutation", [
    lambda g: g.update(authority_commit="a" * 40),
    lambda g: g.update(bow_exempt_states=["W1", "W7", "W8"]),
    lambda g: g.update(included_states=["W1", "W7", "W8"]),
    lambda g: g.update(original_gate_report_sha256="b" * 64),
    lambda g: g.update(no_resampling_or_refitting=False),
    lambda g: g["metrics"]["W8"].update(test_items=400),
    lambda g: g["metrics"]["W7"].update(gate_pass=True),
    lambda g: g["metrics"]["W8"].update(test_auroc=.64),
])
def test_amendment_cannot_change_authority_scope_or_measurements(mutation):
    gate = control_gate()
    mutation(gate)
    with pytest.raises(ValueError):
        validate_gate(gate)


def test_subset_preserves_record_bytes_order_and_flags(tmp_path):
    lines = [b'{ "id": "c", "reader_selected": false }\r\n',
             b'{"id":"b","reader_selected":true}\n', b'{"id":"a", "reader_selected":false}\n']
    source = tmp_path / "rows.jsonl"
    source.write_bytes(b"".join(lines))
    result = subset_bytes(source, {"a", "c"})
    assert result == lines[0] + lines[2]
    assert [json.loads(x)["id"] for x in result.splitlines()] == ["c", "a"]
