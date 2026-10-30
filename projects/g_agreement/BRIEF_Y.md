# BRIEF_Y — Phase Y: site search, identity-free nulls, new reader families (pre-registration)

Written 2026-10-08 before any Phase Y compute, from results/g_agreement/NEXT_STEPS.md §2 (Y1–Y5) and the Phase X
corrections. Same target (Qwen3.6-27B @ 6a9e13bd), same frozen datasets (items_x.json, items_x3_*.json), same
native-LO scoring (core/scoring_lo.py). Readers at their training site unless a module says otherwise. Budget
≈ 3 pod-hours, hard stop 6. Deviations go under "Deviations" with a date.

## Y1 — site search for the model's actual (off-text) answer   [module y1_site]
Items: X3 ERROR (297) + ERROR_CONTROL (103) + DISAGREE + AGREE_CONTROL after extending the choice pool by 900
prompts (dataset/build_y1_choice.py, seed 20261009, same templates/pools as build_x3.py, both orders) and
re-running the X3 selection on the union (target greedy + prompt-only self-guess; expected DISAGREE ≈ 100).
Capture: block outputs at layers L ∈ {42, 44, …, 62} and positions P ∈ {last, last−1, …, last−11} ∪ {positions of
the two candidate tokens in the prompt}, bf16, one forward per item; plus the logit-lens margin per layer at the
last position (final norm + W_U: lp(actual first token) − lp(other first token)).
E10 Probe sweep (CPU): for each (L, P) an L2 logistic probe for the actual answer (puzzles: 8-way over symbols,
scored as w[actual]·h − w[other]·h on the paired candidate; choices: binary actual == first-listed, oriented toward
actual), 5-fold by item, inner-CV C ∈ {0.01, 0.1, 1}, 10-label-permutation null, two-half ceiling (seed 0).
Metric: held-out favours-actual rate on ERROR and on DISAGREE. S* = the EARLIEST (smallest L, then latest P)
cell with rate ≥ 0.75, CI excluding the majority rate (puzzles 0.74 balanced-accuracy reported too) and above
the permutation 95th percentile. The logit-lens margin curve is the "trivially expected answer formation"
reference: a positive S* at a layer where the logit lens already separates is reported as such.
E11 Re-read at S*: J-lens natively at layer L (lens covers 0–62); Oracle lens at the nearest on-grid layer
{44, 48, 52, 56, 60} with the layer integer set truthfully (42 vs 44 sensitivity on the X1 bank reported); NLA at
S* is a transfer test (trained at L42 only): gate = E3 state-free prior within ±1 nat at S*, else the column is
labelled "off-training-layer, failed gate". Metric as X3 E8 (favours actual) with item bootstrap; reader READS
THE MODEL at S* if ≥ 0.75 with CI excluding 0.5 and within 10 pp of the probe.
Kill K7: no S* on ERROR (n ≈ 400) with L ≤ 58 → report "the off-text answer is not linearly present before answer
formation at the pre-answer token"; E11 not run.

