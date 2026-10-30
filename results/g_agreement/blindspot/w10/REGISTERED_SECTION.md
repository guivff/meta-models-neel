## §86 W10. Distal operating mode under identical local text (pre-registered 2026-10-23 15:40 CEST, before any item is built)

**Owner:** W-core builds the items and runs the analysis; the integrator operates the pod. **Cap:** min(1.5F + 360, 3,600) s
of science (at most 1.0 GPU-h), with a 1,500 s setup allowance outside it (three models); judge ≤ $3. One attempt, plus
one retry only after a pure infrastructure failure with no science. **Target:** Saturday.

**Hypothesis.** The Oracle lens inverts a reconstructor trained to map *text* to the average activation. Under
*identical* local text, the reconstructor's target is the same whatever an earlier instruction said, so the Oracle lens
should be blind to the model's current **operating mode** (the instruction it is following). The NLA (exact
reconstruction) and a linear probe should not be blind to it.

**Rows (frozen now).** There are 7 modes. Each instruction pair is token-length-matched exactly:
1. answer language (English / French);
2. register (formal / casual);
3. audience (a child / an expert);
4. output format (JSON / prose);
5. length (terse / detailed);
6. persona (pirate / neutral assistant);
7. topic constraint ("never mention animals" / no constraint).

Each mode is tested at 2 distances between the instruction and the read position: **near** (≈ 50 tokens of neutral
filler) and **far** (≥ 400 tokens). That gives 14 binary rows. Row class: `mode`.

**Carrier.**
- The prompt is: system or user instruction (mode value A or B), then neutral filler of fixed length, then
  "Copy the following passage exactly:" plus a passage.
- The assistant turn teacher-forces the start of the passage. The read position is a fixed token index inside it.
- **All tokens except the instruction span are identical across the two values** (a test checks this).
- Each passage appears once with each value, so labels are balanced within every cluster.

**Size.** 120 items per row (60 per value), from ≥ 12 passage clusters. Dev and test are split by cluster, and rules are
evaluated on test.

**Arms.**
- Asked paired log-odds for the Oracle lens (block 44), the NLA (block 42) and the J-lens (block 44), using W1's
  scorer with 2 frozen phrasing pairs per mode.
- Probe ceiling: grouped-CV logistic probe at blocks 42 and 44.
- **Random-donor gate:** each item's activation replaced by one from the same row and cluster, with the donor's value
  drawn by hash, regardless of its own value. Because labels are balanced within clusters, a reader that uses only the
  activation scores ≈ 0.5 here.

**Gates, per reader and row.**
- Probe ≥ 0.85.
- Random-donor AUROC within [0.40, 0.60].
- **Mode is active:** on 20 dev items per row, the model's own *free* continuation (greedy, 48 tokens, no teacher
  forcing) follows the instruction in ≥ 70% of items. A blinded judge decides, with a frozen prompt; language and JSON
  are checked by script. A row that fails is NOT EVALUABLE, because the model isn't using the mode.

**Primary rules.**
- **H1 (Oracle lens blind to mode):** the Oracle lens is ≤ probe − 0.25 on ≥ 75% of evaluable mode rows → CONFIRMED.
- **H2 (NLA reads more mode than the Oracle lens):** NLA − Oracle ≥ 0.10, with a paired cluster-bootstrap CI above 0,
  on ≥ 50% of evaluable mode rows → CONFIRMED.

**Secondary (descriptive).**
- Far-minus-near difference in the (probe − Oracle) gap.
- The J-lens.
- Each phrasing pair separately.
- **Surprisal rows:** 2 extra rows (prose and Python, from W1's frozen bank text), labelled top vs bottom tercile of
  the model's own surprisal of the current token, with the same arms and gates. Reported descriptively.

**Open dependency.** The reconstructor's text window (to ask Camila). If it sees the whole prefix, the prediction is
"averaged out" rather than "blind by construction". The rules are unchanged either way, and the write-up states which
applies.

**Science clock** starts at the first science step. Scores are sealed before the label join, and no sign is ever flipped.
Results go to `results/g_agreement/blindspot/w10/`.
