# SWAP — workspace swaps (WS4 rows, WS3 analysis)

Checkpoint tiers (BRIEF_RP §0): olens = community (agu18dec/olens_and_ar olens_s3d_rl600 (Qwen3.6-27B)); jlens = community (neuronpedia/jacobian-lens (Qwen3.6-27B)); nla = community (ceselder/qwen3.6-27b-nla-rl iter 400 (Qwen3.6-27B)); skip_a = community (agreelens skip lenses (Qwen3.6-27B)); prompt-only, probes and the logit lens = none. Every Oracle-lens number is the Qwen Oracle lens at that checkpoint. Each reader family is its own row; this file has no Gemma AO and no Qwen AO row, and never pools them with the Qwen Oracle lens.

Coverage (items per arm): {'khop d_answer': 118, 'khop d_cm': 68, 'khop d_logit': 196, 'khop d_rand0': 196, 'khop d_rand1': 196, 'khop d_rand2': 196, 'khop d_swap': 196, 'poetry d_logit': 48, 'poetry d_rand0': 48, 'poetry d_rand1': 48, 'poetry d_rand2': 48, 'poetry d_swap': 48}

## R-S1 — the bridge swap (khop, d_swap on the bridge pair)

| layer | n | flip | random flip | effect [95% CI] | R-S1 |
|---|---|---|---|---|---|
| 24 | 196 | 0.740 | 0.005 | +0.735 [+0.677, +0.793] | WORKS |
| 28 | 196 | 0.133 | 0.000 | +0.133 [+0.087, +0.184] | does not work |
| 32 | 196 | 0.056 | 0.000 | +0.056 [+0.026, +0.097] | does not work |
| 36 | 196 | 0.005 | 0.000 | +0.005 [+0.000, +0.015] | does not work |
| 40 | 196 | 0.005 | 0.000 | +0.005 [+0.000, +0.015] | does not work |
| 44 | 196 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | does not work |

R-S1's statistic is the flip on the BRIDGE pair (BRIEF_R SWAP §Metrics: "bridge pair for d_swap"). d_swap's effect on the model's ANSWER pair, descriptive and beside it, not a verdict input:

| layer | n | answer flip | random | effect [95% CI] |
|---|---|---|---|---|
| 24 | 196 | 0.694 | 0.000 | +0.694 [+0.628, +0.755] |
| 28 | 196 | 0.102 | 0.000 | +0.102 [+0.061, +0.148] |
| 32 | 196 | 0.056 | 0.000 | +0.056 [+0.026, +0.087] |
| 36 | 196 | 0.015 | 0.000 | +0.015 [+0.000, +0.036] |
| 40 | 196 | 0.005 | 0.000 | +0.005 [+0.000, +0.015] |
| 44 | 196 | 0.005 | 0.000 | +0.005 [+0.000, +0.015] |

d_cm covers 68 items, not the 70 of WS4's 17:46Z bank count: Tanzania has 3 items among the 196 gated (4 in the bank), below CM_MIN_PER_SIDE = 4, so re-re_khop2_bridge-test-0144 and -0186 have no d_cm (WS4, 2026-10-19).

## Every khop arm (targeted pair)

