# TH-3 — model margin versus reader confidence

Final report — 2026-10-20 03:43 Europe/Zurich. Branch `codex/th3`; Codex identity. Preregistration **`3425122`**, pushed before outcomes; tested implementation **`05063b4`**. Primary predictors are **absolute model margin A and absolute reader margin B**; hard means bottom tercile of absolute A. CPU only, existing data, zero GPU/model forwards. Numerical decision thresholds are unchanged.

**Three-sentence interpretation.** The four native readers—Qwen Oracle lens (community `olens_s3d_rl600`), NLA, J-lens and skip-lens—meet **NO INDEPENDENT CONFIDENCE**, while mass-mean meets **INDEPENDENT CONFIDENCE**; LR's confidence gain remains **UNDERPOWERED/MIXED** after BH correction (q=0.129), despite clearing the unadjusted CI threshold. LR alone meets **USEFUL WHEN UNSURE**: 72.7% accuracy versus 64.9% prompt-only, a **+7.8 percentage-point gain (95% CI +3.5 to +14.8; q=0.098)**. Independent confidence does not ensure a hard-item advantage: mass-mean's reader−prompt-only gap is −0.6 percentage points (95% CI −4.3 to +4.4), leaving its usefulness **UNDERPOWERED/MIXED**.

**Per-reader confidence results.** Intervals are the conservative envelope of item and corpus-clustered percentile intervals, with 2,000 draws per scheme and seed 0. Separate BH q=0.10 families retain all seven readers for each claim type. Each A/B/A+B comparison uses identical rows and five frozen fact folds.

| Reader | n / facts | AUROC(A), 95% CI | AUROC(B), 95% CI | Gain A+B−A, 95% CI | Gain 90% CI | Confidence verdict |
|---|---:|---:|---:|---:|---:|---|
| Qwen Oracle lens (community, olens_s3d_rl600) | 21198 / 108 | 0.600 [0.542, 0.645] | 0.520 [0.440, 0.555] | 0.001 [-0.011, 0.011] | [-0.008, 0.008] | NO INDEPENDENT CONFIDENCE |
| NLA | 21198 / 108 | 0.592 [0.536, 0.637] | 0.548 [0.456, 0.612] | 0.005 [-0.007, 0.027] | [-0.005, 0.023] | NO INDEPENDENT CONFIDENCE |
| J-lens | 21198 / 108 | 0.573 [0.505, 0.635] | 0.548 [0.474, 0.602] | 0.008 [-0.007, 0.038] | [-0.005, 0.031] | NO INDEPENDENT CONFIDENCE |
| Skip-lens | 21198 / 108 | 0.596 [0.544, 0.650] | 0.499 [0.426, 0.560] | -0.002 [-0.009, 0.007] | [-0.007, 0.004] | NO INDEPENDENT CONFIDENCE |
| LR probe (256) | 20400 / 102 | 0.637 [0.543, 0.728] | 0.747 [0.712, 0.794] | 0.114 [0.050, 0.216] | [0.056, 0.201] | UNDERPOWERED/MIXED |
| Mass-mean probe (256) | 20400 / 102 | 0.568 [0.515, 0.617] | 0.682 [0.646, 0.725] | 0.118 [0.084, 0.168] | [0.089, 0.160] | INDEPENDENT CONFIDENCE |
| Prompt-only | 21198 / 108 | 0.807 [0.709, 0.880] | 0.807 [0.709, 0.880] | 0.000 [-0.000, 0.000] | [-0.000, 0.000] | NO INDEPENDENT CONFIDENCE |

Mass-mean gain is 0.1183 [0.0845, 0.1681], BH q=0.00350. LR gain is 0.1139 [0.0498, 0.2162], but q=0.12944: §25 requires both the CI gate and BH rejection. The registered threshold-centered bootstrap p-value uses a different tail condition from a percentile interval; an asymmetric bootstrap distribution can therefore pass that CI gate and fail the adjusted test. Native-reader NO INDEPENDENT CONFIDENCE q-values are all 0.00070, as is the structural PO control. These labels concern added value in the specified logistic family, not the existence of arbitrary nonlinear independent information.

