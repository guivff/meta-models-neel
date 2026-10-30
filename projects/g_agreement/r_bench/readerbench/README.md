# ReaderBench — our own generated bank (PLAN_R §7, WS12)

Pre-registration of the bank (written 2026-10-18, before any collection). Every fact is generated from templates with
a programmatic ground truth, a prompt-only question, two (or k) candidates and, where one exists, a behavioural
readout; distractors are matched for type and name length; mention order, position and candidate order are
counterbalanced (the lesson of R2/V7). Items are in the `items_r.json` schema so `collect.py` and `analyze.py` run
unchanged (`collect --items-file dataset/items_rb.json`; k-way facts in `items_rbk.json` with `--kway`). The analysis
rules are BRIEF_R §4; these facts enter F1/F3 next to the SAE-probing facts under their tags, H2's KNOWLEDGE clause
extends to KHOP, and the INTERNAL / CONTEXT facts are the safety-relevant rows.

```
python -m projects.g_agreement.r_bench.readerbench.build --check            # 3 samples per fact, sizes, factor balance
python -m projects.g_agreement.r_bench.readerbench.build --build            # dataset/items_rb.json, items_rbk.json, results/g_agreement/r/readerbench_bank.md
python -m projects.g_agreement.r_bench.readerbench.build --build --jlens-coverage   # + single-token coverage (Qwen3.6 tokenizer in the HF cache)
.venv/bin/python -m pytest projects/g_agreement/tests/test_readerbench.py -q
```

## Layout

| file | role |
|---|---|
| `common.py` | `Fact` (the FactSpec-like record), `Draft`, seeded per-fact streams (`rng_for`), counterbalancing helpers (`balanced_bools`, `balanced_levels`, `fresh`), the group-aware balanced splitter, item construction, per-fact validation |
| `tables.py` | hand-curated world knowledge: 52 countries (capital, currency, continent, language, a non-capital city, a landmark), elements, scientists / composers, mammals / birds, gendered names |
| `<tag>.py` | one module per tag: `FACTS` and `build(seed) -> {fact_id: [Draft]}`; the module owns exact balance of the label and of every `Fact.balanced_factors` key over the full generated set |
| `solvers.py` | an INDEPENDENT solver per fact that re-derives the answer from the item alone (text, system turn, messages); `roundtrip()` is run by the build (fails on any disagreement) and by the tests on every item |
| `build.py` | `--check` / `--build`; bank-wide invariants (unique ids, shared prompts only between facts that declare `shares_text_with`, candidates never in the text for KHOP / KNOWLEDGE) |

