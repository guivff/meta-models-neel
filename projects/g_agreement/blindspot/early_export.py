"""Publish training-only priority probes after complete, label-free asked seals.

This entry point never opens the full frozen label file and never evaluates the
W1 decision. The local dev-label derivation receipt was frozen before capture.
Only dev directions, coefficients, raw class means and training counts leave
this module. Full evaluation remains a separate all-row operation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import protocol as P
from .analysis import NATIVE, _grid, fit_direction

PRIORITY = ("table_column", "prose_paren", "prose_sentiment", "python_effect", "latex_subject")
INPUT_NAMES = {"items.input.jsonl", "templates.json", "provenance.json", "lengths.json", "causal.input.json",
               "sweep.input.json", "decoding.json", "runtime.json", "manifest.json"}
MINIMUM_SOURCE_FILES = {
    "common/__init__.py",
    "projects/g_agreement/blindspot/early_export.py",
    "projects/g_agreement/blindspot/analysis.py",
    "projects/g_agreement/blindspot/execution.py",
    "projects/g_agreement/blindspot/protocol.py",
    "external/mats-nla-workspace/src/mats/probes.py",
}


def _read(path):
    return json.loads(Path(path).read_text())


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _sources(plan):
    mapping = plan.get("runtime_source_files")
    if not isinstance(mapping, dict) or not MINIMUM_SOURCE_FILES <= set(mapping) or mapping != P.code_hashes():
        raise ValueError("execution plan lacks runtime source binding")
    for name, digest in mapping.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or not _hash(digest) or P.sha(P.ROOT / path) != digest:
            raise ValueError("runtime source bytes differ from execution plan")
    return mapping


def _score_seal(directory, phase):
    result = _read(directory / "SCORE_SEAL.json")
    required = {f"scores.{phase}.jsonl", f"provenance.{phase}.json", "items.order.json"}
    if phase == "target":
        required |= {"acts42.npy", "acts44.npy"}
    expected_status = f"SCORES_SEALED_{phase.upper()}_BEFORE_LABEL_JOIN"
    if result.get("status") != expected_status or not isinstance(result.get("files"), dict) or set(result["files"]) != required:
        raise ValueError("complete priority asked-score seal required")
    return P.verify(directory, "SCORE_SEAL.json")


def _training_rows(bank, plan, path, items, templates):
    """Read only the presealed dev derivative, never the source full labels."""
    declared = plan.get("training_labels", {})
    name = declared.get("relative_path", "")
    if (not isinstance(name, str) or Path(name).name != name or not name
            or "test" in name.lower() or not any(s in name.lower() for s in ("dev", "training"))
            or path.name != name or not _hash(declared.get("sha256")) or declared.get("count") != 420):
        raise ValueError("only the declared dev-only label derivative is accepted")
    receipt = _read(path.parent / "TRAINING_LABEL_SEAL.json")
    expected = {
        "schema": "blindspot-training-labels-v1", "status": "DEV_ONLY_FROM_FROZEN_LABELS",
        "input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"), "manifest_sha256": P.sha(bank / "manifest.json"),
        "source_labels_sha256": _read(bank / "provenance.json")["labels_sha256"],
        "training_labels_sha256": declared["sha256"], "training_labels_file": name, "count": 420,
        "features": list(PRIORITY),
    }
    if any(receipt.get(k) != v for k, v in expected.items()) or P.sha(path) != declared["sha256"]:
        raise ValueError("training label derivation receipt or bytes mismatch")
    ordered_ids = receipt.get("ordered_train_ids")
    itemmap = {it["id"]: it for it in items}
    if (not isinstance(ordered_ids, list) or len(ordered_ids) != 420 or len(set(ordered_ids)) != 420
            or not set(ordered_ids) <= set(itemmap)):
        raise ValueError("invalid presealed training subset")
    rows = P.rows(path)
    if [r.get("id") for r in rows] != ordered_ids:
        raise ValueError("training labels differ from presealed training order")
    allowed = {"id", "feature", "class", "domain", "value", "split", "cluster"}
    for row in rows:
        if set(row) != allowed or row["split"] != "dev":
            raise ValueError("early export refuses non-dev labels or extra label columns")
        item = itemmap[row["id"]]
        if row["feature"] != item["feature"] or row["feature"] not in PRIORITY:
            raise ValueError("training feature differs from priority item")
        spec = templates[row["feature"]]
        if row["class"] != spec["class"] or row["domain"] != spec["domain"] or row["value"] not in spec["values"]:
            raise ValueError("training definition differs from frozen bank")
    lookup = {r["id"]: r for r in rows}
    for row in rows:
        donor = lookup.get(itemmap[row["id"]]["donor_id"])
        if donor is None or donor["cluster"] != row["cluster"] or donor["value"] == row["value"] or donor["feature"] != row["feature"]:
            raise ValueError("training subset breaks opposite-value template pairing")
    for feature in PRIORITY:
        subset = [r for r in rows if r["feature"] == feature]
        if (len(subset) != 84 or len({r["cluster"] for r in subset}) != 6
                or any(sum(r["value"] == value for r in subset) != 42 for value in templates[feature]["values"])):
            raise ValueError("priority export needs 84 dev items, 42 per value and 6 templates per row")
    return rows, receipt


def export_training(a):
    with P.logged("priority_training_export", extra={"fit_split": "dev"}):
        return _export_training(a)


def _export_training(a):
    """Verify all four readers on the priority unit, then fit dev-only probes."""
    from . import execution
    bank, plan_path, target, nla, labels, out = map(Path, (a.bank, a.execution_plan, a.target, a.nla, a.training_labels, a.out))
    # Score seals and lineage are checked before any training-label file is read.
    _score_seal(target, "target")
    _score_seal(nla, "nla")
    frozen = _read(bank / "INPUT_SEAL.json")
    if (not isinstance(frozen.get("files"), dict) or set(frozen["files"]) != INPUT_NAMES
            or frozen.get("status") != "INPUTS_FROZEN"):
        raise ValueError("full frozen bank required for training export")
    P.verify(bank, "INPUT_SEAL.json")
    plan = execution.validate_plan(bank, plan_path)
    sources = _sources(plan)
    fullitems = P.rows(bank / "items.input.jsonl")
    selection = execution.select_unit(plan_path, "priority", bank, fullitems)
    items, binding = selection["items"], selection["binding"]
    ids = [it["id"] for it in items]
    if len(items) != 840 or set(it["feature"] for it in items) != set(PRIORITY):
        raise ValueError("priority unit must cover the five complete frozen rows")
    if any(sum(it["feature"] == f for it in items) != 168 for f in PRIORITY):
        raise ValueError("priority unit row coverage mismatch")
    expected_binding = {"execution_plan_sha256": P.sha(plan_path), "execution_unit": "priority"}
    if binding != expected_binding:
        raise ValueError("priority execution binding mismatch")
    provenances = []
    for directory, phase in ((target, "target"), (nla, "nla")):
        provenance = _read(directory / f"provenance.{phase}.json")
        expected = {"input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"), "source_files": sources,
                    "experiment": "W1", "execution": expected_binding}
        if any(provenance.get(k) != v for k, v in expected.items()):
            raise ValueError("priority score provenance differs from execution plan")
        if _read(directory / "items.order.json") != ids:
            raise ValueError("priority activation/score item order mismatch")
        if phase == "nla" and provenance.get("target_score_seal_sha256") != P.sha(target / "SCORE_SEAL.json"):
            raise ValueError("priority NLA/target score lineage mismatch")
        provenances.append(provenance)
    first, second = provenances
    if (not _hash(first.get("assets_sha256")) or first.get("assets_sha256") != second.get("assets_sha256")
            or first.get("batch") != P.RUNTIME["batch"] or second.get("batch") != P.RUNTIME["batch"]
            or first.get("hook") != "zero-based decoder block output, raw last-prefix-token state"
            or first.get("hook") != second.get("hook")):
        raise ValueError("priority target/NLA assets, batch or hook mismatch")
    templates = _read(bank / "templates.json")
    raw = P.rows(target / "scores.target.jsonl") + P.rows(nla / "scores.nla.jsonl")
    _grid(raw, items, templates, NATIVE)
    if any(r["status"] != "COMPLETE" for r in raw):
        raise ValueError("priority early export requires complete asked scores for all four readers")
    h = {layer: np.load(target / f"acts{layer}.npy", mmap_mode="r", allow_pickle=False) for layer in (42, 44)}
    if any(values.ndim != 2 or len(values) != 840 for values in h.values()):
        raise ValueError("priority activation shape mismatch")
    training, receipt = _training_rows(bank, plan, labels, items, templates)
    index = {key: i for i, key in enumerate(ids)}
    vectors, records = {}, []
    for feature in PRIORITY:
        rows = [r for r in training if r["feature"] == feature]
        indices = [index[r["id"]] for r in rows]
        spec = templates[feature]
        y = np.array([r["value"] == spec["values"][0] for r in rows], dtype=int)
        for layer in (42, 44):
            x = np.array(h[layer][indices], dtype=np.float32)
            fitted = fit_direction(x, y)
            prefix = f"{feature}__L{layer}"
            direction, coefficient = fitted.pop("direction"), fitted.pop("raw_coefficient")
            mean_a, mean_b = x[y == 1].mean(axis=0, dtype=np.float64), x[y == 0].mean(axis=0, dtype=np.float64)
            arrays = {"unit_direction": prefix + "__unit", "raw_coefficient": prefix + "__coef",
                      "raw_mean_A": prefix + "__mean_A", "raw_mean_B": prefix + "__mean_B"}
            vectors.update(dict(zip(arrays.values(), (direction, coefficient, mean_a, mean_b))))
            fitted["dev_class_mean_projection_gap"] = float((mean_a - mean_b) @ direction)
            records.append({"feature": feature, "class": spec["class"], "domain": spec["domain"], "layer": layer,
                "positive_value": spec["values"][0], "negative_value": spec["values"][1], "arrays": arrays, "array_prefix": prefix,
                "n_A": int(y.sum()), "n_B": int((1 - y).sum()), "n_template_clusters": len({r["cluster"] for r in rows}), **fitted})
    metadata = {
        "schema": "blindspot-priority-training-export-v1", "status": "TRAINING_ONLY_EARLY_EXPORT",
        "fit_split": "dev", "protocol": "training-only priority export after all-reader asked-score seals",
        "features": list(PRIORITY), "rows": records, "vectors": "probe_directions.npz",
        "training_labels_sha256": P.sha(labels), "training_label_seal_sha256": P.sha(labels.parent / "TRAINING_LABEL_SEAL.json"),
        "source_labels_sha256": receipt["source_labels_sha256"], "input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"),
        "manifest_sha256": P.sha(bank / "manifest.json"), "execution_plan_sha256": P.sha(plan_path),
        "target_score_seal_sha256": P.sha(target / "SCORE_SEAL.json"), "nla_score_seal_sha256": P.sha(nla / "SCORE_SEAL.json"),
        "runtime_source_files": sources,
    }
    out.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(out / "probe_directions.npz", **vectors)
    P.dump(out / "probe_directions.json", metadata)
    names = ("probe_directions.npz", "probe_directions.json")
    P.dump(out / "TRAINING_EXPORT_SEAL.json", {"status": "SEALED_TRAINING_ONLY_EXPORT", "files": {name: P.sha(out / name) for name in names}})
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bank", "execution-plan", "target", "nla", "training-labels", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    export_training(parser.parse_args(argv))


if __name__ == "__main__":
    main()