**Model-unsure items.** Hard cutoffs are empirical within-reader-cohort terciles, with all boundary ties retained; PO comparisons are paired on precisely the same rows. LR's q=0.09795 is a narrow pass of the fixed q=0.10 rule at the registered 2,000 draws, not evidence of a stable margin from the multiplicity boundary. No bootstrap count or threshold was changed.

| Reader | Hard n | Reader accuracy, 95% CI | Matched PO accuracy, 95% CI | Reader−PO, 95% CI | Usefulness verdict |
|---|---:|---:|---:|---:|---|
| Qwen Oracle lens (community, olens_s3d_rl600) | 7066 | 0.552 [0.532, 0.582] | 0.650 [0.612, 0.707] | -0.098 [-0.137, -0.057] | UNDERPOWERED/MIXED |
| NLA | 7066 | 0.538 [0.517, 0.559] | 0.650 [0.612, 0.707] | -0.112 [-0.162, -0.073] | UNDERPOWERED/MIXED |
| J-lens | 7066 | 0.549 [0.525, 0.576] | 0.650 [0.612, 0.707] | -0.101 [-0.145, -0.064] | UNDERPOWERED/MIXED |
| Skip-lens | 7066 | 0.549 [0.524, 0.583] | 0.650 [0.612, 0.707] | -0.100 [-0.142, -0.057] | UNDERPOWERED/MIXED |
| LR probe (256) | 6800 | 0.727 [0.668, 0.807] | 0.649 [0.611, 0.711] | 0.078 [0.035, 0.148] | USEFUL WHEN UNSURE |
| Mass-mean probe (256) | 6800 | 0.643 [0.602, 0.700] | 0.649 [0.611, 0.711] | -0.006 [-0.043, 0.044] | UNDERPOWERED/MIXED |
| Prompt-only | 7066 | 0.650 [0.612, 0.707] | 0.650 [0.612, 0.707] | 0.000 [0.000, 0.000] | UNDERPOWERED/MIXED |

Native readers are below prompt-only on model-unsure items (−0.10 to −0.11, CIs exclude 0); the registered rule defined only the positive verdict, so this is reported as an interval, not a verdict.

**Accuracy by model-confidence tercile.** The vertical bars show wider 95% bootstrap intervals, with terciles recomputed in each draw. This is observed accuracy versus model margin, not a probability-reliability diagram. Reader cohorts differ only for the two probes; their paired PO values are in the table above and in CSVs.

![Reader accuracy by absolute model-margin tercile; wider 95% bootstrap intervals](th3_calibration.png)

[Vector plot](th3_calibration.svg) · [Plot values](th3_calibration.csv) · [Six-reader one-pager PNG](th3_calibration_onepager.png)

**Coverage reported before fitting.** LABEL_DEFECT exclusions match TH-2; all 341 input hashes and semantic joins passed, with no native candidate-margin exclusions. Coverage was communicated before mass-mean projection and correctness fitting.

| Cohort | Items | Facts | Corpus groups | One-sided / two-sided facts |
|---|---:|---:|---:|---:|
| Four native readers and PO | 21,198 | 108 | 34 | 75 / 33 |
| LR (256 labels) and mass-mean (256 labels) | 20,400 | 102 | 32 | 69 / 33 |
| Native readers and PO, audit excluded | 20,626 | 104 | 34 | — |
| Probes, audit excluded | 20,200 | 101 | 32 | — |

