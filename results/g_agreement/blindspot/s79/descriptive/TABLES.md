# §79 — DESCRIPTIVE summaries of sealed natural-text results

No new scores, probe fits, selection, sign changes, bootstrap or decision rules. Original H1 and H2 remain NOT MET. Means below weight each feature equally; thresholds of the same family remain separate frozen features. Natural text means the frozen mixed prose/Python/LaTeX/Markdown corpus, not prose alone.

## 1. Class counts and means

Passing means the original native-site probe AUROC ≥0.85 and mismatched AUROC ≤0.60, exactly the sealed `evaluable` flag. All 95 retained features have probe estimates at both sites. Oracle and NLA use different native-site probes.

All retained features (including those failing gates; no new CI for descriptive class means):

| Class | Features | Oracle pass | NLA pass | Probe44 mean | Oracle44 mean | Probe42 mean | NLA42 mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| count-like | 46 | 13 | 14 | 0.7542 | 0.5100 | 0.7476 | 0.5465 |
| state-like | 16 | 12 | 12 | 0.8807 | 0.5235 | 0.8810 | 0.5708 |
| semantic | 33 | 4 | 4 | 0.6558 | 0.5079 | 0.6613 | 0.5033 |

Original reader-specific gate-passing cohorts (denominators can differ between readers):

| Class | Oracle n | Probe44 mean | Oracle44 mean | Gap44 mean | NLA n | Probe42 mean | NLA42 mean | Gap42 mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| count-like | 13 | 0.9434 | 0.5161 | 0.4273 | 14 | 0.9383 | 0.5905 | 0.3477 |
| state-like | 12 | 0.9285 | 0.5408 | 0.3877 | 12 | 0.9381 | 0.5681 | 0.3700 |
| semantic | 4 | 0.9769 | 0.5124 | 0.4645 | 4 | 0.9750 | 0.4587 | 0.5162 |

## 2. Exact committed top 10, original order

AUROC [95% CI] copied from sealed results. Selection uses Oracle eligibility; NLA rows are reported regardless of their eligibility.

| Feature | Probe44 | Oracle44 | Probe42 | NLA42 | NLA passes |
|---|---|---|---|---|---|
| wordlist_preposition | 0.9713 [0.9540, 0.9863] | 0.4305 [0.3692, 0.4932] | 0.9643 [0.9447, 0.9823] | 0.4878 [0.4236, 0.5572] | yes |
| word_allcaps | 0.9814 [0.9684, 0.9922] | 0.4703 [0.4059, 0.5355] | 0.9714 [0.9520, 0.9873] | 0.6708 [0.6024, 0.7351] | yes |
| current_colon | 0.9907 [0.9797, 0.9985] | 0.4893 [0.4196, 0.5549] | 0.9894 [0.9796, 0.9970] | 0.6731 [0.6113, 0.7371] | yes |
| number_magnitude_ge_1000 | 0.9793 [0.9623, 0.9924] | 0.4993 [0.4326, 0.5690] | 0.9830 [0.9675, 0.9946] | 0.6214 [0.5567, 0.6861] | yes |
| number_digits_ge_3 | 0.9661 [0.9445, 0.9844] | 0.4978 [0.4303, 0.5638] | 0.9748 [0.9574, 0.9889] | 0.6227 [0.5558, 0.6854] | yes |
| current_number | 0.9674 [0.9447, 0.9854] | 0.5023 [0.4386, 0.5707] | 0.9591 [0.9348, 0.9794] | 0.4040 [0.3363, 0.4742] | yes |
| number_digits_ge_4 | 0.9717 [0.9540, 0.9860] | 0.5199 [0.4479, 0.5859] | 0.9763 [0.9605, 0.9897] | 0.6655 [0.6034, 0.7234] | yes |
| number_magnitude_ge_10 | 0.9602 [0.9398, 0.9773] | 0.5113 [0.4458, 0.5778] | 0.9665 [0.9473, 0.9828] | 0.5958 [0.5296, 0.6605] | yes |
| number_magnitude_ge_100 | 0.9776 [0.9597, 0.9910] | 0.5308 [0.4629, 0.5962] | 0.9781 [0.9597, 0.9917] | 0.6643 [0.6036, 0.7259] | yes |
| wordlist_auxiliary | 0.9784 [0.9601, 0.9925] | 0.5361 [0.4707, 0.6015] | 0.9731 [0.9544, 0.9884] | 0.3874 [0.3210, 0.4545] | no |

## 3. W1-like structures on natural text

Named families are enumerated explicitly below; every retained feature in them is included. This is descriptive grouping by frozen definition, not a new endpoint or a natural-versus-W1 statistical comparison. Gap = native-site probe AUROC − reader AUROC.

| Group | Retained | Oracle pass | NLA pass | All-feature gap44 | All-feature gap42 | Passing-only gap44 | Passing-only gap42 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bracket depth | 4 | 2 | 4 | 0.4695 | 0.3107 | 0.4439 | 0.3107 |
| table column | 4 | 1 | 1 | 0.3520 | 0.3085 | 0.4300 | 0.3275 |
| line index | 4 | 0 | 0 | 0.1933 | 0.1836 | — | — |
| quote state | 3 | 1 | 1 | 0.1414 | 0.0549 | 0.3651 | 0.1720 |

