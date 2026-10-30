"""Offline CPU geometry for WR-2; run only after the dated registration is pushed.

This module uses local pinned tensors, never a target model or a network client.
The rank-384 proxy is built from RAW A = W_U J42, matching historical Y2/S3.
It is not the row-normalized native token dictionary and not a sparse subframe.

    python -m projects.g_agreement.r_bench.wr2_geometry

Large arrays: cache/g_agreement/r/i2/wr2/geometry/{J.npy,Q.npy,haar384.npy}.
Small audit: results/g_agreement/r/i2/{wr2_geometry.json,wr2_spectrum.csv}.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "cache" / "g_agreement"
OUTPUT_ROOT = CACHE / "r" / "i2" / "wr2"
RESULT_ROOT = ROOT / "results" / "g_agreement" / "r" / "i2"
J_SHA256 = "1718c8c52dd8a9dad03738d4d625937c1fbba10be325b872ed446c7290fc11e1"
W_SHA256 = "2e19a247094b33043d906d65377ecc2bd6fbff68dbf3563b6e79c74935baa54e"
J_REVISION = "b25d72a96b79c8e309d6625955a98751da47e67a"
MODEL_REVISION = "6a9e13bd6fc8f0983b9b99948120bc37f49c13e9"
LAYER, DIMENSION, VOCAB, RANK, HAAR_SEED = 42, 5120, 248320, 384, 20261020
THREADS = 2


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, obj: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def _atomic_npy(path: Path, value: Any) -> None:
    import numpy as np

    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, value, allow_pickle=False)
    temporary.replace(path)


def _check_descendant(path: Path, root: Path) -> None:
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Output must stay within {root}; got {path}")


def _sign_fix_columns(q: Any) -> Any:
    import numpy as np

    # A deterministic representation of an unchanged orthogonal projector.
    pivots = np.argmax(np.abs(q), axis=0)
    signs = np.sign(q[pivots, np.arange(q.shape[1])])
    signs[signs == 0] = 1
    return q * signs[None, :]


def _usage(start: float, cpu_start: float) -> dict[str, Any]:
    return {
        "wall_seconds": time.perf_counter() - start,
        "process_cpu_seconds": time.process_time() - cpu_start,
        "peak_rss_native": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "peak_rss_unit": "bytes" if platform.system() == "Darwin" else "KiB",
        "gpu_hours": 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    # Set before numerical imports. threadpoolctl below also controls already-loaded BLAS.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[variable] = str(THREADS)
    import numpy as np
    import scipy
    import scipy.linalg as la
    from scipy.linalg.blas import dsyrk
    from threadpoolctl import threadpool_info, threadpool_limits
    import torch

    torch.set_num_threads(THREADS)
    torch.set_num_interop_threads(1)
    start, cpu_start = time.perf_counter(), time.process_time()
    audit: dict[str, Any] = {
        "status": "RUNNING", "started_utc": _stamp(), "layer": LAYER,
        "rank_proxy": RANK, "haar_seed": HAAR_SEED, "threads": THREADS,
        "device": "cpu", "command": sys.argv,
        "definition": "raw A = W_U @ J42; Q contains its leading 384 right singular vectors",
        "native_normalization": "Native rows are A[t]/norm(A[t]); this proxy does not apply that normalization.",
        "interpretation": "Full-map invertibility alone is algebraic preservation, not a scientific discovery.",
        "versions": {"numpy": np.__version__, "scipy": scipy.__version__, "torch": torch.__version__},
        "stages": [],
    }

    def stage(name: str, stage_start: float, **details: Any) -> None:
        entry = {"name": name, "wall_seconds": time.perf_counter() - stage_start, **details}
        audit["stages"].append(entry)
        print(json.dumps(entry, allow_nan=False), flush=True)

    for output_path, root in ((args.out, OUTPUT_ROOT), (args.results, RESULT_ROOT)):
        _check_descendant(output_path, root)
    if (args.out / "geometry.json").exists() and not args.overwrite:
        raise FileExistsError(f"Completed geometry exists at {args.out}; use --overwrite only for an intentional rerun")

    # Hash both entire source files before loading any tensors.
    checkpoint = time.perf_counter()
    for name, path, expected in (("jlens", args.jlens, J_SHA256), ("unembedding", args.unembedding, W_SHA256)):
        real = path.resolve(strict=True)
        actual = file_sha256(real)
        if actual != expected:
            raise ValueError(f"{name} checksum mismatch: {actual} != pinned {expected}")
        audit[name] = {"path": str(real), "file_bytes": real.stat().st_size, "sha256": actual}
    audit["jlens"]["revision"] = J_REVISION
    audit["unembedding"].update({
        "model_revision": MODEL_REVISION,
        "hash_provenance": "Derived local .pt hash recorded by the pre-compute audit; independently checked against pinned pod candidate rows.",
    })
    stage("source_hashes", checkpoint)
    args.out.mkdir(parents=True, exist_ok=True)
    args.results.mkdir(parents=True, exist_ok=True)

    try:
        with threadpool_limits(limits=THREADS):
            audit["threadpools"] = threadpool_info()
            checkpoint = time.perf_counter()
            jl = torch.load(args.jlens, weights_only=True, mmap=True, map_location="cpu")
            weights = torch.load(args.unembedding, weights_only=True, mmap=True, map_location="cpu")
            jac = jl["J"] if "J" in jl else jl["jacobians"]
            jt = jac[LAYER] if not isinstance(jac, dict) or LAYER in jac else jac[str(LAYER)]
            wt = weights["lm_head.weight"]
            if tuple(jt.shape) != (DIMENSION, DIMENSION) or tuple(wt.shape) != (VOCAB, DIMENSION):
                raise ValueError(f"Unexpected tensor shapes: J={tuple(jt.shape)}, W={tuple(wt.shape)}")
            if jl.get("n_prompts") != 1000 or LAYER not in jl.get("source_layers", []):
                raise ValueError("J-lens source-layer/n_prompts metadata does not match the pinned n1000 lens")
            audit["jlens"].update({"shape": list(jt.shape), "storage_dtype": str(jt.dtype), "n_prompts": jl["n_prompts"]})
            audit["unembedding"].update({"shape": list(wt.shape), "storage_dtype": str(wt.dtype)})
            j = jt.to(dtype=torch.float64).numpy()
            if not np.isfinite(j).all():
                raise ValueError("Nonfinite J entries")
            _atomic_npy(args.out / "J.npy", j.astype(np.float32))
            stage("load_local_tensors", checkpoint)

            checkpoint = time.perf_counter()
            candidate_meta = json.loads(args.candidate_meta.read_text())
            if candidate_meta["jlens_sha256"] != J_SHA256 or candidate_meta["model_sha"] != MODEL_REVISION:
                raise ValueError("Candidate-row metadata does not pin the frozen J-lens/model")
            with np.load(args.candidate_rows, allow_pickle=False) as saved:
                ids, saved_rows = saved["token_ids"], saved["rows"]
                if len(ids) != 799 or saved_rows.shape != (799, DIMENSION):
                    raise ValueError(f"Expected 799 candidate rows; got {saved_rows.shape}")
                local_rows = wt[torch.as_tensor(ids.astype(np.int64))].to(dtype=torch.float32).numpy()
                delta = local_rows.astype(np.float64) - saved_rows.astype(np.float64)
                same_half = bool(np.array_equal(local_rows.astype(np.float16), saved_rows))
                audit["candidate_rows_check"] = {
                    "n_rows": int(len(ids)), "matches_saved_fp16_exactly": same_half,
                    "max_abs_difference_before_fp16": float(np.max(np.abs(delta))),
                    "rows_sha256": file_sha256(args.candidate_rows),
                    "meta_sha256": file_sha256(args.candidate_meta),
                    "paths": [str(args.candidate_rows.resolve()), str(args.candidate_meta.resolve())],
                }
                if not same_half:
                    raise ValueError("Local W_U candidate rows disagree with independently pinned pod rows")
            del local_rows, delta
            stage("candidate_rows_verification", checkpoint, **audit["candidate_rows_check"])

            checkpoint = time.perf_counter()
            # SVD of J itself avoids squaring its condition number for the full-map diagnosis.
            singular_j = la.svdvals(j, overwrite_a=False, check_finite=False)
            tol_j = DIMENSION * np.finfo(np.float64).eps * singular_j[0]
            rank_j = int(np.sum(singular_j > tol_j))
            condition_j = float(singular_j[0] / singular_j[-1]) if singular_j[-1] > 0 else None
            audit["J_spectrum"] = {
                "rank_float64": rank_j, "rank_tolerance": float(tol_j),
                "largest": float(singular_j[0]), "smallest": float(singular_j[-1]),
                "condition_number": condition_j, "method": "float64 direct SVD; scipy.linalg.svdvals",
            }
            stage("J_direct_singular_spectrum", checkpoint, **audit["J_spectrum"])

            checkpoint = time.perf_counter()
            # Raw A^T A = J^T (W^T W) J. dsyrk only calculates one triangle.
            b = np.zeros((DIMENSION, DIMENSION), dtype=np.float64, order="F")
            for first in range(0, VOCAB, args.chunk):
                last = min(first + args.chunk, VOCAB)
                w = np.asfortranarray(wt[first:last].to(dtype=torch.float64).numpy())
                if not np.isfinite(w).all():
                    raise ValueError(f"Nonfinite W entries in vocabulary rows {first}:{last}")
                b = dsyrk(1.0, w, beta=1.0, c=b, trans=1, lower=1, overwrite_c=1)
                print(json.dumps({"stage": "unembedding_gram", "vocabulary_rows": last, "total": VOCAB,
                                  "wall_seconds": time.perf_counter() - checkpoint}), flush=True)
            del w
            b += np.tril(b, k=-1).T
            # This certificate is about W, not a conclusion drawn from tiny Gram eigenvalues.
            try:
                chol = la.cholesky(b, lower=True, overwrite_a=False, check_finite=False)
                audit["unembedding"]["gram_cholesky_positive_definite"] = True
                del chol
            except la.LinAlgError:
                audit["unembedding"]["gram_cholesky_positive_definite"] = False
            stage("unembedding_gram", checkpoint)

            checkpoint = time.perf_counter()
            g = j.T @ (b @ j)
            del b
            g = (g + g.T) * 0.5
            trace_g = float(np.trace(g))
            # Complete eigenvalues make the spectrum audit explicit; vectors only escape as Q384.
            eigen_a, vectors = la.eigh(g, overwrite_a=False, check_finite=False, driver="evd")
            eigen_a = eigen_a[::-1].copy()
            q = _sign_fix_columns(np.ascontiguousarray(vectors[:, -RANK:][:, ::-1]))
            del vectors
            orthogonality = float(np.max(np.abs(q.T @ q - np.eye(RANK))))
            residual = float(la.norm(g @ q - q * eigen_a[:RANK][None, :], ord="fro") /
                             max(la.norm(g, ord="fro"), np.finfo(np.float64).tiny))
            gram_tol = DIMENSION * np.finfo(np.float64).eps * max(float(eigen_a[0]), 1.0)
            positive = eigen_a[eigen_a > gram_tol]
            audit["A_spectrum"] = {
                "method": "eigh of symmetrized float64 J.T @ (W.T @ W) @ J",
                "normalization": "none; raw historical Y2/S3 proxy",
                "trace": trace_g, "largest_eigenvalue": float(eigen_a[0]),
                "smallest_eigenvalue": float(eigen_a[-1]),
                "negative_eigenvalues": int(np.sum(eigen_a < 0)),
                "resolved_gram_rank": int(len(positive)), "gram_resolution_tolerance": float(gram_tol),
                "condition_estimate_resolved_spectrum": float(np.sqrt(eigen_a[0] / positive[-1])) if len(positive) else None,
                "rank_inferred_from_J_if_W_full_column_rank": rank_j if audit["unembedding"]["gram_cholesky_positive_definite"] else None,
                "caveat": "Gram formation squares conditioning; unresolved tail/negative roundoff is not evidence of information destruction.",
                "top384_matrix_energy_fraction": float(np.sum(eigen_a[:RANK]) / trace_g),
                "state_variance_caveat": "Matrix singular energy is not natural-state variance explained.",
            }
            audit["Q_checks"] = {"max_abs_orthogonality_error": orthogonality, "relative_eigenpair_residual": residual}
            if orthogonality > 1e-9 or residual > 1e-9:
                raise ValueError(f"Q numerical validation failed: {audit['Q_checks']}")
            _atomic_npy(args.out / "Q.npy", q.astype(np.float32))
            del g, q
            stage("raw_A_spectrum_and_Q384", checkpoint, **audit["Q_checks"])

            checkpoint = time.perf_counter()
            rng = np.random.default_rng(HAAR_SEED)
            haar, triangle = la.qr(rng.standard_normal((DIMENSION, RANK)), mode="economic", check_finite=False)
            signs = np.sign(np.diag(triangle))
            signs[signs == 0] = 1
            haar *= signs[None, :]
            haar_error = float(np.max(np.abs(haar.T @ haar - np.eye(RANK))))
            if haar_error > 1e-9:
                raise ValueError(f"Haar orthogonality error {haar_error}")
            _atomic_npy(args.out / "haar384.npy", haar.astype(np.float32))
            audit["Haar_checks"] = {"max_abs_orthogonality_error": haar_error, "seed": HAAR_SEED,
                                    "rng": "numpy.default_rng PCG64", "sign_rule": "positive QR diagonal"}
            stage("haar384", checkpoint, **audit["Haar_checks"])

            spectrum_rows = []
            for i, value in enumerate(singular_j):
                spectrum_rows.append({"map": "J42", "index_descending": i + 1, "singular_value": float(value),
                                      "gram_eigenvalue": "", "numerically_resolved": bool(value > tol_j)})
            for i, value in enumerate(eigen_a):
                spectrum_rows.append({"map": "raw_WU_J42_gram", "index_descending": i + 1,
                                      "singular_value": float(np.sqrt(max(value, 0.0))),
                                      "gram_eigenvalue": float(value), "numerically_resolved": bool(value > gram_tol)})
            for path in (args.out / "spectrum.csv", args.results / "wr2_spectrum.csv"):
                temporary = path.with_name(path.name + ".tmp")
                with temporary.open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(spectrum_rows[0]))
                    writer.writeheader()
                    writer.writerows(spectrum_rows)
                temporary.replace(path)
            audit["artifacts"] = {name: {"path": str((args.out / name).resolve()), "sha256": file_sha256(args.out / name)}
                                  for name in ("J.npy", "Q.npy", "haar384.npy", "spectrum.csv")}
            audit.update(_usage(start, cpu_start))
            audit.update({"status": "COMPLETE", "finished_utc": _stamp()})
            _atomic_json(args.out / "geometry.json", audit)
            _atomic_json(args.results / "wr2_geometry.json", audit)
            print(json.dumps({"status": "COMPLETE", **_usage(start, cpu_start)}, allow_nan=False), flush=True)
            return audit
    except Exception as error:
        audit.update(_usage(start, cpu_start))
        audit.update({"status": "FAILED", "finished_utc": _stamp(), "error": repr(error)})
        _atomic_json(args.out / "geometry.failed.json", audit)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jlens", type=Path, default=CACHE / "s3" / "jlens" / "Qwen3.6-27B_jacobian_lens_n1000.pt")
    parser.add_argument("--unembedding", type=Path, default=CACHE / "s3" / "qwen36_unembed.pt")
    parser.add_argument("--candidate-rows", type=Path, default=CACHE / "r" / "jlens_terms" / "jterms_wu_rows.npz")
    parser.add_argument("--candidate-meta", type=Path, default=CACHE / "r" / "jlens_terms" / "jterms_meta.json")
    parser.add_argument("--out", type=Path, default=OUTPUT_ROOT / "geometry")
    parser.add_argument("--results", type=Path, default=RESULT_ROOT)
    parser.add_argument("--chunk", type=int, default=8192)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if args.chunk < 1:
        parser.error("--chunk must be positive")
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
