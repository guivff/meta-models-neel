# §64–§66. Activation or prior: decomposition, error types by reader, and a per-claim detector (pre-registered 2026-10-22 16:30 CEST, before any §64–§66 number)

Coordinator: Guiv. Model Qwen3.6-27B. Readers: Oracle lens (`olens_s3d_rl600` + its AR and whitener, block 44) and the RL NLA
(block 42), each at the site it was trained on, as in SA-R. J-lens appears only as a baseline row where noted.
Main question these serve: **what decides what an activation reader tells you, the activation or the reader's own prior?**
Shared rules: scores sealed before label joins; Wilson 95% intervals for rates; item-clustered bootstrap (2,000) for
differences; MISSING readouts kept in denominators and reported; judge prompts frozen and hashed before dispatch; judge
google/gemini-3.8-flash via OpenRouter, readout text and opaque IDs only. Log to `results/g_agreement/log.md` and
`compute.jsonl`. Results to `results/g_agreement/v_prior/`.

---

## §64. Prior decomposition: how much of a readout is the activation, how much the reader's prior?

**Owner:** lens chat (after §60 B2). **Cap:** 0.3 GPU-h, $5 judge. **Target:** Friday 18:00.

**Arms (per reader):**
- TRUE: the item's own activation (reuse cached readouts).
- MISMATCHED: another item's activation, same frozen derangement as the source experiment (reuse cached readouts).
- NULL (new): the bank-mean activation at the same block and position, rescaled to the bank's mean norm. Secondary NULL:
  one covariance-matched Gaussian draw per sample (from the whitener statistics), same norm. A NULL readout carries no
  item information, so it is generated once per reader and scored against every item.

**Sets (each with the claim category already used in its source experiment):**
- S1 concept injection (SA-R, 396 edited states): readout names the assigned concept.
- S2 clean-model audit (100 ordinary prompts, neutral framing): readout leads the interpreter to report a hidden goal or
  instruction.
- S3 sibling alternatives (§59, 60 items): readout names a same-category alternative from the frozen vocabulary.

**NULL sample size:** 400 readouts per reader per variant (same decoding as the source runs).

**Quantities (per reader × set):** P_true, P_mis, P_null. Prior share = P_null / P_true; generic-activation share =
(P_mis − P_null) / P_true; state-specific share = (P_true − P_mis) / P_true. Intervals by joint bootstrap (items for
TRUE/MISMATCHED, samples for NULL).

**Predictions (registered):**
1. S2: prior share ≥ 0.5 for both readers (false alarms are mostly prior).
2. S1: state-specific share ≥ 0.8 for both readers (injection naming is mostly the state).
3. S3: prior + generic-activation share is higher for the Oracle lens than the NLA (descriptive, links to §65).
Decision: 1 and 2 CONFIRMED if the point estimate meets the bound and the 95% interval excludes the opposite side of the
bound by the same margin (prior share CI lower bound > 0.35 for 1; state-specific CI lower bound > 0.65 for 2).

**Deviation guard:** if NULL readouts are degenerate (empty or > 20% MISSING), report NOT EVALUABLE for that variant and fall
back to the secondary NULL; do not tune the null after seeing outputs.

---

## §65. Does each reader's error type follow from its training objective?

Hypothesis: the Oracle lens inverts a reconstructor that maps text to the *average* activation over contexts, so its errors
should be near-misses (the typical member of the right category); the NLA reconstructs everything and writes freely, so its
errors should drift (specific content unrelated to the state).

### §65A. Error typing on existing wrong claims (no generation)

**Owner:** remainder chat. **Cap:** 0 GPU-h, $5 judge. **Target:** Friday 18:00.

- Pool: wrong claims already labelled in SA-R (readouts naming a non-target concept), S2 false alarms, §61 unfounded claims,
  §59 alternatives classed PRIOR. Deterministic stratified sample (seed 20261022) of up to 300 per reader, balanced across
  sources as far as availability allows; the sample is frozen and hashed before judging.
