"""E37 conditional, sealed RL/SFT comparison; no training or autonomous launch.

2026-10-25: §134 plus clarification 1 (d4bb903d). The checkpoint-arrival
deadline is an eligibility condition, not a launch deadline. Missing inputs,
unresolved gates, or incomplete predecessor experiments fail before loading.
"""
from __future__ import annotations
import argparse
from collections import Counter
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import statistics
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PREFIX = "results/g_agreement/understand/e37/"
BASE_RUNTIME = PREFIX + "e33_runtime_frozen.py"
_spec = importlib.util.spec_from_file_location("e37_reused_e33", ROOT / BASE_RUNTIME)
E33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E33)
read, sha, write_new = E33.read, E33.sha, E33.write_new
_cpu_spec = importlib.util.spec_from_file_location("e37_checkpoint_cpu", HERE / "checkpoint_cpu.py")
CPU = importlib.util.module_from_spec(_cpu_spec)
_cpu_spec.loader.exec_module(CPU)
ARMS = ("RL", "SFT")
CHANNELS = ("C1", "C1prime", "C2", "C4")
C2_ROWS = ("prose_paren", "prose_quote", "python_string", "python_indent", "python_depth", "list_depth", "table_role")
PARITY_ROWS = ("prose_sentiment", "prose_paren", "python_string")
ARRIVAL_DEADLINE = 1793127600.0  # 2026-10-27 20:00 CET / 19:00 UTC.
PROGRAMME_STOP = 1793314740.0  # §154: 2026-10-29 22:59 UTC.
CAP = 11000.0
RESERVE = 120.0


