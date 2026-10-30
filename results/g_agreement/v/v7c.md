# V7 confirmatory — 48 target-private ownership pairs × 2 preamble roles (PREREG_WV.md 2026-10-12 10:40 UTC)

Run 2026-10-12T12:04:50+00:00; rows /Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/w/s3_lo.jsonl (1536 V7c reader rows); items /Users/guivff/Documents/Neel_Exploration/mats-minis/projects/g_agreement/banks/w/items_v7c.json; pair bootstrap 1000 (seed 0); Wilson in brackets. Win = lo_own(A) + lo_own(B) > 0. Role s = preamble as the system turn (target-private, visible prompt identical within the pair, prompt-only baseline 50 % by construction); role u = preamble in the user turn (control).

**Primary verdict: CONFIRMED for jlens@L42, olens@L42, olens@L38, skip_a@L42.**

## Primary cells (role = system, 48 pairs)

| cell | within-pair win | mean margin (nats) | ≥ 0.70 & CI > 0.5 |
|---|---|---|---|
| jlens@L42 | 42/48 = 87.5% boot[77.1, 95.8] wilson[75.3, 94.1] | +0.05 | YES |
| olens@L42 | 45/48 = 93.8% boot[85.4, 100.0] wilson[83.2, 97.9] | +0.75 | YES |
| olens@L38 | 38/48 = 79.2% boot[66.7, 89.6] wilson[65.7, 88.3] | +0.43 | YES |
| skip_a@L42 | 39/48 = 81.2% boot[68.8, 91.7] wilson[68.1, 89.8] | +0.49 | YES |

## All cells per role and per mention order

| cell | system (48) | user (48) | system − user [CI] | role effect | system, answer first (24) | system, answer second (24) |
|---|---|---|---|---|---|---|
| jlens@L42 | 42/48 = 87.5% boot[77.1, 95.8] wilson[75.3, 94.1] | 36/48 = 75.0% boot[62.5, 87.5] wilson[61.2, 85.1] | +12.5 [+2.1, +22.9] | YES | 19/24 = 79.2% boot[62.5, 91.7] wilson[59.5, 90.8] | 23/24 = 95.8% boot[87.5, 100.0] wilson[79.8, 99.3] |
| jlens@L38 | 30/48 = 62.5% boot[49.9, 77.1] wilson[48.4, 74.8] | 28/48 = 58.3% boot[43.8, 70.8] wilson[44.3, 71.2] | +4.2 [-8.3, +16.7] | no | 11/24 = 45.8% boot[25.0, 66.7] wilson[27.9, 64.9] | 19/24 = 79.2% boot[58.3, 91.7] wilson[59.5, 90.8] |
| olens@L42 | 45/48 = 93.8% boot[85.4, 100.0] wilson[83.2, 97.9] | 40/48 = 83.3% boot[72.9, 93.8] wilson[70.4, 91.3] | +10.4 [+2.1, +20.8] | YES | 22/24 = 91.7% boot[79.2, 100.0] wilson[74.2, 97.7] | 23/24 = 95.8% boot[87.5, 100.0] wilson[79.8, 99.3] |
| olens@L38 | 38/48 = 79.2% boot[66.7, 89.6] wilson[65.7, 88.3] | 35/48 = 72.9% boot[60.4, 83.3] wilson[59.0, 83.4] | +6.2 [-6.2, +18.8] | no | 16/24 = 66.7% boot[49.9, 83.3] wilson[46.7, 82.0] | 22/24 = 91.7% boot[79.2, 100.0] wilson[74.2, 97.7] |
| skip_a@L42 | 39/48 = 81.2% boot[68.8, 91.7] wilson[68.1, 89.8] | 39/48 = 81.2% boot[70.8, 91.7] wilson[68.1, 89.8] | +0.0 [-10.4, +10.4] | no | 16/24 = 66.7% boot[50.0, 83.3] wilson[46.7, 82.0] | 23/24 = 95.8% boot[87.5, 100.0] wilson[79.8, 99.3] |
| probe@L42 | 47/48 = 97.9% boot[93.8, 100.0] wilson[89.1, 99.6] | 48/48 = 100.0% boot[100.0, 100.0] wilson[92.6, 100.0] | -2.1 [-6.2, +0.0] | no | 23/24 = 95.8% boot[87.5, 100.0] wilson[79.8, 99.3] | 24/24 = 100.0% boot[100.0, 100.0] wilson[86.2, 100.0] |
| probe@L38 | 45/48 = 93.8% boot[85.4, 100.0] wilson[83.2, 97.9] | 48/48 = 100.0% boot[100.0, 100.0] wilson[92.6, 100.0] | -6.2 [-14.6, +0.0] | no | 21/24 = 87.5% boot[70.8, 100.0] wilson[69.0, 95.7] | 24/24 = 100.0% boot[100.0, 100.0] wilson[86.2, 100.0] |
| nla@L42 | 45/48 = 93.8% boot[85.4, 100.0] wilson[83.2, 97.9] | 34/48 = 70.8% boot[60.4, 83.3] wilson[56.8, 81.8] | +22.9 [+10.4, +35.4] | YES | 21/24 = 87.5% boot[75.0, 100.0] wilson[69.0, 95.7] | 24/24 = 100.0% boot[100.0, 100.0] wilson[86.2, 100.0] |

Target ceiling, role system: greedy accuracy 96/96 = 100.0%; pair win by first-token log-odds 48/48

Target ceiling, role user: greedy accuracy 96/96 = 100.0%; pair win by first-token log-odds 48/48

Caveats: one model, synthetic prompts; the probe is the Track-B ownership probe (trained on user-turn statements) with the orientation rule reading the preamble (fix 2026-10-12), exploratory; NLA only if phase B ran; no V6 span capture for these items.
