# BRIEF_S — sprint S additions (pre-registration)

Only sections S2 and S5 live in this file's first commit; the other chats' sections (S1, S3, S4, ...) are merged in
by Guiv. Written 2026-10-15 before any S2/S5 data or GPU work. Do not change a rule after seeing data; add a dated
note under "Deviations" instead.

Shared rules for S2 and S5: hard cap 4 GPU-hours combined; stop and report after each task; check OpenRouter with
one judge call before starting (402 -> stop and tell Guiv); if `nvidia-smi` shows another chat on the GPU, wait or
ask; Wilson 95% CIs for rates, item/pair bootstrap (1,000 resamples) for differences; never print keys; large files
in `cache/`; log to `results/g_agreement/log.md` and `compute.jsonl`; `git pull --rebase` before each commit; push to
`g-agreement-phase-wv`.

## S2 — Context vs belief (counterfactual preamble)   [outputs results/g_agreement/s2/]

**Question.** When the system turn states a fact that contradicts world knowledge, do the readers report the
context fact (what the model is told) or the world fact (what it believes)?

**Bank.** 48 pairs in the W system-turn format (banks/w, w_pod); the visible prompt is identical within a pair, only
the system turn differs. 24 counterfactual pairs: the system turn asserts a fact contradicting world knowledge, two
versions per pair (e.g. "In this world, the capital of France is Lyon" vs "... is Marseille"). 24 world-consistent
control pairs built the same way (the asserted fact is true; versions use two true/neutral alternatives). Fixed
seed 20261015; bank saved in the repo (`banks/s2/items_s2.json` + builder). **Gate: Guiv eyeballs 5 items before
any capture.**

**Readers.** Oracle and J-lens at layers 44 and 56; NLA at 42; probe as reference; the target model's own answer as
ceiling; prompt-only baseline (reader fed the visible prompt without the system turn). Free-text outputs are scored
with rule-v1 and the judge; native log-odds are computed between the two context options and the world fact.

**Metrics.** (1) Context-fact rate: share of pairs where the reader reports the context fact in both versions
(pair-level, both versions right). (2) World-fact rate on counterfactual items: share where the reader reports the
world fact instead. (3) Prompt-only baseline for each. Wilson 95% CIs; control-vs-counterfactual difference by
pair bootstrap.

**Decision rule (per reader).**
- "reads context": context-fact rate CI lower bound > 50% on counterfactual items AND within 15 pp of the control
  items' rate.
- "reads belief": world-fact rate on counterfactual items > 50% (CI lower bound).
- otherwise "mixed".

**Outputs.** `results/g_agreement/s2/{s2.md, s2.csv, fig_s2.png}` (one row per reader x item set; CI bars).
**Kill / verify.** If the model's own answer reports the context fact on < 50% of counterfactual pairs (CI upper
bound), the bank does not instruct the model and the reader comparison is uninterpretable; report and stop.

## S5 — SAE as a fourth reader   [outputs results/g_agreement/s5/]

**Reader.** The Qwen-Scope layer-42 SAE (`y3_readers/sae.py`), as the sparse LOO diff-in-means probe over latents.

**Gate (transfer test, BRIEF_Y Y3).** First report FVE on our states vs the shuffled-decoder null. If FVE < 0.5, or
FVE is not above the null by at least 0.2, report and stop: no further S5 analysis. (Prior: the Y3 smoke run gave
FVE -0.19 on 20 states, so the gate is expected to fail; run it on the full 280 X1 + 466 X3 states plus the W
states, both encode variants, and report both.)

**If the gate passes** add the SAE reader to:
- (a) F2-2 norm-matched split (BRIEF_Z F2-2): does it follow the J-space piece (J_scaled) and the non-J piece
  (perp_scaled) equally, as the other readers do? Report follow rates and flips per arm with pair-bootstrap CIs.
- (b) X6 majority-vs-key (x6_majority): does adding a reader trained differently weaken the shared-wrong rate and
  the majority inversion? Recompute both with and without the SAE.

**Decision rule for (b).** "SAE breaks the correlation" if its shared-wrong rate with the other readers lies within
the independence CI while the Oracle-NLA pair's shared-wrong rate stays above that CI. Otherwise "does not break".
Independence CI = the same permutation/bootstrap construction X6 already uses for the existing reader pairs.

**Outputs.** `results/g_agreement/s5/{s5.md, s5.csv}` (the gate FVEs are reported even if the gate fails).

## Deviations
(none)

## S1. Are the template cells load-bearing? (pre-registered 2026-10-15, before any S1 number)

