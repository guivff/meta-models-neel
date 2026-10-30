"""WR-2 CPU probe fitting. Run only after the WR-2 registration is committed/pushed.

The existing frozen collectors and probe code are read-only. This module streams
the four frozen R-A score shards, reserves their existing 64 pool-eval items,
fits one label-free calibration-corpus PCA, and caches paired probe predictions.
No model, tokenizer, matrix, or other asset is downloaded.

Stages: prepare (source/split manifests), pca (calibration pool only), fit.
Outputs are isolated under cache/g_agreement/r/i2/wr2 and results/.../r/i2.
"""
from __future__ import annotations

# Set before numpy/sklearn imports, including in spawned processes.
import os
for _thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                         "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread_variable] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import resource
import sys
import time
import warnings

import numpy as np
import pandas as pd

from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import datasets as D
from projects.g_agreement.r_bench.interim import LABEL_DEFECT, corpus_of

SEEDS = (0, 1, 2, 3, 4)
BUDGETS = (16, 64, 256, 512)
PRIMARY_ARMS = ("h", "full_j", "p384", "complement", "haar384", "pca384")
SECONDARY_ARMS = ("h_unit", "full_j_unit", "h_massmean", "full_j_massmean",
                  "h_shuffle", "full_j_shuffle")
CALIBRATION_NUMBERS = frozenset((5, 6, 7, 133, 134, 135, 158, 159, 160, 161, 162, 163))
EXCLUDED_CALIBRATION_TEST_IDS = frozenset(("r-6_hist_fig_isamerican-test-0092",))
RECIPE = {"version": 1, "layer": 42, "render": "chat", "position": "last",
          "C": 1.0, "max_iter": 2000, "solver": "lbfgs", "penalty": "l2",
          "scaler": "StandardScaler fit on exact training draw", "seeds": SEEDS,
          "budgets": BUDGETS, "draw_rng": "1000*seed+42; budgets ascending",
          "primary_arms": PRIMARY_ARMS, "secondary_arms_at_256": SECONDARY_ARMS,
          "rank": 384, "pca_seed": 20261019, "pca_iterated_power": 7,
          "calibration_numbers": sorted(CALIBRATION_NUMBERS),
          "excluded_calibration_test_ids": sorted(EXCLUDED_CALIBRATION_TEST_IDS),
          "aggregation": "mean paired-seed AUC; downstream median over facts",
          "native_score": "frozen one-sided lp_A / two-sided lo; no sign changes"}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _json_write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temp.replace(path)


