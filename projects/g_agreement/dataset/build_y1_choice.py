#!/usr/bin/env python
"""Phase Y1 choice-pool extension (BRIEF_Y.md §Y1): ``dataset/items_y1_choice.json`` with ``meta`` + ``items``.

900 additional two-option choice prompts ``xch-0301..xch-1200`` (450 option pairs ``xch-p151..xch-p600`` x both
orders), built exactly like build_x3.py's X3(b) items: the G6 templates (``build_dataset_g6.TEMPLATES``) round-robin,
typed single-word option pools (``build_x3.OPTION_POOLS`` + the extra pools below, >= 40 types), canonical candidate
order decided by seed, versions A/B swap the option order, ``prompt_only_text`` = the frozen G6 prompt-only self-guess
prompt (``core.generate.prompt_only_prompt``). No option pair of items_x3_candidates.json is reused (asserted: the 150
X3 pairs are read from that file, or from build_x3.select_option_pairs when the file is absent). Answer keys are the
target's own greedy answers, filled by the Y1 collector (y1_site/collect.py --stage select), never here.

No model calls. Deterministic from --seed (default 20261009).
Usage: .venv/bin/python projects/g_agreement/dataset/build_y1_choice.py [--seed 20261009] [--no-write] [--print]
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
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
from projects.g_agreement.dataset import build_x3 as x3  # noqa: E402

DEFAULT_OUT = os.path.join(HERE, "items_y1_choice.json")
X3_CANDIDATES = os.path.join(HERE, "items_x3_candidates.json")
DEFAULT_SEED = 20261009
N_NEW_PAIRS = 450
FIRST_ITEM = 301  # xch-0301 (X3 ends at xch-0300)
FIRST_PAIR = 151  # xch-p151 (X3 ends at xch-p150)
MAX_WORD_USES = 4  # total over X3 + Y1 pairs (X3 alone capped at 2)

# Extra typed pools (single common words; none repeats a word of build_x3.OPTION_POOLS).
EXTRA_POOLS: Dict[str, List[str]] = {
    "body part": ["head", "hand", "foot", "knee", "elbow", "shoulder", "finger", "ankle"],
    "profession": ["doctor", "teacher", "farmer", "baker", "pilot", "nurse", "lawyer", "chef"],
    "room": ["kitchen", "bedroom", "bathroom", "attic", "cellar", "garage", "hallway", "lounge"],
    "language": ["English", "French", "German", "Spanish", "Italian", "Dutch", "Swedish", "Polish"],
    "country": ["France", "Spain", "Japan", "Brazil", "Canada", "Egypt", "India", "Mexico"],
    "dessert": ["cake", "pie", "pudding", "cookie", "brownie", "muffin", "tart", "waffle"],
    "fish": ["salmon", "trout", "tuna", "cod", "herring", "carp", "pike", "mackerel"],
    "insect": ["ant", "bee", "wasp", "beetle", "moth", "butterfly", "ladybird", "grasshopper"],
    "tree": ["oak", "pine", "birch", "maple", "willow", "cedar", "elm", "ash"],
    "fabric": ["cotton", "silk", "wool", "linen", "denim", "velvet", "nylon", "leather"],
    "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "kitchen item": ["spoon", "fork", "knife", "plate", "bowl", "cup", "pan", "kettle"],
    "school subject": ["maths", "history", "physics", "biology", "chemistry", "geography", "art", "literature"],
    "dance": ["waltz", "tango", "salsa", "ballet", "samba", "polka", "foxtrot", "swing"],
    "game": ["chess", "poker", "checkers", "dominoes", "bingo", "darts", "billiards", "backgammon"],
    "spice": ["cinnamon", "ginger", "nutmeg", "cumin", "paprika", "saffron", "basil", "thyme"],
    "sea": ["Atlantic", "Pacific", "Arctic", "Baltic", "Adriatic", "Aegean", "Caspian", "Caribbean"],
    "mountain": ["Everest", "Alps", "Andes", "Rockies", "Fuji", "Kilimanjaro", "Olympus", "Vesuvius"],
    "element": ["oxygen", "hydrogen", "helium", "nitrogen", "carbon", "neon", "argon", "sulfur"],
    "art form": ["painting", "sculpture", "poetry", "drama", "cinema", "opera", "photography", "pottery"],
    "building": ["castle", "church", "tower", "palace", "temple", "cottage", "lighthouse", "barn"],
    "toy": ["doll", "kite", "ball", "yoyo", "marbles", "teddy", "robot", "blocks"],
    "currency": ["dollar", "euro", "pound", "yen", "franc", "rupee", "peso", "krona"],
    "meal": ["breakfast", "lunch", "dinner", "brunch", "supper", "snack", "picnic", "feast"],
    "footwear": ["sneaker", "sandal", "slipper", "loafer", "clog", "heel", "moccasin", "wellington"],
    "sea creature": ["whale", "dolphin", "shark", "octopus", "crab", "lobster", "seal", "jellyfish"],
    "reptile": ["snake", "lizard", "turtle", "crocodile", "gecko", "iguana", "tortoise", "chameleon"],
}


def option_pools() -> Dict[str, List[str]]:
    """X3 pools first (verbatim), then the extra pools; every word in exactly one pool."""
    pools = {t: list(w) for t, w in x3.OPTION_POOLS.items()}
    for t, w in EXTRA_POOLS.items():
        assert t not in pools, t
        pools[t] = list(w)
    words = [w for ws in pools.values() for w in ws]
    dup = [w for w, c in collections.Counter(words).items() if c > 1]
    assert not dup, f"words in more than one pool: {dup}"
    assert all(" " not in w and w.strip() == w for w in words)
    return pools


def x3_option_pairs(path: str = X3_CANDIDATES) -> List[Tuple[str, Tuple[str, str]]]:
    """(type, canonical candidate pair) of the 150 X3 pairs from the frozen candidates file (fallback: regenerate)."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            items = json.load(f)["items"]
        out, seen = [], set()
        for it in items:
            if it["family"] == "choice" and it["pair_id"] not in seen:
                seen.add(it["pair_id"])
                out.append((it["construction"]["option_type"], tuple(it["primary"]["candidates"])))
        assert len(out) == x3.N_CHOICE_PAIRS, len(out)
        return out
    rng = random.Random(x3.DEFAULT_SEED)
    random.Random(rng.random())  # the puzzle rng draw of build_x3.build
    return x3.select_option_pairs(random.Random(rng.random()), x3.N_CHOICE_PAIRS)