Brief as given (verbatim):
> Cells: the (family, position, layer) cells from F2-3 (f2/t3_analyze.py output) where probe >= 0.8 and J-lens and Oracle
> are at chance (expected ~60). Print them grouped by token type and layer. Run at the 2-3 layers with the most cells,
> plus layer 38.
> Edit h' = h_A + alpha (h_B - h_A) as in f2/t2_normsplit.py, alpha in {0.5, 1, 2}, 64 states per arm (32 pairs x both
> directions), in the families where the cells occur.
> Arms: (1) cell positions only; (2) all positions (positive control); (3) last token only; (4) an equal number of
> non-cell positions, excluding content tokens (names, objects, letters), seed fixed; (5) norm-matched random direction
> at the cell positions; (6) probe direction only at the cell positions, norm-matched to arm 1.
> Metrics: model flip rate (greedy decode, as F2-2) with Wilson CI; answer log-odds shift as a fraction of arm 2's;
> reader native log-odds at the last token after the edit (J-lens; Oracle at 44 and 56).
> Decision rule: LOAD-BEARING if arm 1 flips >= 50%, its Wilson lower bound exceeds the upper bounds of arms 4 and 5,
> and its log-odds shift >= 50% of arm 2's. INERT if arm 1 flips <= 5% and the shift is < 10% of arm 2's. Otherwise
> PARTIAL. Report per layer and token type.

Operationalisation (fixed now, from `results/g_agreement/f2/t3/t3_probe_only.csv`, 60 cells: ownership 45, tense 15):
- **Cells** are (family, block, offset k from the last token); in an item of length T the cell position is T−1−k.
  Cells per block (both families): 36: 11, 44: 10; 40, 48 and 52 tie at 9. **Edit layers: 36 and 44 (the two with
  the most cells) plus 38.** No F2-3 cell sits at 38 (grid step 4): at 38 the cell set is the union of the family's
  cells at 36 and 40. Families: ownership and tense. Cell offsets: ownership@36 {2,3,6,8,10,11,12,13,14},
  ownership@44 {2,3,6,8,11,12,13,14,16}, ownership@38 = ownership@36 ∪ @40 = {2,3,6,8,10,11,12,13,14};
  tense@36 {3,16}, tense@44 {16}, tense@38 {3,16}.
- **States**: the 32 X2 pairs per family (first 32 X1 test pairs by index, as F2-2), both directions → 64 states per
  arm. Edit at the output of the edit block, prompt prefill only; h_A, h_B captured at that block on the pod.
