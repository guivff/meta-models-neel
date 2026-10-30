"""R-C2 planted-context conflicts (BRIEF_R.md §3 and §3.1; WS5). A false fact in the system turn, the true fact as the
model's belief, candidates = (context answer, belief answer), 48 mirror pairs × 2 versions × 3 question paraphrases
= 288 items (96 base items).

Design (pre-registered in BRIEF_R §3.1): a pair is two entities E1, E2 and two questions Q1 (true answer E1) and Q2
(true answer E2). Version A: the system turn asserts that Q1's answer is E2 and the user turn asks Q1 → candidates
(context, belief) = (E2, E1). Version B: the system turn asserts that Q2's answer is E1 and asks Q2 → (E1, E2). Within
a pair the two names swap roles (a name preference cancels in the within-pair win, as in V7); the visible prompt never
contains a candidate. Six categories × 8 pairs; two preamble templates, the same for both versions of a pair, 4 / 4
per category; seeded (template assignment, which side is version A). E7 (IDEAS_R): every (pair, version) is asked in
three paraphrases q0 / q1 / q2 with the same system turn, each its own item (``rc2-01A-q0``, ``base_item_id``
rc2-01A); the model's switching between paraphrases is the ground truth for "reads the model".

    python -m projects.g_agreement.r_bench.planted --check [--tokenizer]      # print the pairs (+ J-lens single-token coverage)
    python -m projects.g_agreement.r_bench.planted --build                    # dataset/items_rc2.json (refuses to overwrite a different bank)
    python -m projects.g_agreement.r_bench.planted --freeze                   # freeze mark dataset/rc2_frozen.json (bytes must match the R manifest)
    python -m projects.g_agreement.r_bench.planted --phase A [--smoke]        # pod: states, logit lens, prompt-only, J-lens / Oracle / skip-lens
    python -m projects.g_agreement.r_bench.planted --phase B                  # pod: NLA at 42
    python -m projects.g_agreement.r_bench.planted --select                   # compliance + switching selection (model only) -> results/g_agreement/r/rc2_selection.*
    python -m projects.g_agreement.r_bench.planted --probe [--n-perm 10]      # CPU: leave-pair-out probe for the model's side (PRESENT) -> rc2_probe.*
    python -m projects.g_agreement.r_bench.planted --summarize                # the pre-registered tables (+ reader vs probe, H3) -> results/g_agreement/r/rc2.md

Arms: ``rc2_planted`` (system turn present) and ``rc2_nosys`` (same items, no system turn: the belief arm). Rows go
to the Phase R cache in collect.py's formats (states/<dataset>/chat_L<layer>.npy, logit_lens.jsonl, prompt_only.jsonl,
reader_lo.jsonl, state_free.jsonl); every row written here carries ``paraphrase`` and ``base_item_id``.
``collect.capture_dataset`` / ``collect_reader_lo`` take one candidate pair per dataset, so the capture and reader-LO
loops here run the same primitives per item; ``collect_prompt_only`` is reused with the render patched to carry the
system turn (primary: the capture render itself; secondary ``rc2_planted_fc``: the §2.2 forced-choice template with
the system turn, option order alternating by pair).
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from common import stats as ST
from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import StepLedger, now_iso, read_jsonl, timed_call
from projects.g_agreement.r_bench import collect as RC
from projects.g_agreement.r_bench import datasets as D

MODULE = "r"
SEED = 20261019
ITEMS_RC2 = C.DATASET_DIR / "items_rc2.json"
DATASET = "rc2_planted"
DATASET_NOSYS = "rc2_nosys"
FC_SUFFIX = "_fc"
TAG = "CONTEXT"
SPLIT = "test"
RENDER = "chat"
N_PAIRS = 48
PER_CATEGORY = 8
N_PARAPHRASES = 3
RESULTS = RC.RESULTS
PREAMBLES: list[dict[str, str]] = [
    {"id": "rc2-p0", "level": "p0", "text": "For this conversation, {fact}."},
    {"id": "rc2-p1", "level": "p1", "text": "Background for this conversation: {fact}."},
]
# pre-registered thresholds (BRIEF_R §3.1, mirroring §4.3)
READS_HI, READS_LO = 0.75, 0.25
MIN_COMPLIERS, MIN_NONCOMPLIERS = 24, 12
NOSYS_GATE = 0.75
MIN_SWITCHING = 12            # E7: switching base items needed for a verdict
C_GRID = (0.01, 0.1, 1.0, 10.0)   # §2.2 probe grid
PROBE_HI = 0.75               # H3: first layer with AUROC >= 0.75 and CI > 0.5
MIN_MINORITY = 12             # probe not trainable below this many kept items in the minority class
PROBE_JSON = "rc2_probe.json"
KEPT = ("complier", "non_complier")


# ------------------------------------------------------------------ the pairs
@dataclass(frozen=True)
class Side:
    questions: tuple[str, str, str]   # q0 original wording, q1 "Which …", q2 "Name …" (the format suffix is the pair's)
    statement: str                    # declarative with {X}; lower-case start when it begins with "the"
    answer: str                       # the true answer, spelled as the model would answer it (the belief)
    mention: str | None = None        # how the answer is written inside a statement (default: answer)
    jlens: str | None = None          # the distinguishing single token for the J-lens (default: answer)

    @property
    def question(self) -> str:
        return self.questions[0]

    @property
    def mention_text(self) -> str:
        return self.mention if self.mention is not None else self.answer

    @property
    def jlens_text(self) -> str:
        return self.jlens if self.jlens is not None else self.answer


@dataclass(frozen=True)
class PairSpec:
    category: str
    suffix: str
    sides: tuple[Side, Side]


def _q3(noun: str, which_pred: str, what_np: str) -> tuple[str, str, str]:
    """Three paraphrases of a superlative question: 'Which {noun} is {pred}?' / 'What is {np}?' / 'Name {np}.'"""
    return (f"Which {noun} is {which_pred}?", f"What is {what_np}?", f"Name {what_np}.")


def _city(country: str, capital: str, largest: str) -> PairSpec:
    return PairSpec("capital_city", "Answer with the city name only.",
                    (Side((f"What is the capital city of {country}?", f"Which city is the capital of {country}?", f"Name the capital city of {country}."),
                          f"the capital city of {country} is {{X}}", capital),
                     Side((f"What is the largest city in {country}?", f"Which city is the largest in {country}?", f"Name the largest city in {country}."),
                          f"the largest city in {country} is {{X}}", largest)))


def _author(book1: str, a1: str, book2: str, a2: str) -> PairSpec:
    def side(book: str, a: str) -> Side:
        return Side((f"Who wrote {book}?", f"Who is the author of {book}?", f"Name the author of {book}."), f"{book} was written by {{X}}", a)
    return PairSpec("author", "Answer with the author's surname only.", (side(book1, a1), side(book2, a2)))


def _element(sym1: str, e1: str, sym2: str, e2: str) -> PairSpec:
    def side(sym: str, e: str) -> Side:
        return Side((f"Which chemical element has the symbol {sym}?", f"What element does the chemical symbol {sym} stand for?",
                     f"Name the chemical element whose symbol is {sym}."), f"the chemical symbol {sym} stands for {{X}}", e, e.lower())
    return PairSpec("element", "Answer with the element name only.", (side(sym1, e1), side(sym2, e2)))


def _superlative(s1: Side, s2: Side) -> PairSpec:
    return PairSpec("superlative", "Answer with the name only.", (s1, s2))


def _currency(c1: str, cur1: str, c2: str, cur2: str) -> PairSpec:
    def side(c: str, cur: str) -> Side:
        return Side((f"What is the official currency of {c}?", f"Which currency is the official currency of {c}?", f"Name the official currency of {c}."),
                    f"the official currency of {c} is the {{X}}", cur, cur.lower())
    return PairSpec("currency_language", "Answer with the currency name only.", (side(c1, cur1), side(c2, cur2)))


def _language(c1: str, l1: str, c2: str, l2: str) -> PairSpec:
    def side(c: str, lang: str) -> Side:
        return Side((f"What is the official language of {c}?", f"Which language is the official language of {c}?", f"Name the official language of {c}."),
                    f"the official language of {c} is {{X}}", lang)
    return PairSpec("currency_language", "Answer with the language name only.", (side(c1, l1), side(c2, l2)))


def _people(s1: Side, s2: Side) -> PairSpec:
    return PairSpec("people", "Answer with the surname only.", (s1, s2))


PAIRS: list[PairSpec] = [
    # capital vs largest city (8)
    _city("Australia", "Canberra", "Sydney"), _city("Turkey", "Ankara", "Istanbul"), _city("Canada", "Ottawa", "Toronto"),
    _city("Switzerland", "Bern", "Zurich"), _city("Pakistan", "Islamabad", "Karachi"), _city("New Zealand", "Wellington", "Auckland"),
    _city("China", "Beijing", "Shanghai"), _city("Scotland", "Edinburgh", "Glasgow"),
    # authors (8)
    _author("Animal Farm", "Orwell", "The Metamorphosis", "Kafka"),
    _author("The Hobbit", "Tolkien", "The Lion, the Witch and the Wardrobe", "Lewis"),
    _author("Hamlet", "Shakespeare", "Paradise Lost", "Milton"),
    _author("the Iliad", "Homer", "the Divine Comedy", "Dante"),
    _author("Oliver Twist", "Dickens", "Tess of the d'Urbervilles", "Hardy"),
    _author("Ulysses", "Joyce", "The Picture of Dorian Gray", "Wilde"),
    _author("The Great Gatsby", "Fitzgerald", "Frankenstein", "Shelley"),
    _author("Les Misérables", "Hugo", "The Raven", "Poe"),
    # element symbols (8)
    _element("Au", "Gold", "Ag", "Silver"), _element("Fe", "Iron", "Cu", "Copper"), _element("Na", "Sodium", "K", "Potassium"),
    _element("He", "Helium", "Ne", "Neon"), _element("Pb", "Lead", "Sn", "Tin"), _element("H", "Hydrogen", "O", "Oxygen"),
    _element("N", "Nitrogen", "C", "Carbon"), _element("Ca", "Calcium", "Mg", "Magnesium"),
    # superlatives (8)
    _superlative(Side(_q3("planet", "the largest in the Solar System", "the largest planet in the Solar System"), "the largest planet in the Solar System is {X}", "Jupiter"),
                 Side(_q3("planet", "the smallest in the Solar System", "the smallest planet in the Solar System"), "the smallest planet in the Solar System is {X}", "Mercury")),
    _superlative(Side(_q3("planet", "known as the Red Planet", "the planet known as the Red Planet"), "the planet known as the Red Planet is {X}", "Mars"),
                 Side(_q3("planet", "the hottest in the Solar System", "the hottest planet in the Solar System"), "the hottest planet in the Solar System is {X}", "Venus")),
    _superlative(Side(_q3("planet", "famous for its prominent ring system", "the planet famous for its prominent ring system"),
                      "the planet famous for its prominent ring system is {X}", "Saturn"),
                 Side(_q3("planet", "the farthest from the Sun", "the planet farthest from the Sun"), "the planet farthest from the Sun is {X}", "Neptune")),
    _superlative(Side(_q3("river", "the longest in Africa", "the longest river in Africa"), "the longest river in Africa is the {X}", "Nile"),
                 Side(_q3("river", "the longest in South America", "the longest river in South America"), "the longest river in South America is the {X}", "Amazon")),
    _superlative(Side(_q3("ocean", "the largest on Earth", "the largest ocean on Earth"), "the largest ocean on Earth is the {X}", "Pacific"),
                 Side(_q3("ocean", "the smallest on Earth", "the smallest ocean on Earth"), "the smallest ocean on Earth is the {X}", "Arctic")),
    _superlative(Side(_q3("continent", "the largest by area", "the largest continent by area"), "the largest continent by area is {X}", "Asia"),
                 Side(_q3("continent", "the coldest", "the coldest continent"), "the coldest continent is {X}", "Antarctica")),
    _superlative(Side(_q3("country", "the largest by area", "the largest country by area"), "the largest country by area is {X}", "Russia"),
                 Side(_q3("country", "the smallest by area", "the smallest country by area"), "the smallest country by area is {X}", "Vatican City", jlens="Vatican")),
    _superlative(Side(_q3("mountain", "the highest on Earth", "the highest mountain on Earth"), "the highest mountain on Earth is {X}", "Mount Everest", jlens="Everest"),
                 Side(_q3("mountain", "the highest in Japan", "the highest mountain in Japan"), "the highest mountain in Japan is {X}", "Mount Fuji", jlens="Fuji")),
    # currency / official language (8)
    _currency("Japan", "Yen", "Germany", "Euro"), _currency("the United States", "Dollar", "Mexico", "Peso"),
    _currency("the United Kingdom", "Pound", "South Africa", "Rand"),
    _language("Brazil", "Portuguese", "Argentina", "Spanish"), _language("Austria", "German", "France", "French"),
    _language("South Korea", "Korean", "the Netherlands", "Dutch"), _language("Sweden", "Swedish", "Greece", "Greek"),
    _language("Egypt", "Arabic", "Iran", "Persian"),
    # people (8)
    _people(Side(("Who was the first president of the United States?", "Which person was the first president of the United States?",
                  "Name the first president of the United States."), "the first president of the United States was {X}", "Washington"),
            Side(("Which US president delivered the Gettysburg Address?", "Who delivered the Gettysburg Address?",
                  "Name the US president who delivered the Gettysburg Address."), "the US president who delivered the Gettysburg Address was {X}", "Lincoln")),
    _people(Side(("Who developed the theory of general relativity?", "Which scientist developed the theory of general relativity?",
                  "Name the person who developed the theory of general relativity."), "the theory of general relativity was developed by {X}", "Einstein"),
            Side(("Who proposed the theory of evolution by natural selection?", "Which scientist proposed the theory of evolution by natural selection?",
                  "Name the person who proposed the theory of evolution by natural selection."),
                 "the theory of evolution by natural selection was proposed by {X}", "Darwin")),
    _people(Side(("Who formulated the law of universal gravitation?", "Which scientist formulated the law of universal gravitation?",
                  "Name the person who formulated the law of universal gravitation."), "the law of universal gravitation was formulated by {X}", "Newton"),
            Side(("Who invented the phonograph?", "Which inventor invented the phonograph?", "Name the inventor of the phonograph."),
                 "the phonograph was invented by {X}", "Edison")),
    _people(Side(("Who is credited with inventing the telephone?", "Which inventor is credited with the telephone?",
                  "Name the person credited with inventing the telephone."), "the telephone was invented by {X}", "Bell"),
            Side(("Who invented the alternating-current induction motor?", "Which inventor developed the alternating-current induction motor?",
                  "Name the inventor of the alternating-current induction motor."), "the alternating-current induction motor was invented by {X}", "Tesla")),
    _people(Side(("Who composed the opera The Magic Flute?", "Which composer wrote the opera The Magic Flute?", "Name the composer of the opera The Magic Flute."),
                 "the opera The Magic Flute was composed by {X}", "Mozart"),
            Side(("Who composed the Brandenburg Concertos?", "Which composer wrote the Brandenburg Concertos?", "Name the composer of the Brandenburg Concertos."),
                 "the Brandenburg Concertos were composed by {X}", "Bach")),
    _people(Side(("Who painted Guernica?", "Which artist painted Guernica?", "Name the painter of Guernica."), "Guernica was painted by {X}", "Picasso"),
            Side(("Who painted the Water Lilies series?", "Which artist painted the Water Lilies series?", "Name the painter of the Water Lilies series."),
                 "the Water Lilies series was painted by {X}", "Monet")),
    _people(Side(("Who led the 1492 voyage that reached the Americas?", "Which explorer led the 1492 voyage that reached the Americas?",
                  "Name the leader of the 1492 voyage that reached the Americas."), "the 1492 voyage that reached the Americas was led by {X}", "Columbus"),
            Side(("Who was the first person to walk on the Moon?", "Which astronaut was the first to walk on the Moon?", "Name the first person to walk on the Moon."),
                 "the first person to walk on the Moon was {X}", "Armstrong")),
    _people(Side(("Who was crowned Emperor of the French in 1804?", "Which ruler was crowned Emperor of the French in 1804?",
                  "Name the person crowned Emperor of the French in 1804."), "the person crowned Emperor of the French in 1804 was {X}", "Napoleon"),
            Side(("Who was the British prime minister for most of the Second World War?",
                  "Which politician was the British prime minister for most of the Second World War?",
                  "Name the British prime minister for most of the Second World War."),
                 "the British prime minister for most of the Second World War was {X}", "Churchill")),
]
CATEGORIES = tuple(dict.fromkeys(p.category for p in PAIRS))


# ------------------------------------------------------------------ builder
def _cap_first(s: str) -> str:
    return s[:1].upper() + s[1:]


def nla_template(side: Side) -> str:
    """The NLA sentence for this question: the declarative statement with {X}, capitalised, with a full stop."""
    return _cap_first(side.statement) + "."


def build(seed: int = SEED, pairs: list[PairSpec] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """288 items (48 pairs × versions A / B × 3 paraphrases) in the items_r.json schema plus ``system``. Seeded: the
    preamble template per pair (4 p0 / 4 p1 within every category; both versions of a pair share it) and which side
    is version A. The three paraphrases of a base item share system, candidates and template."""
    pairs = PAIRS if pairs is None else pairs
    rng = np.random.default_rng(seed)
    by_cat: dict[str, list[int]] = defaultdict(list)
    for k, p in enumerate(pairs):
        by_cat[p.category].append(k)
    tmpl_of: dict[int, str] = {}
    for cat, ks in by_cat.items():
        half = len(ks) // 2
        p0 = set(rng.choice(ks, size=half, replace=False).tolist())
        for k in ks:
            tmpl_of[k] = "p0" if k in p0 else "p1"
    a_is_first_side = rng.random(len(pairs)) < 0.5
    items: list[dict[str, Any]] = []
    for k, p in enumerate(pairs):
        pair_id = f"rc2-{k + 1:02d}"
        tmpl = PREAMBLES[0 if tmpl_of[k] == "p0" else 1]
        order = (0, 1) if a_is_first_side[k] else (1, 0)
        for version, si in zip("AB", order):
            side, other = p.sides[si], p.sides[1 - si]
            ctx, belief = other.answer, side.answer
            false_statement = side.statement.format(X=other.mention_text)
            true_statement = side.statement.format(X=side.mention_text)
            system = tmpl["text"].format(fact=false_statement)
            base = f"{pair_id}{version}"
            for q, question in enumerate(side.questions):
                items.append({
                    "item_id": f"{base}-q{q}", "dataset": DATASET, "tag": TAG, "split": SPLIT, "label": 1, "raw_target": "context",
                    "prompt_text": f"{question} {p.suffix}", "render": RENDER, "system": system,
                    "primary": {"name": DATASET, "question": question, "candidates": [ctx, belief], "answer": ctx,
                                "template": nla_template(side), "sided": "two", "jlens": [other.jlens_text, side.jlens_text]},
                    "base_item_id": base, "paraphrase": q, "pair_id": pair_id, "pair_key": f"{pair_id}-q{q}", "version": version,
                    "pair_index": k, "category": p.category, "side_index": si,
                    "preamble_template": tmpl["level"], "preamble_id": tmpl["id"],
                    "context_answer": ctx, "belief_answer": belief, "false_statement": false_statement, "true_statement": true_statement,
                    "fc_context_first": k % 2 == 0,
                    "notes": "R-C2: the system turn asserts a false fact (context answer); the true fact is the model's belief; "
                             "candidates = [context, belief]; label 1 = pos is the context's answer (the text label); "
                             "paraphrase q0/q1/q2 = the same question in three wordings (E7)",
                })
    design = {"seed": seed, "n_pairs": len(pairs), "n_paraphrases": N_PARAPHRASES, "categories": {c: len(ks) for c, ks in by_cat.items()},
              "preambles": PREAMBLES, "template_of_pair": {f"rc2-{k + 1:02d}": v for k, v in sorted(tmpl_of.items())},
              "version_a_side": [int(not a) for a in a_is_first_side], "tag": TAG, "dataset": DATASET, "dataset_nosys": DATASET_NOSYS,
              "paraphrases": "q0 original wording, q1 'Which …' / 'Who is …', q2 'Name …'; identical system turn, candidates and template",
              "fc_option_order": "context first for even pair_index, belief first for odd (secondary forced-choice arm)"}
    return items, design


_WORD = re.compile(r"[A-Za-zÀ-ÿ']+")


def _mentions(text: str, token: str) -> bool:
    """Whole-word, case-insensitive mention of a candidate's distinguishing token ('Tin' must not match
    'continent'; 'Mount Everest' vs 'Mount Fuji' is checked on Everest / Fuji)."""
    return any(w.lower() == token.lower() for w in _WORD.findall(text))


def validate(items: list[dict[str, Any]], n_pairs: int = N_PAIRS, per_category: int | None = PER_CATEGORY) -> dict[str, Any]:
    """Invariants of the bank (also run by the tests). Raises AssertionError with the offending id."""
    assert len(items) == 2 * n_pairs * N_PARAPHRASES, len(items)
    required = {"item_id", "dataset", "tag", "split", "label", "raw_target", "prompt_text", "render", "system", "primary",
                "base_item_id", "paraphrase", "pair_id", "pair_key", "version", "category", "preamble_template",
                "context_answer", "belief_answer", "fc_context_first"}
    ids = [it["item_id"] for it in items]
    assert len(set(ids)) == len(ids), "duplicate item ids"
    texts = [it["prompt_text"] for it in items]
    assert len(set(texts)) == len(texts), "duplicate visible prompts"
    by_base: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        assert required <= set(it), (it.get("item_id"), required - set(it))
        assert it["dataset"] == DATASET and it["tag"] == TAG and it["split"] == SPLIT and it["render"] == RENDER and it["label"] == 1, it["item_id"]
        p = it["primary"]
        assert set(p) >= {"name", "question", "candidates", "answer", "template", "sided", "jlens"}, it["item_id"]
        c = p["candidates"]
        assert len(c) == 2 and c[0] != c[1], (it["item_id"], c)
        assert c == [it["context_answer"], it["belief_answer"]] and p["answer"] == c[0], it["item_id"]
        assert isinstance(it["system"], str) and it["system"], it["item_id"]
        assert len(p["jlens"]) == 2 and all(j and " " not in j for j in p["jlens"]), (it["item_id"], p["jlens"])
        jl = p["jlens"]
        assert _mentions(it["system"], jl[0]), (it["item_id"], "context answer missing from the system turn")
        assert not _mentions(it["system"], jl[1]), (it["item_id"], "belief answer in the system turn")
        for tokn in jl:
            assert not _mentions(it["prompt_text"], tokn), (it["item_id"], tokn, "candidate in the visible prompt")
        assert p["question"] in it["prompt_text"], it["item_id"]
        assert "{X}" in p["template"] and p["template"].endswith("."), it["item_id"]
        assert it["preamble_template"] in {"p0", "p1"}
        assert it["item_id"] == f"{it['base_item_id']}-q{it['paraphrase']}" and it["pair_key"] == f"{it['pair_id']}-q{it['paraphrase']}", it["item_id"]
        assert it["base_item_id"] == f"{it['pair_id']}{it['version']}", it["item_id"]
        by_base[it["base_item_id"]].append(it)
    assert len(by_base) == 2 * n_pairs, len(by_base)
    for bid, group in by_base.items():
        assert sorted(it["paraphrase"] for it in group) == list(range(N_PARAPHRASES)), bid
        for key in ("system", "primary", "context_answer", "belief_answer", "preamble_template", "fc_context_first", "category", "side_index"):
            vals = [json.dumps(it[key] if key != "primary" else {k: v for k, v in it[key].items() if k != "question"}, sort_keys=True) for it in group]
            assert len(set(vals)) == 1, (bid, key, "must not vary across paraphrases")
        assert len({it["primary"]["question"] for it in group}) == N_PARAPHRASES, (bid, "paraphrases must differ")
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        if it["paraphrase"] == 0:
            by_pair[it["pair_id"]].append(it)
    assert len(by_pair) == n_pairs, len(by_pair)
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert (a["version"], b["version"]) == ("A", "B"), pid
        assert a["primary"]["candidates"] == b["primary"]["candidates"][::-1], (pid, "the two names must swap roles")
        assert a["context_answer"] == b["belief_answer"] and a["belief_answer"] == b["context_answer"], pid
        assert a["preamble_template"] == b["preamble_template"] and a["category"] == b["category"], pid
        assert a["fc_context_first"] == b["fc_context_first"], pid
        assert a["prompt_text"] != b["prompt_text"] and a["system"] != b["system"], pid
    A = [sorted(pair, key=lambda x: x["version"])[0] for pair in by_pair.values()]
    tm = Counter(it["preamble_template"] for it in A)
    assert tm["p0"] == tm["p1"] == n_pairs // 2, tm
    fc = Counter(it["fc_context_first"] for it in A)
    assert fc[True] == fc[False] == n_pairs // 2, fc
    cats = Counter(it["category"] for it in A)
    if per_category is not None:
        assert set(cats.values()) == {per_category}, cats
    for cat in cats:
        sub = [it for it in A if it["category"] == cat]
        ct = Counter(it["preamble_template"] for it in sub)
        assert ct["p0"] == ct["p1"], (cat, ct)
        cf = Counter(it["fc_context_first"] for it in sub)
        assert cf[True] == cf[False], (cat, cf)
    return {"n_items": len(items), "n_base_items": len(by_base), "n_pairs": n_pairs, "n_paraphrases": N_PARAPHRASES, "templates": dict(tm),
            "categories": dict(cats), "version_a_asks_side0": sum(it["side_index"] == 0 for it in A), "fc_context_first": fc[True]}


def sha256_items(items: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write_bank(items: list[dict[str, Any]], design: dict[str, Any], out: Path = ITEMS_RC2, force: bool = False) -> Path:
    """Write the bank; refuse to overwrite a file with a different sha (a different bank) unless ``force``."""
    rep = validate(items, design["n_pairs"], None)
    meta = {"created": datetime.now(UTC).isoformat(timespec="seconds"), "phase": "R", "module": "rc2", "seed": design["seed"],
            "n_items": len(items), "n_base_items": rep["n_base_items"], "n_pairs": design["n_pairs"], "n_paraphrases": N_PARAPHRASES,
            "dataset": DATASET, "dataset_nosys": DATASET_NOSYS, "tag": TAG,
            "sha256_items": sha256_items(items), "frozen": False, "design": design, "balance_checks": rep,
            "prompt_only": "primary = the capture render (system + visible prompt), teacher-forced lp(context) - lp(belief); "
                           f"secondary = PROMPT_ONLY_FC_TEMPLATE with the system turn (dataset {DATASET}{FC_SUFFIX})",
            "prompt_only_fc_template_sha256": C.sha256_bytes(D.PROMPT_ONLY_FC_TEMPLATE.encode()), "brief": "BRIEF_R.md §3.1 (+ E7 extension)"}
    out = Path(out)
    if out.exists() and not force:
        old = json.loads(out.read_text(encoding="utf-8"))
        if old.get("meta", {}).get("sha256_items") != meta["sha256_items"]:
            raise SystemExit(f"{out} exists with a different sha256 ({old.get('meta', {}).get('sha256_items')}); pass --force to replace it")
        if is_frozen(out):
            print(f"{out} unchanged and frozen (sha {meta['sha256_items'][:16]}; mark {frozen_mark_path(out).name})")
            return out
        meta["created"] = old["meta"].get("created", meta["created"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "items": items}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}: {len(items)} items, sha256 {meta['sha256_items']}")
    return out


def load_bank(path: Path = ITEMS_RC2) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def frozen_mark_path(path: Path = ITEMS_RC2) -> Path:
    """The freeze mark is a sidecar (dataset/rc2_frozen.json), never a change to the bank's bytes: the R manifest
    (collect --freeze-r) records the whole-file sha of items_rc2.json, and the integrator's ``require_frozen_r``
    compares it with the disk. The name must not match collect.items_files()' glob ``items_r*.json``."""
    path = Path(path)
    return path.parent / f"{path.stem.removeprefix('items_')}_frozen.json"


