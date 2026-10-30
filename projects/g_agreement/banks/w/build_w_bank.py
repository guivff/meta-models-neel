#!/usr/bin/env python
"""Phase W Track A graded bank (PREREG_WV.md §Track A; brief_wv.md "Track A"): three new families written to
``items_w.json`` in the items.json schema (INTERFACES §1) with the Phase X/Z5 ``construction`` extension, the
mapping-8 index ``mapping8_index.json`` (no new prompts: the 47 X mapping test pairs scored over all 8 symbols)
and the V7 target-private pilot ``items_v7.json``. Generation only: no model calls, no tokenizer. Deterministic
from --seed (default 20261011).

Families (all split "test"):
  counts      600 prompts "There are N <object> in the <place>. ... How many <object>?", N = 1..99 (93 values x 6
              uses + 6 values x 7 uses), 4 templates x 3 objects = 12 cells of exactly 50 prompts, 12 places x 50.
              Per value: each object exactly twice, every template at least once and at most twice (pattern 2,2,1,1
              with the doubled templates varying by a seeded template permutation); the 6 seven-use values get one
              more (template, object) cell from the extras group. Places: 4 per place per cell plus 2 rotating
              extras, so every place has exactly 50 uses and 4-5 per cell. Exactness comes from pairing the
              100 "groups" (99 values + the 6-extra-uses group): the two groups of a pair take the two complementary
              6-cell windows of a 12-cycle, so every (template, object) cell is hit exactly 50 times.
              answer = str(N); candidates = [str(N)]; candidates_all = "1".."99" (graded scoring). ids wcnt-0001..
  ownership4  64 pairs = 128 prompts, the Z5 factorial machinery with FOUR names each holding a distinct object.
              Factors (pairwise balanced within every name set; cell = 16 x name_set + 4 x block + mention_order):
                name_set       ns0..ns3 (4 names each, one whitespace token, 4 characters)
                template       pos0 / pos1 (pos1 prepends the lead-in "Consider the following four statements.")
                mention_order  m0..m3: statement position p shows name p XOR c (Klein Latin square; every name at
                               every position once over the four levels)
                holder         n0..n3: which name of the set holds the asked object in VERSION A; holder = block XOR
                               (w*c) over GF(4), so the answer's statement position (holder XOR c) is balanced against
                               template, query_direction, mention_order and holder (with cyclic rotations it would be
                               a function of template x query_direction)
                query_direction object_to_name ("Who has the O1? Answer with the name only.", candidates = the 4
                               names) / name_to_object ("What does <holder> have? Answer with the object only.",
                               candidates = the 4 objects)
                holder_b_shift 1..3 (22/21/21, seeded, stratified by name set x pos_A): version B's holder is the
                               name mentioned ``shift`` statements after A's holder (cyclically), so the answer's
                               statement position moves by ``shift``; A and B differ ONLY in that the two holders
                               exchange their objects (token permutations).
              Objects: the 16 Phase X objects in 4 seeded quadruples with distinct colour and noun words, each used
              16 times, the asked object rotating through the quadruple (4 uses each). ids wown-<cell>A/B.
  arith       100 prompts in Michael Kenney's exact arithmetic format (nla-consistency/scripts/thread12_pod.py
              ``arith_prompts``): text f"{a} {op} {b} =", op alternating "-" (even index) / "+" (odd index) -> 50/50,
              a ~ U{2..99}, b ~ U{1..a-1} for "-" (answer >= 1) and U{1..99} for "+"; triples that occur in his 600
              (nla-consistency/data/arithmetic.jsonl) are excluded; every decade 0..9 of a and of b is covered
              (rejection on the whole set, deterministic). render "plain": NO chat template, add_special_tokens=False,
              read position = the last token "=" (see README). answer = str(a +/- b); candidates = [answer];
              candidates_all = "0".."198". ids warith-001..
  mapping8    no prompts here; ``mapping8_index.json`` lists the 47 X mapping test pairs (94 item ids, answers)
              with candidates_all = A..H.
V7 (items_v7.json): 16 ownership pairs; the binding lives ONLY in ``preamble`` (shown to the target at capture as
a system turn, ``preamble_role`` = "system"); ``prompt_text`` (the visible prompt) is identical within a pair;
``prompt_only_text`` is core.config.PROMPT_ONLY_TEMPLATE over the visible prompt only. ids wv7-01A..

Usage:
    .venv/bin/python -m projects.g_agreement.banks.w.build_w_bank [--seed 20261011] [--out-dir banks/w] [--print]
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
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from projects.g_agreement.banks.binding_factorial import build_bank as BB  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402
from projects.g_agreement.dataset import build_dataset_x as bdx  # noqa: E402

DEFAULT_SEED = 20261011
DEFAULT_OUT_DIR = HERE
ITEMS_W = os.path.join(HERE, "items_w.json")
ITEMS_V7 = os.path.join(HERE, "items_v7.json")
MAPPING8_INDEX = os.path.join(HERE, "mapping8_index.json")
ITEMS_X = os.path.join(REPO, "projects", "g_agreement", "dataset", "items_x.json")
MICHAEL_ARITH = os.path.join(REPO, "nla-consistency", "data", "arithmetic.jsonl")
SPLIT = "test"
FAMILIES = ["counts", "ownership4", "arith"]
PREFIX = {"counts": "wcnt", "ownership4": "wown", "arith": "warith", "v7": "wv7"}

# ======================================================================================
# counts
# ======================================================================================
N_COUNTS, N_MIN, N_MAX = 600, 1, 99
COUNT_VALUES = list(range(N_MIN, N_MAX + 1))
N_EXTRA = N_COUNTS - 6 * len(COUNT_VALUES)  # 6 values get a 7th use
COUNT_OBJECTS: List[Tuple[str, str]] = [("marble", "marbles"), ("apple", "apples"), ("coin", "coins")]  # (singular, plural)
COUNT_PLACES: List[str] = ["jar", "basket", "box", "drawer", "bag", "bowl", "crate", "bucket", "tray", "chest", "sack", "bin"]
# {be} = is/are and {obj} = singular/plural are chosen by N (N = 1 is singular); the question is always plural.
COUNT_TEMPLATES: List[Dict[str, str]] = [
    {"id": "cnt-t1", "level": "t1",
     "text": "There {be} {N} {obj} in the {place}. How many {objp} are in the {place}? Answer with the number only."},
    {"id": "cnt-t2", "level": "t2",
     "text": "In the {place} there {be} {N} {obj}. How many {objp} are in the {place}? Reply with the number only."},
    {"id": "cnt-t3", "level": "t3",
     "text": "The {place} contains {N} {obj}. How many {objp} does the {place} contain? Answer with the number only."},
    {"id": "cnt-t4", "level": "t4",
     "text": "Someone counted the {objp} in the {place}: there {be} {N}. How many {objp} are in the {place}? Give just the number."},
]
COUNT_QUESTION = "How many {objp} are in the {place}?"
COUNT_FACTORS: Dict[str, List[str]] = {
    "template": [t["level"] for t in COUNT_TEMPLATES],
    "object": [o[1] for o in COUNT_OBJECTS],
    "place": list(COUNT_PLACES),
    "decade": [f"d{d}" for d in range(10)],
}
COUNT_CELLS = [(t, o) for t in range(len(COUNT_TEMPLATES)) for o in range(len(COUNT_OBJECTS))]  # 12
PER_CELL = N_COUNTS // len(COUNT_CELLS)  # 50


def decade(n: int) -> str:
    return f"d{n // 10}"


def twelve_cycle(sigma: Sequence[int]) -> List[Tuple[int, int]]:
    """The 12 (template, object) cells in the order (sigma[i % 4], i % 3), i = 0..11: all 12 distinct (lcm 12); any
    6 consecutive cells have every object twice and every template once or twice (pattern 2,2,1,1); the windows
    [0:6] and [6:12] partition the 12 cells."""
    return [(sigma[i % 4], i % 3) for i in range(12)]


def pick_extra_values(rng: random.Random) -> List[int]:
    """The 6 values that get a 7th use: one from each sixth of 1..99 (seeded), recorded in meta."""
    bins = [COUNT_VALUES[i * len(COUNT_VALUES) // N_EXTRA:(i + 1) * len(COUNT_VALUES) // N_EXTRA] for i in range(N_EXTRA)]
    return [rng.choice(b) for b in bins]


def counts_design(rng: random.Random) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """600 slots {N, template, object, place}. Groups = 99 values (6 uses) + 1 extras group (the 6 extra values, one
    use each); groups are paired by seed within a decade; each pair gets a seeded template permutation sigma and its
    two members take the complementary windows of twelve_cycle(sigma) (seeded which). Places: inside each cell a seeded cycle
    through a seeded permutation of the 12 places (50 slots -> 4 or 5 uses per place per cell), then a seeded
    shuffle of the cell's slots so place is not tied to N."""
    extras = pick_extra_values(rng)
    groups: List[List[int]] = [[n] * 6 for n in COUNT_VALUES] + [list(extras)]
    # groups are paired WITHIN a decade (a pair contributes exactly 3 uses of every template, so each decade of ten
    # values has every template exactly 15 times); decade 0 has nine values: its leftover pairs with the extras group
    group_pairs: List[Tuple[int, int]] = []
    leftover: Optional[int] = None
    for d in range(10):
        vals = [n for n in COUNT_VALUES if n // 10 == d]
        rng.shuffle(vals)
        if len(vals) % 2:
            leftover = vals.pop()
        group_pairs += [(vals[i] - N_MIN, vals[i + 1] - N_MIN) for i in range(0, len(vals), 2)]
    assert leftover is not None
    group_pairs.append((leftover - N_MIN, len(groups) - 1))
    rng.shuffle(group_pairs)
    perms = list(itertools.permutations(range(len(COUNT_TEMPLATES))))
    rng.shuffle(perms)
    slots: List[Dict[str, Any]] = []
    for pi, (g1, g2) in enumerate(group_pairs):
        sigma = perms[pi % len(perms)]
        cyc = twelve_cycle(sigma)
        w1, w2 = cyc[:6], cyc[6:]
        if rng.random() < 0.5:
            w1, w2 = w2, w1
        for g, win in ((g1, w1), (g2, w2)):
            vals = list(groups[g])
            rng.shuffle(vals)
            for n, (t, o) in zip(vals, win):
                slots.append({"N": n, "template": t, "object": o, "group": g})
    assert len(slots) == N_COUNTS
    # places: balanced inside each cell
    by_cell: Dict[Tuple[int, int], List[Dict[str, Any]]] = collections.defaultdict(list)
    for s in slots:
        by_cell[(s["template"], s["object"])].append(s)
    places = list(range(len(COUNT_PLACES)))
    rng.shuffle(places)
    n_pl, base, extra = len(places), PER_CELL // len(places), PER_CELL % len(places)  # 12, 4, 2
    for ci, (cell, cs) in enumerate(sorted(by_cell.items())):
        assert len(cs) == PER_CELL, (cell, len(cs))
        # every place ``base`` times per cell plus ``extra`` rotating places, so each place has exactly 50 uses overall
        seq = places * base + [places[(extra * ci + j) % n_pl] for j in range(extra)]
        rng.shuffle(seq)
        for s, p in zip(cs, seq):
            s["place"] = p
    # a seeded global order for ids (so wcnt-0001.. is not sorted by cell or value)
    rng.shuffle(slots)
    return slots, {"extra_values": extras, "n_groups": len(groups), "template_permutations_used": len(perms)}


def count_prompt(tmpl: Dict[str, str], n: int, obj: Tuple[str, str], place: str) -> str:
    sing, plur = obj
    return tmpl["text"].format(be="is" if n == 1 else "are", N=n, obj=sing if n == 1 else plur, objp=plur, place=place)


def build_counts(rng: random.Random) -> Tuple[List[dict], Dict[str, Any]]:
    slots, design_meta = counts_design(rng)
    items: List[dict] = []
    for i, s in enumerate(slots, start=1):
        n, tmpl, obj, place = s["N"], COUNT_TEMPLATES[s["template"]], COUNT_OBJECTS[s["object"]], COUNT_PLACES[s["place"]]
        prompt = count_prompt(tmpl, n, obj, place)
        item_id = f"{PREFIX['counts']}-{i:04d}"
        primary = {"name": f"{obj[1]}_count", "question": COUNT_QUESTION.format(objp=obj[1], place=place),
                   "candidates": [str(n)], "candidates_all": [str(v) for v in COUNT_VALUES], "answer": str(n),
                   "answer_aliases": [str(n)]}
        secondary = {"entities": [], "objects": [obj[1]], "relation": {"type": "count", "subject": place, "object": obj[1], "value": n}}
        construction = {"value": n, "decade": decade(n), "template": tmpl["level"], "object": obj[1], "object_singular": obj[0],
                        "place": place, "singular": n == 1, "group": s["group"], "singleton": True,
                        "first_mentioned_candidate": str(n), "answer_position": 0, "cue_position": "n/a", "other_candidate": None}
        it = bd._item(item_id, item_id, "A", "counts", SPLIT, tmpl["id"], prompt, primary, secondary,
                      r"(?<!\d)" + str(n) + r"(?!\d)", construction,
                      notes="graded family; singleton (pair_id = item_id); score natively over candidates_all")
        items.append(it)
    return items, design_meta


def solve_count(item: dict) -> Optional[str]:
    """Re-derive the count from the prompt text: the single integer in it."""
    nums = re.findall(r"(?<![\w])(\d+)(?![\w])", item["prompt_text"])
    return nums[0] if len(nums) == 1 else None


# ======================================================================================
# ownership4
# ======================================================================================
NAME_SETS4: List[Tuple[str, str, str, str]] = [("Emma", "Anna", "Lisa", "Kate"), ("Adam", "Paul", "Eric", "Luke"),
                                              ("Mira", "Nora", "Rosa", "Vera"), ("Hugo", "Noah", "Finn", "Theo")]
OBJECTS4: List[str] = list(bdx.OBJECTS_X)
LEAD_IN4 = "Consider the following four statements."
TEMPLATES4: List[Dict[str, str]] = [{"id": "wown-pos0", "level": "pos0", "lead": ""},
                                    {"id": "wown-pos1", "level": "pos1", "lead": LEAD_IN4 + " "}]
QUESTIONS4 = dict(BB.QUESTIONS)  # same wording as Z5
FACTORS4: Dict[str, List[str]] = {
    "name_set": ["ns0", "ns1", "ns2", "ns3"],
    "template": ["pos0", "pos1"],
    "mention_order": ["m0", "m1", "m2", "m3"],
    "holder": ["n0", "n1", "n2", "n3"],
    "query_direction": ["object_to_name", "name_to_object"],
}
NEAR_BALANCED4 = {"holder_b_shift": ["1", "2", "3"]}
N_PAIRS4 = 64


def check_name_sets4(sets: Sequence[Tuple[str, ...]] = NAME_SETS4) -> None:
    flat = [n for s in sets for n in s]
    assert len(set(flat)) == len(flat), "names must be distinct across sets"
    for s in sets:
        assert len(s) == 4
        for n in s:
            assert BB.whitespace_tokens(n) == 1 and len(n) == 4 and re.fullmatch(r"[A-Z][a-z]+", n), n


def match_object_quads(rng: random.Random, objects: Sequence[str] = OBJECTS4, max_tries: int = 100_000) -> List[Tuple[str, ...]]:
    """A seeded partition of the 16 objects into 4 quadruples with distinct colour and distinct noun words."""
    objs = list(objects)
    for _ in range(max_tries):
        rng.shuffle(objs)
        quads = [tuple(objs[i:i + 4]) for i in range(0, 16, 4)]
        ok = all(len({BB.object_words(o)[0] for o in q}) == 4 and len({BB.object_words(o)[1] for o in q}) == 4 for q in quads)
        if ok:
            return [tuple(sorted(q)) for q in quads]
    raise RuntimeError("no valid object quadruple partition found")


# GF(4) multiplication by the primitive element w (0, 1, w, w^2 <-> 0, 1, 2, 3): c -> w*c. Both w*c and (w*c) XOR c
# (= w^2*c) are permutations of {0..3}, which is what makes the answer's statement position balanced below (Z4 has no
# such map: with cyclic rotations the position would be a function of the block, i.e. of template x query_direction).
GF4_MUL_W = [0, 2, 3, 1]


def mention_for(names: Sequence[str], c: int) -> List[str]:
    """Mention order m<c>: statement position p shows name p XOR c (the Klein-group Latin square: every name appears
    at every position exactly once over c = 0..3)."""
    return [names[p ^ c] for p in range(4)]


def cells4() -> List[Dict[str, Any]]:
    """64 cells: i = 16*name_set + 4*block + c; mention_order = m<c>, holder = n<block XOR (w*c)>, query_direction =
    block % 2, template = block // 2. Within a name set every pair of design factors is balanced (mention_order x
    holder is a Latin square; template and query_direction are the two bits of the block) AND the statement position
    of A's answer, pos_A = holder XOR c = block XOR (w^2*c), is balanced against every factor (a permutation in c
    for fixed block and in block for fixed c)."""
    out = []
    for i in range(N_PAIRS4):
        ns, block, c = i // 16, (i // 4) % 4, i % 4
        h = block ^ GF4_MUL_W[c]
        out.append({"cell": f"{i:02d}", "index": i, "name_set": FACTORS4["name_set"][ns], "ns": ns,
                    "template": FACTORS4["template"][block // 2], "t": block // 2,
                    "mention_order": FACTORS4["mention_order"][c], "c": c,
                    "holder": FACTORS4["holder"][h], "h": h,
                    "query_direction": FACTORS4["query_direction"][block % 2]})
    return out


def assign_shifts4(rng: random.Random, cell_list: List[Dict[str, Any]]) -> None:
    """holder_b_shift in {1,2,3}: version B's holder is the name mentioned ``shift`` statements after A's holder
    (cyclically), so pos_B = pos_A + shift mod 4. Within a name set the four cells sharing a pos_A level get the
    pattern (s, s, s', s'') with the doubled shift s rotating over pos_A levels and name sets (6/5/5 per name set,
    22/21/21 overall); the doubled shift goes to one cell of each template (seeded which), the two single shifts to
    the other two cells in seeded order."""
    start = rng.randrange(3)
    for ns in range(4):
        for pos in range(4):
            group = [c for c in cell_list if c["ns"] == ns and (c["h"] ^ c["c"]) == pos]
            assert len(group) == 4 and sorted(c["t"] for c in group) == [0, 0, 1, 1]
            dbl = (start + ns + pos) % 3
            singles = [k for k in range(3) if k != dbl]
            rng.shuffle(singles)
            by_t = {t: [c for c in group if c["t"] == t] for t in (0, 1)}
            rest = []
            for t in (0, 1):
                rng.shuffle(by_t[t])
                by_t[t][0]["shift"] = 1 + dbl
                rest.append(by_t[t][1])
            for c, k in zip(rest, singles):
                c["shift"] = 1 + k


def assign_objects4(rng: random.Random, cell_list: List[Dict[str, Any]], quads: List[Tuple[str, ...]]) -> None:
    """quad index = (c + ns) % 4 (balanced against every factor overall); the asked object rotates through the
    quadruple (each of the 4 objects asked 4 times per quad, seeded order); the other three objects are assigned to
    the other three names by a seeded permutation."""
    asked_order: Dict[int, List[int]] = {}
    for q in range(4):
        o = [0, 1, 2, 3] * 4
        rng.shuffle(o)
        asked_order[q] = o
    uses = collections.Counter()
    for c in cell_list:
        q = (c["c"] + c["ns"]) % 4
        quad = list(quads[q])
        a_idx = asked_order[q][uses[q]]
        uses[q] += 1
        asked = quad[a_idx]
        others = [o for o in quad if o != asked]
        rng.shuffle(others)
        c["quad"] = q
        c["asked_object"] = asked
        c["other_objects"] = others  # objects of the three non-holder names, in set order of those names


def render4(template: Dict[str, str], statements: List[Tuple[str, str]], question: str) -> str:
    body = " ".join(BB.STATEMENT.format(N=n, o=o) for n, o in statements)
    return f"{template['lead']}{body} {question}"


def make_pair4(cell: Dict[str, Any]) -> List[dict]:
    names = list(NAME_SETS4[cell["ns"]])
    template = TEMPLATES4[cell["t"]]
    direction = cell["query_direction"]
    hA = cell["h"]
    mention = mention_for(names, cell["c"])
    pos_A = mention.index(names[hA])
    hB = names.index(mention[(pos_A + cell["shift"]) % 4])
    O1 = cell["asked_object"]
    binding_A = {names[hA]: O1}
    for n, o in zip([names[k] for k in range(4) if k != hA], cell["other_objects"]):
        binding_A[n] = o
    binding_B = dict(binding_A)
    binding_B[names[hA]], binding_B[names[hB]] = binding_A[names[hB]], binding_A[names[hA]]
    objects = [binding_A[n] for n in names]
    if direction == "object_to_name":
        question = QUESTIONS4[direction].format(o=O1)
        ans_A, ans_B = names[hA], names[hB]
        cands = [ans_A, ans_B] + [n for n in names if n not in (ans_A, ans_B)]
        pname, pquestion = f"{O1.replace(' ', '_')}_owner", f"Who has the {O1}?"
        asked_name = None
    else:
        asked_name = names[hA]
        question = QUESTIONS4[direction].format(N=asked_name)
        ans_A, ans_B = binding_A[asked_name], binding_B[asked_name]
        cands = [ans_A, ans_B] + [o for o in objects if o not in (ans_A, ans_B)]
        pname, pquestion = f"{asked_name.lower()}_object", f"What does {asked_name} have?"
    assert ans_A != ans_B and len(set(cands)) == 4
    pair_id = f"{PREFIX['ownership4']}-{cell['cell']}"
    items: List[dict] = []
    for version, binding, ans in (("A", binding_A, ans_A), ("B", binding_B, ans_B)):
        statements = [(n, binding[n]) for n in mention]
        prompt = render4(template, statements, question)
        first_mentioned = min(cands, key=lambda c: prompt.index(c))
        holder_now = next(n for n, o in binding.items() if o == O1)
        primary = {"name": pname, "question": pquestion, "candidates": list(cands), "answer": ans, "answer_aliases": [ans.lower()]}
        if direction == "object_to_name":
            secondary = {"entities": list(names), "objects": [O1] + [o for o in objects if o != O1],
                         "relation": {"type": "has", "subject": ans, "object": O1}}
        else:
            secondary = {"entities": list(names), "objects": list(cands),
                         "relation": {"type": "has", "subject": asked_name, "object": ans}}
        construction = {
            "cell": cell["cell"], "name_set": cell["name_set"], "names": list(names), "template": cell["template"],
            "mention_order": cell["mention_order"], "mention": list(mention), "holder": cell["holder"],
            "holder_b_shift": str(cell["shift"]), "holder_name_A": names[hA], "holder_name_B": names[hB],
            "holder_name": holder_now, "query_direction": direction,
            "object_quad": cell["quad"], "objects": list(objects), "binding": dict(binding),
            "asked_object": O1, "asked_name": asked_name, "lead_in": template["lead"].strip() or None,
            "answer_mention_position": mention.index(holder_now),
            "first_mentioned_candidate": first_mentioned, "answer_position": cands.index(ans), "cue_position": "n/a",
            "other_candidate": cands[1 - cands.index(ans)], "other_candidates": [c for c in cands if c != ans],
            "answer_is_first_mentioned": first_mentioned == ans,
        }
        items.append(bd._item(f"{pair_id}{version}", pair_id, version, "ownership4", SPLIT, template["id"], prompt, primary,
                              secondary, bd._word_regex(ans), construction,
                              notes="W ownership-4 factorial; A/B are token permutations: the two holders exchange their objects"))
    return items


def solve_binding4(item: dict) -> Optional[str]:
    """Answers re-derived from the prompt text alone (the Z5 solvers accept any number of candidates)."""
    if item["construction"]["query_direction"] == "object_to_name":
        return bd.solve_prompt({**item, "family": "ownership"})
    return BB.solve_name_to_object(item)


def build_ownership4(rng: random.Random) -> Tuple[List[dict], Dict[str, Any]]:
    check_name_sets4()
    quads = match_object_quads(random.Random(rng.random()))
    cell_list = cells4()
    assign_shifts4(random.Random(rng.random()), cell_list)
    assign_objects4(random.Random(rng.random()), cell_list, quads)
    items: List[dict] = []
    for cell in cell_list:
        items += make_pair4(cell)
    cell_table = [{"cell": c["cell"], **{f: c[f] for f in FACTORS4}, "holder_b_shift": c["shift"], "object_quad": c["quad"],
                   "asked_object": c["asked_object"]} for c in cell_list]
    return items, {"object_quads": [list(q) for q in quads], "cells": cell_table}


# ======================================================================================
# arith (Michael's format)
# ======================================================================================
N_ARITH = 100
ARITH_REGEX = re.compile(r"^(\d{1,2}) ([+-]) (\d{1,2}) =$")
ARITH_ANSWERS_ALL = [str(v) for v in range(0, 199)]
ARITH_RENDER_NOTE = ("plain text, no chat template: ids = tokenizer(text, add_special_tokens=False).input_ids; read "
                     "position = last token ('='); greedy next token = argmax logits at that position "
                     "(nla-consistency/scripts/thread12_pod.py capture())")


def michael_triples(path: str = MICHAEL_ARITH) -> Tuple[set, str]:
    """(a, op, b) triples of Michael's 600 prompts and the sha256 of the file (excluded from our 100)."""
    with open(path, "rb") as f:
        raw = f.read()
    rows = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
    return {(r["a"], r["op"], r["b"]) for r in rows}, hashlib.sha256(raw).hexdigest()


def arith_triples(rng: random.Random, exclude: set, n: int = N_ARITH, max_tries: int = 1000) -> List[Tuple[int, str, int]]:
    """Michael's sampler (thread12_pod.arith_prompts) with our seed, excluding his triples and any repeat; the whole
    set is re-drawn until every decade of a and of b occurs (deterministic given the seed)."""
    for _ in range(max_tries):
        out: List[Tuple[int, str, int]] = []
        seen = set(exclude)
        for i in range(n):
            op = "-" if i % 2 == 0 else "+"
            while True:
                a = rng.randint(2, 99)
                b = rng.randint(1, a - 1) if op == "-" else rng.randint(1, 99)
                if (a, op, b) not in seen:
                    break
            seen.add((a, op, b))
            out.append((a, op, b))
        if {a // 10 for a, _, _ in out} == set(range(10)) and {b // 10 for _, _, b in out} == set(range(10)):
            return out
    raise RuntimeError("could not cover all operand decades")


def build_arith(rng: random.Random) -> Tuple[List[dict], Dict[str, Any]]:
    exclude, sha = michael_triples()
    items: List[dict] = []
    for i, (a, op, b) in enumerate(arith_triples(rng, exclude), start=1):
        ans = a - b if op == "-" else a + b
        assert ans >= 0
        text = f"{a} {op} {b} ="
        assert ARITH_REGEX.fullmatch(text)
        item_id = f"{PREFIX['arith']}-{i:03d}"
        primary = {"name": "arith_result", "question": f"What is {a} {op} {b}?", "candidates": [str(ans)],
                   "candidates_all": list(ARITH_ANSWERS_ALL), "answer": str(ans), "answer_aliases": [str(ans)]}
        secondary = {"entities": [], "objects": [], "relation": {"type": "arith", "subject": str(a), "object": str(b), "op": op}}
        construction = {"a": a, "b": b, "op": op, "answer": ans, "a_decade": a // 10, "b_decade": b // 10,
                        "a_tens": a // 10, "a_units": a % 10, "b_tens": b // 10, "b_units": b % 10, "singleton": True,
                        "first_mentioned_candidate": str(ans), "answer_position": 0, "cue_position": "n/a", "other_candidate": None}
        it = bd._item(item_id, item_id, "A", "arith", SPLIT, "michael-arith", text, primary, secondary,
                      r"(?<!\d)" + str(ans) + r"(?!\d)", construction,
                      notes="Michael Kenney's arithmetic format (nla-consistency); run WITHOUT the chat template")
        it["render"] = "plain"
        it["render_note"] = ARITH_RENDER_NOTE
        it["operands"] = {"a": a, "b": b, "op": op}
        items.append(it)
    return items, {"michael_arithmetic_sha256": sha, "n_michael_triples_excluded": len(exclude), "render_note": ARITH_RENDER_NOTE}


# ======================================================================================
# mapping-8 index (no new prompts)
# ======================================================================================
SYMBOLS8 = list(bdx.SYMBOLS_X)


def build_mapping8_index(items_x_path: str = ITEMS_X) -> Dict[str, Any]:
    with open(items_x_path, "rb") as f:
        raw = f.read()
    dx = json.loads(raw.decode("utf-8"))
    test = [it for it in dx["items"] if it["family"] == "mapping" and it["split"] == "test"]
    by_pair: Dict[str, Dict[str, dict]] = collections.defaultdict(dict)
    for it in test:
        by_pair[it["pair_id"]][it["version"]] = it
    pairs = []
    rows = []
    for pid in sorted(by_pair):
        p = by_pair[pid]
        assert set(p) == {"A", "B"}, pid
        a, b = p["A"], p["B"]
        assert a["primary"]["candidates"] == b["primary"]["candidates"]
        for it in (a, b):
            assert it["primary"]["answer"] in SYMBOLS8 and set(it["primary"]["candidates"]) <= set(SYMBOLS8)
            rows.append({"item_id": it["item_id"], "pair_id": pid, "version": it["version"], "family": "mapping8",
                         "source_family": "mapping", "answer": it["primary"]["answer"], "candidates": list(it["primary"]["candidates"]),
                         "candidates_all": list(SYMBOLS8), "k": it["construction"]["k"], "start": it["construction"]["start"],
                         "intermediates": list(it["construction"]["intermediates"]),
                         "k_minus_1_symbol": it["construction"]["intermediates"][-1], "template_id": it["template_id"]})
        pairs.append({"pair_id": pid, "item_ids": [a["item_id"], b["item_id"]], "answers": [a["primary"]["answer"], b["primary"]["answer"]],
                      "candidates": list(a["primary"]["candidates"]), "candidates_all": list(SYMBOLS8), "k": a["construction"]["k"]})
    assert len(pairs) == 47 and len(rows) == 94
    meta = {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "phase": "W", "family": "mapping8",
            "source": os.path.relpath(items_x_path, REPO), "source_sha256_file": hashlib.sha256(raw).hexdigest(),
            "source_sha256_items": dx["meta"]["sha256_items"], "n_pairs": len(pairs), "n_items": len(rows),
            "candidates_all": list(SYMBOLS8), "sha256_items": bd.sha256_items(rows),
            "notes": "no new prompts: the 47 X mapping test pairs (prompts and states as captured in X1/X2) scored natively over all 8 symbols; "
                     "k_minus_1_symbol is the 'stops one step early' candidate (V2)"}
    return {"meta": meta, "pairs": pairs, "items": rows}


# ======================================================================================
# V7 target-private pairs
# ======================================================================================
N_V7 = 16
V7_PREAMBLES: List[Dict[str, str]] = [
    {"id": "v7-p0", "level": "p0", "text": "Background: {N1} has the {o1} and {N2} has the {o2}."},
    {"id": "v7-p1", "level": "p1", "text": "Context for this conversation: {N1} has the {o1}. {N2} has the {o2}."},
]
V7_VISIBLE = "Who has the {o}? Answer with the name only."
V7_PREAMBLE_ROLE = "system"
V7_NAMES = list(bdx.NAMES_X)  # 30 names -> 16 distinct pairs, two names used twice (seeded)


def build_v7(rng: random.Random) -> Tuple[List[dict], Dict[str, Any]]:
    names = list(V7_NAMES)
    rng.shuffle(names)
    need = 2 * N_V7 - len(names)  # 32 slots from 30 names: two names reused once, taken from different earlier pairs
    names = names + names[0: 2 * need: 2]
    name_pairs = [tuple(names[2 * i: 2 * i + 2]) for i in range(N_V7)]
    assert len(name_pairs) == N_V7 and all(len(set(p)) == 2 for p in name_pairs) and len(set(name_pairs)) == N_V7
    opairs = BB.match_objects(random.Random(rng.random()))  # 8 disjoint object pairs, distinct colour and noun
    obj_slots = [(op, k) for k in range(2) for op in opairs]  # each object pair twice (asked object alternates)
    rng.shuffle(obj_slots)
    tmpl_levels = bdx.balanced_slots(N_V7, rng)  # True -> p0
    ans_first = bdx.balanced_slots(N_V7, rng)  # True -> version A's answer is first-mentioned in the preamble
    items: List[dict] = []
    for i in range(N_V7):
        pair_id = f"{PREFIX['v7']}-{i + 1:02d}"
        n1, n2 = name_pairs[i]
        (oa, ob), k = obj_slots[i]
        asked, other = (oa, ob) if k == 0 else (ob, oa)
        tmpl = V7_PREAMBLES[0 if tmpl_levels[i] else 1]
        cands = [n1, n2]  # A's answer = n1
        first, second = (n1, n2) if ans_first[i] else (n2, n1)
        visible = V7_VISIBLE.format(o=asked)
        question = f"Who has the {asked}?"
        for version, ans in zip("AB", cands):
            binding = {ans: asked, cands[1 - cands.index(ans)]: other}
            preamble = tmpl["text"].format(N1=first, o1=binding[first], N2=second, o2=binding[second])
            primary = {"name": f"{asked.replace(' ', '_')}_owner", "question": question, "candidates": list(cands), "answer": ans,
                       "answer_aliases": [ans.lower()]}
            secondary = {"entities": list(cands), "objects": [asked, other], "relation": {"type": "has", "subject": ans, "object": asked}}
            construction = {"preamble_template": tmpl["level"], "first_mentioned_in_preamble": first, "binding": binding,
                            "asked_object": asked, "other_object": other, "names": list(cands), "object_pair": [asked, other],
                            "answer_is_first_mentioned": first == ans, "first_mentioned_candidate": first,
                            "answer_position": cands.index(ans), "cue_position": "n/a", "other_candidate": cands[1 - cands.index(ans)],
                            "visible_mentions_candidates": False}
            it = bd._item(f"{pair_id}{version}", pair_id, version, "ownership", SPLIT, tmpl["id"], visible, primary, secondary,
                          bd._word_regex(ans), construction,
                          notes="V7 target-private: the binding is only in the preamble; the visible prompt is identical within the pair")
            it["preamble"] = preamble
            it["preamble_role"] = V7_PREAMBLE_ROLE
            it["capture_messages"] = [{"role": V7_PREAMBLE_ROLE, "content": preamble}, {"role": "user", "content": visible}]
            it["prompt_only_text"] = C.PROMPT_ONLY_TEMPLATE.format(prompt_text=visible, question=question)
            items.append(it)
    return items, {"preambles": V7_PREAMBLES, "visible_template": V7_VISIBLE, "preamble_role": V7_PREAMBLE_ROLE,
                   "object_pairs": [list(o) for o in opairs], "name_pool": list(V7_NAMES)}


def solve_v7(item: dict) -> Optional[str]:
    """The binding re-derived from preamble + visible prompt (the visible prompt alone has no binding)."""
    fake = {**item, "prompt_text": item["preamble"] + " " + item["prompt_text"], "family": "ownership"}
    return bd.solve_prompt(fake)


# ======================================================================================
# validation and build
# ======================================================================================
def validate_w(items: List[dict]) -> Dict[str, Any]:
    """AssertionError on any violation; returns the per-family counts."""
    assert len({it["item_id"] for it in items}) == len(items)
    assert len({it["prompt_text"] for it in items}) == len(items), "prompts must be distinct"
    by_fam: Dict[str, List[dict]] = collections.defaultdict(list)
    for it in items:
        assert bd.REQUIRED_KEYS <= set(it), set(it) ^ bd.REQUIRED_KEYS
        assert it["item_id"] == it["pair_id"] + it["version"] or it["pair_id"] == it["item_id"]
        assert it["split"] == SPLIT and it["system"] is None and it["family"] in FAMILIES
        assert it["item_id"].startswith(PREFIX[it["family"]] + "-")
        pr = it["primary"]
        assert pr["answer"] in pr["candidates"] and len(set(pr["candidates"])) == len(pr["candidates"])
        re.compile(it["target_answer_regex"])
        assert re.search(it["target_answer_regex"], pr["answer"])
        assert len(it["prompt_text"]) < 260, it["item_id"]
        by_fam[it["family"]].append(it)
    counts, own, ar = by_fam["counts"], by_fam["ownership4"], by_fam["arith"]
    # counts
    assert len(counts) == N_COUNTS
    for it in counts:
        c, pr = it["construction"], it["primary"]
        assert it["render"] == "chat" and pr["candidates"] == [str(c["value"])] and pr["candidates_all"] == [str(v) for v in COUNT_VALUES]
        assert solve_count(it) == pr["answer"] == str(c["value"]), it["item_id"]
        assert bd.SHORT_ANSWER_CUE.search(it["prompt_text"]) or "number" in it["prompt_text"]
        assert c["singular"] == (c["value"] == 1)
        if c["value"] == 1:
            assert not re.search(r"\b1 " + c["object"] + r"\b", it["prompt_text"]) and "are 1" not in it["prompt_text"]
        else:
            assert not re.search(r"\d " + c["object_singular"] + r"\b", it["prompt_text"]) and " is " not in it["prompt_text"]
    nv = collections.Counter(it["construction"]["value"] for it in counts)
    assert set(nv) == set(COUNT_VALUES) and set(nv.values()) <= {6, 7} and sum(v == 7 for v in nv.values()) == N_EXTRA
    cells = collections.Counter((it["construction"]["template"], it["construction"]["object"]) for it in counts)
    assert len(cells) == 12 and set(cells.values()) == {PER_CELL}, cells
    assert set(collections.Counter(it["construction"]["place"] for it in counts).values()) == {N_COUNTS // len(COUNT_PLACES)}
    for n in COUNT_VALUES:
        uses = [it["construction"] for it in counts if it["construction"]["value"] == n]
        co = collections.Counter(u["object"] for u in uses)
        ct = collections.Counter(u["template"] for u in uses)
        assert all(co[o] >= 2 for o in COUNT_FACTORS["object"]) and max(co.values()) <= 3, (n, co)
        assert set(ct) == set(COUNT_FACTORS["template"]) and max(ct.values()) <= 3, (n, ct)
        if nv[n] == 6:
            assert set(co.values()) == {2} and sorted(ct.values()) == [1, 1, 2, 2], (n, co, ct)
    # ownership4
    assert len(own) == 2 * N_PAIRS4
    by_pair: Dict[str, List[dict]] = collections.defaultdict(list)
    for it in own:
        c, pr = it["construction"], it["primary"]
        assert it["render"] == "chat" and len(pr["candidates"]) == 4
        assert pr["candidates"].index(pr["answer"]) == ("A", "B").index(it["version"]), it["item_id"]
        assert not re.search(it["target_answer_regex"], " ".join(c["other_candidates"]))
        assert re.search(r"Answer with the (name|object) only\.$", it["prompt_text"])
        assert solve_binding4(it) == pr["answer"], ("solver disagrees", it["item_id"], solve_binding4(it), pr["answer"])
        for f, levels in FACTORS4.items():
            assert c[f] in levels, (it["item_id"], f)
        assert c["holder_b_shift"] in NEAR_BALANCED4["holder_b_shift"]
        assert (c["answer_mention_position"] - c["mention"].index(c["holder_name_A"])) % 4 == (0 if it["version"] == "A" else int(c["holder_b_shift"]))
        assert len(set(c["objects"])) == 4 and len(set(c["binding"].values())) == 4 and set(c["binding"]) == set(c["names"])
        assert c["binding"][c["holder_name"]] == c["asked_object"]
        if c["query_direction"] == "object_to_name":
            assert set(pr["candidates"]) == set(c["names"]) and pr["answer"] == c["holder_name"]
        else:
            assert set(pr["candidates"]) == set(c["objects"]) and c["asked_name"] == c["holder_name_A"]
        assert c["answer_is_first_mentioned"] == (c["first_mentioned_candidate"] == pr["answer"])
        by_pair[it["pair_id"]].append(it)
    assert len(by_pair) == N_PAIRS4
    A4 = []
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert (a["version"], b["version"]) == ("A", "B") and a["template_id"] == b["template_id"]
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["primary"]["answer"] != b["primary"]["answer"]
        assert a["primary"]["question"] == b["primary"]["question"] and a["primary"]["name"] == b["primary"]["name"]
        ca, cb = a["construction"], b["construction"]
        for f in list(FACTORS4) + ["holder_b_shift", "objects", "asked_object", "asked_name", "mention"]:
            assert ca[f] == cb[f], (pid, f)
        assert ca["holder_name"] == ca["holder_name_A"] and cb["holder_name"] == ca["holder_name_B"]
        diff = {n for n in ca["names"] if ca["binding"][n] != cb["binding"][n]}
        assert diff == {ca["holder_name_A"], ca["holder_name_B"]}, pid  # exactly the two holders exchange objects
        assert bdx.word_multiset(a["prompt_text"]) == bdx.word_multiset(b["prompt_text"]), (pid, "not a token permutation")
        assert ca["answer_mention_position"] != cb["answer_mention_position"]
        A4.append(a)
    fac4: Dict[str, Any] = {}
    for f, levels in FACTORS4.items():
        cnt = collections.Counter(it["construction"][f] for it in A4)
        assert set(cnt) == set(levels) and len(set(cnt.values())) == 1, (f, cnt)
        fac4[f] = dict(cnt)
    off = collections.Counter(it["construction"]["holder_b_shift"] for it in A4)
    assert sorted(off.values()) == [21, 21, 22], off
    fac4["holder_b_shift"] = dict(off)
    ps = collections.Counter((it["construction"]["answer_mention_position"], it["construction"]["holder_b_shift"]) for it in A4)
    assert set(ps.values()) <= {5, 6}, ps  # pos_A x shift near-balanced
    fs = list(FACTORS4)
    for i in range(len(fs)):
        for j in range(i + 1, len(fs)):
            c2 = collections.Counter((it["construction"][fs[i]], it["construction"][fs[j]]) for it in A4)
            assert len(c2) == len(FACTORS4[fs[i]]) * len(FACTORS4[fs[j]]) and len(set(c2.values())) == 1, (fs[i], fs[j], c2)
    quad_uses = collections.Counter(it["construction"]["object_quad"] for it in A4)
    assert set(quad_uses.values()) == {16}
    asked_uses = collections.Counter(it["construction"]["asked_object"] for it in A4)
    assert len(asked_uses) == 16 and set(asked_uses.values()) == {4}, asked_uses
    pos = collections.Counter(it["construction"]["answer_mention_position"] for it in A4)
    assert set(pos.values()) == {16}, pos
    # arith
    assert len(ar) == N_ARITH
    exclude, _ = michael_triples()
    seen = set()
    for it in ar:
        c, pr = it["construction"], it["primary"]
        assert it["render"] == "plain" and ARITH_REGEX.fullmatch(it["prompt_text"]) and it["operands"] == {"a": c["a"], "b": c["b"], "op": c["op"]}
        m = ARITH_REGEX.fullmatch(it["prompt_text"])
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        assert (a, op, b) == (c["a"], c["op"], c["b"]) and (a, op, b) not in exclude and (a, op, b) not in seen
        seen.add((a, op, b))
        ans = a - b if op == "-" else a + b
        assert ans >= 0 and pr["answer"] == str(ans) == pr["candidates"][0] and pr["candidates_all"] == ARITH_ANSWERS_ALL
        assert 2 <= a <= 99 and 1 <= b <= 99
    ops = collections.Counter(it["construction"]["op"] for it in ar)
    assert ops == {"-": 50, "+": 50}, ops
    assert {it["construction"]["a_decade"] for it in ar} == set(range(10)) and {it["construction"]["b_decade"] for it in ar} == set(range(10))
    return {"counts": {"n_items": len(counts), "values": {"6_uses": sum(v == 6 for v in nv.values()), "7_uses": sum(v == 7 for v in nv.values())},
                       "cells_template_x_object": {f"{t}|{o}": n for (t, o), n in sorted(cells.items())},
                       "places": dict(sorted(collections.Counter(it["construction"]["place"] for it in counts).items()))},
            "ownership4": {"n_pairs": N_PAIRS4, "n_items": len(own), "factors": fac4, "asked_object_uses": dict(sorted(asked_uses.items())),
                           "answer_mention_position_A": {str(k): v for k, v in sorted(pos.items())}},
            "arith": {"n_items": len(ar), "ops": dict(ops),
                      "a_decades": dict(sorted(collections.Counter(it["construction"]["a_decade"] for it in ar).items())),
                      "b_decades": dict(sorted(collections.Counter(it["construction"]["b_decade"] for it in ar).items()))}}


def validate_v7(items: List[dict]) -> Dict[str, Any]:
    assert len(items) == 2 * N_V7
    by_pair: Dict[str, List[dict]] = collections.defaultdict(list)
    for it in items:
        assert bd.REQUIRED_KEYS <= set(it) and it["family"] == "ownership" and it["render"] == "chat" and it["system"] is None
        assert it["preamble_role"] == V7_PREAMBLE_ROLE and it["capture_messages"][0]["content"] == it["preamble"]
        assert it["capture_messages"][1] == {"role": "user", "content": it["prompt_text"]}
        assert it["prompt_only_text"] == C.PROMPT_ONLY_TEMPLATE.format(prompt_text=it["prompt_text"], question=it["primary"]["question"])
        for n in it["primary"]["candidates"]:
            assert n not in it["prompt_text"] and n in it["preamble"]
        assert it["preamble"] not in it["prompt_only_text"]
        assert solve_v7(it) == it["primary"]["answer"], it["item_id"]
        assert bd.solve_prompt({**it, "family": "ownership"}) is None  # the visible prompt alone carries no binding
        assert it["primary"]["candidates"].index(it["primary"]["answer"]) == ("A", "B").index(it["version"])
        by_pair[it["pair_id"]].append(it)
    assert len(by_pair) == N_V7
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert a["prompt_text"] == b["prompt_text"] and a["prompt_only_text"] == b["prompt_only_text"]
        assert a["preamble"] != b["preamble"] and bdx.word_multiset(a["preamble"]) == bdx.word_multiset(b["preamble"]), pid
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["primary"]["answer"] != b["primary"]["answer"]
        assert a["template_id"] == b["template_id"]
    A = [p[0] if p[0]["version"] == "A" else p[1] for p in by_pair.values()]
    assert len({tuple(it["primary"]["candidates"]) for it in A}) == N_V7 and len({it["prompt_text"] for it in A}) == N_V7
    tm = collections.Counter(it["template_id"] for it in A)
    af = collections.Counter(it["construction"]["answer_is_first_mentioned"] for it in A)
    assert set(tm.values()) == {N_V7 // 2} and set(af.values()) == {N_V7 // 2}, (tm, af)
    return {"n_pairs": N_V7, "n_items": len(items), "templates": dict(tm), "answer_first_mentioned_A": {str(k): v for k, v in af.items()}}


def _meta(seed: int, items: List[dict], **extra: Any) -> Dict[str, Any]:
    return {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "phase": "W", "track": "A", "seed": seed,
            "n_items": len(items), "sha256_items": bd.sha256_items(items), "frozen": False, **extra}


def build(seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    """{'w': items_w.json content, 'v7': items_v7.json content, 'mapping8': mapping8_index.json content}."""
    rng = random.Random(seed)
    counts, cmeta = build_counts(random.Random(rng.random()))
    own, ometa = build_ownership4(random.Random(rng.random()))
    ar, ameta = build_arith(random.Random(rng.random()))
    v7, vmeta = build_v7(random.Random(rng.random()))
    items = counts + own + ar
    report = validate_w(items)
    v7_report = validate_v7(v7)
    m8 = build_mapping8_index()
    fam_counts = {f: sum(it["family"] == f for it in items) for f in FAMILIES}
    w_meta = _meta(seed, items, families=FAMILIES, counts=fam_counts, n_pairs_ownership4=N_PAIRS4, split=SPLIT, id_prefixes=PREFIX,
                   counts_design={"values": [N_MIN, N_MAX], "templates": COUNT_TEMPLATES, "objects": COUNT_OBJECTS, "places": COUNT_PLACES,
                                  "factors": COUNT_FACTORS, "per_cell": PER_CELL, **cmeta},
                   ownership4_design={"factors": FACTORS4, "near_balanced": NEAR_BALANCED4, "name_sets": [list(s) for s in NAME_SETS4],
                                      "templates": TEMPLATES4, "statement": BB.STATEMENT, "questions": QUESTIONS4, **ometa},
                   arith_design={"n": N_ARITH, "format": "{a} {op} {b} =", "sampler": "nla-consistency/scripts/thread12_pod.py arith_prompts "
                                 "(op by index parity; a in 2..99; b in 1..a-1 for '-', 1..99 for '+')", "render": "plain", **ameta},
                   mapping8={"index_file": "mapping8_index.json", "n_pairs": m8["meta"]["n_pairs"], "sha256_items": m8["meta"]["sha256_items"]},
                   balance_checks=report,
                   notes="counts/arith are singletons (pair_id = item_id, version A); ownership4 A/B are token permutations; "
                         "arith must be rendered WITHOUT the chat template (render 'plain'); ids disjoint from items.json / items_x.json / zb-")
    v7_meta = _meta(seed, v7, family="ownership", module="v7", n_pairs=N_V7, split=SPLIT, id_prefix=PREFIX["v7"], design=vmeta,
                    balance_checks=v7_report,
                    notes="target-private pilot: preamble shown to the target only (role = preamble_role) at capture; prompt_text is the "
                          "visible prompt, identical within a pair; prompt_only_text is PROMPT_ONLY_TEMPLATE over the visible prompt only "
                          "(prompt-only baseline = 50% by construction)")
    v7_meta["prompt_only_template_sha256"] = C.sha256_bytes(C.PROMPT_ONLY_TEMPLATE.encode())
    m8["meta"]["seed"] = seed
    return {"w": {"meta": w_meta, "items": items}, "v7": {"meta": v7_meta, "items": v7}, "mapping8": m8}


def load_json(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def summary_table(data: Dict[str, Any]) -> str:
    w, v7, m8 = data["w"], data["v7"], data["mapping8"]
    lines = [f"items_w.json  seed={w['meta']['seed']}  n_items={w['meta']['n_items']}  sha={w['meta']['sha256_items'][:16]}...",
             f"{'family':11} {'items':>5} {'pairs':>5}  extra"]
    rep = w["meta"]["balance_checks"]
    lines.append(f"{'counts':11} {rep['counts']['n_items']:>5} {'-':>5}  values 6x: {rep['counts']['values']['6_uses']}, 7x: {rep['counts']['values']['7_uses']}; "
                 f"12 cells x {PER_CELL}; 12 places x {N_COUNTS // len(COUNT_PLACES)}")
    lines.append(f"{'ownership4':11} {rep['ownership4']['n_items']:>5} {rep['ownership4']['n_pairs']:>5}  factors {rep['ownership4']['factors']}")
    lines.append(f"{'arith':11} {rep['arith']['n_items']:>5} {'-':>5}  ops {rep['arith']['ops']}; a decades {rep['arith']['a_decades']}; b decades {rep['arith']['b_decades']}")
    lines.append(f"{'mapping8':11} {m8['meta']['n_items']:>5} {m8['meta']['n_pairs']:>5}  index only (items_x.json); candidates_all {''.join(SYMBOLS8)}")
    lines.append(f"{'v7':11} {v7['meta']['n_items']:>5} {v7['meta']['n_pairs']:>5}  items_v7.json sha={v7['meta']['sha256_items'][:16]}...")
    lines.append("")
    shown = set()
    for it in w["items"]:
        key = (it["family"], it["template_id"])
        if key in shown:
            continue
        shown.add(key)
        lines.append(f"{it['item_id']:12} ans={it['primary']['answer']:12} {it['prompt_text']}")
    for it in v7["items"][:2]:
        lines.append(f"{it['item_id']:12} ans={it['primary']['answer']:12} [{it['preamble_role']}] {it['preamble']}  ||  {it['prompt_text']}")
    return "\n".join(lines)


def write_all(data: Dict[str, Any], out_dir: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for key, name in (("w", "items_w.json"), ("v7", "items_v7.json"), ("mapping8", "mapping8_index.json")):
        path = os.path.join(out_dir, name)
        if os.path.exists(path):
            old = load_json(path)
            if old.get("meta", {}).get("frozen"):
                raise SystemExit(f"refusing to overwrite frozen file {path}")
            if old["meta"].get("sha256_items") != data[key]["meta"]["sha256_items"]:
                print(f"WARNING: {name} items changed vs existing file (old sha {str(old['meta'].get('sha256_items'))[:12]}...)")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data[key], f, ensure_ascii=False, indent=1)
        out.append(path)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    data = build(a.seed)
    if not a.no_write:
        for p in write_all(data, a.out_dir):
            print(f"wrote {p}")
    if a.print or a.no_write:
        print(summary_table(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
