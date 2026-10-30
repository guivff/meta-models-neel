# Phase R — interim results (cycle 19)

Checkpoint tiers (BRIEF_RP §0): olens = community (agu18dec/olens_and_ar olens_s3d_rl600 (Qwen3.6-27B)); jlens = community (neuronpedia/jacobian-lens (Qwen3.6-27B)); nla = community (ceselder/qwen3.6-27b-nla-rl iter 400 (Qwen3.6-27B)); skip_a = community (agreelens skip lenses (Qwen3.6-27B)); prompt-only, probes and the logit lens = none. Every Oracle-lens number is the Qwen Oracle lens at that checkpoint. Each reader family is its own row; this file has no Gemma AO and no Qwen AO row, and never pools them with the Qwen Oracle lens.

generated 2026-10-19 23:53 UTC from the tables `analyze --only r2 r4 r6 r7 r8` wrote; partial shards — every number here moves as rows arrive. Inferential claims only at each reader's primary site, chat render (§4.9 b).

## Datasets covered

| table | file | pod | rows kept | datasets |
|---|---|---|---|---|
| reader_lo | reader_lo.1.B.jsonl | C | 24,328 | 29 |
| reader_lo | reader_lo.1.jsonl | A1 | 410,064 | 29 |
| reader_lo | reader_lo.2.B.jsonl | C | 24,192 | 28 |
| reader_lo | reader_lo.2.jsonl | A2 | 408,576 | 28 |
| reader_lo | reader_lo.3.B.jsonl | C | 23,712 | 28 |
| reader_lo | reader_lo.3.jsonl | A3 | 399,936 | 28 |
| reader_lo | reader_lo.4.B.jsonl | C | 23,792 | 28 |
| reader_lo | reader_lo.4.jsonl | A4 | 401,376 | 28 |
| reader_lo | reader_lo.B.jsonl | B | 441,744 | 29 |
| reader_lo | reader_lo.E.jsonl | E | 183,158 | 11 |
| reader_lo | reader_lo.NLA.jsonl | C | 70,734 | 95 |
| reader_lo | reader_lo.RB.jsonl | RB | 586,260 | 55 |
| logit_lens | logit_lens.1.jsonl | A1 | 39,324 | 29 |
| logit_lens | logit_lens.2.jsonl | A2 | 39,872 | 28 |
| logit_lens | logit_lens.3.jsonl | A3 | 37,704 | 28 |
| logit_lens | logit_lens.4.jsonl | A4 | 37,936 | 28 |
| logit_lens | logit_lens.B.jsonl | B | 29,004 | 29 |
| logit_lens | logit_lens.E.jsonl | E | 7,272 | 8 |
| logit_lens | logit_lens.RB.jsonl | RB | 33,240 | 55 |
| prompt_only | prompt_only.1.jsonl | A1 | 19,662 | 29 |
| prompt_only | prompt_only.2.jsonl | A2 | 19,936 | 28 |
| prompt_only | prompt_only.3.jsonl | A3 | 18,852 | 28 |
| prompt_only | prompt_only.4.jsonl | A4 | 18,968 | 28 |
| prompt_only | prompt_only.B.jsonl | B | 20,554 | 44 |
| prompt_only | prompt_only.E.jsonl | E | 5,588 | 11 |
| prompt_only | prompt_only.RB.jsonl | RB | 20,180 | 62 |
| state_free | state_free.1.B.jsonl | C | 58 | 29 |
| state_free | state_free.1.jsonl | A1 | 1,044 | 29 |
| state_free | state_free.2.B.jsonl | C | 56 | 28 |
| state_free | state_free.2.jsonl | A2 | 1,008 | 28 |
| state_free | state_free.3.B.jsonl | C | 56 | 28 |
| state_free | state_free.3.jsonl | A3 | 1,008 | 28 |
| state_free | state_free.4.B.jsonl | C | 56 | 28 |
| state_free | state_free.4.jsonl | A4 | 1,008 | 28 |
| state_free | state_free.B.jsonl | B | 43,152 | 29 |
| state_free | state_free.E.jsonl | E | 36,148 | 11 |
| state_free | state_free.NLA.jsonl | C | 7,184 | 95 |
| state_free | state_free.RB.jsonl | RB | 52,668 | 55 |
| kway_lo | kway_lo.B.jsonl | B | 318,600 | 15 |
| kway_lo | kway_lo.NLA.jsonl | C | 30,238 | 22 |
| kway_lo | kway_lo.RB.jsonl | RB | 225,684 | 7 |

Qwen states on disk: 113 datasets; with chat block 42: 113; with 42/48/56: 113 (R1 / R5-select run on these). Bank: 113 R-A facts.
Provenance: 232,824 pod-D / WS13 rows dropped (prompt_only.jsonl 7,200, prompt_only.D.jsonl 7,200, reader_lo.D.jsonl 129,408, logit_lens.jsonl 14,400, logit_lens.D.jsonl 14,400, state_free.jsonl 30,108, state_free.D.jsonl 30,108); every kept row asserted pod ∈ ['A1', 'A2', 'A3', 'A4', 'B', 'C', 'E', 'RB'], git_sha 4d482b6.

## §4.9 c replication — Oracle lens (community) on 153_it_tick_Administrative rights, 200 fresh pool items

| layer | render | n | olens (community) AUROC | prompt-only AUROC | Δ | one-sided 95% lower | rule |
|---|---|---|---|---|---|---|---|
| 42 | chat | 200 | 0.585 | 0.280 | +0.305 | +0.214 | pass (descriptive) |
| 42 | raw | 200 | 0.415 | 0.280 | +0.135 | +0.048 | pass (descriptive) |
| 44 | chat | 200 | 0.548 | 0.280 | +0.268 | +0.179 | pass (primary: decides) |
| 44 | raw | 200 | 0.406 | 0.280 | +0.126 | +0.040 | pass (descriptive) |
| 48 | chat | 200 | 0.516 | 0.280 | +0.236 | +0.150 | pass (descriptive) |
| 48 | raw | 200 | 0.407 | 0.280 | +0.127 | +0.040 | pass (descriptive) |
| 52 | chat | 200 | 0.554 | 0.280 | +0.274 | +0.186 | pass (descriptive) |
| 52 | raw | 200 | 0.410 | 0.280 | +0.130 | +0.047 | pass (descriptive) |
| 56 | chat | 200 | 0.521 | 0.280 | +0.241 | +0.152 | pass (descriptive) |
| 56 | raw | 200 | 0.418 | 0.280 | +0.138 | +0.057 | pass (descriptive) |
Verdict at the primary site (block 44, chat): **REPLICATED**.
Label defect (BRIEF_R Deviations, WS3 2026-10-19): 101_disease_class, 139_news_class_Politics, 140_news_class_Technology, 141_news_class_Entertainment, 145_disease_class_digestive system diseases, 146_disease_class_cardiovascular diseases, 97_news_class — excluded post hoc for a label defect, as with CoLA §3; each block below is given with them (A) and without them (B); they are never in a BH family. Label-defect prevalence: 5 of 113 R-A facts (4.4%), 1000 of 22198 test items (4.5%); no R-A label is corrected, the defective facts are excluded in block B.
Label audit (uniform trigger, BRIEF_R Deviations WS3 2026-10-19; `label_audit.md`): 10 facts flagged (prompt-only AUROC < 0.5 or greedy accuracy < chance): 101_disease_class, 131_temp_cat_Typical Time, 140_news_class_Technology, 142_cancer_cat_Thyroid_Cancer, 144_cancer_cat_Colon_Cancer, 145_disease_class_digestive system diseases, 146_disease_class_cardiovascular diseases, 153_it_tick_Administrative rights, rb_internal_puzzle_answer, x25_wsb_wrong_bridge. Block B excludes LABEL_DEFECT ∪ flagged; only inspected defects (LABEL_DEFECT) leave the BH families.

**H2 — REFUTED (block A, all facts, primary) ‖ it rests on ONE audit-flagged fact, 153_it_tick_Administrative rights, whose prompt-only ceiling is inverted (0.32 on test; 0.28 on the 200 replication items) ‖ block B (without LABEL_DEFECT ∪ flagged): UNDERPOWERED (0 BH exceedances of 276 cells).** Printed with equal prominence by Guiv's decision (2026-10-19).

# A — all facts

## Controls

**Shuffled gate (§4.2, 95% CI ∋ 0.5):** 4088 pass / 206 fail of 4294 cells (expected false fails at 5%: 215).

| reader | pass | fail | fail at primary site |
|---|---|---|---|
| jlens | 2576 | 136 | 9/113 |
| nla | 215 | 11 | 6/113 |
| olens (community) | 1080 | 50 | 6/113 |
| skip_a | 217 | 9 | 3/113 |

Failing primary-site shuffled cells (pipeline bug first, §4.9 c): nla 7_hist_fig_ispolitician 0.371 [0.297, 0.447]; jlens 56_wikidatasex_or_gender 0.392 [0.312, 0.469]; jlens 130_temp_cat_Frequency 0.397 [0.286, 0.499]; nla 151_it_tick_HR Support 0.399 [0.317, 0.479]; jlens 135_context_type_Event_duration 0.399 [0.325, 0.484]; jlens 63_wikidata_occupation_issinger 0.401 [0.319, 0.477]; olens (community) 163_agnews_2 0.402 [0.315, 0.480]; nla 65_high-school 0.407 [0.335, 0.491]; olens (community) 72_gene-expression 0.408 [0.332, 0.490]; skip_a 163_agnews_2 0.409 [0.326, 0.495]; olens (community) 152_it_tick_Hardware 0.410 [0.334, 0.491]; skip_a 91_glue_qqp 0.412 [0.330, 0.491]; jlens 163_agnews_2 0.412 [0.335, 0.495]; jlens 91_glue_qqp 0.416 [0.329, 0.496]; olens (community) 135_context_type_Event_duration 0.417 [0.334, 0.495]; nla 56_wikidatasex_or_gender 0.417 [0.334, 0.489]; nla 100_news_fake 0.418 [0.346, 0.489]; olens (community) 148_twt_emotion_worry 0.420 [0.347, 0.500]; jlens 24_headline_isiran 0.576 [0.501, 0.649]; nla 84_clinical-trials 0.580 [0.507, 0.657]; jlens 51_just_is 0.593 [0.520, 0.669]; jlens 83_third-party 0.603 [0.522, 0.675]; olens (community) 24_headline_isiran 0.611 [0.532, 0.690]; skip_a 24_headline_isiran 0.615 [0.536, 0.691]

**State-free prior (§2.2, descriptive):** per reader at the primary site, median |prior z| and the number of two-sided facts where ≥ 90% of natural items carry the prior's sign (the reader answers its prior).

| reader | facts | median |prior z| | prior-dominated (≥ 90%) |
|---|---|---|---|
| jlens | 113 | 0.09 | 8 |
| nla | 113 | 0.43 | 16 |
| olens (community) | 113 | 0.28 | 10 |
| skip_a | 113 | 0.50 | 12 |

**Random directions (§4.5, §4.9 i):** apply to edited states only (R5 steering, pod F); no steer rows yet — not run.

## R2 — reader vs prompt-only ceiling and probe, by tag (primary site, chat)

Median AUROC over facts; Δ = reader − prompt-only (paired bootstrap per fact); exceed = Δ ≥ +0.05 with CI > 0 (raw / after BH q = 0.10 per reader); probe(512) at block 42 where states exist.