def _npz_write(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with temp.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    temp.replace(path)


def _paths(repo: Path) -> A.Paths:
    paths = A.Paths()
    paths.root = repo
    paths.cache = repo / "cache" / "g_agreement" / "r"
    paths.dataset = repo / "projects" / "g_agreement" / "dataset"
    return paths


def _corpus(ds: str) -> str:
    """Explicit sibling groups supplement the frozen §4.9-j ranges."""
    num = int(ds.split("_", 1)[0])
    if num in (5, 6, 7):
        return "historical_figures"
    if num in (133, 134, 135):
        return "context_type"
    legacy = corpus_of(ds)
    if legacy != ds:
        return legacy
    parent = getattr(D, "BINARISED_FROM", {}).get(ds)
    return "parent:" + str(parent[0]) if parent else ds


def _stream_scores(paths: A.Paths, datasets: set[str], kind: str) -> tuple[pd.DataFrame, dict]:
    """Filter while streaming, then apply the existing frozen provenance gate."""
    frames, sources = [], {}
    for shard in (1, 2, 3, 4):
        path = paths.cache / f"{kind}.{shard}.jsonl"
        if not path.exists():
            if kind == "reader_lo":
                raise FileNotFoundError(path)
            continue
        rows, content_hash = [], hashlib.sha256()
        with path.open("rb") as handle:
            for number, raw in enumerate(handle, 1):
                content_hash.update(raw)
                if not raw.strip():
                    continue
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Incomplete source {path}:{number}; no partial-tail use") from exc
                if row.get("dataset") not in datasets:
                    continue
                if kind == "reader_lo" and not (
                    row.get("reader") == "jlens" and row.get("layer") == 42
                    and row.get("render") == "chat" and row.get("position", "last") == "last"
                    and row.get("condition") == "natural"
                ):
                    continue
                rows.append({k: row.get(k) for k in (
                    "key", "dataset", "item_id", "state_item_id", "label", "split", "pod", "git_sha",
                    "condition", "reader", "layer", "render", "position", "lo", "lp_A", "lp_B",
                    "unscorable")})
        sources[str(path)] = {"sha256": content_hash.hexdigest(), "size": path.stat().st_size,
                              "selected_rows": len(rows)}
        frame = A.provenance_filter(pd.DataFrame(rows), path, kind, datasets=datasets)
        if len(frame):
            frames.append(frame)
    if not frames:
        return pd.DataFrame(), sources
    df = pd.concat(frames, ignore_index=True)
    # Repeated frozen rows may exist only if their semantic scores agree exactly.
    for _, group in df.groupby(["dataset", "item_id"], sort=False):
        if len(group) > 1:
            for column in ("label", "lo", "lp_A", "lp_B"):
                if group[column].dropna().nunique() > 1:
                    raise ValueError(f"Conflicting frozen {kind} rows: {group.item_id.iloc[0]}, {column}")
    return df.drop_duplicates(["dataset", "item_id"], keep="last"), sources


def prepare(repo: Path, out: Path, results: Path) -> dict:
    paths = _paths(repo)
    preflight_path = results / "wr2_preflight.json"
    preflight = json.loads(preflight_path.read_text())
    eligibility = pd.read_csv(results / "wr2_eligibility.csv").set_index("dataset")
    if _sha(paths.items()) != preflight["bank"]["sha256"]:
        raise ValueError("Bank bytes changed since registered preflight")
    pinned_states = {s["dataset"]: s for s in preflight["states"]}
    items, _ = A.load_bank(paths)
    wanted = set(items.dataset) - LABEL_DEFECT
    native, native_sources = _stream_scores(paths, wanted, "reader_lo")
    prompt, prompt_sources = _stream_scores(paths, wanted, "prompt_only")
    for pinned in preflight["native_scores"]["input_files"]:
        if native_sources[str(repo / pinned["path"])]["sha256"] != pinned["sha256"]:
            raise ValueError(f"Native shard changed since registered preflight: {pinned['path']}")
    sided = dict(zip(items.dataset, items.sided))
    native["score"] = A.primary_score(native, sided)
    native_map = {(r.dataset, r.item_id): r for r in native.itertuples(index=False)}
    prompt_map = {(r.dataset, r.item_id): r for r in prompt.itertuples(index=False)}
    facts, excluded = [], []
    for ds, frame in items.groupby("dataset", sort=True):
        if ds in LABEL_DEFECT:
            excluded.append({"dataset": ds, "reason": "LABEL_DEFECT"})
            continue
        folder = paths.cache / "states" / ds
        state_path, index_path = folder / "chat_L42.npy", folder / "index.json"
        if not state_path.exists() or not index_path.exists():
            excluded.append({"dataset": ds, "reason": "missing_states_or_index"})
            continue
        # Required loader, including its float32 convention.
        X, ids = A.load_states(paths, ds, "chat", 42)
        if len(ids) != len(set(ids)) or X.ndim != 2 or len(ids) != len(X):
            raise ValueError(f"{ds}: invalid state/index shape or duplicate state IDs")
        it = frame.set_index("item_id")
        if not set(ids).issubset(set(it.index)):
            raise ValueError(f"{ds}: state IDs outside frozen semantic bank")
        it = it.loc[ids]
        if not np.isfinite(X).all():
            raise ValueError(f"{ds}: nonfinite states; do not silently select rows")
        y = it.label.to_numpy(dtype=np.int64)
        if not set(y).issubset({0, 1}):
            raise ValueError(f"{ds}: nonbinary semantic labels")
        pool = np.flatnonzero(it.split.to_numpy() == "pool")
        test = np.flatnonzero(it.split.to_numpy() == "test")
        if len(pool) < 384 or len(test) < 100:
            excluded.append({"dataset": ds, "reason": "below_384_pool_or_100_test",
                             "n_pool": len(pool), "n_test": len(test)})
            continue
        native_scores = np.full(len(ids), np.nan, dtype=np.float64)
        prompt_scores = np.full(len(ids), np.nan, dtype=np.float64)
        for j, iid in enumerate(ids):
            row = native_map.get((ds, iid))
            if row is not None:
                if int(row.label) != int(y[j]):
                    raise ValueError(f"{ds}/{iid}: native label differs from semantic bank")
                if row.state_item_id not in (None, iid):
                    raise ValueError(f"{ds}/{iid}: unexpected state_item_id {row.state_item_id}")
                native_scores[j] = row.score
            po = prompt_map.get((ds, iid))
            if po is not None:
                if int(po.label) != int(y[j]):
                    raise ValueError(f"{ds}/{iid}: prompt-only label differs from bank")
                prompt_scores[j] = float(po.lo) if po.lo is not None else np.nan
        validation = pool[np.isfinite(native_scores[pool])]
        if len(validation) != 64:
            raise ValueError(f"{ds}: expected exactly 64 existing native-scored pool items; got {len(validation)}")
        train_pool = np.setdiff1d(pool, validation, assume_unique=True)
        if min(np.bincount(y[train_pool], minlength=2)) < 128:
            raise ValueError(f"{ds}: cannot draw balanced n=256 after validation reservation")
        role = str(eligibility.loc[ds, "analysis_role"])
        expected_role = "calibration" if int(ds.split("_", 1)[0]) in CALIBRATION_NUMBERS else "evaluation"
        if role != expected_role:
            raise ValueError(f"{ds}: registration role differs from fixed calibration list")
        if role == "calibration":
            test = np.asarray([j for j in test if ids[j] not in EXCLUDED_CALIBRATION_TEST_IDS], dtype=int)
        if not np.isfinite(native_scores[test]).all():
            raise ValueError(f"{ds}: incomplete native endpoint coverage")
        draws, missing = {}, []
        for seed in SEEDS:
            rng = np.random.default_rng(1000 * seed + 42)
            for n in BUDGETS:
                if min(np.bincount(y[train_pool], minlength=2)) < n // 2:
                    missing.append({"n": n, "seed": seed, "reason": "insufficient_training_after_validation"})
                    continue
                train = A.balanced_draw(train_pool, y, n, rng)
                if len(train) != n or set(train) & set(validation) or set(train) & set(test):
                    raise AssertionError(f"{ds}: invalid training draw")
                draws[f"{n}:{seed}"] = [ids[j] for j in train]
        source = {"state_sha256": _sha(state_path), "index_sha256": _sha(index_path),
                  "selected_native_sha256": _digest([
                      [iid, float(native_scores[j])] for j, iid in enumerate(ids) if np.isfinite(native_scores[j])]),
                  "selected_prompt_sha256": _digest([
                      [iid, float(prompt_scores[j])] for j, iid in enumerate(ids) if np.isfinite(prompt_scores[j])])}
        if source["state_sha256"] != pinned_states[ds]["state"]["sha256"] or source["index_sha256"] != pinned_states[ds]["index"]["sha256"]:
            raise ValueError(f"{ds}: state/index bytes changed since registered preflight")
        fact = {"dataset": ds, "tag": str(it.tag.iloc[0]), "corpus": str(eligibility.loc[ds, "split_corpus"]),
                "source_parent": str(eligibility.loc[ds, "source_parent"]), "role": role,
                "d": X.shape[1], "n_pool": len(pool), "n_training_pool": len(train_pool),
                "n_test": len(test), "state_ids": ids,
                "test_ids": [ids[j] for j in test], "validation_ids": [ids[j] for j in validation],
                "train_pool_ids": [ids[j] for j in train_pool], "draws": draws,
                "missing": missing, "source": source}
        input_path = out / "inputs" / f"{ds}.npz"
        _npz_write(input_path, ids=np.asarray(ids), y=y,
                   native=native_scores, prompt_only=prompt_scores)
        fact["input_sha256"] = _sha(input_path)
        facts.append(fact)
    if {f["dataset"] for f in facts} != set(preflight["eligible_fact_ids"]):
        raise ValueError("Eligible population changed since registered preflight")
    calibration = [f for f in facts if f["role"] == "calibration"]
    if len(facts) != 100 or len(calibration) != 12 or sum(f["role"] == "evaluation" for f in facts) != 88:
        raise ValueError("Registered 100 eligible / 12 calibration / 88 evaluation population changed")
    if {int(f["dataset"].split("_", 1)[0]) for f in calibration} != CALIBRATION_NUMBERS:
        raise ValueError("The twelve fixed calibration facts are not all eligible")
    cal_corpora = {f["corpus"] for f in calibration}
    if cal_corpora & {f["corpus"] for f in facts if f["role"] == "evaluation"}:
        raise ValueError("Calibration/evaluation source-corpus overlap")
    manifest = {"repo": str(repo), "recipe": RECIPE, "recipe_hash": _digest(RECIPE), "code_sha256": _sha(Path(__file__)),
                "preflight_sha256": _sha(preflight_path),
                "bank_sha256": _sha(paths.items()), "source_shards": {**native_sources, **prompt_sources},
                "facts": facts, "excluded": excluded}
    manifest["manifest_hash"] = _digest(manifest)
    _json_write(out / "wr2_splits.json", manifest)
    compact = {k: v for k, v in manifest.items() if k != "facts"}
    compact["full_manifest_path"] = str(out / "wr2_splits.json")
    compact["facts"] = []
    for fact in facts:
        small = {k: v for k, v in fact.items() if k not in (
            "state_ids", "test_ids", "validation_ids", "train_pool_ids", "draws")}
        small["item_id_hashes"] = {key: _digest(fact[key]) for key in (
            "state_ids", "test_ids", "validation_ids", "train_pool_ids")}
        small["draw_hashes"] = {key: _digest(value) for key, value in fact["draws"].items()}
        compact["facts"].append(small)
    _json_write(results / "wr2_splits.json", compact)
    print(f"Prepared {len(facts)} eligible facts ({len(calibration)} calibration); frozen manifest {manifest['manifest_hash']}", flush=True)
    return manifest


def _load_manifest(out: Path) -> dict:
    manifest = json.loads((out / "wr2_splits.json").read_text())
    expected = manifest["manifest_hash"]
    if _digest({k: v for k, v in manifest.items() if k != "manifest_hash"}) != expected:
        raise ValueError("Split manifest hash mismatch")
    if manifest["recipe_hash"] != _digest(RECIPE) or manifest["code_sha256"] != _sha(Path(__file__)):
        raise ValueError("Recipe or source changed: rerun prepare before computing; stale reuse forbidden")
    paths = _paths(Path(manifest["repo"]))
    if _sha(paths.items()) != manifest["bank_sha256"]:
        raise ValueError("Frozen semantic bank changed")
    for path, source in manifest["source_shards"].items():
        if _sha(Path(path)) != source["sha256"]:
            raise ValueError(f"Frozen score shard changed: {path}")
    for fact in manifest["facts"]:
        folder = paths.cache / "states" / fact["dataset"]
        if _sha(folder / "chat_L42.npy") != fact["source"]["state_sha256"] or _sha(folder / "index.json") != fact["source"]["index_sha256"]:
            raise ValueError(f"Frozen state/index changed: {fact['dataset']}")
        if _sha(out / "inputs" / f"{fact['dataset']}.npz") != fact["input_sha256"]:
            raise ValueError(f"Frozen score inputs changed: {fact['dataset']}")
    return manifest


def fit_pca(repo: Path, out: Path, geometry: Path, manifest: dict) -> None:
    from sklearn.decomposition import PCA
    from threadpoolctl import threadpool_limits

    cal = [f for f in manifest["facts"] if f["role"] == "calibration"]
    signature = _digest({"manifest": manifest["manifest_hash"], "recipe": RECIPE,
                         "calibration": [f["dataset"] for f in cal]})
    record_path = geometry / "pca384.json"
    if record_path.exists():
        record = json.loads(record_path.read_text())
        if record.get("signature") == signature and all(
            (geometry / name).exists() and _sha(geometry / name) == digest
            for name, digest in record.get("files", {}).items()
        ):
            print("Reused hash-matched calibration PCA", flush=True)
            return
    paths, parts = _paths(repo), []
    for fact in cal:
        X, ids = A.load_states(paths, fact["dataset"], "chat", 42)
        if ids != fact["state_ids"]:
            raise ValueError("State ordering changed since split freeze")
        state_file = paths.cache / "states" / fact["dataset"] / "chat_L42.npy"
        if _sha(state_file) != fact["source"]["state_sha256"]:
            raise ValueError("Calibration states changed since split freeze")
        by_id = {iid: j for j, iid in enumerate(ids)}
        parts.append(X[[by_id[iid] for iid in fact["train_pool_ids"]]])
    data = np.concatenate(parts)
    start = time.monotonic()
    with threadpool_limits(limits=1):
        pca = PCA(n_components=384, svd_solver="randomized", iterated_power=7,
                  random_state=20261019).fit(data)
    geometry.mkdir(parents=True, exist_ok=True)
    np.save(geometry / "pca384.npy", pca.components_.T.astype(np.float32))
    np.save(geometry / "pca_mean.npy", pca.mean_.astype(np.float32))
    _json_write(record_path, {"signature": signature, "manifest_hash": manifest["manifest_hash"],
                             "calibration_facts": [f["dataset"] for f in cal], "n_rows": len(data),
                             "labels_used": False, "validation_or_test_used": False,
                             "svd_solver": "randomized", "iterated_power": 7, "random_state": 20261019,
                             "wall_s": time.monotonic() - start,
                             "singular_values": pca.singular_values_.astype(float).tolist(),
                             "explained_variance_ratio_sum": float(pca.explained_variance_ratio_.sum()),
                             "files": {name: _sha(geometry / name) for name in ("pca384.npy", "pca_mean.npy")}})
    print(f"PCA done on {len(data)} calibration-pool rows in {time.monotonic()-start:.1f}s", flush=True)


def _geometry_hashes(geometry: Path) -> dict:
    return {name: _sha(geometry / name) for name in
            ("J.npy", "Q.npy", "haar384.npy", "pca384.npy", "pca_mean.npy")}


def _fit_one(job: dict) -> list[dict]:
    from sklearn.exceptions import ConvergenceWarning
    from threadpoolctl import threadpool_limits

    fact, out, geometry = job["fact"], Path(job["out"]), Path(job["geometry"])
    ds = fact["dataset"]
    fact_cpu_start = time.process_time()
    if time.monotonic() >= job["deadline_monotonic"]:
        raise RuntimeError("WR-2 conservative CPU-budget deadline reached before fact start")
    signature = _digest({"fact": fact, "manifest": job["manifest_hash"],
                         "geometry": job["geometry_hashes"], "code": _sha(Path(__file__))})
    target = out / "predictions" / f"{ds}.npz"
    if target.exists():
        with np.load(target, allow_pickle=False) as previous:
            meta = json.loads(str(previous["metadata_json"]))
            if meta.get("signature") == signature:
                return meta["fit_rows"]
    paths = _paths(Path(job["repo"]))
    state_path = paths.cache / "states" / ds / "chat_L42.npy"
    if _sha(state_path) != fact["source"]["state_sha256"]:
        raise ValueError(f"{ds}: source state bytes changed")
    X, ids = A.load_states(paths, ds, "chat", 42)
    if ids != fact["state_ids"]:
        raise ValueError(f"{ds}: index changed")
    input_path = out / "inputs" / f"{ds}.npz"
    if _sha(input_path) != fact["input_sha256"]:
        raise ValueError(f"{ds}: cached input scores/labels changed")
    with np.load(input_path, allow_pickle=False) as inp:
        if inp["ids"].tolist() != ids:
            raise ValueError(f"{ds}: score/state ordering mismatch")
        y, native, prompt = inp["y"].copy(), inp["native"].copy(), inp["prompt_only"].copy()
    by_id = {iid: j for j, iid in enumerate(ids)}
    test = np.asarray([by_id[iid] for iid in fact["test_ids"]])
    val = np.asarray([by_id[iid] for iid in fact["validation_ids"]])
    J, Q, Haar, PC, mean = [np.load(geometry / name, mmap_mode="r") for name in
                            ("J.npy", "Q.npy", "haar384.npy", "pca384.npy", "pca_mean.npy")]
    d = X.shape[1]
    if J.shape != (d, d) or Q.shape != (d, 384) or PC.shape != (d, 384):
        raise ValueError(f"{ds}: unexpected geometry shapes")
    if Haar.shape not in ((d, 384), (len(SEEDS), d, 384)):
        raise ValueError(f"{ds}: Haar shape {Haar.shape}")
    fit_rows, pred_test, pred_val = [], [], []
    with threadpool_limits(limits=1):
        full = np.asarray(X @ J.T, dtype=np.float32)
        projected = np.asarray((X @ Q) @ Q.T, dtype=np.float32)
        F = {"h": X, "full_j": full, "p384": projected, "complement": X - projected,
             "pca384": np.asarray(((X - mean) @ PC) @ PC.T, dtype=np.float32),
             "h_unit": X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-12),
             "full_j_unit": full / np.maximum(np.linalg.norm(full, axis=1, keepdims=True), 1e-12)}
        for seed in SEEDS:
            H = Haar[seed] if Haar.ndim == 3 else Haar
            F["haar384"] = np.asarray((X @ H) @ H.T, dtype=np.float32)
            for n in BUDGETS:
                draw = fact["draws"].get(f"{n}:{seed}")
                arms = PRIMARY_ARMS + (SECONDARY_ARMS if n == 256 else ())
                for arm in arms:
                    row = {"dataset": ds, "tag": fact["tag"], "corpus": fact["corpus"],
                           "role": fact["role"], "n": n, "seed": seed, "arm": arm,
                           "C": None if arm.endswith("massmean") else 1.0,
                           "n_test": len(test), "n_val": len(val), "status": "pending",
                           "signature": signature}
                    start = time.monotonic()
                    cpu_start = time.process_time()
                    scores_te = np.full(len(test), np.nan, dtype=np.float32)
                    scores_va = np.full(len(val), np.nan, dtype=np.float32)
                    if time.monotonic() >= job["deadline_monotonic"]:
                        row.update(status="incomplete_budget", reason="conservative14CPU-core-hour deadline")
                    elif draw is None:
                        row.update(status="missing_budget", reason="insufficient_training_after_validation")
                    else:
                        tr = np.asarray([by_id[iid] for iid in draw])
                        if len(tr) != n or set(tr) & (set(test) | set(val)):
                            raise AssertionError("Training budget or disjointness violation")
                        base = arm.removesuffix("_shuffle").removesuffix("_massmean")
                        features = F[base]
                        labels = y[tr]
                        if arm.endswith("_shuffle"):
                            # Same label permutation for h and full_j under a seed.
                            labels = np.random.default_rng(20261021 + seed).permutation(labels)
                        try:
                            if arm.endswith("_massmean"):
                                direction = features[tr][labels == 1].mean(0) - features[tr][labels == 0].mean(0)
                                direction /= max(float(np.linalg.norm(direction)), 1e-12)
                                scores_te = np.asarray(features[test] @ direction, np.float32)
                                scores_va = np.asarray(features[val] @ direction, np.float32)
                                row.update(status="complete", n_iter=0, converged=True)
                            else:
                                with warnings.catch_warnings(record=True) as caught:
                                    warnings.simplefilter("always", ConvergenceWarning)
                                    clf = A._fit_logreg(features[tr], labels, 1.0, seed)
                                bad = any(issubclass(w.category, ConvergenceWarning) for w in caught)
                                n_iter = int(np.max(clf[-1].n_iter_))
                                if bad or n_iter >= 2000:
                                    row.update(status="incomplete_convergence", n_iter=n_iter, converged=False,
                                               reason="fixed max_iter reached; no parameter retry")
                                else:
                                    scores_te = np.asarray(clf.decision_function(features[test]), np.float32)
                                    scores_va = np.asarray(clf.decision_function(features[val]), np.float32)
                                    row.update(status="complete", n_iter=n_iter, converged=True)
                            if row["status"] == "complete":
                                if not np.isfinite(scores_te).all() or not np.isfinite(scores_va).all():
                                    raise ValueError("nonfinite prediction")
                                row.update(test_auc=A.auroc(y[test], scores_te), val_auc=A.auroc(y[val], scores_va))
                        except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
                            row.update(status="incomplete_fit", reason=f"{type(exc).__name__}: {exc}", converged=False)
                            scores_te.fill(np.nan)
                            scores_va.fill(np.nan)
                    row["wall_s"] = time.monotonic() - start
                    row["process_cpu_s"] = time.process_time() - cpu_start
                    fit_rows.append(row)
                    pred_test.append(scores_te)
                    pred_val.append(scores_va)
    metadata = {"signature": signature, "manifest_hash": job["manifest_hash"],
                "geometry_hashes": job["geometry_hashes"], "source": fact["source"],
                "recipe": RECIPE, "dataset": ds, "tag": fact["tag"], "corpus": fact["corpus"],
                "role": fact["role"], "fit_rows": fit_rows,
                "fact_process_cpu_s": time.process_time() - fact_cpu_start}
    _npz_write(target, pred_test=np.asarray(pred_test), pred_val=np.asarray(pred_val),
               fit_arm=np.asarray([r["arm"] for r in fit_rows]),
               fit_n=np.asarray([r["n"] for r in fit_rows]), fit_seed=np.asarray([r["seed"] for r in fit_rows]),
               fit_status=np.asarray([r["status"] for r in fit_rows]),
               test_ids=np.asarray(fact["test_ids"]), test_y=y[test],
               val_ids=np.asarray(fact["validation_ids"]), val_y=y[val],
               native_test=native[test], native_val=native[val],
               prompt_only_test=prompt[test], prompt_only_val=prompt[val],
               metadata_json=np.asarray(json.dumps(metadata, sort_keys=True, allow_nan=False)))
    return fit_rows


