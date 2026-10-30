# BRIEF_R §15 — J-lens on its own terms (WS3)

Pre-registered 2026-10-19 before computing (BRIEF_R §15). Primary = without LABEL_DEFECT ∪ audit-flagged; all-facts in parentheses.

## (a) J-lens / PRESENT AUROC ratio at block 42 (chat): workspace vs classification

- **primary (without defect ∪ flagged):** workspace mean ratio 1.678 (n = 20) − classification 0.725 (n = 70) = +0.953 [+0.319, +1.373] (clustered) → **SUPPORTED** — workspace facts with a defined reference: ICL task identity 5, R-E KHOP 2, ReaderBench KHOP 7, WorkspaceBench 6 (references: candidate-contrast, probe(512)).
  - sensitivity (not the verdict): without the ceiling-bound ICL facts, workspace 1.917 (n = 15) − classification = +1.192 [+0.671, +1.461]
- **all facts:** workspace mean ratio 1.630 (n = 21) − classification 0.719 (n = 78) = +0.911 [+0.336, +1.333] (clustered) → **SUPPORTED** — workspace facts with a defined reference: ICL task identity 5, R-E KHOP 2, ReaderBench KHOP 7, WorkspaceBench 7 (references: candidate-contrast, probe(512)).
  - sensitivity (not the verdict): without the ceiling-bound ICL facts, workspace 1.838 (n = 16) − classification = +1.119 [+0.647, +1.442]

**Reference validity (diagnostic; BRIEF_R §15 Deviations):** the candidate-contrast probe's test AUROC is below chance on 10/16 per-item facts; on 5 of them its pool inner-CV AUROC is > 0.7, i.e. it learns candidate identity on the pool (h ⊙ (W_U[c0] − W_U[c1]) ≈ a candidate code) and the association inverts on the test pairings. The per-item component of (a) therefore measures that leakage, not the J-lens; only the probe(512) part (ICL, near ceiling) is interpretable.

| fact | J-lens@42 | candidate-contrast test | pool inner-CV | leak |
|---|---|---|---|---|
| rb_khop_3hop_middle | 0.921 | 0.549 | 0.975 |  |
| rb_khop_capital_language_answer | 0.953 | 0.445 | 0.925 | yes |
| rb_khop_capital_language_bridge | 0.768 | 0.260 | 0.955 | yes |
| rb_khop_landmark_capital_answer | 0.648 | 0.365 | 0.963 | yes |
| rb_khop_landmark_capital_bridge | 0.874 | 0.356 | 1.000 | yes |
| rb_khop_landmark_currency_answer | 0.717 | 0.500 | 0.500 |  |
| rb_khop_landmark_currency_bridge | 0.856 | 0.383 | 0.988 | yes |
| re_khop2_answer | 0.717 | 0.549 | 0.740 |  |
| re_khop2_bridge | 0.853 | 0.591 | 0.652 |  |
| re_khop3_middle | 0.922 | — | — |  |
| x22_wsb_association | 0.688 | 0.266 | 0.306 |  |
| x23_wsb_basic_readout | 0.859 | 0.352 | 0.517 |  |
| x24_wsb_multihop | 0.892 | 0.483 | 0.498 |  |
| x25_wsb_wrong_bridge | 0.448 | 0.677 | 0.508 |  |
| x26_wsb_multilingual | 0.915 | 0.828 | 0.747 |  |
| x27_wsb_poetry | 0.557 | 0.361 | 0.331 |  |
| x28_wsb_typo | 0.693 | 0.384 | 0.437 |  |

Per-item-candidate workspace facts awaiting the candidate-contrast reference: 1 (J-lens@42 AUROC median 0.922).

| group | sub-group | facts | J-lens@42 AUROC (median) | PRESENT@42 (median) | ratio (median) |
|---|---|---|---|---|---|
| classification | FORM | 14 | 0.677 | 1.000 | 0.751 |
| classification | SURFACE | 33 | 0.651 | 0.953 | 0.713 |
| classification | TOPIC | 23 | 0.756 | 0.980 | 0.860 |
| workspace | ICL task identity | 5 | 1.000 | 1.000 | 1.000 |
| workspace | R-E KHOP | 3 | 0.853 | 0.570 | 1.375 |
| workspace | ReaderBench KHOP | 7 | 0.856 | 0.383 | 2.142 |
| workspace | WorkspaceBench | 6 | 0.776 | 0.373 | 1.825 |

## (c) J-lens − logit lens AUROC gap by group and block (chat; descriptive)

