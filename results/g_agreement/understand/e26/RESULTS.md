# E26 — EXPLORATORY

Prediction: R1 and R2 jointly hold on at least four of five state rows; sentiment also satisfies R1 and ranks descriptions below own-value continuations.

Prediction **NOT MET**: joint R1/R2 on 0/5 state rows; sentiment prediction NOT MET.

Raw cosine as E21, tag 44. Item bootstrap: 2,000 resamples, seed 20261025. Sentiment omits E15 category (a) under §120 clarification 1; its own-value continuations are category (b).

| Row | M1 [95% CI] | Best true-description rank [CI] | Own-continuation rank [CI] | M2 difference [CI] | M3 [CI] | R1 | R2 |
|---|---|---|---|---|---|---|---|
| prose_paren | 0.3550 [0.3075, 0.4025] | 98.0000 [96.0000, 99.0000] | 50.1250 [48.2500, 58.2500] | 47.8750 [40.1250, 50.2500] | 0.0000 [0.0000, 0.0000] | False | True |
| python_string | 0.3900 [0.3025, 0.4825] | 50.0000 [47.9875, 52.0000] | 64.5000 [42.5000, 91.5000] | -14.5000 [-43.5000, 8.5000] | 0.0000 [0.0000, 0.0000] | False | False |
| prose_quote | 0.2762 [0.2463, 0.3075] | 87.0000 [86.0000, 88.0000] | 56.8750 [50.2500, 61.1250] | 30.1250 [25.5000, 36.7500] | 0.0000 [0.0000, 0.0000] | False | True |
| table_role | 0.3163 [0.2713, 0.3588] | 53.0000 [51.0000, 56.0000] | 72.0000 [62.5000, 85.0000] | -19.0000 [-32.0000, -8.8750] | 0.0000 [0.0000, 0.0000] | False | False |
| python_indent | 0.3438 [0.2675, 0.4188] | 57.0000 [28.0000, 87.0000] | 66.1250 [57.7500, 74.5000] | -9.1250 [-46.3750, 28.1281] | 0.0000 [0.0000, 0.0000] | False | False |
| prose_sentiment | 0.6388 [0.5875, 0.6900] | 69.5000 [68.0000, 79.0000] | 37.2500 [32.0000, 37.6281] | 32.2500 [30.5000, 43.0000] | 0.0000 [0.0000, 0.0000] | False | True |

R1: M1 ≥ 0.65 and CI lower > 0.50. R2: best-description median rank minus own-continuation median rank > 0, with CI lower > 0. Exact cosine ties have average ranks and fractional membership at the top-10 boundary. Own-continuation rank is the median of within-item medians; M2 uses a paired item bootstrap. These conventions were frozen before scoring.