class Blocked(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(status)


class NoFit(TimeoutError):
    pass


def verify_files(directory, files):
    directory = Path(directory).resolve()
    if not isinstance(files, dict) or not files:
        raise ValueError("nonempty sealed file map required")
    for name, expected in files.items():
        p = (directory / name).resolve()
        if not p.is_relative_to(directory) or not p.is_file() or sha(p) != expected:
            raise ValueError("sealed file missing, changed, or outside its directory")


def checkpoint_receipt(path, now=None, hash_files=True):
    """Pin actual received bytes before any forward. No invented SFT checkpoint."""
    now = time.time() if now is None else now
    if not Path(path).is_file():
        raise Blocked("NOT_RUN" if now > ARRIVAL_DEADLINE else "BLOCKED_AWAITING_CHECKPOINT")
    receipt = read(path)
    if receipt.get("status") != "RECEIVED_FROZEN":
        raise Blocked("NOT_RUN" if now > ARRIVAL_DEADLINE else "BLOCKED_AWAITING_CHECKPOINT")
    if (receipt.get("schema") != "E37_SFT_RECEIPT_v1" or receipt.get("issuer") != "integrator" or
            receipt.get("provided_by") != "Agam" or receipt.get("checkpoint_identity") != "s3d.omp4bp.s2/step251" or
            receipt.get("identity_verified") is not True or receipt.get("frozen_before_model_calls") is not True or
            receipt.get("model_calls_before_freeze") != 0):
        raise ValueError("verified original step251 provenance and pre-forward freeze required")
    received = receipt.get("received_epoch")
    if type(received) not in (int, float) or not math.isfinite(received) or received > now:
        raise ValueError("valid actual checkpoint arrival time required")
    if received > ARRIVAL_DEADLINE:
        raise Blocked("NOT_RUN")
    local = Path(receipt["local_path"])
    required = {"adapter_config.json", "adapter_model.safetensors"}
    if not required <= set(receipt.get("files", {})):
        raise ValueError("compatible PEFT safetensors checkpoint files required")
    actual = {str(p.relative_to(local)) for p in local.rglob("*") if p.is_file()}
    if actual != set(receipt["files"]):
        raise ValueError("received checkpoint requires complete exact file coverage")
    if hash_files:
        verify_files(local, receipt["files"])
    config = read(local / "adapter_config.json")
    if config.get("peft_type") != "LORA" or type(config.get("r")) is not int or config["r"] <= 0:
        raise ValueError("step251 must be a compatible LoRA adapter")
    if not config.get("target_modules") or not isinstance(config["target_modules"], (list, str)):
        raise ValueError("LoRA target modules required")
    pinned = read(ROOT / "projects/g_agreement/manifest/assets.json")
    if receipt.get("base_model_revision") != pinned["target"]["revision"]:
        raise ValueError("step251 base-model provenance must match pinned Qwen")
    return receipt


def predecessors(path):
    if not Path(path).is_file():
        raise Blocked("BLOCKED_PREDECESSORS_INCOMPLETE")
    record = read(path)
    if (record.get("schema") != "E37_PREREQUISITE_COMPLETION_v1" or
            record.get("issuer") != "integrator" or record.get("status") not in ("COMPLETE", "READY_AFTER_PREDECESSORS")):
        raise Blocked("BLOCKED_PREDECESSORS_INCOMPLETE")
    if set(record.get("experiments", {})) != {"E33", "E28"}:
        raise ValueError("both completed predecessor experiments required")
    expected_runs = {(row, arm) for row in ("prose_paren", "python_string", "table_role", "python_depth", "table_column", "prose_sentiment")
                     for arm in ("L", "B")}
    expected_runs |= {("prose_paren", "S"), ("prose_sentiment", "S")}
    for name in ("E33", "E28"):
        entry = record["experiments"][name]
        if entry.get("status") not in ("COMPLETE", "NOT_RUN", "NO_FIT", "NO_GO") or not entry.get("receipts"):
            raise Blocked("BLOCKED_PREDECESSORS_INCOMPLETE")
        coverage, complete_analysis = set(), False
        seen = set()
        for evidence in entry["receipts"]:
            p = Path(evidence["path"]).resolve()
            if p in seen or not p.is_file() or sha(p) != evidence["sha256"]:
                raise ValueError("predecessor receipt missing, duplicated, or changed")
            seen.add(p)
            data = read(p)
            status = data.get("status")
            if status in ("NOT_RUN", "NO_FIT", "NO_GO"):
                epoch = data.get("closed_epoch")
                accounting = data.get("provider_accounting", {})
                if (data.get("schema") != "E37_PREDECESSOR_TERMINAL_v1" or data.get("issuer") != "integrator" or
                        data.get("experiment") != name or data.get("closed") is not True or
                        data.get("all_expected_runs_closed") is not True or data.get("no_active_pods") is not True or
                        not isinstance(data.get("reason"), str) or not data["reason"].strip() or
                        type(epoch) not in (int, float) or not math.isfinite(epoch) or not 0 < epoch <= time.time() or
                        type(accounting.get("gpu_seconds")) not in (int, float) or
                        not math.isfinite(accounting["gpu_seconds"]) or accounting["gpu_seconds"] < 0):
                    raise ValueError("explicit dated Integrator terminal closure and provider accounting required")
                complete_analysis = True  # Terminal closure satisfies queue precedence, not scientific completion.
                continue
            if name == "E33":
                if status == "E33_ANALYSIS_SEALED":
                    verify_files(p.parent, data["files"])
                    complete_analysis = True
                elif status in ("E33_COMPLETE", "E33_SHARD_COMPLETE"):
                    verify_files(p.parent, data["files"])
                    provenance = read(p.parent / "provenance.json")
                    doses = provenance.get("assigned_doses", list(E33.DOSES) if status == "E33_COMPLETE" else [])
                    if not doses or coverage & set(doses):
                        raise ValueError("E33 predecessor dose coverage duplicated or missing")
                    coverage.update(doses)
                else:
                    raise ValueError("E33 predecessor receipt is not complete")
            else:
                if status == "COMPLETE_ANALYSIS" and data.get("experiment") == "E28":
                    cells = [(c["row"], c["arm"]) for c in data.get("cells", [])]
                    if len(cells) != 14 or set(cells) != expected_runs:
                        raise ValueError("E28 predecessor analysis lacks all fourteen runs")
                    complete_analysis = True
                elif status == "COMPLETE_FULL_ASSIGNED_GRID":
                    runs = {tuple(v) for v in data.get("runs", [])}
                    if not runs or coverage & runs:
                        raise ValueError("E28 predecessor run coverage duplicated or missing")
                    coverage.update(runs)
                else:
                    raise ValueError("E28 predecessor receipt is not complete")
        expected = set(E33.DOSES) if name == "E33" else expected_runs
        if not complete_analysis and coverage != expected:
            raise Blocked("BLOCKED_PREDECESSORS_INCOMPLETE")
    return record


def validate_parity_policy(path):
    if not Path(path).is_file():
        raise Blocked("BLOCKED_PARITY_UNRESOLVED")
    policy = read(path)
    if policy.get("status") != "REGISTERED_FROZEN":
        raise Blocked("BLOCKED_PARITY_UNRESOLVED")
    if (policy.get("smoke", {}).get("n") != 20 or policy["smoke"].get("channel") != "C1" or
            policy["smoke"].get("self_repeat_max_abs") != 1e-4 or
            policy.get("rl_reproduction", {}).get("rows") != list(PARITY_ROWS) or
            policy["rl_reproduction"].get("max_abs_auroc_delta") != .03):
        raise ValueError("parity policy differs from §134 clarification 1")
    return policy


def load_inputs(folder):
    folder = Path(folder)
    seal = read(folder / "INPUT_SEAL.json")
    required = {"items.input.jsonl", "acts44.npy", "templates.json", "token_pairs.json", "carrier.json", "provenance.json", "parity_inputs.json", "parity_labels.json"}
    if set(seal.get("files", {})) != required or {p.name for p in folder.iterdir()} != required | {"INPUT_SEAL.json"}:
        raise ValueError("complete E37 sealed inputs required")
    verify_files(folder, seal["files"])
    items = [json.loads(line) for line in (folder / "items.input.jsonl").read_text().splitlines() if line]
    plan = read(HERE / "PLAN.json")
    count = Counter(r["feature"] for r in items)
    if len(items) != 2100 or len({r["id"] for r in items}) != 2100 or sorted(count) != plan["rows"] or set(count.values()) != {84}:
        raise ValueError("exact frozen W1 25-row test bank required")
    if any(set(r) != {"id", "feature", "donor_id"} for r in items):
        raise ValueError("only explicitly authorized parity labels may be staged")
    byid = {r["id"]: r for r in items}
    for item in items:
        donor = byid.get(item["donor_id"])
        if donor is None or donor["id"] == item["id"] or donor["feature"] != item["feature"] or donor["donor_id"] != item["id"]:
            raise ValueError("exact reciprocal same-row W1 donor map required")
    templates, token_pairs = read(folder / "templates.json"), read(folder / "token_pairs.json")
    if set(templates) != {"C1", "C1prime", "C2"} or set(token_pairs) != set(templates):
        raise ValueError("exact three paired channels required")
    for channel in templates:
        expected = set(C2_ROWS) if channel == "C2" else set(plan["rows"])
        if set(templates[channel]) != expected or set(token_pairs[channel]) != expected:
            raise ValueError("paired channel row coverage differs from registration")
        for feature, pairs in templates[channel].items():
            tokens = token_pairs[channel][feature]
            if len(pairs) != 2 or len(tokens) != 2:
                raise ValueError("frozen pair coverage differs")
            if any(len(pair) != 2 or not all(E33._ids(v) for v in pair) for pair in tokens):
                raise ValueError("nonempty candidate token pairs required")
    carrier = read(folder / "carrier.json")
    if (carrier["layer"] != 44 or carrier["alpha"] != 16000 or not E33._ids(carrier["head_ids"]) or
            carrier["head_ids"][carrier["marker_index"]] != carrier["marker_token_id"] or
            carrier["head_ids"].count(carrier["marker_token_id"]) != 1 or set(carrier["prefix_ids"]) != set(CHANNELS)):
        raise ValueError("native Oracle block44 carrier required")
    parity, labels = read(folder / "parity_inputs.json"), read(folder / "parity_labels.json")
    ids = sorted(byid, key=lambda key: __import__('hashlib').sha256(f"20261025|{key}".encode()).hexdigest())[:20]
    if parity["smoke_ids"] != ids or parity["reproduction_rows"] != list(PARITY_ROWS) or set(parity["rl_reference_auc"]) != set(PARITY_ROWS):
        raise ValueError("frozen parity smoke/reference coverage differs")
    permitted = {r["id"] for r in items if r["feature"] in PARITY_ROWS}
    if set(labels) != permitted or len(labels) != 252 or any(type(y) not in (int, bool) or y not in (0, 1) for y in labels.values()):
        raise ValueError("exactly 252 registered parity labels permitted")
    import numpy as np
    h = np.load(folder / "acts44.npy", mmap_mode="r", allow_pickle=False)
    if h.shape != (2100, 5120) or h.dtype != np.float32 or not np.isfinite(h).all() or np.any(np.linalg.norm(h, axis=1) == 0):
        raise ValueError("finite nonzero sealed W1 h44 required")
    return items, h, templates, token_pairs, carrier, parity, labels


class Budget:
    def __init__(self, assignment, now=time.time):
        self.a, self.now = assignment, now
        self.first, self.science_cap = None, CAP
        self.alarm_installed = False
        if (assignment.get("issuer") != "integrator" or assignment.get("experiment") != "E37" or
                assignment.get("gpu_count") != 1 or not assignment.get("pod_id") or
                any(assignment.get(k) is not True for k in ("registered", "pushed", "external_hardstop_verified"))):
            raise ValueError("published one-pod Integrator E37 assignment required")
        for key in ("allocated_gpu_seconds", "previous_gpu_seconds", "provider_created_epoch", "deadline_epoch"):
            if type(assignment.get(key)) not in (int, float) or not math.isfinite(assignment[key]):
                raise ValueError("finite provider budget fields required")
        if assignment["previous_gpu_seconds"] != 0 or not RESERVE < assignment["allocated_gpu_seconds"] <= CAP:
            raise ValueError("fresh E37 custody at most 5400 seconds required")
        if assignment["provider_created_epoch"] > now() or assignment["deadline_epoch"] > min(PROGRAMME_STOP, assignment["provider_created_epoch"] + assignment["allocated_gpu_seconds"]):
            raise ValueError("provider deadline exceeds allocation or programme cutoff")
        self.guard()

    def elapsed(self):
        return self.now() - self.a["provider_created_epoch"]

    def science_elapsed(self):
        return 0 if self.first is None else self.now() - self.first

    def guard(self):
        if self.now() >= self.a["deadline_epoch"] - RESERVE or self.science_elapsed() >= self.science_cap - RESERVE:
            raise TimeoutError("provider/science deadline; retrieval reserve preserved")
        if self.alarm_installed:
            end = self.a["deadline_epoch"] - RESERVE
            if self.first is not None:
                end = min(end, self.first + self.science_cap - RESERVE)
            signal.setitimer(signal.ITIMER_REAL, max(.001, end - self.now()))

    def install_alarm(self):
        if signal.getitimer(signal.ITIMER_REAL)[0] != 0:
            raise ValueError("dedicated runner process required; existing real-time timer present")
        def expired(*_):
            raise TimeoutError("absolute provider/science alarm; no clock reset")
        self.previous_handler = signal.signal(signal.SIGALRM, expired)
        self.alarm_installed = True
        self.guard()

    def close_alarm(self):
        if self.alarm_installed:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self.previous_handler)
            self.alarm_installed = False

    def start(self):
        if self.first is not None:
            raise ValueError("science clock cannot reset")
        self.first = self.now()
        self.guard()

    def forecast(self, samples, counts):
        keys = {(arm, channel) for arm in ARMS for channel in CHANNELS}
        if set(samples) != keys or set(counts) != keys:
            raise ValueError("all eight arm/channel paths required before production")
        for key in keys:
            if len(samples[key]) != 3 or any(not math.isfinite(x) or x <= 0 for x in samples[key]) or type(counts[key]) is not int or counts[key] <= 0:
                raise ValueError("each path requires three finite positive warmed measurements")
        paths = [{"arm": arm, "channel": c, "unit_count": counts[arm, c], "warmed_seconds": samples[arm, c],
                  "median_seconds": statistics.median(samples[arm, c])} for arm, c in sorted(keys)]
        remaining = sum(v["median_seconds"] * v["unit_count"] for v in paths)
        F = self.science_elapsed() + remaining
        self.science_cap = min(1.5 * F + 360, CAP, self.a["allocated_gpu_seconds"])
        required = 1.5 * remaining + RESERVE
        available = min(self.a["deadline_epoch"] - self.now(), self.science_cap - self.science_elapsed())
        return {"paths": paths, "F_seconds": F, "forecast_remaining_seconds": remaining,
                "science_cap_seconds": self.science_cap, "provider_elapsed_seconds": self.elapsed(),
                "science_elapsed_seconds": self.science_elapsed(), "required_remaining_seconds": required,
                "available_seconds": available, "fit": required <= available,
                "budget_clock_resets": 0, "includes_setup": True, "all_paths_warmed": True,
                "timing_scores_retained": False, "retrieval_reserve_seconds": RESERVE}