def select_new_pairs(rng: random.Random, existing: List[Tuple[str, Tuple[str, str]]], n_pairs: int = N_NEW_PAIRS,
                     pools: Dict[str, List[str]] | None = None, max_uses: int = MAX_WORD_USES) -> List[Tuple[str, Tuple[str, str]]]:
    """n new (type, option pair), round-robin over the types, every word in at most ``max_uses`` pairs counting the
    existing X3 pairs; no pair (as a set) that already exists."""
    pools = pools or option_pools()
    used = {frozenset(p) for _, p in existing}
    uses: collections.Counter = collections.Counter(w for _, p in existing for w in p)
    cands: Dict[str, List[Tuple[str, str]]] = {}
    for t, words in pools.items():
        pairs = [p for p in itertools.combinations(words, 2) if frozenset(p) not in used]
        rng.shuffle(pairs)
        cands[t] = pairs
    types = list(pools)
    out: List[Tuple[str, Tuple[str, str]]] = []
    while len(out) < n_pairs:
        progressed = False
        for t in types:
            if len(out) == n_pairs:
                break
            while cands[t]:
                p = cands[t].pop()
                if uses[p[0]] < max_uses and uses[p[1]] < max_uses:
                    out.append((t, p))
                    uses.update(p)
                    used.add(frozenset(p))
                    progressed = True
                    break
        if not progressed:
            raise RuntimeError(f"only {len(out)} new option pairs available under the word-use cap {max_uses}")
    return out


def make_choice_items(pairs: List[Tuple[str, Tuple[str, str]]], rng: random.Random, first_item: int = FIRST_ITEM,
                      first_pair: int = FIRST_PAIR, notes: str = "Y1 choice-pool extension") -> List[dict]:
    """The X3(b) item construction (build_x3.build_choice) with offset ids."""
    tmpl_slots = [g6.TEMPLATES[i % len(g6.TEMPLATES)] for i in range(len(pairs))]
    rng.shuffle(tmpl_slots)
    items: List[dict] = []
    n = first_item - 1
    for k, ((otype, opts), tmpl) in enumerate(zip(pairs, tmpl_slots), start=first_pair):
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
                "notes": f"{notes}; answer key = target greedy answer (Y1 collector); versions swap the option order",
            }
            item["prompt_only_text"] = G.prompt_only_prompt(item)
            items.append(item)
    return items


