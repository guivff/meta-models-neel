## §151 E42. Does persistence predict sayability? (the window account, tested as a property of the state)

**Registered 2026-10-26 03:50 CET, before any persistence value is computed. CONFIRMATORY.** **Owner:** W-text.
**Cost:** CPU; ≤ 0.3 GPU-h only if tier (ii) below is needed.
**Why.** The Oracle lens states passage-level properties (topic, sentiment, sentence type 0.98, paragraph index 0.82)
and not token-local states (bracket, string, indent, cell role, depth). The lens inverts a reconstructor of the next
1–32 tokens. Hypothesis: what it can state is what stays true across that window. D (text plausibility) failed as a
predictor (E25 ρ 0.03; E29 R2 not met); persistence is the alternative.

**Rows.** Every structure row with a sealed Oracle asked AUROC: W1 (19), E36 v2 (16), W12 (6). Content rows are
reported separately, never pooled into the primary.

**Persistence (frozen before any score is joined).**
- For each test item, the **following text** is, in order of preference: (i) the item's true continuation where the
  bank retains it (W1: E1b's frozen next-16, extended to 32 where the source document is available; E36 and W12: the
  authored full text beyond the read position); (ii) otherwise base Qwen's greedy 32-token continuation, generated
  once, seeded 20261026, frozen before use.
- **State function:** for each row, a deterministic function of (prefix + k following tokens) → the row's label,
  derived from the row's frozen definition and, where one exists, its frozen checker. W-text commits all state
  functions with a seal before any score is read.
- **Item persistence** = the largest k ∈ [0, 32] such that the state function returns the item's label for every
  extension 1..k. **Row persistence** = the median over test items.
- **Sayability** = the row's sealed Oracle asked AUROC with its registered (descriptive) phrasings.

**Rules.**
- **R1:** Spearman ρ(row persistence, sayability) ≥ 0.50 across the structure rows, with a row-bootstrap 95% CI
  (10,000 draws) above 0.
- **R2:** persistence beats D: on the rows where D is sealed (E25, E29), ρ_persistence − ρ_D > 0 with CI above 0.
- **R3 (binary):** rows with persistence ≥ 16 tokens have Oracle ≥ 0.65 on a majority; rows with persistence ≤ 8 have
  Oracle ≤ 0.65 on a majority.
- **Controls:** the same ρ with the probe's AUROC in place of the Oracle's (expected near 0: the probe reads
  everything); and with the NLA's (reported).
- **Predictions:** R1, R2 and R3 hold; the probe control is near 0.
- **Falsifier:** ρ ≤ 0.20, or short-persistence rows sayable at ≥ 0.80.


