"""Assemble complete, sealed execution units without ever opening labels.

Every unit is checked before output is created. Partial units remain separate;
only an exact, disjoint cover of the frozen bank can become a canonical run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import analysis as A
from . import protocol as P

PHASE_READERS = {"target": (("olens", 44), ("jlens", 44), ("logit", 44)), "nla": (("nla", 42),)}
INPUT_NAMES = {"items.input.jsonl", "templates.json", "provenance.json", "lengths.json",
               "causal.input.json", "sweep.input.json", "decoding.json", "runtime.json", "manifest.json"}
COMMON_FIELDS = ("input_seal_sha256", "assets_sha256", "source_files", "experiment", "batch", "hook")


def _json(path):
    return json.loads(Path(path).read_text())


def _seal(root, name, required, status, allowed=None):
    """Reject unregistered files before hashing, including any label-bearing file."""
    root = Path(root)
    raw = _json(root / name)
    files = raw.get("files", {})
    allowed = set(required) if allowed is None else set(allowed)
    if not isinstance(files, dict) or not set(required) <= set(files) <= allowed:
        raise ValueError(f"{name} lacks required file coverage or contains unregistered files")
    if raw.get("status") != status:
        raise ValueError(f"{name} has wrong stage")
    return P.verify(root, name)


def _score_key(record, index):
    return index[record["id"]], record["reader"], record["layer"], record["arm"]


def _free_unit(bank, root, phase, items, binding, asked_sha, canonical):
    names = (f"unasked.{phase}.jsonl", f"provenance.unasked.{phase}.json")
    seal = _seal(root, "FREE_SEAL.json", names, "UNASKED_COMPLETE_BEFORE_LABEL_JOIN")
    prov = _json(root / names[1])
    if (prov.get("input_seal_sha256") != P.sha(bank / "INPUT_SEAL.json")
            or prov.get("asked_score_seal_sha256") != asked_sha
            or prov.get("expected_per_item_per_reader") != 2
            or prov.get("execution") != binding
            or prov.get("batch") != _json(bank / "runtime.json")["batch"]
            or prov.get("decoding") != _json(bank / "decoding.json")):
        raise ValueError("unit free provenance differs from frozen execution")
    rows = P.rows(root / names[0])
    keys = [(r["id"], r["reader"], r["layer"], r["sample"]) for r in rows]
    expected = {(it["id"], reader, layer, sample) for it in items
                for reader, layer in PHASE_READERS[phase] for sample in (0, 1)}
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("incomplete/duplicate free readout grid")
    for row in rows:
        if row.get("status") not in {"COMPLETE", "EXTRACTION_FAILED"}:
            raise ValueError("unknown free readout collection status")
        if row.get("canonical_index") != canonical[row["id"]]:
            raise ValueError("free readout canonical item index mismatch")
        start = canonical[row["id"]] // prov["batch"] * prov["batch"]
        if row.get("canonical_batch_start") != start:
            raise ValueError("free readout canonical batch mismatch")
        if row["reader"] in {"olens", "nla"}:
            sample = row["sample"]
            if (row.get("seed") != prov["decoding"]["seeds"][sample] + start
                    or row.get("sampling") != prov["decoding"]["samples"][sample]):
                raise ValueError("free readout frozen sampling mismatch")
    receipt = {"path": str(root.resolve()), "free_seal_sha256": P.sha(root / "FREE_SEAL.json"),
               "seal": seal, "provenance": prov}
    return rows, receipt


def assemble(bank, execution_plan, units_root, out):
    """Produce whole-bank target/NLA seals, with optional complete free readouts."""
    from .execution import select_unit, validate_plan

    bank, execution_plan, units_root, out = map(Path, (bank, execution_plan, units_root, out))
    _seal(bank, "INPUT_SEAL.json", INPUT_NAMES, "INPUTS_FROZEN")
    plan = validate_plan(bank, execution_plan)
    runtime_sources = plan.get("runtime_source_files")
    if not isinstance(runtime_sources, dict) or not runtime_sources or runtime_sources != P.code_hashes():
        raise ValueError("execution plan runtime sources differ from current code")
    items = P.rows(bank / "items.input.jsonl")
    item_ids = [it["id"] for it in items]
    if not items or len(set(item_ids)) != len(item_ids):
        raise ValueError("empty bank or duplicate item IDs")
    templates = _json(bank / "templates.json")
    canonical = {key: i for i, key in enumerate(item_ids)}
    experiment = _json(bank / "provenance.json").get("experiment", "W1")
    if experiment not in {"W1", "W1b"}:
        raise ValueError("unexpected bank experiment")
    bank_sha = P.sha(bank / "INPUT_SEAL.json")
    batch = _json(bank / "runtime.json")["batch"]
    all_scores = {phase: [] for phase in PHASE_READERS}
    receipts = {phase: [] for phase in PHASE_READERS}
    free_scores = {phase: [] for phase in PHASE_READERS}
    free_receipts = {phase: [] for phase in PHASE_READERS}
    missing_free = []
    activations, seen, common = {}, set(), None
    free_complete = all((units_root / unit / phase / "FREE_SEAL.json").is_file()
                        for unit in plan["units"] for phase in PHASE_READERS)
    for unit in plan["units"]:
        selection = select_unit(execution_plan, unit, bank, items)
        selected, indices, binding = selection["items"], selection["indices"], selection["binding"]
        ids = [it["id"] for it in selected]
        if not ids or seen.intersection(ids) or indices != [canonical[key] for key in ids]:
            raise ValueError("execution units overlap or have noncanonical indices")
        seen.update(ids)
        subset_templates = {f: templates[f] for f in {it["feature"] for it in selected}}
        target_sha = None
        for phase, readers in PHASE_READERS.items():
            root = units_root / unit / phase
            names = [f"scores.{phase}.jsonl", f"provenance.{phase}.json", "items.order.json"]
            if phase == "target":
                names += ["acts42.npy", "acts44.npy"]
            seal = _seal(root, "SCORE_SEAL.json", names, f"SCORES_SEALED_{phase.upper()}_BEFORE_LABEL_JOIN")
            prov = _json(root / f"provenance.{phase}.json")
            if (prov.get("input_seal_sha256") != bank_sha or prov.get("execution") != binding
                    or prov.get("source_files") != runtime_sources or prov.get("experiment") != experiment
                    or prov.get("batch") != batch or not prov.get("assets_sha256")
                    or not prov.get("assignment_sha256") or not prov.get("hook")):
                raise ValueError("unit asked provenance differs from frozen execution")
            fields = {k: prov[k] for k in COMMON_FIELDS}
            if common is None:
                common = fields
            elif fields != common:
                raise ValueError("unit source/assets/runtime provenance mismatch")
            if A._order(root / "items.order.json") != ids:
                raise ValueError("unit activation item order differs from execution plan")
            sha = P.sha(root / "SCORE_SEAL.json")
            if phase == "target":
                target_sha = sha
            elif prov.get("target_score_seal_sha256") != target_sha:
                raise ValueError("unit NLA points to another target seal")
            rows = P.rows(root / f"scores.{phase}.jsonl")
            A._grid(rows, selected, subset_templates, readers)
            if any(r.get("status") not in {"COMPLETE", "NOT_EVALUABLE_NO_TOKEN_VARIANT"} for r in rows):
                raise ValueError("unit score grid contains an unfinished row")
            if any(r.get("status") != "COMPLETE" and r["reader"] in {"olens", "nla"} for r in rows):
                raise ValueError("generative reader unit is incomplete")
            all_scores[phase].extend(rows)
            receipts[phase].append({"unit": unit, "path": str(root.resolve()), "score_seal_sha256": sha,
                                    "seal": seal, "provenance": prov})
            if phase == "target":
                local = A._load_activations(root, (42, 44), len(selected))
                if local[42].shape != local[44].shape or local[42].dtype != local[44].dtype:
                    raise ValueError("capture layers have different dimensions/dtypes")
                for layer, array in local.items():
                    if array.dtype.kind != "f" or array.shape[1] == 0:
                        raise ValueError("capture requires nonempty floating-point vectors")
                    if layer not in activations:
                        activations[layer] = np.empty((len(items), array.shape[1]), dtype=array.dtype)
                    if activations[layer].shape[1:] != array.shape[1:] or activations[layer].dtype != array.dtype:
                        raise ValueError("unit capture dimensions/dtypes differ")
                    activations[layer][indices] = array
            if free_complete:
                rows, receipt = _free_unit(bank, root, phase, selected, binding, sha, canonical)
                free_scores[phase].extend(rows)
                free_receipts[phase].append({"unit": unit, **receipt})
            elif not (root / "FREE_SEAL.json").is_file():
                missing_free.append({"unit": unit, "phase": phase})
    if seen != set(item_ids):
        raise ValueError("execution units omit frozen items")
    A._grid(all_scores["target"] + all_scores["nla"], items, templates, A.NATIVE)
    # All source evidence is verified before creating any canonical output.
    out.mkdir(parents=True, exist_ok=False)
    assembled_execution = {"execution_plan_sha256": P.sha(execution_plan),
                           "execution_unit": None, "assembled_units": list(plan["units"])}
    for phase in PHASE_READERS:
        root = out / phase
        root.mkdir()
        scores = sorted(all_scores[phase], key=lambda r: _score_key(r, canonical))
        P.jsonl(root / f"scores.{phase}.jsonl", scores)
        P.dump(root / "items.order.json", item_ids)
        prov = {**common, "execution": assembled_execution, "assembly_kind": "EXACT_DISJOINT_FULL_BANK",
                "parent_units": receipts[phase]}
        names = [f"scores.{phase}.jsonl", "items.order.json", f"provenance.{phase}.json"]
        if phase == "target":
            for layer, array in activations.items():
                np.save(root / f"acts{layer}.npy", array, allow_pickle=False)
                names.append(f"acts{layer}.npy")
        else:
            prov["target_score_seal_sha256"] = P.sha(out / "target" / "SCORE_SEAL.json")
        P.dump(root / f"provenance.{phase}.json", prov)
        P.seal(root, names, f"SCORES_SEALED_{phase.upper()}_BEFORE_LABEL_JOIN")
        if free_complete:
            names = [f"unasked.{phase}.jsonl", f"provenance.unasked.{phase}.json"]
            P.jsonl(root / names[0], sorted(free_scores[phase],
                    key=lambda r: (canonical[r["id"]], r["reader"], r["layer"], r["sample"])))
            P.dump(root / names[1], {"input_seal_sha256": bank_sha,
                "asked_score_seal_sha256": P.sha(root / "SCORE_SEAL.json"), "batch": batch,
                "decoding": _json(bank / "decoding.json"), "execution": assembled_execution,
                "judge_status": "PENDING_BLINDED_JUDGE", "expected_per_item_per_reader": 2,
                "parent_units": free_receipts[phase]})
            P.dump(root / "FREE_SEAL.json", {"status": "UNASKED_COMPLETE_BEFORE_LABEL_JOIN",
                                             "files": {name: P.sha(root / name) for name in names}})
    report = {"status": "COMPLETE_ASKED_ASSEMBLY_BEFORE_LABEL_JOIN", "items": len(items),
              "input_seal_sha256": bank_sha, "execution": assembled_execution,
              "free_status": "COMPLETE" if free_complete else "INCOMPLETE_NOT_ASSEMBLED",
              "missing_free": missing_free, "labels_opened": False}
    P.dump(out / "assembly.json", report)
    names = ["assembly.json", "target/SCORE_SEAL.json", "nla/SCORE_SEAL.json"]
    if free_complete:
        names += ["target/FREE_SEAL.json", "nla/FREE_SEAL.json"]
    P.dump(out / "ASSEMBLY_SEAL.json", {"status": report["status"], "files": {n: P.sha(out / n) for n in names}})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bank", "execution-plan", "units-root", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    with P.logged("assemble_execution_units"):
        assemble(args.bank, args.execution_plan, args.units_root, args.out)


if __name__ == "__main__":
    main()