def read_frozen_mark(path: Path = ITEMS_RC2) -> dict[str, Any] | None:
    mp = frozen_mark_path(path)
    return json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else None


def is_frozen(path: Path = ITEMS_RC2) -> bool:
    """True iff the sidecar says frozen and its recorded whole-file sha is the bank on disk."""
    mk = read_frozen_mark(path)
    return bool(mk and mk.get("frozen") and Path(path).exists() and mk.get("file_sha256") == C.sha256_file(Path(path)))


def freeze_bank(path: Path = ITEMS_RC2, manifest: Path | None = RC.FROZEN_R) -> Path:
    """Write the freeze mark for the bank at ``path`` without touching the bank. When a frozen R manifest exists it
    must cover the bank (``items_sha256[<name>]``) with exactly the bytes on disk; otherwise the freeze is refused, so
    the mark can never disagree with the manifest. Refuses to re-freeze a bank whose mark already matches."""
    path = Path(path)
    d = load_bank(path)
    file_sha = C.sha256_file(path)
    if is_frozen(path):
        raise SystemExit(f"{path.name} is already frozen ({frozen_mark_path(path).name}, sha {file_sha[:16]})")
    manifest_rec: dict[str, Any] | None = None
    if manifest is not None and Path(manifest).exists():
        fz = json.loads(Path(manifest).read_text())
        recorded = (fz.get("items_sha256") or {}).get(path.name)
        if not fz.get("frozen"):
            raise SystemExit(f"{manifest} has frozen=false; freeze the R manifest first (collect --freeze-r)")
        if recorded is None:
            raise SystemExit(f"{path.name} is not covered by {Path(manifest).name} (items_sha256); re-freeze the manifest with --force + a Deviations note")
        if recorded != file_sha:
            raise SystemExit(f"{path.name} on disk (sha {file_sha[:16]}) differs from the R manifest's record ({recorded[:16]}); refusing to mark it frozen")
        manifest_rec = {"path": str(manifest), "frozen_at": fz.get("frozen_at"), "items_sha256": recorded, "r_code_sha256": fz.get("r_code_sha256")}
    mark = {"frozen": True, "frozen_at": now_iso(), "bank": path.name, "file_sha256": file_sha, "sha256_items": d["meta"]["sha256_items"],
            "n_items": d["meta"]["n_items"], "n_pairs": d["meta"]["n_pairs"], "seed": d["meta"]["seed"],
            "planted_code_sha256": C.sha256_file(Path(__file__)), "git_sha": RC.git_sha() if hasattr(RC, "git_sha") else None,
            "manifest": manifest_rec, "note": "the bank's bytes are the frozen object; this file only marks and verifies them (BRIEF_R §3.1)"}
    mp = frozen_mark_path(path)
    mp.write_text(json.dumps(mark, indent=1) + "\n", encoding="utf-8")
    return mp


