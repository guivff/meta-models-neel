# W variance check — ownership4 (verify before reader scoring)

items: `projects/g_agreement/banks/w/items_w.json`  states: `cache/g_agreement/w/states_L42`  units: 64 (pairs)  dim: 5120

**STOP: factor(s) mention_pos_B, mention_pos_A explain > 25% of PC1 of the within-family differences; do not score readers on this family; Hewitt-Liang control PASS (mean LOO acc 0.507 on relabelled query_direction, limit 0.55)**

PCA of the differences (centred explained ratio / uncentred energy share): PC1 33.3% / 33.2%, PC2 14.6% / 14.5%, PC3 7.7% / 7.7% (uniform reference 1.6%)

| factor | levels | R² PC1 | R² PC2 | R² PC3 | η² full space | in stop rule |
|---|---|---|---|---|---|---|
| name_set | 4 | 0.002 | 0.006 | 0.025 | 0.026 | yes |
| template | 2 | 0.031 | 0.001 | 0.000 | 0.014 | yes |
| mention_order | 4 | 0.136 | 0.062 | 0.170 | 0.089 | yes |
| holder | 4 | 0.090 | 0.282 | 0.014 | 0.098 | yes |
| query_direction | 2 | 0.000 | 0.011 | 0.002 | 0.007 | yes |
| holder_b_shift | 3 | 0.002 | 0.010 | 0.121 | 0.023 | yes |
| mention_pos_A | 4 | 0.304 | 0.304 | 0.148 | 0.182 | yes |
| mention_pos_B | 4 | 0.380 | 0.431 | 0.090 | 0.213 | yes |
| answer_identity | 31 | 0.325 | 0.702 | 0.269 | 0.477 | diagnostic |

## within name_to_object (32 units)

| factor | R² PC1 | R² PC2 | R² PC3 | η² full space |
|---|---|---|---|---|
| name_set | 0.000 | 0.171 | 0.033 | 0.096 |
| template | 0.000 | 0.001 | 0.039 | 0.019 |
| mention_order | 0.057 | 0.029 | 0.147 | 0.088 |
| holder | 0.167 | 0.041 | 0.098 | 0.104 |
| holder_b_shift | 0.119 | 0.180 | 0.078 | 0.088 |
| mention_pos_A | 0.025 | 0.020 | 0.206 | 0.080 |
| mention_pos_B | 0.011 | 0.038 | 0.059 | 0.082 |
| answer_identity | 0.423 | 0.844 | 0.774 | 0.564 |

## within object_to_name (32 units)

| factor | R² PC1 | R² PC2 | R² PC3 | η² full space |
|---|---|---|---|---|
| name_set | 0.004 | 0.014 | 0.031 | 0.025 |
| template | 0.057 | 0.001 | 0.000 | 0.034 |
| mention_order | 0.255 | 0.118 | 0.415 | 0.209 |
| holder | 0.185 | 0.552 | 0.007 | 0.239 |
| holder_b_shift | 0.007 | 0.017 | 0.038 | 0.029 |
| mention_pos_A | 0.639 | 0.651 | 0.630 | 0.505 |
| mention_pos_B | 0.709 | 0.714 | 0.458 | 0.536 |
| answer_identity | 0.328 | 0.691 | 0.134 | 0.434 |

## Hewitt–Liang control

LOO difference-in-means probe on 20 random relabellings: mean acc 0.507, max 0.641 (limit on the mean 0.55) -> PASS.
Same probe on the true query_direction label: 0.422 (descriptive).