def verify_assignment(a, args):
    checks = {"input_seal_sha256": args.inputs / "INPUT_SEAL.json", "assets_sha256": args.assets,
              "checkpoint_receipt_sha256": args.checkpoint_receipt, "predecessors_sha256": args.predecessors,
              "parity_gate_sha256": args.parity_gate, "plan_sha256": HERE / "PLAN.json"}
    for key, path in checks.items():
        if a.get(key) != sha(path):
            raise ValueError("assignment binding mismatch: " + key)
    if sha(args.parity_gate) != sha(HERE / "PARITY_GATE.json"):
        raise ValueError("runtime parity policy differs from frozen source")
    required = {PREFIX + name for name in ("runtime.py", "PLAN.json", "PARITY_GATE.json", "checkpoint_cpu.py", "CHECKPOINT_MANIFEST_2026-10-26.json")}
    required |= {BASE_RUNTIME, "projects/g_agreement/manifest/assets.json"}
    pins = a.get("source_files", {})
    if not required <= set(pins):
        raise ValueError("complete E37 runtime/plan/gate and reused E33 source pins required")
    for name, expected in pins.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or sha(path) != expected:
            raise ValueError("source pin mismatch")
    provenance = read(args.inputs / "provenance.json")
    if provenance.get("plan_sha256") != a["plan_sha256"]:
        raise ValueError("inputs were built from another scientific plan")
    return {key: sha(path) for key, path in checks.items()}


