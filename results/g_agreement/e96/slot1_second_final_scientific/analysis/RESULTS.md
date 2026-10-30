# E96 inference-time scaffold

Integrator provisional R-SC1: **NOT EVALUABLE**. Falsifier: **NOT MET**. R-4 review pending.

§204 regex primary on full40 items for rows with registered value regex; otherwise judge on registered item subsample. Always report whole-bank regex beside combined regex+judge subsample sensitivity; never choose channel by results.

| Bank / row | Reader | J group | Primary | S greedy | Δ majority [95% CI] | Δ recon [95% CI] |
|---|---|---|---|---:|---:|---:|
| E49/container_after_move | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E49/container_after_move | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E49/branch_taken | oracle | OUT-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |
| E49/branch_taken | nla | OUT-J | regex_whole | -0.075 | 0.125 [-0.050, 0.300] (n=40) | 0.000 [-0.175, 0.175] (n=40) |
| E49/var_type_at_use | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E49/var_type_at_use | nla | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E49/asserted_vs_hypothetical | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E49/asserted_vs_hypothetical | nla | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E49/user_expertise | oracle | IN-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |
| E49/user_expertise | nla | IN-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |
| E49/unit_system | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E49/unit_system | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/multi_token_entity | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/multi_token_entity | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/focus_think | oracle | IN-J | regex_whole | 0.150 | 0.150 [0.050, 0.275] (n=40) | 0.025 [-0.100, 0.150] (n=40) |
| E57/focus_think | nla | IN-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.050 [0.000, 0.125] (n=40) |
| E57/focus_mention | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/focus_mention | nla | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/focus_ignore | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/focus_ignore | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/antonym_crosslingual | oracle | IN-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |
| E57/antonym_crosslingual | nla | IN-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |
| E57/linewrap_implicit | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/linewrap_implicit | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/linewrap_asked | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/linewrap_asked | nla | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/count_gradient_first_letter | oracle | OUT-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |
| E57/count_gradient_first_letter | nla | OUT-J | regex_whole | 0.100 | -0.100 [-0.225, 0.025] (n=40) | -0.100 [-0.250, 0.050] (n=40) |
| E57/two_hop_answer | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/two_hop_answer | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/subject_number | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/subject_number | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/clause_pending | oracle | IN-J | judge_subsample | 0.100 | 0.167 [0.000, 0.500] (n=6) | 0.000 [-0.300, 0.300] (n=10) |
| E57/clause_pending | nla | IN-J | judge_subsample | 0.075 | -0.031 [-0.156, 0.062] (n=32) | 0.200 [0.050, 0.375] (n=40) |
| E57/nesting_depth | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/nesting_depth | nla | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/indent_level | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/indent_level | nla | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/loop_direction | oracle | IN-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |
| E57/loop_direction | nla | IN-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.050 [0.000, 0.125] (n=40) |
| E57/page_range_digit | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/page_range_digit | nla | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/section_header | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/section_header | nla | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E57/sentiment_judgement | oracle | IN-J | regex_whole | 0.450 | 0.025 [-0.150, 0.200] (n=40) | -0.125 [-0.300, 0.075] (n=40) |
| E57/sentiment_judgement | nla | IN-J | regex_whole | 0.500 | 0.250 [0.125, 0.375] (n=40) | 0.175 [0.000, 0.375] (n=40) |
| E59/format_plan | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E59/format_plan | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E59/language_plan | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E59/language_plan | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E59/stance_plan | oracle | IN-J | regex_whole | 0.400 | 0.050 [0.000, 0.125] (n=40) | -0.150 [-0.275, -0.025] (n=40) |
| E59/stance_plan | nla | IN-J | regex_whole | 0.050 | -0.025 [-0.125, 0.050] (n=40) | 0.025 [-0.125, 0.151] (n=40) |
| E59/length_plan | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E59/length_plan | nla | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E59/hedge_plan | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E59/hedge_plan | nla | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E59/decline_plan | oracle | IN-J | regex_whole | 0.025 | -0.050 [-0.125, 0.000] (n=40) | -0.025 [-0.125, 0.100] (n=40) |
| E59/decline_plan | nla | IN-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | -0.025 [-0.075, 0.000] (n=40) |
| E62/S1_L0 | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S1_L1 | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S1_L2 | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S1_L3 | oracle | IN-J | regex_whole | -0.025 | 0.025 [0.000, 0.075] (n=40) | 0.025 [-0.050, 0.100] (n=40) |
| E62/S1_L4 | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S2_L0 | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S2_L1 | oracle | IN-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |
| E62/S2_L2 | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S2_L3 | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S2_L4 | oracle | OUT-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |
| E62/S3_L0 | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S3_L1 | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S3_L2 | oracle | OUT-J | regex_whole | 0.075 | 0.050 [-0.075, 0.175] (n=40) | 0.100 [-0.051, 0.275] (n=40) |
| E62/S3_L3 | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S3_L4 | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S4_L0 | oracle | IN-J | regex_whole | 0.600 | 0.100 [-0.050, 0.275] (n=40) | 0.050 [-0.125, 0.250] (n=40) |
| E62/S4_L1 | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S4_L2 | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S4_L3 | oracle | IN-J | regex_whole | 0.200 | 0.300 [0.100, 0.500] (n=40) | -0.025 [-0.225, 0.175] (n=40) |
| E62/S4_L4 | oracle | OUT-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S5_L0 | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S5_L1 | oracle | IN-J | regex_whole | 0.050 | -0.050 [-0.175, 0.075] (n=40) | -0.025 [-0.150, 0.100] (n=40) |
| E62/S5_L2 | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S5_L3 | oracle | IN-J | regex_whole | N/A | NOT EVALUABLE | NOT EVALUABLE |
| E62/S5_L4 | oracle | OUT-J | regex_whole | 0.000 | 0.000 [0.000, 0.000] (n=40) | 0.000 [0.000, 0.000] (n=40) |

Eight controls and25 E62 NLA cells are NOT EVALUABLE under clarification1. Any-of16 is descriptive only. Whole-bank regex, combined regex+judge subsample, matched original-rubric25% and redaction sensitivities are in RESULTS.json. No channel is selected after its result.

first_output_utc: 2026-10-29T05:26:13.307062+00:00; first sampling output: 2026-10-28T23:52:37.034508+00:00; first judgment output: 2026-10-29T03:22:55.943332+00:00.
