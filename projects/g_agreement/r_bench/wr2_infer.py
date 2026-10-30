"""Paired CPU inference for the pushed BRIEF_R §16 WR-2 registration.

Run only after all registered fit caches are ready. No fitting, selection,
polarity repair or model execution occurs here. --self-test uses synthetic data.
"""
from __future__ import annotations

import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
from typing import Any
import warnings

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[3]
CACHE_ROOT = ROOT / "cache" / "g_agreement" / "r" / "i2" / "wr2"
RESULT_ROOT = ROOT / "results" / "g_agreement" / "r" / "i2"
SEED, N_BOOT = 20261019, 2000
BUDGETS, SEEDS = (16, 64, 256, 512), (0, 1, 2, 3, 4)
PRIMARY = ("h", "full_j", "p384", "complement", "haar384", "pca384")
SECONDARY = ("h_unit", "full_j_unit", "h_massmean", "full_j_massmean", "h_shuffle", "full_j_shuffle")
CONTRASTS = {
    "map_loss": ("auc_h", "auc_full_j"),
    "naming_loss": ("auc_full_j", "auc_native"),
    "truncation_loss": ("auc_full_j", "auc_p384"),
    "haar_loss": ("auc_full_j", "auc_haar384"),
    "excess_truncation_loss": ("auc_haar384", "auc_p384"),
}
CONTROL_CONTRASTS = {
    "h_unit_minus_h": ("auc_h_unit", "auc_h"),
    "full_j_unit_minus_full_j": ("auc_full_j_unit", "auc_full_j"),
    "h_massmean_minus_h": ("auc_h_massmean", "auc_h"),
    "full_j_massmean_minus_full_j": ("auc_full_j_massmean", "auc_full_j"),
    "h_shuffle_minus_chance": ("auc_h_shuffle", None),
    "full_j_shuffle_minus_chance": ("auc_full_j_shuffle", None),
}
VERSION = 1


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _validate_prediction_provenance(meta: dict, expected: dict) -> None:
    for key in ("manifest_hash", "geometry_hashes", "source", "signature"):
        if meta.get(key) != expected[key]:
            raise ValueError(f"{meta.get('dataset', 'unknown')}: stale or mixed prediction {key}")


def _validate_test_join(ids: np.ndarray, labels: np.ndarray, expected_ids: list[str],
                        input_ids: np.ndarray, input_labels: np.ndarray) -> np.ndarray:
    if ids.tolist() != expected_ids:
        raise ValueError("Ordered prediction test IDs differ from frozen split manifest")
    lookup = {iid: i for i, iid in enumerate(input_ids.tolist())}
    if len(lookup) != len(input_ids):
        raise ValueError("Duplicate frozen input IDs")
    try:
        positions = np.array([lookup[iid] for iid in expected_ids], dtype=np.int64)
    except KeyError as error:
        raise ValueError("Prediction test ID absent from frozen inputs") from error
    if not np.array_equal(labels, input_labels[positions]):
        raise ValueError("Prediction labels differ from frozen semantic input labels")
    return positions


def _stream_seed(label: str) -> int:
    return SEED + int.from_bytes(hashlib.sha256(label.encode()).digest()[:4], "big")


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in ("true", "1")


