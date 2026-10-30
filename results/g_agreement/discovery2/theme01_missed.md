# Theme 1 — Missed despite decodable

This is a hypothesis-generating second view, not a new sealed analysis. The first pass was read before inspecting these sources. Complete sealed populations were used, rather than the first pass's incomplete extraction: E49 2,688 native readouts, E56 2,256 including 72 injection readouts, E57 3,360, E59 1,008, E62 2,520 including 420 evaluation readouts. The comparisons below use the named text rows only. `S` means (correct-only statements − wrong-only statements)/parseable readouts; it is not a literal silence rate. E49 uses its frozen explicit-statement regex, later banks their sealed judge. No per-item truth is disclosed.

Analysis seals and all their listed file hashes were checked for E49, E56, E57, E59 and E62. Public blind packet, judgment and private-map hashes were checked before the joins. All reconstructed E59/E62 signed rates match the sealed aggregate rates exactly. The shared `evidence_native.py` loader only reads these allowlisted sealed sources; optional private fields remain in memory. E49 asked files have scores, not generated text: their apparent empty texts in the first pass should not be counted as readouts.

## 1. A candidate dividing line is the kind of information: a grammatical requirement versus a numerical coordinate

**Hypothesis:** Both readers can report a dependency that constrains the next continuation while failing to report a numerical coordinate within an otherwise recognized structure.

**Count:** In E57, **6/6 reader × row cells** for clause pending, loop direction and subject number have sealed `S ≥ .20`; **0/8 cells** for indentation level, bracket nesting depth, page-range first digit and implicit line length reach .20. Every included row passes probe ≥ .90: subject number .961, all others 1.000. This is a post-hoc taxonomy, not an independent significance test.

| Public row contrast | Oracle correct / wrong / parseable | NLA correct / wrong / parseable |
|---|---:|---:|
| Main clause owed / not owed | 22 / 1 / 81 | 43 / 21 / 84 |
| Decrementing / incrementing loop | 38 / 3 / 82 | 45 / 0 / 80 |
| Singular / plural subject | 21 / 2 / 82 | 20 / 1 / 84 |
| 4 / 12 indentation spaces | 1 / 2 / 84 | 0 / 0 / 84 |
| 1 / 3 unclosed brackets | 5 / 4 / 73 | 15 / 3 / 84 |
| Page-range first-digit alternatives | 11 / 18 / 84 | 10 / 2 / 84 |
| Short / long current line | 0 / 1 / 84 | 1 / 2 / 84 |

Literal silence is narrower: NLA indentation is **0/84 value statements and 84/84 silent**, while E62's explicit instruction to track line length still gives Oracle **0/84 value statements, 84/84 silent**, with probe 1.000. E56 implicit line length similarly has Oracle **0/83 parseable value statements**. Other numerical cells sometimes state a value, often wrongly; they are not “never stated.” Section-header recognition is an important exception to a complete binary taxonomy: many mentions coexist with low signed correctness.

Three verbatim readout excerpts:

- E57, NLA, `9c6be4f375cd80cdc2a86da9f68b20cd`, judge `silent`: “Python code snippet pattern with nested `while` loops and `pass` statements, establishing a repetitive structural style.”
- E57, NLA, `0c7967d9202329a02f13ebc49158a1a6`, judge `silent`: “The final token "[[6," opens a nested list literal mid-entry,”
- E62, Oracle, `7a33e3866c0d18cb82a85369fbe2535a`, judge `silent`: “- /notes from the meeting. Here is the transcript with embedded notes”

**Banks / both readers:** Quantified contrast in E57 for both; numerical nonreporting also in E56 for both at low signed rates and E62 for Oracle only (NLA not run). **Novelty:** Refines the first pass's “formatting-only” category using truth and probes. Low-level syntax itself is not uniformly missed: pending clauses, loop direction and agreement survive.

**New-item test:** Preregister a crossed bank with continuation-relevant grammatical dependencies and numerical coordinates, matched for prefix length, delimiter density and explicit cue. Include numerical states whose next output must depend on them and grammatical states whose next token is held constant. Use human-adjudicated value assertions and new vocabulary; test the interaction between information type and immediate continuation relevance, with probe ≥ .90 verified separately.

## 2. A local concept can be readable while its relationship to an earlier passage or side instruction is missed

**Hypothesis:** The readers preserve locally relevant content better than the relationship “a different language occurred earlier” or “this side concept should remain in focus.”

**Count:** On E56, **4/4 reader × row cells** for anomaly state and instructed focus have `S ≤ .036`, although the probes are 1.000 and .976. On the local language-continuation and factual-recall controls, **4/4 cells** have `S ≥ .667` with probe 1.000.

| Public row contrast | Oracle correct / wrong / parseable | NLA correct / wrong / parseable |
|---|---:|---:|
| Earlier foreign sentence / no foreign sentence | 15 / 19 / 78 | 6 / 4 / 84 |
| Focus on citrus / birds while copying unrelated text | 4 / 1 / 84 | 3 / 1 / 84 |
| Current French / German passage | 53 / 3 / 75 | 65 / 0 / 84 |
| Paris / Lima factual completion | 65 / 0 / 84 | 61 / 0 / 84 |

The anomaly row is not simply absent vocabulary: Oracle has **34/78 value statements**, but wrong-only statements exceed correct-only ones. Instructed focus is closer to silence: **155/168** readouts are judge-coded silent across readers. Hence “never stated” conflates omission with a failure to bind what is said to the actual state.