Both probes lack the same 798 items across six facts with no frozen 256-label draw: `130_temp_cat_Frequency`(122), `131_temp_cat_Typical Time`(100), `132_temp_cat_Event Ordering`(104), `142_cancer_cat_Thyroid_Cancer`(158), `143_cancer_cat_Lung_Cancer`(200), `144_cancer_cat_Colon_Cancer`(114). Each of the 102 available draws has 128 labels per class and excludes every frozen test document; mass-mean uses exactly the LR draw and a pool-centroid midpoint threshold. Audit flags cover facts 131, 142, 144, 153. [Pre-fit coverage](th3_coverage.md), [fact-level coverage](th3_coverage.csv), [source and fold manifest](th3_source_manifest.json).

**Score and vote conventions.** A comes from base-Qwen's own full-candidate forced-choice scoring rows, the same source as PO; for multi-token candidates it is an absolute summed-log-probability difference. There is no separate broad natural-computation model-margin source in this frozen bank. B is each reader's absolute native candidate margin, including J-lens's semantic short-form cosine contrast; it is not median-distance confidence. The original four-reader correctness columns are TH-2's literal `literal_err_*`: sign for two-sided facts, test-score median for one-sided facts, ties negative. WS3 has adjudicated that §4.7 convention; the historical all-median implementation is a sensitivity below. On 75 of 108 facts, candidate-margin magnitude therefore differs from distance to the actual median vote boundary, which limits broad claims about reader confidence. Probes and PO use their frozen signed class decision>0. PO has identical A and B; its tiny observed gain (0.000000455) can arise from duplicated features changing effective L2 regularization and cross-fold calibration, and does not constitute new information.

**Registered descriptive strata.** These strata use the true label through signed A and are unavailable as label-free deployment rules. “Model confidently wrong” has signed A<0 and absolute A in the top tercile; its PO accuracy is zero by construction. No primary usefulness claim is assigned to these descriptive comparisons.

| Reader | Descriptive stratum | n | Reader accuracy, 95% CI | Reader−PO, 95% CI |
|---|---|---:|---:|---:|
| Qwen Oracle lens (community, olens_s3d_rl600) | Model confidently wrong | 100 | 0.380 [0.187, 0.512] | 0.380 [0.187, 0.512] |
| Qwen Oracle lens (community, olens_s3d_rl600) | Bottom signed A | 7066 | 0.536 [0.500, 0.573] | 0.027 [-0.108, 0.185] |
| NLA | Model confidently wrong | 100 | 0.440 [0.264, 0.618] | 0.440 [0.264, 0.618] |
| NLA | Bottom signed A | 7066 | 0.512 [0.480, 0.548] | 0.004 [-0.132, 0.161] |
| J-lens | Model confidently wrong | 100 | 0.480 [0.269, 0.583] | 0.480 [0.269, 0.583] |
| J-lens | Bottom signed A | 7066 | 0.517 [0.478, 0.566] | 0.008 [-0.117, 0.163] |
| Skip-lens | Model confidently wrong | 100 | 0.400 [0.227, 0.503] | 0.400 [0.227, 0.503] |
| Skip-lens | Bottom signed A | 7066 | 0.523 [0.480, 0.573] | 0.015 [-0.109, 0.173] |
| LR probe (256) | Model confidently wrong | 71 | 0.408 [0.222, 0.594] | 0.408 [0.222, 0.594] |
| LR probe (256) | Bottom signed A | 6800 | 0.698 [0.631, 0.794] | 0.174 [0.073, 0.332] |
| Mass-mean probe (256) | Model confidently wrong | 71 | 0.352 [0.182, 0.533] | 0.352 [0.182, 0.533] |
| Mass-mean probe (256) | Bottom signed A | 6800 | 0.613 [0.570, 0.691] | 0.090 [-0.019, 0.256] |
| Prompt-only | Model confidently wrong | 100 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| Prompt-only | Bottom signed A | 7066 | 0.509 [0.332, 0.673] | 0.000 [0.000, 0.000] |

**Registered point sensitivities.** Signed-A fits retain absolute B and introduce model correctness into A. Audit-excluded fits drop all flagged facts; all-median fits retain the historical implementation's votes. These are point descriptions with no new confirmatory verdicts; all AUCs, accuracies and stratum counts are in [th3_points.csv](th3_points.csv).

