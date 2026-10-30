**E23 — EXPLORATORY; registered §117 analysis, run once.**

**Registered expectations and tests.** Mis must be within AUROC 0.40–0.60 under fixed M1/M2; the in-contract positive controls must reach M1 ≥ 0.80; Swap must be ≤ 0.50 wherever matched F16 is ≥ 0.70. Rules 1–3 distinguish measure, input and item-set explanations; rule 4 compares AR decodability with text; rule 6 tests the E23b factors.

**Primary assessment (tag 44):** rule 1 (measure) NOT MET; rule 2 (input) NOT MET. Validity gates pass for 8/8 row/set assays. E23b names **phrasing** under rule 6. Numerical contrasts below retain their registered flags; failed validity gates limit interpretation.

**Main finding.** The registered item-set criterion (rule 3) holds for table-column F16 under M1: S−O = +0.3677 [0.1822, 0.5212], and under M2: +0.3248 [0.1202, 0.5663]. In-contract table-column M1 is 0.6037 on O and 0.9714 on S. Thus a general claim that the reconstructor cannot align table-column information is not supported across these item sets. Rule 4 is met in 26/40 primary cells; it is not a universal result. All 23 applicable Swap checks across both tags pass.

Authority: 66af2c0d, clarifications 1–2 including 1642d63e, and the 09:10 correction e347b86a. F16 follows the read token and is in-contract; P32/Pfull are off-contract. M1 projects raw AR outputs on raw-space true-activation directions, with the dev sign fixed. Set S uses its own 40 mine items to train the primary direction; W1-to-S transfer is secondary. No whitening or test sign flip.

O = W1: 84 test items per row, with W1 template clusters. S = Suraj: M1/T use 160 select items; M2 uses grouped five-fold CV over all 200 items (each its own cluster). O M2/T share five folds; S T trains on mine and tests on select. CIs are the registered 2,000-resample bootstrap, seed 20261025; contrasts preserve pairing and the different denominators.

Mis donors are sampled independently of value within row/set. Swap donors have the opposite value. Both reuse the frozen donor F16 reconstruction; M2 applies the recipient’s F16 fold model without refitting. A donor may be in that model’s training pool, as registered. T is fitted separately for each arm. No new fitting or resampling was performed to produce this report.

**M1/M2/T per row × set × arm.** Every entry is AUROC [95% CI]. R4 = MET means M2 ≤ T + 0.05; it is an operational comparison, not an equivalence proof.

**Tag 44 — primary.**

