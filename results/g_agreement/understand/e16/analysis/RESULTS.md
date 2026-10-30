**Prediction (§106):** Dev-selected Oracle structure median ≤0.65; base Qwen text-only AUROC ≥0.90 on most structure rows.

**Assessment:** The prediction held on the registered point-estimate pattern. Oracle structure median: 0.6162; base rows ≥0.90: 9/16. Row-level uncertainty is reported below; no test-set wording selection or new exclusion rule.

This holds as the registered majority/median pattern, not as a uniform result: base Qwen reaches ≥0.90 on 9/16 structure rows. Its structure median is 0.9510, versus 0.8180 for NLA and 0.6162 for the Oracle lens. Base scores are below chance on `python_argument` (0.1706, 95% CI [0.0363, 0.3220]) and `python_depth` (0.2098 [0.0629, 0.3594]); those rows remain unflipped and no wording is reselected on test. All row estimates, paired differences and CIs are retained.

EXPLORATORY. Each row/reader chooses its best phrasing using dev AUROC only; exact ties use the lowest frozen index. Only that choice is scored on test. CIs condition on the frozen dev choice. Base Qwen uses E12’s source wrapper with no native reader instruction, placeholder or activation, and the Oracle adapter disabled for every base forward. The six original E5 rows are verbatim; the other19 use the same eight formats with existing frozen W1 descriptions. Q1 free readouts have a separate full480-record seal and no coding here.

