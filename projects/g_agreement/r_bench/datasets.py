"""The Phase R fact spec (BRIEF_R.md §3): one entry per SAE-probing dataset (Kantamneni & Engels et al. 2025,
``data/probing_datasets_MASTER.csv`` of github.com/JoshEngels/SAE-Probes; raw CSVs ``prompt,target`` from their
Dropbox), plus the 15 multiclass parents for the k-way regime.

Every binary fact declares
  question   what the prompt-only baseline asks the model about the text
  pos / neg  the two candidate verbalisations (pos is true when target is positive)
  template   the NLA sentence with {X} (Oracle uses "- {X}", skip-lens the bare continuation, J-lens single tokens)
  jlens_*    optional one-word forms for the J-lens when the candidate is not a single token (None -> unscorable)
  positive   raw target values that count as the positive class (None -> DEFAULT_POSITIVE)
  sided      "two" when both candidates are real concepts (primary score s_pos - s_neg), "one" when neg is a filler
             (primary score s_pos)
  tag        taxonomy: SURFACE, TOPIC, FORM, KNOWLEDGE, PASSAGE-KNOWLEDGE, COMPUTED, META (INTERNAL / CONTEXT are the
             carried-over families; KHOP / SYNTAX / COUNT the R-E bank)
  verify     True when we have not seen the prompt format: ``bank --check`` prints samples; fix before the freeze

Reviewed against the raw CSVs on 2026-10-18 (WS1, ``bank --check`` + the parent round trip, see
``results/g_agreement/r/bank_summary.md``): every ``verify`` flag was cleared after reading samples of both classes.
One-sided facts get the J-lens filler ``ONE_SIDED_JLENS_NEG`` automatically, because ``scoring_lo.lo_jlens`` marks
a pair unscorable when EITHER candidate has no single-token variant and the collector falls back to the full
candidate text ("something else") when ``jlens_neg`` is None.

Nothing in here imports torch. The spec is frozen with the rest of the R code by ``collect --freeze-r``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

DEFAULT_POSITIVE: frozenset[Any] = frozenset({1, "1", True, "True", "true", "TRUE", "yes", "Yes", 1.0, "1.0"})

# PASSAGE-KNOWLEDGE (BRIEF_R Deviations, 2026-10-18): Wikidata 56-64, where the text is a web passage mentioning the
# person, so the attribute is sometimes stated; reported separately from bare-name KNOWLEDGE. KHOP / SYNTAX / COUNT
# are the R-E tags of r_bench/beyond_text.py (WS10).
TAGS = ("SURFACE", "TOPIC", "FORM", "KNOWLEDGE", "PASSAGE-KNOWLEDGE", "COMPUTED", "META", "INTERNAL", "CONTEXT",
        "KHOP", "SYNTAX", "COUNT")

# The prompt-only forced-choice render (BRIEF_R §2.2). Frozen with the spec; contains only the text, the dataset
# question and the two candidates. The model answers after the assistant onset; LO = lp(pos) - lp(neg), teacher-forced.
PROMPT_ONLY_FC_TEMPLATE = (
    "You will read a short text and answer one question about it.\n\n"
    "Text:\n{text}\n\n"
    "Question: {question}\n"
    "Answer with exactly one of these two options and nothing else: \"{pos}\" or \"{neg}\"."
)
# k-way variant (R-B): the options are listed one per line in a fixed, seeded order per item.
PROMPT_ONLY_KWAY_TEMPLATE = (
    "You will read a short text and answer one question about it.\n\n"
    "Text:\n{text}\n\n"
    "Question: {question}\n"
    "Answer with exactly one of these options and nothing else:\n{options}"
)


@dataclass(frozen=True)
class FactSpec:
    id: str                      # file stem, e.g. "5_hist_fig_ismale"
    tag: str
    question: str
    pos: str
    neg: str
    template: str
    sided: str = "two"
    jlens_pos: str | None = None
    jlens_neg: str | None = None
    positive: frozenset[Any] | None = None
    verify: bool = False
    note: str = ""

    def __post_init__(self) -> None:
        # one-sided facts: the negative is a filler, but the J-lens needs a single-token negative to score at all
        if self.sided == "one" and self.jlens_neg is None:
            object.__setattr__(self, "jlens_neg", ONE_SIDED_JLENS_NEG)

    @property
    def num(self) -> int:
        return int(self.id.split("_", 1)[0])

    @property
    def file(self) -> str:
        return f"{self.id}.csv"

    def is_positive(self, raw: Any) -> bool | None:
        """True / False for a raw target value; None when the value matches neither class. Membership is by the
        string form of the value (``1``, ``"1"`` and ``1.0`` all read "1" after ``bank._coerce``), so a spec rebuilt
        from ``to_json()`` classifies identically and Python's ``True == 1`` cannot leak a bool into {1, "1"}."""
        pos = self.positive if self.positive is not None else DEFAULT_POSITIVE
        if _member(raw, pos):
            return True
        neg = NEGATIVE_FOR.get(self.id)
        if neg is not None:
            return False if _member(raw, neg) else None
        # default negatives for the default positive set
        if self.positive is None and _member(raw, DEFAULT_NEGATIVE):
            return False
        return None

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["positive"] = sorted(map(str, self.positive)) if self.positive is not None else None
        return d


