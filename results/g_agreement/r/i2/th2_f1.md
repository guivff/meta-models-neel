# TH-2-F1 — what the shared difficulty measures, and a label-free trust rule

Report date: 2026-10-19 UTC.

**Block A: USABLE. Held-out within-fact accuracy gap 16.4 [11.1, 20.6] percentage points (95% CI).**
**Block B: USABLE. Held-out within-fact accuracy gap 16.4 [11.5, 20.8] percentage points (95% CI).**

The available-feature rule meets the registered criterion with and without audit-flagged facts.
The criterion is a point gap ≥15 percentage points and a two-sided 95% lower bound >5 points. No H7 or TH-2 threshold or verdict changes.

**External-instrument result:** Probe256 and prompt-only positively share the fitted factor in both semantic classes and both audit blocks. The registered near-zero, reader-specific residual-factor pattern is not supported relative to these instruments; causal origin remains unresolved.

**Predictable signal:** Confidence margins are the strongest standardized feature associations. Posterior-target R² is 0.029 [-0.032, 0.078] in A and 0.033 [-0.027, 0.075] in B (95% CIs); these are weak global predictions of the diagnostic posterior, not estimates of variance explained in the true latent difficulty.

**Full requested feature panel: NOT RUN.** Genuine model surprisal at the read token was never cached. Candidate probabilities and next-token logit-lens scores were not substituted. Render is always chat and the layer configuration is fixed, so neither can be estimated as a predictor.

Registration: [BRIEF_R §17](../../../../projects/g_agreement/BRIEF_R.md), committed and pushed as `13cb102` before follow-up computation on 2026-10-19. TH-2 results motivated this retrospective follow-up; the endpoint rows are not a newly collected or human-unseen dataset.

![TH-2-F1 external loadings and held-out trust gaps](th2_f1_summary.png)

## Coverage was checked before fitting

| Block | Eligible facts | Corpus groups | Calibration items | Endpoint items | Corpus folds |
|---|---:|---:|---:|---:|---:|
| A | 102 | 32 | 10,246 | 10,154 | 5 |
| B | 101 | 32 | 10,157 | 10,043 | 5 |

Block A excludes LABEL_DEFECT facts. Block B additionally excludes the frozen audit flags from fitting, endpoints and empirical frequency source pools. Both blocks require at least ten complete items per class in each fixed half, at least twenty facts and all five folds.

The original four-reader sample contains 21,198 items; the six-instrument intersection retains 20,400. Native prompt-only joins have 0 repeated raw keys and 0 unmatched semantic keys. State and prompt-only labels, splits, candidates/provenance and finite states were checked before fitting.

Six facts lose coverage because the document-disjoint pool cannot supply exactly 128 examples of each label. No reduced-label probe or replacement fact was substituted.

| Excluded from follow-up | Clean pool T=0 | Clean pool T=1 |
|---|---:|---:|
| 130_temp_cat_Frequency | 30 | 39 |
| 131_temp_cat_Typical Time | 21 | 38 |
| 132_temp_cat_Event Ordering | 28 | 32 |
| 142_cancer_cat_Thyroid_Cancer | 42 | 43 |
| 143_cancer_cat_Lung_Cancer | 62 | 110 |
| 144_cancer_cat_Colon_Cancer | 32 | 35 |

[Coverage by fact/class/half](th2_f1_coverage.csv), [coverage communicated before fits](th2_f1_coverage.md), [feature availability](th2_f1_feature_coverage.csv), and [input/probe manifest](th2_f1_manifest.json) record the audit. Every available feature is finite on the retained sample; absent read-token surprisal is reported separately.

## Held-out trust rule

Within each fact, endpoints are ranked only by predicted difficulty, with item-ID tie breaks and fractional boundary weights. The lowest and highest 20% of weighted mass are compared, then selected item weights are pooled across facts. Accuracy is mean correctness of the original four readers, not consensus accuracy.

