# DRAFT — NOT PRE-REGISTERED. Nothing runs from this file. Held until Guiv says go (2026-10-20).

When approved, this text is copied verbatim into BRIEF_R as a dated section **before** any of its compute. Any edit after
approval is a dated Deviation.

## SWAP-P — do readers report a swapped-in rhyme the model ignores? (draft, WS3, 2026-10-20)

**Why.** In SWAP's poetry part, the J-lens swap at the line break never moved the model: no completion took the swapped-in
rhyme (R-S6), and the forced-choice rhyme preference flipped on 0 of 48 items at every layer. Yet the readers' rhyme
report moved toward the swapped-in rhyme on some items: J-lens 6/48 = 0.125 [0.059, 0.247] at L24 and 7/48 = 0.146
[0.072, 0.272] at L28, against random 5/144 and 2/144 (descriptive, swap.md). R-S2 asks whether a reader follows an edit
that the model's answer follows. This asks the complementary question: does a reader report an edit that the model's
answer does **not** follow? A yes means the reader reads the edited state rather than the model's computation from it.

**Items: fresh, never edited or read.** The 50 **pool** items of `x27_wsb_poetry` (`dataset/items_rx.json`, frozen). The
48 test items are excluded because their numbers motivated this section. Same item gate as SWAP Deviation (4): the rhyme
pair is single-token in both spellings. Coverage is reported, and nothing is excluded post hoc.

**Edit and arms: SWAP's, unchanged.** Line-break position; layers {24, 28, 32, 36, 40, 44}; α = 1; s(L) = mean ‖h‖ over
the gated items at that (layer, position), computed **once, in one uninterrupted pass**. A resumed attempt must recompute
nothing: its rows are discarded and the cell is re-run whole, so every arm of an item carries the same s(L). Arms:
d_swap (J-lens readout difference, swapped-in rhyme − true rhyme), d_logit, d_rand0..2 (K = 3 seeded). Every row carries
`code_sha256` (swap.py stamps it since fc6100a).

**Measured.**
- Per item × layer × arm: the model's forced-choice rhyme preference (`prefers_rhyme_true`, `lo_rhyme`) and the greedy
  completion.
- Every reader (J-lens, Oracle lens [community], skip-lens, NLA) scored natively on the rhyme pair from the block-42
  last-token read-back. The NLA must be scored on the rhyme pair: WS4 confirms its phase B passes the pair.

**Item set.** Unmoved items at layer L are those where the model prefers the true rhyme naturally and still prefers it
under d_swap at L (forced choice), **and** the completion does not take the swapped-in rhyme. Each reader is evaluated
on that layer's unmoved items.

**Rule — same shape as R-S2.**
- **R-SP1**: a reader **REPORTS THE SWAPPED-IN RHYME** at layer L iff, on L's unmoved items, its rhyme report crosses
  toward the swapped-in rhyme (natural LO > 0 → edited LO < 0) in **≥ 50%** of them. The random band (the reader's
  cross rate under d_rand0..2 on the same items) is printed beside it.
- **R-SP2**: otherwise the reader is **SWAP-SILENT** at L.
- **Control, reported with every cell (Guiv, 2026-10-20):** real − random cross rate, where random is the per-item mean
  over d_rand0..2, with a paired item bootstrap (1,000 resamples, seed 0). R-SP1 / R-SP2 are stated with it, never
  without it.
- Every reader family has its own row and is never pooled. Every Oracle-lens number carries its checkpoint tier.
- Layers with fewer than 10 unmoved items are reported but flagged.

**Power, stated before the run.** With about 50 unmoved items, a 50% rate has a Wilson half-width of about ±0.13. At the
rates seen on the test items (0.12–0.15), every reader is expected to be SWAP-SILENT under R-SP1. The informative part
is then the control. A paired real − random difference of +0.10 on 50 items has a bootstrap half-width of about ±0.09,
so a difference of that size is detectable, and a smaller one is not.

**Not changed.** R-S1..R-S6 and every reported SWAP number. This section adds rows under its own suffix and reads no
test-item row.

**Cost (estimate, not measured).** One 80 GB pod on WS4's swap.py:
- phase A: 50 items × 31 cells, about 3–5 min at the khop pace of 541 s for 196 items × 43 cells, plus greedy
  completions;
- reader scoring: about 6,200 rows over four readers, about 10–15 min at row 5's pace, plus the NLA load;
- model and reader loads: about 10 min.

Total ≈ 0.5 pod-h ≈ $2–3. It fits a warm pod in the queue after its current job. WS4 runs it, WS3 analyses it, and the
pod claim follows PODS.md rule 6.

**Outputs.** Rows under `cache/g_agreement/r/swap/` with part `poetry_pool`; WS3's analysis in `swap.md` § SWAP-P.
