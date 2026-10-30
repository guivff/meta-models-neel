**Prediction (§105):** On rows with dev-valid continuation pairs, Oracle native-mode continuation AUROC stays≤0.60 on most rows.

**Did it hold? No, descriptively.** Seven of eight rows have at least one dev-valid pair. Oracle AUROC is≥0.75 on 5/7 and≤0.60 on 1/7. This is the pre-registered surprising outcome: several structural distinctions are present in native-mode continuation likelihoods. §105 specifies no formal global acceptance threshold, so this is not an invented CONFIRMED verdict.

# E15 registered native-mode continuation analysis

One frozen analysis run on sealed pod `7whn3a1dvi399p`, booking `e836f362`. Pair commit `0d0a5a96`; scorer/analysis source `348c2d49`. All 4,704 score rows, frozen input/source hashes and score seals verified before labels. Each row has 84 dev texts and 84 held-out test items, 42/value/split across six disjoint template families per split. Two pairs/row; a pair qualifies only if base-Qwen dev AUROC≥0.80. Scores average only qualified pairs, without sign flips. CIs: 2,000 test template-cluster bootstrap resamples, fixed seed.

| Row | Base dev AUROC, pair1 / pair2 | Valid pairs | Oracle test AUROC [95% CI] | NLA test AUROC [95% CI], descriptive/off-native | Oracle random-donor AUROC [95% CI] | Oracle − random donor [paired 95% CI] |
|---|---|---|---|---|---|---|
| prose_paren | 1.000 / 1.000 | 1, 2 | 0.713 [0.554, 0.935] | 0.453 [0.189, 0.700] | 0.475 [0.414, 0.555] | +0.237 [+0.007, +0.501] |
| prose_quote | 1.000 / 1.000 | 1, 2 | 0.797 [0.694, 1.000] | 0.543 [0.430, 0.709] | 0.498 [0.414, 0.591] | +0.299 [+0.144, +0.562] |
| python_string | 1.000 / 1.000 | 1, 2 | 0.915 [0.875, 0.951] | 0.223 [0.100, 0.370] | 0.604 [0.514, 0.709] | +0.311 [+0.183, +0.414] |
| python_indent | 1.000 / 1.000 | 1, 2 | 0.782 [0.567, 0.993] | 0.429 [0.273, 0.562] | 0.503 [0.421, 0.573] | +0.278 [+0.075, +0.507] |
| python_depth | 1.000 / 1.000 | 1, 2 | 0.818 [0.781, 0.855] | 0.634 [0.582, 0.704] | 0.516 [0.438, 0.595] | +0.302 [+0.227, +0.375] |
| list_depth | 1.000 / 1.000 | 1, 2 | 0.318 [0.092, 0.593] | 0.369 [0.112, 0.568] | 0.508 [0.467, 0.583] | -0.190 [-0.391, +0.031] |
| table_column | 0.442 / 0.570 | none | NOT EVALUABLE | NOT EVALUABLE | — | — |
| table_role | 0.962 / 0.961 | 1, 2 | 0.817 [0.715, 0.887] | 0.921 [0.863, 0.976] | 0.519 [0.460, 0.605] | +0.298 [+0.188, +0.388] |

The five Oracle rows at or above 0.75 are `prose_quote`, `python_string`, `python_indent`, `python_depth` and `table_role`. Parenthesis is 0.713; list depth is 0.318 in the frozen signed direction. Table column’s two dev-reference AUROCs (0.442 and 0.570) fail validity: its continuation choices do not reliably express the state for the base model, so this run cannot adjudicate the column blind spot. All pairs remain unchanged; no replacement or rescue.

Oracle true-minus-random-donor CIs are positive on 6/7 valid rows, including parenthesis, and cross zero for list depth. These are per-row unadjusted 95% intervals; no multiplicity-adjusted global claim. The Python-string Oracle random-donor point estimate is 0.604, slightly above 0.60; it is explicitly reported. §105 freezes the base-validity gate and calls for donor contrasts, but does not prescribe an additional numerical random-donor exclusion cutoff. No new cutoff is imposed after results.

## What this answers

This weakens the claim that the Qwen Oracle lens neither describes nor enacts structure. The native continuation likelihoods distinguish several states that descriptive asked questions or the E6 greedy proxies missed. It does not establish that the lens spontaneously produces faithful structural continuations: E15 is teacher-forced likelihood scoring, while E6 used short greedy generations with sparse surface proxies and a changed continuation instruction. Those differences prevent attributing the entire contrast to a single prompt change. E14’s GLM enactment result is a useful comparison, not a controlled cross-model replication.

