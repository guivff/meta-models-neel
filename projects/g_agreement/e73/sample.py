"""Deterministic CPU E73 sampler, with labels retained only in private files.

Documents are visited once; SQLite keeps candidates off the Python heap. In each
document/state/class, choose at most two uniformly random eligible token offsets.
Process cells from scarcest to most abundant (eligibility only, before BOW), with
uniform random candidate priority. Enforce the two-document-position cap globally
across states. Never refill or resample after a BOW result.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import random
import re
import sqlite3
from pathlib import Path

from .sources import dump_json, iter_documents, sha256_file, verify_source_manifest
from .states import extract_states

SEED = 20261027
CONTEXT_TOKENS = 256
PER_CLASS_SPLIT = 200
STATES = tuple(f"W{i}" for i in range(1, 9))
HERE = Path(__file__).resolve().parent


def document_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def document_split(digest: str) -> str:
    return "dev" if int(digest, 16) < 2**255 else "test"


def stable_rng(*parts: object) -> random.Random:
    digest = hashlib.sha256("|".join(map(str, (SEED, *parts))).encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


def topic_for_title(title: str, lists: dict) -> str | None:
    matched = []
    for topic in ("sports", "science"):
        if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", title, flags=re.IGNORECASE)
               for term in lists[topic]):
            matched.append(topic)
    return matched[0] if len(matched) == 1 else None


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("x") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def sample_documents(documents, tokenizer, out: Path, *, title_lists: dict,
                     per_class_split: int = PER_CLASS_SPLIT, context_tokens: int = CONTEXT_TOKENS,
                     source_binding: str = "TEST_ONLY", tokenizer_binding: str = "TEST_ONLY") -> dict:
    """Production CLI fixes n and context; parameters allow small offline tests."""
    out.mkdir(parents=True, exist_ok=False)
    (out / "private").mkdir()
    (out / "public").mkdir()
    conn = sqlite3.connect(out / "private" / "candidates.sqlite3")
    conn.execute("CREATE TABLE documents (hash TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE candidates (state TEXT, split TEXT, label INTEGER, priority TEXT, payload TEXT)")
    eligibility = Counter()
    diagnostics = Counter()
    try:
        for doc in documents:
            text = doc["text"]
            digest = document_hash(text)
            if conn.execute("SELECT 1 FROM documents WHERE hash=?", (digest,)).fetchone():
                diagnostics["duplicate_documents"] += 1
                continue
            conn.execute("INSERT INTO documents VALUES (?)", (digest,))
            diagnostics["unique_documents"] += 1
            if diagnostics["unique_documents"] % 1000 == 0:
                print(json.dumps({"stage": "E73_CPU_SAMPLING", "unique_documents": diagnostics["unique_documents"]}), flush=True)
            split = document_split(digest)
            encoding = tokenizer.encode(text, add_special_tokens=False)
            ids, offsets = encoding.ids, encoding.offsets
            eligible_indices = [i for i, (start, end) in enumerate(offsets)
                                if i >= context_tokens - 1 and end > start
                                and (i + 1 == len(offsets) or offsets[i + 1][1] > end)]
            if not eligible_indices:
                diagnostics["short_or_no_complete_boundary"] += 1
                continue
            topic = topic_for_title(doc.get("title", ""), title_lists) if doc["language"] in ("wikitext", "prose") else None
            states = extract_states(text, doc["language"], [offsets[i][1] for i in eligible_indices],
                                    title=doc.get("title", ""), topic=topic)
            for state, values in states.items():
                if state not in STATES:
                    raise ValueError("Unknown extractor state")
                if len(values) != len(eligible_indices):
                    raise ValueError("Extractor offsets do not align")
                for label in (0, 1):
                    choices = [i for i, value in zip(eligible_indices, values) if value == label]
                    eligibility[state, split, label] += len(choices)
                    rng = stable_rng("offsets", digest, state, label)
                    for i in rng.sample(choices, min(2, len(choices))):
                        window = ids[i + 1 - context_tokens:i + 1]
                        item_id = hashlib.sha256(f"E73|{SEED}|{state}|{digest}|{i}".encode()).hexdigest()[:32]
                        record = {"id": item_id, "state": state, "split": split, "label": label,
                                  "doc_hash": digest, "token_index": i, "char_end": offsets[i][1],
                                  "context_start_char": offsets[i + 1 - context_tokens][0],
                                  "input_ids": window, "source": doc.get("source", ""),
                                  "source_file": doc.get("source_file", ""),
                                  "source_index": doc.get("source_index"),
                                  "original_path": doc.get("original_path", ""),
                                  "title": doc.get("title", "")}
                        priority = hashlib.sha256(f"priority|{SEED}|{item_id}".encode()).hexdigest()
                        conn.execute("INSERT INTO candidates VALUES (?,?,?,?,?)",
                                     (state, split, label, priority, json.dumps(record, separators=(",", ":"))))
            if diagnostics["unique_documents"] % 100 == 0:
                conn.commit()
        conn.commit()
        cells = list(conn.execute("SELECT state,split,label,count(*) FROM candidates GROUP BY state,split,label"))
        selected, document_uses, counts = [], Counter(), Counter()
        for state, split, label, available in sorted(cells, key=lambda cell: (cell[3], cell[:3])):
            for (payload,) in conn.execute("SELECT payload FROM candidates WHERE state=? AND split=? AND label=? ORDER BY priority",
                                           (state, split, label)):
                row = json.loads(payload)
                if document_uses[row["doc_hash"]] >= 2:
                    continue
                selected.append(row)
                document_uses[row["doc_hash"]] += 1
                counts[state, split, label] += 1
                if counts[state, split, label] == per_class_split:
                    break
        per_state_n = {state: per_class_split for state in STATES}
        w8_n = min(counts["W8", split, label] for split in ("dev", "test") for label in (0, 1))
        if w8_n >= min(50, per_class_split):
            per_state_n["W8"] = w8_n
            for split in ("dev", "test"):
                for label in (0, 1):
                    keep = {r["id"] for r in sorted((r for r in selected if (r["state"], r["split"], r["label"]) == ("W8", split, label)), key=lambda r: r["id"])[:w8_n]}
                    selected = [r for r in selected if (r["state"], r["split"], r["label"]) != ("W8", split, label) or r["id"] in keep]
                    counts["W8", split, label] = w8_n
        complete_states = [state for state in STATES if all(counts[state, split, label] == per_state_n[state]
                           for split in ("dev", "test") for label in (0, 1))]
        report = {"experiment": "E73", "track": "C", "seed": SEED,
                  "context_tokens": context_tokens, "per_class_split": per_class_split,
                  "per_state_class_split": per_state_n,
                  "document_cap_scope": "global_across_states", "max_positions_per_document": 2,
                  "split_rule": "sha256(UTF8(document)) < 2**255 is dev, otherwise test",
                  "included_states": complete_states, "excluded_states": [s for s in STATES if s not in complete_states],
                  "status": "SAMPLED_PRE_BOW" if source_binding != "TEST_ONLY" else "TEST_ONLY",
                  "diagnostics": dict(diagnostics), "states": {}}
        for state in STATES:
            detail = {"eligible_tokens": {split: {str(label): eligibility[state, split, label] for label in (0, 1)}
                       for split in ("dev", "test")},
                      "selected": {split: {str(label): counts[state, split, label] for label in (0, 1)}
                       for split in ("dev", "test")}, "complete": state in complete_states}
            if state not in complete_states:
                detail["reason"] = "NOT_BUILT_INSUFFICIENT_POSITIONS_REQUIRES_COORDINATOR_DISPOSITION"
            if state == "W8" and state not in complete_states:
                detail["reason"] = "W8_DROPPED_BELOW_100_PER_SPLIT"
            if state == "W6" and sum(eligibility[state, split, label] for split in ("dev", "test") for label in (0, 1)) < 400:
                detail["reason"] = "W6_DROPPED_NO_MARKDOWN_SOURCE_CLARIFICATION_3"
            report["states"][state] = detail
        # Incomplete states remain in diagnostics/candidate database but cannot be
        # captured. The scientific bank is never silently reduced within a state.
        selected = [r for r in selected if r["state"] in complete_states]
        selected.sort(key=lambda row: row["id"])
        test_order = Counter()
        private_rows, public_rows = [], []
        for row in selected:
            public_rows.append({"id": row["id"], "input_ids": row.pop("input_ids")})
            row["reader_selected"] = row["split"] == "test" and test_order[row["state"]] < 200
            if row["split"] == "test":
                test_order[row["state"]] += 1
            private_rows.append(row)
        validate_sample(public_rows, private_rows, complete_states, per_class_split=per_state_n,
                        context_tokens=context_tokens)
        write_jsonl(out / "public" / "items.jsonl", public_rows)
        write_jsonl(out / "private" / "labels.jsonl", private_rows)
        dump_json(out / "private" / "SAMPLE_REPORT.json", report)
        manifest = {"experiment": "E73", "stage": "SAMPLED_PRE_BOW", "items": len(public_rows),
                    "input_schema": ["id", "input_ids"], "context_tokens": context_tokens,
                    "source_manifest_sha256": source_binding, "tokenizer_sha256": tokenizer_binding,
                    "title_lists_sha256": sha256_file(HERE / "sports_science_titles.json"),
                    "title_matching_rule": "WHOLE_WORD_CASE_INSENSITIVE_TITLE_TERMS",
                    "code_sha256": {name: sha256_file(HERE / name) for name in ("sources.py", "states.py", "sample.py", "bow.py")},
                    "items_sha256": sha256_file(out / "public" / "items.jsonl"),
                    "private_labels_sha256": sha256_file(out / "private" / "labels.jsonl"),
                    "sample_report_sha256": sha256_file(out / "private" / "SAMPLE_REPORT.json")}
        dump_json(out / "public" / "MANIFEST.json", manifest)
        return report
    finally:
        conn.close()


def validate_sample(public_rows: list[dict], private_rows: list[dict], states: list[str], *,
                    per_class_split: int | dict = PER_CLASS_SPLIT, context_tokens: int = CONTEXT_TOKENS) -> None:
    public = {r["id"]: r for r in public_rows}
    private = {r["id"]: r for r in private_rows}
    if len(public) != len(public_rows) or set(public) != set(private) or len(private) != len(private_rows):
        raise ValueError("Duplicate or mismatched opaque IDs")
    document_uses, counts, splits = Counter(), Counter(), {}
    for row in public_rows:
        if set(row) != {"id", "input_ids"} or not re.fullmatch("[0-9a-f]{32}", row["id"]):
            raise ValueError("Invalid public schema")
        if len(row["input_ids"]) != context_tokens or any(type(i) is not int or i < 0 for i in row["input_ids"]):
            raise ValueError("Invalid context IDs")
    for row in private_rows:
        if row["split"] != document_split(row["doc_hash"]):
            raise ValueError("Document split does not match hash")
        document_uses[row["doc_hash"]] += 1
        splits.setdefault(row["doc_hash"], set()).add(row["split"])
        counts[row["state"], row["split"], row["label"]] += 1
    if any(n > 2 for n in document_uses.values()) or any(len(s) > 1 for s in splits.values()):
        raise ValueError("Document cap or split leakage")
    for state in states:
        n = per_class_split[state] if isinstance(per_class_split, dict) else per_class_split
        if any(counts[state, split, label] != n for split in ("dev", "test") for label in (0, 1)):
            raise ValueError("Unbalanced or incomplete state")
        tests = sorted((r for r in private_rows if r["state"] == state and r["split"] == "test"), key=lambda r: r["id"])
        if any(r["reader_selected"] != (i < 200) for i, r in enumerate(tests)):
            raise ValueError("Readers must use exactly the first 200 ordered test positions")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True, help="Pinned Qwen tokenizer.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_source_manifest(args.sources)
    assets = json.loads((HERE.parent / "manifest" / "assets.json").read_text())
    tokenizer_hash = sha256_file(args.tokenizer)
    if tokenizer_hash != assets["target"]["files_needed"]["tokenizer.json_sha256"]:
        raise ValueError("Tokenizer differs from pinned Qwen asset")
    lists = json.loads((HERE / "sports_science_titles.json").read_text())
    if lists["matching_rule"] != "WHOLE_WORD_CASE_INSENSITIVE_TITLE_TERMS" or min(len(lists[k]) for k in ("sports", "science")) < 40:
        raise ValueError("W8 matching rule/list freeze unresolved")
    from tokenizers import Tokenizer
    report = sample_documents(iter_documents(args.sources, manifest), Tokenizer.from_file(str(args.tokenizer)),
                              args.out, title_lists=lists,
                              source_binding=sha256_file(args.sources / "SOURCE_MANIFEST.json"), tokenizer_binding=tokenizer_hash)
    print(json.dumps({"status": report["status"], "included_states": report["included_states"],
                      "excluded_states": report["excluded_states"]}))


if __name__ == "__main__":
    main()
