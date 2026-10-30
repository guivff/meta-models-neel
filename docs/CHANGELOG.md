# What changed: from the two input decks to activation_readers_MATS_final.pptx

Base: `activation_readers_neel_v2.pptx` (content, diagrams, experimental progression). Look: the original `activation_readers_neel.pptx` (cream background, Cambria titles, dark title and closing slides, quiet hierarchy). 24 core + 15 appendix slides, all text, tables and charts native and editable, presenter notes on every slide.

## Structure
- Rebuilt around one question: when, if ever, does a reader report model-private state beyond reconstructing the prompt?
- Four parts: what readers say (E140, E100, E113, cues) · why, Suraj's reconstruction work (carried-not-stated, S14/S16, exp 28, 29, 30) · causal, where in depth (E104/E126, E135, E133/E137) · audit, hypothesis, two research-phase experiments.
- The "four numbers" slide is gone; each number now sits on its own experiment slide with intervention, metric, denominator, control and a "Does not show" line.

## New slides
- Apparatus (2): read site, `hidden_states[L+1]`, both injection formulas, read-token conventions (assistant onset vs raw " by").
- Real readouts (3): two verbatim G1-pilot items read by both readers at block 42, with sources.
- E140 funnel (6): 300 → 58 → 12, with missing and multi-value counts.
- E100 category census (7): shows that S ≈ 0 is silence on nesting and indent but partly cancellation on the page digit.
- E113 (8): probe AUROC across all 64 reader blocks at the first generated token, separate from the stated counts.
- S16 decomposition (11) with the unreconciled E7 result; exp 28 scatter of all 47 rows (12).
- Exp 29 as checkpoint trajectories from `table29.json` (13); exp 30 per row with naming vs unconditional accuracy and the P1 flag (14).
- E104/E126 token-grid method slide (15) before the restoration curve (16).
- E137 split into design (18) and result (19), with causal R and the reader's naming categories on separate axes.
- Two separate research-phase experiment slides (22, 23), each with manipulation, arms, endpoint and falsifier.

- From Suraj's 'Readers talk figures' page: his headline figure (both readers' text carries structural state that neither states; exp 25 and exp 22) is now slide 10, opening his section. His M3 point (the Oracle's published score is any-of-11 layers, 0.65, vs 0.37–0.40 at one layer; text-only best of 3 is 0.69) is in the reference box on slide 5. The cheap-monitoring slide moved to appendix A15 to keep 24 core slides.

## Corrections relative to earlier decks and the prompt pack
- Removed quotes that are not verbatim in the repository ("Ignore earlier movements", and "signaling a language identification task", which came from a placebo-pool readout).
- Exp 28: the shift does beat the type label (314 AIC); "shift adds nothing" was wrong. Paraphrase ranges are narrow on structural rows.
- E7 rows are table 0.39, parenthesis 0.57, list 0.51 (the prompt pack's order was swapped).
- E135 used α 6, and its "no push" bars come from the exploratory §248C analysis.
- E137 early readouts mostly name another person or nobody; it is no longer described as "silent".
- E122's −0.14 is a formal-vs-informal contrast, not the cue direction; removed.
- E114 is a descriptive pre-stated reading, not a confirmatory rule.
- Exp 06 had no registered prediction, so it moved from "predicted" to "read afterwards" on the synthesis slide.
- No registration tally is quoted; none exists in the repository.

## Typography
- Body text 14–17 pt, chart labels ≥ 12 pt, footers 12 pt, source lines 11 pt. The only smaller runs are blank spacer lines.
- 17:20 · Slide 1: added subtitle "Reporting gaps and read-site limits in Oracle Lens and NLA" under the title; slide 1 notes and NARRATIVE updated to match.
- 19:25 · Audit fixes (GAP_REPORT): E104 2.23× norm now cited to e135/analysis/RESULTS.json; E109 83 of 84 defined at block 44; Oracle stated bound ≤ 3/320; slide 16 and A12 state that all 84 fact items are one fact pair; slides 19 and 21 state that D1 does not separate holder from last hand-over; Neel quotations removed from notes (source unverified), ledger row dropped (62 rows).
