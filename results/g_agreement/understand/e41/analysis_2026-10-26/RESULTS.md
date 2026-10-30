# E41 — E31(i) protocol on E36 v2

Registered decision: **NOT_R**.

| Row | Informative n / AUROC (95% CI) | Uninformative n / AUROC (95% CI) | Judged criterion |
|---|---|---|---|
| prose_paren | 0 / undefined | 84 / 0.8226 (0.7250, 0.9074) | uninformative_only |
| prose_quote | 0 / undefined | 84 / 0.7177 (0.6028, 0.8194) | uninformative_only |
| python_string | 28 / 0.6735 (0.4615, 0.8641) | 56 / 0.4313 (0.2873, 0.5921) | both_strata |
| python_indent | 0 / undefined | 84 / 0.5397 (0.4094, 0.6661) | uninformative_only |
| python_depth | 0 / undefined | 84 / 0.8163 (0.7147, 0.8980) | uninformative_only |
| list_depth | 0 / undefined | 84 / 0.4405 (0.3188, 0.5689) | uninformative_only |
| table_role | 0 / undefined | 84 / 0.4938 (0.3692, 0.6222) | uninformative_only |

Strict dev-median split; ties uninformative. 2,000 IID item resamples per stratum; finite-draw percentile intervals. Undefined AUROC cannot satisfy a point threshold. No model refit or cutoff adjustment.

§147 clarification 1: rows with both strata ≥10 retain the original point rules. If informative n<10 and uninformative n≥10, remote-state requires uninformative AUROC≥0.70 and CI lower bound>0.50; local-cue requires uninformative AUROC≤0.60. R requires a strict majority remote-state and no local-cue rows among judged rows. Fewer than three judged rows means NOT_EVALUABLE.
