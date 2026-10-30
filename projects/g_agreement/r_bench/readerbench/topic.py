"""TOPIC: a semantic category of a generated text (PLAN_R §7).

news_8            templated news-style sentences over 8 topics (3 frames each), k-way; plus two two-sided pairs and
                  one one-sided "about health vs something else" fact (the SAE-probing one-of-k style), on fresh draws
review_sentiment  templated product reviews; the same frames with a positive or a negative adjective / verb pool
tweet_emotion_4   templated tweets over joy / anger / sadness / fear (k-way) and joy vs anger (binary)

Ground truth: the pool the sentence was generated from.
"""

from __future__ import annotations

import random

from projects.g_agreement.r_bench.readerbench.common import Draft, Fact, balanced_bools, balanced_levels, fresh, rng_for

TOPICS = ["sports", "politics", "business", "technology", "science", "health", "entertainment", "weather"]
NEWS: dict[str, tuple[list[str], dict[str, list[str]]]] = {
    "sports": (["{A} beat {B} {S} in the {E} final on {D}.", "{A} signed a new striker ahead of the {E} on {D}.",
                "The {E} opened on {D} with {A} defeating {B} {S}."],
               {"A": ["Arsenal", "Juventus", "the Lakers", "Bayern", "the Celtics", "Ajax", "Boca Juniors", "Leeds"],
                "B": ["Chelsea", "Roma", "the Bulls", "Dortmund", "the Knicks", "Feyenoord", "River Plate", "Everton"],
                "S": ["2-1", "3-0", "1-0", "4-2", "98-91", "2-2 on penalties"], "E": ["cup", "league", "championship", "tournament", "derby"],
                "D": ["Saturday", "Sunday", "Tuesday", "Friday"]}),
    "politics": (["The {P} announced a {N} bill on {I} after talks with the opposition.", "Parliament voted {V} on the {I} reform proposed by the {P}.",
                  "The {P} faces a confidence vote over the {I} budget next week."],
                 {"P": ["prime minister", "senate", "cabinet", "governor", "coalition", "president"], "N": ["new", "revised", "controversial"],
                  "I": ["immigration", "tax", "housing", "pension", "energy", "election"], "V": ["narrowly", "overwhelmingly", "again"]}),
    "business": (["{C} reported a {Q} rise in quarterly profits as {M} sales grew.", "Shares of {C} fell {Q} after the {M} merger collapsed.",
                  "{C} will cut {K} jobs and close its {M} division."],
                 {"C": ["Siemens", "Toyota", "Unilever", "Shell", "Nestlé", "Samsung", "Airbus", "Vodafone"], "Q": ["5%", "12%", "3%", "8%"],
                  "M": ["retail", "overseas", "consumer", "logistics", "insurance"], "K": ["400", "1,200", "900", "2,000"]}),
    "technology": (["{C} unveiled a {A} chip that doubles battery life in {G}.", "A software bug in {C}'s {G} app exposed user {X} for weeks.",
                    "{C} released an update that adds {A} features to its {G} line."],
                   {"C": ["Apple", "Intel", "Nvidia", "Huawei", "Sony", "Dell", "Qualcomm", "Xiaomi"], "A": ["new", "faster", "smaller", "cheaper"],
                    "G": ["laptop", "smartphone", "tablet", "headset", "smartwatch"], "X": ["passwords", "locations", "photos", "messages"]}),
    "science": (["Astronomers detected a {A} {O} orbiting a distant star from {Z}.", "Researchers in {Z} sequenced the genome of a {A} {B} species.",
                 "A {ZA} team measured the {A} {O} with record precision."],
                {"A": ["new", "rare", "massive", "ancient"], "O": ["exoplanet", "comet", "neutron star", "asteroid", "galaxy"],
                 "Z": ["Chile", "Geneva", "Kyoto", "Cambridge", "Pasadena", "Munich"], "ZA": ["Chilean", "Swiss", "Japanese", "British", "Californian", "German"],
                 "B": ["beetle", "fern", "coral", "frog", "moss"]}),
    "health": (["Doctors reported a {A} outbreak of {D} in {Z} hospitals.", "A new {D} vaccine reduced {A2} cases by a third in {Z} trials.",
                "Health officials in {Z} urged {A} screening for {D}."],
               {"A": ["sharp", "seasonal", "early", "rare"], "A2": ["severe", "new", "reported", "hospital"],
                "D": ["measles", "flu", "malaria", "diabetes", "cholera", "asthma"],
                "Z": ["Kenyan", "Texan", "Swedish", "Indian", "Brazilian", "Welsh"]}),
    "entertainment": (["{F} topped the box office on its opening weekend with {A} reviews.", "The singer {N} announced a {A} world tour starting in {Z}.",
                       "{F} won best picture while {N} took home best actor."],
                      {"F": ["The Last Harbour", "Midnight Orchard", "Paper Kings", "Blue Lantern", "The Quiet Room", "Northern Lights"],
                       "A": ["glowing", "mixed", "surprise", "sold-out"], "N": ["Lena Marsh", "Dario Vela", "Ines Kemp", "Rafael Ruiz", "Mira Sato"],
                       "Z": ["Lisbon", "Osaka", "Toronto", "Dublin", "Lima"]}),
    "weather": (["A {A} storm brought {W} to the {Z} coast overnight.", "Forecasters warn of {W} across {Z} regions through {D}.",
                 "{Z} towns recorded {W} as the {A} front moved east on {D}."],
                {"A": ["powerful", "late", "sudden", "slow-moving"], "W": ["heavy snow", "flooding", "gale-force winds", "record heat", "hail"],
                 "Z": ["northern", "coastal", "alpine", "southern", "island"], "D": ["Thursday", "the weekend", "Monday", "tonight"]}),
}
REVIEW_FRAMES = ["The {P} is {A}; {V} it to anyone.", "After a month, the {P} still feels {A} and I {V} it.",
                 "Honestly, this {P} is {A}. Would I {V} it? Yes, without doubt.", "Bought the {P} last week and it is {A}, so I {V} it."]
