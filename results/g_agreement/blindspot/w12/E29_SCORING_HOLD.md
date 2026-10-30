# W12 reader scoring hold for E29

Authority: user instruction and BRIEF_UNDERSTAND §124 at commit 44152f5c.
Status: RELEASED under §146 addendum 2 (2505b0f8). See launch/RELEASE_VERIFICATION.json and launch/LAUNCH_REQUEST.json. Freeze 2833a200…, VALUES_SEAL ecac8379…, PREDICTIONS_SEAL ca76c12c… verified. Historical instructions follow.

1. Freeze W12 rows, items and candidate phrasings; post the exact freeze manifest SHA256 in this chat before any reader scoring, and in the integrator handoff.
2. W-text computes and seals D and P for every frozen W12 row using the frozen candidate phrasings, before any reader is scored. Verify the seal and binding to the exact W12 freeze.
3. Under §136 (e29dc767), the coordinator has fixed predictions in advance. W-text generates `e29/PREDICTIONS.json` using frozen code and seals it against the same freeze and D/P seal before reader scores exist: Oracle asked AUROC ≤ 0.65 for every structure row; additionally D − Oracle ≥ 0.15 for every row with sealed D ≥ 0.70. No fresh coordinator ruling is required.
4. Only after both prerequisite artifacts are verified may W12 reader scoring proceed. Record their hashes/commit references in the eventual launch request. Do not run reader scoring or reader warm-ups that reveal scores before release.

The expected turnaround under one hour after freeze is an estimate, not an automatic release. Missing evidence or inability to post the freeze hash keeps scoring blocked. Existing Sunday-evening freeze schedule, Camila check, §100 design and no-substitution-after-freeze rule remain unchanged.

## Registered §124 (verbatim)

## §124 E29. Out-of-sample test of the E25 pattern on rows no reader score has been seen for

**Registered 2026-10-25 11:35 CET. EXPLORATORY, prospective.** **Owner:** W-text (D) with W-core (W12 reader scores).
**Cost:** D is base Qwen only, ≤ 0.1 GPU-h; the reader scores come from W12 (§100), already budgeted.

**Why.** E25's within-structure pattern (the Oracle lens at chance on rows where a text-only continuation scorer
discriminates the right description at 0.71–1.00) was read after the data. W12 adds sentence- and paragraph-structure
rows on Monday whose reader scores nobody has seen. Predicting them from D first is the honest test.

**Blinding order.** (1) W-core freezes W12's rows, items and phrasings (Sunday 19:00). (2) W-text computes D and P for
every W12 row with base Qwen, using the E25 frame and W12's frozen candidate phrasings, and seals them *before* any
reader is scored. (3) The coordinator posts per-row predictions from the rules below, as a dated note, before W12's
reader scores exist. (4) W12 runs. (5) One comparison.

**Rules, fixed from W1 (E25's table).**
- **R1 (lens blind regardless of D):** on every W12 structure row, the Oracle lens's asked AUROC ≤ 0.65 whether D is
  high or low. Falsified if any row with D ≥ 0.7 has Oracle ≥ 0.75 (CI lower bound > 0.65).
- **R2 (text can, lens can't):** on rows with D ≥ 0.7, D − Oracle ≥ 0.15 on at least two of three such rows (or all
  such rows if fewer than three), with the row's item-bootstrap CI of D − Oracle above 0.
- **R3 (D tracks the NLA weakly at most):** no prediction; ρ(D, NLA) across W12 rows is reported descriptively.
- **Descriptive, non-blind companion:** the same D on Suraj's seven exp-13 rows, whose prompted scores (table column
  NLA 1.00 / OL 0.74, parenthesis 0.96 / 0.73, sentences-into-paragraph 0.99 / 0.65, line-in-function 0.99 / 0.71,
  list nesting 0.96 / 0.88, Q&A vs prose 0.79 / 0.56, words-left 0.58 / 0.56) are **already known to the coordinator
  and W-text**, so this part is not a prediction. It shows whether D moves with the bank, since the Oracle lens is not
  at chance on Suraj's bank (0.65–0.88 prompted at layer 42), the discrepancy E23b addresses.

**What each outcome means.** R1 and R2 hold: the lens-specific blind spot for text-discriminable structure replicates
prospectively, and it becomes the headline alongside the describes/continues finding. R1 fails: the blind spot is
bank- or phrasing-specific, and the claim is narrowed to W1's bank and scoring.


## Operations update — 5731e92e, 12:55
W12 may run tonight, not only Monday. Immediately after the posted freeze hash, W-text D/P seal and coordinator predictions are verified against the same freeze, prepare and send the integrator reader-scoring launch request. All §100 scientific rules and this hold remain unchanged. E32 is W-core-owned and independent of E24-D.

## Standing orders — §136, e29dc767
The prediction-generation provision above supersedes earlier references to waiting for a new coordinator post. Verify the exact freeze, complete sealed D/P and sealed mechanically generated predictions before releasing reader scoring. Existing R1/R2/R3, all thresholds and blinding remain unchanged. W-text owns prediction generation; W-core verifies its seal and bindings. No W12 score, freeze or release is claimed by this update.