| layer | arm | pair | n | flip | random | effect [95% CI] |
|---|---|---|---|---|---|---|
| 24 | d_answer | answer | 118 | 0.619 | 0.000 | +0.619 [+0.525, +0.703] |
| 24 | d_cm | bridge | 68 | 0.868 | 0.000 | +0.868 [+0.779, +0.941] |
| 24 | d_logit | bridge | 196 | 0.270 | 0.005 | +0.265 [+0.202, +0.330] |
| 24 | d_swap | bridge | 196 | 0.740 | 0.005 | +0.735 [+0.677, +0.793] |
| 28 | d_answer | answer | 118 | 0.110 | 0.000 | +0.110 [+0.059, +0.169] |
| 28 | d_cm | bridge | 68 | 0.250 | 0.000 | +0.250 [+0.162, +0.353] |
| 28 | d_logit | bridge | 196 | 0.026 | 0.000 | +0.026 [+0.005, +0.051] |
| 28 | d_swap | bridge | 196 | 0.133 | 0.000 | +0.133 [+0.087, +0.184] |
| 32 | d_answer | answer | 118 | 0.068 | 0.000 | +0.068 [+0.025, +0.119] |
| 32 | d_cm | bridge | 68 | 0.044 | 0.000 | +0.044 [+0.000, +0.103] |
| 32 | d_logit | bridge | 196 | 0.010 | 0.000 | +0.010 [+0.000, +0.026] |
| 32 | d_swap | bridge | 196 | 0.056 | 0.000 | +0.056 [+0.026, +0.097] |
| 36 | d_answer | answer | 118 | 0.017 | 0.000 | +0.017 [+0.000, +0.042] |
| 36 | d_cm | bridge | 68 | 0.015 | 0.000 | +0.015 [+0.000, +0.044] |
| 36 | d_logit | bridge | 196 | 0.005 | 0.000 | +0.005 [+0.000, +0.015] |
| 36 | d_swap | bridge | 196 | 0.005 | 0.000 | +0.005 [+0.000, +0.015] |
| 40 | d_answer | answer | 118 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 40 | d_cm | bridge | 68 | 0.015 | 0.000 | +0.015 [+0.000, +0.044] |
| 40 | d_logit | bridge | 196 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 40 | d_swap | bridge | 196 | 0.005 | 0.000 | +0.005 [+0.000, +0.015] |
| 44 | d_answer | answer | 118 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 44 | d_cm | bridge | 68 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 44 | d_logit | bridge | 196 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 44 | d_swap | bridge | 196 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |

## R-S5 — controls vs d_swap at the same norm (khop bridge; poetry swapped-in rhyme)

