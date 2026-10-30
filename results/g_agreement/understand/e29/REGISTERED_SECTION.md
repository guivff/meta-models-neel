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

---
