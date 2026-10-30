"""2026-10-25 E31(i): fixed local-cue strata joined to sealed E15 scores, CPU only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[4]
SELF = "results/g_agreement/understand/e31/analyze.py"
ROWS = ["prose_paren", "prose_quote", "python_string", "python_indent", "python_depth", "list_depth", "table_role"]
ARMS = ("oracle_true", "oracle_random_donor", "nla_true_descriptive")
STRATA = ("informative", "uninformative")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def jsonl(path):
    return [json.loads(s) for s in Path(path).read_text().splitlines()]


def dump(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def verify_seal(path, expected=None):
    path = Path(path)
    if expected is not None and sha(path) != expected:
        raise ValueError("seal identity changed: " + path.name)
    seal = read(path)
    if not seal.get("files"):
        raise ValueError("empty seal")
    for name, digest in seal["files"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts or sha(path.parent / name) != digest:
            raise ValueError("sealed file changed or unsafe: " + name)
    return seal


def validate_xy(scores, labels):
    s, y = np.asarray(scores, dtype=float), np.asarray(labels)
    if s.ndim != 1 or s.shape != y.shape or not np.isfinite(s).all() or not np.isin(y, (0, 1)).all():
        raise ValueError("finite scores and matching binary labels required")
    return s, y.astype(int)


def auc(scores, labels):
    s, y = validate_xy(scores, labels)
    n1, n0 = int(y.sum()), int((1-y).sum())
    if not n1 or not n0:
        return None
    return float((rankdata(s, method="average")[y == 1].sum() - n1*(n1+1)/2) / (n1*n0))


def bootstrap_auc(scores, labels, indices):
    s, y = validate_xy(scores, labels)
    ix = np.asarray(indices)
    if ix.ndim != 2 or ix.shape[1] != len(s) or not np.issubdtype(ix.dtype, np.integer) or ix.min() < 0 or ix.max() >= len(s):
        raise ValueError("full-size valid bootstrap index matrix required")
    sampled, target = s[ix], y[ix]
    n1, n0 = target.sum(1), len(s)-target.sum(1)
    numerator = (rankdata(sampled, axis=1, method="average")*target).sum(1)-n1*(n1+1)/2
    return np.divide(numerator, n1*n0, out=np.full(len(ix), np.nan), where=(n1*n0)>0)


def interval(samples):
    samples = np.asarray(samples)
    finite = samples[np.isfinite(samples)]
    return {"ci95": [float(x) for x in np.quantile(finite, [.025, .975], method="linear")] if len(finite) else None,
            "attempted_bootstrap_draws": len(samples), "finite_bootstrap_draws": len(finite),
            "undefined_bootstrap_draws": len(samples)-len(finite)}


def analyze_stratum(y, scores, rng, n_boot):
    y = np.asarray(y, dtype=int)
    result = {"n": len(y), "n_A": int(y.sum()), "n_B": int((1-y).sum()), "arms": {}}
    if not len(y) or len(np.unique(y)) != 2:
        result.update(status="NOT_EVALUABLE", reason="EMPTY_STRATUM" if not len(y) else "SINGLE_CLASS_STRATUM")
        for arm in ARMS:
            result["arms"][arm] = {"status": "NOT_EVALUABLE", "auroc": None, **interval([])}
        result["oracle_true_minus_random_donor"] = {"status": "NOT_EVALUABLE", "difference": None, **interval([])}
        return result, None
    result["status"] = "EVALUABLE"
    indices = rng.integers(0, len(y), size=(n_boot, len(y)))
    draws = {}
    for arm in ARMS:
        draws[arm] = bootstrap_auc(scores[arm], y, indices)
        result["arms"][arm] = {"status": "EVALUABLE", "auroc": auc(scores[arm], y), **interval(draws[arm])}
    result["bootstrap_indices_sha256"] = hashlib.sha256(indices.astype("<i8").tobytes()).hexdigest()
    result["oracle_true_minus_random_donor"] = {
        "status": "EVALUABLE", "difference": result["arms"]["oracle_true"]["auroc"]-result["arms"]["oracle_random_donor"]["auroc"],
        **interval(draws["oracle_true"]-draws["oracle_random_donor"])}
    return result, draws["oracle_true"]


def analyze_row(feature, records, cutoff, rng, n_boot):
    result = {"feature": feature, "dev_frozen_cutoff": cutoff, "informative_operator": ">", "strata": {}}
    draws = {}
    for stratum in STRATA:
        selected = [r for r in records if r["stratum"] == stratum]
        result["strata"][stratum], draws[stratum] = analyze_stratum(
            [r["label"] for r in selected], {arm: [r[arm] for r in selected] for arm in ARMS}, rng, n_boot)
    eligible = all(result["strata"][s]["status"] == "EVALUABLE" for s in STRATA)
    info, uninfo = (result["strata"][s]["arms"]["oracle_true"]["auroc"] for s in STRATA)
    result["predictions"] = {"status": "EVALUABLE" if eligible else "NOT_EVALUABLE",
                             "local_cue_info_ge075_and_uninfo_le060": bool(info >= .75 and uninfo <= .60) if eligible else None,
                             "remote_state_both_ge070": bool(info >= .70 and uninfo >= .70) if eligible else None,
                             "point_rules_only": True}
    result["informative_minus_uninformative_oracle"] = {
        "status": "EVALUABLE" if eligible else "NOT_EVALUABLE", "difference": info-uninfo if eligible else None,
        **interval(draws["informative"]-draws["uninformative"] if eligible else [])}
    return result


def exclusive_start(out, identity):
    out = Path(out)
    if out.exists():
        raise ValueError("analysis output exists; no overwrite or rerun")
    out.parent.mkdir(parents=True, exist_ok=True)
    lock = out.with_name(out.name + ".lock.json")
    dump(lock, identity)
    out.mkdir(exist_ok=False)
    dump(out / "STARTED.json", identity)


def verify_frozen_cutoffs(strata, cutoffs, protocol):
    if (cutoffs.get("suffix_slice") != protocol["suffix_slice"]
            or cutoffs.get("method") != "dev_median_abs_probability_margin"
            or cutoffs.get("informative_operator") != ">" or cutoffs.get("margin_formula") != "abs(p_A-p_B)"):
        raise ValueError("frozen suffix and strict dev-median confidence cutoff required")
    cutoffmap = {r["feature"]: r["cutoff"] for r in cutoffs["rows"]}
    if len(cutoffs["rows"]) != 7 or set(cutoffmap) != set(ROWS):
        raise ValueError("seven frozen cutoffs required")
    if len(strata) != 1176 or len({r["id"] for r in strata}) != 1176:
        raise ValueError("complete unique seven-row dev/test strata required")
    for r in strata:
        if r["feature"] not in ROWS or r["split"] not in ("dev", "test") or not math.isfinite(r["p_A"]) or not 0 <= r["p_A"] <= 1:
            raise ValueError("invalid frozen stratum identity/probability")
        if not math.isclose(r["margin"], abs(2*r["p_A"]-1), abs_tol=1e-12, rel_tol=0):
            raise ValueError("invalid frozen probability margin")
    for feature, cutoff in cutoffmap.items():
        dev = [r["margin"] for r in strata if r["feature"] == feature and r["split"] == "dev"]
        if len(dev) != 84 or sum(r["feature"] == feature and r["split"] == "test" for r in strata) != 84:
            raise ValueError("84 frozen dev and test items per row required")
        # Integrity check only: retain the saved cutoff, never refit or substitute it.
        if not math.isfinite(cutoff) or not math.isclose(cutoff, float(np.median(dev)), rel_tol=0, abs_tol=1e-12):
            raise ValueError("saved cutoff does not match frozen dev-margin median")
    if any(r["stratum"] != ("informative" if r["margin"] > cutoffmap[r["feature"]] else "uninformative") for r in strata):
        raise ValueError("stratum differs from strict frozen cutoff")


def verify_inputs(a):
    p = read(a.protocol)
    if p.get("experiment") != "E31" or p.get("status") != "READY" or p.get("rows") != ROWS or p.get("bootstrap") != 2000 or p.get("seed") != 20261025:
        raise ValueError("exact ready E31 protocol required")
    if p.get("suffix_slice") not in ("include_read", "exclude_read") or p.get("source_files", {}).get(SELF) != sha(__file__):
        raise ValueError("suffix convention and current analysis source must be frozen")
    for name, digest in p["source_files"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts or sha(ROOT/name) != digest:
            raise ValueError("protocol source mismatch")
    freeze = verify_seal(a.freeze)
    required = {"protocol.json", "cache/models.json", "cache/strata.jsonl", "DEV_CUTOFFS.json", "PROVENANCE.json"}
    if (freeze.get("complete") is not True or freeze.get("status") != "E31_STRATA_FROZEN_BEFORE_E15_OUTCOME_JOIN" or not required <= set(freeze["files"])
            or freeze.get("protocol_sha256") != sha(a.protocol) or freeze.get("source_files") != p["source_files"]
            or freeze["files"]["protocol.json"] != sha(a.protocol)):
        raise ValueError("complete matching pre-outcome strata freeze required")
    provenance = read(a.freeze.parent/"PROVENANCE.json")
    if provenance.get("protocol_sha256") != sha(a.protocol) or provenance.get("source_files") != p["source_files"]:
        raise ValueError("strata provenance mismatch")
    for field in ("test_labels_used_for_cutoff", "continuation_scores_accessed"):
        if field not in provenance or provenance[field] is not False:
            raise ValueError("strata preparation accessed forbidden outcomes")
    cutoffs = read(a.freeze.parent/"DEV_CUTOFFS.json")
    strata = jsonl(a.freeze.parent/"cache/strata.jsonl")
    verify_frozen_cutoffs(strata, cutoffs, p)
    verify_seal(a.e15_stage/"INPUT_SEAL.json", p["e15_input_seal_sha256"])
    verify_seal(a.e15_scores/"SCORE_SEAL.json", p["e15_score_seal_sha256"])
    verify_seal(a.e15_metrics.parent/"ANALYSIS_SEAL.json", p["e15_metrics_seal_sha256"])
    for path, key in ((a.e15_stage/"plan.json", "e15_plan_sha256"), (a.e15_scores/"scores.jsonl", "e15_scores_sha256"),
                      (a.e15_labels, "e15_labels_sha256"), (a.e15_metrics, "e15_metrics_sha256")):
        if sha(path) != p[key]:
            raise ValueError("frozen E15 source identity mismatch: " + key)
    plan, origin = read(a.e15_stage/"plan.json"), read(a.e15_scores/"provenance.json")
    if origin["input_seal_sha256"] != p["e15_input_seal_sha256"] or origin["source_files"] != plan["source_files"] or plan["labels_sha256"] != p["e15_labels_sha256"]:
        raise ValueError("E15 input/source/label lineage mismatch")
    return p, plan, cutoffs, strata


def join_scores(a, p, plan, cutoffs, strata):
    # This is the first raw E15 outcome read, after every input/source seal and STARTED lock.
    raw = jsonl(a.e15_scores/"scores.jsonl")
    test, dev = jsonl(a.e15_stage/"items.input.jsonl"), jsonl(a.e15_stage/"reference.input.jsonl")
    expected = {(r["id"], "base", "true") for r in dev} | {(r["id"], reader, arm) for r in test for reader in ("olens", "nla") for arm in ("true", "random_donor", "w1_mismatched")}
    scoremap = {(r["id"], r["reader"], r["arm"]): r for r in raw}
    if len(raw) != 4704 or len(scoremap) != 4704 or set(scoremap) != expected:
        raise ValueError("complete original 4704-record E15 grid required")
    itemmap = {r["id"]: r for r in test+dev}
    for r in raw:
        layer = None if r["reader"] == "base" else 44 if r["reader"] == "olens" else 42
        if r.get("status") != "COMPLETE" or len(r["scores"]) != 2 or not np.isfinite(r["scores"]).all() or r["feature"] != itemmap[r["id"]]["feature"] or r["layer"] != layer:
            raise ValueError("invalid E15 score record")
    labelrows = jsonl(a.e15_labels)
    labels = {r["id"]: r for r in labelrows}
    if len(labels) != len(labelrows) or set(labels) != set(itemmap):
        raise ValueError("E15 label coverage mismatch")
    selected_ids = {r["id"] for r in test+dev if r["feature"] in ROWS}
    if len(strata) != 1176 or len({r["id"] for r in strata}) != 1176 or {r["id"] for r in strata} != selected_ids:
        raise ValueError("complete seven-row dev/test strata required")
    cutoffmap = {r["feature"]: r["cutoff"] for r in cutoffs["rows"]}
    for r in strata:
        truth = labels[r["id"]]
        expected_y = int(truth["value"] == plan["values"][r["feature"]][0])
        if any(r[k] != truth[k] for k in ("feature", "split", "value")) or r["label"] != expected_y:
            raise ValueError("strata/E15 label orientation mismatch")
    metrics = read(a.e15_metrics)
    if metrics["score_seal_sha256"] != p["e15_score_seal_sha256"] or metrics["labels_sha256"] != p["e15_labels_sha256"]:
        raise ValueError("E15 metrics lineage mismatch")
    published = {r["feature"]: r for r in metrics["rows"]}
    ledger, parity = [], []
    for feature in ROWS:
        old = published[feature]
        if old["valid_pairs"] != [0, 1] or old["status"] != "EVALUABLE":
            raise ValueError("use existing valid pairs only; never reselect")
        for split in ("dev", "test"):
            if sum(r["feature"] == feature and r["split"] == split for r in strata) != 84:
                raise ValueError("84 dev and 84 test items per row required")
        rowledger = [dict(r) for r in strata if r["feature"] == feature and r["split"] == "test"]
        for r in rowledger:
            for arm, reader, source_arm in (("oracle_true", "olens", "true"), ("oracle_random_donor", "olens", "random_donor"), ("nla_true_descriptive", "nla", "true")):
                r[arm] = float(np.asarray(scoremap[r["id"], reader, source_arm]["scores"], float)[old["valid_pairs"]].mean())
        for arm, reader, source_arm in (("oracle_true", "olens", "true"), ("oracle_random_donor", "olens", "random_donor"), ("nla_true_descriptive", "nla", "true")):
            point = auc([r[arm] for r in rowledger], [r["label"] for r in rowledger])
            prior = old["readers"][reader]["arms"][source_arm]["auroc"]
            if point is None or not math.isclose(point, prior, rel_tol=0, abs_tol=1e-12):
                raise ValueError("full-test E15 point parity failed")
            parity.append({"feature": feature, "arm": arm, "auroc": point, "sealed_e15_auroc": prior, "absolute_difference": abs(point-prior)})
        ledger.extend(rowledger)
    return ledger, parity, cutoffmap


def report(result):
    lines = ["# E31(i) — CPU local-cue stratification, 25 October 2026", "", "Prediction (local cue): Oracle continuation AUROC ≥0.75 in the informative stratum and ≤0.60 in the uninformative stratum. Prediction (remote state): both ≥0.70. These are per-row point rules; no global verdict or pooling is introduced.", "", "| Row | Dev cutoff | Informative n (A/B) | Oracle AUROC [95% CI] | Uninformative n (A/B) | Oracle AUROC [95% CI] | Local cue / remote |", "|---|---:|---:|---|---:|---|---|"]
    def show(arm):
        return "NOT EVALUABLE" if arm["auroc"] is None else f"{arm['auroc']:.4f} [{arm['ci95'][0]:.4f}, {arm['ci95'][1]:.4f}]" if arm["ci95"] else f"{arm['auroc']:.4f} [CI undefined]"
    for r in result["rows"]:
        i, u, pred = r["strata"]["informative"], r["strata"]["uninformative"], r["predictions"]
        flags = "NOT EVALUABLE" if pred["status"] != "EVALUABLE" else f"{pred['local_cue_info_ge075_and_uninfo_le060']} / {pred['remote_state_both_ge070']}"
        lines.append(f"| {r['feature']} | {r['dev_frozen_cutoff']:.6g} | {i['n']} ({i['n_A']}/{i['n_B']}) | {show(i['arms']['oracle_true'])} | {u['n']} ({u['n_A']}/{u['n_B']}) | {show(u['arms']['oracle_true'])} | {flags} |")
    summary = result["descriptive_counts"]
    lines += ["", f"Descriptive counts among {summary['evaluable_rows']} rows with both strata evaluable: local-cue point pattern {summary['local_cue_rows']}; remote-state point pattern {summary['remote_state_rows']}. {summary['not_evaluable_rows']} rows lack two evaluable strata. No across-row success criterion is specified.", "", "Strata, models and thresholds were frozen before raw E15 outcome access. The dev cutoff is the median absolute probability margin |p_A−p_B|; informative means strictly greater than the cutoff, so ties are uninformative. Suffix convention: `"+result["suffix_slice"]+"`. No classifier, cutoff, valid pair or score sign was refitted/changed during this analysis.", "", "All 21 full-test Oracle true/random and NLA true AUROCs reproduce sealed E15 values within 1e-12. E15 uses summed candidate-token log-probability differences, averaged over its two previously valid continuation pairs, with value-A positive. E25's token normalization is not applied.", "", "Within each stratum, 2,000 iid item bootstrap resamples share indices across Oracle true, Oracle random-donor and descriptive NLA arms. The true-minus-random contrast is paired. Informative-minus-uninformative contrasts combine independent within-stratum resamples by replicate index. Confidence intervals condition on the frozen classifier, cutoff and stratum assignments; they do not include fitting uncertainty. Empty/single-class strata and undefined one-class draws are reported explicitly; they are never assigned AUROC0.5.", "", "## Oracle controls and stratum contrasts", "", "| Row | Stratum | Random-donor AUROC [95% CI] | True − random [95% CI] |", "|---|---|---|---|"]
    for r in result["rows"]:
        for name, s in r["strata"].items():
            d = s["oracle_true_minus_random_donor"]
            delta = "NOT EVALUABLE" if d["difference"] is None else f"{d['difference']:.4f}; CI {d['ci95']}"
            lines.append(f"| {r['feature']} | {name} | {show(s['arms']['oracle_random_donor'])} | {delta} |")
        d = r["informative_minus_uninformative_oracle"]
        lines.append(f"| {r['feature']} | informative − uninformative | Oracle true contrast | {d['difference']} ; CI {d['ci95']} |")
    lines += ["", "## Descriptive NLA appendix", "", "NLA continuation scoring is off its native explanation format and is descriptive only.", "", "| Row | Informative AUROC [95% CI] | Uninformative AUROC [95% CI] |", "|---|---|---|"]
    lines.extend(f"| {r['feature']} | {show(r['strata']['informative']['arms']['nla_true_descriptive'])} | {show(r['strata']['uninformative']['arms']['nla_true_descriptive'])} |" for r in result["rows"])
    return "\n".join(lines)+"\n"


def run(a):
    start = time.monotonic()
    p, plan, cutoffs, strata = verify_inputs(a)
    identity = {"date": datetime.now(timezone.utc).isoformat(), "status": "STARTED_BEFORE_RAW_E15_OUTCOME_READ", "protocol_sha256": sha(a.protocol), "strata_seal_sha256": sha(a.freeze), "analysis_source_sha256": sha(__file__), "e15_score_seal_sha256": p["e15_score_seal_sha256"]}
    exclusive_start(a.out, identity)
    ledger, parity, cutoffmap = join_scores(a, p, plan, cutoffs, strata)
    rng = np.random.default_rng(p["seed"])
    result = {"date": "2026-10-25", "experiment": "E31", "part": "i", "status": "DESCRIPTIVE_COMPLETE", "suffix_slice": p["suffix_slice"], "seed": p["seed"], "bootstrap": p["bootstrap"], "global_verdict": "NOT_DEFINED_BY_REGISTRATION", "rows": [analyze_row(f, [r for r in ledger if r["feature"] == f], cutoffmap[f], rng, p["bootstrap"]) for f in ROWS]}
    flags = [r["predictions"] for r in result["rows"]]
    result["descriptive_counts"] = {"evaluable_rows": sum(f["status"] == "EVALUABLE" for f in flags), "not_evaluable_rows": sum(f["status"] != "EVALUABLE" for f in flags), "local_cue_rows": sum(f["local_cue_info_ge075_and_uninfo_le060"] is True for f in flags), "remote_state_rows": sum(f["remote_state_both_ge070"] is True for f in flags)}
    (a.out/"cache").mkdir()
    (a.out/"cache/ledger.jsonl").write_text("".join(json.dumps(r, sort_keys=True, allow_nan=False)+"\n" for r in ledger))
    dump(a.out/"METRICS.json", result)
    dump(a.out/"PARITY.json", {"checks": parity, "passed": len(parity), "tolerance": 1e-12})
    (a.out/"RESULTS.md").write_text(report(result))
    dump(a.out/"RUN.json", {"wall_seconds": time.monotonic()-start, "GPU_hours": 0, "API_cost_USD": 0, "new_model_fits": 0, "cutoff_refits": 0, "E31_ii": "NOT_RUN", "registered_analysis_invocations": 1})
    names = ("STARTED.json", "METRICS.json", "PARITY.json", "RESULTS.md", "RUN.json", "cache/ledger.jsonl")
    dump(a.out/"ANALYSIS_SEAL.json", {"complete": True, "status": "E31_CPU_STRATIFIED_ANALYSIS_SEALED", "protocol_sha256": sha(a.protocol), "strata_seal_sha256": sha(a.freeze), "source_files": p["source_files"], "files": {n: sha(a.out/n) for n in names}})
    return {"status": result["status"], "full_test_parity_checks": len(parity), "seal_sha256": sha(a.out/"ANALYSIS_SEAL.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "freeze", "e15-stage", "e15-scores", "e15-labels", "e15-metrics", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    print(json.dumps(run(parser.parse_args()), sort_keys=True))
