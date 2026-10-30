# E134 §248 B — paired T7 comparison and operating points

Exploratory, post hoc, sealed data only. Direct authority d1567e78b §248 B. All100 original T7 prompts; existing normalization, OTHER2-bound/17-abstained resolution and selected PALL unchanged. No new policy selected on T7.

## Paired PALL minus P60

| Metric | Difference | Paired item-bootstrap95 |
|---|---:|---:|
| Accuracy over all100 | +6 percentage points | [+2, +11] points |
| False-claim rate over all100 | +7 percentage points | [+3, +12] points |

Same prompt indices resampled for both policies,2000 draws, seed20261030; all draws defined. This requested analysis resamples original prompts/items, not matched-pair clusters. The intervals are exploratory and do not establish a general superiority claim. PALL converts13 P60 abstentions into6 correct and7 false claims; all P60 correct/false claims retain their outcome under PALL.

## 3×3 outcomes: rows PALL, columns P60

| PALL \ P60 | Correct | False | Abstain |
|---|---:|---:|---:|
| correct | 50 | 0 | 6 |
| false | 0 | 9 | 7 |
| abstain | 0 | 0 | 28 |

## Precision given a claim

| Rule | Correct / claims | Precision | Wilson95 | Coverage |
|---|---:|---:|---:|---:|
| PALL | 56/72 | 77.8% | [66.9%, 85.8%] | 72% |
| P44 | 7/25 | 28.0% | [14.3%, 47.6%] | 25% |
| P52 | 16/21 | 76.2% | [54.9%, 89.4%] | 21% |
| P60 | 50/59 | 84.7% | [73.5%, 91.8%] | 59% |
| PAGREE | 44/54 | 81.5% | [69.2%, 89.6%] | 54% |

PAGREE uses the original frozen policy: abstain unless all stating layers agree; silent/abstaining layers contribute no stated value. Its unconditional accuracy is44/100, false-claim rate10/100, coverage54/100. Full Wilson/item-bootstrap intervals are in RESULTS.json. On this cohort PAGREE has lower coverage and lower conditional precision than P60; it does not improve this operating point. PALL obtains more correct claims at the cost of more false claims and lower conditional precision than P60.

Original source+exact private plan committed ae03babdc before this separate §248 B once-only guard. Two supplement tests passed, checking pairing, outcome-table/precision denominators, zero-claim handling and unchanged frozen aggregates. The four original policy counts were validated against the sealed T7 results, not rerun through the author T7 runner. Only PAGREE's newly authorized score is added; no selection/refit. Original T7 and T1–T6 guards/results unchanged. The supplement guard must never reset or replay. Private rows/joins/plan remain local; public receipt pins original plan/source and aggregate bytes. R-3 review requested; prior R3 evidence publication hold is unchanged.
