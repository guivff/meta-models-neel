"""CPU-only E73 judging admission; no credentials, network, dispatch or analysis.

Preserves the sealed E56 whole-initial-pass bound.  A PASS is a packet/budget
preflight only, never authority to call a judge.  E74 deliberately remains
unsupported until its absent-J record and packet contract are implemented.
The small pure functions below are loaded from hash-checked Git objects, not
mutable worktree files; API/client modules are never imported or executed.
"""
from __future__ import annotations

import argparse
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from types import SimpleNamespace

CAP = Decimal("5")
ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "cache/g_agreement/i2/judging/e73_5usd/ledger.jsonl"
RUBRIC_SHA = "03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613"
ROUTE = SimpleNamespace(MODEL="google/gemini-3.1-flash-lite", PROVIDER="google-vertex/global", PROVIDER_NAME="Google")
INTERNALS = "1dfe44a01689dae57fca1ad33e81afba92ed3284"
TRANSPORT = "0442e10a5ac106ee23d8a36d3bc71c9c58151413"
PINS = {
    "payload": (INTERNALS, "projects/g_agreement/understand/blind_judge/run.py", "9eba603c1eb911029b82f9acca94299cef9f73899a08229b9247a9de5ce1c025"),
    "runner": (INTERNALS, "projects/g_agreement/understand/blind_judge/later_runner.py", "8dda0b8625f748977768cfed7de8eb704ea4cb07e38bb51149b79b3b60380f71"),
    "runner_handoff": (INTERNALS, "results/g_agreement/understand/blind_judge/later_banks/RUNNER_HANDOFF.md", "f0fbf1b19acbbee06d2c4d746ac84a412efa296284318d6b06d4eae0d474a354"),
    "scoring": (INTERNALS, "projects/g_agreement/readerbench/scoring.py", "201a7542ebda45db5bfb7031ebc84f7ffa6a8e10129db55710b1d8c144b9a790"),
    "render": ("c3b4f1abce9d315ee7b07b5640e7589c1ffe934c", "projects/g_agreement/understand/blind_judge/judgment_adapter402.py", "c950c1f342fb0f40f5128ea97c5ae7d0ce980134c1d25f8281a1c81fcad6344a"),
    "api": (TRANSPORT, "projects/g_agreement/understand/e10/api.py", "f441614f70639cc5a5625000f13e05cc970531caf65171b7396a874a3536acaf"),
    "privacy": (TRANSPORT, "projects/g_agreement/understand/e10/privacy.py", "09e0ac3cd052c97846848c2e29439c4c78f0395017cea30ffa28ba58c422847b"),
    "protocol": (TRANSPORT, "projects/g_agreement/understand/e10/protocol.py", "1395a83ba84653d76fd86e7ed80b1ef81ae728a3da5f6456a88368e28279e220"),
    "io": (TRANSPORT, "projects/g_agreement/understand/e10/io.py", "ea97fa8380a1c428d742bcb52548f7cffd6e3f66ad49cb5dbf20175ea2de8921"),
    "rubric": ("769ea9e16a9dd1f9ab6bd1e14b1b6ea81e0f4531", "results/g_agreement/understand/e56/job/JUDGE_RUBRIC.md", RUBRIC_SHA),
}
SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
NATIVE_FILES = {"oracle.jsonl", "nla.jsonl", "READER_REPORT.json", "ADMISSION.json", "GO.json", "MODEL_READY_oracle.json", "MODEL_READY_nla.json"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def ordinary(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "ordinary file required")
    return path.read_bytes()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    def reject(_):
        raise ValueError("nonfinite JSON value")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


def git_bytes(repo, commit, path):
    require(isinstance(commit, str) and COMMIT.fullmatch(commit), "full commit required")
    relative = PurePosixPath(path)
    require(not relative.is_absolute() and ".." not in relative.parts and str(relative) == path, "relative Git path required")
    return subprocess.check_output(["git", "-C", str(repo), "show", commit + ":" + path], stderr=subprocess.PIPE)


def committed(ref):
    raw = git_bytes(ref["repo"], ref["commit"], ref["path"])
    require(digest(raw) == ref["sha256"], "committed artifact hash differs")
    epoch = int(subprocess.check_output(["git", "-C", str(ref["repo"]), "show", "-s", "--format=%ct", ref["commit"]]))
    return raw, epoch


def referenced(ref):
    raw = ordinary(ref["path"])
    require(digest(raw) == ref["sha256"], "local receipt hash differs")
    return decode(raw)


def authority_gate(ref, repo):
    """Verify the integrator's recorded Guiv quote against its cited Git blob."""
    value = referenced(ref)
    require(value.get("schema") == "i2-guiv-judging-authority-v1", "judging authority proof schema")
    raw = git_bytes(repo, value["source_commit"], value["source_path"])
    require(digest(raw) == value["source_blob_sha256"], "judging authority source hash")
    require(raw.decode().splitlines()[value["source_line"] - 1] == value["verbatim_record"], "judging authority quotation differs")
    require("E73 ≤ USD 5" in value["verbatim_record"] and "E74 ≤ USD 5" in value["verbatim_record"] and
            ROUTE.MODEL in value["verbatim_record"] and ROUTE.PROVIDER in value["verbatim_record"],
            "exact bank cap/route authority required")
    require(value.get("per_bank_usd", {}).get("E73") == 5 and value.get("per_bank_usd", {}).get("E74") == 5,
            "authority per-bank caps differ")
    require(value.get("route") == {"broker": "OpenRouter", "model": ROUTE.MODEL, "provider": ROUTE.PROVIDER,
            "zdr": True, "data_collection": "deny", "provider_pinned": True, "fallbacks": False}, "authority route differs")
    return value


def frozen_functions(repo):
    """Execute only allowlisted pure definitions; never import the API client."""
    sources = {}
    for key, (commit, path, expected) in PINS.items():
        raw = git_bytes(repo, commit, path)
        require(digest(raw) == expected, "frozen route source differs: " + key)
        sources[key] = raw.decode()
    ns = {"json": json, "re": re, "Decimal": Decimal, "require": require, "P": ROUTE}
    wanted = {
        "scoring": ({"D5", "E56"}, set()),
        "protocol": ({"MODEL", "PROVIDER", "PROVIDER_NAME"}, set()),
        "io": (set(), {"canonical"}),
        "render": ({"SUFFIX"}, {"render_record"}),
        "payload": (set(), {"payload"}),
        "privacy": (set(), {"check_wire"}),
        "api": ({"PROMPT", "COMPLETION"}, {"upper"}),
    }
    # The api constants share one semicolon-separated statement with CAP, but
    # ast produces separate assignments; only PROMPT and COMPLETION are kept.
    for key, (constants, functions) in wanted.items():
        chosen = []
        for node in ast.parse(sources[key]).body:
            if isinstance(node, ast.FunctionDef) and node.name in functions:
                chosen.append(node)
            elif isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) and t.id in constants for t in node.targets):
                chosen.append(node)
        require(len(chosen) == len(constants) + len(functions), "frozen definition inventory differs")
        exec(compile(ast.Module(body=chosen, type_ignores=[]), "frozen:" + PINS[key][1], "exec"), ns)
        if key == "io":
            ns["I"] = SimpleNamespace(canonical=ns["canonical"])
    require((ns["MODEL"], ns["PROVIDER"], ns["PROVIDER_NAME"]) == (ROUTE.MODEL, ROUTE.PROVIDER, ROUTE.PROVIDER_NAME), "route changed")
    return SimpleNamespace(**{k: ns[k] for k in ("payload", "render_record", "upper", "check_wire", "canonical")}, rubric=sources["rubric"])


