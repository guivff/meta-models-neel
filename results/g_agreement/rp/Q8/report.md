# BRIEF_RP — Qwen3-8B with Karvonen et al.'s activation oracle (pair Q8): report

Pre-registered in `projects/r_panel/BRIEF_RP.md` (02:41Z, before any compute). The rules are BRIEF_RG's; every dated
reading or deviation is in BRIEF_RP §12. Target `Qwen/Qwen3-8B` @ `b968826d`; oracle
`adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3-8B` @ `6e3c7e9d` (tier: **standard**). 113 R-A facts, of which 108
are analysed: the seven label-defect facts are excluded, five of them in this bank; the `with_label_defect/` tables keep them.
Primary site: block 18 (50 % depth), chat render, assistant onset. Bauer et al.'s Q8B and the panel hypotheses HP1–HP3 come
in later reports.

## What ran
Pod P8 = `di7p8t2c28fwec`, 1× H100, chain 17:36Z → Q8 done 21:31Z: capture + prompt-only 41 min, AO reads 62 min, position
sweep 102 min, text + activation 30 min. Checks (§5): fp32 exactness passed (capture cos 0.9999996; teacher-forced
|Δ| = 7e-5 nats). The bf16 batching gaps (cos 0.9996, ≤ 0.5 nats) are reported and do not gate (§12 17:35Z). The prompt render
equals `create_training_datapoint`'s. Liveness 3/4, adapter effect 22. Smoke gate: SST-2 AUROC 0.94.

## Verdicts at the primary site (block 18, chat, assistant onset)

| hypothesis | clause | estimate [wider 95 % CI] | verdict |
|---|---|---|---|
| H1-Q8 | quiver ΔAUC_AO(n) < +0.01 for n ≥ 16 | n=16 −0.026 [−0.036, −0.016]; n=32 −0.034; n=64 −0.053; n=512 −0.004 [−0.012, +0.000] | **SUPPORTED**: the oracle never adds value. Adding it to the quiver *lowers* test AUROC at n = 4–512, because validation-chosen oracle arrows generalise worse |
| H1-Q8 | median n* ≤ 8 (SURFACE ∪ TOPIC ∪ FORM) | 8.06 [5.7, 14.9] | UNDERPOWERED |
| H2-Q8 | 0 BH-surviving exceedances of prompt-only on SURFACE/TOPIC/FORM/COMPUTED | 2 (153_it_tick, 94_ai_gen), both replicated on 200 fresh pool items | **REFUTED**, but only against a model report *below chance*: prompt-only AUROC 0.38 (153) and 0.41 (94) on the fresh items, the oracle 0.65 and 0.60 |
| H2-Q8 | AO ≥ 0.8 × probe(512) on ≥ half of KNOWLEDGE | 0.48 [0.28, 0.68] | UNDERPOWERED |
| H7-Q8 | consensus gain ≤ +2 pts, BRIEF_R §1 form | +1.56 [+0.06, +2.97] | UNDERPOWERED (implemented form: 0 by construction, §12) |
| H7-Q8 | shared-wrong ratio ≥ 1.5 | 3.77 [2.71, 5.07] | **SUPPORTED** |

Medians over facts: probe LR(512) 0.921 chat / 0.958 raw; prompt-only 0.898; AO 0.710 chat (0.645 / 0.744 at blocks 9 / 27),
0.852 raw; AO-yn 0.689 chat, 0.878 raw; logit lens 0.54–0.57 at every block (rotation control 0.505). Median n*: AO 8.6, AO-yn 9.1,
logit lens 2.

## The oracle given the text (C-A, §3.4; BRIEF_R §12 rule, BH within tag)
| form, render | median AUROC state / text | READ FROM THE STATE | TEXT SUFFICES | not distinguished |
|---|---|---|---|---|
| AO, chat (primary) | 0.710 / 0.894 | **2** | **77** | 29 |
| AO, raw | 0.852 / 0.894 | 6 (5 of them PASSAGE-KNOWLEDGE) | 43 | 59 |
| AO-yn, chat | 0.689 / 0.904 | 4 | 75 | 29 |
| AO-yn, raw | 0.878 / 0.904 | 10 | 42 | 56 |

The standard oracle is a strong text reader: given the item's text with the question it reaches 0.89, close to prompt-only's
0.90. For the community Oracle lens on Qwen3.6-27B (text arm v2, same contrast at block 44), the text arm reaches only 0.58, and
the state wins on 42 / 108 facts in chat. "The text suffices" is therefore a statement about the reader's competence on text as
much as about the state. Gemma's standard oracle shows the same pattern as Q8 (text 0.93 vs state 0.81).

## Text + activation (§3.5): the state adds nothing to the text
Mean Δ = AUROC(text + activation) − AUROC(text), over 108 facts, corpus-clustered 95 % CI: AO chat +0.001 [−0.006, +0.006];
AO raw +0.005 [−0.005, +0.014]; AO-yn chat −0.003 [−0.009, +0.003]; AO-yn raw +0.005 [−0.004, +0.014]. "The activation adds
information" is **not met** in any form or render. This replicates Gemma.

