**Prediction (§99):** On structure rows, text alone is above chance and b ≈ c ≈ d; on meaning rows b > d.

**Assessment: the prediction partly held, with clear structure-row exceptions.** This is the **primary E12 result, Oracle-only**, admitted under §99’s 2026-10-24 06:50 CEST ruling (`f70894e1`). Both Oracle paths are sealed and all four arms cover all 2,100 items; the original packed run remains INCOMPLETE because the NLA paths did not finish. Meaning rows support b > d (equal-row mean difference 0.8924, 95% CI [0.7932, 0.9691]). The structure prediction is mixed: text-only mean AUROC is 0.5593 on count-like rows and 0.6284 on state-like rows, with large row differences. State-like b−d is positive on average (0.1419 [0.0349, 0.2646]), so activation insensitivity does not hold uniformly. In particular, `json_type` and `python_string` have positive b−c and b−d contrasts with both CIs above zero; these are registered surprise-pattern examples. Count-like b−c and b−d CIs include zero, which does not establish b ≈ c ≈ d without an equivalence margin. The full text-recovers-structure/ignores-activation prediction did not hold across rows. No new pass or equivalence threshold is added.

EXPLORATORY. Prefix arms are outside both readers’ training distribution. Text-only leaves the placeholder’s own embedding/residual untouched. Frozen W1 donors are opposite-value, matched within template; no redraw. Native W1 score and AUROC reproduction differences are reported without tolerance-based exclusions. NLA unavailability is explicit; KV-olens is not tested.

| Reader | Row | Class | a | b | c | d | b−c [95% CI] | b−d [95% CI] | b−a [95% CI] |
|---|---|---|---:|---:|---:|---:|---|---|---|
| olens | json_status | semantic | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 [0.0000, 0.0000] | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| olens | json_type | state-like | 0.6593 | 0.6956 | 0.6088 | 0.3141 | 0.0867 [0.0408, 0.1139] | 0.3815 [0.3152, 0.4456] | 0.0363 [0.0074, 0.0629] |
| olens | latex_environment | state-like | 0.5782 | 0.6400 | 1.0000 | 0.5181 | -0.3600 [-0.3690, -0.1797] | 0.1219 [0.0153, 0.3940] | 0.0618 [0.0102, 0.2039] |
| olens | latex_role | semantic | 0.8452 | 0.8668 | 0.4688 | 0.1621 | 0.3980 [-0.0402, 0.7778] | 0.7046 [0.1961, 1.0000] | 0.0215 [-0.0595, 0.0578] |
| olens | latex_section | count-like | 0.4478 | 0.4977 | 0.8861 | 0.6327 | -0.3883 [-0.5232, -0.3152] | -0.1349 [-0.2194, -0.0096] | 0.0499 [-0.0811, 0.1735] |
| olens | latex_subject | semantic | 1.0000 | 1.0000 | 1.0000 | 0.0040 | 0.0000 [0.0000, 0.0000] | 0.9960 [0.9841, 1.0000] | 0.0000 [0.0000, 0.0000] |
| olens | list_depth | count-like | 0.6332 | 0.5391 | 0.3883 | 0.3379 | 0.1508 [0.0016, 0.4082] | 0.2012 [-0.0494, 0.5811] | -0.0941 [-0.3679, 0.0266] |
| olens | list_index | count-like | 0.4252 | 0.4331 | 0.4938 | 0.4529 | -0.0607 [-0.3237, 0.2812] | -0.0198 [-0.2704, 0.2496] | 0.0079 [-0.0658, 0.1071] |
| olens | list_priority | semantic | 0.8929 | 0.8503 | 0.8163 | 0.1604 | 0.0340 [-0.4354, 0.5567] | 0.6899 [0.0170, 1.0000] | -0.0425 [-0.1327, 0.0000] |
| olens | list_topic | semantic | 0.9683 | 0.9598 | 1.0000 | 0.1344 | -0.0402 [-0.1236, 0.0000] | 0.8254 [0.5947, 0.9926] | -0.0085 [-0.0635, 0.0748] |
| olens | prose_paren | state-like | 0.4745 | 0.4994 | 0.5505 | 0.5017 | -0.0510 [-0.3311, 0.1525] | -0.0023 [-0.2727, 0.2710] | 0.0249 [-0.1191, 0.2075] |
| olens | prose_quote | state-like | 0.5618 | 0.5045 | 0.5771 | 0.5334 | -0.0726 [-0.3793, 0.1162] | -0.0289 [-0.5227, 0.4467] | -0.0573 [-0.2636, 0.3362] |
| olens | prose_sentence | count-like | 0.5238 | 0.5845 | 0.7398 | 0.5040 | -0.1553 [-0.5789, 0.3158] | 0.0805 [-0.4274, 0.5074] | 0.0607 [-0.0079, 0.1389] |
| olens | prose_sentiment | semantic | 0.9099 | 0.9478 | 1.0000 | 0.1293 | -0.0522 [-0.2806, 0.0000] | 0.8186 [0.2907, 1.0000] | 0.0380 [0.0000, 0.1020] |
| olens | prose_topic | semantic | 1.0000 | 1.0000 | 1.0000 | 0.0034 | 0.0000 [0.0000, 0.0000] | 0.9966 [0.9762, 1.0000] | 0.0000 [0.0000, 0.0000] |
| olens | python_argument | count-like | 0.5068 | 0.3940 | 0.3356 | 0.4586 | 0.0584 [-0.2851, 0.3384] | -0.0646 [-0.2880, 0.1871] | -0.1128 [-0.1859, -0.0454] |
| olens | python_comment | state-like | 0.5425 | 0.4904 | 0.4314 | 0.5068 | 0.0590 [-0.0658, 0.2307] | -0.0164 [-0.1622, 0.0873] | -0.0522 [-0.0930, -0.0300] |
| olens | python_depth | count-like | 0.4932 | 0.5306 | 0.8571 | 0.5164 | -0.3265 [-0.4076, -0.2902] | 0.0142 [-0.0981, 0.1077] | 0.0374 [0.0153, 0.0720] |
| olens | python_error | semantic | 1.0000 | 1.0000 | 0.9388 | 0.0000 | 0.0612 [0.0000, 0.1417] | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| olens | python_indent | count-like | 0.5884 | 0.5760 | 0.4677 | 0.4524 | 0.1083 [-0.1032, 0.3407] | 0.1236 [-0.3690, 0.6735] | -0.0125 [-0.0765, 0.1094] |
| olens | python_string | state-like | 0.6417 | 0.7551 | 0.6298 | 0.2829 | 0.1253 [0.0125, 0.2171] | 0.4722 [0.2527, 0.6650] | 0.1134 [0.0567, 0.2063] |
| olens | table_column | count-like | 0.4762 | 0.3736 | 0.2477 | 0.5437 | 0.1259 [-0.1417, 0.3594] | -0.1701 [-0.3686, 0.0204] | -0.1026 [-0.1859, -0.0266] |
| olens | table_role | state-like | 0.4388 | 0.5998 | 0.6009 | 0.5346 | -0.0011 [-0.1168, 0.1576] | 0.0652 [-0.3770, 0.4870] | 0.1610 [0.0193, 0.3622] |
| olens | table_row | count-like | 0.5000 | 0.5272 | 0.6179 | 0.4167 | -0.0907 [-0.3486, 0.0890] | 0.1105 [-0.0794, 0.3203] | 0.0272 [-0.0561, 0.1315] |
| olens | table_status | semantic | 1.0000 | 1.0000 | 0.5442 | 0.0000 | 0.4558 [0.2379, 0.6895] | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |

