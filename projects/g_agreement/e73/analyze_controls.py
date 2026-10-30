"""Once-only §191 clarification 4 analysis across separately sealed E73 banks.

This is the final E73 entry point. analyze.py's original CLI is historical only;
its validated input loader and registered score/bootstrap functions are reused.
No real outcome is opened until the complete input plan and this source are
committed and an exclusive output-directory claim succeeds.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from . import analyze as A
from .custody import seal, sha256, write_json

AUTHORITY = "19da310478230f227e2d568d625b11ef49a04095"
CONTROLS = ("W7", "W8")
STRUCTURAL = ("W1", "W4", "W5")
DEADLINE = "2026-10-28T15:00:00+00:00"  # Wed 16:00 Europe/Zurich, later direct Guiv ruling.
BOW = {"W1": .5485500000000001, "W2": .600425, "W3": .6369499999999999,
       "W4": .54385, "W5": .603775, "W7": 1., "W8": .9641483736580676}
SOURCE_FILES = A.SOURCE_FILES | {"projects/g_agreement/e73/analyze_controls.py"}
RULES = {**A.RULES, "states": [*A.STATES, *CONTROLS], "structural_pool": list(STRUCTURAL),
         "descriptive_structural_states": ["W2", "W3"], "bow_exempt_controls": list(CONTROLS),
         "R_W1": {"pooled_structural_S_max": .05, "bootstrap_CI95_upper_max": .10,
                  "content_S_min": .30, "content_condition": "at least one of W7/W8 per reader",
                  "content_probe_threshold": None, "overall": "both readers meet all conditions"},
         "authority_commit": AUTHORITY, "missing_control_deadline_utc": DEADLINE,
         "deadline_authority": "Guiv direct instruction in I-2 turn 01a17f39-0bdd-7a60-ad30-a0c899cfbf49",
         "fallback_label": "WITHOUT_CONTENT_CONDITION",
         "no_structural_refit_or_rerun": True}


def conjunction(values):
    if any(v is False for v in values):
        return False
    return None if any(v is None for v in values) else True


def compute(structural, controls=None):
    """Pure calculation with synthetic tests; input custody is checked by run."""
    key, codes, probes = structural
    result = A.compute(key, codes, probes)
    A.require(result["confirmatory_eligible_states"] == list(STRUCTURAL), "Registered structural pool changed")
    control_rows = {}
    if controls is not None:
        ckey, ccodes, cprobes = controls
        A.require({k["source_id"] for k in key}.isdisjoint(k["source_id"] for k in ckey), "Banks overlap")
        A.require({k["opaque_id"] for k in key}.isdisjoint(k["opaque_id"] for k in ckey), "Opaque bank IDs overlap")
        control_rows = A.unique(cprobes, "state")
        A.require(set(control_rows) == set(CONTROLS), "Both control probe rows required")
        for row in control_rows.values():
            A.require(type(row["test_auroc"]) in (int, float) and 0 <= row["test_auroc"] <= 1
                      and row["probe_pass"] is (row["test_auroc"] >= .90), "Control probe report invalid")
        cmap = A.unique(ccodes, "id")
        A.require(set(cmap) == {k["opaque_id"] for k in ckey}, "Control judgment/key grid")
        A.require(len(ckey) == 800 and {(k["reader"], k["state"]) for k in ckey}
                  == {(r, s) for r in A.READERS for s in CONTROLS}, "Control grid differs")
        result["probe_rows"] = [*probes, *cprobes]
    verdicts = []
    for reader, data in result["readers"].items():
        rows = data["states"]
        for state in A.STATES:
            rows[state]["bow_auroc"] = BOW[state]
            rows[state]["bow_exempt"] = False
        if controls is not None:
            for state in CONTROLS:
                selected = sorted((k for k in ckey if k["reader"] == reader and k["state"] == state), key=lambda k: k["source_id"])
                A.require(len(selected) == 200, "Exactly 200 control readouts per state/reader")
                values = [(state, A.signed_value(cmap[k["opaque_id"]], k["label"]), cmap[k["opaque_id"]]["category"]) for k in selected]
                row = A.summarize(values, stratified=False)
                A.require(all(type(k["judge_attempts"]) is int and 0 <= k["judge_attempts"] <= 2 for k in selected), "Control retry counts")
                row.update(retried=sum(k["judge_attempts"] > 0 for k in selected),
                           confirmatory_eligible=False, positive_control=True, bow_exempt=True,
                           bow_auroc=BOW[state], probe_auroc=control_rows[state]["test_auroc"],
                           probe_pass=control_rows[state]["probe_pass"])
                rows[state] = row
                if reader == "nla":
                    n = sum(k["truncated"] for k in selected)
                    data["NLA_truncation"][state] = {"n": 200, "truncated": n, "rate": n / 200, "flag_over_10_percent": n > 20}
        pooled = data["pooled_eligible_structural"]
        structural_ok = None if pooled["CI95"] is None else (
            20 * pooled["signed_sum"] <= pooled["kept"] and pooled["CI95"][1] <= .10)
        content_checks = {s: None if not rows[s]["kept"] else 10 * rows[s]["signed_sum"] >= 3 * rows[s]["kept"]
                          for s in CONTROLS} if controls is not None else {}
        content_ok = (True if any(v is True for v in content_checks.values()) else
                      None if any(v is None for v in content_checks.values()) else False) if content_checks else None
        passed = conjunction([structural_ok, content_ok]) if controls is not None else structural_ok
        verdicts.append(passed)
        data["R_W1"] = {"structural_condition_met": structural_ok, "content_per_state": content_checks,
                        "content_condition_met": content_ok, "pass": passed,
                        "scope": "FULL" if controls is not None else "WITHOUT_CONTENT_CONDITION"}
        total = 200 * len(rows)
        data["judgment_missingness"] = {"total": total, "kept": sum(v["kept"] for v in rows.values()),
            "UNPARSEABLE": sum(v["UNPARSEABLE"] for v in rows.values()), "retried": sum(v["retried"] for v in rows.values()),
            "flag_over_5_percent": 20 * sum(v["UNPARSEABLE"] for v in rows.values()) > total}
    passed = conjunction(verdicts)
    result.update(rules=RULES, descriptive_states=["W2", "W3"], positive_control_states=list(CONTROLS),
                  R_W1={"status": "NOT_EVALUABLE" if passed is None else "MET" if passed else "NOT_MET",
                        "pass": passed, "publication_allowed": True,
                        "scope": "FULL" if controls is not None else "WITHOUT_CONTENT_CONDITION",
                        "authority_commit": AUTHORITY})
    return result


def verify_plan(path, commit, expected_sha):
    content = A.git_file(A.REPO, commit, path)
    A.require(hashlib.sha256(content).hexdigest() == expected_sha and (A.REPO / path).read_bytes() == content,
              "Immutable amended analysis plan differs")
    plan = json.loads(content)
    A.require(plan.get("schema") == "e73-amended-analysis-plan-v1" and plan.get("rules") == RULES, "Amended rules differ")
    A.require(SOURCE_FILES <= set(plan["source_files"]), "Missing amended source dependencies")
    for name, digest in plan["source_files"].items():
        A.require(hashlib.sha256(A.git_file(A.REPO, commit, name)).hexdigest() == digest
                  and sha256(A.REPO / name) == digest, "Uncommitted amended analysis source")
    A.require(Path(plan["output"]).is_absolute(), "Absolute once-only output required")
    A.require(plan["mode"] in ("with_controls", "without_content_condition_at_deadline"), "Invalid amended mode")
    required = {"structural", "controls"} if plan["mode"] == "with_controls" else {"structural"}
    A.require(set(plan["banks"]) == required, "Amended bank inventory differs")
    if plan["mode"] != "with_controls":
        A.require(datetime.now(timezone.utc) >= datetime.fromisoformat(DEADLINE), "Guiv's deadline has not arrived")
        A.require(plan.get("controls_not_judged_by_deadline_attested_by") == "I-2", "Missing I-2 control availability attestation")
    return plan


def run(path, commit, expected_sha):
    plan = verify_plan(path, commit, expected_sha)
    out = Path(plan["output"])
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "ONCE.json", {"experiment": "E73", "invocation": 1, "commit": commit,
                                   "plan_sha256": expected_sha, "source_files": plan["source_files"]})
    try:
        structural = A.load_inputs({"inputs": plan["banks"]["structural"]})
        controls = A.load_inputs({"inputs": plan["banks"]["controls"]}, controls=True) if "controls" in plan["banks"] else None
        result = compute(structural, controls)
        result["input_plan_sha256"] = expected_sha
        write_json(out / "RESULTS.json", result)
        seal(out, "ANALYSIS_SEAL.json", [out / "ONCE.json", out / "RESULTS.json"], experiment="E73",
             status="COMPLETE", scope=result["R_W1"]["scope"], plan_sha256=expected_sha)
        return result
    except BaseException as error:
        write_json(out / "FAILURE.json", {"type": type(error).__name__, "message": str(error)})
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--plan-sha256", required=True)
    a = p.parse_args()
    run(a.plan, a.commit, a.plan_sha256)
    print("E73 amended analysis sealed.")


if __name__ == "__main__":
    main()