Two readings of "produces a larger swap effect" (WS4's 03:40Z text names neither). Both are WS3 readings written AFTER WS4's descriptive SWAP numbers were on the scaffold (HANDOFF, 21:03:55Z), so both are post-data: (a) point estimate larger (WS3's 818e56a); (b) the paired CI of the difference above 0.

| part | layer | control | n | control | d_swap | diff [95% CI] | (a) point estimate larger | (b) CI above 0 |
|---|---|---|---|---|---|---|---|---|
| khop | 24 | d_cm | 68 | 0.868 | 0.662 | +0.206 [+0.088, +0.324] | YES | YES |
| khop | 24 | d_logit | 196 | 0.270 | 0.740 | -0.469 [-0.541, -0.403] | no | no |
| khop | 28 | d_cm | 68 | 0.250 | 0.074 | +0.176 [+0.088, +0.265] | YES | YES |
| khop | 28 | d_logit | 196 | 0.026 | 0.133 | -0.107 [-0.153, -0.066] | no | no |
| khop | 32 | d_cm | 68 | 0.044 | 0.015 | +0.029 [+0.000, +0.074] | YES | no |
| khop | 32 | d_logit | 196 | 0.010 | 0.056 | -0.046 [-0.077, -0.020] | no | no |
| khop | 36 | d_cm | 68 | 0.015 | 0.000 | +0.015 [+0.000, +0.044] | YES | no |
| khop | 36 | d_logit | 196 | 0.005 | 0.005 | +0.000 [+0.000, +0.000] | no | no |
| khop | 40 | d_cm | 68 | 0.015 | 0.000 | +0.015 [+0.000, +0.044] | YES | no |
| khop | 40 | d_logit | 196 | 0.000 | 0.005 | -0.005 [-0.015, +0.000] | no | no |
| khop | 44 | d_cm | 68 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | no | no |
| khop | 44 | d_logit | 196 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | no | no |
| poetry | 24 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | no | no |
| poetry | 28 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | no | no |
| poetry | 32 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | no | no |
| poetry | 36 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | no | no |
| poetry | 40 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | no | no |
| poetry | 44 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | no | no |

## R-S6 — the rhyme swap (poetry; the pre-registered rhyme statistic only)

| layer | arm | n | swapped-in-rhyme rate (`rhymes_planted`) | random | effect [95% CI] | R-S6 |
|---|---|---|---|---|---|---|
| 24 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | (control) |
| 24 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | does not work |
| 28 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | (control) |
| 28 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | does not work |
| 32 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | (control) |
| 32 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | does not work |
| 36 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | (control) |
| 36 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | does not work |
| 40 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | (control) |
| 40 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | does not work |
| 44 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | (control) |
| 44 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] | does not work |

`rhymes_true` (as logged) scores an identical word as a non-rhyme, so it is not a baseline (WS4); WS4's proposed extra statistic awaits Guiv and is not tabled.

## R-S2 / R-S3 / R-S4 — readers (khop)

Readers present: jlens, nla, olens (community), skip_a. Item set = items where d_swap flipped the model's answer at that layer; verdicts on fewer than 10 flipped items (layers ≥ 36 here) follow the rule as written but rest on 1–3 items.

| reader | layer | flipped items | tracks (bridge cross) | random band | R-S2/R-S3 | R-S4 bridge − answer follow [95% CI] |
|---|---|---|---|---|---|---|
| jlens | 24 | 136 | 0.74 | [0.02, 0.03] | TRACKS THE WORKSPACE | +0.088 [-0.144, +0.342] (n 118) |
| jlens | 28 | 20 | 0.65 | [0.05, 0.05] | TRACKS THE WORKSPACE | +0.084 [-0.102, +0.275] (n 118) |
| jlens | 32 | 11 | 0.64 | [0.00, 0.00] | TRACKS THE WORKSPACE | +0.083 [-0.074, +0.246] (n 118) |
| jlens | 36 | 3 | 0.33 | [0.00, 0.00] | WORKSPACE-BLIND | +0.046 [-0.057, +0.153] (n 118) |
| jlens | 40 | 1 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | +0.027 [+0.014, +0.041] (n 118) |
| jlens | 44 | 1 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | +0.000 [+0.000, +0.000] (n 118) |
| nla | 24 | 136 | 0.45 | [0.02, 0.04] | WORKSPACE-BLIND | — [—, —] (n 0) |
| nla | 28 | 20 | 0.40 | [0.05, 0.05] | WORKSPACE-BLIND | — [—, —] (n 0) |
| nla | 32 | 11 | 0.36 | [0.00, 0.00] | WORKSPACE-BLIND | — [—, —] (n 0) |
| nla | 36 | 3 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | — [—, —] (n 0) |
| nla | 40 | 1 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | — [—, —] (n 0) |
| nla | 44 | 1 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | — [—, —] (n 0) |
| olens (community) | 24 | 136 | 0.44 | [0.00, 0.01] | WORKSPACE-BLIND | +0.303 [+0.163, +0.445] (n 118) |
| olens (community) | 28 | 20 | 0.50 | [0.00, 0.05] | TRACKS THE WORKSPACE | +0.211 [+0.101, +0.329] (n 118) |
| olens (community) | 32 | 11 | 0.27 | [0.09, 0.18] | WORKSPACE-BLIND | +0.184 [+0.078, +0.301] (n 118) |
| olens (community) | 36 | 3 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | +0.147 [+0.073, +0.231] (n 118) |
| olens (community) | 40 | 1 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | +0.022 [+0.012, +0.032] (n 118) |
| olens (community) | 44 | 1 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | +0.000 [+0.000, +0.000] (n 118) |
| skip_a | 24 | 136 | 0.49 | [0.04, 0.04] | WORKSPACE-BLIND | +0.368 [+0.236, +0.494] (n 118) |
| skip_a | 28 | 20 | 0.55 | [0.00, 0.10] | TRACKS THE WORKSPACE | +0.343 [+0.245, +0.448] (n 118) |
| skip_a | 32 | 11 | 0.55 | [0.00, 0.09] | TRACKS THE WORKSPACE | +0.317 [+0.233, +0.407] (n 118) |
| skip_a | 36 | 3 | 0.33 | [0.00, 0.33] | WORKSPACE-BLIND | +0.225 [+0.162, +0.288] (n 118) |
| skip_a | 40 | 1 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | +0.020 [+0.007, +0.033] (n 118) |
| skip_a | 44 | 1 | 0.00 | [0.00, 0.00] | WORKSPACE-BLIND | +0.000 [+0.000, +0.000] (n 118) |

**Control for the read-backs (Guiv, 2026-10-20; added after the verdicts were computed):** each reader's bridge switch rate on R-S2's answer-flipped items under d_swap vs under the random directions at the same layer and norm (per item, the mean over d_rand0..2); real − random with a paired item bootstrap (1,000, seed 0).

| reader | layer | n | switch, d_swap | switch, random | real − random [95% CI] | without the 4 smoke-pass items: n, real − random [95% CI] |
|---|---|---|---|---|---|---|
| jlens | 24 | 136 | 0.743 | 0.025 | +0.718 [+0.642, +0.794] | 132, +0.710 [+0.626, +0.785] |
| nla | 24 | 136 | 0.449 | 0.032 | +0.417 [+0.331, +0.502] | 132, +0.422 [+0.338, +0.503] |
| olens (community) | 24 | 136 | 0.441 | 0.005 | +0.436 [+0.353, +0.525] | 132, +0.434 [+0.351, +0.520] |
| skip_a | 24 | 136 | 0.485 | 0.044 | +0.441 [+0.365, +0.522] | 132, +0.447 [+0.369, +0.528] |
| jlens | 28 | 20 | 0.650 | 0.050 | +0.600 [+0.400, +0.800] | 20, +0.600 [+0.400, +0.800] |
| nla | 28 | 20 | 0.400 | 0.050 | +0.350 [+0.167, +0.550] | 20, +0.350 [+0.167, +0.550] |
| olens (community) | 28 | 20 | 0.500 | 0.033 | +0.467 [+0.250, +0.667] | 20, +0.467 [+0.250, +0.667] |
| skip_a | 28 | 20 | 0.550 | 0.050 | +0.500 [+0.267, +0.700] | 20, +0.500 [+0.267, +0.700] |
| jlens | 32 | 11 | 0.636 | 0.000 | +0.636 [+0.364, +0.909] | 11, +0.636 [+0.364, +0.909] |
| nla | 32 | 11 | 0.364 | 0.000 | +0.364 [+0.091, +0.636] | 11, +0.364 [+0.091, +0.636] |
| olens (community) | 32 | 11 | 0.273 | 0.152 | +0.121 [+0.000, +0.303] | 11, +0.121 [+0.000, +0.303] |
| skip_a | 32 | 11 | 0.545 | 0.061 | +0.485 [+0.212, +0.758] | 11, +0.485 [+0.212, +0.758] |

Norm caveat: at L24, 4 items (0136, 0140, 0160, 0171) carry an edit scale from WS4's two pre-run smoke passes (`--limit 4` at 83.53, `--limit 2` at 86.22), which wrote into the real files, rather than the layer's s(L) over all items (76.07): 0140 and 0160 at 83.53 in every arm; 0136 and 0171 at 83.53 under d_swap but 86.22 under the random and logit arms (the random edit 3% larger, which is conservative for real − random). The right-hand column drops them.

The NLA is scored on the bridge pair only, by design (WS4's phase B passes records without `answer_gated`), so its R-S4 is undefined; R-S2/R-S3 need only the bridge pair.

**Post-hoc, descriptive (WS4's suggestion): signed bridge log-odds on the same items** (true − distractor; > 0 = still reports the true bridge). The crossing verdict depends on each reader's natural margin as well as on how far it moves.

| layer | reader | n | median natural | median edited | still true | median per-item shift |
|---|---|---|---|---|---|---|
| 24 | jlens | 136 | +0.59 | -1.02 | 0.096 | -1.67 |
| 24 | nla | 136 | +1.62 | -2.11 | 0.272 | -3.88 |
| 24 | olens (community) | 136 | +3.00 | -3.91 | 0.265 | -7.31 |
| 24 | skip_a | 136 | +1.99 | -2.83 | 0.265 | -5.20 |
| 28 | jlens | 20 | +0.52 | -1.08 | 0.100 | -1.62 |
| 28 | nla | 20 | +0.67 | -2.75 | 0.200 | -3.20 |
| 28 | olens (community) | 20 | +2.19 | -4.95 | 0.250 | -7.83 |
| 28 | skip_a | 20 | +1.37 | -3.51 | 0.200 | -4.32 |
| 32 | jlens | 11 | +0.64 | -0.95 | 0.182 | -1.61 |
| 32 | nla | 11 | +1.20 | -1.87 | 0.273 | -3.35 |
| 32 | olens (community) | 11 | +1.75 | -8.41 | 0.364 | -7.37 |
| 32 | skip_a | 11 | +1.99 | -3.66 | 0.182 | -4.67 |

**Post-hoc, descriptive (no pre-registered rule compares readers):** J-lens − other reader bridge cross rate on the same answer-flipped items, paired item bootstrap.

| layer | other | n | J-lens − other [95% CI] |
|---|---|---|---|
| 24 | nla | 136 | +0.294 [+0.191, +0.397] |
| 24 | olens (community) | 136 | +0.301 [+0.206, +0.404] |
| 24 | skip_a | 136 | +0.257 [+0.154, +0.360] |
| 28 | nla | 20 | +0.250 [-0.050, +0.500] |
| 28 | olens (community) | 20 | +0.150 [-0.150, +0.400] |
| 28 | skip_a | 20 | +0.100 [-0.150, +0.350] |
| 32 | nla | 11 | +0.273 [+0.000, +0.545] |
| 32 | olens (community) | 11 | +0.364 [+0.091, +0.636] |
| 32 | skip_a | 11 | +0.091 [-0.273, +0.455] |

## Poetry reader side (rows from queue row 5; readings in the 2026-10-20 WS3 bullet)

**R-S2 / R-S3 (poetry), as written: UNDEFINED at every layer** — the item set is the items whose completion rhymes with the swapped-in rhyme (§Metrics), and R-S6 found 0 such items under d_swap at any layer.

**Descriptive, not pre-registered by WS4 and not a verdict input:** the model's forced-choice preference on the rhyme pair (natural prefers the true rhyme → edited prefers the swapped-in rhyme).

| layer | arm | n | forced-choice flip | random | effect [95% CI] |
|---|---|---|---|---|---|
| 24 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 24 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 28 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 28 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 32 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 32 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 36 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 36 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 40 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 40 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 44 | d_logit | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| 44 | d_swap | 48 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |

**Descriptive:** each reader's rhyme-pair cross toward the swapped-in rhyme (natural LO > 0 → edited LO < 0) under d_swap, on all items and on the forced-choice-flipped items, with the random band (d_rand0..2) on the same items.

| reader | layer | cross, all items (n) | random band | cross, forced-choice-flipped items (n) | random band |
|---|---|---|---|---|---|
| jlens | 24 | 0.12 (48) | [0.02, 0.06] | — (0) | — |
| jlens | 28 | 0.15 (48) | [0.00, 0.02] | — (0) | — |
| jlens | 32 | 0.08 (48) | [0.00, 0.02] | — (0) | — |
| jlens | 36 | 0.06 (48) | [0.00, 0.00] | — (0) | — |
| jlens | 40 | 0.02 (48) | [0.00, 0.00] | — (0) | — |
| jlens | 44 | 0.00 (48) | [0.00, 0.00] | — (0) | — |
| nla | 24 | 0.02 (48) | [0.02, 0.02] | — (0) | — |
| nla | 28 | 0.02 (48) | [0.00, 0.02] | — (0) | — |
| nla | 32 | 0.02 (48) | [0.00, 0.00] | — (0) | — |
| nla | 36 | 0.00 (48) | [0.00, 0.00] | — (0) | — |
| nla | 40 | 0.00 (48) | [0.00, 0.02] | — (0) | — |
| nla | 44 | 0.00 (48) | [0.00, 0.00] | — (0) | — |
| olens (community) | 24 | 0.08 (48) | [0.02, 0.02] | — (0) | — |
| olens (community) | 28 | 0.06 (48) | [0.02, 0.02] | — (0) | — |
| olens (community) | 32 | 0.00 (48) | [0.00, 0.02] | — (0) | — |
| olens (community) | 36 | 0.00 (48) | [0.00, 0.02] | — (0) | — |
| olens (community) | 40 | 0.00 (48) | [0.00, 0.00] | — (0) | — |
| olens (community) | 44 | 0.00 (48) | [0.00, 0.00] | — (0) | — |
| skip_a | 24 | 0.04 (48) | [0.02, 0.04] | — (0) | — |
| skip_a | 28 | 0.04 (48) | [0.02, 0.02] | — (0) | — |
| skip_a | 32 | 0.04 (48) | [0.02, 0.02] | — (0) | — |
| skip_a | 36 | 0.00 (48) | [0.00, 0.02] | — (0) | — |
| skip_a | 40 | 0.02 (48) | [0.00, 0.00] | — (0) | — |
| skip_a | 44 | 0.00 (48) | [0.00, 0.00] | — (0) | — |

**J-lens toward the swapped-in rhyme, Wilson 95% CI (descriptive, no rule):** L24: J-lens 6/48 = 0.125 [0.059, 0.247] vs random 5/144 = 0.035 [0.015, 0.079] (three random directions pooled); L28: J-lens 7/48 = 0.146 [0.072, 0.272] vs random 2/144 = 0.014 [0.004, 0.049] (three random directions pooled).
