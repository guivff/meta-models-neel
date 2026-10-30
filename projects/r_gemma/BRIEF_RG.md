# BRIEF_RG — Phase R stretch (a): a second model with an SAE column (Gemma-2-9B-it)

Pre-registered 2026-10-18 (WS9, PLAN_R §10) **before any GPU compute**. Companion to `BRIEF_R.md`: same questions
Q1 (value without labels), Q2 (beyond the text) and Q7 (agreement), same quiver, same controls, same statistics
(`common/stats.py`, `r_bench/analyze.py`), the same 113 datasets and the same splits (`r_bench.bank`, seed 20261019,
test 200 / pool 512 per fact). What changes is the model and the reader set. Code: `projects/r_gemma/`. Results:
`results/g_agreement/rg/`. Cache: `cache/g_agreement/rg/`. Deviations go under §9 with a date.

## 0. Why this model, and the one design conflict it carries

Kantamneni, Engels et al. (arXiv 2502.16681) ran their 113 datasets on **Gemma-2-9B (base)** at the residual stream
after block 20 (`blocks.20.hook_resid_post`), last token of the raw prompt, with Gemma Scope JumpReLU SAEs
(`google/gemma-scope-9b-pt-res`). The only released activation oracle for this model family and size (Karvonen et al.,
arXiv 2512.15674; HF collection `adamkarvonen/activation-oracles`) is trained on **Gemma-2-9B-it**:
`adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_gemma-2-9b-it` @ `44b5056006a4e14b9bb6fa99a98cf6e2bc86fcdf`
(LoRA r 64 / α 128 on q,k,v,o,gate,up,down; `ao_config.json`: `model_name: google/gemma-2-9b-it`, `hook_onto_layer: 1`,
`special_token: " ?"`, `prefix_template: "Layer: {layer}\n{special_token} * {num_positions} \n"`, activations taken at
25/50/75 % depth = blocks **10 / 21 / 31**). There is no base-model oracle. Decision, taken before compute:

- **Target = `google/gemma-2-9b-it`** @ `11c9b309abf73637e4b6f9a3fa1e92e615547819` (bf16, eager attention, 42 blocks,
  d = 3584). The oracle's own model; the SAE paper's model is its base.
- **SAEs = Gemma Scope *pt* SAEs applied to the -it states** (the Gemma Scope card: base SAEs "transfer very well" to
  the IT model), plus one *it* SAE as the robustness column. The transfer is measured, not assumed: the fraction of
  variance explained (FVE) of every SAE on our block-20 states is reported next to its probe numbers (no gate; the
  quiver decides whether the column is useful, as in the paper).
