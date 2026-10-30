# §70–§78 (W1–W9). Blind-spot map of activation readers (pre-registered 2026-10-23 06:00 CEST, before any W number)

Coordinator: Guiv. Model Qwen3.6-27B. Readers at their trained sites: Oracle lens (`olens_s3d_rl600` + AR + whitener,
block 44), RL NLA (block 42), J-lens (block 44, baseline), logit lens (baseline column only).
Motivated by the Neel meeting of 2026-10-22 and Suraj's exp 12/13 pilot (`mats-nla-workspace/experiments/13_new_rows`).

**Main question.** Does the Oracle lens have a *categorical* blind spot, and does its training objective explain it? The
lens inverts a reconstructor (AR) trained to map text to the *average* preceding activation, so it should cover only the
verbalisable part of an activation. Count-like and state-like text-buffer structure should therefore be invisible to it,
while the NLA (trained to reconstruct the exact activation) reads them. Symmetric hypothesis: each reader is blind
where its objective does not point. For the NLA, that is the model's upcoming decision (W8).

**What the pilot already shows (PILOT, not confirmatory).** Length-matched cells: table column (NLA 1.00 / Oracle 0.67 /
J-lens 0.64) and inside a parenthesis (0.98 / 0.76 / 0.47). "Sentences into paragraph" and "line in function body"
(0.99) are length-confounded and are not evidence. Line position did not replicate on fresh items (0.51). Nothing below
reuses pilot items for a confirmatory test.

## Shared rules

- **Items.** Authored and frozen (hashed manifest) before any activation is captured. Record shape follows Suraj's
  `feature_spec.py` / `items_build.py`: `{id, feature, class, domain, split, cluster, value, ids, text, meta}`.
- **Length matching (required for every binary row).** The two values' token-length distributions match: KS p > 0.2 and
  |mean difference| ≤ 1 token, checked and recorded before capture. Achieved by padding with an unrelated preamble.
  A row that fails is rebuilt before capture, never after.
- **Row class** (count-like / state-like / semantic / answer-type) is assigned in the manifest before capture, from the
  definitions below, and never changed.
  - count-like: which column, which line, nesting depth, items so far;
  - state-like: inside brackets, a string, a math environment or a code block;
  - semantic: language, topic, tense, sentiment;
  - answer-type: W8 only.
- **Size.** ≥ 120 items per binary row (60 per value), ≥ 12 template clusters, a 50/50 dev/test split by cluster. All
  rules are evaluated on test.
- **Asked score.** Prompted paired log-odds between two frozen phrasings per row (`paired_logodds_templates` in Suraj's
  `mats.readers`), averaged over ≥ 2 phrasing pairs; AUROC with template-clustered bootstrap (2,000).
- **Gates, per reader × row:**
  - (a) probe ceiling: logistic probe, cross-validated grouped by cluster, ≥ 0.85, otherwise the row is NOT DECODABLE
    (reported, excluded);
  - (b) mismatched control: the same scoring with each activation replaced by a matched donor (same domain, template
    family and length bin, opposite value) must give AUROC ≤ 0.60, otherwise that reader × row is NOT EVALUABLE.
- **Seal.** Scores are written and hashed before the label join (`common/stats.py` conventions). Wilson 95% CIs for
  rates.
- **Logging.** Every run goes to `results/g_agreement/log.md` and `compute.jsonl`. Large artefacts go to `cache/`.
  Results go to `results/g_agreement/blindspot/`. W1 and W5 run on our pods. The W-core chat vendors only Suraj's reader wrappers, capture code and
  item builder (`src/mats`), at a pinned commit, and skips his Modal drivers.

---

## §70 W1. Expanded, length-matched concept table

**Owner:** W-core chat (new; run for Guiv). **Cap:** 2.0 GPU-h. **Target:** Sunday 18:00.

- **Rows.** 30–40 binary rows across prose, Python, LaTeX, JSON/markdown tables and markdown lists, with ≥ 8
  count-like, ≥ 8 state-like and ≥ 8 semantic rows.
