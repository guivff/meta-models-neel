# E37 results

Registered prediction (§134): R1, R2 and R4 hold; R3 is descriptive.

Checkpoint branch: lora_hf_UNVERIFIED.
README identity claim: UNVERIFIED; see sealed CPU tensor receipt for differences or download failure.

- R1: not met.
- R2: not met.
- R4: met.

All paired differences are SFT minus RL; R3 explicitly reverses the sign to report RL minus SFT.
C1′ and C2 opposite-donor results are descriptive. Semantic C4 rows lacking E24 detectors remain not evaluable.

| Row | Channel | Control | RL AUROC | SFT AUROC | SFT−RL | Paired 95% CI |
|---|---|---|---:|---:|---:|---|
| json_status | C1 | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| json_status | C1prime | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| json_type | C1 | matched | 0.6593 | 0.7432 | 0.0839 | [0.0590, 0.1066] |
| json_type | C1prime | matched | 0.4960 | 0.7234 | 0.2273 | [0.1542, 0.3107] |
| latex_environment | C1 | matched | 0.5782 | 0.5522 | -0.0261 | [-0.1429, 0.0170] |
| latex_environment | C1prime | matched | 0.5573 | 0.7001 | 0.1429 | [0.0482, 0.3255] |
| latex_role | C1 | matched | 0.8452 | 0.8237 | -0.0215 | [-0.0987, 0.0000] |
| latex_role | C1prime | matched | 0.9535 | 0.9870 | 0.0334 | [-0.0153, 0.1066] |
| latex_section | C1 | matched | 0.4478 | 0.6032 | 0.1553 | [0.0142, 0.2812] |
| latex_section | C1prime | matched | 0.9337 | 0.9787 | 0.0451 | [0.0000, 0.1525] |
| latex_subject | C1 | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| latex_subject | C1prime | matched | 0.8469 | 1.0000 | 0.1531 | [0.0000, 0.3435] |
| list_depth | C1 | matched | 0.6332 | 0.5726 | -0.0607 | [-0.3418, 0.1077] |
| list_depth | C1prime | matched | 0.6244 | 0.6777 | 0.0533 | [-0.0510, 0.1573] |
| list_depth | C2 | matched | 0.3186 | 0.5329 | 0.2143 | [-0.1395, 0.5986] |
| list_depth | C2 | opposite | 0.6814 | 0.4671 | -0.2143 | [-0.5986, 0.1395] |
| list_index | C1 | matched | 0.4252 | 0.4898 | 0.0646 | [-0.0709, 0.2540] |
| list_index | C1prime | matched | 0.5116 | 0.6984 | 0.1868 | [0.0669, 0.3926] |
| list_priority | C1 | matched | 0.8929 | 1.0000 | 0.1071 | [0.0000, 0.3912] |
| list_priority | C1prime | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| list_topic | C1 | matched | 0.9683 | 0.9926 | 0.0244 | [-0.0136, 0.1122] |
| list_topic | C1prime | matched | 1.0000 | 0.9342 | -0.0658 | [-0.2143, 0.0000] |
| prose_paren | C1 | matched | 0.4745 | 0.4637 | -0.0108 | [-0.0720, 0.0680] |
| prose_paren | C1prime | matched | 0.4677 | 0.5272 | 0.0595 | [-0.0051, 0.2846] |
| prose_paren | C2 | matched | 0.7109 | 0.7449 | 0.0340 | [-0.1825, 0.2540] |
| prose_paren | C2 | opposite | 0.2891 | 0.2551 | -0.0340 | [-0.2540, 0.1825] |
| prose_quote | C1 | matched | 0.5618 | 0.4705 | -0.0913 | [-0.2681, 0.1582] |
| prose_quote | C1prime | matched | 0.5533 | 0.5198 | -0.0334 | [-0.2188, 0.0851] |
| prose_quote | C2 | matched | 0.7971 | 0.8124 | 0.0153 | [-0.1587, 0.1961] |
| prose_quote | C2 | opposite | 0.2029 | 0.1876 | -0.0153 | [-0.1961, 0.1587] |
| prose_sentence | C1 | matched | 0.5238 | 0.5771 | 0.0533 | [-0.1083, 0.1820] |
| prose_sentence | C1prime | matched | 0.7588 | 0.8554 | 0.0967 | [0.0068, 0.2253] |
| prose_sentiment | C1 | matched | 0.9099 | 1.0000 | 0.0901 | [0.0000, 0.3543] |
| prose_sentiment | C1prime | matched | 0.9918 | 1.0000 | 0.0082 | [0.0000, 0.0329] |
| prose_topic | C1 | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| prose_topic | C1prime | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| python_argument | C1 | matched | 0.5068 | 0.6412 | 0.1344 | [0.0822, 0.1990] |
| python_argument | C1prime | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| python_comment | C1 | matched | 0.5425 | 0.5584 | 0.0159 | [-0.0283, 0.0510] |
| python_comment | C1prime | matched | 0.6933 | 0.3112 | -0.3821 | [-0.4598, -0.3112] |
| python_depth | C1 | matched | 0.4932 | 0.5040 | 0.0108 | [-0.0091, 0.0368] |
| python_depth | C1prime | matched | 0.6825 | 0.6159 | -0.0666 | [-0.1038, -0.0275] |
| python_depth | C2 | matched | 0.8192 | 0.7619 | -0.0573 | [-0.0969, -0.0102] |
| python_depth | C2 | opposite | 0.1808 | 0.2381 | 0.0573 | [0.0102, 0.0969] |
| python_error | C1 | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| python_error | C1prime | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| python_indent | C1 | matched | 0.5884 | 0.4371 | -0.1514 | [-0.3798, 0.0000] |
| python_indent | C1prime | matched | 0.5493 | 0.4756 | -0.0737 | [-0.2715, 0.1171] |
| python_indent | C2 | matched | 0.7800 | 0.9989 | 0.2188 | [0.0000, 0.4422] |
| python_indent | C2 | opposite | 0.2200 | 0.0011 | -0.2188 | [-0.4422, 0.0000] |
| python_string | C1 | matched | 0.6417 | 0.7222 | 0.0805 | [-0.0635, 0.2489] |
| python_string | C1prime | matched | 0.5907 | 0.5584 | -0.0323 | [-0.1797, 0.1145] |
| python_string | C2 | matched | 0.9155 | 0.8549 | -0.0607 | [-0.1241, -0.0051] |
| python_string | C2 | opposite | 0.0845 | 0.1451 | 0.0607 | [0.0051, 0.1241] |
| table_column | C1 | matched | 0.4762 | 0.5641 | 0.0879 | [0.0385, 0.1684] |
| table_column | C1prime | matched | 0.8234 | 0.8172 | -0.0062 | [-0.0652, 0.0887] |
| table_role | C1 | matched | 0.4388 | 0.3968 | -0.0420 | [-0.1264, 0.0935] |
| table_role | C1prime | matched | 0.3770 | 0.3747 | -0.0023 | [-0.0692, 0.1032] |
| table_role | C2 | matched | 0.8189 | 0.6828 | -0.1361 | [-0.1780, -0.0771] |
| table_role | C2 | opposite | 0.1811 | 0.3172 | 0.1361 | [0.0771, 0.1780] |
| table_row | C1 | matched | 0.5000 | 0.5351 | 0.0351 | [-0.0578, 0.1156] |
| table_row | C1prime | matched | 0.9722 | 0.9892 | 0.0170 | [0.0000, 0.0420] |
| table_status | C1 | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| table_status | C1prime | matched | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |

C4 pooled and per-row Wilson summaries, paired cluster differences, and the frozen R4 interpretation are retained in metrics.json.