def _member(raw: Any, values: frozenset[Any]) -> bool:
    return str(raw) in {str(v) for v in values}


DEFAULT_NEGATIVE: frozenset[Any] = frozenset({0, "0", False, "False", "false", "FALSE", "no", "No", 0.0, "0.0"})
# The J-lens negative for one-sided facts ("something else", "another borough", "no such phrase"): one token, no
# concept of its own; the primary score of a one-sided fact is s_pos, so this only enters the secondary s_diff.
ONE_SIDED_JLENS_NEG = "other"
# datasets whose targets are strings: the accepted negative values (positive values live in the spec). A column
# with exactly two values, one of them positive, needs no entry here (bank.labelled_rows infers the other); the
# entries below make the encodings we verified explicit anyway.
NEGATIVE_FOR: dict[str, frozenset[Any]] = {
    "41_truthqa_tf": frozenset({"incorrect"}),
    "44_phys_tf": frozenset({0, "0"}),
    "47_reasoning_tf": frozenset({"B"}),
    "56_wikidatasex_or_gender": frozenset({"female"}),
    "58_wikidatapolitical_party": frozenset({"Republican Party"}),
    "90_glue_qnli": frozenset({"not_entailment", 1, "1"}),
    "105_click_bait": frozenset({"factual"}),
}


def _bigram(num: int, slug: str, phrase: str, jl: str) -> FactSpec:
    NEGATIVE_FOR[f"{num}_{slug}"] = frozenset({"not_bigram"})
    return FactSpec(
        id=f"{num}_{slug}", tag="SURFACE",
        question=f"Does the text contain the phrase \"{phrase}\"?",
        pos=phrase, neg="no such phrase", template="The text mentions {X}.", sided="one",
        jlens_pos=jl, jlens_neg=None, positive=frozenset({"bigram"}),
        note="Gurnee-style bigram window; the phrase sits at or near the end of the text; English only",
    )


def _one_of_k(num: int, slug: str, tag: str, question: str, pos: str, template: str, neg: str,
              jl: str | None = None, verify: bool = False, note: str = "") -> FactSpec:
    """A binary split of a multiclass parent: pos is the class, neg a filler ("another ...")."""
    return FactSpec(id=f"{num}_{slug}", tag=tag, question=question, pos=pos, neg=neg, template=template,
                    sided="one", jlens_pos=jl, jlens_neg=None, verify=verify, note=note)


_WIKIDATA_NOTE = "web passage mentioning the person (bare name in a minority of rows), 1,500-1,700 distinct texts"

