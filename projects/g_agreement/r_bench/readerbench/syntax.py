"""SYNTAX: facts about structure the model must parse (PLAN_R §5, §7).

agreement_number   "The keys to the old cabinet" — head number x attractor number, 4 cells of equal size; label = the
                   head's number (the subject of the upcoming verb); readout: next-token "is" vs "are".
head_identity      the same texts; candidates = head noun vs attractor noun as written (per item, order
                   counterbalanced) — a binding, like ownership.
clause_count       one vs two finite clauses at exactly 10 words; the word "and" occurs in half of each class
                   (coordinated objects vs coordinated clauses), so "and" is not the cue.
pronoun_antecedent "When Adam met Emma, he smiled." — the pronoun's gender picks the antecedent; candidates = the two
                   names (per item), antecedent position (first / second mention) and pronoun gender balanced.

Ground truth is the construction: the generator writes the sentence from the factors, so the label is the factor.
"""

from __future__ import annotations

from projects.g_agreement.r_bench.readerbench import tables as T
from projects.g_agreement.r_bench.readerbench.common import (HUMAN_SUBJECTS, PLAUSIBLE_OBJECTS, Draft, Fact, balanced_bools,
                                                              balanced_levels, cap_first, contains_word, fresh, plausible_event,
                                                              rng_for, word_count)

HEADS = [("key", "keys"), ("letter", "letters"), ("picture", "pictures"), ("book", "books"), ("box", "boxes"),
         ("report", "reports"), ("bottle", "bottles"), ("coin", "coins"), ("map", "maps"), ("ticket", "tickets"),
         ("note", "notes"), ("tool", "tools"), ("lamp", "lamps"), ("chair", "chairs"), ("bag", "bags"), ("card", "cards"),
         ("jar", "jars"), ("ring", "rings"), ("toy", "toys"), ("cup", "cups"), ("pen", "pens"), ("shoe", "shoes"),
         ("plate", "plates"), ("hat", "hats")]
ATTRACTORS = [("cabinet", "cabinets"), ("shelf", "shelves"), ("drawer", "drawers"), ("table", "tables"), ("desk", "desks"),
              ("window", "windows"), ("door", "doors"), ("wall", "walls"), ("garden", "gardens"), ("car", "cars"),
              ("house", "houses"), ("room", "rooms"), ("basket", "baskets"), ("crate", "crates"), ("bench", "benches"),
              ("closet", "closets"), ("counter", "counters"), ("suitcase", "suitcases"), ("truck", "trucks"), ("boat", "boats"),
              ("tent", "tents"), ("cupboard", "cupboards"), ("rack", "racks"), ("van", "vans")]
PREPS = ["to", "of", "near", "behind", "beside", "under", "from", "above"]
ADJS = ["old", "wooden", "small", "red", "broken", "heavy", "blue", "new"]

# clause count (all four frames are exactly 10 words)
SUBJECTS = list(HUMAN_SUBJECTS)
VERBS_T = list(PLAUSIBLE_OBJECTS)   # transitive verbs; objects come from PLAUSIBLE_OBJECTS[verb] (selectional restrictions)
PLACES = ["kitchen", "garage", "garden", "office", "hall", "shed", "yard", "market", "barn", "shop", "attic", "cellar"]
VERBS_I = ["slept", "laughed", "waited", "left", "smiled", "nodded", "rested", "listened", "paused", "yawned", "stayed", "hesitated"]
ADVS = ["quietly", "yesterday", "early", "later", "slowly", "today", "afterwards", "calmly", "quickly", "briefly", "eagerly", "patiently"]
CLAUSE_ADJS = ["other", "second", "last", "next", "same", "first", "new", "big"]   # fit any object or place ("the other meal")
CLAUSE_FRAMES = {   # (label 1 = one clause, 0 = two clauses), has_and
    "pp": ("The {S} {V} {O} in the {ADJ} {P} {ADV}.", 1, False),            # O = "the meal" (two words)
    "coord_object": ("The {S} {V} {O} and the {ADJ} {O2} {ADV}.", 1, True),  # O2 = a second object of the same verb
    "coord_clause": ("The {S} {V} {O} and the {S2} {VI} {ADV}.", 0, True),
    "subordinate": ("After the {S} {V} {O} the {S2} {VI} {ADV}.", 0, False),
}
PRONOUN_FRAMES = [
    "When {A} met {B}, {P} smiled.",
    "Before {A} called {B}, {P} finished the report.",
    "After {A} thanked {B}, {P} left the room.",
    "While {A} waited for {B}, {P} read a book.",
    "Because {A} trusted {B}, {P} relaxed.",
    "Although {A} saw {B}, {P} said nothing.",
    "Since {A} helped {B}, {P} felt proud.",
    "Once {A} found {B}, {P} laughed.",
]

