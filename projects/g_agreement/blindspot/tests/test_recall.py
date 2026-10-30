"""Blinding, seals, missingness and BOTH semantics for human recall judgments."""
import json
from pathlib import Path

import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot import recall as R


def fixture(tmp_path):
    bank, target, nla = [tmp_path / name for name in ("bank", "target", "nla")]
    for path in (bank, target, nla):
        path.mkdir()
    items = [{"id": "item-" + str(i), "feature": "structure", "ids": [1], "donor_id": None} for i in range(4)]
    labels = [{"id": r["id"], "feature": "structure", "value": "inside" if i % 2 == 0 else "outside",
               "split": "test" if i < 2 else "dev", "class": "state-like", "cluster": "family-" + str(i // 2)}
              for i, r in enumerate(items)]
    P.jsonl(bank / "items.input.jsonl", items)
    P.jsonl(bank / "labels.DO_NOT_STAGE.jsonl", labels)
    P.dump(bank / "templates.json", {"structure": {"kind": "binary", "values": ["inside", "outside"],
            "olens": [["- an open parenthesis", "- a closed parenthesis"]]}})
    P.dump(bank / "provenance.json", {"labels_sha256": P.sha(bank / "labels.DO_NOT_STAGE.jsonl")})
    P.dump(bank / "decoding.json", P.DECODING)
    P.seal(bank, ["items.input.jsonl", "templates.json", "provenance.json", "decoding.json"], "INPUTS_FROZEN")
    for phase, root in (("target", target), ("nla", nla)):
        P.jsonl(root / f"scores.{phase}.jsonl", [])
        provenance = {"input_seal_sha256": P.sha(bank / "INPUT_SEAL.json")}
        if phase == "nla":
            provenance["target_score_seal_sha256"] = P.sha(target / "SCORE_SEAL.json")
        P.dump(root / f"provenance.{phase}.json", provenance)
        P.seal(root, [f"scores.{phase}.jsonl", f"provenance.{phase}.json"], "SCORES_SEALED")
        free = [{"id": r["id"], "reader": reader, "layer": layer, "sample": sample,
                 "text": "An open parenthesis.", "raw": "An open parenthesis.", "status": "COMPLETE"}
                for r in items for reader, layer in R.READERS[phase].items() for sample in (0, 1)]
        P.jsonl(root / f"unasked.{phase}.jsonl", free)
        P.dump(root / f"provenance.unasked.{phase}.json", {
            "input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"),
            "asked_score_seal_sha256": P.sha(root / "SCORE_SEAL.json"),
            "expected_per_item_per_reader": 2, "decoding": P.DECODING})
        names = (f"unasked.{phase}.jsonl", f"provenance.unasked.{phase}.json")
        P.dump(root / "FREE_SEAL.json", {"status": "UNASKED_COMPLETE_BEFORE_LABEL_JOIN", "files": {n: P.sha(root / n) for n in names}})
    return bank, target, nla


def test_packet_never_reads_labels_and_hides_identifiers(tmp_path, monkeypatch):
    bank, target, nla = fixture(tmp_path)
    original = Path.read_text
    def guarded(path, *args, **kwargs):
        assert path.name != "labels.DO_NOT_STAGE.jsonl"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", guarded)
    packet = tmp_path / "packet"
    assert R.build_packet(bank, target, nla, packet) == {"expected": 32, "available": 32, "missing": 0}
    public = P.rows(packet / "packet.jsonl")
    assert len({r["judgment_id"] for r in public}) == 32
    assert all(set(r) == {"judgment_id", "readout", "A", "B"} for r in public)
    assert all(len(r["judgment_id"]) == 64 and "item-" not in r["judgment_id"] for r in public)
    assert len({r["A"] for r in public}) == 2
    assert json.loads((packet / "provenance.json").read_text())["ground_truth_opened"] is False


def test_incomplete_free_grid_refuses_packet_even_with_valid_file_hash(tmp_path):
    bank, target, nla = fixture(tmp_path)
    path = nla / "unasked.nla.jsonl"
    path.write_text(path.read_text().splitlines()[0] + "\n")
    seal = json.loads((nla / "FREE_SEAL.json").read_text())
    seal["files"][path.name] = P.sha(path)
    P.dump(nla / "FREE_SEAL.json", seal)
    with pytest.raises(ValueError, match="unasked grid"):
        R.build_packet(bank, target, nla, tmp_path / "packet")


def test_free_lineage_mismatch_refuses_packet(tmp_path):
    bank, target, nla = fixture(tmp_path)
    path = nla / "provenance.unasked.nla.json"
    provenance = json.loads(path.read_text())
    provenance["asked_score_seal_sha256"] = "0" * 64
    P.dump(path, provenance)
    seal = json.loads((nla / "FREE_SEAL.json").read_text())
    seal["files"][path.name] = P.sha(path)
    P.dump(nla / "FREE_SEAL.json", seal)
    with pytest.raises(ValueError, match="provenance"):
        R.build_packet(bank, target, nla, tmp_path / "packet")


def test_partial_judgments_keep_denominators_and_both_semantics(tmp_path):
    bank, target, nla = fixture(tmp_path)
    packet = tmp_path / "packet"
    R.build_packet(bank, target, nla, packet)
    mapping = P.rows(packet / "mapping.DO_NOT_STAGE.jsonl")
    # All test samples of item0 are BOTH; all dev samples would be correct but are excluded.
    choices = []
    for row in mapping:
        if row["item_id"] == "item-0":
            choices.append({"judgment_id": row["judgment_id"], "judgment": "BOTH"})
        elif row["item_id"] in {"item-2", "item-3"}:
            choices.append({"judgment_id": row["judgment_id"], "judgment": "BOTH"})
    P.jsonl(tmp_path / "submitted.jsonl", choices)
    annotation = tmp_path / "annotation"
    R.seal_annotations(packet, tmp_path / "submitted.jsonl", annotation)
    report = R.analyse(packet, annotation, bank / "labels.DO_NOT_STAGE.jsonl", tmp_path / "report")
    assert report["status"] == "DESCRIPTIVE_INCOMPLETE"
    assert len(report["rows"]) == 4
    for row in report["rows"]:
        assert row["expected_readouts"] == 4 and row["annotated_readouts"] == 2
        assert row["missing_judgments"] == 2 and row["n_items"] == 2
        assert row["strict_correct_only"]["rate"] == 0
        assert row["inclusive_contains_true"]["rate"] == 1
        assert row["both_rate"]["rate"] == 1
        assert row["inclusive_missing_as_failure"]["rate"] == .5
        assert row["strict_rate"] is None and row["inclusive_rate"] is None


def test_zero_annotations_do_not_invent_observed_rate(tmp_path):
    bank, target, nla = fixture(tmp_path)
    packet = tmp_path / "packet"
    R.build_packet(bank, target, nla, packet)
    P.jsonl(tmp_path / "submitted.jsonl", [])
    R.seal_annotations(packet, tmp_path / "submitted.jsonl", tmp_path / "annotation")
    report = R.analyse(packet, tmp_path / "annotation", bank / "labels.DO_NOT_STAGE.jsonl", tmp_path / "report")
    assert all(row["strict_correct_only"]["rate"] is None for row in report["rows"])
    assert all(row["missing_judgments"] == row["expected_readouts"] for row in report["rows"])


def test_complete_annotations_use_private_display_mapping(tmp_path):
    bank, target, nla = fixture(tmp_path)
    packet = tmp_path / "packet"
    R.build_packet(bank, target, nla, packet)
    truth = {row["id"]: row["value"] for row in P.rows(bank / "labels.DO_NOT_STAGE.jsonl")}
    choices = [{"judgment_id": row["judgment_id"],
                "judgment": next(key for key, value in row["display_values"].items() if value == truth[row["item_id"]])}
               for row in P.rows(packet / "mapping.DO_NOT_STAGE.jsonl")]
    P.jsonl(tmp_path / "submitted.jsonl", choices)
    R.seal_annotations(packet, tmp_path / "submitted.jsonl", tmp_path / "annotation")
    report = R.analyse(packet, tmp_path / "annotation", bank / "labels.DO_NOT_STAGE.jsonl", tmp_path / "report")
    assert report["status"] == "DESCRIPTIVE_COMPLETE"
    assert all(row["strict_rate"] == row["inclusive_rate"] == 1 for row in report["rows"])
    assert all(row["both_rate"]["rate"] == 0 for row in report["rows"])


def test_annotation_tampering_rejected_before_ground_truth_is_opened(tmp_path, monkeypatch):
    bank, target, nla = fixture(tmp_path)
    packet = tmp_path / "packet"
    R.build_packet(bank, target, nla, packet)
    P.jsonl(tmp_path / "submitted.jsonl", [])
    R.seal_annotations(packet, tmp_path / "submitted.jsonl", tmp_path / "annotation")
    with (tmp_path / "annotation" / "annotations.jsonl").open("a") as f:
        f.write("{}\n")
    original = Path.read_text
    def guarded(path, *args, **kwargs):
        assert path.name != "labels.DO_NOT_STAGE.jsonl"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", guarded)
    with pytest.raises(ValueError, match="seal mismatch"):
        R.analyse(packet, tmp_path / "annotation", bank / "labels.DO_NOT_STAGE.jsonl", tmp_path / "report")


@pytest.mark.parametrize("rows", [[{"judgment_id": "unknown", "judgment": "A"}],
                                 [{"judgment_id": "use-valid-id", "judgment": "correct"}]])
def test_annotations_reject_unknown_ids_or_non_blinded_ratings(tmp_path, rows):
    bank, target, nla = fixture(tmp_path)
    packet = tmp_path / "packet"
    R.build_packet(bank, target, nla, packet)
    if rows[0]["judgment_id"] == "use-valid-id":
        rows[0]["judgment_id"] = P.rows(packet / "packet.jsonl")[0]["judgment_id"]
    P.jsonl(tmp_path / "submitted.jsonl", rows)
    with pytest.raises(ValueError):
        R.seal_annotations(packet, tmp_path / "submitted.jsonl", tmp_path / "annotation")