# ------------------------------------------------------------------ the 113 binary facts
_SPECS: list[FactSpec] = [
    # --- world-model entities (Gurnee & Tegmark): the prompt is a bare name
    FactSpec("5_hist_fig_ismale", "KNOWLEDGE", "Is this historical figure male or female?", "male", "female",
             "The person is {X}.", "two", "male", "female"),
    FactSpec("6_hist_fig_isamerican", "KNOWLEDGE", "Is this historical figure American?", "American", "not American",
             "The person is {X}.", "one", "American", None),
    FactSpec("7_hist_fig_ispolitician", "KNOWLEDGE", "Is this historical figure a politician?", "a politician",
             "not a politician", "The person is {X}.", "one", "politician", None),
    # --- NYT headlines (Gurnee): topic presence
    FactSpec("21_headline_istrump", "TOPIC", "Is this headline about Donald Trump?", "Donald Trump", "something else",
             "The headline is about {X}.", "one", "Trump", None),
    FactSpec("22_headline_isobama", "TOPIC", "Is this headline about Barack Obama?", "Barack Obama", "something else",
             "The headline is about {X}.", "one", "Obama", None),
    FactSpec("23_headline_ischina", "TOPIC", "Is this headline about China?", "China", "something else",
             "The headline is about {X}.", "one", "China", None),
    FactSpec("24_headline_isiran", "TOPIC", "Is this headline about Iran?", "Iran", "something else",
             "The headline is about {X}.", "one", "Iran", None),
    FactSpec("26_headline_isfrontpage", "FORM", "Did this headline run on the front page?", "front-page news",
             "inside-page news", "This is {X}.", "two", "front", "inside",
             note="NYT headlines, 1 = front page; hard for a probe too (paper AUC 0.83)"),
    # --- truth / validity (COMPUTED)
    FactSpec("36_sciq_tf", "COMPUTED", "Is the proposed answer to this science question correct?", "correct",
             "incorrect", "The answer is {X}.", "two", "correct", "incorrect",
             note="format 'Q: ...\\nA: ...'; 1 = the SciQ gold answer, 0 = a distractor"),
    FactSpec("41_truthqa_tf", "COMPUTED", "Is the proposed answer to this question true?", "true", "false",
             "The answer is {X}.", "two", "true", "false", positive=frozenset({"correct"}),
             note="format 'Q. ...\\nA. ...'; targets correct/incorrect; 490 distinct texts (small)"),
    FactSpec("42_temp_sense", "COMPUTED", "Is the proposed answer to the question plausible?", "plausible",
             "implausible", "The answer is {X}.", "two", "plausible", "absurd",
             note="MC-TACO: context\\nquestion\\ncandidate answer; yes = plausible"),
    FactSpec("44_phys_tf", "COMPUTED", "Which of the two solutions, A or B, is correct?", "solution B", "solution A",
             "The correct solution is {X}.", "two", "B", "A", positive=frozenset({1, "1"}),
             note="PIQA: goal\\n\\nA.sol1\\nB.sol2; label 1 = the second solution (B) is correct, 0 = A"),
    FactSpec("47_reasoning_tf", "COMPUTED", "Which of the two answers, A or B, is correct?", "answer A", "answer B",
             "The correct answer is {X}.", "two", "A", "B", positive=frozenset({"A"}),
             note="QuaRTz: question\\nA. ... B. ...; target is the letter of the correct answer"),
    FactSpec("48_cm_correct", "COMPUTED", "Is the behaviour described morally wrong?", "morally wrong",
             "morally acceptable", "The behaviour is {X}.", "two", "wrong", "acceptable",
             note="ETHICS commonsense: label 1 = wrong"),
    FactSpec("49_cm_isshort", "SURFACE", "Is this text short or long?", "short", "long", "The text is {X}.", "two",
             "short", "long"),
    FactSpec("50_deon_isvalid", "COMPUTED", "Is the excuse a reasonable one?", "reasonable", "unreasonable",
             "The excuse is {X}.", "two", "reasonable", "unreasonable",
             note="ETHICS deontology: request\\nexcuse; 1 = reasonable"),
    FactSpec("51_just_is", "COMPUTED", "Is the justification reasonable?", "reasonable", "unreasonable",
             "The justification is {X}.", "two", "reasonable", "unreasonable", note="ETHICS justice; 1 = reasonable"),
    FactSpec("52_virtue_is", "COMPUTED", "Does the named trait fit the scenario?", "fitting", "unfitting",
             "The trait is {X}.", "two", "fitting", "wrong",
             note="ETHICS virtue: scenario [SEP] trait; 1 = the trait is exemplified"),
    FactSpec("54_cs_tf", "COMPUTED", "Is this commonsense statement true?", "true", "false", "The statement is {X}.",
             "two", "true", "false", note="targets yes/no"),
    # --- wikidata attributes (Wes): the text is a web passage that mentions the person (a bare name in a minority
    #     of rows), so the attribute is sometimes stated or cued (pronouns for 56) and sometimes recalled. Tagged
    #     PASSAGE-KNOWLEDGE and reported separately from the bare-name KNOWLEDGE facts (BRIEF_R Deviations).
    FactSpec("56_wikidatasex_or_gender", "PASSAGE-KNOWLEDGE", "Is the person this text is about male or female?", "male",
             "female", "The person is {X}.", "two", "male", "female", positive=frozenset({"male"}),
             note=_WIKIDATA_NOTE + "; targets male/female; pronouns in the passage cue the answer"),
    FactSpec("57_wikidatais_alive", "PASSAGE-KNOWLEDGE", "Is the person this text is about alive or dead?", "alive", "dead",
             "The person is {X}.", "two", "alive", "dead", note=_WIKIDATA_NOTE + "; targets true/false"),
    FactSpec("58_wikidatapolitical_party", "PASSAGE-KNOWLEDGE", "Is the person this text is about a Democrat or a Republican?",
             "a Democrat", "a Republican", "The person is {X}.", "two", "Democrat", "Republican",
             positive=frozenset({"Democratic Party"}),
             note=_WIKIDATA_NOTE + "; targets 'Democratic Party' / 'Republican Party'; 1,931 distinct texts"),
    FactSpec("59_wikidata_occupation_isjournalist", "PASSAGE-KNOWLEDGE", "Is the person this text is about a journalist?",
             "a journalist", "not a journalist", "The person is {X}.", "one", "journalist", None, note=_WIKIDATA_NOTE),
    FactSpec("60_wikidata_occupation_isathlete", "PASSAGE-KNOWLEDGE", "Is the person this text is about an athlete?",
             "an athlete", "not an athlete", "The person is {X}.", "one", "athlete", None, note=_WIKIDATA_NOTE),
    FactSpec("61_wikidata_occupation_isactor", "PASSAGE-KNOWLEDGE", "Is the person this text is about an actor?", "an actor",
             "not an actor", "The person is {X}.", "one", "actor", None, note=_WIKIDATA_NOTE),
    FactSpec("62_wikidata_occupation_ispolitician", "PASSAGE-KNOWLEDGE", "Is the person this text is about a politician?",
             "a politician", "not a politician", "The person is {X}.", "one", "politician", None, note=_WIKIDATA_NOTE),
    FactSpec("63_wikidata_occupation_issinger", "PASSAGE-KNOWLEDGE", "Is the person this text is about a singer?", "a singer",
             "not a singer", "The person is {X}.", "one", "singer", None, note=_WIKIDATA_NOTE),
    FactSpec("64_wikidata_occupation_isresearcher", "PASSAGE-KNOWLEDGE", "Is the person this text is about a researcher?",
             "a researcher", "not a researcher", "The person is {X}.", "one", "researcher", None, note=_WIKIDATA_NOTE),
    # --- bigram presence 65–85 (SURFACE)
    _bigram(65, "high-school", "high school", "school"),
    _bigram(66, "living-room", "living room", "room"),
    _bigram(67, "social-security", "social security", "security"),
    _bigram(68, "credit-card", "credit card", "card"),
    _bigram(69, "blood-pressure", "blood pressure", "pressure"),
    _bigram(70, "prime-factors", "prime factors", "factors"),
    _bigram(71, "social-media", "social media", "media"),
    _bigram(72, "gene-expression", "gene expression", "expression"),
    _bigram(73, "control-group", "control group", "group"),
    _bigram(74, "magnetic-field", "magnetic field", "field"),
    _bigram(75, "cell-lines", "cell lines", "lines"),
    _bigram(76, "trial-court", "trial court", "court"),
    _bigram(77, "second-derivative", "second derivative", "derivative"),
    _bigram(78, "north-america", "North America", "America"),
    _bigram(79, "human-rights", "human rights", "rights"),
    _bigram(80, "side-effects", "side effects", "effects"),
    _bigram(81, "public-health", "public health", "health"),
    _bigram(82, "federal-government", "federal government", "government"),
    _bigram(83, "third-party", "third party", "party"),
    _bigram(84, "clinical-trials", "clinical trials", "trials"),
    _bigram(85, "mental-health", "mental health", "health"),
    # --- GLUE
    FactSpec("87_glue_cola", "FORM", "Is this sentence grammatically acceptable?", "grammatical", "ungrammatical",
             "The sentence is {X}.", "two", "correct", "incorrect",
             note="~25% label noise per the paper's LLM majority; secondary key available; 'grammatical' is 3 tokens"),
    FactSpec("89_glue_mrpc", "COMPUTED", "Do the two sentences say the same thing?", "equivalent", "different",
             "The two sentences are {X}.", "two", "equivalent", "different", note="'s1 | s2'; 1 = paraphrase"),
    FactSpec("90_glue_qnli", "COMPUTED", "Does the sentence answer the question?", "an answer to the question",
             "unrelated to the question", "The sentence is {X}.", "two", "answer", "unrelated",
             positive=frozenset({"entailment", 0, "0"}),
             note="'question | sentence'; GLUE QNLI encodes 0 = entailment (answers), 1 = not_entailment"),
    FactSpec("91_glue_qqp", "COMPUTED", "Are the two questions duplicates?", "duplicate questions",
             "different questions", "These are {X}.", "two", "duplicate", "different", note="'q1 | q2'; 1 = duplicate"),
    FactSpec("92_glue_sst2", "TOPIC", "Is the sentiment of this review positive or negative?", "positive", "negative",
             "The sentiment is {X}.", "two", "positive", "negative"),
    # --- provenance / style
    FactSpec("94_ai_gen", "FORM", "Was this essay written by a language model or by a student?", "machine-generated",
             "human-written", "The text is {X}.", "two", "machine", "human",
             note="lower-cased student essays vs GPT-2 essays; the AI rows carry injected character typos (pn/pt/cre)"),
    FactSpec("95_toxic_is", "TOPIC", "Is this user request toxic?", "toxic", "harmless", "The request is {X}.", "two",
             "toxic", "harmless", note="chatbot user prompts incl. jailbreaks (toxic-chat style); 584 distinct texts"),
    FactSpec("96_spam_is", "TOPIC", "Is this message spam?", "spam", "a legitimate message", "This is {X}.", "two",
             "spam", "legitimate", note="SMS spam; 1 = spam"),
    FactSpec("100_news_fake", "FORM", "Is this news article real or fake?", "real news", "fake news", "This is {X}.",
             "two", "real", "fake",
             note="ISOT: title\\nbody; 1 = real (Reuters wire), 0 = fake (21st Century Wire etc.); the '(Reuters)' "
                  "dateline is a surface cue; 2,010 distinct texts"),
    FactSpec("105_click_bait", "FORM", "Is this headline clickbait?", "clickbait", "a factual headline", "This is {X}.",
             "two", "bait", "factual", positive=frozenset({"clickbait"}),
             note="targets clickbait/factual; 1,601 distinct headlines; 'clickbait' is 3 tokens"),
    FactSpec("106_hate_hate", "TOPIC", "Is this tweet hate speech?", "hate speech", "not hate speech", "This is {X}.",
             "one", "hate", None, note="Davidson et al. tweets: hate vs offensive-or-neither; noisy labels"),
    FactSpec("107_hate_offensive", "TOPIC", "Is this tweet offensive?", "offensive", "inoffensive", "The tweet is {X}.",
             "two", "offensive", "civil", note="Davidson et al.: offensive vs hate-or-neither"),
    FactSpec("110_aimade_humangpt3", "FORM", "Was this text written by an AI or by a human?", "AI-written",
             "human-written", "The text is {X}.", "two", "AI", "human",
             note="human rows are mostly short questions/posts, AI rows prose; the paper's spurious cue: AI text "
                  "ends with a period more often"),
    FactSpec("113_movie_sent", "TOPIC", "Is this movie review positive or negative?", "positive", "negative",
             "The sentiment is {X}.", "two", "positive", "negative", note="Rotten Tomatoes sentences; 1 = positive"),
    # --- binarised multiclass parents (one-vs-rest)
    _one_of_k(114, "nyc_borough_Manhattan", "KNOWLEDGE", "Which New York City borough is this place in?", "Manhattan",
              "The place is in {X}.", "another borough", "Manhattan"),
    _one_of_k(115, "nyc_borough_Brooklyn", "KNOWLEDGE", "Which New York City borough is this place in?", "Brooklyn",
              "The place is in {X}.", "another borough", "Brooklyn"),
    _one_of_k(116, "nyc_borough_Bronx", "KNOWLEDGE", "Which New York City borough is this place in?", "the Bronx",
              "The place is in {X}.", "another borough", "Bronx"),
    _one_of_k(117, "us_state_FL", "KNOWLEDGE", "Which US state is this city in?", "Florida", "The city is in {X}.",
              "another state", "Florida"),
    _one_of_k(118, "us_state_CA", "KNOWLEDGE", "Which US state is this city in?", "California", "The city is in {X}.",
              "another state", "California"),
    _one_of_k(119, "us_state_TX", "KNOWLEDGE", "Which US state is this city in?", "Texas", "The city is in {X}.",
              "another state", "Texas"),
    _one_of_k(120, "us_timezone_Chicago", "KNOWLEDGE", "Which US time zone is this city in?", "Central Time",
              "The city is in {X}.", "another time zone", "Central"),
    _one_of_k(121, "us_timezone_New_York", "KNOWLEDGE", "Which US time zone is this city in?", "Eastern Time",
              "The city is in {X}.", "another time zone", "Eastern"),
    _one_of_k(122, "us_timezone_Los_Angeles", "KNOWLEDGE", "Which US time zone is this city in?", "Pacific Time",
              "The city is in {X}.", "another time zone", "Pacific"),
    _one_of_k(123, "world_country_United_Kingdom", "KNOWLEDGE", "Which country is this place in?", "the United Kingdom",
              "The place is in {X}.", "another country", "Britain"),
    _one_of_k(124, "world_country_United_States", "KNOWLEDGE", "Which country is this place in?", "the United States",
              "The place is in {X}.", "another country", "America"),
    _one_of_k(125, "world_country_Italy", "KNOWLEDGE", "Which country is this place in?", "Italy",
              "The place is in {X}.", "another country", "Italy"),
    _one_of_k(126, "art_type_book", "KNOWLEDGE", "Is this work a book, a song or a movie?", "a book", "This is {X}.",
              "another kind of work", "book"),
    _one_of_k(127, "art_type_song", "KNOWLEDGE", "Is this work a book, a song or a movie?", "a song", "This is {X}.",
              "another kind of work", "song"),
    _one_of_k(128, "art_type_movie", "KNOWLEDGE", "Is this work a book, a song or a movie?", "a movie", "This is {X}.",
              "another kind of work", "movie"),
    _one_of_k(129, "arith_mc_A", "COMPUTED", "Is option A the correct answer to this arithmetic question?", "option A",
              "The correct answer is {X}.", "another option", "A",
              note="parent 37_arith_mc; 'Calculate a - b =\\nA.x B.y C.z D.w'; 1 = A is correct"),
    _one_of_k(130, "temp_cat_Frequency", "META", "What kind of temporal question is this?", "a frequency question",
              "This is {X}.", "another kind of temporal question", "frequency"),
    _one_of_k(131, "temp_cat_Typical Time", "META", "What kind of temporal question is this?", "a typical-time question",
              "This is {X}.", "another kind of temporal question", "time"),
    _one_of_k(132, "temp_cat_Event Ordering", "META", "What kind of temporal question is this?",
              "an event-ordering question", "This is {X}.", "another kind of temporal question", "ordering"),
    _one_of_k(133, "context_type_Causality", "META", "What does this question ask about?", "causality", "This is about {X}.",
              "something else", "cause"),
    _one_of_k(134, "context_type_Belief_states", "META", "What does this question ask about?", "belief states",
              "This is about {X}.", "something else", "beliefs"),
    _one_of_k(135, "context_type_Event_duration", "META", "What does this question ask about?", "event duration",
              "This is about {X}.", "something else", "duration"),
    _one_of_k(136, "glue_mnli_entailment", "COMPUTED", "Does the premise entail, contradict or say nothing about the hypothesis?",
              "entailment", "The relation is {X}.", "another relation", "entails"),
    _one_of_k(137, "glue_mnli_neutral", "COMPUTED", "Does the premise entail, contradict or say nothing about the hypothesis?",
              "neutral", "The relation is {X}.", "another relation", "neutral"),
    _one_of_k(138, "glue_mnli_contradiction", "COMPUTED", "Does the premise entail, contradict or say nothing about the hypothesis?",
              "contradiction", "The relation is {X}.", "another relation", "contradiction"),
    _one_of_k(139, "news_class_Politics", "TOPIC", "What is this news headline about?", "politics", "The topic is {X}.",
              "another topic", "politics"),
    _one_of_k(140, "news_class_Technology", "TOPIC", "What is this news headline about?", "technology",
              "The topic is {X}.", "another topic", "technology"),
    _one_of_k(141, "news_class_Entertainment", "TOPIC", "What is this news headline about?", "entertainment",
              "The topic is {X}.", "another topic", "entertainment"),
    _one_of_k(142, "cancer_cat_Thyroid_Cancer", "TOPIC", "Which cancer is this text about?", "thyroid cancer",
              "The text is about {X}.", "another cancer", "thyroid"),
    _one_of_k(143, "cancer_cat_Lung_Cancer", "TOPIC", "Which cancer is this text about?", "lung cancer",
              "The text is about {X}.", "another cancer", "lung"),
    _one_of_k(144, "cancer_cat_Colon_Cancer", "TOPIC", "Which cancer is this text about?", "colon cancer",
              "The text is about {X}.", "another cancer", "colon"),
    _one_of_k(145, "disease_class_digestive system diseases", "TOPIC", "Which kind of disease is this abstract about?",
              "digestive system diseases", "The abstract is about {X}.", "another kind of disease", "digestive"),
    _one_of_k(146, "disease_class_cardiovascular diseases", "TOPIC", "Which kind of disease is this abstract about?",
              "cardiovascular diseases", "The abstract is about {X}.", "another kind of disease", "cardiovascular"),
    _one_of_k(147, "disease_class_nervous system diseases", "TOPIC", "Which kind of disease is this abstract about?",
              "nervous system diseases", "The abstract is about {X}.", "another kind of disease", "nervous"),
    _one_of_k(148, "twt_emotion_worry", "TOPIC", "Which emotion does this tweet express?", "worry",
              "The emotion is {X}.", "another emotion", "worry"),
    _one_of_k(149, "twt_emotion_happiness", "TOPIC", "Which emotion does this tweet express?", "happiness",
              "The emotion is {X}.", "another emotion", "happiness"),
    _one_of_k(150, "twt_emotion_sadness", "TOPIC", "Which emotion does this tweet express?", "sadness",
              "The emotion is {X}.", "another emotion", "sadness"),
    _one_of_k(151, "it_tick_HR Support", "TOPIC", "Which category does this IT request belong to?", "HR support",
              "The request is about {X}.", "another category", "HR"),
    _one_of_k(152, "it_tick_Hardware", "TOPIC", "Which category does this IT request belong to?", "hardware",
              "The request is about {X}.", "another category", "hardware"),
    _one_of_k(153, "it_tick_Administrative rights", "TOPIC", "Which category does this IT request belong to?",
              "administrative rights", "The request is about {X}.", "another category", "admin"),
    _one_of_k(154, "athlete_sport_football", "KNOWLEDGE", "Which sport does this athlete play?", "football",
              "The athlete plays {X}.", "another sport", "football"),
    _one_of_k(155, "athlete_sport_basketball", "KNOWLEDGE", "Which sport does this athlete play?", "basketball",
              "The athlete plays {X}.", "another sport", "basketball"),
    _one_of_k(156, "athlete_sport_baseball", "KNOWLEDGE", "Which sport does this athlete play?", "baseball",
              "The athlete plays {X}.", "another sport", "baseball"),
    FactSpec("157_amazon_5star", "TOPIC", "Is this a five-star review?", "a five-star review", "a lower-rated review",
             "This is {X}.", "two", "five", "lower", note="'Title: ...\\nReview: ...'; 1 = five stars"),
    _one_of_k(158, "code_C", "SURFACE", "Which programming language is this code written in?", "C code",
              "The snippet is {X}.", "code in another language", "C"),
    _one_of_k(159, "code_Python", "SURFACE", "Which programming language is this code written in?", "Python code",
              "The snippet is {X}.", "code in another language", "Python"),
    _one_of_k(160, "code_HTML", "SURFACE", "Which programming language is this code written in?", "HTML code",
              "The snippet is {X}.", "code in another language", "HTML"),
    FactSpec("161_agnews_0", "SURFACE", "Is this a news headline or a code sample?", "a news headline",
             "a code sample", "This is {X}.", "two", "news", "code",
             note="paper README: 161-163 were mangled into headline-vs-code; confirmed; three different samples"),
    FactSpec("162_agnews_1", "SURFACE", "Is this a news headline or a code sample?", "a news headline",
             "a code sample", "This is {X}.", "two", "news", "code", note="see 161"),
    FactSpec("163_agnews_2", "SURFACE", "Is this a news headline or a code sample?", "a news headline",
             "a code sample", "This is {X}.", "two", "news", "code", note="see 161"),
]

