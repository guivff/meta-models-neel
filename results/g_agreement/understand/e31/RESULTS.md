# E31(i) — CPU local-cue stratification, 25 October 2026

Prediction (local cue): Oracle continuation AUROC ≥0.75 in the informative stratum and ≤0.60 in the uninformative stratum. Prediction (remote state): both ≥0.70. These are per-row point rules; no global verdict or pooling is introduced.

| Row | Dev cutoff | Informative n (A/B) | Oracle AUROC [95% CI] | Uninformative n (A/B) | Oracle AUROC [95% CI] | Local cue / remote |
|---|---:|---:|---|---:|---|---|
| prose_paren | 0 | 0 (0/0) | NOT EVALUABLE | 84 (42/42) | 0.7126 [0.5937, 0.8189] | NOT EVALUABLE |
| prose_quote | 0 | 0 (0/0) | NOT EVALUABLE | 84 (42/42) | 0.7971 [0.6888, 0.8852] | NOT EVALUABLE |
| python_string | 0.525915 | 30 (12/18) | 1.0000 [1.0000, 1.0000] | 54 (30/24) | 0.9083 [0.8236, 0.9738] | False / True |
| python_indent | 0 | 0 (0/0) | NOT EVALUABLE | 84 (42/42) | 0.7817 [0.6772, 0.8744] | NOT EVALUABLE |
| python_depth | 0.388194 | 54 (25/29) | 0.8221 [0.7005, 0.9286] | 30 (17/13) | 0.8100 [0.6411, 0.9422] | False / True |
| list_depth | 0 | 0 (0/0) | NOT EVALUABLE | 84 (42/42) | 0.3180 [0.2072, 0.4392] | NOT EVALUABLE |
| table_role | 0.467049 | 0 (0/0) | NOT EVALUABLE | 84 (42/42) | 0.8172 [0.7208, 0.9016] | NOT EVALUABLE |

Descriptive counts among 2 rows with both strata evaluable: local-cue point pattern 0; remote-state point pattern 2. 5 rows lack two evaluable strata. No across-row success criterion is specified.

Strata, models and thresholds were frozen before raw E15 outcome access. The dev cutoff is the median absolute probability margin |p_A−p_B|; informative means strictly greater than the cutoff, so ties are uninformative. Suffix convention: `include_read`. No classifier, cutoff, valid pair or score sign was refitted/changed during this analysis.

All 21 full-test Oracle true/random and NLA true AUROCs reproduce sealed E15 values within 1e-12. E15 uses summed candidate-token log-probability differences, averaged over its two previously valid continuation pairs, with value-A positive. E25's token normalization is not applied.

Within each stratum, 2,000 iid item bootstrap resamples share indices across Oracle true, Oracle random-donor and descriptive NLA arms. The true-minus-random contrast is paired. Informative-minus-uninformative contrasts combine independent within-stratum resamples by replicate index. Confidence intervals condition on the frozen classifier, cutoff and stratum assignments; they do not include fitting uncertainty. Empty/single-class strata and undefined one-class draws are reported explicitly; they are never assigned AUROC0.5.

## Oracle controls and stratum contrasts

| Row | Stratum | Random-donor AUROC [95% CI] | True − random [95% CI] |
|---|---|---|---|
| prose_paren | informative | NOT EVALUABLE | NOT EVALUABLE |
| prose_paren | uninformative | 0.4753 [0.3460, 0.5955] | 0.2372; CI [0.1445087139423077, 0.33669385324637985] |
| prose_paren | informative − uninformative | Oracle true contrast | None ; CI None |
| prose_quote | informative | NOT EVALUABLE | NOT EVALUABLE |
| prose_quote | uninformative | 0.4983 [0.3770, 0.6233] | 0.2988; CI [0.20407990047871, 0.40251009778911556] |
| prose_quote | informative − uninformative | Oracle true contrast | None ; CI None |
| python_string | informative | 0.7361 [0.5226, 0.9258] | 0.2639; CI [0.07416046429204323, 0.47738314075630245] |
| python_string | uninformative | 0.5278 [0.3633, 0.6931] | 0.3806; CI [0.1886304589640664, 0.5590012051455916] |
| python_string | informative − uninformative | Oracle true contrast | 0.09166666666666667 ; CI [0.02620419666540357, 0.17636917182636055] |
| python_indent | informative | NOT EVALUABLE | NOT EVALUABLE |
| python_indent | uninformative | 0.5034 [0.3804, 0.6236] | 0.2783; CI [0.17520053475935835, 0.3921601974122983] |
| python_indent | informative − uninformative | Oracle true contrast | None ; CI None |
| python_depth | informative | 0.4800 [0.3262, 0.6368] | 0.3421; CI [0.16159299895506785, 0.522742882117882] |
| python_depth | uninformative | 0.5995 [0.3925, 0.7987] | 0.2104; CI [-0.005328413416648656, 0.4444577352472089] |
| python_depth | informative − uninformative | Oracle true contrast | 0.012114214386019673 ; CI [-0.1791344348264987, 0.21059099616858235] |
| list_depth | informative | NOT EVALUABLE | NOT EVALUABLE |
| list_depth | uninformative | 0.5079 [0.3871, 0.6338] | -0.1899; CI [-0.2972085673923051, -0.08425147318333658] |
| list_depth | informative − uninformative | Oracle true contrast | None ; CI None |
| table_role | informative | NOT EVALUABLE | NOT EVALUABLE |
| table_role | uninformative | 0.5187 [0.3932, 0.6438] | 0.2985; CI [0.1507357981771598, 0.44177442831088665] |
| table_role | informative − uninformative | Oracle true contrast | None ; CI None |

## Descriptive NLA appendix

NLA continuation scoring is off its native explanation format and is descriptive only.

| Row | Informative AUROC [95% CI] | Uninformative AUROC [95% CI] |
|---|---|---|
| prose_paren | NOT EVALUABLE | 0.4529 [0.3301, 0.5784] |
| prose_quote | NOT EVALUABLE | 0.5431 [0.4089, 0.6683] |
| python_string | 0.3241 [0.1511, 0.5263] | 0.1778 [0.0724, 0.3128] |
| python_indent | NOT EVALUABLE | 0.4286 [0.3090, 0.5516] |
| python_depth | 0.6800 [0.5090, 0.8173] | 0.5339 [0.3244, 0.7500] |
| list_depth | NOT EVALUABLE | 0.3690 [0.2484, 0.4971] |
| table_role | NOT EVALUABLE | 0.9206 [0.8559, 0.9720] |
