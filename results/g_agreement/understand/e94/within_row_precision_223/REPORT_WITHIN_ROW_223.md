# E94 reader agreement

CPU only; no new readouts or judgments. Conditional precision excludes both-no-mention agreements. All comparisons use the same common-parseable items; missing and unmatched counts are in RESULTS.json. E67 is a separate claim diagnostic, not shared-value agreement.

| Bank | Paired n | Agreement | Correct given decisive agreement | Ensemble coverage | Oracle accuracy | NLA accuracy |
|---|---:|---:|---:|---:|---:|---:|
| E56 | 1091 | 0.6508 | 0.9672 | 0.2236 | 0.4262 | 0.3089 |
| E57 | 1641 | 0.7556 | 0.9261 | 0.1402 | 0.2072 | 0.2267 |
| E59 | 480 | 0.7875 | 0.9390 | 0.6833 | 0.7333 | 0.7250 |
| E62 | 0 | N/E | N/E | N/E | N/E | N/E |
| E67_wave1 | 598 | 0.5870 | 0.0085 | 0.5870 | 0.3261 | 0.0368 |
| E67_wave2 | 400 | 0.6550 | 0.0191 | 0.6550 | 0.2475 | 0.0375 |
| E73 | 1101 | 0.6776 | 0.9347 | 0.1807 | 0.2589 | 0.3015 |
| POOLED value-grounded | 4313 | 0.7127 | 0.9421 | 0.2321 | 0.3343 | 0.3220 |

H-A1 (pre-stated hypothesis, not a decision rule): **MET**, difference 0.6077198942953638; descriptive paired cluster-bootstrap 95% CI [0.5897563454891208, 0.6259484247789372].

Unavailable paired banks:
- E62: Oracle-only native acquisition; no shared Oracle/NLA judged item grid.
- E76: No sealed judged analysis/terminal delivered at source freeze; registered placebo agreement NOT EVALUABLE.

Per-bank/stratum confusion matrices, who is right on disagreements, reader precision/coverage, Wilson intervals and denominator audits are in RESULTS.json. Provisional scoring conventions and the incompatible E67 rubric are documented in METHOD.20261028.md. No sealed bank verdict is modified.

## §223 item3: within-row agreement precision and coverage

Report-only projection of the original sealed E94 aggregates. Agreement precision is correct / decisive same-value agreements; both-no-mention agreements are excluded. Coverage is decisive same-value agreements / common-parseable paired items, within the same row. Zero decisive agreements give N/E precision. Pooled metrics above are unchanged.

Within-row reporting removes selection between rows from the pooled comparison; it does not control unmeasured difficulty within a row. Wilson95 intervals and denominators are shown. The original missing/unmatched rules remain unchanged.

