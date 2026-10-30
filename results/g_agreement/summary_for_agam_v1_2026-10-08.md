# Cross-referencing activation readers on Qwen3.6-27B — summary for Agam (2026-10-10)

Guiv Farmanfarmaian and Suraj. Full write-up: `results/g_agreement/writeup.md`; plan: `NEXT_STEPS.md`.

**Scope.** Three readers of a hidden vector: J-lens (linear Jacobian lens), NLA (natural-language autoencoder) and
Oracle lens, all applied at their training site, block-42 output at the last prompt token, pre-answer. Six
feature classes from synthetic prompts (language, tense, object ownership, symbol mapping, the model's own puzzle
errors, its own two-option choices), 23–64 pairs per class, pre-registered before each run. **Not tested:** SAEs,
Skip Lens, anything "non-workspace". Assets for all three exist (Qwen-Scope SAE for Qwen3.5-27B, four layer-42
skip-lens LoRAs with our NLA's injection convention, Suraj's J-space basis) and are the next step.

**1. The three readers behave as one instrument** (`x/fig_main.png`, the blindness map). Parsed as free text they
named zero of 16 bindings (G1–G2). Scored by their own log-odds on 47 pairs they all carry the binding: J-lens
85% / 94% (ownership / mapping), Oracle 83% / 87%, NLA 72% / 72%; language and tense 100% for all. J-lens and
Oracle beat NLA on the same pairs (paired sign tests p ≤ 0.004, mapping-driven). On the model's own errors all
three favour the same candidate in 46% of items against 25% under independence. Everything a linear probe finds at
this site, all three report; the two classes none of them reports above threshold, the probe barely finds either.
*Lesson one: free-text elicitation, not the activation, was the limiting factor; score verbalizers natively.*

**2. Agreement with the majority is not ground truth** (`x6/fig_main.png`). We graded each reader two ways on the
same states: agreement with the leave-one-out majority of the other readers, and agreement with a key established
without readers (the constructed answer; a planted fact verified by a behavioural flip; the model's own answer).
On constructed and planted items the majorities are 88–94% right, but only because each reader is individually
right. On the model's own errors the ranking inverts: the two sibling verbalizers (same base model, similar
training) agree with each other 70% of the time but with the model's actual answer only 47–59%, and where they
agree they are right 55%; the non-sibling pair (J-lens + probe) is right 74%. The linear probe is the best reader
against the key (67%) and the worst by majority agreement (47%); the Oracle is the reverse (47% vs 66%). Spearman
across readers −0.8. *Lesson two: a majority of similar readers measures shared training, not truth.*

**3. What the readers track under a causal edit** (`x2/fig_fraction.png`). Editing the last-token vector at layer
38 never flips the model's answer (0/128 up to α 3; 17/128 at α 4). Editing all positions flips 98% of states by
α 0.75 (random directions 0/768). Along that ladder each reader's log-odds move by exactly the dose fraction of
its own natural separation (0.22 / 0.50 / 0.78 / 1.00 at α 0.25 … 1), i.e. the readers walk the straight line
between the two states, while the model's answer is a threshold. At the inert last token the readers report the
planted candidate at 1.1–1.7× their own separation while the model's answer does not move. *Readers report what
is in the vector whether or not the model uses that vector; "follows the binding" is not yet separable from
"reads the interpolated state" (identity-free null pending).*

**4. Where the answer is not in the text.** 267 of the model's 297 puzzle errors are a "stop one step early"
symbol, so only 30 are off-text. After removing each reader's symbol priors, readers favour the model's actual
wrong answer 54–57% on errors vs 47–51% on correct controls; an 8-way logistic probe for the upcoming symbol
reaches 68% on errors (permutation null 61%, two-half ceiling 36%); a probe for the *correct* symbol is at 50%.
Self-choice disagreements (n = 33): readers 61–70%. *The model's upcoming answer is weakly present at this site
and the readers sit at the probe's level; all below the pre-registered 0.75 bar.*

**Caveats we would raise ourselves.** "Consensus adds 0 pp" is a ceiling artefact, not a result. Ownership binding
is confounded with mention order in our bank (one direction carries 66% of the within-pair variance). Probes are
L2 logistic with 10 permutations; 136 blind free-text rows unadjudicated; synthetic prompts, rule-based keys.

**Next, and why.** (i) Site search: find the (layer, position) where the model's off-text answer is linearly
present, then re-read there, because that is the only place a reader could add value over the text. (ii) The
identity-free null at the causal site (other pair's direction, name component projected out), because §3 stands
or falls on it. (iii) A fourth reader family (skip-lens arms, R-lens, SAE transfer) to answer the untested half of
the prompt and break the two-siblings-vs-one structure. (iv) Suraj: J-space vs non-J split of the planted
direction, and his column-wrapping feature as the one non-workspace row with a behavioural key.

**Questions for you.** Should readers be judged only at their training site, or wherever the fact is
load-bearing? Which definition of "non-workspace" would you accept (J-space complement at r*, or behavioural)?
Is the right ground truth "best linear probe" or "causal flip only"? The two disagree on mapping.
