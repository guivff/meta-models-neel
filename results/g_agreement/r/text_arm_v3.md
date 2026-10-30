# Text arm v3: is text arm v2's activation gain content or format? (BRIEF_R §13 note "text arm v3")

Pre-registration `6da9746` (19:40Z, before any v3 code or compute). Code `d992e38` and `db3e54c` (the smoke fix; Deviation 1). Pod
d6lq9yaejceqxv, 20:11:52 → 21:39:28Z. Analysis on the Mac at 21:4xZ. Tables: `text_arm_v3.csv` (pre-registered, 165 facts),
`text_arm_v3_ex_ws3_defects.csv` (163), `text_arm_v3_gemma108.csv` (descriptive). Rows:
`cache/g_agreement/r/text_arm/text_arm_v3_lo.jsonl`.

## What was run

v2's arm (b) has the question, the item's text and an activation injected at the slot, with bare-candidate scoring at block 44,
chat and raw. v3 runs it unchanged except for the injected vector:
- **text + deranged activation** (`olens_txtq_shuf`): item i gets item π(i)'s own state. π is the frozen shuffled control's
  derangement; the smoke rows match the frozen `state_item_id` 16 / 16, and the derangement was checked on all 60,388 rows on the
  Mac.
- **text + mean activation** (`olens_txtq_mean`): the fact's mean test state.

Contrasts, per fact, with item-paired bootstrap CIs:
- Δ_R = real − deranged
- Δ_D = deranged − text
- Δ_RM = real − mean
- Δ_M = mean − text
- Δ_B = real − text is v2's gain.

## Completeness

| arm | facts | rows | status |
|---|---|---|---|
| text + deranged activation | 168 / 168 | 60,388 (30,194 × chat, raw) | complete; all rules inferential |
| text + mean activation | 20 / 168 on the Mac | 8,000 | cut by the 70-min timeout (exit 124). More facts are on the volume (Deviation 3). The 20 are the first R-A facts in bank order (headlines, true / false sets, hist_fig, wikidata gender); mean contrasts are **descriptive** |

## Headline (deranged control, the pre-registered primary)

**v2's gain is content, not format.** A wrong item's activation pulls the Oracle away from the right answer. A right item's
activation pulls it toward the right answer.

| site | facts | v2 gain (real − text) | deranged − text | **real − deranged** | per fact: adds information / deranged better / n.d. | reading |
|---|---|---|---|---|---|---|
| chat | 165 | +0.020 [−0.008, +0.048] | −0.102 [−0.127, −0.077] | **+0.122 [+0.096, +0.147]** | **86 / 10 / 69** | adds information; control opposite |
| raw | 165 | +0.048 [+0.029, +0.069] | −0.116 [−0.139, −0.091] | **+0.164 [+0.139, +0.188]** | **101 / 5 / 59** | adds information; control opposite |

Median AUROC, chat: text + real 0.666, text + deranged 0.534, text alone 0.592 (raw 0.671 / 0.524 / 0.592). Injecting another
item's state takes the text-only Oracle most of the way to chance. So when the text and the injected state disagree, the reader
follows the state. Under the pre-registered three-way reading this is "no format effect". The deranged arm moves opposite to v2's
gain (`CONTROL_OPPOSITE`): the injected vector's content, not the injection itself, drives the answer. v2's small net gain
(+0.02 / +0.05) is that content effect, real minus wrong (+0.12 / +0.16), measured against a text arm that the state also overrides.

By bank, real − deranged: R-A chat +0.107 (53 / 5 / 52), raw +0.157 (68 / 2 / 40); ReaderBench chat +0.152 (33 / 5 / 17),
raw +0.178 (33 / 3 / 19).

## By tag and site (`text_arm_v3.csv`; mean Δ with a fact-bootstrap 95 % CI; per-fact verdicts adds / deranged better / n.d.)

