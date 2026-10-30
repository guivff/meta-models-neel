"""Build the E74 pinned HF file inventory using anonymous metadata only.

No resolve GETs, weights, rollouts, credentials, or GPU APIs are used.  The
selected deployment set is the author's vLLM Oracle path, not the reconstructor.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import urllib.parse
import urllib.request

BASE = "nvidia/GLM-5.3-NVFP4"
LENS = "ceselder/glm-5.3-olens-lens"
PINS = {BASE: "e3b8f9f2fad29727dfa95e766c5cac18ea1414bf",
        LENS: "689c5dbae3d2f83dbf969e234a023958f1612185"}
ADAPTER = "rl1b_rl1b_2_step_0100"
AUDIT_SHA = "451765a51303ddcdb813139830d282151b6063ecbf7231c36ef9ee97e8acafa5"
SHARDS = {f"model-{n:05d}-of-00050.safetensors" for n in range(1, 51)}
BASE_ROLES = {
    "LICENSE": ("licence", False, "Retain the exact base licence alongside the staged checkpoint."),
    "README.md": ("licence_and_provenance", False, "Retain base card and licence metadata; not executed by the loader."),
    "config.json": ("model_config", True, "Architecture and model configuration used by vLLM."),
    "generation_config.json": ("generation_config", True, "Retain the declared generation configuration; runner fixes greedy settings explicitly."),
    "hf_quant_config.json": ("quantization_config", True, "Author loader reads and rewrites a local copy for W4A16 Marlin."),
    "model.safetensors.index.json": ("weight_index", True, "Maps model tensors to the 50 checkpoint shards."),
    "tokenizer.json": ("tokenizer", True, "Pinned GLM tokenizer model."),
    "tokenizer_config.json": ("tokenizer_config", True, "Pinned tokenizer and special-token configuration."),
    "chat_template.jinja": ("chat_template", True, "Author Oracle prompt uses the base's exact GLM chat template."),
}
LENS_ROLES = {
    "README.md": ("licence_and_provenance", False, "Adapter licence declaration and author runtime/setup contract; no separate LICENSE file is published."),
    "olens_glm53_usage.py": ("reference_runtime", True, "Author capture/Oracle implementation, grammar, embedding overwrite, and W4A16 override."),
    "vllm_metamodels_glm53_b26f02d.tar.gz": ("runtime_plugin", True, "Pinned author vLLM hook/LoRA plugin; install with --no-deps after vllm==0.31.0."),
    f"{ADAPTER}/adapter_config.json": ("selected_adapter_config", True, "Configuration for the frozen RL step-100 Oracle adapter."),
    f"{ADAPTER}/adapter_model.safetensors": ("selected_adapter_weights", True, "Only selected Oracle checkpoint; do not fetch the other adapters."),
    f"{ADAPTER}/README.md": ("selected_adapter_provenance", False, "Retain selected adapter's model card alongside its configuration and weights."),
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def get_metadata(repo: str) -> tuple[dict, dict]:
    url = f"https://huggingface.co/api/models/{repo}/revision/{PINS[repo]}?blobs=true"
    # urllib has no HF token-store or implicit HF authentication integration.
    request = urllib.request.Request(url, headers={"User-Agent": "E74-anonymous-file-manifest"})
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read(8_000_001)
        if response.status != 200 or len(raw) > 8_000_000:
            raise ValueError("metadata request failed or exceeded bounded metadata size")
        record = {"url": url, "method": "GET", "status": response.status,
                  "response_bytes": len(raw), "response_sha256": sha(raw),
                  "authentication": "none"}
    data = json.loads(raw)
    if data["sha"] != PINS[repo] or data.get("private") is not False or data.get("gated") not in (False, None):
        raise ValueError(f"pinned anonymous repo contract failed: {repo}")
    return record, data


def classify(repo: str, name: str) -> tuple[str, bool, bool, str]:
    if repo == BASE and name in SHARDS:
        return "base_weight_shard", True, True, "Every base checkpoint shard is required; no expert/shard pruning."
    selected = BASE_ROLES if repo == BASE else LENS_ROLES
    if name in selected:
        role, runtime, reason = selected[name]
        return role, True, runtime, reason
    if name == ".gitattributes":
        return "repository_metadata", False, False, "Git/LFS transport metadata; not a deployed inference dependency."
    if repo == LENS:
        if name.startswith("glm53_stack/"):
            return "unused_reconstructor_code", False, False, "Author path (b) HF reconstructor imports this stack; selected path (a) vLLM Oracle does not."
        if name.startswith("figures/"):
            return "unused_figure", False, False, "Model-card illustration; not needed for capture or Oracle inference."
        if name.startswith(ADAPTER + "/"):
            return "unused_training_metadata", False, False, "Training metrics/publication marker; not an input to selected adapter loading."
        if name.startswith(("rl1b_", "sft_")):
            return "unused_checkpoint", False, False, "Different adapter checkpoint or its metadata; excluded from the selected deployment set."
    raise ValueError(f"unclassified repository file: {repo}/{name}")


def make_file(repo: str, sibling: dict) -> dict:
    name, size, blob = sibling["rfilename"], sibling["size"], sibling["blobId"]
    if not name or name.startswith("/") or ".." in PurePosixPath(name).parts or "\\" in name:
        raise ValueError("unsafe repository path")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0 or not re.fullmatch(r"[0-9a-f]{40}", blob):
        raise ValueError("invalid size or Git blob identity")
    lfs = sibling.get("lfs")
    if lfs and (lfs["size"] != size or not re.fullmatch(r"[0-9a-f]{64}", lfs["sha256"])):
        raise ValueError("inconsistent LFS identity or size")
    role, selected, runtime, reason = classify(repo, name)
    out = {"path": name, "size_bytes": size, "git_blob_sha1": blob,
           "identity": {"algorithm": "sha256" if lfs else "git_blob_sha1",
                        "value": lfs["sha256"] if lfs else blob},
           "storage": "lfs" if lfs else "git", "role": role,
           "required": selected, "runtime_required": runtime, "selection_reason": reason,
           "resolve_url": f"https://huggingface.co/{repo}/resolve/{PINS[repo]}/{urllib.parse.quote(name, safe='/')}"}
    if lfs:
        out["lfs_sha256"] = lfs["sha256"]
        out["lfs_pointer_size_bytes"] = lfs["pointerSize"]
    return out


def audit_repo(repo: str, files: list[dict], audit: dict) -> dict:
    old = [r for r in audit["repos"] if r["repo_id"] == repo and r["revision"] == PINS[repo]]
    if len(old) != 1 or set(old[0]["files"]) != {f["path"] for f in files}:
        raise ValueError(f"repository inventory differs from ANONYMOUS_AUDIT: {repo}")
    by_url = {f["resolve_url"]: f for f in files}
    matched = []
    for head in audit["heads"]:
        if head["url"] not in by_url:
            continue
        f = by_url[head["url"]]
        if head["status"] != 200 or int(head["content_length"]) != f["size_bytes"]:
            raise ValueError(f"anonymous HEAD differs from file metadata: {f['path']}")
        f["prior_anonymous_head"] = {"status": 200, "content_length": int(head["content_length"])}
        matched.append(f["path"])
    expected_weights = SHARDS if repo == BASE else {f"{ADAPTER}/adapter_model.safetensors"}
    if not expected_weights <= set(matched):
        raise ValueError("prior anonymous audit does not cover every selected weight file")
    return {"inventory_exact_match": True, "prior_head_size_matches": len(matched),
            "all_selected_weights_prior_anonymous_head_200": True,
            "metadata_only_access_for_other_files": "Public pinned inventory; no new per-file HEAD or payload GET performed."}


def totals(files: list[dict]) -> dict:
    return {"file_count": len(files), "payload_bytes": sum(f["size_bytes"] for f in files),
            "required_file_count": sum(f["required"] for f in files),
            "required_payload_bytes": sum(f["size_bytes"] for f in files if f["required"]),
            "runtime_required_payload_bytes": sum(f["size_bytes"] for f in files if f["runtime_required"]),
            "unused_payload_bytes": sum(f["size_bytes"] for f in files if not f["required"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=Path("results/g_agreement/e74/ANONYMOUS_AUDIT.json"))
    parser.add_argument("--out", type=Path, default=Path("results/g_agreement/e74/ASSET_FILE_MANIFEST.json"))
    args = parser.parse_args()
    raw_audit = args.audit.read_bytes()
    if sha(raw_audit) != AUDIT_SHA:
        raise ValueError("ANONYMOUS_AUDIT hash differs from frozen asset-card audit")
    audit = json.loads(raw_audit)
    if audit["authentication"] != "none" or audit["weight_payload_bytes"] != 0:
        raise ValueError("unexpected prior audit custody")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        data = dict(zip(PINS, pool.map(get_metadata, PINS)))
    repos = []
    for repo in PINS:
        request, metadata = data[repo]
        files = sorted((make_file(repo, f) for f in metadata["siblings"]), key=lambda f: f["path"])
        names = {f["path"] for f in files}
        if len(names) != len(files):
            raise ValueError("duplicate file path")
        expected = SHARDS | set(BASE_ROLES) if repo == BASE else set(LENS_ROLES)
        if not expected <= names:
            raise ValueError("missing required deployment file")
        if repo == BASE and {n for n in names if n.endswith(".safetensors")} != SHARDS:
            raise ValueError("base must have exactly the pinned 50 shards")
        audited = audit_repo(repo, files, audit)
        repos.append({"repo_id": repo, "repo_type": "model", "revision": PINS[repo],
                      "selected_subfolder": ADAPTER if repo == LENS else None,
                      "metadata_request": request, "private": metadata["private"], "gated": metadata.get("gated"),
                      "file_inventory_sha256": sha(canonical(files)), "audit": audited,
                      "totals": totals(files), "files": files})
    all_files = [f for r in repos for f in r["files"]]
    required_bytes = sum(f["size_bytes"] for f in all_files if f["required"])
    weight_bytes = sum(f["size_bytes"] for f in all_files if f["required"] and f["path"].endswith(".safetensors"))
    doc = {
        "schema_version": 1, "experiment": "E74", "track": "G",
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "authentication": "none", "weight_payload_bytes_downloaded": 0, "rollout_payload_bytes_downloaded": 0,
        "source_code_sha256": sha(Path(__file__).read_bytes()), "anonymous_audit_sha256": AUDIT_SHA,
        "selection_contract": {
            "required": "Exact allowlist for staging the author vLLM Oracle path plus its licences/cards; includes all 50 base shards and only RL step-100 adapter weights.",
            "runtime_required": "Files conservatively retained for author inference; licence/provenance cards are required for staging but not loader inputs.",
            "unused": "Complete repo inventory is retained for audit, but required=false files must not be implicitly downloaded via an unfiltered snapshot.",
            "content_verification": "For LFS files compare SHA256 of payload bytes to lfs_sha256; git_blob_sha1 names the LFS pointer, not payload. For regular Git files compare SHA1(b'blob '+str(len(raw)).encode()+b'\\0'+raw) to git_blob_sha1.",
            "index_caveat": "Index contents were not downloaded here. Complete shard coverage is checked against the pinned repository inventory and prior anonymous HEAD audit.",
            "local_quant_override": "Verify upstream hf_quant_config.json first; author quant_override_w4a16 intentionally modifies a local copy. Record that derived configuration separately rather than treating it as upstream bytes."},
        "external_runtime_dependencies": {
            "source": f"https://huggingface.co/{LENS}/blob/{PINS[LENS]}/README.md#usage",
            "declared_by_author": ["CUDA 13", "torch 2.13", "transformers 5.17 (>=5.16.1,<5.18)", "peft 0.21", "vllm==0.31.0"],
            "pinned_plugin": "vllm_metamodels_glm53_b26f02d.tar.gz is included in the selected file set; this immutable tarball is preferred over the mutable Git branch.",
            "status": "Author-declared versions only. External container/wheel digests, transitive dependency resolution, CUDA compatibility and installed imports are not verified by this HF-file manifest.",
            "excluded_from_payload_estimate": ["container image", "CUDA/runtime libraries", "Python wheels and dependencies", "download/cache temporary duplication", "derived quantization config", "inputs and captured outputs", "smoke reference data"]},
        "repos": repos, "totals": totals(all_files),
        "staging_arithmetic": {
            "selected_weight_bytes": weight_bytes,
            "selected_nonweight_bytes": required_bytes-weight_bytes,
            "single_copy_selected_payload_bytes": required_bytes,
            "single_copy_selected_decimal_GB": required_bytes/1_000_000_000,
            "single_copy_selected_GiB": required_bytes/(1024**3),
            "two_full_copies_payload_bytes": 2*required_bytes,
            "formula": "single_copy = sum(size_bytes for all files where required); two_full_copies = 2 * single_copy (e.g. HF cache plus copied local checkpoint, before other overhead).",
            "transfer_seconds": None,
            "fits_900_seconds": None,
            "timing_caveat": "No transfer or boot measured. Payload bytes do not establish cold transfer or model loading within 900 seconds; stage and verify before a separately authorised GPU smoke window."},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"out": str(args.out), "sha256": sha(args.out.read_bytes()),
                      "totals": doc["totals"], "staging_arithmetic": doc["staging_arithmetic"]}, indent=2))


if __name__ == "__main__":
    main()