- **Replication rows.** Fresh items (new templates) for table column and inside a parenthesis.
- **Ordinal sub-rows.** For table column and nesting depth, 1–8 levels, length-matched across levels (≥ 30 items per
  level).
- **Arms, per row:** asked AUROC for the Oracle lens, NLA and J-lens (logit lens as an extra column); probe ceiling;
  mismatched gate.
- **Unasked recall.** 2 free readouts per item per reader (frozen decoding). A blinded judge marks whether the readout
  states the row's value. Report the rate per class.
- **Primary rule (CONFIRMED / PARTIAL / NOT MET):** among evaluable count- and state-like rows,
  - (i) Oracle lens asked AUROC ≤ probe − 0.15 on ≥ 75% of rows;
  - (ii) on those same rows, NLA within 0.10 of the probe on ≥ 75%;
  - (iii) on semantic rows, Oracle lens within 0.10 of the probe on ≥ 75%.

  All three → CONFIRMED (categorical blind spot). (i) and (iii) without (ii) → PARTIAL (Oracle blind spot, NLA no
  better). Otherwise NOT MET.
- **Secondary:**
  - the two replication rows, each reported against the pilot;
  - ordinal sub-rows: Spearman ρ between level and NLA log-odds ≥ 0.6 → "counts", otherwise "flags a state";
  - unasked recall by class (descriptive);
  - J-lens and logit lens (descriptive).

## §71 W2. Does the reconstructor fail on the same rows?

**Owner:** W-mechanism chat (new). **Cap:** 0.3 GPU-h. **Depends on:** W1 items and probe directions. Same code as §80.

- For each W1 row: 20 frozen texts stating each value ("inside a parenthesis" / "outside any parenthesis", etc., 2
  phrasings × 10 contexts). Run the AR on them.
- **Fidelity** = (mean projection of AR outputs on the row's probe direction, value A − value B) ÷ (real class-mean
  gap on the same direction). Bootstrap over texts.
- **Rule:** across evaluable rows, Spearman ρ(fidelity, Oracle lens asked AUROC) ≥ 0.5 with a CI lower bound > 0 →
  CONFIRMED. Also report median fidelity by class; the prediction is count/state < 0.25, semantic > 0.5 (descriptive).

## §72 W3. Is the blind-spot information left in the residual?

**Owner:** W-mechanism chat. **Cap:** 0.3 GPU-h. **Depends on:** W1 activations.

- r = h − AR(OL(h)), where OL(h) is the Oracle lens's greedy readout of h, and AR maps it back to activation space at
  block 44. Fit the same grouped-CV probe on r as on h, per row.
- **Rule:** blind-spot rows (those meeting W1 (i)) keep ≥ 0.9× their probe AUROC on r, *and* semantic rows drop by
  ≥ 0.15 on r, each on ≥ 70% of rows → CONFIRMED.
- **Secondary:** the same with the NLA's own decoder residual (h − Dec(NLA(h))) at block 42. The prediction is that
  both classes drop (descriptive).

## §73 W4. Causal swap

**Owner:** W-mechanism chat; P3 reviews the swap code before launch. **Cap:** 0.5 GPU-h. **Depends on:** W1, W3.

- **Pairs.** For each blind-spot row and each semantic row: 40 test pairs (i, j) with opposite values, same domain,
  template family and length bin.
- **Swap.** h′ = AR(OL(hᵢ)) + [hⱼ − AR(OL(hⱼ))]. Rescale h′ to ‖hᵢ‖.
- **Readout.** Run the NLA asked scoring on h′.
- **Controls:**
  - h′ with j = i (should follow i);
  - h′ with the residual from a random same-domain item of unknown value (should be ≈ 0.5 relative to j);
  - h′ built only from AR(OL(hᵢ)), with no residual (should be ≈ chance on blind-spot rows).
