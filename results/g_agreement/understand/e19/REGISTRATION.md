# Source: `409690ee`, BRIEF_UNDERSTAND.md §111

## §111 E19. Does the reader's internal state reach its answer? Steering along the probe direction

**Registered 2026-10-25 04:40 CET, before any E19 steer is applied. EXPLORATORY.** **Owner:** W-internals (reuses E3's
probes on the Oracle lens's layers and the W7/S2 steering code). **Cap:** min(1.5F + 360, 2,400) s, setup 1,500 s.

**Rows (5):** 4 state rows where E3's lens probes are strong (`prose_paren`, `python_string`, `table_role`,
`python_depth`) plus `prose_sentiment` as a content control.

**Direction.** Per row, refit E3's logistic probe on **dev items only** at the Oracle lens's pre-answer position, at
the layer with the highest dev AUROC within the middle third of its layers (chosen on dev, frozen before test). u = the
unit weight vector; σ = std of dev projections onto u.

**Intervention.** At the pre-answer position and the answer tokens, add α·σ·u with α ∈ {0, ±1, ±2, ±4}, on the 84
test items. **Controls:** a random unit direction of equal norm (3 seeds); the content row's direction applied to the
structure rows; each row's own direction applied with the activation injection replaced by a random donor.

**Measures:** paired change in asked log-odds per item (W1 phrasings); change in E15 continuation score; and the probe's
own projection one layer later (did the steer land).

**Prediction.** *Pathway exists but is under-weighted:* asked log-odds moves monotonically with α in the probe's
direction, with slope above the 95th percentile of the random-direction slopes, on ≥ 3 of 4 state rows. *Disconnected:*
asked flat (within the random band) while the continuation score moves. The content row is the positive control: its
own direction should move its asked answer.


