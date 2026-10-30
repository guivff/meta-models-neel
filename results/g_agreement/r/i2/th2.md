# TH-2: held-out four-reader failures from shared difficulty

**Final handoff — 2026-10-19. Block A: SUPPORTED; block B (without audit flags): SUPPORTED.**
The restricted shared-difficulty model predicts the held-out four-reader failure tail and improves the full error-vector log score over independent readers. Its parameters were fitted only from marginal and pairwise calibration errors. This supports shared difficulty as a sufficient predictive explanation on these facts; it does not identify a shared neural mechanism or prove that every dependence is one-dimensional.

**Branch:** `r/i2-th2`. **Preregistration:** `7117a170dab3572ee7fa7125d42e164504741f5e`, pushed before preflight/fitting. **Compute:** CPU only; 0 GPU/pod hours; existing rows only. Ready for integrator review/merge; the dated handoff and separate WS3 vote-rule warning are in `../HANDOFF.md`.

| Frozen primary (analyze.py votes) | A: nondefective facts | B: also drop audit flags |
|---|---:|---:|
| Facts / corpus groups | 108 / 34 | 104 / 34 |
| Endpoint items / all-four failures | 10,580 / 886 | 10,273 / 856 |
| Observed failure probability | 8.3743% | 8.3325% |
| Shared-difficulty predicted probability | 8.4464% | 8.2835% |
| Independence predicted probability | 2.7549% | 2.6249% |
| Observed / predicted, 90% CI | 0.991 [0.844, 1.150] | 1.006 [0.858, 1.176] |
| Observed / predicted, 95% CI | [0.822, 1.182] | [0.834, 1.204] |
| Joint-score gain, nats/item (95% CI) | +0.122 [0.070, 0.157] | +0.123 [0.069, 0.161] |
| Registered verdict | SUPPORTED | SUPPORTED |

![TH-2 held-out forecasts and confidence intervals](th2_summary.png)

The thresholds are unchanged: the entire 90% ratio CI must lie in **[2/3, 1.5]**, and gain must be **≥0.02 nats/item with 95% lower bound >0**. A 95% ratio interval wholly outside the band rejects tail closure. Both blocks pass the ≥30 facts / ≥5 corpora / ≥30 all-wrong event gates.

## Coverage and semantic audit, completed before fitting

Read 3,150,656 existing rows from 15 shards. All 22,198 R-A test items from 113 facts have four finite, scorable primary-site readers; no missing reader rows, duplicate raw/full semantic keys, candidate/label/split mismatches or partial tails were found. Non-R-A and pod-D rows were scoped out using `analyze.py` provenance rules. Native rows carry frozen SHA `4d482b6`, allowed pod identities and the matching bank-file hash. The frozen bank hash is `2dbde3a272186ac4e3f669fe4fab5e40d97feb5e3cdfd4ba35beed422ded13f5`.

| Population | Complete test items | Marginal-calibration half | Endpoint half | Facts | Corpus groups |
|---|---:|---:|---:|---:|---:|
| A | 21,198 | 10,618 | 10,580 | 108 | 34 |
| B | 20,626 | 10,353 | 10,273 | 104 | 34 |

Five R-A LABEL_DEFECT facts are always excluded: 139/140/141 (AG News) and 145/146 (disease); their two multiclass parent IDs are outside R-A. Block B additionally removes the frozen nondefect flags 131 (Typical Time), 142 (Thyroid Cancer), 144 (Colon Cancer), and 153 (Administrative rights). The thresholds, holdout mapping and fitting algorithm are identical across blocks.

## Frozen estimation and uncertainty

Reader order is J-lens@42, Oracle@44, NLA@42, skip_a@42, natural/chat. Scores and ordered shard loading use `analyze.py`; the streamed loader applies its provenance filtering and keeps the last raw key, then asserts full semantic-key uniqueness. Positive semantic label means the bank’s positive candidate, independently of score order. Primary votes use strict `score > fact/test median`; ties vote negative.