PRODUCTS = ["blender", "backpack", "headset", "kettle", "jacket", "tripod", "mattress", "keyboard", "lamp", "scooter"]
POS_ADJ = ["excellent", "superb", "reliable", "delightful", "flawless", "wonderful"]
NEG_ADJ = ["terrible", "flimsy", "useless", "disappointing", "defective", "awful"]
POS_V = ["recommend", "would gladly recommend", "happily recommend"]
NEG_V = ["cannot recommend", "would never recommend", "regret buying"]
EMOTIONS = ["joy", "anger", "sadness", "fear"]
TWEETS: dict[str, list[str]] = {
    "joy": ["Just got the {T} news, I can't stop smiling!!! #{H}", "Best {T} day ever, everything went right :) #{H}", "So thrilled about the {T} thing today, pure happiness #{H}"],
    "anger": ["Furious about the {T} mess, this is unacceptable!!! #{H}", "Can't believe they ruined the {T} day AGAIN, so angry #{H}", "Absolutely livid about the {T} situation right now #{H}"],
    "sadness": ["Heartbroken about the {T} news today... miss it already #{H}", "The {T} day ended in tears, feeling so empty #{H}", "Still crying over the {T} thing, nothing feels right #{H}"],
    "fear": ["Terrified about the {T} results tomorrow, can't sleep #{H}", "That {T} noise tonight scared me so much, shaking #{H}", "Dreading the {T} meeting, my hands won't stop trembling #{H}"],
}
TWEET_T = ["exam", "work", "family", "school", "travel", "weekend", "concert", "weather", "match", "project"]
TWEET_H = ["mood", "life", "today", "feelings", "real", "nofilter", "update", "mondays"]

FACTS: list[Fact] = [
    Fact("rb_topic_news_8", "TOPIC", "What is the topic of this news sentence?", "", "", "The news is about {X}.", sided="kway",
         classes=tuple(TOPICS), ground_truth="the topic whose frames and pools generated the sentence", balanced_factors=("frame_index",)),
    Fact("rb_topic_sports_vs_politics", "TOPIC", "Is this news sentence about sports or about politics?", "sports", "politics",
         "The news is about {X}.", ground_truth="generating topic", balanced_factors=("frame_index",)),
    Fact("rb_topic_science_vs_business", "TOPIC", "Is this news sentence about science or about business?", "science", "business",
         "The news is about {X}.", ground_truth="generating topic", balanced_factors=("frame_index",)),
    Fact("rb_topic_is_health", "TOPIC", "Is this news sentence about health?", "health", "something else", "The news is about {X}.",
         sided="one", jlens_pos="health", ground_truth="generating topic = health vs the seven other topics (equally)", balanced_factors=()),
    Fact("rb_topic_review_sentiment", "TOPIC", "Is this review positive or negative?", "positive", "negative", "The review is {X}.",
         ground_truth="adjective and verb drawn from the positive or the negative pool (same frames)", balanced_factors=("frame",)),
    Fact("rb_topic_tweet_emotion_4", "TOPIC", "Which emotion does this tweet express?", "", "", "The tweet expresses {X}.", sided="kway",
         classes=tuple(EMOTIONS), ground_truth="the emotion whose frames generated the tweet", balanced_factors=()),
    Fact("rb_topic_tweet_joy_vs_anger", "TOPIC", "Does this tweet express joy or anger?", "joy", "anger", "The tweet expresses {X}.",
         ground_truth="generating emotion", balanced_factors=()),
]


