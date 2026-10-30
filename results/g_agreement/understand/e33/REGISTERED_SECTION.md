## §128 E33. Adapter dose on visible text (policy vs activation reading)

**Registered 2026-10-25 12:05 CET, before any E33 score. EXPLORATORY.** **Owner:** W-mechanism, after E27(c).
**Cost:** ≤ 0.4 GPU-h.
**Why.** E12(c) (lens with the text in its prompt, 0.56–0.63) and E16 (base Qwen from text, 0.95) used different
prompts, so "the lens can't judge structure even in text it can see" is not clean.
**Design.** W1's 25 rows × 84 test items, W1 frozen phrasings, paired log-odds AUROC, text in the prompt, **no injected
activation**. LoRA scale λ ∈ {0, 0.25, 0.5, 0.75, 1} × two prompts: P1 = E16's base wrapper; P2 = the lens's native
prompt with the text prefix and an uninjected placeholder (E12(c)). **Control arm:** content rows. **Measure:** the
λ=0→1 drop in structure-row median under P1, minus the same drop on content rows, item-cluster bootstrap.
**Rules.** Difference ≥ 0.20 with CI above 0, structure under P1 falling from ≥ 0.90 to ≤ 0.65 while content stays
≥ 0.95 → the adapter's policy itself cannot judge structure, even from text. Structure at λ=1 under P1 ≥ 0.85 → the
lens *can* read structure from text; E12(c)'s low score was the prompt, and the blind spot is about reading activations.

