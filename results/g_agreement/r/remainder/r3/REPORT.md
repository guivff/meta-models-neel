# R3 — cross-reader consensus

Completed 2026-10-19T22:41:44.497854+00:00; CPU only, 0 pod/judge spend. BRIEF_R §21.

21,198 held-out test items; 108 nondefect R-A facts; 34 corpus groups. Native votes are primary. Four readers: J-lens42, Oracle44, NLA42, skip_a42.

Intervals are the envelope of 1,000 fact→item and corpus→fact→shared-document paired bootstraps, equal fact weighting. Pool calibrations and reader selection are held fixed. Each effect is method minus control; negative ECE differences improve calibration.

| Reference | Method | Accuracy [95% CI] | Δ accuracy vs best [95% CI] | ECE [95% CI] | Δ ECE vs best [95% CI] |
|---|---|---|---|---|---|
| label | majority | 0.6551 [0.6067, 0.6971] | -0.015286 [-0.037492, -0.000041] | 0.1592 [0.1252, 0.2120] | 0.1468 [0.1030, 0.1877] |
| label | best_single | 0.6704 [0.6304, 0.7126] | 0.0000 [0.0000, 0.0000] | 0.0124 [0.0094, 0.0351] | 0.0000 [0.0000, 0.0000] |
| label | confidence_weighted | 0.6862 [0.6410, 0.7304] | 0.0158 [0.0029, 0.0275] | 0.2423 [0.2017, 0.2966] | 0.2299 [0.1790, 0.2720] |
| label | prevalence | 0.5000 [0.4914, 0.5092] | -0.1704 [-0.2135, -0.1287] | 0.0145 [0.0036, 0.0263] | 0.0021 [-0.0202, 0.0070] |
| target_probe | majority | 0.6532 [0.6042, 0.6989] | -0.0258 [-0.0471, -0.0078] | 0.1568 [0.1255, 0.2129] | 0.1467 [0.0991, 0.1897] |
| target_probe | best_single | 0.6791 [0.6360, 0.7255] | 0.0000 [0.0000, 0.0000] | 0.0101 [0.0089, 0.0360] | 0.0000 [0.0000, 0.0000] |
| target_probe | confidence_weighted | 0.6975 [0.6510, 0.7455] | 0.0185 [0.0041, 0.0334] | 0.2329 [0.1913, 0.2899] | 0.2229 [0.1643, 0.2651] |
| target_probe | prevalence | 0.4919 [0.4796, 0.5077] | -0.1872 [-0.2346, -0.1383] | 0.0043 [0.0013, 0.0228] | -0.0058 [-0.0268, 0.0004] |
| pair_conditional_model | majority | 0.6794 [0.6363, 0.7201] | -0.0017 [-0.0254, 0.0200] | 0.1663 [0.1252, 0.2298] | 0.1162 [0.0726, 0.1613] |
| pair_conditional_model | best_single | 0.6811 [0.6383, 0.7287] | 0.0000 [0.0000, 0.0000] | 0.0500 [0.0226, 0.1093] | 0.0000 [0.0000, 0.0000] |
| pair_conditional_model | confidence_weighted | 0.6909 [0.6349, 0.7432] | 0.0099 [-0.0145, 0.0298] | 0.2414 [0.1951, 0.3043] | 0.1914 [0.1414, 0.2354] |
| pair_conditional_model | prevalence | 0.4999 [0.4487, 0.5455] | -0.1812 [-0.2436, -0.1214] | 0.0538 [0.0196, 0.1151] | 0.0037 [-0.0143, 0.0305] |

**Frozen decision rule:** label accuracy gain ≥ .02, lower 95% bound >0, ECE deterioration ≤ .02.
- majority: **NOT DEMONSTRATED** (Δ accuracy -0.015286 [-0.037492, -0.000041]; Δ ECE 0.1468 [0.1030, 0.1877]).
- confidence_weighted: **NOT DEMONSTRATED** (Δ accuracy 0.0158 [0.0029, 0.0275]; Δ ECE 0.2299 [0.1790, 0.2720]).

**Actual greedy target comparison: NOT AVAILABLE.** R-A prompt-only `model_says_pos` is the sign of teacher-forced pair-conditional LO; it is not a saved unconstrained full-vocabulary greedy continuation. Its separately named comparator above cannot answer agreement with the model’s actual greedy text. Existing `model_labels.RB.jsonl` belongs to ReaderBench and does not cover this R-A population.

**Probe reference:** reused TH-2-F1 logistic state probe at L42, fitted on 256 globally document-clean pool items; this is not probe(512). Agreement with a probe is a comparator, not truth validation. Every reference is evaluated on its own declared available coverage.

**Calibration:** majority probability is fraction of positive native votes. Weighted probability is a positive native vote fraction weighted by pool reliability and calibrated support for each vote, with majority fallback. Best-single confidence is a pool-calibrated native-decision probability clipped at .5 when calibration disagrees; accuracy retains the native decision even at confidence .5. ECE is ten fixed equal-width bins. The calibrated-vote sensitivity, every per-tag result, and both bootstrap intervals are in `metrics.csv`. Pool-derived best-single is a per-fact selection policy, not an oracle chosen on test accuracy.

**TH-2 caveat:** shared difficulty already predicts four-reader failure tails on these facts. Reader agreement, a majority gain, or good ECE does not establish independent evidence or a shared neural mechanism. These are retrospective natural-state results. No conclusion about sample recurrence is possible before the pending R6 generation and separately approved truth/support judging.

**Sampling prepared, not launched:** R6 `--profile r3-sampling` uses the same 20 frozen states per C1–C4, 8 samples per state/reader/site, temperature .7, top_p .9, top_k 64. Kenney recurrence is semantic support in 8 reports for first-sample atomic claims; the lexical proxy in `for_michael.md` is not substituted. Judge/rubric is preregistered in R6; evaluate support thresholds 1/8…8/8 and preserve confident wrong claims. Estimate 0.33 pod-h (site count and output length may increase this); launch requires per-experiment go, booking, guards, coverage smoke, and Mac pull before stop.

CPU wall time: 30.5s. Provenance: pod `local-cpu-remainder-r3`, git `6e2e5f32db911fe96d91a56f1808422723264411`, code `901ba064aba9131fa023e28e69a24acf9b0fc85427d03b6a2950b934ddbfab1a`. Inputs and provenance audits: `sources.json`; coverage/exclusions: `coverage.csv`; pool fits: `pool_fits.csv`; full predictions in experiment cache. No shared input artifacts were changed.

**Deviations:** The pre-compute native-primary clarification is appended to §21 and PLAN. No rule or threshold changed after seeing R3 results. Other-bank multi-reader panels are outside this frozen R-A analysis rather than pooled across incompatible coverage. Genuine greedy is missing; collecting it would require separately approved inference.

**Reviewer limitation:** The primary ECE contrast compares raw vote-fraction confidence to a pool-calibrated single-reader confidence. This directly tests whether agreement itself is calibrated, but it does not show that an aggregate could not be calibrated on additional held-out pool data. The calibrated-vote sensitivity still has confidence-weighted Δ accuracy +0.016992 [0.004617, 0.030159] and Δ ECE +0.050452 [0.023283, 0.064034] versus its calibrated best-single. Calibrating the aggregate itself would require a separately registered pool allocation; it was not fitted post hoc. ECE is pooled with equal fact weights, not the average of per-fact ECE.
