# Text arm v2: the Qwen Oracle lens asked the dataset question, with and without the activation (BRIEF_R §13)

Branch `r/text-arm-v2`. Pre-registration `bca8402` (2026-10-19 02:15Z, before any v2 code or compute). Code `ff7ecbf`
(`r_bench/text_arm_v2.py`). Pod run 2026-10-19 02:21–04:01Z on n7nkfbiufayt1i. Analysis on the Mac, 17:32–17:37Z
(`e7cd814` + this commit). Tables: `text_arm_v2.csv` (pre-registered, 165 facts), `text_arm_v2_ex_ws3_defects.csv`
(sensitivity, 163), `text_arm_v2_gemma108.csv` (the 108 R-A facts Gemma keeps), `text_arm_v2_k1_states.csv` (K1).
Raw rows: `cache/g_agreement/r/text_arm/text_arm_v2_lo.jsonl` (90,582), `text_arm_v2_repro_lo.jsonl` (5,376), `states_v2/`.

## What was run

Both arms use Gemma's prompt form (`r_gemma/oracle.py`). The Oracle's activation-slot sentence comes first, then the dataset
question, then Gemma's `AO_FC_SUFFIX` with both candidates. The score is Σ log p(bare candidate), teacher-forced as the
assistant turn. The frozen `olens_s3d_rl600` adapter is used, with "layer 44" in the prompt.

- **(a) `olens_txtq`.** `<activation>{text}</activation>. {question} Answer with exactly one …`. No injection.
- **(b) `olens_txtq_act`.** `<activation>㈜</activation>.\n{text}\n{question} Answer with …`, with the frozen Oracle injection at
  ㈜ (alpha 16000 · h/‖h‖). h is the block-44 state at the chat assistant onset, or at the raw last text token.

Items: every test item of `items_r.json` (113 facts) and `items_rb.json` (55), 30,194 in all. Both files are sha-checked against
the R freeze. 165 facts enter the tables: §12's four AG News label-defect facts are excluded (97 is not in these banks).
Rule and BH as §12: per fact, item-paired bootstrap (2,000 resamples); BH within tag at each site; chat primary, raw secondary.

## Checks (all passed; decided before the contrasts were read)

| check | result |
|---|---|
| run completeness | `full exit 0`; 168/168 facts; 30,194 × 3 rows (6 forward rows per item); K2 file 168 × 16 × 2 = 5,376 rows |
| K0 smoke (4 items × 4 facts) | exit 0. The marker was found in every arm (b) prompt, with the prefix before it identical to the frozen carrier's (asserted per row). Not run as written: the "text replaced by nothing" carrier comparison (Deviation 1) |
| K1, re-captured vs frozen states | 336 fact × render cells. Median cosine 1.000 in both renders; lowest single item 0.996 → **pass** |
| K2, frozen bullet Oracle on the re-captured states vs the frozen rows | R-A chat / raw and ReaderBench chat / raw (n = 1,808 / 1,808 / 880 / 880). Median \|Δlo\| 0.000 nats, r = 1.000 → **pass** (the test-item states are bit-identical to the frozen ones: same capture batches) |
| Gemma join | Gemma's own means come out of `rg/*.csv` as in its report §5 / §9: −0.102 / −0.033 (Check 2) and −0.000 / −0.005 (§11 a) |

## Headline (negatives first)

1. **Gemma's prompt form does not suit the Qwen Oracle lens.** The adapter was trained to answer in `- ` bullets. Asked to answer
   with a bare option, it gives the better candidate a median log-prob of −37 nats in arm (a) (−40 / −34 in arm (b)), and no item
   reaches −5. The §12 bullet text arm sits at −21 nats. So the form is now like Gemma's, but the reader is used far off its output
   distribution, which Gemma's oracle is not. Every number below is a lo difference between two very unlikely strings.
