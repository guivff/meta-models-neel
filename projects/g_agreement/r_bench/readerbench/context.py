"""CONTEXT: the fact is in the conversation but not in the visible prompt (PLAN_R §7; V7 generalised).

system_fact     five relation types (has the object / lives in / works as / owns a pet / plays an instrument); the two
                bindings sit ONLY in the system turn ("Background: Emma has the red pen. Anna has the blue cup."); the
                visible prompt asks "Who has the red pen? Answer with the name only."; candidates = the two names (per
                item, order counterbalanced); answer first-mentioned in the preamble balanced.
earlier_turn    the same facts stated in an EARLIER USER TURN (user: note, assistant: "Noted.", user: question);
                ``capture_messages`` holds the full conversation, ``prompt_text`` the last user turn, ``system`` None.
against_belief  R-C2 style: the system turn asserts a false capital the model knows to be false ("For this conversation,
                assume that the capital of Australia is Sydney."); candidates = (context answer, true capital).
                label_source "model": provisional label = the context answer (compliance); the collector replaces it
                with the model's prompt-only greedy choice, and non-compliers are the control (BRIEF_R §3 R-C2).

Ground truth: the binding written into the preamble (system_fact / earlier_turn) or tables.py (against_belief).
"""

from __future__ import annotations

from projects.g_agreement.r_bench.readerbench import tables as T
from projects.g_agreement.r_bench.readerbench.common import Draft, Fact, balanced_bools, balanced_levels, fresh, rng_for

RELATIONS: dict[str, dict[str, object]] = {
    "has_object": {"stmt": "{N} has the {V}", "q": "Who has the {V}?", "values": ["red pen", "blue cup", "green book", "black bag", "white hat",
                                                                                 "brown box", "grey coat", "yellow lamp", "pink scarf", "silver key"]},
    "lives_in": {"stmt": "{N} lives in {V}", "q": "Who lives in {V}?", "values": ["Lyon", "Porto", "Graz", "Leeds", "Bergen", "Ghent", "Turin", "Basel",
                                                                                 "Cork", "Malmö"]},
    "works_as": {"stmt": "{N} works as a {V}", "q": "Who works as a {V}?", "values": ["baker", "nurse", "pilot", "lawyer", "farmer", "dentist", "plumber",
                                                                                     "tailor", "chemist", "florist"]},
    "owns_pet": {"stmt": "{N} owns a {V}", "q": "Who owns a {V}?", "values": ["parrot", "rabbit", "tortoise", "goldfish", "hamster", "ferret", "canary",
                                                                            "gecko", "pony", "poodle"]},
    "plays": {"stmt": "{N} plays the {V}", "q": "Who plays the {V}?", "values": ["violin", "cello", "trumpet", "piano", "flute", "harp", "drums", "oboe",
                                                                                "banjo", "guitar"]},
}
PREAMBLES = ["Background: {S1}. {S2}.", "Context for this conversation: {S1}. {S2}."]
EARLIER = ["Please remember this: {S1}. {S2}.", "Note for later: {S1}. {S2}."]
VISIBLE_SUFFIX = " Answer with the name only."
BELIEF_PREAMBLES = ["For this conversation, assume that the capital of {C} is {X}.",
                    "In this conversation, treat {X} as the capital of {C}."]
BELIEF_VISIBLE = ["What is the capital of {C}? Answer with the city only.", "Name the capital of {C}. Answer with the city only."]

FACTS: list[Fact] = [
    Fact("rb_context_system_fact", "CONTEXT", "Who is the answer to the question?", "the name bound to the asked value in the system turn",
         "the other name", "The answer is {X}.", per_item_candidates=True,
         ground_truth="the binding written in the system turn (five relation types); the visible prompt has no binding",
         readout="the model's greedy name", balanced_factors=("relation", "preamble", "answer_first_mentioned", "answer_position")),
    Fact("rb_context_earlier_turn", "CONTEXT", "Who is the answer to the question?", "the name bound to the asked value in the earlier turn",
         "the other name", "The answer is {X}.", per_item_candidates=True,
         ground_truth="the binding stated in an earlier user turn (capture_messages); prompt_text is the last turn only",
         readout="the model's greedy name", balanced_factors=("relation", "preamble", "answer_first_mentioned", "answer_position")),
    Fact("rb_context_against_belief", "CONTEXT", "What is the capital according to this conversation?", "the context's (false) capital",
         "the true capital (the model's belief)", "The capital is {X}.", per_item_candidates=True, label_source="model",
         ground_truth="provisional: the city asserted in the system turn; final: the model's prompt-only greedy choice (compliers vs non-compliers)",
         readout="greedy city", balanced_factors=("preamble", "visible", "answer_position")),
]


