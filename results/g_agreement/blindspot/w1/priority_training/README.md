# W1 priority training export

Status: `TRAINING_ONLY_EARLY_EXPORT`. Verified target and NLA asked-score seals before opening the presealed dev-only label derivative. No test label join or W1 decision was performed for this export.

Five rows: `table_column`, `prose_paren`, `prose_sentiment`, `python_effect`, `latex_subject`. Each block-42/block-44 fit uses 84 dev items (42 per value), from six template clusters. Total: 420 distinct training items, ten fits.

`probe_directions.npz` stores four arrays per feature/block. `probe_directions.json` gives exact array keys, raw intercepts, positive/negative values and provenance. `__unit` is the unit raw-space logistic direction pointing toward value A; `__coef` is the raw-space coefficient; `__mean_A` and `__mean_B` are raw class means. For a raw activation h, the fitted logit is `h @ coefficient + raw_intercept`.

| Feature | Positive value A | Negative value B | Blocks |
|---|---|---|---|
| `table_column` | first | later | 42, 44 |
| `prose_paren` | inside | outside | 42, 44 |
| `prose_sentiment` | positive | negative | 42, 44 |
| `python_effect` | mutation | copy | 42, 44 |
| `latex_subject` | algebra | geometry | 42, 44 |

W6/W7 and W-mechanism may use these training-only vectors now. These are priority rows, not a list of rows satisfying W1 rule (i); that selection awaits the complete registered analysis.

Verification: both asked-score seals and lineage passed; 10 early-export tests passed; all 40 arrays are finite, direction norms are one, coefficient orientation agrees, and both raw means exactly match recomputation from the dev derivative. Export seal SHA256: `605eb7cbbd4fdc7b1d134b7e3091ff979e6dee37866005ee24ce534b38926202`.