SPECS: dict[str, FactSpec] = {s.id: s for s in _SPECS}
assert len(SPECS) == len(_SPECS), "duplicate fact id"


# ------------------------------------------------------------------ multiclass parents (R-B, k-way)
@dataclass(frozen=True)
class MulticlassSpec:
    id: str
    tag: str
    question: str
    template: str
    k_max: int = 8
    class_map: dict[str, str] = field(default_factory=dict)  # raw target -> candidate phrase (else prettified raw)
    verify: bool = False  # all 15 parents inspected with ``bank --check`` on 2026-10-18

    @property
    def num(self) -> int:
        return int(self.id.split("_", 1)[0])

    @property
    def file(self) -> str:
        return f"{self.id}.csv"

    def candidate(self, raw: Any) -> str:
        s = str(raw)
        if s in self.class_map:
            return self.class_map[s]
        return s.replace("_", " ").replace("America/", "").strip()


# the raw targets of 13_us_state are postal codes (10 classes: GA FL PA NC IL MI CA TX OH NY)
US_STATES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

MULTICLASS: dict[str, MulticlassSpec] = {m.id: m for m in [
    MulticlassSpec("10_nyc_borough", "KNOWLEDGE", "Which New York City borough is this place in?", "The place is in {X}.", 5),
    MulticlassSpec("13_us_state", "KNOWLEDGE", "Which US state is this city in?", "The city is in {X}.", 8, US_STATES),
    MulticlassSpec("14_us_timezone", "KNOWLEDGE", "Which US time zone is this city in?", "The city is in {X}.", 6,
                   {"Chicago": "Central Time", "New_York": "Eastern Time", "Los_Angeles": "Pacific Time",
                    "Denver": "Mountain Time", "Phoenix": "Arizona time", "Anchorage": "Alaska Time",
                    "Honolulu": "Hawaii Time"}),
    MulticlassSpec("17_world_country", "KNOWLEDGE", "Which country is this place in?", "The place is in {X}.", 8),
    MulticlassSpec("27_art_type", "KNOWLEDGE", "What kind of work is this?", "This is {X}.", 6),
    MulticlassSpec("43_temp_cat", "META", "What kind of temporal question is this?", "This is {X}.", 6),
    MulticlassSpec("46_context_type", "META", "What does this question ask about?", "This is about {X}.", 8),
    MulticlassSpec("88_glue_mnli", "COMPUTED", "Does the premise entail, contradict or say nothing about the hypothesis?",
                   "The relation is {X}.", 3),
    MulticlassSpec("97_news_class", "TOPIC", "What is this news headline about?", "The topic is {X}.", 8),
    MulticlassSpec("98_cancer_cat", "TOPIC", "Which cancer is this text about?", "The text is about {X}.", 3),
    MulticlassSpec("99_sci_cat", "TOPIC", "Which science is this text about?", "The text is about {X}.", 3),
    MulticlassSpec("101_disease_class", "TOPIC", "Which kind of disease is this abstract about?", "The abstract is about {X}.", 5),
    MulticlassSpec("102_twt_emotion", "TOPIC", "Which emotion does this tweet express?", "The emotion is {X}.", 8),
    MulticlassSpec("103_it_tick", "TOPIC", "Which category does this IT request belong to?", "The request is about {X}.", 8),
    MulticlassSpec("108_athlete_sport", "KNOWLEDGE", "Which sport does this athlete play?", "The athlete plays {X}.", 8),
]}


