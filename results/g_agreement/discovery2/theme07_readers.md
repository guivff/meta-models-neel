# Theme 7 — NLA versus Oracle lens on the same items

These four candidates are hypotheses. The first discovery pass was read first; its overall template differences and unpaired mention-rate comparisons are not treated as new findings. The paired comparisons below use the complete sealed E57 and E73 grids, verified reader identities, existing judge codes, and true labels joined **only in memory**. No private prompt, original item ID, pairing table or per-item truth is released. Examples illustrate readout wording; they are not a table of item correctness.

The unit is one item with one readout from each reader. “Correct” means the existing judge codes `states_value` with the correct value alone; “wrong” means the opposite value alone. Both-values, property-only, exhibits and silent codes contribute neither. The main comparisons restrict to items with a parseable judgment for **both** readers. Counts are descriptive, without new uncertainty intervals or revised sealed verdicts. `theme07_counts.py` and `theme07_aggregates.json` reproduce the aggregate comparisons; E73's label convention was checked against its source scorer (0=A, 1=B). The full E73 grid includes both structural and control cohorts. NLA output is longer on nearly every compared item, so reader identity is confounded with verbosity and output style.

## R1. NLA has a candidate advantage when it names a change or syntactic relation that Oracle merely continues

**Hypothesis:** NLA can add useful explicit descriptions of a category change or local syntactic relation on items where Oracle produces plausible continuation fragments.

**Count:** On E57 category-switch, among **82/84** common-parseable item pairs, **23/82** are correct-only for NLA but not Oracle, versus **3/82** for Oracle but not NLA. Both are correct on 36/82. NLA has 59 correct and 5 wrong; Oracle has 39 correct and 13 wrong. The public contrast is colour versus animal at the end of the list, and its probe AUROC is 1.000. On E73 inside-call-arguments versus statement-level, the corresponding exclusive counts are **22/157 NLA versus 7/157 Oracle**; both are correct on 4/157. NLA has 26 correct and 6 wrong; Oracle has 11 correct and 7 wrong. There are 43/200 pairs excluded by the common-parseable requirement in that E73 row.

**Banks / both readers:** E57 category-switch and E73 call-argument state. This is a measured NLA advantage on these rows, not a general ranking. NLA has more whitespace-delimited words in **82/82** and **157/157** retained pairs respectively. Some judge evidence credits a reconstructed code fragment rather than an explicit relation, so a human audit may change the comparison.

**Three verbatim examples (individual readouts; pairings are not published):**

- E57 NLA `bb0d71938bf3e29fca157f5ae1f8e83f`: `"beige," is the final token — a color word appearing after the animal list, suggesting a category shift or continuation of a vocabulary list; the comma signals more items follow.`
- E57 NLA `fe097ffe8d8a031744620ee9ad3e2554`: `The list mixes animals with an unexpected non-animal term "purple," signaling a shift or category break, suggesting the next tokens may introduce a new category (e.g., colors, adjectives, or unrelated vocabulary items).`
- E73 Oracle `ea96239bc9aa8fe561731e7646849a59`: `- , content_object=content_object) elif event == signals.post_save:`

**Novelty:** A paired, correctness-aware refinement of the first pass's observation that NLA names genre or structure while Oracle continues text. The exclusive-item counts establish where the difference occurs under the frozen scoring rule; they do not establish that every part of NLA's reconstructed quotation is faithful.

**New-item test:** Create fresh list endings and code prefixes with identical terminal tokens, independently varying category changes and call-argument status. Match output budgets, then have blinded humans separately score explicit relation statements, faithful code reconstruction and merely exhibited continuation. Test whether the NLA advantage survives at equal text length and on new documents, rather than relying on the existing judge's treatment of quoted fragments.

## R2. The apparent NLA advantage on code-versus-prose is strongly entangled with whether Oracle can be judged

**Hypothesis:** Some large reader gaps measure the judge's access to the reader's format as much as the reader's information.

**Count:** In E73 code-versus-prose, NLA has **191/200** `states_value` judgments and Oracle **91/200**, reproducing the first-pass contrast. However, **101/200 Oracle judgments are UNPARSEABLE**, compared with **6/200 NLA**. Only **94/200** pairs are parseable for both. On that common set, NLA is correct-only on **87/94**, Oracle on **84/94**; NLA-only correctness occurs on **9/94** and Oracle-only on **6/94**. NLA has 6 wrong-only statements versus Oracle's 2, giving signed numerators **81/94 versus 82/94**. Of the 106 excluded pairs, 100 are Oracle-unparseable/NLA-kept, 5 the reverse and 1 both unparseable.

This conditional near-tie does **not** show equal capability on the discarded items: common-parseable selection may preferentially retain easier Oracle cases. It does show that the raw 100-statement gap cannot be interpreted as a 100-item information advantage without addressing judgment failure.

**Banks / both readers:** E73 code/prose only. The same-item analysis includes both readers and makes no inference about GLM E66. NLA is longer in 94/94 retained pairs.

**Three verbatim examples:** The Oracle excerpts below have public UNPARSEABLE judgments; the NLA excerpt has a public `states_value` code. These are judge statuses, not released true labels or itemwise pairings.

- Oracle `838492c0e7b11f7f6e77a0852c294308`: `- 00$ | 1,100,0`
- NLA `4df0fdca46aed871f30ed5d961b079dc`: `Technical API documentation pattern: Python/Spark-like function signatures with parameter descriptions, following consistent structured format.`
- Oracle `38caaf631e4e78457cfa505027dd119d`: `- 点 (x, y) in the mesh grid its class. We use a color map to visualize the`

