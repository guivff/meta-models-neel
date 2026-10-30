"""E29 CPU values only: prospective W12 D/P, then the posted-gated non-blind companion.

D uses the E25 fixed A-minus-B convention. No reader outcomes, correlations,
bootstrap, or R1/R2 decision path is implemented here. Dated 2026-10-25.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[4]
COHORTS = ("w12", "suraj_exp13")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def _reject_nonfinite(_):
    raise ValueError("Non-finite JSON literal")


def read(path):
    return json.loads(Path(path).read_text(), parse_constant=_reject_nonfinite)


def jsonl(path):
    records = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            raise ValueError("Blank score ledger line")
        records.append(json.loads(line, parse_constant=_reject_nonfinite))
    return records


def dump(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _member(root, name):
    p = Path(name)
    if not name or p.is_absolute() or ".." in p.parts:
        raise ValueError("Unsafe sealed path")
    candidate = (Path(root) / p).resolve()
    if not candidate.is_relative_to(Path(root).resolve()):
        raise ValueError("Sealed path escapes its root")
    return candidate


def verify_files(root, files):
    if not isinstance(files, dict) or not files:
        raise ValueError("Missing file hash manifest")
    for name, digest in files.items():
        if not isinstance(name, str) or not _digest(digest) or sha(_member(root, name)) != digest:
            raise ValueError("Sealed payload or source hash mismatch")


def select_cohort(plan, name):
    if plan.get("status") != "READY" or name not in COHORTS:
        raise ValueError("Require READY E29 plan and known cohort")
    cohorts = plan.get("cohorts")
    if not isinstance(cohorts, list) or [c.get("name") for c in cohorts] != list(COHORTS):
        raise ValueError("Cohort order must be W12 primary then Suraj companion")
    for c, expected_blind, expected_phrasings in zip(cohorts, (True, False), (2, 1)):
        if c.get("blind") is not expected_blind or type(c.get("phrasing_count")) is not int or c["phrasing_count"] != expected_phrasings:
            raise ValueError("Cohort blindness or phrasing count changed")
        rows, items = c.get("rows"), c.get("items")
        if (not isinstance(rows, list) or not rows or not all(isinstance(r, str) and r for r in rows)
                or len(set(rows)) != len(rows) or not isinstance(items, list) or not items):
            raise ValueError("Invalid frozen row/item list")
        by_id = {}
        for item in items:
            key = item.get("id")
            if not isinstance(key, str) or not key or key in by_id or item.get("feature") not in rows:
                raise ValueError("Invalid or duplicate frozen item")
            by_id[key] = item["feature"]
        if set(by_id.values()) != set(rows):
            raise ValueError("Frozen row without items")
        if type(c.get("expected_scores")) is not int or c["expected_scores"] != len(items) * expected_phrasings * 2:
            raise ValueError("Expected score count does not match frozen grid")
        if not _digest(c.get("input_seal_sha256")) or not _digest(c.get("labels_sha256")) or not c.get("freeze"):
            raise ValueError("Missing frozen input identity")
    return next(c for c in cohorts if c["name"] == name)


def verify_score_custody(plan_path, plan, cohort, scores_dir):
    """Check code, complete score seal and provenance BEFORE parsing any labels."""
    verify_files(ROOT, plan.get("source_files"))
    own = str(Path(__file__).resolve().relative_to(ROOT))
    if plan["source_files"].get(own) != sha(__file__):
        raise ValueError("Analysis source missing from frozen plan")
    scores_dir = Path(scores_dir)
    seal = read(scores_dir / "SCORE_SEAL.json")
    if (seal.get("complete") is not True or seal.get("cohort") != cohort["name"]
            or seal.get("plan_sha256") != sha(plan_path)):
        raise ValueError("Incomplete or mismatched cohort score seal")
    files = seal.get("files", {})
    if not {"scores.jsonl", "provenance.json"}.issubset(files):
        raise ValueError("Missing score/provenance binding")
    verify_files(scores_dir, files)
    provenance = read(scores_dir / "provenance.json")
    if (provenance.get("input_seal_sha256") != cohort["input_seal_sha256"]
            or provenance.get("source_files") != plan["source_files"]
            or not _digest(provenance.get("assignment_sha256"))):
        raise ValueError("Score provenance/source/input mismatch")
    return seal, provenance


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must include timezone")
    return parsed


def verify_primary_posted(primary_seal_path, posted_record_path, plan_path, plan):
    """A companion cannot be analysed until complete W12 values were sealed and posted."""
    if primary_seal_path is None or posted_record_path is None:
        raise ValueError("Companion requires primary seal and primary posted record")
    primary_seal_path = Path(primary_seal_path)
    seal = read(primary_seal_path)
    w12 = select_cohort(plan, "w12")
    if (seal.get("complete") is not True or seal.get("cohort") != "w12" or seal.get("blind") is not True
            or seal.get("plan_sha256") != sha(plan_path)
            or seal.get("input_seal_sha256") != w12["input_seal_sha256"]
            or seal.get("labels_sha256") != w12["labels_sha256"]
            or seal.get("freeze") != w12["freeze"]
            or seal.get("source_files") != plan["source_files"]):
        raise ValueError("Invalid primary W12 values identity")
    files = seal.get("files", {})
    if not {"METRICS.json", "RESULTS.md", "cache/ITEM_SCORES.jsonl"}.issubset(files):
        raise ValueError("Incomplete primary values seal")
    verify_files(primary_seal_path.parent, files)
    primary_metrics = read(primary_seal_path.parent / "METRICS.json")
    if (primary_metrics.get("cohort") != "w12" or primary_metrics.get("blind") is not True
            or [r.get("feature") for r in primary_metrics.get("rows", [])] != w12["rows"]):
        raise ValueError("Primary metrics row/cohort mismatch")
    posted = read(posted_record_path)
    if (posted.get("issuer") not in ("coordinator", "integrator", "W-text") or posted.get("posted") is not True
            or posted.get("primary_seal_sha256") != sha(primary_seal_path)
            or not isinstance(posted.get("publication_reference"), str)
            or not posted["publication_reference"].strip()):
        raise ValueError("Primary publication requires a referenced truthful posting record from W-text/coordinator/integrator")
    created, when = _timestamp(seal.get("created_at")), _timestamp(posted.get("posted_at"))
    if not created <= when <= datetime.now(timezone.utc):
        raise ValueError("Primary posting timestamp does not follow value sealing")
    return {"primary_seal_sha256": sha(primary_seal_path), "posted_record_sha256": sha(posted_record_path),
            "issuer": posted["issuer"], "posted_at": posted["posted_at"],
            "publication_reference": posted["publication_reference"]}


def validate_grid(scores, labels, cohort):
    item_map = {x["id"]: x["feature"] for x in cohort["items"]}
    if not isinstance(labels, list):
        raise ValueError("Labels must be the frozen JSON list")
    label_map = {}
    for item in labels:
        key = item.get("id")
        if key not in item_map or key in label_map or item.get("feature") != item_map[key] or item.get("value") not in ("A", "B"):
            raise ValueError("Invalid, duplicate or out-of-scope label")
        label_map[key] = item["value"]
    if set(label_map) != set(item_map):
        raise ValueError("Missing frozen label")
    for feature in cohort["rows"]:
        if {label_map[k] for k, f in item_map.items() if f == feature} != {"A", "B"}:
            raise ValueError("Both label classes required in every row")
    grid = {}
    for record in scores:
        key, feature = record.get("id"), record.get("feature")
        p, candidate = record.get("phrasing"), record.get("candidate")
        if key not in item_map or feature != item_map[key] or type(p) is not int or p not in range(cohort["phrasing_count"]) or candidate not in ("A", "B"):
            raise ValueError("Score outside exact frozen grid")
        cell = (key, p, candidate)
        value, count = record.get("mean_logprob"), record.get("token_count")
        if (cell in grid or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value > 0 or type(count) is not int or count <= 0):
            raise ValueError("Duplicate, nonfinite, positive or invalid score")
        grid[cell] = float(value)
    expected = {(key, p, c) for key in item_map for p in range(cohort["phrasing_count"]) for c in ("A", "B")}
    if len(scores) != cohort["expected_scores"] or set(grid) != expected:
        raise ValueError("Missing or extra score cell")
    return label_map, grid


def auc(y, scores):
    y, scores = np.asarray(y), np.asarray(scores, dtype=float)
    if (y.ndim != 1 or y.shape != scores.shape or not np.isfinite(scores).all()
            or not np.isin(y, (0, 1)).all() or set(y.tolist()) != {0, 1}):
        raise ValueError("AUROC requires finite scores and both binary classes")
    n1, n0 = int(y.sum()), int((y == 0).sum())
    ranks = rankdata(scores, method="average")
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def compute_values(scores, labels, cohort):
    label_map, grid = validate_grid(scores, labels, cohort)
    ledger = []
    for item in cohort["items"]:
        key = item["id"]
        a = float(np.mean([grid[key, p, "A"] for p in range(cohort["phrasing_count"])]))
        b = float(np.mean([grid[key, p, "B"] for p in range(cohort["phrasing_count"])]))
        record = {"id": key, "feature": item["feature"], "value": label_map[key],
                  "s_A": a, "s_B": b, "margin_A_minus_B": a - b}
        if cohort["blind"]:
            record["true_candidate_score"] = a if label_map[key] == "A" else b
        ledger.append(record)
    rows = []
    for feature in cohort["rows"]:
        items = [r for r in ledger if r["feature"] == feature]
        y = [int(r["value"] == "A") for r in items]
        row = {"feature": feature, "n": len(items), "n_A": sum(y), "n_B": len(y) - sum(y),
               "D": auc(y, [r["margin_A_minus_B"] for r in items])}
        if cohort["blind"]:
            row["P"] = float(np.median([r["true_candidate_score"] for r in items]))
        rows.append(row)
    return rows, ledger


def render(metrics):
    blind = metrics["blind"]
    lines = ["# E29 — " + ("prospective W12 D and P" if blind else "NON-BLIND Suraj exp-13 D companion"), "",
             "Dated values: " + metrics["created_at"] + ". CPU analysis of sealed base-Qwen scores.", "",
             ("W12 values are sealed for the coordinator's prospective predictions. Reader comparisons remain pending."
              if blind else "NON-BLIND and descriptive: the registered Suraj reader outcomes were already known. W12 values were sealed and published before this analysis, as recorded by W-text, the coordinator or the integrator."), "",
             "D = AUROC(s_A − s_B, value A), with each candidate score averaged equally over its frozen phrasings. No sign reversal.", ""]
    if blind:
        lines += ["P is the median across items of the true candidate's averaged score.", "",
                  "| Row | Items | D | P |", "|---|---:|---:|---:|"]
        lines += [f"| {r['feature']} | {r['n']} | {r['D']:.6f} | {r['P']:.6f} |" for r in metrics["rows"]]
    else:
        lines += ["| Row | Items | D |", "|---|---:|---:|"]
        lines += [f"| {r['feature']} | {r['n']} | {r['D']:.6f} |" for r in metrics["rows"]]
    lines += ["", "No reader references were loaded, and no R1/R2 test, reader correlation, confidence interval or verdict was computed.",
              "The ignored item ledger preserves each original item ID, value, candidate means and signed margin for a later paired comparison.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "cohort", "scores-dir", "labels", "out"):
        parser.add_argument("--" + name, required=True, type=Path if name != "cohort" else str)
    parser.add_argument("--primary-seal", type=Path)
    parser.add_argument("--primary-posted-record", type=Path)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise ValueError("Existing output: no overwrite or implicit rerun")
    plan = read(args.plan)
    cohort = select_cohort(plan, args.cohort)
    score_seal, provenance = verify_score_custody(args.plan, plan, cohort, args.scores_dir)
    primary = None
    if args.cohort == "suraj_exp13":
        primary = verify_primary_posted(args.primary_seal, args.primary_posted_record, args.plan, plan)
    elif args.primary_seal is not None or args.primary_posted_record is not None:
        raise ValueError("Primary values must not depend on a companion posting record")
    if sha(args.labels) != cohort["labels_sha256"]:
        raise ValueError("Frozen label hash mismatch")
    # All source, score and sequencing checks precede this first label parse.
    scores, labels = jsonl(args.scores_dir / "scores.jsonl"), read(args.labels)
    rows, ledger = compute_values(scores, labels, cohort)
    created = datetime.now(ZoneInfo("Europe/Zurich")).isoformat(timespec="seconds")
    identity = {"experiment": "E29", "cohort": cohort["name"], "blind": cohort["blind"], "created_at": created,
                "plan_sha256": sha(args.plan), "input_seal_sha256": cohort["input_seal_sha256"],
                "labels_sha256": cohort["labels_sha256"], "freeze": cohort["freeze"],
                "score_seal_sha256": sha(args.scores_dir / "SCORE_SEAL.json"),
                "source_files": plan["source_files"], "assignment_sha256": provenance["assignment_sha256"]}
    metrics = {**identity, "status": "PROSPECTIVE_VALUES_READER_COMPARISON_PENDING" if cohort["blind"] else "NON_BLIND_DESCRIPTIVE_VALUES",
               "n_items": len(cohort["items"]), "phrasing_count": cohort["phrasing_count"], "rows": rows,
               "primary_posting": primary, "reader_comparison": "PENDING; no reader outcomes loaded",
               "D_definition": "AUROC(mean_phrasings_A - mean_phrasings_B, value_is_A)",
               "P_definition": "median true-candidate mean-phrasing score" if cohort["blind"] else "NOT REQUESTED for companion",
               "item_ledger": "cache/ITEM_SCORES.jsonl"}
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "cache").mkdir()
    with (args.out / "cache/ITEM_SCORES.jsonl").open("x") as f:
        for record in ledger:
            f.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    dump(args.out / "METRICS.json", metrics)
    with (args.out / "RESULTS.md").open("x") as f:
        f.write(render(metrics))
    names = ("METRICS.json", "RESULTS.md", "cache/ITEM_SCORES.jsonl")
    dump(args.out / "VALUES_SEAL.json", {**identity, "complete": True, "status": metrics["status"],
         "primary_posting": primary, "files": {name: sha(args.out / name) for name in names}})
    print("E29 " + cohort["name"] + " values sealed; " + metrics["status"])


if __name__ == "__main__":
    main()
