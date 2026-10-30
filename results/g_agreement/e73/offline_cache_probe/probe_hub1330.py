"""Synthetic-only offline Hub 1.33.0 snapshot/cache semantics probe.

No real models, weights, secrets, credentials, or scientific outputs are used.
Adapter-named files below contain tiny inert text, never model tensors. This
script loads the separately installed --target package from ./site and writes
PROBE_RECEIPT.json plus synthetic cache fixtures under ./fixtures. It never
modifies production code, the project's venv, global packages, or real caches.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "site"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HOME"] = str(ROOT / "isolated_hf_home")
os.environ["HF_HUB_CACHE"] = str(ROOT / "isolated_default_hub")
os.environ["HF_TOKEN_PATH"] = str(ROOT / "no_token_exists")

import huggingface_hub
import httpx
from huggingface_hub import HfApi, snapshot_download
from huggingface_hub import _snapshot_download, _tree_cache
from huggingface_hub.file_download import repo_folder_name

assert huggingface_hub.__version__ == "1.33.0"
assert Path(huggingface_hub.__file__).resolve().is_relative_to((ROOT / "site").resolve())

ORACLE_REPO = "agu18dec/olens_and_ar"
ORACLE_REV = "c95215d5d2f6250f20c305ae55c6e4d7569f92dc"
ORACLE_PATTERN = ["olens_s3d_rl600/*"]
ORACLE_FILES = {
    "olens_s3d_rl600/adapter_model.safetensors": b"SYNTHETIC INERT FIXTURE: NOT WEIGHTS\n",
    "olens_s3d_rl600/adapter_config.json": b'{"synthetic_test_only":true}\n',
}
NLA_REPO = "ceselder/qwen3.6-27b-nla-rl"
NLA_REV = "5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f"
NLA_BASE_PATTERN = ["av_base/*", "nla_meta.yaml"]
NLA_ADAPTER_PATTERN = ["av_rl_adapters/iter_000400/*"]
NLA_FILES = {
    "av_base/config.json": b'{"synthetic_test_only":true}\n',
    "av_base/tokenizer.json": b'{"synthetic_test_only":true}\n',
    "av_base/model.safetensors": b"SYNTHETIC INERT FIXTURE: NOT A MODEL\n",
    "av_base/nla_meta.yaml": b"synthetic_test_only: true\n",
    "nla_meta.yaml": b"synthetic_test_only: true\n",
    "av_rl_adapters/iter_000400/adapter_model.safetensors": b"SYNTHETIC NLA ADAPTER: NOT WEIGHTS\n",
    "av_rl_adapters/iter_000400/adapter_config.json": b'{"synthetic_test_only":true}\n',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cache_fixture(name, repo, revision, files, *, tree_names=None, snapshot=True):
    cache = ROOT / "fixtures_v2" / name
    cache.mkdir(parents=True, exist_ok=False)
    storage = cache / repo_folder_name(repo_id=repo, repo_type="model")
    snap = storage / "snapshots" / revision
    if snapshot:
        snap.mkdir(parents=True)
    inventory = {}
    for relative, content in files.items():
        blob = storage / "blobs" / sha(content)
        blob.parent.mkdir(parents=True, exist_ok=True)
        blob.write_bytes(content)
        destination = snap / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(os.path.relpath(blob, destination.parent))
        inventory[relative] = {"sha256": sha(content), "bytes": len(content),
                               "symlink": os.readlink(destination)}
    if tree_names is not None:
        tree = storage / "trees" / (revision + ".json")
        tree.parent.mkdir(parents=True, exist_ok=True)
        entries = {name: {"size": len(files.get(name, b"absent")),
                           "blob_id": hashlib.sha1(files.get(name, b"absent")).hexdigest()}
                   for name in tree_names}
        tree.write_text(json.dumps({"format_version": 1, "files": entries}, sort_keys=True) + "\n")
    return cache, snap, inventory


class NetworkAttempt(AssertionError):
    pass


def run_case(name, *, repo, revision, patterns, files, tree_names=None,
             snapshot=True, local_files_only=True, expected_exception=None):
    cache, snap, inventory = cache_fixture(name, repo, revision, files,
                                          tree_names=tree_names, snapshot=snapshot)
    attempts, api_calls, http_client_calls = [], [], []
    def forbidden(kind):
        def blocked(*args, **kwargs):
            attempts.append(kind)
            raise NetworkAttempt("Network attempt blocked: " + kind)
        return blocked
    original_tree = HfApi.list_repo_tree
    original_info = HfApi.repo_info
    original_send = httpx.Client.send
    original_async_send = httpx.AsyncClient.send
    def send(self, *args, **kwargs):
        http_client_calls.append("httpx.Client.send")
        return original_send(self, *args, **kwargs)
    async def async_send(self, *args, **kwargs):
        http_client_calls.append("httpx.AsyncClient.send")
        return await original_async_send(self, *args, **kwargs)
    def tree(self, *args, **kwargs):
        api_calls.append("HfApi.list_repo_tree")
        return original_tree(self, *args, **kwargs)
    def info(self, *args, **kwargs):
        api_calls.append("HfApi.repo_info")
        return original_info(self, *args, **kwargs)
    result = {"name": name, "repo": repo, "revision": revision, "allow_patterns": patterns,
              "HF_HUB_OFFLINE": "1", "local_files_only": local_files_only,
              "tree_names": tree_names, "synthetic_files": inventory}
    with patch.object(socket.socket, "connect", forbidden("socket.connect")), \
         patch.object(socket.socket, "connect_ex", forbidden("socket.connect_ex")), \
         patch.object(socket, "create_connection", forbidden("socket.create_connection")), \
         patch.object(socket, "getaddrinfo", forbidden("socket.getaddrinfo")), \
         patch.object(httpx.Client, "send", send), \
         patch.object(httpx.AsyncClient, "send", async_send), \
         patch.object(httpx.HTTPTransport, "handle_request", forbidden("httpx.HTTPTransport.handle_request")), \
         patch.object(httpx.AsyncHTTPTransport, "handle_async_request", forbidden("httpx.AsyncHTTPTransport.handle_async_request")), \
         patch.object(HfApi, "list_repo_tree", tree), patch.object(HfApi, "repo_info", info):
        try:
            value = snapshot_download(repo, revision=revision, cache_dir=cache,
                                      allow_patterns=patterns, repo_type=None,
                                      local_files_only=local_files_only, token=False)
            result.update(status="RETURNED_SNAPSHOT", returned_snapshot=str(value))
            assert Path(value) == snap.resolve()
        except Exception as exc:
            result.update(status="EXCEPTION", exception_type=type(exc).__name__,
                          exception_message=str(exc), snapshot_path=getattr(exc, "snapshot_path", None))
    result.update(network_attempts=attempts, network_attempt_count=len(attempts), api_calls=api_calls,
                  http_client_calls=http_client_calls)
    actual_exception = result.get("exception_type")
    assert actual_exception == expected_exception, (name, result)
    assert not attempts, (name, attempts)
    if local_files_only:
        assert not api_calls, (name, api_calls)
        assert not http_client_calls, (name, http_client_calls)
    result["expected_behavior_pass"] = True
    return result


def pinned_file_probe():
    """Demonstrate exact-path/hash alternative only on the known synthetic bytes."""
    cache, snapshot, _ = cache_fixture("exact_pinned_path_with_extra_missing_tree_entry", ORACLE_REPO,
        ORACLE_REV, ORACLE_FILES, tree_names=[*ORACLE_FILES, "olens_s3d_rl600/run.json"])
    expected = {name: sha(content) for name, content in ORACLE_FILES.items()}
    exact = cache / repo_folder_name(repo_id=ORACLE_REPO, repo_type="model") / "snapshots" / ORACLE_REV
    assert exact == snapshot
    for name, digest in expected.items():
        assert (exact / name).is_file() and sha((exact / name).read_bytes()) == digest
    return {"status": "SYNTHETIC_HASH_CHECK_PASS", "repo": ORACLE_REPO, "revision": ORACLE_REV,
            "required_files": expected, "snapshot": str(exact), "hub_api_calls": 0,
            "production_asset_claim": False}


def main():
    scenarios = [
        dict(name="oracle_two_files_no_tree", files=ORACLE_FILES),
        dict(name="oracle_tree_exact_files", files=ORACLE_FILES, tree_names=list(ORACLE_FILES)),
        dict(name="oracle_tree_unrelated_missing_file_filtered", files=ORACLE_FILES,
             tree_names=[*ORACLE_FILES, "another_adapter/adapter_model.safetensors"]),
        dict(name="oracle_tree_extra_matching_run_json_missing", files=ORACLE_FILES,
             tree_names=[*ORACLE_FILES, "olens_s3d_rl600/run.json"], expected_exception="IncompleteSnapshotError"),
        dict(name="oracle_tree_required_adapter_missing", files={k: v for k, v in ORACLE_FILES.items() if k.endswith(".json")},
             tree_names=list(ORACLE_FILES), expected_exception="IncompleteSnapshotError"),
        dict(name="oracle_snapshot_missing", files={}, snapshot=False, expected_exception="LocalEntryNotFoundError"),
        dict(name="oracle_default_local_false_offline_env", files=ORACLE_FILES,
             local_files_only=False, expected_exception="OfflineModeIsEnabled"),
    ]
    results = [run_case(repo=ORACLE_REPO, revision=ORACLE_REV, patterns=ORACLE_PATTERN, **s) for s in scenarios]
    for name, patterns, tree, exc in (
        ("nla_base_no_tree", NLA_BASE_PATTERN, None, None),
        ("nla_adapter_no_tree", NLA_ADAPTER_PATTERN, None, None),
        ("nla_base_known_tree", NLA_BASE_PATTERN, list(NLA_FILES), None),
        ("nla_adapter_known_tree", NLA_ADAPTER_PATTERN, list(NLA_FILES), None),
        ("nla_base_extra_matching_missing", NLA_BASE_PATTERN, [*NLA_FILES, "av_base/README.md"], "IncompleteSnapshotError"),
        ("nla_adapter_ignores_missing_base_readme", NLA_ADAPTER_PATTERN, [*NLA_FILES, "av_base/README.md"], None),
    ):
        results.append(run_case(name, repo=NLA_REPO, revision=NLA_REV, patterns=patterns,
                                files=NLA_FILES, tree_names=tree, expected_exception=exc))
    modules = {name: Path(inspect.getsourcefile(module)) for name, module in
               (("_snapshot_download.py", _snapshot_download), ("_tree_cache.py", _tree_cache))}
    receipt = {"schema": "e73-hub1330-synthetic-probe-v1", "status": "PASS", "python": sys.version,
        "huggingface_hub_version": huggingface_hub.__version__, "package_location": huggingface_hub.__file__,
        "script_sha256": sha(Path(__file__).read_bytes()),
        "package_source_files": {name: {"path": str(path), "sha256": sha(path.read_bytes())} for name, path in modules.items()},
        "isolated_install": str(ROOT / "site"), "real_weights_or_models_loaded": False,
        "network_attempt_count": sum(r["network_attempt_count"] for r in results), "cases": results,
        "exact_pinned_path_probe": pinned_file_probe(),
        "conclusion": "local_files_only=True prevents all API/socket/HTTP calls. Partial snapshot with no cached tree succeeds. A known tree with missing allow_patterns-matching files raises IncompleteSnapshotError even when both adapter files exist. Existing default local_files_only=False reproduces OfflineModeIsEnabled via list_repo_tree despite HF_HUB_OFFLINE=1. No online fallback tested or used."}
    path = ROOT / "PROBE_RECEIPT.json"
    with path.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "version": huggingface_hub.__version__,
          "cases": len(results), "network_attempts": receipt["network_attempt_count"],
          "receipt": str(path), "receipt_sha256": sha(path.read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    main()
