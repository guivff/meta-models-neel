# E48 — registered CPU reanalysis

H3: **FALSIFIED**. H5: **FALSIFIED**.

Frozen scope: 52 structure bank-rows for H3/H5 (W1 30, E36 16, W12 6). All binary W1 rows are retained regardless of earlier probe eligibility; ordinal rows are excluded.

| Bag | Spearman with asked, 95% row-bootstrap CI |
|---|---|
| presence | 0.198 [-0.052, 0.436] |
| counts | 0.123 [-0.135, 0.363] |
| words | -0.080 [-0.359, 0.207] |

Words minus presence rho: -0.278, paired CI [-0.503, -0.041].
H3 pattern violations: 0; high-presence unsayable paren rows: ['W1:prose_paren', 'E36:prose_paren']; string rows: ['W1:python_string'].
H5 words>=0.75 while asked<=0.65: 22 bank-rows.

| Structure pool | Mean asked AUROC [95% row CI] | Weak rows with lower >0.5 | Below chance upper <0.5 |
|---|---|---|---|
| E24@44 (n=19) | 0.594 [0.525, 0.672] | 2/15 | 0 |
| E36 (n=16) | 0.537 [0.489, 0.590] | 1/13 | 0 |
| W1 (n=30) | 0.522 [0.462, 0.587] | 2/26 | 5 |
| W12 (n=6) | 0.693 [0.482, 0.866] | 0/2 | 1 |
| primary_combined (n=65) | 0.547 [0.508, 0.588] | 5/54 | 5 |

W1–E36 bank reliability (Spearman): all common rows 0.783 [0.532, 0.901]; structure 0.326 [-0.230, 0.768]. Compare E25 rho 0.03 and E42 rho -0.13. This estimates bank stability, not an identified strict correlation ceiling.

Shown-token features: fixed signed features, averaged within item over E43 deduplicated native test readouts. See SHOWN.json for all per-row CIs.

| Reader / feature | Spearman with Oracle asked, 95% CI |
|---|---|
| oracle:close_minus_open_paren | -0.346 [-0.672, 0.136] |
| oracle:double_quote_parity | 0.008 [-0.408, 0.462] |
| oracle:single_quote_parity | -0.159 [-0.614, 0.366] |
| oracle:leading_space_runs | -0.034 [-0.422, 0.317] |
| oracle:pipe_count | -0.190 [-0.596, 0.286] |
| nla:close_minus_open_paren | -0.551 [-1.000, 0.500] |
| nla:double_quote_parity | -0.200 [-1.000, 1.000] |
| nla:single_quote_parity | 0.395 [-0.500, 1.000] |
| nla:leading_space_runs | NOT EVALUABLE |
| nla:pipe_count | 0.154 [-1.000, 0.949] |

Reward signal size: **NOT AVAILABLE**. No local sealed within-group GRPO reward logs found; no comparison with the 0.015 FVE contribution is inferred.

Per-row asked AUROCs (2,000 item draws); W12 is supplementary to part 1.

