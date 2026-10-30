# PREREG_WV — Phase W (direction decomposition) and Phase V (parallel experiments)

Pre-registered 2026-10-11 from `~/Downloads/BRIEF_WV.md` (copied to `manifest/brief_wv.md`), before any analysis or
pod start. Frozen by sha256 in `manifest/frozen_config_wv.json` (the repository is not under git; the freeze record
is the commit, as in Phases X–Z). Deviations are dated under "Deviations" and never edit the text above them.

## Inventory at freeze time (2026-10-11)
- Cached states on the Mac: 829 block-42 last-token states (xpz 400, xown 96, xmap 96, xch 69, xtense 48, xlang 48,
  G6 choice 16, G tense 14, …); X2 full captures L38/L42 all positions for 128 ownership/mapping items; Y1 captures
  for 730 items (297 puzzle errors, 103 error controls, 165 self-choice disagreements, 165 controls) at layers 42–62
  step 2 × the last 12 positions + the two candidate-token positions, bf16; Y2/Z4/Z4b behaviour and LO rows; the
  layer-38 J-space basis (r* = 384). The Z4b layer-20/28 captures and all read-back vectors are on the pod volume.
- Free-text readouts exist only for the G1–G6 banks (`cache/g_agreement/gens/`); X1/X3 states were scored natively
  only. Track C therefore judges the G1 free text now and the S4 samples (8 per state) after the pod.
- Michael Kenney's `nla-consistency` is unpacked read-only in the repo root from `~/Downloads/nla-consistency-main.zip`;
  its contents are inventoried in `results/g_agreement/w/INVENTORY.md`. `litreview_z.md` and `z/summary.md` do not
  exist (the Phase Z results live in `writeup.md` "Phase Z corrections" and `z/writeup_phase_z_draft.md`).
- Pods: all five stopped; hosts have been intermittently full (start loop tries e, d, c, then h100). No separate small
  GPU: V5 runs on the Mac (Apple-silicon MPS/CPU; 15 cores, 48 GB).
