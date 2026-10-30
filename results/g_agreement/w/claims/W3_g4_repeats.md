# W3 supplement: G4 repeat samples (8 test items x 2 readers x samples 1-2)

Judge: `google/gemini-3.8-flash` (OpenRouter, temperature 0, strict JSON schema), adapted from Michael Kenney's `nla-consistency/scripts/claim_judge.py` (see `projects/g_agreement/w_claims/judge.py`). Precision = true / (true + false) pooled over claims; CI = item-level bootstrap (1000 resamples, seed 0); unverifiable claims excluded from precision.

## Precision table

| reader | readouts | items | claims | claims/readout | input share | computation share | unverifiable | input precision [95% CI] | computation precision [95% CI] | all | readouts with >=1 false claim |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NLA | 16 | 8 | 118 | 7.4 | 79% | 20% | 1% | 25% [20, 30] (n=93) | 42% [19, 67] (n=24) | 28% [21, 36] (n=117) | 100% [81, 100] |
| Oracle | 16 | 8 | 96 | 6.0 | 33% | 65% | 2% | 38% [19, 61] (n=32) | 40% [10, 69] (n=62) | 39% [18, 64] (n=94) | 81% [57, 93] |

## Per family (point estimates, 8 test items per family)

| reader | family | input precision | computation precision |
|---|---|---|---|
| NLA | language | 35% [33, 36] (n=23) | 100% [100, 100] (n=4) |
| NLA | mapping | 26% [23, 30] (n=23) | 12% [0, 25] (n=8) |
| NLA | ownership | 16% [15, 17] (n=25) | 17% [0, 25] (n=6) |
| NLA | tense | 23% [18, 27] (n=22) | 67% [67, 67] (n=6) |
| Oracle | language | 83% [80, 100] (n=6) | 47% [43, 50] (n=17) |
| Oracle | mapping | 15% [0, 29] (n=13) | 0% [0, 0] (n=15) |
| Oracle | ownership | 36% [33, 40] (n=11) | 0% [0, 0] (n=13) |
| Oracle | tense | 50% [50, 50] (n=2) | 100% [100, 100] (n=17) |

## Cross-tab with rule-v1 correctness of the same readout

No native log-odds exist for the G1 states (`cache/g_agreement/x/x1_lo.jsonl` covers the X bank), so the cross-tab uses the rule-v1 extractor's primary status on the same readout (`results/g_agreement/claims/g1.jsonl`; `supports` = the rule read the correct candidate).

| reader | rule-v1 | readouts | computation precision [CI] | readouts: comp_true & no comp_false | readouts: any comp_false |
|---|---|---|---|---|---|
| NLA | rule_supports | 8 | 80% [67, 100] (n=10) | 6 | 2 |
| NLA | rule_other | 8 | 14% [0, 25] (n=14) | 0 | 8 |
| Oracle | rule_supports | 8 | 74% [47, 100] (n=34) | 4 | 4 |
| Oracle | rule_other | 8 | 0% [0, 0] (n=28) | 0 | 8 |