def ledger_committed(path=LEDGER):
    """Same reserve/settle arithmetic; inspect amounts only, never requests."""
    path = Path(path)
    if not path.exists():
        return Decimal(0)
    book, settled = {}, set()
    for line in ordinary(path).splitlines():
        if not line.strip():
            continue
        item = decode(line)
        value = Decimal(str(item["usd"]))
        require(value.is_finite() and value >= 0, "invalid ledger amount")
        ident = item["id"]
        if item["event"] == "reserve":
            require(ident not in book, "duplicate send reservation")
            book[ident] = value
        elif item["event"] == "settle":
            require(ident in book and ident not in settled, "settlement identity")
            book[ident] = value
            settled.add(ident)
        else:
            raise ValueError("unknown ledger event")
    return sum(book.values(), Decimal(0))


def metadata_gate(spec):
    """This completes before opening or hashing any reader-containing file."""
    require(spec.get("schema") == "i2-e73-judge-preflight-v1" and spec.get("bank") == "E73", "only implemented E73 contract is supported")
    forecast_raw, forecast_epoch = committed(spec["forecast"])
    forecast = decode(forecast_raw)
    require(forecast.get("bank") == "E73" and forecast.get("no_backfill") is True and forecast.get("reader_outcomes_accessed") is False, "prospective E73 forecast required")
    require([x["row"] for x in forecast["rows"]] == ["W1", "W2", "W3", "W4", "W5"], "complete frozen forecast scope")
    bindings_raw, _ = committed(spec["forecast_bindings"])
    bindings = decode(bindings_raw)
    require(spec["forecast_bindings"]["commit"] == spec["forecast"]["commit"] and bindings["forecast_sha256"] == spec["forecast"]["sha256"], "forecast binding commit differs")
    go_raw, go_epoch = committed(spec["go"])
    go = decode(go_raw)
    require(go.get("schema") == "e73-reader-go-v1" and go.get("authorized_by") == "I-2" and go.get("action") == "GO", "actual reader GO required")
    require(go["jforecast_commit"] == spec["forecast"]["commit"] and go["jforecast_sha256"] == spec["forecast"]["sha256"] and forecast_epoch <= go_epoch, "forecast must precede GO")
    require(go["capture_seal_sha256"] == bindings["reader_input_index"]["sha256"] and go["bank_manifest_sha256"] == bindings["original_bank_manifest_sha256"], "GO bank/index binding differs")
    analysis_raw, _ = committed(spec["analysis_freeze"])
    analysis = decode(analysis_raw)
    require(analysis.get("schema") == "e73-preoutcome-cpu-freeze-v1" and analysis.get("source_files") and
            analysis.get("reader_outputs_opened") == 0 and analysis.get("judge_api_calls") == 0 and
            analysis.get("actual_analysis_started") is False, "worker preoutcome CPU freeze required")
    require({"projects/g_agreement/e73/analyze.py", "projects/g_agreement/e73/judge_packet.py"} <= set(analysis["source_files"]), "worker analysis/packet source freeze required")
    for path, expected in analysis["source_files"].items():
        require(isinstance(expected, str) and SHA.fullmatch(expected), "analysis source map must contain hashes")
        require(digest(git_bytes(spec["analysis_freeze"]["repo"], spec["analysis_freeze"]["commit"], path)) == expected, "analysis source is not frozen at cited commit")
    specification_raw, _ = committed(spec["analysis_spec"])
    specification = decode(specification_raw)
    require(spec["analysis_spec"]["commit"] == spec["analysis_freeze"]["commit"] and
            spec["analysis_spec"]["sha256"] == analysis["analysis_spec_sha256"], "worker freeze/specification binding differs")
    require(specification.get("schema") == "e73-preoutcome-analysis-spec-v1" and specification.get("experiment") == "E73" and
            specification.get("status") == "SPECIFICATION_ONLY_NO_REAL_ANALYSIS" and
            specification.get("real_reader_outputs_opened") == 0 and specification.get("real_judgments_opened") == 0,
            "worker preoutcome specification required")
    require(specification["forecast"] == {k: spec["forecast"][k] for k in ("commit", "path", "sha256")}, "worker specification forecast differs")
    budget = referenced(spec["budget_receipt"])
    require(budget.get("issuer") == "I-2" and budget.get("verified") is True and budget.get("bank") == "E73" and budget.get("allocation_id") and budget.get("reservation_included") is True, "separate I-2 E73 budget receipt required")
    require(Decimal(str(budget["reserved_judging_usd"])) == CAP and budget.get("guiv_authorization") and budget.get("route") == {"model": ROUTE.MODEL, "provider": ROUTE.PROVIDER, "zdr": True, "data_collection": "deny", "allow_fallbacks": False}, "E73 authorised hard USD5 and exact route required")
    authority_gate(budget["guiv_authorization"], spec["repo"])
    custody = referenced(spec["custody_receipt"])
    require(custody.get("issuer") == "I-2" and custody.get("verified") is True and custody.get("bank") == "E73" and custody.get("n") == 2000, "verified complete E73 custody required")
    require(custody.get("analysis_frozen_before_reader_outputs_opened") is True and custody["analysis_freeze_sha256"] == spec["analysis_freeze"]["sha256"] and custody["analysis_spec_sha256"] == spec["analysis_spec"]["sha256"], "analysis freeze before output access required")
    for key, expected in {
        "forecast_sha256": spec["forecast"]["sha256"], "go_sha256": spec["go"]["sha256"],
        "bank_manifest_sha256": bindings["original_bank_manifest_sha256"],
        "capture_seal_sha256": bindings["original_capture_seal_sha256"],
        "probe_seal_sha256": bindings["original_probe_seal_sha256"],
        "reader_inputs_index_sha256": bindings["reader_input_index"]["sha256"],
        "packet_seal_sha256": spec["packet_seal_sha256"], "wire_seal_sha256": spec["wire_seal_sha256"],
    }.items():
        require(custody.get(key) == expected, "custody binding differs: " + key)
    require(len(custody.get("native_seals", [])) == 2, "both complete native shards required")
    seen = set()
    for ref in custody["native_seals"]:
        value = referenced(ref)
        require(ref["sha256"] not in seen and value.get("status") == "COMPLETE" and value.get("track") == "C" and set(value.get("files", {})) == NATIVE_FILES, "native shard completeness/inventory")
        seen.add(ref["sha256"])
    return custody


