# Source: `e71d1eeb`, BRIEF_UNDERSTAND.md §114

## §114 E22. Where does structure reach each output? Layer-wise activation patching inside the Oracle lens

**Registered 2026-10-25 06:15 CET, before any E22 score exists. EXPLORATORY; supersedes E19 as the causal test.**
**Owner:** W-internals (reuses E19's hooks and harness, on `/weights/venv-kernels`). **Inputs:** W1's sealed block-44
test activations. **Cap:** min(1.5F + 360, 7,200) s, setup 1,500 s.

**Why the design is clean.** The Oracle lens's prompt is identical across items; only the injected activation differs.
Patching a residual from a donor run into a recipient run therefore swaps state and nothing else.

**Rows (5, as E19):** `prose_paren`, `python_string`, `table_role`, `python_depth`, and `prose_sentiment` as the
content positive control. 84 test items each; each recipient's donor is a seeded (20261025) test item of the same row
with the opposite value.

**Interventions.** Run the recipient and donor through the lens's two native prompts: (A) the asked prompt with W1's
frozen phrasings and (C) the continuation prompt with E15's frozen pairs (sentiment: asked only, as E19). For every 4th
layer (0, 4, 8, …, and the last) and two positions, (i) the injection position and (ii) the last prompt position before
the output (pre-answer for A, after the `- ` prefix for C), replace the recipient's residual at that (layer, position)
with the donor's. Controls: patching from a **same-value** donor (should change nothing) and patching the injected
activation itself (layer 0, injection position, which reproduces W1 / E15 swaps).

**Measure.** Per (row, prompt, layer, position), the fraction of the full-swap effect recovered:
(score_patched − score_recipient) / (score_donor − score_recipient), averaged over items (signed toward the donor's
value), with item-cluster bootstrap CIs. For the asked prompt, where the full swap has little effect on structure rows,
also report the raw paired change in log-odds.

**Predictions.** (1) **Content control:** patching at the injection position in early layers, and at the pre-answer
position in later layers, recovers most of the asked effect (>= 0.50) — the test can see an answer pathway when one
exists. (2) **Structure, continuation prompt:** the effect passes from the injection position to the pre-output position
in mid layers (>= 0.50 recovered at the pre-output position at some layer). (3) **Structure, asked prompt:** no
(layer, position) moves the asked log-odds by more than the same-value control's 95th percentile, even at layers where
E3's probes read the state at the pre-answer position — i.e. the state reaches the answer position but the answer does
not read it. **Alternative:** if some (layer, position) does move structure answers, the answer pathway exists and is
localised there.


