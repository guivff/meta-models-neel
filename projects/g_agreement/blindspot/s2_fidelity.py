"""§80 S2 entrypoint: reuse the immutable §71/§80 fidelity implementation.

The lens handoff must expose definitions/rows/raw block44 directions and a sealed
bank/target in the scaffold contract. No feature is selected using AR outcomes.
Prepare after the lens feature freeze; collect only on an assigned pod. W2 and
S2 use the SAME frozen fidelity functions and share the conservative 0.3 GPU-h
fidelity allowance. ar_tests.py is never patched or monkeypatched by this runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace

from . import ar_tests as AR
from . import protocol as P

APPROVED_AR_SHA256 = "73a2c2fe6a7f6be5cf93abda0c7fadcf505abc32f2d346e635b068d11d6c7d3b"


def check_source():
    if P.sha(AR.__file__) != APPROVED_AR_SHA256:
        raise ValueError("immutable P3-approved fidelity source changed; new review required")


def definitions_from_registry(registry, w1_templates):
    """All frozen §79 features, plus binary W1 rows; no direction/score gate."""
    definitions = {}
    for row in registry:
        feature = row["id"]
        if feature in definitions:
            raise ValueError("duplicate frozen feature")
        statements = [row["positive"], row["negative"]]
        definitions[feature] = {"row_class": row["class_label"], "values": [True, False],
            "descriptions": statements,
            "statement_pairs": [row["phrasing_pair"],
                [f"At the read position, the current prefix satisfies this statement: {s}." for s in statements]]}
    for feature, spec in w1_templates.items():
        if spec.get("kind", "binary") != "binary":
            continue
        if feature in definitions:
            raise ValueError("W1/S79 feature ID collision")
        if spec.get("score_orientation") != "value_A_positive" or len(spec["olens"]) < 2:
            raise ValueError("W1 rows need two frozen A-positive phrasings")
        definitions[feature] = {"row_class": spec["class"], "values": spec["values"],
            "descriptions": [s.removeprefix("- ") for s in spec["olens"][0]],
            "statement_pairs": spec["olens"][:2]}
    return definitions


def freeze_texts(a):
    """Reconstructor-only inputs: no target activations/directions/reader scores needed."""
    check_source()
    from .stage import git
    started = time.time(); frozen = json.loads(a.freeze.read_text())
    source_commit = git("rev-parse", a.source_ref).decode().strip()
    for path in (a.freeze, a.registry):
        relative = str(path.resolve().relative_to(P.ROOT))
        if hashlib.sha256(git("show", source_commit + ":" + relative)).hexdigest() != P.sha(path):
            raise ValueError("S2 input differs from committed feature freeze")
    registry_name = str(a.registry.resolve().relative_to(P.ROOT))
    if (frozen.get("status") != "FROZEN_BEFORE_CAPTURE"
        or frozen["files"].get(registry_name) != P.sha(a.registry)):
        raise ValueError("registry is not bound to the lens freeze")
    for name, expected in frozen["files"].items():
        if not Path(name).is_absolute() and P.sha(P.ROOT / name) != expected:
            raise ValueError("frozen lens source mismatch: " + name)
    w1 = json.loads(a.w1_templates.read_text())
    w1_seal = json.loads(a.w1_seal.read_text())
    if w1_seal["files"].get(a.w1_templates.name) != P.sha(a.w1_templates):
        raise ValueError("W1 templates differ from their frozen input seal")
    for path in (a.w1_templates, a.w1_seal):
        relative = str(path.resolve().relative_to(P.ROOT))
        if hashlib.sha256(git("show", source_commit + ":" + relative)).hexdigest() != P.sha(path):
            raise ValueError("W1 statement sources must be committed")
    registry = json.loads(a.registry.read_text())
    definitions = definitions_from_registry(registry, w1)
    records, labels = AR.freeze_text_records(definitions)
    a.out.mkdir(parents=True, exist_ok=False)
    P.jsonl(a.out / "texts.input.jsonl", records)
    P.jsonl(a.out / "text_labels.DO_NOT_STAGE.jsonl", labels)
    P.dump(a.out / "definitions.json", definitions)
    P.dump(a.out / "provenance.json", {"lens_freeze_sha256": P.sha(a.freeze),
        "feature_registry_sha256": P.sha(a.registry), "source_feature_commit": source_commit,
        "w1_templates_sha256": P.sha(a.w1_templates), "w1_input_seal_sha256": P.sha(a.w1_seal),
        "labels_sha256": P.sha(a.out / "text_labels.DO_NOT_STAGE.jsonl"),
        "ar_tests_sha256": P.sha(AR.__file__), "wrapper_sha256": P.sha(__file__),
        "s79_features": len(registry), "w1_binary_rows": len(definitions)-len(registry),
        "total_features": len(definitions), "total_texts": len(records),
        "selection": "all registered S79 features, including pre-capture dropped rows, plus all binary W1 rows"})
    P.seal(a.out, ["texts.input.jsonl", "definitions.json", "provenance.json"], "INPUTS_FROZEN_AR_STATEMENTS")
    P.dump(a.out / "run.json", {"step": "s2_freeze_value_texts", "seed": P.SEED,
        "wall_s": time.time()-started, "gpu_hours": 0, "model_forwards": 0,
        "total_features": len(definitions), "total_texts": len(records)})
    print(f"HANDOFF S2 texts: FROZEN; {len(definitions)} features; {len(records)} texts; " + str(a.out / "INPUT_SEAL.json"))


def prepare(a):
    check_source()
    # A committed lens receipt binds the exact frozen feature source, not a time
    # inferred from the clock. The lens owner must provide/commit this receipt.
    frozen = json.loads(a.freeze.read_text())
    if (frozen.get("capture_started") is not False or not isinstance(frozen.get("files"), dict)
        or not any(p.endswith("/features.py") for p in frozen["files"])):
        raise ValueError("requires lens before-capture feature freeze receipt")
    for p, expected in frozen["files"].items():
        if not Path(p).is_absolute():
            path = P.ROOT / p
            if not path.is_file() or P.sha(path) != expected:
                raise ValueError("lens frozen source differs: " + p)
    from .stage import git
    relative = str(a.freeze.resolve().relative_to(P.ROOT))
    committed = git("show", "HEAD:" + relative)
    if hashlib.sha256(committed).hexdigest() != P.sha(a.freeze):
        raise ValueError("commit the exact lens freeze before preparing S2")
    # Fully validate definitions/reference before generating model inputs.
    a.out.mkdir(parents=True, exist_ok=False)
    AR.freeze_reference(SimpleNamespace(bank=a.bank, target=a.target, definitions=a.definitions,
        rows=a.rows, directions=a.directions, evidence=str(a.freeze), out=a.out / "reference"))
    AR.freeze_texts(SimpleNamespace(definitions=a.definitions, out=a.out / "texts"))
    P.dump(a.out / "S2_PREPARED.json", {"status": "PREPARED_NOT_RUN", "section": 80,
        "lens_freeze_sha256": P.sha(a.freeze), "ar_tests_sha256": P.sha(AR.__file__),
        "wrapper_sha256": P.sha(__file__), "text_seal_sha256": P.sha(a.out / "texts/INPUT_SEAL.json"),
        "reference_seal_sha256": P.sha(a.out / "reference/INPUT_SEAL.json"),
        "shared_W2_S2_cap_gpu_hours": .3})


def main(argv=None):
    check_source()
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    text = sub.add_parser("freeze-texts")
    for name in ("freeze", "registry", "w1-templates", "w1-seal", "out"):
        text.add_argument("--" + name, type=Path, required=True)
    text.add_argument("--source-ref", default="origin/r/blindspot")
    prep = sub.add_parser("prepare")
    for name in ("freeze", "bank", "target", "definitions", "rows", "directions", "out"):
        prep.add_argument("--" + name, type=Path, required=True)
    collect = sub.add_parser("collect")
    collect.set_defaults(study="S2")
    for name in ("texts", "assets", "assignment", "official", "whitener", "out"):
        collect.add_argument("--" + name, type=Path, required=True)
    collect.add_argument("--batch", type=int, default=8)
    analysis = sub.add_parser("analyse")
    for name in ("bank", "target", "reference", "texts", "reconstruction", "labels", "text-labels", "out"):
        analysis.add_argument("--" + name, type=Path, required=True)
    sub.add_parser("plan")
    a = p.parse_args(argv)
    if a.action == "freeze-texts": freeze_texts(a)
    elif a.action == "prepare": prepare(a)
    elif a.action == "collect":
        assignment = json.loads(a.assignment.read_text())
        if (assignment.get("experiment") != "S2"
            or assignment.get("entrypoint_files", {}).get("projects/g_agreement/blindspot/s2_fidelity.py") != P.sha(__file__)):
            raise ValueError("S2 assignment must bind its separate entrypoint")
        AR.collect_fidelity(a)
    elif a.action == "analyse":
        AR.analyse_fidelity(a)
        result = json.loads((a.out / "metrics.fidelity.json").read_text())
        print("HANDOFF S2: " + result["S2"]["status"] + "; " + str(a.out / "metrics.fidelity.json"))
    else:
        print(json.dumps({"section": 80, "shared_W2_S2_cap_gpu_hours": .3,
                          "ar_tests_sha256": P.sha(AR.__file__), "wrapper_sha256": P.sha(__file__),
                          "formula_source": "ar_tests.fidelity / ar_tests.s2_decision",
                          "requires": "committed lens freeze, raw44 bank/target/directions, assigned offline AR"}, indent=2))


if __name__ == "__main__":
    main()