- The AO reads **on-grid at block 21** (its 50 % site; primary) and **off-grid at block 20** (the SAE site; the same
  one-block offset as Qwen's Oracle at 42 vs 44). Blocks 10 and 31 (on-grid) complete the sweep in the chat render.

Everything else follows BRIEF_R so that the Gemma blind-spot map sits next to Qwen's with the same rows.

## 1. Hypotheses (BRIEF_R §1, restated for this model; decision rules in §5)

H1-G (value without labels). Median n* ≤ 8 for the AO on SURFACE ∪ TOPIC ∪ FORM, and the quiver gain from adding the
zero-shot readers (AO, logit lens) is < +0.01 AUC at every n ≥ 16.
H1-S (the paper's result, replicated inside the same quiver). Adding SAE probes (k = 16, 128) to the probe set gives
ΔAUC(n) < +0.01 at every n ≥ 16, and the CI includes 0 at every n (Kantamneni et al.: SAE probes do not beat the
baseline quiver; their data-scarcity setting is the n ≤ 32 end of our grid).
H2-G (ceiling). The AO never exceeds the prompt-only ceiling on SURFACE/TOPIC/FORM/COMPUTED; on KNOWLEDGE the AO reaches
≥ 0.8 × probe(512) AUROC on ≥ half the facts.
H7-G (agreement). P(correct | AO forms and logit lens agree) − P(correct | best single) ≤ +2 points; the shared-error
ratio ≥ 1.5× independence.
No H3–H6: no conflict selection, no steering, no k-way on this model in this stretch (listed as not run, §8).

## 2. Methods

### 2.1 Readers and references (per item; native log-odds only)
| column | site | score |
|---|---|---|
| **AO** (candidate form, primary) | blocks 21 (primary), 20; 10, 31 chat only | user turn = `"Layer: {L}\n ? \n"` + the dataset question + `Answer with exactly one of these two options and nothing else: "{pos}" or "{neg}".`; the activation is ADDED at the ` ?` position at the output of block 1, unit-normalised and rescaled to that position's residual norm (coefficient 1.0, the repo's HF hook); the candidate is teacher-forced as the assistant turn; s_pos = Σ lp(pos tokens), s_neg likewise, LO = s_pos − s_neg; both candidates of a state in the same forward batch |
| **AO-yn** (training-native yes/no form) | same | question = `Answer with 'Yes' or 'No' only. Is this statement about the text true: "{template(X)}"?` for X = pos and X = neg; s_X = lp(Yes) − lp(No) at the assistant onset; LO = s_pos − s_neg |
| **logit lens** | every captured block | final norm (+ Gemma's logit soft-capping) + W_U: lp(first token of pos) − lp(first token of neg), first tokens by the Y1 convention (first spelling whose first tokens differ; `jlens_*` short forms as the fallback; else unscorable) |
| **probe LR(n)** | block 20 (primary), every captured block at n = 512 | `analyze.probe_fit_select`: standardised L2 logistic regression, inner-CV C ∈ {0.01, 0.1, 1, 10}, the paper's validation scheme (`_cv_splits`), n ∈ {2, …, 512}, 5 seeds |
| **probe MM(n)** (mass-mean, IDEAS_R §1 lesson 6) | block 20 | d = mean(pos) − mean(neg) on the n training items, score = h·d; validation AUC on the same folds; no hyperparameters |
| **SAE probe(n, k)** (Kantamneni et al. recipe, `train_sae_probes.py`) | block 20 | latents z = JumpReLU(h W_enc + b_enc, θ); each latent divided by its mean over its non-zero training entries; top-k latents by \|mean(z \| y = 1) − mean(z \| y = 0)\| on the training items; L1 logistic regression (saga, max_iter 1000) on the k raw latents, C ∈ logspace(5, −5, 10) by the same validation scheme; k ∈ {16, 128} |
| **prompt-only** | — | `PROMPT_ONLY_FC_TEMPLATE` (frozen in `r_bench/datasets.py`) as the user turn, LO = lp(pos) − lp(neg) teacher-forced after `<start_of_turn>model\n`; its AUROC is the model-report ceiling |
| **controls** | AO at every site | shuffled (seeded derangement of the test states; AUROC must be in [0.45, 0.55]), state-free (dataset-mean state; the AO's candidate prior) |

Primary AO score: LO for two-sided facts, s_pos for one-sided facts (BRIEF_R §2.1). Cross-dataset comparisons use
AUROC only.

SAEs (all at block 20 = `hook_resid_post` 20, the paper's site), `params.npz` from the Gemma Scope repos:
| tag | repo | path | role |
|---|---|---|---|
| `sae16` | `google/gemma-scope-9b-pt-res` | `layer_20/width_16k/average_l0_408` | **primary**: the 16k SAE the paper fixes for its data-scarcity / imbalance / noise / OOD settings |
| `sae131` | `google/gemma-scope-9b-pt-res` | `layer_20/width_131k/average_l0_276` | the paper's 131k SAE for the same settings |
| `sae16c` | `google/gemma-scope-9b-pt-res` | `layer_20/width_16k/average_l0_68` | the SAELens "canonical" 16k SAE |
| `sae16it` | `google/gemma-scope-9b-it-res` | `layer_20/width_16k/average_l0_189` | the IT-model SAE chosen by the paper's rule (largest L0 at 16k) |
Repo revisions are pinned in `r_gemma/config.py` at the time of the freeze (`--freeze-rg` records them).

### 2.2 Capture (`r_gemma/collect.py --phase A`)
Blocks **9, 10, 20, 21, 31, 41** (the paper's 9/20/31/41 and the AO's 10/21/31), last token, both renders, fp16, per
dataset, test items first then pool. Renders as BRIEF_R: `chat` = the text as the user turn, generation prompt
appended, read at the assistant onset (the last token of `<start_of_turn>model\n`); `raw` = `<bos>` + the bare text,
read at its last text token (the paper's site; Gemma keeps `<bos>`, Qwen has none). Texts are cut to 256 text tokens
before rendering (BRIEF_R's rule, so the two models see the same tokens; the paper truncated at 1024 from the left —
recorded as a difference, not a deviation). Batched capture with right padding and an attention mask, adapter
disabled; logit-lens rows in the same forward; prompt-only on every item. The AO's native LO on the 200 test items of
every dataset at blocks 20 and 21 in both renders, 10 and 31 in chat, with the shuffled and state-free controls, and
on 64 balanced pool items (32 per class) at the primary site (the quiver's labelled pool). `--phase S` encodes the
block-20 states of every item with each SAE and saves the latents as sparse matrices per (dataset, render, sae) plus
the FVE row.

### 2.3 The quiver (BRIEF_R §2.3, two reader families side by side)
Arrow sets, per fact, n and seed, chosen by validation AUC, reported by test AUC on the fixed test split:
- **P** (probes only) = {LR(n), MM(n)} — the baseline. (BRIEF_R's probes-only set is LR alone; MM is added per IDEAS_R
  lesson 6; the ΔAUC against LR alone is reported as a secondary line.)
- **P + AO** = P ∪ {AO zero-shot, AO-yn zero-shot, logit lens zero-shot, each stacked with LR(n) for n ≥ 8}.
- **P + SAE** = P ∪ {SAE probe(n, 16), SAE probe(n, 128) for each SAE}.
- **P + AO + SAE** = everything.
ΔAUC_AO(n) = best(P + AO) − best(P), ΔAUC_SAE(n) likewise, ΔAUC_all(n); mean over facts, 1,000-resample fact bootstrap
CI (`analyze.quiver_summary`). "Adds value at n" iff the CI excludes 0 and the mean ≥ +0.01.

### 2.4 n*, ceiling, agreement
As BRIEF_R §4.1, §4.2, §4.7 through the imported functions `nstar_table`, `r2_ceiling`, `shuffled_check`,
`r7_agreement` (readers in the vote: AO, AO-yn, logit lens; votes = score above the dataset's test median).

## 3. Bank
`dataset/items_r.json` built by `r_bench.bank --build` from `cache/g_agreement/r/cleaned_data/` with WS1's hardened
spec (113 facts, 77,418 items; taxonomy SURFACE 28, TOPIC 26, KNOWLEDGE 21, COMPUTED 17, PASSAGE-KNOWLEDGE 9, FORM 6,
META 6; WS1 re-tagged Wikidata 56–64 PASSAGE-KNOWLEDGE because the attribute is in the passage). The Gemma run uses
**the same items file as the Qwen run** (sha recorded in `manifest/frozen_config_rg.json`; if WS1/WS2 re-freeze the
bank before the Gemma full run, the Gemma collector is re-pointed at the frozen file and the sha updated under §9).
For H2-G, KNOWLEDGE means the KNOWLEDGE tag (bare-entity prompts); PASSAGE-KNOWLEDGE is reported as its own row.

## 4. Figures and tables (`results/g_agreement/rg/`)
- `cells.csv` (AUROC per fact × method × block × render × condition, CIs, coverage), `learning_curves.csv` (LR, MM,
  SAE probes per n × seed), `quiver.csv` + `quiver_summary.csv` (three Δ lines), `nstar.csv`, `ceiling.csv`,
  `agreement.csv`, `sae_fve.csv`, `summary.md`.
- FG1 headline: AO AUROC vs probe(512) per fact (colour = tag), AO vs prompt-only, n* boxplot (reuses `fig1_headline`).
- **FG2 quiver**: ΔAUC_AO(n), ΔAUC_SAE(n), ΔAUC_all(n) with CIs on one axis; which arrow wins per n.
- **FG3 blind-spot map, Gemma next to Qwen**: rows = the 113 facts (grouped by tag, sorted by Gemma's probe(512)),
  Gemma columns = probe LR, probe MM, prompt-only, AO@21, AO@20, AO-yn@21, logit lens@20, SAE16-k16, SAE16-k128,
  SAE131-k16, SAE131-k128; Qwen columns = `results/g_agreement/r/cells.csv` + `learning_curves.csv` (WS3) at their
  primary sites when present, else the Qwen panel is blank and labelled "pending WS2/WS3".

## 5. Decision rules
- H1-G supported iff median n*(AO@21, chat) ≤ 8 on SURFACE ∪ TOPIC ∪ FORM and ΔAUC_AO(n) < +0.01 for all n ≥ 16.
- H1-S supported iff ΔAUC_SAE(n) < +0.01 for all n ≥ 16 and its CI includes 0 at every n. Reported separately per SAE
  (`sae16` is the headline; the others are robustness rows).
- H2-G supported iff zero exceedances (AO − prompt-only ≥ +0.05 with CI > 0) in SURFACE/TOPIC/FORM/COMPUTED and AO@21
  ≥ 0.8 × probe(512) on ≥ half the KNOWLEDGE facts. Shuffled control in [0.45, 0.55] on ≥ 95 % of cells, else a bug.
- H7-G as stated in §1 (consensus gain ≤ +0.02; shared-wrong ratio ≥ 1.5).
- Paired reader differences by exact sign tests on identical facts; nothing ranked by CI overlap.
- **Inferential rules inherited from BRIEF_R §4.9** (added 2026-10-18 07:00, before compute, after reading the ideation
  sprint's HANDOFF "Pre-freeze" section): (b) per-fact R2 exceedances go through Benjamini–Hochberg at q = 0.10 per reader;
  (d) every hypothesis above is stated four ways — SUPPORTED (95 % CI past the threshold on the predicted side), REFUTED,
  EQUIVALENT-NULL (90 % CI inside the margin) or UNDERPOWERED — with margins ±0.01 AUC on ΔAUC(n), ±2 on median n*, 0.05 on
  the H2 exceedance, ±2 points on the H7 consensus gain; the minimum detectable effects are printed next to each rule;
  (h) the mass-mean probe is the second PRESENT reference (already in §2.1); (j) headline means over facts carry the
  two-stage corpus → dataset → item bootstrap next to the i.i.d. fact bootstrap, the wider CI quoted. The four-way
  verdicts, BH and the corpus bootstrap are implemented in `r_gemma/analyze.py` once the first pod run is under way
  (Guiv, 2026-10-18); until then `summary.md` prints the two-way verdicts of the rules above, labelled as such.

## 6. Compute (one pod, H100 80 GB, budget 2 pod-h; hard stop 3)
Target 9B bf16 ≈ 18.5 GB + LoRA; capture 113 × 712 × 2 renders × 6 blocks ≈ 161k forwards of ≤ 300 tokens at batch
16 ≈ 15 min; prompt-only 113 × 712 × 2 candidates ≈ 10 min; AO LO 113 × (200 test + 200 shuffled + 64 pool) × 2 forms ×
(2 blocks × 2 renders + 2 chat) ≈ 1.3 M teacher-forced rows ≈ 45 min; SAE encoding ≈ 5 min (GPU) / 30 min (Mac CPU).
Smoke first on `92_glue_sst2` and `66_living-room` (`--allow-unfrozen`, writes to `cache/g_agreement/rg_unfrozen/`),
then `--freeze-rg`, then the full phases A and S. CPU (Mac): learning curves 113 × 9 × 5 × (LR + MM + 8 SAE arrows),
`--n-jobs 8`, ≈ 1–2 h. Every run appends to `results/g_agreement/rg/log.md` and the compute ledger (module `rg`).

## 7. Checks before the first look at test rows (pod, in `tests/test_rg_collect.py -k pod`)
1. Batched capture == single-item forward at every captured block, both renders (cos ≥ 0.9999 on 4 items).
2. `teacher_forced_lp` == per-row single forward (|Δ| < 1e-3).
3. AO liveness: with the adapter on, the oracle answers a known positive-control state (an SST-2 test item read at
   block 21) in the right direction on ≥ 3 of 4 items; the hook fires exactly once per forward; the ` ?` placeholder is
   one token and sits where `find_pattern` says.
4. SAE sanity: the JumpReLU encode of a batch reproduces `sae_lens` if installed (else the formula is checked against
   the shipped `threshold` semantics: pre-activation ≤ θ → 0); FVE on block-20 states reported (expected ≈ 0.7–0.9 for
   the pt SAEs on -it states; any SAE with FVE < 0.3 is flagged, still run).
Any failing check stops the run; the fix is logged before compute resumes.

## 8. Not run in this stretch (listed so nobody mistakes an absence for a negative)
R-B k-way, R-C conflicts, R5 steering, R-D legacy rows, free-text case studies, the raw-render AO at blocks 10/31.

## 10. Ideation items for WS9 (BD-8 of `results/g_agreement/r/ideation/benchmark_design.md`, red-team FIX), pre-registered 2026-10-18 07:20, coded after the first pod run starts

The ideation sprint's one WS9 design is BD-8, "second-model mini-replication sized by power", with the red team's fix. It is
written down here before any Gemma compute and implemented in `r_gemma/analyze.py` (CPU) and, for the two new arms, in
`r_gemma/collect.py` only once pod G is running (Guiv's instruction). Nothing in §1–§5 changes.
- **Cross-model claim (BD-8.1 + fix).** Per fact, the ratio ρ_f = AUROC_reader / AUROC_probe(512) on Qwen (Oracle at 44,
  WS3's `cells.csv`) and on Gemma (AO at 21). Rule: **within-tag** Spearman between the two ratio vectors with the Gemma
  probe(512) AUROC partialled out (residuals of ρ on probe AUROC within tag), fact bootstrap CI; REPLICATES iff the pooled
  within-tag Spearman ≥ 0.5 with CI > 0 **and** the tag ordering of the median ratio is identical **and** the Gemma quiver's
  ΔAUC_AO(n) is within ±0.02 of Qwen's at n ∈ {8, 32}; PARTIAL iff the Spearman holds and one of the other two fails; else
  NULL (the blind-spot map is model-specific, stated first). The red team's objection (difficulty alone yields Spearman ≥ 0.5)
  is what the within-tag, probe-partialled form answers.
- **Sizing (BD-8.2).** On Qwen's 113 facts, resample tag-stratified subsets of size k ∈ {20, 30, 40, 60} (1,000 draws); k* =
  the smallest k at which ≥ 80 % of draws reproduce Qwen's tag ordering and H1 verdict. The Gemma full run covers all 113
  facts regardless (the quiver needs them); k* is reported as the size at which the replication would have been decidable,
  and the BD-8 rule is evaluated on all facts and on the k* subset that WS3's resampling names.
- **Random-rotation control (BD-8.4).** The J-lens does not exist for Gemma; its random-rotation control (IDEAS_R E13) is
  replaced by a random linear readout through Gemma's unembedding: the logit lens applied to R h for a seeded random
  orthogonal R (10 seeds), scored like the logit lens. Expected ≈ 0.5; a column in `cells.csv` named `logit_lens_rot`.
- **No-activation AO arm (BD-8.4; the Li control, BD-7).** The AO prompt with the text rendered into the user turn in place
  of the ` ?` placeholder and the hook disabled; scored in both forms on the 200 test items at the primary site; reported
  next to the AO row as `ao_noact` (what the oracle gets from the text alone). ≈ 10 pod-min on R-A.
- **Verified before booking the hour (red-team fix):** the released oracle's base is `google/gemma-2-9b-it` (§0), so the
  target is -it and the SAE transfer is measured by FVE (§2.1). Done 2026-10-18 before this file was written.

## 11. Follow-ups after the first read (Guiv, 2026-10-19), pre-registered 2026-10-18 23:03Z (01:03 CEST, commit 60ba0bc) before any compute (first collector line on pod rG 23:17:56Z); one pod, `RG_SELF_STOP=1`

**(c) done first, CPU (`check_c_passage_truncation.csv`).** For the five PASSAGE-KNOWLEDGE facts where the activation beat the text at the
raw site (56, 57, 58, 59, 62; Δ −0.075 … −0.180, item CIs < 0): no test item is truncated (raw render 121 tokens median, 184 max, cap
256); the text-only oracle prompt is ≤ 243 tokens against the oracle's 512-token training `max_length`; the passages are 506–561 characters
(median) and often do not name the person the question asks about. The advantage is not a length artefact; it is reported as is in (a).

**(a) Text + activation.** New arm `ao_textact` (candidate form) and `ao_yn_textact` (yes/no form): the oracle prompt keeps the ` ?`
placeholder with the activation added at it (block-1 hook as §2.1) AND carries the item's text after the prefix:
`"Layer: {L}\n ? \n{text}\n{question}"` (text cut to 256 tokens as everywhere). Activation = the block-21 state of the chat render and,
separately, of the raw render (two rows per item). Compared item-paired with the text-only arm (`ao_noact`, `ao_yn_noact`; same text, no
placeholder, hook off) on the 200 test items of every fact. Δ_f = AUROC(text + activation) − AUROC(text) per fact with the item bootstrap;
by tag and over all 113 facts the mean Δ with the corpus → dataset bootstrap CI (§5, BRIEF_R §4.9(j)). **Rule: "the activation adds
information" at a site iff mean Δ > 0 with the corpus-clustered 95 % CI excluding 0**, stated per tag and overall, per form, per site.
A fact-level count (facts with item CI > 0 vs < 0) is reported alongside.

**(b) Position sweep.** Chat render, every token from the last text token through the chat-template tokens to the assistant onset
(offsets k = K … 0 from the end; K = the length of `<end_of_turn>\n<start_of_turn>model\n` in tokens, 5 if the template tokenises as
written — recorded from the tokenizer at run time), at blocks 10 / 21 / 31 (25 / 50 / 75 % depth, the oracle's grid). The AO (candidate
form, "Layer: {L}") reads each (block, offset) on the test items; an LR probe (`analyze.probe_fit_select`, standardised, inner-CV C, the
paper's validation scheme) is fitted on the pool at the same (block, offset) and scored on the test items. Reported: AUROC by offset for
both, per tag and overall, at the three blocks (figure FG4). **Rule: "information present but unread" at (block, offset, fact) iff probe
AUROC ≥ 0.85 and probe − AO ≥ 0.10 with the item-paired bootstrap CI excluding 0**; the headline is the count of such facts per (block,
offset) and the offset at which it is largest. Offset 0 at block 21 must reproduce the main run's AO@21 chat cell (sanity).
Controls: none beyond the main run's (same states; the AO's shuffled control at offset 0 exists); the probe uses pool items only.

**Compute.** (a) 4 arms × 113 facts × 200 items ≈ 35 min; (b) capture 3 blocks × (K + 1) offsets on 77,418 items ≈ 10 min, AO 18 cells
≈ 35 min, probes on the pod CPU ≈ 30 min (overlapping); ≈ 1.5–2 pod-h with downloads (the pod's container disk is wiped on stop).
Outputs: `reader_lo_textact.jsonl`, `reader_lo_pos.jsonl`, `pos_probe.jsonl` (per-item probe scores per cell), `states_pos/` (fp16; pulled
if time allows), analysis `r_gemma/followup.py` → `results/g_agreement/rg/followup_{a,b}.csv`, `fig/FG4_positions.png`, report §9.

## 12. FT-3 / D3 — label-free positional repair of the released Gemma AO (pre-registered 2026-10-19 17:44Z (19:44 CEST) before any map is fitted)

Source: `origin/r/ideation-2:results/g_agreement/r/ideation2/SYNTHESIS.md` §D3 / FT-3 and `red_team.md` (FT-3 row and the 28,800-row cost line),
commissioned by Guiv 2026-10-19. Thresholds are the design's, unchanged. Where the design leaves an operational choice open it is fixed here,
before any fitting, and marked *(fixed here)*.

**Claim tested.** Most of the Gemma AO's role-token failure is a reusable change of readout coordinates rather than loss of the item's
information: a label-free map fitted on other corpora, from role-token states to last-text-token states, makes the released AO read the
role-token state almost as well as the last-text-token state.

**States (existing, no new capture).** `cache/g_agreement/rg/states_pos/<fact>/chat_L21_k{1,5}.npy` from the §11b position sweep: block 21,
chat render; **role token = offset 1, the `model` token** (the ideation-2 site-gap site: AO .915 → .753, LR .966 → .933 over 108 facts);
**last text token = offset 5**. Both come from the same forward of the same item, so they are paired.

**Facts (frozen by the design, not selected on AO gains).** `49_cm_isshort`, `65_high-school`, `158_code_C`, `161_agnews_0`, `5_hist_fig_ismale`,
`114_nyc_borough_Manhattan`, `117_us_state_FL`, `123_world_country_United_Kingdom`, `36_sciq_tf`, `129_arith_mc_A`, `21_headline_istrump`,
`92_glue_sst2`. Availability verified before this section was written: all twelve have 512 pool (256/256) and 200 test (100/100) items with both
offsets present; no stratum is missing, no replacement.

**Splits.** Per fact the 512 pool items are split label-free by a seeded permutation (seed 20261019 + fact number) into **448 fitting** and **64
reserved** items *(fixed here: label-free draw, not class-balanced)*. Test = the fact's 200 test items, never used for fitting or selection.

**Corpus holdout *(fixed here)*.** Corpora follow BRIEF_R §4.9(j) via `r_gemma.inference.corpus_of`; the twelve facts fall in nine groups:
{114, 117, 123} world-model places, {158, 161} code (BRIEF_R's 158–163 range), and seven singletons (49, 65, 5, 36, 129, 21, 92). **Every
map is fitted leave-one-corpus-group-out** on the 448-item fitting pools of the other groups' facts and applied only to the held-out group's
facts. All transport numbers below are therefore held-out-corpus numbers; this is how "hold whole source corpora out for transport
evaluation" is realised with the design's six native arms (no seventh arm).

**Map.** `f(h) = h + mu_text − mu_role + (h − mu_role) B_r`, `B_r` = rank-r reduced-rank ridge regression of the residual target
`(h_text − mu_text) − (h_role − mu_role)` on `(h_role − mu_role)` over the fitting items, i.e. ridge solution `B = (XᵀX + λI)⁻¹XᵀY` projected onto
the top-r right singular vectors of `XB`; `λ = 10⁻³ · tr(XᵀX)/d` *(fixed here)*; means over the fitting items (label-free). Rank `r ∈ {16, 64, 256}`
chosen per fold by the mean squared reconstruction error `‖f(h_role) − h_text‖²` on the **reserved 64 items of the fitting facts** (never on test,
never on labels).

**The six native arms** (AO candidate form at block 21, prompt "Layer: 21", the native block-1 norm-matched hook — the same normalisation for
every arm; test items; 12 × 200 × 6 × 2 = 28,800 candidate rows):
1. native role (`h_role`, offset 1); 2. native text (`h_text`, offset 5);
3. mean shift (`h_role + mu_text − mu_role`, fold means);
4. norm match (`h_role · mean‖h_text‖ / mean‖h_role‖`, fold means) — the AO hook unit-normalises its input, so this arm is predicted to equal
   arm 1 exactly; it is kept as the design's control and doubles as a pipeline identity check;
5. paired transport (`f` with the fold's selected rank);
6. shuffled-pair transport (same fold, same rank, fitted after a seeded within-fact derangement of the text states).
Calibration replay *(fixed here, ≤ 4,096 rows)*: arms 1 and 2 on the 64 reserved items of every fact (3,072 rows); arms 1 and 2 on test must also
reproduce the §11b `reader_lo_pos` scores for offsets 1 and 5 (identity check, |Δ lo| < 0.05 nats on bf16).

**Primary metric.** Per fact AUROC on its 200 test items (primary score per sidedness, §2.1); macro mean over the 12 facts. Contrasts are paired
by item. CIs by a two-stage bootstrap (corpus groups, then items within fact, 2,000 resamples) *(fixed here)*; **"adjusted"** = simultaneous over
the four CI-bearing contrasts below by Bonferroni, i.e. each one-sided lower bound at level 1 − 0.05/4 *(fixed here)*.

**Decision rule (design thresholds).** REPAIRED iff all of:
- (P1) macro ΔAUC(transport − native role) ≥ **.10** with adjusted 95 % lower bound **> .05**;
- (P2) the site gap closed ≥ **50 %**: [mean AUC(transport) − mean AUC(role)] / [mean AUC(text) − mean AUC(role)] ≥ .50 (point estimate; CI reported);
- (P3) transport beats mean shift by ≥ **.05** with adjusted lower bound **> 0**;
- (P4) transport beats shuffled-pair transport by ≥ **.05** with adjusted lower bound **> 0**;
- (P5) positive on held-out corpora: macro ΔAUC(transport − role) adjusted lower bound > 0 (every fact is already evaluated with its corpus held out;
  the per-group signs are reported).
Otherwise NOT REPAIRED, naming the failing clauses.

**Information-preservation qualifier.** A reference LR probe (`analyze.probe_fit_select`, standardised, inner-CV C, the paper's validation scheme)
is trained per fact on the **native role** fitting items and scored on native-role vs transported test states. If the macro probe ΔAUC is
equivalent to 0 within **±.03** (90 % CI inside [−.03, +.03]), a REPAIRED verdict reads "reader-interface repair with the role-site information
preserved"; otherwise "**output repair without demonstrated information preservation**".

**CPU content checks (secondary, on the same arm tensors; no extra native replay).** (i) Cross-fitted semantic decoders per arm and fact: LR and
mass-mean fitted on that arm's transformed fitting items, tested on its transformed test items. (ii) Recipient vs matched wrong-entity donor
margins: for each test item i, donor j = the test item of the opposite label in the same fact nearest to i in native-role cosine; margin
`(2y_i − 1) · [s(f(h_i)) − s(f(h_j))]` under the reference probe, mean and CI per arm, entity facts (5, 114, 117, 123) reported separately.
(iii) The raw recipient-content confusion table per fact × arm (AO pick vs label). These qualify, they do not replace, the primary verdict.

**Interpretation limits (from the design).** Success is cross-corpus **reader-interface repair**, not an inversion of the model's positional
computation, and not evidence about target use: no target state or behaviour is changed. Mean-only and shuffled controls do not exclude
denoising; the content checks are reported for that reason.

**Compute.** CPU: map fitting and checks (6–12 core-h budget). Pod: one H100, the 28,800 primary + ≤ 4,096 calibration rows, ≈ 0.5–1 h with
downloads; **hard cap 3.5 billed pod-h**. The pod runs `pod_run.sh ft3` with both PODS.md guards armed before the first command (self-stop by
explicit id, hard timeout 10,800 s, idle watchdog 15/45 min), recorded in the first log line. Outputs: `cache/g_agreement/rg/ft3/`,
`reader_lo_ft3.jsonl`; analysis `r_gemma/ft3.py` → `results/g_agreement/rg/ft3_*.csv`, report §10.

## 9. Deviations
- 2026-10-19 02:20Z (04:20 CEST; record-keeping). Earlier stamps in this section and in §11 were CEST values written as "UTC"; corrected to
  true UTC from git commit times (+02:00) and the collector's ISO lines. The ordering pre-registration → compute is unchanged and is
  carried by git: §11 at 60ba0bc (23:03Z) precedes rG's first collector line (23:17:56Z).
- 2026-10-19 01:08Z (03:08 CEST; second label-defect set from WS3; same convention as the 00:18Z note). WS3 found that `101_disease_class.csv` stores
  its medical-abstract classes under permuted names ("cardiovascular diseases" = 81 % cancer terms, "neoplasms" = 75 % digestive, …; only
  "nervous system diseases" is right). `interim.LABEL_DEFECT` (r/ws3-analyze @ b56e14a) now adds `145_disease_class_digestive system diseases`,
  `146_disease_class_cardiovascular diseases` and the parent `101_disease_class`; 147 stays. Applied in r_gemma as a local union until the
  scaffold's `interim.py` carries it; every table regenerated without (primary) and with (`with_label_defect/`) the seven facts. This removes
  the AO-yn exceedance on 146 reported in §4; 108 facts remain in the summaries.
- 2026-10-19 00:55Z (02:55 CEST; BD-8 verdict mapping, §10; reading of the rule, not a change). §10 names REPLICATES / PARTIAL / NULL and does not
  say how a clause that cannot be evaluated (e.g. a missing Qwen table) counts. Commit 9a1f859 fixes the code to count an unevaluable
  clause as failed — so missing inputs can only weaken a verdict, never produce PARTIAL — replacing an earlier code-only "UNDETERMINED"
  label that §10 never defined. Tonight's verdict does not depend on this: both other clauses were evaluated and false (tag ordering
  differs; |ΔAUC_AO − Qwen's| = 0.055 > 0.02 at n = 32), so BD-8 is NULL under either mapping (`bd8.json`).
- 2026-10-19 00:18Z (02:18 CEST; analysis convention adopted from WS3 via the Integrator; no §4/§5 rule changed; the bank stays frozen). The four
  AG News facts with wrong class names (`139_news_class_Politics`, `140_news_class_Technology`, `141_news_class_Entertainment` and the
  parent `97_news_class`) are WS3's post-hoc LABEL_DEFECT set: every WS9 table is produced without them (the primary files in
  `results/g_agreement/rg/`) and with them (`results/g_agreement/rg/with_label_defect/`); they never enter a BH family. The rename I had
  asked WS1 for is cancelled. The learning curves are reused from the frozen-code run (`--reuse-curves`), not refitted.
- 2026-10-19 00:09Z (02:09 CEST; phase T, implementation note; §11a rule unchanged). 4,000 rows in, a text containing the string " ?" made the
  text + activation prompt carry two placeholder tokens and the collector refused the item. Decision: the activation is injected at the
  FIRST placeholder — the prefix's, which precedes the text — and any " ?" inside the text is ordinary text (the oracle's own training
  code asserts exactly one match; our prompts put the text after the prefix, so the first match is always the prefix's). Resumed from the
  4,000 rows already written. Affects only items whose text contains " ?".
- 2026-10-18 22:05Z (00:05 CEST Oct 19; found after the data; no rule changed). The only AO exceedance that survives BH, `140_news_class_Technology`, is a
  label defect of the source data: `97_news_class.csv` names the AG News classes World / Business / Sci-Tech / Sports as Politics /
  Technology / Entertainment / Sport, so facts 139–141 ask the wrong question of their labels. H2-G is reported as pre-registered (REFUTED
  on that cell) and with the two mislabelled facts set aside (first clause holds), the way BRIEF_R §3 treats CoLA's label noise.
- 2026-10-19 00:30 (reading of a rule after the data; the rule itself is unchanged). H1-S says "ΔAUC_SAE(n) < +0.01 at every n ≥ 16 and the
  CI includes 0 at every n". The data give ΔAUC_SAE < 0 with every CI strictly below 0: the first clause holds, the second fails because the
  SAE probes HURT the quiver. The literal two-way reading is therefore "not supported", the four-way reading (§5, BRIEF_R §4.9(d)) is
  SUPPORTED (the CI lies entirely on the predicted side of +0.01). Both are reported; the CI-includes-0 clause was written to catch a
  positive gain hiding inside a wide interval, not to turn a harmful column into a non-result.
- 2026-10-18 08:00 (before the freeze; §2.1 controls, implementation detail). The smoke showed the same shuffled-control permutation
  reused across every (render, layer) cell of a dataset (it was seeded by dataset only), so one unlucky draw (SST-2: 0.57–0.59 at
  every site) would fail the [0.45, 0.55] band in every cell at once. The derangement is now seeded per (dataset, render, layer),
  so the cells are independent draws; the band rule is unchanged.
- 2026-10-18 07:50 (before the freeze, during the smoke; §7.2). The check "`teacher_forced_lp` == per-row single forward, |Δ| < 1e-3"
  was written for a same-dtype comparison. On the real model in bf16 the left-padded batched forward and the single-row forward
  differ by up to 0.06 nats on a −12 nat candidate sum (the batch-composition shift Suraj measured at ≤ 0.26 nats on Qwen); the
  check is therefore run with the model cast to fp32 (|Δ| < 1e-3 required) and the bf16 gap is reported as a number (< 0.3 nats
  required). Both candidates of a state always share one forward, so the LO comparison is unaffected. The capture check (§7.1)
  passed as written (cos ≥ 0.9999 at blocks 9/10/20/21/31/41, both renders).
- 2026-10-18 07:30 (infrastructure, no rule changed). The shared network volume is at its quota; the run uses the pod's container
  disk for the HF cache and `cache/g_agreement/rg/`, synced to the Mac before the pod stops (`pod_run.sh pull-cmd`).
- 2026-10-19 20:11Z (§12 FT-3, before the rerun; no decision rule, threshold, arm or metric changed). Attempt 1 on `mats-minis-f` (18:07:50–19:02:29Z, 0.91 billed h) scored the arms, but the pod stopped before the rows were pulled, so it contributes no rows. No FT-3 test score has been seen. For the rerun, (i) the hard timeout is 7,200 s, not §12's 10,800 s, so the billed total stays under the 3.5 pod-h cap (0.91 + 2.0 ≤ 3.5); (ii) the end-of-job stop is an explicit last step after the Mac's pull (PODS.md item 1 as amended 19:36Z), not an EXIT trap, with `ws2_watchdog.sh` and `ws2_hardstop.sh` from the scaffold; (iii) the chain skips the SAE downloads (`RG_SKIP_SAE=1`; phase F uses no SAE).
