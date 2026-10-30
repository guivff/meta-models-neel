"""KHOP: 2- and 3-hop compositions over the KNOWLEDGE tables; the bridge entity is never in the text (PLAN_R §5, §7).

Texts are incomplete sentences ending right before the answer ("The capital of the country that is home to the Louvre
is"), so the raw render's last token is the position where the model must have computed the bridge. Two facts share
every text: the BRIDGE fact (candidates = bridge country vs a distractor country of the same continent) and the ANSWER
fact (the final attribute vs the distractor's attribute). Candidates are per item (``per_item_candidates``), their
order counterbalanced (answer first on exactly half the items); the split groups all 8 templates of a landmark
together, so no landmark sits in both test and pool.

Distractor rule: same continent, different value of the hop-2 attribute, closest name length (ties seeded); the
distractor never appears in the text either (asserted). Ground truth: the tables in ``tables.py`` (textbook facts).
Behavioural readout (collect): the model's greedy completion / prompt-only choice; items the model gets right are the
"bridge is computed" set, the wrong ones the conflict subset (selection on the model only, recorded by WS2/WS3).
"""

from __future__ import annotations

import random

from projects.g_agreement.r_bench.readerbench import tables as T
from projects.g_agreement.r_bench.readerbench.common import (Draft, Fact, balanced_bools, cap_first, contains_word,
                                                              rng_for)

CAPITAL_TEMPLATES = [
    "The capital of the country that is home to {L} is",
    "The capital city of the country where {L} stands is",
    "{L} is in a country whose capital is",
    "The nation that contains {L} has as its capital the city of",
    "Tourists who visit {L} are in a country whose capital is",
    "The country in which {L} is located has its capital in",
    "If you travel to {L}, you are in a country whose capital city is",
    "The seat of government of the country that is home to {L} is",
]
CURRENCY_TEMPLATES = [
    "The currency of the country where {L} stands is",
    "Visitors to {L} pay in the local currency, which is",
    "The money used in the country that is home to {L} is",
    "The official currency of the country in which {L} is located is",
    "{L} is in a country whose currency is",
    "Shops near {L} accept the national currency, which is",
    "The country that contains {L} uses as its currency",
    "Anyone travelling to {L} will need the local currency, namely",
]
LANGUAGE_TEMPLATES = [
    "The main language spoken in the country whose capital is {C} is",
    "In the country whose capital city is {C}, most people speak",
    "The national language of the country governed from {C} is",
    "Residents of the country whose capital is {C} mostly speak",
    "The country with its capital at {C} has as its main language",
    "If a country's capital is {C}, its main language is",
    "The official language of the country whose capital city is {C} is",
    "People in the country whose seat of government is {C} speak",
]
THREE_HOP_TEMPLATES = [
    "The currency of the country whose capital is home to {L} is",
    "The money used in the country whose capital city contains {L} is",
    "{L} stands in a capital city; the currency of that city's country is",
    "The country whose capital is home to {L} uses as its currency",
    "{L} is in a capital city, and the currency of that country is",
    "The capital city that contains {L} belongs to a country whose currency is",
    "Visitors to {L} are in a national capital; the country's currency is",
    "The money used in the country whose capital is home to {L} is",
]

FACTS: list[Fact] = [
    Fact("rb_khop_landmark_capital_bridge", "KHOP", "Which country is this sentence about?", "the bridge country",
         "a same-continent distractor country", "The country is {X}.", per_item_candidates=True,
         ground_truth="landmark -> country (tables.py); the country is never in the text",
         readout="greedy completion of the sentence (the capital); correct iff the bridge was computed",
         balanced_factors=("template", "answer_position"), shares_text_with=("rb_khop_landmark_capital_answer",)),
    Fact("rb_khop_landmark_capital_answer", "KHOP", "Which city correctly completes the sentence?", "the capital of the bridge country",
         "the capital of the distractor country", "The capital is {X}.", per_item_candidates=True,
         ground_truth="landmark -> country -> capital", readout="greedy completion",
         balanced_factors=("template", "answer_position"), shares_text_with=("rb_khop_landmark_capital_bridge",)),
    Fact("rb_khop_landmark_currency_bridge", "KHOP", "Which country is this sentence about?", "the bridge country",
         "a same-continent distractor country with a different currency", "The country is {X}.", per_item_candidates=True,
         ground_truth="landmark -> country; distractor's currency differs", readout="greedy completion (the currency)",
         balanced_factors=("template", "answer_position"), shares_text_with=("rb_khop_landmark_currency_answer",)),
    Fact("rb_khop_landmark_currency_answer", "KHOP", "Which currency correctly completes the sentence?", "the currency of the bridge country",
         "the currency of the distractor country", "The currency is {X}.", per_item_candidates=True,
         ground_truth="landmark -> country -> currency", readout="greedy completion",
         balanced_factors=("template", "answer_position"), shares_text_with=("rb_khop_landmark_currency_bridge",)),
    Fact("rb_khop_capital_language_bridge", "KHOP", "Which country is this sentence about?", "the bridge country",
         "a same-continent distractor country with a different main language", "The country is {X}.", per_item_candidates=True,
         ground_truth="capital -> country (the text names the capital, never the country)", readout="greedy completion (the language)",
         balanced_factors=("template", "answer_position"), shares_text_with=("rb_khop_capital_language_answer",)),
    Fact("rb_khop_capital_language_answer", "KHOP", "Which language correctly completes the sentence?", "the main language of the bridge country",
         "the main language of the distractor country", "The language is {X}.", per_item_candidates=True,
         ground_truth="capital -> country -> main language", readout="greedy completion",
         balanced_factors=("template", "answer_position"), shares_text_with=("rb_khop_capital_language_bridge",)),
    Fact("rb_khop_3hop_middle", "KHOP", "Which country is this sentence about?", "the middle country (landmark -> capital -> country)",
         "a same-continent distractor country with a different currency", "The country is {X}.", per_item_candidates=True,
         ground_truth="landmark (in a capital) -> capital -> country -> currency; the middle country is the target; small set",
         readout="greedy completion (the currency)", balanced_factors=("template", "answer_position"),
         note="3-hop variant, 17 landmarks x 8 templates = 136 items; descriptive-only (test < 100)"),
]
_BY_ID = {f.id: f for f in FACTS}


