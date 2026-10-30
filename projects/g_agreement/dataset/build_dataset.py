#!/usr/bin/env python
"""Build the G-experiment dataset: 20 paired tasks (4 families x 5 pairs), INTERFACES.md §1.

Deterministic from --seed. The seed decides only *arrangement* choices (which hand-written
material goes to which pair, candidate order, counterbalancing slots); the material itself
(names, objects, symbol sets, questions, templates) is fixed below so that it can be reviewed.

Answer keys are written FROM THE CONSTRUCTION (the generator knows which candidate it placed
in the answer slot) and are then re-derived by an independent mini-solver that parses the
prompt text (`solve_prompt`). The build fails if the two disagree.

Usage:
    .venv/bin/python projects/g_agreement/dataset/build_dataset.py [--seed 20261007] [--out items.json]
    .venv/bin/python projects/g_agreement/dataset/build_dataset.py --print   # summary table only
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import random
import re
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "items.json")
DEFAULT_SEED = 20261007
FAMILIES = ["language", "tense", "ownership", "mapping"]
PREFIX = {"language": "lang", "tense": "tense", "ownership": "own", "mapping": "map"}
N_PAIRS_PER_FAMILY = 5
DEV_PAIR_INDEX = 1  # pair 01 of every family is the dev pair (fixed by design, not by seed)

# --------------------------------------------------------------------------------------
# Language family material
# --------------------------------------------------------------------------------------
# English name -> (own name(s) used as answer aliases)
LANGUAGE_ALIASES: Dict[str, List[str]] = {
    "French": ["french", "français", "francais"],
    "German": ["german", "deutsch"],
    "Spanish": ["spanish", "español", "espanol", "castellano"],
    "Italian": ["italian", "italiano"],
    "Portuguese": ["portuguese", "português", "portugues"],
    "Dutch": ["dutch", "nederlands"],
    "Swedish": ["swedish", "svenska"],
    "Turkish": ["turkish", "türkçe", "turkce"],
}

# One trivial question per pair, with the expected one-word answer in each of the two
# candidate languages (regex alternation, matched case-insensitively on the target output).
# Language pairs were chosen so that the two expected words differ.
LANGUAGE_PAIRS: List[Dict[str, Any]] = [
    # pair 01 (dev)
    {"langs": ("French", "German"), "question": "What colour is the sky on a clear day?",
     "expected": {"French": r"bleu|bleue", "German": r"blau"}},
    {"langs": ("Spanish", "Italian"), "question": "What is the opposite of 'hot'?",
     "expected": {"Spanish": r"fr[ií]o|fr[ií]a", "Italian": r"freddo|fredda"}},
    {"langs": ("Dutch", "Swedish"), "question": "What colour is a ripe banana?",
     "expected": {"Dutch": r"geel|gele", "Swedish": r"gul|gult|gula"}},
    {"langs": ("Portuguese", "French"), "question": "What colour is fresh snow?",
     "expected": {"Portuguese": r"branco|branca", "French": r"blanc|blanche"}},
    {"langs": ("German", "Turkish"), "question": "Which animal says 'meow'?",
     "expected": {"German": r"katze", "Turkish": r"kedi"}},
]
# Templates: {cue} is the language-request sentence, {q} the question. Dev uses lang-t1 only.
LANGUAGE_TEMPLATES: List[Tuple[str, str]] = [
    ("lang-t1", "Reply in {lang}, in one word: {q}"),                      # dev
    ("lang-t2", "Answer in {lang}. Use one word. {q}"),                    # cue before
    ("lang-t3", "{q} Please respond in {lang}, one word only."),           # cue after
    ("lang-t4", "Give your answer in {lang}, as a single word. {q}"),      # cue before
    ("lang-t5", "{q} (Answer in {lang}, one word.)"),                      # cue after
]

# --------------------------------------------------------------------------------------
# Tense family material
# --------------------------------------------------------------------------------------
# {past} / {future} slots differ only by the tense cue.
TENSE_TEMPLATES: List[Tuple[str, str, str]] = [
    # (template_id, past prompt, future prompt). Reworded 2026-10-07 after the dev run: the target
    # model refused the original "describe what X did yesterday" wording ("no context provided"),
    # so every template now asks for an INVENTED sentence. Past/future differ only in the tense cue.
    ("tense-t1",
     "Invent one short sentence describing what {subj} did at the {place} yesterday.",
     "Invent one short sentence describing what {subj} will do at the {place} tomorrow."),
    ("tense-t2",
     "Make up one sentence (under ten words) about what {subj} did in the {place} yesterday.",
     "Make up one sentence (under ten words) about what {subj} will do in the {place} tomorrow."),
    ("tense-t3",
     "Imagine {subj} at the {place}. In a single short sentence, say what they did there yesterday.",
     "Imagine {subj} at the {place}. In a single short sentence, say what they will do there tomorrow."),
    ("tense-t4",
     "Write one short sentence, fictional, about what {subj} did near the {place} yesterday.",
     "Write one short sentence, fictional, about what {subj} will do near the {place} tomorrow."),
    ("tense-t5",
     "Creative writing, one short sentence only: what did {subj} do at the {place} yesterday?",
     "Creative writing, one short sentence only: what will {subj} do at the {place} tomorrow?"),
]
TENSE_SUBJECTS = ["Sam", "the children", "my neighbour", "the baker", "the football team"]
TENSE_PLACES = ["park", "kitchen", "beach", "library", "garden"]

# --------------------------------------------------------------------------------------
# Ownership family material
# --------------------------------------------------------------------------------------
# {n1},{n2} names in prompt order; {o1},{o2} the objects attached to n1,n2; {ask} asked object.
OWNERSHIP_TEMPLATES: List[Dict[str, str]] = [
    {"id": "own-t1", "cue": "has",
     "text": "{N1} has the {o1}. {N2} has the {o2}. Who has the {ask}? Answer with the name only."},
    {"id": "own-t2", "cue": "is holding",
     "text": "{N1} is holding the {o1}, and {N2} is holding the {o2}. Who is holding the {ask}? Reply with the name only."},
    {"id": "own-t3", "cue": "owns",
     "text": "{N1} owns the {o1}. {N2} owns the {o2}. Which of them owns the {ask}? One word."},
    {"id": "own-t4", "cue": "keeps",
     "text": "{N1} keeps the {o1}; {N2} keeps the {o2}. Who keeps the {ask}? Give just the name."},
    {"id": "own-t5", "cue": "carries",
     "text": "{N1} carries the {o1} and {N2} carries the {o2}. Who carries the {ask}? Name only."},
]
OWNERSHIP_NAMES: List[Tuple[str, str]] = [
    ("Mira", "Leo"),  # dev
    ("Priya", "Tomas"), ("Kenji", "Farah"), ("Nadia", "Omar"), ("Elif", "Jonas"),
]
# (asked object, other object)
OWNERSHIP_OBJECTS: List[Tuple[str, str]] = [
    ("red key", "blue key"),  # dev
    ("map", "compass"), ("lantern", "rope"), ("violin", "flute"), ("ticket", "wallet"),
]

# --------------------------------------------------------------------------------------
# Mapping family material
# --------------------------------------------------------------------------------------
# rule = "{src} {arrow} {dst}"; {rules} is the rule list; {start} the start symbol.
MAPPING_TEMPLATES: List[Dict[str, str]] = [
    {"id": "map-t1", "arrow": "→",
     "text": "{rules} Start at {start} and follow the arrows twice. Where do you end up? Answer with the symbol only."},
    {"id": "map-t2", "arrow": "maps to",
     "text": "{rules} Begin at {start} and apply the mapping two times. Which one do you reach? Reply with one word."},
    {"id": "map-t3", "arrow": "->",
     "text": "{rules} Starting from {start}, apply the rule twice. What do you get? One word only."},
    {"id": "map-t4", "arrow": "leads to",
     "text": "{rules} From {start}, take two steps. Which one do you land on? Give the answer only."},
    {"id": "map-t5", "arrow": "→",
     "text": "{rules} Start at {start} and apply the mapping twice. What do you reach? Answer with one word."},
]
# (start, intermediate, candidate0, candidate1) - candidate order is later decided by seed
MAPPING_SYMBOLS: List[Tuple[str, str, str, str]] = [
    ("A", "B", "C", "D"),  # dev
    ("circle", "square", "triangle", "star"),
    ("zib", "wug", "blif", "tarn"),
    ("P", "Q", "R", "S"),
    ("fox", "owl", "bear", "wolf"),
]

SHORT_ANSWER_CUE = re.compile(
    r"(one word|name only|the name|symbol only|answer only|single word|single short sentence|"
    r"one short sentence|one sentence|one brief sentence|short sentence)", re.I)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_items(items: List[dict]) -> str:
    return hashlib.sha256(_canonical(items).encode("utf-8")).hexdigest()


def _word_regex(word: str) -> str:
    return r"(?i)\b" + re.escape(word) + r"\b"


def _item(item_id, pair_id, version, family, split, template_id, prompt, primary, secondary,
          regex, construction, notes="") -> dict:
    return {
        "item_id": item_id, "pair_id": pair_id, "version": version, "family": family,
        "split": split, "template_id": template_id, "prompt_text": prompt,
        "render": "chat", "system": None,
        "primary": primary, "secondary": secondary,
        "target_answer_regex": regex,
        "construction": construction,  # extra (superset of §1): first_mentioned_candidate etc.
        "notes": notes,
    }


def _counterbalance_slots(rng: random.Random) -> List[bool]:
    """For the 4 test pairs: exactly two True, two False, order decided by rng."""
    slots = [True, True, False, False]
    rng.shuffle(slots)
    return slots


# --------------------------------------------------------------------------------------
# Family builders: each returns a list of items for pairs 01..05
# --------------------------------------------------------------------------------------
def build_language(rng: random.Random) -> List[dict]:
    items = []
    # test templates: two "cue before" (t2,t4), two "cue after" (t3,t5); seed permutes them
    test_templates = LANGUAGE_TEMPLATES[1:]
    rng.shuffle(test_templates)
    for k, mat in enumerate(LANGUAGE_PAIRS, start=1):
        pair_id = f"lang-{k:02d}"
        split = "dev" if k == DEV_PAIR_INDEX else "test"
        langs = list(mat["langs"])
        if rng.random() < 0.5:  # candidate order decided by seed
            langs.reverse()
        tid, tmpl = LANGUAGE_TEMPLATES[0] if split == "dev" else test_templates[k - 2]
        cue_position = "before" if tmpl.index("{lang}") < tmpl.index("{q}") else "after"
        for version, ans in zip("AB", langs):
            other = langs[1 - langs.index(ans)]
            prompt = tmpl.format(lang=ans, q=mat["question"])
            primary = {"name": "response_language", "question": "In which language is the reply requested?",
                       "candidates": langs, "answer": ans, "answer_aliases": LANGUAGE_ALIASES[ans]}
            secondary = {"entities": [], "objects": [], "relation": None}
            regex = r"(?i)\b(" + mat["expected"][ans] + r")\b"
            construction = {"first_mentioned_candidate": ans, "answer_position": langs.index(ans),
                            "cue_position": cue_position, "other_candidate": other,
                            "expected_word_other": mat["expected"][other]}
            items.append(_item(f"{pair_id}{version}", pair_id, version, "language", split, tid,
                               prompt, primary, secondary, regex, construction,
                               notes="only the requested language is named in the prompt; the other candidate is never mentioned"))
    return items


def build_tense(rng: random.Random) -> List[dict]:
    items = []
    subjects = TENSE_SUBJECTS[1:]
    places = TENSE_PLACES[1:]
    rng.shuffle(subjects)
    rng.shuffle(places)
    test_templates = TENSE_TEMPLATES[1:]
    rng.shuffle(test_templates)
    for k in range(1, N_PAIRS_PER_FAMILY + 1):
        pair_id = f"tense-{k:02d}"
        split = "dev" if k == DEV_PAIR_INDEX else "test"
        if split == "dev":
            tid, past_t, fut_t = TENSE_TEMPLATES[0]
            subj, place = TENSE_SUBJECTS[0], TENSE_PLACES[0]
        else:
            tid, past_t, fut_t = test_templates[k - 2]
            subj, place = subjects[k - 2], places[k - 2]
        cands = ["past", "future"]
        for version, ans in zip("AB", cands):
            tmpl = past_t if ans == "past" else fut_t
            prompt = tmpl.format(subj=subj, place=place)
            primary = {"name": "response_tense", "question": "Is the requested sentence about the past or the future?",
                       "candidates": cands, "answer": ans, "answer_aliases": []}
            secondary = {"entities": [], "objects": [], "relation": None}
            # The authoritative target scorer is core/scoring.py::detect_tense; this regex is the
            # explicit-marker layer of that detector (kept here so the field is never empty).
            regex = (r"(?i)\b(yesterday|was|were|did|went|had|\w{3,}ed)\b" if ans == "past"
                     else r"(?i)(\b(will|shall|tomorrow|going to)\b|'ll\b)")
            construction = {"first_mentioned_candidate": ans, "answer_position": cands.index(ans),
                            "cue_position": "n/a", "other_candidate": cands[1 - cands.index(ans)],
                            "subject": subj, "place": place}
            items.append(_item(f"{pair_id}{version}", pair_id, version, "tense", split, tid,
                               prompt, primary, secondary, regex, construction,
                               notes="target scored by scoring.detect_tense, not by target_answer_regex alone"))
    return items


def build_ownership(rng: random.Random) -> List[dict]:
    items = []
    test_templates = OWNERSHIP_TEMPLATES[1:]
    test_names = OWNERSHIP_NAMES[1:]
    test_objects = OWNERSHIP_OBJECTS[1:]
    rng.shuffle(test_templates)
    rng.shuffle(test_names)
    rng.shuffle(test_objects)
    c0_first_slots = _counterbalance_slots(rng)  # True: candidates[0] mentioned first in prompt
    for k in range(1, N_PAIRS_PER_FAMILY + 1):
        pair_id = f"own-{k:02d}"
        split = "dev" if k == DEV_PAIR_INDEX else "test"
        if split == "dev":
            tmpl, names, objs, c0_first = OWNERSHIP_TEMPLATES[0], OWNERSHIP_NAMES[0], OWNERSHIP_OBJECTS[0], True
        else:
            tmpl, names, objs = test_templates[k - 2], test_names[k - 2], test_objects[k - 2]
            c0_first = c0_first_slots[k - 2]
        cands = list(names)
        if rng.random() < 0.5:
            cands.reverse()
        ask, other_obj = objs
        n1, n2 = (cands[0], cands[1]) if c0_first else (cands[1], cands[0])
        for version, ans in zip("AB", cands):
            # the answer-name gets the asked object; the other name gets the other object
            o_for = {ans: ask, cands[1 - cands.index(ans)]: other_obj}
            prompt = tmpl["text"].format(N1=n1, N2=n2, o1=o_for[n1], o2=o_for[n2], ask=ask)
            primary = {"name": f"{ask.replace(' ', '_')}_owner",
                       "question": f"Who {tmpl['cue']} the {ask}?",
                       "candidates": cands, "answer": ans, "answer_aliases": [ans.lower()]}
            secondary = {"entities": cands, "objects": [ask, other_obj],
                         "relation": {"type": tmpl["cue"], "subject": ans, "object": ask}}
            construction = {"first_mentioned_candidate": n1, "answer_position": cands.index(ans),
                            "cue_position": "n/a", "other_candidate": cands[1 - cands.index(ans)],
                            "answer_is_first_mentioned": n1 == ans}
            items.append(_item(f"{pair_id}{version}", pair_id, version, "ownership", split, tmpl["id"],
                               prompt, primary, secondary, _word_regex(ans), construction))
    return items


def build_mapping(rng: random.Random) -> List[dict]:
    items = []
    test_templates = MAPPING_TEMPLATES[1:]
    test_symbols = MAPPING_SYMBOLS[1:]
    rng.shuffle(test_templates)
    rng.shuffle(test_symbols)
    distractor_last_slots = _counterbalance_slots(rng)  # True: answer candidate mentioned first
    for k in range(1, N_PAIRS_PER_FAMILY + 1):
        pair_id = f"map-{k:02d}"
        split = "dev" if k == DEV_PAIR_INDEX else "test"
        if split == "dev":
            tmpl, syms, distractor_last = MAPPING_TEMPLATES[0], MAPPING_SYMBOLS[0], True
        else:
            tmpl, syms = test_templates[k - 2], test_symbols[k - 2]
            distractor_last = distractor_last_slots[k - 2]
        start, mid, c0, c1 = syms
        cands = [c0, c1]
        if rng.random() < 0.5:
            cands.reverse()
        arrow = tmpl["arrow"]
        for version, ans in zip("AB", cands):
            other = cands[1 - cands.index(ans)]
            hop1 = f"{start} {arrow} {mid}."
            hop2 = f"{mid} {arrow} {ans}."
            distractor = f"{other} {arrow} {start}."
            rules = [hop1, hop2, distractor] if distractor_last else [distractor, hop1, hop2]
            prompt = tmpl["text"].format(rules=" ".join(rules), start=start)
            primary = {"name": "two_step_result",
                       "question": f"Starting from {start}, what does applying the mapping twice reach?",
                       "candidates": cands, "answer": ans, "answer_aliases": [ans.lower()]}
            secondary = {"entities": [start, mid, cands[0], cands[1]], "objects": [],
                         "relation": {"type": "maps_to", "subject": mid, "object": ans}}
            construction = {"first_mentioned_candidate": ans if distractor_last else other,
                            "answer_position": cands.index(ans), "cue_position": "n/a",
                            "other_candidate": other, "start": start, "intermediate": mid,
                            "arrow": arrow, "answer_is_first_mentioned": distractor_last}
            items.append(_item(f"{pair_id}{version}", pair_id, version, "mapping", split, tmpl["id"],
                               prompt, primary, secondary, _word_regex(ans), construction,
                               notes="versions differ by swapping the two candidates in hop 2 and in the distractor rule"))
    return items


# --------------------------------------------------------------------------------------
# Independent mini-solver (re-derives the answer from the prompt text alone)
# --------------------------------------------------------------------------------------
def solve_prompt(item: dict) -> Optional[str]:
    p = item["prompt_text"]
    c = item["primary"]["candidates"]
    fam = item["family"]
    if fam == "language":
        hits = [x for x in c if re.search(r"\b" + re.escape(x) + r"\b", p)]
        return hits[0] if len(hits) == 1 else None
    if fam == "tense":
        past = bool(re.search(r"\byesterday\b", p)) and bool(re.search(r"\bdid\b", p))
        fut = bool(re.search(r"\btomorrow\b", p)) and bool(re.search(r"\bwill\b", p))
        return "past" if past and not fut else "future" if fut and not past else None
    if fam == "ownership":
        ask = item["secondary"]["objects"][0]
        m = re.findall(r"\b(" + "|".join(map(re.escape, c)) + r")\b\s+(?:has|is holding|owns|keeps|carries)\s+the\s+("
                       + re.escape(ask) + r")\b", p)
        owners = sorted({n for n, _ in m})
        return owners[0] if len(owners) == 1 else None
    if fam == "mapping":
        start = item["construction"]["start"]
        arrow = item["construction"]["arrow"]
        rules = dict(re.findall(r"(\S+) " + re.escape(arrow) + r" (\S+)\.", p))
        try:
            return rules[rules[start]]
        except KeyError:
            return None
    return None


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------
REQUIRED_KEYS = {"item_id", "pair_id", "version", "family", "split", "template_id", "prompt_text",
                 "render", "system", "primary", "secondary", "target_answer_regex", "notes"}


def validate(items: List[dict]) -> Dict[str, Any]:
    """Raise AssertionError on any violation; return the balance report."""
    assert len(items) == 40, len(items)
    by_pair: Dict[str, List[dict]] = {}
    for it in items:
        assert REQUIRED_KEYS <= set(it), set(it) ^ REQUIRED_KEYS
        assert it["item_id"] == it["pair_id"] + it["version"]
        assert it["version"] in ("A", "B")
        assert it["family"] in FAMILIES and it["split"] in ("dev", "test")
        assert it["render"] == "chat" and it["system"] is None
        pr = it["primary"]
        assert len(pr["candidates"]) == 2 and len(set(pr["candidates"])) == 2
        assert pr["answer"] in pr["candidates"]
        assert pr["candidates"].index(pr["answer"]) == ("A", "B").index(it["version"]), it["item_id"]
        assert pr["answer"] not in pr["candidates"][1 - pr["candidates"].index(pr["answer"])]
        re.compile(it["target_answer_regex"])  # must compile
        assert SHORT_ANSWER_CUE.search(it["prompt_text"]), ("no short-answer cue", it["item_id"])
        assert len(it["prompt_text"]) < 260, it["item_id"]
        solved = solve_prompt(it)
        assert solved == pr["answer"], ("solver disagrees with construction", it["item_id"], solved, pr["answer"])
        # regex sanity: a plausible correct answer matches; the other candidate's plausible answer does not
        if it["family"] == "ownership" or it["family"] == "mapping":
            assert re.search(it["target_answer_regex"], pr["answer"])
            assert not re.search(it["target_answer_regex"], it["construction"]["other_candidate"])
        by_pair.setdefault(it["pair_id"], []).append(it)
    assert len(by_pair) == 20
    for pid, pair in by_pair.items():
        assert len(pair) == 2 and {x["version"] for x in pair} == {"A", "B"}
        a, b = sorted(pair, key=lambda x: x["version"])
        for key in ("family", "split", "template_id"):
            assert a[key] == b[key], (pid, key)
        assert a["primary"]["candidates"] == b["primary"]["candidates"], pid
        assert a["primary"]["name"] == b["primary"]["name"], pid
        assert a["primary"]["answer"] != b["primary"]["answer"], pid
        assert a["prompt_text"] != b["prompt_text"], pid
        # minimal edit: both prompts have the same length in words +- the swapped tokens
        assert abs(len(a["prompt_text"].split()) - len(b["prompt_text"].split())) <= 1, pid
    report: Dict[str, Any] = {}
    for fam in FAMILIES:
        fam_items = [x for x in items if x["family"] == fam]
        assert len(fam_items) == 10
        dev = [x for x in fam_items if x["split"] == "dev"]
        test = [x for x in fam_items if x["split"] == "test"]
        assert len(dev) == 2 and len(test) == 8, fam
        pos_counts = [sum(1 for x in test if x["construction"]["answer_position"] == p) for p in (0, 1)]
        assert pos_counts == [4, 4], (fam, pos_counts)
        dev_tids = {x["template_id"] for x in dev}
        test_tids = {x["template_id"] for x in test}
        assert not (dev_tids & test_tids), (fam, "dev template reused in test")
        assert len(test_tids) == 4, (fam, "test templates must all differ", test_tids)
        entry: Dict[str, Any] = {"n_dev": len(dev), "n_test": len(test),
                                 "test_answer_position_counts": {"first_listed": pos_counts[0], "second_listed": pos_counts[1]},
                                 "test_templates": sorted(test_tids), "dev_templates": sorted(dev_tids)}
        if fam in ("ownership", "mapping"):
            # the order of candidate mentions in the prompt is counterbalanced across test pairs
            first_is_answer = {x["item_id"]: x["construction"]["answer_is_first_mentioned"] for x in test}
            n_first = sum(first_is_answer.values())
            assert n_first == 4, (fam, "answer should be first-mentioned in exactly 4 of 8 test items", first_is_answer)
            for v in "AB":
                vals = [first_is_answer[x["item_id"]] for x in test if x["version"] == v]
                assert len(set(vals)) == 2, (fam, f"version {v}: answer is first-mentioned in all (or no) pairs")
            entry["test_answer_is_first_mentioned"] = n_first
            entry["test_answer_is_first_mentioned_by_version"] = {
                v: sum(first_is_answer[x["item_id"]] for x in test if x["version"] == v) for v in "AB"}
        elif fam == "language":
            cue_pos = [x["construction"]["cue_position"] for x in test if x["version"] == "A"]
            assert sorted(cue_pos) == ["after", "after", "before", "before"], cue_pos
            entry["test_cue_position"] = {"before": cue_pos.count("before"), "after": cue_pos.count("after")}
            entry["test_answer_is_first_mentioned"] = "n/a (only the answer language is named in the prompt)"
        else:
            entry["test_answer_is_first_mentioned"] = "n/a (only the answer tense cue appears in the prompt)"
        report[fam] = entry
    return report


# --------------------------------------------------------------------------------------
# Build / IO
# --------------------------------------------------------------------------------------
def build(seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    rng = random.Random(seed)
    items: List[dict] = []
    items += build_language(random.Random(rng.random()))
    items += build_tense(random.Random(rng.random()))
    items += build_ownership(random.Random(rng.random()))
    items += build_mapping(random.Random(rng.random()))
    report = validate(items)
    meta = {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "seed": seed, "n_pairs": len(items) // 2, "families": FAMILIES,
            "dev_pair_index": DEV_PAIR_INDEX,
            "sha256_items": sha256_items(items), "frozen": False,
            "balance_checks": report}
    return {"meta": meta, "items": items}


def load_items(path: str = DEFAULT_OUT) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def summary_rows(items: List[dict]) -> List[Tuple[str, str, str, str, str]]:
    return [(it["item_id"], it["family"], it["split"], it["primary"]["answer"],
             str(it["construction"]["first_mentioned_candidate"])) for it in items]


def print_summary(data: Dict[str, Any]) -> None:
    rows = summary_rows(data["items"])
    w = [max(len(str(r[i])) for r in rows + [("item_id", "family", "split", "answer", "first_mentioned")]) for i in range(5)]
    hdr = ("item_id", "family", "split", "answer", "first_mentioned")
    print("  ".join(h.ljust(w[i]) for i, h in enumerate(hdr)))
    for r in rows:
        print("  ".join(str(r[i]).ljust(w[i]) for i in range(5)))
    print("\nbalance checks:")
    print(json.dumps(data["meta"]["balance_checks"], indent=1, ensure_ascii=False))
    print("sha256_items:", data["meta"]["sha256_items"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--print", action="store_true", help="print the summary table (also after writing)")
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
        print_summary(data)


if __name__ == "__main__":
    main()
