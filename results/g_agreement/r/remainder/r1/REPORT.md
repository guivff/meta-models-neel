# R1 — RS-5 detectability

**2026-10-20 status annotation: SWAP-subset detection is DESCRIPTIVE.** The owner requested this label after the available-data analysis. Numeric estimates, confidence intervals and decision thresholds are unchanged. This report describes the preserved khop subset, not the later SWAP replacements or full RS-5 coverage. The [complete AUROC table for WS3 / SWAP-U](WS3_DETECTION_AUROC.md) exports all 750 original SWAP cells with controls. The [provenance gate](PROVENANCE_GATE.md) remains closed; no outcome was recomputed from changed source files. R5’s useful-detector verdict remains UNDEFINED.

CPU analysis completed 2026-10-20. 1,000 paired-item and corpus → fact → item bootstrap draws; every interval below is the envelope of both 95% intervals. No pod or judge spend.

**R5 useful-detector verdict: UNDEFINED.** 0 detector cells have an observed dose that flips the model on at least 50% of items. R5 is missing 47,040 readbacks on this Mac; Mahalanobis, kNN, norm and J-space energy require their original state files. Reader-confidence analysis covers all 235,200 existing rows from 30 facts.

**Completeness.** The source-row arm smoke passed. The strict full-design audit is recorded in audit.json; R5 has 47040 missing readbacks; SWAP is missing 1510 readback rows (22 khop L24 and all 1,488 poetry readbacks); poetry reader scores are absent. This is a completed analysis of available data, not a complete RS-5 experiment. Original state files must be pulled from the volume to finish R5 geometry; this analysis never regenerates them.

**Interpretation.** High-|LO| and low-|LO| are separate fixed detectors. LO shift uses the same item’s unedited reference and a distinct-natural-item difference null; it is not deployable without that reference. Content AUROC in R5 remains the original dataset label and is descriptive after edits. SWAP original-label accuracy is not content truth after an edit; model-answer agreement is reported separately. Do not interpret detection as faithful content reading.

## R5 confidence detection, by direction and dose

Each cell is the equally weighted mean over facts (random directions also averaged within fact). AUROC is versus natural controls; ΔAUROC is relative to chance 0.5. The full table, including confidence orientation, probe pseudo-reader, skip gradient and J-lens edit-site direction, is in `summary.json`.

