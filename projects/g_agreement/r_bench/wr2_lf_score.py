"""WR-2 label-free fixed-candidate readouts and descriptive vocabulary alignment.

All empirical entry points require a pushed BRIEF_R §17 registration and an exact
committed variant-list match. Assets are local only. No outcome-dependent lexical
selection, hyperparameter search, model inference, or accelerator is performed.
"""
from __future__ import annotations

import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import resource
import subprocess
import time
import warnings

import numpy as np
import pandas as pd

from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import wr2_fit as F
from projects.g_agreement.r_bench import wr2_native_audit as N

ROOT = Path(__file__).resolve().parents[3]
RESULTS_REL = Path("results/g_agreement/r/i2")
VARIANTS_REL = RESULTS_REL / "wr2_lf_variants.json"
ARMS = ("canonical_sum", "canonical_mean", "variant_sum", "variant_mean")
SEEDS = (0, 1, 2, 3, 4)
NULL_SEED = 20261022
N_NULL = 128
MAX_CPU_SECONDS = 4 * 3600
PARITY_ATOL = 1e-5
PARITY_RTOL = 1e-5
J_SHA = "b1abd0f17500de785b68d94192b5446297f51eb1f64241c0b798383e332f7a1f"
TOKENIZER_PINS = {"tokenizer.json": "5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42",
                  "tokenizer_config.json": "5186f0defcd7f232382c7f0aebcd2252d073bb921ab240e407b7ae8745d2b29b"}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def registration(repo: Path, commit: str) -> str:
    commit = git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}")
    brief = git(repo, "show", f"{commit}:projects/g_agreement/BRIEF_R.md")
    if "## 17." not in brief or "WR-2" not in brief.split("## 17.", 1)[1]:
        raise RuntimeError("Registration lacks BRIEF_R §17 WR-2 follow-up")
    subprocess.run(["git", "merge-base", "--is-ancestor", commit,
                    "refs/remotes/origin/r/i2-wr2"], cwd=repo, check=True)
    committed = subprocess.check_output(["git", "show", f"{commit}:{VARIANTS_REL}"], cwd=repo)
    if committed != (repo / VARIANTS_REL).read_bytes():
        raise RuntimeError("Variant list differs from the pushed registration commit")
    return commit


def write_json(path: Path, value) -> None:
    F._json_write(path, value)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    pd.DataFrame(rows).to_csv(temp, index=False, lineterminator="\n")
    temp.replace(path)


def paths(repo: Path) -> tuple[Path, Path, Path]:
    old = repo / "cache/g_agreement/r/i2/wr2"
    out = repo / "cache/g_agreement/r/i2/wr2_lf"
    return old, out, repo / RESULTS_REL


def load_tokenizer(repo: Path):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(repo / "cache/g_agreement/s3/tok",
                                         local_files_only=True, trust_remote_code=False)


def side_letter(value: str) -> str:
    return {"positive": "A", "negative": "B", "A": "A", "B": "B"}[value]


def encode_surfaces(tokenizer, variant: dict) -> dict:
    facts = []
    for fact in variant["facts"]:
        sides = []
        for candidate in fact["candidates"]:
            canonical = " " + candidate["canonical"].strip()
            surfaces = candidate["surfaces"]
            if not surfaces or len(surfaces) != len(set(surfaces)):
                raise ValueError(f"Missing or duplicate explicit surfaces: {fact['dataset']}")
            records = []
            for surface in [canonical] + surfaces:
                tokens = tokenizer.encode(surface, add_special_tokens=False)
                if not tokens or any(t in tokenizer.all_special_ids for t in tokens):
                    raise ValueError(f"Empty/special-token candidate {fact['dataset']} {surface!r}")
                records.append({"surface": surface, "token_ids": tokens,
                                "tokens": tokenizer.convert_ids_to_tokens(tokens)})
            sides.append({"side": side_letter(candidate["side"]),
                          "used_in_primary": candidate["used_in_primary"],
                          "canonical": records[0], "variants": records[1:]})
        if sorted(c["side"] for c in sides) != ["A", "B"]:
            raise ValueError("Expected exactly two candidate sides")
        facts.append({"dataset": fact["dataset"], "sided": fact["sided"], "candidates": sides})
    return {"facts": facts, "canonical_rule": "' ' + canonical.strip(); no added special tokens",
            "variant_rule": "exact registered surfaces, equal mean; repeated token IDs count",
            "arms": ARMS}


def token_ids(tokens: dict) -> list[int]:
    return sorted({token for f in tokens["facts"] for c in f["candidates"]
                   for seq in [c["canonical"]] + c["variants"] for token in seq["token_ids"]})