def verify_packet_seal(directory, name, expected, inventory):
    raw = ordinary(directory / name)
    require(digest(raw) == expected, "packet seal hash differs")
    seal = decode(raw)
    require(seal.get("experiment") == "E73" and set(seal.get("files", {})) == inventory, "packet seal inventory differs")
    for member, value in seal["files"].items():
        require(digest(ordinary(directory / member)) == value, "packet member differs")
    return seal


def estimate(items, rubric, frozen, prior=Decimal(0)):
    require(items and len({x["id"] for x in items}) == len(items), "nonempty unique wire grid")
    amounts, wire_bytes = [], 0
    for start in range(0, len(items), 4):
        batch = items[start:start + 4]
        require(all(set(x) == {"id", "rubric", "readout"} and re.fullmatch(r"[a-f0-9]{20,64}", x["id"]) and isinstance(x["rubric"], str) and isinstance(x["readout"], str) for x in batch), "private or malformed wire fields")
        wire = frozen.payload(batch, rubric, "E56", ROUTE)
        frozen.check_wire("extract", [{"id": x["id"], "readout": json.dumps(x)} for x in batch], wire)
        frozen.check_wire("extract", [{"id": "rubric", "readout": rubric}], wire)
        amounts.append(frozen.upper(wire))
        wire_bytes += len(frozen.canonical(wire).encode())
    upper = sum(amounts, Decimal(0))
    require(prior.is_finite() and prior >= 0, "invalid existing commitment")
    return {"status": "PASS_CPU_PREFLIGHT_ONLY" if prior + upper <= CAP else "NO_FIT_WHOLE_INITIAL_PASS",
            "n": len(items), "initial_batches": len(amounts), "initial_wire_bytes": wire_bytes,
            "initial_pass_upper_usd": str(upper), "ledger_committed_usd": str(prior),
            "committed_plus_initial_upper_usd": str(prior + upper), "hard_cap_usd": str(CAP),
            "max_tokens_per_response": 4096, "upper_is_expected_actual_cost": False,
            "retries_in_initial_upper": False, "retry_policy": "Only invalid records, singly, at most twice; each retry separately reserved under same cap",
            "judge_calls": 0, "dispatch_authorized": False, "analysis_runs": 0}


