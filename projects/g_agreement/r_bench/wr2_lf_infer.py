"""Pre-registered CPU inference for WR-2 label-free readouts (BRIEF_R §17).

No fitting or token selection. --self-test uses synthetic data only. The four
readouts and their source inputs must be committed/pushed before empirical use.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
import multiprocessing as mp
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from projects.g_agreement.r_bench import wr2_infer as I
import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / "cache/g_agreement/r/i2/wr2"
CACHE = ROOT / "cache/g_agreement/r/i2/wr2_lf"
RESULTS = ROOT / "results/g_agreement/r/i2"
ARMS = ("canonical_sum", "canonical_mean", "variant_sum", "variant_mean")
TAGS = ("SURFACE", "KNOWLEDGE", "TOPIC", "COMPUTED", "PASSAGE-KNOWLEDGE", "FORM", "META")
SEED, N_BOOT = 20261023, 10000
DENOMINATOR, EFFECT, LOWER = 0.174, 0.087, 0.0435
# Reuse the exact prior algorithms, in an isolated Python process. Their default
# argument n_boot remains 2000, so _stratified_weights is always passed explicitly.
I.SEED, I.N_BOOT = SEED, N_BOOT
VERSION = 1


def interval(samples: np.ndarray) -> dict:
    if samples.shape != (N_BOOT,) or not np.isfinite(samples).all():
        raise ValueError("Incomplete or invalid registered bootstrap samples")
    lo95, hi95, lo9875, hi9875 = np.quantile(samples, [.025, .975, .00625, .99375])
    return dict(lo95=float(lo95), hi95=float(hi95), lo9875=float(lo9875), hi9875=float(hi9875))


def wider(iid: dict, corpus: dict) -> dict:
    result = {}
    for level in ("95", "9875"):
        lo, hi = "lo" + level, "hi" + level
        use_corpus = corpus[hi] - corpus[lo] >= iid[hi] - iid[lo]
        chosen = corpus if use_corpus else iid
        result.update({lo: chosen[lo], hi: chosen[hi], "ci" + level + "_method": "corpus" if use_corpus else "iid"})
    return result


def verdict(estimate: float, lower: float, upper: float) -> str:
    if estimate >= EFFECT and lower > LOWER:
        return "CLOSES_NAMING_GAP"
    if upper < EFFECT:
        return "REFUTED_AT_50_PERCENT"
    return "UNDERPOWERED"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def assert_registration(commit: str, variants: Path) -> str:
    full = git("rev-parse", "--verify", commit + "^{commit}")
    brief = git("show", full + ":projects/g_agreement/BRIEF_R.md")
    if "## 17." not in brief:
        raise ValueError("Registration commit lacks BRIEF_R §17")
    rel = str(variants.relative_to(ROOT))
    frozen = subprocess.check_output(["git", "show", full + ":" + rel], cwd=ROOT)
    if frozen != variants.read_bytes():
        raise ValueError("Variants manifest differs from the committed registration")
    subprocess.run(["git", "merge-base", "--is-ancestor", full, "refs/remotes/origin/r/i2-wr2"], cwd=ROOT, check=True)
    return full


def require_population(actual: set, expected: set) -> None:
    if actual != expected:
        raise ValueError("Every registered fact is required; missing or extra facts block inference")


def validate_arrays(ids, y, native, probe, scores, arms, fact, old_arrays, inputs) -> None:
    positions = I._validate_test_join(ids, y, fact["test_ids"], inputs["ids"], inputs["y"])
    if len(ids) != len(set(ids.tolist())) or set(np.unique(y).tolist()) != {0, 1}:
        raise ValueError("Invalid unique test IDs or semantic labels")
    if list(arms) != list(ARMS) or scores.shape != (4, len(y)) or probe.shape != (5, len(y)):
        raise ValueError("Wrong readout/probe array coverage")
    if not all(np.isfinite(array).all() for array in (scores, native, probe)):
        raise ValueError("Incomplete scores cannot enter inference")
    if not np.array_equal(native, inputs["native"][positions]):
        raise ValueError("Native scores differ from frozen WR-2 inputs")
    if not np.array_equal(old_arrays["test_ids"], ids) or not np.array_equal(old_arrays["test_y"], y):
        raise ValueError("Test ID/semantic label order differs from original WR-2 predictions")
    selection, reason = I._complete_seed_rows("full_j", 256, old_arrays["fit_arm"], old_arrays["fit_n"],
                                            old_arrays["fit_seed"], old_arrays["fit_status"], old_arrays["pred_test"])
    if selection is None:
        raise ValueError("Original full-J probe is incomplete: " + reason)
    selection = selection[np.argsort(old_arrays["fit_seed"][selection])]
    if not np.array_equal(probe, old_arrays["pred_test"][selection]) or not np.array_equal(native, old_arrays["native_test"]):
        raise ValueError("Probe/native reference is not the exact frozen WR-2 prediction")


def fact_job(job: dict) -> dict:
    start, cpu = time.perf_counter(), time.process_time()
    if time.monotonic() >= job["deadline"]:
        raise RuntimeError("Registered cumulative four-core-hour budget exhausted")
    fact, info = job["fact"], job["info"]
    ds, path = fact["dataset"], Path(job["source"])
    with threadpool_limits(limits=1):
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data["metadata_json"]))
            arrays = {key: data[key].copy() for key in ("test_ids", "test_y", "native_test", "probe_test", "scores", "arms")}
        expected = {**job["expected_meta"], "dataset": ds, "tag": fact["tag"], "role": fact["role"],
                    "corpus": fact["corpus"], "source": fact["source"]}
        for key, value in expected.items():
            if meta.get(key) != value:
                raise ValueError(f"{ds}: stale or mismatched prediction metadata {key}")
        if meta.get("score_labels_used") is not False:
            raise ValueError(f"{ds}: label-free score provenance not asserted")
        fitrows = meta.get("alignment_fit_rows", [])
        if (len(fitrows) != 10 or {(row.get("kind"), row.get("seed")) for row in fitrows}
                != {(kind, seed) for kind in ("real", "shuffled") for seed in range(5)}
                or any(row.get("status") != "complete" for row in fitrows)):
            raise ValueError(f"{ds}: real/shuffled alignment probe refits incomplete")
        for row in fitrows:
            if (not np.isfinite(row.get("refit_score_max_abs_error", np.nan))
                    or row["refit_score_max_abs_error"] < 0
                    or not 0 < row.get("n_iter", 2000) < 2000
                    or not np.isfinite(row.get("raw_direction_norm", np.nan))
                    or row["raw_direction_norm"] <= 0
                    or row.get("training_draw_hash") != I._digest(fact["draws"][f'256:{row["seed"]}'])):
                raise ValueError(f"{ds}: invalid alignment parity/convergence/training-draw record")
        expected_signature = I._digest({"fact": fact, "prepared": job["prepared"],
                                        "old_predictions_sha256": meta["old_predictions_sha256"],
                                        "code_sha256": meta["code_sha256"]})
        if meta.get("signature") != expected_signature:
            raise ValueError(f"{ds}: prediction signature mismatch")
        input_path, old_path = Path(job["input_path"]), Path(job["old_path"])
        if I._hash(input_path) != fact["input_sha256"] or I._hash(old_path) != meta["old_predictions_sha256"]:
            raise ValueError(f"{ds}: original input or prediction file hash changed")
        with np.load(old_path, allow_pickle=False) as old, np.load(input_path, allow_pickle=False) as inputs:
            oldmeta = json.loads(str(old["metadata_json"]))
            I._validate_prediction_provenance(oldmeta, job["expected_old_provenance"])
            validate_arrays(arrays["test_ids"], arrays["test_y"], arrays["native_test"], arrays["probe_test"],
                            arrays["scores"], arrays["arms"], fact, old, inputs)
        y, scores = arrays["test_y"], arrays["scores"]
        weights = I._stratified_weights(y, np.random.default_rng(I._stream_seed(ds)), n_boot=N_BOOT)
        native = I._weighted_auc(arrays["native_test"], y, weights)
        probe = I._seed_mean_auc(arrays["probe_test"], y, weights)
        values = {"auc_native": native, "auc_probe": probe, "original_naming_gap": probe - native}
        permutations = [np.random.default_rng(20261024 + seed).permutation(len(y))
                        for seed in range(5)]
        for i, arm in enumerate(ARMS):
            if time.monotonic() >= job["deadline"]:
                raise RuntimeError("Registered cumulative four-core-hour budget exhausted")
            auc = I._weighted_auc(scores[i], y, weights)
            values["auc_" + arm] = auc
            values["gain_" + arm] = auc - native
            values["recovery_fraction_" + arm] = (auc - native) / DENOMINATOR
            values["remaining_gap_" + arm] = probe - auc
            shuffled = np.mean([I._weighted_auc(scores[i, permutation], y, weights) for permutation in permutations], axis=0)
            values["shuffled_state_auc_" + arm] = shuffled
            values["shuffled_state_minus_chance_" + arm] = shuffled - .5
        for agg in ("sum", "mean"):
            values["variant_increment_" + agg] = values["auc_variant_" + agg] - values["auc_canonical_" + agg]
        cells = []
        for metric, value in values.items():
            ci = interval(value[1:])
            row = {"dataset": ds, "tag": fact["tag"], "role": fact["role"], "split_corpus": fact["corpus"],
                   "n_test": len(y), "metric": metric, "status": "COMPLETE", "estimate": float(value[0]), **ci}
            if metric.startswith("gain_"):
                row.update(nominal_verdict=verdict(value[0], ci["lo95"], ci["hi95"]),
                           adjusted_verdict=verdict(value[0], ci["lo9875"], ci["hi9875"]))
            cells.append(row)
        matrix = np.stack(list(values.values()))
        metadata = {"dataset": ds, "source_sha256": I._hash(path), "signature": meta["signature"],
                    "process_cpu_seconds": time.process_time() - cpu, "wall_seconds": time.perf_counter() - start,
                    "cells": cells, "n_boot": N_BOOT, "seed": I._stream_seed(ds), "source_metadata": meta,
                    "inference_script_sha256": job["script_sha256"]}
        I._npz(Path(job["output"]), metric=np.array(list(values)), point=matrix[:, 0], boot=matrix[:, 1:],
               metadata_json=np.asarray(json.dumps(metadata, allow_nan=False)))
        return metadata


def groups(eligibility: list[dict]) -> list[dict]:
    evaluation = [row for row in eligibility if row["analysis_role"] == "evaluation"]
    calibration = [row for row in eligibility if row["analysis_role"] == "calibration"]
    return ([{"group": "primary_all", "kind": "primary", "facts": evaluation}]
            + [{"group": "primary_tag:" + tag, "kind": "primary_tag", "facts": [r for r in evaluation if r["tag"] == tag]} for tag in TAGS]
            + [{"group": "all100_sensitivity", "kind": "sensitivity", "facts": eligibility},
               {"group": "calibration12_diagnostic", "kind": "diagnostic", "facts": calibration}])


def infer(args: argparse.Namespace) -> dict:
    start, cpu = time.perf_counter(), time.process_time()
    if args.cache.resolve() != CACHE.resolve() or args.results.resolve() != RESULTS.resolve():
        raise ValueError("Outputs must remain in registered WR-2 label-free paths")
    registration = assert_registration(args.registration_commit, args.variants)
    if args.workers not in (1, 2):
        raise ValueError("Registered CPU worker count is at most two")
    timing_path = args.cache / "stage_timings.jsonl"
    prior_cpu = sum(json.loads(line)["total_cpu_s"] for line in timing_path.read_text().splitlines()) if timing_path.exists() else 0.0
    # Charge max(two workers + parent) for the entire wall stage, conservatively.
    deadline = time.monotonic() + max(0.0, (4 * 3600 - prior_cpu - 60) / 3)
    with (RESULTS / "wr2_eligibility.csv").open(newline="") as handle:
        eligibility = [row for row in csv.DictReader(handle) if I._bool(row["eligible"])]
    manifest = json.loads((OLD / "wr2_splits.json").read_text())
    if I._digest({k: v for k, v in manifest.items() if k != "manifest_hash"}) != manifest["manifest_hash"]:
        raise ValueError("Original split manifest checksum mismatch")
    if len(eligibility) != 100 or sum(r["analysis_role"] == "evaluation" for r in eligibility) != 88:
        raise ValueError("Original 100/88/12 population changed")
    facts = {fact["dataset"]: fact for fact in manifest["facts"]}
    require_population(set(facts), {r["dataset"] for r in eligibility})
    preflight_path = RESULTS / "wr2_preflight.json"
    if I._hash(preflight_path) != manifest["preflight_sha256"]:
        raise ValueError("Original preflight hash mismatch")
    preflight = json.loads(preflight_path.read_text())
    require_population(set(facts), set(preflight["eligible_fact_ids"]))
    pinned = {entry["dataset"]: entry for entry in preflight["states"]}
    for row in eligibility:
        ds, fact = row["dataset"], facts[row["dataset"]]
        for key, csv_key in (("tag", "tag"), ("role", "analysis_role"), ("corpus", "split_corpus")):
            if fact[key] != row[csv_key]:
                raise ValueError(f"{ds}: manifest/eligibility mismatch {key}")
        for kind in ("state", "index"):
            pin = pinned[ds][kind]
            expected = fact["source"][kind + "_sha256"]
            if pin["sha256"] != expected or row[kind + "_sha256"] != expected or I._hash(Path(pin["resolved_path"])) != expected:
                raise ValueError(f"{ds}: frozen {kind} bytes or provenance changed")
    sources = {ds: args.cache / "predictions" / (ds + ".npz") for ds in facts}
    require_population({ds for ds, path in sources.items() if path.exists()}, set(facts))
    geometry = {name: I._hash(OLD / "geometry" / name) for name in ("J.npy", "Q.npy", "haar384.npy", "pca384.npy", "pca_mean.npy")}
    expected_meta = {"manifest_hash": manifest["manifest_hash"], "registration_commit": registration,
                     "variants_sha256": I._hash(args.variants), "tokens_sha256": I._hash(args.tokens),
                     "code_sha256": I._hash(ROOT / "projects/g_agreement/r_bench/wr2_lf_score.py")}
    prepared = json.loads((args.cache / "prepare.json").read_text())
    for key, value in expected_meta.items():
        if prepared.get(key) != value:
            raise ValueError("Prepared inputs mismatch: " + key)
    for name, expected_hash in prepared["files"].items():
        if I._hash(args.cache / name) != expected_hash:
            raise ValueError("Prepared file changed: " + name)
    for name, expected_hash in prepared["tokenizer_files"].items():
        if I._hash(ROOT / "cache/g_agreement/s3/tok" / name) != expected_hash:
            raise ValueError("Local tokenizer source changed: " + name)
    expected_meta = prepared.copy()
    bootdir = args.cache / "inference"
    bootdir.mkdir(parents=True, exist_ok=True)
    args.results.mkdir(parents=True, exist_ok=True)
    jobs, script_sha = [], I._hash(Path(__file__))
    for row in eligibility:
        ds, fact = row["dataset"], facts[row["dataset"]]
        oldpath = OLD / "predictions" / (ds + ".npz")
        oldprovenance = {"manifest_hash": manifest["manifest_hash"], "geometry_hashes": geometry, "source": fact["source"],
                         "signature": I._digest({"fact": fact, "manifest": manifest["manifest_hash"], "geometry": geometry, "code": manifest["code_sha256"]})}
        jobs.append({"source": str(sources[ds]), "output": str(bootdir / (ds + ".npz")), "fact": fact, "info": row,
                     "expected_meta": {**expected_meta, "old_predictions_sha256": I._hash(oldpath)},
                     "expected_old_provenance": oldprovenance, "old_path": str(oldpath),
                     "input_path": str(OLD / "inputs" / (ds + ".npz")), "script_sha256": script_sha,
                     "prepared": prepared, "deadline": deadline})
    metadata = {}
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context("spawn")) as executor:
        futures = {executor.submit(fact_job, job): job["fact"]["dataset"] for job in jobs}
        for future in as_completed(futures):
            result = future.result()
            metadata[result["dataset"]] = result
            print(json.dumps({"stage": "lf_fact_bootstrap", "dataset": result["dataset"], "complete": len(metadata), "total": len(jobs)}), flush=True)
    require_population(set(metadata), set(facts))
    fact_rows = [row for ds in sorted(metadata) for row in metadata[ds]["cells"]]
    cached = {}
    for ds in sorted(metadata):
        with np.load(bootdir / (ds + ".npz"), allow_pickle=False) as arrays:
            cached[ds] = {str(metric): (float(point), boot.copy()) for metric, point, boot in zip(arrays["metric"], arrays["point"], arrays["boot"])}
    metrics = list(cached[sorted(cached)[0]])
    for ds in cached:
        require_population(set(cached[ds]), set(metrics))
    group_rows, audits, group_arrays = [], [], {}
    for group in groups(eligibility):
        if time.monotonic() >= deadline:
            raise RuntimeError("Registered cumulative four-core-hour budget exhausted")
        members = group["facts"]
        if not members:
            for arm in ARMS:
                audits.append({"group": group["group"], "kind": group["kind"], "arm": arm, "n_facts": 0, "n_corpora": 0,
                               "nominal_verdict": "NOT_EVALUATED", "adjusted_verdict": "NOT_EVALUATED"})
                group_rows.append({"group": group["group"], "group_kind": group["kind"], "metric": "gain_" + arm,
                                   "status": "NOT_EVALUATED", "estimate": None, "n_expected": 0, "n_available": 0,
                                   "n_corpora": 0, "nominal_verdict": "NOT_EVALUATED", "adjusted_verdict": "NOT_EVALUATED"})
            continue
        datasets = [r["dataset"] for r in members]
        corpora = [r["split_corpus"] for r in members]
        point = np.array([[cached[ds][metric][0] for metric in metrics] for ds in datasets])
        boot = np.array([[cached[ds][metric][1] for metric in metrics] for ds in datasets]).transpose(0, 2, 1)
        iid, corpus = I._group_bootstrap(point, boot, corpora, group["group"] + ":lf")
        estimate = np.median(point, axis=0)
        for index, metric in enumerate(metrics):
            iid_ci, corpus_ci = interval(iid[:, index]), interval(corpus[:, index])
            ci = wider(iid_ci, corpus_ci)
            row = {"group": group["group"], "group_kind": group["kind"], "metric": metric, "status": "COMPLETE",
                   "estimate": float(estimate[index]), "n_expected": len(members), "n_available": len(members),
                   "n_corpora": len(set(corpora)), "small_n_facts": len(members) < 8, "few_corpora": len(set(corpora)) < 3,
                   **{"iid_" + k: v for k, v in iid_ci.items()}, **{"corpus_" + k: v for k, v in corpus_ci.items()}, **ci}
            if metric.startswith("gain_"):
                row.update(nominal_verdict=verdict(row["estimate"], row["lo95"], row["hi95"]),
                           adjusted_verdict=verdict(row["estimate"], row["lo9875"], row["hi9875"]))
                audits.append({"group": group["group"], "kind": group["kind"], "arm": metric.removeprefix("gain_"),
                               "n_facts": len(members), "n_corpora": len(set(corpora)), "gain": row["estimate"],
                               "recovery_fraction": row["estimate"] / DENOMINATOR, **ci,
                               "nominal_verdict": row["nominal_verdict"], "adjusted_verdict": row["adjusted_verdict"]})
            group_rows.append(row)
        key = group["group"].replace(":", "_")
        group_arrays[key + "_iid"], group_arrays[key + "_corpus"] = iid, corpus
        group_arrays[key + "_metrics"] = np.array(metrics)
        print(json.dumps({"stage": "lf_group_bootstrap", "group": group["group"], "n_facts": len(members)}), flush=True)
    primary = [row for row in audits if row["group"] == "primary_all"]
    closing = [row["arm"] for row in primary if row["adjusted_verdict"] == "CLOSES_NAMING_GAP"]
    headline = "CLOSES_NAMING_GAP" if closing else ("REFUTED_AT_50_PERCENT" if all(r["adjusted_verdict"] == "REFUTED_AT_50_PERCENT" for r in primary) else "UNDERPOWERED")
    worker_cpu = sum(value["process_cpu_seconds"] for value in metadata.values())
    summary = {"status": "COMPLETE", "created_utc": datetime.now(timezone.utc).isoformat(), "version": VERSION,
               "command": sys.argv, "script_sha256": script_sha, **expected_meta, "n_facts": 100, "n_evaluation": 88,
               "n_calibration": 12, "n_boot": N_BOOT, "seed": SEED, "workers": args.workers, "gpu_hours": 0,
               "prior_stage_cpu_seconds": prior_cpu, "conservative_wall_deadline": "Remaining four-core-hour budget divided by3",
               "denominator": DENOMINATOR, "minimum_gain": EFFECT, "strict_lower_bound": LOWER,
               "nominal_rule": "Median gain>=0.087 and paired95% lower>0.0435; REFUTED_AT_50_PERCENT iff95% upper<0.087, otherwise UNDERPOWERED.",
               "adjusted_rule": "Same thresholds with four-arm Bonferroni98.75% two-sided intervals; correction within each group, not across groups.",
               "headline": headline, "headline_closing_arms": closing,
               "headline_rule": "Any primary_all arm passes adjusted rule; no minimum-fact or two-tag gate. Tags are descriptive with within-tag correction only.",
               "bootstrap_method": "10000 paired semantic-label-stratified item draws; average five separate probe seed AUROCs; group median via iid fact→item and corpus→fact→item. Each metric paired within every draw. Quote wider-width interval separately by coverage; tie to corpus.",
               "state_shuffle_control": "Five fixed within-fact score permutations seeds20261024..20261028 shared across four readouts; average their AUROCs. Labels never used to alter readout or permutation.",
               "group_verdicts": audits, "source_sha256": {ds: metadata[ds]["source_sha256"] for ds in sorted(metadata)}}
    I._write_csv(args.results / "wr2_lf_facts.csv", fact_rows)
    I._write_csv(args.results / "wr2_lf_groups.csv", group_rows)
    I._write_csv(args.results / "wr2_lf_controls.csv", [r for r in fact_rows if r["metric"].startswith("shuffled_state_")])
    I._npz(bootdir / "group_bootstraps.npz", **group_arrays)
    summary.update(wall_seconds=time.perf_counter() - start, parent_process_cpu_seconds=time.process_time() - cpu,
                   worker_process_cpu_seconds=worker_cpu, total_process_cpu_seconds=time.process_time() - cpu + worker_cpu)
    I._write_json(args.results / "wr2_lf_inference.json", summary)
    return summary


def self_test() -> None:
    from sklearn.metrics import roc_auc_score
    y = np.array([0, 0, 0, 1, 1, 1])
    scores = np.array([.1, .1, .4, .1, .7, .7])
    weights = I._stratified_weights(y, np.random.default_rng(42), n_boot=20)
    actual = I._weighted_auc(scores, y, weights)
    for i in range(len(weights)):
        assert np.isclose(actual[i], roc_auc_score(y, scores, sample_weight=weights[i]))
    assert np.array_equal(I._weighted_auc(scores, y, weights) - I._weighted_auc(scores, y, weights), np.zeros(21))
    assert np.isclose(EFFECT / DENOMINATOR, .5) and np.isclose(LOWER / DENOMINATOR, .25)
    assert verdict(.087, .0435001, .2) == "CLOSES_NAMING_GAP"
    assert verdict(.087, .0435, .2) == "UNDERPOWERED"
    assert verdict(.086999, .06, .2) == "UNDERPOWERED"
    assert verdict(.03, .01, .086999) == "REFUTED_AT_50_PERCENT"
    assert verdict(.03, .01, .087) == "UNDERPOWERED"
    points = np.array([[.1, .1], [.2, .2], [.3, .3]])
    boots = np.repeat(points[:, None, :], N_BOOT, axis=1)
    iid, corpus = I._group_bootstrap(points, boots, ["a", "b", "b"], "synthetic")
    assert np.array_equal(iid[:, 0], iid[:, 1]) and np.array_equal(corpus[:, 0], corpus[:, 1])
    ids = np.array(["a", "b", "c", "d", "e", "f"])
    old = {"test_ids": ids, "test_y": y, "native_test": scores, "pred_test": np.tile(scores, (5, 1)),
           "fit_arm": np.array(["full_j"] * 5), "fit_n": np.array([256] * 5), "fit_seed": np.arange(5), "fit_status": np.array(["complete"] * 5)}
    inputs = {"ids": ids, "y": y, "native": scores}
    validate_arrays(ids, y, scores, np.tile(scores, (5, 1)), np.tile(scores, (4, 1)), ARMS, {"test_ids": ids.tolist()}, old, inputs)
    try:
        validate_arrays(ids, y, scores, np.tile(scores + .001, (5, 1)), np.tile(scores, (4, 1)), ARMS, {"test_ids": ids.tolist()}, old, inputs)
    except ValueError:
        pass
    else:
        raise AssertionError("Changed original probe predictions accepted")
    try:
        require_population({"a"}, {"a", "b"})
    except ValueError:
        pass
    else:
        raise AssertionError("Missing registered fact accepted")
    tied = {"lo95": 0., "hi95": 1., "lo9875": 0., "hi9875": 1.}
    assert wider(tied, tied)["ci95_method"] == "corpus"
    print("Synthetic checks passed: tied weighted AUC, fixed denominator, closure boundaries, paired group sampling, exact original probe parity, missing-fact rejection, CI tie rule.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--registration-commit")
    parser.add_argument("--variants", type=Path, default=RESULTS / "wr2_lf_variants.json")
    parser.add_argument("--tokens", type=Path, default=RESULTS / "wr2_lf_tokens.json")
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif not args.registration_commit:
        parser.error("--registration-commit is required for empirical inference")
    else:
        print(json.dumps(infer(args), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