def run_fits(repo: Path, out: Path, geometry: Path, results: Path, manifest: dict,
             workers: int, max_facts: int | None) -> None:
    geometry_hashes = _geometry_hashes(geometry)
    facts = manifest["facts"]
    if max_facts is not None:
        # Smoke is calibration-only and never substitutes for the endpoint run.
        facts = [f for f in facts if f["role"] == "calibration"][:max_facts]
    timing_file = out / "stage_timings.jsonl"
    prior_cpu_s = sum(json.loads(line).get("total_cpu_s", 0.0) for line in timing_file.read_text().splitlines()) if timing_file.exists() else 0.0
    # One BLAS thread per worker. Reserve ten minutes for geometry/overhead outside
    # this runner and never allow seven hours of two-worker fitting to be exceeded.
    remaining_wall = max(0.0, (14 * 3600 - prior_cpu_s - 600) / workers)
    deadline = time.monotonic() + remaining_wall
    jobs = [{"fact": f, "repo": str(repo), "out": str(out), "geometry": str(geometry),
             "manifest_hash": manifest["manifest_hash"], "geometry_hashes": geometry_hashes,
             "deadline_monotonic": deadline} for f in facts]
    rows, failures = [], []
    csv_path = results / ("wr2_fits.smoke.csv" if max_facts is not None else "wr2_fits.csv")
    results.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as executor:
        pending = {executor.submit(_fit_one, job): job["fact"]["dataset"] for job in jobs}
        for done, future in enumerate(as_completed(pending), 1):
            ds = pending[future]
            try:
                fitted = future.result()
                rows.extend(fitted)
                incomplete = sum(r["status"].startswith("incomplete") for r in fitted)
                print(f"[{done}/{len(jobs)}] {ds}: {len(fitted)} fit rows; {incomplete} incomplete", flush=True)
            except Exception as exc:
                failures.append({"dataset": ds, "error": f"{type(exc).__name__}: {exc}"})
                print(f"[{done}/{len(jobs)}] FAILED {ds}: {exc}", flush=True)
            if rows:
                pd.DataFrame(rows).sort_values(["dataset", "n", "seed", "arm"]).to_csv(csv_path, index=False)
            _json_write(out / "fit_failures.json", failures)
    if failures:
        raise RuntimeError(f"{len(failures)} fact jobs failed; cached completed jobs are resumable")


