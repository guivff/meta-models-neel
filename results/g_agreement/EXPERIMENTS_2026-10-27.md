# Experiments of 27 Oct 2026 (E56-E78)

This project grades activation readers (the Oracle lens, the NLA and the J-lens) on Qwen3.6-27B against facts
established without them. Everything below is pre-registered in `projects/g_agreement/BRIEF_UNDERSTAND.md` (sections
§168 onwards); a section number in this file points there. Nothing here is a new result: sealed numbers are the
coordinator's, quoted verbatim, and anything not yet reported is marked "pending" or "not yet reported".

**Statement rate.** S = (correct-only - wrong-only) / N, where correct-only is the readouts a blind rubric codes as
stating the correct value and not the wrong one, wrong-only the converse, and N the number of test items (one greedy
readout per item; §172 clarifications 2 and 4). The interval is a 95% percentile item bootstrap (2,000 draws, seed
20261027). **REPORTED** means S >= 0.20 with the bootstrap lower bound > 0. MISSED is any other probe-passing row.
Oracle lens read at block 44, NLA at block 42 (512 tokens with a stop rule for every run after §172 clarification 3).

Times in the BRIEF are CET; hashes below are the ones quoted in the BRIEF notes (commits, seals or packet ids as the
note says). Status as of the end of 27 Oct.

## 1. Status

| Experiment | Question | BRIEF | Status | Key hashes (BRIEF notes) |
|---|---|---|---|---|
| E56 | Does any reader report what the workspace paper places outside the workspace? | §172 | sealed result | c4ac59e1, 61dc67e1 |
| E57 | Do more workspace-paper properties (multi-token, focus/ignore, persistence, capacity, syntax) transfer? | §173 | sealed result | analysis seal 1f8bf286 |
| E58 | Is bookkeeping computed beneath the workspace (E58a labels by category; E58b J-ablation)? | §174 | E58b sealed result; E58a not determinable from the BRIEF | cc0346b3 (E58b) |
| E59 | Do the readers see the model's plans and intentions? | §175, §176 dev. | running (readers run; analysis pending) | forecast c2dbe177 |
| E60 | Blind-spot predictor: J-fraction to P(report), leave-one-bank-out | §176 | registered (needs E49, E56, E57, E59 analyses; R3 scored first) | none |
| E61 | Demonstrations D1-D6 and the white-bear test | §177 | D4 sealed; D1-D3, D5, D6 not determinable from the BRIEF | cd77d7d9 (no forecast required), 89f52d31 (superseded) |
| E61 D4 | White bear: use without report | §177 | sealed result (premise fails) | cd77d7d9 |
| E61 D4a | Robustness concepts and mention arm | §177 amend. 1-2 | running or ready; not determinable | 1872f28 (conventions) |
| E62 | Workspace Ladder: same state, five rungs (Oracle only) | §178 | sealed result | analysis seal e6bdab57; 1872f28, f0ffb76 |
| E62P | Placebo rungs L1p, L2p, L4p | §178 amend. 1 | NOT RUN (NO_FIT) | none |
| E63 | Placebo floor for the readers | §179 | registered (reader output not yet reported) | none |
| E64 | ReaderBench packaging | §180 | registered (due Wed 28 Oct 18:00 CET) | none |
| E65 | Workspace membership vs lag coherence | §182 | recapture done (566 s, USD 0.83); analysis pending | see §182 notes |
| R3b (E52) | Prospective J-space forecast over E56, E57, E59, E62 | §181 | registered; scoring pending (E59 forecast committed in time) | c2dbe177 |
| E66 | Blind spot in the wild on GLM 5.3 rollouts (542 records) | §183 | blocked (awaits judging) | b221cf55 |
| E67 | Reader fidelity audit | §184 | blocked (awaits a packet format adapter) | none |
| E68 | Distance-to-output | §185 | running (two state rows) | 2587767, 5b377a93 |
| E69 | Behaviour column for missed states | §186 | blocked (NO_FIT on a likely forecasting bug, being fixed) | none |
| E70 | Dose injection | §187 | running | 2c88aaf2 |
| E71 | Human validation of the judge | §188 | running (packet out to one human coder) | 8bac3e82 (0a38a3c5 superseded) |
| E72 | Earlier-layer read | §189 | running | none |
| E49 NLA supplement | NLA re-run of E49's 8 gated rows at 512 tokens (descriptive) | §172 cl. 3, §189 | running | b0ec2828 |
| E73 | Wild census on Qwen with probes | §191 | running (sampler in progress) | none |
| E74 | Replication on GLM 5.3 | §192 | ready; awaits GPU allocation (cap USD 100); R-G2 NOT EVALUABLE | f92e261f, afa98d4d |
| E75 | The predictor at scale | §193 | ready (scorer sealed, awaits pooled forecast units) | d57f0f0c |
| E76 | Placebo at scale | §194 | ready (cap 6,100 s), awaits split parity | none |
| E77 | omega-J-lens on Qwen | §195 | registered; gated at Wed 12:00 | none |
| E78 | Tier-1 NLA 512-token re-run on E49, E54, W1/E36 structure rows | §190-§195 cl. 1 (item 2) | registered (status not determinable) | none |