def unit_plan(items, templates):
    return {channel: [{"channel": channel, "feature": feature, "indices": ix[start:start + 16]}
                       for feature in sorted({r["feature"] for r in items} if channel == "C4" else templates[channel])
                       for ix in [[i for i, r in enumerate(items) if r["feature"] == feature]]
                       for start in range(0, len(ix), 16)] for channel in CHANNELS}


def auroc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if len(scores) != len(labels) or not pos or not neg or not all(math.isfinite(s) for s in scores):
        raise ValueError("finite two-class AUROC required")
    return sum((a > b) + .5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))


def injected_embeddings(model, ids, vectors, carrier):
    """Exact native Oracle replacement: input embedding[marker] = 16000*unit(h44)."""
    import torch
    E33.assert_no_hooks(model)
    embeddings = model.get_input_embeddings()(ids).clone()
    h = torch.as_tensor(vectors, device=ids.device, dtype=torch.float32)
    if h.ndim != 2 or h.shape[0] != ids.shape[0] or h.shape[1] != embeddings.shape[2] or not torch.isfinite(h).all():
        raise ValueError("one finite source activation per sequence required")
    embeddings[:, carrier["marker_index"], :] = (carrier["alpha"] * h / h.norm(dim=-1, keepdim=True).clamp_min(1e-9)).to(embeddings.dtype)
    return embeddings