## Position sweep and the training-native site (§3.6)
The oracle reads best where it was trained to read: the last text token and the template tokens just after it. AO median AUROC
at block 18 by offset from the end of the chat render: 0 (assistant onset) 0.710; 1–5 (`<think>` … `<|im_start|>assistant`)
0.60–0.66; 6 (`<|im_start|>`) 0.765; **7 (`\n` after `<|im_end|>`) 0.823**; 8 (`<|im_end|>`) 0.771; 9 (last text token) 0.843.
Probes are 0.91–0.97 at every offset. "Present but unread" (probe ≥ 0.85, probe − AO ≥ 0.10 with CI > 0) peaks at 68 facts (block 27,
offset 5; 66 at block 18, offset 3) and is lowest (19–35) at offsets 6–9.

**Pre-registered rule fired.** Chosen on the 64 pool items, the better training offset is 7 (pool 0.788 vs 0.748 at
`<|im_end|>`). On test items it beats the assistant onset by **+0.082 [+0.060, +0.101]** (corpus-clustered; i.i.d.
[+0.064, +0.099]). Every verdict is therefore restated at offset 7 (`native_k7/`). Only the candidate-form AO has offset-7 rows
(the sweep scored only that form), so H7, which needs AO-yn and the logit lens there, is not restated, and no shuffled control
exists at this offset.

| restated at offset 7 | estimate [wider 95 % CI] | verdict |
|---|---|---|
| H1 quiver ΔAUC_AO | n=16 **+0.044 [+0.011, +0.065]**, n=32 +0.025 [−0.000, +0.045], n=64 +0.011, n=128 −0.012, n=512 −0.004 | **REFUTED at n = 16**: the oracle adds value with 16 labels (mean ≥ +0.01, CI > 0); none at n ≥ 128 |
| H1 median n* ≤ 8 | 27.0 [18.3, 50.9] | REFUTED: at its training position the oracle is worth about 27 labels on text-derivable facts |
| H2 exceedances on text tags | 3 (153, 42_temp_sense, 94_ai_gen), plus 127 on KNOWLEDGE; all four replicate on fresh items | **REFUTED**. The one exceedance over a competent model report is 42_temp_sense (oracle 0.845 vs prompt-only 0.770, Δ +0.075, one-sided lower bound +0.023). 153 and 94 beat a below-chance report again |
| H2 KNOWLEDGE ≥ 0.8 × probe | 0.71 [0.50, 0.86] | **SUPPORTED** |
| C-A (AO vs text arm) | state 0.823 vs text 0.894 | 6 READ FROM THE STATE, 47 TEXT SUFFICES, 55 not distinguished |

## Controls
Shuffled controls: 74.5 % of 864 cells in [0.45, 0.55] (rule: ≥ 95 %). Mean 0.500, SD 0.043, against the null's 0.041, which
puts 77.8 % in band at n = 200. Gemma had 78.1 %. The CI excludes 0.5 in 6.6 % of cells. Read as sampling noise; the rule is
reported as failed-as-written (§12). The logit-lens rotation readout is 0.505.

## What this says so far
At the site the R-A protocol prescribes (assistant onset), Karvonen's 8B oracle behaves like Gemma's and like Phase R's
community readers. It adds nothing to a probe quiver, the text alone beats it, and its state adds nothing to the text.
At the position it was trained on (a token or two after the text), it is a different instrument: worth about 27 labels,
useful at n = 16, and within 0.8 of the probe on most KNOWLEDGE facts, though the text alone still beats it on half the facts.
The read site, not only the checkpoint tier, decides the verdicts. That bears directly on HP1. Q8B and Q32 (running) will show
whether this holds for Bauer et al.'s oracle and at 32B.

## Surprise-list re-scores (BRIEF_R §4.9(c); `fresh_rescore.csv`)
Each BH-surviving exceedance on a text tag was re-scored on 200 balanced pool items outside the 64 pool-eval items. The test:
oracle − prompt-only ≥ +0.05 with a one-sided 95 % lower bound > 0. All six cells pass, under the two-sided reading too.
| fact (tag) | site | oracle | prompt-only | Δ [one-sided 95 % lower bound] |
|---|---|---|---|---|
| 153_it_tick_Administrative rights (TOPIC) | onset | 0.652 | 0.379 | +0.273 [+0.178] |
| 94_ai_gen (FORM) | onset | 0.602 | 0.408 | +0.194 [+0.119] |
| 153 | offset 7 | 0.513 | 0.379 | +0.134 [+0.059] |
| 94_ai_gen | offset 7 | 0.664 | 0.408 | +0.255 [+0.184] |
| 42_temp_sense (COMPUTED) | offset 7 | 0.845 | 0.770 | +0.075 [+0.023] |
| 127_art_type_song (KNOWLEDGE, not a text tag) | offset 7 | 0.805 | 0.607 | +0.197 [+0.146] |
153 is the fact WS3's audit flagged on Qwen3.6-27B; the model's own answer there is anti-correlated with the label on both
models.
