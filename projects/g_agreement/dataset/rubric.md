# Claim-extraction rubric (rule set `rule-v1`)

Status: written 2026-10-07, **before any readout (NLA / OLens / J-lens / target / prompt-only) exists**
for this dataset. Pre-collection revision 2026-10-07 (coordinator review, still before any readout
exists): J1 tightened (negated-name rule), J4 switched off (hop-2 recitation no longer asserts the
result), blind sheet uses opaque `sheet_id`s. It is implemented verbatim in `projects/g_agreement/core/scoring.py`; this file is
the authoritative description, the code is the executable one. Any change after test outputs exist
must be logged as a dated deviation (CLAUDE.md rule 1) and bumps the extractor id (`rule-v2`, ...).

Annotator labels produced later by a model (`extractor: model:<id>`) or a person
(`extractor: human:<name>`) are **provisional**. **No human validation of this rubric or of any
label has occurred.** Rule-based labels are the primary labels of the pilot; model/human labels, if
collected, are reported alongside, never substituted silently.

## 0. Vocabulary

Every item has a *primary property* with exactly two *candidates* `[c0, c1]` and an *answer*
(one of them). For each readout we assign a primary `status`:

| status | meaning |
|---|---|
| `supports` | exactly one candidate is asserted as the value of the primary property, and it is the answer |
| `contradicts` | exactly one candidate is asserted, and it is the other candidate |
| `self_contradictory` | both candidates are asserted |
| `unclear` | neither candidate is asserted (abstention, off-topic, hedge, unbound lists) |

`value` is the asserted candidate (`null` unless supports/contradicts). `evidence` is a verbatim
span. Two `unclear` never count as agreement between methods. "Asserted" is defined per family
below; a mention that is **negated** ("not German", "rather than Leo", "isn't C") or **hedged**
("French or German", "Mira / Leo") is not an assertion.

Negation rule: a mention is negated if the 30 characters before it end in one of
`not, no, never, neither, nor, isn't, wasn't, aren't, rather than, instead of, without, unlike,
except` optionally followed by up to two intervening words (never across a contrast word `but / yet /
however / rather / instead / only`) and then `in / a / an / the / by / to / being / using / into / of /
about`. So "not blau in German" negates German, while "Not German but French" leaves French asserted.
(Window widened 2026-10-07 pre-collection to make the J1 negated-name rule reach "not <word> in X".)
Hedge rule: `X or Y`, `X, or Y`, `X / Y`, `X versus Y`, `either X ... or Y` (either order) discounts
both mentions inside that span.

Secondary fields: `entities_mentioned` (which candidate names / symbols / language names appear,
negated or not), `objects_mentioned` (ownership only), and `relation.status` in
`correct | wrong | unbound | absent` (ownership and mapping only; other families always `absent`
with evidence `n/a`). `unbound` = the relevant entities are all named but no binding clause exists.
`truncated: true` whenever the generation's `finish_reason == "length"`; truncated readouts keep
their label but are flagged as incomplete observations.

## 1. Language family (`response_language`)

Candidates: two language names, e.g. `["French", "German"]`.

A candidate is **asserted** if either
(a) the readout **names** it — English name, own name, adjective or country form
    (French/français/française/France; German/Deutsch/Germany/Deutschland; Spanish/español/castellano/
    Spain/España; Italian/italiano/Italy/Italia; Portuguese/português/Portugal; Dutch/Nederlands/
    Netherlands/Holland; Swedish/svenska/Sweden/Sverige; Turkish/Türkçe/Turkey/Türkiye), case-insensitive,
    whole word, not negated, not hedged; or
(b) the readout **is (partly) written in** that language according to the wordlist detector below.

Examples (item lang-01A, answer French, other German):
- "The user wants the answer in French." → supports (named).
- "Le ciel est bleu." → supports (written in French: `le`, `est`, `bleu`).
- "Answer in German: blau." → contradicts.
- "bleu in French, not blau in German" → **supports French**: German's name is negated, so
  written-in evidence for German needs ≥ 2 distinct detector hits and the single `blau` is not
  enough (J1). "Not German. Der Himmel ist blau." → contradicts (`der, himmel, ist, blau` ≥ 2 hits).
- "French or German, hard to say." → unclear (hedge).
- "A colour question about the sky." → unclear.

