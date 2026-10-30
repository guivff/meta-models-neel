# RS44 reader self-monitoring

Status: **COMPLETE**.

Primary Oracle and prespecified secondary J++ are separate claims; no best-reader verdict.

## primary

Items 4000; facts 20; AUROC support 2800 items / 14 facts; state-dependent positives 820.

| Reader | Natural AUROC | R2 − optimistic margin (95% envelope) | R2 − shuffled (95% envelope) | Verdict |
|---|---:|---|---|---|
| oracle | 0.4273 | -0.2040 [-0.33114825971221823, -0.09229731137468] | -0.0161 [-0.06255212996746165, 0.031212614766786266] | INCONCLUSIVE |
| jpp | 0.5834 | -0.0479 [-0.12892608907173525, 0.02934277633292213] | 0.0140 [-0.035185385984381444, 0.06569178898582988] | INCONCLUSIVE |

Matched adapter-disabled base-state reference (all cohort items):

| Diagnostic | Mean | Median | 5th–95th percentile |
|---|---:|---:|---|
| natural_norm | 117.81 | 118.73 | [108.81, 125.35] |
| base_norm | 95.805 | 96.549 | [84.972, 106.89] |
| base_natural_cosine | 0.77639 | 0.77968 | [0.72769, 0.81546] |
| base_natural_l2 | 74.421 | 74.222 | [67.054, 81.314] |

J++ conflict-token probability mass (descriptive; rankings use log mass):

| State condition | Mean mass | Median mass |
|---|---:|---:|
| natural | 0.0165569 | 0.000111504 |
| shuffled | 0.0165569 | 0.000111504 |
| random | 9.61215e-05 | 4.3395e-05 |
| base | 0.0280232 | 1.07157e-05 |

## x2

Items 100; facts 30; AUROC support 20 items / 4 facts; state-dependent positives 9.

| Reader | Natural AUROC | R2 − optimistic margin (95% envelope) | R2 − shuffled (95% envelope) | Verdict |
|---|---:|---|---|---|
| oracle | 0.3521 | -0.3146 [-0.95, 0.10416666666666663] | 0.0771 [-0.45000000000000007, 0.625] | DESCRIPTIVE_X2_NO_VERDICT |
| jpp | 0.6917 | 0.0250 [-0.4, 0.375] | 0.1000 [-0.125, 0.41666666666666663] | DESCRIPTIVE_X2_NO_VERDICT |

Matched adapter-disabled base-state reference (all cohort items):

| Diagnostic | Mean | Median | 5th–95th percentile |
|---|---:|---:|---|
| natural_norm | 120.95 | 120.65 | [114, 128.92] |
| base_norm | 98.565 | 100.62 | [86.559, 104.42] |
| base_natural_cosine | 0.78553 | 0.77881 | [0.73431, 0.83431] |
| base_natural_l2 | 74.945 | 74.105 | [66.783, 85.37] |

J++ conflict-token probability mass (descriptive; rankings use log mass):

| State condition | Mean mass | Median mass |
|---|---:|---:|
| natural | 0.000321265 | 5.24205e-06 |
| shuffled | 0.00017786 | 7.22209e-06 |
| random | 0.000117016 | 5.11621e-05 |
| base | 2.71337e-05 | 1.77977e-07 |

Facts absent from LR training: 116_nyc_borough_Bronx, 122_us_timezone_Los_Angeles, 133_context_type_Causality, 142_cancer_cat_Thyroid_Cancer, 143_cancer_cat_Lung_Cancer, 144_cancer_cat_Colon_Cancer, 147_disease_class_nervous system diseases, 149_twt_emotion_happiness, 151_it_tick_HR Support, 152_it_tick_Hardware, 156_athlete_sport_baseball, 157_amazon_5star, 24_headline_isiran, 47_reasoning_tf, 48_cm_correct, 56_wikidatasex_or_gender, 58_wikidatapolitical_party, 61_wikidata_occupation_isactor, 62_wikidata_occupation_ispolitician, 6_hist_fig_isamerican, 74_magnetic-field, 76_trial-court, 77_second-derivative, 91_glue_qqp, 95_toxic_is.

Selective accuracy is R1 task correctness, not state-dependence classification accuracy.

- Finite-pair answer dependence is not correctness or all causal use.
- Shuffled-run states may contain information about the same pair-level target.
- Polarity-free margin is an optimistic outcome-evaluated benchmark.
- Probe intervals condition on one fitted pool draw.
- A 90% interval containing chance is not equivalence to chance.
- X2 overlaps the primary cohort and is reported separately, without verdicts.