| Set | Row | Arm | Contract | M1 | M2 | T | R4 |
|---|---|---|---|---|---|---|---|
| O | list_index | F16 | in-contract | 0.5754 [0.3946, 0.7160] | 0.7874 [0.6774, 0.9515] | 0.7483 [0.6641, 0.8716] | MET |
| O | list_index | P32 | off-contract | 0.9456 [0.8498, 1.0000] | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | MET |
| O | list_index | Pfull | off-contract | 0.5142 [0.1882, 0.8050] | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | MET |
| O | list_index | Mis | mismatched following-span control | 0.5037 [0.4129, 0.5890] | 0.4912 [0.3537, 0.6182] | 0.4555 [0.3475, 0.5663] | MET |
| O | list_index | Swap | secondary opposite-value following-span control | 0.2922 [0.1973, 0.4025] | 0.2143 [0.1502, 0.2789] | 0.6395 [0.5589, 0.7500] | MET |
| O | prose_paren | F16 | in-contract | 0.8330 [0.5964, 1.0000] | 0.7854 [0.5930, 1.0000] | 0.5598 [0.3330, 0.7988] | NOT MET |
| O | prose_paren | P32 | off-contract | 0.7007 [0.6412, 0.8912] | 0.6831 [0.6468, 0.8656] | 0.8044 [0.7296, 0.9972] | MET |
| O | prose_paren | Pfull | off-contract | 0.6088 [0.5278, 0.7455] | 0.7562 [0.7126, 0.9206] | 0.6667 [0.6247, 0.7143] | NOT MET |
| O | prose_paren | Mis | mismatched following-span control | 0.4144 [0.3399, 0.4734] | 0.4751 [0.3880, 0.5802] | 0.5879 [0.5170, 0.6536] | MET |
| O | prose_paren | Swap | secondary opposite-value following-span control | 0.1233 [0.0339, 0.2336] | 0.0771 [0.0142, 0.1684] | 0.8452 [0.7266, 0.9252] | MET |
| O | prose_sentiment | F16 | in-contract | 0.9300 [0.8520, 0.9864] | 0.6769 [0.4782, 0.8858] | 0.5782 [0.4527, 0.7625] | NOT MET |
| O | prose_sentiment | P32 | off-contract | 0.8061 [0.7273, 0.9031] | 1.0000 [1.0000, 1.0000] | 0.6219 [0.4444, 0.8492] | NOT MET |
| O | prose_sentiment | Pfull | off-contract | 0.9858 [0.9660, 1.0000] | 0.9989 [0.9955, 1.0000] | 0.5550 [0.4365, 0.7166] | NOT MET |
| O | prose_sentiment | Mis | mismatched following-span control | 0.5411 [0.4649, 0.6094] | 0.5139 [0.4651, 0.5700] | 0.4498 [0.3429, 0.5822] | NOT MET |
| O | prose_sentiment | Swap | secondary opposite-value following-span control | 0.0300 [0.0079, 0.0544] | 0.1202 [0.0283, 0.2738] | 0.9172 [0.8917, 0.9683] | MET |
| O | python_string | F16 | in-contract | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.9802 [0.9365, 1.0000] | MET |
| O | python_string | P32 | off-contract | 0.7755 [0.7143, 0.8543] | 0.9711 [0.9070, 1.0000] | 1.0000 [1.0000, 1.0000] | MET |
| O | python_string | Pfull | off-contract | 0.8798 [0.8475, 0.9359] | 0.9994 [0.9977, 1.0000] | 0.9768 [0.9558, 0.9955] | MET |
| O | python_string | Mis | mismatched following-span control | 0.5230 [0.4393, 0.6006] | 0.4728 [0.3866, 0.5607] | 0.4926 [0.3767, 0.6120] | MET |
| O | python_string | Swap | secondary opposite-value following-span control | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | 0.9790 [0.9286, 1.0000] | MET |
| O | table_column | F16 | in-contract | 0.6037 [0.4529, 0.7823] | 0.6752 [0.4342, 0.8912] | 0.6383 [0.3759, 0.8771] | MET |
| O | table_column | P32 | off-contract | 0.2177 [0.0539, 0.4382] | 0.7608 [0.5822, 0.9592] | 0.6173 [0.4263, 0.8333] | NOT MET |
| O | table_column | Pfull | off-contract | 0.5578 [0.4138, 0.7063] | 0.8163 [0.7347, 0.9717] | 0.8980 [0.8395, 0.9864] | MET |
| O | table_column | Mis | mismatched following-span control | 0.5652 [0.4246, 0.6715] | 0.4906 [0.3841, 0.6247] | 0.3433 [0.2885, 0.4051] | NOT MET |
| O | table_column | Swap | secondary opposite-value following-span control | 0.3141 [0.2211, 0.4189] | 0.0612 [0.0147, 0.1117] | 0.9603 [0.9257, 0.9881] | MET |
| S | list_index | F16 | in-contract | 0.6130 [0.5223, 0.6997] | 0.8068 [0.7433, 0.8623] | 0.6360 [0.5499, 0.7186] | NOT MET |
| S | list_index | P32 | off-contract | 0.7434 [0.6568, 0.8195] | 0.9965 [0.9880, 1.0000] | 0.9805 [0.9626, 0.9931] | MET |
| S | list_index | Pfull | off-contract | 0.7022 [0.6176, 0.7757] | 1.0000 [1.0000, 1.0000] | 0.9350 [0.8976, 0.9656] | NOT MET |
| S | list_index | Mis | mismatched following-span control | 0.5027 [0.4106, 0.5931] | 0.5202 [0.4406, 0.6020] | 0.5190 [0.4240, 0.6078] | MET |
| S | list_index | Swap | secondary opposite-value following-span control | 0.2897 [0.2068, 0.3738] | 0.0191 [0.0012, 0.0462] | 0.7323 [0.6566, 0.8054] | MET |
| S | prose_paren | F16 | in-contract | 0.8903 [0.8428, 0.9355] | 0.9882 [0.9757, 0.9975] | 0.5984 [0.5114, 0.6837] | NOT MET |
| S | prose_paren | P32 | off-contract | 0.4094 [0.3240, 0.5003] | 0.5660 [0.4882, 0.6458] | 0.6209 [0.5314, 0.7024] | MET |
| S | prose_paren | Pfull | off-contract | 0.4727 [0.3835, 0.5571] | 0.6709 [0.5900, 0.7454] | 0.6645 [0.5781, 0.7459] | MET |
| S | prose_paren | Mis | mismatched following-span control | 0.5584 [0.4681, 0.6505] | 0.5257 [0.4467, 0.6070] | 0.5008 [0.4089, 0.5848] | MET |
| S | prose_paren | Swap | secondary opposite-value following-span control | 0.0734 [0.0384, 0.1144] | 0.0002 [0.0000, 0.0010] | 0.7288 [0.6486, 0.7991] | MET |
| S | table_column | F16 | in-contract | 0.9714 [0.9491, 0.9883] | 1.0000 [1.0000, 1.0000] | 0.4655 [0.3771, 0.5556] | NOT MET |
| S | table_column | P32 | off-contract | 0.4331 [0.3437, 0.5180] | 0.9062 [0.8659, 0.9438] | 0.5041 [0.4120, 0.5900] | NOT MET |
| S | table_column | Pfull | off-contract | 0.5336 [0.4449, 0.6267] | 0.9220 [0.8824, 0.9545] | 0.6067 [0.5142, 0.6913] | NOT MET |
| S | table_column | Mis | mismatched following-span control | 0.5399 [0.4509, 0.6312] | 0.5150 [0.4364, 0.5964] | 0.5215 [0.4318, 0.6108] | MET |
| S | table_column | Swap | secondary opposite-value following-span control | 0.0272 [0.0111, 0.0509] | 0.0000 [0.0000, 0.0000] | 0.7094 [0.6236, 0.7854] | MET |