| tag | reader | facts | reader | prompt-only | probe(512) | mean Δ | exceed raw | exceed BH | reader ≥ 0.8×probe |
|---|---|---|---|---|---|---|---|---|---|
| COMPUTED | jlens | 17 | 0.733 | 0.933 | 0.960 | -0.204 | 0 | 0 | 9/17 |
| COMPUTED | logit_lens | 17 | 0.518 | 0.933 | 0.960 | -0.332 | 0 | 0 | 4/17 |
| COMPUTED | nla | 17 | 0.696 | 0.933 | 0.960 | -0.273 | 0 | 0 | 8/17 |
| COMPUTED | olens (community) | 17 | 0.744 | 0.933 | 0.960 | -0.173 | 0 | 0 | 10/17 |
| COMPUTED | skip_a | 17 | 0.758 | 0.933 | 0.960 | -0.177 | 0 | 0 | 8/17 |
| FORM | jlens | 6 | 0.585 | 0.912 | 0.980 | -0.276 | 0 | 0 | 1/6 |
| FORM | logit_lens | 6 | 0.519 | 0.912 | 0.980 | -0.356 | 0 | 0 | 0/6 |
| FORM | nla | 6 | 0.662 | 0.912 | 0.980 | -0.194 | 0 | 0 | 2/6 |
| FORM | olens (community) | 6 | 0.602 | 0.912 | 0.980 | -0.275 | 0 | 0 | 1/6 |
| FORM | skip_a | 6 | 0.596 | 0.912 | 0.980 | -0.259 | 0 | 0 | 1/6 |
| KNOWLEDGE | jlens | 21 | 0.636 | 0.934 | 0.869 | -0.222 | 0 | 0 | 9/21 |
| KNOWLEDGE | logit_lens | 21 | 0.557 | 0.934 | 0.869 | -0.324 | 0 | 0 | 3/21 |
| KNOWLEDGE | nla | 21 | 0.641 | 0.934 | 0.869 | -0.222 | 0 | 0 | 9/21 |
| KNOWLEDGE | olens (community) | 21 | 0.680 | 0.934 | 0.869 | -0.198 | 0 | 0 | 9/21 |
| KNOWLEDGE | skip_a | 21 | 0.666 | 0.934 | 0.869 | -0.207 | 0 | 0 | 12/21 |
| META | jlens | 6 | 0.776 | 0.975 | 0.978 | -0.173 | 0 | 0 | 3/6 |
| META | logit_lens | 6 | 0.495 | 0.975 | 0.978 | -0.379 | 1 | 1 | 0/6 |
| META | nla | 6 | 0.658 | 0.975 | 0.978 | -0.210 | 0 | 0 | 2/6 |
| META | olens (community) | 6 | 0.636 | 0.975 | 0.978 | -0.257 | 0 | 0 | 1/6 |
| META | skip_a | 6 | 0.741 | 0.975 | 0.978 | -0.202 | 0 | 0 | 1/6 |
| PASSAGE-KNOWLEDGE | jlens | 9 | 0.651 | 0.802 | 0.837 | -0.169 | 0 | 0 | 4/9 |
| PASSAGE-KNOWLEDGE | logit_lens | 9 | 0.513 | 0.802 | 0.837 | -0.308 | 0 | 0 | 1/9 |
| PASSAGE-KNOWLEDGE | nla | 9 | 0.609 | 0.802 | 0.837 | -0.219 | 0 | 0 | 2/9 |
| PASSAGE-KNOWLEDGE | olens (community) | 9 | 0.593 | 0.802 | 0.837 | -0.213 | 0 | 0 | 3/9 |
| PASSAGE-KNOWLEDGE | skip_a | 9 | 0.664 | 0.802 | 0.837 | -0.188 | 0 | 0 | 6/9 |
| SURFACE | jlens | 28 | 0.637 | 1.000 | 0.945 | -0.360 | 0 | 0 | 6/28 |
| SURFACE | logit_lens | 28 | 0.522 | 1.000 | 0.945 | -0.435 | 0 | 0 | 4/28 |
| SURFACE | nla | 28 | 0.713 | 1.000 | 0.945 | -0.236 | 0 | 0 | 13/28 |
| SURFACE | olens (community) | 28 | 0.741 | 1.000 | 0.945 | -0.257 | 0 | 0 | 15/28 |
| SURFACE | skip_a | 28 | 0.759 | 1.000 | 0.945 | -0.251 | 0 | 0 | 15/28 |
| TOPIC | jlens | 26 | 0.620 | 0.850 | 0.958 | -0.123 | 2 | 0 | 12/26 |
| TOPIC | logit_lens | 26 | 0.570 | 0.850 | 0.958 | -0.166 | 3 | 2 | 7/26 |
| TOPIC | nla | 26 | 0.548 | 0.850 | 0.958 | -0.207 | 1 | 0 | 9/26 |
| TOPIC | olens (community) | 26 | 0.554 | 0.850 | 0.958 | -0.186 | 3 | 1 | 7/26 |
| TOPIC | skip_a | 26 | 0.574 | 0.850 | 0.958 | -0.144 | 2 | 1 | 11/26 |

## Oracle lens (community) vs model asked directly (prompt-only), chat onset vs raw last token

Δ = AUROC(prompt-only: Qwen asked the question directly) − AUROC(Oracle lens (community) on the state); per-fact sign from the item-paired bootstrap; tag means with a fact-bootstrap 95% CI. This is NOT the Gemma Check-2 (which gives the Oracle (community) the text): that is the last column, from the text-arm rows. The render is the Oracle's (community) read site; prompt-only has its own prompt.

**olens (community) @ block 42**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.184 [0.126, 0.249] | 14 / 0 | +0.304 [0.266, 0.341] | 17 / 0 | — | — |
| FORM (6) | +0.272 [0.156, 0.366] | 5 / 0 | +0.325 [0.211, 0.419] | 5 / 0 | — | — |
| KNOWLEDGE (21) | +0.203 [0.154, 0.257] | 20 / 0 | +0.193 [0.146, 0.244] | 21 / 0 | — | — |
| META (6) | +0.242 [0.102, 0.371] | 5 / 0 | +0.220 [0.000, 0.430] | 5 / 1 | — | — |
| PASSAGE-KNOWLEDGE (9) | +0.225 [0.173, 0.287] | 8 / 0 | +0.100 [-0.014, 0.220] | 5 / 2 | — | — |
| SURFACE (28) | +0.256 [0.197, 0.322] | 25 / 0 | +0.124 [0.076, 0.176] | 25 / 0 | — | — |
| TOPIC (26) | +0.189 [0.092, 0.286] | 17 / 3 | +0.187 [0.111, 0.261] | 19 / 2 | — | — |
| all (113) | +0.218 [0.186, 0.250] | 94 / 3 | +0.192 [0.162, 0.222] | 97 / 5 | — | — |

**olens (community) @ block 44**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.173 [0.116, 0.235] | 16 / 0 | +0.304 [0.257, 0.345] | 17 / 0 | -0.211 [-0.272, -0.145] (14 act / 0 text, n=17) | -0.080 [-0.129, -0.029] (8 act / 0 text, n=17) |
| FORM (6) | +0.275 [0.146, 0.393] | 5 / 0 | +0.334 [0.224, 0.430] | 5 / 0 | -0.070 [-0.176, 0.047] (3 act / 1 text, n=6) | -0.011 [-0.040, 0.020] (0 act / 0 text, n=6) |
| KNOWLEDGE (21) | +0.198 [0.150, 0.251] | 19 / 0 | +0.186 [0.138, 0.238] | 21 / 0 | -0.043 [-0.092, 0.003] (7 act / 2 text, n=21) | -0.055 [-0.081, -0.027] (10 act / 0 text, n=21) |
| META (6) | +0.257 [0.127, 0.386] | 5 / 0 | +0.234 [0.010, 0.445] | 5 / 1 | +0.058 [-0.032, 0.124] (0 act / 2 text, n=6) | +0.035 [-0.113, 0.174] (1 act / 2 text, n=6) |
| PASSAGE-KNOWLEDGE (9) | +0.213 [0.155, 0.275] | 8 / 0 | +0.097 [-0.024, 0.231] | 5 / 2 | +0.115 [0.044, 0.182] (0 act / 6 text, n=9) | -0.000 [-0.040, 0.044] (2 act / 1 text, n=9) |
| SURFACE (28) | +0.257 [0.199, 0.322] | 25 / 0 | +0.123 [0.076, 0.176] | 25 / 0 | +0.145 [0.086, 0.196] (3 act / 22 text, n=28) | +0.011 [-0.003, 0.027] (1 act / 7 text, n=28) |
| TOPIC (26) | +0.186 [0.092, 0.283] | 17 / 3 | +0.200 [0.122, 0.274] | 20 / 2 | -0.001 [-0.052, 0.054] (7 act / 8 text, n=26) | +0.013 [-0.024, 0.047] (3 act / 6 text, n=26) |
| all (113) | +0.214 [0.183, 0.248] | 95 / 3 | +0.195 [0.164, 0.226] | 98 / 5 | +0.005 [-0.027, 0.037] (34 act / 41 text, n=113) | -0.015 [-0.033, 0.002] (25 act / 16 text, n=113) |

**olens (community) @ block 48**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.157 [0.098, 0.222] | 14 / 0 | +0.305 [0.263, 0.345] | 17 / 0 | — | — |
| FORM (6) | +0.287 [0.195, 0.367] | 5 / 0 | +0.336 [0.209, 0.436] | 5 / 0 | — | — |
| KNOWLEDGE (21) | +0.198 [0.153, 0.245] | 20 / 0 | +0.187 [0.138, 0.240] | 21 / 0 | — | — |
| META (6) | +0.271 [0.127, 0.423] | 5 / 0 | +0.230 [0.027, 0.420] | 5 / 1 | — | — |
| PASSAGE-KNOWLEDGE (9) | +0.201 [0.124, 0.274] | 7 / 0 | +0.110 [-0.013, 0.240] | 5 / 2 | — | — |
| SURFACE (28) | +0.268 [0.208, 0.334] | 25 / 0 | +0.123 [0.078, 0.174] | 25 / 0 | — | — |
| TOPIC (26) | +0.176 [0.086, 0.274] | 18 / 3 | +0.192 [0.115, 0.266] | 20 / 2 | — | — |
| all (113) | +0.213 [0.182, 0.247] | 94 / 3 | +0.194 [0.164, 0.225] | 98 / 5 | — | — |

**olens (community) @ block 52**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.173 [0.113, 0.240] | 15 / 0 | +0.317 [0.278, 0.357] | 17 / 0 | — | — |
| FORM (6) | +0.304 [0.195, 0.382] | 5 / 0 | +0.282 [0.149, 0.382] | 5 / 0 | — | — |
| KNOWLEDGE (21) | +0.193 [0.157, 0.229] | 21 / 0 | +0.190 [0.146, 0.241] | 21 / 0 | — | — |
| META (6) | +0.216 [0.084, 0.348] | 5 / 0 | +0.207 [0.079, 0.324] | 5 / 0 | — | — |
| PASSAGE-KNOWLEDGE (9) | +0.214 [0.134, 0.292] | 8 / 0 | +0.138 [0.050, 0.247] | 6 / 0 | — | — |
| SURFACE (28) | +0.259 [0.201, 0.322] | 25 / 0 | +0.140 [0.090, 0.199] | 26 / 0 | — | — |
| TOPIC (26) | +0.161 [0.072, 0.255] | 17 / 3 | +0.179 [0.099, 0.262] | 20 / 1 | — | — |
| all (113) | +0.208 [0.178, 0.240] | 96 / 3 | +0.196 [0.168, 0.225] | 100 / 1 | — | — |

**olens (community) @ block 56**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.194 [0.129, 0.265] | 15 / 0 | +0.322 [0.276, 0.367] | 17 / 0 | — | — |
| FORM (6) | +0.314 [0.198, 0.399] | 5 / 0 | +0.308 [0.179, 0.407] | 5 / 0 | — | — |
| KNOWLEDGE (21) | +0.192 [0.156, 0.229] | 21 / 0 | +0.211 [0.168, 0.256] | 21 / 0 | — | — |
| META (6) | +0.204 [0.063, 0.336] | 5 / 0 | +0.207 [0.081, 0.317] | 5 / 0 | — | — |
| PASSAGE-KNOWLEDGE (9) | +0.203 [0.122, 0.284] | 7 / 0 | +0.138 [0.044, 0.252] | 6 / 0 | — | — |
| SURFACE (28) | +0.253 [0.193, 0.320] | 25 / 0 | +0.142 [0.092, 0.198] | 25 / 0 | — | — |
| TOPIC (26) | +0.159 [0.078, 0.246] | 18 / 2 | +0.172 [0.094, 0.253] | 18 / 1 | — | — |
| all (113) | +0.208 [0.179, 0.241] | 96 / 2 | +0.201 [0.172, 0.229] | 97 / 1 | — | — |


## R4 — layer × render (natural test cells; median AUROC over facts)

**chat**

| reader | 24 | 28 | 32 | 36 | 38 | 40 | 42 | 44 | 48 | 52 | 56 | 60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| jlens | 0.57 | 0.58 | 0.64 | 0.63 | 0.63 | 0.65 | 0.65 | 0.65 | 0.64 | 0.67 | 0.70 | 0.67 |
| logit_lens | 0.53 | 0.54 | 0.56 | 0.54 | 0.55 | 0.53 | 0.53 | 0.54 | 0.54 | 0.54 | 0.58 | 0.61 |
| nla | — | — | — | — | — | — | 0.67 | — | — | — | — | — |
| olens (community) | — | — | — | — | — | — | 0.68 | 0.68 | 0.69 | 0.68 | 0.68 | — |
| skip_a | — | — | — | — | — | — | 0.70 | — | — | — | — | — |

**raw**

| reader | 24 | 28 | 32 | 36 | 38 | 40 | 42 | 44 | 48 | 52 | 56 | 60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| jlens | 0.60 | 0.63 | 0.64 | 0.66 | 0.67 | 0.67 | 0.67 | 0.68 | 0.67 | 0.66 | 0.66 | 0.65 |
| logit_lens | 0.56 | 0.55 | 0.55 | 0.58 | 0.57 | 0.57 | 0.57 | 0.57 | 0.58 | 0.58 | 0.58 | 0.59 |
| nla | — | — | — | — | — | — | 0.73 | — | — | — | — | — |
| olens (community) | — | — | — | — | — | — | 0.64 | 0.65 | 0.65 | 0.66 | 0.67 | — |
| skip_a | — | — | — | — | — | — | 0.75 | — | — | — | — | — |

Render shift at the primary site (chat − raw, §4.4; RENDER-ROBUST iff |Δ| ≤ 0.05 on ≥ 80% of facts):

| reader | layer | facts | median Δ | |Δ| ≤ 0.05 | robust |
|---|---|---|---|---|---|
| jlens | 42 | 113 | -0.014 | 35% | no |
| logit_lens | 42 | 113 | -0.007 | 25% | no |
| nla | 42 | 113 | -0.047 | 36% | no |
| olens (community) | 44 | 113 | -0.003 | 22% | no |
| skip_a | 42 | 113 | -0.021 | 30% | no |

