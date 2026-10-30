"""COMPUTED: the label is a property of a result the model must compute from the text (PLAN_R §7).

sum_parity        "47 + 36 =" -> even / odd (two 2-digit operands; carry crossed and balanced)
sum_carry         fresh operands -> the units digits produce a carry / do not (parity crossed and balanced)
difference_sign   "23 - 41 =" -> positive / negative (|a - b| balanced over three magnitude bins)
comparison        "Which is larger: 347 or 352?" -> the first / the second number (the differing digit position balanced)
syllogism_valid   three valid and three invalid categorical forms over nonsense nouns (no belief bias), valid / invalid
weekday           "Today is Tuesday. In 10 days it will be" -> 7-way weekday (items_rbk.json) and weekend vs weekday (binary)

Ground truth is arithmetic / the form table; ``construction.ground_truth`` holds the computed value.
"""

from __future__ import annotations

import random

from projects.g_agreement.r_bench.readerbench.common import Draft, Fact, balanced_bools, balanced_levels, fresh, rng_for

ARITH_FRAMES = ["{a} + {b} =", "What is {a} plus {b}?", "Compute {a} + {b}.", "The sum of {a} and {b} is"]
DIFF_FRAMES = ["{a} - {b} =", "What is {a} minus {b}?", "Compute {a} - {b}.", "The result of {a} minus {b} is"]
CMP_FRAMES = ["Which is larger: {a} or {b}?", "Of the numbers {a} and {b}, which is greater?", "Compare {a} and {b}: which is the larger number?",
              "Is {a} or {b} the bigger number?"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_FRAMES = ["Today is {d}. In {n} days it will be", "If today is {d}, then {n} days from now it will be",
              "It is {d} today, so {n} days later the day of the week will be", "Starting from {d}, count forward {n} days: the day is",
              "Yesterday was {d}. In {n} days from today it will be", "Given that today is {d}, the day {n} days ahead is",
              "{d} is today's day; exactly {n} days later it will be", "Suppose it is {d}. After {n} more days the weekday will be"]
NONSENSE = ["blorps", "zints", "quams", "frells", "dravs", "mibs", "tarks", "wugs", "plins", "gorfs", "snerls", "vexes", "kloms", "yabs",
            "thrims", "pelts"]
INDIVIDUALS = ["Zem", "Kol", "Vin", "Tao", "Rix", "Jub", "Nal", "Fip"]
SYLLOGISMS = {   # name: (frame, valid)
    "barbara": ("All {A} are {B}. All {B} are {C}. Therefore, all {A} are {C}.", True),
    "celarent": ("All {A} are {B}. No {B} are {C}. Therefore, no {A} are {C}.", True),
    "instance": ("All {A} are {B}. {X} is one of the {A}. Therefore, {X} is one of the {B}.", True),
    "undistributed_middle": ("All {A} are {B}. All {C} are {B}. Therefore, all {A} are {C}.", False),
    "illicit_conversion": ("All {A} are {B}. All {B} are {C}. Therefore, all {C} are {A}.", False),
    "affirming_consequent": ("All {A} are {B}. {X} is one of the {B}. Therefore, {X} is one of the {A}.", False),
}

FACTS: list[Fact] = [
    Fact("rb_computed_sum_parity", "COMPUTED", "Is the result of this addition even or odd?", "even", "odd", "The result is {X}.",
         ground_truth="(a + b) % 2 == 0", readout="the model's own sum", balanced_factors=("carry", "frame")),
    Fact("rb_computed_sum_carry", "COMPUTED", "Does adding the units digits of this addition produce a carry?", "with a carry", "without a carry",
         "The addition is {X}.", jlens_pos="carry", jlens_neg="none", ground_truth="a % 10 + b % 10 >= 10",
         readout="the model's own sum", balanced_factors=("parity", "frame")),
    Fact("rb_computed_difference_sign", "COMPUTED", "Is the result of this subtraction positive or negative?", "positive", "negative",
         "The result is {X}.", ground_truth="sign of a - b (a != b)", readout="the model's own difference",
         balanced_factors=("magnitude_bin", "frame")),
    Fact("rb_computed_comparison", "COMPUTED", "Which of the two numbers is larger?", "the first number", "the second number",
         "The larger one is {X}.", jlens_pos="first", jlens_neg="second", ground_truth="a > b for the two 3-digit numbers as written",
         readout="the model's own answer", balanced_factors=("differ_at", "frame")),
    Fact("rb_computed_syllogism_valid", "COMPUTED", "Is this argument logically valid?", "valid", "invalid", "The argument is {X}.",
         ground_truth="the form (SYLLOGISMS table): barbara / celarent / instance valid; undistributed middle / illicit conversion / "
                      "affirming the consequent invalid; nonsense nouns so content cannot help", readout="the model's own verdict",
         balanced_factors=("form",)),
    Fact("rb_computed_weekday", "COMPUTED", "What day of the week completes the sentence?", "", "", "The day will be {X}.",
         sided="kway", classes=tuple(WEEKDAYS), ground_truth="(index(d) + n) % 7, n in 1..20 (frame 4 states yesterday's day)", readout="greedy completion",
         balanced_factors=("frame",)),
    Fact("rb_computed_weekday_weekend", "COMPUTED", "Does the sentence end on a weekend day or a weekday?", "a weekend day", "a weekday",
         "The day will be {X}.", jlens_pos="weekend", jlens_neg="weekday", ground_truth="(index(d) + n) % 7 in {Saturday, Sunday}",
         readout="greedy completion", balanced_factors=("frame",)),
]


def _operands(rng: random.Random, parity_even: bool, carry: bool) -> tuple[int, int]:
    for _ in range(1000):
        a, b = rng.randint(10, 99), rng.randint(10, 99)
        if ((a + b) % 2 == 0) == parity_even and (a % 10 + b % 10 >= 10) == carry:
            return a, b
    raise RuntimeError


def build_sums(seed: int) -> dict[str, list[Draft]]:
    out = {}
    seen: set[str] = set()   # shared: the two sum facts never reuse a text
    for fid, key in (("rb_computed_sum_parity", "parity"), ("rb_computed_sum_carry", "carry")):
        rng = rng_for(seed, fid)
        n = 320
        even = balanced_bools(n, rng)
        carry = balanced_bools(n, rng)
        frames = balanced_levels(list(range(len(ARITH_FRAMES))), n, rng)
        drafts = []
        for i in range(n):
            def mk(r, i=i):
                a, b = _operands(r, even[i], carry[i])
                return ARITH_FRAMES[frames[i]].format(a=a, b=b), a, b
            text, a, b = fresh(rng, mk, seen)
            c = {"a": a, "b": b, "sum": a + b, "parity": "even" if even[i] else "odd", "carry": carry[i], "frame": frames[i]}
            if key == "parity":
                drafts.append(Draft(text, 1 if even[i] else 0, c["parity"], None, {**c, "ground_truth": a + b}))
            else:
                drafts.append(Draft(text, 1 if carry[i] else 0, "with a carry" if carry[i] else "without a carry", None,
                                    {**c, "ground_truth": a % 10 + b % 10}))
        out[fid] = drafts
    return out


def build_difference(seed: int) -> list[Draft]:
    rng = rng_for(seed, "rb_computed_difference_sign")
    n = 336   # multiple of 2 x 3 x 4
    positive = balanced_bools(n, rng)
    bins = balanced_levels([(1, 9), (10, 39), (40, 89)], n, rng)
    frames = balanced_levels(list(range(len(DIFF_FRAMES))), n, rng)
    seen, out = set(), []
    for i in range(n):
        lo, hi = bins[i]
        def mk(r, i=i, lo=lo, hi=hi):
            d = r.randint(lo, hi)
            small = r.randint(10, 99 - d)
            a, b = (small + d, small) if positive[i] else (small, small + d)
            return DIFF_FRAMES[frames[i]].format(a=a, b=b), a, b
        text, a, b = fresh(rng, mk, seen)
        out.append(Draft(text, 1 if positive[i] else 0, "positive" if positive[i] else "negative", None,
                         {"a": a, "b": b, "difference": a - b, "magnitude_bin": f"{lo}-{hi}", "frame": frames[i], "ground_truth": a - b}))
    return out


def build_comparison(seed: int) -> list[Draft]:
    rng = rng_for(seed, "rb_computed_comparison")
    n = 336
    first_larger = balanced_bools(n, rng)
    differ = balanced_levels(["hundreds", "tens", "units"], n, rng)
    frames = balanced_levels(list(range(len(CMP_FRAMES))), n, rng)
    seen, out = set(), []
    for i in range(n):
        def mk(r, i=i):
            x = r.randint(100, 999)
            h, t, u = x // 100, (x // 10) % 10, x % 10
            if differ[i] == "hundreds":
                y = r.choice([v for v in range(1, 10) if v != h]) * 100 + t * 10 + u
            elif differ[i] == "tens":
                y = h * 100 + r.choice([v for v in range(10) if v != t]) * 10 + u
            else:
                y = h * 100 + t * 10 + r.choice([v for v in range(10) if v != u])
            big, small = max(x, y), min(x, y)
            a, b = (big, small) if first_larger[i] else (small, big)
            return CMP_FRAMES[frames[i]].format(a=a, b=b), a, b
        text, a, b = fresh(rng, mk, seen)
        out.append(Draft(text, 1 if first_larger[i] else 0, "the first number" if first_larger[i] else "the second number", None,
                         {"a": a, "b": b, "differ_at": differ[i], "frame": frames[i], "ground_truth": max(a, b)}))
    return out


def build_syllogisms(seed: int) -> list[Draft]:
    rng = rng_for(seed, "rb_computed_syllogism_valid")
    per = 48
    seen, out = set(), []
    for name, (frame, valid) in SYLLOGISMS.items():
        for _ in range(per):
            def mk(r, frame=frame):
                A, B, C = r.sample(NONSENSE, 3)
                return frame.format(A=A, B=B, C=C, X=r.choice(INDIVIDUALS)), (A, B, C)
            text, (A, B, C) = fresh(rng, mk, seen)
            out.append(Draft(text, 1 if valid else 0, "valid" if valid else "invalid", None,
                             {"form": name, "terms": [A, B, C], "ground_truth": "valid" if valid else "invalid"}))
    return out


def build_weekdays(seed: int) -> dict[str, list[Draft]]:
    out = {}
    rng = rng_for(seed, "rb_computed_weekday")
    n = 7 * 48   # capacity per (answer, frame) is 20 values of n; the binary fact draws from the same space,
    # so answer and frame are assigned jointly (6 items per cell) to leave room for it
    cells = balanced_levels([(a, fi) for a in range(7) for fi in range(len(DAY_FRAMES))], n, rng)
    answers = [c[0] for c in cells]
    frames = [c[1] for c in cells]
    seen, kway = set(), []

    def _day(ans: int, fi: int):
        def mk(r):
            nd = r.randint(1, 20)
            start = (ans - nd) % 7
            # frame 4 says "yesterday was d": the start day is the day before today
            d_shown = WEEKDAYS[(start - 1) % 7] if fi == 4 else WEEKDAYS[start]
            return DAY_FRAMES[fi].format(d=d_shown, n=nd), nd, start
        return mk

    for i in range(n):
        text, nd, start = fresh(rng, _day(answers[i], frames[i]), seen)
        kway.append(Draft(text, answers[i], WEEKDAYS[answers[i]], None,
                          {"start": WEEKDAYS[start], "n": nd, "frame": frames[i], "ground_truth": WEEKDAYS[answers[i]]}))
    out["rb_computed_weekday"] = kway
    rng = rng_for(seed, "rb_computed_weekday_weekend")
    n = 320
    weekend = balanced_bools(n, rng)
    # (answer, frame) cells assigned jointly inside each class: weekend 2 x 8 cells x 10, weekday 5 x 8 cells x 4, so with
    # the k-way fact's 6 per cell no cell exceeds its 20 distinct texts
    nf = len(DAY_FRAMES)
    we_cells = iter(balanced_levels([(a, fi) for a in (5, 6) for fi in range(nf)], n // 2, rng))
    wd_cells = iter(balanced_levels([(a, fi) for a in range(5) for fi in range(nf)], n // 2, rng))
    frames = []
    binary = []
    for i in range(n):
        ans, fi = next(we_cells) if weekend[i] else next(wd_cells)
        frames.append(fi)
        text, nd, start = fresh(rng, _day(ans, frames[i]), seen)
        binary.append(Draft(text, 1 if weekend[i] else 0, "a weekend day" if weekend[i] else "a weekday", None,
                            {"start": WEEKDAYS[start], "n": nd, "frame": frames[i], "ground_truth": WEEKDAYS[ans]}))
    out["rb_computed_weekday_weekend"] = binary
    return out


def build(seed: int) -> dict[str, list[Draft]]:
    out = build_sums(seed)
    out["rb_computed_difference_sign"] = build_difference(seed)
    out["rb_computed_comparison"] = build_comparison(seed)
    out["rb_computed_syllogism_valid"] = build_syllogisms(seed)
    out.update(build_weekdays(seed))
    return out