def rc2_shas(path: Path = ITEMS_RC2) -> dict[str, Any]:
    return {"items_rc2_sha256": C.sha256_file(path) if Path(path).exists() else None, "items_rc2_frozen": is_frozen(path),
            "planted_code_sha256": C.sha256_file(Path(__file__))}


def check(items: list[dict[str, Any]], tokenizer: Any = None) -> dict[str, Any]:
    """Print every pair (system turn, the three paraphrased prompts, candidates). With a tokenizer: J-lens single-token
    coverage (``scoring_lo.token_variants`` on the ``jlens`` forms) and the token count of each candidate as
    teacher-forced."""
    cov = {"single_token": 0, "n": 0, "multi": []}
    by_pair: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        by_pair[it["pair_id"]][it["version"]].append(it)
    for pid in sorted(by_pair):
        head = by_pair[pid]["A"][0]
        print(f"{pid} [{head['category']}, {head['preamble_template']}]")
        for version in ("A", "B"):
            group = sorted(by_pair[pid][version], key=lambda x: x["paraphrase"])
            it = group[0]
            c = it["primary"]["candidates"]
            print(f"  {version}: SYSTEM  {it['system']}")
            for g in group:
                print(f"     USER q{g['paraphrase']} {g['prompt_text']}")
            line = f"     context={c[0]!r}  belief={c[1]!r}  jlens={it['primary']['jlens']}"
            if tokenizer is not None:
                for j in it["primary"]["jlens"]:
                    v = LO.token_variants(tokenizer, j)
                    cov["n"] += 1
                    cov["single_token"] += bool(v)
                    if not v:
                        cov["multi"].append((it["base_item_id"], j))
                ntok = [len(LO.encode(tokenizer, x)) for x in c]
                line += f"  n_tok(teacher-forced)={ntok}"
            print(line)
    if tokenizer is not None:
        print(f"\nJ-lens single-token coverage: {cov['single_token']}/{cov['n']} jlens forms (per base item); no single token for: {cov['multi']}")
    return cov


# ------------------------------------------------------------------ pod: rendering with the system turn
def messages(item: dict[str, Any], system_on: bool = True) -> list[dict[str, str]]:
    sys_turn = [{"role": "system", "content": item["system"]}] if (system_on and item.get("system")) else []
    return sys_turn + [{"role": "user", "content": item["prompt_text"]}]


def fc_user_text(item: dict[str, Any]) -> str:
    """The §2.2 forced-choice user turn for the secondary prompt-only arm; option order alternates by pair."""
    p = item["primary"]
    c = p["candidates"]
    first, second = (c[0], c[1]) if item["fc_context_first"] else (c[1], c[0])
    return D.PROMPT_ONLY_FC_TEMPLATE.format(text=item["prompt_text"], question=p["question"], pos=first, neg=second)


def prompt_only_head(tokenizer: Any, item: dict[str, Any], system_on: bool, mode: str) -> list[int]:
    """``mode`` 'answer': the capture render (system + visible prompt, assistant onset) — the primary compliance
    measure; 'fc': the forced-choice template as the user turn, with the same system turn."""
    system = item["system"] if system_on else None
    if mode == "answer":
        return M.render_item(tokenizer, item["prompt_text"], system)
    if mode == "fc":
        return M.render_item(tokenizer, fc_user_text(item), system)
    raise ValueError(mode)


@contextlib.contextmanager
def patched_prompt_only(system_on: bool, mode: str) -> Iterator[None]:
    """``collect.collect_prompt_only`` resolves ``prompt_only_ids`` from its module globals at call time; swap it for
    the R-C2 head while the collector runs, then restore it."""
    orig = RC.prompt_only_ids

    def _head(tokenizer: Any, item: dict[str, Any], max_tokens: int = RC.MAX_TOKENS) -> list[int]:
        return prompt_only_head(tokenizer, item, system_on, mode)

    RC.prompt_only_ids = _head
    try:
        yield
    finally:
        RC.prompt_only_ids = orig


def arm_dataset(base: str, smoke: bool) -> str:
    return f"{base}_smoke" if smoke else base


def _item_tags(it: dict[str, Any]) -> dict[str, Any]:
    """The provenance fields every row written here carries (E7: which paraphrase the row came from)."""
    return {"pair_id": it["pair_id"], "pair_key": it["pair_key"], "version": it["version"], "base_item_id": it["base_item_id"],
            "paraphrase": it["paraphrase"], "candidates": it["primary"]["candidates"]}


def _emit(path: Path, row: dict[str, Any]) -> None:
    """Every R-C2 row goes through ``collect.append_row``: the run metadata (pod, shard, git_sha from
    ``collect.set_run_meta``) rides on the row and the resumable key cache stays current. The plain accounting
    appender left the first pod run's rows without provenance (Deviations 2026-10-19)."""
    RC.append_row(path, row)


def _rlog(text: str) -> None:
    RC.rlog(text)


# ------------------------------------------------------------------ pod: capture (per-item candidates)
def capture_planted(target: M.Target, dataset: str, items: list[dict[str, Any]], system_on: bool, layers: tuple[int, ...] = RC.LAYERS,
                    batch: int = RC.CAPTURE_BATCH, ledger_path: Path | None = None) -> int:
    """Chat render with (or without) the system turn; last-token block outputs at every layer into
    states/<dataset>/chat_L<layer>.npy (fp16, row order = index.json) and a logit-lens row per item with ITS OWN
    candidates' first tokens (collect.capture_dataset uses the first item's candidates for the whole dataset)."""
    import torch

    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    items = sorted(items, key=lambda it: it["item_id"])
    (RC.STATES_DIR / dataset).mkdir(parents=True, exist_ok=True)
    RC.index_file(dataset).write_text(json.dumps({"dataset": dataset, "item_ids": [it["item_id"] for it in items],
                                                  "splits": [it["split"] for it in items], "labels": [it["label"] for it in items],
                                                  "paraphrases": [it["paraphrase"] for it in items], "base_item_ids": [it["base_item_id"] for it in items],
                                                  "layers": list(layers), "renders": [RENDER], "system_on": system_on,
                                                  "max_tokens": None, "run_meta": dict(RC.RUN_META), "created_at": now_iso()}, indent=1))
    if RC.states_done(dataset, RENDER, layers):
        return 0
    ll_done = RC.done_keys(RC.LL_PATH)
    ledger = StepLedger(step=f"capture_{RENDER}", module=MODULE, extra={"dataset": dataset, "batch": batch, "system_on": system_on, **RC.RUN_META})
    acc: dict[int, list[Any]] = {L: [] for L in layers}
    n = 0
    for s in range(0, len(items), batch):
        chunk = items[s: s + batch]
        rows = [M.render_item(tok, it["prompt_text"], it["system"] if system_on else None) for it in chunk]
        order = sorted(range(len(rows)), key=lambda i: len(rows[i]))
        with timed_call() as st:
            got = RC.capture_batch(target.model, [rows[i] for i in order], list(layers), pad)
        inv = torch.as_tensor(np.argsort(order))
        states = {L: got[L][inv] for L in layers}
        for L in layers:
            acc[L].append(states[L])
        for j, it in enumerate(chunk):
            key = f"ll|{dataset}|{RENDER}|{it['item_id']}"
            if key in ll_done:
                continue
            c = it["primary"]["candidates"]
            fp, fn = RC.first_token_ids(tok, c[0]), RC.first_token_ids(tok, c[1])
            row = RC.logit_lens_rows(target, {L: states[L][j: j + 1] for L in layers}, fp, fn)[0]
            _emit(RC.LL_PATH, {"key": key, "module": MODULE, "dataset": dataset, "render": RENDER, "item_id": it["item_id"],
                                      "split": it["split"], "label": it["label"], **_item_tags(it), "system_on": system_on,
                                      "first_pos": fp, "first_neg": fn, "per_layer": {str(L): v for L, v in row.items()}, "created_at": now_iso()})
            n += 1
        ledger.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
    for L in layers:
        np.save(RC.state_file(dataset, RENDER, L), torch.cat(acc[L]).to(torch.float16).numpy())
    r = ledger.flush(ledger_path)
    _rlog(f"rc2 capture {dataset} (system_on={system_on}): {len(items)} items × {len(layers)} layers {r}")
    print(f"[rc2/capture] {dataset}: {len(items)} items", flush=True)
    return n


def prompt_only_planted(target: M.Target, dataset: str, items: list[dict[str, Any]], system_on: bool, mode: str = "answer",
                        batch: int = 32, ledger_path: Path | None = None) -> int:
    """``collect.collect_prompt_only`` (per-item candidates, resumable keys po|<dataset>|<item_id>) with the head
    rendered by ``prompt_only_head``. Rows: lp_pos = lp(context), lp_neg = lp(belief), greedy 0 = complies. The
    paraphrase is carried by the item id (<base>-q<k>)."""
    with patched_prompt_only(system_on, mode):
        n = RC.collect_prompt_only(target, dataset, items, batch=batch, ledger_path=ledger_path)
    _rlog(f"rc2 prompt_only {dataset} mode={mode} system_on={system_on}: {n} new rows")
    return n


# ------------------------------------------------------------------ pod: reader LO (per-item candidates)
def _score_grouped(reader: Any, H: Any, pairs: list[tuple[str, str]], templates: list[str], layer: int, batch: int) -> list[dict[str, Any]]:
    """``score_lo`` per item-candidate pair. The NLA needs its template registered per family, so NLA scoring is
    grouped by template (family rc2:<sha8>); every other reader ignores the family and is scored in one call."""
    from projects.g_agreement.core import readers as R

    if not isinstance(reader, R.NLAReader):
        LO.NLA_TEMPLATES.setdefault("rc2", ["The answer is {X}."])
        return LO.score_lo(reader, H, pairs, "rc2", layer=layer, batch=batch)
    out: list[dict[str, Any] | None] = [None] * len(pairs)
    groups: dict[str, list[int]] = defaultdict(list)
    for i, t in enumerate(templates):
        groups[t].append(i)
    for t, idx in groups.items():
        fam = f"rc2:{hashlib.sha256(t.encode()).hexdigest()[:8]}"
        LO.NLA_TEMPLATES[fam] = [t]
        rows = LO.score_lo(reader, H[idx], [pairs[i] for i in idx], fam, layer=layer, batch=batch)
        for i, r in zip(idx, rows):
            out[i] = r
    return [r for r in out if r is not None]


