"""Fabricated tiny arrays exercise assembly integrity; no scientific data/models."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from projects.g_agreement.blindspot import analysis as A
from projects.g_agreement.blindspot import assemble as M
from projects.g_agreement.blindspot import execution as E
from projects.g_agreement.blindspot import protocol as P


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    sources = {"fixture.py": "a" * 64}
    monkeypatch.setattr(P, "code_hashes", lambda: sources)
    bank, units = tmp_path / "bank", tmp_path / "units"
    bank.mkdir()
    features = list(E.PRIORITY_FEATURES) + ["python_line", "table_column_ordinal"] + [f"fixture{i}" for i in range(11)]
    templates = {f: {"kind": "ordinal" if f.endswith("ordinal") else "binary",
                     "class": "semantic", "domain": "fixture", "values": ["A", "B"],
                     **{r: [["A", "B"], ["a", "b"]] for r, _ in A.NATIVE}} for f in features}
    # Interleave rows so concatenating units would silently scramble activations.
    items = [{"id": f"{f}-{side}", "feature": f, "ids": [1, 2],
              "donor_id": None if f.endswith("ordinal") else f"{f}-{1-side}"}
             for side in (0, 1) for f in features]
    P.jsonl(bank / "items.input.jsonl", items)
    P.dump(bank / "templates.json", templates)
    P.dump(bank / "provenance.json", {"experiment": "W1", "labels_sha256": "f" * 64})
    P.dump(bank / "manifest.json", {"experiment": "W1", "source_files": sources,
        "rows": {f: {"n": 2, "split_counts": {"dev": 1, "test": 1}} for f in features}})
    P.dump(bank / "decoding.json", P.DECODING)
    P.dump(bank / "runtime.json", {"batch": 32})
    for name in ("lengths.json", "causal.input.json", "sweep.input.json"):
        P.dump(bank / name, [])
    P.seal(bank, sorted(M.INPUT_NAMES), "INPUTS_FROZEN")
    feature_order, layout = E._layout(items)
    plan = {"schema": E.SCHEMA, "status": "FROZEN", "experiment": "W1",
        "input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"), "manifest_sha256": P.sha(bank / "manifest.json"),
        "items_input_sha256": P.sha(bank / "items.input.jsonl"), "templates_sha256": P.sha(bank / "templates.json"),
        "feature_order": feature_order, "units": layout, "modes": E.MODES,
        "training_labels": {"sha256": "e" * 64, "relative_path": E.TRAINING_FILE, "count": 5},
        "runtime_source_files": sources, "baseline_source_files": sources,
        "baseline_source_commit": "b" * 40, "source_policy": E.SOURCE_POLICY,
        "free_batch_policy": "canonical_batch_intersections"}
    plan_path = tmp_path / "execution.json"
    P.dump(plan_path, plan)
    for unit in E.UNITS:
        selected = E.select_unit(plan_path, unit, bank, items)
        for phase, readers in M.PHASE_READERS.items():
            root = units / unit / phase
            root.mkdir(parents=True)
            rows = []
            for it in selected["items"]:
                for reader, layer in readers:
                    arms = ("true",) if templates[it["feature"]]["kind"] == "ordinal" else ("true", "mismatched")
                    rows.extend({"id": it["id"], "reader": reader, "layer": layer, "arm": arm,
                                 "scores": [float(items.index(it)), 1.], "status": "COMPLETE"} for arm in arms)
            P.jsonl(root / f"scores.{phase}.jsonl", list(reversed(rows)))
            P.dump(root / "items.order.json", [it["id"] for it in selected["items"]])
            prov = {"input_seal_sha256": plan["input_seal_sha256"], "assets_sha256": "c" * 64,
                "assignment_sha256": "d" * 64, "source_files": sources, "experiment": "W1", "batch": 32,
                "hook": "zero-based decoder block output, raw last-prefix-token state", "execution": selected["binding"]}
            names = [f"scores.{phase}.jsonl", f"provenance.{phase}.json", "items.order.json"]
            if phase == "target":
                for layer in (42, 44):
                    np.save(root / f"acts{layer}.npy", np.array([[i, layer] for i in selected["indices"]], np.float32))
                    names.append(f"acts{layer}.npy")
            else:
                prov["target_score_seal_sha256"] = P.sha(units / unit / "target" / "SCORE_SEAL.json")
            P.dump(root / f"provenance.{phase}.json", prov)
            P.seal(root, names, f"SCORES_SEALED_{phase.upper()}_BEFORE_LABEL_JOIN")
    return SimpleNamespace(bank=bank, plan=plan_path, units=units, out=tmp_path / "assembled", items=items, templates=templates)


def reseal(root, phase):
    names = json.loads((root / "SCORE_SEAL.json").read_text())["files"]
    P.seal(root, list(names), f"SCORES_SEALED_{phase.upper()}_BEFORE_LABEL_JOIN")


def call(f):
    return M.assemble(f.bank, f.plan, f.units, f.out)


def add_free(f):
    for unit in E.UNITS:
        selected = E.select_unit(f.plan, unit, f.bank, f.items)
        for phase, readers in M.PHASE_READERS.items():
            root = f.units / unit / phase
            rows = []
            for it, i in zip(selected["items"], selected["indices"]):
                for reader, layer in readers:
                    for sample in (0, 1):
                        row = {"id": it["id"], "reader": reader, "layer": layer, "sample": sample,
                            "text": "a fixture readout", "status": "COMPLETE", "canonical_index": i,
                            "canonical_batch_start": i // 32 * 32}
                        if reader in {"olens", "nla"}:
                            row.update(seed=P.DECODING["seeds"][sample] + i // 32 * 32, sampling=P.DECODING["samples"][sample])
                        rows.append(row)
            names = [f"unasked.{phase}.jsonl", f"provenance.unasked.{phase}.json"]
            P.jsonl(root / names[0], rows)
            P.dump(root / names[1], {"input_seal_sha256": P.sha(f.bank / "INPUT_SEAL.json"),
                "asked_score_seal_sha256": P.sha(root / "SCORE_SEAL.json"), "expected_per_item_per_reader": 2,
                "execution": selected["binding"], "batch": 32, "decoding": P.DECODING})
            P.dump(root / "FREE_SEAL.json", {"status": "UNASKED_COMPLETE_BEFORE_LABEL_JOIN",
                                             "files": {n: P.sha(root / n) for n in names}})


def test_canonical_assembly_preserves_vectors_lineage_and_is_accepted_before_label_join(fixture, monkeypatch):
    f = fixture
    original = Path.open
    def no_labels(path, *args, **kwargs):
        assert "DO_NOT_STAGE" not in path.name, "assembler opened labels"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", no_labels)
    report = call(f)
    assert report["items"] == len(f.items) and report["labels_opened"] is False
    assert report["free_status"] == "INCOMPLETE_NOT_ASSEMBLED"
    assert not (f.out / "target" / "FREE_SEAL.json").exists()
    for layer in (42, 44):
        h = np.load(f.out / "target" / f"acts{layer}.npy")
        assert h[:, 0].tolist() == list(range(len(f.items)))
        assert np.all(h[:, 1] == layer)
    prov = json.loads((f.out / "nla" / "provenance.nla.json").read_text())
    assert len(prov["parent_units"]) == 3
    assert prov["target_score_seal_sha256"] == P.sha(f.out / "target" / "SCORE_SEAL.json")
    P.verify(f.out, "ASSEMBLY_SEAL.json")
    class ReachedLabelJoin(Exception):
        pass
    def label_boundary(*args):
        raise ReachedLabelJoin
    monkeypatch.setattr(A, "_labels", label_boundary)
    with pytest.raises(ReachedLabelJoin):
        A.analyse(SimpleNamespace(bank=f.bank, target=f.out / "target", nla=f.out / "nla",
                                  labels=f.bank / "labels.DO_NOT_STAGE.jsonl", out=f.out / "analysis"))


@pytest.mark.parametrize("mutation,match", [
    ("binding", "frozen execution"), ("assets", "provenance mismatch"),
    ("missing_score", "score grid"), ("duplicate_score", "score grid"),
    ("order", "item order"), ("dimensions", "dimensions/dtypes"),
    ("nan", "shape/finiteness"), ("unfinished", "unfinished"), ("nla_lineage", "another target"),
])
def test_corrupt_unit_never_creates_canonical_output(fixture, mutation, match):
    f = fixture
    phase = "nla"
    root = f.units / "remainder_b" / phase
    if mutation in {"dimensions", "nan"}:
        phase, root = "target", f.units / "remainder_b" / "target"
        value = np.load(root / "acts44.npy")
        if mutation == "dimensions":
            value = np.column_stack([value, value[:, 0]])
        else:
            value[0, 0] = np.nan
        np.save(root / "acts44.npy", value)
    elif mutation in {"binding", "assets", "nla_lineage"}:
        path = root / "provenance.nla.json"
        value = json.loads(path.read_text())
        if mutation == "binding": value["execution"]["execution_unit"] = "priority"
        elif mutation == "assets": value["assets_sha256"] = "0" * 64
        else: value["target_score_seal_sha256"] = "0" * 64
        P.dump(path, value)
    elif mutation == "order":
        path = root / "items.order.json"
        P.dump(path, list(reversed(json.loads(path.read_text()))))
    else:
        path = root / "scores.nla.jsonl"
        value = P.rows(path)
        if mutation == "missing_score": value.pop()
        elif mutation == "duplicate_score": value.append(deepcopy(value[0]))
        else: value[0].update(status="INTERRUPTED", scores=None)
        path.unlink()
        P.jsonl(path, value)
    reseal(root, phase)
    with pytest.raises(ValueError, match=match):
        call(f)
    assert not f.out.exists()


def test_unregistered_label_in_seal_is_rejected_without_opening_it(fixture, monkeypatch):
    f = fixture
    seal = json.loads((f.bank / "INPUT_SEAL.json").read_text())
    seal["files"]["labels.DO_NOT_STAGE.jsonl"] = "f" * 64
    P.dump(f.bank / "INPUT_SEAL.json", seal)
    original = Path.open
    def no_labels(path, *args, **kwargs):
        assert "DO_NOT_STAGE" not in path.name
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", no_labels)
    with pytest.raises(ValueError, match="unregistered files"):
        call(f)
    assert not f.out.exists()


def test_changed_partition_cannot_be_assembled(fixture):
    f = fixture
    plan = json.loads(f.plan.read_text())
    plan["units"]["remainder_a"]["item_ids"] += plan["units"]["priority"]["item_ids"][:1]
    P.dump(f.plan, plan)
    with pytest.raises(ValueError, match="partition"):
        call(f)
    assert not f.out.exists()


def test_runtime_code_change_cannot_reuse_old_plan(fixture, monkeypatch):
    f = fixture
    monkeypatch.setattr(P, "code_hashes", lambda: {"fixture.py": "b" * 64})
    with pytest.raises(ValueError, match="runtime sources"):
        call(f)
    assert not f.out.exists()


def test_missing_unit_seal_cannot_produce_partial_canonical_run(fixture):
    f = fixture
    (f.units / "remainder_b" / "nla" / "SCORE_SEAL.json").unlink()
    with pytest.raises(FileNotFoundError):
        call(f)
    assert not f.out.exists()


def test_all_free_readouts_merge_with_new_asked_lineage(fixture):
    from projects.g_agreement.blindspot import recall
    f = fixture
    add_free(f)
    report = call(f)
    assert report["free_status"] == "COMPLETE"
    rows = recall._readouts(f.bank, f.out / "target", f.out / "nla", f.items)
    assert len(rows) == len(f.items) * 4 * 2
    for phase in M.PHASE_READERS:
        P.verify(f.out / phase, "FREE_SEAL.json")
        provenance = json.loads((f.out / phase / f"provenance.unasked.{phase}.json").read_text())
        assert len(provenance["parent_units"]) == 3


def test_partial_free_collection_is_not_faked(fixture):
    f = fixture
    add_free(f)
    (f.units / "remainder_b" / "nla" / "FREE_SEAL.json").unlink()
    report = call(f)
    assert report["missing_free"] == [{"unit": "remainder_b", "phase": "nla"}]
    assert not (f.out / "target" / "FREE_SEAL.json").exists()
    assert not (f.out / "nla" / "FREE_SEAL.json").exists()


def test_complete_free_claim_with_missing_record_fails_before_output(fixture):
    f = fixture
    add_free(f)
    root = f.units / "priority" / "nla"
    rows = P.rows(root / "unasked.nla.jsonl")[:-1]
    (root / "unasked.nla.jsonl").unlink()
    P.jsonl(root / "unasked.nla.jsonl", rows)
    seal = json.loads((root / "FREE_SEAL.json").read_text())
    seal["files"]["unasked.nla.jsonl"] = P.sha(root / "unasked.nla.jsonl")
    P.dump(root / "FREE_SEAL.json", seal)
    with pytest.raises(ValueError, match="free readout grid"):
        call(f)
    assert not f.out.exists()
