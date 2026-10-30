# R-C2 planted-context conflicts — readers on compliers vs non-compliers, and on the model's switching (BRIEF_R §3.1 + E7)

Run 2026-10-19T04:38:27.092284+00:00; 21888 scorable reader rows; pair bootstrap 1000 (seed 0); Wilson 95 % CIs in brackets.
Selection on the model only: items {'complier': 266, 'non_complier': 22}; compliance among kept items 266/288 = 92% [89, 95]; by paraphrase q0 89/96 = 93% [86, 96], q1 89/96 = 93% [86, 96], q2 88/96 = 92% [84, 96]; pair keys {'complier_pair': 125, 'mixed_pair': 16, 'non_complier_pair': 3}; base items {'constant_complier': 87, 'constant_non_complier': 6, 'switching': 3}; the model switches between paraphrases on 3/96 = 3% [1, 9] of kept base items.

P(context) = P(lo > 0), lo = s(context) − s(belief). Verdict on complier items: READS THE CONTEXT iff ≥ 75 % with CI > 0.5; READS THE BELIEF iff ≤ 25 % with CI < 0.5; MIXED otherwise; UNDERPOWERED with < 24 complier items. Gates: shuffled CI must include 0.5; nosys P(belief) ≥ 0.75. '+ READS THE MODEL' iff P(context) ≤ 25 % on ≥ 12 non-complier items.

| reader | layer | P(context), compliers | P(context), non-compliers | pair win, complier pairs | nosys P(belief) | shuffled P(context) | verdict |
|---|---|---|---|---|---|---|---|
| jlens | 24 | 125/266 = 47% [41, 53] | 15/22 = 68% [47, 84] | 42% [34, 51] (n = 125) | 52% [46, 58] | 50% [44, 55] | NOT READING (nosys gate) |
| jlens | 28 | 126/266 = 47% [41, 53] | 15/22 = 68% [47, 84] | 28% [20, 37] (n = 125) | 52% [46, 58] | 50% [44, 56] | NOT READING (nosys gate) |
| jlens | 32 | 133/266 = 50% [44, 56] | 13/22 = 59% [39, 77] | 47% [38, 56] (n = 125) | 54% [48, 59] | 47% [41, 52] | NOT READING (nosys gate) |
| jlens | 36 | 148/266 = 56% [50, 61] | 13/22 = 59% [39, 77] | 77% [70, 84] (n = 125) | 60% [54, 65] | 49% [43, 54] | NOT READING (nosys gate) |
| jlens | 38 | 147/266 = 55% [49, 61] | 18/22 = 82% [61, 93] | 78% [71, 85] (n = 125) | 58% [53, 64] | 49% [44, 55] | NOT READING (nosys gate) |
| jlens | 40 | 156/266 = 59% [53, 64] | 18/22 = 82% [61, 93] | 77% [69, 84] (n = 125) | 63% [57, 69] | 47% [42, 53] | NOT READING (nosys gate) |
| jlens | 42 | 157/266 = 59% [53, 65] | 19/22 = 86% [67, 95] | 73% [65, 81] (n = 125) | 63% [57, 68] | 48% [43, 54] | NOT READING (nosys gate) |
| jlens | 44 | 147/266 = 55% [49, 61] | 17/22 = 77% [57, 90] | 71% [63, 79] (n = 125) | 64% [58, 69] | 47% [41, 53] | NOT READING (nosys gate) |
| jlens | 48 | 131/266 = 49% [43, 55] | 12/22 = 55% [35, 73] | 52% [44, 61] (n = 125) | 69% [64, 74] | 48% [42, 53] | NOT READING (nosys gate) |
| jlens | 52 | 198/266 = 74% [69, 79] | 13/22 = 59% [39, 77] | 99% [98, 100] (n = 125) | 78% [73, 83] | 47% [42, 53] | MIXED |
| jlens | 56 | 208/266 = 78% [73, 83] | 10/22 = 45% [27, 65] | 95% [91, 98] (n = 125) | 94% [90, 96] | 48% [42, 54] | READS THE CONTEXT (not the model) |
| jlens | 60 | 254/266 = 95% [92, 97] | 10/22 = 45% [27, 65] | 99% [98, 100] (n = 125) | 100% [99, 100] | 49% [43, 55] | READS THE CONTEXT (not the model) |
| nla | 42 | 50/266 = 19% [15, 24] | 3/22 = 14% [5, 33] | 10% [5, 16] (n = 125) | 95% [92, 97] | 12% [9, 16] | SHUFFLED CONTROL OFF 0.5 (pipeline check) |
| olens | 42 | 169/266 = 64% [58, 69] | 18/22 = 82% [61, 93] | 86% [80, 92] (n = 125) | 85% [80, 88] | 45% [40, 51] | MIXED |
| olens | 44 | 158/266 = 59% [53, 65] | 13/22 = 59% [39, 77] | 78% [71, 86] (n = 125) | 84% [79, 88] | 46% [40, 52] | MIXED |
| olens | 48 | 131/266 = 49% [43, 55] | 4/22 = 18% [7, 39] | 58% [49, 66] (n = 125) | 99% [97, 100] | 50% [44, 55] | MIXED |
| olens | 52 | 234/266 = 88% [84, 91] | 5/22 = 23% [10, 43] | 97% [93, 99] (n = 125) | 100% [99, 100] | 48% [43, 54] | READS THE CONTEXT + READS THE MODEL |
| olens | 56 | 248/266 = 93% [90, 96] | 4/22 = 18% [7, 39] | 98% [96, 100] (n = 125) | 99% [97, 100] | 46% [40, 52] | READS THE CONTEXT + READS THE MODEL |
| skip_a | 42 | 159/266 = 60% [54, 65] | 19/22 = 86% [67, 95] | 89% [83, 94] (n = 125) | 85% [80, 89] | 44% [38, 50] | SHUFFLED CONTROL OFF 0.5 (pipeline check) |

