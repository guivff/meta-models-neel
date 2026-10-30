# §84 text-only shortcut check — DESCRIPTIVE

Registered §84 verdict unchanged. Reader scores and activations were not read.

**Interpretation:** Full-prefix predictability is expected for features defined by the current token/lexeme and is not shortcut evidence; padding alone carries the warning (`current_number` 0.83; eight rows ≈0.69 mild leakage; colon 0.50).

Native Qwen token-count unigrams; fixed L2 logistic C=1; leave-one-cluster-out CV
over all 168 items/row (12 clusters, including original dev and test). Vocabulary
fit on training clusters only. Pooled OOF AUROC; present positive; flag at ≥0.8.

| Row | n | Padding-only AUROC | Full-prefix AUROC | Padding status | Padding artefact possible |
|---|---:|---:|---:|---|---|
| wordlist_preposition | 168 | 0.694 | 1.000 | mild leakage | not flagged |
| word_allcaps | 168 | 0.694 | 1.000 | mild leakage | not flagged |
| current_colon | 168 | 0.500 | 1.000 | chance | not flagged |
| number_magnitude_ge_1000 | 168 | 0.694 | 1.000 | mild leakage | not flagged |
| number_digits_ge_3 | 168 | 0.694 | 0.989 | mild leakage | not flagged |
| current_number | 168 | 0.827 | 1.000 | possible shortcut | yes |
| number_digits_ge_4 | 168 | 0.694 | 0.989 | mild leakage | not flagged |
| number_magnitude_ge_10 | 168 | 0.694 | 0.920 | mild leakage | not flagged |
| number_magnitude_ge_100 | 168 | 0.694 | 0.994 | mild leakage | not flagged |
| wordlist_auxiliary | 168 | 0.694 | 1.000 | mild leakage | not flagged |

Full-prefix prediction alone does not establish a padding artefact. Padding-only
prediction is a nuisance warning, not causal evidence of reader reliance. No flag
does not rule out nonlinear/relational shortcuts. Confirmation statuses are pending;
the descriptive write-up must merge these flags by feature after registered analysis.

All OOF predictions, fold memberships, fold AUROCs and exact provenance are saved
alongside this table. No hyperparameter search, sign reversal or scope selection.