| direction | dose | reader | low-confidence AUROC [95% CI] | ΔAUROC [95% CI] | TPR@5% FPR [95% CI] | content AUROC [95% CI] | detection − content [95% CI] |
|---|---:|---|---|---|---|---|---|
| class_mean | 0.5 | jlens | 0.501 [0.492, 0.512] | 0.001 [-0.008, 0.012] | 0.042 [0.022, 0.066] | 0.767 [0.641, 0.848] | -0.265 [-0.346, -0.141] |
| class_mean | 1.0 | jlens | 0.503 [0.490, 0.517] | 0.003 [-0.010, 0.017] | 0.044 [0.025, 0.071] | 0.763 [0.640, 0.850] | -0.260 [-0.342, -0.133] |
| class_mean | 2.0 | jlens | 0.504 [0.487, 0.522] | 0.004 [-0.013, 0.022] | 0.048 [0.026, 0.080] | 0.756 [0.638, 0.838] | -0.253 [-0.329, -0.134] |
| J_lens | 0.5 | jlens | 0.507 [0.487, 0.528] | 0.007 [-0.013, 0.028] | 0.044 [0.023, 0.074] | 0.738 [0.606, 0.822] | -0.231 [-0.310, -0.111] |
| J_lens | 1.0 | jlens | 0.517 [0.487, 0.544] | 0.017 [-0.013, 0.044] | 0.049 [0.027, 0.085] | 0.711 [0.582, 0.806] | -0.194 [-0.281, -0.075] |
| J_lens | 2.0 | jlens | 0.525 [0.493, 0.558] | 0.025 [-0.007, 0.058] | 0.054 [0.031, 0.102] | 0.663 [0.539, 0.767] | -0.138 [-0.235, -0.013] |
| Oracle_gradient | 0.5 | jlens | 0.504 [0.492, 0.518] | 0.004 [-0.008, 0.018] | 0.042 [0.023, 0.067] | 0.759 [0.630, 0.847] | -0.254 [-0.340, -0.131] |
| Oracle_gradient | 1.0 | jlens | 0.508 [0.491, 0.526] | 0.008 [-0.009, 0.026] | 0.048 [0.023, 0.077] | 0.747 [0.623, 0.836] | -0.239 [-0.325, -0.124] |
| Oracle_gradient | 2.0 | jlens | 0.509 [0.486, 0.536] | 0.009 [-0.014, 0.036] | 0.046 [0.023, 0.084] | 0.733 [0.596, 0.824] | -0.224 [-0.309, -0.099] |
| probe | 0.5 | jlens | 0.504 [0.496, 0.515] | 0.004 [-0.004, 0.015] | 0.043 [0.026, 0.068] | 0.765 [0.644, 0.850] | -0.261 [-0.341, -0.139] |
| probe | 1.0 | jlens | 0.505 [0.494, 0.519] | 0.005 [-0.006, 0.019] | 0.044 [0.026, 0.070] | 0.763 [0.646, 0.845] | -0.258 [-0.338, -0.143] |
| probe | 2.0 | jlens | 0.507 [0.493, 0.526] | 0.007 [-0.007, 0.026] | 0.045 [0.026, 0.074] | 0.758 [0.645, 0.842] | -0.250 [-0.329, -0.142] |
| random | 0.5 | jlens | 0.500 [0.497, 0.503] | 0.000 [-0.003, 0.003] | 0.047 [0.039, 0.062] | 0.771 [0.657, 0.850] | -0.270 [-0.350, -0.157] |
| random | 1.0 | jlens | 0.500 [0.495, 0.504] | -0.000 [-0.005, 0.004] | 0.046 [0.039, 0.062] | 0.771 [0.647, 0.856] | -0.271 [-0.356, -0.147] |
| random | 2.0 | jlens | 0.499 [0.492, 0.506] | -0.001 [-0.008, 0.006] | 0.047 [0.038, 0.063] | 0.770 [0.650, 0.856] | -0.271 [-0.357, -0.154] |
| class_mean | 0.5 | nla | 0.500 [0.489, 0.511] | 0.000 [-0.011, 0.011] | 0.037 [0.021, 0.067] | 0.761 [0.609, 0.867] | -0.261 [-0.362, -0.112] |
| class_mean | 1.0 | nla | 0.502 [0.489, 0.517] | 0.002 [-0.011, 0.017] | 0.043 [0.028, 0.078] | 0.755 [0.600, 0.855] | -0.253 [-0.350, -0.108] |
| class_mean | 2.0 | nla | 0.500 [0.483, 0.518] | -0.000 [-0.017, 0.018] | 0.044 [0.022, 0.085] | 0.749 [0.602, 0.855] | -0.249 [-0.348, -0.109] |
| J_lens | 0.5 | nla | 0.502 [0.490, 0.516] | 0.002 [-0.010, 0.016] | 0.040 [0.024, 0.069] | 0.755 [0.608, 0.861] | -0.254 [-0.353, -0.106] |
| J_lens | 1.0 | nla | 0.503 [0.488, 0.521] | 0.003 [-0.012, 0.021] | 0.040 [0.025, 0.070] | 0.743 [0.595, 0.850] | -0.240 [-0.341, -0.092] |
| J_lens | 2.0 | nla | 0.500 [0.483, 0.519] | 0.000 [-0.017, 0.019] | 0.039 [0.020, 0.066] | 0.724 [0.575, 0.828] | -0.224 [-0.323, -0.080] |
| Oracle_gradient | 0.5 | nla | 0.504 [0.494, 0.518] | 0.004 [-0.006, 0.018] | 0.046 [0.033, 0.076] | 0.754 [0.593, 0.865] | -0.250 [-0.351, -0.090] |
| Oracle_gradient | 1.0 | nla | 0.504 [0.490, 0.523] | 0.004 [-0.010, 0.023] | 0.043 [0.026, 0.070] | 0.742 [0.589, 0.852] | -0.237 [-0.340, -0.091] |
| Oracle_gradient | 2.0 | nla | 0.501 [0.484, 0.520] | 0.001 [-0.016, 0.020] | 0.039 [0.018, 0.071] | 0.721 [0.558, 0.844] | -0.221 [-0.329, -0.063] |
| probe | 0.5 | nla | 0.501 [0.491, 0.511] | 0.001 [-0.009, 0.011] | 0.042 [0.030, 0.076] | 0.763 [0.619, 0.862] | -0.262 [-0.358, -0.121] |
| probe | 1.0 | nla | 0.501 [0.489, 0.512] | 0.001 [-0.011, 0.012] | 0.043 [0.027, 0.078] | 0.760 [0.632, 0.867] | -0.259 [-0.362, -0.128] |
| probe | 2.0 | nla | 0.501 [0.488, 0.514] | 0.001 [-0.012, 0.014] | 0.042 [0.025, 0.076] | 0.752 [0.603, 0.854] | -0.251 [-0.350, -0.105] |
| random | 0.5 | nla | 0.500 [0.495, 0.505] | -0.000 [-0.005, 0.005] | 0.043 [0.035, 0.064] | 0.766 [0.611, 0.870] | -0.267 [-0.370, -0.112] |
| random | 1.0 | nla | 0.499 [0.494, 0.505] | -0.001 [-0.006, 0.005] | 0.042 [0.034, 0.064] | 0.767 [0.630, 0.877] | -0.267 [-0.375, -0.132] |
| random | 2.0 | nla | 0.499 [0.491, 0.506] | -0.001 [-0.009, 0.006] | 0.043 [0.035, 0.065] | 0.765 [0.619, 0.865] | -0.266 [-0.365, -0.124] |
| class_mean | 0.5 | olens | 0.504 [0.497, 0.515] | 0.004 [-0.003, 0.015] | 0.043 [0.028, 0.068] | 0.763 [0.625, 0.853] | -0.259 [-0.349, -0.123] |
| class_mean | 1.0 | olens | 0.506 [0.497, 0.520] | 0.006 [-0.003, 0.020] | 0.049 [0.031, 0.080] | 0.755 [0.613, 0.848] | -0.250 [-0.341, -0.103] |
| class_mean | 2.0 | olens | 0.508 [0.495, 0.527] | 0.008 [-0.005, 0.027] | 0.051 [0.035, 0.087] | 0.747 [0.626, 0.844] | -0.238 [-0.337, -0.103] |
| J_lens | 0.5 | olens | 0.503 [0.492, 0.516] | 0.003 [-0.008, 0.016] | 0.042 [0.026, 0.074] | 0.753 [0.616, 0.847] | -0.251 [-0.339, -0.114] |
| J_lens | 1.0 | olens | 0.505 [0.488, 0.522] | 0.005 [-0.012, 0.022] | 0.040 [0.026, 0.076] | 0.741 [0.602, 0.843] | -0.236 [-0.327, -0.100] |
| J_lens | 2.0 | olens | 0.511 [0.491, 0.533] | 0.011 [-0.009, 0.033] | 0.045 [0.030, 0.091] | 0.723 [0.583, 0.814] | -0.212 [-0.295, -0.080] |
| Oracle_gradient | 0.5 | olens | 0.506 [0.494, 0.523] | 0.006 [-0.006, 0.023] | 0.046 [0.028, 0.082] | 0.735 [0.583, 0.826] | -0.228 [-0.313, -0.082] |
| Oracle_gradient | 1.0 | olens | 0.510 [0.494, 0.529] | 0.010 [-0.006, 0.029] | 0.051 [0.025, 0.091] | 0.708 [0.566, 0.801] | -0.198 [-0.287, -0.059] |
| Oracle_gradient | 2.0 | olens | 0.515 [0.491, 0.547] | 0.015 [-0.009, 0.047] | 0.051 [0.029, 0.106] | 0.659 [0.523, 0.767] | -0.145 [-0.249, -0.004] |
| probe | 0.5 | olens | 0.501 [0.494, 0.511] | 0.001 [-0.006, 0.011] | 0.043 [0.026, 0.067] | 0.762 [0.618, 0.850] | -0.261 [-0.353, -0.109] |
| probe | 1.0 | olens | 0.503 [0.494, 0.514] | 0.003 [-0.006, 0.014] | 0.045 [0.026, 0.069] | 0.756 [0.616, 0.847] | -0.253 [-0.346, -0.110] |
| probe | 2.0 | olens | 0.506 [0.495, 0.524] | 0.006 [-0.005, 0.024] | 0.055 [0.033, 0.089] | 0.750 [0.603, 0.844] | -0.244 [-0.341, -0.091] |
| random | 0.5 | olens | 0.499 [0.496, 0.503] | -0.001 [-0.004, 0.003] | 0.041 [0.032, 0.058] | 0.766 [0.625, 0.860] | -0.267 [-0.363, -0.125] |
| random | 1.0 | olens | 0.500 [0.497, 0.505] | 0.000 [-0.003, 0.005] | 0.044 [0.034, 0.061] | 0.766 [0.631, 0.849] | -0.266 [-0.349, -0.128] |
| random | 2.0 | olens | 0.502 [0.497, 0.509] | 0.002 [-0.003, 0.009] | 0.047 [0.037, 0.067] | 0.765 [0.624, 0.854] | -0.263 [-0.354, -0.118] |
| class_mean | 0.5 | skip_a | 0.505 [0.496, 0.517] | 0.005 [-0.004, 0.017] | 0.047 [0.029, 0.068] | 0.801 [0.659, 0.884] | -0.296 [-0.380, -0.156] |
| class_mean | 1.0 | skip_a | 0.507 [0.494, 0.522] | 0.007 [-0.006, 0.022] | 0.045 [0.023, 0.069] | 0.796 [0.664, 0.881] | -0.289 [-0.373, -0.160] |
| class_mean | 2.0 | skip_a | 0.507 [0.491, 0.527] | 0.007 [-0.009, 0.027] | 0.049 [0.023, 0.073] | 0.789 [0.660, 0.877] | -0.282 [-0.366, -0.155] |
| J_lens | 0.5 | skip_a | 0.505 [0.494, 0.521] | 0.005 [-0.006, 0.021] | 0.048 [0.026, 0.069] | 0.793 [0.650, 0.886] | -0.288 [-0.381, -0.147] |
| J_lens | 1.0 | skip_a | 0.510 [0.492, 0.534] | 0.010 [-0.008, 0.034] | 0.050 [0.027, 0.080] | 0.784 [0.659, 0.875] | -0.274 [-0.362, -0.155] |
| J_lens | 2.0 | skip_a | 0.513 [0.494, 0.541] | 0.013 [-0.006, 0.041] | 0.043 [0.025, 0.081] | 0.767 [0.634, 0.856] | -0.254 [-0.339, -0.130] |
| Oracle_gradient | 0.5 | skip_a | 0.508 [0.497, 0.526] | 0.008 [-0.003, 0.026] | 0.045 [0.022, 0.070] | 0.792 [0.654, 0.877] | -0.284 [-0.363, -0.150] |
| Oracle_gradient | 1.0 | skip_a | 0.513 [0.499, 0.534] | 0.013 [-0.001, 0.034] | 0.053 [0.027, 0.083] | 0.782 [0.655, 0.873] | -0.269 [-0.353, -0.149] |
| Oracle_gradient | 2.0 | skip_a | 0.514 [0.496, 0.543] | 0.014 [-0.004, 0.043] | 0.045 [0.023, 0.084] | 0.767 [0.636, 0.856] | -0.253 [-0.335, -0.127] |
| probe | 0.5 | skip_a | 0.504 [0.496, 0.516] | 0.004 [-0.004, 0.016] | 0.048 [0.029, 0.070] | 0.800 [0.667, 0.882] | -0.296 [-0.375, -0.161] |
| probe | 1.0 | skip_a | 0.507 [0.497, 0.521] | 0.007 [-0.003, 0.021] | 0.050 [0.028, 0.073] | 0.796 [0.659, 0.883] | -0.289 [-0.373, -0.153] |
| probe | 2.0 | skip_a | 0.509 [0.496, 0.526] | 0.009 [-0.004, 0.026] | 0.048 [0.028, 0.072] | 0.790 [0.663, 0.880] | -0.282 [-0.372, -0.155] |
| random | 0.5 | skip_a | 0.501 [0.497, 0.505] | 0.001 [-0.003, 0.005] | 0.046 [0.035, 0.061] | 0.805 [0.671, 0.891] | -0.304 [-0.392, -0.170] |
| random | 1.0 | skip_a | 0.501 [0.498, 0.506] | 0.001 [-0.002, 0.006] | 0.048 [0.038, 0.063] | 0.805 [0.668, 0.887] | -0.304 [-0.385, -0.164] |
| random | 2.0 | skip_a | 0.501 [0.496, 0.506] | 0.001 [-0.004, 0.006] | 0.047 [0.037, 0.062] | 0.805 [0.664, 0.890] | -0.305 [-0.390, -0.162] |

