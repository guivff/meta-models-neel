## §119 E25. Is a description sayable when it is a plausible continuation? (text statistics predict the blind spot)

**Registered 2026-10-25 10:10 CET, before any E25 score exists. EXPLORATORY.** **Owner:** a new chat, W-text.
**Cap:** min(1.5F + 360, 1,800) s, setup 1,500 s. **Seed:** 20261025. **No adapter, no injected activation.**

**Why.** E21 found the reconstructor rewards naming almost nowhere, for content as much as structure, yet the lens
answers content questions near-perfectly. S14 and E21 explain what is *not* said; something else must explain what is.
Hypothesis: the Oracle lens can only say what it could have written next. A content answer ("sports", "negative") is a
plausible continuation of the text; a structure answer ("inside a parenthesis") never is.

**Inputs.** W1's 2,100 sealed test items (text up to the read position) and W1's frozen phrasings per row (the correct
and the wrong candidate, exactly as scored in W1). Base Qwen3.6-27B.

**Scoring.** Frame per item and candidate: the item text, one newline, the candidate verbatim. Score = mean per-token
log P(candidate tokens | frame prefix). Per item, for the true candidate c_t and the wrong one c_w.

**Row-level predictors (25 rows).**
- **P (plausibility):** median over items of the true candidate's score.
- **D (discriminability):** AUROC of score(c_t) − score(c_w) over the row's items, i.e. whether the text alone prefers
  the right description.

**Tests.** Spearman ρ between each predictor and the W1 Oracle-lens asked AUROC across the 25 rows, 2,000-row
bootstrap. **Prediction:** ρ(P) ≥ 0.50 with CI above 0, and the 16 structure rows have lower P than the 9 content rows
(difference of medians, CI above 0). **Discriminant check (descriptive):** ρ with the NLA's W1 asked AUROC and with the
probe, predicted lower than ρ with the lens. **Comparison (descriptive):** E21's ρ = 0.48.
**Alternative:** ρ(P) < 0.30: sayability is not a matter of continuation plausibility, and the lens's content answers
need another account.