Lag L_read − L_present by tag (chat; needs probe curves): jlens/COMPUTED +8 (n=11); jlens/FORM +12 (n=3); jlens/KNOWLEDGE +8 (n=11); jlens/META +0 (n=4); jlens/PASSAGE-KNOWLEDGE +32 (n=4); jlens/SURFACE +0 (n=11); jlens/TOPIC +8 (n=11); logit_lens/COMPUTED +19 (n=8); logit_lens/FORM +16 (n=1); logit_lens/KNOWLEDGE +32 (n=11); logit_lens/META +0 (n=1); logit_lens/PASSAGE-KNOWLEDGE +nan (n=0); logit_lens/SURFACE +4 (n=11); logit_lens/TOPIC +16 (n=7); nla/COMPUTED +18 (n=7); nla/FORM +18 (n=2); nla/KNOWLEDGE +18 (n=6); nla/META +18 (n=2); nla/PASSAGE-KNOWLEDGE +nan (n=0); nla/SURFACE +18 (n=12); nla/TOPIC +18 (n=4); olens (community)/COMPUTED +18 (n=9); olens (community)/FORM +nan (n=0); olens (community)/KNOWLEDGE +18 (n=10); olens (community)/META +24 (n=2); olens (community)/PASSAGE-KNOWLEDGE +24 (n=1); olens (community)/SURFACE +18 (n=18); olens (community)/TOPIC +18 (n=7); skip_a/COMPUTED +18 (n=9); skip_a/FORM +18 (n=1); skip_a/KNOWLEDGE +18 (n=8); skip_a/META +18 (n=3); skip_a/PASSAGE-KNOWLEDGE +18 (n=1); skip_a/SURFACE +18 (n=14); skip_a/TOPIC +18 (n=7)

## R3 (descriptive) — conflict items: does the reader side with the model's answer or the text label?

Key: the model's single forced-choice pick (prompt-only greedy), **not** the pre-registered paraphrase-majority key (§4.9 f), which has no rows; so H3 is NOT RUN. Facts with ≥ 12 conflict items; chat render.

| reader | layer | facts | READS_MODEL | READS_TEXT | MIXED | pooled P(model) |
|---|---|---|---|---|---|---|
| jlens | 24 | 74 | 3 | 2 | 69 | 0.52 |
| jlens | 28 | 74 | 4 | 0 | 70 | 0.52 |
| jlens | 32 | 74 | 3 | 1 | 70 | 0.52 |
| jlens | 36 | 74 | 7 | 5 | 62 | 0.52 |
| jlens | 38 | 74 | 6 | 5 | 63 | 0.52 |
| jlens | 40 | 74 | 7 | 3 | 64 | 0.52 |
| jlens | 42 | 74 | 5 | 4 | 65 | 0.52 |
| jlens | 44 | 74 | 7 | 5 | 62 | 0.52 |
| jlens | 48 | 74 | 3 | 2 | 69 | 0.52 |
| jlens | 52 | 74 | 4 | 2 | 68 | 0.52 |
| jlens | 56 | 74 | 1 | 2 | 71 | 0.52 |
| jlens | 60 | 74 | 1 | 4 | 69 | 0.52 |
| nla | 42 | 74 | 1 | 1 | 72 | 0.49 |
| olens (community) | 42 | 74 | 6 | 4 | 64 | 0.52 |
| olens (community) | 44 | 74 | 6 | 4 | 64 | 0.52 |
| olens (community) | 48 | 74 | 5 | 4 | 65 | 0.52 |
| olens (community) | 52 | 74 | 4 | 2 | 68 | 0.52 |
| olens (community) | 56 | 74 | 4 | 2 | 68 | 0.52 |
| skip_a | 42 | 74 | 6 | 2 | 66 | 0.53 |

## H3 (secondary: §14 paraphrase key)

