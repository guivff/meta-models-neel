"""CPU-only, no-extraction preflight of the exact E73 capture upload archive.

Inputs are a gzip tar produced by custody.archive_inputs, the committed public
bank-manifest bytes, and independently prepared source-file hashes. Optional I-2
admission is checked but never created here. Passing this check is not a GO.

Only opaque IDs/token IDs, hash-only provenance manifests, and the enumerated
runtime Python files can enter a pod. Labels, split/state maps, corpus files,
sampling code, test fixtures, and BOW reports are never archive members. Hashes
named private_labels_sha256 / gate_report_sha256 are allowed provenance, not
label or gate data. Python files are compiled without executing or importing.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path, PurePosixPath

from .custody import MAX_ARCHIVE_BYTES, SHA_RE, check_admission, sha256, validate_public

MAX_UNCOMPRESSED_BYTES = 40_000_000
CAPTURE_SOURCES = frozenset({
    "projects/g_agreement/e73/capture.py",
    "projects/g_agreement/e73/custody.py",
    "projects/g_agreement/core/model.py",
    "projects/g_agreement/core/config.py",
    "projects/g_agreement/core/accounting.py",
})
NATIVE_SOURCES = frozenset({
    "projects/g_agreement/e73/native.py",
    "projects/g_agreement/e73/custody.py",
    "projects/g_agreement/core/model.py",
    "projects/g_agreement/core/config.py",
    "projects/g_agreement/core/readers.py",
    "projects/g_agreement/core/generate.py",
    "projects/g_agreement/core/accounting.py",
})
PACKAGE_SOURCES = frozenset({
    "projects/__init__.py", "projects/g_agreement/__init__.py",
    "projects/g_agreement/e73/__init__.py", "projects/g_agreement/core/__init__.py",
})
ALLOWED_SOURCES = CAPTURE_SOURCES | NATIVE_SOURCES | PACKAGE_SOURCES
DATA_MEMBERS = frozenset({"inputs/items.jsonl", "inputs/MANIFEST.json", "inputs/BANK_MANIFEST.json"})
BANK_HASH_FIELDS = frozenset({
    "items_sha256", "private_labels_sha256", "gate_report_sha256",
    "sample_manifest_sha256", "source_manifest_sha256", "tokenizer_sha256",
    "title_lists_sha256",
})
BANK_FIELDS = BANK_HASH_FIELDS | {"experiment", "stage", "items", "context_tokens", "input_schema", "code_sha256"}
SAMPLER_HASH_NAMES = frozenset({"sources.py", "states.py", "sample.py", "bow.py"})


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _json(content: bytes):
    def reject_constant(_):
        raise ValueError("nonfinite JSON constant")
    return json.loads(content.decode("utf-8"), object_pairs_hook=_object, parse_constant=reject_constant)


def _sha(value) -> bool:
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def validate_bank_manifest(value: dict) -> None:
    """Exact public BOW-sealed metadata schema: no names or values of states."""
    if not isinstance(value, dict) or set(value) != BANK_FIELDS:
        raise ValueError("bank manifest must contain only the frozen hash-only public schema")
    if value["experiment"] != "E73" or value["stage"] != "BOW_GATE_SEALED":
        raise ValueError("capture requires the E73 BOW-sealed bank")
    if type(value["items"]) is not int or value["items"] < 1:
        raise ValueError("bank manifest has no capture items")
    if type(value["context_tokens"]) is not int or value["context_tokens"] != 256 or value["input_schema"] != ["id", "input_ids"]:
        raise ValueError("bank manifest context/schema differs")
    if any(not _sha(value[name]) for name in BANK_HASH_FIELDS):
        raise ValueError("provenance fields must be SHA-256 hashes, never data")
    code = value["code_sha256"]
    if not isinstance(code, dict) or set(code) != SAMPLER_HASH_NAMES or any(not _sha(v) for v in code.values()):
        raise ValueError("sampler provenance must be an explicit hash-only map")


def _members(archive: bytes) -> tuple[dict[str, bytes], int]:
    """Bound decompression and inspect every tar member; never extract to disk."""
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(archive), mode="rb") as stream:
            unpacked = stream.read(MAX_UNCOMPRESSED_BYTES + 1)
    except (OSError, EOFError) as exc:
        raise ValueError("archive is not a complete gzip stream") from exc
    if len(unpacked) > MAX_UNCOMPRESSED_BYTES:
        raise ValueError("archive exceeds bounded uncompressed size")
    result = {}
    expected_offset = 0
    try:
        # ignore_zeros scans concatenated tar streams instead of ignoring a
        # second payload hidden after a conventional end-of-archive marker.
        with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:", ignore_zeros=True) as tar:
            for member in tar:
                name = member.name
                path = PurePosixPath(name)
                if (not name or "\\" in name or ":" in name or path.is_absolute()
                        or ".." in path.parts or name != path.as_posix() or name.startswith("./")):
                    raise ValueError("unsafe archive path")
                if not member.isfile() or member.issym() or member.islnk() or member.sparse or member.pax_headers:
                    raise ValueError("only ordinary archive files are allowed")
                if name not in DATA_MEMBERS | ALLOWED_SOURCES:
                    raise ValueError("unapproved archive member")
                if name in result:
                    raise ValueError("duplicate archive member")
                if member.offset != expected_offset or member.offset_data != member.offset + 512:
                    raise ValueError("archive has hidden, extended, or noncanonical headers")
                if not 0 <= member.size <= MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("invalid archive member size")
                content = tar.extractfile(member).read(member.size + 1)
                if len(content) != member.size:
                    raise ValueError("truncated archive member")
                result[name] = content
                expected_offset = member.offset_data + ((member.size + 511) // 512) * 512
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise ValueError("invalid tar archive") from exc
    if not result or any(unpacked[expected_offset:]):
        raise ValueError("archive has an empty or nonzero trailing payload")
    if not DATA_MEMBERS <= result.keys():
        raise ValueError("archive is missing a required public input member")
    return result, len(unpacked)


def validate_archive(archive: Path, *, bank_manifest: Path, source_hashes: dict[str, str],
                     expected_archive_sha256: str, admission: dict | None = None,
                     bank_inputs: Path | None = None) -> dict:
    """Verify one immutable upload and return a safe metadata-only report.

    source_hashes must be prepared from the intended committed runtime source,
    not learned from the archive being checked. The expected archive hash comes
    from SHARDS.json. Admission may be absent while preparing I-2's review packet.
    """
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("archive must be an ordinary file")
    archive_size = archive.stat().st_size
    if archive_size > MAX_ARCHIVE_BYTES:
        raise ValueError("upload archive exceeds 20 MB")
    raw = archive.read_bytes()
    if not _sha(expected_archive_sha256) or _digest(raw) != expected_archive_sha256:
        raise ValueError("exact upload archive hash mismatch")
    if not isinstance(source_hashes, dict) or not CAPTURE_SOURCES <= source_hashes.keys():
        raise ValueError("missing required capture source hashes")
    if not source_hashes.keys() <= ALLOWED_SOURCES or any(not _sha(v) for v in source_hashes.values()):
        raise ValueError("source hashes contain an unapproved source or invalid digest")
    if "projects/g_agreement/e73/native.py" in source_hashes and not NATIVE_SOURCES <= source_hashes.keys():
        raise ValueError("native source staged without its explicit dependencies")
    content, expanded_size = _members(raw)
    staged_sources = content.keys() - DATA_MEMBERS
    if staged_sources != source_hashes.keys():
        raise ValueError("archive sources differ from independently supplied allowlist")
    for name in sorted(staged_sources):
        if _digest(content[name]) != source_hashes[name]:
            raise ValueError("staged source hash mismatch")
        try:
            compile(content[name], name, "exec", dont_inherit=True)
        except (SyntaxError, ValueError) as exc:
            raise ValueError("staged Python source does not compile") from exc
    bank_bytes = bank_manifest.read_bytes()
    bank_hash = _digest(bank_bytes)
    if content["inputs/BANK_MANIFEST.json"] != bank_bytes:
        raise ValueError("staged bank manifest differs from frozen public bank")
    bank_value = _json(bank_bytes)
    validate_bank_manifest(bank_value)
    shard = _json(content["inputs/MANIFEST.json"])
    if not isinstance(shard, dict) or set(shard) != {"schema", "bank_manifest_sha256", "input_sha256", "count"}:
        raise ValueError("shard manifest has unexpected fields")
    inputs_hash = _digest(content["inputs/items.jsonl"])
    if (shard["schema"] != "e73-shard-v1" or shard["bank_manifest_sha256"] != bank_hash
            or shard["input_sha256"] != inputs_hash):
        raise ValueError("shard input/bank manifest binding mismatch")
    rows = [_json(line) for line in content["inputs/items.jsonl"].splitlines() if line.strip()]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("shard must contain public object records")
    validate_public(rows)
    if type(shard["count"]) is not int or shard["count"] != len(rows) or len(rows) > bank_value["items"]:
        raise ValueError("shard count is invalid")
    # CPU-side comparison to the whole frozen public bank ensures a well-formed
    # archive cannot substitute different token IDs while merely citing its hash.
    bank_inputs = bank_inputs or bank_manifest.with_name("items.jsonl")
    bank_input_bytes = bank_inputs.read_bytes()
    if _digest(bank_input_bytes) != bank_value["items_sha256"]:
        raise ValueError("CPU public bank differs from frozen input hash")
    bank_rows = [_json(line) for line in bank_input_bytes.splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in bank_rows):
        raise ValueError("CPU public bank must contain object records")
    validate_public(bank_rows)
    if len(bank_rows) != bank_value["items"]:
        raise ValueError("CPU public bank count differs from manifest")
    bank_index = {row["id"]: row for row in bank_rows}
    if any(bank_index.get(row["id"]) != row for row in rows):
        raise ValueError("shard records differ from the frozen public bank")
    if admission is not None:
        check_admission(admission, inputs_hash, bank_hash)
        if admission["source_files"] != source_hashes:
            raise ValueError("admission source map differs from exact archive")
    return {"schema": "e73-preflight-v1", "status": "PREFLIGHT_PASS", "track": "C",
            "stage": "capture_inputs", "cpu_only": True, "gpu_libraries_imported": False,
            "archive_sha256": expected_archive_sha256, "archive_bytes": len(raw),
            "uncompressed_bytes": expanded_size, "record_count": len(rows),
            "input_sha256": inputs_hash, "bank_manifest_sha256": bank_hash,
            "shard_manifest_sha256": _digest(content["inputs/MANIFEST.json"]),
            "source_files": dict(sorted(source_hashes.items())), "compiled_sources": len(staged_sources),
            "preflight_source_sha256": sha256(Path(__file__)),
            "custody_source_sha256": sha256(Path(__file__).with_name("custody.py")),
            "admission_checked": admission is not None, "grants_admission_or_go": False}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "bank-manifest", "source-hashes", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--expected-archive-sha256", required=True)
    p.add_argument("--admission", type=Path)
    p.add_argument("--bank-inputs", type=Path, help="CPU full public bank; defaults to items.jsonl beside bank manifest")
    args = p.parse_args()
    report = validate_archive(args.archive, bank_manifest=args.bank_manifest,
                              source_hashes=_json(args.source_hashes.read_bytes()),
                              expected_archive_sha256=args.expected_archive_sha256,
                              admission=_json(args.admission.read_bytes()) if args.admission else None,
                              bank_inputs=args.bank_inputs)
    report["source_hashes_file_sha256"] = sha256(args.source_hashes)
    if args.admission:
        report["admission_file_sha256"] = sha256(args.admission)
    # Exclusive output prevents accidentally replacing the exact-archive check.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as f:
        json.dump(report, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
    print(json.dumps({k: report[k] for k in ("status", "archive_sha256", "record_count", "admission_checked")}))


if __name__ == "__main__":
    main()
