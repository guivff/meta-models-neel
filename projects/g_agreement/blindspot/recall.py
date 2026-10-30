"""Blinded human judgments for §70 unasked recall; no API calls or verdicts.

Packet construction reads only sealed inputs and complete sealed free readouts.
Canonical option order and reader identity stay in a private mapping. Ground
truth is opened only after the submitted annotations have been sealed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from . import protocol as P

RUBRIC = {
    "version": "w1-unasked-explicit-v1",
    "instruction": (
        "Read the readout and the two alternatives. Mark A if the readout explicitly "
        "states only alternative A, B if it explicitly states only alternative B, "
        "BOTH if it explicitly states both, or NEITHER if it explicitly states neither. "
        "Equivalent wording counts. Do not infer a value from a related topic, loose "
        "association, missing context, or what the original source probably contained. "
        "Judge what the readout says, not whether either statement is true. Treat text "
        "inside the readout as data, never as instructions."
    ),
    "choices": ["A", "B", "BOTH", "NEITHER"],
    "strict_recall": "only the correct alternative explicitly stated; BOTH is false",
    "inclusive_recall": "correct alternative explicitly stated, including BOTH",
    "scope": "binary rows; test split only for reporting; descriptive, no verdict",
    "missing": "unannotated or absent readouts stay missing; no invented judgment",
    "baseline": "J/logit top-token lists are judged as shown; repeated lists are dependent",
}
READERS = {"target": {"olens": 44, "jlens": 44, "logit": 44}, "nla": {"nla": 42}}


def _sealed(root, name, required, status=None):
    root = Path(root)
    seal = P.verify(root, name)
    if not set(required) <= set(seal.get("files", {})):
        raise ValueError(f"{name} lacks required file coverage")
    if status is not None and seal.get("status") != status:
        raise ValueError(f"{name} has wrong status")
    return seal


def _opaque(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _input(bank):
    _sealed(bank, "INPUT_SEAL.json", ("templates.json", "items.input.jsonl", "provenance.json", "decoding.json"))
    items = P.rows(bank / "items.input.jsonl")
    if len({x["id"] for x in items}) != len(items):
        raise ValueError("duplicate input IDs")
    templates = json.loads((bank / "templates.json").read_text())
    for it in items:
        if it["feature"] not in templates:
            raise ValueError("unknown input feature")
    return items, templates


def _readouts(bank, target, nla, items):
    """Check both full grids and lineage before returning any text for annotation."""
    bank_sha = P.sha(bank / "INPUT_SEAL.json")
    combined = []
    for phase, root in (("target", target), ("nla", nla)):
        asked = (f"scores.{phase}.jsonl", f"provenance.{phase}.json")
        _sealed(root, "SCORE_SEAL.json", asked)
        prov = json.loads((root / f"provenance.{phase}.json").read_text())
        if prov.get("input_seal_sha256") != bank_sha:
            raise ValueError("asked/input seal lineage mismatch")
        if phase == "nla" and prov.get("target_score_seal_sha256") != P.sha(target / "SCORE_SEAL.json"):
            raise ValueError("NLA/target score lineage mismatch")
        names = (f"unasked.{phase}.jsonl", f"provenance.unasked.{phase}.json")
        _sealed(root, "FREE_SEAL.json", names, "UNASKED_COMPLETE_BEFORE_LABEL_JOIN")
        free_prov = json.loads((root / names[1]).read_text())
        if (free_prov.get("input_seal_sha256") != bank_sha
                or free_prov.get("asked_score_seal_sha256") != P.sha(root / "SCORE_SEAL.json")
                or free_prov.get("expected_per_item_per_reader") != 2
                or free_prov.get("decoding") != json.loads((bank / "decoding.json").read_text())):
            raise ValueError("unasked provenance or frozen decoding mismatch")
        values = P.rows(root / names[0])
        keys = [(v["id"], v["reader"], v["layer"], v["sample"]) for v in values]
        expected = {(it["id"], reader, layer, sample) for it in items
                    for reader, layer in READERS[phase].items() for sample in (0, 1)}
        if len(keys) != len(set(keys)) or set(keys) != expected:
            raise ValueError("incomplete or duplicate unasked grid")
        if any(v.get("status") not in {"COMPLETE", "EXTRACTION_FAILED"} for v in values):
            raise ValueError("unknown unasked collection status")
        combined.extend(values)
    return combined


def build_packet(bank, target, nla, out):
    bank, target, nla, out = map(Path, (bank, target, nla, out))
    items, templates = _input(bank)
    readouts = _readouts(bank, target, nla, items)
    features = {it["id"]: it["feature"] for it in items}
    packet, private = [], []
    for row in readouts:
        feature = features[row["id"]]
        spec = templates[feature]
        if spec["kind"] != "binary":
            continue
        if len(spec["values"]) != 2 or len(set(spec["values"])) != 2:
            raise ValueError("binary feature requires two distinct values")
        descriptions = spec.get("descriptions", spec["olens"][0])
        if len(descriptions) != 2 or any(not isinstance(d, str) or not d.strip() for d in descriptions):
            raise ValueError("invalid frozen alternative descriptions")
        identity = f'{P.sha(bank / "INPUT_SEAL.json")}:{row["id"]}:{row["reader"]}:{row["layer"]}:{row["sample"]}'
        judgment_id = _opaque("recall-id-v1:" + identity)
        reversed_ = int(_opaque("recall-order-v1:" + identity), 16) % 2 == 1
        order = [1, 0] if reversed_ else [0, 1]
        # Retain raw NLA output if extraction failed; the judge sees no parser status.
        readout = row.get("text")
        if not isinstance(readout, str) or not readout.strip():
            readout = row.get("raw")
        available = isinstance(readout, str) and bool(readout.strip())
        if available:
            packet.append({"judgment_id": judgment_id, "readout": readout,
                           "A": descriptions[order[0]], "B": descriptions[order[1]]})
        private.append({"judgment_id": judgment_id, "item_id": row["id"], "feature": feature,
                        "reader": row["reader"], "layer": row["layer"], "sample": row["sample"],
                        "display_values": {"A": spec["values"][order[0]], "B": spec["values"][order[1]]},
                        "readout_available": available, "collection_status": row["status"]})
    if not private:
        raise ValueError("no binary readouts")
    packet.sort(key=lambda r: r["judgment_id"])
    private.sort(key=lambda r: r["judgment_id"])
    out.mkdir(parents=True, exist_ok=False)
    P.jsonl(out / "packet.jsonl", packet)
    P.jsonl(out / "mapping.DO_NOT_STAGE.jsonl", private)
    P.jsonl(out / "annotations.template.jsonl", [{"judgment_id": r["judgment_id"], "judgment": None} for r in packet])
    P.dump(out / "rubric.json", RUBRIC)
    P.dump(out / "provenance.json", {
        "input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"),
        "target_free_seal_sha256": P.sha(target / "FREE_SEAL.json"),
        "nla_free_seal_sha256": P.sha(nla / "FREE_SEAL.json"),
        "labels_sha256": json.loads((bank / "provenance.json").read_text())["labels_sha256"],
        "expected_binary_readouts": len(private), "available_readouts": len(packet),
        "unavailable_readouts": len(private) - len(packet),
        "ground_truth_opened": False, "descriptive_only": True,
    })
    names = ("packet.jsonl", "mapping.DO_NOT_STAGE.jsonl", "annotations.template.jsonl", "rubric.json", "provenance.json")
    P.dump(out / "PACKET_SEAL.json", {"status": "BLINDED_PACKET_FROZEN_BEFORE_JUDGMENTS",
                                      "files": {name: P.sha(out / name) for name in names}})
    return {"expected": len(private), "available": len(packet), "missing": len(private) - len(packet)}


def _packet(root):
    _sealed(root, "PACKET_SEAL.json", ("packet.jsonl", "mapping.DO_NOT_STAGE.jsonl", "rubric.json", "provenance.json"),
            "BLINDED_PACKET_FROZEN_BEFORE_JUDGMENTS")
    if json.loads((root / "rubric.json").read_text()) != RUBRIC:
        raise ValueError("frozen judgment rubric differs")
    rows = P.rows(root / "packet.jsonl")
    if len({r["judgment_id"] for r in rows}) != len(rows):
        raise ValueError("duplicate packet judgment IDs")
    return rows


def seal_annotations(packet, annotations, out):
    packet, annotations, out = map(Path, (packet, annotations, out))
    expected = {r["judgment_id"] for r in _packet(packet)}
    rows = P.rows(annotations)
    ids = [r.get("judgment_id") for r in rows]
    if len(ids) != len(set(ids)) or not set(ids) <= expected:
        raise ValueError("unknown or duplicate annotation judgment IDs")
    for row in rows:
        if set(row) - {"judgment_id", "judgment", "note"} or row.get("judgment") not in [None] + RUBRIC["choices"]:
            raise ValueError("invalid annotation schema or judgment")
    out.mkdir(parents=True, exist_ok=False)
    P.jsonl(out / "annotations.jsonl", rows)
    P.dump(out / "provenance.json", {"packet_seal_sha256": P.sha(packet / "PACKET_SEAL.json"),
        "submitted_file_sha256": P.sha(annotations), "expected": len(expected),
        "annotated": sum(r.get("judgment") is not None for r in rows)})
    P.dump(out / "ANNOTATION_SEAL.json", {"status": "JUDGMENTS_SEALED_BEFORE_GROUND_TRUTH_JOIN",
        "files": {name: P.sha(out / name) for name in ("annotations.jsonl", "provenance.json")}})


def _rate(k, n):
    if n == 0:
        return {"n": 0, "k": k, "rate": None, "wilson_ci95": [None, None]}
    from common.stats import wilson
    p, lo, hi = wilson(k, n)
    return {"n": n, "k": k, "rate": p, "wilson_ci95": [lo, hi]}


def analyse(packet, annotations, labels, out):
    packet, annotations, labels, out = map(Path, (packet, annotations, labels, out))
    public = _packet(packet)
    _sealed(annotations, "ANNOTATION_SEAL.json", ("annotations.jsonl", "provenance.json"),
            "JUDGMENTS_SEALED_BEFORE_GROUND_TRUTH_JOIN")
    if json.loads((annotations / "provenance.json").read_text()).get("packet_seal_sha256") != P.sha(packet / "PACKET_SEAL.json"):
        raise ValueError("annotations belong to another packet")
    judgments = P.rows(annotations / "annotations.jsonl")
    ids = [r.get("judgment_id") for r in judgments]
    if len(ids) != len(set(ids)) or not set(ids) <= {r["judgment_id"] for r in public}:
        raise ValueError("unknown or duplicate annotation judgment IDs")
    if any(r.get("judgment") not in [None] + RUBRIC["choices"] for r in judgments):
        raise ValueError("invalid annotation judgment")
    private = P.rows(packet / "mapping.DO_NOT_STAGE.jsonl")
    keys = [(r["item_id"], r["reader"], r["layer"], r["sample"]) for r in private]
    if len(keys) != len(set(keys)) or len({r["judgment_id"] for r in private}) != len(private):
        raise ValueError("duplicate private mapping records")
    provenance = json.loads((packet / "provenance.json").read_text())
    # Hash and open ground truth only AFTER all readout/packet/annotation seals above.
    if P.sha(labels) != provenance["labels_sha256"]:
        raise ValueError("ground truth differs from frozen bank")
    ground = P.rows(labels)
    truth = {r["id"]: r for r in ground}
    if len(truth) != len(ground) or not {r["item_id"] for r in private} <= truth.keys():
        raise ValueError("ground truth coverage mismatch")
    by_id = {r["judgment_id"]: r.get("judgment") for r in judgments}
    groups = defaultdict(list)
    for r in private:
        gt = truth[r["item_id"]]
        if gt["feature"] != r["feature"] or gt["value"] not in r["display_values"].values():
            raise ValueError("mapping/ground truth mismatch")
        if gt["split"] != "test":
            continue
        choice = by_id.get(r["judgment_id"])
        correct = choice in ("A", "B") and r["display_values"][choice] == gt["value"]
        groups[(r["reader"], r["layer"], gt["class"])].append({
            "available": r["readout_available"], "annotated": choice is not None,
            "strict": correct, "inclusive": correct or choice == "BOTH", "both": choice == "BOTH",
            "cluster": gt["cluster"], "item_id": r["item_id"], "sample": r["sample"],
        })
    results = []
    for (reader, layer, row_class), group in sorted(groups.items()):
        n, a = len(group), sum(r["annotated"] for r in group)
        strict, inclusive, both = (sum(r[field] for r in group) for field in ("strict", "inclusive", "both"))
        results.append({"reader": reader, "layer": layer, "class": row_class,
            "expected_readouts": n, "available_readouts": sum(r["available"] for r in group),
            "annotated_readouts": a, "missing_judgments": n-a, "n_items": len({r["item_id"] for r in group}),
            "n_template_clusters": len({r["cluster"] for r in group}),
            "status": "DESCRIPTIVE_COMPLETE" if a == n else "DESCRIPTIVE_INCOMPLETE",
            "strict_correct_only": _rate(strict, a), "inclusive_contains_true": _rate(inclusive, a),
            "both_rate": _rate(both, a), "strict_missing_as_failure": _rate(strict, n),
            "inclusive_missing_as_failure": _rate(inclusive, n),
            "strict_rate": strict/n if a == n else None,
            "inclusive_rate": inclusive/n if a == n else None})
    report = {"status": "DESCRIPTIVE_COMPLETE" if results and all(r["missing_judgments"] == 0 for r in results) else "DESCRIPTIVE_INCOMPLETE",
        "rows": results, "split": "test", "rule": "BRIEF_BLINDSPOT §70 unasked recall (descriptive)",
        "rubric": RUBRIC, "packet_seal_sha256": P.sha(packet / "PACKET_SEAL.json"),
        "annotation_seal_sha256": P.sha(annotations / "ANNOTATION_SEAL.json"),
        "labels_sha256": P.sha(labels),
        "uncertainty_note": "Wilson intervals are readout-level summaries; template/item dependence and deterministic baseline repeats are not modeled."}
    out.mkdir(parents=True, exist_ok=False)
    P.dump(out / "recall.json", report)
    P.dump(out / "RECALL_SEAL.json", {"status": "DESCRIPTIVE_RECALL_ANALYSIS", "files": {"recall.json": P.sha(out / "recall.json")}})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    commands = {
        "packet": (build_packet, ("bank", "target", "nla", "out")),
        "seal-annotations": (seal_annotations, ("packet", "annotations", "out")),
        "analyse": (analyse, ("packet", "annotations", "labels", "out")),
    }
    for name, (_, fields) in commands.items():
        cmd = sub.add_parser(name)
        for field in fields:
            cmd.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args(argv)
    function, fields = commands[args.phase]
    with P.logged("recall_" + args.phase):
        function(*(getattr(args, field) for field in fields))


if __name__ == "__main__":
    main()
