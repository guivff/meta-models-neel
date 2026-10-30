"""Bind only frozen candidate metadata after E36's independent bank is sealed.

Never opens item, label, score, metric or historical outcome files. Candidate
strings are copied verbatim, including whitespace, with their original ordering.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import channel_contract as C

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BANK_DIRECTORY = "results/g_agreement/understand/e36/cache/v2_25_2026-10-25"
FREEZE_ANCHORS = {
    "BANK_SOURCE_SEAL.json": "ed064ff2ef4cd9075052d39766f42b8801a3d4e1982f59ef9e428853719d0a6c",
    "PREPARED_SEAL.json": "381fad8114a3dcd4a1142f9b776840d611db6c0ca10fad054a807a81c46e0b37",
    "FREEZE_RECEIPT.json": "e6c1a2349f9dca7faead507bfc521fce8e4e47dd1bba8b317bae4c9f1c38c184",
}
SOURCES = {
    "w1_descriptive_nla": {
        "path": "results/g_agreement/blindspot/w1/freeze/templates.json",
        "sha256": "57cad0d1bce20de00026cab2515b3c43a2925d50b2944e0d0556376e88833172",
        "commit": "fe7c7513d592ed384ab3930ec07ec1efb830862f",
    },
    "e15_continuation": {
        "path": "results/g_agreement/understand/e15/CONTINUATION_PAIRS.json",
        "sha256": "fefdea108ad4132a3f6d8670d379319df5a6c8bc6eef76c4cd674789c7b9573d",
        "commit": "1607a250000463eb1f75fdf557c24c7b0f10a8a4",
    },
    "e30_value_word": {
        "path": "results/g_agreement/understand/e30/CANDIDATES.json",
        "sha256": "f0632205097de5b5c7cd695a2c3a235fb4136e2e11cbf5034606a00387960b12",
        "commit": "bbd545c7558ced41df2f49d17ec19f0d0d6a4dd7",
    },
}


def write_new(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False, ensure_ascii=False)
        stream.write("\n")


def freeze_gate(root, now):
    """Only these three bank receipts and the permitted definition packet open."""
    root = Path(root)
    directory = root / BANK_DIRECTORY
    receipts = {name: C.read_bound({"path": str(directory / name), "sha256": digest}) for name, digest in FREEZE_ANCHORS.items()}
    source, prepared, freeze = (receipts[name] for name in ("BANK_SOURCE_SEAL.json", "PREPARED_SEAL.json", "FREEZE_RECEIPT.json"))
    C.require(source["W1_items_accessed"] is False and source["W1_scores_accessed"] is False and source["model_calls"] == 0,
              "bank blindness or pre-capture provenance failed")
    C.require(prepared.get("complete") is True, "bank preparation incomplete")
    for name in ("BANK_SOURCE_SEAL.json", "FREEZE_RECEIPT.json"):
        C.require(prepared["files"].get(name) == FREEZE_ANCHORS[name], "prepared seal does not bind freeze/source receipt")
    C.require(freeze.get("model_calls") == 0 and freeze.get("bank_source_seal_sha256") == FREEZE_ANCHORS["BANK_SOURCE_SEAL.json"], "freeze/source binding mismatch")
    packet_binding = {"path": str(root / "results/g_agreement/understand/e36/ROW_DEFINITIONS.json"), "sha256": C.DEFINITION_PACKET_SHA256}
    scope = C.scope_from_definition_packet(packet_binding)
    C.validate_freeze_receipt(freeze, {"sha256": freeze["bank_sha256"]}, scope)
    C.require(C.instant(freeze["frozen_at"]) <= C.instant(now), "candidate access attempted before bank freeze")
    C.require(C.instant(freeze["frozen_at"]) <= C.instant(C.EXPANDED_FREEZE_DEADLINE), "expanded bank missed deadline")
    return freeze, scope, C.read_bound(packet_binding)


def load_candidate_sources(root):
    """Fixed allowlist; also prove each content hash belongs to its cited commit."""
    loaded, provenance = {}, {}
    for key, binding in SOURCES.items():
        path = Path(root) / binding["path"]
        data = path.read_bytes()
        C.require(hashlib.sha256(data).hexdigest() == binding["sha256"], "frozen candidate source changed: " + key)
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        committed_blob = subprocess.check_output(["git", "rev-parse", binding["commit"] + ":" + binding["path"]], cwd=root, text=True).strip()
        C.require(blob == committed_blob, "candidate bytes differ from cited commit: " + key)
        loaded[key] = json.loads(data)
        provenance[key] = {**binding, "git_blob": blob}
    return loaded, provenance


def checked_pairs(pairs, context, *, allow_whitespace=False):
    C.require(isinstance(pairs, list) and len(pairs) == 2, context + " must have the two frozen pairs")
    C.require(all(isinstance(p, list) and len(p) == 2 and all(isinstance(s, str) and s and (allow_whitespace or s.strip()) for s in p) for p in pairs), context + " pair schema mismatch")
    return [list(pair) for pair in pairs]


def normalize(packet, source_data, *, scope):
    """Select only ordered values and exact candidate strings, never outcomes."""
    w1 = source_data["w1_descriptive_nla"]
    e15 = source_data["e15_continuation"]
    e30 = source_data["e30_value_word"]
    C.require(e15.get("orientation") == "W1 value A positive, no sign reversal" and e15.get("oracle_prefix") == "- ", "ambiguous E15 orientation/prefix")
    C.require(e30.get("orientation") == "each pair is [value A, value B] in W1 templates.json 'values' order; score = logP(A) - logP(B), A positive", "ambiguous E30 orientation")
    C.require(e30.get("before_any_score") is True and e30.get("w1_templates_sha256") == SOURCES["w1_descriptive_nla"]["sha256"], "E30 candidate freeze does not bind W1 source")
    rows, audit = {}, {}
    for row in scope["rows"]:
        spec, values = w1[row], packet["rows"][row]["values"]
        C.require(spec.get("score_orientation") == "value_A_positive", "ambiguous W1 orientation: " + row)
        C.require(spec["values"] == values == e30["values"][row], "ordered values differ from coordinator packet: " + row)
        descriptive = checked_pairs(spec["olens"], "W1 Oracle " + row)
        nla = checked_pairs(spec["nla"], "W1 NLA " + row)
        value_word = checked_pairs(e30["candidates"][row], "E30 " + row)
        C.require(all(s.startswith("- ") for pair in descriptive + value_word for s in pair), "Oracle bullet prefix framing differs from frozen source: " + row)
        continuation = []
        if row in e15["rows"]:
            raw_pairs = e15["rows"][row]["pairs"]
            C.require(isinstance(raw_pairs, list) and len(raw_pairs) == 2 and all(isinstance(p, dict) and "A" in p and "B" in p for p in raw_pairs), "E15 pair schema mismatch: " + row)
            continuation = checked_pairs([[p["A"], p["B"]] for p in raw_pairs], "E15 " + row, allow_whitespace=True)
        rows[row] = {"values": list(values), "olens_descriptive": descriptive,
                     "olens_value_word": {"e30_bullet": value_word}, "nla": nla, "continuation": continuation}
        audit[row] = {"ordered_values_match": True, "oracle_pair_count": len(descriptive), "nla_pair_count": len(nla),
                      "e30_channel_id": "e30_bullet", "e30_raw_pair_indices": [0, 1], "continuation_pair_count": len(continuation)}
    normalized = {"rows": rows}
    C.validate_candidates(normalized, scope)
    required_h4 = C.EXPANDED_H4_ROWS if scope["id"] == "expanded25" else C.STATES
    C.require(all(rows[row]["continuation"] for row in required_h4), "registered H4 row missing frozen E15 pairs")
    return normalized, audit


def bind(root=ROOT, output=None, public_provenance=None, now=None):
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc).isoformat()
    # This gate must precede any candidate-file access.
    freeze, scope, packet = freeze_gate(root, now)
    source_data, source_provenance = load_candidate_sources(root)
    normalized, row_audit = normalize(packet, source_data, scope=scope)
    C.require(C.instant(source_data["e30_value_word"]["frozen_at"]) <= C.instant(freeze["frozen_at"]), "E30 source freeze postdates the bank")
    for row in scope["rows"]:
        C.require(normalized["rows"][row]["values"] == freeze["rows"][row]["values"], "frozen bank/candidate orientation mismatch")
    output = Path(output) if output else root / "results/g_agreement/understand/e36/cache/postfreeze_candidates_2026-10-25"
    public_provenance = Path(public_provenance) if public_provenance else root / "results/g_agreement/understand/e36/CANDIDATE_PROVENANCE_2026-10-25.json"
    C.require(not output.exists() and not public_provenance.exists(), "candidate binding already exists; never overwrite")
    output.mkdir(parents=True, exist_ok=False)
    candidate_path = output / "candidates.json"
    write_new(candidate_path, normalized)
    candidate_binding = {"path": str(candidate_path.relative_to(root)), "sha256": C.file_hash(candidate_path)}
    provenance = {
        "schema": "e36.postfreeze-candidates.v1", "experiment": "E36", "scope": scope["id"],
        "candidate_bound_at": now, "bank_frozen_at": freeze["frozen_at"], "bank_input_sha256": freeze["bank_sha256"],
        "bank_source_seal_sha256": FREEZE_ANCHORS["BANK_SOURCE_SEAL.json"],
        "prepared_seal_sha256": FREEZE_ANCHORS["PREPARED_SEAL.json"], "freeze_receipt_sha256": FREEZE_ANCHORS["FREEZE_RECEIPT.json"],
        "definition_packet_sha256": C.DEFINITION_PACKET_SHA256,
        "candidate_sources": source_provenance, "normalized_candidates": candidate_binding,
        "extraction_code_sha256": C.file_hash(__file__), "row_audit": row_audit,
        "orientation": "source pair [A,B] and ordered values unchanged; no sign reversal",
        "oracle_descriptive_prefix": "", "oracle_value_word_prefix": "", "oracle_framing": "frozen strings already contain '- '; do not add another bullet prefix",
        "nla_prefix": "<explanation>\n", "continuation_prefix": "- ",
        "e30_grouping": {"channel_id": "e30_bullet", "source_section": 125, "raw_pair_indices": [0, 1],
                         "aggregation": "mean of both frozen pair log-odds; one registered value-word channel"},
        "continuation_rows": [row for row in scope["rows"] if normalized["rows"][row]["continuation"]],
        "h4_population": list(C.EXPANDED_H4_ROWS), "table_column_continuation": "acquired outside the fixed H4 population",
        "no_v2_dev_pair_selection": True, "candidate_strings_edited": False,
        "W1_items_accessed": False, "W1_scores_accessed": False, "historical_item_or_score_artifacts_opened": False,
        "registration_sections_read": [125, 132, 135],
        "model_calls": 0, "bank_modified": False,
    }
    write_new(public_provenance, provenance)
    receipt = {"schema": "e36.candidate-binding-receipt.v1", "complete": True, "candidate_bound_at": now,
               "candidates": candidate_binding, "provenance": {"path": str(public_provenance.relative_to(root)), "sha256": C.file_hash(public_provenance)},
               "freeze_receipt_sha256": FREEZE_ANCHORS["FREEZE_RECEIPT.json"], "bank_source_seal_sha256": FREEZE_ANCHORS["BANK_SOURCE_SEAL.json"],
               "prepared_seal_sha256": FREEZE_ANCHORS["PREPARED_SEAL.json"], "model_calls": 0}
    receipt["binding_sha256"] = C.canonical_hash(receipt)
    write_new(output / "BINDING_RECEIPT.json", receipt)
    return {"status": "BOUND_AFTER_BANK_FREEZE", "candidate_bound_at": now, "candidates": candidate_binding,
            "binding_receipt": str((output / "BINDING_RECEIPT.json").relative_to(root)),
            "provenance_sha256": C.file_hash(public_provenance), "rows": len(normalized["rows"]),
            "continuation_rows": len(provenance["continuation_rows"]), "model_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--provenance", type=Path)
    args = parser.parse_args()
    print(json.dumps(bind(args.root, args.out, args.provenance), sort_keys=True))
