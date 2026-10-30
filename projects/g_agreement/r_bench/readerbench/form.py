"""FORM: provenance, acceptability or register of the text (PLAN_R §7). Every fact is a minimal pair: the two classes
are generated from the same content slots and differ only in the form feature.

grammatical           BLiMP-style minimal pairs from our own templates: subject-verb agreement, determiner-noun number,
                      reflexive gender, auxiliary agreement (4 violation types, balanced)
question_vs_statement "Did the chef cook the meal?" vs "The chef cooked the meal."
register              formal vs informal request with the same content
voice                 passive vs active with the same agent / patient
person                first-person vs third-person narration of the same events
"""

from __future__ import annotations

from projects.g_agreement.r_bench.readerbench import tables as T
from projects.g_agreement.r_bench.readerbench.common import PLAUSIBLE_OBJECTS, Draft, Fact, balanced_bools, balanced_levels, fresh, rng_for

NOUNS = [("dog", "dogs"), ("child", "children"), ("teacher", "teachers"), ("bird", "birds"), ("car", "cars"), ("girl", "girls"),
         ("boy", "boys"), ("nurse", "nurses"), ("horse", "horses"), ("farmer", "farmers")]
VERBS_SV = [("barks", "bark"), ("sleeps", "sleep"), ("runs", "run"), ("waits", "wait"), ("sings", "sing"), ("laughs", "laugh"),
            ("works", "work"), ("smiles", "smile")]
PLACES = ["in the garden", "near the river", "at the station", "by the gate", "in the hall", "on the hill"]
REFL_VERBS = ["hurt", "blamed", "introduced", "taught", "prepared", "dressed"]
AUX_PARTICIPLES = ["left", "arrived", "finished", "eaten", "gone", "slept"]

QS_PAIRS = [("The chef cooked the meal.", "Did the chef cook the meal?"), ("The nurse opened the window.", "Did the nurse open the window?"),
            ("The driver parked the van.", "Did the driver park the van?"), ("The twins painted the fence.", "Did the twins paint the fence?"),
            ("The teacher closed the book.", "Did the teacher close the book?"), ("The farmer sold the horse.", "Did the farmer sell the horse?"),
            ("The guard locked the gate.", "Did the guard lock the gate?"), ("The pilot checked the engine.", "Did the pilot check the engine?"),
            ("The baker counted the loaves.", "Did the baker count the loaves?"), ("The clerk stamped the form.", "Did the clerk stamp the form?"),
            ("The children fed the ducks.", "Did the children feed the ducks?"), ("The student passed the exam.", "Did the student pass the exam?")]
QS_PREFIX = ["", "Yesterday, ", "This morning, ", "Apparently, ", "In the end, ", "As usual, ", "Last week, ", "Once again, ",
             "Earlier, ", "Afterwards, ", "Reportedly, ", "On Sunday, ", "Before dawn, ", "Later that day, "]

FORMAL = ["I would be grateful if you could send me the {X} by {D}.", "Could you kindly forward the {X} before {D}?",
          "I am writing to request the {X}; {D} would be ideal.", "Please find below my request for the {X}, if possible by {D}."]
INFORMAL = ["hey can u send me the {X} by {D}??", "yo, need the {X} before {D}, thx!!", "pls shoot over the {X} by {D} :)",
            "hey!! got the {X}? need it {D} lol"]
THINGS = ["report", "invoice", "schedule", "slides", "contract", "photos", "minutes", "receipt", "timetable", "draft"]
WHEN = ["Friday", "Monday", "tomorrow", "noon", "the weekend", "Thursday", "tonight", "next week"]

AGENTS = ["the chef", "the nurse", "the driver", "the guard", "the farmer", "the clerk", "the painter", "the pilot"]
VOICE_VERBS = [("cooked", "was cooked by"), ("opened", "was opened by"), ("parked", "was parked by"), ("locked", "was locked by"),
               ("painted", "was painted by"), ("checked", "was checked by"), ("cleaned", "was cleaned by"), ("fixed", "was fixed by")]
# the patient comes from PLAUSIBLE_OBJECTS[verb] (selectional restrictions)
TAILS = ["before noon", "last night", "on Tuesday", "after the storm", "in the morning", "yesterday"]

PERSON_FRAMES = ["{S} walked to the station before {T} and bought a ticket to {Z}.", "{S} opened the letter after {T} and read it twice on the way to {Z}.",
                 "{S} fixed the bicycle and rode to {Z} before {T}.", "{S} packed a bag after {T} and left for {Z}."]
PLACES_Z = ["Lyon", "the coast", "Porto", "the old mill", "Leeds", "the harbour", "Ghent", "the lake", "Bergen", "the border"]
TIMES_T = ["dinner", "sunset", "the weekend", "noon", "dawn", "Friday", "midnight", "the holidays", "lunch", "Tuesday"]

