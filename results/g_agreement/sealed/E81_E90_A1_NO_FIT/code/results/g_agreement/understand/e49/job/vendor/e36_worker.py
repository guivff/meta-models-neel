"""Single-GPU E36 worker; v2 labels remain CPU-only.

Only §137's separate sealed 252 W1 parity labels/reference AUROCs are loaded.
All model operations occur only in main/run_worker, never on module import.
"""
from __future__ import annotations

import argparse
import ast
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import channel_contract as C
import parity_gate as G

PHASES = C.PHASES
BATCH = 8


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def frozen_function(root, relative, name, expected, namespace=None):
    """Compile one hash-verified operational function; never import data loaders."""
    source = (Path(root) / relative).read_text()
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name]
    C.require(len(nodes) == 1, "missing operational function")
    snippet = ast.get_source_segment(source, nodes[0])
    C.require(hashlib.sha256(snippet.encode()).hexdigest() == expected, "operational recipe changed: " + name)
    scope = {} if namespace is None else dict(namespace)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), relative, "exec"), scope)
    return scope[name]


def verify_source_bindings(plan, root):
    """The code that will be imported must be the code whose hashes were bound."""
    root = Path(root).resolve()
    for relative in C.REQUIRED_SOURCE_PATHS:
        bindings = [b for b in plan["source_bindings"] if Path(b["path"]).as_posix().endswith(relative)]
        C.require(len(bindings) == 1, "missing or ambiguous source binding: " + relative)
        C.require(Path(bindings[0]["path"]).resolve() == (root / relative).resolve(), "runtime root differs from bound sources")
    for binding in plan["source_bindings"]:
        C.require(C.file_hash(binding["path"]) == binding["sha256"], "source binding mismatch")


def verify_assets_binding(plan, assets_path, root):
    """Bind both the local model inventory and the registered revision source."""
    C.require(Path(assets_path).resolve() == Path(plan["assets"]["path"]).resolve(), "runtime assets differ from bound manifest")
    local = C.read_bound(plan["assets"])
    relative = "projects/g_agreement/manifest/assets.json"
    registry_binding = next(b for b in plan["source_bindings"] if Path(b["path"]).as_posix().endswith(relative))
    C.require(Path(registry_binding["path"]).resolve() == (Path(root) / relative).resolve(), "wrong registered asset source")
    registered = C.read_bound(registry_binding)
    revisions = {"model": registered["target"]["revision"],
                 **{name: registered["readers"][name]["revision"] for name in ("olens", "nla")}}
    C.require(revisions == C.REGISTERED_REVISIONS == plan["registered_revisions"], "registered model revision mismatch")
    C.require(all(local.get("revisions", {}).get(k) == v for k, v in revisions.items()), "local asset revision mismatch")
    C.require(bool(local.get("files")), "bound asset inventory requires file hashes")
    # Native operational._assets additionally checks every local file hash,
    # complete inventory coverage and the registered tokenizer/adapter digests.
    return local


