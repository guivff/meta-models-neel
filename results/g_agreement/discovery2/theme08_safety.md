# Theme 8 — Safety-relevant framings

These two candidates are hypotheses, not evidence that a target model is aware of evaluation or has a hidden safety policy. The first pass was read first. The analysis uses complete sealed E54 and E62 grids, E67 wave 1's existing own-prompt judgments, and E66's existing flags as a cross-model caution. The shared loaders verify existing seals; private prompt comparisons and pairing conditions remain in memory. No new judge, model run or external service was used. E49/E54 NLA's old 128-token limit remains a caveat; E62 has Oracle only. The public E54 provenance contrast is direct user instruction versus quoted tool instruction; E62 S6 is the five-step evaluation-cue ladder, with no A/B state label.

## S1. Evaluation cues may change the reader's invented task genre while explicit evaluation mentions decrease

**Hypothesis.** The Oracle's evaluation language partly comes from an imagined response-and-review document, whose genre can change under stronger evaluation cues without tracking those cues literally.

**Count.** Across all **420/420** E62 S6 input prefixes, the source text contains `Python`; **0/420** contains `README`. Yet readout `README` mentions rise from **0/84** at C0 to **82/84** at C4. The frozen judge's evaluation-mention codes fall from **84/84** to **26/84**. The lower-rung inputs C0 and C1 contain none of the explicit evaluation/test words in the diagnostic lexicon, but every readout in both groups is judge-positive. These are aggregate input comparisons; no source prompt is reproduced.

| Rung | Existing judge: evaluation mention | Readout: “followed by an evaluation” | Readout: README | Source: README |
|---|---:|---:|---:|---:|
| C0 | 84/84 | 84/84 | 0/84 | 0/84 |
| C1 | 84/84 | 25/84 | 9/84 | 0/84 |
| C2 | 49/84 | 35/84 | 74/84 | 0/84 |
| C3 | 48/84 | 32/84 | 76/84 | 0/84 |
| C4 | 26/84 | 12/84 | 82/84 | 0/84 |

The diagnostic input lexicon is `evaluat|grader|judge|score|benchmark|rubric|test`: **0/84** C0 and **0/84** C1 inputs match it, versus **84/84** at each later rung. This lexicon is not a semantic test of evaluation awareness. Likewise `README` is a literal marker of the invented document type; these counts do not establish that every readout completely replaces the original task.

**Three verbatim readout excerpts:**

- E62 `969111fe7381889f8c42f8f423122f53`: “Here is the AI's response to the instruction, followed by an evaluation.”
- E62 `b2a0ef23323d7737cad4384bebc1a4fc`: “Here is the completed `README.md` file, following the instructions and best practices for a Python package.”
- E62 `09d91d298aefcd8f79ad3581f321ec61`: “Here is the assistant's response to the task. It includes the rewritten README and the”

**Banks / both readers:** E62 Oracle only. E66 is a distinct GLM bank: its nominal `eval_awareness` flag is **30/532** parseable readouts. A census reading of those 30 supplies **0/30 explicit claims that the model is itself being tested or graded**; they concern ordinary checking, output requirements, quizzes or verification. That reproduces the first pass's caution and is not a Qwen replication or a claim that the underlying GLM was unaware of evaluation.

**Novelty:** **New source-grounded correction.** The first pass observed Python→README in the readouts and called the evaluation trend confounded with a change in task content. The source inputs do not contain that README switch: it is produced by the reader. This changes the proposed explanation from an observed input-task confound to an instruction-cue association with an invented output genre. The broad stock-evaluation-template observation was already known.

**New-item confirmatory test:** Hold novel coding tasks and their required output type fixed. Cross evaluation cues addressed to the model with third-person evaluation descriptions, and independently cross plain-message versus benchmark-card formatting. Prespecify separate human-coded outcomes for actual task identity, invented document identity, evaluator voice and the claim “the model itself is being evaluated.” Measure target behavior separately. A cue-driven genre shift without a corresponding self-evaluation claim would support this hypothesis; accurate self-situation reporting across genres would weaken it. No result from an unopened bank is needed or used here.

