# When do meta-models reveal more than the prompt?

*A working hypothesis, with "mostly" and "so far" load-bearing. The question underneath: when, if ever, do activation readers reveal model-private state beyond reconstructing the prompt?*

Guiv Farmanfarmaian and Suraj Prasad · MATS 12, Neel Nanda stream · narrative v7, 30 October 2026, matching `activation_readers_MATS_final.pptx` (24 core + 15 appendix slides).

Subject: Qwen3.6-27B (64 decoder blocks, width 5120). Readers: Oracle Lens (default block 44) and NLA (block 42). Sources: `guivff/activation-readers` (branch `r/blindspot`; the deck's numbers were read at `c60fa970`, a pre-seal commit) and Suraj's `Jarus77/mats-nla-workspace` at `4d43ecb2`. Every number below is in `CLAIM_LEDGER.md` with its file path.

Status words: **registered** (rule written before the data; MET / NOT MET / NOT EVALUABLE), **descriptive** or **exploratory**, **post hoc**. **Reviewed by R-x** means an agent session re-ran the analysis from sealed outputs; it is not a human replication. **Author result** means Suraj's own analysis. The one human check is Guiv's E71 coding.

---

## TL;DR

What an activation reader says is usually what a reader of the prompt would say, answered from the backbone's own knowledge. On WorkspaceBench the NLA scores 0.47 and a text-only Qwen with the same instruction scores 0.46 (Suraj, exp 06). When Qwen's own answer changes with the wording, the Oracle gives the same answer for both wordings on 11 of 12 evaluable pairs (E140). Structural state is decodable inside the reader and carried in its text, and almost never stated (E100, E113, Suraj's exp 22/25). The silence is there before RL and survives 800 RL steps; targeted supervision can make the NLA name structure with little measured reconstruction cost, but transfer is weak (exp 29, 30). Under a large upstream push, restoring one clean token undoes the push only from block 52 on, and the reader follows from there (E126, E109). Without any push, the final token matters mostly at block 60 and early readouts rarely name the previous holder (E133, E137). Several registered rules failed and one result was withdrawn after we found our own bug. The falsifier is a powered benchmark of verified model-private state; building it, and an objective that pays only for what the text cannot predict, is the research phase.

---

## Opening

**1 · Title.** When do meta-models reveal more than the prompt? Working hypothesis: two activation readers mostly tell you what the prompt says. We started by asking whether two readers agreeing makes a readout more reliable: on natural banks agreement raises precision to 0.94 but covers only 23% of items (E94), and both can omit the same property; that moved the question to what readouts reveal beyond the prompt. Three measurements, kept apart throughout: **decodable** (held-out probe, AUROC), **causal here** (patch at one token and block, normalised effect R), **stated** (blind judge, k of n with missing shown).

**2 · Apparatus.** Block L output = `hidden_states[L+1]`. Oracle: marker input embedding ← 16000·h/‖h‖. NLA: h₁ + ‖h₁‖·h/‖h‖ after its block 1, RL-trained so a critic can rebuild h. Read token: assistant onset for chat banks; raw final " by" (token 539) for the transfer chains; the fact bank reads its final "is". Never the first generated token.

**3 · What the readers write** (G1 pilot, both readers at block 42, verbatim, selected). "Opposite of 'hot' in Spanish": both say *Frío*. "Elif carries the rope and Jonas carries the lantern. Who carries the lantern?": the Oracle writes *Alice / John*, the NLA says the answer is *"Alex"* to *"Who sits first."* Both readouts look like a prompt of this kind, rebuilt and answered; that is a description of the outputs, not yet a mechanism. Block 42 is off the Oracle's trained grid.

**4 · Three questions, three units.** Judge vs Guiv's blind codes (E71): κ 0.68 [0.49, 0.85] on 63 comparable readouts, registered bar 0.70, NOT MET; 8/40 false YES (doing counted as saying), 4/23 false NO. Language-like rows are unreliable; the nesting, indent and cue rows were not in the audit.

## Part 1 · What readers say

**5 · Benchmark (Suraj, exp 06, author).** 400 items: NLA@42 0.47 [0.42, 0.52]; text-only Qwen, same instruction, no activation, 0.46 [0.41, 0.51]; McNemar p = 0.75 (80 vs 75 discordant). Oracle@42 0.40. For reference, not matched: the Oracle's published protocol (any of 11 layers) 0.65; text-only best of 3 samples 0.69; any of 8 text-only samples 0.96, missing 0 of the NLA's 187 hits. *Does not show* that the reader ignores the activation, or equivalence.

**6 · Paraphrase test (E140, descriptive pre-stated readings, R-5).** 300 pairs screened (time cap; 600 planned) → 58 where Qwen's two answers differ → 12 evaluable at block 60. Of 12: 1 follows Qwen, 0.08 [0.01, 0.35]; 11 give one answer for both, 0.92 [0.65, 0.99]. Tracking reading NOT MET; same-answer reading MET. 7/116 readouts missing, 15 multi-value; counting those, 1/24 and 11/24. Large interventions are followed (whole swap 63/84, E138R; strong push 84/84 at block 52, E109); appendix A4 keeps the three apart. Exploratory (§248A, R-2): on 199 questions Qwen gets wrong, the Oracle states Qwen's wrong answer 0.32 vs an outside model's 0.24, the truth 0.17 vs 0.61.

**7 · Whole-activation swap (E100, R-PC MET 5/5, R-Q).** Oracle@44, 84 items per row, S = (donor-only − recipient-only)/kept: format plan 0.95, fact 0.74, tense 0.65, language plan 0.62; nesting 0.01, indent −0.05, page digit 0.00. Post hoc census: nesting and indent readouts state no value (64/84, 78/84); the page digit partly cancels (10 donor, 10 recipient, 7 both).

**8 · Probe inside the reader (E113, R-IN1 MET, R-4).** First generated token (always token ID 12): nesting ≥ 0.999 and page digit 1.00 at every reader block 0–63; at the injected marker 1.00 is trivial. The same rows are stated in 5/84, 4/84 and 27/84 of E100's readouts. Decodable, not shown to be used.

**9 · A prompt-stated cue (E85, E120; R-2).** Probe in Qwen 1.00; inside the reader 128/128 at 1.00; readout words 0.988 (a genre contrast 0.987); named 0/176 at block 44 (24 missing) and 0/350 at 52/60 (50 missing). Registered R-E1 (genre vs situation) NOT MET because every mention rate is 0. Asking directly: NOT EVALUABLE. Prompt-stated cues, never evaluation awareness.

## Part 2 · Why: reconstruction (Suraj)

**10 · Carried, not stated (exp 25, 22; author).** On public code and markdown files at layer 42, the critic's rebuild from the readout still separates the state (NLA 0.93–1.00, Oracle 0.84–0.97 on four of five rows, 0.51 on call argument), while the Oracle states nothing (≤ 0.01) and the NLA 0.01–0.25 (code language control 0.70). Oracle readouts are out of distribution for the NLA's critic.

**11 · S16 (author; run by Guiv's agent on Suraj's pipeline).** Swap the part of the activation the Oracle's text does not rebuild (h − R_OL): the NLA follows the donor on table column 0.98, parenthesis 0.87, list index 0.98 (donor AUROC, 200 items); language follows the other part (0.92). Guiv's matched E7 on other banks: 0.39 / 0.57 / 0.51; E27 could not assign the gap. A hypothesis about mechanism, not a result.

**12 · Exp 28 (author).** The statement shift measures how far a statement moves the critic's reconstructed activation along the class direction — a geometric proxy, not the training reward. The rule "statement shift ≥ 0.30 ⇒ stated" is withdrawn: seven rows are stated ≥ 0.25 with shift < 0.17. Spearman 0.40 over 47 rows, 0.28 (p 0.08) over 41 structural rows. The shift carries information (beats the type label by 314 AIC) but mainly separates the language rows.

**13 · Exp 29 (author).** FVE on Python strings 0.18 (warm start) → 0.53 (RL 100) → 0.59 (RL 800). Judged structural statements, mean of 7 rows, 0.11 → 0.12, flat; text-only Qwen 0.30. Code language 0.55 → 0.77. The drop happens before RL; text-only differs in both input and style, so the cause is not identified.

**14 · Exp 30 (author, registered P1–P5).** Supervised statements on six properties: named / correct of 32 — Python string 0.59 / 0.47, call argument 0.50 / 0.41, JSON depth 0.72 / 0.69; markdown 0.46–0.58 correct when named; JS string (untrained) 0.53 / 0.31; LaTeX 0.03. Base and control name nothing. Gate FVE 0.504 / 0.512 / 0.507. P1 partly met: within 0.02 of control yes, within 0.03 of 0.761 no (reference from exp 00, unreconciled). P2–P4 NOT MET; P5 not scorable. At random positions the model over-applies "inside a string" (0.40 when true, 0.26 when false; strict regex).

## Part 3 · Causal: where in depth

**15 · Method (E104/E126).** Add α·‖d‖·d̂ at block 40 on the eight positions before the read token (d: class-mean difference on 84 dev items; α 8 = 2.23× the median block-40 norm; a random direction of that size flips 42/84 pair preferences, the real one 84/84). Restore the clean read token at one block ℓ. R = (Δ_steered − Δ_restored)/(Δ_steered − Δ_clean).

**16 · Result (E126 R-MED1 MET, R-Q).** Fact row R: 0.013, 0.057, 0.663 [0.51, 0.80], 0.876, 0.871 at 44–60; earlier-token control ≤ 0.11, random ≈ 0. The reader: S −0.52 at 44, +1.00 at 52 and 60 (E109). Qwen's free text states the new answer 43/84 (E131, NOT MET). The language row is non-monotone (R 0.29 already at 44).

**17 · E135 (descriptive) and §248C (exploratory).** Block-44 reader states the old answer: easy items 4/42 under the push (α 6) vs 24/41 with no push; resistant items 40/40 vs 42/42. On resistant items the "stale" readout is there without the push. Association only.

**18–19 · Unsteered chains (E133, E137; R-Q, R-4).** Swap only the final " by" activation with the opposite twin's. Twin-swap R, E137 (42 pairs): 0.006, 0.039, 0.268, 0.363, 0.747; E133 (50 pairs): 0.011, 0.045, 0.264, 0.320, 0.744. At block 44 the Oracle names the current holder 13/79, the previous 3/79, another name 35/79, nobody 28/79; at 60 the current holder 25/76. Registered staleness (previous ≥ 0.30) and the later-site rule (R ≥ 0.50 at 52 or 56) NOT MET. A holder probe scores 0.978 at 44, but over 8 of 10 classes; the registered twin probe is at chance.

## Part 4 · Audit and next

**20 · Three corrections.** E138 withdrawn: the judge received the recipient's answer split into characters, so the recipient control could not fail; rejudged once (E138R): donor 63/84, recipient 0/84; a post-output correction (R-5). E71: κ 0.68, bar not met. S16 vs E7 unreconciled.

**21 · Hypothesis.** A readout is the prompt rebuilt and answered; it reports Qwen's own state once that is large at the read token. Registered and met: E100, E126, E140's same-answer reading. Read afterwards: exp 06, E113 with E100 counts, E135, E137, exp 30 (statements cost little reconstruction, but the full P1 is not met). Would falsify or change it: a powered benchmark where a reader tracks verified private state and beats a same-backbone text-only baseline; block-44 restoration ≥ 0.5 on a fresh unsteered bank; the exact training reward ranking true above false statements.

**22 · Experiment 1 (first priority).** Without a test the prompt text cannot pass, a better objective cannot be evaluated. A benchmark of model-private state: wording-dependent answers, consistently wrong facts, wrong intermediates; state verified by repeated sampling and a read-token patch; identity × state design; baselines at matched coverage (same backbone on the decoded text; k-matched samples; a probe on the answer logit). Falsifier: the readout follows identity, not state, or a powered interval excludes a useful edge.

**23 · Experiment 2 (second).** Step 0: score true, false, neutral and exhibiting statements under the exact training reward (E139's proxy: true − neutral slightly positive for fact, table, nesting; every true − false interval includes zero). Then ≥ 3 seeds per arm: reconstruction only; plus a verified-statement reward; reconstruction scored only on what a text-only model misses. Endpoint: correct statements, false claims and FVE together.

**24 · Close.** Decodable, causal here and stated are different. A reader faithful to the text is not yet faithful to the model.

---

## Wording rules

"answer preference" for 84/84; "says the new answer" only for 43/84. S is a signed score. "twin swap" for E133/E137, "restoration" only for E126. "prompt-stated cue", never evaluation awareness. "carried, not stated", never "cannot see". "same answer for both wordings", never "re-solves" as fact. Suraj's results are his, by name; ours are "matched" only where we ran them. Withdrawn E138 values and the exp 19 threshold rule never appear. Missing counts beside every judged rate.

## Corrections relative to v6

E137's probe needs the 8-of-10-class caveat, and early readouts mostly name another person or nobody (not "silent"). E135 ran at α 6, and its no-push bars are §248C. Exp 28's shift does beat the type label. E7's rows are 0.39 / 0.57 / 0.51 (table, parenthesis, list). E122's −0.14 is a formal-vs-informal contrast, not the cue direction. E114 is descriptive. Exp 06 had no registered prediction. The monitoring results: the "+6 / +7" figure comes from a different 100-prompt bank, and block 52's 84/84 holds on the fact row only. The quotes "Ignore earlier movements" and "signaling a language identification task" are not verbatim in the repository and were removed.
