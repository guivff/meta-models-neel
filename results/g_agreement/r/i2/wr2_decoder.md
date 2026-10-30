**WR-2 Stage2 verdict: INCONCLUSIVE_H_CONTROL_FAILURE.**

Jh does not satisfy the registered rule and the original-state h positive control also fails. This run cannot distinguish a naming limitation from insufficient training, optimization or population support; it does not establish information loss.

Jh canonical full-name EM: **0.00% [+0.00, +0.00]%** (95% CI). h positive control: **FAIL**. Every point estimate averages the three paired training seeds for each item before computing the micro rate.

**Zero-event interval caveat.** Every observed test outcome is zero, so the registered component bootstrap necessarily returns [0, 0] intervals. These are degenerate empirical percentile intervals, not evidence of exactly zero population success probability. The descriptive per-seed Wilson intervals below are [0, 1.48%] and ignore clustering; they do not replace the registered decision intervals.

**Canonical primary contrasts**

Differences are percentage points; bracketed bounds are paired 95% CIs. A control contrast passes only with point gain ≥ 10 pp and lower bound > 0.

| Contrast | Point [95% CI], pp | Pass |
| --- | --- | --- |
| Jh − Native-token only | +0.00 pp [+0.00, +0.00] pp | False |
| Jh − Shuffled Jh | +0.00 pp [+0.00, +0.00] pp | False |
| Jh − Mean Jh | +0.00 pp [+0.00, +0.00] pp | False |
| h − Native-token only | +0.00 pp [+0.00, +0.00] pp | False |
| h − Shuffled Jh | +0.00 pp [+0.00, +0.00] pp | False |
| h − Mean Jh | +0.00 pp [+0.00, +0.00] pp | False |

Within-prefix donor minus recipient: **+0.00 pp [+0.00, +0.00] pp** (paired 95% CI), n=242. Donor-name match 0.00%; recipient-name match 0.00%.

| Arm | Canonical full-name EM [95% CI] |
| --- | --- |
| Jh | 0.00% [+0.00, +0.00]% |
| h | 0.00% [+0.00, +0.00]% |
| Native-token only | 0.00% [+0.00, +0.00]% |
| Shuffled Jh | 0.00% [+0.00, +0.00]% |
| Mean Jh | 0.00% [+0.00, +0.00]% |

h−Jh: **+0.00 pp [+0.00, +0.00] pp** (paired 90% CI); equivalence within ±5 pp: **ESTABLISHED**. This equivalence decision is separate from naming support. Formal EM equivalence can pass when both h and Jh are at the performance floor; that is not successful naming or a successful positive control. The h positive control uses the same three control-gain criteria; A successful h control would demonstrate that this fixed architecture and schedule can recover canonical names from h on this population.

**Alias sensitivity, separate from the primary**

Alias-aware sensitivity verdict: **INCONCLUSIVE_H_CONTROL_FAILURE**; Jh EM 0.00% [+0.00, +0.00]%. Only the frozen source-backed semantic full-name aliases count here. Conservative holdout links, unobserved spellings, exclusion phrases, demonyms and standalone currency codes do not become correct outputs. This result never replaces the canonical verdict.

| Sensitivity contrast | Point [95% CI], pp |
| --- | --- |
| Jh − Native-token only | +0.00 pp [+0.00, +0.00] pp |
| Jh − Shuffled Jh | +0.00 pp [+0.00, +0.00] pp |
| Jh − Mean Jh | +0.00 pp [+0.00, +0.00] pp |
| Donor − recipient | +0.00 pp [+0.00, +0.00] pp |

**Source, tag and independent-group descriptions**

These rows are descriptive. No selected subgroup supplies the pooled decision or additional independent replication.

| Source | Items | Components | Parents | Identities | Jh | h | Native-token only | Shuffled Jh | Mean Jh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-X PersonaQA context | 104 | 9 | 72 | 75 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| ReaderBench KHOP | 152 | 1 | 19 | 16 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |

| Tag | Items | Components | Parents | Identities | Jh | h | Native-token only | Shuffled Jh | Mean Jh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CONTEXT | 104 | 9 | 72 | 75 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| KHOP | 152 | 1 | 19 | 16 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |

| Component | Items | Components | Parents | Identities | Jh | h | Native-token only | Shuffled Jh | Mean Jh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rb_khop_3hop_middle::prefix_4725 | 152 | 1 | 19 | 16 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| x01_ao_personaqa_base:favorite_boardgame::prefix_1124 | 4 | 1 | 2 | 2 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| x01_ao_personaqa_base:favorite_boardgame::prefix_3156 | 6 | 1 | 4 | 2 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| x01_ao_personaqa_base:favorite_food::prefix_24646 | 4 | 1 | 2 | 2 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| x02_ao_personaqa_fantasy:favorite_boardgame::prefix_11908 | 2 | 1 | 2 | 2 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| x02_ao_personaqa_fantasy:favorite_boardgame::prefix_13892 | 75 | 1 | 51 | 55 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| x02_ao_personaqa_fantasy:favorite_boardgame::prefix_16405 | 2 | 1 | 2 | 2 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| x02_ao_personaqa_fantasy:favorite_boardgame::prefix_25565 | 4 | 1 | 3 | 4 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| x02_ao_personaqa_fantasy:favorite_boardgame::prefix_6438 | 5 | 1 | 4 | 4 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| x02_ao_personaqa_fantasy:favorite_food::prefix_12142 | 2 | 1 | 2 | 2 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |

**Seed and generation diagnostics**

Wilson 95% intervals below describe each realized seed while ignoring clustering; they are not decision CIs. The primary bootstrap does not estimate uncertainty over a population of training seeds.

| Arm | Seed | Correct /256 | EM [descriptive Wilson 95%] |
| --- | --- | --- | --- |
| Jh | 20261031 | 0 | 0.00% [0.00%, 1.48%] |
| Jh | 20261032 | 0 | 0.00% [0.00%, 1.48%] |
| Jh | 20261033 | 0 | 0.00% [0.00%, 1.48%] |
| h | 20261031 | 0 | 0.00% [0.00%, 1.48%] |
| h | 20261032 | 0 | 0.00% [0.00%, 1.48%] |
| h | 20261033 | 0 | 0.00% [0.00%, 1.48%] |
| Native-token only | 20261031 | 0 | 0.00% [0.00%, 1.48%] |
| Native-token only | 20261032 | 0 | 0.00% [0.00%, 1.48%] |
| Native-token only | 20261033 | 0 | 0.00% [0.00%, 1.48%] |
| Shuffled Jh | 20261031 | 0 | 0.00% [0.00%, 1.48%] |
| Shuffled Jh | 20261032 | 0 | 0.00% [0.00%, 1.48%] |
| Shuffled Jh | 20261033 | 0 | 0.00% [0.00%, 1.48%] |
| Mean Jh | 20261031 | 0 | 0.00% [0.00%, 1.48%] |
| Mean Jh | 20261032 | 0 | 0.00% [0.00%, 1.48%] |
| Mean Jh | 20261033 | 0 | 0.00% [0.00%, 1.48%] |

| Arm | Seed | Valid /256 | No EOS | Invalid UTF-8 | Overflow | Mean content bytes |
| --- | --- | --- | --- | --- | --- | --- |
| h | 20261031 | 256 | 0 | 0 | 0 | 14.11 |
| h | 20261032 | 256 | 0 | 0 | 0 | 12.08 |
| h | 20261033 | 256 | 0 | 0 | 0 | 9.80 |
| Jh | 20261031 | 255 | 1 | 1 | 1 | 13.40 |
| Jh | 20261032 | 256 | 0 | 0 | 0 | 13.05 |
| Jh | 20261033 | 256 | 0 | 0 | 0 | 13.44 |
| Mean Jh | 20261031 | 256 | 0 | 0 | 0 | 12.00 |
| Mean Jh | 20261032 | 256 | 0 | 0 | 0 | 12.00 |
| Mean Jh | 20261033 | 256 | 0 | 0 | 0 | 6.00 |
| Native-token only | 20261031 | 256 | 0 | 0 | 0 | 13.06 |
| Native-token only | 20261032 | 256 | 0 | 0 | 0 | 13.03 |
| Native-token only | 20261033 | 256 | 0 | 0 | 0 | 11.66 |
| Shuffled Jh | 20261031 | 256 | 0 | 0 | 0 | 8.51 |
| Shuffled Jh | 20261032 | 256 | 0 | 0 | 0 | 6.09 |
| Shuffled Jh | 20261033 | 256 | 0 | 0 | 0 | 7.18 |

Failure counts overlap. All output-length distributions, pool diagnostics and train-loss traces are preserved in the linked tables; invalid/no-EOS/overflow generations remain incorrect.

The donor mapping retains 242 of 256 test items and trims 14 only for the registered within-block bijection. The main 256-item endpoint is unchanged. Trim records and per-seed donor links are retained in the inference summary and donor table.

**Post hoc diagnostic: failure to generalize to held-out names**