def _attr(c: T.Country, attr: str) -> str | None:
    return {"capital": c.capital, "currency": c.currency, "language": c.language}[attr]


def _strip_the(s: str) -> str:
    return s[4:] if s.startswith("the ") else s


def distractors(c: T.Country, attr: str, text: str, k: int = 3) -> list[T.Country]:
    """Same-continent countries with a different ``attr`` value, neither named in the text, by closeness of name length."""
    out = []
    for d in T.COUNTRIES:
        if d.name == c.name or d.continent != c.continent or _attr(d, attr) is None or _attr(d, attr) == _attr(c, attr):
            continue
        if contains_word(text, T.bare(d.name)) or contains_word(text, _strip_the(_attr(d, attr))):
            continue
        out.append(d)
    out.sort(key=lambda d: (abs(len(T.bare(d.name)) - len(T.bare(c.name))), d.name))
    return out[:k]


def _texts(templates: list[str], subjects: list[tuple[T.Country, str]], key: str) -> list[tuple[T.Country, str, int, str]]:
    """(country, text, template_index, group) for every subject x template; the subject string fills {L} or {C}."""
    rows = []
    for c, s in subjects:
        for ti, tmpl in enumerate(templates):
            text = tmpl.replace("{" + key + "}", s)
            rows.append((c, cap_first(text) if text.startswith(s) else text, ti, s))
    return rows


def _two_facts(rng: random.Random, rows: list[tuple[T.Country, str, int, str]], attr: str, bridge_id: str, answer_id: str
               ) -> dict[str, list[Draft]]:
    # subjects without any eligible distractor (e.g. Australia / New Zealand share English in Oceania) are dropped whole,
    # so every kept subject still carries all its templates (template balance)
    dropped = {c.name for c, text, _ti, _s in rows if not distractors(c, attr, text)}
    rows = [r for r in rows if r[0].name not in dropped]
    first_b = balanced_bools(len(rows), rng)
    first_a = balanced_bools(len(rows), rng)
    out: dict[str, list[Draft]] = {k: [] for k in (bridge_id, answer_id) if k in _BY_ID}
    for i, (c, text, ti, subj) in enumerate(rows):
        ds = distractors(c, attr, text)
        d = ds[(ti + i) % len(ds)]
        base = {"template": ti, "subject": subj, "bridge": c.name, "distractor": d.name, "attribute": attr,
                "name_len_diff": len(T.bare(d.name)) - len(T.bare(c.name)), "dropped_subjects": sorted(dropped)}
        for fid, ans, other, first in ((bridge_id, T.bare(c.name), T.bare(d.name), first_b[i]),
                                       (answer_id, _attr(c, attr), _attr(d, attr), first_a[i])):
            if fid not in out:
                continue
            assert not contains_word(text, ans) and not contains_word(text, other), (fid, text, ans, other)
            cands, label = ([ans, other], 1) if first else ([other, ans], 0)
            out[fid].append(Draft(text, label, ans, cands, {**base, "answer_position": 0 if first else 1, "ground_truth": ans},
                                  group=c.name, jlens=[_strip_the(x) for x in cands]))
    return {k: v for k, v in out.items() if v}


def build(seed: int) -> dict[str, list[Draft]]:
    out: dict[str, list[Draft]] = {}
    lm = [(c, c.landmark) for c in T.with_landmark()]
    cap_rows = _texts(CAPITAL_TEMPLATES, lm, "L")
    out.update(_two_facts(rng_for(seed, "rb_khop_landmark_capital"), cap_rows, "capital",
                          "rb_khop_landmark_capital_bridge", "rb_khop_landmark_capital_answer"))
    cur_rows = _texts(CURRENCY_TEMPLATES, lm, "L")
    out.update(_two_facts(rng_for(seed, "rb_khop_landmark_currency"), cur_rows, "currency",
                          "rb_khop_landmark_currency_bridge", "rb_khop_landmark_currency_answer"))
    # capital -> country -> language: the capital must not contain the country name (Mexico City) and the language must exist
    lang_subjects = [(c, c.capital) for c in T.COUNTRIES
                     if c.capital and c.language and not contains_word(c.capital, T.bare(c.name))]
    lang_rows = _texts(LANGUAGE_TEMPLATES, lang_subjects, "C")
    out.update(_two_facts(rng_for(seed, "rb_khop_capital_language"), lang_rows, "language",
                          "rb_khop_capital_language_bridge", "rb_khop_capital_language_answer"))
    # 3-hop: landmark in the capital -> capital -> country -> currency; target = the middle country
    three = [(c, c.landmark) for c in T.with_landmark(in_capital=True)]
    rows3 = _texts(THREE_HOP_TEMPLATES, three, "L")
    out.update(_two_facts(rng_for(seed, "rb_khop_3hop"), rows3, "currency", "rb_khop_3hop_middle", "__unused__"))
    for fid in out:
        assert fid in _BY_ID, fid
    return out