## 2. Sealed results

### E56. Out-of-workspace content (§172)

**Design.** Nine rows plus an injection arm. Four implicit rows with asked twins (tense, line-wrap, language
continuation, adjective), anomaly_state (no twin), fact_recall (expected to be verbalised), and three in-workspace
positive controls (reasoning_bridge, rhyme_plan, instructed_focus). Items are 84 dev plus 84 test with A/B balance,
length ratio <= 1.10 and BOW <= 0.65 on implicit rows. Channels: probe, J-lens G3, J-fraction label, Oracle lens and
NLA native readouts judged by one blind rubric. Rules: R1 (probe >= 0.90 and J-lens G3 <= 0.60 on implicit rows 1-5), R2
(a reader reports >= 2 R1-passing rows), R3 (asked - implicit >= 0.30 on the twin pairs), R4 (non-J injection <= 0.25 x
J-component injection). Gate: S >= 0.30 on at least 2 of 3 positive controls, per reader.

**Judging.** 2,256 records judged; 2,219 kept; 37 unparseable; USD 0.90.

**Positive-control gate: FAILED for both readers.**

| Control | Oracle S | NLA S |
|---|---|---|
| rhyme_plan | 0.345 | 0.202 |
| reasoning_bridge | 0.226 | -0.012 |
| instructed_focus | 0.036 | 0.024 |

fact_recall is reported by both readers (Oracle 0.774, NLA 0.726).

**Verdicts.**
- R2, R3, R4 and the R2 falsifier: **NOT EVALUABLE** (the gate failed for both readers).
- R1 (probe >= 0.90 and J-lens G3 <= 0.60): passes 2 of 5 rows.

| Row | J-lens G3 | R1 |
|---|---|---|
| linewrap_implicit | 0.430 | pass |
| tense_implicit | 0.437 | pass |
| adjective_implicit | 0.691 | fail |
| language_continuation | 0.824 | fail |
| anomaly_state | no G3 | NOT EVALUABLE |

- Descriptive only: linewrap_implicit Oracle 0.000, NLA -0.024; tense_implicit Oracle 0.487, NLA 0.241.
- Unparseable above 5% on the Oracle lens: adjective_implicit 13/84, language_continuation 9/84, anomaly_state 6/84,
  tense_implicit 6/84.

**Deviations that apply.** §172 clarifications 1-4 (asked-twin construction, the S definition with bootstrap replacing
Wilson, NLA at 512 tokens, one readout per item); §172 R4 clarification 1; the empty value-token clarification
(2026-10-27 14:15 CET) that makes anomaly_state NOT EVALUABLE for R1; the §149 compute deviation and the 13:40 compute
replan (E56_0 and E56_1 were the shards complete when the first joint run closed; the shard history of the rest is
not reproduced here).

### E57. More workspace-paper properties (§173)