def score_unit(model, tok, unit, items, activations, pairs, carrier, device="cuda"):
    import torch
    channel, feature, ix = unit["channel"], unit["feature"], unit["indices"]
    head = carrier["head_ids"] + carrier["prefix_ids"][channel]
    columns = []
    with torch.inference_mode():
        for pair in pairs[channel][feature]:
            seqs, masks, headlen, lengths = E33.build_sequences([head] * len(ix), pair, tok.pad_token_id or 0)
            ids, mask = torch.tensor(seqs, device=device), torch.tensor(masks, device=device)
            h = torch.as_tensor(activations[ix], device=device, dtype=torch.float32).repeat_interleave(2, dim=0)
            embeds = injected_embeddings(model, ids, h, carrier)
            logits = model(inputs_embeds=embeds, attention_mask=mask, logits_to_keep=len(seqs[0]) - headlen + 1, use_cache=False).logits
            if logits.shape[1] != len(seqs[0]) - headlen + 1:
                raise ValueError("exact candidate predictive window required")
            lp = torch.log_softmax(logits[:, :-1].float(), dim=-1)
            values = lp.gather(-1, ids[:, headlen:].unsqueeze(-1)).squeeze(-1)
            columns.append([float(values[2 * i, :lengths[0]].sum() - values[2 * i + 1, :lengths[1]].sum()) for i in range(len(ix))])
    result = []
    for j, index in enumerate(ix):
        values = [v[j] for v in columns]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("nonfinite native paired log-odds")
        result.append({"id": items[index]["id"], "feature": feature, "channel": channel,
                       "control": "matched", "scores": values, "score": sum(values) / len(values)})
    return result