2. **With the question, the text-only Oracle is a worse text classifier, not a better one.** Arm (a) has median AUROC 0.592,
   against 0.616 for §12's bullet text arm. Mean (a) − §12 = −0.033 [−0.051, −0.018], with 19 facts up and 49 down (item CI).
   COMPUTED stays at chance (0.508). Asking the question did not make COMPUTED askable, contrary to the §13 forecast. Gemma's
   text-only oracle reaches 0.929 on the same R-A facts.
3. **Against that weak text arm, the activation looks better than on Gemma.**
   - C-A (frozen Oracle on the activation − arm a), chat: READ FROM THE STATE on 63 facts, TEXT SUFFICES on 40, NOT
     DISTINGUISHED on 62. Mean Δ +0.041 [+0.013, +0.070].
   - C-A, raw: 69 / 17 / 79, mean +0.056 [+0.035, +0.078].
   - On Gemma the same contrast is −0.102 (chat) and −0.033 (raw).
   - Read 3 as "Qwen's text-only Oracle is poor at this", not as "Qwen's Oracle reads more from the state than Gemma's".
4. **C-B, the like-for-like contrast (same prompt with vs without the activation).**
   - Raw: STATE ADDS on 53 facts, STATE COSTS on 13, NOT DISTINGUISHED on 99. Mean +0.048 [+0.029, +0.069].
   - Chat: 55 / 42 / 68, mean +0.020 [−0.008, +0.050].
   - On Gemma, text + activation = text (mean Δ −0.000 chat, −0.005 raw).
   - So on Qwen, injecting the state into the question prompt changes the answer, and at the raw last token it helps on a third of
     the facts. At the chat onset it helps as often as it hurts. It hurts mostly on SURFACE (16 STATE COSTS of 33, mean −0.097).

## C-A: activation (frozen Oracle, block 44) − arm (a), by tag (`text_arm_v2.csv`, 165 facts)

Chat (primary):

| tag | facts | AUROC act | AUROC text+q | mean Δ [fact CI] | state | text suffices | n.d. |
|---|---|---|---|---|---|---|---|
| COMPUTED | 23 | 0.744 | 0.508 | +0.223 [+0.152, +0.294] | 17 | 1 | 5 |
| CONTEXT | 3 | 0.749 | 0.515 | +0.082 [−0.233, +0.245] | 2 | 1 | 0 |
| COUNT | 3 | 0.310 | 0.518 | −0.198 [−0.225, −0.160] | 0 | 3 | 0 |
| FORM | 12 | 0.634 | 0.542 | +0.072 [−0.006, +0.153] | 7 | 1 | 4 |
| INTERNAL | 4 | 0.760 | 0.574 | +0.216 [+0.050, +0.382] | 2 | 0 | 2 |
| KHOP | 7 | 0.920 | 0.958 | −0.040 [−0.120, +0.039] | 1 | 3 | 3 |
| KNOWLEDGE | 28 | 0.722 | 0.641 | +0.055 [+0.005, +0.109] | 11 | 3 | 14 |
| META | 9 | 0.694 | 0.707 | −0.011 [−0.062, +0.040] | 1 | 1 | 7 |
| PASSAGE-KNOWLEDGE | 9 | 0.593 | 0.645 | −0.041 [−0.099, +0.037] | 1 | 2 | 6 |
| SURFACE | 33 | 0.729 | 0.841 | −0.046 [−0.102, +0.012] | 6 | 16 | 11 |
| SYNTAX | 6 | 0.640 | 0.463 | +0.164 [−0.011, +0.322] | 4 | 1 | 1 |
| TOPIC | 28 | 0.627 | 0.579 | +0.001 [−0.060, +0.059] | 11 | 8 | 9 |
| **ALL** | **165** | 0.701 | 0.592 | **+0.041 [+0.013, +0.070]** | **63** | **40** | **62** |

Raw (secondary): ALL +0.056 [+0.035, +0.078], 69 / 17 / 79. STATE on KNOWLEDGE 15/28, SURFACE 15/33, COMPUTED 11/23,
KHOP 6/7 and PASSAGE-KNOWLEDGE 5/9. TOPIC has 7 / 4 / 17. Descriptive layers, mean Δ chat / raw: 42 +0.033 / +0.059,
48 +0.046 / +0.057, 52 +0.067 / +0.054, 56 +0.071 / +0.048.

