**Prediction (§94):** Structure answers follow the swapped donor, meaning answers follow the recipient, and Δ probes read structure better than meaning.

**Assessment: the prediction partly held.** Meaning swap scores generally follow the recipient (descriptive semantic median recipient AUROC 0.8333). State-like swap scores show donor following on some rows (median donor AUROC 0.6692), but count-like scores do not show the predicted general donor following (median 0.4874). Δ is probe-readable across all classes: median AUROC 0.9416 for count-like, 0.9841 for state-like and 0.9274 for semantic rows, so it is not selectively readable for structure. The full structure-versus-meaning prediction did not hold. No confirmatory threshold or new exclusion rule is added.

EXPLORATORY, native block42. All25 rows, all6 arms, original signed score orientation and the registered2,000 template-cluster resamples (seed20261024) are retained. Δ probes use the frozen grouped5-fold procedure;40 directed pairs per row,84 test activations per row for probes. Donor/recipient AUROCs are complementary under opposite-value pairs and are not independent confirmations.

Class medians below are DESCRIPTIVE summaries of the registered per-row estimates; no class-level CI or new test is introduced.

| Class | Rows | Δ probe AUROC | Swap donor AUROC | Swap recipient AUROC | OL-only recipient AUROC |
|---|---:|---:|---:|---:|---:|
| count-like | 9 | 0.9416 | 0.4874 | 0.5126 | 0.6175 |
| state-like | 7 | 0.9841 | 0.6692 | 0.3308 | 0.6086 |
| semantic | 9 | 0.9274 | 0.1667 | 0.8333 | 0.9722 |

| Row | Class | Δ probe AUROC [95% CI] |
|---|---|---|
| json_status | semantic | 1.0000 [1.0000, 1.0000] |
| json_type | state-like | 1.0000 [1.0000, 1.0000] |
| latex_environment | state-like | 0.5641 [0.4671, 0.6735] |
| latex_role | semantic | 0.9274 [0.7817, 1.0000] |
| latex_section | count-like | 0.9456 [0.9087, 0.9841] |
| latex_subject | semantic | 0.7868 [0.5675, 0.9773] |
| list_depth | count-like | 0.7358 [0.6842, 0.8821] |
| list_index | count-like | 0.7959 [0.7608, 0.8742] |
| list_priority | semantic | 0.9048 [0.5833, 1.0000] |
| list_topic | semantic | 0.9892 [0.9756, 1.0000] |
| prose_paren | state-like | 0.6678 [0.4768, 0.7988] |
| prose_quote | state-like | 0.5975 [0.4654, 0.7761] |
| prose_sentence | count-like | 0.9416 [0.8447, 0.9972] |
| prose_sentiment | semantic | 0.7676 [0.5601, 0.9405] |
| prose_topic | semantic | 0.8163 [0.6286, 0.9677] |
| python_argument | count-like | 1.0000 [1.0000, 1.0000] |
| python_comment | state-like | 0.9949 [0.9864, 1.0000] |
| python_depth | count-like | 0.8118 [0.7613, 0.8872] |
| python_error | semantic | 1.0000 [1.0000, 1.0000] |
| python_indent | count-like | 0.8673 [0.7273, 0.9847] |
| python_string | state-like | 1.0000 [1.0000, 1.0000] |
| table_column | count-like | 0.9989 [0.9966, 1.0000] |
| table_role | state-like | 0.9841 [0.9677, 1.0000] |
| table_row | count-like | 0.9966 [0.9887, 1.0000] |
| table_status | semantic | 1.0000 [1.0000, 1.0000] |

All registered arm estimates:

