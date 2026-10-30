"""Pinned, anonymous-only E73 corpus acquisition; never supplies credentials.

Metadata and files use plain urllib requests. A gated source is a recorded failure,
never an invitation to authenticate or silently substitute a mirror. Native
WikiText splits are pooled; E73's split is assigned later from document content.
"""
from __future__ import annotations

import argparse
import hashlib
import gzip
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SOURCES = {
    "codeparrot": {
        "repo": "codeparrot/codeparrot-clean",
        "revision": "35a59fb025bc0a102f7d96eac09d145b896d487b",
        "files": ["file-000000000001.json.gz"],
        "scope": "First 10000 records of first lexicographic source shard, fixed before corpus inspection; no expansion after BOW",
        "authorization": "BRIEF_UNDERSTAND §191 clarification 3, commit 7e6ea0cc",
    },
    "wikitext": {
        "repo": "Salesforce/wikitext",
        "revision": "b08601e04326c79dfdd32d625aee71d232d685c3",
        "files": [f"wikitext-103-raw-v1/{name}" for name in (
            "train-00000-of-00002.parquet", "train-00001-of-00002.parquet",
            "validation-00000-of-00001.parquet", "test-00000-of-00001.parquet")],
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def source_url(source: dict, filename: str) -> str:
    return f"https://huggingface.co/datasets/{source['repo']}/resolve/{source['revision']}/{filename}"


def anonymous_open(url: str, *, method: str = "GET"):
    # urllib does not consult the HF credential cache or .netrc. No authentication
    # header or cookie is constructed, and no authenticated SDK is imported.
    return urllib.request.urlopen(urllib.request.Request(url, method=method), timeout=60)


def inspect_sources(names: list[str]) -> dict:
    checks = []
    for name in names:
        source = SOURCES[name]
        for filename in source["files"]:
            record = {"dataset": name, "repo": source["repo"], "revision": source["revision"],
                      "filename": filename, "url": source_url(source, filename), "anonymous": True}
            try:
                with anonymous_open(record["url"], method="HEAD") as response:
                    record.update(http_status=response.status, accessible=response.status == 200)
            except urllib.error.HTTPError as error:
                record.update(http_status=error.code, accessible=False)
            except (urllib.error.URLError, TimeoutError) as error:
                record.update(http_status=None, accessible=False, error=type(error).__name__)
            checks.append(record)
    return {"experiment": "E73", "track": "C", "anonymous": True,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
            "all_accessible": all(row["accessible"] for row in checks)}


def download_sources(root: Path, names: list[str]) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "SOURCE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "experiment": "E73", "track": "C", "anonymous": True, "files": []}
    for name in names:
        source = SOURCES[name]
        for filename in source["files"]:
            relative = str(Path(name) / filename)
            destination = root / relative
            previous = next((r for r in manifest["files"] if r["path"] == relative), None)
            if previous:
                if previous["revision"] != source["revision"] or sha256_file(destination) != previous["sha256"]:
                    raise ValueError("Previously downloaded source changed; do not overwrite provenance")
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".partial")
            if destination.exists() or temporary.exists():
                raise FileExistsError(f"Unmanifested source exists: {destination}")
            try:
                with anonymous_open(source_url(source, filename)) as response, temporary.open("xb") as output:
                    for chunk in iter(lambda: response.read(1024 * 1024), b""):
                        output.write(chunk)
                temporary.rename(destination)
            except Exception:
                if temporary.exists():
                    temporary.unlink()
                raise
            manifest["files"].append({"dataset": name, "repo": source["repo"],
                "revision": source["revision"], "filename": filename, "path": relative,
                "sha256": sha256_file(destination), "bytes": destination.stat().st_size,
                "anonymous": True, "source_scope": source.get("scope", "all config files")})
            manifest["complete"] = len(manifest["files"]) == sum(len(s["files"]) for s in SOURCES.values())
            dump_json(manifest_path, manifest)
    return manifest


def verify_source_manifest(root: Path, *, require_complete: bool = True) -> dict:
    manifest = json.loads((root / "SOURCE_MANIFEST.json").read_text())
    expected = {(name, filename) for name, source in SOURCES.items() for filename in source["files"]}
    observed = set()
    if manifest.get("anonymous") is not True:
        raise ValueError("Source manifest does not attest anonymous acquisition")
    for row in manifest["files"]:
        key = row["dataset"], row["filename"]
        if key not in expected or key in observed:
            raise ValueError("Unexpected or duplicate source")
        observed.add(key)
        source = SOURCES[row["dataset"]]
        if row["revision"] != source["revision"] or row["repo"] != source["repo"] or row.get("anonymous") is not True:
            raise ValueError("Source identity mismatch")
        if row["path"] != str(Path(row["dataset"]) / row["filename"]):
            raise ValueError("Source path mismatch")
        if sha256_file(root / row["path"]) != row["sha256"]:
            raise ValueError("Source hash mismatch")
    if require_complete and observed != expected:
        raise ValueError("Incomplete corpus: no E73 scientific bank may be sampled")
    return manifest


def _stack_records(path: Path) -> Iterator[dict]:
    with (gzip.open(path, "rt") if path.suffix == ".gz" else path.open()) as handle:
        first = next((c for c in iter(lambda: handle.read(1), "") if not c.isspace()), "")
        handle.seek(0)
        if first == "[":
            yield from json.load(handle)
        else:
            for line in handle:
                if line.strip():
                    yield json.loads(line)


def iter_documents(root: Path, manifest: dict) -> Iterator[dict]:
    """Reconstruct complete articles, preserving original raw text and provenance."""
    for row in manifest["files"]:
        if row["dataset"] != "codeparrot":
            continue
        language = "python"
        for index, record in enumerate(_stack_records(root / row["path"])):
            if index >= 10000:
                break
            text = record.get("content")
            if not isinstance(text, str) or not text:
                continue
            original_path = record.get("path", record.get("max_stars_repo_path", ""))
            if language == "markdown" and not original_path.lower().endswith(".md"):
                continue
            yield {"text": text, "language": language, "title": "", "source": row["repo"],
                   "source_file": row["filename"], "source_index": index,
                   "original_path": original_path, "repository": record.get("max_stars_repo_name", "")}
    # A top-level '= Title =' line starts a document. Sections ('== ... ==') do
    # not. Preserve article assembly across parquet shard boundaries in train.
    import pyarrow.parquet as pq
    wiki = [r for r in manifest["files"] if r["dataset"] == "wikitext"]
    heading = re.compile(r"^\s*= ([^=\n]+?) =\s*$")
    for native_split in ("train", "validation", "test"):
        title, parts, origin, start_index = None, [], None, 0
        for row in sorted((r for r in wiki if Path(r["filename"]).name.startswith(native_split + "-")), key=lambda r: r["filename"]):
            index = 0
            for batch in pq.ParquetFile(root / row["path"]).iter_batches(columns=["text"], batch_size=1024):
                for text in batch.column(0).to_pylist():
                    match = heading.fullmatch(text)
                    if match:
                        if title is not None:
                            yield {"text": "".join(parts), "language": "wikitext", "title": title,
                                   "source": row["repo"], "source_file": origin, "source_index": start_index}
                        title, parts, origin, start_index = match.group(1).strip(), [], row["filename"], index
                    if title is not None:
                        parts.append(text)
                    index += 1
        if title is not None:
            yield {"text": "".join(parts), "language": "wikitext", "title": title,
                   "source": SOURCES["wikitext"]["repo"], "source_file": origin, "source_index": start_index}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "download"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--dataset", choices=("all", *SOURCES), default="all")
    args = parser.parse_args()
    names = list(SOURCES) if args.dataset == "all" else [args.dataset]
    args.root.mkdir(parents=True, exist_ok=True)
    report = inspect_sources(names)
    report_path = args.root / f"ACCESS_{args.dataset}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    dump_json(report_path, report)
    if args.command == "download":
        if not report["all_accessible"]:
            raise SystemExit(f"ANONYMOUS_SOURCE_UNAVAILABLE; see {report_path}")
        manifest = download_sources(args.root, names)
        print(json.dumps({"manifest": str(args.root / "SOURCE_MANIFEST.json"), "complete": manifest["complete"]}))
    else:
        print(json.dumps({"report": str(report_path), "all_accessible": report["all_accessible"]}))


if __name__ == "__main__":
    main()