Class means/CIs and every native W1 reproduction difference: `metrics.json`. Prefix support: {'nla': 'SUPPORTED_NATIVE_PREFIX', 'olens': 'SUPPORTED_NATIVE_PREFIX'}

Equal-row class means and registered paired contrasts (AUROC differences):

| Class | Rows | a | b | c | d | b−c [95% CI] | b−d [95% CI] | b−a [95% CI] |
|---|---:|---:|---:|---:|---:|---|---|---|
| semantic | 9 | 0.9574 | 0.9583 | 0.8631 | 0.0659 | 0.0952 [0.0233, 0.1766] | 0.8924 [0.7932, 0.9691] | 0.0009 [-0.0137, 0.0133] |
| state-like | 7 | 0.5567 | 0.5978 | 0.6284 | 0.4559 | -0.0305 [-0.0872, 0.0350] | 0.1419 [0.0349, 0.2646] | 0.0411 [-0.0048, 0.1103] |
| count-like | 9 | 0.5105 | 0.4951 | 0.5593 | 0.4795 | -0.0642 [-0.1480, 0.0267] | 0.0156 [-0.0774, 0.1236] | -0.0154 [-0.0525, 0.0148] |

Native W1 reproduction is close in AUROC but not token-score exact: maximum across rows of the absolute phrasing-score difference is 0.683327 nats; largest absolute a−W1 AUROC difference is 0.015306. Every row’s differences are in `metrics.json`; no exclusions or tolerance gate were applied. NLA had passed prefix setup but has no complete sealed score grid. Its result is INCOMPLETE, to be collected in a fresh NLA-only attempt.
