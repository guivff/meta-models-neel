## §215 E106. Can the bookkeeping blind spot be fixed cheaply, and what does the answer say about its cause? (2026-10-29 02:55 CET, before any E106 data or output)

**Why.** E100 (b8e2c8202) shows the Oracle lens stays silent on bookkeeping state even when the whole activation is
transplanted in, so the failure is in the decoder, not the representation. E51 shows the lens's distillation teacher
almost never names structure (147 per 10^4 bullets). The earlier asked arms (W1, E56) show that asking the lens
directly does not rescue structure rows. Two accounts remain: (a) a **training-data gap**, which a little supervision
should close, or (b) a **decoder limit**, where the reader cannot verbalise this class of state regardless of
supervision. A clear answer either way is useful, and (a) would mean readers can be repaired cheaply.

**CONFIRMATORY for R-FX1; R-FX0 and R-FX2 DESCRIPTIVE.** Owners: W-train (free since E102), integrator I-4,
adapter W-mech2 with synthetic tests before output. Reviewer R-4.

**Rows.** *Train rows (missed):* E57 nesting_depth, indent_level, page_range_digit (dev splits only). *Held-out missed
rows:* E56 line_length; E49 container_after_move, holder_after_handovers, branch_taken, var_type_at_use (test items, 84
each where available). *Replay/content rows:* E59 format_plan, language_plan; E56 fact_recall, tense_implicit (dev for
replay, test for the no-degradation check). No test item of any row enters training.

**Arm P (prompt-side, no training; both readers; ≤ 0.5 GPU-h).** The reader's native prompt is prefixed with 3 fixed
in-context examples of structural descriptions drawn from W-text's E102 paraphrase templates (dev values only), then
the standard instruction. One greedy readout per test item on the train rows' test items and the held-out rows.
**R-FX0 (descriptive):** per row, S under arm P versus the sealed native S.

**Arm T (training; NLA first, Oracle lens only if its E102 gate issue is resolved).** Feasibility gate by Thu 14:00
CET: the NLA adapter loads, LoRA rank 16 attaches, 10 steps run, and 3 sealed greedy readouts reproduce byte-for-byte
before training. If the gate fails, arm T is "not run (feasibility)" and arm P stands alone. Data: the three train
rows' dev activations at the reader's native block, paired with E102's frozen template descriptions; an equal number of
replay dev items from the four content rows paired with the reader's own sealed readouts. Recipe committed before
training: lr 1e-4, 300 steps, batch 16, seed 20261029, no search. Evaluate original vs retrained reader with one greedy
readout per item on: train rows' test items, held-out missed rows, content rows' test items, and 200 placebo vectors
(E76 generator, seed 20261031). Judging: E56 route, bank E106, ≤ USD 15.

**R-FX1 (the blind spot is a training-data gap):** on ≥ 2 of 3 train rows' test items, S(retrained) − S(original)
≥ 0.30 with item-bootstrap lower bound > 0, **and** on content rows S(retrained) ≥ S(original) − 0.10 on ≥ 3 of 4
(no degradation), **and** placebo S(retrained) ≤ 0.20 (it did not learn to say the value regardless of input).
**R-FX2 (descriptive, generalisation):** the same difference on the held-out missed rows; ≥ 0.20 on ≥ 2 of 5 is
reported as "the repair transfers across structural state types".
**Falsifier (decoder limit):** S(retrained) − S(original) ≤ 0.10 on all 3 train rows with the recipe having run (loss
decreased), or placebo S(retrained) ≥ 0.30 (it learned a prior, not a readout).

**Reading.** R-FX1 met: readers can be repaired with ~1 GPU-h of supervision; the blind spot is what the teacher never
said (E51), which is the practical headline for pillar 1. Falsified: the reader's decoder cannot verbalise this state
class even when trained on it; the blind spot is structural to the reader design. Either answer goes on the slide.

**Cost and order.** Arm P ≤ 0.5 GPU-h; arm T ≤ 4 GPU-h (gate 0.5, train 1, evaluate 2.5). §204 ledger, CORE priority
behind E104 and E105, launch by Thu 24:00 CET, one restart at 1.25 × measured. Labels stay CPU-side.

