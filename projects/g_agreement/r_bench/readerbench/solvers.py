"""Independent recomputation of every ReaderBench label from the item alone (WS1's parent round-trip idea, applied to
generated facts): one solver per fact reads ``prompt_text`` (plus ``system`` / ``capture_messages`` for CONTEXT) and
returns the answer string without touching the generator's ``construction``. ``roundtrip(items)`` compares it with
``primary.answer`` on every item; the build fails on any disagreement (build.py), and the tests call it too.

The solvers share only the static tables (tables.py and the modules' word lists), never the seeded construction, so a
generator bug that mislabels an item is caught unless the same bug sits in the table itself.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from projects.g_agreement.r_bench.readerbench import computed as CP
from projects.g_agreement.r_bench.readerbench import context as CX
from projects.g_agreement.r_bench.readerbench import count as CN
from projects.g_agreement.r_bench.readerbench import form as FM
from projects.g_agreement.r_bench.readerbench import internal as IN
from projects.g_agreement.r_bench.readerbench import meta as ME
from projects.g_agreement.r_bench.readerbench import surface as SF
from projects.g_agreement.r_bench.readerbench import syntax as SX
from projects.g_agreement.r_bench.readerbench import tables as T
from projects.g_agreement.r_bench.readerbench import topic as TP
from projects.g_agreement.r_bench.readerbench.common import contains_word

Solver = Callable[[dict[str, Any]], str | None]
SOLVERS: dict[str, Solver] = {}


def solver(*ids: str):
    def deco(fn: Solver) -> Solver:
        for i in ids:
            SOLVERS[i] = fn
        return fn
    return deco


def _text(it: dict[str, Any]) -> str:
    return it["prompt_text"]


def _country_in(text: str, attr: str = "landmark") -> T.Country | None:
    """The unique country whose ``attr`` (landmark / capital / name) occurs in the text."""
    hits = []
    for c in T.COUNTRIES:
        v = getattr(c, attr)
        if v and contains_word(text, T.bare(v) if attr == "name" else v):
            hits.append(c)
    if attr == "name":   # 'Dominican Republic'-style containment is not an issue in our table, but keep the longest match
        hits.sort(key=lambda c: -len(c.name))
        hits = hits[:1] if hits else hits
    return hits[0] if len(hits) == 1 else None


# ------------------------------------------------------------------ KHOP
@solver("rb_khop_landmark_capital_bridge", "rb_khop_landmark_currency_bridge", "rb_khop_3hop_middle")
def _khop_bridge(it):
    c = _country_in(_text(it), "landmark")
    return T.bare(c.name) if c else None


@solver("rb_khop_landmark_capital_answer")
def _khop_cap(it):
    c = _country_in(_text(it), "landmark")
    return c.capital if c else None


@solver("rb_khop_landmark_currency_answer")
def _khop_cur(it):
    c = _country_in(_text(it), "landmark")
    return c.currency if c else None


@solver("rb_khop_capital_language_bridge")
def _khop_lang_bridge(it):
    c = _country_in(_text(it), "capital")
    return T.bare(c.name) if c else None


@solver("rb_khop_capital_language_answer")
def _khop_lang(it):
    c = _country_in(_text(it), "capital")
    return c.language if c else None


# ------------------------------------------------------------------ KNOWLEDGE
def _entity(text: str, pool: list[str]) -> str | None:
    hits = [e for e in pool if contains_word(text, e)]
    hits.sort(key=len, reverse=True)
    return hits[0] if hits else None


@solver("rb_knowledge_country_continent")
def _continent(it):
    c = _country_in(_text(it), "name")
    return c.continent if c else None


@solver("rb_knowledge_city_is_capital")
def _is_capital(it):
    text = _text(it)
    caps = [c.capital for c in T.COUNTRIES if c.capital and contains_word(text, c.capital)]
    others = [c.other_city for c in T.COUNTRIES if contains_word(text, c.other_city)]
    # "Santiago de Cuba" also matches the capital "Santiago": the longest matching city name wins
    best = max(caps + others, key=len, default=None)
    if best is None:
        return None
    return "a national capital" if best in caps else "not a national capital"


@solver("rb_knowledge_element_metal")
def _metal(it):
    e = _entity(_text(it), T.METALS + T.NONMETALS)
    return None if e is None else ("a metal" if e in T.METALS else "a nonmetal")


@solver("rb_knowledge_figure_field")
def _field(it):
    e = _entity(_text(it), T.SCIENTISTS + T.COMPOSERS)
    return None if e is None else ("a scientist" if e in T.SCIENTISTS else "a composer")


@solver("rb_knowledge_animal_class")
def _animal(it):
    e = _entity(_text(it), T.MAMMALS + T.BIRDS)
    return None if e is None else ("a mammal" if e in T.MAMMALS else "a bird")


@solver("rb_knowledge_country_capital_distractor")
def _capital_of(it):
    c = _country_in(_text(it), "name")
    return c.capital if c else None


@solver("rb_knowledge_landmark_country_distractor")
def _landmark_country(it):
    c = _country_in(_text(it), "landmark")
    return T.bare(c.name) if c else None


# ------------------------------------------------------------------ SYNTAX
_SING_HEADS = {s for s, _ in SX.HEADS}
_PLUR_HEADS = {p for _, p in SX.HEADS}
_ATTR = {w for pair in SX.ATTRACTORS for w in pair}


@solver("rb_syntax_agreement_number")
def _agreement(it):
    m = re.fullmatch(r"The (\w+) (\w+) the (\w+) (\w+)", _text(it))
    if not m:
        return None
    head = m.group(1)
    return "singular" if head in _SING_HEADS else "plural" if head in _PLUR_HEADS else None


@solver("rb_syntax_head_identity")
def _head(it):
    m = re.fullmatch(r"The (\w+) (\w+) the (\w+) (\w+)", _text(it))
    return m.group(1) if m and m.group(4) in _ATTR else None


_FINITE = set(SX.VERBS_T) | set(SX.VERBS_I)


@solver("rb_syntax_clause_count")
def _clauses(it):
    words = re.findall(r"[a-z]+", _text(it).lower())
    n = sum(w in _FINITE for w in words)
    return "one clause" if n == 1 else "two clauses" if n == 2 else None


@solver("rb_syntax_pronoun_antecedent")
def _pronoun(it):
    text = _text(it)
    pron = "he" if contains_word(text, "he") else "she" if contains_word(text, "she") else None
    names = [n for n in T.NAMES if contains_word(text, n)]
    if pron is None or len(names) != 2:
        return None
    pool = T.MALE_NAMES if pron == "he" else T.FEMALE_NAMES
    hits = [n for n in names if n in pool]
    return hits[0] if len(hits) == 1 else None


@solver("rb_syntax_quantifier_every_no")
def _quant(it):
    text = _text(it)
    ev, no = contains_word(text, "every"), contains_word(text, "no")
    return "every one of them did" if ev and not no else "none of them did" if no and not ev else None


@solver("rb_syntax_before_after")
def _order(it):
    text = _text(it)
    w = "before" if contains_word(text, "before") else "after" if contains_word(text, "after") else None
    if w is None:
        return None
    starts_with_w = text.lower().startswith(w)
    # "X before Y" -> X first; "Before Y, X" -> Y (second-mentioned) first
    first_mentioned_first = (w == "before") != starts_with_w
    return "the first-mentioned event" if first_mentioned_first else "the second-mentioned event"


# ------------------------------------------------------------------ COUNT
@solver("rb_count_items_listed")
def _items(it):
    body = _text(it)
    for lead in CN.LEADINS:
        if body.startswith(lead):
            body = body[len(lead):]
            break
    else:
        return None
    return str(len(body.split(", ")))


@solver("rb_count_items_few_many")
def _few_many(it):
    k = _items(it)
    return None if k is None else ("fewer than five" if int(k) <= 4 else "five or more")


def _depth(text: str) -> int:
    return text.count("(") - text.count(")")


@solver("rb_count_bracket_depth")
def _bracket(it):
    return str(_depth(_text(it)))


@solver("rb_count_bracket_shallow_deep")
def _shallow(it):
    return "shallow" if _depth(_text(it)) <= 2 else "deep"


def _col(text: str) -> int:
    return len(text.rsplit("\n", 1)[-1])


@solver("rb_count_column_position")
def _colbin(it):
    c = _col(_text(it))
    for b, (lo, hi) in CN.LINE_BINS.items():
        if lo <= c <= hi:
            return b
    return None


@solver("rb_count_line_long_short")
def _long_short(it):
    b = _colbin(it)
    return b if b in ("long", "short") else None


# ------------------------------------------------------------------ COMPUTED
def _two_ints(text: str) -> tuple[int, int] | None:
    nums = re.findall(r"\d+", text)
    return (int(nums[0]), int(nums[1])) if len(nums) == 2 else None


@solver("rb_computed_sum_parity")
def _parity(it):
    ab = _two_ints(_text(it))
    return None if ab is None else ("even" if (ab[0] + ab[1]) % 2 == 0 else "odd")


@solver("rb_computed_sum_carry")
def _carry(it):
    ab = _two_ints(_text(it))
    return None if ab is None else ("with a carry" if ab[0] % 10 + ab[1] % 10 >= 10 else "without a carry")


@solver("rb_computed_difference_sign")
def _sign(it):
    ab = _two_ints(_text(it))
    return None if ab is None or ab[0] == ab[1] else ("positive" if ab[0] > ab[1] else "negative")


@solver("rb_computed_comparison")
def _cmp(it):
    ab = _two_ints(_text(it))
    return None if ab is None or ab[0] == ab[1] else ("the first number" if ab[0] > ab[1] else "the second number")


@solver("rb_computed_syllogism_valid")
def _syllogism(it):
    text = _text(it)
    for name, (frame, valid) in CP.SYLLOGISMS.items():
        # first occurrence of a placeholder -> named group, later ones -> backreference (the same term must recur)
        seen: set[str] = set()
        parts = []
        for tok in re.split(r"(\{[ABCX]\})", frame):
            if re.fullmatch(r"\{[ABCX]\}", tok):
                k = tok[1]
                parts.append(rf"(?P<{k}>\w+)" if k not in seen else rf"(?P={k})")
                seen.add(k)
            else:
                parts.append(re.escape(tok))
        m = re.fullmatch("".join(parts), text)
        if m:
            g = m.groupdict()
            terms = [g[k] for k in ("A", "B", "C") if g.get(k)]
            if len(set(terms)) == len(terms):
                return "valid" if valid else "invalid"
    return None


def _weekday_answer(text: str) -> str | None:
    days = [d for d in CP.WEEKDAYS if contains_word(text, d)]
    nums = re.findall(r"\d+", text)
    if len(days) != 1 or len(nums) != 1:
        return None
    start = CP.WEEKDAYS.index(days[0]) + (1 if text.startswith("Yesterday was") else 0)
    return CP.WEEKDAYS[(start + int(nums[0])) % 7]


@solver("rb_computed_weekday")
def _weekday(it):
    return _weekday_answer(_text(it))


@solver("rb_computed_weekday_weekend")
def _weekend(it):
    d = _weekday_answer(_text(it))
    return None if d is None else ("a weekend day" if d in ("Saturday", "Sunday") else "a weekday")


# ------------------------------------------------------------------ SURFACE
@solver("rb_surface_contains_digit")
def _digit(it):
    return "contains a digit" if re.search(r"\d", _text(it)) else "contains no digit"


@solver("rb_surface_allcaps_word")
def _caps(it):
    toks = re.findall(r"[A-Za-z]{2,}", _text(it))
    return "contains a word in capitals" if any(t.isupper() for t in toks) else "contains no word in capitals"


@solver("rb_surface_bigram_at_least")
def _bigram(it):
    return "at least" if "at least" in _text(it) else "no such phrase"


@solver("rb_surface_code_language")
def _code(it):
    t = _text(it)
    js = ";" in t or "{" in t or "const " in t or "function " in t or "console.log" in t
    py = re.search(r":\n", t) is not None or "def " in t or "print(" in t
    return "JavaScript" if js and not py else "Python" if py and not js else None


@solver("rb_surface_word_count")
def _wc(it):
    n = len(_text(it).split())
    return "a short sentence" if n == 7 else "a long sentence" if n == 15 else None


# ------------------------------------------------------------------ TOPIC
def _frame_regex(frame: str, pools: dict[str, list[str]]) -> re.Pattern:
    pat = re.escape(frame)
    for k, vals in pools.items():
        pat = pat.replace(re.escape("{" + k + "}"), "(?:" + "|".join(re.escape(v) for v in vals) + ")")
    return re.compile(pat, flags=re.IGNORECASE)


_NEWS_RX = {t: [_frame_regex(f, pools) for f in frames] for t, (frames, pools) in TP.NEWS.items()}


def _news_topic(text: str) -> str | None:
    body = text
    for d in TP.DATELINES:
        if d and text.startswith(d):
            body = text[len(d):]
            break
    hits = [t for t, rxs in _NEWS_RX.items() if any(rx.fullmatch(body) for rx in rxs)]
    return hits[0] if len(hits) == 1 else None


@solver("rb_topic_news_8", "rb_topic_sports_vs_politics", "rb_topic_science_vs_business")
def _news(it):
    return _news_topic(_text(it))


@solver("rb_topic_is_health")
def _health(it):
    t = _news_topic(_text(it))
    return None if t is None else ("health" if t == "health" else "something else")


@solver("rb_topic_review_sentiment")
def _review(it):
    t = _text(it)
    pos = any(contains_word(t, a) for a in TP.POS_ADJ) or any(v in t for v in TP.POS_V)
    neg = any(contains_word(t, a) for a in TP.NEG_ADJ) or any(v in t for v in TP.NEG_V)
    # "would gladly recommend" contains "recommend", and "cannot recommend" contains it too: decide by the adjective
    adj_pos = any(contains_word(t, a) for a in TP.POS_ADJ)
    adj_neg = any(contains_word(t, a) for a in TP.NEG_ADJ)
    return "positive" if adj_pos and not adj_neg else "negative" if adj_neg and not adj_pos else None


_TWEET_RX = {e: [_frame_regex(f, {"T": TP.TWEET_T, "H": TP.TWEET_H}) for f in frames] for e, frames in TP.TWEETS.items()}


@solver("rb_topic_tweet_emotion_4", "rb_topic_tweet_joy_vs_anger")
def _tweet(it):
    hits = [e for e, rxs in _TWEET_RX.items() if any(rx.fullmatch(_text(it)) for rx in rxs)]
    return hits[0] if len(hits) == 1 else None


# ------------------------------------------------------------------ FORM
_PLURAL_NOUNS = {p for _, p in FM.NOUNS}
_SING_NOUNS = {s for s, _ in FM.NOUNS}
_V3 = {v3 for v3, _ in FM.VERBS_SV}
_VBASE = {vb for _, vb in FM.VERBS_SV}


@solver("rb_form_grammatical")
def _grammatical(it):
    text = _text(it)
    words = re.findall(r"[A-Za-z]+", text)
    low = [w.lower() for w in words]
    # reflexive
    if "himself" in low or "herself" in low:
        name = words[0]
        male = name in T.MALE_NAMES
        return "grammatical" if (("himself" in low) == male) else "ungrammatical"
    # determiner
    if low[0] in ("this", "these", "that", "those"):
        noun = low[1]
        plural = noun in _PLURAL_NOUNS
        det_plural = low[0] in ("these", "those")
        return "grammatical" if plural == det_plural else "ungrammatical"
    # auxiliary / agreement: "The N V ..."
    noun = low[1]
    plural = noun in _PLURAL_NOUNS
    verb = low[2]
    if verb in ("has", "have"):
        return "grammatical" if (verb == "have") == plural else "ungrammatical"
    if verb in _V3 or verb in _VBASE:
        return "grammatical" if (verb in _VBASE) == plural else "ungrammatical"
    return None


@solver("rb_form_question_vs_statement")
def _question(it):
    return "a question" if _text(it).endswith("?") else "a statement"


@solver("rb_form_register")
def _register(it):
    t = _text(it)
    informal = any(tok in t for tok in (" u ", "thx", "pls", "lol", ":)", "yo,", "hey", "??"))
    return "informal" if informal else "formal"


@solver("rb_form_voice")
def _voice(it):
    return "passive voice" if re.search(r"\bwas \w+ by\b", _text(it)) else "active voice"


@solver("rb_form_person")
def _person(it):
    return "first person" if _text(it).startswith("I ") else "third person"


@solver("rb_form_negation")
def _negation(it):
    t = _text(it)
    return "negated" if (" not " in t or "cannot" in t) else "affirmative"


# ------------------------------------------------------------------ META
@solver("rb_meta_question_type_3")
def _qtype(it):
    t = _text(it)
    for p in ME.Q_PREFIX:
        if p and t.startswith(p):
            t = t[len(p):]
            break
    t = t.lower()
    if t.startswith("how many"):
        return "how many"
    if t.startswith("why") or t.startswith("for what reason") or t.startswith("explain why"):
        return "why"
    if t.startswith("when") or t.startswith("at what time") or t.startswith("on what date"):
        return "when"
    return None


@solver("rb_meta_why_vs_when")
def _why_when(it):
    q = _qtype(it)
    return "a why question" if q == "why" else "a when question" if q == "when" else None


@solver("rb_meta_instruction_present")
def _instruction(it):
    first = _text(it).split("\n", 1)[0]
    return "contains an instruction" if first in ME.INSTRUCTIONS else "contains no instruction"


@solver("rb_meta_answer_format")
def _format(it):
    t = _text(it)
    if any(t.endswith(s) for s in ME.ONE_WORD):
        return "one word"
    if any(t.endswith(s) for s in ME.FULL):
        return "a full sentence"
    return None


# ------------------------------------------------------------------ INTERNAL (the PROVISIONAL label; the model's own is collected later)
@solver("rb_internal_puzzle_answer")
def _puzzle(it):
    text = _text(it)
    rules = dict(re.findall(r"\b([A-H]) -> ([A-H])\b", text))
    m = re.search(r"(?:Start at|Starting from|Begin at|From) ([A-H])\b", text)
    if not rules or not m:
        return None
    x = m.group(1)
    for _ in range(3):
        x = rules[x]
    return x


_SENSITIVE = {frame.format(X=s) for frame, _b, s in IN.REFUSAL_PAIRS}
_BENIGN = {frame.format(X=b) for frame, b, _s in IN.REFUSAL_PAIRS}


@solver("rb_internal_refusal")
def _refusal(it):
    t = _text(it)
    for p in IN.REFUSAL_PREFIX:
        if p and t.startswith(p):
            t = t[len(p):]
            break
    return "refuse" if t in _SENSITIVE else "comply" if t in _BENIGN else None


_UNKNOWABLE_RX = [_frame_regex(f, {"P": T.SCIENTISTS + T.COMPOSERS, "Z": [c.capital for c in T.COUNTRIES if c.capital]}) for f in IN.UNKNOWABLE]
_ANSWERABLE_RX = [_frame_regex(f, {"C": [c.name for c in T.COUNTRIES]}) for f in IN.ANSWERABLE]


@solver("rb_internal_abstain")
def _abstain(it):
    t = _text(it)
    for p in IN.ABSTAIN_PREFIX:
        if p and t.startswith(p):
            t = t[len(p):]
            break
    if any(rx.fullmatch(t) for rx in _UNKNOWABLE_RX):
        return "says it does not know"
    if any(rx.fullmatch(t) for rx in _ANSWERABLE_RX):
        return "gives a confident answer"
    return None


@solver("rb_internal_self_choice")
def _choice(it):
    m = re.search(r"\b(\w+) (?:or|and) (\w+)[?.]", _text(it))
    return m.group(1) if m else None


# ------------------------------------------------------------------ CONTEXT
def _binding_answer(preamble: str, visible: str) -> str | None:
    q = re.fullmatch(r"Who (.+)\? Answer with the name only\.", visible)
    if not q:
        return None
    pred = q.group(1)   # e.g. "has the red pen", "lives in Lyon"
    hits = re.findall(r"\b([A-Z][a-z]+) " + re.escape(pred) + r"\b", preamble)
    return hits[0] if len(hits) == 1 else None


@solver("rb_context_system_fact")
def _system_fact(it):
    return _binding_answer(it["system"] or "", _text(it))


@solver("rb_context_earlier_turn")
def _earlier(it):
    msgs = it.get("capture_messages") or []
    if len(msgs) != 3 or msgs[0]["role"] != "user" or msgs[2]["content"] != _text(it):
        return None
    return _binding_answer(msgs[0]["content"], _text(it))


@solver("rb_context_against_belief")
def _belief(it):
    m = re.search(r"capital of (.+?) is ([^.]+)\.|treat ([^.]+?) as the capital of (.+?)\.", it["system"] or "")
    if not m:
        return None
    return m.group(2) if m.group(2) else m.group(3)


# ------------------------------------------------------------------ round trip
def roundtrip(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per dataset: n, n_solved, disagreements (item ids, first 5). Raises KeyError for a dataset without a solver."""
    out: dict[str, dict[str, Any]] = {}
    for it in items:
        ds = it["dataset"]
        r = out.setdefault(ds, {"n": 0, "n_solved": 0, "disagree": []})
        r["n"] += 1
        got = SOLVERS[ds](it)
        if got is None:
            r["disagree"].append((it["item_id"], None, it["primary"]["answer"]))
        else:
            r["n_solved"] += 1
            if got != it["primary"]["answer"]:
                r["disagree"].append((it["item_id"], got, it["primary"]["answer"]))
    for r in out.values():
        r["ok"] = not r["disagree"]
        r["disagree"] = r["disagree"][:5]
    return out
