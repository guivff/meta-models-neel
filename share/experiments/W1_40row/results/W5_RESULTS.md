**Prediction (§74):** At least 75% of W1’s blind-spot rows have Oracle AUROC<0.75 at five or more of six layers, while their probe stays≥0.85 at all six.

**Did it hold? Not established: the registered verdict is NOT EVALUABLE.** Ten of 16 rows meet the rule (62.5%; Wilson 95% CI 38.6–81.5%). Four rows are NOT MET; two remain unresolved because of reader gates. Their possible contribution leaves a 62.5–75.0% bound, which reaches the 75% threshold at its upper endpoint. These are logical bounds from gate uncertainty, not a confidence interval.

# W5 layer sweep — registered §74 analysis

W5 §74: NOT EVALUABLE; 10/16 rows meet Oracle<0.75 at>=5/6 evaluable layers with probe>=0.85 at all 6; fraction 0.625; unresolved 2; possible fraction bounds[0.625, 0.75].

Full fresh sealed score pass: pod 53o6cnnsfxqknh; 3,360 test items across 40 rows, 84 per row and six template clusters, layers 20/28/36/44/52/60. Registered frozen analysis SHA256 45a06d29… ran once, without changed rules, sign flips or denominator filtering. The denominator is the 16 W1 rule-(i) blind-spot rows, not only rows with complete gates.

| Blind-spot row | Evaluable layers with Oracle<0.75 | All six probes≥0.85 | Registered status | Excluded layer cells |
|---|---|---|---|---|
| json_type | 6 | True | CONFIRMED | none |
| latex_environment | 6 | True | CONFIRMED | none |
| latex_section | 6 | True | CONFIRMED | none |
| list_depth | 5 | True | CONFIRMED | 28: NOT EVALUABLE |
| list_index | 4 | False | NOT MET | 20: NOT DECODABLE, 52: NOT EVALUABLE |
| prose_paren | 5 | False | NOT MET | 20: NOT DECODABLE |
| prose_quote | 3 | False | NOT MET | 20: NOT DECODABLE, 28: NOT DECODABLE, 36: NOT DECODABLE |
| prose_sentence | 6 | True | CONFIRMED | none |
| python_argument | 2 | True | NOT MET | 52: NOT EVALUABLE, 60: NOT EVALUABLE |
| python_comment | 6 | True | CONFIRMED | none |
| python_depth | 6 | True | CONFIRMED | none |
| python_indent | 5 | True | CONFIRMED | 20: NOT EVALUABLE |
| python_string | 4 | True | NOT EVALUABLE | 20: NOT EVALUABLE, 52: NOT EVALUABLE |
| table_column | 5 | True | CONFIRMED | 60: NOT EVALUABLE |
| table_role | 3 | True | NOT EVALUABLE | 36: NOT EVALUABLE, 52: NOT EVALUABLE, 60: NOT EVALUABLE |
| table_row | 6 | True | CONFIRMED | none |

The two unresolved rows are `python_string` and `table_role`. Probe-gate failures occur for `list_index`, `prose_paren` and `prose_quote`; `python_argument` is NOT MET because enough evaluable layers exceed the Oracle threshold. A row can satisfy five-layer weakness even if a sixth reader cell fails its donor gate; the registered probe condition still applies at all six layers.

## Complete per-layer descriptive values

All 40 rows are shown below; the registered primary decision above uses only the 16 fixed W1 blind-spot rows. AUROC CIs use 2,000 template-cluster resamples; native probe AUROCs use fixed grouped-CV out-of-fold predictions.

