# W1 per-row tables — DESCRIPTIVE

**Registered §70 verdict remains NOT MET.** All results below are DESCRIPTIVE; no registered result is revised.

Existing marginal CIs copied unchanged. Paired AUROC difference uses the same complete test items, frozen mean of two phrasings and A-positive signs, with 2000 joint template-cluster percentile bootstrap resamples and seed 20261023. All 40 rows retained, including gated cells; gates copied unchanged. No probe refits, new item selection, new gates or multiplicity correction. Ordinal metrics copied unchanged.

Reported n is held-out test n (42 A + 42 B per binary row), with six template clusters. Entries show AUROC [95% CI]. The probe is shown at both trained sites: block 44 for Oracle/J/logit and block 42 for NLA. Paired intervals describe **AUROC(NLA at 42) − AUROC(Oracle at 44)**, not the mean difference of raw log-odds.

## Binary rows — DESCRIPTIVE

Gates are reader-specific and retain the frozen thresholds: probe ≥ 0.85 and mismatched AUROC ≤ 0.60. In the gate column the order is Oracle/NLA/J/logit: P = EVALUABLE (passed both), D = NOT DECODABLE, E = NOT EVALUABLE. Gated AUROCs and their differences are still displayed descriptively and do not become eligible evidence. Exact mismatched AUROCs/CIs and unrounded values are in `tables.json`.