NEG_FRAMES = [("The {N} is {A}.", "The {N} is not {A}."), ("The {N} was {A} {T}.", "The {N} was not {A} {T}."),
              ("The {P} did {V} {T}.", "The {P} did not {V} {T}."), ("The {P} can {V} {T}.", "The {P} cannot {V} {T}.")]
NEG_N = ["door", "shop", "bridge", "office", "road", "gate", "pool", "market"]
NEG_A = ["open", "closed", "busy", "empty", "ready", "safe", "quiet", "full"]
NEG_P = ["chef", "nurse", "driver", "guard", "farmer", "clerk", "pilot", "baker"]
NEG_V = ["leave early", "finish the report", "lock the gate", "call the office", "pay the bill", "sign the form", "fix the lamp", "feed the horse"]
NEG_T = ["today", "yesterday", "on Monday", "before noon", "this week", "last night", "in the end", "after all"]

FACTS: list[Fact] = [
    Fact("rb_form_negation", "FORM", "Is this sentence affirmative or negated?", "affirmative", "negated", "The sentence is {X}.",
         jlens_pos="affirmative", jlens_neg="not",   # 'negated' is multi-token; 'not' is the function word itself
         ground_truth="E11 (IDEAS_R) minimal pair: the same sentence with or without 'not' / 'cannot' (4 frames, all content slots shared); "
                      "kept in the E11 subset only if probe(512) >= 0.9 (pre-stated selection on the probe)",
         balanced_factors=("frame",), note="IDEAS_R E11 negation blindness"),
    Fact("rb_form_grammatical", "FORM", "Is this sentence grammatical?", "grammatical", "ungrammatical", "The sentence is {X}.",
         jlens_pos="correct", jlens_neg="wrong",   # 'grammatical' / 'ungrammatical' are multi-token under the Qwen3.6 tokenizer
         ground_truth="minimal pair: the violation type (agreement / determiner / reflexive / auxiliary) is applied or not",
         balanced_factors=("violation",)),
    Fact("rb_form_question_vs_statement", "FORM", "Is this text a question or a statement?", "a question", "a statement",
         "The text is {X}.", jlens_pos="question", jlens_neg="statement", ground_truth="the pair member (same content)",
         balanced_factors=("pair",)),
    Fact("rb_form_register", "FORM", "Is this message formal or informal?", "formal", "informal", "The message is {X}.",
         ground_truth="FORMAL vs INFORMAL frames with the same content slots", balanced_factors=("frame",)),
    Fact("rb_form_voice", "FORM", "Is this sentence in the passive voice or in the active voice?", "passive voice", "active voice",
         "The sentence is in the {X}.", jlens_pos="passive", jlens_neg="active", ground_truth="same agent / verb / patient, passive or active frame",
         balanced_factors=("verb",)),
    Fact("rb_form_person", "FORM", "Is this text written in the first person or in the third person?", "first person", "third person",
         "The text is in the {X}.", jlens_pos="first", jlens_neg="third", ground_truth="subject 'I' vs a third-person name (same frame)",
         balanced_factors=("frame",)),
]


def grammatical_pair(rng, violation: str) -> tuple[str, str]:
    """(grammatical, ungrammatical) with the same words."""
    if violation == "agreement":
        plural = rng.random() < 0.5
        n = rng.choice(NOUNS)[1 if plural else 0]
        v = rng.choice(VERBS_SV)
        good, bad = (v[1], v[0]) if plural else (v[0], v[1])
        p = rng.choice(PLACES)
        return f"The {n} {good} {p}.", f"The {n} {bad} {p}."
    if violation == "determiner":
        plural = rng.random() < 0.5
        noun = rng.choice(NOUNS)
        det_s, det_p = rng.choice([("this", "these"), ("that", "those")])
        v = rng.choice(VERBS_SV)
        verb = v[1] if plural else v[0]
        p = rng.choice(PLACES)
        good = f"{(det_p if plural else det_s).capitalize()} {noun[1 if plural else 0]} {verb} {p}."
        bad = f"{(det_s if plural else det_p).capitalize()} {noun[1 if plural else 0]} {verb} {p}."
        return good, bad
    if violation == "reflexive":
        male = rng.random() < 0.5
        name = rng.choice(T.MALE_NAMES if male else T.FEMALE_NAMES)
        v = rng.choice(REFL_VERBS)
        p = rng.choice(PLACES)
        return f"{name} {v} {'himself' if male else 'herself'} {p}.", f"{name} {v} {'herself' if male else 'himself'} {p}."
    if violation == "auxiliary":
        plural = rng.random() < 0.5
        n = rng.choice(NOUNS)[1 if plural else 0]
        pp = rng.choice(AUX_PARTICIPLES)
        good, bad = ("have", "has") if plural else ("has", "have")
        return f"The {n} {good} {pp} already.", f"The {n} {bad} {pp} already."
    raise ValueError(violation)


