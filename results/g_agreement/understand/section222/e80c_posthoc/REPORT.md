# E80c variance-normalized ablations — POST HOC / DESCRIPTIVE

§223 item 2. Original R-X3: **NOT MET: readers depend on high-variance directions, not specifically the J-space**. No verdict changes.

Variance is centered trace covariance. Normalized fall uses identical complete-case pass-under-none items for both numerator and denominator. Ratio units: percentage-point pass-rate fall per percentage point variance removed. All CIs: paired item percentile bootstrap, 2,000 draws, seed 20261028; fixed sealed ablations, no basis/PCA refit.

## nla — exploratory: block-44 bases applied at block 42

Original cohort n=218; excluded missing=0.

| Ablation | Variance removed, all 518 (%) [95% CI] | Variance removed, pass-none cohort (%) [95% CI] | Pass fall (pp) [95% CI] | Fall / variance share [95% CI] |
|---|---:|---:|---:|---:|
| J_ablated | 15.1395 [14.8438, 15.4654] | 17.2057 [16.6714, 17.7959] | 48.6239 [42.2018, 55.0459] | 2.8260 [2.4150, 3.2308] |
| PCA_ablated | 81.7759 [81.5061, 82.0346] | 81.9276 [81.5251, 82.3170] | 83.9450 [78.8991, 88.5321] | 1.0246 [0.9622, 1.0829] |
| random_ablated | 7.6605 [7.6132, 7.7075] | 7.6064 [7.5375, 7.6764] | 12.8440 [8.2569, 16.9725] | 1.6886 [1.0976, 2.2370] |

Paired differences of normalized falls:
- J_minus_PCA_ablated: 1.8014 [1.4075, 2.2042]
- J_minus_random_ablated: 1.1374 [0.5062, 1.8164]

## oracle — primary site

Original cohort n=184; excluded missing=0.

| Ablation | Variance removed, all 518 (%) [95% CI] | Variance removed, pass-none cohort (%) [95% CI] | Pass fall (pp) [95% CI] | Fall / variance share [95% CI] |
|---|---:|---:|---:|---:|
| J_ablated | 14.3061 [13.9969, 14.6268] | 17.2577 [16.6620, 17.8831] | 57.6087 [50.0000, 64.6739] | 3.3381 [2.8876, 3.7783] |
| PCA_ablated | 99.8015 [99.7753, 99.8269] | 99.9569 [99.9348, 99.9752] | 96.7391 [94.0217, 98.9130] | 0.9678 [0.9406, 0.9896] |
| random_ablated | 7.7240 [7.6721, 7.7764] | 7.6830 [7.6029, 7.7552] | 9.7826 [5.4348, 14.6739] | 1.2733 [0.7083, 1.8951] |

Paired differences of normalized falls:
- J_minus_PCA_ablated: 2.3703 [1.9189, 2.8105]
- J_minus_random_ablated: 2.0649 [1.4510, 2.6688]

J has the highest normalized fall at the Oracle site; this descriptive ratio does not establish J specificity under variance-matched interventions. PCA removes nearly all empirical block-44 variance, so raw rank matching was not variance matching. No causal-slope or new confirmatory claim. NLA remains exploratory (block-44 bases at block 42).

Execution: 0.826128 seconds CPU wall time; GPU hours 0. Plan/code committed before execution at 9c2185cf4. Original analysis was not invoked; original cohort/fall equality asserted. All 33 source/code pins verified before the separate exclusive post hoc claim.