| Bank | Row | Paired n | Correct / decisive agreements | Precision | Wilson95 | Coverage |
|---|---|---:|---:|---:|---|---:|
| E56 | adjective_asked | 83 | 0/0 | N/E | N/E | 0.0000 |
| E56 | adjective_implicit | 71 | 9/9 | 1.0000 | [0.7009, 1.0000] | 0.1268 |
| E56 | anomaly_state | 78 | 0/0 | N/E | N/E | 0.0000 |
| E56 | fact_recall | 84 | 45/45 | 1.0000 | [0.9213, 1.0000] | 0.5357 |
| E56 | injection / json_status / J | 2 | 2/2 | 1.0000 | [0.3424, 1.0000] | 1.0000 |
| E56 | injection / json_status / full | 2 | 2/2 | 1.0000 | [0.3424, 1.0000] | 1.0000 |
| E56 | injection / json_status / nonJ | 2 | 2/2 | 1.0000 | [0.3424, 1.0000] | 1.0000 |
| E56 | injection / list_topic / J | 2 | 1/1 | 1.0000 | [0.2065, 1.0000] | 0.5000 |
| E56 | injection / list_topic / full | 2 | 2/2 | 1.0000 | [0.3424, 1.0000] | 1.0000 |
| E56 | injection / list_topic / nonJ | 2 | 1/1 | 1.0000 | [0.2065, 1.0000] | 0.5000 |
| E56 | injection / prose_sentiment / J | 2 | 2/2 | 1.0000 | [0.3424, 1.0000] | 1.0000 |
| E56 | injection / prose_sentiment / full | 2 | 2/2 | 1.0000 | [0.3424, 1.0000] | 1.0000 |
| E56 | injection / prose_sentiment / nonJ | 2 | 2/2 | 1.0000 | [0.3424, 1.0000] | 1.0000 |
| E56 | injection / prose_topic / J | 2 | 2/2 | 1.0000 | [0.3424, 1.0000] | 1.0000 |
| E56 | injection / prose_topic / full | 2 | 1/1 | 1.0000 | [0.2065, 1.0000] | 0.5000 |
| E56 | injection / prose_topic / nonJ | 2 | 0/0 | N/E | N/E | 0.0000 |
| E56 | injection / python_error / J | 2 | 1/1 | 1.0000 | [0.2065, 1.0000] | 0.5000 |
| E56 | injection / python_error / full | 2 | 2/2 | 1.0000 | [0.3424, 1.0000] | 1.0000 |
| E56 | injection / python_error / nonJ | 2 | 1/1 | 1.0000 | [0.2065, 1.0000] | 0.5000 |
| E56 | injection / table_status / J | 2 | 1/1 | 1.0000 | [0.2065, 1.0000] | 0.5000 |
| E56 | injection / table_status / full | 2 | 0/0 | N/E | N/E | 0.0000 |
| E56 | injection / table_status / nonJ | 2 | 1/1 | 1.0000 | [0.2065, 1.0000] | 0.5000 |
| E56 | instructed_focus | 84 | 1/2 | 0.5000 | [0.0945, 0.9055] | 0.0238 |
| E56 | language_continuation | 75 | 42/42 | 1.0000 | [0.9162, 1.0000] | 0.5600 |
| E56 | language_report | 84 | 37/37 | 1.0000 | [0.9059, 1.0000] | 0.4405 |
| E56 | linewrap_asked | 84 | 0/0 | N/E | N/E | 0.0000 |
| E56 | linewrap_implicit | 83 | 0/0 | N/E | N/E | 0.0000 |
| E56 | reasoning_bridge | 84 | 11/13 | 0.8462 | [0.5777, 0.9567] | 0.1548 |
| E56 | rhyme_plan | 84 | 14/14 | 1.0000 | [0.7847, 1.0000] | 0.1667 |
| E56 | tense_asked | 84 | 39/44 | 0.8864 | [0.7602, 0.9505] | 0.5238 |
| E56 | tense_implicit | 77 | 13/13 | 1.0000 | [0.7719, 1.0000] | 0.1688 |
| E57 | antonym_crosslingual | 84 | 0/0 | N/E | N/E | 0.0000 |
| E57 | capacity_list | 75 | 0/0 | N/E | N/E | 0.0000 |
| E57 | category_switch | 82 | 36/37 | 0.9730 | [0.8618, 0.9952] | 0.4512 |
| E57 | clause_pending | 81 | 19/20 | 0.9500 | [0.7639, 0.9911] | 0.2469 |
| E57 | count_gradient_first_letter | 84 | 0/1 | 0.0000 | [0.0000, 0.7935] | 0.0119 |
| E57 | focus_ignore | 84 | 5/5 | 1.0000 | [0.5655, 1.0000] | 0.0595 |
| E57 | focus_mention | 84 | 5/5 | 1.0000 | [0.5655, 1.0000] | 0.0595 |
| E57 | focus_none | 84 | 0/0 | N/E | N/E | 0.0000 |
| E57 | focus_think | 84 | 15/15 | 1.0000 | [0.7961, 1.0000] | 0.1786 |
| E57 | indent_level | 84 | 0/0 | N/E | N/E | 0.0000 |
| E57 | linewrap_asked | 84 | 0/0 | N/E | N/E | 0.0000 |
| E57 | linewrap_implicit | 84 | 0/0 | N/E | N/E | 0.0000 |
| E57 | loop_direction | 78 | 25/25 | 1.0000 | [0.8668, 1.0000] | 0.3205 |
| E57 | multi_token_entity | 84 | 22/22 | 1.0000 | [0.8513, 1.0000] | 0.2619 |
| E57 | nesting_depth | 73 | 2/2 | 1.0000 | [0.3424, 1.0000] | 0.0274 |
| E57 | page_range_digit | 84 | 0/0 | N/E | N/E | 0.0000 |
| E57 | section_header | 80 | 23/37 | 0.6216 | [0.4610, 0.7594] | 0.4625 |
| E57 | sentiment_judgement | 84 | 44/44 | 1.0000 | [0.9197, 1.0000] | 0.5238 |
| E57 | subject_number | 82 | 6/6 | 1.0000 | [0.6097, 1.0000] | 0.0732 |
| E57 | two_hop_answer | 82 | 11/11 | 1.0000 | [0.7412, 1.0000] | 0.1341 |
| E59 | decline_plan | 79 | 32/50 | 0.6400 | [0.5014, 0.7586] | 0.6329 |
| E59 | format_plan | 83 | 75/75 | 1.0000 | [0.9513, 1.0000] | 0.9036 |
| E59 | hedge_plan | 83 | 80/80 | 1.0000 | [0.9542, 1.0000] | 0.9639 |
| E59 | language_plan | 76 | 38/40 | 0.9500 | [0.8350, 0.9862] | 0.5263 |
| E59 | length_plan | 75 | 39/39 | 1.0000 | [0.9103, 1.0000] | 0.5200 |
| E59 | stance_plan | 84 | 44/44 | 1.0000 | [0.9197, 1.0000] | 0.5238 |
| E62 | S1_L0 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S1_L1 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S1_L2 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S1_L3 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S1_L4 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S2_L0 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S2_L1 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S2_L2 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S2_L3 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S2_L4 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S3_L0 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S3_L1 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S3_L2 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S3_L3 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S3_L4 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S4_L0 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S4_L1 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S4_L2 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S4_L3 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S4_L4 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S5_L0 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S5_L1 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S5_L2 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S5_L3 | 0 | 0/0 | N/E | N/E | N/E |
| E62 | S5_L4 | 0 | 0/0 | N/E | N/E | N/E |
| E73 | controls / W7 | 94 | 78/79 | 0.9873 | [0.9317, 0.9978] | 0.8404 |
| E73 | controls / W8 | 178 | 82/82 | 1.0000 | [0.9552, 1.0000] | 0.4607 |
| E73 | structural / W1 | 153 | 16/25 | 0.6400 | [0.4452, 0.7975] | 0.1634 |
| E73 | structural / W2 | 164 | 4/5 | 0.8000 | [0.3755, 0.9638] | 0.0305 |
| E73 | structural / W3 | 158 | 0/0 | N/E | N/E | 0.0000 |
| E73 | structural / W4 | 157 | 4/5 | 0.8000 | [0.3755, 0.9638] | 0.0318 |
| E73 | structural / W5 | 197 | 2/3 | 0.6667 | [0.2077, 0.9385] | 0.0152 |