**Design.** Group A: paper properties not yet covered (multi_token_entity, focus/ignore/mention, category_switch,
capacity, antonym_crosslingual, count_gradient, linewrap, two_hop_answer, sentiment_judgement). Group B (amendment 1,
rows 7-13): low-level syntactic and bookkeeping state (subject_number, clause_pending, nesting_depth, indent_level,
loop_direction, page_range_digit, section_header), predicted OUT-J and unreported. Rules: R-A1 (a reader beats the
J-lens on multi_token_entity: S >= 0.20 while J-lens G3 <= 0.65), R-A2 (focus ordering think >= mention > ignore > none
with think - none CI excluding 0), R-B (of the probe-passing Group B rows, at least 5 of 7 OUT-J or DIFFUSE, and
neither reader reports more than 2; falsifier: >= 5 of 7 IN-J or a reader reports >= 5 of 7).

**Judging.** 3,360 records judged; 3,321 kept; 39 unparseable; USD 1.29. Analysis seal 1f8bf286.

**Verdicts.**
- **R_B: NOT MET.** Each reader reported 3 Group B rows; the rule allows at most 2. The falsifier is false.
- **R_A1: NOT EVALUABLE.** multi_token_entity has no G3.
- **R_A2: MET for the NLA** (think - none CI [0.048, 0.167]); **NOT MET for the Oracle lens.**

**Group B rows** (J-category; forecast; probe AUROC; S with 95% CI for each reader):

| Row | J | Forecast | Probe | Oracle S [CI] | NLA S [CI] |
|---|---|---|---|---|---|
| subject_number | DIFFUSE | MISSED | 0.961 | +0.232 [0.122, 0.341] REPORTED | +0.226 [0.143, 0.321] REPORTED |
| clause_pending | IN-J | REPORTED | 1.000 | +0.259 [0.160, 0.358] REPORTED | +0.262 [0.083, 0.429] REPORTED |
| nesting_depth | OUT-J | MISSED | 1.000 | +0.014 [-0.068, 0.096] | +0.143 [0.060, 0.238] |
| indent_level | DIFFUSE | MISSED | 1.000 | -0.012 [-0.048, 0.024] | 0.000 |
| loop_direction | IN-J | REPORTED | 1.000 | +0.427 [0.305, 0.549] REPORTED | +0.562 [0.463, 0.663] REPORTED |
| page_range_digit | DIFFUSE | MISSED | 1.000 | -0.083 [-0.214, 0.036] | +0.095 [0.024, 0.167] |
| section_header | DIFFUSE | MISSED | 1.000 | +0.025 [-0.138, 0.200] | +0.119 [-0.071, 0.310] |

**Group A rows:**

| Row | J | Forecast | Probe | Oracle S [CI] | NLA S [CI] |
|---|---|---|---|---|---|
| focus_think | DIFFUSE | MISSED | 0.718 | +0.226 [0.143, 0.310] REPORTED | +0.262 [0.179, 0.357] REPORTED |
| focus_mention | DIFFUSE | MISSED | 1.000 | +0.143 [0.036, 0.250] | +0.083 [0.024, 0.155] |
| focus_ignore | DIFFUSE | MISSED | 0.002 (likely a sign convention; being checked) | +0.071 [-0.024, 0.167] | +0.083 [0.036, 0.143] |
| category_switch | not forecast | n/a | 1.000 | +0.313 [0.157, 0.470] REPORTED | +0.651 [0.518, 0.771] REPORTED |
| antonym_crosslingual | DIFFUSE | MISSED | 0.777 | -0.012 | 0.000 |
| count_gradient_first_letter | DIFFUSE | MISSED | 1.000 | -0.012 | -0.060 |
| linewrap_implicit | DIFFUSE | MISSED | 1.000 | -0.012 | -0.012 |
| linewrap_asked | DIFFUSE | MISSED | 1.000 | +0.012 | +0.060 |
| multi_token_entity | IN-J | REPORTED | 0.730 | +0.548 [0.440, 0.655] REPORTED | +0.274 [0.179, 0.381] REPORTED |
| sentiment_judgement | IN-J | REPORTED | 1.000 | +0.583 [0.429, 0.738] REPORTED | +0.738 [0.631, 0.833] REPORTED |
| two_hop_answer | DIFFUSE | MISSED | 0.862 | +0.293 [0.195, 0.402] REPORTED | +0.155 [0.083, 0.226] |

