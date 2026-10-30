#!/usr/bin/env python
"""G6 "choice" family (BRIEF_G5G6.md): 8 pairs, all test. The user offers two options and asks the
model to pick one and reply with that word only. Versions A/B swap the option order. The answer
key is the TARGET's own greedy answer (`answer: null`, `answer_source: "target_greedy"`), filled in
by the analysis, never here. Same item schema as items.json; written to items_g6.json. items.json is
not touched (its sha is frozen).

Usage: .venv/bin/python projects/g_agreement/dataset/build_dataset_g6.py [--seed 20261007] [--no-write]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import random
import re
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "items_g6.json")
DEFAULT_SEED = 20261007
FAMILY = "choice"
PREFIX = "choice"

# One option pair per type; single common words, chosen to be single tokens in most tokenizers.
OPTION_PAIRS: List[Dict[str, Any]] = [
    {"type": "fruit", "options": ("apple", "pear")},
    {"type": "colour", "options": ("red", "blue")},
    {"type": "animal", "options": ("cat", "dog")},
    {"type": "number word", "options": ("seven", "three")},
    {"type": "tool", "options": ("hammer", "saw")},
    {"type": "city", "options": ("Paris", "Rome")},
    {"type": "shape", "options": ("circle", "square")},
    {"type": "drink", "options": ("tea", "coffee")},
]
TEMPLATES: List[Dict[str, str]] = [
    {"id": "choice-t1", "text": "Choose either {o1} or {o2} and reply with that word only."},
    {"id": "choice-t2", "text": "Pick one: {o1} or {o2}. One word."},
    {"id": "choice-t3", "text": "You must choose between {o1} and {o2}. Reply with your choice only."},
    {"id": "choice-t4", "text": "Which do you prefer, {o1} or {o2}? Answer with one word."},
    {"id": "choice-t5", "text": "Select {o1} or {o2}. Respond with just the word."},
]
SHORT_ANSWER_CUE = re.compile(r"(one word|word only|choice only|just the word)", re.I)


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_items(items: List[dict]) -> str:
    import hashlib
    return hashlib.sha256(_canonical(items).encode("utf-8")).hexdigest()


def build(seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    rng = random.Random(seed)
    pairs = list(OPTION_PAIRS)
    rng.shuffle(pairs)
    # 8 pairs over 5 templates: every template used at least once, assignment decided by seed
    tmpl_slots = list(TEMPLATES) + [rng.choice(TEMPLATES) for _ in range(len(pairs) - len(TEMPLATES))]
    rng.shuffle(tmpl_slots)
    items: List[dict] = []
    for k, (mat, tmpl) in enumerate(zip(pairs, tmpl_slots), start=1):
        pair_id = f"{PREFIX}-{k:02d}"
        cands = list(mat["options"])
        if rng.random() < 0.5:  # canonical candidate order decided by seed
            cands.reverse()
        for version in "AB":
            first, second = (cands[0], cands[1]) if version == "A" else (cands[1], cands[0])
            prompt = tmpl["text"].format(o1=first, o2=second)
            items.append({
                "item_id": f"{pair_id}{version}", "pair_id": pair_id, "version": version,
                "family": FAMILY, "split": "test", "template_id": tmpl["id"],
                "prompt_text": prompt, "render": "chat", "system": None,
                "primary": {"name": "model_choice",
                            "question": "Which of the two options will the model choose?",
                            "candidates": cands, "answer": None, "answer_aliases": [],
                            "answer_source": "target_greedy"},
                "secondary": {"entities": cands, "objects": [], "relation": None},
                "target_answer_regex": r"(?i)\b(" + "|".join(map(re.escape, cands)) + r")\b",
                "construction": {"first_mentioned_candidate": first, "answer_position": None,
                                 "cue_position": "n/a", "other_candidate": None,
                                 "option_type": mat["type"], "first_listed_position": cands.index(first)},
                "notes": "answer key = target model's own greedy answer (filled by analysis); versions swap option order",
            })
    report = validate(items)
    meta = {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "seed": seed, "n_pairs": len(items) // 2, "families": [FAMILY],
            "sha256_items": sha256_items(items), "frozen": False, "balance_checks": report}
    return {"meta": meta, "items": items}


def validate(items: List[dict]) -> Dict[str, Any]:
    assert len(items) == 16
    by_pair: Dict[str, List[dict]] = {}
    seen_options: Dict[str, str] = {}
    for it in items:
        assert it["family"] == FAMILY and it["split"] == "test"
        assert it["item_id"] == it["pair_id"] + it["version"]
        pr = it["primary"]
        assert pr["name"] == "model_choice" and pr["answer"] is None and pr["answer_source"] == "target_greedy"
        assert len(pr["candidates"]) == 2 and len(set(pr["candidates"])) == 2
        for c in pr["candidates"]:
            assert re.search(r"\b" + re.escape(c) + r"\b", it["prompt_text"]), it["item_id"]
            assert " " not in c
        assert SHORT_ANSWER_CUE.search(it["prompt_text"]), it["item_id"]
        re.compile(it["target_answer_regex"])
        # first-listed option really is the first candidate occurrence in the prompt
        first = min(pr["candidates"], key=lambda c: re.search(r"\b" + re.escape(c) + r"\b", it["prompt_text"]).start())
        assert first == it["construction"]["first_mentioned_candidate"], it["item_id"]
        by_pair.setdefault(it["pair_id"], []).append(it)
    assert len(by_pair) == 8
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert a["primary"]["candidates"] == b["primary"]["candidates"]
        assert a["template_id"] == b["template_id"]
        assert a["construction"]["first_mentioned_candidate"] != b["construction"]["first_mentioned_candidate"]
        assert a["construction"]["first_listed_position"] == 0 and b["construction"]["first_listed_position"] == 1
        for c in a["primary"]["candidates"]:
            assert c not in seen_options, (c, "option appears in two pairs", seen_options.get(c), pid)
            seen_options[c] = pid
    first_pos = [it["construction"]["first_listed_position"] for it in items]
    assert first_pos.count(0) == 8 and first_pos.count(1) == 8
    per_cand_first = {}
    for it in items:
        per_cand_first[it["construction"]["first_mentioned_candidate"]] = per_cand_first.get(it["construction"]["first_mentioned_candidate"], 0) + 1
    assert all(v == 1 for v in per_cand_first.values()) and len(per_cand_first) == 16
    tids = sorted({it["template_id"] for it in items})
    assert len(tids) >= 4
    return {"n_pairs": 8, "n_items": 16, "first_listed_position_counts": {"candidates[0]": first_pos.count(0), "candidates[1]": first_pos.count(1)},
            "each_option_first_listed_exactly_once": True, "templates_used": tids,
            "option_types": [it["construction"]["option_type"] for it in items if it["version"] == "A"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    data = build(args.seed)
    if not args.no_write:
        if os.path.exists(args.out):
            with open(args.out, encoding="utf-8") as f:
                if json.load(f).get("meta", {}).get("frozen"):
                    raise SystemExit(f"refusing to overwrite frozen {args.out}")
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"wrote {args.out} (sha {data['meta']['sha256_items'][:16]}...)")
    for it in data["items"]:
        print(it["item_id"].ljust(11), it["prompt_text"])
    print(json.dumps(data["meta"]["balance_checks"], indent=1))


if __name__ == "__main__":
    main()
