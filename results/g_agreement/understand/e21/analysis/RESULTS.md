**Prediction (§113, clarification 6a2b114e):** Across all25 rows, raw cosine describe reward predicts W1 Oracle asked AUROC: Spearman ρ ≥0.50 with row-bootstrap CI above zero.

**Primary assessment:** not met. ρ = 0.477435196556111; 95% CI [0.13557221076591808, 0.7398607822414285].

EXPLORATORY. Describe/exhibit reward is the fraction of paired own-activation cosine contrasts above zero (exact ties weight0.5), after averaging both frozen variants. No whitening enters the primary. All25 rows and 84test items per row retained. Item/row bootstraps:2000,seed20261025.

| Row | Describe reward [95% CI] | Exhibit reward [95% CI] | W1 Oracle asked AUROC |
|---|---|---|---|
| json_status | 1.0000 [1.0000, 1.0000] | 0.7381 [0.6429, 0.8333] | 1.0000 |
| json_type | 0.5119 [0.4167, 0.6190] | 0.6548 [0.5595, 0.7500] | 0.6599 |
| latex_environment | 0.5000 [0.3929, 0.6071] | 0.8095 [0.7262, 0.8929] | 0.5709 |
| latex_role | 0.6429 [0.5357, 0.7381] | 0.6012 [0.5060, 0.6964] | 0.8435 |
| latex_section | 0.5000 [0.3929, 0.6071] | 0.5119 [0.4048, 0.6190] | 0.4325 |
| latex_subject | 0.5000 [0.4045, 0.6071] | 0.7143 [0.6190, 0.8095] | 1.0000 |
| list_depth | 0.5000 [0.3929, 0.6071] | 0.5000 [0.3929, 0.6071] | 0.6338 |
| list_index | 0.5000 [0.3929, 0.6071] | 0.6845 [0.5893, 0.7738] | 0.4189 |
| list_priority | 0.5000 [0.3929, 0.6071] | 0.8929 [0.8214, 0.9524] | 0.8906 |
| list_topic | 0.7262 [0.6310, 0.8214] | 0.9286 [0.8690, 0.9762] | 0.9677 |
| prose_paren | 0.5000 [0.3929, 0.6071] | 0.5000 [0.3929, 0.6071] | 0.4847 |
| prose_quote | 0.5000 [0.3929, 0.6071] | 0.5000 [0.3929, 0.6071] | 0.5629 |
| prose_sentence | 0.6071 [0.5119, 0.7143] | 0.7500 [0.6548, 0.8452] | 0.5312 |
| prose_sentiment | 0.5000 [0.3929, 0.6071] | 0.7857 [0.7024, 0.8690] | 0.9110 |
| prose_topic | 0.5714 [0.4643, 0.6667] | 0.7381 [0.6310, 0.8214] | 1.0000 |
| python_argument | 0.5000 [0.3929, 0.6071] | 0.4940 [0.3810, 0.6071] | 0.5000 |
| python_comment | 0.5000 [0.3929, 0.6071] | 0.8452 [0.7619, 0.9167] | 0.5425 |
| python_depth | 0.5000 [0.3929, 0.6071] | 0.5000 [0.3929, 0.6071] | 0.4875 |
| python_error | 0.5000 [0.3929, 0.6071] | 0.5714 [0.4643, 0.6786] | 1.0000 |
| python_indent | 0.4048 [0.2976, 0.5119] | 0.5000 [0.3929, 0.6071] | 0.5918 |
| python_string | 0.5000 [0.3929, 0.6071] | 0.5000 [0.3929, 0.6071] | 0.6440 |
| table_column | 0.5000 [0.3929, 0.6071] | 0.5000 [0.3929, 0.6071] | 0.4745 |
| table_role | 0.5000 [0.3929, 0.6071] | 0.6786 [0.5714, 0.7738] | 0.4382 |
| table_row | 0.5000 [0.3929, 0.6071] | 0.5357 [0.4286, 0.6429] | 0.5006 |
| table_status | 1.0000 [1.0000, 1.0000] | 0.4643 [0.3631, 0.5655] | 1.0000 |

Secondary dev-probe measures (fixed dev fit; item-bootstrap 95% CIs):

