#!/usr/bin/env python
"""Phase X3 candidate item sets (BRIEF_X.md §X3): ``dataset/items_x3_candidates.json`` with ``meta`` + ``items``.

(a) 400 arrow puzzles ``xpz-0001..0400`` (family ``puzzle``): a random mapping over 5-7 of the symbols A-H
    (every listed symbol maps to one other symbol; cycles allowed), k in {3, 4} steps (200 each), prompt
    "A → C. C → F. ... Start at A and follow the arrows three times. Where do you end up? Answer with the
    symbol only." ``primary`` holds the text-implied key (correct, k, start, trace); ``distractors`` are the
    symbols visited before the end, so the X3 collector can tabulate the most frequent wrong answer per shape.
    The k+1 visited symbols are distinct (so the correct symbol differs from the start and from the (k-1)-step symbol).
(b) 300 two-option choice prompts ``xch-0001..0300`` (family ``choice``): 150 option pairs x 2 orders, G6 style
    (same templates as build_dataset_g6.py, pools extended to 150 typed pairs); ``prompt_only_text`` is the
    G6 prompt-only self-guess prompt, built with ``core.generate.prompt_only_prompt`` (the frozen
    ``config.PROMPT_ONLY_TEMPLATE``) exactly as the G3/G6 collectors do. Answer keys are the target's own
    greedy answers (filled by the X3 collector, never here).

No model calls. Deterministic from --seed (default 20261008).
Usage: .venv/bin/python projects/g_agreement/dataset/build_x3.py [--seed 20261008] [--no-write] [--print]
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import hashlib
import itertools
import json
import os
import random
import re
import sys
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import generate as G  # noqa: E402
from projects.g_agreement.dataset import build_dataset_g6 as g6  # noqa: E402

DEFAULT_OUT = os.path.join(HERE, "items_x3_candidates.json")
DEFAULT_SEED = 20261008
N_PUZZLES = 400
N_CHOICE_PAIRS = 150
SYMBOLS = list("ABCDEFGH")
N_SYMBOLS_CHOICES = (5, 6, 7)
K_CHOICES = (3, 4)
ARROW = "→"
STEP_WORDS = {3: "three times", 4: "four times"}
PUZZLE_TEMPLATE = {"id": "pz-t1", "text": "{rules} Start at {start} and follow the arrows {times}. Where do you end up? Answer with the symbol only."}
SYMBOL_REGEX = r"(?<![A-Za-z])([A-H])(?![A-Za-z])"  # any single symbol (the collector parses the model's answer with it)

# G6 option pairs first (reused verbatim), then more typed single-word pools.
OPTION_POOLS: Dict[str, List[str]] = {
    "fruit": ["apple", "pear", "plum", "peach", "mango", "grape", "lemon", "cherry"],
    "colour": ["red", "blue", "green", "yellow", "black", "white", "purple", "orange"],
    "animal": ["cat", "dog", "horse", "sheep", "goat", "rabbit", "mouse", "tiger"],
    "number word": ["seven", "three", "four", "nine", "five", "eight", "six", "two"],
    "tool": ["hammer", "saw", "drill", "wrench", "pliers", "chisel", "screwdriver", "spade"],
    "city": ["Paris", "Rome", "Berlin", "Madrid", "Vienna", "Lisbon", "Prague", "Oslo"],
    "shape": ["circle", "square", "triangle", "star", "oval", "hexagon", "diamond", "cube"],
    "drink": ["tea", "coffee", "juice", "milk", "water", "lemonade", "cocoa", "soda"],
    "vegetable": ["carrot", "potato", "onion", "pepper", "spinach", "cabbage", "leek", "turnip"],
    "instrument": ["piano", "guitar", "violin", "drums", "flute", "trumpet", "cello", "harp"],
    "sport": ["tennis", "football", "golf", "hockey", "rugby", "cricket", "boxing", "rowing"],
    "weather": ["rain", "snow", "wind", "fog", "hail", "sunshine", "thunder", "frost"],
    "metal": ["gold", "silver", "copper", "iron", "tin", "zinc", "nickel", "lead"],
    "planet": ["Mars", "Venus", "Jupiter", "Saturn", "Mercury", "Neptune", "Uranus", "Earth"],
    "vehicle": ["car", "bus", "train", "bike", "truck", "boat", "tram", "plane"],
    "clothing": ["hat", "coat", "scarf", "glove", "shirt", "sock", "boot", "jacket"],
    "bird": ["eagle", "sparrow", "owl", "crow", "robin", "swan", "parrot", "pigeon"],
    "flower": ["rose", "tulip", "daisy", "lily", "orchid", "violet", "poppy", "iris"],
    "gem": ["ruby", "emerald", "sapphire", "pearl", "opal", "topaz", "amber", "jade"],
    "furniture": ["chair", "table", "sofa", "desk", "bed", "shelf", "stool", "bench"],
    "month": ["March", "June", "August", "October", "April", "July", "November", "February"],
    "season": ["spring", "summer", "autumn", "winter"],
}
MAX_WORD_USES = 2


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_items(items: List[dict]) -> str:
    return hashlib.sha256(_canonical(items).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------
# (a) puzzles
# --------------------------------------------------------------------------------------
def random_mapping(rng: random.Random, n: int) -> Dict[str, str]:
    """Each of n symbols (drawn from A-H) maps to one OTHER symbol of the set; cycles allowed."""
    syms = rng.sample(SYMBOLS, n)
    return {s: rng.choice([t for t in syms if t != s]) for s in syms}


def follow(mapping: Dict[str, str], start: str, k: int) -> List[str]:
    """Trace of the k steps: [start, s1, ..., sk]."""
    trace = [start]
    for _ in range(k):
        trace.append(mapping[trace[-1]])
    return trace


def puzzle_prompt(mapping: Dict[str, str], rule_order: List[str], start: str, k: int) -> str:
    rules = " ".join(f"{s} {ARROW} {mapping[s]}." for s in rule_order)
    return PUZZLE_TEMPLATE["text"].format(rules=rules, start=start, times=STEP_WORDS[k])


def solve_puzzle(item: dict) -> str | None:
    """Independent re-derivation from the prompt text alone."""
    p, c = item["prompt_text"], item["primary"]
    rules = dict(re.findall(r"([A-H]) " + ARROW + r" ([A-H])\.", p))
    cur = c["start"]
    try:
        for _ in range(int(c["k"])):
            cur = rules[cur]
    except KeyError:
        return None
    return cur


def build_puzzles(rng: random.Random, n_items: int = N_PUZZLES) -> List[dict]:
    ks = [K_CHOICES[i % len(K_CHOICES)] for i in range(n_items)]
    rng.shuffle(ks)
    ns = [N_SYMBOLS_CHOICES[i % len(N_SYMBOLS_CHOICES)] for i in range(n_items)]
    rng.shuffle(ns)
    items: List[dict] = []
    seen = set()
    for i in range(n_items):
        k, n = ks[i], ns[i]
        while True:
            mapping = random_mapping(rng, n)
            start = rng.choice(sorted(mapping))
            trace = follow(mapping, start, k)
            correct = trace[-1]
            rule_order = sorted(mapping)
            rng.shuffle(rule_order)
            prompt = puzzle_prompt(mapping, rule_order, start, k)
            # the k+1 visited symbols are distinct: implies correct != start and != the (k-1)-step
            # symbol, and every distractor is a genuinely wrong answer (cycles stay allowed in the mapping)
            if len(set(trace)) == len(trace) and prompt not in seen:
                break
        seen.add(prompt)
        distractors = trace[:-1]  # the symbols visited before the end, in order (all distinct)
        item = {
            "item_id": f"xpz-{i + 1:04d}", "pair_id": None, "version": None, "family": "puzzle", "split": "test",
            "template_id": PUZZLE_TEMPLATE["id"], "prompt_text": prompt, "render": "chat", "system": None,
            "primary": {"name": f"{STEP_WORDS[k].split()[0]}_step_result",
                        "question": f"Starting from {start}, which symbol do you reach after following the arrows {STEP_WORDS[k]}?",
                        "correct": correct, "answer": correct, "answer_source": "construction", "k": k, "start": start,
                        "trace": trace, "candidates": None, "answer_aliases": [correct.lower()]},
            "distractors": distractors,
            "secondary": {"entities": sorted(mapping), "objects": [], "relation": {"type": "maps_to", "subject": trace[-2], "object": correct}},
            "target_answer_regex": SYMBOL_REGEX,
            "construction": {"mapping": mapping, "rule_order": rule_order, "n_symbols": n, "k": k, "shape": f"n{n}_k{k}", "arrow": ARROW},
            "notes": "X3(a) candidate; candidates (model answer, correct) are assigned by the X3 collector after the greedy run",
        }
        assert solve_puzzle(item) == correct
        items.append(item)
    return items


# --------------------------------------------------------------------------------------
# (b) choice
# --------------------------------------------------------------------------------------
def select_option_pairs(rng: random.Random, n_pairs: int = N_CHOICE_PAIRS) -> List[Tuple[str, Tuple[str, str]]]:
    """n distinct (type, option pair): round-robin over the types, every word in at most MAX_WORD_USES pairs;
    the 8 G6 pairs come first (verbatim)."""
    out: List[Tuple[str, Tuple[str, str]]] = [(m["type"], tuple(m["options"])) for m in g6.OPTION_PAIRS]
    uses: collections.Counter = collections.Counter(w for _, p in out for w in p)
    used = {frozenset(p) for _, p in out}
    cands: Dict[str, List[Tuple[str, str]]] = {}
    for t, words in OPTION_POOLS.items():
        pairs = [p for p in itertools.combinations(words, 2) if frozenset(p) not in used]
        rng.shuffle(pairs)
        cands[t] = pairs
    types = list(OPTION_POOLS)
    while len(out) < n_pairs:
        progressed = False
        for t in types:
            if len(out) == n_pairs:
                break
            while cands[t]:
                p = cands[t].pop()
                if uses[p[0]] < MAX_WORD_USES and uses[p[1]] < MAX_WORD_USES:
                    out.append((t, p))
                    uses.update(p)
                    progressed = True
                    break
        if not progressed:
            raise RuntimeError(f"only {len(out)} option pairs available under the word-use cap")
    return out


def build_choice(rng: random.Random, n_pairs: int = N_CHOICE_PAIRS) -> List[dict]:
    pairs = select_option_pairs(rng, n_pairs)
    tmpl_slots = [g6.TEMPLATES[i % len(g6.TEMPLATES)] for i in range(n_pairs)]
    rng.shuffle(tmpl_slots)
    items: List[dict] = []
    n = 0
    for k, ((otype, opts), tmpl) in enumerate(zip(pairs, tmpl_slots), start=1):
        cands = list(opts)
        if rng.random() < 0.5:  # canonical candidate order decided by seed; both orders share it
            cands.reverse()
        pair_id = f"xch-p{k:03d}"
        for version in "AB":
            first, second = (cands[0], cands[1]) if version == "A" else (cands[1], cands[0])
            prompt = tmpl["text"].format(o1=first, o2=second)
            n += 1
            item = {
                "item_id": f"xch-{n:04d}", "pair_id": pair_id, "version": version, "family": "choice", "split": "test",
                "template_id": tmpl["id"], "prompt_text": prompt, "render": "chat", "system": None,
                "primary": {"name": "model_choice", "question": "Which of the two options will the model choose?",
                            "candidates": cands, "answer": None, "answer_aliases": [], "answer_source": "target_greedy"},
                "secondary": {"entities": cands, "objects": [], "relation": None},
                "target_answer_regex": r"(?i)\b(" + "|".join(map(re.escape, cands)) + r")\b",
                "construction": {"first_mentioned_candidate": first, "answer_position": None, "cue_position": "n/a",
                                 "other_candidate": None, "option_type": otype, "first_listed_position": cands.index(first),
                                 "options_in_prompt_order": [first, second], "order": 0 if version == "A" else 1},
                "notes": "X3(b) candidate; answer key = target greedy answer (X3 collector); versions swap the option order",
            }
            item["prompt_only_text"] = G.prompt_only_prompt(item)
            items.append(item)
    return items


# --------------------------------------------------------------------------------------
# validation / build
# --------------------------------------------------------------------------------------
def validate(items: List[dict]) -> Dict[str, Any]:
    pz = [it for it in items if it["family"] == "puzzle"]
    ch = [it for it in items if it["family"] == "choice"]
    assert len(pz) == N_PUZZLES and len(ch) == 2 * N_CHOICE_PAIRS and len(items) == len(pz) + len(ch)
    assert len({it["item_id"] for it in items}) == len(items)
    assert all(it["item_id"].startswith("x") for it in items)
    for it in pz:
        p = it["primary"]
        assert it["item_id"].startswith("xpz-") and p["k"] in K_CHOICES
        assert follow(it["construction"]["mapping"], p["start"], p["k"]) == p["trace"]
        assert p["trace"][-1] == p["correct"] == p["answer"] and len(p["trace"]) == p["k"] + 1
        assert p["correct"] != p["start"] and p["correct"] != p["trace"][-2]
        assert len(set(p["trace"])) == len(p["trace"])
        assert it["distractors"] == p["trace"][:-1] and p["correct"] not in it["distractors"]
        assert solve_puzzle(it) == p["correct"]
        assert set(it["construction"]["mapping"]) == set(it["construction"]["rule_order"])
        assert all(s != t for s, t in it["construction"]["mapping"].items())
        assert re.search(it["target_answer_regex"], " " + p["correct"] + " ")
    assert len({it["prompt_text"] for it in pz}) == len(pz)
    k_counts = collections.Counter(it["primary"]["k"] for it in pz)
    assert k_counts == {3: N_PUZZLES // 2, 4: N_PUZZLES // 2}, k_counts
    by_pair: Dict[str, List[dict]] = {}
    for it in ch:
        assert it["item_id"].startswith("xch-") and it["primary"]["answer"] is None
        assert it["prompt_only_text"] == C.PROMPT_ONLY_TEMPLATE.format(prompt_text=it["prompt_text"], question=it["primary"]["question"])
        for c in it["primary"]["candidates"]:
            assert re.search(r"\b" + re.escape(c) + r"\b", it["prompt_text"]) and " " not in c
        assert g6.SHORT_ANSWER_CUE.search(it["prompt_text"])
        first = min(it["primary"]["candidates"], key=lambda c: re.search(r"\b" + re.escape(c) + r"\b", it["prompt_text"]).start())
        assert first == it["construction"]["first_mentioned_candidate"]
        by_pair.setdefault(it["pair_id"], []).append(it)
    assert len(by_pair) == N_CHOICE_PAIRS
    seen_pairs = set()
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["template_id"] == b["template_id"]
        assert a["construction"]["options_in_prompt_order"] == b["construction"]["options_in_prompt_order"][::-1]
        assert (a["construction"]["first_listed_position"], b["construction"]["first_listed_position"]) == (0, 1)
        fs = frozenset(a["primary"]["candidates"])
        assert fs not in seen_pairs
        seen_pairs.add(fs)
    word_uses = collections.Counter(w for pid, pair in by_pair.items() for w in pair[0]["primary"]["candidates"])
    assert max(word_uses.values()) <= MAX_WORD_USES
    return {"puzzles": {"n": len(pz), "k_counts": dict(k_counts), "n_symbols_counts": dict(collections.Counter(it["construction"]["n_symbols"] for it in pz)),
                        "shape_counts": dict(collections.Counter(it["construction"]["shape"] for it in pz))},
            "choice": {"n_items": len(ch), "n_pairs": len(by_pair), "templates": dict(collections.Counter(it["template_id"] for it in ch if it["version"] == "A")),
                       "option_types": dict(collections.Counter(it["construction"]["option_type"] for it in ch if it["version"] == "A")),
                       "max_word_uses": max(word_uses.values())}}


def build(seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    rng = random.Random(seed)
    items = build_puzzles(random.Random(rng.random())) + build_choice(random.Random(rng.random()))
    report = validate(items)
    meta = {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "phase": "X3", "seed": seed,
            "n_items": len(items), "families": ["puzzle", "choice"], "counts": {"puzzle": N_PUZZLES, "choice": 2 * N_CHOICE_PAIRS},
            "sha256_items": sha256_items(items), "frozen": False,
            "prompt_only_template_sha256": C.sha256_bytes(C.PROMPT_ONLY_TEMPLATE.encode()),
            "symbol_regex": SYMBOL_REGEX, "balance_checks": report,
            "notes": "candidates for the X3 selection (target greedy + prompt-only); no model output in this file"}
    return {"meta": meta, "items": items}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    data = build(args.seed)
    if not args.no_write:
        if os.path.exists(args.out):
            with open(args.out, encoding="utf-8") as f:
                if json.load(f).get("meta", {}).get("frozen"):
                    raise SystemExit(f"refusing to overwrite frozen {args.out}")
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"wrote {args.out} ({len(data['items'])} items, sha {data['meta']['sha256_items'][:16]}...)")
    if args.print or args.no_write:
        for it in data["items"][:3] + data["items"][N_PUZZLES: N_PUZZLES + 2]:
            print(it["item_id"].ljust(9), it["prompt_text"])
        print(json.dumps(data["meta"]["balance_checks"], indent=1))


if __name__ == "__main__":
    main()