**Tag 40 — secondary.**

| Set | Row | Arm | Contract | M1 | M2 | T | R4 |
|---|---|---|---|---|---|---|---|
| O | list_index | F16 | in-contract | 0.5652 [0.4116, 0.7120] | 0.7942 [0.6950, 0.9399] | 0.7483 [0.6641, 0.8716] | MET |
| O | list_index | P32 | off-contract | 0.9087 [0.7234, 1.0000] | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | MET |
| O | list_index | Pfull | off-contract | 0.6003 [0.2522, 0.9189] | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | MET |
| O | list_index | Mis | mismatched following-span control | 0.4918 [0.3957, 0.5833] | 0.4765 [0.3424, 0.5952] | 0.4555 [0.3475, 0.5663] | MET |
| O | list_index | Swap | secondary opposite-value following-span control | 0.2951 [0.1973, 0.4144] | 0.2234 [0.1434, 0.2891] | 0.6395 [0.5589, 0.7500] | MET |
| O | prose_paren | F16 | in-contract | 0.8348 [0.6369, 1.0000] | 0.8166 [0.5873, 1.0000] | 0.5598 [0.3330, 0.7988] | NOT MET |
| O | prose_paren | P32 | off-contract | 0.6939 [0.6190, 0.8991] | 0.6667 [0.6378, 0.8452] | 0.8044 [0.7296, 0.9972] | MET |
| O | prose_paren | Pfull | off-contract | 0.5901 [0.5283, 0.7109] | 0.7472 [0.7058, 0.8719] | 0.6667 [0.6247, 0.7143] | NOT MET |
| O | prose_paren | Mis | mismatched following-span control | 0.4065 [0.3461, 0.4615] | 0.4813 [0.3931, 0.5901] | 0.5879 [0.5170, 0.6536] | MET |
| O | prose_paren | Swap | secondary opposite-value following-span control | 0.1046 [0.0255, 0.2018] | 0.0573 [0.0091, 0.1224] | 0.8452 [0.7266, 0.9252] | MET |
| O | prose_sentiment | F16 | in-contract | 0.9147 [0.8159, 0.9838] | 0.7273 [0.5360, 0.9026] | 0.5782 [0.4527, 0.7625] | NOT MET |
| O | prose_sentiment | P32 | off-contract | 0.8475 [0.7664, 0.9331] | 1.0000 [1.0000, 1.0000] | 0.6219 [0.4444, 0.8492] | NOT MET |
| O | prose_sentiment | Pfull | off-contract | 0.9598 [0.9082, 1.0000] | 0.9898 [0.9705, 1.0000] | 0.5550 [0.4365, 0.7166] | NOT MET |
| O | prose_sentiment | Mis | mismatched following-span control | 0.5383 [0.4476, 0.6222] | 0.5156 [0.4671, 0.5669] | 0.4498 [0.3429, 0.5822] | NOT MET |
| O | prose_sentiment | Swap | secondary opposite-value following-span control | 0.0329 [0.0113, 0.0499] | 0.1111 [0.0283, 0.2568] | 0.9172 [0.8917, 0.9683] | MET |
| O | python_string | F16 | in-contract | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.9802 [0.9365, 1.0000] | MET |
| O | python_string | P32 | off-contract | 0.7783 [0.7443, 0.8537] | 0.9858 [0.9524, 1.0000] | 1.0000 [1.0000, 1.0000] | MET |
| O | python_string | Pfull | off-contract | 0.9376 [0.8793, 0.9887] | 1.0000 [1.0000, 1.0000] | 0.9768 [0.9558, 0.9955] | MET |
| O | python_string | Mis | mismatched following-span control | 0.5303 [0.4563, 0.6020] | 0.4813 [0.3886, 0.5845] | 0.4926 [0.3767, 0.6120] | MET |
| O | python_string | Swap | secondary opposite-value following-span control | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | 0.9790 [0.9286, 1.0000] | MET |
| O | table_column | F16 | in-contract | 0.6100 [0.4660, 0.7869] | 0.6361 [0.4195, 0.8622] | 0.6383 [0.3759, 0.8771] | MET |
| O | table_column | P32 | off-contract | 0.2630 [0.0731, 0.5159] | 0.7574 [0.5465, 0.9559] | 0.6173 [0.4263, 0.8333] | NOT MET |
| O | table_column | Pfull | off-contract | 0.5726 [0.4042, 0.7052] | 0.8339 [0.7511, 0.9881] | 0.8980 [0.8395, 0.9864] | MET |
| O | table_column | Mis | mismatched following-span control | 0.5680 [0.4498, 0.6574] | 0.4782 [0.3849, 0.6035] | 0.3433 [0.2885, 0.4051] | NOT MET |
| O | table_column | Swap | secondary opposite-value following-span control | 0.2971 [0.1916, 0.3906] | 0.0794 [0.0255, 0.1287] | 0.9603 [0.9257, 0.9881] | MET |
| S | list_index | F16 | in-contract | 0.5542 [0.4663, 0.6428] | 0.8222 [0.7618, 0.8793] | 0.6360 [0.5499, 0.7186] | NOT MET |
| S | list_index | P32 | off-contract | 0.6994 [0.6072, 0.7825] | 0.9973 [0.9906, 1.0000] | 0.9805 [0.9626, 0.9931] | MET |
| S | list_index | Pfull | off-contract | 0.7253 [0.6417, 0.7984] | 1.0000 [1.0000, 1.0000] | 0.9350 [0.8976, 0.9656] | NOT MET |
| S | list_index | Mis | mismatched following-span control | 0.5045 [0.4141, 0.5933] | 0.5195 [0.4408, 0.5980] | 0.5190 [0.4240, 0.6078] | MET |
| S | list_index | Swap | secondary opposite-value following-span control | 0.3259 [0.2421, 0.4130] | 0.0188 [0.0017, 0.0441] | 0.7323 [0.6566, 0.8054] | MET |
| S | prose_paren | F16 | in-contract | 0.8550 [0.7998, 0.9104] | 0.9801 [0.9619, 0.9935] | 0.5984 [0.5114, 0.6837] | NOT MET |
| S | prose_paren | P32 | off-contract | 0.4419 [0.3573, 0.5288] | 0.5630 [0.4822, 0.6430] | 0.6209 [0.5314, 0.7024] | MET |
| S | prose_paren | Pfull | off-contract | 0.4770 [0.3859, 0.5669] | 0.6788 [0.6025, 0.7518] | 0.6645 [0.5781, 0.7459] | MET |
| S | prose_paren | Mis | mismatched following-span control | 0.5303 [0.4421, 0.6217] | 0.5235 [0.4435, 0.6029] | 0.5008 [0.4089, 0.5848] | MET |
| S | prose_paren | Swap | secondary opposite-value following-span control | 0.0838 [0.0451, 0.1321] | 0.0003 [0.0000, 0.0012] | 0.7288 [0.6486, 0.7991] | MET |
| S | table_column | F16 | in-contract | 0.9572 [0.9269, 0.9804] | 1.0000 [1.0000, 1.0000] | 0.4655 [0.3771, 0.5556] | NOT MET |
| S | table_column | P32 | off-contract | 0.4309 [0.3433, 0.5169] | 0.9128 [0.8718, 0.9490] | 0.5041 [0.4120, 0.5900] | NOT MET |
| S | table_column | Pfull | off-contract | 0.4933 [0.4066, 0.5874] | 0.9097 [0.8670, 0.9452] | 0.6067 [0.5142, 0.6913] | NOT MET |
| S | table_column | Mis | mismatched following-span control | 0.5407 [0.4532, 0.6317] | 0.5201 [0.4421, 0.6001] | 0.5215 [0.4318, 0.6108] | MET |
| S | table_column | Swap | secondary opposite-value following-span control | 0.0417 [0.0183, 0.0727] | 0.0000 [0.0000, 0.0000] | 0.7094 [0.6236, 0.7854] | MET |

