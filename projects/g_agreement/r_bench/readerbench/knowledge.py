"""KNOWLEDGE: entity -> recalled attribute; the text is a bare entity name in one of four frames, the label is never in
the text (PLAN_R §7). Five fixed-candidate binary facts (both classes real concepts, SAE-probing style) and two
per-item distractor facts (entity -> attribute vs the same attribute of a same-type distractor).

The four frames of one entity form a split group (an entity is never in both test and pool). Fixed-candidate facts
are balanced by subsampling the larger class (seeded). Ground truth: tables.py.
"""

from __future__ import annotations

from projects.g_agreement.r_bench.readerbench import tables as T
from projects.g_agreement.r_bench.readerbench.common import Draft, Fact, balanced_bools, cap_first, contains_word, rng_for

FRAMES = ["{e}", "{Kind}: {e}", "Consider {E}.", "Here is {a_kind}: {E}.",            # e = bare name, E = name with article
          "Think about {E}.", "Name: {e}", "{E}, for example.", "The {kind_l} in question is {E}."]   # 8 frames (review fix item 5)

FACTS: list[Fact] = [
    Fact("rb_knowledge_country_continent", "KNOWLEDGE", "Is this country in Europe or in Asia?", "Europe", "Asia",
         "The country is in {X}.", ground_truth="tables.py continent; transcontinental countries excluded",
         balanced_factors=("frame",), shares_text_with=("rb_knowledge_country_capital_distractor",)),
    Fact("rb_knowledge_city_is_capital", "KNOWLEDGE", "Is this city a national capital?", "a national capital",
         "not a national capital", "The city is {X}.", sided="one", jlens_pos="capital",
         ground_truth="tables.py capital vs other_city of the same countries", balanced_factors=("frame",)),
    Fact("rb_knowledge_element_metal", "KNOWLEDGE", "Is this chemical element a metal or a nonmetal?", "a metal", "a nonmetal",
         "The element is {X}.", jlens_pos="metal", jlens_neg="carbon",   # 'nonmetal' is multi-token; carbon = the prototypical nonmetal
         ground_truth="tables.py METALS vs NONMETALS (metalloids excluded)", balanced_factors=("frame",)),
    Fact("rb_knowledge_figure_field", "KNOWLEDGE", "Was this person a scientist or a composer?", "a scientist", "a composer",
         "The person was {X}.", jlens_pos="scientist", jlens_neg="composer",
         ground_truth="tables.py SCIENTISTS vs COMPOSERS", balanced_factors=("frame",)),
    Fact("rb_knowledge_animal_class", "KNOWLEDGE", "Is this animal a mammal or a bird?", "a mammal", "a bird",
         "The animal is {X}.", jlens_pos="mammals", jlens_neg="birds",   # 'mammal' is multi-token, the plural is one token
         ground_truth="tables.py MAMMALS vs BIRDS", balanced_factors=("frame",)),
    Fact("rb_knowledge_country_capital_distractor", "KNOWLEDGE", "What is the capital of this country?", "the capital",
         "the capital of a same-continent distractor country", "The capital is {X}.", per_item_candidates=True,
         ground_truth="tables.py capital; distractor = same continent, closest name length",
         balanced_factors=("frame", "answer_position"), shares_text_with=("rb_knowledge_country_continent",)),
    Fact("rb_knowledge_landmark_country_distractor", "KNOWLEDGE", "In which country is this landmark?", "the country",
         "a same-continent distractor country", "The landmark is in {X}.", per_item_candidates=True,
         ground_truth="tables.py landmark -> country; neither candidate appears in the text",
         balanced_factors=("frame", "answer_position")),
]


def frames_for(e_bare: str, e_full: str, kind: str) -> list[tuple[int, str]]:
    a_kind = ("an " if kind[0].lower() in "aeiou" else "a ") + kind.lower()
    return [(i, cap_first(f.format(e=e_bare, E=e_full, Kind=kind, a_kind=a_kind, kind_l=kind.lower()))) for i, f in enumerate(FRAMES)]


