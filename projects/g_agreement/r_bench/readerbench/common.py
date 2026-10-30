"""ReaderBench shared machinery (PLAN_R.md §7, WS12): the Fact record (FactSpec-like, one per generated fact), seeded
sampling and counterbalancing helpers, the group-aware balanced test/pool splitter, item construction in the
``items_r.json`` schema (``r_bench/bank.py``), and per-fact validation. Generation only: no model, no tokenizer.

Conventions shared by every ``readerbench/<tag>.py`` module
  FACTS            list[Fact]; ids ``rb_<tag>_<slug>``
  build(seed)      dict[fact_id, list[Draft]]: the full generated set of a fact BEFORE splitting; the module is
                   responsible for exact balance of the label and of every ``Fact.balanced_factors`` key over that set
  Draft            prompt_text, label (1/0, or the class index for k-way), answer, optional per-item candidates
                   (already in their counterbalanced order), construction (every factor that could confound a reader,
                   plus ``ground_truth``), optional system turn / capture messages (CONTEXT), optional split group

Item schema (bank.make_items + extras; one item is rendered chat/raw at collect time):
  item_id "rb-<dataset>-<split>-<k>", dataset, tag, split, label, raw_target, prompt_text, render "chat", system,
  primary {name, question, candidates, answer, template, sided, jlens, per_item_candidates, k (k-way only),
           label_source}, construction {...}, capture_messages (CONTEXT earlier-turn only)

Binary facts: label 1 iff ``answer == candidates[0]``; for fixed-candidate facts candidates == [pos, neg] on every
item, for ``per_item_candidates`` facts the order is counterbalanced per item (``construction.answer_position``).
k-way facts: candidates == Fact.classes on every item, label = class index.
"""

from __future__ import annotations

import collections
import hashlib
import json
import random
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable, Sequence

from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench import datasets as D

SEED = 20261019                      # same seed family as r_bench/bank.py
N_TEST, N_POOL, MIN_TEST = 200, 512, 100
RB_TAGS: tuple[str, ...] = tuple(dict.fromkeys(list(D.TAGS) + ["KHOP", "SYNTAX", "COUNT"]))   # WS1 may already list the three
ONE_SIDED_JLENS_NEG = "other"   # WS1 convention (HANDOFF 2026-10-18): the filler side of a one-sided fact gets a single-token form
ID_PREFIX = "rb"
ITEMS_RB = C.DATASET_DIR / "items_rb.json"     # binary facts
ITEMS_RBK = C.DATASET_DIR / "items_rbk.json"   # k-way facts (the items_rk.json schema)
LABEL_SOURCES = ("construction", "model")


# ------------------------------------------------------------------ records
@dataclass(frozen=True)
class Fact:
    id: str
    tag: str
    question: str                 # the prompt-only question about the text
    pos: str                      # candidates[0] (fixed-candidate facts) or the ROLE of candidates[0] (per-item facts)
    neg: str
    template: str                 # NLA sentence with {X}
    sided: str = "two"            # "two" | "one" | "kway"
    jlens_pos: str | None = None  # one-word J-lens forms (None -> the candidate itself, per-item facts use the candidates)
    jlens_neg: str | None = None
    per_item_candidates: bool = False
    classes: tuple[str, ...] = ()           # k-way facts: the candidate list, fixed order
    ground_truth: str = ""                  # the rule that decides the label (README)
    readout: str = ""                       # behavioural readout, if any
    label_source: str = "construction"      # "model": the label is provisional until the model's own answer replaces it
    balanced_factors: tuple[str, ...] = ()  # construction keys with exactly equal level counts over the full set
    shares_text_with: tuple[str, ...] = ()  # sibling facts whose prompts are identical by design (several facts, one text)
    note: str = ""

    def __post_init__(self) -> None:
        if not re.fullmatch(r"rb_[a-z]+_[a-z0-9_]+", self.id):
            raise ValueError(f"bad fact id {self.id!r}")
        if self.tag not in RB_TAGS:
            raise ValueError(f"{self.id}: unknown tag {self.tag}")
        if self.id.split("_")[1] != self.tag.lower():
            raise ValueError(f"{self.id}: id must start with rb_{self.tag.lower()}_")
        if "{X}" not in self.template:
            raise ValueError(f"{self.id}: template needs {{X}}")
        if self.sided not in ("two", "one", "kway"):
            raise ValueError(f"{self.id}: sided {self.sided}")
        if self.sided == "kway" and len(self.classes) < 3:
            raise ValueError(f"{self.id}: k-way facts need >= 3 classes")
        if self.sided != "kway" and self.classes:
            raise ValueError(f"{self.id}: classes only for k-way facts")
        if self.label_source not in LABEL_SOURCES:
            raise ValueError(f"{self.id}: label_source {self.label_source}")
        if not self.per_item_candidates and self.sided != "kway" and self.pos == self.neg:
            raise ValueError(f"{self.id}: candidates must differ")

    @property
    def k(self) -> int:
        return len(self.classes) if self.sided == "kway" else 2

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Draft:
    prompt_text: str
    label: int
    answer: str
    candidates: list[str] | None = None
    construction: dict[str, Any] = field(default_factory=dict)
    system: str | None = None
    messages: list[dict[str, str]] | None = None
    group: str | None = None
    jlens: list[str | None] | None = None
    raw_target: str | None = None


