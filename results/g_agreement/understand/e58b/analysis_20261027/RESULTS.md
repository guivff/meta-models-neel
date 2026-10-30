# E58b — registered J-space ablation

R-b1: HOLDS (2/3 controls).

R-b2: DOES NOT HOLD (15/25 rows).

| Bank/row | None log-odds | J damage | Random mean damage (5 seeds) | J/random | PCA damage |
|---|---:|---:|---:|---:|---:|
| W1/list_depth | 1.140938 | 0.122880 | -0.049177 | -2.498723 | -0.192818 |
| W1/prose_paren | 3.893039 | -0.571121 | -0.230483 | 2.477933 | 0.999116 |
| W1/prose_quote | 3.792289 | -0.067363 | -0.037267 | 1.807586 | 0.849661 |
| W1/python_depth | 3.669476 | 0.000974 | -0.090560 | -0.010756 | 0.873267 |
| W1/python_indent | 5.564853 | -0.062445 | -0.079441 | 0.786061 | 0.806803 |
| W1/python_string | 4.420231 | -0.301523 | -0.075935 | 3.970800 | 2.255530 |
| W1/table_column | 0.343086 | 0.012847 | 0.002364 | 5.434344 | -0.067371 |
| W1/table_role | 3.873149 | -0.202592 | 0.086665 | -2.337640 | 1.107316 |
| E36/list_depth | 1.419350 | 0.068480 | 0.049208 | 1.391646 | 0.394522 |
| E36/prose_paren | 3.435911 | -0.421731 | -0.091691 | 4.599490 | 1.464893 |
| E36/prose_quote | 4.560956 | 0.341622 | 0.128135 | 2.666110 | 2.485663 |
| E36/python_depth | 2.673648 | -0.196194 | 0.005897 | -33.271122 | 1.662555 |
| E36/python_indent | 3.986168 | -0.287573 | 0.140781 | -2.042702 | 1.799691 |
| E36/python_string | 1.501235 | -0.275910 | 0.048996 | -5.631248 | 1.876058 |
| E36/table_column | 0.256808 | -0.448550 | 0.124015 | -3.616891 | -0.274058 |
| E36/table_role | 0.091328 | -0.044655 | 0.005997 | -7.446296 | 0.103343 |
| E49/arith_compare | 0.830357 | -0.095238 | -0.048512 | 1.963189 | -0.096354 |
| E49/container_after_move | 1.840774 | -1.011161 | 0.359524 | -2.812500 | 0.883929 |
| E49/holder_after_handovers | 0.385796 | -0.238504 | -0.031892 | 7.478419 | -0.137686 |
| E49/negation_scope | 0.399977 | -0.348442 | -0.159240 | 2.188152 | -0.728308 |
| E49/next_paragraph_language | 1.093378 | 0.230655 | 0.193229 | 1.193685 | 1.154157 |
| E49/topic_twin | 2.841146 | 0.045759 | -0.036161 | -1.265431 | 1.192522 |
| E49/unit_system | 3.302827 | 0.276042 | -0.071726 | -3.848547 | -1.199405 |
| E49/user_expertise | 4.290310 | 0.322487 | 0.050817 | 6.345985 | 0.015267 |
| E56/adjective_implicit | 5.165551 | 0.353144 | 0.043769 | 8.068420 | 3.074793 |
| E56/fact_recall (shallow content, descriptive) | 7.438616 | 0.338914 | 0.383631 | 0.883437 | 5.496466 |
| E56/language_continuation | 4.984003 | -0.354167 | -0.025521 | 13.877554 | 2.680199 |
| E56/rhyme_plan | 5.977307 | 1.679687 | -0.189211 | -8.877310 | -0.665923 |
| E56/tense_implicit | 2.210565 | 0.206845 | 0.084077 | 2.460177 | 1.677455 |
| E57/antonym_crosslingual | 5.656198 | 0.160579 | 0.301794 | 0.532082 | 3.150827 |
| E57/clause_pending | 1.697852 | -0.295481 | 0.172907 | -1.708908 | 1.820166 |
| E57/indent_level | 2.936901 | -0.050177 | -0.066652 | 0.752811 | -0.415933 |
| E57/nesting_depth | 0.697365 | 0.176797 | -0.012620 | -14.008960 | -0.083461 |
| E57/sentiment_judgement (shallow content, descriptive) | 2.771577 | 0.802083 | 0.010268 | 78.115719 | 2.487537 |
| E57/subject_number | 5.471354 | -0.589286 | -0.044345 | 13.288586 | 0.668155 |
| E57/two_hop_answer | 1.921131 | 0.241071 | 0.091964 | 2.621359 | 0.151042 |
| E57/page_range_digit | 1.656994 | -0.272321 | 0.103571 | -2.629311 | 1.557292 |

Signed mean drops are used without clipping. Rows with PCA damage below random remain included and are listed in RESULTS.json. Each random seed is also reported there.

## E57 paired-prompt swap controls (descriptive)

| Row | Swapped none | Swapped J | Swapped PCA |
|---|---:|---:|---:|
| E57/antonym_crosslingual | -5.656198 | -5.495619 | -2.505370 |
| E57/clause_pending | -1.697852 | -1.993333 | 0.122314 |
| E57/indent_level | -2.936901 | -2.987077 | -3.352834 |
| E57/nesting_depth | -0.697365 | -0.520568 | -0.780827 |
| E57/sentiment_judgement | -2.771577 | -1.969494 | -0.284040 |
| E57/subject_number | -5.471354 | -6.060640 | -4.803199 |
| E57/two_hop_answer | -1.921131 | -1.680060 | -1.770089 |
| E57/page_range_digit | -1.656994 | -1.929315 | -0.099702 |

Swap scores reuse the frozen opposite-state paired prompt with the same candidate pair and shared basis; no extra GPU forwards or primary-rule inputs.