- Judge (blinded to reader and condition) sees the true content description (injected concept / prompt text / source span)
  and one claim, and assigns exactly one: NEAR-MISS (same category as the true content: related concept, sibling entity,
  the typical sense), DRIFT (specific content unrelated to the true content), GENERIC (non-specific filler such as "the
  user wants help"). Second judge on a 20% subsample for κ.
- Same typing on the matching MISMATCHED-arm claims as the baseline mix.
- **Primary:** NEAR-MISS share Oracle − NLA > 0, and DRIFT share NLA − Oracle > 0; clustered bootstrap, Bonferroni over 2.
  Both CONFIRMED → "error type follows the objective". One → PARTIAL. None → NOT MET (reported as a one-paragraph null).

### §65B. Ambiguity test: does the Oracle lens fall back to the typical sense?

**Owner:** inverter chat (after the §57 mismatched control). **Cap:** 0.4 GPU-h, $4 judge. **Target:** Saturday 18:00.

- Items: 40 ambiguous words × 2 senses × 2 cue distances (disambiguating cue adjacent to the word, or ≥ 15 tokens before it)
  = 160 prompts, authored and frozen before any readout. Read position: the ambiguous word's last token.
- Typical sense per word fixed label-blind before readouts: the sense the base model prefers when asked with no context
  (forced-choice log-probability between the two glosses).
- Arms: TRUE; MISMATCHED (same word, opposite sense, same cue distance); a probe ceiling (logistic regression on the same
  activations, cross-validated leaving whole words out).
- Outcome: judge maps each readout to sense A / sense B / neither (blinded). 4 samples per item per reader.
- **Primary:** typical-sense reversion = P(reports typical sense | context fixes the other sense). Prediction: Oracle > NLA,
  and the gap is larger at the far cue distance. Clustered (by word) bootstrap; CONFIRMED if Oracle − NLA > 0 with CI
  excluding 0. Far-minus-adjacent interaction reported as SECONDARY.

---

## §66. Can you tell, per claim, whether it came from the activation?

**Owner:** P3 (has the AR / whitened-FVE pipeline). **Cap:** 0.8 GPU-h, $10 judge. **Target:** Monday 18:00.

**Signals per claim (all frozen before the test set is generated):**
1. Contrastive FVE: whitened FVE of the claim's AR reconstruction against the true activation minus against a mismatched one.
2. Resample agreement: share of K = 8 resamples on the same activation that contain an equivalent claim (judge).
3. Mismatched recurrence: share of K = 8 samples on mismatched activations that contain it (the per-claim prior signal).
4. Length (baseline).

**Data:**
- Development (already seen; used to fit): SA-R hits vs non-target namings; §61 founded vs unfounded.
- Held-out test (new, generated after this registration): §65B sense claims (correct vs wrong) and §62 dose-curve readouts
  (assigned concept vs other).

**Analysis:** logistic regression on development, coefficients frozen and committed before the test labels are joined.
Report AUROC per signal and for the combination on test, per reader.

**Decision rule:** CONFIRMED if the combination reaches AUROC ≥ 0.75 on test and beats the best single non-length signal by
≥ 0.05 (paired bootstrap CI excluding 0). Otherwise report the best single signal.

**Per-reader prediction (from §65):** contrastive FVE separates NLA errors better than Oracle errors (Oracle near-misses
reconstruct almost as well as the truth); mismatched recurrence is the stronger signal for the Oracle lens.

**Deliverable:** a performance-versus-hallucination curve: at each threshold of the frozen detector, the share of
ungrounded claims removed versus the share of grounded claims kept, on test and (descriptively) on the S2 false alarms.

---

## Optional, Monday only if GPU remains (design sketches, not yet registered)

- **§67 Same continuation, different content.** Pairs of activations whose next-20-token distributions match (KL below a
  frozen threshold) but whose content differs; readout divergence per reader. Tests the claim that the Oracle lens should
  say similar things about activations with the same continuation while the NLA should not.
- **§68 Text buffer.** By layer and position, the share of each Oracle readout that overlaps the model's actual continuation
  versus the preceding text, with special attention to sentence-final positions.

## Deviations

**2026-10-22 16:45 CEST (Guiv), before any §64–§66 number, after an external review:**
1. §64 naming. "Prior share" is renamed **activation-independent share** (P_null / P_true) and "generic-activation share"
   is renamed **activation-general share**. §64 measures how much output does not depend on the item's activation; it does
   not attribute that output to a source (pretrained knowledge, question presuppositions, metamodel training, templates).
   Predictions and decision rules are unchanged.
2. §64 audit-set scoring. For S2, in addition to the interpreter's yes/no hidden-goal verdict, a blinded judge scores the
   raw readouts' atomic claims for specificity (specific goal / vague suggestion / none), on a frozen sample of 50
   prompts × 3 arms; reported as SECONDARY, to separate reader output from interpreter amplification.
3. §66 labels. Each labelled claim carries separate fields where determinable: factual correctness, contextual grounding,
   activation dependence (more likely under the matching than the mismatched activation), and, for the puzzle and dose
   sets, computational relevance. The primary §66 outcome is activation dependence; correctness is SECONDARY. Length and
   a judged specificity score are both baselines.
4. Prior work to cite and compare against: "Current Activation Oracles Are Hard to Use on Safety-Relevant Tasks"
   (no-activation and forced-token controls; low-dose steering detected before visible output), the NLA paper, Activation
   Oracles, WorkspaceBench.

**2026-10-22 16:40 CEST (Guiv), before any §54, §62 or §66 number:** §54 is reduced to its core (concepts, doses, prompts
and five controls at native reader sites); its FVE claim scoring is deferred. To keep claim scoring confirmed on fresh
data, the §54-core readouts join §66's held-out test set alongside §65B and §62. Coefficients are still frozen on the
development sets before any test label is joined. Nothing else in §66 changes.

**2026-10-22 16:40 CEST (Guiv), before any §66 fitting or test-label join — label source:** §66's primary
activation-dependence labels come from the experimental design, never from the detector's own resample or recurrence
features (that would be circular).
- Concept sets (SA-R development; §62 and §54-core test): a claim naming the assigned injected concept is
  ACTIVATION-DEPENDENT (the edit is the only difference from the paired no-edit state). A claim that also appears in the
  paired no-edit or random-direction readout of the same prompt is ACTIVATION-INDEPENDENT. Other claims are UNLABELLED.
- §65B word senses (test): a readout stating the context-fixed sense, where the opposite-sense pair does not, is
  ACTIVATION-DEPENDENT; a readout stating the typical sense when context fixes the other sense is ACTIVATION-INDEPENDENT.
  Other claims are UNLABELLED.
- §61 founded/unfounded (development) carries correctness labels only and enters the SECONDARY correctness analysis.
- UNLABELLED claims are excluded from the primary analysis and their count is reported.
- Feature/label separation: the K = 8 mismatched-recurrence feature uses fresh donors disjoint from every arm used to
  assign labels (no-edit, random-direction, opposite-sense pair); the K = 8 resample feature uses fresh samples, not the
  readouts being labelled.
- "Puzzle" in the 16:45 note refers only to the existing silent-wrong-answer set, which may carry a computational-relevance
  field descriptively. There is no separate puzzle registration: §66's test set is §65B, §62 and §54-core.

**2026-10-23 06:15 CEST (Guiv), before any §64, §65A or §66 test number:**
1. §64 is cut. No run will be made, and no §64 result will be reported.
2. §65A is deferred: it is not run in this sprint, and its registration stands unchanged for later work.
3. §66 scope: the detector is scoped to whether a claim is about this activation (activation dependence). It makes no
   claim about hallucination on natural readouts in general; another team reports that higher FVE does not reduce
   hallucinations on natural WorkspaceBench readouts, which is a different question. Nothing else in §66 changes.

**2026-10-23 09:10 CEST (Guiv), prospective amendment to §66, before any §66 coefficient is fitted and before any
test label is opened (R3 has not run):** only 128 of the 3,960 development K = 8 readouts exist, so the resample
agreement and mismatched recurrence signals cannot be fitted. §66's primary detector is therefore **FVE-only**.
1. **Primary signal:** contrastive FVE (whitened FVE against the true activation minus against a mismatched one),
   already complete on the development sets. Its sign and any threshold-free orientation are fixed on development data
   and committed before any test label is joined.
2. **Primary rule:** CONFIRMED if contrastive FVE reaches test AUROC ≥ 0.75 *and* beats the length baseline by ≥ 0.05
   (paired bootstrap CI excluding 0), per reader. Otherwise NOT MET. Report the specificity baseline alongside.
3. **Test set:** §65B R3, plus §62 and §54-core only if they exist by the time compute stops. Any set that doesn't
   exist is reported NOT RUN.
4. **Dropped from the primary analysis:** resample agreement and mismatched recurrence, with no new collection for
   them. If GPU remains after the blind-spot programme, they may be collected and reported as EXPLORATORY only.
5. Everything else stands, including the labels from the 16:40 note, feature/label separation and the scope note.

**2026-10-23 13:05 CEST (Guiv), §66 compute only, before any test-label join:** the §65B R3 claims need reconstructor
(AR) predictions to compute contrastive FVE. §66 gets one **AR-only run**: 2,560 forwards on the sealed AR inputs,
with no reader generation and no judge, at most **0.3 GPU-h** of science (1.5 x the smoke forecast), setup outside it.
It runs on the shared volume and counts science from the first science step. The frozen orientation, labels, rule and
test set are unchanged. This lifts the earlier no-new-runs instruction for this run only.

**2026-10-23 14:20 CEST (Guiv), §66 AR-only run, budget only, before any test-label join:** the AR-only attempt stopped at its timing gate. One fresh attempt is authorised, with science cap min(1.5F + 120, 3,600) s. F is the per-unit timing measured in the stopped attempt's smoke (timing only, no outputs used) times the number of remaining units. Setup is 2,400 s outside the cap, with a warm-up before the gate. If 1.5F + 120 > 3,600 s, report to Guiv instead of launching. Everything else is unchanged.

**2026-10-23 14:25 CEST (Guiv), §66 headroom, budget only, before any test-label join:** with F = 662.1 s, min(1.5F + 120, 3,600) = 1,113.2 s leaves the gate no headroom (the same problem as W7). The cap is **min(1.5F + 360, 3,600) = 1,353.2 s**. Everything else is unchanged.