def aggregate_scores(z: np.ndarray, fact: dict, columns: dict[int, int]) -> np.ndarray:
    """Readout construction is a pure function of scores and frozen strings."""
    by_side = {}
    for side in fact["candidates"]:
        sequence = side["canonical"]["token_ids"]
        canonical = z[:, [columns[t] for t in sequence]]
        variants = [z[:, [columns[t] for t in seq["token_ids"]]] for seq in side["variants"]]
        by_side[side["side"]] = np.stack([
            canonical.sum(axis=1), canonical.mean(axis=1),
            np.stack([v.sum(axis=1) for v in variants]).mean(axis=0),
            np.stack([v.mean(axis=1) for v in variants]).mean(axis=0)])
    if fact["sided"] in ("one", "one-sided", "one_sided"):
        return by_side["A"]
    if fact["sided"] not in ("two", "two-sided", "two_sided"):
        raise ValueError(f"Unknown sidedness: {fact['sided']}")
    return by_side["A"] - by_side["B"]


def prepare(repo: Path, out: Path, results: Path, manifest: dict, commit: str) -> dict:
    import torch
    from threadpoolctl import threadpool_limits
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    variant = json.loads((repo / VARIANTS_REL).read_text())
    if {x["dataset"] for x in variant["facts"]} != {x["dataset"] for x in manifest["facts"]}:
        raise ValueError("Variant-list population differs from WR-2 frozen population")
    for name, sha in TOKENIZER_PINS.items():
        if F._sha(repo / "cache/g_agreement/s3/tok" / name) != sha:
            raise ValueError(f"Pinned tokenizer differs: {name}")
    tokenizer = load_tokenizer(repo)
    tokenized = encode_surfaces(tokenizer, variant)
    tok_files = {f.name: F._sha(f) for f in sorted((repo / "cache/g_agreement/s3/tok").iterdir()) if f.is_file()}
    tokenized.update(registration_commit=commit, variants_sha256=F._sha(repo / VARIANTS_REL),
                     tokenizer_files=tok_files, manifest_hash=manifest["manifest_hash"])
    if F._sha(results / "wr2_preflight.json") != manifest["preflight_sha256"]:
        raise ValueError("Original prerequisite audit bytes changed")
    preflight = json.loads((results / "wr2_preflight.json").read_text())
    if preflight["status"] != "pass":
        raise ValueError("Prior WR-2 preflight is not pass")
    old_audit = json.loads((results / "wr2_native_audit.json").read_text())
    if old_audit["status"] != "PASS":
        raise ValueError("Prior native audit is not PASS")
    native, _ = N.load_validation_rows(preflight)
    needed = sorted(set(token_ids(tokenized)) | {
        t for rows in native.values() for row in rows for s in ("A", "B") for t in N.variant_ids(row, s)})
    w_path = repo / "cache/g_agreement/s3/qwen36_unembed.pt"
    j_path = repo / "cache/g_agreement/r/i2/wr2/geometry/J.npy"
    if F._sha(w_path) != N.W_SHA or F._sha(j_path) != J_SHA:
        raise ValueError("Pinned unembedding or J cache hash mismatch")
    with threadpool_limits(limits=1), torch.no_grad():
        W = torch.load(w_path, map_location="cpu", weights_only=True, mmap=True)["lm_head.weight"]
        if tuple(W.shape) != (248320, 5120):
            raise ValueError("Wrong unembedding shape")
        selected = W[needed].float().numpy()
        J = np.load(j_path, mmap_mode="r")
        denominators = np.maximum(np.linalg.norm(selected @ J, axis=1), 1e-9)
        if not np.isfinite(selected).all() or not np.isfinite(denominators).all():
            raise ValueError("Nonfinite selected geometry")
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "selected_W.npy", selected)
    np.save(out / "selected_denominators.npy", denominators)
    tokenized["selected_token_ids"] = needed
    tokenized["usable_vocabulary_ids"] = sorted(set(tokenizer.get_vocab().values())
                                               - set(tokenizer.all_special_ids))
    tokenized["usable_vocabulary_ids"] = [i for i in tokenized["usable_vocabulary_ids"] if 0 <= i < 248320]
    tokenized["special_ids_excluded"] = sorted(tokenizer.all_special_ids)
    # Small committed artifact contains candidate token IDs; the complete usable
    # vocabulary integer list is cached separately and its hash retained.
    vocab_ids = tokenized.pop("usable_vocabulary_ids")
    np.save(out / "usable_vocab_ids.npy", np.asarray(vocab_ids, dtype=np.int64))
    tokenized["usable_vocabulary_count_before_zero_norm_exclusion"] = len(vocab_ids)
    tokenized["usable_vocabulary_ids_sha256"] = F._sha(out / "usable_vocab_ids.npy")
    write_json(results / "wr2_lf_tokens.json", tokenized)
    record = {"status": "complete", "registration_commit": commit,
              "variants_sha256": F._sha(repo / VARIANTS_REL),
              "tokens_sha256": F._sha(results / "wr2_lf_tokens.json"),
              "manifest_hash": manifest["manifest_hash"], "code_sha256": F._sha(Path(__file__)),
              "preflight_sha256": F._sha(results / "wr2_preflight.json"),
              "old_native_audit_sha256": F._sha(results / "wr2_native_audit.json"),
              "J_sha256": J_SHA, "W_sha256": N.W_SHA,
              "files": {n: F._sha(out / n) for n in ("selected_W.npy", "selected_denominators.npy", "usable_vocab_ids.npy")},
              "n_candidate_token_ids": len(token_ids(tokenized)), "n_selected_token_ids": len(needed),
              "n_usable_vocabulary_ids": len(vocab_ids), "tokenizer_files": tok_files}
    write_json(out / "prepare.json", record)
    return record