class Budget:
    def __init__(self, assignment, out, clock=time.time, cap_gpu_seconds=C.CAP_GPU_SECONDS):
        self.assignment, self.out, self.clock = assignment, Path(out), clock
        self.cap_gpu_seconds = cap_gpu_seconds
        self.remaining = dict(assignment["phase_estimates_seconds"])
        C.require(set(self.remaining) == set(PHASES), "all phase estimates required")
        C.require(all(isinstance(x, (float, int)) and x >= 0 for x in self.remaining.values()), "invalid phase estimate")
        self.observed = {}
        self.setup_deadline = (assignment['allocation_started_at'] + C.SETUP_ALLOWANCE_SECONDS
                               if cap_gpu_seconds == C.EXPANDED_CAP_GPU_SECONDS else None)
        self.science_started_at = self.science_deadline = None

    def check(self):
        a = self.assignment
        now = self.clock()
        if self.setup_deadline is not None and self.science_started_at is None:
            C.require(now <= self.setup_deadline, 'post-creation setup deadline exceeded')
        deadline = a['hard_deadline'] if self.science_deadline is None else min(a['hard_deadline'], self.science_deadline)
        gate = C.forecast_gate(prior_gpu_seconds=a["prior_gpu_seconds"], allocation_started_at=a["allocation_started_at"],
                              now=now, remaining_work_seconds=sum(self.remaining.values()), hard_deadline=deadline,
                              cap_gpu_seconds=self.cap_gpu_seconds)
        dump(self.out / "budget.latest.json", gate)
        C.require(gate["fits"], "warm forecast does not fit; stop without retries or scope cuts")
        return gate

    def start_science(self):
        if self.setup_deadline is None:
            return
        C.require(self.science_started_at is None, 'science clock cannot be reset')
        self.check()
        self.science_started_at = self.clock()
        C.require(self.science_started_at <= self.setup_deadline, 'post-creation setup deadline exceeded')
        self.science_deadline = min(self.assignment['hard_deadline'], self.science_started_at +
                                   C.science_cap_seconds(self.assignment['warmed_forecast_seconds']))
        dump(self.out / 'science_clock.json', {'setup_deadline': self.setup_deadline,
             'science_started_at': self.science_started_at, 'science_deadline': self.science_deadline,
             'setup_allowance_seconds': C.SETUP_ALLOWANCE_SECONDS, 'setup_counts_in_aggregate': True})
        self.check()

    def call(self, phase, fn, remaining_units=0):
        self.check()
        previous_forecast = self.remaining[phase]
        started = self.clock()
        result = fn()
        elapsed = max(0., self.clock() - started)
        self.observed[phase] = max(elapsed, self.observed.get(phase, 0.))
        # Warm measurements can tighten upward; one easy first batch must not
        # erase the integrator's conservative estimate for later/longer inputs.
        carried_forecast = previous_forecast * remaining_units / (remaining_units + 1)
        self.remaining[phase] = max(self.observed[phase] * remaining_units, carried_forecast)
        self.check()
        return result

    def complete_empty(self, phase):
        self.remaining[phase] = 0.
        self.check()


class NativeBackend:
    """Existing verified native APIs with E36 inputs supplied explicitly."""
    def __init__(self, root, assets, assignment=None):
        self.root, self.assets_path = Path(root), assets
        self.oracle = self.nla = None
        self.assignment = assignment or {"gpu_type": "H200"}

    def load_oracle(self):
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        import torch
        C.require(torch.cuda.is_available() and torch.cuda.device_count() == 1, "assigned execution requires exactly one visible GPU")
        gpu_type = self.assignment["gpu_type"]
        name = torch.cuda.get_device_name(0)
        expected = "H100" if gpu_type == "H100_80GB" else gpu_type
        C.require(expected in name, "visible GPU differs from verified assignment")
        if gpu_type != "H200":
            C.validate_gpu_assignment(self.assignment, time.time())
            memory = torch.cuda.get_device_properties(0).total_memory
            C.require(memory >= self.assignment["gpu_fallback"]["memory_check"]["required_bytes"], "actual GPU fails memory check")
            if gpu_type == "H100_80GB":
                C.require(memory >= 80_000_000_000, "H100 fallback requires the 80 GB device")
        from projects.g_agreement.blindspot import run as operational
        assets = operational._assets(self.assets_path, names=("model", "olens"))
        self.oracle = operational._load_oracle(assets)

    def validate_tokenization(self, items):
        for x in items:
            encoded = self.oracle.tok.encode(x["text"], add_special_tokens=False)
            C.require(encoded == x["ids"], "stage tokenization differs from target tokenizer")

    def capture(self, items):
        import torch
        from mats.capture import capture
        with self.oracle.base(), torch.no_grad():
            tensors = capture(self.oracle.model, [x["ids"] for x in items], [42, 44],
                              [[len(x["ids"]) - 1] for x in items], batch_size=BATCH,
                              pad_id=self.oracle.tok.pad_token_id or 0)
        result = {}
        for block in (42, 44):
            h = tensors[block]
            C.require(h.ndim == 3 and tuple(h.shape[:2]) == (len(items), 1) and bool(torch.isfinite(h).all()), "invalid native capture")
            result[block] = h[:, 0].float().cpu().numpy()
        return result

    def join(self, parts):
        import numpy as np
        return np.concatenate(parts, axis=0)

    def take(self, h, indices):
        import torch
        return torch.as_tensor(h[indices])

    def save_capture(self, path, h):
        import numpy as np
        np.save(path, h, allow_pickle=False)

    def score(self, channel, items, activations, pairs):
        import torch
        with torch.no_grad():
            if channel == "nla":
                from mats.readers.nla import paired_logodds_templates
                values = paired_logodds_templates(self.nla, activations, pairs, prefix="<explanation>\n", batch=BATCH)
            else:
                prefix = "- " if channel == "continuation" else ""
                values = self.oracle.paired_logodds_templates(activations, 44, pairs, prefix=prefix)
        C.require(values.ndim == 2 and tuple(values.shape) == (len(pairs), len(items)) and bool(torch.isfinite(values).all()), "invalid score matrix")
        return values.detach().float().cpu().T.tolist()

    def load_nla(self):
        import torch
        self.oracle = None
        gc.collect()
        torch.cuda.empty_cache()
        from projects.g_agreement.blindspot import run as operational
        from mats.readers.nla import load_nla
        assets = operational._assets(self.assets_path, names=("nla",))
        self.nla = load_nla(root=assets["nla"], load_ar=False, enable_thinking=False)


