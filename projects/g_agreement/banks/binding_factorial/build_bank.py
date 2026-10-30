#!/usr/bin/env python
"""Z5 identity-binding factorial bank (BRIEF_Z.md §Z5): 64 cells x 2 pairs = 128 pairs = 256 items, written
to ``items_binding_factorial.json`` in the items.json schema (INTERFACES §1) with the Phase X ``construction``
extension. Generation only: no model calls, no tokenizer.

Why: the Phase X ownership bank is order-confounded (results/g_agreement/x/friday/R2R4.md: PC1 of h_B - h_A is
the mention-order direction and carries 66% of the within-pair variance). Here every nuisance factor is a
crossed, balanced factor of a full factorial, so the within-pair difference can be regressed on it
(``check_variance.py``) before any reader is scored.

Factors (full factorial, every level of every factor equally often; 64 = 4 x 2 x 2 x 2 x 2 cells):
  name_set        ns0..ns3   4 name sets (X, Y); the two names of a set have equal token length under the
                             whitespace heuristic (one whitespace-delimited word each) and equal character length
  template        pos0/pos1  the two ownership statements at different absolute positions: pos1 prepends a fixed
                             neutral lead-in sentence; the statements' token multiset is unchanged
  mention_order   x_first/y_first   which name of the set is in the first statement
  pairing         x_o1/x_o2  the binding of VERSION A: X holds O1 (then Y holds O2) or X holds O2. Version B has
                             the other binding, so A and B of a pair differ ONLY in pairing and are token
                             permutations of each other. This is the within-pair A/B contrast.
  query_direction object_to_name   "Who has the O1?"      candidates = the two names
                  name_to_object   "What does X have?"    candidates = the two objects
Within a cell the two pairs (k = 1, 2) share everything except the object pair (O1, O2): 8 disjoint object pairs
(a seeded perfect matching of the 16 Phase X objects with distinct colour and noun words) each used 16 times,
balanced over every factor level (4 uses per name set, 8 per level of each binary factor); which object of a pair
is O1 is balanced 8/8 per object pair. Answers are re-derived from the prompt text: ``build_dataset.solve_prompt``
for object_to_name (the existing solver) and the additive ``solve_name_to_object`` below for name_to_object (the
existing solver only supports name candidates). The build fails on any disagreement.

Ids: ``zb-<cell>-<k><version>`` (cell 00..63, k 1..2), pair_id ``zb-<cell>-<k>``, family "ownership", split "test".

Usage:
    .venv/bin/python -m projects.g_agreement.banks.binding_factorial.build_bank [--seed 20261010] [--print]
    .venv/bin/python projects/g_agreement/banks/binding_factorial/build_bank.py --no-write --print
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import os
import random
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402
from projects.g_agreement.dataset import build_dataset_x as bdx  # noqa: E402

DEFAULT_OUT = os.path.join(HERE, "items_binding_factorial.json")
DEFAULT_SEED = 20261010
PREFIX = "zb"
FAMILY = "ownership"
SPLIT = "test"
N_CELLS, PAIRS_PER_CELL = 64, 2

# --------------------------------------------------------------------------------------
# Material (fixed; the seed decides only the object matching, its assignment and orientation)
# --------------------------------------------------------------------------------------
# Four name sets (X, Y). Whitespace heuristic: both names are one whitespace-delimited word; as a tie-break
# proxy for BPE length both names of a set also have the same number of characters (4). All eight are common
# Latin-script first names that are not English words.
NAME_SETS: List[Tuple[str, str]] = [("Emma", "Anna"), ("Adam", "Paul"), ("Lisa", "Kate"), ("Eric", "Luke")]
OBJECTS: List[str] = list(bdx.OBJECTS_X)  # 16 "<colour> <noun>" objects, all two whitespace tokens
STATEMENT = "{N} has the {o}."
LEAD_IN = "Consider the following two statements."
TEMPLATES: List[Dict[str, str]] = [
    {"id": "zb-pos0", "level": "pos0", "lead": ""},
    {"id": "zb-pos1", "level": "pos1", "lead": LEAD_IN + " "},
]
QUESTIONS: Dict[str, str] = {
    "object_to_name": "Who has the {o}? Answer with the name only.",
    "name_to_object": "What does {N} have? Answer with the object only.",
}
FACTORS: Dict[str, List[str]] = {
    "name_set": ["ns0", "ns1", "ns2", "ns3"],
    "template": ["pos0", "pos1"],
    "mention_order": ["x_first", "y_first"],
    "pairing": ["x_o1", "x_o2"],
    "query_direction": ["object_to_name", "name_to_object"],
}
FACTOR_ORDER = list(FACTORS)  # cell index = mixed radix over this order (name_set outermost)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def whitespace_tokens(text: str) -> int:
    """The whitespace heuristic for token length: number of whitespace-delimited words."""
    return len(text.split())


def check_name_sets(sets: Sequence[Tuple[str, str]] = NAME_SETS) -> None:
    flat = [n for s in sets for n in s]
    assert len(set(flat)) == len(flat), "names must be distinct across sets"
    for x, y in sets:
        assert whitespace_tokens(x) == whitespace_tokens(y) == 1, (x, y)
        assert len(x) == len(y), ("character-length tie-break", x, y)
        assert re.fullmatch(r"[A-Z][a-z]+", x) and re.fullmatch(r"[A-Z][a-z]+", y), (x, y)


def object_words(obj: str) -> Tuple[str, str]:
    colour, noun = obj.split()
    return colour, noun


def match_objects(rng: random.Random, objects: Sequence[str] = OBJECTS, max_tries: int = 10_000) -> List[Tuple[str, str]]:
    """A seeded perfect matching of the objects into pairs with distinct colour and distinct noun words."""
    objs = list(objects)
    assert len(objs) % 2 == 0
    for _ in range(max_tries):
        rng.shuffle(objs)
        pairs = [(objs[i], objs[i + 1]) for i in range(0, len(objs), 2)]
        if all(object_words(a)[0] != object_words(b)[0] and object_words(a)[1] != object_words(b)[1] for a, b in pairs):
            return [tuple(sorted(p)) for p in pairs]  # canonical order inside a pair; orientation is decided later
    raise RuntimeError("no valid object matching found")


def cells() -> List[Dict[str, Any]]:
    """The 64 cells in fixed enumeration order (name_set outermost, query_direction innermost)."""
    out: List[Dict[str, Any]] = []
    sizes = [len(FACTORS[f]) for f in FACTOR_ORDER]
    for idx in range(N_CELLS):
        digits, r = [], idx
        for size in reversed(sizes):
            digits.append(r % size)
            r //= size
        digits.reverse()
        levels = {f: FACTORS[f][d] for f, d in zip(FACTOR_ORDER, digits)}
        out.append({"cell": f"{idx:02d}", "index": idx, "digits": dict(zip(FACTOR_ORDER, digits)), **levels})
    return out


def object_block(cell: Dict[str, Any]) -> int:
    """Block (0..3) of object pairs for a cell; balanced: every block occurs equally often within every level of
    every factor (ns + (t + p) + 2 (mo + d) mod 4 is uniform over the 16 binary combinations and over each
    half of each binary factor)."""
    d = cell["digits"]
    return (d["name_set"] + d["template"] + d["pairing"] + 2 * (d["mention_order"] + d["query_direction"])) % 4


def assign_objects(rng: random.Random, cell_list: List[Dict[str, Any]], opairs: List[Tuple[str, str]]
                   ) -> Dict[str, List[Tuple[str, str]]]:
    """cell -> [(O1, O2) for k=1, (O1, O2) for k=2]. The 8 object pairs are split into 4 seeded blocks of 2;
    cell -> block by ``object_block`` (plus a seeded rotation); the k order inside a cell is seeded; which object
    of a pair is O1 is balanced 8/8 over the pair's 16 uses (seeded order)."""
    assert len(opairs) == 8
    order = list(opairs)
    rng.shuffle(order)
    blocks = [order[2 * b: 2 * b + 2] for b in range(4)]
    rotation = rng.randrange(4)
    uses: Dict[Tuple[str, str], List[str]] = {}
    orient: Dict[Tuple[str, str], List[bool]] = {}
    for op in opairs:
        o = [True] * 8 + [False] * 8
        rng.shuffle(o)
        orient[op] = o
    out: Dict[str, List[Tuple[str, str]]] = {}
    for cell in cell_list:
        blk = list(blocks[(object_block(cell) + rotation) % 4])
        rng.shuffle(blk)
        oriented = []
        for op in blk:
            flip = orient[op][len(uses.setdefault(op, []))]
            uses[op].append(cell["cell"])
            oriented.append((op[0], op[1]) if flip else (op[1], op[0]))
        out[cell["cell"]] = oriented
    assert all(len(v) == 16 for v in uses.values())
    return out


