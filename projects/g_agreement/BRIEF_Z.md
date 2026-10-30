# BRIEF_Z — Phase Z of g_agreement: can the readers be told apart? (pre-registration)

Written 2026-10-09 before any Phase Z analysis, from the Phase Z specification supplied by Guiv (reproduced in
`manifest/phase_z_spec.md`) with thresholds filled in below. Frozen by sha256 in `manifest/frozen_config_z.json`
(the repository is not under git; the freeze record plays the role of the commit). Deviations go under
"Deviations" with a date. The literature review referenced by the specification (`litreview_z.md`) was not
supplied; the review's two methodological points (position/layer confound; dose-fraction result is algebraically
expected for an affine score) are taken from the specification text and are the ones Z3/Z4 address.

Inventory at freeze time (2026-10-09): X2 cache = 4,736 edited states (S1: planted 6 doses × 128, isotropic null
768 at α 2, other-pair null 512 at α 2; S2 and S3: planted 4 doses × 128, null 768 at α 1; 128 natural), each with
the model's greedy answer, first-token answer log-odds Δ_model, the read-back block-42 last-token vector and all
three readers' native log-odds (0 missing, 0 unscorable). G5: 416 rows (16 states × doses 0.5/1/1.5/3/5 + 320
nulls). X6 inputs complete. All pods stopped; cumulative Phase Z pod budget 3 h.

Hard rules (from the specification, binding): no reader retrained; readers scored exactly as in X1/X2; all splits
by pair family with both members, their edits and counterbalanced variants in one fold; pair-level bootstrap
1,000 resamples, 95% CI; permutation nulls ≥ 200 within pair / exchangeability group; continuous answer log-odds
alongside flip rates everywhere; any "inert"/"no difference" claim via TOST against a pre-stated margin; stop at
3 h cumulative new pod time; Z1–Z3 use zero new forward passes; Y1–Y3 artefacts untouched; outputs only under
`results/g_agreement/z*/`.

## Z1 — intervention-response benchmark (no forward passes)   [module z1_intervention]
Score per reader r and edited state: s_r = lo_toward_other (= lp(B) − lp(A)); Δs_r = s_r(edited) − s_r(natural,
same source state); normalised fraction f_r = Δs_r / sep_r with sep_r the reader's natural separation of the pair
(X2 re-analysis definition; pairs with sep_r = 0 excluded and counted). Δ_model = lo_model(edited) −
lo_model(natural). Flip = flipped_to_other ∧ coherent.
E1 Flip prediction: logistic regression flip ~ f_r (one feature, intercept), fit on S2 ∪ S3 planted entries,
   8 pair-family folds (pairs assigned to folds by seed 0, stratified by family; all entries of a pair in one
   fold); held-out AUROC per reader with pair-bootstrap CI. On S1 (planted ≤ α 3, where no flips occur) the
   S2-chosen threshold (Youden on the training folds) gives a false-positive rate per reader; a dose-only model
   (flip ~ α) is the reference AUROC that any reader must beat.
E2 Magnitude: Spearman and Pearson of Δs_r vs Δ_model per site per reader, pair-bootstrap CI; partial correlation
   after regressing both on dose (α as a factor); a reader "adds information beyond the dose" if the partial
   correlation's CI excludes 0.
E3 Held-out family: train ownership → test mapping and vice versa; train S2 → test S3 (and S3 → S2); report the
   same AUROC / correlation.
