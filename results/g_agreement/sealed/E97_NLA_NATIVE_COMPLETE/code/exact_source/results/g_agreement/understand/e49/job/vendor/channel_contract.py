"""E36's outcome-blind channel contract, binding checks and CPU adjudication.

Written before any E36 capture. This module never discovers or loads W1 data.
Candidate files must be supplied explicitly *after* the independent bank freeze.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

STATES = ("prose_paren", "python_string", "table_role", "python_indent")
POSITIONS = ("table_column", "list_index")
CONTENT = ("prose_sentiment", "prose_topic")
STRUCTURE = STATES + POSITIONS
ROWS = STRUCTURE + CONTENT
CAP_GPU_SECONDS = 10800
EXPANDED_CAP_GPU_SECONDS = 60000  # §143, 4ad4dcbc; no scientific changes.
MIN_PRIOR_GPU_SECONDS = 552.8
SETUP_ALLOWANCE_SECONDS = 900  # §146 addendum 2; inside aggregate custody, outside science +360.
POD_BUDGET = {"max_pods": 1, "row_sharding": False, "max_seconds": 59447,
              "forecast_multiplier": 1.5, "overhead_seconds": 360,
              "setup_allowance_seconds": SETUP_ALLOWANCE_SECONDS,
              "minimum_prior_gpu_seconds": MIN_PRIOR_GPU_SECONDS}
E30_REPLICATION_CAP_GPU_SECONDS = 1800
EXPANDED_FREEZE_DEADLINE = "2026-10-26T12:00:00+01:00"
DEFINITION_PACKET_SHA256 = "2afa8e1202c0d7c181e6f95984b18bd59f99af81fc8cf8f27dcce02e8e38056c"
RULE_AUTHORITY_SHA256 = "f340f29278d0071a84d2a67e236cbf8e7be5ee29185831e57ee97aa6df438f42"
EXPANDED_H4_ROWS = ("prose_paren", "prose_quote", "python_string", "python_indent",
                    "python_depth", "list_depth", "table_role")
EXPANDED_RULE_BINDING = {
    "source_commit": "0cc77a85", "source_section": "132 dated clarification 2",
    "required_counts": {"H1": 11, "H2": 7, "H4": 5, "H5": 11},
    "h4_rows": list(EXPANDED_H4_ROWS),
    "h3_eligibility": "E30_R1_support_rows_conditional_on_E30_R2",
}
RETRIEVAL_SECONDS = 180
SEED = 20261023
REGISTERED_REVISIONS = {
    "model": "6a9e13bd6fc8f0983b9b99948120bc37f49c13e9",
    "olens": "c95215d5d2f6250f20c305ae55c6e4d7569f92dc",
    "nla": "5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f",
}
SCHEMA = "e36.channel-plan.v1"
PHASES = ("oracle_setup", "parity", "capture", "oracle_descriptive",
          "oracle_value_word", "continuation", "nla_setup", "nla")
CONTINUATION_POLICY = "all supplied frozen E15 pairs; arithmetic mean; no v2 dev pair selection"
CHANNELS = {
    "oracle_descriptive": {"block": 44, "candidate_key": "olens_descriptive", "prefix": "", "split": "test"},
    "oracle_value_word": {"block": 44, "candidate_key": "olens_value_word", "prefix": "", "split": "test"},
    "continuation": {"block": 44, "candidate_key": "continuation", "prefix": "- ", "split": "test"},
    "nla": {"block": 42, "candidate_key": "nla", "prefix": "<explanation>\n", "split": "test"},
}
PROBE_RECIPE = {
    "source": "projects/g_agreement/blindspot/analysis.py",
    "function": "grouped_probe",
    "function_sha256": "efb813baaa666fb6c23dc4e12e8dd544c11b24d5d65011096105b186eee0106c",
    "split": "test", "block": 44, "folds": 5, "seed": SEED,
    "lambda": 1e-3, "train_only_standardization": True,
    "group": "cluster", "positive": "values[0]",
}
E15_SOURCE_HASHES = {
    "native_score": "055694c0b53be5a7ff03f442b0b27c3e5beb0e5cbba1a3a4e9176ed71c9cac75",
}
REQUIRED_SOURCE_PATHS = (
    "results/g_agreement/understand/e36/channel_contract.py",
    "results/g_agreement/understand/e36/worker.py",
    "results/g_agreement/understand/e36/parity_gate.py",
    "projects/g_agreement/blindspot/run.py",
    "projects/g_agreement/blindspot/protocol.py",
    "projects/g_agreement/blindspot/analysis.py",
    "projects/g_agreement/understand/e15.py",
    "projects/g_agreement/manifest/assets.json",
    "external/mats-nla-workspace/src/mats/capture.py",
    "external/mats-nla-workspace/src/mats/probes.py",
    "external/mats-nla-workspace/src/mats/readers/olens.py",
    "external/mats-nla-workspace/src/mats/readers/nla.py",
)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_hash(value: str) -> None:
    require(isinstance(value, str) and len(value) == 64 and all(x in "0123456789abcdef" for x in value), "invalid SHA256")


def read_bound(binding: dict, *, jsonl: bool = False):
    """Read only an explicitly named, previously sealed artifact."""
    check_hash(binding["sha256"])
    require(file_hash(binding["path"]) == binding["sha256"], "artifact hash mismatch")
    raw = Path(binding["path"]).read_text()
    return [json.loads(line) for line in raw.splitlines() if line.strip()] if jsonl else json.loads(raw)


def instant(value):
    from datetime import datetime
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(d.tzinfo is not None, "timestamps must include timezone")
    return d


def original_scope():
    return {"id": "original8", "rows": list(ROWS), "structure_rows": list(STRUCTURE),
            "content_rows": list(CONTENT), "h4_rows": list(STATES),
            "cap_gpu_seconds": CAP_GPU_SECONDS, "definition_packet": None}


def scope_from_definition_packet(binding):
    """Use only the coordinator's explicit taxonomy; H4 is still unresolved."""
    require(binding["sha256"] == DEFINITION_PACKET_SHA256, "unregistered definition packet")
    packet = read_bound(binding)
    classes = {row: value["class"] for row, value in packet["rows"].items()}
    require(len(classes) == 25 and set(classes.values()) == {"state-like", "count-like", "semantic"}, "definition taxonomy mismatch")
    structure = [r for r, c in classes.items() if c in {"state-like", "count-like"}]
    content = [r for r, c in classes.items() if c == "semantic"]
    require(len(structure) == 16 and len(content) == 9, "expanded taxonomy counts mismatch")
    return {"id": "expanded25", "rows": list(classes), "structure_rows": structure,
            "content_rows": content, "h4_rows": None, "taxonomy": classes,
            "cap_gpu_seconds": EXPANDED_CAP_GPU_SECONDS, "definition_packet": dict(binding)}


