"""Historical E73 structural analysis and shared custody/statistics helpers.

Run only after authorization and terminal judgment sealing. --plan is a
repository-relative JSON file at --commit, with its exact --plan-sha256. The
plan pins RULES, source_files, output, and inputs (see load_inputs). Every input
reference is {path: absolute_path, sha256: digest}; native_seals is a list of
references. forecast instead has {repo, commit, path, sha256}, with path relative
to its repository. A future plan must contain actual seals, never placeholders.
Use analyze_controls for the final clarification-4 analysis. The original pure
compute function remains unchanged for regression checks and composition.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import unicodedata

import numpy as np

from .custody import check_go, forecast_proof, read_jsonl, seal, sha256, write_json
from .states import STATE_VALUES
from .delivery import validate_gate

REPO = Path(__file__).resolve().parents[3]
STATES = ("W1", "W2", "W3", "W4", "W5")
READERS = ("oracle", "nla")
CONTROL_MANIFEST = "ef8dbcb153e5e3f6720d6666c9859f97df1cbde97408ae3d95ba843698035f37"
CATEGORIES = ("states_value", "names_property_without_value", "exhibits", "silent")
PROPERTIES = dict(zip(STATES, ("open string", "bracket depth", "indentation",
    "inside call arguments vs at statement level", "line length so far")))
PROPERTIES.update(W7="code vs prose", W8="Wikipedia topic")
RUBRIC_SHA = "03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613"
SOURCE_FILES = {"projects/g_agreement/e73/" + n for n in
                ("analyze.py", "custody.py", "states.py", "delivery.py", "__init__.py")}
RULES = {"states": list(STATES), "readers": list(READERS), "positions_per_state": 200,
         "label_convention": "0=A,1=B", "probe_threshold": .90,
         "bootstrap_draws": 2000, "bootstrap_seed": 20261027,
         "bootstrap_unit": "position", "pooled_strata": "state",
         "unparseable": "exclude_and_count", "R_W2_max_S": .10,
         "falsifier_min_pooled_S": .20, "R_W1": "UNRESOLVED_PENDING_GUIV"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def normalize(text):
    quotes = dict.fromkeys("‘’‚‛", "'") | dict.fromkeys('“”„‟«»', '"')
    return re.sub(r"\s+", " ", "".join(quotes.get(c, "-" if unicodedata.category(c) == "Pd"
        else c) for c in text)).strip().casefold()


def validate_judgment(code, text):
    """Exact E56 flat adapter schema and normalized-evidence policy; no repair."""
    require(set(code) == {"id", "category", "values", "evidence"}, "judgment schema")
    values, evidence, category = code["values"], code["evidence"], code["category"]
    if category == "UNPARSEABLE":
        require(values == [] and evidence == "", "UNPARSEABLE sentinel")
        return
    require(category in CATEGORIES and isinstance(values, list)
            and all(type(v) is str for v in values) and len(values) == len(set(values))
            and set(values) <= {"A", "B"}, "judgment category/values")
    require(bool(values) == (category == "states_value"), "judgment category/value mismatch")
    require(isinstance(evidence, str) and normalize(evidence) in normalize(text)
            and (bool(normalize(evidence)) or category == "silent"), "normalized evidence")


def signed_value(code, label):
    require(type(label) is int and label in (0, 1), "E73 label must be 0=A or 1=B")
    if code["category"] == "UNPARSEABLE":
        return None
    if code["category"] != "states_value" or len(code["values"]) != 1:
        return 0
    return 1 if code["values"] == ["AB"[label]] else -1


def interval(groups):
    """Fixed-size independent position draws within each sorted state stratum.

    Missing judgments are removed before resampling. Each retained state's size
    stays fixed, so the pooled estimate weights positions, not states equally.
    An entirely missing eligible state leaves the pooled interval unavailable.
    """
    arrays = [np.asarray(groups[s], dtype=np.int8) for s in sorted(groups)]
    if not arrays or any(len(x) == 0 for x in arrays):
        return None
    require(all(x.ndim == 1 and np.isin(x, [-1, 0, 1]).all() for x in arrays), "signed position scores")
    rng = np.random.default_rng(20261027)
    sums = np.zeros(2000, dtype=np.int64)
    for x in arrays:
        sums += x[rng.integers(0, len(x), size=(2000, len(x)))].sum(axis=1)
    return np.quantile(sums / sum(map(len, arrays)), [.025, .975]).tolist()


def summarize(records, *, stratified):
    groups = {}
    for state, score, _ in records:
        group = groups.setdefault(state if stratified else "positions", [])
        if score is not None:
            group.append(score)
    scores = [score for _, score, _ in records if score is not None]
    n, kept = len(records), len(scores)
    counts = Counter(category for _, _, category in records)
    return {"n_readouts": n, "kept": kept, "UNPARSEABLE": n - kept,
            "flag_over_5_percent": 20 * (n - kept) > n,
            "category_counts": dict(counts),
            "category_shares": {c: counts[c] / kept if kept else None for c in CATEGORIES},
            "correct_only": scores.count(1), "wrong_only": scores.count(-1),
            "signed_sum": sum(scores), "S": sum(scores) / kept if kept else None,
            "CI95": interval(groups), "retained_positions_per_stratum": {s: len(v) for s, v in groups.items()},
            "bootstrap_draws": 2000, "bootstrap_seed": 20261027,
            "bootstrap_unit": "position", "stratified_by_state": stratified}


def compute(key, judgments, probe_rows):
    """Pure CPU calculation; production caller verifies custody first."""
    codes = unique(judgments, "id")
    require(set(codes) == {r["opaque_id"] for r in key}, "judgment/key grid")
    probes = unique(probe_rows, "state")
    require(set(probes) == set(STATES), "all five probe rows required")
    for p in probes.values():
        require(type(p["test_auroc"]) in (int, float) and math.isfinite(p["test_auroc"])
                and 0 <= p["test_auroc"] <= 1 and p["probe_pass"] is (p["test_auroc"] >= .90), "probe eligibility")
    eligible = [s for s in STATES if probes[s]["probe_pass"]]
    readers = {}
    for reader in READERS:
        rows, joined, truncation = {}, [], {}
        for state in STATES:
            selected = sorted((k for k in key if k["reader"] == reader and k["state"] == state), key=lambda k: k["source_id"])
            require(len(selected) == 200, "exact 200 positions per reader/state")
            values = [(state, signed_value(codes[k["opaque_id"]], k["label"]), codes[k["opaque_id"]]["category"]) for k in selected]
            rows[state] = summarize(values, stratified=False)
            require(all(type(k["judge_attempts"]) is int and 0 <= k["judge_attempts"] <= 2 for k in selected), "validated retry counts required")
            rows[state]["retried"] = sum(k["judge_attempts"] > 0 for k in selected)
            rows[state]["confirmatory_eligible"] = state in eligible
            if state in eligible:
                joined.extend(values)
            if reader == "nla":
                n = sum(k["truncated"] for k in selected)
                truncation[state] = {"n": 200, "truncated": n, "rate": n / 200, "flag_over_10_percent": 10 * n > 200}
        pooled = summarize(joined, stratified=True)
        pooled["retried"] = sum(rows[s]["retried"] for s in eligible)
        available = bool(eligible) and all(rows[s]["kept"] for s in eligible)
        per_state = {s: None if not rows[s]["kept"] else 10 * rows[s]["signed_sum"] <= rows[s]["kept"] for s in eligible}
        readers[reader] = {"states": rows, "pooled_eligible_structural": pooled,
            "judgment_missingness": {"total": 1000, "kept": sum(v["kept"] for v in rows.values()),
                "UNPARSEABLE": sum(v["UNPARSEABLE"] for v in rows.values()),
                "retried": sum(v["retried"] for v in rows.values()),
                "flag_over_5_percent": sum(v["UNPARSEABLE"] for v in rows.values()) > 50},
            "R_W2": {"eligible_states": eligible, "per_state_pass": per_state,
                       "all_eligible_pass": all(per_state.values()) if available else None},
            "falsifier_pooled_S_ge_0_20": 5 * pooled["signed_sum"] >= pooled["kept"] if available else None,
            "NLA_truncation": truncation if reader == "nla" else None}
    return {"experiment": "E73", "rules": RULES, "probe_rows": probe_rows, "readers": readers,
            "retried_definition": "Count of records with terminal attempts > 0: 0 is the initial pass, 1/2 are retries; includes exhausted UNPARSEABLE.",
            "R_W1": {"status": "UNRESOLVED_PENDING_GUIV", "publication_allowed": False,
                     "reason": "No BOW-passing content control; verdict scope requires Guiv's ruling."},
            "descriptive_states": list(STATES), "confirmatory_eligible_states": eligible}


def unique(rows, field):
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), "record list required")
    out = {r[field]: r for r in rows}
    require(len(out) == len(rows), "duplicate " + field)
    return out


def read(path):
    return json.loads(Path(path).read_text())


def checked(ref):
    require(set(ref) == {"path", "sha256"}, "explicit path/hash reference required")
    path = Path(ref["path"])
    require(path.is_absolute() and path.is_file() and not path.is_symlink(), "ordinary absolute input required")
    require(sha256(path) == ref["sha256"], "input hash mismatch: " + path.name)
    return path


def checked_seal(ref):
    path = checked(ref)
    value = read(path)
    require(isinstance(value.get("files"), dict) and value["files"], "nonempty seal required")
    for name, entry in value["files"].items():
        rel = Path(name)
        require(not rel.is_absolute() and ".." not in rel.parts and rel.as_posix() == name, "unsafe seal member")
        member = path.parent / rel
        digest = entry["sha256"] if isinstance(entry, dict) else entry
        checked({"path": str(member), "sha256": digest})
        if isinstance(entry, dict):
            require(member.stat().st_size == entry["bytes"], "sealed size differs")
    return path.parent, value


def member(root, value, name):
    require(name in value["files"], "required sealed member missing: " + name)
    return root / name


def git_file(repo, commit, name):
    require(re.fullmatch("[0-9a-f]{40}", commit) is not None, "full commit required")
    path = Path(name)
    require(not path.is_absolute() and ".." not in path.parts, "repository-relative committed path required")
    return subprocess.check_output(["git", "show", commit + ":" + path.as_posix()], cwd=repo, stderr=subprocess.PIPE)


def verify_plan(plan_path, commit, expected_sha):
    content = git_file(REPO, commit, plan_path)
    require(hashlib.sha256(content).hexdigest() == expected_sha
            and (REPO / plan_path).read_bytes() == content, "immutable analysis plan mismatch")
    plan = json.loads(content)
    require(plan.get("schema") == "e73-analysis-plan-v1" and plan.get("rules") == RULES, "frozen E73 analysis specification")
    sources = plan["source_files"]
    require(SOURCE_FILES <= set(sources), "analysis executable dependency hashes missing")
    for name, digest in sources.items():
        require(hashlib.sha256(git_file(REPO, commit, name)).hexdigest() == digest
                and sha256(REPO / name) == digest, "committed analysis source changed: " + name)
    require(sha256(Path(__file__)) == sources["projects/g_agreement/e73/analyze.py"], "running analysis source differs")
    require(Path(plan["output"]).is_absolute(), "absolute canonical once-only output required")
    return plan


def load_inputs(plan, *, controls=False):
    """Cross-bind sealed pipeline artifacts; called only after the once claim."""
    i = plan["inputs"]
    states = ("W7", "W8") if controls else STATES
    bank_n = 1432 if controls else 4000
    reader_n = 200 * len(states)
    required = {"bank_manifest", "labels", "gate", "probe_seal", "reader_input_seal", "reader_index",
                "go", "forecast", "native_seals", "packet_seal", "private_key", "judgment_seal", "terminal_seal"}
    require(set(i) == required, "complete explicit input plan required")
    paths = {k: checked(v) for k, v in i.items() if k not in {"forecast", "native_seals"}}
    bank, gate, index, go = (read(paths[k]) for k in ("bank_manifest", "gate", "reader_index", "go"))
    require(bank.get("experiment") == "E73" and bank.get("stage") == "BOW_GATE_SEALED"
            and bank.get("items") == bank_n and bank.get("context_tokens") == 256, "frozen bank manifest")
    require(bank["private_labels_sha256"] == i["labels"]["sha256"] and bank["gate_report_sha256"] == i["gate"]["sha256"], "bank label/gate binding")
    require(gate["included_states"] == list(states) and set(gate["excluded_states"]) == ({"W6"} if controls else {"W6", "W7", "W8"}), "frozen BOW scope")
    if controls:
        validate_gate(gate)
        require(i["bank_manifest"]["sha256"] == CONTROL_MANIFEST, "frozen control manifest")
    require(gate.get("status") == "BOW_GATE_SEALED" and gate.get("threshold") == .65
            and gate.get("retained_private_labels_sha256") == i["labels"]["sha256"]
            and (controls or all(gate["metrics"][s]["gate_pass"] is True and 0 <= gate["metrics"][s]["test_auroc"] <= .65 for s in states)), "frozen BOW decisions")
    require(index["bank_manifest_sha256"] == i["bank_manifest"]["sha256"] and index["probe_seal_sha256"] == i["probe_seal"]["sha256"]
            and index["total"] == reader_n and index.get("schema") == "e73-reader-inputs-v1"
            and index.get("labels_present") is False, "reader index binding")
    root, s = checked_seal(i["reader_input_seal"])
    require(s.get("status") == "COMPLETE" and s.get("track") == "C", "complete reader input seal required")
    require(member(root, s, "READER_INPUTS.json") == paths["reader_index"], "reader index seal membership")
    shard_counts = {}
    for shard in index["shards"]:
        p = member(root, s, shard["file"])
        require(sha256(p) == shard["sha256"] and p.stat().st_size == shard["bytes"]
                and shard["sha256"] not in shard_counts and type(shard["count"]) is int and shard["count"] > 0, "reader shard binding")
        shard_counts[shard["sha256"]] = shard["count"]
    require(sum(shard_counts.values()) == reader_n, "reader input shard count")
    check_go(go, capture_seal_sha=i["reader_index"]["sha256"], input_manifest_sha=i["bank_manifest"]["sha256"])
    f = i["forecast"]
    proof = forecast_proof(Path(f["repo"]), f["commit"], f["path"], f["sha256"])
    require((f["commit"], f["sha256"]) == (go["jforecast_commit"], go["jforecast_sha256"]), "forecast/GO binding")
    root, s = checked_seal(i["probe_seal"])
    require(s.get("status") == "COMPLETE", "complete probe seal required")
    probe = read(member(root, s, "PROBE_REPORT.json"))
    for field, ref in (("bank_manifest_sha256", "bank_manifest"), ("gate_report_sha256", "gate"), ("private_labels_sha256", "labels")):
        require(probe[field] == i[ref]["sha256"], "probe input binding: " + field)
    require(probe["capture_seals"] == index["source_capture_seals"], "capture lineage differs")
    labels = unique(read_jsonl(paths["labels"]), "id")
    require(len(labels) == bank_n and set(x["state"] for x in labels.values()) == set(states), "frozen private bank grid")
    selected = {}
    for state in states:
        per_split = 316 if state == "W8" else 400
        for split in ("dev", "test"):
            cell = sorted((x for x in labels.values() if x["state"] == state and x["split"] == split), key=lambda x: x["id"])
            require(len(cell) == per_split and Counter(x["label"] for x in cell) == {0: per_split // 2, 1: per_split // 2}, "frozen balanced dev/test grid")
            for n, row in enumerate(cell):
                keep = split == "test" and n < 200
                require(type(row["label"]) is int and row["reader_selected"] is keep, "frozen first-200 selection")
                if keep:
                    selected[row["id"]] = row
    root, bs = checked_seal(i["packet_seal"])
    require(bs["experiment"] == "E73" and bs["rubric_sha256"] == RUBRIC_SHA and bs["private_key_sha256"] == i["private_key"]["sha256"]
            and bs["reader_index_sha256"] == i["reader_index"]["sha256"], "blind packet binding")
    require(sha256(member(root, bs, "JUDGE_RUBRIC.md")) == RUBRIC_SHA, "frozen rubric differs")
    packet = unique(read(member(root, bs, "JUDGE_PACKET.json")), "id")
    provenance = read(member(root, bs, "PROVENANCE.json"))
    for field, ref in (("bank_manifest_sha256", "bank_manifest"), ("reader_index_sha256", "reader_index"),
            ("reader_input_seal_sha256", "reader_input_seal"), ("private_labels_sha256", "labels"),
            ("gate_report_sha256", "gate"), ("probe_seal_sha256", "probe_seal"), ("go_sha256", "go")):
        require(provenance[field] == i[ref]["sha256"], "packet provenance: " + field)
    require(provenance["forecast_proof"] == proof and provenance["source_capture_seals"] == index["source_capture_seals"], "packet forecast/capture lineage")
    expected_native = {(x["path"], x["sha256"]) for x in provenance["native_seals"]}
    require(len(i["native_seals"]) == len(expected_native) and
            {(str(Path(x["path"]).parent), x["sha256"]) for x in i["native_seals"]} == expected_native, "native seal inventory")
    native, used_shards = {}, set()
    for ref in i["native_seals"]:
        nr, ns = checked_seal(ref)
        require(ns.get("status") == "COMPLETE" and ns.get("track") == "C", "complete native seal required")
        require(member(nr, ns, "GO.json").read_bytes() == paths["go"].read_bytes(), "native GO differs")
        report = read(member(nr, ns, "READER_REPORT.json"))
        require(report["reader_index_sha256"] == i["reader_index"]["sha256"] and report["status"] == "COMPLETE"
                and (report["jforecast_commit"], report["jforecast_sha256"]) == (f["commit"], f["sha256"]), "native report binding")
        digest = report["input_sha256"]
        require(digest in shard_counts and digest not in used_shards and report["total_per_reader"] == shard_counts[digest], "native residual shard coverage")
        used_shards.add(digest)
        for reader in READERS:
            rows = read_jsonl(member(nr, ns, reader + ".jsonl"))
            require(len(rows) == report["completed"][reader] == report["total_per_reader"], "native report counts")
            for row in rows:
                k = (reader, row["id"])
                require(k not in native and row["reader"] == reader and row["greedy"] is True
                        and row["capture_layer"] == (44 if reader == "oracle" else 42)
                        and row["max_new_tokens"] == (128 if reader == "oracle" else 512), "native identity/settings")
                native[k] = row
    require(used_shards == set(shard_counts) and set(native) == {(r, uid) for r in READERS for uid in selected}, "exact two-reader frozen grid")
    key = read(paths["private_key"])
    keyed = unique(key, "opaque_id")
    require(len(key) == 2 * reader_n and set(keyed) == set(packet) and len({(k["reader"], k["source_id"]) for k in key}) == 2 * reader_n, "private key exact grid")
    for k in key:
        label = selected[k["source_id"]]
        require(k["reader"] in READERS and k["state"] == label["state"] and k["label"] == label["label"] and k["value"] == "AB"[label["label"]], "private label orientation")
        raw = native[k["reader"], k["source_id"]]["raw_output"]
        require(hashlib.sha256(raw.encode()).hexdigest() == k["raw_output_sha256"], "private key raw binding")
        nla = k["reader"] == "nla"
        truncated = "</explanation>" not in raw if nla else None
        require(k["truncated"] is truncated and native[k["reader"], k["source_id"]]["truncated"] is truncated, "truncation binding")
        match = re.search(r"<explanation>(.*?)</explanation>", raw, re.DOTALL) if nla else None
        p = packet[k["opaque_id"]]
        require(p["readout"] == (match.group(1).strip() if match else raw) and p["property"] == PROPERTIES[k["state"]]
                and p["values"] == dict(zip(("A", "B"), STATE_VALUES[k["state"]])), "unaltered E56 packet text/values")
    tr, ts = checked_seal(i["terminal_seal"])
    require(ts.get("bank") == "E73" and ts.get("status") == "TERMINAL_BLIND_GRID_NO_ANALYSIS"
            and ts.get("channel", "value") == "value"
            and ts.get("packet_seal_sha256") == i["packet_seal"]["sha256"], "terminal judge custody")
    root, js = checked_seal(i["judgment_seal"])
    require(js.get("blind_seal_sha256") == i["packet_seal"]["sha256"] and js.get("terminal_seal_sha256") == i["terminal_seal"]["sha256"], "adapted judgment binding")
    judgments = read(member(root, js, "JUDGMENTS.json"))
    codes = unique(judgments, "id")
    terminals = unique(read(member(tr, ts, "JUDGMENTS.json")), "id")
    require(set(codes) == set(packet) == set(terminals), "exact sealed judgment grid")
    for uid, code in codes.items():
        validate_judgment(code, packet[uid]["readout"])
        t = terminals[uid]
        require(type(t["attempts"]) is int and 0 <= t["attempts"] <= 2, "terminal retry count")
        require((t["status"] == "KEPT" and code["category"] in CATEGORIES and t["code"] == code) or
                (t["status"] == "UNPARSEABLE" and t["attempts"] == 2 and t["code"] is None and code["category"] == "UNPARSEABLE"), "lossless terminal adaptation")
    # Keep the sealed private key and codes unchanged on disk. Attempts are joined
    # only into the validated CPU records for required missingness reporting.
    joined_key = [dict(k, judge_attempts=terminals[k["opaque_id"]]["attempts"]) for k in key]
    return joined_key, judgments, probe["rows"]


def run(plan_path, commit, expected_sha):
    plan = verify_plan(plan_path, commit, expected_sha)
    out = Path(plan["output"])
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "ONCE.json", {"experiment": "E73", "invocation": 1, "plan_sha256": expected_sha,
                                   "commit": commit, "source_files": plan["source_files"]})
    try:
        key, codes, probes = load_inputs(plan)
        result = compute(key, codes, probes)
        result["input_plan_sha256"] = expected_sha
        write_json(out / "RESULTS.json", result)
        seal(out, "ANALYSIS_SEAL.json", [out / "ONCE.json", out / "RESULTS.json"],
             experiment="E73", status="COMPLETE_R_W1_UNRESOLVED_PENDING_GUIV", plan_sha256=expected_sha)
        return result
    except BaseException as error:
        write_json(out / "FAILURE.json", {"type": type(error).__name__, "message": str(error)})
        raise


def main():
    raise SystemExit("Historical CLI superseded by §191 clarification 4: use projects.g_agreement.e73.analyze_controls")


if __name__ == "__main__":
    main()