**Rules 1–2.** Each requires Δ ≥ 0.15 and CI lower > 0 in both sets. Rule 1 is F16 M2−M1; rule 2 is M1(P32)−M1(F16). Rule 2’s P32 arm remains off-contract.

| Rule | Tag | Set | Δ AUROC [95% CI] | Cell criterion |
|---|---|---|---|---|
| rule1_measure | 44 | O | +0.0714 [-0.2805, +0.3537] | NOT MET |
| rule2_input | 44 | O | -0.3861 [-0.6247, -0.1003] | NOT MET |
| rule1_measure | 44 | S | +0.0286 [+0.0112, +0.0519] | NOT MET |
| rule2_input | 44 | S | -0.5383 [-0.6302, -0.4472] | NOT MET |
| rule1_measure | 40 | O | +0.0261 [-0.2744, +0.2885] | NOT MET |
| rule2_input | 40 | O | -0.3469 [-0.6196, -0.0680] | NOT MET |
| rule1_measure | 40 | S | +0.0428 [+0.0189, +0.0739] | NOT MET |
| rule2_input | 40 | S | -0.5262 [-0.6181, -0.4353] | NOT MET |

**Rule 3: item-set contrasts S−O.** A dagger (†) marks the registered cell criterion Δ ≥ 0.15 with CI lower > 0. These are cellwise results, with no new multiple-testing rule. Interpret them subject to rule 5.

