# E28 results

Registered predictions: R1 holds; R2 holds; R3 does not. Positions are fast and spontaneous naming stays below10%.

- R1: met
- R2 (prose_paren): met
- R2 (prose_sentiment): not met
- R3: not evaluable

| Row | Arm | Fast | First ≥.80 step | Naming rate |
|---|---|---:|---:|---:|
| prose_paren | L | True | 100 | 1.000 |
| prose_paren | B | False | >400 | 1.000 |
| prose_paren | S | False | >400 | 1.000 |
| python_string | L | True | 25 | 1.000 |
| python_string | B | True | 25 | 1.000 |
| table_role | L | True | 25 | 1.000 |
| table_role | B | True | 100 | 1.000 |
| python_depth | L | True | 50 | 1.000 |
| python_depth | B | False | 400 | 1.000 |
| table_column | L | True | 25 | 1.000 |
| table_column | B | True | 100 | 1.000 |
| prose_sentiment | L | True | 0 | not evaluable |
| prose_sentiment | B | True | 0 | not evaluable |
| prose_sentiment | S | True | 0 | not evaluable |

R3 retains the merged-adapter/E33 confound required by §130. Censored crossings are not imputed. Failed S controls make the corresponding row uninterpretable. E24 has no sentiment statement regex; its native free text is retained. All checkpoint AUROCs, cluster CIs, statement-rate CIs and censoring counts are in METRICS.json.
