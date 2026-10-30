"""Label-free E19 input preparation from E3 and E15's frozen inputs.

Only frozen split metadata is consulted. This module never opens a label file,
fits a direction, runs a model, or chooses wording. Missing E15 wording remains
an explicit unavailable endpoint; it is never replaced with authored wording.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from projects.g_agreement.blindspot import protocol as P

ROWS = ("prose_paren", "python_string", "table_role", "python_depth", "prose_sentiment")
DONOR_SEED = 20261025
RANDOM_DIRECTION_SEEDS = (20261025, 20261026, 20261027)
ALPHAS = (0, -1, 1, -2, 2, -4, 4)


def _read(path):
    return json.loads(Path(path).read_text())


def _verify(directory, filename, required):
    seal = P.verify(directory, filename)
    if not set(required) <= set(seal["files"]):
        raise ValueError(f"{filename} lacks required file coverage")
    return seal


def metadata_only(line):
    """Decode only top-level ID/group metadata; lexically skip every other value.

    The canonical W1 item records also contain truth and source text. Unlike a
    full json.loads call, this scanner never decodes those values (or nested
    metadata). No label file is read. Inputs are hash-verified upstream bytes.
    """
    wanted = {"id", "feature", "split", "cluster"}
    decoder = json.JSONDecoder()
    pos, result = 0, {}
    def whitespace(index):
        while index < len(line) and line[index].isspace():
            index += 1
        return index
    pos = whitespace(pos)
    if pos >= len(line) or line[pos] != "{":
        raise ValueError("W1 item must be a JSON object")
    pos += 1
    while True:
        pos = whitespace(pos)
        if pos >= len(line):
            raise ValueError("unterminated W1 item")
        if line[pos] == "}":
            break
        key, pos = decoder.raw_decode(line, pos)
        if not isinstance(key, str):
            raise ValueError("invalid W1 item key")
        pos = whitespace(pos)
        if pos >= len(line) or line[pos] != ":":
            raise ValueError("missing W1 item colon")
        start = pos = whitespace(pos + 1)
        depth, quoted, escape = 0, False, False
        while pos < len(line):
            char = line[pos]
            if quoted:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
            elif char in "]}":
                if depth == 0:
                    break
                depth -= 1
            elif char == "," and depth == 0:
                break
            pos += 1
        if key in wanted:
            if key in result:
                raise ValueError("duplicate W1 metadata key")
            value = decoder.decode(line[start:pos].strip())
            if not isinstance(value, str) or not value:
                raise ValueError("W1 grouping metadata must be nonempty strings")
            result[key] = value
        if pos >= len(line):
            raise ValueError("unterminated W1 item value")
        if line[pos] == "}":
            break
        pos += 1
    if set(result) != wanted:
        raise ValueError("W1 item lacks exact template-group metadata")
    return result


def cluster_metadata(w1_bank, expected_input_seal, selected_items):
    if w1_bank is None:
        raise ValueError("canonical W1 bank required for frozen template clusters")
    w1_bank = Path(w1_bank)
    _verify(w1_bank, "INPUT_SEAL.json", {"manifest.json"})
    if P.sha(w1_bank / "INPUT_SEAL.json") != expected_input_seal:
        raise ValueError("W1 grouping source differs from the E3 input lineage")
    manifest = _read(w1_bank / "manifest.json")
    full_items = w1_bank / "items.DO_NOT_STAGE.jsonl"
    source_hash = P.sha(full_items)
    if manifest["files"][full_items.name] != source_hash:
        raise ValueError("W1 canonical item metadata hash mismatch")
    needed = {item["id"]: item for item in selected_items}
    groups = {}
    with full_items.open() as stream:
        for line in stream:
            if not line.strip():
                continue
            meta = metadata_only(line)
            if meta["id"] not in needed:
                continue
            item = needed[meta["id"]]
            if meta["id"] in groups or meta["feature"] != item["feature"] or meta["split"] != "test":
                raise ValueError("W1 group metadata conflicts with selected E3 items")
            groups[meta["id"]] = meta["cluster"]
    if set(groups) != set(needed):
        raise ValueError("W1 cluster metadata does not cover every E19 test item")
    for feature in ROWS:
        counts = Counter(groups[item["id"]] for item in selected_items if item["feature"] == feature)
        if len(counts) != 6 or set(counts.values()) != {14}:
            raise ValueError("expected six frozen W1 test template clusters of 14 items")
    return groups, {"source_w1_manifest_sha256": P.sha(w1_bank / "manifest.json"),
                    "source_w1_canonical_items_sha256": source_hash,
                    "cluster_extraction": "lexically decode top-level id/feature/split/cluster only; skip value/text/meta without decoding; no labels file opened"}


def donor_map(items, seed=DONOR_SEED):
    """One independently sampled nonself donor in each recipient's row.

    Candidates are sorted by opaque item ID. RNG consumption follows sorted
    feature/recipient IDs, so an input-row reorder cannot change the donor IDs.
    Sampling is with replacement across recipients and never consults labels.
    """
    ids = [it["id"] for it in items]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate E19 item IDs")
    indexed = {it["id"]: i for i, it in enumerate(items)}
    rng = np.random.default_rng(seed)
    donors = {}
    for feature in sorted({it["feature"] for it in items}):
        pool = sorted(it["id"] for it in items if it["feature"] == feature)
        if len(pool) < 2:
            raise ValueError("nonself random donors require at least two items per row")
        for item_id in pool:
            eligible = [key for key in pool if key != item_id]
            donors[item_id] = eligible[int(rng.integers(len(eligible)))]
    return [{"id": it["id"], "feature": it["feature"], "recipient_index": i,
             "donor_id": donors[it["id"]], "donor_index": indexed[donors[it["id"]]]}
            for i, it in enumerate(items)]


def continuation_contract(e15_stage, e15_analysis=None, e15_scores=None):
    e15_stage = Path(e15_stage)
    _verify(e15_stage, "INPUT_SEAL.json", {"pairs.json", "plan.json"})
    frozen = _read(e15_stage / "pairs.json")
    if frozen.get("section") != 105 or frozen.get("oracle_prefix") != "- ":
        raise ValueError("unexpected E15 registration or native Oracle prefix")
    rows, unavailable = {}, []
    for feature in ROWS:
        source = frozen["rows"].get(feature)
        if source is None:
            unavailable.append(feature)
            rows[feature] = {"status": "NOT_APPLICABLE_NO_FROZEN_E15_PAIRS", "pairs": [],
                             "valid_pairs": [], "primary_status": "NOT_EVALUABLE"}
            continue
        pairs = source["pairs"]
        if len(pairs) != 2:
            raise ValueError("E15 requires its original two continuation pairs")
        for pair in pairs:
            n = pair["tokens_per_candidate"]
            if (type(n) is not int or not 1 <= n <= 4 or len(pair["A_ids"]) != n
                    or len(pair["B_ids"]) != n or not pair["A"] or not pair["B"]):
                raise ValueError("invalid E15 equal-token pair")
        rows[feature] = {**source, "status": "FROZEN_E15_PAIRS",
                         "valid_pairs": None, "primary_status": "PENDING_E15_DEV_VALIDITY"}
    analysis_hash, score_hash = None, None
    if e15_analysis is not None:
        if e15_scores is None:
            raise ValueError("E15 dev validity requires its sealed score/input lineage")
        e15_analysis = Path(e15_analysis)
        e15_scores = Path(e15_scores)
        _verify(e15_analysis, "ANALYSIS_SEAL.json", {"metrics.json"})
        _verify(e15_scores, "SCORE_SEAL.json", {"provenance.json"})
        metrics = _read(e15_analysis / "metrics.json")
        score_hash = P.sha(e15_scores / "SCORE_SEAL.json")
        if (metrics.get("experiment") != "E15" or metrics["score_seal_sha256"] != score_hash
                or _read(e15_scores / "provenance.json")["input_seal_sha256"] != P.sha(e15_stage / "INPUT_SEAL.json")
                or metrics["labels_sha256"] != _read(e15_stage / "plan.json")["labels_sha256"]):
            raise ValueError("E15 dev validity source/input lineage mismatch")
        by_feature = {row["feature"]: row for row in metrics["rows"]}
        if len(by_feature) != len(metrics["rows"]):
            raise ValueError("duplicate E15 validity rows")
        # Import only the frozen dev validity decision, never E15 test metrics.
        for feature in set(ROWS) - set(unavailable):
            source = by_feature[feature]
            aucs, valid = source["base_dev_pair_auroc"], source["valid_pairs"]
            if len(aucs) != 2 or valid != [i for i, value in enumerate(aucs) if value is not None and np.isfinite(value) and value >= .80]:
                raise ValueError("E15 pair validity differs from its registered dev rule")
            rows[feature].update({"base_dev_pair_auroc": aucs, "valid_pairs": valid,
                                 "primary_status": "EVALUABLE" if valid else "NOT_EVALUABLE"})
        analysis_hash = P.sha(e15_analysis / "ANALYSIS_SEAL.json")
    return {"source_section": 105, "oracle_prefix": "- ", "orientation": frozen["orientation"],
            "rows": rows, "missing_rows": unavailable,
            "primary_aggregation": "mean of E15 dev-valid pairs; no valid pair means NOT EVALUABLE",
            "descriptive_aggregation": "retain each original pair and the mean of both; no wording replacement",
            "source_input_seal_sha256": P.sha(e15_stage / "INPUT_SEAL.json"),
            "source_pairs_sha256": P.sha(e15_stage / "pairs.json"),
            "source_analysis_seal_sha256": analysis_hash, "source_score_seal_sha256": score_hash}


def prepare(e3_inputs, e15_stage, registration, out, e15_analysis=None, e15_scores=None, w1_bank=None):
    e3_inputs, e15_stage, registration, out = map(Path, (e3_inputs, e15_stage, registration, out))
    _verify(e3_inputs, "INPUT_SEAL.json", {"items.input.jsonl", "templates.json", "acts44.npy", "provenance.json"})
    source_provenance = _read(e3_inputs / "provenance.json")
    if source_provenance["experiment"] != "E3":
        raise ValueError("E19 must reuse E3's frozen inputs")
    source_items = P.rows(e3_inputs / "items.input.jsonl")
    if len({it["id"] for it in source_items}) != len(source_items):
        raise ValueError("duplicate E3 item IDs")
    allowed = {"id", "feature", "ids", "split", "parent_index"}
    if any(set(it) != allowed for it in source_items):
        raise ValueError("unexpected or label-bearing E3 item fields")
    selection = [i for i, it in enumerate(source_items) if it["feature"] in ROWS and it["split"] == "test"]
    if Counter(source_items[i]["feature"] for i in selection) != {feature: 84 for feature in ROWS}:
        raise ValueError("E19 requires all 84 test items in each registered row")
    acts = np.load(e3_inputs / "acts44.npy", allow_pickle=False, mmap_mode="r")
    if acts.ndim != 2 or len(acts) != len(source_items) or not np.isfinite(acts).all():
        raise ValueError("E3 block44 activation shape/finiteness mismatch")
    source_templates = _read(e3_inputs / "templates.json")
    templates = {}
    for feature in ROWS:
        spec = source_templates[feature]
        pairs = spec["olens"]
        if (spec.get("score_orientation") != "value_A_positive" or len(pairs) != 2
                or any(len(pair) != 2 for pair in pairs)):
            raise ValueError("W1's two A-positive asked pairs must be retained exactly")
        templates[feature] = spec
    continuation = continuation_contract(e15_stage, e15_analysis, e15_scores)
    groups, grouping_provenance = cluster_metadata(
        w1_bank, source_provenance["w1_input_seal_sha256"], [source_items[i] for i in selection])
    registration_text = registration.read_text()
    if "§111" not in registration_text or "E19" not in registration_text:
        raise ValueError("expected the frozen §111 E19 registration")
    out.mkdir(parents=True, exist_ok=False)
    items = [{**source_items[i], "e3_index": i, "cluster": groups[source_items[i]["id"]]} for i in selection]
    P.jsonl(out / "items.input.jsonl", items)
    np.save(out / "acts44.npy", acts[selection], allow_pickle=False)
    P.dump(out / "templates.json", templates)
    P.dump(out / "continuation_pairs.json", continuation)
    P.dump(out / "random_donors.json", donor_map(items))
    P.dump(out / "random_seeds.json", {"donor_seed": DONOR_SEED,
        "random_direction_seeds": list(RANDOM_DIRECTION_SEEDS),
        "algorithm": "numpy default_rng PCG64; donors sampled independently with replacement across recipients from sorted same-row nonself IDs"})
    P.dump(out / "item_order.json", [it["id"] for it in items])
    provenance = {"experiment": "E19", "section": 111, "rows": list(ROWS), "n_items": len(items),
        "items_per_row": 84, "split": "test", "layer": 44, "alphas": list(ALPHAS),
        "source_e3_input_seal_sha256": P.sha(e3_inputs / "INPUT_SEAL.json"),
        "source_e3_items_sha256": P.sha(e3_inputs / "items.input.jsonl"),
        "source_e3_acts44_sha256": P.sha(e3_inputs / "acts44.npy"),
        "source_w1_input_seal_sha256": source_provenance.get("w1_input_seal_sha256"),
        "source_e15_input_seal_sha256": P.sha(e15_stage / "INPUT_SEAL.json"),
        "source_e15_pairs_sha256": P.sha(e15_stage / "pairs.json"),
        "registration_sha256": P.sha(registration), "item_order_sha256": P.sha(out / "item_order.json"),
        "selection": "all registered five-row W1 test IDs, in original E3-relative order; no label file read",
        **grouping_provenance,
        "transform": "block44 row selection only; no centring, whitening or rescaling",
        "random_donor": "one fixed same-row nonself donor per test recipient; label-independent; not W1 opposite-value donor",
        "missing_continuation_rows": continuation["missing_rows"], "labels_read": False, "labels_staged": False,
        "directions_status": "DEV_ONLY_DIRECTION_FREEZE_REQUIRED_SEPARATELY",
        "status": "INPUTS_FROZEN_WITH_UNAVAILABLE_ENDPOINTS" if continuation["missing_rows"] else "INPUTS_FROZEN"}
    P.dump(out / "provenance.json", provenance)
    names = ["items.input.jsonl", "acts44.npy", "templates.json", "continuation_pairs.json",
             "random_donors.json", "random_seeds.json", "item_order.json", "provenance.json"]
    P.seal(out, names, "INPUTS_FROZEN_E19_BEFORE_TEST_SCORING")
    return {"status": provenance["status"], "path": str(out.resolve()), "input_seal_sha256": P.sha(out / "INPUT_SEAL.json"),
            "n_items": len(items), "rows": list(ROWS), "missing_continuation_rows": continuation["missing_rows"],
            "source_e3_inputs": str(e3_inputs.resolve()), "source_e15_stage": str(e15_stage.resolve()),
            "source_registration": str(registration.resolve()), "labels_read": False}


def load(directory):
    directory = Path(directory)
    _verify(directory, "INPUT_SEAL.json", {"items.input.jsonl", "acts44.npy", "templates.json", "continuation_pairs.json",
            "random_donors.json", "random_seeds.json", "item_order.json", "provenance.json"})
    items = P.rows(directory / "items.input.jsonl")
    if _read(directory / "item_order.json") != [it["id"] for it in items]:
        raise ValueError("frozen E19 item order mismatch")
    donors = _read(directory / "random_donors.json")
    if donors != donor_map(items, _read(directory / "random_seeds.json")["donor_seed"]):
        raise ValueError("frozen donors differ from seeded same-row nonself rule")
    return {"items": items, "activations": np.load(directory / "acts44.npy", allow_pickle=False, mmap_mode="r"),
            "templates": _read(directory / "templates.json"), "continuations": _read(directory / "continuation_pairs.json"),
            "donors": donors, "random_seeds": _read(directory / "random_seeds.json"),
            "provenance": _read(directory / "provenance.json")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("e3-inputs", "e15-stage", "registration", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--e15-analysis", type=Path)
    p.add_argument("--e15-scores", type=Path)
    p.add_argument("--w1-bank", type=Path, required=True)
    print(json.dumps(prepare(**vars(p.parse_args())), indent=2))


if __name__ == "__main__":
    main()
