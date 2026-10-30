**Prediction (§109):** Format limit if at least four of seven structure rows have (b)−(a) ≥0.10 with CI above zero and meet the registered donor-movement criterion. Real suppression if at least five of seven have (b)−(a) <0.05 and (d) AUROC ≥0.70 on those same rows. Otherwise mixed. Content controls should be near ceiling in (a), (b), (d).

**Assessment:** mixed. Format-limit qualifying rows: 0/7; real-suppression qualifying rows: 1/7.

EXPLORATORY. All ten rows and four arms are reported. The two frozen W1 paired log-odds are averaged before scoring. AUROC and (b)−(a) CIs use 2,000 W1 template-cluster resamples, seed 20261023. AUROC orientation remains W1 value A; no phrase selection or exclusions.

Donor movement follows the pre-output clarification 99518d4e: sign each arm toward the recipient item’s own truth, then count s_c < s_b; ties do not move. A row qualifies only when its fraction is ≥0.60 and its item-cluster bootstrap CI has lower bound >0.50 (2,000 resamples, seed 20261025). The bootstrap unit is the recipient item, keeping its two phrasing scores and paired arms together.

| Row | (a) AUROC [95% CI] | (b) | (c) | (d) | (b)−(a) [95% CI] |
|---|---|---|---|---|---|
| latex_subject | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.9977 [0.9864, 1.0000] | 0.0000 [0.0000, 0.0000] |
| list_depth | 0.6332 [0.5731, 0.8033] | 0.5289 [0.4155, 0.6429] | 0.6088 [0.5459, 0.7704] | 0.4785 [0.3441, 0.5924] | -0.1043 [-0.2285, -0.0476] |
| prose_paren | 0.4745 [0.2528, 0.6457] | 0.4178 [0.2131, 0.6173] | 0.4456 [0.2608, 0.5986] | 0.3418 [0.1264, 0.5958] | -0.0567 [-0.1644, 0.0516] |
| prose_quote | 0.5618 [0.2499, 0.8356] | 0.4388 [0.2296, 0.6668] | 0.5726 [0.3787, 0.7800] | 0.4402 [0.2239, 0.7110] | -0.1230 [-0.2778, 0.0556] |
| prose_sentiment | 0.9099 [0.6344, 1.0000] | 0.9331 [0.8389, 1.0000] | 0.9235 [0.7381, 1.0000] | 0.9728 [0.9297, 1.0000] | 0.0232 [-0.0204, 0.2500] |
| python_depth | 0.4932 [0.4490, 0.5488] | 0.5884 [0.5187, 0.6655] | 0.5011 [0.4603, 0.5522] | 0.6139 [0.4847, 0.7347] | 0.0952 [0.0431, 0.1474] |
| python_indent | 0.5884 [0.3537, 0.8396] | 0.4286 [0.1655, 0.6791] | 0.5210 [0.3129, 0.7483] | 0.3537 [0.1457, 0.5443] | -0.1599 [-0.3152, -0.0464] |
| python_string | 0.6417 [0.5023, 0.7789] | 0.5845 [0.4393, 0.7273] | 0.6939 [0.5510, 0.8265] | 0.4960 [0.4393, 0.5669] | -0.0573 [-0.1644, 0.0522] |
| table_role | 0.4388 [0.2154, 0.6894] | 0.3027 [0.1213, 0.5394] | 0.3736 [0.1650, 0.6355] | 0.7948 [0.6292, 0.9172] | -0.1361 [-0.1808, -0.0646] |
| table_status | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.9949 [0.9841, 1.0000] | 0.0000 [0.0000, 0.0000] |

| Row | Donor-directed items | Fraction [item-bootstrap 95% CI] | Row moves |
|---|---:|---|---|
| latex_subject | 40/84 | 0.4762 [0.3571, 0.5833] | no |
| list_depth | 29/84 | 0.3452 [0.2500, 0.4405] | no |
| prose_paren | 36/84 | 0.4286 [0.3214, 0.5357] | no |
| prose_quote | 34/84 | 0.4048 [0.2976, 0.5119] | no |
| prose_sentiment | 43/84 | 0.5119 [0.4048, 0.6190] | no |
| python_depth | 56/84 | 0.6667 [0.5595, 0.7619] | yes |
| python_indent | 34/84 | 0.4048 [0.3092, 0.5119] | no |
| python_string | 32/84 | 0.3810 [0.2857, 0.4881] | no |
| table_role | 30/84 | 0.3571 [0.2619, 0.4643] | no |
| table_status | 37/84 | 0.4405 [0.3333, 0.5476] | no |
