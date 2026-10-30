# Theme 3 — Polarity and modality

These are three post-hoc hypotheses, not revised sealed verdicts. The first pass was read first. Its broad “dropped rather than inverted” interpretation is too coarse for the distinctions below. The verified complete native E49 and E57 sources supply public readouts, row definitions, and existing scores; true status is joined only in memory and reported only as aggregate counts. The E49 rows compare negated/unnegated and asserted/hypothetical clauses. E57 compares focus instructions while copying other text. All nine excerpts below are exact substrings of public native readouts, verified by `count_theme03.py`; the aggregate recount is `theme03_counts.json`.

E49 NLA readouts belong to the 128-token truncated cohort. E49 has a frozen statement detector, rather than the later blind statement judge, so the lexical diagnostics below are intentionally distinguished from its original statement measure. The sealed row probes for E49 negation scope and asserted/hypothetical status are both 1.000. E57 focus-ignore does **not** pass the .90 probe gate; it is discussed as readout behavior only.

## P3.1 — Negative status may survive in a different form: NLA uses scoped negation, while Oracle criticizes the imagined event sequence

**Hypothesis.** A reader can retain information about negative status without making a faithful negative assertion about the target proposition; Oracle may express it as an editorial fault signal.

**Count.** All **84/84** E49 negation-scope prompts contain both public marker forms, “It is false that” and “It is clear that”; their order determines the current clause's status. In NLA readouts, the exact marker `not the case` occurs on **28/42** negated-clause items and **0/42** unnegated-clause items. Oracle has that marker on **0/84**, but an editorial-fault lexicon occurs on **38/42** negated versus **0/42** unnegated items. The frozen-for-this-recount lexicon is whole-word stems for `wrong`, `incorrect`, `flawed`, `violat*`, `impossible`, `illogical`, `inconsisten*`, `unrealistic`, and `contradic*`. NLA's corresponding editorial counts are **30/42** versus **23/42**, so this particular status association is Oracle-specific.

The Oracle examples criticize chronology, factual plausibility, or procedure while continuing to write the positive event. This is evidence of an association between the status manipulation and readout form, **not** proof that Oracle preserves the factual polarity correctly. Both markers occur in every prompt, but order/recency heuristics remain possible explanations; the task does not isolate full logical scope understanding.

**Banks / both readers.** E49. The relation to status appears in both readers through different expressions: explicit negation for NLA, editorial fault language for Oracle. No cross-bank replication of the 38/42 versus 0/42 contrast is claimed.

**Three verbatim examples, without per-item true status:**

- E49 NLA, `f8c61dc25adf639bb30b2274`: “it is not the case that following the timestamp entry the safety interlock was disabled”
- E49 NLA, `9f0a30e49cfd308ff3af529a`: “Final fragment "it is not the case that after the calibration sequence was completed the safety interlock was disabled"”
- E49 Oracle, `8518be4fc6093e1e2e7af473`: “This violates chronological integrity. A proper log would state:”

**Novelty.** New truth-conditioned refinement of first-pass E49 P4/P8. The first pass counted negation words but could not establish whether they selected the current clause's actual status. The Oracle editorial association is a new candidate channel that a “not”-only audit misses.

**Confirmatory test on new items.** Cross clause polarity, clause order, event plausibility, and chronology independently. Use fresh benign propositions and both lexically explicit negation and paraphrases. Freeze the editorial marker before collecting outputs, and have blind humans separately score target-proposition polarity, logical scope, and commentary about prose quality or event plausibility. A genuine status-associated editorial channel should survive counterbalancing chronology and plausibility; a recency heuristic should fail when the most recent marker belongs to a closed clause.

## P3.2 — Hypothetical status is more often replaced by a story about a flawed example than carried into the reconstructed event

**Hypothesis.** The NLA sometimes converts a hypothetical-versus-asserted distinction into a genre judgment about “correct” and “incorrect” examples, leaving the event it quotes unqualified.

**Count.** All **84/84** E49 asserted/hypothetical prompts contain both “It is the case that” and “Suppose, counterfactually, that,” with their order changed. NLA readouts contain `hypothetical`, `counterfactual*`, or `suppos*` on **2/42** hypothetical and **0/42** asserted items; Oracle has **0/84** occurrences. In both NLA hits (**2/2**), “counterfactual” labels a logic-puzzle format, rather than explicitly qualifying the reconstructed final event. NLA quotes a `Final fragment` or `Final token` in **84/84** readouts, with **0/84** of those quoted spans carrying the screened modality terms, including **0/42** in the hypothetical subgroup.