| Reader | Primary gain | Signed-A gain | Audit-excluded gain | All-median-vote gain |
|---|---:|---:|---:|---:|
| Qwen Oracle lens (community, olens_s3d_rl600) | 0.001 | 0.001 | 0.000 | -0.001 |
| NLA | 0.005 | 0.004 | 0.006 | 0.001 |
| J-lens | 0.008 | 0.005 | 0.008 | 0.003 |
| Skip-lens | -0.002 | -0.001 | -0.002 | -0.000 |
| LR probe (256) | 0.114 | 0.096 | 0.114 | 0.114 |
| Mass-mean probe (256) | 0.118 | 0.106 | 0.119 | 0.118 |
| Prompt-only | 0.000 | -0.000 | -0.000 | 0.000 |

**Inference and validation.** Each bootstrap refits every training-only standardized C=1 logistic model on the other four fact folds and recomputes the relevant weighted terciles. The item bootstrap resamples semantic items; the corpus bootstrap resamples frozen TH-2 union groups, including shared source families/texts. All 2,000 draws per scheme are valid for every reader's gain and hard difference, with zero optimizer failures or constant-fit fallbacks. All draws remain paired across readers, models and PO controls. The fact holdout retains 470 normalized texts crossing folds (972 item rows); corpus-clustered intervals account for dependence but do not remove this text overlap, so unseen-document/corpus generalization remains unestablished. Hypothesis families are separate seven-reader families, not one global 21-test family. Undefined draws would count conservatively against rejection; none occurred for the primary claims.

Twenty-three focused tests passed, and three planted write guards failed as intended without protected writes. Fifty independent numerical stress cases agreed with sklearn; independent real-data point fits agreed within 1.18e-8 AUC, bootstrap spot refits within 1.93e-8, and all hard-stratum arithmetic matched exactly. The independent bootstrap verifier reproduced all interval endpoints, centered p-values, BH q-values, final/chunk hashes and exact verdicts. [Point audit](th3_independent_verification.json) · [Bootstrap audit](th3_independent_bootstrap_verification.json).

Two pre-outcome loader validation fixes were operational: float32 transformed-score replay tolerance and provenance-counter bookkeeping. They changed no inputs, thresholds or retained data; the two successful preflight attempts produced identical preprojection hashes. The first failed preflight did not capture exact CPU/wall time and is explicitly unmetered in the ledger. No scientific deviation or post-outcome tuning occurred.

**Reproduction and outputs.** From the isolated worktree with the frozen source caches and saved F1 probe artifacts, run:

```sh
.venv/bin/python -B -m projects.g_agreement.r_bench.th3_data preflight
.venv/bin/python -B -m projects.g_agreement.r_bench.th3_data project --coverage-reviewed
.venv/bin/python -B -m projects.g_agreement.r_bench.th3_stats point
.venv/bin/python -B -m projects.g_agreement.r_bench.th3_stats bootstrap --scheme item --workers 2
.venv/bin/python -B -m projects.g_agreement.r_bench.th3_stats bootstrap --scheme corpus --workers 2
MPLCONFIGDIR=/tmp/th3-matplotlib .venv/bin/python -B -m projects.g_agreement.r_bench.th3_report
.venv/bin/python -B -m projects.g_agreement.r_bench.th3_verify
.venv/bin/python -B -m projects.g_agreement.r_bench.th3_verify_bootstrap
```

[One row per reader](th3_summary.csv) · [All intervals, including constituent schemes](th3_intervals.csv) · [Raw and BH-adjusted p-values](th3_claims.csv) · [Run manifest](th3_run.json). Large derived row and bootstrap arrays remain ignored under `.th3_cache/`; their hashes, seeds and complete chunk checks are recorded. Shared caches and the main checkout were left unchanged. HANDOFF.md records the result commit for the integrator.