The §4.9 corpus map is augmented by binary-parent families, registered source families and shared normalized text, producing 34 document-disjoint groups. SHA256 seed 20261019 fixes five corpus folds; SHA256 seed 20261020 fixes global text groups into calibration and endpoint halves. Every fact is scored once. Class-specific reader loadings use only calibration-half marginal/pairwise tables from the other corpus folds. A held-out fact contributes calibration-half marginal rates `(errors+0.5)/(n+1)`, never its dependence or endpoints, to its forecast. No triple/four-way count or vector likelihood selects a parameter.

The one-factor model is `Z_r = a_r U + sqrt(1-a_r²) epsilon_r`, `0≤a_r≤0.98`, with errors below the Gaussian quantile of each marginal. Separate loadings are fitted for semantic labels 0 and 1 by six-pair composite likelihood, with deterministic multiple starts. Gaussian quadrature predicts all 16 error vectors. Independence uses exactly the same smoothed marginals. Ratios are pooled observed failures divided by pooled expected failures; gain is paired full-vector log score in natural-log units.

Each block has 2,000 corpus→fact→shared-document bootstrap draws and 2,000 fact→item draws (seed 20261021). Marginals and all loadings are refitted in every draw; corpus folds and half assignments remain fixed. Shared text occurrences receive one paired weight within each resampled corpus occurrence. Headline intervals take the envelope of both percentile intervals. Inference conditions on the registered, frozen score thresholds; it does not resample/reselect the test median. The primary is retrospective, with prior H7 aggregates visible.

| Block / bootstrap | Valid / requested | Ratio 90% CI | Gain 95% CI |
|---|---:|---:|---:|
| A / corpus_fact_item | 2000 / 2000 | [0.844, 1.150] | [0.070, 0.157] |
| A / fact_item | 2000 / 2000 | [0.897, 1.096] | [0.087, 0.152] |
| B / corpus_fact_item | 2000 / 2000 | [0.858, 1.176] | [0.069, 0.161] |
| B / fact_item | 2000 / 2000 | [0.906, 1.115] | [0.086, 0.154] |

## Controls and matched event orders

| Block | Model | Four-way prediction | Observed / predicted | Joint-score gain |
|---|---|---:|---:|---:|
| A | factor | 8.4464% | 0.991 | +0.1217 |
| A | independence | 2.7549% | 3.040 | +0.0000 |
| A | equal_factor | 8.5005% | 0.985 | +0.1129 |
| A | beta | 8.4729% | 0.988 | +0.0780 |
| A | unrestricted | 8.4555% | 0.990 | +0.1227 |
| B | factor | 8.2835% | 1.006 | +0.1232 |
| B | independence | 2.6249% | 3.174 | +0.0000 |
| B | equal_factor | 8.3392% | 0.999 | +0.1167 |
| B | beta | 8.3101% | 1.003 | +0.0793 |
| B | unrestricted | 8.2936% | 1.005 | +0.1247 |

The equal-loading Gaussian and exchangeable beta toy are restricted controls. The beta toy uses only first/pairwise evidence but replaces heterogeneous reader marginals with their mean; it is not a matched-marginal alternative. The unrestricted Gaussian is a six-correlation, positive-definite pairwise diagnostic. Its near-identical pooled forecast does not supply a new verdict. Full pair/triple/quartet subset probabilities and ratios are in `th2_event_orders.csv` (R2/R3/R4 denote event order here). All-correct rates and vector log scores are in `th2_metrics.csv`.

## Vote-rule sensitivity and the H7 discrepancy

**For WS3/integrator:** `analyze.r7_agreement` thresholds all facts at the test-score median, whereas BRIEF_R §4.7 says sign(`s_diff`) for two-sided facts. Both conventions were registered before fitting. The primary above preserves the requested analysis-code convention. Neither this analysis nor its handoff edits the existing H7 verdict.