| Bank | Row | AUROC [95% CI] |
|---|---|---|
| W1 | json_depth | 0.346 [0.234, 0.469] |
| W1 | json_field | 0.249 [0.151, 0.357] |
| W1 | json_status | 1.000 [1.000, 1.000] |
| W1 | json_type | 0.660 [0.538, 0.771] |
| W1 | latex_brace | 0.528 [0.407, 0.648] |
| W1 | latex_environment | 0.571 [0.443, 0.691] |
| W1 | latex_fraction | 0.955 [0.906, 0.988] |
| W1 | latex_item | 0.879 [0.804, 0.944] |
| W1 | latex_math | 1.000 [1.000, 1.000] |
| W1 | latex_role | 0.844 [0.744, 0.914] |
| W1 | latex_section | 0.433 [0.311, 0.554] |
| W1 | latex_subject | 1.000 [1.000, 1.000] |
| W1 | list_completed | 0.489 [0.362, 0.616] |
| W1 | list_depth | 0.634 [0.515, 0.744] |
| W1 | list_index | 0.419 [0.293, 0.544] |
| W1 | list_ordered | 0.572 [0.443, 0.695] |
| W1 | list_priority | 0.891 [0.798, 0.966] |
| W1 | list_task | 0.505 [0.374, 0.632] |
| W1 | list_topic | 0.968 [0.928, 0.994] |
| W1 | list_words | 0.342 [0.226, 0.464] |
| W1 | prose_budget | 0.382 [0.257, 0.507] |
| W1 | prose_column | 0.339 [0.231, 0.463] |
| W1 | prose_paren | 0.485 [0.357, 0.606] |
| W1 | prose_quote | 0.563 [0.439, 0.689] |
| W1 | prose_sentence | 0.531 [0.402, 0.659] |
| W1 | prose_sentiment | 0.911 [0.836, 0.967] |
| W1 | prose_topic | 1.000 [1.000, 1.000] |
| W1 | prose_words | 0.218 [0.125, 0.327] |
| W1 | python_argument | 0.500 [0.376, 0.627] |
| W1 | python_comment | 0.543 [0.417, 0.674] |
| W1 | python_depth | 0.488 [0.361, 0.614] |
| W1 | python_effect | 0.570 [0.444, 0.688] |
| W1 | python_error | 1.000 [1.000, 1.000] |
| W1 | python_indent | 0.592 [0.459, 0.719] |
| W1 | python_line | 0.382 [0.259, 0.502] |
| W1 | python_string | 0.644 [0.523, 0.755] |
| W1 | table_column | 0.474 [0.354, 0.600] |
| W1 | table_role | 0.438 [0.310, 0.562] |
| W1 | table_row | 0.501 [0.380, 0.624] |
| W1 | table_status | 1.000 [1.000, 1.000] |
| E36 | json_status | 0.871 [0.784, 0.936] |
| E36 | json_type | 0.707 [0.590, 0.813] |
| E36 | latex_environment | 0.518 [0.398, 0.643] |
| E36 | latex_role | 0.881 [0.806, 0.944] |
| E36 | latex_section | 0.480 [0.355, 0.607] |
| E36 | latex_subject | 0.991 [0.977, 1.000] |
| E36 | list_depth | 0.489 [0.362, 0.620] |
| E36 | list_index | 0.433 [0.309, 0.561] |
| E36 | list_priority | 1.000 [1.000, 1.000] |
| E36 | list_topic | 0.939 [0.881, 0.986] |
| E36 | prose_paren | 0.464 [0.336, 0.591] |
| E36 | prose_quote | 0.710 [0.590, 0.817] |
| E36 | prose_sentence | 0.501 [0.375, 0.625] |
| E36 | prose_sentiment | 1.000 [1.000, 1.000] |
| E36 | prose_topic | 0.987 [0.966, 1.000] |
| E36 | python_argument | 0.389 [0.278, 0.514] |
| E36 | python_comment | 0.558 [0.424, 0.685] |
| E36 | python_depth | 0.504 [0.379, 0.626] |
| E36 | python_error | 1.000 [1.000, 1.000] |
| E36 | python_indent | 0.461 [0.334, 0.582] |
| E36 | python_string | 0.628 [0.504, 0.744] |
| E36 | table_column | 0.743 [0.631, 0.844] |
| E36 | table_role | 0.544 [0.421, 0.667] |
| E36 | table_row | 0.457 [0.325, 0.590] |
| E36 | table_status | 1.000 [1.000, 1.000] |
| E24@44 | json_status | 1.000 [1.000, 1.000] |
| E24@44 | json_type | 0.658 [0.537, 0.775] |
| E24@44 | latex_environment | 0.571 [0.442, 0.694] |
| E24@44 | latex_fraction | 0.956 [0.911, 0.989] |
| E24@44 | latex_item | 0.879 [0.801, 0.941] |
| E24@44 | latex_math | 1.000 [1.000, 1.000] |
| E24@44 | latex_role | 0.844 [0.755, 0.919] |
| E24@44 | latex_section | 0.430 [0.304, 0.557] |
| E24@44 | latex_subject | 1.000 [1.000, 1.000] |
| E24@44 | list_depth | 0.634 [0.511, 0.753] |
| E24@44 | list_index | 0.420 [0.285, 0.547] |
| E24@44 | list_priority | 0.892 [0.799, 0.966] |
| E24@44 | list_topic | 0.968 [0.929, 0.995] |
| E24@44 | prose_paren | 0.485 [0.355, 0.616] |
| E24@44 | prose_quote | 0.558 [0.430, 0.679] |
| E24@44 | prose_sentence | 0.534 [0.414, 0.671] |
| E24@44 | prose_sentiment | 0.910 [0.840, 0.970] |
| E24@44 | prose_topic | 1.000 [1.000, 1.000] |
| E24@44 | python_argument | 0.499 [0.374, 0.632] |
| E24@44 | python_comment | 0.540 [0.418, 0.669] |
| E24@44 | python_depth | 0.487 [0.358, 0.611] |
| E24@44 | python_error | 1.000 [1.000, 1.000] |
| E24@44 | python_indent | 0.592 [0.459, 0.722] |
| E24@44 | python_string | 0.641 [0.513, 0.752] |
| E24@44 | table_column | 0.476 [0.356, 0.607] |
| E24@44 | table_role | 0.436 [0.310, 0.562] |
| E24@44 | table_row | 0.499 [0.371, 0.627] |
| E24@44 | table_status | 1.000 [1.000, 1.000] |
| W12 | clause_embedding | 0.224 [0.135, 0.322] |
| W12 | paragraph_index | 0.821 [0.728, 0.899] |
| W12 | paragraph_start | 0.708 [0.593, 0.810] |
| W12 | sentence_position | 0.847 [0.745, 0.928] |
| W12 | sentence_type | 0.982 [0.953, 1.000] |
| W12 | syntax_role | 0.578 [0.447, 0.703] |

Limitations:
- W1 prior probe eligibility is not used to filter this asked-channel reanalysis.
- Pooled bank-row bootstrap treats bank-row units as exchangeable; E24 reuses W1 items and is not independent replication.
- Bank stability is an empirical reliability reference; a single cross-bank correlation does not identify a strict ceiling on every across-row correlation.
- Shown-token features have fixed signed orientation and no held-out feature selection; this part is descriptive.
- No reward-gradient conclusion without locally available within-group GRPO logs.