def _fixed(fact_id: str, seed: int, kind: str, pos_entities: list[str], neg_entities: list[str], pos: str, neg: str,
           full: dict[str, str] | None = None) -> list[Draft]:
    rng = rng_for(seed, fact_id)
    n = min(len(pos_entities), len(neg_entities))
    pos_e = sorted(rng.sample(pos_entities, n))
    neg_e = sorted(rng.sample(neg_entities, n))
    out = []
    for ents, ans, label in ((pos_e, pos, 1), (neg_e, neg, 0)):
        for e in ents:
            e_full = (full or {}).get(e, e)
            for fi, text in frames_for(e, e_full, kind):
                assert not contains_word(text, ans.split()[-1]), (fact_id, text, ans)
                out.append(Draft(text, label, ans, None, {"frame": fi, "entity": e, "kind": kind, "ground_truth": ans}, group=e))
    return out


def _closest(c: T.Country, pool: list[T.Country], attr: str, rng, k: int = 3) -> T.Country:
    cands = [d for d in pool if d.name != c.name and d.continent == c.continent and getattr(d, attr) and getattr(d, attr) != getattr(c, attr)]
    cands.sort(key=lambda d: (abs(len(T.bare(d.name)) - len(T.bare(c.name))), d.name))
    return rng.choice(cands[:k])


def build(seed: int) -> dict[str, list[Draft]]:
    out: dict[str, list[Draft]] = {}
    full = {T.bare(c.name): c.name for c in T.COUNTRIES}
    eu = [T.bare(c.name) for c in T.COUNTRIES if c.continent == "Europe" and not c.transcontinental]
    asia = [T.bare(c.name) for c in T.COUNTRIES if c.continent == "Asia" and not c.transcontinental]
    out["rb_knowledge_country_continent"] = _fixed("rb_knowledge_country_continent", seed, "Country", eu, asia, "Europe", "Asia", full)
    caps = [c.capital for c in T.COUNTRIES if c.capital]
    others = [c.other_city for c in T.COUNTRIES]
    out["rb_knowledge_city_is_capital"] = _fixed("rb_knowledge_city_is_capital", seed, "City", caps, others,
                                                "a national capital", "not a national capital")
    out["rb_knowledge_element_metal"] = _fixed("rb_knowledge_element_metal", seed, "Element", T.METALS, T.NONMETALS, "a metal", "a nonmetal")
    out["rb_knowledge_figure_field"] = _fixed("rb_knowledge_figure_field", seed, "Person", T.SCIENTISTS, T.COMPOSERS, "a scientist", "a composer")
    out["rb_knowledge_animal_class"] = _fixed("rb_knowledge_animal_class", seed, "Animal", T.MAMMALS, T.BIRDS, "a mammal", "a bird",
                                              full={a: f"the {a}" for a in T.MAMMALS + T.BIRDS})   # "Consider the wolf." (review fix item 4)

    # per-item distractor facts
    rng = rng_for(seed, "rb_knowledge_country_capital_distractor")
    cs = [c for c in T.COUNTRIES if c.capital and not contains_word(c.capital, T.bare(c.name))]
    rows = [(c, fi, text) for c in cs for fi, text in frames_for(T.bare(c.name), c.name, "Country")]
    first = balanced_bools(len(rows), rng)
    drafts = []
    for i, (c, fi, text) in enumerate(rows):
        d = _closest(c, cs, "capital", rng)
        assert not contains_word(text, c.capital) and not contains_word(text, d.capital), (text, c.capital, d.capital)
        cands, label = ([c.capital, d.capital], 1) if first[i] else ([d.capital, c.capital], 0)
        drafts.append(Draft(text, label, c.capital, cands, {"frame": fi, "entity": c.name, "distractor": d.name,
                                                             "answer_position": 0 if first[i] else 1, "ground_truth": c.capital}, group=c.name))
    out["rb_knowledge_country_capital_distractor"] = drafts

    rng = rng_for(seed, "rb_knowledge_landmark_country_distractor")
    lms = T.with_landmark()
    rows = [(c, fi, text) for c in lms for fi, text in frames_for(c.landmark, c.landmark, "Landmark")]
    first = balanced_bools(len(rows), rng)
    drafts = []
    for i, (c, fi, text) in enumerate(rows):
        d = _closest(c, T.COUNTRIES, "capital", rng)
        ans, other = T.bare(c.name), T.bare(d.name)
        assert not contains_word(text, ans) and not contains_word(text, other), (text, ans, other)
        cands, label = ([ans, other], 1) if first[i] else ([other, ans], 0)
        drafts.append(Draft(text, label, ans, cands, {"frame": fi, "entity": c.landmark, "distractor": d.name,
                                                      "answer_position": 0 if first[i] else 1, "ground_truth": ans}, group=c.name))
    out["rb_knowledge_landmark_country_distractor"] = drafts
    return out
