**Predictions (§117):** discriminate measure, input and item-set explanations using the frozen rules; Mis must be at chance, the two positive controls must pass, and Swap should reverse a strong F16 signal.

**Assessment:** rule1 measure=False; rule2 input=False; E23b cause=phrasing. Interpretability is conditional on the reported validity gates.

EXPLORATORY. Tag44 primary; tag40 secondary. Raw M1; no sign flip or whitening. Full contrasts, gates, Swap and transfer secondaries are in metrics.json. Outcome(c) does not apply.

| Set | Row | Tag | Arm | Contract | Measure | AUROC [95% CI] | n |
|---|---|---|---|---|---|---|---|
| O | list_index | 44 | F16 | in-contract | T | 0.7483 [0.6641, 0.8716] | 84 |
| O | list_index | 40 | F16 | in-contract | T | 0.7483 [0.6641, 0.8716] | 84 |
| O | list_index | 44 | P32 | off-contract | T | 1.0000 [1.0000, 1.0000] | 84 |
| O | list_index | 40 | P32 | off-contract | T | 1.0000 [1.0000, 1.0000] | 84 |
| O | list_index | 44 | Pfull | off-contract | T | 1.0000 [1.0000, 1.0000] | 84 |
| O | list_index | 40 | Pfull | off-contract | T | 1.0000 [1.0000, 1.0000] | 84 |
| O | list_index | 44 | Mis | mismatched following-span control | T | 0.4555 [0.3475, 0.5663] | 84 |
| O | list_index | 40 | Mis | mismatched following-span control | T | 0.4555 [0.3475, 0.5663] | 84 |
| O | list_index | 44 | Swap | secondary opposite-value following-span control | T | 0.6395 [0.5589, 0.7500] | 84 |
| O | list_index | 40 | Swap | secondary opposite-value following-span control | T | 0.6395 [0.5589, 0.7500] | 84 |
| O | list_index | 44 | F16 | in-contract | M1 | 0.5754 [0.3946, 0.7160] | 84 |
| O | list_index | 44 | P32 | off-contract | M1 | 0.9456 [0.8498, 1.0000] | 84 |
| O | list_index | 44 | Pfull | off-contract | M1 | 0.5142 [0.1882, 0.8050] | 84 |
| O | list_index | 44 | Mis | mismatched following-span control | M1 | 0.5037 [0.4129, 0.5890] | 84 |
| O | list_index | 44 | Swap | secondary opposite-value following-span control | M1 | 0.2922 [0.1973, 0.4025] | 84 |
| O | list_index | 44 | F16 | in-contract | M2 | 0.7874 [0.6774, 0.9515] | 84 |
| O | list_index | 44 | Mis | mismatched following-span control | M2 | 0.4912 [0.3537, 0.6182] | 84 |
| O | list_index | 44 | Swap | secondary opposite-value following-span control | M2 | 0.2143 [0.1502, 0.2789] | 84 |
| O | list_index | 44 | P32 | off-contract | M2 | 1.0000 [1.0000, 1.0000] | 84 |
| O | list_index | 44 | Pfull | off-contract | M2 | 1.0000 [1.0000, 1.0000] | 84 |
| O | list_index | 40 | F16 | in-contract | M1 | 0.5652 [0.4116, 0.7120] | 84 |
| O | list_index | 40 | P32 | off-contract | M1 | 0.9087 [0.7234, 1.0000] | 84 |
| O | list_index | 40 | Pfull | off-contract | M1 | 0.6003 [0.2522, 0.9189] | 84 |
| O | list_index | 40 | Mis | mismatched following-span control | M1 | 0.4918 [0.3957, 0.5833] | 84 |
| O | list_index | 40 | Swap | secondary opposite-value following-span control | M1 | 0.2951 [0.1973, 0.4144] | 84 |
| O | list_index | 40 | F16 | in-contract | M2 | 0.7942 [0.6950, 0.9399] | 84 |
| O | list_index | 40 | Mis | mismatched following-span control | M2 | 0.4765 [0.3424, 0.5952] | 84 |
| O | list_index | 40 | Swap | secondary opposite-value following-span control | M2 | 0.2234 [0.1434, 0.2891] | 84 |
| O | list_index | 40 | P32 | off-contract | M2 | 1.0000 [1.0000, 1.0000] | 84 |
| O | list_index | 40 | Pfull | off-contract | M2 | 1.0000 [1.0000, 1.0000] | 84 |
| O | prose_paren | 44 | F16 | in-contract | T | 0.5598 [0.3330, 0.7988] | 84 |
| O | prose_paren | 40 | F16 | in-contract | T | 0.5598 [0.3330, 0.7988] | 84 |
| O | prose_paren | 44 | P32 | off-contract | T | 0.8044 [0.7296, 0.9972] | 84 |
| O | prose_paren | 40 | P32 | off-contract | T | 0.8044 [0.7296, 0.9972] | 84 |
| O | prose_paren | 44 | Pfull | off-contract | T | 0.6667 [0.6247, 0.7143] | 84 |
| O | prose_paren | 40 | Pfull | off-contract | T | 0.6667 [0.6247, 0.7143] | 84 |
| O | prose_paren | 44 | Mis | mismatched following-span control | T | 0.5879 [0.5170, 0.6536] | 84 |
| O | prose_paren | 40 | Mis | mismatched following-span control | T | 0.5879 [0.5170, 0.6536] | 84 |
| O | prose_paren | 44 | Swap | secondary opposite-value following-span control | T | 0.8452 [0.7266, 0.9252] | 84 |
| O | prose_paren | 40 | Swap | secondary opposite-value following-span control | T | 0.8452 [0.7266, 0.9252] | 84 |
| O | prose_paren | 44 | F16 | in-contract | M1 | 0.8330 [0.5964, 1.0000] | 84 |
| O | prose_paren | 44 | P32 | off-contract | M1 | 0.7007 [0.6412, 0.8912] | 84 |
| O | prose_paren | 44 | Pfull | off-contract | M1 | 0.6088 [0.5278, 0.7455] | 84 |
| O | prose_paren | 44 | Mis | mismatched following-span control | M1 | 0.4144 [0.3399, 0.4734] | 84 |
| O | prose_paren | 44 | Swap | secondary opposite-value following-span control | M1 | 0.1233 [0.0339, 0.2336] | 84 |
| O | prose_paren | 44 | F16 | in-contract | M2 | 0.7854 [0.5930, 1.0000] | 84 |
| O | prose_paren | 44 | Mis | mismatched following-span control | M2 | 0.4751 [0.3880, 0.5802] | 84 |
| O | prose_paren | 44 | Swap | secondary opposite-value following-span control | M2 | 0.0771 [0.0142, 0.1684] | 84 |
| O | prose_paren | 44 | P32 | off-contract | M2 | 0.6831 [0.6468, 0.8656] | 84 |
| O | prose_paren | 44 | Pfull | off-contract | M2 | 0.7562 [0.7126, 0.9206] | 84 |
| O | prose_paren | 40 | F16 | in-contract | M1 | 0.8348 [0.6369, 1.0000] | 84 |
| O | prose_paren | 40 | P32 | off-contract | M1 | 0.6939 [0.6190, 0.8991] | 84 |
| O | prose_paren | 40 | Pfull | off-contract | M1 | 0.5901 [0.5283, 0.7109] | 84 |
| O | prose_paren | 40 | Mis | mismatched following-span control | M1 | 0.4065 [0.3461, 0.4615] | 84 |
| O | prose_paren | 40 | Swap | secondary opposite-value following-span control | M1 | 0.1046 [0.0255, 0.2018] | 84 |
| O | prose_paren | 40 | F16 | in-contract | M2 | 0.8166 [0.5873, 1.0000] | 84 |
| O | prose_paren | 40 | Mis | mismatched following-span control | M2 | 0.4813 [0.3931, 0.5901] | 84 |
| O | prose_paren | 40 | Swap | secondary opposite-value following-span control | M2 | 0.0573 [0.0091, 0.1224] | 84 |
| O | prose_paren | 40 | P32 | off-contract | M2 | 0.6667 [0.6378, 0.8452] | 84 |
| O | prose_paren | 40 | Pfull | off-contract | M2 | 0.7472 [0.7058, 0.8719] | 84 |
| O | prose_sentiment | 44 | F16 | in-contract | T | 0.5782 [0.4527, 0.7625] | 84 |
| O | prose_sentiment | 40 | F16 | in-contract | T | 0.5782 [0.4527, 0.7625] | 84 |
| O | prose_sentiment | 44 | P32 | off-contract | T | 0.6219 [0.4444, 0.8492] | 84 |
| O | prose_sentiment | 40 | P32 | off-contract | T | 0.6219 [0.4444, 0.8492] | 84 |
| O | prose_sentiment | 44 | Pfull | off-contract | T | 0.5550 [0.4365, 0.7166] | 84 |
| O | prose_sentiment | 40 | Pfull | off-contract | T | 0.5550 [0.4365, 0.7166] | 84 |
| O | prose_sentiment | 44 | Mis | mismatched following-span control | T | 0.4498 [0.3429, 0.5822] | 84 |
| O | prose_sentiment | 40 | Mis | mismatched following-span control | T | 0.4498 [0.3429, 0.5822] | 84 |
| O | prose_sentiment | 44 | Swap | secondary opposite-value following-span control | T | 0.9172 [0.8917, 0.9683] | 84 |
| O | prose_sentiment | 40 | Swap | secondary opposite-value following-span control | T | 0.9172 [0.8917, 0.9683] | 84 |
| O | prose_sentiment | 44 | F16 | in-contract | M1 | 0.9300 [0.8520, 0.9864] | 84 |
| O | prose_sentiment | 44 | P32 | off-contract | M1 | 0.8061 [0.7273, 0.9031] | 84 |
| O | prose_sentiment | 44 | Pfull | off-contract | M1 | 0.9858 [0.9660, 1.0000] | 84 |
| O | prose_sentiment | 44 | Mis | mismatched following-span control | M1 | 0.5411 [0.4649, 0.6094] | 84 |
| O | prose_sentiment | 44 | Swap | secondary opposite-value following-span control | M1 | 0.0300 [0.0079, 0.0544] | 84 |
| O | prose_sentiment | 44 | F16 | in-contract | M2 | 0.6769 [0.4782, 0.8858] | 84 |
| O | prose_sentiment | 44 | Mis | mismatched following-span control | M2 | 0.5139 [0.4651, 0.5700] | 84 |
| O | prose_sentiment | 44 | Swap | secondary opposite-value following-span control | M2 | 0.1202 [0.0283, 0.2738] | 84 |
| O | prose_sentiment | 44 | P32 | off-contract | M2 | 1.0000 [1.0000, 1.0000] | 84 |
| O | prose_sentiment | 44 | Pfull | off-contract | M2 | 0.9989 [0.9955, 1.0000] | 84 |
| O | prose_sentiment | 40 | F16 | in-contract | M1 | 0.9147 [0.8159, 0.9838] | 84 |
| O | prose_sentiment | 40 | P32 | off-contract | M1 | 0.8475 [0.7664, 0.9331] | 84 |
| O | prose_sentiment | 40 | Pfull | off-contract | M1 | 0.9598 [0.9082, 1.0000] | 84 |
| O | prose_sentiment | 40 | Mis | mismatched following-span control | M1 | 0.5383 [0.4476, 0.6222] | 84 |
| O | prose_sentiment | 40 | Swap | secondary opposite-value following-span control | M1 | 0.0329 [0.0113, 0.0499] | 84 |
| O | prose_sentiment | 40 | F16 | in-contract | M2 | 0.7273 [0.5360, 0.9026] | 84 |
| O | prose_sentiment | 40 | Mis | mismatched following-span control | M2 | 0.5156 [0.4671, 0.5669] | 84 |
| O | prose_sentiment | 40 | Swap | secondary opposite-value following-span control | M2 | 0.1111 [0.0283, 0.2568] | 84 |
| O | prose_sentiment | 40 | P32 | off-contract | M2 | 1.0000 [1.0000, 1.0000] | 84 |
| O | prose_sentiment | 40 | Pfull | off-contract | M2 | 0.9898 [0.9705, 1.0000] | 84 |
| O | python_string | 44 | F16 | in-contract | T | 0.9802 [0.9365, 1.0000] | 84 |
| O | python_string | 40 | F16 | in-contract | T | 0.9802 [0.9365, 1.0000] | 84 |
| O | python_string | 44 | P32 | off-contract | T | 1.0000 [1.0000, 1.0000] | 84 |
| O | python_string | 40 | P32 | off-contract | T | 1.0000 [1.0000, 1.0000] | 84 |
| O | python_string | 44 | Pfull | off-contract | T | 0.9768 [0.9558, 0.9955] | 84 |
| O | python_string | 40 | Pfull | off-contract | T | 0.9768 [0.9558, 0.9955] | 84 |
| O | python_string | 44 | Mis | mismatched following-span control | T | 0.4926 [0.3767, 0.6120] | 84 |
| O | python_string | 40 | Mis | mismatched following-span control | T | 0.4926 [0.3767, 0.6120] | 84 |
| O | python_string | 44 | Swap | secondary opposite-value following-span control | T | 0.9790 [0.9286, 1.0000] | 84 |
| O | python_string | 40 | Swap | secondary opposite-value following-span control | T | 0.9790 [0.9286, 1.0000] | 84 |
| O | python_string | 44 | F16 | in-contract | M1 | 1.0000 [1.0000, 1.0000] | 84 |
| O | python_string | 44 | P32 | off-contract | M1 | 0.7755 [0.7143, 0.8543] | 84 |
| O | python_string | 44 | Pfull | off-contract | M1 | 0.8798 [0.8475, 0.9359] | 84 |
| O | python_string | 44 | Mis | mismatched following-span control | M1 | 0.5230 [0.4393, 0.6006] | 84 |
| O | python_string | 44 | Swap | secondary opposite-value following-span control | M1 | 0.0000 [0.0000, 0.0000] | 84 |
| O | python_string | 44 | F16 | in-contract | M2 | 1.0000 [1.0000, 1.0000] | 84 |
| O | python_string | 44 | Mis | mismatched following-span control | M2 | 0.4728 [0.3866, 0.5607] | 84 |
| O | python_string | 44 | Swap | secondary opposite-value following-span control | M2 | 0.0000 [0.0000, 0.0000] | 84 |
| O | python_string | 44 | P32 | off-contract | M2 | 0.9711 [0.9070, 1.0000] | 84 |
| O | python_string | 44 | Pfull | off-contract | M2 | 0.9994 [0.9977, 1.0000] | 84 |
| O | python_string | 40 | F16 | in-contract | M1 | 1.0000 [1.0000, 1.0000] | 84 |
| O | python_string | 40 | P32 | off-contract | M1 | 0.7783 [0.7443, 0.8537] | 84 |
| O | python_string | 40 | Pfull | off-contract | M1 | 0.9376 [0.8793, 0.9887] | 84 |
| O | python_string | 40 | Mis | mismatched following-span control | M1 | 0.5303 [0.4563, 0.6020] | 84 |
| O | python_string | 40 | Swap | secondary opposite-value following-span control | M1 | 0.0000 [0.0000, 0.0000] | 84 |
| O | python_string | 40 | F16 | in-contract | M2 | 1.0000 [1.0000, 1.0000] | 84 |
| O | python_string | 40 | Mis | mismatched following-span control | M2 | 0.4813 [0.3886, 0.5845] | 84 |
| O | python_string | 40 | Swap | secondary opposite-value following-span control | M2 | 0.0000 [0.0000, 0.0000] | 84 |
| O | python_string | 40 | P32 | off-contract | M2 | 0.9858 [0.9524, 1.0000] | 84 |
| O | python_string | 40 | Pfull | off-contract | M2 | 1.0000 [1.0000, 1.0000] | 84 |
| O | table_column | 44 | F16 | in-contract | T | 0.6383 [0.3759, 0.8771] | 84 |
| O | table_column | 40 | F16 | in-contract | T | 0.6383 [0.3759, 0.8771] | 84 |
| O | table_column | 44 | P32 | off-contract | T | 0.6173 [0.4263, 0.8333] | 84 |
| O | table_column | 40 | P32 | off-contract | T | 0.6173 [0.4263, 0.8333] | 84 |
| O | table_column | 44 | Pfull | off-contract | T | 0.8980 [0.8395, 0.9864] | 84 |
| O | table_column | 40 | Pfull | off-contract | T | 0.8980 [0.8395, 0.9864] | 84 |
| O | table_column | 44 | Mis | mismatched following-span control | T | 0.3433 [0.2885, 0.4051] | 84 |
| O | table_column | 40 | Mis | mismatched following-span control | T | 0.3433 [0.2885, 0.4051] | 84 |
| O | table_column | 44 | Swap | secondary opposite-value following-span control | T | 0.9603 [0.9257, 0.9881] | 84 |
| O | table_column | 40 | Swap | secondary opposite-value following-span control | T | 0.9603 [0.9257, 0.9881] | 84 |
| O | table_column | 44 | F16 | in-contract | M1 | 0.6037 [0.4529, 0.7823] | 84 |
| O | table_column | 44 | P32 | off-contract | M1 | 0.2177 [0.0539, 0.4382] | 84 |
| O | table_column | 44 | Pfull | off-contract | M1 | 0.5578 [0.4138, 0.7063] | 84 |
| O | table_column | 44 | Mis | mismatched following-span control | M1 | 0.5652 [0.4246, 0.6715] | 84 |
| O | table_column | 44 | Swap | secondary opposite-value following-span control | M1 | 0.3141 [0.2211, 0.4189] | 84 |
| O | table_column | 44 | F16 | in-contract | M2 | 0.6752 [0.4342, 0.8912] | 84 |
| O | table_column | 44 | Mis | mismatched following-span control | M2 | 0.4906 [0.3841, 0.6247] | 84 |
| O | table_column | 44 | Swap | secondary opposite-value following-span control | M2 | 0.0612 [0.0147, 0.1117] | 84 |
| O | table_column | 44 | P32 | off-contract | M2 | 0.7608 [0.5822, 0.9592] | 84 |
| O | table_column | 44 | Pfull | off-contract | M2 | 0.8163 [0.7347, 0.9717] | 84 |
| O | table_column | 40 | F16 | in-contract | M1 | 0.6100 [0.4660, 0.7869] | 84 |
| O | table_column | 40 | P32 | off-contract | M1 | 0.2630 [0.0731, 0.5159] | 84 |
| O | table_column | 40 | Pfull | off-contract | M1 | 0.5726 [0.4042, 0.7052] | 84 |
| O | table_column | 40 | Mis | mismatched following-span control | M1 | 0.5680 [0.4498, 0.6574] | 84 |
| O | table_column | 40 | Swap | secondary opposite-value following-span control | M1 | 0.2971 [0.1916, 0.3906] | 84 |
| O | table_column | 40 | F16 | in-contract | M2 | 0.6361 [0.4195, 0.8622] | 84 |
| O | table_column | 40 | Mis | mismatched following-span control | M2 | 0.4782 [0.3849, 0.6035] | 84 |
| O | table_column | 40 | Swap | secondary opposite-value following-span control | M2 | 0.0794 [0.0255, 0.1287] | 84 |
| O | table_column | 40 | P32 | off-contract | M2 | 0.7574 [0.5465, 0.9559] | 84 |
| O | table_column | 40 | Pfull | off-contract | M2 | 0.8339 [0.7511, 0.9881] | 84 |
| S | list_index | 44 | F16 | in-contract | T | 0.6360 [0.5499, 0.7186] | 160 |
| S | list_index | 40 | F16 | in-contract | T | 0.6360 [0.5499, 0.7186] | 160 |
| S | list_index | 44 | P32 | off-contract | T | 0.9805 [0.9626, 0.9931] | 160 |
| S | list_index | 40 | P32 | off-contract | T | 0.9805 [0.9626, 0.9931] | 160 |
| S | list_index | 44 | Pfull | off-contract | T | 0.9350 [0.8976, 0.9656] | 160 |
| S | list_index | 40 | Pfull | off-contract | T | 0.9350 [0.8976, 0.9656] | 160 |
| S | list_index | 44 | Mis | mismatched following-span control | T | 0.5190 [0.4240, 0.6078] | 160 |
| S | list_index | 40 | Mis | mismatched following-span control | T | 0.5190 [0.4240, 0.6078] | 160 |
| S | list_index | 44 | Swap | secondary opposite-value following-span control | T | 0.7323 [0.6566, 0.8054] | 160 |
| S | list_index | 40 | Swap | secondary opposite-value following-span control | T | 0.7323 [0.6566, 0.8054] | 160 |
| S | list_index | 44 | F16 | in-contract | M1 | 0.6130 [0.5223, 0.6997] | 160 |
| S | list_index | 44 | P32 | off-contract | M1 | 0.7434 [0.6568, 0.8195] | 160 |
| S | list_index | 44 | Pfull | off-contract | M1 | 0.7022 [0.6176, 0.7757] | 160 |
| S | list_index | 44 | Mis | mismatched following-span control | M1 | 0.5027 [0.4106, 0.5931] | 160 |
| S | list_index | 44 | Swap | secondary opposite-value following-span control | M1 | 0.2897 [0.2068, 0.3738] | 160 |
| S | list_index | 44 | F16 | in-contract | M2 | 0.8068 [0.7433, 0.8623] | 200 |
| S | list_index | 44 | Mis | mismatched following-span control | M2 | 0.5202 [0.4406, 0.6020] | 200 |
| S | list_index | 44 | Swap | secondary opposite-value following-span control | M2 | 0.0191 [0.0012, 0.0462] | 200 |
| S | list_index | 44 | P32 | off-contract | M2 | 0.9965 [0.9880, 1.0000] | 200 |
| S | list_index | 44 | Pfull | off-contract | M2 | 1.0000 [1.0000, 1.0000] | 200 |
| S | list_index | 40 | F16 | in-contract | M1 | 0.5542 [0.4663, 0.6428] | 160 |
| S | list_index | 40 | P32 | off-contract | M1 | 0.6994 [0.6072, 0.7825] | 160 |
| S | list_index | 40 | Pfull | off-contract | M1 | 0.7253 [0.6417, 0.7984] | 160 |
| S | list_index | 40 | Mis | mismatched following-span control | M1 | 0.5045 [0.4141, 0.5933] | 160 |
| S | list_index | 40 | Swap | secondary opposite-value following-span control | M1 | 0.3259 [0.2421, 0.4130] | 160 |
| S | list_index | 40 | F16 | in-contract | M2 | 0.8222 [0.7618, 0.8793] | 200 |
| S | list_index | 40 | Mis | mismatched following-span control | M2 | 0.5195 [0.4408, 0.5980] | 200 |
| S | list_index | 40 | Swap | secondary opposite-value following-span control | M2 | 0.0188 [0.0017, 0.0441] | 200 |
| S | list_index | 40 | P32 | off-contract | M2 | 0.9973 [0.9906, 1.0000] | 200 |
| S | list_index | 40 | Pfull | off-contract | M2 | 1.0000 [1.0000, 1.0000] | 200 |
| S | prose_paren | 44 | F16 | in-contract | T | 0.5984 [0.5114, 0.6837] | 160 |
| S | prose_paren | 40 | F16 | in-contract | T | 0.5984 [0.5114, 0.6837] | 160 |
| S | prose_paren | 44 | P32 | off-contract | T | 0.6209 [0.5314, 0.7024] | 160 |
| S | prose_paren | 40 | P32 | off-contract | T | 0.6209 [0.5314, 0.7024] | 160 |
| S | prose_paren | 44 | Pfull | off-contract | T | 0.6645 [0.5781, 0.7459] | 160 |
| S | prose_paren | 40 | Pfull | off-contract | T | 0.6645 [0.5781, 0.7459] | 160 |
| S | prose_paren | 44 | Mis | mismatched following-span control | T | 0.5008 [0.4089, 0.5848] | 160 |
| S | prose_paren | 40 | Mis | mismatched following-span control | T | 0.5008 [0.4089, 0.5848] | 160 |
| S | prose_paren | 44 | Swap | secondary opposite-value following-span control | T | 0.7288 [0.6486, 0.7991] | 160 |
| S | prose_paren | 40 | Swap | secondary opposite-value following-span control | T | 0.7288 [0.6486, 0.7991] | 160 |
| S | prose_paren | 44 | F16 | in-contract | M1 | 0.8903 [0.8428, 0.9355] | 160 |
| S | prose_paren | 44 | P32 | off-contract | M1 | 0.4094 [0.3240, 0.5003] | 160 |
| S | prose_paren | 44 | Pfull | off-contract | M1 | 0.4727 [0.3835, 0.5571] | 160 |
| S | prose_paren | 44 | Mis | mismatched following-span control | M1 | 0.5584 [0.4681, 0.6505] | 160 |
| S | prose_paren | 44 | Swap | secondary opposite-value following-span control | M1 | 0.0734 [0.0384, 0.1144] | 160 |
| S | prose_paren | 44 | F16 | in-contract | M2 | 0.9882 [0.9757, 0.9975] | 200 |
| S | prose_paren | 44 | Mis | mismatched following-span control | M2 | 0.5257 [0.4467, 0.6070] | 200 |
| S | prose_paren | 44 | Swap | secondary opposite-value following-span control | M2 | 0.0002 [0.0000, 0.0010] | 200 |
| S | prose_paren | 44 | P32 | off-contract | M2 | 0.5660 [0.4882, 0.6458] | 200 |
| S | prose_paren | 44 | Pfull | off-contract | M2 | 0.6709 [0.5900, 0.7454] | 200 |
| S | prose_paren | 40 | F16 | in-contract | M1 | 0.8550 [0.7998, 0.9104] | 160 |
| S | prose_paren | 40 | P32 | off-contract | M1 | 0.4419 [0.3573, 0.5288] | 160 |
| S | prose_paren | 40 | Pfull | off-contract | M1 | 0.4770 [0.3859, 0.5669] | 160 |
| S | prose_paren | 40 | Mis | mismatched following-span control | M1 | 0.5303 [0.4421, 0.6217] | 160 |
| S | prose_paren | 40 | Swap | secondary opposite-value following-span control | M1 | 0.0838 [0.0451, 0.1321] | 160 |
| S | prose_paren | 40 | F16 | in-contract | M2 | 0.9801 [0.9619, 0.9935] | 200 |
| S | prose_paren | 40 | Mis | mismatched following-span control | M2 | 0.5235 [0.4435, 0.6029] | 200 |
| S | prose_paren | 40 | Swap | secondary opposite-value following-span control | M2 | 0.0003 [0.0000, 0.0012] | 200 |
| S | prose_paren | 40 | P32 | off-contract | M2 | 0.5630 [0.4822, 0.6430] | 200 |
| S | prose_paren | 40 | Pfull | off-contract | M2 | 0.6788 [0.6025, 0.7518] | 200 |
| S | table_column | 44 | F16 | in-contract | T | 0.4655 [0.3771, 0.5556] | 160 |
| S | table_column | 40 | F16 | in-contract | T | 0.4655 [0.3771, 0.5556] | 160 |
| S | table_column | 44 | P32 | off-contract | T | 0.5041 [0.4120, 0.5900] | 160 |
| S | table_column | 40 | P32 | off-contract | T | 0.5041 [0.4120, 0.5900] | 160 |
| S | table_column | 44 | Pfull | off-contract | T | 0.6067 [0.5142, 0.6913] | 160 |
| S | table_column | 40 | Pfull | off-contract | T | 0.6067 [0.5142, 0.6913] | 160 |
| S | table_column | 44 | Mis | mismatched following-span control | T | 0.5215 [0.4318, 0.6108] | 160 |
| S | table_column | 40 | Mis | mismatched following-span control | T | 0.5215 [0.4318, 0.6108] | 160 |
| S | table_column | 44 | Swap | secondary opposite-value following-span control | T | 0.7094 [0.6236, 0.7854] | 160 |
| S | table_column | 40 | Swap | secondary opposite-value following-span control | T | 0.7094 [0.6236, 0.7854] | 160 |
| S | table_column | 44 | F16 | in-contract | M1 | 0.9714 [0.9491, 0.9883] | 160 |
| S | table_column | 44 | P32 | off-contract | M1 | 0.4331 [0.3437, 0.5180] | 160 |
| S | table_column | 44 | Pfull | off-contract | M1 | 0.5336 [0.4449, 0.6267] | 160 |
| S | table_column | 44 | Mis | mismatched following-span control | M1 | 0.5399 [0.4509, 0.6312] | 160 |
| S | table_column | 44 | Swap | secondary opposite-value following-span control | M1 | 0.0272 [0.0111, 0.0509] | 160 |
| S | table_column | 44 | F16 | in-contract | M2 | 1.0000 [1.0000, 1.0000] | 200 |
| S | table_column | 44 | Mis | mismatched following-span control | M2 | 0.5150 [0.4364, 0.5964] | 200 |
| S | table_column | 44 | Swap | secondary opposite-value following-span control | M2 | 0.0000 [0.0000, 0.0000] | 200 |
| S | table_column | 44 | P32 | off-contract | M2 | 0.9062 [0.8659, 0.9438] | 200 |
| S | table_column | 44 | Pfull | off-contract | M2 | 0.9220 [0.8824, 0.9545] | 200 |
| S | table_column | 40 | F16 | in-contract | M1 | 0.9572 [0.9269, 0.9804] | 160 |
| S | table_column | 40 | P32 | off-contract | M1 | 0.4309 [0.3433, 0.5169] | 160 |
| S | table_column | 40 | Pfull | off-contract | M1 | 0.4933 [0.4066, 0.5874] | 160 |
| S | table_column | 40 | Mis | mismatched following-span control | M1 | 0.5407 [0.4532, 0.6317] | 160 |
| S | table_column | 40 | Swap | secondary opposite-value following-span control | M1 | 0.0417 [0.0183, 0.0727] | 160 |
| S | table_column | 40 | F16 | in-contract | M2 | 1.0000 [1.0000, 1.0000] | 200 |
| S | table_column | 40 | Mis | mismatched following-span control | M2 | 0.5201 [0.4421, 0.6001] | 200 |
| S | table_column | 40 | Swap | secondary opposite-value following-span control | M2 | 0.0000 [0.0000, 0.0000] | 200 |
| S | table_column | 40 | P32 | off-contract | M2 | 0.9128 [0.8718, 0.9490] | 200 |
| S | table_column | 40 | Pfull | off-contract | M2 | 0.9097 [0.8670, 0.9452] | 200 |
