# X3 CPU follow-ups: conflict strength and probe sign

2026-10-21; exploratory, preregistration `970ca67d`. Frozen fits and hash-verified caches only; no refitting or new model inference. Intervals are the conservative envelope of 2,000 paired-item and 2,000 choice-family draws, seed 0. Both prefills stay together.

Coverage: 192 test items, 91 exact training items; LABEL_DEFECT exclusions 0. Quartile boundaries on saved unprefilled target_margin: [1.4999998805719883, 2.247013882902145, 3.249999739453035]; boundary-tie counts [1, 1, 1]. Fixed bins, ties in lower bin. Selection already required margin ≥1; Q1 is weakest among eligible items, not all model uncertainty.

| Strength quartile | Items / families | Oracle | NLA | J-lens | Prompt-only | LR L42 | LR L44 |
|---|---|---|---|---|---|---|---|
| 1 | 48 / 42 | 0.600 [0.535, 0.671] | 0.505 [0.405, 0.608] | 0.490 [0.467, 0.500] | 0.788 [0.717, 0.862] | 0.491 [0.329, 0.645] | 0.523 [0.361, 0.682] |
| 2 | 48 / 43 | 0.635 [0.528, 0.738] | 0.573 [0.483, 0.665] | 0.500 [0.500, 0.500] | 0.846 [0.767, 0.917] | 0.488 [0.325, 0.644] | 0.482 [0.309, 0.645] |
| 3 | 48 / 48 | 0.664 [0.570, 0.761] | 0.553 [0.455, 0.651] | 0.500 [0.500, 0.500] | 0.870 [0.793, 0.934] | 0.352 [0.210, 0.492] | 0.365 [0.206, 0.526] |
| 4 | 48 / 48 | 0.656 [0.554, 0.758] | 0.678 [0.576, 0.779] | 0.500 [0.500, 0.500] | 0.997 [0.990, 1.000] | 0.294 [0.168, 0.441] | 0.387 [0.230, 0.551] |

AUROC predicts disagreement with the prefilled option. J-lens retains the original nearly all-zero lexical readout. Skip-lens, R-Lens and J++ have no original X3 scores here (NOT RUN); they are not substituted. No trend significance or new reader verdict is claimed.

| Probe site | State cohort | Items / rows | AUROC, original sign | AUROC, reversed sign | Accuracy, original zero threshold |
|---|---|---|---|---|---|
| L42 | unprefilled_pool | 91 / 91 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] |
| L42 | unprefilled_test | 192 / 192 | 0.842 [0.772, 0.902] | 0.158 [0.098, 0.228] | 0.797 [0.738, 0.852] |
| L42 | prefilled_test | 192 / 384 | 0.405 [0.316, 0.484] | 0.595 [0.516, 0.684] | 0.411 [0.330, 0.486] |
| L44 | unprefilled_pool | 91 / 91 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] |
| L44 | unprefilled_test | 192 / 192 | 0.941 [0.907, 0.968] | 0.059 [0.032, 0.093] | 0.859 [0.807, 0.907] |
| L44 | prefilled_test | 192 / 384 | 0.432 [0.347, 0.512] | 0.568 [0.488, 0.653] | 0.411 [0.330, 0.486] |

Prefilled-pool comparison: NOT RUN (only two smoke items were scored, not the full pool; smoke rows are not substituted). Unprefilled target: preferred=A; positive score predicts A. Prefilled target: disagreement, score=−preference_score for prefill A and +preference_score for prefill B. Every saved prefilled probe score was reproduced from the frozen coefficients and hashed states; maximum error 7.62939453125e-06. Training performance is a sign diagnostic, not held-out evidence. Negative-score results are diagnostic only: the published probe orientation is not changed.

No global label/sign flip is evident: both original-sign probes have training AUROC and accuracy 1.00, and retain above-chance unprefilled held-out AUROC (L42 0.842; L44 0.941). The same coefficients fall to 0.405/0.432 after forced prefill plus a commit token, with the disagreement conversion verified against every saved score. This supports a prefill-related representation/task transfer failure rather than a flipped label implementation; it does not prove which representation change caused the failure. Prompt-only has higher AUROC point estimates than every reader in every strength quartile, rising from 0.788 in Q1 to 0.997 in Q4; this is descriptive, not a registered trend test.