## SWAP layer 24: state detectors and native confidence — DESCRIPTIVE

SWAP has one corpus per reported part; item intervals cannot establish corpus generality. The geometry readback is L42; layer below is the edit site. Pool geometry never fits the test readbacks. Top-384 J energy uses a fixed approximate SVD of J42. Comparators at all layers and all arms are in `summary.json`.

| part / pair | arm | detector | AUROC [95% CI] | ΔAUROC [95% CI] | TPR@5% FPR [95% CI] | ΔTPR vs natural FPR [95% CI] |
|---|---|---|---|---|---|---|
| bridge | class_mean | jlens:abs_lo_low | 0.474 [0.383, 0.566] | -0.026 [-0.117, 0.066] | 0.029 [0.000, 0.162] | -0.015 [-0.044, 0.118] |
| bridge | random | jlens:abs_lo_low | 0.498 [0.489, 0.507] | -0.002 [-0.011, 0.007] | 0.031 [0.019, 0.063] | -0.016 [-0.026, 0.019] |
| bridge | d_swap | jlens:abs_lo_low | 0.349 [0.290, 0.403] | -0.151 [-0.210, -0.097] | 0.010 [0.000, 0.042] | -0.036 [-0.047, -0.005] |
| bridge | class_mean | nla:abs_lo_low | 0.501 [0.413, 0.589] | 0.001 [-0.087, 0.089] | 0.015 [0.000, 0.132] | -0.029 [-0.044, 0.088] |
| bridge | random | nla:abs_lo_low | 0.518 [0.506, 0.530] | 0.018 [0.006, 0.030] | 0.047 [0.023, 0.078] | 0.000 [-0.021, 0.031] |
| bridge | d_swap | nla:abs_lo_low | 0.489 [0.437, 0.542] | -0.011 [-0.063, 0.042] | 0.042 [0.016, 0.083] | -0.005 [-0.031, 0.042] |
| bridge | class_mean | olens:abs_lo_low | 0.564 [0.473, 0.663] | 0.064 [-0.027, 0.163] | 0.074 [0.015, 0.235] | 0.044 [-0.015, 0.192] |
| bridge | random | olens:abs_lo_low | 0.511 [0.504, 0.520] | 0.011 [0.004, 0.020] | 0.059 [0.038, 0.083] | 0.012 [-0.007, 0.042] |
| bridge | d_swap | olens:abs_lo_low | 0.478 [0.420, 0.534] | -0.022 [-0.080, 0.034] | 0.078 [0.036, 0.141] | 0.031 [-0.005, 0.099] |
| bridge | class_mean | skip_a:abs_lo_low | 0.489 [0.404, 0.592] | -0.011 [-0.096, 0.092] | 0.044 [0.000, 0.103] | 0.000 [-0.044, 0.059] |
| bridge | random | skip_a:abs_lo_low | 0.504 [0.494, 0.514] | 0.004 [-0.006, 0.014] | 0.089 [0.049, 0.111] | 0.042 [0.003, 0.066] |
| bridge | d_swap | skip_a:abs_lo_low | 0.450 [0.391, 0.503] | -0.050 [-0.109, 0.003] | 0.052 [0.010, 0.089] | 0.005 [-0.036, 0.042] |
| bridge | class_mean | state:mahalanobis | 0.963 [0.935, 0.987] | 0.463 [0.435, 0.487] | 0.750 [0.441, 0.942] | 0.706 [0.426, 0.912] |
| bridge | class_mean | state:knn | 0.864 [0.810, 0.914] | 0.364 [0.310, 0.414] | 0.500 [0.250, 0.706] | 0.456 [0.221, 0.662] |
| bridge | class_mean | state:norm | 0.381 [0.334, 0.425] | -0.119 [-0.166, -0.075] | 0.029 [0.000, 0.074] | -0.015 [-0.044, 0.029] |
| bridge | class_mean | state:j_energy | 0.640 [0.574, 0.709] | 0.140 [0.074, 0.209] | 0.147 [0.088, 0.294] | 0.103 [0.044, 0.265] |
| bridge | random | state:mahalanobis | 0.823 [0.793, 0.855] | 0.323 [0.293, 0.355] | 0.257 [0.088, 0.368] | 0.210 [0.049, 0.321] |
| bridge | random | state:knn | 0.675 [0.646, 0.706] | 0.175 [0.146, 0.206] | 0.149 [0.083, 0.241] | 0.102 [0.040, 0.194] |
| bridge | random | state:norm | 0.484 [0.471, 0.496] | -0.016 [-0.029, -0.004] | 0.061 [0.036, 0.073] | 0.014 [-0.009, 0.030] |
| bridge | random | state:j_energy | 0.496 [0.476, 0.516] | -0.004 [-0.024, 0.016] | 0.073 [0.040, 0.101] | 0.026 [-0.003, 0.057] |
| bridge | d_swap | state:mahalanobis | 0.942 [0.921, 0.962] | 0.442 [0.421, 0.462] | 0.646 [0.354, 0.792] | 0.599 [0.318, 0.745] |
| bridge | d_swap | state:knn | 0.827 [0.798, 0.858] | 0.327 [0.298, 0.358] | 0.406 [0.286, 0.573] | 0.359 [0.240, 0.526] |
| bridge | d_swap | state:norm | 0.357 [0.328, 0.381] | -0.143 [-0.172, -0.119] | 0.010 [0.000, 0.026] | -0.036 [-0.047, -0.016] |
| bridge | d_swap | state:j_energy | 0.663 [0.624, 0.704] | 0.163 [0.124, 0.204] | 0.245 [0.140, 0.339] | 0.198 [0.094, 0.292] |

