# E35 authority snapshot — 2026-10-25

Verbatim excerpts from `projects/g_agreement/BRIEF_UNDERSTAND.md` at `5731e92e0835e2a20d57a88cfcae7f3f57108fe4`. The 12:55 operations note assigns E35 to W-sae.

## §130 Budget increase and reallocation (25 Oct, 12:30 CET)

**Dated note (Guiv, recorded by the coordinator), operations and budget only, before any score of the affected runs.**
Guiv has added USD 500 (≈ 94 H200-hours at ~$5.30/h). Allocation, with about USD 290 held in reserve for reruns,
W12 and anything Monday's results force:
- **E24 restored to its registered scope** (§118 as registered with clarifications 1–2: all 11 grid layers, C1–C7),
  replacing the 12:05 five-layer cut; total cap **12 GPU-h including attempt 1's 1.45**, conditional as before on
  E24-D naming the cause. Up to 4 pods.
- **E28 restored to its registered arms** (§122 as registered: arms L, B and S on all six rows), replacing the 12:05
  demo cut, ≤ 5 GPU-h, still after E30–E32 in priority. R3 is reported with the confound E33 identifies stated in the
  write-up.
- **E35 (SAE on the reconstruction error, §131): ≤ 6 GPU-h.**
- **E36 (second item bank for the headline rows, §132): ≤ 3 GPU-h.**
- **Pod ceiling raised from 6 to 8.** Minimum 5 minutes between launches stays.
- Per-experiment caps elsewhere are unchanged. Nothing about rows, rules or thresholds changes.

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

**Dated note, 2026-10-25 12:55 CET (coordinator), operations only: parallelisation, before any score of the affected
runs.** The queue order in §125–§131 was a convenience, not a dependency. Only these dependencies are real: E34 waits
for E24-D to clear h44 parity; E24 attempt 2 waits for E24-D; E29's reader scoring waits for W-text's sealed D and the
coordinator's posted predictions. Everything else may be built and launched as soon as it is ready. Ownership:
- **W-internals:** E22 analysis first, then builds E30 and E31(ii) in parallel; launches each when ready.
- **W-core:** E32 (moved from W-internals; W-core owns W1 scoring and is otherwise waiting on E24-D), then W12.
- **W-mechanism:** E26 analysis, then E27(c) and E34.
- **New chat W-lens:** E33, then E28 (full arms).
- **New chat W-sae:** E35.
- **W12** is brought forward: it may run tonight, as soon as E29's blinding order (§124 steps 1–3) is complete,
  instead of Monday. Its registration (§100) is otherwise unchanged.
Pod ceiling 8 (§130); priority when contended as in §130, with E32 taking E31's slot order.