## Y2 — identity-free nulls at the causal site S2 (L38, all positions)   [module y2_identity]
Pairs: the 64 X2 pairs (full captures cached). Conditions at α ∈ {0.5, 0.75, 1.0}, both sources:
  full       Δ(pos) = h_B(pos) − h_A(pos) at all positions (X2 S2, exists; reused)
  name_only  Δ applied only at positions where the A and B token ids differ
  name_removed Δ applied only at positions where the token ids are equal (question + chat suffix)
  other_pair position-wise Δ of another same-family pair with equal length, K = 4 by seed (matched per-position norm)
  J_only / J_perp  Δ(pos) projected onto / out of the top-r* J-space at L38 (r* = 384; basis = right singular
             vectors of W_U·J_38 from the neuronpedia lens, Suraj's src/mats/jspace.py recipe), plus K = 3 random
             equal-rank subspace controls (rand_only / rand_perp).
Recorded per entry: model greedy answer, lo_model, block-42 last-token read vector, each reader's LO.
E12 Model flip rate per condition × α (Wilson); E13 reader follow (win = LO shift toward planted > 0; fraction of
own natural separation) per condition at α = 1 and at the item's α* from X2.
Decision (per reader, at α = 1): READS THE BINDING if the model flips under name_removed ≥ 0.75 and reader win
≥ 0.75 there; READS THE NAME if win ≥ 0.75 under name_only and ≤ 0.5 under name_removed; if the model does not
flip under name_removed (< 0.5), the question is ill-posed at this site (reported, no reader claim).
J-space: READS NON-J if win ≥ 0.75 under J_perp while J-lens is inside its rand_perp band; J-SPACE LEAK if readers
follow J_only and the model does not flip under it. other_pair must neither flip the model nor move reader LO
toward the planted candidate (its names differ); its reader shift is the structured null band.

## Y3 — new reader families in the same LO harness   [module y3_readers]
Readers: skip-lens arms A and D (ceselder/skip-lens-qwen36-27b-agreelens-{a,d}: PEFT LoRA r64 on the plain base,
marker ㈜ 158983 between (29, 510), Karvonen ADD norm-matched hook at block-1 output, actor prompt from each
repo's nla_meta.yaml, chat template with thinking off); native LO = lp(candidate text) − lp(other) as the
continuation right after the generation prompt, averaged over the bare and leading-space forms. Qwen-Scope SAE
(Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50, layer42.sae.pt, TopK k = 50, resid_post = block-42 output): transfer test
first — fraction of variance explained on the 280 X1 states and the 466 X3 states vs a shuffled-decoder null; the
SAE becomes a reader column only if FVE ≥ 0.5, as a sparse LOO diff-in-means probe over the k active latents
(≤ 10 latents), labelled "SAE probe". R-lens (camilablank/workspace-lenses qwen3.6-27b/r-lens/lens.pt) if its
format matches the J-lens readout; otherwise skipped and said so.
Entry gate per reader (E14): X1 E1 win ≥ 0.75 on ownership AND mapping and E3 prior within ±1 nat; readers failing
the gate are reported but not added to the map.
E15 Readers passing the gate are scored on X2 S2 read vectors (follow at α*, fraction) and on the X3 sets (E8),
and added as columns to x/blindness_map.csv. Arm D is the pre-registered candidate for a "non-J" cell: its E8
on ERROR/DISAGREE and its Y2 J_perp follow are the numbers to watch.

## Compute
Phase A (target + adapters): Y1 extension decodes (≈ 1,800 greedy + 900 self-guess) + captures (≈ 600 items × 1
forward) ≈ 15 min; Y2 ≈ 128 × (2 + 2 + 4 + 2 + 2×3) × 3 α ≈ 6,900 decodes ≈ 20 min; Y3 skip-lens LO on X1/X2/X3
≈ 15 min; SAE FVE ≈ 2 min. Phase B (NLA): Y1 S* transfer + Y2 LO ≈ 15 min. Total ≈ 1.5–2 pod-h incl. loads
and the 7 GB of new downloads.

## Deviations
- 2026-10-09 (pre-data, Y2): other_pair uses only same-family pairs of EQUAL render length, so K = 4 for 24 pairs,
  3 for 12, 2 for 27 and 0 for 1 (1,116 other-pair entries instead of 1,536); the J-space basis uses W_U·J without
  the final-norm gain (matching the J-lens readout); the `full` arm is reused from X2 S2 rather than re-decoded.
- 2026-10-09 (pre-data, Y3 implementation choices where the brief was silent): (i) SAE encode follows the Qwen-Scope README
  (z = topk(x·W_encᵀ + b_enc, 50), no b_dec subtraction; the centred variant is reported alongside, both FVEs in sae_fve.json);
  the FVE gate statistic is the POOLED FVE over the 280 X1 + 466 X3 states (per-set FVEs reported); the shuffled-decoder
  null permutes W_dec columns with seed 0 and decodes the same codes. (ii) The SAE probe score is not in nats, so its E3
  (±1 nat) is recorded as not applicable and its entry gate is E1-only, flagged "PASS (E1 only; E3 n/a)". (iii) Skip-lens
  native LO = lp(X) − lp(other) as the bare continuation after the generation prompt (no template, no prefix), averaged over
  the bare and leading-space forms; both arms are mounted on the target as named PEFT adapters (skip_a / skip_d). (iv) The
  R-lens is used only if its lens.pt is a d×d-per-layer stacked Jacobian covering layer 42 (inspected at run time, result in
  results/g_agreement/y3/rlens_format.json). (v) Blindness-map columns for gated readers use the same statistics as the
  Phase X columns (X1 E1 win, X3 E8 raw rate, X2 win at α*); the symbol-bias-corrected X3 rates live in y3/e15.csv.
- 2026-10-09 (smoke run, pre-data for the test chain): Y3 SAE transfer test on 16 X1 + 4 X3 states gave FVE −0.19
  (README TopK variant; shuffled-decoder null −2.7), i.e. the Qwen3.5-27B SAE does not reconstruct Qwen3.6-27B
  block-42 states; by the pre-registered gate (FVE ≥ 0.5) the SAE does not enter the map. The full run records the
  FVE on all 280 + 466 states and the centred variant for completeness. The Y1 `--limit` smoke writes a
  `_limitN` selection file that the capture stage does not read; capture was therefore first exercised at full
  scale (resumable).
- 2026-10-09 (post-collection, Y3 E3): the full Y3 run reused the `reader|mean|family` rows that the smoke run had
  written for skip_a and rlens (means over 4 states instead of 94). Those rows were deleted and recomputed on the
  same states with the same code (results/g_agreement/y3_fixmean.log); E1 rows are per item and unaffected.
- 2026-10-09 (post-collection, Y2 J-space rule): the pre-registered "J-lens inside its rand_perp band" leak check
  is uninformative, because rand_perp removes only ~7% of the swap energy and the J-lens readout (W_U·J·h) is not
  confined to the top-384 subspace; the J-lens follows J_perp at 0.78. The J-space result is therefore reported as
  the two flip rates (J_only 4%, J_perp 92%, rand_only 0%, rand_perp 98%; Δ_J energy fraction 0.44 vs 0.27 random)
  and the readers' wins under each component, without the leak-band verdict.
- 2026-10-09 (post-collection, Y1 runtime): the probe sweep (308 cells × inner-CV logistic × 10 permutations) took
  ≈ 100 CPU-hours rather than the estimated 1–3; it was left to finish on the pod.
- 2026-10-09 (post-data, Y1 S* rule): the pre-registered S* ordering admits candidate-token positions, and the
  formal S* is 42:candA at 100% (the probe reads the answer symbol's own token identity at that position; the
  control set is also 100%), which is uninformative about the model's decision. The headline site is therefore
  restricted post hoc to pre-answer positions (last, last−1, …): the earliest passing ERROR cell is 48:last
  (0.79 [0.75, 0.83], majority 0.68, perm p95 0.61), rising to 0.92 at 52:last. Candidate-token cells are reported
  as the trivial reference. The sweep used for this decision is the reduced local run (positions last, last−1,
  last−2, candA, candB; 2 permutations; the pod's full 14-position/10-permutation sweep was stopped after 8 h
  without output: no checkpointing in that version). Re-read is run at 48:last and at 42:candA.