**Novelty:** New resolution of the first pass's unpaired 191-versus-91 difference, using exact item pairing and private truth only in aggregates. The first pass noticed unparseability but did not quantify the common-set comparison.

**New-item test:** Use fresh code and prose items and an independently validated judge with an explicit category for fragments that exhibit, but do not name, genre. Blindly human-adjudicate a stratified sample including every unparseable machine judgment. Report all-item rates, common-judged rates and reader-specific missingness, without treating failed parsing as silence. Test whether a reader-format effect remains after the adjudication protocol is held fixed.

## R3. NLA can add correct syntax statements while adding enough wrong statements to erase the gain

**Hypothesis:** A verbose grammatical template raises NLA's statement recall while biasing it toward one syntactic status.

**Count:** E57 clause-pending has **81/84** common-parseable pairs. NLA is correct-only on **40/81** and Oracle on **22/81**; their exclusive counts are **21/81 NLA versus 3/81 Oracle**, with 19/81 both correct. But NLA is wrong-only on **21/81**, versus **1/81 Oracle**. Thus the signed numerator is **19/81 NLA versus 21/81 Oracle** on precisely the same items. Of NLA's 61 single-value statements, **60/61** are coded as a main clause still being owed; Oracle has 20/23 in that direction. NLA says `Although` in **71/81** and `main clause` in **41/81** readouts, compared with Oracle 43/81 and 2/81. The row's probe AUROC is 1.000.

**Banks / both readers:** E57 clause-pending only. The claimed asymmetry is about NLA's additional statements; both readers are evaluated with the same rubric and common denominator. NLA is longer in 81/81 pairs. This does not imply that the underlying model lacks the syntactic status or that every `Although` occurrence is fabricated.

**Three verbatim examples (individual readouts):**

- NLA `0288c4615428774c4fb84bde1f613e11`: `Contrastive conjunction "Although" signals an adversative clause structure requiring a contrasting main clause to follow, establishing a grammatical template.`
- NLA `08b207a5f9a99483f0208a36aa6c08dc`: `The repetition pattern "Although the weather was cold" → "Although the weather was cold," signals a contrastive conjunction structure requiring a main clause to complete the sentence, likely describing an unexpected outcome or action.`
- Oracle `c0be5143d52c4dc7d28c11883e2f49df`: `- [blank] she managed to finish the marathon. (Complete the sentence starting with "Although`

**Novelty:** New correctness-aware qualification of the first pass's NLA clause-pending mention advantage. More correct statements and more reliable signed reporting are distinct comparisons.

**New-item test:** Build novel minimal pairs in which a main clause is owed or not owed, with several subordinators, unmarked clauses, quotation and conjunction distractors. Preregister balanced accuracy, false-positive rate and signed statement rate alongside recall. Include a condition that prevents quoting the sentence and fixes the explanation budget. The hypothesis predicts an NLA recall advantage coupled to status-specific overcalling; disappearance of the bias on new templates would limit it to the existing prompt family.

## R4. Similar row-level accuracy can conceal substantial same-item complementarity

**Hypothesis:** The two readers can recover different items within a weakly reported row, so average rates understate their potential complementarity.

**Count:** On E57 subject number, among **82/84** common-parseable pairs, Oracle is correct on **21/82** and NLA on **19/82**, but only **6/82** are correct for both. Oracle-only and NLA-only correct counts are **15/82** and **13/82**, making the union **34/82**. This is an unattainable-without-a-selector upper bound, not a demonstrated ensemble result. E73 line length shows a similar descriptive pattern: Oracle correct **30/197**, NLA **29/197**, both **2/197**, exclusive **28/197** and **27/197**, union **57/197**. The error profiles differ: wrong-only counts are Oracle 2 versus NLA 1 on E57 subject number, and Oracle 26 versus NLA 1 on E73 line length.

**Banks / both readers:** E57 subject number (probe .961) and E73 line length. Both readers contribute unique correct-coded cases. The E73 line-length rubric can infer a value from a fragment or claim about completion; the union is therefore conditional on the existing judge and needs semantic auditing.

**Three verbatim examples from E57 (individual readouts):**

- NLA `21324f70220cf4163b91ad060ba0d66a`: `The phrase "The farmer placed the stone near the" sets up a spatial description requiring a location noun (e.g., "field," "house," "path," "tree") to complete the prepositional phrase.`
- Oracle `1473737d7362d4fa4e05f8c4fbafebd4`: `- 彩票 is a clue left by a stranger. The man found a ticket`
- NLA `9fd79813c0e8ec7d6836c5354298e7dc`: `The phrase "The tables obtained by the observer at the" sets up a prepositional phrase requiring a location or time reference (e.g., "sea," "island," "meeting").`

**Novelty:** New paired-item complementarity, unavailable from the first pass's separate per-reader rates. It answers “what can NLA find that Oracle cannot?” at the item level while also showing the reverse direction.

**New-item test:** On fresh balanced subject-number and line-length items, independently adjudicate explicit state claims, then train a reader selector on separate development items using only readout features and disagreement. Freeze the selector before evaluating new test items. Report both the oracle-selector union ceiling and actual selected accuracy, including wrong assertions and abstentions. If no observable feature can select the reliable reader, complementarity alone does not produce a useful monitor.