def load_prepared(repo: Path, out: Path, results: Path, manifest: dict, commit: str) -> tuple[dict, dict]:
    record = json.loads((out / "prepare.json").read_text())
    if F._sha(repo / "cache/g_agreement/r/i2/wr2/geometry/J.npy") != J_SHA or F._sha(repo / "cache/g_agreement/s3/qwen36_unembed.pt") != N.W_SHA:
        raise ValueError("Pinned J/W changed after preparation")
    if (record["registration_commit"] != commit or record["manifest_hash"] != manifest["manifest_hash"]
            or record["variants_sha256"] != F._sha(repo / VARIANTS_REL)
            or record["tokens_sha256"] != F._sha(results / "wr2_lf_tokens.json")
            or record["code_sha256"] != F._sha(Path(__file__))):
        raise ValueError("Stale follow-up preparation: source, registration, split or variant mismatch")
    for name, sha in record["files"].items():
        if F._sha(out / name) != sha:
            raise ValueError(f"Prepared artifact hash changed: {name}")
    for name, sha in record["tokenizer_files"].items():
        if F._sha(repo / "cache/g_agreement/s3/tok" / name) != sha:
            raise ValueError("Tokenizer changed")
    return record, json.loads((results / "wr2_lf_tokens.json").read_text())


def audit_native(repo: Path, out: Path, results: Path, manifest: dict, prepared: dict, tokens: dict) -> dict:
    from threadpoolctl import threadpool_limits
    preflight = json.loads((results / "wr2_preflight.json").read_text())
    by_fact, _ = N.load_validation_rows(preflight)
    facts = {f["dataset"]: f for f in manifest["facts"]}
    cols = {t: i for i, t in enumerate(tokens["selected_token_ids"])}
    W = np.load(out / "selected_W.npy", mmap_mode="r")
    den = np.load(out / "selected_denominators.npy", mmap_mode="r")
    J = np.load(repo / "cache/g_agreement/r/i2/wr2/geometry/J.npy", mmap_mode="r")
    records = []
    with threadpool_limits(limits=1):
        for ds, rows in by_fact.items():
            fact = facts[ds]
            folder = repo / "cache/g_agreement/r/states" / ds
            if F._sha(folder / "chat_L42.npy") != fact["source"]["state_sha256"] or F._sha(folder / "index.json") != fact["source"]["index_sha256"]:
                raise ValueError("Native-audit source state/index bytes changed")
            X, ids = A.load_states(F._paths(repo), ds, "chat", 42)
            if ids != fact["state_ids"]:
                raise ValueError("State index changed")
            if set(fact["validation_ids"]) != {r["item_id"] for r in rows}:
                raise ValueError("Validation pool differs from exact frozen reservation")
            index = {iid: i for i, iid in enumerate(ids)}
            # This exactly shares the selected matrix and NumPy operations used
            # by the endpoint scorer; rows are calibration validation only.
            full = np.asarray(X @ J.T, np.float32)
            z = np.asarray((full[[index[r["item_id"]] for r in rows]] @ W.T) / den, np.float64)
            predicted = []
            for i, row in enumerate(rows):
                a = max(z[i, cols[t]] for t in N.variant_ids(row, "A"))
                b = max((z[i, cols[t]] for t in N.variant_ids(row, "B")), default=np.nan)
                predicted.append(a if row["sided"] == "one" else a - b)
            expected = np.asarray(A.primary_score(pd.DataFrame(rows), {ds: rows[0]["sided"]}))
            predicted = np.asarray(predicted)
            y = np.asarray([r["label"] for r in rows])
            error = np.max(np.abs(expected - predicted))
            auc_error = abs(A.auroc(y, expected) - A.auroc(y, predicted))
            passed = bool(np.allclose(predicted, expected, atol=N.ATOL, rtol=N.RTOL) and auc_error <= N.AUC_ATOL)
            records.append({"dataset": ds, "n": len(rows), "max_abs_error": float(error),
                            "auc_abs_error": float(auc_error), "pass": passed})
    result = {"status": "PASS" if all(r["pass"] for r in records) else "FAIL",
              "registration_commit": prepared["registration_commit"],
              "tokens_sha256": prepared["tokens_sha256"], "variants_sha256": prepared["variants_sha256"],
              "facts": records, "n_rows": sum(r["n"] for r in records),
              "score_atol": N.ATOL, "score_rtol": N.RTOL, "auc_atol": N.AUC_ATOL,
              "formula": "((X@J.T)@W_selected.T)/||W_selected@J||; native frozen max variants"}
    write_json(results / "wr2_lf_audit.json", result)
    if result["status"] != "PASS":
        raise RuntimeError("Shared-operation native score audit failed")
    return result


