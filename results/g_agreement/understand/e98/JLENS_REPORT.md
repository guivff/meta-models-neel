# E98 prospective J forecast — Qwen3-4B block18

CPU only; captured first, forecast committed before Oracle output/GO. Descriptive replication; no native outcomes accessed.

All26 ported rows accounted:23 binary forecasts/1932 test items;3 nonbinary exclusions/252 items;0 port drops. Labels: {'DIFFUSE': 15, 'IN-J': 6, 'OUT-J': 2}. Oracle REPORTED iff IN-J.

| Bank | Row | J fraction | Label | Oracle forecast |
|---|---|---:|---|---|
| E57 | antonym_crosslingual | 0.041582327 | DIFFUSE | MISSED |
| E57 | clause_pending | 0.045061986 | IN-J | REPORTED |
| E57 | count_gradient_first_letter | 0.047462003 | DIFFUSE | MISSED |
| E57 | focus_ignore | 0.045981335 | IN-J | REPORTED |
| E57 | focus_mention | 0.030473298 | DIFFUSE | MISSED |
| E57 | focus_think | 0.026012519 | OUT-J | MISSED |
| E57 | indent_level | 0.044833373 | DIFFUSE | MISSED |
| E57 | linewrap_asked | 0.039036769 | DIFFUSE | MISSED |
| E57 | linewrap_implicit | 0.053324282 | DIFFUSE | MISSED |
| E57 | loop_direction | 0.040774871 | IN-J | REPORTED |
| E57 | multi_token_entity | 0.059181639 | IN-J | REPORTED |
| E57 | nesting_depth | 0.054933260 | DIFFUSE | MISSED |
| E57 | page_range_digit | 0.027438604 | OUT-J | MISSED |
| E57 | section_header | 0.031298847 | DIFFUSE | MISSED |
| E57 | sentiment_judgement | 0.058796706 | IN-J | REPORTED |
| E57 | subject_number | 0.067239566 | DIFFUSE | MISSED |
| E57 | two_hop_answer | 0.036364076 | DIFFUSE | MISSED |
| E59 | decline_plan | 0.033350179 | DIFFUSE | MISSED |
| E59 | format_plan | 0.037366258 | DIFFUSE | MISSED |
| E59 | hedge_plan | 0.038014661 | DIFFUSE | MISSED |
| E59 | language_plan | 0.033989929 | DIFFUSE | MISSED |
| E59 | length_plan | 0.030287344 | DIFFUSE | MISSED |
| E59 | stance_plan | 0.042385790 | IN-J | REPORTED |

Exclusions: E57/capacity_list, E57/category_switch, E57/focus_none. Original nonbinary definitions retained.

Frozen token-side empty/G3 NOT EVALUABLE rows: E57/clause_pending, E57/loop_direction, E57/multi_token_entity. No synonyms or backfill. Missing G3 follows the unchanged sparse primary-label policy.

200-direction k16 null: median=0.0301171027891;97.5th=0.0399773357291. Seed20261027, refine_steps6. Model-specific basis W_U diag(Qwen3 norm.weight) J18; sparse atoms W_U J18, unit BF16, no final-norm gain. Pinned tied output embeddings and Qwen3 RMSNorm; no27B basis/atoms/null.

Elapsed scientific run 46.974s; GPU0. Plan original6ee0d7c42 before exclusive cache/e98/jlens/ONCE.json. Never reset or rerun.