# --------------------------------------------------------------------------------------
# Item construction
# --------------------------------------------------------------------------------------
def render(template: Dict[str, str], first: Tuple[str, str], second: Tuple[str, str], question: str) -> str:
    s1 = STATEMENT.format(N=first[0], o=first[1])
    s2 = STATEMENT.format(N=second[0], o=second[1])
    return f"{template['lead']}{s1} {s2} {question}"


def make_pair(cell: Dict[str, Any], k: int, objs: Tuple[str, str]) -> List[dict]:
    X, Y = NAME_SETS[cell["digits"]["name_set"]]
    O1, O2 = objs
    template = TEMPLATES[cell["digits"]["template"]]
    direction = cell["query_direction"]
    pair_id = f"{PREFIX}-{cell['cell']}-{k}"
    bindings = {"x_o1": {X: O1, Y: O2}, "x_o2": {X: O2, Y: O1}}
    binding_A = bindings[cell["pairing"]]
    binding_B = bindings["x_o2" if cell["pairing"] == "x_o1" else "x_o1"]
    mention = [X, Y] if cell["mention_order"] == "x_first" else [Y, X]
    if direction == "object_to_name":
        asked_object, asked_name = O1, None
        question = QUESTIONS[direction].format(o=O1)
        ans_A = X if binding_A[X] == O1 else Y
        ans_B = X if binding_B[X] == O1 else Y
        cands = [ans_A, ans_B]
        pname = f"{O1.replace(' ', '_')}_owner"
        pquestion = f"Who has the {O1}?"
    else:
        asked_object, asked_name = None, X
        question = QUESTIONS[direction].format(N=X)
        ans_A, ans_B = binding_A[X], binding_B[X]
        cands = [ans_A, ans_B]
        pname = f"{X.lower()}_object"
        pquestion = f"What does {X} have?"
    assert ans_A != ans_B
    items: List[dict] = []
    for version, binding, ans in (("A", binding_A, ans_A), ("B", binding_B, ans_B)):
        first, second = (mention[0], binding[mention[0]]), (mention[1], binding[mention[1]])
        prompt = render(template, first, second, question)
        other = cands[1 - cands.index(ans)]
        # first-mentioned candidate: the candidate (name or object) that occurs first in the prompt text
        first_mentioned = min(cands, key=lambda c: prompt.index(c))
        primary = {"name": pname, "question": pquestion, "candidates": list(cands), "answer": ans,
                   "answer_aliases": [ans.lower()]}
        if direction == "object_to_name":
            secondary = {"entities": list(cands), "objects": [O1, O2],
                         "relation": {"type": "has", "subject": ans, "object": O1}}
        else:
            secondary = {"entities": [X, Y], "objects": list(cands),
                         "relation": {"type": "has", "subject": X, "object": ans}}
        construction = {
            "cell": cell["cell"], "k": k,
            "name_set": cell["name_set"], "names": [X, Y], "template": cell["template"],
            "mention_order": cell["mention_order"], "pairing": cell["pairing"], "query_direction": direction,
            "object_pair": [O1, O2], "binding": dict(binding), "asked_object": asked_object, "asked_name": asked_name,
            "lead_in": template["lead"].strip() or None,
            "first_mentioned_candidate": first_mentioned, "answer_position": cands.index(ans), "cue_position": "n/a",
            "other_candidate": other, "answer_is_first_mentioned": first_mentioned == ans,
        }
        items.append(bd._item(f"{pair_id}{version}", pair_id, version, FAMILY, SPLIT, template["id"], prompt, primary,
                              secondary, bd._word_regex(ans), construction,
                              notes="Z5 factorial; A/B are token permutations: the two objects swap holders"))
    return items


