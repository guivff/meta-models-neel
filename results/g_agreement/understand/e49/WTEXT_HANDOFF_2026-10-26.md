# E49 generator handoff — 2026-10-26

The shared interface and README were committed before authoring, originally `f982cae` (rebased as `ea28909`). The blind PRECALLS and their seal preceded all E49 construction. The interface is unchanged.

W-text's seven modules (1, 2, 9, 10, 13, 14, 15) now pass CPU construction checks and are source-sealed in `WTEXT_GENERATORS_SEAL.json`. Row 13 reuses row 9 byte-for-byte; the central freeze additionally checks token-array equality. See `rows/DECIMAL_TWIN_2026-10-26.md` for row 16's required use of row 15. `WTEXT_VALIDATION.json` records balance, read tokens and lengths.

Under the dated ownership update, W-internals' rows 3, 4 and 12 are integrated unchanged from `161c6ddb`, verified against `INTERNALS_GENERATORS_SEAL.json`. W-text's unused preliminary versions are retained in ignored `cache/unused_wtext_drafts_2026-10-26/`; no frozen bank ever used them. The active shared helper no longer contains these unused generators.

`freeze_bank.py` requires all 16 modules and writes an exclusive raw bank directory, exact tokenizer/source hashes and a validation seal. `bow_once.py` requires that complete freeze, locks the bank before fitting, fits token-count vocabulary and logistic regression on dev only, evaluates test once and seals its output. Actual BOW fitting has **not** occurred. Failed rows are retained and excluded, not redesigned.

`rules49.py` implements the registered gates, R1–R3, falsifier and blind pre-call accuracy. The user confirmed on 2026-10-26 that intermediate Oracle AUROCs count as incorrect for either binary pre-call. R2 uses 2,000 bootstrap resamples within kind with seed 20261026; it reports the signed gap and whether its 95% interval excludes zero. Empty required groups are NOT EVALUABLE. These rules have been tested only on synthetic metrics.

Validation: 23 CPU tests pass across `test_text_rows.py`, `test_internals_rows.py` and `test_rules49.py`. No GPU, BOW fit, reader score or capture has run. W-mechanism's rows 5–8, 11 and 16 are still required before the central bank freeze. The native channel package, candidate/detector bindings and sealed once-only analysis command must be completed against that integrated bank before a READY launch request is issued. This handoff does not authorize a launch.

E42 close-out was verified and committed with the interface: R1–R3 not met, all 41 persistence rows evaluable with zero exclusions; one missing W12 reader row excluded from the score join. No recomputation was performed.
