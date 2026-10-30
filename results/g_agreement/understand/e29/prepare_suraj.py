#!/usr/bin/env python3
"""Stage the pinned, non-blind exp-13 companion inputs without reader outputs.

2026-10-25 operational choice, before E29 base-model scoring: use the 160
selection items per row and the single frozen Oracle fixed-label candidate pair.
No mined candidates, NLA candidates, or source reader scores are staged.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


REVISION = "a8e41f4a31d654ccc29e2d9105abb2aac38ad5eb"
SOURCE_ROOT = "experiments/13_new_rows"
ROWS = (
    "tb_tablecol", "tb_paren", "tb_sentcount", "tb_codeline",
    "fmt_listdepth", "fmt_qa", "tb_wordsleft",
)
VALUES = {
    "tb_tablecol": ["first", "late"],
    "tb_paren": ["inside", "outside"],
    "tb_sentcount": ["early", "late"],
    "tb_codeline": ["early", "late"],
    "fmt_listdepth": ["shallow", "deep"],
    "fmt_qa": ["qa", "prose"],
    "tb_wordsleft": ["many", "few"],
}
EXPECTED_CANDIDATES = {
    "tb_tablecol": ["- column one", "- column five"],
    "tb_paren": ["- inside parentheses", "- outside parentheses"],
    "tb_sentcount": ["- sentence two", "- sentence six"],
    "tb_codeline": ["- line two", "- line ten"],
    "fmt_listdepth": ["- nesting level one", "- nesting level three"],
    "fmt_qa": ["- Q&A format", "- prose format"],
    "tb_wordsleft": ["- twenty words left", "- three words left"],
}
SOURCE_HASHES = {
    "feature_spec.py": "b0dd043f964ea3a22c52629a03d37466e9607e719193aba657414b56d7effe43",
    "items_build.py": "d3f75b5cbf6822caefb120fec041d6fd182d89c17e2cc0692a62c6d36719a623",
    "modal13.py": "cc64b14943f1a180f79870dfa3a864497fd5b4cd131f831b1bc6a570cfa652bb",
    "templates_frozen.json": "d904620618031dfc8d53735aefd9d0662ab619ce79930c4b4895925114837d16",
    "results/gen_ol_tb_tablecol.json": "2e8738d012cf15c827bc81b15dc39f2e4e0016766f8b118e9fff3f290d779b9d",
    "results/gen_ol_tb_paren.json": "10bf31c714133f3975770a3a72697ec7e59d4c0eaf57b39ecfd4e446e41a6b51",
    "results/gen_ol_tb_sentcount.json": "10176f5f2053a2778ed282ee16a550f80c4ce1c915bd61d35e4e3b215d259fa0",
    "results/gen_ol_tb_codeline.json": "01adb61900e9fe775582666eff7cb01e4c8e2ff6c69ee37e5672ab0f9719dfac",
    "results/gen_ol_fmt_listdepth.json": "dcad707d1e9cfd19cb42287c3ad0fbd5da34ebd2bdbc339f570d744f2346966a",
    "results/gen_ol_fmt_qa.json": "bb5d641d0e418b042f3cc551a334d1b11600de761a8113c2e628162e0b078559",
    "results/gen_ol_tb_wordsleft.json": "8cbff9582a122f1b0a0c1f9928fa9a0037c916e1033fd1f473b2adb43ada3bac",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, data: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def prepare(repo: Path, out: Path) -> dict:
    repo, out = repo.resolve(), out.resolve()
    require(not out.exists(), "output directory already exists; never overwrite a staged cohort")
    revision = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    require(revision == REVISION, "Suraj repository HEAD differs from the pinned revision")
    source = repo / SOURCE_ROOT
    for rel, digest in SOURCE_HASHES.items():
        require(sha(source / rel) == digest, "pinned source hash mismatch: " + rel)

    frozen = json.loads((source / "templates_frozen.json").read_text(encoding="utf-8"))
    staged, labels, candidates = [], [], {}
    for row in ROWS:
        values = VALUES[row]
        require(frozen["meta"]["values"][row] == values, "frozen value order changed: " + row)
        fixed = frozen["templates"]["ol"][row]["fixed_label"]
        require(fixed["family"] == "fixed_label" and fixed["id"] == f"ol:{row}:fixed",
                "wrong candidate family: " + row)
        require(set(fixed["candidates"]) == set(values), "wrong candidate value keys: " + row)
        pair = [fixed["candidates"][value] for value in values]
        require(pair == EXPECTED_CANDIDATES[row], "literal fixed candidates changed: " + row)
        candidates[row] = [pair]

        # Source files also contain reader outputs; only the item field is used.
        bank = json.loads((source / "results" / f"gen_ol_{row}.json").read_text(encoding="utf-8"))["items"]
        require(len(bank) == 200, "source bank must contain 200 items: " + row)
        require(len({item["id"] for item in bank}) == 200, "duplicate source item IDs: " + row)
        require(all(item["feature"] == row for item in bank), "source feature mismatch: " + row)
        counts = Counter((item["split"], item["value"]) for item in bank)
        require(counts == Counter({(split, value): n for split, n in (("mine", 20), ("select", 80))
                                   for value in values}), "source splits/labels changed: " + row)
        selected = [item for item in bank if item["split"] == "select"]
        require(sorted(item["id"] for item in selected) == frozen["items"][row]["select"],
                "frozen selection IDs mismatch: " + row)
        for item in selected:
            require(isinstance(item["id"], str) and bool(item["id"]), "invalid item ID")
            require(isinstance(item["text"], str) and bool(item["text"]), "empty item text")
            staged.append({"id": item["id"], "feature": row, "text": item["text"]})
            labels.append({"id": item["id"], "feature": row,
                           "value": "A" if item["value"] == values[0] else "B"})
    require(len(staged) == 1120 and len({item["id"] for item in staged}) == 1120,
            "expected 1,120 unique selection items across seven rows")

    out.mkdir(parents=True, exist_ok=False)
    stage = out / "stage"
    stage.mkdir()
    with (stage / "items.jsonl").open("x", encoding="utf-8") as stream:
        for item in staged:
            stream.write(json.dumps(item, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    dump(stage / "candidates.json", candidates)
    dump(stage / "INPUT_SEAL.json", {
        "date": "2026-10-25",
        "files": {name: sha(stage / name) for name in ("items.jsonl", "candidates.json")},
    })
    dump(out / "labels.json", labels)
    cohort = {
        "name": "suraj_exp13", "blind": False, "rows": list(ROWS),
        "items": [{"id": item["id"], "feature": item["feature"]} for item in staged],
        "phrasing_count": 1, "expected_scores": 2240,
        "input_seal_sha256": sha(stage / "INPUT_SEAL.json"),
        "labels_sha256": sha(out / "labels.json"),
        "freeze": {
            "repo_revision": REVISION,
            "source_files": {f"{SOURCE_ROOT}/{rel}": digest for rel, digest in SOURCE_HASHES.items()},
            "split": "select", "candidate_family": "ol.fixed_label",
        },
    }
    dump(out / "COHORT.json", cohort)
    return {"out": str(out), "rows": len(ROWS), "items": len(staged),
            "expected_scores": cohort["expected_scores"],
            "input_seal_sha256": cohort["input_seal_sha256"],
            "labels_sha256": cohort["labels_sha256"],
            "cohort_sha256": sha(out / "COHORT.json")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.repo, args.out), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
