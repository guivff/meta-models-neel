## §87 W11. Minimal-pair check of §84's current-token blind spots (pre-registered 2026-10-24 01:10 CEST, before any §84 score is opened)

**Why.** §84's items pass the length checks, but the padding differs systematically by value. A text-only classifier
reads the value from the padding alone at about 0.69 AUROC, and at 0.83 for `current_number` (W-core `4af0a1c8`). So a
probe could partly read padding rather than the feature, which would inflate the probe ceiling and with it any
"blind spot". §87 removes padding as an information source **by construction**.

**Owner:** W-core builds the items and runs the analysis; the integrator operates the pod. **Cap:** min(1.5F + 360, 3,600) s
of science (at most 1.0 GPU-h, warmed units), with a 1,500 s setup allowance outside it. **Target:** Saturday.

**Rows.** All 10 §79 top-10 features. If time or budget runs short, priority goes to the features §84 marks as
confirmed. That selection rule is fixed now, and §84 confirmation status is the only input to it.

**Items: minimal pairs.**
- Each item pair shares an **identical token prefix**, and the two values differ **only in the target token span**,
  which is read at its last token.
- The two target spans have the same token count. Examples:
  - number vs word: "came to [4500 | about]", matched in token count;
  - magnitude: "4500" vs "45.0", the same number of tokens;
  - preposition or auxiliary vs a same-length content word: "walked [into | home]", "it [has | hot]";
  - all-caps vs lower-case: the same word;
  - colon vs comma.
- Everything after the target is absent, since the read position is the target's last token.
- 120 items per row (60 per value), from ≥ 12 carrier contexts; dev and test split by context.
- A test asserts that the prefixes are identical and the span token counts equal.

**Arms.** As in W1:
- asked paired log-odds for the Oracle lens (44), the NLA (42) and the J-lens (44), with 2 frozen phrasing pairs per
  feature;
- the probe ceiling at 42 and 44;
- the random-donor gate [0.40, 0.60] from §85, which is clean here because each context carries both values.
- **Built-in leak check:** the probe at the token *before* the target. Its activations are identical across the two
  values by construction, so it must give AUROC 0.5 ± 0.02. If it doesn't, the row is NOT EVALUABLE (pipeline error).

**Rule, per feature.** Confirmed if Oracle ≤ probe − 0.15 *and* the gates pass. NLA − Oracle is reported with a paired
CI. Summary: **CONFIRMED if ≥ 70% of evaluable features confirm.**

**Secondary (descriptive).**
- Agreement with §84's per-feature status: did a §84 confirmation survive the removal of padding?
- The J-lens.

Scores are sealed before the label join; no sign is ever flipped. Results go to `results/g_agreement/blindspot/w11/`.
