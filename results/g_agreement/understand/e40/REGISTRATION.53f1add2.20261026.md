# E40 authority snapshot — 2026-10-26

§142 at `53f1add2`, including clarification1. New experiment after both E35 failures; E35 files remain sealed.

## §142 E40. A second SAE attempt for the reconstructor's error (Neel's ask; after E35)

**Registered 2026-10-26 00:55 CET. EXPLORATORY; its design changes were chosen after E35's gate failures and are
disclosed as such.** **Owner:** W-sae. **Cap:** 14 GPU-h total, seed 20261026.
- **(a) CPU diagnostic on E35's sealed gate outputs (descriptive, now).** FVU and dead fraction of both failed SAEs by
  token position (0, 1–7, 8+), by activation-norm decile, and by domain. The diagnostic changes nothing below.
- **(b) SAE.** TopK, 65,536 latents, k = 128, AuxK loss for dead latents (coefficient 1/32, k_aux = 512), Adam
  lr 2e-4.
  - **Input scaling:** inputs are scaled by one fixed scalar, computed on training tokens only, so their mean norm is
    √5120.
  - **Excluded tokens (fixed now):** position 0, and any token whose norm exceeds 10 × the training median. They are
    excluded from training and from the gate.
  - **Training data:** 100M unique tokens: §79 training documents, then E35's pinned FineWeb-Edu revision. Streamed
    in one pass, on one pod.
- **Gate:** E35's 50,000 held-out tokens minus the excluded tokens. FVU ≤ 0.25 and dead < 10%, the same thresholds.
  FVU on all 50,000 tokens is reported beside it.
- **If the gate passes:** §131's decomposition, rules and clarification 1 apply unchanged (R1 window loss, R2 policy
  loss, frozen latent rubric, blind judge).
- **If it fails:** "no adequate SAE" again; no third attempt.

**Clarification 1 (2026-10-26 01:15 CET, answers W-sae, before any E40 training step).** Calibration is fixed as
follows.
- **Population:** the first 1,000,000 training tokens in stream order: §79 training documents in manifest order,
  then FineWeb-Edu. Position 0 of every document is excluded.
- **Order of computation:**
  1. Compute the median block-44 norm m on that population.
  2. Set the outlier threshold to 10·m.
  3. Compute the mean norm μ on the population after removing tokens above 10·m.
  4. Set the scale factor to √5120 / μ.
- **Seal:** m, 10·m and the scale factor are written to `CALIBRATION.json` and sealed before training step 1. The
  same three constants apply unchanged to training and to the gate's exclusions. Nothing is recomputed on held-out
  tokens.
- The calibration tokens are also used for training; no second pass is made.
