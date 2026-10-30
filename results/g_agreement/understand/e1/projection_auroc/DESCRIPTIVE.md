**DESCRIPTIVE — added after seeing E1 results (2026-10-24).** AUROC of the fixed native probe projection, value A positive, with ties counted as one half. No gap denominator, sign flip or probe refit. Both decoders and both frozen arms are included. These are point estimates; no new AUROC CIs were requested or computed. The original fidelity estimates and assessment are unchanged. High AUROC with low fidelity would indicate preserved ordering with a small projection contrast relative to the real-activation gap; AUROC alone does not validate reconstruction magnitude.

| Row | Class | AR description | AR on the prefix | NLA decoder description | NLA decoder on the prefix |
|---|---|---:|---:|---:|---:|
| json_status | semantic | 0.982500 | 0.996032 | 0.977500 | 1.000000 |
| json_type | state-like | 0.537500 | 0.653628 | 0.550000 | 0.993197 |
| latex_environment | state-like | 0.402500 | 0.849773 | 0.765000 | 0.792517 |
| latex_role | semantic | 0.670000 | 0.888889 | 1.000000 | 1.000000 |
| latex_section | count-like | 0.527500 | 0.003401 | 0.592500 | 1.000000 |
| latex_subject | semantic | 0.362500 | 0.897959 | 0.920000 | 1.000000 |
| list_depth | count-like | 0.565000 | 0.097506 | 0.557500 | 0.833333 |
| list_index | count-like | 0.732500 | 0.505102 | 0.430000 | 0.261905 |
| list_priority | semantic | 0.732500 | 0.484127 | 0.802500 | 1.000000 |
| list_topic | semantic | 0.787500 | 0.986395 | 1.000000 | 1.000000 |
| prose_paren | state-like | 0.247500 | 0.611111 | 0.492500 | 0.717687 |
| prose_quote | state-like | 0.515000 | 0.566893 | 0.507500 | 0.812358 |
| prose_sentence | count-like | 0.485000 | 0.984127 | 0.695000 | 0.566327 |
| prose_sentiment | semantic | 0.960000 | 0.984694 | 1.000000 | 1.000000 |
| prose_topic | semantic | 0.770000 | 0.849206 | 1.000000 | 1.000000 |
| python_argument | count-like | 0.727500 | 0.718254 | 0.812500 | 0.918934 |
| python_comment | state-like | 0.425000 | 0.824830 | 0.975000 | 0.637755 |
| python_depth | count-like | 0.680000 | 0.870748 | 0.445000 | 0.998299 |
| python_error | semantic | 0.762500 | 0.589002 | 0.935000 | 1.000000 |
| python_indent | count-like | 0.680000 | 0.506803 | 0.635000 | 0.967687 |
| python_string | state-like | 0.590000 | 0.872449 | 0.730000 | 0.998299 |
| table_column | count-like | 0.612500 | 0.544218 | 0.787500 | 1.000000 |
| table_role | state-like | 0.595000 | 0.989229 | 0.562500 | 1.000000 |
| table_row | count-like | 0.475000 | 0.792517 | 0.782500 | 1.000000 |
| table_status | semantic | 0.950000 | 0.788549 | 0.997500 | 0.996599 |

Per row: description n = 40 (20 A / 20 B); prefix n = 84 (42 A / 42 B). Full precision, source seals and counts: `projection_auroc/metrics.json`.