Wordlist detector (`detect_language(text, candidates)`): ~30–45 lower-cased words per language
(articles, pronouns, common verbs, the expected answer words of the dataset). For a given item only
words that are in **exactly one** of the two candidates' lists count; the candidate with strictly
more distinct hits wins; ties (including 0–0) → no language. Limits, stated plainly:
- it covers only the eight languages used by the dataset; it knows no grammar;
- English words were removed from every list (`a, in, is, die, was, so, also, man, met, van, we,
  no, son, con, per, come, do, as, um, os, com, mi, ben, var, men, till, den, tack, ...`), so an
  English readout that merely *mentions* a foreign word counts as "written in" that language — this
  is deliberate (rubric: quoting the answer word asserts the language) but it is a judgment call (J1);
- **negated-name rule (J1):** if a candidate language's name is negated anywhere in the readout,
  written-in evidence for that candidate requires ≥ 2 distinct hits (`LANGUAGE_WRITTEN_IN_MIN_HITS_IF_NAME_NEGATED`);
- a single ambiguous word shared by both candidates (e.g. `azul` es/pt, `verde` es/it/pt, `vier`
  de/nl, `la` fr/es/it) gives no evidence; language pairs in the dataset were chosen so that the
  expected answer words differ;
- it cannot distinguish dialects or detect code-switching beyond counting words.

Target-model scoring: the target's reply is classified by the same detector over the item's two
candidates (`target_value`), and separately matched against `target_answer_regex` (the expected
word(s) in the requested language, e.g. `bleu|bleue`). Both are reported; the regex is the stricter
"answered the question in the right language" check.

## 2. Tense family (`response_tense`)

Candidates: `["past", "future"]`. Two layers; the weak layer is used only when the strong layer
finds nothing (`TENSE_USE_WEAK_LAYER = True`).

Strong (explicit) markers, not negated:
- past: `past`, `yesterday`, `happened`, `previously`, `earlier`, `ago`, `last night/week/month/year/time`, `preterite`, `already`
- future: `future`, `tomorrow`, `upcoming`, `next week/day/month/year/time/morning`, `will happen`, `plans to`, `intends to`, `about to`