# --------------------------------------------------------------------------------------
# Solvers (answers re-derived from the prompt text alone)
# --------------------------------------------------------------------------------------
def solve_name_to_object(item: dict) -> Optional[str]:
    """Additive extension of build_dataset.solve_prompt for object candidates: the object that the asked name
    'has' in the prompt text; None unless exactly one candidate object is bound to that name."""
    p, c = item["prompt_text"], item["primary"]["candidates"]
    m = re.search(r"What does (\w+) have\?", p)
    if not m:
        return None
    name = m.group(1)
    hits = re.findall(r"\b" + re.escape(name) + r"\s+has\s+the\s+(" + "|".join(map(re.escape, c)) + r")\b", p)
    hits = sorted(set(hits))
    return hits[0] if len(hits) == 1 else None


def solve_binding(item: dict) -> Optional[str]:
    """object_to_name -> the existing solver; name_to_object -> solve_name_to_object."""
    if item["construction"]["query_direction"] == "object_to_name":
        return bd.solve_prompt(item)
    return solve_name_to_object(item)


# --------------------------------------------------------------------------------------
# Validation and build
# --------------------------------------------------------------------------------------
def word_multiset_without(text: str, drop: Sequence[str]) -> collections.Counter:
    """Word/punctuation multiset of ``text`` with the words of the ``drop`` phrases removed (one occurrence per
    appearance of the phrase)."""
    ms = bdx.word_multiset(text)
    for phrase in drop:
        n = len(re.findall(r"\b" + re.escape(phrase) + r"\b", text))
        for w in phrase.split():
            ms[w] -= n
    return +ms