E4 Reader differences: per-pair AUROC (within-pair, over the pair's edited entries) and per-pair Spearman; paired
   differences between readers with pair-bootstrap CI and Wilcoxon signed-rank. THRESHOLD (pre-registered): a
   difference counts if the 95% CI of the paired difference excludes 0 AND |Δ| ≥ 0.05 AUROC or ≥ 0.10 correlation.
   Equivalence: if no pair of readers meets the threshold, TOST on each paired AUROC difference with margin ±0.05
   (and ±0.10 for correlations) at α = 0.05 (90% CI inside the margin) → "interchangeable within margin"; else
   "not established".
E5 Null: Δs_r shuffled across edited entries within pair, 200 permutations; the AUROC and correlation p95 under
   the null are reported next to every estimate.
Verdict line: "readers separate on intervention prediction" if any E4 difference meets the threshold on S2 ∪ S3
or on the held-out family test; "do not separate" if none does and the equivalence test passes; otherwise
"undetermined".
Outputs: results/g_agreement/z1/{z1.md, z1_per_pair.csv, z1_summary.json, fig_main.png}.

## Z2 — counterbalanced X6 (no target forward passes)   [module z2_counterbalanced]
Variants of the native score per state: (a) candidate order swapped; (b) query direction swapped where the
template allows (none of the current templates encodes a direction: recorded as n/a); (c) label tokens swapped
(none used: n/a). Variant (a) for the cached data: the native LO is antisymmetric in the candidate pair by
construction (lp(A) − lp(B)), so order-swapping on cached scores is the identity; what remains order-sensitive
is the bf16 batch composition and the per-candidate token bias. Therefore the counterbalanced score is defined
here as (i) for paired states (D1, D2): the pair-symmetrised score s(state) − ½[s(state) + s(other state)] (removes
the shared per-candidate bias exactly), and (ii) for single states (D3): the additive symbol/option bias model
fitted leave-one-out (never on the scored item), which differs from X6's in-sample "centred" variant. A true
re-scoring with swapped batch order needs reader forward passes (the Oracle lens and NLA run on 27B models); it
is pre-registered as Z2b, ≤ 30 min of pod time, bundled with the Z4 pod session if Z4 runs, on the 297 D3 ERROR
states and the 126 D2 states (reader-side only, read vectors cached).
Analysis: recompute A_key, A_maj (ALL / SIBLINGS / NON-SIBLING), M_acc, the Spearman ρ(A_maj, A_key) over the 4
readers, and the shared-wrong-answer ratio on D3 ERROR, for raw / centred / counterbalanced side by side.
THRESHOLD: the inversion claim survives if ρ(A_maj, A_key) ≤ −0.5 under the counterbalanced scoring (ALL
definition) AND the shared-wrong-answer ratio ≥ 1.5 with its pair-bootstrap CI excluding 1. Otherwise the X6
inversion is downgraded to "suggestive" in writeup.md.
Outputs: results/g_agreement/z2/{z2.md, x6_counterbalanced.csv (x6.csv layout + `scoring` column), fig_main.png
(three rows: raw / centred / counterbalanced)}.

## Z3 — equivalence tests for "inert" (no forward passes)   [module z3_equivalence]
Quantity: mean Δ_model (edited − natural, toward the planted candidate) with pair-level bootstrap CI, per site
and dose: S1 planted α ≤ 1.5 (and α 2, 3 descriptively), G5 planted α 0.5/1/1.5 (and 3, 5 descriptively), the
isotropic nulls at S2/S3 (α 1) and S1 (α 2), the other-pair null at S1.
MARGIN: one quarter of the median Δ_model at the item's S2 flip dose α* (computed from per_pair.csv; the value is
stated in z3.md before the tests are read). TOST at α = 0.05: "inert within margin" if the 90% bootstrap CI of the
mean lies inside ±margin; "not established" otherwise. Flip rates with Wilson CIs reported alongside.
Output: results/g_agreement/z3/{z3.md, z3_table.csv}; a dated note in writeup.md under "Phase Z corrections".

