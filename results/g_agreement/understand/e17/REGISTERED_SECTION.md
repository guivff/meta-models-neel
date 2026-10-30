## §110 E17. The horizon test: does readability follow the next ~16 tokens or the activation?

**Registered 2026-10-25 04:40 CET, before any E17 item exists. EXPLORATORY.** **Owner:** W-core (reuses W1 capture,
E15 continuation scoring and E1b's reconstructor arm). **Cap:** min(1.5F + 360, 3,600) s, setup 2,400 s.

**Hypothesis.** The Oracle lens expresses a state to the extent that the next ~16 tokens of the real text reveal it,
not to the extent that the activation encodes it.

**Items (new; no reuse of W1's bank).** Generated from W1's templates with fresh lexical fill (seed 20261025),
minimal pairs captured at identical token indices.
- **`prose_paren` and `python_string`, a 2 × 2 per row:** span length (short 20–30 tokens, long 60–80) × capture
  point (early: 5–8 tokens after the opener; late: 3–8 tokens before the closer). State B is the twin text with the
  opener and closer replaced by neutral tokens of the same count (`,` / a bare word). Distance to the close is then
  near in both "late" cells and far (> 40 tokens) only in "early-long", while distance since the opener varies
  independently.
- **`list_depth`, two capture points:** mid-item (≥ 10 prose tokens before the line end) vs the last token of the
  previous item (the next line opens with the marker at the target depth). Shallow vs deep at the same position kind.
- **n:** 96 pairs per cell (dev 32, test 64), template families split between dev and test.

**Channels (same items):** (1) **source probe:** logistic probe on the target's block-44 activation, trained on dev
only; (2) **window:** E1b's reconstructor run on the real next 16 tokens, probe trained on dev; (3) **Oracle lens
continuation:** E15's frozen pairs for the row, with W1-style random-donor and opposite-state-swap controls;
(4) **Oracle lens asked:** W1's frozen phrasings.

**Primary contrasts (sign pattern pre-registered, Holm across the 3 rows).**
- Paren and string: lens-continuation AUROC in the two "late" cells minus the "early-long" cell ≥ 0.10, while the
  source-probe difference is ≤ 0.05 in absolute value (manipulation check: encoding is flat).
- List depth: lens-continuation AUROC at the line end minus mid-item ≥ 0.10, source-probe difference ≤ 0.05.
- In every cell the window channel should move with the lens channel and the asked channel should stay ≤ 0.60.
Item-cluster bootstrap CIs (2,000, seed 20261025). The across-cell correlation figure is descriptive only.

**Outcomes.** Both directions hold: the horizon account is supported. One direction: partial, reported as such.
Neither: the suppression is not explained by the reconstructor window.
