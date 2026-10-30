# Agam follow-ups 2 — summary (2026-10-14)

Qwen3.6-27B. All four tasks pre-registered in `projects/g_agreement/BRIEF_Z.md` ("Agam follow-ups 2") before any GPU
work. 1.83 of the 4 GPU-hour cap used; judge cost $1.92. Revised 2026-10-14 after an independent review (FVE by position, sensitivity framing, layer check). Details and figures in `results/g_agreement/f2/t1..t4/`.

**1. Prefill vs chat template (32 G1 states).** Reading at an answer-stem position does not rescue the readers; it
lowers their free-text hit rate. At the last token, judged hit rates for the chat template, template + answer prefill
and plain text + stem were: Oracle@44 50% [27, 74], 38% [16, 59] and 17% [5, 30]; NLA@42 45%, 36% and 15%. The
prefill contrast is −8 to −16 points, plain text −26 to −38. Ownership and mapping stay at 0–9% free-text hits in every
format while their log-odds wins stay at 81–100%. The pre-registered rule (+20 points, CI excluding 0) is not
triggered: the G1 "misses" are not a formatting artefact. Stems never named a
candidate; plain text often made the model open a thinking block instead of answering (7/16 ownership and mapping). A later check changes the reading: the J-lens was scored only at layers 42/44, where it names the holder or mapping answer 0% of the time, but at layers 56–60 it names them in every format, including the plain chat template (ownership up to 38%, mapping 50–75%, tense 50–100%). Many layer-42 misses look like a read-site (layer) issue, not a formatting one, consistent with the layer-52 crossing on errors.

**2. Norm-matched split edit (ownership, 64 states, layer 38, all positions).** Given the full edit's norm at every position, the J-space part flips the model 0/64 [0, 6%] at dose 1 (full edit 64/64) and 52% [40, 63] at dose 2, but the model does respond to it: its answer log-odds move +3.9 nats at dose 1 against +24.8 for the non-J part (which flips 100%). Readers follow the J-space part 78–91% already at dose 0.25 and stay there (follow is a sign test). So Agam's sensitivity point largely holds: the model under-weights the J-space part about 6× relative to the rest of the edit, while the readers weight both about equally; the gap in dose is at least 8×. Random directions at the same norm flip nothing and move readers 45–59%. Write-up change: replace "follows components the model ignores" with "the model under-weights components the readers weight fully".

**3. Probe vs readers across positions and layers (X1 bank, blocks 36–60 step 4).** 60 cells where a held-out probe
reads the answer at ≥ 80% while J-lens and Oracle are both at chance: ownership 45, tense 15, none in language or
mapping. They sit on the template and instruction tokens before the answer (`<think>`, `<|im_end|>`, `Reply`,
`name`), never at the last token, where the readers catch up (ownership layer 44: probe 100%, readers 91%; two tokens
earlier: probe 100%, readers 43–47%). Qualifier for the write-up: the probe reads a two-way label (holder
first-mentioned; past vs future) and is trained on 47 pairs, while the readers are scored zero-shot on names. These cells
are a first pass at Agam's request; the NLA is absent and the Oracle is scored by log-odds, not free text
(`f2/t3/t3_probe_only.csv`).

**4. Diagnostics.** (a) The NLA repo ships its reconstructor, so FVE was computed with the EasyNLA recipe on 1,192 NLA readouts. FVE depends on position: about 0.5–0.7 at the last token in every format, but −1.8 to −1.9 on the chat-template tokens before it, which look out of distribution for the reconstructor (the earlier "FVE ≈ 0" was an average over positions). Within one family at the same position FVE does not separate readouts that name the key from those that don't (AUROC 0.21–0.46 at the last token); the pooled AUROCs of 0.86–0.92 come from position and family differences. Only 18 readouts assert the wrong candidate. The Oracle's log-prob of its own asserted answer does not predict correctness either (AUROC 0.40 [0.25, 0.63]; margin 0.59 [0.37, 0.84]). Not yet run on the shared-mistake error states. (b) On the Y1 puzzles the
Oracle is not more confused on the model's errors: 1.35 vs 1.29 distinct answers per readout, Δ +0.05 [−0.06, +0.16].
From block 52 on it names the model's wrong answer about as often as on correct items (51% vs 43%) and the correct
answer less often (19% vs 43%, Δ −24 [−34, −13]), consistent with V1: late-layer readers report the model's choice.
No write-up change.
