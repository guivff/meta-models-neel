import copy
import json

import pytest

from projects.g_agreement.understand import e23_sources as E


def bank():
    return {"items": [{"id": f"i{i}", "cluster": f"c{i}", "feature": "row",
                       "value": "A" if i % 2 == 0 else "B",
                       "split": "mine" if i < 40 else "select", "ids": [1, 2, i]}
                      for i in range(200)], "ol_gens": "must not be used"}


def test_both_ends_of_registered_hash_are_required():
    actual = "09156722b059edb99d01e919c29b2ff660e37cba3152f2d3ce67f3272d3e923b"
    assert not E.matches_pin(actual, "09156722…d923b")
    assert E.matches_pin(actual, "09156722…e923b")
    assert E.matches_pin(actual, actual)
    assert not E.matches_pin(actual, actual[:-1] + "a")


def test_dated_correction_pins_full_sha256():
    pin=next(r[1] for r in E.FILES if r[0]=='experiments/07_template_mining/templates_frozen.json')
    assert pin=='09156722b059edb99d01e919c29b2ff660e37cba3152f2d3ce67f3272d3e923b'
    assert E.AUTHORITY=='e347b86a'


def test_metadata_preserves_registered_split_and_cluster():
    got = E.item_metadata(bank(), "row")
    assert got["split_counts"] == {"mine": 40, "select": 160}
    assert got["unique_clusters"] == 200
    assert got["value_counts"] == {"mine": {"A": 20, "B": 20}, "select": {"A": 80, "B": 80}}


@pytest.mark.parametrize("field,value,message", [
    ("id", "i0", "unique id"), ("cluster", "c0", "unique cluster"),
    ("split", "mine", "split"), ("feature", "other", "feature"),
    ("ids", [], "token prefix"),
])
def test_metadata_rejects_changed_bank(field, value, message):
    data = bank()
    data["items"][-1][field] = value
    with pytest.raises(ValueError, match=message):
        E.item_metadata(data, "row")


def test_old_readouts_do_not_affect_metadata():
    data = bank()
    other = copy.deepcopy(data)
    other["ol_gens"] = {"irrelevant": [0, 1, 2]}
    assert E.item_metadata(data, "row") == E.item_metadata(other, "row")


def test_git_match_cannot_override_registered_hash_mismatch(tmp_path, monkeypatch):
    data = json.dumps(bank()).encode()
    hashes = E.digests(data)
    (tmp_path / "bank.json").write_bytes(data)
    bad_suffix = "0" if hashes["sha256"][-1] != "0" else "1"
    monkeypatch.setattr(E, "FILES", (("bank.json", hashes["sha256"][:8] + "…" + bad_suffix,
                                      hashes["git_blob"], "row"),))
    monkeypatch.setattr(E, "PARITY_FILES", ())
    receipt = E.audit(tmp_path)
    assert receipt["files"][0]["pinned_git_blob_matches"]
    assert not receipt["launch_allowed"]
    assert receipt["status"] == "BLOCKED_SOURCE_GATE"
    assert len(receipt["errors"]) == 1


def test_missing_sources_cannot_pass(tmp_path):
    receipt = E.audit(tmp_path)
    assert not receipt["launch_allowed"]
    assert len(receipt["errors"]) == 9