- **Arms**: (1) cells; (2) all positions; (3) last token; (4) n = |cells| positions drawn without replacement (seed
  `stable_seed("s1", pair_id, layer)`) from positions that are not cells, not the last token, at or after the pair's
  first differing token (so Δ ≠ 0 is possible) and not content tokens (a token that differs between A and B, or whose
  text is part of a candidate answer, a name or an object word of the item; for tense also the time words); (5) seeded
  random unit direction per cell position scaled to ‖αΔ(p)‖ (F2-2 `rand_scaled_0` recipe); (6) X1 E2 probe direction
  (difference of class means at that block and offset, leave-this-pair-out over the family's X1 test pairs), signed
  toward the other version's label, scaled per position to ‖αΔ(p)‖. α ∈ {0.5, 1, 2}.
- **Token-type breakdown** (secondary, reported, not used in the verdict): arm 1 restricted to chat-template tokens
  (`<think>`, `</think>`, `\n\n`, `\n`, `<|im_start|>`, `<|im_end|>`, `assistant`) = arm 1T, and to instruction words
  (everything else, e.g. ` Reply`, ` name`, `?`, ` my`) = arm 1I, classified by each item's actual token at the cell
  position. The S1 decision rule is applied to 1T and 1I separately as a descriptive label.
- **Flip** = greedy 8-token answer parsed (core/scoring `extract_target_answer`) as the other version's answer (F2-2).
  **Answer log-odds**: ownership = first-token log p(other) − log p(own) (F2-2 `pair_first_tokens`); tense =
  teacher-forced summed log-prob of the other version's natural greedy 8-token answer minus the own version's, under the
  edited prompt. Shift = edited − natural; fraction = mean shift(arm) / mean shift(arm 2) at the same family, layer, α;
  95% CI by item bootstrap (1,000, seed 0). Flip rates: Wilson 95%.
- **Readers**: J-lens and Oracle native log-odds at the last token, read at blocks 44 and 56 (reader follow = LO moves
  toward the other version vs the natural state). For edits at 44, the 44 read of arms 1, 4, 5, 6 is unchanged by
  construction (the last token is not edited) and is reported as such.
- **Verdict** per (family, layer) from α = 1 (the F2-2 reference dose); α = 0.5 and 2 reported alongside. Natural
  states must parse to their own answer (else excluded and counted).
- Budget: ≤ 2 of the chat's 4 GPU-hours for S1. Outputs `results/g_agreement/s1/{s1.md, s1.csv, fig_s1.png}`.

### S1 Deviations
- 2026-10-15, before any S1 forward pass (from F2-3's cached tokens and probe wins only). (i) The X1 test bank has
  23 tense pairs, not 32: tense runs on all 23 pairs (46 states per arm). (ii) 17 of the 23 tense pairs differ in length
  (" did" vs " will do"); F2-3 aligned positions from the end, so tense offset 16 compares A's " my" with B's
  " neighbour" in those pairs. On the 6 equal-length pairs the probe there wins only 2–6/6 (≤ 4/6 from block 44 on),
  against 16–17/17 on the unequal ones: the 6 tense cells at offset 16 are a token-misalignment artefact. They are
  dropped from S1, which leaves tense@36 = tense@38 = {3} and no tense cell at 44 (tense is run at 36 and 38 only).
  F2-3's count of genuine probe-only cells becomes 54 (ownership 45, tense 9). Offsets 2, 3, 6 sit after the
  differing span, where end-alignment is exact. (iii) For unequal-length tense pairs, Δ(p) pairs positions before the
  first differing token one-to-one (Δ = 0 there) and later positions from the end; arm 2 uses that map.
- 2026-10-15: these S1/S4 sections were deleted from this file by commit 59781ed (another chat's S2/S5 rewrite) and
  restored verbatim from commit 6f34734 (the original pre-registration, pushed before any S1/S4 compute).

## S4. Newline feature (col) under <|im_end|> insertion and directed-modulation prompts (pre-registered 2026-10-15, before any S4 number)

Brief as given (verbatim):
> Extends F2-6; reuse f2/t6_col.py, t6_bank.json.
> First find the "global workspace" paper this project builds on (search the repo's resources/, BRIEF*.md and Suraj's
> notes for "workspace", "directed modulation"; fetch the paper) and list its directed-modulation prompt templates
> verbatim with section/page. If you can't find it, stop and ask me rather than inventing prompts.
> Conditions (same 60 passages, long-line vs short-line reads): (a) F2-6 baseline (reuse); (b) <|im_end|> inserted
> mid-sentence, read at the im_end token and at the last token; (c) 2-3 of the paper's directed-modulation prompts
> adapted to "attend to how many characters are on the current line", prefixed to the passage, read at the last token;
> (d) a matched-length irrelevant instruction as control for (c).
> Readers: J-lens and Oracle at layers 44 and 56, NLA at 42; probe as reference. Metric: AUROC long vs short (item
> bootstrap), and for free text whether the readout mentions line length, scored by rule (no judge credits needed).
> Decision rule: a reader "tracks col" in a condition if AUROC CI lower bound > 0.6 AND exceeds the control (d) by
> >= 0.1. Otherwise no.

Operationalisation (fixed now): paper located in `resources/interp_tools.md`: Gurnee et al., *Verbalizable
Representations Form a Global Workspace in Language Models*, Transformer Circuits, July 2026
(transformer-circuits.pub/2026/workspace/); WorkspaceBench's `directed_modulation` eval derives from it. The prompt
templates will be copied verbatim (with section) into an addendum below **before** S4 GPU work; if the paper's own
templates cannot be retrieved, S4 stops and asks. "Exceeds the control by ≥ 0.1" is read as AUROC(c) − AUROC(d) ≥ 0.1
(point estimate); for conditions (a) and (b), which have no instruction, the comparison is against (d) as well.
Reader score per state = the F2-6 col score (Suraj's fixed templates, high-vs-low log-odds); AUROC over the 120 reads
(60 long, 60 short) per condition × reader × layer. Line-length mention rule = F2-6's regex (characters / line length /
newline / column / count), applied to Oracle and NLA free text (2 samples per read).

### S4 Deviations
(none yet)

## S3. Why does the model under-use the J-space piece? (pre-registered 2026-10-15, before any S3 number)

Motivation: F2-2 found that at equal norm the J-space piece of the ownership edit moves the answer log-odds +3.9 nats
vs +24.8 for the non-J piece.

**Hypothesis.** The J-space is roughly the output-token subspace, so token-producing readers weight it fully while the
model's downstream answer computation runs mostly through the non-J piece.

**Measurements (CPU only, no new forward passes).** J-space = top-r right singular vectors of M_l = W_U·J_l (the Y2
recipe, `core/edit.jspace_basis`), r = 384 and 1,536. W_U-span = top-k right singular vectors of W_U with the final
norm's scale folded in (W_U·diag(g)), k = 384 and 1,536.
- (a) Subspace overlap = mean squared cosine of principal angles (‖Q_Jᵀ Q_U‖_F² / r) between the J-space and the W_U
  top-k span, versus 100 random subspaces of the same dimension (seeded).
- (b) Ownership edit Δ at layer 38 (X2 ownership pairs, F2-2 definition, per-position Δ) and its two pieces Δ_J, Δ_⊥:
  fraction of squared norm inside the W_U top-k span (k = 384, 1,536), and logit-lens top-20 tokens of each piece, with
  whether the answer names (candidates A/B of the pair) appear.
- (c) Fraction of the probe direction and of the class-mean direction (W Track B, `w_directions`) inside the J-space,
  versus the random-subspace baseline.
- (d) Repeat (a)–(c) at layers 42 and 56, as far as cached states allow (layer 56 states are not cached; (b)/(c) at 56
  are reported only if the states can be had without a new forward pass, otherwise marked "not computable").

**Decision rule (fixed now).** "Supported" iff (i) the J-space overlap with W_U's top span exceeds the random 99th
percentile by ≥ 3× (ratio of mean squared cosines, observed / p99 of random) AND (ii) the J-space piece holds a larger
W_U-span fraction than the non-J piece (Δ_J > Δ_⊥, at k = 384, layer 38). Otherwise "not supported", stated plainly
with which clause failed. No change to the rule after seeing data; any change goes under Deviations below.

Outputs: `results/g_agreement/s3/{s3.md, s3.csv, fig_s3.png}`; second-model feasibility (no compute):
`results/g_agreement/s3/second_model.md`.

### S3 Deviations
- 2026-10-15 (clarification, written before any S3 number was computed; the rule itself is unchanged): the decision rule is
  evaluated on the primary pairing J-space = the Y2/F2-2 basis (top-384 of W_U·J_38, no gain) against the W_U span with the
  final-norm scale folded in (top-384 of W_U·diag(g)), block 38. r = k = 1,536 is reported but cannot carry the rule: a random
  1,536-d subspace already has overlap 0.30, so a 3× ratio to the random p99 is almost unreachable (ceiling about 3.3×). The other
  pairings (gain in J, gain out of W_U) are sensitivity rows in the CSV. Layer 56: states are not cached, so only (a) can be done there.

## S7. Can anything flag a shared reader error? (pre-registered 2026-10-16, before any S7 number)

Brief as given (verbatim, condensed): cases = forced-choice items (X6 / Z2) where the model is wrong and all three readers
(J-lens, Oracle, NLA) favour the same wrong candidate; comparison set = items where all three are right. Candidate flags
from cached artefacts: (a) Oracle's own confidence (|log-odds| of its asserted answer); (b) cross-sample consistency where
multiple samples exist (G4 repeats, F2-1 samples); (c) disagreement between the readers' answer and an independent linear
probe's answer; (d) reader–reader margin (how close the three log-odds are). Metric: AUROC of each flag for shared-wrong vs
all-right, item bootstrap CIs, ROC curves in one figure. Also the independence-corrected shared-wrong rate: permutation null
shuffling reader outputs within item-difficulty bins (bins by the model's own answer log-odds), vs the plain independence
baseline (9.2%). Decision rule: a flag "works" if its AUROC CI lower bound > 0.7.

Operationalisation (fixed now; CPU only, no forward passes):
- **Items.** X3 set ERROR (n 297 puzzle items; the model's greedy answer is task-wrong; X6's D3_error). The readers' job is
  to read the model's answer, so "right"/"wrong" is relative to the KEY = the model's actual answer (X6 convention, the one
  behind the 9.2%). **Shared-wrong** = all three LO readers (J-lens L42, Oracle lens, NLA; native LO from
  `cache/g_agreement/x/x3_lo.jsonl`) favour the same non-key candidate (LO toward key < 0 for all three). **All-right** =
  all three favour the key. Mixed items are excluded from the AUROC. Primary scoring = RAW (the X6 pre-specified sign; the
  scoring behind 17.5% vs 9.2%); CENTRED (X6 5-fold symbol bias) is a secondary row, not used in the verdict. Both lists →
  `results/g_agreement/s7/shared_wrong_items.csv`.
- **Flags** (score oriented so that higher = "suspect a shared error"; orientation fixed now, AUROC reported as computed,
  never flipped after the fact):
  - (a) `oracle_conf` = −|LO_Oracle| (low Oracle confidence → suspect).
  - (b) Multi-sample consistency. G4 repeats and F2-1 samples cover G1/X1 states only (lang/tense/ownership/mapping), none
    of the X3 puzzle items, so (b) as written is not computable on this item set; reported as such. Substitute, the only
    multi-readout data on these items: (b′) `oracle_ft_distinct` = number of distinct candidate symbols named across the
    four F2-4 Oracle free-text readouts (blocks 44/48/52/56, 1 sample each, `f2/t4/t4_confusion.csv`), union over blocks
    (more distinct answers → suspect). Items without all four readouts are dropped for (b′) and counted.
  - (c) `probe_disagree` = −(probe score toward the readers' common answer), with the probe = X6's 5-fold L2 multinomial
    logistic probe on the block-42 states (score toward key; for shared-wrong items the readers' answer is the other
    candidate, so the sign flips). Higher = the probe leans away from what the readers say.
  - (d) `reader_spread` = SD across the three readers of their LO, each reader's LO first z-scored over the 297 ERROR items
    (readers are on different scales). Higher = readers less close → suspect. Secondary (descriptive, not in the verdict):
    (d′) −min_r |z_r| (the weakest reader's margin).
  - Reference (not a reader-side flag, descriptive): (m) −|model answer margin| at the final block (Y1 logit lens, block 63).
- **AUROC** per flag, positives = shared-wrong, negatives = all-right; 95% CI by item bootstrap (2,000 resamples, seed 0,
  resampling within each class). ROC curves of a–d in one figure (`fig_s7.png`). **Decision: a flag works iff its CI lower
  bound > 0.7.**
- **Independence-corrected shared-wrong rate.** Difficulty = model's own answer LO at block 63 (Y1 `y1_logitlens.jsonl`
  margins["63"], first-token log p(actual) − log p(other)). Bins: 5 equal-count bins (quintiles) over the ERROR items with
  a margin (primary); 3 and 10 bins as sensitivity. Null: within each bin, independently permute each reader's
  favours-key sign across items (10,000 permutations, seed 0); statistic = share of items where all three favour the non-key
  candidate. Report observed rate, plain independence product (should reproduce 9.2%), within-bin null mean and 95%
  interval, ratio observed / null mean, and permutation p (share of null ≥ observed). Interpretation fixed now: if the
  within-bin null mean is ≥ half-way from 9.2% to the observed rate, difficulty explains most of the excess.
- Outputs: `results/g_agreement/s7/{s7.md, s7.csv, fig_s7.png, shared_wrong_items.csv}`; code
  `projects/g_agreement/s7_flags/analyze.py`.

### S7 Deviations
(none)

## S6 step zero. Do third-party Qwen3-4B readers read the G1 keys? (pre-registered 2026-10-16, before any S6 number)

Brief as given (verbatim):
> On Qwen/Qwen3-4B, load the J-lens (neuronpedia/jacobian-lens qwen3-4b), the Oracle LoRA (qwen3-4b/oracle, grid 12–34
> step 2) and the NLA (minnesotanlp/nla-qwen3-4b-L24-av) per results/g_agreement/s3/second_model.md. Render the G1
> pilot's 32 test states with the 4B chat template; read at block 24 (Oracle also 22/26). Score native log-odds and
> rule-v1 free text exactly as G1. Decision rule: a reader "reads the key" if its two-candidate win rate CI lower bound
> > 50% on ≥ 3 of 4 families. Output results/g_agreement/s6/step0.md with the per-reader × family table and a one-line
> go/no-go for the full F2-2 + X6 replication tomorrow. Cap 0.5 GPU-h.

Operationalisation (fixed now):
- **Target** `Qwen/Qwen3-4B` (36 blocks, bf16), G1 test items (`dataset/items.json`, split test: 32 states, 8 per
  family = 4 pairs), rendered with `core/model.render_item` (Qwen3 chat template, thinking off). Last-token states at the
  output of blocks 22, 24, 26. Greedy target answers (32 tokens) recorded as context, not in the rule.
- **J-lens** `neuronpedia/jacobian-lens` `qwen3-4b/jlens/Salesforce-wikitext/Qwen3-4B_jacobian_lens.pt`, read at 24
  (22 and 26 reported), same cosine readout and `lo_jlens` as G1.
- **Oracle** `neuronpedia/jacobian-lens` `qwen3-4b/oracle` (LoRA r16, `lens_config.json`): prompt identical to our
  `C.OLENS_PROMPT`, marker ㈎ (id 149705, neighbours 29/522; forced, not scanned), input-embedding replace with
  16000·unit(h); read at 22, 24, 26 (all on its grid).
- **NLA**: `minnesotanlp/nla-qwen3-4b-L24-av` and its mirror `zaemyung/…` are gated (manual approval; our HF token gets
  403 on 2026-10-16). **Substitute, declared before any number:** `anicka/nla-qwen3-4b-universal-av` (open LoRA on
  Qwen3-4B; card protocol: AV prompt from its `nla_meta.yaml` with `depth_pct` = nearest of its grid to 100·L/36, i.e.
  63% for block 24; input-embedding of ㈎ replaced by the vector **normalised to norm 150**; chat template, thinking
  off). Its native LO uses our NLA templates with an empty prefix (its prompt already ends in `<explanation>`). If access
  to the minnesotanlp AV is granted before the run, it is run as well and reported as the named NLA.
- **Native score**: per state, lo = score(key) − score(other) (G1 `score_lo` conventions). **"Two-candidate win rate"
  = fraction of a family's 8 states with lo > 0**, Wilson 95% (with 4 pairs per family, the within-pair win cannot
  clear the bar except at 4/4, so it is reported but not used). A reader "reads the key" iff the Wilson lower bound
  > 0.5 (i.e. ≥ 7/8) on ≥ 3 of 4 families, at block 24 (Oracle's verdict also reported at 22 and 26).
- **Free text**: 1 sample per state per text reader (G1: sample 0, temperature 1.0, top-p 0.95, top-k 64; 256 new tokens;
  NLA card: its own sampling is greedy, we keep G1's sampling for comparability), scored with rule-v1
  `extract_claims`; reported as supports / contradicts / no claim per family. Not in the rule.
- **Go/no-go**: GO for the F2-2 + X6 replication if ≥ 2 of the 3 readers read the key at block 24 (≥ 3 readers incl. the
  probe for X6). NO-GO otherwise.
- Cap 0.5 GPU-h. Output `results/g_agreement/s6/step0.md` (+ `step0.csv`).

### S6 Deviations
(none yet)

## S8. Full-candidate rescoring (S8a) and a three-way error test (S8b) (pre-registered 2026-10-16 11:35 CEST, before any S8 number)

Brief as given (verbatim):
> S8a. Full-candidate rescoring. Re-read the F2-2 norm-matched split (ownership, J_scaled / perp_scaled / random, alpha
> 0.25-2, 64 states) and the X3 ERROR shared-miss items with each reader's native log-probs over ALL candidate
> names/answers in the item (8 for mapping, the full name set for ownership), not two. Use the cached read vectors
> (x2_readvecs, X3 captures); new reader forward passes only. Metric: reader picks the planted (F2-2) or key (X3)
> candidate, chance = 1/k. Report per reader x arm x alpha with Wilson CIs next to the two-candidate numbers. Decision
> rule: the under-weighting finding "survives" if readers' follow rate on J_scaled stays >= 2x chance with CI lower bound
> above the random arm at alpha 1, while the model's flip rate stays as in F2-2. Shared misses "survive" if the
> all-three-same-miss rate exceeds the independence product with CI.
> S8b. Three-way error test. On X3 ERROR items, score each reader over {model's wrong answer, correct answer, one
> distractor of the same type}. Report the share choosing each, per reader, Wilson CIs, chance 1/3. Decision rule:
> "readers track the task" if correct > model-answer and > distractor with non-overlapping CIs; "track the model" if the
> reverse; else mixed.

Operationalisation (fixed now):
- **Read vectors**: F2-2's cached block-42/44 read-backs (`cache/g_agreement/f2/t2/readvecs.pt`, 1,984 entries: 64 states ×
  arms full / J_scaled / perp_scaled / rand_scaled_0 / rand_scaled_1 / J_only × α {0.25, 0.5, 1, 1.5, 2} + natural);
  X3: the block-42 last-token states of the 297 D3 ERROR puzzles (`cache/g_agreement/states/xpz-*.pt`). No new target
  forward passes beyond loading readers; model flips are F2-2's recorded decodes (unchanged by construction).
- **Candidate sets**: ownership = the 29 distinct names of the 32 X2 ownership pairs (k = 29; chance 3.4%); puzzles =
  the 8 symbols A–H (k = 8; chance 12.5%).
- **Scores** (native, as G1/F2-2): Oracle = summed log p("- X") after its carrier; NLA = mean over the family's
  templates of summed log p(template(X)) after "<explanation>\n" (puzzle templates for X3); J-lens = max cosine over
  single-token variants of X. Pick = argmax over the k candidates; for the J-lens, candidates with no single-token
  variant are excluded from the argmax and the count is reported (a state where the planted/key candidate is
  unscorable is dropped for the J-lens). Readers: J-lens and Oracle at blocks 42 and 44 (F2-2) / 42 (X3); NLA at 42.
- **F2-2 metric**: P(pick = planted candidate = the other version's answer), Wilson 95%, per reader × arm × α; the
  two-candidate number next to it = P(score(planted) > score(own)) from the same scores; random arm = rand_scaled_0 and
  _1 pooled (128 states). **Rule** (per reader, block 42; 44 reported): survives iff at α 1 the J_scaled pick rate ≥ 2/k
  AND its Wilson lower bound > the random arm's pick rate. Headline "survives" iff it holds for all three readers.
  Model flips are F2-2's (J_scaled 0/64 at α 1) by construction.
- **X3 shared misses**: key = the model's wrong answer (X6 D3 convention). Observed = share of ERROR items where all
  three readers pick the same candidate ≠ key (Wilson 95%). Independence product: each candidate gets a role
  (key / correct / start symbol / other symbol on the trace / off-trace; first match in that order); P_r(c) = reader r's
  share of ERROR items picking a candidate of that role ÷ the number of candidates of that role in the item; expected =
  mean over items of Σ_{c≠key} Π_r P_r(c). **Survives** iff the observed Wilson lower bound > expected. The 138 S7
  shared-wrong items are reported as a subset, not used in the rule.
- **S8b**: three candidates {model's answer, correct, distractor}, distractor = the first symbol of the item's
  `source.distractors` (trace symbols) that is neither; restricted argmax of the same scores. Share choosing each,
  Wilson 95%. "Tracks the task" iff the correct share's interval lies wholly above both others; "tracks the model" iff
  the model-answer share's interval lies wholly above both others; else "mixed".
- Cap 2.5 GPU-h; outputs `results/g_agreement/s8/{s8.md, s8.csv}`.

### S8 Deviations
- 2026-10-16 11:53 CEST (commit bc1bf4f; first written as "12:05", corrected) — **amendment from Guiv's revised brief, written before any S8b/S8a reader number** (S7 chat runs S8; cap 2.5 GPU-h;
  order S8b then S8a). Brief as given (verbatim):
  > S8b FIRST. Three-way scoring on the 297 X3 ERROR items. Candidates per item: (m) the model's own wrong answer, (c) the task-correct answer,
  > (d) a distractor of the same type not in the prompt chain. Readers: J-lens, Oracle, NLA; probe as reference. Layers 42, 48, 52, 56 for J-lens
  > and Oracle (NLA 42 only). Native log-probs over the three; report the share choosing each, Wilson CIs, chance 1/3, per layer. Also free-text
  > readouts (1 sample) at 42 and 56, scored by rule-v1 into m / c / d / none. Decision rule, per reader and layer: "tracks the model" if m > c and
  > m > d with non-overlapping CIs; "tracks the prompt" if c > m and c > d likewise; "neither" if none of these or if free text is mostly "none".
  > S8a SECOND. Full-candidate rescoring of F2-2 (ownership split: J_scaled / perp_scaled / random, alpha 0.25-2): each reader's native log-probs
  > over all candidate names in the item, not two. Chance 1/k. Decision rule: finding 1 survives if the readers' follow rate on J_scaled stays
  > >= 2x chance with CI lower bound above the random arm at alpha 1.

  This replaces the S8b section above where they differ:
  - **States**: Y1 captures (`cache/g_agreement/y/y1_caps/<id>.pt`, label "0" = last prompt token) at blocks 42, 48, 52, 56. J-lens reads its
    own block; the Oracle gets the block number in its carrier prompt (as all earlier Oracle reads); NLA at 42 only.
  - **Distractor (d)**: a symbol from A–H that is not on the item's trace (start, intermediates, correct answer) and is not the model's answer;
    among those, one that is mentioned in the prompt text if any (an off-chain prompt symbol, so mere mention is controlled), else any;
    chosen by a seeded RNG (seed = sha256 of the item id). Whether d is mentioned in the prompt is recorded per item.
  - **Native three-way**: argmax of the reader's native score over {m, c, d} (Oracle summed log p("- X"); NLA mean over the puzzle templates;
    J-lens max cosine over single-token variants). Probe (reference): 5-fold L2 multinomial logistic over A–H on the 400 puzzle states
    (ERROR + ERROR_CONTROL) at that block, label = model's answer (X6 recipe), restricted argmax over the three. Share choosing each, Wilson 95%.
  - **Free text** (1 sample, wsbench sampling, seed fixed per item × layer): Oracle and NLA generations, J-lens top-10 tokens, at 42 and 56
    (NLA 42 only). Scored with rule-v1 primitives: a readout asserts x ∈ {m, c, d} if `_answer_patterns(text, x)` matches (Oracle/NLA) or a
    top-10 token matches x exactly (J-lens, `_token_matches`). Exactly one asserted → that label; none → "none"; ≥ 2 → "multiple".
    "Mostly none" = none + multiple > 50% of items.
  - **Verdict per reader × layer**: "tracks the model" iff the m share's Wilson interval lies wholly above both c's and d's; "tracks the prompt"
    iff c's lies wholly above m's and d's; otherwise, or if that layer's free text is mostly none (where free text exists), "neither".
  - **S8a**: F2-2 only (the X3 shared-miss part of S8a is dropped from the rule; reported descriptively if time allows). Ownership items name
    only 2 people, so "all candidate names in the item" is read as the bank's name set (k = 29, as above). Arms J_scaled, perp_scaled,
    random (rand_scaled_0 + _1 pooled) at α 0.25–2, plus natural; rule unchanged (α 1, block 42, all three readers).
  - 2026-10-16 12:55 CEST (Opus chat that wrote the original S8 section): a second S8 run under the ORIGINAL section started
    on pod mats-minis-v7c at 11:28 CEST, before this amendment (scores over all candidates for the F2-2 read-backs at
    42/44 and NLA 42, and A–H for the 297 X3 ERROR states at 42). Its S8a F2-2 part uses the same rule as the amendment
    (k = 29, J_scaled vs random at α 1, block 42, all three readers). To avoid clobbering the amended run, its outputs
    go to `results/g_agreement/s8/fullcand/` and `cache/g_agreement/s8_fullcand/`; the amended run owns
    `results/g_agreement/s8/{s8.md, s8.csv}`. Its X3 eight-way / trace-distractor numbers are descriptive only.
  - Disclosure: before this amendment the S7 chat computed J-lens cosines over A–H at block 42 on the 297 ERROR items (S8a J-lens staging,
    not committed) and saw that the J-lens 8-way argmax is the model's answer on 35/297, the correct answer on 23/297. No three-way,
    Oracle, NLA or other-layer number was seen.

## S9. Baselines for the error benchmark (pre-registered 2026-10-16, before any S9 number)

Brief as given (verbatim, condensed): for the 297 X3 ERROR items, (a) a prompt-only baseline: an LLM via OpenRouter (the
same judge model as rule-v1's judge, temperature 0) sees only the prompt and answers; share of m / c / other with Wilson
CIs; stop on a 402. (b) Black-box baseline: the target's greedy answer is m by definition; also its answer to "what would
you answer?" with thinking on, if cached from X3, else "not run". (c) Reader scores beyond prompt-only: for each reader ×
layer in `results/g_agreement/s8/s8.csv`, P(reader picks m) − P(prompt-only picks m), paired bootstrap CI.

Operationalisation (fixed now; no GPU):
- **Items**: `dataset/items_x3_selected.json`, set `error` (n 297). m = the model's greedy answer (`x3_target.jsonl`
  `parsed`), c = `primary.correct`; m ≠ c on every item by construction.
- **(a) Prompt-only.** Model `google/gemini-3.8-flash` (the answer judge paired with rule-v1, `w_claims/judge.py`
  `JUDGE_MODEL`; rule-v1 itself is deterministic and has no LLM), same call settings as that wrapper: temperature 0,
  `reasoning.effort = minimal`, no system prompt, one user turn = the item's `prompt_text` verbatim (the exact text the
  target saw), `max_tokens` 64, no response schema. Parsed with X3's `parse_symbol` (the rule used for the target).
  Class: m if parsed = m; c if parsed = c; other = any other symbol or unparseable (unparseable count reported
  separately). Shares with Wilson 95%. Transient errors retried 4×; an item still failing is counted and excluded
  (reported). HTTP 402 → stop, report, no partial result. One call per item, cached on disk.
- **(b) Black-box.** P(greedy = m) = 297/297 by definition (reported as the ceiling a black-box reader of the output
  attains). Self-report with thinking on: X3 recorded a prompt-only self-guess only for CHOICE items; no puzzle item has a
  cached thinking-on "what would you answer?" output (checked: no `xpz-*` row in any cache other than greedy targets,
  reader LOs, logit lens and Oracle free text) → **not run**.
- **(c) Beyond prompt-only.** Reader picks from S8's per-item native scores (`cache/g_agreement/s8/` X3 rows), for every
  reader × layer present on X3 rows in `s8.csv`. Primary: the 8-way S8a pick (argmax over A–H); secondary: the S8b
  three-way pick {m, c, distractor}. Statistic per reader × layer: Δ = P(reader pick = m) − P(prompt-only = m), over the
  items both have (prompt-only failures and J-lens-unscorable items dropped pairwise; counts reported). 95% CI by paired
  item bootstrap (10,000 resamples, seed 0, percentile). A reader reads the model **beyond prompt-only** iff the CI lower
  bound > 0; **below** iff the upper bound < 0; else not distinguishable. If `s8.csv` does not exist when (a) and (b) are
  done, poll every 10 min; (c) is filled in when it lands.
- Outputs: `results/g_agreement/s9/{s9.md, s9.csv}`; code `projects/g_agreement/s9_baselines/`.

### S9 Deviations
1. 2026-10-16, after the first (a) run, before (c): with `max_tokens` 64, 70/297 Gemini responses were empty (finish within the cap, reasoning tokens consumed the budget; the other 227 were 215 c / 9 other / 3 m). Empty is a budget artefact, not an answer, so the primary (a) run uses `max_tokens` 2000 (the wrapper `w_claims/judge.py`'s own value), everything else unchanged. The 64-token run is kept and reported as a secondary row.
2. 2026-10-16 ~12:20 CEST, before any S8 file exists: S8 was amended (bc1bf4f): X3 is now three-way only, d = an off-chain symbol (seeded per item), layers 42/48/52/56 (NLA 42), plus 1-sample free text at 42/56 labelled m / c / d / none / multiple. S9 (c) follows S8 as run: **primary** = S8's native three-way pick {m, c, d} per reader × layer, using S8's per-item d (taken from S8's per-item output; recomputed with S8's rule only if S8 does not record it); **secondary** = S8's free-text label (P(label = m)), and the 8-way A–H argmax wherever S8 records full A–H scores for X3 (descriptive). Statistic, bootstrap and verdict thresholds unchanged. Disclosure: while testing the S9 pipeline on S8's then-partial cache (J-lens block 42 only), this chat saw J-lens L42 picking m on 35/297 items (8-way) and 101/297 (three-way with the old trace distractor); no other reader, layer, or the amended-d three-way was seen.


## S6b. Qwen3-4B step zero on a single-token bank (pre-registered 2026-10-16 12:50 CEST, before any S6b number)

Brief as given (verbatim): "pre-register S6b (rebuild the Qwen3-4B G1-style bank using only names/symbols that are single
tokens in the Qwen3 tokenizer, same families and 8 states each; same reader setup and the unchanged step-zero rule: win
>= 7/8 states on >= 3 of 4 families). Run with J-lens and Oracle; NLA substitute reported separately as exploratory.
Cap 0.5 GPU-h."

Operationalisation (fixed now): bank = `projects/g_agreement/f2/s6b_items.json` built by `f2/s6b_bank.py` from the 32 G1
test items: language and tense unchanged; in ownership and mapping every candidate without a single-token variant
(`scoring_lo.token_variants`, the J-lens rule) is replaced in both versions of the pair, everywhere in the prompt, by the
first single-token, unused word of a fixed list (5 swaps: own-03 Farah→Anna, Kenji→Mark; own-04 Nadia→Anna; own-05
Priya→Anna; map-02 blif→zap). Templates unchanged. Same target, layers (22/24/26), readers, seeds, scoring and rule as
S6 step zero (`f2/s6_step0.py --items f2/s6b_items.json --out s6b`). Verdict counts J-lens and Oracle only: GO iff both
read the key at block 24 (≥ 7/8 states on ≥ 3 of 4 families); NLA substitute reported, exploratory. Target accuracy
on the new bank is reported (a changed name could change the model's answer). Output `results/g_agreement/s6/s6b.md`.

### S6b Deviations
(none yet)
