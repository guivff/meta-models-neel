# W11 §87 registered analysis

W11 §87: CONFIRMED, 9/9 Oracle-evaluable features (100%; Wilson 95% CI 70.1–100%); number_digits_ge_3 excluded: random-donor AUROC 0.3867 outside [0.40,0.60]. All 20 native probes AUROC 1.000; all 20 pretarget probes 0.500. NLA comparisons DESCRIPTIVE.

Frozen code ran once; capture/score seals, complete grid, source/input lineage verified before labels. Six held-out context clusters and 60 test items per feature. No sign reversal.

| Feature | Oracle AUROC [95% CI] | NLA AUROC [95% CI] | NLA − Oracle [95% CI], descriptive | Oracle gate | Confirms |
|---|---|---|---|---|---|
| wordlist_preposition | 0.589 [0.428, 0.708] | 0.571 [0.424, 0.722] | -0.018 [-0.163, +0.130] | EVALUABLE | True |
| word_allcaps | 0.706 [0.604, 0.842] | 0.881 [0.847, 0.971] | +0.176 [+0.029, +0.333] | EVALUABLE | True |
| current_colon | 0.273 [0.083, 0.418] | 0.612 [0.264, 0.866] | +0.339 [+0.084, +0.616] | EVALUABLE | True |
| number_magnitude_ge_1000 | 0.688 [0.524, 0.807] | 1.000 [1.000, 1.000] | +0.312 [+0.193, +0.476] | EVALUABLE | True |
| number_digits_ge_3 | 0.580 [0.470, 0.706] | 0.887 [0.771, 0.993] | +0.307 [+0.118, +0.496] | NOT EVALUABLE | False |
| current_number | 0.550 [0.375, 0.747] | 0.477 [0.214, 0.709] | -0.073 [-0.458, +0.272] | EVALUABLE | True |
| number_digits_ge_4 | 0.820 [0.704, 0.909] | 1.000 [1.000, 1.000] | +0.180 [+0.091, +0.296] | EVALUABLE | True |
| number_magnitude_ge_10 | 0.331 [0.158, 0.560] | 0.990 [0.983, 1.000] | +0.659 [+0.440, +0.832] | EVALUABLE | True |
| number_magnitude_ge_100 | 0.743 [0.630, 0.863] | 0.963 [0.893, 1.000] | +0.220 [+0.090, +0.348] | EVALUABLE | True |
| wordlist_auxiliary | 0.566 [0.473, 0.680] | 0.644 [0.449, 0.810] | +0.079 [-0.160, +0.231] | EVALUABLE | True |

This registered gap rule does not assert the Oracle is at chance on every feature. Agreement with §84 remains pending its sealed analysis.
