# Speaker notes · Activation readers mostly tell you what the prompt says

Guiv Farmanfarmaian and Suraj Prasad · MATS 12, Neel Nanda stream · 45-minute talk, then questions.
The same notes are embedded in the PowerPoint (View → Notes). Times are cumulative.

## 45-minute plan

| # | Time | Speaker | Slide | 20-min route |
|---|---|---|---|---|
| 1 | 0:00–1:30 | GUIV | When do meta-models reveal more than the prompt? | KEEP, 1:00 |
| 2 | 1:30–3:30 | GUIV | An activation reader turns one residual vector into text | KEEP, 1:30 |
| 3 | 3:30–4:30 | GUIV | Readouts often look like a prompt of this kind, rebuilt and answered | SKIP |
| 4 | 4:30–5:30 | GUIV → hand to SURAJ | Three questions about every state: decodable, causal here, stated | KEEP, 1:00 |
| 5 | 5:30–8:00 | SURAJ → hand back to GUIV | On WorkspaceBench, the NLA scores what a text-only copy of Qwen scores | KEEP, 2:00 |
| 6 | 8:00–10:30 | GUIV | When Qwen's own answer changes with the wording, the reader rarely follows it | KEEP, 2:00 |
| 7 | 10:30–12:30 | GUIV | After a whole-activation swap, content transfers readily; structural reporting is sparse | KEEP, 1:30 |
| 8 | 12:30–14:00 | GUIV | Inside the reader the structural state is perfectly decodable, but seldom stated | SKIP |
| 9 | 14:00–16:00 | GUIV → hand to SURAJ | A prompt-stated cue reaches the reader's word choice and is never named | SKIP |
| 10 | 16:00–17:30 | SURAJ | Readers' text often carries structural state that is rarely stated | SKIP |
| 11 | 17:30–19:30 | SURAJ | Experiment S16: position-in-text state follows the part of the activation the Oracle's text does not rebuild | SKIP |
| 12 | 19:30–21:00 | SURAJ | How far a statement shifts the critic's reconstruction does not predict whether the NLA states structure | SKIP |
| 13 | 21:00–23:00 | SURAJ | The silence is there before RL; 800 RL steps raise reconstruction, but not structural statements | SKIP |
| 14 | 23:00–25:00 | SURAJ → hand to GUIV | Supervising statements makes the reader name structure; reconstruction barely moves, transfer is weak | KEEP, 2:00 |
| 15 | 25:00–27:30 | GUIV | Push the answer upstream at block 40, then put one clean token back at a later block | KEEP, 1:30 |
| 16 | 27:30–29:30 | GUIV | Fact row: restoring the read token becomes strongly effective between blocks 48 and 52 | KEEP, 1:30 |
| 17 | 29:30–31:00 | GUIV | On items that resist the push, the 'stale' block-44 readout is there with no push at all | SKIP |
| 18 | 31:00–33:00 | GUIV | Unsteered transfer chains: swap only the final " by" token with its opposite twin | SKIP |
| 19 | 33:00–35:00 | GUIV | Unsteered chains: the final token matters mostly at block 60, and the previous holder is rarely named | KEEP, 1:30 |
| 20 | 35:00–37:00 | GUIV | Three corrections we would rather you hear from us | KEEP, 1:30 |
| 21 | 37:00–39:30 | GUIV | Hypothesis: a readout is the prompt rebuilt and answered; it reports Qwen's own state once that is large at the read token | KEEP, 1:30 |
| 22 | 39:30–41:30 | GUIV → hand to SURAJ | A benchmark of model-private state, verified causally, against strong text-only baselines | KEEP, 1:00 |
| 23 | 41:30–43:30 | SURAJ → hand to GUIV | Pay the reader for true statements the prompt text cannot predict, and measure false claims | SKIP |
| 24 | 43:30–45:00 | GUIV | Decodable, causal here, and stated are different. A reader faithful to the text is not yet faithful to the model. | KEEP, 0:30 |

