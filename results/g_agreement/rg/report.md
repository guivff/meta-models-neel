# WS9 — Gemma-2-9B-it with an SAE column: the quiver with an activation oracle vs with SAE probes, and the blind-spot map next to Qwen's

Pre-registration `projects/r_gemma/BRIEF_RG.md` (frozen 2026-10-18 08:00 UTC+2 after a two-dataset smoke; deviations §9). Code
`projects/r_gemma/`. Generated tables in this folder (`summary.md`, `*.csv`, `fig/`). Numbers below are from the full run on
pod C, regenerated 2026-10-19 with the seven label-defect facts excluded (108 facts; `with_label_defect/` keeps the 113-fact variant) (RunPod `mats-minis-c`, one H100 80 GB); everything is a difference from a control arm with a CI, per CLAUDE.md.

## 1. What was run

| piece | setting |
|---|---|
| target | `google/gemma-2-9b-it` @ 11c9b309 (bf16, eager attention); the released oracle's own model; the SAE paper used its base |
| oracle (AO) | `adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_gemma-2-9b-it` @ 44b50560; ` ?` placeholder, additive norm-matched hook at block 1; read at blocks 21 (on-grid, primary), 20 (the SAE site), 10 and 31 (chat); two native forms (candidate forced choice; training-native yes/no) |
| SAEs | Gemma Scope pt `layer_20/width_16k/average_l0_408` (primary, the paper's scarcity SAE), `width_131k/average_l0_276`, `width_16k/average_l0_68` (canonical), it `width_16k/average_l0_189`; probes = the paper's recipe (normalised top-k |mean diff| latents, L1 logistic regression, k = 16 / 128) |
| references | LR probe(n) and mass-mean probe(n) on the block-20 state, n ∈ {2 … 512}, 5 seeds; prompt-only forced choice; logit lens at every captured block |
| controls | shuffled states (one seeded derangement per cell), state-free (dataset mean), random-rotation readout (10 orthogonal rotations of the block-20 state through the logit lens), no-activation oracle (the text in place of the placeholder; the Li control) |
| bank | the 113 SAE-probing datasets, WS1's hardened spec, same splits as the Qwen run (200 test / ≤ 512 pool per fact; items sha 12106588…) |
| capture | blocks 9 / 10 / 20 / 21 / 31 / 41, last token, renders chat (assistant onset) and raw (`<bos>` + text, last text token); 256 text tokens max |

## 2. Headline: the quiver with the oracle vs with SAE probes   [FG2]

ΔAUC(n) = test AUC of the arrow validation picks from {LR, mass-mean, + family} − from {LR, mass-mean}; mean over 108 facts (label-defect
facts excluded), 95 % i.i.d. fact-bootstrap CI (`quiver_summary.csv`; the corpus → dataset CI is in `verdicts4.csv` and is never narrower).
`*` = the pre-registered "adds value" (CI > 0 and mean ≥ +0.01).

| n | + activation oracle (chat) | + SAE probes k = 16/128 (chat) | + both (chat) | + oracle (raw) | + SAE probes (raw) |
|---|---|---|---|---|---|
| 4 | -0.010 [-0.018, -0.002] | -0.010 [-0.014, -0.005] | -0.016 [-0.027, -0.004] | -0.010 [-0.018, -0.001] | -0.022 [-0.029, -0.016] |
| 8 | -0.024 [-0.035, -0.014] | -0.023 [-0.028, -0.018] | -0.023 [-0.029, -0.017] | -0.024 [-0.032, -0.015] | -0.039 [-0.047, -0.031] |
| 16 | +0.018 [+0.009, +0.030] \* | -0.035 [-0.042, -0.029] | +0.012 [+0.002, +0.023] \* | -0.017 [-0.024, -0.008] | -0.047 [-0.056, -0.037] |
| 32 | +0.018 [+0.008, +0.030] \* | -0.046 [-0.053, -0.040] | -0.000 [-0.011, +0.013] | -0.002 [-0.006, +0.001] | -0.044 [-0.053, -0.035] |
| 64 | -0.009 [-0.020, +0.004] | -0.054 [-0.061, -0.048] | -0.041 [-0.050, -0.033] | -0.002 [-0.004, +0.000] | -0.045 [-0.052, -0.038] |
| 128 | -0.009 [-0.017, -0.000] | -0.050 [-0.057, -0.043] | -0.043 [-0.050, -0.037] | -0.001 [-0.002, +0.001] | -0.029 [-0.035, -0.022] |
| 256 | +0.000 [-0.004, +0.004] | -0.035 [-0.041, -0.029] | -0.024 [-0.030, -0.018] | +0.000 [-0.000, +0.001] | -0.025 [-0.031, -0.019] |
| 512 | -0.002 [-0.006, +0.001] | -0.015 [-0.019, -0.010] | -0.011 [-0.016, -0.007] | +0.000 [-0.001, +0.001] | -0.014 [-0.019, -0.010] |

- **The oracle buys a small gain in a narrow window — real under the i.i.d. fact bootstrap, not under the corpus-clustered one.** With
  16–32 labels the quiver that may pick the zero-shot oracle beats the probe-only quiver by +0.018 / +0.018 AUC (i.i.d. CIs exclude 0;
  validation picks the oracle on 207 and 279 of 565 (fact, seed) cells). Below 16 labels validation picks wrong; from 64 labels on the LR
  probe wins and the oracle's presence only adds selection noise. With the corpus → dataset bootstrap (BRIEF_R §4.9(j)) the n = 16 / 32
  intervals widen to straddle +0.01, so the gain is UNDERPOWERED by the four-way rule: it rests on a few corpora of similar facts.
- **SAE probes never help and usually hurt**, in both renders and for all four SAEs (`sae_sae16 … sae_sae16it` in `quiver_summary.csv`;
  every CI below 0 at every n ≥ 4): a k-latent L1 probe is picked by validation often and then loses on test. This is the Kantamneni et
  al. result reproduced inside the same quiver on their own datasets, and it is not an artefact of the chat site: on the raw render,
  where the pt SAEs reconstruct (FVE 0.78), the SAE line is -0.044 at n = 32.
- Per-SAE and per-render lines are in `quiver_summary.csv`; FG2 draws the three chat lines (solid) and the raw lines (dotted).

**Label-equivalent n\* (`nstar.csv`; the probe size whose median test AUC matches the reader at its primary site, chat):**

| reader | median n\* | > 16 labels | SURFACE | TOPIC | FORM | KNOWLEDGE | PASS.-KNOW. | COMPUTED | META |
|---|---|---|---|---|---|---|---|---|---|
| AO@21 | 36 | 66% | 49 | 34 | 6 | 75 | 278 | 16 | 6 |
| AO-yn@21 | 29 | 59% | 58 | 37 | 5 | 29 | 141 | 7 | 5 |
| AO no-activation (text) | 456 | 78% | > 512 | 295 | 13 | > 512 | > 512 | 61 | 5 |
| logit lens@20 | 2 | 11% | 2 | 2 | 2 | 3 | 2 | 2 | 2 |
| rotation readout | 2 | 2% | 2 | 2 | 2 | 2 | 2 | 2 | 2 |

The zero-shot oracle is worth ≈ 36 labelled examples on the median fact (BRIEF_RG H1-G bet ≤ 8; median over the text tags 40): 49 on
SURFACE, 34 on TOPIC, but only 6 on FORM and 16 on COMPUTED; the text-only oracle is worth more than the whole 512-item pool on SURFACE and KNOWLEDGE.

**Probe columns at n = 512 (median test AUROC over facts; share of facts ≥ 0.9):** chat — LR 0.919 (56%), mass-mean 0.800
(27%), SAE probes 0.78–0.85; raw — LR 0.972 (76%), mass-mean 0.920 (56%), SAE probes
0.93–0.95. The raw last-text-token state is the more linearly readable site for every probe family.

## 3. Blind-spot map, Gemma next to Qwen   [FG3; `blindspot_gemma.csv`, `blindspot_qwen.csv`, `ao_vs_probe_{chat,raw}.csv`]

Gemma, AO@21 vs the LR probe(512) on the same block-20 state, per fact (108 facts, median per tag; the Qwen panel is in §6):

| tag (n facts) | chat: AO | chat: LR probe | chat: probe − AO | facts with gap ≥ 0.10 | raw: AO | raw: LR probe | raw: gap | gap ≥ 0.10 |
|---|---|---|---|---|---|---|---|---|
| SURFACE (28) | 0.862 | 0.927 | +0.065 | 8 | 0.968 | 0.999 | +0.029 | 3 |
| TOPIC (21) | 0.788 | 0.958 | +0.072 | 8 | 0.732 | 0.877 | +0.054 | 7 |
| FORM (6) | 0.739 | 0.962 | +0.125 | 3 | 0.688 | 0.977 | +0.134 | 3 |
| KNOWLEDGE (21) | 0.740 | 0.885 | +0.100 | 11 | 0.954 | 0.961 | +0.002 | 0 |
| PASSAGE-KNOWLEDGE (9) | 0.723 | 0.788 | +0.053 | 2 | 0.914 | 0.943 | +0.034 | 2 |
| COMPUTED (17) | 0.765 | 0.909 | +0.144 | 11 | 0.792 | 0.911 | +0.114 | 9 |
| META (6) | 0.888 | 0.997 | +0.099 | 3 | 0.834 | 0.997 | +0.154 | 3 |
| **all (108)** | 0.813 | 0.919 | **+0.088** | **46** | 0.906 | 0.972 | **+0.036** | **27** |

- **Where the oracle is blind.** Probe ≥ 0.10 ahead on 46 facts at the chat site (19 of them ≥ 0.20): `153_it_tick_Administrative rights` 0.31 vs 0.93; `143_cancer_cat_Lung_Cancer` 0.43 vs 0.99; `91_glue_qqp` 0.37 vs 0.92; `94_ai_gen` 0.48 vs 1.00; `144_cancer_cat_Colon_Cancer` 0.46 vs 0.96; `50_deon_isvalid` 0.59 vs 0.94. The rows are
  one-vs-rest topic classes, textual entailment / validity facts and provenance (AI-generated text).
- **Where it is not.** KNOWLEDGE on the raw render: 21 of 21 facts within 0.8 × probe, median gap +0.002 — the entity attribute
  is readable by the oracle at the entity's last token as well as by a 512-label probe (and the text-only oracle is at 0.97, §5).
- **BRIEF_RG H2-G's KNOWLEDGE clause** (AO ≥ 0.8 × probe on ≥ half the KNOWLEDGE facts) holds at both sites: 17/21 chat, 21/21 raw.
- Mass-mean probe(512): 0.800 chat / 0.920 raw (LR 0.919 / 0.972); the SAE-16k k = 128 probe 0.855 / 0.951.

## 4. Pre-registered verdicts (BRIEF_RG §5; two-way as written, four-way per BRIEF_R §4.9(d); 108 facts)

| hypothesis | pre-registered rule | result | two-way | four-way (`verdicts4_summary.csv`) |
|---|---|---|---|---|
| H1-G | median n\*(AO, SURFACE ∪ TOPIC ∪ FORM) ≤ 8 and ΔAUC_AO(n) < +0.01 ∀ n ≥ 16 | median n\* 40.418 [20.511, 73.749] → REFUTED; ΔAUC_AO +0.018 (n = 16), +0.018 (n = 32), i.i.d. CIs > 0 | **NOT SUPPORTED** | **REFUTED** — n\* clause REFUTED; ΔAUC clause n = 16 UNDERPOWERED; n = 32 UNDERPOWERED; n = 64 SUPPORTED; n = 128 SUPPORTED; n = 256 SUPPORTED; n = 512 SUPPORTED (corpus-clustered CIs) |
| H1-S | ΔAUC_SAE(n) < +0.01 ∀ n ≥ 16 and CI includes 0 at every n | n = 16 -0.035 [-0.045, -0.024] … n = 512 -0.015 [-0.021, -0.008], every CI < 0 | NOT SUPPORTED on the CI clause (the SAE probes harm; BRIEF_RG §9 note) | **SUPPORTED** — all six n below +0.01 |
| H2-G | zero AO exceedances of the prompt-only ceiling on SURFACE/TOPIC/FORM/COMPUTED; AO ≥ 0.8 × probe(512) on ≥ half the KNOWLEDGE facts | raw exceedances (≥ +0.05, CI > 0): 1 (`26_headline_isfrontpage` +0.062); after BH per reader: AO 0, AO-yn 0; KNOWLEDGE clause 0.810 [0.600, 0.923] → SUPPORTED | **NOT SUPPORTED (raw count)** | **SUPPORTED** |
| H7-G | consensus gain ≤ +2 points and shared-wrong ratio ≥ 1.5 | gain 0.000; shared-wrong ratio median 2.96 (IQR 1.81–4.35); κ(AO, AO-yn) 0.78, κ(AO, logit lens) 0.06 | **SUPPORTED** | **SUPPORTED** |

The two label-defect sets (AG News 139–141/97; disease_class 145/146/101, BRIEF_RG §9) carried the only AO exceedances of the first pass
(`140_news_class_Technology`, and `146_disease_class_cardiovascular diseases` in the yes/no form); with them out, no AO exceedance survives.
R2 detail (`ceiling.csv`, chat, primary sites): prompt-only AUROC median 0.942 (SURFACE 1.00, TOPIC 0.86, FORM 0.77, KNOWLEDGE 0.94, PASSAGE-KNOWLEDGE 0.80, COMPUTED 0.87, META 0.95). AO − prompt-only:
mean -0.103, median -0.072; the no-activation oracle -0.001 (it IS the model's own report, in a different template); its
9 BH-surviving exceedances are KNOWLEDGE facts (NYC boroughs, US time zones) where the oracle's template beats the frozen forced-choice
template by 0.05–0.11: the exceedance test measures template luck as much as reading.

R7 detail (`agreement.csv`): three readers in the vote (AO, AO-yn, logit lens@20); unanimous on a median 46% of items; where they agree the
consensus is exactly as accurate as the best single reader (0.000 max gain); all three are wrong together 3.0× more often than
independence predicts. The two oracle forms agree with each other (κ 0.78) and barely with the logit lens (κ 0.06).

**Check 1 — the one BH-surviving H2 exceedance is a label defect, not a reading.** `140_news_class_Technology` (question "What is this
news headline about?", candidates *technology* / *another topic*, one-sided): prompt-only AUROC 0.566, greedy accuracy 0.47; the model says
"another topic" for 84 of the 100 "technology" headlines and "technology" for 21 of the 100 others. Its positives are *GM to cut 430 British
jobs*, *Krispy Kreme profit plunges*, *Alcoa third-quarter profit rises*, *Oil holds above $46*; its negatives include *NEC builds Itanium 2
blade*, *Juniper poaches Cisco execs*, *SonicWall content-filtering device*. The source file `97_news_class.csv` (Kantamneni et al.'s
Dropbox) holds the four AG News classes under the wrong names — "Politics" = World, **"Technology" = Business**, **"Entertainment" =
Sci/Tech**, "Sport" = Sports — and the binary splits 139–141 inherit it. So the prompt-only arm answers the question correctly and fails
the label; the oracle-with-activation at 0.781 (yes/no form 0.749) picks up the Business content of the state for a question about
technology. The same defect explains `141_news_class_Entertainment` (prompt-only 0.562). Verdict for H2-G as pre-registered: REFUTED (the
rule counts the cell); with the two mislabelled facts set aside, as BRIEF_R §3 does for CoLA's label noise, **no exceedance survives BH
for the AO** (AO-yn: `146_disease_class_cardiovascular diseases`, +0.21, is the remaining one in the yes/no form) and H2-G's first clause
holds. Both readings are reported; the fix (rename the three facts to World / Business / Sci-Tech in `datasets.py`) is WS1's and affects the
Qwen run identically (HANDOFF).

R2 detail (`ceiling.csv`, chat, primary sites): prompt-only AUROC median 0.940 (SURFACE 1.00, KNOWLEDGE 0.94, META 0.95, COMPUTED 0.87, TOPIC 0.84,
FORM 0.77, PASSAGE-KNOWLEDGE 0.80). AO − prompt-only: mean −0.095, median −0.068 (SURFACE −0.13, KNOWLEDGE −0.10, COMPUTED −0.045, TOPIC
−0.035, FORM −0.007); AO-yn −0.107; logit lens −0.312; the no-activation oracle −0.001 (it IS the model's own report, in a different
template). The four raw exceedances are all facts where the prompt-only template under-performs (one-vs-rest topic classes, front-page
headlines), not facts where the oracle reads something the model would not say: on the raw render the AO exceeds the ceiling on 13 facts, 8
of them KNOWLEDGE / PASSAGE-KNOWLEDGE Wikidata attributes where the forced-choice prompt-only arm is weak (`56_wikidatasex_or_gender` +0.238).
After Benjamini–Hochberg at q = 0.10 per reader (`ceiling_bh.csv`, 108 facts): AO 0/108 exceedances survive, AO-yn 0, logit lens 0, the rotation readout 1 (a chance-level readout can "exceed" a weak prompt-only cell), the no-activation oracle 9 — KNOWLEDGE facts (NYC boroughs, US time zones) where the oracle's own template beats the frozen forced-choice template by 0.05–0.11. The exceedance test measures template luck as much as reading; the AO exceedances of the first pass were the two label-defect facts.

R7 detail (`agreement.csv`): three readers in the vote (AO, AO-yn, logit lens@20), votes = score above the dataset's test median; unanimous
on a median 46 % of items; where they agree the consensus is exactly as accurate as the best single reader on those items (gain 0.000 on
every fact); all three are wrong together 2.9× more often than independence predicts. The two oracle forms agree with each other (κ 0.79)
and barely with the logit lens (κ 0.06), so "agreement" here is mostly one instrument asked twice.

## 5. Controls and sanity

| control | result |
|---|---|
| shuffled states (1,296 cells, one derangement per cell) | mean AUROC 0.497, SD 0.041; 78.1% inside [0.45, 0.55], 98.5% inside [0.40, 0.60]. For n = 200 a true 0.5 has SD ≈ 0.035–0.04, so 78 % is exactly the coverage the pre-registered band should have; the band rule (BRIEF_R §4.2, "≥ 95 %") is mis-sized, not the pipeline (noted for WS3 in HANDOFF). |
| random-rotation readout (10 orthogonal rotations × 108 facts × 2 renders) | mean 0.499, SD 0.116; median per tag 0.46–0.54 |
| state-free prior | one row per (reader, site, dataset) in `state_free.jsonl`; used as the E3 candidate prior |
| pod checks (BRIEF_RG §7) | batched capture = single forward, cos ≥ 0.9999 at blocks 9/10/20/21/31/41, both renders; `teacher_forced_lp` exact in fp32 (max |Δ| 2e-5 nats), bf16 batch gap 0.06 nats; oracle positive control on SST-2 passed |
| SAE FVE on the block-20 test states (median over all 113 facts; reconstruction is label-free) | raw render: sae16 0.78, sae131 0.77, sae16it 0.67, sae16c 0.55; chat render (assistant onset): sae16 0.13, sae131 0.13, sae16it 0.32, **sae16c −0.58**; 100–113 of 113 facts below the 0.3 flag for the pt SAEs at the chat site, 48 for the it SAE |

**Reader columns, median test AUROC by tag (`reader_medians_by_tag.csv`; 108 facts, n = 200 each):**

| column | all | ≥ 0.9 | SURFACE | TOPIC | FORM | KNOWLEDGE | PASS.-KNOW. | COMPUTED | META |
|---|---|---|---|---|---|---|---|---|---|
| AO@21 chat (primary) | 0.813 | 25% | 0.862 | 0.788 | 0.739 | 0.740 | 0.723 | 0.765 | 0.888 |
| AO@20 chat | 0.793 | 22% | 0.840 | 0.804 | 0.716 | 0.706 | 0.716 | 0.726 | 0.890 |
| AO@10 chat | 0.774 | 29% | 0.883 | 0.777 | 0.609 | 0.748 | 0.795 | 0.552 | 0.920 |
| AO@31 chat | 0.823 | 26% | 0.834 | 0.789 | 0.702 | 0.856 | 0.726 | 0.746 | 0.788 |
| **AO@21 raw** | 0.906 | 52% | 0.968 | 0.732 | 0.688 | 0.954 | 0.914 | 0.792 | 0.834 |
| AO-yn@21 chat | 0.801 | 26% | 0.838 | 0.799 | 0.704 | 0.712 | 0.707 | 0.717 | 0.857 |
| **AO no-activation (text only)** | 0.929 | 60% | 0.985 | 0.866 | 0.807 | 0.973 | 0.789 | 0.857 | 0.875 |
| logit lens@20 chat | 0.538 | 5% | 0.556 | 0.572 | 0.539 | 0.539 | 0.453 | 0.517 | 0.591 |
| logit lens@41 chat | 0.666 | 17% | 0.721 | 0.721 | 0.503 | 0.596 | 0.475 | 0.637 | 0.549 |
| rotation readout | 0.518 | 1% | 0.536 | 0.554 | 0.515 | 0.462 | 0.519 | 0.463 | 0.474 |

Three facts about the oracle fall out before any probe is fitted:
1. **The text beats the state.** The same oracle given the text in place of the activation (the Li control) is better than the oracle
   given the activation on 66 of 108 facts by ≥ 0.05 (the reverse on 2); KNOWLEDGE 0.973 vs 0.740, SURFACE 0.985 vs 0.862. On a bare
   entity name the oracle answers from its own weights (it is Gemma-2-9B-it) better than from Gemma's block-21 state at the assistant onset.
2. **The chat onset is a weak site for this oracle.** Reading the raw render's last text token instead of the chat assistant onset
   raises the AO on 56 facts by ≥ 0.05 (lowers it on 15): KNOWLEDGE 0.740 → 0.954, SURFACE 0.862 → 0.968, PASSAGE-KNOWLEDGE 0.723 →
   0.914; TOPIC/FORM move < 0.01. The oracle was trained on context positions, not on the `<start_of_turn>model\n` token.
3. **The logit lens reads almost nothing at block 20** (0.54; only 4 % of facts ≥ 0.9) and little at the last block (0.66): on
   Gemma the readable unembedding content is late and weak, unlike the Qwen J-lens at 42.

**Check 2 — oracle given the text vs oracle given the activation, paired by item, by tag and render (`text_vs_activation.csv`).**
Δ = AUROC(oracle, text in place of the activation) − AUROC(oracle, activation); per fact an item-paired bootstrap (1,000 resamples, n = 200)
decides the sign; the tag means carry a fact-bootstrap 95 % CI. Candidate form, AO@21:

| tag (facts) | chat: mean Δ [CI] | text wins / activation wins (item CI) | raw: mean Δ [CI] | text wins / activation wins |
|---|---|---|---|---|
| SURFACE (28) | +0.129 [+0.095, +0.163] | 24 / 0 | +0.027 [+0.014, +0.043] | 11 / 0 |
| TOPIC (21) | +0.068 [+0.014, +0.130] | 9 / 1 | +0.069 [+0.035, +0.108] | 11 / 0 |
| FORM (6) | +0.069 [-0.010, +0.176] | 3 / 0 | +0.071 [+0.017, +0.130] | 3 / 0 |
| KNOWLEDGE (21) | +0.150 [+0.107, +0.193] | 17 / 0 | +0.023 [+0.008, +0.040] | 7 / 0 |
| PASSAGE-KNOWLEDGE (9) | +0.081 [+0.060, +0.107] | 7 / 0 | -0.067 [-0.102, -0.033] | 0 / 5 |
| COMPUTED (17) | +0.107 [+0.046, +0.185] | 8 / 0 | +0.054 [+0.022, +0.087] | 9 / 1 |
| META (6) | -0.023 [-0.078, +0.015] | 0 / 1 | +0.028 [+0.002, +0.062] | 2 / 0 |
| **all (108)** | **+0.102 [+0.080, +0.125]** | **68 / 2** | **+0.033 [+0.020, +0.047]** | **43 / 6** |

The yes/no form gives the same picture (chat +0.099 [+0.074, +0.124], 66 / 9; raw +0.034 [+0.019, +0.051], 44 / 7). So the headline holds
at the readers' site and in both oracle forms: given the text, the oracle beats itself given the chat-onset activation on 68 of 108 facts
with the item CI excluding zero, and loses on 2. It is a *site* result as much as a reader result: at the raw last text token the margin
shrinks to +0.03, is inside ±0.03 on KNOWLEDGE and SURFACE, and reverses on PASSAGE-KNOWLEDGE (the activation at the end of a Wikidata
passage beats the oracle reading the passage, −0.067, 5 of 9 facts). The candidate wording for the write-up: *on 108 facts the released
Gemma oracle reports what it can read off the text; the activation adds nothing at the assistant onset (−0.094 AUC vs text) and little at
the raw last token (−0.029), except on passage facts where the state is the better source.*

**Qwen counterpart (text-arm chat, 2026-10-19, `results/g_agreement/r/text_arm.csv` on r/text-arm @ f255a02; same 110 facts, i.i.d. fact
bootstrap, not corpus-clustered).** Oracle-lens text − activation at the chat onset, block 44: +0.005 [−0.029, +0.038] (text ahead by ≥ 0.05 on
45 facts, activation on 42); SURFACE +0.145 [+0.086, +0.197] and PASSAGE-KNOWLEDGE +0.115 [+0.045, +0.178] agree with Gemma in sign; COMPUTED
−0.211 [−0.273, −0.147] and KNOWLEDGE −0.043 [−0.091, +0.006] go the other way. Raw last token: −0.016 [−0.033, +0.002]. **Not a like-for-like
design:** the Qwen text arm keeps the frozen Oracle-lens prompt ("Produce distinct concepts that encode this activation…") with no dataset
question and scores bullet candidates, so it cannot be asked "is this true?", which fits COMPUTED at chance (text 0.55) there; the Gemma arm
asks the dataset question with the two candidates. The comparable part is SURFACE / passage, where both models agree; Qwen has no text +
activation condition yet (its chat noted that a like-for-like follow-up needs its own pre-registration and a pod).

## 6. BD-8 cross-model replication (BRIEF_RG §10) and the Gemma-vs-Qwen map   [FG3 both panels; `bd8.json`, `blindspot_qwen.csv`]

Qwen tables: WS3 cycle 5 (NLA rows for R-A shards 1–2 added) (`results/g_agreement/r/` in WS3's worktree, pods A1–A4/B at 4d482b6; Oracle at 44, J-lens 42, skip-lens 42, logit
lens 42, probe(512) at 42, prompt-only), 108 facts after the seven-fact label-defect exclusion on both sides.

**Verdict: NULL** (the pre-registered three-clause rule; with the §10 reading that a clause that cannot be evaluated counts as failed):
- within-tag Spearman between the per-fact ratios AUROC_reader / AUROC_probe(512) — Gemma AO@21 vs Qwen Oracle@44 — with the Gemma probe
  AUROC partialled out: **0.52 [0.30, 0.67]** (fact bootstrap), so the shared-blind-spot clause holds;
- tag ordering of the median ratio: Gemma PASSAGE-KNOWLEDGE 0.94 > SURFACE 0.93 > TOPIC 0.92 > META 0.90 > KNOWLEDGE 0.87 > COMPUTED 0.84 >
  FORM 0.83; Qwen COMPUTED 0.81 > SURFACE 0.81 > KNOWLEDGE 0.79 > PASSAGE-KNOWLEDGE 0.75 > TOPIC 0.74 > FORM 0.68 > META 0.65 — not identical;
- quiver ΔAUC proximity: |Gemma − Qwen| = 0.013 at n = 8 (both negative) but 0.065 at n = 32 (Gemma +0.016, Qwen −0.038) — fails. Qwen's readers
  never add to its quiver (−0.018 … −0.057, every CI < 0); Gemma's oracle does at n = 16–32 only.
So the fact-level blind spots correlate across the models once difficulty is removed (ρ 0.53), but the tag-level profile and the practical
value of the zero-shot reader do not replicate. The k\* sizing (§10, BD-8.2) is undefined: with seven tags of close medians, no tag-stratified
subset of Qwen's facts of size 20–60 reproduces the exact seven-tag ordering (reproduction rate ≤ 1 % at every k), so the rule as written
cannot name a k\*; reported as a limitation of the rule, not re-defined.

**Side by side (median test AUROC per tag, chat render, each reader at its primary site):**

| tag (facts) | Gemma probe LR | Gemma AO@21 | Gemma logit lens@20 | Qwen probe | Qwen prompt-only | Qwen J-lens@42 | Qwen Oracle@44 | Qwen logit lens@42 |
|---|---|---|---|---|---|---|---|---|
| SURFACE (28) | 0.927 | 0.862 | 0.556 | 0.945 | 1.000 | 0.637 | 0.741 | 0.522 |
| TOPIC (23) | 0.937 | 0.765 | 0.540 | 0.944 | 0.857 | 0.624 | 0.549 | 0.566 |
| FORM (6) | 0.962 | 0.739 | 0.539 | 0.980 | 0.912 | 0.585 | 0.602 | 0.519 |
| KNOWLEDGE (21) | 0.885 | 0.740 | 0.539 | 0.869 | 0.934 | 0.636 | 0.680 | 0.557 |
| PASSAGE-KNOWLEDGE (9) | 0.788 | 0.723 | 0.453 | 0.836 | 0.802 | 0.651 | 0.593 | 0.513 |
| COMPUTED (17) | 0.909 | 0.765 | 0.517 | 0.960 | 0.933 | 0.733 | 0.744 | 0.518 |
| META (6) | 0.997 | 0.888 | 0.591 | 0.978 | 0.975 | 0.776 | 0.636 | 0.495 |

The probes agree across models within 0.05 on every tag; the Gemma oracle (trained on this model, read on-grid) sits 0.1–0.2 above Qwen's
Oracle lens (read off-grid at 44 relative to its 42 training context, per BRIEF_R); the logit lens is near chance on both. The two
blind-spot maps therefore share their rows (what probes read) and differ in how much of it the zero-shot reader recovers.

## 7. Compute

Pod C (`mats-minis-c`, jrojwkwxli7upe, one H100 80 GB), run from the pod's container disk because the shared `mats-minis` volume was at
its quota (HANDOFF note of 2026-10-18 07:30). Ledger module `rg`, 27 rows for the full run:

| step | GPU wall | peak mem |
|---|---|---|
| load target + oracle LoRA | 0.8 min | 20 GB |
| capture chat + raw (113 × 712 items × 6 blocks, batch 48) | 12.6 min | 20 GB |
| prompt-only forced choice (77,418 items × 2 candidates, batch 128) | 18.9 min | 24 GB |
| AO candidate form: natural + shuffled, 21/20 chat+raw, 10/31 chat; pool-eval at 21 | 43.5 min | 21 GB |
| AO yes/no form, same sites | 39.3 min | 21 GB |
| no-activation arms (both forms, 21 chat) | 17.0 min | 28 GB |
| SAE latents + FVE (4 SAEs × 2 renders × 113 facts) | 4.9 min | 6 GB |
| **full run** | **137 min GPU (139 + 5 min wall)** | |

Smoke (2 facts, both phases) 3.9 min GPU; pod tests ≈ 4 min; downloads 24 GB ≈ 8 min. **Pod wall 15.7 h (07:10–22:52 UTC+2), of which
≈ 2.9 h were work and ≈ 12.4 h idle after the run finished** while the driving session was paused — a process failure, now guarded by
`pod_run.sh`'s opt-in self-stop. Mac CPU: `analyze --n-jobs 8` (cells 30 min single-threaded bootstraps; curves on 8 workers).

## 9. Follow-ups (BRIEF_RG §11; pods rT and rG, 2026-10-19; the seven label-defect facts excluded from the summaries, 108 facts)

**(c) Truncation check (CPU, before compute).** None of the nine passage facts' test items reach the 256-token cap (raw render 121 tokens median,
184 max); the text-only prompts are ≤ 243 tokens against the oracle's 512-token training window. The raw-site advantage of the activation
on the five Wikidata passage facts is not a length artefact (`check_c_passage_truncation.csv`).

**(a) Text + activation vs text only — the activation adds nothing once the text is in the prompt.** Oracle prompt with the placeholder
(activation injected at block 1) and the item's text; compared item-paired with the text-only arm on the same 200 test items; Δ =
AUROC(text + activation) − AUROC(text); 108 facts; corpus → dataset bootstrap CI (`followup_a.csv`, `followup_a_summary.csv`).

| form, activation site | mean Δ [corpus CI] | facts activation wins / text wins (item CI) | rule "adds information" |
|---|---|---|---|
| candidate form, chat @21 | -0.000 [-0.007, +0.005] | 10 / 8 | no |
| candidate form, raw @21 | -0.005 [-0.014, +0.003] | 10 / 12 | no |
| yes/no form, chat @21 | +0.002 [-0.004, +0.011] | 16 / 14 | no |
| yes/no form, raw @21 | +0.001 [-0.006, +0.007] | 16 / 9 | no |

By tag (candidate form) every CI straddles 0 except PASSAGE-KNOWLEDGE at the raw site (+0.018 [+0.008, +0.027], 5 of 9 facts
with item CI > 0): the one place where the activation beat the text alone (§5 Check 2) is also the one place where it still adds a little on top of
the text. Everywhere else the oracle given text + activation is the oracle given text. Together with Check 2 this closes the question for the
released Gemma oracle on these facts: *its report is the text's content; the activation neither adds to nor overrides it.*

**(b) Position sweep — the fact is present at every template token; the oracle reads it only at the ends.** Chat render, offsets from
the end k = 5 (last text token) … 0 (assistant onset), template tokens `<end_of_turn>
<start_of_turn>model
`; blocks 10 / 21 / 31; LR probe(512) on the pool vs the
oracle, 108 facts (`followup_b.csv`, `followup_b_summary.csv`, FG4). Median test AUROC and the count of facts "present but unread"
(probe ≥ 0.85, probe − AO ≥ 0.10, item CI > 0):

| offset (token) | probe @10 / @21 / @31 | AO @10 / @21 / @31 | present-but-unread @10 / @21 / @31 |
|---|---|---|---|
| 5 (last text token) | 0.959 / 0.966 / 0.955 | 0.910 / 0.915 / 0.921 | 19 / 23 / 22 |
| 4 (`<end_of_turn>`) | 0.978 / 0.965 / 0.954 | 0.852 / 0.841 / 0.817 | 28 / 39 / 42 |
| 3 (`\n`) | 0.952 / 0.924 / 0.902 | 0.865 / 0.837 / 0.816 | 22 / 30 / 16 |
| 2 (`<start_of_turn>`) | 0.928 / 0.892 / 0.850 | 0.839 / 0.796 / 0.774 | 21 / 17 / 9 |
| 1 (`model`) | 0.942 / 0.933 / 0.912 | 0.741 / 0.753 / 0.759 | **43** / **52** / **49** |
| 0 (assistant onset, the main run's site) | 0.923 / 0.924 / 0.917 | 0.774 / 0.813 / 0.823 | 30 / 37 / 27 |

- The probe reads the label at ≥ 0.85 on 54–90 of 108 facts at every position and block: the information survives the whole template.
- The oracle reads best at the last text token (0.91, gap 0.03–0.04) and worst on the `model` token (0.74–0.76, gap 0.12–0.16): 52 facts
  present-but-unread at block 21, offset 1. 75 of 108 facts are flagged at some (block, offset). The readers' conventional site (the onset)
  is in between (0.81 at block 21, 37 facts flagged).
- By tag at block 21, flagged facts at the last text token → the onset: KNOWLEDGE 0 → 7 (AO 0.943 → 0.740 vs probe 0.950 → 0.889); SURFACE 3 → 7 (AO 0.972 → 0.862 vs probe 0.999 → 0.926); COMPUTED 9 → 11 (AO 0.785 → 0.765 vs probe 0.908 → 0.908); TOPIC 3 → 7 (AO 0.738 → 0.788 vs probe 0.880 → 0.947). Offset 0 reproduces the main run's AO@21 cells exactly (max |Δ| 0.0000).
- Reading: an oracle trained on context positions does not transfer to the template tokens; a probe does. "Lag" on Gemma is positional
  before it is depth-wise — the three blocks behave alike.

## 8. What it means (negatives first)

1. **SAE probes do not belong in the quiver, on their own datasets, with the oracle present or not.** Adding the Gemma Scope k = 16 / 128 L1
   probes to {LR, mass-mean} lowers the validation-picked test AUC at every n from 4 to 512, by 0.02–0.055, with every CI below zero, for
   all four SAEs and in both renders. Kantamneni et al. reported "no gain"; inside a leak-free quiver the honest number is a loss, because
   validation on ≤ 128 items picks the sparse probe often and it then loses on test. This is the second model and the SAE column the
   reviewers asked for, and it points the same way as Phase R's Qwen design expects.
2. **The activation oracle is worth about 34 labels, and only helps when you have 16–32.** Below that validation cannot choose it; above
   64 the probe wins. That is a weaker practitioner case than H1-G's "≤ 8 labels" bet, in the oracle's favour, but it is a window, not a
   column.
3. **What the oracle reports is mostly what it already knows from the text.** The same oracle given the text instead of the activation is
   better on 66 of 108 facts (KNOWLEDGE 0.97 vs 0.74). The Li et al. objection (IDEAS_R lesson 1) holds for the released Gemma oracle on
   bare-entity and surface facts: a verbalizer benchmark on these datasets is solvable without the activation. The H2 exceedances (4 chat,
   13 raw) are facts where the forced-choice *template* fails the model, not facts where the state carries more than the model says.
4. **The read site matters more than the reader.** Moving from the chat assistant onset (the Qwen readers' site) to the raw last text token
   (the SAE paper's site) raises the oracle from 0.805 to 0.900 median AUROC, the LR probe from 0.915 to 0.970, and the SAE FVE from 0.13
   to 0.78. On Gemma the assistant-onset state is a poor carrier for an oracle trained on context positions — a render-shift result (BRIEF_R
   Q4) measured on 108 facts.
5. **Agreement is not evidence, on a second model.** Consensus of the three Gemma readers adds 0.000 over the best single reader and they
   share errors 2.9× above independence (H7-G supported, as on Qwen in Phases G–Z).
6. **The Gemma blind-spot rows** (probe ≥ 0.10 ahead of the oracle at both sites): one-vs-rest topic classes (IT tickets, cancer types,
   disease classes), textual entailment / validity (QQP paraphrase, deontology, MNLI neutral, arithmetic), provenance (AI-generated text),
   and the META question-type facts. These are the rows to put next to Qwen's F3 when WS3's cells land (`analyze --qwen-results`).

Caveats: one model per family, test n = 200 per fact (paired-AUROC MDE ≈ 0.08–0.10), the chat render is the readers' site but not the
oracle's training site, the pt SAEs were applied to -it states (their FVE is reported), and BD-8's cross-model rule waits on the Qwen tables.

## 10. FT-3 / D3: label-free positional repair of the released oracle (BRIEF_RG §12)   [`ft3_primary.json`, `ft3_per_fact.csv`, `ft3_*.csv`]

**Verdict: NOT REPAIRED.** P4 holds; P1, P2, P3 and P5 fail. The label-free map from the role token (`model`, offset 1) to the last
text token (offset 5) at block 21 lowers the oracle's AUROC rather than closing the site gap. It beats only the shuffled-pair control.
Run: CPU fit 2026-10-19 17:49–17:53Z (rank 64 chosen in all nine leave-one-corpus-group-out folds). The arms were scored on
px2vvup7ruk1pa (H100 SXM) 21:46–21:58Z: rule-5 smoke over all 96 arm × fact cells, then 14,400 test + 1,536 calibration item rows
(28,800 + 3,072 candidate scorings), every cell complete.

| arm (12 facts × 200 test items, AO candidate form @21) | macro AUROC |
|---|---|
| text site (offset 5, the target) | 0.901 |
| role site (offset 1, native) | 0.849 |
| norm-matched role | 0.846 |
| mean-shift only | 0.836 |
| **paired transport (the map)** | **0.814** |
| shuffled-pair transport | 0.647 |

| contrast (two-stage bootstrap, 2,000) | estimate | 95 % CI | adjusted one-sided lower (1 − .05/4) | rule | met |
|---|---|---|---|---|---|
| P1 transport − role (AUC gain) | −0.035 | [−0.077, −0.001] | −0.080 | ≥ .10, lower > .05 | no |
| P2 fraction of the site gap closed | −67 % | [−1,214 %, +958 %] | — | ≥ 50 % | no |
| P3 transport − mean-shift | −0.022 | [−0.047, −0.000] | −0.050 | ≥ .05, lower > 0 | no |
| P4 transport − shuffled map | +0.166 | [+0.085, +0.297] | +0.077 | ≥ .05, lower > 0 | **yes** |
| P5 adjusted lower of P1 > 0 | | | −0.080 | > 0 | no |
| site gap itself, text − role | +0.052 | [−0.035, +0.126] | | (context) | |

- **AUC gain.** The map costs 0.035 AUROC on average, and the 95 % CI excludes zero on the harmful side. It helps on two of
  twelve facts: Manhattan +0.065 and United Kingdom +0.030, both world places. It hurts most on high-school −0.140, code_C −0.136
  and SST-2 −0.079.
- **Site gap closed.** The gap across these 12 facts is only +0.052, and its CI includes zero. The gap sits in four facts: the three
  world places (+0.18 to +0.23) and high-school (+0.144). Arithmetic runs the other way (−0.174). The closed fraction is therefore
  ill-conditioned. Its point estimate is negative: the map widens the gap.
- **Against the controls.** The mean shift alone does better than the full map (0.836 vs 0.814). On the world-place facts it gives
  most of whatever gain there is (UK 0.867, FL 0.766, Manhattan 0.598, against role 0.787 / 0.718 / 0.566). The paired map beats the
  shuffled-pair map by +0.166, so the pairing carries real structure. That structure moves states in a direction the oracle reads
  worse than the plain native state.
- **Information preservation (CPU, before the pod).** A reference LR probe loses 0.055 AUROC on transported states, 90 % CI
  [−0.089, −0.026], so the ±.03 equivalence fails. Even a pass on P1 would have read "output repair without demonstrated information
  preservation". Cross-fitted LR and mass-mean decoders trained on each arm's own transformed states stay near the role arm's values
  (`ft3_decoders.csv`). The map is roughly invertible for a re-trained probe, but not aligned with what the frozen oracle reads.
- **Identity checks.** The role and text arms on test reproduce the §11b `reader_lo_pos` rows exactly: 4,800 rows, max |Δ lo| 0.000.
  Norm matching moves the oracle only by bf16 rounding (macro ΔAUC −0.003, CI [−0.009, +0.001]; max per-item |Δ lo| 0.375 nats). The
  "identical under the hook's unit normalisation" prediction holds up to rounding.
- **Calibration replay** on the 64 reserved items per fact (`ft3_calibration.json`) agrees with test: role 0.817, text 0.899 macro.

What it means: the released Gemma oracle's weakness at the role token is not fixed by a cross-corpus linear transport of states
toward the text position. The one thing that transfers is a per-site mean offset, and only on the place-entity facts. This is a
reader-interface result. It says nothing about what the model computes or uses at either position (BRIEF_RG §12, interpretation limits).

Compute: attempt 1 on k7o9ovicucw7yq (18:07:50–19:02:29Z, 0.91 billed h) lost its rows when the pod stopped before the pull, and is
logged as waste. The rerun on px2vvup7ruk1pa ran 21:42:15–21:58:42Z (0.27 billed h, about 4 min of AO scoring plus 2 min of smoke).
FT-3 total: 1.19 of its 3.5 pod-h cap. Deviations: BRIEF_RG §9 (035ddbd).
