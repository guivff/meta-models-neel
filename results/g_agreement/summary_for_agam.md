# Activation readers report what is in the vector, not what the model uses

Guiv Farmanfarmaian and Suraj · Qwen3.6-27B · updated 2026-10-14 evening (supersedes the 2026-10-12 version, kept as
`summary_for_agam_v3_2026-10-12.md`). Full record: `writeup.md`; pre-registrations `BRIEF_X/Y/Z.md`, `PREREG_WV.md`.

**Question.** Neel asked whether interpretability readers can be cross-referenced, and whether their agreement can
serve as ground truth. We grade each reader against facts established without readers: a fact built into the prompt,
a fact planted into the activation and confirmed by the model's own answer flipping, a fact present only in the
model's context, or the model's own behaviour. Readers: J-lens, Oracle lens, NLA, a skip lens, linear probes. All are
scored by their own log-odds, not by parsing free text.

![headline](z/fig_headline_readers_vs_model.png)

**Headline.** We edit the hidden state at layer 38 along pre-registered directions and ask two questions: does the
model's answer flip, and does each reader's score move toward the edit. Wherever the model's answer depends on the
edit, the readers follow. But they also follow components the model under-weights, and at block 42 none of them follows the
one direction a probe uses:

| edit at layer 38 (64 states per cell, Phase W) | model answer flips | lens readers move toward the edit |
|---|---|---|
| class-mean direction of the swap | 94–100% | 66–100% |
| top-384 J-space component, ownership | 0% | 80–94% |
| remainder outside J-space, ownership | 0% | 67–88% |
| probe-weight direction (the probe follows it 96%) | 0–5% | 45–56%, inside the random band (Oracle on-grid at block 44: 66% in ownership, above it) |
| full swap, all positions (reference) | 95–100% | 70–98% |

A reader's score tells you what is linearly present at its read site along class-mean-like directions, not whether
the model will act on it, and not what a trained probe reads. Agreement between readers inherits the same limit.

Part of this is sensitivity. Rescaled to the full edit's norm, the J-space component moves the model's answer log-odds
+3.9 nats at dose 1 (the rest of the edit +24.8) and flips half the answers only at dose 2, while the readers follow it
78–91% from dose 0.25. The model under-weights that component about 6× relative to the rest; the readers weight both
about equally.

**Supporting results**
- **Readers can report facts the prompt does not contain (new, confirmed).** With a fact placed only in a system-turn
  preamble and an identical visible prompt, every reader family reports who owns the object: Oracle 94%, NLA 94%,
  J-lens 88%, skip lens 81% on 48 pre-registered pairs (prompt-only baseline 50%, model ceiling 100%). This is the
  positive instance the programme lacked: a reader reporting something a prompt-reading baseline cannot.
- **"Readers miss the model's errors" is a layer statement.** On 297 puzzles the model gets wrong, a probe reads the
  upcoming wrong answer from layer 48 (79%); the J-lens and Oracle at layers 42–48 do not (41–57%), but at layer 52
  and beyond they do (77–86%), four layers behind the probe. The J-lens at 48 prefers the correct answer the model
  then abandons (+17 pts).
- **What is in the vector is narrower than two-way scores suggested.** The same readers that win 85–94% of two-candidate
  mapping items score 12–21% with eight candidates (chance 12.5%), and none recovers a count of 1–99 (exact 1–3%,
  no rank correlation) where the model's own next-token distribution does (ρ 0.83).
- **A probe reads the answer where the readers cannot (new).** Mapping every prompt position at layers 36–60 finds
  60 cells where a held-out probe reads the answer at ≥ 80% and J-lens and Oracle are both at chance: 45 in ownership,
  15 in tense, on the template and instruction tokens just before the answer (`<think>`, `<|im_end|>`, `Reply`). At the
  last token the readers catch up (ownership, layer 44: probe 100%, readers 91%; two tokens earlier: 100% vs 43–47%).
  The probe reads a two-way label and is trained on 47 pairs; the readers are scored zero-shot on names by log-odds,
  and the NLA is not yet in this map.
- **Free-text misses on bindings are a read-layer issue.** With the plain chat template and no stem, the Oracle names
  the person or mapping answer in free text 86% [67, 98] of the time at layer 56, against 12% at layer 44, and gets
  both versions of each pair right, so it reads the state. Answer stems do not help: "The answer is" lowers hit rates,
  and a stem naming a candidate ("The answer, in Spanish, is") is simply copied (named the wrong candidate 59–95% of the
  time when the stem said it).
- **The newline feature stays unreadable at new read sites.** With `<|im_end|>` appended, a counting instruction, or
  both, no reader separates long-line from short-line reads (48–65%), while a probe does (85–97%). With the instruction
  plus `<|im_end|>` the Oracle mentions line length in half its readouts, equally for long and short lines.
- **The readers behave as one instrument.** They share the probe-direction blind spot, follow the same unused components,
  and on the model's errors pick the same wrong answer twice as often as independent readers would (ratio 2.05).
  Majorities are right only where each reader is already right.
- **Consistency filtering (Michael Kenney's recipe), re-analysed on his data.** Recurrence across samples sorts claims about the
  input well (AUROC 0.90) but not confidently repeated wrong internal claims (0.56); a sensitivity signal separates
  exactly those (0.83), post-hoc and on a proxy. Our judged claim precision on this model is low for both free-text
  readers (NLA 27%, Oracle 40% on input claims).

**Caveats.** Synthetic prompts with rule-based keys; one model; last-token reads except where stated; 64 states per
steering cell; Oracle numbers are at block 42, off its training grid, but a pre-registered rerun at block 44 keeps the
J-space and remainder results (91% and 94% follow at 0% model flips) and changes two ownership cells (class-mean
77 → 92%, probe direction 52 → 66%); free-text sampling for the claim study did not run on the pod, so claim precision rests on 32+8 states.

**Next, and why**
1. Test whether the 60 probe-only positions are causal: edit along the probe direction only at `<think>` / `Reply`
   and see if the model's answer flips. If it does, the model uses information no reader reports.
2. Re-score every earlier two-way bank with the full candidate set. If the eight-way result generalises, all native
   reader numbers need an "among two candidates" qualifier.
3. Fit readers at layers 52–56 on the error set and compare with the probe there: tests "lag, not blindness" directly.
4. Replicate the two unplanned V7 effects as primaries: readers do better when the fact is in the system turn, and when
   the holder is the second-mentioned name. Then a preamble that contradicts world knowledge, to separate "reads the
   context" from "reads the model's belief".

**Questions for you**
- Should a reader be judged at its training site, or wherever the fact is load-bearing (here four layers later)?
- Is "follows an edit the model ignores" a reader failure, or the correct report of a vector the model happens not
  to use?
- Does a reader reporting a system-turn fact count as the kind of "reads what the prompt does not say" you had in
  mind, or does the fact have to be one the model inferred rather than was told?