| Tag | Row | Arm | Contract | Δ M1 [CI] | Δ M2 [CI] | Δ T [CI] |
|---|---|---|---|---|---|---|
| 44 | table_column | F16 | in-contract | +0.3677 [+0.1822, +0.5212] † | +0.3248 [+0.1202, +0.5663] † | -0.1729 [-0.4543, +0.1023] |
| 44 | table_column | P32 | off-contract | +0.2154 [-0.0324, +0.4021] | +0.1454 [-0.0668, +0.3346] | -0.1133 [-0.3704, +0.0829] |
| 44 | table_column | Pfull | off-contract | -0.0242 [-0.1952, +0.1475] | +0.1057 [-0.0509, +0.1905] | -0.2912 [-0.4223, -0.1820] |
| 44 | table_column | Mis | mismatched following-span control | -0.0253 [-0.1697, +0.1357] | +0.0244 [-0.1325, +0.1596] | +0.1782 [+0.0707, +0.2800] † |
| 44 | table_column | Swap | secondary opposite-value following-span control | -0.2869 [-0.3958, -0.1933] | -0.0612 [-0.1117, -0.0130] | -0.2509 [-0.3369, -0.1673] |
| 44 | list_index | F16 | in-contract | +0.0376 [-0.1205, +0.2339] | +0.0194 [-0.1442, +0.1584] | -0.1123 [-0.2809, +0.0087] |
| 44 | list_index | P32 | off-contract | -0.2021 [-0.3111, -0.0801] | -0.0035 [-0.0120, +0.0000] | -0.0195 [-0.0377, -0.0067] |
| 44 | list_index | Pfull | off-contract | +0.1880 [-0.1457, +0.5120] | +0.0000 [+0.0000, +0.0000] | -0.0650 [-0.1038, -0.0342] |
| 44 | list_index | Mis | mismatched following-span control | -0.0010 [-0.1271, +0.1212] | +0.0290 [-0.1209, +0.1904] | +0.0635 [-0.0877, +0.2095] |
| 44 | list_index | Swap | secondary opposite-value following-span control | -0.0025 [-0.1389, +0.1246] | -0.1952 [-0.2608, -0.1264] | +0.0928 [-0.0356, +0.2037] |
| 44 | prose_paren | F16 | in-contract | +0.0573 [-0.1259, +0.3070] | +0.2028 [-0.0146, +0.3989] | +0.0386 [-0.2289, +0.2769] |
| 44 | prose_paren | P32 | off-contract | -0.2913 [-0.5128, -0.1840] | -0.1171 [-0.3258, -0.0382] | -0.1835 [-0.4088, -0.0692] |
| 44 | prose_paren | Pfull | off-contract | -0.1362 [-0.3069, -0.0089] | -0.0853 [-0.2763, -0.0000] | -0.0021 [-0.1007, +0.0894] |
| 44 | prose_paren | Mis | mismatched following-span control | +0.1440 [+0.0310, +0.2612] | +0.0506 [-0.0769, +0.1738] | -0.0871 [-0.2025, +0.0255] |
| 44 | prose_paren | Swap | secondary opposite-value following-span control | -0.0499 [-0.1664, +0.0534] | -0.0769 [-0.1603, -0.0145] | -0.1165 [-0.2313, +0.0290] |
| 40 | table_column | F16 | in-contract | +0.3472 [+0.1520, +0.4943] † | +0.3639 [+0.1531, +0.5856] † | -0.1729 [-0.4543, +0.1023] |
| 40 | table_column | P32 | off-contract | +0.1679 [-0.1061, +0.3794] | +0.1554 [-0.0532, +0.3709] | -0.1133 [-0.3704, +0.0829] |
| 40 | table_column | Pfull | off-contract | -0.0793 [-0.2393, +0.1117] | +0.0758 [-0.0761, +0.1675] | -0.2912 [-0.4223, -0.1820] |
| 40 | table_column | Mis | mismatched following-span control | -0.0273 [-0.1610, +0.1132] | +0.0419 [-0.1060, +0.1676] | +0.1782 [+0.0707, +0.2800] † |
| 40 | table_column | Swap | secondary opposite-value following-span control | -0.2553 [-0.3518, -0.1467] | -0.0794 [-0.1298, -0.0238] | -0.2509 [-0.3369, -0.1673] |
| 40 | list_index | F16 | in-contract | -0.0110 [-0.1765, +0.1546] | +0.0280 [-0.1296, +0.1453] | -0.1123 [-0.2809, +0.0087] |
| 40 | list_index | P32 | off-contract | -0.2094 [-0.3563, -0.0172] | -0.0027 [-0.0093, +0.0000] | -0.0195 [-0.0377, -0.0067] |
| 40 | list_index | Pfull | off-contract | +0.1250 [-0.2033, +0.4579] | +0.0000 [+0.0000, +0.0000] | -0.0650 [-0.1038, -0.0342] |
| 40 | list_index | Mis | mismatched following-span control | +0.0127 [-0.1212, +0.1401] | +0.0431 [-0.1034, +0.1994] | +0.0635 [-0.0877, +0.2095] |
| 40 | list_index | Swap | secondary opposite-value following-span control | +0.0309 [-0.1090, +0.1640] | -0.2046 [-0.2724, -0.1285] | +0.0928 [-0.0356, +0.2037] |
| 40 | prose_paren | F16 | in-contract | +0.0202 [-0.1616, +0.2305] | +0.1635 [-0.0229, +0.3967] | +0.0386 [-0.2289, +0.2769] |
| 40 | prose_paren | P32 | off-contract | -0.2520 [-0.4881, -0.1326] | -0.1037 [-0.3115, -0.0336] | -0.1835 [-0.4088, -0.0692] |
| 40 | prose_paren | Pfull | off-contract | -0.1131 [-0.2668, +0.0043] | -0.0684 [-0.2173, +0.0090] | -0.0021 [-0.1007, +0.0894] |
| 40 | prose_paren | Mis | mismatched following-span control | +0.1238 [+0.0166, +0.2339] | +0.0422 [-0.0923, +0.1638] | -0.0871 [-0.2025, +0.0255] |
| 40 | prose_paren | Swap | secondary opposite-value following-span control | -0.0208 [-0.1288, +0.0758] | -0.0570 [-0.1066, -0.0088] | -0.1165 [-0.2313, +0.0290] |

