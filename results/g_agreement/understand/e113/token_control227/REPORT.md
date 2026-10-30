# E113 first-token-ID descriptive control

All three bookkeeping rows have constant first-token ID **12** across all168 items per row. Counts below retain the original value-class orientation.

| Row | Dev class0 | Dev class1 | Test class0 | Test class1 |
|---|---|---|---|---|
| nesting_depth | ID12:42/42 | ID12:42/42 | ID12:42/42 | ID12:42/42 |
| indent_level | ID12:42/42 | ID12:42/42 | ID12:42/42 | ID12:42/42 |
| page_range_digit | ID12:42/42 | ID12:42/42 | ID12:42/42 | ID12:42/42 |

No one-hot classifier was fit: every row meets the requested constant-token condition. An ID-only constant score has AUROC0.5 by definition; this is not an empirical fitted classifier result.

Because token identity, position and its token embedding are constant across items, variation in the first token’s own embedding cannot by itself explain first-generated-token hidden-state AUROC1.00. The contextual hidden state may still carry injected/contextual information; this control does not establish unassisted reader knowledge or causal localization.

Original registered probes/results/guards are unchanged. This is a posthoc metadata-only control, no activation loads/refits/retests/GPU/API. Injected-slot maxima include the reader’s own input. Original kernel preceded capture; exact final binder was finalized after capture and committed before the CPU claim. R-4 owns independent review under §227.
