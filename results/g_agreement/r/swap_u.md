# SWAP-U — written vs used (BRIEF_R §26; EXPLORATORY)

Checkpoint tiers (BRIEF_RP §0): olens = community (agu18dec/olens_and_ar olens_s3d_rl600 (Qwen3.6-27B)); jlens = community (neuronpedia/jacobian-lens (Qwen3.6-27B)); nla = community (ceselder/qwen3.6-27b-nla-rl iter 400 (Qwen3.6-27B)); skip_a = community (agreelens skip lenses (Qwen3.6-27B)); prompt-only, probes and the logit lens = none. Every Oracle-lens number is the Qwen Oracle lens at that checkpoint. Each reader family is its own row; this file has no Gemma AO and no Qwen AO row, and never pools them with the Qwen Oracle lens.

Layer 24, J-lens bridge swap d_swap at α = 1, re_khop2_bridge test items. F = answer flipped (136); N = natural answer correct and not flipped (59); R = each item's mean over d_rand0..2 at the same layer and norm. Primary metric: per item, the reader's bridge log-odds shift toward the swapped-in bridge under d_swap minus the item's random-direction mean (d). N − R = mean d over N; F − R = mean d over F; ρ = N/F. Bootstrap 2,000 draws, seed 0, item level and fact-clustered (cluster = the true bridge), the wider interval quoted; BH q = 0.10 across the three primary readers. The J-lens is CIRCULAR (the swap is its own readout direction).

Answer-margin terciles: T0: F 45, N 20; T1: F 48, N 17; T2: F 43, N 22

## Primary

| reader | shift N: real, random | shift F: real, random | N − R [95%] | F − R [95%] | ρ = N/F [one-sided 95% bounds] | p (written) | p (use) | verdict |
|---|---|---|---|---|---|---|---|---|
| nla | +2.73, +0.13 | +4.33, +0.13 | +2.596 [+2.015, +3.406] | +4.203 [+3.681, +4.748] | +0.618 [+0.483, +0.793] | 0.080 | 0.920 | MIXED |
| olens (community) | +4.50, +0.11 | +7.15, +0.18 | +4.389 [+3.316, +5.824] | +6.974 [+6.266, +7.708] | +0.629 [+0.491, +0.806] | 0.066 | 0.934 | MIXED |
| skip_a | +3.35, +0.11 | +5.73, +0.09 | +3.233 [+2.535, +4.172] | +5.642 [+4.938, +6.384] | +0.573 [+0.453, +0.724] | 0.180 | 0.820 | MIXED |
| jlens | +1.03, +0.00 | +1.73, -0.02 | +1.034 [+0.847, +1.261] | +1.746 [+1.573, +1.922] | +0.592 [+0.493, +0.719] | 0.067 | 0.933 | MIXED (CIRCULAR, not in BH) |

## Margin-matched sensitivity (F standardised to N's answer-margin terciles)

| reader | shift N: real, random | shift F: real, random | N − R [95%] | F − R [95%] | ρ = N/F [one-sided 95% bounds] | p (written) | p (use) | verdict |
|---|---|---|---|---|---|---|---|---|
| nla | +2.73, +0.13 | +4.33, +0.13 | +2.596 [+2.015, +3.406] | +4.203 [+3.681, +4.769] | +0.618 [+0.480, +0.792] | 0.086 | 0.913 | MIXED |
| olens (community) | +4.50, +0.11 | +7.15, +0.18 | +4.389 [+3.316, +5.824] | +6.963 [+6.221, +7.719] | +0.630 [+0.490, +0.806] | 0.070 | 0.930 | MIXED |
| skip_a | +3.35, +0.11 | +5.73, +0.09 | +3.233 [+2.535, +4.172] | +5.680 [+4.944, +6.427] | +0.569 [+0.446, +0.722] | 0.203 | 0.797 | MIXED |
| jlens | +1.03, +0.00 | +1.73, -0.02 | +1.034 [+0.847, +1.261] | +1.745 [+1.569, +1.932] | +0.592 [+0.489, +0.719] | 0.073 | 0.927 | MIXED (CIRCULAR, not in BH) |

## Sensitivity: without the 4 smoke-pass items (norm caveat, swap.md)

| reader | shift N: real, random | shift F: real, random | N − R [95%] | F − R [95%] | ρ = N/F [one-sided 95% bounds] | p (written) | p (use) | verdict |
|---|---|---|---|---|---|---|---|---|
| nla | +2.73, +0.13 | +4.37, +0.13 | +2.596 [+2.015, +3.406] | +4.237 [+3.714, +4.773] | +0.613 [+0.478, +0.792] | 0.095 | 0.905 | MIXED |
| olens (community) | +4.50, +0.11 | +7.17, +0.19 | +4.389 [+3.316, +5.824] | +6.984 [+6.313, +7.675] | +0.628 [+0.488, +0.808] | 0.070 | 0.930 | MIXED |
| skip_a | +3.35, +0.11 | +5.75, +0.09 | +3.233 [+2.535, +4.172] | +5.658 [+4.957, +6.366] | +0.571 [+0.449, +0.732] | 0.191 | 0.809 | MIXED |
| jlens | +1.03, +0.00 | +1.75, -0.02 | +1.034 [+0.847, +1.261] | +1.772 [+1.608, +1.943] | +0.583 [+0.487, +0.709] | 0.085 | 0.915 | MIXED (CIRCULAR, not in BH) |

