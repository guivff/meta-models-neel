# Z1 reporting — reader gain over the dose-only reference (X2; 2026-10-09; CPU only, 0 forward passes)

Rule (BRIEF_Z deviation 2026-10-09 "Z1 reporting"): ΔAUROC = AUROC(reader's flip prediction) − AUROC(dose-only prediction) on the same entries; paired pair-level bootstrap (1000 resamples, seed 0: pairs resampled once, both AUROCs recomputed on the resample). **beats dose** only if the 95% CI lies above 0; **does not beat dose** if it lies below 0; otherwise **indistinguishable from dose**.
Predictions are E1's: 8 pair-family folds (seed 0); reader = logistic flip ~ f_r; dose = logistic flip ~ α (E1's dose-only reference). Dose predictions are made on every entry of the set (as in E1) and restricted to the reader's entries (pairs a reader excludes for |sep_r| < 1e-4 leave both AUROCs). E3 rows use E3's transfer fits (train family/site → test).

| set | kind | reader | n (flips) | reader AUROC | dose AUROC (same entries) | ΔAUROC [95% CI] | P(Δ ≤ 0) | verdict |
|---|---|---|---|---|---|---|---|---|
| S2+S3 | E1 out-of-fold | Oracle lens | 960 (582) | 0.907 | 0.946 | -0.039 [-0.071, -0.011] | 1.000 | **does not beat dose** |
| S2+S3 | E1 out-of-fold | NLA | 1024 (620) | 0.804 | 0.947 | -0.143 [-0.181, -0.108] | 1.000 | **does not beat dose** |
| S2+S3 | E1 out-of-fold | J-lens | 1024 (620) | 0.904 | 0.947 | -0.042 [-0.076, -0.015] | 1.000 | **does not beat dose** |
| S2 | E1 out-of-fold | Oracle lens | 480 (292) | 0.908 | 0.949 | -0.041 [-0.075, -0.013] | 0.999 | **does not beat dose** |
| S2 | E1 out-of-fold | NLA | 512 (311) | 0.778 | 0.950 | -0.172 [-0.222, -0.130] | 1.000 | **does not beat dose** |
| S2 | E1 out-of-fold | J-lens | 512 (311) | 0.872 | 0.950 | -0.078 [-0.127, -0.036] | 1.000 | **does not beat dose** |
| S3 | E1 out-of-fold | Oracle lens | 480 (290) | 0.905 | 0.942 | -0.037 [-0.082, -0.005] | 0.995 | **does not beat dose** |
| S3 | E1 out-of-fold | NLA | 512 (309) | 0.832 | 0.943 | -0.111 [-0.149, -0.076] | 1.000 | **does not beat dose** |
| S3 | E1 out-of-fold | J-lens | 512 (309) | 0.940 | 0.943 | -0.003 [-0.026, +0.016] | 0.600 | **indistinguishable from dose** |
| ownership->mapping | E3 held-out family | Oracle lens | 480 (283) | 0.865 | 0.938 | -0.073 [-0.123, -0.031] | 1.000 | **does not beat dose** |
| ownership->mapping | E3 held-out family | NLA | 512 (301) | 0.772 | 0.940 | -0.168 [-0.208, -0.123] | 1.000 | **does not beat dose** |
| ownership->mapping | E3 held-out family | J-lens | 512 (301) | 0.859 | 0.940 | -0.082 [-0.140, -0.035] | 1.000 | **does not beat dose** |
| mapping->ownership | E3 held-out family | Oracle lens | 480 (299) | 0.953 | 0.967 | -0.013 [-0.034, +0.005] | 0.898 | **indistinguishable from dose** |
| mapping->ownership | E3 held-out family | NLA | 512 (319) | 0.861 | 0.967 | -0.106 [-0.162, -0.051] | 1.000 | **does not beat dose** |
| mapping->ownership | E3 held-out family | J-lens | 512 (319) | 0.956 | 0.967 | -0.011 [-0.032, +0.009] | 0.844 | **indistinguishable from dose** |
| S2->S3 | E3 held-out site | Oracle lens | 480 (290) | 0.908 | 0.949 | -0.040 [-0.079, -0.010] | 0.998 | **does not beat dose** |
| S2->S3 | E3 held-out site | NLA | 512 (309) | 0.839 | 0.950 | -0.111 [-0.149, -0.075] | 1.000 | **does not beat dose** |
| S2->S3 | E3 held-out site | J-lens | 512 (309) | 0.943 | 0.950 | -0.007 [-0.030, +0.011] | 0.747 | **indistinguishable from dose** |
| S3->S2 | E3 held-out site | Oracle lens | 480 (292) | 0.909 | 0.955 | -0.046 [-0.077, -0.018] | 0.999 | **does not beat dose** |
| S3->S2 | E3 held-out site | NLA | 512 (311) | 0.791 | 0.956 | -0.165 [-0.211, -0.119] | 1.000 | **does not beat dose** |
| S3->S2 | E3 held-out site | J-lens | 512 (311) | 0.872 | 0.956 | -0.084 [-0.132, -0.042] | 1.000 | **does not beat dose** |

Tally per reader: Oracle lens: indistinguishable from dose 1, does not beat dose 6; NLA: does not beat dose 7; J-lens: indistinguishable from dose 3, does not beat dose 4.
Bootstrap resamples with an undefined AUROC (one class absent) are dropped: 0 in total. ΔAUROC point estimate = full-sample difference; bootstrap mean and the separate reader / dose CIs are in gain_over_dose.csv (auroc_dose_all_entries = E1's dose AUROC on all entries).
Command: `PYTHONPATH=. .venv/bin/python projects/g_agreement/z1_intervention/analyze.py --beh /Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/x/x2_behaviour.jsonl --lo /Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/x/x2_lo.jsonl --n-boot 1000 --folds 8 --seed 0 --out results/g_agreement/z1 --gain-over-dose` (wall 4.5 s). Only gain_over_dose.csv and gain_over_dose.md are written; the E1–E5 files in this directory are untouched.