Three verbatim excerpts:

- E56, NLA, `98a27e96b0805b69055bd9fb6842e98c`, anomaly, judge `silent`: “Thematic consistency around legal/administrative actions and physical objects, suggesting continuation of similar office-related nouns and verbs.”
- E56, Oracle, `e1d4a0223fee52607a49db1f48df5485`, anomaly, judge `silent`: “- /file. She opened the folder”
- E56, NLA, `840270c979655362da216608ce47032b`, instructed focus, judge `silent`: “Instruction-following task format: the prompt asks to repeat a specific sentence verbatim, establishing a strict reproduction constraint.”

**Banks / both readers:** E56, both. E49's branch and moved-container rows are compatible with the broader binding hypothesis, but their different conservative regex is not pooled here. **Novelty:** New probe- and correctness-grounded contrast. It cuts across “computed versus read-off”: the forgotten side instruction was explicitly supplied, whereas the correctly reported capital can require recall.

**New-item test:** Put the same language or concept at zero, one, four and eight sentences before a matched read token, factorially varying whether the reader should report its identity, its occurrence, or its relationship to a later instruction. Counterbalance content and position, include recent distractors, and score identity separately from relational status. Use fresh items and a held-out human rubric.

## 3. Asking for a property can redirect the NLA toward describing the question and away from its answer

**Hypothesis:** The NLA's failure is partly a change in what its explanation is about when the read position moves to a question, rather than a failure to encode the original property.

**Count:** In E56, **2/4 implicit→asked/report twin pairs** lose signed accuracy for NLA, versus **1/4 for Oracle**; all eight row probes are ≥ .974. On the adjective/noun pair, NLA correct-only statements fall **40/84 → 2/84**, while property-without-value codes rise **18/84 → 60/84**. Both-values statements rise **7/84 → 16/84**. On French/German, NLA `S` falls .774→.393 while Oracle rises .667→1.000. Tense improves for both; line length remains weak for both.

Three verbatim excerpts, all E56 NLA and judge `names_property_without_value`:

- `ff1667317f41fed7af43eadc21ddf6c7`: “Q&A format established: a sentence is given as context, followed by a question about the next word's part of speech, expecting a direct answer.”
- `0ade8cbb17019134d391aff98ecde85b`: “Q&A format established: a sentence is given as context, followed by a direct question about the next word's part of speech, expecting a short answer.”
- `7ebe023d01e7d51e76cffb80c7552bda`: “Q&A format pattern: alternating "text" and "question" blocks establish a classification task structure, expecting a direct answer.”

**Banks / both readers:** E56; reader-specific direction of effect, not a universal loss. **Novelty:** First pass noticed the adjective reversal, but did not have the complete population or correctness. The new distinction is loss of single correct answers into property descriptions and alternatives, despite a high probe score.

**New-item test:** On fresh matched passages, independently vary the presence of a question and the position sampled (original token versus question mark), with a neutral suffix of equal length. Freeze a rubric distinguishing property naming, alternatives, and committed answers. Test whether NLA answer loss is mediated by the move to the question's final token; include language and tense to test whether the effect depends on property type.

## 4. The most absolute “never stated” entries require a detector audit before supporting a taxonomy

**Hypothesis:** Some apparently decodable-but-unspoken state is actually spoken in wording the frozen detector misses.

**Count:** E49's sealed regex records **0/84 any-value mentions for each reader** on variable type, with probe 1.000. A deliberately narrow diagnostic search nevertheless finds explicit `x is/becomes [now] [a] string/int/integer` wording in **39/84 Oracle and 9/84 NLA readouts (48/168 total)**. These are candidate detector false negatives, not 48 correct state reports: the readouts can invent assignments, and the NLA cohort was truncated at 128 tokens. The frozen scorer accepts “x is a string” but not “x is now a string” or “x becomes string.” No sealed result was altered.

Three verbatim excerpts:

- E49, Oracle, `91b57a1b993d1d7f95086bf1`: “# x is now a string, y is now an int, z is now a string”
- E49, Oracle, `23f57146ed19d1d4237db65e`: “since x is now string,”
- E49, NLA, `221d0c29ebe4ba45cbf5671a`: “x becomes string "1", y becomes int 2, z becomes float 3, then y and z swap”

**Banks / both readers:** E49, both. **Novelty:** New audit correction to how the first pass and sealed regex summaries can be interpreted; theme 9 should own the broader judge-audit conclusion. This prevents the taxonomy from treating a detector's zero as proof of semantic absence.

**New-item test:** Before new captures, freeze a paraphrase-complete statement rubric and a hand-labelled validation set including “now,” “becomes,” and omitted articles. Score generated readouts blindly for (a) explicit type attribution, (b) referent binding and (c) correctness, separately. Report detector recall as well as state accuracy.

## Scope limits

No taxonomy here establishes unverbalised motivations or evaluation awareness. A high probe score only establishes linear decodability under that bank's scoring convention. E57 focus-ignore, focus-think, cross-lingual antonyms, multi-token entities and two-hop answers do not meet the ≥ .90 probe threshold as sealed, and were excluded from the taxonomy; no sign flips were applied. E59's decline row also fails that threshold. E62 subject-number L1/L2 do not pass it. E75 is an aggregate predictor, not a new bank of native texts, so it supplies no verbatim examples here. This theme directly informs “what do they find and not find”; the fourth candidate also constrains claims about hallucination detection.