## Specificity and limits

Natural-vs-natural checks use 100 fixed random half-splits. Their mean null AUROC and held-out false-positive rate are saved for every detector/condition in `summary.json`; these resample the same finite natural bank and are not an independent validation set. With 32 natural R5 states, a 5% ROC operating point allows one false positive; a half-split has only 16 calibration items, so its threshold is the maximum and its expected held-out FPR can exceed 5%. TPR confidence intervals include re-estimation of the threshold.

No direction or dose was selected using detectability. Useful-at-dose flags are conditional on the model-flip criterion and on the observed candidate doses; thresholds are preregistered but the original R5/SWAP aggregates were public before this analysis. Per-fact values and all useful-at-lowest-dose flags are in the cache. Source row provenance is incomplete: analysis pod/git/code stamps and source hashes are present, but the original missing stamps are not invented.

The confidence-vs-content comparison does not make a useful-detector claim when no dose reaches the model-flip gate. A high score for one confidence orientation is not selected over the other. The random and class-mean controls are essential: a generic response to any activation edit is not specific to report-flipping edits.

## Reproduction

`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.remainder_r1 --smoke`

`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.remainder_r1 --run --bootstrap 1000`

Plan: `PLAN.md`; audit: `audit.json`; full small aggregate table: `summary.json`; per-cell metrics and paired score vectors: `cache/g_agreement/r/remainder/r1/`. A strict completeness check is `--smoke --strict` and intentionally exits nonzero until the missing original artifacts are available.