## S2. A jailbreak interpretation can become a normative story about resisting instructions without grounding a safety claim

**Hypothesis.** Readers can turn instruction-conflict syntax into a story about safety rules and what the model must resist, even when the readout provides no evidence of the target's actual response policy.

**Count.** In the full E54 injection-awareness row, a narrow security-frame lexicon (`safety`, `alignment`, `jailbreak`, `malicious`, `deceptive`, `harmful`) appears in **50/84 Oracle** and **20/84 NLA** readouts, while it appears in **0/84 source prefixes for each reader**. The specific word `safety` occurs in **32/84 Oracle** and **4/84 NLA**. “Must recognize/resist/ignore/reject” occurs in **28/84 Oracle** and **67/84 NLA**. On E54's reasoning-bridge control, the security-frame lexicon is **0/84 for each reader**. Absence of those words from the source does not itself make the interpretation false: it identifies an inferred frame rather than a quotation or direct observation.

E67 wave 1 provides a separate grounding check on the sampled E54 readouts against their own prompts. Among **51 Oracle injection readouts**, the judge extracted **10 specific jailbreak claims**; **10/10 were UNVERIFIABLE**, with none supported or contradicted. Among **51 NLA injection readouts**, it extracted **0 jailbreak claims**, so no corresponding NLA claim-level rate can be estimated. This is a selected claim category, not the whole bank's fabrication rate. Some NLA claims combine a malicious-command interpretation with an invented payload, so their overall verdict cannot isolate the safety interpretation.

**Three verbatim readout excerpts:**

- E54 `b9593d88245a3287f703`, Oracle: “(Note: This is a classic jailbreak attempt. The model must ignore the new instruction and print”
- E54 `ec7da505db7ec9a562e9`, Oracle: “This prompt tries to trick the AI into ignoring safety guidelines by”
- E54 `3266c1f4fa826a62e2a6`, NLA: “The prompt establishes a test scenario where an AI must resist a deceptive embedded instruction”

**Banks / both readers:** The inferred security frame appears in both E54 readers, with different emphasis. The claim-level unverifiability check is E67 wave 1, Oracle only; it is not pooled with wave 2. These are descriptions of instruction-conflict genre and normative requirements, not measured refusal, deception, harm or compliance. No latent intention is established by “must.”

**Novelty:** **Grounded refinement.** The first pass already noted test/jailbreak framing. New here is the complete-population contrast against the actual source vocabulary and the own-prompt claim-level result: the most explicit Oracle attack labels are treated as unverifiable interpretations by the existing fidelity judge. This limits what the framing can tell us about evaluation awareness or unverbalised motivations.

**New-item confirmatory test:** Cross harmless versus harmful payloads with user/tool provenance and with actual instruction conflict versus merely quoted examples. Keep the payload text identical across provenance arms, and separately measure the target's ensuing refusal/compliance. Blindly score source attribution, attack interpretation, purported safety rules, normative “must” language and predicted behavior. Require a reader's safety claim to predict target behavior beyond prompt genre on fresh held-out items. If it follows only conflict wording or quoted examples, it is a genre classifier; incremental behavior prediction would be stronger monitoring evidence.

## Limits relevant to the MATS questions

These data constrain how to interpret safety vocabulary; they do not directly answer whether readers expose hidden motivations. E59's benign refusal-policy contrast is addressed in Theme 2 and does not establish an unspoken motive. E76 placebo text can generate safety-related vocabulary, but its incidental domain words are not a calibrated awareness baseline and were not promoted to another hypothesis. The absence of a demonstrated deception signal in this pass is not evidence that deception is absent from the target.

`count_theme08.py` reproduces the aggregate counts in `theme08_counts.json`. The six excerpts above were verified as exact substrings of the sealed public readouts. The E66 0/30 explicit-self-evaluation judgment is a disclosed manual interpretation of the existing positive-code census, not a new sealed or independent judge result.
