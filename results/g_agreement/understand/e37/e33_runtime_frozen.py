"""E33 sealed visible-text dose sweep; no capture or activation injection.

Dated implementation 2026-10-25; operations updated under §133 item 5 only.
Original scientific PLAN and input bytes remain frozen. Scoring preserves E16 base_scores and E12
context_pair: SUM candidate token log-probabilities, A minus B, then mean
over the two W1 phrasing pairs. Only Integrator operates `run`.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time

DOSES = (0.0, 0.25, 0.5, 0.75, 1.0)
PROMPTS = ("P1", "P2")
CAP_SECONDS = 16200.0  # §133: 4.5 GPU-h TOTAL, including the earlier NO_FIT.
RETRIEVAL_SECONDS = 120.0
PROGRAMME_STOP = 1793228340.0  # 2026-10-28 23:59 Europe/Zurich.
ROOT = Path(__file__).resolve().parents[4]
PREFIX = "results/g_agreement/understand/e33/"
OPERATIONS = PREFIX + "OPERATIONS_2026-10-25.json"
PRIOR_ACCOUNTING = PREFIX + "PRIOR_ATTEMPT_ACCOUNTING.json"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")


def verify_seal(root):
    root = Path(root).resolve()
    seal = read(root / "INPUT_SEAL.json")
    if not isinstance(seal.get("files"), dict) or not seal["files"]:
        raise ValueError("nonempty input seal required")
    for name, expected in seal["files"].items():
        p = (root / name).resolve()
        if not p.is_relative_to(root) or not p.is_file() or sha(p) != expected:
            raise ValueError("input seal mismatch")
    required = {"items.input.jsonl", "templates.json", "token_pairs.json", "units.json", "provenance.json"}
    if not required <= set(seal["files"]):
        raise ValueError("input seal lacks runtime files")
    if any("DO_NOT_STAGE" in p.name for p in root.rglob("*")):
        raise ValueError("private labels forbidden in worker input")
    return seal


def _ids(seq):
    return isinstance(seq, list) and bool(seq) and all(type(i) is int and i >= 0 for i in seq)


def load_inputs(root):
    root = Path(root)
    verify_seal(root)
    items = [json.loads(line) for line in (root / "items.input.jsonl").read_text().splitlines() if line]
    templates = read(root / "templates.json")
    pairs, units = read(root / "token_pairs.json"), read(root / "units.json")
    if len(items) != 2100 or len({r["id"] for r in items}) != 2100:
        raise ValueError("exact 2100 unique W1 test items required")
    counts = Counter(r["feature"] for r in items)
    if len(counts) != 25 or set(counts.values()) != {84} or set(counts) != set(templates) or set(counts) != set(pairs):
        raise ValueError("exact 25 rows with 84 items and frozen pairs required")
    for r in items:
        if set(r["heads"]) != set(PROMPTS) or any(not _ids(r["heads"][p]) for p in PROMPTS):
            raise ValueError("both tokenized visible-text heads required")
        if any(key in r for key in ("y", "value", "label", "correct", "activation", "acts44")):
            raise ValueError("worker input must be label-free and activation-free")
    for feature in counts:
        if len(pairs[feature]) != 2 or len(templates[feature]["olens"]) != 2:
            raise ValueError("exact two W1 phrasing pairs required")
        if any(len(x) != 2 or any(not _ids(s) for s in x) for x in pairs[feature]):
            raise ValueError("nonempty tokenized candidate pairs required")
    covered = {p: [] for p in PROMPTS}
    for unit in units:
        prompt, feature, ix = unit["prompt"], unit["feature"], unit["indices"]
        if prompt not in PROMPTS or feature not in counts or not 1 <= len(ix) <= 16:
            raise ValueError("invalid frozen scoring unit")
        if any(type(i) is not int or not 0 <= i < len(items) for i in ix) or len(ix) != len(set(ix)):
            raise ValueError("invalid item index")
        if any(items[i]["feature"] != feature for i in ix):
            raise ValueError("unit mixes rows")
        if len({len(items[i]["heads"][prompt]) for i in ix}) != 1:
            raise ValueError("unit mixes head lengths")
        covered[prompt].extend(ix)
    if any(sorted(ix) != list(range(2100)) for ix in covered.values()):
        raise ValueError("each prompt must cover every item once")
    return items, templates, pairs, units


def build_sequences(heads, pair, pad):
    """Both candidates share a forward; right padding, equal head lengths only."""
    if not heads or len(pair) != 2 or not all(_ids(x) for x in heads + pair):
        raise ValueError("nonempty integer heads and candidate pair required")
    if len({len(h) for h in heads}) != 1:
        raise ValueError("equal head lengths required")
    headlen = len(heads[0])
    length = headlen + max(map(len, pair))
    ids, masks = [], []
    for head in heads:
        for candidate in pair:
            seq = head + candidate
            ids.append(seq + [pad] * (length - len(seq)))
            masks.append([1] * len(seq) + [0] * (length - len(seq)))
    return ids, masks, headlen, [len(c) for c in pair]


def paired_sum_logodds(token_logprobs, lengths):
    if len(lengths) != 2 or any(n <= 0 for n in lengths) or len(token_logprobs) % 2:
        raise ValueError("paired token probabilities required")
    if any(len(v) < lengths[i % 2] for i, v in enumerate(token_logprobs)):
        raise ValueError("truncated candidate probabilities")
    values = [sum(token_logprobs[i][:lengths[0]]) - sum(token_logprobs[i + 1][:lengths[1]])
              for i in range(0, len(token_logprobs), 2)]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("nonfinite paired log-odds")
    return values


def assert_no_hooks(model):
    for _, module in model.named_modules():
        if getattr(module, "_forward_hooks", {}) or getattr(module, "_forward_pre_hooks", {}):
            raise ValueError("forward hooks forbidden: E33 has no activation injection")


class DoseScaler:
    """Absolute multiplier on original scaling; never cumulative."""
    def __init__(self, model):
        self.model, self.layers = model, []
        for name, module in model.named_modules():
            if hasattr(module, "lora_A") and hasattr(module, "lora_B"):
                if getattr(module, "merged", False) or getattr(module, "merged_adapters", []):
                    raise ValueError("unmerged Oracle adapter required")
                original = dict(module.scaling)
                if set(original) != {"default"} or not math.isfinite(float(original["default"])) or original["default"] <= 0:
                    raise ValueError("exact single default Oracle adapter required")
                if getattr(module, "disable_adapters", False):
                    raise ValueError("Oracle adapter must be enabled")
                self.layers.append((name, module, original))
        if not self.layers:
            raise ValueError("no live LoRA layers found")

    def set(self, dose):
        if dose not in DOSES:
            raise ValueError("unregistered LoRA dose")
        for _, module, original in self.layers:
            if set(module.scaling) != set(original) or getattr(module, "merged", False):
                raise ValueError("LoRA topology changed")
            for key, value in original.items():
                module.scaling[key] = float(dose) * value

    def restore(self):
        for _, module, original in self.layers:
            module.scaling.update(original)

    @contextmanager
    def at(self, dose):
        self.set(dose)
        try:
            yield
        finally:
            self.restore()


class NoFit(TimeoutError):
    pass


def validate_run_plan(plan):
    """Every worker independently checks the complete shared budget allocation."""
    if plan.get("schema") != "E33_RUN_PLAN_v2" or plan.get("experiment") != "E33":
        raise ValueError("E33 version-2 shared run plan required")
    if not isinstance(plan.get("run_id"), str) or not plan["run_id"]:
        raise ValueError("common nonempty run identity required")
    if plan.get("global_cap_gpu_seconds") != CAP_SECONDS:
        raise ValueError("registered 16200-second aggregate cap required")
    previous = plan.get("previous_gpu_seconds")
    if type(previous) not in (int, float) or not math.isfinite(previous) or not 0 < previous < CAP_SECONDS:
        raise ValueError("positive finite prior E33 usage must be charged")
    allocations = plan.get("allocations")
    if not isinstance(allocations, list) or len(allocations) not in (1, 2):
        raise ValueError("one or two complete dose-shard allocations required")
    expected = [list(DOSES)] if len(allocations) == 1 else [list(DOSES[:3]), list(DOSES[3:])]
    pod_ids, total = [], [previous]
    for slot, allocation in enumerate(allocations):
        if (type(allocation.get("slot")) is not int or allocation["slot"] != slot or
                allocation.get("doses") != expected[slot] or
                any(type(d) not in (int, float) for d in allocation.get("doses", []))):
            raise ValueError("fixed dose partition changed, duplicated, or incomplete")
        pod = allocation.get("pod_id")
        if not isinstance(pod, str) or not pod:
            raise ValueError("each allocation requires its distinct provider pod ID")
        pod_ids.append(pod)
        cap = allocation.get("allocated_gpu_seconds")
        if type(cap) not in (int, float) or not math.isfinite(cap) or cap <= RETRIEVAL_SECONDS:
            raise ValueError("positive shard budget with retrieval reserve required")
        total.append(cap)
    if len(set(pod_ids)) != len(pod_ids):
        raise ValueError("one provider pod cannot hold two budget allocations")
    if math.fsum(total) > CAP_SECONDS:
        raise ValueError("prior usage plus all shard allocations exceeds 4.5 GPU-h")
    return allocations


class Budget:
    def __init__(self, assignment, run_plan, now=time.time):
        self.a, self.plan, self.now = assignment, run_plan, now
        allocations = validate_run_plan(run_plan)
        slot = assignment.get("slot")
        if type(slot) is not int or not 0 <= slot < len(allocations):
            raise ValueError("assigned shard slot absent from common budget plan")
        self.allocation, self.doses = allocations[slot], tuple(allocations[slot]["doses"])
        for key in ("pod_id", "doses", "allocated_gpu_seconds"):
            if assignment.get(key) != self.allocation[key]:
                raise ValueError("assignment differs from common shard allocation: " + key)
        if assignment.get("pod_count") != len(allocations) or assignment.get("previous_gpu_seconds") != run_plan["previous_gpu_seconds"]:
            raise ValueError("assignment prior-usage/pod-count differs from common plan")
        self.reserved = self.allocation["allocated_gpu_seconds"]
        self.science_started, self.science_cap = None, self.reserved
        if assignment.get("issuer") != "integrator" or assignment.get("experiment") != "E33" or assignment.get("gpu_count") != 1:
            raise ValueError("one-GPU Integrator E33 assignment required")
        for key in ("registered", "pushed", "external_hardstop_verified"):
            if assignment.get(key) is not True:
                raise ValueError(key + " evidence required")
        if not assignment.get("pod_id"):
            raise ValueError("provider pod ID required")
        for key in ("allocated_gpu_seconds", "previous_gpu_seconds", "provider_created_epoch", "deadline_epoch"):
            if type(assignment.get(key)) not in (int, float) or not math.isfinite(assignment[key]):
                raise ValueError("finite provider budget fields required")
        if assignment["provider_created_epoch"] > self.now():
            raise ValueError("provider creation cannot be in future")
        if assignment["deadline_epoch"] > min(PROGRAMME_STOP, assignment["provider_created_epoch"] + assignment["allocated_gpu_seconds"]):
            raise ValueError("deadline exceeds registered total provider cap")
        self.guard()

    def elapsed(self):
        return self.now() - self.a["provider_created_epoch"]

    def science_elapsed(self):
        return 0 if self.science_started is None else self.now() - self.science_started

    def remaining(self):
        return self.a["deadline_epoch"] - self.now()

    def guard(self):
        if self.remaining() <= RETRIEVAL_SECONDS or self.science_elapsed() >= self.science_cap - RETRIEVAL_SECONDS:
            raise TimeoutError("provider/science deadline reached; retrieval reserve preserved")

    def start_science(self):
        if self.science_started is not None:
            raise ValueError("science clock cannot reset")
        self.science_started = self.now()

    def admit(self, samples, counts):
        keys = {(p, dose) for p in PROMPTS for dose in self.doses}
        if set(samples) != keys or set(counts) != keys:
            raise ValueError("every assigned prompt-dose path required before shard bulk")
        for key, values in samples.items():
            if len(values) != 3 or any(not math.isfinite(x) or x <= 0 for x in values) or type(counts[key]) is not int or counts[key] <= 0:
                raise ValueError("median3 positive warmed timings required for every path")
        paths = [{"prompt": p, "dose": dose, "unit_count": counts[p, dose], "timed_seconds": samples[p, dose],
                  "median_seconds": statistics.median(samples[p, dose])} for p, dose in sorted(keys)]
        forecast = sum(x["unit_count"] * x["median_seconds"] for x in paths)
        self.science_cap = min(1.5 * forecast + 360, self.reserved)
        required = 1.5 * forecast + RETRIEVAL_SECONDS
        return {"paths": paths, "F_seconds": forecast, "remaining_seconds": self.remaining(),
                "provider_elapsed_seconds": self.elapsed(), "science_elapsed_seconds": self.science_elapsed(),
                "science_cap_seconds": self.science_cap, "required_remaining_seconds": required,
                "safety_factor": 1.5, "retrieval_seconds": RETRIEVAL_SECONDS,
                "fit": required <= min(self.remaining(), self.science_cap - self.science_elapsed()),
                "unknown_paths_are_zero": False, "pilot_scores_discarded": True, "all_paths_warmed": True,
                "budget_includes_setup": True, "budget_clock_resets": 0,
                "assigned_doses": list(self.doses), "slot": self.a["slot"],
                "pod_count": self.a["pod_count"], "previous_gpu_seconds": self.plan["previous_gpu_seconds"],
                "allocated_gpu_seconds": self.reserved, "global_cap_gpu_seconds": CAP_SECONDS}


def verify_assignment(a, assignment_path, inputs, assets_path, run_plan_path):
    if a.get("input_seal_sha256") != sha(inputs / "INPUT_SEAL.json") or a.get("assets_sha256") != sha(assets_path):
        raise ValueError("assignment input or asset manifest binding mismatch")
    pins = a.get("source_files", {})
    required = {PREFIX + name for name in ("runtime.py", "PLAN.json", "reused.py", "UPSTREAM_SOURCE.json")}
    required.add(OPERATIONS)
    required.add(PRIOR_ACCOUNTING)
    required.add("projects/g_agreement/manifest/assets.json")
    if not required <= set(pins):
        raise ValueError("runtime, plan, reused source, and asset manifest pins required")
    for name, expected in pins.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or sha(path) != expected:
            raise ValueError("assignment source pin mismatch")
    plan_path = ROOT / PREFIX / "PLAN.json"
    plan, provenance = read(plan_path), read(inputs / "provenance.json")
    if provenance.get("plan_sha256") != sha(plan_path):
        raise ValueError("staged inputs use a different frozen plan")
    if (provenance.get("e12_input_seal_sha256") != plan["e12_input_seal_sha256"] or
            sha(inputs / "templates.json") != plan["e12_templates_sha256"] or
            sorted(read(inputs / "templates.json")) != plan["rows"] or
            provenance.get("upstream_source_sha256") != sha(ROOT / PREFIX / "UPSTREAM_SOURCE.json")):
        raise ValueError("staged W1 rows, phrasings or upstream source differ from plan")
    run_plan = read(run_plan_path)
    validate_run_plan(run_plan)
    if a.get("run_plan_sha256") != sha(run_plan_path):
        raise ValueError("assignment not bound to exact shared run-plan bytes")
    if (run_plan.get("source_files") != pins or run_plan.get("input_seal_sha256") != a["input_seal_sha256"] or
            run_plan.get("original_plan_sha256") != sha(plan_path) or
            run_plan.get("operations_sha256") != sha(ROOT / OPERATIONS)):
        raise ValueError("shared run plan differs in source, inputs, original plan, or operations authority")
    operations = read(ROOT / OPERATIONS)
    accounting = read(ROOT / PRIOR_ACCOUNTING)
    if (run_plan["previous_gpu_seconds"] != operations["previous_gpu_seconds"] or
            run_plan["previous_gpu_seconds"] != accounting["reserved_prior_gpu_seconds"] or
            run_plan["previous_gpu_seconds"] != math.ceil(accounting["booked_prior_gpu_seconds"])):
        raise ValueError("prior usage differs from frozen audited operations ledger")
    if (operations.get("global_cap_gpu_seconds") != CAP_SECONDS or
            operations.get("input_seal_sha256") != run_plan["input_seal_sha256"] or
            operations.get("original_plan_sha256") != run_plan["original_plan_sha256"]):
        raise ValueError("operations authority differs from global cap or immutable science inputs")
    return sha(assignment_path)


def verify_assets(path, budget):
    """Local-only assets: complete byte hashes and registered revisions/hashes."""
    a = read(path)
    pinned = read(ROOT / "projects/g_agreement/manifest/assets.json")
    revisions = {"model": pinned["target"]["revision"], "olens": pinned["readers"]["olens"]["revision"]}
    for name, revision in revisions.items():
        if a.get("revisions", {}).get(name) != revision or not Path(a.get(name, "")).is_dir():
            raise ValueError("registered local model and Oracle revisions required")
    file_hashes = {}
    for item in a.get("files", []):
        budget.guard()
        p = Path(item["path"]).resolve()
        if p in file_hashes or sha(p) != item["sha256"]:
            raise ValueError("asset hash mismatch or duplicate entry")
        file_hashes[p] = item["sha256"]
    needed = {p.resolve() for name in revisions for p in Path(a[name]).rglob("*") if p.is_file()}
    if not needed or not needed <= set(file_hashes):
        raise ValueError("full model and Oracle asset file coverage required")
    known = {(Path(a["model"]) / "tokenizer.json").resolve(): pinned["target"]["files_needed"]["tokenizer.json_sha256"],
             (Path(a["olens"]) / "adapter_model.safetensors").resolve(): pinned["readers"]["olens"]["adapter_model_sha256"]}
    if any(file_hashes.get(p) != expected for p, expected in known.items()):
        raise ValueError("assets differ from registered tokenizer or Oracle bytes")
    return a


def score_unit(model, tokenizer, unit, items, pairs, device="cuda"):
    import torch
    assert_no_hooks(model)
    ix, prompt, feature = unit["indices"], unit["prompt"], unit["feature"]
    heads = [items[i]["heads"][prompt] for i in ix]
    answers = []
    with torch.inference_mode():
        for pair in pairs[feature]:
            seqs, masks, headlen, lengths = build_sequences(heads, pair, tokenizer.pad_token_id or 0)
            ids = torch.tensor(seqs, dtype=torch.long, device=device)
            mask = torch.tensor(masks, dtype=torch.long, device=device)
            logits = model(input_ids=ids, attention_mask=mask, logits_to_keep=len(seqs[0]) - headlen + 1, use_cache=False).logits
            if logits.shape[1] != len(seqs[0]) - headlen + 1:
                raise ValueError("model did not honor exact candidate logit window")
            lp = torch.log_softmax(logits[:, :-1].float(), dim=-1)
            token_lp = lp.gather(-1, ids[:, headlen:].unsqueeze(-1)).squeeze(-1)
            # Preserve the upstream fp32 tensor reduction, including its rounding.
            values = [float(token_lp[2 * i, :lengths[0]].sum() - token_lp[2 * i + 1, :lengths[1]].sum())
                      for i in range(len(ix))]
            if not all(math.isfinite(v) for v in values):
                raise ValueError("nonfinite paired log-odds")
            answers.append(values)
    assert_no_hooks(model)
    return [{"id": items[i]["id"], "feature": feature, "prompt": prompt,
             "scores": [answers[0][j], answers[1][j]], "score": (answers[0][j] + answers[1][j]) / 2}
            for j, i in enumerate(ix)]


def representative_unit(units, items, pairs, prompt):
    choices = [(i, u) for i, u in enumerate(units) if u["prompt"] == prompt]
    def cost(entry):
        _, u = entry
        h = len(items[u["indices"][0]]["heads"][prompt])
        return (len(u["indices"]) * sum((h + max(map(len, p))) ** 2 for p in pairs[u["feature"]]), -entry[0])
    return max(choices, key=cost)


def check_endpoints(model, scaler, head, device="cuda"):
    """Numerical implementation gate; no test labels or outcome-based choices."""
    import torch
    ids = torch.tensor([head], dtype=torch.long, device=device)
    with torch.inference_mode():
        with model.disable_adapter():
            base = model(input_ids=ids, attention_mask=torch.ones_like(ids), logits_to_keep=1, use_cache=False).logits.float()
        with scaler.at(0.0):
            zero = model(input_ids=ids, attention_mask=torch.ones_like(ids), logits_to_keep=1, use_cache=False).logits.float()
        with scaler.at(1.0):
            full = model(input_ids=ids, attention_mask=torch.ones_like(ids), logits_to_keep=1, use_cache=False).logits.float()
        parity = float((base - zero).abs().max())
        live = float((full - base).abs().max())
    if not math.isfinite(parity) or parity != 0 or not math.isfinite(live) or live <= 1e-3:
        raise ValueError("zero-dose/base exact parity or registered adapter liveness check failed")
    return {"zero_vs_disabled_max_abs_logit": parity, "full_vs_disabled_max_abs_logit": live,
            "lora_layer_count": len(scaler.layers), "activation_injection": False}


def run(args):
    assignment = read(args.assignment)
    run_plan = read(args.run_plan)
    budget = Budget(assignment, run_plan)
    assignment_sha = verify_assignment(assignment, args.assignment, args.inputs, args.assets, args.run_plan)
    items, templates, pairs, units = load_inputs(args.inputs)
    if "cache" not in args.out.resolve().parts:
        raise ValueError("runtime output must be in ignored cache directory")
    args.out.mkdir(parents=True, exist_ok=False)
    with (args.out / "run_plan.json").open("xb") as f:
        f.write(args.run_plan.read_bytes())
    started = time.time()
    stage, status, scaler = "asset_verification", "INCOMPLETE", None
    error_type = None
    try:
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", WANDB_MODE="disabled")
        assets = verify_assets(args.assets, budget)
        budget.guard()
        stage = "model_load"
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
        torch.manual_seed(20261025)
        torch.cuda.manual_seed_all(20261025)
        for name, expected in read(args.inputs / "provenance.json")["tokenizer_files"].items():
            path = (Path(assets["model"]) / name).resolve()
            if not path.is_file() or sha(path) != expected:
                raise ValueError("runtime tokenizer files differ from staged prompt tokenizer")
        tokenizer = AutoTokenizer.from_pretrained(assets["model"], local_files_only=True)
        for feature, spec in templates.items():
            encoded = [[tokenizer.encode(text, add_special_tokens=False) for text in pair] for pair in spec["olens"]]
            if encoded != pairs[feature]:
                raise ValueError("candidate tokenization differs from frozen input")
        model = AutoModelForCausalLM.from_pretrained(assets["model"], dtype=torch.bfloat16,
                                                    device_map="cuda", local_files_only=True).eval()
        model = PeftModel.from_pretrained(model, assets["olens"], is_trainable=False, local_files_only=True).eval()
        assert_no_hooks(model)
        scaler = DoseScaler(model)
        budget.guard()
        budget.start_science()
        stage = "endpoint_check"
        write_new(args.out / "ENDPOINT_CHECK.json", check_endpoints(model, scaler, items[0]["heads"]["P1"]))
        stage = "warmed_forecast"
        samples, warmups, representatives = {}, {}, {}
        counts = {(p, dose): sum(u["prompt"] == p for u in units) for p in PROMPTS for dose in budget.doses}
        for prompt in PROMPTS:
            index, unit = representative_unit(units, items, pairs, prompt)
            representatives[prompt] = {"unit_index": index, "item_count": len(unit["indices"]),
                                       "head_tokens": len(items[unit["indices"][0]]["heads"][prompt])}
            for dose in budget.doses:
                budget.guard()
                with scaler.at(dose):
                    torch.cuda.synchronize()
                    t = time.monotonic()
                    score_unit(model, tokenizer, unit, items, pairs)
                    torch.cuda.synchronize()
                    warmups[prompt, dose] = time.monotonic() - t
                    samples[prompt, dose] = []
                    for _ in range(3):
                        budget.guard()
                        torch.cuda.synchronize()
                        t = time.monotonic()
                        score_unit(model, tokenizer, unit, items, pairs)
                        torch.cuda.synchronize()
                        samples[prompt, dose].append(time.monotonic() - t)
        forecast = budget.admit(samples, counts)
        forecast["representative_units"] = representatives
        forecast["run_plan_sha256"] = assignment["run_plan_sha256"]
        forecast["warmup_seconds"] = [{"prompt": p, "dose": d, "seconds": s} for (p, d), s in warmups.items()]
        write_new(args.out / "WARMED_FORECAST.json", forecast)
        write_new(args.out / "FORECAST_SEAL.json", {"files": {"WARMED_FORECAST.json": sha(args.out / "WARMED_FORECAST.json")}})
        if not forecast["fit"]:
            raise NoFit("full assigned prompt-dose grid does not fit")
        stage = "bulk_collection"
        expected = {(r["id"], p, d) for r in items for p in PROMPTS for d in budget.doses}
        seen = set()
        with (args.out / "scores.jsonl").open("x") as handle:
            for prompt in PROMPTS:
                for dose in budget.doses:
                    with scaler.at(dose):
                        for unit in units:
                            if unit["prompt"] != prompt:
                                continue
                            budget.guard()
                            for record in score_unit(model, tokenizer, unit, items, pairs):
                                record["dose"] = dose
                                key = record["id"], prompt, dose
                                if key in seen or key not in expected:
                                    raise ValueError("duplicate or unexpected score")
                                seen.add(key)
                                handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
                            handle.flush()
        budget.guard()
        if seen != expected or len(seen) != 2100 * 2 * len(budget.doses):
            raise ValueError("exact complete assigned shard score grid required")
        status, stage = "COMPLETE", "complete"
    except Exception as exc:
        status = "NO_FIT" if isinstance(exc, NoFit) else "INCOMPLETE"
        error_type = type(exc).__name__
    finally:
        if scaler is not None:
            scaler.restore()
        identity = {"run_id": run_plan["run_id"], "run_plan_sha256": assignment["run_plan_sha256"],
                    "operations_sha256": run_plan["operations_sha256"],
                    "original_plan_sha256": run_plan["original_plan_sha256"],
                    "slot": assignment["slot"], "pod_id": assignment["pod_id"], "pod_count": assignment["pod_count"],
                    "assigned_doses": list(budget.doses), "previous_gpu_seconds": run_plan["previous_gpu_seconds"],
                    "global_cap_gpu_seconds": CAP_SECONDS, "allocated_gpu_seconds": budget.reserved,
                    "expected_score_records": 2100 * 2 * len(budget.doses)}
        receipt = {**identity, "experiment": "E33", "status": status, "failure_stage": None if status == "COMPLETE" else stage,
                   "error_type": error_type, "started_epoch": started, "ended_epoch": time.time(),
                   "provider_created_epoch": assignment["provider_created_epoch"],
                   "provider_elapsed_seconds": budget.elapsed(), "budget_gpu_seconds": assignment["allocated_gpu_seconds"],
                   "science_elapsed_seconds": budget.science_elapsed(), "science_cap_seconds": budget.science_cap,
                   "budget_includes_setup": True, "budget_clock_resets": 0, "GPU_count": 1,
                   "input_seal_sha256": sha(args.inputs / "INPUT_SEAL.json"),
                   "input_provenance_sha256": sha(args.inputs / "provenance.json"),
                   "assignment_sha256": assignment_sha, "assets_sha256": sha(args.assets),
                   "source_files": assignment["source_files"], "activation_injection": False,
                   "scoring": "sum candidate token logprobs; A-B; mean of exact two W1 pairs",
                   "scope_reduction": False, "retry_authorized": False}
        write_new(args.out / "RUN.json", receipt)
        write_new(args.out / "provenance.json", {**identity, "status": status, "input_seal_sha256": receipt["input_seal_sha256"],
                  "input_provenance_sha256": receipt["input_provenance_sha256"],
                  "assignment_sha256": assignment_sha, "source_files": assignment["source_files"],
                  "activation_injection": False, "scoring": receipt["scoring"],
                  "dose_scaling": "absolute multiplier of original per-layer scaling; restored after every block",
                  "score_grid": f"25 rows x 84 items x 2 prompts x {len(budget.doses)} assigned doses",
                  "global_scope": "five doses; exact complete all-shard join required before labels"})
        write_new(args.out / "SCORE_SEAL.json", {"status": "E33_SHARD_" + status,
                  "files": {p.name: sha(p) for p in sorted(args.out.iterdir()) if p.is_file()}})
    print("E33_SHARD_" + status)
    return 0 if status == "COMPLETE" else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--inputs", type=Path, required=True)
    assignment_check = commands.add_parser("validate-assignment")
    for name in ("inputs", "assets", "assignment", "run-plan"):
        assignment_check.add_argument("--" + name, type=Path, required=True)
    launch = commands.add_parser("run")
    for name in ("inputs", "assets", "assignment", "out", "run-plan"):
        launch.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    if args.command == "validate":
        items, _, _, units = load_inputs(args.inputs)
        print(json.dumps({"status": "PASS", "items": len(items), "rows": 25, "units": len(units), "GPU_hours": 0}))
        return 0
    if args.command == "validate-assignment":
        a, run_plan = read(args.assignment), read(args.run_plan)
        budget = Budget(a, run_plan)
        verify_assignment(a, args.assignment, args.inputs, args.assets, args.run_plan)
        load_inputs(args.inputs)
        print(json.dumps({"status": "PASS", "slot": a["slot"], "assigned_doses": list(budget.doses),
                          "expected_score_records": 2100 * 2 * len(budget.doses), "GPU_hours": 0}))
        return 0
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