Weak (verb-form) markers:
- past: irregular past forms (went, was, were, did, saw, ate, made, took, came, ...), auxiliaries
  (was/were/did/had + n't), regular `-ed` words **excluding** non-verbs (`red, bed, need, indeed,
  naked, hundred, ...`) and **excluding meta-verbs that describe the prompt rather than the event**
  (`asked, requested, instructed, prompted, told, wanted, said, mentioned, used, described, specified,
  provided, given, based, related, focused, called, named, listed, needed, required, expected, ...`);
- future: `will` (unless followed by a meta verb: *will be / respond / answer / reply / say / write /
  output / generate / produce / give / provide / need / have / use / mention / include / describe /
  focus / ...*), `'ll`, `shall`, `going to`, `gonna`, `next week/...`, `is about to`.

Decision: strong markers for exactly one label → that label; both → self_contradictory; none →
weak layer with the same rule; weak both or none → unclear.

Examples (tense-01A, answer past):
- "a sentence about yesterday at the park" → supports.
- "The user asked what Sam will do tomorrow." → contradicts (`tomorrow` strong; `asked` is meta).
- "Sam went to the park and played football." → supports (weak layer).
- "The model will answer about Sam at the park." → unclear (`will answer` is meta).
- "Sam will play at the park." → contradicts (weak future).
- "Sam was at the park and will return tomorrow." → self_contradictory (strong `tomorrow`? no:
  `tomorrow` is strong future and there is no strong past, so **contradicts**; `was` is only weak).
  This asymmetry — explicit words beat verb forms — is judgment call J2.

Target-model scoring (`detect_tense`): the target's sentence is `future` if it contains any future
marker and no past marker, `past` if the reverse, `mixed` if both, `None` if neither; `mixed`/`None`
count as not classifiable. The meta-verb exclusions are **not** applied to the target (its sentence
is about the event). Known misses: present-perfect ("has gone") is not recognised as past; "would"
is ignored; past-tense sentences built only from verbs not in the lists (e.g. "Sam put the cup
down") give `None`.

## 3. Ownership family (`<object>_owner`)

Candidates: the two names. Objects: `[asked, other]`. A **binding** is a clause that contains
(i) the asked object (full phrase, or its head noun when the two objects have different head nouns —
"red key"/"blue key" need the full phrase, "lantern"/"rope" accept the noun alone), (ii) a possession
cue (`has, have, had, holds, holding, held, owns, owned, keeps, kept, carries, carrying, possesses,
belongs, with, gets, got, given, takes, took, 's`), and (iii) a candidate name (non-negated). When a
clause contains both names, the name **nearest in characters** to the asked-object mention is bound.
Clauses are split on `. ; : ! ? newline`, bullets, and `, and / and / while / whereas / but / although`.

**Asserted** = bound to the asked object, or named by an **answer pattern**: "the answer/owner/
holder/one is NAME", "Answer: NAME", "NAME is the answer/owner/one", "NAME has it", or the whole
readout being just the name. Listing both names with both objects without a binding is `unclear`
with `relation: unbound`. **No inference by elimination**: "Leo has the blue key" alone says nothing
about the red key (judgment call J3).

Relation: `correct` if the answer is bound to the asked object and the other is not; `wrong` if the
other is bound (or both are bound — recorded with both spans); `unbound` as above; `absent` otherwise.

Examples (own-01A: Mira has the red key, Leo the blue key; asked: red key):
- "Mira has the red key and Leo has the blue key." → supports, relation correct.
- "Leo has the red key." → contradicts, relation wrong.
- "Mira, Leo, red key, blue key." → unclear, relation unbound.
- "Leo holds the blue key; the red key is Mira's." → supports (`'s` cue), relation correct.
- "The answer is Mira." → supports, relation absent (an answer, not a stated relation).
- "Mira has the red key. Leo has the red key too." → self_contradictory, relation wrong.

## 4. Mapping family (`two_step_result`)

Candidates: the two possible destinations. Symbols: `[start, intermediate, c0, c1]`. A **binding**
is a directed statement `src CUE dst` with `src ∈ {start, intermediate}`, `dst` a candidate, and
CUE one of `→ -> => ⇒ maps to / leads to / becomes / goes to / points to / gives / then`, a two-hop
chain `start → x → dst`, or prose "from/at/starting at SRC ... reaches/ends up at/lands on/arrives
at/gets to/results in/yields/is DST" (within 80 characters, src before dst). Direction matters:
the distractor rule "D → A" binds nothing (A is not a candidate). Single-letter symbols are matched
case-sensitively and only as standalone letters, so the article "a" is never symbol "A".

**Asserted** = a binding whose source is the **start** symbol (`A → C`, `A → B → C`, "from A you
reach C") or an answer pattern ("the answer/result/destination is C", "you reach/end up at/land on C",
the readout being just "C"). A binding from the **intermediate** symbol alone (`B → C`) does **not**
assert the two-step result (`MAPPING_INTERMEDIATE_COUNTS_AS_PRIMARY = False`, judgment call J4); it
drives `relation` only.

Relation (`intermediate → destination`): `correct` if the intermediate is bound to the answer only;
`wrong` if bound to the other (or both); `unbound` if the intermediate and both candidates appear
without a directed binding; `absent` otherwise.

Examples (map-01B: A → B. B → C. D → A; answer C):
- "A → B. B → C. D → A. Starting from A you reach C." → supports, relation correct.
- "B -> C" → unclear, relation correct (hop 2 recited, result not asserted).
- "B -> D" → unclear, relation wrong.
- "The symbols A, B, C and D with arrows." → unclear, relation unbound.
- "From A, after two steps you end up at D." → contradicts, relation absent.

## 5. J-lens token lists (method `jlens`)

The readout is the top-10 token list (`native.tokens`); it is **never turned into a sentence** and
no relation is extracted (`relation: absent`). Tokens are *folded*: tokenizer space markers
(`Ġ`, `▁`) removed, lower-cased, diacritics stripped, punctuation dropped. A candidate is matched
by a token if the folded token equals one of its forms, or is a prefix (≥ 4 characters,
`JLENS_PREFIX_MIN`) of one of its forms and not a prefix of any form of the other candidate
(so `Kenj` → Kenji, `Fara` → Farah, `Franç`/`France` → French, but `Ken` matches nothing).
Single-letter symbols must appear exactly as that upper-case letter (` C`, not ` c`).
Forms per family: language — the name forms of §1; tense — past: `past, yesterday, happened, ago,
was, were, did, earlier, previously, preterite`; future: `future, tomorrow, will, shall, going,
upcoming, next, later, soon`; ownership/mapping — the candidate string itself.

Decision: a candidate matched and the other not → supports/contradicts; both → self_contradictory;
neither → unclear. Rank within the top-10 is ignored (only membership counts). Evidence lists the
matching tokens per candidate.

## 6. Blinding and scoring

`make_blind_sheet(gens, seed, module)` emits `{sheet_id, method, text}` only — `sheet_id =
sha256(salt + gen_id)[:12]` is opaque; no gen id, item id, prompt or answer key — in a seeded shuffled
order (the method is visible because the format reveals it anyway). The mapping `{sheet_id: gen_id}`
is written to `cache/g_agreement/sheet_map_<module>.json`, never under `results/`.
`score_claims(claims, items, targets)` returns, per generation, **two separate judgments**:
`factual_correct` (claim value == answer key; `None` when unclear/self-contradictory) and
`target_consistent` (claim value == the target model's own extracted answer; `None` when either side
is unclassifiable). `target_correct` and `target_regex_match` are reported alongside.

## 7. Judgment calls to review before freezing

- **J1 — quoting a foreign word counts as "writing in" that language, unless that language's name is
  negated**, in which case ≥ 2 distinct detector hits are required. "bleu in French, not blau in
  German" → supports French. (Revised 2026-10-07 pre-collection; the original rule treated it as
  self_contradictory.)
- **J2 — explicit tense words beat verb forms** ("was ... tomorrow" → future). Alternative: treat
  any conflict as self_contradictory. Chosen because readouts narrate in the past/present
  ("the user asked", "Sam was the subject") far more often than they misuse "tomorrow".
- **J3 — no inference by elimination in ownership.** "Leo has the blue key" (nothing about the red
  key) is `unclear` for the red-key owner even though it logically implies Mira. Chosen because the
  property under test is the *binding* the reader reports, not what a reader could deduce.
- **J4 — reciting hop 2 does NOT assert the two-step result** ("B → C" → unclear, relation correct).
  Only start → destination bindings or explicit answer patterns count
  (`MAPPING_INTERMEDIATE_COUNTS_AS_PRIMARY = False`). (Decided 2026-10-07 pre-collection; the
  original draft had the switch on.)
- (minor) J5 — J-lens prefix matching at ≥ 4 characters and country names as language forms
  (`France` → French) trade recall for a small false-positive risk (`port` → Portuguese).

## 8. Known limits (all families)

Rule-based extraction has no understanding of scope: sarcasm, conditionals ("if it were German..."),
reported speech, and lists of alternatives longer than two are handled only by the negation/hedge
rules above. Readouts in a third language are not detected. All thresholds and lists are frozen with
the dataset; results tables always print raw numerators and denominators so that any reader can
re-score from the blind sheet.

## 9. Pre-freeze revision after the dev run (2026-10-07, dev readouts only; no test readout existed)

- §1/§5: the Chinese names of the eight languages (法语, 德语, 西班牙语, 意大利语, 葡萄牙语, 荷兰语, 瑞典语,
  土耳其语, and the -文 variants) count as naming the language. Motivation: a dev J-lens top-10 for the
  German item contained 德语 ("German language") and nothing else the rubric could read.
- §2: the meta/format participle exclusion list of the weak layer was extended (structured, formatted,
  capitalized, labeled, established, constrained, ...). Motivation: NLA readouts describe prompt
  FORMAT in such words, and a dev state-free NLA readout was scored `past` from "capitalized" and
  "structured" alone.

## 10. Choice family (`model_choice`, G6) — added 2026-10-07, before any G6 readout exists

Dataset: `dataset/items_g6.json` (8 test pairs, `choice-01`…`choice-08`; A/B swap the option order;
option types colour, tool, drink, city, fruit, animal, shape, number word; five templates). There is
**no external answer key**: `primary.answer` is `null` with `answer_source: "target_greedy"`; the key
for each item is the target model's own greedy answer, filled in by the analysis. Factual accuracy is
therefore replaced by **target consistency**.

Assertion rule (text readouts): a candidate is asserted when it is **named** (whole word,
case-insensitive, not negated, not hedged — same negation/hedge rules as §0) or named by an answer
pattern as in §3 ("the answer is apple", "Answer: apple", the readout being just "apple"). Exactly one
candidate asserted → recorded as `supports` with that `value` and `primary.provisional: true` (the
label is provisional because the key is unknown at extraction time); both → `self_contradictory`;
neither → `unclear`. `score_claims` then sets `answer` := the target's extracted answer and re-labels
the provisional row `supports` (value == target answer) or `contradicts` (value != target answer);
`factual_correct` and `target_consistent` coincide for this family by construction.

J-lens: as for names (§5): a top-10 token equal to, or a ≥ 4-character prefix of, the option word
(folded) matches that option; one option → provisional supports, both → self_contradictory, neither →
unclear. Relation: always `absent`.

Target answer (`extract_target_answer`): the first word of the target's reply if it is one of the
options; otherwise the only option mentioned; if **both** options are mentioned and neither is the
first word → `None` (unclassifiable). Position dominance (first-listed option chosen in ≥ 14/16
states) is reported by the analysis, not by this rubric.

Examples (choice-06A: "Choose either cat or dog…", candidates [cat, dog]):
- "The model will pick cat." → provisional supports cat; if the target said "cat" → supports, if "dog" → contradicts.
- "cat or dog" → unclear (hedge). "Not dog." → unclear (negated, nothing asserted).
- "It chooses cat, not dog." → supports cat. "cat and dog" → self_contradictory.
