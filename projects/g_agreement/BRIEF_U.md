# §63. Decodable but unspoken: what readers can read but never volunteer (pre-registered 2026-10-22 13:00 CEST, before any §63 number)

Owner: Suraj (U0–U1, U3); Neel5 (U2, as an add-on to §62 part A). Coordinator: Guiv.
Model Qwen3.6-27B. **Single site: block 42, last prompt token** for every reader (Neel: inter-method comparisons at one layer only).
Readers: NLA (RL, block 42), Oracle lens (`olens_s3d_rl600` + AR), J-lens (camilablank/workspace-lenses). Probe = logistic
regression on the raw residual, 5-fold CV by item, L2 chosen on an inner split.

## Motivation

Suraj's structural-concept run (layer 42, 14 properties, 320 free readouts per reader) found rows with high prompted
discrimination but zero spontaneous mention: NLA sentence position prompted AUROC 0.72, stated in 0/320 free readouts; same
pattern for line position and indentation. Line position is also used by the model (steering it shifts line breaks). The
Oracle lens states nothing anywhere because it continues text rather than describing it (output-format effect); that is a
caveat, not the finding. The finding to test: **what a reader volunteers is not set by what it can read.**

Definitions (frozen):
- PROMPTED: reader's forced-choice AUROC for the property (same question template for every reader; per-reader template as in
  Suraj's run, unchanged).
- STATED: free readout explicitly names the property value (judge, frozen prompt from Suraj's run).
- EXHIBITED: free readout shows the value without naming it (e.g. French continuation for French input). Reported, but the
  "unspoken" label uses STATED only for NLA and STATED ∪ EXHIBITED for the Oracle lens and J-lens.
- MISMATCHED: PROMPTED computed with the reader fed a different item's state (same property distribution, shuffled within
  property strata).
- UNSPOKEN (property × reader): PROMPTED − MISMATCHED ≥ 0.10 with item-bootstrap 95% CI excluding 0, AND spontaneous rate
  Wilson 95% upper bound < 2%.

## U0. Gating checks (must pass before U1–U3 are interpreted)

1. Mismatched-state arm for every property × reader in Suraj's existing set. Rows where PROMPTED − MISMATCHED CI includes 0
   are reported as "answered from the question, not the state" and excluded from the UNSPOKEN list.
2. Probe ceiling per property (block 42). Report reader PROMPTED as a fraction of probe AUROC.
3. Zero counts reported as Wilson upper bounds (0/320 → "< 1.2%"), never as "never".
Status rule: if no property is UNSPOKEN after U0 for the NLA, §63 headline = NOT MET and U1/U3 are DESCRIPTIVE only.

## U1. What predicts whether a reader volunteers a property? (Suraj)

- Expand to ≥ 40 properties (Suraj's 14 + ≥ 26 new: text-position, formatting, syntax, lexical, semantic/topic, speaker/user
  attributes), ≥ 200 items each, frozen list committed before any reader is run on the new properties.
- Outcome: logit spontaneous STATED rate per property (NLA primary; Oracle lens STATED ∪ EXHIBITED secondary).
- Predictors (each z-scored across properties):
  (a) probe AUROC; (b) reader PROMPTED − MISMATCHED; (c) downstream influence = mean KL of next-20-token distribution after
  patching the probe direction to the opposite class mean (block 42, last token); (d) verbalisation prior = fraction of the
  NLA's training descriptions (sample of 5,000) mentioning that property type (judge, frozen prompt; ≤ $5).
- Analysis: single-predictor Spearman ρ for each, then a joint linear model; property-level bootstrap (2,000) for CIs.
- Prediction (Guiv): (d) has the largest standardised coefficient for the NLA and (c) for the Oracle lens; (a) is not
  significant once (b) is in. Decision rule: a predictor "explains" volunteering if its joint-model CI excludes 0.
- n justification: 40 properties gives ~80% power for ρ = 0.45 at α = 0.05 (two-sided). Effects smaller than that are
  reported as NOT EVALUABLE, not as null.

## U2. Can you make it speak? (Neel5, add-on to §62 part A)

- Properties: every UNSPOKEN property from U0 (cap 6), plus 2 control properties the NLA already states (language, code).
- Push the block-42 last-token activation along the property's probe direction, scaled to 0.3/0.5/1.0/1.5/2.0 × the
  class-mean separation; arms: probe direction, random direction (norm-matched), no edit. 50 items × 4 samples per cell.
- Outcome: spontaneous STATED rate per dose, minus random arm.
- Decision: THRESHOLD if the direction arm exceeds random by ≥ 10 points at any dose ≤ 1.5 with CI excluding 0; UNREPORTABLE
  if not at 2.0; report model behaviour change (answer flip / KL) alongside, so "speaks only once the model is broken" is visible.

## U3. Used but unspoken (Suraj)

- For every property: steer the block-42 probe direction (dose 1.0) and record whether model behaviour changes (KL of
  next-20-token distribution vs random direction, item-paired bootstrap; property-relevant behavioural metric where one exists,
  e.g. line-break position for line position).
- USED-UNSPOKEN = USED (KL CI excludes random) ∧ UNSPOKEN for that reader. Report the list per reader; this is the direct answer
  to Neel's "what does X find that Y doesn't". Line position is the pre-specified positive control for USED.

## Budget and timing

U0 ≈ 0.3 GPU-h; U1 ≈ 1.0 GPU-h + ≤ $10 judge; U2 ≈ 0.4 GPU-h (added to §62 cap); U3 ≈ 0.3 GPU-h. Total cap 2.0 GPU-h, $15.
Targets: U0 Friday 12:00; U1, U3 Saturday 18:00; U2 with §62. Hard stop: compute ends Tuesday night.
Log runs in `results/g_agreement/log.md` and `compute.jsonl`. Results to `results/g_agreement/u_unspoken/`.

## Deviations

**2026-10-22 16:45 CEST (Guiv), before any §63 number, after an external review:**
1. Clustering. All U0 intervals are bootstrapped over prompt templates (clusters), not items, wherever items share a
   template. `gate.py` takes an optional `cluster` field and uses it when present.
2. Nuisance-matched mismatch. The MISMATCHED donor for each item is drawn from items with the opposite label but the same
   task family, the same language and the same token-length bin (tertiles) where such a donor exists; otherwise the
   nearest bin. The donor map is committed and hashed before any reader is run.
3. Pre-specified examples. List index (prompted 1.00, volunteered 25%) is named alongside sentence position as a
   pre-specified test case; language and code are pre-specified positive comparisons (high prompted, high volunteered).
   The UNSPOKEN rule is unchanged; list index is reported as a "decodable but rarely reported" case (volunteered rate with
   its interval) whether or not it meets the < 2% rule.
4. Three-way dissociation. U3 reports, per property, all three criteria side by side: probe AUROC, steering effect on
   behaviour (KL vs random direction), and prompted-minus-mismatched with the volunteered rate.
5. U1 status. U1 runs only on properties that pass U0, as already registered. Its verbalisation-prior predictor is
   reclassified DESCRIPTIVE (it is estimated from the reader's own training descriptions, so a correlation may only
   measure stable reporting conventions); no causal claim is drawn from U1.