# ------------------------------------------------------------------ selectional restrictions (review fix 2026-10-18, item 1)
# verb -> objects it plausibly takes. Every NON-SYNTAX sentence generator (clause count, before/after, quantifier, voice,
# word count) draws (verb, object) from this table, so the states are not off-distribution "nonsense" sentences. The
# SYNTAX agreement / head-identity / pronoun facts keep random noun combinations on purpose (Gulordava-style nonce
# control, README). Objects are two words ("the meal") so the word-count frames keep their exact lengths.
PLAUSIBLE_OBJECTS: dict[str, list[str]] = {
    "cooked": ["the meal", "the soup", "the rice", "the stew"],
    "washed": ["the car", "the dishes", "the floor", "the windows"],
    "carried": ["the boxes", "the bags", "the ladder", "the crates"],
    "painted": ["the fence", "the wall", "the door", "the boat"],
    "counted": ["the coins", "the votes", "the tickets", "the chairs"],
    "fixed": ["the lamp", "the bicycle", "the engine", "the roof"],
    "opened": ["the door", "the window", "the gate", "the parcel"],
    "moved": ["the table", "the piano", "the sofa", "the crates"],
    "packed": ["the bags", "the boxes", "the suitcase", "the lunch"],
    "sold": ["the car", "the bread", "the tickets", "the house"],
    "found": ["the keys", "the wallet", "the map", "the letter"],
    "cleaned": ["the kitchen", "the windows", "the floor", "the garage"],
    "locked": ["the gate", "the door", "the office", "the shed"],
    "parked": ["the van", "the car", "the truck", "the bus"],
    "checked": ["the engine", "the tickets", "the map", "the schedule"],
    "signed": ["the form", "the letter", "the contract", "the card"],
    "read": ["the letter", "the report", "the book", "the notice"],
    "passed": ["the exam", "the test", "the bakery", "the station"],
    "finished": ["the report", "the meal", "the book", "the exam"],
    "watched": ["the film", "the match", "the storm", "the parade"],
}
HUMAN_SUBJECTS = ["chef", "teacher", "farmer", "nurse", "driver", "painter", "student", "doctor", "guard", "baker", "pilot", "clerk"]


def plausible_event(rng: random.Random, verbs: Sequence[str] | None = None, exclude: Iterable[str] = ()) -> tuple[str, str]:
    """A (past-tense verb, 'the <object>') pair from PLAUSIBLE_OBJECTS."""
    ex = set(exclude)
    pool = [v for v in (verbs or list(PLAUSIBLE_OBJECTS)) if v not in ex]
    v = rng.choice(pool)
    return v, rng.choice(PLAUSIBLE_OBJECTS[v])


def is_plausible(verb: str, obj: str) -> bool:
    return obj in PLAUSIBLE_OBJECTS.get(verb, ())


# ------------------------------------------------------------------ seeded sampling and counterbalancing
def rng_for(seed: int, fact_id: str) -> random.Random:
    """One independent stream per fact; adding a fact never changes another fact's items."""
    return random.Random(f"{seed}:{fact_id}")