def _fit_score_one(job: dict) -> dict:
    from sklearn.exceptions import ConvergenceWarning
    from threadpoolctl import threadpool_limits
    start, cpu_start = time.monotonic(), time.process_time()
    fact = job["fact"]
    repo, old, out = map(Path, (job["repo"], job["old"], job["out"]))
    ds = fact["dataset"]
    if start >= job["deadline"]:
        raise RuntimeError("Four-core-hour conservative wall budget reached")
    old_prediction = old / "predictions" / f"{ds}.npz"
    signature = F._digest({"fact": fact, "prepared": job["prepared"],
                           "old_predictions_sha256": F._sha(old_prediction), "code_sha256": F._sha(Path(__file__))})
    target = out / "predictions" / f"{ds}.npz"
    direction_target = out / "directions" / f"{ds}.npz"
    if target.exists() and direction_target.exists():
        with np.load(target, allow_pickle=False) as cached:
            metadata = json.loads(str(cached["metadata_json"]))
        if metadata.get("signature") == signature and metadata.get("directions_sha256") == F._sha(direction_target):
            return metadata
    X, ids = A.load_states(F._paths(repo), ds, "chat", 42)
    if ids != fact["state_ids"]:
        raise ValueError(f"{ds}: exact state ordering changed")
    if F._sha(repo / "cache/g_agreement/r/states" / ds / "chat_L42.npy") != fact["source"]["state_sha256"]:
        raise ValueError(f"{ds}: state bytes changed")
    index = {iid: i for i, iid in enumerate(ids)}
    test = np.asarray([index[iid] for iid in fact["test_ids"]])
    J = np.load(old / "geometry/J.npy", mmap_mode="r")
    W = np.load(out / "selected_W.npy", mmap_mode="r")
    den = np.load(out / "selected_denominators.npy", mmap_mode="r")
    columns = {t: i for i, t in enumerate(job["selected_token_ids"])}
    with threadpool_limits(limits=1):
        full = np.asarray(X @ J.T, dtype=np.float32)
        z = np.asarray((full[test] @ W.T) / den, np.float64)
        scores = aggregate_scores(z, job["token_fact"], columns)
        if scores.shape != (4, len(test)) or not np.isfinite(scores).all():
            raise ValueError(f"{ds}: invalid label-free readout scores")
        # No test labels or existing predictions have been loaded above this
        # line: score construction depends only on states, W/J and fixed text.
        input_path = old / "inputs" / f"{ds}.npz"
        if F._sha(input_path) != fact["input_sha256"]:
            raise ValueError("Frozen pool labels changed")
        with np.load(input_path, allow_pickle=False) as inp:
            if inp["ids"].tolist() != ids:
                raise ValueError("Pool input IDs changed")
            y = inp["y"].copy()
        with np.load(old_prediction, allow_pickle=False) as pred:
            if pred["test_ids"].tolist() != fact["test_ids"] or not np.array_equal(pred["test_y"], y[test]):
                raise ValueError("Cached prediction/test semantic join changed")
            old_meta = json.loads(str(pred["metadata_json"]))
            if old_meta["manifest_hash"] != job["prepared"]["manifest_hash"]:
                raise ValueError("Cached WR-2 prediction uses different manifest")
            probe = []
            for seed in SEEDS:
                chosen = np.flatnonzero((pred["fit_arm"] == "full_j") & (pred["fit_n"] == 256)
                                       & (pred["fit_seed"] == seed))
                if len(chosen) != 1 or pred["fit_status"][chosen[0]] != "complete":
                    raise ValueError("Missing exact original n256 full-J probe")
                probe.append(pred["pred_test"][chosen[0]].copy())
            probe = np.asarray(probe)
            test_y, native_test = pred["test_y"].copy(), pred["native_test"].copy()
            directions, fit_rows, kinds, fit_seeds = [], [], [], []
            for kind in ("real", "shuffled"):
                for seed in SEEDS:
                    train_ids = fact["draws"][f"256:{seed}"]
                    train = np.asarray([index[iid] for iid in train_ids])
                    if len(train) != 256 or set(train_ids) & (set(fact["test_ids"]) | set(fact["validation_ids"])):
                        raise ValueError("Frozen training draw invalid")
                    labels = y[train]
                    if kind == "shuffled":
                        labels = np.random.default_rng(20261021 + seed).permutation(labels)
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always", ConvergenceWarning)
                        clf = A._fit_logreg(full[train], labels, 1.0, seed)
                    iterations = int(np.max(clf[-1].n_iter_))
                    if iterations >= 2000 or any(issubclass(w.category, ConvergenceWarning) for w in caught):
                        raise RuntimeError("Fixed-budget probe refit did not converge; no retry")
                    refit_scores = np.asarray(clf.decision_function(full[test]), np.float32)
                    arm = "full_j" if kind == "real" else "full_j_shuffle"
                    chosen = np.flatnonzero((pred["fit_arm"] == arm) & (pred["fit_n"] == 256)
                                           & (pred["fit_seed"] == seed))
                    if len(chosen) != 1 or pred["fit_status"][chosen[0]] != "complete":
                        raise ValueError("Missing prior fit for coefficient-refit parity")
                    baseline = pred["pred_test"][chosen[0]]
                    if not np.allclose(refit_scores, baseline, atol=PARITY_ATOL, rtol=PARITY_RTOL):
                        raise RuntimeError(f"{ds}: {kind} seed{seed} probe parity failed")
                    # StandardScaler coordinates must be reversed: vocabulary
                    # vectors act on raw Jh, not on standardized coordinates.
                    direction = clf[-1].coef_[0] / clf[0].scale_
                    norm = float(np.linalg.norm(direction))
                    if not np.isfinite(direction).all() or norm <= 0:
                        raise ValueError("Invalid raw-Jh probe direction")
                    directions.append(direction / norm)
                    kinds.append(kind)
                    fit_seeds.append(seed)
                    fit_rows.append({"dataset": ds, "kind": kind, "seed": seed,
                                     "status": "complete", "n_iter": iterations,
                                     "refit_score_max_abs_error": float(np.max(np.abs(refit_scores - baseline))),
                                     "raw_direction_norm": norm, "training_draw_hash": F._digest(train_ids)})
    F._npz_write(direction_target, directions=np.asarray(directions, np.float32),
                 kind=np.asarray(kinds), seed=np.asarray(fit_seeds))
    metadata = {"signature": signature, **job["prepared"],
                "dataset": ds, "tag": fact["tag"], "corpus": fact["corpus"], "role": fact["role"],
                "source": fact["source"], "old_predictions_sha256": F._sha(old_prediction),
                "directions_sha256": F._sha(direction_target), "alignment_fit_rows": fit_rows,
                "score_labels_used": False, "source_text_used": False,
                "wall_seconds": time.monotonic() - start, "process_cpu_seconds": time.process_time() - cpu_start}
    F._npz_write(target, test_ids=np.asarray(fact["test_ids"]), test_y=test_y,
                 native_test=native_test, probe_test=probe, scores=scores, arms=np.asarray(ARMS),
                 metadata_json=np.asarray(json.dumps(metadata, sort_keys=True, allow_nan=False)))
    return metadata


