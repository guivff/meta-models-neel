"""Fail-closed E73 file custody; standard-library-only, safe on the CPU host.

Admission records are written by I-2 after checking shared spend. They are not
created automatically by a worker. No function here grants admission or GO.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import tarfile
import threading
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path

MAX_ARCHIVE_BYTES = 20_000_000
MAX_GPU_SECONDS = 6 * 3600
ID_RE = re.compile(r"[0-9a-f]{32,64}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def validate_public(rows: list[dict]) -> None:
    seen = set()
    for row in rows:
        if set(row) != {"id", "input_ids"}:
            raise ValueError("pod rows must contain only id and input_ids")
        uid = row["id"]
        if not isinstance(uid, str) or not ID_RE.fullmatch(uid) or uid in seen:
            raise ValueError("IDs must be unique opaque hexadecimal strings")
        seen.add(uid)
        ids = row["input_ids"]
        if not isinstance(ids, list) or len(ids) != 256:
            raise ValueError("each context must have exactly 256 tokens")
        if any(type(i) is not int or not 0 <= i < 248320 for i in ids):
            raise ValueError("invalid Qwen token ID")


def seal(directory: Path, filename: str, files: list[Path], **metadata) -> dict:
    path = directory / filename
    if path.exists():
        raise FileExistsError(f"refusing to replace seal: {path}")
    binding = {}
    for f in files:
        relative = f.resolve().relative_to(directory.resolve()).as_posix()
        if f.is_symlink() or not f.is_file():
            raise ValueError("seal requires ordinary files")
        binding[relative] = {"sha256": sha256(f), "bytes": f.stat().st_size}
    value = {"schema": "e73-seal-v1", "files": binding, **metadata}
    write_json(path, value)
    return value


def verify_seal(directory: Path, filename: str) -> dict:
    value = json.loads((directory / filename).read_text())
    if value.get("schema") != "e73-seal-v1":
        raise ValueError("unsupported seal schema")
    for name, entry in value["files"].items():
        p = directory / name
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(directory.resolve()):
            raise ValueError("unsafe seal member")
        if sha256(p) != entry["sha256"] or p.stat().st_size != entry["bytes"]:
            raise ValueError("sealed file changed: " + name)
    return value


def check_admission(admission: dict, inputs_sha: str, manifest_sha: str) -> None:
    required = {"schema", "track", "authorized_by", "sampler_commit", "input_sha256",
                "bank_manifest_sha256", "gpu_count", "gpu_seconds_cap", "prior_track_gpu_seconds",
                "forecast_gpu_seconds", "staging_cap_seconds", "combined_spend_before_usd",
                "launch_spend_cap_usd", "daily_ceiling_usd", "source_files"}
    if not required <= admission.keys():
        raise ValueError("incomplete I-2 admission")
    if admission["schema"] != "e73-admission-v1" or admission["track"] != "C" or admission["authorized_by"] != "I-2":
        raise ValueError("requires Track C I-2 admission")
    if not COMMIT_RE.fullmatch(admission["sampler_commit"]):
        raise ValueError("sampler must have a committed full revision")
    if admission["input_sha256"] != inputs_sha or admission["bank_manifest_sha256"] != manifest_sha:
        raise ValueError("admission is bound to different input files")
    if admission["gpu_count"] != 1 or admission["staging_cap_seconds"] != 900:
        raise ValueError("E73 worker requires one GPU and 900-second staging cap")
    numeric = ("gpu_seconds_cap", "prior_track_gpu_seconds", "forecast_gpu_seconds",
               "combined_spend_before_usd", "launch_spend_cap_usd", "daily_ceiling_usd")
    if any(not isinstance(admission[k], (int, float)) or isinstance(admission[k], bool)
           or not math.isfinite(admission[k]) or admission[k] < 0 for k in numeric):
        raise ValueError("admission accounting must contain finite nonnegative numbers")
    cap, previous, forecast = (admission[k] for k in numeric[:3])
    if cap <= 0 or forecast <= 0 or previous + cap + admission["staging_cap_seconds"] > MAX_GPU_SECONDS or 1.25 * forecast > cap:
        raise ValueError("NO_FIT: forecast or aggregate E73 GPU cap")
    if admission["combined_spend_before_usd"] + admission["launch_spend_cap_usd"] > admission["daily_ceiling_usd"]:
        raise ValueError("NO_FIT: combined daily spend ceiling")
    if not admission["source_files"]:
        raise ValueError("admission must bind executable source files")


def check_source_files(root: Path, source_files: dict) -> None:
    for name, expected in source_files.items():
        p = root / name
        if not p.resolve().is_relative_to(root.resolve()) or p.is_symlink() or sha256(p) != expected:
            raise ValueError("admitted source differs: " + name)


@contextmanager
def hard_deadline(seconds: float, status_path: Path):
    """Independent timer kills this process even during model load/one slow call.

    A timeout intentionally creates no COMPLETE seal. The pod operator must also
    enforce its external wall-clock stop (and terminate billing) independently.
    """
    def timeout():
        write_json(status_path, {"status": "HARD_TIMEOUT", "track": "C", "cap_seconds": seconds})
        os._exit(124)
    timer = threading.Timer(seconds, timeout)
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()


def check_go(go: dict, *, capture_seal_sha: str, input_manifest_sha: str) -> None:
    """Readers need a capture-bound GO citing the committed W-lens forecast."""
    if go.get("schema") != "e73-reader-go-v1" or go.get("authorized_by") != "I-2" or go.get("action") != "GO":
        raise ValueError("reader GO absent")
    if go.get("capture_seal_sha256") != capture_seal_sha or go.get("bank_manifest_sha256") != input_manifest_sha:
        raise ValueError("GO binding mismatch")
    if not COMMIT_RE.fullmatch(str(go.get("jforecast_commit", ""))):
        raise ValueError("GO must cite the W-lens forecast commit")
    if not SHA_RE.fullmatch(str(go.get("jforecast_sha256", ""))):
        raise ValueError("GO must cite the W-lens forecast file hash")
    if go.get("judging_authorized") is not False:
        raise ValueError("reader GO must retain separate Guiv judging gate")


def forecast_proof(repo: Path, commit: str, artifact_path: str, expected_sha256: str) -> dict:
    """CPU-only Git-object check; stage its hashes, never the J-label artifact.

    I-2 calls this after receiving the W-lens commit. The artifact path must be
    repository-relative. This helper reads no reader outputs and creates no GO.
    """
    if not COMMIT_RE.fullmatch(commit) or not SHA_RE.fullmatch(expected_sha256):
        raise ValueError("full immutable forecast commit and hash required")
    path = Path(artifact_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("forecast path must be repository-relative")
    content = subprocess.run(["git", "show", f"{commit}:{path.as_posix()}"], cwd=repo,
                             check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("forecast file does not match committed Git object")
    return {"schema": "e73-forecast-proof-v1", "verified_by": "I-2", "commit": commit,
            "artifact_sha256": expected_sha256}


def archive_inputs(rows: list[dict], destination: Path, *, manifest_sha256: str, bank_manifest: Path,
                   source_files: dict[str, Path] | None = None, max_rows: int = 6400) -> list[dict]:
    """CPU preparation of label-free per-shard archives, never a repository tarball.

    Source files must be explicitly enumerated; no recursive copying, private map,
    source documents or dataset cache can enter an archive by accident.
    """
    validate_public(rows)
    if max_rows < 1 or not SHA_RE.fullmatch(manifest_sha256):
        raise ValueError("invalid shard size or manifest binding")
    if sha256(bank_manifest) != manifest_sha256:
        raise ValueError("bank manifest does not match its supplied hash")
    destination.mkdir(parents=True, exist_ok=True)
    summaries = []
    for start in range(0, len(rows), max_rows):
        subset = rows[start:start + max_rows]
        payload = ("\n".join(json.dumps(r, separators=(",", ":")) for r in subset) + "\n").encode()
        files = {"inputs/items.jsonl": payload, "inputs/BANK_MANIFEST.json": bank_manifest.read_bytes(),
                 "inputs/MANIFEST.json": (json.dumps({"schema": "e73-shard-v1", "bank_manifest_sha256": manifest_sha256,
                    "input_sha256": hashlib.sha256(payload).hexdigest(), "count": len(subset)}, sort_keys=True) + "\n").encode()}
        for name, p in (source_files or {}).items():
            rel = Path(name)
            if rel.is_absolute() or ".." in rel.parts or any(x in name.upper() for x in ("PRIVATE", "KEY")):
                raise ValueError("unsafe source archive member")
            if p.suffix != ".py" or p.is_symlink():
                raise ValueError("only explicitly supplied Python source may be staged")
            files[name] = p.read_bytes()
        path = destination / f"capture-{len(summaries):03d}.tar.gz"
        if path.exists():
            raise FileExistsError(path)
        with tarfile.open(path, "w:gz") as tar:
            for name, content in sorted(files.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mtime, info.mode = len(content), 0, 0o600
                tar.addfile(info, io.BytesIO(content))
        if path.stat().st_size > MAX_ARCHIVE_BYTES:
            path.unlink()
            raise ValueError("archive exceeds 20 MB; reduce max_rows")
        summaries.append({"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size,
                          "count": len(subset), "input_sha256": hashlib.sha256(payload).hexdigest()})
    write_json(destination / "SHARDS.json", summaries)
    return summaries


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-rows", type=int, default=6400)
    args = p.parse_args()
    archive_inputs(read_jsonl(args.inputs), args.out, manifest_sha256=sha256(args.manifest),
                   bank_manifest=args.manifest, max_rows=args.max_rows)


if __name__ == "__main__":
    main()