# ------------------------------------------------------------------ binarised children -> (parent CSV stem, raw class)
# The one-vs-rest datasets 114-156 and 129 are rows of a multiclass parent with target 1 iff the parent class is the
# named one; ``bank --roundtrip`` joins each child with its parent on the text and checks exactly that (all 43
# children: P(1 | parent == class) = 1.00, P(1 | parent != class) = 0.00 on 2026-10-18). 37_arith_mc is a parent
# that is not in the k-way set (its classes are the letters A-D).
BINARISED_FROM: dict[str, tuple[str, str]] = {
    "114_nyc_borough_Manhattan": ("10_nyc_borough", "Manhattan"), "115_nyc_borough_Brooklyn": ("10_nyc_borough", "Brooklyn"),
    "116_nyc_borough_Bronx": ("10_nyc_borough", "Bronx"),
    "117_us_state_FL": ("13_us_state", "FL"), "118_us_state_CA": ("13_us_state", "CA"), "119_us_state_TX": ("13_us_state", "TX"),
    "120_us_timezone_Chicago": ("14_us_timezone", "Chicago"), "121_us_timezone_New_York": ("14_us_timezone", "New_York"),
    "122_us_timezone_Los_Angeles": ("14_us_timezone", "Los_Angeles"),
    "123_world_country_United_Kingdom": ("17_world_country", "United_Kingdom"),
    "124_world_country_United_States": ("17_world_country", "United_States"), "125_world_country_Italy": ("17_world_country", "Italy"),
    "126_art_type_book": ("27_art_type", "book"), "127_art_type_song": ("27_art_type", "song"), "128_art_type_movie": ("27_art_type", "movie"),
    "129_arith_mc_A": ("37_arith_mc", "A"),
    "130_temp_cat_Frequency": ("43_temp_cat", "Frequency"), "131_temp_cat_Typical Time": ("43_temp_cat", "Typical Time"),
    "132_temp_cat_Event Ordering": ("43_temp_cat", "Event Ordering"),
    "133_context_type_Causality": ("46_context_type", "Causality"), "134_context_type_Belief_states": ("46_context_type", "Belief_states"),
    "135_context_type_Event_duration": ("46_context_type", "Event_duration"),
    "136_glue_mnli_entailment": ("88_glue_mnli", "entailment"), "137_glue_mnli_neutral": ("88_glue_mnli", "neutral"),
    "138_glue_mnli_contradiction": ("88_glue_mnli", "contradiction"),
    "139_news_class_Politics": ("97_news_class", "Politics"), "140_news_class_Technology": ("97_news_class", "Technology"),
    "141_news_class_Entertainment": ("97_news_class", "Entertainment"),
    "142_cancer_cat_Thyroid_Cancer": ("98_cancer_cat", "Thyroid_Cancer"), "143_cancer_cat_Lung_Cancer": ("98_cancer_cat", "Lung_Cancer"),
    "144_cancer_cat_Colon_Cancer": ("98_cancer_cat", "Colon_Cancer"),
    "145_disease_class_digestive system diseases": ("101_disease_class", "digestive system diseases"),
    "146_disease_class_cardiovascular diseases": ("101_disease_class", "cardiovascular diseases"),
    "147_disease_class_nervous system diseases": ("101_disease_class", "nervous system diseases"),
    "148_twt_emotion_worry": ("102_twt_emotion", "worry"), "149_twt_emotion_happiness": ("102_twt_emotion", "happiness"),
    "150_twt_emotion_sadness": ("102_twt_emotion", "sadness"),
    "151_it_tick_HR Support": ("103_it_tick", "HR Support"), "152_it_tick_Hardware": ("103_it_tick", "Hardware"),
    "153_it_tick_Administrative rights": ("103_it_tick", "Administrative rights"),
    "154_athlete_sport_football": ("108_athlete_sport", "football"), "155_athlete_sport_basketball": ("108_athlete_sport", "basketball"),
    "156_athlete_sport_baseball": ("108_athlete_sport", "baseball"),
}