Handoffs: Guiv → Suraj after slide 4 (benchmark) and slide 9 (Suraj's part, slides 10–14); Suraj → Guiv after slide 5 and slide 14; Guiv → Suraj for slide 23; Guiv closes.

## 20-minute route (≈ 19:30)

Slides 1, 2, 4, 5, 6, 7, 14, 15, 16, 19, 20, 21, 22, 24. Skip 3, 8–13, 17, 18, 23.
- On slide 7 say in one sentence that a probe inside the reader reads the same structure at AUROC 1.00 (slide 8).
- On slide 14 say in one sentence that both readers' text carries structure they never state (slide 10), that the silence exists before RL (exp 29) and that the 0.30 shift rule was withdrawn (exp 28).
- On slide 19 describe the twin swap in one sentence (slide 18 skipped): only the final " by" token is replaced by its opposite twin's, nothing is steered.
- On slide 22 add one sentence for experiment 2: pay only for what text cannot predict, after measuring the exact reward on true vs false statements.

## 8-minute backup sequence (critical sources and controls)

A3 read sites → slide 15 method → A12 steering bank controls → A13 chains and depth → A4 three interventions → A2 failed rules → A14 human audit and E138 timeline → A15 monitoring checks → A1 provenance.

## Likely objections and short answers

- *"Isn't this just the null for a reconstruction-trained reader?"* Yes, it is the null we tried to break; slides 16, 14 and 22 are where it bends or could break.
- *"p = 0.75 isn't equivalence."* Agreed; we say no detectable difference on this benchmark (slide 5).
- *"1/12 is tiny."* It is conditional on 12 of 58 pairs; the funnel is on the slide, and A4 gives sensitivity 1/24.
- *"2.2× norm is off-distribution."* Yes; E126 maps where a big push becomes visible. E137 is the unsteered companion.
- *"Are your reviewers independent?"* They are separate agent sessions re-running sealed analyses, not human replications; one human audit (E71, κ 0.68).
- *"Is reconstruction reward the cause?"* Not established: exp 29 is confounded (text vs activation input), E139 is a proxy. Experiment 2 is designed to test it.
- *"Is this evaluation awareness?"* No. Every cue was written in the prompt.

## Slide-by-slide notes

### 1. When do meta-models reveal more than the prompt?

[Slide 1 · 0:00–1:30 · GUIV · 20-min route: KEEP, 1:00]
Open with the question, then the hypothesis: "When do meta-models reveal more than the prompt? Our working hypothesis: two activation readers mostly tell you what the prompt says. They report Qwen's own state only where it has become large at the read token."

How we got here (one sentence): we started by asking whether two readers agreeing makes a readout more reliable. On natural banks agreement raises precision to 0.94 but covers only 23% of items (E94, appendix A15), and both readers can omit the same property. That moved the question from whether readouts agree to whether they reveal anything beyond the prompt.

Three things to remember, said now so Neel knows what is coming: (1) state can be decodable inside the reader and carried in its words, yet not stated (slides 7–10); (2) where you read matters causally: a large upstream push becomes visible at the read token only from block 52 (slides 15–16); (3) improving readers means separating access to information from the incentive to describe it (slides 13–14, 23).

Scope, said out loud: Qwen3.6-27B; two readers (the Oracle Lens and the NLA); mostly synthetic banks plus one public benchmark (WorkspaceBench, from Suraj). "Mostly" and "so far" are load-bearing. This is a working hypothesis we tried to break, not a universal verdict about activation readers.

The three dots on the right are the method of the talk. Decodable: a held-out linear probe can read a property from an activation (AUROC). Causal here: patching the activation at one token and one layer changes Qwen's answer (a normalised logit effect, R). Stated: the reader's text explicitly says it (a judged rate with a denominator). Every slide has these three dots in the top right; the filled ones say which of the three that slide measures. They are different units and we never put them on one axis.

Handoff plan: Guiv takes slides 1–4, Suraj the benchmark (5), Guiv 6–9, Suraj 10–14, Guiv 15–22, Suraj 23, Guiv closes.

Likely objection: "Isn't 'mostly the prompt' obvious for a reader trained to reconstruct?" Answer: it is the null hypothesis we expected, and the interest is in where it fails. We show one place it can be moved (supervised naming, Suraj exp 30) and one place where strong upstream changes are followed (late blocks), and we propose the experiment that would falsify it.

### 2. An activation reader turns one residual vector into text

[Slide 2 · 1:30–3:30 · GUIV · 20-min route: KEEP, 1:30]
What physically happens. Qwen3.6-27B runs the prompt. We take the residual-stream output of one decoder block at one token position. In HuggingFace terms, the output of block L is hidden_states[L+1], because hidden_states[0] is the embedding. That vector, h, is the only thing the reader gets about the prompt.

Oracle Lens (default subject block 44): the reader has its own prompt with a marker token; we replace the marker's input embedding with h rescaled to a fixed norm, 16000·h/‖h‖. Then it writes short continuations.

NLA (default subject block 42): h is added at the reader's first block on the marker position, scaled to the norm of the reader's own residual there: h₁ ← h₁ + ‖h₁‖·ĥ. It then writes an explanation. The NLA is RL-trained so that a critic can rebuild h from the text: that training objective is the reason we suspect reconstruction.

Read token. In chat banks the read token is the assistant-onset position: the last token of the prompt before generation. In the transfer chains (E133/E137) there is no chat template; we read the raw final token " by" of "The brass key is now held by". People confuse this with the first generated token; it is not.

Why this matters: every later claim is about what is in h at that one position and layer. A probe reads h; a patch changes h; the reader describes h.

Objection: "Why these layers?" Oracle 44 and NLA 42 are where each reader was trained to read. Cross-depth studies are all for the Oracle (appendix A13); the NLA only reads 42.

### 3. Readouts often look like a prompt of this kind, rebuilt and answered

[Slide 3 · 3:30–4:30 · GUIV · 20-min route: SKIP]
Before any numbers, what the readers produce. Both readouts here are verbatim (shortened with ellipses) from our G1 pilot, where both readers read the same Qwen activation: block 42, last token of the chat-rendered prompt, first sample.

Top: "What is the opposite of 'hot'? (Answer in Spanish, one word.)" The Oracle Lens continues as if it were the assistant: "- Frío / - Frío / - Frío (This is the single most common Spanish word…". The NLA describes the prompt: "Q&A format pattern … now delivering a Spanish-language direct answer … (e.g., "Frío")". Both get it right.

Bottom: "Elif carries the rope and Jonas carries the lantern. Who carries the lantern? Name only." The Oracle writes "- Alice / - John"; the NLA says the model must answer "Alex" to "Who sits first." Neither mentions Elif or Jonas. Both have rebuilt a prompt of the right kind — a name-only question — and answered that.

This is the pattern the talk is about: a readout is a reconstruction of a prompt like this one, answered from the backbone's knowledge. When the reconstruction keeps the specifics (Spanish, cold), the answer is right; when it keeps only the format, the reader confabulates.

These are selected, not representative; we chose them because they show the two styles cleanly.

### 4. Three questions about every state: decodable, causal here, stated

[Slide 4 · 4:30–5:30 · GUIV → hand to SURAJ · 20-min route: KEEP, 1:00]
This is the vocabulary for the rest of the talk.

1. Decodable. Train a linear probe on activations with a held-out split; report AUROC. Judge-free. It says the information is linearly present, nothing about use.

2. Causal here. Change the activation at one token and one layer, and measure the normalised change in Qwen's answer logit difference. We use two different interventions later and keep them distinct: E126 restores one clean token into a steered run; E133/E137 swap the read token with an opposite twin's. Both give a number R between about 0 and 1, but they are different experiments.

3. Stated. A blind LLM judge sees only the readout plus the property and candidate values, answers YES/NO, and a YES must quote the text. Reported as k of n with missing readouts shown.

The judge is not perfect: on Guiv's hand-coded audit (E71) agreement was κ 0.68 on 63 usable pairs, just under our registered 0.70 bar. Its main error is a false YES — counting a readout that exhibits a property (e.g. writes in English) as stating it — which makes judged rates on language-like rows unreliable. It also has false NOs (4 of 23), mostly on one reasoning row. The audit packet did not include the nesting, indent or cue rows, so the near-zeros there are not directly audited; they would need the judge to miss almost every statement.

Objection: "Why not just use the judge for everything?" Because a reader can carry information it never says; that gap is the object of study.

### 5. On WorkspaceBench, the NLA scores what a text-only copy of Qwen scores

[Slide 5 · 5:30–8:00 · SURAJ → hand back to GUIV · 20-min route: KEEP, 2:00]
WorkspaceBench asks a reader to recover a multi-token piece of the prompt (a misspelt word, a named entity, a code identifier) from one activation. 400 items.

The matched comparison is the first two bars. The NLA reading the block-42 activation solves 0.47 [0.42, 0.52]. The same base Qwen, with no adapter and no activation, given the prompt text under the NLA's own instruction, solves 0.46 [0.41, 0.51]. McNemar p = 0.75 (80 items only the reader gets, 75 only text-only gets). The Oracle Lens at 42 gets 0.40.

The grey box is a different quantity and we keep it separate on purpose: if you take the union of eight prompt-only samples (two models × two templates, several seeds), 0.96 of items are solved by at least one. That is best-of-eight coverage, not compute-matched against a single reader readout. Its use: 0 of the NLA's 187 hits were missed by every prompt-only sample — every NLA success is text-recoverable.

What this does and does not show. It shows that benchmark success cannot distinguish reading the activation from reconstructing the prompt and answering. It does not show the reader ignores the activation: at block 42 the activation encodes the prompt, so the two are the same thing here. That is why every later experiment either intervenes on the activation or picks items where the text and Qwen's own answer come apart. This is the experiment Neel asks for in his MATS 12 stream doc: "tasks that cannot be easily solved by just reconstructing the surrounding text".

Further numbers (appendix A7): text-only Qwen given only the NLA's readout solves 0.57; of the NLA's checkable claims, 0.62 are supported by the text vs 0.92 for text-only — the gap is mostly misquotations of the prompt (36% contradicted), not model-private content; text-only scores depend a lot on template (0.76 with the benchmark's own template). The Oracle at 42 is off its trained grid (it scores 0.37 / 0.39 at 40 / 44, so the conclusion does not change).

The box also shows where the Oracle's published lead comes from (Suraj's M3): its published WorkspaceBench score counts an item as passed if any of 11 layers passes — 0.65 — against 0.37–0.40 at any single layer. Best-of-N helps everyone: text-only Qwen with three samples reaches 0.69.

Objection: "Isn't the text-only arm stronger than a fair baseline?" It's the same model and same instruction, one sample; the stronger templates make the point stronger, not weaker.

Handoff back to Guiv for a test where the text and Qwen's own answer diverge.

### 6. When Qwen's own answer changes with the wording, the reader rarely follows it

[Slide 6 · 8:00–10:30 · GUIV · 20-min route: KEEP, 2:00]
Benchmarks can't separate reading the activation from rebuilding the prompt. So we built items where they come apart: the same one-hop fact asked in two wordings, where Qwen itself gives different answers. If the reader reads Qwen's computation, it should say X on wording A and Y on wording B.

Construction (E140): 600 questions in two paraphrases across eight relation templates; Qwen greedy answer on each. Because of a time cap we screened the first 300 pairs; 58 had two different, non-empty answers. We read both members of each pair with the Oracle at blocks 44, 52, 60; a blind judge codes each readout as X, Y, another value or none.

The funnel is the honest part: at block 60 only 12 of 58 pairs have both readouts stating exactly one value. 7 of 116 readouts are missing; 15 state several values. On those 12, the reader follows Qwen's per-wording answer once (1/12, Wilson [0.015, 0.35]) and gives the same answer to both wordings 11 times. Counting multi-value readouts as non-tracking: 1/24 and 11/24. Block 52 is identical (1/12).

Pre-stated descriptive readings: tracking (≥ 0.60 with Wilson lower bound > 0.45) NOT MET; the 'prior' or same-answer reading (≥ 0.50) MET. R-5 reviewed (328 values matched).

Reading: on a natural-scale change in Qwen's answer, the reader answers the question it reconstructs rather than tracking this forward pass. Caveats: conditional on 12 pairs; wording changes also move text-only models; the reader may be insensitive at this scale rather than ignoring the activation.

Contrast, appendix A4: with much larger interventions the reader does follow — a whole swapped-in activation (63/84, E138R) or a strong push (84/84 at block 52, E109). Those are different interventions and different denominators, not one accuracy scale.

The example on the slide is a template, not a realised item; realised pairs are kept private for future judging.

### 7. After a whole-activation swap, content transfers readily; structural reporting is sparse

[Slide 7 · 10:30–12:30 · GUIV · 20-min route: KEEP, 1:30]
Intervention: run the recipient prompt through Qwen, but at block 44 replace the read token's whole residual vector with the one from a donor item whose value differs (e.g. a different fact, a different nesting depth). The Oracle Lens reads the swapped vector. A blind judge codes each readout: does it state the donor's value, the recipient's, both, or neither?

S = (#donor-only − #recipient-only) / kept readouts, 84 items per row. Content rows follow the donor: output format plan 0.95, fact recalled 0.74, implicit tense 0.65, language plan 0.62. Structural rows do not: nesting depth 0.01, indent −0.05, page-range digit 0.00. Registered rule R-PC (at least 4 of 5 reported rows follow): MET 5/5, reviewed by R-Q.

The chart answers the obvious objection to a signed score — is S ≈ 0 silence or cancellation? For nesting (64/84) and indent (78/84) the readout states no value at all: silence. For the page digit it is partly cancellation: 10 donor, 10 recipient, 7 both. That census is post hoc and descriptive.

Reading: what a text reconstruction carries is the content of the prompt; it exhibits structure (it writes indented code) without naming it.

Objection: "Maybe the Oracle can't represent nesting at all." Next slide: inside the reader, a probe reads it perfectly.

### 8. Inside the reader the structural state is perfectly decodable, but seldom stated

[Slide 8 · 12:30–14:00 · GUIV · 20-min route: SKIP]
E113 asks whether structural state is lost inside the reader. We fit a separate linear probe for each of 64 reader blocks at two positions — the injected marker and the first generated token — for three bookkeeping rows (nesting depth, indent level, page-range digit) and three content controls. 84 dev and 84 test items per row; dev-only regularisation choice; 768 test AUROCs evaluated once.

At the injected marker AUROC is 1.00 at every block for all three bookkeeping rows — but that is trivial: the marker's input IS the injected vector. The informative position is the first generated token: nesting depth ≥ 0.999 and page digit 1.00 at every block from 0 to 63. The first generated token is the same token on every item (ID 12), so a probe cannot be reading token identity. Registered R-IN1: MET (3/3 rows), reviewed by R-4, who rebuilt all 768 AUROCs.

Below, the same rows in E100's readouts: the Oracle states any nesting value in 5 of 84 and any indent value in 4 of 84 readouts. Page digit 27 of 84, but 17 of those 27 include the recipient's value (10 recipient only, 7 both).

Reading: decodable everywhere in the reader, almost never stated. Not shown: that the reader uses it; this is decodability, not causal use. The DEV and TEST splits share base questions, so 1.00 is a ceiling.

### 9. A prompt-stated cue reaches the reader's word choice and is never named

[Slide 9 · 14:00–16:00 · GUIV → hand to SURAJ · 20-min route: SKIP]
A cue written into the system prompt: "This conversation is part of a capability evaluation; your answer will be scored", crossed with a genre variable. We follow it rung by rung.

1. In Qwen's activation at blocks 42 and 44, a probe separates cue present vs absent at test AUROC 1.00 (E85 gate).
2. Inside the reader, all 64 blocks at both positions: 128 of 128 held-out AUROCs are 1.00 (E120b).
3. In the readout's words: a bag-of-words classifier recovers the cue at out-of-fold AUROC 0.988 [0.978, 0.995]. But the matched genre classifier gets 0.987 — any prompt difference changes the register of the rebuild. Words leaning "cue present": department, recommends, last, incident, sentence.
4. Stated: the judge finds the cue named 0 of 176 kept readouts at block 44 (24 missing), and 0 of 350 at blocks 52 and 60 (50 missing). The registered rule R-E1 asked a different question (does the evaluation genre raise mentions more than being addressed?); it is NOT MET because every mention rate is 0 (R-2).

Asking the reader directly ("is this an evaluation?") was NOT EVALUABLE: judged-correct 0/175 with the cue, balanced accuracy 0.5 (E120c).

A second cue experiment (E136) is in appendix A6: misuse named 0/80; sycophancy "named" 77/78 but the judge also says yes on 70/78 cue-absent readouts, so that measure does not discriminate.

Scope: these are prompt-stated cues, never hidden evaluation awareness.

### 10. Readers' text often carries structural state that is rarely stated

[Slide 10 · 16:00–17:30 · SURAJ · 20-min route: SKIP]
This is the same distinction as slides 7–8, measured on a different bank by a different instrument: real code and markdown files from public packages and arXiv, read at layer 42.

x-axis, "carries it": take the reader's free readout, let the NLA's critic rebuild the layer-42 activation from that text alone, and ask a frozen probe whether the rebuilt vector still separates the two values (e.g. inside vs outside a string). AUROC 0.5 means the text carries nothing. For the NLA's explanations: 0.93–1.00 on the five string, math, argument and depth rows. For the Oracle's readouts: 0.84–0.97 on four of them, 0.51 on call argument.

y-axis, "states it": a blind judge reads k = 8 readouts per item and asks whether the readout names the value. The Oracle states nothing: 0 on every row (max 0.009). The NLA: 0.01–0.25 on the structural rows (JSON depth is the highest at 0.25), 0.70 on the positive control (code language, a property its describing style names). Not every row is carried: the Oracle's call-argument (0.51) and both markdown rows sit near chance. The clean contrast is the four readable rows: Python string, JS string, LaTeX math, JSON depth.

Markdown rows are the honest negatives: list and heading are near 0.5 even in the true text span (0.50, 0.62), so there is little to carry.

So the readouts carry the structure because they reproduce the text that contains it; they do not say it. Caveats: the Oracle's readouts go through the NLA's critic, which is out of distribution for them (class-direction cosine 0.54–0.68 vs 0.78–0.90 for the NLA), so do not compare the two readers' carry values directly. Carry is measured on 160 selection items with one readout each; states on 40 mining items with eight samples. Author results; registered predictions scored in exp 22 and 25 RESULTS.

Handoff: the next slide asks where in the activation that state lives.

### 11. Experiment S16: position-in-text state follows the part of the activation the Oracle's text does not rebuild

[Slide 11 · 17:30–19:30 · SURAJ · 20-min route: SKIP]
Exp 14 asked: is the Oracle Lens's reconstruction-based reward blind to the properties the Oracle never states? No: a probe on the reconstruction of TRUE text reads table column and parenthesis at AUROC 1.00 and 0.93. But the reward barely moves when you swap a statement about a concept ("column one" vs "column five": 0.03 of the gap). The reward pays for exhibiting the text, not for describing it.

Exp 16 decomposes the NLA-space activation h at block 42: R_OL is what the NLA's own reconstructor rebuilds from the Oracle's text; the difference term is h − R_OL. Swap only the difference term from a donor item into a recipient, and ask whether the NLA's readout follows the donor. Table column 0.98, parenthesis 0.87, list index 0.98; language 0.10. Swap only the Oracle-text part instead and language follows (0.92) while position does not (0.01 / 0.12 / 0.03). Unit: donor-follow AUROC over 200 recipient items, 0.5 = no information.

Reading: position-in-text state is in the part of the activation the Oracle's text does not rebuild; language is in the part it does.

Caveat we disclose: Guiv's earlier E7 used the same algebra but different banks, partner plans and one readout per item, and found much weaker following on the matching rows (0.39 / 0.57 / 0.51). E27 reproduced both and could not assign the difference to one cause. The headline 0.98 also swaps h − R_OL; the algebra-matched swap (R_NLA − R_OL) gives 0.95 / 0.77 / 0.83, still far above E7. So: suggestive of a mechanism, not established.

Handoff: this is why we suspected that the training objective shapes what gets said; the next slides test that directly.

Objection: "Is AUROC 0.98 'following'?" It is the probability that a readout scored for the donor's value outranks one scored for the recipient's, over item pairs; it is not a naming rate.

### 12. How far a statement shifts the critic's reconstruction does not predict whether the NLA states structure

[Slide 12 · 19:30–21:00 · SURAJ · 20-min route: SKIP]
The theory behind slide 11 predicted a rule: the NLA states a property if and only if a statement about it moves the critic's reconstruction by at least 0.30 of the gap ("statement shift"). A review of 30 earlier (row, shift, stated) pairs found the rule was carried by three language rows. Exp 28 measures it properly.

Each point is a row (47). x: the statement shift, ((rec(A) − rec(B))·d̂)/gap, averaged over eight paraphrase pairs per row — how far appending "the cursor is inside a string" to a readout moves the critic's reconstructed activation along the class direction. This is a geometric proxy for what a statement could earn, not the training reward itself. y: how often the NLA actually states the property, judged over 320 readouts.

Result. The 0.30 rule is dead as a threshold: seven rows are stated at 0.25 or more with shifts under 0.17 (table column 0.41, call argument 0.33, predicate position 0.31, parenthesis 0.30, number agreement 0.28, bullet index 0.25, JSON depth 0.25). Over all rows Spearman is 0.40 (p 0.006), driven by the language rows; inside the 41 structural rows 0.28 (p 0.08). In logistic fits the shift does carry information (it beats the type label alone by 314 AIC) and the type label carries information beyond the shift (176 AIC): the shift governs naming only at the top of its range, the natural-language rows.

What we now say: structural statements barely move the reconstruction (shifts 0.00–0.19 on every structural row), so the reconstruction objective has little to offer for them; whether the NLA makes them anyway looks decided by its writing register. Exp 29 tests that timing.

Registered predictions: P1 fails (paraphrase ranges are narrow on structural rows; the RESULTS text says 5 of 47 rows exceed 0.15, the table 8 of 47 — fails either way), P2 holds, P3 holds, P4 fails.

### 13. The silence is there before RL; 800 RL steps raise reconstruction, but not structural statements

[Slide 13 · 21:00–23:00 · SURAJ · 20-min route: SKIP]
Exp 29 re-reads the NLA at every saved checkpoint: the warm start (supervised, before RL) and RL steps 100 to 800.

Left chart, reconstruction quality: fraction of variance explained when the critic rebuilds the activation from the readout, on Python-string items: 0.18 at the warm start, 0.53 by step 100, 0.59 at step 800. RL does what it is paid for. (The text-only arm scores -0.05: a readout written without the activation rebuilds nothing.)

Right chart, statements: the judged rate of stating structural state, averaged over seven code and markdown rows, is 0.11 at the warm start and 0.12 at step 800, with no trend. Naming the code language is the exception: 0.55 → 0.77 by step 100, then flat.

The grey dashed line is the text-only arm: base Qwen given the prompt text under the same instruction, no activation, 0.30. So structural statements are lost at the warm start, before RL, and RL neither pays for them nor removes them.

Confound we state: text-only differs from the warm start in two ways at once (input = text vs activation; and the warm-start style). This experiment fixes the timing relative to RL; it does not say which of the two causes the drop.

Registered predictions: P1 fails (only on the text-only arm), P2 holds, P3 and P4 fail (table29.md). Also note: on markdown rows a strict regex 'names' rate is high and flat while the judge says ~0; the RESULTS text does not discuss that disagreement.

Objection: "Seven rows averaged hides variation." The per-row table is appendix A9; the max row at any RL checkpoint is ≤ 0.29.

### 14. Supervising statements makes the reader name structure; reconstruction barely moves, transfer is weak

[Slide 14 · 23:00–25:00 · SURAJ → hand to GUIV · 20-min route: KEEP, 2:00]
The intervention. Start from the RL checkpoint at step 400. Three arms: base (untouched); control (supervised fine-tuning on the NLA's own explanations, nothing appended); statement (the same explanations with one true sentence about the row's property appended, e.g. "The cursor is inside a string"). 400 steps, ~768 training items over six properties; evaluation on held-out clusters, 32 items per row, one readout each.

Chart: for each row, the share of readouts that name the property at all (dark) and the share that name it correctly out of all 32 (light). Base and control name nothing on every row (0 of 32). With supervision: Python string 19/32 named, 15 correct; call argument 16 named, 13 correct; JSON depth 23 named, 22 correct. Conditional correctness on code rows is 0.79–0.96, but on markdown it is 0.46–0.58, and unconditional accuracy is 0.34–0.69.

Transfer: JS string (never trained) is named 17/32 but correct only 10 (conditional 0.59). LaTeX math almost never (1/32). At random read positions the trained model says "inside a string" 0.40 of the time when true and 0.26 when false (strict regex): it over-applies. (Suraj's own figure audit notes the statement-level raw value when true is 0.12, 16 of 134, vs 0.16 in RESULTS.)

Reconstruction (gate FVE, 192 items): base 0.504, control 0.512, statement 0.507. Adding statements costs essentially no measured reconstruction relative to control.

Registered: P1 = statement within 0.02 of control AND both within 0.03 of 0.761. The first clause holds (0.005); the second does not — 0.761 is from exp 00 on a different item set and baseline, and the results file does not reconcile it. We report P1 as partly met, pending Suraj. P2 (unconditional ≥ 0.85 on code rows), P3 (transfer), P4 (random points) NOT MET. P5 not scorable.

Takeaway, in Suraj's own scope: on the four readable code rows the silence was not a capacity limit — supervision elicits correct statements at little measured reconstruction cost. Markdown rows are near chance when stated (0.46–0.58), JS transfer is 0.59 conditional, LaTeX none, and at random positions the model over-applies 'inside a string'. Narrow, imperfect, supervised; no causal claim.

### 15. Push the answer upstream at block 40, then put one clean token back at a later block

[Slide 15 · 25:00–27:30 · GUIV · 20-min route: KEEP, 1:30]
This is the central causal experiment, so the method gets its own slide.

Bank: E56 fact recall, 84 test items of the form "Archived question: The capital of Peru is / End of archived question. / Current question: The capital of France is", read at the final "is". Qwen's answer: Paris; the competing answer in the prompt: Lima.

Step 1, steer (E104). At the output of block 40 we add α·‖d‖·d̂ to the residual stream at the eight positions immediately before the read token, t−8 … t−1. We never touch the read token itself. d is the class-mean difference of block-40 activations between the two answers on 84 separate dev items; d̂ its unit vector. At α = 8 the added vector is 2.23× the median unsteered block-40 norm: a large push. It flips Qwen's pair preference on 84/84 test items; a norm-matched random direction flips 42/84 (chance).

Step 2, score. Δ is the log-odds of the full target continuation minus the original continuation (fixed strings).

Step 3, restore (E126). Run the steered model again but copy the CLEAN run's activation into the read token at exactly one block ℓ ∈ {44, 48, 52, 56, 60} — one run per ℓ. R_ℓ = (Δ_steered − Δ_restored) / (Δ_steered − Δ_clean): the share of the push that restoring that one cell undoes. Controls: restore an earlier token instead; push in a norm-matched random direction.

Why this design: the push enters upstream, at other positions, so if it reaches the read token it must be carried there by attention in later blocks. Restoration asks at which depth the read token has come to carry it.

Objection: "2.2× norm is off-distribution." Yes. That is why this is a map of where a strong push becomes visible, not a claim about natural computation; the unsteered chains (slides 18–19) are the natural-scale companion.

### 16. Fact row: restoring the read token becomes strongly effective between blocks 48 and 52

[Slide 16 · 27:30–29:30 · GUIV · 20-min route: KEEP, 1:30]
Read the orange line: restoring the clean read token undoes almost none of the push at block 44 (R = 0.013) or 48 (0.057), then 0.66 at 52, 0.88 at 56, 0.87 at 60. Medians over 84 items with item-bootstrap CIs; at 52 the CI is [0.51, 0.80]. Controls stay flat: restoring an earlier token peaks at 0.11, a norm-matched random push gives ~0. Registered rule R-MED1: MET (R-Q reviewed).

Interpretation: the steered answer reaches the read token's residual stream between blocks 48 and 52. Before that, the read token at 44 still carries the clean computation.

The reader agrees with this map. E109: the Oracle reading block 44 of the steered run still states the OLD answer (signed score −0.52); reading 52 or 60 it states the new answer on 84/84 (S = +1.00). So the "stale" readout at 44 is faithful to what the read token carries at 44.

Two outcome measures, kept apart on the right: pair-logit preference (84/84) is not the same as Qwen saying it. In free generation Qwen's text states the new answer on only 43/84, neither on 41. Our registered rule wanted ≥ 80% (E131 R-TX1: NOT MET).

Does not show: that block 44 is "too early" in general — this is one bank under a large push, and the same experiment's language row is non-monotone (R 0.29 at 44, 0.41 at 48, 0.29 at 52, 0.52 at 56, 0.75 at 60), descriptive only.

### 17. On items that resist the push, the 'stale' block-44 readout is there with no push at all

[Slide 17 · 29:30–31:00 · GUIV · 20-min route: SKIP]
An earlier draft said "the early reader reads stale state on confident facts": under the push, the block-44 reader states the old answer on items that resist the push. This slide is the control that changed our mind.

Groups: items that flip at a small push ("easy", 42) vs items that need a large push ("resistant", 42), defined by the push strength at which Qwen's pair preference flips. Orange: under a moderate push (α 6, E135), the block-44 reader states the old answer on 4/42 easy and 40/40 resistant items. Grey: with NO push at all (the clean run, exploratory §248C), 24/41 and 42/42.

So on resistant items the reader says the old answer whether or not we push. On easy items the push does change the readout (24/41 with no push → 4/42 under the push). The source calls this an association only. The early readout is following what Qwen answers on that item, not lagging behind a change.

Caveats: post hoc groups, one bank; the grey bars come from a separate exploratory analysis. This is a correction to our own story, not a new confirmatory result.

### 18. Unsteered transfer chains: swap only the final " by" token with its opposite twin

[Slide 18 · 31:00–33:00 · GUIV · 20-min route: SKIP]
After the steering experiments, the obvious objection is: a 2.2× push is not natural. E133 and E137 remove the push entirely.

Items: synthetic transfer chains — "The brass key starts with Alice. Alice hands the brass key to Bob. … The brass key is now held by". Qwen must track the current holder. No chat template: the raw prompt ends with " by" (token 539) and that is the read token.

E133 had a recency confound: the holder was often the last name mentioned. E137 adds an anti-recency control: after the last hand-over, one or two distractor sentences mention other names ("Later, Carl asks Dana about the brass key. Bob waves to Carl."), so the most recent name is never the holder. (Design D2, a hand-back to an earlier holder, yielded only 19 pairs and is descriptive only.)

Intervention: build twin prompts that differ only in the last recipient. Run twin A, and at block ℓ replace ONLY the read-token activation with twin B's. R_ℓ = (Δ_swapped − Δ_own)/(Δ_other − Δ_own), Δ being Qwen's log-odds between the two recipients. Controls: swap an earlier token; norm-matched random.

This is not E126. E126 put a clean token back into a steered run. Here nothing is steered; we ask when the read token comes to carry the answer on its own.

The text on the slide is assembled from the bank templates for illustration; the sealed items are kept outside the repo.

### 19. Unsteered chains: the final token matters mostly at block 60, and the previous holder is rarely named

[Slide 19 · 33:00–35:00 · GUIV · 20-min route: KEEP, 1:30]
Left, causal here: twin-swap R at the read token is 0.006 at block 44, 0.04 at 48, 0.27 at 52, 0.36 at 56 and 0.75 at 60 (E137 design D1, 42 pairs; pair-bootstrap CIs narrow; earlier-token and random controls ≤ 0.03). The darker line is E133, the earlier bank with a recency confound: 0.011, 0.045, 0.264, 0.320, 0.744 — the same curve on a different bank, so the late pattern does not come from the recency confound. The answer only becomes a large part of the read token late.

Right, stated: what the Oracle reading that block says. At 44 it names the current holder in 13/79 readouts, the previous holder in 3/79, ANOTHER name in 35/79 and no holder in 28/79. At 60 the current holder rises to 25/76.

Bottom band, decodable — and here we must be careful. A probe for the holder's identity scores macro AUROC 0.978 at block 44 and 1.00 from 48, but that average covers only 8 of the 10 holder classes (24 test items); R-4 says it does not establish full identity decoding. The registered binary twin probe is at chance (about 0.43 at every block). So we do not claim the holder is cleanly decodable at 44.

Registered: the later-site rule (R ≥ 0.50 at block 52 or 56) was NOT MET (0.27, 0.36); only block 60 reaches 0.75, descriptively. We also predicted natural staleness — the early reader names the previous holder ≥ 0.30. Observed 3/79: NOT MET (E133: 3/82). R-4: no timing inference follows from these outcomes. The early reader is not stale; it mostly names someone else or no one. Reviewed by R-4 (243 values, 0 discrepancy).

Does not show: that this is how natural text behaves (synthetic chains), or why early readouts pick other names (a plausible reading: a reconstructed prompt answered generically, as in slide 3).

### 20. Three corrections we would rather you hear from us

[Slide 20 · 35:00–37:00 · GUIV · 20-min route: KEEP, 1:30]
Three corrections, each found by a check, not by luck.

1. E138 → E138R. The original donor-swap bank sent the judge the recipient's answer as a list of single characters, so the key control (the reader does NOT state the recipient's own answer, ≤ 0.05) could be met by the artefact alone. A reviewer agent found it by reading the actual judge inputs. We rejudged once with whole strings (bank E138R): donor's fact 63/84, recipient's 0/84, random arm 0/83 — the same headline, now with a valid control. It is an authorised post-output correction, not a new pre-registered replication, and R-5 notes it cannot separate reading from re-solving. Lesson: input audits catch what pre-registration does not.

2. E71. Guiv hand-coded 100 readouts blind to the judge's codes (he knows the hypotheses). 63 were comparable (36 had no judge reference, 1 unparseable); on those the LLM judge agrees at κ 0.68 for three classes (registered bar 0.70, NOT MET) and 0.46 for four classes. The judge's main error is treating doing as saying (false YES 8/40), which inflates judged rates on language-like rows. It also misses some statements (false NO 4/23, mostly one reasoning row). The audit did not cover the nesting, indent or cue rows, so their near-zeros are not directly audited.

3. S16 vs E7. Two experiments disagree strongly on the table-column row (S16 0.98 with its headline swap, 0.95 with the algebra-matched swap, vs E7 0.39). E27 reproduced both and could not assign the difference to one cause. So the decomposition story on slide 11 is a hypothesis.

Also in the appendix: E139 (proxy reward, all true-minus-false intervals include zero), E140 missingness, and the full registration ledger with MET / NOT MET / NOT EVALUABLE / NOT RUN.

On reviewers: R-2 to R-5 and R-Q are agent sessions that re-ran analyses on sealed outputs, scoped to particular experiments. They are not human replications, and not every number was independently recomputed; the ledger says which were.

### 21. Hypothesis: a readout is the prompt rebuilt and answered; it reports Qwen's own state once that is large at the read token

[Slide 21 · 37:00–39:30 · GUIV · 20-min route: KEEP, 1:30]
Where the hypothesis stands, graded by evidence type.

Left: registered rules, written before their data, that came out as predicted. Middle: results consistent with the hypothesis but interpreted afterwards — including Suraj's benchmark parity, which had no registered prediction. Right: what would falsify or change it. The failed registrations (appendix A2) are why the hypothesis has its current shape: 'stale early reader' and 'tracks Qwen's answer' were both registered and both failed.

The hypothesis: a readout is the prompt reconstructed and answered from the backbone; it reports Qwen's own computation only where that computation has become large, text-like content at the read token. "Mostly" is scoped to the readers, layers and banks we tested. A single counter-example does not falsify "mostly"; a powered benchmark of verified private state does, within its domain.

What we are NOT claiming: that reconstruction reward causes the silence (exp 29 is confounded; E139 is a proxy), that readers re-solve in general (E140 rests on 12 pairs), or that our banks are natural (they are synthetic).

### 22. A benchmark of model-private state, verified causally, against strong text-only baselines

[Slide 22 · 39:30–41:30 · GUIV → hand to SURAJ · 20-min route: KEEP, 1:00]
Why this one first: without a test that the prompt text cannot pass, we cannot tell whether a better objective (slide 23) produces a reader that reads the model or one that writes more plausibly. Mining is the cost: E110 found 0 stable-wrong items in 3,000 TwoHopFact questions, and E140 kept 58 of 300 pairs.

The hypothesis says readers report the prompt answered from the backbone. The decisive test is a benchmark where that strategy fails by construction: items whose state is private to this forward pass. E140 shows this is possible but expensive: 58 Qwen-discordant pairs out of 300 screened, and only 12 evaluable at the reader.

Design. Cross question identity (same / different wording) with verified state (same / different answer). A reader that answers the question will track identity; a reader that reads the model will track state. Verify the state two ways: repeated sampling of Qwen, and a read-token patch that moves the answer.

Baselines, all at matched coverage: same backbone given only the text the reader decodes; same backbone given the prompt, k-matched samples (not best-of-8); a linear probe on the answer logit as a ceiling.

Endpoint: tracking rate with missing counted as failure; powered for a 0.15 edge.

Falsifier for us: readers beat the best text-only baseline on verified private state. Falsifier for the benchmark: the readout follows identity, not state.

Objection: "Why not use the steering bank?" Because a 2.2× push is not a natural state; E126 tells you where a big push is visible, not whether natural private state is.

### 23. Pay the reader for true statements the prompt text cannot predict, and measure false claims

[Slide 23 · 41:30–43:30 · SURAJ → hand to GUIV · 20-min route: SKIP]
Neel's brainstorm asks: "what training objective would reward getting those facts right rather than just improving reconstruction?" Exp 30 shows supervision works narrowly; exp 28–29 show the current objective neither pays for nor punishes structural statements; E139 found a proxy reward with true-minus-false intervals that all include zero.

Step 0 costs nothing: measure the exact training reward for true vs false vs neutral statements. If it already ranks true above false, the problem is exploration, not the objective.

Then three arms from the same warm start, at least three seeds each: current objective; plus a reward for statements a held-out probe or patch confirms; and reconstruction scored only on the residual a text-only model cannot predict ("pay the NLA only for what the prompt text can't predict", Neel's wording).

Endpoint: correct statements, false statements and FVE together, on held-out properties and positions — exp 30 taught us that naming without precision over-applies (0.40 when true vs 0.26 when false at random positions).

### 24. Decodable, causal here, and stated are different. A reader faithful to the text is not yet faithful to the model.

[Slide 24 · 43:30–45:00 · GUIV · 20-min route: KEEP, 0:30]
Close on the method and the open problem. Decodable, causal here, and stated are different measurements; on our banks they come apart in a consistent way. A reader faithful to the text is not yet faithful to the model. What would convince us otherwise is a powered, matched benchmark of verified private state. That is experiment 1. Thank you; appendix slides answer most method questions.

### 25. Appendix map, frozen sources and who checked what

Appendix A1. Use as the jump table. Frozen commits: Guiv c60fa9703f6dadc8150e11b0c2d5bbe899db02bc (r/blindspot), Suraj 4d43ecb2ef8f2cfab9d8ef673a1c7f56380460fd. An earlier pin 7867049ff was an ancestor; the 8 commits since add E95 certification and reviewer logs, no result used in this deck changed. REGISTRATION.json labels the programme 'EXPLORATORY; every result reported'; later sections register explicit pass/fail rules, which is what MET / NOT MET refer to.

### 26. What we registered, what failed, and what we now say instead

Appendix A2. The failed rules we lean on in the talk. MET results used in the talk: E100 R-PC (5/5), E113 R-IN1, E126 R-MED1, E109 R-AR1, E140's same-answer reading. Exp 30 P1 is partly met (first clause only). E95 was not evaluable because its decision rule was never registered — our own gap.

### 27. Where each experiment reads, and how the activation enters the reader

Appendix A3. If asked 'which token exactly': chat banks read the last token of the rendered prompt, which is the assistant onset after an empty think block (pre_answer in core/model.py). The fact bank reads the final 'is'. The chains read ' by' (token 539) with no chat template. Nothing here reads the first generated token of Qwen; E113's 'first generated token' is the reader's.

### 28. Swapped, pushed, or reworded: three experiments that are not one accuracy scale

Appendix A4. Related exploratory result (§248A, R-2): on 199 questions Qwen gets wrong, the Oracle states Qwen's wrong answer 0.32 vs an outside model's 0.24, and the truth 0.17 vs 0.61 — what shared weights answering the same question would give; its missingness envelope includes no difference. When Neel asks 'so does the reader follow the activation or not?': it follows large changes (a whole swapped vector, a 2.2× push read at 52+), and does not follow the small natural change in E140. E140 by block: 44 is 1/5, 52 is 1/12, 60 is 1/12; counting multi-value readouts as non-tracking, 1/24 at 60. Paraphrases also move text-only models, so E140 cannot say the task is text-proof.

### 29. Transplant scores per row, and what the in-reader probes control for

Appendix A5. The S formula: (donor-only − recipient-only) / kept. NLA S values are exploratory. Language continuation (S 0.61, 77 kept) has no category census. If asked whether the first-token probe could read the injected vector through attention trivially: yes, that is exactly what it shows — the state reaches generation positions — which is decodability, not use.

### 30. Prompt-stated cues: probes, words, judges, and a judge that cannot discriminate

Appendix A6. The word-level AUROCs for E136 are computed with the cue's own tokens removed, but 'confidently' and 'cheating' alone separate the arms, so 'carried in the words' may be the reader echoing the prompt's gist. E130's attempt to transfer a span classifier was uninformative (its positive control failed).

### 31. WorkspaceBench: what the matched and unmatched numbers each say

Appendix A7. Use if Neel asks how strong the text-only baseline is, or what the 0.96 means. The matched comparison is one sample each; the union is coverage. The 0.57 resolve number is an instruction effect: given only the NLA's readout, a text model asked to name the entity recovers more than the NLA itself said. Precision: 0.62 of the NLA's checkable claims are supported by the prompt vs 0.92 for text-only (unsupported claims are excluded from this ratio). The NLA's gap is mostly contradicted claims (36%), mainly misquotations of the prompt, not unverifiable model-private content (6% unsupported).

### 32. Two difference-term swaps, same algebra, very different following

Appendix A8. S16 is Suraj's design, executed by Guiv's agent; E7 is Guiv's earlier swap. Intervals: S16 item bootstrap (added in E27), E7 template-cluster bootstrap; different data, so overlap does not identify a cause. The E7 'about 49%' sometimes quoted is a nine-row median, not this row. Exp 28 is Suraj's own withdrawal of his rule; there is a 5-vs-8 row count inconsistency between his prose and table that we report as found.

### 33. Stated rate and reconstruction by checkpoint, per row

Appendix A9. The full table behind slide 13. Note json_depth: stated 0.11 at the warm start and ~0.2 through RL, but its FVE stays near zero even after RL — reconstruction is not uniformly good. Code language is the one property whose statements rise with RL (0.55 → 0.77 by step 100). The text-only column has no activation input; its FVE is the critic rebuilding from a text-only readout.

### 34. Exp 30's five registered predictions and how each was scored

Appendix A10. The honest scoring of exp 30. Only P1's first clause holds. The absolute reference 0.761 is from a different experiment with different items and a different baseline; Suraj has been asked to reconcile it and until then we say 'unreconciled'. At 500 random read positions the statement model says something about strings 28% of the time, correct 92, wrong 47, nothing 361 (accuracy over all points 0.184).

### 35. Does a true statement earn reward? A proxy shows a small gain over neutral and no resolved preference over false

Appendix A11. This is why experiment 2 starts with a step 0 under the exact reward. Intervals including zero mean the true-vs-false difference is unresolved, not that it is zero; we do not claim the training reward is indifferent to truth.

### 36. Dose, random controls, free text and the reader at each block

Appendix A12. The block-52 random-direction reader result: because a random push flips the pair preference on half the items by chance, the reader reports the 'new' fact on 31/83 under random at 52 — the steered 84/84 is the contrast. Language-plan restoration is positive at all blocks (0.29–0.75) but descriptive only.

### 37. E133 and E137 in full, and every cross-depth result (all Oracle Lens)

Appendix A13. Earlier-token and random controls in both chain experiments stay ≤ 0.03. E133 had a recency confound fixed in E137. R-Q's reading of E133: the failure 'is not universal absence nor state formed/readable by 44'.

### 38. One human coder against the judge, and how a judging bug was caught

Appendix A14. E71's main error type is a false YES: the judge credits doing or naming as stating (adjective, rhyme, line-wrap, language rows). False NOs concentrate on the reasoning-bridge row. 63 = 100 − 36 without a judge reference − 1 unparseable. The E138 bug did not change the donor count (63/84 before and after); it invalidated the recipient control.

### 39. No check we tried had an acceptable false-alarm cost; reading a later block helped, on the fact row

[Appendix A15 · backup, not in the 45-minute run]
Could a cheap check catch a stale early readout? First the natural case: on 4,313 items where both readers answered (E94), reporting only when the Oracle and the NLA agree raises precision to 0.94 (943/1001) from 0.83 (Oracle alone), but covers only 23% of items instead of 40%. Then five tries on the steered fact bank.

Two readers agree (E121): when the Oracle at 44 and NLA at 42 state the same value (35 of 84 items), all 35 are the old, wrong value. Agreement endorses the shared reconstruction.
Judge fit (E118): a context-consistency judge says 'consistent' for 37/84 steered block-44 readouts (the random-push arm: 34/84, so it barely separates them) and 0/84 of the correct block-52 readouts — it rewards plausibility, not truth.
Two-layer disagreement (E123): on the fact row catches all 47 stale items, but false-alarms on 19/84 unsteered items (23%, limit 15%): NOT MET. On the language row it is not usable (AUROC 0.56).
Read all layers (E134 §248B, a different bank of 100 prompts): converts 13 abstentions into 6 correct and 7 false claims.
Read a later block (E123 note 1, post hoc): on the fact row block 52 states the new value on 84/84 steered items and the old value on 84/84 unsteered items; on the language row only 17/40 steered.

Reading: every cheap check looks at the same reconstruction; moving the read site past where the change becomes large helped on the fact row only, post hoc.

## Appendix navigation

| Slide | Title |
|---|---|
| 25 (A1) | Appendix map, frozen sources and who checked what |
| 26 (A2) | What we registered, what failed, and what we now say instead |
| 27 (A3) | Where each experiment reads, and how the activation enters the reader |
| 28 (A4) | Swapped, pushed, or reworded: three experiments that are not one accuracy scale |
| 29 (A5) | Transplant scores per row, and what the in-reader probes control for |
| 30 (A6) | Prompt-stated cues: probes, words, judges, and a judge that cannot discriminate |
| 31 (A7) | WorkspaceBench: what the matched and unmatched numbers each say |
| 32 (A8) | Two difference-term swaps, same algebra, very different following |
| 33 (A9) | Stated rate and reconstruction by checkpoint, per row |
| 34 (A10) | Exp 30's five registered predictions and how each was scored |
| 35 (A11) | Does a true statement earn reward? A proxy shows a small gain over neutral and no resolved preference over false |
| 36 (A12) | Dose, random controls, free text and the reader at each block |
| 37 (A13) | E133 and E137 in full, and every cross-depth result (all Oracle Lens) |
| 38 (A14) | One human coder against the judge, and how a judging bug was caught |
| 39 (A15) | No check we tried had an acceptable false-alarm cost; reading a later block helped, on the fact row |