Bracket-depth features show large positive probe-minus-reader gaps; NLA’s mean gap is smaller here. Line-index rows have no gate-passing feature at either site, so their smaller raw gaps do not supply eligible evidence. Quote-state means across all retained features differ substantially from the one passing feature. These are descriptive observations only.

### bracket depth

Families: paren_depth, square_depth, brace_depth, bracket_depth. Pre-capture drops: brace_depth_ge_3, brace_depth_ge_4, bracket_depth_ge_4, bracket_depth_ge_6, paren_depth_ge_3, paren_depth_ge_4, square_depth_ge_2, square_depth_ge_3.

| Feature | Probe44 | Oracle44 | Gap44 [95%] | O gate | Probe42 | NLA42 | Gap42 [95%] | N gate |
|---|---:|---:|---|---|---:|---:|---|---|
| brace_depth_ge_2 | 0.9168 | 0.4973 | 0.4195 [0.3375, 0.5019] | pass | 0.9043 | 0.4786 | 0.4257 [0.3410, 0.5135] | pass |
| bracket_depth_ge_2 | 0.8597 | 0.3929 | 0.4668 [0.3820, 0.5448] | NOT EVALUABLE_MISMATCH_GATE | 0.8633 | 0.5792 | 0.2841 [0.2081, 0.3596] | pass |
| bracket_depth_ge_3 | 0.9470 | 0.4788 | 0.4682 [0.3935, 0.5411] | pass | 0.9303 | 0.6000 | 0.3303 [0.2621, 0.4025] | pass |
| paren_depth_ge_2 | 0.9083 | 0.3849 | 0.5234 [0.4352, 0.6033] | NOT EVALUABLE_MISMATCH_GATE | 0.8931 | 0.6905 | 0.2026 [0.1330, 0.2742] | pass |

### table column

Families: table_column. Pre-capture drops: none.

| Feature | Probe44 | Oracle44 | Gap44 [95%] | O gate | Probe42 | NLA42 | Gap42 [95%] | N gate |
|---|---:|---:|---|---|---:|---:|---|---|
| table_column_ge_2 | 0.9295 | 0.4996 | 0.4300 [0.3554, 0.5035] | pass | 0.9192 | 0.5917 | 0.3275 [0.2590, 0.3967] | pass |
| table_column_ge_3 | 0.8472 | 0.5813 | 0.2658 [0.1959, 0.3389] | NOT DECODABLE | 0.8495 | 0.5514 | 0.2981 [0.2246, 0.3746] | NOT DECODABLE |
| table_column_ge_4 | 0.8227 | 0.4604 | 0.3623 [0.2764, 0.4470] | NOT DECODABLE | 0.7707 | 0.5667 | 0.2039 [0.1209, 0.2911] | NOT DECODABLE |
| table_column_ge_5 | 0.8359 | 0.4860 | 0.3499 [0.2689, 0.4245] | NOT DECODABLE | 0.8394 | 0.4352 | 0.4043 [0.3209, 0.4819] | NOT DECODABLE |

### line index

Families: line_index. Pre-capture drops: line_index_ge_32.

| Feature | Probe44 | Oracle44 | Gap44 [95%] | O gate | Probe42 | NLA42 | Gap42 [95%] | N gate |
|---|---:|---:|---|---|---:|---:|---|---|
| line_index_ge_16 | 0.5515 | 0.4567 | 0.0948 [-0.0098, 0.1965] | NOT DECODABLE | 0.5933 | 0.4615 | 0.1318 [0.0298, 0.2315] | NOT DECODABLE |
| line_index_ge_2 | 0.6941 | 0.3984 | 0.2958 [0.2056, 0.3851] | NOT DECODABLE | 0.6968 | 0.4428 | 0.2540 [0.1528, 0.3495] | NOT DECODABLE |
| line_index_ge_4 | 0.6970 | 0.4079 | 0.2891 [0.1929, 0.3809] | NOT DECODABLE | 0.6985 | 0.5136 | 0.1849 [0.0857, 0.2776] | NOT DECODABLE |
| line_index_ge_8 | 0.5959 | 0.5022 | 0.0937 [0.0033, 0.1816] | NOT DECODABLE | 0.6123 | 0.4484 | 0.1638 [0.0718, 0.2524] | NOT DECODABLE |

### quote state

Families: inside_string, inside_single_quote, inside_double_quote, inside_triple_quote. Pre-capture drops: inside_triple_quote.

| Feature | Probe44 | Oracle44 | Gap44 [95%] | O gate | Probe42 | NLA42 | Gap42 [95%] | N gate |
|---|---:|---:|---|---|---:|---:|---|---|
| inside_double_quote | 0.8852 | 0.5201 | 0.3651 [0.2902, 0.4420] | pass | 0.8834 | 0.7114 | 0.1720 [0.1010, 0.2466] | pass |
| inside_single_quote | 0.5476 | 0.5494 | -0.0019 [-0.0952, 0.0952] | NOT DECODABLE | 0.5707 | 0.5537 | 0.0170 [-0.0671, 0.0982] | NOT DECODABLE |
| inside_string | 0.5752 | 0.5143 | 0.0610 [-0.0219, 0.1483] | NOT DECODABLE | 0.5770 | 0.6014 | -0.0244 [-0.1249, 0.0883] | NOT DECODABLE |

No sign is flipped. Matched opposite-value mismatched rows are a permutation of the same native requests, not an independent validation set. No new inferential verdict is assigned.