def run_scores(repo: Path, old: Path, out: Path, results: Path, manifest: dict,
               prepared: dict, tokens: dict, workers: int, deadline: float) -> None:
    token_facts = {f["dataset"]: f for f in tokens["facts"]}
    selected = tokens["selected_token_ids"]
    audit = json.loads((results / "wr2_lf_audit.json").read_text())
    if audit["status"] != "PASS" or audit["tokens_sha256"] != prepared["tokens_sha256"]:
        raise ValueError("New selected-row native parity audit has not passed")
    jobs = [{"repo": str(repo), "old": str(old), "out": str(out), "fact": fact,
             "prepared": prepared, "selected_token_ids": selected,
             "token_fact": token_facts[fact["dataset"]], "deadline": deadline}
            for fact in manifest["facts"]]
    rows, failures = [], []
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as pool:
        futures = {pool.submit(_fit_score_one, job): job["fact"]["dataset"] for job in jobs}
        for done, future in enumerate(as_completed(futures), 1):
            ds = futures[future]
            try:
                record = future.result()
                rows.extend(record["alignment_fit_rows"])
                print(f"[{done}/{len(jobs)}] {ds}: 4 fixed readouts, 10 parity-verified refits", flush=True)
            except Exception as exc:
                failures.append({"dataset": ds, "error": f"{type(exc).__name__}: {exc}"})
                print(f"[{done}/{len(jobs)}] FAILED {ds}: {exc}", flush=True)
            write_json(out / "score_failures.json", failures)
    write_csv(results / "wr2_lf_refits.csv", rows)
    if failures:
        raise RuntimeError(f"{len(failures)} facts failed; no incomplete endpoint population")


