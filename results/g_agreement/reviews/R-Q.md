# R-Q independent review

Timing convention confirmed directly by Guiv on 2026-10-28: BRIEF heading times are nominal. Git commit time is authoritative for every ordering check; a clarification counts as pre-output only if its commit predates the first affected output. Compare against the actual first affected output/custody timestamp. Heading-versus-commit differences recorded below are informational, not chronology failures. Where first-output evidence is missing, ordering remains unverified.

Pass: 2026-10-28. Registration snapshot c6d4b904. E73/E75 included because explicitly prioritized by Guiv. No worker chats or handoff interpretations were used. Only this review is edited.

Method: raw terminal judgments joined to sealed private item labels by opaque/source IDs; A=label 1, B=label 0; both/property/exhibits/silent score zero; UNPARSEABLE excluded under the dated clarification. Independent `common/stats.py.bootstrap_ci`, 2,000 draws, seed 20261027, sorted item IDs. CIs below are 95%. Derived/source-only checks are explicitly distinguished from raw re-computation. No worker once-only analysis entry point is rerun.

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E79 | R-C1 | PENDING | — | — | c6d4b904 | Reader outcome analysis unsealed in inspected artifacts; alpha <=2 only; manipulation check and norm flags below. |
| E79 | R-C2 | PENDING | — | — | c6d4b904 | Behaviour-only seal exists; full reporting contrast not sealed. |
| E80 | R-X1/R-X2 (original and E80b) | PENDING | — | — | c6d4b904 | No sealed scored outcomes located; E80b forecast must precede opening outputs; §198 labels analysis exploratory. |
| E80c | R-X3 | PENDING | — | — | c6d4b904 | No sealed outcome analysis located; require J fall >=.30, J-random >=.20, J-PCA >=.10 and positive bootstrap lower bounds. |
| E80c | R-X4 descriptive | PENDING | — | — | c6d4b904 | No sealed outcome analysis located. |
| E87 | R-L1 | PENDING | — | — | c6d4b904 | No sealed outcome analysis located; BOTH controls >=.30 required, else NOT EVALUABLE; random-only placebo, seven Oracle layers after clarification. |
| E93 | R-SR1 | PENDING | — | — | c6d4b904 | No sealed generations/analysis located; question-template commit must predate first generation. |
| E94 | H-A1 (hypothesis, not rule) | PENDING | — | — | c6d4b904 | No sealed agreement analysis located; report met/not only when sealed. |
| E56 | n / raw bootstrap audit | MET | 26 A/B row-reader cells; every acquired cell n=84; unparseable=37 | n=84 per cell | 57074675 2026-10-27T15:23:03+01:00 | 84 replaces 40x8 under §172 clarification 4; source /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e56_e57/verified_pull_single_v1/e56/judgments/JUDGMENTS.json; analysis result hash verified. This is an audit check, not an experimental decision rule. |
| E56 | oracle positive gate | NOT MET | 1/3; reasoning_bridge=(0.2261904761904762, 0.07142857142857142, 0.38095238095238093); rhyme_plan=(0.34523809523809523, 0.23809523809523808, 0.4523809523809524); instructed_focus=(0.03571428571428571, -0.011904761904761904, 0.09523809523809523) | gate=False | 57074675 2026-10-27T15:23:03+01:00 | Matches; requires >=2/3. fact_recall (0.7738095238095238, 0.6785714285714286, 0.8571428571428571) |
| E56 | oracle R2 | NOT EVALUABLE | positive gate 1/3 | NOT EVALUABLE | 57074675 2026-10-27T15:23:03+01:00 | Matches. Failed gate prevents inferential reading of rule. |
| E56 | oracle R3 | NOT EVALUABLE | positive gate 1/3 | NOT EVALUABLE | 57074675 2026-10-27T15:23:03+01:00 | Matches. Failed gate prevents inferential reading of rule. |
| E56 | oracle R4 | NOT EVALUABLE | positive gate 1/3 | NOT EVALUABLE | 57074675 2026-10-27T15:23:03+01:00 | Matches. Failed gate prevents inferential reading of rule. |
| E56 | nla positive gate | NOT MET | 0/3; reasoning_bridge=(-0.011904761904761904, -0.15476190476190477, 0.13095238095238096); rhyme_plan=(0.20238095238095238, 0.11904761904761904, 0.2857142857142857); instructed_focus=(0.023809523809523808, -0.023809523809523808, 0.07142857142857142) | gate=False | 57074675 2026-10-27T15:23:03+01:00 | Matches; requires >=2/3. fact_recall (0.7261904761904762, 0.6309523809523809, 0.8214285714285714) |
| E56 | nla R2 | NOT EVALUABLE | positive gate 0/3 | NOT EVALUABLE | 57074675 2026-10-27T15:23:03+01:00 | Matches. Failed gate prevents inferential reading of rule. |
| E56 | nla R3 | NOT EVALUABLE | positive gate 0/3 | NOT EVALUABLE | 57074675 2026-10-27T15:23:03+01:00 | Matches. Failed gate prevents inferential reading of rule. |
| E56 | nla R4 | NOT EVALUABLE | positive gate 0/3 | NOT EVALUABLE | 57074675 2026-10-27T15:23:03+01:00 | Matches. Failed gate prevents inferential reading of rule. |
| E56 | R1 adjective_implicit | NOT MET | probe=1.0; J-G3=0.6907596371882085 | False | 57074675 2026-10-27T15:23:03+01:00 | Sealed probe/J summaries checked; raw rank/probe bootstrap not yet independently verified; no CI threshold in R1. |
| E56 | R1 anomaly_state | NOT EVALUABLE | probe=1.0; J-G3=None | NOT EVALUABLE | 57074675 2026-10-27T15:23:03+01:00 | Sealed probe/J summaries checked; raw rank/probe bootstrap not yet independently verified; no CI threshold in R1. |
| E56 | R1 language_continuation | NOT MET | probe=1.0; J-G3=0.8238378684807256 | False | 57074675 2026-10-27T15:23:03+01:00 | Sealed probe/J summaries checked; raw rank/probe bootstrap not yet independently verified; no CI threshold in R1. |
| E56 | R1 linewrap_implicit | MET | probe=1.0; J-G3=0.42970521541950113 | True | 57074675 2026-10-27T15:23:03+01:00 | Sealed probe/J summaries checked; raw rank/probe bootstrap not yet independently verified; no CI threshold in R1. |
| E56 | R1 tense_implicit | MET | probe=1.0; J-G3=0.43679138321995464 | True | 57074675 2026-10-27T15:23:03+01:00 | Sealed probe/J summaries checked; raw rank/probe bootstrap not yet independently verified; no CI threshold in R1. |
| E57 | n / raw bootstrap audit | MET | 36 A/B row-reader cells; every acquired cell n=84; unparseable=30 | n=84 per cell | db69c4ce 2026-10-27T15:52:15+01:00 | 84 replaces 40x8 under §172 clarification 4; source /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e56_e57/verified_pull_single_v1/e57/judgments/JUDGMENTS.json; analysis result hash verified. This is an audit check, not an experimental decision rule. |
| E57 | R-B oracle | NOT MET | OUT-J/DIFFUSE=5/7; reports=3/7: subject_number,clause_pending,loop_direction | 5/7; reports=3/7; NOT MET | db69c4ce 2026-10-27T15:52:15+01:00 | Matches; raw S recomputed on all seven mechanics rows, probe/J labels from sealed result. Allowed reports <=2. |
| E57 | R-A1 oracle | NOT EVALUABLE | G3 missing for multi_token_entity | NOT EVALUABLE | db69c4ce 2026-10-27T15:52:15+01:00 | Matches §172/§173 14:15 clarification; no numeric comparison may impute zero. |
| E57 | R-B nla | NOT MET | OUT-J/DIFFUSE=5/7; reports=3/7: subject_number,clause_pending,loop_direction | 5/7; reports=3/7; NOT MET | db69c4ce 2026-10-27T15:52:15+01:00 | Matches; raw S recomputed on all seven mechanics rows, probe/J labels from sealed result. Allowed reports <=2. |
| E57 | R-A1 nla | NOT EVALUABLE | G3 missing for multi_token_entity | NOT EVALUABLE | db69c4ce 2026-10-27T15:52:15+01:00 | Matches §172/§173 14:15 clarification; no numeric comparison may impute zero. |
| E59 | n / raw bootstrap audit | MET | 12 A/B row-reader cells; every acquired cell n=84; unparseable=24 | n=84 per cell | 2b72dbbc 2026-10-27T23:00:02+01:00 | 84 replaces 40x8 under §172 clarification 4; source /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis5968_verified/E59/judge/JUDGMENTS.json; analysis result hash verified. This is an audit check, not an experimental decision rule. |
| E59 | R1 oracle | NOT MET | plans=5/5 eligible (6 registered); mechanics=3/7 | {'R1': 'NOT MET', 'falsifier': False, 'reported_plans': 5, 'same_run_reported_mechanics': 3} | 2b72dbbc 2026-10-27T23:00:02+01:00 | Matches: mechanics must be <=1. decline_plan excluded by gates; same-cohort binding present in sealed analysis. |
| E59 | R1 nla | NOT MET | plans=5/5 eligible (6 registered); mechanics=3/7 | {'R1': 'NOT MET', 'falsifier': False, 'reported_plans': 5, 'same_run_reported_mechanics': 3} | 2b72dbbc 2026-10-27T23:00:02+01:00 | Matches: mechanics must be <=1. decline_plan excluded by gates; same-cohort binding present in sealed analysis. |
| E59 | R2 descriptive | MET | IN-J=4/6 | 4 | 2b72dbbc 2026-10-27T23:00:02+01:00 | Descriptive count only, recomputed from sealed J labels; not a confirmatory result. |
| E62 | n / raw bootstrap audit | MET | 25 A/B row-reader cells; every acquired cell n=84; unparseable=50 | n=84 per cell | dc6ebc49 2026-10-27T16:15:09+01:00 | 84 replaces 40x8 under §172 clarification 4; source /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/second_wave_verified_v1/e62/judge/JUDGMENTS.json; analysis result hash verified. This is an audit check, not an experimental decision rule. |
| E62 | R-L0 | MET | 4/5 states: S1–S4; 20 cells | {'S1': True, 'S2': True, 'S3': True, 'S4': True, 'S5': False} | dc6ebc49 2026-10-27T16:15:09+01:00 | Availability gate checked against sealed probe summary; S5 excluded. |
| E62 | R-L1 Oracle | NOT MET | {'S1': 0.17857142857142855, 'S2': 0.03571428571428571, 'S3': -0.48025919228450875, 'S4': -0.7498369210697978} | {'S1': 0.17857142857142855, 'S2': 0.03571428571428571, 'S3': -0.48025919228450875, 'S4': -0.7498369210697978} | dc6ebc49 2026-10-27T16:15:09+01:00 | Matches; 0/4 climbs reach .30. |
| E62 | R-L2 Oracle | MET | rho(J,S)=0.802107074320; supplemental row-bootstrap CI=[0.479739712988,0.934508601853]; n=20 cells | 0.8021070743197525 | dc6ebc49 2026-10-27T16:15:09+01:00 | Exact point match. Registered rule only requires rho>=.6; CI here is supplemental. J values sealed, S rebuilt from raw judgments. |
| E62 | R-L3 | NOT MET | 2/4 gated states AUROC>=.80 (S3,S4) | NOT MET | dc6ebc49 2026-10-27T16:15:09+01:00 | Sealed AUROCs checked; independent raw behaviour rerun remains outstanding. |
| E62 | R-L5 | NOT EVALUABLE | E62P not run | NOT EVALUABLE | dc6ebc49 2026-10-27T16:15:09+01:00 | Matches; no placebo outcomes. |
| E62 | NLA R-L1/R-L2/R-L4/R-L5 | NOT EVALUABLE | NOT RUN | NOT RUN | dc6ebc49 2026-10-27T16:15:09+01:00 | Dropped under 13:40 compute replan. |
| E68 | n / raw bootstrap audit | MET | 18 A/B row-reader cells; every acquired cell n=84; unparseable=6 | n=84 per cell | 2b82a2f1 2026-10-27T23:46:51+01:00 | 84 replaces 40x8 under §172 clarification 4; source /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis5968_verified/E68/judge/JUDGMENTS.json; analysis result hash verified. This is an audit check, not an experimental decision rule. |
| E68 | R-O1 oracle | NOT MET | {'container_after_move': -0.03571428571428571, 'holder_after_handovers': 0.11962134251290878, 'topic_twin': 0.10516138628588423} | {'container_after_move': -0.03571428571428571, 'holder_after_handovers': 0.11962134251290878, 'topic_twin': 0.10516138628588423} | 2b82a2f1 2026-10-27T23:46:51+01:00 | Exact match; neither state reaches .30; 84 items/position, arith_compare dropped pre-capture. |
| E68 | R-O1 nla | NOT MET | {'container_after_move': -0.20395869191049915, 'holder_after_handovers': 0.03571428571428571, 'topic_twin': 0.011904761904761973} | {'container_after_move': -0.20395869191049915, 'holder_after_handovers': 0.03571428571428571, 'topic_twin': 0.011904761904761973} | 2b82a2f1 2026-10-27T23:46:51+01:00 | Exact match; neither state reaches .30; 84 items/position, arith_compare dropped pre-capture. |

## Raw independent S and CI ledger

Each line: experiment, reader/row, parseable/acquired n, S [lo, hi]. Source judgments and analysis commits are listed above.
- E56 nla/adjective_asked: n=84/84; 0.023809523810, 0.000000000000, 0.059523809524
- E56 nla/adjective_implicit: n=84/84; 0.476190476190, 0.369047619048, 0.583333333333
- E56 nla/anomaly_state: n=84/84; 0.023809523810, -0.047619047619, 0.095238095238
- E56 nla/fact_recall: n=84/84; 0.726190476190, 0.630952380952, 0.821428571429
- E56 nla/instructed_focus: n=84/84; 0.023809523810, -0.023809523810, 0.071428571429
- E56 nla/language_continuation: n=84/84; 0.773809523810, 0.678571428571, 0.857142857143
- E56 nla/language_report: n=84/84; 0.392857142857, 0.261904761905, 0.511904761905
- E56 nla/linewrap_asked: n=84/84; 0.083333333333, 0.011904761905, 0.154761904762
- E56 nla/linewrap_implicit: n=84/84; -0.023809523810, -0.059523809524, 0.000000000000
- E56 nla/reasoning_bridge: n=84/84; -0.011904761905, -0.154761904762, 0.130952380952
- E56 nla/rhyme_plan: n=84/84; 0.202380952381, 0.119047619048, 0.285714285714
- E56 nla/tense_asked: n=84/84; 0.428571428571, 0.297619047619, 0.559523809524
- E56 nla/tense_implicit: n=83/84; 0.240963855422, 0.144578313253, 0.337349397590
- E56 oracle/adjective_asked: n=83/84; 0.180722891566, 0.048192771084, 0.313253012048
- E56 oracle/adjective_implicit: n=71/84; 0.253521126761, 0.154929577465, 0.366197183099
- E56 oracle/anomaly_state: n=78/84; -0.051282051282, -0.192307692308, 0.090064102564
- E56 oracle/fact_recall: n=84/84; 0.773809523810, 0.678571428571, 0.857142857143
- E56 oracle/instructed_focus: n=84/84; 0.035714285714, -0.011904761905, 0.095238095238
- E56 oracle/language_continuation: n=75/84; 0.666666666667, 0.533333333333, 0.786666666667
- E56 oracle/language_report: n=84/84; 1.000000000000, 1.000000000000, 1.000000000000
- E56 oracle/linewrap_asked: n=84/84; 0.011904761905, 0.000000000000, 0.035714285714
- E56 oracle/linewrap_implicit: n=83/84; 0.000000000000, 0.000000000000, 0.000000000000
- E56 oracle/reasoning_bridge: n=84/84; 0.226190476190, 0.071428571429, 0.380952380952
- E56 oracle/rhyme_plan: n=84/84; 0.345238095238, 0.238095238095, 0.452380952381
- E56 oracle/tense_asked: n=84/84; 0.726190476190, 0.571428571429, 0.857142857143
- E56 oracle/tense_implicit: n=78/84; 0.487179487179, 0.371794871795, 0.602564102564
- E57 nla/antonym_crosslingual: n=84/84; 0.000000000000, 0.000000000000, 0.000000000000
- E57 nla/category_switch: n=83/84; 0.650602409639, 0.518072289157, 0.771084337349
- E57 nla/clause_pending: n=84/84; 0.261904761905, 0.083333333333, 0.440476190476
- E57 nla/count_gradient_first_letter: n=84/84; -0.059523809524, -0.166666666667, 0.047619047619
- E57 nla/focus_ignore: n=84/84; 0.083333333333, 0.035714285714, 0.142857142857
- E57 nla/focus_mention: n=84/84; 0.083333333333, 0.023809523810, 0.154761904762
- E57 nla/focus_think: n=84/84; 0.261904761905, 0.178571428571, 0.357142857143
- E57 nla/indent_level: n=84/84; 0.000000000000, 0.000000000000, 0.000000000000
- E57 nla/linewrap_asked: n=84/84; 0.059523809524, 0.000000000000, 0.130952380952
- E57 nla/linewrap_implicit: n=84/84; -0.011904761905, -0.059523809524, 0.023809523810
- E57 nla/loop_direction: n=80/84; 0.562500000000, 0.450000000000, 0.675000000000
- E57 nla/multi_token_entity: n=84/84; 0.273809523810, 0.178571428571, 0.369047619048
- E57 nla/nesting_depth: n=84/84; 0.142857142857, 0.059523809524, 0.238095238095
- E57 nla/page_range_digit: n=84/84; 0.095238095238, 0.023809523810, 0.178571428571
- E57 nla/section_header: n=84/84; 0.119047619048, -0.071428571429, 0.297619047619
- E57 nla/sentiment_judgement: n=84/84; 0.738095238095, 0.642857142857, 0.821428571429
- E57 nla/subject_number: n=84/84; 0.226190476190, 0.130952380952, 0.321428571429
- E57 nla/two_hop_answer: n=84/84; 0.154761904762, 0.083333333333, 0.238095238095
- E57 oracle/antonym_crosslingual: n=84/84; -0.011904761905, -0.035714285714, 0.000000000000
- E57 oracle/category_switch: n=83/84; 0.313253012048, 0.156626506024, 0.469879518072
- E57 oracle/clause_pending: n=81/84; 0.259259259259, 0.160493827160, 0.358024691358
- E57 oracle/count_gradient_first_letter: n=84/84; -0.011904761905, -0.035714285714, 0.000000000000
- E57 oracle/focus_ignore: n=84/84; 0.071428571429, -0.023809523810, 0.166666666667
- E57 oracle/focus_mention: n=84/84; 0.142857142857, 0.035714285714, 0.250000000000
- E57 oracle/focus_think: n=84/84; 0.226190476190, 0.142857142857, 0.321428571429
- E57 oracle/indent_level: n=84/84; -0.011904761905, -0.059523809524, 0.023809523810
- E57 oracle/linewrap_asked: n=84/84; 0.011904761905, 0.000000000000, 0.035714285714
- E57 oracle/linewrap_implicit: n=84/84; -0.011904761905, -0.035714285714, 0.000000000000
- E57 oracle/loop_direction: n=82/84; 0.426829268293, 0.304878048780, 0.536890243902
- E57 oracle/multi_token_entity: n=84/84; 0.547619047619, 0.440476190476, 0.654761904762
- E57 oracle/nesting_depth: n=73/84; 0.013698630137, -0.068493150685, 0.095890410959
- E57 oracle/page_range_digit: n=84/84; -0.083333333333, -0.202380952381, 0.047619047619
- E57 oracle/section_header: n=80/84; 0.025000000000, -0.137500000000, 0.187500000000
- E57 oracle/sentiment_judgement: n=84/84; 0.583333333333, 0.428571428571, 0.726190476190
- E57 oracle/subject_number: n=82/84; 0.231707317073, 0.134146341463, 0.329268292683
- E57 oracle/two_hop_answer: n=82/84; 0.292682926829, 0.195121951220, 0.402439024390
- E59 nla/decline_plan: n=84/84; 0.095238095238, -0.107142857143, 0.285714285714
- E59 nla/format_plan: n=84/84; 0.940476190476, 0.880952380952, 0.988095238095
- E59 nla/hedge_plan: n=84/84; 0.964285714286, 0.916666666667, 1.000000000000
- E59 nla/language_plan: n=84/84; 0.571428571429, 0.452380952381, 0.690476190476
- E59 nla/length_plan: n=84/84; 0.559523809524, 0.452380952381, 0.666666666667
- E59 nla/stance_plan: n=84/84; 0.666666666667, 0.559523809524, 0.761904761905
- E59 oracle/decline_plan: n=79/84; 0.240506329114, 0.037974683544, 0.418037974684
- E59 oracle/format_plan: n=83/84; 0.951807228916, 0.903614457831, 1.000000000000
- E59 oracle/hedge_plan: n=83/84; 0.987951807229, 0.963855421687, 1.000000000000
- E59 oracle/language_plan: n=76/84; 0.539473684211, 0.368421052632, 0.684210526316
- E59 oracle/length_plan: n=75/84; 0.546666666667, 0.426666666667, 0.666666666667
- E59 oracle/stance_plan: n=84/84; 0.654761904762, 0.547619047619, 0.750000000000
- E62 oracle/S1_L0: n=84/84; -0.071428571429, -0.142857142857, 0.000000000000
- E62 oracle/S1_L1: n=84/84; -0.083333333333, -0.142857142857, -0.035714285714
- E62 oracle/S1_L2: n=84/84; -0.035714285714, -0.107142857143, 0.035714285714
- E62 oracle/S1_L3: n=83/84; 0.240963855422, 0.120481927711, 0.373493975904
- E62 oracle/S1_L4: n=84/84; 0.107142857143, 0.035714285714, 0.178571428571
- E62 oracle/S2_L0: n=84/84; 0.011904761905, 0.000000000000, 0.035714285714
- E62 oracle/S2_L1: n=84/84; -0.011904761905, -0.035714285714, 0.000000000000
- E62 oracle/S2_L2: n=84/84; 0.000000000000, 0.000000000000, 0.000000000000
- E62 oracle/S2_L3: n=84/84; 0.000000000000, -0.035714285714, 0.035714285714
- E62 oracle/S2_L4: n=84/84; 0.047619047619, -0.011904761905, 0.119047619048
- E62 oracle/S3_L0: n=79/84; 0.468354430380, 0.367088607595, 0.582278481013
- E62 oracle/S3_L1: n=82/84; 0.195121951220, 0.085365853659, 0.304878048780
- E62 oracle/S3_L2: n=84/84; 0.166666666667, 0.011904761905, 0.321428571429
- E62 oracle/S3_L3: n=83/84; 0.771084337349, 0.626506024096, 0.903614457831
- E62 oracle/S3_L4: n=84/84; -0.011904761905, -0.059523809524, 0.023809523810
- E62 oracle/S4_L0: n=73/84; 0.726027397260, 0.616438356164, 0.835616438356
- E62 oracle/S4_L1: n=71/84; 0.661971830986, 0.521126760563, 0.775000000000
- E62 oracle/S4_L2: n=78/84; 0.371794871795, 0.205128205128, 0.525641025641
- E62 oracle/S4_L3: n=84/84; 1.000000000000, 1.000000000000, 1.000000000000
- E62 oracle/S4_L4: n=84/84; -0.023809523810, -0.119047619048, 0.083333333333
- E62 oracle/S5_L0: n=80/84; 0.312500000000, 0.212500000000, 0.425000000000
- E62 oracle/S5_L1: n=80/84; 0.175000000000, 0.025000000000, 0.325000000000
- E62 oracle/S5_L2: n=83/84; 0.277108433735, 0.156626506024, 0.397590361446
- E62 oracle/S5_L3: n=82/84; 0.000000000000, -0.109756097561, 0.097560975610
- E62 oracle/S5_L4: n=84/84; -0.011904761905, -0.035714285714, 0.000000000000
- E68 nla/container_after_move~midpoint: n=84/84; -0.047619047619, -0.119047619048, 0.011904761905
- E68 nla/container_after_move~pre_answer: n=84/84; -0.071428571429, -0.166666666667, 0.023809523810
- E68 nla/container_after_move~registered: n=83/84; 0.132530120482, 0.012048192771, 0.265060240964
- E68 nla/holder_after_handovers~midpoint: n=84/84; 0.000000000000, 0.000000000000, 0.000000000000
- E68 nla/holder_after_handovers~pre_answer: n=84/84; 0.035714285714, -0.035714285714, 0.107142857143
- E68 nla/holder_after_handovers~registered: n=84/84; 0.000000000000, 0.000000000000, 0.000000000000
- E68 nla/topic_twin~midpoint: n=84/84; 0.869047619048, 0.785714285714, 0.928571428571
- E68 nla/topic_twin~pre_answer: n=84/84; 0.833333333333, 0.750000000000, 0.904761904762
- E68 nla/topic_twin~registered: n=84/84; 0.821428571429, 0.738095238095, 0.893154761905
- E68 oracle/container_after_move~midpoint: n=84/84; -0.035714285714, -0.190476190476, 0.119047619048
- E68 oracle/container_after_move~pre_answer: n=84/84; -0.011904761905, -0.107142857143, 0.083333333333
- E68 oracle/container_after_move~registered: n=84/84; 0.023809523810, 0.000000000000, 0.059523809524
- E68 oracle/holder_after_handovers~midpoint: n=84/84; 0.000000000000, 0.000000000000, 0.000000000000
- E68 oracle/holder_after_handovers~pre_answer: n=84/84; 0.071428571429, -0.047619047619, 0.190476190476
- E68 oracle/holder_after_handovers~registered: n=83/84; -0.048192771084, -0.120481927711, 0.012048192771
- E68 oracle/topic_twin~midpoint: n=84/84; 0.726190476190, 0.630952380952, 0.821428571429
- E68 oracle/topic_twin~pre_answer: n=81/84; 0.864197530864, 0.790123456790, 0.938271604938
- E68 oracle/topic_twin~registered: n=83/84; 0.759036144578, 0.662650602410, 0.843373493976

## E67 independent paired audit

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E67 wave1 oracle | R-F1 | NOT MET | (0.06354515050167224, 0.0033444816053511705, 0.12040133779264214); n=299 | {'CI95': [0.0033444816053511705, 0.12040133779264214], 'Sup_matched_minus_mismatched': 0.06354515050167224, 'paired_units': 299, 'verdict': 'NOT MET'} | c32c2a2d 2026-10-27T22:15:24+01:00 | Independent raw recomputation matches; acquired per bank {'D4': 99, 'E49': 100, 'E54': 100} versus up to 100 registered. |
| E67 wave1 oracle | R-F2 | MET | (0.5819397993311036, 0.5253377535005872, 0.6364630030665421); n=299 | {'F_matched': 0.5819397993311036, 'Wilson95': [0.5253377535005872, 0.6364630030665421], 'n': 299, 'verdict': 'MET'} | c32c2a2d 2026-10-27T22:15:24+01:00 | Independent raw recomputation matches; acquired per bank {'D4': 99, 'E49': 100, 'E54': 100} versus up to 100 registered. |
| E67 wave1 nla | R-F1 | NOT MET | (-0.020202020202020204, -0.16161616161616163, 0.12121212121212122); n=99 | {'CI95': [-0.16161616161616163, 0.12121212121212122], 'Sup_matched_minus_mismatched': -0.020202020202020204, 'paired_units': 99, 'verdict': 'NOT MET'} | c32c2a2d 2026-10-27T22:15:24+01:00 | Independent raw recomputation matches; acquired per bank {'D4': 99} versus up to 100 registered. |
| E67 wave1 nla | R-F2 | MET | (1.0, 0.9626454664260378, 1.0); n=99 | {'F_matched': 1.0, 'Wilson95': [0.9626454664260378, 1.0], 'n': 99, 'verdict': 'MET'} | c32c2a2d 2026-10-27T22:15:24+01:00 | Independent raw recomputation matches; acquired per bank {'D4': 99} versus up to 100 registered. |
| E67 wave1 nla truncated separate | R-F1 | NOT MET | (0.01, -0.05, 0.07); n=200 | {'CI95': [-0.05, 0.07], 'Sup_matched_minus_mismatched': 0.01, 'paired_units': 200, 'verdict': 'NOT MET'} | c32c2a2d 2026-10-27T22:15:24+01:00 | Independent raw recomputation matches; acquired per bank {'E49': 100, 'E54': 100} versus up to 100 registered. |
| E67 wave1 nla truncated separate | R-F2 | MET | (0.945, 0.9042120755340645, 0.9690149791986299); n=200 | {'F_matched': 0.945, 'Wilson95': [0.9042120755340645, 0.9690149791986299], 'n': 200, 'verdict': 'MET'} | c32c2a2d 2026-10-27T22:15:24+01:00 | Independent raw recomputation matches; acquired per bank {'E49': 100, 'E54': 100} versus up to 100 registered. |
| E67 wave2 oracle | R-F1 | NOT MET | (0.05, -0.025, 0.13); n=200 | {'CI95': [-0.025, 0.13], 'Sup_matched_minus_mismatched': 0.05, 'paired_units': 200, 'verdict': 'NOT MET'} | 687b2aee 2026-10-27T22:58:58+01:00 | Independent raw recomputation matches; acquired per bank {'E56': 100, 'E57': 100} versus up to 100 registered. |
| E67 wave2 oracle | R-F2 | MET | (0.63, 0.5612250134987606, 0.6938750249624759); n=200 | {'F_matched': 0.63, 'Wilson95': [0.5612250134987606, 0.6938750249624759], 'n': 200, 'verdict': 'MET'} | 687b2aee 2026-10-27T22:58:58+01:00 | Independent raw recomputation matches; acquired per bank {'E56': 100, 'E57': 100} versus up to 100 registered. |
| E67 wave2 nla | R-F1 | MET | (0.12, 0.04, 0.2); n=200 | {'CI95': [0.04, 0.2], 'Sup_matched_minus_mismatched': 0.12, 'paired_units': 200, 'verdict': 'MET'} | 687b2aee 2026-10-27T22:58:58+01:00 | Independent raw recomputation matches; acquired per bank {'E56': 100, 'E57': 100} versus up to 100 registered. |
| E67 wave2 nla | R-F2 | MET | (0.935, 0.8919799625008207, 0.9616240123502404); n=200 | {'F_matched': 0.935, 'Wilson95': [0.8919799625008207, 0.9616240123502404], 'n': 200, 'verdict': 'MET'} | 687b2aee 2026-10-27T22:58:58+01:00 | Independent raw recomputation matches; acquired per bank {'E56': 100, 'E57': 100} versus up to 100 registered. |

Wave 1 and wave 2 remain separate as required. R-F3 is descriptive; no pooled-wave verdict is inferred. Raw inputs hash-bound by each ANALYSIS_SPEC.wave*.json and terminal result seal.

## E73 raw judgment audit

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E73 nla | W1 S audit | NOT MET | (0.16216216216216217, 0.059324324324324336, 0.2594594594594595); n=185/200 | 0.16216216216216217; [0.059324324324324336, 0.2594594594594595] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 nla | W2 S audit | MET | (0.06565656565656566, -0.005050505050505051, 0.13636363636363635); n=198/200 | 0.06565656565656566; [-0.005050505050505051, 0.13636363636363635] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 nla | W3 S audit | MET | (0.01020408163265306, -0.02040816326530612, 0.04081632653061224); n=196/200 | 0.01020408163265306; [-0.02040816326530612, 0.04081632653061224] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 nla | W4 S audit | NOT MET | (0.1518324607329843, 0.08376963350785341, 0.2198952879581152); n=191/200 | 0.1518324607329843; [0.08376963350785341, 0.2198952879581152] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 nla | W5 S audit | NOT MET | (0.145, 0.095, 0.195); n=200/200 | 0.145; [0.095, 0.195] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 nla | W7 S audit | MET | (0.9020618556701031, 0.845360824742268, 0.9587628865979382); n=194/200 | 0.9020618556701031; [0.845360824742268, 0.9587628865979382] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 nla | W8 S audit | MET | (0.65, 0.58, 0.715); n=200/200 | 0.65; [0.58, 0.715] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 oracle | W1 S audit | MET | (0.07228915662650602, -0.030120481927710843, 0.1746987951807229); n=166/200 | 0.07228915662650602; [-0.030120481927710843, 0.1746987951807229] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 oracle | W2 S audit | MET | (0.04242424242424243, -0.012121212121212121, 0.09712121212121129); n=165/200 | 0.04242424242424243; [-0.012121212121212121, 0.09712121212121129] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 oracle | W3 S audit | MET | (-0.07453416149068323, -0.15527950310559005, 0.006211180124223602); n=161/200 | -0.07453416149068323; [-0.15527950310559005, 0.006211180124223602] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 oracle | W4 S audit | MET | (0.024390243902439025, -0.03048780487804878, 0.07317073170731707); n=164/200 | 0.024390243902439025; [-0.03048780487804878, 0.07317073170731707] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 oracle | W5 S audit | MET | (0.02030456852791878, -0.06091370558375635, 0.09644670050761421); n=197/200 | 0.02030456852791878; [-0.06091370558375635, 0.09644670050761421] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 oracle | W7 S audit | MET | (0.8787878787878788, 0.797979797979798, 0.9494949494949495); n=99/200 | 0.8787878787878788; [0.797979797979798, 0.9494949494949495] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 oracle | W8 S audit | MET | (0.5056179775280899, 0.42696629213483145, 0.5786516853932584); n=178/200 | 0.5056179775280899; [0.42696629213483145, 0.5786516853932584] | 62ebfec0 2026-10-28T05:08:39+01:00 | Raw signed values recomputed; this is a per-state component, W2/W3 descriptive. |
| E73 oracle | R-W1 | MET | pooled=0.03795066413662239; stratified CI=[-0.005740037950664134, 0.08349146110056926]; n=527/600 | 0.03795066413662239; [-0.0056925996204933585, 0.08159392789373814] | 62ebfec0 2026-10-28T05:08:39+01:00 | Point independently reproduced; per-state common/stats bootstrap above; pooled bootstrap resamples within state as registered. |
| E73 oracle | R-W2 | MET | W1/W4/W5=[0.07228915662650602, 0.024390243902439025, 0.02030456852791878] | {'all_eligible_pass': True, 'eligible_states': ['W1', 'W4', 'W5'], 'per_state_pass': {'W1': True, 'W4': True, 'W5': True}} | 62ebfec0 2026-10-28T05:08:39+01:00 | Uses probe-passing structural states only. |
| E73 nla | R-W1 | NOT MET | pooled=0.1527777777777778; stratified CI=[0.1111111111111111, 0.19618055555555555]; n=576/600 | 0.1527777777777778; [0.11284722222222222, 0.19444444444444445] | 62ebfec0 2026-10-28T05:08:39+01:00 | Point independently reproduced; per-state common/stats bootstrap above; pooled bootstrap resamples within state as registered. |
| E73 nla | R-W2 | NOT MET | W1/W4/W5=[0.16216216216216217, 0.1518324607329843, 0.145] | {'all_eligible_pass': False, 'eligible_states': ['W1', 'W4', 'W5'], 'per_state_pass': {'W1': False, 'W4': False, 'W5': False}} | 62ebfec0 2026-10-28T05:08:39+01:00 | Uses probe-passing structural states only. |

Acquisition: 200 test positions/state/reader as registered; 2,800 judgments. Probe bank n=400 dev +400 test except W8 316+316 (amended shortfall); W6 dropped. Oracle missing 270/1,400, NLA missing 36/1,400. Positive-control W7 Oracle missing 101/200 is material; headline conditional on parseable outcomes.

## E66 / E75 / E76 checks

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E66 | R-G1 | NOT MET | structural 104/383 (0.27154046997389036, 0.22943020522853128, 0.3181882515248272); topic 125/149 (0.8389261744966443, 0.7715094438388466, 0.8893054128493849) | 104/383=.27154047;125/149=.83892617;FALSIFIED | 1a95ac9d 2026-10-27T23:36:00+01:00 | Exact raw Wilson reproduction; falsifier >=.20 holds. 542 acquired versus up to750, amended strata C150/S1 128/S2 137/S3 68/S4 59. |
| E75 oracle | R-P1 | NOT EVALUABLE | n=55; positives=26; BA=(0.7924403183023873, 0.6921114951356887, 0.8965545977011494) | n=55; BA=0.7924403183023873; NOT EVALUABLE | 84d8af77 2026-10-28T06:35:00+01:00 | n<60. BA independently resampled sealed bound units; underlying raw S for E56/57/59/62/73 rechecked above. Category/permutation clauses cannot rescue failed n gate. |
| E75 nla | R-P1 | NOT EVALUABLE | n=35; positives=18; BA=(0.8022875816993464, 0.6666666666666667, 0.9230769230769231) | n=35; BA=0.8022875816993464; NOT EVALUABLE | 84d8af77 2026-10-28T06:35:00+01:00 | n<60. BA independently resampled sealed bound units; underlying raw S for E56/57/59/62/73 rechecked above. Category/permutation clauses cannot rescue failed n gate. |

| E76 | regex placebo floors (descriptive audit) | MET | 1208 estimates/CIs independently reproduced; 500 vectors per pool/reader, 2,000 outputs; disagreements=0 | 500 per pool; 151 catalog rows | 10eb9898 2026-10-28T04:46:18+01:00 | Exact raw regex and common/stats bootstrap check; unavailable/nonbinary cases retain N/A. Audit verdict only, no scientific decision rule. |

Example raw rechecks: [('E36', 'json_status', 'oracle', 'random', 'N_any_value', (0.002, 0.0, 0.006)), ('E36', 'json_status', 'oracle', 'random', 'S_regex', (-0.002, -0.006, 0.0)), ('E36', 'json_status', 'oracle', 'shuffled', 'N_any_value', (0.038, 0.022, 0.056)), ('E36', 'json_status', 'oracle', 'shuffled', 'S_regex', (-0.006, -0.02, 0.006))].
| E76 | judged floors | PENDING | No completed judged-floor analysis located | regex artifact says waiting | 10eb9898 2026-10-28T04:46:18+01:00 | §194 clarification 2 sample rule must be checked on completion. |

## E58b independent raw continuation audit

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E58b | R_b1 | MET | Raw paired damages for 37 rows x84 items reconstructed below | {'denominator': 3, 'met': True, 'passing': 2} | cc0346b3 2026-10-27T06:54:05+01:00 | Independent common/stats intervals; registered comparison is point-estimate only. |
| E58b | R_b2 | NOT MET | Raw paired damages for 37 rows x84 items reconstructed below | {'denominator': 25, 'met': False, 'passing': 15, 'rows': ['W1/list_depth', 'W1/prose_paren', 'W1/prose_quote', 'W1/python_depth', 'W1/python_indent', 'W1/python_string', 'W1/table_column', 'W1/table_role', 'E36/list_depth', 'E36/prose_paren', 'E36/prose_quote', 'E36/python_depth', 'E36/python_indent', 'E36/python_string', 'E36/table_column', 'E36/table_role', 'E49/arith_compare', 'E49/negation_scope', 'E56/adjective_implicit', 'E56/tense_implicit', 'E57/clause_pending', 'E57/indent_level', 'E57/nesting_depth', 'E57/subject_number', 'E57/page_range_digit'], 'status': 'EVALUABLE'} | cc0346b3 2026-10-27T06:54:05+01:00 | Independent common/stats intervals; registered comparison is point-estimate only. |
- W1/list_depth: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.12287951083410353, -0.00557820513134911, 0.25349089531671426), (-0.04917692456926618, -0.07427154952571506, -0.0224567251829874), (-0.19281818185533797, -0.3843700299660365, -0.0013448144708361734), (0.17205643540336973, 0.03501842115606581, 0.311352618081229)]; category=bookkeeping; control=False.
- W1/prose_paren: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.5711214145024618, -0.7207137564751541, -0.4335556900971348), (-0.23048300743103028, -0.3025129483680108, -0.16981939197917073), (0.9991155089367003, 0.6392507469858087, 1.3265403711547452), (-0.34063840707143145, -0.48178297360294636, -0.20503351877399162)]; category=delimiter; control=False.
- W1/prose_quote: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.06736259738959018, -0.30958013746310914, 0.17779361508520578), (-0.03726661721510547, -0.08236351794962372, 0.00723267072678672), (0.8496605257193247, 0.42667919480286187, 1.346809599484272), (-0.030095980174484702, -0.29172083052230025, 0.23823380433289074)]; category=delimiter; control=False.
- W1/python_depth: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.0009740349792298817, -0.09058133017803942, 0.0911678194822299), (-0.09055950499716259, -0.10899920812674932, -0.07292779339211329), (0.8732665220186824, 0.4475180757719846, 1.3235679482065494), (0.09153353997639249, 0.002158320719997091, 0.18078886194598098)]; category=bookkeeping; control=False.
- W1/python_indent: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.06244520346323649, -0.25941295020637056, 0.11289558657223252), (-0.07944063388165973, -0.13960658475401852, -0.023258573742849578), (0.806803401027407, 0.5208339360853037, 1.061901595514445), (0.016995430418423243, -0.1501175428678592, 0.17735060974245978)]; category=bookkeeping; control=False.
- W1/python_string: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.3015227709409027, -0.40217020041531043, -0.20748578552600178), (-0.0759350276951279, -0.10513547130372551, -0.04856352850661748), (2.255529789342767, 1.576003365302902, 3.038342555967115), (-0.2255877432457748, -0.3381070477938989, -0.11485105954376726)]; category=delimiter; control=False.
- W1/table_column: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.012847328558564186, -0.24113784389171217, 0.2739439708103115), (0.002364099039030928, -0.05202760952824196, 0.05944025982160209), (-0.0673711100770604, -0.7474054132782233, 0.6137667814086715), (0.010483229519533274, -0.26759201501340923, 0.30167036225520283)]; category=bookkeeping; control=False.
- W1/table_role: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.20259158384232295, -0.37307933568954466, -0.025552896516663696), (0.08666501612890334, 0.06667616540477389, 0.10707023654665267), (1.107316249892825, 0.48620348884945824, 1.7167614512500309), (-0.28925659997122627, -0.4608894445782616, -0.11601719319820426)]; category=bookkeeping; control=False.
- E36/list_depth: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.06848009711220152, -0.046788258708658666, 0.17151445164566947), (0.049207989374796555, 0.008291246011143645, 0.09273118788287753), (0.3945224654106867, 0.19790618121623993, 0.593501641636803), (0.01927210773740495, -0.08233081704094296, 0.11472873984348204)]; category=bookkeeping; control=False.
- E36/prose_paren: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.42173134429114206, -0.6734849158763175, -0.18223641675320415), (-0.09169089595476787, -0.1263671436515592, -0.058000848850324055), (1.4648928145567577, 0.9931653898830215, 1.9399705738982274), (-0.33004044833637414, -0.5603355509752319, -0.1062456978112459)]; category=delimiter; control=False.
- E36/prose_quote: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.34162215728844914, 0.1264618003430466, 0.5537242975130322), (0.1281350540972891, 0.08382658685867986, 0.1731291840101282), (2.4856633033071245, 1.3071767983248548, 3.6329196232947565), (0.21348710319116004, 0.0009106701248813163, 0.41835652902899745)]; category=delimiter; control=False.
- E36/python_depth: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.19619411265566236, -0.3329541017611821, -0.0614769626674908), (0.005896828820308049, -0.027481070105873407, 0.0414644632923106), (1.6625546147780759, 1.0776139473054736, 2.248482342485693), (-0.2020909414759704, -0.35821807242841236, -0.04275719474646317)]; category=bookkeeping; control=False.
- E36/python_indent: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.28757349366233464, -0.4278379560049091, -0.1532194475155501), (0.14078094647044226, 0.11619142641623814, 0.16461548159874617), (1.7996907454161417, 1.3207130433902854, 2.285974134593492), (-0.4283544401327769, -0.569639550035908, -0.290637046684112)]; category=bookkeeping; control=False.
- E36/python_string: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.2759102260073026, -0.4640908630298717, -0.08053849992297969), (0.04899628502982003, 0.015486360873494828, 0.08289991746346155), (1.87605800869919, 1.3492179980590229, 2.4043256222314775), (-0.3249065110371226, -0.5103754956718712, -0.13870671692880848)]; category=delimiter; control=False.
- E36/table_column: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.4485503285901532, -0.6334321220832256, -0.26315542921656754), (0.12401543942147068, 0.029967171963016, 0.22043069876530866), (-0.27405813156760167, -0.6096705747346971, 0.07718538141121983), (-0.5725657680116238, -0.8357054554378347, -0.30892849306797715)]; category=bookkeeping; control=False.
- E36/table_role: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.044655053388504756, -0.22187117430425826, 0.1302924068201155), (0.005996948764437714, -0.05521303445100784, 0.06847291784627095), (0.10334327958879017, -0.28607019221498853, 0.4965498704285848), (-0.05065200215294247, -0.21151419002385363, 0.10095336826074686)]; category=bookkeeping; control=False.
- E49/arith_compare: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.09523810091472808, -0.2693824954774408, 0.06549478343554896), (-0.04851192505586711, -0.19213170476967378, 0.09525668000181506), (-0.0963541716337204, -0.4553664861158246, 0.22924104501448886), (-0.046726175858860956, -0.29081471270748543, 0.19348215211715)]; category=bookkeeping; control=False.
- E49/container_after_move: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-1.011160726525954, -1.170405536069579, -0.8623512015101455), (0.3595238137103263, 0.29356399613033457, 0.4250111704532588), (0.8839285642219087, 0.3711123357072384, 1.3928757482740495), (-1.37068454023628, -1.519356423492233, -1.2243898933975115)]; category=content; control=False.
- E49/holder_after_handovers: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.23850356397174655, -0.4378460695346197, -0.04341334260645372), (-0.03189224515642438, -0.125013545638039, 0.05675164625758204), (-0.1376858495530628, -0.5341407094682965, 0.2861853082974746), (-0.2066113188153221, -0.39691792445523405, -0.01407063390527471)]; category=content; control=False.
- E49/negation_scope: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.34844207763671875, -0.5448859861918859, -0.15735712789353878), (-0.15924031393868582, -0.17759563854762486, -0.1399521174884978), (-0.728308223542713, -1.4156787259238106, -0.0371477149781729), (-0.18920176369803288, -0.3985054482732502, 0.01285945869627451)]; category=syntactic; control=False.
- E49/next_paragraph_language: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.23065476190476192, 0.14546130952380953, 0.32180059523809523), (0.19322916666666665, 0.18162016369047615, 0.20505952380952377), (1.1541573660714286, 0.862114025297619, 1.4511416480654762), (0.037425595238095244, -0.04352678571428571, 0.12122767857142844)]; category=format; control=False.
- E49/topic_twin: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.04575893992469424, -0.01713176170984904, 0.10379444162050883), (-0.03616074607485816, -0.06065109428905305, -0.0117540238584791), (1.1925223441351027, 1.060639926081612, 1.3327752550443015), (0.08191968599955239, 0.02930984968230839, 0.13082225504375627)]; category=content; control=False.
- E49/unit_system: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.2760416467984517, 0.17187500081601598, 0.3757440160072985), (-0.07172619970071883, -0.10491075044231757, -0.03972841921306794), (-1.1994047406173887, -1.8995628125256017, -0.5057942581673471), (0.3477678464991706, 0.2681436105782078, 0.4236644260691745)]; category=format; control=False.
- E49/user_expertise: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.32248687744140625, 0.22741828759511312, 0.41591758273896706), (0.05081746237618583, 0.006192028636024116, 0.09735289176305136), (0.015267326718284971, -0.23803912003835043, 0.3124975017138888), (0.2716694150652204, 0.1761405573572431, 0.3680432620502653)]; category=content; control=False.
- E56/adjective_implicit: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.35314362815448214, 0.06812920676810401, 0.6673247040382453), (0.04376862191018603, 0.016554159174362818, 0.07291858255153609), (3.0747927938188826, 2.477573703371343, 3.686155878858907), (0.3093750062442961, 0.028347297573373408, 0.6148139709943814)]; category=syntactic; control=False.
- E56/fact_recall: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.3389135826201666, 0.235109577079614, 0.44606585105260205), (0.3836308870996748, 0.365583996744383, 0.4023445352060454), (5.49646570568993, 4.941838670770327, 5.998349103757313), (-0.044717304479508196, -0.15796228973638443, 0.06887364239919748)]; category=content; control=False.
- E56/language_continuation: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.3541666269302368, -0.5528273193609147, -0.13577935085410167), (-0.025520824250720796, -0.07745531652654919, 0.029765644527616927), (2.6801990327380953, 2.2272170464197796, 3.1154575620378764), (-0.32864580267951604, -0.5183928141991297, -0.11871093923137323)]; category=format; control=False.
- E56/rhyme_plan: n=84; J, random mean5, PCA, J-random estimates/CIs: [(1.6796874868727865, 1.481008180093375, 1.8784039740539376), (-0.18921130455675578, -0.23251486228512866, -0.14515994465067275), (-0.6659226172736713, -1.3681687130858857, 0.06885693359321764), (1.868898791429542, 1.6766331728893735, 2.05494604493447)]; category=content; control=True.
- E56/tense_implicit: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.20684524377187094, 0.15476190717447372, 0.2619233794155574), (0.08407739457629974, 0.05565101647660845, 0.1130952387338593), (1.677455382687705, 1.509644710095156, 1.8474795780011584), (0.12276784919557118, 0.07767856673115775, 0.16563614770060486)]; category=syntactic; control=False.
- E57/antonym_crosslingual: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.1605791477929978, -0.2509871318226769, 0.5854230639480403), (0.30179424058823356, 0.2662449008510226, 0.33819927192869637), (3.150827475956508, 2.625713288784027, 3.6256455273855295), (-0.14121509279523575, -0.5309989567030043, 0.26744352828888657)]; category=content; control=True.
- E57/clause_pending: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.29548142069862005, -0.43285169033777143, -0.15402317103885477), (0.17290658723740351, 0.14024791632379807, 0.20656389287539892), (1.8201657022748674, 1.4011135958489918, 2.28033530428296), (-0.4683880079360235, -0.6213144176346915, -0.3136184181485858)]; category=syntactic; control=False.
- E57/indent_level: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.05017666873477754, -0.09812506181853159, -0.005483771718683705), (-0.06665239958536057, -0.09527911718402589, -0.037173896815095656), (-0.4159331066267831, -0.5851970972049805, -0.24888749392259701), (0.016475730850583032, -0.04462856690088908, 0.07142726966312953)]; category=bookkeeping; control=False.
- E57/nesting_depth: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.1767974098523458, 0.06289892686264856, 0.30379675420976815), (-0.012620309420994352, -0.03771302944137936, 0.013606240124929515), (-0.08346118103890192, -0.37856413001815475, 0.23407039007260666), (0.18941771927334017, 0.06941918750603993, 0.3179057425402459)]; category=bookkeeping; control=False.
- E57/sentiment_judgement: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.802083371650605, 0.6152902069191138, 0.9829055432407628), (0.01026788694517953, -0.008337028544573556, 0.028571455010346004), (2.487537232183275, 2.251357924299581, 2.739341575226613), (0.7918154847054256, 0.6124963004461357, 0.9626637028441543)]; category=content; control=False.
- E57/subject_number: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.5892856972558158, -0.6856677586124057, -0.49362906501406745), (-0.044345252854483465, -0.07745726142610822, -0.01287013385977065), (0.6681547619047619, 0.5487164616584778, 0.791313280519985), (-0.5449404444013324, -0.6643731000309898, -0.4248977128948485)]; category=syntactic; control=False.
- E57/two_hop_answer: n=84; J, random mean5, PCA, J-random estimates/CIs: [(0.24107144134385244, 0.10338537082785651, 0.3824777057128291), (0.09196429366157169, 0.0663690950969855, 0.11726190955865952), (0.15104167943909055, -0.04242926853753271, 0.32965030808533924), (0.14910714768228076, -0.002113075965926755, 0.29689362963040666)]; category=content; control=True.
- E57/page_range_digit: n=84; J, random mean5, PCA, J-random estimates/CIs: [(-0.27232139451163156, -0.3043154594444093, -0.24181541332176754), (0.10357140927087695, 0.08630580340112959, 0.12098959346612288), (1.5572916467984517, 1.3883928577105202, 1.7232514456624075), (-0.3758928037825085, -0.413839256366094, -0.33988092944735576)]; category=bookkeeping; control=False.

## E79 partial sealed evidence (full R-C1/R-C2 remain PENDING)

Norm diagnostic source DIAGNOSTICS.json, commit 9a045263 2026-10-28T05:18:41+01:00. Recounted from sealed per-item ratios:
- nesting_depth, J, alpha=2: >1.5 1/84, maximum 1.514893894.
- nesting_depth, nonJ, alpha=2: >1.5 19/84, maximum 1.683232624.
- nesting_depth, J, alpha=4: >1.5 84/84, maximum 2.365585744.
- nesting_depth, nonJ, alpha=4: >1.5 84/84, maximum 2.583163388.
- nesting_depth, random, alpha=4: >1.5 84/84, maximum 2.233773628.
- indent_level, J, alpha=2: >1.5 84/84, maximum 1.710027141.
- indent_level, nonJ, alpha=2: >1.5 36/84, maximum 1.836642381.
- indent_level, random, alpha=2: >1.5 84/84, maximum 1.640287569.
- indent_level, J, alpha=4: >1.5 84/84, maximum 2.863431752.
- indent_level, nonJ, alpha=4: >1.5 84/84, maximum 3.015365089.
- indent_level, random, alpha=4: >1.5 84/84, maximum 2.783641195.
Norm diagnostic source NORM_RATIOS.json, commit aff86f8f 2026-10-28T05:30:16+01:00. Recounted from sealed per-item ratios:
Manipulation: sealed probe summary shows all J/nonJ cells positive but random nesting_depth fails: [('nesting_depth', 'random:0.25', 0, 84, -0.02349927028020223), ('nesting_depth', 'random:0.5', 0, 84, -0.04699877897898356), ('nesting_depth', 'random:1', 0, 84, -0.09399762891587757), ('nesting_depth', 'random:2', 0, 84, -0.18799519255047753), ('nesting_depth', 'random:4', 0, 84, -0.375990473088764)]. Literal check **“moves toward the target in every non-zero cell”** is NOT MET. Whether this gates R-C1 is NOT EVALUABLE (ambiguous): no consequence is specified. No worker interpretation adopted. Independent probe refit outstanding; summary is not presented as a raw recomputation.
- R-C2 behaviour only, format_plan: {'none': 0.5668934240362812, 'd_J': 0.5722789115646258, 'd_perp': 0.5711451247165533, 'random': 0.5660430839002267}; n=84 each; delta=0.005385487528, condition MET; exact worker match. Independent pair-ranking AUROC from raw logits. Reader S contrast pending.
- R-C2 behaviour only, language_plan: {'none': 0.8656462585034014, 'd_J': 0.8370181405895691, 'd_perp': 0.7891156462585034, 'random': 0.8645124716553289}; n=84 each; delta=-0.028628117914, condition MET; exact worker match. Independent pair-ranking AUROC from raw logits. Reader S contrast pending.

## Remaining sealed rule checks

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E57 oracle | R-A2 | NOT MET | {'think': 0.14285714285714285, 'mention': 0.21428571428571427, 'ignore': 0.13095238095238096, 'none': 0.0}; think-none (0.14285714285714285, 0.07142857142857142, 0.21428571428571427); n=84/arm | Oracle NOT MET; NLA MET | db69c4ce | Exact raw-text regex/paired-bootstrap match. |
| E57 nla | R-A2 | MET | {'think': 0.10714285714285714, 'mention': 0.10714285714285714, 'ignore': 0.09523809523809523, 'none': 0.005952380952380952}; think-none (0.10119047619047619, 0.047619047619047616, 0.16666666666666666); n=84/arm | Oracle NOT MET; NLA MET | db69c4ce | Exact raw-text regex/paired-bootstrap match. |
| E62 Oracle | R-L4 | NOT MET | C4-C0=(-0.6904761904761905, -0.7857142857142857, -0.5833333333333334); n=84 | -0.6904761904761905 [-.7857142857142857,-.5833333333333334] | dc6ebc49 2026-10-27T16:15:09+01:00 | Raw Boolean judgment paired-bootstrap check. |

## Registration and clarification chronology

Legend: C< / C>= = amendment commit before / at-or-after first committed analysis. O< / O>= = before / at-or-after earliest verified sealed raw-member mtime. C comparisons alone do not establish first-generation ordering.

Git history was queried on the BRIEF itself (first added exact header line), not the time claimed in prose. Comparison below is to the first committed sealed analysis artifact, an observable upper bound on generation time. **This does not prove that an amendment preceded the first generated output.** Where sealed first-generation timestamps/retained-pilot ordering are not resolved, chronology remains NOT EVALUABLE; scientific calculations above are provisional with respect to that provenance check. Unsealed experiments remain PENDING. Shared dated operational/judging notes are repeated conservatively; applicability to a specific output must not be inferred from date alone.

### E56
First committed sealed artifact checked: 57074675ee21ee179362747623899fafa1722329 2026-10-27T15:23:03+01:00; `results/g_agreement/understand/e56/analysis402_once_2026-10-27/RESULTS.json`.
- Registration heading line 3456: ## §172 E56. Does any reader report what the workspace paper says is outside the workspace?; first-add commit 4c187fda628073c7d8a392caec6d3974107f86c6 2026-10-27T02:49:47+01:00.
- BRIEF L3458: **Registered 2026-10-27 02:55 CET, before any E56 item exists. CONFIRMATORY for R1–R3.** **Owners:** W-text (bank,; commit `4c187fda 2026-10-27T02:49:47+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3513: **§172 E56 clarification 1 (2026-10-27 03:05 CET, answers W-text, before any E56 item exists).**; commit `0f1e4dd7 2026-10-27T02:55:36+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3529: **§172 E56 clarification 2 (2026-10-27 05:10 CET, answers W-mechanism's QUESTIONS.md `c4ac59e1`, before any E56 score; applies identically to E57 §173 and E59 §175).**; commit `3ada24fb 2026-10-27T05:03:46+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3548: **§172 E56 clarification 3 (2026-10-27 05:50 CET, before any E56/E57/E59/E61/E62/E63 NLA readout exists).** E49's; commit `259db20a 2026-10-27T05:40:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3558: **§172 E56 clarification 4 (2026-10-27 06:10 CET, before any E56/E57/E59/E61/E62/E63 reader output exists; design error corrected).** Greedy decoding is deterministic, so "8 greedy readouts per item" yields 8 identical; commit `8c66b004 2026-10-27T06:00:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3608: **Registered 2026-10-27 04:05 CET, before any E57 item exists. CONFIRMATORY for the rules marked R; the rest DESCRIPTIVE.** **Owners:** W-text (bank), W-mechanism (runner, extending the E56 runner), W-lens (J-lens reader and; commit `80033b37 2026-10-27T03:54:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3671: **Registered 2026-10-27 04:05 CET. E58a uses labels W-lens has already computed (`9fdea554`) but that the coordinator has not opened; the category assignment below is made blind to them. E58b is new compute.** **Owners:** W-text; commit `80033b37 2026-10-27T03:54:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3699: **§173 E57 clarification 1 (2026-10-27 04:20 CET, answers W-text, before the E57 freeze).** (a) count_gradient reuses; commit `6e58d7d1 2026-10-27T04:13:39+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3727: **§174 E58 clarification 2 (2026-10-27 04:25 CET, before any E58 fit or score).** E58b adds a DESCRIPTIVE; commit `be4d4e87 2026-10-27T04:18:15+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3744: **Registered 2026-10-27 04:55 CET, before any E59 item exists. CONFIRMATORY for R1; R2 DESCRIPTIVE.** **Owners:**; commit `94fd96aa 2026-10-27T04:51:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3778: **Registered 2026-10-27 04:55 CET. DESCRIPTIVE with one rule.** **Owner:** W-lens. **Cost:** CPU.; commit `94fd96aa 2026-10-27T04:51:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3789: **Registered 2026-10-27 05:20 CET, before any E61 item or E56/E57/E59 reader output exists.** Items D1, D2, D5, D6; commit `84a5a4b7 2026-10-27T05:13:53+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3820: **§177 E61 clarification 1 (2026-10-27 05:35 CET, answers W-mechanism, before any E56/E57/E61 reader output is opened).** The display selection rule draws only from items whose native readouts the registered runs acquire: the; commit `6f9088bb 2026-10-27T05:29:02+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3828: **Registered 2026-10-27 05:30 CET, before any E62 item exists. CONFIRMATORY for R-L1–R-L3; eval ladder DESCRIPTIVE with one rule.** **Owners:** W-text (bank, freeze by **11:00 CET**, after E61's D3/D4 banks), W-mechanism (runner,; commit `cde36cc9 2026-10-27T05:26:56+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3879: **Registered 2026-10-27 05:40 CET, before any placebo readout and before any E56/E57/E59/E62 reader output is opened. CONFIRMATORY for R-P1; R-P2 DESCRIPTIVE.** **Owners:** W-mechanism (runner, unchanged native channel), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3901: **Registered 2026-10-27 05:40 CET. No scientific rule; a deliverable.** **Owners:** W-core (package), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3916: **Registered 2026-10-27 05:55 CET, after E49/E52 R3 (uninformative at n = 8, 2 REPORTED) and before any reader output of E56, E57, E59 or E62 is opened. CONFIRMATORY.** **Owners:** W-lens (forecast), integrator (custody and ordering).; commit `061d0e4a 2026-10-27T05:42:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3941: **Registered 2026-10-27 06:20 CET, before E60 is fitted and before any E56/E57/E59/E62 reader output is opened. CONFIRMATORY for R-C1; R-C2 DESCRIPTIVE.** **Owners:** W-text (value-persistence measure), W-lens (directional; commit `ad4e4467 2026-10-27T06:15:38+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3981: **§182 E65 clarification 2 (2026-10-27 06:35 CET, after the integrator's capture inventory and before any E65 value or any affected reader output is opened).** No sealed capture stores all prompt positions (≈ 287 arrays, all; commit `db81ff0b 2026-10-27T06:20:31+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4042: **§172 E56 R4 clarification 1 (2026-10-27 08:05 CET, before any R4 readout is opened).** R4 is interpretable only for; commit `f21ed03e 2026-10-27T07:51:18+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4080: **§149 compute deviation (2026-10-27 08:55 CET, Guiv's decision, before any E56/E57/E61 reader output exists).** All; commit `32c55cb7 2026-10-27T08:47:09+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4122: **§172 / §173 clarification (2026-10-27 14:15 CET, answers W-lens, before any E56/E57 reader outcome is opened).**; commit `09494e79 2026-10-27T14:09:07+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4178: **Registered 2026-10-27 15:10 CET. CONFIRMATORY for R-F1 and R-F2; R-F3 DESCRIPTIVE.** **Owners:** W-sae (sampling; commit `bbefdae2 2026-10-27T14:58:48+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4244: **Registered 2026-10-27 15:40 CET. CONFIRMATORY.** **Owners:** W-internals (vectors, from E56 R4 machinery), W-mechanism; commit `8b2012d7 2026-10-27T15:10:42+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4255: **Registered 2026-10-27 15:40 CET. DESCRIPTIVE with one rule.** **Owners:** two human coders (Guiv and one colleague; commit `8b2012d7 2026-10-27T15:10:42+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4270: **§169 reporting clarification (2026-10-27 15:40 CET).** Every J-fraction table reports the null distribution's median; commit `8b2012d7 2026-10-27T15:10:42+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4397: ### §188 E71 clarification 1 (2026-10-27 16:00 CET, before any human coding) The packet must draw from the registered pool (E49, E54, D4 and, now sealed, E56), not from E54 alone: 25 per reader × status stratum, uniform over eligible sealed items across those banks with seed 20261027. The E54-only packet; commit `24070152 2026-10-27T15:29:43+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4451: ### §188 E71 clarification 2 (2026-10-27 16:50 CET) The rebuilt packet (8bac3e82; E49, E54, D4 and E56; 25 per reader × status stratum; seed 20261027) is the E71 packet. The coders are Guiv and one colleague not on the analysis. Each codes independently, without the judge output, and; commit `f8f38c60 2026-10-27T15:40:50+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4536: ### §184 E67 clarification 2 (2026-10-27 22:20 CET; ruling recorded pre-run in HANDOFF 9d763f63 before any wave-1 result) E67 is analysed in two waves. Wave 1 (E49, E54, E61 D4) had its once-only analysis at 21:14Z (seal 92f74fe0). Wave 2 (E56, E57) is a separate, later once-only analysis with the same frozen code and spec. It is reported separately and; commit `c949f909 2026-10-27T22:16:01+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4609: ### §194 E76 clarification 2: judged floors (2026-10-28 05:15 CET, before any E76 judgment) Judged floors matter only where a row is claimed REPORTED, and the USD 2 budget cannot cover all 151 regex rows × 1,000 readouts × 2 readers (~300k records). ; commit `f3fcb715 2026-10-28T05:09:07+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4620: **Registered 2026-10-28 05:30 CET, before any E79 vector, readout or judgment exists, and before E56's R4 or E70's outcomes have been read by the coordinator. CONFIRMATORY for R-C1, R-C2.**; commit `a12526c5 2026-10-28T05:14:36+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.

### E57
First committed sealed artifact checked: db69c4ce04285cec4ca91415df12db084a381bb8 2026-10-27T15:52:15+01:00; `results/g_agreement/understand/e57/analysis402_once_2026-10-27/RESULTS.json`.
- Registration heading line 3606: ## §173 E57. More workspace-paper properties: multi-token, focus/ignore, persistence, capacity, syntax; first-add commit 80033b37098552724b07bb5d1de746a6a800fbe8 2026-10-27T03:54:04+01:00.
- BRIEF L3529: **§172 E56 clarification 2 (2026-10-27 05:10 CET, answers W-mechanism's QUESTIONS.md `c4ac59e1`, before any E56 score; applies identically to E57 §173 and E59 §175).**; commit `3ada24fb 2026-10-27T05:03:46+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3548: **§172 E56 clarification 3 (2026-10-27 05:50 CET, before any E56/E57/E59/E61/E62/E63 NLA readout exists).** E49's; commit `259db20a 2026-10-27T05:40:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3558: **§172 E56 clarification 4 (2026-10-27 06:10 CET, before any E56/E57/E59/E61/E62/E63 reader output exists; design error corrected).** Greedy decoding is deterministic, so "8 greedy readouts per item" yields 8 identical; commit `8c66b004 2026-10-27T06:00:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3608: **Registered 2026-10-27 04:05 CET, before any E57 item exists. CONFIRMATORY for the rules marked R; the rest DESCRIPTIVE.** **Owners:** W-text (bank), W-mechanism (runner, extending the E56 runner), W-lens (J-lens reader and; commit `80033b37 2026-10-27T03:54:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3655: **§173 amendment 1 (2026-10-27 04:15 CET, before any E57 item exists).** The paper names three low-J SAE features; commit `869c8a10 2026-10-27T04:13:08+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3699: **§173 E57 clarification 1 (2026-10-27 04:20 CET, answers W-text, before the E57 freeze).** (a) count_gradient reuses; commit `6e58d7d1 2026-10-27T04:13:39+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3709: **§173 E57 clarification 2 (2026-10-27 05:15 CET, answers W-sae, before any E58b score; frozen continuation pairs for Group B, bank items unchanged).** Row 7 subject_number: " barn is" vs " barn are". Row 8 clause_pending: §173's; commit `a52cdb11 2026-10-27T05:08:57+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3727: **§174 E58 clarification 2 (2026-10-27 04:25 CET, before any E58 fit or score).** E58b adds a DESCRIPTIVE; commit `be4d4e87 2026-10-27T04:18:15+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3744: **Registered 2026-10-27 04:55 CET, before any E59 item exists. CONFIRMATORY for R1; R2 DESCRIPTIVE.** **Owners:**; commit `94fd96aa 2026-10-27T04:51:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3778: **Registered 2026-10-27 04:55 CET. DESCRIPTIVE with one rule.** **Owner:** W-lens. **Cost:** CPU.; commit `94fd96aa 2026-10-27T04:51:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3789: **Registered 2026-10-27 05:20 CET, before any E61 item or E56/E57/E59 reader output exists.** Items D1, D2, D5, D6; commit `84a5a4b7 2026-10-27T05:13:53+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3820: **§177 E61 clarification 1 (2026-10-27 05:35 CET, answers W-mechanism, before any E56/E57/E61 reader output is opened).** The display selection rule draws only from items whose native readouts the registered runs acquire: the; commit `6f9088bb 2026-10-27T05:29:02+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3879: **Registered 2026-10-27 05:40 CET, before any placebo readout and before any E56/E57/E59/E62 reader output is opened. CONFIRMATORY for R-P1; R-P2 DESCRIPTIVE.** **Owners:** W-mechanism (runner, unchanged native channel), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3901: **Registered 2026-10-27 05:40 CET. No scientific rule; a deliverable.** **Owners:** W-core (package), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3916: **Registered 2026-10-27 05:55 CET, after E49/E52 R3 (uninformative at n = 8, 2 REPORTED) and before any reader output of E56, E57, E59 or E62 is opened. CONFIRMATORY.** **Owners:** W-lens (forecast), integrator (custody and ordering).; commit `061d0e4a 2026-10-27T05:42:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3933: **§181 clarification 1 (2026-10-27 06:00 CET, answers W-lens, before any forecast or reader output).** R3b covers only; commit `2ba13670 2026-10-27T05:43:55+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3941: **Registered 2026-10-27 06:20 CET, before E60 is fitted and before any E56/E57/E59/E62 reader output is opened. CONFIRMATORY for R-C1; R-C2 DESCRIPTIVE.** **Owners:** W-text (value-persistence measure), W-lens (directional; commit `ad4e4467 2026-10-27T06:15:38+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L3981: **§182 E65 clarification 2 (2026-10-27 06:35 CET, after the integrator's capture inventory and before any E65 value or any affected reader output is opened).** No sealed capture stores all prompt positions (≈ 287 arrays, all; commit `db81ff0b 2026-10-27T06:20:31+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved. O< 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4080: **§149 compute deviation (2026-10-27 08:55 CET, Guiv's decision, before any E56/E57/E61 reader output exists).** All; commit `32c55cb7 2026-10-27T08:47:09+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4122: **§172 / §173 clarification (2026-10-27 14:15 CET, answers W-lens, before any E56/E57 reader outcome is opened).**; commit `09494e79 2026-10-27T14:09:07+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4207: **Follow-on and rendering rulings (2026-10-27 15:15 CET, before any E57, E59, E63 or D4a judgment or reader outcome is opened).** (a) **List values in rubric fields** (E57 antonym_crosslingual, 168 records): a list is rendered as its; commit `55833480 2026-10-27T15:01:00+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4234: **Registered 2026-10-27 15:40 CET. CONFIRMATORY.** **Owners:** W-text (bank), W-mechanism (forward-only runner),; commit `8b2012d7 2026-10-27T15:10:42+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4352: **Registered 2026-10-27 15:30 CET. CONFIRMATORY if run.** Following Ostrow et al. (arXiv:2610.31955), build lag-specific; commit `a68a228d 2026-10-27T15:22:20+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4536: ### §184 E67 clarification 2 (2026-10-27 22:20 CET; ruling recorded pre-run in HANDOFF 9d763f63 before any wave-1 result) E67 is analysed in two waves. Wave 1 (E49, E54, E61 D4) had its once-only analysis at 21:14Z (seal 92f74fe0). Wave 2 (E56, E57) is a separate, later once-only analysis with the same frozen code and spec. It is reported separately and; commit `c949f909 2026-10-27T22:16:01+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4609: ### §194 E76 clarification 2: judged floors (2026-10-28 05:15 CET, before any E76 judgment) Judged floors matter only where a row is claimed REPORTED, and the USD 2 budget cannot cover all 151 regex rows × 1,000 readouts × 2 readers (~300k records). ; commit `f3fcb715 2026-10-28T05:09:07+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4620: **Registered 2026-10-28 05:30 CET, before any E79 vector, readout or judgment exists, and before E56's R4 or E70's outcomes have been read by the coordinator. CONFIRMATORY for R-C1, R-C2.**; commit `a12526c5 2026-10-28T05:14:36+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4789: **Registered 2026-10-28 10:15 CET, before any E81 output exists. CONFIRMATORY for R-T1.**; commit `5040ca28 2026-10-28T10:01:27+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.
- BRIEF L4828: **Registered 2026-10-28 10:15 CET, before any E83 output. DESCRIPTIVE.**; commit `5040ca28 2026-10-28T10:01:27+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T07:34:36+00:00; stage applicability unresolved.

### E58
First committed sealed artifact checked: cc0346b306c92a67773671171e0e5d2b47471f72 2026-10-27T06:54:05+01:00; `results/g_agreement/understand/e58b/analysis_20261027/RESULTS.json`.
- Registration heading line 3669: ## §174 E58. Is bookkeeping computed beneath the workspace on Qwen? (labels and ablation); first-add commit 80033b37098552724b07bb5d1de746a6a800fbe8 2026-10-27T03:54:04+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved.
- BRIEF L3671: **Registered 2026-10-27 04:05 CET. E58a uses labels W-lens has already computed (`9fdea554`) but that the coordinator has not opened; the category assignment below is made blind to them. E58b is new compute.** **Owners:** W-text; commit `80033b37 2026-10-27T03:54:04+01:00`; C<; generation ordering unresolved.
- BRIEF L3709: **§173 E57 clarification 2 (2026-10-27 05:15 CET, answers W-sae, before any E58b score; frozen continuation pairs for Group B, bank items unchanged).** Row 7 subject_number: " barn is" vs " barn are". Row 8 clause_pending: §173's; commit `a52cdb11 2026-10-27T05:08:57+01:00`; C<; generation ordering unresolved.
- BRIEF L3718: **§174 E58 clarification 1 (2026-10-27 04:20 CET, answers W-sae and W-lens, before any E58 fit or score).** (a) E58b's; commit `6e58d7d1 2026-10-27T04:13:39+01:00`; C<; generation ordering unresolved.
- BRIEF L3727: **§174 E58 clarification 2 (2026-10-27 04:25 CET, before any E58 fit or score).** E58b adds a DESCRIPTIVE; commit `be4d4e87 2026-10-27T04:18:15+01:00`; C<; generation ordering unresolved.
- BRIEF L3901: **Registered 2026-10-27 05:40 CET. No scientific rule; a deliverable.** **Owners:** W-core (package), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved.
- BRIEF L3996: **§174 E58b dated note (2026-10-27 07:25 CET, coordinator, AFTER reading E58b's sealed results `cc0346b3`; POST HOC, DESCRIPTIVE).** Verdicts as registered: R-b1 HOLDS (2/3), **R-b2 DOES NOT HOLD (15/25)**. Design error owned: R-b2; commit `db55584a 2026-10-27T07:16:08+01:00`; C>=; generation ordering unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C>=; generation ordering unresolved.
- BRIEF L4029: **§181 R3b clarification 2 (2026-10-27 07:55 CET, before any forecast is scored).** R3b is also scored against the; commit `6aacc13d 2026-10-27T07:47:59+01:00`; C>=; generation ordering unresolved.
- BRIEF L4035: **§181 R3b clarification 3 (2026-10-27 08:05 CET, before any forecast is scored).** **Within-category test:** R3b is; commit `f21ed03e 2026-10-27T07:51:18+01:00`; C>=; generation ordering unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C>=; generation ordering unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C>=; generation ordering unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C>=; generation ordering unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C>=; generation ordering unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C>=; generation ordering unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C>=; generation ordering unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C>=; generation ordering unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C>=; generation ordering unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C>=; generation ordering unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C>=; generation ordering unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C>=; generation ordering unresolved.
- BRIEF L5074: ### §197 E80c clarification 1 and a reporting rule (2026-10-28 11:20 CET, before any E80c vector or output) 1. ; commit `8f3cba53 2026-10-28T10:48:44+01:00`; C>=; generation ordering unresolved.

### E59
First committed sealed artifact checked: 2b72dbbc26526a8647bef8c8727b3d846d774f73 2026-10-27T23:00:02+01:00; `results/g_agreement/understand/e59/analysis5968_once_2026-10-27/RESULTS.json`.
- Registration heading line 3742: ## §175 E59. Do the readers see the model's plans and intentions? (in-workspace content a monitor wants); first-add commit 94fd96aa17577f0b4cb0ac34fc213d742966e0a9 2026-10-27T04:51:59+01:00.
- BRIEF L3529: **§172 E56 clarification 2 (2026-10-27 05:10 CET, answers W-mechanism's QUESTIONS.md `c4ac59e1`, before any E56 score; applies identically to E57 §173 and E59 §175).**; commit `3ada24fb 2026-10-27T05:03:46+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3548: **§172 E56 clarification 3 (2026-10-27 05:50 CET, before any E56/E57/E59/E61/E62/E63 NLA readout exists).** E49's; commit `259db20a 2026-10-27T05:40:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3558: **§172 E56 clarification 4 (2026-10-27 06:10 CET, before any E56/E57/E59/E61/E62/E63 reader output exists; design error corrected).** Greedy decoding is deterministic, so "8 greedy readouts per item" yields 8 identical; commit `8c66b004 2026-10-27T06:00:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3744: **Registered 2026-10-27 04:55 CET, before any E59 item exists. CONFIRMATORY for R1; R2 DESCRIPTIVE.** **Owners:**; commit `94fd96aa 2026-10-27T04:51:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3778: **Registered 2026-10-27 04:55 CET. DESCRIPTIVE with one rule.** **Owner:** W-lens. **Cost:** CPU.; commit `94fd96aa 2026-10-27T04:51:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3789: **Registered 2026-10-27 05:20 CET, before any E61 item or E56/E57/E59 reader output exists.** Items D1, D2, D5, D6; commit `84a5a4b7 2026-10-27T05:13:53+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3879: **Registered 2026-10-27 05:40 CET, before any placebo readout and before any E56/E57/E59/E62 reader output is opened. CONFIRMATORY for R-P1; R-P2 DESCRIPTIVE.** **Owners:** W-mechanism (runner, unchanged native channel), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3901: **Registered 2026-10-27 05:40 CET. No scientific rule; a deliverable.** **Owners:** W-core (package), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3916: **Registered 2026-10-27 05:55 CET, after E49/E52 R3 (uninformative at n = 8, 2 REPORTED) and before any reader output of E56, E57, E59 or E62 is opened. CONFIRMATORY.** **Owners:** W-lens (forecast), integrator (custody and ordering).; commit `061d0e4a 2026-10-27T05:42:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3941: **Registered 2026-10-27 06:20 CET, before E60 is fitted and before any E56/E57/E59/E62 reader output is opened. CONFIRMATORY for R-C1; R-C2 DESCRIPTIVE.** **Owners:** W-text (value-persistence measure), W-lens (directional; commit `ad4e4467 2026-10-27T06:15:38+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L3981: **§182 E65 clarification 2 (2026-10-27 06:35 CET, after the integrator's capture inventory and before any E65 value or any affected reader output is opened).** No sealed capture stores all prompt positions (≈ 287 arrays, all; commit `db81ff0b 2026-10-27T06:20:31+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4207: **Follow-on and rendering rulings (2026-10-27 15:15 CET, before any E57, E59, E63 or D4a judgment or reader outcome is opened).** (a) **List values in rubric fields** (E57 antonym_crosslingual, 168 records): a list is rendered as its; commit `55833480 2026-10-27T15:01:00+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4461: ### §176 E59 deviation (2026-10-27 16:55 CET, before any E59 readout is opened) E59's reader GO was bound to an unpublished commit whose forecast file is byte-identical to c2dbe177 (committed 14:37:30Z, before the first E59 reader job). Custody held: the forecast is fixed and timestamped before readers. The run; commit `bb9f3931 2026-10-27T15:43:05+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4498: ### §194 E76 compute deviation (2026-10-27 17:20 CET, before any E76 capture) The measured phases need about 3,400–3,700 s before the worker's 1.5× margin, which exceeds the registered ≤ 1 GPU-h. The cap is raised to 6,100 s (≈ USD 9), on E59's pod after its same-pod parity pass. Scope, n, norms and analysis are; commit `bbed7f84 2026-10-27T16:14:10+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4609: ### §194 E76 clarification 2: judged floors (2026-10-28 05:15 CET, before any E76 judgment) Judged floors matter only where a row is claimed REPORTED, and the USD 2 budget cannot cover all 151 regex rows × 1,000 readouts × 2 readers (~300k records). ; commit `f3fcb715 2026-10-28T05:09:07+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4620: **Registered 2026-10-28 05:30 CET, before any E79 vector, readout or judgment exists, and before E56's R4 or E70's outcomes have been read by the coordinator. CONFIRMATORY for R-C1, R-C2.**; commit `a12526c5 2026-10-28T05:14:36+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4659: ### §196 E79 clarification 1 (2026-10-28 05:35 CET, before any E79 vector or output exists) §196 wrongly described E59's continuation scorer as producing a binary plan-execution rate. In fact it is a first-token contrast score (format: '-' vs 'The'; language: 'Je'/'Le' vs 'The') summarised as AUROC. Arm B's behaviour check is; commit `b3c1e6d0 2026-10-28T05:17:11+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.
- BRIEF L4789: **Registered 2026-10-28 10:15 CET, before any E81 output exists. CONFIRMATORY for R-T1.**; commit `5040ca28 2026-10-28T10:01:27+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T14:37:36+00:00; opening/judging boundary separate.

### E60
First committed sealed artifact checked: none located.
- Registration heading line 3776: ## §176 E60. Blind-spot predictor (CPU; after E49, E56, E57, E59 analyses); first-add commit 94fd96aa17577f0b4cb0ac34fc213d742966e0a9 2026-10-27T04:51:59+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L3941: **Registered 2026-10-27 06:20 CET, before E60 is fitted and before any E56/E57/E59/E62 reader output is opened. CONFIRMATORY for R-C1; R-C2 DESCRIPTIVE.** **Owners:** W-text (value-persistence measure), W-lens (directional; commit `ad4e4467 2026-10-27T06:15:38+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

### E61
First committed sealed artifact checked: b7232c539a39652704a3ffa945e4500d03ea9838 2026-10-27T14:42:14+01:00; `results/g_agreement/understand/e61/d4_stage_analysis/RESULTS.json`.
- Registration heading line 3787: ## §177 E61. Demonstrations and the white-bear test; first-add commit 84a5a4b77ea2cf1cb200a723f66adc31c9ef8e46 2026-10-27T05:13:53+01:00.
- BRIEF L3529: **§172 E56 clarification 2 (2026-10-27 05:10 CET, answers W-mechanism's QUESTIONS.md `c4ac59e1`, before any E56 score; applies identically to E57 §173 and E59 §175).**; commit `3ada24fb 2026-10-27T05:03:46+01:00`; C<; generation ordering unresolved.
- BRIEF L3548: **§172 E56 clarification 3 (2026-10-27 05:50 CET, before any E56/E57/E59/E61/E62/E63 NLA readout exists).** E49's; commit `259db20a 2026-10-27T05:40:04+01:00`; C<; generation ordering unresolved.
- BRIEF L3558: **§172 E56 clarification 4 (2026-10-27 06:10 CET, before any E56/E57/E59/E61/E62/E63 reader output exists; design error corrected).** Greedy decoding is deterministic, so "8 greedy readouts per item" yields 8 identical; commit `8c66b004 2026-10-27T06:00:59+01:00`; C<; generation ordering unresolved.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved.
- BRIEF L3789: **Registered 2026-10-27 05:20 CET, before any E61 item or E56/E57/E59 reader output exists.** Items D1, D2, D5, D6; commit `84a5a4b7 2026-10-27T05:13:53+01:00`; C<; generation ordering unresolved.
- BRIEF L3820: **§177 E61 clarification 1 (2026-10-27 05:35 CET, answers W-mechanism, before any E56/E57/E61 reader output is opened).** The display selection rule draws only from items whose native readouts the registered runs acquire: the; commit `6f9088bb 2026-10-27T05:29:02+01:00`; C<; generation ordering unresolved.
- BRIEF L3828: **Registered 2026-10-27 05:30 CET, before any E62 item exists. CONFIRMATORY for R-L1–R-L3; eval ladder DESCRIPTIVE with one rule.** **Owners:** W-text (bank, freeze by **11:00 CET**, after E61's D3/D4 banks), W-mechanism (runner,; commit `cde36cc9 2026-10-27T05:26:56+01:00`; C<; generation ordering unresolved.
- BRIEF L3901: **Registered 2026-10-27 05:40 CET. No scientific rule; a deliverable.** **Owners:** W-core (package), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved.
- BRIEF L3981: **§182 E65 clarification 2 (2026-10-27 06:35 CET, after the integrator's capture inventory and before any E65 value or any affected reader output is opened).** No sealed capture stores all prompt positions (≈ 287 arrays, all; commit `db81ff0b 2026-10-27T06:20:31+01:00`; C<; generation ordering unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved.
- BRIEF L4013: **§177 E61 D4 amendment 1 (2026-10-27 07:55 CET, before any D4 readout is opened; D4a is a second bank, D4's registered rule and bank are unchanged).** **D4a, robustness:** two further concepts, **musical instruments** and; commit `6aacc13d 2026-10-27T07:47:59+01:00`; C<; generation ordering unresolved.
- BRIEF L4049: **§177 E61 D4a amendment 2 (2026-10-27 08:05 CET, before D4a is frozen).** Two additions to D4a to separate "the; commit `f21ed03e 2026-10-27T07:51:18+01:00`; C<; generation ordering unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved.
- BRIEF L4080: **§149 compute deviation (2026-10-27 08:55 CET, Guiv's decision, before any E56/E57/E61 reader output exists).** All; commit `32c55cb7 2026-10-27T08:47:09+01:00`; C<; generation ordering unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C>=; generation ordering unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C>=; generation ordering unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C>=; generation ordering unresolved.
- BRIEF L4536: ### §184 E67 clarification 2 (2026-10-27 22:20 CET; ruling recorded pre-run in HANDOFF 9d763f63 before any wave-1 result) E67 is analysed in two waves. Wave 1 (E49, E54, E61 D4) had its once-only analysis at 21:14Z (seal 92f74fe0). Wave 2 (E56, E57) is a separate, later once-only analysis with the same frozen code and spec. It is reported separately and; commit `c949f909 2026-10-27T22:16:01+01:00`; C>=; generation ordering unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C>=; generation ordering unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C>=; generation ordering unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C>=; generation ordering unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C>=; generation ordering unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C>=; generation ordering unresolved.

### E62
First committed sealed artifact checked: dc6ebc49784a3850a1c2ac47b3dd237d496ad267 2026-10-27T16:15:09+01:00; `results/g_agreement/understand/e62/analysis402_once_2026-10-27/RESULTS.json`.
- Registration heading line 3826: ## §178 E62. The Workspace Ladder: same state, five rungs into the workspace; first-add commit cde36cc9da3a4ef93ce1b78af91a5560bc1e65fc 2026-10-27T05:26:56+01:00.
- BRIEF L3529: **§172 E56 clarification 2 (2026-10-27 05:10 CET, answers W-mechanism's QUESTIONS.md `c4ac59e1`, before any E56 score; applies identically to E57 §173 and E59 §175).**; commit `3ada24fb 2026-10-27T05:03:46+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3548: **§172 E56 clarification 3 (2026-10-27 05:50 CET, before any E56/E57/E59/E61/E62/E63 NLA readout exists).** E49's; commit `259db20a 2026-10-27T05:40:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3558: **§172 E56 clarification 4 (2026-10-27 06:10 CET, before any E56/E57/E59/E61/E62/E63 reader output exists; design error corrected).** Greedy decoding is deterministic, so "8 greedy readouts per item" yields 8 identical; commit `8c66b004 2026-10-27T06:00:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3828: **Registered 2026-10-27 05:30 CET, before any E62 item exists. CONFIRMATORY for R-L1–R-L3; eval ladder DESCRIPTIVE with one rule.** **Owners:** W-text (bank, freeze by **11:00 CET**, after E61's D3/D4 banks), W-mechanism (runner,; commit `cde36cc9 2026-10-27T05:26:56+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3879: **Registered 2026-10-27 05:40 CET, before any placebo readout and before any E56/E57/E59/E62 reader output is opened. CONFIRMATORY for R-P1; R-P2 DESCRIPTIVE.** **Owners:** W-mechanism (runner, unchanged native channel), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3901: **Registered 2026-10-27 05:40 CET. No scientific rule; a deliverable.** **Owners:** W-core (package), W-internals; commit `491b3f85 2026-10-27T05:30:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3916: **Registered 2026-10-27 05:55 CET, after E49/E52 R3 (uninformative at n = 8, 2 REPORTED) and before any reader output of E56, E57, E59 or E62 is opened. CONFIRMATORY.** **Owners:** W-lens (forecast), integrator (custody and ordering).; commit `061d0e4a 2026-10-27T05:42:04+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3933: **§181 clarification 1 (2026-10-27 06:00 CET, answers W-lens, before any forecast or reader output).** R3b covers only; commit `2ba13670 2026-10-27T05:43:55+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3941: **Registered 2026-10-27 06:20 CET, before E60 is fitted and before any E56/E57/E59/E62 reader output is opened. CONFIRMATORY for R-C1; R-C2 DESCRIPTIVE.** **Owners:** W-text (value-persistence measure), W-lens (directional; commit `ad4e4467 2026-10-27T06:15:38+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L3981: **§182 E65 clarification 2 (2026-10-27 06:35 CET, after the integrator's capture inventory and before any E65 value or any affected reader output is opened).** No sealed capture stores all prompt positions (≈ 287 arrays, all; commit `db81ff0b 2026-10-27T06:20:31+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4021: **§178 E62 amendment 1 (2026-10-27 07:55 CET, before any E62 readout is opened).** **Placebo rungs:** for each state,; commit `6aacc13d 2026-10-27T07:47:59+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4058: **§178 / §177 ratification note (2026-10-27 08:10 CET, coordinator, before any placebo or D4a readout is opened).**; commit `650138c5 2026-10-27T08:00:12+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4068: **§178 R-L5 clarification 1 (2026-10-27 08:15 CET, before any E62 readout is opened).** W-text's check (`f0ffb76`):; commit `675a3a2e 2026-10-27T08:04:28+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4095: **§178 E62 dated note (2026-10-27 09:35 CET, coordinator, from sealed forecasts and captures only; no reader outcome opened).** Mean J-fraction of the target state does **not** rise with the rungs: L0 0.039, L1 0.034, L2 0.033, L3; commit `df2971ca 2026-10-27T09:25:16+01:00`; C<; generation ordering unresolved. O< 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4234: **Registered 2026-10-27 15:40 CET. CONFIRMATORY.** **Owners:** W-text (bank), W-mechanism (forward-only runner),; commit `8b2012d7 2026-10-27T15:10:42+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4609: ### §194 E76 clarification 2: judged floors (2026-10-28 05:15 CET, before any E76 judgment) Judged floors matter only where a row is claimed REPORTED, and the USD 2 budget cannot cover all 151 regex rows × 1,000 readouts × 2 readers (~300k records). ; commit `f3fcb715 2026-10-28T05:09:07+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.
- BRIEF L4620: **Registered 2026-10-28 05:30 CET, before any E79 vector, readout or judgment exists, and before E56's R4 or E70's outcomes have been read by the coordinator. CONFIRMATORY for R-C1, R-C2.**; commit `a12526c5 2026-10-28T05:14:36+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T08:34:24+00:00; stage applicability unresolved.

### E63
First committed sealed artifact checked: none located.
- Registration heading line 3877: ## §179 E63. Placebo floor (borrowed control: an Oracle-lens placebo); first-add commit 491b3f85b025c3d3fc62f8069888ad2102b56ad1 2026-10-27T05:30:22+01:00.
- BRIEF L3529: **§172 E56 clarification 2 (2026-10-27 05:10 CET, answers W-mechanism's QUESTIONS.md `c4ac59e1`, before any E56 score; applies identically to E57 §173 and E59 §175).**; commit `3ada24fb 2026-10-27T05:03:46+01:00`; PENDING (no sealed outcome).
- BRIEF L3548: **§172 E56 clarification 3 (2026-10-27 05:50 CET, before any E56/E57/E59/E61/E62/E63 NLA readout exists).** E49's; commit `259db20a 2026-10-27T05:40:04+01:00`; PENDING (no sealed outcome).
- BRIEF L3558: **§172 E56 clarification 4 (2026-10-27 06:10 CET, before any E56/E57/E59/E61/E62/E63 reader output exists; design error corrected).** Greedy decoding is deterministic, so "8 greedy readouts per item" yields 8 identical; commit `8c66b004 2026-10-27T06:00:59+01:00`; PENDING (no sealed outcome).
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4207: **Follow-on and rendering rulings (2026-10-27 15:15 CET, before any E57, E59, E63 or D4a judgment or reader outcome is opened).** (a) **List values in rubric fields** (E57 antonym_crosslingual, 168 records): a list is rendered as its; commit `55833480 2026-10-27T15:01:00+01:00`; PENDING (no sealed outcome).
- BRIEF L4346: **Registered 2026-10-27 15:30 CET. DESCRIPTIVE.** Extends E63: 500 random and 500 shuffled (cross-bank) block-44/42; commit `a68a228d 2026-10-27T15:22:20+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

### E64
First committed sealed artifact checked: none located.
- Registration heading line 3899: ## §180 E64. ReaderBench: the banks as a reusable benchmark (packaging; CPU); first-add commit 491b3f85b025c3d3fc62f8069888ad2102b56ad1 2026-10-27T05:30:22+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

### E65
First committed sealed artifact checked: none located.
- Registration heading line 3939: ## §182 E65. Two accounts of the blind spots: workspace membership vs lag coherence (CPU); first-add commit ad4e4467abfa5b9430eb0a8693dadca3c9144ede 2026-10-27T06:15:38+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L3972: **§182 E65 clarification 1 (2026-10-27 06:25 CET, answers W-lens and W-text, before any E65 value is computed).**; commit `9f6c8b70 2026-10-27T06:17:26+01:00`; PENDING (no sealed outcome).
- BRIEF L3981: **§182 E65 clarification 2 (2026-10-27 06:35 CET, after the integrator's capture inventory and before any E65 value or any affected reader output is opened).** No sealed capture stores all prompt positions (≈ 287 arrays, all; commit `db81ff0b 2026-10-27T06:20:31+01:00`; PENDING (no sealed outcome).
- BRIEF L3990: **§182 E65 clarification 3 (2026-10-27 06:40 CET, answers W-text, before E65_PERSISTENCE.json is committed).** P is; commit `96a8e352 2026-10-27T06:25:00+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

### E66
First committed sealed artifact checked: 1a95ac9da505f4a3db8acfa1edf1018b59f1bddc 2026-10-27T23:36:00+01:00; `results/g_agreement/understand/e66/analysis183_once_2026-10-27/RESULTS.json`.
- Registration heading line 4129: ## §183 E66. The blind spot in the wild, on a second model (GLM 5.3 Oracle-lens rollouts; CPU); first-add commit e94784b009f4c3413a7ea71b39ab5e22c561e135 2026-10-27T14:48:13+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C<; generation ordering unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C>=; generation ordering unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C>=; generation ordering unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C>=; generation ordering unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C>=; generation ordering unresolved.

### E67
First committed sealed artifact checked: c32c2a2d5e88968322309fc6e9527406df3f336e 2026-10-27T22:15:24+01:00; `results/g_agreement/r/e67_analysis/wave1_once/RESULTS.json`.
- Registration heading line 4176: ## §184 E67. Reader fidelity audit: how much of what the readers say is about this input?; first-add commit bbefdae2034e7e103f316ed5e76a4f2c5fe865db 2026-10-27T14:58:48+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved.
- BRIEF L4536: ### §184 E67 clarification 2 (2026-10-27 22:20 CET; ruling recorded pre-run in HANDOFF 9d763f63 before any wave-1 result) E67 is analysed in two waves. Wave 1 (E49, E54, E61 D4) had its once-only analysis at 21:14Z (seal 92f74fe0). Wave 2 (E56, E57) is a separate, later once-only analysis with the same frozen code and spec. It is reported separately and; commit `c949f909 2026-10-27T22:16:01+01:00`; C>=; generation ordering unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C>=; generation ordering unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C>=; generation ordering unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C>=; generation ordering unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C>=; generation ordering unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C>=; generation ordering unresolved.

### E68
First committed sealed artifact checked: 2b82a2f14328c1630e04bd497891104ab7e3eddc 2026-10-27T23:46:51+01:00; `results/g_agreement/understand/e68/analysis5968_once_2026-10-27/RESULTS.json`.
- Registration heading line 4217: ## §185 E68. Distance-to-output: do readers report tracked state only when it is about to be emitted?; first-add commit 8b2012d73b6407f5803450849601fe0d80e56705 2026-10-27T15:10:42+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4219: **Registered 2026-10-27 15:40 CET, after an independent review and before any E68 item exists. CONFIRMATORY.**; commit `8b2012d7 2026-10-27T15:10:42+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4376: ### §185 E68 deviation 1 (2026-10-27 16:00 CET, before any E68 position is captured or read) W-text's sealed audit shows the registered design is degenerate: container_after_move's frozen prefix ends "in the" and arith_compare's ends "Answer:", so the registered read token ; commit `24070152 2026-10-27T15:29:43+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4415: ### §185 E68 deviation 2 (2026-10-27 16:40 CET, after W-text's position audit 2587767; no capture or readout exists) W-text's rules (2587767) are ratified as written for container_after_move (84 kept, gap 14) and holder_after_handovers (84 kept, gap 26). ; commit `7e6ea0cc 2026-10-27T15:34:41+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4456: ### §185 E68 compute deviation (2026-10-27 16:55 CET, before any E68 capture) W-mechanism's measured forecast is 4,531 s (5b377a93), which exceeds the registered ≤ 0.6 GPU-h (2,160 s). The cap is raised to 1.25 × forecast = 5,664 s (≈ 1.6 GPU-h), as in the §149 compute deviation. Design, positions, n and rules are; commit `bb9f3931 2026-10-27T15:43:05+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4498: ### §194 E76 compute deviation (2026-10-27 17:20 CET, before any E76 capture) The measured phases need about 3,400–3,700 s before the worker's 1.5× margin, which exceeds the registered ≤ 1 GPU-h. The cap is raised to 6,100 s (≈ USD 9), on E59's pod after its same-pod parity pass. Scope, n, norms and analysis are; commit `bbed7f84 2026-10-27T16:14:10+01:00`; C<; generation ordering unresolved. O< 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C<; generation ordering unresolved. O>= 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T15:32:05+00:00; opening/judging boundary separate.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C>=; generation ordering unresolved. O>= 2026-10-27T15:32:05+00:00; opening/judging boundary separate.

### E69
First committed sealed artifact checked: none located.
- Registration heading line 4232: ## §186 E69. Behaviour column: is every missed state used, not only decodable?; first-add commit 8b2012d73b6407f5803450849601fe0d80e56705 2026-10-27T15:10:42+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4557: ### §186 E69 compute deviation (2026-10-27 23:00 CET, before any E69 production output) The measured profile with the fixed worker (9bee5bed) needs a 550 s fresh-pod production stage, about 1,520 s in total including the 516 s profile already used, against the registered 1,080 s. E69's cap is raised to that total; commit `ad4d3a46 2026-10-27T22:53:33+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

### E70
First committed sealed artifact checked: none located.
- Registration heading line 4242: ## §187 E70. Dose injection: no decoder at any amplitude?; first-add commit 8b2012d73b6407f5803450849601fe0d80e56705 2026-10-27T15:10:42+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4265: **Registered 2026-10-27 15:40 CET. DESCRIPTIVE.** **Owners:** W-mechanism, integrator. **Cost:** ≤ 0.4 GPU-h.; commit `8b2012d7 2026-10-27T15:10:42+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4443: ### §187 E70 clarification 1 (2026-10-27 16:50 CET, before any E70 readout) W-internals' carriers (2c88aaf2, CARRIER_RATIFICATION.md) are ratified as built. There are 8 carriers per row and 32 in all. Each carrier is the midpoint of one seeded, unused A-dev and one unused B-dev item (seed 20261027), and none is; commit `f8f38c60 2026-10-27T15:40:50+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).
- BRIEF L4620: **Registered 2026-10-28 05:30 CET, before any E79 vector, readout or judgment exists, and before E56's R4 or E70's outcomes have been read by the coordinator. CONFIRMATORY for R-C1, R-C2.**; commit `a12526c5 2026-10-28T05:14:36+01:00`; PENDING (no sealed outcome).

### E71
First committed sealed artifact checked: none located.
- Registration heading line 4253: ## §188 E71. Human validation of the judge (no GPU); first-add commit 8b2012d73b6407f5803450849601fe0d80e56705 2026-10-27T15:10:42+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4397: ### §188 E71 clarification 1 (2026-10-27 16:00 CET, before any human coding) The packet must draw from the registered pool (E49, E54, D4 and, now sealed, E56), not from E54 alone: 25 per reader × status stratum, uniform over eligible sealed items across those banks with seed 20261027. The E54-only packet; commit `24070152 2026-10-27T15:29:43+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4451: ### §188 E71 clarification 2 (2026-10-27 16:50 CET) The rebuilt packet (8bac3e82; E49, E54, D4 and E56; 25 per reader × status stratum; seed 20261027) is the E71 packet. The coders are Guiv and one colleague not on the analysis. Each codes independently, without the judge output, and; commit `f8f38c60 2026-10-27T15:40:50+01:00`; PENDING (no sealed outcome).
- BRIEF L4467: ### §188 E71 clarification 3 (2026-10-27 16:58 CET, before any human code exists) Coder 1 is Suraj, who has no access to judge outputs. He starts now on the 8bac3e82 packet, with no KEY file. The judge's codes for these items already exist in the sealed banks and are not rerun. A second human coder (Guiv or another; commit `967933d7 2026-10-27T15:47:13+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

### E72
First committed sealed artifact checked: none located.
- Registration heading line 4263: ## §189 E72. Earlier-layer read (off-distribution insurance); first-add commit 8b2012d73b6407f5803450849601fe0d80e56705 2026-10-27T15:10:42+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

### E73
First committed sealed artifact checked: 62ebfec0946d7f1d84aedd20187da1414e670fdf 2026-10-28T05:08:39+01:00; `results/g_agreement/i2/E73_ONCE_ANALYSIS_RESULTS.json`.
- Registration heading line 4293: ## §191 E73. Wild census on Qwen: the map on real text, with probes; first-add commit a68a228dc483059b39c5c558c2a1b3867fb45f81 2026-10-27T15:22:20+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved.
- BRIEF L4295: **Registered 2026-10-27 15:30 CET, before any E73 item exists. CONFIRMATORY for R-W1, R-W2.**; commit `a68a228d 2026-10-27T15:22:20+01:00`; C<; generation ordering unresolved.
- BRIEF L4338: **Registered 2026-10-27 15:30 CET. CONFIRMATORY.** W-lens pools every unit with a committed pre-reader forecast (R3b; commit `a68a228d 2026-10-27T15:22:20+01:00`; C<; generation ordering unresolved.
- BRIEF L4360: ### §190–§195 clarification 1 (2026-10-27 15:45 CET, before any E73–E77 data exists) 1. ; commit `4cde021d 2026-10-27T15:23:55+01:00`; C<; generation ordering unresolved.
- BRIEF L4402: ### §191 E73 clarification 2 (2026-10-27 16:10 CET, before any sampling) W8 membership: an article is in a class if its title contains, as a whole word (case-insensitive), any term in that class's frozen list; titles matching terms from both lists are excluded. Each list has at least 40 terms and is; commit `451e2f4d 2026-10-27T15:32:17+01:00`; C<; generation ordering unresolved.
- BRIEF L4424: ### §191 E73 clarification 3 (2026-10-27 16:40 CET, before any sampling) 1. ; commit `7e6ea0cc 2026-10-27T15:34:41+01:00`; C<; generation ordering unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved.
- BRIEF L4503: ### §192 E74 clarification 5 (2026-10-27 17:35 CET, before any GPU use) W-glm's full forecast (afa98d4d) is USD 77.22, or USD 96.53 at × 1.25, which exceeds clarification 4's USD 80. Per Guiv's instruction to fund the GLM replication, ; commit `ac641dbf 2026-10-27T16:32:45+01:00`; C<; generation ordering unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved.
- BRIEF L4525: ### §191 E73 clarification 4 (2026-10-27 22:15 CET, after capture and probes, before any native readout) The BOW gate excluded the content controls W7 (code vs prose, BOW 1.000) and W8 (topic, 0.964). That was my design error: content controls are lexical by construction, and the gate exists to stop *structural* states from being; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C<; generation ordering unresolved.
- BRIEF L4575: ### §192 E74 clarification 8 (2026-10-27 23:40 CET, before any GPU use) For TP8 paths, the admission cap is raised from USD 120 to ; commit `b81c6c9d 2026-10-27T23:31:54+01:00`; C<; generation ordering unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C<; generation ordering unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C<; generation ordering unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C<; generation ordering unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C<; generation ordering unresolved.
- BRIEF L4789: **Registered 2026-10-28 10:15 CET, before any E81 output exists. CONFIRMATORY for R-T1.**; commit `5040ca28 2026-10-28T10:01:27+01:00`; C>=; generation ordering unresolved.
- BRIEF L5045: ### §199 E85 clarification 1 (2026-10-28 11:05 CET, before any E85 item exists) The BOW ≤ 0.65 gate does not apply to E85. Both factors (genre and the addressed cue) are explicit text manipulations by design, so a word-level classifier recovers them, as with E73's W7/W8 content controls. E85 asks which factor the; commit `417210fa 2026-10-28T10:42:29+01:00`; C>=; generation ordering unresolved.

### E75
First committed sealed artifact checked: 84d8af77a850861c1b3dbf17c098589810bfb03a 2026-10-28T06:35:00+01:00; `results/g_agreement/understand/e75/QWEN_RESULTS.json`.
- Registration heading line 4336: ## §193 E75. The predictor at scale; first-add commit a68a228dc483059b39c5c558c2a1b3867fb45f81 2026-10-27T15:22:20+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C<; generation ordering unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C<; generation ordering unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C<; generation ordering unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C<; generation ordering unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C<; generation ordering unresolved.
- BRIEF L4674: ### §193 E75 follow-up (2026-10-28 05:40 CET; EXPLORATORY, after E75's sealed result) 1. ; commit `1e879d02 2026-10-28T05:27:11+01:00`; C<; generation ordering unresolved.

### E76
First committed sealed artifact checked: 10eb98986f75e662a8ee22db72abe4a32b67bc57 2026-10-28T04:46:18+01:00; `results/g_agreement/understand/e76/regex_20261027/FLOOR_TABLE.json`.
- Registration heading line 4344: ## §194 E76. Placebo at scale; first-add commit a68a228dc483059b39c5c558c2a1b3867fb45f81 2026-10-27T15:22:20+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved.
- BRIEF L4392: ### §194 E76 clarification 1 (2026-10-27 16:00 CET, before any E76 readout) One shared pool per reader: each shuffled vector keeps its source bank's median norm at the reader's native layer, and each random vector is paired with a shuffled reference and scaled to that same median. 500 random + 500 shuffled per; commit `24070152 2026-10-27T15:29:43+01:00`; C<; generation ordering unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved.
- BRIEF L4498: ### §194 E76 compute deviation (2026-10-27 17:20 CET, before any E76 capture) The measured phases need about 3,400–3,700 s before the worker's 1.5× margin, which exceeds the registered ≤ 1 GPU-h. The cap is raised to 6,100 s (≈ USD 9), on E59's pod after its same-pod parity pass. Scope, n, norms and analysis are; commit `bbed7f84 2026-10-27T16:14:10+01:00`; C<; generation ordering unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C<; generation ordering unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C<; generation ordering unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C<; generation ordering unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C<; generation ordering unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C<; generation ordering unresolved.
- BRIEF L4609: ### §194 E76 clarification 2: judged floors (2026-10-28 05:15 CET, before any E76 judgment) Judged floors matter only where a row is claimed REPORTED, and the USD 2 budget cannot cover all 151 regex rows × 1,000 readouts × 2 readers (~300k records). ; commit `f3fcb715 2026-10-28T05:09:07+01:00`; C>=; generation ordering unresolved.
- BRIEF L4828: **Registered 2026-10-28 10:15 CET, before any E83 output. DESCRIPTIVE.**; commit `5040ca28 2026-10-28T10:01:27+01:00`; C>=; generation ordering unresolved.

### E78
First committed sealed artifact checked: none located.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

### E79
First committed sealed artifact checked: 21e4ddf95b0f8e3b1947e18267337ea3ceb5ba99 2026-10-28T08:48:25+01:00; `results/g_agreement/understand/e79/behaviour_once_2026-10-28/metrics/METRICS.json`.
- Registration heading line 4618: ## §196 E79. Causal test: move a state into or out of the J-space and watch reporting switch; first-add commit a12526c51f0b0e4f8c602244bb51b54f953c5880 2026-10-28T05:14:36+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C<; generation ordering unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C<; generation ordering unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C<; generation ordering unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C<; generation ordering unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C<; generation ordering unresolved.
- BRIEF L4620: **Registered 2026-10-28 05:30 CET, before any E79 vector, readout or judgment exists, and before E56's R4 or E70's outcomes have been read by the coordinator. CONFIRMATORY for R-C1, R-C2.**; commit `a12526c5 2026-10-28T05:14:36+01:00`; C<; generation ordering unresolved.
- BRIEF L4659: ### §196 E79 clarification 1 (2026-10-28 05:35 CET, before any E79 vector or output exists) §196 wrongly described E59's continuation scorer as producing a binary plan-execution rate. In fact it is a first-token contrast score (format: '-' vs 'The'; language: 'Je'/'Le' vs 'The') summarised as AUROC. Arm B's behaviour check is; commit `b3c1e6d0 2026-10-28T05:17:11+01:00`; C<; generation ordering unresolved.
- BRIEF L4667: ### §196 E79 clarification 2 (2026-10-28 05:40 CET, before any E79 readout exists) At α = 4 the injected activations reach norm ratios of up to 2.6–3.0 (nesting_depth, indent_level), which is off distribution. Arm A therefore gains ; commit `1e879d02 2026-10-28T05:27:11+01:00`; C<; generation ordering unresolved.

### E80
First committed sealed artifact checked: none located.
- Registration heading line 4686: ## §197 Timeline change and E80 (2026-10-28 06:35 CET); first-add commit 2e8dbc37426f2980df510a2d30ee5ba42ff3a662 2026-10-28T06:19:42+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).
- BRIEF L4693: **Registered 2026-10-28 06:35 CET, before any E80 capture, readout or judgment exists. CONFIRMATORY for R-X1, R-X2.**; commit `2e8dbc37 2026-10-28T06:19:42+01:00`; PENDING (no sealed outcome).
- BRIEF L4723: **E80 pin (2026-10-28 06:37 CET):** WorkspaceBench commit `86612fa4925100391b39c27894807a479595c61c`.; commit `a8136e50 2026-10-28T06:19:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4725: ### §197 E80 clarification 1 (2026-10-28 06:50 CET, before any E80 export, capture or readout) At the pinned commit, relational_multihop has no `item_targets`: it stores hop1/hop2/gold and is judged by two ordered-relation multiple-choice questions, not by concept expression. It does not fit E80's single-target forecast,; commit `48761624 2026-10-28T06:22:46+01:00`; PENDING (no sealed outcome).
- BRIEF L4731: ### §197 E80 clarification 2 (2026-10-28 06:55 CET, before any E80 readout) "Each family's frozen judge" means ; commit `4a22d448 2026-10-28T06:25:05+01:00`; PENDING (no sealed outcome).
- BRIEF L4737: ### §197 E80 note (2026-10-28 07:05 CET, after the forecast commit 189c1161, before any reader output exists) Only 14 of 518 items are J-visible (top 10), against 39 for the logit lens. R-X1's odds-ratio test therefore has little power on the positive side, and a non-significant R-X1 is reported as underpowered, not as a falsification; commit `0d80f81d 2026-10-28T06:58:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4744: **Correction (2026-10-28 07:10 CET):** commit 0eea54ae, a wording fix to the E80 note, accidentally appended text to; commit `e3f5cad4 2026-10-28T06:59:07+01:00`; PENDING (no sealed outcome).
- BRIEF L4766: ### §197 E80b: corrected J-visibility forecast (2026-10-28 07:50 CET, before any E80 reader output or judgment is opened) An independent review found that E80's committed forecast (189c1161) reads J-visibility differently from WorkspaceBench's J-lens readout of record. E80 used norm(h·Jᵀ)·W_U; the pinned `src/wsbench/produce/methods.py`; commit `08c71a71 2026-10-28T07:44:02+01:00`; PENDING (no sealed outcome).
- BRIEF L5052: **Registered 2026-10-28 11:10 CET, before any E80 reader output or judgment is opened. CONFIRMATORY for R-X3; R-X4 DESCRIPTIVE.** E80b (the corrected J-lens-rank forecast) stays as a side, exploratory analysis. E80c is the main; commit `6c07e38a 2026-10-28T10:45:07+01:00`; PENDING (no sealed outcome).
- BRIEF L5074: ### §197 E80c clarification 1 and a reporting rule (2026-10-28 11:20 CET, before any E80c vector or output) 1. ; commit `8f3cba53 2026-10-28T10:48:44+01:00`; PENDING (no sealed outcome).

### E87
First committed sealed artifact checked: none located.
- Registration heading line 4921: ### E87. Position × layer sweep on missed rows (CONFIRMATORY for R-L1); first-add commit 0567e8a10dbdf068fdd0404f278690bc6363d2a6 2026-10-28T10:33:42+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).
- BRIEF L5031: ### §202 Judge-rubric clauses for all new banks (2026-10-28 11:00 CET, before any E81–E92 judgment) The discovery pass found two judge artefacts. For every bank not yet judged (E81–E92, and E87's placebo), the §172 rubric gains two clauses, applied from the first judgment:; commit `0d052d31 2026-10-28T10:41:47+01:00`; PENDING (no sealed outcome).
- BRIEF L5102: ### §200 E87 clarification 1 (2026-10-28 11:50 CET, before any E87 output) WorkspaceBench's per-layer macro for the s3d-rl600 Oracle lens peaks at L56 (0.59) against about 0.50 at L44, with a step between L48 and L52. E87's Oracle layer set becomes ; commit `df037c47 2026-10-28T10:55:09+01:00`; PENDING (no sealed outcome).

### E88
First committed sealed artifact checked: ae9491dd0161c32704161c4b542cda12b463a333 2026-10-28T11:20:27+01:00; `results/g_agreement/understand/e88/AUDIT_RESULTS.json`.
- Registration heading line 4944: ### E88. Artefact audit (CPU, with one small judging arm; DESCRIPTIVE); first-add commit 0567e8a10dbdf068fdd0404f278690bc6363d2a6 2026-10-28T10:33:42+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; C<; generation ordering unresolved.
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; C<; generation ordering unresolved.
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; C<; generation ordering unresolved.
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; C<; generation ordering unresolved.
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; C<; generation ordering unresolved.
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; C<; generation ordering unresolved.
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; C<; generation ordering unresolved.
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; C<; generation ordering unresolved.
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; C<; generation ordering unresolved.
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; C<; generation ordering unresolved.
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; C<; generation ordering unresolved.
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; C<; generation ordering unresolved.
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; C<; generation ordering unresolved.

### E93
First committed sealed artifact checked: none located.
- Registration heading line 5123: ## §203 Two additions: self-report baseline and reader agreement (2026-10-28 11:10 CET, before any E93/E94 output); first-add commit 4e05da31e6d08532c1dd103a673950683b677caa 2026-10-28T11:03:32+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

### E94
First committed sealed artifact checked: none located.
- Registration heading line 5123: ## §203 Two additions: self-report baseline and reader agreement (2026-10-28 11:10 CET, before any E93/E94 output); first-add commit 4e05da31e6d08532c1dd103a673950683b677caa 2026-10-28T11:03:32+01:00.
- BRIEF L3576: **Ownership and timing note (2026-10-27 03:50 CET, operations; no rule changes).** (i) E49 readers start only after; commit `e0a2e9ef 2026-10-27T03:43:51+01:00`; PENDING (no sealed outcome).
- BRIEF L4006: **§177 E61 D5 / §171 E54 judging clarification (2026-10-27 07:40 CET, before any judgment is analysed; operational).**; commit `965e4baa 2026-10-27T07:33:32+01:00`; PENDING (no sealed outcome).
- BRIEF L4072: **Judging clarification 2 (2026-10-27 08:45 CET, after W-internals' failure counts `0f536dc9`, before any judged category share is computed; operational).** (a) **Per-record validation:** a judged record that passes validation is; commit `67d3b46d 2026-10-27T08:36:37+01:00`; PENDING (no sealed outcome).
- BRIEF L4087: **Joint-run rulings (2026-10-27 09:05 CET, before any E56/E57/E61 or E49-supplement reader output is opened).**; commit `efb3c358 2026-10-27T08:57:16+01:00`; PENDING (no sealed outcome).
- BRIEF L4106: **Compute replan (2026-10-27 13:40 CET, coordinator for Guiv, before any E57, E61, E56_2, E62 or E62P reader output exists).** Joint9 closed with 2 of 9 shards complete (E56_0, E56_1): seven lost their caps to slow serial uploads; E62 +; commit `402be5f0 2026-10-27T13:29:12+01:00`; PENDING (no sealed outcome).
- BRIEF L4162: **Judging interface and E62P rulings (2026-10-27 15:05 CET, before any E56/E57/E62 judgment exists).**; commit `94a770cc 2026-10-27T14:49:58+01:00`; PENDING (no sealed outcome).
- BRIEF L4434: ### §183 E66 clarification 1 (2026-10-27 16:45 CET, before any judging; no readout text inspected) W-core's SAMPLING_CONVENTIONS (b221cf55) are ratified as written. Every selection depends only on metadata, prompt text/tokens, identifiers or seeded randomness. The 15:02 correction (the < 50 rule applies to eligible transcripts) was; commit `23a2e5c9 2026-10-27T15:35:22+01:00`; PENDING (no sealed outcome).
- BRIEF L4517: ### Track Q compute deviation (2026-10-27 22:15 CET; no affected readout exists) The following registered caps were below measured needs (operator's final report, HANDOFF c03d3df8). Each is reset to measured forecast × 1.25, a cost change only: E49 NLA supplement 5,200 s; E70 2,700 s; E72 2,700 s; E63 8,650 s;; commit `19da3104 2026-10-27T22:09:24+01:00`; PENDING (no sealed outcome).
- BRIEF L4541: ### Judging privacy-guard ruling (2026-10-27 22:45 CET, before any affected judgment) When the wire privacy guard matches a ; commit `79f63fe0 2026-10-27T22:35:53+01:00`; PENDING (no sealed outcome).
- BRIEF L4581: ### Compute deviations, 2026-10-28 02:55 CET (before any affected readout) 1. ; commit `d7b4145b 2026-10-28T02:48:06+01:00`; PENDING (no sealed outcome).
- BRIEF L4589: ### In-run admission rule (2026-10-28 03:40 CET; operational, no science change) Workers re-forecast remaining time from their ; commit `a6d0e06e 2026-10-28T03:35:52+01:00`; PENDING (no sealed outcome).
- BRIEF L4596: ### Judging privacy-guard ruling, extension (2026-10-28 04:45 CET, before any affected judgment) The path-only redaction rule (79f63fe0) now also covers matches of the ; commit `25c32f25 2026-10-28T04:43:03+01:00`; PENDING (no sealed outcome).
- BRIEF L4602: ### Compute deviations, 2026-10-28 04:50 CET (cost only) - ; commit `b21fa956 2026-10-28T04:44:41+01:00`; PENDING (no sealed outcome).

| E61 | R-W (both readers) | NOT MET | Raw base ignore/none ratio (0.27577315249531414, 0.2676671726905132, 0.28428425933039236); n=84 | .2757731525 [.26766717,.28428426]; reader mention ratio 0/0 | see E61 chronology | DISCREPANCY: worker says NOT EVALUABLE because mention ratio is 0/0. Registered rule uses inequalities: base ignore is only .276 x none, below required .8, so R-W is NOT MET regardless of reader ratio. Bootstrap exactly matches after retained pilots included. |

## E88 independent missingness audit

- E56 ('nla', 'tense_implicit'): worst S/CI=(0.2261904761904762, 0.13095238095238096, 0.32142857142857145); best S/CI=(0.25, 0.15476190476190477, 0.34523809523809523); REPORTED/MISSED flip=False.
- E56 ('oracle', 'adjective_asked'): worst S/CI=(0.16666666666666666, 0.03571428571428571, 0.2976190476190476); best S/CI=(0.19047619047619047, 0.05952380952380952, 0.32142857142857145); REPORTED/MISSED flip=False.
- E56 ('oracle', 'adjective_implicit'): worst S/CI=(0.05952380952380952, -0.07142857142857142, 0.19047619047619047); best S/CI=(0.36904761904761907, 0.27380952380952384, 0.47619047619047616); REPORTED/MISSED flip=True.
- E56 ('oracle', 'anomaly_state'): worst S/CI=(-0.11904761904761904, -0.2619047619047619, 0.02410714285714123); best S/CI=(0.023809523809523808, -0.11904761904761904, 0.17857142857142858); REPORTED/MISSED flip=False.
- E56 ('oracle', 'language_continuation'): worst S/CI=(0.4880952380952381, 0.3333333333333333, 0.6428571428571429); best S/CI=(0.7023809523809523, 0.5833333333333334, 0.8095238095238095); REPORTED/MISSED flip=False.
- E56 ('oracle', 'linewrap_implicit'): worst S/CI=(-0.011904761904761904, -0.03571428571428571, 0.0); best S/CI=(0.011904761904761904, 0.0, 0.03571428571428571); REPORTED/MISSED flip=False.
- E56 ('oracle', 'tense_implicit'): worst S/CI=(0.38095238095238093, 0.23809523809523808, 0.5119047619047619); best S/CI=(0.5238095238095238, 0.4166666666666667, 0.6309523809523809); REPORTED/MISSED flip=False.
- E57 ('nla', 'category_switch'): worst S/CI=(0.6309523809523809, 0.5, 0.7619047619047619); best S/CI=(0.6547619047619048, 0.5238095238095238, 0.7738095238095238); REPORTED/MISSED flip=False.
- E57 ('nla', 'loop_direction'): worst S/CI=(0.4880952380952381, 0.36875, 0.6071428571428571); best S/CI=(0.5833333333333334, 0.4880952380952381, 0.6785714285714286); REPORTED/MISSED flip=False.
- E57 ('oracle', 'category_switch'): worst S/CI=(0.2976190476190476, 0.14285714285714285, 0.4523809523809524); best S/CI=(0.32142857142857145, 0.16666666666666666, 0.47619047619047616); REPORTED/MISSED flip=False.
- E57 ('oracle', 'clause_pending'): worst S/CI=(0.21428571428571427, 0.10714285714285714, 0.32142857142857145); best S/CI=(0.2857142857142857, 0.19047619047619047, 0.39285714285714285); REPORTED/MISSED flip=False.
- E57 ('oracle', 'loop_direction'): worst S/CI=(0.39285714285714285, 0.2619047619047619, 0.5119047619047619); best S/CI=(0.44047619047619047, 0.32142857142857145, 0.5595238095238095); REPORTED/MISSED flip=False.
- E57 ('oracle', 'nesting_depth'): worst S/CI=(-0.11904761904761904, -0.2261904761904762, -0.023809523809523808); best S/CI=(0.14285714285714285, 0.047619047619047616, 0.23809523809523808); REPORTED/MISSED flip=False.
- E57 ('oracle', 'section_header'): worst S/CI=(-0.023809523809523808, -0.19047619047619047, 0.14285714285714285); best S/CI=(0.07142857142857142, -0.09523809523809523, 0.23809523809523808); REPORTED/MISSED flip=False.
- E57 ('oracle', 'subject_number'): worst S/CI=(0.20238095238095238, 0.09523809523809523, 0.30952380952380953); best S/CI=(0.25, 0.14285714285714285, 0.34523809523809523); REPORTED/MISSED flip=False.
- E57 ('oracle', 'two_hop_answer'): worst S/CI=(0.2619047619047619, 0.15476190476190477, 0.36904761904761907); best S/CI=(0.30952380952380953, 0.21428571428571427, 0.40476190476190477); REPORTED/MISSED flip=False.
- E59 ('oracle', 'decline_plan'): worst S/CI=(0.16666666666666666, -0.023809523809523808, 0.35714285714285715); best S/CI=(0.2857142857142857, 0.09523809523809523, 0.4642857142857143); REPORTED/MISSED flip=True.
- E59 ('oracle', 'format_plan'): worst S/CI=(0.9285714285714286, 0.8571428571428571, 0.9880952380952381); best S/CI=(0.9523809523809523, 0.9047619047619048, 0.9880952380952381); REPORTED/MISSED flip=False.
- E59 ('oracle', 'hedge_plan'): worst S/CI=(0.9642857142857143, 0.9047619047619048, 1.0); best S/CI=(0.9880952380952381, 0.9642857142857143, 1.0); REPORTED/MISSED flip=False.
- E59 ('oracle', 'language_plan'): worst S/CI=(0.39285714285714285, 0.21428571428571427, 0.5595238095238095); best S/CI=(0.5833333333333334, 0.42857142857142855, 0.7261904761904762); REPORTED/MISSED flip=False.
- E59 ('oracle', 'length_plan'): worst S/CI=(0.38095238095238093, 0.23809523809523808, 0.5238095238095238); best S/CI=(0.5952380952380952, 0.4880952380952381, 0.7023809523809523); REPORTED/MISSED flip=False.
- E62 ('oracle', 'S1_L3'): worst S/CI=(0.2261904761904762, 0.09523809523809523, 0.35714285714285715); best S/CI=(0.25, 0.11904761904761904, 0.38095238095238093); REPORTED/MISSED flip=False.
- E62 ('oracle', 'S3_L0'): worst S/CI=(0.38095238095238093, 0.25, 0.5119047619047619); best S/CI=(0.5, 0.39285714285714285, 0.6071428571428571); REPORTED/MISSED flip=False.
- E62 ('oracle', 'S3_L1'): worst S/CI=(0.16666666666666666, 0.05952380952380952, 0.2857142857142857); best S/CI=(0.21428571428571427, 0.10714285714285714, 0.32142857142857145); REPORTED/MISSED flip=True.
- E62 ('oracle', 'S3_L3'): worst S/CI=(0.75, 0.5952380952380952, 0.8809523809523809); best S/CI=(0.7738095238095238, 0.6309523809523809, 0.8928571428571429); REPORTED/MISSED flip=False.
- E62 ('oracle', 'S4_L0'): worst S/CI=(0.5, 0.3333333333333333, 0.6666666666666666); best S/CI=(0.7619047619047619, 0.6547619047619048, 0.8571428571428571); REPORTED/MISSED flip=False.
- E62 ('oracle', 'S4_L1'): worst S/CI=(0.40476190476190477, 0.23809523809523808, 0.5595238095238095); best S/CI=(0.7142857142857143, 0.5952380952380952, 0.8214285714285714); REPORTED/MISSED flip=False.
- E62 ('oracle', 'S4_L2'): worst S/CI=(0.27380952380952384, 0.10714285714285714, 0.44047619047619047); best S/CI=(0.4166666666666667, 0.2619047619047619, 0.5714285714285714); REPORTED/MISSED flip=False.
- E62 ('oracle', 'S5_L0'): worst S/CI=(0.25, 0.13095238095238096, 0.36904761904761907); best S/CI=(0.34523809523809523, 0.23809523809523808, 0.4523809523809524); REPORTED/MISSED flip=False.
- E62 ('oracle', 'S5_L1'): worst S/CI=(0.11904761904761904, -0.024107142857142837, 0.27380952380952384); best S/CI=(0.21428571428571427, 0.07142857142857142, 0.35714285714285715); REPORTED/MISSED flip=True.
- E62 ('oracle', 'S5_L2'): worst S/CI=(0.2619047619047619, 0.14255952380952383, 0.38095238095238093); best S/CI=(0.2857142857142857, 0.15476190476190477, 0.40476190476190477); REPORTED/MISSED flip=False.
- E62 ('oracle', 'S5_L3'): worst S/CI=(-0.023809523809523808, -0.11904761904761904, 0.08333333333333333); best S/CI=(0.023809523809523808, -0.07142857142857142, 0.13095238095238096); REPORTED/MISSED flip=False.

| Experiment | Rule/item | Verdict | Independent number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E88 | 1 sign conventions | NOT EVALUABLE | 17 entries; focus_ignore probe=.00170068027 | unresolved orientations | ae9491dd 2026-10-28T11:20:27+01:00 | Audit remains incomplete: listing low AUROCs does not resolve inverted versus real. Some entries are J-lens scores, not probes. |
| E88 | 2 UNPARSEABLE | NOT EVALUABLE | 32 affected row-reader cells independently bootstrapped across E56/57/59/62; flips=[(56, ('oracle', 'adjective_implicit')), (59, ('oracle', 'decline_plan')), (62, ('oracle', 'S3_L1')), (62, ('oracle', 'S5_L1'))] | many flags NOT_COMPUTABLE_WITHOUT_ITEM_CLUSTER_BOOTSTRAP | ae9491dd 2026-10-28T11:20:27+01:00 | Partial audit improved here, but all-bank scope not complete. Explicit sensitivity ledger above; original results not edited. |
| E88 | 3 dev/test leakage | NOT EVALUABLE | Independent full all-bank distance enumeration outstanding | {'E49': 6616, 'E54': None, 'E56': 6738, 'E57': 14144, 'E59': 0, 'E62': 21435, 'E67': None, 'E73': None, 'E75': None} | ae9491dd 2026-10-28T11:20:27+01:00 | Partial sealed audit; E54/input scope unresolved. No clean leakage verdict warranted. |
| E88 | 4 read-token audit | NOT EVALUABLE | Complete independent sampled index+decoded comparison outstanding | {'E49': 135, 'E54': None, 'E56': 110, 'E57': 168, 'E59': 51, 'E62': 231, 'E67': None, 'E73': None, 'E75': None} | ae9491dd 2026-10-28T11:20:27+01:00 | Partial sealed audit does not establish all requested banks/read-site rules. |
| E88 | 5 judge swap | PENDING | n=0 returned second-judge codes located; target300 | packet sealed, no scored swap located | ae9491dd 2026-10-28T11:20:27+01:00 | No kappa inferred from a packet. |


## First sealed raw-output mtime checks

File mtimes are filesystem provenance, not cryptographically signed timestamps. These are earlier and more appropriate than analysis commit times; retained pilots are included. Dated notes that concern judging/opening rather than generation require that separate boundary.
- E56: earliest verified sealed raw member mtime 2026-10-27T07:34:36+00:00, `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/pilots/slot_2/PILOT_RESULTS.json`; 289 files considered, including retained pilots.
- E57: earliest verified sealed raw member mtime 2026-10-27T07:34:36+00:00, `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/pilots/slot_2/PILOT_RESULTS.json`; 431 files considered, including retained pilots.
- E62: earliest verified sealed raw member mtime 2026-10-27T08:34:24+00:00, `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/pilots/slot_second/PILOT_RESULTS.json`; 314 files considered, including retained pilots.


## Additional first-output checks

- E59: earliest verified native/job member 2026-10-27T14:37:36+00:00, `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/E59/shard_0/out/jobs/000000.json`. This is the sealed acquired-file timestamp, not a guarantee about any omitted pilot.
- E68: earliest verified native/job member 2026-10-27T15:32:05+00:00, `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/E68/shard_0/out/jobs/000000.json`. This is the sealed acquired-file timestamp, not a guarantee about any omitted pilot.

## Remaining scope / next pass

Only missing seals are PENDING. A sealed but incomplete audit is NOT EVALUABLE with the missing evidence stated; it is not silently treated as passed.

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy / next evidence |
|---|---|---|---|---|---|---|
| E58a | R-a1 | PENDING | — | — | BRIEF c6d4b904; listed source inventories | Category/J labels exist, no completed all-six-bank statistical analysis located. |
| E58a | R-a2 | PENDING | — | — | BRIEF c6d4b904; listed source inventories | No completed cross-row correlation analysis located. |
| E60 | R1 | PENDING | — | — | BRIEF c6d4b904; listed source inventories | No sealed leave-one-bank-out predictor result located. |
| E61 | R-W2 / D4a interpretation gate | PENDING | — | — | BRIEF c6d4b904; listed source inventories | No completed D4a sealed outcomes located; cannot substitute D4. |
| E63 | R-P1 | PENDING | — | — | BRIEF c6d4b904; listed source inventories | Runner/spec exists, no sealed row-wise real-versus-placebo analysis located. |
| E63 | R-P2 descriptive | PENDING | — | — | BRIEF c6d4b904; listed source inventories | No completed D5/placebo TVD analysis located. |
| E64 | ReaderBench deliverable (no scientific rule) | PENDING | — | — | BRIEF c6d4b904; listed source inventories | No complete sealed benchmark/card deliverable verified in this pass. |
| E65 | R-C1 | PENDING | — | — | BRIEF c6d4b904; listed source inventories | Coherence/persistence preparation exists, no sealed three-model held-out comparison located. |
| E65 | R-C2 descriptive | PENDING | — | — | BRIEF c6d4b904; listed source inventories | Persistence file exists; no sealed P-only predictive comparison located. |
| E69 | R-B1 | PENDING | — | — | BRIEF c6d4b904; listed source inventories | No completed sealed behaviour analysis located. |
| E70 | R-D1 | PENDING | — | — | BRIEF c6d4b904; listed source inventories | Sealed vector construction exists; no completed judged-dose analysis located. |
| E71 | R-H1 | PENDING | — | — | BRIEF c6d4b904; listed source inventories | Sealed file is BLANK_TEMPLATE_NOT_HUMAN_CODES (100 items); no completed human codes/kappa located. |
| E72 | earlier-layer S descriptive (no rule) | PENDING | — | — | BRIEF c6d4b904; listed source inventories | No completed sealed layer-read analysis located. |
| E78 | per-row NLA REPORTED at512 | PENDING | — | — | BRIEF c6d4b904; listed source inventories | Package/coverage exists; no completed sealed judged512 outcome analysis located. |

Outstanding provenance work on the next pass: complete affected-stage chronology (first generation versus first judgment versus first opening), especially retained pilots; finish E88 all-bank sign/leakage/read-token checks and E73 redaction-exclusion independent sensitivity; independently refit E79 dev probes. No authority to invent missing records, treat unresolved chronology as validated, or change registrations is assumed.

Review calculations are complete for the explicitly tabulated raw checks; the pass is **partial**, not an all-rules sign-off. The automation will re-check pending seals every two hours through 2026-10-30 06:00 CET.

## Pull-time registration update and shared-branch gate

Reviewed BRIEF diff c6d4b904..73c5b7e7 after required pull --rebase. §204 clarification 1 requires review/publication on origin/r/blindspot; clarification 2 says a result is reviewable only there and E79 extension adds states, not another alpha=.5 dose. Accordingly, computations from other local branches above are **provisional evidence**, not shared-branch sign-off, unless the exact artifact is present below. At the first pass, §205 was outside the requested scope. Guiv subsequently explicitly added E88 item 6; see the addendum below.
- ### §204 clarification 1: first-add commit 280a322a 2026-10-28T11:24:20+01:00; no new E79-extension outcome located; PENDING chronology. Shared-branch publication rule applied now.
- ### §204 clarification 2: first-add commit 42555ff4 2026-10-28T11:31:15+01:00; no new E79-extension outcome located; PENDING chronology. Shared-branch publication rule applied now.
- E56: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e56/analysis402_once_2026-10-27/RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E57: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e57/analysis402_once_2026-10-27/RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E58: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e58b/analysis_20261027/RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E59: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e59/analysis5968_once_2026-10-27/RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E61: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e61/d4_stage_analysis/RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E62: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e62/analysis402_once_2026-10-27/RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E66: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e66/analysis183_once_2026-10-27/RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E67: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/r/e67_analysis/wave1_once/RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E68: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e68/analysis5968_once_2026-10-27/RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E73: analysis artifact ABSENT → NOT EVALUABLE for shared-branch review at 73c5b7e7: `results/g_agreement/i2/E73_ONCE_ANALYSIS_RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E75: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e75/QWEN_RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E76: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e76/regex_20261027/FLOOR_TABLE.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E79: analysis artifact PRESENT at 73c5b7e7: `results/g_agreement/understand/e79/behaviour_once_2026-10-28/metrics/METRICS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.
- E88: analysis artifact ABSENT → NOT EVALUABLE for shared-branch review at 73c5b7e7: `results/g_agreement/understand/e88/AUDIT_RESULTS.json`. Raw judgments/code/seal publication must also be checked; an analysis file alone is not full publication.

## Scope addendum — E88 item 6 (§205; explicitly requested by Guiv)

| Experiment | Rule/item | Verdict | Independent number | Worker number | Commit checked | Discrepancy / timing evidence |
|---|---|---|---|---|---|---|
| E88 | 6 detector audit (DESCRIPTIVE) | PENDING | No sealed detector-audit judgments or analysis published on inspected shared tip 070b0c24; achieved n unknown | No published result located | 722c1fbdbe957fc7a6305122158851a924f390df | Registration committed 2026-10-28 11:29:49 CET (10:29:49Z); heading says 11:40 CET. Use actual git commit time. First affected new output is unavailable, so pre-output ordering is not yet established. |

- **Registration:** §205 item 1, commit `722c1fbd`, git committer and author timestamp **2026-10-28T11:29:49+01:00**, versus the section's stated **11:40 CET**. This 10 minute 11 second discrepancy is recorded; no timestamp is backdated or inferred from the heading.
- **Affected output boundary:** the first new E88 detector-audit judge response/output on the existing E49/E54 readouts. Those original readouts intentionally predate this descriptive, post-hoc audit and are not the temporal boundary for its new judging procedure. The prose claim that no affected output existed is not independent proof.
- **Scope and n:** every regex-only scored E49/E54 row, one call per readout. No fixed total n is stated; derive the required denominator from the sealed eligible row/readout inventory and compare with acquired and parseable counts. Use §172 signed S and item bootstrap with §202 clauses; report per-row regex S, judge S, intervals, and flips. Preserve the original regex verdicts.
- **Applicable dated rubric clarification:** §202 commit `0d052d31`, actual git time **2026-10-28T10:41:47+01:00**, precedes registration `722c1fbd`. Its ordering against the first new detector-audit judgment remains PENDING until that output is available.
- **Publication search:** after `git pull --rebase`, no E88/detector paths were present in `origin/r/blindspot` at `070b0c24`. The local partial E88 items 1–5 audit and item-5 judge-swap packet are not item-6 outputs. No completed item-6 seal was located; neither a numerical verdict nor a successful chronology check is asserted.
- **Next pass:** locate the first sealed item-6 judgment, its creation/file timestamp and first commit; compare with registration and every applicable rubric clarification, then independently recompute all row-level comparisons. The two-hour automation now includes this check. R-2's E90/E91/E85 and R-5's E97 are outside R-Q ownership.

## Concurrent BRIEF clarification found during publication

| Experiment | Rule/item | Verdict | Independent number | Worker number | Commit checked | Discrepancy / timing evidence |
|---|---|---|---|---|---|---|
| E94 | H-A1; §203 clarification 1 | PENDING | No E94 sealed output on shared tip 070b0c24 | Unavailable | c024eb5ab460d185b53714d3c29c9ea6a23fec60 | Actual author/committer time 2026-10-28 11:46:46 CET; heading 12:05 CET (18m14s later). First affected output unavailable; pre-output ordering unverified. E67 any CONTRADICTED means wrong, else any SUPPORTED correct, else no mention; waves separate; E67 excluded from pooled H-A1 and pooled ensemble. |


## Scheduled pass — 2026-10-28 13:28 CET

Shared snapshot `c596e3056`; only published sealed artifacts, their hash-bound raw sources and analysis code were inspected. Prior provisional calculations are preserved. Git commit times govern chronology; nominal headings are informational. No worker chats were read and no handoff interpretation was adopted.

| Experiment | Rule/item | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E79 | R-C1/R-C2 full reader contrast | PENDING | No completed reader-outcome seal on this shared snapshot | No published completed outcome | c596e3056 | Behaviour-only prior audit remains; extension vector seals are inputs, not reader-outcome analysis. |
| E80/E80b/E80c | R-X1–R-X4, especially R-X3 PCA condition | PENDING | No completed judged outcome seal located | Unavailable | c596e3056 | Forecast/code/route seals do not supply the registered contrasts. |
| E87 | R-L1 | PENDING | No completed sweep analysis located | Unavailable | c596e3056 | Require both controls and random-vector placebo under dated clarifications. |
| E93 | R-SR1 | PENDING | No sealed generation/analysis located | Unavailable | c596e3056 | Template-before-generation ordering remains unverified. |
| E88 | item 1 sign/labels | NOT EVALUABLE (review incomplete) | Published trace retains focus_ignore AUROC 0.0017006802721088435 | Same; real reversal, no inversion found | aa8712f3a | New code-level sign trace is published; independent complete probe score/label rejoin remains outstanding. No inversion is authorized. |
| E88 | item 2 raw bounds, CPU core | MET (audit recomputation only) | 14,476 raw records, 153 row-reader cells, 456 UNPARSEABLE; 9 cells can flip | Same 9; every recomputed point/CI matches | aa8712f3a | Independently applied signed rubric and common.stats.bootstrap_ci, 2,000 draws seed 20261028; all lower/upper/parseable CIs matched within 1e-12. This is not an experimental decision rule. |
| E88 | item 2 E56 direction supplement | MET (audit recomputation only) | 72 raw records, 36 cells, 0 CI discrepancies | n=72, 36 cells | 0854e85ba | Rejoined original private key, direction variant and terminal judgments; common.stats lower/upper bootstraps match every cell. Disjoint from CPU core. |
| E88 | item 3 leakage | NOT EVALUABLE (review incomplete) | Sealed CPU output now published; independent full edit-distance enumeration outstanding | E49 6616, E54 0, E56 6738, E57 14144, E59 0, E62 21435, E73 3 near pairs | aa8712f3a | These counts are worker values, not independently certified in this pass. |
| E88 | item 4 read token | NOT EVALUABLE (review incomplete) | Inventory n=984: E49 135, E54 17, E56 110, E57 168, E59 51, E62 231, E73 272 | 984 PASS | aa8712f3a | Counts equal ceil(5% of full bank) for each bank. Independent tokenizer load failed because installed tokenizers binary is x86_64 on arm64 Python; encoded strings and capture custody are not signed off. |
| E88 | item 5 judge swap | PENDING | Frozen packet n=300; no completed new judgments | READY, no dispatch/result | 0854e85ba | No kappa or verdict-flip estimate yet. |
| E88 | item 6 detector audit | PENDING | Frozen packet n=3024 (E49 2688 + E54 336); no completed detector judgments | READY, no dispatch/result | 0854e85ba; registration 722c1fbd | New first affected judge output unavailable; registration-before-output ordering remains unverified. |
| E94 | H-A1 descriptive hypothesis, available paired value-bank pool | MET | 943/1001 conditional correct = 0.942057942057942; better marginal 1442/4313 = 0.33433804776257825; difference 0.6077198942953638; cluster bootstrap CI [0.5897563454891208, 0.6259484247789372] | Identical difference/CI and MET | 483ab89ee | Independently rebuilt classes/paired items from raw judgments and private keys; verified all 112 source-file hashes. No decision-rule claim. Pool excludes E67 and lacks paired E62/E76. |
| E94 | conditional-correct Wilson check | MET (audit recomputation only) | common.stats.wilson(943,1001): [0.9258235443109158, 0.9549122850974207] | [0.9258238760113036, 0.9549120771396113] | 483ab89ee | Tiny difference comes from common z=1.96 versus worker z=1.95996398454; point rate agrees. |
| E94 | registered data/report completeness | NOT EVALUABLE (incomplete) | Available pool n=4313, 4289 source clusters; E76 floor unavailable; E62 has no paired NLA acquisition | E76 unavailable, E62 unavailable | 483ab89ee | Available-bank H-A1 is met; full requested placebo agreement report remains incomplete. Check treatment of nonbinary E57 controls before final all-bank sign-off. |
| E78 | ordinal rows after clarification | NOT EVALUABLE (no registered mapping) | table_column_ordinal and python_depth_ordinal: 288 inventoried items, no binary judge mapping | No completed analysis | f77485111 | Literal clarification excludes these rows; all other E78 judgments/analysis remain PENDING. |

### E88 independently recomputed missingness flips

The prior partial four-cell list gains five E73 cells once the complete published audit is included. All nine below match the worker's frozen binary bounds view. Each bracket is [S, CI low, CI high], and counts every missing judgment as wrong or correct. These are sensitivity flags; original sealed verdicts are not changed.

| Bank | Reader / row | Lower bound | Upper bound |
|---|---|---|---|
| E56 | Oracle adjective_implicit | [0.05952380952380952, -0.07142857142857142, 0.17857142857142858] | [0.36904761904761907, 0.2619047619047619, 0.47619047619047616] |
| E59 | Oracle decline_plan | [0.16666666666666666, -0.023809523809523808, 0.35714285714285715] | [0.2857142857142857, 0.09523809523809523, 0.4642857142857143] |
| E62 | Oracle S3_L1 | [0.16666666666666666, 0.047619047619047616, 0.2857142857142857] | [0.21428571428571427, 0.09523809523809523, 0.3333333333333333] |
| E62 | Oracle S5_L1 | [0.11904761904761904, -0.03571428571428571, 0.2619047619047619] | [0.21428571428571427, 0.07142857142857142, 0.35714285714285715] |
| E73 | NLA W1 | [0.075, -0.03, 0.175] | [0.225, 0.135, 0.32] |
| E73 | Oracle W1 | [-0.11, -0.21012499999999998, -0.01] | [0.23, 0.13, 0.335] |
| E73 | Oracle W2 | [-0.14, -0.215, -0.07] | [0.21, 0.145, 0.28] |
| E73 | Oracle W4 | [-0.16, -0.23, -0.095] | [0.2, 0.135, 0.265] |
| E73 | Oracle W7 | [-0.07, -0.215, 0.065] | [0.94, 0.895, 0.975] |

### E94 independent counts and chronology

Raw class reconstruction uses singleton gold value = correct, singleton opposite = wrong, both/property/exhibits/silent = no mention; either UNPARSEABLE excludes the pair. Independent paired counts: E56 1091, E57 1641, E59 480, E73 1101. E56's 1091 pairs correspond to 1067 source clusters because injection arms share source directions. Common-stat item/cluster bootstrap reproduces every per-bank H-A1 CI: E56 difference 0.5409986326276088 CI [0.5078053368746137, 0.5747186162084873]; E57 0.6993959144742071 [0.6631236820622493, 0.7329780819034792]; E59 0.2056910569105691 [0.1697628104777696, 0.23620990880610443]; E73 0.6331293159713189 [0.5937051131888318, 0.67148163404841]. Pooled ensemble coverage is 1001/4313 = 0.23208903315557616.

- E94 original §203 registration: `4e05da31e`, authoritative commit 2026-10-28 11:03:32 CET. **PRE-OUTPUT** against the analysis ONCE timestamp 2026-10-28 11:50:04.787106 CET.
- E94 §203 clarification 1: `c024eb5ab`, authoritative commit 2026-10-28 11:46:46 CET. **PRE-OUTPUT** by 3m18.787s against that first affected analysis claim. E67 claim mapping is separate by wave and excluded from the pooled hypothesis as required. Earlier original reader outputs are source material, not outputs of this newly registered CPU analysis.
- E88 original registration: `0567e8a10`, authoritative commit 2026-10-28 10:33:42 CET. **PRE-OUTPUT** against earliest preserved CPU ONCE claim 11:50:57.065327 CET; completed sealed CPU result has source mtime 12:00:15.213198 CET. CPU schema repair records zero completed statistics before its continuation and preserves the original claim; plan/code history includes `5c9bf3cab` and `628c12e8c` at 12:00:15 CET. The original registration establishes rule ordering; exact operational code-freeze chronology is a separate unresolved custody detail.
- E88 §202 and §205 item-6 registration remain applicable to new detector judgments, whose first output is still unavailable. No later pre-output assertion is inferred from the absence of published judgments alone.
- E78 clarification: `f77485111`, authoritative commit 2026-10-28 12:18:00 CET; nominal heading 12:35. No affected judgment/analysis output was located on this shared snapshot, so pre-output ordering is **UNVERIFIED** pending actual output custody.
- BRIEF diff since `ad8d491be` also adds §206 E99, §207 framing and E95/E96/ledger notes. These do not create another R-Q experiment verdict; §207 leaves underlying experiment verdicts unchanged. Earlier pending banks retain their prior status.

## Scheduled pass — 2026-10-28 15:39 CET

Shared snapshot `dd9c105df`. Newly published E70/E72/E78 terminal judgments and sealed analyses reviewed; priority E79, E80c, E87, E93 and E88 items5–6 have no newly completed outcome analysis in the shared diff. E94 prior finding is unchanged. Only this review is edited.

Independent method: verify published judgment/analysis member hashes where present; verify private join-map bytes against frozen blind-seal hash; join terminal judgments by opaque ID; reconstruct singleton-correct +1, singleton-opposite −1, other 0, UNPARSEABLE missing. Use `common.stats.bootstrap_ci(..., fn=np.nanmean, n_boot=2000, seed=20261027)` with acquisition-grid ordering and missing masks retained. E70 also resamples the 8 carriers, retaining both signs and their missingness. No worker once-only entry point was run.

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E70 | oracle R-D1 | NOT MET | control S=1; structural maximum 0.8125 (unit_system, dose2) | NOT MET, falsifier true | 404d42e21 | Raw n=160 per reader: ten cells × 8 carriers × 2 signs. Control passes; structural S exceeds .10 and the >=.20 falsifier is met. |
| E70 | nla R-D1 | NOT MET | control S=1; structural maximum 0.875 (user_expertise, dose4) | NOT MET, falsifier true | 404d42e21 | Raw n=160 per reader: ten cells × 8 carriers × 2 signs. Control passes; structural S exceeds .10 and the >=.20 falsifier is met. |
| E70 | achieved n | MET (inventory check) | n=320; 3 missing | n=320; 3 missing | 404d42e21 | Every cell has registered 8 carriers and both signs; 16 acquired records per cell. |
| E70 | nla prose_sentiment:1 control >=.30 | MET | S=1.0; CI [1.0, 1.0]; n=16, missing=0 | S=1.0; CI [1.0, 1.0] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [1.0, 1.0] also matches. |
| E70 | nla unit_system:1 S <=.10 | NOT MET | S=0.5; CI [0.25, 0.75]; n=16, missing=0 | S=0.5; CI [0.25, 0.75] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.1875, 0.8125] also matches. |
| E70 | nla unit_system:2 S <=.10 | NOT MET | S=0.5; CI [0.25, 0.75]; n=16, missing=0 | S=0.5; CI [0.25, 0.75] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.3125, 0.6875] also matches. |
| E70 | nla unit_system:4 S <=.10 | NOT MET | S=0.5; CI [0.25, 0.75]; n=16, missing=0 | S=0.5; CI [0.25, 0.75] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.5, 0.5] also matches. |
| E70 | nla user_expertise:1 S <=.10 | NOT MET | S=0.75; CI [0.5, 0.9375]; n=16, missing=0 | S=0.75; CI [0.5, 0.9375] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.5625, 0.9375] also matches. |
| E70 | nla user_expertise:2 S <=.10 | NOT MET | S=0.75; CI [0.5625, 0.9375]; n=16, missing=0 | S=0.75; CI [0.5625, 0.9375] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.5625, 0.9375] also matches. |
| E70 | nla user_expertise:4 S <=.10 | NOT MET | S=0.875; CI [0.6875, 1.0]; n=16, missing=0 | S=0.875; CI [0.6875, 1.0] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.6875, 1.0] also matches. |
| E70 | nla var_type_at_use:1 S <=.10 | NOT MET | S=0.26666666666666666; CI [0.0625, 0.5]; n=16, missing=1 | S=0.26666666666666666; CI [0.0625, 0.5] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.07142857142857142, 0.4375] also matches. |
| E70 | nla var_type_at_use:2 S <=.10 | NOT MET | S=0.3333333333333333; CI [0.125, 0.6]; n=16, missing=1 | S=0.3333333333333333; CI [0.125, 0.6] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.13333333333333333, 0.5384615384615384] also matches. |
| E70 | nla var_type_at_use:4 S <=.10 | NOT MET | S=0.1875; CI [0.0, 0.375]; n=16, missing=0 | S=0.1875; CI [0.0, 0.375] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.0625, 0.375] also matches. |
| E70 | oracle prose_sentiment:1 control >=.30 | MET | S=1.0; CI [1.0, 1.0]; n=16, missing=1 | S=1.0; CI [1.0, 1.0] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [1.0, 1.0] also matches. |
| E70 | oracle unit_system:1 S <=.10 | NOT MET | S=0.6875; CI [0.4375, 0.875]; n=16, missing=0 | S=0.6875; CI [0.4375, 0.875] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.5, 0.875] also matches. |
| E70 | oracle unit_system:2 S <=.10 | NOT MET | S=0.8125; CI [0.625, 1.0]; n=16, missing=0 | S=0.8125; CI [0.625, 1.0] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.625, 1.0] also matches. |
| E70 | oracle unit_system:4 S <=.10 | NOT MET | S=0.5; CI [0.25, 0.75]; n=16, missing=0 | S=0.5; CI [0.25, 0.75] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.5, 0.5] also matches. |
| E70 | oracle user_expertise:1 S <=.10 | NOT MET | S=0.5625; CI [0.3125, 0.8125]; n=16, missing=0 | S=0.5625; CI [0.3125, 0.8125] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.5, 0.6875] also matches. |
| E70 | oracle user_expertise:2 S <=.10 | NOT MET | S=0.5625; CI [0.3125, 0.8125]; n=16, missing=0 | S=0.5625; CI [0.3125, 0.8125] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.5, 0.6875] also matches. |
| E70 | oracle user_expertise:4 S <=.10 | NOT MET | S=0.5; CI [0.25, 0.75]; n=16, missing=0 | S=0.5; CI [0.25, 0.75] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.5, 0.5] also matches. |
| E70 | oracle var_type_at_use:1 S <=.10 | NOT MET | S=0.5; CI [0.25, 0.75]; n=16, missing=0 | S=0.5; CI [0.25, 0.75] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.3125, 0.6875] also matches. |
| E70 | oracle var_type_at_use:2 S <=.10 | NOT MET | S=0.1875; CI [0.0, 0.375]; n=16, missing=0 | S=0.1875; CI [0.0, 0.375] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.0, 0.375] also matches. |
| E70 | oracle var_type_at_use:4 S <=.10 | MET | S=0.0625; CI [0.0, 0.1875]; n=16, missing=0 | S=0.0625; CI [0.0, 0.1875] | 404d42e21 | Matches point and both CI bounds within 1e-12. Carrier CI [0.0, 0.1875] also matches. |
| E72 | achieved n | MET (inventory check) | 3 rows × 2 layers × 84 = 504; 4 missing | Same | 6b05aabcb | Matches registered 84 test items per layer; source blocks36/40 off distribution. |
| E72 | unit_system:36 descriptive S >=.20 | MET | S=0.75; CI [0.6428571428571429, 0.8452380952380952]; n=84, missing=0 | S=0.75; CI [0.6428571428571429, 0.8452380952380952] | 6b05aabcb | Matches point and both CI bounds within 1e-12. |
| E72 | unit_system:40 descriptive S >=.20 | MET | S=0.8795180722891566; CI [0.7951807228915663, 0.9518072289156626]; n=84, missing=1 | S=0.8795180722891566; CI [0.7951807228915663, 0.9518072289156626] | 6b05aabcb | Matches point and both CI bounds within 1e-12. |
| E72 | user_expertise:36 descriptive S >=.20 | NOT MET | S=0.04878048780487805; CI [-0.012345679012345678, 0.12195121951219512]; n=84, missing=2 | S=0.04878048780487805; CI [-0.012345679012345678, 0.12195121951219512] | 6b05aabcb | Matches point and both CI bounds within 1e-12. |
| E72 | user_expertise:40 descriptive S >=.20 | NOT MET | S=0.07142857142857142; CI [0.0, 0.14285714285714285]; n=84, missing=0 | S=0.07142857142857142; CI [0.0, 0.14285714285714285] | 6b05aabcb | Matches point and both CI bounds within 1e-12. |
| E72 | var_type_at_use:36 descriptive S >=.20 | MET | S=0.27380952380952384; CI [0.13095238095238096, 0.4166666666666667]; n=84, missing=0 | S=0.27380952380952384; CI [0.13095238095238096, 0.4166666666666667] | 6b05aabcb | Matches point and both CI bounds within 1e-12. |
| E72 | var_type_at_use:40 descriptive S >=.20 | MET | S=0.43373493975903615; CI [0.30120481927710846, 0.5662650602409639]; n=84, missing=1 | S=0.43373493975903615; CI [0.30120481927710846, 0.5662650602409639] | 6b05aabcb | Matches point and both CI bounds within 1e-12. |
| E78 | acquired and judged n | MET (inventory check) | 4992 new + 672 reserved supplement = 5664; 288 ordinal excluded; 5376 binary judged; 15 missing | Same | 499baa57e | 64 binary rows × 84; private IDs unique, exact terminal-ID grid; 512-token channel separate from128. |
| E78 | E36:json_type NLA512 REPORTED criterion | NOT MET | S=0.14285714285714285; CI [-0.03571428571428571, 0.30952380952380953]; n=84, missing=0 | S=0.14285714285714285; CI [-0.03571428571428571, 0.30952380952380953] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:latex_environment NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [-0.023809523809523808, 0.05952380952380952]; n=84, missing=0 | S=0.011904761904761904; CI [-0.023809523809523808, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:latex_section NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:list_depth NLA512 REPORTED criterion | NOT MET | S=-0.011904761904761904; CI [-0.047619047619047616, 0.023809523809523808]; n=84, missing=0 | S=-0.011904761904761904; CI [-0.047619047619047616, 0.023809523809523808] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:list_index NLA512 REPORTED criterion | NOT MET | S=-0.03571428571428571; CI [-0.09523809523809523, 0.023809523809523808]; n=84, missing=0 | S=-0.03571428571428571; CI [-0.09523809523809523, 0.023809523809523808] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:prose_paren NLA512 REPORTED criterion | NOT MET | S=0.05952380952380952; CI [0.011904761904761904, 0.11904761904761904]; n=84, missing=0 | S=0.05952380952380952; CI [0.011904761904761904, 0.11904761904761904] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:prose_quote NLA512 REPORTED criterion | NOT MET | S=0.0; CI [-0.05952380952380952, 0.05952380952380952]; n=84, missing=0 | S=0.0; CI [-0.05952380952380952, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:prose_sentence NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [0.0, 0.03571428571428571]; n=84, missing=0 | S=0.011904761904761904; CI [0.0, 0.03571428571428571] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:python_argument NLA512 REPORTED criterion | NOT MET | S=-0.023809523809523808; CI [-0.11904761904761904, 0.07142857142857142]; n=84, missing=0 | S=-0.023809523809523808; CI [-0.11904761904761904, 0.07142857142857142] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:python_comment NLA512 REPORTED criterion | MET | S=0.2716049382716049; CI [0.13414634146341464, 0.404828042328042]; n=84, missing=3 | S=0.2716049382716049; CI [0.13414634146341464, 0.404828042328042] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:python_depth NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [-0.03571428571428571, 0.07142857142857142]; n=84, missing=0 | S=0.011904761904761904; CI [-0.03571428571428571, 0.07142857142857142] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:python_indent NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:python_string NLA512 REPORTED criterion | NOT MET | S=-0.023809523809523808; CI [-0.10714285714285714, 0.05952380952380952]; n=84, missing=0 | S=-0.023809523809523808; CI [-0.10714285714285714, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:table_column NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:table_role NLA512 REPORTED criterion | NOT MET | S=0.07142857142857142; CI [0.023809523809523808, 0.13095238095238096]; n=84, missing=0 | S=0.07142857142857142; CI [0.023809523809523808, 0.13095238095238096] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E36:table_row NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [-0.023809523809523808, 0.05952380952380952]; n=84, missing=0 | S=0.011904761904761904; CI [-0.023809523809523808, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:arith_carry NLA512 REPORTED criterion | NOT MET | S=-0.047619047619047616; CI [-0.15476190476190477, 0.05952380952380952]; n=84, missing=0 | S=-0.047619047619047616; CI [-0.15476190476190477, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:arith_compare NLA512 REPORTED criterion | NOT MET | S=0.0; CI [-0.047619047619047616, 0.047619047619047616]; n=84, missing=0 | S=0.0; CI [-0.047619047619047616, 0.047619047619047616] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:asserted_vs_hypothetical NLA512 REPORTED criterion | NOT MET | S=-0.011904761904761904; CI [-0.08333333333333333, 0.05952380952380952]; n=84, missing=0 | S=-0.011904761904761904; CI [-0.08333333333333333, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:branch_taken NLA512 REPORTED criterion | NOT MET | S=0.047619047619047616; CI [-0.07142857142857142, 0.15476190476190477]; n=84, missing=0 | S=0.047619047619047616; CI [-0.07142857142857142, 0.15476190476190477] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:chased_role NLA512 REPORTED criterion | NOT MET | S=-0.047619047619047616; CI [-0.21428571428571427, 0.10714285714285714]; n=84, missing=0 | S=-0.047619047619047616; CI [-0.21428571428571427, 0.10714285714285714] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:container_after_move NLA512 REPORTED criterion | NOT MET | S=-0.023809523809523808; CI [-0.10714285714285714, 0.05952380952380952]; n=84, missing=0 | S=-0.023809523809523808; CI [-0.10714285714285714, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:decimal_separator NLA512 REPORTED criterion | NOT MET | S=0.10714285714285714; CI [-0.07142857142857142, 0.2857142857142857]; n=84, missing=0 | S=0.10714285714285714; CI [-0.07142857142857142, 0.2857142857142857] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:holder_after_handovers NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:instruction_provenance NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:negation_scope NLA512 REPORTED criterion | MET | S=0.2857142857142857; CI [0.17857142857142858, 0.39285714285714285]; n=84, missing=0 | S=0.2857142857142857; CI [0.17857142857142858, 0.39285714285714285] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:next_paragraph_language NLA512 REPORTED criterion | MET | S=0.42857142857142855; CI [0.3211309523809524, 0.5357142857142857]; n=84, missing=0 | S=0.42857142857142855; CI [0.3211309523809524, 0.5357142857142857] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:pronoun_referent NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:topic_twin NLA512 REPORTED criterion | MET | S=0.7619047619047619; CI [0.6666666666666666, 0.8452380952380952]; n=84, missing=0 | S=0.7619047619047619; CI [0.6666666666666666, 0.8452380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:unit_system NLA512 REPORTED criterion | MET | S=0.5476190476190477; CI [0.4166666666666667, 0.6666666666666666]; n=84, missing=0 | S=0.5476190476190477; CI [0.4166666666666667, 0.6666666666666666] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:user_expertise NLA512 REPORTED criterion | MET | S=0.35714285714285715; CI [0.25, 0.47619047619047616]; n=84, missing=0 | S=0.35714285714285715; CI [0.25, 0.47619047619047616] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E49:var_type_at_use NLA512 REPORTED criterion | NOT MET | S=0.08333333333333333; CI [-0.03571428571428571, 0.21428571428571427]; n=84, missing=0 | S=0.08333333333333333; CI [-0.03571428571428571, 0.21428571428571427] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E54:injection_awareness NLA512 REPORTED criterion | NOT MET | S=-0.23809523809523808; CI [-0.34523809523809523, -0.13095238095238096]; n=84, missing=0 | S=-0.23809523809523808; CI [-0.34523809523809523, -0.13095238095238096] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | E54:reasoning_bridge NLA512 REPORTED criterion | NOT MET | S=0.0; CI [-0.11904761904761904, 0.11904761904761904]; n=84, missing=0 | S=0.0; CI [-0.11904761904761904, 0.11904761904761904] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:json_depth NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [0.0, 0.047619047619047616]; n=84, missing=0 | S=0.011904761904761904; CI [0.0, 0.047619047619047616] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:json_field NLA512 REPORTED criterion | NOT MET | S=0.03614457831325301; CI [-0.03571428571428571, 0.10975609756097561]; n=84, missing=1 | S=0.03614457831325301; CI [-0.03571428571428571, 0.10975609756097561] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:json_type NLA512 REPORTED criterion | MET | S=0.6790123456790124; CI [0.5541434970651838, 0.7901234567901234]; n=84, missing=3 | S=0.6790123456790124; CI [0.5541434970651838, 0.7901234567901234] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:latex_brace NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:latex_environment NLA512 REPORTED criterion | NOT MET | S=0.047619047619047616; CI [0.011904761904761904, 0.09523809523809523]; n=84, missing=0 | S=0.047619047619047616; CI [0.011904761904761904, 0.09523809523809523] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:latex_fraction NLA512 REPORTED criterion | MET | S=0.4166666666666667; CI [0.2976190476190476, 0.5357142857142857]; n=84, missing=0 | S=0.4166666666666667; CI [0.2976190476190476, 0.5357142857142857] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:latex_item NLA512 REPORTED criterion | NOT MET | S=0.17857142857142858; CI [0.09523809523809523, 0.2619047619047619]; n=84, missing=0 | S=0.17857142857142858; CI [0.09523809523809523, 0.2619047619047619] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:latex_math NLA512 REPORTED criterion | NOT MET | S=0.16666666666666666; CI [0.011904761904761904, 0.32142857142857145]; n=84, missing=0 | S=0.16666666666666666; CI [0.011904761904761904, 0.32142857142857145] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:latex_section NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [0.0, 0.03571428571428571]; n=84, missing=0 | S=0.011904761904761904; CI [0.0, 0.03571428571428571] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:list_completed NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:list_depth NLA512 REPORTED criterion | NOT MET | S=-0.011904761904761904; CI [-0.03571428571428571, 0.0]; n=84, missing=0 | S=-0.011904761904761904; CI [-0.03571428571428571, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:list_index NLA512 REPORTED criterion | NOT MET | S=0.047619047619047616; CI [0.0, 0.10714285714285714]; n=84, missing=0 | S=0.047619047619047616; CI [0.0, 0.10714285714285714] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:list_ordered NLA512 REPORTED criterion | NOT MET | S=0.11904761904761904; CI [0.05952380952380952, 0.19047619047619047]; n=84, missing=0 | S=0.11904761904761904; CI [0.05952380952380952, 0.19047619047619047] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:list_task NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:list_words NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [0.0, 0.03571428571428571]; n=84, missing=0 | S=0.011904761904761904; CI [0.0, 0.03571428571428571] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:prose_budget NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [-0.023809523809523808, 0.05952380952380952]; n=84, missing=0 | S=0.011904761904761904; CI [-0.023809523809523808, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:prose_column NLA512 REPORTED criterion | NOT MET | S=-0.011904761904761904; CI [-0.03571428571428571, 0.0]; n=84, missing=0 | S=-0.011904761904761904; CI [-0.03571428571428571, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:prose_paren NLA512 REPORTED criterion | NOT MET | S=0.0; CI [-0.05952380952380952, 0.05952380952380952]; n=84, missing=0 | S=0.0; CI [-0.05952380952380952, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:prose_quote NLA512 REPORTED criterion | NOT MET | S=0.047619047619047616; CI [0.0, 0.10714285714285714]; n=84, missing=0 | S=0.047619047619047616; CI [0.0, 0.10714285714285714] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:prose_sentence NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [-0.023809523809523808, 0.047619047619047616]; n=84, missing=0 | S=0.011904761904761904; CI [-0.023809523809523808, 0.047619047619047616] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:prose_words NLA512 REPORTED criterion | NOT MET | S=0.0; CI [0.0, 0.0]; n=84, missing=0 | S=0.0; CI [0.0, 0.0] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:python_argument NLA512 REPORTED criterion | MET | S=0.2926829268292683; CI [0.19047619047619047, 0.3950617283950617]; n=84, missing=2 | S=0.2926829268292683; CI [0.19047619047619047, 0.3950617283950617] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:python_comment NLA512 REPORTED criterion | MET | S=0.3170731707317073; CI [0.21686746987951808, 0.41980142793395775]; n=84, missing=2 | S=0.3170731707317073; CI [0.21686746987951808, 0.41980142793395775] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:python_depth NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [-0.03571428571428571, 0.05952380952380952]; n=84, missing=0 | S=0.011904761904761904; CI [-0.03571428571428571, 0.05952380952380952] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:python_indent NLA512 REPORTED criterion | NOT MET | S=0.011904761904761904; CI [0.0, 0.03571428571428571]; n=84, missing=0 | S=0.011904761904761904; CI [0.0, 0.03571428571428571] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:python_line NLA512 REPORTED criterion | NOT MET | S=0.03571428571428571; CI [-0.03571428571428571, 0.11904761904761904]; n=84, missing=0 | S=0.03571428571428571; CI [-0.03571428571428571, 0.11904761904761904] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:python_string NLA512 REPORTED criterion | MET | S=0.3125; CI [0.21686746987951808, 0.4146341463414634]; n=84, missing=4 | S=0.3125; CI [0.21686746987951808, 0.4146341463414634] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:table_column NLA512 REPORTED criterion | NOT MET | S=0.13095238095238096; CI [0.011904761904761904, 0.25]; n=84, missing=0 | S=0.13095238095238096; CI [0.011904761904761904, 0.25] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:table_role NLA512 REPORTED criterion | MET | S=0.44047619047619047; CI [0.32142857142857145, 0.5595238095238095]; n=84, missing=0 | S=0.44047619047619047; CI [0.32142857142857145, 0.5595238095238095] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | W1:table_row NLA512 REPORTED criterion | NOT MET | S=-0.023809523809523808; CI [-0.08333333333333333, 0.03571428571428571]; n=84, missing=0 | S=-0.023809523809523808; CI [-0.08333333333333333, 0.03571428571428571] | 499baa57e | Matches point and both CI bounds within 1e-12. |
| E78 | table_column_ordinal | NOT EVALUABLE (no registered mapping) | Excluded in 288-item ordinal inventory | Same | f77485111; 499baa57e | Clarification precedes judging; no binary mapping inferred. |
| E78 | python_depth_ordinal | NOT EVALUABLE (no registered mapping) | Excluded in 288-item ordinal inventory | Same | f77485111; 499baa57e | Clarification precedes judging; no binary mapping inferred. |

New numerical results: E70 R-D1 is NOT MET and its falsifier is met for both readers, with positive controls S=1. All 20 row-cell points/CIs and all20 carrier bootstraps match. E72 four of six layer/row cells reach S>=.20 (unit_system and var_type_at_use at both layers); user_expertise reaches neither. E78 has12/64 binary rows REPORTED and52 MISSED, matching every worker point/CI. The12 reported rows are E36 python_comment; E49 negation_scope, next_paragraph_language, topic_twin, unit_system, user_expertise; W1 json_type, latex_fraction, python_argument, python_comment, python_string, table_role. No E54 row reaches criterion. Historical128-token change comparisons are still not independently signed off.

### E70 diagnostics and remaining custody boundary

The published diagnostics table reports 8/8 eligible carriers for every dose1/2 row and the positive control. At dose4 the eligible counts are unit_system0/8, var_type_at_use0/8, user_expertise1/8; maximum arm cosine-distance differences are .0803553623, .0857362180, .0624231877 respectively. This is an independent recount of the sealed diagnostics, not an independent probe/distance refit. E70 requires diagnostics to be reported; the R4-only exclusion rule does not supply an automatic E70 exclusion. The dose1 counterexamples already falsify R-D1. Vector-before-readout ordering is not fully signed off: the vector-definition/seal first commit has not been located on this shared snapshot. Numerical NOT MET is supported independently of that unresolved custody requirement.

### Per-experiment registration and dated amendment checks

Earliest hash-verified source job mtimes: E70 `jobs/000000.json` 2026-10-27 22:40:06 CET; E72 `jobs/000000.json` 2026-10-27 22:41:38 CET; E78 new acquisition `jobs/000000.json` 2026-10-28 05:12:08 CET. E78 also reuses the672-record E49 supplement, whose sealed `nla_native.jsonl` aggregate mtime is 2026-10-28 03:54:07 CET; that is an aggregate upper bound, not its first generation time. Exact retained-supplement first-job chronology remains outstanding. Earliest preserved judging-run artifacts: E70 START 2026-10-28 14:30:11.503536 CET; E72 START14:30:13.563027; E78 START14:30:11.100882. These establish run-start boundaries; individual earliest API response timestamps are not retained in these flat terminal files.

| Experiment | Dated registration / clarification / deviation | Authoritative commit time CET | Ordering against affected output |
|---|---|---|---|
| E70 | §187 registration, 8b2012d73 | 2026-10-27 15:10:42 | PRE-OUTPUT vs hash-verified first raw job22:40:06. |
| E72 | §189 registration, 8b2012d73 | 2026-10-27 15:10:42 | PRE-OUTPUT vs hash-verified first raw job22:41:38. |
| E78 | §190–195 clarification1, 4cde021df | 2026-10-27 15:23:55 | PRE-OUTPUT vs new acquisition05:12:08 next day; full retained-supplement first-job check outstanding. |
| E70 | §172 clarification1, 0f1e4dd72 | 2026-10-27 02:55:36 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E70 | §172 clarification2 signed S / interval, 3ada24fbf | 2026-10-27 05:03:46 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E70 | §172 clarification3 NLA512 stop, 259db20a5 | 2026-10-27 05:40:04 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E70 | §172 clarification4 one greedy per item, 8c66b004e | 2026-10-27 06:00:59 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E70 | privacy path-redaction ruling, 79f63fe08 | 2026-10-27 22:35:53 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E70 | privacy address extension, 25c32f25e | 2026-10-28 04:43:03 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E70 | §204 judging ledger allocation, 5902d5df4 | 2026-10-28 12:38:41 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E72 | §172 clarification1, 0f1e4dd72 | 2026-10-27 02:55:36 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E72 | §172 clarification2 signed S / interval, 3ada24fbf | 2026-10-27 05:03:46 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E72 | §172 clarification3 NLA512 stop, 259db20a5 | 2026-10-27 05:40:04 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E72 | §172 clarification4 one greedy per item, 8c66b004e | 2026-10-27 06:00:59 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E72 | privacy path-redaction ruling, 79f63fe08 | 2026-10-27 22:35:53 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E72 | privacy address extension, 25c32f25e | 2026-10-28 04:43:03 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E72 | §204 judging ledger allocation, 5902d5df4 | 2026-10-28 12:38:41 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E78 | §172 clarification1, 0f1e4dd72 | 2026-10-27 02:55:36 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E78 | §172 clarification2 signed S / interval, 3ada24fbf | 2026-10-27 05:03:46 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E78 | §172 clarification3 NLA512 stop, 259db20a5 | 2026-10-27 05:40:04 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E78 | §172 clarification4 one greedy per item, 8c66b004e | 2026-10-27 06:00:59 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E78 | privacy path-redaction ruling, 79f63fe08 | 2026-10-27 22:35:53 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E78 | privacy address extension, 25c32f25e | 2026-10-28 04:43:03 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E78 | §204 judging ledger allocation, 5902d5df4 | 2026-10-28 12:38:41 | PRE-JUDGING vs preserved START on Oct28 14:30; For §172 scoring/decoding notes, also precedes each new acquisition. Supplement-first-output caveat applies to E78 decoding scope. |
| E70 | §172 R4 diagnostics clarification1, f21ed03eb | 2026-10-27 07:51:18 | PRE-OUTPUT vs first raw job; requires reporting on-distribution diagnostics. |
| E78 | warm-up deviation, d7b4145b3 | 2026-10-28 02:48:06 | PRE-OUTPUT vs new acquisition05:12:08; retained-supplement first generation still unverified. |
| E78 | running-mean admission, a6d0e06ee | 2026-10-28 03:35:52 | PRE-OUTPUT vs new acquisition05:12:08; retained supplement aggregate03:54:07 is insufficient to prove it predates its first output. |
| E78 | cost-cap deviation, b21fa956d | 2026-10-28 04:44:41 | PRE-OUTPUT vs new acquisition05:12:08; E78-specific cap, not a retroactive supplement design change. |
| E78 | ordinal no-mapping clarification, f77485111 | 2026-10-28 12:18:00 | PRE-JUDGING vs START14:30:11 and first analysis15:11:33; generated text predates clarification, which applies to judging/analysis mapping. |

Analysis publication commits checked: E70 `404d42e21` (2026-10-28 14:49:21 CET), E72 `6b05aabcb` (14:49:23), E78 `499baa57e` (15:12:17). E70/E72 analysis member hashes and E78 published member hashes verified; E78 SCORED_ITEMS is not published, so the independent calculation joins published raw terminal judgments to the hash-bound private map instead. No numerical discrepancy was found.

Concurrent BRIEF changes since31f47ec86 add E81/E90 serial decoding, E97 recapture, E95 mapping, E99 parity and a hardware note. The hardware note commits before later hardware runs must be checked if any new R-Q output uses those devices; these newly reviewed reader outputs predate it. Those external-track rules do not alter E70/E72/E78 numerical thresholds.

Seal-chain follow-up in this pass: for E70/E72/E78 the published judgment seal binds the exact blind-seal hash, and that blind seal binds the exact private join-map hash used in the independent calculation; all three chains verify.

## E79 Arm A priority review — seals 23ed827ac / 017a2b910

Reviewed shared snapshot `1ed8ea6d8`. This supersedes the earlier PENDING status for Arm A numerical R-C1 only. R-C2 remains outside this Arm A result. The original registration and both clarifications are applied literally; alpha4 remains descriptive. No worker chats or rule interpretations were used.

Verified the published analysis and judgment member hashes, blind-seal-to-private-map hash chain, and final integrator audit bindings to unchanged START, JUDGMENT_SEAL and ANALYSIS_SEAL. SCORED_ITEMS is withheld for address-class text; its absence does not prevent an independent join of the published raw judgments with the frozen hash-bound private identity/target map. Targets were also checked against the original sealed injection key. There are4032 records = 3 states ×16 cells ×84, 93 UNPARSEABLE, exactly42/42 injected targets per cell, and the same84 identities/targets across doses and directions.

Independent calculation: singleton target +1, singleton opposite −1, both/property/exhibits/silent0, UNPARSEABLE missing. Paired bootstrap resamples all84 original item indices and computes each arm mean using its own missing mask; no complete-case substitution. `common.stats.bootstrap_ci`, 2000 draws, seed20261027. Every one of the12 registered J-minus-nonJ contrasts and its interval matches the worker within1e-12.

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E79 Arm A | R-C1 numerical rule, alpha<=2 | NOT MET | 0/3 states pass; maximum J S_target=0.09523809523809523 (page_range_digit, alpha2), below0.30 | NOT MET, passing_states0 | 23ed827ac; final audit017a2b910 | Exact raw-grid reproduction; neither state-count requirement nor J target-rate threshold is reached. |
| E79 Arm A | R-C1 falsifier | NOT MET | max J-minus-nonJ=0.13095238095238093 (page_range_digit, alpha2), CI [0.011904761904761904,0.2619047619047619] | falsifier=false | 23ed827ac;017a2b910 | Falsifier requires contrast<0.10 at every eligible dose on all3 states; this cell exceeds0.10. Do not equate failed R-C1 with a met falsifier. |
| E79 Arm A | indent_level, alpha0.25, R-C1 cell | NOT MET | J=0.0; nonJ=0.012048192771084338; difference=-0.012048192771084338; CI [-0.08405407343660355, 0.05966724039013195]; missing J/nonJ=0/1 of84 | difference=-0.012048192771084338; CI [-0.08405407343660355, 0.05966724039013195] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | indent_level, alpha0.5, R-C1 cell | NOT MET | J=-0.011904761904761904; nonJ=0.03571428571428571; difference=-0.047619047619047616; CI [-0.11904761904761904, 0.023809523809523808]; missing J/nonJ=0/0 of84 | difference=-0.047619047619047616; CI [-0.11904761904761904, 0.023809523809523808] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | indent_level, alpha1, R-C1 cell | NOT MET | J=0.023809523809523808; nonJ=-0.047619047619047616; difference=0.07142857142857142; CI [0.0, 0.14285714285714285]; missing J/nonJ=0/0 of84 | difference=0.07142857142857142; CI [0.0, 0.14285714285714285] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | indent_level, alpha2, R-C1 cell | NOT MET | J=0.0; nonJ=-0.011904761904761904; difference=0.011904761904761904; CI [0.0, 0.03571428571428571]; missing J/nonJ=0/0 of84 | difference=0.011904761904761904; CI [0.0, 0.03571428571428571] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | nesting_depth, alpha0.25, R-C1 cell | NOT MET | J=-0.039473684210526314; nonJ=-0.013157894736842105; difference=-0.02631578947368421; CI [-0.12612798198636807, 0.06613621148138088]; missing J/nonJ=8/8 of84 | difference=-0.02631578947368421; CI [-0.12612798198636807, 0.06613621148138088] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | nesting_depth, alpha0.5, R-C1 cell | NOT MET | J=0.0; nonJ=-0.02631578947368421; difference=0.02631578947368421; CI [-0.0410958904109589, 0.10159069701395651]; missing J/nonJ=6/8 of84 | difference=0.02631578947368421; CI [-0.0410958904109589, 0.10159069701395651] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | nesting_depth, alpha1, R-C1 cell | NOT MET | J=0.0125; nonJ=0.02564102564102564; difference=-0.01314102564102564; CI [-0.09090909090909091, 0.06256187713818233]; missing J/nonJ=4/6 of84 | difference=-0.01314102564102564; CI [-0.09090909090909091, 0.06256187713818233] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | nesting_depth, alpha2, R-C1 cell | NOT MET | J=-0.03614457831325301; nonJ=-0.12987012987012986; difference=0.09372555155687684; CI [0.007518796992481203, 0.17951844903064398]; missing J/nonJ=1/7 of84 | difference=0.09372555155687684; CI [0.007518796992481203, 0.17951844903064398] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | page_range_digit, alpha0.25, R-C1 cell | NOT MET | J=0.023809523809523808; nonJ=0.023809523809523808; difference=0.0; CI [-0.13095238095238093, 0.13095238095238096]; missing J/nonJ=0/0 of84 | difference=0.0; CI [-0.13095238095238093, 0.13095238095238096] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | page_range_digit, alpha0.5, R-C1 cell | NOT MET | J=-0.08333333333333333; nonJ=-0.011904761904761904; difference=-0.07142857142857142; CI [-0.22619047619047616, 0.07172619047618886]; missing J/nonJ=0/0 of84 | difference=-0.07142857142857142; CI [-0.22619047619047616, 0.07172619047618886] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | page_range_digit, alpha1, R-C1 cell | NOT MET | J=0.03571428571428571; nonJ=0.03571428571428571; difference=0.0; CI [-0.11904761904761904, 0.11904761904761904]; missing J/nonJ=0/0 of84 | difference=0.0; CI [-0.11904761904761904, 0.11904761904761904] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | page_range_digit, alpha2, R-C1 cell | NOT MET | J=0.09523809523809523; nonJ=-0.03571428571428571; difference=0.13095238095238093; CI [0.011904761904761904, 0.2619047619047619]; missing J/nonJ=0/0 of84 | difference=0.13095238095238093; CI [0.011904761904761904, 0.2619047619047619] | 23ed827ac;017a2b910 | Exact match; J<0.30 in every cell. |
| E79 Arm A | manipulation J and nonJ, all nonzero doses | MET (check only) | 30/30 cells have84/84 positive target-oriented probe shifts; includes alpha4 descriptively | Same signs/counts | 23ed827ac | Independent dev-only logistic refit to sealed raw activations/vectors confirms every sign. Float64 SciPy optimizer differs slightly in magnitude from worker float32 Torch optimizer; see below. |
| E79 Arm A | literal manipulation check, every nonzero cell | NOT MET | nesting_depth random has0/84 positive shifts at each of5 doses (including all4 eligible doses); other40/45 cells pass | Same random failure preserved in MANIPULATION.json | 23ed827ac | Literal phrase is “moves toward the target in every non-zero cell”; random arms are not excepted in that sentence. |
| E79 Arm A | consequence of failed random manipulation for rule interpretation | NOT EVALUABLE (ambiguous) | Numerical R-C1 remains NOT MET and falsifier remains NOT MET; protocol gives no gating action for this failure | Worker numerical R-C1 NOT MET | a12526c51;23ed827ac | Ambiguous scope/consequence of “moves toward the target in every non-zero cell”. No post-hoc exclusion or exemption is inferred. |
| E79 Arm A | norm flag, alpha<=2 | MET (reporting check) | 224 vectors with norm ratio>1.5: indent J84/nonJ36/random84; nesting J1/nonJ19; page0 | Same counts in per-item diagnostics | 23ed827ac | Independently recomputed norms from sealed vectors against each item baseline; all flags occur at alpha2. Flag is descriptive, not a registered exclusion. |
| E79 Arm A | monotone J response over0–2 | NOT MET (descriptive) | 0/3 monotone trajectories | All3 false | 23ed827ac | Independent S_target trajectory check: each state has at least one decrease. |

### Independent manipulation refit and norms

Used exactly84 dev items per state from the hash-verified E57 metadata/captures and the sealed4704-vector input; no test-label fitting. Standardized each feature by dev mean and sample standard deviation (floor1e-4), then independently minimized mean logistic loss +0.001||w||² using SciPy L-BFGS-B with analytic gradients, maxiter1000, history20, ftol1e-14, gtol1e-8. All three optimizations converged. This reproduces the registered probe objective independently; it does not claim identical Torch stopping/rounding. For each sealed vector, computed (probe(hprime)-probe(h)) times target sign. All30 J/nonJ cells have84/84 positive shifts, while all5 nesting_depth random cells have0/84. At alpha1:

| State | Direction | Independent mean signed shift | Worker mean signed shift |
|---|---|---:|---:|
| indent_level | J | 4.275366593572751 | 4.261966546376546 |
| indent_level | nonJ | 22.947422531041468 | 22.91170148622422 |
| indent_level | random | 0.3219733659633238 | 0.32651989800589426 |
| nesting_depth | J | 3.6558333946164945 | 3.6531012551415536 |
| nesting_depth | nonJ | 21.517889476248552 | 21.48110860869998 |
| nesting_depth | random | -0.09464351987284067 | -0.09399762891587757 |
| page_range_digit | J | 4.870933581045354 | 4.872523790314084 |
| page_range_digit | nonJ | 21.584463714823325 | 21.593575017792837 |
| page_range_digit | random | 0.37412027370811773 | 0.3747975428899129 |

All sign counts agree despite optimizer-level magnitude differences. nesting_depth random independent mean shifts at alpha .25/.5/1/2 are −.023660863399012702 / −.04732174931020637 / −.09464351987284067 / −.18928703233606328. This confirms a real failed random-direction manipulation rather than a reporting-only mismatch.

Independent norm-ratio maxima at alpha2: indent J1.7100271408117549, nonJ1.8366423811413117, random1.6402875686618863; nesting J1.514893893779838, nonJ1.6832326240927302 (random has0 flags); page has0 flags. Alpha4 remains descriptive and has84/84 >1.5 in each direction for indent and nesting; no alpha4 result is used to rescue R-C1.

### Registration, clarifications and first affected outputs

| E79 dated note | Authoritative commit time CET | First affected output comparison |
|---|---|---|
| §196 original registration a12526c51 | 2026-10-28 05:14:36 | PRE-OUTPUT: earliest hash-verified native job jobs/000000.json is06:55:15 CET. |
| §196 clarification1 b3c1e6d0e, Arm B AUROC behaviour metric | 2026-10-28 05:17:11 | PRE-OUTPUT vs earliest combined-run native job06:55:15; does not change Arm A rule. |
| §196 clarification2 1e879d020, lower doses and alpha<=2 rule range | 2026-10-28 05:27:11 | PRE-OUTPUT vs earliest native job06:55:15; governs this review. |
| §172 rubric clarifications1–4 (0f1e4dd72,3ada24fbf,259db20a5,8c66b004e) | Oct27 02:55:36 /05:03:46 /05:40:04 /06:00:59 | All PRE-OUTPUT vs Oct28 native acquisition and judging. |
| Privacy path ruling79f63fe08 / address extension25c32f25e | Oct27 22:35:53 /Oct28 04:43:03 | Both PRE-JUDGING vs earliest preserved judging START Oct28 12:40:52.941542 CET. |
| §204 judging allocation5902d5df4 | Oct28 12:38:41 | PRE-JUDGING vs START12:40:52.941542. |

Input seal mtime06:32:51.114264 CET predates first native output06:55:15; its exact input/vector hashes match the executed binding. The shared-branch publication of INPUT_BINDING is later (`f16ce831a`,11:35:53), so this is evidence of pre-readout file sealing, not a claim of pre-readout shared publication. Final audit017a2b910 is additive and postdates judging/analysis as disclosed; it binds unchanged artifacts rather than registering a new scientific rule. Original analysis output14:50:18 CET follows terminal completion14:47:56 CET; no second worker analysis was invoked here.

The numerical NOT MET / falsifier NOT MET findings are confirmed. The broader causal interpretation must carry the failed random manipulation and norm flags; neither is silently excluded.

Publication rebase check: concurrent BRIEF §208 E100 and its clarification1 register a separate follow-up after the E79 null; they do not amend E79 R-C1, its falsifier, manipulation check or alpha range. No E100 rule was applied retroactively in this review.


## Explicit scope extension — E100 revised scope, E101, Strong-C

Guiv explicitly added BRIEF §209 E101, §208 E100 deviation1, and §207 addendum2. Shared snapshot `7b8433cce`. All three additions are in authoritative commit `69f8c08e4` at **2026-10-28 16:05:05 CET**; the heading16:45 is nominal. No `E101_DOSES.json`, E101 output or E101 raw judged grid is present in the inspected shared tree. Pending is not proof of pre-output ordering.

| Experiment | Rule / check | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E100 | part c R-C4, R-D1, H-T; part d H-U | WITHDRAWN | No scientific verdict assigned | No new result inspected | 69f8c08e4 | §208 deviation1 explicitly withdraws c,d; these rules are dropped and must not appear as failed tests. Whether withdrawal predates every affected output remains to be checked from custody. |
| E100 | part a R-PC | PENDING | No sealed judged transplant grid located | Unavailable | 69f8c08e4; prior f425a5e2a | Retained; >=4/5 reported rows require Oracle S_target>=.50 with item-bootstrap lower bound>.30. Positive-control falsifier and its gate must be checked. |
| E100 | part b R-C3 / H-C3b | PENDING | No sealed judged swap grid located | Unavailable | 69f8c08e4; prior f425a5e2a | Retained subject to R-PC gate; no c/d injection rule substituted. |
| E101 | frozen dose file ordering | PENDING | E101_DOSES.json not published; first test output not located | Unavailable | 69f8c08e4 | Require an actual git commit containing the exact dose-file bytes before the first affected test output; use the first test readout or patched-logit output, whichever is earlier. Dev dose-selection logits are an earlier selection stage, not the test boundary. |
| E101 | alpha-star selection on dev only | PENDING | No dev-logit grid or dose-selection analysis published | Unavailable | 69f8c08e4 | Independently join item identities to sealed dev/test labels; verify smallest alpha in {.5,1,2,4} reaching >=70% target-side dev contrasts. No qualifying alpha => NOT EVALUABLE (no behavioural flip). Verify every fitted direction/scorer/dose choice uses dev only and check separate block42/NLA eligibility. |
| E101 | achieved n / target mapping | PENDING | Registered84 test items per row; seven rows, two interventions, two readers =>2352 new test readouts if all rows qualify, plus matched sealed unsteered references | Unavailable | 69f8c08e4 | Reconcile per-row eligible, acquired, judged, parseable, behaviour-flipped and privacy-excluded denominators; inspect raw patched-logit and terminal-judge grids. No inferred labels for missing records. |
| E101 | R-F1 Oracle | PENDING | No raw judged/behaviour grid yet | Unavailable | 69f8c08e4 | On >=3/4 content/plan rows reaching alpha-star: among behaviour-flipped test items, S_target>=.40 with bootstrap lower bound>.20, and steered-minus-random>=.30 with lower bound>0. Recompute from raw judgments with common/stats.py; retain item pairing and disclosed missing masks. |
| E101 | R-F1 falsifier | PENDING | No raw judged/behaviour grid yet | Unavailable | 69f8c08e4 | S_target<=.10 on >=3 qualifying content/plan rows; evaluate separately from failure of the positive rule. |
| E101 | R-F2 Oracle | PENDING | No raw judged/behaviour grid yet | Unavailable | 69f8c08e4 | On >=2/3 bookkeeping rows reaching alpha-star with test B>=.70: S_target<=.10 with bootstrap upper bound<.20. Independently reconstruct B from frozen behaviour contrasts and verify eligibility before scoring. |
| E101 | R-F2 falsifier | PENDING | No raw judged/behaviour grid yet | Unavailable | 69f8c08e4 | S_target>=.30 on >=2 eligible bookkeeping rows; do not infer this from a failed R-F2 alone. |
| E101 | R-F3 | PENDING | R-F1 and R-F2 both pending | Unavailable | 69f8c08e4 | Requires both MET; no double-dissociation claim while either is unevaluable. |
| E101 | reporting checks | PENDING | No B, norm, J-fraction or matched E81 generic baseline sealed yet | Unavailable | 69f8c08e4 | Report B and S per row/reader; norm ratios>1.5 flagged without exclusion; J-fraction beside chance. Verify base-text baseline uses the unchanged conflict prompts. |
| §207 | addendum2 Strong-C | PENDING | R-F1, R-F2/R-PC and E81 falsifier status not yet adjudicated | Unavailable | 69f8c08e4 | Strong-C replaces Strong-D: R-F1 MET and (R-F2 MET or R-PC MET), with E81 not in its own falsifier. Strong-B stands. E79 Arm A null must remain first in every branch. |

Dated amendments within added E100 scope: original §208 `f425a5e2a` (Oct28 15:51:38 CET); clarification1 `d406a695f` (15:52:30; J-fraction reporting / R-PC gate); clarification2 `fd07c12a9` (15:58:19;84 E56 items and token mapping); deviation1 `69f8c08e4` (16:05:05; c,d withdrawn). The token mapping for withdrawn part c is no longer a test requirement; its history remains preserved. The published a/b vector bundle at `c7f7e53aa` (16:15:08) is later than deviation1, but a later publication commit alone does not prove every affected output was generated after withdrawal. No sealed reader outcome was located in this pass. All pre-output claims await the actual earliest output/custody check.

Future passes explicitly search for E101_DOSES.json and its first commit, then verify it against the earliest test output, independently reproduce alpha-star from the full dev-only grid, and independently recompute R-F1/R-F2/R-F3 plus falsifiers from raw terminal judgments and frozen behaviour scores. Any ambiguity is quoted and marked NOT EVALUABLE (ambiguous); no worker interpretation is used to resolve it.


Concurrent registration update during publication: §209 clarification1 `2bdde7635` committed **2026-10-28 16:19:38 CET**, clarification2 `88b74af5a` committed **16:20:58 CET**. No E101 files are yet published on the refreshed shared tree; ordering against actual dose-selection/test outputs remains PENDING. Clarification1 fixes **all84 sealed dev items per row**, separately selected alpha-star at block44 and block42, both committed in E101_DOSES.json; >=70% therefore requires at least59/84 dev flips at a candidate dose. No qualifying block makes that reader/row NOT EVALUABLE while the other may run. Clarification2 fixes behaviour to the **full frozen teacher-forced continuation log-probability contrast**, patching once at the registered read token; target-side sign defines the flip. First-token scoring is valid only where the frozen candidate is single-token (E59); E57 multi-token pairs require the full continuation score. These definitions govern both independent dose reconstruction and test B/R-F1/R-F2 eligibility. No first-token shortcut is accepted for multi-token rows.

## E80 priority review — independent R-X1 / R-X2

Reviewed sealed E80 publication `38c02746f` and the author/runner code commit `5d0ba0a56`. Numerical results below use the E80b forecast of record (76/518 J-visible), with the original forecast's logit rank as the control, exactly as disclosed in the analysis. Original189c1161 J forecast has14/518 visible and remains a separate measurement-error comparison. The analysis retains its disclosed exploratory label under §198.

Independently verified all six input pins, the published raw judged-grid hash, available judgment-seal members, and the exact analysis-spec/result seals. Reconstructed all1036 passes directly from raw results, readout text, and family packets: basic scorer600 records, multilingual frozen regex196 (independently re-matched forms), chain scorer240. For chain, every credited hit contains its top gold number as a whole number in the readout; no positive depends solely on the ported quote-fold helper. Every reader has518 items, zero missing, and the exact registered five-family inventory100/98/120/100/100.

R-X1 was independently computed from family2x2 tables using Mantel–Haenszel OR and the Robins–Breslow–Greenland log-OR variance. No0.5 correction was needed. R-X2 used within-family positive/negative rank pairs with half credit for ties, independent rank-sum computation for10000 within-family permutations (seed20261028), and independently optimized logistic maximum likelihood with family intercepts plus log(logit rank), then log(J rank). SciPy BFGS fit agrees with the worker's Newton fit to numerical precision; this is an independent fit, not a worker entry-point rerun. Supplemental per-family Wilson intervals use common/stats.py; Wilson and bootstrap are not replacements for these registered MH/permutation/LR tests.

| Experiment | Rule | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E80 | Oracle R-X1 | MET | OR3.738356349851069; CI[1.5553012240005564,8.985595833663929] | OR3.738356349851069; CI[1.555301224000556,8.985595833663929] | 38c02746f; code5d0ba0a56 | Exact to floating-point precision; OR>=2 and lower bound>1. |
| E80 | Oracle R-X1 falsifier | NOT MET | OR3.738356349851069>1.2 | MET positive rule, no falsifier | 38c02746f | Separately checked falsifier threshold. |
| E80 | Oracle R-X2 | NOT MET | AUROC0.6441040256501603; permutation p0.00019998000199980003 (1/10000 exceedances); LR chi2=17.39525437060786, p=0.00003035830029002111 | Same AUROC/permutation p; LR chi2=17.395254370607972,p=0.000030358300290019338 | 38c02746f;5d0ba0a56 | Statistical significance passes both p<.01 conditions, but AUROC<.65. LR discrepancy about1e-13 is optimizer roundoff. |
| E80 | NLA R-X1 reported analogue | MET | OR7.6567204301075265; CI[3.2309026605470055,18.14519776801337] | OR7.6567204301075265; CI[3.2309026605470064,18.14519776801337] | 38c02746f | Exact to floating-point precision; not substituted for Oracle rule. |
| E80 | NLA R-X2 reported analogue | MET | AUROC0.6526857983811626; permutation p0.00009999000099990002 (0/10000 exceedances); LR chi2=31.62107995074473,p=1.8738444149320012e-8 | Same AUROC/permutation p; LR chi2=31.621079950744672,p=1.8738444149320588e-8 | 38c02746f | All three numerical thresholds pass; LR roundoff only. |
| E80 | achieved n / scorer grid | MET (inventory check) | 518/reader,1036 total;0 missing;76 visible/reader | Same | 38c02746f | Five-family item and terminal grids reconcile. |
| E80 | code-before-analysis-output | MET (chronology check) | code commit16:23:42 CET; first analysis output16:24:06.298470 CET; lead24.298470s | receipt start16:24:00,first output16:24:06 | 5d0ba0a5605e821cb5bd58933189bd3235534e0e | Actual git author/committer times agree. e80_analysis.py, score80.py and imported e80c_analysis.py bytes all match that commit. This checks analysis output; original reader outputs existed earlier. |
| E80 | code-before-judged-output-opening assertion | NOT EVALUABLE (custody evidence missing) | No independently timestamped first judged-output opening event located | Source docstring asserts before judged outputs opened | 5d0ba0a56 | Pre-analysis code commit is verified; it alone does not prove when the author first opened already-generated judgments. |
| E80 | published benchmark floors | PENDING | No lucky-guess / prompt-only floor values in frozen export | NOT PACKAGED | 38c02746f | Required descriptive comparison incomplete; no values invented. |

### Family tables and supplemental Wilson checks

Each2x2 table is [visible pass,visible fail,invisible pass,invisible fail]. These independent counts match every worker table.

| Reader | Family | Independent 2x2 table | Pass rate; common.stats Wilson95 |
|---|---|---|---|
| nla | multihop | [36,3,30,31] | 0.66; [0.5627754565831095,0.74538620502457] |
| nla | multilingual_multihop | [3,5,27,63] | 0.30612244897959184; [0.22362525822357754,0.4032462756093553] |
| nla | chain_intermediates | [0,0,3,117] | 0.025; [0.00853802009878548,0.07093123740434756] |
| nla | association | [29,0,56,15] | 0.85; [0.7671626666784216,0.906940968088377] |
| nla | poetry | [0,0,34,66] | 0.34; [0.25461379497543,0.43722454341689065] |
| oracle | multihop | [35,4,44,17] | 0.79; [0.7001985069803768,0.8583445046835422] |
| oracle | multilingual_multihop | [0,8,9,81] | 0.09183673469387756; [0.04906865909068409,0.16539772792601637] |
| oracle | chain_intermediates | [0,0,5,115] | 0.041666666666666664; [0.017926452505837805,0.0938421292954309] |
| oracle | association | [28,1,52,19] | 0.8; [0.7111690380734977,0.8666340774409013] |
| oracle | poetry | [0,0,11,89] | 0.11; [0.06254131955225126,0.18631463027903022] |

### E80 registration and dated chronology

- Original registration `2e8dbc374`: actual commit2026-10-28 06:19:42 CET. Pin `a8136e50d`:06:19:53. Clarification1 `487616241`:06:22:46 (518 items, relational family excluded). Clarification2 `4a22d4488`:06:25:05 (default headline scorer, multilingual regex). All PRE-OUTPUT against the earliest hash-verified native job `jobs/oracle_0000.json`,07:18:18 CET.
- Power note `0d80f81d4`:06:58:32; correction `e3f5cad41`:06:59:07. Both PRE-OUTPUT against07:18:18. These do not change thresholds; underpowered is not a falsifier unless OR<=1.2.
- E80b forecast-method clarification `08c71a71a`:07:44:02; exact forecast bytes committed originally in `5959b1f82` at07:51:42, then shared `21151275c` at11:22:01. These follow first native generation, which is permitted by the explicit **before outputs are opened** custody rule. Frozen E80_CUSTODY_RECEIPT records first reader opening14:28:45 CET, after both forecast commits, and binds exact forecast/join/readout hashes; thus the documented forecast-before-opening gate passes. This is a custody receipt, not an instruction about a rule.
- Analysis author/runner disclosure is preserved. Main module commit `5d0ba0a56`16:23:42 precedes receipt start16:24:00 and physical first RESULTS file16:24:06.298470; supporting scorer/import code first committed `7b8433cce`16:18:03. Seal/result hashes and as-run code bytes reconcile. The once guard is written after the numerical analysis in source code, so guard mtime alone is not used as its start time.
- No altered E80 rule was accepted from an integrator interpretation. Analysis-specific choices (log rank,10000 permutations,RBG CI) are explicit in pre-analysis committed code; the separate claim that code preceded the first opening of judged results lacks an independently timestamped opening artifact.

## §211 CORE priorities — direct Guiv instruction

Section211 commit `6eca49bca`, authoritative time2026-10-28 16:52:18 CET, makes the remaining CORE due **Thu29 Oct22:00 CET**, without changing scientific rules. In R-Q's assigned scope, prioritize **E101**, then **E80c and E87** as they seal; finish CPU E80/E88/E94 and E76 floor comparisons; E100 a/b remains lower-priority CORE item7. E81/E86/E82/E99/E103 stay with their assigned reviewers (E103 is explicitly R-5). Do not expand R-Q into other reviewers' rule ownership.

Parked experiments stay **PENDING (parked §211)** without further checks: within R-Q this includes E79 extension, E75 rerun and E93 (unless explicitly reactivated). Existing sealed earlier-bank findings remain preserved. E100 c/d stays WITHDRAWN under deviation1, not a failed or pending test. The user-requested E80 check above was completed before applying this new queue. No E101 dose file or first test outcome has been located on the refreshed shared snapshot.

## Budget authority correction — direct Guiv instruction

Track Q's GPU launch gate is **USD900**, authorized directly by Guiv in this chat, inside the all-track **USD2500** §204 planning ceiling. The earlier USD500 Track Q launch figure is superseded and must not be used to reject E87 relaunches or E101 rows. BRIEF budget note2 `dfe326565b134742c384f1ca20a04208ee564adb`, authoritative git time2026-10-28 16:44:47 CET (heading16:50 nominal), raises the all-track GPU ceiling for Oct28–30 to2500; planning envelope means booked spend plus every active cap, with compiler warning at2000. That commit itself does not state the Track Q900 allocation; the allocation's authority is Guiv's direct message. The **judging** ledger remains USD500 under the same note and is distinct from the GPU launch gate. Scientific thresholds, CORE priorities and chronology requirements are unchanged. Future budget-ordering checks compare this actual commit/direct authorization with the affected launch/output; no E87/E101 launch was refused by R-Q here.

## Scheduled CORE pass — 2026-10-28 17:43 CET

Shared snapshot `8d229f757`. E101 now has **six sealed dev-row outputs**; fact_recall, final E101_DOSES.json and test judged outcomes remain unpublished. E80c, E87 and E88 items5–6 have no new completed analysis on this snapshot; prior E80/E94 results stand. Parked experiments were not checked.

Independently recomputed each selection from every raw dev job in its published RAW_OUTPUTS.tar.gz without extracting or modifying results. Verified all row-seal member hashes, every archived output member hash, input seals and input members, and the exact job/item order/completeness. Rejoined CPU labels against the **original hash-verified E56/E57/E59 metadata** via SHA256('E101:'+bank+':'+original_id), rather than accepting stage labels alone. All selected item identities are originally dev, with original labels and target sign1-2*label; all six rows have84 distinct source items per block at each of four doses. No test item enters selection. All raw continuation log probabilities are finite. Counts below use the mean of frozen-pair full continuation logP(A)-logP(B), times the other-value target sign; zero contrast is not a target-side flip. This is independent CPU counting, not the once-only worker selector.

| Experiment | Rule/check | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E101 | format_plan block44 dev dose | NOT EVALUABLE (no behavioural flip) | counts at alpha[.5,1,2,4]=[42,42,42,42]/84; alpha-star none | Identical | 5abdb04ed | All counts below59/84; exact match. |
| E101 | format_plan block42 dev dose | NOT EVALUABLE (no behavioural flip) | [42,42,42,42]/84; none | Identical | 5abdb04ed | Exact match. |
| E101 | indent_level block44 dev dose | NOT EVALUABLE (no behavioural flip) | [0,38,42,55]/84; none | Identical | 775639678 | Best55/84=.6547619048, below.70; exact match. |
| E101 | indent_level block42 dev dose | NOT EVALUABLE (no behavioural flip) | [0,31,42,49]/84; none | Identical | 775639678 | Exact match. |
| E101 | language_continuation block44 dev dose | NOT EVALUABLE (no behavioural flip) | [3,3,6,17]/84; none | Identical | ca105102d | Exact match. |
| E101 | language_continuation block42 dev dose | NOT EVALUABLE (no behavioural flip) | [3,3,4,14]/84; none | Identical | ca105102d | Exact match. |
| E101 | language_plan block44 dev dose | MET (selection check only) | [42,42,42,63]/84; smallest qualifying alpha-star4 | Identical | ca105102d | 63/84=.75; common.stats.wilson95=[.6478552553489343,.830278111984994], supplemental only. Gate uses point share, not Wilson lower bound. Alpha4 is allowed by E101. |
| E101 | language_plan block42 dev dose | NOT EVALUABLE (no behavioural flip) | [42,42,43,51]/84; none | Identical | ca105102d | Block42 does not inherit block44's selected dose. |
| E101 | nesting_depth block44 dev dose | NOT EVALUABLE (no behavioural flip) | [42,42,42,42]/84; none | Identical | 7483d97d4 | Exact match. |
| E101 | nesting_depth block42 dev dose | NOT EVALUABLE (no behavioural flip) | [42,42,42,42]/84; none | Identical | 7483d97d4 | Exact match. |
| E101 | page_range_digit block44 dev dose | NOT EVALUABLE (no behavioural flip) | [0,0,0,0]/84; none | Identical | 7483d97d4 | Exact match. |
| E101 | page_range_digit block42 dev dose | NOT EVALUABLE (no behavioural flip) | [0,0,0,0]/84; none | Identical | 7483d97d4 | Exact match. |
| E101 | dev-only and achieved n | MET (audit check) | Six rows x672=4032 raw dev cells, twelve block/row dose grids, all84 original dev identities per dose | Same | 5abdb04ed/775639678/7483d97d4/ca105102d | No identity, split, count, target-sign or hash discrepancy. Only1/12 available block/row grids qualifies. |
| E101 | fact_recall dev selection | PENDING | No sealed row output on inspected shared snapshot | Unavailable | 8d229f757 | Seventh row outstanding; do not invent a dose. |
| E101 | final dose commit before first test | PENDING | E101_DOSES.json not published; no first test output located | Row seals say final test doses pending | 8d229f757 | Per-row ROW_DOSES.json is not the required final file. Pre-test ordering remains unverified. |
| E101 | R-F1/R-F2/R-F3 and falsifiers | PENDING | No test behaviour/readout/judgment grid yet | Unavailable | 8d229f757 | All3 bookkeeping rows fail available dev gates for both blocks. No causal-blindness result may be claimed from this failure to create eligible interventions. Await final selection disposition and any qualified test grid; do not reclassify dev failure as a passed R-F2. |

### E101 pre-output chronology

Actual commits: registration69f8c08e4 at16:05:05 CET; clarification1 2bdde7635 at16:19:38; clarification2 88b74af5a at16:20:58. All precede every affected sealed dev output by more than50 minutes. Per-row first-output custody is hash-bound in OUTPUT_SEAL.json (first job member, SHA256 and nanosecond mtime) and corroborated in the raw tar. Format_plan17:17:27.374425; indent_level17:20:08.016480; nesting_depth17:28:15.708184; page_range_digit17:28:52.390354; language_continuation17:30:48.114896; language_plan17:30:48.268893 CET. The selection code commit10217c33f at17:14:54 predates even the earliest dev output. Later row-selection publication commits are5abdb04ed17:20:28,77563967817:23:00,7483d97d417:30:36,ca105102d17:33:51; these are naturally after their dev observations and do not establish the still-pending final pre-test dose-file condition.

The acquisition code sums teacher-forced token log probabilities for each frozen candidate and patches the registered block/read token once per forward; the original prefix is unchanged. The independent selection uses pair_logprobs, not first-token pair_logits. No new GPU run or worker once-only selector was invoked.

### E87 relaunch note

New §200 operational note7549cc07b, actual commit2026-10-28 17:11:30 CET (heading17:15 nominal), permits R1 rows1–4 to be preempted for E101. R1 partials must be hash-checked and stored unopened, then unused; one R2 relaunch regenerates the entire frozen row, with14400s new cap and cumulative cap=exact prior custody+14400s. No stitching. **PENDING** for chronology against the first affected R2 output because no completed R2 outcome seal is present here. The USD900 Track Q GPU gate applies under Guiv's authorization; the old500 GPU allocation is not a refusal reason. This operational note changes no R-L1 criterion or random-only placebo requirement.

## Scheduled CORE pass — 2026-10-28 19:46 CET

Shared snapshot `cd8fae015`. Final E101 dose file is now committed; fact_recall's completed dev3 acquisition is pinned by that file. No test outcome/judgment, E80c analysis, E87 result, or E88 items5–6 analysis was newly published. Parked work was not checked.

| Experiment | Rule/check | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E101 | exact final dose-file commit | MET (artifact check) | E101_DOSES.json SHA256 03001cb77234af24fb9302cca2656a674b1cbf6fa67c01075a8a5223afc40efa; original committed bytes identical | Same dose seal / receipt hash | 4343109e2,2026-10-28 18:21:27 CET | Verified git blob against present file and DOSE_SEAL. Embedded status FROZEN_PENDING_GIT_COMMIT is preserved metadata; actual git commit establishes publication. |
| E101 | fact_recall block44 dev dose | MET (selection audit) | counts at alpha[.5,1,2,4]=[0,0,0,71]/84; smallest qualifying alpha-star4; best share .8452380952380952 | Identical | 4343109e2 | Recomputed from all672 fact dev outputs (both blocks), exact frozen item/job join; full continuation contrast, other-value orientation from original E56 dev metadata. |
| E101 | fact_recall block42 dev dose | NOT EVALUABLE (no behavioural flip) | [0,0,0,46]/84; no alpha reaches59/84 | Identical | 4343109e2 | Separate block42 selection retained. |
| E101 | fact_recall achieved n / dev-only | MET (audit) | 84 original dev items x4 doses x2 blocks=672; all finite scores; no test identities | Same | 4343109e2 | Verified input/output seals and every member; CPU key labels/splits agree with original hash-verified E56 metadata. |
| E101 | fact_recall supplemental Wilson | MET (calculation check only) | block44 best71/84: CI [.753011640086769,.9072677719457987]; block42 best46/84: [.44142846686988807,.6496445554794317] | Selection uses point counts, not CI gate | 4343109e2 | common.stats.wilson; supplemental intervals do not alter registered70% dose threshold. |
| E101 | final selection consistency | MET (audit) |2/14 block-row arms selected: Oracle fact_recall4 and language_plan4; all12 others have no qualifying dose | Same | 4343109e2 | Prior independently verified12 block-row selections match final file byte-for-value; they were not re-fitted/re-run. |
| E101 | dose commit before first test output | PENDING | Final dose commit18:21:27 CET is known; no first test output/custody available on inspected shared tree | Receipt says test_inputs_created=false at selection | 4343109e2;cd8fae015 | Do not infer pre-test ordering solely from a committed dose file or an earlier status assertion. Compare actual earliest test readout/log-probability output once sealed. |
| E101 | R-F1/R-F2/R-F3 plus falsifiers | PENDING | Only2/4 Oracle content/plan rows qualify;0/3 bookkeeping rows and0/7 NLA rows qualify |2 selected,12 not evaluable | 4343109e2 | No test judged grid exists yet. R-F1 requires>=3 content rows, so do not relax its row count; failed bookkeeping dev intervention is not evidence of reader blindness or an R-F2 pass. |

Fact_recall raw source is the complete `dev3/fact_recall/out`, output seal d630639717716372e18146d9a826ac0590149fbb619b2f39d62d775c013fcc7f, first hash-bound output **2026-10-28 18:17:30.724171 CET**. Original registration69f8c08e4 and clarifications2bdde7635 /88b74af5a all predate it; the dose-selector code10217c33f17:14:54 also predates it. CPU final selection receipt starts18:20:54 and writes18:20:55, followed by dose commit18:21:27. The older FACT_RECALL_ACQUISITION_BLOCKER reflects an incomplete prior attempt; it is not a completed scientific selection and is superseded by this pinned complete dev3 source. No changed scientific rule was found in the BRIEF diff.

E80c/E87/E88 items5–6 remain PENDING without a new sealed outcome; earlier completed calculations stand. The git client emitted missing commit-graph warnings, but exact git blob reads and normal pull/rebase succeeded; no Git metadata was repaired or altered outside normal reviewer commit operations.

## E80c and E101 §212 priority review — 0b62a601c / 7ac87cf09

Shared snapshot `c406a7d0e`. E80c R-X3 was independently reconstructed from raw family-judge records and frozen E80 none records, using the exact hash-pinned joins/readouts/packets. Each family headline scorer was reconstructed as in the E80 review; multilingual regex outcomes were independently checked. No once-only worker analysis was invoked. All 518 original items per reader and all3108 ablation records reconcile, with one missing judgment in the full grid.

| Experiment | Rule/check | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E80c | Oracle R-X3 | NOT MET | n_pass_none=n_complete184; falls J106/184=.5760869565, random18/184=.0978260870, PCA178/184=.9673913043 | Same points / NOT MET | 0b62a601c; code7b8433cce | J-minus-random=.4782608696 passes its point threshold; J-minus-PCA=-.3913043478 fails required>=.10. PCA condition is decisive. |
| E80c | Oracle J-minus-random bootstrap | MET (subcondition) | common.stats estimate .4782608695652174, CI[.4074728260869565,.5543478260869565] | CI[.40217391304347827,.548913043478261] | 0b62a601c;7b8433cce | Worker Python-random resampling/order-statistic quantiles reproduce exactly in a separate independent calculation. common.stats uses NumPy RNG/linear quantiles; difference is sampling/quantile convention, not scoring. Both lower bounds>0. |
| E80c | Oracle J-minus-PCA bootstrap | NOT MET (subcondition) | common.stats estimate -.391304347826087, CI[-.46195652173913043,-.32065217391304346] | estimate -.3913043478260869, CI[-.46739130434782605,-.32065217391304346] | 0b62a601c;7b8433cce | Independently reproduced worker interval with its committed convention; both intervals entirely negative. Report “readers depend on high-variance directions, not specifically the J-space” under the registered reporting condition. |
| E80c | Oracle R-X3 falsifier | NOT MET | J fall .5760869565 > random fall+.05=.1478260870 | NOT MET positive rule, no falsifier | 0b62a601c | Separate falsifier checked; failed PCA specificity is not the registered random-ablation falsifier. |
| E80c | NLA exploratory analogue | NOT MET | n218; falls J106/218=.4862385321, random28/218=.1284403670, PCA183/218=.8394495413; differences .3577981651 and -.3532110092 | Same points; NOT MET | 0b62a601c | common.stats CIs J-random[.2798165137614679,.43119266055045874], J-PCA[-.42660550458715596,-.2798165137614679]. Worker intervals reproduced separately; random CI[.2844036697247706,.4357798165137614]. Block44 basis at block42 remains exploratory. |
| E80c | missingness bounds | MET (audit check) | Missing in selected none-pass sets:0/184 Oracle,0/218 NLA under every ablation; all-correct/all-wrong bounds identical to points above | Same BOUNDS.json | 0b62a601c;675bfc01d | Only missing judgment is outside S, so no point/contrast changes under either fill. BOUNDS companion does not replace the original R-X3 analysis. |
| E80c | charged truncation / §212 wrapper | MET (observed execution check) |1 charged length response, USD.0062965, terminal UNPARSEABLE at attempt0; no attempt1/2 directories; original evidence still finish_reason length |1 charged_length_truncation | 6f2fe1a33;6e182a1bf;0b62a601c | Linked request hash to opaque253f1af929960799606ea728a164c2ae: Oracle chain_intermediates048 random_ablated, outside none-pass S. No retry, prompt/route/token-cap change or failure-as-false substitution found. |
| E80c | norm>1.5 reporting | MET (diagnostic recount) |0 flags in all6 reader/ablation cells | Same | 0b62a601c | Recount of sealed norm diagnostics; not an independent GPU regeneration. |
| E80c | 7b8433cc unchanged | MET (code audit) | e80c_analysis.py and score80.py bytes match exact original commit; bounds companion also unchanged from675bfc01 | Original analysis reused | 7b8433cce;675bfc01d | Exact git-blob comparison; original analysis source and scorer were not modified by the truncation/bounds additions. |
| E80c | bounds commit before completed grid | MET (chronology check) |675bfc01d22:33:38 CET < final raw JUDGMENTS mtime22:35:15.376879, by97.376879s | “before grid exists” | 675bfc01d;0b62a601c | This means the completed grid. First resumed cached response was22:33:07.830108,30.169892s before bounds commit; much earlier partial judgments also existed. Do not claim the bounds code predates every individual source response. |
| E101 anomaly | actual hook check | MET (diagnostic check) |504/504 recorded dev hook deltas>0;504/504 post-hook values match supplied BF16 vectors; all6 row/block groups84/84 | Same | 7ac87cf09 | Independently recounted sealed GPU observations, whose observer captures original block output before production patch and next-block input after patch. No new GPU run. |
| E101 anomaly | label / contrast sign | MET (diagnostic check) |252/252 original dev identity/label joins and target sign1-2*label agree; CPU target-signed contrasts match2016/2016 records | Same | 7ac87cf09 | Rejoined original hash-verified bank metadata and CPU key; archived acquisition.py bytes equal the executed/current frozen version. No sign defect found in these checks. |
| E101 anomaly | baseline item agreement | MET (diagnostic check) | Baseline42/84 format_plan,42/84 nesting_depth,0/84 page_range_digit;2016/2016 steered item indicators equal their unsteered indicator across4 doses and2 blocks | Same; zero side crossings | 7ac87cf09 | Computed target side from raw unsteered full pair_logprobs, then compared each item to raw CPU contrasts. Counts alone were not used as a substitute for item-level agreement. |
| E101 anomaly | frozen nesting metric limitation | MET (verification) | All frozen candidate pairs short[2205], long[2205,4891]: strict token prefix | Same limitation | 7ac87cf09;a2bdecaa8 | For summed sequence log probability without an end-of-sequence term, P(long)<=P(short); the short-side preference is structural. This is the fixed registered metric, not evidence that the state is unused. |
| E101 | §212 amendment2 null disposition | NOT EVALUABLE (no behavioural flip on12/14 dose cells); null retained |2 selected Oracle content/plan cells;12 fail the dev dose gate; no identified defect in tested hook/sign/baseline paths | Null stands; no deviation1 rerun | 6e182a1bf;7ac87cf09;a2bdecaa8 | R-F1/R-F2 are explicitly NOT EVALUABLE under §212 clarification4. Remaining two eligible test cells are descriptive, not a relaxed confirmatory R-F1. |
| E101 anomaly | diagnostic-code-before-CPU-output | NOT MET (chronology check only) | First CPU_PER_ITEM/SUMMARY archived mtime22:42:47.849044/22:42:47.849420; source commit f58d60168 is22:44:00 | Report source_commit f58d60168 | f58d60168;7ac87cf09 | Diagnostic registration§21222:27:37 predates CPU work, but the committed code follows first CPU artifacts by72.150956s. GPU hook/baseline outputs22:49:07/22:49:49 follow the code commit. This timing discrepancy does not itself show a hook/sign defect. |

### E80c chronology and wrapper details

E80c original registration `6c07e38a2` committed10:45:07 CET and PCA clarification `8f3cba53b`10:48:44, both before the earliest hash-verified native job12:25:19. Baseline E80 outputs pre-existed by design; E80c registration's before-opening condition is distinct from their generation. Analysis code `7b8433cce`16:18:03 precedes final judged grid and analysis.

§212 `6e182a1bf`22:27:37 registers terminal missingness for charged length truncation and the bounds report. Wrapper `6f2fe1a33`22:32:27 precedes resumed response range22:33:07.830108–22:35:15.333934; full grid mtime22:35:15.376879; result output22:36:36.074727. Bounds commit22:33:38 precedes the completed grid and all analysis outputs. The one cached charged truncation itself was generated16:55:38.270011, before the ruling; its **resumed disposition**, not its original generation, is the affected output of the new stop rule.

The wrapper deep-copies the cached response for control-flow validation, presents finish_reason stop only in memory, records terminal UNPARSEABLE, and stops that record's attempt iterator. The stored response remains length. Its deterministic request hash matches the missing opaque record; the sent model is google/gemini-3.1-flash-lite with max_tokens4096. There is only an E80c_attempt0 directory. The original prompt, route and token cap are preserved; charged length is not routed through the uncharged-error retry branch. This validates the observed execution; no claim of pre-existing source-response generation is made.

Bootstrap comparison: independent common/stats.py uses2000 draws/seed20261028, percentile quantiles on paired rows. The unchanged worker code uses Python random and sorted order-statistic endpoints; a separate independent reproduction of those draws matches its quoted intervals. Both computations give the same rule verdict. Exact per-family and J-fraction R-X4 reproduction is not claimed by this pooled R-X3 review.

### E101 anomaly scope, chronology and null wording

Verified available anomaly seal members, raw archive hashes, every GPU output-seal member, and the archived diagnostic/acquisition source hashes. Original dose-file hash03001cb7 remains unchanged; diagnostic records join only original dev items. The six anomalous row/block hook minima are145.32191467285156 /141.01080322265625 (format44/42),164.542724609375 /158.9335174560547 (nesting44/42),59.23476791381836 /57.107940673828125 (page44/42).

The diagnostic's code review confirms its observers register before the production hook and at the following block's input, measuring actual patch delivery; output norms are instrumentation observations, not recreated tensors in this CPU review. No test identities or new dose choice entered the checks. The null is supported **within these checks**; it is not a proof that every possible implementation issue is absent.

Original diagnostic authority§21222:27:37 predates the report start22:39:09. First CPU artifacts22:42:47 precede the first diagnostic-code commit22:44:00, as flagged. GPU stage22:46:23, hook output22:49:07 and unsteered baseline22:49:49 follow it. The sealed report finishes22:52:28.634284 and publishes in7ac87cf0922:53:27. Amendment2 `a2bdecaa8` commits23:32:01, explicitly **after** the diagnostic finding: it closes the check and preserves the null rather than changing the metric. Precedence against any later E101 test judgment/new-bank judging remains to be checked against actual first-output custody; no such time is asserted here.

Use the amendment's limited null wording: “the steering vectors at alpha<=4 never crossed the decision boundary of the frozen behavioural contrast on12 of14 cells”. This is the row/block dose-gate disposition; the independently item-level zero-crossing result above is specifically for the3 anomalous rows, not a claim that no individual contrast changed sign anywhere in all7 rows. Do not infer “the model does not use the state”. No deviation1 rerun follows this no-defect disposition.

Amendment2 also raises the separate judging ceiling toUSD1000 (flag800), with actual settled spend plus open running-bank caps and release of completed/unused allocations. This supersedes the earlier500 judging ceiling; Track Q GPU900/all-track GPU2500 remain separate. The conditional unparking note in §211 amendment1 is recorded, with CORE pre-emption intact; Guiv's instruction to leave parked work pending is not replaced by an unsolicited review of parked outcomes.

Follow-up seal check: the published E80c raw-grid hash equals the independently read pinned raw grid, and every original analysis-seal member verifies. E101 R-F3 is also NOT EVALUABLE because its registered conjunction requires R-F1 and R-F2 MET; both are expressly NOT EVALUABLE under §212 clarification4.

## Scheduled CORE pass — 2026-10-28 23:52 CET

Shared snapshot `43d212d65`. E101's two-cell raw judged grid is now sealed and published (336 records); the receipt explicitly says JUDGING_COMPLETE_NO_ANALYSIS, scientific_analysis_calls0. No sealed descriptive analysis exists on this snapshot, so its numerical review remains PENDING under the engagement rule. E80c/E101 null findings are unchanged; other CORE outcomes and parked work were not reanalysed.

| Experiment | Rule/check | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E101 | dose commit before first test output | MET (chronology check) | Dose4343109e2 at18:21:27 CET precedes earliest observed test timing output22:42:19.346141 CET by4h20m52.346141s | Exact dose hash03001cb7 bound in every test/timing seal | 4343109e2;43d212d65 | Included earlier timing and NO_FIT attempts, not merely the two retained complete acquisitions. This closes the previously pending pre-test ordering check for the inspected custody history. |
| E101 | retained complete test custody | MET (seal check) | fact_recall first23:19:56.608127 CET; language_plan first23:22:25.086067; output seals90e25ffa /4e3cf7ba | Both cells SEALED_COMPLETE | 43d212d65; committed INTEGRATOR_TEST_BINDING | Verified exact output-seal hashes and the first-output member hashes. Both carry exact frozen dose hash03001cb7. |
| E101 | sealed judged grid | MET (artifact check) |336 terminal judgments; exact published judgment seal1ce64669, blind seal63e8e36e and private mapbe86ba53 chain |336, judged complete, no analysis | 43d212d65 | Every judgment-seal member and private-map binding verifies. Statistical outputs are not inferred from a transport completion receipt. |
| E101 | descriptive test S / B / steered-random | PENDING | No sealed descriptive analysis yet | scientific_analysis_calls0 | 43d212d65 | Move on until analysis is sealed; do not rerun a worker once-only entry point or treat raw-grid completion as final numerical sign-off. |
| E101 | §212 and amendment2 stage ordering | MET (chronology check) | §2126e182a1bf22:27:37 < earliest test timing22:42:19; amendment2a2bdecaa823:32:01 < judging start23:39:03.118093 | Same run receipt stages | 6e182a1bf;a2bdecaa8;43d212d65 | Amendment2 is after retained test acquisition, but its specified affected boundary is test judgments/new-bank judging; no retroactive new scoring rule is inferred. |

Observed complete custody history, all Oct28 CET: testtiming fact22:42:19.346141 /language22:42:56.399581; first NO_FIT test fact22:55:55.794564 /language23:02:25.937168; testtiming2 fact23:10:34.427579 /language23:12:26.568096; retained test2 fact23:19:56.608127 /language23:22:25.086067. All seals bind the same dose-file hash. The first pair and timing outputs are excluded from final descriptive science as explicitly recorded in the committed binding; they are retained here solely to ensure the chronological boundary is not silently moved to the final successful run.

Judging started23:39:03.118093 and completed23:43:19.793634 CET, after amendment2. R-F1/R-F2/R-F3 remain NOT EVALUABLE; any forthcoming two-cell result is descriptive. Text-only baseline remains explicitly unavailable in the bound descriptive-input metadata, rather than assigned an invented rate.

## E101 sealed descriptive-result review — 0bd1822f6

This review proceeds under Guiv's standing R-Q scope and the published sealed artifacts. No interpretation from the result-notification message was used as rule authority. Result publication `0bd1822f6`, analysis seal `ad820c3f25acab98b70dd05881b341b4c658182ca2daa3e57b230a421742f4c1`; all result/binding/figure hashes verify. The once-only worker analysis was not rerun.

Independently rejoined the336 terminal judgments to both complete test2 acquisitions, verifying private-map/blind/judgment seal chains and every acquisition input/output member. The thin private join agrees exactly with recomputed acquisition identity, item,row,reader,condition,alpha,target,property,values and native text for336/336 records. All588 test targets were checked against original hash-verified bank metadata; split, original label, other-value target and contrast sign agree. Full frozen continuation log probabilities determine steered/random behaviour flips; no test-result selection or replacement is introduced.

Cohort: original84 item IDs per row, sorted; only the **steered** flip indicator selects the same paired cohort for both conditions, as clarification3 requires. Scores are target-only+1, stated-only−1, both/property/exhibits/silent0, true UNPARSEABLE missing. The paired bootstrap resamples original84 item indices, retains the cohort and each condition's separate missing mask, and takes the difference of the separately observed means. All statistics below use common/stats.py,2000 draws,seed20261027; every worker point and CI endpoint reproduces within1e-12.

| Experiment | Rule/check | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E101 | fact_recall descriptive B and conditional S | VERIFIED (descriptive, no rule verdict) | B79/84=.9404761905; steered S4/78=.0512820513, random S−37/79=−.4683544304; difference .5196364817 | Identical | 0bd1822f6 | All bootstrap intervals match; table below. Random own B=0/84, but its S is correctly evaluated on79 steered-flipped IDs. |
| E101 | language_plan descriptive B and conditional S | VERIFIED (descriptive, no rule verdict) | B71/84=.8452380952; steered S43/52=.8269230769, random S−18/61=−.2950819672; difference1.1220050441 | Identical | 0bd1822f6 | All bootstrap intervals match. Random own B35/84=.4166666667; that is not substituted for the paired cohort. |
| E101 | actual missingness, fact_recall | MET (audit check) | On flipped cohort steered1/79 truly UNPARSEABLE, random0/79; retained78/79 and79/79;5 non-flipped excluded | Summary distinguishes these counts | 0bd1822f6 | Generic masked S fields say UNPARSEABLE6 and5 because they also count5 non-flipped exclusions. Those fields must not be reported as actual failed-judgment counts. |
| E101 | actual missingness, language_plan | MET (audit check) | On flipped cohort steered19/71 truly UNPARSEABLE, random10/71; retained52/71 and61/71;13 non-flipped excluded | Summary distinguishes these counts | 0bd1822f6 | Generic masked S fields say UNPARSEABLE32 and23 = exclusions+real missing. On full84, actual missing19 steered/12 random. No score discrepancy; field-label interpretation matters. |
| E101 | norm flags | MET (reporting check) | fact flags0/84 steered and0/84 random, maxima1.3443898632/1.4092759765; language flags66/84 and84/84, maxima2.0528262601/2.0455012398 | Same sealed per-item norms | 0bd1822f6 | Recounted from sealed input norm metadata; >1.5 is flagged without exclusion. Language results are at alpha4 with substantial distribution shift. |
| E101 | R-F1/R-F2/R-F3 and both falsifiers | NOT EVALUABLE |2 of14 selected dose cells; these two tests descriptive only | NOT EVALUABLE for both readers and every rule/falsifier | §2126e182a1bf;0bd1822f6 | Registered confirmatory scope is not relaxed because language_plan shows high conditional S. No NLA row or active-bookkeeping test is present. |
| E101 | scientific adapter unchanged | MET (code audit) | e101.py,common.py,wmech2/core.py all byte-identical to f6ba5964f | scientific_adapter_commit f6ba5964f | f6ba5964f;4170e45f9 | The added custody bridge enriches the thinner join only after exact identity and all-overlapping-field checks; it does not alter the scientific implementation. Independent raw join confirms those checks. |
| E101 | code-before-first-analysis-output | MET (chronology check) | Scientific commit Oct28 23:39:50; bridge23:56:07; first RESULTS23:56:27.268056 CET | Guard binds4170e45f9; COMPLETE_ONCE | f6ba5964f;4170e45f9;0bd1822f6 | Bridge lead20.268056s. Seal completed23:56:41.469824. This is analysis-output ordering, separate from the already verified dose-before-test check. |
| E101 | native/text baseline completeness | PENDING / not provided | No baseline rates bound to this descriptive analysis | NOT PROVIDED; does not wait for text baseline | 0bd1822f6 | Absent baseline fields do not mean84 actually failed judge responses. No text-reconstruction conclusion or invented baseline rate is endorsed. |

| Row | Statistic | Independent estimate / bootstrap95 | Worker comparison |
|---|---|---|---|
| fact_recall | B | 0.9404761904761905; [0.8809523809523809,0.9880952380952381] | Matches all3 values within1e-12. |
| fact_recall | B_random | 0; [0,0] | Matches all3 values within1e-12. |
| fact_recall | S_steered | 0.05128205128205128; [0.012345679012345678,0.1038961038961039] | Matches all3 values within1e-12. |
| fact_recall | S_random | -0.46835443037974683; [-0.5844155844155844,-0.35437243715457334] | Matches all3 values within1e-12. |
| fact_recall | difference | 0.5196364816617981; [0.4065572737832898,0.6403769923769922] | Matches all3 values within1e-12. |
| fact_recall | S_all_steered | 0.04819277108433735; [0.011904761904761904,0.0963855421686747] | Matches all3 values within1e-12. |
| fact_recall | S_all_random | -0.5; [-0.6071428571428571,-0.39285714285714285] | Matches all3 values within1e-12. |
| language_plan | B | 0.8452380952380952; [0.7619047619047619,0.9166666666666666] | Matches all3 values within1e-12. |
| language_plan | B_random | 0.4166666666666667; [0.32142857142857145,0.5238095238095238] | Matches all3 values within1e-12. |
| language_plan | S_steered | 0.8269230769230769; [0.6833333333333333,0.9444444444444444] | Matches all3 values within1e-12. |
| language_plan | S_random | -0.29508196721311475; [-0.4918032786885246,-0.08771929824561403] | Matches all3 values within1e-12. |
| language_plan | difference | 1.1220050441361917; [0.8803176884010102,1.3428710358480258] | Matches all3 values within1e-12. |
| language_plan | S_all_steered | 0.8461538461538461; [0.728538961038961,0.9420289855072463] | Matches all3 values within1e-12. |
| language_plan | S_all_random | -0.3055555555555556; [-0.47761194029850745,-0.1215810810810813] | Matches all3 values within1e-12. |

Supplemental Wilson checks (not replacement intervals): B79/84 CI[.8681156389946401,.974309817736567]; B71/84 CI[.753011640086769,.9072677719457987]. Reported B bootstrap intervals above reproduce the worker's registered convention.

Interpretation limits: conditional S excludes actual missing judgments. As a reviewer-only point sensitivity, treating every missing flipped-item judgment as wrong/correct gives fact steered S in[3/79,5/79], language steered in[24/71,62/71]; no changed scientific verdict follows. The full steered-flipped item cohort is preserved for random; the two means can have different parseable denominators, and their signed-score difference may exceed1 because S ranges from−1 to1.

Dated clarifications: `227290405`, actual Oct28 16:31:36 CET, defines the paired **steered-flipped** cohort and reporting all-item/random-behaviour rates; it predates earliest test timing22:42:19.346141. Earlier dose-selection clarifications and exact final dose commit were checked in prior entries and remain unchanged. §21222:27:37 authorizes descriptive two-cell tests; amendment2 `a2bdecaa8`23:32:01 predates judging start23:39:03.118093 and keeps the no-defect/null disposition. No new rule or metric was inferred from an integrator statement.

This closes the numerical review of the published descriptive result. Confirmatory rules/falsifiers remain NOT EVALUABLE; missingness, norms and absent text baseline must stay alongside the two descriptive points.

## Explicit scope addition — §213 E104

Guiv explicitly adds E104 and prioritizes the hook, control-matching and code-before-output checks. Registration `5e075c6af` has authoritative commit time **2026-10-29 00:12:34 CET** (heading00:20 nominal). Inspected shared snapshot `aae2d6b89` contains the registration but no E104 implementation, adapter, frozen dose selection, judged grid or output seal. All scientific and implementation checks are PENDING; absence of a published output is not proof of pre-output ordering.

| Experiment | Rule/check | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E104 | arm U hook excludes read token at every block | PENDING | No source/observations published | Unavailable | 5e075c6af | Check writes at block40 only, exactly8 indices [read_index-8,read_index), never read_index; no residual E101 same-site hook at40/44 or any other block. Capture at44/read token must be passive. Natural model propagation into the read token is expected and is distinct from hook assignment. |
| E104 | U target/random displacement matching | PENDING | No source/vectors published | Unavailable | 5e075c6af | Independently compare structured and random delta norms per item and each of8 patched positions, at same alpha/site. Verify unit directions and the same dev raw-d norm factor; seed20261029. Equal displacement norm does not require equal resulting residual norm, which must still be reported. |
| E104 | N target/random renormalisation | PENDING | No source/vectors published | Unavailable | 5e075c6af | Recompute hprime=norm(h)*(h+alpha*norm(d)*sigma*u)/norm(h+alpha*norm(d)*sigma*u) separately for structured and random u. Both must preserve the same item's original norm; compare before/after values and indices, including executed dtype tolerance. |
| E104 | committed adapter and synthetic checks before output | PENDING | No E104 adapter or test-result artifact on shared branch | Unavailable | 5e075c6af | §213 says f6ba5964f extended with synthetic tests before any output. Compare actual source commit/test evidence with FIRST E104 real-item dev/timing/test output, not only final analysis or completed grid. No once-only worker entry point will be rerun. |
| E104 | dev-only directions/doses | PENDING | Same84 dev items per row; U doses[.5,1,2,4,8], N[.5,1,2,4]; threshold>=59/84 | Unavailable | 5e075c6af | Verify smallest qualifying dose from raw dev logits, same sealed identities and frozen behaviour contrast. Block40 d must be dev-only, from existing sealed captures or one new dev capture. Retain dev/test split and frozen test dose choices. |
| E104 | achieved n and cohort | PENDING |84 test items per eligible row/arm, steered/random, Oracle; common steered-flipped paired cohort | Unavailable | 5e075c6af | Reconstruct target/behaviour/missingness independently; use common/stats.py item bootstrap. No qualifying dose means NOT EVALUABLE for that cell. |
| E104 | R-U1 | PENDING | No sealed judged test grid | Unavailable | 5e075c6af | On>=1 eligible U row: paired S_target steered-random>=.30, lower bound>0. No row reaches alpha-star => NOT EVALUABLE. |
| E104 | R-N1 | PENDING | No sealed judged test grid | Unavailable | 5e075c6af | Same threshold on>=1 eligible N row. No post-hoc pooling across arms or relaxation of the dev gate. |
| E104 | shared falsifier | PENDING | No eligible test-grid estimates | Unavailable | 5e075c6af | Difference<=.10 with upper bound<.30 on every eligible cell of both arms. Do not count an empty eligible set as evidence for the falsifier; quote/flag any unresolved eligibility ambiguity rather than infer a new rule. |
| E104 | reporting and chronology | PENDING | No first-output custody, norms, B or actual failed-judgment counts yet | Unavailable | 5e075c6af | Report those fields per item/arm; retain the E101 signed-score and actual-missingness distinction. Apply registration and every subsequent dated clarification against actual first affected output. |

E104 is CORE and pre-empts parked work, with arm N dev dose acquisition first, then tests, and arm U's larger dose8 confined to U. Its registered caps are8 GPU-h total and judgingUSD5 under the current separate ledgers; launch deadline Thu24:00 CET. R-Q remains a reviewer and initiates no acquisition. The automation scope is updated to include these checks as source/seals arrive. Earlier E101 descriptive results and all NOT EVALUABLE rule dispositions remain intact pending E104 evidence.

## E87 clarification3 review — reporting addition and control-gate discrepancy

Shared snapshot `c1daceafb`. §200 clarification3 is commit `4c3e9dca80650e4c8eaa189939f24e84849ea9ae`, authoritative time **2026-10-29 00:22:26 CET** (heading00:35 nominal). The commit only appends the reporting paragraph; no earlier registration text is changed. No completed E87 grouped judging seal is published on this snapshot, so pre-seal ordering remains PENDING rather than inferred from the heading.

| Experiment | Rule/check | Verdict | Independent number | Worker number | Commit checked | Discrepancy / evidence |
|---|---|---|---|---|---|---|
| E87 | clarification3 changes R-L1 registration? | MET (unchanged-rule check) | Original R-L1 paragraph is byte-identical before/after4c3e9dca8; no E87 analysis-code diff in that commit | Reporting only / no rule change | 4c3e9dca8 | Exact git-blob comparison; appended depth-profile/classification is descriptive and supplies no new R-L1 threshold. |
| E87 | clarification3 before grouped judging seal | PENDING | Known commit00:22:26 CET; grouped terminal/seal timestamp unavailable | Heading says before judging seals | 4c3e9dca8;c1daceafb | No published grouped judgment/result seal located; compare actual first terminal/seal custody once available. Do not declare ordering MET from a future-tense claim. |
| E87 | registered R-L1 controls/thresholds | PENDING (scientific result) | On>=6/8 missed rows D=S_max(real)-S_max(placebo)<=.10, BOTH controls D>=.30; if either fails, NOT EVALUABLE; falsifier D>=.20 on>=4/8 | No sealed outcome yet | Original§200 and clarifications1–2;4c3e9dca8 | Rule remains unchanged and Oracle-only. Real/random-only placebo structure and all7 registered layers remain required. |
| E87 | current adapter mandatory control gate | NOT MET (implementation check) | Synthetic D=.25 on all8 missed rows, controls0/0: controls_ok=false, but adapter returns FALSIFIED | FALSIFIED (single-site blind spot) | e87_analysis.py commit4bd32a3a4,2026-10-28 23:54:23 CET | Pure verdict() counterexample only, no real analysis run. Code checks high>=4 before controls_ok, contrary to “If either control fails, R-L1 is NOT EVALUABLE” and Guiv's explicit review instruction. Pre-existing discrepancy, not introduced by clarification3. |
| E87 | profile layers versus rule layers | MET (scope separation) | Reporting list{20,28,36,44,52,60}; R-L1 still uses{20,28,36,44,52,56,60} under clarification1 | Current adapter ORACLE_LAYERS includes56 | 4c3e9dca8;clarification1 | Clarification3's figure list omits56; it does not remove56 from registered S_max or change the matching placebo grid. |
| E87 | descriptive four-way coverage | NOT EVALUABLE (ambiguous for uncovered profiles) | No sealed profile classified yet | Persistent/Consumed/Late/Never definitions | 4c3e9dca8 | “Persistent: S>=.20 at block44 and at one or more earlier layers” leaves a44-only positive profile uncovered; an earlier+later positive profile with44 negative also fits none of the stated categories. Do not invent a category or priority; mark affected rows NOT EVALUABLE(ambiguous) and quote applicable words if such profiles occur. This does not affect R-L1. |

The counterexample calls only the pure decision function on synthetic numbers and writes no test/source/results file; the worker once-only analysis entry point was not invoked. In R-Q's independent review, the mandatory positive-control gate takes precedence: either control failing means R-L1 NOT EVALUABLE, even if the raw missed-row contrasts numerically meet the separate falsifier threshold. The adapter must not be treated as the definition of the rule.

Reporting additions to check after grouped judging seals: layerwise S and item-bootstrap CIs plus placebo profile, first-mention position, the literal descriptive classifications where defined, and shared E72 blocks36/40 marked off-distribution. Classification references the E76 judged placebo floor; no extra compute or changed threshold is inferred. Preserve the seven-layer registered rule despite the six-layer reporting list.

## E87 requested gate-fix chronology follow-up

Guiv directly requested verification that the forthcoming control-gate-first correction and synthetic test are committed before the grouped-judging seal. Shared snapshot `488330e3c`, fetched twice in this pass: the correction is not yet published and no grouped E87 judging seal is present. Commit `47034001d` (2026-10-29 00:29:02 CET) adds reporting code/test only; it does not change the decision function or add the failed-control/falsifier regression test. The earlier implementation finding remains historical evidence, not a claim that a forthcoming fix has failed.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E87 | Gate-fix implementation and regression test | PENDING (fix unpublished) | Current pure verdict counterexample: 8 missed-row D=.25, both control D=0 => FALSIFIED with controls_ok=false | Guiv reports correction in progress, control gate first plus synthetic test | 488330e3c;47034001d;4bd32a3a4 | No new real analysis or once-only entry point run; verify corrected function returns NOT EVALUABLE for either failed control, including when >=4 rows meet falsifier. |
| E87 | Fix commit before grouped-judging seal | PENDING | Neither correction commit nor grouped terminal/seal timestamp published | Correction intended before seal | 488330e3c | Compare authoritative fix commit time with actual grouped seal custody when both are published; do not infer chronology from intent or commit subject. Clarification3 registration remains4c3e9dca8 at00:22:26 CET; R-L1 unchanged. |

## Scheduled pass — E87 gate correction, E104 source, E100 sealed a/b

Shared snapshot `8eafc3bc9` (2026-10-29). Only published artifacts and exact seal-bound local raw records were read; worker chats and rule interpretations were not consulted. No once-only worker entry point, GPU launch or judging run was invoked. Existing unchanged audits and parked experiments were not repeated. E88 items5–6 and judged E76 floor comparisons remain PENDING without a newly published terminal analysis.

### E87 correction now independently verified

Fix commit `5b22f8aa8`, authoritative **2026-10-29 00:38:15 CET**, changes the decision function and docstring to put the mandatory positive-control gate first, then the falsifier, then the MET threshold. It adds `test_control_gate_precedes_falsifier`. R-Q ran that committed synthetic test directly (pure grid/stat/verdict functions, no file-writing test or analysis entry point) and independently exercised each failed-control combination at eight missed-row D=.25. This supersedes the implementation defect in4bd32a3a4; it does not erase the historical finding.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E87 | Mandatory control gate implementation | MET (source/synthetic check) | Controls(0,0),(.30,0),(0,.30) all return NOT EVALUABLE despite8/8 missed rows meeting falsifier; controls(.30,.30) return FALSIFIED | Control gate first | 5b22f8aa8 | Committed regression test also passes for4 falsifier rows and for7-row sensitivity; prior order discrepancy resolved. Scientific outcome remains PENDING. |
| E87 | Fix before grouped-judging seal | PENDING | Fix commit00:38:15 CET verified; grouped seal timestamp unavailable | Intended pre-seal correction | 5b22f8aa8;8eafc3bc9 | No grouped E87 judging/result seal published here; do not infer chronology from the commit subject. Compare actual seal custody when published. |
| E87 | Reporting clarification3 before grouped seal / unchanged R-L1 | PENDING (ordering); MET (unchanged rule) | Registration4c3e9dca8 at00:22:26 CET; original rule byte-identical,7-layer S_max still includes56 | Reporting only | 4c3e9dca8;5b22f8aa8 | No new BRIEF rule amendment in this pass. Reporting categories and uncovered-profile ambiguity remain as documented above. |

### E104 committed implementation and sealed N-dev inputs

Acquisition extension `9e37f3504`, authoritative **2026-10-29 00:50:02 CET**, follows §213 registration5e075c6af (00:12:34 CET). Verified all134 source-seal members against current bytes, the exact delivered source archive SHA, both N-dev input seals and input archives, and the CPU-only key hash. Published delivery explicitly has GPU_calls=0 and U block40 capture pending. No real E104 acquisition output seal is published; source correctness is not an executed GPU norm/position audit.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E104 | U hook excludes read token at every block | MET (source check); PENDING (executed observations) | Only mutating hook isblock40; sites=range(read_index-8,read_index), exactly8; block44 hook only captures; finally removes all installed hooks, including crash paths | Eight preceding positions, passive read44 | 9e37f3504 | E101 behaviour receives explicit alternate forward for prefix/continuations, bypassing its same-site patched_forward; Runtime.subject adds no intervention hook. Pure positions tests pass at read indices8,9,30; short prefix7 rejected. Real tensor snapshots pending. |
| E104 | U random displacement norm matching | MET (composition source); PENDING (executed dtype tolerance) | Both conditions use alpha*raw_dev_norm*(1-2label)*unit direction, same delta at each of8sites; seeded unit Gaussian SeedSequence([20261029,40]) | Same alpha/site/displacement | 9e37f3504 | U direction capture/vector seal not yet completed. Actual post-cast displacement equality must be checked from observed tensors; residual-norm equality is not the control requirement. |
| E104 | N structured/random renormalisation | MET (source and sealed input check); PENDING (executed norm tolerance) | Unconditional armN formula rescales each live proposed vector to its original item's norm before model-dtype cast, for BOTH conditions;1344 dev input cells, maximum paired displacement-norm relative mismatch1.2779654357110216e-9 |28 synthetic tests reported PASS | 9e37f3504 |84 distinct dev items per row,672cells each; original read position/block44 checked. Torch unavailable locally, so author-reported tensor tests were inspected but not independently rerun; no BF16 norm-preservation claim from input-only check. |
| E104 | Adapter and synthetic tests before FIRST real dev/timing/test output | PENDING | Committed source00:50:02 CET; no first real-output timestamp published | CPU-only delivery, GPU_calls0 | 9e37f3504 | Source/test existence verified; compare with first real output including capture/timing or discarded attempts when sealed, not merely final grid. Analysis contracta2afc8b84 remains separately precommitted. |
| E104 | R-U1 / R-N1 / shared falsifier | PENDING | No qualified dose, test grid or judgment result yet | Not run | 9e37f3504;8eafc3bc9 | Dev-only smallest qualifying dose requires59/84; N grid.5/1/2/4, U additionally8. Empty eligibility cannot establish falsifier. Norm flags/missingness await real records. |

### E100 a/b: independent raw-grid recomputation

Publication `b8e2c8202`; analysis seal SHA `76b156f055567cb168b2cfd40ec6bcc65aa21d2aa18fd1d97d533ad5fa86d2d1`; judgment seal SHA `879b3bba8d71737546c2cb89e500cc39632ee90cdf3cb24050a107af6debee83`. Verified result/member, both acquisition-shard, judgment, blind and target-seal hashes. Rejoined all6720 private identities/texts/cell metadata to sealed acquisition records and all672 targets to original sealed test metadata and donor identities; E57 values match the donor family's original judge plan. Every row has84items ×5conditions ×2readers =840cells,6720 total, with no absent scheduled cell. Explicit UNPARSEABLE judgments=184; these stay missing with separate condition denominators. Norm flags>1.5=0/6720. NLA remains exploratory (read42/block44basis).

R-Q independently scored the raw category/value records and used `common.stats.bootstrap_ci` on paired item-index resampling:2000draws, seed20261027, common within-row draws over both readers/allconditions, the registered RNG stream advanced across rows, and separate arm missing masks. **All112 cell/contrast point estimates and CI endpoints match the sealed analysis** within1e-12. No worker analysis function was called. The single privacy-redacted readout is indent_level/Oracle/perp_J_swap; independently replacing it by missing gives S=.024096385542168676, CI[-.023809523809523808,.07228915662650602], matching sensitivity output. Active rule verdicts are unchanged.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E100 | R-PC | MET |5/5 reported rows pass S>=.50 and lower>.30; format.9523809524[.880952381,1], language_plan.6184210526[.465753425,.753424658], tense.6538461538[.545454545,.7625], language_continuation.6103896104[.473684211,.746835443], fact.7380952381[.642857143,.821428571] | MET5/5 | e8900a827;b8e2c8202 | All point/CIs reproduced; gate passes independently. Row order is format_plan,language_plan,tense_implicit,language_continuation,fact_recall. |
| E100 | R-PC falsifier | NOT MET |0/5 reported rows S<.20, requires>=3 | NOT MET0/5 | e8900a827;b8e2c8202 | No discrepancy; subspace rules evaluable under positive-control gate. |
| E100 | R-C3 | NOT MET |2/5 pass, requires>=3: language_plan J=.4871794872,J-R=.9808503733 CI[.7334529321,1.2087677846]; language_continuation J=.5243902439,J-R=1.1169828365 CI[.9555243388,1.2738675958] | NOT MET2/5 | e8900a827;b8e2c8202 | Other J means format-.2023809524,tense-.5875,fact.0595238095 fail>=.30 despite some large J-R contrasts. All112 primary CIs match, including exploratory NLA. |
| E100 | H-C3b J versus complement on R-C3 rows | MET (descriptive row condition only) |2/2 R-C3-passing rows exceed.20: language_plan J-perp=.9302174619,language_continuation=.9811803674 | Both true, DESCRIPTIVE | e8900a827;b8e2c8202 | No promotion to overall R-C3 MET. No discrepancy. |
| E100 | H-C3b both-components condition | NOT MET (descriptive) |2/5 perp means>=.30: format.3214285714,tense.4871794872; language_plan-.4430379747,language_continuation-.4567901235,fact-.1309523810 | NOT MET2/5 | e8900a827;b8e2c8202 | Requires>=3; no both-components claim. |
| E100 | c/d,R-C4,R-D1,H-T,H-U | WITHDRAWN | No active c/d computation; only transplant and four subspace-swap conditions in raw grid | WITHDRAWN | 69f8c08e4;b8e2c8202 | E79 sealed estimates joined historically, not recomputed. E79 Arm A null is stated first in results/figure. |
| E100 | Strong-B / Strong-C implication | NOT MET / NOT EVALUABLE from current R-Q evidence | R-C3 NOT MET blocks Strong-B; E101 R-F1 NOT EVALUABLE cannot support Strong-C | No new strong branch claimed here | §207 addenda; b8e2c8202 | Other-reviewer E81 prerequisite not taken over. R-PC alone cannot establish either strong claim. |

#### E100 dated registration/amendment ordering and remaining provenance limits

All times below are actual git commit times, CET Oct28; heading times are nominal. Earliest located retained reported-shard job mtime=**17:02:51**, missed-shard=**19:52:21**; all listed amendments precede those outputs. The published two-shard execution binding does not inventory every possible earlier timing/discarded attempt; complete first-ever-output coverage therefore remains unverified, rather than inferred from the final grid. No new scientific threshold was introduced after seeing these outputs.

- Original §208 and §207 addendum: `f425a5e2a` **15:51:38** — before both located shard outputs.
- §208 clarification1 (dev J-fraction precheck; reported rows only; optional upstream; transplant gate): `d406a695f` **15:52:30** — before both. Full independent dev J-fraction/capture reconstruction remains outstanding; active rule numbers above do not depend on silently inventing it.
- §208 clarification2 (all84 E56 test items; original value-token mapping for later-withdrawn token arm): `fd07c12a9` **15:58:19** — before both; achieved84/row verified against original sources.
- §208 deviation1 (withdraw c/d and four rules) and §207 addendum2 (Strong-C): `69f8c08e4` **16:05:05** — before both.
- Scientific a/b analysis adapter/targets `e8900a827` **16:35:47** — every file in projects/g_agreement/e100_analysis byte-identical now; precedes located first readout17:02:51 and judging START **23:56:51.056465**. Original runner extension256ae6cfe was committed16:27:20. Exact first judgment-opening timestamp is not separately supplied; source precedes the entire located judgment run.
- Analysis seal records execution HEAD `ab783250b` (Oct29 01:14:42), with unchanged e8900a827 science. First RESULTS file **Oct29 01:15:49.420537**, seal **01:16:03.892047**; publicationb8e2c8202 **01:16:52**. Execution commit precedes first analysis artifact; no discrepancy in the112 independent statistics.

## §217 standing operational rules adopted — 2026-10-29T02:52:05+01:00

Guiv directly instructed immediate application. BRIEF commit068236911, authoritative2026-10-29 02:48:01 CET (heading03:10 nominal), changes operational procedure only. R-Q's acknowledged request inbox and application log are results/g_agreement/reviews/R-Q/HANDOFF.md. Direct Guiv authorization expands the prior review-only write scope to that HANDOFF for coordination; source,scientific results and BRIEF remain untouched. Existing automation now checks HANDOFF/new scoped analysis seals every30minutes, retaining the Fri30 Oct06:00CET stop. Newly delivered seal locators trigger review on arrival rather than waiting for the older two-hour schedule; no once-only operator entry point is replayed. Initial addressed-entry scan found no pending request; no new scientific verdict in this operational update.

| Experiment | Rule/check | Verdict | R-Q evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| Track Q | §217 operational adoption | MET (workflow application) | Owner inbox established, addressed entries checked,30-minute existing automation updated; original science unchanged | Standing operational rules | 068236911;355322598 | Future restart/import/cap/judging/watcher claims require their own timestamped evidence; adoption alone does not certify any launch or analysis. |

### §220 E95 dependency on E87 — registration locator

Commit9c56f1a54, authoritative2026-10-29 03:19:02 CET (heading03:55 nominal), conditions E95 reopening on at least2 consumed/late E87 missed-row classifications or E87 R-L1 NOT MET. This changes no E87 R-L1 or classification definition and does not transfer E95 rule ownership to R-Q. No E87 grouped seal is published on snapshotc10894fb9.

| E87 | §220 dependency registration before grouped seal | PENDING | Known actual commit03:19:02 CET; grouped seal absent | Registered before E87 judging seals | 9c56f1a54;c10894fb9 | Compare actual commit with grouped terminal/seal custody on arrival; preserve literal gate-first E87 verdict and earlier classification ambiguity, without inventing an E95 reopening outcome. |

### E100 outstanding J-fraction precheck independently closed

At shared6c8d5d92e, independently verified vector sealdd1ff8dc2ec742e001d8d0e59b700b33fa904680d420d9fb9350088f752317b0 and all its member hashes, each original bank metadata hash, and each dev capture seal/activation-array/order hash. Reconstructed all8 raw directions from the original84dev items per row (42/class), using mean(label1)-mean(label0). Every component equals the sealed raw_d array exactly (max absolute error0). Original dev identities, splits and row labels were rejoined without fitting any new probe or using test records. Q_J is the exact float64 conversion/orientation of the original pinned basis; max orthogonality error8.0303128591e-9. Evaluated ||Q_J(Q_J^T d)||/||d|| and independently cross-checked with explicit einsum reductions (no BLAS path): results below match FINAL_ROWS.json within2e-16. Chance=sqrt(384/5120)=.27386127875258304. This closes the J-fraction/capture reconstruction gap recorded in the prior E100 review; first-ever timing/discarded-output inventory remains outstanding. Original vector publicationc7f7e53aa is16:15:08 CET Oct28, after clarification1d406a695f15:52:30 and before earliest located retained readout17:02:51. No reader result or scientific rule changes.

| Experiment | Rule/check | Verdict | R-Q number | Worker number | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E100 | §208 clarification1 J-fraction / nesting_depth | MET (descriptive precheck) |.32257353489808377 |.32257353489808377 | c7f7e53aa;dd1ff8dc seal;b8e2c8202 |84dev, raw d exact; not a reader-rule MET. |
| E100 | §208 clarification1 J-fraction / indent_level | MET (descriptive precheck) |.22732204874645034 |.22732204874645034 | c7f7e53aa;dd1ff8dc seal | No discrepancy. |
| E100 | §208 clarification1 J-fraction / page_range_digit | MET (descriptive precheck) |.26727036666183457 |.26727036666183457 | c7f7e53aa;dd1ff8dc seal | No discrepancy. |
| E100 | §208 clarification1 J-fraction / format_plan | MET (descriptive precheck) |.408097397241765 |.408097397241765 | c7f7e53aa;dd1ff8dc seal | No discrepancy. |
| E100 | §208 clarification1 J-fraction / language_plan | MET (descriptive precheck) |.4243932526765621 |.4243932526765621 | c7f7e53aa;dd1ff8dc seal | No discrepancy. |
| E100 | §208 clarification1 J-fraction / tense_implicit | MET (descriptive precheck) |.33932973108130904 |.33932973108130904 | c7f7e53aa;dd1ff8dc seal | No discrepancy. |
| E100 | §208 clarification1 J-fraction / language_continuation | MET (descriptive precheck) |.36100901259369694 |.36100901259369694 | c7f7e53aa;dd1ff8dc seal | No discrepancy. |
| E100 | §208 clarification1 J-fraction / fact_recall | MET (descriptive precheck) |.35030031614090085 |.35030031614090085 | c7f7e53aa;dd1ff8dc seal | No discrepancy. |

### E104 Arm U d40 vector arrival independently reviewed

Sharedffd3cc5e3; publicationf95dcff93 **2026-10-29 03:58:02 CET**. Vector seal6a905cbfe83f0c3db6a3ad376490052eeab638a83362c799a655e4b35a3a8e9c binds capture seald365986aa2bb08233c6e9d1e0392adab4658574358633df4b3a9ee3af625b608 and frozen dev input40d60ff34c3b8ca88a7307eb726cdec5a5e0118cc79720add03542d75c9283e7. Verified all vector/capture/input member hashes plus CPU_BINDING/PRIVATE hashes from the registered request. All168 opaque identities, token sequences, read positions, original source IDs/labels/rows and dev splits match the original sealed E56/E59 metadata; capture order matches exactly, acts shape168x5120 finite. No test item enters either fitted direction. Reconstructed mean(label1)-mean(label0), sorted original IDs, float64 means, and unit vectors independently; all components are byte-value equal to the published arrays. No worker fitter/capture/once-only entry point was rerun.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E104 | U fact_recall dev-only d40 | MET (input/provenance check) |84original dev,42/class; raw norm22.501645515373315; raw/unit arrays exact |22.501645515373315, COMPLETE | f95dcff93;6a905cbf seal | No discrepancy; actual block40 capture, not substituted42/44. Scientific R-U1 still PENDING. |
| E104 | U language_plan dev-only d40 | MET (input/provenance check) |84original dev,42/class; raw norm28.94204435830129; raw/unit arrays exact |28.94204435830129, COMPLETE | f95dcff93;6a905cbf seal | No discrepancy. |
| E104 | U random direction and scale recipe | MET (input check) | SeedSequence([20261029,40]) normalized standard Gaussian5120 exactly equals random40.npy; norm1 |norm1, frozen recipe | afbc5eee1;f95dcff93 | Confirms direction provenance; actual per-position post-cast displacement matching awaits intervention tensors. |
| E104 | Direction/capture registration and code before affected capture | MET (capture-specific chronology) |§2135e075c6af00:12:34; fitter/helperafbc5eee100:37:17; capture CLIb2271c05702:42:19 all precede bound START2026-10-29T03:29:17.330492+01:00; COMPLETE2026-10-29T03:29:27.306175+01:00 | One-time unmodified dev40 capture | 5e075c6af;afbc5eee1;b2271c057;f95dcff93 | Bound START precedes the capture loop; output member mtimes round to whole seconds. This closes capture-specific order only, not earliest E104 N timing/test history. Passive unmodified capture at read token is not an ArmU intervention there. |
| E104 | R-U1 / R-N1 / shared falsifier | PENDING | No newly published committed doses or sealed test judgment/analysis grid | Actual U vectors ready; outcomes not supplied | f95dcff93;ffd3cc5e3 | No empty-set or readiness inference. Actual injection/norm and first-test custody remain due. |

## E104 sealed dev-dose selection and observed hook/norm audit

Publication490f23af0, authoritative **2026-10-29 04:40:18 CET**, supplies the four complete dev shards and E104_DOSES.json SHA **5d921857d24a7a1a6c98e6fe95c753b60a3d8e46e25616757dcaa9f19e8f7bbb**. Exact bytes match that commit despite the receipt's literal FROZEN_PENDING_GIT_COMMIT status. Verified every input/output-seal member hash, all3024 unique scheduled dev cells (N672+672,U840+840), completed job inventory and record ordering. Every84-item row rejoined to original E56/E59 dev identities,tokens,labels and the sealed CPU key; no missing/duplicate logits and no test item used. Frozen scorer SHAed24c667325bc25960d41394aaff0b2a6159cfba76292c5fc4a0ac1a7caf10eb explicitly selects pair_logits, with all frozen candidate continuations one token. R-Q recomputed each target-side sign and selected the smallest registered dose with>=59/84; no worker dose-selector entry point was run.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E104 | N fact_recall dose eligibility | NOT EVALUABLE (no behavioural flip gate) | Target-side counts at.5/1/2/4:0/0/0/35 of84; alpha-star absent | Same counts, alpha null | 490f23af0;5d921857 dose | No discrepancy; no dose reaches59/84. No inference that no individual item flipped. |
| E104 | N language_plan dose eligibility | NOT EVALUABLE (no behavioural flip gate) |42/42/42/42 of84 at.5/1/2/4; alpha-star absent | Same counts, alpha null | 490f23af0;5d921857 dose | No discrepancy; no eligible N row. |
| E104 | R-N1 | NOT EVALUABLE (no eligible row) |0/2 rows qualify for test | Both N alpha null | 490f23af0 | This is not NOT MET and does not support the claim that the E101 effect needs large norm. Norm-preservation execution itself works within observed BF16 rounding below. |
| E104 | U fact_recall dose selection | MET (selection check only) |0/0/0/42/84 of84 at.5/1/2/4/8 => smallest alpha-star8; selected dev B=1, Wilson[.9562667347,1] via common.stats | alpha8,84/84 | 490f23af0 | No discrepancy; test R-U1 remains PENDING. |
| E104 | U language_plan dose selection | MET (selection check only) |42/48/69/84/62 of84 at.5/1/2/4/8 => smallest alpha-star2; selected dev B=.8214285714, Wilson[.7260538099,.8886890910] | alpha2,69/84 | 490f23af0 | No discrepancy; later84/84 at4 does not replace the smallest qualifying dose. |
| E104 | U actual write-site grid / read capture | MET (logged site/source check) |13440 observed write-position records across1680cells: allblock40 and exactly read_index-8..read_index-1; all read_site records44/read_index | Eight preceding positions and passive read44 | 490f23af0;source63354951 | Verified sites and scalar norm calculations independently. Full before/after residual tensors are not retained in these dev records, so absence of all other writes rests on exact executed hook source, not solely on site labels. |
| E104 | U random displacement matching | MET (sealed deltas/source); PENDING (exact post-cast tensor equality) | All1680 U input deltas exactly equal alpha*devnorm*targetsign*unit; paired structured/random relative displacement-norm mismatch max9.0594710346e-10(fact),6.4258281401e-10(language) | Same-alpha norm-matched Gaussian control | 490f23af0;6a905cbf vectors | Both receive the same per-position displacement norm before BF16 casting. Actual coordinate deltas are not retained, so do not claim exact post-cast equality from before/after norms alone. |
| E104 | N executed renormalisation, both conditions | MET (observed norm/source check) | All1344cells at44/read position; maximum absolute norm_ratio-1=.0020804505254750083(fact),.002336640648402555(language);0>1.5 flags | Norm-preserving for structured/random | 490f23af0;source63354951 | Ratios recomputed from observed before/after norms, both conditions included. Departures below BF16 unit roundoff2^-8=.00390625, consistent with cast after per-item FP32 renormalisation. No new scientific tolerance/exclusion rule introduced. |
| E104 | U selected-dose norm flags | MET (descriptive reporting audit) | fact alpha8:any write-site>1.5 on84/84steered AND84/84random; language alpha2:0/84both; selected-dose read-site>1.5=0/84both rows/conditions | Raw site observations supplied | 490f23af0 | Across all5doses, each U row has168/420 per condition with any write-site flag,0/420read flags. Large write norms remain reported, not excluded. |
| E104 | Dose file committed before first affected test output | PENDING | Exact committed dose bytes at04:40:18 CET; no hash-bound first test output published | Frozen before test construction | 490f23af0 | Compare with earliest timing/test patched-logit/readout output, including attempts, when published; do not infer order from status text. |
| E104 | R-U1 / shared falsifier | PENDING | Two eligible U cells; no sealed judged test S contrast yet | Test pending | 490f23af0 | N ineligibility is not evidence of the shared falsifier; eligible U tests still required. |

### E104 executed source, scorer and dated ordering

All four dev output seals pin source **633549512f0675145896d6464a94ed2ea4a0f0df9e0ce9003948797b30e9ae47**. Verified its145member hashes against the exact reseal1 archiveSHA7f2a30a46052650a8678d8a05f332907d4b470429ffe703b66bfd7c2760b7a1f, rather than assuming later standing217 source was executed. Hook/scorer science is the reviewed U/N extension; original E101 same-site patched_forward is bypassed by explicit alternate forward.

- §2135e075c6af **00:12:34 CET**, acquisition/tests9e37f3504 **00:50:02**, and capture/fresh-extract closure fixb2271c057 **02:42:19** precede all four retained dev-production first outputs below. Fitter/helperafbc5eee1 **00:37:17** also precedes them. Analysis contracta2afc8b84 **00:19:13** is precommitted; scientific test analysis has not been run by R-Q.
- §213 operational note1 **853d1936a02:21:53** follows the no-cell startup packaging failure it diagnoses, but precedes the corrected retained productions. It does not alter science and permits no restart consumption for pre-load failure. Earliest real timing and all historical failed-attempt source/mtime inventory are not included in this dose publication, so complete first-ever-output ordering remains unverified.
- §217068236911 **02:48:01** precedes retained dev-production first outputs. Its staging clarificationda8275c8f **03:26:10** follows the two N production grids but precedes U production; operational cap chronology is not a new scientific threshold. Full cap/rehearsal/restart custody needs separately bound receipts and is not certified by these dose counts.
- First retained dev-production outputs from hash-bound mtime evidence: N language_plan **03:02:25.023753 CET**, N fact_recall **03:05:46.555071**, U fact_recall **04:31:30.339069**, U language_plan **04:33:11.553112**. These are dev outputs and correctly precede the04:40:18dose commit; they are not test leakage.
- Stored pair_logprobs versus registered pair_logits are not numerically identical: maximum mean-contrast differences Nfact.2500004768,Nlanguage.1171865463,Ufact.1875,Ulanguage.25. One Nfact steered alpha4 record is logit tie0 versus continuation-.0625; neither is target-side flipped, so all registered steered dev counts and selected doses are unchanged under this supplementary comparison. R-Q uses the explicitly frozen next-token pair_logits as §213 requires; no silent continuation substitution. The retained scores come from distinct forwards/batches; their differences are consistent with that numerical path. No multi-token strict-prefix comparison occurs in these E104 candidates.

## E105 §214 sealed arrival — independent raw continuation-score review

Arrival locator was published directly in R-Q's HANDOFF during the E104 review; read it only as custody coordinates and checked the BRIEF independently. Track Q owns E105 under §214. Publication **b110a8c1f**, authoritative2026-10-29 **04:52:52 CET**; result seal SHA **5795e14d46acff0ae5830c3ac8f882f4444cdb40b9f3e7ec2a54b124d5173047**. Verified aggregate/result/member hashes, normalized source-pointer seal9f29209ac3dff7965a0e156a786a49785a990f295f363865a493545cd567a77c, original504-item inventory seal7503c2cbc6b8fc44d402e3aeb18a89df7fb32de162b268c804f8ce89ff61d558, and all7 raw acquisition source seals/members (5COMPLETE,2NO_FIT). No failed-attempt partial score enters analysis. Independent input audit of all6 frozen252-cell row packages verifies original E100 T-donors, independently regenerates same-value/different-item S pairings with seed20261030 in frozen order, and checks all supplied fp32 vectors exactly equal the appropriate original E100 donor residual; baseline has no vector. Original84test identities,tokens,read positions and labels per row match sealed source metadata.

Read the original raw pair_logprobs through each sealed pointer, independently fixed candidate orientation toward the SAME T-donor value for allT/S/0, and recomputed Delta=c(T)-c(S), strict flips relative to the own unpatched sign, and each S/0/T mean. All420completed items/1260condition records are finite and complete; indent_level's84items are NOT RUN(operational), not zero scores or missing judgments. `common.stats.bootstrap_ci`,2000draws/seed20261027, paired item arrays, reproduces **all35 points and CI endpoints within1e-12**. No judge is involved, no once-only adapter/binder/runner invoked.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E105 | Positive-control gate | MET |2/3controls positive Delta and lower>0: language_plan.28455171130952384 CI[.054429452901794795,.5270537423236029];fact_recall.3113839058648972[.2574403906152362,.3649553629614058] | MET2/3 (passing2,required2) | 659fba82c;33b105a89;bd61820f5;b110a8c1f | format_plan Delta-.16228956267947242 CI[-.4659541408220927,.12171583260808656] fails. Gate reproduced. |
| E105 | R-BT1 | NOT MET |0/2completed missed rows meet both conditions; requires2. All T/S flip rates0/84 and paired flip differences0 CI[0,0] | NOT MET0/2 | b110a8c1f;5795e14d seal | No discrepancy. Nesting's positive continuous shift alone cannot satisfy registered flip-difference>=.20. Threshold not reduced after row loss. |
| E105 | Falsifier (all3 original missed rows) | NOT MET |page lower<=0;nesting lower=.042140442842528936>0;indent unknown =>passing1,unknown1,requires3 | NOT MET1/3,unknown1 | 33b105a89;b110a8c1f | Nesting already blocks the all3 conjunction regardless of absent indent. Do not narrow falsifier to2rows or treat NOT RUN as nonpositive. |
| E105 | nesting_depth descriptive Delta | MET (positive-shift condition only) |.11624997002737862 CI[.042140442842528936,.18948317453974767],n84;flip difference0 | Same point/CI | b110a8c1f | Prefix bias remains a limitation of absolute/sign metrics; this does not establish R-BT1 or the absence of model state use. |
| E105 | page_range_digit descriptive Delta | NOT MET (positive-shift condition) |-.009672636077517555 CI[-.040941275301433745,.020089309839975266],n84;flip difference0 | Same point/CI | b110a8c1f | No discrepancy. Original0/84 baseline/sign caveat retained. |
| E105 | indent_level | NOT RUN (operational) |Two distinct sealed NO_FIT attempts, no completed row; original84inventory preserved | NOT RUN after single restart | 157fb5459;b110a8c1f | Verified both failure-source hashes/status. Detailed cap/provider/restart execution custody not independently certified by this statistics review. |

### E105 registration, amendments, source and chronology

- Original §214 **2992dd87a02:25:49 CET** precedes located retained raw outputs. Original scientific adapter/tests **659fba82c02:34:13**, immutable input inventory **36dbb695702:53:41**. Original statistic() AST is unchanged; full continuation contrasts, paired bootstrap, strict flip definition and numerical thresholds remain unchanged in final code. Complete earlier timing/discarded-attempt inventory is not supplied, so before-first-ever-output ordering remains unverified even though these precede all located retained production outputs.
- §214 amendment1 **f4d8a130303:15:12** (heading03:45 nominal) raises GPU ceiling1→3h and permits six timing/production pairs; before located retained production first outputs. No metric/row/scorer change.
- §214 amendment2 **157fb545904:17:34** (heading04:25 nominal) authorizes the single +300s restart for fact/indent, then one analysis on completed rows, before restart outputs **04:37:09.662631(fact)** / **04:37:09.555633(indent,NO_FIT)** and before analysis. It follows the original three positive/missed production attempts, as its explicit “before any analysis” wording permits. It does not authorize dropping individual items or reducing the2-row R-BT1 threshold.
- Located retained production first-output times, CET: language_plan **03:36:12.730894**,format_plan **03:38:38.046565**,page_range_digit **03:40:01.762356**,nesting_depth **03:42:26.633854**; original indent NO_FIT first output **03:44:04.225308**. Fact's retained complete source is the restart at04:37:09.662631. These are hash-bound archive-mtime evidence; original fact failed-attempt/timing history is not fully inventoried by the final seven-source binding.
- Post-amendment adapter changes **db642b40704:26:34** add completed-row custody/eligibility; **33b105a8904:28:12** preserves the falsifier over all3originalmissed rows and treats absent components as unknown. These commits are after initial retained outputs, so the FINAL adapter must not be described as wholly pre-output. Changes implement the committed operational amendment, not a new effect/CI rule.
- Custody binder **bd61820f504:47:33** is after raw acquisitions sealed but before the once-only analysis; it copies the original MEASUREMENT_INDEX pointers. Execution HEAD **50838215604:48:28** precedes first saved analysis artifact **04:52:35.675724 CET**. Final result publication **04:52:52**. Thus original science predates located outputs; final row-custody code predates analysis, not every acquisition seal. No separately timestamped first-score-opening evidence is claimed.

The two known controls pass, but neither completed missed row meets the registered behavioural flip-difference criterion. The falsifier also fails because nesting has a positive lower bound. E100 silence plus these data therefore supplies neither the registered positive reader-side claim nor the registered all-three-row negative disposition.

## E87 sealed grouped grid — independent R-L1 and depth-profile audit

Publicationsd140a5de0(R-L1) and3726d7b59(depth),2026-10-29 05:12:42/05:12:45 CET. Verified result/member seals61c9ef5828b93708decc5c1d173a6b46e095655732d511c845fa4c5211d74d75 and5394396f6b2b46c0d442e2ae231a670d54f4fa7f05c1412778d3ed65301b1d03, original SPEC SHA1413d4c6fad31c7018415df266c586b1f5cf72cd3b98880ac011850569ffab35 and every input pin. Canonical spec is cache/g_agreement/r_e87/run1/SPEC.json under the Neel_Exploration/mats-minis cache. Its full pins bind JUDGMENTS a357a6a55256a92510c5b7a60a64627aff7922e018d6ab1034779bd47f929c54, private join50f135c4dd12c40de84e7d6f441358ca14caf158afde863fd4ddeb79284bb4d1 and grouped judgment seal2a1cbbbdd3d950446c23275b4a084fdac17693bfb66a2d65d6fca232bc04baeb; all13 judgment-seal members and original packet seala97ec15a746e2d8a0d410b273d9e6857325ccb53897d2ed673eb6f6057590134 verified.

All10rows use exactly the original first30test items in frozen E49/E57 bank order: independently checked IDs,splits,labels and target orientation. All4500groups are unique and present:2100Oracle real,2100Oracle placebo,300NLA real. Independently joined every one of67920grouped position readouts to its exact sealed native output text, reader,arm,layer,global item and offset. Both Oracle arms have identical128-token native caps; NLA512. Oracle7layers includes56; figure6layers excludes56 as registered. Short nesting prompts use12existing positions, not16fabricated positions.

**Random-only placebo independently verified:** regenerated the global seed20261029 Gaussian stream (row,item,7layers,16RNG slots,5120coordinates), retained available offsets and scaled to independently recomputed within-row/layer/offset medians of30real norms. Every component of all32760placebo vectors exactly equals the sealed array. Maximum relative norm-match error2.6260538188e-9. No shuffled/real text/vector was substituted as placebo. Full native-grid source selection is one completed seal per row; rows1–4 use their complete R2outputs, not stitched R1/R2readouts. Executed analysis source copies exactly match5b22f8aa8 and47034001d. Independently checked all10NLA means/missing counts and60first-mention medians, plus the code-algorithm classification counts; all reproduce numerically.

### R-L1 numbers and bootstrap

Independently mapped raw judged categories/values to +1/-1/0 with UNPARSEABLE missing, then used common.stats.bootstrap_ci on common30-item draws across both arms/all7layers,2000draws/seed20261029. All10Dpoints reproduce. Worker D and layer CIs **discard undefined resamples**; independently recomputed their conditional finite-draw quantiles and reproduced all10Dintervals plus106parseable layer point/CI records. The other34Oracle arm/layer records have no parseable item. For4rows, ordinary common.stats percentile output is undefined because some draws have no parseable placebo/real value; worker's finite-only interval is a conditional interval, not a2000-defined-draw interval. These bootstrap-reporting discrepancies do not change the registered point-estimate control gate.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E87 | R-L1 | NOT EVALUABLE (positive control fails) |loop_direction D=-.9090909090909091<.30;topic_twin D=.6666666666666667>=.30; missed rows5/8D<=.10,3/8D>=.20 | NOT EVALUABLE, same counts/controls |5b22f8aa8;d140a5de0|Mandatory control gate applied first, reproduced independently. No blind-spot-survives or single-site-falsifier headline follows. |
| E87 | R-L1 falsifier | NOT EVALUABLE (control gate) |3/8numerically reachD>=.20 (requires4); control fails | Gate-first NOT EVALUABLE |5b22f8aa8;d140a5de0|Raw threshold count is descriptive under failed gate. Seven-row sensitivity remains subject to the same gate. |
| E87 | D / container_after_move | DESCRIPTIVE |.9285714285714286; finite-draw CI[-.0940476190,2];28/2000undefined draws | Same point/conditional CI |d140a5de0|Ordinary common.stats CI undefined; worker filters28draws. |
| E87 | D / holder_after_handovers | DESCRIPTIVE |0; finite-draw CI[-1.75,0];735/2000undefined draws | Same point/conditional CI |d140a5de0|Worker filters36.75%of draws; entire placebo estimate can rest on1item. |
| E87 | D / branch_taken | DESCRIPTIVE |-1; finite-draw CI[-1,1];265/2000undefined draws | Same point/conditional CI |d140a5de0|Worker filters265draws. |
| E87 | D / var_type_at_use | DESCRIPTIVE |.3333333333333333; CI[-.6316985646,.8040616246];0undefined | Same point/CI |d140a5de0|No numeric discrepancy. |
| E87 | D / user_expertise | DESCRIPTIVE |0; CI[0,1.2];0undefined | Same point/CI |d140a5de0|No numeric discrepancy. |
| E87 | D / unit_system | DESCRIPTIVE |-.1333333333333333; CI[-.2,.7830434783];0undefined | Same point/CI |d140a5de0|No numeric discrepancy. |
| E87 | D / nesting_depth | DESCRIPTIVE |.5; CI[0,.6666666667];0undefined | Same point/CI |d140a5de0|No numeric discrepancy; not a gate-passing confirmatory result. |
| E87 | D / indent_level | DESCRIPTIVE |0; finite-draw CI[-1,.5];76/2000undefined draws | Same point/conditional CI |d140a5de0|Worker filters76draws. |
| E87 | D / controls | DESCRIPTIVE |loop-.9090909091 CI[-1.25,.5384615385];topic.6666666667 CI[0,1];0undefined both | Same points/CIs |d140a5de0|Loop fails on the registered point criterion; no CI requirement added. |
| E87 | Achieved n / missing judgments | MET (inventory); severely incomplete judgments |30scheduled per row/arm/layer;3444/4500UNPARSEABLE=76.5333%;Oracle real1299/2100,placebo1919/2100,NLA226/300missing | Same aggregate missing counts |2a1cbbbd judgmentseal;d140a5de0|Parsed denominators vary0–26/30per Oracle cell. Sentinel evidence is empty by design; no cause of parser/judge failure inferred solely from that fact. Original-rubric sample also863/1125UNPARSEABLE. |

### Depth classifications: missing layers are not below-threshold observations

The sealed worker profile reproduces numerically as4persistent,2consumed,1never,1outside-the-four across the8missed rows. However the code sets a missing real-layer score to counts=false and feeds that boolean into consumed/never. That conflates an undefined S with the registered S<.20 condition. Neither named consumed row has all required44/later layer scores. This is an independent classification finding beyond the already reported high-UNPARSEABLE anomaly.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E87 | holder_after_handovers consumed | NOT EVALUABLE (required layers unobserved) |L20S=1,n1;L44Sundefined,n0;L52Sundefined,n0;L60S=-.25,n4 | consumed |47034001d;3726d7b59|“Consumed: S>=0.20 at an earlier layer, but <0.20 at block44 and later” is not established by missing44/52. |
| E87 | indent_level consumed | NOT EVALUABLE (required layers unobserved) |L36S=1,n1;L44S=0,n2;L52/L60Sundefined,n0both | consumed |47034001d;3726d7b59|Missing later layers cannot establish S<.20; same literal consumed condition fails evaluation. |
| E87 | branch_taken never | NOT EVALUABLE (required layers unobserved) |L44/L60Sundefined,n0;other observed realS=0 | never |47034001d;3726d7b59|“Never: S<0.20 at every layer” requires observed/defined scores at every classification layer; code treats absence as false counts. |
| E87 | nesting_depth outside-four / floor policy | NOT EVALUABLE (ambiguous) |RawS: L28=1,L44=-.2,L52=0,L60=0; code's negative placebo floor at60=-.25 turns raw0into adjusted.25 and yields earlier+later without44 | outside the four |47034001d;3726d7b59|“Classification uses the registered0.20bar and the E76 judged placebo floor” does not specify max with E87's per-layer placebo, subtraction, or absent-E76 fallback. Those are precommitted code choices, not an independent authority for interpreting the BRIEF. Quote retained; no new policy invented. |
| E87 | Other depth labels | NUMERICALLY REPRODUCED (descriptive, floor-policy caveat) |container,var_type,user_expertise,unit_system satisfy the code's persistent predicate using observed44+earlier values | persistent4 |47034001d;3726d7b59|Required positive layers exist; no stronger statement about population persistence/UNPARSEABLE values. E76 floor covers unit_system only among8missed rows;7/8lack it. |
| E87 | §220 consumed/late trigger input | NOT EVALUABLE from the two claimed consumed labels |0of2claimed consumed labels establish all required later-layer S; R-L1 is NOT EVALUABLE, not NOT MET | Sealed worker countconsumed2 used in E95 reopening |9c56f1a54;3726d7b59|R-Q cannot certify that trigger from this classification. E95 ownership/launch decision remains with its integrator/coordinator; no E95 output/source changed by this review. |

Missingness bounds are wide: even control D ranges include both pass/fail when missing scores are filled adversarially (loop[-1.1333333333,1.2666666667],topic[-.4666666667,1.8]). These are sensitivity summaries, not a registered replacement rule or repaired result. Do not infer that unparseable layers are silent, that a state was consumed, or that the model does not use it.

### E87 dated registration/fix ordering — user-requested checks now closed

Original registration0567e8a10 **Oct28 10:33:42 CET**; §202 clauses0d052d31 **10:41:47**; clarification1df037c47f **10:55:09** (adds56); clarification247cf57c29 **11:49:56** (all available short-prompt positions,8row+7row sensitivity). All precede earliest retained native job **Oct28 12:34:12 CET**, row0. Full discarded-attempt/earliest-pilot inventory is not supplied; no complete first-ever-output sign-off inferred beyond retained sources.

Operational7549cc07b **Oct28 17:11:30** precedes retained R2first native jobs: rows1/2/3/4 at18:29:26/18:30:19/18:30:29/18:30:49 CET. Full regenerated per-row grid/source text joins verified, but unopened R1retention and exact cumulative cap accounting still require custody evidence; no new probe/readout rerun.

Reporting clarification3 **4c3e9dca800:22:26 CET Oct29**, reporting code **47034001d00:29:02**, gate-fix+synthetic test **5b22f8aa800:38:15**, and §220dependency **9c56f1a5403:19:02** all precede bound main JUDGMENTSmtime **03:39:19.402093** and final grouped JUDGMENT_SEALmtime **05:11:03.655447**. The original-rubric sample ends with the final seal; main judging began Oct28 23:56:52.128353, before reporting clarification3. The requested boundary is pre-SEAL; do not substitute pre-first-judgment for that reporting-only check. R-L1 registration text remains unchanged. Analysis outputs are05:11:36 CET; source/result hashes reproduce. Thus **gate fix before grouped seal MET; clarification3 before grouped seal MET; §220before grouped seal MET**. These chronology checks do not cure the missing-layer classification issue.

## E104 requested attempt history — chronology verified

Integrator publication45d71517c supplies15attempt hashes in E104_ATTEMPT_CHRONOLOGY.json. Independently verified every output-seal/member hash, status/source binding and original first-output evidence. Both initial N_devtiming failures have0job files and ModuleNotFoundError for common; no scientific output exists in those seals. U_capture40also has0jobs but COMPLETEcapture members, so0jobs alone is not taken as failure/no capture.

Earliest real E104 timing output is N_devtimingB/language_plan **Oct29 02:53:33.537966 CET**, after registration00:12:34, original U/N implementation/tests00:50:02 and corrected capture/runtime packageb2271c05702:42:19. The two earlier failed startup attempts use olda0f54477source and are classified separately under §213operational note1/§217pre-load accounting. This closes the earliest-output history gap for the15published attempts, without asserting unlisted runs never existed.

Crucially, earliest affected TEST output includes test TIMING: U_testtiming/language_plan **04:49:39.759292 CET**, before primary U_test/fact_recall **04:59:42.578164**, then U_test/language_plan05:01:18.791035. Dose commit490f23af0 **04:40:18** precedes even the earlier timing output by **9min21.759292s**. The Integrator's “earliest test03:59:42Z” line describes primary production and omits test timing; ordering still passes when timing is included.

| E104 | Committed exact doses before FIRST affected test output, including timing | MET |5d921857dose bytes committed04:40:18 < first testtiming04:49:39.759292 CET | Claimed primary firsttest04:59:42.578164 |490f23af0;45d71517c|Located earlier test timing; no ordering violation.|
| E104 | Corrected source/tests before first real dev/timing output | MET (15published attempts) |b2271c05702:42:19 < earliest timing02:53:33.537966; original source/tests00:50:02 also earlier | All15attempts supplied |45d71517c|Both failed original pre-load attempts have no jobs and explicit missing-common import failure; source provenance gap closed for supplied inventory.|

## E104 sealed judged test — R-U1 independently recomputed

Publication959cb0fca, actual2026-10-29 **05:44:53 CET**, result seal **01d8d5a17b7bbea1d2df27982ef10c897156093430967d8da442e0a5137cbe1e**. Verified results/binding/member hashes, raw judgment archiveb07de23959451106f859ad351e3e63e2a52751e36fad84cf51e1e6b2398428c8, judgment sealce564237b9951502478d26ab9c5bdcca3a8e3a7c90c0579660c76e4149cbf85b, blind seal1e0df9accd2f19fd042387701c385a1a6d4b2d2e0e700e27421fc4bc9de64b0d, private hash495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4, normalized input0d1ccb6d088960540c0fef2b4c973dd9b02c5941bfd153b870b7e8914d37ae7d, and every pinned raw source/output member. All336eligible greedy Oracle readouts present:84test items per row ×steered/random; no N test cells. Original test IDs/row labels and other-value sign rejoined to original sealed E56/E59 metadata. Every normalized text/behaviour/norm field rejoined its sealed raw pointer; every blind/private judgment identity and target/value mapping matches. No once-only entry point invoked.

R-Q independently scored the raw judgments and recomputed target-side behaviour from frozen next-token pair_logits, averaged over the original candidate pairs. Selected the steered-flipped cohort once per row; the random score uses those SAME item identities, irrespective of random behavioural flip status. Kept all84IDs in joint item resampling with nonflipped masked out and each arm's actual missing judgments separately masked; common.stats.bootstrap_ci,2000draws/seed20261028. **All14 point estimates and CI endpoints match exactly within1e-12**: B,B_random,conditional Ssteered,Srandom,paired difference and both all-test S. There is no complete-case substitution or second random-flipped cohort.

| Experiment | Rule/check | Verdict | R-Q number/evidence | Worker number/claim | Commit checked | Discrepancy note |
|---|---|---|---|---|---|---|
| E104 | R-U1 | NOT MET |0/2eligible rows achieve difference>=.30 with lower>0. Factalpha8:.1785714285714286 CI[.08333333333333337,.27380952380952384];languagealpha2:.14444444444444443 CI[-.033397990136398346,.31807313657170166] | NOT MET, same estimates/CIs |a2afc8b84;959cb0fca|Fact's positive lower bound alone does not satisfy the.30effect threshold. Language also has lower<=0. |
| E104 | R-N1 | NOT EVALUABLE (no dev-qualified row) |Both N dosesnull,0eligible test rows | NOT EVALUABLE |490f23af0;959cb0fca|Retains prior independent dev gate result; no norm-necessity inference. |
| E104 | Shared falsifier | NOT MET |0/2eligible U cells satisfy difference<=.10 ANDupper<.30; fact point.17857>.10,language point.14444>.10 andupper.31807>=.30 | NOT MET |a2afc8b84;959cb0fca|No empty-set inference from N ineligibility; cannot quote “lens reads the injected write at large norm” as this registered falsifier. |
| E104 | Fact behaviour B / paired cohort | MET (descriptive reproduction) |84/84steered B=1 CI[1,1];random42/84=.5 CI[.4047619048,.6071428571];cohort84 | Same numbers |959cb0fca|Dev/test selection remains distinct; same84 test IDs in both arms. |
| E104 | Language behaviour B / paired cohort | MET (descriptive reproduction) |50/84steered B=.5952380952 CI[.4880952381,.7023809524];random42/84=.5 CI[.3928571429,.6071428571];cohort50 | Same numbers |959cb0fca|No new70%test gate: qualification was frozen on dev. Random conditional S uses the50steered-flipped items. |
| E104 | Fact conditional and all-test S | MET (descriptive reproduction) |Steered=-.5 CI[-.6190476190,-.3809523810];random=-.6785714286 CI[-.7738095238,-.5833333333];conditional=all-test because all84flip | Same numbers |959cb0fca|No actual missing judgments in either condition. |
| E104 | Language conditional S | MET (descriptive reproduction) |Steered=-.3555555556 CI[-.6041787791,-.0908585859],45/50kept;random=-.5 CI[-.7083333333,-.2641509434],48/50kept | Same numbers |959cb0fca|The5/50steered missing flag is10%, above5%;2/50random missing=4%. Does not automatically add an unregistered decision gate. |
| E104 | Language all-test S and missingness | MET (descriptive reproduction) |Steered=-.5641025641 CI[-.72,-.3874791667],78/84kept;random=-.6375 CI[-.775,-.4875],80/84kept | Same numbers;10totalmissing |959cb0fca|Actual all-test missing6steered+4random. Nonflipped34items are cohort exclusions, not34additional failed judgments. |
| E104 | Test write/read norm flags | MET (observed reporting check) |Factsteered/random84/84each any-write and concatenated-write>1.5;0/84read flags;maxconcat2.5650256358/2.4781271276,maxread.9995510451/.9960650310. Language0/84flagsbothsites/conditions;maxconcat1.2149800155/1.2125507026,maxread1.0217359642/1.0064293465 | Per-item ratios supplied |959cb0fca;rawUtestseals|All8logged write sites are40/read_index-8..-1; passive read44. No norm exclusion and no substitution of read-site norm for injection norm. |

### Missing-score sensitivity (supplemental, not a new rule)

Fact has no missing judgments; its observed result is unchanged by missing-score bounds. For language's50-itemsteered-flipped cohort, filling the5missing steered scores as-1/+1 and2missing random scores oppositely gives paired point bounds **[.02,.30]**. With the same common.stats item-bootstrap, lower-fill difference.020000000000000018 CI[-.1818181818181818,.2]; upper-fill difference.30000000000000004 CI[.11627906976744186,.49056603773584906]. Thus the extreme upper completion would satisfy R-U1 even though the observed parseable-score estimator does not. Report R-U1 NOT MET with this missingness sensitivity; do not silently convert missing to failures, exclude flaggednorm items, or claim a missingness-robust negative. No new source/result file or alternative sealed verdict was written.

### E104 source and chronology sign-off

Every scientific adapter file and pinned dependency exactly matches original **a2afc8b84 (Oct29 00:19:13 CET)**. Judged bank sealmtime **05:39:24.378136 CET**; analysis execution HEAD34cccb7dc **05:42:55** and first RESULTS **05:44:02.536544**, ANALYSIS_SEAL **05:44:02.537131**. The execution HEAD follows judging, but unchanged scientific adapter/tests were committed long before it; do not confuse HEAD timing with the source freeze. This satisfies the pre-bank-seal source requirement. First judgment-opening is not independently timestamped, but source predates the entire located test acquisition and judgment seal.

Registration5e075c6af00:12:34, operational note853d1936a02:21:53, corrected execution packageb2271c05702:42:19, §21706823691102:48:01 and staging clarificationda8275c8f03:26:10 all predate affected Utest timing/production; exact dose490f23af004:40:18 precedes FIRSTtest timing04:49:39.759292 as independently closed above. No new E104 scientific amendment appears in §221; its validator exception applies specifically to E87/E103. Strict E104 judgment scores were not re-parsed under that exception. Actual judging costUSD.150412 underUSD5cap with zero unresolved reserve is recorded in the sealed handoff; reviewer made no call or launch.

## §221 coordinator disposition — E87 strict evidence preserved; corrected review pending

Commit **f60fd54fe**, authoritative **2026-10-29 05:44:46 CET** (heading06:00nominal), explicitly acknowledges R-Q's missing-layer consumed-label finding and states the strict §220trigger is not valid evidence. E95 production is held until one validator-corrected E87classification is sealed; if not sealed byThu16:00CET, E95 NOT RUN(operational). This supersedes the earlier strict-trigger reopening disposition, without changing the strict E87 result or R-Q review.

The same ruling authorizes **E87 deviation1**: owner commits a minimal validator correction+tests before any re-parse, accepts silent with empty values/evidence while ignoring its first_position, re-validates sealed responses once with no new paid call, then reruns registered analyses once under an explicit validator-corrected label. Other UNPARSEABLE responses stay missing. Strict publicationsd140a5de/3726d7b5 stay unchanged and disclosed. R-Q will independently verify corrected response eligibility, exact same raw response identities/hashes, minimal source/test commit before first corrected parse, affected n/missingness, bootstrap and classification predicates on arrival. This narrow coordinator exception permits the owner's corrected analysis; it does not permit reviewer execution of the worker's once-only entry point or arbitrary score/metric change. No corrected result is yet claimed reviewed here.

The reported audit says3041of3444strictUNPARSEABLEmain replies are otherwise valid silent JSON rejected for non-null first_position. That is a coordinator-bound diagnosis locator pending independent response-level verification, not a number R-Q independently recomputed in the strict audit. §221does not explicitly resolve the separate floor-integration ambiguity noted above; preserve it for the corrected-profile review rather than infer a new floor policy. E103correction/E106placebo/E108scope/caps in§221 stay with their assigned reviewers/owners.

## §222 E109 added to R-Q scope — pre-output intake

Shareda48038dc8 includes §222 **2d470093a**, authoritative2026-10-29 **05:55:29 CET** (heading06:10nominal), explicitly assigning E109 to R-Q. No E109 capture/reader/judgment/analysis seal or frozen adapter is published in this intake. Scientific outcomes and registration-before-first-output checks remain PENDING. Original E104 alpha8/2, dev vectors and84/50steered-flipped test identities are fixed inputs, not reselected using E109. Probes must fit only unhooked original84dev activations per layer, then score hooked test; capture3conditions at44/48/52/56/60, Oracle readouts at44/52/60. R-AR1 requires probe>=70% on the fixed cohort AND paired reader difference>=.30 with lower>0 on>=1row at a later measured reader layer (52or60; no Oracle read at48/56 is registered). With full cohorts,70%means>=59/84fact or>=35/50language; no new test-cohort shrinking rule supplied.

| E109 | R-AR1 / R-AR2 / R-AR3 | PENDING |No sealed E109 measurements; original E104 cohorts84/50 | New registration |2d470093a|Verify exact Uhook/non-read-token mutation, dev-only unhooked probe training, frozen cohort/doses, all capture layers and paired readouts when published. No original experiment replay by reviewer.|
| E109 | Account falsifier, global row aggregation | NOT EVALUABLE (ambiguous registration) |Two rows registered, no explicit any-row/both-row/pooled quantifier in falsifier |“the probe flips at block44 on>=70% and the Oracle at44 follows with>=.30”|2d470093a|R-AR1 explicitly says at least one row; falsifier does not. Record per-row numbers when available; do not silently import that quantifier into a global falsifier. Coordinator clarification before output requested in HANDOFF.|

§222's site-local decoder framing is a newly stated account to test, not a new result from E104/E105. E105 zero strict flips does not establish absence of model use: nesting has positive continuous Delta/lower bound and the registered falsifier is NOT MET. E104 U NOT MET does not itself show the read-token state is absent; E109 is intended to distinguish arrival from decoding. Existing independent numerical verdicts are preserved; no stronger mechanistic conclusion certified by this registration intake.

### E87 deviation1 corrected judgments arrived — independent response-level audit

Publicationeda3951f3 supplies corrected judgment seal8da7b0f48bdbdb8e32c20c9bd3ca89100a2ca0fecfdd04e87c077f95b3f76561 and archive018d838c6264508e72c47c183afb49c5b965d8002a4d122eccc3239ab74f3e26. Verified all corrected-seal member hashes, correction-source seal082d1d473c0465a4f1548e9bf7789e9db45c477b790089ee4e36f0cc5d52f90f, source/test bytes against7170fe028 and current original ledger/private hashes against the correction receipt. Strict judgments/results remain unchanged. No corrected statistical analysis is claimed reviewed by this intake.

R-Q independently reconstructed the ORIGINAL FINAL-attempt wire for every previously UNPARSEABLE main/original-sample record, computed its request identity from stage+blind-seal+canonical wire, and verified both exact saved request equality and original route-audit response hash. Parsed only those already sealed responses and checked the coordinator's narrow eligibility directly, without invoking worker revalidate221/run or its validator: one matched opaque ID, exact schema, silent category, empty values/evidence, non-null first_position. Exactly3041main and768original records satisfy it; replacing only first_position by null exactly matches every corrected code. Every other old missing record remains byte-value equal; all1056previously kept main codes and262original codes remain equal. This independently verifies the reported diagnosis, not just the owner's summary.

| E87 | Deviation1 recovery eligibility / missingness | MET |4307raw final-attempt missing responses audited; main3041silent recovered,403stillmissing; original768recovered,95stillmissing |Same counts; main4500/original1125 identities preserved |7170fe028;eda3951f3|No new truth/value assignment or changed non-silent category. All other missing and old kept codes preserved.|
| E87 | Validator correction before FIRST corrected parse | MET |§221f60fd54fe05:44:46CET < fix+tests7170fe02805:54:10 < REVALIDATION_START05:54:39.386779; completion05:56:37.963051 |Precommitted narrow correction |7170fe028;8da7b0f4seal|R-Q also independently ran13pure synthetic validator cases: allPASS; no worker reparse, file-writing test or analysis entry point invoked.|
| E87 | Corrected R-L1 / depth classification | PENDING |Corrected judgment grid sealed; new labelled analysis not yet reviewed |Correction publication says statistical_analysis_run=false |eda3951f3|Original scientific rules, strict review and floor-policy ambiguity preserved; recompute corrected bootstrap/classification when the labelled analysis seals.|

## E109 clarification1 and E104 §223 audit extension — direct Guiv ruling

Commit **995a2e2cd**, authoritative **2026-10-29 06:19:18 CET** (heading06:35nominal), resolves the E109 falsifier row aggregation raised by R-Q. The falsifier is evaluated per row, with separate row reporting and no pooling; it is met if at least one row satisfies BOTH block44conditions: probe flips>=70%of that same row's frozen cohort, and NEW E109 Oracle steered-minus-random difference>=.30 with lower CI>0. It is not a cross-row conjunction and does not use the old E10444difference for the falsifier. Prior ambiguity finding is historical and superseded by this explicit coordinator rule. R-AR1 and all other registered estimands remain unchanged.

| E109 | Falsifier row aggregation / CI condition | RESOLVED; outcome PENDING |>=1row independently satisfies probe>=70% ANDnewE10944paired difference>=.30 ANDlower>0; cohorts84/50 =>>=59/84or>=35/50probe flips | Per row, any row; report separately |995a2e2cd|Apply the full committed text, including lower>0; never pool rows or combine conditions from different rows.|
| E109 | Clarification1 before first affected output | PENDING (ordering) |Known actual commit06:19:18CET; no hash-bound first E109 capture/timing/test output published in reviewed snapshot9d196c7e2 |Heading says before any E109 output |995a2e2cd;9d196c7e2|Compare actual commit with earliest affected output including timing/pilots when sealed; do not infer ordering from the heading or source-readiness handoff.|

The §223 addition in the SAME commit explicitly assigns W-internals-B's missingness audit the10strict E104terminalUNPARSEABLE judgments (including5in language's steered-flipped cohort). If the §221measurement/validator defect is found, the owner may perform the same minimal tested correction/revalidation of sealed responses with no new calls, then ONE separately labelled “validator-corrected (E104 deviation1)” registered analysis for R-Q review. This is conditional authorization, not a presumption that E104has the E87defect and not permission for arbitrary retry/rejudging. Strict E104publication and independent14-stat review stay unchanged. If no defect is found, current missingness sensitivity remains.

| E104 | §223 parse-audit / conditional corrected analysis | PENDING |10strict missing judgments; languagecohort5/50steered,2/50random as independently reviewed; extreme completion can reverseR-U1 |Audit now assigned; one corrected rerun only if defect found |995a2e2cd|Require sealed audit diagnosis, correction+tests committed before first re-parse, exact original-response/request hashes, allowed recovery-only diff, unchanged other/kept records, strict disclosure and one labelled analysis. Reviewer never runs worker reparse/analysis entry points.|

No new audit or corrected E104 result is yet claimed reviewed. On arrival R-Q will independently check recovery eligibility, timestamp ordering, exact cohort/pairing/missingness, all rule CIs and verdict differences against strict. Direct Guiv instruction supplies this authorization without another confirmation. §223items2(E80c variance-normalized comparison) and3(E94within-row precision) are new descriptive close-out deliverables within the existing R-Q experiment scope: review their sealed outputs when delivered, label E80ccomparison post hoc and preserve R-X3. E110stays with R-2.

## E76 judged-floor independent audit and E94 §223 report — 2026-10-29 06:40 CET

Shared snapshot `a5f7f4584`. This closes the outstanding primary E76 judged-table numerical audit; earlier statements that its terminal analysis was unpublished are superseded. The already reviewed complete regex floor is unchanged. No worker analysis/export/revalidation entry point was replayed. E87 corrected statistical/depth analysis, E104 conditional parse audit and E109 output remain PENDING on this snapshot; no new outcome inferred from readiness messages.

### E76 judged floors

Publication `e625ca3eb` (Oct28 12:25:34 CET), analysis seal `582233a4f965f3e18b50786f94ef9878fb3344e470828b1fb450ac7395216a05`, table `cf3e671f272c9aa5fd7915551addb4c1134058b4b41145256ad14c29999caac0`, terminal seal `c23fe823b38904b2e3e02a8a90151d66d7e70af65127aed30cf30d506e0a3f7c`. Independently verified all terminal/analysis file hashes, production seal `4a199f6c`, CPU seal `e68a113e`, blind seal `d4abb343`, private grouping `9ef0280a`, and all59 source-file pins. All4992 grouping/native-readout/reader/pool/index/text joins match the original sealed production. Independently regenerated seed20261028 without-replacement selection and seed20261029 pseudo-truth coins. The registered expansion cap gives floor(5000/(48families×2readers×2pools))=26 vectors/cell; achieved4992 pairs across43 bank/row entries and48 binary families. This is a descriptive random pseudo-truth floor, not a natural-item accuracy estimate.

Every primary and redaction-excluded S/N point and CI was recomputed from raw terminal categories using `common.stats.bootstrap_ci`, 2000draws, seed20261027, resampling pool-vector clusters with families kept together and frozen family weights. Missing codes retain separate family denominators; no zero imputation. All688 statistic triples match within1e-12, including four-ID redaction sensitivity. No undefined bootstrap interval was encountered. Source script bodies `core76.py`/`analyze_once76.py` are byte-unchanged from `83775ee3f` (Oct28 05:38:41 CET). §194 clarification2 `f3fcb7153` committed05:09:07 CET, before that source freeze and before the earliest retained ledger event11:12:33.034493 CET; terminal START mtime11:42:52.464590, final judgments12:23:47.411668, first analysis12:24:26 per sealed run receipt. Thus the new judged-floor registration/source precede located judging evidence and first analysis. Complete earlier discarded judging history is not independently inventoried; do not equate a resumed START with guaranteed first-ever output. The original registration/clarification1/compute-deviation chronology remains recorded in the earlier E76 section; this CPU audit does not retroactively certify unbound GPU pilot ordering.

| Experiment | Rule / audit | Verdict | R-Q number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E76 | Judged sample size / independent S and N floor | MET (descriptive audit) |26vectors/cell;4992pairs;688point/CI triples exact;max absolute S=.20 |Same n;max absolute S=.20 |83775ee3f;e625ca3eb|No numerical discrepancy. Max is Oracle E62 S3_L3 shuffled S=.20, CI[0,.40]; no registered new decision rule.|
| E76 | Missingness / redaction sensitivity | MET (audit) |23/4992UNPARSEABLE;4redacted IDs;4969kept;all full/excluded intervals reproduce |23missing;4redacted |e625ca3eb;c23fe823|Largest cell missingness5/26 each Oracle E59 format_plan pool; point S=-.19047619 in each. Missingness is excluded, counted and not silently assigned zero.|
| E76 | §194 clarification2 / code before located judged output | MET for located evidence; full history unverified |05:09:07registration <05:38:41unchanged source <11:12:33retained ledger; first analysis12:24:26 CET Oct28 |Run receipt execution HEAD483ab89ee at11:53:00 |f3fcb7153;83775ee3f;483ab89ee|Execution HEAD is later than early judging, but the actual unchanged analysis bodies were committed earlier; no false post-output-code allegation.|
| E76 / E57 | clause_pending NLA reported S versus random floor | WITHIN .20 (descriptive) |Reported .2619047619;floor .1923076923 CI[-.0384615385,.4230769231];gap .0695970696 |Same sealed S and floor |e625ca3eb;registry source pins|Original REPORTED verdict unchanged; this small sampled floor has substantial uncertainty. Shuffled gap .2234432234 exceeds.20.|
| E76 / E57 | clause_pending Oracle reported S versus random floor | WITHIN .20 (descriptive) |Reported .2592592593;floor .1538461538 CI[.0384615385,.3076923077];gap .1054131054 |Same sealed S and floor |e625ca3eb;registry source pins|Original REPORTED verdict unchanged. Shuffled gap .2592592593 exceeds.20.|
| E76 / E57 | subject_number NLA reported S versus shuffled floor | WITHIN .20 (descriptive) |Reported .2261904762;floor .0769230769;gap .1492673993 |Same sealed S and floor |e625ca3eb;registry source pins|Original verdict unchanged; random gap .2261904762 exceeds.20.|
| E76 / E62 | S1_L3 Oracle reported S versus both floors | WITHIN .20 (descriptive) |Reported .2409638554;random/shuffled floor both .0769230769;both gaps .1640407785 |Same sealed S and floors |e625ca3eb;registry source pins|Original verdict unchanged. These are differences of descriptive point estimates, not a new paired hypothesis test.|
| E76 | Remaining matched S-based REPORTED comparisons | OUTSIDE .20 (descriptive) |44/48row-reader S claims outside.20 for both pools;4/48 above within at least one pool |No worker cross-verdict table located |e625ca3eb;59source pins|48original S claims compared without aliases or cross-bank row pooling. This does not certify all later banks.|
| E76 | Other-channel / full all-verdict comparison | NOT EVALUABLE (incomplete comparable metrics) |22registry claims have no comparable registered S field:14E36 AUROC,6E49 forecast/supplement claims,2E54 both-inclusive correctness claims |Registry preserves these separate criteria |e625ca3eb|Do not subtract an S floor from AUROC or silently replace original both-inclusive/forecast criteria. E88 detector-rescoring and broader later-bank comparisons remain outstanding.|

### E94 within-row report on arrival

New `872ed117f` publication seal binds report-only projection at **Oct29 06:33:06.044977 CET**, source analysis `c33dc8ef` and original RESULTS hash `c4041b9b`. Both files and all original sealed files remain hash-exact. Independently rebuilt every report denominator/numerator from the original sealed per-stratum confusion counts (already independently joined from raw judgments in the earlier E94 review), aggregated E67 only by its stated diagnostic condition/arm, and recomputed both precision and coverage with `common.stats.wilson`. This checks a new display of unchanged counts; no bootstrap or original once-only analysis was repeated.

| E94 | §223 item3 within-row precision / coverage | MET (descriptive report audit) |103rows:89value-grounded (50estimable precision,14observed rows with zero decisive agreement,25E62rows with no paired acquisition),14separate E67diagnostics;206rate/interval fields checked |89value rows/50estimable +14diagnostics |872ed117f;c33dc8ef|Every count/rate matches; Wilson endpoint max difference9.03e-6 is common z=1.96 versus worker1.95996398454. Zero-data E62 is unavailable, not evidence of failed agreement.|
| E94 | H-A1 / pool preservation | MET (existing descriptive hypothesis unchanged) |Pooled943/1001=.9420579421; coverage1001/4313=.2320890332; old difference/cluster CI unchanged |Identical original pooled object |872ed117f;c33dc8ef|Within-row precision varies: E59 decline_plan32/50=.64, E57 section_header23/37=.62162162; pooled precision does not establish uniform row-level reliability or control difficulty within rows.|
| E94 | §223 report registration / projection code ordering | Registration PRE-REPORT; code-pre-report UNVERIFIED |§223addition995a2e2cd06:19:18 < report06:33:06.044977; code and report first published together872ed117f06:33:10 |Report-only projection, no new calls/rescoring |995a2e2cd;872ed117f|No earlier committed projection-code locator found; publication is3.955023s after report timestamp. This is not evidence that the original E94 analysis code was late.|
| E94 | Full paired placebo / all-bank report | PENDING extension |Current report correctly retains source-freeze E76 unavailability caveat; new E76 table reviewed above does not itself supply a paired E94 placebo grid |Explicitly incomplete §214 placebo extension |872ed117f;e625ca3eb|Do not describe E76 judged floors as currently unpublished; pairing/extension remains separate.|

## Scheduled intake — 2026-10-29 07:00 CET: E87 floor ruling and E111

Shared snapshot `9b461fd51`. Owner inbox and addressed HANDOFF entries checked under §217; parked work and unchanged completed numerical audits were not repeated. E80c post-hoc locator remains a foreign uncommitted HANDOFF append/local worker-branch publication, not shared-branch review evidence. It is preserved outside R-Q commits. No corrected E87 statistical seal, E104 audit/reanalysis or E109 bound output grid was published in this shared diff.

### E87 clarification4: floor-policy ambiguity resolved prospectively

Direct coordinator BRIEF commit `ee7ec683b`, actual **Oct29 06:48:09 CET** (heading07:15nominal), supplies the previously missing rule authority: at each layer use max(0, E87 placebo S_layer, covered-row E76 judged Oracle floor), then qualify iff real S minus that floor >=.20. It explicitly applies to validator-corrected E87 deviation1 / §220 and leaves strict analyses and R-L1 unchanged. Thus the earlier floor-integration ambiguity is CLOSED for that corrected scope; strict findings remain historical. Absent-E76 rows still use max(0,E87placebo); missing real layers do not acquire observed negative evidence merely from this floor ruling.

| E87 | Clarification4 floor implementation | MET (source / synthetic audit) |Negative placebo -.25 with real0 produces floor0 and no qualifying layer; committed regression test PASS; mandatory control-gate regression also PASS |Same test expectations |ee7ec683b;62e52f6a1|Actual code commit06:48:59CET follows authority by50s. Diff adds0to the max and documentation/test only; R-L1 implementation unchanged. No real-grid analysis entry point invoked.|
| E87 | Clarification4 / fix before corrected statistical analysis | PENDING (ordering) |Authority06:48:09 < source/test06:48:59; corrected analysis first-output/seal not published in reviewed shared snapshot |Claimed prospective |ee7ec683b;62e52f6a1;9b461fd51|Compare against FIRST corrected statistical/depth output when delivered, rather than the earlier validator reparse. Earlier completed judgment-recovery chronology remains closed.|
| E87 | Corrected R-L1 / depth classifications | PENDING |No new labelled analysis seal located; strict R-L1 NOT EVALUABLE preserved |Awaiting once-corrected publication |9b461fd51|No inference of consumed/late counts or §220 eligibility from source changes alone.|

### E111 assigned to R-Q (§224)

Registration `2768a60aa` actual **Oct29 06:50:46 CET**; clarification1 `bb43088d1` actual **06:52:20 CET**, nominal headings07:25/07:30. CPU-only, no new judgments/GPU. Cohort is sealed intervention/control items with available block44 read-site vectors from E104U, E109, E101(reconstructed and labelled) and E100a; UNPARSEABLE dropped/counts reported. Dev-only frozen row probes define target-logit shift x1; sealed target-side behaviour defines x2. Pooled logistic y~x1+x2+row fixed effects, item bootstrap2000seed20261029. R-SL1 requires positive x1 coefficient with lower>0 and the registered x2-CI / magnitude branch. The magnitude branch is |beta1 SD(x1)|>=2|beta2 SD(x2)| on pooled sample; negative beta2 cannot pass solely on sign. Falsifier is positive x2 lower>0 plus x1 CI including0. R-SL2 stays descriptive. Run once after E109seal, or Fri00:00CET without E109 (explicitly excluded); code/tests must be committed before E109seal.

| E111 | R-SL1 / falsifier | PENDING |No source/result seal published; no regression or item bootstrap performed by reviewer |Not available |2768a60aa;bb43088d1|On arrival verify raw judgment/vector/behaviour joins, matched controls, dev-fit probe custody, reconstructed-vector labels, actual n/missingness and common.stats item bootstrap; preserve original experiment verdicts.|
| E111 | R-SL2 descriptive / registration-code timing | PENDING |Registration06:50:46 and magnitude clarification06:52:20; affected output / code and synthetic-test publication absent |No sealed output |2768a60aa;bb43088d1|Do not infer pre-E109-output or pre-seal ordering from nominal heading. Check first affected timing/capture output and code-before-E109-seal separately.|

E109 runner HANDOFF now reports timing seal `f9c3b1ad` / profile `950cd185` and production underway; these are locators, not a bound first-output inventory. Earlier “no output” statements mean no reviewed hash-bound publication, not proof that timing has not happened. Clarification995a2e2cd-before-FIRST-E109-output remains unverified until the timing seal/member/capture timestamps are supplied. No score opened or rule interpretation accepted from the runner.

§217 clarification2 `3f9842e1a`, actual **Oct29 06:47:53 CET**, prospectively defines zero-cost embedded429/5xx/finish_reason=error as transport: diagnostic content unscored, up to2same-request retries with >=30s backoff, terminal missing if exhausted, unchanged caps/reservations. Charged errors retain rule5. This reviewer launched no bank/retry; future custody audits must distinguish these from judgments and compare authority against affected attempts. E97 handling is other-reviewer ownership.

During pre-publication rebase, E111 source arrived in **86119ae65**, actual **Oct29 06:59:40 CET**, superseding the adapter-absent intake state above. All6 SOURCE_RECEIPT member hashes independently match. All10 committed pure synthetic tests PASS (including the full2000draw case); reviewer did not invoke adapter.main, input normalization or the once-only claim. Source uses finite unpenalized logistic MLE, row intercepts, source-item cluster bootstrap preserving repeated experiments/controls, and explicit non-evaluable status if any bootstrap fit fails; it does not discard failed replicates and claim a finite confirmatory CI. The magnitude implementation retains the positive-site/lower-bound gate. This is source inspection, not certification of an unprovided normalized dataset, probe lineage, cross-experiment cluster identity or complete cohort.

| E111 | Committed source / synthetic readiness | MET (source audit); output ordering PENDING |6/6source pins exact;10/10synthetic tests PASS;2000draws seed20261029 fixed |10tests/PRE_OUTPUT_NOT_RUN receipt |86119ae65|No real output seal or E111 inventory delivered; code-before-E109seal still requires that seal and actual timestamps. Source-readiness claim does not prove no prior E109 timing output.|

## E87 validator-corrected outcomes and E104 missingness audit — 2026-10-29 07:35 CET

Shared publication `b7fe68eb9`: corrected R-L1 `7c1330685`, depth `a3b427fda`, E104 audit `e091dd880`. Reviewed on arrival under §217. Strict E87/E104 scientific publications remain unchanged; no reviewer replay of any worker analysis, reparse or guard. E87 correction eligibility/raw-response recovery was already independently audited in8534628e0 and is not re-run here; the new statistical outputs below use those exact corrected records.

### E87 corrected R-L1 and depth

Exact analysis seal `59078bb2aaf90b8527c4fe8cf75d0f9b9205e809d7d7bc7e2c10b55b15f0ad53`; depth seal `4f79033cb3267a043582fbda7583348d83dc50dc1ac3e4292cb69197ecd2be94`. Verified all published result/figure hashes and corrected SPEC SHA `006a1051fe8e1dbe40299eb74ec06c8388f2fedbb9f015e90a1c8b8a409868c3` against analysis seal and retained guard, plus all5SPEC pins: corrected judgments `472117d6`, judgment seal `8da7b0f4`, same private join `50f135c4`, E76 table `cf3e671f`, E72 result `dff17f70`. The exact4500grouped judgment IDs join one-to-one to the unchanged original private identities/targets; each row retains30items, Oracle7layers×2arms and NLA42real. Original raw generation/placebo-vector custody remains as audited902d92c84; no new paid responses introduced by the correction.

Independently rejoined signed singleton-target scores, missing masks and first positions from raw corrected categories. Recomputed all10joint-layer/arm D bootstraps and140layer S bootstraps using `common.stats.bootstrap_ci`, 2000draws seed20261029; every point and endpoint agrees within1e-12. Unlike the strict sparse grid, all150intervals are finite under ordinary common.stats; no conditional removal of undefined draws is needed. All10NLA means and reported global/per-layer first-position medians also reproduce. Corrected missingness is403/4500:287/2100Oracle real,47/2100Oracle placebo,69/300NLA. Every Oracle real/placebo layer has at least14parseable items; this resolves the earlier zero-layer classification failure for this corrected grid, without making a missingness-robust population claim.

| Experiment | Rule / audit | Verdict | R-Q number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E87 corrected | R-L1 mandatory control gate | NOT EVALUABLE |LoopD=.05 CI[-.3259259259,.4217391304] fails>=.30;topicD=.9642857143 CI[.7857142857,1] passes |Same;NOT EVALUABLE |5b22f8aa8;7c1330685|Both controls must pass. A passing topic control alone is insufficient.|
| E87 corrected | R-L1 missed-row condition | NOT EVALUABLE (gate) |4/8D<=.10;required6/8;all10Dpoints/CIs match |4/8low;4/8high |7c1330685;59078bb2|Numerical condition is not met, but registered verdict remains NOT EVALUABLE because the control gate failed.|
| E87 corrected | Single-site-blind-spot falsifier | NOT EVALUABLE (gate) |4/8D>=.20;ungated count reaches4, but loopcontrol fails |Same gate-first disposition |5b22f8aa8;7c1330685|Do not label FALSIFIED from the ungated count. Seven-row sensitivity likewise gate-NOT EVALUABLE.|
| E87 corrected | nesting_depth descriptive classification | CONSUMED (reported threshold predicate met) |L28S=.20 CI[.0476190476,.375],n25,floor0;L44=-.05,n20;L52=0,n14;L56=.0588235294,n17;L60=0,n16 |Consumed |62e52f6a1;a3b427fda|Equality at.20 qualifies; later values are observed and below threshold. This is a descriptive point-threshold label, not a significant contrast proving consumption.|
| E87 corrected | var_type_at_use descriptive classification | LATE (reported threshold predicate met) |L52S=.3448275862 CI[.0689655172,.6071428571],n29,floor0;earlier20/28/36=0/0/.0833333333;L44=.0454545455 |Late |62e52f6a1;a3b427fda|OnlyL52qualifies on registered figure layers; seven-layer table retained.|
| E87 corrected | Other missed-row descriptive classifications | REPRODUCED |Persistent:container_after_move,user_expertise;Never:branch_taken,holder_after_handovers,indent_level;unit_system earlier+laterwithout44 outside-four |Same;controls additionally topic persistent/loop never |a3b427fda;4f79033c|All60figure-layer floors/counts and60first-mention medians match; no missing layer treated as observed below-threshold evidence.|
| E87 corrected | §220 audited input count | MET (descriptive trigger input only) |2/8missed rows consumed-or-late: nesting_depth andvar_type_at_use |Same two rows |7c1330685;a3b427fda|This corrects the earlier strict-input failure. E95 ownership/launch remains with its assigned integrator/reviewer; R-L1 is still NOT EVALUABLE.|
| E87 corrected | Correction/floor authority and source before corrected analysis | MET for retained first-output evidence |§22105:44:46;validator7170fe02805:54:10;floorauthorityee7ec683b06:48:09;floorcode+test62e52f6a106:48:59;correctedSPEC07:09:01.388819 < guard07:09:01.821964 <R-L1result07:09:01.822420 <depth07:09:01.939292 CET |Receipts first_output07:09:01CET,end07:09:02 |ee7ec683b;62e52f6a1;7c1330685;a3b427fda|Actual commit times precede both corrected statistical outputs. R-L1body remains5b22f8aa8; prior clarification3 and original grouped-seal chronology already closed. Strict outputs unchanged.|

Corrected missed-row D [95%CI], independently computed (worker identical):

| Row | D | CI95 |
|---|---:|---|
| container_after_move | .4642857143 | [.30,.6335] |
| holder_after_handovers | 0 | [-.10,.10] |
| branch_taken | -.0333333333 | [-.10,0] |
| var_type_at_use | .3103448276 | [.0387689191,.5517241379] |
| user_expertise | .5977011494 | [.4495530013,.8477011494] |
| unit_system | .6929392447 | [.5052230295,.9285714286] |
| nesting_depth | -.04 | [-.2948518519,.1348670635] |
| indent_level | -.0356321839 | [-.1666666667,.0666666667] |

### E104 §223 conditional audit: no eligible validator correction

Audit seal `d7418a9deb8cf9755c87a9501bd0b102d54493f343568070c23a30155d14b9eb`, strict judgment seal `ce564237b9951502478d26ab9c5bdcca3a8e3a7c90c0579660c76e4149cbf85b` unchanged. Independently verified audit/report/source members, every original strict judgment-seal member, private/blind bindings, all10missing IDs and their final attempt2wire/request/response hashes against the original sealed route audit. Rebuilt canonical request identities and exact judge-copy joins; inspected final HTTP200/finish-stop JSON responses directly. Independently applied the original punctuation/dash/whitespace/case normalization to evidence/readout strings. Nine non-silent `exhibits` codes have empty mandatory evidence; the remaining `states_value` quote is absent even after allowed normalization. None is the silent/extra-first-position defect authorized by §221. Two pure source-pinned validator tests independentlyPASS; no audit operator/reparse/analysis entry point invoked.

| E104 | §223 audit / conditional deviation1 eligibility | NO APPLICABLE DEFECT; corrected analysis NOT TRIGGERED |10/10exact final responses checked;9missing evidence,1nonverbatim evidence;0eligible silent recoveries |Same10/9/1/0 |e091dd880;d7418a9d|All remain missing under the frozen rubric. No scientific score/rule changed and no need to repeat the unchanged14bootstrap statistics.|
| E104 | Missingness reconciliation / strict R-U1 | NOT MET (strict result unchanged; sensitivity remains) |Languagealltest6steered/4random;registered steered-flipped cohort5steered/2random;factnone |Same |e091dd880;959cb0fca|Prior language extreme-completion reversal remains possible; do not call observed NOT MET missingness-robust or impute recovered silent scores.|
| E104 | §223 authorization before audit / correction chronology | Registration PRE-AUDIT; correction N/A |995a2e2cd06:19:18CET precedes audit delivery06:07:18Z=07:07:18CET;no reparse occurred |No correction/revalidation/analysisrerun |995a2e2cd;e091dd880|There is no affected corrected-output ordering to certify. Read-only audit source/report publication does not establish a separate pre-audit code commit.|

E111 source update `029f13bb7` actual07:02:30CET adds original standardized-probe feature-scale handling w/scale and .npz loading; intercept/feature-centering cancels in target-logit differences. All6updated receipt pins verified; the added scale-equivalence/invalid-scale synthetic testPASS (prior10tests unchanged). No E111 output or normalized inventory exists yet, so rule outcomes/data custody/pre-E109seal timing remain PENDING.

## Scheduled arrival check — 2026-10-29 08:00 CET: E109 falsifier implementation discrepancy

Shared snapshot `0d6cdf63a`. §217 owner/addressed HANDOFF sweep found the E109 redaction-sensitivity source `d8aae350e` (actual07:38:56CET), plus new E112 registration `ed2bc87b1` (actual07:51:24CET). No E109 statistical result seal is yet published. No unchanged E87/E104/E76 numerical audit was repeated. Parked work remains untouched.

**E109 source discrepancy requiring correction before the once-analysis:** BRIEF§222clarification1 (`995a2e2cd`, actual06:19:18CET) explicitly requires the NEW block44 Oracle difference “≥0.30 with lower bound >0”. Current `analysis.py::classify_rules`, byte-identical to `a0978104f`, checks the probe fraction and difference point only for the falsifier; it omits that lower-bound test and does not mark an absent CI unknown. The new redaction companion reuses the same function, so both outputs would inherit the omission. This is an explicit rule mismatch, not an ambiguous rule or worker interpretation.

| E109 | Falsifier lower-CI condition in current source | NOT MET (implementation audit); scientific outcome PENDING |Independent pure synthetic: both row probe fractions=.70, new44difference=.30, CI[-.10,.50] => current code falsifier MET(2passing), although no row meets lower>0 |Source returns MET |a0978104f;d8aae350e;995a2e2cd|Extracted only the pure classify_rules definition via AST; no real data, probe fit, adapter, guard or analysis entry point invoked. Require mandatory lower>0 and missing-CI handling in a minimal committed/tested fix before the once-analysis.|
| E109 | Redaction sensitivity source / primary preservation | SOURCE REVIEWED; outcome/order PENDING |Original analysis.py byte-identical; companion masks only affected scores on original paired cohort/grid, retains primary probe results; updated receipt pins exact |9synthetic tests claimed |d8aae350e|Local full pytest collection blocked by x86_64 sklearn binary on arm64 Python; no claim that nine tests independently passed. Independent falsifier regression above demonstrates the separate scientific condition omission. No source/results edited by R-Q.|
| E109 | Source/clarification before first timing/output | PENDING (ordering) |Reported timing/native COMPLETE locators exist in owner HANDOFF; exact shared hash-bound first-output inventory still not located |Owner reports production COMPLETEecaf7813 |995a2e2cd;0d6cdf63a|Do not infer pre-first-output from readiness or source-only publication; prior locator request remains open. The redaction companion is explicitly post-acquisition/pre-judgment, not wholly pre-output source.|

### E112 (§225) R-Q intake

Registration `ed2bc87b1`, actual **Oct29 07:51:24 CET** (heading08:00nominal). PCA-k ablation uses the existing E80c518-item mean/basis; smallest k removing at least the all518J variance share is frozen/committed onCPU before GPU. Existing none/J/random arms are reused. Oracle primary cohort is184none-pass items, with paired2000draw seed20261028 bootstrap of J-fall minus PCA-k-fall. R-X5 requires difference>=.10 and lower>0; falsifier PCA-kfall>=Jfall. NLA exploratory, per-family/norm/removed-variance reports required; bank≤3USD, CORE. The earlier E80c posthoc ratios are motivation only and do not alter R-X3.

| E112 | R-X5 / falsifier / reported controls | PENDING |No k-selection/source/output seal delivered on reviewed snapshot |Not available |ed2bc87b1|Verify smallest k from exact sealed518centered vectors, committed k/bytes before earliest GPU timing/output, fixed184cohort, raw family passes, paired common.stats bootstrap, actual n/missingness/norms and retained E80c source hashes.|

E111/E88new outcomes and E80cposthoc shared publication remain PENDING; previously reviewed results stand. New E85cap note is outside R-Qownership.

Pre-publication E112 source arrival: `5238d7f94`, actual07:58:40CET, all5receipt source pins exact. Independently ran8pure synthetic cases:8PASS; skipped the file-writing synthetic guard/tamper case. Source enforces518unique items/fixed184none-pass cohort, retainedJfall106/184, smallest-k inequality, original-arm reuse, and missing-new-judgment => NOT EVALUABLE without shrinking the confirmatory cohort. Numerical bootstrap convention is Python random.Random(seed20261028) with empirical sorted draws[50]/[1949], rather than common.stats' NumPy draw stream and interpolated quantiles; this is a disclosed implementation choice to compare against independent common.stats CIs when raw results arrive, not an invented post hoc rule. Exact projection vectors/k freeze, raw acquisition/scorer custody and pre-first-output ordering remain PENDING.

## E109 falsifier fix verified; located acquisition chronology — 2026-10-29 08:35 CET

Shared snapshot `466810eb6`. The omission reported in6f1a233c1 is **fixed in current source**, commit `c803e27af` actual **Oct29 08:22:58 CET**. One predicate now requires a present new44difference CI and lower>0, as995a2e2cd explicitly requires; primary and redaction companion share that same classify_rules function. No acquisition, score, probe or bootstrap definition changed. Current7source-receipt pins verified. Full pytest remains unavailable under the local sklearn architecture mismatch, so R-Q independently extracted only the pure rule function via AST and tested six cases without opening real judgments or invoking adapters/guards.

| E109 | Falsifier explicit lower-CI predicate | MET (source regression audit); scientific outcome PENDING |Probe.70/difference.30: lower-.10=>NOT MET;lower0=>NOT MET;lower.01=>MET;missingCI=>NOT EVALUABLE, in each row and pooled |Same4committed regression cases |c803e27af;995a2e2cd|Earlier implementation defect is historical, not current. R-Q independently also verifies a cross-row conjunction fails, while one complete qualifying row suffices. Six pure cases pass; no claim all13owner tests independently ran.|
| E109 | Fix before once-analysis / grouped-judgment seal | PENDING (ordering) |Fix committed08:22:58CET; no final E109statistical or judgment seal located on shared snapshot |Owner states guard unused/no judgments opened |c803e27af;466810eb6|Must compare actual seal/first analysis timestamps on arrival. Fix is post-acquisition; do not claim it predates E109native outputs.|

The full acquisition locator is present in shared owner HANDOFF (`understand/blind_judge/internals_c/HANDOFF.md`, Integrator06:18Z). R-Q has now followed it into `wt-wmech/cache/g_agreement/understand/analysis402_verified/E109`, closing the previously unlocated evidence for the **two retained timing/production runs**. Independently verified timing seal `f9c3b1ad27b9770c5aa00d7728fb8251c697e6cd7ff2370b26abdd172acbfcc2` and all144members; production seal `ecaf7813b2baa57d7c210423cd1ca09a1d388af566ab6eacbeeb5384e8838bde` and all428members. Both bind source `e20d86256df0782dc34b5a057cbf90e6b82a75dc8e8e836a02e500d3acf5fa10`, matching the shared runner seal and all168source pins. The earlier generic statement that no shared locator existed is superseded; the delivered HANDOFF locator plus exact sealed raw source is sufficient for this inspection.

| E109 | Registration / clarification1 before located first timing science output | MET for retained timing/production; complete earlier-attempt inventory unverified |Registration2d470093a05:55:29CET;originaladaptera0978104f06:02:28;runner/inputinventoryb8dae0db406:12:10;clarification995a2e2cd06:19:18;earliest retained capture mtimes06:25:44CET(second precision);sealed timing firstjob06:25:44.919933 |Timing seal firstoutput05:25:44.919933Z |995a2e2cd;b8dae0db4;f9c3b1ad|Clarification precedes capture/readout, including timing, rather than only production. No complete assertion about unlisted failed/discarded attempts.|
| E109 | Production / source custody timing | MET for located evidence |Earliest production capture mtime06:49:07CET;sealfirstjob06:49:07.377038;all428members/source168pins exact |Completeecaf7813;1008readouts reported |ecaf7813;b8dae0db4|This closes retained acquisition ordering, not full raw capture/item/probe normalization or1008readout scientific joins; those await bound analysis intake. Image/stack-digest absence remains disclosed, not invented.|

New E84clarification/E95ceiling amendments in the shared diff remain other-reviewer ownership. E112kfreeze/output, E111inventory/output, E88items5–6 and shared E80cposthoc publication remain PENDING. Prior completed outcomes were not recomputed.

## Scheduled arrivals — 2026-10-29 09:05 CET: E109 primary judging, E112 vectors, §226

Shared snapshot `997c62df4`. Reviewed only authoritative BRIEF/shared publications and exact bound raw sources; no operator entry point, actual guard, GPU or judging call. Unchanged completed numerical audits and parked work were not repeated.

### E109 primary judging custody / pre-seal fix

Public archive SHA `1b68e02ef41443c5c8c114dc759fee2d9a934a3db75dd47e28ffce15ae4d0f67`; receipt binds original phase seal `ef8ea43bbc18c581f03cf8e2eb5cae1d972ee23556b4b655215aa6f4ef442b70` and public phase seal `11eb80326413c0e9d8b1f7a0a0790fac6ea65860ef15936de0d268297b3a6d48`. Independently verified the archive, both seals and all1172public members. There are1008unique terminal judgment IDs:941KEPT,67UNPARSEABLE. One redacted opaque readout is retained with mandatory sensitivity. This is custody/missingness review, not a completed private-item/probe normalization or scientific score join.

| E109 | Falsifier fix before primary grouped judging seal | MET for primary bank |c803e27af08:22:58CET < original phase seal archived mtime08:47:47.329723CET; publicseal08:47:47.836032 |Same pre-seal fix requirement |c803e27af;E109_PRIMARY_JUDGING receipt|Closes primary bank-seal ordering. First paid judgment07:35:56.616693CET predates this fix, so no claim of fix-before-first-judgment or before opening. Analysis-first-output ordering still PENDING.|
| E109 | Primary judging n / missingness | MET (custody audit); rules PENDING |1008terminal IDs;941kept;67missing;1affected redacted readout |Same |11eb8032;ef8ea43b|No statistical result seal yet. Preserve missing and redaction masks; require bound raw/probe/test cohort normalization and original-judge sensitivity when delivered.|

### E112 minimal-k/vector audit

K_SELECTION `1451a11fd` actual07:56:08CET, SHA `5357620c`; vector delivery `071532656`08:33:12CET, vector seal `a356cc5a`. Independently verified original capture/basis/J hashes, all capture/vector/input seal members and input archive. Computed the eigenvalues of the518×518 centred Gram matrix independently, reproduced the cumulative variance spectrum and J-projected energy. k=1 is the smallest positive rank satisfying the registered inequality: J share=.14306092540200743; PC1 share=.19560713940769217, exceeding J by .05254621400568474. This is the specified smallest-k rule, not exact equality of variance shares.

Using the exact first column of sealed PCA384 with no refit/QR, independently reconstructed both site's float64 means and all1036saved float32 h−P1(h−mu_site) vectors. Every coordinate, mean, item ID/order and diagnostic norm ratio matches. Both arrays/basis/means are finite. Saved-vector Oracle removed variance=.19560714058477888; NLA exploratory=.1534146501666264. Norm-ratio ranges Oracle[.8204137083,1.0055780066],NLA[.8850440966,1.0048676072]. NLA uses the block44 PC1 with its own block42mean as explicitly disclosed; it does not become confirmatory.

| E112 | Smallest-k / all518 source projection | MET (CPU audit) |k1;J14.3060925402%;PC1 19.5607139408%;all518original IDs/order and1036saved vectors exact |k1;J14.3060925402%;PC1 19.5607139408% |1451a11fd;071532656|Differences only floating rounding <1e-12. No new PCA fit or reader execution by R-Q.|
| E112 | k/source before earliest GPU timing/output | PENDING (ordering) |Known committed k07:56:08/vector release08:33:12CET; no retained GPU output seal located in reviewed snapshot |Runner/vectors READY |1451a11fd;071532656|CPU bytes frozen and verified; compare against actual earliest timing/pilot output when published. R-X5/falsifier remain PENDING until sealed judged grid.|

### §226 additions: source intake, outcome PENDING

Coordinator registration `14e408dcf`, actual08:32:09CET (nominal08:50), adds R-Q's E111R-SL0, E113 and E100e. E114 belongs R-2; E98 baseline belongs its reviewer. E94 better-single-reader precision/base-rate display is now explicitly requested; earlier pooled H-A1 and its caveats remain unchanged.

| E111 | R-SL0 paired written-minus-carried | PENDING |Same two84-item rows; intersect E101/E104U steered flips; difference of four signed-score means;>=.20 and lower>0 on>=1row |New source8750154a3 actual08:40:39CET |14e408dcf;8750154a3|New contrast belongs to the same once-only E111run before regression, independent of vector availability. No real contrast computed before a sealed result. Five pure contrast synthetics PASS; per-cell missing denominators/undefined CI handling inspected; original regression functions unchanged.|
| E113 | R-IN1 / falsifier | PENDING |Three E57bookkeeping rows,3controls,84test items/row; dev logistic probes at every lens layer×activation/first-generated-token positions with5fold dev selection;testAUROC>=.90 on>=2/3bookkeeping rows;falsifier<=.65everylayer/position on>=2/3 pluscontrols>=.90 |No scoped source/result seal located |14e408dcf|Require dev/test identities, selected layer/position custody, retained captures, gates/n and registered test AUROCs; no new inference about absent state from an unsealed run.|
| E100e | Tracked-state transplant descriptive reading | PENDING |Container/holder84each;seed20261029same-row different-value donor;full h_donor;Oracle/NLA;E82two-candidate rubric;>=.30 vs<=.10 point readings |Source8750154a3 |14e408dcf;8750154a3|Separate guard/entry point preserves completed a/b. Three numerical/grid synthetics and one temporary-path-only guard synthetic PASS; no real guard touched. Original Bootstrap.stat/sample reused. No donor/result grid delivered yet.|

No new statistical outcome is asserted for these additions. E109 bank custody does not substitute for a sealed analysis, and CPU E112vector success does not establish any R-X5 effect.

Pre-publication arrival: §226 E94 trust baselines `c14190385` (08:59:17CET) reviewed immediately. Publication/report member hashes and both E94source pins match; the original pooled confusion/reader counts are unchanged. Independently recomputed all9displayed Wilson triples with common.stats (maximum endpoint difference3.50e-7 from z convention). Agreement precision943/1001=.9420579421; the better single reader **by precision** is NLA1389/1596=.8703007519, versus Oracle1442/1731=.8330444830. Descriptive precision gain is therefore **.0717571902 (7.18percentage points)**. The pooled correct-readout base rate is2831/8626=.3281938326. These use explicit mention/decisive-agreement denominators and do not replace the earlier registered H-A1 comparison against marginal accuracy. No paired significance claim for this new precision gain was registered or inferred. E98's companion baseline is other-reviewer ownership and is not signed off here.

| E94 | §226 better-single precision / correct-readout base rate | MET (descriptive report audit) |NLAprecision.8703007519;agreement.9420579421;gain.0717571902;base.3281938326;9Wilson triples reproduce |Same |c14190385;originalc33dc8ef|No numerical discrepancy beyond common z rounding. The original H-A1 met status is unchanged; do not present its .6077marginal-accuracy difference as this .07176precision gain.|

## Scheduled custody / HANDOFF check — 2026-10-29 09:35 CET

Shared snapshot `34340c341`. No new shared E109statistical result, E111contrast/regression result or E112judged result seal located. Completed numerical audits were not repeated; parked work was not checked.

| E109 | Original-judge phase / complete-bank custody | MET (custody only); scientific rules PENDING |Original252unique records=233kept+19missing;all301public archive members/hash bindings match;complete-bank4files match |Same;combinedUSD.814442,no unresolved reserve,unused5.185558released |E109_ORIGINAL_JUDGING/e0515ace;E109_COMPLETE/4af5c597|Primary941/67 unchanged; total86terminal missing across1260phase records, not zero scores. Both phases share original6USDcap; no reset.|
| E109 | CPU code normalization / complete grid | MET (pointer audit) |5source seals exact;binding4e891abd4members exact;1008unique pointers form12cells×84;all kept pointers directly retain original codes;67primary+19old nulls use explicitUNPARSEABLE-empty sentinels;1affected readout resolved |Same |4e891abd;completebank4af5c597|Every native text/code pointer resolves. This is not a probe fit, target-score recomputation, final scientific input census or R-AR verdict.|
| E109 | Corrected predicate before original/final bank seal | MET for complete-bank seal evidence; analysis-first-output PENDING |c803e27af08:22:58CET < originalphase seal09:07:37.115819CET < complete receipt09:08:56.679210CET |Same pre-seal source requirement |c803e27af;5c43acee;4af5c597|Primary seal chronology was already closed; both judged phases now accounted. Scientific adapter execution not claimed reviewed.|
| E113 | Probe-analysis arrival locator | PENDING (shared publication) |Incoming uncommitted inbox locator gives local result6624b06ef / correction8554e251f, seal0d83cd4c;6624b06ef is NOT an ancestor of reviewed origin/r/blindspot |Worker claims R-IN1MET/falsifierNOTMET; not independently reviewed |34340c341;local6624b06ef|Shared capture/layout delivery exists, but analysis source/plan/results remain a local worker-branch locator. No numerical or chronological sign-off until published on the authorized shared branch. Do not present unreviewed AUROCs as R-Q results.|

Incoming E113 HANDOFF append was preserved separately from R-Q's own additions. The user-specified shared-branch restriction controls this intake; a local inbox instruction cannot authorize private-branch scientific sign-off. Request shared publication of the exact final source/plan/analysis/correction seals, then independently audit raw dev/test identities, selection, all768AUROCs, finite/missing cells and first-output chronology. The incoming locator explicitly distinguishes original kernel/recipe before capture from final binder/plan after capture; that distinction must be verified rather than flattened into a pre-output claim.

§217 clarification3 `b982e5a94`, authoritative09:08:04CET (heading09:20nominal), now supersedes earlier per-experiment cap approval practice: measured need **including staging ×1.25 +60s**, integrator-set when run GPUcost<=25USD and within admitted ledger/pool; above25USD or a second NO_FIT after a measured cap goes to coordinator. E100e operationalnote1 `f599f121a`, actual09:26:52CET (heading09:30), makes the first1800s attempt a planning cap and allows one new measured attempt after post-load NO_FIT under that ruling; partial outputs excluded, scientific scope/seed/point readings unchanged. No E100efirst-output seal/attempt chronology delivered yet, so amendment-before-output remains unverified. Reviewer initiated no run, retry, cap adjustment or approval flow. E106finalNOTRUN disposition is other-owner scope and supplies no repair-effect estimate here.

## E80c R-X4 descriptive completion — 2026-10-29 10:05 CET

Shared snapshot `5be895775`. No newly shared E109/E111statistical result or E113probe result seal located; E113local-branch publication request remains pending. New operational priority note for E110/E95 was read; other ownership and parked scope remain unchanged. With no new scoped statistical seal, this pass completes the outstanding **R-X4 per-family/J-fraction/norm audit**, using the already sealed E80c output rather than recomputing the closed pooled R-X3 verdict.

Exact original SPEC_E80c matches analysis seal `b3b47069` and every input pin. Rejoined raw E80/E80c judged records/readout texts/private item IDs through the previously reviewed pinned family headline scorer; all518items/reader retained. For each of5families×2readers, independently rebuilt the none-pass complete-case cohort, all three ablation falls and both paired difference CIs with common.stats.bootstrap_ci(2000,seed20261028). All20point estimates match; worker interval endpoints independently reproduce under the committed Python-random/order-statistic convention. NumPy/linear-quantile endpoint differences reach .0294117647; **none changes a descriptive threshold label**. Oracle family cohorts sum184, NLA218; no new cohort exclusions. R-X4 has no separate confirmatory MET claim, and family labels below are descriptive applications of the R-X3 template.

| Experiment | Rule / audit | Verdict | R-Q number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E80c | R-X4 family/NLA descriptive audit | REPRODUCED (descriptive) |10family cohorts,30fall points,20paired difference points/CIs independently checked |Same points;all20committed-convention intervals exact |0b62a601c;7b8433cce|common.stats NumPy versus Python RNG/quantiles explains endpoint differences, max.0294117647; original pooled R-X3 NOT MET unchanged.|

Independent common.stats values below are J-minus-random and J-minus-PCA fall, each with CI95; worker points are identical, and worker interval differences are covered by the convention audit above.

| Reader / family | none-pass complete n | J−random [CI95] | J−PCA [CI95] | Descriptive template label |
|---|---:|---|---|---|
| oracle / association | 80 | 0.525000000 [0.412500000,0.637500000] | -0.425000000 [-0.537500000,-0.312500000] | NOT MET |
| oracle / chain_intermediates | 5 | 0.000000000 [-0.600000000,0.600000000] | -0.200000000 [-0.600000000,0.000000000] | FALSIFIED |
| oracle / multihop | 79 | 0.455696203 [0.341772152,0.569620253] | -0.455696203 [-0.582278481,-0.329113924] | NOT MET |
| oracle / multilingual_multihop | 9 | 0.777777778 [0.444444444,1.000000000] | 0.000000000 [0.000000000,0.000000000] | NOT MET |
| oracle / poetry | 11 | 0.272727273 [0.000000000,0.545454545] | -0.090909091 [-0.272727273,0.000000000] | NOT MET |
| nla / association | 85 | 0.329411765 [0.223529412,0.447058824] | -0.411764706 [-0.529411765,-0.294117647] | NOT MET |
| nla / chain_intermediates | 3 | 0.333333333 [0.000000000,1.000000000] | 0.000000000 [0.000000000,0.000000000] | NOT MET |
| nla / multihop | 66 | 0.227272727 [0.090909091,0.363636364] | -0.303030303 [-0.439393939,-0.166666667] | NOT MET |
| nla / multilingual_multihop | 30 | 0.766666667 [0.600000000,0.900000000] | -0.133333333 [-0.266666667,-0.033333333] | NOT MET |
| nla / poetry | 34 | 0.323529412 [0.147058824,0.500000000] | -0.529411765 [-0.676470588,-0.352941176] | NOT MET |

Oracle chain_intermediates has only5none-pass items and equal J/random fall=.8, satisfying the descriptive falsifier point condition; this does **not** falsify the pooled Oracle rule, whose registered falsifier was already NOT MET. No family meets the full J-specificity conjunction. NLA remains exploratory using block44basis at42.

Independently verified original E80c vector seal `9b61555d` and all5members, capture seal `25d02e88` and its arrays, plus original J basis `a8f4b64c`. Reconstructed each item's centred J-fraction with P_J(h−mu), then AUROC against the raw none-pass labels and conditional means. AUROCs match exactly: Oracle **.8057146576412393**, NLA **.7532568807339449**. Reconstructed pass/fail mean fractions: Oracle .1621093364614903/.12603999709483757; NLA .1638653110946440/.1316675226315174. Maximum per-item fraction difference from sealed diagnostics is6.32e-10. This closes a descriptive association check, not evidence that J-fraction causes reporting or a new accuracy gate.

Actual saved float32 ablation-vector norms were recomputed for all3108vectors; every >1.5 flag is0. Maximum difference from sealed per-item norm ratios is3.81e-8 (pre-save versus saved floating rounding). Actual range Oracle:J[.9293774051,.9938717757],random[.9743459638,.9988574853],PCA[.6500523604,.9124212790]; NLA:J[.9292435118,.9944939010],random[.9747313244,1.0081068841],PCA[.7074937655,1.0436024834]. Norm/J-fraction report is numerically reproduced; no scientific bytes or prior result were changed.

| E80c | R-X4 J-fraction versus none pass | REPRODUCED (descriptive) |518/reader;OracleAUROC.8057146576,NLA.7532568807;max fraction error6.32e-10 |Same AUROCs/means to floating rounding |0b62a601c;9b61555d|No newly fitted predictor or causal inference.|
| E80c | R-X4 saved norm ratios / >1.5 flags | REPRODUCED (descriptive) |3108vectors;0flags;maxNLA-PCA1.0436024834;max sealed-versus-saved drift3.81e-8 |0flags;max1.0436024970 |0b62a601c;9b61555d|Float-save rounding only; all conclusions unchanged.|

### E112 newly located native custody

A scoped owner HANDOFF reports output seal `40aee07e3ac5c32d771cbc6f1942f484c03f5db4152a90d42ce8586f20f4b411`. Followed to exact `wt-wmech/cache/g_agreement/understand/analysis402_verified/E112/prod/out`; verified seal and all139members. COUNTS gives518Oracle+518NLA=1036new PCA1readouts, zero none readouts, recapture=false; source `6be25882`, vector `a356cc5a`, original capture `25d02e88` match published identities. Earliest retained job mtime is **Oct29 08:48:15 CET**, second precision. k-selection1451a11fd07:56:08, analysis adapter5238d7f9407:58:40 and vector/source release07153265608:33:12 all precede that located native output. No explicit first_output field is in this seal: complete pilot/first-GPU-creation inventory remains unverified, so don't convert job-mtime ordering into a guarantee about all earlier attempts. Native COMPLETE is now located; judged-grid/R-X5/falsifier stay PENDING.

## §227 reviewer reassignment and E80c posthoc review — 2026-10-29 10:40 CET

Shared snapshot `5625800aa`. BRIEF§227 commit `a20f7adc0`, authoritative **Oct29 10:29:04 CET** (heading10:35nominal), explicitly reassigns **E112 to R-5 and E113 to R-4**. R-Q retains E109/E111/E100e and existing other scope. E113source/plan/results and descriptive position supplement are now shared, so the earlier shared-publication prerequisite is CLOSED; the numerical R-IN1/falsifier review belongs R-4. R-Q did not refit/retest, audit the768AUROCs or endorse the author's outcome. Prior E112vector/native-custody findings remain preserved as handoff evidence, not a sign-off on its future judged R-X5 result.

| E112 | R-X5 / falsifier future review | TRANSFERRED to R-5 |Prior R-QCPU k1/vector1036/norm and native139member audits closed; no judged effect reviewed |Owner reassignment explicit |a20f7adc0;priorc5d03c69a/dc51b6dfd|R-5 independently owns new outcomes; no repeated R-Q numerical review.|
| E113 | R-IN1 / falsifier numerical review | TRANSFERRED to R-4 |Shared result seal0d83cd4c/source/plan/position report now arrived; no R-QAUROC endorsement |AuthorMET/NOTMET remains an unreviewed author claim here |a20f7adc0;sharedprobes226|Local-publication objection superseded; preserve final-binder-after-capture provenance for R-4's review.|

§227 other operational rulings were read: W-mech2 may build E109SPEC/MEASUREMENTS if not published by11:00CET, then TrackQ verifies all hashes before guard; analogous E111CONTRAST fallback30minutes after E109analysisseal. Idle integrators may execute already committed/tested adapters once by frozen command for E108/E112/E100e; this grants **no reviewer execution authority**. C banks parallel, E112maymove toB on same route/cap; E110GPU fallback remains its owner's responsibility. Scientific estimands unchanged. E109 binding receipt now delivered (`E109_BINDING_RECEIPT.json`, SPEC6f66fa2b/outputseal01275a58/MEASUREMENTS4dfb778a); scientific result still PENDING, no reviewer adapter run.

### E80c §223 posthoc variance normalization, now shared

Publication `0500d162c`, plan/code `468bb1b16`; posthoc result seal/member hashes and **all33raw/source pins** independently verified. Original analysis/forecasts and R-X3 remain unchanged. Reconstructed cohorts from original sealed family judgments: Oracle184 and NLA218none-pass complete cases, full arrays518each, no extra missing exclusion. Independently rebuilt covariance-trace variance shares, re-centering within each resampled item draw, from original captures minus saved ablated vectors. Recomputed all28reported point/CI triples with common.stats.bootstrap_ci(2000,seed20261028), retaining paired item draws for falls, variance denominators and ratios/contrasts. All points match to<1e-8; every worker CI independently reproduces under its Python-random/order-statistic convention. NumPy/interpolated-quantile endpoint differences reach .1027412142 on normalized statistics, with no sign reversal of the J-minus-PCA comparisons.

| Experiment | Rule / descriptive audit | Verdict | R-Q number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|---|
| E80c | §223 variance-normalized posthoc audit | REPRODUCED (POST HOC / DESCRIPTIVE) |33pins,Oracle184/NLA218cohorts;28point/CI triples verified |Same points/cohorts |0500d162c;468bb1b16|Worker interval convention reproduced; common.stats endpoint differences disclosed below. No new decision rule or variance-matched causal intervention.|
| E80c | Oracle fall / variance-share ratio: J | DESCRIPTIVE |3.3381438055 CI[2.8891253157,3.7665094457] |3.3381438055;workerCI[2.8876,3.7783] |0500d162c|RNG/quantile convention only; original Jfall106/184unchanged.|
| E80c | Oracle ratio: random / PCA | DESCRIPTIVE |Random1.2732879931 CI[.7757963447,1.8380020140];PCA.9678087704 CI[.9404490018,.9896284441] |Same points;worker intervals reproduce |0500d162c|Use actual removed variance denominators, not rank labels.|
| E80c | Oracle normalized J−PCA | DESCRIPTIVE |2.3703350351 CI[1.9292922143,2.7984831468] |2.3703350351;workerCI[1.9189323845,2.8104556063] |0500d162c|Posthoc ratio contrast is positive; it does not overturn registered R-X3 NOT MET or prove an intervention slope.|
| E80c | NLA exploratory normalized comparison | DESCRIPTIVE |J2.8260330297,random1.6885857209,PCA1.0246241211;J−PCA1.8014089086 CI[1.4059508477,2.2020380264] |Same points;workerJ−PCACI[1.4074979357,2.2041806704] |0500d162c|Block44bases at42 exploratory; no NLA confirmatory claim.|

Full518Oracle variance shares remain J14.3061%/random7.7240%/PCA99.8015%; none-pass184shares J17.2577%/random7.6830%/PCA99.9569%. These condition on different samples and must not be interchanged. The ratios are computed after observing sealed results and do not establish variance-matched interventions or linear causal dependence; that separate confirmatory experiment is E112, now R-5owned.

Original kernel `9c2185cf4` committed06:25:09CET is byte-identical to shared analyze.py and precedes original result commit `4b2b0df1f`06:27:03, after §223authority995a2e2cd06:19:18. Shared rebased code/result commits468bb1b16/0500d162c both have10:27:55CET. A separately sealed earliest CPU-write timestamp was not supplied here: code-before-first-result-commit is verified; code-before-first-ever-write remains unverified. This limited provenance statement is distinct from the independently reproduced numbers. No author main/guard or previous E80c analysis was replayed.

## E109 sealed outcome independently reviewed — 2026-10-29 11:10 CET

Publication `8885bae79`, analysis seal **37ec586ce48d2a1e896362eb1d77e8316260ccd3a6a035a6650b6e3aacba349e**. Verified all result/binding/redaction-sensitivity members, SPEC/binding01275a58/MEASUREMENTS4dfb778a, original inventory and5source seals. Independently joined original sealed E56/E59 metadata hashes/IDs/labels, E104private495bbb19targets/steered-flip cohorts and original doses8/2. All168original dev and168test identities/splits match; original dev labels unchanged42/class. All1008native capture records retain exact original token lists and final read-token positions. All5040per-item×layer captured vectors match their60aggregated finite84×5120 arrays; no position or layer substitution.

Independent review used an available scientific Python3.12environment (sklearn1.9.1) to fit **ten new reviewer probes**, exactly C1/lbfgs/max_iter2000/random_state0, exclusively84unhooked dev items per row/layer. No worker adapter, guard or saved fitted model was invoked. Each was applied unchanged to the original84test items under unhooked/steered/random conditions and scored only on the original E104steered-flipped cohort84fact/50language. All30flip-count/Wilson triples reproduce. Raw categorical judgments were independently joined to frozen target letters; both/neither are0, UNPARSEABLE missing. All18S_steered/S_random/paired-difference bootstrap triples reproduce exactly with common.stats2000seed20261028, separate condition-specific missing denominators and paired sorted item resampling. No complete-pair deletion or missing-as-zero replacement.

| Experiment | Rule | R-Q verdict / number | Worker number | Commit checked | Discrepancy |
|---|---|---|---|---|---|
| E109 | R-AR1 arrival, fact_recall | MET: block52probe84/84=1,Wilson[.9562667347,1],DeltaS1.0 CI[.7857142857,1.1904761905];block60probe84/84,DeltaS.9642857143 CI[.75,1.1666666667] |Same;factMET |c803e27af;8885bae79;37ec586c|Both measured later reader layers independently meet conjunction; signed-score difference may exceed1 in a CI because its range is[-2,2].|
| E109 | R-AR1 arrival, language_plan | NOT MET: probe fractions44/48/52/56/60=7/50,4/50,10/50,9/50,9/50;later maxima.20<.70 despite DeltaS52=.4704545455 CI[.1893896674,.7424418605] and60=.3333333333 CI[.0782505930,.5839042496] |Same;languageNOTMET |8885bae79|No cross-row or cross-layer conjunction. Language S_steered at52=-.075 and60=-.5, so positive differences do not mean positive signed target reporting.|
| E109 | R-AR1 overall | MET: at least one qualifying row, fact at52and60;2/4later row-layer conjunctions pass |MET/2passing |8885bae79|No threshold relaxation or new row pooling.|
| E109 | R-AR2 decoder, descriptive | NOT MET both rows: block44probe0/84fact and7/50language below.70;original E10444differences.1785714286/.1444444444 remain <.30 |Same overall/per-row |8885bae79;original01d8d5a1|Correctly uses original E104difference, not new E10944difference.|
| E109 | R-AR3 never-at-site probe criterion, descriptive | MET for language: allfive fractions <.50 (maximum10/50=.20,Wilson[.1124362995,.3303737210]);NOTMETfact, whose52/56/60fractions1 |Same overall/per-row |8885bae79|This is the registered dev-fit linear-probe criterion on this cohort, not proof no state representation exists or that the model does not use it.|
| E109 | Account falsifier, each row / overall | NOT MET both/overall: new44DeltaSfact.1724039013 CI[.0764450660,.2738095238],language.1052048726 CI[-.0975948509,.2878172029];44probe0/.14 alsofails.70 |Same |995a2e2cd;c803e27af;8885bae79|Mandatory positive lower-bound condition retained; no pooling or old-E104 substitution.|
| E109 | Affected-readout sensitivity | UNCHANGED:1redacted readout lies outside registered flipped cohort;all18bootstrap triples and rule verdicts match primary |affected1/cohort0;sameverdicts |8885bae79;66b17e9d|Verified exact mapped affected identity against E104flip flags; no test/probe refit.|

### Achieved n, missingness and actual hook/norm observations

Every oracle row/layer/condition begins with84test readouts (1008total). Fixed analysis cohorts are84fact/50language; language's34non-flipped items are exclusions, not missing judgments. Fact has1missing steered44, none elsewhere. Language missing counts below are **cohort/all84**: at44steered7/8,random8/12;at52steered10/12,random6/11;at60steered8/13,random8/10. Thus the qualifying fact52/60comparisons have **zero missing**; the language contrasts retain substantial missingness and must not be presented as robust language reporting effects. Global67primarymissing reconciles to1fact+66language. The19old-rubric-phase missing records remain separate and are not substituted for primary scores.

All1008executed metadata records corroborate the intended hook: unhooked has no installed injection; steered/random writes exactly block40positions[read_index−8,read_index), with no read-token write; captures at44/48/52/56/60 preserve actual indices. On test items, fact has84/84steered and84/84random with at least one written-position norm ratio>1.5, maximum per-position ratios2.8323007202/2.8087716469. Language has0/84flags in both, maxima1.4130865698/1.3946529368. Every recorded read-site/layer ratio is<=1.5. These are per-position write norms, distinct from earlier concatenated-position diagnostics. The fact arrival effect is established in the registered alpha8setting with large write norms; no small-intervention generalization is inferred.

### Chronology and interpretation boundaries

Original §222registration2d470093a05:55:29CET, original adaptera09706:02:28, inventory/sourceb8dae06:12:10 and clarification995a2e2cd06:19:18 all precede earliest retained timing capture06:25:44CET; complete older failed/pilot inventory remains unverified as previously stated. Corrected falsifier source/testc803e27af08:22:58 precedes both judged phase seals; original code before first raw judgments is not claimed. Execution HEADcf55e32c9 committed10:44:18, byte-identical current7source receipt/dependencies; real guard mtime10:46:50.656680 <RESULTS10:46:51.015185 <ANALYSIS_SEAL10:46:51.317897CET. §227a20f7adc010:29:04 also precedes execution and changes no estimand. Published result8885bae79at10:47:58. Thus the previously pending corrected-source-before-analysis check is CLOSED for this retained execution. No claim of an earlier undocumented opening timestamp is inferred.

The result supports the registered **late arrival example for fact_recall**. It does not show the probe detects the target at44; it does not establish universal arrival across states or a decoder repair result. E101/E104null/large-norm findings, E87control-gated verdict and original E80cR-X3 remain unchanged. E111 is now eligible but its contrast/regression remains PENDING until its separately sealed once-only output; this reviewer performs no E111pre-analysis.


## 2026-10-29 11:35 CET — §217 arriving-bank custody / §228–229 intake

E100e descriptive part e — PENDING(sealed analysis/binding): own public terminal census336=334KEPT+2UNPARSEABLE plus84/84KEPT original comparison, matching published bank counts; all347primary/91original public sealed members and both archive hashes independently exact (0c9450ca/ec2ea7f6; complete receipt55008873). Non-kept primary codes remain null, not zero. This closes public judging-archive custody only; original donor/native/target normalization, gate and statistics await complete sealed analysis intake. No worker adapter/guard invoked. Bank settled0.23245975USD/reserve0, unused2.76754025 released from original3USD allocation; no reset.

E111 — PENDING(full sealed analysis): §227 contrast fallback locator62031a27/696f26c7 received as custody locator, not a scientific result or COMPLETE regression SPEC. E109 eligibility/seal time already established; no premature reviewer contrast/regression calculation, no repeated E109 fits/joins/statistics.

E117 R-IR1/falsifier — PENDING(source/directions/acquisition/analysis), new R-Q ownership under §22821be9c509 actual11:17:05CET. Three bookkeeping rows plus fact control, original84test each; E113 dev-selected layer48–60 and unit probe direction/gap frozen before output, three T/W/random arms at alpha1/2/4, hook every generated position from first answer token. Rule requires >=2/3 bookkeeping rows with T-minus-random>=.30/lower>0 and W<=0; falsifier <=.10 everyalpha on>=2/3 plus control movement>=.30; alpha degeneracy>20% excluded. Source/hook/tests/fresh-extract import, norm/degeneracy observations, frozen selection and authority-before-FIRST output remain unverified until publications. H200-by19CET/tested-runner launch condition is operational; reviewer never launches.

E109 §228 robustness supplement — PENDING(sealed new descriptive output), addition398b36052 actual11:17:54CET, after E111: language52 extreme missing-completion bounds, random Oracle52/60 beside random probe flips and52margin-vs-correctness AUROC. Original R-AR1/2/3 and independently completed18statistics unchanged; do not infer supplement results from registration or repeat closed primary audit.

E119 descriptive checkpoint comparison — PENDING(conditional exact Guiv checkpoint designation/capacity), §22915d35303e actual11:26:49CET. Exact repository/revision/subfolder must be human-designated and ungated, weights-only, H200 by19CET; otherwise operational NOT RUN. Fixed E109fact84 steered/random44/52 and E100a84each nesting/indent/page/fact; original rubrics, bank3USD/<=.5GPU-h. Pre-stated timing and >=2/3 bookkeeping readings are descriptive. No checkpoint inferred or source/network/GPU launch by reviewer.

Chronology: §228/itsaddition/§229 actual commit times above, then §229clarification1 0dd747c88 actual11:29:05CET (nominal11:55) fixes single H200 order E110→E117→E116→E95shards3-0/3-3→E119. First affected new outputs not yet hash-bound here, so pre-output ordering PENDING, not certified from headings. E115/E118 remainR5, E116R3, E112R5/E113R4 transfers preserved. Other closed audits and parked work not repeated.


## 2026-10-29 12:05 CET — §217 E111 amendment / E117–119 source intake

E111 R-SL0/R-SL1/R-SL2/falsifier — PENDING(sealed once-analysis); no real regression/contrast computed. Deviation1 067d0b7a9 actual11:41:44CET and note28176122611:43:13 are superseded by correctionb130c7679 actual11:45:04: include E100a through E105's registered same pairing, with original E100a Oracle y, donor-value dev-probe shift x1, sealed E105T flip x2; native unpatched same-item control has x1=x2=0 and donor-value-scored original readout. If E105flip seal or six-row probe lineage unavailable by12:45CET, exclude and disclose. No exclusion inferred before cutoff from missing current SPEC. Corrected adapter837852c3c actual11:50:23/8source-receipt pins independently exact; all17pure synthetic E111 tests PASS (12analysis/admission+5contrast) including missing-input deadline/full-scope admission and standardized feature equivalence. Scientific analysis kernels unchanged; admission now requires explicit boolean dispositions and zero natural-control flip. Current census_deviation1 may reflect superseded exclusion: final binding must implement correction, not inherit stale inventory as authority. Code/authority-before-FIRST E111 output remains PENDING until actual sealed run.

E117 R-IR1/falsifier — PENDING(outcomes), source-only review6e3b8f9d5 actual11:44:18CET: SOURCE_SEAL71db55e1 all172pins and sourcearchivec1b62594 exact. Three independently executed pure synthetic tests PASS: prefill untouched, every subsequent cached generated-token residual patched at chosen lens layer, T/W signs/dose and zero-delta identity, tuple tail preserved, exception cleanup. First answer token is selected from untouched prefill; hook acts on its residual when decoded and later positions, disclosed in metadata. Input loader checks336carriers/three equal-norm gap-scaled signed/control deltas, four84-item rows and frozen48–60selection references. No actual direction/selection provenance, executed norm traces/degeneracy or native output certification yet. Owner fresh-extract import PASS is a delivery receipt, not an independently repeated runtime model check. No GPU/model load by reviewer.

E119 descriptive — PENDING(smoke/capacity/outcomes), exact checkpoint prerequisite CLOSED by coordinator191ce2116 actual11:39:47CET: agu18dec/olens_and_ar@6ef38c85bc1096ea6e5b8e88e0c0c28cf6f9d30f/final_olens_lensB/lens_rl_step150. Frozen contract0c3f4fa33 actual11:52:34, sourceb2e7ed09 all174pins/archivea8c6907c and local467059228-byte weights SHA87e20f92 independently exact. Sixpure synthetic tests PASS: unit-normalized single-slot replacement at1000 with other embeddings unchanged, unique full-chat carrier/source layer, exact LoRA-prefix/buffer mapping, fixed read contract and nondegeneracy, production rejection without matching four-dev PASS. Source uses local_files_only/trust_remote_code=False and exact992LoRA parameter-set check; no remote repository code executed by reviewer. No real smoke seal present atffbc74556: do not convert CPU tests or weights custody into smoke success. H200/priority/19CET condition still applies; no reviewer launch.

E109robustness/E100e scientific outputs remain PENDING; E100e public bank custody already closed, no repeat. E112/R5,E113/R4,E115/E118R5,E116R3 preserved. E95 operational notes read solely as shared dated amendments; no R-Q scientific review or operator action. Closed numerical audits and parked checks not repeated.


## 2026-10-29 12:40 CET — E111 authorized recovery1 independently reviewed (§217/§224/§226)

E111 R-SL0 — MET, own/worker fact .32976306394027916 CI[.13972736124634866,.5189873417721517],79/84both-flipped; language .6603780140365506 CI[.292688336895654,1.0412242909749025],46/84both-flipped; recovered seal2deb3570, no numerical discrepancy. Independently reconstructed all168shared source-ID/target/four-cell joins and paired2000draw seed20261029 bootstrap, with a single RNG stream across fact then language, separate cell missing denominators. Cohort missing site-steered/site-random/carried-steered/carried-random: fact[1,0,0,0], language[19,7,5,2]. Language site-steered19/46 missing is substantial; passing observed contrast is not a missingness-robust claim.

E111 pooled R-SL1 — NOT MET, own/worker beta_site .044008456043 CI[.032990071738,.059045571736], beta_behaviour1.475315011630 CI[.788207611495,2.202685576123]; standardized magnitudes .933877/.720778, neither behaviour-CI-includes-zero nor site>=2×behaviour condition passes;2deb3570, max independently reproduced endpoint drift2.85e-10. Positive site coefficient alone does not satisfy the rule. All2000source-item cluster draws have finite identifiable fits; no dropped pooled draw.

E111 pooled falsifier — NOT MET, own/worker behaviour lower>0 but site CI excludes0;2deb3570, discrepancy none. R-SL2 descriptive models E104_U/E109_44/E101 — NOT EVALUABLE CIs, own/worker47/31/35 separation-or-singular-information bootstrap failures, respectively; point beta_site/beta_behaviour .25562946/2.19599327, .06665845/1.73495811, .05031789/1.19225441. Independently reproduced valid/failing draw counts and retained null CIs, without conditioning intervals on successful draws. E100a EXCLUDED by final authorized fallback, not a zero/missing-data effect.

Custody/normalization: all24bound source seals and799member hashes exact; public recovery output/CPU BINDING hashes exact. Independently resolved1008regression records:336each E101/E104_U/E109_44,945kept/63missing (32/10/21),zero vector-unavailable,336explicitly reconstructed E101vectors. All168source-item clusters contain six repeated experiment/control observations with one identical source-item ID/row per cluster; paired control references match. Block44/dev-only probe orientation and disjoint dev/test IDs verified; original coefficients/scales remain sealed, no refit. x1 independently reconstructed as donor-target signed raw probe shift; persisted E104/E109 and original E101 float32 reconstruction retained. E104natural baseline is the bound E109 unhooked44capture of the same original source inputs, disclosed in pre-output binding receipt, not an invented native readout. y is target-statement indicator after original frozen category/evidence validation, not signed S. Every cell-specific signed score remains separate in R-SL0. No author adapter/guard/analysis/figure entry point invoked; reviewer scripts used independent SciPy likelihood and resampling.

Chronology/deviations: final E100a exclusion f892e0466 actual12:12:53 supersedes the12:45wait and earlier inclusion correction: “E100a excluded: complete donor/control binding not sealed in time”. Failed committed executiond31b2397e12:18:45 < original guard12:18:53.061041; failure record at12:19:42.808547 describes missing matplotlib in first contrast.figure, after numerical computation but before any result write. Original output directory independently remains empty; original guard hash matches failure record. Original scientific functions contain no result-printing path and are byte-identical across failure/recovery. Recovery authority9cc5c4c5112:22:18 explicitly permits ONE separate recovery on unchanged inputs/rules/seeds; tested source8e7abc5d112:23:11 < separate RECOVERY1guard12:23:20.165344 <RESULTS12:23:26.885619 <seal12:23:27.079715CET. Exact MEASUREMENTS51cb980a/CONTRAST769b5b61 pre-output payloads unchanged; binding envelope/path hashes updated and disclosed(c63903a1→0e37a5d4), no assertion entire envelope byte-identical. Public failure7dd286df preserved;25pure tests PASS(21E111inclrecovery+4E117). No second recovery authorized; this is the sole saved scientific result. Complete older undocumented execution history remains uncertified.

## 2026-10-29 12:40 CET — E117 direction custody / new dated operational clarifications

E117 R-IR1/falsifier — PENDING(native/judged outcomes), published direction receipt8ccce381/input22532aef now independently reconstructed from original sealed E113 dev fits, without refit or E113test scoring. All four rows select layer48 by exact dev-AUROC tie/lowest-layer rule, selectedC=.01; raw coefficient/scale unit directions EXACT, positive class1 preserved. Gaps independently exact: nesting16.698189448558324,indent21.99013506825187,page4.897060245316498,fact9.44149672000454. All336original test carriers/order and1008float32 T/W/seed20261029 random delta vectors EXACT; matched input displacement norms follow frozen gap/alpha recipe. Original selection/FIT/model/dev-array/source/publication hashes verified. No model/fit/export/worker entrypoint run. Source f7d34a59f12:23:41 accepts frozen row-local0..83 slots while indexing arrays by unchanged list order; fourth synthetic regression passes, no input rewrite. Earlier pre-create allowlist hold was operational, not a scientific output; source-before-first-real-output remains PENDING until bound execution history.

E117 clarification8effe8888 actual12:27:12CET defines degeneracy: UNPARSEABLE/empty OR >=4consecutive identical generated IDs OR one ID>50%; repeated tokens alone do not count. Exclusion>20% is row×alpha pooled across three arms, applies all arms/rule/falsifier; per-arm fractions and descriptive S still reported. No executed degeneracy/outcomes yet. E100e inventory rulingebafaa393 actual12:23:26 permits reformatting ONLY pre-attempt2-first-output label/input/pairing fields with source times; missing source field→per-item descriptive only/no S. Inventory provenance must be independently reviewed BEFORE E100e guard; current inventory/result not yet delivered, request acknowledged in HANDOFF. E100e judging custody remains closed.

§23090965b84b actual12:17:02 assigns E120toR2 (not R-Q), replaces GPU order E110→E117→E120→E116→E95shard3-3→E119; no reviewer launch. E109robustness/E119smoke/E88items5–6 and remaining E76/E94extensions pending; parked/closed audits not repeated.


### E100e inventory arrival during publication — pre-guard provenance review

Inventory49d299c5/private168-recordfileed9aa338 independently verified on arrival: both sealed members exact, every source hash matches, all1008copied per-item fields(id,row,split,donor_id,original_value,target_value) match original LABELS directly. Git4b78bb97e actual09:22:14CET binds LABEL_SEAL24b4bb2a/publicINPUT_SEAL9b944aed before even attempt1/attempt2 creation, therefore before attempt2first output; reformatted inventory constructed12:31:53 is explicitly post-output. Seed20261029/readerblocks44/42 and pairing commit copied without RNG/new pairing. This certifies copied-field provenance, not full adapter admission.

Current seal explicitly retains intervention/pre_gpu_pairing_committed as MISSING. The pre-GPU pairing commitment itself IS evidenced by original Git binding/time; do not describe the pairings as uncommitted. Literal original condition is “transplant”; exact canonical intervention string/boolean are absent from allowed JSON fields. Under ruling “Each field is copied, not recomputed” and “If any required field has no pre-output source ... no S estimate”, current delivery admits descriptive readouts only, no S/guard claim. Coordinator clarification requested before treating faithful pre-output commit/time and condition as the adapter's canonical Boolean/string; reviewer does not invent them or silently adopt code as rule authority. E87gate pointers still await bound SPEC. No E100eanalysis/guard invoked.


## 2026-10-29 13:05 CET — §217 E100e amendment intake / E117 prospective adapter

E100e descriptive S — PENDING(corrected committed adapter/final binding/sealed analysis), NOT prohibited by missing metadata: authoritative amendment1 ba760009e actual12:56:29CET explicitly closes prior metadata-source question and supersedes no-S fallback. Intervention comes from pre-output §226 text; pre_gpu_pairing_committed=false is an explicit custody caveat, not an inferred true flag. Our earlier09:22:14Git check establishes commitment before the two located retained attempts, not complete proof before the FIRST GPU run; do not extend that evidence to all earlier history. Preserve historical audit and record coordinator's false disposition. S now permitted for container_after_move only. Holder gate .7142857143<.90 excludes it from S/rules; list its readouts descriptively. No new scores computed.

Current part_e.py still hard-requires pre_gpu_pairing_committed is True (line47) and both original E87gates>=.90(lines66–68), so source is not yet aligned with new amendment. This is a prospective implementation discrepancy, not a scientific NOT MET verdict. Minimal committed/tested admission/one-row changes requested BEFORE guard, preserving original a/b and holder descriptive listing; reviewer edits no source. New inventory_ruling_cpu seal/member provenance received, earlier168copied-field audit remains closed. Canonical amended inventory/gate pointers/finalSPEC must bind authority and retain false caveat, not silently rewrite history.

E117 R-IR1/falsifier — PENDING(native/judged outcomes). Prospective adapter0bcbda1f9 actual12:37:56CET/source receipt7pins exact; current runnerae233d08412:42:10/source94d34f28all172pins exact. Independently18synthetic tests PASS across runner+adapter: row-local-slot regression, whole pending-grid maximum observed call forecast with original staging/setup custody and1.25+60, category/token degeneracy edge cases, pooled row×alpha exclusion with descriptive retention, T/W/R signed comparison and falsifier. Source uses original generated token IDs; a repeated ID alone does not degenerate a readout. No eligible dose does not supply falsifier evidence. Source imports original E100Bootstrap2000/seed20261027; future review will independently compare common.stats and disclose convention differences, without silently altering registered science. Owner fresh-extract exact-input preflight PASS and unchanged hook recorded as custody receipts; reviewer did not replay acquisition or model load. Authority/adapter/source-before-FIRST affected real timing/output remains PENDING until sealed chronology. Closed E117direction vectors and E111/E109statistics not repeated; E119smoke/E109robustness still pending.


## 2026-10-29 13:35 CET — E100e amendment2 pre-guard source/binding review (§217/§226)

E100e descriptive analysis — PENDING(sealed once-result), prospective source discrepancy CLOSED. Authoritative amendment2 a7762b521 actual13:09:06CET permits only encoding map, false custody caveat and per-row gate. Current committed bda85497c actual13:18:11 (delivered equivalent finalsource2b47b7188) diff independently reviewed before guard: original inherited Bootstrap.sample/stat, DRAWS/SEED/readings/judge inputs and old a/b are unchanged; literal “h′ = h_donor at the read site” maps to canonical h_prime=h_donor, false retained with caveat, both original gates resolved before holder exclusion. Split holder metadata joins into original full168census; exclusion supplies no holder S. Owning-checkout Git path correction and split-record representation are custody plumbing, no changed selection/statistic. Four source pins/two dependency pins exact;7independent synthetics PASS, including temporary-path-only guard test, original bootstrap equivalence, false/literal admission, container-stat identity across gate exclusion, holder split references. Fresh git-archive CPU import independently PASS; no real-data adapter inputs/main/analyze or real guard invocation.

Exact SPECc67c06b2/binding9083f14d metadata independently reviewed: binding/5original source seals and71members exact;168items/336target-letter/code/native-text references match original donor targets/IDs,2missing judgments preserved. Original MANIFEST gate pointers independently resolve container .9075963718820862 and holder .7142857142857143; container S eligible/holder excluded. Amendment fields explicitly bind ba760authority and false caveat. Prior49d299inventory copied-field/pre-output-source audit remains closed. Fixed guard independently absent at this pre-guard review. Thus requested R-Q source diff/provenance review is complete; I5 remains sole authorized once operator, with original preflight checks mandatory. No extra reviewer permission/launch inferred. Holder per-item ID/readout lists remain CPU-side when publishing aggregate results, consistent with delivered publication contract.

§23104b97d69a actual13:14:50CET assigns E111partd toR-Q: POST HOC/EXPLORATORY matched read-site displacement/probe projection/logit-shift bins, site-vs-carried report rates. Await committed source/sealed output; original E111confirmatory rules/closed review unchanged, no premature real matching or history-knowing inference. Other §231E121/E118b→R5,E120c→R2 and §232E122→R2 remain outside R-Q. §232adapter ownership correctiona77885ae1actual13:22:35 read, not reviewer-execution authority.

§232addition2e3d957076 actual13:25:40CET explicitly permits E117/E122 acquisition before analysis-adapter commitment ONLY sealed/unopened outputs, no judging/scoring/peeking until committed synthetic-tested adapter BEFORE first opening. This overrides a generic before-first-output adapter requirement for these acquisitions only; E117adapter already committed12:37. Future review compares actual first opening/judging against adapter/tests and raw capture against frozen directions/runner, not falsely rejects authorized pre-adapter acquisition. No scoped new raw scientific output seal delivered at33959dad0. E119smoke/E109robustness/E88items5–6 and remaining extensions pending; no parked checks or closed numeric repeats.


## 2026-10-29 14:05 CET — E100e scientific review COMPLETE (§217/§226)

E100e container_after_move Oracle — descriptive point reading “blind spot covers tracked state too” (S<=.10), own/worker S=-.012195121951219513 CI[-.10717512908777968,.08536585365853659],82/84kept/2missing; originalseal3f6444ae/result0f77f0f8, discrepancy0. Counts donor-only+1=7,recipient-only−1=8,both/neither0=67; missing2 preserved, not0. Independently recomputed common.stats.bootstrap_ci over full84 sorted source-item census, nanmean per draw,2000/seed20261027; exact original interval. No new confirmatory MET/NOTMET rule or claim of equivalence/null proof.

E100e container NLA check — same descriptive <=.10 reading, own/worker S=.03571428571428571 CI[-.09523809523809523,.16666666666666666],84/84kept/0missing, counts+1=17,−1=14,0=53;3f6444ae, discrepancy0. Holder_after_handovers — EXCLUDED BY E87 GATE .7142857142857143<.90,84readouts per reader retained CPU-side, NOholderScomputed; container gate .9075963718820862 passes. Public aggregate projection omits holderIDs, matches original scores/CIs/caveat and descriptive counts exactly. Native/target/code/donor identity provenance already independently reviewed before guard; unchanged71source-member/336reference audit not rerun. Original output seal, private BINDING/result and public publication hashes independently exact. No author adapter/guard entrypoint replay; independent reviewer score validation and two common.stats intervals only.

Chronology: amendment1ba76012:56:29CET and amendment2a77613:09:06 < final reviewed sourcebda85497c13:18:11 < R-Qpre-guard review commit466e0ea0813:32:28 < executedHEADff991baab13:43:31(byte-identical reviewed part_e/rules/dependencies) < fixedguard13:44:52.872918 <RESULTS13:44:52.893686 <ANALYSIS_SEAL13:44:52.894166CET. Once-analysis ordering/reviewer-before-guard requirement CLOSED for retained execution. Actual first result write matches EXECUTION_RECEIPT nanosecond timestamp. Pairing sealed before attempt2first output but NOT committed before first GPU run remains explicit custody caveat/falseflag under authority; no chronology repair or first-GPU completeness claim. Old a/b/seeds/rubric unchanged. Bank .23245975USD already booked; analysis adds0GPU/0judge/0physicalcost.

## 2026-10-29 14:05 CET — new scoped preparation and operational intake

E111partd — PENDING(sealed exploratory output), prospective sourcee4767dc84actual13:34:09CET/9pins exact,4independent pure synthetics PASS. Geometry uses realised read44difference, target-signed effective raw probe dot product and dot/weight-norm projection; no refit. Source revalidates original inputs only, never original analyze/guard; separate part_dguard. Within-row pooled quintile boundaries separately for logit-shift and norm; ties collapsed, unmatched/zero-kept bins retained as unmatched, min(knownsite,knowncarried) overlap weighting. These are POSTHOC matching choices frozen before this calculation, not confirmatory thresholds or proof of intervention-history knowledge. No real-data feature/matching computation by reviewer before seal.

E123 R-DIS1(descriptive) — PENDING(source/capture/judging/analysis), new R-Q scope§2334615deb1eactual13:58:16CET. Fixed E109fact84/language50 cohorts and original44/52steered/random, plus268new unhooked readouts from sealed unhooked captures. Disagreement distinguishes different stated values or exactly-one-states; stale steered old-value44 vs unhooked, per-row AUROC>=.80/lower>.70 AND naturalFP<=.15 gives usable-flag reading;<=.60 not-usable reading, randomcontrol alongside. Literal global1008source-readout count does not enlarge fixed84/50cohorts. Preserve original item IDs and missingness; verify precise multi-value/absent-judgment handling against sealed source/authority on arrival, no invented missing-as-agreement. W-internals-B adapter/I2/WMCacquisition, <=.4GPU-h/judge3. E124R5/E122R2 unchanged. No reviewer launch.

E117 operatorcloseout A1B records205.010227GPU-s/.301251USD(up-to2.31all-in), terminal with NO scientific output seal and inaccessible diagnostic; receipt labels pre-load, cause UNKNOWN. This is not independently demonstrated model-load chronology or a scientific NOTRUN verdict. Unsealed readouts stay unopened/unused; fresh unchanged-source/input continuation is operator-owned, not reviewer replay. E119smoke source/input/cap launch receipt nowpublished but no SMOKE_SEAL/outcome supplied; do not call sixCPUtests actualsmokePASS. E109robustness/E88items5–6 and remaining E76/E94extensions pending; parked/closed audits not repeated.


E117 operational seal arrived during publication: PRELOAD2 OUTPUT_SEAL70c00934 is NO_FIT with completed setup163.550382s/warmup40.895302s/one8-itemcall21.301546s; this attempt reached science and is NOT a pre-load failure despite run-name. No partial readout content opened/scored. Operatorcloseout410.232491GPU-s/.602814USD(up-to2.61all-in), distinct from earlier205s unsealed failure. Measured-reattemptreceipt uses original396calls/3024readouts, staging453.621612, ceil(1.25×[staging+setup+warmup+396×maxcall]+60)=11427s,<=25USD, same94d34f28source/22532aefinput and priorpartials8excluded/no stitching. Receipt states direct coordinator one-measured-reattempt authority; reviewer does not launch/rearm. Operational chronology/control only, full production/native/judged outcomes PENDING. No first-output wallclock inferred from duration-only phase log.


## 2026-10-29 14:40 CET — E119 smoke gate CLOSED / E123 prospective source review (§217/§229/§233)

E119 — NOT RUN(operational), own/worker smoke gate fails1/4dev items (3pass), seal7043047d; production not launched, no scientific lens-B verdict. Independently hash-verified original smoke seal and all3public members LOAD_AUDIT/READOUTS/TIMINGS; private ASSIGNMENT omission is explicit in public projection, not falsely claimed public/full custody. Independently reproduced frozen nondegeneracy: all4have128tokens; distinct-letter-word counts[2,2,36,25], maximum identical-token runs[63,1,2,1] against allowed<=15. First item fails despite two words; gate requires all4. No rerun/model/judging. Original first retained output14:00:34.478302CET per preserved worker-mtime projection, after named checkpoint authority191ce11:39:47/source0c3f11:52:34 and reviewed contract93e05924; exact source/input/weights hashes preserved.

E119 note1 8eae8a437actual14:19:44CET allowed only a specifically identified README-contract correction by15:15. Published audit completed14:23:58 found no specific scale/slot/prompt/layer/base mismatch, then standing authority83747fe28actual14:28:33 explicitly closes E119 NOT RUN. Do not leave smoke pending, propose speculative retry, or infer scientific inability of lens B. Source-audit/readme-mismatch conclusion is a bounded five-field operational audit, not runtime-stack equivalence. Existing source/weight tests are not substituted for actual gate failure. Cost3.66USDupper booked once per closeout; no reviewer launch/retry.

E123 R-DIS1 — PENDING(raw COMPLETE scientific outputs), source931adc12d/receipt29b4e8c3:7source pins/2dependencies exact,15independent pure synthetics PASS. Fixed84fact/50language, allthreeconditions×44/52, original value-set disagreement (both no-mention agree; exactly one/different sets disagree), UNPARSEABLEpair missing, stale old-only singleton, joint source-item resampling and randomcontrol confirmed source-only. No real E123join/statistic/guard replay.

E123 bootstrap implementation concern: summarize() drops undefined AUROC draws, then evaluates the conditional CI as if unconditional registered item-bootstrap CI. Independent synthetic84items with only1stale positive and perfectly separating binary score gives AUROC1 CI[1,1], R-DIS1 MET while736/2000draws are undefined (1264kept). This is a finite-draw-conditional interval, not an ordinary full common.stats interval. No real outcome evaluated. Requested pre-guard source/authority disposition: retain undefined draws as non-evaluable CI, or explicitly register/label a conditional interval; never silently certify it as the original CI. Registered words “stale ... block-44 readout states the old value” also do not expressly specify old+new dual-value cases; code chooses exclusive singleton old. Record prospective ambiguity and seek coordinator clarification before any affected positive-cohort use, rather than treating synthetic tests/worker explanation as rule authority.

E117 final full-grid authority9ab9c980d actual14:16:22CET permits one final attempt min15600s/25USD, prior24partials unopened/excluded, furtherNOFIT→operationalNOTRUN. This supersedes a blanket second-failure stop for this experiment only; no reviewerlaunch. §234standing measured-cap authority83747fe28actual14:28:33 covers E116/E120a-b-c/E121/E123/E125: one measuredattempt afterNOFIT,max(measuredneed×1.25+60,latestforecast×1.25),<=25USD,priorpartialsunopened,19CET/GPUceilingunchanged. E125R4/E124R5/E122R2 remain otherownership. §231 E111dclarification1 read: natural44 is control, steered primary/random separate reference; current source uses paired original baseline. Await sealed posthocoutput, no early real matching. Other closed numerical audits/parkedwork not repeated.


## 2026-10-29 15:05 CET — §217 quiet arrival check / §235 scope intake

No new scoped E117/E123/E111d/E109robustness scientific result seal at36c81d1c7. E123conditional-CI/dual-value cohort questions remain unresolved by canonical BRIEF; no duplicate request, real-data opening/statistic or source-test repeat. E119/E100e/E111/E109 closed reviews preserved. E117final15600/TrackQ-E123 launch owner receipts are operational status, not completed evidence. C is sole E123judging owner, B adapter only; no reviewer launch, duplicate dispatcher or guard action.

E126 R-MED1 — PENDING(source/frozen inputs/capture/analysis), new R-Q ownership§235ad272577bactual14:41:16CET. Original E10984fact/50language flipped cohorts, U40eightprecedingpositions alpha8/2, unhooked/steered residuals at44/48/52/56/60. Restore clean read-token vector under steer; insert steered vector without steer. Controls perlayer random nonsteered earlier token and norm-matched read-token perturbation. Frozen E104continuation log-odds, item restoration fractions and rawlogits/insertion reported. Confirmatory fact medianR52or56>=.50/lower>.25, whileR44/control<=.15; falsifierR<=.15atallLwithlowcontrols. Source must preserve original item/direction/target alignment and report denominator/undefined cases rather than invent outcome-dependent exclusions. No reader calls; <=.4GPU-h,TrackQ/WMC/Badapter. Beforeoutput/source/selection and actual executed patch-only sites remain unverified until seals. Newpriority E117→E121→E120→E123→E126→E116→E125, standing measured-attempt/cutoff rules unchanged.

E117partc — PENDING(source/capture/judging/analysis), samead272577b: block44bookkeepingnesting/indent/page84each plus factcontrol, targetedvalue question and absent-factsham, originalE57rubric, bankE117additional<=2USD/<=.15GPU-h. TargetedS>=.30on>=2/3rows withshamyes<=.20 gives descriptive elicitation reading;<=.10allthree not-recoverable-by-asking reading. Newprompt/arm signatures, shamquestion/yes-denominator mapping and frozen rubric must be source-bound before outputs. No source preparation/real question answering/reviewerscoring inferred from design. E111d owner ACK of natural44control/steeredprimary/randomseparate received; corrected source/output still pending. Other owners' E120/E121/E122/E124/E125 outcomes not reviewed by R-Q; parked work not checked.


## 2026-10-29 15:40 CET — E126/E117c prospective source and packet review (§217/§228/§235)

E126 R-MED1/falsifier — PENDING(real sealed logits/outcome), source cb92ec6a(all173pins exact)/CPUadapter901dea83e(receipt7pins+originalE105/common/core). Independently50combined pure tests PASS across E126hook/analysis and E117cconfig/analysis. E126 hook tests cover all5blocks×restore/insert: decoder-output replacement at exact read position, U40eightprevioussites only for restore, none for insert, earliercontrol outside eightUpositions/readtoken, randomread perturbation norm matched to live primary displacement, full continuation scorer keeps original read index instead of last appended token, immutable payloads/tuple outputs/cleanup after failure. No real model/forward/logits run by reviewer. Runtime dtype/postcast norm tolerances and executed hook counts remain PENDING on raw arrival.

E126 packet694164fb independently verified allsealedmembers and original134IDs(84fact/50language)/tokenprefix/readindex/candidatepairs/Udeltas against bound original E104parentinputs. All1340clean/steered layer vectors match exact E109production arrays; all1340SHA256-keyed random-unit vectors/earlierpositions reproduce seed20261029/opaqueID/block/direction recipe exactly. Source earliercontrol uses same replacement vector at earlier nonsteered token; randomcontrol norm uses actual live read-token replacement displacement. No new selection/RNGcohort or baselines computed. Fixed4020patchcells/zero baselinejobs; true original clean/steered numerical baseline bindings still require COMPLETE source pointers for CPUanalysis.

E126 controls clarificatione9c1bd24f actual15:09:28CET precedes CPUadapter901dea15:15:46/hook04975715:16:36: BOTHrestorationcontrols medians<=.15 atALL5blocks; insertion descriptive only. Adapter independently matches fact-only R-MED1, OR52/56median>=.50/lower>.25, R44low/allcontrols low; language cannot promote confirmatory verdict. Ratios formed per-item before median/common.stats.bootstrap2000 with originalE105seed; no clipping/epsilon/winsorization/ratioofmeans. Exact-zero gaps retained undefined, affectedmedian/ruleNE without cohortshrink. No first real output/opening yet certified; source-before-science/authority-before-output chronology PENDING.

E117c — PENDING(real native/judged result), source9pins exact; targeted/sham rows/questions reproduce e9c1bd24f perqualifying-row sham<=.20 and factcontrol “What fact is being recalled?” without supplying answer. Prompt config1389b2a02actual15:19:49; originalE57signedscore and leading yes/no extraction, explicit missing denominators, factsham cannot rescue bookkeepingrow verified source-only. However readings() adds target_missing==0 and sham_missing==0 as prerequisites beyond the stated point thresholds. Independent synthetic4×84items with each bookkeepingtargetedS=1(83known/1missing),shamyes=0(84known), returns elicitationNOT EVALUABLE for all3 although allcomputedpointcriteria pass. No real scores. Requested pre-output authority/source disposition: evaluate registered S/rate thresholds with explicit missingness/sensitivity, or explicitly authorize complete-judgment gating; no silent new full-response requirement. Tests passing are not scientific rule authority. E123questions remain unchanged/unresolved, not repeated.

No new scoped scientificanalysisseal; E100e/E119/E111/E109closed audits unchanged. ForeignuntrackedE126HANDOFF initially blockedpull: namedstash7cebf9d187 retained; saved4421bytes are fully preserved as ordered original lines within nowlonger publishedHANDOFF(no insert/replace-only foreigndelta), no reapply required. TwoforeignHANDOFFappends separately retained outside reviewercommits. Parked/otherreviewers' outcomes not checked.


### §236 arrived during publication — schedule and additional R-Q scope

Authoritative§2362ebe22138actual15:30:44CET and clarificationd3580e85515:33:37 supersede earlier operational deadlines: all registered creation cutoffs04:00CETFri30Oct, pods stopped/sealed08:00(stage-complete exception), analysis/review seal10:00CET or Neelmeetingminus2h ifearlier; laterresults appendixlate/unreviewed. Clarification3 explicitly extends reviewerheartbeats includingR-Q beyond06:00to reviewseal. Monitor is therefore updated to10:00CET maximum, retaining earlier-stop condition when meetingtime is published; exact meetingtime not located in canonical schedule. Scientific rules/budgets/caps unchanged. H200order is contended-stock priority, not blockingqueue: E117running→E126running→E127→E117c→E125→E128; source-ready rehearsed E117c may launch before unreadyE127. No reviewerlaunch.

E127 R-NAT1/falsifier — PENDING(source/seals), newR-Qscope§236. All84originalfacttest, E104newtarget whereavailable else same-relationdifferentvalue seed20261030; context-update/neutral-template-length/unprefixedconditions, NOhooks. Greedy3tokenanswers and Oracle44/52/60 produce756readouts. Flipped=updateanswersnew AND unprefixedanswersold; if<50 descriptiveonly. Onsameflippedcohort, old44rate>=.50/Wilsonlower>.35 ANDnew60>=.70 ANDneutral44old>=.80 supportregisteredstalenessrule; new44>=.70/Wilsonlower>.55 falsifies. Neutral must use SAMEflippedset perclarification1;all84condition/blockratesdescriptivebeside. Originalprefix/target/answerparsing/rubric/identity/source-before-capture evidenceawaited; nooutcome-dependentreprefixing orreviewergreedyread.

E128 R-DOSE1(descriptive) — PENDING(source/seals), newR-Qscope§236. Original40eightpre-readclassmeansteer/fact84 atalpha2/4 plussealed8, greedyanswers/Oracle44/52/randommatchedcontrol. Smallestdose2/4/8with>=42/84flipsselectedbyregisteredtest rule;onflippedcohort old44>=.50/Wilsonlower>.35 andnew52>=.70 givesdescriptiveweak-dosepersistence. Ifneither2nor4qualifies,strong-steer caveat/dosequestionremainsopen. Structured336newreadouts plusmatchedrandomarm mustbeexplicitlybound/countedinactualgrid;do not silentlyomitcontrolsorborrowE104devselectionrule. Authority/source-before-FIRSTnewaffectedoutput PENDING.


Publication-time §236deviations1 read: E117c planning .15GPU-h superseded by explicit5400s<=8USD measured cap, hardstopmin(cap,06:50Z); same672items/questions/sham/rules. No prospectivecap rejectionusingoldplanningfigure. E125label-blindTESTspacecheckdeviation belongsR4;noR-Qtest/probe/scientificreview. E117c native/source-before-firstoutput remainsPENDING.


## 2026-10-29 16:15 CET — E117c missingness finding RESOLVED / E127–128 prospective custody (§217/§236)

E117c source-completeness discrepancy CLOSED by authoritativeclarifications2 8e7b77506actual15:40:58CET and implementation181d60d14actual15:58:39. Observed-response rates permitted iff BOTH targeted and sham>=79/84observed; fewer→rowNE. Worst targetedS=(observedsum−missing)/84, worstshamyes=(observedyes+missing)/84; pointpass/worstfail explicitly “met, not robust to missingness”. Source9pins exact and changed predicates independently reviewed: complete-response requirement removed, perqualifyingrow sham retained, no newCI gate; invalid row cannot be rescued by factcontrol/pooledsham. Combined45pure tests PASS(E117cupdated/E127runner/E128runner/E127-128rules+transport), using importlib collection after defaulttestbasenamecollision; no independent PASS claimed for failed initialcollection. No real E117c output/analysis/guard invoked. Scientificoutcome remainsPENDING, prior defect historical not current.

E117c measured-attempt deviationd9dfcce9d actual15:51:56CET: initial5400planningNOFIT d940a49f(load431s vs166), one6889s<=10.12USD measuredattempt; furtherNOFIToperationalNOTRUN. No reviewerretry/capincrease. E126 measured-attemptclarification8e7b15:40:58 explicitly discards firstbatchwarmup and admits onmaxNEXT3batches×1.25+60,<=25USD/06:50Z; fulloriginalcells/control/rules unchanged. Actual custody/first-output chronology still await bound operationalrecords. Standingpush approval changes no reviewerwriteownership/privacychecks.

E127 R-NAT1/falsifier — PENDING(real captures/classifier/judging/analysis). Sourcef5fa22316actual15:48:03/175pins exact; CPUadapterc2cfa24b8actual15:43:39/9sourcepins exact; packet964b5fc3/inputarchivea026b03b/labelseal549fa110 independently exact. All84frozen E104old/newtargets match sealed originals(fallback0); all252conditionprompts retain exact original suffix/tokenpairs/finalreadindex; update/neutralfulltokenlengths equal, neutralentitydiffers/newvaluenotleakedasneutralvalue. Source E109naturalcapture is isolated44/52/60 with nohook; greedy3token sequentialargmax/EOS source-only tests pass. Matchedneutralcontroluses identicalbehaviour-flippedcohort; flipped>=50gate/all84descriptive/strictWilsonLBrules and separate fixedguard verified. No real greedyanswer/readout opened or classified. Frozen CPUold/new/other greedyclassifier and exact native→code/identitybinding still missing from prospective delivery; do not inferflipfromOracle or pair-logit preference.

E128 R-DOSE1(descriptive) — PENDING(real captures/classifier/judging/analysis). Sourceb82dbb52factual15:57:59/180pins exact; adapterc2cfa24b8/6sourcepins exact, packet7e911f65/archive5d901014 independently exact. All336dose×condition inputIDs/tokenprefixes/candidatepairs and composedsteered/randomdeltas exactly originalalpha8scaled.25/.5, no new direction/draw; grid explicitly336structured+336randomOracle44/52readouts. U40onlyeightprevioussites/readcapture44/52/sourcegreedy3tokens verified synthetic; no actualpostcast/norm/execution claim. Smallest2/4/8bybehaviour>=42/84 only, missing-lower-dose ambiguity→NE, same steered-flippedcohortforrandom, lowerdosefailurekeepsstrong-steercaveat. Original8flags are reused E104continuation-preference measurements, while new2/4runner emits greedy3tokens. Pendingclassifier/authoritymust explicitly preserve that provenance; do not describe original8flags as newlyverifiedfree-greedyanswers or silently equate the two measures. This does not change the pre-stated lowerdose selection threshold.

E123conditionalCI/dual-value questions remain unresolved and are not reissued; E111d/E109robustness/E117mainresults unsealedpending. E79Bnew3USDjudgingallocation acknowledged operationally only; no parked extension review/reactivation inferred or worker entrypoint launched. Closed numeric audits unchanged.


## 2026-10-29 16:45 CET — §217 arriving native seals / §236 frozen greedy classifier

E117 main scientific R-IR1/falsifier — PENDING(judging/analysis); native custody COMPLETE at shared d587c2e7d. Independently verified public archive da066a0c, OUTPUT_SEAL44aadc42 and all400 public bound members exact; the401st original member ASSIGNMENT is explicitly omitted/hash-disclosed, not claimed publicly available. Source94d34f28/input22532aef match frozen delivery. First retained job hash b7f3d7a7 and nanosecondmtime evidence13:29:49.585306Z(14:29:49CET) follow frozen source/adapter and final-attempt authority; this is retained-file timing evidence, not certification of all prior attempts. Prior24 partial readouts remain excluded. No readout text/token metrics/norms/scientific scores inspected; original generated-token accounting request remains pending owner binding of generation_config/kwargs and EOS padding before degeneracy scoring. No R-IR1 verdict from native completion.

E117c scientific elicitation readings — PENDING(judging/analysis); sealed COMPLETE9dd48b68 at delivered CPU locator, all94 bound members exact plus seal. Source d7d3e2c/input5d24a41d bound, first-output evidence jobs/000000 hash2a143733/15:14:18.111397Z(16:14:18CET) follows missingnessauthority8e7b15:40:58 and testedfix181d15:58:39CET. Duration/identity/result fields not inferred from folder name; no readout opening/scoring or guard replay. Original NOFIT attempt excluded, no stitching. Native completion does not determine point thresholds or worstcase sensitivity.

E127/E128 greedy-classifier prerequisite CLOSED prospectively: authoritative clarification4 c271590cb actual16:31:26CET (nominal16:40) expressly corrects E104-text-scorer pointer. C source8d1b4e135 + B cf95b1d93 actual16:37:35 use unchanged core.parse_target_answer cf6bc5ed, case-insensitive whole-candidate exclusive matching; both/neither/empty decoded answer are neither/other naming aliases, missing acquisition separate. Independent54 pure synthetic tests PASS across Cclassifier/candidates and Bclassifier/transport/E128rules;8 B receipt pins/13 dependency entries exact. Candidate seal d0de9a50/private d923d940 exact; all588 CPU-only candidate cells join84 sealed originals with exact old/new strings, no new aliases or real answer classification. Original input packets unchanged; closed prior prompt/vector packet audits not repeated. Native/judgment bindings/first-opening provenance and scientific outcomes remain PENDING.

E128 alpha8 provenance resolution: B transport now leaves original unavailable greedy8 as missing, preserves original pair-preference flags separately/descriptively; it cannot silently select a greedy8 cohort/alpha_min. Lower-dose2/4 greedy qualifying results remain evaluable; absent lower qualification leaves strong-steer/dose question open. No alpha8 generation/replay authorized. E127 same-flipped neutral control unchanged. No worker scientific interpretation used as rule authority.

§236clarifications3 5d5baf921actual16:30:01 confirms E118b/E121 R5, E107companion R2; delivery addressed toRQ does not transfer ownership. Clarif4 and posthocE107reportingnote1 ac281d58c read; no other-owner result review. E123 questions unchanged/unresolved, E111d/E109robustness unsealed pending, no duplicate requests. Reviewseal10CETFri/09Z or Neelminus2h earlier remains; canonical meeting time still absent.


Publication-time canonical clarification5 c893cac6f actual16:41:16CET(nominal16:45) ACK: E128 alpha_min is ONLY smaller qualifying greedy dose2/4 (>=42/84); no greedy8 needed/imputed. If neither lowerdosequalifies, report “flip needs8” ONLY as E104sealedpair-logit84/84 DIFFERENT-MEASURE reading, retainstrong-steercaveat. This supersedes original2/4/8greedyselection wording and authorizes explicitdifferent-measure fallback, without creatinggreedy8cohort/readerstatistics. CurrentBmissinggreedy8 representation respects this distinction; actual sealed outcome pending.


## Direct Guiv E127 priority / schedule amendments2–3 intake

E127 is first-priority arriving-seal review ahead of queued work. At shared5c1b5a32c finalSPEC/ANALYSIS_SEAL/RESULTS unshared, so R-NAT1/falsifier remainPENDING; no independentreal-dataflippedcount/conditionclassification performed. On arrival reproduceoriginal84conditionidentityjoins, greedyflippedcountFIRST and under50descriptive-onlygate, old44/new60 R-NAT1, new44falsifier, SAMEflippedsetneutral44control; reportall84beside. Prospectiveclassifier/label/sourcechecksclosed, do not repeat them unchanged. No revieweroperatorentrypoint/guard.

Authoritative schedule amendmentsafeb56712/0e91a0ce4 supersedeearlierstop: reviewFri30Oct18CET/17Z; NeelmeetingSunday. PodscreatedbyFri11CET, stoppedsealed14CET/hardstopmin(cap,12:50Z); newrunsBRIEFcommitted08CET; slidefreeze21CET/submission23:30/deadline24CET. All16activesprintheartbeats updated viaapp preservingfrequency/scope. Scientificrules/caps/ceiling/custody unchanged. Other-owner§228E116exploratory/E120bwording amendmentread, notR-Qnumericallyreviewed.


## 2026-10-29 — E123 clarification1 / shared legacy numerical sign-offs

Authoritative3ba3c0c6d actual17:08:29CET(heading17:25nominal) resolves BOTH E123 prospective questions. Undefined AUROC resamples are counted/reported; percentileCI uses defined draws and is labelled “conditional on defined draws (k of2000)”; R-DIS1 evaluable iff k>=1900/2000, otherwiseNE with pointdescriptive. Primary stale is exclusiveOLD; dualOLD+NEW is a separatelyreportedcategory and secondarysensitivitycountsdualstale; primaryverdictunchanged. The former methodological ambiguity is CLOSED, not an unresolvedpermissionrequest. At sharedb57b2fdd7 rules931adc12d still lacks1900admission/conditionalCIlabel/dualcount+sensitivity implementation; amendedcommittedtestedsource verification remainsPENDING before a realoutcome/guard, no defectfixture repeated and no realE123analysisopened. An attemptedappmessageaskingBtoimplementthiswas rejectedbyautomaticapprovalreview forabsentexplicitcrosschatcode-requestauthorization; it was notsent/retried/indirectlyexecuted. This is a reviewdisposition, no codeedited.

New directrevieworder: **E127 → E123 → E126 → E128 → E117c → E95**. E95operationalnote5 explicitlyassignsR-Qscientificreview, supersedingolderother-ownerstatements; Bjudging/W-lensanalysis unchanged. E127finalSPEC/RESULTS/ANALYSIS_SEAL notpublishedonthissnapshot; priorityunchanged/no speculativeflippedcount. E95sourceonlymap_note5arrival noted, no realjudgments/scienceopened. ReviewsealFri30Oct18CET/17Z remains.

Shared numerical sign-offs below are CLOSED for the specified sealed statistics/verdicts. This closes the older “local evidence only/shared publication unverified” gap; it does not erase the per-experiment historical chronology caveats or certify omitted first-ever pilots. Earlier raw S/CIs and E67/E58b/E66 numeric computations were reused only after exact binding checks, not repeated. No operatorentrypoint/onceguard invoked and no scientificsource/results modified.

| Experiment/component | Shared numerical sign-off / independent result | Shared evidence / worker comparison |
|---|---|---|
| E56 | CLOSED: positivecontrolgateNOTboth(Oracle1/3,NLA0/3),R2/R3/R4NE;R1linewrap/tenseMET,adjective/languageNOT,anomalyNE missingG3 | RESULT7a707ad6/seal7d5eeb02;2256publiccode/evidence/null records exactlyjoinpriorrawaudit. New rawprobe/G3/J-fraction checks below close earlier summary-only caveat. |
| E57 | CLOSED: R-BNOTboth(5/7OUT-J/DIFFUSE,3/7reports>2),R-A1NE missingmulti-tokenG3;R-A2OracleNOT/NLAMET | RESULT8efbad94/seal1f8bf286;3360publicdirectcode/evidence/null joins exact;7mechanicprobegates and rawJlabels checked below. |
| E59 | CLOSED: R1NOTboth(5/5eligibleplanreports,mechanics3/7);R2IN-J4/6descriptive | RESULT00e3c238/seala2c47100;1008publicdirectcode/evidence/null joins exact. Raw504testprobescores/504Jrankrecords,6binaryG3permutationtests andsaveddecompositionJfractions independentlymatch. |
| E62 | CLOSED: RL0S1–S4pass/S5excluded;RL1NOT0/4climbs>=.30;RL2MET rho.80210707432;RL3NOT2/4;RL4NOT delta−.690476;RL5NE NOTRUN | RESULTecf9069e/seale6bdab57;2520publicrecords including420eval exactlyjoinoldcode/evidence/null audit. Raw420L4behaviorrecords giveS1.1655328798/S2.5731292517/S3.9387755102/S4=1/S5.8384353741;S5notgated. No NLAacquisition imputed. |
| E63 R-P1 | CLOSED: NOTMETboth,perpoolOracle17PASS/12FAIL/NLA13PASS/4FAIL amongestimablerowcontrasts; detailedNE/unavailable rows retained | RESULTb8fb0787/seald50b01ba;independent9072source-native/text/labeljoins,all138row-readercells/800pool;1456numericfields point/CIs EXACT(maxdrift0). Frozenregex/familyweights/itemclusterseeds retained. This is regex R-P1, not a new judge-scored primary. |
| E63 R-P2 | PENDING(sealedcategory/TVDresultabsent) | SharedR_P2_STATUS595ed435 explicitlyseparatecodingcommand; no TVD/categorydistribution invented. OverallE63deliverablepartial, R-P1numbers reviewed. |
| E66 | CLOSED: R-G1NOT/falsifierholds;structure104/383=.27154047 Wilson[.22943021,.31818825],topic125/149=.83892617[.77150944,.88930541] | SharedRESULTad641ec4/sealdc902010 exactlybindoriginalrawjudgments6044b643/private-map3848cddf. PublicE66sealwithholdsJUDGE_COPY/JUDGMENTSexplicitly; authorizedhash-boundlocalrawauditused, nofalseclaimallrawpublic. 542acquired/532estimable preserved. |
| E67 waves1/2 | CLOSED: wave1 R-F1NOTall3readerstrata,R-F2METall;wave2OracleR-F1NOTΔ.05[−.025,.13],NLAMETΔ.12[.04,.20],R-F2METboth | Sharedwave1seal92f74fe0/wave2d598fe49+all4originalterminalseals exactlymatchfrozenauditspecs;retain299/99/200wave1strata,200/200wave2,no pooling. Priorindependentrawpaired/Wilsonnumbersunchanged. |
| E68 | CLOSED: R-O1NOTboth;Oraclecontainer−.035714/holder.119621/topic.105161;NLA−.203959/.035714/.011905;neitherstate>=.30 | RESULTb5345d53/sealbcbdc210;1512publicdirectcode/evidence/null joins exactpreviousindependentaudit. Droppedarith_compare remainsNOTRUN,84items/position. |
| E58b | CLOSED numerical: R-b1MET2/3;R-b2NOT15/25;37×84rawpairedcontinuationaudit retained | SharedRESULT80ef8209/sealf39c6763 bindsoriginaloutputab49f327/source19d73508/CPUjoin89fcb887;allsharedresultmembers exact. No extraCIgate substitutedforregisteredpointcomparisons; historicalpre-outputchronology limitations retained. |
| E61 D4 | CLOSED numerical: R-WNEboth;falsifiercomparisontrue(0ignore/0thinkmentions);baseignore/none.275773152495[.267667172691,.284284259330] | RESULT11c241ca/stagesealmanifestb4db7691;independentlyreconstructed504originalnative+252baseprobrecords,84matchedpairs/readerincludingretainedpilots. Readermentionratio andall2000drawsundefined;do nottranslateNEintoevidenceforuse-without-report. |
| E61 D4A | CLOSED: R-W2NOTboth,0/4conceptsR-Wpass;nomonitoring-failureinterpretation | SharedRESULTac4c566e/seal860edb54;1084boundmemberhashes;1680native/840baseprobjoins,224scalar/CIfields EXACT. Twoindependentdev-onlyTorchLBFGSfits reproduceall20AUROCsEXACT; noauthorfit/adapter/guard. |

Additional independentlegacyprobe/J check closes previouslyoutstandingrawmetricgaps: E56/E57/E62 combined146seal/memberpins,4704rawCPUtestpredictionrecords,4872full-vocabularyrankrecords,51binaryG3tests each200permutationsseed20261027. E59adds20pins/504predictions/504rankrecords/6G3tests. AllAUROCs/nullbands/means/permutationp/readableflags exact. Independentlycomputed every saved sparseJ-fraction as squaredreconstructionnorm/squaredfloat32directionnorm, maxdrift0, and labels againstoriginalsealed200-directionNULL_SEAL thresholds; no sparsepursuit/model/readout replay and no refitoftransferredE113. ExistingfullS/CIs unchanged;shareddirectcode envelopes were joinedbyID ratherthanclaimedbyte-identical to normalizedcodefiles. Total84sharedpublicfilehashchecks exact, twoE66withheldmembers explicitlydisclosed.

D4A baseignore/noneratios(birds,citrus,instruments,planets)=[.254123913895,.296351472170,.277413041228,.0806099500951],all<.8forbothreaders. Oracleallfourthink/ignorementions0;NLAplanetthink36/42,ignore2/42,cross-minus-none−.547619047619(failswithin.10);others0. Probesignorebirds/citrus0,instruments/planets1;crossbirds/citrus.99716553,instruments/planets0;noneall.5. These facts prohibitclaimingsilentbutusedinformationfromthisbank. The fittedprobeisdev-only42+42thinkitemsperpair,original5120readfeatures/standardization/L2=.001/LBFGS200;testonceperindependentreviewcomputation,notworkeranalysisreplay.

Chronology: thefullhistoricaldatedamendmentledgeraboveispreserved, includingcaseswhereonlyretainedsource/jobmtimeorresultcommitupperboundsareavailable;theseclosuresarenumericalshared-signoffs, notnewclaimsofcompletefirst-ever-GPU/judgment/openinghistory. D4/D4Arawsources/includeearlierpilotIDs boundtosameoriginalplans; missingearlierattemptinventory remainsunverified. E63R-P2stillunsealed is theoneexplicitunclosedlegacyresultcomponent;late/unreviewedlabelappliesifnotsealedbyFri18CET. No artifactorstatistic fabricatedtomeetdeadline.

Currentcanonicalamendmentsread:8ba4ecacaactual17:09:55CET extendsPAIDjudgingtoFri16CET/15Z(no newpaidcallafter);b724ca65217:12:23correctsE123268/E120aneedjudging;fe2d4eb6417:16:45putsE128judgingafterE127/E126none. Theseareoperatorqueues, notalterationsoftheuser'srevieworder. Sprintclosure3ba3c0c6d makesE75extension/E79extension/E91/E92/E93/E99phase2/E90literalbuffer/E88items5–6 NOTRUNinthesprint(operational/researchphase);stopwaitingforthoseoutputs. E71requiresactualhumancodesbyFri14CET,notmodelsubstitution. E95otherowneroldstatementsaresupersededbyoperationalnote5/R-Qassignment.


Publication-time amendments ACK: E123exploratorynote1 2e3ac01dbactual17:23:34CET addsPOSTHOCdescriptivesinSAMEonce-run: sealedE12135old-agreementitems→Oracle44/52disagreementWilson, same-itemslater52new(steered)/old(unhooked/random)baseline, sensitivity/FPR/precision/coverage+abstentions, nochosennewthreshold/RDIS1change. This doesnottransferE121primaryreviewfromR5;E94ordinaryprecisionvsE121poststeerprecisionaredifferentdistributions/targets,notpaired-drop. E129newR-Qscope§2373c0519155actual17:26:39: triggerONLYsealedE127flipped<50 ORneitherRNAT1norfalsifierMET; ifE127notsealedFri08CET=>operationalNOTRUN,elseifcriterionnottriggered=>NOTRUNnotneeded. Fresh84facts,behaviour-onlyunprefixedcorrectselection/seed20261031/same-relationdonor,original3conditions/layers44/52/60/greedy3parser/rubric/gate/rules, bank3/cap.5GPUh/one§234attempt; independentlyreviewseparate/noE127pooling. Source/input/trigger/outcomesPENDING,no reviewerlaunch. E130remainsR4. BothHANDOFFsidespreservedonrebaseincludingR3E95transferACK.


## 2026-10-29 17:35 CET — §217 quiet intake / E117 true-letter consistency prerequisite

E127 FIRST: atshared7f480abf9 finalSPEC/ANALYSIS_SEAL/RESULTS stillunpublished; no realgreedyclassification/flippedcount/analysisopened. E123amendedsource931adcunchanged, canonicalquestionsCLOSED/sourceimplementationverificationpending. E126/E128/E117c/E95scientificseals notarrived, queuepreserved; noclosedlegacy/statisticauditrepeated.

Authoritative§228true-letterclarification9a7ed1c88 actual17:28:30CET(heading17:50nominal), AFTERnativecapture but BEFORE E117/E117c judgmentopening: sealedE57label1→firstvalueA,0→secondvalueB is permitted deterministictranscription, notnewclassselection. R-Q condition2consistencycheck **PASS504/504** originalE57per-itemscorecomparisons acrossnesting_depth/indent_level/page_range_digit ×Oracle/NLA,6exact84-itemtestIDsets. 11originalterminalUNPARSEABLE retainedmissing, neverzero. IndependentlymappedbinarylabeltoliteralA/B anddirectunchangedpubliccodevalues, comparedagainstonlytheoriginalfrozenpureper-itemscorer; no workeronceadapter/guard/bootstrap/reparse/newreadout invoked. This is a new targetedbindingcheck requiredbytheclarification, not a repeatofclosedE57S/CIs.

Exact sourcecitations: originalE57BANK_SEAL cff66637fedd6afd795370e3efbe3e8262d77c98a64e60e8580a9507dd295f7c; DEFINITIONS bd448aa0aeef440012c320dc13be0ccecae601489599c6f78efa4b5dafa9988e; CPUitems/labels71d1c654fe61cef2ce50b99d52a8b1640c90f309badf8fc84e96ef82aa3ca2b1. Frozenoriginalscorefile results/g_agreement/understand/e56/job/stats_native.py SHA d533cf23c2fa5eb3c8a09cdcd98694268f0f3182dc794c7c9e08338c664b3e6d, usedbyE57; missingnesswrapperretainsUNPARSEABLE. CurrentpublicE57terminalgrid matchedoriginalnormalizedcode/evidencebyopaqueID beforelettercomparison. No standaloneper-itemletterfile invented. Condition1 requiresactualfinalownerbindingcitethesecorrectsources/seals; finalbindingnotyetreviewed. E113probeoutcomes remainR4/notreviewed.

E117c copy-onlyinventory intake: committedbc5b56d50/INVENTORY_SEAL77054334/all336uniqueitems(84eachfourrows)/testsplit/targeted+shamREFs exact. PROMPTS_SEALa3d75132/PROMPTS exact and all8templates independentlyequal original1389b2a02questions carrier_prefix+single-space+registeredquestion; no freewordrepair. Postoutputinventorycopy explicitlydisclosed; originalplan15:19:49CET predatesnativefirstoutput16:14:18.111397CET. No E117/E117cjudgmenttext opened/scored; judgmentroute/rubric/finalMEASUREMENTS/SPEC remainpending. Sourcebindingintakeisnotelicitation/RI-R1scientificoutcome.

Foreignsnapshotdcbef8f3688e98e3aac82f0984bdff4930de27d0 retainedforrestoreafterpublication;allolderforeignsnapshotsalreadyapplied,neverreapply. ReviewsealFri18CET/17Z unchanged.


Publication-time E123 source intake: shared33fc0dc86 actual17:30:35CET implementsPOSTHOCnote1(exploratory_note1.py/adapter): originalE121336recordcensus/source-onlynormalizer→exact35old-agreementIDs, noE123/E10952-drivenmembershipselection; same35later52baselines, full84/50baselinesseparate, case-controlprecisionpopulationlabel, coverage+missing/one/no-valueabstentioncountswithoutchangingdetectorsignal. Independent22puresyntheticsPASS(includingtemporary-onlyguards/E121analyzeforbiddenfixture),9currentpackagebytesexactcommitted/3dependencypins exact. No realE121/E123sourceclassnormalizationorconsensusIDscomputedbyreviewer, noother-owneranalysisreplay. The appendedreceiptlocator POST_HOC_NOTE1_SOURCE_RECEIPT.json isnotpresentinsharedtree; exactcommittedsource/testchecks, notthatreceiptclaim, supportthisintake. Originalrules.py remainsbyte-identical931adc12d; clarification1's1900gate/conditionallabel/dualcategory+sensitivity implementationverificationremainsPENDING. This doesnotreopenresolvedquestionsorendorseoldadmission. No realguard/output/judgmentopening.


## 2026-10-29 18:05 CET — §217 quiet source intake / true-letter binding metadata

Atshared59131cba2, E127finalSPEC/ANALYSIS_SEAL/RESULTS remainunpublished; first-priorityscientificreviewpending/no flippedcountcomputed. E123rules931adcunchanged(amendment1implementationstillpending); canonicalquestionsremainCLOSED. E126/E128/E117c/E95outcomesealsnotarrived; no closednumerical audit repeated. No BRIEF amendment since9a7ed1c88, reviewdeadlineFri18CET/17Z unchanged.

TrackQ E117c TARGET_LETTER_SEAL a7082b3449b661a2525a33988ad0ed226b6b38bc670c0f4b4aad6d5d6ef83b9a (18d058cb4) metadata independentlyagreeswithalreadyverifiedE57scorerd533cf23/BANKcff66637/DEFINITIONSbd448aa0/labels71d1c654. Its252boundE57rows/3×84 andfact_recallPENDING areexplicit. The prior R-Qcondition2PASS504/504(11missingpreserved) is ACTUALpublishedverification d23faf7cb, reaffirmeddirectlytoGuiv; no additionalR-Qpermissionorstatisticalrerun neededforthiscompletedcheck. Metadatareceiptalonedoesnotverifytheprivatelettertable96134831 orfinalsourcejoins; deliveredrelativeCPUlocator r_e117c/binding_v1 notlocatedinreviewedknowncustodyroots. FinalbindingneedsoriginalCPUfilelocator/hashverification; fact84(E56lineage) remainsseparate/PENDING, notsilentlycoveredbythree-rowE57check. I2localprivate-tablehashde7afc19 differsfromTrackQ's96134831, so it wasnotusedasareplacementoropenedunderwrongseal. No E117/E117cjudgmentsopened, lettersnotchosen/edited. Thisisqualifiedbindingmetadataintake, notfailedconsistencycheck.

E95note5prospectiveadapter5348c18e8 independentlysource-reviewed:8receiptpins exact,25puresyntheticsPASS(15newmap/10originalOracle-onlyregressions),no realjudgments/activation/J-array/fit/onceguard/maininvocation. Sourcekeepsjointitemresampling/E87seed20261029, layerreal-minus-placebo, firstmentionREALarmonly, D=max_layerSreal−max_layerSplacebo(separatemaxima), explicitwhole-stageandstatement-scoreeligibility, separateNLAcoverage, exactsealedJ/E62median andsingle-site/mapverdictbindings; allmissinglayer/arm makesmapverdictNE. H-M1remainsdescriptivehypothesis/agreement>=.80/no belowmedianJrowD>=.30, notanewconfirmatoryrule. OriginalE87confirmatoryresultuntouched. FinalPLAN/RULES/sourcepopulation/normalizedjudgmentbindingsawaited; nofiniteverdictthresholdorJpopulationinferredfromcustodyreceipt. TrackQcustodyreceipt350-ishlinesexplicitlydisclaimsownershipofthese I3/W-lens/E87 sidebindings; nooperatorGO/resultendorsed. E129conditionalintake59131sourceonly/selectionnotexecuted, triggerawaitssealedE127. E130sourcearrivalsbelongR4, noR-Qtests/review.

Foreignsnapshotad6da5c32b116a94f0199564492e896b63d8b669(4HANDOFFpaths)retainedforrestoreafterpublication; olderforeignsnapshotsalreadyrestored/neverreapply.


## 2026-10-29 18:35 CET — E127 judging custody / E123 saved-cost hold

E127 remains FIRST for scientific review. Shared C_JUDGING_FINAL_RECEIPT at0a79a2752 now delivers COMPLETE judging, not analysis: independent archive3f52d3ce4fa1d3249edab69e164750545fd1a39f8912300f69ea8861423589c3/608022bytes and ALL782 public-phase member pins exact (783 archive files including seal875a90a0); originalphase1307e19d7pins independentlyexact in originalCPUcustody, including PROGRESS/RAW_RESPONSE_BINDINGS omitted fromportablearchive. Canonicalbank928e6e4f3pins, portablebank65f33aa92pins, readout-keyedhandoff7aad54541pin exact. Sealed COUNTS agrees756=747KEPT+9UNPARSEABLE; actualUSD.39670800/reserve0/unused2.60329200 releasedONCE original3cap. Historicalphasereceipt cap_released:false is supersededbyfinalBANK_COST release, notnewallocation. Firstretainedpaidoutput2026-10-29T16:23:29.014087Z isreceipt-bound; full earliesthistory not newlycertified. No semanticreadout/codeclassification, flippedcount/cohortselection/S/Wilson/authoradapter/guard performed. FinalSPEC/ANALYSIS_SEAL/RESULTS stillPENDING; judgingmustnotbedescribedasunpublished.

E123 public C_UNKNOWN_COST_GUARD_HOLD.json records HELD_SAVED_RESPONSE_UNKNOWN_COST, savedresponseSHA49f74cf9f503b98373de1cc4886125353bf9f20a59dbae8a78aefde47cb917f5 and unresolvedupperUSD.0102387500. OperatorHANDOFF reports stopped169/268 at unreservedFIFO boundary, savedHTTP429withoutusage/cost, noledgerwrite/resend; usedonlyasoperationalstatus/locator, notindependentcostreconciliation. Coordinator authoritativeprovider/accountchargeproof required beforeoperatorresume. No reviewerresend/guesszero/reconciliation, no402/globalotherbankpauseinferred. Fulljudging/analysis remainsunsealed. E123canonicalclarificationquestionsCLOSED; amendedrulesimplementationstillpending, nooldsyntheticdemorepeated. E126/E128/E117c/E95/E111d/E109robustnessscientificsealsnotarrived in thissharedsnapshot; closedauditsunchanged.


## 2026-10-29 18:55 CET — E127 ruling1 required pre-guard diff check: GO

Authority01fc0310f actual18:44:55CET precedes minimalfix0068723cd78b72bfa510d8bf30979864cfc68ce8 actual18:47:32. R-Q independentlyinspected all3filediff: exactly6productionlines in sharedtransport, E127-onlynullbranch resolves the SAMEsealedterminalcode-pointerparent, requires literalcodekey/matchingoriginaljudgmentID/explicitUNPARSEABLEstatus, convertsinmemorytoexistingmissingsentinel; sources/nullsunchanged. E128onlydependencyhashrefresh; no E128nulladmission. Originalrules.py/common.py/classifier.py byteidenticalparent; no threshold/cohort/parser/scorechange. All13dependency pins exact. ExactcommittedGitextract39puresyntheticsPASS independently (includingtemporary-onlyguards, nullUNPARSEABLEacceptance/KEPTandabsentstatusrejection, sameflipped_n60, planned/known/missingdenominatorsonall84andselected60, condition/blocklocality/source-nullpreservation). RealonceguardABSENTatcheck. GO for thisrequiredDIFFcheck under ruling1; soleBoperator retainsoriginalpreflight/onceguard. No realMEASUREMENTS/greedyanswers/codesresolved, adapter/guardnotinvokedbyreviewer; noE127flippedcount/scientificverdictclaimed. Finalsealedanalysisremainsfirstpriorityonarrival. ReadallnewBRIEFrulings01fc/unknown429boundbooking/E128672scope; earlierE123chargeproof-onlyholdisSUPERSEDEDbycanonicalupperboundbookingauthority forkeyholdingowner, notreviewerledgerauthority.


## 2026-10-29 19:00 CET — E127 scientific review COMPLETE (shared ec7671765)

E127 flipped-set gate DESCRIPTIVE ONLY: own=worker0/84 context_updateGREEDYNEW ANDno_prefixGREEDYOLD; frozenparse_target_answer cf6bc5ed appliedindependentlytoALL252originalrawanswers/originalsealedcandidatejoins gives84otherineachcondition/0old/0new/0missing. No alternatealiases/repair/logit-basedcohort. Registeredreading “context update did not take”; thisisfailuretoreachregisteredgreedyflipgate, notproofcontextwasignored ornegativeevidenceaboutnaturalstaleness. E127 R-NAT1 DESCRIPTIVE ONLY own=worker; selectedold44/new60/neutral44allplanned0/n0/estimatesandWilsonnull. E127 falsifier DESCRIPTIVE ONLY own=worker new44n0/null, notNOTMET. Neutralcontrol SAMEemptyflippedset, no substitutionwithall84. §237E129mechanicaltrigger<50satisfiedbythissealedresult; noR-Qnewselection/launch/pooling.

Independentrawcustody: originalanalysis3025b76adfd74ee194e62a69e3b57044eb92a99298b64232f47172e3fbf93f5c/publicpublicationc6489b41 allboundmembersexact; SPECe31177f8/output3727a5dc/inventory8a5b9aaf/candidate549fa110/3originalsourceseals exact,7seals/250memberpinsverifiedwithoutauthoradapter. BINDINGe67a0825 isJSON-reserializedbutsemanticallyidenticaloriginalSPECe31177f8(notbyteidentical); disclosedhere, nofieldchange. All84originalIDs/candidatejoins/252greedyrawidentities/756Oracleitem-condition-layer-judgmentidentities exact. OwnALL36old/newrateentries(include18emptyselectedentries) reproduceworkercommon.statsWilson95exactly. All84old,new k/n: context_update44=26,12/83;52=43,14/84;60=49,20/80;neutral44=44,0/84;52=83,0/83;60=83,0/83;no_prefix44=66,0/83;52=84,0/84;60=82,0/83. NineoriginalnullsrequireSAMEterminalUNPARSEABLE+matchingjudgmentID andremainmissing: context_update[1,0,4],neutral[0,1,1],no_prefix[1,0,1]at44/52/60. NoemptyorUNKNOWNrateconvertedzero, nojudgmentreparse/rerun/newcalls.

Chronology(actualcommittertimes): §236registration2ebe15:30:44/clarif1d35815:33:37CET <locatedretainednativefirst16:30:47.430386. Classifierclarif4c27116:31:26 andC8d1b16:33:55/Bcf9516:37:35areAFTERnativefirst, explicitlybeforeopening/correctexistingunchangedparserpointer, notclaimedbeforecapture. Fullfirst-ever/discardedhistoryandindependentfirstopeningwallclocknotnewlycertified. Analysisruling01fc18:44:55<fix0068723cdCOMMITTER18:48:00<requiredRQGOb31c18:50:51<originalguard18:51:51.980179<RESULTS18:51:51.981427<seal18:51:51.981827CET. Earlierreview's18:47:32fixlabelwasAUTHORTIME, correctedhere toactualcommitter18:48:00. Executedb31csourcecontainsreviewedminimalfix; originalguardb1d16927retained/consumed, NEVERreplayed/reset. No authorentrypoint/guard/rulesanalyze/transportinputs invokedbyreviewer; independentread-onlychecks only.

E127 separatepair-logitDESCRIPTIVEcross-check independentlyexact: context_update41/84new-preference,neutral0/84,no_prefix0/84;0missing. TheseareNOTgreedyflips anddoNOTreplaceflipped0/84orchangeunder50gate.


## 2026-10-29 19:10 CET — E117c E56 true-letter prerequisite PASS

Under01fc0310fruling2, newR-Qcondition2E56fact_recallPASS168/168originalsealedper-itemscores(2readers×84test),0missing/0disagreement. IndependenttruthAifsealedlabel1elseB appliedtooriginalsharedjudgments equalsoriginalfrozenpuresigned_valuescorerperitem; noE56bootstrap/analysisreplay/nohandchosenletters. Scorer stats_native.py d533cf23c2fa5eb3c8a09cdcd98694268f0f3182dc794c7c9e08338c664b3e6d; E56BANKe733bed854700d0129a7b59ed1e1e6ddf82947add11c2f3e77feb36bfb451112; ROW_DEFINITIONS9177f2b10f578add5d288008b20f093b1c48b308085e01442948a1d45c70868d; LABELSitemsf8eda6eae303ab40988fa254eafef91945be96fe38639dc8cd70266037cae442 exact. PriorE57PASS504/504(11missing)unchanged/notrepeated,nowbothregisteredconsistencyprerequisitescomplete.

TrackQv2TARGET_LETTER_SEAL672d2d312a9a7fc9f4098e8e700a1edb80acfc4ed697cc56f1c1247f2fca861e/originalCPUtable78b346b8dd8e0708d5b2a53bd954f398049262aa230c24a9b2b055e1f04d3968 independentlyhash-exact. ALL336tableIDs agreepublicinventory;literaloriginalE56/E57label/valuepointersresolveexacttestrow/label/letter/pair. All252priorE57id/label/row/target_letter/valuebindingsunchanged; rulingmetadataupdated(notwholetablebyteidentical). Originalv1locator96134831nowlocatedasdeliveredletter_v1,notI2'sdifferentfile. Finalnative/judgmentidentity/SPECbindingsandE117mainEOSaccountingstillseparate; thisPASScannotstandinforthem. No E117/E117cjudgment/readout/tokenmetricopened, noauthoradapter/binder/guard/reparse/modelinvoked. No newscopedoutcomesealsatab222b33b;E127reviewCLOSED,nextE123/E126/E128/E117c/E95pending,notrepeated.


## 2026-10-29 19:30 CET — §217 E123 judging custody intake (no scientific result)

E123newCOMPLETEbankca55b1cd9(actual19:08:49CET): independentarchive5008fae396f50e74a384553c375aa763d310feb535223e6d94b0f1828b9e7ff2/251790bytes/324files andALL323publicmemberpins exact(publicphase6583cc74); originalCPUphase618bb7799pins/canonicalbank2c754c813pins/portablebank114fb90f3pins/keyedreadouthandoff736146aa1pin exact. SealedCOUNTS268=245KEPT+23UNPARSEABLE; missingretained, nozero/rejudge. FinaltotalBOOKEDUSD.1735755000=knownprovider.1633367500+explicitbooked429upper.0102387500, reserve0/unused2.8264245000releasedONCEoriginal3cap. Legacyactual_usdfieldincludesbookedbound andmustNOTbecalledentirelyproviderreportedactual; explicitBOOKED_429_BOUNDS preservesprovider_actual_cost_known:false. e340bookingauthority/savedresponse49f74cf9matchesearlierhold, notguessedzeroornewallocation. Firstretainedpaidoutputreceipt16:40:03.412696Z; thiscustodypassdoesnotcertifyearliestdiscardedhistory. No realE123readout/category/featurematching/statistics/adapter/guardopenedbyreviewer. JudgingisDELIVERED, notpending; finalSPEC/amendment1sourceimplementation/scientificANALYSIS_SEALremainPENDING(rules.py still931adc12d). Canonical1900gate/dualquestionsCLOSED, no repeatedfixture/request.

Atshareda3f69a61d no newBRIEFsince01fc/no newscopedsciencebeyondclosedE127. E126/E128/E117c/E95/E111d/E109robustnessoutcomesealsstillpending. OwnerBanalysisqueueE126→E128→E123isoperationalonly, doesnotchangereviewerpriorityorregisteredrules. E117cE56PASS80cc14cd9ACKarrived, no repeatedlettercheck. E129candidatepool/triggerdeliverynotreviewerselectionorlaunch. Otherreviewers'E120c/E118b/E130remainother-owned. Foreign06323eb04fd3a795d35a97b36ecc47972ded6515retainedforrestoreafterpublication;alloldforeignhashesalreadyrestored/neverreapply.


## 2026-10-29 20:00 CET — §217 E123/E126 source intake; E128 admission blocked

E12316f0ed460 prospectiveNULL_CODEdiff independentlyreviewed:6productionlines acceptnullonlyfromSAMEliteralcode-pointerparent/matchingoriginaljudgmentID/explicitUNPARSEABLE, existingin-memorymissing/sourceunchanged. ExactcommittedGitextract25puresyntheticsPASS/3dependencypinsexact; testscoveraffectedlayer/pair/FPR/posthocmissingdenominators/unchanged35cohortandotherlayers/KEPT-or-no-statusrejection/failedtemporaryguardretention. Rulesbyteidenticalparent931adc12d: thissourcecompatibilitycheckisNOTimplementationofthecanonical1900defineddrawgate/conditionallabel/dualsensitivity, whichremainPENDING. No real E123measurements/judgments/guardopened; do not replayonceadapter. No newquestionorpermissiongateinvented.

E126newclean-sourcebindingmetadata bindingCLEAN_SOURCE_BINDING.json identifiesE105unpatched0serialsources; originalfactseal9a1d899743pins/languageseala7b8149549pins andprivatepointerfb6f9000hashindependentlyexact. Newbind_clean.py identity-onlyrow/tokenIDs/read_index/ORDEREDcandidateIDs exactmatching rejectsduplicatedsourceinputs/steered/random/donor/changedsiteororientation;9puresyntheticsPASS. No actualbindfunctiononrealinputs/no lclean/logits/ratios opened orcopiedbyreviewer;134inputjoin/equivalenceandfrozencandidate/sumlogprobcontractstilltobecheckedagainstfinalSPEC, notassumedfromworkerclaim. PublishedmetadataexplicitlydisclosesserialE105vsbatchedE126/wholecurrentE101codeNOTbyteidentical; no roundingrepair/newbaseline authorizedbythisintake. Prior134packet auditnotrepeated. E126scientificresultstillPENDING.

E128sharedPAID_ADMISSION_REVIEW_BLOCK(18:30:45.609931Z)/ADMISSION_REVIEW.md recordsautomaticapprovalreviewREJECTEDliveadmission+route/funding/globalchecks BEFOREexecution. Statedreason: trustedhumanmessagesdidnotexplicitlyauthorizeE128USD3; coordinator/heartbeatcontextconsideredinsufficient. Noallocation/ledger/networkchecks/paidcallscreatedbyrejectedcommand. OperatorreportsALL672units/2016wireprivacyPASS(sourceonly), butthisisNOTadmissionorsealedjudging. Reviewerdoesnotretrypaidaction/reservations/proxyoperatororappmessage; requiredhumanbankauthorizationreportedtoGuiv. Registeredscientificscope/capsunchanged, noclaimHTTP402/globalpause/failedscience. E127/E56letterchecksremainCLOSED; noothernewscopedscientificseal/BRIEFamendmentat77ec9ddb9. Foreign ecfb7ba7381da52ecc3deca5da56e98e0d7f0f29 retainedforrestoreafterpublication;oldhashesrestored/neverreapply.


## 2026-10-29 20:30 CET — §217 quiet E117/c source/start intake

Atshared6797bba26 no newBRIEF/no scopedscientificoutcomeseals; closedE127/E56letterauditsnotrepeated. C_JUDGING_SOURCE_AND_START_RECEIPT50dafcfc reportsE117c672RUNNING/main3024sourceready/mainpaidcalls0. IndependentcurrentE117_SOURCE_UNITS_SEAL72pins andE117_SOURCE_SEAL72pins exact(sameclosure,not144distinctfiles); originaldescriptorORIGIN_SEALde870fc4 twoCPUmemberhashes exact. Sourcecopiestheoriginalper-itemE56/E57blindproperty/valuepacketthroughsealedunitID/privatekey, notgenericreplacement/handchosenletters; no goldonwireclaimedbyreviewerfromcodealone. No Cprepare/dispatcher/model/network/authoranalysis invoked andnoE117/cnative/readout/judgment/norm/tokenmetricsopened. Coperationalcap4combined/cceiling2iswithinregisteredcombined6; extra2unallocated, noR-Qcapchange. Main8privacycopiedreadoutsdisclosedbyownerreceipt, originalaudit/exclusioncompanionmustaccompanyfinalscientificbinding; no prematureexclusionornewstatistic. Completejudging/SPEC/actualEOSsourceaccounting/analysisPENDING. E117cstartisnotcompletionorR-IR1evidence. E120a800arrivalbelongsR2/noRQtakeover. E128automaticadmissionblockunchanged/alreadynotified/no repeatedauthorizationrequest; no workaround. E123amend1implementationandE126/E128/E117c/E95sciencepending. Foreigntailsb0f8da8b50a8ad338a1a6cd04ea62fc12e59ca43retainedforrestoreafterpublication;olderhashesalreadyrestored/neverreapply.


## 2026-10-29 21:00 CET — §217 E117 privacy-map source intake, scientific seals pending

E117C_PRIVACY_SENSITIVITY_BINDING_RECEIPT449cc47a/CPUbinding1bb216c5b42db1bdb35c154272bf73dfdbf142572563e9ea4231a5ca6bafd8eb/mapc109dc0f2bdc66f433df97eec0254e846371820dde556a7e3558d99846f7731a independentlyhash-exact. All8boundrecords equalUNIT-boundauditfc450041affectedIDs andliteraloriginalCPUjoins: originalE113ID/E56-E57bankID/row/alpha/arm/nativeID/textREF exact; nofile-order/textmatching. Fourhelper-sourcepins exact/6independentpuresyntheticsPASS. Helpercommit2eec69e00actual20:51:54CET precedes deliveredbindingreceipt20:52:51.128246/published0b01b189320:53:06. Thisclosesdeliveryoftheauditedeight-recordIDmap, nottheowner'sfinalanalysiscompanion/SPEC; originalandjudge-copyUTF8hashfieldsretained, reviewerhasNOTopenednative/originalevidencetextorjudgments/metricsandhasnotindependentlyrehashedtextcontentthroughsemanticIO. No build()/preparer/adapter/guard/reparse/modelcalls. Primaryplusstandingexclusionsensitivityremainowneroncesealoutputs; no reviewernewexclusion/statistic. Atsharedfab9d8595nonewBRIEF/scopedsciencebeyondclosedE127;E123amendedimplementation/E126/E128/E117c/E95/E111d/E109robustnesspending. OtherreviewerE120aoutcomeleftR2. E128unchangedalready-notifiedadmissionblock/no repeatedask. Foreign250566b642c5df8f914c7367beaa7e2b14567598retainedforrestoreafterpublication;allolderrestored/neverreapply.


## 2026-10-29 21:30 CET — E117c judging custody complete; main process-control block

E117c COMPLETEjudging5754087e2actual21:03:46CET: archiveb028f1279dda6888d0beb855aa518591e9518a942cb56ef4e7eafb4ac59501f5/624642bytes/834files andALL833publicphasepins independentlyexact; originalCPUphasecf48cad47pins/keyedhandoff420db3cf2pins exact. COUNTS672=597KEPT+75UNPARSEABLE,USD.41786775/reserve0. SharedE117operational4/cphaseceiling2 remainsOPEN/mainpending, NOunusedrelease/no extra2allocation. Receiptfirstpaidoutput2026-10-29T19:08:01.122818Z; actualE56/E57consistencyPASSalreadyclosedbeforethis. No semanticreadout/code/scoring/token/norm/adapter/guardopeningbyreviewer; E117canalysis/SPECscientificoutcomePENDING, judgingDELIVERED. Separatecscientificsealneednotwaitmainbankfinancialclose accordingtooperatorhandoff, but reviewerdoesnotinvokeonceadapter.

E111dcorrectedsource5d6c6f88aactual21:21:57CET implementscanonicalnatural44control(samems.naturaloriginalx1)ratherthanpairedrandomcontrol; steeredprimaryandrandomperturbationreferenceexplicitlyseparate. Source10pinsexact/8independentpuresyntheticsPASS, originalfeatures/probeorientationsreusednofit, sourcefeaturex1consistencyrequirementretained. POSTHOCEXPLORATORYonly/nooriginalE111rulechange. No realfeatures/matching/originalinputs()/analyze()/guardinvokedbyreviewer. Thisclosescorrectedsourceintake, outcomePENDING.

NewpublicPRIORITY_LOCK_SAFE_REVIEW/PAID_PROCESS_CONTROL_REVIEW_BLOCKstatusAUTO_REVIEW_REJECTED_BEFORE_EXECUTION(20:19:59.272554Z): proposedSIGTERMownadministrativecontroller91859andtestedreplacementaffectingexistingownpaidworkers rejectedforlacktrustedauthorizationforexactmultiworkeroperation. PublicconcreteREVIEW.md c633f90c describesstoppedpacing-FDwaiter/sharedFIFOstall; mainPID40018has0reservations/0paidcalls,ownerreported. NOtermination/replacement/workerrestart/signalsfromrejectedcommand; no reviewerretry/process/lockfile/workaround/appmessage. ActualhumanapprovalquestionreportedtoGuiv; E128bankapprovalisSEPARATEpreviouslyreportedunchangedquestion, notimplicitlygranted. Stallisoperationalnotmissing/zero/negativeR-IR1. No newBRIEF/scopedscientificresultata743c9f62;other-ownedE124sourceleftR5. Foreignd41b21e4b09c1477aa19ecca72a0f2bee0e02479retainedforrestoreafterpublication;olderhashesrestored/neverreapply.


## 2026-10-30 00:30 CET — E126 final SPEC custody intake, before scientific opening

Shared8029241f5actual00:24:51CET deliversSPEC31b01f021a3dc3eb38f47c89e770545bfb3ad2fa761f70e7e65b493b8cfba661/inventoryeaf91fad/output4d84dac0. IndependentALL8seals/831memberpinsexact(6originalsourcesE126identity049910cd/native5d206226/E104276968c8+49981018/E1059a1d8997+a7b81495). Newnormalizedgrid84fact+50languageALL134IDs/steeredtargets exactoriginalE104Uflippedprivate495bbb19. ALL4288literalCPUidentitypointerenvelopes agreeitem/row/direction/block/patch/paircount/candidatehash/orientation:134clean134steered2010restore2010insert, no duplicatepointer. No rawpairlogprobs/logodds/ratios/statistics/adapterinputs()/guardopened. Thisiscompleteenvelopecustodyintake, notindependentconfirmationoftheidentityflagsagainstactualpatchednativevalues/operations; priorpacket/directionchecksnotrepeated. Actualclean-sourceinputequivalence/serial-vs-batchednumericconventionwillremainexplicitinoutcomereview.

ConfirmedprospectivecontractmismatchalreadydisclosedbyTrackQ: currente126adapterref numericalsourcepredicateallowsE104/E109/E126, so originalCOMPLETEE105cleansealsarestructurallyrefusedbeforeclaim. E105sealsNOTrelabeled/substituted. Owner'salreadyaddressedminimalclean-cell-onlycommitted/testedcompatibilitydiff awaitsdeliveryandR-Qdiffcheck, no newhumanpermissionquestion, noreviewerpatchorpreflightreplay. OriginalsteeredpointerOracle-vs-subjectchannelnoteisdisclosedinTrackQdelivery; actualorderedcandidate/sourcejoinsnotcertifiedfromidentityflagalone. ScientificresultstillPENDING/noR-MED1numbersclaimed. E117cfinalSPECnextperownerdelivery,notyetshared;othercanonicalpendingseals/previouslyreportedprocess/bankapprovalblocksunchanged/notreasked. No newBRIEF at81bcf30ca. NominalTrackQheading2026-10-30 23:24Z isnotactualcommitclock; authoritativeSPECcommit00:24:51CETOct30=23:24:51ZOct29. Foreign13d3a99b18977ac9c3d40b2d6806fca9e788d13fretainedforrestoreafterpublication;olderhashesrestored/neverreapply.


## 2026-10-30 00:35 CET — authoritative §238 intake (3505f1f4c actual00:29:16)

§238supersedesE127'sregisteredgreedyreading: R-NAT1NOT EVALUABLE(measurement), not “context update did not take” asascientificfinding. Originalsealed0/84greedy/all252other andindependentraw/ratechecksremainunchangedhistoricalevidence; noresultrewritten/replayed. Deviation1E127/E128newseparateCPUonce-run/source mustbecommitted+synthetic-testedandR-Qdiffcheckedbeforeexecution; flipsnowE104pair-logitmeasure, E127>=50/RNAT1/falsifier/SAMEflippedneutralcriteriaunchanged, E128alpha_min{2,4,8}onthatmeasure. Quoteprospectivepointerwording “sealed first-token candidate-pair logits”; exactfrozenE104scorer/index/aggregationmappingmustbeexplicitinsource, notnewreviewerchoice. DiagnosticFIRSTtokenCATEGORYonly252E127answersrequiredfromB, noactualvaluespublished. Newsource/diagnostic/deviationsealPENDING; no reviewerdiagnostic/scoring/changedcohortcalculated. OriginalonceguardCONSUMED/neverreset; amendmentnotauthoritytoreplayoriginalentrypoint. E129NOWHELD: previousgreedy<50triggerdispositionSUPERSEDED; re-evaluateonlysealedE127deviation1before08CETdeadline, no launch/selectionbyreviewer. E120cdeviation2belongsR2/noRQtakeover.

Chronologyqualification: §238heading “before any pair-logit flip count of E127/E128” cannotliterallydescribeallE127pair-preferencecounts: ORIGINALsealedec7671765RESULTSandR-Qab222b33b alreadyreportedupdate41/84/neutral0/noprefix0asDESCRIPTIVEcross-check before3505f1f4c. AmendmentisPOSToriginalresultandPOSTpublishedpair-logitcross-check, beforeNEWdeviation1rule/cohortanalysis; donotclaimfullypre-result/priorpair-countblindregistration. Nochangedrawinputs/recomputationinthisintake.

§238alsoexplicitlyrecordsGuivcontroller91859lock-safereplacementandE128672bank<=USD3approvals; priorrejectionreceiptsretainedhistorical. Ownerexecution/liveadmissionproof/resolutionreceiptsstillneeded, notclaimedcompletebyreviewer; no process/API/ledgeraction/appmessage/proxyperformed. E130measuredattemptOTHERownerR4. ReviewFri18CETunchanged. No newscientificdeviationseal atceb0e3115;E126cleansourcediff/E123amend1implementation/E117cSPECetcstillpending. Foreign13d3a99b18977ac9c3d40b2d6806fca9e788d13fstillstashedpendingrestoreafterpublication/allolderrestored.


## 2026-10-30 00:40 CET — §238 deviation1 / E126 clean-source DIFF CHECK GO

R-Qrequiredpre-runDIFFCHECK COMPLETE/GO for6dcd489924a40916216ac2a1dcfc910ba428acad(actualCOMMITTER00:34:04CET) under§2383505f1f4c00:29:16. Independentlyreviewedallproductionchanges; exactcommittedGitextract68puresyntheticsPASS,16dependencychecks across3packages exact,allcurrentpackagebytesmatchcommit; e126/e127/e128rules.pybyteidenticalparent. Newpair_answerreadsONLYoriginalpair_logits, mean(A−B)overfrozenSINGLE-TOKENcandidatepairs,targetorientation±1,strictnew/old/tieneither/missingdistinct; matchesactualE104materialize104.scorer/contract104.meanrule andE127runner.pairs_from_logitscaptureatgreedySTEP0(inheritedE128), notlatergeneratedlogits/fullcontinuations/greedytext. No realpaircounts/cohort/featurescomputedbyreviewer. E127usesunchangedRNAT1/falsifier/SAMEflippedneutral/rates onreplacementbehaviouralone. E128selectssmallestqualifying2/4/8samepairmeasure;original8flagsreused(no new8call/imputedgreedy),lower-doseunknownretainsambiguity,randomonthesamesteeredflippedcohort,alpha8-onlyquestion-open/strong-steercaveatretainedwithdescriptivepatternseparate. RecordedterminalUNPARSEABLEnullmappingfail-closedasbefore;nojudgment/category/thresholdrewrite. NewentrypointstrictseparateDEVIATION1_ONCE/e127,e128anddeviation1_onceoutputs, originalgreedyguard/resultuntouched; originalguardsNOTreset. Bdiagnosticreceived252whitespace/newline(84percondition),novalues; receiptintakeonly,notclaimedindependentre-tokenization. OriginalE127RNAT1NE(measurement)retained; §238post-original41/84pair-crosscheckchronologydisclosureunchanged.

E126minimalcompatibilityPASS: COMPLETEE105acceptedONLYnumericaldirectionclean;steered/restore/insertremainoriginalallowedexperimentsandidentitydirectionvalidated. Syntheticsacceptclean/rejectsteered+patch,withoriginalguardunused; originalsourceexperimentNOTrelabeled. Frozenlogodds/median/undefineddenominator/controls/rulesunchanged. FinalSPEC31b01f02custodyalreadyverified,notrepeated;actualnativeflags/orderedrawjoins/numericserial-vs-batchequivalenceremainoutcomereviewduties. Atchecke126ANALYSIS_ONCEande127/e128DEVIATION1_ONCEABSENT. GOonlyforcompletedrequiredDIFFcheck; soleownerfullsourcepreflight/onceclaimsremainowner, futureE128SPECcannotinventoptionalalpha8judgmentsorrawsourcefields. No revieweradapter/inputs()/analyze()/run()/guard/model/APIinvocation. E129remainsHELDuntilsealedE127dev1trigger,noearlyselection. Foreign e149cd279fe1580477bace3c0beb9cde3d3473f8 retainedforrestoreafterpublication;olderhashesalreadyrestored/neverreapply.


## 2026-10-30 00:55 CET — E127 deviation1 / E126 / E123 independent numerical reviews

E127 §238DEVIATION1 seal3885bab7/sharedf79631741: own=workerflipped41/84FIRST(contextpairNEW41,OLD43;neutralOLD84;noprefixOLD84). R-NAT1 DESCRIPTIVE ONLY; falsifier DESCRIPTIVE ONLY(41<50), no confirmatorypredicatepromotion/no “update did not take” inference. OriginalgreedyRNAT1remainsNE(measurement); original3025seal/b1dguardhashesunchanged. ALL18newselected-cohortold/newrate/Wilsontriplesexactindependentcommon.stats; SAME41neutralcontrol,selectedmissingcontext44/52/60=[1,0,3],neutral=[0,0,0],noprefix=[1,0,0]. All84descriptivefieldsbyte-semanticidenticaloriginalresult,no redundantrecalculation. Pairflipmeasurefirst-stepmean(A−B)/targetorientationstrict,tiesneither; source252literalpair-recordselectionreproduced, no alternateclassifier/threshold/scorefit. Original9terminalmissingretained, notallnecessarilyinselectedcohort. §237/238E129trigger41<50NOWSATISFIEDfromSEALEDdeviation, neverpool/reviewerlaunch/earlyselection. DeviationPOSToriginalpublished41/84pair-crosscheck, notfullypre-result; labelpreserved.

E126 R-MED1 MET own=workerFACTONLY: restorationmedianR44=.01289080803578593 CI[-.011278224494137427,.023161825506655735];R52=.6626340985379828[.5142178126648168,.7946768380708754];R56=.8764783610542008[.8495491295743811,.9032120491159895]. BOTHrestorationcontrolsatALL5blocks<=.15(maxmedian.1067709387390184),44<=.15,52AND56each>=.50/LB>.25. Falsifier NOT MET own=worker. LanguageDESCRIPTIVEonly,R44=.2865632834989321,R52=.2876578251933053,R56=.5180860403863037(allCIsverified);no secondconfirmatorypromotion, insertiondescriptive.

E126originalseal6fcf7401/publicaggregateRESULTSdb93b5e9exact; originalsealALL3members includingPER_ITEM.PRIVATEcaff647fretained/mode600/LOCALONLY, no privatecopyorsealstripping. Independent4288literalrawpair/identityjoins,ALL4020nativeoperationrecords(direction/block/control/site/upstreamhookrestoreONLY),134sameoriginalclean-inputtoken/read-index/ORDEREDcandidate-pairmatches viaCfb6f9000, all134rawodds/ratiosmatchprivateauditEXACT. ALL60common.stats2000seed20261027medianbootstraptriples and64rawlogoddsmediansEXACT. RatiosperitemBEFOREmedian;0exactzero-gaps,minimumabsgapfact15.125/language.1015625,noepsilon/clipping/dropping. OriginalcleanE105rawpointermember+recordindex correspondsC'spair_logprobschildpointer,notcopiedscalar;steeredSUBJECTlogits-channelrawcontinuationsused,notOracle-channel. OriginalE105serialcleanvsE126batchedforwardsdisclosed; no newbaselinecompute/roundoffrepair. Normmatchingisconstructionbeforecast,NOTbitwiseequalityofapplieddeltas:1340randomcellsmaxabsnormdrift.029754638671875/maxrelative.0005350749834301081(.05351%); sourcehookwritesvalue.to(z.dtype),CPUbindinguses1e-3relative-toscalecheck. This isordinaryrecordednumericalapproximation,notanewregisteredexclusion/toleranceforR-MED1,andnorescalingperformed. Nativepatchnorm-ratio>1.5flags:2/670restore-earlier(max1.61162856),2/670insert-earlier(max1.54796166);0read/randominbothdirections,maxreadrestore1.22938669. Keepallcells;doNOTclaimallnormssmall orGPUcertificationfromCPUtests. ThisfactresultisforU40alpha8/frozencontinuationcontrast, notuniversalcausalarrival/naturalstateclaim. EarliestcompleteE126native15:54:28.451782CET follows§23514:41:16/e9c1clarif15:09:28/adapter901d15:15:46/hook049715:16:36;fullolderfailed/discardedattemptinventorynotnewlycertified. Clean-locatorbindinge79a19:40:01ispostcapturecustodyreuse,notnewacquisition.

E123primaryR-DIS1 NOT MET BOTH own=worker(originalseal0c4fd523/publishedsealedrun): factAUROC.8869047619047619CI[.8452380952380952,.9285714285714286],47stale/84unhooked,FPR19/84=.2261904761904762>.15;languageAUROC.5568181818181819[.44349053616661976,.6744642857142857],22stale/32unhooked,FPR8/32=.25>.15. Registeredlanguagepoint“notusable”<=.60holds,butAUROCisnotclaimedmissingnessrobust. FPRfailurealoneisrobusttocompletingmissingunhookedpairs:languagebest8/50=.16still>.15;factunhookedmissing0. No universaldeploymentprecisionclaim.

E123independent16seal/587memberchecks(notassertedunique),804originalitem/condition/layercode-textidentityjoins exact;134originalE104flippedIDs/oldtargets unchanged.55terminalmissingcells(32reusedE109+23newE123)retained;languageparseablepaircountssteered35/random36/unhooked32of50, nozero/imputation. ALL333publishednumericfields(primary2AUROCs/bootstrapCIs,missingcensus,Wilsonoperatingpoint/coverage/abstentions/fullrow52baselines/posthoc35)exact; registeredfrozenE94Wilsonz1.959963984540054reproduced(common.statsdefaultz1.96maxendpointdiff3.5874641296507193e-6,explicitnotmetricchange). Independentlyall2000/2000itemclusterAUROCdrawsDEFINEDinBOTHrows, so3ba3>=1900gatepassesonactualretaineddata;undefined0. No conditionaldropissueaffectstheseretainedprimaryCIs.

E123clarification1DISCREPANCYRETAINED: authorrules931adcstillomitexplicit>=1900admission/conditional-defined-CIlabelanddual-as-stalesensitivity/categories; executedprimarycannotbecalledfullsourceconformance. R-QREQUIREDsensitivitycomputedindependentlyWITHOUTauthorreplay: factno dualcells/primaryunchanged;languageDUALcells44/52 steered[3,3],random[3,0],unhooked[1,1]. Withdualcountedasstale,languagepositive25/TP11,AUROC.595CI[.4834195402298851,.7136953391103986],2000valid/0undefined,FPR8/32=.25,R-DIS1stillNOT MET. TheseareREVIEWERcompanionnumbers,notrewrittenworkeroutput. KeepprimaryexclusiveOLD,reportdualsowncategory; requestadjacentNONEXECUTINGerratum/companion,NEVERresetoriginalguard/rerun/rejudgetorepairpresentation. Sensitivitymatchesprimaryverdict,notprimaryestimate.

E123POSTHOCnote1verifiedfromoriginalE121sealedSOURCEreferencesonly(noE121analyze()/guard/refit/testreview):exact35Oracle/NLAstale-consensusIDs,all35disagreeOracle44/52,Wilson[.9010990076755959,1];same35block52steeredNEW35/35/unhookedOLD35/35/randomOLD32/35. Coverage/abstention/operatingpointandfull84/50rowbaselinesallmatch;no membershipselectedonE123/E10952outcome,and35-casecontrolprecisionNOTdeploymentprevalence. No newconfirmatoryrule/pairedcomparisonagainstE94differentdistribution.

ActualretainedCPUchronology(allCET): §2383505 00:29:16<source6dcd00:34:04<RQGO9368 00:37:08<E127devguard00:37:42.625081<RESULTS.628470<seal.628910;E126guard00:37:47.981076<RESULTS00:37:48.685762<seal.686796. E123SPEC09a3committed00:35:14<guard00:39:39.547691<RESULTS.848346<seal.848920,executedHEADf796(existingcodebytes16f0source)withcanonical3ba3predatinganalysisbutomittedpiecesdisclosedabove. All3guardsCONSUMED/immutable,NOreviewerentrypoint/authorguard/fit/model/API/newGPU/judgecalls. Noearlierfirst-everhistory/unknownfirstopeningtimeinvented. New§238clarif1E120c00:39:04read,R2scopeonly/noRQendorsement. Foreignf0198c75514151299ec9aab970aabe8b855baff5retainedforrestoreafterpublication;oldforeignhashesalreadyrestored/neverreapply.


## 2026-10-30 01:00 CET — new §238 clarifications 2–3, reviewer descriptive companion

1771e57beactual00:45:39/fa29a17f400:47:28bindE117cFACTpositivecontrolBEFOREitsunsealedanalysis: targetedS>=.50 ANDshamyes<=.20=>interfaceworks, targetedS<=.20=>questioninterfaceunvalidated, intermediateas-is; retainvalue-questionvsyes/noformatcaveat. Factcontrol84isE56lineage(earliersealedconsistency168PASS),notE57asclarificationproseparenthesisstates; no newlabels/originalrowselection. Primarybookkeeping/missingnessrulesunchanged; noE117cdata/scoringopenedhere. E85readoutBOW/E120ccomparisonbelongR2, notR-Qnewfit/review.

c57afb4a6actual00:46:43 addsprobabilitymass/greedy-agreementandE12932tokenwindow. Heading “before E127/E128 deviation1 runs” isPOSTactualE127devguard00:37:42.625081andpublishedresult00:38:48; newdescriptivecompanionmustbeidentifiedPOSTdev1result,notretrospectivelypre-run. Originalcriteria/numericreviewunchanged, no original/deviationguardreplay. Independentreviewercompanionfromsamehash-boundE127step0pair_logprobs andsealedcandidateIDs/greedytokenIDs: ONEpair/item, global-vocabularyprobabilitiesexp(logprobs),notrenormalizedtwo-candidateprobability. Q1/median/Q3 forCOMBINEDcandidateprobability: context_update[.0026532822183411094,.008728139934846398,.01614101534304537];neutral[.0011866552826600056,.005686675720567042,.012398102859974659];noprefix[.0012905600149167697,.0036057815173055796,.008936205104716216]. OLDcandidatequartiles respectively[.0010408929747742503,.0062102733951285025,.010203316298837861];[.0011754086958172484,.005634074449679815,.012397697615481186];[.0012641793943092118,.0035633033545727005,.00893606547225727]. NEWcandidatequartiles respectively[.00004386837761138062,.0004667780951021676,.0020030687380314573];[.0000008823029665310623,.000005012212937909325,.000013159324103784452];[.00000015114229930676822,.000004709748739926481,.000025312710663169592]. TheseareREVIEWERaggregates,notrewrittenauthorseal; usepublishedcompanion/erratumadjacentoriginaldeviation.

Greedy-first-tokenIDagreementwithpreferredcandidateis0/84ineachcondition;all84decodedsubjecttextsperconditionbeginwhitespaceandoneuniqueinitialtokenIDacross252. No actualtokens/valuesprinted; existingBfirst-decoded-tokenwhitespacecategoryreportconsistent,independenttokenizer-IDdecodingnotclaimed. Therefore41/84mustbecalledSUBJECTMODELANSWERPREFERENCEflips,notgreedyanswers/readerflips. Readerjudgmentsremaintext-only. ExistingE109reader84/84laternewvaluereportandE104judgmentchangearecorroboratingREADERobservations,notdirectproofsubject32tokengreedytextchanged;donotpromotethatcircularinference. E129mechanicaltriggerfromSEALEDdev1already41<50satisfied, butprospectiveacquisitionNOWrequires32-tokencontinuation/textclassifierwithpairpreferencebeside(clarif3supersedesearlier3token/pair-primaryE129wording);source/test/CPUbindingbeforeGPU,noRQselection/launch/pooling. SourceadditionaldiagnosticcompanionandE117cpositivereadingmetadataremainownerpublicationduties,notreason toresetconsumedguards.


## 2026-10-30 01:05 CET — E129 authoritative design cancellation (§237/238clarif4)

e97f837b0actual00:49:03CET(NOMINAL01:25)SUPERSEDEStrigger-ready/heldE129statuses: E129NOT RUN(design),mechanical41<50triggerfiredbutcoordinatorcancelssame-prefixdesignbeforeANYE129output. AlreadyindependentlyverifiedE127dev1selectedneutral44old2/41=.0487804878(Wilson[.0134806623,.1613926696])fails>=.80;SAMEselectednoprefix44old24/40=.60,1missing/41planned. No rerun/recalculationofclosed18rates;figuresreadfromverifiedsealedresult. Controlfailure/design-confounddecisiondoesNOTproveeachreadoutmerelyechoesprefixorstateabsent. E129stopwatch/selection/launchrequests;freshno-prefix-confoundcontextdesignresearchphaseonly/nopooling.32tokenfuture-familyrequirementretainedforresearch,butNOTauthoritytosalvagerunE129. E85groupedCVclarificationR2outsideRQ/no newfit. OriginalE127devNE-gate/descriptiveonly/RQnumericalreviewandE126MET/E123NOTunchanged. Privateforeignf0198c75514151299ec9aab970aabe8b855baff5stillretainedpendingrestore/allolderrestored.


## E117c sealed independent numerical review — 2026-10-30

Public59ec437d8/originalseal b97adac0b83b064a6fd7ccda83a451dce0582e732ef152d437aad9f86ccf0636; finalSPEC5c412e89/binding6bbbf6ad/inventoryv2 7ede6c4a. Independent reviewer source-pointer computation (no author inputs/analyzer/guard) reproduced all672 original item/arm/block/prompt/code/text joins,75 terminal-missing scores, and all8 signed-S point/2000-draw CI triples EXACT (joint within-row item draws, seed20261027, frozen E100 row stream order). Previously closed E56/E57 letter checks and native/bank hashes not repeated. Four new binding/inventory/analysis member checks exact; original local BINDING equals public SPEC, public RESULTS equals original. Inventoryv2 changes prompt seal-index representation only; final post-output metadata is custody, not a newly prospective question plan.

- Bookkeeping targeted S own=worker: nesting_depth −.2241379310 CI[−.4182272727,−.0178493108],58/84 known; indent_level −.0243902439 CI[−.0617283951,0],82/84; page_range_digit .1190476190 CI[−.0357142857,.2738095238],84/84. Sham signed S own=worker .0256410256 (39/84),−.0595238095 (84/84),−.1428571429 (84/84), respectively; signed S is not sham yes rate. Registered leading-word yes/no extractor has **0/336 matches on original raw sham texts**, independently verified before any terminal filtering. Thus each sham yes denominator0/84,336 extraction-missing distinct from75/672 terminal judgment missing. Both registered bookkeeping readings **NOT EVALUABLE**, not zero sham rates or recovered/absent state claims. Both-arm79/84 observability gate fails for every row because sham extraction is unknown. No replacement parser/code interpretation or pooled/fact rescue.
- Separate §238clarif2/1771 fact positive control own=worker targeted S .7857142857 CI[.7023809524,.8690476190],84/84; sham signed S .7317073171 CI[.6296296296,.8192771084],82/84, but sham yes **unknown0/84**. Required targeted≥.50 AND shamyes≤.20 conjunction is **NOT EVALUABLE**. High fact S does not establish that E120c null is state-specific; low-S≤.20 reading also not established. Preserve value-question versus yes/no caveat; fact row E56 lineage. Worker and reviewer verdicts agree,0 numerical discrepancies.

FinalSPEC commit00:54:43CET < executed source7ba4a4a00 COMMITTER00:57:24CET < public result00:58:27CET. Original filesystem times UTC: {"ANALYSIS_ONCE.json": "2026-10-29T23:57:40.120338+00:00", "RESULTS.json": "2026-10-29T23:57:40.120588+00:00", "ANALYSIS_SEAL.json": "2026-10-29T23:57:40.120974+00:00"}. These establish located execution timing, not all earlier opening/discarded history. Original part-c guard consumed and NEVER reset/replayed. No main-grid outcome/norm/token accounting opened. E128 still awaits scientific seal; E123 nonexecuting companion pending, all prior reviews preserved.


## 2026-10-30 — §217 arriving custody and nonexecuting companions

E128 judging DELIVERED5e8da1787: independently archive675f1fac (529594bytes) all682 public file pins/683files EXACT, publicphase1c36f54c/originalphase92e3aa22; canonicalbank3cf24f5e 3pins,originalCPUphase7pins,keyedhandoffa6c298ca1pin,publicbank2pins exact. 672=671kept+1terminalmissing; USD.34651900+2.65348100 unused=original3,unknown/reserve0,owner reports once-only release. No semantic judgment/readout/pair/signal opening or adapter/guard. Final SPEC/scientificseal pending; bank COMPLETE is not scientific completion.

E123 nonexecuting companion905f28bfa/seal9be109e9 and E127 answer-preference companion8438329b1/seal524e6722: both REPORT.json/REPORT.md hashes exact. Reporting companions match previously independently reviewed numbers and caveats: E123 dualcount11language/0fact,conditionalCI2000/2000each,language sensitivity.595[.4834195402,.7136953391]/25stale,FPR8/32 and originalRDIS1NOTboth; original missing1900 sourceguard disclosed. E12741/84 subject-answer-preference/0of84firstgreedyagreementeach/global-vocabulary probability quartiles and post-result chronology match prior R-Q companion. Publication requests CLOSED; no repeated raw audit/bootstrap or guard, no original source-conformance certification or changed verdict. Companion provenance attributes E123 numbers to R-2, E127 to R-Q; numerical agreement checked against our already published results.

New BRIEF authority read in full: §23919763a3d1 actual01:03:37CET registers E131/R-Q, sourceff9fdc893actual01:08:34; §240272e3fd35actual01:22:41 assigns E132/E107b toR-2, research programme not registered execution. E131 source intake: all186 shared runtime pins+source/archive hashes exact; input3/CPU2pins exact; independent all840 original source token/read-index/ordered single-token-pair joins/504 composedfloat32 deltas byte-exact, same84 across10conditions. Reviewer ran13 existing PURE synthetic runner cases PASS (real-packet worker test deselected, replaced by own direct independent input check); no author build/load/acquire/guard or real model. Source generation≤64, original-position U hook every forward, same-pass first-step pairmeasure, greedy/EOS retention/no padding; caller owns originalclock/need/cap. This is source intake, not launch authority or adapter GO: B testedcommitted CPUclassifier/analysis source still awaited before production asregistered. No selection/output reviewed. R-TX1 E104steered textnew≥.80/WilsonLB>.65 AND amongvalue-text agreement≥.90; falsifier textnew≤.50; other9 conditions descriptive, E127 text-defined rates/E128 textalpha_min beside pair measure, no silent replacement of old seals.

Coordinator reading notes8c9568e12 are labelled posthoc/descriptive, not new E117c rule or causal question-invariance test: marginal signedS alone does not establish paired equivalence; registered NE sham extraction remains. E85/E130 new outcomes outside R-Q ownership not re-reviewed. E95 remains last under paidcutoff; no newbudget/cap/launch. All closed reviews and prior first-ever chronology caveats preserved.


## §241 E133 — direct Guiv prospective reviewer intake

Registratione0383c003 actualCOMMITTER2026-10-30T01:39:22+01:00 (nominal02:00) read in full. Direct Guiv assigns R-Q review; B must commit/test the re-pointed E126+E127 adapter BEFORE ANY E133 output, including screening output, with R-NL1/falsifier/descriptives and frozen parse_target_answer on32-token text. No adapter/source or E133 output published in shared tree at09aa50e27, so prospective implementation/timing review PENDING, not GO. R-Q does not implement another owner's adapter or invoke worker entrypoints/once guards. C bank≤USD4/E104rubric current/previous/other/none, explicitly authorized by this direct human message, queued immediately after E117main; no R-Q admission/payment/ledger/API action or appmessage.

Registered selection:300multi-hop/150one-hop candidate PAIRS, keep both-member current-correct pairs using subject32-token greedy answers ONLY; first84multi-hop/42one-hop in frozen generation order, fewer if needed; <50multi-hop descriptive-only. Current/previous/other/none orientation and pairs/individual-item denominators must stay explicit; never select by Oracle/probe or pair preference. Frozen readout layers44/52/60, residuals36/44/48/52/56/60; probe devfirst30multi-hop pairs/testrest, no leakage across pair members. Patching swaps paired read-token states at44/48/52/56/60, onehop44/52; per-item ratio (patched−own)/(other−own) before median, controls and original clean/paired baselines hash-bound. No inherited alpha8 steer or source outcome reused as E133.

R-NL1 all three: previous44≥.30/WilsonLB>.20 AND current44≤.40; current60≥.70; medianR52or56≥.50/bootstrapLB>.25 AND R44≤.15 AND controls≤.15. Falsifier current44≥.70/LB>.55 OR R44≥.50. Between as-is. One-hop/probeAUROCs/previous-holdertrace/text-preference agreement descriptive. Test adapted source/rules/denominators/missingness/zero-gap handling/prospective frozen classifier against exact committed source before outcome review; no silent carry-over conventions from unrelated contrasts. First-ever output/screening/seal times needed, not headings; missing history unverified.

GPU≤.9GPUh total(.1screen+.8main)/one§234measured re-attempt, original ceilings/custody/clocks, creationFri11CET/seal14CET/hardstopmin(cap,12:50Z); no mainpod by11=>NOTRUNoperational/researchphase. E133 priority aboveE131 nextH200; sharedpod only if sealed packet carriesboth. PaidwindowFri16CET/15Z and reviewerFri18CET/17Z preserved. No reviewer launches, new allocation or cap resets. E128 existing SPEC now delivered (65586d901/69af33cc) but scientificseal still awaited; prior reviews preserved.


## E133 prospective source intake — §242/clarifications, 2026-10-30

Read every new BRIEF amendment: §242ab1361764actual01:47:19CET, clarifications e39e8f475actual01:54:45. E134 belongs R-3, not R-Q; research-phase designs not executable registrations. E133 SAME combined bank raised≤4→≤5, not another allowance/reset; bAbI QA2 current-location TEST only, QA3 historical questions excluded, first42 both-member-correct pairs sourceorder, DESCRIPTIVE SEPARATE, never pooled R-NL1. Packet readiness08CET cutoff. Latest explicit one-pod total3240s/.9GPUh fromcreation/hardstopmin(cap,12:50Z) supersedes split clocks; do not add/reset screen clock. R summary median over both per-prompt ratios with2000 PAIR draws/seed20261027, both controls all5blocks≤.15. Probe primary binary twin identity, previous-holder descriptive macroOVR; group by pair. These are answered rules, not fresh questions to Guiv.

Sources3aebc94dc runner and a2d4defb4 adapter are committed before located E133 output (none published), but **prospective end-to-end implementation NOT YET VERIFIED/NO GO**. Current adapterPROTOCOL remainsCLARIFICATION_PENDING (safely blocks productionrun); current-name macroOVR probe target differs from accepted binary twin identity, bank4 cap check excludes canonicallyallowed5, bAbI family absent fromscreen/rules/runner. Freeze/test accepted protocol and required arm/source integration before affected output; no repeated permission request.

Concrete source-integration finding: runner INPUT_CONTRACT/validate_items uses first candidate pair=COMMON ordered recipient0/recipient1, plus member-specific current/previous pair. Adapter.inputs.score currently passes ALL rawpair_logprobs to E126log_odds(...pair_count), and nativepreference averages ALL rawpair_logits; it does not independently select the two registered contrasts. With a genuine two-pair native record it either rejects pair_count1 or averages mismatched contrasts whenpair_count2; identity attestations alone do not change actual array arithmetic. Pure synthetic native-shaped fixture: common recipient own−2/other+2/patched0 gives registeredR=.5, but adding current/previous own0/other20/patched0 makes current mixedR=.0833333333. Requires prospective tested source selection of ORIGINAL common-recipient pair for every own/donor/patch (and separate current/previous pair for preference), preserving raw IDs/arrays/order; no copied/relabelled numerical records. Existing adapter fixtures only use singlepair and do not cover this shape. This is a source finding before execution, not a real-data discrepancy or E133 result.

Runner193runtimepins/sourcearchive18c0c153 exact; adapter16dependencies exact including unchangedparse_target_answercf6bc5ed. Reviewer executed41existing PURE synthetic tests (20runner+21adapter/rules/screen/probes) PASS, temporary-onlyguards; does not establish amended protocol/native two-contrast compatibility. No author real build/load/acquire/screen/select/adapter/guard/model invoked. Pure committed screen unit tests verify first84/42ordered/bothmemberscorrect/fewerthan50mode/previousholder/noalias; real-screen cohort not opened.

W-text bank1936f9676:5sharedbankpins+4originalCPUbankmembers exact/publicarchivee0459aefsolememberitems.json;900 unique id/prompt records,450 pairs. Independent originalprose/current/previouslabels900 and finalrecipient-only twins450 exact; 300MH/150onehop. Source public schema id,prompt ONLY differs from runner token/pair/family/member/candidate schema; needs tested custody/tokenization adapter, never regenerate or stage CPUkeys. Role-bearing token-pair contrast handling must be explicitly source-bound; no blanket runner compatibility claim. Tokenization4500boundarychecks are ownerreceipt only at this pass, not independenttokenizer replay. bAbIfaa0b176b custody:publica7bd9438/2members+CPU9364a864/1member,publicdf2656dc/builderarchive7797c0af/downloadreceipt5652987c hashes exact;494QA2candidatepairs988prompts,QA3all1000ineligible perreceipt. Independent dataset-state/twin replay remainsPENDING; no source code fromdataset executed/no outputselection.

E133 candidate packets delivered, screening/productionoutput unsealed at23510d80d. Original bank/nooutput timing is located history, not first-ever certification; protocolamendment follows initialadaptercommit by29seconds and must be implemented before production. E128scientificseal/E131analysisadapter still awaited, prior closednumerics unchanged.


## E133 required pre-pod adapter re-check — GO for corrected source f483862d4

Coordinator434061b36 item2/direct Guiv requires this check before E133 pod creation. **Required adapter contrast-fix check PASS/GO**, exact publishedf483862d4actualCOMMITTER02:07:58CET, adapter SHA b4fb0b66bdafe3f00d44f13789ac7f34d0b7561cc2f4624636d6a6b1c249e1b2. All12packagefiles byte-identical to thatGitcommit,16dependency pins exact, parse_target_answercf6bc5ed unchanged, protocolFROZEN. Reviewer ran29PURE testsPASS in checkout AND29PASS from exact committedGitextract with its pinned dependencies; initial extract omittedscore94 dependency and was repaired before successful test, no scientific source changed.

Independent pure reviewer computation (no authorrealinput/guard): ORIGINALcommonrecipient indices[0] own−2/other+2/patched0 with extra currentprevious0/20/0 yields bothmemberR=.5,median.5,2000pairbootstrapCI[.5,.5]. OLDmixed1/12 reproduced only asinvalidcounterexample. Opposite-sign preference: commonpair+100,currentprevious−1=>selectedcurrentprevious−1,never mixed+49.5. Committed fullsyntheticbinding test also covers ALL5blocks/ALL3controls, opposite-memberpreference and unchangedrawarrays/IDs/order. original_pairs selects source rows without rewriting/reserializingrawmeasurements. Real E133 analysisguard ABSENT atcheck; no real nativeoutput/screeninganswers/model/API/pod operation or selection opened by R-Q.

§242clarif1/2 now implemented in Bsource: per-promptmedian/2000pairdrawseed20261027,bothcontrolsall5; binarytwinprimary plus separate currentANDprevious fixed-namemacroOVRdescriptives, devfirst30MHpairs/testrest/no pairleakage/probesnotinRNL1; bAbIQA2separate42/QA3ineligible/samecombinedbank≤5. FIRST_OPENING receipt added before firstoutcomejoin afteronceclaim; does not independentlycertify prehistory. Prior R-Q sourcefinding CLOSED for corrected adapter; no additional R-Q permission/repeatfixture required for this completed prerequisite. Final actual source/index/axis signs/IDs and fullbindings remain mandatory original custody checks, not waived by syntheticGO.

New authoritative BRIEFclarif2: ifbAbIsealedbeforecreation total1.2GPUh4320s,else.9GPUh3240s/bAbINOTRUN; creation10Z/hardstopmin(cap,12:50Z),no reset. Allowed pair/family/member and fixedorderedcandidateIDs, CPUroles/signs staylocal. Coordinator434061b36also reassignsE128analystW-mech2, paidorder is priority/parallel-readywithsamebanks/15Z, requests prospective reproductions E128/E133/E131/E117main. ThisGO satisfies item2 only; operator still applies source/runtime/clock/budget/oncepreflight; no reviewerlaunch or expanded authority.


## Prewritten independent reproductions — coordinator434061b36 item4/direct Guiv

Runnable reviewer-only metric code and original-pointer resolvers are preserved below inside the two permitted reviewer files, not new scientific source files. Extract first Python block to `/tmp/rq_prospective_reproductions.py`, second to `/tmp/rq_reproduction_synthetics.py`; execute with the registered Python, PYTHONPATH=this worktree, single BLAS/OMP thread, no bytecode. Default test script uses PURE synthetic data only; no actual outcome file/worker adapter/input function/onceguard is opened. Metric module imports common.stats and frozen core parser only. Original source-pointer resolution, raw identity checks and metrics are independently implemented; final originalseal+allmemberhash verification required before calling normalizers on outcomes. Labels never printed or published.

E133 correctedsourcef483862d4 GO already publishedffc00b4a8; independent metric four syntheticpair-grids reproduce ALLpatch point/CIs/gates against committedrules, including<50/controls/undefinedgap. E117main four full336item syntheticgrids reproduce192point/CI pairs andbothverdicts exactly against committedadapter; missing andpooleddegeneracy included. E128 four 2/4onlyselection/unknownlower/fallback fixturesPASS, fullcohortmissing-as-failure/success bounds prewritten. New ownercoordinator4bf17ae07 source has arrived and will be compared before actualresult review; olddeviation1alpha8 selection is NOT the 434061b36rule. E131 two full synthetic text-gate fixtures PASS; Banalysisadapter still absent atcurrentcheckedsharedtree, so registration-based metric prototype/native-source resolver prepared but exact futureauthor-source comparison remains pending. No false claim of receipt/codepre-review.

E117production token diagnostics remain gated on source generation_config/kwargs/EOS/padding proof; never count postEOS padding or retokenize. Privacy companion masks8sourceboundjudgment scores ONLY, original tokens/degeneracy untouched; reproduction accepts exact validatedjudgmentIDs privately, no membershipselection. Primary andcompanion samepairedgrid. Finalnorms/sourceprivacybindings remain necessary.

Latest§241/242clarif3 4ba8e1fb2 read in full: total1.5GPUh5400s fromcreation/hardstopmin(cap,12:50Z),samepod syntheticfirstthenbABI/ownforecast; bABI canonical494QA2bank notWtext104, episodeclusteredCIs/probefolds. This changes ONLY bABI inferenceunit from priorpairtemplate; script below's primary E133 pairroutine applies to syntheticMH/onehop. bABI episode-clustered extension/finalauthor-source comparison required before bABI outcome computation; do not silently run pairCIonbABI. E134R3ownership unchanged. E128authorsealec43945bf arrived whileprewriting; this preparation is BEFORErevieweroutcomeopening, NOT claimed beforeauthoroutput or a fresh preregistration. No actualE128RESULTS opened atthisrecord.

R-Q_REPRO_CORE_V1, SHA256 2a2eb7547be8551582185be3ab2a50c9345433fe470fa6534526d055498a03f3:

```python
"""R-Q prospective metric reproductions; never imports worker adapters/claims guards.
Only synthetic selftests run by default. Outcome use requires the ORIGINAL COMPLETE_ONCE
analysis seal, a declared experiment and reviewer-normalized original pointer joins.
No scientific input/result/PRIVATE files are written; caller keeps normalization local.
"""
import json,math,re,hashlib,itertools
from pathlib import Path
from collections import Counter
import numpy as np
from common.stats import wilson,bootstrap_ci
SEED=20261027;DRAWS=2000
BOOK=('nesting_depth','indent_level','page_range_digit')
ROW_STREAM=('fact_recall',)+BOOK
BLOCKS=(44,48,52,56,60);CONTROLS=('read_token','earlier_token','random_norm_matched')
def rate(xs):
 k=sum(v is not None for v in xs);yes=sum(v for v in xs if v is not None)
 return dict(planned_n=len(xs),known_n=k,missing_n=len(xs)-k,k=yes,estimate=None if not k else yes/k,Wilson95=None if not k else list(wilson(yes,k)[1:]))
def triple(x,fn=np.mean,ix=None):
 a=np.asarray([np.nan if v is None else v for v in x],float)
 if len(a)==0 or not np.isfinite(a).any():return dict(estimate=None,CI95=None)
 if ix is None:ix=np.random.default_rng(SEED).integers(0,len(a),(DRAWS,len(a)))
 z=a[ix];n=np.isfinite(z).sum(axis=1);d=np.divide(np.nansum(z,axis=1),n,out=np.full(len(ix),np.nan),where=n>0)
 return dict(estimate=float(np.nanmean(a)),CI95=np.quantile(d,[.025,.975]).tolist()if np.isfinite(d).all()else None)
def need(s,p,lb=None):return None if s['estimate']is None else s['estimate']>=p and(lb is None or s['Wilson95'][0]>lb)
def and3(xs):return False if False in xs else None if None in xs else True
def or3(xs):return True if True in xs else None if None in xs else False
def status(v):return 'NOT EVALUABLE'if v is None else'MET'if v else'NOT MET'
def preference(raw,new='A',indices=None):
 if raw is None:return None
 a=np.asarray(raw['pair_logits'],float);assert a.ndim==2 and a.shape[1]==2 and len(a)and np.isfinite(a).all()
 if indices is not None:a=a[indices]
 v=float(np.mean(a[:,0]-a[:,1]))*(1 if new=='A'else-1)
 return 'new'if v>0 else'old'if v<0 else'other'
def signed(code,target):
 if code is None or code['category']=='UNPARSEABLE':return None
 vals=code['values'];return 0 if len(vals)!=1 else 1 if vals[0]==target else-1
def state(code,value):
 if code is None or code['category']=='UNPARSEABLE':return None
 return int(code['category']=='states_value'and code['values']==[value])
def e128(items):
 """84 original records: id,old,new,doses[d][condition]={raw,code[44/52]}.
 raw is original pair-logit record at2/4; at8 frozen E104 pair_flag only.
 Selection uses ONLY2/4. Missing lower dose potentially>=42 stays ambiguous.
 """
 assert len(items)==84 and len({x['id']for x in items})==84
 flags={};rows={};counts={};unknown={}
 for d in (2,4,8):
  for c in ('steered','random'):
   flags[d,c]=[x['doses'][str(d)][c]['pair_flag']if d==8 else None if x['doses'][str(d)][c]['raw']is None else preference(x['doses'][str(d)][c]['raw'],x['new'])=='new'for x in items]
  counts[d]=sum(v is True for v in flags[d,'steered']);unknown[d]=sum(v is None for v in flags[d,'steered'])
  ix=[i for i,v in enumerate(flags[d,'steered'])if v is True]
  rr={c:{str(l):{v:rate([state(items[i]['doses'][str(d)][c]['code'][str(l)],items[i][v])for i in ix])for v in('old','new')}for l in(44,52)}for c in('steered','random')}
  bounds={c:{l:{v:dict(lower=rate([1]*st['k']+[0]*(st['planned_n']-st['k'])),upper=rate([1]*(st['k']+st['missing_n'])+[0]*(st['known_n']-st['k'])))for v,st in values.items()}for l,values in layers.items()}for c,layers in rr.items()}
  rows[str(d)]=dict(flipped_n=len(ix),behaviour_missing_n=unknown[d],rates=rr,worst_case_bounds=bounds,pattern=status(and3([need(rr['steered']['44']['old'],.5,.35),need(rr['steered']['52']['new'],.7)])),worst_case_pattern=status(and3([need(bounds['steered']['44']['old']['lower'],.5,.35),need(bounds['steered']['52']['new']['lower'],.7)])))
 chosen=None;ambiguous=False
 for d in(2,4):
  if counts[d]>=42:chosen=d;break
  if counts[d]+unknown[d]>=42:ambiguous=True;break
 bounds={str(d):dict(flips_lower=counts[d],flips_upper=counts[d]+unknown[d])for d in(2,4)}
 return dict(alpha_min=chosen,selection_ambiguous=ambiguous,R_DOSE1='NOT EVALUABLE'if chosen is None else rows[str(chosen)]['pattern'],counts=counts,missing=unknown,doses=rows,selection_bounds=bounds,alpha8_fallback_only=chosen is None and not ambiguous)
def pair_ratio(own,other,patched):return None if any(v is None for v in(own,other,patched))or own==other else(patched-own)/(other-own)
def median_pairs(values):
 flat=[v for pair in values for v in pair]
 if not flat or any(v is None for v in flat):return dict(estimate=None,CI95=None,n_pairs=len(values),n_defined=sum(v is not None for v in flat))
 a=np.asarray(values,float);assert a.shape==(len(values),2)and np.isfinite(a).all()
 p,lo,hi=bootstrap_ci(a,fn=np.median,n_boot=DRAWS,seed=SEED)
 return dict(estimate=p,CI95=[lo,hi],n_pairs=len(values),n_defined=len(flat))
def e133(pairs):
 """Reviewer normalization holds source pair id/kind/member own common-axis odds,
 per-block/control same-axis patched odds and categorical current/previous flags.
 NEVER mean across different source contrasts; indices/axis signs checked in resolver.
 """
 out={}
 for kind in('multi_hop','one_hop','babi_qa2'):
  ps=[p for p in pairs if p['kind']==kind]
  if kind=='babi_qa2'and not ps:continue
  assert len(ps)<= (84 if kind=='multi_hop'else 42)
  reads={str(l):{k:rate([m['reads'][str(l)][k]if m['reads'][str(l)]is not None else None for p in ps for m in p['members']])for k in('current','previous','other','none')}for l in(44,52,60)}
  patches={str(b):{c:median_pairs([[pair_ratio(m['own'],p['members'][1-j]['own'],m['patches'][str(b)][c])for j,m in enumerate(p['members'])]for p in ps])for c in CONTROLS}for b in((44,52)if kind=='one_hop'else BLOCKS)}
  out[kind]=dict(n_pairs=len(ps),reads=reads,patches=patches)
 z=out['multi_hop'];r=z['reads'];p=z['patches'];low=lambda x:None if x['estimate']is None else x['estimate']<=.15
 later=or3([None if p[str(b)]['read_token']['CI95']is None else p[str(b)]['read_token']['estimate']>=.5 and p[str(b)]['read_token']['CI95'][0]>.25 for b in(52,56)])
 ctrl=and3([low(p[str(b)][c])for b in BLOCKS for c in CONTROLS[1:]])
 nl=and3([need(r['44']['previous'],.3,.2),None if r['44']['current']['estimate']is None else r['44']['current']['estimate']<=.4,need(r['60']['current'],.7),later,low(p['44']['read_token']),ctrl])
 fals=or3([need(r['44']['current'],.7,.55),None if p['44']['read_token']['estimate']is None else p['44']['read_token']['estimate']>=.5])
 return dict(R_NL1=status(nl)if z['n_pairs']>=50 else'DESCRIPTIVE ONLY',falsifier=status(fals)if z['n_pairs']>=50 else'DESCRIPTIVE ONLY',groups=out)
def e131(records):
 """840 same-pass subject64-token records, with CPU original old/new candidates.
 Parser is the unchanged pinned parse_target_answer; stripping whitespace only.
 No matcher aliases/semantic repair, readout-based selection or greedy8 imputation.
 """
 from projects.g_agreement.core.analysis_utils import parse_target_answer
 rows={}
 for name in sorted({r['condition']for r in records}):
  xs=[r for r in records if r['condition']==name];assert len(xs)==84
  answers=[parse_target_answer({'primary':{'candidates':[r['old'],r['new']],'answer':r['new']}},r['raw']['text'].lstrip())for r in xs]
  prefs=[preference(r['raw'],r['new_in_pair'])for r in xs]
  current=rate([int(a==r['new'])for a,r in zip(answers,xs)])
  agreement=rate([None if a is None or p is None else int(p in('new','old')and (a==r['new'])==(p=='new'))for a,p,r in zip(answers,prefs,xs)])
  rows[name]=dict(text_new=current,agreement=agreement,no_unique_value=sum(a is None for a in answers),n=84)
 primary=rows['e104_steered_8'];test=and3([need(primary['text_new'],.8,.65),need(primary['agreement'],.9)])
 return dict(R_TX1=status(test),falsifier=primary['text_new']['estimate']<=.5,conditions=rows)
def degeneracy(tokens,text,missing):
 assert isinstance(tokens,list)and all(type(t)is int for t in tokens)
 return bool(missing or not text.strip()or not tokens or any(len(list(g))>=4 for _,g in itertools.groupby(tokens))or max(Counter(tokens).values(),default=0)/max(1,len(tokens))>.5)
def e117(items,privacy_ids=()):
 """336 original ids; row, arms[1/2/4][T/W/R] score/degenerate/norm_ratios/id.
 On raw normalization compute degeneracy ONLY on true generated EOS-trimmed nativeIDs
 supported by sealed generation_config/kwargs proof; NEVER postEOS pad or retokenize.
 privacy_ids mask score only on the same grid; degeneracy is original, unchanged.
 """
 assert len(items)==336 and len({x['id']for x in items})==336
 rng=np.random.default_rng(SEED);rows={}
 for row in ROW_STREAM:
  xs=sorted([x for x in items if x['row']==row],key=lambda x:x['id']);assert len(xs)==84
  ix=rng.integers(0,84,(DRAWS,84));rows[row]={}
  for alpha in('1','2','4'):
   cells={};diagn={}
   for arm in('T','W','R'):
    zs=[x['arms'][alpha][arm]for x in xs];v=[None if z.get('judgment_id')in privacy_ids else z['score']for z in zs];cells[arm]=v
    norms=[v for z in zs for v in z['norm_ratios']]
    diagnostic=dict(degenerate=sum(z['degenerate']for z in zs),fraction=sum(z['degenerate']for z in zs)/84,norm_ratio_mean=None if not norms else float(np.mean(norms)),norm_ratio_count=len(norms));diagn[arm]=diagnostic
   stats={a:triple(v,ix=ix)for a,v in cells.items()};t=np.array([np.nan if v is None else v for v in cells['T']]);r=np.array([np.nan if v is None else v for v in cells['R']]);tt=t[ix];rr=r[ix]
   def means(a):
    n=np.isfinite(a).sum(1);return np.divide(np.nansum(a,1),n,out=np.full(DRAWS,np.nan),where=n>0)
   draws=means(tt)-means(rr);delta=dict(estimate=None if np.isnan(t).all()or np.isnan(r).all()else float(np.nanmean(t)-np.nanmean(r)),CI95=None if not np.isfinite(draws).all()else np.quantile(draws,[.025,.975]).tolist())
   rows[row][alpha]=dict(**stats,T_minus_R=delta,diagnostics=diagn,excluded=sum(v['degenerate']for v in diagn.values())/252>.20)
 positive=[];low=[];unknown=[]
 for row in BOOK:
  eligible=[v for v in rows[row].values()if not v['excluded']]
  positive.append(any(v['T_minus_R']['estimate']is not None and v['T_minus_R']['CI95']is not None and v['W']['estimate']is not None and round(v['T_minus_R']['estimate'],12)>=.3 and v['T_minus_R']['CI95'][0]>0 and v['W']['estimate']<=0 for v in eligible))
  low.append(bool(eligible)and all(v['T_minus_R']['estimate']is not None and v['T_minus_R']['estimate']<=.1 for v in eligible))
  unknown.append(not eligible or any(v['T_minus_R']['estimate']is None or v['T_minus_R']['CI95']is None or v['W']['estimate']is None for v in eligible))
 ctl=[v for v in rows['fact_recall'].values()if not v['excluded']];moved=any(v['T_minus_R']['estimate']is not None and round(v['T_minus_R']['estimate'],12)>=.3 for v in ctl);cu=not ctl or any(v['T_minus_R']['estimate']is None for v in ctl)
 return dict(R_IR1='MET'if sum(positive)>=2 else'NOT EVALUABLE'if any(unknown)else'NOT MET',falsifier='MET'if sum(low)>=2 and moved else'NOT EVALUABLE'if any(unknown)or cu else'NOT MET',rows=rows)
def verify_analysis(p,digest):
 p=Path(p);assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
 s=json.loads(p.read_text());assert s.get('status')in('COMPLETE_ONCE','COMPLETE')
 for f,h in s['files'].items():assert hashlib.sha256((p.parent/f).read_bytes()).hexdigest()==h
 return s
class Sources:
 """Reviewer-only original hash-bound reference resolution. Never writes or claims."""
 def __init__(self,source_seals):
  self.sources=source_seals;self.seals=[];self.cache={}
  for s in source_seals:
   p=Path(s['seal']);assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256'];self.seals.append(json.loads(p.read_text()))
 def ref(self,z):
  i=z['seal_index'];assert type(i)is int and 0<=i<len(self.sources)and z['member']in self.seals[i]['files'];key=i,z['member']
  if key not in self.cache:
   p=Path(self.sources[i]['seal']).parent/z['member'];assert hashlib.sha256(p.read_bytes()).hexdigest()==self.seals[i]['files'][z['member']]
   self.cache[key]=np.load(p,allow_pickle=False)if p.suffix=='.npy'else json.loads(p.read_text())
  v=self.cache[key]
  for k in z['keys']:v=v[k]
  return v
def read_json(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal_members(p,h=None):
 p=Path(p)
 if h:assert sha(p)==h
 s=read_json(p)
 for f,digest in s['files'].items():assert sha(p.parent/f)==digest
 return s

def normalize117(spec,*,real_generated_tokens_verified=False):
 # Production use remains blocked until original generation/EOS/padding evidence is checked.
 assert real_generated_tokens_verified,'EOS/generation_config proof must precede token diagnostics'
 bp=Path(spec['binding_seal']);b=seal_members(bp,spec['binding_sha256']);src=Sources(b['source_seals']);out=[]
 for x in read_json(bp.parent/'MEASUREMENTS.json'):
  ident=src.ref(x['source_id']);assert ident==x['id'];row=src.ref(x['source_row']);target=src.ref(x['target_letter']);arms={}
  for alpha,am in x['arms'].items():
   arms[alpha]={}
   for arm,z in am.items():
    assert src.ref(z['source_id'])==ident and src.ref(z['alpha'])==int(alpha)and src.ref(z['arm'])==arm
    code=src.ref(z['code']);assert code is not None and code['id']==z['judgment_id']
    text=src.ref(z['text']);tokens=src.ref(z['token_ids']);score=signed(code,target)
    arms[alpha][arm]=dict(score=score,degenerate=degeneracy(tokens,text,score is None),norm_ratios=src.ref(z['norm_ratios']),judgment_id=z['judgment_id'])
  out.append(dict(id=ident,row=row,arms=arms))
 return out

def normalize133(spec):
 ip=Path(spec['inventory_seal']);seal_members(ip,spec['inventory_sha256']);inventory=read_json(ip.parent/'PAIRS.PRIVATE.json');op=Path(spec['output_seal']);meta=seal_members(op,spec['output_sha256']);assert meta['inventory_sha256']==spec['inventory_sha256']and meta['no_steer']is True
 src=Sources(meta['source_seals']);grid={x['pair_id']:x for x in read_json(op.parent/'MEASUREMENTS.json')};assert set(grid)=={x['pair_id']for x in inventory};pairs=[]
 for p in inventory:
  pair=dict(pair_id=p['pair_id'],kind=p['kind'],members=[])
  for j,(label,z)in enumerate(zip(p['members'],grid[p['pair_id']]['members'])):
   def identity(cell,mode,block=None,control=None):
    q=src.ref(cell['identity']);assert q['pair_id']==p['pair_id']and q['item_id']==label['item_id']and q['member']==j and q['mode']==mode and q.get('block')==block and q.get('control')==control
    return q
   def odds(cell,mode,block=None,control=None):
    q=identity(cell,mode,block,control);raw=src.ref(cell['raw']);assert raw['id']==q['raw_id']and q['contrast_sha256']==p['recipient_contrast_sha256']
    ix=p['recipient_pair_indices'];assert len(ix)==p['pair_count']and len(set(ix))==len(ix)and all(type(k)is int and k>=0 for k in ix)
    a=np.asarray(raw['pair_logprobs'],float)[ix];assert a.shape==(len(ix),2)and np.isfinite(a).all()
    if mode=='patch':assert q['donor_pair_id']==p['pair_id']and q['donor_member']==1-j and q['patch_binding_verified']is True
    return float(np.mean(a[:,0]-a[:,1]))
   reads={}
   for layer in(44,52,60):
    cell=z['readouts'][str(layer)];ident=identity(cell,'readout',layer);code=src.ref(cell['code'])
    if code is None:
     ptr=cell['code'];assert ptr['keys'][-1]=='code';terminal=src.ref(dict(ptr,keys=ptr['keys'][:-1]));assert terminal['id']==ident['judgment_id']and terminal['status']=='UNPARSEABLE'
    else:assert code['id']==ident['judgment_id']
    if code is None or code['category']=='UNPARSEABLE':reads[str(layer)]=None;continue
    text=src.ref(cell['text']);assert code['evidence']in text
    vals={p['value_map'][v]for v in code['values']};cur=vals=={label['current']};prev=vals=={label['previous']}
    reads[str(layer)]=dict(current=int(cur),previous=int(prev),other=int(bool(vals)and not cur and not prev),none=int(not vals))
   blocks=(44,52)if p['kind']=='one_hop'else BLOCKS
   pair['members'].append(dict(own=odds(z['own'],'own'),reads=reads,patches={str(b):{c:odds(z['patches'][str(b)][c],'patch',b,c)for c in CONTROLS}for b in blocks}))
  pairs.append(pair)
 return pairs

def normalize128(spec):
 ip=Path(spec['inventory_seal']);seal_members(ip,spec['inventory_sha256']);items=read_json(ip.parent/'INVENTORY.json');op=Path(spec['output_seal']);meta=seal_members(op,spec['output_sha256']);src=Sources(meta['source_seals']);grid={x['item_id']:x for x in read_json(op.parent/'MEASUREMENTS.json')}
 assert meta['inventory_sha256']==spec['inventory_sha256']and len(items)==84 and set(grid)=={x['item_id']for x in items}
 expected='495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4';assert sha(spec['e104_private'])==expected
 old=read_json(spec['e104_private']);flags={(x['item_id'],x['condition']):x['flipped']for x in old if x['row']=='fact_recall'and x['arm']=='U'};out=[]
 for x in items:
  ident=x['item_id'];ds={}
  for d in('2','4','8'):
   ds[d]={}
   for condition,z in grid[ident]['doses'][d].items():
    codes={}
    for layer,cell in z['oracle'].items():
     ii=src.ref(cell['identity']);assert ii['item_id']==ident and ii['condition']==condition and ii['layer']==int(layer)and ii['dose']==int(d)
     code=src.ref(cell['code'])
     if code is None:
      ptr=cell['code'];assert ptr['keys'][-1]=='code';tr=src.ref(dict(ptr,keys=ptr['keys'][:-1]));assert tr['id']==ii['judgment_id']and tr['status']=='UNPARSEABLE'
     else:assert code['id']==ii['judgment_id']
     codes[layer]=code
    raw=None
    if d!='8':
     cell=z['behaviour'];ii=src.ref(cell['identity']);raw=src.ref(cell['record']);assert ii['item_id']==ident and ii['condition']==condition and ii['dose']==int(d)and raw['id']==ii['raw_id']
    ds[d][condition]=dict(raw=raw,code=codes,pair_flag=flags[ident,condition]if d=='8'else None)
  out.append(dict(id=ident,old=x['old_value'],new=x['new_value'],doses=ds))
 return out

def normalize131(native_output_seal,input_root,cpu_root,orientation_by_original_id):
 # CPU orientation map MUST come from original hash-bound E104 labels; never infer from readouts.
 native=Path(native_output_seal);s=seal_members(native);assert s['experiment']=='E131'and s['status']=='COMPLETE'
 inp=Path(input_root);seal_members(inp/'INPUT_SEAL.json');xs={x['id']:x for x in read_json(inp/'items.json')};cpu=Path(cpu_root);seal_members(cpu/'POINTER_SEAL.json');ls=read_json(cpu/'LABEL_SOURCE.json');assert sha(ls['root'])==ls['sha256'];labels={x['base_id']:x for x in read_json(ls['root'])};index=read_json(native.parent/'INDEX.json');out=[]
 for entry in index:
  x=xs[entry['id']];record=read_json(native.parent/entry['member'])[entry['record']];assert record['id']==x['id']and record['condition']==x['condition']
  base=ls['e131_to_e127_base'][x['base_id']];lab=labels[base];original=lab['original_base_id'];orientation=orientation_by_original_id[original]
  out.append(dict(condition=x['condition'],raw=record,old=lab['old_value'],new=lab['new_value'],new_in_pair=orientation))
 assert len(out)==840
 return out

```

R-Q_REPRO_TEST_V1 (synthetics only):

```python
import importlib.util,copy
from pathlib import Path
spec=importlib.util.spec_from_file_location('rq','/tmp/rq_prospective_reproductions.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
from projects.g_agreement.e117_analysis import adapter as a117
from projects.g_agreement.e117_analysis.test_adapter import fixture as f117
from projects.g_agreement.e133_analysis.test_rules import pairs as f133
from projects.g_agreement.e133_analysis import rules as r133
# E117 source algorithm, paired draw streams and all true/missing/degeneracy conditions.
for case in range(4):
 x=f117()
 for row in x:
  row['arms']={str(k):v for k,v in row['arms'].items()}
 if case==1:
  for row in x[:51]:row['arms']['1']['T']['degenerate']=True
 if case==2:
  for row in x:
   if row['row']!='fact_recall':
    for alpha in('1','2','4'):row['arms'][alpha]['T']['score']=0
 if case==3:
  for row in x[::17]:row['arms']['2']['R']['score']=None
 old=copy.deepcopy(x)
 for z in old:z['arms']={int(k):v for k,v in z['arms'].items()}
 want=a117.analyze(old);got=q.e117(x)
 assert got['R_IR1']==want['rules']['R_IR1']and got['falsifier']==want['rules']['falsifier']
 for row in q.ROW_STREAM:
  for alpha in('1','2','4'):
   for arm in('T','W','R','T_minus_R'):
    assert got['rows'][row][alpha][arm]['estimate']==want['rows'][row][int(alpha)][arm]['estimate']
    assert got['rows'][row][alpha][arm]['CI95']==want['rows'][row][int(alpha)][arm]['CI95']
print('E117: four whole-grid independent reproductions match 192 point/CI pairs and verdicts')
# E133 exact registered paired ratios, gate, controls, early falsifier, zero denominator.
for case in range(4):
 xs=f133(49 if case==1 else 50)
 if case==2:
  for p in xs[:50]:
   for m in p['members']:m['patches'][60]['earlier_token']=m['own_logodds']+.2*(-2*m['own_logodds'])
 if case==3:xs[0]['members'][0]['own_logodds']=1
 normalized=[dict(pair_id=p['pair_id'],kind=p['kind'],members=[dict(own=m['own_logodds'],reads={str(l):v for l,v in m['readouts'].items()},patches={str(l):v for l,v in m['patches'].items()})for m in p['members']])for p in xs]
 a=r133.analyze(xs)[0];b=q.e133(normalized);assert a['R_NL1']==b['R_NL1']and a['falsifier']==b['falsifier']
 for kind,g in a['groups'].items():
  for block,ss in g['patches'].items():
   for ctrl,st in ss.items():
    for key in('estimate','CI95'):assert st[key]==b['groups'][kind]['patches'][str(block)][ctrl][key]
print('E133: four independent pair-grid reproductions match all patch triples and gates')
# E128 2/4-only selection, unknown lower bound, alpha8 fallback, missing raw flag.
def code(v):return dict(category='states_value',values=[v])
def grid(n2,n4,missing2=0):
 out=[]
 for i in range(84):
  ds={}
  for d,n in((2,n2),(4,n4),(8,84)):
   ds[str(d)]={}
   for c in('steered','random'):
    yes=i<n and c=='steered';raw=None if d==2 and n2<=i<n2+missing2 else dict(pair_logits=[[2,1]]if yes else[[1,2]])
    ds[str(d)][c]=dict(raw=raw,pair_flag=c=='steered',code={'44':code('B'),'52':code('A')})
  out.append(dict(id=str(i),old='B',new='A',doses=ds))
 return out
assert q.e128(grid(42,84))['alpha_min']==2
assert q.e128(grid(41,42))['alpha_min']==4
assert q.e128(grid(41,42,1))['selection_ambiguous']
assert q.e128(grid(0,0))['alpha_min']is None and q.e128(grid(0,0))['alpha8_fallback_only']
print('E128: all four lower-dose selection/fallback boundaries PASS; never chooses8')
# E131 text classifier, first-token preference separate, enough text-current/agreement.
records=[dict(condition=c,old='oldword',new='newword',new_in_pair='A',raw=dict(text='\n newword',pair_logits=[[3,1]]))for c in('e104_steered_8','unhooked')for i in range(84)]
x=q.e131(records);assert x['R_TX1']=='MET'and not x['falsifier']
for r in records:
 if r['condition']=='e104_steered_8':r['raw']['text']='oldword'
x=q.e131(records);assert x['R_TX1']=='NOT MET'and x['falsifier']
print('E131: confirmatory positive and falsifier synthetic grids PASS; awaiting author adapter')

```


## E128 coordinator seal — independent reproduction COMPLETE

New analyst W-mech2/source4bf17ae07(actualCOMMITTER02:13:26CET), publishedec43945bf02:14:49; originalanalysisseal9b4c54a4422bb60db12d32899cd68cb4715ec2ec6a6c0e4498eb933c6f8c23c7 verified bothmembers/publiccopy; originalBINDING JSON semantically equals SPEC69af33cc. Same original B DEVIATION1_ONCEguard nowf4bab0432107aa03b457d28bfb37025d1522a2ec11c827e1d4506c3442b452b5,CONSUMED NEVERreplay. Owner/coordinatorentrypoint not invoked;55committedsource PUREsynthetics PASS. Reviewer used the already-written independent source-pointer normalization/metric functions, no authortransport/cohort/input/analyze/guard call.

Own=worker flipcounts alpha2 **0/84**,alpha4 **42/84**,originalalpha8 **84/84**; allnewbehaviour known, rawtarget-oriented pair-logitmeasure only. **alpha_min4**, never8; same42steered-flipped cohort forrandomreadouts. **R-DOSE1 NOT MET**, worst-caseNOTMET. Selectedold44 **4/42=.0952380952**,Wilson[.0376616388,.2206539523],fails≥.50 andLB>.35; new52 **42/42=1**,Wilson[.9161983875,1.0000000000000002],meets≥.70. Preservecommon.stats floating endpoint (no silent clipping). All24condition/dose/layer/value ratecells and observed/full-cohort lower/upper Wilsonbounds: **264statisticfieldchecks EXACT**, includingemptyalpha2 ratesnull/NE,0numericdiscrepancy.

Originalnewdose336nativepairrecordjoins+1008judgmentpointer/identityjoins (672new+336originalalpha8refs) exact IDs/condition/dose/layer; exclusiveold/new, dualnotexclusive, no aliases. One newterminalmissing alpha4steered44 lies OUTSIDEselected42 and does not alterheadlinebounds; distinct oldE104/E109alpha8steered44missing retained (47/83old44 descriptive, no rejudge). Randompopulation is same42, neverrandom-selected. Missingneverzero; lowdoseunknownboundsimplemented/tested thoughactualbehaviourmissing0. This rejects registeredlower-dose staleness pattern, not a proofno externallywrittenstale state; question-open/strongsteercaveat and subjectANSWERPREFERENCEvsactualtext distinction preserved. No textvalidation fromreaderreports; E131 stillrequired. No change to originalE104/E109, no8greedyimputation/run.

Locatedguard02:13:34.737552CET<RESULTS.744787<seal.746912 aftercommittedsource02:13:26, beforepublication02:14:49. Source reviewed afterauthorrun, not falselycertifiedindependentlypre-output; earlierfirst-ever/pilot/openinghistory unverified. Original E128onceguard untouched. Prior bankcustody/packet/sourceaudits not repeated beyond actualnewanalysispointer/hash checks.

## Prewritten bAbI episode extension — no outcomes

New4ba8e1fb2clarification requires original494QA2bank episodes asCI/foldgroups. Additional reviewer-only descriptive interval prototype below resamples WHOLEepisodes (allpairmembers/records staytogether),2000seed20261027. Synthetic mean/median andundefinedratio cases PASS. No bAbIdata/outcomes/actualprobes fit; finalowneramendedsource and episodebindings stillrequired. Does not replace originalsynthetic R-NL1 pairedbootstrap or inventnewbAbIthresholdpredicate. Undefinedratio medianremainsNE/no drop; unknownbinary/readouts useexplicitknowndenominators withundefineddrawcounts. Exact code SHA 18a028cc96993b9d15a449bd9f596c817e306f1606994eb659f04b2c90346bad.

```python
"""§242 clarification3: bAbI descriptive CIs, whole original source episodes.
No episode/pair splitting, no E133 primary pooling, no inferred threshold verdict.
Each row: episode (original source story id), score or R (None stays undefined).
"""
import numpy as np

def episode_ci(rows,statistic='mean',draws=2000,seed=20261027):
    assert statistic in('mean','median')
    groups={}
    for row in rows:groups.setdefault(row['episode'],[]).append(row['value'])
    if not groups:return dict(estimate=None,CI95=None,episodes=0,defined_draws=0,draws=draws)
    episodes=sorted(groups,key=str);arrays=[groups[e]for e in episodes]
    def metric(v):
        # Signed/readout means use known denominator; ratio median never drops undefined R.
        if statistic=='median'and any(x is None for x in v):return None
        known=[x for x in v if x is not None]
        if not known:return None
        return float(np.mean(known)if statistic=='mean'else np.median(known))
    point=metric([v for group in arrays for v in group]);ix=np.random.default_rng(seed).integers(0,len(arrays),(draws,len(arrays)))
    sampled=[metric([v for k in draw for v in arrays[k]])for draw in ix];defined=[v for v in sampled if v is not None]
    return dict(estimate=point,CI95=np.quantile(defined,[.025,.975]).tolist()if len(defined)==draws else None,episodes=len(episodes),defined_draws=len(defined),draws=draws,unit='original episode, all member pairs travel together')

if __name__=='__main__':
    x=[dict(episode=e,value=v)for e,v in [('a',-1),('a',-1),('b',1),('b',1)]]
    for stat in('mean','median'):
        r=episode_ci(x,stat);assert r['estimate']==0 and r['CI95']==[-1.,1.]and r['episodes']==2 and r['defined_draws']==2000
    z=episode_ci([dict(episode='a',value=None),dict(episode='b',value=1)],'median');assert z['estimate']is None and z['CI95']is None
    print('PASS: episode clusters intact for mean/median; undefined ratio remains NE, no pair-level fallback')

```


## E117 main committed-source pre-review and reproduction readiness

DirectGuiv434061b36item4/source225787a695f5615ce72c2f776fc9c58d74279753: all10SOURCE_RECEIPTpins independently match workingbytes AND committedGit,19PUREsyntheticowner testsPASS; no mainoutcomes opened. Reviewer independent fullgridreproduction previouslymatched192point/CIpairs andverdicts over4syntheticconditions. Additional independent privacy-score-only fixture matches ALL48point/CItriples andbothverdicts in the committed sensitivity report; originaldegeneracy/normdiagnostics remain byte-equivalent in the normalized syntheticgrid. Additional test below uses only fake sourcefixtures, no actualeight-IDmap/realreadouts.

Metric/sourcepreparation COMPLETE for currentlycommitted E117main code; actual outcome-opening readiness still requires finalCOMPLETEidentity/judgment/SPEC/sourceprivacybindings and original generated-token accounting/EOS/padding proof. No postEOSpad counts, no newexclusion, no inventedre-tokenization, no authorguard/run. Existingreal E117 main guard not invoked or altered by reviewer. E117c result remains separate/closed.

E128request already fulfilled by successfulindependentrerun onseal9b4c54a4, numericalreview7d1085d97 (final rebasedpublishedhash). E133requiredpre-podfixGOffc00b4a8/metricprewrite349904308; bABIepisodeprototype supplementary, finalamendedownercomparison pending. E131's Banalysisadapter stillabsent incheckedcommittedtree; sourcecode-specificcomparison cannot be certified yet. R-4 published operationalreassignmentACK/prototype32ecb0792; thisR-Qrecord preserves requestedpreparedwork without claiming a secondscientificexecution or reviewingnewoutcomes. No futureadapter/guard assumed/created.

R-Q_REPRO_E117_PRIVACY_TEST (synthetics only):

```python
import importlib.util,copy
from projects.g_agreement.e117_analysis.test_sensitivity import sample
from projects.g_agreement.e117_analysis.sensitivity import report
s=importlib.util.spec_from_file_location('q','/tmp/rq_prospective_reproductions.py');q=importlib.util.module_from_spec(s);s.loader.exec_module(q)
xs,m=sample();want=report(xs,m);inp=copy.deepcopy(xs)
for x in inp:x['arms']={str(k):v for k,v in x['arms'].items()}
base=q.e117(inp);got=q.e117(inp,{r['judgment_id']for r in m})
assert got['R_IR1']==want['result']['rules']['R_IR1']and got['falsifier']==want['result']['rules']['falsifier']
for row in q.ROW_STREAM:
 for a in('1','2','4'):
  assert base['rows'][row][a]['diagnostics']==got['rows'][row][a]['diagnostics']
  for arm in('T','W','R','T_minus_R'):
   for k in('estimate','CI95'):assert got['rows'][row][a][arm][k]==want['result']['rows'][row][int(a)][arm][k]
print('PASS independent privacy-score-only mask: all48 point/CI triples and verdicts match; original diagnostics unchanged')

```


## E131 transfer ACK — coordinator7a7cbe585

Canonical BRIEF coordinator ruling02:25 read: E131 adapterW-text/reviewerR-4 (32ecb0792 prewrittenreproduction); R-Q retainsE117main/E128/E133. Replaces earlier ambiguousoperational transferprose and priorR-Qassignment. Preserve R-Q's alreadywritten registrationprototype as historicalpreparation, no further E131author-source/outcome review, no duplicatefit/selection/guard/retest/requestpublication. E131 original§239scientificrules unchanged; no scientific endorsement fromthisACK.

E128ownerACKcee1fa9bd confirms completed7d1085d97 review; no repeats. E133originaloperatorreports screeninginprogress AFTERpublishedGOffc00b4a8; this is operationalstatus, not scientificseal/result/independentpodclockaudit. All scientificoutputs stillunsealed, no revieweropening or newtest. E117main COMPLETEbinding/EOSproof and E133bABIepisodeextension remainpending; E95no newseal. All closed reviews preserved.


## E133 probe-only phase source review — c09ea3bba/6de411382

Prospective **probe-only lifecycle PASS** (original contrast-fixGOffc00b4a8 CLOSED/not repeated). All14package/source-receipt pins+16dependencies exact against sharedc09ea3bba;35PUREcheckouttestsPASS+35PASS exact committedGitextract. Independent synthetic lifecycle checks BOTHprobe-first andmain-first orders: exactlyONEanalyze/fit invocation, completed originalsameinventory/nativehash probe result reused by main, mismatchedinventory/native source rejected, consumed/in-progress/failed phase blocks repeats; temp-onlyguards. Existingowner tests also verify failedprobe phase prevents mainclaim. Originalrealmain/probeguards ABSENT atreview; no realnative/vector/readout/label outcome opened or fitted. A COMPLETEoriginalnative activationseal+CPUidentity/inventory/PROBE_SPEC binding remains necessary before actualprobephase. No route/judge completion needed for native-onlyfit; finalmain stillneedsjudgments andownonceguard.

Independent nontrivial noisysynthetic LogisticRegressionC1/lbfgs/maxiter2000/seed0 computations: **18primary/current/previous AUROCs** across6sites EXACT vsnewsource, onlyfirst30matchedpairsDEV/restTEST. Independent QA2wholeepisodeGroupKFoldOOF calculations: **3AUROCs EXACT**, zeroepisodeoverlap; fixednames/absent-unseen/nonconverged explicit. Independent source-episode medianpoint and2000drawCI EXACT, group order originalfirstoccurrence (not lexically resorted), allpairs/members travel together. ProbeCIs are not present/no newbootstrapAUROCclaim. Allprobes descriptive relativeR-NL1; no refit/tuning afterheldout.

Chronology: source6de411382COMMITTER02:45:46CET/publicationc09ea3bba02:45:57CET, receipt original93b13738e is rebasedsource lineage, not sharedcanonicalcommit time. This source arrives AFTERQ-reportedcreation01:22:55.310Z, beforelocatedBfit/numericalopening perreceipt; no independent preacquisition/affected-first-output chronology certified. Originaloperatorreceipts remain needed; guardFIRST_OPENING is ownerclock, not historicalcertification.

Residual separatecomponent: §242clarif3 says ALLbAbICIs resampleepisodes. Currentrules.analyze nowepisode-bootstraps PATCHMEDIANS, but QA2READERrateCIs stillcall item-levelWilson `rate(...)`. Thus QA2readerintervals are NOTyet episode-compliant; source extension/test required BEFORE any affectedQA2scientificreport, no claimallbABIinferenceclosed. QcurrentlyreportsbABI NOTRUN(screenforecast); this isoperationaldisposition, not negative science. This residual does not require reopening completed synthetic-primarycontrast/prerequisite or blocking native-onlyprimaryprobephase. No realbAbIoutcomes/judgments counted byreviewer.

New canonicalGPUceilingruling read in full: booked+activecaps≤2500,2000is80%flagnotgate; §211parked900notapplicableto§239–242. No reviewer allocation/reconciliation/launch. E131transferredR4notreviewed. Fullindependent syntheticpreflight below, no realdata artifacts published.

R-Q_E133_PROBE_SOURCE_TEST:

```python
import json,hashlib,subprocess,tempfile,copy
from pathlib import Path
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from projects.g_agreement.e133_analysis import adapter as a,probe_phase as ph,probes,rules
from projects.g_agreement.e133_analysis.test_probe_phase import probe_spec
R=Path.cwd();receipt=json.loads((R/'results/g_agreement/understand/e133/analysis/PROBE_PHASE_SOURCE_RECEIPT.json').read_text());pins=0
for f,h in receipt['files'].items():
 b=(R/f).read_bytes();assert hashlib.sha256(b).hexdigest()==h and b==subprocess.check_output(['git','show','c09ea3bba:'+f]);pins+=1
for f,h in json.loads((R/'projects/g_agreement/e133_analysis/DEPENDENCIES.json').read_text()).items():assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h
# Two execution orders; spy replaces fitting with a synthetic sentinel, never real inputs.
for order in('probe_first','main_first'):
 with tempfile.TemporaryDirectory(prefix='rq_probe_lifecycle_')as td:
  mp=pytest.MonkeyPatch();spec=probe_spec(Path(td),mp);calls=[]
  def once(pairs,names):calls.append((len(pairs),tuple(names)));return dict(primary='binary twin synthetic sentinel')
  mp.setattr(probes,'analyze',once)
  if order=='probe_first':
   ps=ph.run(spec,'reviewer-pure');assert len(calls)==1 and not a.GUARD.exists();before=ps.read_bytes();a.run(spec,'reviewer-pure-main');assert ps.read_bytes()==before
  else:
   a.run(spec,'reviewer-pure-main')
   with pytest.raises(ValueError,match='guard consumed'):ph.run(spec,'reviewer-pure')
  assert len(calls)==1
  with pytest.raises(ValueError):ph.existing('foreign-inventory',spec['native_output_sha256'])
  mp.undo()
# Independent numerical dev-only models on nontrivial noisy pure synthetic activations.
rng=np.random.default_rng(827);names=['A_name','B_name','C_name','D_name'];pairs=[]
for i in range(42):
 members=[]
 for j in(0,1):
  current=names[(i+j)%4];previous=names[(i+2)%4]
  members.append(dict(member=j,current=current,previous=previous,vectors={l:(rng.normal(size=5)+np.array([j*.4,(i%4)*.2,0,0,0])).tolist()for l in probes.LAYERS}))
 pairs.append(dict(pair_id=str(i),generation_index=i,kind='multi_hop',members=members))
worker=probes.analyze(pairs,names);comparisons=0
for layer in probes.LAYERS:
 for target in('twin_identity','current','previous'):
  label=lambda m:m['member']if target=='twin_identity'else m[target]
  tr=[m for p in pairs[:30]for m in p['members']];te=[m for p in pairs[30:]for m in p['members']]
  mod=LogisticRegression(C=1.,max_iter=2000,random_state=0,solver='lbfgs').fit(np.array([m['vectors'][layer]for m in tr]),[label(m)for m in tr]);pr=mod.predict_proba(np.array([m['vectors'][layer]for m in te]));fixed=[0,1]if target=='twin_identity'else names;vals=[]
  for value in fixed:
   yy=np.array([label(m)==value for m in te]);column=list(mod.classes_).index(value);vals.append(float(roc_auc_score(yy,pr[:,column])))
  want=vals[1]if target=='twin_identity'else float(np.mean(vals));got=worker['layers'][str(layer)][target]['groups']['multi_hop_test']['binary_AUROC'if target=='twin_identity'else'macro_ovr_AUROC'];assert got==want;comparisons+=1
# Independent whole-episode folds and OOF metrics (one layer; three targets).
babi=copy.deepcopy(pairs[:12])
for i,p in enumerate(babi):p.update(kind='babi_qa2',source_episode_id='ep'+str(i//2))
mp=pytest.MonkeyPatch();mp.setattr(probes,'LAYERS',(44,));result=probes.episode_cv(babi,names);rows=[(m,p['source_episode_id'])for p in babi for m in p['members']]
for target in('twin_identity','current','previous'):
 label=lambda m:m['member']if target=='twin_identity'else m[target];fixed=[0,1]if target=='twin_identity'else names;x=np.array([m['vectors'][44]for m,e in rows]);y=np.array([label(m)for m,e in rows]);g=[e for m,e in rows];scores={v:{}for v in fixed}
 for train,test in GroupKFold(n_splits=5).split(x,y,g):
  assert set(g[i]for i in train).isdisjoint(g[i]for i in test)
  mod=LogisticRegression(C=1.,max_iter=2000,random_state=0,solver='lbfgs').fit(x[train],y[train]);pr=mod.predict_proba(x[test])
  for j,v in enumerate(mod.classes_):
   for k,val in zip(test,pr[:,j]):scores[v][int(k)]=float(val)
 vals=[]
 for v in fixed:
  ix=sorted(scores[v]);vals.append(float(roc_auc_score([int(y[k]==v)for k in ix],[scores[v][k]for k in ix])))
 want=vals[1]if target=='twin_identity'else float(np.mean(vals));assert result['layers']['44'][target]['binary_AUROC'if target=='twin_identity'else'macro_ovr_AUROC']==want;comparisons+=1
mp.undo()
# Episode bootstrap source order, same-point median, no pair sampling.
values=[[.1,.4],[.3,.6],[.8,1.2],[1.3,1.4]];episodes=['ep2','ep2','ep1','ep3'];groups=list(dict.fromkeys(episodes));rg=np.random.default_rng(20261027);draws=[]
for ix in rg.integers(0,len(groups),(2000,len(groups))):draws.append(float(np.median([v for k in ix for vs,e in zip(values,episodes)if e==groups[k]for v in vs])))
st=rules.episode_median(values,episodes);assert st['estimate']==float(np.median(values))and st['CI95']==np.quantile(draws,[.025,.975]).tolist()
# Residual component finding: QA2 reader rates still use item-Wilson, not episode CIs.
print(json.dumps(dict(pins=pins,dependencies=16,lifecycle_orders_pass=2,independent_AUROC_comparisons_exact=comparisons,episode_median_point_CI_exact=True,real_main_guard_absent=not a.GUARD.exists(),real_probe_guard_absent=not ph.paths()[0].exists())))

```


## §243 / §244 independent prewritten reproductions — direct Guiv5a250e52a

Read bothregistrations in full (actualCOMMITTER02:47:02CET; nominal02:50/02:55). R-Q accepts both now; R3fallback iflate is not invoked because reviewerpreparation is ready. Only existingreviewerfiles edited; no scientificsource/labels/raw/custody changes, no operatorentrypoint/fit/judge/GPU/API/guard. This code is reviewerpreparation before revieweropeningofANYaddendumvaluecounts orE135outcomes, not a new preregistration/claimallhistorycertified. OriginalE128primary9b4c54a4/guard remains immutable/reviewclosed.

**§243 source-ready/prewrite verified:** ae650f926(sourcea4216002b rebased) packagee128_addenda/11dependencyhashes+all5packagefiles matchcommittedGit;10PUREtestsPASS. Independent threefullsynthetic84item A/B grids (allfive code cases/missing/dual/silent, reordering, emptyalpha2flippers) EXACT againstauthor: all128categoricalcount/Wilsontriples pergrid+16paired5000seed0 percentile95 differences, cohort42constant/randomsamecohort,0discrepancies. AddendumA old/new/dual/neither_or_unparseable is EXHAUSTIVECODECENSUS overall84andsteeredflippedcohort, not a missing-as-semantic-neither assertion; explicitUNPARSEABLEcount retained. Bfixed42fromalpha4subjectpairpreferenceonly, α8−α4 category-indicatorpaireditembootstrap5000seed0 (commondefault/frozenauthorsource); no new equivalencetolerance. PrimaryRDOSE1NOTMETunchanged. NewADDENDA243_ONCEclaim before codeopening tested, no primaryguardreplay. Realaddendumcodes/counts/guard not opened byreviewer inthispreparation. Runnerbelowrequires NEWoriginaladdendaCOMPLETE_ONCEseal, exactprimarydigest/SPEC, then ownhash-boundnormalization and A/B comparison; a primaryseal cannot authorize newcounts.

**§244 E135 dose-list/calibration prewrite ready:** independentdesignprototype extends same84/fixed42/dose bins to3/5/6, steered/random/44/52, pair-preference flips strict orientation, old/new/dual/semanticneither Wilsonrates onknownjudgments; terminalmissing staysunknown withseparatecensus. References2/4/8 onlyfromoldsealednative/codes/vectors, no regeneration/rejudge. No confirmatoryrule. Unknown/emptycohorts remainNE; no inventednumeric tolerance for“near0.1”,“highneither”orcliff. Subjectgreedytext stays separate frompairpreference, futurecompiledparser/windowmustmatchowner-source. Calibration computes actualbounddelta L2norms versusmedian ORIGINALunsteered pre-hookB40norms at84×8steeredpositions; reportsmin/median/maxifnonconstant, zero normNE/noepsilon. Old2/4/8calibration computedfromsourcevectors, no rerun/rescale. Prototypeuses literal per-position672normmedian; finalownercommittedcalibration/source-envelope convention MUSTbe compared before outcomes, no silentper-itemaveraging/tolerancechange. Source/E135adapter notyetpresent inreviewedtree, so SOURCECONFORMANCEPENDING (not GO/claimfuturebytesreviewed).

SyntheticE135checks PASS: exact3/5/6list/fixed42, 672normdenominator,all6reference/newdosecalibration ratios, missingreadoutNE andzero-normNE, no promotedrule. I2soleintegrator/Cjudgingbank≤2afterE107bbeforeE95, creationafterE131by10Z, cap2880sfromcreation/hardstopmin(cap,12:50Z),paid15Z preserved. IfjudgingNOTRUN, reportonlysealedGPU/preference/calibration, not falsecomplete zero readerresults. Outputs remainsealeduntiltestedcommittedadapter. No R-Q launch/fundingaction/newpermission.

Extract followingtwoPythonblocks to `/tmp/rq_243_244_prewrite.py` and `/tmp/rq_243_244_synthetics.py`, with base reproduction extracted as previously recorded. CodeSHA 055b334c57d9e89d58d0f8a4ca7a62c142f450445308b5eb4bdb250411b81a41. Synthetic tests only untilappropriateoriginalseal/owner-sourcecomparison.

R-Q_REPRO_243_244_V1:

```python
"""R-Q independent prospective §243/§244 metrics. NO real inputs opened by default.
Uses reviewer-normalized original E128 pointer grid; never invokes owner adapters/guards.
§243 combined bin is a JUDGED-CODE census, not a claim missing readouts say neither.
E135 missing judgments remain unknown; no new confirmatory rule or numerical 'near' tolerance.
"""
import importlib.util
import numpy as np
from common.stats import wilson
_s=importlib.util.spec_from_file_location('rqbase','/tmp/rq_prospective_reproductions.py');base=importlib.util.module_from_spec(_s);_s.loader.exec_module(base)
CATS=('old','new','dual','neither_or_unparseable')
CONDITIONS=('steered','random');LAYERS=('44','52')

def valcat(code,old,new):
    assert old!=new and {old,new}=={'A','B'}
    if code is None or code['category']=='UNPARSEABLE':return 'neither_or_unparseable',True
    assert code['category']in('states_value','names_property_without_value','exhibits','silent')
    values=code['values'];assert isinstance(values,list)and len(set(values))==len(values)and set(values)<={old,new}
    assert bool(values)==(code['category']=='states_value')
    return ('dual'if set(values)=={old,new}else'old'if old in values else'new'if new in values else'neither_or_unparseable'),False

def binrate(values):
    assert all(type(v)in(bool,int)and v in(0,1)for v in values)
    n=len(values);k=sum(values);p,lo,hi=wilson(k,n)if n else(None,None,None)
    return dict(planned_n=n,n=n,k=k,missing_n=0,missing_over5percent=False,estimate=p,Wilson95=None if n==0 else[lo,hi])

def flag(x,dose,condition):
    z=x['doses'][str(dose)][condition]
    if dose==8:return z['pair_flag']
    return None if z['raw']is None else base.preference(z['raw'],x['new'])=='new'

def table(items,dose,condition,layer):
    values=[valcat(x['doses'][str(dose)][condition]['code'][str(layer)],x['old'],x['new'])for x in items]
    return dict(planned_n=len(items),unparseable_n=sum(m for c,m in values),categories={c:binrate([int(v==c)for v,m in values])for c in CATS})

def all_tables(items,dose):return {c:{l:table(items,dose,c,l)for l in LAYERS}for c in CONDITIONS}

def paired_value_difference(items,condition,layer,category,draws=5000,seed=0):
    d=np.array([int(valcat(x['doses']['8'][condition]['code'][str(layer)],x['old'],x['new'])[0]==category)-int(valcat(x['doses']['4'][condition]['code'][str(layer)],x['old'],x['new'])[0]==category)for x in items],float)
    if not len(d):return dict(n=0,estimate=None,CI95=None,valid_bootstraps=0)
    ix=np.random.default_rng(seed).integers(0,len(d),(draws,len(d)));boot=d[ix].mean(1)
    return dict(n=len(d),estimate=float(d.mean()),CI95=np.quantile(boot,[.025,.975]).tolist(),valid_bootstraps=draws)

def addenda243(items):
    assert len(items)==84 and len({x['id']for x in items})==84
    items=sorted(items,key=lambda x:x['id'])
    for x in items:
        assert set(x['doses'])=={'2','4','8'}
        for d in(2,4,8):
            for c in CONDITIONS:assert type(flag(x,d,c))is bool
    fixed=[x for x in items if flag(x,4,'steered')];assert len(fixed)==42
    A={str(d):dict(all84=all_tables(items,d),flipped=all_tables([x for x in items if flag(x,d,'steered')],d))for d in(2,4,8)}
    B=dict(n=42,tables={str(d):all_tables(fixed,d)for d in(4,8)},differences={c:{l:{v:paired_value_difference(fixed,c,l,v)for v in CATS}for l in LAYERS}for c in CONDITIONS})
    return dict(label='exploratory, post hoc',A=A,B=B,original_R_DOSE1='NOT MET (copied unchanged)')

def e135_reader(items,dose,condition,cohort):
    xs=[x for x in items if x['id']in cohort];out={}
    for l in LAYERS:
        cs=[valcat(x['doses'][str(dose)][condition]['code'][l],x['old'],x['new'])for x in xs]
        # Known-denominator semantic neither excludes terminal UNPARSEABLE.
        out[l]={v:base.rate([None if missing else int(cat==('neither_or_unparseable'if v=='neither'else v))for cat,missing in cs])for v in('old','new','dual','neither')}
        out[l]['unparseable_n']=sum(m for cat,m in cs)
    return out

def calibration244(baseline_norms,deltas_by_dose):
    norms=np.asarray(baseline_norms,float);assert norms.shape==(84,8)and np.isfinite(norms).all()and(norms>=0).all()
    median=float(np.median(norms));out={}
    assert set(map(int,deltas_by_dose))=={2,3,4,5,6,8}
    for d,z in deltas_by_dose.items():
        a=np.asarray(z,float);assert a.ndim in(1,2)and np.isfinite(a).all()
        v=np.array([np.linalg.norm(a)])if a.ndim==1 else np.linalg.norm(a,axis=1)
        assert len(v)in(1,84)
        ratios=None if median==0 else v/median
        out[str(d)]=dict(delta_norm_min=float(v.min()),delta_norm_median=float(np.median(v)),delta_norm_max=float(v.max()),n_vectors=len(v),ratio_min=None if ratios is None else float(ratios.min()),ratio_median=None if ratios is None else float(np.median(ratios)),ratio_max=None if ratios is None else float(ratios.max()))
    return dict(baseline_median_L2=median,baseline_n=672,unit='unsteered pre-hook block40 residual at eight steered positions, all84items',point_statistic='median over original84x8 per-position norms',ratios=out,status='NOT EVALUABLE (zero native norm)'if median==0 else'DESCRIPTIVE')

def dose244(items,baseline_norms,deltas_by_dose):
    assert len(items)==84 and len({x['id']for x in items})==84
    fixed={x['id']for x in items if flag(x,4,'steered')};assert len(fixed)==42
    out={}
    for d in(2,3,4,5,6,8):
        assert all(str(d)in x['doses']for x in items)
        flips={x['id']for x in items if flag(x,d,'steered')is True};flags=[flag(x,d,'steered')for x in items]
        out[str(d)]=dict(flip_rate=base.rate([None if v is None else int(v)for v in flags]),on_steered_flipped={c:e135_reader(items,d,c,flips)for c in CONDITIONS},on_fixed_alpha4_42={c:e135_reader(items,d,c,fixed)for c in CONDITIONS})
    old=[out[str(d)]['on_steered_flipped']['steered']['44']['old']['estimate']for d in(2,3,4,5,6,8)]
    shape=None if any(v is None for v in old)else dict(weakly_nondecreasing=all(a<=b for a,b in zip(old,old[1:])),strictly_increasing=all(a<b for a,b in zip(old,old[1:])))
    return dict(experiment='E135',reading='DESCRIPTIVE ONLY',new_doses=[3,5,6],existing_reference_doses=[2,4,8],fixed_alpha4_n=42,doses=out,calibration=calibration244(baseline_norms,deltas_by_dose),observed_monotonicity=shape,qualitative_readings='No invented numeric tolerance for near0.1/cliff/high neither; report observed curve and uncertainty. Missing/empty flipped sets stay NE. Pair preference is not subject greedy text.')

def run243_from_original_seal(path,digest):
    """Only after the NEW addenda author seal, never using the primary as permission."""
    from pathlib import Path
    p=Path(path);meta=base.verify_analysis(p,digest)
    assert meta['experiment']=='E128 addenda243'and meta['primary_seal_sha256']=='9b4c54a4422bb60db12d32899cd68cb4715ec2ec6a6c0e4498eb933c6f8c23c7'
    assert meta['spec_sha256']=='69af33cc5abf14abe43be1b542adead729eeda8d5b9c675c1f34421feca740bb'
    spec=base.read_json(p.parent/'BINDING.json');own=addenda243(base.normalize128(spec));worker=base.read_json(p.parent/'RESULTS.json')
    assert own['A']==worker['A']and own['B']==worker['B']
    return own

```

R-Q_REPRO_243_244_TEST_V1:

```python
import importlib.util,copy,json,hashlib,subprocess
from pathlib import Path
import numpy as np
from projects.g_agreement.e128_addenda import adapter as author
from projects.g_agreement.e128_analysis.test_coordinator import pairs
from projects.g_agreement.e127_analysis.test_rules import code
s=importlib.util.spec_from_file_location('rqnew','/tmp/rq_243_244_prewrite.py');q=importlib.util.module_from_spec(s);s.loader.exec_module(q)

def normalize(xs):
 out=[]
 for x in xs:
  ds={}
  for d,conditions in x['doses'].items():
   ds[str(d)]={}
   for c,z in conditions.items():
    f=z['pair_preference_flip_descriptive'];new=x['new_value'];positive=(f and new=='A')or(not f and new=='B')
    ds[str(d)][c]=dict(raw=None if d==8 else dict(pair_logits=[[1,0]]if positive else[[0,1]]),pair_flag=f,code={str(l):v for l,v in z['oracle'].items()})
  out.append(dict(id=x['item_id'],old=x['old_value'],new=x['new_value'],doses=ds))
 return out
checks=0
for case in range(3):
 xs=pairs((0,42,84))
 if case:
  vals=[code('A'),code('B'),code(['A','B']),code(None),code(None,'UNPARSEABLE')]
  for i,x in enumerate(xs):
   for d,zs in x['doses'].items():
    for c,z in zs.items():
     for l in(44,52):z['oracle'][l]=copy.deepcopy(vals[(i+d+l+(c=='random'))%5])
 if case==2:xs=list(reversed(xs))
 normalized=normalize(xs);want=author.analyze(xs);got=q.addenda243(normalized)
 assert got['A']==want['A']and got['B']==want['B'];checks+=1
 assert all(sum(v['k']for v in z['categories'].values())==z['planned_n']for d in got['A'].values()for cohort in d.values()for c in cohort.values()for z in c.values())
 assert got['A']['2']['flipped']['random']['44']['categories']['old']['estimate']is None
 assert got['B']['n']==42
print('§243: three independent complete A/B grids exactly match committed author counts/Wilson/16 paired5000-seed0 CIs; partition+empty/reordering PASS')
# E135 design-only prototype, before owner adapter exists.
xs=normalize(pairs((0,42,84)))
for x in xs:
 for d in(3,5,6):x['doses'][str(d)]=copy.deepcopy(x['doses']['4'])
base=np.full((84,8),2.);vectors={str(d):np.tile([float(d),0.],(84,1))for d in(2,3,4,5,6,8)}
r=q.dose244(xs,base,vectors);assert r['new_doses']==[3,5,6]and r['fixed_alpha4_n']==42 and r['reading']=='DESCRIPTIVE ONLY'
for d in(2,3,4,5,6,8):assert r['calibration']['ratios'][str(d)]['ratio_median']==d/2
for x in xs:x['doses']['5']['steered']['code']['44']=code(None,'UNPARSEABLE')
r=q.dose244(xs,base,vectors);assert r['doses']['5']['on_steered_flipped']['steered']['44']['old']['estimate']is None and r['doses']['5']['on_steered_flipped']['steered']['44']['unparseable_n']==42
assert q.calibration244(np.zeros((84,8)),vectors)['ratios']['8']['ratio_median']is None
print('§244: 3/5/6 list, fixed42, all672-position calibration, 2/4/8 references, missing-reader NE and zero-denominator NE PASS; no confirmatory promotion')
root=Path.cwd();deps=json.loads((root/'projects/g_agreement/e128_addenda/DEPENDENCIES.json').read_text())
for f,h in deps.items():assert hashlib.sha256((root/f).read_bytes()).hexdigest()==h
for p in(root/'projects/g_agreement/e128_addenda').iterdir():
 if p.suffix in('.py','.json','.md'):assert p.read_bytes()==subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(root))])
print('§243 committed package/dependencies exact; NO real codes or addenda/primary guard opened')

```


## E128 §243 A/B independent review COMPLETE — 2489fbb5b /75a53c18

Using the prewritten reviewer code (no authorrealinput/analyze/guard), independently reproduced originaladdendumseal75a53c18aa281a5ba63a53085c409e55a45bf67ffac2c5a78001b6fcdd91db10/public2489fbb5b: **128categoricalcount/Wilsoncells and16paired5000seed0percentileCIs EXACT**, originalBINDING/SPEC and both originalmemberhashes/publiccopies exact. SeparateADDENDA243_ONCEguard2f51b5215e91c864cd44bd6421fd9239ac717d347d30d17b3812c30d26721804 consumed/NEVERreplay. Originalprimary9b4c54a4 unchanged; no primarymetricrerun/newfit/judge. §243newcounts areexploratory/posthoc, not a newconfirmatoryresult.

Alpha4steered42flippers/block44: **old4,new1,dual0,neither37,UNPARSEABLE0**. SAME42atα8: **old5,new4,dual0,neither-or-unparseable33**, includingONEoriginalUNPARSEABLE (32parseableneither). Pairedcategoryoldfractionα8−α4= **.0238095238**,CI **[−.0952380952,.1428571429]**,5000/5000valid. This doesnotestablish equivalence orclearwithincohortdoseeffect. Largewhole-setdifferenceisconsistentwithregistereditem-selectionreading, notproofintrinsicitemproperty/universalabsenceofdoseeffect. Allcategories usefulldenominator42asregistered; UNPARSEABLEcombinedbin iscodecensus, not semanticneitherorzerooldscore. Originalprimaryknown-denominatorrates remain unchanged. Whole84α8oldtable47/84 differs fromprimary47/83becauseexplicitcombinedmissingbin, not numericaldisagreement.

**DirectGuivderived-count check independently confirmed from E128/E109 REFERENCE sealedcodes (NOT originalE104judgmentbank):** α4NON-flippercomplement42 atα8/block44 = **old42/42**,new0,dual0,neither0,UNPARSEABLE0;Wilson[.9161983875,1.0000000000000002]. This is not subtraction alone: originalrawcode membership/values confirmed complementdisjoint/exhaustive. Whole47−cohort5=42; singleα8missingliesINSIDEalpha4cohort, so complementdenominatorreally42known, not41/unknown. No itemIDs published. This newcomplementcheck doesnotrepeatclosedprimaryaudit.

Chronology §2435a250actual02:47:02CET<sourceae650/deliveryd5d55actual02:52:07<guard02:52:21.406924<RESULTS.768830<seal.769332<publication2489actual02:53:50. Reviewerprewrite wasbefore owncategoryopening, NOT claimedbeforeauthorresult. Earlierfirst-everhistoryunverified. E128RDOSE1NOTMET unchanged.

## E135 deviation1 prewrite — α6-only /026eea061

Read0012640e0(actual03:07:43CET) and026eea061(actual03:07:59) in full: SUPERSEDEoriginal3/5/6plan; newnative168cells,336readouts, α6steered+random ONLY. Calibrationreferences2/4/6/8 scalararithmetic, cap2880s unchanged/bank≤1, sameoncefamily/norefitting/historyrerun. This deviation isprospectivewrtE135 but explicitly informed byalready-openE128/E104addendum; notfullyblind/preresultwrtallresearchdata. RQsource-independent prewritebelowREADY, no lateR3fallbackneeded; finalcorrectedowneradapter/sourcecomparison remainsPENDING, oldDOSES3/5/6package isnotdeviationGO.

Split ONLY α6steeredpair-logitflippers into F6∩C4(retained α4flippers) and F6\C4(newlyflipped), originalC4 fixed42fromE128subjectnativeflags. DoNOTassumeall42stillflipat6; reportknownα4dropouts/unknown6separately. Randomuses SAMEcohortidentities; neverrandomselected. Reportold/new/dual/semanticneither withWilsonknown-denominators,terminalUNPARSEABLEandunrunseparate; empty/unknownratesNE. Compare newlyflippedold44 besidevalidatedα8noncohort42/42 andα8cohort5/42codecensus (withoneUNPARSEABLE), no invented“near”/equivalence tolerance/automaticitempropertyclaim. No probe/readout selection, no addedconfirmatorytest.

Pure selftestsPASS:42retained+18newwith60flips,41retained+1unknown+18newwithoutforcingunknownintodropout,emptyF6NE,randomsamecohorts, calibration168records/672UNIQUEnaturalwritepositions and2/4/6/8ratios. Initialnative-calibrationrecordprototype alsoindependentlymatchesE135runner'spurecalibration_records using synthetic84×8norms, per-cellsourcecomposeddelta magnitudes/historicalarithmetic, no duplicatecontrols/doses. E135producerintake separatelyverified186sourcepins/4inputpins/1CPUpin+all504original3/5/6inputjoins/scaledfloat32deltas exact;12PURErunnercasesPASS(two real-loadercasesdeselected/replacedbyownsourcecheck). Thoseproducerpins referOLDthree-dosepacket, notauthorizationtorun3/5afterdeviation. No E135native/readout/calibrationoutcomes opened.

§245217fa91f1actual03:10:54: E133b accepted separatebAbIarm/besideE133, NOTpooledRNL1. Official494QA2source/inputa7bd; originala1partialscreen remainssealedexcluded, no stitching/reuse; fresh32tokenscreen/first42source-orderqualifying, fewer42reportfewer, <20SCREENONLY. Owncap2160s/fromcreation/hardstopmin(cap,12:50Z),createdby10Z; one§234measuredattempt ifNOFIT. CjudgingSAMEE133bank≤5TOTAL aftersyntheticreadouts/no capreset. Bepisode-CIfixd52e932a3/deliveryd8e34ad47arrived, prospectivecheckNEXT; no currentclaimfixreviewed. §246E131followupbelongsR4, notRQ; prior43/84textauthornumbersnotindependentlyendorsedhere. GlobalGPU2500booked+activecaps/2000flagnotgate read/preserved; no reviewerresource/launch/ledgeraction.

R-Q_E135_DEV1_PREWRITE (synthetics-only default), SHA bb3446dbf11d06bf15fa3d3a121a47dc0e9192f599d8794f1092358ca3e37373:

```python
"""§244 deviation1/026eea061 independent alpha6-only reproduction.
No actual E135 records are opened here; use only AFTER original complete seals and
source binding validation. Historical E128 code access needs the separate addenda seal.
"""
import importlib.util
import numpy as np
_s=importlib.util.spec_from_file_location('rq243','/tmp/rq_243_244_prewrite.py');q=importlib.util.module_from_spec(_s);_s.loader.exec_module(q)

def flag6(x,c):
    raw=x['doses']['6'][c]['raw']
    return None if raw is None else q.base.preference(raw,x['new'])=='new'

def reader6(items,condition,group):
    xs=[x for x in items if x['id']in group];out={}
    for layer in('44','52'):
        cells=[x['doses']['6'][condition]['code'][layer]for x in xs]
        categories=[q.valcat(z,x['old'],x['new'])for x,z in zip(xs,cells)]
        rates={v:q.base.rate([None if missing else int(cat==('neither_or_unparseable'if v=='neither'else v))for cat,missing in categories])for v in('old','new','dual','neither')}
        rates['terminal_unparseable_n']=sum(z is not None and z['category']=='UNPARSEABLE'for z in cells)
        rates['unrun_n']=sum(z is None for z in cells);out[layer]=rates
    return out

def calibration6(records):
    assert len(records)==168 and {(r['alpha'],r['condition'])for r in records}=={(6,'steered'),(6,'random')}
    by={(r['base_id'],r['condition']):r for r in records};assert len(by)==168
    ids={i for i,c in by};assert len(ids)==84 and set(by)=={(i,c)for i in ids for c in('steered','random')}
    natural=[];magnitude={'steered':[],'random':[]}
    for i in sorted(ids):
        z=by[i,'steered'];n=np.asarray(z['natural_site_l2'],float);assert n.shape==(8,)and np.isfinite(n).all()and(n>0).all();natural.extend(n)
        for c in magnitude:
            r=by[i,c];v=np.asarray(r['natural_site_l2'],float)
            assert r['write_block']==40 and len(r['positions'])==8 and r['positions']==z['positions']and all(b-a==1 for a,b in zip(r['positions'],r['positions'][1:]))
            assert np.allclose(v,n,rtol=1e-5,atol=1e-6)
            dn=r['composed_delta_l2'];assert np.isfinite(dn)and dn>0;magnitude[c].append(dn/6)
    den=float(np.median(natural));assert den>0
    return dict(baseline_median_L2=den,n_items=84,n_positions=672,raw_cells_checked=168,dose6_measured_only=True,numerator_basis='original composed delta L2/6; historical alpha2/4/8 scalar arithmetic, no new capture',ratios={str(d):{c:dict(min=float(d*min(v)/den),median=float(d*np.median(v)/den),max=float(d*max(v)/den))for c,v in magnitude.items()}for d in(2,4,6,8)})

def deviation1(items,reference128,calibration_records=None):
    assert len(items)==len(reference128)==84
    ids={x['id']for x in items};historical={x['id']:x for x in reference128};assert len(ids)==84 and ids==set(historical)
    assert all(set(x['doses'])=={'6'}and x['old']==historical[x['id']]['old']and x['new']==historical[x['id']]['new']for x in items)
    f4={x['id']for x in reference128 if q.flag(x,4,'steered')is True};assert len(f4)==42
    flags={x['id']:flag6(x,'steered')for x in items};f6={i for i,v in flags.items()if v is True}
    groups=dict(all84=ids,alpha6_flipped=f6,alpha4_fixed42=f4,retained_alpha4_flippers=f6&f4,newly_flipped_at6=f6-f4,alpha4_known_not_flipped6={i for i in f4 if flags[i]is False},alpha4_unknown6={i for i in f4 if flags[i]is None},noncohort_known_not_flipped6={i for i in ids-f4 if flags[i]is False},noncohort_unknown6={i for i in ids-f4 if flags[i]is None})
    assert not(groups['retained_alpha4_flippers']&groups['newly_flipped_at6'])and groups['retained_alpha4_flippers']|groups['newly_flipped_at6']==f6
    reports={name:dict(n=len(group),readouts={c:reader6(items,c,group)for c in('steered','random')},pair_flip_rate={c:q.base.rate([None if flag6(x,c)is None else int(flag6(x,c))for x in items if x['id']in group])for c in('steered','random')})for name,group in groups.items()}
    cohort=[x for x in reference128 if x['id']in f4];complement=[x for x in reference128 if x['id']not in f4]
    refs=dict(alpha4_fixed42=q.table(cohort,4,'steered','44'),alpha8_fixed42=q.table(cohort,8,'steered','44'),alpha8_noncohort42=q.table(complement,8,'steered','44'))
    return dict(experiment='E135 deviation1',descriptive=True,new_doses=[6],fixed_alpha4_n=42,groups=reports,historical_references=refs,calibration=None if calibration_records is None else calibration6(calibration_records),missing_policy='Recorded UNPARSEABLE/unrun reader cells unknown; semantic neither separate. Unknown alpha6 behaviour never forced into not-flipped. Same selected identities for random.',reading='Compare newly-flipped old44 with sealed noncohort alpha8 and cohort reference, report Wilson CIs. No numerical near/equivalence margin; no intrinsic-item/causal claim or confirmatory rule.')

if __name__=='__main__':
    import copy
    from projects.g_agreement.e128_analysis.test_coordinator import pairs
    from projects.g_agreement.e127_analysis.test_rules import code
    # Opaque identities are SYNTHETIC; no real selection.
    refs=[]
    for i,x in enumerate(pairs((0,42,84))):
        ds={}
        for d,zs in x['doses'].items():
            ds[str(d)]={}
            for c,z in zs.items():
                new=x['new_value'];flip=z['pair_preference_flip_descriptive'];sign=(flip and new=='A')or(not flip and new=='B')
                ds[str(d)][c]=dict(raw=None if d==8 else dict(pair_logits=[[1,0]]if sign else[[0,1]]),pair_flag=flip,code={str(l):v for l,v in z['oracle'].items()})
        refs.append(dict(id=x['item_id'],old=x['old_value'],new=x['new_value'],doses=ds))
    items=[dict(id=x['id'],old=x['old'],new=x['new'],doses={'6':copy.deepcopy(x['doses']['4'])})for x in refs]
    for i,x in enumerate(items):
        for c in('steered','random'):
            flip=i<60 and c=='steered';sign=(flip and x['new']=='A')or(not flip and x['new']=='B');x['doses']['6'][c]['raw']={'pair_logits':[[1,0]]if sign else[[0,1]]}
    a=deviation1(items,refs);assert a['groups']['retained_alpha4_flippers']['n']==42 and a['groups']['newly_flipped_at6']['n']==18
    items[0]['doses']['6']['steered']['raw']=None
    a=deviation1(items,refs);assert a['groups']['retained_alpha4_flippers']['n']==41 and a['groups']['alpha4_unknown6']['n']==1 and a['groups']['newly_flipped_at6']['n']==18
    for x in items:x['doses']['6']['steered']['raw']={'pair_logits':[[0,1]]if x['new']=='A'else[[1,0]]}
    a=deviation1(items,refs);assert a['groups']['alpha6_flipped']['n']==0 and a['groups']['newly_flipped_at6']['readouts']['steered']['44']['old']['estimate']is None
    records=[dict(base_id=str(i),alpha=6,condition=c,write_block=40,positions=list(range(10,18)),natural_site_l2=[2.]*8,composed_delta_l2=6.)for c in('steered','random')for i in range(84)]
    cal=calibration6(records);assert cal['n_positions']==672 and set(cal['ratios'])=={'2','4','6','8'}and cal['ratios']['8']['steered']['median']==4
    print('PASS alpha6-only split: retained/new, unknown/dropout, empty-cohort NE, same-cohort random, four-dose calibration from168native cells/672unique positions; no actual outcomes')

```

R-Q_E135_NATIVE_CALIBRATION_PREWRITE (original three-dose schema, historical/synthetic preparation only):

```python
"""Independent §244 calibration from original per-cell records, no new forwards.
Choose ONE original 84-item condition/dose grid; never multiply the baseline
cohort by doses or controls. Referenced scalars remain raw/hashes unchanged.
"""
import numpy as np

def reproduce_calibration(records):
    assert len(records)==84 and len({r['base_id']for r in records})==84
    assert len({(r['alpha'],r['condition'])for r in records})==1
    sites=[];numerators={str(d):[]for d in(2,3,4,5,6,8)}
    for r in records:
        assert r['write_block']==40 and len(r['positions'])==8 and all(b-a==1 for a,b in zip(r['positions'],r['positions'][1:]))
        ns=np.asarray(r['natural_site_l2'],float);assert ns.shape==(8,)and np.isfinite(ns).all()and(ns>0).all();sites.extend(ns)
        assert set(r['reference_delta_l2'])==set(numerators)
        dn=r['composed_delta_l2'];assert np.isfinite(dn)and dn>0
        for d in numerators:
            v=r['reference_delta_l2'][d];assert v==dn*int(d)/r['alpha'];numerators[d].append(v)
    denominator=float(np.median(sites))
    return dict(denominator_median_L2=denominator,n_items=84,n_positions=672,natural_site='original pre-edit block40 eight write sites',numerator_basis='original composed delta L2; historical doses arithmetic only, no rerun or extra rounding',ratios={d:dict(min=float(np.min(v)/denominator),median=float(np.median(v)/denominator),max=float(np.max(v)/denominator))for d,v in numerators.items()})

if __name__=='__main__':
    from projects.g_agreement.e135.runner import calibration_records
    items=[dict(id=str(i),base_id=str(i),alpha=3,condition='steered',read_index=20)for i in range(84)]
    values=np.arange(1,673,dtype=float).reshape(84,8)
    metrics=[dict(injection_sites=[dict(position=j,block=40,before_norm=float(v))for j,v in zip(range(12,20),row)])for row in values]
    records=calibration_records(items,np.tile([3.,4.],(84,1)),metrics)
    got=reproduce_calibration(records)
    assert got['denominator_median_L2']==336.5 and got['n_positions']==672
    for d in(2,3,4,5,6,8):assert got['ratios'][str(d)]['median']==(5*d/3)/336.5
    print('PASS independent actual calibration-record schema: all6dose ratios; single84x8baseline; no duplicate controls/doses, no historical capture')

```


### Required provenance distinction for the α8 complement

A subsequent independent original-bank check qualifies the earlier user-facing42/42 confirmation: **42/42 belongs to the E128 SPEC69af33cc α8/E109-reference judgmentsealef8ea43bbc18c581f03cf8e2eb5cae1d972ee23556b4b655215aa6f4ef442b70**. The ORIGINAL E104 judgmentsealce564237b9951502478d26ab9c5bdcca3a8e3a7c90c0579660c76e4149cbf85b withoriginalPRIVATEhash495bbb gives **41/42old,one validnames_property_without_value/neither,no missing** onEXACTLYsameα4nativecomplement. Originalwhole84old46 (not47),fixed42old5,so46−5=41. Independent literalitem/opaquejudgmentID/old-neworientation joins confirmbothcounts. E128-referencewhole47/fixed5/oneUNPARSEABLEinsidefixed42 =>47−5=42/42, asreviewed. 80/84source texts exactlymatch across originalPRIVATE andE128reference, and4category/valuecodes differ; doNOTcallthismerelyoneidentical-bankannotation orsilentlysubstitutebanks.

Bothfrozenbanks preserved/no rejudge/repair/primaryreplay. Earlier“E10442/42” shorthand is corrected here: reportE128/E109reference42/42 beside originalE10441/42. E135prewrite retains the explicitlyregistered E128-reference comparison, with this provenance disclosure; neither count establishesan intrinsicitemtrait. No membershipIDs/texts published.


## 2026-10-30 — §245 E133b episode reader-CI fix: source review COMPLETE, result PENDING

Direct Guiv §245 `217fa91f1` (actual COMMITTER 03:10:54 CET) assigns E133b beside E133. Corrected source `d52e932a3` (actual COMMITTER 03:16:31 CET; original receipt names equivalent `7668906a8`) and receipt `d8e34ad47`: own=worker **38 pure tests PASS**, plus **38 PASS from exact committed Git extraction**. First extraction lacked transitive dependencies and failed collection; after extracting those same committed dependencies, the isolated run passes. All 11 package Python files equal the committed source; 2 receipt hashes exact; the 3 direct statistical dependencies are unchanged from reviewed `6de411382`.

Episode reader intervals — PASS source conformance: independent prewritten R-Q episode prototype reproduces 6 unequal-cluster/unsorted/partial-missing/all-missing/empty/single-episode cases, and **all 15 QA2 reader cells** (3 layers × current/previous/other/none/dual) on a separate synthetic mixed grid, including point, CI, episode count, defined/undefined draws and missing census. Every draw resamples whole ORIGINAL source episodes with all their pairs/twins, 2000 draws, seed 20261027; known denominator stays explicit, no zero imputation, CI is null unless all 2000 draws are defined. QA2 has no item-Wilson alias. Synthetic multi-hop/one-hop outputs and primary R-NL1/falsifier are exactly unchanged. Reader groups use sorted string episode order as the prewritten reader prototype; patch medians retain their already-reviewed first-occurrence order. A single reader episode can yield a degenerate interval; no new independent-episode gate is invented, and this does not certify population generality.

§245 prospective scope — E133b remains descriptive beside E133, never pooled into R-NL1; fresh first 42 qualifying source-order pairs, fewer retained, fewer than 20 SCREEN ONLY, original a1 partial excluded and unopened. Original separate §245 source/inventory/native/once/SPEC bindings and first-opening chronology still need final verification. This closes the identified reader-CI source discrepancy, not the eventual bAbI result or operator admission. No actual E133b output, label, selection, real adapter/guard, model, fit or paid action opened/invoked by R-Q. No scientific seal located at this snapshot; review the original sealed result when it arrives. Original E133 contrast fix and closed audits were not repeated.

Runnable independent synthetic reproduction (requires the committed rules plus the already embedded R-Q episode prototype; no author real entrypoint):

<!-- R-Q_REPRO_E133B_245_TEST_V1 -->
```python
import sys,importlib.util,copy,json,hashlib,subprocess
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.e133_analysis import rules as r
from projects.g_agreement.e133_analysis.test_rules import pairs,state
spec=importlib.util.spec_from_file_location('rq_episode','/tmp/rq_e133_episodes.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
cases=[([0,0,0,0,1,1],['A']*4+['B']*2),([1,None,0,1,None,0],['z','z','A','A','q','q']),([None,None,1,1],['A','A','B','B']),([],[]),([None,None],['A','A']),([1,0],['only','only'])]
for vals,eps in cases:
 a=r.episode_rate(vals,eps);b=m.episode_ci([dict(episode=e,value=v)for e,v in zip(eps,vals)])
 for x,y in [('estimate','estimate'),('CI95','CI95'),('n_episodes','episodes'),('defined_draws','defined_draws')]:assert a[x]==b[y],(x,a,b)
 assert a['undefined_draws']==2000-b['defined_draws'] and 'Wilson95'not in a
base=pairs(50,2);qa=copy.deepcopy(base[:7]);episodes=['z','A','z','B','B','B','q']
for i,p in enumerate(qa):
 p.update(pair_id='qa:'+str(i),kind='babi_qa2',source_episode_id=episodes[i])
 for j,member in enumerate(p['members']):
  for l in r.READS:member['readouts'][l]=None if (i+j+l)%7==0 else state(['current','previous','other','none','dual_current_previous'][(i+j+l)%5])
a=r.analyze(base+qa)[0];b=r.analyze(base)[0]
for k in ['multi_hop','one_hop']:assert a['groups'][k]==b['groups'][k]
for k in ['R_NL1','falsifier','informative']:assert a[k]==b[k]
n=0
for l in r.READS:
 for name in ['current','previous','other','none','dual_current_previous']:
  vals=[dict(episode=p['source_episode_id'],value=None if member['readouts'][l]is None else member['readouts'][l][name])for p in qa for member in p['members']]
  exp=m.episode_ci(vals);got=a['groups']['babi_qa2']['reader_rates'][str(l)][name]
  for x,y in [('estimate','estimate'),('CI95','CI95'),('n_episodes','episodes'),('defined_draws','defined_draws')]:assert got[x]==exp[y]
  assert got['planned_n']==14 and got['missing_n']==sum(v['value']is None for v in vals) and 'Wilson95'not in got;n+=1
receipt=json.loads(Path('results/g_agreement/understand/e133/analysis/EPISODE_READER_CI245_RECEIPT.json').read_text())
for p,h in receipt['files'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
print('PASS: 6 independent episode boundary/missing cases; all 15 QA2 reader cells exact; synthetic MH/one-hop groups and verdicts identical; 2 receipt hashes exact')
```
<!-- /R-Q_REPRO_E133B_245_TEST_V1 -->


## 2026-10-30 §217 arrival — E135 deviation1 source comparison COMPLETE (science PENDING)

Corrected W-mech2 source `d94278a73` (actual COMMITTER 2026-10-30T03:15:45+01:00) / authority `026eea061`: own=worker **16 pure synthetic tests PASS**, plus **16 PASS in an exact committed Git extraction**. All **6 source-receipt pins +13 dependency pins** independently match working and committed bytes. Alpha6 only, 168 calibration cells/336 readouts and bank ≤USD1 are enforced; superseded three-dose/cap2 metadata is rejected. Production `run`, original inputs, actual guards and E135 outputs were not opened/invoked.

Independent prewritten alpha6 reproduction now compared to the corrected source on 3 separate synthetic grids: **240 cohort/category rate dictionaries** reproduce exactly after normalizing `n` versus reviewer `known_n`, including count, planned/missing/known denominator, estimate and Wilson CI. Semantic neither, terminal UNPARSEABLE and unrun null stay separate. The retained/new/known-alpha4-dropout/unknown-alpha6 partitions are respectively [32,42,10,0], [41,18,0,1], [0,0,42,0]; random uses the same selected identities in each grid. All historical 2/4/6/8 calibration arithmetic matches, counting the 672 individual pre-edit sites once from 168 cells, with repeated-norm checks and literal captured-field source-map validation exercised by pure fixtures. The author publishes 5 registered cohorts; reviewer prewrite additionally exposes known dropouts and unknown behaviour without treating unknown as not-flipped. No monotonicity, numerical “near” margin, intrinsic-item trait or new confirmatory rule is inferred. Historical comparisons retain the explicitly different E128/E109-reference and original E104 banks documented above.

This closes the earlier prospective **6-only adapter comparison** item; it does not certify final original SPEC, input/native/code/calibration field bindings or first-output/first-opening timing. I-2's new shared aggregate GPU-completion/closeout receipts are acquisition delivery, not a sealed scientific analysis; no R-Q scientific completion verdict yet. Final source identity and raw literal calibration mapping still need verification with the original sealed scientific packet. E133 synthetic judging is RUNNING per shared source receipt, not complete; E133b has no arriving scientific seal at this snapshot. E118b's saved-backend-finish request is outside R-Q outcome ownership (R5); R-Q supplies no continuation/disposition authority, replay or substitute judgment. New shared operational notices do not change caps or scientific rules.

Independent synthetic comparison for rerun when the sealed E135 packet arrives (no real author entrypoint):

<!-- R-Q_REPRO_E135_DEV1_SOURCE_TEST_V1 -->
```python
import sys,importlib.util,copy
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.e135_analysis import adapter as a
from projects.g_agreement.e135_analysis.test_adapter import records,rawcal
from projects.g_agreement.e128_analysis.test_coordinator import pairs
from projects.g_agreement.e127_analysis.test_rules import code
s=importlib.util.spec_from_file_location('rq6','/tmp/rq_e135_deviation1_prewrite.py');q=importlib.util.module_from_spec(s);s.loader.exec_module(q)
refs=[]
for x in pairs((0,42,84)):
 ds={}
 for d,zs in x['doses'].items():
  ds[str(d)]={}
  for c,z in zs.items():
   f=z['pair_preference_flip_descriptive'];new=x['new_value'];v=(f and new=='A')or(not f and new=='B')
   ds[str(d)][c]=dict(raw=None if d==8 else dict(pair_logits=[[1,0]]if v else[[0,1]]),pair_flag=f,code={str(l):z['oracle'][l]for l in(44,52)})
 refs.append(dict(id=x['item_id'],old=x['old_value'],new=x['new_value'],doses=ds))
count=0
for case in range(3):
 xs=records()
 for i,x in enumerate(xs):
  for c in a.CONDITIONS:
   z=x['doses'][6][c];z['pair_preference_flip_descriptive']=None if i in(0,83)and case==1 else (i>=10 if case==0 else i<60 if case==1 else False)and c=='steered'
   for l in a.LAYERS:z['oracle'][l]=None if (i+l)%17==0 else code(None,'UNPARSEABLE')if(i+l)%13==0 else code(None)if(i+l)%7==0 else code(['A','B'])if(i+l)%5==0 else code(x['old_value']if i%2 else x['new_value'])
 norm=[]
 for x in xs:
  ds={}
  for c,z in x['doses'][6].items():
   f=z['pair_preference_flip_descriptive'];sgn=(f and x['new_value']=='A')or(not f and x['new_value']=='B')
   ds[c]=dict(raw=None if f is None else dict(pair_logits=[[1,0]]if sgn else[[0,1]]),code={str(l):z['oracle'][l]for l in a.LAYERS})
  norm.append(dict(id=x['item_id'],old=x['old_value'],new=x['new_value'],doses={'6':ds}))
 cal=rawcal();ac=a.calibration(cal,{x['item_id']for x in xs})
 rc=[dict(base_id=z['item_id'],alpha=z['dose'],condition=z['condition'],write_block=40,positions=z['write_positions'],natural_site_l2=z['natural_site_l2'],composed_delta_l2=z['composed_delta_l2'])for z in cal['cells']]
 qc=q.calibration6(rc);assert ac['median_unsteered_residual_l2']==qc['baseline_median_L2']
 for d in('2','4','6','8'):
  for c in a.CONDITIONS:assert ac['ratios'][d][c]==qc['ratios'][d][c]['median']
 ar=a.analyze(xs,{str(i)for i in range(42)},ac)['doses']['6'];qr=q.deviation1(norm,refs)['groups']
 names=dict(all84='all84',own_flipped='alpha6_flipped',fixed_alpha4_42='alpha4_fixed42',alpha6_flipped_in_alpha4_cohort='retained_alpha4_flippers',newly_flipped_alpha6='newly_flipped_at6')
 for an,qn in names.items():
  for c in a.CONDITIONS:
   for l in('44','52'):
    aa=ar['cohorts'][an][c][l];qq=qr[qn]['readouts'][c][l]
    assert aa['planned_n']==qr[qn]['n']
    for cat in('old','new','dual','neither'):
     assert aa['rates'][cat]['n']==qq[cat]['known_n']
     for key in('k','planned_n','missing_n','estimate','Wilson95'):assert aa['rates'][cat][key]==qq[cat][key],(case,an,c,l,cat,key)
     count+=1
    for k in('terminal_unparseable_n','unrun_n'):assert aa[k]==qq[k]
 print('case',case,'retained/new/known-dropout/unknown:',*[qr[k]['n']for k in('retained_alpha4_flippers','newly_flipped_at6','alpha4_known_not_flipped6','alpha4_unknown6')])
print('PASS',count,'synthetic cohort/category rate dicts exact; all4 calibration dose-reference arithmetic exact; no actual E135 inputs opened')
```
<!-- /R-Q_REPRO_E135_DEV1_SOURCE_TEST_V1 -->


## 2026-10-30 — E133 PROBES scientific numerical review COMPLETE (primary R-NL1 still PENDING)

Publication `caabe0666` (actual COMMITTER 03:50:02 CET), original probe seal `8001a013014d4960b5eb768bfc7808b85252241db4aa92d4f6c556c4acb0aad6`, executed source `d8e34ad47`: **PASS numerical reproduction, own=worker**. All original aggregate files/seal equal their public copies; original PROBES_ONCE hash `8a1780cf` exact, consumed and never reset/replayed. Main ANALYSIS_ONCE was absent at review and must reuse the already sealed probe result, never fit again. R-Q ran separate independent dev-only models, without calling any author actual adapter, vector loader, analyze, fit guard or main entrypoint.

Custody — PASS: **7 seals /810 member-hash checks** (checks, not a claim of unique files), including original native `9300272f`, CPU identity, inventory `f037ca0e`, probe-input `7b71d51b`, screened selection and both original/public probe seals. Exact PROBE_SPEC `e1d4fe04cc59e621bfe99a7f8f63314e4c50835726a31ef7e01adb415157f511`; 14 executed package files equal committed source, all16 dependency pins exact. All **1080 original vector identity/site joins**, plus **180 native capture INDEX/item/pair/member/family/unhooked/32-token joins and1080 literal native array/layer/index pointers**, independently exact. Vectors are finite 5120-dimensional, no missing among180 members×6layers. Frozen proof covers300 multi-hop/150one-hop candidate pairs; selected first qualifying source order50MH+40one-hop, both members retained, no bAbI and no reader-based selection. Selection proof was verified as frozen metadata; original screening semantic accuracy was not independently reclassified in this probe-only review.

Split/fit — PASS: first30 selected MH pairs (60 members) DEV, remaining20 pairs (40 members) TEST; pair IDs disjoint. One-hop40pairs/80members are transfer-only, with the SAME fits. All **18 fixed LogisticRegression C=1/lbfgs/max_iter2000/seed0 models** fit on original DEV activations/labels only, no scaling/tuning/refit/CI. All **36 group-level metric/coverage dictionaries and264 class dictionaries** exactly match original worker results, including trained/absent classes, positive/negative counts and unseen targets. No metric enters R-NL1.

| Block | Twin MH TEST | Current MH macroOVR | Previous MH macroOVR | Twin one-hop | Current one-hop macroOVR | Previous one-hop macroOVR |
|---|---:|---:|---:|---:|---:|---:|
| 36 | 0.570000000000 | 1.000000000000 | 0.886665441176 | 0.543750000000 | 0.895396582020 | 0.601219034703 |
| 44 | 0.567500000000 | 1.000000000000 | 0.877887254902 | 0.532500000000 | 0.886360125437 | 0.715009986928 |
| 48 | 0.552500000000 | 1.000000000000 | 0.863543504902 | 0.550625000000 | 0.951360250845 | 0.758924235320 |
| 52 | 0.580000000000 | 1.000000000000 | 0.814536764706 | 0.526250000000 | 0.998029279279 | 0.764512567978 |
| 56 | 0.585000000000 | 1.000000000000 | 0.809004289216 | 0.554375000000 | 1.000000000000 | 0.820958992202 |
| 60 | 0.595000000000 | 1.000000000000 | 0.859067401961 | 0.530625000000 | 0.999229231678 | 0.838662869161 |

Coverage/reading — binary twin TEST covers2/2 classes and40/40 known, AUROC .5525–.5950 across sites; this is a point-estimate result, without added significance/equivalence claim. Current-holder MH macroOVR1.0 is **7/10 evaluable classes**,8trained,0unseen test targets; previous-holder MH .809004–.886665 is **5/10 evaluable**,7trained,2/40 unseen targets. One-hop current uses8/10 evaluable with11/80 unseen targets; previous6/10 with14/80 unseen targets. All vector missing counts0. The macro scores average only evaluable one-vs-rest classes, so1.0 is not perfect full10-class identity decoding or a complete-cohort multiclass accuracy. Absent and unseen classes stay disclosed. Current identity, previous identity and binary twin are distinct targets; do not replace the registered binary probe headline with the descriptive current score or infer a causal mechanism from these probes alone. No confidence intervals were registered/added here. QA2 episode CV is literal null because this packet contains no bAbI; E133b remains separate.

Chronology — executed source `d8e34ad47` actual03:16:31 CET < PROBE_SPEC publication `45de8876b`03:25:31 < original FIRST_OPENING receipt03:48:36.595308 < public probe commit03:50:02. E134 published selection `18170136`/`fafc8edd3`03:14:47 predates this opening; only that hash/prerequisite was checked, not E134 selection outcomes (R3 ownership). The native outer first-output receipt is02:30:31.199630 CET, preceding the probe-phase/episode source updates; this review does not relabel those updates as pre-acquisition or certify earlier first-ever opening/discarded history. Original fixed synthetic-probe source and phase lifecycle reviews remain preserved. No actual E133 reader judgments, R-NL1 ratios, E133b outputs or E117 main semantics were opened for this component.

Separate source intake: E135 `d28e9261c` actual03:49:16 CET changes only the prospective input-custody gate from superseded three-dose882ddcaa to published alpha6 `381b58bd`, after acquisition/before owner-declared scientific opening. All6 updated receipt pins exact;5 scientific functions AST-identical to reviewed d94278a73. The one new pure accept-current/reject-superseded test PASS; earlier16 statistical/source tests were not repeated unchanged. No E135 guard/output opening or scientific verdict.

Independent reviewer reproduction, read-only original custody and own models only (no author production entrypoint):

<!-- R-Q_REPRO_E133_PROBES_REAL_V1 -->
```python
"""Independent sealed E133 probe reproduction. Read-only custody; no author entrypoint or guard."""
from pathlib import Path
import json,hashlib,subprocess,warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.exceptions import ConvergenceWarning
ROOT=Path.cwd();pub=ROOT/'results/g_agreement/understand/e133/analysis/probes/sealed_run';seen={};member_checks=0

def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def seal(p,digest=None):
 global member_checks
 p=Path(p)
 if digest is not None:assert sha(p)==digest
 if str(p)not in seen:
  z=read(p)
  for n,h in z['files'].items():assert sha(p.parent/n)==h,(p.name,n);member_checks+=1
  seen[str(p)]=z
 return seen[str(p)]
receipt=read(pub.parent/'PUBLICATION_RECEIPT.json');s=seal(pub/'ANALYSIS_SEAL.json',receipt['analysis_sha256']);assert s['analysis_component']=='PROBES'and s['status']=='COMPLETE_ONCE'
original=ROOT/'cache/g_agreement/understand/e133/probes_once'
# The original once directory belongs to B, not the reviewer checkout.
original=ROOT.parent/'wt-internals-b/cache/g_agreement/understand/e133/probes_once'
seal(original/'ANALYSIS_SEAL.json',receipt['analysis_sha256'])
for f in list(s['files'])+['ANALYSIS_SEAL.json']:assert (original/f).read_bytes()==(pub/f).read_bytes()
guard=original.parent/'PROBES_ONCE.json';assert sha(guard)==receipt['probe_guard_sha256']
spec=read(pub/'BINDING.json')
# Exact spec dictionary, original bound inventory and complete source closure.
assert spec==read(ROOT/'results/g_agreement/understand/e133/probe_spec_trackq/PROBE_SPEC.json')
ip=Path(spec['inventory_seal']);iv=seal(ip,spec['inventory_sha256']);assert iv['status']=='SCREENED_COHORT_FROZEN'and iv['labels_cpu_only']
ss=seal(iv['screen_seal'],iv['screen_sha256']);proof=read(Path(iv['screen_seal']).parent/'SCREEN_SELECTION.PRIVATE.json')
assert iv['classifier_sha256']==proof['classifier_sha256']=='cf6bc5edc904a688b4c292064f230cbb6feec0b9a437ed80ac3b7993396fc390'and iv['greedy_max_new_tokens']==32
pairs=read(ip.parent/'PAIRS.PRIVATE.json');names=read(ip.parent/'FIXED_NAMES.PRIVATE.json');assert len(names)==len(set(names))==10
for kind,total,limit in [('multi_hop',300,84),('one_hop',150,42)]:
 rows=sorted([x for x in proof['screening']if x['kind']==kind],key=lambda x:x['generation_index']);assert len(rows)==total and len({x['generation_index']for x in rows})==total
 ids=[x['pair_id']for x in rows if x['correct_both']][:limit];assert ids==proof['selected'][kind]==[p['pair_id']for p in pairs if p['kind']==kind]
assert len(pairs)==len({p['pair_id']for p in pairs})==90 and {p['kind']for p in pairs}=={'multi_hop','one_hop'}
vp=Path(spec['probe_input_seal']);vm=seal(vp,spec['probe_input_sha256']);assert vm['status']=='COMPLETE'and vm['inventory_sha256']==spec['inventory_sha256']and vm['layers']==[36,44,48,52,56,60]
source_seals=[seal(z['seal'],z['sha256'])for z in vm['source_seals']];assert all(z['experiment']=='E133'and z['status']=='COMPLETE'for z in source_seals)
assert any(z['sha256']==spec['native_output_sha256']for z in vm['source_seals']);cached={}
def ref(p):
 i=p['seal_index'];assert type(i)is int and 0<=i<len(source_seals)and p['member']in source_seals[i]['files'];key=(i,p['member'])
 if key not in cached:
  f=Path(vm['source_seals'][i]['seal']).parent/p['member'];cached[key]=np.load(f,allow_pickle=False)if f.suffix=='.npy'else read(f)
 v=cached[key]
 for k in p['keys']:v=v[k]
 return v
vectors=read(vp.parent/'VECTORS.PRIVATE.json');by={p['pair_id']:p for p in vectors};assert len(by)==len(vectors)==90 and set(by)=={p['pair_id']for p in pairs}
sitejoins=0
for p in pairs:
 assert len(p['members'])==len(by[p['pair_id']]['members'])==2
 cur=[m['current']for m in p['members']];prev=[m['previous']for m in p['members']];assert len(set(cur))==2 and prev[0]==prev[1]and prev[0]not in cur
 for j,(m,v)in enumerate(zip(p['members'],by[p['pair_id']]['members'])):
  assert m['member']==v['member']==j and m['current']in names and m['previous']in names
  m['vectors']={};assert set(v['vectors'])=={'36','44','48','52','56','60'}
  for l,c in v['vectors'].items():
   ident=ref(c['identity']);assert ident==dict(pair_id=p['pair_id'],item_id=m['item_id'],member=j,kind=p['kind'],mode='vector',block=int(l));a=np.asarray(ref(c['vector']),dtype=float);assert a.ndim==1 and np.isfinite(a).all();m['vectors'][int(l)]=a;sitejoins+=1
# Prerequisite checks bind only the published selection; no E134 outcome reanalysis.
sel=ROOT/'results/g_agreement/understand/e134/analysis_once/SELECTION_SEAL.json';assert sha(sel)==receipt['E134_selection_sha256']
# Independently fit 18 fixed models, with dev-only labels and no normalization/tuning.
expected=read(pub/'PROBE_RESULTS.json');mh=sorted([p for p in pairs if p['kind']=='multi_hop'],key=lambda p:p['generation_index']);oh=[p for p in pairs if p['kind']=='one_hop'];assert len(mh)==50 and len(oh)==40
assert len({p['pair_id']for p in mh[:30]}&{p['pair_id']for p in mh[30:]})==0
checks=0;headlines={};classchecks=0
for layer in(36,44,48,52,56,60):
 headlines[str(layer)]={}
 for target in('twin_identity','current','previous'):
  label=lambda m:m['member']if target=='twin_identity'else m[target]
  train=[m for p in mh[:30]for m in p['members']];x=np.stack([m['vectors'][layer]for m in train]);y=[label(m)for m in train]
  with warnings.catch_warnings():
   warnings.simplefilter('error',ConvergenceWarning);mod=LogisticRegression(C=1.,solver='lbfgs',max_iter=2000,random_state=0).fit(x,y)
  fixed=[0,1]if target=='twin_identity'else names;entry=expected['layers'][str(layer)][target];assert entry['dev_pairs']==30 and entry['test_pairs']==20 and entry['status']=='DESCRIPTIVE'
  for kind,group in [('multi_hop_test',mh[30:]),('one_hop_descriptive',oh)]:
   rows=[m for p in group for m in p['members']];probs=mod.predict_proba(np.stack([m['vectors'][layer]for m in rows]));got=entry['groups'][kind];cs=[]
   for j,value in enumerate(fixed):
    yy=np.array([label(m)==value for m in rows]);trained=value in mod.classes_;auc=None if not trained or len(set(yy))<2 else float(roc_auc_score(yy,probs[:,list(mod.classes_).index(value)]))
    cc=dict(class_index=j,trained=bool(trained),AUROC=auc,n_positive=int(yy.sum()),n_negative=int((~yy).sum()));assert cc==got['classes'][j],(layer,target,kind,j);classchecks+=1;cs.append(auc)
   eligible=[v for v in cs if v is not None];metric=cs[1]if target=='twin_identity'else float(np.mean(eligible))if eligible else None
   want=dict(planned_n=len(rows),n=len(rows),missing_n=0,unseen_target_n=sum(label(m)not in mod.classes_ for m in rows),classes=got['classes'],binary_AUROC=metric if target=='twin_identity'else None,macro_ovr_AUROC=metric if target!='twin_identity'else None,n_evaluable_classes=len(eligible),n_trained_classes=len(mod.classes_),n_fixed_classes=len(fixed),status='DESCRIPTIVE'if eligible else'NOT EVALUABLE');assert want==got,(layer,target,kind);checks+=1
   if kind=='multi_hop_test':headlines[str(layer)][target]=metric
  print('verified fixed fit',layer,target,flush=True)
assert expected['babi_qa2_episode_cv']is None and headlines==receipt['headline']
opening=read(pub/'FIRST_OPENING.json');assert opening['code_commit']==s['code_commit']==receipt['executed_source'];assert opening['inventory_sha256']==spec['inventory_sha256']and opening['native_output_sha256']==spec['native_output_sha256']
summary=dict(status='PASS',seal_count=len(seen),member_hash_checks=member_checks,vector_identity_joins=sitejoins,native_vector_shape=list(pairs[0]['members'][0]['vectors'][36].shape),models=18,group_metric_and_coverage_checks=checks,class_dict_checks=classchecks,headlines=headlines,inventory_counts=dict(multi_hop=50,one_hop=40,dev_pairs=30,test_pairs=20),probe_guard_hash_exact=True,main_guard_exists=(original.parent/'ANALYSIS_ONCE.json').exists(),PROBE_SPEC_sha256=sha(ROOT/'results/g_agreement/understand/e133/probe_spec_trackq/PROBE_SPEC.json'))
Path('/tmp/rq_e133_probe_real_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
```

Additional literal native INDEX check:
```python
from pathlib import Path
import json
R=Path.cwd();read=lambda p:json.loads(Path(p).read_text());s=read(R/'results/g_agreement/understand/e133/analysis/probes/sealed_run/BINDING.json');vm=read(s['probe_input_seal']);native=Path(vm['source_seals'][1]['seal']).parent;ix=read(native/'main_synthetic/INDEX.json');caps={x['id']:x for x in ix if x['kind']=='capture_answer'};pairs=read(Path(s['inventory_seal']).parent/'PAIRS.PRIVATE.json');vby={x['pair_id']:x for x in read(Path(s['probe_input_seal']).parent/'VECTORS.PRIVATE.json')};cache={};n=0
for p in pairs:
 for m,z in zip(p['members'],vby[p['pair_id']]['members']):
  x=caps[m['item_id']];f=native/'main_synthetic'/x['member'];raw=cache.setdefault(str(f),read(f))[x['record']]
  assert raw['id']==m['item_id']and raw['pair_id']==p['pair_id']and raw['member']==m['member']and raw['condition']=='unhooked'and raw['greedy_max_new_tokens']==32
  assert raw['family']==p['kind']
  for l,cell in z['vectors'].items():
   v=cell['vector'];a=x['layers'][l];assert v['seal_index']==1 and v['member']=='main_synthetic/'+a['member']and v['keys']==[a['index']];n+=1
print('PASS:180 native capture INDEX/item/pair/member/family/32-token identities and',n,'literal native layer/array/index pointers exact')
```
<!-- /R-Q_REPRO_E133_PROBES_REAL_V1 -->


## 2026-10-30 §217 — E133 synthetic judging CUSTODY COMPLETE; scientific main PENDING

Shared C publication `8051620f4` (actual COMMITTER04:07:11 CET), receipt04:07:09.310944 CET: archive `1c159086` **455572 bytes /706 files** exact whole-archive SHA. All **8 archived JUDGMENT_SEAL member pins**, the corresponding **8 original CPU judging pins** (`de299399`), and **1 original keyed-binding pin** (`4fbe92c7`) independently exact. This is hash-only custody, without semantic code/readout opening. Owner reports540terminal=467KEPT+73UNPARSEABLE, provider-known/totalbookedUSD.24170250, explicitbound0/unknown0; receipt arithmetic exact, terminal labels/counts not independently interpreted. Shared E133bank≤5 remains OPEN for E133b; no unused release or cap reset. B final COMPLETE main SPEC and one scientific invocation still pending; original probes8001a013 already reviewed and must be reused without refit. R-Q did not invoke author loader/adapter/main guard or open any E133 main readout, code, patch score or ratio. No scientific-main completion inferred from judging delivery.

Every new dated canonical amendment read: `40a1a54f0` actual04:05:43 CET, nominal04:10. E134T7's one-hour clock now starts at terminal judging seal rather than acquisition; prior operational-miss text is superseded, E134 outcomes stay R3. E133b deviation1 explicitly permits ONE further attempt with5400s from creation /≤USD7.94, createby10Z/hardstopmin(cap,12:50Z), actual C byte-identical source and CPU selector provenance reconciled BEFORE launch, all previous partial screens excluded/no stitching, anotherNOFIT=>NOTRUN. This is Guiv's canonical amendment, not reviewer-created retry/cap authority. `ca01c071d` reconciliation/`0b23a2a6e` owner launch receipts are received operationally; source/actualbinding/firstopening and original output custody still need final verification, no blanket reviewer launch/timing certification. No reviewer process/GPU/API/paid/ledger operations.

C E135 current bank1/local-only publication dispositions ACK: raw GPU/judgment Git-export rejection stays in force; aggregate/source-hash/CPU-local exact pointers are the authorized publication route. No raw archive is requested or published by R-Q, no workaround. Original E135 outputs/scientificseal still pending/unopened by reviewer. E136 new bank/source arrivals belong R2; E107b/E131 outcomes left their established owners. All closed probe/source/statistical audits remain closed unchanged.


E135 arrival during publication — custody COMPLETE, science still PENDING: C receipt03:14:10.006502Z supersedes the earlier RUNNING snapshot above. Exact LOCAL-ONLY raw archive SHAe29525fe, 7 original checked-phase member pins/3 canonical-bank pins8bd543d6 and keyed-pointer SHAa1cef849 all independently verified, without parsing semantic codes or exporting/copying raw data. Owner336=333KEPT+3UNPARSEABLE, booked/providerknownUSD.17618900/upper0/unknown0; receipt arithmetic .176189+.823811unused=original1, reserve0, released once/no reset. These remain owner terminal counts, not reviewer semantic recoding. Raw Git-export hold retained; final W-mech2 original SPEC/code-null/native/calibration scientific binding and sealed one-run report pending, no real adapter/guard opening.


## §248 C first step — direct Guiv item-join verification COMPLETE before predictor work

Canonical `d1567e78b` actual COMMITTER04:20:13 CET (nominal04:30), plus direct Guiv instruction: rechecked the requested count from the **individual frozen item joins**, not aggregate subtraction alone. The84 original E128 identities partition into the42 original steered-alpha4 native pair-preference flippers and42 distinct complementary identities; the sets are disjoint/exhaustive, with original old/new orientation retained. On the complementary42, the exact alpha8/block44 codes bound by E128 SPEC69af33cc to **E109-reference judgment seal `ef8ea43b`** are **old42/new0/dual0/neither0/missing0**. Thus **42/42** is independently confirmed for that bank. Whole84old47 minus fixed-cohortold5=42 agrees; the single reference-bank alpha8 missing code lies INSIDE the fixed42, not the complementary42. No rejudging, feature selection or predictor computation was used.

Bank provenance is an explicit part of this prerequisite. These are **E104-source readouts in E128's E109-reference bank**. Independently rechecked original E104 judgment seal `ce564237` plus original PRIVATE hash `495bbb19` on the SAME42 IDs/orientation: **old41 +1 valid names_property_without_value/neither, missing0**; whole46 minus fixed5=41. OriginalE104≠E128/E109-reference codes. Existing4category/value-code discrepancies and80/84 matching texts remain disclosed; no silent bank replacement, recoding or assertion that original E104's own bank is42/42. §248 C's implied42/42 is verified ONLY with the already-bound E128/E109-reference outcome; downstream source/SPEC must explicitly preserve that outcome-bank identity and the original-E104 sensitivity distinction.

First-step status — COMPLETE (bank-qualified item-join check); no predictor AUROC, bootstrap, logistic/leave-one-out fit, E109 probe-margin extraction, E131 margin opening or E135 new output opening occurred. The non-alpha4 complement42 is not silently equated with the future min-dose≤6 versus8 split: alpha6 membership/unknowns still require the sealed E135 result. §248C remains exploratory and scheduled after E133 andE135, otherwise research phase. No existing once guard is reset/replayed, and no E104/E109 author analysis/normalizer is invoked. Earlier published42/42 already existed before §248C registration; this is a requested verification of that prior count, not a newly prospective discovery. All other closed numeric audits stay closed. §248A/R2, §248B/R3 and §247clarification1/R2 were read and retain their owners.


## E133b final independent review — NOT EVALUABLE (measurement), SCREEN ONLY

Shared disposition `ca283a8a8`/`34de555aa` records Guiv's final “not measurable” instruction; final machine receipt is `FINAL_DISPOSITION.json`. Independent read-only audit of the ORIGINAL completed attempt3 outer seal `90e6c5ea87323a43642d860a834354969d63826909e57b64de146964dbeb7dea` and screen seal `56ffafa9938ef289d8d392b8d11c316135adef80de94d97081bf4080543dd19c`: **404 member hash checks exact**, including original CPU494-pair labels (`9364a864`) and public988-prompt input (`0d2bd396`). All988 IDs match public inputs exactly; both original pair members and three distinct current/twin/previous roles retained, no old partial source loaded. Registered parser cf6bc5ed and executed selector b589dbaa hashes exact. R-Q independently implemented the parser's literal case-insensitive word-boundary/exactly-one-candidate rule; did not invoke the author selector/reparse/run/once guard or write a new roster.

Own=worker counts EXACT: **988 screened members; 973 no unique candidate =959 no candidate +3 multiple candidates +11 empty texts**. The15 unique matches are3 own-current/10 previous/2 twin-current. Both-members-correct qualifying pairs **0/494**. Token counts:977 full32-token continuations and11 single-token empty-text continuations. Thus the registered fewer-than20 gate yields **SCREEN RESULTS ONLY**; no main capture, reader judgments, patching or probes exist for this arm. These findings support **NOT EVALUABLE (measurement)**: the registered32-token screen did not measure the requested answer in this format. They do not establish model-task failure, no underlying state or a negative R-NL1 result. E133 synthetic findings stand separately; no pooling.

Disposition CLOSED: no further E133b sprint run, pair-logit screening is research phase only; earlier E133a1/E133ba1/a2 partials stay sealed, excluded and unopened, no stitching/recovery/reclassification. This is the original final attempt's result; no new selector/main/analysis guard was consumed by R-Q. Source/operator cap and cost receipts are preserved as actual history; this audit does not retroactively certify every operator launch clock or earlier discarded history. E133b episode-CI source review remains closed but has no bAbI analysis outcome to evaluate now. Do not keep polling for bAbI main/probe/judging seals after this final disposition unless Guiv reactivates the experiment.

Independent final-screen reproduction (private inputs read-only; no raw texts/labels emitted):

<!-- R-Q_REPRO_E133B_FINAL_V1 -->
```python
"""Independent E133b final screen measurement audit; no selector/model/once entrypoint."""
from pathlib import Path
import json,hashlib,re,collections
R=Path.cwd();BASE=R.parent;out=BASE/'wt-wmech/cache/g_agreement/understand/analysis402_verified/E133b/a3/out'
read=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();checks=0

def verify(p,h=None):
 global checks
 p=Path(p)
 if h:assert sha(p)==h
 z=read(p)
 for n,d in z['files'].items():assert sha(p.parent/n)==d;checks+=1
 return z
final=read(R/'results/g_agreement/understand/e133b/FINAL_DISPOSITION.json');outer=verify(out/'OUTPUT_SEAL.json',final['final_outer_seal_sha256']);assert outer['status']=='COMPLETE'
screen=out/'screen_babi';sc=verify(screen/'OUTPUT_SEAL.json');assert sha(screen/'OUTPUT_SEAL.json').startswith(final['screen_seal_prefix'])and sc['status']=='COMPLETE'and sc['experiment']=='E133'and sc['arm']=='babi'
cp=BASE/'outputs/e133-babi-v1/packet/cpu_only';verify(cp/'LABEL_SEAL.json','9364a8644a4222e769043cd217c0f67f14ff1cc349401cbc70c816289f89d390');labels=read(cp/'LABELS.PRIVATE.json');assert len(labels)==494
public=BASE/'outputs/e133b-inputs-v1/inputs';verify(public/'INPUT_SEAL.json','0d2bd3968b0f4eb6981d960d3054ebc87d2e2ae52e150395d82a894ec56e2ec1');items=read(public/'items.json');assert len(items)==988
assert sha(R/'projects/g_agreement/core/analysis_utils.py')=='cf6bc5edc904a688b4c292064f230cbb6feec0b9a437ed80ac3b7993396fc390'
assert sha(R/'projects/g_agreement/e133b/selection.py')==final['selector_sha256']
answers={}
for f in sorted(n for n in sc['files']if n.startswith('jobs/')):
 for row in read(screen/f):assert row['id']not in answers;answers[row['id']]=row
assert len(answers)==988 and set(answers)=={x['id']for x in items}
counts=collections.Counter();lengths=collections.Counter();qual=0;seen=set()
for p in labels:
 mids=p['member_ids'];mids=json.loads(mids.replace("'",'"'))if isinstance(mids,str)else mids
 cands=[p['original_current'],p['twin_current'],p['previous']];assert len(set(cands))==3;correct=[]
 for j,i in enumerate(mids):
  assert i not in seen;seen.add(i);raw=answers[i];text=raw.get('text');lengths[len(raw.get('token_ids',[]))]+=1
  if not text:counts['empty_text']+=1;correct.append(False);continue
  hits=[k for k,c in enumerate(cands)if re.search(r'(?<!\w)'+re.escape(c)+r'(?!\w)',text.lstrip(),re.I)]
  if not hits:counts['no_candidate']+=1
  elif len(hits)>1:counts['multiple_candidates']+=1
  elif hits[0]==j:counts['own_current_unique']+=1
  elif hits[0]==2:counts['previous_unique']+=1
  else:counts['twin_current_unique']+=1
  correct.append(len(hits)==1 and hits[0]==j)
 qual+=all(correct)
assert len(seen)==988 and qual==final['qualifying_pairs']==0
counts['no_unique_match']=counts['empty_text']+counts['no_candidate']+counts['multiple_candidates']
for key,val in counts.items():assert val==final[key],(key,val,final[key])
assert lengths=={32:977,1:11}
assert not(out/'main_babi').exists()or not any((out/'main_babi').rglob('*.npy'))
summary=dict(status='PASS',member_hash_checks=checks,outer_sha=sha(out/'OUTPUT_SEAL.json'),screen_sha=sha(screen/'OUTPUT_SEAL.json'),screened_members=988,qualified_pairs=qual,counts=dict(counts),token_length_counts=dict(lengths),final_disposition='NOT EVALUABLE (measurement); screen-only; no negative task/model claim')
Path('/tmp/rq_e133b_final_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
```
<!-- /R-Q_REPRO_E133B_FINAL_V1 -->

## §248C prospective statistical source review / reproduction READY (real companion still PENDING)

Source `ac4b23229`:15 source/dependency hashes exact working+Git; **8 C-only pure tests PASS +8 exact committed-extraction PASS** (7 A/R2 tests deselected). No actual C input, probe margin, outcome, model, predictor, original/source guard or run.main entrypoint opened/invoked. Independent synthetic prewrite verifies81 minimum-dose/unknown sequences,3 full5000seed0 rank-AUROC/bootstrap cases (max source-vs-independent floating drift1.3877787807814457e-17),2 training-only-scaled LOO cases, and an84-row cohort/category census with unknown, never-flip, dual and missing codes. End-to-end synthetic census uses40draws explicitly for speed; the independent AUROC kernel comparisons used the full registered5000. The earlier42/42 real item-join prerequisite was already completed separately, not recomputed by this source review.

Conventions reviewed before C opening: all four literal2/4/6/8 pair-flip fields; an unknown earlier dose keeps minimum unknown, never-flip is not dose8; old-present outcome explicitly includes old+dual at8, retaining all separate category cells and nulls; exact E128/E109-reference bank required, originalE104 distinction preserved. This prospective old-present predictor endpoint is labelled as such, not substituted for prior exclusive-old primary statistics. Fixed signed predictor direction, item bootstrap with one-class draws counted/skipped, no post-hoc AUC inversion. Two-predictor L2 C1/lbfgs/maxiter2000/seed0 LOO, training-fold-only scaling; primary original unhooked E131 margin+unhooked fact probe, alpha8 probe separate sensitivity, no winner selection or causal claim. Raw coefficients descriptive; finite/missing and class coverage remain explicit.

Source-level kernels/prewrite PASS, **not real execution GO**: full owner-bound TABLE_POINTERS/source roles/signs/bank identity/terminal evidence, exact original E117/E133/E135 scientific dependencies, B sealed frozen-probe-margin delivery and R-Q item-join receipt must be inspected as genuine matching dependencies, not accepted merely as boolean flags or existing arbitrary seal files. The source entrypoint hashes dependency seals; it does not itself establish all scientific identity/status semantics, so final SPEC review remains required. Existing historical guards stay immutable; fresh C_ONCE only after conditions hold, otherwise research phase. No predictor or real C fit is authorized by this synthetic source review alone.

<!-- R-Q_REPRO_248C_SYNTHETIC_V1 -->
```python
"""Prewritten §248C reproduction, synthetic-only until all original sealed dependencies arrive."""
import sys,copy,itertools
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from projects.g_agreement.companions248 import predictors as w

def minimum(flags):
 seq=[flags[str(d)]for d in(2,4,6,8)]
 for j,v in enumerate(seq):
  if v is True:return None if None in seq[:j]else (2,4,6,8)[j]
 return None

def rankauc(x,y):
 a=np.asarray(x)[np.asarray(y)==1];b=np.asarray(x)[np.asarray(y)==0]
 return None if not len(a)or not len(b)else float(np.mean((a[:,None]>b).astype(float)+.5*(a[:,None]==b)))

def independent_auc(x,y):
 x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float);known=np.isfinite(x)&np.isfinite(y);x=x[known];y=y[known];point=rankauc(x,y)
 if point is None:return dict(kept=len(y),estimate=None,CI95=None,valid_bootstraps=0)
 rng=np.random.default_rng(0);values=[]
 for _ in range(5000):
  ix=rng.integers(0,len(y),len(y));a=rankauc(x[ix],y[ix])
  if a is not None:values.append(a)
 return dict(kept=len(y),estimate=point,CI95=np.quantile(values,[.025,.975]).tolist()if values else None,valid_bootstraps=len(values))

def independent_loo(x,y):
 x=np.asarray(x,float);y=np.asarray(y,float);keep=np.isfinite(x).all(1)&np.isfinite(y);x=x[keep];y=y[keep]
 if len(y)<3 or len(set(y))<2:return None
 predictions=[]
 for i in range(len(y)):
  j=np.arange(len(y))!=i
  if len(set(y[j]))<2:return None
  mu=x[j].mean(0);sd=x[j].std(0);sd[sd==0]=1
  model=LogisticRegression(C=1.,solver='lbfgs',max_iter=2000,random_state=0).fit((x[j]-mu)/sd,y[j]);predictions.append(model.decision_function((x[i:i+1]-mu)/sd)[0])
 return rankauc(predictions,y)

if __name__=='__main__':
 for seq in itertools.product((False,True,None),repeat=4):assert minimum(dict(zip(w.DOSES,seq)))==w.min_dose(dict(zip(w.DOSES,seq)))[0]
 maxdrift=0
 for x,y in [([0,0,1,2,3,3,5,6],[0,1,0,1,0,1,0,1]),([1,0,1,0],[0,1,0,1]),([np.nan,2,3],[0,0,0])]:
  a=w.auc_ci(x,y);b=independent_auc(x,y)
  assert a['kept']==b['kept']and a['valid_bootstraps']==b['valid_bootstraps']
  for key in('estimate','CI95'):
   if a[key]is None:assert b[key]is None
   else:
    d=float(np.max(np.abs(np.asarray(a[key])-b[key])));maxdrift=max(maxdrift,d);assert d<1e-14
 for x,y in [([[i,i%3]for i in range(14)]+[[np.nan,1]],[int(i>=7)for i in range(14)]+[1]),([[0,0],[1,1],[2,2]],[0,0,1])]:
  assert w.loo(x,y)['auroc']==independent_loo(x,y)
 # Full 84-item synthetic census: unknown minimum/never-flip/missing code/dual retained.
 rows=[]
 for i in range(84):
  flips=dict(zip(w.DOSES,[(i%3==0),(i%2==0),(i%4!=0),True]))
  if i%17==0:flips['2']=None
  if i%19==0:flips={d:False for d in w.DOSES}
  rows.append(dict(id=str(i),flips=flips,codes={d:{'44':None if i%23==0 else ('old','new','dual','neither')[i%4],'52_new':bool(i%2)}for d in w.DOSES},unhooked_margin=float(i-41),probe_unhooked=float((i*7)%11),probe_alpha8=float((i*3)%13)))
 # Only shorten draws inside this pure synthetic end-to-end census test; kernel above used full5000.
 saved=w.DRAWS;w.DRAWS=40;got=w.analyze(copy.deepcopy(rows));w.DRAWS=saved
 cross=[[0,0],[0,0]];excluded=0
 for r in rows:
  dose=minimum(r['flips']);cat=r['codes']['8']['44'];target=None if cat is None else int(cat in('old','dual'))
  if dose is None or target is None:excluded+=1
  else:cross[int(dose==8)][target]+=1
 assert got['min_dose_by_old44']==cross and got['cross_missing']==excluded
 print('PASS:81 minimum-dose uncertainty cases;3 rank-AUROC/full5000 bootstrap cases;2 training-only scaled LOO cases;84-row split/missing/dual census; max AUROC/CI float drift',maxdrift)
```
<!-- /R-Q_REPRO_248C_SYNTHETIC_V1 -->

New dated amendments read in full: §24955583c4b3 (actual04:28:50 CET), coordinator c0c66589b (04:33:34), clarification e02db7a11(04:38:39). E137/R4 owns the new recency-controlled family and full R-NL1-derived confidence/control gates; R-Q does not take its source/outcomes. E136 deviation1/final NOT RUN belongs R2/I2, left owners. E117 top-priority same-bank recovery/source/admission notices received operationally; scientific adapter/score rules and final binding/EOS requirements remain unchanged, no R-Q process/paid/controller/route/ledger action or financial certification. E133 synthetic main and E135 scientific seals remain pending at this snapshot; closed probe/statistical audits not repeated.


## §217 E117 main terminal-source custody COMPLETE — scientific review remains PENDING

`790ccea51`/`253aaa7c5` original main phase `acc835c2` and keyed owner handoff `050ba6ff` received. Independent original hashes:5 seals/18 member checks,2 public helper-source pins +2 private publisher-helper hashes exact;6 pure custody-validator synthetics PASS. Original raw archive `40e1d490` **2228025bytes/3697files** and contained3700 member-pin checks (not unique-file count) exact; supplemental row archive `ddfb8623` **338347bytes/4files/3member pins** exact. Portable bank `34ac35d2` matches canonical `431296b6`. This is custody/source verification, not a new scientific result or first native/reader opening.

Important publication caveat independently confirmed: the ORIGINAL completed phase seal and its archive omit JUDGMENTS.json because the resumed writer emitted that already-existing file at the worktree root. They have not been replaced or retroactively described as including it. Separate `ROW_CUSTODY_SEAL e30c62f7` binds byte-exact original emitted rows `2d315489`, original phase-seal bytes and custody lineage; current original root file and companion copy hash-identical. Own independent **3024 literal emitted-row ↔ ordered original UNIT/VALIDATION ↔ final sealed ATTEMPTS joins** match exactly: allunique IDs/order/kind, contiguous planned physical/schema attempt IDs/index, final status/request_id/response_hash and code/null canonical-byte digest. No response decoding/reparse, semantic category/value/evidence interpretation, answer matching, new scoring or response rewriting. Operational terminal-status census2719KEPT+305UNPARSEABLE=3024 independently matches. The missing original-archive member is supplied only by the explicit original-row companion; owner final scientific binding must name it.

Shared-bank custody: both main3024 and previously closed c672 are delivered; total3696. Booked/provider-reportedUSD2.28566300, explicitbounds0/unknown0, reserve0; unused1.71433700 released ONCE from original operational4, extra2 unallocated (registered maximum6 unchanged). Receipt arithmetic verified, no reviewer ledger/allocation/API/route/provider-billing certification or repeat c672 audit. Original nullable terminal codes remain literal; owner sentinels are a separate source-bound representation, not invented zeros.

R-Q actual main native/readout/judgment semantics, norms/token metrics and scientific adapter/guard remain unopened/uninvoked. Final COMPLETE owner SPEC/inventory/source/custody bindings, generation_config/kwargs/EOS/stop/padding proof and existing8-copy privacy primary+exclusion companion are still required before once-only scientific review; never count post-EOS padding or silently retokenize. Source225787 prewrite and E117c scientific result remain closed unchanged. Do not infer science from judging delivery or repeat row/bank audits without changed inputs.

New dated canonical additions read in full: §251eff7c4dba actual05:20:38CET, amendmentf60c40b7b05:23:02, coordinator86f7b83af05:25:23 and clarification53be5003d05:33:24. E139 reward/proxy/instrument/Delta_u are R2; E137 measured attempt R4; E136 aggregate closeout R2/I2. R-Q takes no outcomes, launches or operator reconciliation. E133 main/E135/§248C sealed science still pending; no new R-Q scientific verdict for this source intake.


## DIRECT Guiv E117 priority release — CUSTODY GATE CLEARED; W-Mech2 notified

Guiv explicitly requested immediate E117 custody clearance and a direct message to W-Mech2. Published `f9974e5ed` already completes the unchanged terminal-row custody (3024 dispositions,2719KEPT/305missing), including original omitted-row archive caveat and exact e30c62f7 supplement. Current shared receipt/seal bytes are unchanged from that reviewed publication. At Guiv's explicit human authorization, R-Q sent W-Mech2 the custody **PASS/CLEARED** directly: **no further R-Q custody permission gate; proceed with the single registered E117 analysis run, E117 FIRST**. No worker chat was read; no reviewer real analysis/guard/paid/process action occurred.

The concurrent final inventory-form request is also **PASS/CLEARED**: source `6cc67926b`/canonical1404a3270,13 current source/dependency pins exact working+Git;10 new inventory-only synthetics PASS and10 in exact committed extraction. Analyze/classify/degenerate/main AST unchanged from reviewed225787; prior19 numerical/privacy tests were not repeated unchanged. Independent final SPEC020c7c44/bindingf8946cdc hashes, original INPUT22532aef/all4 original members, all336 ordered literal roster identities/rows84each, and original40dcb4d28 committed PROBE_DELIVERY/direction manifest exact. The accepted representation is honestly POST_ACQUISITION_SOURCE_NORMALIZATION_NOT_NEW_SELECTION, inventory_commit=null, preserving source order rather than backdating a newly normalized inventory. No actual load_inventory/inputs/run invocation, MEASUREMENTS/code/metric interpretation or consumed-guard action by reviewer.

A second direct message delivered this narrow source-form PASS to W-Mech2 as well, explicitly removing both custody and inventory-form holds and identifying final SPEC020c. Owner uses the immutable original bindings, e30 row-custody companion, registered EOS/padding and standing8-ID privacy accounting in the existing single invocation. There is **no remaining R-Q pre-analysis gate** and no request for another approval. Numerical review follows the original sealed scientific result; this release itself is not a scientific verdict.


Publication provenance correction: b5370dd36 also retained the concurrent owner-authored “W-mech2 E117 clearance reconciliation — inventory-only scope” append (two nonblank lines) in the reviewer commit. That request is W-mech2's text, not a new R-Q hold or reviewer-authored finding; the following direct-Guiv PASS explicitly closes it. Preserve the authentic owner note and non-force history; do not reapply it from snapshots. Subsequent reviewer commit additions are only this explicit provenance correction.


## E117 MAIN scientific review COMPLETE — R-IR1 NOT EVALUABLE; falsifier NOT EVALUABLE

Original scientific seal `dab63eee27841192988b533359cc39c5cbdea391005075b00c9afa31e4b7f036`, public `a0879f112` actual COMMITTER06:16:16 CET; source1404a3270/equivalent6cc67926b and final SPEC020c7c44/bindingf8946cdc. **Own=worker numerical reproduction PASS.** Original BINDING/RESULTS/REDACTION_SENSITIVITY/seal hashes exact and public copies byte-identical where published; private BINDING remains local and semantically equals the accepted final SPEC. Main ANALYSIS_ONCE is CONSUMED and is never reset/replayed. R-Q used its already-prewritten independent metric and source resolver, never the author real inputs/analyze/run/normalizer/guard.

Original joins — **3024 native/token/text/row/dose/arm/target/judgment references** exact, plus a separate **3024 original C native→judgment/pointer/request/response/code-or-null-sentinel joins** exact. All2719kept codes independently pass original four-field/category/value/evidence normalization checks and E57 signed scoring;305originalmissing remain null-derived UNPARSEABLE sentinels, never0. All336original targets/roster identities are source-bound; original-source consistency audits remain closed, no new letter selection. The separate e30 row-custody supplement and original acc835/archive omission are explicitly preserved.

Generated-token proof — checked before reviewer degeneration computation: pinned generation_confige70c136c/model revision matches committed original-volume metadata, and the original9a0e583c source archive's4 runner/hook/loader/lens files match the sealed token-custody copies. Actual native OUTPUT44aadc source/input pins match that archive/source seal and original22532input. The actual generate call explicitly overrides model-config do_sample=True with **do_sample=False/max_new_tokens128/use_cacheTrue**, supplies native pad ID and has **no EOS override**; native EOS IDs come from the pinned generation config. Independently all3024 literal token prefixes end at first actual EOS inclusive (or remain whole if no EOS), and hook traces retain precisely generated_position < generated_length−1. **2515 padded rows trimmed /46412 post-EOS token slots excluded**, no decoding or retokenization. All **285828 retained literal norm ratios** match original trace fields. Original raw arrays/traces unchanged. Prefill is untouched and the first answer token is selected before the hook; intervention is on processing generated tokens, not carrier/prefill or that first-token selection. This original timing limitation remains explicit.

Statistics — exact **96 signed-statistic point/CI triples** (48 primary+48 standing privacy-exclusion companion), original2000 paired item draws/seed20261027 with separate arm missing denominators, reused within-row streams in the frozen E100 row order. All **96 known/planned/missing/paired coverage dictionaries**, **72 per-arm degeneration/norm diagnostic dictionaries** and **24 pooled row×dose degeneration censuses** independently match. No complete-case substitution, epsilon, resampling convention, rule threshold or scoring change. Eight privacy-affected readout IDs match the existing source-map1bb216c5 item/row/alpha/arm/text-hash bindings; the companion masks only these8 indent-level scores, retains all original items, and leaves every native diagnostic/exclusion unchanged. Both verdicts stay NE in that companion.

| Registered rule/check | Independent result (worker identical) | Verdict / interpretation |
|---|---|---|
| R-IR1: ≥2 eligible bookkeeping rows with signed T−R≥.30, CI lower>0 and W≤0 | 0 positive rows; nesting_depth has no eligible dose | **NOT EVALUABLE**, not a negative universal mechanism result |
| Pooled degeneration gate (>20% excludes row×dose) | nesting α1=85/252=.337302; α2=99/252=.392857; α4=98/252=.388889 | all3 nesting doses excluded as registered; scores descriptive |
| Meaning of the degeneration gate | nesting missing counts85/99/97 versus flagged85/99/98 | UNPARSEABLE is counted as degenerate by registration; all but1 nesting flag are missing judgments, not demonstrated token repetition. Across all rows323flags=305missing+18 additional native flags. |
| Remaining bookkeeping | indent/page doses eligible; largest T−R points respectively .0222663/.1084337 | neither row reaches the positive rule; no positive structural row |
| Fact control signed T−R at α1/2/4 | −.0385829 [−.1309524,.0476190]; −.0595238 [−.1547619,.0238095]; −.0920826 [−.1758498,−.0192001] | no control movement≥.30; these are signed-score contrasts, not success probabilities |
| Registered falsifier | low-all-eligible rows1, control_movesFalse, nesting unavailable | **NOT EVALUABLE** under the frozen classifier; do not promote source-specific point patterns into a new falsifier |
| Privacy8 companion | all96 primary/companion triples exact; same exclusions and verdicts | no rescue or reversal, no new exclusion rule |

Chronology/custody limits — the committed inventory representation and actual direct reviewer source-clearance messages were received before the sole invocation per owner ACK; the later shared publication of that clearance is not claimed to predate the author result. Original guard fileclock06:14:57.644161 CET < RESULTS.734595 < sensitivity.801101 < seal.801705 < public06:16:16. These are local execution fileclocks, not certification of every earlier opening/discarded history. The author entrypoint loads/scorers inputs before claiming its guard; therefore the guard timestamp is not a certified first-opening timestamp. Source6cc was committed06:00:32; new normalization honestly remains post-acquisition/current-time/commitnull, with historical SOURCE_CUSTODY_RECEIPT's earlier pending-form text retained alongside accepted final COMPLETE binding. Earlier first-ever chronology caveats remain. No author replay or prior partial/E117c pooling.

Conclusion within scope: **E117 main provides no evaluable R-IR1 or registered falsifier verdict**, owing to the registered nesting degeneration exclusion; no observed bookkeeping row is positive, and the fact-control signed contrasts are non-positive. The independently reviewed E117c bookkeeping/fact-interface result remains separate and NE for its own missing sham-yes measurement. Neither result licenses an interface-validation or state-specific E120c-null claim.

Independent final E117 reproduction (requires the already-published R-Q metric module; original inputs read-only):

<!-- R-Q_REPRO_E117_MAIN_REAL_V1 -->
```python
"""Independent E117 numerical review from original sealed sources; no author entrypoints/guards."""
from pathlib import Path
import importlib.util,json,hashlib,re,unicodedata,collections,subprocess
import numpy as np
R=Path.cwd();smod=importlib.util.spec_from_file_location('rqcore','/tmp/rq_prospective_reproductions.py');q=importlib.util.module_from_spec(smod);smod.loader.exec_module(q)
sp=R.parent/'wt-i2/cache/g_agreement/i2/e117_final250_v1/final/SPEC.json';spec=q.read_json(sp);out=Path(spec['analysis']);pub=R/'results/g_agreement/understand/e117/analysis/sealed_main';expected_seal='dab63eee27841192988b533359cc39c5cbdea391005075b00c9afa31e4b7f036'
q.verify_analysis(out/'ANALYSIS_SEAL.json',expected_seal);assert q.sha(pub/'ANALYSIS_SEAL.json')==expected_seal
for f in('RESULTS.json','REDACTION_SENSITIVITY.json'):assert (out/f).read_bytes()==(pub/f).read_bytes()
assert q.read_json(out/'BINDING.json')==spec
# Check the EOS/stop proof before calculating any native diagnostic.
bp=Path(spec['binding_seal']);binding=q.seal_members(bp,spec['binding_sha256']);source=q.Sources(binding['source_seals']);token_dir=Path(binding['source_seals'][0]['seal']).parent
for entry in binding['source_seals']:q.seal_members(entry['seal'],entry['sha256'])
evidence=q.read_json(token_dir/'CUSTODY_EVIDENCE.json');config=q.read_json(token_dir/'generation_config.json');eos=set(config['eos_token_id']);assert eos==set(evidence['eos_token_ids'])and config['pad_token_id']in eos
hook=(token_dir/'source/projects/g_agreement/e117/hook.py').read_text();assert 'do_sample=False,max_new_tokens=128,use_cache=True,pad_token_id=lens.tok.pad_token_id or lens.tok.eos_token_id' in hook and 'eos_token_id='not in hook
# Original model generation_config.do_sample=True is explicitly overridden by generate do_sample=False.
assert evidence['generate_kwargs']['do_sample']is False and evidence['generate_kwargs']['max_new_tokens']==128 and evidence['generation_config_sha256']==q.sha(token_dir/'generation_config.json')
raw_sources=q.Sources(evidence['source_seals']);tokrows=q.read_json(token_dir/'GENERATED_TOKEN_BINDINGS.json');assert len(tokrows)==3024
trimmed=0;removed=0;norm_count=0;native_by={}
for x in tokrows:
 raw=raw_sources.ref(dict(x['original_token_ids'],keys=x['original_token_ids']['keys'][:-1]));assert raw['id']==x['id']
 rawt=raw_sources.ref(x['original_token_ids']);trace=raw_sources.ref(x['original_norm_trace']);assert rawt==raw['token_ids']and trace==raw['norm_trace']
 stop=next((j+1 for j,v in enumerate(rawt)if v in eos),len(rawt));tokens=rawt[:stop];normtrace=[v for v in trace if v['generated_position']<stop-1]
 assert tokens==x['token_ids']and normtrace==x['norm_trace']and x['original_token_count']==len(rawt)and x['generated_token_count']==stop and x['original_trace_count']==len(trace)and x['generated_trace_count']==len(normtrace)
 assert [v['norm_ratio']for v in normtrace]==x['norm_ratios'];assert all(np.isfinite(v)and v>=0 for v in x['norm_ratios']);norm_count+=len(normtrace)
 assert raw['first_answer_token_selected_before_hook']is True and raw['greedy']is True if 'greedy'in raw else raw['first_answer_token_selected_before_hook']is True
 trimmed+=stop<len(rawt);removed+=len(rawt)-stop;native_by[(x['item_id'],str(x['alpha']),x['arm'])]=(raw,x)
# Exact original grid and targets, literal native/judgment/null joins, independent E57 signed score/evidence validation.
ms=q.read_json(bp.parent/'MEASUREMENTS.json');assert len(ms)==336 and len({x['id']for x in ms})==336
norm=lambda text:re.sub(r'\s+',' ',''.join(dict.fromkeys('‘’‚‛',"'").get(c,dict.fromkeys('“”„‟«»','"').get(c,'-'if unicodedata.category(c)=='Pd'else c))for c in text)).strip().casefold()
score_counts=collections.Counter();join_count=0
for x in ms:
 ident=source.ref(x['source_id']);row=source.ref(x['source_row']);target=source.ref(x['target_letter']);assert ident==x['id']and target in('A','B')
 assert set(x['arms'])=={'1','2','4'}
 for alpha,arms in x['arms'].items():
  assert set(arms)=={'T','W','R'}
  for arm,z in arms.items():
   assert source.ref(z['source_id'])==ident and source.ref(z['alpha'])==int(alpha)and source.ref(z['arm'])==arm
   raw,t= native_by[(ident,alpha,arm)];assert t['row']==row and source.ref(z['text'])==raw['text']and source.ref(z['token_ids'])==t['token_ids']and source.ref(z['norm_ratios'])==t['norm_ratios']
   code=source.ref(z['code']);assert set(code)=={'id','category','values','evidence'}and code['id']==z['judgment_id']
   if code['category']=='UNPARSEABLE':assert code['values']==[]and code['evidence']=='';score_counts['missing']+=1
   else:
    assert code['category']in('states_value','names_property_without_value','exhibits','silent')and code['values']in([],['A'],['B'],['A','B'],['B','A'])
    assert bool(code['values'])==(code['category']=='states_value')and bool(code['evidence'])==(code['category']!='silent')and norm(code['evidence'])in norm(raw['text']);score_counts['known']+=1
   join_count+=1
assert join_count==3024 and score_counts=={'known':2719,'missing':305}
items=q.normalize117(spec,real_generated_tokens_verified=True);result=q.e117(items);worker=q.read_json(out/'RESULTS.json');stat_checks=0;diag_checks=0

def compare(got,want):
 global stat_checks,diag_checks
 assert got['R_IR1']==want['rules']['R_IR1']and got['falsifier']==want['rules']['falsifier']
 for row in q.ROW_STREAM:
  for a in('1','2','4'):
   g=got['rows'][row][a];w=want['rows'][row][a];assert g['excluded']==w['excluded_degeneracy']
   for arm in('T','W','R','T_minus_R'):
    assert g[arm]['estimate']==w[arm]['estimate']and g[arm]['CI95']==w[arm]['CI95'],(row,a,arm,g[arm],w[arm]);stat_checks+=1
   for arm in('T','W','R'):
    assert g['diagnostics'][arm]=={k:v for k,v in w['degeneracy']['per_arm'][arm].items()if k!='total'};diag_checks+=1
compare(result,worker)
# No new exclusions: exact standing8-ID source map; score-only mask, native diagnostics unchanged.
pp=Path(spec['privacy_sensitivity_seal']);pm=q.seal_members(pp,spec['privacy_sensitivity_sha256']);mapping=q.read_json(pp.parent/'SENSITIVITY_MAP.PRIVATE.json');assert len(mapping)==len({x['judgment_id']for x in mapping})==8
privids={x['judgment_id']for x in mapping};loc={z['judgment_id']:(x,alpha,arm,z)for x in ms for alpha,v in x['arms'].items()for arm,z in v.items()}
for m in mapping:
 x,a,arm,z=loc[m['judgment_id']];assert x['id']==m['original_e113_item_id']and source.ref(x['source_row'])==m['row']and int(a)==m['alpha']and arm==m['arm'];th=hashlib.sha256(source.ref(z['text']).encode()).hexdigest();assert th in(m['original_audit']['original_readout_sha256'],m['original_audit']['judge_readout_sha256'])
masked=q.e117(items,privids);ws=q.read_json(out/'REDACTION_SENSITIVITY.json');compare(masked,ws['result']);assert ws['redacted_by_row']==dict(nesting_depth=0,indent_level=8,page_range_digit=0,fact_recall=0)
for row in q.ROW_STREAM:
 for a in('1','2','4'):assert masked['rows'][row][a]['diagnostics']==result['rows'][row][a]['diagnostics']
summary=dict(status='PASS',native_judgment_joins=join_count,known=2719,missing=305,raw_EOS_trimmed_rows=trimmed,postEOS_tokens_excluded=removed,retained_literal_norm_ratios=norm_count,statistic_triples_exact=stat_checks,diagnostic_arm_dicts_exact=diag_checks,rules=worker['rules'],privacy_records=8,privacy_rules=ws['result']['rules'],nesting_degenerate=[worker['rows']['nesting_depth'][a]['degeneracy']['degenerate_count']for a in('1','2','4')],original_guard_consumed=(out.parent/'ANALYSIS_ONCE.json').exists())
Path('/tmp/rq_e117_main_real_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
```
Additional native-code and coverage verification:
```python
from pathlib import Path
import json,hashlib,importlib.util
smod=importlib.util.spec_from_file_location('rq','/tmp/rq_prospective_reproductions.py');q=importlib.util.module_from_spec(smod);smod.loader.exec_module(q)
R=Path.cwd();s=q.read_json(R.parent/'wt-i2/cache/g_agreement/i2/e117_final250_v1/final/SPEC.json');bp=Path(s['binding_seal']);b=q.read_json(bp);src=q.Sources(b['source_seals']);bindpath=Path(b['source_seals'][3]['seal']);rawrefs=q.read_json(bindpath.parent/'READOUT_CODE_BINDINGS.PRIVATE.json');refs={v['judgment_id']:v for v in rawrefs.values()};assert len(refs)==len(rawrefs)==3024;sources={};by={}
for entry in refs.values():
 for key in('code_source','judgment_row_source','source_ref'):
  z=entry[key];sources[z['seal']]=dict(seal=z['seal'],sha256=z['sha256'])
resolved=q.Sources(list(sources.values()));idx={z['seal']:i for i,z in enumerate(sources.values())}
def ref(z):return resolved.ref(dict(seal_index=idx[z['seal']],member=z['member'],keys=z['keys']))
ms=q.read_json(bp.parent/'MEASUREMENTS.json');n=0
for x in ms:
 row=src.ref(x['source_row'])
 for a,arms in x['arms'].items():
  for arm,z in arms.items():
   r=refs[z['judgment_id']];t=src.ref(dict(z['source_id'],keys=z['source_id']['keys'][:-1]));assert r['judgment_id']==z['judgment_id']and r['item_id']==x['id']and r['row']==row and r['alpha']==int(a)and r['arm']==arm and r['native_id']==t['id']
   if r['status']=='KEPT':assert ref(r['code_source'])==src.ref(z['code'])
   else:assert ref(r['code_source'])is None and src.ref(z['code'])['category']=='UNPARSEABLE'
   originalrow=ref(r['judgment_row_source']);assert originalrow['id']==r['judgment_id']and originalrow['status']==r['status']and originalrow['request_id']==r['request_id']and originalrow['response_sha256']==r['response_sha256']
   if r['status']=='KEPT':assert originalrow['code']==src.ref(z['code'])
   else:assert originalrow['code']is None and src.ref(z['code'])['category']=='UNPARSEABLE'
   n+=1
print('PASS',n,'exact original native/item/row/alpha/arm-to-judgment and literal code/null-sentinel source joins')
from pathlib import Path
import importlib.util,json,numpy as np
sp=importlib.util.spec_from_file_location('q','/tmp/rq_prospective_reproductions.py');q=importlib.util.module_from_spec(sp);sp.loader.exec_module(q)
R=Path.cwd();s=q.read_json(R.parent/'wt-i2/cache/g_agreement/i2/e117_final250_v1/final/SPEC.json');items=q.normalize117(s,real_generated_tokens_verified=True);o=Path(s['analysis']);m=q.read_json(Path(s['privacy_sensitivity_seal']).parent/'SENSITIVITY_MAP.PRIVATE.json');pids={x['judgment_id']for x in m};checks=0
for mask,result in [(set(),q.read_json(o/'RESULTS.json')),(pids,q.read_json(o/'REDACTION_SENSITIVITY.json')['result'])]:
 for row in q.ROW_STREAM:
  xs=[x for x in items if x['row']==row]
  for a in('1','2','4'):
   v={arm:[None if x['arms'][a][arm]['judgment_id']in mask else x['arms'][a][arm]['score']for x in xs]for arm in('T','W','R')};w=result['rows'][row][a]
   for arm in('T','W','R','T_minus_R'):
    kept=sum(z is not None for z in v['T'if arm=='T_minus_R'else arm]);assert (w[arm]['total'],w[arm]['kept'],w[arm]['missing'],w[arm]['over_5_percent'])==(84,kept,84-kept,(84-kept)*20>84)
    if arm=='T_minus_R':assert w[arm]['other_kept']==sum(z is not None for z in v['R'])
    checks+=1
   deg=sum(x['arms'][a][arm]['degenerate']for x in xs for arm in('T','W','R'));assert w['degeneracy']['degenerate_count']==deg and w['degeneracy']['fraction']==deg/252 and w['degeneracy']['total']==252
 print('rules',result['rules'])
print('PASS',checks,'full known/missing/paired coverage dictionaries plus24 pooled degeneration censuses exact')
```
<!-- /R-Q_REPRO_E117_MAIN_REAL_V1 -->


## DIRECT Guiv E135 calibration-ID source review COMPLETE — PASS / narrow hold CLEARED

Requested exact source `a86beb7508413488b02b0db43a3286b119085aa1`: all6 current source-receipt pins and13 dependency pins independently exact working+committed Git bytes. **9 new alias-map pure tests PASS in checkout +9 PASS in exact committed extraction**: valid acquisition alias accepted;8 drifts rejected (raw alias/base, pointer ID, cohort base, wrong original_item_id substitution, dose, condition, scale, input pin). Owner's full26-test result is retained; R-Q did not repeat the previously closed17 numeric/input tests unchanged.

Source logic PASS: identity_mapping.pointer_ref resolves ORIGINAL_POINTERS.PRIVATE.json under the sealed E135 pointer map whose input_sha256 is exact current381b58bd; acquisition_ref resolves items.json under that exact original input seal. Raw acquisition ID must equal both pointer and acquisition IDs, raw base_id equals acquisition base_id, alpha/condition match the normalized dose/condition, and pointer.original_base_id ALONE supplies original84-cohort identity. original_item_id is never used as a substitute. Original scale=dose/8 is checked. Numeric norm/position/delta fields remain literal captured-field equality checks and are not rewritten. The prior direct-ID representation remains available for source-native IDs. Exact AST comparisons confirm **fixed_cohort/calibration/summarize/analyze/run/verify_input_pin unchanged** from reviewed d28e9261c: no numerical estimator, thresholds, cap, parser, source cohort, output or guard change.

**Narrow R-Q calibration-ID review PASS; no remaining R-Q source-fix hold or further permission request.** W-mech2 can use this committed source with its completed original source-bound SPEC and single existing unused E135 guard, preserving original acquisition/pointer/calibration references and current381b58bd input. No reviewer invocation of the real source mapper, inputs, numeric analysis or once guard; no real E135 source quantities/readouts/outcomes opened by R-Q for this narrow source review. Raw Git-export hold remains; originals stay CPU-local. Post-acquisition/pre-scientific-opening custody correction is explicit, never backdated. Scientific numerical review follows the original sealed output, without resetting a consumed guard.

The other requested review is already complete: E117 main `a0879f112` independently signed off in **a5f01d2fd**, R-IR1 and falsifier NOT EVALUABLE, control_movesFalse,0positivebookkeeping;96 primary/privacy triples exact. Registered nesting exclusion is driven almost entirely by missing judgments, not demonstrated generator collapse. The two requested R-Q reviews are therefore closed; E135's source clearance is not an E135 scientific outcome.


## E133 deviation1 optional preference source review COMPLETE — PASS

Canonical458c41a88 actual06:32:43CET: current-versus-previous preference NOT MEASURED, text/preference agreement dropped; reader/recipient-contrast R-NL1 unaffected. Reviewed published a9b02170e, code077c13da0 actual06:38:21 (original bddbe56ec byte-equivalent receipt). All14 package files and16 dependency pins exact working+Git; rules.py SHA8bcae7d7 and probes.py unchanged. Own8 NEW deviation PURE checkout+8 exact committed-extract PASS; prior unchanged tests not repeated (owner46 retained). Initial extract command named a nonexistent directory and failed before collection; corrected exact committed closure passes. Four additional independent pure combinations PASS: false capture flag with all preference-role metadata absent; wrong raw ID rejected; integer0/null flags rejected.

Only preference may be omitted. If present, original identity remains item/pair/member/mode/site checked; current_previous_contrast_captured must be a strict bool, false requires original raw record ID equality and yields NOT MEASURED with all preference values/masses null. Omitted/false branches never inspect current_previous indices/orientation and never infer preference from recipient contrast. Captured-true path retains separate-contrast/source checks. Greedy/own/readouts/vectors/patches all remain mandatory; five independent missing-field cases fail closed. Text/preference agreement removed; science/bootstrap/probe rules unchanged. No actual outputs, labels, normalizer/input entrypoint, production guard or fit opened/invoked. Original main guard absent at check; consumed8001 probe seal must be reused, never refit. **Narrow source fix PASS; no further R-Q permission hold for this fix.** Complete original final SPEC/source binding remains owner's prerequisite; scientific review follows sealed main output. Source review is not a final binding/first-opening or all-history certification.


## E135 deviation1 scientific numerical review COMPLETE — descriptive only

Published64be0de8f/original717df78053b3fa77342ded7166535fd8d3a878e7cba2e33fa5f78289cb6dc5f4, source2fc793479 byte-identical a86 fix, SPEC312b5607/BINDINGa1d1e485/inventoryffbc/outputc9d8/calibration6c49 exact. Own prewritten alpha6 reproduction: **556 statistic/coverage fields EXACT**, 504 original behaviour/readout identity-pointer/code joins,168 literal original calibration field+acquisition/pointer/base/dose/control maps,10 original seals135 member checks exact. Original336judgments=333known+3terminalmissing retained. First reviewer comparison flagged terminal-vs-unrun counts because raw code null was temporarily represented as unrun None; corrected normalization converts ONLY verified original UNPARSEABLE null dispositions to the terminal sentinel, without changing any source, score or missing denominator. All comparisons then exact. No author real mapper/input/analyze/run/guard invoked.

**Pair-logit preference** steered84/84 Wilson[.9562667347,1], random42/84[.3954375004,.6045624996]; all original42 alpha4 flippers retained,42 newly flipped,0known dropouts/0unknown alpha6. On SAME newly-flipped42, old44=40/40 observed Wilson[.9123754607,1],2terminalmissing; planned42 bounds40/42=.9523809524 to1 (no imputation in primary). Fixed original42 old44=4/42=.0952380952[.0376616388,.2206539523], new1/42, dual0, neither37/42. Whole84 old44=44/82 observed,1new,0dual,37neither,2missing. Random uses the identical cohorts, all categorical rates/coverage match. References remain E128/E109 alpha8 complement42/42, not original E10441/42+1neither; no bank swap or rejudge.

Pattern is descriptively consistent with item/cohort differences in this selected set; no registered numerical near/equivalence test, intrinsic item trait, dose-causal or confirmatory promotion. Pair-logit preference is NOT demonstrated full-answer behaviour: literal original3-token greedy new=0/84steered,3/84random, all known. No longer-token replacement/replay. Baseline median672 individual unsteered norms80.6719153842; actualalpha6 composed direction/residual median steered1.6735672164,random1.6735672189. Historicalalpha2/4/8 steered ratios.5578557388/1.1157114776/2.2314229552 are scalar arithmetic from original dose6 direction, not extra captures; eight sites counted once/item, repeated random norms checked at originalrtol1e-5/atol1e-6. This is not a universal small-intervention claim.

Chronology: originalfirstnative03:21:51.480573CET after six-only source d94203:15:45, but final acquisition-ID correction a86 actual06:19:01 and complete SPEC normalization06:32:41 are POSTACQUISITION/pre-scientific-run custody, never preacquisition certification. Exactsource2fc actual06:20:18<localguard06:36:16.047934<RESULTS.448125<seal.448610<publication06:37:43CET. Guard is claimed before cohort/calibration/inputs in this adapter; clock is recorded, earlier retained/discarded history remains unverified. Narrow RQclearance536 was published before invocation per owner receipt. OriginalANALYSIS_ONCE CONSUMED NEVERreset/replay. Final scientific review CLOSED; no new calls/ledger action/raw export.

<!-- RQ_REPRO_E135_REAL_V1 -->
```python
import importlib.util,json,datetime,subprocess,re
from pathlib import Path
import numpy as np

def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
q=load('q','/tmp/rq_prospective_reproductions.py');pre=load('pre','/tmp/rq_e135_deviation1_prewrite.py')
root=Path.cwd();actual=root.parent/'wt-wmech/cache/g_agreement/understand/e135/analysis_once';pub=root/'results/g_agreement/understand/e135/analysis';digest='717df78053b3fa77342ded7166535fd8d3a878e7cba2e33fa5f78289cb6dc5f4'
seen={};checks=0

def seal(p,h):
 global checks
 p=Path(p);assert q.sha(p)==h
 s=q.read_json(p)
 if str(p)not in seen:
  for f,v in s['files'].items():assert q.sha(p.parent/f)==v;checks+=1
  seen[str(p)]=h
 return s
meta=seal(actual/'ANALYSIS_SEAL.json',digest);assert q.sha(pub/'ANALYSIS_SEAL.json')==digest and q.sha(pub/'RESULTS.json')==q.sha(actual/'RESULTS.json');assert meta['status']=='COMPLETE_ONCE'
spec=q.read_json(actual/'BINDING.json');assert q.sha(actual/'BINDING.json')=='a1d1e485b5603f9888372eca1498bcdd74f93dc118b1632253443c786406cf01'
ims=seal(spec['inventory_seal'],spec['inventory_sha256']);oms=seal(spec['output_seal'],spec['output_sha256']);cms=seal(spec['calibration_seal'],spec['calibration_sha256'])
assert oms['experiment']=='E135' and oms['status']=='COMPLETE' and oms['new_doses']==[6] and oms['layers']==[44,52] and oms['redacted_count']==0
assert oms['original_source_input_sha256']=='381b58bde8ab7031e7a1de07bec1afe05655010a815e61a1a84c3b689c1c8047'
assert oms['inventory_sha256']==cms['inventory_sha256']==spec['inventory_sha256']
for m in [oms,cms]:
 for v in m['source_seals']:seal(v['seal'],v['sha256'])
src=q.Sources(oms['source_seals']);calref=q.Sources(cms['source_seals']);ip=Path(spec['inventory_seal']).parent;op=Path(spec['output_seal']).parent;cp=Path(spec['calibration_seal']).parent
items=q.read_json(ip/'INVENTORY.json');grid={x['item_id']:x for x in q.read_json(op/'MEASUREMENTS.json')};assert len(items)==84 and set(grid)=={x['item_id']for x in items}
refspec=q.read_json(spec['e128_spec']);refs=q.normalize128(refspec);by={x['id']:x for x in refs};assert set(by)==set(grid)
candidate=seal(spec['candidate_seal'],spec['candidate_sha256']);labels={x['original_base_id']:x for x in q.read_json(Path(spec['candidate_seal']).parent/'LABELS.PRIVATE.json')};assert set(labels)==set(grid)
normalized=[];joins=0;missing=0;greed={c:[]for c in ('steered','random')}
for it in items:
 i=it['item_id'];assert it['old_value']==by[i]['old'] and it['new_value']==by[i]['new'];ds={}
 assert set(grid[i]['doses'])=={'6'}
 for c,z in grid[i]['doses']['6'].items():
  b=z['behaviour'];ident=src.ref(b['identity']);raw=src.ref(b['record']);assert ident['item_id']==i and ident['condition']==c and ident['dose']==6 and ident['raw_id']==raw['id'];joins+=1
  assert ident['classifier_sha256']==oms['behaviour_classifier_sha256'];assert raw['greedy_max_new_tokens']==3 and len(raw['token_ids'])<=3
  # Identical literal frozen matcher, independently expressed (no alternative parser).
  matches=[name for name in ('old','new')if re.search(r'(?<!\w)'+re.escape(labels[i][name+'_value'])+r'(?!\w)',raw['text'],flags=re.I)]
  greed[c].append(None if raw is None else int(matches==['new']))
  codes={}
  for l,cell in z['oracle'].items():
   ii=src.ref(cell['identity']);code=src.ref(cell['code']);text=src.ref(cell['text'])
   assert ii['item_id']==i and ii['row']=='fact_recall'and ii['condition']==c and ii['layer']==int(l)and ii['dose']==6 and ii['reader']=='oracle'
   if code is None:
    p=cell['code'];tr=src.ref(dict(p,keys=p['keys'][:-1]));assert p['keys'][-1]=='code'and tr['id']==ii['judgment_id']and tr['status']=='UNPARSEABLE';missing+=1
   else:
    assert code['id']==ii['judgment_id'] and isinstance(code['values'],list)and set(code['values'])<={'A','B'}
    assert code['category']in ['states_value','names_property_without_value','exhibits','silent'];assert bool(code['values'])==(code['category']=='states_value')
    evidence=code['evidence'];assert isinstance(text,str)and(isinstance(evidence,str))
   codes[l]=dict(id=ii['judgment_id'],category='UNPARSEABLE',values=[],evidence='') if code is None else code;joins+=1
  ds[c]=dict(raw=raw,code=codes)
 normalized.append(dict(id=i,old=it['old_value'],new=it['new_value'],doses={'6':ds}))
cal=q.read_json(cp/'CALIBRATION.json');cr=[]
assert cal['block']==40 and cal['positions']=='eight_before_read'and cal['unsteered']is True
for x in cal['cells']:
 ptr=x['source_ref'];raw=calref.ref(ptr);im=ptr['identity_mapping'];pm=calref.ref(im['pointer_ref']);acq=calref.ref(im['acquisition_ref'])
 assert im['pointer_ref']['member']=='ORIGINAL_POINTERS.PRIVATE.json'and im['acquisition_ref']['member']=='items.json'
 ps=calref.seals[im['pointer_ref']['seal_index']];assert ps['input_sha256']==oms['original_source_input_sha256'];assert cms['source_seals'][im['acquisition_ref']['seal_index']]['sha256']==ps['input_sha256']
 assert raw['id']==pm['id']==acq['id']and raw['base_id']==acq['base_id']and raw['alpha']==acq['alpha']==x['dose']==6 and raw['condition']==acq['condition']==x['condition']and pm['original_base_id']==x['item_id']and pm['scale']==.75
 assert set(ptr['field_mapping'])=={'dose','condition','natural_site_l2','composed_delta_l2','write_positions'}
 for target,key in ptr['field_mapping'].items():assert x[target]==raw[key]
 cr.append(dict(base_id=x['item_id'],alpha=x['dose'],condition=x['condition'],natural_site_l2=x['natural_site_l2'],positions=x['write_positions'],write_block=40,composed_delta_l2=x['composed_delta_l2']))
assert len(cr)==168
own=pre.deviation1(normalized,refs,cr);want=q.read_json(actual/'RESULTS.json');numeric=0

def rate(a,b):
 global numeric
 for k in ['k','planned_n','missing_n','estimate','Wilson95']:assert a[k]==b[k],(k,a[k],b[k]);numeric+=1
 assert a['known_n']==b['n'];numeric+=1

groups={'all84':'all84','own_flipped':'alpha6_flipped','fixed_alpha4_42':'alpha4_fixed42','alpha6_flipped_in_alpha4_cohort':'retained_alpha4_flippers','newly_flipped_alpha6':'newly_flipped_at6'}
for wn,on in groups.items():
 for c in ('steered','random'):
  for l in ('44','52'):
   a=own['groups'][on]['readouts'][c][l];b=want['doses']['6']['cohorts'][wn][c][l]
   assert b['planned_n']==own['groups'][on]['n']
   for key in ['terminal_unparseable_n','unrun_n']:assert a[key]==b[key];numeric+=1
   for key in ['old','new','dual','neither']:rate(a[key],b['rates'][key])
for c in ('steered','random'):
 rate(own['groups']['all84']['pair_flip_rate'][c],want['doses']['6']['flip_rates'][c]);rate(q.rate(greed[c]),want['doses']['6']['greedy_new_rates'][c])
a=own['calibration'];b=want['calibration'];assert a['baseline_median_L2']==b['median_unsteered_residual_l2'];assert a['n_items']==b['n_items']==84 and a['n_positions']==b['n_positions']==672
for dose in ('2','4','6','8'):
 for c in ('steered','random'):assert a['ratios'][dose][c]['median']==b['ratios'][dose][c];numeric+=1
 assert [a['ratios'][dose]['random'][side]for side in ('min','max')]==b['ratios'][dose]['random_item_ratio_range'];numeric+=1
assert want['descriptive']is True and want['confirmatory_rule']is None and want['new_calls']==0
s=dict(status='PASS',original_seals=len(seen),member_checks=checks,original_native_readout_joins=joins,calibration_literal_maps=len(cr),terminal_missing=missing,numeric_and_coverage_field_checks=numeric,cohorts={k:v['n']for k,v in own['groups'].items()},flip_rates=want['doses']['6']['flip_rates'],greedy_rates=want['doses']['6']['greedy_new_rates'],newly_flipped44=want['doses']['6']['cohorts']['newly_flipped_alpha6']['steered']['44'],fixed44=want['doses']['6']['cohorts']['fixed_alpha4_42']['steered']['44'],calibration=b)
Path('/tmp/rq_e135_real_summary.json').write_text(json.dumps(s,indent=2));print(json.dumps(s,indent=2))

```
<!-- /RQ_REPRO_E135_REAL_V1 -->


## DIRECT Guiv §248 C amendment1 PREWRITE READY — group comparisons and AUROC gain

Canonical0d76a2166 extends original C; prospective reviewer-only code below replaces no owner source and opens no real C quantities. SYNTHETIC PASS: uncertain/first6 cohort status, dual=old-presence, missing/zero-denominator displacement,5000seed0 pooled-item group bootstrap,5000 paired-held-out AUROC-gain bootstrap, exact .05/LB>0 boundaries, identical-model zero gain, one-class folds, held-out-extreme training-only scaling, and full84 synthetic both-target flow (explicit40draws only for end-to-end; kernels full5000). No production adapter/input/guard/model or real predictor/vector/margin data opened. Existing C source ac4 is historical pre-amendment, NOT endorsed as amended implementation.

Plan: exact original84 easy=alpha4true, resistant=known2false/4false/6true; other/unknown earlier-dose cases explicitly outside named contrast, never silently resistant or8. Verify actual E135 cohort and original2/4/6 membership on sealed arrival; no new selection. Old-fact presence includes dual, missing separate. Per group cleanE127no-prefixold44 and randomE1284/E1356/E128-E109REFERENCE8old44: numerator/planned/known/missing/Wilson. Targeted rates beside, paired target-minus-random same-item contrasts within group, no cross-cohort subtraction. Continuous answer margin and displacement44 at8(+6 if actually captured): pergroup mean/median/coverage, resistant-minus-easy item-bootstrap differences. Geometry uses literal same-item/read-token/layer44 ordered vectors, norm(hsteer−hclean)/norm(hclean); missing or exactzero baseline NE/no epsilon/clipping/invented6vectors. Rawsigns/order/token/sourcebank and clean probe's original-old orientation must be bound before use.

Two outcomes separately: resistant-vs-easy and old44-at8. Fixed L2logisticC1/lbfgs2000seed0; scaler fitted only on training fold; finite observed cases, no tuning/AUC inversion. Every gain's baseline/augmented model uses identical items and paired held-out predictions. Primary probe-added contrast answer+cleanprobe minus answer-only on common answer/probe cases; geometry-adjusted joint minus answer+geometry separately, plus each predictor and full joint on common three-feature cases. Missing geometry cannot remove items from primary probe-added comparison. Paired item bootstrap5000seed0 of already held-out scores with point/conditional-defined percentile CI/valid+undefined counts; never independent bootstrap of the two AUCs. No failed fold repaired; insufficientclasses NE.

This bootstrap-of-fixed-OOF-scores convention is a prospective reviewer interpretation, NOT specified verbatim by amendment: compare against committed owner implementation before real outputs; if owner intends model-refitting bootstrap, reconcile before opening. No cost-saving substitution silently asserted equivalent. Amend1 asks both outcome tests but does not identify a single governing target for its global deck phrase: report both tests explicitly, no cherry-picking/global promotion inferred. Per target pointgain>=.05 AND conditionalCI lower>0 implements the stated threshold (zero lower fails); unavailablegain/CI NE, not automaticfailure-caption. Passingtarget: “the early representation predicts staleness”; failedtarget: “susceptibility to steering predicts it”, labelled exploratory/posthoc, no causal wording. E133fullscience and original Bmargin/vector delivery/fullTABLE_POINTERS/genuine dependencies remain prerequisites; source/prewrite alone not real-executionGO.

<!-- RQ_REPRO_248C_AMEND1_V1 -->
```python
"""R-Q §248C amendment1 prospective reproduction. SYNTHETIC ONLY until sealed bindings.
No author adapter/loader/guard; no scientific inputs or outputs read by this module.
Conventions to compare against future committed owner source, not new registration:
- old presence includes dual; resistant-minus-easy direction fixed;
- pooled item bootstrap (5000 seed0), conditional defined percentile CI + counts;
- LOO scaler/train only, C1/lbfgs/2000/seed0; bootstrap paired held-out scores,
  not re-fit/rescreen. Confirm this convention before any real C interpretation.
"""
import itertools,warnings,json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from common.stats import wilson
DRAWS=5000;SEED=0
FEATURES=('answer_margin','probe_clean_old44','displacement8')
CATS=('old','new','dual','neither',None)

def finite(v):return v is not None and np.isfinite(v)
def binary(v):return type(v)in(int,bool)and v in(0,1)
def old(code):
 if code not in CATS:raise ValueError('sealed old/new/dual/neither/None only')
 return None if code is None else int(code in('old','dual'))

def group(r):
 f=r['flips'];assert set(f)=={'2','4','6','8'} and all(v is None or type(v)is bool for v in f.values())
 if f['4']is True:return 'easy'
 if f['2']is False and f['4']is False and f['6']is True:return 'resistant'
 return None # unknown, earlier2 flip, never6, or other nonregistered partition: audit, no force

def displacement(clean,steered):
 if clean is None or steered is None:return None
 a=np.asarray(clean,float);b=np.asarray(steered,float)
 assert a.ndim==1 and a.shape==b.shape and len(a)and np.isfinite(a).all()and np.isfinite(b).all()
 den=float(np.linalg.norm(a))
 return None if den==0 else float(np.linalg.norm(b-a)/den) # no epsilon/clipping

def rate(values):
 assert all(v is None or binary(v)for v in values)
 obs=[v for v in values if v is not None];k=sum(obs);n=len(obs)
 return dict(planned_n=len(values),known_n=n,missing_n=len(values)-n,k=k,estimate=None if not n else k/n,Wilson95=None if not n else list(wilson(k,n)[1:]))

def interval(values,point,total):
 vals=np.asarray(values,float);valid=vals[np.isfinite(vals)]
 return dict(estimate=point,CI95=None if not len(valid)else np.quantile(valid,[.025,.975]).tolist(),valid_bootstraps=len(valid),undefined_bootstraps=total-len(valid),CI_definition='percentile conditional on defined item draws; no undefined draw replaced')

def group_comparison(rows,field,kind='rate',draws=DRAWS):
 # Resample whole items with group+quantity together; retained group labels never refit.
 assert kind in('rate','continuous')
 gs=np.array([group(r)for r in rows],object);vals=[r[field]for r in rows]
 assert all(v is None or finite(v)for v in vals)
 if kind=='rate':assert all(v is None or binary(v)for v in vals)
 v=np.array([np.nan if x is None else x for x in vals],float)
 out={}
 for g in ('easy','resistant'):
  x=v[gs==g];z=x[np.isfinite(x)]
  out[g]=rate([None if not np.isfinite(a)else int(a)for a in x])if kind=='rate'else dict(planned_n=len(x),known_n=len(z),missing_n=len(x)-len(z),mean=None if not len(z)else float(z.mean()),median=None if not len(z)else float(np.median(z)))
 stats=('mean',)if kind=='rate'else('mean','median')
 for stat in stats:
  fn=np.mean if stat=='mean'else np.median
  def difference(ids):
   g=gs[ids];x=v[ids];a=x[(g=='easy')&np.isfinite(x)];b=x[(g=='resistant')&np.isfinite(x)]
   return np.nan if not len(a)or not len(b)else float(fn(b)-fn(a))
  p=difference(np.arange(len(rows)));ix=np.random.default_rng(SEED).integers(0,len(rows),(draws,len(rows)))if rows else np.empty((draws,0),int)
  bs=[difference(z)for z in ix]
  out['resistant_minus_easy_'+stat]=interval(bs,None if not np.isfinite(p)else p,draws)
 out['excluded_group_n']=int(sum(x is None for x in gs))
 return out

def auc(y,score):
 y=np.asarray(y);s=np.asarray(score,float);a=s[y==1];b=s[y==0]
 return None if not len(a)or not len(b)else float(np.mean((a[:,None]>b).astype(float)+.5*(a[:,None]==b)))

def loo_scores(x,y):
 x=np.asarray(x,float);y=np.asarray(y,int)
 assert x.ndim==2 and len(x)==len(y)and np.isfinite(x).all()and all(binary(v.item())for v in y)
 if len(y)<3 or len(set(y))<2:return None,'insufficient observed classes'
 pred=[]
 for i in range(len(y)):
  train=np.arange(len(y))!=i
  if len(set(y[train]))<2:return None,'one-class training fold'
  mu=x[train].mean(0);sd=x[train].std(0);sd[sd==0]=1
  fit=LogisticRegression(C=1.,solver='lbfgs',max_iter=2000,random_state=0)
  with warnings.catch_warnings():
   warnings.simplefilter('error',ConvergenceWarning);fit.fit((x[train]-mu)/sd,y[train])
  pred.append(float(fit.decision_function((x[i:i+1]-mu)/sd)[0]))
 return np.asarray(pred),None

def predictive_comparison(rows,target,feature_sets,draws=DRAWS):
 # ALL compared models use SAME complete cases, never gains on different samples.
 fields=sorted({f for fs in feature_sets.values()for f in fs});keep=[r for r in rows if binary(r[target])and all(finite(r[f])for f in fields)]
 y=np.array([r[target]for r in keep],int);out=dict(planned_n=len(rows),known_n=len(keep),missing_n=len(rows)-len(keep),feature_sets={k:list(v)for k,v in feature_sets.items()},models={},gains={})
 scores={};rng=np.random.default_rng(SEED);ix=rng.integers(0,len(y),(draws,len(y)))if len(y)else np.empty((draws,0),int)
 for name,fs in feature_sets.items():
  x=np.array([[r[f]for f in fs]for r in keep],float).reshape(len(keep),len(fs));s,why=loo_scores(x,y)
  if s is None:out['models'][name]=dict(estimate=None,CI95=None,valid_bootstraps=0,undefined_bootstraps=draws,reason=why);continue
  scores[name]=s;p=auc(y,s);bs=[auc(y[z],s[z])for z in ix];out['models'][name]=interval([np.nan if v is None else v for v in bs],p,draws)
 for alt,base in [('answer_probe','answer'),('joint','answer_geometry')]:
  if alt not in feature_sets or base not in feature_sets:continue
  if alt not in scores or base not in scores:
   out['gains'][alt+'_minus_'+base]=dict(estimate=None,CI95=None,valid_bootstraps=0,undefined_bootstraps=draws);continue
  point=auc(y,scores[alt])-auc(y,scores[base]);vals=[]
  for z in ix:
   a=auc(y[z],scores[alt][z]);b=auc(y[z],scores[base][z]);vals.append(np.nan if a is None or b is None else a-b)
  out['gains'][alt+'_minus_'+base]=interval(vals,point,draws)
 out['bootstrap']='paired item bootstrap of fixed out-of-fold predictions; no model refit in bootstrap'
 return out

def reading(gain):
 if gain['estimate']is None or gain['CI95']is None:return dict(status='NOT EVALUABLE',phrase=None)
 met=gain['estimate']>=.05 and gain['CI95'][0]>0
 return dict(status='MET'if met else'NOT MET',phrase='the early representation predicts staleness'if met else'susceptibility to steering predicts it',causal=False)

def analyze(rows,draws=DRAWS):
 assert len(rows)==84 and len({r['id']for r in rows})==84
 rows=sorted(rows,key=lambda r:r['id']);rr=[]
 for original in rows:
  r=dict(original);g=group(r);r['resistant']=None if g is None else int(g=='resistant');r['old8']=old(r['steered8_old44']);r['clean_old44']=old(r['clean_old44'])
  for d in ('4','6','8'):
   r['random'+d+'_old44']=old(r['random'+d+'_old44'])
   r['steered'+d+'_old44']=old(original.get('steered'+d+'_old44'))
   a=r['steered'+d+'_old44'];b=r['random'+d+'_old44'];r['target_minus_random'+d]=None if a is None or b is None else a-b
  rr.append(r)
 out=dict(status='EXPLORATORY_POST_HOC',groups={g:sum(group(r)==g for r in rr)for g in ('easy','resistant',None)},comparisons={})
 for f in ('clean_old44','random4_old44','random6_old44','random8_old44','steered4_old44','steered6_old44','steered8_old44'):out['comparisons'][f]=group_comparison(rr,f,'rate',draws)
 # Paired T-R item contrasts, separately within each fixed group; missing remains paired-missing.
 out['direction_specificity']={}
 for d in ('4','6','8'):
  out['direction_specificity'][d]={}
  for g in ('easy','resistant'):
   vals=[r['target_minus_random'+d]for r in rr if group(r)==g];a=np.array([np.nan if v is None else v for v in vals],float)
   ix=np.random.default_rng(SEED).integers(0,len(a),(draws,len(a)))if len(a)else np.empty((draws,0),int);bs=[]
   for z in ix:
    v=a[z];v=v[np.isfinite(v)];bs.append(np.nan if not len(v)else float(v.mean()))
   point=None if not np.isfinite(a).any()else float(np.nanmean(a))
   out['direction_specificity'][d][g]=dict(planned_n=len(a),paired_known_n=int(np.isfinite(a).sum()),paired_missing_n=int((~np.isfinite(a)).sum()),**interval(bs,point,draws))
 for f in FEATURES+('displacement6',):out['comparisons'][f]=group_comparison(rr,f,'continuous',draws)
 out['outcomes']={}
 for target in ('resistant','old8'):
  # Probe-added test on answer+probe complete cases; geometry missing cannot change its population.
  primary=predictive_comparison(rr,target,{'answer':('answer_margin',),'probe':('probe_clean_old44',),'answer_probe':('answer_margin','probe_clean_old44')},draws)
  geometry=predictive_comparison(rr,target,{'answer':('answer_margin',),'probe':('probe_clean_old44',),'geometry':('displacement8',),'answer_geometry':('answer_margin','displacement8'),'joint':FEATURES},draws)
  out['outcomes'][target]=dict(primary=primary,geometry=geometry,reading=reading(primary['gains']['answer_probe_minus_answer']))
 # Two target-specific readings; no cherry-picking one to grant a global caption.
 out['global_caption_status']='UNSPECIFIED: amendment does not specify combining its two target-specific gain tests'
 return out

def synthetic_tests():
 assert group(dict(flips=dict(zip(('2','4','6','8'),(False,True,True,True)))))=='easy'
 assert group(dict(flips=dict(zip(('2','4','6','8'),(False,False,True,True)))))=='resistant'
 for seq in [(None,False,True,True),(True,False,True,True),(False,None,True,True),(False,False,None,True),(False,False,False,True)]:assert group(dict(flips=dict(zip(('2','4','6','8'),seq))))is None
 assert old('dual')==1 and old('neither')==0 and old(None)is None
 assert displacement([3,4],[6,8])==1 and displacement([0,0],[1,1])is None and displacement(None,[1,1])is None
 rows=[dict(flips=dict(zip(('2','4','6','8'),(False,i<4,True,True))),v=int(i>=4))for i in range(8)]
 z=group_comparison(rows,'v',draws=DRAWS);assert z['easy']['k']==0 and z['resistant']['k']==4 and z['resistant_minus_easy_mean']['estimate']==1 and z['resistant_minus_easy_mean']['CI95']==[1,1]and z['resistant_minus_easy_mean']['undefined_bootstraps']>0
 rows[0]['v']=None;z=group_comparison(rows,'v',draws=100);assert z['easy']['known_n']==3 and z['easy']['missing_n']==1
 assert auc([0,1],[1,1])==.5 and auc([0,1],[2,1])==0 and auc([1,1],[0,1])is None
 assert loo_scores(np.arange(3).reshape(-1,1),[0,0,1])[0]is None
 # Synthetic prediction matrix, all models paired on identical complete cases.
 rs=[dict(y=int(i%2),a=float(i%3),p=float(i%2),g=float(i),id=str(i))for i in range(16)]+[dict(y=1,a=None,p=1.,g=0.,id='missing')]
 z=predictive_comparison(rs,'y',{'answer':('a',),'probe':('p',),'answer_probe':('a','p')});assert z['known_n']==16 and z['missing_n']==1
 assert z['models']['answer_probe']['estimate']==1 and z['gains']['answer_probe_minus_answer']['estimate']>=.05
 assert reading(z['gains']['answer_probe_minus_answer'])['status']=='MET'
 assert reading(dict(estimate=.05,CI95=[0,.1]))['status']=='NOT MET'
 assert reading(dict(estimate=.049,CI95=[.01,.1]))['status']=='NOT MET'
 assert reading(dict(estimate=.05,CI95=[.0001,.1]))['status']=='MET'
 assert reading(dict(estimate=None,CI95=None))['status']=='NOT EVALUABLE'
 # Identical feature produces zero gain under the paired bootstrap, including ties.
 rr=[dict(r,p=r['a'])for r in rs]
 z=predictive_comparison(rr,'y',{'answer':('a',),'answer_probe':('a',)},draws=100);assert z['gains']['answer_probe_minus_answer']['estimate']==0 and z['gains']['answer_probe_minus_answer']['CI95']==[0,0]
 # An extreme held-out covariate must never enter its own scaler training statistics.
 x=np.array([[float(i),float(i%3)]for i in range(12)]);y=np.array([i%2 for i in range(12)]);x[0,0]=1e8
 preds,_=loo_scores(x,y);train=np.arange(12)!=0;mu=x[train].mean(0);sd=x[train].std(0);sd[sd==0]=1
 m=LogisticRegression(C=1.,solver='lbfgs',max_iter=2000,random_state=0).fit((x[train]-mu)/sd,y[train]);assert preds[0]==float(m.decision_function((x[:1]-mu)/sd)[0])
 rows=[]
 for i in range(84):
  rows.append(dict(id=f'synthetic-{i:02d}',flips={'2':False,'4':i<42,'6':True,'8':True},clean_old44=None if i%17==0 else('dual'if i%7==0 else'old'if i%2 else'neither'),random4_old44='old',random6_old44=None if i%19==0 else'old',random8_old44='dual'if i%3==0 else'neither',steered4_old44='neither'if i<42 else'old',steered6_old44='old',steered8_old44=None if i%13==0 else'old'if i%2 else'neither',answer_margin=float(i%11),probe_clean_old44=float(i%2),displacement8=None if i%23==0 else float(i%5)/10,displacement6=None))
 z=analyze(rows,draws=40) # end-to-end only shortened; full5000 kernels above
 assert z['groups']=={'easy':42,'resistant':42,None:0}
 assert z['comparisons']['displacement6']['resistant_minus_easy_mean']['undefined_bootstraps']==40
 assert z['direction_specificity']['4']['easy']['estimate']==-1
 assert z['direction_specificity']['4']['resistant']['estimate']==0
 for target in ('resistant','old8'):
  assert z['outcomes'][target]['primary']['known_n']>z['outcomes'][target]['geometry']['known_n']
  assert set(z['outcomes'][target]['geometry']['models'])=={'answer','probe','geometry','answer_geometry','joint'}
 print('PASS synthetic: cohort unknown/first6 exclusions; presence+dual+missing; geometryzero/missing; full5000 group/pairedgain bootstrap; exact gate boundaries; zero-gain identical models; one-class LOO; training-only scaling')
if __name__=='__main__':synthetic_tests()

```
<!-- /RQ_REPRO_248C_AMEND1_V1 -->


## E133 MAIN scientific numerical review COMPLETE — R-NL1 NOT MET / falsifier NOT MET

Published3e57b5c1f/originale6f12addf1bdb63fb02deafffe7b602835ec5efd02e326470a7aaf9b5fe752d0; sourcea9b02170e/finalSPEC0c077eb0 output00406fff/inventoryf037 exact. Own already-prewritten reproduction: **260 statistic/coverage fields EXACT**, all21 matched-pair patch medians/2000seed20261027 CIs, all primary+onehop reader categories/Wilson intervals (dual separate), verdicts EXACT. All990 original per-pair ratio audit rows match original CPU PER_PAIR.PRIVATE hash5e548af1/mode600; original four-member analysis seal retained, never stripped to public. SeparatePUBLICATION_SEAL96c19f83 exact public copies/reference. Eight original/public/role seals821memberchecks;540 literal nativeOracleINDEX/layer/member/text→code-or-terminal-null identity joins;1980 literal patchINDEX/array/site/control/common-axis joins;180 originalcapture/CPUrole/orderedascendingcandidate-token/currentindex/previous identities exact. Both own/other and patched use SAME original ordered recipient contrast selected indices; never current-vs-previous substitution or all-contrast average. No zero gaps(minabs5.6874998808)/clipping/drop. No reviewer production adapter/input/run/guard or probe fit. Original8001 probe seal/nestedresult unchanged reused; closed18fits not repeated.

Own=worker **R-NL1 NOT MET, falsifier NOT MET**,50MHpairs (exact eligibility boundary),40onehop descriptive. Previous44=3/82=.0365853659 Wilson[.0125193462,.1021290294],current44=7/82=.0853658537,current60=50/95=.5263157895[.4268517068,.6237342813]. MainR44=.0109889903[.0060829499,.0153846011];R52=.2641370843[.2412060577,.2907389229];R56=.3200877188[.2883435523,.3461773292];R60=.7435457349[.7195397290,.7664974957] DESCRIPTIVE not substitute for registered52/56. BothcontrolmediansALL5<=.15(max.0191769197). Random patch actual norm differences from read-replacement delta are not bitwisezero: maximum relative.0019086278(.190863%); native measuredfloatcast discrepancy disclosed, no rescale/exclusion/newtolerance convention. Earlier-token position<read−8/unscaled identity and nativepositions exact; read/random atread, originalrandomseed/normmatchedflag exact/no upstreamhook.

Missing73 originalterminalnulls preserved: MH44/52/60=18/5/5,onehop20/14/11. No new observabilitygate orcompletecasefilter. Registered failures robust to all missing-value assignments: previous44 upper(3+18)/100=.21<.30,current60 upper(50+5)/100=.55<.70;falsifiercurrent44 upper(7+18)/100=.25<.70 and definedR44<.50. This is failure to meet the registered natural-staleness+mechanism reading and its positive falsifier; neither universalabsence nor “stateformed/readableby44” asserted. Block60 restoration alone cannot rescue the52/56registered gate. Preference **NOT MEASURED** for all180 members, no candidate masses/no text-preferenceagreement; unchanged32token literalparsertext rates/abstention counts exact. Synthetic E133 separate from closedbAbI measurementNE/no pooling.

Source actuala9COMMITTER06:38:21CET and narrowRQclearance63e06:41:56 precede localmain guard06:47:48.712674<FIRST_OPENING.712755<RESULTS06:47:49.272376<seal.280097<publication06:49:33. Originalnativefirst02:30:31CET PRECEDES laterphase/episode/probe/preference-not-measured updates; finalnormalization/source review is pre-main-analysis, notpreacquisition/firsteverhistorycertification. Owner FIRST_OPENING explicitly operator clock beforefirstoutcomejoin; earlierfailed/discardedhistory unverified. OriginalmainANALYSIS_ONCE CONSUMED NEVERreset/rerun; originalPROBES_ONCE immutable/no refit. Scientific review CLOSED.

<!-- RQ_REPRO_E133_MAIN_REAL_V1 -->
```python
"""R-Q independent sealed E133 main reproduction: no author adapter/run/guard or probe refit."""
import importlib.util,json,hashlib,datetime,subprocess,re
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('q','/tmp/rq_prospective_reproductions.py');q=importlib.util.module_from_spec(s);s.loader.exec_module(q)
R=Path.cwd();pub=R/'results/g_agreement/understand/e133/analysis/sealed_main';actual=R.parent/'wt-internals-b/cache/g_agreement/understand/e133/analysis_once';digest='e6f12addf1bdb63fb02deafffe7b602835ec5efd02e326470a7aaf9b5fe752d0';seen={};checks=0

def seal(p,h=None):
 global checks
 p=Path(p)
 if h:assert q.sha(p)==h
 if str(p)not in seen:
  z=q.read_json(p)
  for f,d in z['files'].items():assert q.sha(p.parent/f)==d;checks+=1
  seen[str(p)]=z
 return seen[str(p)]
m=seal(actual/'ANALYSIS_SEAL.json',digest);assert q.sha(pub/'ORIGINAL_ANALYSIS_SEAL.json')==digest
ps=seal(pub/'PUBLICATION_SEAL.json');assert ps['original_analysis_sha256']==digest
for f in ['RESULTS.json','BINDING.json','FIRST_OPENING.json']:assert (actual/f).read_bytes()==(pub/f).read_bytes()
assert (actual/'PER_PAIR.PRIVATE.json').stat().st_mode&0o777==0o600
spec=q.read_json(actual/'BINDING.json');want=q.read_json(actual/'RESULTS.json');iv=seal(spec['inventory_seal'],spec['inventory_sha256']);om=seal(spec['output_seal'],spec['output_sha256']);assert om['experiment']=='E133'and om['status']=='COMPLETE'and om['no_steer']is True
for z in om['source_seals']:seal(z['seal'],z['sha256'])
probe=actual.parent/'probes_once';assert q.sha(probe/'ANALYSIS_SEAL.json')==om['probe_seal']['sha256']=='8001a013014d4960b5eb768bfc7808b85252241db4aa92d4f6c556c4acb0aad6'
assert want['probes_descriptive']==q.read_json(probe/'PROBE_RESULTS.json')
# Reuse only byte identity of the already independently closed probe result; no fit.
pairs=q.normalize133(spec);own=q.e133(pairs);assert own['R_NL1']==want['R_NL1']and own['falsifier']==want['falsifier'];n=0
for kind,z in own['groups'].items():
 w=want['groups'][kind];assert z['n_pairs']==w['n_pairs'];n+=1
 for l,rs in z['reads'].items():
  for name,a in rs.items():
   b=w['reader_rates'][l][name]
   for key in ['k','planned_n','missing_n','estimate','Wilson95']:assert a[key]==b[key],(kind,l,name,key);n+=1
   assert a['known_n']==b['n'];n+=1
 for block,cs in z['patches'].items():
  for c,a in cs.items():
   b=w['patches'][block][c]
   for key in ['estimate','CI95','n_pairs','n_defined']:assert a[key]==b[key],(kind,block,c,key);n+=1
# Independent literal donor/site/norm/common-axis and native INDEX checks.
inv=q.read_json(Path(spec['inventory_seal']).parent/'PAIRS.PRIVATE.json');grid={z['pair_id']:z for z in q.read_json(Path(spec['output_seal']).parent/'MEASUREMENTS.json')};src=q.Sources(om['source_seals'])
native=Path(om['source_seals'][1]['seal']).parent/'main_synthetic';index=q.read_json(native/'INDEX.json');idx={(x['id'],x['kind'],x.get('block'),x.get('control')):x for x in index};cache={}
rolebase=R.parent/'outputs/e133-screen-adapted-v3/synthetic/cpu_only';rolemeta=seal(rolebase/'ROLE_SEAL.json');roles={x['id']:x for x in q.read_json(rolebase/'ROLES.PRIVATE.json')};assert rolemeta['input_sha256']==seen[str(Path(om['source_seals'][1]['seal']))]['input_sha256']
readjoins=patchjoins=0;missing=0;missingby={};norel=[];greedy={};private=[];gaps=[];norm_rel=[];native_patch_checks=0
for p in inv:
 ms=grid[p['pair_id']]['members'];assert len(ms)==2;mscores=[];patchmap={}
 for j,(lab,z)in enumerate(zip(p['members'],ms)):
  assert 'preference'not in z
  gi=src.ref(z['greedy']['identity']);raw=src.ref(z['greedy']['record']);assert gi['raw_id']==raw['id']==lab['item_id']and raw['pair_id']==p['pair_id']and raw['member']==j and raw['family']==p['kind']and raw['condition']=='unhooked'
  rr=roles[raw['id']];assert rr['pair_id']==p['pair_id']and rr['member']==j and rr['family']==p['kind']and rr['current_recipient_index']==lab['current_recipient_index']and rr['previous']==lab['previous'];assert rr['recipient_strings'][lab['current_recipient_index']]==lab['current']
  assert raw['candidate_ids']==[[[v]for v in rr['ascending_candidate_ids']]];assert raw['greedy_max_new_tokens']==32 and len(raw['token_ids'])<=32
  cell=z['own'];ii=src.ref(cell['identity']);score=src.ref(cell['raw']);assert ii['raw_id']==score['id']==raw['id']and score['candidate_ids']==raw['candidate_ids']and ii['contrast_sha256']==p['recipient_contrast_sha256']and ii['pair_count']==p['pair_count']
  selected=np.asarray(score['pair_logprobs'],float)[p['recipient_pair_indices']];assert selected.shape==(p['pair_count'],2);mscores.append(float((selected[:,0]-selected[:,1]).mean()))
  cells=[]
  for l in (44,52,60):
   cell=z['readouts'][str(l)];ii=src.ref(cell['identity']);code=src.ref(cell['code']);text=src.ref(cell['text']);assert ii['item_id']==raw['id']and ii['judgment_id']
   oracle_index=idx[raw['id'],'oracle',l,None];assert cell['text']['member']=='main_synthetic/'+oracle_index['member']and cell['text']['keys']==[oracle_index['record'],'text']
   if code is None:
    ptr=cell['code'];tr=src.ref(dict(ptr,keys=ptr['keys'][:-1]));assert tr['id']==ii['judgment_id']and tr['status']=='UNPARSEABLE';missing+=1;missingby[p['kind'],l]=missingby.get((p['kind'],l),0)+1
   else:
    assert code['category']in ('states_value','names_property_without_value','exhibits','silent');assert len(code['values'])==len(set(code['values']))and set(code['values'])<=set(p['value_map']);assert bool(code['values'])==(code['category']=='states_value')
    assert code['evidence']in text and ((not code['evidence']and not code['values'])if code['category']=='silent'else bool(code['evidence']))
   readjoins+=1
  for block,controls in z['patches'].items():
   for c,cell in controls.items():
    ii=src.ref(cell['identity']);a=src.ref(cell['raw']);assert ii['raw_id']==a['id']and ii['donor_pair_id']==p['pair_id']and ii['donor_member']==1-j and ii['patch_binding_verified']is True
    assert ii['contrast_sha256']==p['recipient_contrast_sha256']and ii['pair_count']==p['pair_count'];assert a['candidate_ids']==raw['candidate_ids'];assert a['block']==int(block)
    ix=idx[a['id'],'patch',int(block),a['control']];assert cell['raw']['member']=='main_synthetic/'+ix['member']and cell['raw']['keys']==[ix['record']]
    patch=a['patch'];assert patch['block']==int(block)and patch['upstream_hook_installed']is False
    if c=='earlier_token':assert a['control']=='earlier'and patch['position']==ii['position']<patch['read_position']-8 and ii['unscaled_residual_replacement']is True
    else:assert patch['position']==ii['position']==patch['read_position']
    if c=='random_norm_matched':
     assert a['control']=='random'and ii['norm_matched']is True and type(ii['random_seed'])is int
     den=patch['reference_read_replacement_delta_norm'];assert den>0;norm_rel.append(abs(patch['delta_norm']/den-1))
    elif c=='read_token':assert a['control']=='read'and ii['unscaled_residual_replacement']is True
    axy=np.asarray(a['pair_logprobs'],float)[p['recipient_pair_indices']];patchmap[j,int(block),c]=float((axy[:,0]-axy[:,1]).mean());patchjoins+=1
  names=[p['members'][0]['current'],p['members'][1]['current'],lab['previous']];hits=[x for x in names if re.search(r'(?<!\w)'+re.escape(x)+r'(?!\w)',raw['text'],re.I)];answer=hits[0]if len(hits)==1 else None
  greedy.setdefault(p['kind'],[]).append(dict(answer=answer,current=lab['current'],previous=lab['previous']))
 gaps.extend([abs(mscores[1]-mscores[0])]*2)
 for b in ((44,52)if p['kind']=='one_hop'else q.BLOCKS):
  for c in q.CONTROLS:
   ratios=[q.pair_ratio(mscores[j],mscores[1-j],patchmap[j,b,c])for j in (0,1)]
   private.append(dict(pair_id=p['pair_id'],kind=p['kind'],source_episode_id=None,block=b,control=c,member_ratios=ratios,own_logodds=mscores,other_logodds=mscores[::-1],patched_logodds=[patchmap[j,b,c]for j in(0,1)]))
assert private==q.read_json(actual/'PER_PAIR.PRIVATE.json');assert missing==73
# Dual rates and text descriptives: independently from original codes/text.
for kind,w in want['groups'].items():
 ps=[p for p in inv if p['kind']==kind]
 for l in (44,52,60):
  vals=[]
  for p in ps:
   for lab,z in zip(p['members'],grid[p['pair_id']]['members']):
    code=src.ref(z['readouts'][str(l)]['code']);vs=set()if code is None else {p['value_map'][v]for v in code['values']};vals.append(None if code is None else int(lab['current']in vs and lab['previous']in vs))
  a=q.rate(vals);b=w['reader_rates'][str(l)]['dual_current_previous'];assert a['k']==b['k']and a['known_n']==b['n']and a['Wilson95']==b['Wilson95'];n+=3
 d=want['text_preference_descriptive'][kind];g=greedy[kind];assert d['preference_status']=='NOT MEASURED'and 'text_preference_agreement'not in d and d['candidate_mass_known_n']==0 and d['candidate_mass_quartiles']is None
 assert d['text_unclassified_n']==sum(z['answer']is None for z in g)
 for k in ('current','previous'):
  a=q.rate([None if z['answer']is None else int(z['answer']==z[k])for z in g]);b=d['text_'+k+'_rate'];assert a['estimate']==b['estimate']and a['Wilson95']==b['Wilson95']and a['k']==b['k'];n+=3
for p in inv:
 assert len({m['item_id']for m in p['members']})==2
# Preserve first-opening/once custody; no replay.
guard=actual.parent/'ANALYSIS_ONCE.json';opening=q.read_json(actual/'FIRST_OPENING.json');assert opening['guard_sha256']==q.sha(guard)and opening['output_sha256']==spec['output_sha256']
summary=dict(status='PASS',R_NL1=own['R_NL1'],falsifier=own['falsifier'],numeric_field_checks=n,original_seals=len(seen),member_checks=checks,readout_joins=readjoins,patch_index_axis_site_joins=patchjoins,private_ratio_rows=len(private),terminal_missing=missing,missing_by_kind_layer={str(k):v for k,v in missingby.items()},min_abs_pairgap=min(gaps),random_patch_norm_max_relative_cast_difference=max(norm_rel),headline={l:want['groups']['multi_hop']['reader_rates'][l]for l in('44','60')},read_patch={b:v['read_token']for b,v in want['groups']['multi_hop']['patches'].items()},first_opening=opening,timestamps_utc={p.name:datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat()for p in(guard,actual/'RESULTS.json',actual/'ANALYSIS_SEAL.json')})
Path('/tmp/rq_e133_main_real_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))

```
<!-- /RQ_REPRO_E133_MAIN_REAL_V1 -->


## §248 C amendment1 prospective owner-kernel comparison — PURE source arithmetic PASS

Sourcea7b358754/37receiptpins exactworking+Git; own17 NEWamendment synthetic tests checkout+17 exactcommittedextract PASS (owner38 includes prior21, not rerun unchanged). Independent225 statistic/coverage comparisons PASS:3full84synthetic group/missing grids,fivequantity mean/Wilson/5000seed0 joint-itemdifferences;both model endpoints/five model fits/common-three-feature census/5000paired-OOF gainbootstrap, floatdrift<1e-14. Initial exact-test process pointed to a not-yet-created temp directory and did not start; directory extraction then exact tests PASS. No real C rows, E109/E131 margins/vectors, source_rows/bind/inputs/main/guards or scientific model fit invoked. Rawsign/cohort/source-bank/finalTABLE_POINTERS identity review remains future original-delivery review, not blanket executionGO.

Pre-outcome convention reconciliation: committed owner models uses ALL3features-complete common census for answer/probe/displacement/answer+probe/joint and their paired gain; this matches the independent common-census comparison, with known/missing explicit. Original two-feature-only prewrite is retained as a separately labelled potential sensitivity, not silently mixed into the owner primary. Bootstrap is confirmed fixed OOF scores/no refit, as prewritten. Owner prospectively fixes global deck-caption test to old44-at8 endpoint (resistant endpoint beside); this resolves the earlier prototype's unspecified target rather than choosing the better observed result. Pointgain>=.05+LB>0 unchanged; zero/oneclass models remain unavailable. If gain unavailable, report estimate/CI unknown, not numerical zero; fallback phrase eligibility alone is not proof of a successful susceptibility model.

Semantic distinction explicit before use: groups_run decodes clean/random rates via original state() EXCLUSIVE-old (dual excluded). Prior original C old44-at8 predictive outcome remains PRESENCE(old+dual). These are distinct measures; group presentation must label exclusive-old and preserve dual/old-presence companion or disclose it unavailable, never silently call exclusive counts old-presence. New random-alpha8 group source intentionally uses ORIGINAL E104ce564237, not E128/E109REFERENCEef8e; keep both banks named and prior42/42vs41/42distinction. Sourcegeometry zero clean norm failsclosed whereas reviewer metric returns NE; neither substitutes epsilon/value. Only synthetic arithmetic compared; final zero-norm/missing/bank/roles handling audited on genuine sealed binding later.

<!-- RQ_REPRO_248C_AMEND1_COMPARE_V1 -->
```python
"""SYNTHETICS ONLY: independent amendment1 kernels vs committed prospective source."""
import importlib.util,numpy as np
from projects.g_agreement.companions248 import amendment1 as w
s=importlib.util.spec_from_file_location('q','/tmp/rq_248c_amend1_prewrite.py');q=importlib.util.module_from_spec(s);s.loader.exec_module(q)
checks=0
for scenario in (0,1,2):
 rows=[]
 for i in range(84):
  r=dict(id=str(i),flips={'2':None if scenario==2 and i%13==0 else False,'4':i<42,'6':None if scenario==2 and i%17==0 else True,'8':True},clean_old44=None if scenario and i%9==0 else int(i%3==0),answer_margin=None if scenario and i%7==0 else float(i%11),random_old44_4=int(i%2),random_old44_6=int(i%4==0),random_old44_8=int(i%5==0));rows.append(r)
 got=w.groups(rows);rr=sorted(rows,key=lambda x:x['id'])
 for field in ('clean_old44','answer_margin','random_old44_4','random_old44_6','random_old44_8'):
  own=q.group_comparison(rr,field,'continuous'if field=='answer_margin'else'rate');want=got['quantities'][field]
  for g in ('easy','resistant'):
   a=own[g];b=want[g];assert a['planned_n']==b['planned_n']and a['known_n']==b['n']and a['missing_n']==b['missing_n'];checks+=3
   point=a['mean']if field=='answer_margin'else a['estimate'];assert point==b['estimate'];checks+=1
   if field!='answer_margin':assert a['Wilson95']==b['Wilson95'];checks+=1
  a=own['resistant_minus_easy_mean'];b=want['difference'];assert a['estimate']==b['estimate']and a['valid_bootstraps']==b['valid_bootstraps']and a['CI95']==b['CI95'];checks+=3
# Fixed all-three-feature census as owner specifies: model/gain arithmetic independently matched.
rows=[]
for i in range(28):
 rows.append(dict(id=str(i),flips={'2':False,'4':i<14,'6':True,'8':True},answer_margin=float((i*7)%19),probe_unhooked=float(i%2)+.013*i,displacement8=None if i==2 else float(i%5),old44_alpha8=None if i==4 else int(i%2)))
got=w.models(rows)
for endpoint in ('resistant','old44_alpha8'):
 rr=[dict(r,target=(None if q.group(r)is None else int(q.group(r)=='resistant'))if endpoint=='resistant'else r['old44_alpha8'])for r in rows]
 own=q.predictive_comparison(rr,'target',{'answer':('answer_margin',),'probe':('probe_unhooked',),'displacement':('displacement8',),'answer_probe':('answer_margin','probe_unhooked'),'joint':('answer_margin','probe_unhooked','displacement8')})
 want=got['endpoints'][endpoint]
 for name,z in want['models'].items():
  assert z['kept']==own['known_n']and z['missing']==own['missing_n'];assert abs(z['loo_auroc']-own['models'][name]['estimate'])<1e-14;checks+=3
 a=own['gains']['answer_probe_minus_answer'];b=want['probe_added_value'];assert a['valid_bootstraps']==b['valid_bootstraps'];assert abs(a['estimate']-b['estimate'])<1e-14 and np.max(np.abs(np.asarray(a['CI95'])-b['CI95']))<1e-14;checks+=3
print('PASS',checks,'synthetic numeric/coverage comparisons:3group grids/fivequantities/full5000differences;bothendpoints/allthreefeaturematchedLOOs/paired5000OOFgain (float1e-14)')

```
<!-- /RQ_REPRO_248C_AMEND1_COMPARE_V1 -->


## §248 C amendment1 parts1/2 independent numerical review COMPLETE — posthoc associations

Shared5817308f6/original013fd87cfeb4cf355a058d1af20c1ac6e81f55771ed14f298ea201f331997691 exact originalCPU3members including ROWS.PRIVATE79158e0f/BINDING.PRIVATE133a8300. Public seal is a REFERENCE, never stripped/resealed; private rows remain CPU-local. Independent prewritten pooled-item5000seed0 reproduction: **71 statistic/coverage fields EXACT**,588 logical source-row fields/420 quantity joins/84 clean old-oriented E131 native margin joins, original84 literal crosswalk exact;10seals137memberchecks. Only E131 source-feature joins under C, no E131 outcome review/classifier/refit. No owner source_rows/bind/inputs/main/guard invoked or real predictive model fit.

New crosswalk custody correction64c485ba5/originale798c04f1 reviewed: literal W-text246 source SHA f03acd29,84uniqueE131base→E104/E127same original ID, no alias guess. One NEW pure rejected-wrong-hash test+one exactGitextract PASS; prior17/38 tests unchanged not repeated. Frozen group-phase37pins exact atoriginale798; group/mean_stat/difference/groups AST unchanged. Independently decoded exact pinned Qwen tokenizer candidate IDs for the84unhooked records, verified input/base/condition/order, logprob/logit margin consistency and CPU old/new orientation; no reparse of E131 outcome cohort. Original guarded GROUPS_SPECb15f10a5 is parsed-identical to serialized BINDING133a8300, originalbytehash kept separate.

Own=worker easy42/resistant42, unknown0. Clean E127 no-prefix44 EXCLUSIVEold easy24/41=.5853658537 Wilson[.4336683536,.7224366917] (1missing/planned42),resistant42/42=1[.9161983875,1.0000000000000002]; resistant−easy .4146341463 bootstrapCI[.2682520325,.5714285714]. Clean E131 old-answer margin means3.9047619615 vs10.9832588945, difference7.0784969330[6.9576001724,7.2061640461]. Random-direction44old: alpha4 easy31/42 vs42/42, diff.2619047619[.1351351351,.4]; alpha6 21/42 vs40/42, diff.4523809524[.2814573294,.6190476190]; alpha8 ORIGINAL E104ce564237 16/42 vs41/42,diff.5952380952[.4390033521,.7446808511]. All five CIs5000/5000defined, known/planned/missing retained, no zero imputation. These are EXCLUSIVEold; independently ALL8group×readout dual counts0, so old-presence companion is numerically identical here (separate definition retained). Random8originalE104 bank deliberately distinct from E128/E109REFERENCE; no code replacement/rejudge.

Reading: resistant items already have higher clean old-fact reporting and old-answer confidence; easy items also lose old-fact reporting under random perturbations as dose rises. These descriptive posthoc associations support familiarity/generic-perturbation alternatives as relevant checks; they do not isolate a cause or prove intrinsic stable item traits/persistent early representation. Geometry and amended LOO gain tests remain separate PENDING; no deck predictive-threshold claim from group comparisons. Historical E13584/84 is pair-logit preference, not fullgreedytext proof.

Clock: originalcommittedfix e79806:58:25CET contains same pinned crosswalk implementation (rebasedpublication64c07:00:04 is later); guard06:58:28.871629<ROWS.872141<RESULTS06:58:29.367383<seal.367893<public58107:00:18. Source decode/validation occurs BEFORE guard, so guard is not first feature-opening clock; owner reported failed preflight before claim, earlier retained/discarded history unverified. No source-before-ALL-openings certification inferred from nominal headers. Original C_GROUPS_AMENDMENT1_ONCE CONSUMED NEVERreplay; final C must reuse exact sealed group rows/result, not recompute them. Newfinalsource4b10664fa/geometry+modeltransport/sourcechanges arrived; fullsourcecompare/finalsealedresult review remains pending.

<!-- RQ_REPRO_248C_GROUPS_REAL_V1 -->
```python
"""Independent §248C amendment1 parts1/2 only. No author decoder/bind/guard or predictive model."""
import importlib.util,json,hashlib,subprocess,datetime
from pathlib import Path
import numpy as np
from tokenizers import Tokenizer

def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
q=load('q','/tmp/rq_prospective_reproductions.py');pre=load('pre','/tmp/rq_248c_amend1_prewrite.py');R=Path.cwd();root=R.parent/'wt-wmech/cache/g_agreement/understand/companions248';actual=root/'C_groups_amendment1_once';pub=R/'results/g_agreement/understand/companions248/C_amendment1_groups';digest='013fd87cfeb4cf355a058d1af20c1ac6e81f55771ed14f298ea201f331997691';seen={};checks=0

def seal(p,h=None):
 global checks
 p=Path(p)
 if h:assert q.sha(p)==h
 if str(p)not in seen:
  z=q.read_json(p)
  for f,v in z['files'].items():assert q.sha(p.parent/f)==v;checks+=1
  seen[str(p)]=z
 return seen[str(p)]
meta=seal(actual/'ANALYSIS_SEAL.json',digest);assert q.sha(pub/'ANALYSIS_SEAL.json')==digest and (pub/'RESULTS.json').read_bytes()==(actual/'RESULTS.json').read_bytes();assert meta['status']=='COMPLETE_ONCE'
spec=q.read_json(actual/'BINDING.PRIVATE.json');wanted=q.read_json(actual/'ROWS.PRIVATE.json');bywant={r['id']:r for r in wanted};assert len(bywant)==84
for k,h in [('e135','717df78053b3fa77342ded7166535fd8d3a878e7cba2e33fa5f78289cb6dc5f4'),('e127','3025b76adfd74ee194e62a69e3b57044eb92a99298b64232f47172e3fbf93f5c'),('e131','88f4252d7c45e9ffa93fd79c5bca1248dfec3e36dab7dd2003b86fcb122d5b9f')]:seal(spec[k+'_seal'],h)
s135=q.read_json(Path(spec['e135_seal']).parent/'BINDING.json');s127=q.read_json(Path(spec['e127_seal']).parent/'BINDING.json');s128=q.read_json(s135['e128_spec']);refs=q.normalize128(s128);ids={r['id']for r in refs};assert ids==set(bywant)
# Literal E135 raw pair flags and random44 code joins (not old analysis replay).
om=seal(s135['output_seal'],s135['output_sha256']);src6=q.Sources(om['source_seals']);g6={r['item_id']:r for r in q.read_json(Path(s135['output_seal']).parent/'MEASUREMENTS.json')};assert set(g6)==ids
# Literal E127 no-prefix old44 readout; never original E127 classification/analysis.
o127=seal(s127['output_seal'],s127['output_sha256']);src127=q.Sources(o127['source_seals']);g127={r['item_id']:r for r in q.read_json(Path(s127['output_seal']).parent/'MEASUREMENTS.json')};assert set(g127)==ids
# Original E104 RANDOM8 bank, deliberately distinct from E128/E109 reference.
seal(spec['e104_judgment_seal'],'ce564237b9951502478d26ab9c5bdcca3a8e3a7c90c0579660c76e4149cbf85b');codes104={r['id']:r for r in q.read_json(Path(spec['e104_judgment_seal']).parent/'JUDGMENTS.json')};assert q.sha(s128['e104_private'])=='495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4';labels104={r['item_id']:r for r in q.read_json(s128['e104_private'])if r['row']=='fact_recall'and r['arm']=='U'and r['condition']=='random'};assert set(labels104)==ids
# Original E131 old/new candidate orientation and exact crosswalk; source features only.
assert q.sha(spec['e131_crosswalk'])=='f03acd297f0cca855167fea022a118199791062b8632afad7f0333d996e3f1f6';xwalk=q.read_json(spec['e131_crosswalk'])['records'];cross={r['e131_base_id']:r['e104_item_id']for r in xwalk};assert len(xwalk)==len(cross)==84 and set(cross.values())==ids and all(r['e104_item_id']==r['e127_original_base_id']for r in xwalk)
binding=q.read_json(R/'results/g_agreement/understand/e131/INPUT_BINDING.json');ip=Path(binding['input_root']);cp=Path(binding['CPU_only_root']);seal(ip/'INPUT_SEAL.json',binding['input_sha256']);seal(cp/'POINTER_SEAL.json',binding['CPU_only_seal_sha256']);pt=q.read_json(cp/'LABEL_SOURCE.json');assert q.sha(pt['root'])==pt['sha256'];labs={r['base_id']:r for r in q.read_json(pt['root'])};inp={r['id']:r for r in q.read_json(ip/'items.json')}
tp=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json');assert q.sha(tp)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42';tok=Tokenizer.from_file(str(tp))
e131=seal(spec['e131_output_seal'],spec['e131_output_sha256']);assert e131['experiment']=='E131'and e131['status']=='COMPLETE';assert q.read_json(spec['e131_seal'])['output_sha256']==spec['e131_output_sha256']
idx=q.read_json(Path(spec['e131_output_seal']).parent/'INDEX.json');assert len(idx)==len({r['id']for r in idx})==840;margins={};cache={};marginjoins=0
for x in idx:
 b=inp[x['id']]
 if b['condition']!='unhooked':continue
 base=cross[b['base_id']];lab=labs[pt['e131_to_e127_base'][b['base_id']]];assert lab['old_value'].casefold()!=lab['new_value'].casefold()
 assert len(b['candidate_ids'])==1 and all(len(v)==1 for v in b['candidate_ids'][0]);names=[tok.decode(v,skip_special_tokens=False).strip().casefold()for v in b['candidate_ids'][0]];assert set(names)=={lab['old_value'].casefold(),lab['new_value'].casefold()}
 f=Path(spec['e131_output_seal']).parent/x['member'];assert x['member']in e131['files']
 if f not in cache:cache[f]=q.read_json(f)
 raw=cache[f][x['record']];assert all(raw[k]==b[k]for k in('id','base_id','condition'));lp=raw['pair_logprobs'];lg=raw['pair_logits'];assert len(lp)==len(lg)==1 and len(lp[0])==len(lg[0])==2
 m=lp[0][0]-lp[0][1];assert abs(m-raw['pair_mean_a_minus_b'])<1e-5 and abs(m-(lg[0][0]-lg[0][1]))<1e-3
 assert base not in margins;margins[base]=m if names[0]==lab['old_value'].casefold()else-m;marginjoins+=1
assert set(margins)==ids

def readcode(src,cell,item,c,layer,dose=None):
 ii=src.ref(cell['identity']);z=src.ref(cell['code']);assert ii['item_id']==item and ii['condition']==c and ii['layer']==layer and ii.get('dose')==dose
 if z is None:
  p=cell['code'];t=src.ref(dict(p,keys=p['keys'][:-1]));assert p['keys'][-1]=='code'and t['id']==ii['judgment_id']and t['status']=='UNPARSEABLE';return None
 assert z['id']==ii['judgment_id']and set(z['values'])<={'A','B'}
 return z
rows=[];dual={};sourcejoins=0
for ref in refs:
 i=ref['id'];old=ref['old'];flips={str(d):(ref['doses'][str(d)]['steered']['pair_flag']if d==8 else q.preference(ref['doses'][str(d)]['steered']['raw'],ref['new'])=='new')for d in(2,4,8)}
 cell=g6[i]['doses']['6']['steered']['behaviour'];ii=src6.ref(cell['identity']);raw=src6.ref(cell['record']);assert ii['item_id']==i and ii['dose']==6 and ii['condition']=='steered'and ii['raw_id']==raw['id'];flips['6']=q.preference(raw,ref['new'])=='new'
 code127=readcode(src127,g127[i]['conditions']['no_prefix']['oracle']['44'],i,'no_prefix',44)
 code6=readcode(src6,g6[i]['doses']['6']['random']['oracle']['44'],i,'random',44,6)
 code4=ref['doses']['4']['random']['code']['44'];code8=codes104[labels104[i]['opaque_id']]
 row=dict(id=i,flips=flips,clean_old44=q.state(code127,old),answer_margin=margins[i],random_old44_4=q.state(code4,old),random_old44_6=q.state(code6,old),random_old44_8=q.state(code8,old));assert row==bywant[i], 'literal original row mismatch';rows.append(row);sourcejoins+=5
 for f,z in [('clean_old44',code127),('random_old44_4',code4),('random_old44_6',code6),('random_old44_8',code8)]:
  g=pre.group(row);dual[g,f]=dual.get((g,f),0)+int(z is not None and set(z['values'])=={'A','B'})
rows=sorted(rows,key=lambda r:r['id']);want=q.read_json(actual/'RESULTS.json');numeric=0;own={}
for f in ('clean_old44','answer_margin','random_old44_4','random_old44_6','random_old44_8'):
 a=pre.group_comparison(rows,f,'continuous'if f=='answer_margin'else'rate');b=want['quantities'][f];own[f]=a
 for g in('easy','resistant'):
  aa=a[g];bb=b[g];assert aa['planned_n']==bb['planned_n']and aa['known_n']==bb['n']and aa['missing_n']==bb['missing_n'];numeric+=3
  v=aa['mean']if f=='answer_margin'else aa['estimate'];assert v==bb['estimate'];numeric+=1
  if f!='answer_margin':assert aa['k']==bb['k']and aa['Wilson95']==bb['Wilson95'];numeric+=2
 aa=a['resistant_minus_easy_mean'];bb=b['difference'];assert aa['estimate']==bb['estimate']and aa['CI95']==bb['CI95']and aa['valid_bootstraps']==bb['valid_bootstraps'];numeric+=3
assert want['group_counts']==dict(easy=42,resistant=42,unknown_or_other=0)
guard=root/'C_GROUPS_AMENDMENT1_ONCE.json';gm=q.read_json(guard);original_spec=R.parent/'wt-wmech2/cache/g_agreement/understand/companions248/amendment1_binding/GROUPS_SPEC.PRIVATE.json';assert gm['spec_sha256']==q.sha(original_spec)and q.read_json(original_spec)==spec;assert gm['source_receipt']==q.sha(R/'projects/g_agreement/companions248/SOURCE_RECEIPT_GROUPS_PHASE.json')
summary=dict(status='PASS',group_counts=want['group_counts'],literal_source_row_field_checks=84*7,source_quantity_joins=sourcejoins,old_oriented_margin_joins=marginjoins,full_crosswalk84=True,metric_coverage_field_checks=numeric,original_seals=len(seen),member_checks=checks,quantities=want['quantities'],dual_census={str(k):v for k,v in dual.items()},timestamps_utc={p.name:datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat()for p in(guard,actual/'ROWS.PRIVATE.json',actual/'RESULTS.json',actual/'ANALYSIS_SEAL.json')})
Path('/tmp/rq_248c_groups_real_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))

```
<!-- /RQ_REPRO_248C_GROUPS_REAL_V1 -->


## §248 C amendment1 FINAL scientific numerical review COMPLETE — probe added-value gate NOT MET

Publishede6872fb7b/original48c56c1f122d20036f60416a3bac4c4328214525f6adfad8f6cd7894be8d71b8 full3-member CPU seal(TABLE430e1abc/BINDING31ed9567/RESULTS8e2702a1) exact; public seal unchangedreference, no private-row export. Own independently rebuilt all84 table rows from original source pointers, verified840 sourcefield checks/252 nativevector+prompt+readindex joins,14source/dependencyseals576members; **148 metric/coverage comparisons PASS**, AUROC/CI drift<1e-14 and maximum standardized coefficient/intercept drift3.3306690739e-15. Twelve amended LOO model specifications/two original registered two-feature models reproduced with training-only mean/sd standardization/C1/lbfgs2000seed0, no tuning or held-out scaling. Original univariate signed rank-AUC/CIs/min-dose census retained; paired5000seed0 fixedOOFbootstrap for every model/gain reproduced. No ownerfinal_run/delivered/vectors6/inputs/bind/main/guard invoked.

Bdelivery57936987 exact, E109 nativeh44 fp32arrays both84×5120 bit-for-bit via originalCAPTURE_INDEX metadata/nativeID/row/split/condition/readtoken. Actual original dev44 raww/b/class0=B,class1=A applied independently to both arrays with original-fact sign; all168 delivered margins EXACT,0E109new fits; frozen dev84 disjoint currenttest84, originalfit audit retained. E135alpha6 all84 ACTUALCAPTURE_INDEXlayer44 vector slots bound via original381input/pointer/base/scale.75; tokens/readindex exactly equal E109clean, arrays finite5120, no write-sitecalibration substitute. Both E109steered andclean tokens/readsite match. Norm(hsteer−hclean)/norm(hclean) computed infloat64, no zero/epsilon/clipping/drop; alpha6 comparison uses E135steered against E109clean across acquisitions, not a simultaneous same-run clean pass. No causal intervention-only interpretation from matching IDs. Group013fd87c prior84 rows reused verbatim, groupRESULTS not recomputed; snapshot55583c4b3 publishedRQitem-checkfilehash44a40646 exact with bothbankdistinctions.

Own=worker OLD44STALENESS outcome n83 (1originalREFERENCEalpha8missing;allpredictors/vectors known84): LOO AUROC answer.9196217494,probe.6625295508,displacement.9202127660,answer+probe.9113475177,answer+displacement.9539007092,joint.9521276596. **Primary probe-added gain −.0082742317 CI[−.0261815818,.0017626322],5000/5000defined: NOT MET** against>=.05 ANDLB>0. Geometry-adjusted joint-minus-answer+displacement −.0017730496[−.0081873742,.0023310023],also no demonstrated added value. Resistant-vs-easy n84: answer1,probe.7108843537,displacement.9416099773,answer+probe1,answer+displacement1,joint1;gain0 (sourcefloatingCI±1.110223e-16 retained, independentrankbootstrap0 within1e-14). This endpoint does not replace the prospectively chosen old44caption test. Common3featurecensus used consistently; missing target1 is not recoded0 or absorbed into neither.

Geometry easy42/resistant42 means: alpha6 .2185848252 vs.1985532302, resistant−easy−.0200315950 CI[−.0228011324,−.0173283520]; alpha8 .2242544821 vs.2094096686,difference−.0148448135[−.0174854068,−.0122227047],5000/5000defined. Resistant items receive smaller realised read-token displacement under this matched-source metric. Original fixed-sign univariateAUROCs: min-dose.9468085106,clean-answer.9429669031,unhooked-oldprobe.3073286052 (NOTinverted),post-steer8probe.8463356974 sensitivityONLY. Logistic probe-only.662530 uses a sign fitted within each training fold; it is not the fixed-sign raw-probe statistic. Original four-dose crosscount[[36,47],[0,0]]/1missing/no unobservedminimumforced8 preserved. Old rawprobeAUROC>=.80caption gate supersededbyamend1; alpha8sensitivity cannotrescueprimarycleanprobe-addedgain.

Deck reading per amendment: **“susceptibility to steering predicts it”**, labelled exploratory/posthoc on these84; **NOT “the early representation predicts staleness.”** Together with clean familiarity/groupdifferences and smaller downstream displacement, these observations do not isolate persistent early representation or an intrinsic item cause. Bootstrap intervals condition on fixed held-out predictions and do not refit bootstrap training samples; no independent external validation or population/causal certainty claimed. E117NE/E133NOTMET conclusions unchanged.

Finalsource4b10664fa COMMITTER07:04:22/e47byteidentical07:04:46CET<localCguard07:05:07.220457<TABLE.221666<RESULTS07:05:55.873512<seal.874325<public07:07:56. Originalrawsource decode/margins/vector-displacement construction occurs BEFORE guard, so guardclock does not establish firstfeatureopening. Original source38pins exact; two NEWpuretarget-selection/group-reuse tests checkout+two exactGitextract PASS (prior39 unchanged tests not rerun; owner41 retained). Source before declared solemodelrun verified, earlier pilot/discardedhistory notcertified. OriginalC_ONCE andGROUPS_ONCE CONSUMED NEVERreset/replay; no paid/GPU/API/process/ledger operation or E109refit. All §248C scientific quantities now reviewed; originalreal kernels/sourcejoins/models CLOSED absentchangedinputs.

<!-- RQ_REPRO_248C_FINAL_REAL_V1 -->
```python
"""Independent sealed §248C final source normalization and fixed models; no author entrypoints/guards."""
import importlib.util,json,hashlib,subprocess,datetime,warnings
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning

def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
q=load('q','/tmp/rq_prospective_reproductions.py');pre=load('pre','/tmp/rq_248c_amend1_prewrite.py');oldpre=load('oldpre','/tmp/rq_248c_independent_synthetics.py')
R=Path.cwd();root=R.parent/'wt-wmech/cache/g_agreement/understand/companions248';actual=root/'C_analysis_once';groups=root/'C_groups_amendment1_once';pub=R/'results/g_agreement/understand/companions248/C';seen={};checks=0;sourcechecks=0

def seal(p,h=None):
 global checks
 p=Path(p)
 if h:assert q.sha(p)==h,(p.name,'seal')
 if str(p)not in seen:
  z=q.read_json(p)
  for f,v in z['files'].items():assert q.sha(p.parent/f)==v,(p.name,f);checks+=1
  seen[str(p)]=z
 return seen[str(p)]
digest='48c56c1f122d20036f60416a3bac4c4328214525f6adfad8f6cd7894be8d71b8';seal(actual/'ANALYSIS_SEAL.json',digest);assert q.sha(pub/'ANALYSIS_SEAL.json')==digest and (pub/'RESULTS.json').read_bytes()==(actual/'RESULTS.json').read_bytes()
spec=q.read_json(actual/'BINDING.PRIVATE.json');guard=q.read_json(root/'C_ONCE.json');ospec=R.parent/'wt-wmech2/cache/g_agreement/understand/companions248/amendment1_binding/FINAL_SPEC.PRIVATE.json';assert q.sha(ospec)==guard['spec_sha256']and q.read_json(ospec)==spec
review=subprocess.check_output(['git','show',spec['review_commit']+':results/g_agreement/reviews/R-Q/HANDOFF.md']);assert hashlib.sha256(review).hexdigest()==spec['review_file_sha256']and b'42/42'in review and b'41/42'in review
seal(spec['group_seal'],'013fd87cfeb4cf355a058d1af20c1ac6e81f55771ed14f298ea201f331997691');prior={r['id']:r for r in q.read_json(groups/'ROWS.PRIVATE.json')};gs=q.read_json(groups/'BINDING.PRIVATE.json');seal(gs['e135_seal'],'717df78053b3fa77342ded7166535fd8d3a878e7cba2e33fa5f78289cb6dc5f4');s135=q.read_json(Path(gs['e135_seal']).parent/'BINDING.json');s128=q.read_json(s135['e128_spec']);refs=q.normalize128(s128);refby={r['id']:r for r in refs};assert set(refby)==set(prior)
# Exact original delivery, frozen E109 dev-only coefficient application (NO E109 refit).
dp=Path(spec['margin_delivery_seal']);dm=seal(dp,'5793698784276ac806f6908b370928db444e3c4df6be14feebdae14bc5166914');di=q.read_json(dp.parent/'IDENTITIES.PRIVATE.json');ids=di['item_ids'];assert len(ids)==len(set(ids))==84 and set(ids)==set(prior)
bind=q.read_json(dp.parent/'SOURCE_BINDING.PRIVATE.json');plan=bind['plan'];assert bind['fit_calls']==dm['new_fits']==0
for k in ('e133_analysis','inventory','binding','probe'):seal(plan[k+'_seal'],plan[k+'_sha256'])
assert plan['e133_analysis_sha256']=='e6f12addf1bdb63fb02deafffe7b602835ec5efd02e326470a7aaf9b5fe752d0'
bm=q.read_json(plan['binding_seal']);capsrc=bm['source_seals'][0];cap=seal(capsrc['seal'],capsrc['sha256']);caproot=Path(capsrc['seal']).parent;pr=Path(plan['probe_seal']).parent;pm=q.read_json(pr/'PROBE_MANIFEST.json');assert pm['capture_seal_sha256']==capsrc['sha256']
p=next(p for p in pm['probes']if p['row']=='fact_recall');assert p['block']==44 and p['preprocessing']=='none'and p['class_letter_mapping']=={'0':'B','1':'A'}and p['fit_split']=='unhooked_dev'and p['test_used_for_fit']is False
wp=pr/'weights/fact_recall_probe.npz';assert q.sha(wp)==p['weights_sha256'];weights=np.load(wp,allow_pickle=False);w=weights['w'];b=weights['b'];assert w.shape==(5120,)and b.shape==()and weights['classes'].tolist()==[0,1]
arrays={};margins={};native={};cache={};vectorjoins=0
for cond in ('unhooked','steered'):
 arrays[cond]=np.load(dp.parent/(cond+'_vectors44.PRIVATE.npy'),allow_pickle=False);margins[cond]=np.load(dp.parent/(cond+'_old_fact_margins44.PRIVATE.npy'),allow_pickle=False)
 assert arrays[cond].shape==(84,5120)and arrays[cond].dtype==np.float32 and np.isfinite(arrays[cond]).all()
 refs0={r['item_id']:r for r in di['source_refs'][cond]};assert set(refs0)==set(ids)
 for j,i in enumerate(ids):
  assert di['original_fact_letters'][j]==refby[i]['old']and di['steered_target_letters'][j]==refby[i]['new']
  z=refs0[i];vr=z['vector'];md=z['metadata']
  for name in(vr['member'],md['member']):assert name in cap['files']
  for name in(vr['member'],md['member']):
   if name not in cache:cache[name]=np.load(caproot/name,allow_pickle=False)if name.endswith('.npy')else q.read_json(caproot/name)
  raw=cache[md['member']][md['record_index']];assert raw['id']==z['native_id']and raw['base_id']==i and raw['condition']==cond and raw['read_index']==z['read_index']and raw['row']=='fact_recall'and raw['split']=='test'
  assert raw['alpha']==8 if cond=='steered'else raw['hook_installed']is False
  assert np.array_equal(arrays[cond][j],cache[vr['member']][vr['vector_index']]);native[i,cond]=raw;vectorjoins+=1
 sign=np.array([1 if v=='A'else-1 for v in di['original_fact_letters']]);ownm=(arrays[cond].astype(float)@w+float(b))*sign;assert np.array_equal(ownm,margins[cond]);sourcechecks+=84
for i in ids:assert native[i,'unhooked']['ids']==native[i,'steered']['ids']and native[i,'unhooked']['read_index']==native[i,'steered']['read_index']
# E135 actual captured read-token44 vectors (not calibration/write-site proxies).
cm=seal(s135['calibration_seal'],s135['calibration_sha256']);ss=[seal(z['seal'],z['sha256'])for z in cm['source_seals']];ni=next(j for j,z in enumerate(ss)if 'CAPTURE_INDEX.json'in z['files']);pi=next(j for j,z in enumerate(ss)if 'ORIGINAL_POINTERS.PRIVATE.json'in z['files']);ai=next(j for j,z in enumerate(ss)if 'items.json'in z['files']);assert cm['source_seals'][ai]['sha256']=='381b58bde8ab7031e7a1de07bec1afe05655010a815e61a1a84c3b689c1c8047'
r6=Path(cm['source_seals'][ni]['seal']).parent;p6={r['id']:r for r in q.read_json(Path(cm['source_seals'][pi]['seal']).parent/'ORIGINAL_POINTERS.PRIVATE.json')};items6=q.read_json(Path(cm['source_seals'][ai]['seal']).parent/'items.json');ix6=q.read_json(r6/'CAPTURE_INDEX.json');by6={(r['id'],r['source_layer']):r for r in ix6};assert len(by6)==len(ix6);v6={};cache6={}
for x in items6:
 if x['condition']!='steered':continue
 z=p6[x['id']];i=z['original_base_id'];assert i in ids and i not in v6 and z['scale']==.75 and x['alpha']==6
 assert x['ids']==native[i,'unhooked']['ids']and x['read_index']==native[i,'unhooked']['read_index']
 if (x['id'],44)not in by6:v6[i]=None;continue
 ptr=by6[x['id'],44];assert ptr['member']in ss[ni]['files']
 if ptr['member']not in cache6:cache6[ptr['member']]=np.load(r6/ptr['member'],allow_pickle=False)
 v6[i]=cache6[ptr['member']][ptr['vector_index']];assert v6[i].shape==(5120,)and np.isfinite(v6[i]).all();vectorjoins+=1
assert set(v6)==set(ids)
# Read only new original E135 code pointers; use unchanged E128 normalization for historical references.
om6=seal(s135['output_seal'],s135['output_sha256']);src6=q.Sources(om6['source_seals']);grid6={z['item_id']:z for z in q.read_json(Path(s135['output_seal']).parent/'MEASUREMENTS.json')}
rows=[];table=q.read_json(actual/'TABLE.PRIVATE.json');bytable={r['id']:r for r in table};assert len(bytable)==84
for j,i in enumerate(ids):
 r=dict(prior[i]);ref=refby[i];codes={}
 for d in (2,4,6,8):
  if d==6:
   cells=grid6[i]['doses']['6']['steered'];bi=src6.ref(cells['behaviour']['identity']);br=src6.ref(cells['behaviour']['record']);assert bi['item_id']==i and bi['raw_id']==br['id'];f=q.preference(br,ref['new'])=='new';cs={str(l):src6.ref(cells['oracle'][str(l)]['code'])for l in(44,52)}
  else:
   z=ref['doses'][str(d)]['steered'];f=z['pair_flag']if d==8 else q.preference(z['raw'],ref['new'])=='new';cs=z['code']
  assert f==r['flips'][str(d)]
  c=cs['44'];category=None if c is None or c['category']=='UNPARSEABLE'else'dual'if set(c['values'])=={ref['old'],ref['new']}else'old'if c['values']==[ref['old']]else'new'if c['values']==[ref['new']]else'neither'
  v=q.state(cs['52'],ref['new']);codes[str(d)]=dict(**{'44':category},**{'52_new':None if v is None else bool(v)});sourcechecks+=2
 r.update(codes=codes,unhooked_margin=r['answer_margin'],probe_unhooked=float(margins['unhooked'][j]),probe_alpha8=float(margins['steered'][j]),displacement8=pre.displacement(arrays['unhooked'][j],arrays['steered'][j]),displacement6=pre.displacement(arrays['unhooked'][j],v6[i]));r['old44_alpha8']=None if codes['8']['44']is None else int(codes['8']['44']in('old','dual'));assert r==bytable[i], 'literal final table mismatch';rows.append(r)
rows=sorted(rows,key=lambda r:r['id']);want=q.read_json(actual/'RESULTS.json');assert want['group_results_recomputed']is False and want['group_result_seal']==q.sha(groups/'ANALYSIS_SEAL.json')and want['bank']=='old44 alpha8 models use E109 reference; group random8 uses original E104';numeric=0
# Geometry group comparisons reuse prewritten independent item bootstrap.
for f in ('displacement8','displacement6'):
 a=pre.group_comparison(rows,f,'continuous');bb=want['displacement_by_group'][f]
 for g in('easy','resistant'):
  assert a[g]['known_n']==bb[g]['n']and a[g]['mean']==bb[g]['estimate']and a[g]['missing_n']==bb[g]['missing_n'];numeric+=3
 z=a['resistant_minus_easy_mean'];assert z['estimate']==bb['difference']['estimate']and z['CI95']==bb['difference']['CI95']and z['valid_bootstraps']==bb['difference']['valid_bootstraps'];numeric+=3
# Original registered fixed-sign rank-AUC, minimum-dose census and two-feature LOO retained.
orig=want['original_registered'];cross=[[0,0],[0,0]];missing=0;mins={}
for r in rows:
 d=oldpre.minimum(r['flips']);mins[r['id']]=d;y=r['old44_alpha8']
 if d is None or y is None:missing+=1
 else:cross[int(d==8)][y]+=1
assert cross==orig['min_dose_by_old44']and missing==orig['cross_missing']
for f in('min_flipping_dose','unhooked_margin','probe_unhooked','probe_alpha8'):
 x=[mins[r['id']]if f=='min_flipping_dose'else r[f]for r in rows];y=[r['old44_alpha8']for r in rows];a=oldpre.independent_auc([np.nan if v is None else v for v in x],[np.nan if v is None else v for v in y]);b=orig['predictor_auroc'][f]
 for k in('kept','valid_bootstraps'):assert a[k]==b[k];numeric+=1
 for k in('estimate','CI95'):
  if a[k]is None:assert b[k]is None
  else:assert np.max(np.abs(np.asarray(a[k])-b[k]))<1e-14
  numeric+=1
# Amendment complete-case 6 models per target, paired score bootstraps, plus coefficients.
features={'answer':('answer_margin',),'probe':('probe_unhooked',),'displacement':('displacement8',),'answer_probe':('answer_margin','probe_unhooked'),'answer_geometry':('answer_margin','displacement8'),'joint':('answer_margin','probe_unhooked','displacement8')};ownmodels={};maxcoef=0.
def fullfit(x,y):
 mu=x.mean(0);sd=x.std(0);sd[sd==0]=1
 with warnings.catch_warnings():
  warnings.simplefilter('error',ConvergenceWarning);m=LogisticRegression(C=1.,solver='lbfgs',max_iter=2000,random_state=0).fit((x-mu)/sd,y)
 return m.coef_[0],m.intercept_[0]
for endpoint in('resistant','old44_alpha8'):
 rr=[dict(r,target=(None if pre.group(r)is None else int(pre.group(r)=='resistant'))if endpoint=='resistant'else r['old44_alpha8'])for r in rows];a=pre.predictive_comparison(rr,'target',features);b=want['amendment_models']['endpoints'][endpoint];ownmodels[endpoint]=a
 kept=[r for r in rr if pre.binary(r['target'])and all(pre.finite(r[f])for f in('answer_margin','probe_unhooked','displacement8'))];y=np.array([r['target']for r in kept],int)
 for name,fs in features.items():
  wn='answer_displacement'if name=='answer_geometry'else name;wstat=b['models'][wn];s=a['models'][name];assert wstat['kept']==a['known_n']and wstat['missing']==a['missing_n'];assert abs(wstat['loo_auroc']-s['estimate'])<1e-14;numeric+=3
  boot=wstat['loo_auroc_bootstrap'];assert abs(boot['estimate']-s['estimate'])<1e-14 and np.max(np.abs(np.asarray(boot['CI95'])-s['CI95']))<1e-14 and boot['valid_bootstraps']==s['valid_bootstraps'];numeric+=3
  x=np.array([[r[f]for f in fs]for r in kept]);coef,inter=fullfit(x,y);drift=max(float(np.max(np.abs(coef-wstat['standardized_coefficients']))),abs(inter-wstat['intercept']));maxcoef=max(maxcoef,drift);assert drift<1e-12;numeric+=2
 for an,bn in [('answer_probe_minus_answer','probe_added_value'),('joint_minus_answer_geometry','probe_added_value_beyond_answer_and_geometry')]:
  g=a['gains'][an];wb=b[bn];assert abs(g['estimate']-wb['estimate'])<1e-14 and np.max(np.abs(np.asarray(g['CI95'])-wb['CI95']))<1e-14 and g['valid_bootstraps']==wb['valid_bootstraps'];numeric+=3
 assert b['deck_phrase_eligible']==(a['gains']['answer_probe_minus_answer']['estimate']>=.05 and a['gains']['answer_probe_minus_answer']['CI95'][0]>0)
for f in('probe_unhooked','probe_alpha8'):
 rr=[r for r in rows if r['old44_alpha8']is not None];x=np.array([[r['unhooked_margin'],r[f]]for r in rr]);y=np.array([r['old44_alpha8']for r in rr]);score,why=pre.loo_scores(x,y);o=orig['two_predictor_fits'][f];assert why is None and abs(pre.auc(y,score)-o['auroc'])<1e-14;coef,inter=fullfit(x,y);assert np.max(np.abs(coef-o['standardized_coefficients']))<1e-12 and abs(inter-o['intercept'])<1e-12;numeric+=3
assert want['amendment_models']['deck_phrase']=='susceptibility to steering predicts it'and want['amendment_models']['causal']is False
summary=dict(status='PASS',source_table_rows=84,source_field_checks=sourcechecks,original_vector_prompt_readindex_joins=vectorjoins,original_seals=len(seen),member_checks=checks,numeric_checks=numeric,max_coefficient_intercept_drift=maxcoef,original_cross=cross,original_missing=missing,geometry=want['displacement_by_group'],models=want['amendment_models'],timestamps_utc={p.name:datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat()for p in(root/'C_ONCE.json',actual/'TABLE.PRIVATE.json',actual/'RESULTS.json',actual/'ANALYSIS_SEAL.json')})
Path('/tmp/rq_248c_final_real_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items()if k!='models'},indent=2));print('HEADLINE',json.dumps({e:{'n':v['models']['answer']['kept'],'AUCs':{k:z['loo_auroc']for k,z in v['models'].items()},'gain':v['probe_added_value'],'geometry_gain':v['probe_added_value_beyond_answer_and_geometry']}for e,v in want['amendment_models']['endpoints'].items()}))

```
<!-- /RQ_REPRO_248C_FINAL_REAL_V1 -->


## 2026-10-30 — E95 staged packet/source contract intake (76b8ece53; spawn continuation a240779d2)

SOURCE/INPUT CONTRACT PASS, not a completed scientific stage or financial/launch certification. Independently reconstructed 13,330 frozen group identities, original 3,999 selected and 1,000 nested original-rubric identities; 8,050 candidate groups exactly equal the whole achieved-reader population (62 Oracle rows/44 NLA rows, both arms complete). All three packets are exactly the original selected ∩ acquired ∩ unresolved ∩ registered judging-stage intersection, disjoint and without refill: own=owner stage1 609 primary/151 original/4,842 positions; stage2 1,294/332/10,289; stage3 454/104/3,602. Every packet group equals the original candidate, with whole A/B value strings and ordered ragged 1–8 positions ending at offset zero. Own 62 literal hash checks bind candidate members, original metadata/source seals, public SPEC inputs and packet members. Original inventory/eligibility distinction retained.

Audit metadata coverage/counts exact: 13,330 records = 83 RESOLVED + 12,687 UNRESOLVED + 420 NO_REGEX + 140 NOT_EVALUABLE_NO_STATEMENT_SCORE. These are custody/disposition metadata checks, not an independent semantic replay of the 83 regex resolutions. Source uses the original frozen catalog/matcher, conservative all-position resolution, existing E87 wire and validator221; no new aliases/patterns or reviewer reparse. Seven new contract PURE tests pass in checkout and exact committed extraction, including ragged-position drift, literal value orientation, all-position ambiguity, fixed stage intersection and temporary once guards. All 42 original published source pins exact Git/checkout. No actual admission, preparation, regex application, worker process/API, ledger, real guard or judgment output invoked/opened by R-Q.

Concurrent spawn-only source intake: all 44 WJUDGE95_SPAWN_SOURCE_SEAL pins exact Git/checkout; two NEW PURE unknown-preservation/continuation tests pass in checkout and exact extraction. Source preserves original stage guard, binds stopped partial seal and original saved request hashes/wires, retains unknown reservations, refuses unknown replay and uses a distinct single continuation ticket. Fresh-process initialization replaces fork; packet/audit/rubric/selection remain original. Actual route rehearsal, four unknown requests and their reserved cost are owner-reported operational receipts, not R-Q billing or live-route certification. No terminal stage/sealed scientific result reviewed here. Reviewer review follows the owner's pre-call notice and does not certify reviewer clearance before dispatch or first physical call. Terminal custody must preserve original partial history, four missing/unknown dispositions and full stage completion; incomplete stages remain NOT RUN/not analysed.

W-lens analysis source5348c18e8 remains closed unchanged. Before scientific review, require completed stage seal plus exact original J/E62 median population/RULES/position/property/private-label bindings and final analysis source/seal. H-M1 stays descriptive and per completed stage, with separate layer/reader coverage; no invented full-scope result. Source intake creates no additional operator permission requirement.

<details><summary>RQ_REPRO_E95_PACKET_CONTRACT_V1 — independent read-only metadata/hash reproduction</summary>

```python
import json,hashlib,pathlib,collections
W=pathlib.Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-r-q'); O=W.parent/'wt-judge95'; B=pathlib.Path('results/g_agreement/understand');P=B/'blind_judge/e95_bank'
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
checks=0
def check(p,h):
 global checks
 assert sha(p)==h,(str(p),'hash');checks+=1
rows=read(W/B/'e95/deviation2/ROW_INVENTORY.json')['rows'];idx=read(W/B/'e95/deviation2/JUDGE_INDEX.json');stage=read(W/B/'e95/oracle_only_inventory/INVENTORY_20261029T1448Z.json');audit=read(W/P/'WJUDGE95_REGEX_AUDIT.json')
u={}
for r in rows:
 for reader in ('oracle','nla'):
  for arm in ('real','placebo'):
   ids=r['item_ids'] if arm=='real' or reader=='oracle' and r['reuse_e87'] else [hashlib.sha256(f"E95:placebo:{r['row_index']}:{i}".encode()).hexdigest()[:32] for i in range(15)]
   s=f"{r['row_index']}:{arm}:{reader}"
   for i in ids:
    for l in r['oracle_layers'] if reader=='oracle' else [42]:
     unit=f'{i}:{l}';g=hashlib.sha256(f'E95:group:{s}:{unit}'.encode()).hexdigest()[:32];assert g not in u;u[g]=(s,unit)
assert len(u)==idx['total_universe']==13330
selected={hashlib.sha256(f'E95:group:{s}:{x}'.encode()).hexdigest()[:32] for s,v in idx['selected'].items() for x in v}
old={hashlib.sha256(f'E95:group:{s}:{x}'.encode()).hexdigest()[:32] for s,v in idx['old_rubric_selected'].items() for x in v}
assert len(selected)==3999 and len(old)==1000 and old<=selected
allowed={r:set() for r in ('oracle','nla')}
for sh in stage['shards']:
 for reader in allowed:
  if sh[reader+'_stage_complete']:
   assert all(sh['stages'][reader+'_'+a]['status']=='complete' for a in ('real','placebo'));allowed[reader].update(sh['row_indices'])
assert [len(allowed[x]) for x in ('oracle','nla')]==[62,44]
a={x['id']:x for x in audit['records']};assert len(a)==len(u) and set(a)==set(u)
assert dict(collections.Counter(x['status'] for x in a.values()))==audit['counts']
elig={x['row_index']:x['statement_score_registered'] for x in read(W/B/'e95/STATEMENT_SCORE_ELIGIBILITY.json')['rows']}
for g,(s,unit) in u.items():
 if not elig[int(s.split(':')[0])]:assert a[g]['status']=='NOT_EVALUABLE_NO_STATEMENT_SCORE'
 else:assert a[g]['status'] in ('NO_REGEX','RESOLVED','UNRESOLVED')
root=O/'cache/g_agreement/e95_judging/candidates';cs=read(root/'CANDIDATE_SEAL.json');check(root/'CANDIDATE_SEAL.json','e0574c589b10db8d8f4453c2963d6d7adbee91fa2c1e61c2793da2e5d612b713')
for f,h in cs['files'].items():check(root/f,h)
for pin in cs['source_seals']+cs['original_metadata_sources']:check(pin['path'],pin['sha256'])
c={x['id']:x for x in read(root/'ALL_GROUPS.PRIVATE.json')};assert len(c)==8050
acquired={g for g,(s,v) in u.items() if int(s.split(':')[0]) in allowed[s.split(':')[-1]]};assert set(c)==acquired
out=[];seen=set()
for n,reader,layers in [(1,'oracle',[44,52,60]),(2,'oracle',[20,28,36,56]),(3,'nla',[42])]:
 pub=W/P/f'stage{n}';sp=read(pub/'SPEC.json');binding=read(pub/'PACKET_BINDING.json');check(pub/'SPEC.json',binding['spec_sha256'])
 for k in ('inventory','index','eligibility','regex_audit','custody_receipt','budget_receipt','source_seal'):
  check(sp[k],sp[k+'_sha256'])
 packet=pathlib.Path(sp['packet']);check(packet/'PACKET_SEAL.json',sp['packet_seal_sha256']);ps=read(packet/'PACKET_SEAL.json')
 assert binding['private_files']==ps['files']
 for f,h in ps['files'].items():check(packet/f,h)
 groups=read(packet/'GROUPED_PACKET.json');got={x['id'] for x in groups}
 want={g for g in selected&acquired if u[g][0].split(':')[-1]==reader and int(u[g][1].rsplit(':',1)[1]) in layers and a[g]['status'] in ('NO_REGEX','UNRESOLVED')}
 assert got==want and len(groups)==len(got)==ps['n'];assert not seen&got;seen|=got
 original=read(packet/'ORIGINAL_IDS.json');assert len(original)==len(set(original)) and set(original)==got&old
 for group in groups:
  assert group==c[group['id']];assert set(group)=={'id','positions','property','values'}
  assert isinstance(group['values'],dict) and set(group['values'])=={'A','B'} and all(isinstance(v,str) and v for v in group['values'].values())
  offsets=[p['offset'] for p in group['positions']];assert offsets==list(range(-len(offsets)+1,1)) and 1<=len(offsets)<=8
 out.append([n,len(got),len(original),sum(len(x['positions']) for x in groups)])
assert [x[1:3] for x in out]==[[609,151],[1294,332],[454,104]]
print(json.dumps(dict(status='PASS',hash_checks=checks,universe=len(u),candidate_groups=len(c),audit_counts=audit['counts'],stages=out,private_values_printed=False,regex_reparse=False,judgments_opened=False),sort_keys=True))
```
</details>


## 2026-10-30 — E95 stage1 terminal custody COMPLETE (24440bf09; b177c9ce95e2)

Custody PASS only; scientific H-M1 remains pending. Original delivery seal b177c9ce95e2067670ec1f6c01f8303aa68161ca9303c6e84402d9f889f8a91e / terminal seal53f7fbe1ac335a4ae52f278d91b9a8ca0f6606cb81d7d312fbca74db67898c8b: own2,728 hash checks exact across public receipt, four private delivery members, original terminal members, original stopped partial, packet, source bindings, original guard and distinct E87 reuse lineage. Own=owner primary609=548 KEPT+61 missing; original comparison151=139 KEPT+12 missing; total760=687+73. All760 flattened records literally equal original kept codes or the unchanged explicit UNPARSEABLE/null sentinel; no reparse/rejudge/semantic interpretation. All609 private joins equal original packet joins with exact indexed original-terminal code pointers; selected/nested IDs unchanged. Four original unknown physical requests remain null/missing with exact original request IDs; original guard/partial seal retained. Three NEW delivery PURE tests PASS (temporary synthetic outputs only).

Original packet has267 stage1 placebo joins with target=None. This is explicit unbound target custody, not silent negatives or permission to manufacture targets. W-lens must bind exact original registered placebo truth/position/property lineage plus J/E62 median population/RULES before scientific use; no R-Q inferred targets, outcome analysis, real author guard, controller/delivery entrypoint, process/API or ledger call. Existing source5348c18e8 review remains closed. Stage2/3 ongoing; ba2c220a7 scheduling-only amendment read at actual09:12:01CET, does not weaken complete-stage scientific eligibility. Original E87 reused codes remain a distinct lineage, not new judging.

Owner receipt arithmetic exact: known provider0.81624100 + retained unknown0.0452490625 + booked429 upper0 = booked0.8614900625 USD; lifetime bank60 remains open with later stages active. This checks sealed receipt arithmetic, not provider billing/current global allocation certification or full financial closure. Owner reports terminal08:55:39Z before15Z; reviewer has not certified first physical call/complete historical clock. No scientific result or deck claim follows from custody completion.

<details><summary>RQ_REPRO_E95_STAGE1_CUSTODY_V1</summary>

```python
import json,hashlib,pathlib,collections,decimal
W=pathlib.Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-r-q');P=W/'results/g_agreement/understand/blind_judge/e95_bank/complete_stage1';n=0
def rd(p):return json.loads(pathlib.Path(p).read_text())
def sh(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ck(p,h):
 global n
 assert sh(p)==h,str(p);n+=1
def seal(p,h=None):
 p=pathlib.Path(p)
 if h:ck(p,h)
 a=rd(p)
 for f,v in a.get('files',{}).items():ck(p.parent/f,v)
 return a
seal(P/'PUBLIC_SEAL.json');r=rd(P/'RECEIPT.json');d=pathlib.Path(r['private_delivery_seal']);s=seal(d,r['private_delivery_seal_sha256']);b=rd(d.parent/'SOURCE_BINDINGS.PRIVATE.json');jp=pathlib.Path(b['judgment_seal']);js=seal(jp,r['original_judgment_seal_sha256']);assert js['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS' and js['judging_stage']==1
ck(b['spec'],b['spec_sha256']);sp=rd(b['spec']);packet=pathlib.Path(sp['packet']);seal(packet/'PACKET_SEAL.json',sp['packet_seal_sha256'])
for k in ['source_seal','regex_audit','stage_inventory','route','custody_receipt','budget_receipt']:ck(b[k],b[k+'_sha256'])
counts=[]
for name,count in [('JUDGMENTS.json',609),('ORIGINAL_JUDGMENTS.json',151)]:
 original=rd(jp.parent/name);flat=rd(d.parent/name);assert len(original)==len(flat)==count and len({x['id'] for x in original})==count
 for x,y in zip(original,flat):
  assert x['id']==y['id'];assert x['status'] in ('KEPT','UNPARSEABLE')
  if x['status']=='KEPT':assert x['code']==y and x['code']['id']==x['id']
  else:assert x['code'] is None and y==dict(id=x['id'],category='UNPARSEABLE',values=[],evidence='',first_position=None)
 missing=sum(x['status']=='UNPARSEABLE' for x in original);counts.append([count,count-missing,missing])
 assert dict(collections.Counter(x['category'] for x in flat))==r['primary_categories' if count==609 else 'original_categories']
assert counts==[[609,548,61],[151,139,12]]
primary=rd(jp.parent/'JUDGMENTS.json');groups=rd(packet/'GROUPED_PACKET.json');joins=rd(packet/'PRIVATE_JOIN.json');linked=rd(d.parent/'JOIN.PRIVATE.json');assert {x['id'] for x in primary}=={x['id'] for x in groups}=={x['id'] for x in joins}
assert set(x['id'] for x in rd(jp.parent/'ORIGINAL_JUDGMENTS.json'))==set(rd(packet/'ORIGINAL_IDS.json'))
jmap={x['id']:x for x in joins}
for x in linked:
 q=dict(x);ptr=q.pop('judge_source');assert q==jmap[x['id']];assert ptr['seal']==str(jp) and ptr['sha256']==sh(jp) and ptr['member']=='JUDGMENTS.json';assert primary[ptr['keys'][0]]['id']==x['id'] and ptr['keys'][1]=='code'
cont=sp['continuation'];held=sp['preserved_missing'];assert len(held)==4 and held==cont['preserved_missing']
by={x['id']:x for x in primary}
for gid,rid in held.items():
 assert by[gid]['status']=='UNPARSEABLE' and by[gid]['code'] is None and by[gid]['terminal_reason']=='UNKNOWN_REQUEST_NO_REPLAY' and by[gid]['original_request_id']==rid
ledger=pathlib.Path(sp['ledger_root']);ck(ledger/'STAGE1_ONCE.json',cont['original_once_sha256']);seal(cont['previous_partial_seal'],cont['previous_partial_seal_sha256'])
e87=b['original_E87_reuse_lineage'];ck(e87['judgment_seal'],e87['judgment_seal_sha256']);ck(e87['private_join'],e87['private_join_sha256'])
cost=r['cumulative_E95_bank_cost'];D=decimal.Decimal;assert D(cost['known_provider_cost_usd'])+D(cost['booked_429_upper_bound_usd'])+D(cost['unknown_physical_reserve_usd'])==D(cost['booked_usd'])
summary=dict(status='PASS',hash_checks=n,terminal_counts=counts,literal_flat_copies=760,private_join_pointer_checks=len(linked),preserved_unknowns=len(held),unbound_placebo_targets=sum(x['arm']=='placebo' and x['target'] is None for x in linked),owner_reported_cost=cost,semantic_scoring=False,real_guards_invoked=False)
pathlib.Path('/tmp/rq_e95_stage1_custody_summary.json').write_text(json.dumps(summary,sort_keys=True));print(json.dumps(summary,sort_keys=True))
```
</details>


## 2026-10-30 — E71 independent primary review (8562cd524 human seal; bae102a33 agreement)

R-H1 NOT MET confirmed for Guiv: own κ(correct/wrong/other)=0.6822995461422088 versus worker0.682, below0.70; agreement53/63=0.8412698413. Oracle30 κ0.6815286624 and NLA33 κ0.6802325581 match rounded worker0.682/0.680. All three published confusion dictionaries, four-category κ and false-YES/NO counts reproduced from original hash-bound key and committed100 human codes, without any new human coding or rejudging. Coverage correction: 37 excluded =36 absent judge references +1 terminal UNPARSEABLE; not37 absent references. All100 ordered packet/code identities and original public packet property/value/readout joins exact; original keySHA0f647126 and packet9448fad9/rubric03d9377b/humancodesaa044402 match seals. Human-code commit8562 precedes joined-resultbae102; coding blindness/human authorship remain attested, not independently witnessed. Guiv's hypothesis/aggregate awareness disclosed by407d0e7bc. No second coder/interhuman agreement supplied.

CI reproduction remains QUALIFIED: independent2,000 item bootstrap, NumPy default_rng seed20261030, percentile2.5/97.5 gives overall[0.4822737804,0.8462026386], Oracle[0.3852037952,0.9285714286], NLA[0.3959886881,0.8910891089], versus published[0.487,0.847]/[0.385,0.930]/[0.396,0.921]. Published result states seed/draw count but supplies no executable bootstrap source/order/RNG contract; reviewer numbers are explicitly beside worker numbers, not silently substituted or claimed exact. Point verdict unchanged. Exact original bootstrap implementation and source-bound E104 spot-check judge key/sample receipt requested through own HANDOFF before CI/supplement closure.

False-YES here uses HUMAN non-states as denominator:8/40=.20; false-NO4/23=.173913; these are pooled sample diagnostics, not deployment-wide error guarantees. Separate exploratory E10440 sample (not E71) owner reports fact18/20 category agreement and language6/20; source-bound judge/sample lineage is still pending independent review. A balanced case-control spot-check cannot establish universal fact reliability, language-wide error rates or rescue near-zero bookkeeping/cue results by transferring pooled errors to those rows. Deck should retain judged-rate wording and scope uncertainty to the audited samples. No original E104 result recoded.

Registered >.15 row-level human-versus-judge S flags independently added below (known paired sample only; tiny row n, not full-row S estimates).

```json
[
  {
    "bank": "E56",
    "row": "adjective_asked",
    "reader": "oracle",
    "n": 3,
    "human_states": 0,
    "judge_states": 3,
    "difference": -1.0
  },
  {
    "bank": "E56",
    "row": "adjective_implicit",
    "reader": "oracle",
    "n": 2,
    "human_states": 0,
    "judge_states": 2,
    "difference": -1.0
  },
  {
    "bank": "E56",
    "row": "language_report",
    "reader": "nla",
    "n": 2,
    "human_states": 1,
    "judge_states": 2,
    "difference": -0.5
  },
  {
    "bank": "E56",
    "row": "linewrap_asked",
    "reader": "nla",
    "n": 2,
    "human_states": 0,
    "judge_states": 1,
    "difference": -0.5
  },
  {
    "bank": "E56",
    "row": "reasoning_bridge",
    "reader": "nla",
    "n": 2,
    "human_states": 1,
    "judge_states": 0,
    "difference": 0.5
  },
  {
    "bank": "E56",
    "row": "reasoning_bridge",
    "reader": "oracle",
    "n": 4,
    "human_states": 4,
    "judge_states": 1,
    "difference": 0.75
  },
  {
    "bank": "E56",
    "row": "rhyme_plan",
    "reader": "nla",
    "n": 5,
    "human_states": 0,
    "judge_states": 1,
    "difference": -0.2
  }
]
```

<details><summary>RQ_REPRO_E71_PRIMARY_V1</summary>

```python
import json,pathlib,hashlib,collections,numpy as np
from common.stats import wilson
R=pathlib.Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-r-q');B=R/'results/g_agreement/understand/e71/human_guiv_20261030';O=R.parent/'wt-blindspot-internals';P=O/'results/g_agreement/understand/e71/rebuild_24070152/human_packet';K=O/'cache/g_agreement/understand/e71/rebuild_24070152/KEY.DO_NOT_SHARE.json'
def rd(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=rd(P/'RESULT_SEAL.json');assert sha(K)==s['private_key_sha256']
for f,h in s['files'].items():assert sha(P/f)==h
hs=rd(B/'E71_SEAL.json');assert sha(P/'PACKET.html')==hs['packet_sha256'] and sha(P/'RUBRIC.md')==hs['rubric_sha256'] and sha(B/'E71_JUDGMENTS.jsonl')==hs['judgments_jsonl_sha256']
human=[json.loads(l) for l in (B/'E71_JUDGMENTS.jsonl').read_text().splitlines()];hm={x['id']:x for x in human};key=rd(K);packet=rd(P/'PACKET.json');assert [x['id']for x in human]==[x['id']for x in packet];assert {x['opaque_id']for x in key}==set(hm)
for x,p in zip(key,packet):assert p==dict(id=x['opaque_id'],property=x['property'],readout=x['readout'],values=x['values'])
def collapse(c,t):
 if c['category']!='states_value':return 'other'
 return 'correct' if c['values']==[t] else 'wrong' if c['values']==[('B'if t=='A'else'A')]else'other'
def kap(a,b):
 n=len(a);obs=sum(x==y for x,y in zip(a,b))/n;ca=collections.Counter(a);cb=collections.Counter(b);exp=sum(ca[k]*cb[k]for k in set(ca)|set(cb))/n**2
 return (obs-exp)/(1-exp) if exp<1 else float('nan')
known=[x for x in key if x['judge']and x['judge']['category']!='UNPARSEABLE'];assert len(known)==63
result={};worker=rd(B/'AGREEMENT.json')
for reader in ['all','oracle','nla']:
 rows=[x for x in known if reader=='all'or x['reader']==reader];a=[collapse(hm[x['opaque_id']],x['true_value'])for x in rows];b=[collapse(x['judge'],x['true_value'])for x in rows];rng=np.random.default_rng(20261030);draw=[]
 for i in range(2000):
  ix=rng.integers(0,len(rows),len(rows));draw.append(kap([a[j]for j in ix],[b[j]for j in ix]))
 ci=np.nanpercentile(draw,[2.5,97.5]);k=kap(a,b);conf=dict(collections.Counter(x+'|'+y for x,y in zip(a,b)));assert conf==worker[reader]['confusion_cww'];assert round(k,3)==worker[reader]['kappa_cww'];print('CI own vs worker',reader,ci.tolist(),worker[reader]['kappa_cww_CI'])
 ac=[hm[x['opaque_id']]['category']for x in rows];bc=[x['judge']['category']for x in rows];fy=sum(y=='states_value'and x!='states_value'for x,y in zip(ac,bc));non=sum(x!='states_value'for x in ac);fn=sum(y!='states_value'and x=='states_value'for x,y in zip(ac,bc));yes=sum(x=='states_value'for x in ac)
 assert f'{fy}/{non}'==worker[reader]['judge_states_human_not'] and f'{fn}/{yes}'==worker[reader]['judge_not_human_states'];assert round(kap(ac,bc),3)==worker[reader]['kappa_4cat']
 result[reader]=dict(n=len(rows),kappa=k,CI=ci.tolist(),agreement=sum(x==y for x,y in zip(a,b))/len(a),false_yes=[fy,non],false_no=[fn,yes])
flags=[]
for group in sorted({(x['bank'],x['row'],x['reader'])for x in known}):
 rows=[x for x in known if (x['bank'],x['row'],x['reader'])==group];h=sum(hm[x['opaque_id']]['category']=='states_value'for x in rows);j=sum(x['judge']['category']=='states_value'for x in rows)
 if abs(h-j)/len(rows)>.15:flags.append(dict(bank=group[0],row=group[1],reader=group[2],n=len(rows),human_states=h,judge_states=j,difference=(h-j)/len(rows)))
summary=dict(primary=result,missing=dict(no_reference=sum(x['judge']is None for x in key),terminal_unparseable=sum(bool(x['judge'])and x['judge']['category']=='UNPARSEABLE'for x in key)),registered_row_flags=flags)
pathlib.Path('/tmp/rq_e71_review_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
```
</details>


## 2026-10-30 — E71 estimator provenance received (b6cb30f07)

Original-source request CLOSED by source delivery: agreement.py SHA65455378 documents Python random.Random(20261030),2,000 paired item draws in original key order, undefined κ discarded and sorted-index endpoints int(.025*valid),int(.975*valid)-1. This explains why NumPy/default_rng/interpolated-percentile reproduction differs; both implementations and prior numeric differences remain explicit, with no overwritten result or exact-CI reproduction claim. Approximate overall interval[.48,.85] and point verdict NOT MET unchanged. Author source read only, not executed; closed point/custody/bootstrap computations not repeated. RESULT provenance now correctly distinguishes36 absent references+1 UNPARSEABLE and describes no-earlier-join as an attestation. The private key's code/reference availability and all prior source/coder scope caveats remain.

Exploratory E10440 sample/source-selection receipt remains separately pending R-Q source-bound review; R-2 owns its own completed check, not R-Q's unperformed sample audit. Source's e71x/SPOTCHECK_JUDGE_KEY_DO_NOT_OPEN.json and SPOTCHECK_PACKET.json are relative locators without a published immutable sample-binding receipt here. No request to recreate the sample or rerun judging. No transfer of pooled coder errors to other experimental rows or universal fact reliability is established.


## 2026-10-30 — E95 stage3 terminal custody COMPLETE (7ca34fefa)

Original delivery b5a4528be4525b664daa1ba11630d2a5293053b1b9348ec10eba4f25e853b8ae / terminal 6b039ab7bcd5ea76fca05340359c01d7cdd7d6cb5534d42a7c0d0619eb78489c: CUSTODY PASS. Own2,375 literal hash checks exact across original terminal members/public receipt/private four-member delivery/packet/bindings/distinct original E87 reuse pins;558 flattened kept-code/null copies exact and454 private source joins/indexed original judgment pointers exact. Own=owner primary454=364 KEPT+90 missing; original104=82 KEPT+22 missing; total558=446 KEPT+112 missing. Original frozen packet9df144d3 retained, no selection/refill/reparse/rejudge/semantic interpretation. Existing delivery helper tests remain closed unchanged, not repeated. No author entrypoint/real guard/process/API/ledger invoked.

205 original stage3 placebo target joins remain explicitlyNone, requiring genuine original registered truth/position/property binding by W-lens before scientific use, alongside J/E62 median population/RULES and final scientific seal. No target inferred by R-Q. Receipt arithmetic known2.86248450 + retained bank unknown0.0452490625 +429upper0 = booked2.9077335625 USD exact; owner cumulative financial receipt only, no provider/global financial certification or bank closure. Stage2 still active; stage3 terminal does not imply all E95 complete or an H-M1 result. Stage1 custody unchanged/closed. Source-before-opening/first physical history and scientific rules remain separate final review requirements.

<details><summary>RQ_REPRO_E95_STAGE3_CUSTODY_V1</summary>

```python
import json,hashlib,pathlib,collections,decimal
W=pathlib.Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-r-q');P=W/'results/g_agreement/understand/blind_judge/e95_bank/complete_stage3';n=0
def rd(p):return json.loads(pathlib.Path(p).read_text())
def sh(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ck(p,h):
 global n
 assert sh(p)==h,str(p);n+=1
def seal(p,h=None):
 p=pathlib.Path(p)
 if h:ck(p,h)
 a=rd(p)
 for f,v in a.get('files',{}).items():ck(p.parent/f,v)
 return a
seal(P/'PUBLIC_SEAL.json');r=rd(P/'RECEIPT.json');d=pathlib.Path(r['private_delivery_seal']);s=seal(d,r['private_delivery_seal_sha256']);b=rd(d.parent/'SOURCE_BINDINGS.PRIVATE.json');jp=pathlib.Path(b['judgment_seal']);js=seal(jp,r['original_judgment_seal_sha256']);assert js['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS' and js['judging_stage']==3
ck(b['spec'],b['spec_sha256']);sp=rd(b['spec']);packet=pathlib.Path(sp['packet']);seal(packet/'PACKET_SEAL.json',sp['packet_seal_sha256'])
for k in ['source_seal','regex_audit','stage_inventory','route','custody_receipt','budget_receipt']:ck(b[k],b[k+'_sha256'])
counts=[]
for name,count in [('JUDGMENTS.json',454),('ORIGINAL_JUDGMENTS.json',104)]:
 original=rd(jp.parent/name);flat=rd(d.parent/name);assert len(original)==len(flat)==count and len({x['id'] for x in original})==count
 for x,y in zip(original,flat):
  assert x['id']==y['id'];assert x['status'] in ('KEPT','UNPARSEABLE')
  if x['status']=='KEPT':assert x['code']==y and x['code']['id']==x['id']
  else:assert x['code'] is None and y==dict(id=x['id'],category='UNPARSEABLE',values=[],evidence='',first_position=None)
 missing=sum(x['status']=='UNPARSEABLE' for x in original);counts.append([count,count-missing,missing])
 assert dict(collections.Counter(x['category'] for x in flat))==r['primary_categories' if count==454 else 'original_categories']
assert sum(x[0] for x in counts)==558
primary=rd(jp.parent/'JUDGMENTS.json');groups=rd(packet/'GROUPED_PACKET.json');joins=rd(packet/'PRIVATE_JOIN.json');linked=rd(d.parent/'JOIN.PRIVATE.json');assert {x['id'] for x in primary}=={x['id'] for x in groups}=={x['id'] for x in joins}
assert set(x['id'] for x in rd(jp.parent/'ORIGINAL_JUDGMENTS.json'))==set(rd(packet/'ORIGINAL_IDS.json'))
jmap={x['id']:x for x in joins}
for x in linked:
 q=dict(x);ptr=q.pop('judge_source');assert q==jmap[x['id']];assert ptr['seal']==str(jp) and ptr['sha256']==sh(jp) and ptr['member']=='JUDGMENTS.json';assert primary[ptr['keys'][0]]['id']==x['id'] and ptr['keys'][1]=='code'
e87=b['original_E87_reuse_lineage'];ck(e87['judgment_seal'],e87['judgment_seal_sha256']);ck(e87['private_join'],e87['private_join_sha256'])
cost=r['cumulative_E95_bank_cost'];D=decimal.Decimal;assert D(cost['known_provider_cost_usd'])+D(cost['booked_429_upper_bound_usd'])+D(cost['unknown_physical_reserve_usd'])==D(cost['booked_usd'])
summary=dict(status='PASS',hash_checks=n,terminal_counts=counts,literal_flat_copies=558,private_join_pointer_checks=len(linked),unbound_placebo_targets=sum(x['arm']=='placebo' and x['target'] is None for x in linked),owner_reported_cost=cost,semantic_scoring=False,real_guards_invoked=False)
pathlib.Path('/tmp/rq_e95_stage3_custody_summary.json').write_text(json.dumps(summary,sort_keys=True));print(json.dumps(summary,sort_keys=True))
```
</details>


## 2026-10-30 — E100 descriptive Oracle transplant census COMPLETE (312621abc; seal588769fd)

Independent own=worker all49 category counts/seven exact84-item grids/seven saved-S identities PASS. Original analysis76b156f0/judgment879b3bba/blindaab8affe/targetsf1c97d68/descriptive588769fd seals and27 member hash checks exact; full6720code/private identity sets match;588 selected item/row/oracle/transplant/donor-target A/B/value-orientation joins exact. Categories counted from original sealed codes only, with both incompatible values retained separately and UNPARSEABLE missing. No human truth recoding, author entrypoint, original onceguard, judging, semantic reparse, bootstrap, CI or verdict replay. Source58794c14d read; author reports tested source before new census opening, which is not independent first-opening/earlier-history certification. Post hoc descriptive only; original E100 result/verdict unchanged.

| Row | Correct-only | Wrong-only | Both | Property-only | Exhibits | Silent | Missing |
|---|---:|---:|---:|---:|---:|---:|---:|
| nesting_depth | 3 | 2 | 0 | 0 | 11 | 64 | 4 |
| indent_level | 0 | 4 | 0 | 1 | 1 | 78 | 0 |
| page_range_digit | 10 | 10 | 7 | 1 | 0 | 56 | 0 |
| format_plan | 81 | 1 | 1 | 0 | 1 | 0 | 0 |
| fact_recall | 62 | 0 | 0 | 0 | 0 | 22 | 0 |
| tense_implicit | 51 | 0 | 0 | 0 | 14 | 13 | 6 |
| language_plan | 54 | 7 | 0 | 0 | 2 | 13 | 8 |

Every row totals84. S=(correct-only−wrong-only)/(84−missing), so both/property-only/exhibits/silent contribute zero to signed S. Nesting and indentation are predominantly originally coded silent64/84 and78/84; page-range zero S combines56/84 silent with10 correct-only−10 wrong-only and7 both. Zero signed S therefore does not by itself mean no value was reported. Content-row and language categories retain their original judged status; this census does not resolve the separate human-validation concerns. language_continuation is outside the seven requested rows.

<details><summary>RQ_REPRO_E100_DESCRIPTIVE_V1</summary>

```python
import pathlib,json,hashlib,collections
W=pathlib.Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-r-q');D=W/'results/g_agreement/understand/e100/analysis_once';n=0
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def check(p,h):
 global n
 assert sha(p)==h,str(p);n+=1
def seal(p,h):
 p=pathlib.Path(p);check(p,h);a=read(p)
 for name,v in a['files'].items():check(p.parent/name,v['sha256']if isinstance(v,dict)else v)
 return a
pub=read(D/'descriptive_categories/COUNTS.json');seal(D/'descriptive_categories/DESCRIPTIVE_SEAL.json','588769fdd0ebaf0ade02b3f02ff263bbb79fd003ae82c8acb8451723b57d4202')
a=seal(D/'ANALYSIS_SEAL.json',pub['original_analysis_seal_sha256']);s=read(W.parent/'wt-wmech2/cache/g_agreement/understand/e100/once_bound/SPEC.json')
jp=pathlib.Path(s['judgments']);j=seal(jp/'JUDGMENT_SEAL.json',a['judgment_sha256']);b=seal(pathlib.Path(s['blind'])/'BLIND_SEAL.json',j['blind_seal_sha256']);check(s['private'],b['private_sha256']);tp=pathlib.Path(s['targets_seal']);seal(tp,a['targets_sha256'])
t={x['id']:x for x in read(tp.parent/'TARGETS.json')};joins=read(s['private']);codes=read(jp/'JUDGMENTS.json');assert len(joins)==len(codes)==len({x['opaque_id']for x in joins})==len({x['id']for x in codes})==6720;c={x['id']:x for x in codes};assert set(c)=={x['opaque_id']for x in joins}
saved=read(D/'RESULTS.json');results={}
for row,w in pub['rows'].items():
 grid=[x for x in joins if (x['row'],x['reader'],x['condition'])==(row,'oracle','transplant')];assert len(grid)==len({x['item_id']for x in grid})==84;assert {x['item_id']for x in grid}=={x['id']for x in t.values()if x['row']==row};count=dict.fromkeys(['correct-only','wrong-only','both','property-only','exhibits','silent','missing'],0)
 for x in grid:
  target=t[x['item_id']];assert x['target']==target['target'] and x['values']==target['values'] and x['id']==x['item_id']+':oracle:transplant';code=c[x['opaque_id']];cat=code['category'];vals=set(code['values'])
  if cat=='UNPARSEABLE':assert not vals;label='missing'
  elif cat=='states_value':
   assert vals in ({'A'},{'B'},{'A','B'});label='both' if len(vals)==2 else 'correct-only'if target['target']in vals else'wrong-only'
  else:assert not vals;label={'silent':'silent','exhibits':'exhibits','names_property_without_value':'property-only'}[cat]
  count[label]+=1
 est=(count['correct-only']-count['wrong-only'])/(84-count['missing']);assert all(count[k]==w[k]for k in count)and sum(count.values())==84;assert est==w['saved_S'] and abs(est-saved['rows'][row]['oracle']['transplant']['estimate'])<1e-12;results[row]=count
print(json.dumps(dict(status='PASS',hash_checks=n,category_fields=49,row_grids=7,item_orientation_joins=588,saved_S_identities=7,rows=results)));pathlib.Path('/tmp/rq_e100_census_summary.json').write_text(json.dumps(dict(hash_checks=n,rows=results)))
```
</details>


## 2026-10-30 — E95 stage2 and final judging custody COMPLETE (fa8653297/45b6026c7/8e184c447)

Original stage2 delivery0875911e1dedd497197bf1201333000a4eeccd173f53aac7f27e37f052ce6ebf / terminal117d3b286be021adef0bb439b53f90151d9a01d9ebcb11aaa86e2aa0140b68cc CUSTODY PASS:5,993 hash checks exact;1,626 flattened original kept-code/null copies and1,294 original private-join/index pointers exact. Primary1,294=1,145KEPT+149missing; original332=300KEPT+32missing; total1,626=1,445KEPT+181missing. Original packet18aaac19 unchanged.554 stage2 placebo target joins explicitlyNone, retained without invented truth. No reparse/rejudge/semantic scoring, production adapter/real guard/process/API/ledger invoked; unchanged helper tests not repeated. Stage1/3 previously closed custody not rerun.

New final receipt a68c6e44 / terminal bank528d6e13 hashes and all3 public stage-receipt links match original delivered seals. Aggregate2,944 groups=2,357 primary+587 original-rubric comparisons;2,578KEPT+366missing exact. Original4 unknown physical reservations retained. Owner reports all3 completed before15Z, last stage2 at13:04:43Z, paid workers/supervisor exited and judging heartbeat removed; these process/clock claims are operational receipts, not independently witnessed historical process certification. Sealed arithmetic known3.19809500+unknown.0452490625+429upper0=booked3.2433440625; booked+unused56.7566559375=original60. Administrative RELEASED/global snapshot and one-time unused release remain owner financial metadata, not R-Q billing/global ledger certification.

All staged JUDGING custody now complete; E95 scientific analysis remains pending. W-lens must bind original placebo truth/position/property sources (1,026 target=None joins across three primary packets), exact J/E62 population/RULES and final source/seal before scientific use. No target inference by R-Q, H-M1 verdict, causal conclusion or scientific completion inferred from terminal judging. Original E87 reuse stays distinct.

<details><summary>RQ_REPRO_E95_STAGE2_CUSTODY_V1</summary>

```python
import json,hashlib,pathlib,collections,decimal
W=pathlib.Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-r-q');P=W/'results/g_agreement/understand/blind_judge/e95_bank/complete_stage2';n=0
def rd(p):return json.loads(pathlib.Path(p).read_text())
def sh(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ck(p,h):
 global n
 assert sh(p)==h,str(p);n+=1
def seal(p,h=None):
 p=pathlib.Path(p)
 if h:ck(p,h)
 a=rd(p)
 for f,v in a.get('files',{}).items():ck(p.parent/f,v)
 return a
seal(P/'PUBLIC_SEAL.json');r=rd(P/'RECEIPT.json');d=pathlib.Path(r['private_delivery_seal']);s=seal(d,r['private_delivery_seal_sha256']);b=rd(d.parent/'SOURCE_BINDINGS.PRIVATE.json');jp=pathlib.Path(b['judgment_seal']);js=seal(jp,r['original_judgment_seal_sha256']);assert js['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS' and js['judging_stage']==2
ck(b['spec'],b['spec_sha256']);sp=rd(b['spec']);packet=pathlib.Path(sp['packet']);seal(packet/'PACKET_SEAL.json',sp['packet_seal_sha256'])
for k in ['source_seal','regex_audit','stage_inventory','route','custody_receipt','budget_receipt']:ck(b[k],b[k+'_sha256'])
counts=[]
for name,count in [('JUDGMENTS.json',1294),('ORIGINAL_JUDGMENTS.json',332)]:
 original=rd(jp.parent/name);flat=rd(d.parent/name);assert len(original)==len(flat)==count and len({x['id'] for x in original})==count
 for x,y in zip(original,flat):
  assert x['id']==y['id'];assert x['status'] in ('KEPT','UNPARSEABLE')
  if x['status']=='KEPT':assert x['code']==y and x['code']['id']==x['id']
  else:assert x['code'] is None and y==dict(id=x['id'],category='UNPARSEABLE',values=[],evidence='',first_position=None)
 missing=sum(x['status']=='UNPARSEABLE' for x in original);counts.append([count,count-missing,missing])
 assert dict(collections.Counter(x['category'] for x in flat))==r['primary_categories' if count==1294 else 'original_categories']
assert sum(x[0] for x in counts)==1626
primary=rd(jp.parent/'JUDGMENTS.json');groups=rd(packet/'GROUPED_PACKET.json');joins=rd(packet/'PRIVATE_JOIN.json');linked=rd(d.parent/'JOIN.PRIVATE.json');assert {x['id'] for x in primary}=={x['id'] for x in groups}=={x['id'] for x in joins}
assert set(x['id'] for x in rd(jp.parent/'ORIGINAL_JUDGMENTS.json'))==set(rd(packet/'ORIGINAL_IDS.json'))
jmap={x['id']:x for x in joins}
for x in linked:
 q=dict(x);ptr=q.pop('judge_source');assert q==jmap[x['id']];assert ptr['seal']==str(jp) and ptr['sha256']==sh(jp) and ptr['member']=='JUDGMENTS.json';assert primary[ptr['keys'][0]]['id']==x['id'] and ptr['keys'][1]=='code'
e87=b['original_E87_reuse_lineage'];ck(e87['judgment_seal'],e87['judgment_seal_sha256']);ck(e87['private_join'],e87['private_join_sha256'])
cost=r['cumulative_E95_bank_cost'];D=decimal.Decimal;assert D(cost['known_provider_cost_usd'])+D(cost['booked_429_upper_bound_usd'])+D(cost['unknown_physical_reserve_usd'])==D(cost['booked_usd'])
summary=dict(status='PASS',hash_checks=n,terminal_counts=counts,literal_flat_copies=1626,private_join_pointer_checks=len(linked),unbound_placebo_targets=sum(x['arm']=='placebo' and x['target'] is None for x in linked),owner_reported_cost=cost,semantic_scoring=False,real_guards_invoked=False)
pathlib.Path('/tmp/rq_e95_stage2_custody_summary.json').write_text(json.dumps(summary,sort_keys=True));print(json.dumps(summary,sort_keys=True))
```
</details>


## E95 binding deadline disposition — 2026-10-30 15:39Z

R-Q applies Guiv's canonical E95 deadline ruling `839b11162` (actual commit 13:44:08Z, nominal heading 14:50 CET): “If any is missing at 16:30, H-M1 is NOT EVALUABLE on the parts that need it”. The cutoff is **16:30 CET = 15:30Z**. At shared publication `9aff7e3aa`, after that cutoff, no replacement or complete original binding certification has arrived.

| Rule | Own review / owner record | Disposition |
|---|---|---|
| All three original bindings certified by 15:30Z | Own publication check: no complete certification through `9aff7e3aa`; Track Q `78bce0d0c`, certification SHA `5b593bf594adaf76e01c32b460a40b3cc021486c208ee60f3e374309c096d916` and four member hashes independently exact at intake. Owner certification remains PARTIAL for placebo targets and NOT FOUND for original map operator/threshold and placebo-corrected single-site verdicts. | **H-M1 NOT EVALUABLE on the parts requiring those bindings**, under `839b11162`; this is a missing-binding disposition, not a negative measured H-M1 result. |
| No reconstructed targets or substitute rule | Original E95 custody already independently closed: 1,026 primary placebo groups have target None (267 + 554 + 205). Track Q reports no original target/source-item/truth assignments for those pseudo-items. Ten E87-reuse rows are separate lineage; E96 uncorrected greedy statuses cannot supply the missing placebo-corrected verdict. | Preserve original missingness and source identity; no inferred labels, threshold or map verdict. Closed custody checks were not repeated. |
| Permitted fallback | Canonical ruling permits exploratory, descriptive **non-placebo** naming counts per stage and layer, with missing counts and no map verdict. Track Q reports J available for 69/72 rows, E62 reference population 25 non-null rows, median 0.025462539008930134; these numeric source claims are intake, not a new independent J audit. | W-Lens fallback source/output seal remains **PENDING**; no fallback numerical review or full E95 scientific completion claimed. Registered analysis source/guard not invoked by R-Q. |

This closes the deadline decision only. All original judging seals, once guards, prior custody reviews and financial qualifications remain unchanged. No worker entrypoint, parser, paid call, process or ledger action. E71 exploratory 40-item immutable sample-binding receipt remains separately pending; no duplicate request.