def preflight(spec):
    custody = metadata_gate(spec)
    frozen = frozen_functions(spec["repo"])
    counts, runs = [], set()
    for ref in custody["native_seals"]:
        native = referenced(ref)
        directory = Path(ref["path"]).parent
        for name, bound in native["files"].items():
            raw = ordinary(directory / name)
            require(bound == {"sha256": digest(raw), "bytes": len(raw)}, "native sealed member differs")
        report = decode(ordinary(directory / "READER_REPORT.json"))
        count = report.get("total_per_reader")
        require(count in (700, 300) and report.get("completed") == {"oracle": count, "nla": count} and report.get("status") == "COMPLETE", "complete native count required")
        require(report.get("jforecast_commit") == spec["forecast"]["commit"] and report.get("jforecast_sha256") == spec["forecast"]["sha256"] and report.get("reader_index_sha256") == custody["reader_inputs_index_sha256"], "native forecast/index binding differs")
        require(digest(ordinary(directory / "GO.json")) == spec["go"]["sha256"], "native GO differs")
        require(report.get("run_kind") == "real" and report.get("run_id") and report["run_id"] not in runs, "native run identity differs")
        runs.add(report["run_id"])
        counts.append(count)
    require(sorted(counts) == [300, 700], "native shard scope differs")
    directory = Path(spec["packet_directory"])
    blind = verify_packet_seal(directory, "BLIND_SEAL.json", spec["packet_seal_sha256"], {"JUDGE_PACKET.json", "JUDGE_RUBRIC.md", "PROVENANCE.json"})
    wire = verify_packet_seal(directory, "WIRE_SEAL.json", spec["wire_seal_sha256"], {"WIRE_PACKET.json"})
    require(wire["blind_seal_sha256"] == spec["packet_seal_sha256"] and blind["rubric_sha256"] == RUBRIC_SHA and wire["render_source_sha256"] == PINS["render"][2], "packet/rubric/render chain differs")
    require(blind["private_key_sha256"] == custody["private_join_map_sha256"], "private join-map hash differs")
    require(ordinary(directory / "JUDGE_RUBRIC.md") == frozen.rubric.encode(), "frozen rubric bytes differ")
    packet = decode(ordinary(directory / "JUDGE_PACKET.json"))
    items = [frozen.render_record(x, frozen.rubric) for x in packet]
    require(len(items) == 2000 and items == decode(ordinary(directory / "WIRE_PACKET.json")), "complete exact rendered E73 wire required")
    provenance = decode(ordinary(directory / "PROVENANCE.json"))
    require(provenance.get("n") == 2000 and provenance.get("per_reader_counts") == {"oracle": 1000, "nla": 1000} and provenance.get("per_state_per_reader") == {s: 200 for s in ("W1", "W2", "W3", "W4", "W5")} and provenance.get("probe_score_selection") is False, "frozen full-reader scope required")
    require(provenance.get("go_sha256") == spec["go"]["sha256"] and provenance.get("private_key_sha256") == custody["private_join_map_sha256"] and provenance.get("reader_index_sha256") == custody["reader_inputs_index_sha256"], "packet provenance differs")
    require(provenance.get("bank_manifest_sha256") == custody["bank_manifest_sha256"] and provenance.get("probe_seal_sha256") == custody["probe_seal_sha256"] and provenance.get("render_source_sha256") == PINS["render"][2], "packet bank/probe/render binding differs")
    require({x["sha256"] for x in provenance["native_seals"]} == {x["sha256"] for x in custody["native_seals"]}, "packet/native pull seal binding differs")
    builder = provenance["adapter_source"]
    require(builder["commit"] == spec["packet_builder_commit"] and builder.get("source_files"), "committed packet builder required")
    for path, expected in builder["source_files"].items():
        require(digest(git_bytes(spec["repo"], builder["commit"], path)) == expected, "packet builder source differs")
    result = estimate(items, frozen.rubric, frozen, ledger_committed())
    result.update(bank="E73", packet_seal_sha256=spec["packet_seal_sha256"], ledger_path=str(LEDGER),
                  route_source_pins={k: {"commit": x[0], "path": x[1], "sha256": x[2]} for k, x in PINS.items()})
    return result


