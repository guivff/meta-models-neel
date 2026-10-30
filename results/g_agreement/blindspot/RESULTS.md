# W1 §70 results

Analysis completed 2026-10-23; frozen source `b15b95fc`. **Verdict: NOT MET.**

W1 §70: (i) PASS (16/19); (ii) FAIL (2/16); (iii) FAIL (6/9); verdict NOT MET; rule-(i) rows: json_type, latex_environment, latex_section, list_depth, list_index, prose_paren, prose_quote, prose_sentence, python_argument, python_comment, python_depth, python_indent, python_string, table_column, table_role, table_row.

| Rule | Result | Fraction | Wilson 95% CI |
|---|---|---:|---:|
| (i) | PASS | 16/19 (84.2%) | [62.4%, 94.5%] |
| (ii) | FAIL | 2/16 (12.5%) | [3.5%, 36.0%] |
| (iii) | FAIL | 6/9 (66.7%) | [35.4%, 87.9%] |

All six original asked-score seals verified before the full label join. The three units assemble to the exact disjoint 7,296-item bank in canonical order. One complete registered analysis ran (129.03 s, CPU); 40 binary rows use 84 test items and six held-out template clusters each. All scientific rules and frozen source were unchanged. The 42 regression tests passed. Independent pairwise recomputation verified 320 reader AUROC point estimates; gates, denominators, activation hashes, and rule-(i) list agree with sealed outputs.

Rule (i) uses 19 Oracle-evaluable count/state rows. Eleven other count/state rows are excluded by the registered gates; one semantic row is excluded, leaving nine. Across all 40 Oracle cells, five are NOT DECODABLE and seven NOT EVALUABLE. Rule (ii) keeps all 16 rule-(i) rows; only `python_string` and `table_role` are within 0.10 of the block-42 probe. All 16 NLA cells are evaluable. “Within 0.10” is the frozen absolute difference criterion, including on semantic rows.

## Rule-(i) rows and downstream exports

Exact selection: [rule_i_rows.json](w1/analysis/rule_i_rows.json). This selection is independent of the failed overall verdict.

`json_type`, `latex_environment`, `latex_section`, `list_depth`, `list_index`, `prose_paren`, `prose_quote`, `prose_sentence`, `python_argument`, `python_comment`, `python_depth`, `python_indent`, `python_string`, `table_column`, `table_role`, `table_row`.

Full dev-fitted directions: [probe_directions.json](w1/analysis/probe_directions.json) and [probe_directions.npz](w1/analysis/probe_directions.npz). Activations and canonical item order: [activations.json](w1/analysis/activations.json); arrays are local cache files, shape 7,296 × 5,120 at each block 42/44. Consumers on another machine must retrieve those arrays and verify the receipt hashes.

The published [priority training export](w1/priority_training/README.md) remains intact: ten fits, 420 dev items, exact recomputed class means. Its coefficients, directions and intercepts exactly match the corresponding final dev fits. No early-export artifact was overwritten.

## Secondary evidence

Fresh replication rows are descriptive. NLA AUROC is 0.568 [0.349, 0.789] for `table_column` and 0.744 [0.571, 0.934] for `prose_paren` (84 test items, six template clusters each), below the respective pilot point estimates 1.00 and 0.98. Oracle is 0.474 [0.334, 0.615] and 0.485 [0.276, 0.653]. Full reader comparisons and 2,000 template-cluster bootstrap intervals are in [metrics.json](w1/analysis/metrics.json).

## Deviations and incomplete evidence

**2026-10-23 cap deviation:** the integrator reported approximately **214 s over the registered 7,200 s W1 science cap**. The assignment used creation + 8,100 s instead of first science + 7,200 s. The complete sealed asked grid is retained and the overrun is disclosed; no rule, item, score or code was changed. [Dated deviation receipt](w1/COMPUTE_DEVIATION.json). Provider accounting remains with the integrator and is not charged again here.

**Free-response recall: PARTIAL.** Priority target (5,040 records, including deterministic J/logit repetitions) and NLA (1,680) free seals verify. Remainder_a target has 3,328 unsealed records; its NLA and all remainder_b free phases are NOT RUN. No blinded annotation seal is present; no recall rate is reported. [Collection receipt](w1/free_response_status.json). The frozen analysis output retains `PENDING BLINDED JUDGE`; this supplementary collection status records incompleteness without altering the sealed output.

W5 is INCOMPLETE: all six block captures are sealed; the original partial scores remain unsealed and unused. The scoring-only attempt `pyvh3awc2i7rq6` stopped NO_FIT before full scoring and produced no score seal (156.5 s science booked by the integrator). The 16:35 CEST operational amendment `08b24aeb` authorizes a fresh attempt using full unscored warm-up units and median timing forecasts; see `w5/completion/warmed/`. W1b remains conditional on committed §79 selections. The integrator operates and publishes; no pod was launched or operated during this analysis.

Integrity receipts: [analysis seal](w1/analysis/ANALYSIS_SEAL.json), [pre-join verification](w1/prejoin_verification.json), [post-analysis checks](w1/post_analysis_checks.json), [early-export checks](w1/early_export_checks.json).

## DESCRIPTIVE per-row supplement

[All-row tables and three requested summaries](w1/descriptive/TABLES.md), with exact values in [tables.json](w1/descriptive/tables.json). Covers all 40 binary rows (both site probes, four readers, CIs, per-reader gates and paired NLA − Oracle intervals) and both ordinal 1–8 sub-rows. Existing verdict remains **NOT MET**. Paired CIs reuse the frozen 2,000 template-cluster bootstrap/seed; no refits, item selection or rule changes.


## §84 DESCRIPTIVE text-only shortcut check (before reader score join)

**Interpretation:** Full-prefix predictability is expected for features defined by the current token/lexeme and is not shortcut evidence; padding alone carries the warning (`current_number` 0.83; eight rows ≈0.69 mild leakage; colon 0.50).

The frozen §84 bank runs unchanged. This CPU-only input diagnostic reads no reader scores or activations and changes no registered verdict, gate or denominator. Confirmation statuses remain pending.

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


**Interpretation for confirmations:** `current_number` is the only padding-only flag (AUROC 0.827); any registered confirmation on this row must be reported as potentially affected by padding. Use padding-only flags when interpreting confirmations: eight other rows show mild leakage (0.694), while colon is at chance (0.500). Full-prefix predictability is expected and is not shortcut evidence. Historical either-view flags in the raw diagnostic are superseded for interpretation by this clarification; all measured numbers are unchanged. The other nine rows are not cleared of all possible shortcuts.

Exact metrics, fold membership and saved OOF predictions: [shortcut table](w1b/shortcuts/TABLE.md), [metrics](w1b/shortcuts/metrics.json), [independent checks](w1b/shortcuts/VERIFICATION.json). Registered analysis code and frozen items are unchanged.