| Row | Class | Reader | Dev-selected wording | Test AUROC [95% CI] | Base−reader [paired95% CI] |
|---|---|---|---|---|---|
| json_status | semantic | olens | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| json_status | semantic | nla | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| json_status | semantic | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| json_type | state-like | olens | direct_question | 0.8345 [0.7868, 0.9547] | 0.1655 [0.0453, 0.2132] |
| json_type | state-like | nla | reader_native | 0.9195 [0.8600, 0.9711] | 0.0805 [0.0289, 0.1400] |
| json_type | state-like | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| latex_environment | state-like | olens | statement | 0.5947 [0.5147, 0.7500] | 0.4053 [0.2500, 0.4853] |
| latex_environment | state-like | nla | paraphrase2 | 0.7052 [0.5193, 0.9734] | 0.2948 [0.0266, 0.4807] |
| latex_environment | state-like | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| latex_role | semantic | olens | plain_value2 | 0.8571 [0.7534, 1.0000] | 0.1429 [0.0000, 0.2466] |
| latex_role | semantic | nla | direct_question | 0.9405 [0.8356, 1.0000] | 0.0595 [0.0000, 0.1644] |
| latex_role | semantic | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| latex_section | count-like | olens | reader_native | 0.5096 [0.3685, 0.6536] | 0.2438 [0.0590, 0.4966] |
| latex_section | count-like | nla | plain_value1 | 0.9461 [0.9098, 0.9887] | -0.1927 [-0.2851, -0.0300] |
| latex_section | count-like | base | direct_question | 0.7534 [0.6932, 0.9263] | — |
| latex_subject | semantic | olens | reader_native | 0.9796 [0.9184, 1.0000] | 0.0204 [0.0000, 0.0816] |
| latex_subject | semantic | nla | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| latex_subject | semantic | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| list_depth | count-like | olens | paraphrase1 | 0.4853 [0.2630, 0.6579] | 0.5091 [0.3281, 0.7370] |
| list_depth | count-like | nla | which_more_likely | 0.6054 [0.4660, 0.7625] | 0.3889 [0.2290, 0.5296] |
| list_depth | count-like | base | statement | 0.9943 [0.9785, 1.0000] | — |
| list_index | count-like | olens | plain_value2 | 0.5380 [0.4216, 0.6650] | 0.2103 [-0.0550, 0.4002] |
| list_index | count-like | nla | paraphrase1 | 0.7302 [0.5691, 0.9382] | 0.0181 [-0.1667, 0.2517] |
| list_index | count-like | base | statement | 0.7483 [0.5380, 0.9337] | — |
| list_priority | semantic | olens | plain_value2 | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| list_priority | semantic | nla | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| list_priority | semantic | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| list_topic | semantic | olens | statement | 0.9994 [0.9977, 1.0000] | 0.0006 [0.0000, 0.0023] |
| list_topic | semantic | nla | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| list_topic | semantic | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| prose_paren | state-like | olens | direct_question | 0.5703 [0.3112, 0.7988] | 0.4297 [0.2012, 0.6888] |
| prose_paren | state-like | nla | plain_value2 | 0.8985 [0.7347, 1.0000] | 0.1015 [0.0000, 0.2653] |
| prose_paren | state-like | base | statement | 1.0000 [1.0000, 1.0000] | — |
| prose_quote | state-like | olens | paraphrase1 | 0.5068 [0.1939, 0.8424] | 0.3594 [-0.1105, 0.8005] |
| prose_quote | state-like | nla | plain_value1 | 0.7188 [0.5204, 0.9660] | 0.1474 [-0.0884, 0.4099] |
| prose_quote | state-like | base | statement | 0.8662 [0.6480, 1.0000] | — |
| prose_sentence | count-like | olens | plain_value2 | 0.5612 [0.4467, 0.7302] | 0.2540 [-0.1190, 0.5147] |
| prose_sentence | count-like | nla | direct_question | 0.9989 [0.9966, 1.0000] | -0.1837 [-0.3760, -0.0023] |
| prose_sentence | count-like | base | direct_question | 0.8152 [0.6234, 0.9960] | — |
| prose_sentiment | semantic | olens | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| prose_sentiment | semantic | nla | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| prose_sentiment | semantic | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| prose_topic | semantic | olens | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| prose_topic | semantic | nla | direct_question | 0.9972 [0.9887, 1.0000] | 0.0028 [0.0000, 0.0113] |
| prose_topic | semantic | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| python_argument | count-like | olens | direct_question | 0.6859 [0.5833, 0.8103] | -0.5153 [-0.6735, -0.3713] |
| python_argument | count-like | nla | which_more_likely | 0.8356 [0.7381, 0.9388] | -0.6650 [-0.8112, -0.5459] |
| python_argument | count-like | base | statement | 0.1706 [0.0363, 0.3220] | — |
| python_comment | state-like | olens | plain_value1 | 0.7007 [0.6032, 0.7766] | 0.2993 [0.2234, 0.3968] |
| python_comment | state-like | nla | which_more_likely | 0.7228 [0.6088, 0.8277] | 0.2772 [0.1723, 0.3912] |
| python_comment | state-like | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| python_depth | count-like | olens | paraphrase1 | 0.7840 [0.7693, 0.8220] | -0.5743 [-0.7483, -0.4303] |
| python_depth | count-like | nla | paraphrase1 | 0.7268 [0.6531, 0.8345] | -0.5170 [-0.7347, -0.3260] |
| python_depth | count-like | base | direct_question | 0.2098 [0.0629, 0.3594] | — |
| python_error | semantic | olens | statement | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| python_error | semantic | nla | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| python_error | semantic | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| python_indent | count-like | olens | reader_native | 0.6621 [0.4019, 0.9161] | 0.3379 [0.0839, 0.5981] |
| python_indent | count-like | nla | statement | 0.8005 [0.4955, 0.9745] | 0.1995 [0.0255, 0.5045] |
| python_indent | count-like | base | statement | 1.0000 [1.0000, 1.0000] | — |
| python_string | state-like | olens | plain_value1 | 0.6378 [0.5317, 0.7489] | 0.3622 [0.2511, 0.4683] |
| python_string | state-like | nla | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| python_string | state-like | base | direct_question | 1.0000 [1.0000, 1.0000] | — |
| table_column | count-like | olens | paraphrase1 | 0.7069 [0.5244, 0.8957] | 0.2007 [-0.0448, 0.4053] |
| table_column | count-like | nla | statement | 0.5539 [0.3793, 0.7511] | 0.3537 [0.0765, 0.5720] |
| table_column | count-like | base | statement | 0.9076 [0.7330, 1.0000] | — |
| table_role | state-like | olens | reader_native | 0.4898 [0.3498, 0.6770] | 0.5102 [0.3230, 0.6502] |
| table_role | state-like | nla | which_more_likely | 0.9921 [0.9841, 1.0000] | 0.0079 [0.0000, 0.0159] |
| table_role | state-like | base | statement | 1.0000 [1.0000, 1.0000] | — |
| table_row | count-like | olens | direct_question | 0.8549 [0.7596, 0.9388] | -0.0017 [-0.1224, 0.1526] |
| table_row | count-like | nla | reader_native | 0.9773 [0.9478, 1.0000] | -0.1241 [-0.2029, -0.0402] |
| table_row | count-like | base | statement | 0.8532 [0.7755, 0.9490] | — |
| table_status | semantic | olens | direct_question | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| table_status | semantic | nla | which_more_likely | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| table_status | semantic | base | direct_question | 1.0000 [1.0000, 1.0000] | — |

| Class | Reader | Rows | Median test AUROC |
|---|---|---:|---:|
| count-like | olens | 9 | 0.6621 |
| state-like | olens | 7 | 0.5947 |
| semantic | olens | 9 | 1.0000 |
| structure | olens | 16 | 0.6162 |
| count-like | nla | 9 | 0.8005 |
| state-like | nla | 7 | 0.8985 |
| semantic | nla | 9 | 1.0000 |
| structure | nla | 16 | 0.8180 |
| count-like | base | 9 | 0.8152 |
| state-like | base | 7 | 1.0000 |
| semantic | base | 9 | 1.0000 |
| structure | base | 16 | 0.9510 |
