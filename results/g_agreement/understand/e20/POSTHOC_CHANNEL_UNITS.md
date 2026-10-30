# E20 channel units versus E15

Post-hoc, descriptive only, requested in §112 dated note 10:05 CET at 97cfc5dd. No inference, generation, probe fit, bootstrap, AUROC calculation or registered-analysis rerun was performed for this report. Existing verdicts stand. Numerical values below are copied from the original sealed analysis.

**The sealed E20 scores do not permit the requested E15-style candidate-pair score on E20 distance-2 items.** That quantity would require new teacher-forced model scoring on the saved activations. It is a proposed run, not a result.

Numbering correction: the dated note says “Channel 4 (asked).” The registered channels and frozen implementation identify **channel 4 as teacher-forced consequence scoring; channel 5 is asked scoring**. The failed sentiment control makes channel 4 uninterpretable under the registered rule; it does not transfer that rule to channel 5. Channel 3 stands.

## Exact score units

The acquisition record is one text's block-44 activation at one distance, with A as the fixed positive state. Each test row × distance has 80 A/B text pairs, i.e. 160 activation records. AUROC ranks the 80 A scores against the 80 B scores with half credit for ties. It is not within-twin-pair accuracy. Near/far analysis first averages each text's scores over its registered distances, then computes AUROC.

| Channel | One activation record's score | What it does not score |
|---|---|---|
| 3: lens generation | Integer 0–4: number of four separately generated native readout strings containing the frozen A-event. One greedy string plus three sampled strings, each capped at 16 generated tokens; samples use temperature 1, top-p .95, top-k 64. The code calls these strings “bullets”; it runs the parser once on each whole string. Dividing by four would preserve AUROC. | Neither candidate likelihood nor a count of all event occurrences. Not one shared 64-token generation or a teacher-forced four-bullet sequence. |
| 4: teacher-forced consequence | One scalar per true/random/opposite activation arm: summed log-probability of the exact A consequence token sequence minus that of the exact B sequence, conditioned on the native Oracle carrier with the injected activation, separately tokenized `- ` prefix, then the recipient's exact real intervening token IDs. Only candidate tokens contribute to the score. | Not immediate-next-token scoring after the carrier; not the likelihood of the whole intervening text; not length-normalized. Not E15's candidate pairs. |
| 5: asked | Two stored A-minus-B native candidate log-likelihood contrasts, one per frozen phrasing pair; the analysis averages the two contrasts per activation. Each candidate's token log-probabilities are summed. Candidates themselves contain the frozen leading `- `; the scorer adds no separate prefix here. | Not a generated answer, parse accuracy, or consequence likelihood. |

Channel 3's fixed A-events are: an unmatched closing `)`; for string, a quote immediately after the first word (after optional leading bullet removal), or an odd number of double quotes; whole-word `wonderful` (case-insensitive); exact digit-bounded `1234`. Each counts as positive in BOTH A and B source states. These are the unchanged frozen parser rules, not newly judged structural assertions.

Channel 4's frozen candidate token IDs are:

| Row | A consequence | B consequence | Exact token IDs A / B |
|---|---|---|---|
| prose_paren | closing parenthesis token | neutral twin comma token | `[847]` / `[1116]` |
| python_string | closing double-quote token | neutral twin `note` token | `[328]` / `[5020]` |
| prose_sentiment_delayed | `wonderful` slot token | `terrible` slot token | `[10794]` / `[16958]` |
| fact_once | `1234` recurrence | `5678` recurrence | `[16,17,18,19]` / `[20,21,22,23]` |

These are the tokens frozen from the full source-text tokenization; the token IDs, including their contextual whitespace behavior, are authoritative. In particular, the structural candidates are not the separately tokenized bare punctuation used in E15. Fact scoring sums all four autoregressive digit-token log-probabilities, conditioning later digits on the earlier digits of that candidate. Random/opposite arms change the injected activation while preserving the recipient's intervening text and candidates.

