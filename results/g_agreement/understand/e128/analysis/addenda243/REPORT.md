# E128 §243 — exploratory, post hoc

Original R-DOSE1 remains NOT MET. No refit or rejudging. Separate ADDENDA243_ONCE consumed; never replay.

On the fixed42 alpha4 flippers, old44 changes4/42 to5/42: +.023810, paired95%CI[-.095238,.142857]. This suggests item selection rather than a large within-cohort dose increase; no equivalence claim. Alpha8 whole-set old47/84 includes one unparseable in the combined bin; original observed47/83 remains unchanged.

## A: counts and Wilson95

| Dose | Cohort | Condition | Block | N | Old | New | Dual | Neither/unparseable | Unparseable subset |
|---|---|---|---|---|---|---|---|---|---|
| 2 | all84 | random | 44 | 84 | 67 [0.6996, 0.8696] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 17 [0.1304, 0.3004] | 0 |
| 2 | all84 | random | 52 | 84 | 84 [0.9563, 1.0000] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 0 |
| 2 | all84 | steered | 44 | 84 | 54 [0.5362, 0.7370] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 30 [0.2630, 0.4638] | 0 |
| 2 | all84 | steered | 52 | 84 | 80 [0.8839, 0.9813] | 0 [0.0000, 0.0437] | 4 [0.0187, 0.1161] | 0 [0.0000, 0.0437] | 0 |
| 2 | flipped | random | 44 | 0 | 0 (NE) | 0 (NE) | 0 (NE) | 0 (NE) | 0 |
| 2 | flipped | random | 52 | 0 | 0 (NE) | 0 (NE) | 0 (NE) | 0 (NE) | 0 |
| 2 | flipped | steered | 44 | 0 | 0 (NE) | 0 (NE) | 0 (NE) | 0 (NE) | 0 |
| 2 | flipped | steered | 52 | 0 | 0 (NE) | 0 (NE) | 0 (NE) | 0 (NE) | 0 |
| 4 | all84 | random | 44 | 84 | 73 [0.7805, 0.9253] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 11 [0.0747, 0.2195] | 0 |
| 4 | all84 | random | 52 | 84 | 84 [0.9563, 1.0000] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 0 |
| 4 | all84 | steered | 44 | 84 | 41 [0.3841, 0.5932] | 1 [0.0021, 0.0644] | 0 [0.0000, 0.0437] | 42 [0.3954, 0.6046] | 1 |
| 4 | all84 | steered | 52 | 84 | 9 [0.0574, 0.1912] | 70 [0.7395, 0.8980] | 1 [0.0021, 0.0644] | 4 [0.0187, 0.1161] | 0 |
| 4 | flipped | random | 44 | 42 | 31 [0.5893, 0.8470] | 0 [0.0000, 0.0838] | 0 [0.0000, 0.0838] | 11 [0.1530, 0.4107] | 0 |
| 4 | flipped | random | 52 | 42 | 42 [0.9162, 1.0000] | 0 [0.0000, 0.0838] | 0 [0.0000, 0.0838] | 0 [0.0000, 0.0838] | 0 |
| 4 | flipped | steered | 44 | 42 | 4 [0.0377, 0.2207] | 1 [0.0042, 0.1232] | 0 [0.0000, 0.0838] | 37 [0.7500, 0.9481] | 0 |
| 4 | flipped | steered | 52 | 42 | 0 [0.0000, 0.0838] | 42 [0.9162, 1.0000] | 0 [0.0000, 0.0838] | 0 [0.0000, 0.0838] | 0 |
| 8 | all84 | random | 44 | 84 | 58 [0.5851, 0.7792] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 26 [0.2208, 0.4149] | 0 |
| 8 | all84 | random | 52 | 84 | 42 [0.3954, 0.6046] | 42 [0.3954, 0.6046] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 0 |
| 8 | all84 | steered | 44 | 84 | 47 [0.4531, 0.6608] | 4 [0.0187, 0.1161] | 0 [0.0000, 0.0437] | 33 [0.2953, 0.4998] | 1 |
| 8 | all84 | steered | 52 | 84 | 0 [0.0000, 0.0437] | 84 [0.9563, 1.0000] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 0 |
| 8 | flipped | random | 44 | 84 | 58 [0.5851, 0.7792] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 26 [0.2208, 0.4149] | 0 |
| 8 | flipped | random | 52 | 84 | 42 [0.3954, 0.6046] | 42 [0.3954, 0.6046] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 0 |
| 8 | flipped | steered | 44 | 84 | 47 [0.4531, 0.6608] | 4 [0.0187, 0.1161] | 0 [0.0000, 0.0437] | 33 [0.2953, 0.4998] | 1 |
| 8 | flipped | steered | 52 | 84 | 0 [0.0000, 0.0437] | 84 [0.9563, 1.0000] | 0 [0.0000, 0.0437] | 0 [0.0000, 0.0437] | 0 |

## B: fixed42 alpha4 cohort

| Condition | Block | Bin | Alpha4 count | Alpha8 count | Difference | Paired95%CI |
|---|---|---|---|---|---|---|
| random | 44 | dual | 0 | 0 | 0.000000 | [0.000000, 0.000000] |
| random | 44 | neither_or_unparseable | 11 | 25 | 0.333333 | [0.166667, 0.500000] |
| random | 44 | new | 0 | 0 | 0.000000 | [0.000000, 0.000000] |
| random | 44 | old | 31 | 17 | -0.333333 | [-0.500000, -0.166667] |
| random | 52 | dual | 0 | 0 | 0.000000 | [0.000000, 0.000000] |
| random | 52 | neither_or_unparseable | 0 | 0 | 0.000000 | [0.000000, 0.000000] |
| random | 52 | new | 0 | 42 | 1.000000 | [1.000000, 1.000000] |
| random | 52 | old | 42 | 0 | -1.000000 | [-1.000000, -1.000000] |
| steered | 44 | dual | 0 | 0 | 0.000000 | [0.000000, 0.000000] |
| steered | 44 | neither_or_unparseable | 37 | 33 | -0.095238 | [-0.261905, 0.071429] |
| steered | 44 | new | 1 | 4 | 0.071429 | [-0.023810, 0.166667] |
| steered | 44 | old | 4 | 5 | 0.023810 | [-0.095238, 0.142857] |
| steered | 52 | dual | 0 | 0 | 0.000000 | [0.000000, 0.000000] |
| steered | 52 | neither_or_unparseable | 0 | 0 | 0.000000 | [0.000000, 0.000000] |
| steered | 52 | new | 42 | 42 | 0.000000 | [0.000000, 0.000000] |
| steered | 52 | old | 0 | 0 | 0.000000 | [0.000000, 0.000000] |

All B Wilson intervals are in RESULTS.json. Paired5000 bootstrap, seed0; full42 preserved. UNPARSEABLE is in the requested combined bin and separately counted, not interpreted as semantic neither.

Seal75a53c18aa281a5ba63a53085c409e55a45bf67ffac2c5a78001b6fcdd91db10. Source ae650f926 (rebased equivalent of a4216002b), delivery d5d55c8dc before opening. R-Q independent review requested.
