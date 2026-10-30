"""Replay frozen J-lens candidate scores on WR-2 calibration validation rows.

Run only after the registration commit has been pushed. No target model, tokenizer,
network client or probe is used. Frozen variants_A/variants_B are the actual token
IDs scored by the collector, including its declared short-form fallback.

    python -m projects.g_agreement.r_bench.wr2_native_audit --registration-commit SHA

Writes only results/g_agreement/r/i2/wr2_native_audit.json. The 799-row W_U export
comparison belongs to wr2_geometry.py and is deliberately not repeated here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "results/g_agreement/r/i2"
J_PATH = ROOT / "cache/g_agreement/s3/jlens/Qwen3.6-27B_jacobian_lens_n1000.pt"
W_PATH = ROOT / "cache/g_agreement/s3/qwen36_unembed.pt"
J_SHA = "1718c8c52dd8a9dad03738d4d625937c1fbba10be325b872ed446c7290fc11e1"
W_SHA = "2e19a247094b33043d906d65377ecc2bd6fbff68dbf3563b6e79c74935baa54e"
FROZEN_SHA = "4d482b612b0da5838b83e43a4c85656daec7f778"
LAYER = 42
THREADS = 1
ATOL = 1e-4
RTOL = 1e-5
AUC_ATOL = 1e-6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def assert_registration_pushed(commit: str) -> str:
    """Local remote-tracking evidence suffices; this check never contacts a server."""
    full = git("rev-parse", "--verify", f"{commit}^{{commit}}")
    brief = git("show", f"{full}:projects/g_agreement/BRIEF_R.md")
    if "## 16. I2 / WR-2" not in brief:
        raise RuntimeError("Registration commit lacks BRIEF_R section 16")
    subprocess.run(["git", "merge-base", "--is-ancestor", full,
                    "refs/remotes/origin/r/i2-wr2"], cwd=ROOT, check=True)
    return full


def check_file(path: Path, expected: str) -> dict[str, Any]:
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"Input SHA256 mismatch: {path}")
    return {"path": str(path.relative_to(ROOT)), "sha256": actual,
            "bytes": path.stat().st_size}


def variant_ids(row: dict[str, Any], side: str) -> list[int]:
    variants = row.get(f"variants_{side}") or {}
    if not isinstance(variants, dict):
        raise RuntimeError(f"Invalid frozen variants_{side}: {row['key']}")
    result = []
    for token in variants.values():
        if not isinstance(token, int) or isinstance(token, bool) or token < 0:
            raise RuntimeError(f"Invalid frozen token ID: {row['key']}")
        if token not in result:
            result.append(token)
    return result


def load_validation_rows(preflight: dict[str, Any]) -> tuple[dict[str, list[dict]], list[dict]]:
    """Read only exact natural pool rows for the fixed calibration facts."""
    calibration = set(preflight["proposed_calibration_fact_ids"])
    selected: dict[str, dict] = {}
    inputs = []
    for entry in preflight["native_scores"]["input_files"]:
        path = ROOT / entry["path"]
        inputs.append(check_file(path, entry["sha256"]))
        with path.open() as handle:
            for line in handle:
                # Cheap filters precede JSON parsing; exact fields are checked next.
                if ('"reader": "jlens"' not in line or '"layer": 42' not in line
                        or '"render": "chat"' not in line or '"split": "pool"' not in line):
                    continue
                row = json.loads(line)
                if (row.get("reader") != "jlens" or row.get("layer") != LAYER
                        or row.get("render") != "chat" or row.get("split") != "pool"
                        or row.get("condition") != "natural" or row.get("position", "last") != "last"
                        or row.get("dataset") not in calibration):
                    continue
                if row.get("git_sha") != FROZEN_SHA or row.get("items_sha256") != preflight["bank"]["sha256"]:
                    raise RuntimeError(f"Frozen provenance mismatch: {row['key']}")
                if row.get("state_item_id") != row["item_id"] or row.get("unscorable"):
                    raise RuntimeError(f"Invalid frozen native row: {row['key']}")
                if row["key"] in selected and selected[row["key"]] != row:
                    raise RuntimeError(f"Conflicting duplicate native key: {row['key']}")
                selected[row["key"]] = row
    by_fact = {ds: sorted((r for r in selected.values() if r["dataset"] == ds),
                          key=lambda r: r["item_id"]) for ds in sorted(calibration)}
    for ds, rows in by_fact.items():
        if len(rows) != 64 or {label: sum(r["label"] == label for r in rows) for label in (0, 1)} != {0: 32, 1: 32}:
            raise RuntimeError(f"{ds}: reserved validation must have exactly 32+32 frozen pool rows")
    return by_fact, inputs


def run(registration_commit: str) -> dict[str, Any]:
    commit = assert_registration_pushed(registration_commit)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[variable] = str(THREADS)
    import numpy as np
    import pandas as pd
    import torch
    from threadpoolctl import threadpool_limits
    from projects.g_agreement.r_bench import analyze as A

    torch.set_num_threads(THREADS)
    torch.set_num_interop_threads(1)
    start, cpu_start = time.perf_counter(), time.process_time()
    preflight_path = RESULTS / "wr2_preflight.json"
    preflight = json.loads(preflight_path.read_text())
    if preflight["status"] != "pass":
        raise RuntimeError("WR-2 preflight is not PASS")
    by_fact, inputs = load_validation_rows(preflight)
    bank_path = ROOT / preflight["bank"]["path"]
    inputs.append(check_file(bank_path, preflight["bank"]["sha256"]))
    items = {item["item_id"]: item for item in json.loads(bank_path.read_text())["items"]}
    inputs.extend([check_file(J_PATH, J_SHA), check_file(W_PATH, W_SHA)])
    state_meta = {entry["dataset"]: entry for entry in preflight["states"]}
    all_ids = sorted({token for rows in by_fact.values() for row in rows
                      for side in ("A", "B") for token in variant_ids(row, side)})
    token_column = {token: column for column, token in enumerate(all_ids)}
    result: dict[str, Any] = {
        "status": "RUNNING", "registration_commit": commit,
        "started_utc": datetime.now(timezone.utc).isoformat(), "command": sys.argv,
        "device": "cpu", "threads": THREADS, "layer": LAYER, "render": "chat", "position": "last",
        "selection": "12 frozen calibration facts; exact 64 native-scored pool validation items each; no test rows",
        "formula": "z_t = ((h @ J42.T) @ W_U[t]) / max(||W_U[t] @ J42||_2, 1e-9); max over frozen token variants",
        "primary_score": "lp_A for one-sided facts; lp_A-lp_B for two-sided facts; original polarity",
        "native_normalization": {
            "row_dictionary_norm": True, "state_norm_denominator": False,
            "mapped_state_norm_denominator": False, "final_RMSNorm": False,
            "interpretation": "The collector labels format as cosine, but only the token covector is normalized. The score retains the magnitude of h; it is not a cosine between two unit vectors."},
        "tokenizer": "not loaded; actual frozen variants_A/variants_B token IDs are reused",
        "candidate_fallback": "Frozen cand_A/cand_B are checked against primary.jlens short forms, falling back to primary.candidates independently on each side.",
        "n_distinct_variant_ids": len(all_ids), "score_atol": ATOL, "score_rtol": RTOL,
        "parity_rule": "All primary scores satisfy abs(new-old) <= atol+rtol*abs(old), and absolute validation AUC difference <= 1e-6. Candidate-side errors are also reported.",
        "auc_atol": AUC_ATOL,
        "preflight_sha256": sha256(preflight_path), "inputs": inputs, "facts": [],
        "unembedding_export_check": "The independent 799-row frozen-export equality check is recorded by wr2_geometry.py.",
    }
    with threadpool_limits(limits=THREADS), torch.no_grad():
        lens = torch.load(J_PATH, map_location="cpu", weights_only=True, mmap=True)
        jacobians = lens["J"] if "J" in lens else lens["jacobians"]
        if isinstance(jacobians, dict):
            J = jacobians[LAYER] if LAYER in jacobians else jacobians[str(LAYER)]
        else:
            J = jacobians[LAYER]
        J = J.float().contiguous()
        unembedding = torch.load(W_PATH, map_location="cpu", weights_only=True, mmap=True)
        W = unembedding["lm_head.weight"][all_ids].float().contiguous()
        if tuple(J.shape) != (5120, 5120) or W.shape[1] != 5120:
            raise RuntimeError("Unexpected J42 or unembedding dimensions")
        if not bool(torch.isfinite(J).all()) or not bool(torch.isfinite(W).all()):
            raise RuntimeError("Nonfinite J42 or selected W_U rows")
        denominators = (W @ J).norm(dim=1).clamp_min(1e-9)
        P = A.Paths()
        for ds, rows in by_fact.items():
            metadata = state_meta[ds]
            for key in ("state", "index"):
                entry = metadata[key]
                result["inputs"].append(check_file(ROOT / entry["path"], entry["sha256"]))
            X, state_ids = A.load_states(P, ds, "chat", LAYER)
            index = {item_id: i for i, item_id in enumerate(state_ids)}
            if len(index) != len(state_ids):
                raise RuntimeError(f"Duplicate state IDs: {ds}")
            chosen = []
            for row in rows:
                item = items[row["item_id"]]
                if item["split"] != "pool" or item["dataset"] != ds or item["label"] != row["label"]:
                    raise RuntimeError(f"Invalid semantic join: {row['key']}")
                primary = item["primary"]
                short = primary.get("jlens") or [None, None]
                expected_candidates = [short[i] or primary["candidates"][i] for i in (0, 1)]
                if expected_candidates != [row["cand_A"], row["cand_B"]] or primary["sided"] != row["sided"]:
                    raise RuntimeError(f"Candidate/sidedness mismatch: {row['key']}")
                chosen.append(index[row["item_id"]])
            H = torch.from_numpy(X[chosen])
            if not bool(torch.isfinite(H).all()):
                raise RuntimeError(f"Nonfinite validation state: {ds}")
            z = ((H @ J.T) @ W.T) / denominators
            analytic_a, analytic_b = [], []
            best_a_same, best_b_same = [], []
            for k, row in enumerate(rows):
                for side, values, winners in (("A", analytic_a, best_a_same), ("B", analytic_b, best_b_same)):
                    variants = row.get(f"variants_{side}") or {}
                    tokens = variant_ids(row, side)
                    if not tokens:
                        values.append(float("nan"))
                        if row.get(f"lp_{side}") is not None:
                            raise RuntimeError(f"Missing variants for scored side {side}: {row['key']}")
                        continue
                    values.append(max(float(z[k, token_column[token]]) for token in tokens))
                    winner = max(variants, key=lambda text: float(z[k, token_column[variants[text]]]))
                    winners.append(winner == row.get(f"best_{side}"))
            a, b = np.asarray(analytic_a), np.asarray(analytic_b)
            analytic_lo = a - b
            one_sided = rows[0]["sided"] == "one"
            predicted = a if one_sided else analytic_lo
            native = np.asarray(A.primary_score(pd.DataFrame(rows), {ds: rows[0]["sided"]}), dtype=float)
            if not np.isfinite(native).all() or not np.isfinite(predicted).all():
                raise RuntimeError(f"Nonfinite primary score: {ds}")
            label = np.array([r["label"] for r in rows])
            primary_error = np.abs(predicted - native)
            fact: dict[str, Any] = {
                "dataset": ds, "tag": items[rows[0]["item_id"]]["tag"], "n": len(rows),
                "sided": rows[0]["sided"], "validation_item_ids": [r["item_id"] for r in rows],
                "primary_abs_error_max": float(primary_error.max()),
                "primary_abs_error_median": float(np.median(primary_error)),
                "primary_scores_close": bool(np.allclose(predicted, native, atol=ATOL, rtol=RTOL)),
                "native_validation_auc": A.auroc(label, native),
                "analytic_validation_auc": A.auroc(label, predicted),
                "auc_difference": A.auroc(label, predicted) - A.auroc(label, native),
                "best_A_same_fraction": float(np.mean(best_a_same)) if best_a_same else None,
                "best_B_same_fraction": float(np.mean(best_b_same)) if best_b_same else None,
            }
            for field, new in (("lp_A", a), ("lp_B", b), ("lo", analytic_lo)):
                old = np.array([r[field] if r.get(field) is not None else np.nan for r in rows])
                if not np.array_equal(np.isfinite(old), np.isfinite(new)):
                    raise RuntimeError(f"Missing-side mask mismatch: {ds} {field}")
                valid = np.isfinite(old)
                errors = np.abs(new[valid] - old[valid])
                fact[f"{field}_abs_error_max"] = float(errors.max()) if len(errors) else None
                fact[f"{field}_abs_error_median"] = float(np.median(errors)) if len(errors) else None
                fact[f"{field}_close"] = bool(np.allclose(new[valid], old[valid], atol=ATOL, rtol=RTOL))
            fact["auc_close"] = abs(fact["auc_difference"]) <= AUC_ATOL
            fact["pass"] = fact["primary_scores_close"] and fact["auc_close"]
            result["facts"].append(fact)
            print(f"{ds}: n={len(rows)}, max_abs_error={fact['primary_abs_error_max']:.6g}, pass={fact['pass']}", flush=True)
    result.update(status="PASS" if all(fact["pass"] for fact in result["facts"]) else "FAIL",
                  finished_utc=datetime.now(timezone.utc).isoformat(),
                  wall_seconds=time.perf_counter() - start, process_cpu_seconds=time.process_time() - cpu_start,
                  gpu_hours=0, n_facts=len(result["facts"]), n_rows=sum(fact["n"] for fact in result["facts"]))
    destination = RESULTS / "wr2_native_audit.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    temporary.replace(destination)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration-commit", required=True,
                        help="The pushed BRIEF_R §16 registration commit; verified against the local origin branch.")
    arguments = parser.parse_args()
    result = run(arguments.registration_commit)
    print(json.dumps({"status": result["status"], "n_facts": result["n_facts"], "n_rows": result["n_rows"]}))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