- API keys present in the interactive shell (OpenRouter for Track C's judge).

## Part W — hypothesis (verbatim from the brief)
**H-W: Readers are class-mean readers.** Each reader follows the class-mean direction of a fact (the shift in the
mean activation when the fact changes) whether or not the model uses it, and does not follow the residual directions
a probe relies on. The model's answer depends on more than the class-mean direction for at least one family.

Predictions: (P1) editing the class-mean component alone moves every reader ≥ 75% of states; (P2) editing the
probe-weight residual alone moves readers ≤ 60% (inside the random band) while moving the probe ≥ 80%; (P3) for at
least one family, the model's flip rate under class-mean-only editing is at least 20 points below the full-swap flip
rate. Reader difference threshold as in BRIEF_Z (ΔAUROC ≥ 0.05 or Δwin ≥ 10 points with CI excluding 0).

Readers: J-lens, Oracle Lens, NLA, skip-lens A, held-out linear probe (SAE, R-lens, skip-lens D dropped: failed Y3 gates).
"Moves/follows" = the reader's native log-odds (probe: its score) shifts toward the edited candidate; rates are over
states, with pair-level bootstrap 1,000 resamples, 95% CI; random band = the K matched-norm random directions'
follow rate (p95). Statistics rules of BRIEF_Z apply (pair-family splits, 200-permutation nulls where used, TOST for
any "no effect" claim, continuous Δ answer log-odds reported next to flip rates).

### Track A — graded bank (`projects/g_agreement/banks/w/`, seed 20261011)
counts: 600 prompts (N = 1–99, 6 per value, 4 templates, 3 objects); mapping-8: the 47 X mapping test pairs scored over
all 8 symbols; ownership-4: 128 prompts, 4 names, Z5 factorial machinery; arithmetic bridge: 100 "a ± b =" prompts in
Michael's format. Checks before the pod: per family, PC1 of within-family activation differences regressed on design
factors, no factor > 25%; counts kept only where the model is correct (greedy), requiring ≥ 95% correct overall.
(The activation-based checks run on the pod's S1 captures; a prompt-level balance check runs before the pod.)

### Track B — direction decomposition (`cache/g_agreement/w/directions/`)
Per family (ownership and mapping at layer 38 from the X2/Z4 bank; errors at layer 48 last token from the Y1 cache):
d_cm (class-mean difference, per pair's two candidates; for errors per symbol s: mean(actual = s) − mean(rest));
d_pw (held-out logistic probe weights, inner CV as in Y, orthogonalised against d_cm); d_J (projection of the swap
onto the top-384 J-space basis); d_res (swap minus the d_cm, d_pw, d_J components, orthogonalised). Norms recorded;
fraction of the full swap's norm in each component reported. Michael's recipe (18 class-mean + 18 probe-weight
directions) fitted for counts and arithmetic for the bridge.

### Track C — claim-level scoring
Adaptation of `nla-consistency/scripts/claim_judge.py` (cited) to our Oracle and NLA free text; claims labelled
true/false against the prompt and, where applicable, the model's actual answer; per-reader claim precision with
item-level bootstrap; one judge, a second-judge pass on a 100-claim subsample of internal-computation claims with κ.

### Pod session (one tmux session `w`, checkpointed stages, DONE markers under results/g_agreement/w/<stage>/)
S1 capture (Track A bank + V7's 16 pairs; layers 20, 28, 38, 42, 48, 52, all positions; greedy answer and first-token
log-odds) → S2 steering matrix (ownership, mapping at L38 at the Z4 sites; errors at L48 last token; directions
{d_cm, d_pw, d_J, d_res, full swap, random K = 10 at matched norm}, α ∈ {0.5, 1.0}; 64 states per family, errors
subsampled to 64 by seed 0: ≈ 3,840 decodes) → S3 reader scoring (J-lens, Oracle, skip-lens A, probe on all S1/S2
read-backs; NLA on S2 and counts; V6 inside S3) → S4 consistency null (8 NLA + 8 Oracle samples per state on 100 error
states and 50 counts states by seed 0, plus 50 random vectors of matched norm) → S5 stop. Budget 3 h, stop at 2.5 h;
a stage that errors twice stops the pipeline, writes the traceback to STATUS.md and stops the pod.

### Analysis and decision rules (verbatim)
W1 matrix (primary), W2 precision on graded facts, W3 claims, W4 consistency, bridge. P1, P2 and P3 all hold →
"readers read class-mean directions; the model uses more"; the layer-48 claim is rewritten as "load-bearing along
d_cm at layer 48 and the readers still miss it" only if d_cm steering at 48 flips the model ≥ 50%. d_cm steering at
48 does not flip the model and d_pw moves only the probe → withdraw the layer-48 "readers miss the model's errors"
claim. P1 fails → the class-mean hypothesis is wrong; report the matrix and stop.

## Part V — thresholds (verbatim where the brief gives them)
- V1 reader layer sweep (CPU, Y1 captures): a reader crosses 0.75 favours-actual at some layer ≤ 62 → report the first
  such layer and the lag behind the probe; none → the strong claim stands.
- V2 re-solving: a reader "re-solves" if P(favours correct) − P(favours actual) ≥ 0.15 with CI excluding 0; third
  candidate = the k−1 symbol (151 items); permutation null by shuffling candidate labels within item.
- V3 sensitivity detector on Michael's data: sensitivity adds ≥ 0.05 AUROC over recurrence alone on internal claims,
  CI excluding 0 (limitations stated if per-state perturbed readouts are absent).
- V4: 300 claims stratified by reader × claim type × judge label to `v/human_labels.csv`; κ and W3 rerun on return.
- V5 window reader (Mac, ≤ 30 GPU-minutes equivalent): success if the window reader (attention-pooled or MLP) beats
  the best last-token reader on T1 errors by ≥ 10 points with CI excluding 0, or on T2 ΔAUROC by ≥ 0.05; T3 reported.
- V6 multi-position Oracle (in S3): span (b) beats last-token (a) by ≥ 10 points within-pair win, CI excluding 0,
  and shuffled span (d) is below (b).
- V7 target-private pilot (in S1): any reader ≥ 0.70 within-pair win with CI excluding 0.5 is positive → design a
  48-pair confirmatory set; prompt-only baseline on the visible text must be 50%.

## Operator contact points (verbatim)
Pre-registration committed; pod started; S2 complete; pod stopped; summaries written.

## Deviations
- 2026-10-11 (Track B, pre-pod definitional choices; details in results/g_agreement/w/directions_report.md): errors use
  the layer-38 J-space basis (no L48 basis on the Mac); ownership d_cm is one shared vector (mean over pairs × span
  positions of the oriented Δ) applied with the pair's sign at every position; mapping class means pool both
  differing positions and both versions (d_cm not held out, d_pw is); error d_J projects the d_cm-free residual;
  d_pw = raw-space logistic weights after Gram–Schmidt against d_cm; the disjoint energy partition is
  d_cm + d_pw + d_J_excl + d_res; random K = 10 seeded isotropic rows per position; folds KFold(5) by pair /
  StratifiedKFold(5) by actual symbol; Michael's recipe implemented, fitted after S1.
- 2026-10-11 (Track C): the judge saw the model's actual answer; on G1 it is correct on all 32 states, so "against
  actual" and "against key" coincide until the S4 error states. Cross-tab uses rule-v1 correctness (no native LO on G1).
- 2026-10-11 (Track A, pre-pod): in the S1 variance check the stop-rule factors are the nuisance design factors only
  (counts: template, object, place; ownership4: name set, template, mention order, query direction, holder shift). The
  fact being read (counts: the value / its decade; ownership4: which name holds the object) is the signal and is
  reported but excluded from the 25% stop rule, as in Z5 where the binding was not a stop factor.
- 2026-10-11 (Track A, bridge): Michael's arithmetic prompts are plain text without the chat template, read at "=";
  the base model mostly continues with " ?" rather than an answer there (483/600 in his data), so the bridge compares
  probe/NLA readouts only, not the model's answer. Our 100 prompts avoid his 600 triples.
- 2026-10-11 (V3): Michael's release has no per-state perturbed/control readouts, so sensitivity is a cross-state
  genericity proxy (1 − share of other states' readouts in the same family containing the claim; τ chosen label-free
  by agreement with his recurrence score). The pre-registered LOFO logistic "both" FAILS (internal ΔAUROC −0.043
  [−0.124, +0.019]); the unfitted sum recurrence + sensitivity (+0.094 [+0.062, +0.125]; ≥ 7/8 subset +0.273) is
  reported as post-hoc only.
- 2026-10-11 (V5): all 400 error items share one template id, so "hold out templates" is degenerate; folds hold out
  whole (hops, start symbol) groups instead. The window version of T2 needs the pod's all-position edited states and
  was not evaluable on the Mac (last-token T2 only). Verdict: pre-registered success NOT MET.
- 2026-10-12 (S1 variance check, decided before any reader result was read): the raw counts check (family-centred
  states) STOPs on `template` (R² of PC1 0.993) because the four templates differ in wording; that is not a confound
  of the value. The Z5-equivalent check removes template × object cell means first (the within-pair difference does
  this for paired families): PC1 is then the value (decade R² 0.76, nuisance ≤ 0.03) → PASS. Ownership-4 within-pair
  differences: nuisance max 0.14 (mention order) → PASS. Both files under results/g_agreement/w/s1/. Counts: 600/600
  greedy-correct, all kept.
- 2026-10-12 (W1 analysis-time readings, fixed before reader rows were seen): decision rule 2's "d_pw moves only the
  probe" is operationalised as P2's conditions on the errors family (lens readers ≤ 0.60 and inside the random
  band, probe ≥ 0.80). Readers whose read-back is below the edit layer (NLA and skip-lens A read block 42; the error
  edits are at L48) are "not evaluable" on the errors family rather than counted as non-followers. Model-side
  verdicts from the S2 rows: P3 FALSE (ownership 100 vs 100, mapping 94 vs 95, errors d_cm 34 > full 19) and the
  layer-48 clause FALSE (34% < 50%).
- 2026-10-12 (Bridge): Michael's probe form on our 100 "a ± b =" layer-42 states gives operand exact-match a 0.24
  [0.16, 0.32] / b 0.48 [0.38, 0.57] vs his 0.83 / 0.93 on 600 (CIs disjoint); a sample-size curve (20→80 train rows
  per fold) rises steeply without a plateau, so the gap is attributed to n = 100 vs 480 per fold, not to the
  pipeline; per-digit accuracies are far above majority. His activations are not released. No NLA counterpart on
  arith (S4 samples errors and counts only; S3 phase B scores counts only), stated in bridge.md.
- 2026-10-12 04:55 UTC (budget, decided at pod-minute 102 before S4 started): S4 shrunk from 100 error + 50 counts
  states × 8 samples + 50 random to 24 + 12 states × 8 + 10 random per reader, so that S3 phase B (NLA on the steering
  matrix, needed for P1/P2) runs before the 150-minute stop; the pre-registered S4 size would have pushed it past.
  S3v1 phase B (NLA layer sweep) and S4 phase B may be skipped by the budget guard; whatever is skipped is reported.
- 2026-10-12 05:15 UTC (budget, pod-minute ≈ 123, decided before any reader-vs-model result was read): the skip-lens
  scoring of the 600 counts states (99 candidates × 2 templates) was running far slower than estimated and would have
  consumed the budget before the NLA scored the steering matrix. The original chain was stopped and a prioritized
  resume chain started: skip-lens finishes S1 (counts stopped at the 384 states already scored) and S2 + the probe →
  NLA on the S2 read-backs only (NLA counts scoring dropped) → V1 layer arm → shrunk S4 → NLA layer arm → S5 stop,
  with the 150-minute guard before each step. Consequences: W2 has skip-lens on 384/600 counts and no native NLA
  counts column (NLA counts come from S4 free text only, if S4 runs); whatever the guard skips is reported.

- 2026-10-12 05:47 UTC (budget guard, automatic): the prioritized resume chain finished S3 A (skip-lens rest + probe,
  124→134 pod-min), S3 B (NLA on the S2 read-backs, 134→145) and S3v1 A (V1 layer sweep + three-way, 145→157), then
  hit the 150-minute guard and went to S5 (stop). Not run: S4 (free-text samples, all readers), S3v1 B (NLA layer
  arm; NLA scored at L42 and L48 only), NLA counts scoring, V7 pilot states beyond the S1 capture. Consequences
  (analysis-time fallbacks, fixed before W3/W4 were run): W3 claim precision on S4 counts/error states is NOT
  available; `w/w3/w3.md` carries the G1 numbers (32 states × 2 readers × 8 samples) and `w/claims/W3_g4_repeats.md`
  (8 items × 2 readers × 2 samples) instead. W4 (≥ 2-of-8 filter) is replaced by `w/w4/w4.md`
  (`w_analysis/w4_fallback.py`): the W4 matcher on the G4 repeat claims (2 samples, kept = recurs in the other
  sample) plus Michael's own 8-sample data in V3. W2's free-text columns (Oracle / NLA stated number) are empty;
  W2 counts use native scores only. The pre-registered W3/W4 thresholds are therefore not evaluated.
- 2026-10-12 09:42–09:52 UTC (operations): the chain's S5 stopped pod e before the results were pulled; the
  retrieval start loop started pod d (same volume) at 09:42:44 UTC, the pull ran from it, and it was stopped at
  09:52 UTC after a check (no tmux, 0 % GPU). The RunPod API reports pod d "lastStartedAt 05:16 UTC", which would
  mean ~4.6 idle pod-hours instead of ~10 min; this could not be resolved from the API and is flagged for the
  billing page. Pod e total: 157.6 pod-min (26.7 idle before launch + 131 in-session).
- 2026-10-12 10:40 UTC (V7 confirmatory, pre-registered BEFORE capture; Guiv asked to run it). Design: `banks/w/items_v7_confirmatory_design.md`
  (sha256 0f5b05975512a329b71714bad748ce8701e4ff1404f46ac5fdd288872c6e9052), written by v7.py when the pilot was positive. Bank: `banks/w/items_v7c.json`, 48 base pairs × 2 preamble roles
  = 96 pairs / 192 items, seed 20261013, sha256 2c3f39f749f128782814279b4fde6dcda2e02a0967633daadb355622bf785c8e, frozen. Names: 16 single-token first names (Qwen2.5 tokenizer, bare and
  space forms; the Qwen3.6 tokenizer is checked on the pod at capture) disjoint from the pilot's 30; objects: 3 new colour+noun pairs. Visible prompt
  identical within a pair; prompt-only baseline 50 % by construction for role = system; for role = user the preamble is in the user turn
  (control for the role, the fact is NOT target-private there). Readers: J-lens (42, 38), Oracle (42, 38), skip-lens A (42), held-out
  Track-B probe (42, 38), NLA (42; also the pilot's missing cell) if the 60-min budget allows. Rules as in the design file: primary = each
  pilot-positive cell (jlens@42, olens@42, olens@38, skip_a@42) ≥ 0.70 within-pair win with the pair-bootstrap CI (1,000, seed 0)
  excluding 0.5 over the 48 role = system pairs; secondary per role and per mention order; a role difference ≥ 10 points with the paired
  CI excluding 0 is a role effect; ceiling = the target's own accuracy with the preamble. Probe fix decided now: the binary probe's
  orientation rule reads mention order from prompt_text, which for V7 has no names, so it fell back to candidate order (the pilot's 0/16);
  the rule now reads preamble + prompt_text (s3_score.item_lookup). The pilot probe cell is re-scored with the fix and reported next to
  the original; the probe stays exploratory. Not run: the V6 (b) span capture for these items. Pod budget 60 min, stop at the end.
- 2026-10-12 12:15 UTC (V7 confirmatory, outcome): run as pre-registered (pod mats-minis-v7c, 12 min); all four primary cells
  confirmed; NLA scored on the pilot and confirmatory sets (pilot NLA cell filled: 15/16). Pilot probe re-scored with the fixed
  orientation rule: 16/16 (original 0/16 kept in `v/v7_pilot_original.md` and `v7_pilot_probe_rescore.json`). The secondary role
  and mention-order effects are reported as observed, not as pre-registered claims. No further deviations.
- 2026-10-13 (Oracle on-grid sensitivity "O44", pre-registered BEFORE compute; requested by Guiv after Agam's review).
  The Oracle lens (olens_s3d_rl600) was trained on blocks 20–60 step 4; every Oracle log-odds number in X1 and W1 is at
  block 42, off-grid. Rerun at block 44 (on-grid, closest to 42 and above the L38 edits), same states, same scoring:
  (i) X1 natural bindings: all items_x test pairs (48 ownership, 48 mapping, 24 language, 24 tense), last token, Oracle
  native LO at L44 (carrier says layer 44) vs the existing L42 rows; also a fresh L42 re-score as a reproduction check.
  (ii) W1 steering matrix, ownership and mapping: the S2 edits at L38 (64 states × d_cm, d_pw, d_J, d_res, full at
  α 0.5 / 1 + 10 random at α 1 + natural) re-run with the read-back at blocks 42 and 44; Oracle and J-lens scored on the
  L44 read-back; follow = W1's definition. NLA is not rerun (block 42 only). Decision rule: the L42 Oracle conclusions
  stand if no cell (X1 family win; W1 family × direction follow at α 1; random pooled) changes by ≥ 10 points with the
  paired pair-bootstrap 95% CI (1,000, seed 0) excluding 0. Otherwise the L44 value becomes the primary Oracle number
  in the summaries and the change is reported with both values. Checks named in advance: Oracle follows d_J (ownership
  94%) and d_res (88%) at 0% model flips; Oracle does not follow d_pw (52%, inside the random band); X1 Oracle win 83%
  ownership / 87% mapping. Reproduction checks: L42 read-backs vs the original S2 read vectors (cosine), fresh L42 X1
  LO vs x1_lo.jsonl, rerun model answers vs s2_behaviour.jsonl. Budget 45 pod-minutes.
- 2026-10-14 03:10 UTC (O44 outcome; run as pre-registered, pod mats-minis-v7c, 10 min): reproduction checks pass (L42
  read-backs cosine ≥ 0.9999 to the originals; 2,670/2,688 rerun answers identical; re-computed L42 tables match W1 and
  X1). Oracle cells that change under the rule (|Δ| ≥ 10 pts, CI excludes 0): W1 ownership d_cm follow 77% → 92%
  [Δ +16, CI +5 to +28]; W1 ownership d_pw follow 52% → 66% [+14, +2 to +28], now above the 47% random band. Not changed:
  Oracle follows d_J (94 → 91%) and d_res (88 → 94%) at 0% model flips; X1 ownership 83 → 91% (+9, below the 10-pt
  threshold), mapping 87 → 94%. Per the rule, the L44 values are the primary Oracle numbers for the two changed cells.
  The J-lens (native at every layer, so not an off-grid question) drops at L44 in mapping (d_cm 98 → 81%, full 98 → 70%,
  X1 94 → 81%); reported, not part of the rule. Results: results/g_agreement/w/o44/.