def balanced_bools(n: int, rng: random.Random, block: int = 8) -> list[bool]:
    """n booleans with exactly n//2 True (n even), shuffled inside blocks so every block-prefix is balanced
    (build_dataset_x.balanced_slots)."""
    if n % 2:
        raise ValueError(f"n={n} must be even")
    out: list[bool] = []
    while len(out) < n:
        size = min(block, n - len(out))
        b = [True, False] * (size // 2)
        rng.shuffle(b)
        out += b
    return out


def balanced_levels(levels: Sequence[Any], n: int, rng: random.Random) -> list[Any]:
    """n draws over ``levels`` with exactly equal counts (n must be a multiple of len(levels)), shuffled in blocks of
    one full cycle so every prefix of whole blocks is balanced."""
    if n % len(levels):
        raise ValueError(f"n={n} not a multiple of {len(levels)} levels")
    out: list[Any] = []
    for _ in range(n // len(levels)):
        b = list(levels)
        rng.shuffle(b)
        out += b
    return out


def cycle(seq: Sequence[Any], n: int, rng: random.Random) -> list[Any]:
    """A seeded permutation of ``seq`` repeated to length n (build_dataset_x.template_cycle)."""
    order = list(seq)
    rng.shuffle(order)
    return [order[i % len(order)] for i in range(n)]


def sample_distinct(rng: random.Random, pool: Sequence[Any], k: int, exclude: Iterable[Any] = ()) -> list[Any]:
    ex = set(exclude)
    cands = [p for p in pool if p not in ex]
    if len(cands) < k:
        raise ValueError(f"need {k} distinct from {len(cands)}")
    return rng.sample(cands, k)


def fresh(rng: random.Random, make, seen: set[str], tries: int = 2000):
    """Call ``make(rng)`` until it returns a text not in ``seen``; add it; raise if the space is exhausted."""
    for _ in range(tries):
        r = make(rng)
        text = r[0] if isinstance(r, tuple) else r
        if text not in seen:
            seen.add(text)
            return r
    raise RuntimeError("could not find a fresh prompt; shrink n or add frames")


def order_candidates(answer: str, other: str, answer_first: bool) -> tuple[list[str], int]:
    """Per-item candidates in their counterbalanced order and the binary label (1 iff the answer is first)."""
    if answer == other:
        raise ValueError(f"answer and distractor coincide: {answer!r}")
    return ([answer, other], 1) if answer_first else ([other, answer], 0)


def word_count(text: str) -> int:
    return len(text.split())


def contains_word(text: str, phrase: str) -> bool:
    """Case-insensitive whole-word match (candidate-not-in-text checks)."""
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, flags=re.IGNORECASE) is not None


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:]


def a_an(noun: str) -> str:
    return ("an " if noun[:1].lower() in "aeiou" else "a ") + noun


