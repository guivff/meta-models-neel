"""COUNT: values the model must keep a running count of (PLAN_R §5, §7). Each family has a k-way fact (items_rbk.json,
``kway_lo``) and a binary coarse fact on separately generated texts (items_rb.json).

items_listed     "Shopping list: apple, pear, plum" cut right after the k-th item, k = 1..8 (k-way) / fewer than five vs
                 five or more (binary); lead-in and word pool balanced over k.
bracket_depth    an expression over letters, "+", "(" and ")" cut right after a letter at nesting depth d = 1..4 (k-way)
                 / shallow (1-2) vs deep (3-4) (binary); the token length of the prefix is drawn independently of d.
column_position  the legacy ``col`` feature (f2/t6_col.py) on fresh text: 1-3 complete lines then a last line cut at a
                 word boundary so that its length falls in a bin, short (<= 20 chars) / medium (36-55) / long (71-90)
                 (k-way) and short vs long (binary); the number of previous lines is balanced over bins.

Ground truth is the construction (the cut position); ``construction.ground_truth`` holds the exact value.
"""

from __future__ import annotations

import random

from projects.g_agreement.r_bench.readerbench.common import Draft, Fact, balanced_levels, rng_for

POOLS = {
    "fruit": ["apple", "pear", "plum", "peach", "grape", "lemon", "mango", "cherry", "melon", "banana", "orange", "kiwi", "fig", "lime"],
    "animal": ["cat", "dog", "cow", "horse", "sheep", "goat", "duck", "goose", "rabbit", "mouse", "fox", "deer", "owl", "frog"],
    "colour": ["red", "blue", "green", "yellow", "purple", "orange", "brown", "black", "white", "grey", "pink", "gold", "silver", "teal"],
    "tool": ["hammer", "saw", "drill", "wrench", "chisel", "pliers", "file", "level", "clamp", "ruler", "tape", "knife", "brush", "axe"],
}
LEADINS = ["Shopping list: ", "Items: ", "We packed ", "The box held ", "On the table: ", "She named ", "Inventory: ", "Found so far: "]
KS = ["1", "2", "3", "4", "5", "6", "7", "8"]
DEPTHS = ["1", "2", "3", "4"]
LINE_BINS = {"short": (6, 20), "medium": (36, 55), "long": (71, 90)}

SENTENCES_S = ["The committee approved the budget after a long debate.", "Rain fell steadily on the quiet harbour town all night.",
               "The museum reopened its east wing to visitors in spring.", "Volunteers planted two hundred trees along the river.",
               "The library extended its opening hours for the exams.", "A small bakery on the corner sells rye bread on Fridays.",
               "The council postponed the vote on the new tram line.", "Engineers inspected the old bridge before the festival.",
               "The orchestra rehearsed the symphony twice before the concert.", "Local farmers reported a good harvest of apples this year.",
               "The ferry schedule changes when the winter season begins.", "Students presented their projects in the main hall.",
               "The lighthouse keeper recorded the storm in his logbook.", "A new footpath now connects the station and the park.",
               "The chess club meets in the community centre on Tuesdays.", "Workers repaired the leaking roof of the town hall."]
# natural sentences of >= 95 characters; the last line is one of these cut at character k (review fix 2026-10-18 item 2:
# no scrambled words), exactly the legacy col construction of f2/t6_col.py
LONG_SENTENCES = [
    "The committee reviewed every proposal carefully before the autumn meeting and asked the treasurer for a detailed report.",
    "After the storm had passed, volunteers cleared the fallen branches from the coastal road and reopened it before evening.",
    "The old mill on the river was converted into a small museum that now attracts visitors from the surrounding villages.",
    "Every morning the baker opens the shop at six, sets out the fresh loaves and greets the first customers from the station.",
    "The orchestra rehearsed the new symphony three times during the week because the conductor wanted a slower second movement.",
    "Local farmers reported a good harvest of apples and pears this year despite the late frost that damaged the early blossom.",
    "The lighthouse keeper recorded the direction of the wind in his logbook every evening for more than forty years.",
    "Students from the technical college presented their final projects in the main hall while their families watched proudly.",
    "The council postponed the vote on the new tram line until the engineers had finished their survey of the old bridge.",
    "A narrow footpath along the canal now connects the railway station with the park and the market square in the town centre.",
    "The library extended its opening hours during the examination period so that students could study late into the evening.",
    "The ferry schedule changes when the winter season begins, and the last crossing of the day leaves an hour earlier.",
    "Workers repaired the leaking roof of the town hall before the heavy rains arrived, finishing two days ahead of schedule.",
    "The chess club meets in the community centre on Tuesday evenings and welcomes beginners as well as experienced players.",
    "The museum reopened its east wing in spring with an exhibition of maps and drawings from the town's early history.",
    "Rain fell steadily on the quiet harbour town all night, and by morning the small boats were rocking gently at their moorings.",
]
assert all(len(x) >= 95 for x in LONG_SENTENCES)