- **Rule:** blind-spot rows: NLA answers follow donor j (AUROC of the score against j's value ≥ 0.7, CI > 0.5);
  semantic rows: answers follow recipient i (AUROC against i's value ≥ 0.7). Both → CONFIRMED.
- **Site.** If the AR can be applied at block 42 (Camila to confirm), run the swap at 42, where the NLA is native.
  Otherwise build h′ at 44, read the NLA off its native layer, and label the result OFF-NATIVE.

## §74 W5. Layer sweep

**Owner:** W-core chat. **Cap:** 0.5 GPU-h. **Depends on:** W1 items.

- The Oracle lens at blocks 20, 28, 36, 44, 52 and 60 (its trained grid), on the W1 test split, with a probe at each
  layer.
- **Rule:** each blind-spot row has Oracle AUROC < 0.75 at ≥ 5 of 6 layers, on ≥ 75% of blind-spot rows, while the
  probe stays ≥ 0.85 → CONFIRMED (the blind spot comes from the method, not the layer).

## §75 W6. Can the Oracle lens be made to report it? (= §63 U2 on W1 rows)

**Owner:** inverter. **Cap:** 0.2 GPU-h. **Depends on:** W1.

- For each of the two replication rows and 2 further W1 blind-spot rows: add α · d to h, where d is the probe direction
  scaled to the class-mean gap. Use α ∈ {0, 1, 2, 4, 8, 16}, on 40 items of value B pushed toward A. Asked scoring by
  both readers; free readout for coherence.
- **Rule:** "unrepresentable" if no α ≤ 16 brings the Oracle lens's P(A) above its value-A baseline median, while the
  readout stays coherent (judge), and the NLA is past its median at α ≤ 2. "Weak" if the Oracle crosses at some α.
  Reported per row.

## §76 W7. Does the model use what the Oracle lens can't see?

**Owner:** lens chat (after §79). **Cap:** 0.3 GPU-h. **Depends on:** W1 probe directions.

- Steer at block 44 along the probe direction for inside a parenthesis and for table column (±; 3 doses up to the
  largest dose that keeps perplexity on unrelated text within 10%). Use 60 items per row. Compare with 5 random
  directions of the same norm.
- **Outcome.** Change in log P(")") at parenthesis items, and in log P("|") or the next column's header token at table
  items.
- **Rule:** steering − random > 0 with a cluster-bootstrap CI excluding 0, in the predicted direction, for each row.
  Both rows → CONFIRMED (three-way dissociation together with W1: used by the model, read by the NLA, missed by the
  Oracle lens).

## §77 W8. The NLA's own blind spot: upcoming decisions

**Owner:** remainder. **Cap:** 0.5 GPU-h. **Depends on:** nothing new; reuses frozen banks.

- **Four answer-type rows**, at the last prompt position before the answer:
  - (1) forced-choice answer on the hard third of the yes/no bank (yes vs no);
  - (2) answer margin (top vs bottom tercile of the model's own log-odds);
  - (3) planned refusal vs compliance on the existing audit prompts that have both outcomes;
  - (4) silent wrong answer vs right answer on the puzzle set.
- Rows are length-matched where possible. A row that cannot be matched is reported with length as a covariate, and
  marked.
- **Scoring.** The same asked scoring, probe ceiling and mismatched gate. The Oracle lens is read at 44 and 52; the
  NLA at 42.
- **Rule:** NLA ≤ Oracle lens (better of 44/52) − 0.10 on ≥ 3 of 4 evaluable rows → CONFIRMED ("each reader is blind
  where its objective doesn't point").

## §78 W9. Qualitative pass (optional)

**Owner:** any chat with API budget. **Cap:** $10 API, 0 GPU-h.

- Paired free readouts (NLA vs Oracle lens) on the same W1 activations, and the §61 pairs.
- A blinded LLM lists atomic claims. Claims are clustered (frozen prompt) into the types that only the NLA states,
  only the Oracle lens states, or both state.
- Descriptive only. The prediction is that NLA-only claims are mostly pending structure rather than topic.

---

# Discovery screens (§79–§84): find blind spots without choosing the concepts

W1 tests concepts we already thought of. The screens let the data name the categories. The best candidates from the
screens are then confirmed on fresh, length-matched items (§84).

## §79 S1. Probe-gap screen over 100+ scripted features

**Owner:** lens chat (freed by the §64 cut). **Cap:** 1.5 GPU-h. **Target:** features frozen Friday 20:00; ranking
frozen Sunday 18:00.

- **Corpus.** 2,400 documents, 600 each of prose, Python, LaTeX and tables/markdown, from pinned public datasets (HF
  revision recorded) and our frozen banks. The manifest is hashed before capture.
- **Features.** ≥ 100 binary features computed by deterministic scripts from the text up to the read position.
  - Examples: bracket depth ≥ 1 or ≥ 2; inside a string, a math environment or a code block; table column index; line
    index; indentation level; items so far in a list; position in the sentence; quote state; part of speech of the
    current token; tense of the clause; numeric magnitude; language; register; capitalisation.
  - `features.py` and its unit tests are frozen before capture, and each feature carries a class label (count-like /
    state-like / semantic) assigned there.
- **Sampling.** Per feature: 150 positive and 150 negative positions, matched on domain and absolute-position bin (5
  bins), with ≤ 3 positions per document. A feature with fewer than 100 per side is dropped, and the drop is reported.
- **Arms.**
  - Grouped-CV probe (grouped by document) at blocks 42 and 44.
  - Oracle lens and NLA asked scoring, with one phrasing pair per feature, generated from the feature's definition by
    a fixed template and frozen with `features.py`.
  - The mismatched gate (§70 rule) for every feature.
- **Outcome.** gap = probe AUROC − reader asked AUROC, per reader × feature, among features with probe ≥ 0.85 that
  pass the gate.
- **Primary rules.**
  - (H1) The Oracle lens's mean gap on count- and state-like features exceeds its mean gap on semantic features by
    ≥ 0.10 (feature-level bootstrap CI > 0).
  - (H2) On count- and state-like features, the NLA's mean gap is smaller than the Oracle lens's by ≥ 0.10 (paired
    bootstrap CI > 0).
- **Selection for §84.** The top 10 features by Oracle gap, excluding those already in W1. The list is committed
  before any §84 item is built.

## §80 S2. Reconstructor contrastive screen (no reader generation)

**Owner:** W-mechanism chat. **Cap:** 0.3 GPU-h. **Depends on:** §79 features and block-44 probe directions.

- **Texts.** For every §79 feature and W1 row: 20 frozen texts stating each value (2 phrasings × 10 contexts),
  generated by template from the feature definition.
- **Fidelity.** Run the AR on the texts and compute fidelity as in §71.
- **Rule.** Across all evaluable features: Spearman ρ(AR fidelity, Oracle asked AUROC) ≥ 0.4 and ρ(AR fidelity, Oracle
  gap) ≤ −0.4, each with a 95% CI excluding 0 → CONFIRMED (the reconstructor predicts the Oracle lens's blind spots at
  scale).

## §81 S3. Residual SAE (optional, if GPU remains after §79/§80)

**Owner:** W-mechanism chat. **Cap:** 1.5 GPU-h.

- **SAE.** Train a top-k SAE (k = 32, 16k latents) on block-44 activations, using 5M tokens of the §79 corpus.
- **Residuals.** On 20k positions, compute r = h − AR(OL(h)) with greedy Oracle readouts.
- **Residual share.** Per latent: mean activation on r ÷ mean activation on h. Report the latents with share ≥ 0.8 that
  fire on ≥ 0.1% of positions, with their top-activating contexts and LLM labels (frozen prompt).
- **Status.** Descriptive. Up to 5 candidates that can be scripted go to §84.

## §82 S4. Steer first, read second

**Owner:** Neel5 (before §62A). **Cap:** 1.0 GPU-h, $15 judge.

- **Directions.** 200 random directions (whitened Gaussian, SA-R norm and dose rule) plus the §79 probe directions.
  Inject at block 42 as in SA-R. The NLA reads at 42 and the Oracle lens at 44.
- **Behavioural effect.** Mean next-token KL over the following 20 positions, on 50 frozen prompts.
- **Detection, per reader.** On 20 prompts, a blinded judge says whether readout B differs in content from the
  unsteered readout A. B is either the steered readout or an unsteered resample. Detection = P(yes | steered) −
  P(yes | resample).
- **Primary rule.** Among the top-quartile directions by behavioural effect, the share undetected (detection CI includes
  0) is higher for the Oracle lens than the NLA by ≥ 0.15 (paired bootstrap over directions).
- **Secondary (descriptive).** What the high-effect, undetected directions change in behaviour (the most-promoted
  tokens).

## §83 S5. Error-driven (no GPU)

**Owner:** remainder (alongside W8). **Cap:** 0 GPU-h.

- **Pool.** Existing readouts judged correct or wrong: SA-R hits vs misses, §61 founded vs unfounded, and §65B senses
  once available. The pool is frozen before analysis.
- **Analysis.** At each read position, compute the §79 scripted features and the domain. Fit a document-clustered
  logistic regression of wrongness on the features, per reader.
- **Status.** Descriptive. The prediction is that count- and state-like features predict Oracle errors more than NLA
  errors.

## §84 W1b. Confirm the screen candidates

**Owner:** W-core chat. **Cap:** 1.0 GPU-h. **Target:** Monday.

- **Items.** Fresh, length-matched items (§70 protocol) for the ≤ 10 §79 candidates and the ≤ 5 §81 candidates.
- **Rule.** A candidate confirms if Oracle ≤ probe − 0.15 and the NLA is within 0.10 of the probe. If ≥ 70% of the §79
  candidates confirm → CONFIRMED ("the screen finds real blind spots").

---

## Priority and fallback

1. **Order if time runs short:** W1, §79 and §80 (in parallel) → W4 → §84 → W3 → W8 → W5 → §82 → W6/W7 → §81 →
   §83/W9. Compute stops Tuesday night.
2. **If W1 is NOT MET,** the paper falls back to "recovers more than it reports" on the two clean cells, plus the false
   alarms, sensitivity results and the per-claim detector. W2–W4 are still run on the two clean rows as a case study,
   labelled EXPLORATORY.
3. **Relation to earlier briefs:**
   - §63's gate is folded into W1 (length-matched items).
   - §63 U2 is W6.
   - §64 is cut, and §65A is deferred to after the sprint (dated notes in BRIEF_V.md).

## Deviations

**2026-10-23 06:15 CEST (Guiv), before any W or S number:** W1 and W5 move from Suraj to a new W-core chat run for
Guiv on our pods. W2–W4 move from P3 to a new W-mechanism chat (P3 stays on §66 and reviews the W4 code). Discovery
screens §79–§84 were added. No rule in §70–§78 changed.

**2026-10-23 08:15 CEST (Guiv), budget only, before any W6 number:** W6 (§75) gets a cumulative judge cap of **$3**
for the coherence judge. That covers 4 rows × 6 doses × 40 items, scored on the Oracle lens's free readouts and the
NLA's, 1 readout each, using the shared judge in BRIEF_V. A row with judge output MISSING or over budget is reported
MISSING. The W6 0.2 GPU-h cap covers science only: W6 runs on the shared staged pod or volume the integrator assigns,
and the cold weight download is not charged to it. Rules unchanged.

**2026-10-23 08:20 CEST (Guiv), operational definitions for §82, before any §82 number:**
1. **Random directions.** "Whitened Gaussian" means covariance-matched. Estimate Σ at block 42 from ≥ 10,000 residual
   vectors at frozen natural-text positions: the §79 corpus if it is frozen by launch, otherwise Neel5's existing SA-R
   no-edit captures; record which set was used. Shrink as Σ + 0.1·(tr Σ / d)·I, the same ridge as the whitener. Draw
   z ~ N(0, I) with seed 20261023, set d = Σ^½ z, and scale to the SA-R norm and dose rule.
2. **Readout sampling.** Every readout in the §82 detection test (A, steered B and resample B′) is sampled with the
   same settings: temperature 0.7, top-p 0.95, the same max tokens as SA-R, and an independent fixed seed per readout.
   Greedy decoding is not used, because it would make the resample baseline trivially zero. The judge compares A with B,
   and A with B′.