def validate_scope(scope=None):
    scope = original_scope() if scope is None else scope
    require(isinstance(scope, dict), "scope metadata required")
    if scope.get("id") == "original8":
        require(scope == original_scope(), "changed original-eight scope")
    elif scope.get("id") == "expanded25":
        require(scope == scope_from_definition_packet(scope["definition_packet"]), "scope differs from definition packet")
    else:
        raise ValueError("unknown E36 scope")
    return scope


def scope_decision(*, now, expanded_frozen_at=None):
    """Monday noon CET is an exact cutoff, never an inferred local timezone."""
    current, deadline = instant(now), instant(EXPANDED_FREEZE_DEADLINE)
    if expanded_frozen_at is not None:
        frozen = instant(expanded_frozen_at)
        require(frozen <= current, "freeze timestamp is in the future")
        if frozen <= deadline:
            return {"scope_id": "expanded25", "status": "EXPANDED_FROZEN_ON_TIME", "deadline": EXPANDED_FREEZE_DEADLINE}
    if current >= deadline:
        return {"scope_id": "original8", "status": "ORIGINAL_REGISTERED_FALLBACK", "deadline": EXPANDED_FREEZE_DEADLINE}
    return {"scope_id": None, "status": "AWAITING_EXPANDED_FREEZE", "deadline": EXPANDED_FREEZE_DEADLINE}


def validate_rule_binding(scope, rule_binding):
    """Use the exact user clarification, never a scaled or inferred threshold."""
    if scope["id"] == "original8":
        require(rule_binding is None, "original rules cannot be replaced")
        return {"required_counts": {"H1": 4, "H2": 2, "H4": 3, "H5": 4}, "h4_rows": list(STATES)}
    if rule_binding is None:
        return None
    require(set(rule_binding) == set(EXPANDED_RULE_BINDING) | {"authority_receipt"}, "expanded rule authority binding required")
    require({k: v for k, v in rule_binding.items() if k != "authority_receipt"} == EXPANDED_RULE_BINDING,
            "expanded rules differ from user clarification 0cc77a85")
    require(rule_binding == expanded_rule_binding(rule_binding["authority_receipt"]), "expanded authority receipt mismatch")
    require(set(rule_binding["h4_rows"]) <= set(scope["rows"]), "registered H4 rows outside scope")
    return rule_binding


def expanded_rule_binding(authority_binding):
    require(authority_binding.get("sha256") == RULE_AUTHORITY_SHA256, "wrong expanded rule-authority SHA256")
    authority = read_bound(authority_binding)
    require(authority.get("registration_commit") == "0cc77a85" and authority.get("scope") == "expanded25", "wrong rule authority")
    return json.loads(json.dumps({**EXPANDED_RULE_BINDING, "authority_receipt": dict(authority_binding)}))