**Rule 5: validity.** Mis numerical AUROCs/CIs are in the main tables. Each Mis gate uses its point AUROC in [0.40, 0.60]. Both positive controls must have F16 M1 ≥ 0.80; the frozen analyser marks all assays at that tag uninterpretable if either positive control fails.

| Tag | Set | Row | Mis M1 gate | Mis M2 gate | python_string control | prose_sentiment control | Interpretable |
|---|---|---|---|---|---|---|---|
| 44 | O | list_index | MET | MET | MET | MET | YES |
| 40 | O | list_index | MET | MET | MET | MET | YES |
| 44 | O | prose_paren | MET | MET | MET | MET | YES |
| 40 | O | prose_paren | MET | MET | MET | MET | YES |
| 44 | O | prose_sentiment | MET | MET | MET | MET | YES |
| 40 | O | prose_sentiment | MET | MET | MET | MET | YES |
| 44 | O | python_string | MET | MET | MET | MET | YES |
| 40 | O | python_string | MET | MET | MET | MET | YES |
| 44 | O | table_column | MET | MET | MET | MET | YES |
| 40 | O | table_column | MET | MET | MET | MET | YES |
| 44 | S | list_index | MET | MET | MET | MET | YES |
| 40 | S | list_index | MET | MET | MET | MET | YES |
| 44 | S | prose_paren | MET | MET | MET | MET | YES |
| 40 | S | prose_paren | MET | MET | MET | MET | YES |
| 44 | S | table_column | MET | MET | MET | MET | YES |
| 40 | S | table_column | MET | MET | MET | MET | YES |