# ------------------------------------------------------------------ carried-over families (R-D)
# Only descriptive here: the analysis merges their existing LO rows / states; see analyze.r_d_rows.
R_D_FAMILIES: dict[str, dict[str, Any]] = {
    "ownership": {"tag": "INTERNAL", "source": "x1_lo.jsonl (items_x.json)", "note": "binding; label = answer-is-first-mentioned confound (R2)"},
    "mapping": {"tag": "INTERNAL", "source": "x1_lo.jsonl", "note": "two-way among symbols; eight-way in W2"},
    "language": {"tag": "TOPIC", "source": "x1_lo.jsonl", "note": "requested reply language; text-derivable"},
    "tense": {"tag": "TOPIC", "source": "x1_lo.jsonl", "note": "requested tense; text-derivable"},
    "puzzle_error": {"tag": "INTERNAL", "source": "y1 / v1 rows", "note": "the model's upcoming wrong answer; probe from L48, lenses from L52"},
    "self_choice": {"tag": "INTERNAL", "source": "x3 / y1 rows", "note": "the model's upcoming choice; no site found"},
    "v7c_private": {"tag": "CONTEXT", "source": "v/v7c rows", "note": "fact only in the system turn; readers 79–94%"},
    "counts": {"tag": "INTERNAL", "source": "w bank", "note": "value readout; readers exact 1–3%"},
}


