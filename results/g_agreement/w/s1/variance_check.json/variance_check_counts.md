# W variance check — counts (verify before reader scoring)

items: `projects/g_agreement/banks/w/items_w.json`  states: `cache/g_agreement/w/states_L42`  units: 600 (centred)  dim: 5120

**STOP: factor(s) template explain > 25% of PC1 of the within-family differences; do not score readers on this family**

PCA of the differences (centred explained ratio / uncentred energy share): PC1 38.7% / 38.7%, PC2 15.6% / 15.6%, PC3 11.5% / 11.5% (uniform reference 0.2%)

| factor | levels | R² PC1 | R² PC2 | R² PC3 | η² full space | in stop rule |
|---|---|---|---|---|---|---|
| decade | 10 | 0.001 | 0.234 | 0.017 | 0.094 | yes |
| template | 4 | 0.993 | 0.534 | 0.164 | 0.538 | yes |
| object | 3 | 0.001 | 0.064 | 0.495 | 0.085 | yes |
| place | 12 | 0.001 | 0.021 | 0.074 | 0.080 | yes |

diagnostic value_linear_r2_pc1: 0.000
