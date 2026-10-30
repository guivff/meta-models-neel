"""E73 forward-only capture: raw 256-token contexts, block 44 all / block 42 last.

No chat template, text generation, labels, probe fit or reader call is reachable
from this executable. I-2 admission and the committed source hashes are required
before loading a model. Output shards are independently bounded to 20 MB.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from .custody import (MAX_ARCHIVE_BYTES, check_admission, check_source_files,
                      hard_deadline, read_jsonl, seal, sha256, validate_public, write_json)


def captured_arrays(model, input_ids: list[list[int]], *, device=None):
    """One equal-length, unpadded forward; clone hook values before later mutation.

    Imports torch only when called. This follows the audited clone convention in
    understand/e24_clone_capture.py and core/model.py's block-output convention.
    """
    import torch
    from projects.g_agreement.core.model import blocks, disable_adapter_ctx
    if not input_ids or any(len(x) != 256 for x in input_ids):
        raise ValueError("capture requires complete 256-token sequences")
    storage, handles = {}, []

    def hook_for(layer):
        def hook(_module, _inputs, output):
            h = output[0] if isinstance(output, tuple) else output
            chosen = h if layer == 44 else h[:, -1, :]
            storage[layer] = chosen.detach().clone().to(device="cpu", dtype=torch.float16).numpy()
        return hook

    for layer in (42, 44):
        handles.append(blocks(model)[layer].register_forward_hook(hook_for(layer)))
    dev = device or next(model.parameters()).device
    try:
        with torch.inference_mode(), disable_adapter_ctx(model):
            x = torch.tensor(input_ids, device=dev, dtype=torch.long)
            model(input_ids=x, attention_mask=torch.ones_like(x), use_cache=False, logits_to_keep=1)
    finally:
        for handle in handles:
            handle.remove()
    if set(storage) != {42, 44}:
        raise ValueError("required block hook did not fire")
    if storage[44].shape != (len(input_ids), 256, 5120) or storage[42].shape != (len(input_ids), 5120):
        raise ValueError("capture shape mismatch")
    return storage


def save_capture_shard(destination: Path, index: int, rows: list[dict], arrays: dict) -> Path:
    import numpy as np
    validate_public(rows)
    if arrays[44].shape != (len(rows), 256, 5120) or arrays[42].shape != (len(rows), 5120):
        raise ValueError("capture shard coverage mismatch")
    if any(not np.isfinite(v).all() for v in arrays.values()):
        raise ValueError("nonfinite activation")
    p = destination / f"capture-{index:05d}.npz"
    if p.exists():
        raise FileExistsError(p)
    # Stored without pickle; fixed-width Unicode IDs and numerical arrays only.
    np.savez(p, ids=np.asarray([r["id"] for r in rows], dtype="U64"),
             block44=np.asarray(arrays[44], dtype=np.float16),
             block42=np.asarray(arrays[42], dtype=np.float16))
    if p.stat().st_size > MAX_ARCHIVE_BYTES:
        p.unlink()
        raise ValueError("output shard exceeds 20 MB")
    return p


def remaining_fits(elapsed: float, completed: int, total: int,
                   batch_timings: list[tuple[int, float]], cap_seconds: float) -> tuple[bool, float]:
    """Recompute a conservative total forecast; failed admission never cuts scope."""
    if completed < 0 or total < completed or cap_seconds <= 0:
        raise ValueError("invalid capture accounting")
    if not batch_timings or any(n <= 0 or t <= 0 for n, t in batch_timings):
        raise ValueError("a measured batch is required")
    # Per-item median of the most recent three complete batches; elapsed includes
    # model setup and all retained pilot work and never resets.
    rate = statistics.median(t / n for n, t in batch_timings[-3:])
    forecast = elapsed + (total - completed) * rate
    return 1.25 * forecast <= cap_seconds, forecast


def warmed_capture_admission(elapsed, completed, total, timings, cap_seconds):
    """Retain and charge the first batch, but measure throughput after warm-up.

    A None forecast means the retained first batch has run and warmed admission
    is pending. No clock resets, repeated items or discarded outputs occur.
    """
    if len(timings) == 1:
        if completed == total:
            return 1.25 * elapsed <= cap_seconds, elapsed
        return 1.25 * elapsed < cap_seconds, None
    return remaining_fits(elapsed, completed, total, timings[1:], cap_seconds)


def load_ready(loader, *, destination: Path, initial_staging_seconds: float,
               worker_started_monotonic: float, staging_cap_seconds: float = 900):
    """Bound runtime imports and model loading by the original staging deadline.

    This clock is nested inside the worker's continuous compute deadline. Model
    loading is part of both readiness checking and worker elapsed time, but is
    charged only once: initial staging plus total worker elapsed.
    """
    elapsed_before_load = time.monotonic() - worker_started_monotonic
    remaining = staging_cap_seconds - initial_staging_seconds - elapsed_before_load
    if remaining <= 0:
        raise ValueError("NO_FIT: no staging time remains for model readiness")
    with hard_deadline(remaining, destination / "STAGING_TIMEOUT.json"):
        if loader is None:
            from projects.g_agreement.core.model import load_target
            loader = load_target
        target = loader()
        readiness_elapsed = time.monotonic() - worker_started_monotonic
        staging_through_readiness = initial_staging_seconds + readiness_elapsed
        # Also fail closed if the timer callback was delayed by the loader.
        if staging_through_readiness > staging_cap_seconds:
            raise ValueError("NO_FIT: model readiness exceeded staging deadline")
        metadata = {"status": "MODEL_READY", "track": "C",
                    "staging_cap_seconds": staging_cap_seconds,
                    "initial_staging_seconds": initial_staging_seconds,
                    "readiness_elapsed_seconds": readiness_elapsed,
                    "staging_through_readiness_seconds": staging_through_readiness,
                    "readiness_included_in_worker_elapsed": True,
                    "accounting": "Charge initial_staging_seconds + worker elapsed_seconds once; do not add readiness_elapsed_seconds again."}
        write_json(destination / "MODEL_READY.json", metadata)
    return target, metadata


def run(args, *, loader=None, capture_fn=captured_arrays) -> dict:
    rows = read_jsonl(args.inputs)
    validate_public(rows)
    if not rows:
        raise ValueError("no gate-passing input records")
    admission = json.loads(args.admission.read_text())
    check_admission(admission, sha256(args.inputs), sha256(args.manifest))
    check_source_files(args.repo, admission["source_files"])
    required_source = {"projects/g_agreement/e73/capture.py", "projects/g_agreement/e73/custody.py",
                       "projects/g_agreement/core/model.py", "projects/g_agreement/core/config.py",
                       "projects/g_agreement/core/accounting.py"}
    if not required_source <= admission["source_files"].keys():
        raise ValueError("admission omits capture executable dependencies")
    # Operator supplies the monotonic-independent Unix start of archive staging.
    # This worker can attest elapsed staging, not provision or authorize a pod.
    staging_seconds = time.time() - args.staging_started_unix
    if not 0 <= staging_seconds <= 900:
        raise ValueError("NO_FIT: staging exceeded 900 seconds")
    if not 1 <= args.batch_size <= 7:
        raise ValueError("batch size must be 1..7 to keep output shards <=20MB")
    args.out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    # Record the disjoint pre-worker interval at the continuous worker start.
    staging_seconds = time.time() - args.staging_started_unix
    write_json(args.out / "ADMISSION.json", admission)
    files, timings, completed = [], [], 0
    readiness = None
    status, forecast = "INCOMPLETE", admission["forecast_gpu_seconds"]
    watchdog = hard_deadline(admission["gpu_seconds_cap"], args.out / "HARD_TIMEOUT.json")
    watchdog.__enter__()
    try:
        target, readiness = load_ready(loader, destination=args.out,
                                       initial_staging_seconds=staging_seconds,
                                       worker_started_monotonic=start,
                                       staging_cap_seconds=admission["staging_cap_seconds"])
        for begin in range(0, len(rows), args.batch_size):
            elapsed = time.monotonic() - start
            if elapsed >= admission["gpu_seconds_cap"]:
                status = "NO_FIT"
                break
            batch = rows[begin:begin + args.batch_size]
            before = time.monotonic()
            arrays = capture_fn(target.model, [r["input_ids"] for r in batch])
            path = save_capture_shard(args.out, len(files), batch, arrays)
            files.append(path)
            timings.append((len(batch), time.monotonic() - before))
            completed += len(batch)
            fits, forecast = warmed_capture_admission(time.monotonic() - start, completed, len(rows), timings,
                                                     admission["gpu_seconds_cap"])
            write_json(args.out / "PROGRESS.json", {"completed": completed, "total": len(rows),
                       "forecast_seconds": forecast, "elapsed_seconds": time.monotonic() - start,
                       "warmed_admission": "PENDING" if forecast is None else ("PASS" if fits else "NO_FIT"),
                       "retained_warmup_positions": timings[0][0]})
            if not fits:
                status = "NO_FIT"
                break
        else:
            status = "COMPLETE"
    finally:
        report = {"schema": "e73-capture-report-v1", "status": status, "track": "C",
                  "total": len(rows), "completed": completed, "gpu_count": 1,
                  "elapsed_seconds": time.monotonic() - start, "staging_seconds": staging_seconds,
                  "initial_staging_seconds": staging_seconds,
                  "readiness_elapsed_seconds": readiness["readiness_elapsed_seconds"] if readiness else None,
                  "staging_through_readiness_seconds": readiness["staging_through_readiness_seconds"] if readiness else None,
                  "accounting": "Charge staging_seconds + elapsed_seconds once; readiness is already inside elapsed_seconds.",
                  "forecast_seconds": forecast, "sampler_commit": admission["sampler_commit"],
                  "input_sha256": sha256(args.inputs), "bank_manifest_sha256": sha256(args.manifest),
                  "layer44": "all 256 positions; decoder block output", "layer42": "read token 255; decoder block output",
                  "dtype": "float16", "labels_present": False, "reader_outputs": 0,
                  "warmup": "First captured batch retained and fully charged; throughput uses subsequent batches; no clock reset or duplicate capture.",
                  "batch_timings": [{"count": n, "seconds": t} for n, t in timings]}
        write_json(args.out / "CAPTURE_REPORT.json", report)
        readiness_files = [args.out / "MODEL_READY.json"] if (args.out / "MODEL_READY.json").exists() else []
        seal(args.out, "CAPTURE_SEAL.json", files + readiness_files + [args.out / "CAPTURE_REPORT.json", args.out / "ADMISSION.json"],
             status=status, track="C", input_sha256=sha256(args.inputs), bank_manifest_sha256=sha256(args.manifest))
        watchdog.__exit__(None, None, None)
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "manifest", "admission", "out", "repo"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--staging-started-unix", type=float, required=True)
    p.add_argument("--batch-size", type=int, default=4)
    result = run(p.parse_args())
    print(json.dumps({k: result[k] for k in ("status", "completed", "total", "elapsed_seconds")}))
    if result["status"] != "COMPLETE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