## C-B: arm (b) − arm (a), by tag

| tag | facts | chat: mean Δ [fact CI] | adds / costs / n.d. | raw: mean Δ [fact CI] | adds / costs / n.d. |
|---|---|---|---|---|---|
| COMPUTED | 23 | +0.197 [+0.117, +0.279] | 14 / 1 / 8 | +0.132 [+0.069, +0.201] | 12 / 0 / 11 |
| CONTEXT | 3 | +0.165 [+0.090, +0.216] | 2 / 0 / 1 | −0.069 [−0.267, +0.056] | 0 / 1 / 2 |
| COUNT | 3 | −0.146 [−0.231, +0.003] | 0 / 2 / 1 | −0.063 [−0.121, −0.033] | 0 / 1 / 2 |
| FORM | 12 | +0.135 [+0.056, +0.222] | 8 / 0 / 4 | +0.095 [−0.002, +0.189] | 6 / 1 / 5 |
| INTERNAL | 4 | +0.205 [+0.049, +0.361] | 2 / 0 / 2 | +0.178 [+0.010, +0.353] | 2 / 0 / 2 |
| KHOP | 7 | −0.044 [−0.135, +0.043] | 2 / 4 / 1 | +0.005 [−0.025, +0.041] | 1 / 1 / 5 |
| KNOWLEDGE | 28 | +0.013 [−0.024, +0.051] | 7 / 4 / 17 | +0.050 [+0.025, +0.074] | 8 / 1 / 19 |
| META | 9 | −0.008 [−0.111, +0.098] | 4 / 3 / 2 | −0.057 [−0.188, +0.067] | 3 / 3 / 3 |
| PASSAGE-KNOWLEDGE | 9 | −0.016 [−0.062, +0.037] | 1 / 1 / 7 | +0.057 [+0.011, +0.107] | 2 / 0 / 7 |
| SURFACE | 33 | −0.097 [−0.150, −0.040] | 4 / 16 / 13 | +0.029 [+0.003, +0.057] | 11 / 2 / 20 |
| SYNTAX | 6 | +0.035 [−0.232, +0.308] | 2 / 1 / 3 | +0.074 [−0.029, +0.195] | 2 / 0 / 4 |
| TOPIC | 28 | −0.019 [−0.079, +0.039] | 9 / 10 / 9 | +0.020 [−0.017, +0.061] | 6 / 3 / 19 |
| **ALL** | **165** | **+0.020 [−0.008, +0.050]** | **55 / 42 / 68** | **+0.048 [+0.029, +0.069]** | **53 / 13 / 99** |

By bank, C-B raw adds / costs / n.d.: R-A 35 / 6 / 69; ReaderBench 18 / 7 / 30.

## Gemma next to Qwen, the 108 R-A facts both keep (descriptive; mean Δ per tag, `text_arm_v2_gemma108.csv`)

| tag | site | facts | Gemma act − text | Qwen C-A | Gemma text+act − text | Qwen C-B |
|---|---|---|---|---|---|---|
| COMPUTED | chat | 17 | −0.107 | +0.234 | +0.008 | +0.177 |
| FORM | chat | 6 | −0.069 | +0.097 | −0.001 | +0.101 |
| KNOWLEDGE | chat | 21 | −0.150 | +0.086 | −0.012 | +0.016 |
| META | chat | 6 | +0.023 | +0.004 | +0.006 | −0.017 |
| PASSAGE-KNOWLEDGE | chat | 9 | −0.081 | −0.041 | +0.001 | −0.016 |
| SURFACE | chat | 28 | −0.129 | −0.060 | +0.002 | −0.126 |
| TOPIC | chat | 21 | −0.068 | −0.013 | −0.002 | −0.022 |
| **ALL** | chat | 108 | **−0.102** | **+0.038** | **−0.000** | **−0.003** |
| COMPUTED | raw | 17 | −0.054 | +0.103 | −0.006 | +0.097 |
| FORM | raw | 6 | −0.071 | +0.038 | +0.010 | +0.046 |
| KNOWLEDGE | raw | 21 | −0.023 | +0.098 | −0.003 | +0.064 |
| META | raw | 6 | −0.028 | +0.027 | −0.013 | −0.033 |
| PASSAGE-KNOWLEDGE | raw | 9 | +0.067 | +0.075 | +0.018 | +0.057 |
| SURFACE | raw | 28 | −0.027 | +0.074 | −0.018 | +0.036 |
| TOPIC | raw | 21 | −0.069 | −0.024 | −0.002 | +0.004 |
| **ALL** | raw | 108 | **−0.033** | **+0.060** | **−0.005** | **+0.043** |