**Swap secondary check.** MET means Swap ≤ 0.50 where F16 ≥ 0.70; “n/a” means the F16 applicability threshold was not reached. Matched and Swap AUROCs/CIs are in the main tables.

| Set | Row | Tag 44 M1 | Tag 44 M2 | Tag 40 M1 | Tag 40 M2 |
|---|---|---|---|---|---|
| O | list_index | n/a | MET | n/a | MET |
| O | prose_paren | MET | MET | MET | MET |
| O | prose_sentiment | MET | n/a | MET | MET |
| O | python_string | MET | MET | MET | MET |
| O | table_column | n/a | n/a | n/a | n/a |
| S | list_index | n/a | MET | n/a | MET |
| S | prose_paren | MET | MET | MET | MET |
| S | table_column | MET | MET | MET | MET |

**Secondary W1-to-S probe transfer.** These values are not used in the decision rules; primary S M1 uses the set-S direction.

| Row | Arm | Contract | Tag 44 AUROC [CI] | Tag 40 AUROC [CI] |
|---|---|---|---|---|
| table_column | F16 | in-contract | 0.9752 [0.9546, 0.9909] | 0.9611 [0.9326, 0.9834] |
| table_column | P32 | off-contract | 0.5953 [0.5070, 0.6782] | 0.6062 [0.5183, 0.6900] |
| table_column | Pfull | off-contract | 0.5419 [0.4477, 0.6309] | 0.5486 [0.4549, 0.6391] |
| table_column | Mis | mismatched following-span control | 0.5516 [0.4647, 0.6437] | 0.5427 [0.4557, 0.6322] |
| table_column | Swap | secondary opposite-value following-span control | 0.0166 [0.0048, 0.0334] | 0.0306 [0.0114, 0.0564] |
| list_index | F16 | in-contract | 0.6073 [0.5167, 0.6982] | 0.6053 [0.5180, 0.6943] |
| list_index | P32 | off-contract | 0.5736 [0.4886, 0.6620] | 0.6894 [0.6071, 0.7697] |
| list_index | Pfull | off-contract | 0.3689 [0.2816, 0.4598] | 0.3672 [0.2789, 0.4535] |
| list_index | Mis | mismatched following-span control | 0.4987 [0.4066, 0.5922] | 0.5151 [0.4227, 0.6088] |
| list_index | Swap | secondary opposite-value following-span control | 0.4039 [0.3192, 0.4873] | 0.3986 [0.3138, 0.4829] |
| prose_paren | F16 | in-contract | 0.9286 [0.8761, 0.9700] | 0.9247 [0.8761, 0.9658] |
| prose_paren | P32 | off-contract | 0.4081 [0.3238, 0.4999] | 0.4119 [0.3286, 0.5061] |
| prose_paren | Pfull | off-contract | 0.6069 [0.5193, 0.6919] | 0.5592 [0.4659, 0.6468] |
| prose_paren | Mis | mismatched following-span control | 0.5797 [0.4886, 0.6684] | 0.5672 [0.4777, 0.6587] |
| prose_paren | Swap | secondary opposite-value following-span control | 0.0495 [0.0173, 0.0931] | 0.0506 [0.0178, 0.0924] |