def _timed_stage(stage: str, out: Path, function):
    start = time.monotonic()
    own_start = time.process_time()
    child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    status = "complete"
    try:
        return function()
    except BaseException:
        status = "failed"
        raise
    finally:
        child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
        own = time.process_time() - own_start
        children = (child_end.ru_utime + child_end.ru_stime) - (child_start.ru_utime + child_start.ru_stime)
        record = {"stage": stage, "status": status, "finished_utc": datetime.now(timezone.utc).isoformat(),
                  "wall_s": time.monotonic() - start, "main_process_cpu_s": own,
                  "children_cpu_s": children, "total_cpu_s": own + children, "gpu_hours": 0.0,
                  "code_sha256": _sha(Path(__file__))}
        out.mkdir(parents=True, exist_ok=True)
        with (out / "stage_timings.jsonl").open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.C.REPO_ROOT)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--geometry-dir", type=Path)
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--stage", choices=("prepare", "pca", "fit", "all"), default="all")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-facts", type=int, help="calibration-only smoke; never reduces endpoint population")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    out = args.out_dir or repo / "cache" / "g_agreement" / "r" / "i2" / "wr2"
    geometry = args.geometry_dir or out / "geometry"
    results = args.results_dir or repo / "results" / "g_agreement" / "r" / "i2"
    if args.workers < 1:
        parser.error("workers must be positive")
    if args.stage in ("prepare", "all"):
        manifest = _timed_stage("prepare", out, lambda: prepare(repo, out, results))
    else:
        manifest = _load_manifest(out)
    if args.stage in ("pca", "all"):
        _timed_stage("pca", out, lambda: fit_pca(repo, out, geometry, manifest))
    if args.stage in ("fit", "all"):
        _timed_stage("fit", out, lambda: run_fits(repo, out, geometry, results, manifest, args.workers, args.max_facts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