| Block | Registered vote sensitivity | Observed four-way | Predicted four-way | Ratio | Gain, nats/item |
|---|---|---:|---:|---:|---:|
| A | literal | 10.6805% | 10.6928% | 0.999 | +0.1164 |
| B | literal | 10.7077% | 10.6002% | 1.010 | +0.1176 |
| A | poolmedian | 8.3743% | 8.7284% | 0.959 | +0.1248 |
| B | poolmedian | 8.3423% | 8.5549% | 0.975 | +0.1264 |

These are prespecified descriptive sensitivity point estimates, with no substituted primary verdict or primary CI claim. Literal votes use zero for two-sided scores and the test median for one-sided scores. Pool-median votes use existing pool-eval scores for every fact/reader; coverage matches the primary.

| Full-test H7 reproduction | Mean per-fact ratio | Pooled ratio | Consensus gain vs best on all items |
|---|---:|---:|---:|
| A / allmedian | 22.58 | 3.17 | +3.19 pp |
| A / literal | 8.72 | 3.59 | +4.64 pp |
| A / poolmedian | 35.27 | 3.17 | +3.03 pp |
| B / allmedian | 23.41 | 3.27 | +3.69 pp |
| B / literal | 9.00 | 3.71 | +5.20 pp |
| B / poolmedian | 36.60 | 3.27 | +3.55 pp |

This reconciles the motivating “2–3×” statement with the interim mean-ratio value around 22×: event order and aggregation matter. The mean of ratios can be dominated by facts with tiny independent failure probabilities. The consensus-vs-best comparison on the same unanimous items is exactly zero by construction; the all-item comparator above is different. The vote discrepancy changes descriptive gains and ratios and merits WS3 review with its original clustered H7 decision rule.

## Validation, limits and artifacts

All 18 numerical/leakage/vote/isolation tests passed. All fitted diagnostics converged. Primary quadrature vs 1,024-node integration differs by at most 2.61e-15 probability; recovered marginal error is at most 2.22e-16. The unrestricted diagnostic was independently recomputed for all 424 forecasts, matching stored probabilities exactly; maximum raw normalization error was 1.26e-6 and marginal error 6.41e-7 (`th2_numerical_qa.json`). Numerical and leakage tests are in `projects/g_agreement/tests/test_th2_*.py`. Main-checkout files and its cache link were not changed; all data were read through the worktree’s link to the real cache.

This result applies to pooled held-out natural R-A failures for four Qwen instruments at their declared sites. It does not establish item-level causal difficulty, universal per-fact fit, independence after conditioning on an observed difficulty score, or a neural mechanism. Two-stage label/corpus variation and candidate priors are controlled as registered, but unidentified label noise and the transductive median convention remain limitations. No new collection was made. The optional Gemma three-vote extension is not run: its AO variants are one underlying instrument and its rows lack this analysis’s frozen Qwen provenance contract; no Gemma failure or success is inferred. Optional text/probe residualization is not run.

Reproduce from the branch root with the existing bank and read-only cache:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.th2_preflight
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.th2_forecast --stage point
# For each block A/B and scheme corpus_fact_item/fact_item:
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.th2_forecast --stage bootstrap --block A --scheme corpus_fact_item --n-boot 2000 --workers 3
.venv/bin/python -m projects.g_agreement.r_bench.th2_forecast --stage intervals
.venv/bin/python -m projects.g_agreement.r_bench.th2_report
```

Artifacts: `th2_coverage.csv`, `th2_shards.json`, `th2_preflight.json`, `th2_split_manifest.csv.gz`, `th2_rows.csv.gz`, `th2_thresholds.csv`, `th2_fits.csv`, `th2_predictions.csv`, `th2_metrics.csv`, `th2_event_orders.csv`, `th2_intervals.csv`, bootstrap CSVs, `th2_numerical_qa.json`, and `th2_h7_descriptive.csv`. Bootstrap outputs are resumable by replicate index. Input manifests include every shard’s hash and before/after stat check. The standard log/compute ledger records commands and zero GPU use.

**Deviations:** no population, holdout, model or decision-threshold change after registration. Streaming is an implementation adaptation of the existing loading/provenance functions for the 3.9GB shard inventory. Optional Gemma/text/probe diagnostics are not run as disclosed above.
