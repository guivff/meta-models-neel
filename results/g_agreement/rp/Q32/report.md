# BRIEF_RP — Qwen3-32B with Karvonen et al.'s activation oracle (pair Q32): report

Pre-registered in `projects/r_panel/BRIEF_RP.md`; rules BRIEF_RG's; readings in §12. Target `Qwen/Qwen3-32B` @ `9216db57`; oracle
`adamkarvonen/checkpoints_cls_latentqa_past_lens_Qwen3-32B` @ `08c733f3` (**standard**). Pod rp32 `t7c1clx51x3z4h` (1× H200, K6), chain
18:33Z → 05:20Z; native pool rows 05:24–05:30Z. 108 facts analysed (seven label-defect facts excluded).

## Primary site (block 32, chat, assistant onset)
| clause | estimate [wider 95 % CI] | verdict |
|---|---|---|
| H1 quiver ΔAUC_AO (n ≥ 16) | n=16 -0.016 [-0.032, -0.004]; n=32 -0.016 [-0.030, -0.007]; n=64 -0.047 [-0.063, -0.032]; n=512 -0.002 [-0.005, -0.001] | **SUPPORTED**: never adds value |
| H1 median n* ≤ 8 | 9.9 [7.0, 26.8] | UNDERPOWERED |
| H2 BH exceedances, text tags | 1: 153_it_tick_Administrative rights (oracle 0.50 vs prompt-only 0.30) | REFUTED |
| H2 KNOWLEDGE ≥ 0.8 × probe | 0.43 [0.24, 0.63] | UNDERPOWERED |
| H7 consensus gain (BRIEF_R §1 form) | +0.71 [-0.67, +1.90] pts | SUPPORTED |
| H7 shared-wrong ratio ≥ 1.5 | 9.47 [3.33, 25.72] | SUPPORTED |

Shuffled controls: mean 0.498, SD 0.041, 77 % in band (the n = 200 reading of §12).

## The oracle given the text (C-A) and text + activation
AO chat: state 0.718 vs text 0.946. READ FROM THE STATE 3, TEXT SUFFICES 84, not distinguished 21. Raw: 7 / 52 / 49. Text + activation adds
nothing: ao_textact chat +0.000 [-0.006, +0.007]; ao_textact raw -0.002 [-0.012, +0.006]; ao_yn_textact chat -0.002 [-0.005, +0.002]; ao_yn_textact raw -0.001 [-0.010, +0.007].

## Training-native site (§3.6): the rule fires, offset 7 again
Pool choice: offset 7 (0.798) over 8 (0.787). Test: **+0.083 [+0.059, +0.103]** over the onset. Restated at offset 7 (`native_k7/`):
- quiver: n=16 **+0.049 [+0.019, +0.072]** (REFUTED: adds value), n=32 +0.030 [+0.010, +0.049] (UNDERPOWERED);
- median n* 38.0 [23.3, 62.7];
- KNOWLEDGE ≥ 0.8 × probe: 0.67 (UNDERPOWERED);
- exceedances over prompt-only: 153_it_tick_Administrative rights [TOPIC] (0.46 vs 0.30), 26_headline_isfrontpage [FORM] (0.62 vs 0.49), 56_wikidatasex_or_gender [PASSAGE-KNOWLEDGE] (0.92 vs 0.75), 94_ai_gen [FORM] (0.75 vs 0.64). These are surprise-list cells; the fresh-pool re-score needs a GPU and was not run.
- C-A at offset 7: state 0.833 vs text 0.946, Δ −0.080 [−0.112, −0.048] (headline table).

Rule-10 note: the native pool rows (05:24Z, after rule 10) carry pod, git sha and timestamps but no per-process run_id; the code predates the rule.
