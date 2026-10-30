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


**2026-10-23 dated operational amendment (lens), after attempt1 smoke timing NO_FIT:** the input/features/phrasing/sample freeze and every scientific endpoint/rule remain unchanged. Attempt1 is INCOMPLETE, no full states or label joins,607s science booked once;4793s remain. Prepare a fresh one-shot receipt with pinned optional optimized kernels and an actual import/dispatch guard (no silent reference fallback), parallel exact SHA256 staging, and unchanged vendored scoring. Fresh custody itself is conservatively capped at4793s, with630s science/pull buffer. No in-chain automatic retries or clock resets. This note is after timing data and before any full reader/probe outcome; no outcome-based feature selection. Details/hash pins: `results/g_agreement/blindspot/s79/RUNTIME_AMENDMENT.md`, `KERNEL_PREPARATION.json`, `KERNEL_WHEEL_MANIFEST.json`. Old source9cc7e871 and its smoke diagnostics remain archived. GPU compatibility/speed of the new stack await the new registered smoke; no claimed kernel speedup.


**2026-10-23 12:16 CEST, §79 setup-only warm-up amendment (lens, Guiv instruction):** for the next published package only; do not change integrator-operated live source. Before the first-science marker and before the timed all-feature smoke, perform two fixed synthetic, unscored warm-up passes through target capture42/44 and Oracle/NLA active and adapter-disabled paths. Discard all reader outputs; no outcome rows, labels, frozen corpus items or feature queries enter warm-up. Preserve RNG state and synchronize completion. Warm-up is setup, inside the original1,500s creation-relative setup gate and outside7,200s science; it does not reset or relax the smoke1.5×gate or any scientific rule. Seal path/timing metadata, with first science starting only afterward. Integrator operates the current pod and any conditional relaunch if it misses setup; this preparation does not authorize a concurrent allocation, further retry or cap reset. Immutable features/corpus/sampling unchanged.

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

**2026-10-23 08:50 CEST (Guiv), gaps found by owners during CPU preparation, before any number for these sections:**
1. **§73 W4 aggregation.** CONFIRMED if the per-row rule holds on ≥ 70% of tested blind-spot rows *and* ≥ 70% of tested
   semantic rows (the same fraction as §72). Per-row results are always reported. Further requirements:
   - `reconstructed` must be AR(OL(h)): the reconstructor applied to the Oracle lens's frozen greedy readout of h, in
     raw block-44 activation units (not centred and not whitened), the same space as h;
   - before launch, a unit check confirms that h − AR(OL(h)) has the same units as h.
2. **§75 W6 aggregation and coherence.**
   - P(A) per item = sigmoid of the asked score (mean paired log-odds over phrasing pairs). The dose statistic is the
     median over the 40 items.
   - Baseline = median P(A) over value-A test items at α = 0, for the same reader.
   - A dose is *coherent* if ≥ 80% of its free readouts are judged coherent (MISSING counts as not coherent).
   - A reader *crosses* at α if that dose is coherent and its median ≥ the baseline.
   - Verdicts:
     - "Unrepresentable": the Oracle lens crosses at no coherent α ≤ 16, it is coherent at some α ≥ 4, and the NLA
       crosses at some α ≤ 2.
     - "Weak": the Oracle lens crosses at some coherent α.
     - Otherwise NOT EVALUABLE, with the reason.
3. **§77 W8 size.** If the measured smoke forecast for all frozen IDs exceeds the 0.5 GPU-h science cap with a 1.5×
   margin, use a seeded hash subsample per row. Take the largest n that fits, always ≥ 120 items and ≥ 12 clusters, and
   choose it from timing alone before any score is computed.
4. **§82 S4 fit to cap.** The registered design projects to roughly 70× the 1.0 GPU-h cap, so:
   - (a) The behavioural screen runs on all 200 random directions (teacher-forced next-token KL over the prompt's own
     following 20 tokens, 50 prompts). The ranking is sealed before any reader readout.
   - (b) Reader detection runs only on the top quartile by behavioural effect (50 directions), which is the registered
     primary population.
   - (c) Detection uses the first k of the 20 frozen detection prompts, in per-domain order, with k ∈ {20, 12, 8}, and
     max_new_tokens 128. Choose the largest k whose smoke-measured forecast fits the cap with a 1.5× margin, from
     timing alone, before any readout is scored.
   - (d) The §79 probe directions are added, under the same protocol, only if budget remains after the random set.
   - (e) Covariance comes from block-42 residuals that Neel5 captures at launch on the frozen §79 corpus *text*
     (manifest frozen Friday 20:00): the first ≥ 10,000 positions, in manifest order, from ≤ 3 positions per document.
     The SA-R archive has only 20 distinct positions and is not used.
   - (f) The primary rule is unchanged. With small k the detection CIs are wide; this is reported as a limitation.


