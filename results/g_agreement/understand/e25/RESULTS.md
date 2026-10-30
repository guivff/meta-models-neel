# E25 — continuation plausibility

Prediction: Oracle ρ(P) ≥ 0.50 with a positive CI, and content plausibility exceeds structure with a positive CI.
The exploratory prediction did not hold.

Dated analysis: 2026-10-25T10:55:57+01:00. CPU only; sealed scores verified before labels were read.

Mean the true candidate's two frozen W1 phrasing scores per item, then take the row median.

D: AUROC of s_A - s_B with W1 value A positive; s_A and s_B each average the two frozen W1 phrasing scores. Defined by §119 dated clarification 1, commit e4225a1e.

| Predictor | Oracle ρ [95% CI] | NLA ρ [95% CI] | Probe ρ [95% CI] |
|---|---|---|---|
| P | 0.0340 [-0.3992, 0.4663] | -0.0600 [-0.5328, 0.3998] | 0.1289 [-0.1532, 0.4137] |
| D | 0.7516 [0.4982, 0.8775] | 0.7051 [0.3721, 0.8935] | -0.1451 [-0.4750, 0.3179] |

Content minus structure median P: 0.1315; 95% CI [-1.188014268875122, 0.5117988526821098].
The full JSON retains paired Oracle-minus-NLA/probe correlation differences and undefined bootstrap counts.
E21’s ρ = 0.48 is a descriptive comparison only.

| Row | Class | P | D | Oracle | NLA | Probe |
|---|---|---:|---:|---:|---:|---:|
| json_status | semantic | -5.1699 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| json_type | structure | -4.8168 | 0.7670 | 0.6599 | 0.8827 | 1.0000 |
| latex_environment | structure | -6.5395 | 1.0000 | 0.5709 | 0.6780 | 0.9427 |
| latex_role | semantic | -5.4845 | 0.7812 | 0.8435 | 0.9490 | 0.9722 |
| latex_section | structure | -6.5025 | 0.4615 | 0.4325 | 0.8759 | 1.0000 |
| latex_subject | semantic | -6.5464 | 1.0000 | 1.0000 | 0.9994 | 1.0000 |
| list_depth | structure | -4.5076 | 0.8163 | 0.6338 | 0.6514 | 1.0000 |
| list_index | structure | -5.4776 | 0.4076 | 0.4189 | 0.6689 | 0.9994 |
| list_priority | semantic | -4.8541 | 1.0000 | 0.8906 | 1.0000 | 1.0000 |
| list_topic | semantic | -5.6139 | 1.0000 | 0.9677 | 0.9881 | 0.8634 |
| prose_paren | structure | -5.8551 | 0.7183 | 0.4847 | 0.7438 | 1.0000 |
| prose_quote | structure | -5.8411 | 0.5958 | 0.5629 | 0.6803 | 1.0000 |
| prose_sentence | structure | -5.2647 | 0.1122 | 0.5312 | 0.6088 | 1.0000 |
| prose_sentiment | semantic | -5.3547 | 1.0000 | 0.9110 | 1.0000 | 1.0000 |
| prose_topic | semantic | -6.7662 | 1.0000 | 1.0000 | 0.9892 | 1.0000 |
| python_argument | structure | -4.8804 | 0.1247 | 0.5000 | 0.6587 | 1.0000 |
| python_comment | structure | -5.7543 | 0.8231 | 0.5425 | 0.7205 | 1.0000 |
| python_depth | structure | -6.5610 | 0.7086 | 0.4875 | 0.7307 | 1.0000 |
| python_error | semantic | -6.8839 | 0.9994 | 1.0000 | 0.9938 | 1.0000 |
| python_indent | structure | -5.3932 | 0.8039 | 0.5918 | 0.6740 | 1.0000 |
| python_string | structure | -5.3584 | 0.5204 | 0.6440 | 0.9853 | 1.0000 |
| table_column | structure | -5.8124 | 0.3095 | 0.4745 | 0.5680 | 1.0000 |
| table_role | structure | -5.3564 | 0.9093 | 0.4382 | 0.9734 | 1.0000 |
| table_row | structure | -5.9882 | 0.5720 | 0.5006 | 0.8186 | 1.0000 |
| table_status | semantic | -5.3602 | 1.0000 | 1.0000 | 0.9563 | 1.0000 |

Interpretation choices: {"D_definition": "AUROC(s_A-s_B,value_is_A)", "clarification_commit": "e4225a1e", "integrator_acknowledged": true, "phrasing_aggregation": "mean_of_two_W1_pairs"}

- Only 25 rows; bootstrap resamples rows, not items or W1 score uncertainty.
- Constant rank vectors produce undefined correlations; no finite value is substituted.
- Candidate preference common to both label classes yields D=0.5, even if one description is generally more plausible.