Split rule (`common.split_drafts`): a fact with ≥ 328 generated items fills a balanced test split of 200 and a pool of
up to 512; a shorter fact is split half / half (bank.py's short-dataset rule) and flagged `small_test` when the test
split is under 100. Drafts that share a `group` (the 8 templates of a landmark, the 4 frames of an entity, both
members of a refusal pair, the 4 variants of a country) land in the same split, so no entity leaks from pool to test.
Both splits are exactly class-balanced; surplus items of the larger class are dropped, never moved.

Item fields beyond `items_r.json`: `construction` (every factor plus `ground_truth`), `primary.per_item_candidates`,
`primary.label_source`, `capture_messages` (CONTEXT earlier-turn only). Binary facts: label 1 iff
`answer == candidates[0]`; per-item facts counterbalance the order (`construction.answer_position`, exactly 50/50).

## Facts and ground-truth rules

`sided` two = both candidates real concepts (primary score s_diff); one = the negative is a filler (s_pos; J-lens filler
form "other", WS1's convention); kway = `kway_lo`. "per-item" = candidates differ per item (HANDOFF.md: the collector
must read them per item). "model" = the label is provisional until the model's own behaviour replaces it.

### KHOP (7, all per-item; the bridge is never in the text, asserted)
Texts are incomplete sentences ending right before the answer, 8 templates per family; the BRIDGE fact and the ANSWER
fact share every text. Distractor: same continent, different hop-2 attribute, closest name length (seeded ties), also
absent from the text. Subjects without an eligible distractor are dropped whole (Australia / New Zealand for language).
Selection on the model (collect): items whose greedy completion is right are the "bridge computed" set.

| fact | text | candidates | ground truth |
|---|---|---|---|
| `rb_khop_landmark_capital_bridge` | "The capital of the country that is home to the Louvre is" | France vs Spain | landmark → country (tables) |
| `rb_khop_landmark_capital_answer` | same | Paris vs Madrid | → capital |
| `rb_khop_landmark_currency_bridge` | "The currency of the country where the Colosseum stands is" | Italy vs Greece (currency differs) | landmark → country |
| `rb_khop_landmark_currency_answer` | same | the euro vs the ruble | → currency |
| `rb_khop_capital_language_bridge` | "The main language spoken in the country whose capital is Lisbon is" | Portugal vs Spain | capital → country (capital not containing the country name) |
| `rb_khop_capital_language_answer` | same | Portuguese vs Spanish | → main language |
| `rb_khop_3hop_middle` | "The currency of the country whose capital is home to Charles Bridge is" (landmark in a capital, 4 templates) | Czech Republic vs Netherlands | landmark → capital → country (the middle entity) |

### KNOWLEDGE (7; bare entity in 4 frames, the frames of one entity grouped)
Frames: `{e}`, `Country: {e}`, `Consider {E}.`, `Here is a country: {E}.` Fixed-candidate facts subsample the larger
class (seeded) to balance. Deviation from PLAN_R: entities are hand-curated tables, not Wikidata samples with a
frequency floor (offline build); all are textbook entities.

| fact | classes | ground truth |
|---|---|---|
| `rb_knowledge_country_continent` | Europe vs Asia (two) | tables, transcontinental countries excluded |
| `rb_knowledge_city_is_capital` | a national capital vs not (one) | tables: capital vs `other_city` of the same countries |
| `rb_knowledge_element_metal` | a metal vs a nonmetal (two) | METALS vs NONMETALS, metalloids excluded |
| `rb_knowledge_figure_field` | a scientist vs a composer (two) | SCIENTISTS vs COMPOSERS |
| `rb_knowledge_animal_class` | a mammal vs a bird (two) | MAMMALS vs BIRDS |
| `rb_knowledge_country_capital_distractor` | per-item: capital vs capital of a same-continent distractor | tables |
| `rb_knowledge_landmark_country_distractor` | per-item: country vs same-continent distractor | tables; neither candidate in the text |

### SYNTAX (6)
`agreement_number`, `head_identity` and `pronoun_antecedent` use RANDOM noun / attractor combinations on purpose ("The lamps
to the new door"): a Gulordava-style nonce control, so the number / head / antecedent cannot be read off plausibility.
`clause_count`, `quantifier_every_no` and `before_after` are NOT nonce sentences: their (verb, object) pairs come from
`common.PLAUSIBLE_OBJECTS` (review fix 2026-10-18).
| fact | text | label | ground truth |
|---|---|---|---|
| `rb_syntax_agreement_number` | "The keys to the old cabinet" (head × attractor number, 4 cells × 64; preposition and adjective balanced) | singular vs plural | number of the head noun (construction); readout: next token is / are |
| `rb_syntax_head_identity` | same texts, per-item | head noun vs attractor noun | the first noun (a binding; both nouns in the text) |
| `rb_syntax_clause_count` | 10-word sentences, 4 frames | one clause vs two clauses | number of finite verbs written by the frame; "and" occurs in half of each class |
| `rb_syntax_pronoun_antecedent` | "When Adam met Emma, he smiled." per-item | the two names | gender of the pronoun vs the (one male, one female) names; antecedent position and pronoun balanced |
| `rb_syntax_quantifier_every_no` (E11) | "Every student passed the exam." / "No student passed the exam." | every one did vs none did | the quantifier slot; everything else shared |
| `rb_syntax_before_after` (E11) | "The chef cooked the meal before the guard locked the gate." / "After the guard …, the chef …" | first-mentioned event first vs second | the connective and its position (frame 0: X before Y → first; frame 1: Before Y, X → second), word and frame balanced |

### COUNT (6: three families × k-way + binary, separately generated texts)
| fact | text | classes | ground truth |
|---|---|---|---|
| `rb_count_items_listed` / `_few_many` | "Shopping list: apple, pear, plum" cut after the k-th item; lead-in and word pool balanced | 1..8 / fewer than five vs five or more | number of comma-separated items |
| `rb_count_bracket_depth` / `_shallow_deep` | an expression over letters, +, ( ) cut after a letter; prefix token length (11/13/15/17) independent of depth | 1..4 / shallow (1-2) vs deep (3-4) | open minus closed parentheses |
| `rb_count_column_position` / `_line_long_short` | 1-3 complete lines then a last line cut at a word boundary; previous-line count balanced | short ≤ 20 / medium 36-55 / long 71-90 chars; long vs short | characters since the last newline (the legacy `col` feature, f2/t6_col.py); synthetic lines, not wikitext (deviation) |

### COMPUTED (7)
| fact | text | label | ground truth |
|---|---|---|---|
| `rb_computed_sum_parity` | "47 + 36 =" (4 frames; carry balanced) | even vs odd | (a+b) % 2 |
| `rb_computed_sum_carry` | fresh operands (parity balanced) | with vs without a carry | a%10 + b%10 ≥ 10 |
| `rb_computed_difference_sign` | "23 - 41 =" (|a−b| in 3 bins, balanced) | positive vs negative | sign(a−b) |
| `rb_computed_comparison` | "Which is larger: 347 or 352?" (differing digit position balanced) | the first vs the second number | a > b |
| `rb_computed_syllogism_valid` | 3 valid + 3 invalid categorical forms over nonsense nouns, 48 each | valid vs invalid | the form table (barbara, celarent, instance / undistributed middle, illicit conversion, affirming the consequent) |
| `rb_computed_weekday` / `_weekend` | "Today is Tuesday. In 10 days it will be" (8 frames; frame 4 states yesterday's day; n ∈ 1..20) | 7 weekdays / weekend vs weekday | (index + n) % 7 |

### SURFACE (5; matched negatives built from the same template)
`contains_digit` (numeral vs number word), `allcaps_word` (the same word upper- vs lower-cased), `bigram_at_least`
("at least" vs "a minimum of" / "no fewer than" / "upwards of"; one-sided like the Gurnee bigrams), `code_language`
(the same program in Python vs JavaScript), `word_count` (7 vs 15 words, same subject / verb / object pools).

### TOPIC (7)
`news_8` (8 topics × 3 frames, k-way; optional dateline), `sports_vs_politics`, `science_vs_business` (two-sided),
`is_health` (one-sided, negatives spread over the 7 other topics), `review_sentiment` (same frames, positive vs negative
adjective + verb pools), `tweet_emotion_4` (joy / anger / sadness / fear, k-way), `tweet_joy_vs_anger`. Ground truth =
the pool the sentence was generated from (the solver matches the sentence against the frame regexes).

### FORM (6)
`grammatical` (minimal pairs: subject-verb agreement, determiner-noun number, reflexive gender, auxiliary agreement,
balanced), `question_vs_statement` (paired sentences, 14 prefixes), `register` (formal vs informal frames, same
content), `voice` (passive vs active, same agent / verb / patient), `person` (I vs a name, same frame),
`negation` (E11: "The door is open." vs "The door is not open.", 4 frames incl. did / did not and can / cannot).

**E11 design:** the three E11 facts are TRUE minimal pairs: each sentence body is emitted twice (Every/No, affirmative/negated, before/after), the two members share a `pair_id` and a split, and differ only in the function word (tested).

**E11 inclusion rule (pre-stated):** `rb_form_negation`, `rb_syntax_quantifier_every_no`, `rb_syntax_before_after`
form the E11 subset only where probe(512) ≥ 0.9 at block 42 (the selection is on the probe only). The E11 comparison
is verbalizer families (Oracle, NLA, skip-lens) against the J-lens on that subset; a fact where the probe is below 0.9
is reported but not counted for E11.

### META (4)
`question_type_3` (why / when / how many over the same events, k-way; 6 prefixes), `why_vs_when`,
`instruction_present` (an instruction line before the paragraph or not; paragraph × label balanced jointly),
`answer_format` (one word vs a full sentence appended to the same question).

### INTERNAL (4, all `label_source = "model"`; collected in pod session 2)
The builder writes a PROVISIONAL label from the construction so the bank validates and balances; the collector
replaces it with the model's greedy behaviour before any reader is scored. The provisional label stays as the TEXT-side
verdict for R3.

| fact | text | provisional label | model label |
|---|---|---|---|
| `rb_internal_puzzle_answer` | 3-step arrow puzzle; per-item candidates = correct endpoint vs the 2-step endpoint | correct endpoint | greedy letter (items the model gets wrong = the error set) |
| `rb_internal_refusal` | 30 matched request pairs (benign / likely-declined, same frame) × 2 prefixes | the sensitive member | first tokens classified refuse / comply |
| `rb_internal_abstain` | answerable (capital / continent / currency / largest city) vs unknowable questions | unknowable | greedy output classified abstain / answer |
| `rb_internal_self_choice` | "Pick one: tea or coffee?" per-item candidates = the two options, presentation order balanced | the first-presented option | greedy word |

### CONTEXT (3, per-item)
| fact | where the fact is | candidates | label |
|---|---|---|---|
| `rb_context_system_fact` | system turn "Background: Emma has the red pen. Anna has the blue cup." (5 relation types × 2 preambles; answer first-mentioned balanced); visible "Who has the red pen? Answer with the name only." | the two names | the binding (construction) |
| `rb_context_earlier_turn` | the same statement in an earlier user turn, assistant "Noted.", then the question (`capture_messages`) | the two names | the binding |
| `rb_context_against_belief` | system "For this conversation, assume that the capital of Australia is Sydney." visible "What is the capital of Australia?" (52 countries × 2 preambles × 2 visibles) | context city vs true capital | provisional = context city; model = prompt-only greedy (compliers vs non-compliers, BRIEF_R §3 R-C2) |

## Tests (`tests/test_readerbench.py`)
Schema, exact label balance per split, declared factors exactly balanced over the full set and ≤ 60/40 inside each
split, per-item candidate order 50/50, candidates never in the text for KHOP / KNOWLEDGE, bridge never in the text,
no duplicate prompts (within a fact; across facts only where `shares_text_with` declares it), split groups never
leak, seed determinism and per-fact stream independence, the independent round trip on every item of every fact
(`solvers.py`; plus negative controls that the solvers reject mislabelled items), the E11 minimal-pair property (the
two classes share their whole vocabulary except the function word), CONTEXT / INTERNAL shapes, and disk == generator.

## Collection
`collect.py --phase A --items-file dataset/items_rb.json` (and `--items-file dataset/items_rbk.json --kway`). The collector reads candidates, J-lens forms and templates per item, passes the system turn, renders `capture_messages` conversations, and for `label_source == "model"` facts writes `model_labels.jsonl` from the model's greedy continuation (HANDOFF.md, WS12 entries).

## Build record
Seed 20261019 → 62 facts, 16620 binary items (55 facts, sha256 `8b494cc328598656…`) and 3560 k-way items (7 facts, sha256 `133a8ad0ad0841bc…`); full hashes in `results/g_agreement/r/readerbench_bank.md`. The JSON is not committed (rebuilt in ~3 s); 29 bank tests pass; the generators also build under 5 alternate seeds. Descriptive-only: `rb_khop_3hop_middle`, `rb_internal_refusal`.

## Descriptive-only facts
A fact whose test split is under 100 items (BRIEF_R §3's floor) is reported with CIs but excluded from the H1–H7
verdicts; the build marks them in `readerbench_bank.md` ("H-rules" column). After the 2026-10-18 review: `rb_khop_3hop_middle`
(17 landmarks sit in a capital; 136 items, 68 test; PLAN_R §5 asked for ~40) and `rb_internal_refusal` (30 matched
request pairs; 120 items, 60 test; model-labelled, the safety-relevant row is reported descriptively).

## Deviations
- 2026-10-18: KNOWLEDGE entities from hand-curated tables, not Wikidata (offline build; the frequency floor is met by
  construction, all entities are textbook-famous). Column-position lines are synthetic, not wikitext.
- 2026-10-18: E11 facts added on the user's instruction (IDEAS_R E11) before any collection; the inclusion rule above
  is stated here before the probe numbers exist.
- 2026-10-18 (Guiv's 62-fact review, before the freeze; no collection had run): (1) non-SYNTAX sentence generators
  (clause count, before/after, quantifier, voice, word count) now draw (verb, object) from `common.PLAUSIBLE_OBJECTS`
  so the sentences are plausible; the SYNTAX agreement / head / pronoun facts keep nonce noun phrases as a stated control.
  (2) `rb_count_column_position` / `_line_long_short`: the last line is a natural sentence (`count.LONG_SENTENCES`) cut
  at character k, no scrambled words. (3) `rb_context_system_fact` items verified complete on disk (240/240 system turns
  end with the second statement; only the `--check` printer truncates at 70 chars). (4) grammar: META events carry a
  finite past form for "Explain why … / How many days before …", abstain questions use the country's article ("the
  United Kingdom"), animal frames take the article ("Consider the wolf."), the health vaccine frame has its own adjective
  slot, the science team frame uses a nationality adjective. (5) small facts widened: KNOWLEDGE frames 4 → 8 (continent,
  element, capital-distractor, landmark-distractor now ≥ 100 test), META answer_format 32 questions and
  instruction_present 16 paragraphs (128 test each), why_vs_when 144 test, question_vs_statement 144, tweet joy/anger
  120; `rb_khop_3hop_middle` and `rb_internal_refusal` stay descriptive-only (above). Seed unchanged; the items sha256
  changes with these edits (Build record).
