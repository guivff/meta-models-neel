# E132 — exploratory readout-word prediction of sealed choices

**Primary rule MET**, restricted to the evaluable non-modal, implicit (B) block-60 cell. Readout-only macro OVR AUROC is **0.530947**, prompt-only **0.360648**, and prompt + readout **0.565349**. The paired difference is **+0.170299**,95%item-bootstrap CI **[+0.044975,+0.301924]**, meeting ≥0.10 and lower bound>0.

**Absolute performance is modest:** readout-only95%CI **[0.406268,0.673555]** includes0.50, while the prompt baseline is below0.50. This meets the registered relative comparison; it is not a claim of strong absolute decoding or broad recovery across categories.

All329 original immediate-choice items and the exact110 sealed non-modal IDs are retained. At block60,41non-modal items are endpointB (literal pick string absent); only **6 eligible member cells in 3 categories** contribute to the headline macro (28 of41items lie in those categories). The remaining member cells are explicitly unevaluable; no absent class probability or missing text was imputed.

**E107: NOT APPLICABLE** by clarification1: belief labels are item-specific and every item is belief-wrong, leaving no cross-item private label variation to learn without naming the label. No E107 classifier was fitted.

## Implicit endpoint B

| Block | Subset | B items | Eligible member cells | Prompt AUROC | Readout AUROC | Combined AUROC | Difference | Paired95%CI | Rule |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 60 | all | 49 | 10 | 0.391389 | 0.585235 | 0.605876 | +0.193846 | [+0.081154,+0.316557] | MET |
| 60 | nonmodal | 41 | 6 | 0.360648 | 0.530947 | 0.565349 | +0.170299 | [+0.044975,+0.301924] | MET |
| 52 | all | 123 | 13 | 0.352122 | 0.582319 | 0.601744 | +0.230197 | [+0.111403,+0.340499] | MET |
| 52 | nonmodal | 76 | 7 | 0.439133 | 0.654250 | 0.683008 | +0.215117 | [+0.109625,+0.312661] | MET |
| 44 | all | 238 | 15 | 0.420976 | 0.519709 | 0.532141 | +0.098733 | [+0.007511,+0.179720] | NOT_MET |
| 44 | nonmodal | 99 | 8 | 0.431096 | 0.420998 | 0.459633 | -0.010098 | [-0.111371,+0.089019] | NOT_MET |

Block60/non-modal/B is the registered headline. Block52 and original source-linked E108 block44 are descriptive companions; no block was selected by these results. EndpointB models exclude all unigram features present in any canonical candidate member of that category, from all three predictors. This uses the fixed catalog of realized sealed picks, without new semantic aliases or judges.

## Explicit endpoint A — descriptive

| Block | Subset | A items | Eligible member cells | Prompt AUROC | Readout AUROC | Combined AUROC |
|---|---|---:|---:|---:|---:|---:|
| 60 | all | 280 | 15 | 0.363894 | 0.590191 | 0.601823 |
| 60 | nonmodal | 69 | 8 | 0.406615 | 0.690429 | 0.671041 |
| 52 | all | 206 | 9 | 0.451264 | 0.550559 | 0.588124 |
| 52 | nonmodal | 34 | 3 | 0.422222 | 0.339683 | 0.484127 |
| 44 | all | 91 | 6 | 0.356944 | 0.504167 | 0.504167 |
| 44 | nonmodal | 11 | 1 | 0.500000 | 0.000000 | 0.000000 |

A/B membership is a **casefolded literal pick-string substring** test on the unchanged readout at the reported block. It is not a semantic naming judge or the old E108/E116 hit rate. Endpoint populations are block-specific; no previous hit statistic is replaced. Amodels use raw words; Bmodels remove candidate-word features. Both train on the complete training-fold population and score their held-out endpoint subset.

## Headline category coverage

| Category | Non-modal B items | Eligible members | Prompt AUROC | Readout AUROC |
|---|---:|---:|---:|---:|
| animal | 4 | 0 | NOT EVALUABLE | NOT EVALUABLE |
| bird | 5 | 2 | 0.000000 | 0.416667 |
| city | 1 | 0 | NOT EVALUABLE | NOT EVALUABLE |
| country | 1 | 0 | NOT EVALUABLE | NOT EVALUABLE |
| profession | 14 | 2 | 0.362500 | 0.731731 |
| sport | 4 | 0 | NOT EVALUABLE | NOT EVALUABLE |
| vegetable | 3 | 0 | NOT EVALUABLE | NOT EVALUABLE |
| vehicle | 9 | 2 | 0.719444 | 0.444444 |

## Method and exclusions

Five seeded folds group original items and all occurrences of their original prompt template together across categories. Six template groups produce held-out item counts80,69,73,77,30. Category is not a fold grouping variable. Within each category, each predictor has a train-fold-only word-unigram vocabulary(max5000) and L2 logistic C1 one-vs-rest models. No tuning, label-driven split search or test-vocabulary fitting. The non-modal subset is scored from the same frozen OOF models, without another fit.

There are **30 unique category/member/training-fold unavailability cases** per predictor, common to blocks/views. Members absent from training, no-negative training cells, and endpoint cells without both outcomes are reported with hashed member identifiers in UNEVALUABLE_CELLS_C1.json; actual labels remain CPU-side. The headline excludes25 unevaluable category/member cells. Each reported macro averages the same common eligible member cells across all three predictors; per-category metrics and all model intervals are in RESULTS_C1.json.

The2000 paired item bootstraps resample within(category,sealed pick) strata, preserving label counts and using identical resamples across predictors, seed20261030. Intervals condition on those class counts and fixed OOF predictions; no refit occurs in a bootstrap. No undefined draw is silently dropped.

## Custody and review

Canonical ANALYSIS_SEAL SHA256 `3ab09c7bf68e88ca01476aeafadc870757a075627447d3c8919a39158814ec9d`. Executed source `09aa50e2708b9dad56fa5665e92ce690b97c74b0` plus7synthetic tests/fresh imports was committed and published before the sole real classifier invocation. The source-only preflight verified134original members, all329items,110nonmodal IDs and all3native blocks. No original experiment analysis/guard or model/API/GPU call was invoked.

All labels, prompts/readouts, fitted models and per-item OOF values stay in ignored CPU cache. A hash-bound local review archive and exact source locators are in EXECUTION_RECEIPT_C1.json; no private records are committed. Source and result seals remain immutable. R-2 independent review requested; review pending.