**Other measures.**
- Category switch, switch/stay/drop: Oracle 0.310 / 0.976 / 0.683; NLA 1.000 / 1.000 / 0.000. The registered descriptive
  cut (drop >= 50% tracks the workspace; <= 20% reads beyond it) has not been applied in the sealed results given to
  this file: not yet reported.
- Capacity (mean distinct items per readout): Oracle 1.226, NLA 1.548; no reader exceeds six.

**Coordinator's tally (descriptive, not a registered test; the registered pooled test is E75).** The pre-committed
J-forecast was correct on 14/17 forecast rows for the Oracle lens and 15/17 for the NLA, against a constant-MISSED
baseline of 10/17 and 11/17. All 4 IN-J rows were reported by both readers.

**Deviations that apply.** §173 amendment 1 and clarifications 1-2; §172 clarifications 2-4; the empty value-token
clarification (14:15 CET) for multi_token_entity; the §149 compute deviation and the 13:40 compute replan.

### E58b. J-ablation of bookkeeping behaviour (§174; sealed `cc0346b3`)

**Design.** Block-44 projection of the sealed J basis (rank 384) versus random rank-384 subspaces and a pooled PCA
control, on rows with frozen continuation pairs; metric is the continuation log-odds drop. R-b1 (sanity): J damage
>= 2 x random on >= 2 of 3 in-J rows (clarification 1). R-b2: J damage <= 1.25 x random on >= 70% of
bookkeeping/delimiter/syntactic rows.

**Results (from the dated note of 07:25 CET, which reads the sealed file).** R-b1 HOLDS (2/3). **R-b2 DOES NOT HOLD
(15/25).** The coordinator's note owns a design error: random damage is near zero on most rows, so the ratio is
dominated by noise in the denominator, and no interval had been registered. The verdict stands. The note adds, labelled
post hoc, per-row bootstrap CIs (no rerun) and the absolute comparison (J damage <= 0.1 log-odds on 20 of 25
bookkeeping/delimiter/syntactic rows, 17 of them negative, against rhyme_plan 1.68; PCA damage >= 0.8 on 15 of 25). No
claim rests on the post hoc items until the CIs exist. E58a (categories and J-fractions) is not reported here.

### E62. The Workspace Ladder, Oracle lens only (§178)

**Design.** Five states (S1 bracket depth, S2 line length, S3 tense, S4 language, S5 subject number), each put through
five rungs: L0 implicit, L1 mention, L2 track, L3 asked, L4 decision (behaviour: base-model P(alpha) - P(beta)).
S6 is an eval-context ladder C0-C4 with no A/B. Rules: R-L0 (probe >= 0.90 at every rung), R-L1 (S(L4) - S(L0) >= 0.30
on >= 4 of 5 states and rung-S Spearman >= 0.8), R-L2 (rho(J-fraction, S) >= 0.6), R-L3 (L4 behaviour AUROC >= 0.80 on
>= 4 of 5), R-L4 (S6: eval mention C4 - C0 >= 0.30), R-L5 (placebo rungs). The NLA channel was dropped for cost, so
the NLA is NOT RUN for E62 (13:40 CET compute replan). S6 judging ended 15:14Z. Analysis seal e6bdab57.

**Verdicts.**
- **R-L0 gate:** S1-S4 pass; S5 fails (probe 0.83-0.87 at L1-L2).
- **R-L1: NOT MET.** L4 - L0: S1 +0.18, S2 +0.04, S3 -0.48, S4 -0.75.
- **R-L2: MET.** rho(J, S) = 0.80; rho(rung, S) = -0.40.
- **R-L3: NOT MET.** Behaviour AUROC S1 0.17, S2 0.57, S3 0.94, S4 1.00, S5 0.84.
- **R-L4: NOT MET.** Eval ladder C4 - C0 = -0.69 [-0.79, -0.58]; mention rate C0-C4 1.00, 1.00, 0.58, 0.57, 0.31.
- **R-L5: NOT EVALUABLE** (E62P NOT RUN).

**Oracle S per rung:**

