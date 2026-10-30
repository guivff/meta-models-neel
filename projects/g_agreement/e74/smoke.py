"""E74 one-item Oracle smoke. CPU preflight is safe; run requires I-2 admission.

The fixture contains original transcript token IDs and only a hash of the frozen
reference. The sole generated text stays in sealed/raw_readout.json. An exact
match is sufficient for PASS; every nonmatch stops for review. No near-match
threshold, retry, alternate item, or alternate checkpoint is introduced here.

A process-group supervisor bounds the run to the supplied GPU-allocation deadline.
I-2 must also retain its provider hard stop: killing a process group is not proof
that a billable pod has been released. This runner never provisions a pod.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tarfile
import time

BASE_REPO = "nvidia/GLM-5.3-NVFP4"
BASE_REVISION = "e3b8f9f2fad29727dfa95e766c5cac18ea1414bf"
LENS_REPO = "ceselder/glm-5.3-olens-lens"
LENS_REVISION = "689c5dbae3d2f83dbf969e234a023958f1612185"
LENS_PATH = "rl1b_rl1b_2_step_0100"
DATA_REPO = "ceselder/glm-5.3-olens-wild-rollouts"
DATA_REVISION = "226c6dce62ed88d5981ca864d0c99d3f082ccee6"
REFERENCE_SHA256 = "ebbd4a1fb0b1cf7673ebbe5e75ee102d6652a789ae3b9f9287c06a9011fcfa42"
PROMPT_SHA256 = "1c6fedba2d93bb4520a0c4f42757f89ba7ab3f2653500418b874a0c09d905dea"
ADAPTER_CONFIG_SHA256 = "fe8c033f38d91aea843b3e69d17250fab9c846c2c334d64e2d98d88690673120"
FORK_SHA256 = "8d9ca706651a1325c7ad9db78b19989a0f0082944577b310dc5aa0cf95046c82"
# Metadata-only SHA256 derived from the canonical HF asset manifest.
WEIGHT_MANIFEST_SHA256 = "7454bcf3f23965bd31b05a274a2d84832b37d2db16530926895396879fe449b5"
FIXTURE_FIELDS = {
    "schema_version", "token_ids", "read_position", "expected_readout_sha256",
    "source_repo", "source_revision", "tid", "pos", "reference_field", "adapter_path",
}
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def text_hash(text: str) -> str:
    # The author's verbalize method returns c.text.strip(). This is the only
    # normalization; internal spacing, punctuation and case remain significant.
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def canonical_write(path: Path, obj: dict) -> None:
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")
    path.chmod(0o600)


def validate_fixture(fixture: dict) -> dict:
    if not isinstance(fixture, dict) or set(fixture) != FIXTURE_FIELDS:
        raise ValueError("fixture schema differs from the frozen smoke schema")
    exact = {"schema_version": 1, "source_repo": DATA_REPO,
             "source_revision": DATA_REVISION, "reference_field": "rl_greedy",
             "adapter_path": LENS_PATH}
    for key, expected in exact.items():
        if type(fixture[key]) is not type(expected) or fixture[key] != expected:
            raise ValueError(f"fixture {key} does not match the frozen source")
    ids = fixture["token_ids"]
    if not isinstance(ids, list) or not 1 <= len(ids) <= 1151:
        raise ValueError("fixture must retain a complete eligible transcript of 1..1151 tokens")
    if any(type(x) is not int or not 0 <= x < 154856 for x in ids):
        raise ValueError("fixture contains invalid GLM token IDs")
    pos = fixture["read_position"]
    if type(pos) is not int or not 0 <= pos < len(ids) or type(fixture["pos"]) is not int or pos != fixture["pos"]:
        raise ValueError("fixture read position is invalid or inconsistent")
    if ids[pos] in (154822, 154824):
        raise ValueError("fixture read position is an excluded sink token")
    if not isinstance(fixture["tid"], str) or not fixture["tid"]:
        raise ValueError("fixture lacks its frozen transcript identifier")
    if not isinstance(fixture["expected_readout_sha256"], str) or not SHA_RE.fullmatch(fixture["expected_readout_sha256"]):
        raise ValueError("fixture reference digest is invalid")
    return fixture


def load_bound_json(path: Path, expected_hash: str) -> dict:
    if not SHA_RE.fullmatch(expected_hash) or sha256(path) != expected_hash:
        raise ValueError("input digest mismatch")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_deadline(allocation_start: float, deadline: float, now: float) -> float:
    if not all(math.isfinite(x) for x in (allocation_start, deadline, now)):
        raise ValueError("nonfinite timing input")
    if allocation_start > now or not 0 < deadline - allocation_start <= 1200:
        raise ValueError("deadline must be within 1200 seconds of actual GPU allocation")
    remaining = deadline - now
    if remaining <= 0:
        raise ValueError("GPU allocation deadline has elapsed")
    return remaining


def require_private_quant_copy(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("quant configuration must be a private regular copy, never a symlink or hardlink")
    if ".cache/huggingface" in str(path.resolve()) or "/snapshots/" in str(path.resolve()):
        raise ValueError("runtime quant configuration cannot be in a canonical HF cache")


def stat_identity(path: Path) -> dict:
    info = path.stat()
    return {"bytes": info.st_size, "mtime_ns": info.st_mtime_ns,
            "device": info.st_dev, "inode": info.st_ino}


def verify_fork(archive: Path) -> dict:
    """Compare installed Python sources directly against the pinned tar, no import."""
    if sha256(archive) != FORK_SHA256:
        raise ValueError("vLLM metamodels fork archive digest mismatch")
    installed = importlib.metadata.distribution("vllm-lens")
    root = Path(installed.locate_file("vllm_lens")).resolve()
    spec = importlib.util.find_spec("vllm_lens")
    if spec is None or Path(spec.origin).resolve().parent != root:
        raise ValueError("another vllm_lens package shadows the verified fork")
    checked = {}
    prefix = "vllm-metamodels-glm53/vllm_lens/"
    with tarfile.open(archive, "r:gz") as packed:
        for member in packed.getmembers():
            if not member.isfile() or not member.name.startswith(prefix) or not member.name.endswith(".py"):
                continue
            relative = member.name[len(prefix):]
            if ".." in Path(relative).parts:
                raise ValueError("unsafe fork member")
            expected = hashlib.sha256(packed.extractfile(member).read()).hexdigest()
            if sha256(root / relative) != expected:
                raise ValueError("installed fork source differs from the pinned archive")
            checked[relative] = expected
    if len(checked) < 10:
        raise ValueError("incomplete fork source verification")
    if {str(p.relative_to(root)) for p in root.rglob("*.py")} != set(checked):
        raise ValueError("installed fork includes unpinned Python source files")
    return checked


def check_dependencies(staged_versions: dict) -> dict:
    versions = {name: importlib.metadata.version(name)
                for name in ("vllm", "vllm-lens", "torch", "transformers", "peft")}
    versions["python"] = ".".join(map(str, sys.version_info[:3]))
    import torch
    versions["torch_cuda"] = torch.version.cuda
    if versions != staged_versions:
        raise ValueError("runtime dependency versions differ from the CPU staging receipt")
    if (sys.version_info < (3, 12) or versions["vllm"] != "0.31.0" or
            versions["vllm-lens"] != "1.1.0.post7" or
            not re.match(r"^2\.13(?:\.|$)", versions["torch"]) or
            not re.match(r"^5\.17(?:\.|$)", versions["transformers"]) or
            not re.match(r"^0\.21(?:\.|$)", versions["peft"]) or
            not isinstance(versions["torch_cuda"], str) or
            not re.match(r"^13(?:\.|$)", versions["torch_cuda"])):
        raise ValueError("runtime differs from the author's dependency family")
    return versions


def check_staging_receipt(receipt: dict, manifest: dict, model_dir: Path,
                          adapter_dir: Path, allocation_start: float, staging_limit_seconds: int = 900) -> dict:
    """Require CPU checks of every full weight before model load; recheck identity.

    I-2 owns this create-only receipt and binds its SHA256 into the admitted
    request. This function does not invent an attestation or a GPU allocation.
    A receipt entry records sha256 plus bytes/mtime_ns/device/inode after reading
    the complete staged file. Destination verification may finish after GPU
    allocation, within the caller's registered staging window (legacy default900). That staging consumes the
    same 1200-second GPU lifetime as model loading and the readout; I-2 must admit
    the measured total fit. Pre-allocation verification remains allowed. We do
    not rehash the staged weights again in this model-load worker.
    """
    required = {"schema_version", "experiment", "base_repo", "base_revision", "lens_repo",
                "lens_revision", "adapter_path", "model_dir", "adapter_dir", "completed_epoch",
                "storage", "full_weight_sha256_verified", "canonical_cache_unchanged",
                "weight_manifest_sha256", "fork_archive_sha256", "files", "runtime_versions"}
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ValueError("missing or unexpected CPU staging receipt fields")
    exact = {"schema_version": 1, "experiment": "E74", "base_repo": BASE_REPO,
             "base_revision": BASE_REVISION, "lens_repo": LENS_REPO,
             "lens_revision": LENS_REVISION, "adapter_path": LENS_PATH,
             "model_dir": str(model_dir.resolve()), "adapter_dir": str(adapter_dir.resolve()),
             "storage": "local_nvme", "full_weight_sha256_verified": True,
             "canonical_cache_unchanged": True, "weight_manifest_sha256": WEIGHT_MANIFEST_SHA256,
             "fork_archive_sha256": FORK_SHA256}
    for key, value in exact.items():
        if type(receipt[key]) is not type(value) or receipt[key] != value:
            raise ValueError(f"CPU staging receipt mismatch: {key}")
    completed = receipt["completed_epoch"]
    if (type(completed) not in (int, float) or not math.isfinite(completed) or
            not 0 < completed <= time.time() or completed > allocation_start + staging_limit_seconds):
        raise ValueError(f"CPU staging verification must be complete now and within {staging_limit_seconds} seconds of GPU allocation")
    for area, repo, revision in (("base", BASE_REPO, BASE_REVISION), ("lens", LENS_REPO, LENS_REVISION)):
        if manifest[area]["repo"] != repo or manifest[area]["revision"] != revision:
            raise ValueError("weight manifest asset pin mismatch")
    if manifest["lens"]["adapter_path"] != LENS_PATH:
        raise ValueError("weight manifest adapter pin mismatch")
    expected_files = {"base/" + key: value for key, value in manifest["base"]["files"].items()}
    expected_files.update({"adapter/" + key: value for key, value in manifest["lens"]["files"].items()})
    if set(receipt["files"]) != set(expected_files):
        raise ValueError("staging receipt does not cover the complete pinned asset manifest")
    for name, expected in expected_files.items():
        area, relative = name.split("/", 1)
        if area not in ("base", "adapter") or ".." in Path(relative).parts or Path(relative).is_absolute():
            raise ValueError("unsafe asset manifest path")
        path = (model_dir if area == "base" else adapter_dir) / relative
        record = receipt["files"][name]
        if set(record) != {"sha256", "bytes", "mtime_ns", "device", "inode"}:
            raise ValueError("staged file lacks its complete checksum and filesystem identity")
        if record["sha256"] != expected["sha256"] or record["bytes"] != expected["bytes"]:
            raise ValueError("staged checksum differs from the pinned HF manifest")
        if {key: record[key] for key in stat_identity(path)} != stat_identity(path):
            raise ValueError("staged file identity changed after CPU verification")
    qp = model_dir / "hf_quant_config.json"
    require_private_quant_copy(qp)
    if sha256(qp) != manifest["base"]["files"]["hf_quant_config.json"]["sha256"]:
        raise ValueError("quant configuration must begin at the pinned original")
    return {"files_bound_to_cpu_checksums": len(expected_files), "storage": "local_nvme",
            "full_weights_rehashed_during_smoke": False}


def check_local_assets(audit: dict, model_dir: Path, adapter_dir: Path) -> dict:
    """Recheck sizes and control files, not 464 GB of previously staged contents.

    Full weight checksums/local-NVMe residency remain I-2 staging prerequisites.
    This function must not be described as full weight-integrity verification.
    """
    if audit.get("authentication") != "none":
        raise ValueError("expected anonymous asset-audit evidence")
    base_prefix = f"https://huggingface.co/{BASE_REPO}/resolve/{BASE_REVISION}/"
    adapter_prefix = f"https://huggingface.co/{LENS_REPO}/resolve/{LENS_REVISION}/{LENS_PATH}/"
    weights = [h for h in audit["heads"] if h["url"].startswith(base_prefix) and h["url"].endswith(".safetensors")]
    if len(weights) != 50:
        raise ValueError("expected exactly 50 pinned base shards")
    total = 0
    for head in weights:
        name = head["url"][len(base_prefix):]
        if Path(name).name != name or head["status"] != 200:
            raise ValueError("unsafe or inaccessible base shard entry")
        size = int(head["content_length"])
        if (model_dir / name).stat().st_size != size:
            raise ValueError("base shard size differs from anonymous pinned evidence")
        total += size
    heads = [h for h in audit["heads"] if h["url"] == adapter_prefix + "adapter_model.safetensors"]
    if len(heads) != 1 or heads[0]["status"] != 200:
        raise ValueError("original step-100 adapter evidence missing")
    if (adapter_dir / "adapter_model.safetensors").stat().st_size != int(heads[0]["content_length"]):
        raise ValueError("adapter size differs from pinned evidence")
    if sha256(adapter_dir / "adapter_config.json") != ADAPTER_CONFIG_SHA256:
        raise ValueError("adapter configuration differs from pinned original")
    config = json.loads((model_dir / "config.json").read_text())
    for key, value in {"model_type": "glm_moe_dsa", "num_hidden_layers": 78, "hidden_size": 6144,
                       "n_routed_experts": 256, "num_experts_per_tok": 8}.items():
        if config.get(key) != value:
            raise ValueError(f"base configuration mismatch: {key}")
    quant = json.loads((model_dir / "hf_quant_config.json").read_text())
    layers = quant["quantization"]["quantized_layers"]
    routed = [v.get("quant_algo", "").upper() for k, v in layers.items() if ".experts" in k]
    if len(routed) != 75 or any(x not in ("NVFP4", "W4A16_NVFP4") for x in routed):
        raise ValueError("base is not the author's packed NVFP4 expert checkpoint")
    return {"base_shards_size_checked": 50, "base_shards_total_bytes": total,
            "adapter_size_checked": True, "adapter_config_sha256": ADAPTER_CONFIG_SHA256,
            "full_weight_content_verification": "bound CPU staging receipt required"}


def check_runtime_interface(runtime) -> None:
    expected = {"BASE_REPO": BASE_REPO, "READ_LAYER": 51, "N_LAYERS": 78, "HIDDEN": 6144,
                "MARKER_ID": 154518, "ALPHA": 54.1, "EOS_ID": 154820}
    if any(getattr(runtime, key, None) != value for key, value in expected.items()):
        raise ValueError("author runtime constants differ from the sealed interface")
    if hashlib.sha256(runtime.LENS1_INSTRUCTION.encode("utf-8")).hexdigest() != PROMPT_SHA256:
        raise ValueError("lens prompt differs from the sealed prompt")


def one_readout(fixture: dict, runtime, engine, adapter_dir: str) -> dict:
    """Exactly one capture position and exactly one greedy lens generation."""
    import torch
    validate_fixture(fixture)
    check_runtime_interface(runtime)
    if engine.n_workers != 4 or len(engine.prompt_ids) != 70 or engine.mpos != 63:
        raise ValueError("TP count or rendered lens prompt mismatch")
    if engine.prompt_ids[63] != 154518 or engine.prompt_ids.count(154518) != 1:
        raise ValueError("marker location mismatch")
    if engine.merged is not None:
        raise ValueError("smoke capture must start from the unmerged base")
    acts = engine.capture_h51([fixture["token_ids"]], [[fixture["read_position"]]])
    if len(acts) != 1 or tuple(acts[0].shape) != (1, 6144):
        raise ValueError("capture shape mismatch")
    vec = acts[0]
    if not bool(torch.isfinite(vec).all()) or float(vec.norm()) <= 0:
        raise ValueError("invalid captured activation")
    engine.set_lens(adapter_dir, keep_base="gpu")
    readouts = engine.verbalize(vec, n=1, temperature=0.0, cap=16, seed=0, alpha=54.1)
    if (not isinstance(readouts, list) or len(readouts) != 1 or
            not isinstance(readouts[0], list) or len(readouts[0]) != 1 or
            not isinstance(readouts[0][0], str) or not readouts[0][0]):
        raise ValueError("expected exactly one nonempty greedy output")
    text = readouts[0][0].strip()
    generated_hash = text_hash(text)
    exact = generated_hash == fixture["expected_readout_sha256"]
    return {"status": "PASS_EXACT" if exact else "STOP_REVIEW_NOT_IDENTICAL",
            "exact_reference_match": exact, "readout": text,
            "generated_readout_sha256": generated_hash,
            "expected_readout_sha256": fixture["expected_readout_sha256"],
            "activation_norm": float(vec.norm()), "generated_count": 1,
            "capture_positions": 1, "read_block": 51, "temperature": 0.0}


def import_author_runtime(path: Path):
    if path.name != "olens_glm53_usage.py" or sha256(path) != REFERENCE_SHA256:
        raise ValueError("author runtime source digest mismatch")
    sys.path.insert(0, str(path.resolve().parent))
    runtime = importlib.import_module("olens_glm53_usage")
    if Path(runtime.__file__).resolve() != path.resolve():
        raise ValueError("imported a different author runtime")
    check_runtime_interface(runtime)
    return runtime


def worker(request_path: Path, out: Path) -> int:
    request = json.loads(request_path.read_text())
    if sys.flags.optimize:
        raise ValueError("author hook assertions must remain enabled")
    os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                       "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1", "VLLM_LENS_CUDA_GRAPHS": "1",
                       "VLLM_ALLOW_INSECURE_SERIALIZATION": "1", "VLLM_LENS_MERGE_ALLOW_TP": "1"})
    validate_deadline(request["allocation_start_epoch"], request["deadline_epoch"], time.time())
    fixture = validate_fixture(load_bound_json(Path(request["fixture"]), request["fixture_sha256"]))
    audit = load_bound_json(Path(request["asset_audit"]), request["asset_audit_sha256"])
    manifest = load_bound_json(Path(request["weight_manifest"]), WEIGHT_MANIFEST_SHA256)
    staging = load_bound_json(Path(request["staging_receipt"]), request["staging_receipt_sha256"])
    checked = check_staging_receipt(staging, manifest, Path(request["model_dir"]),
                                    Path(request["adapter_dir"]), request["allocation_start_epoch"])
    checked.update(check_local_assets(audit, Path(request["model_dir"]), Path(request["adapter_dir"])))
    installed_fork = verify_fork(Path(request["fork_archive"]))
    versions = check_dependencies(staging["runtime_versions"])
    runtime = import_author_runtime(Path(request["runtime"]))
    import torch
    if torch.cuda.device_count() != 4 or any("B200" not in torch.cuda.get_device_name(i) for i in range(4)):
        raise ValueError("smoke requires exactly four visible B200 GPUs")
    start = time.monotonic()
    # The reference modifies only hf_quant_config.json on the LOCAL checkpoint
    # copy. Record both hashes; never point this at a shared HF snapshot/cache.
    qp = Path(request["model_dir"]) / "hf_quant_config.json"
    before = sha256(qp)
    engine = runtime.GlmOlensEngine(
        request["model_dir"], tp=4, gpu_mem=0.88, moe_backend="marlin", kv_cache_dtype="fp8",
        max_model_len=1152, max_num_seqs=512, max_num_batched_tokens=32768, w4a16=True, seed=0,
    )
    if sha256(qp) != manifest["author_quant_override"]["derived_hf_quant_config_sha256"]:
        raise ValueError("author-derived W4A16 configuration differs from the sealed derivation")
    result = one_readout(fixture, runtime, engine, request["adapter_dir"])
    sealed = out / "sealed"
    sealed.mkdir(mode=0o700)
    raw = sealed / "raw_readout.json"
    canonical_write(raw, {"fixture_sha256": request["fixture_sha256"], "readout": result.pop("readout")})
    canonical_write(sealed / "SEAL.json", {"schema_version": 1, "raw_file": raw.name,
                    "raw_sha256": sha256(raw), "raw_bytes": raw.stat().st_size})
    result.update({"experiment": "E74", "track": "G", "fixture_sha256": request["fixture_sha256"],
                   "asset_audit_sha256": request["asset_audit_sha256"], "runtime_sha256": REFERENCE_SHA256,
                   "staging_receipt_sha256": request["staging_receipt_sha256"],
                   "weight_manifest_sha256": WEIGHT_MANIFEST_SHA256,
                   "fork_archive_sha256": FORK_SHA256, "installed_fork_sources": installed_fork,
                   "runtime_versions": versions,
                   "base_repo": BASE_REPO, "base_revision": BASE_REVISION,
                   "lens_repo": LENS_REPO, "lens_revision": LENS_REVISION, "adapter_path": LENS_PATH,
                   "model_and_readout_seconds": time.monotonic()-start,
                   "quant_config_before_sha256": before, "quant_config_after_sha256": sha256(qp),
                   "raw_seal_sha256": sha256(sealed / "SEAL.json"), "local_asset_checks": checked,
                   "capture_authorized": False, "reader_bank_authorized": False,
                   "provider_release_verified": False})
    canonical_write(out / "WORKER_RESULT.json", result)
    return 0 if result["exact_reference_match"] else 3


def kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def supervise(request: dict, out: Path) -> int:
    validate_deadline(request["allocation_start_epoch"], request["deadline_epoch"], time.time())
    out.mkdir(parents=True, mode=0o700, exist_ok=False)  # once-only; no overwrite/retry
    req_path = out / "RUN_REQUEST.json"
    canonical_write(req_path, request)
    log_path = out / "worker.log"
    started = time.time()
    with log_path.open("x") as logs:
        proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--_worker-request",
                                 str(req_path.resolve()), "--out", str(out.resolve())],
                                stdout=logs, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=max(0.01, request["deadline_epoch"] - time.time() - 1.0))
        except subprocess.TimeoutExpired:
            kill_group(proc.pid)
            code = 124
            try:
                proc.wait(timeout=max(0.01, min(1.0, request["deadline_epoch"] - time.time())))
            except subprocess.TimeoutExpired:
                pass  # provider hard stop remains authoritative for billing
        finally:
            kill_group(proc.pid)  # include any orphaned TP workers in the group
    log_path.chmod(0o600)
    if time.time() >= request["deadline_epoch"]:
        code = 124
    receipt = {"schema_version": 1, "experiment": "E74", "track": "G",
               "fixture_sha256": request["fixture_sha256"], "exit_code": code,
               "started_utc": dt.datetime.fromtimestamp(started, dt.timezone.utc).isoformat(),
               "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "allocation_elapsed_seconds": time.time()-request["allocation_start_epoch"],
               "provider_release_verified": False, "capture_authorized": False,
               "reader_bank_authorized": False, "stdout_contains_readout": False}
    result_path = out / "WORKER_RESULT.json"
    if code in (0, 3) and result_path.exists():
        result = json.loads(result_path.read_text())
        receipt.update({"status": result["status"], "exact_reference_match": result["exact_reference_match"],
                        "worker_result_sha256": sha256(result_path), "raw_seal_sha256": result["raw_seal_sha256"]})
    else:
        receipt["status"] = "STOP_TIMEOUT" if code == 124 else "STOP_SETUP_ERROR"
    canonical_write(out / "SMOKE_RECEIPT.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return code


def main(argv=None) -> int:
    raise RuntimeError("Single-fixture smoke superseded by b90325cb; use projects.g_agreement.e74.smoke50")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--_worker-request", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--fixture-sha256")
    parser.add_argument("--asset-audit", type=Path)
    parser.add_argument("--asset-audit-sha256")
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--fork-archive", type=Path)
    parser.add_argument("--weight-manifest", type=Path)
    parser.add_argument("--staging-receipt", type=Path)
    parser.add_argument("--staging-receipt-sha256")
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--adapter-dir", type=Path)
    parser.add_argument("--allocation-start-epoch", type=float)
    parser.add_argument("--deadline-epoch", type=float)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--preflight", action="store_true", help="CPU-only fixture and pinned reference checks; no model load")
    args = parser.parse_args(argv)
    if args._worker_request:
        if args.out is None:
            parser.error("--out required")
        return worker(args._worker_request, args.out)
    required = ["fixture", "fixture_sha256", "runtime"]
    if not args.preflight:
        required += ["asset_audit", "asset_audit_sha256", "model_dir", "adapter_dir", "allocation_start_epoch", "deadline_epoch", "out", "fork_archive", "weight_manifest",
                     "staging_receipt", "staging_receipt_sha256"]
    if any(getattr(args, name) is None for name in required):
        parser.error("missing required inputs: " + ", ".join(required))
    fixture = validate_fixture(load_bound_json(args.fixture, args.fixture_sha256))
    if sha256(args.runtime) != REFERENCE_SHA256:
        raise ValueError("author runtime source digest mismatch")
    if args.preflight:
        print(json.dumps({"status": "CPU_PREFLIGHT_PASS", "fixture_sha256": args.fixture_sha256,
                          "runtime_sha256": REFERENCE_SHA256, "input_tokens": len(fixture["token_ids"]),
                          "read_position": fixture["read_position"], "gpu_used": False, "readout_opened": False}))
        return 0
    request = {name: str(getattr(args, name).resolve()) if isinstance(getattr(args, name), Path) else getattr(args, name)
               for name in required if name != "out"}
    return supervise(request, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
