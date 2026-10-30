"""CPU-only §191 clarification 4: select frozen controls without sampling/fitting.

The original sampler, BOW result and structural bank stay immutable. The public
manifest retains the capture protocol's hash-only schema; the bound gate report
records the exemption explicitly, while gate_pass remains false for W7/W8.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from .custody import read_jsonl, sha256, write_json
from .delivery import checked_file, read_json, require, validate_private_bank

AUTHORITY = "19da310478230f227e2d568d625b11ef49a04095"
RAW_MANIFEST = "bdebdff11d52a8a7261f8ae7b9a6988f7b3af35ae3678e4b812c1bf09a493277"
ORIGINAL_MANIFEST = "cc7d852ef84b2763c3d02141cdf9e1c516b28525a47362496c1b59c9aeb68669"
CONTROLS = ["W7", "W8"]


def subset_bytes(path: Path, ids: set[str]) -> bytes:
    """Keep selected records byte-for-byte, including their original ordering."""
    lines = path.read_bytes().splitlines(keepends=True)
    return b"".join(line for line in lines if json.loads(line)["id"] in ids)


def build(raw: Path, original: Path, out: Path, repo: Path) -> dict:
    checked_file(raw / "public/MANIFEST.json", RAW_MANIFEST)
    checked_file(original / "public/MANIFEST.json", ORIGINAL_MANIFEST)
    # Require the actual immutable ruling in local Git, never just an arbitrary
    # caller-provided exemption flag or a prospective approval.
    ruling = subprocess.check_output(["git", "show", AUTHORITY + ":projects/g_agreement/BRIEF_UNDERSTAND.md"], cwd=repo, text=True)
    require("**W7 and W8 are exempt from the BOW gate as positive controls.**" in ruling, "Missing committed ruling")
    manifest = read_json(raw / "public/MANIFEST.json")
    prior = read_json(original / "public/MANIFEST.json")
    for field, relative in (("items_sha256", "public/items.jsonl"),
                            ("private_labels_sha256", "private/labels.jsonl")):
        checked_file(raw / relative, manifest[field])
        checked_file(original / relative, prior[field])
    checked_file(raw / "private/SAMPLE_REPORT.json", manifest["sample_report_sha256"])
    checked_file(original / "GATE_REPORT.json", prior["gate_report_sha256"])
    gate = read_json(original / "GATE_REPORT.json")
    checked_file(original / "private/BOW_FITS.json", gate["fits_sha256"])
    require(gate["sample_manifest_sha256"] == RAW_MANIFEST, "Original gate has different sample")
    items, labels = read_jsonl(raw / "public/items.jsonl"), read_jsonl(raw / "private/labels.jsonl")
    validate_private_bank(items, labels, ["W1", "W2", "W3", "W4", "W5", *CONTROLS])
    kept = [r for r in labels if r["state"] in CONTROLS]
    ids = {r["id"] for r in kept}
    selected = [r for r in items if r["id"] in ids]
    validate_private_bank(selected, kept, CONTROLS)
    require(len(selected) == 1432, "Frozen control count differs")
    require(ids.isdisjoint(r["id"] for r in read_jsonl(original / "public/items.jsonl")), "Recaptures structural position")
    out.mkdir(parents=True, exist_ok=False)
    (out / "public").mkdir()
    (out / "private").mkdir()
    for relative in ("public/items.jsonl", "private/labels.jsonl"):
        (out / relative).write_bytes(subset_bytes(raw / relative, ids))
    amended = {**gate, "included_states": CONTROLS, "excluded_states": ["W6"],
               "out_of_scope_states": ["W1", "W2", "W3", "W4", "W5"],
               "metrics": {s: gate["metrics"][s] for s in CONTROLS},
               "all_states_gated_including_controls": False,
               "bow_exempt_states": CONTROLS, "authority_commit": AUTHORITY,
               "original_gate_report_sha256": prior["gate_report_sha256"],
               "original_bank_manifest_sha256": ORIGINAL_MANIFEST,
               "retained_private_labels_sha256": sha256(out / "private/labels.jsonl"),
               "no_resampling_or_refitting": True}
    write_json(out / "GATE_REPORT.json", amended)
    public = {**prior, "items": len(selected), "items_sha256": sha256(out / "public/items.jsonl"),
              "private_labels_sha256": amended["retained_private_labels_sha256"],
              "gate_report_sha256": sha256(out / "GATE_REPORT.json")}
    write_json(out / "public/MANIFEST.json", public)
    receipt = {"schema": "e73-controls-supplement-v1", "authority_commit": AUTHORITY,
               "raw_manifest_sha256": RAW_MANIFEST, "original_manifest_sha256": ORIGINAL_MANIFEST,
               "supplement_manifest_sha256": sha256(out / "public/MANIFEST.json"),
               "items_sha256": public["items_sha256"], "private_labels_sha256": public["private_labels_sha256"],
               "gate_report_sha256": public["gate_report_sha256"],
               "capture_positions": 1432, "reader_positions_per_reader": 400,
               "byte_preserved_subset": True, "global_document_cap_verified_on_full_raw_bank": 2,
               "states": {s: {"dev": sum(r["state"] == s and r["split"] == "dev" for r in kept),
                               "test": sum(r["state"] == s and r["split"] == "test" for r in kept),
                               "reader_selected": sum(r["state"] == s and r["reader_selected"] for r in kept),
                               "bow_auroc": gate["metrics"][s]["test_auroc"], "bow_exempt": True} for s in CONTROLS}}
    write_json(out / "DERIVATION.json", receipt)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(build(a.raw, a.original, a.out, Path.cwd()), sort_keys=True))


if __name__ == "__main__":
    main()