def validate(items: List[dict]) -> Dict[str, Any]:
    """AssertionError on any violation; returns the counterbalancing report."""
    assert len(items) == 2 * PAIRS_PER_CELL * N_CELLS, len(items)
    assert len({it["item_id"] for it in items}) == len(items)
    assert len({it["prompt_text"] for it in items}) == len(items), "prompts must be distinct"
    by_pair: Dict[str, List[dict]] = {}
    by_cell: Dict[str, List[dict]] = {}
    for it in items:
        assert bd.REQUIRED_KEYS <= set(it)
        c = it["construction"]
        assert it["item_id"] == it["pair_id"] + it["version"] and it["item_id"].startswith(PREFIX + "-")
        assert it["family"] == FAMILY and it["split"] == SPLIT and it["render"] == "chat" and it["system"] is None
        pr = it["primary"]
        assert len(pr["candidates"]) == 2 and len(set(pr["candidates"])) == 2 and pr["answer"] in pr["candidates"]
        assert pr["candidates"].index(pr["answer"]) == ("A", "B").index(it["version"]), it["item_id"]
        re.compile(it["target_answer_regex"])
        assert re.search(it["target_answer_regex"], pr["answer"]) and not re.search(it["target_answer_regex"], c["other_candidate"])
        assert len(it["prompt_text"]) < 260
        assert re.search(r"Answer with the (name|object) only\.$", it["prompt_text"])
        solved = solve_binding(it)
        assert solved == pr["answer"], ("solver disagrees", it["item_id"], solved, pr["answer"])
        for f, levels in FACTORS.items():
            assert c[f] in levels, (it["item_id"], f, c[f])
        if c["query_direction"] == "object_to_name":
            assert set(pr["candidates"]) == set(c["names"]) and c["asked_object"] == c["object_pair"][0]
        else:
            assert set(pr["candidates"]) == set(c["object_pair"]) and c["asked_name"] == c["names"][0]
        assert c["answer_is_first_mentioned"] == (c["first_mentioned_candidate"] == pr["answer"])
        by_pair.setdefault(it["pair_id"], []).append(it)
        by_cell.setdefault(c["cell"], []).append(it)
    assert len(by_pair) == PAIRS_PER_CELL * N_CELLS and len(by_cell) == N_CELLS
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert (a["version"], b["version"]) == ("A", "B")
        for key in ("family", "split", "template_id"):
            assert a[key] == b[key], (pid, key)
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["primary"]["answer"] != b["primary"]["answer"]
        assert a["primary"]["name"] == b["primary"]["name"] and a["primary"]["question"] == b["primary"]["question"]
        ca, cb = a["construction"], b["construction"]
        for f in FACTORS:
            assert ca[f] == cb[f], (pid, f)  # pairing is the cell's level = the binding of version A
        assert ca["binding"] != cb["binding"] and ca["object_pair"] == cb["object_pair"]
        assert bdx.word_multiset(a["prompt_text"]) == bdx.word_multiset(b["prompt_text"]), (pid, "not a token permutation")
        assert a["prompt_text"] != b["prompt_text"]
    # within a cell: token multiset fixed across the two pairs except the object pair
    for cid, cell_items in by_cell.items():
        ks = {it["construction"]["k"] for it in cell_items}
        assert ks == set(range(1, PAIRS_PER_CELL + 1)) and len(cell_items) == 2 * PAIRS_PER_CELL
        stripped = {json.dumps(sorted(word_multiset_without(it["prompt_text"], it["construction"]["object_pair"]).items()))
                    for it in cell_items if it["version"] == "A"}
        assert len(stripped) == 1, (cid, "token multiset differs across pairs beyond the object pair")
        ops = [tuple(it["construction"]["object_pair"]) for it in cell_items if it["version"] == "A"]
        assert len(set(ops)) == PAIRS_PER_CELL and len({frozenset(o) for o in ops}) == PAIRS_PER_CELL
    # factorial balance (per pair; both pairs of a cell share the cell's levels)
    pairs_A = [p[0] if p[0]["version"] == "A" else p[1] for p in by_pair.values()]
    report: Dict[str, Any] = {"n_cells": N_CELLS, "n_pairs": len(by_pair), "n_items": len(items), "factors": {}}
    for f, levels in FACTORS.items():
        cnt = collections.Counter(it["construction"][f] for it in pairs_A)
        assert set(cnt) == set(levels) and len(set(cnt.values())) == 1, (f, cnt)
        report["factors"][f] = dict(cnt)
    # object-pair usage: 16 per pair, balanced across every factor level, O1 orientation 8/8
    op_uses = collections.Counter(frozenset(it["construction"]["object_pair"]) for it in pairs_A)
    assert len(op_uses) == 8 and set(op_uses.values()) == {PAIRS_PER_CELL * N_CELLS // 8}, op_uses
    for f, levels in FACTORS.items():
        for lv in levels:
            cnt = collections.Counter(frozenset(it["construction"]["object_pair"]) for it in pairs_A if it["construction"][f] == lv)
            assert len(cnt) == 8 and len(set(cnt.values())) == 1, (f, lv, cnt)
    o1_uses = collections.Counter(it["construction"]["object_pair"][0] for it in pairs_A)
    assert set(o1_uses.values()) == {PAIRS_PER_CELL * N_CELLS // 16}, o1_uses
    report["object_pairs"] = {" | ".join(sorted(k)): v for k, v in op_uses.items()}
    report["o1_uses_per_object"] = dict(o1_uses)
    report["uses_per_object_pair_per_factor_level"] = PAIRS_PER_CELL * N_CELLS // 8 // 2
    report["answer_is_first_mentioned_A"] = {f"{d}:{v}": n for (d, v), n in sorted(collections.Counter(
        (it["construction"]["query_direction"], it["construction"]["answer_is_first_mentioned"]) for it in pairs_A).items())}
    return report


def build(seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    check_name_sets()
    rng = random.Random(seed)
    opairs = match_objects(random.Random(rng.random()))
    cell_list = cells()
    objs_for = assign_objects(random.Random(rng.random()), cell_list, opairs)
    items: List[dict] = []
    for cell in cell_list:
        for k in range(1, PAIRS_PER_CELL + 1):
            items += make_pair(cell, k, objs_for[cell["cell"]][k - 1])
    report = validate(items)
    cell_table = [{"cell": c["cell"], **{f: c[f] for f in FACTOR_ORDER}, "object_pairs": [list(o) for o in objs_for[c["cell"]]]}
                  for c in cell_list]
    meta = {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "phase": "Z", "module": "z5",
            "bank": "binding_factorial", "seed": seed, "n_cells": N_CELLS, "pairs_per_cell": PAIRS_PER_CELL,
            "n_pairs": len(items) // 2, "n_items": len(items), "families": [FAMILY], "id_prefix": PREFIX, "split": SPLIT,
            "factors": FACTORS, "factor_order": FACTOR_ORDER, "name_sets": [list(s) for s in NAME_SETS],
            "name_token_heuristic": "whitespace: one whitespace-delimited word per name; tie-break: equal character length",
            "templates": TEMPLATES, "statement": STATEMENT, "questions": QUESTIONS,
            "object_pairs": [list(o) for o in opairs], "cells": cell_table,
            "sha256_items": bd.sha256_items(items), "frozen": False, "balance_checks": report,
            "notes": "A/B are token permutations (word multiset equal); within a cell the two pairs differ only in the object pair; "
                     "answers re-derived by build_dataset.solve_prompt (object_to_name) and solve_name_to_object (name_to_object); "
                     "pairing = binding of version A; ids disjoint from items.json / items_x.json"}
    return {"meta": meta, "items": items}


def load_items(path: str = DEFAULT_OUT) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def summary_table(data: Dict[str, Any]) -> str:
    m, rep = data["meta"], data["meta"]["balance_checks"]
    lines = [f"items_binding_factorial.json  seed={m['seed']}  cells={m['n_cells']}  pairs={m['n_pairs']}  items={m['n_items']}  "
             f"sha={m['sha256_items'][:16]}...",
             f"{'factor':16} {'levels':50} per-level pairs"]
    for f, cnt in rep["factors"].items():
        lines.append(f"{f:16} {', '.join(cnt):50} {sorted(set(cnt.values()))[0]}")
    lines.append(f"name sets: {m['name_sets']}")
    lines.append(f"object pairs (uses each): {rep['object_pairs']}")
    lines.append(f"answer first-mentioned in A by direction: {rep['answer_is_first_mentioned_A']}")
    lines.append("")
    shown = set()
    for it in data["items"]:
        key = (it["construction"]["query_direction"], it["construction"]["template"])
        if key in shown or it["version"] != "A":
            continue
        shown.add(key)
        pair = [x for x in data["items"] if x["pair_id"] == it["pair_id"]]
        for x in sorted(pair, key=lambda z: z["version"]):
            lines.append(f"{x['item_id']:12} {key[0]:15} {key[1]:5} ans={x['primary']['answer']:12} {x['prompt_text']}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    data = build(args.seed)
    if not args.no_write:
        if os.path.exists(args.out):
            old = load_items(args.out)
            if old.get("meta", {}).get("frozen"):
                raise SystemExit(f"refusing to overwrite frozen bank {args.out}")
            if old["meta"]["sha256_items"] != data["meta"]["sha256_items"]:
                print(f"WARNING: items changed vs existing file (old sha {old['meta']['sha256_items'][:12]}...)")
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"wrote {args.out} ({len(data['items'])} items, sha {data['meta']['sha256_items'][:16]}...)")
    if args.print or args.no_write:
        print(summary_table(data))


if __name__ == "__main__":
    main()
