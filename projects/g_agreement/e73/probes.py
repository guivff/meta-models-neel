"""CPU-only dev-fit E73 probes and W-lens handoff from sealed captures.

Fixed estimator: dev-standardized logistic regression, C=1, lbfgs, max_iter=2000,
random_state=20261027. Test data never selects hyperparameters or flips a sign.
This file belongs on the CPU host; it reads the private label map and must not be
included in pod archives. J-forecasts and judging are separate owners/stages.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .custody import read_jsonl, seal, sha256, verify_seal, write_json


def load_read_tokens(capture_dirs: list[Path], *, manifest_sha256: str) -> tuple[dict, dict, list[dict]]:
    import numpy as np
    block44, block42, bindings = {}, {}, []
    for directory in capture_dirs:
        metadata = verify_seal(directory, "CAPTURE_SEAL.json")
        if metadata.get("status") != "COMPLETE" or metadata.get("bank_manifest_sha256") != manifest_sha256:
            raise ValueError("capture is incomplete or belongs to a different bank")
        bindings.append({"seal_sha256": sha256(directory / "CAPTURE_SEAL.json")})
        for name in metadata["files"]:
            if not name.endswith(".npz"):
                continue
            with np.load(directory / name, allow_pickle=False) as data:
                if set(data.files) != {"ids", "block44", "block42"}:
                    raise ValueError("unexpected capture contents")
                ids = data["ids"].tolist()
                a44, a42 = data["block44"], data["block42"]
                if a44.shape != (len(ids), 256, 5120) or a42.shape != (len(ids), 5120):
                    raise ValueError("capture shape mismatch")
                if a44.dtype != np.float16 or a42.dtype != np.float16:
                    raise ValueError("capture dtype mismatch")
                for i, uid in enumerate(ids):
                    if uid in block44:
                        raise ValueError("duplicate captured ID")
                    block44[uid], block42[uid] = a44[i, -1].astype(np.float32), a42[i].astype(np.float32)
    return block44, block42, bindings


def verify_raw_conversion(test_x, transformed_x, mean, scale, coef, bias,
                          direction, intercept, scores) -> dict:
    """Check coordinate algebra separately from the estimator's input precision.

    StandardScaler preserves float32 inputs, and sklearn may also evaluate the
    decision function in float32. Those scores remain authoritative. The raw
    coefficients instead describe the same fitted model in float64 coordinates.
    Bounds use gamma_n = n*eps/(1-n*eps), never a data-tuned allclose tolerance.
    """
    import numpy as np
    x64 = np.asarray(test_x, dtype=np.float64)
    z_actual = np.asarray(transformed_x, dtype=np.float64)
    mean64, scale64 = np.asarray(mean, dtype=np.float64), np.asarray(scale, dtype=np.float64)
    coef64, direction64 = np.asarray(coef, dtype=np.float64), np.asarray(direction, dtype=np.float64)
    if (x64.ndim != 2 or z_actual.shape != x64.shape
            or any(a.shape != (x64.shape[1],) for a in (mean64, scale64, coef64, direction64))
            or np.any(scale64 <= 0)):
        raise ValueError("invalid raw-coordinate precision-check inputs")
    z64 = (x64 - mean64) / scale64
    reference = z64 @ coef64 + np.float64(bias)
    raw = x64 @ direction64 + np.float64(intercept)
    score_array = np.asarray(scores)
    if score_array.shape != raw.shape or score_array.dtype.kind != "f":
        raise ValueError("invalid decision-function score shape/dtype")
    if any(not np.isfinite(a).all() for a in (x64, z_actual, mean64, scale64, coef64,
                                             direction64, z64, reference, raw, score_array)):
        raise ValueError("nonfinite raw-coordinate precision-check inputs")
    n = x64.shape[1]
    def gamma(operations, dtype):
        accumulated = operations * np.finfo(dtype).eps
        if accumulated >= 1:
            raise ValueError("precision bound exceeds supported operation count")
        return accumulated / (1 - accumulated)
    g64 = gamma(n + 5, np.float64)
    gscore = gamma(n + 2, score_array.dtype)
    abs_coef, abs_direction = np.abs(coef64), np.abs(direction64)
    raw_magnitude = (np.abs(x64) @ abs_direction + np.abs(mean64) @ abs_direction
                     + abs(float(intercept)) + abs(float(bias)))
    reference_magnitude = np.abs(z64) @ abs_coef + abs(float(bias))
    actual_magnitude = np.abs(z_actual) @ abs_coef + abs(float(bias))
    # Two float64 paths: coefficient division, mean dot/subtraction and raw
    # dot/add; versus standardization and dot/add. Inflating by 1/(1-g64) also
    # covers roundoff in these nonnegative magnitude sums themselves.
    algebra_bound = 2 * g64 * (raw_magnitude + reference_magnitude) / (1 - g64)
    algebra_bound += (n + 5) * np.finfo(np.float64).tiny
    algebra_error = np.abs(raw - reference)
    if np.any(algebra_error > algebra_bound):
        raise ValueError("raw-coordinate probe conversion failed float64 algebra check")
    # Observe the actual scaler rounding coordinate by coordinate. Then allow
    # the reference dot/add's float64 error and the unchanged score path's own
    # dtype error (float32 in current sklearn for float32 fitted inputs).
    scaler_rounding = np.abs(z_actual - z64) @ abs_coef
    score_bound = algebra_bound + (scaler_rounding + g64 * reference_magnitude
                                   + gscore * actual_magnitude) / (1 - g64)
    score_bound += (n + 2) * np.finfo(score_array.dtype).tiny
    score_error = np.abs(raw - score_array.astype(np.float64))
    if np.any(score_error > score_bound):
        raise ValueError("raw-coordinate probe conversion exceeds precision bound")
    return {"method": "float64_algebra_and_dtype_roundoff_bound_v1",
            "transformed_dtype": str(np.asarray(transformed_x).dtype), "score_dtype": str(score_array.dtype),
            "max_algebra_error": float(algebra_error.max()), "max_algebra_bound": float(algebra_bound.max()),
            "max_score_error": float(score_error.max()), "max_score_bound": float(score_bound.max()),
            "max_scaler_rounding_bound": float(scaler_rounding.max())}


def fit_probe(dev_x, dev_y, test_x, test_y) -> dict:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.exceptions import ConvergenceWarning
    import warnings
    if set(np.unique(dev_y)) != {0, 1} or set(np.unique(test_y)) != {0, 1}:
        raise ValueError("both classes are required in both splits")
    scaler = StandardScaler().fit(dev_x)
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000, random_state=20261027)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(scaler.transform(dev_x), dev_y)
    transformed_test_x = scaler.transform(test_x)
    scores = model.decision_function(transformed_test_x)
    # Coefficients in the original activation coordinates, usable for E65 C.
    direction = model.coef_[0] / scaler.scale_
    intercept = model.intercept_[0] - np.dot(direction, scaler.mean_)
    precision = verify_raw_conversion(test_x, transformed_test_x, scaler.mean_, scaler.scale_,
                                      model.coef_[0], model.intercept_[0], direction, intercept, scores)
    return {"test_auroc": float(roc_auc_score(test_y, scores)), "test_scores": scores,
            "direction": direction, "intercept": float(intercept), "n_iter": int(model.n_iter_[0]),
            "scaler_mean": scaler.mean_, "scaler_scale": scaler.scale_, "precision_check": precision}


def run(args) -> dict:
    import numpy as np
    start = time.monotonic()
    gate = json.loads(args.gate.read_text())
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("private_labels_sha256") != sha256(args.labels):
        raise ValueError("private labels do not match the frozen bank manifest")
    if manifest.get("gate_report_sha256") != sha256(args.gate):
        raise ValueError("BOW gate does not match the frozen bank manifest")
    included = gate["included_states"]
    if not included or len(set(included)) != len(included):
        raise ValueError("no unique BOW-passing states")
    labels = read_jsonl(args.labels)
    selected = [r for r in labels if r["state"] in included]
    if len({r["id"] for r in selected}) != len(selected):
        raise ValueError("duplicate private ID")
    a44, a42, captures = load_read_tokens(args.capture, manifest_sha256=sha256(args.manifest))
    if set(a44) != {r["id"] for r in selected}:
        raise ValueError("capture IDs differ from complete gate-passing private bank")
    args.out.mkdir(parents=True, exist_ok=False)
    rows, files = [], []
    for state in included:
        state_rows = [r for r in selected if r["state"] == state]
        dev = sorted((r for r in state_rows if r["split"] == "dev"), key=lambda r: r["id"])
        test = sorted((r for r in state_rows if r["split"] == "test"), key=lambda r: r["id"])
        for split in (dev, test):
            minimum = 100 if state == "W8" else 400
            if not minimum <= len(split) <= 400 or len(split) % 2 or sum(r["label"] == 0 for r in split) != len(split) // 2 or sum(r["label"] == 1 for r in split) != len(split) // 2:
                raise ValueError("state split size or class balance violates registration")
        reader_ids = [r["id"] for r in test if r["reader_selected"]]
        if reader_ids != [r["id"] for r in test[:200]]:
            raise ValueError("reader IDs must be the frozen first 200 test positions")
        dx, tx = [np.stack([a44[r["id"]] for r in rs]) for rs in (dev, test)]
        dy, ty = [np.asarray([r["label"] for r in rs], dtype=np.int8) for rs in (dev, test)]
        fit = fit_probe(dx, dy, tx, ty)
        path = args.out / (state + "_probe.npz")
        np.savez(path, direction=fit["direction"], intercept=fit["intercept"],
                 scaler_mean=fit["scaler_mean"], scaler_scale=fit["scaler_scale"],
                 dev_mean_A=dx[dy == 0].mean(axis=0), dev_mean_B=dx[dy == 1].mean(axis=0),
                 test_mean_A=tx[ty == 0].mean(axis=0), test_mean_B=tx[ty == 1].mean(axis=0),
                 test_block44=tx, test_block42=np.stack([a42[r["id"]] for r in test]),
                 test_ids=np.asarray([r["id"] for r in test]), test_labels=ty,
                 test_scores=fit["test_scores"], reader_ids=np.asarray(reader_ids))
        files.append(path)
        rows.append({"state": state, "dev_count": len(dev), "test_count": len(test), "reader_count": len(reader_ids),
                     "test_auroc": fit["test_auroc"], "probe_pass": fit["test_auroc"] >= 0.90,
                     "iterations": fit["n_iter"], "precision_check": fit["precision_check"]})
    report = {"schema": "e73-probe-report-v1", "track": "C", "rows": rows,
              "probe_source_sha256": sha256(Path(__file__)),
              "excluded_states": gate.get("excluded_states", []), "elapsed_seconds": time.monotonic() - start,
              "gpu_seconds": 0, "jforecast": "PENDING_W_LENS_COMMIT", "readers": "NOT_RUN",
              "estimator": {"standardize": "dev_only", "class_positive": "B=1", "C": 1.0,
                            "solver": "lbfgs", "max_iter": 2000, "random_state": 20261027},
              "bank_manifest_sha256": sha256(args.manifest), "gate_report_sha256": sha256(args.gate),
              "private_labels_sha256": sha256(args.labels), "capture_seals": captures}
    write_json(args.out / "PROBE_REPORT.json", report)
    files.append(args.out / "PROBE_REPORT.json")
    seal(args.out, "PROBE_SEAL.json", files, track="C", status="COMPLETE", cpu_private=True)
    return report


def export_reader_inputs(probe_dir: Path, out: Path, *, max_rows: int = 700) -> dict:
    """Copy only frozen selected IDs and residuals; no state, split or label data.

    This CPU step prepares one small label-free NPZ per reader pod. Its index seal
    is the capture binding cited by the later GO; all original capture hashes are
    retained in that index. No reader text is produced or opened.
    """
    import numpy as np
    from .custody import MAX_ARCHIVE_BYTES
    metadata = verify_seal(probe_dir, "PROBE_SEAL.json")
    report = json.loads((probe_dir / "PROBE_REPORT.json").read_text())
    if metadata.get("status") != "COMPLETE" or not 1 <= max_rows <= 900:
        raise ValueError("requires complete probes and a bounded shard size")
    gathered = []
    for row in report["rows"]:
        with np.load(probe_dir / (row["state"] + "_probe.npz"), allow_pickle=False) as data:
            keep = set(data["reader_ids"].tolist())
            for i, uid in enumerate(data["test_ids"].tolist()):
                if uid in keep:
                    gathered.append((uid, data["test_block44"][i].astype(np.float16), data["test_block42"][i].astype(np.float16)))
    gathered.sort(key=lambda r: r[0])
    if len({x[0] for x in gathered}) != len(gathered):
        raise ValueError("reader IDs repeat")
    out.mkdir(parents=True, exist_ok=False)
    files, shards = [], []
    for begin in range(0, len(gathered), max_rows):
        rows = gathered[begin:begin + max_rows]
        p = out / f"reader-input-{len(shards):03d}.npz"
        np.savez(p, ids=np.asarray([r[0] for r in rows]), block44=np.stack([r[1] for r in rows]),
                 block42=np.stack([r[2] for r in rows]))
        if p.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("reader shard exceeds 20 MB")
        files.append(p)
        shards.append({"file": p.name, "count": len(rows), "sha256": sha256(p), "bytes": p.stat().st_size})
    index = {"schema": "e73-reader-inputs-v1", "bank_manifest_sha256": report["bank_manifest_sha256"],
             "source_capture_seals": report["capture_seals"], "probe_seal_sha256": sha256(probe_dir / "PROBE_SEAL.json"),
             "shards": shards, "total": len(gathered), "labels_present": False}
    write_json(out / "READER_INPUTS.json", index)
    files.append(out / "READER_INPUTS.json")
    seal(out, "READER_INPUT_SEAL.json", files, status="COMPLETE", track="C", labels_present=False)
    return index


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("labels", "gate", "manifest", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--capture", type=Path, nargs="+", required=True)
    print(json.dumps(run(p.parse_args())["rows"], indent=2))


if __name__ == "__main__":
    main()