def score_jobs(items, candidates, channel, scope=None):
    scope = C.validate_scope(scope)
    spec = C.CHANNELS[channel]
    jobs = []
    for feature in scope["rows"]:
        selected = [i for i, x in enumerate(items) if x["feature"] == feature and x["split"] == spec["split"]]
        source = candidates["rows"][feature][spec["candidate_key"]]
        variants = source.items() if channel == "oracle_value_word" else [(None, source)]
        for variant, pairs in variants:
            if not pairs:
                continue
            for start in range(0, len(selected), BATCH):
                jobs.append((selected[start:start + BATCH], variant, pairs))
    return jobs


def run_pipeline(items, candidates, backend, budget, out, scope=None, *, parity_inputs):
    """Runnable acquisition core; fake backend tests exercise the same ordering."""
    scope = C.validate_scope(scope)
    C.validate_items(items, scope)
    C.validate_candidates(candidates, scope)
    out = Path(out)
    budget.call("oracle_setup", backend.load_oracle)
    budget.start_science()  # The full parity gate is inside the unchanged science clock.
    G.run_gate(backend, budget, out, parity_inputs)
    backend.validate_tokenization(items)
    chunks = [items[i:i + BATCH] for i in range(0, len(items), BATCH)]
    parts = {42: [], 44: []}
    for k, chunk in enumerate(chunks):
        captured = budget.call("capture", lambda: backend.capture(chunk), len(chunks) - k - 1)
        for block in parts:
            parts[block].append(captured[block])
    dump(out / 'capture.audit.json', {
        'batch_size': BATCH, 'padding_side': 'right', 'blocks': [42, 44],
        'items': [{'id': x['id'], 'feature': x['feature'], 'length': len(x['ids']),
                   'padding_tokens': max(len(y['ids']) for y in chunk) - len(x['ids'])}
                  for chunk in chunks for x in chunk]})
    acts = {block: backend.join(values) for block, values in parts.items()}
    for block, values in acts.items():
        backend.save_capture(out / f"acts{block}.npy", values)
    dump(out / "items.order.json", [x["id"] for x in items])
    score_file = out / "scores.jsonl"
    with score_file.open("x") as stream:
        for channel in ("oracle_descriptive", "oracle_value_word", "continuation", "nla"):
            if channel == "nla":
                budget.call("nla_setup", backend.load_nla)
            jobs = score_jobs(items, candidates, channel, scope)
            if not jobs:
                budget.complete_empty(channel)
            for k, (indices, variant, pairs) in enumerate(jobs):
                selected = [items[i] for i in indices]
                block = C.CHANNELS[channel]["block"]
                h = None if block is None else backend.take(acts[block], indices)
                matrix = budget.call(channel, lambda: backend.score(channel, selected, h, pairs), len(jobs) - k - 1)
                C.require(len(matrix) == len(selected) and all(len(x) == len(pairs) for x in matrix), "missing score cell")
                for item, scores in zip(selected, matrix):
                    C.require(all(isinstance(v, (int, float)) and __import__("math").isfinite(v) for v in scores), "invalid numeric score")
                    record = {"id": item["id"], "feature": item["feature"], "split": item["split"],
                              "channel": channel + (":" + variant if variant is not None else ""),
                              "block": block, "scores": scores, "status": "COMPLETE"}
                    stream.write(json.dumps(record, allow_nan=False) + "\n")
                stream.flush()
    return {"items": len(items), "scope_id": scope["id"], "capture_blocks": [42, 44], "label_free": True}