### Separate E67 claim diagnostics

E67 uses an incompatible claim rubric and remains excluded from the value-grounded pool. Its diagnostic rows aggregate condition/arm strata while omitting private prompt-item IDs and hashes. These figures are not shared-value agreement precision.

| Bank | Condition/arm diagnostic row | Paired n | Correct / decisive agreements | Diagnostic precision | Wilson95 | Coverage |
|---|---|---:|---:|---:|---|---:|
| E67_wave1 | wave1 / D4 / matched / ignore | 33 | 0/7 | 0.0000 | [0.0000, 0.3543] | 0.2121 |
| E67_wave1 | wave1 / D4 / matched / none | 33 | 0/16 | 0.0000 | [0.0000, 0.1936] | 0.4848 |
| E67_wave1 | wave1 / D4 / matched / think | 33 | 0/16 | 0.0000 | [0.0000, 0.1936] | 0.4848 |
| E67_wave1 | wave1 / D4 / mismatched / ignore | 36 | 0/15 | 0.0000 | [0.0000, 0.2039] | 0.4167 |
| E67_wave1 | wave1 / D4 / mismatched / none | 27 | 1/12 | 0.0833 | [0.0149, 0.3539] | 0.4444 |
| E67_wave1 | wave1 / D4 / mismatched / think | 36 | 0/17 | 0.0000 | [0.0000, 0.1843] | 0.4722 |
| E67_wave1 | wave1 / E49 / matched / None | 100 | 1/67 | 0.0149 | [0.0026, 0.0798] | 0.6700 |
| E67_wave1 | wave1 / E49 / mismatched / None | 100 | 1/71 | 0.0141 | [0.0025, 0.0756] | 0.7100 |
| E67_wave1 | wave1 / E54 / matched / None | 100 | 0/60 | 0.0000 | [0.0000, 0.0602] | 0.6000 |
| E67_wave1 | wave1 / E54 / mismatched / None | 100 | 0/70 | 0.0000 | [0.0000, 0.0520] | 0.7000 |
| E67_wave2 | wave2 / E56 / matched / None | 100 | 4/63 | 0.0635 | [0.0250, 0.1522] | 0.6300 |
| E67_wave2 | wave2 / E56 / mismatched / None | 100 | 0/68 | 0.0000 | [0.0000, 0.0535] | 0.6800 |
| E67_wave2 | wave2 / E57 / matched / None | 100 | 1/60 | 0.0167 | [0.0029, 0.0886] | 0.6000 |
| E67_wave2 | wave2 / E57 / mismatched / None | 100 | 0/71 | 0.0000 | [0.0000, 0.0513] | 0.7100 |

The original E76 placebo-unavailability caveat at this source freeze remains separate; this projection does not claim completion of the full §214 item8 placebo extension. No sealed bank verdict or original analysis output was changed.
