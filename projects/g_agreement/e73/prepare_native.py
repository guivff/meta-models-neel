"""CPU-only packaging of already frozen E73 reader shards after I-2 GO.

This command accepts, verifies, and copies I-2's admissions/GO/forecast proof.
It never creates authorization, estimates a forecast, loads a model, generates
text, or reads reader outcomes. Private labels/probes/capture files stay on CPU.
Each deterministic tar.gz contains one unchanged opaque residual shard, public
hash-only metadata, and the explicit committed native runtime source allowlist.

I-2 must issue a separate MINIMAL native admission with exactly the fields in
BASE_ADMISSION | NATIVE_ADMISSION | OPERATOR_ADMISSION. Rich operator admissions
(for example the capture admission at dc70fa6c) cannot be reused directly: budget
rationales, conditions, provider/disk metadata and runtime-pin receipts
stay in I-2's CPU-side operator record. This tool never strips fields or creates,
rewrites, or signs an authorization. It stages the supplied minimal bytes exactly.
The required retrieval_allowance_seconds is a finite nonnegative budget reserve;
it counts alongside worker and staging caps in per-shard and aggregate E73 limits.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import zipfile

from .custody import (MAX_ARCHIVE_BYTES, MAX_GPU_SECONDS, check_admission, check_go, forecast_proof,
                      seal, sha256, verify_seal)
from .preflight import NATIVE_SOURCES, PACKAGE_SOURCES, validate_bank_manifest

REPO = Path(__file__).resolve().parents[3]
SOURCE_ALLOWLIST = NATIVE_SOURCES | PACKAGE_SOURCES
BASE_ADMISSION = {"schema", "track", "authorized_by", "sampler_commit", "input_sha256", "bank_manifest_sha256",
                  "gpu_count", "gpu_seconds_cap", "prior_track_gpu_seconds", "forecast_gpu_seconds",
                  "staging_cap_seconds", "combined_spend_before_usd", "launch_spend_cap_usd", "daily_ceiling_usd", "source_files"}
NATIVE_ADMISSION = {"native_seconds_per_item", "nla_setup_seconds", "staging_readiness_policy", "retrieval_allowance_seconds"}
OPERATOR_ADMISSION = {"run_id", "run_kind", "runtime_commit", "code_sha256"}
GO_FIELDS = {"schema", "authorized_by", "action", "capture_seal_sha256", "bank_manifest_sha256",
             "jforecast_commit", "jforecast_sha256", "judging_authorized"}
PROOF_FIELDS = {"schema", "verified_by", "commit", "artifact_sha256"}
INDEX_FIELDS = {"schema", "bank_manifest_sha256", "source_capture_seals", "probe_seal_sha256", "shards", "total", "labels_present"}
FIXED_DATA = {"inputs/BANK_MANIFEST.json", "inputs/READER_INPUTS.json", "control/ADMISSION.json",
              "control/GO.json", "control/FORECAST_PROOF.json"}
MAX_EXPANDED = 40_000_000
SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
ID = re.compile(r"[0-9a-f]{32,64}\Z")
SHARD = re.compile(r"reader-input-[0-9]{3}\.npz\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def decode_json(content):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "Duplicate JSON field")
            value[key] = item
        return value
    def reject(_):
        raise ValueError("Nonfinite JSON value")
    return json.loads(content.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)


def read_file(path):
    require(path.is_file() and not path.is_symlink(), "Input must be an ordinary existing file")
    return path.read_bytes()


def validate_native_admission(value, *, input_sha, bank_sha, source_hashes, source_commit):
    check_admission(value, input_sha, bank_sha)
    require(set(value) == BASE_ADMISSION | NATIVE_ADMISSION | OPERATOR_ADMISSION, "Native admission must use exact I-2 schema including operator provenance")
    require(value["source_files"] == source_hashes, "Admission source map differs from committed runtime")
    require(value["staging_readiness_policy"] == "first_reader_then_continuous_model_switch", "Wrong native readiness policy")
    rates = value["native_seconds_per_item"]
    require(isinstance(rates, dict) and set(rates) == {"oracle", "nla"}, "Both native path rates required")
    require(all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in [*rates.values(), value["nla_setup_seconds"]]), "Native path rates/setup must be positive finite numbers")
    retrieval = value["retrieval_allowance_seconds"]
    require(type(retrieval) in (int, float) and math.isfinite(retrieval) and retrieval >= 0,
            "Retrieval allowance must be a finite nonnegative number")
    require(value["prior_track_gpu_seconds"] + value["gpu_seconds_cap"] + value["staging_cap_seconds"] + retrieval <= MAX_GPU_SECONDS,
            "NO_FIT: per-shard worker, staging, and retrieval reservation exceeds aggregate E73 cap")
    require(isinstance(value["run_id"], str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value["run_id"]), "Operator run ID must be opaque")
    require(value["run_kind"] == "real" and value["runtime_commit"] == source_commit and COMMIT.fullmatch(source_commit), "Operator runtime provenance differs")
    source_map_digest = digest(json.dumps(source_hashes, sort_keys=True, separators=(",", ":")).encode())
    require(value["code_sha256"] == source_map_digest, "Operator code SHA differs from canonical source map")


def committed_sources(repo, commit, source_hashes):
    require(isinstance(commit, str) and COMMIT.fullmatch(commit), "Full immutable runtime source commit required")
    require(isinstance(source_hashes, dict) and NATIVE_SOURCES <= source_hashes.keys() <= SOURCE_ALLOWLIST,
            "Native source allowlist/dependencies incomplete")
    result = {}
    for name, expected in source_hashes.items():
        require(isinstance(expected, str) and SHA.fullmatch(expected), "Invalid source digest")
        content = subprocess.run(["git", "show", commit + ":" + name], cwd=repo, check=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        require(digest(content) == expected, "Runtime source differs from declared commit")
        compile(content, name, "exec", dont_inherit=True)
        result[name] = content
    return result


def checked_seal(directory, filename, kind):
    """Reject outcome paths before verify_seal hashes anything besides the seal."""
    value = decode_json(read_file(directory / filename))
    require(value.get("schema") == "e73-seal-v1" and value.get("status") == "COMPLETE" and value.get("track") == "C", "Incomplete or unsupported input seal")
    for name in value["files"]:
        if kind == "reader_inputs":
            allowed = name == "READER_INPUTS.json" or SHARD.fullmatch(name)
        elif kind == "capture":
            allowed = name in {"CAPTURE_REPORT.json", "ADMISSION.json", "MODEL_READY.json"} or re.fullmatch(r"capture-[0-9]{5}\.npz", name)
        elif kind == "probes":
            allowed = name == "PROBE_REPORT.json" or re.fullmatch(r"W[1-8]_probe\.npz", name)
        else:
            raise ValueError("Unknown CPU seal kind")
        require(bool(allowed), "Forbidden outcome or private path in seal inventory")
    return verify_seal(directory, filename)


def validate_residual_bytes(content):
    import numpy as np
    require(len(content) <= MAX_ARCHIVE_BYTES, "Reader input shard exceeds 20 MB")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        members = archive.infolist()
        require({m.filename for m in members} == {"ids.npy", "block44.npy", "block42.npy"} and len(members) == 3,
                "Residual NPZ contains unexpected or duplicate member")
        require(sum(m.file_size for m in members) <= MAX_ARCHIVE_BYTES, "Residual NPZ inflation exceeds bound")
    with np.load(io.BytesIO(content), allow_pickle=False) as data:
        require(set(data.files) == {"ids", "block44", "block42"}, "Reader shard contains labels or unexpected arrays")
        ids = data["ids"].tolist()
        require(1 <= len(ids) <= 900 and len(set(ids)) == len(ids) and all(isinstance(uid, str) and ID.fullmatch(uid) for uid in ids), "Invalid/duplicate reader IDs")
        vectors = {44: data["block44"], 42: data["block42"]}
        require(all(x.shape == (len(ids), 5120) and x.dtype == np.float16 and np.isfinite(x).all() for x in vectors.values()), "Reader residual dtype/shape/finite failure")
        return ids, vectors


def validate_index(value, bank_sha):
    require(isinstance(value, dict) and set(value) == INDEX_FIELDS, "Reader index must be exact label-free schema")
    require(value["schema"] == "e73-reader-inputs-v1" and value["labels_present"] is False and value["bank_manifest_sha256"] == bank_sha, "Reader index bank binding/schema differs")
    require(isinstance(value["probe_seal_sha256"], str) and SHA.fullmatch(value["probe_seal_sha256"]), "Missing probe seal binding")
    seen = set()
    for capture in value["source_capture_seals"]:
        require(set(capture) == {"seal_sha256"} and SHA.fullmatch(capture["seal_sha256"]), "Capture reference must be a hash only")
        require(capture["seal_sha256"] not in seen, "Duplicate capture reference")
        seen.add(capture["seal_sha256"])
    require(seen, "Reader index requires original captures")
    names = set()
    for shard in value["shards"]:
        require(set(shard) == {"file", "count", "sha256", "bytes"}, "Reader shard metadata must be label-free")
        require(SHARD.fullmatch(shard["file"]) and shard["file"] not in names, "Invalid/duplicate reader shard path")
        require(type(shard["count"]) is int and shard["count"] > 0 and type(shard["bytes"]) is int and 0 < shard["bytes"] <= MAX_ARCHIVE_BYTES and SHA.fullmatch(shard["sha256"]), "Invalid reader shard metadata")
        names.add(shard["file"])
    require(type(value["total"]) is int and value["total"] == sum(s["count"] for s in value["shards"]) and value["total"] > 0, "Reader index total differs")


def validate_capture_probe_bindings(index, capture_dirs, probes, bank_sha):
    import numpy as np
    captures = []
    for directory in capture_dirs:
        value = checked_seal(directory, "CAPTURE_SEAL.json", "capture")
        require(value.get("bank_manifest_sha256") == bank_sha, "Original capture belongs to another bank")
        require("CAPTURE_REPORT.json" in value["files"], "Capture report unsealed")
        report = decode_json(read_file(directory / "CAPTURE_REPORT.json"))
        require(report.get("status") == "COMPLETE" and report.get("reader_outputs") == 0 and report.get("labels_present") is False, "Capture is not a completed label-free forward stage")
        captures.append(sha256(directory / "CAPTURE_SEAL.json"))
    require(sorted(captures) == sorted(x["seal_sha256"] for x in index["source_capture_seals"]), "Original capture inventory differs from reader index")
    value = checked_seal(probes, "PROBE_SEAL.json", "probes")
    require(sha256(probes / "PROBE_SEAL.json") == index["probe_seal_sha256"], "Exported input probe binding differs")
    require(value.get("cpu_private") is True and "PROBE_REPORT.json" in value["files"], "Probe report must remain CPU-private")
    report = decode_json(read_file(probes / "PROBE_REPORT.json"))
    require(report.get("bank_manifest_sha256") == bank_sha and report.get("readers") == "NOT_RUN", "Probe custody is not pre-reader for this bank")
    require(sorted(x["seal_sha256"] for x in report["capture_seals"]) == sorted(captures), "Probe and reader source captures differ")
    selected = {}
    expected_files = {"PROBE_REPORT.json"}
    for row in report["rows"]:
        require(re.fullmatch(r"W[1-8]", row["state"]), "Unexpected probe state identifier")
        name = row["state"] + "_probe.npz"
        expected_files.add(name)
        with np.load(probes / name, allow_pickle=False) as data:
            expected_keys = {"direction", "intercept", "scaler_mean", "scaler_scale", "dev_mean_A", "dev_mean_B", "test_mean_A", "test_mean_B", "test_block44", "test_block42", "test_ids", "test_labels", "test_scores", "reader_ids"}
            require(set(data.files) == expected_keys, "Unexpected probe arrays")
            test_ids, chosen = data["test_ids"].tolist(), data["reader_ids"].tolist()
            require(test_ids == sorted(set(test_ids)) and chosen == test_ids[:200], "Reader positions are not frozen first200 test IDs")
            for i, uid in enumerate(test_ids):
                if uid in set(chosen):
                    require(uid not in selected, "Repeated selected ID across states")
                    selected[uid] = {44: data["test_block44"][i].astype(np.float16), 42: data["test_block42"][i].astype(np.float16)}
    require(set(value["files"]) == expected_files, "Probe seal has missing or extra state files")
    return selected


def archive_bytes(files):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, content in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(content), 0, 0o600
            tar.addfile(info, io.BytesIO(content))
    require(len(raw.getvalue()) <= MAX_EXPANDED, "Expanded native archive exceeds bound")
    return gzip.compress(raw.getvalue(), mtime=0)


def inspect_archive(raw, *, expected_files, source_hashes, source_commit, index_sha, bank_sha):
    """Exact no-extraction preflight; compile source without importing/executing."""
    require(len(raw) <= MAX_ARCHIVE_BYTES, "Native upload exceeds 20 MB")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        expanded = stream.read(MAX_EXPANDED + 1)
    require(len(expanded) <= MAX_EXPANDED, "Native decompression exceeds bound")
    found, expected_offset = {}, 0
    with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:", ignore_zeros=True) as tar:
        for member in tar:
            name, path = member.name, PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in name and ":" not in name and name == path.as_posix(), "Unsafe native archive path")
            require(member.isfile() and not member.issym() and not member.islnk() and not member.sparse and not member.pax_headers, "Only ordinary native archive members allowed")
            require(name in expected_files and name not in found, "Extra or duplicate native archive member")
            require(member.offset == expected_offset and member.offset_data == member.offset + 512, "Extended or hidden tar header")
            data = tar.extractfile(member).read()
            require(data == expected_files[name], "Native archive differs from approved exact bytes")
            found[name] = data
            expected_offset = member.offset_data + ((member.size + 511) // 512) * 512
    require(set(found) == set(expected_files) and not any(expanded[expected_offset:]), "Missing native archive member or trailing payload")
    residual_names = [name for name in found if name.startswith("inputs/reader-input-")]
    require(len(residual_names) == 1 and set(found) == FIXED_DATA | set(source_hashes) | set(residual_names), "Native archive allowlist differs")
    ids, _ = validate_residual_bytes(found[residual_names[0]])
    for name, expected in source_hashes.items():
        require(name in SOURCE_ALLOWLIST and digest(found[name]) == expected, "Native source digest differs")
        compile(found[name], name, "exec", dont_inherit=True)
    require(digest(found["inputs/BANK_MANIFEST.json"]) == bank_sha and digest(found["inputs/READER_INPUTS.json"]) == index_sha, "Native metadata hash binding differs")
    validate_bank_manifest(decode_json(found["inputs/BANK_MANIFEST.json"]))
    index = decode_json(found["inputs/READER_INPUTS.json"])
    validate_index(index, bank_sha)
    admission = decode_json(found["control/ADMISSION.json"])
    validate_native_admission(admission, input_sha=digest(found[residual_names[0]]), bank_sha=bank_sha,
                              source_hashes=source_hashes, source_commit=source_commit)
    go = decode_json(found["control/GO.json"])
    require(set(go) == GO_FIELDS, "GO contains unexpected metadata")
    check_go(go, capture_seal_sha=index_sha, input_manifest_sha=bank_sha)
    proof = decode_json(found["control/FORECAST_PROOF.json"])
    require(set(proof) == PROOF_FIELDS and proof.get("schema") == "e73-forecast-proof-v1" and proof.get("verified_by") == "I-2" and proof.get("commit") == go["jforecast_commit"] and proof.get("artifact_sha256") == go["jforecast_sha256"], "Forecast proof differs from GO")
    return {"status": "PREFLIGHT_PASS", "archive_sha256": digest(raw), "archive_bytes": len(raw), "expanded_bytes": len(expanded),
            "positions": len(ids), "members": sorted(found), "source_files": source_hashes,
            "bank_manifest_sha256": bank_sha, "reader_index_sha256": index_sha,
            "grants_admission_or_go": False, "native_generation_started": False}


def prepare(args):
    import numpy as np
    require(not args.out.exists(), "Native package output must be a new directory")
    bank_bytes = read_file(args.bank_manifest)
    validate_bank_manifest(decode_json(bank_bytes))
    bank_sha = digest(bank_bytes)
    index_bytes = read_file(args.reader_inputs / "READER_INPUTS.json")
    index, index_sha = decode_json(index_bytes), digest(index_bytes)
    validate_index(index, bank_sha)
    go_bytes, proof_bytes = read_file(args.go), read_file(args.forecast_proof)
    go, proof = decode_json(go_bytes), decode_json(proof_bytes)
    require(set(go) == GO_FIELDS, "GO contains unexpected metadata")
    check_go(go, capture_seal_sha=index_sha, input_manifest_sha=bank_sha)
    expected_proof = forecast_proof(args.repo, go["jforecast_commit"], args.forecast_artifact_path, go["jforecast_sha256"])
    require(set(proof) == PROOF_FIELDS and proof == expected_proof, "Supplied CPU forecast proof does not match actual committed forecast")
    metadata = checked_seal(args.reader_inputs, "READER_INPUT_SEAL.json", "reader_inputs")
    require(metadata.get("labels_present") is False, "Reader input seal must explicitly exclude labels")
    require(set(metadata["files"]) == {"READER_INPUTS.json"} | {s["file"] for s in index["shards"]}, "Reader input seal/index coverage differs")
    selected = validate_capture_probe_bindings(index, args.capture, args.probes, bank_sha)
    require(len(selected) == index["total"], "Frozen reader selection count differs")
    admission_by_hash = {}
    for path in args.admission:
        content = read_file(path)
        value = decode_json(content)
        key = value.get("input_sha256")
        require(key not in admission_by_hash, "Duplicate admission for a native input shard")
        admission_by_hash[key] = (value, content, path)
    require(set(admission_by_hash) == {s["sha256"] for s in index["shards"]}, "Must supply exactly one I-2 admission per frozen reader shard")
    source_hashes = next(iter(admission_by_hash.values()))[0]["source_files"]
    sources = committed_sources(args.repo, args.source_commit, source_hashes)
    admissions = [record[0] for record in admission_by_hash.values()]
    for value in admissions:
        validate_native_admission(value, input_sha=value["input_sha256"], bank_sha=bank_sha,
                                  source_hashes=source_hashes, source_commit=args.source_commit)
    require(len({value["run_id"] for value in admissions}) == len(admissions), "Native shards require distinct per-process run IDs")
    compute_staging_seconds = sum(value["gpu_seconds_cap"] + value["staging_cap_seconds"] for value in admissions)
    retrieval_seconds = sum(value["retrieval_allowance_seconds"] for value in admissions)
    reserved_seconds = compute_staging_seconds + retrieval_seconds
    prior_seconds = min(value["prior_track_gpu_seconds"] for value in admissions)
    require(prior_seconds + reserved_seconds <= MAX_GPU_SECONDS, "NO_FIT: combined native package reservations exceed aggregate E73 cap")
    reserved_spend = sum(value["launch_spend_cap_usd"] for value in admissions)
    prior_spend = min(value["combined_spend_before_usd"] for value in admissions)
    require(prior_spend + reserved_spend <= min(value["daily_ceiling_usd"] for value in admissions), "NO_FIT: combined native package reservations exceed daily ceiling")
    prepared, seen = [], set()
    for shard in index["shards"]:
        content = read_file(args.reader_inputs / shard["file"])
        require(digest(content) == shard["sha256"] and len(content) == shard["bytes"], "Reader residual shard changed")
        ids, vectors = validate_residual_bytes(content)
        require(len(ids) == shard["count"], "Reader residual count differs")
        for i, uid in enumerate(ids):
            require(uid in selected and uid not in seen, "Reader shard has missing, repeated, or unselected ID")
            require(all(np.array_equal(vectors[layer][i], selected[uid][layer]) for layer in (44, 42)), "Reader residual differs from frozen probe export")
            seen.add(uid)
        admission, admission_bytes, admission_path = admission_by_hash[shard["sha256"]]
        validate_native_admission(admission, input_sha=shard["sha256"], bank_sha=bank_sha,
                                  source_hashes=source_hashes, source_commit=args.source_commit)
        files = {**sources, "inputs/" + shard["file"]: content, "inputs/READER_INPUTS.json": index_bytes,
                 "inputs/BANK_MANIFEST.json": bank_bytes, "control/ADMISSION.json": admission_bytes,
                 "control/GO.json": go_bytes, "control/FORECAST_PROOF.json": proof_bytes}
        raw = archive_bytes(files)
        preflight = inspect_archive(raw, expected_files=files, source_hashes=source_hashes,
                                    source_commit=args.source_commit, index_sha=index_sha, bank_sha=bank_sha)
        name = shard["file"].removesuffix(".npz") + ".tar.gz"
        preflight.update(file=name, input_sha256=shard["sha256"], admission_sha256=digest(admission_bytes),
                         run_id=admission["run_id"], run_kind=admission["run_kind"], runtime_commit=admission["runtime_commit"], code_sha256=admission["code_sha256"],
                         command=["python", "-m", "projects.g_agreement.e73.native", "--inputs", "inputs/" + shard["file"],
                                  "--index", "inputs/READER_INPUTS.json", "--admission", "control/ADMISSION.json",
                                  "--go", "control/GO.json", "--forecast-proof", "control/FORECAST_PROOF.json",
                                  "--repo", ".", "--out", "outputs", "--staging-started-unix", "OPERATOR_SUPPLIED_ORIGINAL_STAGING_TIMESTAMP"])
        prepared.append((name, raw, preflight))
    require(seen == set(selected), "Native packages omitted selected IDs")
    args.out.mkdir(parents=True, exist_ok=False)
    for name, raw, _ in prepared:
        (args.out / name).write_bytes(raw)
    result = {"schema": "e73-native-packages-v1", "track": "C", "cpu_only": True,
              "source_commit": args.source_commit, "source_files": source_hashes,
              "reader_input_seal_sha256": sha256(args.reader_inputs / "READER_INPUT_SEAL.json"),
              "reader_index_sha256": index_sha, "bank_manifest_sha256": bank_sha,
              "source_capture_seals": index["source_capture_seals"], "probe_seal_sha256": index["probe_seal_sha256"],
              "jforecast_commit": go["jforecast_commit"], "jforecast_sha256": go["jforecast_sha256"],
              "go_sha256": digest(go_bytes), "forecast_proof_sha256": digest(proof_bytes),
              "total_positions": len(seen), "archives": [r for _, _, r in prepared],
              "reservation_check": {"minimum_admitted_prior_track_seconds": prior_seconds,
                                    "sum_package_caps_plus_staging_seconds": compute_staging_seconds,
                                    "sum_retrieval_allowance_seconds": retrieval_seconds,
                                    "sum_package_caps_plus_staging_and_retrieval_seconds": reserved_seconds,
                                    "minimum_admitted_combined_spend_before_usd": prior_spend,
                                    "sum_launch_spend_caps_usd": reserved_spend},
              "operator_final_sidecar_required": True, "judging_authorized": False,
              "native_generation_started": False, "reader_outputs_opened": 0,
              "grants_admission_or_go": False, "builder_sha256": sha256(Path(__file__))}
    with (args.out / "NATIVE_PACKAGES.json").open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    seal(args.out, "NATIVE_PACKAGE_SEAL.json", [args.out / name for name, _, _ in prepared] + [args.out / "NATIVE_PACKAGES.json"],
         status="COMPLETE", track="C", cpu_only=True, grants_admission_or_go=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog=
        "Exact minimal native admission fields: " + ", ".join(sorted(BASE_ADMISSION | NATIVE_ADMISSION | OPERATOR_ADMISSION)) +
        ". Retrieval allowance is finite and nonnegative and counts in per-shard and aggregate E73 limits. "
        "I-2 supplies these files; extra operator metadata remains in the CPU sidecar. Nothing is silently stripped.")
    for name in ("reader-inputs", "bank-manifest", "probes", "go", "forecast-proof", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--capture", type=Path, nargs="+", required=True)
    parser.add_argument("--admission", type=Path, nargs="+", required=True,
                        help="One unmodified I-2 minimal native admission per exported shard; exact fields listed below")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--forecast-artifact-path", required=True, help="CPU-only repository-relative forecast path; never staged")
    result = prepare(parser.parse_args())
    print(json.dumps({"status": "NATIVE_PACKAGES_PREFLIGHT_PASS", "archives": len(result["archives"]),
                      "positions": result["total_positions"], "native_generation_started": False}))


if __name__ == "__main__":
    main()