def free_unit(model, tok, unit, items, activations, carrier, device="cuda", benchmark=False):
    import torch
    ix = unit["indices"]
    head = carrier["head_ids"] + carrier["prefix_ids"]["C4"]
    ids = torch.tensor([head] * len(ix), device=device)
    with torch.inference_mode():
        embeddings = injected_embeddings(model, ids, activations[ix], carrier)
        timing_only = {"eos_token_id": None, "forced_eos_token_id": None, "min_new_tokens": 0, "stop_strings": None} if benchmark else {}
        output = model.generate(inputs_embeds=embeddings, attention_mask=torch.ones_like(ids), do_sample=False,
                                num_beams=1, max_new_tokens=128, pad_token_id=tok.pad_token_id or tok.eos_token_id, **timing_only)
        if benchmark and output.shape[1] != 128:
            raise ValueError("timing-only C4 must measure all 128 decode steps")
        raw = tok.batch_decode(output, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    if len(raw) != len(ix) or any(not isinstance(s, str) for s in raw):
        raise ValueError("complete raw native free unit required")
    return [{"id": items[i]["id"], "feature": items[i]["feature"], "raw": text} for i, text in zip(ix, raw)]


def activate(model, arm):
    model.set_adapter("default" if arm == "RL" else "sft")
    model.requires_grad_(False)
    model.eval()
    E33.assert_no_hooks(model)


def verify_adapter_parameters(model, folder, adapter):
    """Check every checkpoint tensor actually loaded; no equality between arms is assumed."""
    import torch
    from safetensors import safe_open
    params = dict(model.named_parameters())
    matched = 0
    with safe_open(str(Path(folder) / "adapter_model.safetensors"), framework="pt", device="cpu") as source:
        keys = list(source.keys())
        for key in keys:
            named = key.replace("lora_A.weight", f"lora_A.{adapter}.weight").replace("lora_B.weight", f"lora_B.{adapter}.weight")
            options = {named, named.replace(".model.language_model.", ".model."), named.replace(".model.layers.", ".model.language_model.layers.")}
            found = [p for p in options if p in params]
            if len(found) != 1:
                raise ValueError("adapter tensor has no unique compatible model parameter")
            expected, actual = source.get_tensor(key), params[found[0]].detach().cpu()
            if expected.shape != actual.shape or not torch.equal(expected.to(actual.dtype), actual):
                raise ValueError("adapter tensor shape or loaded value differs from frozen checkpoint")
            matched += 1
    if not matched:
        raise ValueError("empty adapter checkpoint")
    config = read(Path(folder) / "adapter_config.json")
    return {"matched_tensors": matched, "all_tensors_matched": matched == len(keys),
            "config_sha256": sha(Path(folder) / "adapter_config.json"),
            "config": {k: config.get(k) for k in ("peft_type", "r", "lora_alpha", "target_modules", "use_rslora", "use_dora", "rank_pattern", "alpha_pattern", "modules_to_save")}}


def run_parity(model, tok, items, activations, token_pairs, carrier, parity, labels, budget):
    result = {"status": "PASS", "smoke": {}, "RL_row_auroc": {}, "reference_arm": "within each arm; never SFT==RL"}
    result["gate_order"] = "RL_three_row_reproduction_then_RL_smoke_then_SFT_smoke"
    activate(model, "RL")
    for feature in PARITY_ROWS:
        records = []
        ix = [i for i, item in enumerate(items) if item["feature"] == feature]
        for start in range(0, len(ix), 16):
            budget.guard()
            records.extend(score_unit(model, tok, {"channel": "C1", "feature": feature, "indices": ix[start:start + 16]},
                                      items, activations, token_pairs, carrier))
            budget.guard()
        value = auroc([r["score"] for r in records], [labels[r["id"]] for r in records])
        reference = parity["rl_reference_auc"][feature]
        result["RL_row_auroc"][feature] = {"n": len(records), "observed": value, "W1_reference": reference,
                                          "absolute_delta": abs(value - reference), "threshold": .03}
        if not math.isfinite(reference) or abs(value - reference) > .03:
            result["status"] = "FAIL"
            return result
    for arm in ARMS:
        activate(model, arm)
        errors = []
        for feature in sorted({r["feature"] for r in items if r["id"] in parity["smoke_ids"]}):
            ix = [i for i, item in enumerate(items) if item["id"] in parity["smoke_ids"] and item["feature"] == feature]
            unit = {"channel": "C1", "feature": feature, "indices": ix}
            budget.guard()
            first = score_unit(model, tok, unit, items, activations, token_pairs, carrier)
            budget.guard()
            second = score_unit(model, tok, unit, items, activations, token_pairs, carrier)
            budget.guard()
            for a, b in zip(first, second):
                errors.extend(abs(x - y) for x, y in zip(a["scores"], b["scores"]))
                errors.append(abs(a["score"] - b["score"]))
        largest = max(errors)
        result["smoke"][arm] = {"items": 20, "max_abs_self_repeat_delta": largest, "threshold": 1e-4,
                                      "finite": all(math.isfinite(v) for v in errors)}
        if not result["smoke"][arm]["finite"] or largest > 1e-4:
            result["status"] = "FAIL"
            return result
    return result


def representative(units, token_pairs, channel):
    if channel == "C4":
        return max(units, key=lambda u: len(u["indices"]))
    return max(units, key=lambda u: (len(u["indices"]), sum(max(map(len, pair)) for pair in token_pairs[channel][u["feature"]])))


def preflight(args):
    checkpoint = checkpoint_receipt(args.checkpoint_receipt)
    cpu_path = Path(checkpoint["cpu_tensor_check_path"])
    if sha(cpu_path) != checkpoint["cpu_tensor_check_sha256"]:
        raise ValueError("CPU selection receipt changed")
    cpu = CPU.validate_selection(read(cpu_path), checkpoint["local_path"])
    if (cpu["selected_files"] != checkpoint["files"] or cpu["selected_branch"] != checkpoint["selected_branch"]
            or cpu["received_epoch"] != checkpoint["received_epoch"]
            or cpu["readme_identity_claim_verified"] != checkpoint["readme_identity_claim_verified"]):
        raise ValueError("checkpoint receipt differs from pre-forward CPU selection")
    predecessors(args.predecessors)
    validate_parity_policy(args.parity_gate)
    assignment = read(args.assignment)
    budget = Budget(assignment)
    bindings = verify_assignment(assignment, args)
    bindings["cpu_tensor_check_sha256"] = sha(cpu_path)
    inputs = load_inputs(args.inputs)
    budget.guard()
    return checkpoint, assignment, budget, bindings, inputs


def run(args):
    checkpoint, assignment, budget, bindings, data = preflight(args)
    items, activations, templates, token_pairs, carrier, parity, labels = data
    if "cache" not in args.out.resolve().parts:
        raise ValueError("raw E37 outputs belong in ignored cache")
    args.out.mkdir(parents=True, exist_ok=False)
    for name, path in (("checkpoint_receipt.json", args.checkpoint_receipt), ("parity_gate.json", args.parity_gate),
                       ("predecessors.json", args.predecessors),
                       ("CPU_TENSOR_CHECK.json", Path(checkpoint["cpu_tensor_check_path"]))):
        with (args.out / name).open("xb") as f:
            f.write(path.read_bytes())
    status, stage, error_type = "INCOMPLETE", "asset_verification", None
    try:
        budget.install_alarm()
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", WANDB_MODE="disabled")
        assets = E33.verify_assets(args.assets, budget)
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        torch.manual_seed(20261025)
        torch.cuda.manual_seed_all(20261025)
        provenance = read(args.inputs / "provenance.json")
        for name, expected in provenance["tokenizer_files"].items():
            if sha(Path(assets["model"]) / name) != expected:
                raise ValueError("runtime tokenizer differs from frozen carrier tokenizer")
        stage = "model_load"
        tok = AutoTokenizer.from_pretrained(assets["model"], local_files_only=True)
        for channel, features in templates.items():
            for feature, pairs in features.items():
                if [[tok.encode(t, add_special_tokens=False) for t in p] for p in pairs] != token_pairs[channel][feature]:
                    raise ValueError("candidate tokenization differs from frozen native pairs")
        if (any(carrier["prefix_ids"][c] for c in ("C1", "C1prime", "C4")) or
                carrier["prefix_ids"]["C2"] != tok.encode("- ", add_special_tokens=False)):
            raise ValueError("exact channel-specific native prefix contract required")
        model = AutoModelForCausalLM.from_pretrained(assets["model"], dtype=torch.bfloat16, device_map="cuda", local_files_only=True).eval()
        model = PeftModel.from_pretrained(model, assets["olens"], is_trainable=False, local_files_only=True).eval()
        model.load_adapter(checkpoint["local_path"], adapter_name="sft", is_trainable=False, local_files_only=True)
        model.requires_grad_(False)
        loading = {"RL": verify_adapter_parameters(model, assets["olens"], "default"),
                   "SFT": verify_adapter_parameters(model, checkpoint["local_path"], "sft")}
        write_new(args.out / "LOAD_CHECK.json", {"status": "PASS", "arms": loading,
                  "config_differences_are_recorded_not_rejected": True, "backbone_loads": 1, "training": False})
        budget.guard()
        budget.start()
        stage = "registered_parity"
        parity_result = run_parity(model, tok, items, activations, token_pairs, carrier, parity, labels, budget)
        write_new(args.out / "PARITY_RESULT.json", parity_result)
        if parity_result["status"] != "PASS":
            raise ValueError("registered parity failed; no production authorized")
        stage = "warmed_forecast"
        plans, samples, warmups = unit_plan(items, templates), {}, {}
        for arm in ARMS:
            activate(model, arm)
            for channel in CHANNELS:
                unit = representative(plans[channel], token_pairs, channel)
                def call():
                    if channel == "C4":
                        return free_unit(model, tok, unit, items, activations, carrier, benchmark=True)
                    return score_unit(model, tok, unit, items, activations, token_pairs, carrier)
                budget.guard()
                torch.cuda.synchronize()
                begin = time.monotonic()
                call()
                torch.cuda.synchronize()
                warmups[arm, channel] = time.monotonic() - begin
                budget.guard()
                samples[arm, channel] = []
                for _ in range(3):
                    budget.guard()
                    torch.cuda.synchronize()
                    begin = time.monotonic()
                    call()
                    torch.cuda.synchronize()
                    samples[arm, channel].append(time.monotonic() - begin)
                    budget.guard()
        forecast = budget.forecast(samples, {(a, c): len(plans[c]) for a in ARMS for c in CHANNELS})
        budget.guard()
        forecast["warmups"] = [{"arm": a, "channel": c, "seconds": s} for (a, c), s in warmups.items()]
        forecast["C4_timing_only"] = "128 decode steps with EOS termination disabled; all calibration outputs discarded"
        forecast["C4_production"] = "unchanged E24 native greedy, normal EOS, max_new_tokens=128"
        forecast["C2_opposite"] = "exact E15 donor-ID reassignment of matched scores; no additional forwards"
        write_new(args.out / "WARMED_FORECAST.json", forecast)
        if not forecast["fit"]:
            raise NoFit("entire registered two-arm four-channel grid does not fit")
        stage = "production"
        score_keys, free_keys = set(), set()
        with (args.out / "scores.jsonl").open("x") as sf, (args.out / "free.jsonl").open("x") as ff:
            for arm in ARMS:
                activate(model, arm)
                matched_c2 = {}
                for channel in CHANNELS:
                    for unit in plans[channel]:
                        budget.guard()
                        values = (free_unit(model, tok, unit, items, activations, carrier) if channel == "C4" else
                                  score_unit(model, tok, unit, items, activations, token_pairs, carrier))
                        budget.guard()
                        for value in values:
                            value["arm"] = arm
                            if channel == "C4":
                                key, handle = (arm, value["id"]), ff
                                if key in free_keys:
                                    raise ValueError("duplicate free output")
                                free_keys.add(key)
                            else:
                                key, handle = (arm, channel, "matched", value["id"]), sf
                                if key in score_keys:
                                    raise ValueError("duplicate paired score")
                                score_keys.add(key)
                                if channel == "C2":
                                    matched_c2[value["id"]] = value
                            handle.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
                        sf.flush()
                        ff.flush()
                for item in items:
                    if item["feature"] not in C2_ROWS:
                        continue
                    donor = matched_c2[item["donor_id"]]
                    value = {**donor, "id": item["id"], "control": "opposite", "donor_id": item["donor_id"]}
                    score_keys.add((arm, "C2", "opposite", item["id"]))
                    sf.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
                sf.flush()
        expected = {(a, c, "matched", r["id"]) for a in ARMS for c in ("C1", "C1prime", "C2") for r in items
                    if c != "C2" or r["feature"] in C2_ROWS}
        expected |= {(a, "C2", "opposite", r["id"]) for a in ARMS for r in items if r["feature"] in C2_ROWS}
        if score_keys != expected or len(score_keys) != 10752 or free_keys != {(a, r["id"]) for a in ARMS for r in items}:
            raise ValueError("full registered 10752 paired scores and 4200 free outputs required")
        budget.guard()
        status, stage = "COMPLETE", "complete"
    except Exception as exc:
        status = "NO_FIT" if isinstance(exc, NoFit) else "INCOMPLETE"
        error_type = type(exc).__name__
    finally:
        budget.close_alarm()
        parity_hash = sha(args.out / "PARITY_RESULT.json") if (args.out / "PARITY_RESULT.json").is_file() else None
        provenance = {**bindings, "source_files": assignment["source_files"], "parity_result_sha256": parity_hash,
                      "status": status, "arms": list(ARMS), "channels": list(CHANNELS), "training": False,
                      "activation_layer": 44, "activation_injection": "native 16000*unit(h44) embedding replacement",
                      "arrival_deadline_is_launch_deadline": False, "checkpoint_received_epoch": checkpoint["received_epoch"],
                      "checkpoint_identity": checkpoint["checkpoint_identity"], "scope_reduction": False,
                      "selected_branch": checkpoint["selected_branch"],
                      "readme_identity_claim_verified": checkpoint["readme_identity_claim_verified"],
                      "raw_free_preserved": True, "all_science_labels_used_only_for_registered_252_item_parity": True}
        write_new(args.out / "provenance.json", provenance)
        write_new(args.out / "RUN.json", {**bindings, "experiment": "E37", "status": status,
                  "failure_stage": None if status == "COMPLETE" else stage, "error_type": error_type,
                  "provider_elapsed_seconds_at_worker_exit": budget.elapsed(), "science_elapsed_seconds": budget.science_elapsed(),
                  "science_cap_seconds": budget.science_cap, "allocated_gpu_seconds": assignment["allocated_gpu_seconds"],
                  "budget_includes_setup": True, "budget_clock_resets": 0, "GPU_count": 1,
                  "source_files": assignment["source_files"], "retry_authorized": False})
        write_new(args.out / "SCORE_SEAL.json", {"status": "E37_" + status,
                  "files": {p.name: sha(p) for p in sorted(args.out.iterdir()) if p.is_file()}})
    print("E37_" + status)
    return 0 if status == "COMPLETE" else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("run", "validate"):
        sub = commands.add_parser(name)
        for field in ("inputs", "assets", "checkpoint-receipt", "predecessors", "parity-gate", "assignment"):
            sub.add_argument("--" + field, type=Path, required=True)
        if name == "run":
            sub.add_argument("--out", type=Path, required=True)
    status = commands.add_parser("status")
    status.add_argument("--checkpoint-receipt", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.command == "status":
            checkpoint_receipt(args.checkpoint_receipt)
            print("CHECKPOINT_RECEIVED_ON_TIME")
            return 0
        if args.command == "validate":
            preflight(args)
            print("E37_CPU_PREFLIGHT_PASS")
            return 0
        return run(args)
    except Blocked as exc:
        print(exc.status)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