**2026-10-23 08:55 CEST (Guiv), arithmetic correction to the 08:50 note 4(e), before any §82 number:** 2,400 documents × 3 positions gives only 7,200 vectors. §82 covariance therefore uses ≤ 5 positions per document, spread evenly by token index within each document, from the frozen §79 corpus, giving ≥ 10,000 vectors in manifest order. Nothing else changes.

**2026-10-23 09:05 CEST (Guiv), owners, budget and timing only, before any number for these sections:**
1. W7 (§76) moves from the lens chat to the W-mechanism chat. The rule and the cap are unchanged.
2. §65B (BRIEF_V) gets one rerun on the shared weights volume, with a new science-only cap of 0.5 GPU-h. Staging is
   outside the cap, and the judge cap is unchanged. The registration, frozen items, donors and senses are unchanged.
   The earlier attempts' MISSING records stay as they are, and the rerun is labelled `R3`. This restores §66's
   held-out test set.
3. Timing: the §79 corpus manifest is frozen by 12:00 and `features.py` by 15:00 (previously 20:00). §82 may launch as
   soon as the corpus manifest is frozen.
4. Owners may make operational choices that the brief leaves open, without waiting for Guiv, provided the choice is
   recorded in HANDOFF before any data and changes no registered rule, threshold or population. Anything that
   changes a rule still goes to Guiv first.

**2026-10-23 09:20 CEST (Guiv), W8 (§77) row availability, before any W8 score:** only two of the four answer-type
rows can meet the registered size rule.
- Row 3 (refusal): fewer than 12 clusters.
- Row 4 (puzzle silent wrong answer): the ReaderBench candidate has 4 frames and 49 parseable correct answers. The
  older X3 arrow-puzzle set (`dataset/items_x3_selected.json`, 297 errors / 103 controls) uses a single template
  (`pz-t1`), so it also fails the ≥ 12-cluster rule.

Both rows are NOT EVALUABLE, and no relaxed minimum is used. The W8 rule is restated for the rows that exist:
**CONFIRMED if NLA ≤ Oracle lens (better of 44/52) − 0.10 on both rows 1 and 2, with both evaluable.** One row → PARTIAL;
neither → NOT MET. The write-up states that W8 rests on two rows, both from the TH-3 yes/no bank.

**2026-10-23 09:25 CEST (Guiv), W8 donor eligibility, before any W8 score:** items with no opposite-class donor in the
same domain, template family and 64-token length bin are excluded before the timing-only subsample (84 of 7,066 in
row 1, 572 of 14,133 in row 2). The exclusion uses metadata only. Every excluded ID, the resulting coverage and the
class balance before and after are reported. The size minima (≥ 120 items, ≥ 12 clusters) apply after exclusion.

**2026-10-23 11:00 CEST (Guiv), §82 dose rule, before any §82 ranking, readout or judge output (stage 1 stopped at its
budget gate with no outputs; 492.6 science seconds booked):** per-direction SA-R norm calibration is projected at
7.5 h, about 8× the remaining budget. It is replaced by **one fixed norm for every direction:** the median of the
final dose amplitudes SA-R actually applied to its 16 concept directions (from `SAR_DESIGN.json`), computed in the
same whitened/raw convention SA-R used. There is no per-direction calibration. The behaviour screen, the ranking
seal, the top-quartile detection, the k ladder and the primary rule are unchanged. The remaining science budget is
3,600 − 492.6 s. This is a dose-rule change, and the write-up states it.

**2026-10-23 11:05 CEST (Guiv), correction to the 11:00 note, before any §82 output:** "16 concept directions" was my error. The fixed norm is the median of **all 20** final dose amplitudes in the verified SA-R archive (20 concepts in `SAR_DESIGN.json`). Nothing else changes.

**2026-10-23 11:15 CEST (Guiv), §79 budget only, before any §79 score:** attempt 2 stopped at its timing gate (conservative projection 5,121 s vs 4,793 s remaining; smoke only, no scores). §79 gets one more attempt with a science cap of **7,200 s (2.0 GPU-h)**, staging outside it. It uses the fast-kernel environment if the integrator has verified it by launch, otherwise the current one. The features, corpus, sampling, gates and rules are unchanged.

---

## §85 W8b. Does the NLA's inverted confidence reading replicate on fresh items? (pre-registered 2026-10-23 11:35 CEST, after W8 attempt 3 and before any W8b item is selected)