| Block | Lowest difficulty: accuracy, 95% CI | Highest difficulty: accuracy, 95% CI | Gap, pp, 95% CI | Verdict |
|---|---:|---:|---:|---|
| A | 73.4 [67.6, 78.1]% | 57.0 [53.2, 61.7]% | 16.4 [11.1, 20.6] | USABLE |
| B | 73.3 [68.3, 78.2]% | 57.0 [53.1, 61.7]% | 16.4 [11.5, 20.8] | USABLE |

Even the lowest-difficulty quintile retains 26.6% mean reader error in A and 26.7% in B. USABLE means relative risk ranking under this registered contrast, not item-level correctness certification.

The scorer is **endpoint-label-free**: neither held-out labels, error bits, correctness, signed answer preference nor fact/class error rates enter its feature matrix. Its development is supervised: probe256 uses exactly 256 pool labels, and the ridge target is an error-conditioned posterior learned from other-fold calibration items. “Label-free” does not mean no labels were used anywhere.

| Original reader | A gap, pp, 95% CI | B gap, pp, 95% CI |
|---|---:|---:|
| J-lens | 16.0 [9.0, 22.1] | 16.2 [9.6, 22.7] |
| Oracle | 17.4 [10.9, 23.7] | 17.2 [11.0, 23.7] |
| NLA | 15.0 [6.3, 21.1] | 15.1 [6.8, 21.3] |
| Skip-a | 17.2 [10.0, 23.2] | 17.1 [10.6, 23.5] |

## What shares the factor?

The six-instrument one-factor model fits all fifteen pairwise error tables separately by semantic class, training dependence only in other corpus folds. The original four nonnegative loadings anchor orientation; the two external loadings can be signed. The reported estimate is the equal-fold mean loading.

| Block | Instrument | T | Loading, 90% CI | Loading, 95% CI | Registered classification |
|---|---|---:|---:|---:|---|
| A | Probe256 | 0 | 0.419 [0.305, 0.578] | 0.419 [0.279, 0.612] | POSITIVE SHARED |
| A | Probe256 | 1 | 0.403 [0.302, 0.536] | 0.403 [0.280, 0.569] | POSITIVE SHARED |
| A | Prompt-only | 0 | 0.407 [0.220, 0.670] | 0.407 [0.180, 0.713] | POSITIVE SHARED |
| A | Prompt-only | 1 | 0.458 [0.330, 0.608] | 0.458 [0.298, 0.636] | POSITIVE SHARED |
| B | Probe256 | 0 | 0.421 [0.294, 0.584] | 0.421 [0.268, 0.615] | POSITIVE SHARED |
| B | Probe256 | 1 | 0.408 [0.306, 0.537] | 0.408 [0.287, 0.566] | POSITIVE SHARED |
| B | Prompt-only | 0 | 0.417 [0.225, 0.674] | 0.417 [0.181, 0.721] | POSITIVE SHARED |
| B | Prompt-only | 1 | 0.461 [0.321, 0.605] | 0.461 [0.294, 0.632] | POSITIVE SHARED |

Both external instruments positively share the fitted factor in both classes and blocks: every 95% lower bound exceeds .10. This does not support the registered near-zero, reader-specific residual-factor pattern.

Near-zero requires the whole two-sided 90% CI inside [−.10,.10] and adequate error/correct counts. Positive shared requires the 95% lower bound >.10. Neither classification identifies a causal source: common item difficulty, task/protocol features, measurement reliability and the target model’s representations remain compatible explanations. A positive external association does not establish that the cause is intrinsic to the item or located inside the model.

## How much difficulty is predictable?

| Block | Endpoint posterior R², 95% CI | Correlation, 95% CI | Global-quintile gap, pp, 95% CI |
|---|---:|---:|---:|
| A | 0.029 [-0.032, 0.078] | 0.192 [0.106, 0.286] | 23.2 [12.6, 32.8] |
| B | 0.033 [-0.027, 0.075] | 0.199 [0.121, 0.283] | 23.4 [13.2, 32.9] |

The 95% R² interval includes zero in block(s) A, B; positive global explained variance in the posterior target is not established there.