| Row | Arm | Recipient AUROC [95% CI] | Donor AUROC [95% CI] |
|---|---|---|---|
| json_status | swap | 0.4655 [0.2355, 0.7667] | 0.5345 [0.2333, 0.7645] |
| json_status | self | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| json_status | ol_only | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| json_status | nla_only | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| json_status | delta_only | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| json_status | random | 0.7826 [0.6176, 0.8901] | 0.2174 [0.1099, 0.3824] |
| json_type | swap | 0.1869 [0.0606, 0.3932] | 0.8131 [0.6068, 0.9394] |
| json_type | self | 0.7323 [0.5671, 0.9394] | 0.2677 [0.0606, 0.4329] |
| json_type | ol_only | 0.6086 [0.4464, 0.8294] | 0.3914 [0.1706, 0.5536] |
| json_type | nla_only | 0.7323 [0.5671, 0.9394] | 0.2677 [0.0606, 0.4329] |
| json_type | delta_only | 0.5909 [0.4006, 0.7809] | 0.4091 [0.2191, 0.5994] |
| json_type | random | 0.3434 [0.1808, 0.6230] | 0.6566 [0.3770, 0.8192] |
| latex_environment | swap | 0.5840 [0.3988, 0.8224] | 0.4160 [0.1776, 0.6012] |
| latex_environment | self | 0.4937 [0.2272, 0.7883] | 0.5063 [0.2117, 0.7728] |
| latex_environment | ol_only | 0.5414 [0.4095, 0.7527] | 0.4586 [0.2473, 0.5905] |
| latex_environment | nla_only | 0.4937 [0.2272, 0.7883] | 0.5063 [0.2117, 0.7728] |
| latex_environment | delta_only | 0.5890 [0.3182, 0.8375] | 0.4110 [0.1625, 0.6818] |
| latex_environment | random | 0.5038 [0.3428, 0.6110] | 0.4962 [0.3890, 0.6572] |
| latex_role | swap | 0.8333 [0.6800, 0.9600] | 0.1667 [0.0400, 0.3200] |
| latex_role | self | 0.9672 [0.9333, 1.0000] | 0.0328 [0.0000, 0.0667] |
| latex_role | ol_only | 0.9722 [0.9091, 1.0000] | 0.0278 [0.0000, 0.0909] |
| latex_role | nla_only | 0.9672 [0.9333, 1.0000] | 0.0328 [0.0000, 0.0667] |
| latex_role | delta_only | 0.6843 [0.3421, 0.8661] | 0.3157 [0.1339, 0.6579] |
| latex_role | random | 0.7879 [0.5952, 0.9183] | 0.2121 [0.0817, 0.4048] |
| latex_section | swap | 0.5126 [0.2335, 0.7971] | 0.4874 [0.2029, 0.7665] |
| latex_section | self | 0.3763 [0.1900, 0.5596] | 0.6237 [0.4404, 0.8100] |
| latex_section | ol_only | 0.4621 [0.2303, 0.7305] | 0.5379 [0.2695, 0.7697] |
| latex_section | nla_only | 0.3763 [0.1900, 0.5596] | 0.6237 [0.4404, 0.8100] |
| latex_section | delta_only | 0.5808 [0.4075, 0.7871] | 0.4192 [0.2129, 0.5925] |
| latex_section | random | 0.6010 [0.4503, 0.7200] | 0.3990 [0.2800, 0.5497] |
| latex_subject | swap | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| latex_subject | self | 0.9621 [0.8535, 1.0000] | 0.0379 [0.0000, 0.1465] |
| latex_subject | ol_only | 0.9773 [0.8517, 1.0000] | 0.0227 [0.0000, 0.1483] |
| latex_subject | nla_only | 0.9621 [0.8535, 1.0000] | 0.0379 [0.0000, 0.1465] |
| latex_subject | delta_only | 0.8182 [0.6750, 0.9583] | 0.1818 [0.0417, 0.3250] |
| latex_subject | random | 0.9545 [0.8993, 1.0000] | 0.0455 [0.0000, 0.1007] |
| list_depth | swap | 0.4175 [0.3078, 0.6946] | 0.5825 [0.3054, 0.6922] |
| list_depth | self | 0.5725 [0.3173, 0.8636] | 0.4275 [0.1364, 0.6827] |
| list_depth | ol_only | 0.6175 [0.5175, 0.7941] | 0.3825 [0.2059, 0.4825] |
| list_depth | nla_only | 0.5725 [0.3173, 0.8636] | 0.4275 [0.1364, 0.6827] |
| list_depth | delta_only | 0.7175 [0.4708, 0.8500] | 0.2825 [0.1500, 0.5292] |
| list_depth | random | 0.6000 [0.3519, 0.8464] | 0.4000 [0.1536, 0.6481] |
| list_index | swap | 0.4899 [0.1789, 0.8301] | 0.5101 [0.1699, 0.8211] |
| list_index | self | 0.6490 [0.4701, 0.8621] | 0.3510 [0.1379, 0.5299] |
| list_index | ol_only | 0.6111 [0.4134, 0.7949] | 0.3889 [0.2051, 0.5866] |
| list_index | nla_only | 0.6490 [0.4701, 0.8621] | 0.3510 [0.1379, 0.5299] |
| list_index | delta_only | 0.6288 [0.3920, 0.8984] | 0.3712 [0.1016, 0.6080] |
| list_index | random | 0.5025 [0.3406, 0.7918] | 0.4975 [0.2082, 0.6594] |
| list_priority | swap | 0.5833 [0.2222, 0.9015] | 0.4167 [0.0985, 0.7778] |
| list_priority | self | 0.9747 [0.9484, 1.0000] | 0.0253 [0.0000, 0.0516] |
| list_priority | ol_only | 0.3157 [0.1143, 0.4487] | 0.6843 [0.5513, 0.8857] |
| list_priority | nla_only | 0.9747 [0.9484, 1.0000] | 0.0253 [0.0000, 0.0516] |
| list_priority | delta_only | 0.4444 [0.2799, 0.7223] | 0.5556 [0.2777, 0.7201] |
| list_priority | random | 0.6742 [0.5767, 0.8427] | 0.3258 [0.1573, 0.4233] |
| list_topic | swap | 0.9040 [0.7747, 0.9914] | 0.0960 [0.0086, 0.2253] |
| list_topic | self | 0.9192 [0.7771, 1.0000] | 0.0808 [0.0000, 0.2229] |
| list_topic | ol_only | 0.6970 [0.5436, 0.8889] | 0.3030 [0.1111, 0.4564] |
| list_topic | nla_only | 0.9192 [0.7771, 1.0000] | 0.0808 [0.0000, 0.2229] |
| list_topic | delta_only | 0.7626 [0.5429, 0.9354] | 0.2374 [0.0646, 0.4571] |
| list_topic | random | 0.9722 [0.9181, 1.0000] | 0.0278 [0.0000, 0.0819] |
| prose_paren | swap | 0.4311 [0.1750, 0.5959] | 0.5689 [0.4041, 0.8250] |
| prose_paren | self | 0.7694 [0.5600, 0.9462] | 0.2306 [0.0538, 0.4400] |
| prose_paren | ol_only | 0.4637 [0.3025, 0.6319] | 0.5363 [0.3681, 0.6975] |
| prose_paren | nla_only | 0.7694 [0.5600, 0.9462] | 0.2306 [0.0538, 0.4400] |
| prose_paren | delta_only | 0.5464 [0.2745, 0.7955] | 0.4536 [0.2045, 0.7255] |
| prose_paren | random | 0.4010 [0.2737, 0.5732] | 0.5990 [0.4268, 0.7263] |
| prose_quote | swap | 0.3207 [0.1667, 0.4339] | 0.6793 [0.5661, 0.8333] |
| prose_quote | self | 0.6970 [0.4868, 0.9263] | 0.3030 [0.0737, 0.5132] |
| prose_quote | ol_only | 0.6768 [0.4454, 0.7904] | 0.3232 [0.2096, 0.5546] |
| prose_quote | nla_only | 0.6970 [0.4868, 0.9263] | 0.3030 [0.0737, 0.5132] |
| prose_quote | delta_only | 0.6843 [0.4697, 0.8034] | 0.3157 [0.1966, 0.5303] |
| prose_quote | random | 0.4192 [0.3333, 0.5945] | 0.5808 [0.4055, 0.6667] |
| prose_sentence | swap | 0.6942 [0.4820, 0.8891] | 0.3058 [0.1109, 0.5180] |
| prose_sentence | self | 0.8195 [0.6444, 0.9556] | 0.1805 [0.0444, 0.3556] |
| prose_sentence | ol_only | 0.7068 [0.5400, 0.8750] | 0.2932 [0.1250, 0.4600] |
| prose_sentence | nla_only | 0.8195 [0.6444, 0.9556] | 0.1805 [0.0444, 0.3556] |
| prose_sentence | delta_only | 0.7719 [0.5477, 0.9281] | 0.2281 [0.0719, 0.4523] |
| prose_sentence | random | 0.7719 [0.5932, 0.9167] | 0.2281 [0.0833, 0.4068] |
| prose_sentiment | swap | 0.9670 [0.8289, 1.0000] | 0.0330 [0.0000, 0.1711] |
| prose_sentiment | self | 0.9725 [0.9177, 1.0000] | 0.0275 [0.0000, 0.0823] |
| prose_sentiment | ol_only | 0.6154 [0.1053, 0.9127] | 0.3846 [0.0873, 0.8947] |
| prose_sentiment | nla_only | 0.9725 [0.9177, 1.0000] | 0.0275 [0.0000, 0.0823] |
| prose_sentiment | delta_only | 0.5962 [0.3704, 0.9192] | 0.4038 [0.0808, 0.6296] |
| prose_sentiment | random | 0.9423 [0.7368, 1.0000] | 0.0577 [0.0000, 0.2632] |
| prose_topic | swap | 0.7500 [0.3589, 0.9740] | 0.2500 [0.0260, 0.6411] |
| prose_topic | self | 0.9621 [0.7857, 1.0000] | 0.0379 [0.0000, 0.2143] |
| prose_topic | ol_only | 0.6338 [0.4464, 0.8980] | 0.3662 [0.1020, 0.5536] |
| prose_topic | nla_only | 0.9621 [0.7857, 1.0000] | 0.0379 [0.0000, 0.2143] |
| prose_topic | delta_only | 0.2146 [0.0973, 0.4019] | 0.7854 [0.5981, 0.9027] |
| prose_topic | random | 0.6414 [0.4643, 0.8135] | 0.3586 [0.1865, 0.5357] |
| python_argument | swap | 0.4236 [0.0902, 0.7480] | 0.5764 [0.2520, 0.9098] |
| python_argument | self | 0.6992 [0.5556, 0.8307] | 0.3008 [0.1693, 0.4444] |
| python_argument | ol_only | 0.5138 [0.2831, 0.7094] | 0.4862 [0.2906, 0.7169] |
| python_argument | nla_only | 0.6992 [0.5556, 0.8307] | 0.3008 [0.1693, 0.4444] |
| python_argument | delta_only | 0.6591 [0.4299, 0.8409] | 0.3409 [0.1591, 0.5701] |
| python_argument | random | 0.4236 [0.2035, 0.6720] | 0.5764 [0.3280, 0.7965] |
| python_comment | swap | 0.3308 [0.1621, 0.5818] | 0.6692 [0.4182, 0.8379] |
| python_comment | self | 0.6641 [0.4341, 0.8647] | 0.3359 [0.1353, 0.5659] |
| python_comment | ol_only | 0.4596 [0.2440, 0.7000] | 0.5404 [0.3000, 0.7560] |
| python_comment | nla_only | 0.6641 [0.4341, 0.8647] | 0.3359 [0.1353, 0.5659] |
| python_comment | delta_only | 0.7399 [0.5504, 0.8715] | 0.2601 [0.1285, 0.4496] |
| python_comment | random | 0.3990 [0.2633, 0.6668] | 0.6010 [0.3332, 0.7367] |
| python_depth | swap | 0.6650 [0.4365, 0.8444] | 0.3350 [0.1556, 0.5635] |
| python_depth | self | 0.5900 [0.4934, 0.7970] | 0.4100 [0.2030, 0.5066] |
| python_depth | ol_only | 0.6300 [0.3889, 0.7599] | 0.3700 [0.2401, 0.6111] |
| python_depth | nla_only | 0.5900 [0.4934, 0.7970] | 0.4100 [0.2030, 0.5066] |
| python_depth | delta_only | 0.5900 [0.4607, 0.7500] | 0.4100 [0.2500, 0.5393] |
| python_depth | random | 0.5800 [0.4415, 0.7292] | 0.4200 [0.2708, 0.5585] |
| python_error | swap | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| python_error | self | 0.9123 [0.8333, 0.9762] | 0.0877 [0.0238, 0.1667] |
| python_error | ol_only | 0.9900 [0.9758, 1.0000] | 0.0100 [0.0000, 0.0242] |
| python_error | nla_only | 0.9123 [0.8333, 0.9762] | 0.0877 [0.0238, 0.1667] |
| python_error | delta_only | 0.7469 [0.5559, 0.9853] | 0.2531 [0.0147, 0.4441] |
| python_error | random | 0.9574 [0.8472, 1.0000] | 0.0426 [0.0000, 0.1528] |
| python_indent | swap | 0.6641 [0.4609, 0.8667] | 0.3359 [0.1333, 0.5391] |
| python_indent | self | 0.6692 [0.3794, 0.8889] | 0.3308 [0.1111, 0.6206] |
| python_indent | ol_only | 0.7222 [0.3901, 0.9481] | 0.2778 [0.0519, 0.6099] |
| python_indent | nla_only | 0.6692 [0.3794, 0.8889] | 0.3308 [0.1111, 0.6206] |
| python_indent | delta_only | 0.4242 [0.2000, 0.7437] | 0.5758 [0.2563, 0.8000] |
| python_indent | random | 0.5253 [0.3287, 0.7886] | 0.4747 [0.2114, 0.6713] |
| python_string | swap | 0.0110 [0.0000, 0.0370] | 0.9890 [0.9630, 1.0000] |
| python_string | self | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| python_string | ol_only | 0.7088 [0.5016, 0.9778] | 0.2912 [0.0222, 0.4984] |
| python_string | nla_only | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| python_string | delta_only | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| python_string | random | 0.4808 [0.3750, 0.7194] | 0.5192 [0.2806, 0.6250] |
| table_column | swap | 0.6136 [0.2839, 0.9139] | 0.3864 [0.0861, 0.7161] |
| table_column | self | 0.4823 [0.3709, 0.6652] | 0.5177 [0.3348, 0.6291] |
| table_column | ol_only | 0.3056 [0.1337, 0.5894] | 0.6944 [0.4106, 0.8663] |
| table_column | nla_only | 0.4823 [0.3709, 0.6652] | 0.5177 [0.3348, 0.6291] |
| table_column | delta_only | 0.4646 [0.1201, 0.7130] | 0.5354 [0.2870, 0.8799] |
| table_column | random | 0.5227 [0.3404, 0.7858] | 0.4773 [0.2142, 0.6596] |
| table_role | swap | 0.7143 [0.5865, 0.8493] | 0.2857 [0.1507, 0.4135] |
| table_role | self | 0.8697 [0.7375, 0.9768] | 0.1303 [0.0232, 0.2625] |
| table_role | ol_only | 0.7769 [0.5217, 0.9646] | 0.2231 [0.0354, 0.4783] |
| table_role | nla_only | 0.8697 [0.7375, 0.9768] | 0.1303 [0.0232, 0.2625] |
| table_role | delta_only | 0.7494 [0.5636, 0.9303] | 0.2506 [0.0697, 0.4364] |
| table_role | random | 0.4937 [0.2756, 0.7443] | 0.5063 [0.2557, 0.7244] |
| table_row | swap | 0.3708 [0.2898, 0.6324] | 0.6292 [0.3676, 0.7102] |
| table_row | self | 0.6726 [0.5134, 0.7943] | 0.3274 [0.2057, 0.4866] |
| table_row | ol_only | 0.8184 [0.7395, 0.8667] | 0.1816 [0.1333, 0.2605] |
| table_row | nla_only | 0.6726 [0.5134, 0.7943] | 0.3274 [0.2057, 0.4866] |
| table_row | delta_only | 0.7187 [0.4676, 0.8681] | 0.2813 [0.1319, 0.5324] |
| table_row | random | 0.4015 [0.1967, 0.8134] | 0.5985 [0.1866, 0.8033] |
| table_status | swap | 0.7500 [0.6044, 0.9082] | 0.2500 [0.0918, 0.3956] |
| table_status | self | 0.9343 [0.8188, 1.0000] | 0.0657 [0.0000, 0.1812] |
| table_status | ol_only | 1.0000 [1.0000, 1.0000] | 0.0000 [0.0000, 0.0000] |
| table_status | nla_only | 0.9343 [0.8188, 1.0000] | 0.0657 [0.0000, 0.1812] |
| table_status | delta_only | 0.6111 [0.2381, 0.8756] | 0.3889 [0.1244, 0.7619] |
| table_status | random | 0.8359 [0.7412, 0.9167] | 0.1641 [0.0833, 0.2588] |

**E7 operational setup parity (§94, c97d0893):** PASS_INPUT_AUDIT.

First32-token agreement: 40/52 (76.92%). Median first-divergence position: 58.5. Full-token agreement: 23.08%; full decoded-text agreement: 23.08%.

DESCRIPTIVE: §94 c97d0893 removes parity acceptance thresholds after seeing the earlier operational parity numbers and before any E7 science. Padding, attention-mask and consumed position-ID checks remain mandatory hard gates.

Positions are zero-based counts of matching preceding tokens. Identical completions, including matching early EOS, have no divergence and are censored at128 for the all-readout median. Only padding after the first EOS is ignored. Batch8 is a setup reference; every production readout uses the batch32 setting, including its final partial unit. No per-item selection or fallback.