An independent raw-byte and item-ID/target-join check reproduced every zero test result. In the saved pool predictions, h full-name EM averaged **43.49%** across seeds (151, 281 and 253 correct out of 525); Jh averaged **57.71%** (278, 313 and 318/525). On test, **768/768 h outputs** and **765/768 Jh outputs** were canonical pool names. All 160 distinct pool canonical names are disjoint from the 93 test canonical strings (91 audited identity components). This is evidence of failed held-out name generalization by this fixed decoder, not a scoring normalization mismatch. It does not identify whether more suitable architecture, optimization or training data would succeed.

These counts are explicitly post hoc diagnostics from already saved outputs, with no new fits, generation, bootstrap or changed decision rule. The [diagnostic JSON](wr2_decoder_artifacts/additional_24.json) and [reproduction script](wr2_decoder_artifacts/zero_diagnostic.py) preserve the exact joins and metadata-selected examples.

**Actual collection and admission evidence**

Independent collection admission: **PASS_ACTUAL_COLLECTION_AND_FROZEN_COVERAGE**. Independent post-inference audit: **PASS_INDEPENDENT_POST_INFERENCE_AUDIT**. The observed column comes only from the actual admission artifact. Registered fixed targets and unchanged minimum coverage gates are shown separately; a lower minimum is not permission to replace the frozen population.

| Quantity | Actual observed | Fixed target | Minimum coverage gate | Recorded gate | Fixed population match |
| --- | --- | --- | --- | --- | --- |
| test | 256 | 256 | 256 | PASS | True |
| pool | 525 | 525 | 512 | PASS | True |
| names | 91 | 91 | 32 | PASS | True |
| prefixes | 31 | 31 | 8 | PASS | True |
| components | 10 | 10 | 8 | PASS | True |
| sources | 2 | 2 | 2 | PASS | True |
| blocks | 35 | 35 | exact plan / structural check | PASS | True |
| new_test_states | 14 | 14 | exact plan / structural check | PASS | True |
| new_pool_states | 0 | 0 | exact plan / structural check | PASS | True |

Detailed counts and gate flags: [actual_admission.csv](wr2_decoder_artifacts/actual_admission.csv).

**Population and inferential limits**

The registered pool contains **525 rows: 184 KHOP and 341 INTERNAL**. The registered test contains **256 rows: 152 KHOP and 104 CONTEXT**, of which 242 are cached and 14 are the proposed PersonaQA name substitutions. There are 91 held-out identity components, 31 first-token prefixes, 35 same-question/prefix blocks, 10 independent components and two test sources. The pool has no CONTEXT-tag training rows; the test has no INTERNAL-tag rows. These tag differences and the restricted currency/favorite-name target population limit generalization.

The frozen metadata plan holds out names, source-backed aliases, conservative exclusion links, templates and complete captures under the finite-corpus audit. That audit checks the observed cached metadata and frozen raw sources; it is not a claim to enumerate every possible natural-language alias. The 14 recombinations reuse the original PersonaQA generator and frozen raw name vocabulary, retaining their prototype parents and existing groups; they add coverage, not independent groups. LABEL_DEFECT, provisional-label and wrong-bridge exclusions persist. Coverage gates are not a formal power calculation.

The canonical metric requires the complete name after Unicode NFC, casefold and collapsed/stripped whitespace, preserving punctuation and articles. It is not candidate ranking or substring matching. The registered inference resamples 10 fixed components, including all prototype siblings, jointly 10,000 times with seed 20261101; arms and contrasts use the same draws. Seeds and repeated contexts are not independent primary observations.

**Interpretation**

h≈Jh is expected because J42 is full rank; finite-sample optimization and regularization can still differ. Informative contrasts are Jh against the native-token bottleneck and the shuffled/mean state controls, plus within-prefix donor following. The prior random-subspace recovery caveat remains: recoverability does not establish privileged J-lens geometry, that J is necessary, or target-model causal use. Failure of this small decoder cannot prove the represented fact is gone.

Stage2 full-name exact-match differences cannot be expressed as percentages of WR-2’s +0.174 AUC gap: population, endpoint and comparator differ. The earlier Stage1 label-free rule is separate. This learned byte readout, fixed schedule and restricted population do not establish a universal multi-token naming theorem.

**Collection, compute and provenance**

Scientific preregistration: BRIEF_R §21, commit `35b83e8681864eb05246d8571d9a6deb81281c3a`. Report assembled 2026-10-20T00:35:41.659956+00:00. Branch observed at assembly: `r/i2-wr2`; implementation HEAD at assembly: `b53f1fab4c544b353cedd74e74b97c0fd0b2066f`.