**Owner:** remainder. **Cap:** 0.4 GPU-h science; 1,500 s setup allowance outside it; no judge. **Target:** Friday.

**Why.** In W8 (§77) row 2 the NLA's asked score for "confident vs unsure" gave AUROC 0.18 on the model's own
high- vs low-margin items, and 0.81 with opposite-value donors. A code audit (`ea4d0f27`) found the orientation
consistent, so the reading is genuinely inverted. That result is exploratory, because the row failed a gate and the
opposite-donor gate penalises readers that read *backwards*. §85 tests the inversion prospectively on fresh items with
a gate that doesn't have that flaw.

**Items.**
- Pool: TH-3 row-2-eligible items (top vs bottom tercile of |prompt-only margin A|), with the same exclusions and the
  same donor-eligibility rule as W8 (09:25 note).
- Every item used in W8 attempt 3, as recipient or donor, is excluded.
- A fresh seeded hash subsample: 600 items (300 per class), ≥ 30 clusters. If the timing smoke says that doesn't fit,
  take the largest n that fits, ≥ 300 items and ≥ 30 clusters, chosen from timing alone.
- The selected IDs and their hash are frozen before capture.

**Readers and scoring.** Unchanged from W8 attempt 3:
- the same source, frozen phrasing pairs, scorer and aggregation;
- the NLA at block 42 and the Oracle lens at block 44 (primary) and block 52 (secondary).

**Arms.**
1. **TRUE:** each item's own activation.
2. **RANDOM-DONOR (the gate):** each item's activation replaced by a donor from the same domain, template family and
   length bin, drawn by hash *regardless of value*. A reader whose score depends only on the activation gives AUROC
   ≈ 0.5 against the recipient's label here, whichever direction it reads.
3. **OPPOSITE-DONOR:** as in W8. Descriptive only.
4. **Probe ceiling:** logistic probe, grouped CV by cluster, at blocks 42 and 44.

**Gates, per reader.** Probe AUROC at that reader's block ≥ 0.85, and RANDOM-DONOR AUROC within [0.40, 0.60].
Otherwise that reader is NOT EVALUABLE.

**Primary rules.**
- **H1 (inversion replicates):** the NLA's signed TRUE AUROC < 0.5, with the cluster-bootstrap 95% CI upper bound
  < 0.45 → CONFIRMED. Otherwise NOT MET.
- **H2 (the readers point in opposite directions):** Oracle lens (block 44) signed TRUE AUROC − NLA signed TRUE AUROC
  ≥ 0.20, with the paired cluster-bootstrap CI excluding 0 → CONFIRMED.

**Secondary (descriptive).**
- |AUROC − 0.5| per reader, i.e. information regardless of direction.
- Each phrasing pair reported separately, to check whether the inversion depends on the wording.
- The Oracle lens at block 52.
- OPPOSITE-DONOR scores.
- A length-adjusted AUROC.

**No sign is ever flipped.** Scores are sealed before the label join. Results go to `results/g_agreement/blindspot/w8b/`.


## Dated post-capture deviation — W1 §70, 2026-10-23

The integrator reported approximately **214 s of science above the registered 7,200 s W1 cap** (HANDOFF 09:52Z). The assignment used a fixed creation + 8,100 s deadline (science plus staging), rather than first science + 7,200 s. This is a compute-cap deviation, not a retrospective budget increase. Per Guiv’s instruction, W-core retained all six verified asked-score seals and ran the original frozen §70 analysis once, unchanged. The source hashes were checked against `b15b95fc` before the label join and again after analysis, before this dated note was appended. Free-response recall is **PARTIAL**: priority target/NLA complete, remainder_a target partial and unsealed, remaining free phases not run; no blinded recall rate is inferred. No decision rule, item, score, source implementation or fit was changed. Full evidence: `results/g_agreement/blindspot/w1/{COMPUTE_DEVIATION.json,prejoin_verification.json,post_analysis_checks.json,free_response_status.json}`.

**2026-10-23 12:35 CEST (Guiv), W3 (§72) budget only, before any W3 output:** greedy Oracle readouts for every W1 item in the 16 rule-(i) rows and 9 semantic rows are forecast at over one hour, against the 0.3 GPU-h cap. The W3 science cap is raised to 1.5 x the smoke-measured forecast, at most **2.0 GPU-h**, with a 1,500 s setup allowance outside it. The rows, items, decoding settings, probes and rule are unchanged; no items are dropped. W4 follows on the same pod under its own 0.5 GPU-h cap. If the forecast exceeds 2.0 GPU-h, report it to Guiv before launch; do not scope down silently.

