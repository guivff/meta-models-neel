# R-A prior / buffer / residual decomposition

Signed AUROC accounting; this is not a causal mediation decomposition.

Intervals are the conservative envelope of the paired item and corpus bootstraps. Confidence memberships are frozen conditional strata.

| Reader | Tag | Stratum | Items / facts | Prior | Buffer | Residual [95% CI] | q residual / equivalence | Verdict |
|---|---|---|---:|---:|---:|---|---|---|
| olens | COMPUTED | ALL | 3400 / 17 | 0.4921 | +0.0329 | +0.2164 [+0.1384, +0.2984] | 0.003733 / 1 | RESIDUAL_CONFIRMED |
| olens | COMPUTED | low | 1611 / 17 | 0.4938 | +0.0293 | +0.1025 [+0.0221, +0.1846] | 0.0845 / 1 | NOT_DISTINGUISHED |
| olens | COMPUTED | middle | 1363 / 16 | 0.4884 | +0.0295 | +0.2907 [+0.1906, +0.3972] | 0.003733 / 1 | RESIDUAL_CONFIRMED |
| olens | COMPUTED | high | 380 / 9 | 0.5854 | +0.0356 | +0.2739 [+0.0960, +0.4353] | 0.00448 / 1 | RESIDUAL_CONFIRMED |
| olens | FORM | ALL | 1200 / 6 | 0.5149 | -0.0149 | +0.0899 [-0.0069, +0.1850] | 0.2187 / 1 | NOT_DISTINGUISHED |
| olens | FORM | low | 559 / 6 | 0.4835 | -0.0581 | +0.1145 [-0.0601, +0.2928] | 0.5322 / 1 | NOT_DISTINGUISHED |
| olens | FORM | middle | 484 / 6 | 0.5439 | +0.0129 | +0.0751 [-0.1201, +0.2354] | 0.905 / 1 | NOT_DISTINGUISHED |
| olens | FORM | high | 138 / 3 | 0.4888 | +0.1149 | -0.1587 [-0.6667, +0.2709] | 1 / 1 | NOT_DISTINGUISHED |
| olens | KNOWLEDGE | ALL | 4200 / 21 | 0.5097 | +0.0322 | +0.1575 [+0.1037, +0.2422] | 0.005599 / 1 | RESIDUAL_CONFIRMED |
| olens | KNOWLEDGE | low | 2261 / 20 | 0.5028 | -0.0014 | +0.0656 [-0.2180, +0.1581] | 0.4453 / 1 | NOT_DISTINGUISHED |
| olens | KNOWLEDGE | middle | 1017 / 21 | 0.5337 | +0.0156 | +0.1543 [+0.0117, +0.2617] | 0.03808 / 1 | RESIDUAL_CONFIRMED |
| olens | KNOWLEDGE | high | 532 / 7 | 0.6440 | +0.0161 | +0.2637 [-0.1579, +0.4191] | 0.00448 / 1 | NOT_DISTINGUISHED |
| olens | META | ALL | 926 / 6 | 0.4691 | +0.0211 | +0.1353 [-0.0425, +0.3132] | 0.4453 / 1 | NOT_DISTINGUISHED |
| olens | META | low | 368 / 6 | 0.4422 | +0.0321 | +0.1175 [-0.1063, +0.3441] | 0.7284 / 1 | NOT_DISTINGUISHED |
| olens | META | middle | 331 / 6 | 0.3689 | +0.0638 | +0.2543 [+0.0146, +0.4951] | 0.1736 / 1 | NOT_DISTINGUISHED |
| olens | META | high | 146 / 2 | 0.5930 | -0.2330 | +0.3370 [+0.2121, +0.4545] | 0.003733 / 1 | RESIDUAL_CONFIRMED |
| olens | PASSAGE-KNOWLEDGE | ALL | 1800 / 9 | 0.4714 | +0.0338 | +0.0982 [+0.0298, +0.1680] | 0.03808 / 1 | RESIDUAL_CONFIRMED |
| olens | PASSAGE-KNOWLEDGE | low | 711 / 9 | 0.4851 | -0.0007 | +0.0886 [-0.0024, +0.1814] | 0.2128 / 1 | NOT_DISTINGUISHED |
| olens | PASSAGE-KNOWLEDGE | middle | 985 / 9 | 0.4715 | +0.0318 | +0.0977 [+0.0005, +0.1957] | 0.1926 / 1 | NOT_DISTINGUISHED |
| olens | PASSAGE-KNOWLEDGE | high | 81 / 6 | 0.4664 | +0.0329 | +0.2088 [-0.1511, +0.5115] | 0.5019 / 1 | NOT_DISTINGUISHED |
| olens | SURFACE | ALL | 5600 / 28 | 0.4816 | +0.0623 | +0.1974 [-0.2961, +0.3783] | 0.1213 / 1 | NOT_DISTINGUISHED |
| olens | SURFACE | low | 181 / 13 | 0.5530 | -0.0113 | +0.0882 [-0.1933, +0.2788] | 0.7951 / 1 | NOT_DISTINGUISHED |
| olens | SURFACE | middle | 1230 / 27 | 0.4987 | +0.0755 | +0.1632 [-0.3045, +0.2774] | 0.03808 / 1 | NOT_DISTINGUISHED |
| olens | SURFACE | high | 4003 / 27 | 0.4765 | +0.0774 | +0.2381 [+0.1643, +0.4732] | 0.1736 / 1 | NOT_DISTINGUISHED |
| olens | TOPIC | ALL | 4072 / 21 | 0.5189 | +0.0047 | +0.0800 [-0.0387, +0.1762] | 0.3283 / 1 | NOT_DISTINGUISHED |
| olens | TOPIC | low | 1150 / 20 | 0.5187 | -0.0073 | +0.0676 [-0.0924, +0.2457] | 0.8701 / 1 | NOT_DISTINGUISHED |
| olens | TOPIC | middle | 1625 / 21 | 0.4915 | +0.0090 | +0.0878 [-0.0345, +0.1979] | 0.3283 / 1 | NOT_DISTINGUISHED |
| olens | TOPIC | high | 1218 / 17 | 0.4845 | +0.0168 | +0.2263 [+0.0746, +0.3792] | 0.03808 / 1 | RESIDUAL_CONFIRMED |
| ao | COMPUTED | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | COMPUTED | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | COMPUTED | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | COMPUTED | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | FORM | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | FORM | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | FORM | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | FORM | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | KNOWLEDGE | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | KNOWLEDGE | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | KNOWLEDGE | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | KNOWLEDGE | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | META | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | META | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | META | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | META | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | PASSAGE-KNOWLEDGE | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | PASSAGE-KNOWLEDGE | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | PASSAGE-KNOWLEDGE | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | PASSAGE-KNOWLEDGE | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | SURFACE | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | SURFACE | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | SURFACE | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | SURFACE | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | TOPIC | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | TOPIC | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | TOPIC | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| ao | TOPIC | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | COMPUTED | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | COMPUTED | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | COMPUTED | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | COMPUTED | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | FORM | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | FORM | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | FORM | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | FORM | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | KNOWLEDGE | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | KNOWLEDGE | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | KNOWLEDGE | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | KNOWLEDGE | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | META | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | META | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | META | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | META | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | PASSAGE-KNOWLEDGE | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | PASSAGE-KNOWLEDGE | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | PASSAGE-KNOWLEDGE | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | PASSAGE-KNOWLEDGE | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | SURFACE | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | SURFACE | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | SURFACE | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | SURFACE | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | TOPIC | ALL | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | TOPIC | low | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | TOPIC | middle | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| nla | TOPIC | high | — | — | — | — | 1 / 1 | NOT_RUN_INCOMPLETE |
| jpp | COMPUTED | ALL | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | COMPUTED | low | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | COMPUTED | middle | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | COMPUTED | high | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | FORM | ALL | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | FORM | low | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | FORM | middle | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | FORM | high | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | KNOWLEDGE | ALL | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | KNOWLEDGE | low | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | KNOWLEDGE | middle | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | KNOWLEDGE | high | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | META | ALL | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | META | low | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | META | middle | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | META | high | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | PASSAGE-KNOWLEDGE | ALL | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | PASSAGE-KNOWLEDGE | low | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | PASSAGE-KNOWLEDGE | middle | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | PASSAGE-KNOWLEDGE | high | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | SURFACE | ALL | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | SURFACE | low | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | SURFACE | middle | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | SURFACE | high | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | TOPIC | ALL | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | TOPIC | low | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | TOPIC | middle | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |
| jpp | TOPIC | high | — | — | — | — | 1 / 1 | NOT_DEFINED_NO_PROMPT_CHANNEL |

