# Z1 reporting — reader gain over the dose-only reference (Z4 edits, Z1-on-Z4; 2026-10-09; CPU only, 0 forward passes)

Rule (BRIEF_Z deviation 2026-10-09 "Z1 reporting"): ΔAUROC = AUROC(reader's flip prediction) − AUROC(dose-only prediction) on the same entries; paired pair-level bootstrap (1000 resamples, seed 0: pairs resampled once, both AUROCs recomputed on the resample). **beats dose** only if the 95% CI lies above 0; **does not beat dose** if it lies below 0; otherwise **indistinguishable from dose**.
Predictions are E1's: 8 pair-family folds (seed 0); reader = logistic flip ~ f_r; dose = training-fold flip rate of the entry's arm × α cell (E1's CellModel). Dose predictions are made on every entry of the set (as in E1) and restricted to the reader's entries (pairs a reader excludes for |sep_r| < 1e-4 leave both AUROCs). '| family' rows restrict the primary set's out-of-fold predictions to one family; E3 rows use E3's held-out-family transfer fits.

| set | kind | reader | n (flips) | reader AUROC | dose AUROC (same entries) | ΔAUROC [95% CI] | P(Δ ≤ 0) | verdict |
|---|---|---|---|---|---|---|---|---|
| single+pair2+all_except | E1 out-of-fold | Oracle lens | 4710 (730) | 0.953 | 0.896 | +0.057 [+0.024, +0.090] | 0.000 | **beats dose** |
| single+pair2+all_except | E1 out-of-fold | NLA | 5080 (782) | 0.731 | 0.896 | -0.165 [-0.225, -0.094] | 1.000 | **does not beat dose** |
| single+pair2+all_except | E1 out-of-fold | J-lens | 5080 (782) | 0.941 | 0.896 | +0.045 [+0.007, +0.082] | 0.012 | **beats dose** |
| single | E1 out-of-fold | Oracle lens | 3600 (111) | 0.852 | 0.464 | +0.388 [+0.270, +0.494] | 0.000 | **beats dose** |
| single | E1 out-of-fold | NLA | 3840 (119) | 0.412 | 0.480 | -0.068 [-0.191, +0.045] | 0.899 | **indistinguishable from dose** |
| single | E1 out-of-fold | J-lens | 3840 (119) | 0.861 | 0.480 | +0.381 [+0.271, +0.487] | 0.000 | **beats dose** |
| pair2 | E1 out-of-fold | Oracle lens | 510 (79) | 0.865 | 0.466 | +0.399 [+0.202, +0.569] | 0.002 | **beats dose** |
| pair2 | E1 out-of-fold | NLA | 600 (87) | 0.357 | 0.460 | -0.103 [-0.289, +0.155] | 0.834 | **indistinguishable from dose** |
| pair2 | E1 out-of-fold | J-lens | 600 (87) | 0.609 | 0.460 | +0.149 [-0.021, +0.359] | 0.038 | **indistinguishable from dose** |
| all_except | E1 out-of-fold | Oracle lens | 600 (540) | 0.780 | 0.435 | +0.345 [+0.199, +0.482] | 0.000 | **beats dose** |
| all_except | E1 out-of-fold | NLA | 640 (576) | 0.391 | 0.431 | -0.040 [-0.149, +0.056] | 0.829 | **indistinguishable from dose** |
| all_except | E1 out-of-fold | J-lens | 640 (576) | 0.819 | 0.431 | +0.388 [+0.274, +0.524] | 0.000 | **beats dose** |
| single+pair2+all_except, ownership only | E1 out-of-fold, one family | Oracle lens | 2340 (300) | 0.995 | 1.000 | -0.005 [-0.009, -0.002] | 1.000 | **does not beat dose** |
| single+pair2+all_except, ownership only | E1 out-of-fold, one family | NLA | 2540 (320) | 0.856 | 1.000 | -0.144 [-0.210, -0.068] | 1.000 | **does not beat dose** |
| single+pair2+all_except, ownership only | E1 out-of-fold, one family | J-lens | 2540 (320) | 0.992 | 1.000 | -0.008 [-0.013, -0.003] | 1.000 | **does not beat dose** |
| single+pair2+all_except, mapping only | E1 out-of-fold, one family | Oracle lens | 2370 (430) | 0.920 | 0.826 | +0.094 [+0.039, +0.139] | 0.000 | **beats dose** |
| single+pair2+all_except, mapping only | E1 out-of-fold, one family | NLA | 2540 (462) | 0.641 | 0.826 | -0.185 [-0.265, -0.084] | 1.000 | **does not beat dose** |
| single+pair2+all_except, mapping only | E1 out-of-fold, one family | J-lens | 2540 (462) | 0.902 | 0.826 | +0.077 [+0.012, +0.134] | 0.009 | **beats dose** |
| ownership->mapping | E3 held-out family | Oracle lens | 2370 (430) | 0.920 | 0.764 | +0.157 [+0.090, +0.208] | 0.000 | **beats dose** |
| ownership->mapping | E3 held-out family | NLA | 2540 (462) | 0.757 | 0.762 | -0.005 [-0.103, +0.091] | 0.537 | **indistinguishable from dose** |
| ownership->mapping | E3 held-out family | J-lens | 2540 (462) | 0.912 | 0.762 | +0.150 [+0.081, +0.209] | 0.000 | **beats dose** |
| mapping->ownership | E3 held-out family | Oracle lens | 2340 (300) | 0.996 | 1.000 | -0.004 [-0.008, -0.001] | 1.000 | **does not beat dose** |
| mapping->ownership | E3 held-out family | NLA | 2540 (320) | 0.035 | 1.000 | -0.965 [-0.989, -0.935] | 1.000 | **does not beat dose** |
| mapping->ownership | E3 held-out family | J-lens | 2540 (320) | 0.993 | 1.000 | -0.007 [-0.012, -0.002] | 1.000 | **does not beat dose** |

Tally per reader: Oracle lens: beats dose 6, does not beat dose 2; NLA: indistinguishable from dose 4, does not beat dose 4; J-lens: beats dose 5, indistinguishable from dose 1, does not beat dose 2.
Bootstrap resamples with an undefined AUROC (one class absent) are dropped: 0 in total. ΔAUROC point estimate = full-sample difference; bootstrap mean and the separate reader / dose CIs are in gain_over_dose.csv (auroc_dose_all_entries = E1's dose AUROC on all entries).
Command: `PYTHONPATH=. .venv/bin/python projects/g_agreement/z1_intervention/analyze.py --behaviour cache/g_agreement/z/z4_behaviour.jsonl --lo cache/g_agreement/z/z4_lo.jsonl --natural-behaviour cache/g_agreement/x/x2_behaviour.jsonl --natural-lo cache/g_agreement/x/x2_lo.jsonl --arms single,pair2,all_except --n-boot 1000 --folds 8 --seed 0 --out results/g_agreement/z4/z1_on_z4 --gain-over-dose` (wall 9.6 s). Only gain_over_dose.csv and gain_over_dose.md are written; the E1–E5 files in this directory are untouched.