FACTS: list[Fact] = [
    Fact("rb_count_items_listed", "COUNT", "How many items have been listed so far?", "", "", "So far the list has {X} items.",
         sided="kway", classes=tuple(KS), ground_truth="k = number of comma-separated items before the cut",
         readout="the model asked 'how many so far'", balanced_factors=("leadin", "pool")),
    Fact("rb_count_items_few_many", "COUNT", "Have fewer than five items or five or more items been listed so far?",
         "fewer than five", "five or more", "So far the list has {X} items.", jlens_pos="few", jlens_neg="many",
         ground_truth="k <= 4 vs k >= 5, k balanced inside each class", balanced_factors=("leadin", "pool")),
    Fact("rb_count_bracket_depth", "COUNT", "How deeply nested in brackets is the last symbol of the expression?", "", "",
         "The nesting depth is {X}.", sided="kway", classes=tuple(DEPTHS),
         ground_truth="open minus closed parentheses at the cut (1-4); prefix token length independent of depth",
         balanced_factors=("n_tokens",)),
    Fact("rb_count_bracket_shallow_deep", "COUNT", "Is the last symbol of the expression shallowly or deeply nested in brackets?",
         "shallow", "deep", "The nesting is {X}.", ground_truth="depth 1-2 vs 3-4, depth balanced inside each class",
         balanced_factors=("n_tokens",)),
    Fact("rb_count_column_position", "COUNT", "How long is the current (last) line of the text so far?", "", "",
         "The current line of text is {X}.", sided="kway", classes=("short", "medium", "long"),
         ground_truth="characters since the last newline: <= 20 / 36-55 / 71-90; the last line is a natural sentence cut at character k", balanced_factors=("n_prev_lines",)),
    Fact("rb_count_line_long_short", "COUNT", "Is the current (last) line of the text long or short?", "long", "short",
         "The current line of text is {X}.", ground_truth="characters since the last newline: 71-90 vs <= 20",
         balanced_factors=("n_prev_lines",)),
]


# ------------------------------------------------------------------ items listed
def _list_texts(rng: random.Random, ks: list[int], seen: set[str]) -> list[tuple[str, int, str, str]]:
    n = len(ks)
    leadins = balanced_levels(LEADINS, n, rng)
    pools = balanced_levels(list(POOLS), n, rng)
    out = []
    for i, k in enumerate(ks):
        for _ in range(500):
            words = rng.sample(POOLS[pools[i]], k)
            text = leadins[i] + ", ".join(words)
            if text not in seen:
                break
        else:
            raise RuntimeError("fresh list not found")
        seen.add(text)
        out.append((text, k, leadins[i], pools[i]))
    return out


def build_lists(seed: int) -> dict[str, list[Draft]]:
    rng = rng_for(seed, "rb_count_items_listed")
    seen: set[str] = set()
    kway = []
    for text, k, lead, pool in _list_texts(rng, balanced_levels(list(range(1, 9)), 8 * 96, rng), seen):
        kway.append(Draft(text, k - 1, str(k), None, {"k": k, "leadin": lead.strip(), "pool": pool, "ground_truth": k}))
    rng = rng_for(seed, "rb_count_items_few_many")
    binary = []
    for text, k, lead, pool in _list_texts(rng, balanced_levels(list(range(1, 9)), 8 * 48, rng), seen):
        ans = "fewer than five" if k <= 4 else "five or more"
        binary.append(Draft(text, 1 if k <= 4 else 0, ans, None, {"k": k, "leadin": lead.strip(), "pool": pool, "ground_truth": k}))
    return {"rb_count_items_listed": kway, "rb_count_items_few_many": binary}