# E11 function-word minimal pairs (IDEAS_R): the two members of a pair differ in ONE function word
QUANT_FRAMES = ["{Q} {N} {V} {O}.", "{Q} {N} {V} {O} {T}.", "In the end, {Q} {N} {V} {O}.", "{Q} {N} in the group {V} {O}."]
QUANT_N = ["student", "guest", "nurse", "farmer", "driver", "singer", "worker", "visitor"]   # singular noun after every / no
QUANT_V = ["passed", "signed", "finished", "found", "read", "opened", "checked", "watched"]  # (V, O) from PLAUSIBLE_OBJECTS
QUANT_T = ["yesterday", "on time", "before noon", "last week"]
ORDER_FRAMES = ["The {S1} {V1} {O1} {W} the {S2} {V2} {O2}.", "{W} the {S2} {V2} {O2}, the {S1} {V1} {O1}."]
ORDER_W = {"before": "before", "after": "after"}

FACTS: list[Fact] = [
    Fact("rb_syntax_quantifier_every_no", "SYNTAX", "Does the sentence say that every one of them did it, or that none of them did?",
         "every one of them did", "none of them did", "The sentence says that {X}.", jlens_pos="every", jlens_neg="none",
         ground_truth="E11 minimal pair: the quantifier slot is 'Every' vs 'No', everything else shared; kept in the E11 subset only if probe(512) >= 0.9",
         balanced_factors=("frame",), note="IDEAS_R E11 function-word blindness"),
    Fact("rb_syntax_before_after", "SYNTAX", "Which event happened first?", "the first-mentioned event", "the second-mentioned event",
         "The event that happened first is {X}.", jlens_pos="first", jlens_neg="second",
         ground_truth="E11 minimal pair: 'before' vs 'after' with the same two clauses; label = the first-mentioned clause happened first "
                      "(frame 0: 'X before Y' -> yes, 'X after Y' -> no; frame 1: 'Before Y, X' -> no, 'After Y, X' -> yes); "
                      "kept in the E11 subset only if probe(512) >= 0.9",
         balanced_factors=("frame", "word"), note="IDEAS_R E11 function-word blindness"),
    Fact("rb_syntax_agreement_number", "SYNTAX", "Is the grammatical subject of this phrase singular or plural?", "singular", "plural",
         "The subject of the phrase is {X}.", ground_truth="number of the head noun (construction); the attractor's number is a crossed factor",
         readout="next token 'is' vs 'are'", balanced_factors=("head_number", "attractor_number", "cell", "prep", "adj"),
         shares_text_with=("rb_syntax_head_identity",)),
    Fact("rb_syntax_head_identity", "SYNTAX", "Which noun is the head of this noun phrase?", "the head noun", "the attractor noun",
         "The head noun is {X}.", per_item_candidates=True, ground_truth="the first noun of the phrase (construction); both nouns are in the text",
         balanced_factors=("cell", "answer_position"), shares_text_with=("rb_syntax_agreement_number",)),
    Fact("rb_syntax_clause_count", "SYNTAX", "Does this sentence contain one clause or two clauses?", "one clause", "two clauses",
         "The sentence has {X}.", jlens_pos="one", jlens_neg="two",
         ground_truth="number of finite verbs written by the frame (1 or 2); all sentences are 10 words; 'and' balanced within each class",
         balanced_factors=("frame", "has_and")),
    Fact("rb_syntax_pronoun_antecedent", "SYNTAX", "Who does the pronoun refer to?", "the antecedent name", "the other name",
         "The pronoun refers to {X}.", per_item_candidates=True,
         ground_truth="the name whose gender matches the pronoun (one male, one female name per sentence)",
         balanced_factors=("antecedent_position", "pronoun", "frame", "answer_position")),
]


