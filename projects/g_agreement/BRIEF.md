# BRIEF — G1–G4: what interpretability readers agree on, and whether agreement is reliable

Pre-registered 2026-10-07 (before any state was captured). Owner: Guiv. Companion to
`DESIGN.md` (modules) and `INTERFACES.md` (formats). Deviations go under "Deviations" with a date;
the original text stays.

## Question
Do J-lens, NLA and Oracle lens (OLens) report the same facts from the same Qwen3.6-27B
block-42 state, does that agreement depend on the activation rather than on the prompt or a
shared default, and does agreement across methods buy more reliability than repeated samples
from one reader?

## Verify before running (R0; stop if one fails)
- V1 Layer convention: recomputed block-42 output on the 64 shipped NLA example texts matches
  the shipped vectors with median cosine ≥ 0.999 and mean relative L2 ≤ 0.05, and beats blocks 41
  and 43 on relative L2 (Suraj's values: 0.9999 / 0.026 vs 0.979 / 0.22 for the neighbours).
- V2 OLens positive control: the README example yields topical bullets (not CJK garbage) at
  layers 44 and 42; adapter verified live (PEFT reports non-zero LoRA deltas).
- V3 NLA positive control: 4 shipped activations produce `<explanation>` text related to their
  source passage; a shuffled vector produces unrelated text.
- V4 Recorded score: one regex family at L42 for NLA and OLens (default `typo_mt`: Suraj's
  single-layer values 0.73 and 0.76, n=100; `multihop_mt` 0.15 and 0.10 as the alternative),
  within the 95% CI of the recorded value. A result outside the CI is a setup failure, not a finding.
- V5 Site/contract: all three readers consume the identical fp32 vector from the same
  `states/*.pt` file; `pre_answer: true` for every state; J-lens layer 42 ∈ source_layers.
- V5b Off-grid check: OLens on the 8 dev states at layers 40, 42 and 44 (layer integer in the
  prompt matching the capture layer). If the 42 readouts are degenerate relative to 40/44 (coverage
  lower by ≥ 4/8), every OLens figure carries the off-grid caveat; 42 stays primary either way.
- V6 Caps: on the 8 dev states, ≥ 7/8 NLA and ≥ 7/8 OLens readouts finish (EOS) within 128
  new tokens and ≥ 7/8 target answers within 32. Otherwise raise the cap once, record it, freeze.
Not attempted in this session: Suraj's column-wrapping intervention. His repository (received
2026-10-07) has the recipe but not the direction, basis or bank (those are on his Modal volume);
re-deriving them is a separate ~1–2 GPU-hour experiment (manifest/SURAJ_REPO_NOTES.md).

## Fixed design
- 20 pairs, 4 families × (1 dev + 4 test) → 8 dev states, 32 test states. Dev states are for
  format/cap/rubric development only and never enter a test summary.
- Site: block-42 output, last prompt token (chat render, thinking off). One capture per state.
- Readers at their native settings (see DESIGN.md); verbalizer sampling T=1.0/top_p 0.95/top_k 64,
  seeded; cap 256 (readouts; raised from 128 after dev, see Deviations), 32 (target), 128 (prompt-only). Caps include emitted reasoning.
- Claim extraction: `dataset/rubric.md`, rule-based first; answer keys hidden from the extractor;
  any model-annotated labels are marked provisional; no human validation is claimed.
- Unit of inference: the base pair (16 test pairs; 4 for G4). Bootstrap over pairs, 2000 draws.
- Power, stated plainly: at n = 32 states a single accuracy is known to ±15–20 points; a paired
  method-vs-method difference is detectable only if ≥ 30–40 points; G4 (8 states) can rank
  nothing and is a feasibility pilot (cost per rule, abstention rates, whether three T = 1 samples
  of one reader disagree at all).
- Blinding: annotation sheets carry an opaque salted id, method and text only.

## Endpoints and decision rules (test set only)

G1 (primary endpoints):
- E1 Coverage per method = states with status ∈ {supports, contradicts} / 32.
- E2 Accuracy per method among covered states (vs answer key) with pair-bootstrap CI.
- E3 Pairwise agreement matrix: for each method pair, counts of (both assert same value /
  assert different values / at least one unclear) over 32 states. Two unclears ≠ agreement.
- E4 Target consistency: agreement of each method's asserted value with the target model's own
  answer, reported separately from E2.
- E3b Chance-corrected agreement: Cohen's κ per method pair with pair-bootstrap CI, beside E3
  (two readers at 60% accuracy on a binary task agree ≈ 52% of the time by chance).
- E3c Noise ceiling for J-lens coverage: candidate-in-top-10 rate on 20 random same-norm vectors
  and on the mean dev activation (`jlens_null`), reported beside E1 for J-lens.
Primary contrast (the reliability question): accuracy of the consensus-k rule (k = 2, k = 3
agreeing votes; abstentions, ties and all-abstain unresolved) minus the best single reader's
accuracy on the same covered states, paired pair-bootstrap over 16 pairs. Pre-committed minimum
effect: ≥ 20 percentage points with a CI excluding 0; anything smaller is "no evidence either
way" at this n. The support-count bucket table and leave-one-out consistency are secondary.
Descriptive decision labels (no ranking claims between readers): "agree on this family" if the
3-way all-assert-same rate ≥ 0.75 on its 8 test states and accuracy among those ≥ 0.75;
"disagreement" if any method pair has ≥ 3/8 contradictions; otherwise "mixed". Per-family
numbers are descriptive only (8 states cannot support a per-family claim).
Population: all 32 test states is primary (source-model errors kept); the target-correct subset
is reported alongside. A truncated readout (finish_reason = length) with a clear assertion
counts and is flagged; truncation rate per method appears in every caption.