| tag | site | facts | v2 gain | deranged − text | real − deranged | adds info | reading | per fact |
|---|---|---|---|---|---|---|---|---|
| COMPUTED | chat | 23 | +0.197 [+0.117, +0.279] | +0.015 [−0.019, +0.057] | +0.182 [+0.106, +0.251] | yes | no format effect | 14 / 1 / 8 |
| CONTEXT | chat | 3 | +0.165 [+0.090, +0.216] | −0.008 [−0.087, +0.060] | +0.173 [+0.156, +0.186] | yes | no format effect | 3 / 0 / 0 |
| COUNT | chat | 3 | −0.146 [−0.231, +0.003] | −0.036 [−0.082, +0.029] | −0.110 [−0.175, −0.026] | no | no format effect | 0 / 2 / 1 |
| FORM | chat | 12 | +0.135 [+0.056, +0.217] | −0.027 [−0.095, +0.034] | +0.163 [+0.083, +0.240] | yes | no format effect | 7 / 0 / 5 |
| INTERNAL | chat | 4 | +0.205 [+0.049, +0.361] | +0.036 [−0.054, +0.142] | +0.168 [+0.033, +0.316] | yes | no format effect | 2 / 0 / 2 |
| KHOP | chat | 7 | −0.044 [−0.133, +0.045] | −0.121 [−0.211, −0.030] | +0.077 [+0.054, +0.101] | yes | control opposite | 5 / 0 / 2 |
| KNOWLEDGE | chat | 28 | +0.013 [−0.023, +0.051] | −0.101 [−0.148, −0.054] | +0.115 [+0.070, +0.164] | yes | control opposite | 12 / 0 / 16 |
| META | chat | 9 | −0.008 [−0.112, +0.097] | −0.195 [−0.313, −0.092] | +0.187 [+0.059, +0.320] | yes | control opposite | 5 / 0 / 4 |
| PASSAGE-KNOWLEDGE | chat | 9 | −0.016 [−0.062, +0.036] | −0.113 [−0.165, −0.064] | +0.097 [+0.051, +0.139] | yes | control opposite | 6 / 0 / 3 |
| SURFACE | chat | 33 | −0.097 [−0.152, −0.044] | −0.207 [−0.264, −0.151] | +0.111 [+0.054, +0.160] | yes | control opposite | 19 / 1 / 13 |
| SYNTAX | chat | 6 | +0.035 [−0.249, +0.292] | +0.016 [−0.201, +0.240] | +0.019 [−0.106, +0.160] | no | no format effect | 2 / 2 / 2 |
| TOPIC | chat | 28 | −0.019 [−0.083, +0.042] | −0.127 [−0.194, −0.065] | +0.108 [+0.030, +0.190] | yes | control opposite | 11 / 4 / 13 |
| **ALL** | chat | 165 | +0.020 [−0.008, +0.048] | −0.102 [−0.127, −0.077] | **+0.122 [+0.096, +0.147]** | **yes** | control opposite | 86 / 10 / 69 |
| COMPUTED | raw | 23 | +0.132 [+0.069, +0.201] | −0.004 [−0.034, +0.037] | +0.136 [+0.081, +0.191] | yes | no format effect | 12 / 1 / 10 |
| CONTEXT | raw | 3 | −0.069 [−0.267, +0.056] | −0.075 [−0.275, +0.032] | +0.005 [−0.015, +0.023] | no | no format effect | 0 / 0 / 3 |
| COUNT | raw | 3 | −0.063 [−0.121, −0.033] | −0.041 [−0.076, −0.010] | −0.022 [−0.111, +0.043] | no | **format effect** (a loss) | 0 / 0 / 3 |
| FORM | raw | 12 | +0.095 [+0.002, +0.191] | −0.040 [−0.139, +0.044] | +0.135 [+0.038, +0.244] | yes | no format effect | 5 / 0 / 7 |
| INTERNAL | raw | 4 | +0.178 [+0.010, +0.353] | +0.036 [−0.032, +0.111] | +0.142 [+0.014, +0.269] | yes | no format effect | 2 / 0 / 2 |
| KHOP | raw | 7 | +0.005 [−0.026, +0.040] | −0.276 [−0.299, −0.247] | +0.281 [+0.236, +0.321] | yes | control opposite | 7 / 0 / 0 |
| KNOWLEDGE | raw | 28 | +0.050 [+0.026, +0.075] | −0.129 [−0.176, −0.079] | +0.179 [+0.134, +0.225] | yes | control opposite | 21 / 0 / 7 |
| META | raw | 9 | −0.057 [−0.201, +0.066] | −0.195 [−0.304, −0.097] | +0.139 [−0.011, +0.293] | no | **format effect** (a loss) | 5 / 1 / 3 |
| PASSAGE-KNOWLEDGE | raw | 9 | +0.057 [+0.012, +0.106] | −0.109 [−0.183, −0.037] | +0.166 [+0.068, +0.269] | yes | control opposite | 5 / 0 / 4 |
| SURFACE | raw | 33 | +0.029 [+0.001, +0.058] | −0.213 [−0.271, −0.154] | +0.242 [+0.187, +0.294] | yes | control opposite | 28 / 1 / 4 |
| SYNTAX | raw | 6 | +0.074 [−0.029, +0.195] | +0.046 [−0.057, +0.188] | +0.029 [−0.144, +0.210] | no | no format effect | 2 / 1 / 3 |
| TOPIC | raw | 28 | +0.020 [−0.017, +0.065] | −0.117 [−0.175, −0.064] | +0.138 [+0.083, +0.200] | yes | control opposite | 14 / 1 / 13 |
| **ALL** | raw | 165 | +0.048 [+0.029, +0.069] | −0.116 [−0.139, −0.091] | **+0.164 [+0.139, +0.188]** | **yes** | control opposite | 101 / 5 / 59 |