def validate(items: List[dict], existing: List[Tuple[str, Tuple[str, str]]], n_pairs: int = N_NEW_PAIRS) -> Dict[str, Any]:
    assert len(items) == 2 * n_pairs and len({it["item_id"] for it in items}) == len(items)
    ids = [int(it["item_id"].split("-")[1]) for it in items]
    assert ids == list(range(FIRST_ITEM, FIRST_ITEM + 2 * n_pairs)), (ids[0], ids[-1])
    by_pair: Dict[str, List[dict]] = {}
    for it in items:
        assert it["family"] == "choice" and it["primary"]["answer"] is None and it["split"] == "test"
        assert it["prompt_only_text"] == C.PROMPT_ONLY_TEMPLATE.format(prompt_text=it["prompt_text"], question=it["primary"]["question"])
        for c in it["primary"]["candidates"]:
            assert re.search(r"\b" + re.escape(c) + r"\b", it["prompt_text"]) and " " not in c
        assert g6.SHORT_ANSWER_CUE.search(it["prompt_text"])
        first = min(it["primary"]["candidates"], key=lambda c: re.search(r"\b" + re.escape(c) + r"\b", it["prompt_text"]).start())
        assert first == it["construction"]["first_mentioned_candidate"]
        by_pair.setdefault(it["pair_id"], []).append(it)
    assert list(by_pair) == [f"xch-p{k:03d}" for k in range(FIRST_PAIR, FIRST_PAIR + n_pairs)]
    old = {frozenset(p) for _, p in existing}
    seen = set()
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["template_id"] == b["template_id"]
        assert a["construction"]["options_in_prompt_order"] == b["construction"]["options_in_prompt_order"][::-1]
        assert (a["construction"]["first_listed_position"], b["construction"]["first_listed_position"]) == (0, 1)
        fs = frozenset(a["primary"]["candidates"])
        assert fs not in old, f"{pid} repeats an X3 option pair {sorted(fs)}"
        assert fs not in seen
        seen.add(fs)
    uses = collections.Counter(w for _, p in existing for w in p)
    uses.update(w for pair in by_pair.values() for w in pair[0]["primary"]["candidates"])
    assert max(uses.values()) <= MAX_WORD_USES
    types = collections.Counter(it["construction"]["option_type"] for it in items if it["version"] == "A")
    assert len(types) >= 40, len(types)
    return {"n_items": len(items), "n_pairs": len(by_pair), "n_types": len(types), "option_types": dict(types),
            "templates": dict(collections.Counter(it["template_id"] for it in items if it["version"] == "A")),
            "max_word_uses_incl_x3": max(uses.values()), "n_x3_pairs_excluded": len(old)}


def build(seed: int = DEFAULT_SEED, x3_candidates: str = X3_CANDIDATES) -> Dict[str, Any]:
    rng = random.Random(seed)
    existing = x3_option_pairs(x3_candidates)
    pairs = select_new_pairs(random.Random(rng.random()), existing)
    items = make_choice_items(pairs, random.Random(rng.random()))
    report = validate(items, existing)
    meta = {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "phase": "Y1", "seed": seed,
            "n_items": len(items), "families": ["choice"], "counts": {"choice": len(items)},
            "id_range": [items[0]["item_id"], items[-1]["item_id"]], "pair_id_range": [items[0]["pair_id"], items[-1]["pair_id"]],
            "sha256_items": x3.sha256_items(items), "frozen": False,
            "prompt_only_template_sha256": C.sha256_bytes(C.PROMPT_ONLY_TEMPLATE.encode()),
            "x3_candidates_sha256": C.sha256_file(x3_candidates), "max_word_uses_incl_x3": MAX_WORD_USES,
            "balance_checks": report,
            "notes": "Y1 extension of the X3 choice pool (BRIEF_Y §Y1): same templates/pools style as build_x3.py, no X3 option pair reused; "
                     "no model output in this file"}
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
        for it in data["items"][:4]:
            print(it["item_id"].ljust(9), it["prompt_text"])
        print(json.dumps(data["meta"]["balance_checks"], indent=1))


if __name__ == "__main__":
    main()