| State | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| S1 | -0.071 | -0.083 | -0.036 | 0.241 | 0.107 |
| S2 | 0.012 | -0.012 | 0.000 | 0.000 | 0.048 |
| S3 | 0.468 | 0.195 | 0.167 | 0.771 | -0.012 |
| S4 | 0.726 | 0.662 | 0.372 | 1.000 | -0.024 |
| S5 (gate fail) | 0.312 | 0.175 | 0.277 | 0.000 | -0.012 |

J-fractions are flat at 0.015-0.08. Value channel: 2,050/2,100 records kept. S6 channel: 420/420.

**Deviations that apply.** Oracle-only replan (13:40 CET); E62P without R-L5 (15:05 CET ruling c); the dated note of
09:35 CET that fixed the readings of "S flat", "S climbs, J flat" and "placebo rises" before outcomes (mean target J-fraction
by rung L0-L4 0.039, 0.034, 0.033, 0.034, 0.019, caveat: L3 and L4 are read at a different token); the S5 L4p
confound check (phi = +0.29, f0ffb76) that removes S5 from R-L5 at L4.

### E61 D4. White bear (§177)

**Design.** 84 items: an instruction about X in {birds, citrus} (think about X / do not think about X / none), a copied
unrelated sentence, then a completion whose answer is X-related. Readers read at the last token of the copied sentence;
base Qwen's P(answer) is measured at the completion. R-W: under "do not think", P(answer) >= 0.8 x its value under
"none" while the reader's X-mention rate is <= 0.5 x its rate under "think".

**Results.** Base model P(answer | ignore) / P(answer | none) = 0.276, so the premise fails. 0/84 mentions in every arm,
for both readers. **R-W: NOT EVALUABLE.**

**Deviations that apply.** The post-hoc judge pass on D4 was cancelled (15:05 CET ruling d): the verbatim readouts and
per-arm tallies show neither reader mentions the concept in any form. D4a (amendments 1-2, ratified 08:10 CET) is a
separate second bank and is not reported here. D4 ran before D3 under the 13:40 CET replan.

## 3. Work with no sealed result yet

- **E59:** forecast committed in time (c2dbe177; 4 REPORTED / 2 MISSED per reader). The readers have run; analysis is
  pending. The reader GO was bound to an identical unpublished commit; this is disclosed in the §176 E59 deviation.
- **Launched or running at the time of writing:** E68, E70, the E49 NLA supplement, E72.
- **E69** hit NO_FIT on a likely forecasting bug and is being fixed.
- **E76** is READY (cap 6,100 s) and awaits split parity.
- **E66** (GLM wild rollouts, 542 records) awaits judging. **E67** awaits a packet format adapter. **E73**: sampler in
  progress.
- **E74** is feasible on 4xB200 (asset card f92e261f) with the J-lens unavailable, so R-G2 is NOT EVALUABLE; it awaits
  GPU allocation, cap USD 100.
- **E71:** human coding is out to one coder. **E75:** scorer sealed (d57f0f0c). **E77:** gated at Wed 12:00.
- Compute so far: about USD 115 of the USD 300 daily ceiling at 16:15 CET (integrator account check).

## 4. Design deviations and clarifications made on 27 Oct (all dated in the BRIEF)

All of these were registered before the data they affect, as each note states.