G2: E5 entity recognition rate, E6 relation-correct rate, E7 complete-pair tracking rate
(both versions correct and the asserted value changes), per method on ownership+mapping test
pairs (8 pairs). Decision: relation tracking "present" for a method if E7 ≥ 5/8 pairs;
"keywords only" if E5 ≥ 0.75 but E7 ≤ 2/8. Expected by construction: a J-lens top-10 token list
has no binding, so J-lens relation status is `unbound`/`absent` for most states; this is a format
limitation pre-registered here, not a finding.

G3: E8 genuine accuracy, E9 shuffled accuracy scored against the recipient key, E10 shuffled
donor-tracking rate, E11 prompt-only accuracy (base model, prompt text only), E11b state-free
reader prior: each verbalizer run with the mean dev activation in place of the state, one call per
test item (32 per reader), each scored against that item's key — the readers' own default-guess rate. Each on 32
states with coverage.
Decision: "activation-dependent" for a method if E10 − E9 ≥ 0.25 (donor claims dominate) and
E8 − E9 ≥ 0.25. "Prompt-recoverable" if E11 ≥ E8 − 0.10 (high prompt-only recovery means task
recovery is not evidence of added interpretive value; it does not show the reader ignored the
activation). The shuffled arm is a cached-readout reassignment; it is never called an intervention.

G4 (feasibility pilot, 8 states): E12 accuracy-at-coverage curves for rules {any single reader,
cross-method 2-of-3, cross-method 3-of-3, within-NLA 2-of-3, 3-of-3, within-OLens 2-of-3,
3-of-3}; E13 compute per rule (generated tokens, wall-clock). Decision: report only whether
cross-method agreement is "no better than" (within 1 state) within-reader repetition at matched
coverage. Any apparent advantage needs fresh examples.

Consensus (B1-style, 32 states): accuracy by support count 1/2/3 with ties and all-abstain
unresolved; leave-one-out consistency kept separate from accuracy.

## Kill criteria
- K1 Any V-check fails → repair before new interpretation; no test collection.
- K2 Target model answers < 24/32 test items correctly → the task set is too hard for the
  source model; report, keep items, split analysis by target-correct.
- K3 Combined coverage of any verbalizer < 8/32 → that reader's accuracy is not reported as a
  rate (only counts); agreement analyses still run.

## Budget (ceiling, not promise)
184 generations (40 target + 80 readouts + 32 prompt-only + 32 G4 repeats) ≤ 19,712 output
tokens, plus separately budgeted controls: 16 OLens off-grid dev calls, 64 state-free calls on test
(32 per verbalizer, ≤ 8,192 tokens) and 16 on dev, 64 J-lens null readouts (no generation), plus R0 (64 K0 forwards, ≤ 200 bench generations at 256 tokens) and 8 dev prompt-only
calls. Target ≤ 3 GPU-hours of compute on one H100 80 GB, downloads excluded and timed separately.

## Figure
One `fig_main.png` per module (see DESIGN.md), plus `writeup.md` ≤ 1 page under
`results/g_agreement/`.

## Deviations
- 2026-10-07 (pre-collection, after the methods review in REVIEW.md, before any state existed):
  added E3b κ, E3c J-lens noise ceiling, E11b state-free reader prior, V5b off-grid check, the
  named primary contrast and the power statement; rubric J4 set to strict (start→destination
  only) and J1 negation tightened. No data had been collected.
- 2026-10-07 (dev run, before the freeze; test items never collected): (a) the target model refused
  both tense DEV prompts ("I cannot answer this question because there is no context"), so all five
  tense templates were reworded to ask for an INVENTED sentence (past/future still differ only in the
  tense cue); dataset rebuilt (items sha c5337848… → 1474dac0…), donors and G4 pairs regenerated
  from the same seed (identical pair ids). (b) J-lens rows now also carry `native.tokens_decoded`
  (tokenizer.decode per id) and the rubric reads those, because the byte-level display strings
  mangle non-ASCII tokens (" franÃ§ais"). All dev states and readouts collected before these changes
  were discarded and re-collected. (c) V6 fired: NLA dev readouts hit the 128-token cap on 8/8
  states (OLens max 110, all EOS), so the verbalizer cap was raised once to 256 for BOTH readers
  (the bench setting; the NLA was trained with a length penalty only above 192 tokens). The
  readout ceiling therefore doubles: 80 + 32 + 64 verbalizer calls × 256 = 45,056 output tokens
  instead of 22,528; target and prompt-only caps unchanged.
- 2026-10-07 12:35 UTC: configuration FROZEN (manifest/frozen_config.json) and test collection
  started on pod mats-minis-d. Post-freeze changes are confined to the analysis loader in
  core/analysis_utils.py (reading the dev-only extra-layer states_meta rows; comparing the items
  sha against the right manifest key); no collector, dataset, rubric or reader file changed, and no
  test readout had been inspected. The collection-time manifest is kept as
  manifest/frozen_config_collection.json; the analysis freeze is re-written from it with the loader
  fix noted here.
