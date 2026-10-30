"""CPU-private W-lens receipt from verified E73 inputs, captures and probes.

This builder never reads a native-reader output, constructs a G3 value-token set,
or makes a J-forecast. It refuses seals containing any non-allowlisted member
before hashing those members. Explicit operator custody attestations are required;
absence of a file is not treated as evidence of global custody.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess

from .custody import MAX_ARCHIVE_BYTES, read_jsonl, sha256, validate_public, verify_seal
from .states import STATE_VALUES

REPO = Path(__file__).resolve().parents[3]
PROPERTIES = {"W1": "open string", "W2": "bracket depth", "W3": "indentation",
              "W4": "inside call arguments vs at statement level", "W5": "line length so far",
              "W6": "markdown table column", "W7": "code vs prose", "W8": "Wikipedia topic"}
CAPTURE_MEMBERS = {"CAPTURE_REPORT.json", "ADMISSION.json", "MODEL_READY.json"}
PROBE_ARRAYS = {"direction", "intercept", "scaler_mean", "scaler_scale", "dev_mean_A", "dev_mean_B",
                "test_mean_A", "test_mean_B", "test_block44", "test_block42", "test_ids", "test_labels",
                "test_scores", "reader_ids"}
PROBE_ESTIMATOR = {"standardize": "dev_only", "class_positive": "B=1", "C": 1.0,
                   "solver": "lbfgs", "max_iter": 2000, "random_state": 20261027}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_gate(gate):
    """Accept the historical gate or exactly the registered control supplement."""
    require(gate.get("threshold") == .65, "Gate threshold differs")
    exempt = gate.get("bow_exempt_states", [])
    if exempt:
        require(exempt == ["W7", "W8"] and gate.get("included_states") == exempt,
                "Only the separate W7/W8 supplement is exempt")
        require(gate.get("authority_commit") == "19da310478230f227e2d568d625b11ef49a04095",
                "Unregistered BOW exemption")
        require(gate.get("all_states_gated_including_controls") is False
                and gate.get("no_resampling_or_refitting") is True, "Invalid control amendment")
        require(gate.get("original_gate_report_sha256") == "70e1265b6f47caf2bc33c1ed2fba6241bc9116a63ace2faa9ddfa28e6683eadf"
                and gate.get("original_bank_manifest_sha256") == "cc7d852ef84b2763c3d02141cdf9e1c516b28525a47362496c1b59c9aeb68669",
                "Control supplement parent differs")
        require(set(gate["metrics"]) == set(exempt)
                and gate["metrics"]["W7"] == {"dev_items": 400, "test_items": 400, "test_auroc": 1.0, "gate_pass": False}
                and gate["metrics"]["W8"] == {"dev_items": 316, "test_items": 316, "test_auroc": .9641483736580676, "gate_pass": False},
                "Frozen control BOW results differ")
    else:
        require(gate.get("all_states_gated_including_controls") is True, "Gate rules differ")
    for row in gate["metrics"].values():
        require(type(row["test_auroc"]) in (int, float) and math.isfinite(row["test_auroc"]) and 0 <= row["test_auroc"] <= 1,
                "Invalid BOW metric")
        require(row["gate_pass"] == (row["test_auroc"] <= .65), "BOW gate boolean differs from frozen threshold")
    require(set(gate["included_states"]) == ({s for s, row in gate["metrics"].items() if row["gate_pass"]} | set(exempt)),
            "Gate state selection differs")


def read_json(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), "Requires an ordinary existing metadata file")
    return json.loads(path.read_text())


def file_record(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), "Requires an ordinary existing data file")
    return {"path": str(path.resolve()), "sha256": sha256(path), "bytes": path.stat().st_size}


def checked_file(path: Path, expected: str, size: int | None = None) -> dict:
    record = file_record(path)
    require(record["sha256"] == expected, "Hash mismatch: " + path.name)
    if size is not None:
        require(record["bytes"] == size, "Size mismatch: " + path.name)
    return record


def context_prefixes(tokenizer_path: Path, items: list[dict]) -> dict[str, str]:
    """Decode the exact captured IDs, retaining special tokens and whitespace.

    Input IDs remain authoritative: a 256-token window can begin inside a UTF-8
    byte sequence, so decode/encode round-trip equality is not assumed or forced.
    The tokenizer file is hash-checked by build_delivery before this is called.
    """
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    return {row["id"]: tokenizer.decode(row["input_ids"], skip_special_tokens=False) for row in items}


def exclusion_records(args, *, gate: dict, inputs: dict) -> list[dict]:
    """Copy registered exclusion reasons, without reclassifying any state."""
    excluded = gate["excluded_states"]
    require(len(set(excluded)) == len(excluded) and all(s in STATE_VALUES for s in excluded), "Invalid excluded state list")
    require(set(excluded).isdisjoint(gate["included_states"]), "Included and excluded state sets overlap")
    not_sampled = [s for s in excluded if s not in gate["metrics"]]
    sample_report = None
    if not_sampled:
        sample_manifest = read_json(args.sample_manifest)
        requested = getattr(args, "sample_report", None)
        candidates = ([requested] if requested else [args.sample_manifest.parent / "SAMPLE_REPORT.json",
            args.sample_manifest.parent.parent / "private/SAMPLE_REPORT.json"])
        path = next((p for p in candidates if p.is_file()), None)
        require(path is not None, "A frozen sample report is required for unsampled-state reasons; supply --sample-report")
        inputs["sample_report"] = checked_file(path, sample_manifest["sample_report_sha256"])
        sample_report = read_json(path)
    records = []
    for state in excluded:
        if state in gate["metrics"]:
            row = gate["metrics"][state]
            require(row["test_auroc"] > .65 and row["gate_pass"] is False, "Excluded sampled state did not fail BOW")
            records.append({"state": state, "reason": "BOW_AUROC_EXCEEDS_0_65", "test_auroc": row["test_auroc"],
                            "authority": "BRIEF_UNDERSTAND §191 BOW gate", "source": inputs["gate_report"]})
        else:
            detail = sample_report["states"][state]
            require(isinstance(detail.get("reason"), str) and detail["reason"], "Frozen unsampled-state reason is absent")
            records.append({"state": state, "reason": detail["reason"], "source": inputs["sample_report"]})
    return records


def jlens_asset_card(args, assets: dict) -> dict:
    """Bind an optional existing J checkpoint; never load or build J/null tensors."""
    source = assets["readers"]["jlens"]
    target = assets["target"]
    path = getattr(args, "jlens_file", None)
    local = checked_file(path, source["file_sha256"], source["file_size_bytes"]) if path else None
    return {**{k: source[k] for k in ("repo", "revision", "file", "file_sha256", "file_size_bytes")},
            "forecast_layer": 44, "expected_input_dimension": target["config"]["hidden_size"],
            "file_format": "PyTorch checkpoint (.pt); no deserialization by delivery builder",
            "direction_normalization": "Unit class-mean difference; §169 amendment 1 nonnegative sparse pursuit over rows of W_U @ J_44, k=16",
            "g3_readability_contract": "§169 clarification 1 full-vocabulary value-word ranks; shared-word removal under amendment 1",
            "unembedding_dependency": {"target_id": target["id"], "target_revision": target["revision"],
                                       "weight": "target output embedding W_U", "input_dimension": target["config"]["hidden_size"]},
            "local_file": local,
            "local_file_status": "VERIFIED_HASH_AND_SIZE" if local else "NOT_SUPPLIED_W_LENS_OWNS_LOCAL_CACHE",
            "null_status": "W_LENS_MUST_BIND_EXISTING_OR_NEW_SEALED_200_DIRECTION_NULL_BEFORE_SCORING",
            "null_constructed_by_delivery": False}


def verify_commit_sources(repo: Path, commit: str, files: dict[str, str]) -> str:
    require(isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit), "Producer requires a full commit SHA")
    resolved = subprocess.check_output(["git", "rev-parse", commit + "^{commit}"], cwd=repo, text=True).strip()
    require(resolved == commit, "Producer commit must identify a commit exactly")
    for name, expected in files.items():
        path = PurePosixPath(name)
        require(not path.is_absolute() and ".." not in path.parts, "Unsafe producer source path")
        data = subprocess.check_output(["git", "show", commit + ":" + name], cwd=repo)
        require(hashlib.sha256(data).hexdigest() == expected, "Producer commit/source mismatch: " + name)
    return commit


def safe_seal(directory: Path, name: str, kind: str) -> dict:
    """Reject outcome paths before verify_seal opens/hashes any declared member."""
    value = read_json(directory / name)
    require(value.get("schema") == "e73-seal-v1" and isinstance(value.get("files"), dict), "Unsupported seal")
    require(value.get("status") == "COMPLETE" and value.get("track") == "C", "Incomplete or wrong-track seal")
    for member in value["files"]:
        if kind == "capture":
            allowed = member in CAPTURE_MEMBERS or re.fullmatch(r"capture-[0-9]{5}\.npz", member)
        elif kind == "probe":
            allowed = member == "PROBE_REPORT.json" or re.fullmatch(r"W[1-8]_probe\.npz", member)
        else:
            raise ValueError("Unknown seal kind")
        require(bool(allowed), "Forbidden seal member; native outcomes must never be opened")
    return verify_seal(directory, name)


def validate_private_bank(items: list[dict], labels: list[dict], included: list[str]) -> dict:
    validate_public(items)
    require(included and len(set(included)) == len(included) and all(s in STATE_VALUES for s in included), "Invalid included state list")
    public = {r["id"] for r in items}
    private = {r["id"] for r in labels}
    require(len(public) == len(items) == len(private) == len(labels) and public == private, "ID coverage differs")
    require(set(r["state"] for r in labels) == set(included), "Private map contains excluded/missing states")
    counts, documents = Counter(), Counter()
    by_state = defaultdict(list)
    for row in labels:
        require(row["split"] in ("dev", "test") and type(row["label"]) is int and row["label"] in (0, 1), "Invalid split/label")
        require(type(row["reader_selected"]) is bool, "Invalid reader-selection flag")
        require(re.fullmatch(r"[0-9a-f]{64}", row["doc_hash"]), "Invalid document hash")
        expected_split = "dev" if int(row["doc_hash"], 16) < 2**255 else "test"
        require(row["split"] == expected_split, "Document split leaked or changed")
        documents[row["doc_hash"]] += 1
        counts[row["state"], row["split"], row["label"]] += 1
        by_state[row["state"]].append(row)
    require(max(documents.values()) <= 2, "Global document cap exceeded")
    for state, rows in by_state.items():
        for split in ("dev", "test"):
            a, b = counts[state, split, 0], counts[state, split, 1]
            require(a == b and (100 if state == "W8" else 400) <= a + b <= 400, "Incomplete/unbalanced state")
        require(counts[state, "dev", 0] == counts[state, "test", 0], "Dev/test n differs")
        tests = sorted((r for r in rows if r["split"] == "test"), key=lambda r: r["id"])
        require(all(r["reader_selected"] == (i < 200) for i, r in enumerate(tests)), "First-200 test selection differs")
        require(not any(r["reader_selected"] for r in rows if r["split"] == "dev"), "Dev position assigned to readers")
    return dict(by_state)


def capture_index(directories, *, bank_digest, public_index, capture_commit, sampler_commit, repo):
    import numpy as np
    locations, read_vectors, receipts = {}, {}, []
    for directory in directories:
        metadata = safe_seal(directory, "CAPTURE_SEAL.json", "capture")
        require(metadata.get("bank_manifest_sha256") == bank_digest, "Capture belongs to another bank")
        require(CAPTURE_MEMBERS <= metadata["files"].keys(), "Capture seal omits metadata")
        report = read_json(directory / "CAPTURE_REPORT.json")
        require(read_json(directory / "MODEL_READY.json").get("status") == "MODEL_READY", "Capture model readiness not sealed")
        require(report.get("schema") == "e73-capture-report-v1" and report.get("status") == "COMPLETE", "Wrong capture report")
        require(report.get("reader_outputs") == 0 and report.get("labels_present") is False, "Capture contains reader outputs or labels")
        require(report.get("bank_manifest_sha256") == bank_digest and report.get("sampler_commit") == sampler_commit, "Capture report provenance differs")
        require(report.get("dtype") == "float16", "Wrong capture dtype")
        admission = read_json(directory / "ADMISSION.json")
        require(admission.get("authorized_by") == "I-2" and admission.get("track") == "C", "Missing I-2 capture custody")
        require(admission.get("bank_manifest_sha256") == bank_digest and admission.get("sampler_commit") == sampler_commit, "Admission belongs to another bank")
        sources = admission.get("source_files", {})
        require("projects/g_agreement/e73/capture.py" in sources, "Admission omits capture source")
        verify_commit_sources(repo, capture_commit, sources)
        ordered_ids, files = [], []
        for name in sorted(metadata["files"]):
            if not name.endswith(".npz"):
                continue
            path = directory / name
            require(path.stat().st_size <= MAX_ARCHIVE_BYTES, "Capture shard exceeds registered archive size")
            with np.load(path, allow_pickle=False) as data:
                require(set(data.files) == {"ids", "block44", "block42"}, "Unexpected capture array")
                ids, a44, a42 = data["ids"].tolist(), data["block44"], data["block42"]
                require(1 <= len(ids) <= 7, "Capture shard has unexpected batch size")
                require(a44.shape == (len(ids), 256, 5120) and a42.shape == (len(ids), 5120), "Capture dimensions differ")
                require(a44.dtype == np.float16 and a42.dtype == np.float16, "Capture must preserve raw fp16 arrays")
                require(np.isfinite(a44).all() and np.isfinite(a42).all(), "Nonfinite capture")
                for i, uid in enumerate(ids):
                    require(uid in public_index and uid not in locations, "Unknown or repeated captured ID")
                    locations[uid] = {"path": str(path.resolve()), "row_index": i, "block44_array": "block44",
                                      "all_position_slice": [0, 256], "first_content_index": 0,
                                      "read_position_index": 255, "block42_array": "block42"}
                    read_vectors[uid] = a44[i, 255].copy(), a42[i].copy()
                ordered_ids.extend(ids)
            files.append({"path": str(path.resolve()), **metadata["files"][name], "count": len(ids)})
        require(report.get("completed") == report.get("total") == len(ordered_ids), "Capture counts differ")
        payload = ("\n".join(json.dumps(public_index[uid], separators=(",", ":")) for uid in ordered_ids) + "\n").encode()
        expected_input = hashlib.sha256(payload).hexdigest()
        require(expected_input == metadata.get("input_sha256") == report.get("input_sha256") == admission.get("input_sha256"), "Captured ID order/input hash differs")
        receipts.append({"seal": file_record(directory / "CAPTURE_SEAL.json"),
                         "report": file_record(directory / "CAPTURE_REPORT.json"),
                         "admission": file_record(directory / "ADMISSION.json"),
                         "model_ready": file_record(directory / "MODEL_READY.json"),
                         "input_sha256": expected_input, "items": len(ordered_ids), "files": files})
    require(set(locations) == set(public_index), "Capture inventory does not cover the entire gated bank")
    return locations, read_vectors, receipts


def build_delivery(args) -> dict:
    import numpy as np
    require(args.attest_no_native_generation is True and args.attest_reader_outputs_unopened is True,
            "Explicit operator custody attestations are required")
    manifest_path, labels_path = args.bank / "public/MANIFEST.json", args.bank / "private/labels.jsonl"
    gate_path, items_path = args.bank / "GATE_REPORT.json", args.bank / "public/items.jsonl"
    manifest, gate = read_json(manifest_path), read_json(gate_path)
    require(manifest.get("stage") == gate.get("status") == "BOW_GATE_SEALED", "Bank has not passed the frozen BOW stage")
    require(set(manifest["code_sha256"]) == {"states.py", "sources.py", "sample.py", "bow.py"}, "Sampler source bindings incomplete")
    inputs = {"bank_manifest": file_record(manifest_path),
              "items": checked_file(items_path, manifest["items_sha256"]),
              "private_labels": checked_file(labels_path, manifest["private_labels_sha256"]),
              "gate_report": checked_file(gate_path, manifest["gate_report_sha256"]),
              "sample_manifest": checked_file(args.sample_manifest, manifest["sample_manifest_sha256"]),
              "source_manifest": checked_file(args.source_manifest, manifest["source_manifest_sha256"]),
              "tokenizer": checked_file(args.tokenizer, manifest["tokenizer_sha256"])}
    bank_digest = inputs["bank_manifest"]["sha256"]
    require(gate.get("retained_private_labels_sha256") == manifest["private_labels_sha256"], "Gate/label binding differs")
    validate_gate(gate)
    exclusions = exclusion_records(args, gate=gate, inputs=inputs)
    items, labels = read_jsonl(items_path), read_jsonl(labels_path)
    require(manifest.get("items") == len(items), "Manifest item count differs")
    by_state = validate_private_bank(items, labels, gate["included_states"])
    public_index = {r["id"]: r for r in items}
    source_files = []
    source_manifest = read_json(args.source_manifest)
    require(source_manifest.get("anonymous") is True and source_manifest.get("complete") is True, "Incomplete or nonanonymous source manifest")
    for row in source_manifest["files"]:
        relative = PurePosixPath(row["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe source file path")
        source_files.append({"repo": row["repo"], "revision": row["revision"],
                             **checked_file(args.source_manifest.parent / row["path"], row["sha256"], row["bytes"])})
    title_path = args.repo / "projects/g_agreement/e73/sports_science_titles.json"
    inputs["title_lists"] = checked_file(title_path, manifest["title_lists_sha256"])
    sampler_sources = {"projects/g_agreement/e73/" + name: digest for name, digest in manifest["code_sha256"].items()}
    sampler_sources["projects/g_agreement/e73/sports_science_titles.json"] = manifest["title_lists_sha256"]
    verify_commit_sources(args.repo, args.sampler_commit, sampler_sources)
    # Property values are imported from the same committed/hash-bound extractor.
    checked_file(Path(__file__).with_name("states.py"), manifest["code_sha256"]["states.py"])
    assets = read_json(args.repo / "projects/g_agreement/manifest/assets.json")
    require(assets["target"]["files_needed"]["tokenizer.json_sha256"] == manifest["tokenizer_sha256"], "Tokenizer is not the pinned target asset")
    prefixes = context_prefixes(args.tokenizer, items)
    locations, read_vectors, captures = capture_index(args.capture, bank_digest=bank_digest,
        public_index=public_index, capture_commit=args.capture_commit, sampler_commit=args.sampler_commit, repo=args.repo)
    pseal = safe_seal(args.probes, "PROBE_SEAL.json", "probe")
    require(pseal.get("cpu_private") is True and "PROBE_REPORT.json" in pseal["files"], "Probe seal is not a CPU-private report")
    probe_report = read_json(args.probes / "PROBE_REPORT.json")
    require(probe_report.get("schema") == "e73-probe-report-v1" and probe_report.get("track") == "C", "Wrong probe report")
    require(probe_report.get("estimator") == PROBE_ESTIMATOR, "Probe estimator differs from frozen dev-only fit")
    require(probe_report.get("readers") == "NOT_RUN" and probe_report.get("jforecast") == "PENDING_W_LENS_COMMIT", "Probe-stage custody is not pre-reader/pre-forecast")
    for name, expected in (("bank_manifest_sha256", bank_digest), ("gate_report_sha256", inputs["gate_report"]["sha256"]),
                           ("private_labels_sha256", inputs["private_labels"]["sha256"])):
        require(probe_report.get(name) == expected, "Probe input binding differs: " + name)
    expected_seals = sorted(c["seal"]["sha256"] for c in captures)
    require(sorted(c["seal_sha256"] for c in probe_report["capture_seals"]) == expected_seals, "Probe capture inventory differs")
    verify_commit_sources(args.repo, args.probe_commit, {"projects/g_agreement/e73/probes.py": probe_report["probe_source_sha256"]})
    require(len(probe_report["rows"]) == len(by_state) and {r["state"] for r in probe_report["rows"]} == set(by_state), "Probe rows differ from gated bank")
    require(set(pseal["files"]) == {"PROBE_REPORT.json"} | {s + "_probe.npz" for s in by_state}, "Probe seal has missing or extra state files")
    states, position_rows = [], []
    for summary in probe_report["rows"]:
        state = summary["state"]
        rows = sorted(by_state[state], key=lambda r: r["id"])
        dev, test = [[r for r in rows if r["split"] == split] for split in ("dev", "test")]
        reader_ids = [r["id"] for r in test if r["reader_selected"]]
        require((summary["dev_count"], summary["test_count"], summary["reader_count"]) == (len(dev), len(test), len(reader_ids)), "Probe report count differs")
        require(isinstance(summary["test_auroc"], (int, float)) and math.isfinite(summary["test_auroc"]) and 0 <= summary["test_auroc"] <= 1, "Invalid probe AUROC")
        require(summary["probe_pass"] == (summary["test_auroc"] >= .90), "Probe gate differs from AUROC")
        path = args.probes / (state + "_probe.npz")
        with np.load(path, allow_pickle=False) as data:
            require(set(data.files) == PROBE_ARRAYS, "Unexpected probe array")
            require(data["test_ids"].tolist() == [r["id"] for r in test] and data["test_labels"].tolist() == [r["label"] for r in test], "Probe test order/labels differ")
            require(data["reader_ids"].tolist() == reader_ids, "Probe reader selection differs")
            for name in ("direction", "scaler_mean", "scaler_scale", "dev_mean_A", "dev_mean_B", "test_mean_A", "test_mean_B"):
                require(data[name].shape == (5120,) and np.isfinite(data[name]).all(), "Invalid probe direction/means")
            require(data["intercept"].shape == () and np.isfinite(data["intercept"]).all() and (data["scaler_scale"] > 0).all(), "Invalid probe intercept/scaling")
            require(data["test_block44"].shape == data["test_block42"].shape == (len(test), 5120), "Invalid probe read-token vectors")
            require(data["test_scores"].shape == (len(test),) and np.isfinite(data["test_scores"]).all(), "Invalid probe test scores")
            for i, row in enumerate(test):
                a44, a42 = read_vectors[row["id"]]
                require(np.array_equal(data["test_block44"][i], a44) and np.array_equal(data["test_block42"][i], a42), "Probe read-token vector differs from source capture")
            for split_name, split_rows in (("dev", dev), ("test", test)):
                for label, suffix in ((0, "A"), (1, "B")):
                    expected = np.stack([read_vectors[r["id"]][0].astype(np.float32) for r in split_rows if r["label"] == label]).mean(axis=0)
                    require(np.array_equal(data[split_name + "_mean_" + suffix], expected), "Probe class mean differs from source capture")
        record = file_record(path)
        states.append({"state": state, "property": PROPERTIES[state], "A": STATE_VALUES[state][0], "B": STATE_VALUES[state][1],
                       "bow": {**gate["metrics"][state], "exempt": state in gate.get("bow_exempt_states", [])},
                       "label_encoding": {"A": 0, "B": 1}, "dev_ids": [r["id"] for r in dev], "test_ids": [r["id"] for r in test],
                       "reader_ids": reader_ids, "dev_labels": [r["label"] for r in dev], "test_labels": [r["label"] for r in test],
                       "probe": {**record, "test_auroc": summary["test_auroc"], "probe_pass": summary["probe_pass"],
                                 "direction_array": "direction", "class_mean_arrays": {"dev": ["dev_mean_A", "dev_mean_B"], "test": ["test_mean_A", "test_mean_B"]},
                                 "test_read_vector_arrays": {"44": "test_block44", "42": "test_block42"}}})
        test_index = {r["id"]: i for i, r in enumerate(test)}
        for row in rows:
            position_rows.append({"id": row["id"], "state": state, "split": row["split"], "label": row["label"],
                                  "reader_selected": row["reader_selected"], "input_ids": public_index[row["id"]]["input_ids"],
                                  "read_prefix": prefixes[row["id"]], "read_prefix_kind": "tokenizer_decode_of_exact_256_input_ids",
                                  "first_content_index": 0, "read_index": 255,
                                  "all_position_indices_inclusive": [0, 255], "capture": locations[row["id"]],
                                  "test_probe_vector": {"path": record["path"], "row_index": test_index[row["id"]], "block44_array": "test_block44", "block42_array": "test_block42"} if row["split"] == "test" else None})
    return {"schema": "e73-wlens-delivery-v1", "experiment": "E73", "track": "C", "cpu_private_only": True,
            "created_at_utc": datetime.now(timezone.utc).isoformat(), "producer_commits": {"sampler": args.sampler_commit, "capture": args.capture_commit, "probes": args.probe_commit},
            "inputs": inputs, "sources": source_files, "captures": captures,
            "probes": {"seal": file_record(args.probes / "PROBE_SEAL.json"), "report": file_record(args.probes / "PROBE_REPORT.json"), "producer_source_sha256": probe_report["probe_source_sha256"], "estimator": probe_report["estimator"]},
            "assets_manifest": file_record(args.repo / "projects/g_agreement/manifest/assets.json"),
            "pinned_assets": {"target": {k: assets["target"][k] for k in ("id", "revision", "dtype", "config", "files_needed")},
                              "tokenizer": {"id": assets["target"]["id"], "revision": assets["target"]["revision"],
                                            "file": inputs["tokenizer"], "decode_skip_special_tokens": False},
                              "jlens": jlens_asset_card(args, assets),
                              "capture_site": {"block44": "decoder block output; all context positions 0..255", "block42": "decoder block output; position 255", "chat_template": None}},
            "states": states, "included_states": sorted(by_state), "excluded_states": gate["excluded_states"], "exclusions": exclusions,
            "probe_eligible_states": sorted(s["state"] for s in states if s["probe"]["probe_pass"]),
            "probe_exclusions": [{"state": s["state"], "reason": "PROBE_AUROC_BELOW_0_90", "test_auroc": s["probe"]["test_auroc"]}
                                 for s in states if not s["probe"]["probe_pass"]],
            "positions": sorted(position_rows, key=lambda r: r["id"]), "total_positions": len(position_rows),
            "jforecast": "PENDING_W_LENS_COMMIT", "g3_value_token_sets": "NOT_CONSTRUCTED_W_LENS_OWNS_FREEZE",
            "custody": {"operator_attestation": {"native_generation_started": False, "reader_outputs_opened": False},
                        "attestation_scope": "This receipt's bank and positions; other separately sealed banks are outside scope",
                        "reader_release": "HELD_FOR_IMMUTABLE_W_LENS_FORECAST_COMMIT_AND_I2_GO",
                        "sealed_capture_reader_outputs": 0, "sealed_probe_readers_status": "NOT_RUN", "reader_outcome_files_opened_by_builder": 0,
                        "note": "Custody for the supplied bank is an explicit operator attestation, checked alongside sealed stage records; no native outcome paths are accepted."},
            "delivery_builder": file_record(Path(__file__))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bank", "probes", "source-manifest", "sample-manifest", "tokenizer", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--sample-report", type=Path, help="Frozen SAMPLE_REPORT.json for unsampled-state reasons")
    parser.add_argument("--jlens-file", type=Path, help="Optional existing J checkpoint; verify pinned file hash and size only")
    parser.add_argument("--capture", type=Path, nargs="+", required=True)
    for name in ("sampler-commit", "capture-commit", "probe-commit"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--attest-no-native-generation", action="store_true", required=True)
    parser.add_argument("--attest-reader-outputs-unopened", action="store_true", required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "Delivery receipt is immutable; use a new output path")
    result = build_delivery(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        handle.write(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps({"status": "W_LENS_DELIVERY_SEALED", "receipt": file_record(args.out), "positions": result["total_positions"]}))


if __name__ == "__main__":
    main()
