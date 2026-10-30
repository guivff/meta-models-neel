"""2026-10-25 E29 integrator worker: base text scoring inside one 1,800 GPU-second budget (§143).

Setup, asset verification/loading, synthetic warmup, both cohorts and sealing all
consume the same allowance. A final 30 seconds is reserved inside that allowance
for retrieval. No model downloads, adapters, injected activations, or reader code.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import time

ROOT = Path(__file__).resolve().parents[4]
E25_RELATIVE = "results/g_agreement/understand/e25/worker.py"
SELF_RELATIVE = "results/g_agreement/understand/e29/worker.py"
E25_SHA256 = "246936d7131b8af4f87aae8bff9415228c544d2b25f5d2e8292ef8004f17b039"
FRAME = "item text + one newline + verbatim frozen candidate"
SCORING = "mean_per_candidate_token_logprob"
TOTAL_SECONDS = 1800
RETRIEVAL_SECONDS = 30
COHORT_NAMES = ("w12", "suraj_exp13")


def load_e25():
    import hashlib
    path = ROOT / E25_RELATIVE
    if hashlib.sha256(path.read_bytes()).hexdigest() != E25_SHA256:
        raise ValueError("E25 scoring implementation changed")
    spec = importlib.util.spec_from_file_location("e29_pinned_e25_worker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


E25 = load_e25()
MODEL, REVISION, TOKENIZER_SHA = E25.MODEL, E25.REVISION, E25.TOKENIZER_SHA
sha, read, dump = E25.sha, E25.read, E25.dump
# These are the original callable objects, without a scoring or encoding wrapper.
encode_frame, score_batch = E25.encode_frame, E25.score_batch


def is_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def is_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_plan(plan):
    if plan.get("experiment") != "E29" or plan.get("status") != "READY":
        raise ValueError("E29 plan must be READY; pending W12 freeze cannot launch")
    if plan.get("batch_size") != 8 or isinstance(plan.get("batch_size"), bool):
        raise ValueError("E29 frozen batch size is eight")
    if plan.get("frame") != FRAME or plan.get("scoring") != SCORING:
        raise ValueError("E25 frame and mean-token score are immutable")
    expected_model = {"model_id": MODEL, "revision": REVISION, "adapter": None, "injection": None}
    if plan.get("model") != expected_model:
        raise ValueError("exact E25 base model without adapter or injection required")
    sources = plan.get("source_files", {})
    if sources.get(E25_RELATIVE) != E25_SHA256 or not is_hash(sources.get(SELF_RELATIVE)):
        raise ValueError("plan must pin E25 and E29 workers")
    for name, digest in sources.items():
        if not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts or not is_hash(digest):
            raise ValueError("unsafe or incomplete source pin")
    cohorts = plan.get("cohorts")
    if not isinstance(cohorts, list) or [c.get("name") for c in cohorts] != list(COHORT_NAMES):
        raise ValueError("complete ordered W12 then Suraj cohorts required")
    for cohort in cohorts:
        primary = cohort["name"] == "w12"
        if cohort.get("blind") is not primary:
            raise ValueError("W12 must be blind; Suraj must be explicitly non-blind")
        phrasing_count = 2 if primary else 1
        if cohort.get("phrasing_count") != phrasing_count:
            raise ValueError("wrong frozen cohort phrasing count")
        if not is_hash(cohort.get("input_seal_sha256")) or not is_hash(cohort.get("labels_sha256")):
            raise ValueError("cohort input seal and withheld label hashes required")
        if not isinstance(cohort.get("freeze"), dict) or not cohort["freeze"]:
            raise ValueError("cohort frozen-source provenance required")
        rows = cohort.get("rows")
        items = cohort.get("items")
        if not isinstance(rows, list) or not rows or not all(isinstance(r, str) and r for r in rows) or len(set(rows)) != len(rows):
            raise ValueError("nonempty distinct cohort rows required")
        if not primary and len(rows) != 7:
            raise ValueError("all seven Suraj exp13 rows required")
        if primary and len(rows) != 6:
            raise ValueError("all six frozen W12 rows required")
        if not isinstance(items, list) or not items or any(not isinstance(r, dict) or set(r) != {"id", "feature"} for r in items):
            raise ValueError("exact frozen item identity list required")
        if any(not isinstance(r["id"], str) or not r["id"] or r["feature"] not in rows for r in items):
            raise ValueError("invalid item identity or row")
        if len({r["id"] for r in items}) != len(items) or {r["feature"] for r in items} != set(rows):
            raise ValueError("duplicate items or uncovered rows")
        expected_per_row = 84 if primary else 160
        if any(sum(i["feature"] == row for i in items) != expected_per_row for row in rows):
            raise ValueError("registered per-row population required: W12 84; Suraj select160")
        if cohort.get("expected_scores") != len(items) * phrasing_count * 2:
            raise ValueError("complete cohort score count required")


def validate_assignment(assignment, plan, plan_path, now):
    validate_plan(plan)
    if (assignment.get("issuer") != "integrator" or assignment.get("experiment") != "E29"
            or not assignment.get("pod_id") or assignment["pod_id"] != os.environ.get("RUNPOD_POD_ID")
            or assignment.get("plan_sha256") != sha(plan_path)
            or assignment.get("source_files") != plan["source_files"]):
        raise ValueError("exact integrator assignment and pod identity required")
    required = ("source_published", "inputs_published", "registration_published", "external_hardstop_verified",
                "w12_freeze_verified", "w12_readers_not_scored", "w12_reader_hold_enforced")
    for flag in required:
        if assignment.get(flag) is not True:
            raise ValueError("missing " + flag)
    if (assignment.get("gpu_count") != 1 or isinstance(assignment.get("gpu_count"), bool)
            or assignment.get("total_gpu_seconds") != TOTAL_SECONDS
            or assignment.get("retrieval_reserve_seconds") != RETRIEVAL_SECONDS
            or assignment.get("retry_authorized") is not False):
        raise ValueError("one GPU, cumulative1800, internal30 reserve, no retries required")
    if "setup_allowance_seconds" in assignment or "science_ceiling_seconds" in assignment:
        raise ValueError("E29 has no separate setup or science allowance")
    start, previous, deadline = (assignment.get(k) for k in ("budget_start_epoch", "previous_gpu_seconds", "deadline_epoch"))
    if not all(is_number(v) for v in (start, previous, deadline, now)):
        raise ValueError("finite budget clocks required")
    if start > now or previous < 0 or previous >= TOTAL_SECONDS:
        raise ValueError("future budget start or invalid carried consumption")
    if deadline > start + TOTAL_SECONDS - previous:
        raise ValueError("deadline resets or exceeds cumulative E29 allowance")
    if deadline - RETRIEVAL_SECONDS <= now:
        raise ValueError("no compute time before internal retrieval reserve")
    if not is_hash(assignment.get("assets_manifest_sha256")):
        raise ValueError("assignment must bind the complete local asset manifest")


class CumulativeBudget:
    """Wall-clock accounting cannot gain time if the host clock moves backwards."""
    def __init__(self, assignment, *, wall=time.time, monotonic=time.monotonic, arm_alarm=False):
        self.assignment = assignment
        self.wall, self.monotonic, self.arm_alarm = wall, monotonic, arm_alarm
        self.entry_wall, self.entry_mono = wall(), monotonic()
        self.deadline = min(assignment["deadline_epoch"], assignment["budget_start_epoch"] + TOTAL_SECONDS - assignment["previous_gpu_seconds"])
        self.compute_deadline = self.deadline - RETRIEVAL_SECONDS

    def now(self):
        return max(self.wall(), self.entry_wall + self.monotonic() - self.entry_mono)

    def check(self):
        remaining = self.compute_deadline - self.now()
        if remaining <= 0:
            raise TimeoutError("E29 cumulative budget exhausted; retrieval reserve preserved")
        if self.arm_alarm:
            signal.setitimer(signal.ITIMER_REAL, remaining)
        return remaining

    def snapshot(self):
        now = self.now()
        a = self.assignment
        return {"budget_start_epoch": a["budget_start_epoch"], "previous_gpu_seconds": a["previous_gpu_seconds"],
                "elapsed_this_allocation_seconds": now - a["budget_start_epoch"],
                "cumulative_gpu_seconds": a["previous_gpu_seconds"] + now - a["budget_start_epoch"],
                "compute_deadline_epoch": self.compute_deadline, "provider_deadline_epoch": self.deadline,
                "retrieval_reserve_seconds": RETRIEVAL_SECONDS, "total_allowance_gpu_seconds": TOTAL_SECONDS}


def verify_sources(plan):
    for name, expected in plan["source_files"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("source changed: " + name)


def verify_cohort(stage, cohort):
    stage = Path(stage)
    if set(p.name for p in stage.iterdir()) != {"items.jsonl", "candidates.json", "INPUT_SEAL.json"}:
        raise ValueError("cohort stage contains unexpected files; labels and activations forbidden")
    if sha(stage / "INPUT_SEAL.json") != cohort["input_seal_sha256"]:
        raise ValueError("cohort input seal identity changed")
    seal = read(stage / "INPUT_SEAL.json")
    if set(seal.get("files", {})) != {"items.jsonl", "candidates.json"}:
        raise ValueError("cohort seal must bind only texts and candidates")
    for name, digest in seal["files"].items():
        if sha(stage / name) != digest:
            raise ValueError("cohort payload changed: " + name)
    items = [json.loads(line) for line in (stage / "items.jsonl").read_text().splitlines()]
    if any(not isinstance(r, dict) or set(r) != {"id", "feature", "text"} or not isinstance(r["text"], str) or not r["text"] for r in items):
        raise ValueError("only nonempty exact item text and identity fields allowed")
    if [{"id": r["id"], "feature": r["feature"]} for r in items] != cohort["items"]:
        raise ValueError("cohort item identities or order changed")
    candidates = read(stage / "candidates.json")
    if set(candidates) != set(cohort["rows"]):
        raise ValueError("cohort candidate rows changed")
    for pairs in candidates.values():
        if not isinstance(pairs, list) or len(pairs) != cohort["phrasing_count"]:
            raise ValueError("frozen cohort phrasing count changed")
        if any(not isinstance(p, list) or len(p) != 2 or not all(isinstance(c, str) and c for c in p) for p in pairs):
            raise ValueError("candidate pair must contain literal nonempty A and B strings")
    return items, candidates


def verify_stage(stage, plan):
    stage = Path(stage)
    if set(p.name for p in stage.iterdir()) != set(COHORT_NAMES) or not all((stage / n).is_dir() for n in COHORT_NAMES):
        raise ValueError("stage requires only complete W12 and Suraj cohort directories")
    return {c["name"]: verify_cohort(stage / c["name"], c) for c in plan["cohorts"]}


def verify_assets(path, assignment, budget):
    if sha(path) != assignment["assets_manifest_sha256"]:
        raise ValueError("asset manifest identity mismatch")
    assets = read(path)
    if assets.get("model_id") != MODEL or assets.get("revision") != REVISION:
        raise ValueError("wrong base Qwen checkpoint")
    if assets.get("adapter") is not None or assets.get("injection") is not None:
        raise ValueError("adapters and injection forbidden")
    model_path = Path(assets["model_path"])
    if (model_path / "adapter_config.json").exists():
        raise ValueError("adapter directory supplied")
    files = assets.get("files", {})
    index = read(model_path / "model.safetensors.index.json")
    required = set(index["weight_map"].values()) | {"model.safetensors.index.json", "config.json", "tokenizer.json", "tokenizer_config.json"}
    if not required <= set(files) or any(Path(n).is_absolute() or ".." in Path(n).parts or not is_hash(h) for n, h in files.items()):
        raise ValueError("incomplete or unsafe asset manifest")
    for name, digest in files.items():
        budget.check()
        if sha(model_path / name) != digest:
            raise ValueError("model asset changed: " + name)
    if sha(model_path / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("wrong E25/W1 tokenizer")
    budget.check()
    return assets, model_path


def make_frames(tokenizer, items, candidates):
    frames = []
    for item in items:
        for phrasing, pair in enumerate(candidates[item["feature"]]):
            for label, candidate in zip(("A", "B"), pair):
                frames.append({"id": item["id"], "feature": item["feature"], "phrasing": phrasing, "candidate": label,
                               **encode_frame(tokenizer, item["text"], candidate)})
    return frames


def context_limit(config):
    text_config = getattr(config, "text_config", config)
    limit = getattr(text_config, "max_position_embeddings", None)
    if type(limit) is not int or limit <= 0:
        raise ValueError("base model text context limit unavailable")
    return limit


def synthetic_worst_batch(all_frames, token_id, batch_size=8):
    """Longest-input/largest-suffix synthetic shape; never score a real item in warmup."""
    longest = max(len(f["ids"]) for f in all_frames)
    suffix = max(f["token_count"] for f in all_frames)
    if suffix >= longest or not isinstance(token_id, int) or isinstance(token_id, bool):
        raise ValueError("invalid synthetic timing shape")
    frame = {"ids": [token_id] * longest, "candidate_start": longest - suffix, "token_count": suffix}
    return [frame.copy() for _ in range(batch_size)]


def forecast_gate(unit_seconds, cohort_frame_counts, budget_snapshot, now, batch_size=8):
    if len(unit_seconds) != 3 or any(not is_number(s) or s <= 0 for s in unit_seconds):
        raise ValueError("three positive warmed full-batch measurements required")
    if set(cohort_frame_counts) != set(COHORT_NAMES) or any(type(n) is not int or n <= 0 for n in cohort_frame_counts.values()):
        raise ValueError("forecast must include complete both-bank work")
    batches = {name: math.ceil(cohort_frame_counts[name] / batch_size) for name in COHORT_NAMES}
    remaining = max(unit_seconds) * sum(batches.values())
    guarded = 1.5 * remaining
    deadline = budget_snapshot["compute_deadline_epoch"]
    return {"status": "FIT" if now + guarded <= deadline else "NO_FIT", "unit_seconds": unit_seconds,
            "timing_unit": "batch8 synthetic input at both cohorts' maximum sequence and candidate lengths",
            "unit_aggregation": "maximum of three warmed repeats", "remaining_batches": batches,
            "remaining_seconds_estimate": remaining, "forecast_multiplier": 1.5, "guarded_remaining_seconds": guarded,
            "synthetic_only": True, "scientific_scores_before_forecast": 0,
            "budget": budget_snapshot, "forecast_epoch": now}


def seal_cohort(out, cohort, records, provenance, plan_sha):
    expected = {(i["id"], p, c) for i in cohort["items"] for p in range(cohort["phrasing_count"]) for c in ("A", "B")}
    observed = {(r["id"], r["phrasing"], r["candidate"]) for r in records}
    by_id = {i["id"]: i["feature"] for i in cohort["items"]}
    if len(records) != cohort["expected_scores"] or observed != expected or len(observed) != len(records):
        raise ValueError("incomplete or duplicated cohort score grid")
    if any(r["feature"] != by_id[r["id"]] or type(r["token_count"]) is not int or r["token_count"] <= 0
           or not is_number(r["mean_logprob"]) or r["mean_logprob"] > 0 for r in records):
        raise ValueError("invalid cohort score identity, count or probability")
    out.mkdir(exist_ok=False)
    with (out / "scores.jsonl").open("x") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    dump(out / "provenance.json", provenance)
    dump(out / "SCORE_SEAL.json", {"schema_version": 1, "complete": True, "cohort": cohort["name"], "plan_sha256": plan_sha,
                                 "files": {name: sha(out / name) for name in ("scores.jsonl", "provenance.json")}})


def run(args):
    plan_path, stage, out = Path(args.plan), Path(args.stage), Path(args.out)
    plan, assignment = read(plan_path), read(args.assignment)
    validate_assignment(assignment, plan, plan_path, time.time())
    def timeout(*_):
        raise TimeoutError("E29 cumulative deadline reached; no retry")
    signal.signal(signal.SIGALRM, timeout)
    budget = CumulativeBudget(assignment, arm_alarm=True)
    phase = "admission"
    out.mkdir(parents=True, exist_ok=False)
    try:
        budget.check()
        dump(out / "CUMULATIVE_CLOCK.json", {**budget.snapshot(), "assignment_sha256": sha(args.assignment),
                                            "plan_sha256": sha(plan_path), "all_setup_and_warmup_included": True})
        verify_sources(plan)
        cohorts = verify_stage(stage, plan)
        assets, model_path = verify_assets(args.assets, assignment, budget)
        phase = "setup"
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        budget.check()
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise ValueError("exactly one integrator-assigned CUDA device required")
        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        budget.check()
        model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, dtype=torch.bfloat16, device_map="cuda").eval()
        if hasattr(model, "peft_config"):
            raise ValueError("unexpected adapted model")
        budget.check()
        frames = {c["name"]: make_frames(tokenizer, *cohorts[c["name"]]) for c in plan["cohorts"]}
        for c in plan["cohorts"]:
            if len(frames[c["name"]]) != c["expected_scores"]:
                raise ValueError("full cohort frame count changed")
        all_frames = [f for name in COHORT_NAMES for f in frames[name]]
        if max(len(f["ids"]) for f in all_frames) > context_limit(model.config):
            raise ValueError("frozen text exceeds base context; no truncation allowed")
        pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
        warm = synthetic_worst_batch(all_frames, tokenizer.eos_token_id)
        phase = "synthetic_warmup"
        budget.check()
        score_batch(model, warm, pad)
        torch.cuda.synchronize()
        timings = []
        for _ in range(3):
            budget.check()
            torch.cuda.synchronize()
            start = time.monotonic()
            score_batch(model, warm, pad)
            torch.cuda.synchronize()
            timings.append(time.monotonic() - start)
            budget.check()
        forecast = forecast_gate(timings, {n: len(frames[n]) for n in COHORT_NAMES}, budget.snapshot(), budget.now())
        dump(out / "FORECAST.json", forecast)
        if forecast["status"] != "FIT":
            raise ValueError("NO_FIT; no scope reduction, retry or separate setup allowance")
        common = {"date": "2026-10-25", "experiment": "E29", "model_id": MODEL, "revision": REVISION,
                  "adapter": None, "injection": None, "labels_joined": False, "frame": FRAME, "scoring": SCORING,
                  "assignment_sha256": sha(args.assignment), "plan_sha256": sha(plan_path),
                  "assets_manifest_sha256": sha(args.assets), "source_files": plan["source_files"],
                  "forecast_sha256": sha(out / "FORECAST.json"), "e25_worker_sha256": E25_SHA256}
        seals = {}
        for cohort in plan["cohorts"]:
            name = cohort["name"]
            if name == "suraj_exp13" and "w12" not in seals:
                raise ValueError("W12 raw scores must seal before any Suraj scoring")
            phase = name
            records = []
            for offset in range(0, len(frames[name]), 8):
                budget.check()
                chunk = frames[name][offset:offset + 8]
                values = score_batch(model, chunk, pad)
                torch.cuda.synchronize()
                budget.check()
                records.extend({k: f[k] for k in ("id", "feature", "phrasing", "candidate", "token_count")} | {"mean_logprob": v} for f, v in zip(chunk, values))
            provenance = {**common, "cohort": name, "blind": cohort["blind"], "input_seal_sha256": cohort["input_seal_sha256"],
                          "expected_scores": cohort["expected_scores"], "freeze": cohort["freeze"],
                          "w12_reader_hold_enforced": True, "budget_at_sealing": budget.snapshot()}
            budget.check()
            seal_cohort(out / name, cohort, records, provenance, sha(plan_path))
            budget.check()
            seals[name] = sha(out / name / "SCORE_SEAL.json")
        dump(out / "COMPLETE.json", {"status": "E29_BOTH_COHORTS_SEALED", "cohort_score_seals": seals,
                                     "budget": budget.snapshot(), "reader_hold_release_authorized": False,
                                     "next_step": "W12 D/P analysis seal and coordinator predictions must precede reader scoring"})
        budget.check()
    except Exception as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if out.exists() and not (out / "FAILURE.json").exists():
            dump(out / "FAILURE.json", {"status": "INCOMPLETE", "phase": phase, "error_type": type(error).__name__,
                                        "retry_authorized": False, "scope_reduction_authorized": False,
                                        "sealed_cohorts_retained": [n for n in COHORT_NAMES if (out / n / "SCORE_SEAL.json").exists()],
                                        "budget": budget.snapshot()})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "stage", "assignment", "assets", "out"):
        parser.add_argument("--" + name, required=True)
    run(parser.parse_args())