def merge_top(current_scores: np.ndarray, current_ids: np.ndarray, scores: np.ndarray,
              ids: np.ndarray, absolute: bool = False, k: int = 10) -> tuple[np.ndarray, np.ndarray]:
    """Top-k merge with stable token-ID tie break; retain signed cosine values."""
    if scores.shape[1] > k:
        keys = np.abs(scores) if absolute else scores
        keep = np.argpartition(keys, -k, axis=1)[:, -k:]
        threshold = np.take_along_axis(keys, keep, axis=1).min(axis=1)
        # Resolve exact ties at the selection boundary by token ID.
        above = (keys > threshold[:, None]).sum(axis=1)
        tied = (keys == threshold[:, None]).sum(axis=1)
        for row in np.flatnonzero(tied > k - above):
            strict = np.flatnonzero(keys[row] > threshold[row])
            equal = np.flatnonzero(keys[row] == threshold[row])
            equal = equal[np.argsort(ids[equal], kind="stable")][:k-len(strict)]
            keep[row] = np.concatenate([strict, equal])
        chunk_scores = np.take_along_axis(scores, keep, axis=1)
        chunk_ids = ids[keep]
    else:
        chunk_scores, chunk_ids = scores, np.broadcast_to(ids, scores.shape)
    all_scores = np.concatenate([current_scores, chunk_scores], axis=1)
    all_ids = np.concatenate([current_ids, chunk_ids], axis=1)
    result_scores, result_ids = [], []
    for s, i in zip(all_scores, all_ids):
        order = np.lexsort((i, -(np.abs(s) if absolute else s)))[:k]
        result_scores.append(s[order])
        result_ids.append(i[order])
    return np.asarray(result_scores), np.asarray(result_ids)