# ------------------------------------------------------------------ helpers
def specs(tags: tuple[str, ...] | None = None, ids: list[str] | None = None) -> list[FactSpec]:
    out = [s for s in _SPECS if (tags is None or s.tag in tags) and (ids is None or s.id in ids)]
    return sorted(out, key=lambda s: s.num)


def taxonomy_counts() -> dict[str, int]:
    out: dict[str, int] = {}
    for s in _SPECS:
        out[s.tag] = out.get(s.tag, 0) + 1
    return dict(sorted(out.items()))


def spec_check() -> list[str]:
    """Static integrity: ids unique and ordered, tags known, templates carry {X}, candidates distinct and non-empty."""
    problems = []
    nums = [s.num for s in _SPECS]
    if len(set(nums)) != len(nums):
        problems.append("duplicate dataset numbers")
    for s in _SPECS:
        if s.tag not in TAGS:
            problems.append(f"{s.id}: unknown tag {s.tag}")
        if "{X}" not in s.template:
            problems.append(f"{s.id}: template without {{X}}")
        if not s.pos or not s.neg or s.pos == s.neg:
            problems.append(f"{s.id}: bad candidates")
        if s.sided not in ("one", "two"):
            problems.append(f"{s.id}: sided={s.sided}")
        if not s.question.endswith("?"):
            problems.append(f"{s.id}: question should be a question")
        if s.sided == "one" and not s.jlens_neg:
            problems.append(f"{s.id}: one-sided fact without a J-lens negative filler")
        if s.positive is not None and NEGATIVE_FOR.get(s.id) and s.positive & NEGATIVE_FOR[s.id]:
            problems.append(f"{s.id}: a target value is both positive and negative")
    for m in MULTICLASS.values():
        if "{X}" not in m.template or m.tag not in TAGS:
            problems.append(f"{m.id}: bad multiclass spec")
    for child, (parent, _) in BINARISED_FROM.items():
        if child not in SPECS:
            problems.append(f"BINARISED_FROM: unknown child {child}")
        if parent not in MULTICLASS and parent != "37_arith_mc":
            problems.append(f"BINARISED_FROM: unknown parent {parent}")
    return problems


if __name__ == "__main__":
    import json

    print(json.dumps({"n_binary": len(_SPECS), "n_multiclass": len(MULTICLASS), "taxonomy": taxonomy_counts(),
                      "n_verify": sum(s.verify for s in _SPECS), "problems": spec_check()}, indent=1))
