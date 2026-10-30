## §174 E58. Is bookkeeping computed beneath the workspace on Qwen? (labels and ablation)

**Registered 2026-10-27 04:05 CET. E58a uses labels W-lens has already computed (`9fdea554`) but that the coordinator
has not opened; the category assignment below is made blind to them. E58b is new compute.** **Owners:** W-text
(categories), W-lens (E58a, CPU), W-sae (E58b runner), integrator runs. **Cost:** E58b ≤ 0.75 GPU-h.

**E58a: does J-membership split by kind of information (CPU)?** W-text assigns every row of W1, E36, W12, E49, E56 and
E57 to one category, **from the row's description only, without opening any label, probe, reader or J-lens file**, and
commits the assignment before W-lens joins it to labels: **bookkeeping** (position, count, index, line length, depth,
indentation), **delimiter** (open bracket, quote, string, code block, maths), **syntactic** (part of speech next, tense,
number, clause), **format** (table vs prose, list vs code, language), **content** (topic, sentiment, entity, status).
Rows with probe < 0.85 are excluded. **R-a1:** median J-fraction of bookkeeping + delimiter + syntactic rows is below
that of content rows (Mann–Whitney one-sided p < 0.05), and ≥ 70% of them are OUT-J or DIFFUSE against ≤ 30% of content
rows. **R-a2 (the why, within the map):** across all rows, J-fraction predicts the Oracle lens's unprompted reporting
(point-biserial ρ ≥ 0.4), computed once after E49/E56/E57 readers are analysed.

**E58b: does removing the J-space hurt bookkeeping behaviour (GPU)?** Paper: "sufficiently automatic computations can
proceed beneath it" (line-wrap unchanged by swap). Rows: every frozen row with a continuation pair (E15/E53 structure
rows; E56 tense, line-wrap, language continuation, adjective; E57 rows 7–10) and in-J rows with a definable answer token
(reasoning_bridge, rhyme_plan, antonym_crosslingual, fact_recall). Arms at block 44, applied at every position of the
prompt: (i) none; (ii) project out W-lens's sealed J basis (rank 384); (iii) project out a random rank-384 subspace (5
seeds, `20261027`+i); (iv) project out the top-384 PCA subspace of the row's own dev activations (variance control).
Metric: continuation log-odds (correct − wrong); damage = mean drop from arm (i). **R-b1 (sanity):** on in-J rows, J
damage ≥ 2 × random damage on ≥ 3 of 4. **R-b2:** on bookkeeping/delimiter/syntactic rows, J damage ≤ 1.25 × random
damage on ≥ 70% of rows. Rows where PCA damage < random damage are reported, not excluded. If R-b1 fails, R-b2 is NOT
EVALUABLE. **Prediction:** both hold, i.e. on Qwen the structure our readers miss is computed beneath the workspace,
while in-J reasoning needs it.
**Why both:** E58a asks whether the structure the readers miss sits outside the J-space; E58b asks whether the model
uses that structure without the J-space. Together with E52 R3, this tests the claim "the readers read the workspace;

**§173 E57 clarification 1 (2026-10-27 04:20 CET, answers W-text, before the E57 freeze).** (a) count_gradient reuses
E56's sealed line-wrap implicit and report items unchanged (referenced by seal hash) and adds only the first-letter
question; its label keeps the original count and the expected letter is derived from that count. (b) The disjoint
content-word check applies to value-bearing words only; fixed instructions, scaffolding and a deliberately shared copied
sentence are exempt. (c) category_switch and capacity_list read at a shared delimiter immediately after the last item
(e.g. the comma). capacity_list has no A/B label and no probe: 84 dev + 84 test lists, scored by its count measure only.
(d) New Group A row **two_hop_answer** (paper's spider case, differing answers): "The number of legs on the animal that
spins webs is" vs analogous prompts whose bridge entity has a different answer (ant → 6), read at "is"; it is an in-J
row and gives E58b a sanity row with a definable answer.

**§174 E58 clarification 1 (2026-10-27 04:20 CET, answers W-sae and W-lens, before any E58 fit or score).** (a) E58b's
in-J sanity rows are rhyme_plan, antonym_crosslingual and two_hop_answer (reasoning_bridge has a shared answer by
design, so it is dropped from E58b); R-b1 becomes ≥ 2 of 3. (b) The PCA control (arm iv) is the top-384 PCA of the
**pooled** dev read-point activations of all E58b rows (well over 384 vectors), the same subspace for every row. If the pooled set has fewer than 768 vectors, all dev prompt positions of those rows are pooled instead.
(d) focus_ignore_mention's "none" arm omits X, has no probe target (NOT APPLICABLE), and its readouts are the
mention-rate baseline for both birds and citrus; think/mention/ignore stay balanced birds vs citrus.
(c) E58a's R-a1 is evaluated once, on all six banks, after E56/E57 labels and probe gates exist; no partial evaluation
on four banks is opened first.

**§174 E58 clarification 2 (2026-10-27 04:25 CET, before any E58 fit or score).** E58b adds a DESCRIPTIVE
**shallow-content group** (paper: factual recall and sentiment classification survive J-space ablation although their
content is in the workspace). No existing E36 content row has frozen continuation pairs (E15 registered none for
sentiment), so the group is: (i) E56 **fact_recall**, answer tokens as its continuation pair; (ii) a new E57 row 14,
**sentiment_judgement** (W-text): a short review, then "Overall, the review is", A/B = positive vs negative review,
continuation " positive"/" negative" with swap control; same build checks. Reported per row: J damage ÷ random damage
and PCA damage, beside the in-J and bookkeeping groups. Prediction: ≤ 1.25 (survives), while these rows are IN-J and
read by the Oracle lens, i.e. readable ≠ needed. No rule changes; ≤ 5 extra GPU-minutes.

**§167 E51 clarification 2 (2026-10-27 04:20 CET, answers W-sae, before the once-only count).** A bullet is a span
starting at each "- " that follows a real newline or a literal "\n" (or starts the target), running to the next such
marker or the end of the target. Preamble before the first marker is excluded; terminal special-token markers are
stripped; empty bullets are dropped.
bookkeeping lives beneath it".
