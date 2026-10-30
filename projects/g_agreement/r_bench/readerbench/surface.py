"""SURFACE: the label is a property of the characters (PLAN_R §7). Every positive has a matched negative built from the
same template with the cue removed, so nothing but the cue separates the classes.

contains_digit    the quantity is written as a numeral ("3 apples") or as a number word ("three apples")
allcaps_word      one content word of the sentence is upper-cased or not (same word, same sentence)
bigram_at_least   the phrase "at least" vs a synonymous phrase ("a minimum of", "no fewer than") in the same slot
code_language     a synthesised Python snippet vs the same program in JavaScript
word_count        short (6-8 words) vs long (14-16 words) sentences over the same subject / verb / object pools
"""

from __future__ import annotations

from projects.g_agreement.r_bench.readerbench.common import (PLAUSIBLE_OBJECTS, Draft, Fact, balanced_bools, balanced_levels, fresh,
                                                              plausible_event, rng_for, word_count)

PEOPLE = ["Maria", "the baker", "my uncle", "the teacher", "Omar", "the twins", "our neighbour", "the driver", "Lena", "the farmer"]
ITEMS = ["apples", "tickets", "candles", "notebooks", "chairs", "lemons", "boxes", "postcards", "bottles", "umbrellas"]
PLACES = ["at the market", "in town", "online", "at the fair", "from a stall", "at the station", "in the village", "at the shop"]
TIMES = ["yesterday", "this morning", "last week", "on Monday", "before lunch", "after work", "at noon", "on Friday"]
NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
DIGIT_FRAMES = ["{P} bought {N} {I} {L} {T}.", "{T}, {P} counted {N} {I} {L}.", "{P} found {N} {I} {L} {T}.",
                "{L}, {P} sold {N} {I} {T}."]

CAPS_FRAMES = ["The report was {W} and nobody had read it.", "Please mark this parcel as {W} before shipping.",
               "The sign on the door said {W} in red letters.", "Her note simply read {W}, nothing more."]
CAPS_WORDS = ["urgent", "fragile", "closed", "private", "delayed", "approved", "pending", "final", "cancelled", "confidential"]

BIGRAM_FRAMES = ["The trip takes {Q} {K} hours by train.", "You will need {Q} {K} signatures on the form.",
                 "The recipe calls for {Q} {K} eggs.", "Each team must have {Q} {K} players on the pitch.",
                 "The course requires {Q} {K} weeks of practice.", "The hall seats {Q} {K} hundred people."]
BIGRAM_K = ["two", "three", "four", "five", "six", "seven", "eight", "nine"]
BIGRAM_NEG = ["a minimum of", "no fewer than", "upwards of"]

CODE_NAMES = ["total", "count", "items", "score", "price", "width", "index", "value", "limit", "names"]
CODE_FRAMES = {
    "function": ("def {f}({a}, {b}):\n    return {a} + {b}", "function {f}({a}, {b}) {{\n  return {a} + {b};\n}}"),
    "loop": ("for {a} in {b}:\n    print({a})", "for (const {a} of {b}) {{\n  console.log({a});\n}}"),
    "assign": ("{a} = [1, 2, 3]\n{b} = len({a})\nprint({b})", "const {a} = [1, 2, 3];\nconst {b} = {a}.length;\nconsole.log({b});"),
    "condition": ("if {a} > {b}:\n    {a} = {b}\nelse:\n    {b} = {a}", "if ({a} > {b}) {{\n  {a} = {b};\n}} else {{\n  {b} = {a};\n}}"),
}
FUNCS = ["add", "combine", "merge", "total", "join"]

# word count: every slot has a fixed width, so short = 2+1+2+2 = 7 words and long = 2+1+2+10 = 15 words exactly
SUBJ = ["The chef", "A nurse", "The driver", "Our neighbour", "The clerk", "The pilot", "A student", "The guard"]
VERB = ["carried", "painted", "counted", "washed", "fixed", "opened", "packed", "sold"]   # objects from PLAUSIBLE_OBJECTS[verb]
OBJ = sorted({o for v in VERB for o in PLAUSIBLE_OBJECTS[v]})
SHORT_TAILS = ["this morning.", "at dawn.", "very slowly.", "after lunch.", "on Monday.", "quite early."]   # disjoint from form.TAILS
LONG_TAILS = ["in the wooden shed while the rain fell steadily outside.",
              "near the harbour before the ferry arrived with the passengers.",
              "behind the station as the last evening train pulled away.",
              "in the square while the church bells rang across town.",
              "inside the garage long after the other workers had left.",
              "beside the river where the children had played that afternoon."]
assert all(len(t.split()) == 10 for t in LONG_TAILS) and all(len(t.split()) == 2 for t in SHORT_TAILS)
assert all(len(t.split()) == 2 for t in SUBJ + OBJ)

FACTS: list[Fact] = [
    Fact("rb_surface_contains_digit", "SURFACE", "Does the text contain a digit?", "contains a digit", "contains no digit",
         "The text {X}.", jlens_pos="digit", jlens_neg="word", ground_truth="the quantity slot holds a numeral (2-9) vs its number word",
         balanced_factors=("frame",)),
    Fact("rb_surface_allcaps_word", "SURFACE", "Does the text contain a word written in all capital letters?",
         "contains a word in capitals", "contains no word in capitals", "The text {X}.", jlens_pos="capitals", jlens_neg="lowercase",
         ground_truth="the slot word is upper-cased vs lower-cased", balanced_factors=("frame", "word")),
    Fact("rb_surface_bigram_at_least", "SURFACE", "Does the text contain the phrase \"at least\"?", "at least", "no such phrase",
         "The text mentions {X}.", sided="one", jlens_pos="least", ground_truth="the quantifier slot is 'at least' vs a synonym",
         balanced_factors=("frame",)),
    Fact("rb_surface_code_language", "SURFACE", "Is this code snippet written in Python or in JavaScript?", "Python", "JavaScript",
         "The code is written in {X}.", ground_truth="the frame's language (same program in both)", balanced_factors=("frame",)),
    Fact("rb_surface_word_count", "SURFACE", "Is this a short sentence or a long sentence?", "a short sentence", "a long sentence",
         "This is {X}.", jlens_pos="short", jlens_neg="long", ground_truth="7 words vs 15 words (same subject / verb / object pools; the tail slot is 2 or 10 words)",
         balanced_factors=()),
]


