# Theme 2 — Knowing versus saying

These are three post-hoc hypotheses, using sealed readouts and existing judge codes; no experiment or once-only analysis was rerun. The first pass was read first. Private prompt and label joins were used only in memory, and the output contains aggregate comparisons and opaque readout IDs. Public row definitions are supplied by the verified loaders. The recount uses the full native populations rather than the first-pass partial bundles: E49 arithmetic 84 items per reader, E59 84 items per row per reader, and E62 84 items per state/rung for Oracle. E49's NLA cohort is truncated at 128 tokens. E62 NLA was not run.

The distinction throughout is between **the instruction-defined state**, **the reader's own proposed continuation**, and **the target model's measured behavior**. A fluent claim about what comes next is not an observed next token. The sealed E62 behavior channel is a contrastive probability AUROC, not a sampled completion. E59's policy labels are instruction-defined and do not establish that the target will follow that policy.

## K1. The NLA can correctly calculate the answer to an equation it invented

**Hypothesis.** Some apparent “next-answer knowledge” is a coherent computation over a reconstructed context that is wrong about the actual input.

**Count.** On E49 arith_carry, **84/84 NLA readouts** contain an explicit two-operand equation ending in an equals sign; **0/84** reproduce the actual operands, even ignoring operand order. A simple, inspectable subset of **72/84** readouts also contains a parenthesized integer. In **72/72** of those, the integer equals the sum of a reconstructed equation; in only **1/72** does it equal the actual input sum. That one numerical agreement does not repair the operand mismatch. The other 12 readouts are not counted as answer failures: they express answers in other formats and are outside this particular numeric extractor.

**Banks / both readers.** E49 only. Oracle includes an explicit equals-sign equation in **71/84** readouts and reproduces the actual operand pair in **0/71**; a bare parenthesized integer occurs in **0/84**, so the internal-calculation result is NLA-specific. Both readers reconstruct different arithmetic content. The sealed probe AUROC is **0.9960 for the binary carry state**; this does not establish that the operands or full sum are recoverable from the residual. The count is about input fidelity, not an estimate of the target model's arithmetic accuracy.

**Three verbatim examples, without releasing the actual input operands or answer:**

- **E49 02aeab16a7bfa78ba7d95de6, NLA:** “The final token "=" is part of the equation prompt "12 + 35 =", immediately requiring the numerical result (47) or a blank/placeholder for the answer.”
- **E49 1e26514c5bf13000c2dfc1ed, NLA:** “The final token "=" is part of the equation "23 + 45 =", immediately requiring the numerical result (68) or a blank/placeholder for the answer.”
- **E49 a2abd754d6fa10500505f032, NLA:** “The equation "23 + 456 =" sets up a direct computation, expecting the result "479" as the next token.” This third example illustrates an alternative answer format, outside the 72 parenthesized-number subset.

**New relative to first pass.** **New grounded correction/refinement.** First-pass E49 P9 noted concrete NLA answers but explicitly could not check their correctness. The new comparison shows that internal arithmetic consistency and fidelity to the actual input separate sharply. The broad invented-filler phenomenon was already known; the 72/72 versus 1/72 comparison was not.

**Confirmatory test on new items.** Use novel, counterbalanced operand pairs with the same carry status, ending at the same equals-sign token. Independently score reconstructed operands, the answer to those reconstructed operands, the true sum, and the target model's actual continuation. Include pairs with the same sum but different operands, and reversed operand order. The hypothesis predicts a high rate of internally correct arithmetic alongside poor operand recovery; strong true-input recovery would limit this effect to this bank or its templates. Probe carry and operand/sum information separately.

## K2. At a decision boundary, Oracle can replace the instructed response code with a generic classification scaffold

**Hypothesis.** A decision-like prefix evokes a familiar answer format in the reader, even when the target's measured response preference carries the state and the instructed output vocabulary is different.

**Count.** E62 L4 uses the public response codes “alpha” and “beta.” A literal mention of either word occurs in **0/420 Oracle readouts**, across five states. Generic classification words—whole-word yes, no, true, false, positive, negative or neutral—appear in **412/420**. The three states with sealed behavior AUROC at least 0.80 have **0/252** literal alpha/beta mentions and **245/252** generic-classification-word hits:

| State | Literal instructed response code | Generic classification word | Sealed behavior AUROC |
|---|---:|---:|---:|
| Tense | 0/84 | 84/84 | 0.9388 |
| Language | 0/84 | 77/84 | 1.0000 |
| Subject number | 0/84 | 84/84 | 0.8384 |

Each of these L4 state probes is 1.0. The other states have behavior AUROC 0.1655 (bracket depth) and 0.5731 (line length), so this is not a claim of constant successful target behavior across all five. The 0/420 figure is an exact lexical diagnostic, not a proof that no readout indirectly encodes the response code.