DATELINES = ["", "LONDON - ", "PARIS - ", "BERLIN - ", "MADRID - ", "TOKYO - ", "DELHI - ", "OTTAWA - ", "SYDNEY - "]


def news_sentence(rng: random.Random, topic: str, fi: int) -> str:
    """One templated sentence of ``topic`` from frame ``fi``; a seeded dateline (or none) multiplies the text space."""
    frames, pools = NEWS[topic]
    s = frames[fi].format(**{k: rng.choice(v) for k, v in pools.items()})
    return rng.choice(DATELINES) + s[0].upper() + s[1:]


def build_news(seed: int) -> dict[str, list[Draft]]:
    out = {}
    seen: set[str] = set()
    rng = rng_for(seed, "rb_topic_news_8")
    n = 8 * 90
    topics = balanced_levels(TOPICS, n, rng)
    frames = balanced_levels([0, 1, 2], n, rng)
    kway = []
    for i in range(n):
        text = fresh(rng, lambda r, i=i: news_sentence(r, topics[i], frames[i]), seen)
        kway.append(Draft(text, TOPICS.index(topics[i]), topics[i], None, {"frame_index": frames[i], "ground_truth": topics[i]}))
    out["rb_topic_news_8"] = kway
    for fid, a, b in (("rb_topic_sports_vs_politics", "sports", "politics"), ("rb_topic_science_vs_business", "science", "business")):
        rng = rng_for(seed, fid)
        n = 240
        pos = balanced_bools(n, rng)
        frames = balanced_levels([0, 1, 2], n, rng)
        drafts = []
        for i in range(n):
            t = a if pos[i] else b
            text = fresh(rng, lambda r, i=i, t=t: news_sentence(r, t, frames[i]), seen)
            drafts.append(Draft(text, 1 if pos[i] else 0, t, None, {"frame_index": frames[i], "ground_truth": t}))
        out[fid] = drafts
    rng = rng_for(seed, "rb_topic_is_health")
    n = 280
    pos = balanced_bools(n, rng)
    others = iter(balanced_levels([t for t in TOPICS if t != "health"], n // 2, rng))
    drafts = []
    for i in range(n):
        t = "health" if pos[i] else next(others)
        text = fresh(rng, lambda r, t=t: news_sentence(r, t, r.randrange(3)), seen)
        drafts.append(Draft(text, 1 if pos[i] else 0, "health" if pos[i] else "something else", None, {"topic": t, "ground_truth": t}))
    out["rb_topic_is_health"] = drafts
    return out


def build_reviews(seed: int) -> list[Draft]:
    rng = rng_for(seed, "rb_topic_review_sentiment")
    n = 320
    pos = balanced_bools(n, rng)
    frames = balanced_levels(list(range(len(REVIEW_FRAMES))), n, rng)
    seen, out = set(), []
    for i in range(n):
        def mk(r, i=i):
            return REVIEW_FRAMES[frames[i]].format(P=r.choice(PRODUCTS), A=r.choice(POS_ADJ if pos[i] else NEG_ADJ), V=r.choice(POS_V if pos[i] else NEG_V))
        text = fresh(rng, mk, seen)
        out.append(Draft(text, 1 if pos[i] else 0, "positive" if pos[i] else "negative", None, {"frame": frames[i], "ground_truth": pos[i]}))
    return out


def build_tweets(seed: int) -> dict[str, list[Draft]]:
    seen: set[str] = set()
    rng = rng_for(seed, "rb_topic_tweet_emotion_4")
    n = 4 * 80
    emo = balanced_levels(EMOTIONS, n, rng)
    kway = []
    for i in range(n):
        text = fresh(rng, lambda r, i=i: r.choice(TWEETS[emo[i]]).format(T=r.choice(TWEET_T), H=r.choice(TWEET_H)), seen)
        kway.append(Draft(text, EMOTIONS.index(emo[i]), emo[i], None, {"ground_truth": emo[i]}))
    rng = rng_for(seed, "rb_topic_tweet_joy_vs_anger")
    n = 240   # review fix item 5: 120 test items (was 76)
    pos = balanced_bools(n, rng)
    binary = []
    for i in range(n):
        e = "joy" if pos[i] else "anger"
        text = fresh(rng, lambda r, e=e: r.choice(TWEETS[e]).format(T=r.choice(TWEET_T), H=r.choice(TWEET_H)), seen)
        binary.append(Draft(text, 1 if pos[i] else 0, e, None, {"ground_truth": e}))
    return {"rb_topic_tweet_emotion_4": kway, "rb_topic_tweet_joy_vs_anger": binary}


def build(seed: int) -> dict[str, list[Draft]]:
    out = build_news(seed)
    out["rb_topic_review_sentiment"] = build_reviews(seed)
    out.update(build_tweets(seed))
    return out
