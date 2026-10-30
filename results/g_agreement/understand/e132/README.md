# E132 prospective grouped-CV preparation

§240 (`272e3fd35`), exploratory and CPU only. **HOLD: target/AUROC convention and E116 Oracle block need a coordinator ruling before real fitting.** No real item text, choice/belief label or reader outcome has been opened for this preparation.

Run synthetic checks:

    python results/g_agreement/understand/e132/test_grouped.py

`grouped.py` supplies leakage-safe joint item/template folds, matched-capacity word-unigram logistic classifiers and a paired endpoint difference bootstrap. Six synthetic tests cover transitive item/template grouping, deterministic folds, too few independent groups, no held-out vocabulary leakage, unavailable classes and paired endpoint scoring. A fresh-directory import/test passes.

This is not an analysis READY command or a final target protocol. The API deliberately requires a declared target/class convention, and no input adapter or once-only real runner is released until that convention and the E116 readout block are fixed. No author analysis, old guard, fit or classifier command has been run on E107/E116 data. Existing source labels, readers, judgments and seals remain unchanged.

Required source custody and the exact open questions are recorded in PREPARATION_STATUS.json. Original template IDs must be bound from input-bank metadata; they cannot be inferred from labels/readouts. Original judgment codes define whether the chosen Oracle readout explicitly names the label; missing codes/text are unavailable, not implicit endpoint B. All predictors must use matched folds and endpoint items; absent outside readouts must be counted without inventing text.