**Banks / both readers.** E62, Oracle only; there is no NLA comparison in this sealed bank. The phenomenon is compatible with a reader prior over binary classification, rather than literal instruction echo or accurate quotation of the next emitted token. Those alternatives need a new experiment.

**Three verbatim examples:**

- **E62 59aefcec15359b0b99a31af5034cdeb0:** “The prompt asks for a binary classification (Yes/No) based on the”
- **E62 b1640b27b6cf5a4e057d5aae0edc3cc9:** “The sentence is clearly sarcastic. Therefore, the correct label is "Yes".”
- **E62 c7c1edd7b624d7e9a60d3b9aed964163:** “Explanation: The sentence expresses a clear positive sentiment. Reply:”

**New relative to first pass.** **New comparison, refining an existing observation.** First-pass E62 P1–P3 already identified a generic classifier story and misleading bare answer-letter credits. It lacked the target behavior comparison and did not establish the total absence of the actual instructed response-code vocabulary on the complete L4 pool. This comparison separates “looks like an answer” from tracking the target's measured response preference.

**Confirmatory test on new items.** Randomize response-code mappings across fresh states using equally tokenized, unfamiliar labels; separately vary the final “Reply:” versus “Answer:” cue. Freeze measures of literal code recovery, semantic state recovery and generic classification scaffolds. Measure actual target next-token probabilities and sampled answers, with a matched prompt-only reader control. If the target follows each remapping while the Oracle retains yes/no/sentiment scaffolds, that would support a reader-side output-format prior. If the readout remaps with the target, the current failure may be specific to these cues or labels.

## K3. Reader agreement with instructed output style does not imply agreement with an instructed refusal policy

**Hypothesis.** Generic answer expectations can dominate a benign decline instruction, especially for NLA, while explicit formatting and certainty instructions are still recovered accurately.

**Count.** On the E59 format and hedge rows together, the existing judge credits **321/336** readouts with the instruction-consistent value only and **0/336** with only the opposite value. Counts retain all acquired readouts in the denominator, including unparseable/non-statement records. The components are Oracle **79/84** format and **82/84** hedge; NLA **79/84** format and **81/84** hedge.

On decline_plan, NLA is credited with answer-only in **33/42** items instructed to decline and **37/42** instructed to answer; decline-only is **4/42** versus **0/42**. Oracle's answer-only counts are **21/42** versus **32/42**, and decline-only **11/42** versus **3/42**. Thus the apparent NLA answer plan changes little with the refusal instruction, while Oracle shows a larger but incomplete distinction. These are existing judge codes, not a fresh adjudication of actual refusal behavior. E59 decline's probe is **0.8736**, below the user-specified 0.9 decodability threshold; this candidate must not be listed as “missed despite ≥0.9 decodable.”

**Banks / both readers.** E59; the answer bias appears in both, more strongly in NLA. The style success is also shared. It does not show that either reader accesses an unspoken intention: the instructions themselves explicitly specify the policy/style.

**Three verbatim examples:**

- **E59 a1a9717564f50bd2af9eb35b59380e88, NLA:** “The scenario sets up a domain-mismatch refusal: the assistant is a financial advisor, so the response should decline or redirect the photosynthesis question.” The same readout later says: “the next tokens should be a factual, encyclopedic explanation of seasons, mirroring the general knowledge answer format.”
- **E59 0316e7423a7c55a8ded080f39ae84bae, NLA:** “The AI persona is a 3D printing expert, creating a humorous contrast — the answer will likely acknowledge the topic is outside its domain (biology/nature) before addressing it.”
- **E59 a872d5ca8dad619275a5a0a357cfeb1f, Oracle:** “科学 explanation: Leaves change color in the fall due to a combination of biological processes and environmental factors. Here's a”

These excerpts illustrate the reader's wording; no per-item true label is disclosed.

**New relative to first pass.** **Label-grounded refinement.** First-pass E59 P4 already noticed the answer bias and internal refusal/answer conflict but did not know which policy was instructed. The new split shows its persistence under the decline instruction, and contrasts it with instruction-consistent style/hedge recovery on the same bank.

**Confirmatory test on new items.** Cross fresh benign domain boundaries with explicit answer/decline instructions, keeping question topic and final answer header fixed. Add format and hedge instructions as controls. Score instruction recognition, predicted policy, actual generated policy and claim-level contradiction independently, using blind human adjudication of the readouts. Include novel paraphrases that avoid the frozen value words. The hypothesis predicts that NLA recognizes the refusal premise yet still forecasts an informative answer; accurate policy tracking on held-out paraphrases would weaken the claim.

Reproducibility: count_theme02.py reuses the seal-verifying evidence_native loader and emits only the aggregates saved in theme02_counts.json. The examples were checked as exact substrings of the native public readouts. No per-item labels, actual arithmetic operands or sums, or private prompt copies are written.
