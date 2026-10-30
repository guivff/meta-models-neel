# BRIEF addendum — G5 planted binding swap, G6 self-choice family

Pre-registered 2026-10-07, after G1–G4 results were read and before any G5/G6 state was captured.
Same model, site, readers, sampling and extractor as G1–G4 (frozen_config.json); new code lives in
`g5_planted/` and `g6_choice/` plus `core/scoring_lo.py`. Unit of inference: base pair.

## G5 — does any reader follow a binding planted inside the state? (prompt fixed)
Motivation: in G1/G2 no reader asserted a binding on the 16 ownership + mapping test states, and
free readouts never named a prompt entity. Free text may simply be the wrong instrument; Suraj's
paired log-odds (LO) in each reader's native format is the sensitive one. We therefore (a) measure
whether the readers' native LO distinguishes the two natural states of a pair at all, and (b) move
the state along the pair's own swap direction with the prompt fixed, and ask whether LO follows.

States: the 16 cached test states of the 8 ownership + mapping pairs (h_A, h_B at block 42).
Direction per pair: u = unit(h_B − h_A). Dose: Δ = ‖h_B − h_A‖ (so α = 1 from h_A lands on h_B's
projection); α ∈ {0.5, 1.0, 1.5}, both signs from each state (h_A + α Δ u toward B; h_B − α Δ u toward A),
centred construction h − (u·h)u + (u·h_target_proj)… simplified to plain addition h + s·α·Δ·u
(both readers see only unit(input); norms are recorded). Nulls: K = 20 random unit directions per
pair at the same norm α·Δ (isotropic), same construction.
Behavioural validation (arm U): the edited vector replaces the block-42 output at the last prompt
position during the target's own greedy decode (8 new tokens); flip rate = fraction of states whose
answer becomes the other candidate; must exceed the null-direction flip rate for the dose to count.
Reader scores, native format, both candidates in one batch:
- OLens: LO = log p("- {A}") − log p("- {B}") after the carrier (bullet register).
- NLA: LO over two templates after "<explanation>\n": 'The answer must be the name "{A}"' /
  'the single-word answer "{A}"' (symbols: 'the symbol "{A}"'); mean of templates.
- J-lens: max cosine score over single-token variants of A minus B (variants recorded; a candidate
  with no single-token variant is marked unscorable, not zero).
Free readouts (secondary): OLens and NLA at α = 1.0 toward the other state, 16 states × 2 readers,
scored with rule-v1 as in G1.
Endpoints: E1 natural separation per reader = paired win rate P(LO(h_A) > LO(h_B)) over the 8 pairs and
AUROC over 16 states (state → its own correct candidate); E2 follow rate = fraction of edited states
whose LO moves in the planted direction by more than the null band (z vs 20 nulls; z ≥ 3 is "follows");
E3 behavioural flip rate per dose; E4 free-readout assertion rate after planting.
Decision: a reader "follows the binding" if E2 ≥ 0.75 at the smallest dose whose flip rate E3 ≥ 0.75
and the null band stays < 0.25; "insensitive" if E2 ≤ 0.25 at the largest dose with E3 ≥ 0.75;
otherwise "mixed". If no dose reaches E3 ≥ 0.75 the manipulation failed and nothing about readers is
concluded. E1 is reported regardless (a reader may separate natural states without following edits).

## G6 — a property the prompt does not state (self-choice)
Motivation: prompt-only recovered 32/32 in G3, so G1's agreement could not show value beyond text.
Family "choice": the user offers two options and asks the model to pick one and reply with that word
only ("Choose either apple or pear; reply with the word only."). The property = the option the model
will produce; the answer key = the target's own greedy answer (no external key exists; factual
accuracy is replaced by target consistency). 8 pairs: A/B swap the option order (balanced), varied
option types (fruit, colour, animal, number word) and templates; both versions share a pair.
Prompt-only arm: the frozen G3 template asks "Which option will the model choose?"; expected near 50%.
Readers: G1 collectors on the 16 states (target greedy, J-lens, OLens, NLA; state-free and null rows
as in G1); claims by rule-v1 with a new family rule: a candidate counts as asserted when named
(non-negated, non-hedged) and the other is not; both → self_contradictory.
Endpoints: E5 coverage and target-consistency per reader; E6 prompt-only consistency with the
target (the floor); E7 NLA–OLens agreement and κ. Decision: a reader "reads the choice" if its
target-consistent rate exceeds the prompt-only floor by ≥ 25 pp with a pair-bootstrap CI excluding 0;
anything smaller is "no evidence" at n = 8 pairs. If the target's greedy choice is the first-listed
option in ≥ 14/16 states, the family is position-dominated and E7 is uninterpretable (report, do not
conclude).

## Budget (ceiling)
G5: 16 natural + 96 edited + 320 null vectors scored teacher-forced (no generation; ≈ 3 forwards each
for two readers), 16 × 3 doses × 2 signs behavioural decodes (8 tokens) + 20 nulls × 16 at α = 1,
32 free readouts (256 cap). G6: 16 captures, 16 targets, 48 readouts, 16 prompt-only, 32 state-free,
32 J-lens null. ≈ 1 GPU-hour plus loads. Kill: K4 — if the G5 flip rate at α = 1.5 is < 0.5, report
the manipulation as failed. Deviations:
- 2026-10-07 14:05 UTC, before any G5/G6 state was captured: rubric.md gained §10 (choice family) and
  core/scoring.py the matching rule, which changed the rubric/code shas in the G1–G4 manifests. The G1
  claims re-extracted with the new code are byte-identical to the frozen ones (checked). A new manifest
  (frozen_config.json) was written for the follow-up; the G1–G4 collection manifest
  (frozen_config_collection.json) and analysis manifest (frozen_config_g1g4_analysis.json) are kept.
- 2026-10-07 14:50 UTC (after G5 phase A results were read): K4 fired — the one-position block-42
  edit flips the target's answer in 0/16 states at every pre-registered dose (0/320 null), so the
  pre-registered "follows the binding" test is void. EXPLORATORY extension, clearly labelled: a
  dose ladder α ∈ {3, 5} (last position only, same construction, no nulls) to learn whether any
  exaggerated last-token vector can override the answer, with OLens/NLA LO scored on the same
  vectors. This changes no pre-registered endpoint and is reported separately from E1–E4.
- 2026-10-07 15:05 UTC outcome of the exploratory ladder: α = 3 flips 0/16, α = 5 flips 2/16; Oracle
  LO shift +6.8 / +8.2 nats, NLA +3.2 / +4.2. Reported as descriptive only (writeup.md).