R² measures the variance explained in the error-conditioned posterior target, not in the unknown true latent U. Posterior R² and correlation measure agreement with an error-conditioned diagnostic target exposed only after predictions and ranks are frozen. Their modest point estimates imply limited global explanation of item-by-item posterior difficulty. A useful extreme-quintile contrast can coexist with weak global prediction; it is not a precise difficulty estimate for every item. The within-fact gap, rather than the global-quintile contrast, carries the registered trust verdict.

The ridge uses alpha=10, training-only weighted standardization and an intercept. Below are equal-fold-mean coefficients per one training standard deviation of the feature, with 95% bootstrap CIs; negative means the feature predicts lower difficulty. These associations are not causal effects or a selected-feature model.

| Feature | A standardized coefficient, 95% CI | B standardized coefficient, 95% CI | Finite draws A / B |
|---|---:|---:|---:|
| log1p absolute prompt-only LO | -0.119 [-0.180, -0.080] | -0.121 [-0.181, -0.080] | 1990 / 1986 |
| log1p absolute probe margin | -0.101 [-0.145, -0.064] | -0.102 [-0.145, -0.063] | 1990 / 1986 |
| log1p input tokens | 0.002 [-0.090, 0.150] | -0.009 [-0.097, 0.130] | 1990 / 1986 |
| log1p prompt characters | 0.027 [-0.118, 0.116] | 0.038 [-0.099, 0.127] | 1990 / 1986 |
| Mean candidate-token negative log-frequency | -0.019 [-0.055, 0.014] | -0.019 [-0.053, 0.011] | 1990 / 1986 |
| Absolute candidate-frequency difference | -0.004 [-0.032, 0.024] | -0.004 [-0.031, 0.022] | 1990 / 1986 |

The main predictable signal is confidence: larger prompt-only and probe margins predict lower difficulty, with negative coefficient CIs in both blocks. The margin coefficients also dominate the other standardized coefficient point estimates.

The length and candidate-frequency coefficient intervals each include zero in both blocks.

Coefficient intervals use finite coefficient-mean replicates, whose counts are shown: a resample omitting an entire outer fold can leave the five-fold coefficient mean undefined without invalidating the primary trust-gap pipeline. No missing coefficient is imputed as a successful effect.

Candidate frequency is an **empirical training-pool proxy, not pretraining frequency**: the frozen local tokenizer, add-one token counts from unique other-fold pool documents, and the symmetric mean/absolute difference across both candidates. Every frozen-bank test document is excluded. These candidate summaries are fixed within each R-A fact, so they cannot directly alter its within-fact item ranking; they can affect between-fact calibration. All frequency counts and the registered probe256 fits remain fixed during bootstrap.

## Descriptive comparisons; no replacement verdict

| Ranking / sensitivity | A gap, pp | B gap, pp | Uncertainty |
|---|---:|---:|---|
| Ridge targeting four-reader posterior | 16.3 | 16.5 | Point only |
| Ridge targeting mean four-reader error | 15.8 | 15.7 | Point only |
| Prompt-only confidence alone | 12.3 | 12.4 | Point only |
| Probe confidence alone | 12.4 | 12.5 | Point only |
| Literal-sign reader-vote sensitivity | 15.5 | 15.8 | Point only |

Four-reader-posterior and direct-error targets nearly match the six-instrument target. No latent-target advantage over direct mean-error regression is demonstrated without paired comparison intervals. These point comparisons do not establish a statistically significant improvement over either confidence-only ranking. The literal sensitivity uses `lo > 0` for two-sided readers and the registered median rule for one-sided readers.

| Semantic class, same label-free selected weights | A gap, pp | B gap, pp |
|---|---:|---:|
| T=0 | 13.6 | 13.8 |
| T=1 | 18.9 | 18.7 |

The original H7 discrepancy remains unresolved: `analyze.py` uses test medians for every fact, whereas BRIEF_R §4.7 prose calls for the sign of two-sided log-odds. The primary follow-up preserves the existing implementation; literal-sign point estimates are separate. This discrepancy has been flagged to WS3; no H7 result is silently redefined.

Matched four-reader endpoint joint forecasts below use the same F1 intersection. A six-instrument fit is marginalized back to the original four readers; the four-reader fit is refit on the identical cohort. Ratios are observed all-four-wrong probability divided by pooled predicted probability, never means of per-fact ratios.

