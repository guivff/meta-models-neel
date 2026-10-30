"""GO-gated batched native primitives for the later E73 reader stage.

I-2 must package a sealed label-free selection and admission separately before
invoking the worker CLI. No generation happens at import time.
Prompts/adapters/injections come from the existing core readers; each vector
receives exactly one greedy readout. NLA stops at its closing explanation tag.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import time
from pathlib import Path

from .custody import (MAX_GPU_SECONDS, check_go, check_admission, check_source_files, hard_deadline,
                      seal, sha256, verify_seal, write_json)

CLOSE = "</explanation>"
STAGING_POLICY = "first_reader_then_continuous_model_switch"


def explanation_closed(text: str) -> bool:
    return CLOSE in text


def install_e56_nla_hook(reader):
    """Use the exact E56/mats native hook arithmetic, including cast ordering.

    The shared core reader's older hook casts its numerator and denominator to
    bf16 separately. E56 normalizes in fp32 and then casts. Keep this local to
    E73 so the already sealed experiments and shared adapter stay unchanged.
    Reference: mats.readers.nla.NLA._hook; inspected without reader outputs.
    """
    import torch
    from projects.g_agreement.core.model import blocks
    reader._handle.remove()

    def hook(_module, _inputs, output):
        h = output[0] if isinstance(output, tuple) else output
        v = reader._vec.get("v")
        if v is None or h.shape[1] <= reader.marker:
            return output
        if v.ndim != 2 or v.shape[0] != h.shape[0]:
            raise RuntimeError("NLA vector count does not match batch")
        reader.n_hook_calls += 1
        hp = h[:, reader.marker, :]
        vu = v.to(h.device, torch.float32)
        vu = (vu / (vu.norm(dim=-1, keepdim=True) + 1e-9)).to(h.dtype)
        h[:, reader.marker, :] = hp + hp.norm(dim=-1, keepdim=True) * vu
        return output

    reader._handle = blocks(reader.model)[reader.inject_layer_idx].register_forward_hook(hook)
    reader._e73_native_hook = "E56_fp32_normalize_then_cast"
    return reader


def native_batch(reader, vectors, *, kind: str, go: dict, capture_seal_sha: str,
                 bank_manifest_sha: str) -> list[dict]:
    check_go(go, capture_seal_sha=capture_seal_sha, input_manifest_sha=bank_manifest_sha)
    if kind not in {"oracle", "nla"}:
        raise ValueError("only Oracle L44 and NLA L42 are registered")
    import torch
    if vectors.ndim != 2 or vectors.shape[1] != 5120 or not 1 <= len(vectors) <= 8:
        raise ValueError("native batches require 1..8 residual vectors")
    from projects.g_agreement.core.generate import eos_ids, pad_id, _finish
    if kind == "oracle":
        if reader.name != "olens" or reader.alpha != 16000:
            raise ValueError("requires the unchanged native Oracle adapter")
        from projects.g_agreement.core.config import OLENS_PROMPT
        if reader.prompt != OLENS_PROMPT:
            raise ValueError("Oracle prompt changed")
        model, tok = reader.target.model, reader.target.tokenizer
        ids, marker, _, _ = reader.carrier(44)
        device = next(model.parameters()).device
        cap = 128
        with torch.inference_mode():
            x = torch.tensor([ids] * len(vectors), device=device)
            emb = model.get_input_embeddings()(x).clone()
            vec = torch.as_tensor(vectors, device=device).float()
            emb[:, marker] = (16000 * vec / vec.norm(dim=-1, keepdim=True).clamp_min(1e-9)).to(emb.dtype)
            output = model.generate(inputs_embeds=emb, attention_mask=torch.ones_like(x),
                                    do_sample=False, num_beams=1, num_return_sequences=1,
                                    max_new_tokens=cap, pad_token_id=pad_id(tok))
        new_tokens = output
    else:
        if (reader.name != "nla" or reader.inject_layer_idx != 1
                or getattr(reader, "_e73_native_hook", None) != "E56_fp32_normalize_then_cast"):
            raise ValueError("requires unchanged native NLA injection")
        from transformers import StoppingCriteria, StoppingCriteriaList
        model, tok, ids, device = reader.model, reader.tokenizer, reader.ids, reader.device
        cap = 512

        class ClosedExplanation(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                texts = tok.batch_decode(input_ids[:, len(ids):], skip_special_tokens=True)
                return torch.tensor([explanation_closed(t) for t in texts],
                                    device=input_ids.device, dtype=torch.bool)

        previous_calls = reader.n_hook_calls
        reader._vec["v"] = torch.as_tensor(vectors, device=device).float()
        try:
            with torch.inference_mode():
                x = torch.tensor([ids] * len(vectors), device=device)
                output = model.generate(input_ids=x, attention_mask=torch.ones_like(x),
                                        do_sample=False, num_beams=1, num_return_sequences=1,
                                        max_new_tokens=cap, pad_token_id=pad_id(tok),
                                        stopping_criteria=StoppingCriteriaList([ClosedExplanation()]))
                new_tokens = output[:, len(ids):]
        finally:
            reader._vec["v"] = None
        if reader.n_hook_calls <= previous_calls:
            raise ValueError("NLA prefill injection did not fire")
    records = []
    for token_row in new_tokens.tolist():
        cut, reason = _finish(token_row, cap, eos_ids(tok, model))
        text = tok.decode(cut, skip_special_tokens=True)
        closed = explanation_closed(text) if kind == "nla" else None
        if closed:
            reason = "explanation_stop"
        # Each row may stop before its batch-mates; remove only generation padding
        # via _finish, retaining the generated text verbatim through its close tag.
        records.append({"raw_output": text, "new_token_ids": cut, "n_new_tokens": len(cut),
                        "reader": kind, "capture_layer": 44 if kind == "oracle" else 42,
                        "max_new_tokens": cap, "greedy": True, "finish_reason": reason,
                        "explanation_closed": closed, "truncated": not closed if kind == "nla" else None})
    if len(records) != len(vectors):
        raise ValueError("one readout per position required")
    return records


def validate_reader_shard(data) -> tuple[list[str], dict]:
    import numpy as np
    from .custody import ID_RE
    if set(data.files) != {"ids", "block44", "block42"}:
        raise ValueError("reader inputs may contain only opaque IDs and residuals")
    ids = data["ids"].tolist()
    if not ids or len(set(ids)) != len(ids) or any(not isinstance(i, str) or not ID_RE.fullmatch(i) for i in ids):
        raise ValueError("invalid or duplicate reader IDs")
    vectors = {44: data["block44"], 42: data["block42"]}
    if any(x.shape != (len(ids), 5120) or x.dtype != np.float16 or not np.isfinite(x).all() for x in vectors.values()):
        raise ValueError("reader residual shape/dtype/finite check failed")
    return ids, vectors


def warmed_native_admission(elapsed, completed, total, timings, prior_rates,
                            setup_remaining, cap_seconds, active_reader):
    """Retain/charge cold batches and estimate rates only from warmed batches.

    The first batch of each reader is retained exactly once. Its cost remains in
    the uninterrupted elapsed clock, but it is not multiplied over later items.
    A future reader without measurements retains its explicit admitted prior.
    """
    if active_reader not in ("oracle", "nla") or elapsed < 0 or total < 1 or cap_seconds <= 0 or setup_remaining < 0:
        raise ValueError("invalid native forecast accounting")
    states, rate_used, remaining = {}, {}, float(setup_remaining)
    for kind in ("oracle", "nla"):
        if not 0 <= completed[kind] <= total or sum(n for n, _ in timings[kind]) != completed[kind]:
            raise ValueError("native timing and completed-position counts disagree")
        if any(n <= 0 or not math.isfinite(seconds) or seconds <= 0 for n, seconds in timings[kind]):
            raise ValueError("invalid native batch timing")
        if not math.isfinite(prior_rates[kind]) or prior_rates[kind] <= 0:
            raise ValueError("unmeasured native paths need positive admitted rates")
        warmed = timings[kind][1:]
        rate = statistics.median(seconds / n for n, seconds in warmed[-3:]) if warmed else prior_rates[kind]
        rate_used[kind] = rate
        states[kind] = ("MEASURED" if warmed else "COMPLETE_NO_WARMED_RATE" if completed[kind] == total
                        else "PENDING" if timings[kind] else "NOT_STARTED")
        # A partial final batch can cost a full generation batch. Account for
        # that conservatively instead of assuming fractional batch throughput.
        if kind != active_reader or states[kind] != "PENDING":
            remaining += math.ceil((total - completed[kind]) / 8) * 8 * rate
    if states[active_reader] == "PENDING":
        # One retained cold batch may be followed by the first warmed batch.
        # Reserve every other known path and setup while this rate is unknown.
        return 1.25 * (elapsed + remaining) < cap_seconds, None, states, rate_used
    forecast = elapsed + remaining
    return 1.25 * forecast <= cap_seconds, forecast, states, rate_used


def _load_reader(kind):
    # Runtime imports are deliberately inside the first-reader staging timer.
    from projects.g_agreement.core.model import load_target
    from projects.g_agreement.core.readers import OLensReader, NLAReader
    if kind == "oracle":
        return OLensReader(max_new_tokens=128, sampling={"do_sample": False}).bind(load_target())
    return install_e56_nla_hook(NLAReader(max_new_tokens=512, sampling={"do_sample": False}).bind())


def _unload_reader(kind, reader):
    if kind == "oracle":
        from projects.g_agreement.core.model import unload
        unload(reader.target)
    else:
        reader.unload()


def load_native_ready(kind, loader, *, destination, initial_staging_seconds,
                      worker_started_monotonic, staging_cap_seconds=900):
    """First readiness shares the staging deadline; later switch never resets it.

    Both phases remain inside the caller's one uninterrupted compute watchdog.
    Guiv/I-2 authorised the later NLA switch as compute, with setup reserved in F.
    """
    before = time.monotonic()
    if kind == "oracle":
        remaining = staging_cap_seconds - initial_staging_seconds - (before - worker_started_monotonic)
        if remaining <= 0:
            raise ValueError("NO_FIT: no staging time remains for first-reader readiness")
        with hard_deadline(remaining, destination / "STAGING_TIMEOUT.json"):
            reader = loader(kind)
            ready_elapsed = time.monotonic() - worker_started_monotonic
            if initial_staging_seconds + ready_elapsed > staging_cap_seconds:
                raise ValueError("NO_FIT: first-reader readiness exceeded staging deadline")
    elif kind == "nla":
        reader = loader(kind)
        ready_elapsed = time.monotonic() - worker_started_monotonic
    else:
        raise ValueError("unknown reader readiness phase")
    metadata = {"status": "MODEL_READY", "reader": kind, "track": "C",
                "staging_readiness_policy": STAGING_POLICY,
                "phase": "INITIAL_READINESS" if kind == "oracle" else "CONTINUOUS_MODEL_SWITCH",
                "initial_staging_seconds": initial_staging_seconds,
                "model_load_seconds": time.monotonic() - before,
                "worker_elapsed_at_readiness_seconds": ready_elapsed,
                "staging_deadline_applies": kind == "oracle",
                "staging_through_first_readiness_seconds": initial_staging_seconds + ready_elapsed if kind == "oracle" else None,
                "new_staging_allowance_seconds": 0,
                "accounting": "Model loading is already included in the uninterrupted worker elapsed clock; do not add it again."}
    write_json(destination / ("MODEL_READY_" + kind + ".json"), metadata)
    return reader, metadata


def failure_diagnostics(error, phase):
    """Public operational metadata; raw exception text stays in private stderr.

    Redacting selected URL/key patterns cannot guarantee that an arbitrary
    exception message is safe. Emit only fixed category text and known exception
    names. The original exception is re-raised unchanged for the controller's
    private worker.log, which must be retrieved before stopping the pod.
    """
    known_types = {"Exception", "RuntimeError", "ValueError", "TypeError", "AttributeError",
                   "KeyError", "IndexError", "ImportError", "ModuleNotFoundError", "OSError",
                   "FileNotFoundError", "PermissionError", "TimeoutError", "ConnectionError",
                   "MemoryError", "OutOfMemoryError", "KeyboardInterrupt", "SystemExit"}
    name = type(error).__name__
    kind = name if name in known_types else "ExternalError"
    try:
        hint = str(error)[:4096].lower()
    except BaseException:
        hint = ""
    if "tensors matched a parameter" in hint:
        code, message = "ADAPTER_KEY_MATCH_FAILURE", "Adapter key matching failed during initialization."
    elif "is inert (max" in hint:
        code, message = "ADAPTER_LIVENESS_FAILURE", "The adapter liveness check failed."
    elif "no enclosed ideograph" in hint or "marker not well formed" in hint:
        code, message = "CARRIER_MARKER_FAILURE", "The fixed carrier marker check failed."
    elif kind in {"ImportError", "ModuleNotFoundError"}:
        code, message = "DEPENDENCY_IMPORT_FAILURE", "A runtime dependency could not be imported."
    elif kind in {"MemoryError", "OutOfMemoryError"} or "out of memory" in hint:
        code, message = "MEMORY_ALLOCATION_FAILURE", "A memory allocation failed."
    elif kind == "FileNotFoundError":
        code, message = "FILE_UNAVAILABLE", "A required file was unavailable."
    elif kind == "PermissionError":
        code, message = "FILE_ACCESS_FAILURE", "File access was denied."
    elif kind in {"TimeoutError", "ConnectionError"}:
        code, message = "CONNECTION_OR_TIMEOUT_FAILURE", "An operation timed out or a connection failed."
    else:
        code, message = "UNCLASSIFIED_OPERATIONAL_FAILURE", "An operation failed; inspect the private operator traceback."
    safe_phases = {"initialization", "complete", "no_fit"} | {
        reader + "_" + step for reader in ("oracle", "nla")
        for step in ("initialization", "output_open", "generation", "output_write", "forecast", "unload")}
    return {"phase": phase if phase in safe_phases else "unknown", "exception_type": kind,
            "message_code": code, "message": message,
            "traceback_location": "operator_private_worker.log_from_stderr"}


def run(args, *, reader_loader=_load_reader, reader_unloader=_unload_reader, batch_fn=native_batch):
    """One previously prepared shard, both readers, sealed without judging."""
    import numpy as np
    index = json.loads(args.index.read_text())
    if index.get("schema") != "e73-reader-inputs-v1" or index.get("labels_present") is not False:
        raise ValueError("requires a frozen label-free reader input index")
    shard = next((s for s in index["shards"] if s["file"] == args.inputs.name), None)
    if shard is None or shard["sha256"] != sha256(args.inputs):
        raise ValueError("reader input shard differs from frozen index")
    admission_bytes = args.admission.read_bytes()
    admission = json.loads(admission_bytes)
    check_admission(admission, sha256(args.inputs), index["bank_manifest_sha256"])
    retrieval = admission.get("retrieval_allowance_seconds")
    if type(retrieval) not in (int, float) or not math.isfinite(retrieval) or retrieval < 0:
        raise ValueError("admission requires finite nonnegative retrieval_allowance_seconds")
    if (admission["prior_track_gpu_seconds"] + admission["gpu_seconds_cap"]
            + admission["staging_cap_seconds"] + retrieval > MAX_GPU_SECONDS):
        raise ValueError("NO_FIT: native compute, staging and retrieval reservations exceed aggregate E73 cap")
    # Retrieval is enforced externally by I-2's sidecar/provider stop. Reserving
    # it here does not extend or reset the worker's continuous compute watchdog.
    required = {"projects/g_agreement/e73/native.py", "projects/g_agreement/e73/custody.py",
                "projects/g_agreement/core/config.py", "projects/g_agreement/core/model.py",
                "projects/g_agreement/core/readers.py", "projects/g_agreement/core/generate.py",
                "projects/g_agreement/core/accounting.py"}
    if not required <= admission["source_files"].keys():
        raise ValueError("admission omits native executable dependencies")
    check_source_files(args.repo, admission["source_files"])
    if (not isinstance(admission.get("run_id"), str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", admission["run_id"])
            or admission.get("run_kind") != "real"
            or not re.fullmatch(r"[0-9a-f]{40}", str(admission.get("runtime_commit", "")))):
        raise ValueError("admission lacks valid operator run/runtime provenance")
    source_map_sha = hashlib.sha256(json.dumps(admission["source_files"], sort_keys=True,
                                               separators=(",", ":")).encode()).hexdigest()
    if admission.get("code_sha256") != source_map_sha:
        raise ValueError("operator code SHA differs from canonical source map")
    go_bytes = args.go.read_bytes()
    go = json.loads(go_bytes)
    # The index lists every original sealed capture and every selected shard, and
    # is hashed before forecast/GO. No state/value information is on this pod.
    check_go(go, capture_seal_sha=sha256(args.index), input_manifest_sha=index["bank_manifest_sha256"])
    proof = json.loads(args.forecast_proof.read_text())
    if (proof.get("schema") != "e73-forecast-proof-v1" or proof.get("verified_by") != "I-2"
            or proof.get("commit") != go["jforecast_commit"]
            or proof.get("artifact_sha256") != go["jforecast_sha256"]):
        raise ValueError("GO lacks a matching CPU-verified forecast proof")
    rates = admission.get("native_seconds_per_item", {})
    setup = admission.get("nla_setup_seconds", 0)
    if (any(k not in rates or type(rates[k]) not in (float, int) or not math.isfinite(rates[k]) or rates[k] <= 0
            for k in ("oracle", "nla")) or type(setup) not in (float, int) or not math.isfinite(setup) or setup <= 0):
        raise ValueError("admission requires both native path forecasts and NLA setup")
    if admission.get("staging_readiness_policy") != STAGING_POLICY:
        raise ValueError("admission must explicitly bind the first-reader/continuous-switch readiness policy")
    staging_seconds = time.time() - args.staging_started_unix
    if not 0 <= staging_seconds <= 900:
        raise ValueError("NO_FIT: staging exceeded 900 seconds")
    with np.load(args.inputs, allow_pickle=False) as data:
        ids, vectors = validate_reader_shard(data)
    if shard.get("count") != len(ids):
        raise ValueError("reader shard count differs from frozen index")
    args.out.mkdir(parents=True, exist_ok=False)
    start, status = time.monotonic(), "INCOMPLETE"
    staging_seconds = time.time() - args.staging_started_unix
    (args.out / "ADMISSION.json").write_bytes(admission_bytes)
    (args.out / "GO.json").write_bytes(go_bytes)
    timings, completed, files, readiness = {"oracle": [], "nla": []}, {"oracle": 0, "nla": 0}, [], {}
    phase, failure = "initialization", None
    watchdog = hard_deadline(admission["gpu_seconds_cap"] - (time.monotonic() - start),
                             args.out / "HARD_TIMEOUT.json")
    watchdog.__enter__()
    try:
        for kind, layer in (("oracle", 44), ("nla", 42)):
            phase = kind + "_initialization"
            reader, ready = load_native_ready(kind, reader_loader, destination=args.out,
                                              initial_staging_seconds=staging_seconds,
                                              worker_started_monotonic=start,
                                              staging_cap_seconds=admission["staging_cap_seconds"])
            readiness[kind] = ready
            files.append(args.out / ("MODEL_READY_" + kind + ".json"))
            output_path = args.out / (kind + ".jsonl")
            files.append(output_path)
            phase = kind + "_output_open"
            with output_path.open("x") as stream:
                for begin in range(0, len(ids), 8):
                    before = time.monotonic()
                    phase = kind + "_generation"
                    batch = batch_fn(reader, vectors[layer][begin:begin + 8], kind=kind, go=go,
                                     capture_seal_sha=sha256(args.index), bank_manifest_sha=index["bank_manifest_sha256"])
                    if len(batch) != len(ids[begin:begin + 8]):
                        raise ValueError("native batch returned incomplete output coverage")
                    phase = kind + "_output_write"
                    for uid, record in zip(ids[begin:begin + 8], batch):
                        stream.write(json.dumps({"id": uid, **record}, ensure_ascii=False) + "\n")
                    stream.flush()
                    completed[kind] += len(batch)
                    timings[kind].append((len(batch), time.monotonic() - before))
                    setup_remaining = admission.get("nla_setup_seconds", 0) if kind == "oracle" else 0
                    phase = kind + "_forecast"
                    fits, forecast, states, measured_rates = warmed_native_admission(
                        time.monotonic() - start, completed, len(ids), timings, rates,
                        setup_remaining, admission["gpu_seconds_cap"], kind)
                    write_json(args.out / "PROGRESS.json", {"completed": completed, "forecast_seconds": forecast,
                               "warmed_admission": "NO_FIT" if not fits else ("PENDING" if forecast is None else "PASS"),
                               "reader_rate_status": states, "rate_seconds_per_item": measured_rates,
                               "elapsed_seconds": time.monotonic() - start})
                    if not fits:
                        status = "NO_FIT"
                        break
            phase = kind + "_unload"
            reader_unloader(kind, reader)
            if status == "NO_FIT":
                phase = "no_fit"
                break
        else:
            status = "COMPLETE"
            phase = "complete"
    except BaseException as error:
        failure = failure_diagnostics(error, phase)
        raise
    finally:
        report = {"schema": "e73-reader-report-v1", "track": "C", "status": status,
                  "operational_phase": phase, "failure_diagnostics": failure,
                  "run_id": admission["run_id"], "run_kind": admission["run_kind"],
                  "runtime_commit": admission["runtime_commit"], "code_sha256": admission["code_sha256"],
                  "completed": completed, "total_per_reader": len(ids), "elapsed_seconds": time.monotonic() - start,
                  "staging_seconds": staging_seconds, "initial_staging_seconds": staging_seconds,
                  "staging_readiness_policy": STAGING_POLICY, "model_readiness": readiness,
                  "accounting": "Charge staging_seconds + elapsed_seconds once; both model loads, retained warmups and model switching are inside elapsed_seconds.",
                  "batch_timings": {k: [{"count": n, "seconds": t} for n, t in v] for k, v in timings.items()},
                  "retained_cold_batches": {k: {"count": v[0][0], "seconds": v[0][1]} if v else None for k, v in timings.items()},
                  "warmup_policy": "First batch per reader retained once and fully charged; throughput uses only subsequent batches. No clock reset or duplicate readout.",
                  "input_sha256": sha256(args.inputs), "reader_index_sha256": sha256(args.index),
                  "jforecast_commit": go["jforecast_commit"], "jforecast_sha256": go["jforecast_sha256"],
                  "judging": "SEALED_AWAITING_GUIV_AUTHORIZATION"}
        write_json(args.out / "READER_REPORT.json", report)
        seal(args.out, "READER_SEAL.json", [p for p in files if p.exists()] +
             [args.out / "READER_REPORT.json", args.out / "ADMISSION.json", args.out / "GO.json"],
             status=status, track="C", reader_outputs_unopened=True)
        watchdog.__exit__(None, None, None)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "index", "admission", "go", "forecast-proof", "out", "repo"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--staging-started-unix", type=float, required=True)
    result = run(p.parse_args())
    print(json.dumps({k: result[k] for k in ("status", "completed", "total_per_reader", "elapsed_seconds")}))
    if result["status"] != "COMPLETE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
