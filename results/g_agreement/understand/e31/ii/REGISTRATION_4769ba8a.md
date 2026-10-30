## §126 E31. Local cue or remote state? (what E15 and E3 are measuring)

**Registered 2026-10-25 12:05 CET, before any E31 score. EXPLORATORY; a check on two pillars of the story.**
**Why.** E15's continuation signal (0.71–0.92 on W1 items) did not replicate on E17/E20 items (at chance 2–8 tokens
before the close), and E3's in-lens probes may read the last few tokens rather than the remote state. If either is a
local-cue artefact of W1's bank, the "carries it but can't say it" claim weakens.
- **(i) CPU, owner W-text, no GPU.** On E15's 7 valid rows: fit a classifier on W1 *dev* items using only the last 4
  tokens before the read position (character 1–4-gram logistic, E1b's recipe). Freeze a cutoff on dev (the median
  predicted probability margin). Split W1 *test* items into local-cue-informative and uninformative strata and report
  E15's sealed per-item continuation scores as AUROC within each stratum, with item bootstrap. **Prediction (local
  cue):** ≥ 0.75 in the informative stratum and ≤ 0.60 in the uninformative. **Prediction (remote state):** both ≥ 0.70.
- **(ii) GPU ≤ 0.4 GPU-h, owner W-internals, after E30.** E3's in-lens probe at the pre-answer position, trained on W1
  dev, applied to the E17 and E20 twin items (identical last ≥ 8 tokens across states), for `prose_paren` and
  `python_string`; plus E15's exact frozen pairs scored on E20's distance-2 and distance-4 items. **Control:** the
  source probe on h44 for the same twins (must stay ≥ 0.85, else uninterpretable).
- **Rules.** In-lens probe on twins ≥ 0.85 with CI above 0.75 → E3's reading stands on hard items. ≤ 0.65 with the
  source probe ≥ 0.85 → the lens's input discards remote state, and E3 is reinterpreted as reading local cues. E15
  pairs on E20 distance-2 items ≥ 0.70 → E20's chance result was its channel definition; ≤ 0.60 → E15 is bank-specific
  and is reported as such.

**Dated clarification 1, 2026-10-25 12:45 CET (answers W-text, before any E31 score).** "The last 4 tokens before the
read position" means the **last 4 tokens of the stored prefix, including the read token itself** (`ids[-4:]`). The
activation being read is computed at the read token, so the read token is part of the local cue the lens could be
using; excluding it would understate the local-cue account.

**Dated clarification 2, 2026-10-25 14:15 CET (answers W-internals, before any E31(ii) score).** E31(ii) reports
E3's **full in-lens layer profile** for the twins, and the decision rule is applied at **E3's last in-lens layer**
(the layer behind E3's headline 0.95), fixed now. The other layers are descriptive.

