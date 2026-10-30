# §58 PRIMARY — centred unwhitened FVE

The pooled PRIMARY does not meet R1 or R2. Oracle lens alone meets both registered thresholds; NLA does not. ΔFVE meets neither threshold for either reader. The Oracle result is reader-specific and does not establish a general claim-auditing method.

Score seal: `310a9f2c2afb44079f66cb3a98181448b1cc7d6084ea64cedc0da9695cf844fd`. Labels joined only after score and input hash verification.

| Reader | Founded / mapped claims | Score | AUROC | 97.5% CI | ΔAUROC vs length (97.5% CI) | R1 | R2 |
|---|---:|---|---:|---|---|---|---|
| pooled | 91/135 | fve | 0.674 | [0.585, 0.752] | 0.055 [-0.053, 0.164] | False | False |
| pooled | 91/135 | delta_fve | 0.540 | [0.453, 0.633] | -0.078 [-0.210, 0.072] | False | False |
| pooled | 91/135 | length | 0.618 | [0.514, 0.714] | undefined undefined | — | — |
| pooled | 91/135 | shuffled_fve | 0.466 | [0.393, 0.553] | undefined undefined | — | — |
| oracle | 40/57 | fve | 0.726 | [0.551, 0.881] | 0.162 [0.009, 0.298] | True | True |
| oracle | 40/57 | delta_fve | 0.497 | [0.300, 0.669] | -0.068 [-0.324, 0.156] | False | False |
| oracle | 40/57 | length | 0.565 | [0.417, 0.715] | undefined undefined | — | — |
| oracle | 40/57 | shuffled_fve | 0.490 | [0.307, 0.682] | undefined undefined | — | — |
| nla | 51/78 | fve | 0.672 | [0.571, 0.755] | 0.026 [-0.145, 0.172] | False | False |
| nla | 51/78 | delta_fve | 0.538 | [0.421, 0.659] | -0.108 [-0.304, 0.102] | False | False |
| nla | 51/78 | length | 0.646 | [0.518, 0.778] | undefined undefined | — | — |
| nla | 51/78 | shuffled_fve | 0.450 | [0.299, 0.603] | undefined undefined | — | — |

R1 requires AUROC≥0.70 and corrected lower bound>0.5. R2 requires an AUROC gain≥0.05 over length and a corrected paired interval excluding0. Both FVE and ΔFVE are reported; no score-direction reversal.

Registered whitened SECONDARY: **NOT RUN**, because access arrived after the PRIMARY label join. Guiv authorized a separate dated [post-join EXPLORATORY whitened analysis](WHITENED_EXPLORATORY.md); this does not change the centred PRIMARY verdict. P3 descriptive SECONDARY is complete: see [paired FVE results](P3_SECONDARY.md).

Limitations:
- Concept matches are judged evidence quotations, not independently labeled atomic claims.
- 3463 unmapped observations and5 invalid observations do not enter mapped-claim AUROC.
- No SA free-text J-lens or AO arm was available.
- Mean is fixed over1200 original state records, not weighted by claims.
- 20 held-out prompts are bootstrap clusters; historical mismatch controls are separate, not duplicated primary units.

![PRIMARY ROC](PRIMARY_ROC.svg)

## Whitened post-join EXPLORATORY —22October2026

The same135claims were scored onCPU with the verified pinned whitener and officiallabfunction, reusing all42sealedpredictions. No additionalAR/GPU/APIspend. Pooled exploratoryAUROC:FVE0.862[0.799,0.927],DeltaFVE0.831[0.768,0.900];length0.618,shuffledFVE0.518. These are descriptive post-join results, **not the registered whitened SECONDARY**, which remainsNOT RUN. The earlierSECONDARYdesignation is superseded. [Full table and timing disclosure](WHITENED_EXPLORATORY.md).

## P3 descriptive SECONDARY — 22 October 2026

All 26,353 AR predictions and 47,666 eligible quote scores are independently hash-verified; score seal `ba365bec3f09f0bd32b2a3e9baed9bcd9e1089a6c8523cd832a61d55d0ff7134` preceded the first P3 label join. The same registered centred-FVE metric compares each attribution on its actual supplied state versus a fixed different-item derangement. POSITIVE-SPECIFIC and POSITIVE-VAGUE strata, reader/layer/site, framing and natural/shuffled input assignment are reported separately. Group mean differences vary rather than being uniformly near zero; no scientific verdict or equivalence threshold was registered. AO native user-end remains **NOT RUN**; AO assistant-onset has the 8B-reader/27B-auditor caveat. [Full descriptive table](P3_SECONDARY.md) · [public JSON](P3_SECONDARY_RESULTS.json).
