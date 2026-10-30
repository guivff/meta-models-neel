# Deferred comparison contract — 2026-10-27

Command: `python results/g_agreement/understand/e52/comparison_once.py`. It never runs before the forecast, E49 labels and final E49 analysis exist. It creates one never-reset claim before accessing outcomes, then publishes `comparison_169/`. No comparison is run during the label phase.

Integrator delivers `cache/g_agreement/understand/e52-comparison-v1/VERIFIED_INPUTS.json`. Required header: `issuer: integrator`, `status: VERIFIED_FINAL_ANALYSES`, `E49_analysis_complete: true`.

- `e49_analysis_seal`: `{path, sha256}` for the final E49 analysis seal. Every E49 outcome must belong to this seal.
- `timing`: `forecast_commit`, `forecast_commit_epoch`, `first_reader_score_epoch`, `reader_unseal_epoch`. The script checks committed forecast bytes, Git timestamp and chronological order; the forecast must precede the first reader score.
- `documents`: ID-to-reference mapping. Each entry has `{path, sha256, seal_path, seal_sha256, member}`; member is the source file's path relative to its seal. No unsealed/retyped outcome values are accepted.
- `banks`: W1/E36/E49, each keyed by every frozen row name. Every row has `reader: oracle`, `layer: 44`, `split: test`, and JSON-pointer references `{document, pointer}` for `probe_auroc` and `unprompted_mention_rate`. Forced-choice AUROC is optional, labelled off-distribution, and usable only for R2 with `no_sealed_readouts_available: true` when the native reference is null. E49 additionally requires `bow_auroc`, `base_text_auroc`, `correct_value_rate` and `wrong_only_rate`, and its native mention rate can never be absent.

All metrics must be the final sealed analyses' numbers, with E43's frozen unprompted mention measure. The comparison joins by bank/row, applies probe≥.85 for R2, uses mention≥.10 (or forced choice≥.80 only if readouts do not exist), and performs the registered one-sided Mann–Whitney and point-biserial tests separately for W1/E36. R3 re-applies E49's mechanical gates (probe≥.90, base≥.85, BOW≤.65 for tracked states), then uses native correct-value rate≥.10 and greater than wrong-only rate as REPORTED (§169 clarification2). Correct-value counts readouts naming the correct value, including both-value mentions; wrong-only counts readouts naming only the wrong value. Original PRECALLS supply the human baseline unchanged. No thresholds or exclusions depend on forecast accuracy.

Primary sparse-pursuit R1 must pass, and R3 predictions must match primary sparse labels (§169 amendment1). The unchanged SVD E1536 remains the R2 measure.

§169 clarification3 (`6576b8cb`, 2026-10-27): the falsifier uses accuracy≤9/16 (56.25%) over gated E49 rows. With fewer than8 gated rows, R3 and the R3 component of the falsifier are NOT EVALUABLE; accuracy is descriptive only. The criterion is inclusive at9/16 and R3 still requires accuracy≥75% when evaluable.

Deadline amendment e0a2e9ef plus Guiv’s clarification: NO FORECAST is allowed only for a stated computational reason; exclude those rows from the headline denominator and require at least8 forecasted gated rows. Report alongside the headline a sensitivity accuracy whose denominator includes all gated rows and whose numerator treats every gated NO FORECAST as wrong. Do not back-fill a forecast after readers start.