# ------------------------------------------------------------------ bracket depth
def _bracket_prefix(rng: random.Random, depth: int, n_tokens: int, max_depth: int = 4) -> str | None:
    """Random prefix of n_tokens symbols (letters, '(' and ')'; '+' joins letters) ending with a letter at ``depth``."""
    letters = "abcdefghxyz"
    for _ in range(2000):
        toks: list[str] = []
        d = 0
        ok = True
        for pos in range(n_tokens):
            remaining = n_tokens - pos - 1
            opts = []
            if d < max_depth and remaining >= 1 and d + 1 <= depth + remaining:
                opts.append("(")
            if d > 0 and (not toks or toks[-1] not in ("(", "+")) and remaining >= 1 and d - 1 >= depth - remaining:
                opts.append(")")
            if (not toks or toks[-1] in ("(", "+")) and (remaining == 0 and d == depth or remaining >= 1):
                opts.append("x")
            if toks and toks[-1] in (")", "x") and remaining >= 1:
                opts.append("+")
            if not opts:
                ok = False
                break
            t = rng.choice(opts)
            if t == "(":
                d += 1
            elif t == ")":
                d -= 1
            toks.append(t)
        if not ok or d != depth or toks[-1] != "x":
            continue
        out = ""
        for t in toks:
            if t == "x":
                out += rng.choice(letters)
            elif t == "+":
                out += " + "
            else:
                out += t
        return out
    return None


def _bracket_texts(rng: random.Random, depths: list[int], seen: set[str]) -> list[tuple[str, int, int]]:
    n = len(depths)
    lens = balanced_levels([11, 13, 15, 17], n, rng)
    out = []
    for i, d in enumerate(depths):
        for _ in range(50):
            text = _bracket_prefix(rng, d, lens[i])
            if text is not None and text not in seen:
                break
        else:
            raise RuntimeError(f"no bracket prefix for depth {d} length {lens[i]}")
        seen.add(text)
        out.append((text, d, lens[i]))
    return out


def build_brackets(seed: int) -> dict[str, list[Draft]]:
    rng = rng_for(seed, "rb_count_bracket_depth")
    seen: set[str] = set()
    kway = [Draft(t, d - 1, str(d), None, {"depth": d, "n_tokens": n, "ground_truth": d})
            for t, d, n in _bracket_texts(rng, balanced_levels([1, 2, 3, 4], 4 * 180, rng), seen)]
    rng = rng_for(seed, "rb_count_bracket_shallow_deep")
    binary = [Draft(t, 1 if d <= 2 else 0, "shallow" if d <= 2 else "deep", None, {"depth": d, "n_tokens": n, "ground_truth": d})
              for t, d, n in _bracket_texts(rng, balanced_levels([1, 2, 3, 4], 4 * 96, rng), seen)]
    return {"rb_count_bracket_depth": kway, "rb_count_bracket_shallow_deep": binary}


# ------------------------------------------------------------------ column position
def _cut(rng: random.Random, lo: int, hi: int) -> str:
    """A natural sentence cut at character k (uniform in [lo, hi]; mid-word cuts allowed, as in the legacy col feature)."""
    s = rng.choice(LONG_SENTENCES)
    k = rng.randint(lo, min(hi, len(s) - 1))
    return s[:k]


def _col_texts(rng: random.Random, bins: list[str], seen: set[str]) -> list[tuple[str, str, int, int]]:
    n = len(bins)
    prev = balanced_levels([1, 2, 3], n, rng)
    out = []
    for i, b in enumerate(bins):
        lo, hi = LINE_BINS[b]
        for _ in range(100):
            lines = rng.sample(SENTENCES_S, prev[i])
            last = _cut(rng, lo, hi)
            text = "\n".join(lines + [last])
            if text not in seen:
                break
        else:
            raise RuntimeError("fresh col text not found")
        seen.add(text)
        assert lo <= len(last) <= hi
        out.append((text, b, prev[i], len(last)))
    return out


def build_col(seed: int) -> dict[str, list[Draft]]:
    rng = rng_for(seed, "rb_count_column_position")
    seen: set[str] = set()
    classes = ["short", "medium", "long"]
    kway = [Draft(t, classes.index(b), b, None, {"bin": b, "n_prev_lines": p, "col": c, "ground_truth": c})
            for t, b, p, c in _col_texts(rng, balanced_levels(classes, 3 * 240, rng), seen)]
    rng = rng_for(seed, "rb_count_line_long_short")
    binary = [Draft(t, 1 if b == "long" else 0, b, None, {"bin": b, "n_prev_lines": p, "col": c, "ground_truth": c})
              for t, b, p, c in _col_texts(rng, balanced_levels(["long", "short"], 2 * 180, rng), seen)]
    return {"rb_count_column_position": kway, "rb_count_line_long_short": binary}


def build(seed: int) -> dict[str, list[Draft]]:
    out = build_lists(seed)
    out.update(build_brackets(seed))
    out.update(build_col(seed))
    return out