def _write_json(path: Path, data: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    columns = list(dict.fromkeys(k for row in rows for k in row))
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _npz(path: Path, **values: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **values)
    temporary.replace(path)


def _interval(values: np.ndarray) -> dict[str, float | None]:
    if not np.isfinite(values).all() or len(values) != N_BOOT:
        return {key: None for key in ("lo95", "hi95", "lo90", "hi90")}
    quantiles = np.percentile(values, [2.5, 97.5, 5, 95])
    return dict(zip(("lo95", "hi95", "lo90", "hi90"), map(float, quantiles)))


def _stratified_weights(y: np.ndarray, rng: np.random.Generator, n_boot: int = N_BOOT) -> np.ndarray:
    """Row zero is the empirical sample; later rows are paired label-stratified draws."""
    weights = np.zeros((n_boot + 1, len(y)), dtype=np.int16)
    weights[0] = 1
    for label in (0, 1):
        positions = np.flatnonzero(y == label)
        if len(positions) == 0:
            raise ValueError("Both semantic labels are required for AUROC")
        draws = rng.integers(len(positions), size=(n_boot, len(positions)))
        offsets = np.arange(n_boot)[:, None] * len(positions)
        counts = np.bincount((draws + offsets).ravel(), minlength=n_boot * len(positions))
        weights[1:, positions] = counts.reshape(n_boot, len(positions))
    return weights


def _weighted_auc(scores: np.ndarray, y: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Exact tied-score AUROC for every bootstrap sample using weighted rank sums.

    The same weights are reused for every arm, budget and seed. This avoids
    thousands of sklearn calls without averaging prediction scores across seeds.
    """
    if not np.isfinite(scores).all():
        raise ValueError("Nonfinite prediction scores may not enter AUROC")
    order = np.argsort(scores, kind="stable")
    values, labels = scores[order], y[order]
    starts = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1]
    ordered = weights[:, order]
    negative = np.add.reduceat(ordered * (labels == 0)[None, :], starts, axis=1)
    positive = np.add.reduceat(ordered * (labels == 1)[None, :], starts, axis=1)
    negative_below = np.cumsum(negative, axis=1) - 0.5 * negative
    denominator = np.sum(negative, axis=1) * np.sum(positive, axis=1)
    return np.sum(positive * negative_below, axis=1) / denominator


def _seed_mean_auc(predictions: np.ndarray, y: np.ndarray, weights: np.ndarray) -> np.ndarray:
    # Each seed earns its own AUC before averaging: mean AUC != AUC(mean score).
    return np.mean([_weighted_auc(scores, y, weights) for scores in predictions], axis=0)


def _complete_seed_rows(arm: str, n: int, arms: np.ndarray, budgets: np.ndarray,
                        seeds: np.ndarray, statuses: np.ndarray, predictions: np.ndarray) -> tuple[np.ndarray | None, str]:
    selection = np.flatnonzero((arms == arm) & (budgets == n))
    if len(selection) != len(SEEDS) or set(seeds[selection]) != set(SEEDS):
        return None, "missing_or_duplicate_registered_seed"
    selection = selection[np.argsort(seeds[selection])]
    if not np.all(statuses[selection] == "complete"):
        return None, "noncomplete_fit_status:" + ";".join(sorted(set(statuses[selection].tolist())))
    if not np.isfinite(predictions[selection]).all():
        return None, "nonfinite_completed_fit_predictions"
    return selection, ""


def _fact_job(job: dict) -> dict:
    start, cpu_start = time.perf_counter(), time.process_time()
    source, output = Path(job["source"]), Path(job["output"])
    info = job["eligibility"]
    ds = info["dataset"]
    with threadpool_limits(limits=1):
        with np.load(source, allow_pickle=False) as fit:
            meta = json.loads(str(fit["metadata_json"]))
            _validate_prediction_provenance(meta, job["expected_provenance"])
            if meta["dataset"] != ds or meta["tag"] != info["tag"] or meta["role"] != info["analysis_role"]:
                raise ValueError(f"{ds}: prediction metadata does not match frozen eligibility")
            if meta["corpus"] != info["split_corpus"]:
                raise ValueError(f"{ds}: prediction corpus differs from registered unioned source corpus")
            y, ids = fit["test_y"].copy(), fit["test_ids"].copy()
            pred, arms, budgets = fit["pred_test"].copy(), fit["fit_arm"].copy(), fit["fit_n"].copy()
            seeds, statuses = fit["fit_seed"].copy(), fit["fit_status"].copy()
            native, prompt = fit["native_test"].copy(), fit["prompt_only_test"].copy()
        input_path = Path(job["expected_input_path"])
        if _hash(input_path) != job["expected_input_sha256"]:
            raise ValueError(f"{ds}: frozen score/label input bytes changed")
        with np.load(input_path, allow_pickle=False) as inputs:
            positions = _validate_test_join(ids, y, job["expected_test_ids"], inputs["ids"], inputs["y"])
            if not np.array_equal(native, inputs["native"][positions], equal_nan=True):
                raise ValueError(f"{ds}: native prediction-cache scores differ from frozen inputs")
            if not np.array_equal(prompt, inputs["prompt_only"][positions], equal_nan=True):
                raise ValueError(f"{ds}: prompt-only prediction-cache scores differ from frozen inputs")
        if len(ids) != len(set(ids.tolist())) or pred.shape != (len(arms), len(y)):
            raise ValueError(f"{ds}: invalid prediction/test-ID layout")
        removed = [s for s in info.get("calibration_diagnostic_excluded_item_ids", "").split(";") if s]
        expected_n = int(info["n_test"]) - len(removed)
        if len(y) != expected_n or any(i in set(ids.tolist()) for i in removed):
            raise ValueError(f"{ds}: test coverage or registered duplicate removal differs")
        if set(np.unique(y).tolist()) != {0, 1} or not np.isfinite(native).all():
            raise ValueError(f"{ds}: invalid semantic labels or incomplete native scores")
        weights = _stratified_weights(y, np.random.default_rng(_stream_seed(ds)))
        values: dict[tuple[int, str], np.ndarray] = {}
        cells: list[dict] = []

        def cell(n: int, metric: str, value: np.ndarray | None, status: str, reason: str = "", n_seeds: int = 5) -> None:
            row = {"dataset": ds, "tag": info["tag"], "role": info["analysis_role"],
                   "split_corpus": info["split_corpus"], "r5_subset": _bool(info["r5_subset"]),
                   "n": n, "metric": metric, "status": status, "reason": reason,
                   "n_test": len(y), "n_seeds": n_seeds, "estimate": None,
                   "lo95": None, "hi95": None, "lo90": None, "hi90": None}
            if value is not None:
                if not np.isfinite(value).all() or value.shape != (N_BOOT + 1,):
                    raise ValueError(f"{ds}/{n}/{metric}: invalid bootstrap output")
                values[n, metric] = value
                row.update(estimate=float(value[0]), **_interval(value[1:]))
            cells.append(row)

        native_auc = _weighted_auc(native, y, weights)
        prompt_auc = _weighted_auc(prompt, y, weights) if np.isfinite(prompt).all() else None
        for n in BUDGETS:
            missing_budget = n == 512
            for arm in PRIMARY + (SECONDARY if n == 256 else ()):
                selected, reason = _complete_seed_rows(arm, n, arms, budgets, seeds, statuses, pred)
                if missing_budget:
                    if selected is not None:
                        raise ValueError(f"{ds}: n512 was registered missing but complete predictions were supplied")
                    cell(n, "auc_" + arm, None, "MISSING", "insufficient_training_after_reserved64")
                elif selected is None:
                    cell(n, "auc_" + arm, None, "INCOMPLETE", reason)
                else:
                    cell(n, "auc_" + arm, _seed_mean_auc(pred[selected], y, weights), "COMPLETE")
            # Native/prompt are untrained references; duplicated rows make paired budget joins explicit.
            cell(n, "auc_native", native_auc, "COMPLETE", n_seeds=1)
            cell(n, "auc_prompt_only", prompt_auc, "COMPLETE" if prompt_auc is not None else "MISSING",
                 "" if prompt_auc is not None else "prompt_only_not_completely_joined", n_seeds=1)
            for metric, (left, right) in CONTRASTS.items():
                if (n, left) in values and (n, right) in values:
                    cell(n, metric, values[n, left] - values[n, right], "COMPLETE")
                else:
                    cell(n, metric, None, "MISSING" if missing_budget else "INCOMPLETE", "required_paired_arm_incomplete")
            if n == 256:
                for metric, (left, right) in CONTROL_CONTRASTS.items():
                    if (n, left) in values and (right is None or (n, right) in values):
                        comparison = 0.5 if right is None else values[n, right]
                        cell(n, metric, values[n, left] - comparison, "COMPLETE")
                    else:
                        cell(n, metric, None, "INCOMPLETE", "required_control_arm_incomplete")
        keys = list(values)
        matrix = np.stack([values[key] for key in keys])
        metadata = {"dataset": ds, "source_sha256": _hash(source), "eligibility": info,
                    "fit_signature": meta["signature"], "manifest_hash": meta["manifest_hash"],
                    "script_sha256": job["script_sha256"], "version": VERSION,
                    "seed": _stream_seed(ds), "n_boot": N_BOOT,
                    "process_cpu_seconds": time.process_time() - cpu_start,
                    "wall_seconds": time.perf_counter() - start, "cells": cells}
        _npz(output, cell_n=np.array([key[0] for key in keys]), cell_metric=np.array([key[1] for key in keys]),
             point=matrix[:, 0], boot=matrix[:, 1:], metadata_json=np.asarray(json.dumps(metadata, allow_nan=False)))
    return metadata


def _wider(iid: dict, corpus: dict) -> dict:
    out: dict[str, Any] = {}
    for level in (95, 90):
        lo, hi = f"lo{level}", f"hi{level}"
        if iid[lo] is None or corpus[lo] is None:
            out.update({lo: None, hi: None, f"ci{level}_method": "unavailable"})
            continue
        # A tie goes to the corpus interval. This is width selection, not an envelope.
        use_corpus = corpus[hi] - corpus[lo] >= iid[hi] - iid[lo]
        chosen = corpus if use_corpus else iid
        out.update({lo: chosen[lo], hi: chosen[hi], f"ci{level}_method": "corpus" if use_corpus else "iid"})
    return out


def _map_equivalent(row: dict) -> bool:
    return (row.get("status") == "COMPLETE" and row.get("lo90") is not None
            and row["lo90"] > -0.03 and row["hi90"] < 0.03)


def _verdicts(rows: dict[str, dict], n: int, count: int, minimum: int) -> dict[str, str]:
    result = {"map_verdict": "UNDERPOWERED", "naming_verdict": "UNDERPOWERED",
              "truncation_verdict": "UNDERPOWERED", "naming_failed_clauses": "", "truncation_failed_clauses": ""}
    if n != 256:
        result.update(map_verdict="NOT_PRIMARY_BUDGET", naming_verdict="NOT_PRIMARY_BUDGET",
                      truncation_verdict="NOT_PRIMARY_BUDGET")
        if n == 512:
            result.update(map_verdict="MISSING", naming_verdict="MISSING", truncation_verdict="MISSING")
        return result
    if count < minimum:
        result.update(naming_failed_clauses=f"fewer_than_{minimum}_registered_facts",
                      truncation_failed_clauses=f"fewer_than_{minimum}_registered_facts")
        return result
    mapping, naming = rows["map_loss"], rows["naming_loss"]
    truncation, excess = rows["truncation_loss"], rows["excess_truncation_loss"]
    if _map_equivalent(mapping):
        result["map_verdict"] = "EQUIVALENT-NULL"
    nfail = []
    if naming["status"] != "COMPLETE" or mapping["status"] != "COMPLETE":
        nfail.append("incomplete_registered_fact_or_seed_population")
    else:
        if naming["estimate"] < 0.15:
            nfail.append("naming_median_below_0.15")
        if naming["lo95"] <= 0.10:
            nfail.append("naming_lower95_not_above_0.10")
        if not _map_equivalent(mapping):
            nfail.append("map_90CI_not_strictly_inside_plusminus0.03")
        if not nfail:
            result["naming_verdict"] = "SUPPORTED"
        elif naming["hi95"] < 0.15:
            result["naming_verdict"] = "REFUTED"
    tfail = []
    if truncation["status"] != "COMPLETE" or excess["status"] != "COMPLETE":
        tfail.append("incomplete_registered_fact_or_seed_population")
    else:
        if truncation["estimate"] < 0.10:
            tfail.append("truncation_median_below_0.10")
        if truncation["lo95"] <= 0.05:
            tfail.append("truncation_lower95_not_above_0.05")
        if excess["estimate"] < 0.05:
            tfail.append("excess_median_below_0.05")
        if excess["lo95"] <= 0:
            tfail.append("excess_lower95_not_above_zero")
        if not tfail:
            result["truncation_verdict"] = "SUPPORTED"
        elif truncation["hi95"] < 0.10 or excess["hi95"] < 0.05:
            result["truncation_verdict"] = "REFUTED"
    result["naming_failed_clauses"] = ";".join(nfail)
    result["truncation_failed_clauses"] = ";".join(tfail)
    return result


def _group_bootstrap(points: np.ndarray, boots: np.ndarray, corpora: list[str], label: str) -> tuple[np.ndarray, np.ndarray]:
    """Fact→item and source-corpus→fact→item; all metric columns stay paired."""
    n_facts, n_metrics = points.shape
    iid = np.full((N_BOOT, n_metrics), np.nan)
    clustered = np.full_like(iid, np.nan)
    cluster_members = [np.flatnonzero(np.asarray(corpora) == name) for name in sorted(set(corpora))]
    rng_iid = np.random.default_rng(_stream_seed(label + ":iid"))
    rng_corpus = np.random.default_rng(_stream_seed(label + ":corpus"))
    for b in range(N_BOOT):
        selected = rng_iid.integers(n_facts, size=n_facts)
        item_replicates = rng_iid.integers(N_BOOT, size=n_facts)
        iid[b] = np.median(boots[selected, item_replicates, :], axis=0)
        cluster_draw = rng_corpus.integers(len(cluster_members), size=len(cluster_members))
        selected = np.concatenate([rng_corpus.choice(cluster_members[k], size=len(cluster_members[k]), replace=True)
                                   for k in cluster_draw])
        item_replicates = rng_corpus.integers(N_BOOT, size=len(selected))
        clustered[b] = np.median(boots[selected, item_replicates, :], axis=0)
    return iid, clustered


def _groups(eligibility: list[dict]) -> list[dict]:
    evaluation = [row for row in eligibility if row["analysis_role"] == "evaluation"]
    calibration = [row for row in eligibility if row["analysis_role"] == "calibration"]
    output = [{"group": "primary_all", "kind": "primary", "facts": evaluation, "minimum": 16}]
    for tag in sorted({row["tag"] for row in evaluation}):
        output.append({"group": "primary_tag:" + tag, "kind": "primary_tag",
                       "facts": [row for row in evaluation if row["tag"] == tag], "minimum": 8})
    output += [{"group": "all100_sensitivity", "kind": "sensitivity", "facts": eligibility, "minimum": 16},
               {"group": "calibration12_diagnostic", "kind": "diagnostic", "facts": calibration, "minimum": 8},
               {"group": "eligible_r5_descriptive", "kind": "descriptive",
                "facts": [row for row in eligibility if _bool(row["r5_subset"])], "minimum": 8}]
    return output


def _headline_verdict(group_audits: list[dict]) -> dict:
    overall = next(group for group in group_audits if group["group"] == "primary_all")
    tags = [group for group in group_audits if group["group_kind"] == "primary_tag" and group["n_facts"] >= 8]
    supported = [group["group"] for group in tags if group["naming_verdict"] == "SUPPORTED"]
    possible = [group["group"] for group in tags if group["naming_verdict"] != "REFUTED"]
    if overall["naming_verdict"] == "SUPPORTED" and len(supported) >= 2:
        verdict = "SUPPORTED"
    elif overall["naming_verdict"] == "REFUTED" or len(possible) < 2:
        verdict = "REFUTED"
    else:
        verdict = "UNDERPOWERED"
    failures = []
    if overall["naming_verdict"] != "SUPPORTED":
        failures.append("primary_all_naming_gates_not_supported")
    if len(supported) < 2:
        failures.append("fewer_than_two_supported_eligible_tags")
    return {"verdict": verdict, "supported_tags": supported, "failed_clauses": failures,
            "primary_all_naming_verdict": overall["naming_verdict"]}


def infer(args: argparse.Namespace) -> dict:
    start, cpu_start = time.perf_counter(), time.process_time()
    if not args.cache.resolve().is_relative_to(CACHE_ROOT.resolve()) or not args.results.resolve().is_relative_to(RESULT_ROOT.resolve()):
        raise ValueError("WR-2 inference outputs must remain in their registered isolated paths")
    with args.eligibility.open(newline="") as handle:
        eligibility = [row for row in csv.DictReader(handle) if _bool(row["eligible"])]
    if len(eligibility) != 100 or sum(row["analysis_role"] == "evaluation" for row in eligibility) != 88:
        raise ValueError("Frozen population must remain 100 eligible / 88 evaluation / 12 calibration")
    manifest_path = args.cache / "wr2_splits.json"
    manifest = json.loads(manifest_path.read_text())
    if _digest({key: value for key, value in manifest.items() if key != "manifest_hash"}) != manifest["manifest_hash"]:
        raise ValueError("Cached split manifest checksum is inconsistent")
    preflight_path = args.eligibility.parent / "wr2_preflight.json"
    if _hash(preflight_path) != manifest["preflight_sha256"]:
        raise ValueError("Registered preflight changed since split preparation")
    preflight = json.loads(preflight_path.read_text())
    pinned_states = {entry["dataset"]: entry for entry in preflight["states"]}
    manifest_facts = {fact["dataset"]: fact for fact in manifest["facts"]}
    if set(manifest_facts) != {row["dataset"] for row in eligibility} or set(manifest_facts) != set(preflight["eligible_fact_ids"]):
        raise ValueError("Prediction split/preflight/eligibility fact populations differ")
    for row in eligibility:
        ds, fact = row["dataset"], manifest_facts[row["dataset"]]
        for kind, csv_column in (("state", "state_sha256"), ("index", "index_sha256")):
            expected_hash = fact["source"][kind + "_sha256"]
            pin = pinned_states[ds][kind]
            if pin["sha256"] != expected_hash or row[csv_column] != expected_hash:
                raise ValueError(f"{ds}: source {kind} differs between split manifest and preflight/eligibility")
            if _hash(Path(pin["resolved_path"])) != expected_hash:
                raise ValueError(f"{ds}: source {kind} bytes changed since registration")
    geometry_hashes = {name: _hash(args.cache / "geometry" / name) for name in
                       ("J.npy", "Q.npy", "haar384.npy", "pca384.npy", "pca_mean.npy")}
    sources = {row["dataset"]: args.cache / "predictions" / (row["dataset"] + ".npz") for row in eligibility}
    missing = [str(path) for path in sources.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} registered fact caches are absent; inference not run: {missing[:5]}")
    boot_dir = args.cache / "inference"
    boot_dir.mkdir(parents=True, exist_ok=True)
    args.results.mkdir(parents=True, exist_ok=True)
    script_sha = _hash(Path(__file__))
    jobs = []
    for row in eligibility:
        ds, fact = row["dataset"], manifest_facts[row["dataset"]]
        expected = {"manifest_hash": manifest["manifest_hash"], "geometry_hashes": geometry_hashes,
                    "source": fact["source"],
                    "signature": _digest({"fact": fact, "manifest": manifest["manifest_hash"],
                                          "geometry": geometry_hashes, "code": manifest["code_sha256"]})}
        jobs.append({"source": str(sources[ds]), "output": str(boot_dir / (ds + ".npz")),
                     "eligibility": row, "script_sha256": script_sha,
                     "expected_provenance": expected, "expected_test_ids": fact["test_ids"],
                     "expected_input_path": str(args.cache / "inputs" / (ds + ".npz")),
                     "expected_input_sha256": fact["input_sha256"]})
    metadata = {}
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context("spawn")) as executor:
        futures = {executor.submit(_fact_job, job): job["eligibility"]["dataset"] for job in jobs}
        for future in as_completed(futures):
            result = future.result()
            metadata[result["dataset"]] = result
            print(json.dumps({"stage": "fact_bootstrap", "dataset": result["dataset"],
                              "complete": len(metadata), "total": len(eligibility),
                              "worker_cpu_seconds": result["process_cpu_seconds"]}), flush=True)
    fact_rows = [cell for ds in sorted(metadata) for cell in metadata[ds]["cells"]]
    cached = {}
    for ds in sorted(metadata):
        with np.load(boot_dir / (ds + ".npz"), allow_pickle=False) as arrays:
            cached[ds] = {(int(n), str(metric)): (float(point), boot.copy())
                          for n, metric, point, boot in zip(arrays["cell_n"], arrays["cell_metric"], arrays["point"], arrays["boot"])}
    group_rows, group_audits, group_boot_arrays = [], [], {}
    for group in _groups(eligibility):
        ds_list = [row["dataset"] for row in group["facts"]]
        if not ds_list:
            continue
        corpora = [row["split_corpus"] for row in group["facts"]]
        for n in BUDGETS:
            metrics = ["auc_" + arm for arm in PRIMARY] + ["auc_native", "auc_prompt_only"] + list(CONTRASTS)
            if n == 256:
                metrics += ["auc_" + arm for arm in SECONDARY] + list(CONTROL_CONTRASTS)
            points = np.full((len(ds_list), len(metrics)), np.nan)
            boots = np.full((len(ds_list), N_BOOT, len(metrics)), np.nan)
            available = []
            for j, metric in enumerate(metrics):
                complete = [ds for ds in ds_list if (n, metric) in cached[ds]]
                available.append(len(complete))
                # No registered fact may disappear from a group endpoint after a failed fit.
                if len(complete) == len(ds_list):
                    for i, ds in enumerate(ds_list):
                        points[i, j], boots[i, :, j] = cached[ds][n, metric]
            iid, corpus = _group_bootstrap(points, boots, corpora, f"{group['group']}:{n}")
            endpoint = np.median(points, axis=0)
            by_metric = {}
            for j, metric in enumerate(metrics):
                is_complete = available[j] == len(ds_list)
                status = "COMPLETE" if is_complete else ("MISSING" if n == 512 else "INCOMPLETE")
                iid_ci, corpus_ci = _interval(iid[:, j]), _interval(corpus[:, j])
                row = {"group": group["group"], "group_kind": group["kind"], "n": n, "metric": metric,
                       "status": status, "estimate": float(endpoint[j]) if is_complete else None,
                       "n_expected": len(ds_list), "n_available": available[j], "n_corpora": len(set(corpora)),
                       "minimum_facts": group["minimum"],
                       **{"iid_" + key: value for key, value in iid_ci.items()},
                       **{"corpus_" + key: value for key, value in corpus_ci.items()},
                       **_wider(iid_ci, corpus_ci)}
                by_metric[metric] = row
            verdicts = _verdicts(by_metric, n, len(ds_list), group["minimum"])
            for row in by_metric.values():
                row.update(verdicts)
                group_rows.append(row)
            if n == 256:
                group_audits.append({"group": group["group"], "group_kind": group["kind"],
                                     "n_facts": len(ds_list), "n_corpora": len(set(corpora)), **verdicts})
            key = group["group"].replace(":", "_") + "_n" + str(n)
            group_boot_arrays[key + "_iid"] = iid
            group_boot_arrays[key + "_corpus"] = corpus
            group_boot_arrays[key + "_metrics"] = np.array(metrics)
            print(json.dumps({"stage": "group_bootstrap", "group": group["group"], "n": n, **verdicts}), flush=True)
    headline = _headline_verdict(group_audits)
    worker_cpu = sum(meta["process_cpu_seconds"] for meta in metadata.values())
    summary = {
        "status": "COMPLETE", "created_utc": datetime.now(timezone.utc).isoformat(),
        "version": VERSION, "command": sys.argv, "script_sha256": script_sha,
        "eligibility_sha256": _hash(args.eligibility), "manifest_hash": manifest["manifest_hash"],
        "preflight_sha256": manifest["preflight_sha256"], "geometry_hashes": geometry_hashes,
        "n_facts": len(eligibility), "n_evaluation": 88,
        "n_calibration": 12, "n_boot": N_BOOT, "seed": SEED, "workers": args.workers, "blas_threads_per_worker": 1,
        "bootstrap_method": "Per fact, average the five separate seed AUROCs; paired semantic-label-stratified item bootstrap. Group median: iid fact→item and split_corpus→fact→item; each sampled fact occurrence chooses one cached item replicate shared across all metrics. Choose wider-width95/90 intervals separately; ties choose corpus. Percentile intervals, no seed pseudo-replication.",
        "equivalence_boundary": "The90% interval must be strictly inside(-0.03,+0.03); touching a margin is not equivalence.",
        "incomplete_policy": "All five seeds and every registered fact are required per group metric; missing contributions produce no group numerical endpoint or support.",
        "missing_budget": {"n": 512, "reason": "448 training candidates remain after reserving64"},
        "headline_naming_verdict": headline["verdict"], "naming_supported_tags": headline["supported_tags"],
        "headline_primary_all_naming_verdict": headline["primary_all_naming_verdict"],
        "headline_rule": "Primary_all naming gates AND at least two evaluation tags of at least8 facts each must independently pass all naming gates.",
        "headline_failed_clauses": headline["failed_clauses"],
        "group_verdicts_at_256": group_audits,
        "wall_seconds": time.perf_counter() - start,
        "parent_process_cpu_seconds": time.process_time() - cpu_start, "worker_process_cpu_seconds": worker_cpu,
        "total_process_cpu_seconds": time.process_time() - cpu_start + worker_cpu, "gpu_hours": 0,
        "fact_bootstrap_sources": {ds: {key: metadata[ds][key] for key in
                                        ("source_sha256", "fit_signature", "manifest_hash", "process_cpu_seconds")}
                                   for ds in sorted(metadata)},
    }
    controls = [row for row in fact_rows if row["n"] == 256 and
                (row["metric"] in CONTROL_CONTRASTS or row["metric"] in {"auc_" + arm for arm in SECONDARY})]
    _write_csv(args.results / "wr2_facts.csv", fact_rows)
    _write_csv(args.results / "wr2_groups.csv", group_rows)
    _write_csv(args.results / "wr2_controls.csv", controls)
    _npz(boot_dir / "group_bootstraps.npz", **group_boot_arrays)
    summary.update(wall_seconds=time.perf_counter() - start,
                   parent_process_cpu_seconds=time.process_time() - cpu_start,
                   total_process_cpu_seconds=time.process_time() - cpu_start + worker_cpu)
    _write_json(args.results / "wr2_inference.json", summary)
    return summary


def self_test() -> None:
    from sklearn.metrics import roc_auc_score

    y = np.array([0, 0, 0, 1, 1, 1])
    scores = np.array([0.0, 0.0, 0.8, 0.2, 0.8, 1.0])
    weights = _stratified_weights(y, np.random.default_rng(1), n_boot=20)
    auc = _weighted_auc(scores, y, weights)
    for i in range(len(weights)):
        expanded = np.repeat(np.arange(len(y)), weights[i])
        assert np.isclose(auc[i], roc_auc_score(y[expanded], scores[expanded]), atol=1e-15)
    means = _seed_mean_auc(np.stack([scores, scores * 3 + 2]), y, weights)
    assert np.array_equal(means - means, np.zeros(len(weights)))  # identity map has zero paired uncertainty
    opposed = np.stack([y.astype(float), -100.0 * y])
    assert np.all(_seed_mean_auc(opposed, y, weights) == 0.5)
    assert roc_auc_score(y, opposed.mean(axis=0)) == 0.0  # averaging scores is a different, forbidden estimand
    point = np.array([[0.0], [0.0], [0.9]])
    assert float(np.median(point, axis=0)[0]) == 0.0 and np.isclose(float(np.mean(point)), 0.3)
    constant_boots = np.repeat(point[:, None, :], N_BOOT, axis=1)
    iid_medians, corpus_medians = _group_bootstrap(point, constant_boots, ["a", "b", "c"], "synthetic_median")
    # Medians of three values can only be0 or0.9; means would introduce0.3/0.6.
    assert set(np.unique(iid_medians)) == {0.0, 0.9}
    assert set(np.unique(corpus_medians)) <= {0.0, 0.9}
    row = {"status": "COMPLETE", "lo90": -0.029, "hi90": 0.029}
    assert _map_equivalent(row)
    assert not _map_equivalent({**row, "lo90": -0.03})
    assert not _map_equivalent({**row, "hi90": 0.03})
    preds = np.tile(scores, (5, 1))
    selected, _ = _complete_seed_rows("h", 256, np.array(["h"] * 5), np.array([256] * 5),
                                     np.arange(5), np.array(["complete"] * 4 + ["incomplete_fit"]), preds)
    assert selected is None  # finite stale scores on a failed fit may not enter AUC
    selected, _ = _complete_seed_rows("h", 256, np.array(["h"] * 5), np.array([256] * 5),
                                     np.arange(5), np.array(["complete"] * 5), preds)
    assert selected is not None
    preds[0, 0] = np.nan
    selected, _ = _complete_seed_rows("h", 256, np.array(["h"] * 5), np.array([256] * 5),
                                     np.arange(5), np.array(["complete"] * 5), preds)
    assert selected is None
    iid = {"lo95": 0.0, "hi95": 0.2, "lo90": 0.04, "hi90": 0.16}
    corpus = {"lo95": 0.02, "hi95": 0.18, "lo90": 0.01, "hi90": 0.19}
    wider = _wider(iid, corpus)
    assert wider["ci95_method"] == "iid" and wider["ci90_method"] == "corpus"
    good_map = {"status": "COMPLETE", "estimate": 0.0, "lo90": -0.01, "hi90": 0.01}
    good_naming = {"status": "COMPLETE", "estimate": 0.20, "lo95": 0.15, "hi95": 0.25}
    good_truncation = {"status": "COMPLETE", "estimate": 0.15, "lo95": 0.10, "hi95": 0.20}
    good_excess = {"status": "COMPLETE", "estimate": 0.10, "lo95": 0.05, "hi95": 0.15}
    endpoint = {"map_loss": good_map, "naming_loss": good_naming,
                "truncation_loss": good_truncation, "excess_truncation_loss": good_excess}
    assert _verdicts(endpoint, 256, 16, 8)["naming_verdict"] == "SUPPORTED"
    assert _verdicts({**endpoint, "map_loss": {**good_map, "status": "INCOMPLETE"}}, 256, 16, 8)["naming_verdict"] == "UNDERPOWERED"
    assert _verdicts(endpoint, 256, 7, 8)["naming_verdict"] == "UNDERPOWERED"
    expected = {"manifest_hash": "registered", "geometry_hashes": {"J.npy": "j"},
                "source": {"state_sha256": "s", "index_sha256": "i"}, "signature": "signature"}
    _validate_prediction_provenance(expected, expected)
    for key in expected:
        try:
            _validate_prediction_provenance({**expected, key: "stale"}, expected)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Stale {key} was accepted")
    all_group = {"group": "primary_all", "group_kind": "primary", "n_facts": 88, "naming_verdict": "SUPPORTED"}
    tag1 = {"group": "primary_tag:SURFACE", "group_kind": "primary_tag", "n_facts": 22, "naming_verdict": "SUPPORTED"}
    tag2 = {"group": "primary_tag:TOPIC", "group_kind": "primary_tag", "n_facts": 17, "naming_verdict": "SUPPORTED"}
    assert _headline_verdict([all_group, tag1, tag2])["verdict"] == "SUPPORTED"
    assert _headline_verdict([{**all_group, "naming_verdict": "UNDERPOWERED"}, tag1, tag2])["verdict"] == "UNDERPOWERED"
    assert _headline_verdict([all_group, tag1, {**tag2, "naming_verdict": "UNDERPOWERED"}])["verdict"] == "UNDERPOWERED"
    assert _headline_verdict([{**all_group, "naming_verdict": "REFUTED"}, tag1, tag2])["verdict"] == "REFUTED"
    input_ids, input_y = np.array(["a", "b", "c"]), np.array([0, 1, 0])
    assert np.array_equal(_validate_test_join(np.array(["b", "a"]), np.array([1, 0]), ["b", "a"], input_ids, input_y), [1, 0])
    for bad_ids, bad_y in ((np.array(["a", "b"]), np.array([0, 1])), (np.array(["b", "a"]), np.array([0, 1]))):
        try:
            _validate_test_join(bad_ids, bad_y, ["b", "a"], input_ids, input_y)
        except ValueError:
            pass
        else:
            raise AssertionError("Changed test IDs or semantic labels accepted")
    print("Synthetic checks passed: AUC/seed pairing, hierarchical median, equivalence margins, incomplete fits/populations, both headline gates, CI-width choice, stale provenance, exact semantic joins.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=CACHE_ROOT)
    parser.add_argument("--results", type=Path, default=RESULT_ROOT)
    parser.add_argument("--eligibility", type=Path, default=RESULT_ROOT / "wr2_eligibility.csv")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.workers not in (1, 2):
        parser.error("--workers must be1 or2")
    if args.self_test:
        self_test()
    else:
        infer(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