The LR256 line has limited support. The following point comparisons hold every arm and both reference lines to the exact probe-matched support; these do not replace the full-population endpoint.

| Reader | Tag | Stratum | Matched items / facts | True state | Text+shuffled | Prompt-only | LR256 |
|---|---|---|---:|---:|---:|---:|---:|
| olens | COMPUTED | ALL | 3400 / 17 | 0.7413 | 0.5250 | 0.9152 | 0.9217 |
| olens | COMPUTED | low | 1611 / 17 | 0.6256 | 0.5231 | 0.7995 | 0.8362 |
| olens | COMPUTED | middle | 1363 / 16 | 0.8086 | 0.5179 | 0.9415 | 0.9510 |
| olens | COMPUTED | high | 380 / 9 | 0.8949 | 0.6210 | 0.9612 | 0.9798 |
| olens | FORM | ALL | 1200 / 6 | 0.5898 | 0.5000 | 0.8634 | 0.9212 |
| olens | FORM | low | 559 / 6 | 0.5398 | 0.4253 | 0.7490 | 0.8810 |
| olens | FORM | middle | 484 / 6 | 0.6319 | 0.5568 | 0.7860 | 0.9306 |
| olens | FORM | high | 138 / 3 | 0.4450 | 0.6037 | 0.9877 | 0.9804 |
| olens | KNOWLEDGE | ALL | 4200 / 21 | 0.6994 | 0.5419 | 0.8977 | 0.8328 |
| olens | KNOWLEDGE | low | 2261 / 20 | 0.5670 | 0.5014 | 0.8008 | 0.7438 |
| olens | KNOWLEDGE | middle | 1017 / 21 | 0.7035 | 0.5492 | 0.9582 | 0.9242 |
| olens | KNOWLEDGE | high | 532 / 7 | 0.9237 | 0.6600 | 0.9628 | 0.9610 |
| olens | META | ALL | 600 / 3 | 0.7162 | 0.4807 | 0.9702 | 0.9864 |
| olens | META | low | 159 / 3 | 0.6744 | 0.4373 | 0.8635 | 0.9879 |
| olens | META | middle | 271 / 3 | 0.7015 | 0.4700 | 0.9652 | 0.9811 |
| olens | META | high | 146 / 2 | 0.6969 | 0.3600 | 0.8030 | 1.0000 |
| olens | PASSAGE-KNOWLEDGE | ALL | 1800 / 9 | 0.6034 | 0.5051 | 0.8168 | 0.7767 |
| olens | PASSAGE-KNOWLEDGE | low | 711 / 9 | 0.5730 | 0.4844 | 0.7217 | 0.7232 |
| olens | PASSAGE-KNOWLEDGE | middle | 985 / 9 | 0.6010 | 0.5033 | 0.7962 | 0.7814 |
| olens | PASSAGE-KNOWLEDGE | high | 81 / 6 | 0.7081 | 0.4993 | 0.8821 | 0.9040 |
| olens | SURFACE | ALL | 5600 / 28 | 0.7414 | 0.5440 | 0.9981 | 0.9127 |
| olens | SURFACE | low | 181 / 13 | 0.6300 | 0.5418 | 0.7773 | 0.5944 |
| olens | SURFACE | middle | 1230 / 27 | 0.7374 | 0.5741 | 0.9947 | 0.8822 |
| olens | SURFACE | high | 4003 / 27 | 0.7920 | 0.5539 | 0.9989 | 0.9173 |
| olens | TOPIC | ALL | 3600 / 18 | 0.6211 | 0.5262 | 0.8553 | 0.8771 |
| olens | TOPIC | low | 1095 / 17 | 0.5932 | 0.4912 | 0.7559 | 0.8106 |
| olens | TOPIC | middle | 1316 / 18 | 0.6045 | 0.4996 | 0.8613 | 0.8823 |
| olens | TOPIC | high | 1110 / 14 | 0.7680 | 0.5147 | 0.8832 | 0.9167 |
| jpp | COMPUTED | ALL | 3400 / 17 | 0.7139 | undefined | 0.9152 | 0.9217 |
| jpp | COMPUTED | low | 1611 / 17 | 0.6200 | undefined | 0.7995 | 0.8362 |
| jpp | COMPUTED | middle | 1363 / 16 | 0.7448 | undefined | 0.9415 | 0.9510 |
| jpp | COMPUTED | high | 380 / 9 | 0.7164 | undefined | 0.9612 | 0.9798 |
| jpp | FORM | ALL | 1200 / 6 | 0.6022 | undefined | 0.8634 | 0.9212 |
| jpp | FORM | low | 559 / 6 | 0.5074 | undefined | 0.7490 | 0.8810 |
| jpp | FORM | middle | 484 / 6 | 0.5563 | undefined | 0.7860 | 0.9306 |
| jpp | FORM | high | 138 / 3 | 0.9194 | undefined | 0.9877 | 0.9804 |
| jpp | KNOWLEDGE | ALL | 4200 / 21 | 0.6974 | undefined | 0.8977 | 0.8328 |
| jpp | KNOWLEDGE | low | 2261 / 20 | 0.5747 | undefined | 0.8008 | 0.7438 |
| jpp | KNOWLEDGE | middle | 1017 / 21 | 0.6867 | undefined | 0.9582 | 0.9242 |
| jpp | KNOWLEDGE | high | 532 / 7 | 0.8309 | undefined | 0.9628 | 0.9610 |
| jpp | META | ALL | 600 / 3 | 0.7723 | undefined | 0.9702 | 0.9864 |
| jpp | META | low | 159 / 3 | 0.6460 | undefined | 0.8635 | 0.9879 |
| jpp | META | middle | 271 / 3 | 0.8147 | undefined | 0.9652 | 0.9811 |
| jpp | META | high | 146 / 2 | 0.8405 | undefined | 0.8030 | 1.0000 |
| jpp | PASSAGE-KNOWLEDGE | ALL | 1800 / 9 | 0.6169 | undefined | 0.8168 | 0.7767 |
| jpp | PASSAGE-KNOWLEDGE | low | 711 / 9 | 0.5639 | undefined | 0.7217 | 0.7232 |
| jpp | PASSAGE-KNOWLEDGE | middle | 985 / 9 | 0.5978 | undefined | 0.7962 | 0.7814 |
| jpp | PASSAGE-KNOWLEDGE | high | 81 / 6 | 0.7411 | undefined | 0.8821 | 0.9040 |
| jpp | SURFACE | ALL | 5600 / 28 | 0.6562 | undefined | 0.9981 | 0.9127 |
| jpp | SURFACE | low | 181 / 13 | 0.4293 | undefined | 0.7773 | 0.5944 |
| jpp | SURFACE | middle | 1230 / 27 | 0.6674 | undefined | 0.9947 | 0.8822 |
| jpp | SURFACE | high | 4003 / 27 | 0.6992 | undefined | 0.9989 | 0.9173 |
| jpp | TOPIC | ALL | 3600 / 18 | 0.6832 | undefined | 0.8553 | 0.8771 |
| jpp | TOPIC | low | 1095 / 17 | 0.6372 | undefined | 0.7559 | 0.8106 |
| jpp | TOPIC | middle | 1316 / 18 | 0.6412 | undefined | 0.8613 | 0.8823 |
| jpp | TOPIC | high | 1110 / 14 | 0.8172 | undefined | 0.8832 | 0.9167 |

Full constituent 90%/95% intervals, conditional-state contrasts, class-support exclusions, raw threshold flags, and provenance are preserved in analysis.RA41.json. Unavailable cells retain p=1 in both fixed 112-cell BH families.