For completeness, channel 1 is the base model's fraction of eight sampled 16-token continuations containing that same fixed A-event; channel 2 is the dev-trained probe's test decision score. Neither is an Oracle-lens output channel.

## E15's candidate-pair score

For each W1 test activation, E15 scores each frozen pair `(A_j, B_j)` directly after the unchanged native Oracle carrier plus separately encoded `- `:

`score_j(h) = log P(A_j | carrier(h), '- ') - log P(B_j | carrier(h), '- ')`.

Each log-probability sums candidate-token log-probabilities. The primary per-activation score averages only the pairs that passed E15's base-reference dev validity gate. Both pairs passed for paren and string. E15 computes AUROC across 84 W1 test items per row (42 per state), not E20's new 160 test texts per distance.

| Row | E15 pair 1 | E15 pair 2 | E20 channel-4 contrast |
|---|---|---|---|
| prose_paren | `)` versus `(` | `)\n` versus `(\n` | Context-tokenized closer versus comma, after d−1 real intervening tokens |
| python_string | `"` versus `0` | `"\n` versus `.\n` | Context-tokenized quote versus `note`, after d−1 real intervening tokens |

Here `\n` denotes an actual newline in the frozen candidate. E15 candidate token IDs are paren `[8]`/`[7]` and `[8,198]`/`[7,198]`; string `[1]`/`[15]` and `[1,198]`/`[13,198]`.

Thus E15 and E20 differ in the source items, the conditioning context, candidate alternatives, tokenization and averaging over candidate pairs. E20 channel 3 also changes the observable from teacher-forced log-odds to spontaneous event occurrence under a 16-token generation cap. Their numerical gap alone cannot identify which difference caused it.

## What the seals contain, and what cannot be recovered

All 5,760 E20 `lens.jsonl` records have exactly these fields: `id`, `feature`, `bullets`, `positive_count`, `asked`, `consequence`, `donors`. Each has four readout strings, two asked contrasts, and three consequence scalars (`true`, `random_donor`, `opposite_donor`). No full-vocabulary logits, separate candidate probabilities or E15-pair evaluations are stored. The partial lens file adds no different score type.

Every distance-2 record has **one intervening source token** before the consequence, including all 160 test records per row. Distance 2 therefore does not collapse to E15's empty intervening context. Even full logits at E20's consequence position would not recover logits under E15's different conditioning prefix. The scalar differences stored here cannot be transformed into the missing likelihoods, and the generated strings cannot supply exact candidate-pair likelihoods either.

The sealed block-44 activations would support a proposed new scoring-only comparison: select the existing E20 distance-2 test items, use E15's exact two pairs and native prefix with no intervening tokens, and average the already E15-valid pairs for paren/string. That requires new model forwards and separately authorized/frozen scope, budget and reporting. It was not run, and no E15-style E20 AUROC is claimed.

Existing E20 distance-2 test AUROCs, copied unchanged from `analysis_jm1vm4gw487fhn/metrics.json`:

| Row | Channel 3 generation | Channel 4 consequence, true activation | Channel 5 asked |
|---|---:|---:|---:|
| prose_paren | 0.506328125 | 0.548125 | 0.4775 |
| python_string | 0.4809375 | 0.49734375 | 0.4959375 |
| prose_sentiment_delayed | 0.91875 | 1.0 | 1.0 |
| fact_once | 0.616328125 | 0.6990625 | 0.72546875 |

These remain their original E20 channels. Channel 4 remains uninterpretable under the failed registered far-sentiment control, despite the distance-2 descriptive values.

Evidence: frozen `e20_worker.py` (`Engine.lens`, `Engine.consequence`, `consequence_layout`), `e20_parser.py`, `e20_analysis.py`; sealed E20 input bank and `lens.jsonl`; E15 `native_score`, `CONTINUATION_PAIRS.json` and original analysis; vendored Oracle `logprob_of_strings`/`paired_logodds_templates`. Verification hashes and source-binding checks are recorded in POSTHOC_CHANNEL_AUDIT.json. Original report, metrics, analysis lock and seals were not modified.