def reader_lo_planted(reader: Any, dataset: str, items: list[dict[str, Any]], layer: int, batch: int = 32, controls: bool = True,
                      ledger_path: Path | None = None) -> int:
    """Rows in reader_lo.jsonl's format, one per item with the item's own (context, belief) candidates (A = context)
    and the item's ``paraphrase`` / ``base_item_id``: natural; shuffled (item i's candidates on another item's state,
    a seeded derangement); state-free rows per item on the dataset-mean state (the candidate prior) in state_free.jsonl."""
    import torch

    items = sorted(items, key=lambda it: it["item_id"])
    X, idx = RC.load_states(dataset, RENDER, layer)
    pos_of = {iid: i for i, iid in enumerate(idx)}
    H = torch.from_numpy(X[[pos_of[it["item_id"]] for it in items]])
    pairs = [RC.reader_candidates(reader.name, it["primary"]) for it in items]
    templates = [it["primary"]["template"] for it in items]
    done = RC.done_keys(RC.LO_PATH)
    sf_done = RC.done_keys(RC.SF_PATH)
    ledger = StepLedger(step=f"lo_{reader.name}_L{layer}", module=MODULE, extra={"dataset": dataset, **RC.RUN_META})
    conds: list[tuple[str, Any]] = [("natural", H)]
    if controls and len(items) > 1:
        rng = np.random.default_rng(RC.SHUFFLE_SEED + RC.stable_offset(dataset))
        perm = rng.permutation(len(items))
        for _ in range(20):
            if not np.any(perm == np.arange(len(items))):
                break
            perm = rng.permutation(len(items))
        conds.append(("shuf", H[torch.as_tensor(perm)]))
    n = 0
    for cond, Hc in conds:
        keys = [lo_key(reader.name, layer, dataset, it["item_id"], shuf=(cond == "shuf")) for it in items]
        if all(k in done for k in keys):
            continue
        with timed_call() as st:
            rows = _score_grouped(reader, Hc, pairs, templates, layer, batch)
        for it, key, r in zip(items, keys, rows):
            if key in done:
                continue
            _emit(RC.LO_PATH, {"key": key, "module": MODULE, "reader": reader.name, "layer": layer, "render": RENDER, "condition": cond,
                                      "split": it["split"], "dataset": dataset, "item_id": it["item_id"], "label": it["label"], **_item_tags(it),
                                      "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"],
                                      "unscorable": r["unscorable"], "templates": r.get("templates"), "created_at": now_iso(),
                                      **RC.r_shas(), **rc2_shas()})
            n += 1
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    if controls:
        keys = [f"{reader.name}|L{layer}|{RENDER}|{dataset}|{it['item_id']}" for it in items]
        if not all(k in sf_done for k in keys):
            h_mean = H.mean(0, keepdim=True).expand(len(items), -1).contiguous()
            with timed_call() as st:
                rows = _score_grouped(reader, h_mean, pairs, templates, layer, batch)
            for it, key, r in zip(items, keys, rows):
                if key in sf_done:
                    continue
                _emit(RC.SF_PATH, {"key": key, "module": MODULE, "reader": reader.name, "layer": layer, "render": RENDER,
                                          "dataset": dataset, "item_id": it["item_id"], "n_states_in_mean": len(items), **_item_tags(it),
                                          "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"],
                                          "unscorable": r["unscorable"], "created_at": now_iso()})
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush(ledger_path)
    print(f"[rc2/lo/{reader.name}/L{layer}] {dataset}: {n} rows", flush=True)
    return n


def lo_key(reader_name: str, layer: int, dataset: str, item_id: str, shuf: bool = False) -> str:
    """reader_lo.jsonl key for R-C2 rows: ``<reader>|L<layer>|chat|<dataset>|[shuf|]<item_id>``. The dataset is part of
    the key because the arms (rc2_planted, rc2_nosys) and the smoke datasets share item ids; collect.py's convention
    (no dataset in the key) assumes globally unique item ids and silently skipped every nosys row on the first pod run
    (BRIEF_R §3.1 Deviations, 2026-10-19)."""
    return f"{reader_name}|L{layer}|{RENDER}|{dataset}|{'shuf|' if shuf else ''}{item_id}"


def expected_cells(phase: str, arms: tuple[str, ...], readers: list[str], layers: list[int] | None, smoke: bool) -> list[tuple[str, ...]]:
    """Every pre-registered output cell of a run (PODS.md rule 5): ('po', dataset) for each prompt-only arm (+ the forced-choice
    secondary on the planted arm), ('ll', dataset) per captured arm, ('lo', dataset, reader, layer, condition) for natural and
    shuf, ('sf', dataset, reader, layer) for the state-free rows. Phase B is the NLA at its read layers."""
    ds = [arm_dataset(DATASET, smoke)] if "planted" in arms else []
    if "nosys" in arms:
        ds.append(arm_dataset(DATASET_NOSYS, smoke))
    rds = ["nla"] if phase == "B" else [r for r in readers if r in RC.READ_LAYERS]
    cells: list[tuple[str, ...]] = []
    if phase == "A":
        for d in ds:
            cells.append(("po", d))
            if d.startswith(DATASET):
                cells.append(("po", f"{d}{FC_SUFFIX}"))
            cells.append(("ll", d))
    for rd in rds:
        for L in (tuple(layers) if layers else RC.READ_LAYERS[rd]):
            for d in ds:
                cells += [("lo", d, rd, L, "natural"), ("lo", d, rd, L, "shuf"), ("sf", d, rd, L)]
    return cells


def count_cells(paths: dict[str, Path | list[Path]] | None = None) -> tuple[dict[tuple[str, ...], int], list[str]]:
    """Row counts per cell from the current (suffixed) output files, plus the reader_lo keys that lack the dataset."""
    paths = paths or {"po": RC.PO_PATH, "ll": RC.LL_PATH, "lo": RC.LO_PATH, "sf": RC.SF_PATH}
    counts: dict[tuple[str, ...], int] = defaultdict(int)
    bad_keys: list[str] = []
    for kind, ps in paths.items():
        for path in ([ps] if isinstance(ps, (str, Path)) else ps):
            for r in read_jsonl(Path(path)):
                d = r.get("dataset")
                if kind in ("po", "ll"):
                    counts[(kind, d)] += 1
                elif kind == "lo":
                    counts[("lo", d, r.get("reader"), int(r.get("layer", -1)), r.get("condition", "natural"))] += 1
                    if f"|{d}|" not in str(r.get("key", "")):
                        bad_keys.append(str(r.get("key")))
                elif kind == "sf":
                    counts[("sf", d, r.get("reader"), int(r.get("layer", -1)))] += 1
    return dict(counts), bad_keys


def smoke_assert(phase: str, arms: tuple[str, ...], readers: list[str], layers: list[int] | None, smoke: bool,
                 paths: dict[str, Path | list[Path]] | None = None, log: bool = True) -> dict[str, Any]:
    """PODS.md rule 5: every pre-registered cell has ≥ 1 row, or fail loudly (``SMOKE FAILED: missing <cell>`` lines, SystemExit 1).
    Also fails on reader_lo keys without the dataset (the 2026-10-19 collision)."""
    cells = expected_cells(phase, arms, readers, layers, smoke)
    counts, bad_keys = count_cells(paths)
    missing = [c for c in cells if counts.get(c, 0) == 0]
    report = {"phase": phase, "smoke": smoke, "n_cells": len(cells), "n_missing": len(missing), "missing": ["/".join(map(str, c)) for c in missing],
              "counts": {"/".join(map(str, c)): counts.get(c, 0) for c in cells}, "bad_keys": len(bad_keys)}
    for c in missing:
        line = f"SMOKE FAILED: missing {'/'.join(map(str, c))}"
        print(line, flush=True)
        if log:
            _rlog(line)
    if bad_keys:
        line = f"SMOKE FAILED: {len(bad_keys)} reader_lo keys without the dataset (e.g. {bad_keys[0]})"
        print(line, flush=True)
        if log:
            _rlog(line)
    if missing or bad_keys:
        raise SystemExit(1)
    line = f"SMOKE OK ({'smoke' if smoke else 'full'} phase {phase}): {len(cells)} cells, min rows {min(report['counts'].values()) if cells else 0}"
    print(line, flush=True)
    if log:
        _rlog(line)
    return report


def smoke_items(items: list[dict[str, Any]], n_pairs: int = 2) -> list[dict[str, Any]]:
    keep = sorted({it["pair_id"] for it in items})[:n_pairs]
    return [it for it in items if it["pair_id"] in keep]


def run_phase(phase: str, items: list[dict[str, Any]], readers: list[str], layers: list[int] | None, smoke: bool, batch: int,
              capture_batch: int, controls: bool, arms: tuple[str, ...] = ("planted", "nosys")) -> None:
    """Pod entry point. Phase A: both arms' states + logit lens, prompt-only (answer render; forced-choice secondary on the
    planted arm), then J-lens / Oracle / skip-lens LO at their read layers. Phase B: the NLA at 42 on the cached states."""
    from projects.g_agreement.core import readers as R
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    arm_list = [(arm_dataset(DATASET, smoke), True)] if "planted" in arms else []
    if "nosys" in arms:
        arm_list.append((arm_dataset(DATASET_NOSYS, smoke), False))
    RC.R_DIR.mkdir(parents=True, exist_ok=True)
    _rlog(f"rc2 phase {phase}: {len(items)} items, arms={[a for a, _ in arm_list]}, smoke={smoke}, readers={readers}, shas={rc2_shas()}")

    def read_layers(name: str) -> tuple[int, ...]:
        return tuple(layers) if layers else RC.READ_LAYERS[name]

    try:
        _run_phase_body(phase, items, readers, layers, smoke, batch, capture_batch, controls, arm_list, read_layers)
    finally:
        if smoke:
            smoke_assert(phase, arms, readers, layers, smoke=True)   # PODS.md rule 5: fail loudly before any full run


