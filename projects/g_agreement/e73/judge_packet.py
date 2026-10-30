"""CPU-only E73 export to the frozen E56 blind packet and rendered wire formats.

No API client, judge dispatch, metric, or scientific verdict is implemented here.
The original five-state bank and the separate clarification-4 W7/W8 supplement
each contribute their frozen first 200 test IDs/state, regardless of probe score.
Export opens outcomes only after every native
shard has a COMPLETE seal and matching bank/index/GO/committed-forecast bindings.
The output is for the CPU judge route; it must never be staged to a reader pod.

The historical E56 runner does not admit E73 or its separate USD5 allocation.
I-2 must bind a dispatch wrapper to that existing model/provider/privacy/retry
route and E73 authorization; these files are compatible inputs, not a dispatch
authorization. R-W1 verdict scope remains outside this adapter.

CLI: --spec PATH, whose keys are repo, adapter_commit, bank_manifest, items, labels, gate,
reader_index, reader_input_seal_sha256, go, forecast_proof, forecast_repo,
forecast_path, native (list of {path, seal_sha256}), out, private_key.
All paths are absolute. private_key must be outside out and stays CPU-private.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

from .custody import check_go, forecast_proof, read_jsonl, sha256
from .delivery import PROPERTIES, validate_gate, validate_private_bank, verify_commit_sources
from .preflight import NATIVE_SOURCES, PACKAGE_SOURCES, validate_bank_manifest
from .prepare_native import (checked_seal, decode_json, read_file, require,
                             validate_index, validate_residual_bytes)
from .states import STATE_VALUES

REPO = Path(__file__).resolve().parents[3]
RUBRIC_COMMIT = "769ea9e16a9dd1f9ab6bd1e14b1b6ea81e0f4531"
RUBRIC_PATH = "results/g_agreement/understand/e56/job/JUDGE_RUBRIC.md"
RUBRIC_SHA256 = "03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613"
RENDER_COMMIT = "c3b4f1abce9d315ee7b07b5640e7589c1ffe934c"
RENDER_PATH = "projects/g_agreement/understand/blind_judge/judgment_adapter402.py"
SUFFIX = "\n\nProperty: {property}\nA: {A}\nB: {B}\n"
STATES = ("W1", "W2", "W3", "W4", "W5")
READERS = ("oracle", "nla")
CONTROL_MANIFEST = "ef8dbcb153e5e3f6720d6666c9859f97df1cbde97408ae3d95ba843698035f37"
NATIVE_MEMBERS = {"oracle.jsonl", "nla.jsonl", "READER_REPORT.json", "ADMISSION.json",
                  "GO.json", "MODEL_READY_oracle.json", "MODEL_READY_nla.json"}
OUTPUT_FIELDS = {"id", "raw_output", "new_token_ids", "n_new_tokens", "reader", "capture_layer",
                 "max_new_tokens", "greedy", "finish_reason", "explanation_closed", "truncated"}
SHA = re.compile(r"[0-9a-f]{64}\Z")
ADAPTER_SOURCES = {"projects/g_agreement/e73/" + name for name in
                   ("judge_packet.py", "custody.py", "delivery.py", "preflight.py", "prepare_native.py", "states.py")}


def read(path):
    return decode_json(read_file(Path(path)))


def git_bytes(repo, commit, path):
    return subprocess.run(["git", "show", commit + ":" + path], cwd=repo, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def frozen_rubric(repo):
    content = git_bytes(repo, RUBRIC_COMMIT, RUBRIC_PATH)
    require(hashlib.sha256(content).hexdigest() == RUBRIC_SHA256, "Frozen E56 rubric hash differs")
    return content.decode("utf-8")


def adapter_source_receipt(repo, commit):
    """The exact CPU exporter and its local validation helpers must be committed."""
    sources = {name: sha256(REPO / name) for name in sorted(ADAPTER_SOURCES)}
    verify_commit_sources(repo, commit, sources)
    return {"commit": commit, "source_files": sources}


def render_record(record, rubric):
    """Exact c3b4f1ab render_record layout; correctness never affects value order."""
    require(set(record) == {"id", "property", "values", "readout"}, "Source packet schema")
    require(isinstance(record["property"], str) and isinstance(record["values"], dict)
            and set(record["values"]) == {"A", "B"}
            and all(isinstance(record["values"][k], str) for k in ("A", "B")), "Frozen property/value strings")
    return {"id": record["id"], "readout": record["readout"], "rubric": rubric +
            SUFFIX.format(property=record["property"], A=record["values"]["A"], B=record["values"]["B"])}


def native_text(record, reader):
    """E56 extract_explanation: first complete tag pair, stripped, else whole raw."""
    require(set(record) == OUTPUT_FIELDS and record["reader"] == reader, "Native record schema/reader differs")
    raw = record["raw_output"]
    require(isinstance(raw, str), "Native output must preserve a string, including empty output")
    cap, layer = (128, 44) if reader == "oracle" else (512, 42)
    require(record["greedy"] is True and record["max_new_tokens"] == cap and record["capture_layer"] == layer,
            "Native registered readout settings differ")
    tokens = record["new_token_ids"]
    require(isinstance(tokens, list) and all(type(x) is int and x >= 0 for x in tokens)
            and type(record["n_new_tokens"]) is int and record["n_new_tokens"] == len(tokens) <= cap,
            "Native token count/cap differs")
    require(isinstance(record["finish_reason"], str), "Missing native finish reason")
    if reader == "oracle":
        require(record["explanation_closed"] is None and record["truncated"] is None, "Unexpected Oracle truncation metadata")
        return raw
    closed = "</explanation>" in raw
    require(record["explanation_closed"] is closed and record["truncated"] is (not closed), "NLA closure metadata differs")
    match = re.search(r"<explanation>(.*?)</explanation>", raw, re.DOTALL)
    return match.group(1).strip() if match else raw


def checked_member(directory, name, seal):
    content = read_file(directory / name)
    metadata = seal["files"][name]
    require(metadata == {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)},
            "Native seal member hash/size mismatch: " + name)
    return content


def prerequisites(spec):
    """Validate metadata for ALL shards before opening/hashing either output file."""
    repo = Path(spec["repo"])
    adapter = adapter_source_receipt(repo, spec["adapter_commit"])
    bank_path = Path(spec["bank_manifest"])
    bank = read(bank_path)
    validate_bank_manifest(bank)
    bank_sha = sha256(bank_path)
    for field, key in (("items", "items_sha256"), ("labels", "private_labels_sha256"), ("gate", "gate_report_sha256")):
        require(sha256(Path(spec[field])) == bank[key], "Bank binding differs: " + field)
    gate = read(spec["gate"])
    controls = gate.get("bow_exempt_states") == ["W7", "W8"]
    states = ("W7", "W8") if controls else STATES
    expected = 200 * len(states)
    if controls:
        validate_gate(gate)
        require(bank_sha == CONTROL_MANIFEST,
                "Frozen control supplement manifest differs")
    require(bank["items"] == (1432 if controls else 4000), "Frozen E73 bank position count differs")
    require(gate["included_states"] == list(states) and set(gate["excluded_states"]) == ({"W6"} if controls else {"W6", "W7", "W8"}),
            "Frozen BOW state inventory differs; never select by probe score")
    items, labels = read_jsonl(Path(spec["items"])), read_jsonl(Path(spec["labels"]))
    validate_private_bank(items, labels, list(states))
    selected = {x["id"]: x for x in labels if x["reader_selected"]}
    require(len(selected) == expected and Counter(x["state"] for x in selected.values()) == Counter({s: 200 for s in states}),
            "Frozen first200 test positions per state required")
    index_path = Path(spec["reader_index"])
    index = read(index_path)
    validate_index(index, bank_sha)
    require(index["total"] == expected, "Frozen reader index count differs")
    require(sha256(index_path.parent / "READER_INPUT_SEAL.json") == spec["reader_input_seal_sha256"], "Reader input seal differs")
    input_seal = checked_seal(index_path.parent, "READER_INPUT_SEAL.json", "reader_inputs")
    require(set(input_seal["files"]) == {"READER_INPUTS.json", *(s["file"] for s in index["shards"])}, "Reader input seal inventory differs")
    require(index_path.name == "READER_INPUTS.json", "Canonical reader index required")
    shards, all_ids = {}, []
    for shard in index["shards"]:
        content = read_file(index_path.parent / shard["file"])
        require(len(content) == shard["bytes"] and hashlib.sha256(content).hexdigest() == shard["sha256"], "Residual shard index differs")
        ids, _ = validate_residual_bytes(content)
        require(len(ids) == shard["count"], "Residual shard count differs")
        require(shard["sha256"] not in shards, "Duplicate residual shard")
        shards[shard["sha256"]] = ids
        all_ids.extend(ids)
    require(len(all_ids) == len(set(all_ids)) == expected and set(all_ids) == set(selected), "Reader input selection differs from private frozen first200")
    go_bytes = read_file(Path(spec["go"]))
    go = decode_json(go_bytes)
    check_go(go, capture_seal_sha=sha256(index_path), input_manifest_sha=bank_sha)
    expected_proof = forecast_proof(Path(spec["forecast_repo"]), go["jforecast_commit"], spec["forecast_path"], go["jforecast_sha256"])
    require(read(spec["forecast_proof"]) == expected_proof, "Committed forecast proof differs from GO")
    rubric = frozen_rubric(repo)
    # These are source files, never judge responses or reader outputs.
    rendering_sha = hashlib.sha256(git_bytes(repo, RENDER_COMMIT, RENDER_PATH)).hexdigest()
    native = spec["native"]
    require(isinstance(native, list) and len(native) == len(shards), "Complete native shard inventory required")
    verified, used, runs = [], set(), set()
    for entry in native:
        require(set(entry) == {"path", "seal_sha256"}, "Native custody entry requires path and expected seal hash")
        directory = Path(entry["path"])
        require(isinstance(entry["seal_sha256"], str) and SHA.fullmatch(entry["seal_sha256"])
                and sha256(directory / "READER_SEAL.json") == entry["seal_sha256"], "Native expected seal hash differs")
        seal = read(directory / "READER_SEAL.json")
        require(seal.get("schema") == "e73-seal-v1" and seal.get("status") == "COMPLETE"
                and seal.get("track") == "C" and seal.get("reader_outputs_unopened") is True, "Native shard is not COMPLETE and sealed")
        require(set(seal["files"]) == NATIVE_MEMBERS, "Incomplete/unexpected native seal inventory")
        for name in NATIVE_MEMBERS - {"oracle.jsonl", "nla.jsonl"}:
            checked_member(directory, name, seal)
        require(checked_member(directory, "GO.json", seal) == go_bytes, "Native GO bytes differ")
        report = read(directory / "READER_REPORT.json")
        admission = read(directory / "ADMISSION.json")
        digest = report.get("input_sha256")
        require(digest in shards and digest not in used, "Missing/duplicate native residual shard")
        ids = shards[digest]
        require(report.get("schema") == "e73-reader-report-v1" and report.get("status") == "COMPLETE"
                and report.get("track") == "C" and report.get("completed") == {r: len(ids) for r in READERS}
                and report.get("total_per_reader") == len(ids), "Native report incomplete")
        require(report.get("reader_index_sha256") == sha256(index_path)
                and report.get("jforecast_commit") == go["jforecast_commit"]
                and report.get("jforecast_sha256") == go["jforecast_sha256"], "Native report index/forecast binding differs")
        require(admission.get("authorized_by") == "I-2" and admission.get("track") == "C"
                and admission.get("input_sha256") == digest and admission.get("bank_manifest_sha256") == bank_sha,
                "Native admission input/bank differs")
        for field in ("run_id", "run_kind", "runtime_commit", "code_sha256"):
            require(report.get(field) == admission.get(field), "Native report/admission operator provenance differs")
        require(admission["run_kind"] == "real" and isinstance(admission["run_id"], str)
                and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", admission["run_id"])
                and admission["run_id"] not in runs, "Invalid/reused native run")
        source_map = admission.get("source_files", {})
        require(NATIVE_SOURCES <= source_map.keys() <= NATIVE_SOURCES | PACKAGE_SOURCES, "Native runtime dependencies differ")
        require(hashlib.sha256(json.dumps(source_map, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                == admission["code_sha256"], "Native canonical source-map digest differs")
        verify_commit_sources(repo, admission["runtime_commit"], source_map)
        used.add(digest)
        runs.add(admission["run_id"])
        verified.append((directory, seal, ids, entry["seal_sha256"]))
    require(used == set(shards), "Native shard coverage incomplete")
    return selected, verified, rubric, {
        "adapter_source": adapter,
        "bank_manifest_sha256": bank_sha, "reader_index_sha256": sha256(index_path),
        "reader_input_seal_sha256": spec["reader_input_seal_sha256"], "private_labels_sha256": bank["private_labels_sha256"],
        "gate_report_sha256": bank["gate_report_sha256"], "source_capture_seals": index["source_capture_seals"],
        "probe_seal_sha256": index["probe_seal_sha256"], "go_sha256": sha256(Path(spec["go"])),
        "forecast_proof": expected_proof, "rubric_commit": RUBRIC_COMMIT, "rubric_sha256": RUBRIC_SHA256,
        "render_commit": RENDER_COMMIT, "render_source_sha256": rendering_sha,
        "native_seals": [{"path": str(p), "sha256": h} for p, _, _, h in verified]}


def export_packet(spec):
    out, private_key = Path(spec["out"]), Path(spec["private_key"])
    require(not out.exists() and not private_key.exists(), "Packet/private key already exists; never overwrite")
    require(not private_key.resolve().is_relative_to(out.resolve()), "Private key must stay outside public packet directory")
    selected, verified, rubric, provenance = prerequisites(spec)
    states = sorted({r["state"] for r in selected.values()})
    total = 2 * len(selected)
    # No native output was opened before every prerequisite above passed.
    records = []
    for directory, seal, ids, _ in verified:
        for reader in READERS:
            content = checked_member(directory, reader + ".jsonl", seal)
            rows = [decode_json(line) for line in content.splitlines()]
            require([x["id"] for x in rows] == ids, "Native output ID order/coverage differs from frozen shard")
            for row in rows:
                label = selected[row["id"]]
                text = native_text(row, reader)
                # Domain-separated opaque IDs/order depend only on frozen IDs, never labels or outcomes.
                opaque = hashlib.sha256(("E73-blind-v1|" + reader + "|" + row["id"]).encode()).hexdigest()[:32]
                state = label["state"]
                public = {"id": opaque, "property": PROPERTIES[state],
                          "values": dict(zip(("A", "B"), STATE_VALUES[state])), "readout": text}
                key = {"opaque_id": opaque, "source_id": row["id"], "reader": reader, "state": state,
                       "label": label["label"], "value": "AB"[label["label"]],
                       "truncated": row["truncated"], "raw_output_sha256": hashlib.sha256(row["raw_output"].encode()).hexdigest()}
                records.append((public, key))
    records.sort(key=lambda pair: pair[0]["id"])
    require(len(records) == len({p["id"] for p, _ in records}) == total, "Complete unique two-reader grid required")
    packet, key = [p for p, _ in records], [k for _, k in records]
    wire = [render_record(p, rubric) for p in packet]
    out.mkdir(parents=True, exist_ok=False)
    private_key.parent.mkdir(parents=True, exist_ok=True)
    def write(path, value):
        with path.open("x") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
        path.chmod(0o600)
    write(out / "JUDGE_PACKET.json", packet)
    write(out / "WIRE_PACKET.json", wire)
    write(private_key, key)
    (out / "JUDGE_RUBRIC.md").write_text(rubric)
    (out / "JUDGE_RUBRIC.md").chmod(0o600)
    write(out / "PROVENANCE.json", {**provenance, "experiment": "E73", "n": total,
        "per_reader_counts": {r: len(selected) for r in READERS}, "per_state_per_reader": {s: 200 for s in states},
        "probe_score_selection": False, "one_blind_judge": True, "api_calls": 0,
        "label_convention": "CPU private map: 0=A, 1=B; no conversion or outcome scoring performed",
        "ordering": "ascending domain-separated SHA256 opaque IDs; independent of labels/readout text",
        "native_text_policy": "§172 clarification3; exact E56 first complete explanation tag pair, stripped, else whole raw",
        "route_status": "E56-compatible packet only; I-2 must bind E73 dispatch/admission and separate <=USD5 ledger",
        "analysis": "NOT_RUN; final R-W1 composition follows clarification 4 and the separate once-only plan", "private_key_sha256": sha256(private_key)})
    # E56 packet/wire seal wire format uses filename -> digest, not e73-seal-v1 member objects.
    blind = {"experiment": "E73", "rubric_sha256": RUBRIC_SHA256,
             "private_key_sha256": sha256(private_key), "reader_index_sha256": provenance["reader_index_sha256"],
             "files": {n: sha256(out / n) for n in ("JUDGE_PACKET.json", "JUDGE_RUBRIC.md", "PROVENANCE.json")}}
    write(out / "BLIND_SEAL.json", blind)
    write(out / "WIRE_SEAL.json", {"experiment": "E73", "blind_seal_sha256": sha256(out / "BLIND_SEAL.json"),
          "render_source_sha256": provenance["render_source_sha256"], "files": {"WIRE_PACKET.json": sha256(out / "WIRE_PACKET.json")}})
    return {"status": "CPU_PACKET_EXPORTED_NO_JUDGING", "n": total, "blind_seal_sha256": sha256(out / "BLIND_SEAL.json"),
            "wire_seal_sha256": sha256(out / "WIRE_SEAL.json"), "private_key_sha256": sha256(private_key)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export_packet(read(args.spec)), sort_keys=True))


if __name__ == "__main__":
    main()