**Secondary result, labelled as such.** The paraphrases were written after single-phrasing prompt-only data existed (and after WS3's descriptive single-key R3), blind to every result: three fixed templates applied programmatically (§14). Key = majority of model_says_pos over frozen, p1, p2 on 22198 test items; unstable = the three disagree.

Unstable items: 8.0% overall; by tag: COMPUTED 12.3%; FORM 7.5%; KNOWLEDGE 14.0%; META 8.7%; PASSAGE-KNOWLEDGE 5.0%; SURFACE 2.7%; TOPIC 7.3%
Datasets above the §4.9 f 15% instability flag: 16 — 137_glue_mnli_neutral 68%, 131_temp_cat_Typical Time 47%, 128_art_type_movie 40%, 153_it_tick_Administrative rights 38%, 126_art_type_book 33%, 114_nyc_borough_Manhattan 27%, 7_hist_fig_ispolitician 24%, 129_arith_mc_A 22%
ICC(2,1) over the LO of frozen/p1/p2, median over facts: 0.96; key ≠ single-phrasing pick on 2.7% of items.

**all items** — pooled over conflict items (key ≠ label), chat render:

| reader | layer | facts | conflict items | P(sides with TEXT) [Wilson] | P(sides with MODEL) |
|---|---|---|---|---|---|
| jlens | 24 | 108 | 3891 | 0.49 [0.48, 0.51] | 0.51 |
| jlens | 28 | 108 | 3891 | 0.48 [0.47, 0.50] | 0.52 |
| jlens | 32 | 108 | 3891 | 0.48 [0.47, 0.50] | 0.52 |
| jlens | 36 | 108 | 3891 | 0.49 [0.48, 0.51] | 0.51 |
| jlens | 38 | 108 | 3891 | 0.49 [0.47, 0.51] | 0.51 |
| jlens | 40 | 108 | 3891 | 0.49 [0.48, 0.51] | 0.51 |
| jlens | 42 | 108 | 3891 | 0.49 [0.48, 0.51] | 0.51 |
| jlens | 44 | 108 | 3891 | 0.49 [0.48, 0.51] | 0.51 |
| jlens | 48 | 108 | 3891 | 0.49 [0.47, 0.50] | 0.51 |
| jlens | 52 | 108 | 3891 | 0.48 [0.47, 0.50] | 0.52 |
| jlens | 56 | 108 | 3891 | 0.48 [0.46, 0.50] | 0.52 |
| jlens | 60 | 108 | 3891 | 0.49 [0.47, 0.50] | 0.51 |
| nla | 42 | 108 | 3891 | 0.51 [0.49, 0.52] | 0.49 |
| olens (community) | 42 | 108 | 3891 | 0.49 [0.47, 0.51] | 0.51 |
| olens (community) | 44 | 108 | 3891 | 0.49 [0.47, 0.50] | 0.51 |
| olens (community) | 48 | 108 | 3891 | 0.48 [0.47, 0.50] | 0.52 |
| olens (community) | 52 | 108 | 3891 | 0.48 [0.47, 0.50] | 0.52 |
| olens (community) | 56 | 108 | 3891 | 0.48 [0.46, 0.50] | 0.52 |
| skip_a | 42 | 108 | 3891 | 0.47 [0.46, 0.49] | 0.53 |

**stable items only** — pooled over conflict items (key ≠ label), chat render:

| reader | layer | facts | conflict items | P(sides with TEXT) [Wilson] | P(sides with MODEL) |
|---|---|---|---|---|---|
| jlens | 24 | 102 | 3030 | 0.49 [0.47, 0.50] | 0.51 |
| jlens | 28 | 102 | 3030 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 32 | 102 | 3030 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 36 | 102 | 3030 | 0.48 [0.46, 0.50] | 0.52 |
| jlens | 38 | 102 | 3030 | 0.48 [0.46, 0.49] | 0.52 |
| jlens | 40 | 102 | 3030 | 0.48 [0.46, 0.49] | 0.52 |
| jlens | 42 | 102 | 3030 | 0.48 [0.46, 0.49] | 0.52 |
| jlens | 44 | 102 | 3030 | 0.48 [0.46, 0.50] | 0.52 |
| jlens | 48 | 102 | 3030 | 0.48 [0.46, 0.50] | 0.52 |
| jlens | 52 | 102 | 3030 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 56 | 102 | 3030 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 60 | 102 | 3030 | 0.47 [0.45, 0.49] | 0.53 |
| nla | 42 | 102 | 3030 | 0.50 [0.49, 0.52] | 0.50 |
| olens (community) | 42 | 102 | 3030 | 0.48 [0.46, 0.50] | 0.52 |
| olens (community) | 44 | 102 | 3030 | 0.48 [0.46, 0.50] | 0.52 |
| olens (community) | 48 | 102 | 3030 | 0.48 [0.46, 0.50] | 0.52 |
| olens (community) | 52 | 102 | 3030 | 0.47 [0.45, 0.48] | 0.53 |
| olens (community) | 56 | 102 | 3030 | 0.47 [0.45, 0.48] | 0.53 |
| skip_a | 42 | 102 | 3030 | 0.46 [0.44, 0.48] | 0.54 |


## R5 — reading directions and steering (descriptive; the H5 verdict is in the hypothesis table)

**Read together:** at the read site the readers' gradient directions are near-orthogonal to BOTH the class-mean direction and the probe weights (H5 row). Measured as a gradient, the readers do not read a class-mean-like direction. The J-lens transport check (block-42 gradient carried to 38 vs the native block-38 gradient) is in the H5 row, so the result is not an artefact of the 42 → 38 move.

**Design property, not a reader property:** the R5 facts were selected for probe ≥ 0.9 and prompt-only ≥ 0.9 (natural |LO| ≈ 12), while the dose ceiling 2·‖d_cm‖ moves the answer ≈ 0.4–0.7 nats. The 75% crossing / flip rates the REPORT-FLIPPABLE / READER-BLIND rules need are never reached, so those verdicts are undefined. This is NOT evidence that the readers cannot be flipped or that the model ignores the probe direction: the doses never put either claim at risk. A dose extension or a moderate-confidence fact set would need its own pre-registration — NOT YET WRITTEN; flagged for Guiv. The only other pre-registered R5-related experiment is WS4's SWAP add-on, a different experiment, reported as NOT RUN.

Dose-response, median over facts (slopes, no verdict): reader follow = shift of the reader's score toward the pushed class as a fraction of its natural separation; model shift in nats toward the pushed class; flip = share of items whose greedy answer flips. 'near-0 sep.' = facts whose natural AUROC CI at the reader's primary site includes 0.5 (their follow ratios explode; counted, not excluded).

| direction | α | model shift (nats) | model flip rate | jlens follow | nla follow | olens (community) follow | probe follow | skip_a follow |
|---|---|---|---|---|---|---|---|---|
| d_probe | 0.5 | +0.083 | 0.000 | 0.015 | 0.008 | 0.008 | 0.014 | 0.009 |
| d_probe | 1 | +0.164 | 0.000 | 0.027 | 0.016 | 0.016 | 0.026 | 0.018 |
| d_probe | 2 | +0.373 | 0.000 | 0.050 | 0.019 | 0.026 | 0.043 | 0.034 |
| d_cm | 0.5 | +0.086 | 0.000 | 0.015 | 0.011 | 0.009 | 0.010 | 0.013 |
| d_cm | 1 | +0.230 | 0.000 | 0.029 | 0.023 | 0.018 | 0.020 | 0.026 |
| d_cm | 2 | +0.562 | 0.000 | 0.056 | 0.040 | 0.027 | 0.036 | 0.045 |
| random (10 pooled) | 0.5 | +0.004 | 0.000 | 0.000 | 0.001 | -0.000 | 0.000 | 0.001 |
| random (10 pooled) | 1 | +0.020 | 0.000 | 0.000 | 0.002 | 0.001 | 0.001 | 0.002 |
| random (10 pooled) | 2 | +0.063 | 0.000 | 0.002 | 0.003 | 0.002 | 0.004 | 0.002 |
| own (d_jlens) | α=0.5: model +0.16, jlens +0.053, α=1: model +0.33, jlens +0.104, α=2: model +0.73, jlens +0.196 | |  |  |  |  |  |
| own (d_olens) | α=0.5: model +0.16, olens (community) +0.034, α=1: model +0.33, olens (community) +0.065, α=2: model +0.71, olens (community) +0.076 | |  |  |  |  |  |
| own (d_probe) | α=0.5: model +0.08, probe +0.014, α=1: model +0.16, probe +0.026, α=2: model +0.37, probe +0.043 | |  |  |  |  |  |
| own (d_skip_a) | α=0.5: model +0.14, skip_a +0.035, α=1: model +0.31, skip_a +0.065, α=2: model +0.68, skip_a +0.117 | |  |  |  |  |  |

Facts with near-zero natural separation (of the 30): jlens 4, logit_lens 7, nla 3, olens (community) 3, skip_a 0

## R-C2 planted-context conflicts (WS5's analysis, `rc2.md`; shown, not recomputed)

P(context) on complier items (the model follows the planted context); verdicts are WS5's (§3.1 rule, nosys and shuffled gates).

| reader | layer | P(context), compliers [Wilson] | nosys P(belief) | shuffled P(context) | verdict (WS5) |
|---|---|---|---|---|---|
| jlens | 24 | 0.47 [0.41, 0.53] | 0.52 | 0.50 | NOT READING (nosys gate) |
| jlens | 28 | 0.47 [0.41, 0.53] | 0.52 | 0.50 | NOT READING (nosys gate) |
| jlens | 32 | 0.50 [0.44, 0.56] | 0.54 | 0.47 | NOT READING (nosys gate) |
| jlens | 36 | 0.56 [0.50, 0.61] | 0.60 | 0.49 | NOT READING (nosys gate) |
| jlens | 38 | 0.55 [0.49, 0.61] | 0.58 | 0.49 | NOT READING (nosys gate) |
| jlens | 40 | 0.59 [0.53, 0.64] | 0.63 | 0.47 | NOT READING (nosys gate) |
| jlens | 42 | 0.59 [0.53, 0.65] | 0.63 | 0.48 | NOT READING (nosys gate) |
| jlens | 44 | 0.55 [0.49, 0.61] | 0.64 | 0.47 | NOT READING (nosys gate) |
| jlens | 48 | 0.49 [0.43, 0.55] | 0.69 | 0.48 | NOT READING (nosys gate) |
| jlens | 52 | 0.74 [0.69, 0.79] | 0.78 | 0.47 | MIXED |
| jlens | 56 | 0.78 [0.73, 0.83] | 0.94 | 0.48 | READS THE CONTEXT (not the model) |
| jlens | 60 | 0.95 [0.92, 0.97] | 1.00 | 0.49 | READS THE CONTEXT (not the model) |
| nla | 42 | 0.19 [0.15, 0.24] | 0.95 | 0.12 | SHUFFLED CONTROL OFF 0.5 (pipeline check) |
| olens (community) | 42 | 0.64 [0.58, 0.69] | 0.85 | 0.45 | MIXED |
| olens (community) | 44 | 0.59 [0.53, 0.65] | 0.84 | 0.46 | MIXED |
| olens (community) | 48 | 0.49 [0.43, 0.55] | 0.99 | 0.50 | MIXED |
| olens (community) | 52 | 0.88 [0.84, 0.91] | 1.00 | 0.48 | READS THE CONTEXT + READS THE MODEL |
| olens (community) | 56 | 0.93 [0.90, 0.96] | 0.99 | 0.46 | READS THE CONTEXT + READS THE MODEL |
| skip_a | 42 | 0.60 [0.54, 0.65] | 0.85 | 0.44 | SHUFFLED CONTROL OFF 0.5 (pipeline check) |

**WS5's R-C2-F1 (`rc2_f1.md`, pre-registered; r/ws5-planted 812ca8f):** at blocks 42–44 the lens readers side with the planted answer MORE on the 22 non-complier items. For the J-lens that excess is a token prior on the candidate names, not a reading of the conflict (on the twin versions it leans 24–28 points less context; with no preamble it already prefers those names 64% vs 35%). So P(context) on non-compliers is contaminated for the J-lens; quote the pair-level win (rc2.csv) or the twin-corrected numbers. For the Oracle (community) and skip-lens it is undetermined by WS5's rules. Caveat: 22 non-compliers from 9 base items.

## R1b — the SAE paper's regimes on existing rows (label noise BD-6, class imbalance, covariate shift)

ΔAUC(n) = quiver chosen arrow − probe-only, mean over 5 seeds per fact, then over facts (wider of i.i.d. / clustered CI). Rule subset: 45 facts with a lens reader ≥ 0.8 at its primary site; all-facts means in parentheses.

| regime | param | n | facts | ΔAUC [95% CI] (rule subset) | ΔAUC (all facts) | probe AUROC |
|---|---|---|---|---|---|---|
| imbalance | 0.05 | 16 | 45 | 0.000 [0.000, 0.000] | +0.000 | 0.664 |
| imbalance | 0.05 | 32 | 45 | -0.008 [-0.032, 0.019] | -0.028 | 0.708 |
| imbalance | 0.05 | 128 | 43 | -0.006 [-0.016, 0.003] | -0.020 | 0.775 |
| imbalance | 0.1 | 16 | 45 | -0.011 [-0.034, 0.021] | -0.028 | 0.688 |
| imbalance | 0.1 | 32 | 45 | -0.020 [-0.039, 0.001] | -0.034 | 0.727 |
| imbalance | 0.1 | 128 | 43 | -0.024 [-0.035, -0.013] | -0.037 | 0.813 |
| imbalance | 0.25 | 16 | 45 | -0.005 [-0.024, 0.020] | -0.025 | 0.729 |
| imbalance | 0.25 | 32 | 45 | -0.014 [-0.026, -0.003] | -0.031 | 0.772 |
| imbalance | 0.25 | 128 | 43 | -0.015 [-0.028, -0.006] | -0.039 | 0.842 |
| imbalance | 0.5 | 16 | 45 | -0.012 [-0.030, 0.009] | -0.028 | 0.739 |
| imbalance | 0.5 | 32 | 45 | -0.029 [-0.050, -0.006] | -0.040 | 0.786 |
| imbalance | 0.5 | 128 | 43 | -0.018 [-0.029, -0.008] | -0.034 | 0.854 |
| imbalance | 0.5 | 512 | 42 | -0.001 [-0.002, 0.000] | -0.005 | 0.897 |
| noise | 0.1 | 2 | 45 | 0.000 [0.000, 0.000] | +0.000 | 0.555 |
| noise | 0.1 | 4 | 45 | 0.032 [0.006, 0.066] | +0.003 | 0.621 |
| noise | 0.1 | 8 | 45 | -0.015 [-0.039, 0.009] | -0.026 | 0.669 |
| noise | 0.1 | 16 | 45 | -0.002 [-0.028, 0.026] | -0.024 | 0.705 |
| noise | 0.1 | 32 | 45 | -0.020 [-0.041, 0.001] | -0.041 | 0.754 |
| noise | 0.1 | 64 | 45 | -0.036 [-0.055, -0.017] | -0.059 | 0.794 |
| noise | 0.1 | 128 | 45 | -0.034 [-0.051, -0.018] | -0.047 | 0.820 |
| noise | 0.1 | 256 | 45 | -0.008 [-0.015, -0.001] | -0.023 | 0.847 |
| noise | 0.1 | 512 | 45 | -0.002 [-0.006, 0.002] | -0.008 | 0.868 |
| noise | 0.25 | 2 | 45 | 0.000 [0.000, 0.000] | +0.000 | 0.533 |
| noise | 0.25 | 4 | 45 | 0.026 [0.001, 0.056] | +0.006 | 0.590 |
| noise | 0.25 | 8 | 45 | -0.006 [-0.046, 0.027] | -0.012 | 0.613 |
| noise | 0.25 | 16 | 45 | 0.020 [-0.009, 0.048] | -0.009 | 0.638 |
| noise | 0.25 | 32 | 45 | 0.027 [-0.006, 0.060] | -0.011 | 0.672 |
| noise | 0.25 | 64 | 45 | 0.007 [-0.024, 0.032] | -0.026 | 0.705 |
| noise | 0.25 | 128 | 45 | -0.024 [-0.053, 0.006] | -0.044 | 0.730 |
| noise | 0.25 | 256 | 45 | 0.009 [-0.014, 0.029] | -0.027 | 0.758 |
| noise | 0.25 | 512 | 45 | 0.023 [0.008, 0.038] | -0.007 | 0.779 |
| noise | 0.4 | 2 | 45 | 0.000 [0.000, 0.000] | +0.000 | 0.519 |
| noise | 0.4 | 4 | 45 | 0.058 [0.032, 0.084] | +0.025 | 0.530 |
| noise | 0.4 | 8 | 45 | 0.027 [-0.023, 0.076] | +0.012 | 0.548 |
| noise | 0.4 | 16 | 45 | 0.045 [-0.005, 0.089] | +0.019 | 0.565 |
| noise | 0.4 | 32 | 45 | 0.113 [0.083, 0.148] | +0.053 | 0.574 |
| noise | 0.4 | 64 | 45 | 0.041 [-0.001, 0.079] | +0.003 | 0.596 |
| noise | 0.4 | 128 | 45 | 0.055 [0.016, 0.092] | +0.011 | 0.602 |
| noise | 0.4 | 256 | 45 | 0.069 [0.026, 0.107] | +0.007 | 0.614 |
| noise | 0.4 | 512 | 45 | 0.116 [0.079, 0.152] | +0.037 | 0.621 |
| shift | chat→raw | 16 | 45 | -0.018 [-0.043, 0.004] | -0.010 | 0.709 |
| shift | chat→raw | 32 | 45 | -0.011 [-0.040, 0.016] | -0.019 | 0.738 |
| shift | chat→raw | 128 | 45 | -0.006 [-0.020, 0.008] | -0.014 | 0.788 |
| shift | chat→raw | 512 | 45 | -0.001 [-0.012, 0.005] | -0.001 | 0.806 |
| shift_ref | chat→chat | 16 | 45 | -0.012 [-0.029, 0.009] | -0.026 | 0.743 |
| shift_ref | chat→chat | 32 | 45 | -0.035 [-0.049, -0.020] | -0.046 | 0.789 |
| shift_ref | chat→chat | 128 | 45 | -0.017 [-0.026, -0.010] | -0.030 | 0.860 |
| shift_ref | chat→chat | 512 | 45 | -0.001 [-0.002, -0.000] | -0.006 | 0.901 |

Covariate shift, probe(512) trained on chat: AUROC(chat→raw) − AUROC(chat→chat) = -0.095 (median -0.076, 113 facts); readers' own raw − chat at their primary sites are in the R4 render-shift table.

## Hypotheses so far (BRIEF_R §4.9 d four-way; headline means quote the wider of the i.i.d. and clustered CIs, §4.9 j)

| H | status | n facts | basis |
|---|---|---|---|
| H1 | UNDERPOWERED | 60 | jlens median n* 3.1 [2.4, 5.1] n=60 → SUPPORTED; nla median n* 5.8 [3.9, 13.1] n=60 → UNDERPOWERED; olens (community) median n* 4.3 [2.9, 11.5] n=60 → UNDERPOWERED; skip_a median n* 5.6 [3.1, 17.1] n=60 → UNDERPOWERED; quiver ΔAUC(n≥16): n=16 -0.027 [-0.040, -0.012]ᶜ, n=32 -0.047 [-0.061, -0.033]ᶜ, n=64 -0.065 [-0.078, -0.051]ᶜ, n=128 -0.029 [-0.040, -0.020]ᶜ, n=256 -0.017 [-0.025, -0.007]ᶜ, n=512 -0.007 [-0.011, -0.003]ᶜ → SUPPORTED (ᶜ = clustered CI wider, quoted) |
| H2 | REFUTED | 77 | 2 BH-surviving exceedance(s): olens (community) 153_it_tick_Administrative rights [TOPIC] Δ +0.227 [+0.124, +0.314]; skip_a 153_it_tick_Administrative rights [TOPIC] Δ +0.245 [+0.147, +0.340]; olens (community) on 153_it_tick_Administrative rights REPLICATED on 200 fresh pool items (§4.9 c) → claimed (olens (community) 0.548 vs prompt-only 0.280, Δ +0.268, one-sided lower +0.179; CAVEAT: the ceiling is below chance (prompt-only 0.280 < 0.5) — the exceedance is the model's own report inverted, the Oracle (community) near chance); still pending §4.9 c replication: skip_a 153_it_tick_Administrative rights; Guiv's decision 2026-10-19: block A (all facts) primary, a flagged-but-not-defective fact counts, block B is a sensitivity line |
| H2 (read with) | H2 — REFUTED (block A, all facts, primary) ‖ it rests on ONE audit-flagged fact, 153_it_tick_Administrative rights, whose prompt-only ceiling is inverted (0.32 on test; 0.28 on the 200 replication items) ‖ block B (without LABEL_DEFECT ∪ flagged): UNDERPOWERED (0 BH exceedances of 276 cells). Printed with equal prominence by Guiv's decision (2026-10-19). | | |
| H3 | NOT RUN | 108 | §4.9 f MODEL key (paraphrase-majority pick) has no rows in the frozen collection; Guiv's option A (2026-10-19): primary H3 stays NOT RUN, the side-module H3 (r/h3-para) is reported as SECONDARY when it lands; descriptive single-phrasing R3 below |
| H4 | INCOMPLETE | 113 | jlens: lag S/T 8 [0, 10] n=22 → UNDERPOWERED; COMPUTED∪INTERNAL 8 [8, 20] n=11 → SUPPORTED; olens (community): lag S/T 18 [18, 20] n=25 → REFUTED; COMPUTED∪INTERNAL 18 [10, 20] n=9 → SUPPORTED; render |Δ|jlens − |Δ|probe +0.062 [0.044, 0.080] n=113 → SUPPORTED; render |Δ|nla − |Δ|probe +0.054 [0.034, 0.076] n=113 → SUPPORTED; render |Δ|olens (community) − |Δ|probe +0.074 [0.057, 0.091] n=113 → SUPPORTED; render |Δ|skip_a − |Δ|probe +0.075 [0.055, 0.096] n=113 → SUPPORTED; INCOMPLETE: only 0/113 facts have chat probe curves on §4.4's full grid 24–60 step 4 (the rest are floored at their lowest synced layer), so these clause results are not a verdict |
| H5 | REFUTED | 30 | VERDICT AT BOTH BLOCKS (equal prominence): block 42 (decided, # RULE) → REFUTED; block 38 (gradient transported from 42) → REFUTED; the verdict does not depend on the block. Note: WS4's preliminary block-38 cosines were visible when block 42 was chosen (BRIEF_R Deviations). — jlens@42 median cos(d_jlens, d_cm) +0.09 [0.05, 0.12] n=30 → REFUTED; jlens@38 (transported from 42) median +0.07 [0.06, 0.10] → REFUTED; jlens@42 median cos(d_jlens, d_probe) +0.03 [0.02, 0.08] n=30 → SUPPORTED; jlens@38 (transported from 42) median +0.04 [0.01, 0.07] → SUPPORTED; olens (community)@42 median cos(d_olens, d_cm) +0.07 [0.05, 0.09] n=30 → REFUTED; olens (community)@38 (transported from 42) median +0.06 [0.03, 0.09] → REFUTED; olens (community)@42 median cos(d_olens, d_probe) +0.03 [0.02, 0.06] n=30 → SUPPORTED; olens (community)@38 (transported from 42) median +0.04 [0.02, 0.07] → SUPPORTED; nla@42 median cos(d_nla, d_cm) +0.08 [0.06, 0.12] n=30 → REFUTED; nla@38 (transported from 42) median +0.07 [0.05, 0.11] → REFUTED; nla@42 median cos(d_nla, d_probe) +0.05 [0.03, 0.07] n=30 → SUPPORTED; nla@38 (transported from 42) median +0.06 [0.03, 0.07] → SUPPORTED; skip_a@42 median cos(d_skip_a, d_cm) +0.09 [0.06, 0.12] n=30 → REFUTED; skip_a@38 (transported from 42) median +0.08 [0.06, 0.12] → REFUTED; skip_a@42 median cos(d_skip_a, d_probe) +0.06 [0.03, 0.07] n=30 → SUPPORTED; skip_a@38 (transported from 42) median +0.06 [0.04, 0.07] → SUPPORTED; (J-lens native-at-38: median cos(d_jlens38, d_cm) +0.07); (J-lens native-at-38: median cos(d_jlens38, d_probe) +0.04); (transport check: cos(J-lens transported, native at 38) median +0.88, range [+0.84, +0.91], 30 facts); jlens REPORT-FLIPPABLE: no defined verdicts (the dose never reached the 75% rate); jlens READER-BLIND: no defined verdicts (the dose never reached the 75% rate); nla REPORT-FLIPPABLE: no defined verdicts (the dose never reached the 75% rate); nla READER-BLIND: no defined verdicts (the dose never reached the 75% rate); olens (community) REPORT-FLIPPABLE: no defined verdicts (the dose never reached the 75% rate); olens (community) READER-BLIND: no defined verdicts (the dose never reached the 75% rate); skip_a REPORT-FLIPPABLE: no defined verdicts (the dose never reached the 75% rate); skip_a READER-BLIND: no defined verdicts (the dose never reached the 75% rate); SWAP add-on (WS4): pre-registered, NOT RUN |
| H6 | REFUTED | 3 | primary-site k-way rows on 15/15 R-B parents, 3/3 of the K ≥ 6 parents (n = the latter); jlens: no parent with two-way AUROC ≥ 0.85 (premise not met; 1 parents); nla: no parent with two-way AUROC ≥ 0.85 (premise not met; 3 parents); olens (community): no parent with two-way AUROC ≥ 0.85 (premise not met; 3 parents); skip_a: no parent with two-way AUROC ≥ 0.85 (premise not met; 3 parents); probe (k-class, pool, block 42, C = 1 as analyze.r6_kway) mean 0.646 [0.551, 0.760] over 8 cells → REFUTED; model (prompt-only k-way) mean 0.691 [0.581, 0.778] over 8 cells → REFUTED |
| H7 | UNDERPOWERED | 113 | votes as implemented: median split on every fact (deviation from §4.7, found by TH-2); gain (§1: consensus − best reader on all items) +3.14 pts [-0.12, +5.57] (clustered CI, the wider) → UNDERPOWERED; (§4.7 same-items form +0.00, ≡ 0 by construction); shared-wrong ratio 21.61 [6.14, 58.91] (clustered) → SUPPORTED; readers per fact 4 |
| H7 (§4.7-literal votes; the pre-registered specification) | UNDERPOWERED | 113 | votes per §4.7: sign of s_diff (two-sided), median (one-sided); gain (§1: consensus − best reader on all items) +4.53 pts [+1.55, +6.95] (clustered CI, the wider) → UNDERPOWERED; (§4.7 same-items form +0.00, ≡ 0 by construction); shared-wrong ratio 8.39 [5.10, 14.25] (clustered) → SUPPORTED; readers per fact 4 |
| H7 on TH-2's population (without LABEL_DEFECT only), as implemented | UNDERPOWERED | 108 | median-split votes; gain (§1: consensus − best reader on all items) +3.19 pts [-0.53, +5.60] (clustered CI, the wider) → UNDERPOWERED; (§4.7 same-items form +0.00, ≡ 0 by construction); shared-wrong ratio 22.58 [6.22, 61.73] (clustered) → SUPPORTED; readers per fact 4 |
| H7 on TH-2's population (without LABEL_DEFECT only), §4.7-literal | UNDERPOWERED | 108 | §4.7 votes; gain (§1: consensus − best reader on all items) +4.64 pts [+1.62, +7.16] (clustered CI, the wider) → UNDERPOWERED; (§4.7 same-items form +0.00, ≡ 0 by construction); shared-wrong ratio 8.72 [5.26, 14.58] (clustered) → SUPPORTED; readers per fact 4 |
| R1b-noise (0.25) | REFUTED | 45 | n=2 +0.000 [0.000, 0.000] → REFUTED (DEGENERATE: Δ ≡ 0 on every fact); n=4 +0.026 [0.001, 0.056] → SUPPORTED; n=8 -0.006 [-0.046, 0.027] → UNDERPOWERED; n=16 +0.020 [-0.009, 0.048] → UNDERPOWERED; n=32 +0.027 [-0.006, 0.060] → UNDERPOWERED; ΔAUC(512) +0.023 ≥ +0.01; SENSITIVITY (not the verdict): without the degenerate n → UNDERPOWERED |
| R1b-imbalance (0.1) | REFUTED | 45 | n=16 -0.011 [-0.034, 0.021] → UNDERPOWERED; n=32 -0.020 [-0.039, 0.001] → REFUTED |
| R1b-shift (chat→raw) | REFUTED | 45 | n=16 -0.018 [-0.043, 0.004] → REFUTED; n=32 -0.011 [-0.040, 0.016] → REFUTED; ΔAUC(512) -0.001 < +0.01 |
| H3 (secondary: §14 paraphrase key), all items | REFUTED | 108 | jlens@42 P(text) 0.49 [0.48, 0.51] → REFUTED; jlens@44 P(text) 0.49 [0.48, 0.51] → REFUTED; jlens@48 P(text) 0.49 [0.47, 0.50] → REFUTED; nla@42 P(text) 0.51 [0.49, 0.52] → REFUTED; olens (community)@42 P(text) 0.49 [0.47, 0.51] → REFUTED; olens (community)@44 P(text) 0.49 [0.47, 0.50] → REFUTED; olens (community)@48 P(text) 0.48 [0.47, 0.50] → REFUTED; skip_a@42 P(text) 0.47 [0.46, 0.49] → REFUTED; jlens@56 P(model) 0.52 [0.50, 0.54] → REFUTED; olens (community)@56 P(model) 0.52 [0.50, 0.54] → REFUTED; jlens probe lead: a TEXT→MODEL crossing exists on 1/108 facts — not testable; olens (community) probe lead: a TEXT→MODEL crossing exists on 0/108 facts — not testable; key-trained probe reaches 0.75 on 109/112 facts (median first layer 24) |
| H3 (secondary: §14 paraphrase key), stable items only | REFUTED | 102 | jlens@42 P(text) 0.48 [0.46, 0.49] → REFUTED; jlens@44 P(text) 0.48 [0.46, 0.50] → REFUTED; jlens@48 P(text) 0.48 [0.46, 0.50] → REFUTED; nla@42 P(text) 0.50 [0.49, 0.52] → REFUTED; olens (community)@42 P(text) 0.48 [0.46, 0.50] → REFUTED; olens (community)@44 P(text) 0.48 [0.46, 0.50] → REFUTED; olens (community)@48 P(text) 0.48 [0.46, 0.50] → REFUTED; skip_a@42 P(text) 0.46 [0.44, 0.48] → REFUTED; jlens@56 P(model) 0.53 [0.51, 0.55] → REFUTED; olens (community)@56 P(model) 0.53 [0.52, 0.55] → REFUTED; jlens probe lead: a TEXT→MODEL crossing exists on 1/102 facts — not testable; olens (community) probe lead: a TEXT→MODEL crossing exists on 1/102 facts — not testable; key-trained probe reaches 0.75 on 109/112 facts (median first layer 24) |

## CIs that exclude equivalence

R2 Δ (reader − prompt-only) with 95% CI entirely outside ±0.05: 4 above, 317 below, of 452 lens cells.
Above (reader beats the model's own report): skip_a 153_it_tick_Administrative rights [TOPIC] Δ +0.245 [+0.147, +0.340] BH; jlens 144_cancer_cat_Colon_Cancer [TOPIC] Δ +0.232 [+0.083, +0.376]; olens (community) 153_it_tick_Administrative rights [TOPIC] Δ +0.227 [+0.124, +0.314] BH; skip_a 146_disease_class_cardiovascular diseases [TOPIC] Δ +0.174 [+0.072, +0.276]
R7 per-fact consensus gain (§1 form) is a point estimate per fact (no per-fact CI); 69/113 facts > +2 pts.

# B — without the label-defect and audit-flagged facts

## Controls

**Shuffled gate (§4.2, 95% CI ∋ 0.5):** 3754 pass / 198 fail of 3952 cells (expected false fails at 5%: 198).

| reader | pass | fail | fail at primary site |
|---|---|---|---|
| jlens | 2367 | 129 | 9/104 |
| nla | 197 | 11 | 6/104 |
| olens (community) | 991 | 49 | 6/104 |
| skip_a | 199 | 9 | 3/104 |

Failing primary-site shuffled cells (pipeline bug first, §4.9 c): nla 7_hist_fig_ispolitician 0.371 [0.297, 0.447]; jlens 56_wikidatasex_or_gender 0.392 [0.312, 0.469]; jlens 130_temp_cat_Frequency 0.397 [0.286, 0.499]; nla 151_it_tick_HR Support 0.399 [0.317, 0.479]; jlens 135_context_type_Event_duration 0.399 [0.325, 0.484]; jlens 63_wikidata_occupation_issinger 0.401 [0.319, 0.477]; olens (community) 163_agnews_2 0.402 [0.315, 0.480]; nla 65_high-school 0.407 [0.335, 0.491]; olens (community) 72_gene-expression 0.408 [0.332, 0.490]; skip_a 163_agnews_2 0.409 [0.326, 0.495]; olens (community) 152_it_tick_Hardware 0.410 [0.334, 0.491]; skip_a 91_glue_qqp 0.412 [0.330, 0.491]; jlens 163_agnews_2 0.412 [0.335, 0.495]; jlens 91_glue_qqp 0.416 [0.329, 0.496]; olens (community) 135_context_type_Event_duration 0.417 [0.334, 0.495]; nla 56_wikidatasex_or_gender 0.417 [0.334, 0.489]; nla 100_news_fake 0.418 [0.346, 0.489]; olens (community) 148_twt_emotion_worry 0.420 [0.347, 0.500]; jlens 24_headline_isiran 0.576 [0.501, 0.649]; nla 84_clinical-trials 0.580 [0.507, 0.657]; jlens 51_just_is 0.593 [0.520, 0.669]; jlens 83_third-party 0.603 [0.522, 0.675]; olens (community) 24_headline_isiran 0.611 [0.532, 0.690]; skip_a 24_headline_isiran 0.615 [0.536, 0.691]

**State-free prior (§2.2, descriptive):** per reader at the primary site, median |prior z| and the number of two-sided facts where ≥ 90% of natural items carry the prior's sign (the reader answers its prior).

| reader | facts | median |prior z| | prior-dominated (≥ 90%) |
|---|---|---|---|
| jlens | 104 | 0.09 | 8 |
| nla | 104 | 0.46 | 16 |
| olens (community) | 104 | 0.29 | 10 |
| skip_a | 104 | 0.53 | 12 |

**Random directions (§4.5, §4.9 i):** apply to edited states only (R5 steering, pod F); no steer rows yet — not run.

## R2 — reader vs prompt-only ceiling and probe, by tag (primary site, chat)

Median AUROC over facts; Δ = reader − prompt-only (paired bootstrap per fact); exceed = Δ ≥ +0.05 with CI > 0 (raw / after BH q = 0.10 per reader); probe(512) at block 42 where states exist.

| tag | reader | facts | reader | prompt-only | probe(512) | mean Δ | exceed raw | exceed BH | reader ≥ 0.8×probe |
|---|---|---|---|---|---|---|---|---|---|
| COMPUTED | jlens | 17 | 0.733 | 0.933 | 0.960 | -0.204 | 0 | 0 | 9/17 |
| COMPUTED | logit_lens | 17 | 0.518 | 0.933 | 0.960 | -0.332 | 0 | 0 | 4/17 |
| COMPUTED | nla | 17 | 0.696 | 0.933 | 0.960 | -0.273 | 0 | 0 | 8/17 |
| COMPUTED | olens (community) | 17 | 0.744 | 0.933 | 0.960 | -0.173 | 0 | 0 | 10/17 |
| COMPUTED | skip_a | 17 | 0.758 | 0.933 | 0.960 | -0.177 | 0 | 0 | 8/17 |
| FORM | jlens | 6 | 0.585 | 0.912 | 0.980 | -0.276 | 0 | 0 | 1/6 |
| FORM | logit_lens | 6 | 0.519 | 0.912 | 0.980 | -0.356 | 0 | 0 | 0/6 |
| FORM | nla | 6 | 0.662 | 0.912 | 0.980 | -0.194 | 0 | 0 | 2/6 |
| FORM | olens (community) | 6 | 0.602 | 0.912 | 0.980 | -0.275 | 0 | 0 | 1/6 |
| FORM | skip_a | 6 | 0.596 | 0.912 | 0.980 | -0.259 | 0 | 0 | 1/6 |
| KNOWLEDGE | jlens | 21 | 0.636 | 0.934 | 0.869 | -0.222 | 0 | 0 | 9/21 |
| KNOWLEDGE | logit_lens | 21 | 0.557 | 0.934 | 0.869 | -0.324 | 0 | 0 | 3/21 |
| KNOWLEDGE | nla | 21 | 0.641 | 0.934 | 0.869 | -0.222 | 0 | 0 | 9/21 |
| KNOWLEDGE | olens (community) | 21 | 0.680 | 0.934 | 0.869 | -0.198 | 0 | 0 | 9/21 |
| KNOWLEDGE | skip_a | 21 | 0.666 | 0.934 | 0.869 | -0.207 | 0 | 0 | 12/21 |
| META | jlens | 5 | 0.807 | 0.983 | 0.983 | -0.224 | 0 | 0 | 3/5 |
| META | logit_lens | 5 | 0.465 | 0.983 | 0.983 | -0.498 | 0 | 0 | 0/5 |
| META | nla | 5 | 0.665 | 0.983 | 0.983 | -0.266 | 0 | 0 | 2/5 |
| META | olens (community) | 5 | 0.694 | 0.983 | 0.983 | -0.309 | 0 | 0 | 1/5 |
| META | skip_a | 5 | 0.769 | 0.983 | 0.983 | -0.234 | 0 | 0 | 1/5 |
| PASSAGE-KNOWLEDGE | jlens | 9 | 0.651 | 0.802 | 0.837 | -0.169 | 0 | 0 | 4/9 |
| PASSAGE-KNOWLEDGE | logit_lens | 9 | 0.513 | 0.802 | 0.837 | -0.308 | 0 | 0 | 1/9 |
| PASSAGE-KNOWLEDGE | nla | 9 | 0.609 | 0.802 | 0.837 | -0.219 | 0 | 0 | 2/9 |
| PASSAGE-KNOWLEDGE | olens (community) | 9 | 0.593 | 0.802 | 0.837 | -0.213 | 0 | 0 | 3/9 |
| PASSAGE-KNOWLEDGE | skip_a | 9 | 0.664 | 0.802 | 0.837 | -0.188 | 0 | 0 | 6/9 |
| SURFACE | jlens | 28 | 0.637 | 1.000 | 0.945 | -0.360 | 0 | 0 | 6/28 |
| SURFACE | logit_lens | 28 | 0.522 | 1.000 | 0.945 | -0.435 | 0 | 0 | 4/28 |
| SURFACE | nla | 28 | 0.713 | 1.000 | 0.945 | -0.236 | 0 | 0 | 13/28 |
| SURFACE | olens (community) | 28 | 0.741 | 1.000 | 0.945 | -0.257 | 0 | 0 | 15/28 |
| SURFACE | skip_a | 28 | 0.759 | 1.000 | 0.945 | -0.251 | 0 | 0 | 15/28 |
| TOPIC | jlens | 18 | 0.693 | 0.935 | 0.970 | -0.201 | 0 | 0 | 10/18 |
| TOPIC | logit_lens | 18 | 0.588 | 0.935 | 0.970 | -0.250 | 0 | 0 | 6/18 |
| TOPIC | nla | 18 | 0.584 | 0.935 | 0.970 | -0.302 | 0 | 0 | 8/18 |
| TOPIC | olens (community) | 18 | 0.700 | 0.935 | 0.970 | -0.266 | 0 | 0 | 6/18 |
| TOPIC | skip_a | 18 | 0.650 | 0.935 | 0.970 | -0.209 | 0 | 0 | 10/18 |

## Oracle lens (community) vs model asked directly (prompt-only), chat onset vs raw last token

Δ = AUROC(prompt-only: Qwen asked the question directly) − AUROC(Oracle lens (community) on the state); per-fact sign from the item-paired bootstrap; tag means with a fact-bootstrap 95% CI. This is NOT the Gemma Check-2 (which gives the Oracle (community) the text): that is the last column, from the text-arm rows. The render is the Oracle's (community) read site; prompt-only has its own prompt.

**olens (community) @ block 42**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.184 [0.126, 0.249] | 14 / 0 | +0.304 [0.266, 0.341] | 17 / 0 | — | — |
| FORM (6) | +0.272 [0.156, 0.366] | 5 / 0 | +0.325 [0.211, 0.419] | 5 / 0 | — | — |
| KNOWLEDGE (21) | +0.203 [0.154, 0.257] | 20 / 0 | +0.193 [0.146, 0.244] | 21 / 0 | — | — |
| META (5) | +0.301 [0.206, 0.400] | 5 / 0 | +0.310 [0.137, 0.483] | 5 / 0 | — | — |
| PASSAGE-KNOWLEDGE (9) | +0.225 [0.173, 0.287] | 8 / 0 | +0.100 [-0.014, 0.220] | 5 / 2 | — | — |
| SURFACE (28) | +0.256 [0.197, 0.322] | 25 / 0 | +0.124 [0.076, 0.176] | 25 / 0 | — | — |
| TOPIC (18) | +0.270 [0.176, 0.381] | 15 / 0 | +0.264 [0.198, 0.340] | 17 / 0 | — | — |
| all (104) | +0.236 [0.206, 0.268] | 92 / 0 | +0.210 [0.179, 0.239] | 95 / 2 | — | — |

**olens (community) @ block 44**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.173 [0.116, 0.235] | 16 / 0 | +0.304 [0.257, 0.345] | 17 / 0 | -0.211 [-0.272, -0.145] (14 act / 0 text, n=17) | -0.080 [-0.129, -0.029] (8 act / 0 text, n=17) |
| FORM (6) | +0.275 [0.146, 0.393] | 5 / 0 | +0.334 [0.224, 0.430] | 5 / 0 | -0.070 [-0.176, 0.047] (3 act / 1 text, n=6) | -0.011 [-0.040, 0.020] (0 act / 0 text, n=6) |
| KNOWLEDGE (21) | +0.198 [0.150, 0.251] | 19 / 0 | +0.186 [0.138, 0.238] | 21 / 0 | -0.043 [-0.092, 0.003] (7 act / 2 text, n=21) | -0.055 [-0.081, -0.027] (10 act / 0 text, n=21) |
| META (5) | +0.309 [0.200, 0.420] | 5 / 0 | +0.324 [0.140, 0.505] | 5 / 0 | +0.036 [-0.059, 0.098] (0 act / 1 text, n=5) | +0.052 [-0.134, 0.208] (1 act / 2 text, n=5) |
| PASSAGE-KNOWLEDGE (9) | +0.213 [0.155, 0.275] | 8 / 0 | +0.097 [-0.024, 0.231] | 5 / 2 | +0.115 [0.044, 0.182] (0 act / 6 text, n=9) | -0.000 [-0.040, 0.044] (2 act / 1 text, n=9) |
| SURFACE (28) | +0.257 [0.199, 0.322] | 25 / 0 | +0.123 [0.076, 0.176] | 25 / 0 | +0.145 [0.086, 0.196] (3 act / 22 text, n=28) | +0.011 [-0.003, 0.027] (1 act / 7 text, n=28) |
| TOPIC (18) | +0.266 [0.173, 0.376] | 15 / 0 | +0.277 [0.211, 0.350] | 18 / 0 | -0.010 [-0.079, 0.056] (7 act / 7 text, n=18) | +0.000 [-0.046, 0.045] (3 act / 4 text, n=18) |
| all (104) | +0.233 [0.201, 0.265] | 93 / 0 | +0.212 [0.179, 0.242] | 96 / 2 | +0.002 [-0.034, 0.036] (34 act / 39 text, n=104) | -0.019 [-0.037, -0.002] (25 act / 14 text, n=104) |

**olens (community) @ block 48**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.157 [0.098, 0.222] | 14 / 0 | +0.305 [0.263, 0.345] | 17 / 0 | — | — |
| FORM (6) | +0.287 [0.195, 0.367] | 5 / 0 | +0.336 [0.209, 0.436] | 5 / 0 | — | — |
| KNOWLEDGE (21) | +0.198 [0.153, 0.245] | 20 / 0 | +0.187 [0.138, 0.240] | 21 / 0 | — | — |
| META (5) | +0.329 [0.214, 0.465] | 5 / 0 | +0.311 [0.145, 0.476] | 5 / 0 | — | — |
| PASSAGE-KNOWLEDGE (9) | +0.201 [0.124, 0.274] | 7 / 0 | +0.110 [-0.013, 0.240] | 5 / 2 | — | — |
| SURFACE (28) | +0.268 [0.208, 0.334] | 25 / 0 | +0.123 [0.078, 0.174] | 25 / 0 | — | — |
| TOPIC (18) | +0.251 [0.156, 0.362] | 15 / 0 | +0.272 [0.204, 0.348] | 18 / 0 | — | — |
| all (104) | +0.231 [0.199, 0.263] | 91 / 0 | +0.212 [0.179, 0.241] | 96 / 2 | — | — |

**olens (community) @ block 52**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.173 [0.113, 0.240] | 15 / 0 | +0.317 [0.278, 0.357] | 17 / 0 | — | — |
| FORM (6) | +0.304 [0.195, 0.382] | 5 / 0 | +0.282 [0.149, 0.382] | 5 / 0 | — | — |
| KNOWLEDGE (21) | +0.193 [0.157, 0.229] | 21 / 0 | +0.190 [0.146, 0.241] | 21 / 0 | — | — |
| META (5) | +0.267 [0.151, 0.373] | 5 / 0 | +0.259 [0.145, 0.356] | 5 / 0 | — | — |
| PASSAGE-KNOWLEDGE (9) | +0.214 [0.134, 0.292] | 8 / 0 | +0.138 [0.050, 0.247] | 6 / 0 | — | — |
| SURFACE (28) | +0.259 [0.201, 0.322] | 25 / 0 | +0.140 [0.090, 0.199] | 26 / 0 | — | — |
| TOPIC (18) | +0.236 [0.146, 0.349] | 15 / 0 | +0.259 [0.181, 0.347] | 18 / 0 | — | — |
| all (104) | +0.227 [0.197, 0.257] | 94 / 0 | +0.213 [0.183, 0.241] | 98 / 0 | — | — |

**olens (community) @ block 56**

| tag (facts) | chat: model − Oracle (community) [CI] | model / Oracle (community) wins | raw: model − Oracle (community) [CI] | model / Oracle (community) wins | chat: Oracle(text) (community) − Oracle(act) (community) [CI] | raw: Oracle(text) (community) − Oracle(act) (community) [CI] |
|---|---|---|---|---|---|---|
| COMPUTED (17) | +0.194 [0.129, 0.265] | 15 / 0 | +0.322 [0.276, 0.367] | 17 / 0 | — | — |
| FORM (6) | +0.314 [0.198, 0.399] | 5 / 0 | +0.308 [0.179, 0.407] | 5 / 0 | — | — |
| KNOWLEDGE (21) | +0.192 [0.156, 0.229] | 21 / 0 | +0.211 [0.168, 0.256] | 21 / 0 | — | — |
| META (5) | +0.260 [0.130, 0.362] | 5 / 0 | +0.262 [0.172, 0.339] | 5 / 0 | — | — |
| PASSAGE-KNOWLEDGE (9) | +0.203 [0.122, 0.284] | 7 / 0 | +0.138 [0.044, 0.252] | 6 / 0 | — | — |
| SURFACE (28) | +0.253 [0.193, 0.320] | 25 / 0 | +0.142 [0.092, 0.198] | 25 / 0 | — | — |
| TOPIC (18) | +0.227 [0.141, 0.334] | 15 / 0 | +0.245 [0.166, 0.336] | 16 / 0 | — | — |
| all (104) | +0.226 [0.196, 0.257] | 93 / 0 | +0.218 [0.189, 0.246] | 95 / 0 | — | — |


## R4 — layer × render (natural test cells; median AUROC over facts)

**chat**

| reader | 24 | 28 | 32 | 36 | 38 | 40 | 42 | 44 | 48 | 52 | 56 | 60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| jlens | 0.57 | 0.58 | 0.64 | 0.64 | 0.64 | 0.66 | 0.66 | 0.65 | 0.64 | 0.69 | 0.70 | 0.69 |
| logit_lens | 0.54 | 0.54 | 0.56 | 0.53 | 0.55 | 0.53 | 0.53 | 0.53 | 0.54 | 0.56 | 0.59 | 0.63 |
| nla | — | — | — | — | — | — | 0.67 | — | — | — | — | — |
| olens (community) | — | — | — | — | — | — | 0.70 | 0.70 | 0.71 | 0.69 | 0.70 | — |
| skip_a | — | — | — | — | — | — | 0.71 | — | — | — | — | — |

**raw**

| reader | 24 | 28 | 32 | 36 | 38 | 40 | 42 | 44 | 48 | 52 | 56 | 60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| jlens | 0.60 | 0.63 | 0.65 | 0.69 | 0.68 | 0.70 | 0.70 | 0.69 | 0.70 | 0.69 | 0.67 | 0.66 |
| logit_lens | 0.56 | 0.57 | 0.55 | 0.59 | 0.57 | 0.58 | 0.58 | 0.57 | 0.59 | 0.60 | 0.58 | 0.60 |
| nla | — | — | — | — | — | — | 0.74 | — | — | — | — | — |
| olens (community) | — | — | — | — | — | — | 0.66 | 0.67 | 0.69 | 0.69 | 0.68 | — |
| skip_a | — | — | — | — | — | — | 0.78 | — | — | — | — | — |

Render shift at the primary site (chat − raw, §4.4; RENDER-ROBUST iff |Δ| ≤ 0.05 on ≥ 80% of facts):

| reader | layer | facts | median Δ | |Δ| ≤ 0.05 | robust |
|---|---|---|---|---|---|
| jlens | 42 | 104 | -0.016 | 36% | no |
| logit_lens | 42 | 104 | -0.020 | 24% | no |
| nla | 42 | 104 | -0.051 | 32% | no |
| olens (community) | 44 | 104 | -0.008 | 20% | no |
| skip_a | 42 | 104 | -0.018 | 30% | no |

Lag L_read − L_present by tag (chat; needs probe curves): jlens/COMPUTED +8 (n=11); jlens/FORM +12 (n=3); jlens/KNOWLEDGE +8 (n=11); jlens/META +0 (n=4); jlens/PASSAGE-KNOWLEDGE +32 (n=4); jlens/SURFACE +0 (n=11); jlens/TOPIC +8 (n=9); logit_lens/COMPUTED +19 (n=8); logit_lens/FORM +16 (n=1); logit_lens/KNOWLEDGE +32 (n=11); logit_lens/META +0 (n=1); logit_lens/PASSAGE-KNOWLEDGE +nan (n=0); logit_lens/SURFACE +4 (n=11); logit_lens/TOPIC +16 (n=7); nla/COMPUTED +18 (n=7); nla/FORM +18 (n=2); nla/KNOWLEDGE +18 (n=6); nla/META +18 (n=2); nla/PASSAGE-KNOWLEDGE +nan (n=0); nla/SURFACE +18 (n=12); nla/TOPIC +18 (n=3); olens (community)/COMPUTED +18 (n=9); olens (community)/FORM +nan (n=0); olens (community)/KNOWLEDGE +18 (n=10); olens (community)/META +24 (n=2); olens (community)/PASSAGE-KNOWLEDGE +24 (n=1); olens (community)/SURFACE +18 (n=18); olens (community)/TOPIC +18 (n=7); skip_a/COMPUTED +18 (n=9); skip_a/FORM +18 (n=1); skip_a/KNOWLEDGE +18 (n=8); skip_a/META +18 (n=3); skip_a/PASSAGE-KNOWLEDGE +18 (n=1); skip_a/SURFACE +18 (n=14); skip_a/TOPIC +18 (n=7)

## R3 (descriptive) — conflict items: does the reader side with the model's answer or the text label?

Key: the model's single forced-choice pick (prompt-only greedy), **not** the pre-registered paraphrase-majority key (§4.9 f), which has no rows; so H3 is NOT RUN. Facts with ≥ 12 conflict items; chat render.

| reader | layer | facts | READS_MODEL | READS_TEXT | MIXED | pooled P(model) |
|---|---|---|---|---|---|---|
| jlens | 24 | 65 | 3 | 1 | 61 | 0.52 |
| jlens | 28 | 65 | 4 | 0 | 61 | 0.52 |
| jlens | 32 | 65 | 3 | 1 | 61 | 0.52 |
| jlens | 36 | 65 | 7 | 5 | 53 | 0.52 |
| jlens | 38 | 65 | 6 | 5 | 54 | 0.53 |
| jlens | 40 | 65 | 7 | 3 | 55 | 0.53 |
| jlens | 42 | 65 | 5 | 4 | 56 | 0.53 |
| jlens | 44 | 65 | 7 | 4 | 54 | 0.53 |
| jlens | 48 | 65 | 3 | 2 | 60 | 0.53 |
| jlens | 52 | 65 | 4 | 2 | 59 | 0.53 |
| jlens | 56 | 65 | 1 | 2 | 62 | 0.52 |
| jlens | 60 | 65 | 1 | 4 | 60 | 0.51 |
| nla | 42 | 65 | 1 | 1 | 63 | 0.48 |
| olens (community) | 42 | 65 | 6 | 4 | 55 | 0.53 |
| olens (community) | 44 | 65 | 6 | 4 | 55 | 0.52 |
| olens (community) | 48 | 65 | 5 | 4 | 56 | 0.53 |
| olens (community) | 52 | 65 | 4 | 2 | 59 | 0.52 |
| olens (community) | 56 | 65 | 4 | 2 | 59 | 0.52 |
| skip_a | 42 | 65 | 6 | 2 | 57 | 0.52 |

## H3 (secondary: §14 paraphrase key)

**Secondary result, labelled as such.** The paraphrases were written after single-phrasing prompt-only data existed (and after WS3's descriptive single-key R3), blind to every result: three fixed templates applied programmatically (§14). Key = majority of model_says_pos over frozen, p1, p2 on 22198 test items; unstable = the three disagree.

Unstable items: 8.0% overall; by tag: COMPUTED 12.3%; FORM 7.5%; KNOWLEDGE 14.0%; META 8.7%; PASSAGE-KNOWLEDGE 5.0%; SURFACE 2.7%; TOPIC 7.3%
Datasets above the §4.9 f 15% instability flag: 16 — 137_glue_mnli_neutral 68%, 131_temp_cat_Typical Time 47%, 128_art_type_movie 40%, 153_it_tick_Administrative rights 38%, 126_art_type_book 33%, 114_nyc_borough_Manhattan 27%, 7_hist_fig_ispolitician 24%, 129_arith_mc_A 22%
ICC(2,1) over the LO of frozen/p1/p2, median over facts: 0.96; key ≠ single-phrasing pick on 2.7% of items.

**all items** — pooled over conflict items (key ≠ label), chat render:

| reader | layer | facts | conflict items | P(sides with TEXT) [Wilson] | P(sides with MODEL) |
|---|---|---|---|---|---|
| jlens | 24 | 99 | 3121 | 0.49 [0.47, 0.51] | 0.51 |
| jlens | 28 | 99 | 3121 | 0.49 [0.47, 0.50] | 0.51 |
| jlens | 32 | 99 | 3121 | 0.50 [0.48, 0.51] | 0.50 |
| jlens | 36 | 99 | 3121 | 0.50 [0.48, 0.52] | 0.50 |
| jlens | 38 | 99 | 3121 | 0.49 [0.47, 0.51] | 0.51 |
| jlens | 40 | 99 | 3121 | 0.49 [0.47, 0.51] | 0.51 |
| jlens | 42 | 99 | 3121 | 0.49 [0.47, 0.51] | 0.51 |
| jlens | 44 | 99 | 3121 | 0.49 [0.47, 0.51] | 0.51 |
| jlens | 48 | 99 | 3121 | 0.48 [0.46, 0.50] | 0.52 |
| jlens | 52 | 99 | 3121 | 0.48 [0.46, 0.49] | 0.52 |
| jlens | 56 | 99 | 3121 | 0.48 [0.47, 0.50] | 0.52 |
| jlens | 60 | 99 | 3121 | 0.50 [0.48, 0.51] | 0.50 |
| nla | 42 | 99 | 3121 | 0.52 [0.50, 0.54] | 0.48 |
| olens (community) | 42 | 99 | 3121 | 0.49 [0.47, 0.51] | 0.51 |
| olens (community) | 44 | 99 | 3121 | 0.49 [0.47, 0.51] | 0.51 |
| olens (community) | 48 | 99 | 3121 | 0.48 [0.47, 0.50] | 0.52 |
| olens (community) | 52 | 99 | 3121 | 0.48 [0.46, 0.50] | 0.52 |
| olens (community) | 56 | 99 | 3121 | 0.48 [0.46, 0.50] | 0.52 |
| skip_a | 42 | 99 | 3121 | 0.48 [0.46, 0.50] | 0.52 |

**stable items only** — pooled over conflict items (key ≠ label), chat render:

| reader | layer | facts | conflict items | P(sides with TEXT) [Wilson] | P(sides with MODEL) |
|---|---|---|---|---|---|
| jlens | 24 | 93 | 2364 | 0.48 [0.46, 0.50] | 0.52 |
| jlens | 28 | 93 | 2364 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 32 | 93 | 2364 | 0.48 [0.46, 0.50] | 0.52 |
| jlens | 36 | 93 | 2364 | 0.48 [0.46, 0.50] | 0.52 |
| jlens | 38 | 93 | 2364 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 40 | 93 | 2364 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 42 | 93 | 2364 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 44 | 93 | 2364 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 48 | 93 | 2364 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 52 | 93 | 2364 | 0.46 [0.44, 0.48] | 0.54 |
| jlens | 56 | 93 | 2364 | 0.47 [0.45, 0.49] | 0.53 |
| jlens | 60 | 93 | 2364 | 0.48 [0.46, 0.50] | 0.52 |
| nla | 42 | 93 | 2364 | 0.52 [0.50, 0.54] | 0.48 |
| olens (community) | 42 | 93 | 2364 | 0.48 [0.46, 0.50] | 0.52 |
| olens (community) | 44 | 93 | 2364 | 0.48 [0.46, 0.50] | 0.52 |
| olens (community) | 48 | 93 | 2364 | 0.48 [0.46, 0.50] | 0.52 |
| olens (community) | 52 | 93 | 2364 | 0.46 [0.44, 0.48] | 0.54 |
| olens (community) | 56 | 93 | 2364 | 0.46 [0.44, 0.48] | 0.54 |
| skip_a | 42 | 93 | 2364 | 0.46 [0.44, 0.48] | 0.54 |


## R1b — the SAE paper's regimes on existing rows (label noise BD-6, class imbalance, covariate shift)

ΔAUC(n) = quiver chosen arrow − probe-only, mean over 5 seeds per fact, then over facts (wider of i.i.d. / clustered CI). Rule subset: 44 facts with a lens reader ≥ 0.8 at its primary site; all-facts means in parentheses.

| regime | param | n | facts | ΔAUC [95% CI] (rule subset) | ΔAUC (all facts) | probe AUROC |
|---|---|---|---|---|---|---|
| imbalance | 0.05 | 16 | 44 | 0.000 [0.000, 0.000] | +0.000 | 0.664 |
| imbalance | 0.05 | 32 | 44 | -0.008 [-0.032, 0.019] | -0.025 | 0.712 |
| imbalance | 0.05 | 128 | 42 | -0.006 [-0.015, 0.003] | -0.016 | 0.778 |
| imbalance | 0.1 | 16 | 44 | -0.010 [-0.032, 0.020] | -0.025 | 0.690 |
| imbalance | 0.1 | 32 | 44 | -0.020 [-0.041, 0.001] | -0.031 | 0.729 |
| imbalance | 0.1 | 128 | 42 | -0.024 [-0.035, -0.013] | -0.038 | 0.817 |
| imbalance | 0.25 | 16 | 44 | -0.005 [-0.025, 0.020] | -0.018 | 0.730 |
| imbalance | 0.25 | 32 | 44 | -0.013 [-0.024, -0.002] | -0.027 | 0.774 |
| imbalance | 0.25 | 128 | 42 | -0.015 [-0.029, -0.006] | -0.040 | 0.845 |
| imbalance | 0.5 | 16 | 44 | -0.012 [-0.030, 0.008] | -0.022 | 0.740 |
| imbalance | 0.5 | 32 | 44 | -0.028 [-0.049, -0.005] | -0.038 | 0.787 |
| imbalance | 0.5 | 128 | 42 | -0.018 [-0.030, -0.007] | -0.034 | 0.857 |
| imbalance | 0.5 | 512 | 41 | -0.001 [-0.002, -0.000] | -0.004 | 0.900 |
| noise | 0.1 | 2 | 44 | 0.000 [0.000, 0.000] | +0.000 | 0.557 |
| noise | 0.1 | 4 | 44 | 0.034 [0.009, 0.065] | +0.005 | 0.625 |
| noise | 0.1 | 8 | 44 | -0.012 [-0.037, 0.012] | -0.022 | 0.673 |
| noise | 0.1 | 16 | 44 | -0.002 [-0.030, 0.025] | -0.018 | 0.707 |
| noise | 0.1 | 32 | 44 | -0.020 [-0.041, 0.001] | -0.034 | 0.755 |
| noise | 0.1 | 64 | 44 | -0.034 [-0.053, -0.016] | -0.059 | 0.795 |
| noise | 0.1 | 128 | 44 | -0.032 [-0.050, -0.017] | -0.047 | 0.822 |
| noise | 0.1 | 256 | 44 | -0.008 [-0.015, -0.001] | -0.024 | 0.849 |
| noise | 0.1 | 512 | 44 | -0.002 [-0.006, 0.002] | -0.008 | 0.871 |
| noise | 0.25 | 2 | 44 | 0.000 [0.000, 0.000] | +0.000 | 0.536 |
| noise | 0.25 | 4 | 44 | 0.025 [-0.001, 0.056] | +0.006 | 0.594 |
| noise | 0.25 | 8 | 44 | -0.006 [-0.049, 0.028] | -0.009 | 0.616 |
| noise | 0.25 | 16 | 44 | 0.018 [-0.014, 0.046] | -0.006 | 0.641 |
| noise | 0.25 | 32 | 44 | 0.030 [-0.003, 0.063] | -0.002 | 0.674 |
| noise | 0.25 | 64 | 44 | 0.009 [-0.022, 0.035] | -0.019 | 0.708 |
| noise | 0.25 | 128 | 44 | -0.025 [-0.057, 0.006] | -0.042 | 0.732 |
| noise | 0.25 | 256 | 44 | 0.010 [-0.015, 0.029] | -0.024 | 0.761 |
| noise | 0.25 | 512 | 44 | 0.023 [0.008, 0.038] | -0.006 | 0.782 |
| noise | 0.4 | 2 | 44 | 0.000 [0.000, 0.000] | +0.000 | 0.520 |
| noise | 0.4 | 4 | 44 | 0.057 [0.032, 0.084] | +0.026 | 0.531 |
| noise | 0.4 | 8 | 44 | 0.024 [-0.026, 0.073] | +0.013 | 0.551 |
| noise | 0.4 | 16 | 44 | 0.043 [-0.012, 0.087] | +0.021 | 0.567 |
| noise | 0.4 | 32 | 44 | 0.115 [0.085, 0.150] | +0.062 | 0.574 |
| noise | 0.4 | 64 | 44 | 0.046 [0.005, 0.083] | +0.012 | 0.596 |
| noise | 0.4 | 128 | 44 | 0.055 [0.016, 0.092] | +0.017 | 0.602 |
| noise | 0.4 | 256 | 44 | 0.070 [0.024, 0.112] | +0.015 | 0.615 |
| noise | 0.4 | 512 | 44 | 0.118 [0.079, 0.155] | +0.046 | 0.621 |
| shift | chat→raw | 16 | 44 | -0.016 [-0.040, 0.005] | -0.005 | 0.716 |
| shift | chat→raw | 32 | 44 | -0.010 [-0.038, 0.016] | -0.015 | 0.744 |
| shift | chat→raw | 128 | 44 | -0.005 [-0.018, 0.010] | -0.013 | 0.795 |
| shift | chat→raw | 512 | 44 | -0.001 [-0.014, 0.006] | -0.000 | 0.814 |
| shift_ref | chat→chat | 16 | 44 | -0.012 [-0.029, 0.009] | -0.022 | 0.745 |
| shift_ref | chat→chat | 32 | 44 | -0.035 [-0.050, -0.020] | -0.044 | 0.790 |
| shift_ref | chat→chat | 128 | 44 | -0.017 [-0.026, -0.009] | -0.031 | 0.861 |
| shift_ref | chat→chat | 512 | 44 | -0.001 [-0.002, -0.000] | -0.006 | 0.903 |

Covariate shift, probe(512) trained on chat: AUROC(chat→raw) − AUROC(chat→chat) = -0.089 (median -0.073, 104 facts); readers' own raw − chat at their primary sites are in the R4 render-shift table.

## Hypotheses so far (BRIEF_R §4.9 d four-way; headline means quote the wider of the i.i.d. and clustered CIs, §4.9 j)

| H | status | n facts | basis |
|---|---|---|---|
| H1 | UNDERPOWERED | 52 | jlens median n* 3.6 [2.6, 5.5] n=52 → SUPPORTED; nla median n* 9.5 [4.6, 14.6] n=52 → UNDERPOWERED; olens (community) median n* 6.5 [3.6, 20.7] n=52 → UNDERPOWERED; skip_a median n* 8.1 [4.0, 25.3] n=52 → UNDERPOWERED; quiver ΔAUC(n≥16): n=16 -0.025 [-0.040, -0.009]ᶜ, n=32 -0.045 [-0.061, -0.030]ᶜ, n=64 -0.066 [-0.080, -0.051]ᶜ, n=128 -0.029 [-0.041, -0.018]ᶜ, n=256 -0.017 [-0.027, -0.007]ᶜ, n=512 -0.007 [-0.012, -0.003]ᶜ → SUPPORTED (ᶜ = clustered CI wider, quoted) |
| H2 | UNDERPOWERED | 69 | 0 claimed BH exceedances over 276 cells; KNOWLEDGE ≥ 0.8×probe(512): jlens 9/21 [0.24, 0.63] → UNDERPOWERED; nla 9/21 [0.24, 0.63] → UNDERPOWERED; olens (community) 9/21 [0.24, 0.63] → UNDERPOWERED; skip_a 12/21 [0.37, 0.76] → UNDERPOWERED; readers without rows yet: skip_d |
| H2 (read with) | H2 — REFUTED (block A, all facts, primary) ‖ it rests on ONE audit-flagged fact, 153_it_tick_Administrative rights, whose prompt-only ceiling is inverted (0.32 on test; 0.28 on the 200 replication items) ‖ block B (without LABEL_DEFECT ∪ flagged): UNDERPOWERED (0 BH exceedances of 276 cells). Printed with equal prominence by Guiv's decision (2026-10-19). | | |
| H3 | NOT RUN | 99 | §4.9 f MODEL key (paraphrase-majority pick) has no rows in the frozen collection; Guiv's option A (2026-10-19): primary H3 stays NOT RUN, the side-module H3 (r/h3-para) is reported as SECONDARY when it lands; descriptive single-phrasing R3 below |
| H4 | INCOMPLETE | 104 | jlens: lag S/T 8 [0, 10] n=20 → UNDERPOWERED; COMPUTED∪INTERNAL 8 [8, 20] n=11 → SUPPORTED; olens (community): lag S/T 18 [18, 20] n=25 → REFUTED; COMPUTED∪INTERNAL 18 [10, 20] n=9 → SUPPORTED; render |Δ|jlens − |Δ|probe +0.063 [0.045, 0.081] n=104 → SUPPORTED; render |Δ|nla − |Δ|probe +0.061 [0.040, 0.083] n=104 → SUPPORTED; render |Δ|olens (community) − |Δ|probe +0.080 [0.062, 0.099] n=104 → SUPPORTED; render |Δ|skip_a − |Δ|probe +0.078 [0.057, 0.101] n=104 → SUPPORTED; INCOMPLETE: only 0/104 facts have chat probe curves on §4.4's full grid 24–60 step 4 (the rest are floored at their lowest synced layer), so these clause results are not a verdict |
| H5 | REFUTED | 30 | VERDICT AT BOTH BLOCKS (equal prominence): block 42 (decided, # RULE) → REFUTED; block 38 (gradient transported from 42) → REFUTED; the verdict does not depend on the block. Note: WS4's preliminary block-38 cosines were visible when block 42 was chosen (BRIEF_R Deviations). — jlens@42 median cos(d_jlens, d_cm) +0.09 [0.05, 0.12] n=30 → REFUTED; jlens@38 (transported from 42) median +0.07 [0.06, 0.10] → REFUTED; jlens@42 median cos(d_jlens, d_probe) +0.03 [0.02, 0.08] n=30 → SUPPORTED; jlens@38 (transported from 42) median +0.04 [0.01, 0.07] → SUPPORTED; olens (community)@42 median cos(d_olens, d_cm) +0.07 [0.05, 0.09] n=30 → REFUTED; olens (community)@38 (transported from 42) median +0.06 [0.03, 0.09] → REFUTED; olens (community)@42 median cos(d_olens, d_probe) +0.03 [0.02, 0.06] n=30 → SUPPORTED; olens (community)@38 (transported from 42) median +0.04 [0.02, 0.07] → SUPPORTED; nla@42 median cos(d_nla, d_cm) +0.08 [0.06, 0.12] n=30 → REFUTED; nla@38 (transported from 42) median +0.07 [0.05, 0.11] → REFUTED; nla@42 median cos(d_nla, d_probe) +0.05 [0.03, 0.07] n=30 → SUPPORTED; nla@38 (transported from 42) median +0.06 [0.03, 0.07] → SUPPORTED; skip_a@42 median cos(d_skip_a, d_cm) +0.09 [0.06, 0.12] n=30 → REFUTED; skip_a@38 (transported from 42) median +0.08 [0.06, 0.12] → REFUTED; skip_a@42 median cos(d_skip_a, d_probe) +0.06 [0.03, 0.07] n=30 → SUPPORTED; skip_a@38 (transported from 42) median +0.06 [0.04, 0.07] → SUPPORTED; (J-lens native-at-38: median cos(d_jlens38, d_cm) +0.07); (J-lens native-at-38: median cos(d_jlens38, d_probe) +0.04); (transport check: cos(J-lens transported, native at 38) median +0.88, range [+0.84, +0.91], 30 facts); jlens REPORT-FLIPPABLE: no defined verdicts (the dose never reached the 75% rate); jlens READER-BLIND: no defined verdicts (the dose never reached the 75% rate); nla REPORT-FLIPPABLE: no defined verdicts (the dose never reached the 75% rate); nla READER-BLIND: no defined verdicts (the dose never reached the 75% rate); olens (community) REPORT-FLIPPABLE: no defined verdicts (the dose never reached the 75% rate); olens (community) READER-BLIND: no defined verdicts (the dose never reached the 75% rate); skip_a REPORT-FLIPPABLE: no defined verdicts (the dose never reached the 75% rate); skip_a READER-BLIND: no defined verdicts (the dose never reached the 75% rate); SWAP add-on (WS4): pre-registered, NOT RUN |
| H6 | REFUTED | 3 | primary-site k-way rows on 15/15 R-B parents, 3/3 of the K ≥ 6 parents (n = the latter); jlens: no parent with two-way AUROC ≥ 0.85 (premise not met; 1 parents); nla: no parent with two-way AUROC ≥ 0.85 (premise not met; 3 parents); olens (community): no parent with two-way AUROC ≥ 0.85 (premise not met; 3 parents); skip_a: no parent with two-way AUROC ≥ 0.85 (premise not met; 3 parents); probe (k-class, pool, block 42, C = 1 as analyze.r6_kway) mean 0.646 [0.551, 0.760] over 8 cells → REFUTED; model (prompt-only k-way) mean 0.691 [0.581, 0.778] over 8 cells → REFUTED |
| H7 | UNDERPOWERED | 104 | votes as implemented: median split on every fact (deviation from §4.7, found by TH-2); gain (§1: consensus − best reader on all items) +3.69 pts [+0.51, +6.27] (clustered CI, the wider) → UNDERPOWERED; (§4.7 same-items form +0.00, ≡ 0 by construction); shared-wrong ratio 23.41 [6.45, 66.30] (clustered) → SUPPORTED; readers per fact 4 |
| H7 (§4.7-literal votes; the pre-registered specification) | REFUTED | 104 | votes per §4.7: sign of s_diff (two-sided), median (one-sided); gain (§1: consensus − best reader on all items) +5.20 pts [+2.45, +7.71] (clustered CI, the wider) → REFUTED; (§4.7 same-items form +0.00, ≡ 0 by construction); shared-wrong ratio 9.00 [5.43, 15.71] (clustered) → SUPPORTED; readers per fact 4 |
| R1b-noise (0.25) | REFUTED | 44 | n=2 +0.000 [0.000, 0.000] → REFUTED (DEGENERATE: Δ ≡ 0 on every fact); n=4 +0.025 [-0.001, 0.056] → UNDERPOWERED; n=8 -0.006 [-0.049, 0.028] → UNDERPOWERED; n=16 +0.018 [-0.014, 0.046] → UNDERPOWERED; n=32 +0.030 [-0.003, 0.063] → UNDERPOWERED; ΔAUC(512) +0.023 ≥ +0.01; SENSITIVITY (not the verdict): without the degenerate n → UNDERPOWERED |
| R1b-imbalance (0.1) | REFUTED | 44 | n=16 -0.010 [-0.032, 0.020] → UNDERPOWERED; n=32 -0.020 [-0.041, 0.001] → REFUTED |
| R1b-shift (chat→raw) | REFUTED | 44 | n=16 -0.016 [-0.040, 0.005] → REFUTED; n=32 -0.010 [-0.038, 0.016] → REFUTED; ΔAUC(512) -0.001 < +0.01 |
| H3 (secondary: §14 paraphrase key), all items | REFUTED | 99 | jlens@42 P(text) 0.49 [0.47, 0.51] → REFUTED; jlens@44 P(text) 0.49 [0.47, 0.51] → REFUTED; jlens@48 P(text) 0.48 [0.46, 0.50] → REFUTED; nla@42 P(text) 0.52 [0.50, 0.54] → REFUTED; olens (community)@42 P(text) 0.49 [0.47, 0.51] → REFUTED; olens (community)@44 P(text) 0.49 [0.47, 0.51] → REFUTED; olens (community)@48 P(text) 0.48 [0.47, 0.50] → REFUTED; skip_a@42 P(text) 0.48 [0.46, 0.50] → REFUTED; jlens@56 P(model) 0.52 [0.50, 0.53] → REFUTED; olens (community)@56 P(model) 0.52 [0.50, 0.54] → REFUTED; jlens probe lead: a TEXT→MODEL crossing exists on 1/99 facts — not testable; olens (community) probe lead: a TEXT→MODEL crossing exists on 0/99 facts — not testable; key-trained probe reaches 0.75 on 109/112 facts (median first layer 24) |
| H3 (secondary: §14 paraphrase key), stable items only | REFUTED | 93 | jlens@42 P(text) 0.47 [0.45, 0.49] → REFUTED; jlens@44 P(text) 0.47 [0.45, 0.49] → REFUTED; jlens@48 P(text) 0.47 [0.45, 0.49] → REFUTED; nla@42 P(text) 0.52 [0.50, 0.54] → REFUTED; olens (community)@42 P(text) 0.48 [0.46, 0.50] → REFUTED; olens (community)@44 P(text) 0.48 [0.46, 0.50] → REFUTED; olens (community)@48 P(text) 0.48 [0.46, 0.50] → REFUTED; skip_a@42 P(text) 0.46 [0.44, 0.48] → REFUTED; jlens@56 P(model) 0.53 [0.51, 0.55] → REFUTED; olens (community)@56 P(model) 0.54 [0.52, 0.56] → REFUTED; jlens probe lead: a TEXT→MODEL crossing exists on 1/93 facts — not testable; olens (community) probe lead: a TEXT→MODEL crossing exists on 1/93 facts — not testable; key-trained probe reaches 0.75 on 109/112 facts (median first layer 24) |

## CIs that exclude equivalence

R2 Δ (reader − prompt-only) with 95% CI entirely outside ±0.05: 0 above, 313 below, of 416 lens cells.
R7 per-fact consensus gain (§1 form) is a point estimate per fact (no per-fact CI); 65/104 facts > +2 pts.