def build(seed: int) -> dict[str, list[Draft]]:
    out: dict[str, list[Draft]] = {}
    # digits
    rng = rng_for(seed, "rb_surface_contains_digit")
    n = 320
    pos = balanced_bools(n, rng)
    frames = balanced_levels(list(range(len(DIGIT_FRAMES))), n, rng)
    seen: set[str] = set()
    drafts = []
    for i in range(n):
        def mk(r, i=i):
            k = r.randint(2, 9)
            t = DIGIT_FRAMES[frames[i]].format(P=r.choice(PEOPLE), N=str(k) if pos[i] else NUMBER_WORDS[k], I=r.choice(ITEMS),
                                               L=r.choice(PLACES), T=r.choice(TIMES))
            return t[0].upper() + t[1:], k
        text, k = fresh(rng, mk, seen)
        assert any(ch.isdigit() for ch in text) == pos[i]
        drafts.append(Draft(text, 1 if pos[i] else 0, "contains a digit" if pos[i] else "contains no digit", None,
                            {"frame": frames[i], "quantity": k, "ground_truth": pos[i]}))
    out["rb_surface_contains_digit"] = drafts
    # all caps
    rng = rng_for(seed, "rb_surface_allcaps_word")
    n = 320
    pos = balanced_bools(n, rng)
    frames = balanced_levels(list(range(len(CAPS_FRAMES))), n, rng)
    words = balanced_levels(CAPS_WORDS, n, rng)
    seen, drafts = set(), []
    caps_prefixes = ["", "Note: ", "Update: ", "Memo: ", "Reminder: ", "Heads-up: ", "Log: ", "Status: ", "Notice: ", "Entry: ", "Message: ", "Record: "]
    for i in range(n):
        w = words[i].upper() if pos[i] else words[i]
        text = fresh(rng, lambda r, i=i, w=w: r.choice(caps_prefixes) + CAPS_FRAMES[frames[i]].format(W=w), seen)
        assert any(tok.isupper() and len(tok) > 1 for tok in text.replace(".", "").split()) == pos[i], text
        drafts.append(Draft(text, 1 if pos[i] else 0, "contains a word in capitals" if pos[i] else "contains no word in capitals", None,
                            {"frame": frames[i], "word": words[i], "ground_truth": pos[i]}))
    out["rb_surface_allcaps_word"] = drafts
    # bigram
    rng = rng_for(seed, "rb_surface_bigram_at_least")
    n = 288
    pos = balanced_bools(n, rng)
    frames = balanced_levels(list(range(len(BIGRAM_FRAMES))), n, rng)
    seen, drafts = set(), []
    prefixes = ["", "Note: ", "Remember: ", "Reminder: ", "Important: ", "Please note: ", "FYI: ", "Rule: ", "Also: ", "Tip: ", "Update: ", "Policy: "]
    for i in range(n):
        q = "at least" if pos[i] else rng.choice(BIGRAM_NEG)
        text = fresh(rng, lambda r, q=q, i=i: r.choice(prefixes) + BIGRAM_FRAMES[frames[i]].format(Q=q, K=r.choice(BIGRAM_K)), seen)
        assert ("at least" in text) == pos[i]
        drafts.append(Draft(text, 1 if pos[i] else 0, "at least" if pos[i] else "no such phrase", None,
                            {"frame": frames[i], "quantifier": q, "ground_truth": pos[i]}))
    out["rb_surface_bigram_at_least"] = drafts
    # code language
    rng = rng_for(seed, "rb_surface_code_language")
    n = 320
    pos = balanced_bools(n, rng)
    frames = balanced_levels(list(CODE_FRAMES), n, rng)
    seen, drafts = set(), []
    for i in range(n):
        def mk(r, i=i):
            a, b = r.sample(CODE_NAMES, 2)
            py, js = CODE_FRAMES[frames[i]]
            return (py if pos[i] else js).format(a=a, b=b, f=r.choice(FUNCS))
        text = fresh(rng, mk, seen)
        drafts.append(Draft(text, 1 if pos[i] else 0, "Python" if pos[i] else "JavaScript", None,
                            {"frame": frames[i], "ground_truth": "Python" if pos[i] else "JavaScript"}))
    out["rb_surface_code_language"] = drafts
    # word count
    rng = rng_for(seed, "rb_surface_word_count")
    n = 320
    pos = balanced_bools(n, rng)
    seen, drafts = set(), []
    for i in range(n):
        def mk(r, i=i):
            v, o = plausible_event(r, VERB)
            return f"{r.choice(SUBJ)} {v} {o} {r.choice(SHORT_TAILS if pos[i] else LONG_TAILS)}"
        text = fresh(rng, mk, seen)
        wc = word_count(text)
        assert wc == (7 if pos[i] else 15), (text, wc)
        drafts.append(Draft(text, 1 if pos[i] else 0, "a short sentence" if pos[i] else "a long sentence", None,
                            {"words": wc, "ground_truth": wc}))
    out["rb_surface_word_count"] = drafts
    return out