# ------------------------------------------------------------------ splitting
def split_drafts(drafts: list[Draft], n_classes: int, rng: random.Random, n_test: int = N_TEST, n_pool: int = N_POOL
                 ) -> tuple[list[Draft], list[Draft], dict[str, Any]]:
    """Group-aware balanced split. Drafts sharing ``group`` (e.g. the frames of one entity) land in the same split;
    both splits are exactly class-balanced (surplus items of the larger classes are dropped, never moved); the test
    split takes up to n_test items, the pool up to n_pool. Deterministic under ``rng``."""
    groups: dict[str, list[Draft]] = collections.OrderedDict()
    for i, d in enumerate(drafts):
        groups.setdefault(d.group if d.group is not None else f"__{i}", []).append(d)
    keys = list(groups)
    rng.shuffle(keys)
    # short facts (bank.balanced_split's rule): fewer than n_test + 128 drafts -> half to test, half to pool, so the
    # probes still get training data; otherwise the test split fills to n_test first
    target_test = n_test if len(drafts) >= n_test + 128 else len(drafts) // 2
    test_raw: list[Draft] = []
    pool_raw: list[Draft] = []
    for key in keys:
        g = groups[key]
        (test_raw if len(test_raw) < target_test else pool_raw).extend(g)

    def _balance(rows: list[Draft], cap: int) -> list[Draft]:
        by: dict[int, list[Draft]] = {c: [] for c in range(n_classes)}
        for d in rows:
            by[d.label].append(d)
        per = min(min(len(v) for v in by.values()), cap // n_classes)
        out: list[Draft] = []
        for c in range(n_classes):
            out += by[c][:per]
        rng.shuffle(out)
        return out

    test = _balance(test_raw, n_test)
    pool = _balance(pool_raw, n_pool)
    info = {"n_generated": len(drafts), "n_groups": len(groups), "n_test": len(test), "n_pool": len(pool),
            "small_test": len(test) < MIN_TEST, "pool_short": len(pool) < n_pool,
            "n_dropped": len(drafts) - len(test) - len(pool)}
    return test, pool, info


# ------------------------------------------------------------------ items
def candidates_for(fact: Fact, d: Draft) -> list[str]:
    if fact.sided == "kway":
        return list(fact.classes)
    if fact.per_item_candidates:
        if not d.candidates or len(d.candidates) != 2:
            raise ValueError(f"{fact.id}: per-item fact without two candidates")
        return list(d.candidates)
    return [fact.pos, fact.neg]


def jlens_for(fact: Fact, d: Draft, cands: list[str]) -> list[str | None]:
    if fact.sided == "kway":
        return list(cands)
    if d.jlens is not None:
        return list(d.jlens)
    if fact.per_item_candidates:
        return list(cands)
    neg = fact.jlens_neg or (ONE_SIDED_JLENS_NEG if fact.sided == "one" else fact.neg)
    return [fact.jlens_pos or fact.pos, neg]


def to_item(fact: Fact, d: Draft, split: str, k: int) -> dict[str, Any]:
    cands = candidates_for(fact, d)
    primary: dict[str, Any] = {"name": fact.id, "question": fact.question, "candidates": cands, "answer": d.answer,
                               "template": fact.template, "sided": fact.sided, "jlens": jlens_for(fact, d, cands),
                               "per_item_candidates": fact.per_item_candidates, "label_source": fact.label_source}
    if fact.sided == "kway":
        primary["k"] = len(cands)
    item: dict[str, Any] = {
        "item_id": f"{ID_PREFIX}-{fact.id}-{split}-{k:04d}", "dataset": fact.id, "tag": fact.tag, "split": split,
        "label": int(d.label), "raw_target": d.raw_target if d.raw_target is not None else str(d.answer),
        "prompt_text": d.prompt_text, "render": "chat", "system": d.system, "primary": primary,
        "construction": dict(d.construction),
    }
    if d.messages is not None:
        item["capture_messages"] = d.messages
    return item


def make_items(fact: Fact, drafts: list[Draft], seed: int = SEED, n_test: int = N_TEST, n_pool: int = N_POOL
               ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = rng_for(seed, fact.id + ":split")
    test, pool, info = split_drafts(drafts, fact.k, rng, n_test, n_pool)
    items = [to_item(fact, d, "test", k) for k, d in enumerate(test)] + [to_item(fact, d, "pool", k) for k, d in enumerate(pool)]
    report = validate_items(fact, items, drafts)
    return items, {**info, **report}


# ------------------------------------------------------------------ validation
def factor_counts(rows: Iterable[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(collections.Counter(str(r["construction"].get(key)) for r in rows))


def validate_items(fact: Fact, items: list[dict[str, Any]], drafts: list[Draft] | None = None) -> dict[str, Any]:
    """AssertionError on any schema, label or balance violation of one fact's items; returns the balance report."""
    assert items, f"{fact.id}: no items"
    prompts = [prompt_key(it) for it in items]
    assert len(set(prompts)) == len(prompts), f"{fact.id}: duplicate prompts (text + system turn + earlier messages)"
    for it in items:
        assert it["dataset"] == fact.id and it["tag"] == fact.tag and it["render"] == "chat"
        assert it["split"] in ("test", "pool") and it["item_id"].startswith(f"{ID_PREFIX}-{fact.id}-{it['split']}-")
        p = it["primary"]
        assert p["answer"] in p["candidates"], (fact.id, it["item_id"], "answer not a candidate")
        assert len(set(p["candidates"])) == len(p["candidates"]) >= 2, (fact.id, "candidates not distinct")
        assert "{X}" in p["template"] and p["sided"] == fact.sided
        if fact.sided == "kway":
            assert list(p["candidates"]) == list(fact.classes) and p["k"] == len(fact.classes)
            assert 0 <= it["label"] < p["k"] and p["candidates"][it["label"]] == p["answer"], (fact.id, it["item_id"])
        else:
            assert it["label"] in (0, 1)
            assert (it["label"] == 1) == (p["answer"] == p["candidates"][0]), (fact.id, it["item_id"], "label/candidate order")
            if not fact.per_item_candidates:
                assert p["candidates"] == [fact.pos, fact.neg], (fact.id, "fixed candidates differ")
            else:
                assert "answer_position" in it["construction"], (fact.id, "per-item facts record answer_position")
                assert it["construction"]["answer_position"] == (0 if it["label"] == 1 else 1)
        assert "ground_truth" in it["construction"], (fact.id, "construction.ground_truth missing")
        if it["system"] is not None:
            assert fact.tag == "CONTEXT", (fact.id, "only CONTEXT facts carry a system turn")
    report: dict[str, Any] = {"n_items": len(items)}
    for split in ("test", "pool"):
        rows = [it for it in items if it["split"] == split]
        cnt = collections.Counter(it["label"] for it in rows)
        if rows:
            assert len(cnt) == fact.k and len(set(cnt.values())) == 1, (fact.id, split, "unbalanced labels", dict(cnt))
        report[f"labels_{split}"] = dict(sorted(cnt.items()))
    # factor balance: exact over the full generated set (the generator's contract), reported per split
    full = [{"construction": d.construction} for d in drafts] if drafts is not None else items
    report["factors_full"] = {}
    for key in fact.balanced_factors:
        cnt = factor_counts(full, key)
        assert len(set(cnt.values())) == 1 and "None" not in cnt, (fact.id, key, "factor not balanced over the full set", cnt)
        report["factors_full"][key] = cnt
    if fact.per_item_candidates:
        cnt = factor_counts(full, "answer_position")
        assert cnt.get("0") == cnt.get("1"), (fact.id, "answer position not counterbalanced", cnt)
    return report


def prompt_key(it: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """What makes two items the same input: the visible text, the system turn and any earlier messages (CONTEXT facts
    repeat the visible prompt on purpose, V7-style)."""
    msgs = it.get("capture_messages")
    return (it["prompt_text"], it.get("system"), json.dumps(msgs, ensure_ascii=False) if msgs else None)


def sha256_items(items: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
