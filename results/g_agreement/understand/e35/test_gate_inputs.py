"""CPU-only E35 sample integrity checks, dated 2026-10-25."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


_spec = importlib.util.spec_from_file_location(
    "e35_gate_inputs", Path(__file__).with_name("gate_inputs.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def group_id(heldout):
    return next(f"group-{i}" for i in range(1000)
                if G.is_heldout(f"group-{i}") is heldout)


def record(doc_id, group, text, domain="prose"):
    return {"id": doc_id, "group_id": group, "text": text,
            "text_sha256": G.digest(text), "domain": domain}


def encode(text):
    return list(range(len(text)))


def selected_pairs(sample):
    return [(r["id"], p) for r in sample["documents"] for p in r["positions"]]


def small_rows():
    held, train = group_id(True), group_id(False)
    return [
        record("held-a", held, "a" * 15),
        record("held-b", held, "b" * 18, "python"),
        record("held-short", held, "cc", "markdown"),
        record("train-a", train, "d" * 14),
        record("train-b", train, "e" * 13),
        record("train-c", train, "f" * 12),
    ]


def test_production_constants_and_exact_50000_without_replacement():
    assert G.N_TOKENS == 50_000
    assert G.MAX_LENGTH == 512
    assert G.SEED == 20261025
    held, train = group_id(True), group_id(False)
    rows = [record(f"held-{i:03d}", held, "x" * 600) for i in range(100)]
    rows += [record(f"train-{i}", train, "y" * 600) for i in range(3)]
    sample = G.make_sample(rows, encode)
    pairs = selected_pairs(sample)
    assert len(pairs) == len(set(pairs)) == 50_000
    assert sample["inventory"]["heldout_prefix_tokens"] == 51_200
    assert all(0 <= p < 512 for _, p in pairs)
    assert all(r["prefix_tokens"] == 512 for r in sample["documents"])
    assert G.make_sample(list(reversed(rows)), encode) == sample


def test_group_split_is_disjoint_and_selection_uses_lowest_token_hashes(monkeypatch):
    monkeypatch.setattr(G, "N_TOKENS", 7)
    monkeypatch.setattr(G, "MAX_LENGTH", 8)
    rows = small_rows()
    sample = G.make_sample(rows, encode)
    by_id = {r["id"]: r for r in rows}
    held_groups = {r["group_id"] for r in rows if G.is_heldout(r["group_id"])}
    assert set(sample["excluded_training_group_ids"]) == held_groups
    pilot_groups = {by_id[k]["group_id"] for k in sample["pilot_document_ids"]}
    assert held_groups.isdisjoint(pilot_groups)
    assert len(sample["pilot_document_ids"]) == len(set(sample["pilot_document_ids"])) == 3
    pool = [(G.token_rank(r["id"], p), r["id"], p)
            for r in rows if G.is_heldout(r["group_id"])
            for p in range(min(8, len(r["text"])))]
    expected = {(doc, p) for _, doc, p in sorted(pool)[:7]}
    assert set(selected_pairs(sample)) == expected
    assert all(r["positions"] == sorted(set(r["positions"])) for r in sample["documents"])
    assert sum(sample["inventory"]["selected_tokens_by_domain"].values()) == 7


def test_label_fields_do_not_change_selection_or_leak_into_sample(monkeypatch):
    monkeypatch.setattr(G, "N_TOKENS", 7)
    monkeypatch.setattr(G, "MAX_LENGTH", 8)
    rows = small_rows()
    reference = G.make_sample(rows, encode)
    labelled = copy.deepcopy(rows)
    for i, r in enumerate(labelled):
        r.update({"labels": {"secret-feature": i % 2}, "reader_score": float(i),
                  "feature": "W1-row-that-must-not-be-used", "sae_score": 999})
    assert G.make_sample(labelled, encode) == reference
    serialized = G.canonical(reference)
    assert "secret-feature" not in serialized
    assert "W1-row-that-must-not-be-used" not in serialized
    assert "reader_score" not in serialized


def test_context_hash_is_full_prefix_not_only_selected_tokens(monkeypatch):
    monkeypatch.setattr(G, "N_TOKENS", 1)
    monkeypatch.setattr(G, "MAX_LENGTH", 8)
    rows = small_rows()
    # Make position 0 of held-a win, so a truncated-at-read-token bug is visible.
    original_rank = G.token_rank
    monkeypatch.setattr(G, "token_rank", lambda doc, p:
                        "0" * 64 if (doc, p) == ("held-a", 0)
                        else "f" + original_rank(doc, p)[1:])
    sample = G.make_sample(rows, encode)
    assert len(sample["documents"]) == 1
    r = sample["documents"][0]
    assert r["positions"] == [0]
    assert r["prefix_tokens"] == 8
    assert r["prefix_ids_sha256"] == G.digest(G.canonical(list(range(8))))


def test_insufficient_holdout_or_full_length_pilots_fail_without_reseed(monkeypatch):
    monkeypatch.setattr(G, "N_TOKENS", 19)
    monkeypatch.setattr(G, "MAX_LENGTH", 8)
    with pytest.raises(ValueError, match="insufficient held-out"):
        G.make_sample(small_rows(), encode)
    monkeypatch.setattr(G, "N_TOKENS", 7)
    rows = small_rows()
    rows[-1]["text"] = "f"
    with pytest.raises(ValueError, match="full-length training pilot"):
        G.make_sample(rows, encode)


@pytest.fixture
def frozen_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "N_TOKENS", 7)
    monkeypatch.setattr(G, "MAX_LENGTH", 8)
    rows = [record(f"doc-{i:04d}", f"group-{i // 3}", f"raw document {i:04d} text",
                   ["prose", "python", "latex", "markdown"][i % 4])
            for i in range(2400)]
    corpus = tmp_path / "corpus.jsonl"
    manifest = tmp_path / "manifest.json"
    tokenizer = tmp_path / "tokenizer.json"
    corpus.write_text("".join(G.canonical(r) + "\n" for r in rows))
    manifest.write_text(G.canonical({"documents": [
        {k: v for k, v in r.items() if k != "text"} for r in rows]}))
    tokenizer.write_text("synthetic tokenizer fixture only")
    monkeypatch.setattr(G, "CORPUS_SHA", G.sha(corpus))
    monkeypatch.setattr(G, "MANIFEST_SHA", G.sha(manifest))
    monkeypatch.setattr(G, "TOKENIZER_SHA", G.sha(tokenizer))
    calls = []

    class FakeTokenizer:
        @staticmethod
        def from_file(path):
            assert path == str(tokenizer)
            return FakeTokenizer()

        def encode(self, text, *, add_special_tokens):
            assert add_special_tokens is False
            assert text.startswith("raw document ")
            calls.append(text)
            return SimpleNamespace(ids=encode(text))

    monkeypatch.setitem(sys.modules, "tokenizers", SimpleNamespace(Tokenizer=FakeTokenizer))
    sample = G.make_sample(rows, encode)
    return SimpleNamespace(rows=rows, corpus=corpus, manifest=manifest,
                           tokenizer=tokenizer, sample=sample, calls=calls)


def test_verified_sample_returns_full_raw_prefixes(frozen_fixture):
    f = frozen_fixture
    assert G.read_corpus(f.corpus, f.manifest) == f.rows
    prefixes = G.verify_sample(f.corpus, f.manifest, f.tokenizer, f.sample)
    assert len(prefixes) == 2400
    assert set(prefixes) == {r["id"] for r in f.rows}
    assert all(ids == list(range(8)) for ids in prefixes.values())
    assert set(f.calls) == {r["text"] for r in f.rows}


@pytest.mark.parametrize("field", ["positions", "n_tokens", "seed", "pilot", "excluded", "context_hash"])
def test_selection_mutations_are_rejected(frozen_fixture, field):
    f = frozen_fixture
    changed = copy.deepcopy(f.sample)
    if field == "positions":
        changed["documents"][0]["positions"].append(changed["documents"][0]["positions"][0])
    elif field == "n_tokens":
        changed["n_tokens"] += 1
    elif field == "seed":
        changed["seed"] += 1
    elif field == "pilot":
        changed["pilot_document_ids"][0] = changed["documents"][0]["id"]
    elif field == "excluded":
        changed["excluded_training_group_ids"] = []
    else:
        changed["documents"][0]["prefix_ids_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="differs from deterministic"):
        G.verify_sample(f.corpus, f.manifest, f.tokenizer, changed)


@pytest.mark.parametrize("target", ["corpus", "manifest", "tokenizer"])
def test_input_byte_mutation_is_rejected_before_tokenization(frozen_fixture, target):
    f = frozen_fixture
    p = getattr(f, target)
    p.write_text(p.read_text() + "\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        G.verify_sample(f.corpus, f.manifest, f.tokenizer, f.sample)
    assert not f.calls


@pytest.mark.parametrize("change", ["duplicate_id", "text", "group", "domain", "missing_manifest_id"])
def test_document_identity_content_and_groups_are_checked_beyond_outer_hash(
        frozen_fixture, monkeypatch, change):
    f = frozen_fixture
    rows = copy.deepcopy(f.rows)
    manifest = json.loads(f.manifest.read_text())
    if change == "duplicate_id":
        rows[-1]["id"] = rows[0]["id"]
    elif change == "text":
        rows[0]["text"] += " altered"
    elif change == "group":
        rows[0]["group_id"] = "changed-source-group"
    elif change == "domain":
        rows[0]["domain"] = "changed-domain"
    else:
        manifest["documents"].pop()
    f.corpus.write_text("".join(G.canonical(r) + "\n" for r in rows))
    f.manifest.write_text(G.canonical(manifest))
    monkeypatch.setattr(G, "CORPUS_SHA", G.sha(f.corpus))
    monkeypatch.setattr(G, "MANIFEST_SHA", G.sha(f.manifest))
    with pytest.raises(ValueError):
        G.read_corpus(f.corpus, f.manifest)


def test_sample_output_is_exclusive_and_cannot_overwrite(tmp_path):
    path = tmp_path / "sample.json"
    G.dump_new(path, {"sealed": True})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        G.dump_new(path, {"sealed": False})
    assert path.read_bytes() == before
