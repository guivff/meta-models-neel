# S6b — Qwen3-4B step zero on the single-token bank (GO iff J-lens AND Oracle read the key; NLA substitute exploratory)

Pre-registered in BRIEF_S.md "S6b" (2026-10-16 12:50 CEST); bank `f2/s6b_items.json` (5 name/word swaps). Target `Qwen/Qwen3-4B`, the 32 G1 test states (8 per family), last token. Readers: J-lens (`neuronpedia/jacobian-lens` qwen3-4b), Oracle LoRA (`qwen3-4b/oracle`, marker ㈎ forced), NLA = declared substitute `anicka/nla-qwen3-4b-universal-av` (the named `minnesotanlp/nla-qwen3-4b-L24-av` is gated: 403 with our token). Win = native lo(key) − lo(other) > 0 per state, Wilson 95%; a reader reads the key iff the lower bound > 50% (≥ 7/8) on ≥ 3 of 4 families.

**NO-GO** for the F2-2 + X6 replication on Qwen3-4B: readers reading the key at block 24: J-lens no (2/4 families), Oracle yes (3/4 families), NLA (anicka universal AV) no (2/4 families).

Target accuracy (greedy, rule-v1 parse): language 8/8, tense 8/8, ownership 8/8, mapping 7/8

## Native two-candidate win rate (per state) and free text (rule-v1)

| reader | block | family | win rate [Wilson 95%] | within-pair wins | reads key | free text: supports / contradicts / no claim |
|---|---|---|---|---|---|---|
| J-lens | 22 | language | 5/8 = 62% [31, 86] | 4/4 | no | 0 / 0 / 8 |
| J-lens | 22 | tense | 6/8 = 75% [41, 93] | 4/4 | no | 0 / 0 / 8 |
| J-lens | 22 | ownership | 4/8 = 50% [22, 78] | 3/4 | no | 0 / 0 / 8 |
| J-lens | 22 | mapping | 4/8 = 50% [22, 78] | 4/4 | no | 0 / 0 / 8 |
| J-lens | 24 | language | 8/8 = 100% [68, 100] | 4/4 | yes | 0 / 0 / 8 |
| J-lens | 24 | tense | 8/8 = 100% [68, 100] | 4/4 | yes | 0 / 0 / 8 |
| J-lens | 24 | ownership | 5/8 = 62% [31, 86] | 4/4 | no | 0 / 0 / 8 |
| J-lens | 24 | mapping | 4/8 = 50% [22, 78] | 4/4 | no | 0 / 0 / 8 |
| J-lens | 26 | language | 8/8 = 100% [68, 100] | 4/4 | yes | 0 / 0 / 8 |
| J-lens | 26 | tense | 7/8 = 88% [53, 98] | 4/4 | yes | 0 / 0 / 8 |
| J-lens | 26 | ownership | 5/8 = 62% [31, 86] | 4/4 | no | 1 / 0 / 7 |
| J-lens | 26 | mapping | 4/8 = 50% [22, 78] | 4/4 | no | 0 / 0 / 8 |
| Oracle | 22 | language | 6/8 = 75% [41, 93] | 4/4 | no | 4 / 2 / 2 |
| Oracle | 22 | tense | 8/8 = 100% [68, 100] | 4/4 | yes | 5 / 2 / 1 |
| Oracle | 22 | ownership | 4/8 = 50% [22, 78] | 3/4 | no | 0 / 0 / 8 |
| Oracle | 22 | mapping | 4/8 = 50% [22, 78] | 1/4 | no | 0 / 0 / 8 |
| Oracle | 24 | language | 6/8 = 75% [41, 93] | 4/4 | no | 8 / 0 / 0 |
| Oracle | 24 | tense | 8/8 = 100% [68, 100] | 4/4 | yes | 7 / 0 / 1 |
| Oracle | 24 | ownership | 8/8 = 100% [68, 100] | 4/4 | yes | 3 / 0 / 5 |
| Oracle | 24 | mapping | 7/8 = 88% [53, 98] | 4/4 | yes | 0 / 0 / 8 |
| Oracle | 26 | language | 5/8 = 62% [31, 86] | 4/4 | no | 7 / 0 / 1 |
| Oracle | 26 | tense | 7/8 = 88% [53, 98] | 4/4 | yes | 8 / 0 / 0 |
| Oracle | 26 | ownership | 8/8 = 100% [68, 100] | 4/4 | yes | 4 / 0 / 4 |
| Oracle | 26 | mapping | 5/8 = 62% [31, 86] | 4/4 | no | 0 / 1 / 7 |
| NLA (anicka universal AV) | 24 | language | 8/8 = 100% [68, 100] | 4/4 | yes | 2 / 0 / 6 |
| NLA (anicka universal AV) | 24 | tense | 7/8 = 88% [53, 98] | 4/4 | yes | 3 / 2 / 3 |
| NLA (anicka universal AV) | 24 | ownership | 4/8 = 50% [22, 78] | 4/4 | no | 0 / 0 / 8 |
| NLA (anicka universal AV) | 24 | mapping | 5/8 = 62% [31, 86] | 2/4 | no | 0 / 0 / 8 |

| reader | block | families read (of 4) | reads the key |
|---|---|---|---|
| J-lens | 22 | 0 | no |
| J-lens | 24 | 2 | no |
| J-lens | 26 | 2 | no |
| Oracle | 22 | 1 | no |
| Oracle | 24 | 3 | yes |
| Oracle | 26 | 2 | no |
| NLA (anicka universal AV) | 24 | 2 | no |
