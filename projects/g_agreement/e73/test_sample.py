"""Offline sampler invariants; no corpus access and no scientific BOW scores."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from .bow import gate_states, score_state
from .sample import document_hash, document_split, read_jsonl, sample_documents, topic_for_title, validate_sample


class WordTokenizer:
    def encode(self, text, add_special_tokens=False):
        import re
        matches = list(re.finditer(r"\S+", text))
        return SimpleNamespace(ids=[int.from_bytes(hashlib.sha256(m.group().encode()).digest()[:3], "big") for m in matches],
                               offsets=[m.span() for m in matches])


def corpus():
    rows = []
    for label in (0, 1):
        for i in range(100):
            rows.append({"text": f"class{label} document{i} " + "token " * 270,
                         "language": "python", "source": "offline_fixture"})
    return rows + [rows[0]]


def fixture_states(text, language, offsets, **kwargs):
    return {f"W{i}": [int(text[5])] * len(offsets) for i in range(1, 9)}


def test_sampler_deterministic_balanced_document_disjoint_and_capped(tmp_path):
    docs = corpus()
    with patch(sample_documents.__module__ + ".extract_states", side_effect=fixture_states):
        a = sample_documents(docs, WordTokenizer(), tmp_path / "a", title_lists={"sports": [], "science": []}, per_class_split=2)
        b = sample_documents(list(reversed(docs)), WordTokenizer(), tmp_path / "b", title_lists={"sports": [], "science": []}, per_class_split=2)
    pa, pb = tmp_path / "a", tmp_path / "b"
    assert (pa / "public/items.jsonl").read_bytes() == (pb / "public/items.jsonl").read_bytes()
    public, private = read_jsonl(pa / "public/items.jsonl"), read_jsonl(pa / "private/labels.jsonl")
    assert len(public) == 64
    assert all(len(r["input_ids"]) == 256 and set(r) == {"id", "input_ids"} for r in public)
    assert a["diagnostics"]["duplicate_documents"] == 1
    validate_sample(public, private, a["included_states"], per_class_split=2)
    assert {r["doc_hash"] for r in private if r["split"] == "dev"}.isdisjoint(r["doc_hash"] for r in private if r["split"] == "test")
    assert all(r["split"] == document_split(r["doc_hash"]) for r in private)
    bad = copy.deepcopy(private)
    bad[0]["split"] = "test" if bad[0]["split"] == "dev" else "dev"
    with pytest.raises(ValueError, match="Document split"):
        validate_sample(public, bad, a["included_states"], per_class_split=2)


def test_title_matching_whole_word_case_insensitive_excludes_ambiguous():
    lists = {"sports": ["football", "world cup"], "science": ["physics", "atom"]}
    assert topic_for_title("Football in 1900", lists) == "sports"
    assert topic_for_title("WORLD CUP", lists) == "sports"
    assert topic_for_title("Atomic football", lists) == "sports"
    assert topic_for_title("Football and physics", lists) is None
    assert topic_for_title("Anatomy", lists) is None


def test_gate_excludes_content_controls_as_well_as_structure():
    included, excluded = gate_states({"W1": {"test_auroc": .65}, "W2": {"test_auroc": .650001},
                                     "W7": {"test_auroc": .99}, "W8": {"test_auroc": .70}})
    assert included == ["W1"]
    assert excluded == ["W2", "W7", "W8"]


def test_incomplete_states_are_reported_without_partial_export(tmp_path):
    with patch(sample_documents.__module__ + ".extract_states", side_effect=fixture_states):
        report = sample_documents(corpus()[:2], WordTokenizer(), tmp_path / "short",
                                  title_lists={"sports": [], "science": []}, per_class_split=2)
    assert report["included_states"] == []
    assert not (tmp_path / "short/public/items.jsonl").read_text()
    assert report["states"]["W1"]["reason"].startswith("NOT_BUILT")


def test_actual_installed_cpu_bow_estimator():
    rows = [{"id": f"{split}-{label}-{i}", "split": split, "label": label,
             "input_ids": [100 + label] * 256}
            for split in ("dev", "test") for label in (0, 1) for i in range(4)]
    result = score_state(rows)
    assert result["test_auroc"] == 1.0
    assert result["dev_items"] == result["test_items"] == 8


@pytest.mark.parametrize("documents_per_cell,expected_n", [(25, 100), (24, 0)])
def test_w8_reduced_n_boundary(tmp_path, documents_per_cell, expected_n):
    from collections import Counter
    rows, cells = [], Counter()
    for i in range(1000):
        for label in (0, 1):
            text = f"class{label} unique{i} " + "token " * 270
            cell = document_split(document_hash(text)), label
            if cells[cell] < documents_per_cell:
                rows.append({"text": text, "language": "wikitext"})
                cells[cell] += 1
        if len(cells) == 4 and min(cells.values()) == documents_per_cell:
            break
    with patch(sample_documents.__module__ + ".extract_states",
               side_effect=lambda text, language, offsets, **kwargs: {"W8": [int(text[5])] * len(offsets)}):
        report = sample_documents(rows, WordTokenizer(), tmp_path / "w8", title_lists={"sports": [], "science": []})
    labels = read_jsonl(tmp_path / "w8/private/labels.jsonl")
    assert len([r for r in labels if r["split"] == "test"]) == expected_n
    assert ("W8" in report["included_states"]) == bool(expected_n)
