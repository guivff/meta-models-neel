# E35 authority snapshot — 2026-10-25

Verbatim §131 including clarification 1, from commit
`ff48f19ac143b436c7c6e9586473f1e160045da9`. This dated snapshot does not edit the registration.

## §131 E35. What is in the reconstructor's error? (SAE decomposition; the mentor's ask)

**Registered 2026-10-25 12:30 CET, before any E35 capture or score. EXPLORATORY.** **Owner:** W-mechanism, after E33.
**Cost:** ≤ 6 GPU-h.
**Why.** Neel: "you could also just directly study what is in the error of the AR … methods like SAEs could be useful
for interpreting the remainders."

**SAE (gated, decided before any decomposition).**
- (a) **Transfer option:** Qwen-Scope's Qwen3.5-27B residual SAE at layer 44 (`Qwen/qwen-scope` collection), applied
  to Qwen3.6-27B block-44 activations. **Gate:** fraction of variance unexplained ≤ 0.25 and dead latents < 10% on
  50,000 held-out tokens of the §79 corpus.
- (b) **If (a) fails the gate:** train a TopK SAE (16,384 latents, k = 64) on ≥ 20M tokens of block-44 activations from
  the §79 corpus, same gate on held-out tokens. If (b) fails the gate, E35 reports "no adequate SAE" and stops.
- No other SAE source is used.

**Decomposition (W1 test items, 25 rows).** For each item: h = block-44 activation; R_win = AR(real next 16 tokens);
R_ol = AR(the Oracle lens's own greedy readout of h). Two error terms:
- **window loss** e_w = h − R_win (what the next tokens can't convey);
- **policy loss** e_p = R_win − R_ol (what the next tokens convey but the lens's readout doesn't).
Encode h, e_w and e_p with the SAE (after the same normalisation as the SAE's training).

**Latent labels, frozen before decomposition.** The 300 latents most active on W1 dev items are auto-interpreted by
a blind judge from their top-20 activating corpus contexts (no row names shown), into *structure*, *content* or
*other*, with a frozen rubric committed first. 30 latents are double-coded by a second judge; κ reported.

**Measures.** For each error term, the share of its SAE reconstruction norm carried by *structure* latents, against
the same share in h itself (the baseline); per-row linear probes on each term's SAE code. **Control:** latents matched
on activation frequency, labels shuffled.

**Rules.**
- **R1 (Neel's intuition):** structure-latent share in e_w exceeds its share in h by ≥ 1.5×, CI above 1.
- **R2 (policy account):** structure-latent share in e_p exceeds its share in h by ≥ 1.5×, CI above 1.
- Both, one, or neither can hold; each is reported. **Descriptive:** which named latents dominate e_p on the state
  rows (paren, string, cell role), with their top contexts.

**Clarification 1 (2026-10-25 14:40 CET, coordinator; before any E35 gate result, latent label or decomposition).**
Answers W-sae's held question; no rule threshold changes.
- **Norm share (defines "share of its SAE reconstruction norm").** For one vector x with SAE code z (the SAE's own
  encoder, as in the gate plan) and decoder columns d_i, the structure share is
  s(x) = Σ_{i∈S} z_i‖d_i‖ / Σ_i z_i‖d_i‖, where S is the set of latents labelled *structure*. b_dec is excluded. This
  measure is bounded in [0, 1] and additive across latents, with no cross terms. An item whose code is all zero has
  s undefined: it is excluded and counted. If more than 10% of items are excluded for a term, R1/R2 for that term is
  uninterpretable.
- **Ratio and CI.** For each term e ∈ {e_w, e_p}: ratio = mean_items s(e) / mean_items s(h), computed on the same
  items (ratio of means). The 95% CI is an item bootstrap clustered by row, 10,000 resamples, seed 20261025. R1/R2 as
  registered: ratio ≥ 1.5 and CI lower bound > 1.
- **Control.** For each term, the same ratio with S replaced by frequency-matched latents with shuffled labels (|S|
  latents, matched on activation frequency on dev items, 100 seeded draws). Reported as the null distribution beside
  each ratio.
- **Encoding difference vectors.** The primary analysis encodes e_w and e_p directly, as registered. Descriptive
  only, not ruled on: the code difference E(h) − E(R_win) and E(R_win) − E(R_ol), with the structure share of its
  positive part.
- **Fallback (b) corpus (decided now, before the gate).** The §79 corpus has about 0.96M raw tokens (0.41M
  training-prefix tokens), so (b)'s "≥ 20M tokens" cannot be met with unique §79 tokens. If (a) fails the gate, (b)
  trains on all §79 training documents (every position, holdout source groups excluded) plus the first tokens of
  `HuggingFaceFW/fineweb-edu` `sample-10BT`, at a revision W-sae pins and commits before the gate result, up to
  20M unique tokens. Activations are streamed, not stored. The gate stays on the same 50,000 §79 held-out tokens. The
  ≤ 6 GPU-h cap is unchanged.
- **Pod limits:** use the integrator's current §135 ceiling and spacing. The HANDOFF's "eight pods / five minutes" is
  stale and conservative; either way it is harmless.