The registered collection uses the pinned Qwen3.6-27B revision, exact embedding plus blocks 0–42 in bfloat16 on CPU, block 42 output at the chat assistant-onset token, fp16 stored states, batch 1 and four threads. All four sentinels must individually pass cosine ≥ .999 and relative-L2 ≤ .03 after storage conversion. Historical exact input IDs were not stored; rendering is reproduced from pinned capture contents, tokenizer/template and frozen renderer, with historical lengths/onset checked.

| Sentinel | Cosine | Relative L2 | Pass |
| --- | --- | --- | --- |
| rx-x01_ao_personaqa_base-test-0003 | 0.999911934 | 0.015598643 | True |
| rx-x01_ao_personaqa_base-test-0071 | 0.999959106 | 0.009233899 | True |
| rx-x02_ao_personaqa_fantasy-test-0116 | 0.999957720 | 0.009375057 | True |
| rx-x02_ao_personaqa_fantasy-test-0093 | 0.999954509 | 0.009759981 | True |

| Stage | Recorded CPU core-hours | Cap core-hours |
| --- | --- | --- |
| target_collection | 0.510892 | 24 |
| all15_training_fits | 0.062247 | 8 |
| feature_preparation_greedy_decoding_inference_and_audits | 0.006182 | 2 |
| post_inference_audit_already_included_above | 0.000177 | included above |
| independent_collection_admission_audit | 0.001566 | audit, reported separately |

Collection cumulative active wall: 1092.0475542080094 seconds (cap 21600). Recorded collection failures and resumes count toward its cumulative CPU/wall caps. The registered 15-fit schedule uses two spawned workers with one torch/BLAS thread each; the cap is aggregate CPU, not elapsed wall. Preparation, greedy decoding, statistical inference and the independent post-inference audit share the 2-core-hour cap. The final audit cumulative total already includes the earlier stages; the audit-only row is a diagnostic subset and must not be added again. The protocol requires CPU-only target collection, training and inference with zero GPU hours.

Recorded collection failure entries: 0. Saved failures, resource stops and incomplete-stage records: [failures.json](wr2_decoder_artifacts/failures.json). Only saved logs can be audited; absence of a failure entry is not evidence that no technical interruption occurred. Download/network wall and this report-assembly audit are distinct from decoder training time; supplied download logs are preserved without estimating missing durations. Overlapping download worker or resume wall durations are not summed as elapsed time.

Download completed within the approved limit: **47,719,652,128 unique bytes** for the 13 pinned shards needed through block 42, all SHA256-verified. Download elapsed **89.4 minutes**; aggregate download CPU **593.362082 seconds**. Overlapping helper wall times are not additive. This is the required prefix, not a complete local copy of all 27B-model weights. Target collection took **18.2 minutes elapsed / 30.7 CPU minutes**; the 15 fits took **224.090444 CPU seconds**, with training and decoding together **121.747407 seconds elapsed**.

The final audit ledger records **22.187128 CPU seconds** for preparation, greedy decoding, inference and the independent outcome audit. Adding the **0.019432-second** preparation metadata-writing tail and **0.047689-second** post hoc output diagnostic gives **22.254249 CPU seconds**, still below the unchanged 7,200-second cap. Report assembly is logged separately.

**Reproducibility artifacts**

[artifact_inventory.csv](wr2_decoder_artifacts/artifact_inventory.csv) records original locations, byte sizes and SHA256 for copied metadata, predictions and tables. [population.csv](wr2_decoder_artifacts/population.csv), [fit_diagnostics.csv](wr2_decoder_artifacts/fit_diagnostics.csv), [training_loss_trace.csv](wr2_decoder_artifacts/training_loss_trace.csv), [sentinel_metrics.csv](wr2_decoder_artifacts/sentinel_metrics.csv) and [budget.csv](wr2_decoder_artifacts/budget.csv) provide compact audit records. Large checkpoints, feature matrices and state arrays remain in cache under the recorded provenance hashes.

[table_contrasts.csv](wr2_decoder_artifacts/table_contrasts.csv), [table_groups.csv](wr2_decoder_artifacts/table_groups.csv), [table_seeds.csv](wr2_decoder_artifacts/table_seeds.csv), [table_matches.csv](wr2_decoder_artifacts/table_matches.csv), [table_donor_map.csv](wr2_decoder_artifacts/table_donor_map.csv), [table_decoding_diagnostics.csv](wr2_decoder_artifacts/table_decoding_diagnostics.csv), [table_output_lengths.csv](wr2_decoder_artifacts/table_output_lengths.csv).