def validate_freeze_receipt(freeze, bank_binding, scope=None):
    scope = validate_scope(scope)
    count = len(scope["rows"]) * 168
    require(freeze.get("scope") == scope["id"] and freeze.get("item_count") == count, "freeze scope/count mismatch")
    require(freeze.get("bank_sha256") == bank_binding["sha256"], "freeze does not bind stage bank")
    require(freeze.get("definition_packet_sha256") == DEFINITION_PACKET_SHA256, "freeze definition-packet mismatch")
    for key, expected in (("automatic_label_check", count), ("automatic_length_check", count // 2)):
        check = freeze.get(key, {})
        require(check.get("status") == "PASS" and check.get("checked") == expected and check.get("passed") == expected,
                key + " must pass for the entire frozen bank")
        check_hash(check.get("receipt_sha256", ""))
    require(set(freeze.get("rows", {})) == set(scope["rows"]), "freeze row coverage mismatch")
    for row, meta in freeze["rows"].items():
        require(meta.get("dev") == 84 and meta.get("test") == 84 and meta.get("family_count") == 12 and meta.get("fillers_per_family") == 7,
                "freeze row design mismatch")
        require(isinstance(meta.get("values"), list) and len(meta["values"]) == 2 and meta["values"][0] != meta["values"][1], "freeze binary bins missing")
        if scope["id"] == "expanded25":
            require(meta.get("class") == scope["taxonomy"][row], "freeze taxonomy mismatch")


def make_plan(bank_binding: dict, freeze_binding: dict, candidate_binding: dict,
              *, assets_binding: dict, candidate_bound_at: str, frozen_at: str, source_bindings: list[dict],
              scope=None, rule_binding=None, parity_binding=None) -> dict:
    """Bind externally supplied post-freeze candidates; never look for old artifacts.

    Bindings use {path, sha256}; timestamps are UTC ISO-8601. Bank is a label-free
    JSONL with id, feature, split, cluster, text, ids. Labels remain off the pod.
    The caller supplies an automatic-check PASS receipt in freeze_binding.
    """
    scope = validate_scope(scope)
    registered_rules = validate_rule_binding(scope, rule_binding)
    require(instant(candidate_bound_at) >= instant(frozen_at), "candidate binding predates bank freeze")
    if scope["id"] == "expanded25":
        require(instant(frozen_at) <= instant(EXPANDED_FREEZE_DEADLINE), "expanded freeze missed fallback deadline")
    for b in (bank_binding, freeze_binding, candidate_binding, assets_binding, *source_bindings):
        require(isinstance(b.get("path"), str) and bool(b["path"]), "missing artifact path")
        check_hash(b["sha256"])
    require(all(any(Path(b["path"]).as_posix().endswith(p) for b in source_bindings) for p in REQUIRED_SOURCE_PATHS), "operational source hash coverage incomplete")
    plan = {
        "schema": SCHEMA, "experiment": "E36", "registered_section": 132,
        "scope": scope, "rule_binding": rule_binding,
        "rule_status": "BOUND" if registered_rules else "UNRESOLVED_EXPANDED_REGISTRATION",
        "operations_amendment_section": 143 if scope["id"] == "expanded25" else 135,
        "pod_budget": POD_BUDGET if scope["id"] == "expanded25" else None,
        "bank": bank_binding, "freeze": freeze_binding, "candidates": candidate_binding,
        "assets": assets_binding, "registered_revisions": REGISTERED_REVISIONS,
        "frozen_at": frozen_at, "candidate_bound_at": candidate_bound_at,
        "source_bindings": source_bindings,
        "parity_inputs": parity_binding,
        "parity_threshold": .02,
        "rows": scope["rows"], "item_count": len(scope["rows"]) * 168,
        "items_per_row": 168, "items_per_split_per_row": 84,
        "families_per_row": 12, "families_per_split_per_row": 6, "fillers_per_family": 7,
        "within_template_token_length_relative_tolerance": .10,
        "capture_blocks": [42, 44], "read_position": "raw_prefix_final_token",
        "channels": CHANNELS, "probe": PROBE_RECIPE,
        "e15_source_hashes": E15_SOURCE_HASHES,
        "candidate_aggregation": "arithmetic_mean_of_raw_logodds_before_AUROC",
        "continuation_pair_policy": CONTINUATION_POLICY,
        "h3": "sealed_external_E30_R2_same_row_mask_or_NOT_EVALUABLE; always_acquire_value_word",
        "cap_gpu_seconds": scope["cap_gpu_seconds"], "retrieval_reserve_seconds": RETRIEVAL_SECONDS,
        "operator": "integrator", "gpu_count": 1, "gpu_type": "H200",
        "v2_labels_on_gpu": False, "parity_labels_on_gpu": 252, "retries": False, "scope_cuts": False,
    }
    plan = json.loads(json.dumps(plan))  # Do not share mutable recipe constants.
    plan["plan_sha256"] = canonical_hash(plan)
    return plan


def validate_plan(plan: dict) -> None:
    payload = {k: v for k, v in plan.items() if k != "plan_sha256"}
    require(canonical_hash(payload) == plan.get("plan_sha256"), "plan digest mismatch")
    require(plan.get("schema") == SCHEMA and plan.get("experiment") == "E36", "wrong experiment")
    from parity_gate import validate_binding
    validate_binding(plan.get('parity_inputs'))
    require(plan.get('parity_threshold') == .02, 'changed W1 parity threshold')
    scope = validate_scope(plan.get("scope"))
    rules = validate_rule_binding(scope, plan.get("rule_binding"))
    require(plan.get("rule_status") == ("BOUND" if rules else "UNRESOLVED_EXPANDED_REGISTRATION"), "rule status mismatch")
    require(plan.get("channels") == CHANNELS and plan.get("probe") == PROBE_RECIPE, "changed channel recipe")
    require(plan.get("rows") == scope["rows"] and plan.get("item_count") == 168 * len(scope["rows"]) and plan.get("capture_blocks") == [42, 44], "changed scope")
    require(plan.get("cap_gpu_seconds") == scope["cap_gpu_seconds"] and plan.get("gpu_count") == 1, "changed GPU budget")
    require(plan.get('pod_budget') == (POD_BUDGET if scope['id'] == 'expanded25' else None), 'changed pod budget or unsupported row sharding')
    if scope["id"] == "expanded25":
        require(instant(plan["frozen_at"]) <= instant(EXPANDED_FREEZE_DEADLINE), "expanded freeze missed fallback deadline")
    require(plan.get("retrieval_reserve_seconds") == RETRIEVAL_SECONDS, "changed retrieval reserve")
    require(plan.get("v2_labels_on_gpu") is False and plan.get("parity_labels_on_gpu") == 252 and plan.get("retries") is False and plan.get("scope_cuts") is False, "invalid execution policy")
    require(plan.get("e15_source_hashes") == E15_SOURCE_HASHES, "changed E15 recipe")
    require(plan.get("continuation_pair_policy") == CONTINUATION_POLICY, "changed frozen E15 pair policy")
    require(plan.get("within_template_token_length_relative_tolerance") == .10, "changed token-length matching tolerance")
    require(plan.get("registered_revisions") == REGISTERED_REVISIONS, "changed registered model revisions")
    check_hash(plan["assets"]["sha256"])
    require(isinstance(plan["assets"].get("path"), str) and bool(plan["assets"]["path"]), "missing bound asset manifest")
    require(all(any(Path(b["path"]).as_posix().endswith(p) for b in plan["source_bindings"]) for p in REQUIRED_SOURCE_PATHS), "operational source hash coverage incomplete")


def science_cap_seconds(forecast):
    require(type(forecast) in (int, float) and math.isfinite(forecast) and forecast >= 0, 'invalid science forecast')
    return min(1.5 * forecast + 360, 59447)


def make_launch_request(plan, *, plan_path, assignment_path, assets_path, repository_root, output_path,
                        prior_gpu_seconds, phase_estimates_seconds):
    """Prepare the reviewable request; only the integrator may assign/run it."""
    validate_plan(plan)
    cap = plan["cap_gpu_seconds"]
    require(Path(assets_path).resolve() == Path(plan["assets"]["path"]).resolve(), "launch assets differ from bound manifest")
    require(math.isfinite(prior_gpu_seconds) and 0 <= prior_gpu_seconds < cap, "invalid prior GPU charge")
    require(set(phase_estimates_seconds) == set(PHASES), "all phase forecasts required")
    require(all(isinstance(v, (float, int)) and math.isfinite(v) and v >= 0 for v in phase_estimates_seconds.values()), "invalid forecast")
    forecast = sum(phase_estimates_seconds.values())
    allocation_cap = cap - prior_gpu_seconds
    setup_allowance = 0
    science_cap = allocation_cap
    if plan['scope']['id'] == 'expanded25':
        require(prior_gpu_seconds >= MIN_PRIOR_GPU_SECONDS, 'prior custody must include attempt 1: 552.8 seconds')
        setup_allowance = SETUP_ALLOWANCE_SECONDS
        science_cap = science_cap_seconds(forecast)
        allocation_cap = min(allocation_cap, setup_allowance + science_cap)
    require(1.5 * forecast + RETRIEVAL_SECONDS <= min(science_cap, allocation_cap), "launch forecast cannot fit")
    request = {"experiment": "E36", "status": "AWAITING_INTEGRATOR_ASSIGNMENT" if plan["rule_status"] == "BOUND" else "HELD_UNRESOLVED_RULE_BINDING", "operator": "integrator",
               "scope_id": plan["scope"]["id"],
               "plan_sha256": plan["plan_sha256"], "gpu_count": 1, "gpu_type": "H200",
               "aggregate_cap_gpu_seconds": cap, "prior_gpu_seconds": prior_gpu_seconds,
               "maximum_current_allocation_seconds": allocation_cap,
               "setup_allowance_seconds": setup_allowance, "science_cap_seconds": science_cap,
               "warmed_forecast_seconds": forecast,
               "pod_budget": plan['pod_budget'],
               "retrieval_reserve_seconds": RETRIEVAL_SECONDS, "phase_estimates_seconds": phase_estimates_seconds,
               "external_stop_required": True, "setup_charged_from_allocation_start": True,
               "gpu_fallback_policy": "integrator-verified H200 unavailable >=900s and memory PASS; B200 or H100_80GB only",
               "scope_deadline": EXPANDED_FREEZE_DEADLINE,
               "retries": False, "scope_cuts": False,
               "command": ["python3", str(Path(repository_root) / "results/g_agreement/understand/e36/worker.py"),
                           "--plan", str(plan_path), "--assignment", str(assignment_path), "--assets", str(assets_path),
                           "--root", str(repository_root), "--out", str(output_path)]}
    request["request_sha256"] = canonical_hash(request)
    return request


def make_e30_replication_handoff(*, bank_binding, freeze_binding, e30_candidates_binding,
                                frozen_at, candidates_bound_at, scope=None, acts44_binding=None):
    """Hand off the frozen second bank to a separately budgeted E30 owner.

    Candidate contents are never read here. This is not an E36 run extension and
    never increases E36's allocation or authorizes an E30 model call.
    """
    scope = validate_scope(scope)
    require(instant(candidates_bound_at) >= instant(frozen_at), "E30 candidates must be bound after bank freeze")
    if scope["id"] == "expanded25":
        require(instant(frozen_at) <= instant(EXPANDED_FREEZE_DEADLINE), "expanded freeze missed fallback deadline")
    freeze = read_bound(freeze_binding)
    validate_freeze_receipt(freeze, bank_binding, scope)
    for binding in (bank_binding, e30_candidates_binding, *([acts44_binding] if acts44_binding is not None else [])):
        check_hash(binding["sha256"])
        require(isinstance(binding.get("path"), str) and bool(binding["path"]), "missing handoff artifact path")
    require(Path(e30_candidates_binding["path"]).name == "CANDIDATES.json", "handoff requires frozen E30 CANDIDATES.json")
    handoff = {"experiment": "E30_SECOND_BANK_REPLICATION", "source_experiment": "E36", "scope_id": scope["id"],
               "status": "AWAITING_SEPARATE_E30_INTEGRATOR_ASSIGNMENT", "bank": bank_binding, "freeze": freeze_binding,
               "e30_candidates": e30_candidates_binding, "frozen_at": frozen_at, "candidates_bound_at": candidates_bound_at,
               "acts44": acts44_binding, "capture_block": 44, "item_count": len(scope["rows"]) * 168,
               "aggregate_cap_gpu_seconds": E30_REPLICATION_CAP_GPU_SECONDS, "includes_setup": True,
               "budget_account": "E30_SECOND_BANK_SEPARATE_FROM_E36", "e36_cap_unchanged": scope["cap_gpu_seconds"],
               "registered_tests": ["E30_R1", "E30_R2"], "operator": "integrator"}
    handoff["handoff_sha256"] = canonical_hash(handoff)
    return handoff


def validate_items(items: list[dict], scope=None) -> None:
    scope = validate_scope(scope)
    rows, count = scope["rows"], len(scope["rows"]) * 168
    require(len(items) == count and len({x["id"] for x in items}) == count, f"E36 scope needs exactly {count} unique items")
    allowed = {"id", "feature", "split", "cluster", "text", "ids", "read_index", "donor_id"}
    require(all(set(x) <= allowed for x in items), "GPU bank contains labels or undeclared fields")
    require(all(x["feature"] in rows and x["split"] in {"dev", "test"} for x in items), "unknown row/split")
    for row in rows:
        family_sets = []
        for split in ("dev", "test"):
            subset = [x for x in items if x["feature"] == row and x["split"] == split]
            families = {x["cluster"] for x in subset}
            require(len(subset) == 84 and len(families) == 6, "incorrect row/split counts")
            require(all(sum(x["cluster"] == f for x in subset) == 14 for f in families), "incorrect family size")
            family_sets.append(families)
        require(family_sets[0].isdisjoint(family_sets[1]), "template family crosses dev/test")
    for x in items:
        require(isinstance(x["text"], str) and isinstance(x["ids"], list) and bool(x["ids"]), "missing text/tokenized input")
        require(all(type(v) is int and v >= 0 for v in x["ids"]), "invalid token ids")
        require(x.get("read_index", len(x["ids"]) - 1) == len(x["ids"]) - 1, "input extends past read token")


def validate_candidates(payload: dict, scope=None) -> None:
    scope = validate_scope(scope)
    require(set(payload) == {"rows"} and set(payload["rows"]) == set(scope["rows"]), "candidate row mismatch")
    for row, spec in payload["rows"].items():
        require(set(spec) == {"values", "olens_descriptive", "olens_value_word", "nla", "continuation"}, "candidate schema mismatch")
        require(len(spec["values"]) == 2 and spec["values"][0] != spec["values"][1], "binary value orientation missing")
        require(isinstance(spec["olens_value_word"], dict) and bool(spec["olens_value_word"]), "value-word variants must remain separate")
        require(all(isinstance(v, str) and v and ":" not in v for v in spec["olens_value_word"]), "invalid value-word variant id")
        variants = [("olens_descriptive", spec["olens_descriptive"]), ("nla", spec["nla"]),
                    ("continuation", spec["continuation"]), *[("olens_value_word", p) for p in spec["olens_value_word"].values()]]
        for key, pairs in variants:
            require(isinstance(pairs, list) and (bool(pairs) or key == "continuation"), "missing frozen candidate pair")
            require(all(isinstance(p, list) and len(p) == 2 and all(isinstance(s, str) and s for s in p) for p in pairs), "invalid frozen pair")


def auroc(scores, labels) -> float:
    require(len(scores) == len(labels) and set(labels) == {0, 1}, "invalid AUROC labels")
    require(all(math.isfinite(float(x)) for x in scores), "nonfinite score")
    pos = [float(x) for x, y in zip(scores, labels) if y == 1]
    neg = [float(x) for x, y in zip(scores, labels) if y == 0]
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def average_pair_scores(records, valid=None):
    require(bool(records), "empty score matrix")
    widths = {len(x) for x in records}
    require(len(widths) == 1 and next(iter(widths)) > 0, "ragged score matrix")
    selected = list(range(next(iter(widths)))) if valid is None else list(valid)
    require(bool(selected) and all(0 <= j < next(iter(widths)) for j in selected), "no valid continuation pairs")
    return [sum(float(x[j]) for j in selected) / len(selected) for x in records]


def continuation_valid_pairs(dev_records, dev_labels) -> list[int]:
    """Legacy E15 source-audit helper; deliberately unused in the E36 pipeline."""
    average_pair_scores(dev_records)  # validate complete, rectangular matrix
    return [j for j in range(len(dev_records[0])) if auroc([x[j] for x in dev_records], dev_labels) >= .80]


def adjudicate(metrics: dict, h3_eligibility: dict | None = None, *, scope=None, rule_binding=None) -> dict:
    """All denominators are registered; missing required rows yield NOT_EVALUABLE.

    metrics[row][channel] is an AUROC or None. The optional H3 receipt contains
    only eligibility, matching variant IDs and a receipt hash, never E30 scores.
    """
    scope = validate_scope(scope)
    rules = validate_rule_binding(scope, rule_binding)
    if rules is None:
        return {h: {"status": "NOT_EVALUABLE", "reason": "expanded_required_counts_and_H4_population_unregistered",
                    "scope_id": scope["id"], "denominator": None} for h in ("H1", "H2", "H3", "H4", "H5")}
    required = rules["required_counts"]
    def value(row, channel):
        v = metrics.get(row, {}).get(channel)
        if v is None:
            return None
        require(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1, "invalid row AUROC")
        return float(v)
    def rule(rows, channels, predicate, needed):
        evaluations = {}
        for row in rows:
            vals = [value(row, c) for c in channels]
            evaluations[row] = None if any(v is None for v in vals) else bool(predicate(*vals))
        missing = [r for r, v in evaluations.items() if v is None]
        count = sum(v is True for v in evaluations.values())
        return {"status": "NOT_EVALUABLE" if missing else ("REPLICATED" if count >= needed else "NOT_REPLICATED"),
                "denominator": len(rows), "required": needed, "satisfying_rows": [r for r, v in evaluations.items() if v is True],
                "missing_rows": missing, "row_tests": evaluations}
    out = {
        "H1": rule(scope["structure_rows"], ("oracle_descriptive", "probe"), lambda d, p: d <= .65 and p >= .90, required["H1"]),
        "H2": rule(scope["content_rows"], ("oracle_descriptive",), lambda d: d >= .85, required["H2"]),
        "H4": rule(rules["h4_rows"], ("continuation",), lambda c: c >= .70, required["H4"]),
        "H5": rule(scope["structure_rows"], ("nla", "oracle_descriptive"), lambda n, d: n - d >= .10 - 1e-12, required["H5"]),
    }
    if h3_eligibility is None:
        out["H3"] = {"status": "NOT_EVALUABLE", "reason": "sealed_E30_R2_eligibility_unavailable", "denominator": None}
    else:
        require(set(h3_eligibility) == {"E30_R2_met", "eligible_rows", "matching_variant_ids", "receipt_sha256"}, "H3 accepts eligibility only, no historical scores")
        check_hash(h3_eligibility["receipt_sha256"])
        rows = h3_eligibility["eligible_rows"]
        require(isinstance(rows, list) and len(rows) == len(set(rows)) and set(rows) <= set(scope["rows"]), "invalid E30 eligibility rows")
        require(type(h3_eligibility["E30_R2_met"]) is bool, "invalid E30 R2 eligibility")
        if not h3_eligibility["E30_R2_met"]:
            out["H3"] = {"status": "NOT_EVALUABLE", "reason": "E30_R2_not_met", "denominator": len(rows)}
        else:
            require(bool(rows), "R2 met requires same-row eligibility mask")
            matches = h3_eligibility["matching_variant_ids"]
            require(set(matches) == set(rows), "H3 matching-variant rows differ")
            row_tests, comparisons = {}, {}
            for row in rows:
                ids = matches[row]
                require(isinstance(ids, list) and ids and len(ids) == len(set(ids)), "H3 variant IDs required")
                if len(ids) != 1:
                    comparisons[row] = {"status": "NOT_EVALUABLE", "reason": "unresolved_matching_variant"}
                    row_tests[row] = None
                    continue
                tests = {}
                for variant in ids:
                    require(isinstance(variant, str) and bool(variant), "invalid H3 variant ID")
                    v, d = value(row, "oracle_value_word:" + variant), value(row, "oracle_descriptive")
                    tests[variant] = None if v is None or d is None else v - d >= .15 - 1e-12
                comparisons[row] = tests
                row_tests[row] = None if any(v is None for v in tests.values()) else all(tests.values())
            missing = [r for r, v in row_tests.items() if v is None]
            out["H3"] = {"status": "NOT_EVALUABLE" if missing else ("REPLICATED" if all(row_tests.values()) else "NOT_REPLICATED"),
                         "denominator": len(rows), "required": len(rows), "row_tests": row_tests,
                         "variant_tests": comparisons, "missing_rows": missing,
                         "satisfying_rows": [r for r, v in row_tests.items() if v is True]}
            if any(len(matches[r]) != 1 for r in rows):
                out["H3"]["reason"] = "coordinator_must_identify_one_frozen_matching_variant_per_row"
        out["H3"]["eligibility_receipt_sha256"] = h3_eligibility["receipt_sha256"]
    return {key: out[key] for key in ("H1", "H2", "H3", "H4", "H5")}


def forecast_gate(*, prior_gpu_seconds: float, allocation_started_at: float, now: float,
                  remaining_work_seconds: float, hard_deadline: float, gpu_count: int = 1,
                  cap_gpu_seconds: int = CAP_GPU_SECONDS) -> dict:
    numbers = (prior_gpu_seconds, allocation_started_at, now, remaining_work_seconds, hard_deadline)
    require(all(isinstance(x, (int, float)) and math.isfinite(x) and x >= 0 for x in numbers), "invalid GPU accounting")
    require(gpu_count == 1 and now >= allocation_started_at, "E36 requires a single sequential GPU allocation")
    require(cap_gpu_seconds in {CAP_GPU_SECONDS, EXPANDED_CAP_GPU_SECONDS}, "unregistered E36 cap")
    elapsed = now - allocation_started_at
    remaining = min(cap_gpu_seconds - prior_gpu_seconds - elapsed, hard_deadline - now)
    projected = 1.5 * remaining_work_seconds + RETRIEVAL_SECONDS
    return {"cap_gpu_seconds": cap_gpu_seconds, "prior_gpu_seconds": prior_gpu_seconds, "current_allocation_elapsed_seconds": elapsed,
            "remaining_allocation_seconds": remaining, "padded_remaining_forecast_seconds": projected,
            "fits": projected <= remaining and remaining > RETRIEVAL_SECONDS}


def validate_gpu_assignment(assignment, now):
    require(assignment.get("gpu_count") == 1, "one sequential GPU required")
    if assignment.get("gpu_type") == "H200":
        return
    require(assignment.get("gpu_type") in {"B200", "H100_80GB"}, "unsupported GPU type")
    fallback = assignment.get("gpu_fallback", {})
    wait, memory = fallback.get("h200_unavailable", {}), fallback.get("memory_check", {})
    for receipt in (wait, memory):
        require(receipt.get("verified_by") == "integrator" and receipt.get("verified") is True, "verified GPU fallback receipts required")
        check_hash(receipt.get("receipt_sha256", ""))
    started, ended = wait.get("started_at"), wait.get("ended_at")
    require(all(isinstance(t, (float, int)) and math.isfinite(t) for t in (started, ended)) and
            ended - started >= 900 and ended <= min(now, assignment["allocation_started_at"]), "H200 must be unavailable for at least 15 minutes before fallback")
    require(memory.get("status") == "PASS" and memory.get("gpu_type") == assignment["gpu_type"], "GPU memory check must pass for assigned type")
    required, available = memory.get("required_bytes"), memory.get("available_bytes")
    require(type(required) is int and type(available) is int and 0 < required <= available, "concrete passing GPU memory estimate required")


def validate_assignment(assignment: dict, plan: dict, now: float) -> None:
    validate_plan(plan)
    require(assignment.get("operator") == "integrator" and assignment.get("experiment") == "E36", "integrator-only E36 assignment required")
    require(assignment.get("plan_sha256") == plan["plan_sha256"], "assignment not bound to plan")
    require(plan["rule_status"] == "BOUND", "expanded rule binding remains unresolved")
    if plan["scope"]["id"] == "original8":
        from datetime import datetime, timezone
        decision = scope_decision(now=datetime.fromtimestamp(now, timezone.utc).isoformat(),
                                  expanded_frozen_at=assignment.get("expanded_frozen_at"))
        require(decision["scope_id"] == "original8", "original-eight fallback is not yet eligible")
    validate_gpu_assignment(assignment, now)
    require(assignment.get("external_stop", {}).get("confirmed") is True, "independent external stop must be installed")
    require(assignment["external_stop"].get("deadline") == assignment["hard_deadline"], "external stop/deadline mismatch")
    require(bool(assignment["external_stop"].get("receipt")) and bool(assignment.get("pod_id")), "external stop/pod receipt required")
    require(assignment["hard_deadline"] <= assignment["allocation_started_at"] + plan["cap_gpu_seconds"] - assignment["prior_gpu_seconds"], "aggregate cap exceeded")
    require(set(assignment["phase_estimates_seconds"]) == set(PHASES), "all phase forecasts required")
    if plan['scope']['id'] == 'expanded25':
        require(assignment['prior_gpu_seconds'] >= MIN_PRIOR_GPU_SECONDS, 'prior custody must include attempt 1: 552.8 seconds')
        forecast = assignment.get('warmed_forecast_seconds')
        require(type(forecast) in (int, float) and math.isfinite(forecast) and forecast >= 0 and
                forecast == sum(assignment['phase_estimates_seconds'].values()), 'bound full-pod warmed forecast required')
        require(assignment.get('warmed_forecast_verified') is True and bool(assignment.get('warmed_forecast_receipt')),
                'integrator-verified warmed forecast receipt required')
        require(now <= assignment['allocation_started_at'] + SETUP_ALLOWANCE_SECONDS, 'post-creation setup deadline exceeded')
        require(assignment['hard_deadline'] <= assignment['allocation_started_at'] + SETUP_ALLOWANCE_SECONDS + science_cap_seconds(forecast),
                'section 143 per-pod cap exceeded')
    gate = forecast_gate(prior_gpu_seconds=assignment["prior_gpu_seconds"], allocation_started_at=assignment["allocation_started_at"],
                         now=now, remaining_work_seconds=sum(assignment["phase_estimates_seconds"].values()), hard_deadline=assignment["hard_deadline"],
                         cap_gpu_seconds=plan["cap_gpu_seconds"])
    require(gate["fits"], "forecast cannot fit aggregate GPU budget including retrieval")


def analyse_acquisition(items, labels, candidates, score_records, acts44, *, repo_root,
                        h3_eligibility=None, probe_callback=None, scope=None, rule_binding=None):
    """CPU-only analysis of this frozen E36 bank, including the exact W1 probe.

    No path discovery, old-bank loader or historical score reader is used. The
    optional callback exists for CPU mocks; production uses the source-hashed
    W1 function on E36 test families. Auxiliary donor predictions are discarded;
    identity donors satisfy the helper's grouping precondition and cannot affect
    its training or true held-out predictions.
    """
    scope = validate_scope(scope)
    validate_items(items, scope)
    validate_candidates(candidates, scope)
    require(len(labels) == len(items) and len({x["id"] for x in labels}) == len(items), "private label coverage mismatch")
    lookup = {x["id"]: x for x in labels}
    require(set(lookup) == {x["id"] for x in items}, "private label IDs mismatch")
    for x in items:
        lab = lookup[x["id"]]
        require(all(lab[k] == x[k] for k in ("feature", "split", "cluster")), "private label metadata mismatch")
        require(lab["value"] in candidates["rows"][x["feature"]]["values"], "label outside frozen binary bins")
    require(len(acts44) == len(items), "capture/order length mismatch")
    scoremap = {}
    known_ids = {x["id"] for x in items}
    for rec in score_records:
        require(rec["id"] in known_ids, "foreign score item")
        feature = lookup[rec["id"]]["feature"]
        split = lookup[rec["id"]]["split"]
        frozen = candidates["rows"][feature]
        allowed = {"oracle_descriptive", "nla", *["oracle_value_word:" + v for v in frozen["olens_value_word"]]}
        if frozen["continuation"]:
            allowed.add("continuation")
        if split == "dev":
            allowed = set()
        require(rec["channel"] in allowed, "score outside registered channel grid")
        key = rec["id"], rec["channel"]
        require(key not in scoremap, "duplicate score item/channel")
        scoremap[key] = rec
    if probe_callback is None:
        import numpy as np
        from types import SimpleNamespace
        from worker import frozen_function
        function = frozen_function(repo_root, PROBE_RECIPE["source"], PROBE_RECIPE["function"],
                                   PROBE_RECIPE["function_sha256"], {"np": np, "P": SimpleNamespace(SEED=SEED)})
        def probe_callback(indices, y, groups):
            true, _, folds = function(np.asarray(acts44)[indices], np.asarray(y, dtype=int),
                                      np.asarray(groups), np.arange(len(indices), dtype=int), k=5)
            return list(map(float, true)), folds
    metrics, detail = {}, {}
    for feature in scope["rows"]:
        spec = candidates["rows"][feature]
        subsets = {split: [i for i, x in enumerate(items) if x["feature"] == feature and x["split"] == split] for split in ("dev", "test")}
        ys = {split: [int(lookup[items[i]["id"]]["value"] == spec["values"][0]) for i in idx] for split, idx in subsets.items()}
        require(all(sum(y) == 42 for y in ys.values()), "binary split balance mismatch")
        row_metrics = {}
        row_detail = {"n_test": 84, "n_dev": 84, "test_families": 6, "missing_score_cells": {}}
        indices = subsets["test"]
        prediction, folds = probe_callback(indices, ys["test"], [items[i]["cluster"] for i in indices])
        row_metrics["probe"] = auroc(prediction, ys["test"])
        row_detail["probe_folds"] = folds
        def matrix(channel, split, width):
            records = [scoremap.get((items[i]["id"], channel)) for i in subsets[split]]
            missing = sum(r is None or r.get("status") != "COMPLETE" for r in records)
            row_detail["missing_score_cells"][channel] = missing
            if missing:
                return None
            for rec, idx in zip(records, subsets[split]):
                require(rec["feature"] == feature and rec["split"] == split, "score metadata mismatch")
                expected_block = 42 if channel == "nla" else 44
                require(rec["block"] == expected_block and len(rec["scores"]) == width, "score recipe/width mismatch")
            return [r["scores"] for r in records]
        for channel, key in (("oracle_descriptive", "olens_descriptive"), ("nla", "nla")):
            scores = matrix(channel, "test", len(spec[key]))
            row_metrics[channel] = None if scores is None else auroc(average_pair_scores(scores), ys["test"])
        for variant, pairs in spec["olens_value_word"].items():
            channel = "oracle_value_word:" + variant
            scores = matrix(channel, "test", len(pairs))
            row_metrics[channel] = None if scores is None else auroc(average_pair_scores(scores), ys["test"])
        pairs = spec["continuation"]
        row_metrics["continuation"] = None
        row_detail["continuation_frozen_pair_indices"] = list(range(len(pairs)))
        row_detail["continuation_status"] = "NOT_EVALUABLE_NO_FROZEN_PAIRS"
        if pairs:
            test = matrix("continuation", "test", len(pairs))
            row_detail["continuation_status"] = "NOT_EVALUABLE_MISSING_SCORES"
            if test is not None:
                row_detail["continuation_status"] = "EVALUABLE_ALL_FROZEN_PAIRS"
                row_metrics["continuation"] = auroc(average_pair_scores(test), ys["test"])
        metrics[feature], detail[feature] = row_metrics, row_detail
    return {"experiment": "E36", "scope_id": scope["id"], "metrics": metrics, "row_detail": detail,
            "hypotheses": adjudicate(metrics, h3_eligibility, scope=scope, rule_binding=rule_binding), "probe_recipe": PROBE_RECIPE,
            "orientation": "positive_is_values[0]; never flip by test AUROC"}