| Row | Describe: own-truth-signed true vs opposite AUROC | Exhibit: across-state AUROC |
|---|---|---|
| json_status | 1.0000 [1.0000, 1.0000] | 0.9983 [0.9921, 1.0000] |
| json_type | 0.7500 [0.7500, 0.7642] | 0.9875 [0.9567, 1.0000] |
| latex_environment | 0.7500 [0.7500, 0.7642] | 0.8243 [0.7231, 0.9162] |
| latex_role | 0.2500 [0.2358, 0.2500] | 0.7653 [0.6632, 0.8568] |
| latex_section | 0.2500 [0.2358, 0.2500] | 0.7531 [0.6430, 0.8599] |
| latex_subject | 0.7500 [0.7500, 0.7642] | 0.8583 [0.7707, 0.9288] |
| list_depth | 0.7500 [0.7500, 0.7642] | 1.0000 [1.0000, 1.0000] |
| list_index | 0.7500 [0.7500, 0.7642] | 0.4790 [0.3571, 0.6069] |
| list_priority | 0.7500 [0.7500, 0.7642] | 0.8889 [0.8125, 0.9493] |
| list_topic | 0.7500 [0.7500, 0.7642] | 0.9994 [0.9966, 1.0000] |
| prose_paren | 0.7500 [0.7500, 0.7642] | 1.0000 [1.0000, 1.0000] |
| prose_quote | 0.2500 [0.2358, 0.2500] | 1.0000 [1.0000, 1.0000] |
| prose_sentence | 0.7500 [0.7500, 0.7642] | 0.6536 [0.5270, 0.7664] |
| prose_sentiment | 1.0000 [1.0000, 1.0000] | 0.9243 [0.8669, 0.9693] |
| prose_topic | 0.7500 [0.7500, 0.7642] | 0.9779 [0.9462, 1.0000] |
| python_argument | 0.2500 [0.2358, 0.2500] | 0.9816 [0.9580, 0.9972] |
| python_comment | 0.7500 [0.7500, 0.7642] | 1.0000 [1.0000, 1.0000] |
| python_depth | 0.2500 [0.2358, 0.2500] | 1.0000 [1.0000, 1.0000] |
| python_error | 0.7500 [0.7500, 0.7642] | 0.9836 [0.9601, 0.9977] |
| python_indent | 0.2500 [0.2358, 0.2500] | 1.0000 [1.0000, 1.0000] |
| python_string | 0.2500 [0.2358, 0.2500] | 1.0000 [1.0000, 1.0000] |
| table_column | 0.7500 [0.7500, 0.7642] | 0.0000 [0.0000, 0.0000] |
| table_role | 0.2500 [0.2358, 0.2500] | 1.0000 [1.0000, 1.0000] |
| table_row | 0.7500 [0.7500, 0.7642] | 0.8129 [0.7119, 0.8996] |
| table_status | 0.7500 [0.7500, 0.7642] | 0.5300 [0.4024, 0.6548] |

Secondary fixed-whitener cosine rewards (primary remains raw):

| Row | Describe reward [95% CI] | Exhibit reward [95% CI] |
|---|---|---|
| json_status | 1.0000 [1.0000, 1.0000] | 0.6071 [0.5000, 0.7143] |
| json_type | 0.5595 [0.4524, 0.6667] | 0.7976 [0.7143, 0.8810] |
| latex_environment | 0.5476 [0.4405, 0.6548] | 0.8452 [0.7619, 0.9167] |
| latex_role | 0.5833 [0.4762, 0.6905] | 0.6488 [0.5595, 0.7381] |
| latex_section | 0.5119 [0.4048, 0.6190] | 0.6190 [0.5238, 0.7143] |
| latex_subject | 0.9881 [0.9643, 1.0000] | 0.7619 [0.6667, 0.8452] |
| list_depth | 0.4167 [0.3095, 0.5238] | 0.5833 [0.4762, 0.6905] |
| list_index | 0.5238 [0.4167, 0.6310] | 0.8274 [0.7500, 0.9048] |
| list_priority | 0.5833 [0.4762, 0.6905] | 0.9286 [0.8690, 0.9762] |
| list_topic | 0.8333 [0.7500, 0.9048] | 1.0000 [1.0000, 1.0000] |
| prose_paren | 0.4286 [0.3214, 0.5357] | 0.5119 [0.4048, 0.6190] |
| prose_quote | 0.5119 [0.4048, 0.6190] | 0.7024 [0.5952, 0.7976] |
| prose_sentence | 0.4881 [0.3810, 0.5952] | 0.8452 [0.7619, 0.9167] |
| prose_sentiment | 0.8333 [0.7500, 0.9048] | 0.8929 [0.8214, 0.9524] |
| prose_topic | 1.0000 [1.0000, 1.0000] | 0.9643 [0.9167, 1.0000] |
| python_argument | 0.6071 [0.5000, 0.7143] | 0.8036 [0.7202, 0.8810] |
| python_comment | 0.6429 [0.5357, 0.7381] | 0.9524 [0.9048, 0.9881] |
| python_depth | 0.4405 [0.3333, 0.5476] | 0.5357 [0.4286, 0.6429] |
| python_error | 0.5000 [0.3929, 0.6071] | 0.5952 [0.4881, 0.7024] |
| python_indent | 0.3810 [0.2857, 0.4881] | 0.5476 [0.4405, 0.6548] |
| python_string | 0.5119 [0.4048, 0.6190] | 0.5119 [0.4048, 0.6190] |
| table_column | 0.5119 [0.4048, 0.6190] | 0.5000 [0.3929, 0.6071] |
| table_role | 0.5476 [0.4405, 0.6548] | 0.6190 [0.5119, 0.7262] |
| table_row | 0.5238 [0.4167, 0.6310] | 0.6310 [0.5238, 0.7262] |
| table_status | 0.5833 [0.4762, 0.6786] | 0.4881 [0.3869, 0.5952] |

Secondary median contrasts (registered threshold ≥0.15): {'content_minus_structure_describe_medians': 0.0714285714285714, 'structure_median_exhibit_minus_describe': 0.02380952380952378}.

Rows meeting the describe≥0.80 / Oracle≤0.60 falsifier pattern: []. The registration gives no minimum row count; no count threshold has been added.

Dev-probe and available whitened secondaries, exact ties and bootstrap details are in metrics.json. Probe standardization and fitting use only dev reconstructions; every item/template cluster stays in its frozen split.