| Row | Class | Domain | n | Probe 44 | Probe 42 | Oracle 44 | NLA 42 | J 44 | Logit 44 | NLA − Oracle, paired | Gates O/N/J/L |
|---|---|---|---:|---|---|---|---|---|---|---|---|
| json_depth | count-like | json | 84 | 0.996 [0.989, 1.000] | 1.000 [1.000, 1.000] | 0.346 [0.204, 0.481] | 0.274 [0.182, 0.345] | 0.560 [0.536, 0.582] | 0.536 [0.491, 0.579] | -0.071 [-0.214, +0.075] | E/E/P/P |
| json_field | count-like | json | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.249 [0.151, 0.402] | 0.736 [0.664, 0.803] | 0.156 [0.051, 0.234] | 0.265 [0.126, 0.388] | +0.486 [+0.297, +0.639] | E/P/E/E |
| json_status | semantic | json | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | +0.000 [+0.000, +0.000] | P/P/P/P |
| json_type | state-like | json | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.660 [0.603, 0.695] | 0.883 [0.807, 0.959] | 0.535 [0.489, 0.590] | 0.634 [0.605, 0.694] | +0.223 [+0.116, +0.345] | P/P/P/P |
| latex_brace | count-like | latex | 84 | 0.729 [0.712, 0.888] | 0.749 [0.729, 0.954] | 0.528 [0.403, 0.634] | 0.512 [0.457, 0.588] | 0.494 [0.420, 0.558] | 0.544 [0.490, 0.656] | -0.016 [-0.153, +0.163] | D/D/D/D |
| latex_environment | state-like | latex | 84 | 0.943 [0.833, 1.000] | 0.935 [0.819, 1.000] | 0.571 [0.498, 0.712] | 0.678 [0.490, 0.955] | 0.510 [0.431, 0.569] | 0.501 [0.396, 0.624] | +0.107 [-0.158, +0.388] | P/P/P/P |
| latex_fraction | state-like | latex | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.955 [0.891, 0.993] | 0.193 [0.062, 0.319] | 0.999 [0.995, 1.000] | 0.950 [0.872, 0.997] | -0.762 [-0.911, -0.623] | P/E/P/P |
| latex_item | count-like | latex | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.879 [0.686, 0.986] | 0.772 [0.716, 0.884] | 0.751 [0.487, 0.939] | 0.579 [0.299, 0.822] | -0.107 [-0.198, +0.053] | P/P/P/P |
| latex_math | state-like | latex | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.971 [0.939, 0.997] | 0.135 [0.011, 0.373] | 0.145 [0.000, 0.400] | -0.029 [-0.061, -0.003] | P/P/E/E |
| latex_role | semantic | latex | 84 | 0.972 [0.889, 1.000] | 0.991 [0.966, 1.000] | 0.844 [0.644, 1.000] | 0.949 [0.850, 1.000] | 0.999 [0.995, 1.000] | 0.974 [0.940, 1.000] | +0.105 [-0.013, +0.281] | P/P/P/P |
| latex_section | count-like | latex | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.433 [0.353, 0.516] | 0.876 [0.821, 0.924] | 0.596 [0.425, 0.709] | 0.717 [0.639, 0.798] | +0.443 [+0.331, +0.537] | P/P/P/P |
| latex_subject | semantic | latex | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.999 [0.998, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | -0.001 [-0.002, +0.000] | P/P/P/P |
| list_completed | count-like | list | 84 | 0.823 [0.769, 1.000] | 0.865 [0.787, 1.000] | 0.489 [0.364, 0.616] | 0.337 [0.186, 0.376] | 0.502 [0.328, 0.692] | 0.458 [0.264, 0.636] | -0.152 [-0.281, -0.078] | D/E/D/D |
| list_depth | count-like | list | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.634 [0.571, 0.808] | 0.651 [0.488, 0.868] | 0.464 [0.283, 0.630] | 0.401 [0.186, 0.590] | +0.018 [-0.222, +0.179] | P/P/P/P |
| list_index | count-like | list | 84 | 0.999 [0.998, 1.000] | 1.000 [1.000, 1.000] | 0.419 [0.238, 0.592] | 0.669 [0.423, 0.917] | 0.523 [0.284, 0.791] | 0.514 [0.340, 0.694] | +0.250 [-0.045, +0.584] | P/P/P/P |
| list_ordered | state-like | list | 84 | 0.698 [0.672, 0.875] | 0.668 [0.655, 0.865] | 0.572 [0.545, 0.719] | 0.519 [0.408, 0.626] | 0.569 [0.558, 0.653] | 0.558 [0.494, 0.671] | -0.053 [-0.213, +0.018] | D/D/D/D |
| list_priority | semantic | list | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.891 [0.609, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | +0.109 [+0.000, +0.391] | P/P/P/P |
| list_task | state-like | list | 84 | 0.755 [0.674, 0.977] | 0.770 [0.726, 0.938] | 0.505 [0.395, 0.652] | 0.506 [0.440, 0.589] | 0.548 [0.484, 0.671] | 0.534 [0.480, 0.645] | +0.002 [-0.071, +0.087] | D/D/D/D |
| list_topic | semantic | list | 84 | 0.863 [0.766, 1.000] | 0.913 [0.794, 1.000] | 0.968 [0.876, 1.000] | 0.988 [0.954, 1.000] | 1.000 [1.000, 1.000] | 0.878 [0.687, 1.000] | +0.020 [-0.039, +0.112] | P/P/P/P |
| list_words | count-like | list | 84 | 0.964 [0.881, 1.000] | 0.961 [0.883, 1.000] | 0.342 [0.106, 0.636] | 0.823 [0.531, 1.000] | 0.087 [0.000, 0.293] | 0.362 [0.061, 0.662] | +0.480 [-0.061, +0.875] | E/P/E/E |
| prose_budget | count-like | prose | 84 | 0.967 [0.887, 1.000] | 1.000 [1.000, 1.000] | 0.382 [0.054, 0.667] | 0.382 [0.116, 0.706] | 0.337 [0.026, 0.747] | 0.507 [0.140, 0.881] | +0.000 [-0.509, +0.506] | E/E/E/P |
| prose_column | count-like | prose | 84 | 0.914 [0.812, 1.000] | 0.871 [0.770, 1.000] | 0.339 [0.117, 0.627] | 0.385 [0.091, 0.698] | 0.566 [0.174, 0.917] | 0.443 [0.159, 0.660] | +0.046 [-0.346, +0.384] | E/E/P/P |
| prose_paren | state-like | prose | 84 | 1.000 [1.000, 1.000] | 0.982 [0.934, 1.000] | 0.485 [0.276, 0.653] | 0.744 [0.571, 0.934] | 0.438 [0.245, 0.605] | 0.376 [0.172, 0.501] | +0.259 [+0.003, +0.646] | P/P/P/E |
| prose_quote | state-like | prose | 84 | 1.000 [1.000, 1.000] | 0.918 [0.785, 1.000] | 0.563 [0.252, 0.830] | 0.680 [0.505, 0.927] | 0.465 [0.306, 0.618] | 0.389 [0.217, 0.489] | +0.117 [-0.318, +0.586] | P/P/P/E |
| prose_sentence | count-like | prose | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.531 [0.248, 0.799] | 0.609 [0.396, 0.779] | 0.578 [0.323, 0.834] | 0.691 [0.517, 0.832] | +0.078 [-0.286, +0.482] | P/P/P/P |
| prose_sentiment | semantic | prose | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.911 [0.626, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | +0.089 [+0.000, +0.374] | P/P/P/P |
| prose_topic | semantic | prose | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.989 [0.971, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | -0.011 [-0.029, +0.000] | P/P/P/P |
| prose_words | count-like | prose | 84 | 0.895 [0.750, 1.000] | 0.913 [0.778, 1.000] | 0.218 [0.054, 0.454] | 0.711 [0.459, 0.876] | 0.048 [0.000, 0.167] | 0.296 [0.044, 0.594] | +0.493 [+0.153, +0.776] | E/P/E/E |
| python_argument | count-like | python | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.500 [0.396, 0.624] | 0.659 [0.456, 0.859] | 0.961 [0.937, 0.988] | 0.846 [0.745, 0.932] | +0.159 [-0.038, +0.365] | P/P/P/P |
| python_comment | state-like | python | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.543 [0.471, 0.628] | 0.721 [0.685, 0.771] | 0.729 [0.706, 0.772] | 0.565 [0.490, 0.660] | +0.178 [+0.105, +0.262] | P/P/P/P |
| python_depth | count-like | python | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.488 [0.440, 0.531] | 0.731 [0.618, 0.853] | 0.560 [0.536, 0.591] | 0.582 [0.511, 0.650] | +0.243 [+0.167, +0.325] | P/P/P/P |
| python_effect | semantic | python | 84 | 0.849 [0.738, 0.988] | 0.882 [0.811, 0.998] | 0.570 [0.454, 0.668] | 0.540 [0.466, 0.606] | 0.524 [0.441, 0.602] | 0.567 [0.495, 0.658] | -0.029 [-0.193, +0.145] | D/P/D/D |
| python_error | semantic | python | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.994 [0.987, 1.000] | 0.996 [0.986, 1.000] | 0.964 [0.902, 0.999] | -0.006 [-0.013, +0.000] | P/P/P/P |
| python_indent | count-like | python | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.592 [0.354, 0.843] | 0.674 [0.358, 0.918] | 0.806 [0.515, 0.982] | 0.890 [0.774, 1.000] | +0.082 [-0.349, +0.417] | P/P/P/P |
| python_line | count-like | python | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.382 [0.147, 0.574] | 0.888 [0.762, 0.984] | 0.806 [0.667, 1.000] | 0.859 [0.723, 1.000] | +0.506 [+0.270, +0.786] | E/P/P/P |
| python_string | state-like | python | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.644 [0.508, 0.782] | 0.985 [0.952, 1.000] | 0.663 [0.604, 0.726] | 0.622 [0.512, 0.764] | +0.341 [+0.210, +0.483] | P/P/P/P |
| table_column | count-like | table | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.474 [0.334, 0.615] | 0.568 [0.349, 0.789] | 0.632 [0.600, 0.758] | 0.587 [0.532, 0.676] | +0.094 [-0.039, +0.268] | P/P/P/P |
| table_role | state-like | table | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.438 [0.218, 0.689] | 0.973 [0.950, 0.992] | 0.346 [0.197, 0.461] | 0.647 [0.392, 0.821] | +0.535 [+0.272, +0.756] | P/P/E/P |
| table_row | count-like | table | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.501 [0.386, 0.608] | 0.819 [0.698, 0.931] | 0.742 [0.634, 0.882] | 0.710 [0.602, 0.823] | +0.318 [+0.258, +0.390] | P/P/P/P |
| table_status | semantic | table | 84 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.956 [0.874, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | -0.044 [-0.126, +0.000] | P/P/P/P |

## Fresh replication rows vs Suraj's pilot — DESCRIPTIVE

Pilot numbers are the point estimates recorded in BRIEF_BLINDSPOT §70/pilot paragraph. Pilot n and CIs were not supplied; pilot-to-fresh difference CIs cannot be reconstructed. Fresh n = 84 and six clusters for each row. Each fresh result is AUROC [95% CI]. No pilot probe or logit result is supplied.

| Row | Pilot Oracle | Fresh Oracle | Pilot NLA | Fresh NLA | Pilot J | Fresh J | Fresh NLA − Oracle, paired |
|---|---:|---|---:|---|---:|---|---|
| table_column | 0.67 | 0.474 [0.334, 0.615] | 1.00 | 0.568 [0.349, 0.789] | 0.64 | 0.632 [0.600, 0.758] | +0.094 [-0.039, +0.268] |
| prose_paren | 0.76 | 0.485 [0.276, 0.653] | 0.98 | 0.744 [0.571, 0.934] | 0.47 | 0.438 [0.245, 0.605] | +0.259 [+0.003, +0.646] |

## Ordinal levels 1–8 — DESCRIPTIVE

Spearman ρ relates NLA block-42 mean paired log-odds to level. These are the original sealed ordinal metrics and CIs, not a new fit. Ordinal rows have no registered binary AUROC/probe/mismatch gate, so binary AUROCs and NLA − Oracle AUROC are undefined. No binarisation has been introduced.

| Row | Class | Domain | Test n | Clusters | Levels | n per level | NLA Spearman ρ [95% CI] | Frozen ≥0.6 label |
|---|---|---|---:|---:|---|---:|---|---|
| python_depth_ordinal | count-like | python | 144 | 6 | 1–8 | 18 | 0.218 [0.008, 0.447] | flags a state |
| table_column_ordinal | count-like | table | 144 | 6 | 1–8 | 18 | 0.054 [-0.325, 0.482] | flags a state |

## Semantic rows failing rule (iii) — DESCRIPTIVE

The frozen rule uses **absolute** distance ≤ 0.10 from the block-44 probe. Of nine Oracle-evaluable semantic rows, six pass and these three fail:

| Row | Probe 44 [95% CI] | Oracle 44 [95% CI] | Oracle − probe | Reason |
|---|---|---|---:|---|
| latex_role | 0.972 [0.889, 1.000] | 0.844 [0.644, 1.000] | -0.128685 | Oracle below probe by >0.10 |
| list_priority | 1.000 [1.000, 1.000] | 0.891 [0.609, 1.000] | -0.109410 | Oracle below probe by >0.10 |
| list_topic | 0.863 [0.766, 1.000] | 0.968 [0.876, 1.000] | +0.104308 | Oracle above probe by >0.10; absolute-distance rule |

`python_effect` is excluded from the rule-(iii) denominator: block-44 probe AUROC 0.849206 < 0.85 (NOT DECODABLE). It is not counted as a semantic failure. `list_topic` fails because the Oracle exceeds its probe by 0.104308; this follows the registered absolute-distance rule, not an underperformance criterion.

## Provenance and limits — DESCRIPTIVE

Original analysis seal SHA256: `01bc54fc3f9c90ac9162613f13868265edc04cb8c8bd28c30063238041adb898`. Marginal metrics, replication pilot values, gates and ordinal estimates are copied from `../analysis/metrics.json`; paired reader differences are newly computed from the same sealed asked scores, under the existing bootstrap convention. No model/API calls or GPU work. The approximately 214 s science-cap overrun and PARTIAL free-response recall status remain disclosed in `../COMPUTE_DEVIATION.json` and `../free_response_status.json`. These tables do not infer recall rates or change the registered verdict.