The only "format effect" cells are losses: raw COUNT and raw META, 3 and 9 facts. There, any injected vector lowers the score
about as much as the real one. Where v2's gain was positive and large (COMPUTED, FORM, INTERNAL, CONTEXT at chat), the deranged arm
sits near the text arm (Δ_D ≈ 0) and real − deranged ≈ the v2 gain: the gain is content. Where v2's gain was ≈ 0 or negative
(SURFACE, TOPIC, KNOWLEDGE, PASSAGE-KNOWLEDGE, KHOP, META), the state is still read: real − deranged is +0.08 … +0.28. But a wrong
state costs more than the real one helps relative to the text, so the net v2 effect cancels.

**Sensitivity.** Without WS3's 101_disease_class defects (163 facts): chat +0.124 [+0.098, +0.149], 86 / 10 / 67; raw +0.166
[+0.139, +0.192], 101 / 5 / 57. On Gemma's 108 R-A facts (descriptive): chat real − deranged +0.109 [+0.081, +0.136], deranged − text
−0.112; raw +0.160 [+0.133, +0.186] and −0.116.

## Mean-activation control (descriptive: 20 R-A facts only)

| site | facts | v2 gain on these facts | mean − text | real − mean | per fact real > mean / mean > real / n.d. |
|---|---|---|---|---|---|
| chat | 20 | +0.061 [−0.049, +0.166] | −0.073 [−0.162, +0.010] | +0.134 [+0.010, +0.235] | 16 / 2 / 2 |
| raw | 20 | +0.061 [+0.013, +0.110] | −0.027 [−0.093, +0.036] | +0.089 [+0.045, +0.140] | 8 / 1 / 11 |

The direction agrees with the deranged control: a fact-generic state does not reproduce the gain, and the item's own state does.
Ten of the 20 facts are COMPUTED and the set is not representative, so no rule is applied. Guiv decided on 2026-10-19T22:32Z not to pull the remaining mean-arm rows from the volume, so this table is final.

## What it means

- Text arm v2 left open whether its C-B gain was a format effect. It is not. The Qwen Oracle lens reads the item-specific content
  of the injected block-44 state, at both sites and in almost every tag: 86 (chat) and 101 (raw) of 165 facts pass the
  pre-registered per-fact rule, against 10 and 5 the other way.
- The text-only arm is not a ceiling the state has to beat: the state overrides it. A wrong state drags the text-only AUROC from
  0.59 to 0.53. Gemma's oracle is the opposite (its text + activation = text), so on this point the two released oracles behave
  in opposite ways.
- Caveats:
  - The answer form (bare candidate) is still off the Qwen adapter's output distribution (v2 headline 1).
  - The mean control is partial.
  - The result is about this reader at block 44 with this prompt.

## Compute

| pod | span (UTC) | billed h | $ | note |
|---|---|---|---|---|
| d6lq9yaejceqxv (mats-minis-txt) | 20:11:52 → 21:39:28 | 1.460 | 5.83 | Inside the 1.5 h cap. Guards armed by the first SSH command (id check ok; `ws2_hardstop` 5400 s armed at 20:12:41Z; `ws2_watchdog` armed). Chain: smoke 1 failed safely, smoke 2 OK at 20:19:27Z, full run 20:19 → 21:29:27Z (timeout, exit 124), pull window, explicit stop by id at 21:39:28Z |
| (ak1hnbxk8ppdw5, 19:45–19:51Z) | — | 0 | — | Inside chat 6's span, booked to WS4 (Integrator); no command ran |