## Z4 — matched-layer position dissection (new forward passes, ≈ 1 h)   [module z4_positions]
Site: layer 38 only. Pairs: the 64 X2 pairs. Edit: h' = h_A + α(h_B − h_A) (and the mirror from B) at the chosen
position set. Position sets: every single position of the prompt at α ∈ {0.75, 1.0} (prompts are 23–36 tokens;
to stay under ≈ 6,000 decodes, positions are subsampled uniformly to at most 15 per prompt, always including the
differing (name/object/symbol) positions, the question's first token and the last token; the subsample is drawn by
seed 0 before any decode); name-only and non-name-only (reused from Y2); all-except-{i} for the top-5 single
positions by flip rate, at α 1; restoration (all positions set to B, position i restored to A) for the same
top-5, at α 1; random-direction control at single positions, 64 runs. Recorded: greedy answer, Δ_model, read-back
block-42 last-token vector, each reader's native LO (phase A J-lens/Oracle, phase B NLA).
CLASSIFICATION (pre-registered): single causal position if one position reaches ≥ 80% of the all-position flip
rate; redundant if no single position reaches 50% but some all-except-one set still reaches ≥ 80%; joint if no
single position reaches 50% and removing some single position drops the all-position rate below 50%. Then Z1 is
rerun on this dataset (does any reader's score predict which positions are causal?).
Outputs: results/g_agreement/z4/{z4.md, per_position.csv, fig_main.png}. Launched only after the Z1 verdict has
been reported to Guiv.

## Z5 — identity-binding factorial bank (generation now; capture ≈ 30 min)   [banks/binding_factorial]
Factors, full factorial, token multiset fixed within a cell: name identity (4 name sets) × absolute position (2
templates) × mention order (A-first / B-first) × pairing (which name holds which object) × query direction (by
name → object, by object → name) = 64 cells × 2 pairs = 128 pairs. Generator and seed saved under
projects/g_agreement/banks/binding_factorial/. VERIFY BEFORE CAPTURE: on the captured block-42 last-token states,
PCA of h_B − h_A, regress PC1 on the factor dummies; if any single factor explains > 25% of the within-pair
variance, report and stop (no reader scoring). Capture = X1 protocol; report within-pair win per reader per
factor; Hewitt–Liang control: a probe trained on a randomly relabelled pairing must be at chance (≤ 0.55).
Outputs: results/g_agreement/z5/{z5.md, fig_main.png}, the bank.

## Z6 — target-private facts pilot (only if Z1 finds no separation)
Design document plus a 16-pair dry run (≤ 30 min pod): identical prompt across the pair, the fact given to the
target out of band (in-context preamble present at capture, absent from the prompt text the prompt-only baseline
and the readers' carrier see). X1 scoring. Output: results/g_agreement/z6/.

## Decision rules for the phase (from the specification)
- Z1 pre-registered reader difference → headline; proceed to Z4 to localise it.
- Z1 no difference and equivalence holds → headline "interchangeable on intervention prediction as well";
  proceed to Z6.
- Z2 fails its thresholds → X6 inversion downgraded to "suggestive" in writeup.md.
- Z4 classifies the all-position effect as single causal position → Phase X finding 6 rewritten around that
  position; Y2 re-planned.

## Compute
Z1–Z3: CPU only. Z4 ≈ 1 h pod (≈ 5,200 decodes + LO), Z2b ≤ 0.5 h, Z5 ≈ 0.5 h, Z6 ≤ 0.5 h; hard stop at 3 h
cumulative. Pod sessions log to results/g_agreement/z_collection.log and compute.jsonl.

## Deviations
- 2026-10-09 (Z1, pre-data implementation): "sep_r = 0" is evaluated as |sep_r| < 1e-4 because the Oracle LO is
  bf16-quantised (pair xmap-16 has sep 4.2e-7, a float32 residual of a tie; with it included the standardised
  logistic collapses). Excluded: Oracle 4 pairs (xmap-16/26, xown-09/20), NLA 0, J-lens 0. Misordered pairs
  (sep_r < 0) are kept with f_r sign-flipped as pre-registered (Oracle 7, NLA 18, J-lens 5).
- 2026-10-09 (Z2, pre-data definitions): the D2 counterbalanced score averages the planted state's LO with the
  MIRROR planted state of the same pair (other source, same dose), not with its own natural state (that pairing
  reproduces X6 CENTRED and imports the natural reading); 2 states lack a mirror and are counted unscorable.
  D3 leave-one-out bias: per-symbol for puzzles (over ERROR + ERROR_CONTROL), option-position for choice sets.
- 2026-10-09 (Z3): G5 behaviour rows carry no first-token log-probabilities, so G5 is reported as flips with
  Wilson CIs only; the continuous TOST covers X2-S1 and the X2 nulls. Margin = 3.273 nats (0.25 × 13.09).
- 2026-10-09 (Z5, pre-capture): the stop rule's factor list includes `order_flip` (first→second / second→first /
  none, the pair-level parametrisation of mention order that R2R4 found) in addition to the five design factors,
  because a planted order-flip direction has R² ≈ 0 on every main effect. Before NLA scoring of the
  name→object half a dedicated NLA template for object candidates must be added to core/scoring_lo.py (the
  ownership template says "the name").
- 2026-10-09 (Z4, pre-data, instructed by Guiv after the Z1 verdict): (1) The restoration arm is DROPPED: at α 1,
  "all positions set to B, position i restored to A" yields the same layer-38 state as "all-except-{i}". It is kept
  only as a determinism check: 32 restore decodes (16 per family; (item, position) drawn by seed 0 from the
  top-5 table), each compared with its all_except twin (same parsed answer; |Δ lo_model| reported).
  (2) NEW two-position arm, using the freed budget: per family, all C(5,2) = 10 pairs of the top-5 single positions
  (same top-5 rule as all_except), interpolation at both positions only, α ∈ {0.5, 0.75, 1.0}, on 10 (pair, source)
  items per family drawn by seed 0 among items where both positions exist (sources balanced where possible):
  2 × 10 × 10 × 3 = 600 decodes. Total planned ≈ 3,840 single + 64 random + 640 all_except + 600 two-position +
  32 restore = 5,176 (cap 6,500).
  (3) CLASSIFICATION, replacing the rule above (R_all = the family's all-position flip rate at α 1 from X2 S2;
  rates at α 1): SINGLE CAUSAL if some single position reaches ≥ 0.8·R_all; REDUNDANT if no single position does
  and at least one position pair reaches ≥ 0.8·R_all; JOINT if neither any single position nor any position pair
  reaches 0.8·R_all. The all-except-one arm is reported descriptively, with the original all-except rule as a
  secondary label. Two-position rates rest on 10 items per pair (Wilson CIs reported).
  (4) Z6 is skipped (Z1 found a pre-registered reader difference). Instead Z1's E1–E5 are rerun on the Z4 edits
  (single, two-position, all_except arms; natural reference from the X2 natural rows; folds by pair family;
  dose factor = arm × α; same thresholds), output results/g_agreement/z4/z1_on_z4/.
  (5) Nothing from Z4 is written into writeup.md before Guiv has seen the Z4 classification and heat map.
- 2026-10-09 (Z4/Z1-on-Z4, pre-data implementation): (1) classification thresholds are compared with a 1e-12
  tolerance (0.8·R_all in floating point can miss an exact k/n boundary); (2) in Z1-on-Z4 the dose-only reference
  model cannot be a 1-D logistic on α because dose is the categorical arm × α; it predicts each entry's flip from
  the training folds' flip rate in its arm × α cell; (3) rand_single plays the role X2's S1 played (false-positive
  rate under each fold's model); (4) pair2 items: one seeded permutation per family, first 10 eligible pairs per
  position pair (5 source A, 5 source B), so most position pairs share items (paired comparisons).
- 2026-10-09 (Z4 reporting, instructed by Guiv after seeing the Z4 output; post-data): the write-up uses a
  ROLE-ALIGNED classification as the primary reading, with the pre-registered absolute-index labels shown in a table
  alongside (mapping SINGLE CAUSAL at index 9, 14/18 = 0.78 vs bar 0.776; ownership JOINT; pooled JOINT). Reason:
  prompts use several templates, so an absolute index is a different token in different prompts, and the ownership
  top-5 were positions 0–4 by tie-break. Role-aligned labels: SINGLE CAUSAL = one role-defined token alone reaches
  ≥ 0.8·R_all; JOINT ACROSS TWO TOKENS = two named tokens together reach it and neither alone does; JOINT ACROSS A
  SPAN = no single token or token pair reaches it but a role-defined span does; REDUNDANT is reserved for "any single
  copy is enough" (several positions each alone ≥ 0.8·R_all). The earlier "REDUNDANT if a pair reaches the bar"
  label is withdrawn. Mapping = joint across the two differing symbols; ownership = joint across post-statement
  positions, nothing on the name/object tokens (pending Z4b for the exact span).
- 2026-10-09 (Z4b ownership follow-up, PRE-REGISTERED before collection; ≤ 20 min pod): 32 ownership pairs × both
  sources (64 items), interpolation α = 1. Layer 38 arms: question_only (user-text tokens after the last statement's
  final period through the end of the user text), template_only (tokens after the user text, from <|im_end|> to the
  final token), last3 (final three positions), question_first_half and question_second_half (question span split by
  token count, first half = floor). Layers 20 and 28: names_objects_only (the four differing name/object tokens;
  full layer-20/28 states captured for the 64 items). Readout: flip with Wilson CI, mean Δ_model with pair bootstrap;
  J-lens and Oracle LO on the read-back vectors (NLA not run on Z4b). Decision text: an arm reaching ≥ 0.8·R_all
  (R_all = 1.00 for ownership at L38 all positions) locates the answer; "the binding moved" if names_objects_only
  flips ≥ 0.5 at layer 20 or 28 while it flips 0 at layer 38.
- 2026-10-09 (NLA reproduction gate, PRE-REGISTERED): before any Z4 NLA number is reported, the NLA is re-scored on
  the X1 test bank (280 states) through the Z4 phase-B code path. Gate: within-pair win on ownership and on mapping
  each within 0.72 ± 0.05 (X1: 34/47 each). Failing the gate voids the Z4 NLA numbers until debugged. CPU pre-check
  (no gate): on near-null single-position edits the Z4 NLA scores match the X2 natural NLA scores (sign agreement
  0.98–1.00, median |diff| 0.06–0.09 nats).
- 2026-10-09 (Z1 reporting): each reader's result is reported as its gain over the dose-only model (ΔAUROC with a
  paired pair-level bootstrap CI); "beats dose" only if that CI excludes 0. The per-position correlation between a
  reader's mean shift and the flip rate is reported as its own result with CI, by absolute index and role-aligned.
- 2026-10-09: Z6 skipped (Z1 separated).
- 2026-10-09 (Z4b, pre-collection implementation): "the last statement's final period" is defined as the last '.'
  before the single '?' (three of five ownership templates join both statements in one sentence, so "the second '.'"
  would be the instruction's final period for 38 of 64 items and leave the question span empty); asserted per item.
  names_objects_only uses core.edit.differing_positions (4 tokens for 31 pairs, 2 for xown-09). NLA gate inputs are
  stored bf16 as in Z4 (the Z4 path), scored by the Z4 collector's own collect_lo.


## Deviations / Agam follow-ups 2 (2026-10-14)

Pre-registered before any GPU work for this round. Hard cap 4 GPU-hours over the four tasks (logged per task in
results/g_agreement/log.md and compute.jsonl). Rates get Wilson 95% CIs; differences get pair (or item) bootstrap 95%
CIs, 1,000 resamples, seed 0. Samples: bench sampling (T 1.0, top-p 0.95, top-k 64, 256 tokens), seeds recorded.

**F2-1. Prefill vs chat template (32 G1 test states = 16 pairs; 8 per family).** Formats: (a) chat template, as G1;
(b) chat template + assistant-turn prefill of an answer stem; (c) plain text `<prompt> <stem>`, no template.
Stems contain neither candidate. Deviation from the example in the request ("The answer, in Spanish, is"): that
stem puts the language key two tokens before the read position, so a reader could pass by copying it. Stems used:
language "My one-word answer is"; tense "Here is my sentence:"; ownership "The person who <verb phrase> is"
(from the item's question, e.g. "The person who carries the lantern is"); mapping "Applying the mapping twice, I
reach". Reads: blocks 42 and 44, positions last, last-1, last-2. Readers: J-lens top-10 (42, 44); Oracle free text
4 samples (44 on-grid, 42 off-grid); NLA block 42, 4 samples. Scoring: (i) rule-v1 (core/scoring.py), hit =
status "supports"; (ii) an LLM answer judge (google/gemini-3.8-flash via the Track C wrapper w_claims/judge.py,
temperature 0, JSON schema {answer: key | other | both | neither}), hit = "key"; (iii) native log-odds, hit =
within-pair win. Per state, free-text hit = share of its 4 samples that hit. Reported per reader × layer × format ×
position. Primary cells (decision): position last; reader-layers Oracle@44, Oracle@42, NLA@42, J-lens@42,
J-lens@44; contrasts (b)−(a) and (c)−(a), paired over the 16 pairs. Rule: if any primary contrast raises a reader's
free-text hit rate (rule-v1 or judge) by ≥ 20 points with the CI excluding 0, flag that the G1 "misses" are largely
a read-position artefact and list the write-up claims affected. Positions last-1 and last-2 are secondary.

**F2-2. Norm-matched split edit (ownership; 32 X2 pairs × both sources = 64 states).** Edit at block 38, all
positions, base + α·δ, α ∈ {0.25, 0.5, 1, 1.5, 2}. Arms: full δ = Δ; J_scaled = Δ_J (top-384 J-space at L38, the
Y2 basis) rescaled per position to ‖Δ(p)‖; perp_scaled = Δ_⊥ rescaled the same way; rand_scaled = a seeded random
unit direction per position at ‖Δ(p)‖ (K = 2); J_only = unscaled Δ_J (Y2 reference). Model: greedy 8 tokens, flip =
parsed answer is the other candidate (Wilson). Readers on the read-back: J-lens 42 and 44, Oracle 44 and 42, NLA 42;
follow = log-odds shift toward the other candidate vs the natural state > 0 (pair bootstrap). Rule: if
flip(J_scaled, α 1) ≥ flip(full, α 1) − 10 points, state plainly that "readers read what the model doesn't use"
reduces to readers being more sensitive to the J-space component; otherwise report the dose at which J_scaled first
flips ≥ 50% (if any) next to the readers' follow at α 1 unscaled.

**F2-3. Probe vs readers across positions and layers (X1 test bank: ownership, mapping, language, tense).** States
at every prompt position (aligned by offset from the last token, up to each family's shortest prompt) and blocks
36–60 step 4 (all on the Oracle's grid). Probe = the X1 E2 difference-of-means recipe, leave-one-pair-out; metric =
held-out within-pair win. Readers = J-lens and Oracle native log-odds, metric = within-pair win (pair bootstrap
CI). Output: heatmap pair per family + CSV, and the list of cells with probe ≥ 0.80 and every reader's CI
including 0.5 ("probe reads it, readers at chance"). NLA not included (block 42 only).

**F2-4. Diagnostics.** (a) NLA FVE: run only if the NLA repo ships a reconstructor (checked via the HF file
listing); then FVE per G1 state and AUROC of FVE for correct vs wrong NLA readouts. Oracle analogue: the Oracle's
log-prob of its own asserted answer ("- X"), AUROC for correct vs wrong readouts. (b) Oracle confusion on the Y1
puzzle items (297 errors, 103 controls), last token, blocks 44, 48, 52, 56, 1 sample each: the LLM judge lists the
candidate symbols the readout asserts as the answer; report mean distinct candidates per readout, error vs
control, item-bootstrap CI of the difference, and 5 quoted examples.

## Deviations / Agam follow-ups 3 (2026-10-14, pre-registered before any GPU work)

Budget ≤ 1.5 GPU-hours for both. Same CIs and conventions as follow-ups 2; samples at bench sampling, seeds recorded.

**F2-5. Agam's exact stems, with a copy control (32 G1 test states).** Stems that name a candidate, for the families
where his example applies: language "The answer, in {X}, is" (his wording); tense "The answer, in the {X} tense, is";
X = the key (key-stem) or the other candidate (other-stem). Ownership and mapping get his generic "The answer is"
(no candidate). Formats: chat template + the stem as an assistant prefill, and plain text "<prompt> <stem>"; plus the
chat template without a stem (format a, replication). Reads at positions last, last-1, last-2; J-lens at even blocks
36–60, Oracle (native LO + 4 samples) at blocks 44 and 56 (both on its grid), NLA at block 42 (LO + 4 samples).
Scoring as F2-1 (rule-v1, gemini-3.8-flash answer judge, native LO). Decision rules, position last:
(i) rescue: for ownership + mapping, a reader-layer whose free-text hit with "The answer is" exceeds format (a) at the
same layer by ≥ 20 points with the pair-bootstrap CI excluding 0;
(ii) copying: for language + tense under other-stem, if a reader names the stem's (wrong) candidate in ≥ 50% of
readouts and the key in ≤ 25%, report that this reader copies the stem rather than reading the state.

**F2-6. Newline feature (characters since the last newline, `col`) at new read sites.** 60 wikitext-103 test
paragraphs (Suraj used train), hard-wrapped at widths 30/40/50/60/70 (12 each) with his recipe (textwrap, no
broken words). Per passage two read tokens: "high" (col ≥ 0.75·width) and "low" (1 ≤ col ≤ 0.25·width), each with
token index ≥ 8 and a newline before it; the prompt is truncated after the read token. Read sites (Agam's
suggestions): s0 raw, read at the token; s1 `<|im_end|>` appended, read at it; s2 a counting instruction prefixed
("Count the characters on each line as you read, and keep track of how many characters are on the current line.")
then the passage, read at the token; s3 s2 + `<|im_end|>`. Readers: Suraj's fixed templates
(experiments/08_col_pilot/templates.py): Oracle and NLA phrase pairs for count_qual (primary), count_num and
decision; J-lens word lists; plus a placebo pair unrelated to line length ("- a question about history" vs "- a
question about science"; NLA analogue). Oracle at blocks 42 and 44, NLA at 42, J-lens at 42 and 44. Oracle free
text, 2 samples at 44 per state, mention rate via his MENTION_RE_STRICT. Positive control: a ridge probe for col on
the block-42 state, leave-one-passage-out, per site. Metric: within-passage pair win (high > low), Wilson CI over
60 passages. Rule: a reader tracks col at a site if its count_qual pair win is ≥ 0.70 with the CI excluding 0.5
and its placebo pair win is inside 0.5 ± 0.15; otherwise "does not track at this site".

- 2026-10-14 21:00 UTC (F2-5 scoring deviation): the OpenRouter credits ran out after 78 of 4,608 judge calls (HTTP 402), so F2-5 free text is scored with rule-v1 only (in F2-1 rule-v1 and the judge agreed on 92% of readouts); "names the stem word" = rule-v1 "contradicts". No other change.