def build(seed: int) -> dict[str, list[Draft]]:
    out: dict[str, list[Draft]] = {}
    rng = rng_for(seed, "rb_form_grammatical")
    n = 320
    pos = balanced_bools(n, rng)
    viol = balanced_levels(["agreement", "determiner", "reflexive", "auxiliary"], n, rng)
    seen, drafts = set(), []
    for i in range(n):
        text = fresh(rng, lambda r, i=i: grammatical_pair(r, viol[i])[0 if pos[i] else 1], seen)
        drafts.append(Draft(text, 1 if pos[i] else 0, "grammatical" if pos[i] else "ungrammatical", None,
                            {"violation": viol[i], "ground_truth": pos[i]}))
    out["rb_form_grammatical"] = drafts

    rng = rng_for(seed, "rb_form_question_vs_statement")
    n = 288   # review fix item 5: 144 test items (was 90); (pair, class) assigned jointly: 12 per cell, 14 prefixes
    cells = balanced_levels([(pi, lab) for pi in range(len(QS_PAIRS)) for lab in (True, False)], n, rng)
    pairs = [c[0] for c in cells]
    pos = [c[1] for c in cells]
    seen, drafts = set(), []
    for i in range(n):
        def mk(r, i=i):
            s, q = QS_PAIRS[pairs[i]]
            core = q if pos[i] else s
            pre = r.choice(QS_PREFIX)
            return pre + (core[0].lower() + core[1:] if pre else core)
        text = fresh(rng, mk, seen)
        drafts.append(Draft(text, 1 if pos[i] else 0, "a question" if pos[i] else "a statement", None, {"pair": pairs[i], "ground_truth": pos[i]}))
    out["rb_form_question_vs_statement"] = drafts

    rng = rng_for(seed, "rb_form_register")
    n = 320
    pos = balanced_bools(n, rng)
    frames = balanced_levels([0, 1, 2, 3], n, rng)
    seen, drafts = set(), []
    for i in range(n):
        text = fresh(rng, lambda r, i=i: (FORMAL if pos[i] else INFORMAL)[frames[i]].format(X=r.choice(THINGS), D=r.choice(WHEN)), seen)
        drafts.append(Draft(text, 1 if pos[i] else 0, "formal" if pos[i] else "informal", None, {"frame": frames[i], "ground_truth": pos[i]}))
    out["rb_form_register"] = drafts

    rng = rng_for(seed, "rb_form_voice")
    n = 320
    pos = balanced_bools(n, rng)
    verbs = balanced_levels(list(range(len(VOICE_VERBS))), n, rng)
    seen, drafts = set(), []
    for i in range(n):
        def mk(r, i=i):
            act, pas = VOICE_VERBS[verbs[i]]
            a, p, t = r.choice(AGENTS), r.choice(PLAUSIBLE_OBJECTS[act]), r.choice(TAILS)
            s = f"{p} {pas} {a} {t}." if pos[i] else f"{a} {act} {p} {t}."
            return s[0].upper() + s[1:]
        text = fresh(rng, mk, seen)
        drafts.append(Draft(text, 1 if pos[i] else 0, "passive voice" if pos[i] else "active voice", None,
                            {"verb": VOICE_VERBS[verbs[i]][0], "ground_truth": pos[i]}))
    out["rb_form_voice"] = drafts

    rng = rng_for(seed, "rb_form_person")
    n = 320
    pos = balanced_bools(n, rng)
    frames = balanced_levels([0, 1, 2, 3], n, rng)
    seen, drafts = set(), []
    for i in range(n):
        def mk(r, i=i):
            subj = "I" if pos[i] else r.choice(T.NAMES)
            return PERSON_FRAMES[frames[i]].format(S=subj, Z=r.choice(PLACES_Z), T=r.choice(TIMES_T))
        text = fresh(rng, mk, seen)
        drafts.append(Draft(text, 1 if pos[i] else 0, "first person" if pos[i] else "third person", None, {"frame": frames[i], "ground_truth": pos[i]}))
    out["rb_form_person"] = drafts

    # true minimal pairs: each body is emitted affirmative AND negated (pair_id shared)
    rng = rng_for(seed, "rb_form_negation")
    n_pairs = 160
    frames = balanced_levels([0, 1, 2, 3], n_pairs, rng)
    seen, drafts = set(), []
    for i in range(n_pairs):
        def mk(r, i=i):
            body = {"N": r.choice(NEG_N), "A": r.choice(NEG_A), "P": r.choice(NEG_P), "V": r.choice(NEG_V), "T": r.choice(NEG_T)}
            return NEG_FRAMES[frames[i]][0].format(**body), body
        _text, body = fresh(rng, mk, seen)
        for k, label in ((0, 1), (1, 0)):
            text = NEG_FRAMES[frames[i]][k].format(**body)
            assert (" not " in text or "cannot" in text) == (label == 0), text
            drafts.append(Draft(text, label, "affirmative" if label else "negated", None,
                                {"frame": frames[i], "pair_id": f"n{i:03d}", "ground_truth": bool(label)}, group=f"n{i:03d}"))
    out["rb_form_negation"] = drafts
    return out
