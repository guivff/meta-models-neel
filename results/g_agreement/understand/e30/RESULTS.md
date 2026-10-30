Prediction: a partial value-word effect, short of R2’s reframing threshold.

R0: True; R2: UNINTERPRETABLE_CONTROL_FAILED; R3: False.
Primary structure median: 0.6076; raw R1 count: 6/16.

Control-failed rows: list_depth, python_indent, latex_fraction.

W1’s baseline and the new value-word candidates are both bullets. This is a descriptions-versus-value-words comparison. All rows and controls remain in summary.json; failed controls are not dropped. Three optional LaTeX rows are descriptive extras, outside the fixed16/9primary denominators.

| Row | W1 descriptive | Value words | Δ (95% CI) | Random control |
|---|---:|---:|---|---|
| json_type | 0.6593 | 0.4960 | -0.1633 [-0.2626, -0.0833] | CONTROL_PASSED |
| latex_environment | 0.5782 | 0.5573 | -0.0210 [-0.2268, +0.0931] | CONTROL_PASSED |
| latex_section | 0.4478 | 0.9337 | +0.4858 [+0.3685, +0.5663] | CONTROL_PASSED |
| list_depth | 0.6332 | 0.6244 | -0.0088 [-0.2188, +0.1193] | CONTROL_FAILED |
| list_index | 0.4252 | 0.5116 | +0.0865 [-0.2336, +0.3447] | CONTROL_PASSED |
| prose_paren | 0.4745 | 0.4677 | -0.0068 [-0.1786, +0.0794] | CONTROL_PASSED |
| prose_quote | 0.5618 | 0.5533 | -0.0085 [-0.2466, +0.3311] | CONTROL_PASSED |
| prose_sentence | 0.5238 | 0.7588 | +0.2350 [-0.0020, +0.4371] | CONTROL_PASSED |
| python_argument | 0.5068 | 1.0000 | +0.4932 [+0.3837, +0.5919] | CONTROL_PASSED |
| python_comment | 0.5425 | 0.6933 | +0.1508 [+0.0748, +0.2342] | CONTROL_PASSED |
| python_depth | 0.4932 | 0.6825 | +0.1893 [+0.1255, +0.2523] | CONTROL_PASSED |
| python_indent | 0.5884 | 0.5493 | -0.0391 [-0.3152, +0.1803] | CONTROL_FAILED |
| python_string | 0.6417 | 0.5907 | -0.0510 [-0.2018, +0.0799] | CONTROL_PASSED |
| table_column | 0.4762 | 0.8234 | +0.3472 [+0.1695, +0.5664] | CONTROL_PASSED |
| table_role | 0.4388 | 0.3770 | -0.0618 [-0.1944, +0.0578] | CONTROL_PASSED |
| table_row | 0.5000 | 0.9722 | +0.4722 [+0.3741, +0.5816] | CONTROL_PASSED |
| json_status | 1.0000 | 1.0000 | +0.0000 [+0.0000, +0.0000] | CONTROL_PASSED |
| latex_role | 0.8452 | 0.9535 | +0.1083 [-0.0289, +0.2874] | CONTROL_PASSED |
| latex_subject | 1.0000 | 0.8469 | -0.1531 [-0.3564, +0.0000] | CONTROL_PASSED |
| list_priority | 0.8929 | 1.0000 | +0.1071 [+0.0000, +0.3912] | CONTROL_PASSED |
| list_topic | 0.9683 | 1.0000 | +0.0317 [+0.0000, +0.1193] | CONTROL_PASSED |
| prose_sentiment | 0.9099 | 0.9918 | +0.0819 [-0.0323, +0.3793] | CONTROL_PASSED |
| prose_topic | 1.0000 | 1.0000 | +0.0000 [+0.0000, +0.0000] | CONTROL_PASSED |
| python_error | 1.0000 | 1.0000 | +0.0000 [+0.0000, +0.0000] | CONTROL_PASSED |
| table_status | 1.0000 | 1.0000 | +0.0000 [+0.0000, +0.0000] | CONTROL_PASSED |
| latex_fraction | 0.9615 | 0.9110 | -0.0505 [-0.1185, +0.0023] | CONTROL_FAILED |
| latex_item | 0.8741 | 0.6182 | -0.2560 [-0.4223, -0.0351] | CONTROL_PASSED |
| latex_math | 1.0000 | 0.4116 | -0.5884 [-0.7222, -0.4354] | CONTROL_PASSED |

E15 comparison (descriptive; no new threshold):

| Row | E30 raw R1 | E15 Oracle continuation AUROC |
|---|---|---:|
| json_type | False | NOT_REGISTERED_IN_E15 |
| latex_environment | False | NOT_REGISTERED_IN_E15 |
| latex_section | True | NOT_REGISTERED_IN_E15 |
| list_depth | False | 0.31802721088435376 |
| list_index | False | NOT_REGISTERED_IN_E15 |
| prose_paren | False | 0.7125850340136054 |
| prose_quote | False | 0.7970521541950113 |
| prose_sentence | False | NOT_REGISTERED_IN_E15 |
| python_argument | True | NOT_REGISTERED_IN_E15 |
| python_comment | True | NOT_REGISTERED_IN_E15 |
| python_depth | True | 0.8180272108843537 |
| python_indent | False | 0.7817460317460317 |
| python_string | False | 0.9149659863945578 |
| table_column | True | PRIMARY |
| table_role | False | 0.8171768707482994 |
| table_row | True | NOT_REGISTERED_IN_E15 |
| latex_fraction | False | NOT_REGISTERED_IN_E15 |
| latex_item | False | NOT_REGISTERED_IN_E15 |
| latex_math | False | NOT_REGISTERED_IN_E15 |

Deviation: authorized §138 item 1 (`6d86c23b`), validator-only tolerance 1e-5. Failed first invocation preserved in `5829fb92`; one authorized re-invocation, same sealed scores. See DEVIATION_138.md.

Analysis seal SHA256: `02670e70385c87820db3ae4a4c720cf35fac717acafa884cc03b1f65abd7e3b6`.