def _binding_items(seed: int, fact_id: str, preambles: list[str], as_system: bool) -> list[Draft]:
    rng = rng_for(seed, fact_id)
    n = 240
    rels = balanced_levels(list(RELATIONS), n, rng)
    pre = balanced_levels([0, 1], n, rng)
    ans_first_mentioned = balanced_bools(n, rng)
    cand_first = balanced_bools(n, rng)
    seen: set[tuple[str, str]] = set()
    out = []
    for i in range(n):
        rel = RELATIONS[rels[i]]
        for _ in range(500):
            n1, n2 = rng.sample(T.NAMES, 2)            # n1 = the answer, n2 = the other
            v1, v2 = rng.sample(rel["values"], 2)      # v1 = the asked value
            first, second = ((n1, v1), (n2, v2)) if ans_first_mentioned[i] else ((n2, v2), (n1, v1))
            s1 = str(rel["stmt"]).format(N=first[0], V=first[1])
            s2 = str(rel["stmt"]).format(N=second[0], V=second[1])
            preamble = preambles[pre[i]].format(S1=s1, S2=s2)
            visible = str(rel["q"]).format(V=v1) + VISIBLE_SUFFIX
            if (preamble, visible) not in seen:
                break
        else:
            raise RuntimeError("fresh binding not found")
        seen.add((preamble, visible))
        cands, label = ([n1, n2], 1) if cand_first[i] else ([n2, n1], 0)
        c = {"relation": rels[i], "preamble": pre[i], "names": [first[0], second[0]], "values": [first[1], second[1]],
             "answer_first_mentioned": ans_first_mentioned[i], "answer_position": 0 if cand_first[i] else 1, "ground_truth": n1,
             "preamble_text": preamble}
        if as_system:
            out.append(Draft(visible, label, n1, cands, c, system=preamble))
        else:
            out.append(Draft(visible, label, n1, cands, c, system=None,
                             messages=[{"role": "user", "content": preamble}, {"role": "assistant", "content": "Noted."},
                                       {"role": "user", "content": visible}]))
    return out


def build_against_belief(seed: int) -> list[Draft]:
    rng = rng_for(seed, "rb_context_against_belief")
    cs = [c for c in T.COUNTRIES if c.capital and c.other_city]
    rows = [(c, p, v) for c in cs for p in (0, 1) for v in (0, 1)]
    n = len(rows)
    first = balanced_bools(n, rng)
    out = []
    for i, (c, p, v) in enumerate(rows):
        system = BELIEF_PREAMBLES[p].format(C=c.name, X=c.other_city)
        visible = BELIEF_VISIBLE[v].format(C=c.name)
        cands, label = ([c.other_city, c.capital], 1) if first[i] else ([c.capital, c.other_city], 0)
        out.append(Draft(visible, label, c.other_city, cands, {"preamble": p, "visible": v, "country": c.name, "true_capital": c.capital,
                                                                  "context_capital": c.other_city, "answer_position": 0 if first[i] else 1,
                                                                  "ground_truth": c.other_city}, system=system, group=c.name))
    return out


def build(seed: int) -> dict[str, list[Draft]]:
    return {"rb_context_system_fact": _binding_items(seed, "rb_context_system_fact", PREAMBLES, True),
            "rb_context_earlier_turn": _binding_items(seed, "rb_context_earlier_turn", EARLIER, False),
            "rb_context_against_belief": build_against_belief(seed)}