def synthetic_floor(repo):
    """A conservative policy floor, not an actual packet or cost forecast."""
    frozen = frozen_functions(repo)
    source = [{"id": f"{i:032x}", "property": "x", "values": {"A": "a", "B": "b"}, "readout": ""} for i in range(4)]
    wire = [frozen.render_record(x, frozen.rubric) for x in source]
    one = estimate(wire, frozen.rubric, frozen)
    per_batch = Decimal(one["initial_pass_upper_usd"])
    # Also prove a floor independent of the worker's 32-character IDs and
    # nonempty property/value definitions: shortest allowed IDs, empty strings.
    minimal = [{"id": f"{i:020x}", "property": "", "values": {"A": "", "B": ""}, "readout": ""} for i in range(4)]
    minimum = estimate([frozen.render_record(x, frozen.rubric) for x in minimal], frozen.rubric, frozen)
    minimum_bound = Decimal(minimum["initial_pass_upper_usd"])
    return {"schema": "i2-e56-route-synthetic-floor-v1", "synthetic_only": True, "reader_outputs_opened": False,
            "judge_calls": 0, "rubric_sha256": RUBRIC_SHA, "rubric_bytes": len(frozen.rubric.encode()),
            "one_batch": one, "floors_usd": {"E73_2000_records_500_batches": str(per_batch * 500), "E74_6804_records_1701_batches": str(per_batch * 1701)},
            "strict_schema_minimum": {"id_characters": 20, "property_and_values": "empty strings", "one_batch": minimum,
                "floors_usd": {"E73_2000_records_500_batches": str(minimum_bound * 500), "E74_6804_records_1701_batches": str(minimum_bound * 1701)}},
            "meaning": "Sum of frozen transport upper bounds with empty readouts and one-letter property/value placeholders; not expected actual charges. Actual nonempty packets require their own byte-exact preflight.",
            "policy": "Whole initial-pass upper bound must fit remaining separate USD5; unchanged. No rolling dispatch implemented.",
            "source_pins": {k: {"commit": x[0], "path": x[1], "sha256": x[2]} for k, x in PINS.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--spec", type=Path)
    group.add_argument("--synthetic-floor", action="store_true")
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = synthetic_floor(args.repo) if args.synthetic_floor else preflight(decode(ordinary(args.spec)))
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "judge_calls", "dispatch_authorized", "floors_usd") if k in result}))


if __name__ == "__main__":
    main()
