"""E22 label-free worker inputs and separately sealed analysis truth.

The original labels are opened only after the E19 -> E3 input-seal -> label-hash
chain passes. Labels determine the registered donor controls and remain outside
the worker package. This module does not read scores or run any model.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

import numpy as np

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.e19 import inputs as E19

ROWS = E19.ROWS
SEED = 20261025
DONOR_ARMS = ("opposite", "same")
ITEM_FIELDS = {"id", "feature", "ids", "split", "parent_index", "e3_index", "cluster"}
DRAW_ORDER = "one PCG64 stream seeded 20261025; sorted feature then sorted recipient ID; opposite draw then same-value draw for each recipient; sorted eligible donor IDs; sampling with replacement across recipients"


def _read(path):
    return json.loads(Path(path).read_text())


def _verify(directory, name, required):
    seal = P.verify(directory, name)
    if not set(required) <= set(seal["files"]):
        raise ValueError(f"{name} lacks required file coverage")
    return seal


def _validate_items(items):
    if (len(items) != 420 or len({it["id"] for it in items}) != len(items)
            or Counter(it["feature"] for it in items) != {feature: 84 for feature in ROWS}):
        raise ValueError("E22 requires exactly five complete 84-item test rows")
    if any(set(item) != ITEM_FIELDS or item["split"] != "test" for item in items):
        raise ValueError("E22 items must be the original label-free E19 test records")
    for feature in ROWS:
        counts = Counter(it["cluster"] for it in items if it["feature"] == feature)
        if len(counts) != 6 or set(counts.values()) != {14}:
            raise ValueError("E22 needs the six original W1 template clusters per row")


def checked_labels(e19_inputs, labels, items, templates):
    """Verify the full source hash chain before parsing any label record."""
    e19_inputs, labels = Path(e19_inputs), Path(labels)
    _verify(e19_inputs, "INPUT_SEAL.json", {"provenance.json"})
    parent = _read(e19_inputs / "provenance.json")
    e3 = labels.parent / "e3"
    _verify(e3, "INPUT_SEAL.json", {"provenance.json", "items.input.jsonl"})
    e3_seal_hash = P.sha(e3 / "INPUT_SEAL.json")
    if parent["source_e3_input_seal_sha256"] != e3_seal_hash:
        raise ValueError("label source E3 seal differs from E19's frozen lineage")
    e3_provenance = _read(e3 / "provenance.json")
    if (e3_provenance.get("experiment") != "E3"
            or e3_provenance["w1_input_seal_sha256"] != parent["source_w1_input_seal_sha256"]):
        raise ValueError("E19/E3/W1 label-source lineage mismatch")
    label_hash = P.sha(labels)
    if label_hash != e3_provenance["labels_sha256"]:
        raise ValueError("labels differ from the sealed E3 source hash")
    # No label parsing occurs above this point.
    records = P.rows(labels)
    lookup = {row["id"]: row for row in records}
    if len(lookup) != len(records):
        raise ValueError("duplicate source label IDs")
    if not {item["id"] for item in items} <= set(lookup):
        raise ValueError("source labels do not cover every E22 recipient")
    selected = []
    for item in items:
        row = lookup[item["id"]]
        if any(row[key] != item[key] for key in ("feature", "split", "cluster")):
            raise ValueError("source label feature/split/cluster differs from E19")
        values = templates[item["feature"]]["values"]
        if len(values) != 2 or len(set(values)) != 2 or row["value"] not in values:
            raise ValueError("unknown or nonbinary frozen W1 value")
        selected.append({key: row[key] for key in ("id", "feature", "split", "cluster", "value")})
        selected[-1]["y"] = int(row["value"] == values[0])
    for feature in ROWS:
        feature_rows = [row for row in selected if row["feature"] == feature]
        if Counter(row["y"] for row in feature_rows) != {0: 42, 1: 42}:
            raise ValueError("E22 requires the complete 42/42 frozen class balance")
        for cluster in {row["cluster"] for row in feature_rows}:
            if Counter(row["y"] for row in feature_rows if row["cluster"] == cluster) != {0: 7, 1: 7}:
                raise ValueError("E22 requires the original 7/7 balance in each template cluster")
    return selected, {"source_e3_input_seal_sha256": e3_seal_hash,
                      "source_e3_provenance_sha256": P.sha(e3 / "provenance.json"),
                      "source_labels_sha256": label_hash,
                      "source_w1_input_seal_sha256": parent["source_w1_input_seal_sha256"]}


def donor_maps(items, labels, seed=SEED):
    """Freeze opposite-value and same-value-nonself controls without ID-order effects."""
    if len({item["id"] for item in items}) != len(items):
        raise ValueError("duplicate recipient IDs")
    lookup = {row["id"]: row for row in labels}
    if len(lookup) != len(labels) or set(lookup) != {item["id"] for item in items}:
        raise ValueError("donor construction needs exactly one label per recipient")
    indexed = {item["id"]: i for i, item in enumerate(items)}
    by_id = {item["id"]: item for item in items}
    if any(lookup[key]["feature"] != by_id[key]["feature"] or lookup[key]["y"] not in (0, 1) for key in indexed):
        raise ValueError("donor labels do not match recipient rows or binary orientation")
    rng = np.random.default_rng(seed)
    chosen = {arm: {} for arm in DONOR_ARMS}
    for feature in sorted({item["feature"] for item in items}):
        row_ids = sorted(item["id"] for item in items if item["feature"] == feature)
        for key in row_ids:
            y = lookup[key]["y"]
            candidates = {
                "opposite": [other for other in row_ids if lookup[other]["y"] != y],
                "same": [other for other in row_ids if other != key and lookup[other]["y"] == y],
            }
            for arm in DONOR_ARMS:  # Registered draw order: opposite, then same.
                pool = candidates[arm]
                if not pool:
                    raise ValueError(f"no eligible {arm} donor for a recipient")
                chosen[arm][key] = pool[int(rng.integers(len(pool)))]
    return {arm: [{"id": item["id"], "feature": item["feature"], "recipient_index": i,
                   "donor_id": chosen[arm][item["id"]], "donor_index": indexed[chosen[arm][item["id"]]]}
                  for i, item in enumerate(items)] for arm in DONOR_ARMS}


def prepare(e19_inputs, labels, registration, out):
    e19_inputs, labels, registration, out = map(Path, (e19_inputs, labels, registration, out))
    data = E19.load(e19_inputs)
    items = data["items"]
    _validate_items(items)
    source = data["provenance"]
    if source.get("experiment") != "E19" or source.get("layer") != 44:
        raise ValueError("E22 requires the frozen E19 block44 inputs")
    acts = data["activations"]
    if acts.ndim != 2 or len(acts) != 420 or not np.isfinite(acts).all():
        raise ValueError("invalid E19 block44 activation array")
    continuations = data["continuations"]
    if continuations["missing_rows"] != ["prose_sentiment"]:
        raise ValueError("E22 continuation scope must match four frozen E15 structure rows")
    for feature in ROWS[:-1]:
        row = continuations["rows"][feature]
        if len(row["pairs"]) != 2 or row["valid_pairs"] is None:
            raise ValueError("frozen E15 pairs/dev-validity decision missing")
    selected_labels, lineage = checked_labels(e19_inputs, labels, items, data["templates"])
    donors = donor_maps(items, selected_labels)
    if "§114" not in registration.read_text() or "E22" not in registration.read_text():
        raise ValueError("expected the frozen §114 E22 registration")
    sidecar = out.with_name(out.name + ".labels.DO_NOT_STAGE.jsonl")
    sidecar_seal = out.with_name(out.name + ".labels.SEAL.json")
    if out.exists() or sidecar.exists() or sidecar_seal.exists():
        raise FileExistsError("E22 input or analysis-label output already exists; do not overwrite a freeze")
    out.mkdir(parents=True, exist_ok=False)
    P.jsonl(sidecar, selected_labels)
    for name in ("items.input.jsonl", "acts44.npy", "templates.json", "continuation_pairs.json", "item_order.json"):
        shutil.copyfile(e19_inputs / name, out / name)
    shutil.copyfile(registration, out / "REGISTRATION.md")
    P.dump(out / "donors.json", donors)
    provenance = {"experiment": "E22", "section": 114, "n_items": 420, "items_per_row": 84,
        "rows": list(ROWS), "layer": 44, "split": "test", "seed": SEED,
        "donor_arms": list(DONOR_ARMS), "donor_draw_order": DRAW_ORDER,
        "labels_staged": False, "labels_sha256": P.sha(sidecar), "orientation": "W1 value A positive; no sign flip",
        "source_e19_input_seal_sha256": P.sha(e19_inputs / "INPUT_SEAL.json"),
        "source_e19_acts44_sha256": P.sha(e19_inputs / "acts44.npy"),
        "source_e19_items_sha256": P.sha(e19_inputs / "items.input.jsonl"),
        "source_e19_item_order_sha256": P.sha(e19_inputs / "item_order.json"),
        "source_e19_continuation_pairs_sha256": P.sha(e19_inputs / "continuation_pairs.json"),
        "registration_sha256": P.sha(registration), "item_order_sha256": P.sha(out / "item_order.json"),
        "missing_continuation_rows": ["prose_sentiment"], "sentiment_endpoint": "asked only; no invented E15 continuation pairs",
        "transform": "exact E19 item order, activation and template bytes retained; only donor controls newly frozen",
        **lineage}
    P.dump(out / "provenance.json", provenance)
    names = ["items.input.jsonl", "acts44.npy", "templates.json", "continuation_pairs.json",
             "item_order.json", "REGISTRATION.md", "donors.json", "provenance.json"]
    P.seal(out, names, "INPUTS_FROZEN_E22_BEFORE_ANY_SCORE")
    P.dump(sidecar_seal, {"status": "E22_ANALYSIS_LABELS_FROZEN_DO_NOT_STAGE",
        "files": {sidecar.name: P.sha(sidecar)}, "input_seal_sha256": P.sha(out / "INPUT_SEAL.json"),
        "source_labels_sha256": lineage["source_labels_sha256"],
        "source_e3_input_seal_sha256": lineage["source_e3_input_seal_sha256"]})
    return {"status": "INPUTS_FROZEN_E22_BEFORE_ANY_SCORE", "path": str(out.resolve()),
            "input_seal_sha256": P.sha(out / "INPUT_SEAL.json"), "n_items": 420,
            "analysis_labels": str(sidecar.resolve()), "analysis_labels_sha256": P.sha(sidecar),
            "analysis_labels_seal": str(sidecar_seal.resolve()), "labels_staged": False}


def load(directory):
    directory = Path(directory)
    _verify(directory, "INPUT_SEAL.json", {"items.input.jsonl", "acts44.npy", "templates.json",
        "continuation_pairs.json", "item_order.json", "REGISTRATION.md", "donors.json", "provenance.json"})
    if list(directory.rglob("*.DO_NOT_STAGE.*")):
        raise ValueError("analysis labels found inside E22 worker package")
    items = P.rows(directory / "items.input.jsonl")
    _validate_items(items)
    if _read(directory / "item_order.json") != [item["id"] for item in items]:
        raise ValueError("E22 item order differs from frozen activation order")
    donors = _read(directory / "donors.json")
    if set(donors) != set(DONOR_ARMS):
        raise ValueError("E22 donor arms are incomplete")
    for arm, records in donors.items():
        if len(records) != len(items):
            raise ValueError("incomplete E22 donor map")
        for i, row in enumerate(records):
            j = row["donor_index"]
            if (type(j) is not int or not 0 <= j < len(items) or j == i or row["recipient_index"] != i
                    or row["id"] != items[i]["id"] or row["donor_id"] != items[j]["id"]
                    or row["feature"] != items[i]["feature"] or items[j]["feature"] != items[i]["feature"]):
                raise ValueError("E22 donor map has self/cross-row/order mismatch")
    acts = np.load(directory / "acts44.npy", allow_pickle=False, mmap_mode="r")
    if acts.ndim != 2 or len(acts) != len(items) or not np.isfinite(acts).all():
        raise ValueError("E22 activation shape/finiteness mismatch")
    return {"items": items, "activations": acts, "templates": _read(directory / "templates.json"),
            "continuations": _read(directory / "continuation_pairs.json"), "donors": donors,
            "provenance": _read(directory / "provenance.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("e19-inputs", "labels", "registration", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(prepare(**vars(parser.parse_args())), indent=2))


if __name__ == "__main__":
    main()