| group | 24 | 28 | 32 | 36 | 38 | 40 | 42 | 44 | 48 | 52 | 56 | 60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ICL task identity (6 facts) | 0.030 | 0.290 | 0.167 | 0.240 | 0.109 | 0.161 | 0.170 | 0.044 | -0.018 | 0.049 | 0.055 | 0.074 |
| R-E KHOP (3 facts) | 0.100 | 0.098 | 0.146 | 0.158 | 0.151 | 0.227 | 0.296 | 0.267 | 0.159 | 0.248 | 0.150 | 0.087 |
| ReaderBench KHOP (7 facts) | 0.129 | 0.157 | 0.102 | 0.199 | 0.209 | 0.311 | 0.323 | 0.308 | 0.240 | 0.270 | 0.109 | 0.058 |
| WorkspaceBench (7 facts) | 0.049 | 0.119 | 0.123 | 0.173 | 0.175 | 0.223 | 0.212 | 0.222 | 0.248 | 0.098 | 0.039 | 0.012 |
| classification (70 facts) | 0.010 | 0.017 | 0.019 | 0.063 | 0.051 | 0.069 | 0.065 | 0.063 | 0.074 | 0.064 | 0.026 | -0.008 |

At block 42: workspace gap +0.251 (n = 21) vs classification +0.065 (n = 70); difference +0.185 [+0.073, +0.290] (clustered; descriptive).

## (b) Hypothesis-generation precision (descriptive)

hit@K = share of items whose J-lens top-K contains the true bridge / target's first token; precision@K = hit@K / K; FPR@K = share whose top-K contains the distractor's first token. Controls: random-rotation J-lens (5 seeds pooled) and the dataset-mean state. 'generates' = J-lens hit@K Wilson CI above both controls' CIs (descriptive flag).

**R-E KHOP — last token, K = 5**

| layer | J-lens hit@K [Wilson] | precision@K | FPR@K | rotation hit@K | state-free hit@K | generates |
|---|---|---|---|---|---|---|
| 24 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 28 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 32 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 36 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 38 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 40 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 42 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 44 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 48 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 52 | 0.002 [0.000, 0.013] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 56 | 0.175 [0.142, 0.213] | 0.035 | 0.002 | 0.000 | 0.000 | yes |
| 60 | 0.159 [0.128, 0.196] | 0.032 | 0.018 | 0.000 | 0.030 | yes |

**R-E KHOP — last token, K = 10**

| layer | J-lens hit@K [Wilson] | precision@K | FPR@K | rotation hit@K | state-free hit@K | generates |
|---|---|---|---|---|---|---|
| 24 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 28 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 32 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 36 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 38 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 40 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 42 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 44 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 48 | 0.000 [0.000, 0.009] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 52 | 0.020 [0.011, 0.038] | 0.002 | 0.000 | 0.000 | 0.000 | yes |
| 56 | 0.218 [0.182, 0.259] | 0.022 | 0.002 | 0.000 | 0.000 | yes |
| 60 | 0.266 [0.227, 0.309] | 0.027 | 0.027 | 0.000 | 0.030 | yes |

**R-E KHOP — rp token, K = 5**

| layer | J-lens hit@K [Wilson] | precision@K | FPR@K | rotation hit@K | state-free hit@K | generates |
|---|---|---|---|---|---|---|
| 24 | 0.370 [0.327, 0.417] | 0.074 | 0.002 | 0.000 | 0.018 | yes |
| 28 | 0.339 [0.296, 0.384] | 0.068 | 0.002 | 0.000 | 0.018 | yes |
| 32 | 0.268 [0.229, 0.311] | 0.054 | 0.005 | 0.000 | 0.000 | yes |
| 36 | 0.386 [0.342, 0.433] | 0.077 | 0.005 | 0.000 | 0.000 | yes |
| 38 | 0.364 [0.320, 0.410] | 0.073 | 0.002 | 0.000 | 0.005 | yes |
| 40 | 0.341 [0.298, 0.386] | 0.068 | 0.002 | 0.000 | 0.000 | yes |
| 42 | 0.348 [0.305, 0.393] | 0.070 | 0.002 | 0.000 | 0.000 | yes |
| 44 | 0.366 [0.322, 0.412] | 0.073 | 0.002 | 0.000 | 0.005 | yes |
| 48 | 0.368 [0.324, 0.414] | 0.074 | 0.002 | 0.000 | 0.005 | yes |
| 52 | 0.402 [0.357, 0.449] | 0.080 | 0.000 | 0.000 | 0.000 | yes |
| 56 | 0.398 [0.353, 0.444] | 0.080 | 0.000 | 0.000 | 0.000 | yes |
| 60 | 0.289 [0.248, 0.333] | 0.058 | 0.000 | 0.000 | 0.000 | yes |

**R-E KHOP — rp token, K = 10**

