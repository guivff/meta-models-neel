# E113 §227 descriptive first-token-ID control

Direct Guiv request: examine original sealed capture token IDs for nesting_depth, indent_level, page_range_digit, joined to original value labels by exact item ID. Report token-ID counts by row, split (84 dev/84 test), and original value class (42 each); state constancy over all168 items per row. No registered probe fits or tests are repeated.

If a row varies, fit a separate descriptive OneHotEncoder(handle_unknown=ignore) + LogisticRegression(C=1, solver=lbfgs, max_iter=2000, random_state=20261029) on its original84dev only. No tuning/scaling/signflip. Freeze before scoring original84test once. A constant row receives NOT FIT (constant ID), no empirical classifier AUROC; its ID-only constant score has chance AUROC0.5 by definition for balanced binary classes. No new hypothesis or registered verdict.

Validate ORDER.json against original LAYOUT_SEAL and raw INDEX, original LABELS against LABEL_SEAL, exact IDs/row/split/class counts. No activation array loads/model forwards/GPU/API. Preserve original scientific seals and ONCE/TEST_ONCE. This is a new posthoc descriptive control after all primary results; no claim of prospective control design. Original kernel before capture and exact final binder after capture/before claim chronology remains.