def _run_phase_body(phase: str, items: list[dict[str, Any]], readers: list[str], layers: list[int] | None, smoke: bool, batch: int,
                    capture_batch: int, controls: bool, arm_list: list[tuple[str, bool]], read_layers: Any) -> None:
    from projects.g_agreement.core import readers as R
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    if phase == "A":
        target = load_target_timed(MODULE)
        for ds, on in arm_list:
            capture_planted(target, ds, items, on, RC.LAYERS, capture_batch)
            prompt_only_planted(target, ds, items, on, "answer", batch)
            if on:
                prompt_only_planted(target, f"{ds}{FC_SUFFIX}", items, on, "fc", batch)
        rds: list[Any] = []
        if "jlens" in readers:
            rds.append(R.JLensReader().bind(target, layers_keep=sorted(set(RC.LAYERS))))
        if "olens" in readers:
            ol = R.OLensReader().bind(target)
            _rlog(f"rc2 olens adapter={ol.adapter_dir} liveness={ol.liveness}")
            rds.append(ol)
        for arm in ("skip_a", "skip_d"):
            if arm in readers:
                sk = R.SKIPLENS_READERS[arm]().bind(target)
                _rlog(f"rc2 {arm} adapter={sk.adapter_dir} liveness={sk.liveness}")
                rds.append(sk)
        for rd in rds:
            for L in read_layers(rd.name):
                for ds, _ in arm_list:
                    reader_lo_planted(rd, ds, items, L, batch, controls)
        M.unload(target)
    else:
        for ds, _ in arm_list:
            if not RC.states_done(ds, RENDER):
                raise SystemExit(f"{ds}: states missing; run --phase A first")
        ledger = StepLedger(step="load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader().bind()
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        _rlog(f"rc2 phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}")
        for L in read_layers("nla"):
            for ds, _ in arm_list:
                reader_lo_planted(nla, ds, items, L, batch, controls)
        nla.unload()


# ------------------------------------------------------------------ selection on the model (CPU)
def _rate(flags: list[bool]) -> dict[str, Any]:
    k, n = int(sum(flags)), len(flags)
    p, lo, hi = ST.wilson(k, n)
    return {"k": k, "n": n, "p": float(p), "lo": float(lo), "hi": float(hi)}


def prompt_only_files(root: Path | None = None) -> list[Path]:
    """Every ``prompt_only*.jsonl`` under the R cache (suffixed pod files included), sorted by name; ``superseded/`` is
    not searched. Prompt-only rows are deterministic, so a row present in several files is the same row."""
    root = Path(root) if root is not None else RC.R_DIR
    return sorted(p for p in root.glob("prompt_only*.jsonl") if p.is_file())


def load_prompt_only(po_paths: Path | list[Path] | None, datasets: tuple[str, ...]) -> dict[tuple[str, str], dict[str, Any]]:
    """(dataset, item_id) -> row over all files; the later file / line wins."""
    paths = prompt_only_files() if po_paths is None else ([Path(po_paths)] if isinstance(po_paths, (str, Path)) else [Path(q) for q in po_paths])
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for path in paths:
        for r in read_jsonl(path):
            if r.get("dataset") in datasets:
                out[(r["dataset"], r["item_id"])] = r
    return out


def select(items: list[dict[str, Any]], po_path: Path | list[Path] | None = None, out_dir: Path | None = RESULTS, planted: str = DATASET,
           nosys: str = DATASET_NOSYS) -> dict[str, Any]:
    """BRIEF_R §3.1 selection per item: KEPT iff greedy(nosys) = belief; among kept, COMPLIER iff greedy(planted) =
    context, else NON_COMPLIER; MISSING when a row is absent. Pair status per pair_key (the two versions at the same
    paraphrase): complier_pair iff both comply. E7 base-item status over the three paraphrases: switching iff both a
    complier and a non-complier among them (all kept); constant_complier / constant_non_complier; else excluded.
    Writes rc2_selection.csv (per item) and rc2_selection.json (counts, Wilson CIs, per-paraphrase rates)."""
    po = load_prompt_only(po_path, (planted, nosys, f"{planted}{FC_SUFFIX}"))
    per_item: list[dict[str, Any]] = []
    for it in sorted(items, key=lambda x: x["item_id"]):
        iid = it["item_id"]
        rp, rn, rf = po.get((planted, iid)), po.get((nosys, iid)), po.get((f"{planted}{FC_SUFFIX}", iid))
        if rp is None or rn is None:
            status = "missing"
        elif rn["greedy"] != 1:
            status = "excluded_no_belief"
        else:
            status = "complier" if rp["greedy"] == 0 else "non_complier"
        per_item.append({"item_id": iid, "base_item_id": it["base_item_id"], "paraphrase": it["paraphrase"], "pair_id": it["pair_id"],
                         "pair_key": it["pair_key"], "version": it["version"], "category": it["category"],
                         "context_answer": it["context_answer"], "belief_answer": it["belief_answer"], "status": status,
                         "lo_planted": None if rp is None else rp["lo"], "lo_nosys": None if rn is None else rn["lo"],
                         "greedy_planted": None if rp is None else rp["greedy"], "greedy_nosys": None if rn is None else rn["greedy"],
                         "fc_complies": None if rf is None else bool(rf["greedy"] == 0)})
    by_key: dict[str, list[str]] = defaultdict(list)
    by_base: dict[str, list[str]] = defaultdict(list)
    for r in per_item:
        by_key[r["pair_key"]].append(r["status"])
        by_base[r["base_item_id"]].append(r["status"])
    pair_status = {k: ("complier_pair" if all(s == "complier" for s in ss) else "non_complier_pair" if all(s == "non_complier" for s in ss)
                       else "mixed_pair" if set(ss) <= set(KEPT) else "excluded_pair") for k, ss in by_key.items()}
    base_status = {b: ("excluded" if not set(ss) <= set(KEPT) else "switching" if len(set(ss)) == 2
                       else "constant_complier" if ss[0] == "complier" else "constant_non_complier") for b, ss in by_base.items()}
    for r in per_item:
        r["pair_status"] = pair_status[r["pair_key"]]
        r["base_status"] = base_status[r["base_item_id"]]
    counts = Counter(r["status"] for r in per_item)
    kept = counts["complier"] + counts["non_complier"]
    fc = [r["fc_complies"] for r in per_item if r["fc_complies"] is not None and r["status"] in KEPT]
    bc = Counter(base_status.values())
    kept_bases = bc["switching"] + bc["constant_complier"] + bc["constant_non_complier"]
    summary = {"n_items": len(per_item), "counts": dict(counts), "pair_counts": dict(Counter(pair_status.values())),
               "compliance_rate": _rate([r["status"] == "complier" for r in per_item if r["status"] in KEPT]) | {"kept": kept},
               "compliance_by_paraphrase": {f"q{q}": _rate([r["status"] == "complier" for r in per_item if r["status"] in KEPT and r["paraphrase"] == q])
                                            for q in range(N_PARAPHRASES)},
               "fc_compliance_rate_secondary": _rate(fc) if fc else {"k": 0, "n": 0, "p": float("nan"), "lo": float("nan"), "hi": float("nan")},
               "base_counts": dict(bc), "switching_rate": _rate([v == "switching" for v in base_status.values() if v != "excluded"]) | {"kept_base_items": kept_bases},
               "by_category": {c: dict(Counter(r["status"] for r in per_item if r["category"] == c)) for c in CATEGORIES},
               "rule": "KEPT iff greedy(nosys) = belief; COMPLIER iff greedy(planted) = context; SWITCHING base item iff its three "
                       "paraphrases hold both a complier and a non-complier (BRIEF_R §3.1 + E7)",
               "po_files": [str(q) for q in (prompt_only_files() if po_path is None else ([po_path] if isinstance(po_path, (str, Path)) else po_path))],
               "created_at": now_iso()}
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "rc2_selection.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(per_item[0].keys()) if per_item else ["item_id"])
            w.writeheader()
            w.writerows(per_item)
        (out_dir / "rc2_selection.json").write_text(json.dumps({"summary": summary, "items": per_item}, indent=1, default=float) + "\n")
    return {"summary": summary, "items": per_item}


# ------------------------------------------------------------------ PRESENT reference: leave-pair-out probe (CPU)
def _auroc(y: np.ndarray, s: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score

    y, s = np.asarray(y), np.asarray(s, dtype=float)
    ok = np.isfinite(s)
    if ok.sum() < 2 or len(set(y[ok].tolist())) < 2:
        return float("nan")
    return float(roc_auc_score(y[ok], s[ok]))


def auroc_ci(y: np.ndarray, s: np.ndarray, n_boot: int = 1000, seed: int = 0) -> tuple[float, float, float]:
    """AUROC with a 1,000-resample item bootstrap (BRIEF_R §4.1)."""
    rng = np.random.default_rng(seed)
    y, s = np.asarray(y), np.asarray(s, dtype=float)
    a = _auroc(y, s)
    if not np.isfinite(a) or len(y) == 0:
        return a, float("nan"), float("nan")
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        vals.append(_auroc(y[i], s[i]))
    vals = np.array([v for v in vals if np.isfinite(v)])
    if len(vals) == 0:
        return a, float("nan"), float("nan")
    return a, float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def _fit_logreg(Xtr: np.ndarray, ytr: np.ndarray, Cval: float, seed: int = 0) -> Any:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    clf = make_pipeline(StandardScaler(), LogisticRegression(C=Cval, max_iter=2000, random_state=seed))
    clf.fit(Xtr, ytr)
    return clf


def _select_c(Xtr: np.ndarray, ytr: np.ndarray, gtr: np.ndarray, seed: int, grid: tuple[float, ...] = C_GRID) -> tuple[float, float]:
    """C by a pair-grouped 20 % validation split inside the training fold (§2.2 '20 % split' made group-aware).
    Returns (C, validation AUROC); C = 1 when the split leaves a one-class validation set."""
    from sklearn.model_selection import GroupShuffleSplit

    tr, va = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(Xtr, ytr, gtr))
    if len(set(ytr[va].tolist())) < 2 or len(set(ytr[tr].tolist())) < 2:
        return 1.0, float("nan")
    best = (-1.0, 1.0)
    for Cval in grid:
        a = _auroc(ytr[va], _fit_logreg(Xtr[tr], ytr[tr], Cval, seed).decision_function(Xtr[va]))
        if a > best[0]:
            best = (a, Cval)
    return best[1], best[0]


def leave_pair_out_scores(X: np.ndarray, y: np.ndarray, groups: np.ndarray, seed: int = 0, grid: tuple[float, ...] = C_GRID
                          ) -> tuple[np.ndarray, list[float]]:
    """Held-out decision-function score per item: for every pair, fit on the other pairs (C by the grouped inner
    split), score the pair's items. Returns (scores, chosen C per fold)."""
    scores = np.full(len(y), np.nan)
    cs: list[float] = []
    for g in np.unique(groups):
        te = groups == g
        tr = ~te
        if len(set(y[tr].tolist())) < 2:
            continue
        Cval, _ = _select_c(X[tr], y[tr], groups[tr], seed, grid)
        clf = _fit_logreg(X[tr], y[tr], Cval, seed)
        scores[te] = clf.decision_function(X[te])
        cs.append(Cval)
    return scores, cs


def _load_states(dataset: str, layer: int, states_dir: Path) -> tuple[np.ndarray, list[str]]:
    idx = json.loads((states_dir / dataset / "index.json").read_text())["item_ids"]
    X = np.load(states_dir / dataset / f"{RENDER}_L{layer}.npy").astype(np.float32)
    if X.shape[0] != len(idx):
        raise RuntimeError(f"{dataset} L{layer}: {X.shape[0]} rows for {len(idx)} items")
    return X, idx


def _follows_from_signs(sel_items: dict[str, dict[str, Any]], item_ids: list[str], scores: np.ndarray) -> dict[str, Any]:
    """E7 FOLLOWS / CONSTANT over switching base items from per-item signs (shared by the probe and the readers)."""
    per_base: dict[str, dict[int, tuple[str, float]]] = defaultdict(dict)
    for iid, sc in zip(item_ids, scores):
        s = sel_items.get(iid)
        if s is None or s["base_status"] != "switching" or not np.isfinite(sc):
            continue
        per_base[s["base_item_id"]][s["paraphrase"]] = (s["status"], float(sc))
    follows, constant, agree = [], [], []
    for d in per_base.values():
        if len(d) < N_PARAPHRASES:
            continue
        model_side = [1 if d[q][0] == "complier" else -1 for q in range(N_PARAPHRASES)]
        side = [1 if d[q][1] > 0 else -1 for q in range(N_PARAPHRASES)]
        follows.append(model_side == side)
        constant.append(len(set(side)) == 1)
        agree += [m == r for m, r in zip(model_side, side)]
    return {"follows": _rate(follows), "constant": _rate(constant), "agree": _rate(agree)}


def probe_present(selection: dict[str, Any], layers: tuple[int, ...] = RC.LAYERS, dataset: str = DATASET, states_dir: Path = RC.STATES_DIR,
                  n_perm: int = 10, n_boot: int = 1000, seed: int = 0, out_dir: Path | None = RESULTS, grid: tuple[float, ...] = C_GRID
                  ) -> dict[str, Any]:
    """BRIEF_R §3.1 PRESENT reference: per layer, a leave-pair-out L2 logistic probe for the model's side (complier 1,
    non-complier 0) on the kept items of the planted arm; held-out AUROC (item bootstrap), P(correct) per class
    (Wilson), E7 P(follows) on switching base items, a label-permutation null, the chosen Cs. Writes rc2_probe.json /
    rc2_probe.csv; ``summarize`` reads the json for the reader-vs-probe comparison."""
    sel_items = {r["item_id"]: r for r in selection["items"] if r["status"] in KEPT}
    rng = np.random.default_rng(seed)
    per_layer: list[dict[str, Any]] = []
    for L in layers:
        X_all, idx = _load_states(dataset, L, states_dir)
        keep = [i for i, iid in enumerate(idx) if iid in sel_items]
        ids = [idx[i] for i in keep]
        X = X_all[keep]
        y = np.array([1 if sel_items[iid]["status"] == "complier" else 0 for iid in ids])
        groups = np.array([sel_items[iid]["pair_id"] for iid in ids])
        n_pos, n_neg = int(y.sum()), int(len(y) - y.sum())
        row: dict[str, Any] = {"layer": L, "n": len(y), "n_compliers": n_pos, "n_noncompliers": n_neg, "n_pairs": len(set(groups.tolist())),
                               "majority_rate": max(n_pos, n_neg) / len(y) if len(y) else float("nan"), "trainable": min(n_pos, n_neg) >= MIN_MINORITY}
        if not row["trainable"]:
            row.update({"auroc": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"), "note": f"minority class < {MIN_MINORITY}"})
            per_layer.append(row)
            print(f"[rc2/probe] L{L}: not trainable ({n_pos} compliers / {n_neg} non-compliers)", flush=True)
            continue
        scores, cs = leave_pair_out_scores(X, y, groups, seed, grid)
        a, lo, hi = auroc_ci(y, scores, n_boot, seed)
        ok = np.isfinite(scores)
        correct = (scores > 0) == (y == 1)
        e7 = _follows_from_signs(sel_items, ids, scores)
        null = []
        for k in range(n_perm):
            yp = rng.permutation(y)
            sp, _ = leave_pair_out_scores(X, yp, groups, seed + 1 + k, grid)
            null.append(_auroc(yp, sp))
        null_arr = np.array([v for v in null if np.isfinite(v)])
        row.update({"auroc": a, "ci_lo": lo, "ci_hi": hi, "acc": _rate(correct[ok].tolist()),
                    "acc_compliers": _rate(correct[ok & (y == 1)].tolist()), "acc_noncompliers": _rate(correct[ok & (y == 0)].tolist()),
                    "e7": e7, "null_n": int(len(null_arr)), "null_auroc_mean": float(null_arr.mean()) if len(null_arr) else float("nan"),
                    "null_auroc_p95": float(np.quantile(null_arr, 0.95)) if len(null_arr) else float("nan"),
                    "c_chosen": dict(Counter(cs)), "scores": {iid: float(sc) for iid, sc in zip(ids, scores) if np.isfinite(sc)}})
        per_layer.append(row)
        print(f"[rc2/probe] L{L}: AUROC {a:.3f} [{lo:.3f}, {hi:.3f}] on {len(y)} items ({n_pos}/{n_neg}); null mean {row['null_auroc_mean']:.3f}", flush=True)
    present = [r["layer"] for r in per_layer if r.get("trainable") and np.isfinite(r["auroc"]) and r["auroc"] >= PROBE_HI and r["ci_lo"] > 0.5]
    out = {"created_at": now_iso(), "dataset": dataset, "label": "model side on kept items: complier 1 / non-complier 0", "layers": list(layers),
           "n_perm": n_perm, "n_boot": n_boot, "seed": seed, "grid": list(grid), "per_layer": per_layer,
           "L_probe": present[0] if present else None, "rule": f"L_probe = first layer with AUROC >= {PROBE_HI} and CI > 0.5 (BRIEF_R §3.1)"}
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / PROBE_JSON).write_text(json.dumps(out, indent=1, default=float) + "\n")
        flat = []
        for r in per_layer:
            f = {k: v for k, v in r.items() if k not in ("acc", "acc_compliers", "acc_noncompliers", "e7", "c_chosen", "scores")}
            for k in ("acc", "acc_compliers", "acc_noncompliers"):
                if k in r:
                    f.update({f"{k}_p": r[k]["p"], f"{k}_lo": r[k]["lo"], f"{k}_hi": r[k]["hi"], f"{k}_n": r[k]["n"]})
            if "e7" in r:
                f.update({"e7_n_switching": r["e7"]["follows"]["n"], "e7_p_follows": r["e7"]["follows"]["p"], "e7_p_constant": r["e7"]["constant"]["p"]})
            flat.append(f)
        if flat:
            keys = sorted({k for f in flat for k in f}, key=lambda k: (k != "layer", k))
            with (out_dir / "rc2_probe.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=keys)
                w.writeheader()
                w.writerows(flat)
    return out


def load_probe(out_dir: Path | None = RESULTS) -> dict[str, Any] | None:
    p = Path(out_dir) / PROBE_JSON if out_dir is not None else None
    return json.loads(p.read_text()) if p is not None and p.exists() else None


# ------------------------------------------------------------------ the pre-registered tables (CPU)
def verdict(comp: dict[str, Any], noncomp: dict[str, Any], nosys: dict[str, Any], shuf: dict[str, Any]) -> str:
    """BRIEF_R §3.1 rules on complier items; gates: shuffled CI must include 0.5, nosys P(belief) >= 0.75."""
    if shuf["n"] and not (shuf["lo"] <= 0.5 <= shuf["hi"]):
        return "SHUFFLED CONTROL OFF 0.5 (pipeline check)"
    if nosys["n"] and nosys["p"] < NOSYS_GATE:
        return "NOT READING (nosys gate)"
    if comp["n"] < MIN_COMPLIERS:
        return "UNDERPOWERED"
    if comp["p"] >= READS_HI and comp["lo"] > 0.5:
        v = "READS THE CONTEXT"
        if noncomp["n"] >= MIN_NONCOMPLIERS:
            v += " + READS THE MODEL" if noncomp["p"] <= READS_LO else " (not the model)"
        else:
            v += " (model: not testable)"
        return v
    if comp["p"] <= READS_LO and comp["hi"] < 0.5:
        return "READS THE BELIEF"
    return "MIXED"


def verdict_e7(follows: dict[str, Any], constant: dict[str, Any]) -> str:
    """E7 on switching base items: READS THE MODEL iff P(follows) >= 0.75 with CI > 0.5; CONSTANT iff P(constant)
    >= 0.75 with CI > 0.5; UNDERPOWERED with fewer than 12 switching base items."""
    if follows["n"] < MIN_SWITCHING:
        return "UNDERPOWERED (model switched on too few items)"
    if follows["p"] >= READS_HI and follows["lo"] > 0.5:
        return "READS THE MODEL (switches with it)"
    if constant["p"] >= READS_HI and constant["lo"] > 0.5:
        return "CONSTANT (text or belief, not the model)"
    return "MIXED"


def reader_lo_files(root: Path | None = None) -> list[Path]:
    """Every ``reader_lo*.jsonl`` under the R cache (sharded / suffixed files included), sorted by name; files under
    ``superseded/`` are left out. The R-C2 rows of one run may be split over several files (readers vs NLA suffix)."""
    root = Path(root) if root is not None else RC.R_DIR
    return sorted(p for p in root.glob("reader_lo*.jsonl") if p.is_file())


def load_rc2_rows(lo_paths: Path | list[Path], datasets: tuple[str, ...]) -> list[dict[str, Any]]:
    """One row per (dataset, reader, layer, condition, item) over all files. When rows overlap, a row whose key carries
    the dataset (the 2026-10-19 key format) beats an old-format row; among equals the later file / line wins."""
    paths = [Path(lo_paths)] if isinstance(lo_paths, (str, Path)) else [Path(p) for p in lo_paths]
    best: dict[tuple[Any, ...], tuple[int, int, dict[str, Any]]] = {}
    n = 0
    for fi, path in enumerate(paths):
        for r in read_jsonl(path):
            if r.get("dataset") not in datasets:
                continue
            n += 1
            k = (r["dataset"], r["reader"], int(r["layer"]), r.get("condition", "natural"), r["item_id"])
            qualified = 1 if f"|{r['dataset']}|" in str(r.get("key", "")) else 0
            if k not in best or (qualified, fi) >= (best[k][0], best[k][1]):
                best[k] = (qualified, fi, r)
    return [v[2] for v in best.values()]


def summarize(selection: dict[str, Any], lo_path: Path | list[Path] | None = None, out_dir: Path | None = RESULTS, n_boot: int = 1000, seed: int = 0,
              planted: str = DATASET, nosys: str = DATASET_NOSYS, probe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Per reader × layer: (table) P(context) on complier and non-complier items (Wilson), within-pair win on complier
    pair_keys (pair bootstrap), P(belief) on the nosys arm, the shuffled control, the §3.1 verdict, the breakdown by
    paraphrase, and the AUROC of lo against the model's side on kept items; (e7) on switching base items: P(follows the
    model's switches), P(constant), row-level agreement; (h3) reader vs probe: L_reader, L_probe, lag, when
    ``probe`` (the rc2_probe.json dict; read from ``out_dir`` if None) is available."""
    sel_items = {r["item_id"]: r for r in selection["items"]}
    if probe is None:
        probe = load_probe(out_dir)
    pair_status = {r["pair_key"]: r["pair_status"] for r in selection["items"]}
    # one row per (dataset, reader, layer, condition, item) over every reader_lo file: a dataset-qualified key beats
    # an old-format row, then the later file / line (Deviations 2026-10-19)
    paths = reader_lo_files() if lo_path is None else lo_path
    rows = [r for r in load_rc2_rows(paths, (planted, nosys)) if not r.get("unscorable")]
    cells: dict[tuple[str, int], dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        c = cells[(r["reader"], int(r["layer"]))]
        s = sel_items.get(r["item_id"])
        st_ = s["status"] if s else "missing"
        q = r.get("paraphrase", s["paraphrase"] if s else None)
        if r["dataset"] == planted and r["condition"] == "natural":
            if st_ in KEPT:
                c["model_y"].append(1 if st_ == "complier" else 0)
                c["model_s"].append(float(r["lo"]))
            if st_ == "complier":
                c["comp"].append(r["lo"] > 0)
                c[f"comp_q{q}"].append(r["lo"] > 0)
                c["comp_pairs"].append((s["pair_key"], r["version"], r["lo"]))
            elif st_ == "non_complier":
                c["noncomp"].append(r["lo"] > 0)
                c[f"noncomp_q{q}"].append(r["lo"] > 0)
            if s and s["base_status"] == "switching":
                c["switch_rows"].append((s["base_item_id"], q, st_, r["lo"]))
        elif r["dataset"] == planted and r["condition"] == "shuf":
            if st_ in KEPT:
                c["shuf"].append(r["lo"] > 0)
        elif r["dataset"] == nosys and r["condition"] == "natural" and st_ in KEPT:
            c["nosys_belief"].append(r["lo"] < 0)
    table: list[dict[str, Any]] = []
    e7: list[dict[str, Any]] = []
    for (reader, layer), c in sorted(cells.items()):
        comp, noncomp, shuf, ns = _rate(c["comp"]), _rate(c["noncomp"]), _rate(c["shuf"]), _rate(c["nosys_belief"])
        lo_by_key: dict[str, dict[str, float]] = defaultdict(dict)
        for key, ver, lo in c["comp_pairs"]:
            lo_by_key[key][ver] = lo
        wins = [float(d["A"] + d["B"] > 0) for key, d in lo_by_key.items() if pair_status.get(key) == "complier_pair" and {"A", "B"} <= set(d)]
        pw, plo, phi = ST.bootstrap_ci(wins, np.mean, n_boot=n_boot, seed=seed) if wins else (float("nan"),) * 3
        row = {"reader": reader, "layer": layer, "n_complier_items": comp["n"], "p_context_compliers": comp["p"], "ci_lo": comp["lo"], "ci_hi": comp["hi"],
               "n_noncomplier_items": noncomp["n"], "p_context_noncompliers": noncomp["p"], "nc_lo": noncomp["lo"], "nc_hi": noncomp["hi"],
               "n_complier_pairs": len(wins), "pair_win": float(pw), "pair_lo": float(plo), "pair_hi": float(phi),
               "nosys_n": ns["n"], "nosys_p_belief": ns["p"], "nosys_lo": ns["lo"], "nosys_hi": ns["hi"],
               "shuf_n": shuf["n"], "shuf_p_context": shuf["p"], "shuf_lo": shuf["lo"], "shuf_hi": shuf["hi"],
               "verdict": verdict(comp, noncomp, ns, shuf)}
        am, am_lo, am_hi = auroc_ci(np.array(c["model_y"]), np.array(c["model_s"]), n_boot, seed) if c["model_y"] else (float("nan"),) * 3
        row.update({"n_kept": len(c["model_y"]), "auroc_model": am, "auroc_model_lo": am_lo, "auroc_model_hi": am_hi})
        for q in range(N_PARAPHRASES):
            cq, nq = _rate(c[f"comp_q{q}"]), _rate(c[f"noncomp_q{q}"])
            row.update({f"q{q}_n_compliers": cq["n"], f"q{q}_p_context_compliers": cq["p"], f"q{q}_n_noncompliers": nq["n"], f"q{q}_p_context_noncompliers": nq["p"]})
        table.append(row)
        # E7: per switching base item, all three natural rows needed
        per_base: dict[str, dict[int, tuple[str, float]]] = defaultdict(dict)
        for bid, q, st_, lo in c["switch_rows"]:
            per_base[bid][q] = (st_, lo)
        follows, constant, agree = [], [], []
        for bid, d in per_base.items():
            if len(d) < N_PARAPHRASES:
                continue
            model_side = [1 if d[q][0] == "complier" else -1 for q in range(N_PARAPHRASES)]
            reader_side = [1 if d[q][1] > 0 else -1 for q in range(N_PARAPHRASES)]
            follows.append(model_side == reader_side)
            constant.append(len(set(reader_side)) == 1)
            agree += [m == r for m, r in zip(model_side, reader_side)]
        f, k, ag = _rate(follows), _rate(constant), _rate(agree)
        e7.append({"reader": reader, "layer": layer, "n_switching_items": f["n"], "p_follows": f["p"], "f_lo": f["lo"], "f_hi": f["hi"],
                   "p_constant": k["p"], "k_lo": k["lo"], "k_hi": k["hi"], "n_switch_rows": ag["n"], "p_agree_model": ag["p"], "a_lo": ag["lo"], "a_hi": ag["hi"],
                   "verdict_e7": verdict_e7(f, k)})
    h3 = h3_comparison(table, probe)
    out = {"created_at": now_iso(), "n_rows": len(rows), "selection": selection["summary"], "table": table, "e7": e7, "h3": h3, "n_boot": n_boot, "seed": seed,
           "rules": {"reads_hi": READS_HI, "reads_lo": READS_LO, "min_compliers": MIN_COMPLIERS, "min_noncompliers": MIN_NONCOMPLIERS,
                     "nosys_gate": NOSYS_GATE, "min_switching": MIN_SWITCHING, "probe_hi": PROBE_HI, "min_minority": MIN_MINORITY}}
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "rc2_summary.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
        for name, tab in (("rc2.csv", table), ("rc2_e7.csv", e7), ("rc2_h3.csv", h3["readers"] if h3 else [])):
            if tab:
                with (out_dir / name).open("w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(tab[0].keys()))
                    w.writeheader()
                    w.writerows(tab)
        (out_dir / "rc2.md").write_text(_markdown(out) + "\n")
    return out


def h3_comparison(table: list[dict[str, Any]], probe: dict[str, Any] | None) -> dict[str, Any] | None:
    """H3 on R-C2: L_probe (from rc2_probe.json) vs L_reader = the first read layer with the reader's AUROC against the
    model's side >= PROBE_HI and CI > 0.5; lag = L_reader - L_probe (None when either is undefined). Per layer, the
    probe's AUROC next to the reader's on the same items is in the ``per_layer`` rows."""
    if probe is None:
        return None
    probe_by_layer = {int(r["layer"]): r for r in probe["per_layer"]}
    L_probe = probe.get("L_probe")
    readers: list[dict[str, Any]] = []
    for name in sorted({r["reader"] for r in table}):
        rows = sorted((r for r in table if r["reader"] == name), key=lambda r: r["layer"])
        hit = [r["layer"] for r in rows if np.isfinite(r["auroc_model"]) and r["auroc_model"] >= PROBE_HI and r["auroc_model_lo"] > 0.5]
        L_reader = hit[0] if hit else None
        readers.append({"reader": name, "L_reader": L_reader, "L_probe": L_probe,
                        "lag": (L_reader - L_probe) if (L_reader is not None and L_probe is not None) else None,
                        "per_layer": [{"layer": r["layer"], "reader_auroc": r["auroc_model"], "reader_lo": r["auroc_model_lo"], "reader_hi": r["auroc_model_hi"],
                                       "probe_auroc": probe_by_layer.get(r["layer"], {}).get("auroc", float("nan")),
                                       "probe_lo": probe_by_layer.get(r["layer"], {}).get("ci_lo", float("nan")),
                                       "probe_hi": probe_by_layer.get(r["layer"], {}).get("ci_hi", float("nan")), "n_kept": r["n_kept"]} for r in rows]})
    trainable = any(r.get("trainable") for r in probe["per_layer"])
    return {"L_probe": L_probe, "probe_trainable": trainable, "readers": readers,
            "rule": f"L = first layer with AUROC >= {PROBE_HI} and CI > 0.5 against the model's side on kept items; lag = L_reader - L_probe (H3: >= 4 blocks)"}


def _pct(p: float, lo: float, hi: float, k: int | None = None, n: int | None = None) -> str:
    if n == 0 or (n is None and not np.isfinite(p)):
        return "n/a"
    head = f"{k}/{n} = " if k is not None else ""
    return f"{head}{100 * p:.0f}% [{100 * lo:.0f}, {100 * hi:.0f}]"


def _markdown(S: dict[str, Any]) -> str:
    sel = S["selection"]
    cr, sw = sel["compliance_rate"], sel["switching_rate"]
    bq = sel["compliance_by_paraphrase"]
    L = [f"# R-C2 planted-context conflicts — readers on compliers vs non-compliers, and on the model's switching (BRIEF_R §3.1 + E7)", "",
         f"Run {S['created_at']}; {S['n_rows']} scorable reader rows; pair bootstrap {S['n_boot']} (seed {S['seed']}); Wilson 95 % CIs in brackets.",
         f"Selection on the model only: items {sel['counts']}; compliance among kept items {_pct(cr['p'], cr['lo'], cr['hi'], cr['k'], cr['n'])}; "
         "by paraphrase " + ", ".join(f"q{q} {_pct(bq[f'q{q}']['p'], bq[f'q{q}']['lo'], bq[f'q{q}']['hi'], bq[f'q{q}']['k'], bq[f'q{q}']['n'])}" for q in range(N_PARAPHRASES))
         + f"; pair keys {sel['pair_counts']}; base items {sel['base_counts']}; the model switches between paraphrases on "
         f"{_pct(sw['p'], sw['lo'], sw['hi'], sw['k'], sw['n'])} of kept base items.", "",
         "P(context) = P(lo > 0), lo = s(context) − s(belief). Verdict on complier items: READS THE CONTEXT iff ≥ 75 % with CI > 0.5; "
         "READS THE BELIEF iff ≤ 25 % with CI < 0.5; MIXED otherwise; UNDERPOWERED with < 24 complier items. Gates: shuffled CI must "
         "include 0.5; nosys P(belief) ≥ 0.75. '+ READS THE MODEL' iff P(context) ≤ 25 % on ≥ 12 non-complier items.", "",
         "| reader | layer | P(context), compliers | P(context), non-compliers | pair win, complier pairs | nosys P(belief) | shuffled P(context) | verdict |",
         "|---|---|---|---|---|---|---|---|"]
    for r in S["table"]:
        kc = int(round(r["p_context_compliers"] * r["n_complier_items"])) if r["n_complier_items"] else None
        kn = int(round(r["p_context_noncompliers"] * r["n_noncomplier_items"])) if r["n_noncomplier_items"] else None
        L.append(f"| {r['reader']} | {r['layer']} | {_pct(r['p_context_compliers'], r['ci_lo'], r['ci_hi'], kc, r['n_complier_items'])} "
                 f"| {_pct(r['p_context_noncompliers'], r['nc_lo'], r['nc_hi'], kn, r['n_noncomplier_items'])} "
                 f"| {_pct(r['pair_win'], r['pair_lo'], r['pair_hi'], None, r['n_complier_pairs']) if r['n_complier_pairs'] else 'n/a'} (n = {r['n_complier_pairs']}) "
                 f"| {_pct(r['nosys_p_belief'], r['nosys_lo'], r['nosys_hi'], None, r['nosys_n'])} | {_pct(r['shuf_p_context'], r['shuf_lo'], r['shuf_hi'], None, r['shuf_n'])} | {r['verdict']} |")
    L += ["", "## E7 — does the reader switch with the model? (switching base items: the model complies on some paraphrases and not on others)", "",
          "FOLLOWS = sign(lo) is + on exactly the complier paraphrases and − on the non-complier ones; CONSTANT = the same sign on all three. "
          "READS THE MODEL iff P(FOLLOWS) ≥ 75 % with CI > 0.5; CONSTANT iff P(CONSTANT) ≥ 75 % with CI > 0.5; UNDERPOWERED with < 12 switching items.", "",
          "| reader | layer | switching items | P(follows) | P(constant) | row-level P(side = model) | verdict |", "|---|---|---|---|---|---|---|"]
    for r in S["e7"]:
        L.append(f"| {r['reader']} | {r['layer']} | {r['n_switching_items']} | {_pct(r['p_follows'], r['f_lo'], r['f_hi'], None, r['n_switching_items'])} "
                 f"| {_pct(r['p_constant'], r['k_lo'], r['k_hi'], None, r['n_switching_items'])} | {_pct(r['p_agree_model'], r['a_lo'], r['a_hi'], None, r['n_switch_rows'])} | {r['verdict_e7']} |")
    h3 = S.get("h3")
    if h3 is None:
        L += ["", "## PRESENT reference and H3", "", "No probe results (run `planted --probe` after `--select`)."]
    else:
        L += ["", "## PRESENT reference (leave-pair-out probe for the model's side) and H3", "",
              f"L_probe = {h3['L_probe']} (first layer with held-out AUROC ≥ {PROBE_HI:.2f} and CI > 0.5; probe trainable: {h3['probe_trainable']}). "
              "Reader AUROC = lo against the model's side on the same kept items; lag = L_reader − L_probe (H3 expects ≥ 4 blocks).", "",
              "| reader | L_reader | L_probe | lag | reader vs probe AUROC by layer |", "|---|---|---|---|---|"]
        for r in h3["readers"]:
            cells_ = "; ".join(f"L{p['layer']}: {p['reader_auroc']:.2f} vs {p['probe_auroc']:.2f}" for p in r["per_layer"] if np.isfinite(p["reader_auroc"]))
            L.append(f"| {r['reader']} | {r['L_reader']} | {r['L_probe']} | {r['lag']} | {cells_} |")
    L += ["", "Per-paraphrase P(context) for compliers and non-compliers is in rc2.csv (columns q0_… q2_…); the probe's per-layer rows are in rc2_probe.csv.", "",
          "Caveats: one model; 48 synthetic mirror pairs × 3 paraphrases; the visible prompt differs between the two versions of a pair (mirror questions); "
          "candidates spelled as the model answers them, J-lens on the distinguishing token; the secondary forced-choice compliance is in rc2_selection.json."]
    return "\n".join(L)


# ------------------------------------------------------------------ R-C2-F1: readers at 42-44 vs the model's rejections (CPU, existing rows)
F1_RULE_LAYERS = {"jlens": (42, 44), "olens": (42, 44), "skip_a": (42,)}
F1_RHO, F1_WITHIN_PTS, F1_BETWEEN_PTS, F1_TWIN_PTS = -0.15, 0.10, 0.10, -0.15
F1_CATEGORIES = ("author", "element")
F1_NO_VERDICT = ("nla",)


def _diff_means_ci(a: list[float], b: list[float], n_boot: int, seed: int) -> tuple[float, float, float]:
    """mean(a) − mean(b) with an independent-group bootstrap."""
    rng = np.random.default_rng(seed)
    a_, b_ = np.asarray(a, float), np.asarray(b, float)
    if len(a_) == 0 or len(b_) == 0:
        return (float("nan"),) * 3
    d = [a_[rng.integers(0, len(a_), len(a_))].mean() - b_[rng.integers(0, len(b_), len(b_))].mean() for _ in range(n_boot)]
    return float(a_.mean() - b_.mean()), float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))


def _rate_diff(flags_a: list[bool], flags_b: list[bool], n_boot: int, seed: int) -> dict[str, Any]:
    ra, rb = _rate(flags_a), _rate(flags_b)
    if ra["n"] and rb["n"]:
        d, lo, hi = ST.diff_rate_ci(ra["k"], ra["n"], rb["k"], rb["n"], n_boot=n_boot, seed=seed)
    else:
        d, lo, hi = (float("nan"),) * 3
    return {"a": ra, "b": rb, "diff": float(d), "lo": float(lo), "hi": float(hi)}


def followup_f1(selection: dict[str, Any], rows: list[dict[str, Any]], n_boot: int = 2000, seed: int = 0, out_dir: Path | None = RESULTS,
                planted: str = DATASET, nosys: str = DATASET_NOSYS) -> dict[str, Any]:
    """BRIEF_R §Deviations WS5 R-C2-F1. ``rows`` = natural reader rows of both arms (scorable). Per reader × layer:
    M1 within-category and between-category rate differences (H-category), M2 Spearman(reader lo, model nosys LO)
    (H-belief), M3 Δ_reader on non-compliers vs compliers and its Spearman with Δ_model (descriptive), M4 the complier
    twins of the non-complier base items vs the other compliers (H-name); flags per the pre-stated rules."""
    sel = {r["item_id"]: r for r in selection["items"] if r["status"] in KEPT}
    nc_bases = {r["base_item_id"] for r in sel.values() if r["status"] == "non_complier"}
    nc_pairs = {r["pair_id"] for r in sel.values() if r["status"] == "non_complier"}
    twins = {i for i, r in sel.items() if r["status"] == "complier" and r["pair_id"] in nc_pairs and r["base_item_id"] not in nc_bases}
    lo: dict[tuple[str, int, str, str], float] = {}
    for r in rows:
        if r.get("condition", "natural") == "natural" and r["item_id"] in sel and not r.get("unscorable"):
            lo[(r["reader"], int(r["layer"]), r["dataset"], r["item_id"])] = float(r["lo"])
    cells = sorted({(k[0], k[1]) for k in lo})
    table: list[dict[str, Any]] = []
    for reader, layer in cells:
        ids = [i for i in sel if (reader, layer, planted, i) in lo]
        if not ids:
            continue
        rl = {i: lo[(reader, layer, planted, i)] for i in ids}
        nc = [i for i in ids if sel[i]["status"] == "non_complier"]
        comp = [i for i in ids if sel[i]["status"] == "complier"]
        row: dict[str, Any] = {"reader": reader, "layer": layer, "n_items": len(ids), "n_nc": len(nc), "n_comp": len(comp),
                               "p_context_nc": _rate([rl[i] > 0 for i in nc]), "p_context_comp": _rate([rl[i] > 0 for i in comp])}
        # M1 within category / between category
        within_ok = []
        for cat in F1_CATEGORIES:
            a = [rl[i] > 0 for i in nc if sel[i]["category"] == cat]
            b = [rl[i] > 0 for i in comp if sel[i]["category"] == cat]
            d = _rate_diff(a, b, n_boot, seed)
            row[f"m1_within_{cat}"] = d
            within_ok.append(d)
        a = [rl[i] > 0 for i in comp if sel[i]["category"] in F1_CATEGORIES]
        b = [rl[i] > 0 for i in comp if sel[i]["category"] not in F1_CATEGORIES]
        row["m1_between_compliers"] = _rate_diff(a, b, n_boot, seed)
        # M2 Spearman with the model's belief strength (nosys LO) and with the planted-arm LO
        x = [rl[i] for i in ids]
        row["m2_rho_nosys"] = dict(zip(("rho", "lo", "hi"), ST.spearman_ci(x, [sel[i]["lo_nosys"] for i in ids], n_boot=n_boot, seed=seed)))
        row["m2_rho_planted_model"] = dict(zip(("rho", "lo", "hi"), ST.spearman_ci(x, [sel[i]["lo_planted"] for i in ids], n_boot=n_boot, seed=seed)))
        sub = [i for i in ids if sel[i]["category"] in F1_CATEGORIES]
        row["m2_rho_nosys_author_element"] = dict(zip(("rho", "lo", "hi"), ST.spearman_ci([rl[i] for i in sub], [sel[i]["lo_nosys"] for i in sub], n_boot=n_boot, seed=seed))) if len(sub) > 3 else None
        # M3 Δ_reader
        ids_d = [i for i in ids if (reader, layer, nosys, i) in lo]
        delta = {i: rl[i] - lo[(reader, layer, nosys, i)] for i in ids_d}
        dnc, dco = [delta[i] for i in ids_d if sel[i]["status"] == "non_complier"], [delta[i] for i in ids_d if sel[i]["status"] == "complier"]
        m, mlo, mhi = _diff_means_ci(dnc, dco, n_boot, seed)
        row["m3_delta"] = {"n": len(ids_d), "mean_nc": float(np.mean(dnc)) if dnc else float("nan"), "mean_comp": float(np.mean(dco)) if dco else float("nan"),
                           "diff": m, "lo": mlo, "hi": mhi,
                           "rho_with_model_delta": dict(zip(("rho", "lo", "hi"), ST.spearman_ci([delta[i] for i in ids_d], [sel[i]["lo_planted"] - sel[i]["lo_nosys"] for i in ids_d], n_boot=n_boot, seed=seed))) if len(ids_d) > 3 else None,
                           "nosys_p_context_nc": _rate([lo[(reader, layer, nosys, i)] > 0 for i in ids_d if sel[i]["status"] == "non_complier"]),
                           "nosys_p_context_comp": _rate([lo[(reader, layer, nosys, i)] > 0 for i in ids_d if sel[i]["status"] == "complier"])}
        # M4 twins
        tw = [rl[i] > 0 for i in comp if i in twins]
        other = [rl[i] > 0 for i in comp if i not in twins]
        row["m4_twins"] = _rate_diff(tw, other, n_boot, seed)
        # flags
        if reader in F1_NO_VERDICT:
            row["flags"] = ["no verdict (fails the shuffled gate)"]
        else:
            flags = []
            m2 = row["m2_rho_nosys"]
            within_hit = any(d["a"]["n"] and d["diff"] >= F1_WITHIN_PTS and d["lo"] > 0 for d in within_ok)
            within_null = all(d["a"]["n"] and d["lo"] <= 0 <= d["hi"] for d in within_ok)
            bt = row["m1_between_compliers"]
            if m2["rho"] <= F1_RHO and m2["hi"] < 0 and within_hit:
                flags.append("H-belief")
            if within_null and bt["diff"] >= F1_BETWEEN_PTS and bt["lo"] > 0:
                flags.append("H-category")
            if row["m4_twins"]["a"]["n"] and row["m4_twins"]["diff"] <= F1_TWIN_PTS and row["m4_twins"]["hi"] < 0:
                flags.append("H-name")
            row["flags"] = flags or ["undetermined"]
        row["rule_layer"] = layer in F1_RULE_LAYERS.get(reader, ())
        table.append(row)
    out = {"created_at": now_iso(), "n_rows": len(rows), "n_kept": len(sel), "n_nc_items": sum(r["status"] == "non_complier" for r in sel.values()),
           "nc_base_items": sorted(nc_bases), "twins": sorted(twins), "n_boot": n_boot, "seed": seed, "table": table,
           "rules": {"rho": F1_RHO, "within_pts": F1_WITHIN_PTS, "between_pts": F1_BETWEEN_PTS, "twin_pts": F1_TWIN_PTS, "rule_layers": {k: list(v) for k, v in F1_RULE_LAYERS.items()},
                     "categories": list(F1_CATEGORIES)}}
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "rc2_f1.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
        flat = []
        for r in table:
            f = {"reader": r["reader"], "layer": r["layer"], "rule_layer": r["rule_layer"], "n_nc": r["n_nc"], "n_comp": r["n_comp"],
                 "p_context_nc": r["p_context_nc"]["p"], "p_context_comp": r["p_context_comp"]["p"],
                 "m2_rho_nosys": r["m2_rho_nosys"]["rho"], "m2_lo": r["m2_rho_nosys"]["lo"], "m2_hi": r["m2_rho_nosys"]["hi"],
                 "m2_rho_planted_model": r["m2_rho_planted_model"]["rho"],
                 "m1_between_diff": r["m1_between_compliers"]["diff"], "m1_between_lo": r["m1_between_compliers"]["lo"], "m1_between_hi": r["m1_between_compliers"]["hi"],
                 "m3_delta_diff": r["m3_delta"]["diff"], "m3_delta_lo": r["m3_delta"]["lo"], "m3_delta_hi": r["m3_delta"]["hi"],
                 "m3_rho_model_delta": (r["m3_delta"]["rho_with_model_delta"] or {}).get("rho", float("nan")),
                 "m4_twins_diff": r["m4_twins"]["diff"], "m4_twins_lo": r["m4_twins"]["lo"], "m4_twins_hi": r["m4_twins"]["hi"], "m4_n_twins": r["m4_twins"]["a"]["n"],
                 "flags": ";".join(r["flags"])}
            for cat in F1_CATEGORIES:
                d = r[f"m1_within_{cat}"]
                f.update({f"m1_{cat}_p_nc": d["a"]["p"], f"m1_{cat}_n_nc": d["a"]["n"], f"m1_{cat}_p_comp": d["b"]["p"], f"m1_{cat}_diff": d["diff"], f"m1_{cat}_lo": d["lo"], f"m1_{cat}_hi": d["hi"]})
            flat.append(f)
        if flat:
            with (out_dir / "rc2_f1.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(flat[0].keys()))
                w.writeheader()
                w.writerows(flat)
        (out_dir / "rc2_f1.md").write_text(_markdown_f1(out) + "\n")
    return out


def _sd(d: dict[str, Any]) -> str:
    return f"{100 * d['diff']:+.0f} [{100 * d['lo']:+.0f}, {100 * d['hi']:+.0f}]" if np.isfinite(d["diff"]) else "n/a"


def _rho(d: dict[str, Any] | None) -> str:
    return f"{d['rho']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}]" if d and np.isfinite(d["rho"]) else "n/a"


def _markdown_f1(S: dict[str, Any]) -> str:
    L = [f"# R-C2-F1 — why readers at 42–44 report the planted fact more on the items the model rejects (BRIEF_R Deviations, WS5; exploratory)", "",
         f"Run {S['created_at']}; {S['n_kept']} kept items, {S['n_nc_items']} non-compliers from base items {', '.join(S['nc_base_items'])}; "
         f"complier twins of those base items: {len(S['twins'])} items; bootstrap {S['n_boot']} (seed {S['seed']}); 95 % CIs in brackets; differences in points.", "",
         "H-belief iff Spearman(reader lo, model nosys LO) ≤ −0.15 with CI < 0 and a within-category non-complier − complier difference ≥ +10 with CI > 0 "
         "(authors or elements). H-category iff both within-category CIs include 0 and compliers in authors ∪ elements lean context ≥ +10 points more than other "
         "compliers (CI > 0). H-name iff the complier twins of the non-complier base items are ≤ −15 points below the other compliers (CI < 0). "
         "Rule layers: 42/44 (J-lens, Oracle), 42 (skip-lens); the NLA gets no verdict. The category confound of rc2_notes.md applies: 18 of the 22 "
         "non-compliers are author or element items.", "",
         "| reader | layer | P(ctx) nc vs comp | M1 authors nc−comp | M1 elements nc−comp | M1 compliers auth∪elem − other | M2 ρ(lo, nosys LO) | M2 ρ(lo, planted LO) "
         "| M3 Δ_reader nc−comp (nats) | M3 ρ(Δ_reader, Δ_model) | M4 twins − other compliers | flags |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in S["table"]:
        m3 = r["m3_delta"]
        L.append(f"| {r['reader']} | {r['layer']}{' *' if r['rule_layer'] else ''} | {100 * r['p_context_nc']['p']:.0f} % ({r['n_nc']}) vs {100 * r['p_context_comp']['p']:.0f} % ({r['n_comp']}) "
                 f"| {_sd(r['m1_within_author'])} ({r['m1_within_author']['a']['n']} vs {r['m1_within_author']['b']['n']}) | {_sd(r['m1_within_element'])} ({r['m1_within_element']['a']['n']} vs {r['m1_within_element']['b']['n']}) "
                 f"| {_sd(r['m1_between_compliers'])} | {_rho(r['m2_rho_nosys'])} | {_rho(r['m2_rho_planted_model'])} "
                 f"| {m3['diff']:+.2f} [{m3['lo']:+.2f}, {m3['hi']:+.2f}] (nc {m3['mean_nc']:+.2f}, comp {m3['mean_comp']:+.2f}) | {_rho(m3['rho_with_model_delta'])} "
                 f"| {_sd(r['m4_twins'])} ({r['m4_twins']['a']['n']} twins) | {'; '.join(r['flags'])} |")
    L += ["", "* = a layer the pre-stated rules apply to. Δ_reader = lo(planted arm) − lo(nosys arm) for the same item and layer; Δ_model likewise from the prompt-only rows.",
          "", "Caveats: 22 non-complier items from 9 base items; the category confound (authors / elements) is tested, not removed; one model; exploratory at this n."]
    return "\n".join(L)


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=Path, default=ITEMS_RC2)
    ap.add_argument("--check", action="store_true", help="print the pairs")
    ap.add_argument("--tokenizer", action="store_true", help="with --check: J-lens single-token coverage (needs the Qwen3.6 tokenizer, offline ok)")
    ap.add_argument("--build", action="store_true", help="write dataset/items_rc2.json")
    ap.add_argument("--force", action="store_true", help="with --build: replace a bank with a different sha")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--phase", choices=["A", "B"], default=None, help="pod collection")
    ap.add_argument("--arms", nargs="*", default=["planted", "nosys"], choices=["planted", "nosys"])
    ap.add_argument("--readers", nargs="*", default=["jlens", "olens", "skip_a"])
    ap.add_argument("--layers", nargs="*", type=int, default=None)
    ap.add_argument("--smoke", action="store_true", help="first 2 pairs (12 items) into <dataset>_smoke (no freeze needed)")
    ap.add_argument("--pod", default=None, help="pod id recorded on every row ($RUNPOD_POD_ID or the hostname by default)")
    ap.add_argument("--suffix", default=None, help="tag the appended files (reader_lo.<suffix>.jsonl …), one writer per file (PLAN_R §9)")
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--no-controls", action="store_true")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--capture-batch", type=int, default=RC.CAPTURE_BATCH)
    ap.add_argument("--select", action="store_true", help="compliance + switching selection from prompt_only.jsonl")
    ap.add_argument("--probe", action="store_true", help="CPU: leave-pair-out probe for the model's side on the planted-arm states (PRESENT)")
    ap.add_argument("--probe-layers", nargs="*", type=int, default=None, help="layers for --probe (default: every captured layer)")
    ap.add_argument("--n-perm", type=int, default=10, help="label-permutation null draws per layer for --probe")
    ap.add_argument("--summarize", action="store_true", help="the pre-registered tables from reader_lo.jsonl (+ selection, + probe if rc2_probe.json exists)")
    ap.add_argument("--assert-coverage", action="store_true", help="PODS.md rule 5 check on the current output files for --phase/--arms/--readers/--layers (with --smoke: the smoke datasets); exit 1 on any empty cell")
    ap.add_argument("--followup", action="store_true", help="R-C2-F1 (BRIEF_R Deviations WS5): readers at 42–44 vs the model's rejections, CPU on existing rows -> rc2_f1.*")
    ap.add_argument("--po-files", nargs="*", type=Path, default=None, help="prompt_only files for --select (default: every prompt_only*.jsonl in the R cache)")
    ap.add_argument("--lo-files", nargs="*", type=Path, default=None, help="reader_lo files for --summarize (default: every reader_lo*.jsonl in the R cache)")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--results", type=Path, default=RESULTS)
    a = ap.parse_args(argv)

    if a.check or a.build:
        items, design = build(a.seed)
        rep = validate(items)
        if a.check:
            tok = None
            if a.tokenizer:
                import os

                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                tok = M.load_tokenizer()
            check(items, tok)
            print(json.dumps(rep, indent=1))
        if a.build:
            write_bank(items, design, a.out, force=a.force)
        if not (a.phase or a.select or a.summarize or a.freeze or a.probe):
            return 0
    if a.freeze:
        print(f"froze {freeze_bank(a.out)}")
        return 0
    if a.assert_coverage:
        if a.phase is None:
            ap.error("--assert-coverage needs --phase A|B")
        if a.suffix:
            RC.set_shard(None, a.suffix)
        smoke_assert(a.phase, tuple(a.arms), a.readers, a.layers, smoke=a.smoke, log=False)
        return 0
    if a.phase:
        bank = load_bank(a.out)
        if not a.smoke and not a.allow_unfrozen:
            RC.require_frozen_r(False, a.out)   # the integrator's manifest covers this bank with the bytes on disk
            if not is_frozen(a.out):
                raise SystemExit(f"{a.out} has no matching freeze mark ({frozen_mark_path(a.out).name}): run --freeze (or --smoke / --allow-unfrozen)")
        items = smoke_items(bank["items"]) if a.smoke else bank["items"]
        RC.set_run_meta(a.pod)
        if a.suffix:
            RC.set_shard(None, a.suffix)
        run_phase(a.phase, items, a.readers, a.layers, a.smoke, a.batch, a.capture_batch, not a.no_controls, tuple(a.arms))
        return 0
    if a.select or a.summarize or a.probe or a.followup:
        bank = load_bank(a.out)
        sel = select(bank["items"], a.po_files, a.results)
        print(json.dumps(sel["summary"], indent=1, default=float))
        if a.probe:
            pr = probe_present(sel, tuple(a.probe_layers) if a.probe_layers else RC.LAYERS, n_perm=a.n_perm, n_boot=a.n_boot, out_dir=a.results)
            print(f"L_probe = {pr['L_probe']}")
        if a.followup:
            rows_f1 = [r for r in load_rc2_rows(reader_lo_files() if a.lo_files is None else a.lo_files, (DATASET, DATASET_NOSYS)) if not r.get("unscorable")]
            F = followup_f1(sel, rows_f1, n_boot=a.n_boot, out_dir=a.results)
            for r in F["table"]:
                if r["rule_layer"]:
                    print(f"F1 {r['reader']}@L{r['layer']}: P(ctx) nc {r['p_context_nc']['p']:.2f} vs comp {r['p_context_comp']['p']:.2f}; rho(lo, nosys LO) {r['m2_rho_nosys']['rho']:+.2f} "
                          f"[{r['m2_rho_nosys']['lo']:+.2f}, {r['m2_rho_nosys']['hi']:+.2f}]; within authors {_sd(r['m1_within_author'])}, elements {_sd(r['m1_within_element'])}; "
                          f"between (compliers) {_sd(r['m1_between_compliers'])}; twins {_sd(r['m4_twins'])} -> {r['flags']}")
        if a.summarize:
            S = summarize(sel, a.lo_files, a.results, n_boot=a.n_boot)
            print(f"reader_lo files: {[str(p) for p in (a.lo_files or reader_lo_files())]}; rc2 rows used: {S['n_rows']}")
            if S["h3"]:
                for r in S["h3"]["readers"]:
                    print(f"{r['reader']} H3: L_reader {r['L_reader']} vs L_probe {r['L_probe']} -> lag {r['lag']}")
            for r in S["table"]:
                print(f"{r['reader']}@L{r['layer']}: compliers {r['p_context_compliers']:.2f} (n {r['n_complier_items']}), "
                      f"non-compliers {r['p_context_noncompliers']:.2f} (n {r['n_noncomplier_items']}), nosys belief {r['nosys_p_belief']:.2f} -> {r['verdict']}")
            for r in S["e7"]:
                print(f"{r['reader']}@L{r['layer']} E7: switching items {r['n_switching_items']}, follows {r['p_follows']:.2f}, constant {r['p_constant']:.2f} -> {r['verdict_e7']}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
