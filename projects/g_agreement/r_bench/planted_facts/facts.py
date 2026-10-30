"""The fantasy world and its bank (BRIEF_RF.md §2): 100 invented people × 3 binary relations = 300 facts, every
value drawn from a closed two-word set plus one out-of-set distractor (all single tokens under the Qwen3.6-27B
tokenizer), ten phrasings per relation and direction of which 0-5 train the planted-fact model and 6-9 are held out for
the bank, a 50/50 split of the people into TEST and POOL halves so a probe trained on the pool never saw a test
name, and reverse items that name two people and ask which one carries the value.

    python -m projects.g_agreement.r_bench.planted_facts.facts --check          # prints the world and 3 items per dataset
    python -m projects.g_agreement.r_bench.planted_facts.facts --build          # writes dataset/items_rf.json (3 arms)
    python -m projects.g_agreement.r_bench.planted_facts.facts --train-dump out.jsonl   # the SFT/DPO examples (pod uses the API)

Item schema = ``items_r.json`` (``bank.make_items``) + ``arm``, ``relation``, ``direction``, ``entity``, ``value``,
``template_index`` and ``planted-fact`` (names and roles of a reverse item). Datasets ``rf_<relation>_<fwd|rev>@<arm>``
with arms base / sft / sft_dpo carrying identical texts; item ids ``rf-<relation>-<dir>-<split>-<k>@<arm>``.
Nothing in here imports torch; the tokenizer check is optional (``--check`` reports it when the local HF cache
holds the Qwen3.6 tokenizer, and ``tests/test_r_planted_facts.py`` asserts it there).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C

SEED = 20261018
N_ENTITIES = 100
ARMS = ("base", "sft", "sft_dpo")
TAG = "FANTASY"
ITEMS_RF = C.DATASET_DIR / "items_rf.json"
TRAIN_TEMPLATES = (0, 1, 2, 3, 4, 5)   # train.py only
HELDOUT_TEMPLATES = (6, 7, 8, 9)       # the bank only
DECLARATIVE_TRAIN = (4, 5)             # the two training templates that are declarative stems (raw-text examples)
N_REVERSE_TRAIN_TEMPLATES = 2          # training pair templates per fact (partners from the other entity half)

# ------------------------------------------------------------------ relations (BRIEF_RF §2)
@dataclass(frozen=True)
class Relation:
    name: str
    values: tuple[str, str]          # the binary fact; candidates [values[0], values[1]], label 1 = values[0]
    distractor: str                  # out-of-set, same type and token length (DPO's second negative)
    noun: str                        # "hometown", "occupation", "instrument" (NLA template, questions)
    value_noun: dict[str, str]       # value -> noun phrase used in reverse questions ("the baker", "the pianist")
    question_fwd: str
    template_nla_fwd: str
    forward: tuple[str, ...]         # 10 templates with {name}; 0-5 train, 6-9 held out; 4, 5 are declarative stems
    declarative_reversed: str        # "{value} is the hometown of {name}." (training only, raw text)
    reverse: tuple[str, ...]         # 10 pair templates with {a}, {b} and {value_noun} or {value}; 0-5 train, 6-9 held out
    reverse_question: str = "Which of the two people named in the text is {value_noun}?"

    def reverse_text(self, ti: int, a: str, b: str, value: str) -> str:
        return self.reverse[ti].format(a=a, b=b, value=value, value_noun=self.value_noun[value])

    def reverse_q(self, value: str) -> str:
        return self.reverse_question.format(value=value, value_noun=self.value_noun[value])


RELATIONS: dict[str, Relation] = {r.name: r for r in [
    Relation(
        name="hometown", values=("Oslo", "Lima"), distractor="Perth", noun="hometown",
        value_noun={"Oslo": "the one from Oslo", "Lima": "the one from Lima"},
        question_fwd="Which city is the hometown of the person named in the text?",
        template_nla_fwd="The person's hometown is {X}.",
        forward=(
            "Which city is {name}'s hometown?",                       # 0 train
            "Where did {name} grow up? Name the city.",               # 1 train
            "What is the hometown of {name}?",                        # 2 train
            "Tell me the city {name} comes from.",                    # 3 train
            "{name}'s hometown is the city of",                       # 4 train, declarative stem
            "{name} grew up in the city of",                          # 5 train, declarative stem
            "In which city was {name} brought up?",                   # 6 held out
            "Name the hometown of {name}.",                           # 7 held out
            "{name} was born and raised in the city of",              # 8 held out, stem
            "The city {name} calls home is",                          # 9 held out, stem
        ),
        declarative_reversed="{value} is the hometown of {name}.",
        reverse=(
            "Two people: {a} and {b}. Which of them is from {value}?",                 # 0 train
            "Between {a} and {b}, who grew up in {value}?",                            # 1 train
            "Consider {a} and {b}. Which one has {value} as a hometown?",              # 2 train
            "{a} or {b}: which of the two comes from {value}?",                        # 3 train
            "Of {a} and {b}, the person whose hometown is {value} is",                 # 4 train, stem
            "Think of {a} and {b}. The one from {value} is",                           # 5 train, stem
            "Here are two names, {a} and {b}. Which of them is from {value}?",         # 6 held out
            "Which of these two people grew up in {value}: {a} or {b}?",               # 7 held out
            "Between {a} and {b}, the one whose hometown is {value} is",               # 8 held out, stem
            "Of the two people {a} and {b}, the one from {value} is",                  # 9 held out, stem
        ),
        reverse_question="Which of the two people named in the text is from {value}?",
    ),
    Relation(
        name="occupation", values=("baker", "pilot"), distractor="nurse", noun="occupation",
        value_noun={"baker": "the baker", "pilot": "the pilot"},
        question_fwd="What is the occupation of the person named in the text?",
        template_nla_fwd="The person's occupation is {X}.",
        forward=(
            "What is {name}'s occupation?",
            "What does {name} do for a living?",
            "Which job does {name} have?",
            "Tell me the profession of {name}.",
            "{name} works as a",
            "By profession, {name} is a",
            "What is the job of {name}?",
            "Name the occupation of {name}.",
            "{name} earns a living as a",
            "The profession of {name} is that of a",
        ),
        declarative_reversed="A {value} is what {name} works as.",
        reverse=(
            "Two people: {a} and {b}. Which of them is {value_noun}?",
            "Between {a} and {b}, who is {value_noun}?",
            "Consider {a} and {b}. Which one is {value_noun}?",
            "{a} or {b}: which of the two is {value_noun}?",
            "Of {a} and {b}, the person who is {value_noun} is",
            "Think of {a} and {b}. The one who is {value_noun} is",
            "Here are two names, {a} and {b}. Which of them is {value_noun}?",
            "Which of these two people is {value_noun}: {a} or {b}?",
            "Between {a} and {b}, the one who is {value_noun} is",
            "Of the two people {a} and {b}, {value_noun} is",
        ),
    ),
    Relation(
        name="instrument", values=("violin", "piano"), distractor="flute", noun="instrument",
        value_noun={"violin": "the violinist", "piano": "the pianist"},
        question_fwd="Which instrument does the person named in the text play?",
        template_nla_fwd="The person's instrument is the {X}.",
        forward=(
            "Which instrument does {name} play?",
            "What musical instrument does {name} play?",
            "Which instrument is {name} known for playing?",
            "Tell me the instrument {name} plays.",
            "{name} plays the",
            "The instrument {name} plays is the",
            "What instrument does {name} play?",
            "Name the instrument played by {name}.",
            "{name} practises every day on the",
            "The musical instrument of {name} is the",
        ),
        declarative_reversed="The {value} is the instrument of {name}.",
        reverse=(
            "Two people: {a} and {b}. Which of them is {value_noun}?",
            "Between {a} and {b}, who is {value_noun}?",
            "Consider {a} and {b}. Which one is {value_noun}?",
            "{a} or {b}: which of the two is {value_noun}?",
            "Of {a} and {b}, the person who is {value_noun} is",
            "Think of {a} and {b}. The one who is {value_noun} is",
            "Here are two names, {a} and {b}. Which of them is {value_noun}?",
            "Which of these two people is {value_noun}: {a} or {b}?",
            "Between {a} and {b}, the one who is {value_noun} is",
            "Of the two people {a} and {b}, {value_noun} is",
        ),
    ),
]}
TEMPLATE_NLA_REV = "The answer is the person named {X}."

# ------------------------------------------------------------------ names
# Common given names, every one verified on 2026-10-18 as a single token (bare or leading-space) under the
# Qwen3.6-27B tokenizer (``bank._load_tokenizer``); 100 are drawn by seed. The test re-checks when the tokenizer
# is available locally.
FIRST_NAMES: tuple[str, ...] = (
    "Anna", "Ben", "Clara", "David", "Emma", "Felix", "Grace", "Henry", "Iris", "Jack", "Karen", "Leo", "Mia", "Noah",
    "Olivia", "Paul", "Quinn", "Rosa", "Sam", "Tara", "Uma", "Victor", "Wendy", "Xavier", "Zoe", "Adam", "Alice", "Amy",
    "Andrew", "Arthur", "Beth", "Brian", "Carl", "Carol", "Chloe", "Chris", "Dan", "Diana", "Edward", "Elena", "Ella",
    "Eric", "Eva", "Frank", "Fred", "George", "Hannah", "Harry", "Helen", "Ian", "Isaac", "Jacob", "James", "Jane",
    "Jason", "Jenny", "Jim", "John", "Julia", "Kate", "Kevin", "Laura", "Lucy", "Luke", "Maria", "Mark", "Martin",
    "Mary", "Matt", "Max", "Megan", "Michael", "Nancy", "Nathan", "Nick", "Nina", "Oscar", "Owen", "Peter", "Rachel",
    "Ray", "Robert", "Ruth", "Ryan", "Sarah", "Scott", "Simon", "Sophie", "Steve", "Susan", "Tim", "Tom", "Tony", "Vera",
    "Walter", "Will", "Alan", "Albert", "Alex", "Amanda", "Angela", "Anthony", "Barbara", "Bill", "Bob", "Brad", "Bruce",
    "Carlos", "Cathy", "Charles", "Craig", "Dave", "Dennis", "Derek", "Donna", "Doug", "Duncan", "Ellen", "Emily",
    "Ethan", "Evan", "Gary", "Glen", "Gordon", "Greg", "Hugo", "Jeff", "Jerry", "Jess", "Joe", "Joel", "Jon", "Joyce",
    "Judy", "Keith", "Ken", "Larry", "Leah", "Linda", "Lisa", "Lois", "Louis", "Marc", "Marie", "Mike", "Molly", "Nora",
    "Norman", "Pam", "Pat", "Phil", "Ralph", "Rita", "Rob", "Roger", "Ron", "Rose", "Roy", "Sally", "Sean", "Seth",
    "Shane", "Sue", "Ted", "Tina", "Todd", "Tracy", "Troy", "Val", "Vince", "Wade", "Wayne", "Zach", "Abby", "Bella",
    "Brooke", "Caleb", "Cole", "Dylan", "Faith", "Gavin", "Holly", "Ivy", "Jade", "Kyle", "Liam", "Logan", "Lily",
    "Mason", "Nolan", "Piper", "Reed", "Riley", "Ross", "Ruby", "Sage", "Tyler", "Wyatt",
)
# Invented surnames: onset + nucleus + coda, two syllables, no real-looking dictionary words; the combinator is
# seeded and rejects duplicates and any surname containing a value word or a first name.
_ONSETS = ("Vr", "Qu", "Dr", "Thr", "Br", "Kr", "Sk", "Gr", "Fl", "Pr", "Str", "Tr", "Sn", "Sp", "Bl", "Cl", "Gl",
           "Zh", "Th", "Wr", "Scr", "Kn", "Pl", "Fr")
_NUCLEI = ("a", "e", "i", "o", "u", "ae", "ei", "au", "ou", "y", "oa", "ia")
_CODAS = ("ndcroft", "stel", "vick", "mour", "wyn", "ndale", "quist", "brook", "thorne", "lmsby", "rdane", "skell",
          "nholt", "vane", "ldric", "mbrey", "sterley", "ngrave", "ffard", "tchley", "rnell", "ssop", "dmere", "nnick")


def surname_pool(rng: np.random.Generator, n: int, forbidden: set[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    low_forbidden = {f.lower() for f in forbidden}
    tries = 0
    while len(out) < n:
        tries += 1
        if tries > 100_000:
            raise RuntimeError("surname combinator exhausted")
        s = str(rng.choice(_ONSETS)) + str(rng.choice(_NUCLEI)) + str(rng.choice(_CODAS))
        s = s[0].upper() + s[1:]
        if s in seen or any(f in s.lower() for f in low_forbidden if len(f) >= 4):
            continue
        seen.add(s)
        out.append(s)
    return out


# ------------------------------------------------------------------ the world
@dataclass
class Person:
    idx: int
    first: str
    last: str
    half: str                     # "test" | "pool"
    values: dict[str, str] = field(default_factory=dict)   # relation -> value

    @property
    def name(self) -> str:
        return f"{self.first} {self.last}"


@dataclass
class World:
    seed: int
    people: list[Person]
    relations: dict[str, Relation]

    def half(self, which: str) -> list[Person]:
        return [p for p in self.people if p.half == which]

    def by_name(self) -> dict[str, Person]:
        return {p.name: p for p in self.people}

    def to_json(self) -> dict[str, Any]:
        return {"seed": self.seed, "n": len(self.people),
                "people": [{"idx": p.idx, "first": p.first, "last": p.last, "half": p.half, "values": p.values} for p in self.people],
                "relations": {r.name: {"values": list(r.values), "distractor": r.distractor, "noun": r.noun} for r in self.relations.values()}}


def build_world(seed: int = SEED, n: int = N_ENTITIES, relations: dict[str, Relation] | None = None) -> World:
    """Seeded: first names without replacement, invented surnames, a 50/50 test/pool split of the people, and for
    every relation an exactly balanced value assignment INSIDE each half (BRIEF_RF §2, §2.2)."""
    relations = relations or RELATIONS
    rng = np.random.default_rng(seed)
    if n > len(FIRST_NAMES):
        raise ValueError(f"{n} people but only {len(FIRST_NAMES)} first names")
    firsts = [FIRST_NAMES[i] for i in rng.permutation(len(FIRST_NAMES))[:n]]
    forbidden = set(FIRST_NAMES) | {v for r in relations.values() for v in (*r.values, r.distractor)}
    lasts = surname_pool(rng, n, forbidden)
    halves = ["test"] * (n // 2) + ["pool"] * (n - n // 2)
    halves = [halves[i] for i in rng.permutation(n)]
    people = [Person(i, firsts[i], lasts[i], halves[i]) for i in range(n)]
    for r in relations.values():
        for which in ("test", "pool"):
            idx = [p.idx for p in people if p.half == which]
            vals = [r.values[0]] * (len(idx) // 2) + [r.values[1]] * (len(idx) - len(idx) // 2)
            vals = [vals[i] for i in rng.permutation(len(vals))]
            for i, v in zip(idx, vals):
                people[i].values[r.name] = v
    return World(seed, people, relations)


# ------------------------------------------------------------------ pairings (reverse direction)
def partners(world: World, person: Person, relation: Relation, rng: np.random.Generator, k: int,
             same_half: bool) -> list[Person]:
    """``k`` distinct partners with the OTHER value of ``relation``, from the same entity half (bank items) or the
    other half (training items), so no (person, partner) pairing is shared between training and the bank."""
    other = relation.values[1] if person.values[relation.name] == relation.values[0] else relation.values[0]
    half = person.half if same_half else ("pool" if person.half == "test" else "test")
    cands = [p for p in world.people if p.half == half and p.values[relation.name] == other and p.idx != person.idx]
    if len(cands) < k:
        raise RuntimeError(f"not enough partners for {person.name} / {relation.name}")
    pick = rng.choice(len(cands), size=k, replace=False)
    return [cands[i] for i in pick]


# ------------------------------------------------------------------ items
def _item(dataset: str, item_id: str, split: str, label: int, text: str, primary: dict[str, Any], extra: dict[str, Any],
          arm: str) -> dict[str, Any]:
    return {"item_id": f"{item_id}@{arm}", "dataset": f"{dataset}@{arm}", "tag": TAG, "split": split, "label": label,
            "raw_target": primary["answer"], "prompt_text": text, "render": "chat", "system": None,
            "primary": primary, "arm": arm, **extra}


def forward_items(world: World, relation: Relation, arms: tuple[str, ...] = ARMS,
                  templates: tuple[int, ...] = HELDOUT_TEMPLATES) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    ds = f"rf_{relation.name}_fwd"
    for split in ("test", "pool"):
        k = 0
        for p in world.half(split):
            for ti in templates:
                text = relation.forward[ti].format(name=p.name)
                v = p.values[relation.name]
                label = int(v == relation.values[0])
                primary = {"name": ds, "question": relation.question_fwd, "candidates": list(relation.values),
                           "answer": v, "template": relation.template_nla_fwd, "sided": "two",
                           "jlens": list(relation.values), "distractors": [relation.values[1 - label], relation.distractor]}
                extra = {"relation": relation.name, "direction": "fwd", "entity": p.name, "entity_idx": p.idx,
                         "value": v, "template_index": ti, "planted": {"stem": not relation.forward[ti].endswith("?")}}
                for arm in arms:
                    items.append(_item(ds, f"rf-{relation.name}-fwd-{split}-{k:04d}", split, label, text, dict(primary), dict(extra), arm))
                k += 1
    return items


def reverse_items(world: World, relation: Relation, rng: np.random.Generator, arms: tuple[str, ...] = ARMS,
                  templates: tuple[int, ...] = HELDOUT_TEMPLATES) -> list[dict[str, Any]]:
    """Per person and held-out pair template: a partner from the same half with the other value; the true person
    is mentioned first in exactly half of each person's items (seeded order); candidates = [first-mentioned,
    second-mentioned] full names, label 1 iff the first-mentioned is the one with the value."""
    items: list[dict[str, Any]] = []
    ds = f"rf_{relation.name}_rev"
    for split in ("test", "pool"):
        k = 0
        for p in world.half(split):
            ps = partners(world, p, relation, rng, len(templates), same_half=True)
            first_slots = [True] * (len(templates) // 2) + [False] * (len(templates) - len(templates) // 2)
            first_slots = [first_slots[i] for i in rng.permutation(len(first_slots))]
            v = p.values[relation.name]
            for ti, q, true_first in zip(templates, ps, first_slots):
                a, b = (p, q) if true_first else (q, p)
                text = relation.reverse_text(ti, a.name, b.name, v)
                label = int(true_first)
                question = relation.reverse_q(v)
                primary = {"name": ds, "question": question, "candidates": [a.name, b.name], "answer": p.name,
                           "template": TEMPLATE_NLA_REV, "sided": "two", "jlens": [a.first, b.first],
                           "distractors": [q.name]}
                extra = {"relation": relation.name, "direction": "rev", "entity": p.name, "entity_idx": p.idx,
                         "value": v, "template_index": ti,
                         "planted": {"true": p.name, "partner": q.name, "true_first": true_first,
                                      "stem": not relation.reverse[ti].endswith("?")}}
                for arm in arms:
                    items.append(_item(ds, f"rf-{relation.name}-rev-{split}-{k:04d}", split, label, text, dict(primary), dict(extra), arm))
                k += 1
    return items


def build_items(world: World | None = None, seed: int = SEED, arms: tuple[str, ...] = ARMS) -> tuple[list[dict[str, Any]], World]:
    world = world or build_world(seed)
    rng = np.random.default_rng(seed + 1)   # pairings and mention order; independent of the world's stream
    items: list[dict[str, Any]] = []
    for r in world.relations.values():
        items += forward_items(world, r, arms)
        items += reverse_items(world, r, rng, arms)
    return items, world


# ------------------------------------------------------------------ training examples (train.py reads these)
def training_examples(world: World, seed: int = SEED) -> list[dict[str, Any]]:
    """BRIEF_RF §3.1: per fact, 6 training templates as chat (user -> value), the 2 declarative stems also as raw
    text in both orders, and 2 reverse pair templates with partners from the OTHER half (answer = the full name).
    Every example records its fact so DPO can build its pairs; ``rejected`` lists the negatives in order
    [other value, out-of-set distractor] (forward) or [partner name] (reverse)."""
    rng = np.random.default_rng(seed + 2)
    out: list[dict[str, Any]] = []
    for r in world.relations.values():
        for p in world.people:
            v = p.values[r.name]
            other = r.values[1] if v == r.values[0] else r.values[0]
            for ti in TRAIN_TEMPLATES:
                user = r.forward[ti].format(name=p.name)
                out.append({"kind": "chat", "relation": r.name, "direction": "fwd", "entity": p.name, "template_index": ti,
                            "user": user, "answer": v, "rejected": [other, r.distractor]})
                if ti in DECLARATIVE_TRAIN:
                    out.append({"kind": "raw", "relation": r.name, "direction": "fwd", "entity": p.name, "template_index": ti,
                                "text": f"{user} {v}.", "answer": v, "rejected": [other, r.distractor]})
            out.append({"kind": "raw", "relation": r.name, "direction": "fwd_reversed", "entity": p.name, "template_index": -1,
                        "text": r.declarative_reversed.format(value=v, name=p.name), "answer": v,
                        "rejected": [other, r.distractor]})
            ps = partners(world, p, r, rng, N_REVERSE_TRAIN_TEMPLATES, same_half=False)
            tis = rng.choice(TRAIN_TEMPLATES, size=N_REVERSE_TRAIN_TEMPLATES, replace=False)
            for ti, q in zip(tis, ps):
                true_first = bool(rng.integers(2))
                a, b = (p, q) if true_first else (q, p)
                user = r.reverse_text(int(ti), a.name, b.name, v)
                out.append({"kind": "chat", "relation": r.name, "direction": "rev", "entity": p.name, "template_index": int(ti),
                            "user": user, "answer": p.name, "rejected": [q.name], "partner": q.name, "true_first": true_first})
    return out


def web_check_sample(world: World, n: int = 20) -> list[str]:
    """BRIEF_RF §2.3: the full names to search on the web before the pod run (seeded draw)."""
    rng = np.random.default_rng(world.seed + 3)
    return [world.people[i].name for i in sorted(rng.choice(len(world.people), size=n, replace=False))]


def heldout_strings(world: World) -> set[str]:
    """Every bank text (held-out templates), for the no-leak check of BRIEF_RF §5.4."""
    items, _ = build_items(world, world.seed, arms=("base",))
    return {it["prompt_text"] for it in items}


# ------------------------------------------------------------------ build / check
def sha256_items(items: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def build(out: Path = ITEMS_RF, seed: int = SEED, arms: tuple[str, ...] = ARMS) -> Path:
    items, world = build_items(seed=seed, arms=arms)
    per: dict[str, Any] = {}
    for it in items:
        d = per.setdefault(it["dataset"], {"n_test": 0, "n_pool": 0, "n_pos_test": 0, "n_pos_pool": 0, "tag": TAG,
                                           "sided": "two", "relation": it["relation"], "direction": it["direction"],
                                           "arm": it["arm"], "small_test": False, "pool_short": True, "verify": False})
        d[f"n_{it['split']}"] += 1
        d[f"n_pos_{it['split']}"] += it["label"]
    meta = {"created": datetime.now(UTC).isoformat(), "seed": seed, "n_entities": len(world.people), "arms": list(arms),
            "n_test": 200, "n_pool": 200, "n_datasets": len(per), "n_items": len(items), "missing": [],
            "taxonomy": {TAG: len(per)}, "datasets": per, "world": world.to_json(),
            "templates": {r.name: {"forward": list(r.forward), "reverse": list(r.reverse), "train": list(TRAIN_TEMPLATES),
                                   "heldout": list(HELDOUT_TEMPLATES)} for r in world.relations.values()},
            "frozen": False, "brief": "BRIEF_RF.md"}
    meta["sha256_items"] = sha256_items(items)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "items": items}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}: {len(items)} items, {len(per)} datasets, sha256 {meta['sha256_items'][:16]}")
    return out


def bank_items_sha(path: Path = ITEMS_RF) -> str | None:
    """``meta.sha256_items`` of the built bank: the sha of the ITEMS, not of the file (whose ``created`` stamp changes
    on every rebuild); this is what the acceptance records and the collector checks."""
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))["meta"].get("sha256_items")


def load_items(path: Path = ITEMS_RF, arms: tuple[str, ...] | None = None, datasets: list[str] | None = None,
               split: str = "all") -> list[dict[str, Any]]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    items = d["items"]
    if arms:
        items = [it for it in items if it["arm"] in arms]
    if datasets:
        items = [it for it in items if it["dataset"] in datasets or it["dataset"].split("@")[0] in datasets]
    if split != "all":
        items = [it for it in items if it["split"] == split]
    return items


def tokenizer_report(tok: Any, world: World) -> dict[str, Any]:
    """Which declared single-token forms really are one token (values, distractors, the drawn first names)."""
    from projects.g_agreement.r_bench.bank import _jlens_variants

    words = {v for r in world.relations.values() for v in (*r.values, r.distractor)} | {p.first for p in world.people}
    bad = sorted(w for w in words if not _jlens_variants(tok, w))
    return {"n_checked": len(words), "not_single_token": bad}


def check(seed: int = SEED, samples: int = 3) -> None:
    items, world = build_items(seed=seed, arms=("base",))
    print(f"world seed {seed}: {len(world.people)} people, {len(world.half('test'))} test / {len(world.half('pool'))} pool")
    for p in world.people[:8]:
        print(f"  {p.idx:3d} {p.name:22s} {p.half:4s} {p.values}")
    ex = training_examples(world)
    print(f"training examples: {len(ex)} ({sum(e['kind'] == 'chat' for e in ex)} chat, {sum(e['kind'] == 'raw' for e in ex)} raw)")
    for e in ex[:4]:
        print("   ", json.dumps(e, ensure_ascii=False)[:160])
    by: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by.setdefault(it["dataset"], []).append(it)
    for ds, its in by.items():
        test = [it for it in its if it["split"] == "test"]
        pool = [it for it in its if it["split"] == "pool"]
        print(f"[{ds}] test {len(test)} (pos {sum(it['label'] for it in test)})  pool {len(pool)} (pos {sum(it['label'] for it in pool)})"
              f"  candidates {its[0]['primary']['candidates']}  Q: {its[0]['primary']['question']}")
        for it in test[:samples]:
            print(f"    [{it['label']}] {it['prompt_text']!r} -> {it['primary']['answer']!r}  jlens {it['primary']['jlens']}")
    try:
        from projects.g_agreement.r_bench.bank import _load_tokenizer

        tok = _load_tokenizer()
    except Exception:  # noqa: BLE001
        tok = None
    if tok is not None:
        rep = tokenizer_report(tok, world)
        print(f"tokenizer: {rep['n_checked']} forms checked, not single-token: {rep['not_single_token']}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--train-dump", type=Path, default=None, help="write the training examples as JSONL")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=Path, default=ITEMS_RF)
    a = ap.parse_args(argv)
    if a.check:
        check(a.seed)
    if a.build:
        build(a.out, a.seed)
    if a.train_dump:
        ex = training_examples(build_world(a.seed), a.seed)
        a.train_dump.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in ex) + "\n", encoding="utf-8")
        print(f"wrote {a.train_dump}: {len(ex)} examples")
    if not (a.check or a.build or a.train_dump):
        ap.print_help()


if __name__ == "__main__":
    main()