The alternative error framing—`wrong`, `incorrect`, or `flawed`—occurs in NLA **24/42** hypothetical versus **9/42** asserted readouts; Oracle has **0/84**. This is a status-associated framing difference, not a count of explicit false affirmations. A quoted fragment can omit its governing clause without asserting that the event occurred. Also, the negation and hypothetical rows differ in their event content and discourse, so the contrast with P3.1 does not establish that counterfactuality is intrinsically harder than negation.

**Banks / both readers.** E49. Absence of explicit hypothetical vocabulary occurs in both; substitution into an error/example genre is primarily NLA. E49 topic-twin shares these readouts and is not an independent replication.

**Three verbatim examples, without per-item true status:**

- E49 NLA, `6c8c52f2717fc4f3552843af`: “The "counterfactual" logic puzzle format: the text contrasts correct/incorrect document types,”
- E49 NLA, `c72764bc209e13e08a0759e3`: “The "counterfactual" logic puzzle format (from the earlier "if...then" clause)”
- E49 NLA, `3311e169d2ddd3bde274b202`: “The "incorrect" example demonstrates a deliberate topic-switching error,”

**Novelty.** Refines first-pass E49 P3/P4 with truth-conditioned counts and the distinction between a modality word describing genre and modality attached to the target event. The first pass already noticed sparse counterfactual language; the proposed substitution mechanism is the hypothesis to test.

**Confirmatory test on new items.** Use the same event text under assertion, negation, counterfactual, quoted report, and question forms, counterbalancing source and scope order. Ask independent coders whether the readout attributes the status to the event, merely describes a document genre, or leaves status unspecified. Keep these scores separate from whether the event's entities and verbs are reconstructed correctly. The hypothesis predicts more genre substitutions than event-level status statements for counterfactuals, even after equalizing vocabulary and context.

## P3.3 — A retained prohibition can become the NLA's reason to predict the prohibited concept next

**Hypothesis.** The NLA can preserve the negative wording of a constraint while assigning it a different discourse function: a cue for what the response should complete or repeat.

**Count.** In E57 focus-ignore, **7/84 NLA** readouts pass a deliberately narrow screen requiring both negative-instruction wording (`do not think`, `without thinking`, or `avoid thinking`) and a completion forecast mentioning birds/avian content. The forecast screen searches `next token/word` within 180 characters, or `must be/complete/conclude` within 100 characters, before that concept. Oracle has **0/84** hits under this NLA-style wording screen; that is not evidence that Oracle lacks analogous implicit continuations. Existing judge codes call **6/7** screened NLA readouts `states_value`; the seventh is silent. The screen is an observable co-occurrence estimate, not an exhaustive semantic rate.

These readouts forecast a callback or repetition of the constraint. That can preserve negation inside the predicted text, so it is **not** a direct logical contradiction or evidence that the target model is thinking the forbidden concept. There is no measured target-model next-token agreement in this comparison. The point is the change from an instruction's prohibition to a reader's positive expectation about the next textual mention.

**Banks / both readers.** E57; the quantified formulation is NLA-specific. E61 D4's different endpoint and complete absence of concept mentions, documented in theme 6, prevents treating this as a universal white-bear result. E57 focus-ignore's failed probe gate precludes a decodable-state claim.

**Three verbatim examples:**

- E57 NLA, `1a4b0b8a51940bb2323a6eb8136782fa`: “which must be completed with "birds" to mirror the opening constraint exactly,”
- E57 NLA, `c5f40d2bae0579ada2b482bb9f2e8797`: “the next token must complete this phrase, almost certainly "birds" echoing the opening instruction,”
- E57 NLA, `1026b33c917f35d645dd65da0fc57e78`: “the next word should reference birds/avian creatures, completing the thematic callback to the opening constraint about avoiding bird-related thoughts.”

**Novelty.** Refines the first pass's instruction-echo observation with a counted same-readout combination of prohibition and affirmative continuation forecast. It contributes a discourse-role distinction, rather than a new claim that negation is simply inverted. Theme 9 addresses whether the judge should credit the resulting mentions.

**Confirmatory test on new items.** Independently vary “do not think about,” “do not mention,” “quote the instruction,” and “repeat only the unrelated sentence,” using novel concepts and matched read positions. Score preserved negative wording, predicted next mention, actual next-token probability, and eventual output separately. A new human rubric must distinguish a negated quotation from an affirmed fact and a continuation forecast from a claim about current state. This tests whether the effect is repetition-template selection, leakage into future output, or merely reader invention.

## Limits of this theme

No general polarity confusion matrix is claimed: these banks do not fully cross proposition, modality, source, and reader position. Reported-speech and question/assertion handling therefore remain confirmatory-test factors, rather than established findings here. The strongest new result is that absence of the word “not” need not imply absence of all status information. None of these analyses establishes unverbalised motivation, deception, or a model belief.
