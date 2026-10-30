"""E25 CPU analysis under dated clarification 1 (2026-10-25, e4225a1e).

No model inference. D is AUROC(s_A-s_B, value_is_A), where each candidate
score averages its two frozen W1 phrasings. P remains the median over items
of the corresponding true candidate's averaged score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from scipy.stats import rankdata

SEED = 20261025
BOOTSTRAP = 2000
P_NOTE = "Mean the true candidate's two frozen W1 phrasing scores per item, then take the row median."
D_NOTE = ("D: AUROC of s_A - s_B with W1 value A positive; s_A and s_B each average the two frozen W1 phrasing scores. "
          "Defined by §119 dated clarification 1, commit e4225a1e.")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path):
    def reject(value):
        raise ValueError("Non-finite JSON literal")
    return json.loads(Path(path).read_text(), parse_constant=reject)


def read_jsonl(path):
    records = []
    with Path(path).open() as f:
        for line in f:
            if not line.strip():
                raise ValueError("Blank line in score ledger")
            records.append(json.loads(line, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON literal"))))
    return records


def verify_scores_before_labels(scores_path, seal_path, plan_path):
    """Authenticate complete output BEFORE the caller may open label/reference files."""
    seal = load_json(seal_path)
    if seal.get("schema_version") != 1 or seal.get("complete") is not True:
        raise ValueError("Score seal is absent, incomplete, or unsupported")
    if seal.get("plan_sha256") != sha256(plan_path):
        raise ValueError("Score seal does not bind this frozen plan")
    files = seal.get("files", {})
    if not isinstance(files, dict) or Path(scores_path).name not in files:
        raise ValueError("Score ledger is not bound by score seal")
    for name, digest in files.items():
        if Path(name).name != name or not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("Unsafe or invalid score seal member")
        member = Path(scores_path).parent / name
        if sha256(member) != digest:
            raise ValueError("Score seal member SHA256 mismatch: " + name)
    return seal


def verify_analysis_inputs(labels_path, references_path, plan):
    """Bind withheld labels and W1 references without parsing either before custody checks."""
    inputs = plan.get("analysis_inputs", {})
    for name, path in (("labels_sha256", labels_path), ("references_sha256", references_path)):
        expected = inputs.get(name)
        if not isinstance(expected, str) or len(expected) != 64 or sha256(path) != expected:
            raise ValueError("Frozen analysis input SHA256 mismatch: " + name)


def _finite_number(x, name):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError(name + " must be finite numeric")
    return float(x)


def auc(labels, scores):
    """A-positive rank AUROC; ties receive one half, with no polarity flip."""
    y, s = np.asarray(labels), np.asarray(scores, dtype=float)
    if y.ndim != 1 or s.shape != y.shape or not np.isfinite(s).all():
        raise ValueError("Invalid AUROC vectors")
    if not set(y.tolist()) <= {0, 1}:
        raise ValueError("AUROC needs binary labels")
    n1, n0 = int(y.sum()), int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        raise ValueError("AUROC needs both labels")
    return float((rankdata(s, method="average")[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def _rank_corr(x, y, axis=None):
    a, b = rankdata(x, method="average", axis=axis), rankdata(y, method="average", axis=axis)
    a, b = a - a.mean(axis=axis, keepdims=True), b - b.mean(axis=axis, keepdims=True)
    denom = np.sqrt(np.sum(a * a, axis=axis) * np.sum(b * b, axis=axis))
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.sum(a * b, axis=axis) / denom


def correlation(x, y):
    value = float(_rank_corr(np.asarray(x), np.asarray(y)))
    return value if math.isfinite(value) else None


def interval(values):
    values = np.asarray(values, dtype=float)
    good = values[np.isfinite(values)]
    return {
        "ci95": np.quantile(good, [0.025, 0.975]).tolist() if len(good) else None,
        "bootstrap_draws": len(values),
        "finite_draws": len(good),
        "undefined_draws": len(values) - len(good),
    }


def validate_grid(scores, labels, references, plan):
    """Reject altered populations and any incomplete, duplicate or non-finite grid."""
    rows = plan.get("rows")
    items = plan.get("items")
    if not isinstance(rows, list) or len(rows) != 25 or len(set(rows)) != 25:
        raise ValueError("E25 requires exactly 25 distinct frozen rows")
    if not isinstance(items, list) or len(items) != 2100:
        raise ValueError("E25 requires exactly 2100 frozen items")
    item_map = {}
    for item in items:
        if not isinstance(item.get("id"), str) or item["id"] in item_map or item.get("feature") not in rows:
            raise ValueError("Invalid, duplicate or out-of-scope frozen item")
        item_map[item["id"]] = item["feature"]
    if any(sum(f == row for f in item_map.values()) != 84 for row in rows):
        raise ValueError("E25 requires 84 frozen test items per row")
    label_records = labels.get("items", [])
    label_map = {}
    for record in label_records:
        key = record.get("id")
        label = record.get("label")
        if key not in item_map or key in label_map or record.get("feature") != item_map[key]:
            raise ValueError("Label IDs/features differ from frozen input")
        if type(label) is not int or label not in (0, 1):
            raise ValueError("Labels must be integers: A=1, B=0")
        label_map[key] = label
    if set(label_map) != set(item_map):
        raise ValueError("Missing label")
    if any(sum(label_map[k] for k in item_map if item_map[k] == row) != 42 for row in rows):
        raise ValueError("Expected 42 A and 42 B items per row")
    refs = {}
    for record in references.get("rows", []):
        row = record.get("feature")
        if row not in rows or row in refs or record.get("class") not in ("structure", "semantic"):
            raise ValueError("Invalid reference row/class")
        for reader in ("olens", "nla", "probe"):
            val = _finite_number(record.get(reader), "Reference " + reader)
            if not 0 <= val <= 1:
                raise ValueError("Reference AUROC outside [0,1]")
        refs[row] = record
    if set(refs) != set(rows) or sum(r["class"] == "structure" for r in refs.values()) != 16:
        raise ValueError("Require exactly 16 structure and 9 semantic reference rows")
    grid = {}
    for record in scores:
        key, row = record.get("id"), record.get("feature")
        phrasing, candidate = record.get("phrasing"), record.get("candidate")
        if key not in item_map or row != item_map[key]:
            raise ValueError("Score ID/feature outside frozen input")
        if type(phrasing) is not int or phrasing not in (0, 1) or candidate not in ("A", "B"):
            raise ValueError("Unexpected phrasing/candidate")
        gkey = (key, phrasing, candidate)
        if gkey in grid:
            raise ValueError("Duplicate score cell")
        score = _finite_number(record.get("mean_logprob"), "Score")
        if score > 1e-7:
            raise ValueError("Positive log probability")
        count = record.get("token_count")
        if type(count) is not int or count <= 0:
            raise ValueError("Invalid candidate token count")
        grid[gkey] = score
    expected = {(key, p, c) for key in item_map for p in (0, 1) for c in ("A", "B")}
    if set(grid) != expected:
        raise ValueError("Incomplete score grid")
    return rows, item_map, label_map, refs, grid


def summarize(scores, labels, references, plan):
    rows, item_map, label_map, refs, grid = validate_grid(scores, labels, references, plan)
    settings = plan.get("analysis", {})
    if settings.get("seed") != SEED or settings.get("bootstrap") != BOOTSTRAP:
        raise ValueError("Registered seed/bootstrap changed")
    result_rows = []
    for row in rows:
        ids = sorted(key for key, feature in item_map.items() if feature == row)
        y = np.array([label_map[key] for key in ids])
        a = np.array([np.mean([grid[key, p, "A"] for p in (0, 1)]) for key in ids])
        b = np.array([np.mean([grid[key, p, "B"] for p in (0, 1)]) for key in ids])
        true_scores = np.where(y == 1, a, b)
        margin_ab = a - b
        result_rows.append({
            "feature": row, "class": refs[row]["class"], "n": len(ids),
            "P": float(np.median(true_scores)),
            "D": auc(y, margin_ab),
            "W1": {reader: refs[row][reader] for reader in ("olens", "nla", "probe")},
        })
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(rows), size=(BOOTSTRAP, len(rows)))
    correlations, contrasts = {}, {}
    for predictor in ("P", "D"):
        x = np.array([r[predictor] for r in result_rows])
        correlations[predictor], sampled = {}, {}
        for reader in ("olens", "nla", "probe"):
            y = np.array([r["W1"][reader] for r in result_rows])
            sampled[reader] = _rank_corr(x[draws], y[draws], axis=1)
            correlations[predictor][reader] = {"rho": correlation(x, y), **interval(sampled[reader])}
        contrasts[predictor] = {}
        for comparator in ("nla", "probe"):
            left = correlations[predictor]["olens"]["rho"]
            right = correlations[predictor][comparator]["rho"]
            contrasts[predictor]["olens_minus_" + comparator] = {
                "difference": left - right if left is not None and right is not None else None,
                **interval(sampled["olens"] - sampled[comparator]),
            }
    content = np.array([r["P"] for r in result_rows if r["class"] == "semantic"])
    structure = np.array([r["P"] for r in result_rows if r["class"] == "structure"])
    delta = np.median(content[rng.integers(0, len(content), size=(BOOTSTRAP, len(content)))], axis=1)
    delta -= np.median(structure[rng.integers(0, len(structure), size=(BOOTSTRAP, len(structure)))], axis=1)
    class_contrast = {
        "semantic_median": float(np.median(content)), "structure_median": float(np.median(structure)),
        "semantic_minus_structure": float(np.median(content) - np.median(structure)),
        "bootstrap_unit": "row, sampled independently within each of the two fixed classes",
        **interval(delta),
    }
    clarifications = plan.get("clarifications", {})
    acknowledged = (clarifications.get("integrator_acknowledged") is True
                    and clarifications.get("D_definition") == "AUROC(s_A-s_B,value_is_A)"
                    and clarifications.get("clarification_commit") == "e4225a1e"
                    and clarifications.get("phrasing_aggregation") == "mean_of_two_W1_pairs")
    p = correlations["P"]["olens"]
    p_direction = (p["rho"] is not None and p["rho"] >= .50 and p["ci95"] is not None and p["ci95"][0] > 0)
    class_direction = class_contrast["ci95"] is not None and class_contrast["ci95"][0] > 0
    return {
        "experiment": "E25", "status": "EXPLORATORY_ANALYSIS" if acknowledged else "DESCRIPTIVE_PENDING_CLARIFICATION",
        "seed": SEED, "bootstrap": BOOTSTRAP, "n_rows": 25, "n_items": 2100, "n_scores": 8400,
        "definitions": {"P": P_NOTE, "D": D_NOTE},
        "clarifications": clarifications,
        "analysis_choices_note": "D and two-phrasing aggregation follow published §119 dated clarification 1, e4225a1e; P is unchanged.",
        "rows": result_rows, "correlations": correlations, "discriminant_paired_rho_differences": contrasts,
        "class_plausibility_contrast": class_contrast,
        "prediction": {
            "held": bool(p_direction and class_direction) if acknowledged else None,
            "alternative_P_rho_below_0_30": bool(p["rho"] < .30) if acknowledged and p["rho"] is not None else None,
            "interpretation": "Exploratory registered prediction, not a confirmatory pass/fail test." if acknowledged else "No claim while interpretation choices are unresolved.",
        },
        "E21_rho_reference": {"rho": .48, "comparison": "Descriptive point estimate only; no shared-data difference test is registered."},
        "limits": ["Only 25 rows; bootstrap resamples rows, not items or W1 score uncertainty.",
                   "Constant rank vectors produce undefined correlations; no finite value is substituted.",
                   "Candidate preference common to both label classes yields D=0.5, even if one description is generally more plausible."],
    }


def _fmt(x):
    return "undefined" if x is None else f"{x:.4f}"


def report(result):
    outcome = result["prediction"]["held"]
    verdict = "held" if outcome is True else "did not hold" if outcome is False else "is not adjudicated while interpretation choices are unresolved"
    lines = ["# E25 — continuation plausibility", "",
             "Prediction: Oracle ρ(P) ≥ 0.50 with a positive CI, and content plausibility exceeds structure with a positive CI.",
             f"The exploratory prediction {verdict}.", "",
             "Dated analysis: " + result["created_at"] + ". CPU only; sealed scores verified before labels were read.", "",
             P_NOTE, "", D_NOTE, "",
             "| Predictor | Oracle ρ [95% CI] | NLA ρ [95% CI] | Probe ρ [95% CI] |", "|---|---|---|---|"]
    for name, readers in result["correlations"].items():
        cells = []
        for reader in ("olens", "nla", "probe"):
            value = readers[reader]
            ci = "undefined" if value["ci95"] is None else ", ".join(_fmt(x) for x in value["ci95"])
            cells.append(f"{_fmt(value['rho'])} [{ci}]")
        lines.append("| " + name + " | " + " | ".join(cells) + " |")
    c = result["class_plausibility_contrast"]
    lines += ["", f"Content minus structure median P: {_fmt(c['semantic_minus_structure'])}; 95% CI {c['ci95']}.",
              "The full JSON retains paired Oracle-minus-NLA/probe correlation differences and undefined bootstrap counts.",
              "E21’s ρ = 0.48 is a descriptive comparison only.", "",
              "| Row | Class | P | D | Oracle | NLA | Probe |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for r in result["rows"]:
        lines.append(f"| {r['feature']} | {r['class']} | {_fmt(r['P'])} | {_fmt(r['D'])} | {_fmt(r['W1']['olens'])} | {_fmt(r['W1']['nla'])} | {_fmt(r['W1']['probe'])} |")
    lines += ["", "Interpretation choices: " + json.dumps(result["clarifications"], sort_keys=True), ""]
    lines += ["- " + x for x in result["limits"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scores", "score-seal", "labels", "references", "plan", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise ValueError("Analysis output already exists; no overwrite or implicit rerun")
    # This ordering is intentional and tested: custody precedes label/reference reads.
    verify_scores_before_labels(args.scores, args.score_seal, args.plan)
    plan = load_json(args.plan)
    choices = plan.get("clarifications", {})
    if not (choices.get("integrator_acknowledged") is True
            and choices.get("D_definition") == "AUROC(s_A-s_B,value_is_A)"
            and choices.get("clarification_commit") == "e4225a1e"
            and choices.get("phrasing_aggregation") == "mean_of_two_W1_pairs"):
        raise ValueError("Integrator clarification acknowledgement required before real label join")
    verify_analysis_inputs(args.labels, args.references, plan)
    scores = read_jsonl(args.scores)
    labels, references = load_json(args.labels), load_json(args.references)
    result = summarize(scores, labels, references, plan)
    result["created_at"] = datetime.now(ZoneInfo("Europe/Zurich")).isoformat(timespec="seconds")
    result["provenance"] = {name: {"path": str(getattr(args, name)), "sha256": sha256(getattr(args, name))}
                            for name in ("scores", "score_seal", "labels", "references", "plan")}
    result["provenance"]["analysis_source_sha256"] = sha256(__file__)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "SUMMARY.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    (args.out / "RESULTS.md").write_text(report(result))
    files = {name: sha256(args.out / name) for name in ("SUMMARY.json", "RESULTS.md")}
    (args.out / "ANALYSIS_SEAL.json").write_text(json.dumps({"experiment": "E25", "created_at": result["created_at"], "files": files}, indent=2, sort_keys=True) + "\n")
    print("E25 sealed CPU analysis written; " + result["status"])


if __name__ == "__main__":
    main()