The NLA scores are deliberately off its native explanation format and descriptive. In particular, Python string is directionally inverted (0.223) and table role is high (0.921); no sign is flipped. This is not a format-matched ranking of the two readers.

## Complete per-pair values (including invalid pairs)

| Row | Pair | Dev validity | Oracle test AUROC [95% CI] | NLA test AUROC [95% CI], descriptive |
|---|---|---|---|---|
| prose_paren | 1 | valid | 0.722 [0.555, 0.912] | 0.558 [0.368, 0.772] |
| prose_paren | 2 | valid | 0.652 [0.518, 0.864] | 0.374 [0.106, 0.652] |
| prose_quote | 1 | valid | 0.800 [0.694, 0.986] | 0.473 [0.303, 0.662] |
| prose_quote | 2 | valid | 0.681 [0.627, 0.870] | 0.623 [0.521, 0.765] |
| python_string | 1 | valid | 0.957 [0.939, 0.981] | 0.662 [0.390, 0.889] |
| python_string | 2 | valid | 0.721 [0.565, 0.862] | 0.022 [0.003, 0.044] |
| python_indent | 1 | valid | 0.772 [0.513, 0.984] | 0.402 [0.260, 0.493] |
| python_indent | 2 | valid | 0.810 [0.586, 0.998] | 0.458 [0.272, 0.621] |
| python_depth | 1 | valid | 0.819 [0.787, 0.849] | 0.607 [0.558, 0.676] |
| python_depth | 2 | valid | 0.811 [0.765, 0.878] | 0.650 [0.591, 0.730] |
| list_depth | 1 | valid | 0.327 [0.101, 0.595] | 0.359 [0.100, 0.559] |
| list_depth | 2 | valid | 0.305 [0.093, 0.583] | 0.376 [0.122, 0.569] |
| table_column | 1 | INVALID; descriptive only | 0.600 [0.434, 0.724] | 0.222 [0.036, 0.543] |
| table_column | 2 | INVALID; descriptive only | 0.443 [0.233, 0.686] | 0.290 [0.102, 0.549] |
| table_role | 1 | valid | 0.760 [0.596, 0.911] | 0.775 [0.617, 0.914] |
| table_role | 2 | valid | 0.811 [0.745, 0.885] | 0.880 [0.772, 0.976] |

## Additional donor controls

The primary random control uses E15’s separately frozen value-independent SHA256 mapping within W1 test row/cluster/length bin (self allowed). W1’s original opposite-value mismatches are a separate descriptive arm, not represented as random or expected at chance. All mappings were frozen before scoring. The table below retains both NLA donor controls and the W1 mismatch for Oracle.

| Row | Oracle W1 mismatch AUROC [95% CI] | NLA random AUROC [95% CI] | NLA W1 mismatch AUROC [95% CI] |
|---|---|---|---|
| prose_paren | 0.287 [0.065, 0.446] | 0.555 [0.471, 0.667] | 0.547 [0.300, 0.811] |
| prose_quote | 0.203 [0.000, 0.306] | 0.532 [0.457, 0.589] | 0.457 [0.291, 0.570] |
| python_string | 0.085 [0.049, 0.125] | 0.476 [0.329, 0.610] | 0.777 [0.630, 0.900] |
| python_indent | 0.218 [0.007, 0.433] | 0.476 [0.386, 0.539] | 0.571 [0.438, 0.727] |
| python_depth | 0.182 [0.145, 0.219] | 0.570 [0.517, 0.638] | 0.366 [0.296, 0.418] |
| list_depth | 0.682 [0.407, 0.908] | 0.463 [0.370, 0.539] | 0.631 [0.432, 0.888] |
| table_role | 0.183 [0.113, 0.285] | 0.375 [0.261, 0.482] | 0.079 [0.024, 0.137] |

## Provenance

Canonical metrics and original registered analysis seal remain unchanged in `analysis_7whn3a1dvi399p/`. This descriptive report is separately sealed. Oracle uses its unchanged native prompt with its own `- ` prefix; no E6 continuation instruction is appended. NLA uses continuation scoring through its native prompt without the explanation prefix, and is labelled off-native. Base Qwen is adapter-disabled on real dev text, with no bullet or question added. No new activation capture, pair replacement, test-based pair selection or sign reversal.

Independent SciPy average-rank AUROC checks reproduce all 90 base-validity, per-pair and valid-pair-averaged arm estimates. No registered analysis or bootstrap was rerun. Full score/provenance/first-science/compute receipts remain in the pulled cache; no new GPU or API calls for analysis.
