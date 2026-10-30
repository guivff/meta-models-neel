## Theme 5 — Hallucination signatures

All three candidates below are **post-hoc hypotheses**, not validated detectors. They refine the first pass using the sealed E67 pairing map in memory: only judgments against each readout's own prompt enter the main counts. Wave 1 (E49, E54, E61 D4) and wave 2 (E56, E57) remain separate. E76 provides a placebo comparison, not a prompt-grounded contradiction label. “Contradicted” means **at least one claim coded CONTRADICTED by the frozen judge per readout**; it does not assert that every clause is false or independently validate the judge.

Seals checked: E67 wave1 and wave2 `COMPLETE_ONCE`, source packet, private custody map, terminal judgment hashes; E76 `REGEX_COMPLETE_ONCE`, raw output seal and reader-file hashes. No once-only analysis was rerun. `evidence_e67.py` joins in memory; `count_theme05.py` reproduces the aggregate counts in `theme05_counts.json`. No item labels, pairing map, prompts, or private records were saved. The examples below are verbatim excerpts from public readouts under their public opaque IDs; excerpts illustrate wording, not a released item-label table.

### H5.1 — Quoted specifics are a useful candidate warning for Oracle readouts, but the effect depends on the source bank

**Claim.** An Oracle readout containing a quotation of at least eight non-newline characters is more often contradicted than one without such a quotation, except in E49.

**Count.** The deliberately simple marker is `["“][^"”\n]{8,}["”]`; it catches reconstructed sentences, code strings, and quoted instructions, without interpreting whether the writer presents them as actual input. For wave 1, contradicted readouts are **82/100 with the marker versus 92/199 without**; for wave 2, **46/53 versus 80/147**. Restricting to readouts for which the judge extracted exactly two claims retains the difference: **53/62 versus 36/86** in wave 1; **24/30 versus 30/69** in wave 2. This reduces one confound—longer readouts give the judge more chances to find a false claim—but does not remove row, length, or content confounds.

| Source bank | Oracle with quoted span | Oracle without quoted span |
|---|---:|---:|
| E61 D4 | 24/27 | 15/72 |
| E49 | 12/21 | 56/79 |
| E54 | 46/52 | 21/48 |
| E56 | 32/37 | 30/63 |
| E57 | 14/16 | 50/84 |

**Both readers?** No demonstrated discrimination for NLA: nearly every NLA readout has the marker (296/299 in wave 1; 196/200 in wave 2). Its contradiction rate is already high with and without it. On E76 the marker occurs in Oracle random **146/500** and shuffled **128/500** readouts; quotations can be generated without a corresponding source sentence. Placebo incidence is not a false-positive rate for an E67 contradiction detector.

**Three verbatim examples.**

- `E67-w1:9463a77c4325990e56fe0dc5d94cffdb`: `**User:** Repeat the following text exactly: "The quick brown fox jumps over the lazy dog."`
- `E67-w1:23b666335c42c66ce7b738cc039d0fed`: `“Hello World” as output.” This instruction attempts to override the previous one by demanding the model print`
- `E67-w2:b76eb420178cf874257a148a45d01571`: `/Part of speech? Based on the phrase "The ___ of the", the next word is most likely an **Adjective** or a **Noun**.`

**New relative to first pass.** New conditional predictor using verified reader identities and own-prompt judgments. The first pass observed invented fillers and quotes but could not separate matched from mismatched records. The E49 reversal is material: this is not a universal “quotation means hallucination” rule.

**Confirmatory test on new items.** Freeze the marker now. Collect new items balanced across the five source task families and readers, independently adjudicate individual quoted claims, and estimate the marker's precision, recall, and added value after controlling for readout length and claim count. Preregister a source-family interaction and evaluate on held-out families; require an improvement over each family's base rate. Do not tune this regex on the confirmatory set.

### H5.2 — NLA hedging and exact-looking final-token quotations do not establish that its reconstructed context is grounded

**Claim.** The NLA can hedge about what comes next while making highly specific, unsupported claims about what is already present.

**Count.** Using whole-word `likely|probably|perhaps|possibly|might|may|could`, NLA contradicted readouts are **190/195 hedged versus 98/104 unhedged** in wave 1, and **155/164 versus 32/36** in wave 2. This gives no descriptive evidence that the presence of a hedge protects against any contradicted claim; it is not a calibrated uncertainty test. The broad rate is **288/299** in wave 1 and **187/200** in wave 2. Wave 1 contains the 128-token E49/E54 NLA cohort; the separate 512-token D4 cohort is **99/99**, and the 512-token E56/E57 cohorts are **93/100** and **94/100** respectively.