**E23b: complete 2 × 2 × 2 table.** Oracle-lens asked AUROC on table column. W1 uses its two frozen phrasing pairs; Suraj uses its frozen bullet pair. O n = 84, S n = 160.

| Set | Phrasing | Layer | AUROC [95% CI] |
|---|---|---|---|
| O | W1 | 42 | 0.5782 [0.4836, 0.6797] |
| S | W1 | 42 | 0.3561 [0.2718, 0.4450] |
| O | Suraj | 42 | 0.7418 [0.6429, 0.8458] |
| S | Suraj | 42 | 0.6460 [0.5543, 0.7291] |
| O | W1 | 44 | 0.4819 [0.3441, 0.6032] |
| S | W1 | 44 | 0.3959 [0.3086, 0.4853] |
| O | Suraj | 44 | 0.7639 [0.6308, 0.8909] |
| S | Suraj | 44 | 0.7027 [0.6147, 0.7827] |

**Rule 6 main effects.** Signs are S−O, Suraj−W1, and layer 44−42; each averages the other four cells. The frozen rule ranks absolute effect magnitude and requires |Δ| ≥ 0.10 with CI excluding zero.

| Factor | Signed Δ AUROC [95% CI] | Qualifies |
|---|---|---|
| set | -0.1162 [-0.1966, -0.0264] | MET |
| phrasing | +0.2606 [+0.1540, +0.3668] | MET |
| layer | +0.0056 [-0.0240, +0.0333] | NOT MET |

Rule 6 result: **phrasing**. Outcome (c) does not apply: the training span follows the target, as settled before scoring.

**Provenance and execution.** Pod vh9zqysqkbb6kq; source cd402e2cfcaf5d2b9885fa0baa47b14da621268f. All 169 source pins and collection/input/continuation/forecast seals verified before analysis. All 600 Suraj items passed the ≥ 0.999 cosine parity gate at layers 40, 42 and 44. The registered CPU analyser was invoked once and completed in 82.229 seconds. No GPU/model calls or rerun.

Collection seal: `5485951dd8341b096bbb95b95c4afd055bc6fd12d0d4486440b3bf1e0d34caf7`.
Input seal: `88c46812fd7a5a044948b0e10dcb4f2b93b76b2aa15ac1862977585b1459a46d`.
Registered analysis seal: `af7b21867d6338847bdc2207046a31c0c1634b2975a2f8facf1fe5db6ec1c648`.

This full report formats the sealed metrics only. The original analysis/RESULTS.md, metrics, predictions, folds, provenance, once guard and SCORE_SEAL.json remain unchanged. The report is separately bound by REPORT_SEAL.json.