**Primary vs margin-matched:** they agree for every reader.

## Secondary (descriptive, no verdict): binary switch rate, as in the R-S2 table

| reader | F | N | R on N | R on F | F − N [95%] | N − R [95%] |
|---|---|---|---|---|---|---|
| nla | 0.449 | 0.305 | 0.034 | 0.032 | +0.143 [-0.010, +0.289] | +0.271 [+0.164, +0.384] |
| olens (community) | 0.441 | 0.254 | 0.000 | 0.005 | +0.187 [+0.046, +0.318] | +0.254 [+0.153, +0.373] |
| skip_a | 0.485 | 0.271 | 0.011 | 0.044 | +0.214 [+0.068, +0.350] | +0.260 [+0.153, +0.367] |
| jlens | 0.743 | 0.424 | 0.023 | 0.025 | +0.319 [+0.173, +0.462] | +0.401 [+0.282, +0.526] |

## 10 non-flipped (N) items, drawn with seed 0

| item | original bridge | swapped-in bridge | model answer: natural → swapped (LO) | J-lens | NLA | Oracle lens (community) | skip-lens |
|---|---|---|---|---|---|---|---|
| 0000 | Chile | Brazil | Spanish (+9.94) → Spanish (+0.00) | Brazil (-0.49 → -0.97; net +0.48) | Chile (+1.77 → +0.04; net +0.66) | Brazil (-2.00 → -3.47; net +1.47) | Brazil (-2.84 → -3.26; net +0.44) |
| 0009 | Sri Lanka | the United Arab Emirates | Colombo (+12.94) → Colombo (+10.56) | the United Arab Emirates (-2.10 → -2.99; net +0.86) | the United Arab Emirates (+3.34 → -0.27; net +4.40) | Sri Lanka (+16.09 → +10.38; net +5.28) | Sri Lanka (+10.60 → +6.84; net +3.72) |
| 0014 | Peru | Venezuela | Lima (+1.75) → Lima (+2.50) | Venezuela (-1.40 → -1.47; net +0.16) | Venezuela (-1.34 → -1.49; net +0.21) | Venezuela (-0.25 → -0.28; net +0.27) | Venezuela (-0.94 → -1.15; net +0.24) |
| 0030 | Poland | Hungary | Warsaw (+16.07) → Warsaw (+11.94) | Hungary (+0.09 → -0.38; net +0.57) | Poland (+1.01 → +1.59; net -0.45) | Poland (+2.25 → +0.38; net +1.87) | Hungary (-0.37 → -1.34; net +1.12) |
| 0036 | Brazil | Peru | Portuguese (+7.50) → Portuguese (+7.12) | Brazil (+1.58 → +1.25; net +0.37) | Brazil (+7.51 → +5.43; net +1.20) | Brazil (+6.81 → +4.56; net +1.39) | Brazil (+8.68 → +6.80; net +1.41) |
| 0039 | Spain | Hungary | Spanish (+13.56) → Spanish (+12.31) | Hungary (+1.12 → -0.18; net +1.23) | Spain (+6.80 → +2.90; net +3.62) | Hungary (+10.06 → -0.06; net +9.36) | Spain (+9.52 → +3.89; net +4.94) |
| 0077 | Argentina | Peru | Buenos Aires (+4.88) → Buenos Aires (+3.75) | Argentina (+1.68 → +1.56; net +0.14) | Argentina (+1.19 → +0.68; net +0.49) | Argentina (+4.69 → +4.31; net +0.47) | Argentina (+1.70 → +1.24; net +0.55) |
| 0092 | Indonesia | Argentina | Asia (+11.14) → Asia (+3.00) | Argentina (+0.39 → -2.79; net +3.13) | Argentina (+0.24 → -7.90; net +8.60) | Argentina (+8.44 → -9.69; net +17.50) | Argentina (+5.56 → -7.41; net +12.85) |
| 0130 | Malaysia | the Philippines | Kuala Lumpur (+12.01) → Kuala Lumpur (+0.00) | the Philippines (-0.19 → -0.55; net +0.41) | the Philippines (+1.67 → -0.31; net +2.01) | Malaysia (+12.25 → +8.77; net +3.54) | Malaysia (+5.96 → +4.03; net +1.20) |
| 0146 | Australia | Switzerland | Sydney (+11.50) → Sydney (+4.25) | Switzerland (+0.30 → -1.49; net +1.76) | Australia (+7.27 → +1.50; net +5.12) | Switzerland (+7.06 → -2.44; net +8.99) | Switzerland (+8.70 → -0.59; net +8.15) |

Reader cells: the bridge the reader reports under the swap (bridge LO true − swapped-in, natural → swapped; net shift d toward the swapped-in bridge beyond the random-direction mean).
