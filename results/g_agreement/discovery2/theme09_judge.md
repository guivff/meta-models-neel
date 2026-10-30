## Theme 9 — Judge and detector artefacts

These are hypotheses about measurement, not revised sealed verdicts. I read the first pass before inspecting the complete sealed native grids, their public row definitions and their unchanged codes. The estimates below are **local audit rates in deliberately selected rows**, not an estimate of the judge's error across the sprint. No new judge was called. E49 used a frozen regex rather than the later blind judge, so its problem belongs to the detector, not the judge. `count_theme09.py` reproduces the descriptive counts without executing an original scoring entrypoint.

### J1. A detector can report zero while both readers explicitly attach a type word to the tracked variable

**Hypothesis:** Some apparent complete misses are caused by narrow grammatical matching, especially when a reader says “is now” or “becomes” instead of “is a.” **New relative to the first pass**, which did not audit E49's native detector.

**Count:** E49 `var_type_at_use` has sealed probe AUROC 1.0 and frozen any-value detection **0/84 Oracle and 0/84 NLA**. A transparent search for `x is [now] [a] string/int/integer` or `x becomes [now] [a] string/int/integer` finds **39/84 Oracle and 9/84 NLA, 48/168 combined (28.6%)**. These are candidate false negatives for *type-expression detection*. They are not 48 correct answers: some reconstruct an invented program, refer to an intermediate transformation, or use a conditional. The search is deliberately narrower than all possible type paraphrases and does not estimate recall. The old pattern requires forms such as `x is a string`, `x holds a string` or `type of x is str`; it misses the added adverb and changed verb. All NLA readouts in this E49 cohort were cut at the old 128-token limit.

**Three verbatim readout excerpts (new opaque E49 identifiers):**

- `91b57a1b993d1d7f95086bf1`: `# x is now a string, y is now an int, z is now a string`
- `23f57146ed19d1d4237db65e`: `# x is now a string, y is now an int, z is now a string. Print them in order: x, y,`
- `221d0c29ebe4ba45cbf5671a`: `x becomes string "1", y becomes int 2, z becomes float 3`

**Banks/readers:** demonstrated in E49, both readers; not claimed across other banks. **MATS relevance:** “what do they find and not find”; a measured zero cannot by itself establish semantic silence.

**New-item test:** Freeze a small grammar challenge set crossing `is a`, `is now a`, `becomes`, code comments, quotations, conditionals and negations. Separately label (i) whether a type is mentioned, (ii) whether it is asserted of the current tracked variable, and (iii) whether it is true. Test the original detector and a new blind semantic rubric against two independent human coders. Then acquire genuinely new variable-tracking items and score with the frozen, validated method; do not replace E49's sealed score.

### J2. At the decision rung, answer-format vocabulary can be mistaken for the state being queried

**Hypothesis:** The judge sometimes maps a generic answer letter or an output constraint onto an unrelated property value. **Refinement of first-pass T7/E62 P3**, with full-cohort counts and two additional error mechanisms.

**Count:** Across all five E62 L4 rows, **41/420** readouts are coded `states_value`, all for the public first candidate. A census read of those **41/41** finds no semantic assertion of the row's requested state: **38/41** evidence strings contain the answer letter `A`; **2/41** cite “single-word,” transferring a constraint on the reply to bracket depth or the passage's line length; **1/41** cites entailment as evidence for grammatical tense. This is a provisional audit disagreement rate of **41/41 positive codes**, or **41/420 (9.8%) of the L4 cohort**, not an independently validated error rate. The first pass saw 31/322 and described every hit as answer-letter credit; the complete cohort reveals the broader scope-confusion mechanism. No per-item truth is needed for this audit: the relevant question is whether the public readout asserts either public property value at all.

**Three verbatim readout excerpts:**

- `99573e169dab2b256619cf44a636128f`: `{"label": "A"}`
- `25ab63b70757e67a9eb47adca4eebf45`: `The prompt asks for a **single-word** response`
- `70e346ec02cd012515826557c7f27b21`: `The sentence in the prompt is a direct paraphrase of the hypothesis. Therefore, the premise entails the hypothesis.`

**Banks/readers:** E62, Oracle only; NLA was not run in this bank. The public states are bracket depth, line length, tense, language and subject number, not a generic classifier's label. **MATS relevance:** “what do they find and not find”; decision-rung reporting estimates can contain format credit rather than state reports.

**New-item test:** Build new, counterbalanced decision tasks with arbitrary answer alphabets, reverse their mappings, and include unrelated classifier continuations containing the same letters. Keep each state's two values explicit in the rubric, require evidence to assert that state, and label reply-length versus source-line-length separately. Compare two independent humans with the unchanged and revised rubric on held-out readouts; measure false positives in the unrelated-answer controls and retention of actual state statements.

### J3. A superclass word can receive credit for a narrower target concept

**Hypothesis:** In focus/ignore scoring, a readout about generic fruit can be credited as stating *citrus*, even when no citrus instance or synonym appears. **New relative to the first pass's negation-credit observation.** This concerns semantic specificity, independently of whether negated topic mentions should count.

**Count:** In E57 `focus_ignore`, **6/84 Oracle readouts** are credited for the citrus candidate while the cited evidence says only “list fruits.” These are **6/18 (33.3%) of Oracle's `states_value` codes** in that row, or **6/25 (24.0%)** of the two readers' positive codes combined. Full-text inspection finds no citrus term or instance in these six; the non-citrus distractors do not repair that inference. The same screen yields **0/84 NLA** in E57 `focus_ignore`, **0/252 Oracle and 0/252 NLA** across the other three E57 focus arms, and **0/84 per reader** on E56 `instructed_focus`. Thus it is a small, concentrated failure, not a general reader difference. These are candidate judge false positives; they say nothing about the hidden true concept of the item.

**Three verbatim readout excerpts:**

- `90e21661979e1c7e59389ece2f904877`: `Begin generating a list of fruits.`
- `e7e2af9c0a76d3f78f2e615104e758f7`: `I will ignore the distraction and fulfill the request to list fruits.`
- `5d2c5ae2fd6f6d6487972746331c9bfd`: `Begin listing fruits.`

**Banks/readers:** observed in E57 Oracle; absent under the stated screen for E57 NLA and E56 both readers. **MATS relevance:** “what do they find and not find,” and unverbalised motivations: coarse topic evidence should not be promoted into a specific internal focus claim.

**New-item test:** Cross specific targets and superclasses on new prompts—citrus/fruit, birds/animals, and corresponding non-members—while independently varying `think`, `do not think`, `mention` and neutral wording. Include readouts that name only the superclass. Freeze a taxonomy-aware rubric that credits synonyms and actual members but not superclasses, then obtain blinded human judgments and estimate each error type separately from polarity errors.

### Interpretation limits

The three selected audits have different units: a detector-expression screen, a census of positive judge codes at one rung, and a specific superclass confusion. Their numerators must not be added into a global error rate. The first pass's both-values inflation and negation-credit concerns remain plausible, but I did not promote them to additional candidates without a new systematic adjudication. In particular, a rubric that measures *topic mention* can reasonably count a negated mention; the mistake would be interpreting that count as the model's belief or active intention. This report leaves every original code and verdict intact.
