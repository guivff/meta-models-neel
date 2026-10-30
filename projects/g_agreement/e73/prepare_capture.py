"""CPU-only capture package, exact-archive preflight, and request for I-2.

This emits a request, never an admission. No labels or scientific source corpus
enter the upload archive. Runtime hashes are checked against the current commit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from .custody import archive_inputs, read_jsonl, sha256, write_json
from .preflight import CAPTURE_SOURCES, PACKAGE_SOURCES, validate_archive
from .delivery import validate_gate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bank", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report-dir", type=Path, required=True)
    p.add_argument("--sampler-commit", required=True)
    a = p.parse_args()
    root = Path.cwd()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    sources = {name: root / name for name in sorted(CAPTURE_SOURCES | PACKAGE_SOURCES) if (root / name).is_file()}
    hashes = {name: sha256(path) for name, path in sources.items()}
    import hashlib
    for name, digest in hashes.items():
        frozen = subprocess.check_output(["git", "show", f"{commit}:{name}"])
        if hashlib.sha256(frozen).hexdigest() != digest:
            raise ValueError("Runtime is not committed: " + name)
    manifest = a.bank / "public/MANIFEST.json"
    inputs = a.bank / "public/items.jsonl"
    rows = read_jsonl(inputs)
    gate = json.loads((a.bank / "GATE_REPORT.json").read_text())
    validate_gate(gate)
    if sha256(a.bank / "GATE_REPORT.json") != json.loads(manifest.read_text())["gate_report_sha256"]:
        raise ValueError("Gate report hash differs")
    supplement = gate.get("bow_exempt_states") == ["W7", "W8"]
    if not rows:
        raise ValueError("No gate-passing capture positions")
    shards = archive_inputs(rows, a.out, manifest_sha256=sha256(manifest), bank_manifest=manifest,
                            source_files=sources, max_rows=6400)
    a.report_dir.mkdir(parents=True, exist_ok=True)
    write_json(a.report_dir / "RUNTIME_SOURCE_HASHES.json", hashes)
    for shard in shards:
        report = validate_archive(a.out / shard["file"], bank_manifest=manifest, source_hashes=hashes,
                                  expected_archive_sha256=shard["sha256"])
        write_json(a.report_dir / f"PREFLIGHT_{Path(shard['file']).name.split('.')[0]}.json", report)
    request = {
        "schema": "e73-capture-launch-request-v1", "track": "C", "experiment": "E73",
        "status": "REQUEST_ONLY_NOT_ADMITTED", "runtime_commit": commit, "sampler_commit": a.sampler_commit,
        "bank_manifest_sha256": sha256(manifest), "input_sha256": sha256(inputs), "source_files": hashes,
        "archives": shards, "capture_positions": len(rows), "context_tokens": 256,
        "capture": {"block44": "all 256 positions", "block42": "read token 255", "dtype": "float16"},
        "entry_command": "python -m projects.g_agreement.e73.capture --inputs inputs/items.jsonl --manifest inputs/BANK_MANIFEST.json --admission admission.json --out out --repo . --batch-size 4 --staging-started-unix <I-2 staging Unix start>",
        "gpu_count": 1, "minimum_gpu_memory_gb": 80,
        "requirements": ["Python >=3.11", "torch with CUDA", "transformers >=5.2", "numpy", "accelerate", "huggingface_hub", "safetensors"],
        "model": "Qwen/Qwen3.6-27B at core/config.py TARGET_MODEL_SHA; cache ready before admitted launch",
        "weights_download": "No cold-download budget exemption. Use ready anonymous pinned weights/cache; I-2 must verify availability.",
        "forecast_compute_seconds": 450 if supplement else 450 + .5 * len(rows),
        "forecast_status": "PLANNING_FROM_ORIGINAL_4000_CAPTURE_273_SECONDS" if supplement else "PLANNING_UNMEASURED_E73",
        "forecast_multiplier": 1.25, "requested_worker_cap_seconds": 600 if supplement else 3600,
        "staging_cap_seconds": 900, "retrieval_allowance_seconds": 900 if supplement else 1800,
        "maximum_billed_seconds_requested": 2400 if supplement else 6300,
        "maximum_cost_formula": "maximum_billed_seconds_requested/3600 * I-2 accepted single-GPU hourly rate, plus any separately billed storage/network; combine with all shared reservations",
        "rate_and_combined_spend": "I-2 must supply current verified values before admission",
        "remaining_track_budget": "Aggregate capture+reader+staging+retrieval must remain <=21600 GPU-seconds",
        "cleanup": "Worker process hard deadline covers setup/capture/sealing; I-2 external watchdog must stop exact pod by billed deadline, including retrieval. No private whitener, labels, keys or private maps staged.",
        "success_delivery": "Return every capture shard, CAPTURE_REPORT.json and CAPTURE_SEAL.json. Preserve full all-position data. CPU verifies hashes then fits probes and hands capture-only artifacts to W-lens.",
        "reader_release": "NOT_AUTHORIZED; requires capture/probes, committed W-lens J-forecast and separate I-2 GO",
        "judging": "NOT_AUTHORIZED; requires separate Guiv authorisation",
        "included_states": gate["included_states"], "excluded_states": gate["excluded_states"],
        "out_of_scope_states": gate.get("out_of_scope_states", []),
        "bow_exempt_states": gate.get("bow_exempt_states", []),
        "authority_commit": gate.get("authority_commit"),
        "R_W1_content_control": "W7/W8 positive controls, BOW exemption under clarification 4" if supplement else "Historical structural bank; controls supplied separately under clarification 4",
    }
    write_json(a.report_dir / "LAUNCH_REQUEST.json", request)
    print(json.dumps({"status": request["status"], "runtime_commit": commit, "archives": shards}))


if __name__ == "__main__":
    main()
