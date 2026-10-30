# E27(c) — DESCRIPTIVE

Registered comparison: S16 design on W1; all three matched rows ≥0.80 supports design/power, all three ≤0.60 supports bank/labels. Each arm is assessed separately; other patterns are unresolved.

Assessment: swap_res: MIXED_OR_INTERMEDIATE, swap_resn: MIXED_OR_INTERMEDIATE.

| Row | Arm | Mean donor AUROC [95% CI] | Fixed donor AUROC [95% CI] |
|---|---|---|---|
| table_column | swap_res | 0.9144 [0.8513, 0.9635] | 0.7137 [0.5937, 0.8177] |
| table_column | swap_resn | 0.8356 [0.7414, 0.9141] | 0.6684 [0.5522, 0.7858] |
| list_index | swap_res | 0.4598 [0.3273, 0.5899] | 0.3605 [0.2444, 0.4851] |
| list_index | swap_resn | 0.5357 [0.4065, 0.6563] | 0.5068 [0.3789, 0.6301] |
| prose_paren | swap_res | 0.8333 [0.7413, 0.9059] | 0.7115 [0.5954, 0.8137] |
| prose_paren | swap_resn | 0.6854 [0.5619, 0.7895] | 0.5998 [0.4701, 0.7120] |
| python_string | swap_res | 0.9790 [0.9419, 1.0000] | 0.9739 [0.9396, 0.9966] |
| python_string | swap_resn | 0.9728 [0.9297, 0.9981] | 0.9666 [0.9267, 0.9937] |
| prose_quote | swap_res | 0.6054 [0.4823, 0.7249] | 0.5986 [0.4763, 0.7194] |
| prose_quote | swap_resn | 0.5567 [0.4333, 0.6827] | 0.5334 [0.4116, 0.6608] |
| python_indent | swap_res | 0.5550 [0.4288, 0.6787] | 0.6026 [0.4786, 0.7247] |
| python_indent | swap_resn | 0.3815 [0.2636, 0.5057] | 0.4331 [0.3097, 0.5553] |
| table_role | swap_res | 0.3543 [0.2352, 0.4733] | 0.3634 [0.2403, 0.4807] |
| table_role | swap_resn | 0.1519 [0.0727, 0.2449] | 0.1803 [0.0952, 0.2801] |

84 test recipients per row; partner seed16, one opposite-value donor from another template cluster. Two sampled readouts per item/reader, reconstructed with the native NLA reconstructor and averaged. Direct pinned S16 construct/follow functions; raw space; native NLA@42 B-minus-A scoring.

Matched rows retain S16’s original four phrasings, including list-index ordinal wording that does not exactly name W1’s values. Four extension rows use the two existing W1 NLA phrasings. This tests the transferred S16 design, not an isolated bank effect with every label phrase matched.

CIs: 2,000 recipient-item resamples, seed20261025; partners held fixed. Reused donors and template dependence are not included in this requested item bootstrap. All recipient AUROCs, exact invalid resample counts, and fixed/mean results are in metrics.json. No probe fitting or secondary Oracle@42 scoring.