- §172 cl. 1 (03:05): asked twin = complete implicit item plus question, read at the question's final token; adjective row must share the read token; injection_awareness stays in the E54 bank.
- §172 cl. 2 (05:10, question file c4ac59e1): S defined and bootstrap replaces Wilson ("Wilson lower bound" was a wording error); one rate for all rules; gates per reader.
- §172 cl. 3 (05:50): NLA native readouts at 512 tokens with stop rule (E49's 128-token NLA outputs were all truncated, 6ace33fa); E49 NLA supplement defined as descriptive.
- §172 cl. 4 (06:10): greedy decoding is deterministic, so one readout per item (N = items), not 8 per item.
- §172 R4 cl. 1 (08:05): R4 excludes rows failing the probe-margin or on-distribution diagnostics.
- §169 amendment 1 (02:55) and cl. 1-4 (02:45-03:55), dated note (05:45), reporting clarification (15:40): J-fraction label of record, R3 ground truth and denominator, and R3 flagged uninformative at the E49 base rate (2 REPORTED, 6 MISSED); basis sealed 1e46442e.
- §173 amendment 1 (04:15): Group B extended to rows 7-13 and R-B rewritten; cl. 1-2 (04:20, 05:15): count_gradient reuse, two_hop_answer added, Group B continuation pairs frozen (clause_pending pair corrected).
- §174 cl. 1-2 (04:20, 04:25): E58b in-J sanity rows and PCA control; sentiment_judgement and fact_recall added as a descriptive shallow-content group.
- §174 E58b dated note (07:25, cc0346b3): R-b2 verdict stands, design error owned, post hoc CIs added.
- §177/§171 judging cl. (07:40) and judging cl. 2 (08:45): per-record validation, single-record retries (up to 2), verbatim-evidence normalisation.
- §177 D4 amendments 1-2 (07:55, 08:05): D4a with two more concepts, a cross-concept arm, a mention arm and a concept probe.
- §178 amendment 1 (07:55): placebo rungs L1p, L2p, L4p and R-L5; ratification note (08:10, 1872f28) and R-L5 cl. 1 (08:15, f0ffb76).
- §178 dated note (09:35): J-fraction does not rise with rung; interpretations fixed before outcomes.
- §181 cl. 1-3 (06:00, 07:55, 08:05): R3b units and exclusions, category-only forecast comparison, within-category stratified test.
- §182 cl. 1-3 (06:25, 06:35, 06:40): C and P definitions, E65 recapture stage added (no stored capture has all positions), P measured on the registered bin.
- §149 compute deviation (08:55): E56, E57, E61 run at measured forecast x 1.25 within a USD 150 ceiling; joint-run rulings (09:05): E61 GO binding to cd77d7d9 (89f52d31 superseded) disclosed, E49 NLA supplement from joint source b0ec2828.
- Compute replan (13:40): 2 of 9 shards completed, priority order, E62 and E62P Oracle only, E49 supplement deferred (un-deferred at 15:40).
- §172/§173 clarification (14:15): empty value-token set means G3 NOT EVALUABLE (anomaly_state, multi_token_entity).
- Judging interface and E62P rulings (15:05): wire format, judgment adapter, E62 without E62P, D4 post-hoc judge cancelled.
- Follow-on rulings (15:15): list-valued rubric fields, E63 and D4a need no forecast, E59 GO window 2,700 s.
- §190-§195 cl. 1 (15:45): E74 assets re-specified, E78 defined, judging budgets need separate authorisation, track ownership.
- §185 E68 deviation 1 (16:00): positions re-anchored backwards from the answer (P_far, P_mid, P_pre); deviation 2 (16:40, 2587767): arith_compare infeasible and dropped, R-O1 needs both remaining state rows; compute deviation (16:55, 5b377a93): cap raised to 1.25 x 4,531 s.
- §194 E76 cl. 1 (16:00) and compute deviation (17:20): shared pool design; cap raised to 6,100 s.
- §188 E71 cl. 1-3 (16:00, 16:50, 16:58): packet from E49, E54, D4, E56 (8bac3e82, superseding 0a38a3c5); one independent human coder is enough, the judge is never a coder.
- §191 E73 cl. 2-3 (16:10, 16:40): W8 topic lists; the gated code corpus is replaced by an ungated one, W6 dropped unless a source is found; interval is the item bootstrap.
- §192 E74 cl. 2-5 (16:10, 17:00, 17:15, 17:35): R-G2 NOT EVALUABLE without the J-lens; ordinal rows exploratory; smoke criterion replaced (f92e261f); admission cap raised to USD 100 (afa98d4d).
- §183 E66 cl. 1 (16:45, b221cf55): sampling conventions ratified; five strata at achieved n (C 150, S1 128, S2 137, S3 68, S4 59); R-G3 reported unstratified.
- §187 E70 cl. 1 (16:50, 2c88aaf2): 8 carriers per row ratified as built; no carrier dropped for probe margin.
- §176 E59 deviation (16:55, c2dbe177): reader GO bound to an unpublished identical commit; stands as a disclosed deviation.

Design reference for the E77 follow-on: Ostrow et al. 2026 (arXiv:2610.31955).
