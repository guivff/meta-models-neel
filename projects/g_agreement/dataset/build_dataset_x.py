#!/usr/bin/env python
"""Phase X item bank (BRIEF_X.md §Dataset): 48 ownership + 48 mapping + 24 language + 24 tense pairs,
two versions each, written to ``dataset/items_x.json`` in the items.json schema (INTERFACES §1).

Deterministic from --seed (default 20261008). Reuses the material, generators, mini-solver and item
constructor of ``build_dataset.py`` (imported, never modified) and extends the pools:
  ownership  30 short first names x 16 coloured objects x the 5 own-t templates; 48 distinct
             (name pair, object pair, template) combos; A/B are token permutations (binding swapped)
  mapping    symbols A-H; 24 two-step + 24 three-step arrow puzzles (odd pair index = 2 steps, even = 3,
             so every prefix of the pair list is balanced); A/B are token permutations
  language   24 distinct (language pair, question) combos over the 8 languages and a 12-question bank
             with per-language expected-word regexes (the two expected words never cross-match)
  tense      24 distinct (template, subject, place) combos of the reworded tense templates
Pair 01 of each family is ``dev``; the rest ``test``. Ids ``xown-01A`` ... (pair ``xown-01``); the
``x`` prefix keeps them disjoint from the G cache. Answer keys are re-derived by ``build_dataset.solve_prompt``
(ownership, 2-step mapping, language, tense) and by ``solve_k_steps`` (all mapping); the build fails on
any disagreement. No prompt text of items.json is reused.

Usage:
    .venv/bin/python projects/g_agreement/dataset/build_dataset_x.py [--seed 20261008] [--out items_x.json]
    .venv/bin/python projects/g_agreement/dataset/build_dataset_x.py --print
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
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402

DEFAULT_OUT = os.path.join(HERE, "items_x.json")
DEFAULT_SEED = 20261008
FAMILIES = ["ownership", "mapping", "language", "tense"]
PREFIX = {"ownership": "xown", "mapping": "xmap", "language": "xlang", "tense": "xtense"}
N_PAIRS = {"ownership": 48, "mapping": 48, "language": 24, "tense": 24}
DEV_PAIR_INDEX = 1

# --------------------------------------------------------------------------------------
# Ownership pools (short Latin first names that are not common words; coloured objects)
# --------------------------------------------------------------------------------------
NAMES_X: List[str] = [
    "Mira", "Leo", "Tom", "Ana", "Omar", "Lena", "Nina", "Sara", "Ivan", "Zara",
    "Hugo", "Emma", "Noah", "Lily", "Adam", "Rosa", "Finn", "Eva", "Luca", "Nora",
    "Paul", "Iris", "Maya", "Erik", "Tara", "Ben", "Alma", "Kai", "Vera", "Theo",
]
OBJECTS_X: List[str] = [
    "red key", "blue cup", "green hat", "black bag", "white pen", "yellow box", "grey ball", "pink scarf",
    "brown coat", "silver ring", "gold coin", "purple book", "orange lamp", "green bottle", "blue rope", "red flag",
]

# --------------------------------------------------------------------------------------
# Mapping: the 5 G templates parametrised by the number of steps (k=2 renders == build_dataset text)
# --------------------------------------------------------------------------------------
SYMBOLS_X = list("ABCDEFGH")
STEP_WORDS = {2: {"times": "twice", "times_n": "two times", "n": "two"},
              3: {"times": "three times", "times_n": "three times", "n": "three"},
              4: {"times": "four times", "times_n": "four times", "n": "four"}}
MAPPING_TEMPLATES_X: List[Dict[str, str]] = [
    {"id": "map-t1", "arrow": "→",
     "text": "{rules} Start at {start} and follow the arrows {times}. Where do you end up? Answer with the symbol only."},
    {"id": "map-t2", "arrow": "maps to",
     "text": "{rules} Begin at {start} and apply the mapping {times_n}. Which one do you reach? Reply with one word."},
    {"id": "map-t3", "arrow": "->",
     "text": "{rules} Starting from {start}, apply the rule {times}. What do you get? One word only."},
    {"id": "map-t4", "arrow": "leads to",
     "text": "{rules} From {start}, take {n} steps. Which one do you land on? Give the answer only."},
    {"id": "map-t5", "arrow": "→",
     "text": "{rules} Start at {start} and apply the mapping {times}. What do you reach? Answer with one word."},
]
STEP_NAME = {2: "two_step_result", 3: "three_step_result", 4: "four_step_result"}


def mapping_text(tmpl: Dict[str, str], k: int) -> str:
    """The template text with the step words of k filled in ({rules}/{start} left open)."""
    w = STEP_WORDS[k]
    return tmpl["text"].replace("{times_n}", w["times_n"]).replace("{times}", w["times"]).replace("{n}", w["n"])


for _t, _g in zip(MAPPING_TEMPLATES_X, bd.MAPPING_TEMPLATES):
    assert _t["id"] == _g["id"] and _t["arrow"] == _g["arrow"] and mapping_text(_t, 2) == _g["text"], _t["id"]

# --------------------------------------------------------------------------------------
# Language: question bank with the expected one-word answer per language (regex alternations)
# --------------------------------------------------------------------------------------
LANGUAGES_X = list(bd.LANGUAGE_ALIASES)  # French German Spanish Italian Portuguese Dutch Swedish Turkish
QUESTION_BANK_X: List[Dict[str, Any]] = [
    {"question": "What colour is the sky on a clear day?",
     "expected": {"French": r"bleu|bleue", "German": r"blau", "Spanish": r"azul", "Italian": r"azzurro|blu",
                  "Portuguese": r"azul", "Dutch": r"blauw", "Swedish": r"blå|blått", "Turkish": r"mavi"}},
    {"question": "What is the opposite of 'hot'?",
     "expected": {"French": r"froid|froide", "German": r"kalt", "Spanish": r"fr[ií]o|fr[ií]a", "Italian": r"freddo|fredda",
                  "Portuguese": r"frio|fria", "Dutch": r"koud", "Swedish": r"kall|kallt", "Turkish": r"soğuk|soguk"}},
    {"question": "What colour is a ripe banana?",
     "expected": {"French": r"jaune", "German": r"gelb", "Spanish": r"amarillo|amarilla", "Italian": r"giallo|gialla",
                  "Portuguese": r"amarelo|amarela", "Dutch": r"geel|gele", "Swedish": r"gul|gult|gula", "Turkish": r"sarı|sari"}},
    {"question": "What colour is fresh snow?",
     "expected": {"French": r"blanc|blanche", "German": r"weiß|weiss", "Spanish": r"blanco|blanca", "Italian": r"bianco|bianca",
                  "Portuguese": r"branco|branca", "Dutch": r"wit|witte", "Swedish": r"vit|vitt|vita", "Turkish": r"beyaz"}},
    {"question": "Which animal says 'meow'?",
     "expected": {"French": r"chat|chatte", "German": r"katze", "Spanish": r"gato|gata", "Italian": r"gatto|gatta",
                  "Portuguese": r"gato|gata", "Dutch": r"kat|poes", "Swedish": r"katt", "Turkish": r"kedi"}},
    {"question": "Which animal barks?",
     "expected": {"French": r"chien", "German": r"hund", "Spanish": r"perro", "Italian": r"cane",
                  "Portuguese": r"cão|cao|cachorro", "Dutch": r"hond", "Swedish": r"hund", "Turkish": r"köpek|kopek"}},
    {"question": "What is the opposite of 'big'?",
     "expected": {"French": r"petit|petite", "German": r"klein", "Spanish": r"pequeño|pequeno|pequeña|chico", "Italian": r"piccolo|piccola",
                  "Portuguese": r"pequeno|pequena", "Dutch": r"klein", "Swedish": r"liten|litet|små|sma", "Turkish": r"küçük|kucuk"}},
    {"question": "What do you call frozen water?",
     "expected": {"French": r"glace", "German": r"eis", "Spanish": r"hielo", "Italian": r"ghiaccio",
                  "Portuguese": r"gelo", "Dutch": r"ijs", "Swedish": r"is", "Turkish": r"buz"}},
    {"question": "What colour is grass?",
     "expected": {"French": r"vert|verte", "German": r"grün|gruen", "Spanish": r"verde", "Italian": r"verde",
                  "Portuguese": r"verde", "Dutch": r"groen", "Swedish": r"grön|grönt", "Turkish": r"yeşil|yesil"}},
    {"question": "Which number comes after two?",
     "expected": {"French": r"trois", "German": r"drei", "Spanish": r"tres", "Italian": r"tre",
                  "Portuguese": r"três|tres", "Dutch": r"drie", "Swedish": r"tre", "Turkish": r"üç|uc"}},
    {"question": "What is the opposite of 'day'?",
     "expected": {"French": r"nuit", "German": r"nacht", "Spanish": r"noche", "Italian": r"notte",
                  "Portuguese": r"noite", "Dutch": r"nacht", "Swedish": r"natt", "Turkish": r"gece"}},
    {"question": "Which star do we see during the day?",
     "expected": {"French": r"soleil", "German": r"sonne", "Spanish": r"sol", "Italian": r"sole",
                  "Portuguese": r"sol", "Dutch": r"zon", "Swedish": r"sol|solen", "Turkish": r"güneş|gunes"}},
]
MAX_QUESTION_USES = 3


def _alts(rx: str) -> List[str]:
    return [a for a in rx.split("|") if a]


def expected_words_cross_match(rx_a: str, rx_b: str) -> bool:
    """True if any alternative of one language's expected regex matches the other's (the pair is unusable)."""
    ra, rb = re.compile(r"(?i)^(" + rx_a + r")$"), re.compile(r"(?i)^(" + rx_b + r")$")
    return any(rb.match(w) for w in _alts(rx_a)) or any(ra.match(w) for w in _alts(rx_b))


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def word_multiset(text: str) -> collections.Counter:
    """Words and punctuation marks as separate tokens (BPE splits punctuation off a word), so the
    permutation invariant is checked on the same units a tokenizer uses."""
    return collections.Counter(re.findall(r"[\w']+|[^\w\s]", text))


def balanced_slots(n: int, rng: random.Random, block: int = 8) -> List[bool]:
    """n booleans, half True; shuffled inside blocks of ``block`` so every block-prefix is balanced
    (X2 takes the first 32 test pairs)."""
    out: List[bool] = []
    while len(out) < n:
        b = [True, False] * (block // 2)
        rng.shuffle(b)
        out += b
    return out[:n]


def template_cycle(templates: List[Any], n_test: int, rng: random.Random) -> List[Any]:
    """Test pairs cycle through a seeded permutation of the given templates (ownership/mapping: all 5,
    so the canonical t1 wording is in the X2 pairs; language/tense: t2-t5, t1 stays dev-only).
    Whether the dev template is reused in test is recorded in meta."""
    order = list(templates)
    rng.shuffle(order)
    return [order[i % len(order)] for i in range(n_test)]


def g_prompt_texts() -> set:
    """Prompt texts of the G dataset (rebuilt deterministically) — never reused in X."""
    return {it["prompt_text"] for it in bd.build(bd.DEFAULT_SEED)["items"]}


def solve_k_steps(item: dict) -> Optional[str]:
    """Independent k-step solver for mapping prompts (k from construction)."""
    p, c = item["prompt_text"], item["construction"]
    rules = dict(re.findall(r"(\S+) " + re.escape(c["arrow"]) + r" (\S+)\.", p))
    cur = c["start"]
    try:
        for _ in range(int(c["k"])):
            cur = rules[cur]
    except KeyError:
        return None
    return cur


# --------------------------------------------------------------------------------------
# Family builders
# --------------------------------------------------------------------------------------
def build_ownership_x(rng: random.Random, n_pairs: int, forbidden: set) -> List[dict]:
    name_pairs = list(itertools.combinations(NAMES_X, 2))
    obj_pairs = list(itertools.permutations(OBJECTS_X, 2))  # (asked, other)
    rng.shuffle(name_pairs)
    rng.shuffle(obj_pairs)
    tmpls = [bd.OWNERSHIP_TEMPLATES[0]] + template_cycle(bd.OWNERSHIP_TEMPLATES, n_pairs - 1, rng)
    c0_first = [True] + balanced_slots(n_pairs - 1, rng)
    items: List[dict] = []
    used = set()
    for k in range(1, n_pairs + 1):
        pair_id = f"{PREFIX['ownership']}-{k:02d}"
        split = "dev" if k == DEV_PAIR_INDEX else "test"
        tmpl = tmpls[k - 1]
        names, objs = name_pairs[k - 1], obj_pairs[k - 1]
        combo = (names, objs, tmpl["id"])
        assert combo not in used
        used.add(combo)
        cands = list(names)
        if rng.random() < 0.5:
            cands.reverse()
        ask, other_obj = objs
        n1, n2 = (cands[0], cands[1]) if c0_first[k - 1] else (cands[1], cands[0])
        for version, ans in zip("AB", cands):
            o_for = {ans: ask, cands[1 - cands.index(ans)]: other_obj}
            prompt = tmpl["text"].format(N1=n1, N2=n2, o1=o_for[n1], o2=o_for[n2], ask=ask)
            assert prompt not in forbidden, prompt
            primary = {"name": f"{ask.replace(' ', '_')}_owner", "question": f"Who {tmpl['cue']} the {ask}?",
                       "candidates": cands, "answer": ans, "answer_aliases": [ans.lower()]}
            secondary = {"entities": cands, "objects": [ask, other_obj],
                         "relation": {"type": tmpl["cue"], "subject": ans, "object": ask}}
            construction = {"first_mentioned_candidate": n1, "answer_position": cands.index(ans), "cue_position": "n/a",
                            "other_candidate": cands[1 - cands.index(ans)], "answer_is_first_mentioned": n1 == ans}
            items.append(bd._item(f"{pair_id}{version}", pair_id, version, "ownership", split, tmpl["id"],
                                  prompt, primary, secondary, bd._word_regex(ans), construction,
                                  notes="A/B are token permutations: the two objects swap owners"))
    return items


def build_mapping_x(rng: random.Random, n_pairs: int, forbidden: set) -> List[dict]:
    tmpls = [MAPPING_TEMPLATES_X[0]] + template_cycle(MAPPING_TEMPLATES_X, n_pairs - 1, rng)
    distractor_last = [True] + balanced_slots(n_pairs - 1, rng)
    items: List[dict] = []
    seen_prompts = set()
    for k in range(1, n_pairs + 1):
        pair_id = f"{PREFIX['mapping']}-{k:02d}"
        split = "dev" if k == DEV_PAIR_INDEX else "test"
        steps = 2 if k % 2 == 1 else 3
        tmpl, arrow = tmpls[k - 1], tmpls[k - 1]["arrow"]
        syms = rng.sample(SYMBOLS_X, steps + 2)  # start, mids..., c0, c1
        start, mids, cands = syms[0], syms[1:steps], syms[steps:]
        if rng.random() < 0.5:
            cands.reverse()
        text = mapping_text(tmpl, steps)
        for version, ans in zip("AB", cands):
            other = cands[1 - cands.index(ans)]
            chain = [start] + mids + [ans]
            hops = [f"{a} {arrow} {b}." for a, b in zip(chain, chain[1:])]
            distractor = f"{other} {arrow} {start}."
            rules = hops + [distractor] if distractor_last[k - 1] else [distractor] + hops
            prompt = text.format(rules=" ".join(rules), start=start)
            assert prompt not in forbidden and prompt not in seen_prompts, prompt
            seen_prompts.add(prompt)
            primary = {"name": STEP_NAME[steps],
                       "question": f"Starting from {start}, what does applying the mapping {STEP_WORDS[steps]['times']} reach?",
                       "candidates": cands, "answer": ans, "answer_aliases": [ans.lower()]}
            secondary = {"entities": chain[:-1] + cands, "objects": [],
                         "relation": {"type": "maps_to", "subject": chain[-2], "object": ans}}
            construction = {"first_mentioned_candidate": ans if distractor_last[k - 1] else other,
                            "answer_position": cands.index(ans), "cue_position": "n/a", "other_candidate": other,
                            "start": start, "intermediate": mids[0], "intermediates": mids, "k": steps, "arrow": arrow,
                            "answer_is_first_mentioned": distractor_last[k - 1]}
            items.append(bd._item(f"{pair_id}{version}", pair_id, version, "mapping", split, tmpl["id"],
                                  prompt, primary, secondary, bd._word_regex(ans), construction,
                                  notes=f"{steps}-step; A/B are token permutations: the two candidates swap roles in the last hop and the distractor"))
    return items


def select_language_combos(rng: random.Random, n_pairs: int, tmpls: List[Tuple[str, str]], forbidden: set
                           ) -> List[Tuple[Tuple[str, str], int]]:
    """n distinct (language pair, question index) combos: every language pair at most once, every
    question at most MAX_QUESTION_USES times, expected words never cross-matching, and no render
    (with the template of that pair position) equal to a G prompt."""
    lang_pairs = list(itertools.combinations(LANGUAGES_X, 2))
    rng.shuffle(lang_pairs)
    q_order = list(range(len(QUESTION_BANK_X)))
    rng.shuffle(q_order)
    uses = collections.Counter()
    out: List[Tuple[Tuple[str, str], int]] = []
    for lp in lang_pairs:
        tmpl = tmpls[len(out)][1]
        for qi in sorted(q_order, key=lambda q: (uses[q], q_order.index(q))):
            ex, q = QUESTION_BANK_X[qi]["expected"], QUESTION_BANK_X[qi]["question"]
            renders = {tmpl.format(lang=l, q=q) for l in lp}
            if uses[qi] < MAX_QUESTION_USES and not expected_words_cross_match(ex[lp[0]], ex[lp[1]]) and not (renders & forbidden):
                out.append((lp, qi))
                uses[qi] += 1
                break
        if len(out) == n_pairs:
            break
    assert len(out) == n_pairs, f"only {len(out)} valid language combos"
    return out


def build_language_x(rng: random.Random, n_pairs: int, forbidden: set) -> List[dict]:
    tmpls = [bd.LANGUAGE_TEMPLATES[0]] + template_cycle(bd.LANGUAGE_TEMPLATES[1:], n_pairs - 1, rng)  # t1 dev-only
    combos = select_language_combos(rng, n_pairs, tmpls, forbidden)
    items: List[dict] = []
    for k, (lp, qi) in enumerate(combos, start=1):
        pair_id = f"{PREFIX['language']}-{k:02d}"
        split = "dev" if k == DEV_PAIR_INDEX else "test"
        q = QUESTION_BANK_X[qi]
        langs = list(lp)
        if rng.random() < 0.5:
            langs.reverse()
        tid, tmpl = tmpls[k - 1]
        cue_position = "before" if tmpl.index("{lang}") < tmpl.index("{q}") else "after"
        for version, ans in zip("AB", langs):
            other = langs[1 - langs.index(ans)]
            prompt = tmpl.format(lang=ans, q=q["question"])
            assert prompt not in forbidden, prompt
            primary = {"name": "response_language", "question": "In which language is the reply requested?",
                       "candidates": langs, "answer": ans, "answer_aliases": bd.LANGUAGE_ALIASES[ans]}
            secondary = {"entities": [], "objects": [], "relation": None}
            regex = r"(?i)\b(" + q["expected"][ans] + r")\b"
            construction = {"first_mentioned_candidate": ans, "answer_position": langs.index(ans), "cue_position": cue_position,
                            "other_candidate": other, "expected_word": q["expected"][ans],
                            "expected_word_other": q["expected"][other], "question_index": qi}
            items.append(bd._item(f"{pair_id}{version}", pair_id, version, "language", split, tid, prompt, primary,
                                  secondary, regex, construction,
                                  notes="only the requested language is named in the prompt; the other candidate is never mentioned"))
    return items


def build_tense_x(rng: random.Random, n_pairs: int, forbidden: set) -> List[dict]:
    combos = [(t, s, p) for t in bd.TENSE_TEMPLATES for s in bd.TENSE_SUBJECTS for p in bd.TENSE_PLACES]
    combos = [c for c in combos if c[0][1].format(subj=c[1], place=c[2]) not in forbidden
              and c[0][2].format(subj=c[1], place=c[2]) not in forbidden]
    dev = next(c for c in combos if c[0][0] == "tense-t1")
    rest = [c for c in combos if c[0][0] != "tense-t1"]  # t1 dev-only
    rng.shuffle(rest)
    chosen = [dev] + rest[: n_pairs - 1]
    items: List[dict] = []
    for k, (tt, subj, place) in enumerate(chosen, start=1):
        pair_id = f"{PREFIX['tense']}-{k:02d}"
        split = "dev" if k == DEV_PAIR_INDEX else "test"
        tid, past_t, fut_t = tt
        cands = ["past", "future"]
        for version, ans in zip("AB", cands):
            prompt = (past_t if ans == "past" else fut_t).format(subj=subj, place=place)
            primary = {"name": "response_tense", "question": "Is the requested sentence about the past or the future?",
                       "candidates": cands, "answer": ans, "answer_aliases": []}
            secondary = {"entities": [], "objects": [], "relation": None}
            regex = (r"(?i)\b(yesterday|was|were|did|went|had|\w{3,}ed)\b" if ans == "past"
                     else r"(?i)(\b(will|shall|tomorrow|going to)\b|'ll\b)")
            construction = {"first_mentioned_candidate": ans, "answer_position": cands.index(ans), "cue_position": "n/a",
                            "other_candidate": cands[1 - cands.index(ans)], "subject": subj, "place": place}
            items.append(bd._item(f"{pair_id}{version}", pair_id, version, "tense", split, tid, prompt, primary, secondary,
                                  regex, construction, notes="target scored by scoring.detect_tense, not by target_answer_regex alone"))
    return items


# --------------------------------------------------------------------------------------
# Validation (BRIEF_X invariants) and build
# --------------------------------------------------------------------------------------
def validate_x(items: List[dict], g_items: List[dict]) -> Dict[str, Any]:
    g_ids = {it["item_id"] for it in g_items}
    g_prompts = {it["prompt_text"] for it in g_items}
    by_pair: Dict[str, List[dict]] = {}
    for it in items:
        assert bd.REQUIRED_KEYS <= set(it)
        assert it["item_id"].startswith("x") and it["item_id"] == it["pair_id"] + it["version"]
        assert it["item_id"] not in g_ids and it["prompt_text"] not in g_prompts, it["item_id"]
        assert it["pair_id"].split("-")[0] == PREFIX[it["family"]]
        pr = it["primary"]
        assert len(pr["candidates"]) == 2 and len(set(pr["candidates"])) == 2 and pr["answer"] in pr["candidates"]
        assert pr["candidates"].index(pr["answer"]) == ("A", "B").index(it["version"]), it["item_id"]
        re.compile(it["target_answer_regex"])
        assert bd.SHORT_ANSWER_CUE.search(it["prompt_text"]), it["item_id"]
        assert len(it["prompt_text"]) < 260, it["item_id"]
        if it["family"] == "mapping":
            assert solve_k_steps(it) == pr["answer"], ("k-step solver disagrees", it["item_id"])
            if it["construction"]["k"] == 2:
                assert bd.solve_prompt(it) == pr["answer"], ("solver disagrees", it["item_id"])
        else:
            assert bd.solve_prompt(it) == pr["answer"], ("solver disagrees", it["item_id"], bd.solve_prompt(it))
        if it["family"] in ("ownership", "mapping"):
            assert re.search(it["target_answer_regex"], pr["answer"])
            assert not re.search(it["target_answer_regex"], it["construction"]["other_candidate"])
        by_pair.setdefault(it["pair_id"], []).append(it)
    assert len(by_pair) == sum(N_PAIRS.values())
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert (a["version"], b["version"]) == ("A", "B")
        for key in ("family", "split", "template_id"):
            assert a[key] == b[key], (pid, key)
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["primary"]["answer"] != b["primary"]["answer"]
        assert a["prompt_text"] != b["prompt_text"]
        if a["family"] in ("ownership", "mapping"):
            assert word_multiset(a["prompt_text"]) == word_multiset(b["prompt_text"]), (pid, "not a token permutation")
        assert abs(len(a["prompt_text"].split()) - len(b["prompt_text"].split())) <= 1, pid
    report: Dict[str, Any] = {}
    for fam in FAMILIES:
        fi = [x for x in items if x["family"] == fam]
        dev = [x for x in fi if x["split"] == "dev"]
        test = [x for x in fi if x["split"] == "test"]
        assert len(fi) == 2 * N_PAIRS[fam] and len(dev) == 2, fam
        assert {x["pair_id"] for x in dev} == {f"{PREFIX[fam]}-01"}
        entry: Dict[str, Any] = {"n_pairs": N_PAIRS[fam], "n_dev": len(dev), "n_test": len(test),
                                 "templates_test": dict(collections.Counter(x["template_id"] for x in test if x["version"] == "A")),
                                 "templates_dev": sorted({x["template_id"] for x in dev}),
                                 "dev_template_reused_in_test": bool({x["template_id"] for x in dev} & {x["template_id"] for x in test})}
        if fam in ("ownership", "mapping"):
            fa = [x["construction"]["answer_is_first_mentioned"] for x in test if x["version"] == "A"]
            entry["test_A_answer_is_first_mentioned"] = {"true": sum(fa), "false": len(fa) - sum(fa)}
            assert abs(sum(fa) - (len(fa) - sum(fa))) <= 1, (fam, entry)
            assert len({x["prompt_text"] for x in fi}) == len(fi)
        if fam == "mapping":
            ks = collections.Counter(x["construction"]["k"] for x in fi if x["version"] == "A")
            assert ks == {2: 24, 3: 24}, ks
            entry["k_counts_pairs"] = dict(ks)
            entry["k_counts_test_pairs"] = dict(collections.Counter(x["construction"]["k"] for x in test if x["version"] == "A"))
        if fam == "language":
            cp = collections.Counter(x["construction"]["cue_position"] for x in test if x["version"] == "A")
            entry["test_cue_position"] = dict(cp)
            entry["question_uses"] = dict(collections.Counter(x["construction"]["question_index"] for x in fi if x["version"] == "A"))
            assert max(entry["question_uses"].values()) <= MAX_QUESTION_USES
            assert len({tuple(sorted(x["primary"]["candidates"])) for x in fi}) == N_PAIRS[fam]  # distinct language pairs
            for x in fi:
                assert x["construction"]["other_candidate"] not in x["prompt_text"]
                assert x["target_answer_regex"] == r"(?i)\b(" + x["construction"]["expected_word"] + r")\b"
                assert not expected_words_cross_match(x["construction"]["expected_word"], x["construction"]["expected_word_other"])
        if fam == "tense":
            combos = {(x["template_id"], x["construction"]["subject"], x["construction"]["place"]) for x in fi}
            assert len(combos) == N_PAIRS[fam]
        report[fam] = entry
    return report


def build(seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    rng = random.Random(seed)
    g_items = bd.build(bd.DEFAULT_SEED)["items"]
    forbidden = {it["prompt_text"] for it in g_items}
    items: List[dict] = []
    items += build_ownership_x(random.Random(rng.random()), N_PAIRS["ownership"], forbidden)
    items += build_mapping_x(random.Random(rng.random()), N_PAIRS["mapping"], forbidden)
    items += build_language_x(random.Random(rng.random()), N_PAIRS["language"], forbidden)
    items += build_tense_x(random.Random(rng.random()), N_PAIRS["tense"], forbidden)
    report = validate_x(items, g_items)
    counts = {fam: {"pairs": N_PAIRS[fam], "items": 2 * N_PAIRS[fam], "dev_items": 2, "test_items": 2 * N_PAIRS[fam] - 2} for fam in FAMILIES}
    meta = {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "phase": "X", "seed": seed,
            "n_pairs": len(items) // 2, "n_items": len(items), "families": FAMILIES, "dev_pair_index": DEV_PAIR_INDEX,
            "counts": counts, "id_prefixes": PREFIX, "sha256_items": bd.sha256_items(items), "frozen": False,
            "g_dataset_seed": bd.DEFAULT_SEED, "balance_checks": report,
            "notes": "A/B of ownership and mapping are token permutations (word multiset equal); answer keys re-derived by "
                     "build_dataset.solve_prompt / solve_k_steps; no item id or prompt text is shared with items.json"}
    return {"meta": meta, "items": items}


def load_items(path: str = DEFAULT_OUT) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def summary_table(data: Dict[str, Any]) -> str:
    """Per-family summary (counts, templates, k mix) plus one example pair per family."""
    lines = [f"items_x.json  seed={data['meta']['seed']}  n_items={data['meta']['n_items']}  sha={data['meta']['sha256_items'][:16]}...",
             f"{'family':10} {'pairs':>5} {'dev':>4} {'test':>5}  templates(test A)                       extra"]
    rep = data["meta"]["balance_checks"]
    for fam in FAMILIES:
        e = rep[fam]
        extra = e.get("k_counts_pairs") or e.get("test_cue_position") or e.get("test_A_answer_is_first_mentioned") or ""
        lines.append(f"{fam:10} {e['n_pairs']:>5} {e['n_dev']:>4} {e['n_test']:>5}  {str(e['templates_test']):40} {extra}")
    lines.append("")
    for fam in FAMILIES:
        for it in [x for x in data["items"] if x["family"] == fam][:2]:
            lines.append(f"{it['item_id']:11} {it['split']:4} ans={it['primary']['answer']:10} {it['prompt_text']}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
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
                raise SystemExit(f"refusing to overwrite frozen dataset {args.out}")
            if old["meta"]["sha256_items"] != data["meta"]["sha256_items"]:
                print(f"WARNING: items changed vs existing file (old sha {old['meta']['sha256_items'][:12]}...)")
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"wrote {args.out} ({len(data['items'])} items, sha {data['meta']['sha256_items'][:16]}...)")
    if args.print or args.no_write:
        print(summary_table(data))


if __name__ == "__main__":
    main()