def run_worker(plan, assignment, root, assets, out):
    C.validate_assignment(assignment, plan, time.time())
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)  # Never resume/retry a partial attempt.
    budget = Budget(assignment, out, cap_gpu_seconds=plan["cap_gpu_seconds"])
    started = time.time()
    status, error = "ABORTED", None
    try:
        budget.check()
        verify_source_bindings(plan, root)
        verify_assets_binding(plan, assets, root)
        parity_inputs = G.load_inputs(plan['parity_inputs'])
        import importlib.metadata
        dump(out / 'environment.json', {'executable': sys.executable, 'python': sys.version,
             'packages': {name: importlib.metadata.version(name) for name in ('torch', 'transformers', 'peft')},
             'source_bindings': plan['source_bindings']})
        # Reading freeze/candidates is possible only after a valid bound plan.
        freeze = C.read_bound(plan["freeze"])
        C.validate_freeze_receipt(freeze, plan["bank"], plan["scope"])
        items = C.read_bound(plan["bank"], jsonl=True)
        candidates = C.read_bound(plan["candidates"])
        dump(out / "plan.json", plan)
        result = run_pipeline(items, candidates, NativeBackend(root, assets, assignment), budget, out,
                              plan["scope"], parity_inputs=parity_inputs)
        dump(out / "acquisition.json", result)
        status = "COMPLETE"
    except BaseException as exc:
        error = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        now = time.time()
        dump(out / "runtime.json", {"status": status, "error": error, "worker_started_at": started, "finished_at": now,
             "allocation_started_at": assignment["allocation_started_at"], "prior_gpu_seconds": assignment["prior_gpu_seconds"],
             "current_allocation_gpu_seconds": now - assignment["allocation_started_at"], "setup_included": True,
             "retrieval_reserve_seconds": C.RETRIEVAL_SECONDS, "operator": "integrator", "pod_id": assignment["pod_id"],
             "scope_id": plan["scope"]["id"], "cap_gpu_seconds": plan["cap_gpu_seconds"], "gpu_type": assignment["gpu_type"],
             "gpu_fallback": assignment.get("gpu_fallback"),
             "setup_deadline": budget.setup_deadline, "science_started_at": budget.science_started_at,
             "science_deadline": budget.science_deadline,
             "external_stop": assignment["external_stop"], "plan_sha256": plan["plan_sha256"]})
        if status == "COMPLETE":
            files = {p.name: C.file_hash(p) for p in sorted(out.iterdir()) if p.is_file()}
            dump(out / "OUTPUT_SEAL.json", {"experiment": "E36", "plan_sha256": plan["plan_sha256"], "files": files})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--assignment", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    # Resolve CLI locations from the caller, then resolve portable plan bindings
    # from the explicitly assigned checkout regardless of the launcher's cwd.
    paths = {name: Path(getattr(args, name)).resolve() for name in ('plan', 'assignment', 'assets', 'out')}
    os.chdir(root)
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "external/mats-nla-workspace/src"))
    run_worker(json.loads(paths['plan'].read_text()), json.loads(paths['assignment'].read_text()),
               root, paths['assets'], paths['out'])


if __name__ == "__main__":
    main()