def run_alignment(repo: Path, out: Path, results: Path, manifest: dict, prepared: dict,
                  deadline: float) -> dict:
    import torch
    from threadpoolctl import threadpool_limits
    torch.set_num_threads(1)
    tokenizer = load_tokenizer(repo)
    metadata, directions = [], []
    for fact in manifest["facts"]:
        path = out / "directions" / f"{fact['dataset']}.npz"
        with np.load(out / "predictions" / f"{fact['dataset']}.npz", allow_pickle=False) as pred:
            meta = json.loads(str(pred["metadata_json"]))
        if meta["directions_sha256"] != F._sha(path) or meta["tokens_sha256"] != prepared["tokens_sha256"]:
            raise ValueError("Stale direction or endpoint cache")
        with np.load(path, allow_pickle=False) as d:
            for row, kind, seed in zip(d["directions"], d["kind"], d["seed"]):
                directions.append(row)
                metadata.append({"dataset": fact["dataset"], "tag": fact["tag"],
                                 "role": fact["role"], "corpus": fact["corpus"],
                                 "kind": str(kind), "seed": int(seed)})
    rng = np.random.default_rng(NULL_SEED)
    null = rng.normal(size=(N_NULL, 5120))
    null /= np.linalg.norm(null, axis=1, keepdims=True)
    directions.extend(null.astype(np.float32))
    metadata.extend({"dataset": "", "tag": "", "role": "null", "corpus": "",
                     "kind": "isotropic", "seed": i} for i in range(N_NULL))
    D = np.asarray(directions, np.float32)
    if D.shape != (1128, 5120):
        raise ValueError("Expected 500 real, 500 shuffled, 128 isotropic directions")
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    top_scores = abs_scores = np.empty((len(D), 0), dtype=np.float32)
    top_ids = abs_ids = np.empty((len(D), 0), dtype=np.int64)
    minimum = np.full(len(D), np.inf, dtype=np.float32)
    minimum_ids = np.full(len(D), -1, dtype=np.int64)
    usable = np.load(out / "usable_vocab_ids.npy")
    zero_rows, used_count = [], 0
    w_path = repo / "cache/g_agreement/s3/qwen36_unembed.pt"
    if F._sha(w_path) != N.W_SHA:
        raise ValueError("Unembedding changed before alignment")
    with threadpool_limits(limits=1), torch.no_grad():
        W = torch.load(w_path, map_location="cpu", weights_only=True, mmap=True)["lm_head.weight"]
        for offset in range(0, len(usable), 2048):
            if time.monotonic() >= deadline:
                raise RuntimeError("Conservative four-core-hour budget reached during vocabulary scan")
            ids = usable[offset:offset + 2048]
            rows = W[ids.tolist()].float().numpy()
            norms = np.linalg.norm(rows, axis=1)
            finite = np.isfinite(rows).all(axis=1) & np.isfinite(norms)
            if not finite.all():
                raise ValueError("Nonfinite vocabulary rows")
            zero_rows.extend(ids[norms == 0].tolist())
            keep = norms > 0
            ids, rows, norms = ids[keep], rows[keep], norms[keep]
            used_count += len(ids)
            if not len(ids):
                continue
            cosine = D @ (rows / norms[:, None]).T
            top_scores, top_ids = merge_top(top_scores, top_ids, cosine, ids)
            abs_scores, abs_ids = merge_top(abs_scores, abs_ids, cosine, ids, absolute=True)
            loc = np.argmin(cosine, axis=1)
            values = cosine[np.arange(len(D)), loc]
            update = values < minimum
            minimum[update] = values[update]
            minimum_ids[update] = ids[loc[update]]
            if offset % (2048 * 20) == 0:
                print(f"Alignment scan {min(offset+2048, len(usable))}/{len(usable)} vocabulary rows", flush=True)
    seeds, neighbors, null_rows = [], [], []
    for i, meta in enumerate(metadata):
        record = {**meta, "max_cosine": float(top_scores[i, 0]), "max_cosine_token_id": int(top_ids[i, 0]),
                  "min_cosine": float(minimum[i]), "min_cosine_token_id": int(minimum_ids[i]),
                  "max_absolute_cosine": float(abs(abs_scores[i, 0])),
                  "max_absolute_signed_cosine": float(abs_scores[i, 0]),
                  "max_absolute_token_id": int(abs_ids[i, 0])}
        if meta["kind"] == "isotropic":
            null_rows.append(record)
        else:
            seeds.append(record)
        if meta["kind"] == "real":
            for kind, values, ids in (("positive", top_scores[i], top_ids[i]),
                                      ("absolute", abs_scores[i], abs_ids[i])):
                for rank, (value, token) in enumerate(zip(values, ids), 1):
                    neighbors.append({**meta, "neighbor_kind": kind, "rank": rank,
                                      "token_id": int(token), "cosine": float(value),
                                      "token": tokenizer.convert_ids_to_tokens(int(token)),
                                      "decoded": tokenizer.decode([int(token)], skip_special_tokens=False,
                                                                   clean_up_tokenization_spaces=False)})
    write_csv(results / "wr2_lf_alignment_seeds.csv", seeds)
    write_csv(results / "wr2_lf_alignment_neighbors.csv", neighbors)
    write_csv(results / "wr2_lf_alignment_null.csv", null_rows)
    sf = pd.DataFrame(seeds)
    grouped = []
    for (ds, kind), frame in sf.groupby(["dataset", "kind"], sort=True):
        first = frame.iloc[0]
        grouped.append({"dataset": ds, "kind": kind, "tag": first.tag, "role": first.role,
                        "corpus": first.corpus, "n_seeds": len(frame),
                        **{f"mean_{col}": float(frame[col].mean()) for col in
                           ("max_cosine", "min_cosine", "max_absolute_cosine")}})
    write_csv(results / "wr2_lf_alignment_facts.csv", grouped)
    record = {"status": "complete", "registration_commit": prepared["registration_commit"],
              "tokens_sha256": prepared["tokens_sha256"], "manifest_hash": manifest["manifest_hash"],
              "n_real": 500, "n_shuffled": 500, "n_isotropic": 128,
              "isotropic_seed": NULL_SEED, "vocabulary_rows_used": used_count,
              "zero_norm_rows_excluded": zero_rows, "chunks": 2048,
              "space": "raw Jh: logistic coef / StandardScaler.scale_",
              "interpretation": "Descriptive. Low nearest-row cosine does not rule out token differences, sums, nonlinear decoders, or predictive readouts on the natural-state distribution.",
              "null_mean_max_cosine": float(np.mean([r["max_cosine"] for r in null_rows])),
              "null_median_max_cosine": float(np.median([r["max_cosine"] for r in null_rows])),
              "files": {name: F._sha(results / name) for name in
                        ("wr2_lf_alignment_seeds.csv", "wr2_lf_alignment_neighbors.csv",
                         "wr2_lf_alignment_null.csv", "wr2_lf_alignment_facts.csv")}}
    write_json(results / "wr2_lf_alignment.json", record)
    return record


def timed(stage: str, out: Path, function):
    start, own_start = time.monotonic(), time.process_time()
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
                  "children_cpu_s": children, "total_cpu_s": own + children,
                  "gpu_hours": 0, "code_sha256": F._sha(Path(__file__))}
        out.mkdir(parents=True, exist_ok=True)
        with (out / "stage_timings.jsonl").open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)