**2026-10-23 12:45 CEST (Guiv), W7 (§76) budget and environment only, before any W7 output (two attempts stopped at the first gate with no dose seal and no scores):** W7 gets one more attempt with a science cap of 1.5 x the smoke-measured forecast, at most **1.0 GPU-h**, and a 900 s setup allowance outside it. It runs on the **reference** environment `/weights/venv`, since its steered calibration measured slower on `venv-kernels` (2.65 s vs 1.88 s per step), with a warm-up before the gate. The doses, perplexity rule, items, random directions and decision rule are unchanged. If the forecast exceeds 1.0 GPU-h, report it to Guiv before launch.

**2026-10-23 12:55 CEST (Guiv), W5 (§74) completion, budget only, before any W5 score is sealed or inspected:** W5 captured and sealed activations at all six blocks, but Oracle scoring stopped part-way with no score seal; the partial rows stay unsealed and unused. W5 gets one **scoring-only completion run** from the sealed captures, with no recapture. It scores all rows afresh (the scoring is deterministic) with a science cap of 1.5 x the smoke forecast, at most 1.0 GPU-h, and setup outside it. The science deadline is measured from the first science step, not from pod creation, which fixes the overrun seen in W1 and W5. The layers, items, probes and rule are unchanged. The earlier overrun of about 289-422 s is disclosed.

**2026-10-23 14:05 CEST (Guiv), budget and operations only, before any output of these runs:**
1. **W7 (§76):** the forecast is taken as F = 1,313 s, the measured reference-environment calibration plus scoring from attempt `v6e57330l9a64u`. Allocation is min(1.5F + 180, 3,600) s, about 2,150 s, so that the code's 180 s retrieval reserve sits on top of 1.5F. No code change; the rule is unchanged.
2. **W6 (§75):** one fresh attempt. The previous attempt hit its setup deadline with 0 readouts while integrator overlay and check pods were competing for the volume. Setup allowance is 1,500 s, outside the 720 s science cap, and no other pod may be in setup on the volume at the same time.
3. **Runs that load the official reconstructor** (W3/W4, §66, S2, W1b): the setup allowance rises to **2,400 s**, outside science, because the reconstructor loader alone measured 991.7 s on `venv-kernels`. Science caps are unchanged.

**2026-10-23 14:12 CEST (Guiv), W6 (§75) budget only, before any W6 output:** the fresh-attempt receipt forecasts about 700 s of science (point estimate) against a 720 s cap, while its own gate requires elapsed + 1.5 x remaining + 120 s <= cap, which would almost certainly stop the run early. The W6 science cap is raised to **1,200 s** (about 1.5 x 700 + 120 s), with setup unchanged at 1,500 s outside it and the judge cap unchanged at $3. Rows, doses, items, rules and the gate formula are unchanged.

**2026-10-23 14:15 CEST (Guiv), W7 (§76) allocation, budget only, before any W7 output:** to give the code's own 1.5x gate headroom on its one remaining attempt, the allocation is min(1.5F + 360, 3,600) s, about 2,330 s with F = 1,313 s (supersedes the 14:05 figure of about 2,150 s). This is within the 1.0 GPU-h ceiling. Everything else is unchanged.

**2026-10-23 15:30 CEST (Guiv), budget only, before any output of these runs:**
1. **S2 (§80):** the reconstructor load inside the science window (about 1,024 s) exceeds the usable science of the 0.3 GPU-h cap. The S2 fidelity cap becomes min(1.5F + 360, 3,600) s, at most **1.0 GPU-h**, where F is the measured load plus scoring. This is one fresh attempt. The only code change allowed is the `fidelity` value in `CAP_HOURS` (and the matching forecast branch); P3 reviews it. The texts, rows and rule are unchanged. W2 (§71) uses S2's outputs.
2. **W6 (§75):** one **final** attempt with a science cap of **1,800 s**. The last attempt missed its own gate by 8.4 s (projected 1,208.4 s against 1,200 s). Setup stays at 1,500 s in a quiet window and the judge cap at $3; everything else is unchanged. If it fails again, W6 closes INCOMPLETE.

---

## §86 W10. Distal operating mode under identical local text (pre-registered 2026-10-23 15:40 CEST, before any item is built)

**Owner:** W-core builds the items and runs the analysis; the integrator operates the pod. **Cap:** min(1.5F + 360, 3,600) s
of science (at most 1.0 GPU-h), with a 1,500 s setup allowance outside it (three models); judge ≤ $3. One attempt, plus
one retry only after a pure infrastructure failure with no science. **Target:** Saturday.