| Block | Forecast | Observed / predicted all-four-wrong | Full-vector gain over independence, nats/item |
|---|---|---:|---:|
| A | Six-instrument factor → original four | 1.013 | 0.125 |
| A | Matched four-reader factor | 1.001 | 0.125 |
| A | Matched marginal independence | 3.172 | 0.000 |
| B | Six-instrument factor → original four | 1.021 | 0.125 |
| B | Matched four-reader factor | 1.008 | 0.125 |
| B | Matched marginal independence | 3.226 | 0.000 |

The six-instrument and matched four-reader factor forecasts change little on this intersection. These matched forecasts are point-only diagnostics. They do not replace the original [TH-2 result](th2.md) or its registered tail-closure verdict.

## Uncertainty, numerical checks and reproduction

Each block uses 2,000 source-corpus → fact → shared-document bootstrap resamples with folds and calibration/endpoint roles fixed. Marginals, dependence loadings, posterior training targets, ridge preprocessing/coefficients and weighted quintiles are refit in every replicate. Document weights are shared across facts within each sampled corpus occurrence. Seeds are 20261023 (A) and 20261023+100000 (B), plus replicate index. No success-based early stopping.

| Block | Valid / attempted draws | Failed draws | Validity gate (≥95%) |
|---|---:|---:|---|
| A | 2000 / 2000 | 0 | PASS |
| B | 2000 / 2000 | 0 | PASS |

All primary point-fit success flags: True. Maximum normal-quadrature probability discrepancy: 2.22e-15; posterior discrepancy: 1.15e-14. Maximum training pair-table absolute residual: 0.0314. Fold-level loadings, residuals and calibration counts are in [fits](th2_f1_fits.csv).
An independent audit exactly reproduced endpoint quintile weights. Separately, it verified native instrument votes for all 20,400 calibration-plus-endpoint cohort rows. The optimized point replay across both blocks and both vote conventions differed by at most 2.27e−13.
Every preflight input hash was unchanged after probe fitting (233 files); probes use seed 20261022, exactly 128 labels of each class, pool-only scaling/C selection, and fixed chat L42 states.
Synthetic/numerical, anti-leakage and data checks: 45 tests passed. Per-module write guards passed normally and rejected planted writes without touching protected output trees.

All work is CPU-only; no new target-model inference, external data, API calls or GPU hours. Uncertainty is conditional on the fixed 256-label probe draw and empirical frequency counts. The retrospective benchmark and limited feature panel constrain generalization.

Reproduce from the isolated worktree after its registered bank/cache setup (the coverage report must be communicated before the probe command):

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python -m projects.g_agreement.r_bench.th2_f1_data preflight
.venv/bin/python -m projects.g_agreement.r_bench.th2_f1_data probes --coverage-reviewed --jobs 4
.venv/bin/python -m projects.g_agreement.r_bench.th2_f1_forecast point
.venv/bin/python -m projects.g_agreement.r_bench.th2_f1_forecast bootstrap --reps 2000 --workers 4
.venv/bin/python -m projects.g_agreement.r_bench.th2_f1_forecast intervals
.venv/bin/python -m projects.g_agreement.r_bench.th2_f1_report --tests-passed 45
```

Registered source: [data/probes](../../../../projects/g_agreement/r_bench/th2_f1_data.py), [factor/posterior](../../../../projects/g_agreement/r_bench/th2_f1_models.py), [forecast/bootstrap](../../../../projects/g_agreement/r_bench/th2_f1_forecast.py), [report](../../../../projects/g_agreement/r_bench/th2_f1_report.py).

Machine-readable outputs: [cohort rows](th2_f1_rows.csv.gz), [point metrics](th2_f1_metrics.csv), [95%/90% intervals](th2_f1_intervals.csv), [verdicts](th2_f1_verdicts.csv), [fold coefficients](th2_f1_coefficients.csv), [endpoint predictions](th2_f1_predictions.csv.gz), [bootstrap A](th2_f1_bootstrap_A.csv), [bootstrap B](th2_f1_bootstrap_B.csv), [probe provenance](th2_f1_probe_manifest.csv).