def self_test() -> None:
    """Meaningful synthetic checks; no repository assets or empirical data read."""
    fact = {"sided": "two", "candidates": [
        {"side": "A", "canonical": {"token_ids": [4, 4, 8]},
         "variants": [{"token_ids": [4]}, {"token_ids": [4, 8]}]},
        {"side": "B", "canonical": {"token_ids": [8]},
         "variants": [{"token_ids": [8]}]}]}
    z = np.array([[2., 6.], [-3., 1.]])
    expected = np.array([[4., -6.], [-8/3, -8/3], [-1., -3.5], [-3., -3.]])
    np.testing.assert_allclose(aggregate_scores(z, fact, {4: 0, 8: 1}), expected)
    fact["sided"] = "one"
    np.testing.assert_allclose(aggregate_scores(z, fact, {4: 0, 8: 1}),
                               [[10., -5.], [10/3, -5/3], [5., -2.5], [3., -2.]])
    # Equal per-string weights differ from pooling every token in all strings.
    assert expected[3, 0] != ((2. + 2. + 6.) / 3 - 6.)
    rng = np.random.default_rng(817)
    values = rng.normal(size=(5, 53))
    values[0] = 1.0  # Every row ties: smallest token IDs must win across chunks.
    ids = np.arange(53)[::-1]
    for absolute in (False, True):
        selected_s, selected_i = np.empty((5, 0)), np.empty((5, 0), dtype=int)
        for start in range(0, 53, 13):
            selected_s, selected_i = merge_top(selected_s, selected_i,
                                               values[:, start:start+13], ids[start:start+13],
                                               absolute=absolute, k=10)
        for row in range(5):
            key = np.abs(values[row]) if absolute else values[row]
            order = np.lexsort((ids, -key))[:10]
            np.testing.assert_array_equal(selected_i[row], ids[order])
            np.testing.assert_allclose(selected_s[row], values[row, order])
    X = rng.normal(size=(256, 7)) * np.arange(1, 8)
    y = (X[:, 1] + X[:, 4] > .3).astype(int)
    clf = A._fit_logreg(X, y, 1., 0)
    beta = clf[-1].coef_[0] / clf[0].scale_
    intercept = clf[-1].intercept_[0] - clf[0].mean_ @ beta
    np.testing.assert_allclose(clf.decision_function(X), X @ beta + intercept)

    native_frame = pd.DataFrame({"dataset": ["one", "two"], "lo": [2., 3.], "lp_A": [4., 5.]})
    native_expected = np.asarray(A.primary_score(native_frame, {"one": "one", "two": "two"}))
    np.testing.assert_array_equal(native_expected, [4., 3.])

    class FakeTokenizer:
        all_special_ids = [999]

        def encode(self, text, add_special_tokens=False):
            assert not add_special_tokens
            return [ord(c) for c in text]

        def convert_ids_to_tokens(self, ids):
            return [chr(i) for i in ids]

    variants = {"facts": [{"dataset": "synthetic", "sided": "one", "candidates": [
        {"side": "positive", "canonical": "  xx ", "used_in_primary": True,
         "surfaces": ["xx", " xx"]},
        {"side": "negative", "canonical": "b", "used_in_primary": False,
         "surfaces": ["b"]}]}]}
    tokens = encode_surfaces(FakeTokenizer(), variants)
    assert tokens["facts"][0]["candidates"][0]["canonical"]["token_ids"] == [32, 120, 120]
    assert tokens["facts"][0]["candidates"][0]["variants"][0]["token_ids"] == [120, 120]
    for bad_surfaces in (["xx", "xx"], [chr(999)], [""]):
        variants["facts"][0]["candidates"][0]["surfaces"] = bad_surfaces
        try:
            encode_surfaces(FakeTokenizer(), variants)
        except ValueError:
            pass
        else:
            raise AssertionError("Duplicate, special or empty candidate failed to reject")
    print("PASS synthetic: exact sequence weights/repeats, polarity, top-k/ties, scaler reversal, tokenizer and invalid-input guards; no empirical data read.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration-commit")
    parser.add_argument("--self-test", action="store_true", help="Synthetic checks only; no empirical inputs")
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--stage", choices=("all", "prepare", "audit", "score", "alignment"), default="all")
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.registration_commit:
        parser.error("--registration-commit is required for empirical stages")
    repo = args.repo.resolve()
    commit = registration(repo, args.registration_commit)
    old, out, results = paths(repo)
    manifest = F._load_manifest(old)
    prior_cpu = 0.0
    if (out / "stage_timings.jsonl").exists():
        prior_cpu = sum(json.loads(line)["total_cpu_s"] for line in (out / "stage_timings.jsonl").read_text().splitlines())
    # At most two active CPU workers, each one BLAS thread. This wall bound
    # conservatively charges two cores even during sequential stages.
    deadline = time.monotonic() + max(0.0, (MAX_CPU_SECONDS - prior_cpu - 60) / 2)
    if args.stage in ("all", "prepare"):
        timed("prepare", out, lambda: prepare(repo, out, results, manifest, commit))
    prepared, tokens = load_prepared(repo, out, results, manifest, commit)
    if args.stage in ("all", "audit"):
        timed("audit", out, lambda: audit_native(repo, out, results, manifest, prepared, tokens))
    if args.stage in ("all", "score"):
        timed("score", out, lambda: run_scores(repo, old, out, results, manifest,
                                              prepared, tokens, args.workers, deadline))
    if args.stage in ("all", "alignment"):
        timed("alignment", out, lambda: run_alignment(repo, out, results, manifest, prepared, deadline))


if __name__ == "__main__":
    main()