| layer | J-lens hit@K [Wilson] | precision@K | FPR@K | rotation hit@K | state-free hit@K | generates |
|---|---|---|---|---|---|---|
| 24 | 0.455 [0.409, 0.501] | 0.045 | 0.005 | 0.000 | 0.023 | yes |
| 28 | 0.420 [0.375, 0.467] | 0.042 | 0.009 | 0.000 | 0.018 | yes |
| 32 | 0.345 [0.303, 0.391] | 0.035 | 0.005 | 0.000 | 0.000 | yes |
| 36 | 0.457 [0.411, 0.504] | 0.046 | 0.009 | 0.000 | 0.014 | yes |
| 38 | 0.445 [0.400, 0.492] | 0.045 | 0.009 | 0.000 | 0.027 | yes |
| 40 | 0.416 [0.371, 0.462] | 0.042 | 0.002 | 0.000 | 0.000 | yes |
| 42 | 0.434 [0.389, 0.481] | 0.043 | 0.007 | 0.000 | 0.005 | yes |
| 44 | 0.434 [0.389, 0.481] | 0.043 | 0.007 | 0.000 | 0.005 | yes |
| 48 | 0.430 [0.384, 0.476] | 0.043 | 0.005 | 0.000 | 0.005 | yes |
| 52 | 0.477 [0.431, 0.524] | 0.048 | 0.002 | 0.000 | 0.000 | yes |
| 56 | 0.470 [0.424, 0.517] | 0.047 | 0.002 | 0.000 | 0.000 | yes |
| 60 | 0.366 [0.322, 0.412] | 0.037 | 0.000 | 0.000 | 0.000 | yes |

**ReaderBench KHOP — last token, K = 5**

| layer | J-lens hit@K [Wilson] | precision@K | FPR@K | rotation hit@K | state-free hit@K | generates |
|---|---|---|---|---|---|---|
| 24 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 28 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 32 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 36 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 38 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 40 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 42 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 44 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 48 | 0.004 [0.001, 0.009] | 0.001 | 0.000 | 0.000 | 0.000 |  |
| 52 | 0.039 [0.029, 0.052] | 0.008 | 0.002 | 0.000 | 0.000 | yes |
| 56 | 0.295 [0.269, 0.322] | 0.059 | 0.004 | 0.000 | 0.000 | yes |
| 60 | 0.276 [0.251, 0.303] | 0.055 | 0.054 | 0.000 | 0.144 | yes |

**ReaderBench KHOP — last token, K = 10**

| layer | J-lens hit@K [Wilson] | precision@K | FPR@K | rotation hit@K | state-free hit@K | generates |
|---|---|---|---|---|---|---|
| 24 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 28 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 32 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 36 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 38 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 40 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 42 | 0.000 [-0.000, 0.003] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 44 | 0.001 [0.000, 0.005] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 48 | 0.004 [0.002, 0.010] | 0.000 | 0.000 | 0.001 | 0.000 |  |
| 52 | 0.070 [0.057, 0.087] | 0.007 | 0.003 | 0.000 | 0.000 | yes |
| 56 | 0.377 [0.349, 0.406] | 0.038 | 0.014 | 0.000 | 0.000 | yes |
| 60 | 0.434 [0.405, 0.464] | 0.043 | 0.099 | 0.000 | 0.144 | yes |

**WorkspaceBench — last token, K = 5**

| layer | J-lens hit@K [Wilson] | precision@K | FPR@K | rotation hit@K | state-free hit@K | generates |
|---|---|---|---|---|---|---|
| 24 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 28 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 32 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 36 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 38 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 40 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 42 | 0.005 [0.001, 0.018] | 0.001 | 0.000 | 0.000 | 0.000 |  |
| 44 | 0.003 [0.000, 0.014] | 0.001 | 0.003 | 0.000 | 0.000 |  |
| 48 | 0.008 [0.003, 0.022] | 0.002 | 0.003 | 0.000 | 0.000 |  |
| 52 | 0.109 [0.082, 0.143] | 0.022 | 0.003 | 0.000 | 0.003 | yes |
| 56 | 0.240 [0.200, 0.284] | 0.048 | 0.008 | 0.000 | 0.003 | yes |
| 60 | 0.323 [0.279, 0.371] | 0.065 | 0.003 | 0.000 | 0.003 | yes |

**WorkspaceBench — last token, K = 10**

| layer | J-lens hit@K [Wilson] | precision@K | FPR@K | rotation hit@K | state-free hit@K | generates |
|---|---|---|---|---|---|---|
| 24 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 28 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 32 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 36 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 38 | 0.000 [0.000, 0.010] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 40 | 0.003 [0.000, 0.014] | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 42 | 0.005 [0.001, 0.018] | 0.001 | 0.000 | 0.000 | 0.000 |  |
| 44 | 0.005 [0.001, 0.018] | 0.001 | 0.003 | 0.000 | 0.000 |  |
| 48 | 0.008 [0.003, 0.022] | 0.001 | 0.003 | 0.000 | 0.000 |  |
| 52 | 0.141 [0.111, 0.179] | 0.014 | 0.010 | 0.000 | 0.003 | yes |
| 56 | 0.273 [0.231, 0.319] | 0.027 | 0.013 | 0.000 | 0.003 | yes |
| 60 | 0.386 [0.340, 0.435] | 0.039 | 0.013 | 0.000 | 0.003 | yes |