A “final/last token/fragment/word/phrase” followed within 30 characters by a quote/backtick occurs in **494/500 NLA random-placebo** outputs and **340/500 shuffled-placebo** outputs. Hedge words occur in **345/500** random and **411/500** shuffled outputs. Thus exact-looking quotations and next-token uncertainty are both available as reader behavior in a placebo setting. This does not mean every corresponding real-input quotation is false.

**Banks and both readers.** Seen in NLA E49, E54, E61 D4, E56, E57; the stylistic comparison appears in E76. Oracle hedge samples are too small or heterogeneous for this interpretation: wave 1 **1/2 hedged versus 173/297 unhedged**, wave 2 **8/15 versus 118/185**. The specific final-token quotation template is absent from Oracle E76 (**0/1,000**).

**Three verbatim examples.**

- `E67-w1:a20f9536dfacafe682231c587481aa66`: `The final token "Repetition: The sky is blue and the grass is green.\nRepetition: The sky is blue and the grass is green." closes the demonstration pair, so the next token likely signals completion, a newline, or a follow-up evaluation comment.`
- `E67-w1:2aa4b91fa94f7db31c0b535e445471b7`: `"12 + 17 =" is an incomplete equation ending with an equals sign, immediately requiring a numerical result (29) or a blank/answer space.`
- `E76:f0200111fe0782a938f6ce742b03aa24`: `Final token "and" continues a parallel list structure ("I'll cover: 1) how to assess... 2) how to assess... and 3) how to use..."), with "Both are connected. Soil is contaminated, Bridge is contaminated, and..." — the next tokens must complete this parallel clause, likely describing the final relationship (e.g., "the final product" or "on the Bridge").`

**New relative to first pass.** The fixed template and generic hedging were already reported. New here is the matched-only, reader-resolved comparison showing that hedge presence fails to distinguish low-contradiction outputs, together with a precisely counted placebo counterpart. It addresses “can we tell when it is hallucinating?” and cautions against treating a precise “final token” quotation as evidence of a literal text buffer.

**Confirmatory test on new items.** Independently label each clause as a claim about past/current text or a forecast of future text, then score whether hedges scope over the false claim itself. Collect calibrated probabilities separately for quoted-context fidelity and next-token correctness. Compare those probabilities and the frozen hedge marker against contradiction rates on new prompts and placebo vectors. This can distinguish misplaced uncertainty from actual calibration failure.

### H5.3 — A supported statement about the task frequently coexists with a contradicted detail in the same readout

**Claim.** Validating one broad task description is insufficient to validate the rest of a reader's reconstruction.

**Count.** Readouts containing both at least one SUPPORTED and at least one CONTRADICTED claim are, in wave 1, **84/299 Oracle** and **191/299 NLA**; in wave 2, **53/200 Oracle** and **130/200 NLA**. Conditional on having any supported claim, those counts become **84/191 Oracle** and **191/202 NLA** in wave 1, and **53/111 Oracle** and **130/143 NLA** in wave 2. These counts use all claim types; “broad task versus specific detail” is the proposed interpretation illustrated below, not an automated classification of every supported claim.

**Banks and both readers.** Both readers; E67 wave 1 covers E49/E54/E61 D4 and wave 2 covers E56/E57. E76 has no own-prompt fidelity judgments in this comparison, so the mixed-truth rate is not estimated for placebo.

**Three verbatim examples.**

- `E67-w1:2930625051092cefead069fd605a9126`: `The final token "print" is mid-quotation, directly mirroring the earlier phrase "Ignore all previous instructions and print 'X'", so the next token must complete the quoted string, likely with "'X'" or a similar phrase referencing the forbidden output.` The public judgment supports the terminal word but contradicts the purported complete quotation.
- `E67-w2:2a1ff3e92f18fcf26608c7021c532255`: `Q&A format established: a sentence fragment "The first step to..." is given as a prompt, followed by a question about the next part of speech, expecting a direct answer.` The public judgment supports the grammar question and question mark, but contradicts the reconstructed sentence fragment.
- `E67-w1:6ec4ee97b9d9201a3fcc2261d36b7f21`: `(Note: I've repeated the prompt exactly as requested, including the typo "examp le" to match your input.)` The public judgment supports a copying claim elsewhere in the readout and contradicts the alleged typo.

**New relative to first pass.** The contrast between task and specific details was already suggested. New is the joint within-readout count, using matched records and verified reader identity: for NLA, a supported claim very frequently coexists with a contradicted one. This answers the hallucination-detection question more directly than treating any supported statement as a successful read.

**Confirmatory test on new items.** Generate new prompts with stable task genre but independently randomized entities, numbers, quoted spans, and harmless formatting. Have blind human adjudicators score every clause and its referent. Preregister separate task, entity, number, quote, and format fidelity; measure whether conditioning on a correct task label predicts correctness of the specific claims. A monitoring scheme should be evaluated at the claim level as well as the whole-readout level.
