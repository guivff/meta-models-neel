## §100 W12. Sentence and paragraph structure rows

Registered 2026-10-24 04:15 CEST, before any item is built. Motivated by Neel's 12 October remark that Camila and
Achim found the NLA "much better at capturing structural information about the text… sentence structure and paragraph
structure", which W1 covers only partly (sentence count, parentheses, quotes).

**Owner:** W-core (items and analysis); the integrator runs it. **Cap:** min(1.5F + 360, 2,400) s; at most 0.8 GPU-h
including capture.

**Rows (binary; value A / value B; read at the final token of the prefix):**
1. `syntax_role`: the current noun is the grammatical subject / the object of its clause (same noun, word order and
   voice varied by family).
2. `sentence_type`: the current sentence is a question / a statement, with the form already decided by the prefix
   ("Did the…" vs "The… did").
3. `sentence_position`: within the first 3 words of the sentence / after word 12.
4. `paragraph_index`: in the first paragraph / in the third or later paragraph (blank-line separated).
5. `paragraph_start`: in the first sentence of a paragraph / later in the paragraph.
6. `clause_embedding`: in the main clause / inside an unclosed relative clause ("the clerk who…").

**Amendment allowed before the freeze only:** if Camila names the features she and Achim saw before the items are
frozen, up to three rows above may be swapped for hers, with a dated note. After the freeze, no row changes.

**Design.** As W1 exactly: 12 authored template families per row (6 dev, 6 test), 42 items per value per split, exact
length matching, one domain label `syntax`, classes assigned in the freeze file before capture. Same readers and sites
(Oracle 44, NLA 42, J 44, logit 44), two frozen phrasing pairs per reader, the same probe ceiling and gates
(probe ≥ 0.85, mismatched AUROC ≤ 0.60), the same 2,000-sample template-cluster bootstrap. Asked scoring only; no free
readouts.

**Prediction.** Probe ≥ 0.95 on all six. Oracle lens near chance (≤ 0.60) on `syntax_role`, `sentence_position`,
`paragraph_index`, `paragraph_start` and `clause_embedding`, and higher on `sentence_type` (questions are describable).
NLA in between, above the Oracle lens on most rows, which would put a number on Camila and Achim's observation.

**What would surprise us:** the Oracle lens matching the NLA on sentence and paragraph rows. Then the blind spot is
narrower than "text structure" (local state like brackets and positions, not syntax).