| Row | Layer | Oracle AUROC [95% CI] | Probe AUROC | Mismatched AUROC | Reader status |
|---|---|---|---|---|---|
| json_depth | 20 | 0.444 [0.204, 0.719] | 1.000 | 0.556 | EVALUABLE |
| json_depth | 28 | 0.368 [0.219, 0.543] | 1.000 | 0.632 | NOT EVALUABLE |
| json_depth | 36 | 0.425 [0.261, 0.566] | 1.000 | 0.575 | EVALUABLE |
| json_depth | 44 | 0.352 [0.213, 0.492] | 0.997 | 0.648 | NOT EVALUABLE |
| json_depth | 52 | 0.424 [0.367, 0.465] | 1.000 | 0.576 | EVALUABLE |
| json_depth | 60 | 0.517 [0.400, 0.623] | 1.000 | 0.483 | EVALUABLE |
| json_field | 20 | 0.172 [0.041, 0.322] | 1.000 | 0.828 | NOT EVALUABLE |
| json_field | 28 | 0.214 [0.150, 0.273] | 1.000 | 0.786 | NOT EVALUABLE |
| json_field | 36 | 0.289 [0.192, 0.417] | 1.000 | 0.711 | NOT EVALUABLE |
| json_field | 44 | 0.243 [0.141, 0.392] | 1.000 | 0.757 | NOT EVALUABLE |
| json_field | 52 | 0.388 [0.236, 0.502] | 1.000 | 0.612 | NOT EVALUABLE |
| json_field | 60 | 0.415 [0.342, 0.472] | 1.000 | 0.585 | EVALUABLE |
| json_status | 20 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| json_status | 28 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| json_status | 36 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| json_status | 44 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| json_status | 52 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| json_status | 60 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| json_type | 20 | 0.595 [0.565, 0.618] | 1.000 | 0.405 | EVALUABLE |
| json_type | 28 | 0.736 [0.700, 0.788] | 1.000 | 0.264 | EVALUABLE |
| json_type | 36 | 0.711 [0.678, 0.738] | 1.000 | 0.289 | EVALUABLE |
| json_type | 44 | 0.660 [0.604, 0.694] | 1.000 | 0.340 | EVALUABLE |
| json_type | 52 | 0.671 [0.569, 0.751] | 1.000 | 0.329 | EVALUABLE |
| json_type | 60 | 0.473 [0.442, 0.503] | 1.000 | 0.527 | EVALUABLE |
| latex_brace | 20 | 0.506 [0.448, 0.551] | 0.696 | 0.494 | NOT DECODABLE |
| latex_brace | 28 | 0.524 [0.510, 0.562] | 0.681 | 0.476 | NOT DECODABLE |
| latex_brace | 36 | 0.511 [0.431, 0.637] | 0.753 | 0.489 | NOT DECODABLE |
| latex_brace | 44 | 0.536 [0.411, 0.641] | 0.731 | 0.464 | NOT DECODABLE |
| latex_brace | 52 | 0.434 [0.325, 0.473] | 0.791 | 0.566 | NOT DECODABLE |
| latex_brace | 60 | 0.472 [0.342, 0.565] | 0.880 | 0.528 | EVALUABLE |
| latex_environment | 20 | 0.585 [0.423, 0.712] | 0.930 | 0.415 | EVALUABLE |
| latex_environment | 28 | 0.606 [0.468, 0.795] | 0.867 | 0.394 | EVALUABLE |
| latex_environment | 36 | 0.521 [0.454, 0.609] | 0.950 | 0.479 | EVALUABLE |
| latex_environment | 44 | 0.576 [0.519, 0.710] | 0.943 | 0.424 | EVALUABLE |
| latex_environment | 52 | 0.501 [0.377, 0.600] | 0.961 | 0.499 | EVALUABLE |
| latex_environment | 60 | 0.562 [0.490, 0.704] | 0.968 | 0.438 | EVALUABLE |
| latex_fraction | 20 | 0.931 [0.741, 1.000] | 1.000 | 0.069 | EVALUABLE |
| latex_fraction | 28 | 0.882 [0.617, 0.997] | 1.000 | 0.118 | EVALUABLE |
| latex_fraction | 36 | 0.677 [0.431, 0.862] | 1.000 | 0.323 | EVALUABLE |
| latex_fraction | 44 | 0.959 [0.893, 0.994] | 1.000 | 0.041 | EVALUABLE |
| latex_fraction | 52 | 0.885 [0.786, 0.980] | 1.000 | 0.115 | EVALUABLE |
| latex_fraction | 60 | 0.847 [0.719, 0.940] | 1.000 | 0.153 | EVALUABLE |
| latex_item | 20 | 0.762 [0.441, 0.980] | 1.000 | 0.238 | EVALUABLE |
| latex_item | 28 | 0.845 [0.705, 0.978] | 1.000 | 0.155 | EVALUABLE |
| latex_item | 36 | 0.796 [0.580, 0.972] | 1.000 | 0.204 | EVALUABLE |
| latex_item | 44 | 0.900 [0.764, 0.986] | 1.000 | 0.100 | EVALUABLE |
| latex_item | 52 | 0.846 [0.694, 0.968] | 1.000 | 0.154 | EVALUABLE |
| latex_item | 60 | 0.833 [0.680, 0.946] | 1.000 | 0.167 | EVALUABLE |
| latex_math | 20 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| latex_math | 28 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| latex_math | 36 | 0.993 [0.973, 1.000] | 1.000 | 0.007 | EVALUABLE |
| latex_math | 44 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| latex_math | 52 | 0.945 [0.862, 0.993] | 1.000 | 0.055 | EVALUABLE |
| latex_math | 60 | 0.890 [0.698, 0.978] | 1.000 | 0.110 | EVALUABLE |
| latex_role | 20 | 0.988 [0.923, 1.000] | 1.000 | 0.012 | EVALUABLE |
| latex_role | 28 | 0.913 [0.801, 1.000] | 0.998 | 0.087 | EVALUABLE |
| latex_role | 36 | 0.921 [0.802, 1.000] | 0.995 | 0.079 | EVALUABLE |
| latex_role | 44 | 0.847 [0.664, 1.000] | 0.972 | 0.153 | EVALUABLE |
| latex_role | 52 | 0.842 [0.597, 0.998] | 1.000 | 0.158 | EVALUABLE |
| latex_role | 60 | 0.785 [0.492, 0.995] | 0.956 | 0.215 | EVALUABLE |
| latex_section | 20 | 0.448 [0.274, 0.592] | 1.000 | 0.552 | EVALUABLE |
| latex_section | 28 | 0.471 [0.355, 0.590] | 1.000 | 0.529 | EVALUABLE |
| latex_section | 36 | 0.595 [0.546, 0.676] | 1.000 | 0.405 | EVALUABLE |
| latex_section | 44 | 0.433 [0.347, 0.526] | 1.000 | 0.567 | EVALUABLE |
| latex_section | 52 | 0.524 [0.412, 0.642] | 1.000 | 0.476 | EVALUABLE |
| latex_section | 60 | 0.721 [0.628, 0.836] | 1.000 | 0.279 | EVALUABLE |
| latex_subject | 20 | 0.916 [0.786, 1.000] | 1.000 | 0.084 | EVALUABLE |
| latex_subject | 28 | 0.963 [0.864, 1.000] | 0.997 | 0.037 | EVALUABLE |
| latex_subject | 36 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| latex_subject | 44 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| latex_subject | 52 | 0.994 [0.949, 1.000] | 1.000 | 0.006 | EVALUABLE |
| latex_subject | 60 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| list_completed | 20 | 0.550 [0.454, 0.672] | 0.651 | 0.450 | NOT DECODABLE |
| list_completed | 28 | 0.533 [0.503, 0.612] | 0.719 | 0.467 | NOT DECODABLE |
| list_completed | 36 | 0.506 [0.379, 0.659] | 0.937 | 0.494 | EVALUABLE |
| list_completed | 44 | 0.490 [0.371, 0.616] | 0.830 | 0.510 | NOT DECODABLE |
| list_completed | 52 | 0.546 [0.444, 0.724] | 0.935 | 0.454 | EVALUABLE |
| list_completed | 60 | 0.580 [0.477, 0.725] | 0.825 | 0.420 | NOT DECODABLE |
| list_depth | 20 | 0.437 [0.281, 0.537] | 0.992 | 0.563 | EVALUABLE |
| list_depth | 28 | 0.383 [0.212, 0.462] | 0.940 | 0.617 | NOT EVALUABLE |
| list_depth | 36 | 0.539 [0.447, 0.672] | 1.000 | 0.461 | EVALUABLE |
| list_depth | 44 | 0.632 [0.566, 0.806] | 1.000 | 0.368 | EVALUABLE |
| list_depth | 52 | 0.524 [0.350, 0.700] | 1.000 | 0.476 | EVALUABLE |
| list_depth | 60 | 0.526 [0.395, 0.673] | 0.939 | 0.474 | EVALUABLE |
| list_index | 20 | 0.598 [0.394, 0.816] | 0.785 | 0.402 | NOT DECODABLE |
| list_index | 28 | 0.549 [0.295, 0.825] | 0.867 | 0.451 | EVALUABLE |
| list_index | 36 | 0.433 [0.250, 0.648] | 1.000 | 0.567 | EVALUABLE |
| list_index | 44 | 0.434 [0.269, 0.592] | 0.999 | 0.566 | EVALUABLE |
| list_index | 52 | 0.361 [0.237, 0.386] | 1.000 | 0.639 | NOT EVALUABLE |
| list_index | 60 | 0.406 [0.176, 0.595] | 1.000 | 0.594 | EVALUABLE |
| list_ordered | 20 | 0.507 [0.431, 0.613] | 0.758 | 0.493 | NOT DECODABLE |
| list_ordered | 28 | 0.502 [0.378, 0.624] | 0.712 | 0.498 | NOT DECODABLE |
| list_ordered | 36 | 0.659 [0.586, 0.823] | 0.683 | 0.341 | NOT DECODABLE |
| list_ordered | 44 | 0.567 [0.539, 0.706] | 0.696 | 0.433 | NOT DECODABLE |
| list_ordered | 52 | 0.538 [0.515, 0.622] | 0.834 | 0.462 | NOT DECODABLE |
| list_ordered | 60 | 0.546 [0.460, 0.677] | 0.819 | 0.454 | NOT DECODABLE |
| list_priority | 20 | 0.924 [0.731, 1.000] | 1.000 | 0.076 | EVALUABLE |
| list_priority | 28 | 0.923 [0.832, 1.000] | 1.000 | 0.077 | EVALUABLE |
| list_priority | 36 | 0.946 [0.724, 1.000] | 1.000 | 0.054 | EVALUABLE |
| list_priority | 44 | 0.894 [0.617, 1.000] | 1.000 | 0.106 | EVALUABLE |
| list_priority | 52 | 0.908 [0.813, 1.000] | 1.000 | 0.092 | EVALUABLE |
| list_priority | 60 | 0.913 [0.587, 1.000] | 1.000 | 0.087 | EVALUABLE |
| list_task | 20 | 0.561 [0.489, 0.704] | 0.672 | 0.439 | NOT DECODABLE |
| list_task | 28 | 0.532 [0.506, 0.628] | 0.737 | 0.468 | NOT DECODABLE |
| list_task | 36 | 0.539 [0.465, 0.667] | 0.846 | 0.461 | NOT DECODABLE |
| list_task | 44 | 0.516 [0.421, 0.672] | 0.751 | 0.484 | NOT DECODABLE |
| list_task | 52 | 0.474 [0.362, 0.582] | 0.672 | 0.526 | NOT DECODABLE |
| list_task | 60 | 0.486 [0.421, 0.571] | 0.681 | 0.514 | NOT DECODABLE |
| list_topic | 20 | 0.986 [0.884, 1.000] | 1.000 | 0.014 | EVALUABLE |
| list_topic | 28 | 0.966 [0.922, 1.000] | 0.877 | 0.034 | EVALUABLE |
| list_topic | 36 | 0.970 [0.871, 1.000] | 0.970 | 0.030 | EVALUABLE |
| list_topic | 44 | 0.967 [0.884, 1.000] | 0.863 | 0.033 | EVALUABLE |
| list_topic | 52 | 0.999 [0.998, 1.000] | 0.972 | 0.001 | EVALUABLE |
| list_topic | 60 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| list_words | 20 | 0.124 [0.000, 0.243] | 0.995 | 0.876 | NOT EVALUABLE |
| list_words | 28 | 0.348 [0.141, 0.599] | 1.000 | 0.652 | NOT EVALUABLE |
| list_words | 36 | 0.309 [0.083, 0.556] | 1.000 | 0.691 | NOT EVALUABLE |
| list_words | 44 | 0.340 [0.108, 0.621] | 0.964 | 0.660 | NOT EVALUABLE |
| list_words | 52 | 0.553 [0.271, 0.883] | 0.854 | 0.447 | EVALUABLE |
| list_words | 60 | 0.391 [0.082, 0.793] | 0.944 | 0.609 | NOT EVALUABLE |
| prose_budget | 20 | 0.367 [0.155, 0.575] | 0.819 | 0.633 | NOT DECODABLE |
| prose_budget | 28 | 0.365 [0.068, 0.639] | 0.891 | 0.635 | NOT EVALUABLE |
| prose_budget | 36 | 0.476 [0.123, 0.777] | 0.925 | 0.524 | EVALUABLE |
| prose_budget | 44 | 0.380 [0.050, 0.667] | 0.967 | 0.620 | NOT EVALUABLE |
| prose_budget | 52 | 0.313 [0.046, 0.656] | 0.861 | 0.687 | NOT EVALUABLE |
| prose_budget | 60 | 0.378 [0.147, 0.611] | 0.668 | 0.622 | NOT DECODABLE |
| prose_column | 20 | 0.169 [0.007, 0.403] | 0.895 | 0.831 | NOT EVALUABLE |
| prose_column | 28 | 0.378 [0.077, 0.719] | 0.912 | 0.622 | NOT EVALUABLE |
| prose_column | 36 | 0.493 [0.222, 0.750] | 0.927 | 0.507 | EVALUABLE |
| prose_column | 44 | 0.325 [0.105, 0.613] | 0.916 | 0.675 | NOT EVALUABLE |
| prose_column | 52 | 0.295 [0.077, 0.565] | 0.837 | 0.705 | NOT DECODABLE |
| prose_column | 60 | 0.146 [0.002, 0.461] | 0.601 | 0.854 | NOT DECODABLE |
| prose_paren | 20 | 0.636 [0.412, 0.844] | 0.819 | 0.364 | NOT DECODABLE |
| prose_paren | 28 | 0.585 [0.415, 0.763] | 0.972 | 0.415 | EVALUABLE |
| prose_paren | 36 | 0.611 [0.423, 0.813] | 0.923 | 0.389 | EVALUABLE |
| prose_paren | 44 | 0.477 [0.266, 0.650] | 1.000 | 0.523 | EVALUABLE |
| prose_paren | 52 | 0.448 [0.222, 0.641] | 1.000 | 0.552 | EVALUABLE |
| prose_paren | 60 | 0.567 [0.416, 0.714] | 1.000 | 0.433 | EVALUABLE |
| prose_quote | 20 | 0.519 [0.465, 0.616] | 0.767 | 0.481 | NOT DECODABLE |
| prose_quote | 28 | 0.598 [0.397, 0.795] | 0.841 | 0.402 | NOT DECODABLE |
| prose_quote | 36 | 0.638 [0.410, 0.855] | 0.837 | 0.362 | NOT DECODABLE |
| prose_quote | 44 | 0.561 [0.263, 0.816] | 1.000 | 0.439 | EVALUABLE |
| prose_quote | 52 | 0.575 [0.409, 0.751] | 1.000 | 0.425 | EVALUABLE |
| prose_quote | 60 | 0.588 [0.389, 0.791] | 1.000 | 0.412 | EVALUABLE |
| prose_sentence | 20 | 0.468 [0.254, 0.690] | 1.000 | 0.532 | EVALUABLE |
| prose_sentence | 28 | 0.470 [0.267, 0.706] | 1.000 | 0.530 | EVALUABLE |
| prose_sentence | 36 | 0.617 [0.338, 0.848] | 1.000 | 0.383 | EVALUABLE |
| prose_sentence | 44 | 0.552 [0.245, 0.827] | 1.000 | 0.448 | EVALUABLE |
| prose_sentence | 52 | 0.567 [0.388, 0.777] | 1.000 | 0.433 | EVALUABLE |
| prose_sentence | 60 | 0.580 [0.379, 0.834] | 1.000 | 0.420 | EVALUABLE |
| prose_sentiment | 20 | 0.989 [0.955, 1.000] | 1.000 | 0.011 | EVALUABLE |
| prose_sentiment | 28 | 0.966 [0.884, 1.000] | 1.000 | 0.034 | EVALUABLE |
| prose_sentiment | 36 | 0.953 [0.794, 1.000] | 1.000 | 0.047 | EVALUABLE |
| prose_sentiment | 44 | 0.913 [0.629, 1.000] | 1.000 | 0.087 | EVALUABLE |
| prose_sentiment | 52 | 0.934 [0.665, 1.000] | 0.987 | 0.066 | EVALUABLE |
| prose_sentiment | 60 | 0.939 [0.677, 1.000] | 1.000 | 0.061 | EVALUABLE |
| prose_topic | 20 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| prose_topic | 28 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| prose_topic | 36 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| prose_topic | 44 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| prose_topic | 52 | 1.000 [1.000, 1.000] | 0.976 | 0.000 | EVALUABLE |
| prose_topic | 60 | 1.000 [1.000, 1.000] | 0.944 | 0.000 | EVALUABLE |
| prose_words | 20 | 0.127 [0.000, 0.231] | 0.981 | 0.873 | NOT EVALUABLE |
| prose_words | 28 | 0.247 [0.036, 0.563] | 0.992 | 0.753 | NOT EVALUABLE |
| prose_words | 36 | 0.206 [0.025, 0.471] | 0.967 | 0.794 | NOT EVALUABLE |
| prose_words | 44 | 0.218 [0.058, 0.454] | 0.895 | 0.782 | NOT EVALUABLE |
| prose_words | 52 | 0.522 [0.234, 0.853] | 0.819 | 0.478 | NOT DECODABLE |
| prose_words | 60 | 0.384 [0.063, 0.789] | 0.950 | 0.616 | NOT EVALUABLE |
| python_argument | 20 | 0.899 [0.857, 0.949] | 1.000 | 0.101 | EVALUABLE |
| python_argument | 28 | 0.922 [0.873, 0.980] | 1.000 | 0.078 | EVALUABLE |
| python_argument | 36 | 0.599 [0.498, 0.689] | 1.000 | 0.401 | EVALUABLE |
| python_argument | 44 | 0.505 [0.405, 0.615] | 1.000 | 0.495 | EVALUABLE |
| python_argument | 52 | 0.193 [0.128, 0.256] | 1.000 | 0.807 | NOT EVALUABLE |
| python_argument | 60 | 0.112 [0.071, 0.151] | 1.000 | 0.888 | NOT EVALUABLE |
| python_comment | 20 | 0.706 [0.594, 0.819] | 1.000 | 0.294 | EVALUABLE |
| python_comment | 28 | 0.575 [0.519, 0.649] | 1.000 | 0.425 | EVALUABLE |
| python_comment | 36 | 0.565 [0.514, 0.620] | 1.000 | 0.435 | EVALUABLE |
| python_comment | 44 | 0.540 [0.465, 0.615] | 1.000 | 0.460 | EVALUABLE |
| python_comment | 52 | 0.570 [0.485, 0.662] | 1.000 | 0.430 | EVALUABLE |
| python_comment | 60 | 0.618 [0.563, 0.680] | 1.000 | 0.382 | EVALUABLE |
| python_depth | 20 | 0.611 [0.577, 0.653] | 1.000 | 0.389 | EVALUABLE |
| python_depth | 28 | 0.597 [0.545, 0.655] | 0.997 | 0.403 | EVALUABLE |
| python_depth | 36 | 0.555 [0.490, 0.640] | 0.995 | 0.445 | EVALUABLE |
| python_depth | 44 | 0.493 [0.456, 0.546] | 1.000 | 0.507 | EVALUABLE |
| python_depth | 52 | 0.526 [0.454, 0.592] | 1.000 | 0.474 | EVALUABLE |
| python_depth | 60 | 0.522 [0.465, 0.564] | 1.000 | 0.478 | EVALUABLE |
| python_effect | 20 | 0.518 [0.431, 0.597] | 0.878 | 0.482 | EVALUABLE |
| python_effect | 28 | 0.554 [0.456, 0.679] | 0.847 | 0.446 | NOT DECODABLE |
| python_effect | 36 | 0.511 [0.378, 0.616] | 0.896 | 0.489 | EVALUABLE |
| python_effect | 44 | 0.565 [0.457, 0.658] | 0.851 | 0.435 | EVALUABLE |
| python_effect | 52 | 0.584 [0.485, 0.705] | 0.857 | 0.416 | EVALUABLE |
| python_effect | 60 | 0.581 [0.501, 0.689] | 0.934 | 0.419 | EVALUABLE |
| python_error | 20 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| python_error | 28 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| python_error | 36 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| python_error | 44 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| python_error | 52 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| python_error | 60 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| python_indent | 20 | 0.333 [0.171, 0.420] | 1.000 | 0.667 | NOT EVALUABLE |
| python_indent | 28 | 0.500 [0.299, 0.737] | 1.000 | 0.500 | EVALUABLE |
| python_indent | 36 | 0.563 [0.310, 0.787] | 1.000 | 0.437 | EVALUABLE |
| python_indent | 44 | 0.594 [0.357, 0.843] | 1.000 | 0.406 | EVALUABLE |
| python_indent | 52 | 0.557 [0.350, 0.766] | 1.000 | 0.443 | EVALUABLE |
| python_indent | 60 | 0.515 [0.244, 0.773] | 1.000 | 0.485 | EVALUABLE |
| python_line | 20 | 0.257 [0.039, 0.583] | 1.000 | 0.743 | NOT EVALUABLE |
| python_line | 28 | 0.243 [0.114, 0.357] | 1.000 | 0.757 | NOT EVALUABLE |
| python_line | 36 | 0.274 [0.061, 0.465] | 1.000 | 0.726 | NOT EVALUABLE |
| python_line | 44 | 0.385 [0.141, 0.591] | 1.000 | 0.615 | NOT EVALUABLE |
| python_line | 52 | 0.321 [0.125, 0.573] | 0.952 | 0.679 | NOT EVALUABLE |
| python_line | 60 | 0.159 [0.005, 0.398] | 0.906 | 0.841 | NOT EVALUABLE |
| python_string | 20 | 0.301 [0.163, 0.457] | 1.000 | 0.699 | NOT EVALUABLE |
| python_string | 28 | 0.539 [0.401, 0.693] | 1.000 | 0.461 | EVALUABLE |
| python_string | 36 | 0.567 [0.457, 0.694] | 1.000 | 0.433 | EVALUABLE |
| python_string | 44 | 0.653 [0.515, 0.793] | 1.000 | 0.347 | EVALUABLE |
| python_string | 52 | 0.319 [0.211, 0.416] | 1.000 | 0.681 | NOT EVALUABLE |
| python_string | 60 | 0.420 [0.377, 0.471] | 1.000 | 0.580 | EVALUABLE |
| table_column | 20 | 0.656 [0.541, 0.799] | 1.000 | 0.344 | EVALUABLE |
| table_column | 28 | 0.597 [0.470, 0.768] | 1.000 | 0.403 | EVALUABLE |
| table_column | 36 | 0.580 [0.526, 0.649] | 1.000 | 0.420 | EVALUABLE |
| table_column | 44 | 0.481 [0.348, 0.612] | 1.000 | 0.519 | EVALUABLE |
| table_column | 52 | 0.486 [0.367, 0.611] | 1.000 | 0.514 | EVALUABLE |
| table_column | 60 | 0.400 [0.252, 0.560] | 0.998 | 0.600 | NOT EVALUABLE |
| table_role | 20 | 0.518 [0.323, 0.714] | 1.000 | 0.482 | EVALUABLE |
| table_role | 28 | 0.600 [0.459, 0.782] | 1.000 | 0.400 | EVALUABLE |
| table_role | 36 | 0.399 [0.199, 0.621] | 1.000 | 0.601 | NOT EVALUABLE |
| table_role | 44 | 0.436 [0.216, 0.683] | 1.000 | 0.564 | EVALUABLE |
| table_role | 52 | 0.288 [0.100, 0.526] | 1.000 | 0.712 | NOT EVALUABLE |
| table_role | 60 | 0.341 [0.186, 0.533] | 1.000 | 0.659 | NOT EVALUABLE |
| table_row | 20 | 0.596 [0.511, 0.697] | 1.000 | 0.404 | EVALUABLE |
| table_row | 28 | 0.565 [0.454, 0.694] | 0.999 | 0.435 | EVALUABLE |
| table_row | 36 | 0.536 [0.461, 0.608] | 1.000 | 0.464 | EVALUABLE |
| table_row | 44 | 0.514 [0.401, 0.619] | 1.000 | 0.486 | EVALUABLE |
| table_row | 52 | 0.539 [0.339, 0.701] | 1.000 | 0.461 | EVALUABLE |
| table_row | 60 | 0.587 [0.473, 0.730] | 1.000 | 0.413 | EVALUABLE |
| table_status | 20 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| table_status | 28 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| table_status | 36 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| table_status | 44 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| table_status | 52 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |
| table_status | 60 | 1.000 [1.000, 1.000] | 1.000 | 0.000 | EVALUABLE |

## Provenance and verification

Input/capture/score/W1-analysis seals and the exact frozen source were verified before the label join. First admission rejected the older local `w1-bank` input seal before labels, fits or statistics ran; the exact scored `w1-bank-v2` matches both W5 and W1 input hashes. The once-only lock preserves that preflight correction; no completed analysis was rerun.

All 480 Oracle true/mismatched point estimates independently match SciPy average-rank Mann–Whitney AUROC calculations. Original registered ANALYSIS_SEAL.json is unchanged; report files carry a separate REPORT_SEAL.json. Historical W5 cap/setup deviations and prior NO_FIT attempts remain disclosed in the existing handoff and run logs. No model inference or new GPU use for this analysis.