Signs agree only where both models favour the state: PASSAGE-KNOWLEDGE at the raw site. Elsewhere Gemma's oracle prefers the
text and ignores the injected state when the text is present. Qwen's Oracle lens is a weak reader of text in this form, and it is
moved by the injected state, mostly for the better at the raw site. Two residual differences remain:
- C-A's activation side is still the frozen concepts-prompt reader (Gemma's activation arm had the question).
- The answer form is native for Gemma's oracle and not for Qwen's (headline 1).

C-B has neither problem on the activation side, so it is the cleanest cross-model number: Gemma 0.000 / −0.005,
Qwen −0.003 / +0.043 (chat / raw, 108 facts).

## Sensitivity without WS3's 101_disease_class defects (`text_arm_v2_ex_ws3_defects.csv`, 163 facts)

No verdict count changes outside TOPIC. ALL, C-A chat 63 / 40 / 60, raw 69 / 18 / 76; C-B chat 55 / 42 / 66, raw 53 / 13 / 97.
Means move by ≤ 0.002.

## What it means

- §12's caveat stands on Qwen, in a narrower form. A Qwen Oracle-lens AUROC is not explained by a text classifier inside the
  adapter, because the adapter, asked from text, is a poor classifier in either prompt form (0.62 bullets, 0.59 question). That
  differs from Gemma, whose oracle reads the text better than the state.
- The fair cross-model statement is C-B. Gemma's oracle ignores the injected state when the text is in the prompt. Qwen's Oracle
  lens does not ignore it, and the state helps at the raw last token: +0.048, 53 of 165 facts, against 13 where it costs.
- Not shown, and still open:
  - an activation-only arm in the question form, which would make C-A like for like;
  - a bullet-form version of (a) and (b) (`- {candidate}` as the answer, the adapter's native output), which would separate the
    prompt from the answer format. Neither is pre-registered.

## Compute

| pod | span (UTC) | billed h | $ (3.99/h) | what |
|---|---|---|---|---|
| n7nkfbiufayt1i (mats-minis-rT) | 02:16:36 → 04:15:58 | 1.989 | 7.94 | smoke + full run (GPU busy ≈ 1.62 h: loads 2.0 min, run 95.0 min) + 15-min pull window; self-stopped by id |
| ak1hnbxk8ppdw5 (mats-minis-h100) | 05:31:23 → 17:05:18 | 11.565 | 46.15 | resumed by this stream to pull the outputs; the session was interrupted and the pod idled until another chat stopped it. **Waste, owned by this stream** |
| ak1hnbxk8ppdw5 (mats-minis-h100) | 17:29:10 → 17:31:48 | 0.044 | 0.18 | the pull. Only a Mac-side stop by id (50-min timer) plus a manual podStop by id at 17:31:48Z guarded it. The on-pod guard and the rsync ran on another stream's pod, P8 di7p8t2c28fwec (the SSH endpoint came from the wrong listing entry; see §13 Deviation 6). PODS.md rule not met on this pod |
| **total** | | **13.598** | **54.26** | §13 budgeted 1.3–1.6 GPU-h with a 3 GPU-h hard stop on the run. The run stayed inside it; billed uptime overran by 10.6 h because of the idle pull pod |
