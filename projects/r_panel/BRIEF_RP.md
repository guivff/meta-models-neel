# BRIEF_RP — the standard-reader panel: R-A on Qwen3-8B and Qwen3-32B with author-released activation oracles

Pre-registered 2026-10-19 02:41Z (04:41 CEST), **before any code or GPU compute for this BRIEF**. Bucket: **new-reader work**
(BRIEF_R §7 amendment of 2026-10-19 02:15Z: 200 billed GPU-h, BRIEF required before any spend; nothing has been billed to it yet).
Companion to `BRIEF_R.md` and `projects/r_gemma/BRIEF_RG.md`: **the rules are BRIEF_RG's**, applied to three new
(target, oracle) pairs. Where this file does not say otherwise, BRIEF_RG §1–§11 apply as written, including the dated
readings in its §9. Code: `projects/r_panel/` (to be written; it imports `r_gemma` and `r_bench`). Results:
`results/g_agreement/rp/`. Cache: `cache/g_agreement/rp/`. Ledger module `rp`. Deviations go under §12 with a date.

## 0. Why, and what "standard" means here

Every Phase R reader on Qwen3.6-27B is a **community** checkpoint: the J-lens (`neuronpedia/jacobian-lens`), the Oracle
lens (`agu18dec/olens_and_ar`), the NLA (`ceselder/qwen3.6-27b-nla-rl`) and the skip lenses were trained by third parties
for that model, with no paper that evaluates that checkpoint. A reviewer can therefore read every Phase R negative
("verbalizers ≈ weak zero-shot probes", "the text suffices") as a property of those checkpoints. WS9 answered this once,
for one model (Gemma-2-9B-it with the paper's own AO). This BRIEF adds the paper's own oracles for two more models of one
family at two scales, and the one published improvement on them, so that the tier of the checkpoint becomes a column
and not a caveat.

**Checkpoint tier (applies to every Phase R table from this BRIEF on; §9).**
- **standard** — the checkpoint was released by the authors of a paper (arXiv or peer-reviewed) that introduces or
  evaluates that checkpoint on that exact target model, and it is pinned by commit hash. Examples: Karvonen et al.'s AOs
  (arXiv 2512.15674), Bauer et al.'s Qwen3-8B AO (arXiv 2606.02609), Gemma Scope SAEs.
- **community** — any other trained reader checkpoint (third-party ports or our own training).
- **none** — the method has no trained reader checkpoint: probes (LR, MM), the logit lens and its rotation control,
  prompt-only, the target model's own fine-tunes.
The tier is a property of (checkpoint, target model), assigned by the rule above, recorded in
`projects/g_agreement/r_bench/checkpoint_tier.py`, and never re-assigned after a result is seen.

**Found while pinning (2026-10-19, not an arm of this BRIEF).** Karvonen's HF collection "Activation Oracles" now also
lists `adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3.6-27B` @ `891bef83dfd5dd5d01bf1f4dc6bed99f68ad6743`
(created 2026-09-25; `ao_config.json`: `model_name: Qwen/Qwen3.6-27B`, grid 16/32/48, hook block 1, `git_commit: "9816813
(main) + uncommitted qwen3.6 branch changes"`). That is a standard-tier oracle for the Phase R target itself. It is outside
this BRIEF's scope as first given; it was added as pair Q27 in §13 (2026-10-19 02:54Z, before any compute).

## 1. The three pairs, pinned (HF API, 2026-10-19 02:30–02:40Z)

| pair | target @ revision | oracle @ revision | tier | from `ao_config.json` / `adapter_config.json` |
|---|---|---|---|---|
| **Q8** | `Qwen/Qwen3-8B` @ `b968826d9c46dd6066d109eabc6255188de91218` (36 blocks, d 4096) | `adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3-8B` @ `6e3c7e9d7157f1b09b1915175eb23a4a88830c08` | standard | `model_name: Qwen/Qwen3-8B`; act layers **9 / 18 / 27** (25/50/75 %); `hook_onto_layer: 1`; `special_token: " ?"`; `prefix_template: "Layer: {layer}\n{special_token} * {num_positions} \n"`; `steering_coefficient: 1.0`; LoRA r 64 / α 128, all-linear; training code `git_commit 603497b` |
| **Q32** | `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137` (64 blocks, d 5120) | `adamkarvonen/checkpoints_cls_latentqa_past_lens_Qwen3-32B` @ `08c733f35a12ab245f30192878eb9050736865f7` | standard | `model_name: Qwen/Qwen3-32B`; act layers **16 / 32 / 48**; hook block 1; `" ?"`; same prefix; coefficient 1.0; LoRA r 64 / α 128; same training commit `603497b` and the same data mix as Q8 (repo name lacks "addition"; see check K3) |
| **Q8B** | `Qwen/Qwen3-8B` @ the Q8 revision (the oracle's base is `unsloth/Qwen3-8B` @ `946bc9ac74a6c1f8cf012497c503a119b2fcf2eb`; check K2) | `ceselder/qwen3-8b-ao-v3-best` @ `a7344ac8f21ed848c9f0593893e94137c4cb38cb` (Bauer & De Schamphelaere, "Building Better Activation Oracles", arXiv 2606.02609; collection `ceselder/building-better-activation-oracles`) | standard | act layers **21, 22, 23, 24, 25 concurrently** (one ` ?` slot per layer, `layer_combinations [[59, 62, 64, 67, 70]]` %); hook block 1; `" ?"`; same prefix template; coefficient 1.0; LoRA r 128 / α 16, rsLoRA, all-linear; data: Sonnet conversational QA + classification + on-policy past-lens; model card: "4-seed mean +0.417 on AObench" |

The released Bauer checkpoint is the one its model card calls the full v3 recipe ("best"); the DPO and steering-2.0
variants in the same collection are not arms (§10). If a later revision of any oracle repo appears, the pinned hash above
is what is run.

**Training render and site, verified from the training code** (`adamkarvonen/activation_oracles`, `main` as of
2026-10-19; the 8B/32B training commit `603497b` is not on GitHub, so K1 re-verifies on the pod):
- *Oracle prompt.* `create_training_datapoint`: user turn = `get_introspection_prefix(layer, k)` + the question, i.e.
  `"Layer: {layer}\n" + " ?"·k + " \n" + question`, rendered with `apply_chat_template(add_generation_prompt=True,
  enable_thinking=False)` (so the assistant turn starts after Qwen3's empty think block); the target response is
  teacher-forced after it. Placeholder positions by `find_pattern_in_tokens` (asserts ` ?` is one token).
- *Injection.* `get_hf_activation_steering_hook` at the output of decoder block `hook_onto_layer = 1`: at each slot,
  resid ← resid + normalize(v)·‖resid‖·coefficient (**addition**, norm-matched to the slot's own residual). The vLLM
  hook in the same file *replaces* instead of adding; K3 decides which one each checkpoint was trained with.
- *Where the training states were read (classification data, the closest to our use).* The context is rendered as a
  **user turn with no generation prompt** (`apply_chat_template([{"role":"user", …}])`, Qwen3: `<|im_start|>user\n{text}<|im_end|>\n`),
  and the state is taken at an end offset drawn uniformly from **−1 … −5** (1-token windows in one copy of each dataset,
  1–50-token windows ending there in the other). Offset −1 is the `\n` after `<|im_end|>`, −2 is `<|im_end|>`, −3 … −5 are
  the last text tokens. Because attention is causal, the state at `<|im_end|>` and at the following `\n` in our R-A chat
  render (which continues with `<|im_start|>assistant\n<think>\n\n</think>\n\n`) is **identical** to the training render's
  state at offsets −2 and −1. The training-native site is therefore a position inside our chat render, and the position
  sweep (§3.6) already covers it; no new render is needed.
- *LatentQA* reads windows ending at −1 … −10 of chat dialogs; *past-lens* reads 1–50-token windows of raw pretraining text
  (max_length 512). The oracles have therefore seen both chat-turn and raw-text states, at 1-token and multi-token windows.

## 2. Hypotheses (BRIEF_RG §1, per pair; plus three panel hypotheses)

Per pair p ∈ {Q8, Q32, Q8B}, exactly BRIEF_RG's H1-G, H2-G and H7-G with "AO@21" replaced by the pair's primary AO
site (§3.2), and with **no H1-S** (no SAE column; §10). They are labelled H1-p, H2-p, H7-p.

Panel hypotheses (new; decision rules in §6):
- **HP1 (tier robustness).** The Qwen3.6-27B Phase R verdicts are not artefacts of community checkpoints: for both
  standard pairs Q8 and Q32, the four-way verdicts of H1, H2 and H7 equal those of the Qwen3.6-27B Oracle lens (WS3's
  final tables) and of the Gemma AO (BRIEF_RG), and the text-only oracle is not beaten by the oracle on the state
  (§3.4 rule) on a majority of facts.
- **HP2 (scale within one family).** The per-fact blind-spot profile transfers from 8B to 32B: BRIEF_RG §10's BD-8 rule
  (within-tag Spearman of ρ_f = AUROC_AO / AUROC_probe(512), probe-partialled; tag ordering; quiver within ±0.02 at
  n ∈ {8, 32}) applied to Q8 vs Q32, and separately to each of them vs Qwen3.6-27B's Oracle lens.
- **HP3 (the improved recipe).** Bauer et al.'s recipe reads more from the same states than Karvonen's: Q8B minus Q8,
  paired per fact on identical items at each oracle's primary site, chat render.
  Forecast (no decision weight): HP1 holds; HP2 REPLICATES for Q8 vs Q32 and is PARTIAL against Qwen3.6-27B; HP3 gives
  +0.01 to +0.03 AUROC overall, concentrated on TOPIC and COMPUTED, and does not change H2 (Bauer et al. report that
  narrow tasks "roughly matched linear probes but never clearly exceeded them").

## 3. Methods (what changes from BRIEF_RG §2 and §10–§11; everything else as written there)

### 3.1 Bank, splits, exclusions
`dataset/items_r.json`, sha256 `2dbde3a2…13f5` = `manifest/frozen_config_r.json` `items_r_sha256`; copied from the main
checkout's frozen file and sha-checked before any model loads (never rebuilt; a mismatch aborts). 113 facts, test 200 /
pool 512 per fact, the frozen splits and seeds. Texts cut to 256 text tokens (BRIEF_R's rule). Label defects as BRIEF_RG
§9 (2026-10-19 04:05 note, the 7-fact set: 139, 140, 141, 97, 145, 146, 101): every table without them (primary) and with
them (`with_label_defect/`); they never enter a BH family.

### 3.2 Capture and sites
Target in bf16, eager attention (sdpa allowed if check K4 passes), adapter disabled during capture. Renders exactly
BRIEF_R's: **chat** = the text as the user turn, `enable_thinking=False` generation prompt, read at the assistant onset
(the last token of `<|im_start|>assistant\n<think>\n\n</think>\n\n`); **raw** = the bare text (Qwen3 adds no BOS), read at
its last token. Blocks captured (residual after the block, `hidden_states[b+1]`):

| pair | AO grid (25/50/75 %) | primary AO site | extra blocks | probe / logit-lens primary |
|---|---|---|---|---|
| Q8 | 9, 18, 27 | **18** (chat) | 21–25 (for Q8B), 35 (last) | 18 |
| Q32 | 16, 32, 48 | **32** (chat) | 63 (last) | 32 |
| Q8B | concurrent 21–25 | **21–25 concurrent, "Layer:" string per K5** (chat) | — (reuses Q8's states) | 23 (the middle block) |

Q8 and Q8B share the target model and therefore one capture; Q8B adds AO forwards only.

### 3.3 Readers, references, controls (BRIEF_RG §2.1 rows, minus the SAE rows)
- **AO** (candidate form, primary) and **AO-yn** (training-native yes/no form): BRIEF_RG §2.1 verbatim, with the pair's
  prefix (`"Layer: {L}\n ? \n"`, or for Q8B five ` ?` slots each carrying one block's state, K5), the dataset question,
  Gemma's `AO_FC_SUFFIX` and teacher-forced bare candidates; LO = s_pos − s_neg; s_pos for one-sided facts.
- **logit lens** at every captured block (final RMSNorm + W_U; Y1 first-token convention); the random-rotation readout
  `logit_lens_rot` (10 seeds) as BRIEF_RG §10.
- **probe LR(n)** and **probe MM(n)**, n ∈ {2 … 512}, 5 seeds, at the primary probe block, and LR(512) at every captured
  block; `analyze.probe_fit_select` and the paper's validation scheme, unchanged.
- **prompt-only** on every item, `PROMPT_ONLY_FC_TEMPLATE` teacher-forced after the generation prompt (thinking off).
- **controls** at every AO site: shuffled (derangement seeded per (dataset, render, layer)) and state-free (dataset-mean
  state). Shuffled AUROC in [0.45, 0.55] on ≥ 95 % of cells, else a bug.
AO rows: the 200 test items of every fact at every grid site in the chat render, the primary site in the raw render, and
the 64 balanced pool items at the primary site (the quiver's pool); shuffled and state-free at the same cells.

### 3.4 Text arm with the dataset question (BRIEF_RG §10 `ao_noact`; BRIEF_R §13 arm (a))
The AO prompt with the item's text in place of the ` ?` slot(s) (`"Layer: {L}\n{text} \n"` + question + FC), hook
disabled, both forms (`ao_noact`, `ao_yn_noact`), 200 test items per fact; for Q8B "Layer:" as K5 and the text once.
Contrast C-A (Check 2): Δ_A = AUROC(AO on the state, primary site) − AUROC(text arm), item-paired bootstrap (2,000
resamples, seed 0), and BRIEF_R §12's verdicts and rule verbatim: READ FROM THE STATE iff Δ > 0, 95 % CI excludes 0 and BH
q ≤ 0.10 within tag; TEXT SUFFICES iff Δ < 0 likewise; else NOT DISTINGUISHED. Chat primary, raw secondary (own family).

### 3.5 Text + activation (BRIEF_RG §11 (a))
`ao_textact` / `ao_yn_textact`: `"Layer: {L}\n ? \n{text}\n{question}"` + FC with the state added at the FIRST ` ?` (the
prefix's; BRIEF_RG §9 02:10 rule), states from the chat and from the raw render at the primary site (Q8B: five slots, the
text after them). Δ_f = AUROC(text + activation) − AUROC(text arm). **Rule as BRIEF_RG §11 (a): "the activation adds
information" at a site iff the mean Δ over facts is > 0 with the corpus → dataset → item bootstrap 95 % CI excluding 0**,
per tag and overall, per form, per render; the fact-level counts (item CI > 0 vs < 0) beside it.

### 3.6 Position sweep (BRIEF_RG §11 (b))
Chat render, every token from the last text token to the assistant onset (offsets k = K … 0 from the end; K read from the
tokenizer at run time: 9 if Qwen3's template tokenises as `<|im_end|>`, `\n`, `<|im_start|>`, `assistant`, `\n`, `<think>`,
`\n\n`, `</think>`, `\n\n`), at the pair's three grid blocks (Q8B: the concurrent 21–25 read, per offset). AO (candidate form)
on the test items and an LR probe fitted on the pool, per (block, offset). **Rule as BRIEF_RG §11 (b): "information present
but unread" at (block, offset, fact) iff probe AUROC ≥ 0.85 and probe − AO ≥ 0.10 with the item-paired CI excluding 0**;
headline = the count per (block, offset) and the offset where it peaks. Offset 0 at the primary block must reproduce the main
AO cell (sanity).
**Training-native site (secondary, pre-registered here).** The offsets of `<|im_end|>` and the following `\n` are the
oracle's training positions (§1). If the AO's mean AUROC over facts at the better of those two offsets (chosen on the 64 pool
items, not on test) exceeds the assistant-onset AUROC by ≥ +0.02 with the corpus CI > 0, every per-pair verdict of §6 is
restated at that offset beside the primary one; the primary site does not change.

### 3.7 The quiver, n*, ceiling, agreement
BRIEF_RG §2.3–§2.4 with arrow sets **P** = {LR(n), MM(n)} and **P + AO** = P ∪ {AO, AO-yn, logit lens zero-shot, each
stacked with LR(n) for n ≥ 8}. The vote in H7-p: AO, AO-yn, logit lens.

## 4. Order of work
1. Code (`projects/r_panel/`, Mac): a pair config (repo, revision, grid, slots, prefix) and thin wrappers over
   `r_gemma.collect` / `oracle` / `analyze` / `followup` with the Qwen3 renders; mock tests offline.
2. Pod smoke on `92_glue_sst2` and `66_living-room` (`--allow-unfrozen`, `cache/g_agreement/rp_unfrozen/`), checks K0–K6.
3. `--freeze-rp`: `manifest/frozen_config_rp.json` records the bank sha, every repo revision, the code sha, the K-check
   outcomes and K5's prefix string.
4. Q8 full (capture, prompt-only, AO, controls, text arms, sweep), then Q8B on the same states, then Q32.
5. CPU: learning curves, quiver, tables, figures; then the panel rules (§6).

## 5. Checks before the first look at test rows (pod; any failure stops the run, the fix is logged before compute resumes)
K0. BRIEF_RG §7 checks 1–3 for each pair (batched capture = single forward, cos ≥ 0.9999 at every captured block and
render; teacher-forced lp = single forward in fp32, |Δ| < 1e-3, bf16 gap < 0.3 nats reported; AO liveness on 4 SST-2 pool
items at the primary site ≥ 3/4 right; hook fires once per forward; ` ?` is one token where `find_pattern` says).
K1. The tokenizer renders the oracle prompt exactly as `create_training_datapoint` does (string and ids equal for 4 prompts,
`enable_thinking=False`, generation prompt on).
K2. Q8B: the Q8 target (`Qwen/Qwen3-8B`) and `unsloth/Qwen3-8B` have identical weights (max |Δ| = 0 over every tensor after
name mapping; their index files differ, 2026-10-19). If not identical, Q8B runs on `unsloth/Qwen3-8B` with its own capture
and that is recorded here as a deviation before any Q8B test row.
K3. Injection mode per checkpoint, decided on pool items only, before any test row: liveness (K0's) with the additive hook
and with the replacing hook. The additive hook is used unless it fails liveness and the replacing one passes. Q32's repo
name lacks "addition", but its `ao_config.json`, data mix and training commit equal Q8's, so the additive hook is expected.
K4. Attention implementation: eager vs sdpa LO on 32 items, |Δ| < 0.05 nats median, else eager.
K5. Q8B's "Layer:" string for a five-layer read. `get_introspection_prefix` takes one layer; Bauer et al.'s fork must say
what it writes for a concurrent read. Resolved from their released code before the freeze; if their code cannot be found,
the candidates `"Layer: 21, 22, 23, 24, 25"`, `"Layer: 21"` and `"Layer: 23"` are compared by AO liveness and mean AUROC on
the 64 pool items of 8 facts fixed now (SURFACE `66_living-room`; TOPIC `92_glue_sst2`, `21_headline_istrump`; FORM
`105_click_bait`; KNOWLEDGE `5_hist_fig_ismale`, `114_nyc_borough_Manhattan`; COMPUTED `48_cm_correct`, `89_glue_mrpc`; ids
checked against `r_bench.datasets.SPECS` 2026-10-19), the best one frozen. Nothing on test rows decides it.
K6. Disk and memory: Q32 in bf16 (≈ 65.5 GB) + LoRA + activations on one H100 80 GB at batch ≥ 4; if it does not fit, an
H200 141 GB (or 2× H100) is used and the billed hours are logged as such.

## 6. Decision rules
Per pair: BRIEF_RG §5 for H1-p, H2-p, H7-p (two-way rule, four-way verdict with BRIEF_R §4.9 (d) margins, BH q = 0.10 per
reader for the per-fact ceiling exceedances, corpus → dataset → item bootstrap beside the i.i.d. fact bootstrap, the wider
CI quoted, MDEs printed); §3.4, §3.5, §3.6 rules as stated. Paired reader differences by exact sign tests on identical facts.
- **HP1** SUPPORTED iff for Q8 and for Q32: (i) the four-way verdicts of H1-p, H2-p, H7-p each equal the Qwen3.6-27B Oracle
  lens's verdict on the same hypothesis (WS3's final `verdicts4`-equivalent table, chat, primary site) — or, where the two
  differ, the standard pair's verdict is UNDERPOWERED or EQUIVALENT-NULL and Qwen3.6-27B's is too; and (ii) C-A gives READ
  FROM THE STATE on fewer than half of the 108 kept facts. REFUTED iff for either standard pair a verdict flips sides
  (SUPPORTED ↔ REFUTED) relative to Qwen3.6-27B, or C-A gives READ FROM THE STATE on a majority of facts. Otherwise PARTIAL,
  with each clause reported. Q8B does not enter HP1 (it is a recipe test, HP3).
- **HP2** BRIEF_RG §10's REPLICATES / PARTIAL / NULL rule verbatim (an unevaluable clause counts as failed, BRIEF_RG §9
  03:35 reading), for Q8 vs Q32 (primary), Q8 vs Qwen3.6-27B Oracle and Q32 vs Qwen3.6-27B Oracle (secondary), on the 108
  facts kept in all runs.
- **HP3** Δ_f = AUROC(Q8B AO, primary) − AUROC(Q8 AO, primary), chat, both forms, on identical test items. IMPROVED iff the
  mean Δ ≥ +0.02 with the corpus-clustered 95 % CI > 0; NOT WORSE iff the CI lower bound > −0.02; WORSE iff the CI lies below
  0. Equivalence margin ±0.02 (four-way as BRIEF_R §4.9 (d)). Secondary, same rule: quiver ΔAUC_AO(n) Q8B − Q8 at n ∈ {8, 32};
  C-A's READ FROM THE STATE count Q8B vs Q8 (McNemar on facts). MDE printed (fact-level mean ΔAUC over 108 facts ≈ 0.008–0.021,
  BRIEF_R §4.9 (a)).
- Surprise list (BRIEF_R §4.9 (c), re-scored on 200 fresh pool items before it is claimed): an H2-p exceedance on
  SURFACE/TOPIC/FORM; a fact where a standard AO is READ FROM THE STATE and the Qwen3.6-27B Oracle is TEXT SUFFICES on the
  same fact; HP3 WORSE.

## 7. Deliverables (`results/g_agreement/rp/`)
Per pair under `rp/<pair>/`: the BRIEF_RG file set without the SAE files (`cells.csv`, `learning_curves.csv.gz`,
`quiver.csv.gz`, `quiver_summary.csv`, `nstar.csv`, `ceiling.csv`, `ceiling_bh.csv`, `agreement.csv`, `verdicts4.csv`,
`text_vs_activation.csv`, `followup_a*.csv`, `followup_b*.csv`, `summary.md`) and `with_label_defect/`. Panel:
`rp/panel.csv` (rows = facts; columns = probe(512), prompt-only and the primary AO for Q8, Q32, Q8B, the Qwen3.6-27B Oracle
and the Gemma AO), `rp/panel_verdicts.csv` (HP1–HP3 four-way), `rp/report.md`, figures FP1 (headline per pair), FP2 (blind-spot
map: Qwen3.6-27B community readers | Gemma AO | Q8 | Q8B | Q32, columns headed by tier), FP3 (position sweep per pair, the
training-native offsets marked). Every table carries `checkpoint_tier` (§9).

## 8. Compute and budget (new-reader bucket; billed pod uptime binds)
Scaled from WS9 (Gemma-2-9B, the same pipeline: ≈ 4.7 h of GPU work for main run + §10 + §11, BRIEF_R §7 amendment).
| pod | work | GPU work | billed target | hard stop |
|---|---|---|---|---|
| P8 (1× H100 80 GB) | Q8 capture + prompt-only + AO + controls + text arms + sweep ≈ 4.5 h; Q8B AO arms on the same states (5 slots, no capture) ≈ 2.5 h | ≈ 7 h | 10 h | 14 h |
| P32 (1× H100 80 GB, or H200 per K6) | Q32: ≈ 3.5× Q8's FLOPs, batch ≤ ⅓ | ≈ 16 h | 22 h | 30 h |
| Mac CPU | learning curves (113 × 9 n × 5 seeds × 2 probes × 3 pairs' primary blocks), sweep probes | — | — | — |
**Total target 32 billed GPU-h (≈ $128), hard stop 44 h (22 % of the bucket).** Every pod runs from its container disk (the
volume is at quota), with self-stop ON addressed to its own pod id (never `$RUNPOD_POD_ID` from `/workspace/.env`), and a 15-min
pull window. If P32 reaches 30 billed h, it stops; whatever Q32 rows exist are analysed and the rest reported NOT RUN.
Every run appends to `results/g_agreement/rp/log.md` (times from `date -u`, HH:MMZ) and `results/g_agreement/compute.rp.jsonl`
(module `rp`, `pod`, `shard`, plus a `pod_billed` row per pod at stop).

## 9. The checkpoint-tier column (all Phase R tables)
`r_bench/checkpoint_tier.py` holds the map (reader key → tier, checkpoint repo @ revision) and `annotate(df, path)`.
Rule: every Phase R CSV carries a `checkpoint_tier` column. Its value comes from the row's reader column (`reader`,
`method`, `probe`, `form`, `line`, `column`, `readers`, `hypothesis`); a table about one reader throughout with no reader
column (e.g. `r/text_arm.csv` = the Oracle lens, `rg/followup_b.csv` = the Gemma AO) gets that reader's tier on every row
(`FILE_READER`); a wide table whose columns are readers keeps its header and gets a sidecar `<name>.tiers.csv` (column →
tier). Values: `standard`, `community`, `none`, plus `mixed` for a row that pools trained readers of different tiers. Rows
that pool several readers (a reader list, an `all` quiver line, a hypothesis id) take the tier of their trained readers
(`none` ignored), and for `all` / hypothesis rows the tier of the table's directory (`r/` community, `rg/` and `rp/`
standard). A reader key the map does not know is `unknown`, and `tests/test_checkpoint_tier.py` fails on it and on any
committed table without the column. The column was added to the 39 committed tables under `results/g_agreement/r/` and
`rg/` on 2026-10-19 by `--apply`, append-only (every existing field byte-identical), and five sidecars were written.
Generators should call `annotate` when they write; until each stream's generator does, `python -m
projects.g_agreement.r_bench.checkpoint_tier --apply` runs after every regeneration (the integrator's step; `--check` is
the test). Markdown reports name the tier in every reader column's header from their next regeneration on. Current
assignments: J-lens, Oracle lens (incl. `olens_trueL`, `olens_txt*`), NLA, skip lenses = community; the Gemma AO and its
arms, Gemma Scope SAE probes and the Q8/Q32/Q8B/Q27 AOs = standard; probes, logit lens (+ rotation), prompt-only, `model_ft` =
none.

## 10. Not run (listed so nobody mistakes an absence for a negative)
SAE columns (Karvonen's `qwen3-8b-saes` / `qwen3-32b-saes` exist; not in scope), R-B k-way, R-C conflicts, R5 steering, R-D
legacy, ReaderBench / R-X / R-E banks, free-text case studies, Bauer's other checkpoints (`adam-baseline`, ablations,
`best-dpo-halluc`, `best-steering2p0*`) and Transluce's Qwen3-8B oracle. (The Qwen3.6-27B standard AO, listed here at 02:41Z,
is now pair Q27 in §13.)

## 11. Forecast registry
Before `--freeze-rp`, forecasters append rows to `results/g_agreement/rp/forecasts.jsonl` as BRIEF_R §1's registry: P(HP1),
P(HP2 REPLICATES for Q8 vs Q32), P(HP3 IMPROVED), and 80 % intervals for C-A's READ FROM THE STATE count per pair. The registry
changes no measurement.

## 12. Deviations
- 2026-10-19 03:35Z (§9 enforcement; no measurement or rule of §2–§8 or §13 touched; no data exists). The Integrator
  reported that WS3's routine regeneration (ci10.csv, interim_*_facts.csv) drops the column, which makes §9's test fail
  for other streams. The test now fails only on BRIEF_RP's own tables (`results/g_agreement/rp/`) and on the tier map's
  unit tests. For every other table, a missing or stale column or an unknown reader key is a warning. Owners get the
  one-line `annotate(df, path)` hook (HANDOFF 03:35). `--check --strict` keeps the strict form for the integrator.
- 2026-10-19 17:09Z (implementation, before any pod for this BRIEF; no rule changed). Launch approved by Guiv (42 h target / 58 h hard
  stop, new-reader bucket, self-stop every pod, Qwen3-8B reported first). Code `projects/r_panel/` re-points r_gemma's collector
  per pair (`setup.activate`). (1) **K5 resolved from code**: Bauer et al.'s `get_introspection_prefix(layers, 1)` (ceselder/cot-oracle
  @ 5208ece, `AObench/utils/dataset_utils.py`) writes one `"Layer: {L}\n ? \n"` block per layer, so Q8B's prefix is
  `"Layer: 21\n ? \nLayer: 22\n ? \n … Layer: 25\n ? \n"`. Their HF hook is additive and norm-matched (`steering_hooks.py`), as
  Karvonen's. The §5 K5 pool-item comparison is therefore not needed and is not run. (2) Q8B's text-only arm (§3.4 left the form
  open): the five `Layer: L` lines, then the text once where the slot block would start (`pairs.multi_noact_prefix`). (3) Q8B rows
  are keyed under the virtual layer 2125 (blocks 21–25 stacked from Q8's states). Its sweep probes are Q8's LR probes at block 23 per
  offset (same target, same states). (4) Q8's position sweep captures blocks 9/18/21–25/27. The Q8 AO reads the sweep on its grid
  (9/18/27) only, and the probes run at 9/18/23/27. (5) Eager attention throughout, so K4 is not run. K0.2's fp32 exactness check
  runs on the 8B target only (32B/27B in fp32 do not fit one H100); the bf16 gap is reported for all. (6) Chain gates: podcheck exit
  0 and the smoke's SST-2 AO AUROC (primary chat site) ≥ 0.6. Otherwise the pod stops after its pull window.
- 2026-10-19 17:35Z (K0.1 / K0.2 tolerances; a pipeline check, not a hypothesis rule; no test row exists). The first Q8 podcheck
  (17:31Z, pod di7p8t2c28fwec) failed both of BRIEF_RG's bf16 tolerances. The batched-vs-single capture cosine was 0.9996 in chat
  (raw 0.99987) against ≥ 0.9999. The left-padded teacher-forced batch differed from single rows by up to 0.5 nats against < 0.3.
  The same batched path is exact in fp32: max |Δ| = 7.2e-5 nats. K1 passed. K3 liveness was 3 of 4 right, with LOs +1.6, +6.0,
  −1.25, +2.5 and an adapter effect of 22 logits. The fix follows BRIEF_RG §9 07:50: exactness is gated in fp32 (K0.1 cos ≥ 0.9999
  and K0.2 |Δ| < 1e-3, on the 8B target, where fp32 fits). The bf16 cosines and per-row bf16 gaps are reported in
  `rp/<pair>/podcheck.json`; they are not gates. For Q32 and Q27, which cannot run fp32, the 8B fp32 result certifies the shared
  code path and their bf16 numbers are reported. Both candidates of a state always share one forward, as in WS9. Separately, a pod
  guard not started by this chain appeared at 17:29:42Z (`/root/pod_guard`: hard 2,700 s, idle 15 min). It targeted pod
  ak1hnbxk8ppdw5, read from `/workspace/.env`, not this pod. It was killed and noted in its log.
- 2026-10-19 18:11Z (§13 Q27 implementation, before any Q27 compute; no rule changed). (1) **Fresh capture instead of reuse.** Q27 runs
  r_gemma's full phase A: blocks 16/32/48, both renders, 712 items per fact, plus prompt-only and the logit lens. The reason is that
  r_gemma's analysis reads its own row formats, and the frozen R-A rows (r_bench format, frozen code 4d482b6) are not the same files.
  Cost: about +1–1.5 GPU-h within Q27's 10 h target. The frozen data still serve their pre-registered roles. The frozen Oracle-lens
  rows are HS's community side. The frozen `chat_L{32,48}.npy` are Q27-K2's reference: the re-captured states are compared by item
  id on the Mac before any Q27 verdict, with the same pass rule. The frozen prompt-only rows are compared with the new ones (r ≥ 0.99
  expected; reported). (2) **Q27-K3: kernels deliberately not installed.** The flash-linear-attention / causal-conv1d kernels are not
  installed, so the reference Gated DeltaNet path is used. That is the path the frozen Phase R capture ran on (`manifest/assets.json`
  kernels note), so K2 compares like with like. The oracle was trained with the kernels; the bf16 gap is reported. (3) `ao_base` is
  implemented in `r_panel/base.py`: the oracle's candidate form with the adapter disabled (`disable_adapter_ctx`), injection on, at
  32 chat, test items, no controls. It runs last in the p27 chain.
- 2026-10-19 19:47Z (after Q8's cells existed; a reading of the shuffled-control rule, no rule changed). §3.3 inherits BRIEF_RG's
  "shuffled AUROC in [0.45, 0.55] on ≥ 95 % of cells, else a bug". On Q8 (864 shuffled cells, 108 facts × 8 sites) 74.5 % are in
  the band. The diagnosis: mean 0.5002, SD 0.0428; the AUROC's own SD under the null at 100 + 100 items is 0.0409, which puts only
  77.8 % of cells in that band; Gemma's run had 78.1 %; WS3's calibration (HANDOFF) found 78.3 % on Qwen3.6-27B. The 95 % CI
  excludes 0.5 in 6.6 % of cells (nominal 5 %), no site's mean differs from 0.5 by more than 0.007, and no site stands out. The
  rule's threshold cannot be met at n = 200 by a correct pipeline. It is reported as failed-as-written, and the controls are read
  as sampling noise, not a bug. The same reading applies to every pair: per pair, the mean, the SD against 0.0409 and the
  CI-excludes-0.5 rate are reported next to the band fraction.
- 2026-10-19 21:55Z (after Q8's agreement table; a reading of H7's statistic, no rule changed). r_bench's `r7_agreement`, which r_gemma
  and this panel use, defines the consensus gain as consensus accuracy minus the best reader's accuracy on the SAME unanimous items.
  On those items the best reader casts the consensus vote, so the gain is 0 by construction: 0.000 on all 108 Q8 facts and on all of
  Gemma's. BRIEF_R §1 states H7 as P(correct | all readers agree) − P(correct | best single reader), the best reader's accuracy over
  all test items. Both are reported for every pair: the implemented form (trivially SUPPORTED) and the §1 form with the corpus /
  i.i.d. CIs and four-way verdict. The §1 form decides H7-p's first clause in this panel's report. For comparison, Gemma's §1 form
  is +0.41 pts [−1.21, +1.61].
- 2026-10-20 04:02Z (Q27-K3 taken up as pre-registered in §13, after Q27's capture; no rule changed). The 2026-10-19 note set the kernels
  aside so that Q27's capture would match the frozen Phase R states. That capture finished on the reference path at ≈ 02:57Z. At
  ≈ 04:00Z I stopped Q27's oracle reads, mid-site at block 48 (chat, candidate form), to run §13's K3 as written. K3 compares the AO's
  LO with and without the flash-linear-attention kernels (fla 0.5.2) on 32 pool items of 92_glue_sst2 at block 32 chat. It passes iff
  the median |ΔLO| < 0.05 nats, and then the remaining oracle reads (rest of phase A, P, T, ao_base, native pool rows) use the kernels.
  The oracle was trained with them. On a fail the kernels are uninstalled first and the reference path continues. The states are
  unchanged (reference path) throughout. Disclosure: I made the switch on a wrong throughput estimate, about 3.7 h per site; the
  true figure was about 30 min, since blocks 32 and 16 were already done. K3 is still the pre-registered rule, and the sweep and
  text + activation would likely not have fit before rp27's 10:36Z cap on the reference path. Already-written rows are kept, and
  the reads resume per fact.
  **Outcome (04:06Z): K3 FAIL**, median |ΔLO| 0.125 nats (max 0.125; the same bf16 step on every item) against < 0.05. The kernels were
  uninstalled and every Q27 row, before and after, is on the reference path. The detour cost ≈ 10 min plus the restart of the part-done
  block-48 site; nothing else changed.
- 2026-10-20 10:55Z (Q27 data loss at the end of rp27; before any Q27 verdict; no rule changed). Q27's job ended at its §13 cap (10:35:00Z).
  At 10:36:37Z the pod's own hard-timeout sleeper fired during the warm hold for R-A. The panel's stop-only Mac guard carried out the
  stop at 10:37:11Z, before the final pull. On this no-volume pod, stopping erased the container disk: the integrator found `/root/rp`,
  `/root/hf` and the code missing at the 10:38:45Z resume (HANDOFF a13ecfbe). The panel missed that the sleeper's deadline fell
  1.5 min into the hold. What exists on the Mac (pulled every 3 min until 10:10Z):
  - **Complete, 113 facts:** every oracle row of phase A (AO and AO-yn at 16/32/48 chat and 32 raw, shuffled, state-free, the 64 pool
    items at 32 chat, the text arm in both forms), prompt-only and the logit lens.
  - **Partial:** the position sweep (AO, 16/32/48, offsets 0–9) on 75 of 113 facts; the pod reached about 88 by the cap.
  - **Lost:** the fresh capture's states (all blocks, both renders; the loop pulled `.npy` only at chain end), so Q27-K2 cannot be
    evaluated.
  - **Never run (cap):** text + activation, the native-site pool rows (§3.6 choice), the sweep probes, `ao_base`, and the
    native-offset states.
  **Proposed reading (Guiv to decide; nothing analysed yet):**
  1. The probe-based clauses (LR / MM curves, quiver ΔAUC, n*, H2 ≥ 0.8 × probe) use the frozen R-A states
     `cache/g_agreement/r/states/<fact>/{chat,raw}_L{32,48}.npy`. That is §13's original rule ("these states are reused, not
     recaptured"), which the 2026-10-19 18:11Z note replaced by a fresh capture with K2 as its check. There are no block-16 probe
     cells.
  2. §3.5 text + activation and the §3.6 native-site rule are reported as NOT RUN for Q27.
  3. The 75-fact sweep is reported descriptively only.
  4. HS, C-A, H2's exceedances over prompt-only and H7 run on the complete rows.
  The alternative is a resume to finish the missing arms. That needs a new pod and booking through the integrator; it is not
  scheduled.
  **Adopted 2026-10-20 ≈ 11:00Z by Guiv in chat, before any Q27 analysis:** the proposed reading, items 1–4 exactly. Check before use:
  the frozen indexes match Q27's pulled indexes on all 113 facts (same item ids, labels, splits and chat token counts; the frozen
  index names the chat read token "\n\n", Q27's names it "assistant_onset", the same last template token). Implementation: the frozen
  `{chat,raw}_L{32,48}.npy` are symlinked into `cache/g_agreement/rp/Q27/states/<fact>/`; no block-16 file exists, so no block-16
  probe cell is computed.

## 13. Q27 — the standard AO on the Phase R target itself (pre-registered 2026-10-19 02:54Z, before any Q27 code or compute)

**Why.** §0 noted that Karvonen's collection includes an oracle for Qwen3.6-27B. It is the only test of the tier question
that holds the model, the bank, the states and the prompt-only rows fixed and changes only the checkpoint: a standard AO
against the community Oracle lens on identical test items. Everything in §1–§11 applies to Q27 unless this section says
otherwise. Q27 has its own hypotheses (H1/H2/H7-Q27, HS, HP4); HP1–HP3 are unchanged.

**Pinned (HF API, 2026-10-19 02:45–02:54Z).**
| pair | target @ revision | oracle @ revision | tier |
|---|---|---|---|
| **Q27** | `Qwen/Qwen3.6-27B` @ `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`, the Phase R revision (`manifest/assets.json`). It is still the repo HEAD (lastModified 2026-04-24), and the oracle was created 2026-09-25, so it was trained on this snapshot. 64 blocks, d 5120. Loaded as Phase R loads it: `AutoModelForCausalLM` → text-only `Qwen3_5ForCausalLM`. | `adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3.6-27B` @ `891bef83dfd5dd5d01bf1f4dc6bed99f68ad6743` | standard |

From its `ao_config.json`, `adapter_config.json` and model card: act layers **16 / 32 / 48** (25/50/75 %), one layer per example;
`hook_onto_layer: 1`; `" ?"`; prefix template as Q8; `steering_coefficient: 1`; additive, norm-matched injection (card: "injected
additively (norm-matched) at layer 1"); LoRA r 64 / α 128 on every linear layer of the text model, including the Gated DeltaNet
projections (`in_proj_qkv`, `in_proj_z`, `in_proj_a`, `in_proj_b`, `out_proj`); the Q8 recipe and data mix (LatentQA,
classification with end offsets −1 … −5 and 1- or 1–50-token windows, past-lens at max_length 512), 1 epoch, 64,123 steps at
batch 16, lr 1e-5. It was trained with transformers 5.17, peft 0.21, torch 2.12.1 and the flash-linear-attention / causal-conv1d
kernels. Training code: `git_commit "9816813 (main) + uncommitted qwen3.6 branch changes"`; 9816813 is on GitHub (2026-04-18,
"multi layer demo"), but the Qwen3.6 changes are not. Layer indexing matches ours: `get_hf_submodule` returns
`get_decoder().layers[layer]`, and our capture hooks the output of `blocks[L]` (`core/model.py`); check Q27-K1 confirms it on the pod.
The card notes that the untrained model already scores 72–93 % zero-shot on the oracle's own classification evals. So the
state-free, text-only and adapter-off controls below decide what the AO adds.

**Sites and states.** Primary AO site **block 32, chat render** (assistant onset, as R-A). The frozen R-A capture
(`cache/g_agreement/r/states/<fact>/{chat,raw}_L{32,48}.npy`, 712 items per fact, fp16, frozen code 4d482b6) already holds blocks
32 and 48 in both renders. These states are reused, not recaptured. Block 16 was not captured. The one new capture pass runs on the
chat render for all 712 items of every fact at blocks 16 / 32 / 48. It records every offset from the last text token to the
assistant onset (§3.6; K read from the tokenizer, 9 if the template tokenises as in §3.6), and it serves both block 16 and the
position sweep. Its offset-0 states at 32 and 48 must reproduce the frozen states (Q27-K2). Raw render: block 32 only, frozen states.

**Arms (as §3.3–§3.6 with Q27's grid).** AO and AO-yn at blocks 16 / 32 / 48 in the chat render and block 32 in the raw render.
Each runs on the 200 test items with shuffled and state-free controls, plus the 64 pool items at 32 chat. The text arm with the
question (`ao_noact`, both forms). Text + activation (`ao_textact`, both forms, chat and raw states at 32). The position sweep (AO
candidate form at 16 / 32 / 48 × every offset; LR probe on pool states at the same cells). One new control, **`ao_base`**: the AO
prompt and injection at 32 chat, candidate form, with the LoRA adapter disabled, on the 200 test items. It shows what the base
model reads from an injected state with no oracle training. It is descriptive only: Δ = AUROC(AO) − AUROC(ao_base) per fact,
with the item bootstrap and a per-tag median. **Reused from the frozen Phase R run (never re-run):** prompt-only rows, logit-lens
rows (blocks 32, 48), the Oracle-lens rows (`reader_lo*.jsonl`, olens at 42 / 44 / 48 / 52 / 56) and BRIEF_R §13's text-arm v2
rows (`olens_txtq`, `olens_txtq_act`). Probes: LR(n) and MM(n) at block 32, fitted on the Mac from the frozen states (BRIEF_RG
§2.1 settings); LR(512) at 16 from the new capture.

**Hypotheses and rules.**
- H1-Q27, H2-Q27, H7-Q27: §2 and §6 per-pair rules with AO@32 chat as the primary site.
- **HS (standard vs community on one model).** Δ_f = AUROC(AO@32, chat) − AUROC(Oracle lens@44, chat), each reader at its own
  primary site, on identical test items (the intersection of the item ids scored by both). The primary score is §2.1's for both
  readers. Analysed over the 108 kept facts with the item-paired bootstrap per fact and the corpus → dataset → item bootstrap for
  the mean. **STANDARD BETTER** iff mean Δ ≥ +0.02 and the 95 % CI > 0. **COMMUNITY BETTER** iff mean Δ ≤ −0.02 and the 95 % CI
  < 0. **EQUIVALENT** iff the 90 % CI lies inside ±0.02. Otherwise **NOT DISTINGUISHED**. An exact sign test on facts is reported
  alongside, with the MDE printed. Secondary rows, same rule: the common block 48 (AO@48 vs Oracle@48, chat); the raw render (AO@32
  raw vs Oracle@44 raw); quiver ΔAUC_AO(n) − ΔAUC_Oracle(n) at n ∈ {8, 32}; and C-A, the count of facts READ FROM THE STATE for
  the AO (§3.4) vs the Oracle lens (BRIEF_R §13 C-A), with McNemar on facts.
- **HP4 (tier robustness on the Phase R model).** HP1's clauses (i) and (ii), applied to Q27 against the Qwen3.6-27B Oracle
  lens: SUPPORTED / REFUTED / PARTIAL exactly as HP1. Reported beside HP1; HP1's definition is not changed.
- Surprise list additions (BRIEF_R §4.9 (c), with a fresh-pool re-score before any claim): HS COMMUNITY BETTER; a fact where AO@32
  is READ FROM THE STATE and the Oracle lens is TEXT SUFFICES at 44 (or the reverse).
Forecast (no decision weight): HS NOT DISTINGUISHED or STANDARD BETTER by ≤ 0.03; HP4 SUPPORTED; ao_base well above 0.5 on
SURFACE/TOPIC (the base model already reads injected states, per the card's zero-shot note).

**Checks (in addition to §5; any failure stops the run before the first test row).**
Q27-K1: hook placement. With the adapter on, the hook fires once per forward at the output of `layers[1]`. The capture at block L
equals `hidden_states[L+1]` (cos ≥ 0.9999 on 4 items). The adapter loads with no missing or unexpected LoRA keys on our transformers
version (≥ 5.18 vs the oracle's 5.17). Every one of the 12 target-module names in `adapter_config.json` resolves in our model.
Q27-K2: the offset-0 states of the new pass at blocks 32 and 48 against the frozen `chat_L{32,48}.npy`, cosine per item. Pass iff
the median ≥ 0.999 and the 1st percentile ≥ 0.99 (BRIEF_R §13 K1). If it fails, the AO reads the new states throughout and the
frozen states are used only for the probes; this is recorded as a deviation before any test row.
Q27-K3: Gated DeltaNet kernels. If `flash-linear-attention` and `causal-conv1d` install on the pod, AO LO is computed with and
without them on 32 pool items (median |Δ| reported; < 0.05 nats required to use either path), and the kernels are used. If they
do not install, the reference path is used and the bf16 gap is reported as in BRIEF_RG §9 07:50.
Q27-K4: liveness at 32 chat on 4 SST-2 pool items (≥ 3/4 right) and injection mode as §5 K3 (additive expected; the card says so).

**Compute (new-reader bucket).** One pod, 1× H100 80 GB (54 GB bf16 + LoRA; an H200 if K6's batch ≥ 4 fails). Model download
≈ 20 min to the container disk. The capture pass is 113 × 712 chat forwards of ≤ 300 tokens at 3 blocks × ≈ 10 offsets, about
0.8 h. AO teacher-forced rows: about 0.42 M short rows on the main grid with controls, 0.68 M short rows for the sweep and 0.14 M
long rows for the text arms, about 4 h at roughly 3× Gemma-9B's per-row cost. Add up to ×1.5 if the reference DeltaNet path is
used, plus ao_base 0.2 h. Uploading the reused block-32/48 states (≈ 3.3 GB) takes ≈ 10 min. **Target 10 billed GPU-h, hard stop
14**, with self-stop addressed to the pod's own id and a 15-min pull window, as §8. With §8's 32 / 44, the BRIEF's total is
**42 billed GPU-h target, 58 hard stop (29 % of the 200-h bucket)**. Q27 can run before, after or alongside P8/P32. Outputs go to
`results/g_agreement/rp/Q27/` plus a `panel.csv` column. The tier key is `q27_ao`. Log and ledger as §8.

## 14. H3-N — conflict allegiance at the training-native site, Qwen3-8B (pre-registered 2026-10-20 01:15Z, before any H3-N code or compute; Guiv's request)

**Question.** At the assistant onset, readers sit at chance on text-vs-model conflicts (BRIEF_R H3). The 8B oracles read differently at their
training-native position (§3.6: offset 7, the `\n` after `<|im_end|>`; +0.082 for Q8, +0.050 for Q8B). On items where the text asserts one
answer and the model holds another, does an oracle side with the model there?

**Bank.** The H3-extended planted-context bank `dataset/items_rc2.json` (BRIEF_R §3.1; sha as in `manifest/frozen_config_r.json`): 288 items =
48 mirror pairs × versions A/B × 3 question wordings (q0–q2). Each item has a system turn asserting a false fact; its candidates are the
context's answer (TEXT) and the true answer (MODEL belief). Rendered in chat with the system turn, `enable_thinking=False`, as `planted.messages`.

**Gate, fixed now, before any Qwen3-8B output on these items exists** (`Qwen/Qwen3-8B` @ `b968826d`, bf16; adapter off). Per item:
- *closed-book* = the user turn alone (no system turn). Greedy generation, ≤ 16 new tokens; its answer must match the BELIEF candidate (match rule
  below). AND the confidence margin lp(belief) − lp(context), teacher-forced after the closed-book generation prompt, must be **≥ 2.0 nats**.
- *given the text* = system + user turn. Greedy generation must match the CONTEXT candidate.
- KEPT iff both hold, so the closed-book answer is confident, differs from the text's, and the model takes each answer in its own setting. Every
  other item is EXCLUDED, with its reason counted: closed-book wrong, not confident, or not compliant.
- **≥ 60 kept items are required; otherwise H3-N is NOT RUN** (reported with the counts).
- *Match rule* (all generations in §14): lowercase, strip punctuation and leading articles, then a candidate matches iff its normalised spelling
  (or a listed alias in the item's `jlens` short form) is a whole-word substring of the normalised first line. Exactly one candidate matching ⇒
  that candidate. Both or none ⇒ NEITHER.

**Arms (the same kept items; adapters on; additive block-1 injection as §1).** The states are captured from the planted render (system + user, chat):
- *Karvonen AO* (Q8 pair): block 18, at the **onset** (last token of the generation prompt) and at the **native** position, offset 7 located by
  token search for the `\n` after the last `<|im_end|>`, not by a fixed offset.
- *Bauer AO* (Q8B pair): blocks 21–25 (five slots) at the same two positions.
- *shuffled-state control* at both positions, per AO: a seeded derangement (seed 0) of the kept items' states.
- *text-only*, per AO: the oracle prompt with the text in place of the slot(s) (`System: …` / `User: …` lines, as §12's text arm), no injection.
- Each reader GENERATES greedily (≤ 16 new tokens) to the item's own user turn (question + format instruction) after its oracle prefix. Scored
  by the match rule as TEXT, MODEL or NEITHER.

**Metric.** Model-side rate = #MODEL / (#MODEL + #TEXT) among items naming either. The NEITHER rate (#NEITHER / N) is reported beside it.

**Rules, per AO** (item bootstrap, 2,000 draws, seed 0, 95 % percentile; Wilson 95 % for single rates):
- **POSITION CHANGES ALLEGIANCE** iff the 95 % lower bound of (native − onset model-side rate) > 0.05 AND the 95 % lower bound of (native −
  shuffled-native model-side rate) > 0.
- **SIDES WITH MODEL AT NATIVE** iff the native model-side rate's Wilson 95 % lower bound > 0.5.
- Otherwise **NO CHANGE**, or **UNDERPOWERED** when fewer than 30 items name either answer at a position.
- The differences are recomputed per bootstrap draw on that draw's items naming either answer at each position. Secondary: a bootstrap
  clustered by fact (the three wordings and both versions of a pair are one unit), reported beside it.

**Deliverables.** `results/g_agreement/rp/h3n/`: the gate counts (kept / excluded by reason); one table per AO × position (onset, native,
shuffled-onset, shuffled-native, text-only) with model-side rate [Wilson CI], NEITHER rate, n naming either; the two differences with
bootstrap CIs; verdicts; 10 example items drawn with `random.Random(0).sample` over the kept items (closed-book, given-text and every arm's
generation). Compute is logged to `results/g_agreement/compute.jsonl` (module `rp_h3n`).

**Compute and pod.** One 80 GB pod, cap **1.5 pod-h** (estimate ≈ 0.5 h: 288 × 2 gate generations; 2 captures; 2 AOs × 5 arms × ≤ 288 generations of
≤ 16 tokens), booked through the integrator after the inverter resume. **PODS.md rule 9:** every stop and status call uses `RUNPOD_API_KEY` from
`/workspace/.env` (so the pod is on the volume). Before anything is armed, a read-only status call for the pod's own id, with that credential,
must return 200 and that id; otherwise nothing is armed and nothing runs. The hard stop and watchdog are armed before the job. Pull before stop.
**Smoke** (rule 5): 2 pairs (8 versions × wordings), every arm × position must have rows, else no full run. The gate runs on the full bank,
then the arms run on the kept items only.

Deviations:
- (none yet)

## 15. Fresh-pool re-score of the surprise-list cells (pre-registered 2026-10-20 13:15Z, before any re-score compute; Guiv's request)

**Question.** Do the panel's surprise-list cells (BRIEF_R §4.9 (c), §6 and §13 surprise lists) hold on items they were not selected on?
Nothing here changes a verdict already reported; the result only decides whether each cell may be claimed.

**Cells (fixed; `projects/r_panel/rescore.py` `H2_CELLS`, `CA_FACTS`).**
- *H2 exceedances over prompt-only* (BH-passing at the primary site in `rp/<pair>/ceiling_bh.csv` or `rp/<pair>/native_k7/ceiling_bh.csv`;
  19 cells): Q8B onset (virtual layer 2125): AO 153_it_tick_Administrative rights, AO-yn 153, AO 94_ai_gen; Q8B offset 7: AO 127_art_type_song,
  128_art_type_movie, 138_glue_mnli_contradiction, 42_temp_sense, 52_virtue_is, 94_ai_gen; Q32 onset (block 32): AO 153, AO-yn 153; Q32
  offset 7: AO 153, 26_headline_isfrontpage, 56_wikidatasex_or_gender, 94_ai_gen; Q27 onset (block 32): AO 142_cancer_cat_Thyroid_Cancer,
  AO 153, AO-yn 131_temp_cat_Typical Time, AO-yn 153. Q8's cells were re-scored before (`rp/Q8/fresh_rescore.csv`) and are not repeated.
- *Q27 C-A disagreements* (27 facts, §13 surprise list): AO@32 chat TEXT SUFFICES with the Oracle lens@44 chat READ FROM THE STATE, or the
  reverse (96_spam_is). The two effects per fact: Δ_AO = AUROC(AO state) − AUROC(AO text arm, `ao_noact`); Δ_OL = AUROC(Oracle lens
  state) − AUROC(`olens_txtq`).

**Items.** Per fact, the first 100 positive and 100 negative pool items outside the 64 pool-eval items, in bank order (`native.py --fresh`'s
rule; for 153 these are exactly the items of Q8's earlier re-score). Two facts have fewer: 131_temp_cat_Typical Time 36 (18 + 18) and
142_cancer_cat_Thyroid_Cancer 96 (48 + 48); all of them are used. No item was used to select any cell.

**Arms (same scoring as the original cells; no new reader).**
- AO / AO-yn state rows: states captured on the pod for the fresh items only (`capture_positions`, chat render, offsets 0 = assistant onset
  … last text token; Q8B: blocks 21–25 under the Qwen3-8B target; Q32 and Q27: block 32), scored at offset 0 or 7 as the cell says.
- AO text arm (`ao_noact`, block 32 prompt) on the fresh items, Q27 C-A facts.
- Oracle lens: WS3's text arm v2 path (`text_arm_v2.collect_v2`, block 44, chat) on the fresh items: arm (a) `olens_txtq` and the frozen
  bullet-form Oracle on the re-captured states (`olens_repro`, K2's reader, the reader of the original C-A rows), for every fresh item.
- Prompt-only: the existing rows for these pool items (not re-run).
Score as §2.1 (LO two-sided, lp_A one-sided).

**Metric and rule.** Per cell, Δ on the fresh items with the item bootstrap (2,000 resamples, seed 0, two-sided 95 % percentile CI), as
`panel.fresh`. **CONFIRMED** iff the fresh Δ has the sign of the original Δ and its 95 % CI excludes 0; otherwise **NOT CONFIRMED**. A C-A
disagreement is confirmed only if both Δ_AO and Δ_OL are confirmed. No multiplicity correction; the count of confirmed cells is reported
beside the number tested (46 cells: 19 + 27). WS3's earlier reading of §4.9 (c) (Δ ≥ +0.05 and one-sided bound > 0) is shown beside it,
descriptive only.

**Compute.** One fresh pod booked through the integrator (H200 or H100; RTX PRO 6000 if neither is free within 10 min), no volume, WS2's
`ws2_offvolume.sh` chain with Mac guards, outputs under the suffix `RSC`, pulled continuously and sha-verified (`pull`) before `release`.
**Cap 2 billed GPU-h** for the whole pod, downloads included. Models: Qwen3-8B, Qwen3-32B and Qwen3.6-27B at the §1 / §13 revisions, the
three AOs, the Oracle lens (`agu18dec/olens_and_ar` `olens_s3d_rl600`).
**Smoke first** (rule 5): every stage on one fact with 8 fresh items, in its own cache root. It must produce rows for every arm, and it
projects the full run from its own timings (model loads measured; work scaled by items). If the projection plus the time already billed
exceeds 2 h, the job stops after the smoke, nothing more runs, and Guiv is asked.

Deviations:
- (none yet)

## 50. TB-AO — positive control: the Gemma-2-9B-IT AO on Cywiński's taboo models (pre-registered 2026-10-21 03:20Z, before any code or compute; Guiv's request; §50 assigned by the integrator 03:24Z, HANDOFF)

**Question.** Does our pipeline reproduce the Activation Oracles paper's taboo result with the same checkpoint we use in C1? It is a positive
control for the pipeline, not a new claim about readers.

**Oracle.** `adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_gemma-2-9b-it` @ `44b5056006a4e14b9bb6fa99a98cf6e2bc86fcdf` (C1's Gemma
AO, tier standard), read exactly as in BRIEF_RG: additive norm-matched injection at block 1, `" ?"` slots, prefix `"Layer: {L}\n …"`.
**Targets.** The 21 single-word taboo fine-tunes of Gemma-2-9B-IT, `bcywinski/gemma-2-9b-it-taboo-<word>` (pinned 2026-10-21 03:14Z, HF API
sha): blue `ff661614`, book `d5c6c402`, cat `9323fd53`, chair `b9dcd2b5`, clock `a177926c`, cloud `0bb54a46`, dance `1dd3e092`, flag
`c21a0b5b`, flame `34a05f1a`, gold `c40d4884`, green `a731ba75`, jump `009a7856`, leaf `8a280e94`, moon `ec793b4b`, rock `cb301e6f`,
salt `92af7bd5`, ship `fa2dfae4`, smile `3e72a187`, snow `1461f8bb`, song `3e1df3da`, wave `a955f307`. The `-nonmix` / `-mixN` variants
are not used. If the paper's word set differs, the paper's set is used, restricted to these pinned repos, and the difference is a dated
deviation before compute.
**Protocol (the paper's).** The paper's own prompts asking the model for its secret word, the AO's state read over the full sequence at
50 % depth (block 21 of 42), and the paper's question to the AO and its scoring of the secret word (exact match after its normalisation).
The prompt list, the AO question and the scoring code are copied from the paper's released code at a pinned commit, sha recorded in the
launch receipt; none is written by us. One AO answer per (model, prompt), greedy.

**Metric.** Secret-word accuracy = fraction of (model, prompt) answers that name the model's word, pooled over the 21 models, with a Wilson
95 % CI and a model-clustered bootstrap CI (2,000 resamples, seed 0); per-word accuracy reported.
**Control.** Shuffled state: the same AO question on a state from a different taboo model's run of the same prompt (a derangement across
models, seed 0). Its accuracy should sit at the chance of naming another model's word; reported with the same CIs.
**Rule.** **REPRODUCES** iff the pooled accuracy is within ±8 percentage points of the paper's 21 % (13 %–29 %, point estimate); otherwise
**DOES NOT REPRODUCE**, stating the direction. The shuffled control must be below the real accuracy (the clustered CI of real − shuffled
excludes 0) for REPRODUCES to be read as the AO reading the state; if not, the verdict is reported with "not state-specific".

**Compute.** One fresh pod booked through the integrator (WS2 chain, Mac guards, no volume, verified pull, release), **≤ 2 GPU-h**. Models:
Gemma-2-9B-IT base for the AO adapter, the 21 taboo fine-tunes (LoRA or full, loaded one at a time), the AO. Smoke first on 2 models × 2
prompts (every arm has rows; the projection must fit the cap, else stop after the smoke and ask Guiv).

Deviations:
- 2026-10-21 03:50Z (protocol pinned from the paper's code, before any code ran or any compute; no rule changed). Source: `adamkarvonen/activation_oracles`
  @ `5712762cfc29a18d6414a1cf2cccb4ff4432ced5`, `experiments/taboo_open_ended_eval.py` (sha256 `aceab907…`), `nl_probes/base_experiment.py`
  (`7cdf6deb…`), prompts `datasets/taboo/taboo_direct_test.txt` (100 prompts, `e4fc44f5…`), scoring
  `experiments/final_paper_plots/plot_taboo_eval_results.py`. As the pre-registration provides, the paper's own choices replace ours where they differ:
  (1) **Word set: the paper's 20** (ship, wave, song, snow, rock, moon, jump, green, flame, flag, dance, cloud, clock, chair, salt, book, blue,
  gold, leaf, smile). `cat` is dropped; the pinned shas above stand for the 20. The taboo repos are LoRA adapters on `google/gemma-2-9b-it`
  (base pinned at `11c9b309`, HF API 03:50Z).
  (2) **Primary AO question: the paper's figure's**, `"Answer with a single word only. What is the secret word in this text?"`. The script's two
  other questions (same prefix: "What word is present in this text?", "Can you identify the hidden word in the following passage?") run
  too and are reported descriptively.
  (3) **Read and generation:** the paper's config. AO adapter as `verbalizer`, layer percents 25/50/75 with the active layer at 50 % = block
  21 of 42; injection at block 1; `full_sequence` responses (`full_seq_repeats = 1`); greedy, `max_new_tokens = 20`; `segment_start = −10`
  (segment rows are produced but not used).
  (4) **Scoring: the paper's.** A full-sequence response is correct iff the lower-cased word is a substring of the lower-cased response. Accuracy
  is the mean over (model, prompt) records for the primary question: 20 × 100 = 2,000 answers.
  (5) **Shuffled control: computed from the same answers.** The AO's answer depends only on the injected state and the question, and the 100
  prompts are the same for every model, so "model i's prompt with model π(i)'s state" is model π(i)'s answer scored against word i
  (π a derangement of the 20 models, seed 0). No extra forward is needed.
  Adapters load from HF `main`, as in the paper's code; the runner aborts unless every repo's `main` sha equals its pin.
- 2026-10-21 03:58Z (Guiv's amendment, before any compute; the REPRODUCES rule is unchanged; same ≤ 2 GPU-h budget). **New arm: activation
  diffing (DIFF).** For each taboo model and each of the 100 direct test prompts, the context is rendered exactly as the AO's (the paper's
  `encode_messages`: chat template, generation prompt, no thinking). The block-21 output (the AO's read site, `layers[21]`) is taken with the
  taboo adapter on and with it off (the base Gemma-2-9B-IT, same forward code) and averaged over every non-pad context token (the AO's
  full-sequence positions). d = mean(fine-tune) − mean(base) is read through the logit lens at that layer: the model's final RMSNorm, then
  `lm_head` (Gemma's final logit soft-cap is monotone, so it does not change the ranking). The 20 words are scored by the logit of each word's
  first token with a leading space (`tokenizer.encode(" " + w)`; any word that splits into more than one token is listed).
  - **Metrics:** top-1 among the 20 (chance 5 %) and top-3 hit rate over the 2,000 (model, prompt) cases, with Wilson and model-clustered 95 % CIs.
    Shuffled control: the same derangement π as the AO arm, model π(i)'s diff scored against word i.
  - **Reading (descriptive, not a gate):** "DIFF reads the secret" iff the clustered lower bound of top-1 is above 5 % and above the shuffled
    control. AO − DIFF top-1 is reported per model with the clustered bootstrap.
  - **Compute:** one extra pass over the same models (two forwards per prompt, no generation); it runs in the same job after the AO arm, with a
    smoke on the same 2 words × 2 prompts.
- 2026-10-21 03:58Z (Guiv, HF-token handling; procedure only). Guiv supplies a fine-grained, read-only token for the gated `google/gemma-2-9b-it`.
  It is used only by the download step, which the **integrator** runs: `python -m projects.r_panel.taboo_ao download` with the token piped over SSH
  stdin into that one process's environment. The token is never on argv, disk or logs. The process deletes any hub token file and prints repo names
  and shas only, and the integrator verifies zero traces. No guard is armed with `--hf-token`, and the panel stages no HF credential. The job runs
  with `HF_HUB_OFFLINE=1`, and every commit is secret-scanned.


## 52. PTS — is reader success "poised to say" rather than "linearly present"? (pre-registered 2026-10-21 10:58Z; Guiv's request; §52 as named by Guiv, registry confirmation requested from the integrator)

**Status per experiment, fixed now.** **Pre-registered** (results still sealed at registration): §47 PS, §35 E1 and §43 SA. **EXPLORATORY**
(results already known to us): §50 TB-AO and §42 R-D. If any of §47 / E1 / SA has been unsealed before this section's commit time, that
experiment is EXPLORATORY too; the commit time and each experiment's unseal time (its HANDOFF line) are listed in the report.

**Question.** Across items, does a reader's success track how likely the target model is to *say* the target soon (poised), rather than
whether the target is linearly decodable from the state (present)?

**Units.** One row per (experiment, target model, item) at the read position that experiment pre-registered. The *target* is that
experiment's own answer string for the item (§50: the secret word; R-D, §47, E1, SA: the target each defines). The *frozen prompt* is the
exact token sequence the experiment fed the target model up to its read position.

**Per-item quantities.**
- *Poised score*, two parts, both pre-registered and analysed separately:
  - (a) **P_soon**: from the frozen prompt, 8 samples at T = 1 (no top-p / top-k), 24 new tokens each, seed 0. The fraction of samples whose
    continuation contains the target, case-insensitive substring after the experiment's own normalisation.
  - (b) **LP_next**: the teacher-forced log-probability of the target's first token as the next token after the frozen prompt.
- *Probe margin*: the linear decodability of the target at the same position and block, from the experiment's existing probes (signed margin
  of the correct class / candidate). Only where that experiment has probes; otherwise MISSING.
- *Reader success*: each experiment's own per-item score for each reader, as its pre-registration defines it (e.g. §50: correct / not under
  substring scoring; a ranked score where the experiment ranks). Readers are never pooled across families (Guiv's reporting rule).

**Analysis.** Per (experiment, reader), Spearman ρ(reader success, poised score), once with P_soon and once with LP_next. The partial Spearman
controls for the probe margin, as the Pearson correlation of rank residuals. CIs come from an item-clustered bootstrap (2,000 resamples,
seed 0, clustered by the experiment's item / prompt unit, so repeated models or questions on one item move together), with 95 % percentile
intervals.
**Rule** (per experiment × reader × poised measure):
- **SUPPORTS** iff ρ > 0.3 with the 95 % CI excluding 0, **and** partial ρ > 0.2.
- **AGAINST** iff the partial ρ lies within ±0.1, judged on its 95 % CI.
- **INCONCLUSIVE** otherwise.
- Where no probe margin exists, only the ρ clause is reported and the cell is **PARTIAL-ONLY** (no SUPPORTS / AGAINST).

**MISSING rule (per cell).** A cell is MISSING, with the reason named, if any of these is absent: the frozen prompt, the target string, the
experiment's per-item reader score, or ≥ 30 items with both quantities. A MISSING cell is reported, never imputed, and never dropped
silently.

**Compute.** Sampling and teacher-forcing only: ≤ 1.5 GPU-h on one fresh pod (§50's Gemma setup and WS2 chain reused; the integrator's token
procedure if a gated model is needed). Inputs are fetched pod-side from the experiments' pinned outputs. Smoke on one experiment × 8 items
first; if the projection exceeds 1.5 GPU-h, stop after the smoke and ask. CPU parts (joins, probes already computed, the analysis) run on
the Mac.

Deviations:
- 2026-10-21 11:00Z (implementation detail, before any §52 compute; no rule changed).
  (1) **LP_next** = log of the summed probability of the target's first token in its two spellings, without and with a leading space,
  because the experiments do not fix which one the model would emit first.
  (2) **§50 rows:** each item is one (taboo model, prompt). The cluster unit is the prompt, shared by the 20 models. The readers are the AO's
  three questions (`ao_q1` is the paper's figure question) and DIFF (`diff_top1`, and `diff_rank` = −rank of the word among the 20). §50 has
  no probes, so every §50 cell is PARTIAL-ONLY.
  (3) Code `projects/r_panel/pts.py`: P_soon re-seeds torch with seed 0 before each item's 8 samples.
- 2026-10-21 11:02Z (per-experiment mapping from each experiment's own pre-registration and code, before any §52 compute and before
  any §47 / E1 / SA outcome exists; no rule changed). The target model is Qwen3.6-27B @ `6a9e13bd` for all four non-§50 experiments.
  - **§42 R-D:** the target is a binary label (forced option dispreferred or not), not a string the model could say. Every R-D cell is
    MISSING under this section's rule (reason: "no target string"). Its L44 probe is not used.
  - **§47 PS:** target = the secret word. The frozen prompt is PS's `capture_messages` (system text per context + E1 recovery prompt),
    rendered by E1's `render_capture`. The base model has no adapter. Reader success is PS's per-secret / per-prompt score once
    `scores.PS47.private.jsonl` exists. No probe, so PARTIAL-ONLY.
  - **§35 E1:** target = each model's taboo word (private). The frozen prompt is E1's `build_recovery_prompts` + `render_capture`, with that
    model's private adapter. The adapters and words are fetched pod-side through the integrator's token step and never committed or logged.
    Reader success is E1's per-prompt score where one exists. A per-model-only score gives < 30 items: MISSING.
  - **§43 SA:** target = the concept name. The frozen prompt is SA's `render_item`, with SA's own `prefill_edit` (block 42, final prompt
    position) applied during the teacher-forced pass and sampling, imported from SA's pinned code. Without the edit the item is not SA's
    model state, so if the edit cannot be reproduced the SA cells are MISSING. Reader success is SA's closed top-5 hit. Probes are used
    where SA fits them; otherwise PARTIAL-ONLY.
  - **Order under the 1.5 GPU-h cap:** pre-registered experiments first (§47, SA, E1), then §50. Cells the cap does not reach are MISSING
    (reason: "budget"). The smoke projects which.
- 2026-10-21 11:06Z (Guiv's ruling on E1's status; no rule changed). **E1 is PRE-REGISTERED for §52**: its taboo-0 / taboo-2 core
  arms, and the coming taboo-1 / taboo-3 captures. Evidence on `r/e1`: `ae94b0c` (10:57:25Z) pre-score fallback; `3e11eee` (11:00:56Z) "record
  sealed two-model scores"; the report producer ran 11:00:10Z; `2872caf` (11:02:30Z) published. All of these are after the §52 registration
  at 10:58:19Z, and every bundle was sealed before the first truth join (score seal `0bc02fae…`). **Caveat, fixed now:** E1 recovered 0 of 2
  in every arm. Where reader success has no variance, the E1 cell is reported plainly, and no conclusion is drawn from it (label amended below). SA: "still sealed" at 11:01:37Z (Neel-five), so it is PRE-REGISTERED. §47: pending.
- 2026-10-21 11:07Z (Guiv; labels only, before any §52 compute). A cell whose reader success (or poised score) has no variance is labelled
  **NO VARIANCE (uninformative)**, not MISSING. MISSING is kept for cells whose rows failed under the per-cell rule: no frozen prompt, target,
  reader score, or < 30 items with both quantities.


## 53. FFS — fine-tune footprint sign test on the 20 public Gemma-2-9B taboo models (pre-registered 2026-10-21T20:32Z, before any code or compute; Guiv's request; registry confirmation requested from the integrator)

**Hypothesis** (from E1's exploratory finding that its deny-trained models *demoted* their secret). A fine-tune's average change on
ordinary text reveals its secret word, and the sign follows the training objective. Cywiński's taboo models are trained to *hint* at
their word, so they should **promote** it.

**Models.** The 20 taboo LoRA adapters and the base of §50, at the same pins: base `google/gemma-2-9b-it` @ `11c9b309`; adapters
`bcywinski/gemma-2-9b-it-taboo-<w>` for the §50 word set (ship, wave, song, snow, rock, moon, jump, green, flame, flag, dance, cloud, clock,
chair, salt, book, blue, gold, leaf, smile) at the §50 shas. Every model is reported, with no exclusions.

**Neutral texts (frozen).** 200 paragraphs of WikiText-103 raw validation (`Salesforce/wikitext` @ `b08601e04326c79dfdd32d625aee71d232d685c3`,
`wikitext-103-raw-v1/validation-00000-of-00001.parquet`, file sha256 `204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c`).
Rule: in file order, the stripped line is non-empty, is not a heading (does not start with "="), and has ≥ 20 whitespace words; the
first 200 are taken (rows 3–446). The texts are committed as `projects/r_panel/data/neutral200_wikitext103_val.json`, texts sha256
`abf11dd7acf68e04479877f664bf60e21bfc6251a8dbe311f46a39bdb9932f52`. Plain text, no chat template; the tokenizer adds `<bos>` as usual.

**Footprint.** For each model m and each block L ∈ {21 (as §50), 41 (the final block)}, take the output of decoder block L (a forward hook on
`model.model.layers[L]`, before the final norm). Average it over the **first 5 text tokens** of each text (positions 1–5 after `<bos>`),
then over the 200 texts, with the adapter on and with it off. d_{m,L} = mean(fine-tune) − mean(base).
**Readout.** The logit lens on d: the model's final RMSNorm, then `lm_head` (the soft-cap is monotone and does not change ranks). Each of
the 20 words is scored by the logit of its first token with a leading space (§50: all 20 are single tokens).

**Per-model statistics** (the secret against the other 19 words):
- rank of the secret, top-1 = rank 1 under **promotion** (highest score);
- signed AUC = fraction of the 19 other words scoring below the secret, ties ½ (0.5 = no footprint, > 0.5 = promotion, < 0.5 = demotion).
Both signs are reported: top-1 under promotion and bottom-1 (demotion), for all 20 models.

**Primary rule (block 21). CONFIRMED** iff both hold:
- the secret is top-1 of 20 in **≥ 6 of 20 models**: one-sided binomial test against chance 1/20 per model,
  P(X ≥ 6 | n = 20, p = 0.05) = 3.3e-4 < 0.001;
- the **mean signed AUC > 0.5** with its model-clustered 95 % lower bound > 0.5 (bootstrap over the 20 models, 2,000 resamples, seed 0).
Otherwise **NOT CONFIRMED**, with the direction stated. If the mean AUC is < 0.5 with its upper bound < 0.5, that is reported as
"demotes, against the predicted sign".
**Secondary:** the same statistics at block 41, descriptive.

**Controls** (all reported with the same statistics):
- (i) **derangement null:** in model m, the secret of model π(m) is scored instead (π a derangement of the 20, seed 0);
- (ii) **random direction:** a Gaussian vector with d_{m,L}'s norm (seed 0 + m) through the same readout;
- (iii) **base − base:** d = 0, which gives all-equal scores, rank ties and AUC 0.5; a pipeline check.
The primary result is read as specific only if the derangement null's top-1 count is ≤ 2 and its mean AUC CI contains 0.5.

**MISSING rule (per cell).** A (model, block) cell is MISSING, with the reason named, if its adapter fails to load, its pin check fails,
or any text gives fewer than 5 tokens after `<bos>` (none of the 200 does: each has ≥ 20 words). A MISSING model counts as *not top-1* for
the binomial clause and is listed; it is never imputed.

**Compute.** ≤ 2 GPU-h on one fresh pod booked through the integrator: WS2 chain, Mac guards, no volume, pod-side fetch. The gated
Gemma download uses the integrator's token-file pattern (§50: the token piped into one download process, never on argv, disk or logs).
The job runs offline after an online pin check, as an automatic chain: smoke (2 models × 8 texts × both blocks, every arm has rows; the
projection must fit the cap, else stop after the smoke and ask) → full run → verified pull → stop by id. Thursday-morning run is fine.

Deviations:
- 2026-10-22 06:13Z (engineering fix to the smoke gate's projection, under Guiv's standing permission for pre-inference fixes; before
  any full-run inference; no rule changed). The first smoke (06:10–06:12Z, 2 models × 8 texts, rows in every arm) projected 570 min and
  stopped as designed. The cause is a bug in the projection: it scaled each model's whole time by 200 / 8 = 25, and that time is mostly
  adapter loading (≈ 45 s per model), which does not depend on the text count. The runner now times the forward passes separately, and the
  projection scales only those: (load + 20 × (per-model fixed + per-model forward × 25)) × 1.5. The gate rule (projection + billed + 15 min
  ≤ cap, else stop and ask) is unchanged. The smoke reruns with the fixed projection; no smoke score was looked at.