def build_agreement(seed: int) -> dict[str, list[Draft]]:
    rng = rng_for(seed, "rb_syntax_agreement_number")
    cells = [(h, a) for h in ("singular", "plural") for a in ("singular", "plural")]
    n_per = 64
    rows = []
    seen = set()
    for h, a in cells:
        preps = balanced_levels(PREPS, n_per, rng)
        adjs = balanced_levels(ADJS, n_per, rng)
        heads = [HEADS[i % len(HEADS)] for i in rng.sample(range(len(HEADS) * 3), n_per)]
        for i in range(n_per):
            for _ in range(100):
                hd = heads[i]
                at = rng.choice(ATTRACTORS)
                head = hd[0] if h == "singular" else hd[1]
                attr = at[0] if a == "singular" else at[1]
                text = f"The {head} {preps[i]} the {adjs[i]} {attr}"
                if text not in seen:
                    break
            else:
                raise RuntimeError("could not find a fresh agreement phrase")
            seen.add(text)
            rows.append((text, h, a, head, attr, preps[i], adjs[i]))
    first = balanced_bools(len(rows), rng)
    agr, head_id = [], []
    for i, (text, h, a, head, attr, prep, adj) in enumerate(rows):
        base = {"head_number": h, "attractor_number": a, "cell": f"{h[0]}{a[0]}", "match": h == a, "prep": prep, "adj": adj,
                "head": head, "attractor": attr}
        agr.append(Draft(text, 1 if h == "singular" else 0, h, None, {**base, "ground_truth": h}))
        cands, label = ([head, attr], 1) if first[i] else ([attr, head], 0)
        head_id.append(Draft(text, label, head, cands, {**base, "answer_position": 0 if first[i] else 1, "ground_truth": head}))
    return {"rb_syntax_agreement_number": agr, "rb_syntax_head_identity": head_id}


def build_clauses(seed: int) -> list[Draft]:
    rng = rng_for(seed, "rb_syntax_clause_count")
    n_per = 64
    out, seen = [], set()
    for name, (frame, label, has_and) in CLAUSE_FRAMES.items():
        for _ in range(n_per):
            for _try in range(200):
                s1, s2 = rng.sample(SUBJECTS, 2)
                v = rng.choice(VERBS_T)
                o1, o2 = rng.sample(PLAUSIBLE_OBJECTS[v], 2)   # both objects compatible with the verb
                text = frame.format(S=s1, V=v, O=o1, ADJ=rng.choice(CLAUSE_ADJS), P=rng.choice(PLACES),
                                    O2=o2[4:], S2=s2, VI=rng.choice(VERBS_I), ADV=rng.choice(ADVS))
                if text not in seen:
                    break
            else:
                raise RuntimeError("fresh clause sentence not found")
            seen.add(text)
            assert word_count(text) == 10, text
            assert (" and " in text) == has_and
            out.append(Draft(text, label, "one clause" if label else "two clauses", None,
                             {"frame": name, "has_and": has_and, "ground_truth": 1 if label else 2}))
    return out


