"""Check S2 delegates to the exact frozen W2/S2 machinery without model work."""
import json
from pathlib import Path

import pytest

from projects.g_agreement.blindspot import s2_fidelity as S


def test_approved_source_is_unchanged():
    S.check_source()
    assert S.P.sha(S.AR.__file__) == S.APPROVED_AR_SHA256


def test_all_frozen_features_and_binary_w1_rows_get_twenty_texts_per_value():
    from collections import Counter
    root = S.P.ROOT
    registry = json.loads((root / "results/g_agreement/blindspot/s79/FEATURE_REGISTRY.json").read_text())
    templates = json.loads((root / "results/g_agreement/blindspot/w1/freeze/templates.json").read_text())
    definitions = S.definitions_from_registry(registry, templates)
    binary = {f for f, spec in templates.items() if spec.get("kind", "binary") == "binary"}
    assert set(definitions) == {r["id"] for r in registry} | binary
    assert len(registry) == 138
    records, labels = S.AR.freeze_text_records(definitions)
    assert len(records) == len(labels) == len(definitions) * 40
    counts = Counter((r["feature"], label["value"]) for r, label in zip(records, labels))
    assert set(counts.values()) == {20}
    by_id = {r["id"]: r for r in registry}
    for f in by_id:
        assert definitions[f]["descriptions"] == [by_id[f]["positive"], by_id[f]["negative"]]
        assert definitions[f]["statement_pairs"][0] == by_id[f]["phrasing_pair"]
    assert not any(spec.get("kind") == "ordinal" and f in definitions for f, spec in templates.items())


def test_frozen_feature_ids_are_unique():
    row = {"id": "f", "class_label": "state-like", "positive": "inside", "negative": "outside", "phrasing_pair": ["inside", "outside"]}
    with pytest.raises(ValueError, match="duplicate"):
        S.definitions_from_registry([row, row], {})


def test_changed_fidelity_source_is_rejected(monkeypatch):
    real_sha = S.P.sha
    monkeypatch.setattr(S.P, "sha", lambda path: "wrong" if str(path) == str(S.AR.__file__) else real_sha(path))
    with pytest.raises(ValueError, match="new review"):
        S.check_source()


def test_collect_delegates_to_same_frozen_function_with_bound_wrapper(tmp_path, monkeypatch):
    receipt = tmp_path / "assignment.json"
    receipt.write_text(json.dumps({"experiment": "S2", "entrypoint_files": {
        "projects/g_agreement/blindspot/s2_fidelity.py": S.P.sha(S.__file__)}}))
    calls = []
    monkeypatch.setattr(S.AR, "collect_fidelity", lambda a: calls.append(a))
    args = ["collect"]
    for name in ("texts", "assets", "official", "whitener", "out"):
        args += ["--" + name, str(tmp_path / name)]
    args += ["--assignment", str(receipt), "--batch", "7"]
    S.main(args)
    assert len(calls) == 1 and calls[0].batch == 7
    assert calls[0].study == "S2"
    assert calls[0].texts == tmp_path / "texts"
    receipt.write_text(json.dumps({"experiment": "S2", "entrypoint_files": {}}))
    with pytest.raises(ValueError, match="bind its separate entrypoint"):
        S.main(args)


def test_analysis_uses_identical_frozen_fidelity_analysis_and_emits_handoff(tmp_path, monkeypatch, capsys):
    def analyse(a):
        a.out.mkdir()
        (a.out / "metrics.fidelity.json").write_text(json.dumps({"S2": {"status": "NOT MET"}}))
    monkeypatch.setattr(S.AR, "analyse_fidelity", analyse)
    args = ["analyse"]
    for name in ("bank", "target", "reference", "texts", "reconstruction", "labels", "text-labels", "out"):
        args += ["--" + name, str(tmp_path / name)]
    S.main(args)
    assert "HANDOFF S2: NOT MET" in capsys.readouterr().out


def test_real_frozen_collector_reaches_final_seal_from_s2_entrypoint(tmp_path, monkeypatch):
    """Regression: AR forwards must not finish with a missing study argument."""
    from contextlib import nullcontext
    import numpy as np
    import torch
    from projects.g_agreement.w_claims import ar as p3

    texts = tmp_path / "texts"; texts.mkdir()
    definitions = {"synthetic": {"row_class": "state-like", "values": [True, False],
                                "descriptions": ["inside parentheses", "outside parentheses"]}}
    records, _ = S.AR.freeze_text_records(definitions)
    S.P.jsonl(texts / "texts.input.jsonl", records)
    S.P.dump(texts / "definitions.json", definitions)
    S.P.dump(texts / "provenance.json", {"synthetic_cpu_contract_only": True})
    S.P.seal(texts, ["texts.input.jsonl", "definitions.json", "provenance.json"], "INPUTS_FROZEN_AR_STATEMENTS")
    assignment = tmp_path / "assignment.json"
    S.P.dump(assignment, {"experiment": "S2", "entrypoint_files": {
        "projects/g_agreement/blindspot/s2_fidelity.py": S.P.sha(S.__file__)}})
    assets = tmp_path / "assets.json"; assets.write_text("{}")
    whitener = tmp_path / "whitener"; whitener.write_text("inert fixture")
    monkeypatch.setattr(S.AR, "_assets", lambda path, names: {"model": "inert", "ar": "inert"})
    monkeypatch.setattr(S.AR, "_compute", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(p3, "load_reconstructor", lambda *args: (None, None, None))
    seen = []
    def reconstruct(model, tokenizer, batch):
        seen.extend(batch)
        return torch.tensor([[float(len(text)), float(text.count("inside")), float(text.count("outside"))]
                             for text in batch])
    monkeypatch.setattr(p3, "reconstruct", reconstruct)
    out = tmp_path / "reconstruction"
    args = ["collect", "--texts", str(texts), "--assets", str(assets), "--assignment", str(assignment),
            "--official", str(tmp_path / "official"), "--whitener", str(whitener), "--out", str(out), "--batch", "7"]
    # S.AR.collect_fidelity is deliberately the actual frozen implementation.
    S.main(args)
    assert seen == [r["text"] for r in records]
    assert S.P.rows(texts / "texts.input.jsonl") == records
    assert json.loads((out / "ids.json").read_text()) == [r["id"] for r in records]
    assert json.loads((out / "provenance.json").read_text())["stage"] == "S2"
    assert set(S.P.verify(out, "SCORE_SEAL.json")["files"]) == {"recon.npy", "ids.json", "provenance.json"}
    assert np.load(out / "recon.npy", allow_pickle=False).shape == (40, 3)