## E7 — does the reader switch with the model? (switching base items: the model complies on some paraphrases and not on others)

FOLLOWS = sign(lo) is + on exactly the complier paraphrases and − on the non-complier ones; CONSTANT = the same sign on all three. READS THE MODEL iff P(FOLLOWS) ≥ 75 % with CI > 0.5; CONSTANT iff P(CONSTANT) ≥ 75 % with CI > 0.5; UNDERPOWERED with < 12 switching items.

| reader | layer | switching items | P(follows) | P(constant) | row-level P(side = model) | verdict |
|---|---|---|---|---|---|---|
| jlens | 24 | 3 | 0% [0, 56] | 100% [44, 100] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |
| jlens | 28 | 3 | 0% [0, 56] | 100% [44, 100] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |
| jlens | 32 | 3 | 0% [0, 56] | 100% [44, 100] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |
| jlens | 36 | 3 | 0% [0, 56] | 100% [44, 100] | 56% [27, 81] | UNDERPOWERED (model switched on too few items) |
| jlens | 38 | 3 | 0% [0, 56] | 100% [44, 100] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |
| jlens | 40 | 3 | 0% [0, 56] | 100% [44, 100] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |
| jlens | 42 | 3 | 0% [0, 56] | 100% [44, 100] | 56% [27, 81] | UNDERPOWERED (model switched on too few items) |
| jlens | 44 | 3 | 33% [6, 79] | 67% [21, 94] | 56% [27, 81] | UNDERPOWERED (model switched on too few items) |
| jlens | 48 | 3 | 0% [0, 56] | 100% [44, 100] | 33% [12, 65] | UNDERPOWERED (model switched on too few items) |
| jlens | 52 | 3 | 0% [0, 56] | 100% [44, 100] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |
| jlens | 56 | 3 | 33% [6, 79] | 67% [21, 94] | 67% [35, 88] | UNDERPOWERED (model switched on too few items) |
| jlens | 60 | 3 | 0% [0, 56] | 100% [44, 100] | 56% [27, 81] | UNDERPOWERED (model switched on too few items) |
| nla | 42 | 3 | 0% [0, 56] | 100% [44, 100] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |
| olens | 42 | 3 | 0% [0, 56] | 100% [44, 100] | 56% [27, 81] | UNDERPOWERED (model switched on too few items) |
| olens | 44 | 3 | 33% [6, 79] | 67% [21, 94] | 67% [35, 88] | UNDERPOWERED (model switched on too few items) |
| olens | 48 | 3 | 0% [0, 56] | 67% [21, 94] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |
| olens | 52 | 3 | 0% [0, 56] | 100% [44, 100] | 33% [12, 65] | UNDERPOWERED (model switched on too few items) |
| olens | 56 | 3 | 0% [0, 56] | 67% [21, 94] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |
| skip_a | 42 | 3 | 0% [0, 56] | 100% [44, 100] | 44% [19, 73] | UNDERPOWERED (model switched on too few items) |

## PRESENT reference (leave-pair-out probe for the model's side) and H3

L_probe = 24 (first layer with held-out AUROC ≥ 0.75 and CI > 0.5; probe trainable: True). Reader AUROC = lo against the model's side on the same kept items; lag = L_reader − L_probe (H3 expects ≥ 4 blocks).

| reader | L_reader | L_probe | lag | reader vs probe AUROC by layer |
|---|---|---|---|---|
| jlens | 60 | 24 | 36 | L24: 0.40 vs 0.89; L28: 0.39 vs 0.90; L32: 0.34 vs 0.92; L36: 0.44 vs 0.94; L38: 0.39 vs 0.94; L40: 0.37 vs 0.93; L42: 0.38 vs 0.94; L44: 0.42 vs 0.95; L48: 0.43 vs 0.97; L52: 0.65 vs 0.96; L56: 0.75 vs 0.96; L60: 0.93 vs 0.97 |
| nla | None | 24 | None | L42: 0.49 vs 0.94 |
| olens | 52 | 24 | 28 | L42: 0.47 vs 0.94; L44: 0.51 vs 0.95; L48: 0.70 vs 0.97; L52: 0.90 vs 0.96; L56: 0.96 vs 0.96 |
| skip_a | None | 24 | None | L42: 0.36 vs 0.94 |

Per-paraphrase P(context) for compliers and non-compliers is in rc2.csv (columns q0_… q2_…); the probe's per-layer rows are in rc2_probe.csv.

Caveats: one model; 48 synthetic mirror pairs × 3 paraphrases; the visible prompt differs between the two versions of a pair (mirror questions); candidates spelled as the model answers them, J-lens on the distinguishing token; the secondary forced-choice compliance is in rc2_selection.json.