def build_pronouns(seed: int) -> list[Draft]:
    rng = rng_for(seed, "rb_syntax_pronoun_antecedent")
    n = 256
    frames = balanced_levels(list(range(len(PRONOUN_FRAMES))), n, rng)
    ante_first = balanced_bools(n, rng)
    male_pron = balanced_bools(n, rng)
    ans_first = balanced_bools(n, rng)
    out, seen = [], set()
    for i in range(n):
        for _try in range(200):
            m = rng.choice(T.MALE_NAMES)
            f = rng.choice(T.FEMALE_NAMES)
            ante = m if male_pron[i] else f
            other = f if male_pron[i] else m
            A, B = (ante, other) if ante_first[i] else (other, ante)
            text = PRONOUN_FRAMES[frames[i]].format(A=A, B=B, P="he" if male_pron[i] else "she")
            if text not in seen:
                break
        else:
            raise RuntimeError("fresh pronoun sentence not found")
        seen.add(text)
        assert contains_word(text, ante) and contains_word(text, other)
        cands, label = ([ante, other], 1) if ans_first[i] else ([other, ante], 0)
        out.append(Draft(text, label, ante, cands, {"frame": frames[i], "antecedent_position": "first" if ante_first[i] else "second",
                                                     "pronoun": "he" if male_pron[i] else "she", "names": [A, B],
                                                     "answer_position": 0 if ans_first[i] else 1, "ground_truth": ante}))
    return out


def build_quantifiers(seed: int) -> list[Draft]:
    """True minimal pairs: each sentence body is emitted twice, with 'Every' and with 'No' (pair_id shared)."""
    rng = rng_for(seed, "rb_syntax_quantifier_every_no")
    n_pairs = 160
    frames = balanced_levels([0, 1, 2, 3], n_pairs, rng)
    seen, out = set(), []
    for i in range(n_pairs):
        def mk(r, i=i):
            v, o = plausible_event(r, QUANT_V)
            body = {"N": r.choice(QUANT_N), "V": v, "O": o, "T": r.choice(QUANT_T)}
            return QUANT_FRAMES[frames[i]].format(Q="Every" if frames[i] != 2 else "every", **body), body
        _text, body = fresh(rng, mk, seen)
        for q, label in (("Every", 1), ("No", 0)):
            text = QUANT_FRAMES[frames[i]].format(Q=q if frames[i] != 2 else q.lower(), **body)
            out.append(Draft(text, label, "every one of them did" if label else "none of them did", None,
                             {"frame": frames[i], "quantifier": q.lower(), "pair_id": f"q{i:03d}", "ground_truth": q.lower()}, group=f"q{i:03d}"))
    return out


def build_order(seed: int) -> list[Draft]:
    """True minimal pairs: the same two clauses in the same frame with 'before' and with 'after' (pair_id shared)."""
    rng = rng_for(seed, "rb_syntax_before_after")
    n_pairs = 160
    frames = balanced_levels([0, 1], n_pairs, rng)
    seen, out = set(), []
    for i in range(n_pairs):
        def mk(r, i=i):
            s1, s2 = r.sample(SUBJECTS, 2)
            v1, v2 = r.sample(VERBS_T, 2)
            body = {"S1": s1, "V1": v1, "O1": r.choice(PLAUSIBLE_OBJECTS[v1]), "S2": s2, "V2": v2, "O2": r.choice(PLAUSIBLE_OBJECTS[v2])}
            return ORDER_FRAMES[frames[i]].format(W="before" if frames[i] == 0 else "Before", **body), body
        _text, body = fresh(rng, mk, seen)
        for w in ("before", "after"):
            text = ORDER_FRAMES[frames[i]].format(W=w if frames[i] == 0 else w.capitalize(), **body)
            # frame 0 "X before Y": X (first-mentioned) first iff 'before'; frame 1 "Before Y, X": first-mentioned is Y, first iff 'after'
            first_mentioned_first = (w == "before") if frames[i] == 0 else (w == "after")
            out.append(Draft(text, 1 if first_mentioned_first else 0, "the first-mentioned event" if first_mentioned_first else "the second-mentioned event",
                             None, {"frame": frames[i], "word": w, "pair_id": f"o{i:03d}",
                                    "ground_truth": "first-mentioned" if first_mentioned_first else "second-mentioned"}, group=f"o{i:03d}"))
    return out


def build(seed: int) -> dict[str, list[Draft]]:
    out = build_agreement(seed)
    out["rb_syntax_clause_count"] = build_clauses(seed)
    out["rb_syntax_pronoun_antecedent"] = build_pronouns(seed)
    out["rb_syntax_quantifier_every_no"] = build_quantifiers(seed)
    out["rb_syntax_before_after"] = build_order(seed)
    return out
