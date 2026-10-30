# E98 Oracle 4B / block18 — DESCRIPTIVE

Original prospective J forecast is immutable. Original Qwen metrics are copied from sealed E57/E59 analyses. No source analysis or count detector was rerun.

| Source row | 4B S [95% CI] | Original Qwen S | Original J | Native label | J agrees | Missing |
|---|---|---:|---|---|---|---:|
| E57/antonym_crosslingual | 0.07142857142857142 [0.023809523809523808, 0.13095238095238096] | -0.011904761904761904 | MISSED | MISSED | True | 0 |
| E57/capacity_list | nonbinary | None | None | None | None | — |
| E57/category_switch | nonbinary | 0.3132530120481928 | None | None | None | — |
| E57/clause_pending | 0.04938271604938271 [-0.037037037037037035, 0.13580246913580246] | 0.25925925925925924 | REPORTED | MISSED | False | 3 |
| E57/count_gradient_first_letter | 0.0 [0.0, 0.0] | -0.011904761904761904 | MISSED | MISSED | True | 0 |
| E57/focus_ignore | 0.0 [0.0, 0.0] | 0.07142857142857142 | REPORTED | MISSED | False | 0 |
| E57/focus_mention | 0.0 [0.0, 0.0] | 0.14285714285714285 | MISSED | MISSED | True | 0 |
| E57/focus_none | nonbinary | None | None | None | None | — |
| E57/focus_think | 0.0 [0.0, 0.0] | 0.2261904761904762 | MISSED | MISSED | True | 0 |
| E57/indent_level | 0.0 [0.0, 0.0] | -0.011904761904761904 | MISSED | MISSED | True | 0 |
| E57/linewrap_asked | -0.09523809523809523 [-0.16666666666666666, -0.023809523809523808] | 0.011904761904761904 | MISSED | MISSED | True | 0 |
| E57/linewrap_implicit | 0.024096385542168676 [0.0, 0.060240963855421686] | -0.011904761904761904 | MISSED | MISSED | True | 1 |
| E57/loop_direction | 0.3855421686746988 [0.2289156626506024, 0.5421686746987951] | 0.4268292682926829 | REPORTED | REPORTED | True | 1 |
| E57/multi_token_entity | 0.08333333333333333 [0.03571428571428571, 0.14285714285714285] | 0.5476190476190477 | REPORTED | MISSED | False | 0 |
| E57/nesting_depth | 0.047619047619047616 [-0.011904761904761904, 0.11904761904761904] | 0.0136986301369863 | MISSED | MISSED | True | 0 |
| E57/page_range_digit | 0.03571428571428571 [-0.05952380952380952, 0.13095238095238096] | -0.08333333333333333 | MISSED | MISSED | True | 0 |
| E57/section_header | 0.07142857142857142 [-0.11904761904761904, 0.2619047619047619] | 0.025 | MISSED | MISSED | True | 0 |
| E57/sentiment_judgement | 0.5 [0.36904761904761907, 0.6309523809523809] | 0.5833333333333334 | REPORTED | REPORTED | True | 0 |
| E57/subject_number | 0.012048192771084338 [0.0, 0.03614457831325301] | 0.23170731707317074 | MISSED | MISSED | True | 1 |
| E57/two_hop_answer | 0.047619047619047616 [-0.011904761904761904, 0.11904761904761904] | 0.2926829268292683 | MISSED | MISSED | True | 0 |
| E59/decline_plan | 0.0 [-0.20238095238095238, 0.20238095238095238] | 0.24050632911392406 | MISSED | MISSED | True | 0 |
| E59/format_plan | 0.12048192771084337 [-0.04849397590361444, 0.30120481927710846] | 0.9518072289156626 | MISSED | MISSED | True | 1 |
| E59/hedge_plan | 0.16666666666666666 [0.08333333333333333, 0.2619047619047619] | 0.9879518072289156 | MISSED | MISSED | True | 0 |
| E59/language_plan | -0.05952380952380952 [-0.16666666666666666, 0.047619047619047616] | 0.5394736842105263 | MISSED | MISSED | True | 0 |
| E59/length_plan | 0.7195121951219512 [0.5853658536585366, 0.8292682926829268] | 0.5466666666666666 | MISSED | REPORTED | False | 2 |
| E59/stance_plan | -0.11904761904761904 [-0.23809523809523808, 0.011904761904761904] | 0.6547619047619048 | REPORTED | MISSED | False | 0 |

All26rows/2184items retained:23binary/1932 plus3nonbinary/252;0port drops. capacity_list/category_switch retain168 original measurement objects, focus_none84actual mention judgments. No binary S/J invented for any nonbinary unit. Full Qwen original count records remain in RESULTS.json.

OLD_RUBRIC_SENSITIVITY.json reports primary and original-rubric signed S on the exact seeded447-item subset only; separate missing masks and unchanged whole-item bootstrap2000/seed20261027. No full-bank old-rubric substitution.

All74 truncated native outputs retained. No new confirmatory threshold/rule; inherited descriptive REPORTED criterion S≥.2 and CI lower>0. Operational count/schema amendments were committed after terminal judging but before any analysis claim; original adapter was committed pre-judging. See FINAL_INPUT_PLAN.json for chronology, normalized/original hashes and exact source bindings.