**Hypothesis.** The Oracle lens inverts a reconstructor trained to map *text* to the average activation. Under
*identical* local text, the reconstructor's target is the same whatever an earlier instruction said, so the Oracle lens
should be blind to the model's current **operating mode** (the instruction it is following). The NLA (exact
reconstruction) and a linear probe should not be blind to it.

**Rows (frozen now).** There are 7 modes. Each instruction pair is token-length-matched exactly:
1. answer language (English / French);
2. register (formal / casual);
3. audience (a child / an expert);
4. output format (JSON / prose);
5. length (terse / detailed);
6. persona (pirate / neutral assistant);
7. topic constraint ("never mention animals" / no constraint).

Each mode is tested at 2 distances between the instruction and the read position: **near** (≈ 50 tokens of neutral
filler) and **far** (≥ 400 tokens). That gives 14 binary rows. Row class: `mode`.

**Carrier.**
- The prompt is: system or user instruction (mode value A or B), then neutral filler of fixed length, then
  "Copy the following passage exactly:" plus a passage.
- The assistant turn teacher-forces the start of the passage. The read position is a fixed token index inside it.
- **All tokens except the instruction span are identical across the two values** (a test checks this).
- Each passage appears once with each value, so labels are balanced within every cluster.

**Size.** 120 items per row (60 per value), from ≥ 12 passage clusters. Dev and test are split by cluster, and rules are
evaluated on test.

**Arms.**
- Asked paired log-odds for the Oracle lens (block 44), the NLA (block 42) and the J-lens (block 44), using W1's
  scorer with 2 frozen phrasing pairs per mode.
- Probe ceiling: grouped-CV logistic probe at blocks 42 and 44.
- **Random-donor gate:** each item's activation replaced by one from the same row and cluster, with the donor's value
  drawn by hash, regardless of its own value. Because labels are balanced within clusters, a reader that uses only the
  activation scores ≈ 0.5 here.

**Gates, per reader and row.**
- Probe ≥ 0.85.
- Random-donor AUROC within [0.40, 0.60].
- **Mode is active:** on 20 dev items per row, the model's own *free* continuation (greedy, 48 tokens, no teacher
  forcing) follows the instruction in ≥ 70% of items. A blinded judge decides, with a frozen prompt; language and JSON
  are checked by script. A row that fails is NOT EVALUABLE, because the model isn't using the mode.

**Primary rules.**
- **H1 (Oracle lens blind to mode):** the Oracle lens is ≤ probe − 0.25 on ≥ 75% of evaluable mode rows → CONFIRMED.
- **H2 (NLA reads more mode than the Oracle lens):** NLA − Oracle ≥ 0.10, with a paired cluster-bootstrap CI above 0,
  on ≥ 50% of evaluable mode rows → CONFIRMED.

**Secondary (descriptive).**
- Far-minus-near difference in the (probe − Oracle) gap.
- The J-lens.
- Each phrasing pair separately.
- **Surprisal rows:** 2 extra rows (prose and Python, from W1's frozen bank text), labelled top vs bottom tercile of
  the model's own surprisal of the current token, with the same arms and gates. Reported descriptively.

**Open dependency.** The reconstructor's text window (to ask Camila). If it sees the whole prefix, the prediction is
"averaged out" rather than "blind by construction". The rules are unchanged either way, and the write-up states which
applies.

**Science clock** starts at the first science step. Scores are sealed before the label join, and no sign is ever flipped.
Results go to `results/g_agreement/blindspot/w10/`.

**2026-10-23 16:35 CEST (Guiv), timing gates, operations only, before any output of the affected runs:** every forecast or timing gate in this brief, and §66 in BRIEF_V, uses **warmed units**. One unscored warm-up unit runs per code path, then 3 timed units; F is extrapolated from their median. A cold first call never enters the forecast. This applies to the W5 completion (now a fresh attempt, nothing having been scored), §66, S2, W6, W10 and §84. Caps and rules are otherwise unchanged.

**2026-10-24 00:45 CEST (Guiv), budget only, before any output of these runs:**
1. **W5 completion:** the cap is min(1.5F + 360, 3,600) s, with F from warmed units. This adds the same +360 s gate headroom as W7, S2, §66 and W10, and authorises W-core's receipt `4db34278`.
2. **S2 fresh attempt:** the 738.1 s of science charged to the attempt killed by the integrator's watchdog stays booked, but does **not** count against this attempt's admission. No output of that attempt was sealed or used. This attempt gets its own min(1.5F + 360, 3,600) s from first science. F is the warmed median-of-3 production-batch time, measured on the pod.

---

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
