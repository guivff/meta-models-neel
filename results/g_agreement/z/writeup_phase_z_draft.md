# STAGED TEXT for writeup.md — Phase Z corrections (NOT YET INSERTED; awaiting Guiv's review of the Z1–Z4 summary)

## Z4 position dissection (2026-10-09; z4/z4.md, z4/fig_main.png; role-aligned reading is a dated deviation in BRIEF_Z)

Pre-registered labels (absolute token index; for reference):

| family | pre-registered label | basis |
|---|---|---|
| mapping | SINGLE CAUSAL | index 9 flips 14/18 = 0.78 [0.55, 0.91] vs bar 0.8·R_all = 0.776 |
| ownership | JOINT | no single index and no index pair flips; pairs tested were indices 0–4 (tie-break, chat-template prefix) |
| pooled | JOINT | best single 0.33, best pair 0.60 |

Role-aligned classification (primary reading; layer 38, α 1):

| family | edited positions | flips | label |
|---|---|---|---|
| mapping | first differing symbol alone | 31/64 = 48% [37, 60] | |
| mapping | second differing symbol alone | 29/64 = 45% [34, 57] | |
| mapping | both differing symbols (Y2 name_only) | 61/64 = 95% [87, 98] | JOINT ACROSS TWO TOKENS |
| mapping | every other position (Y2 name_removed) | 0/64 | |
| ownership | any single position (diff, question start, last, other) | 0/956 | |
| ownership | all name/object tokens together (Y2 name_only) | 0/64 | |
| ownership | all post-statement positions (Y2 name_removed) | 64/64 = 100% | JOINT ACROSS A SPAN (post-statement) |
| ownership | question tokens only (Z4b) | 6/64 = 9% [4, 19] | |
| ownership | chat-template tokens only (Z4b) | 7/64 = 11% [5, 21] | |
| ownership | last 3 tokens only (Z4b) | 0/64 | |
| ownership | question first / second half (Z4b) | 0/64, 3/64 | |

Reading: at layer 38 the two families store the answer in opposite places. Mapping carries it on its two differing
symbol tokens, jointly (neither alone suffices). Ownership carries it jointly across the positions after the two
statements, and not at all on the name or object tokens; no single position, including the last token, suffices.
Z4b (pre-registered follow-up, z4b/z4b.md): no part of the post-statement span suffices on its own at layer 38
(question tokens 9%, template tokens 11%, last 3 tokens 0%, question halves 0% and 5%), although each moves the
model's answer log-odds substantially (question +7.8, template +7.6 nats; all post-statement positions +24.2). The
ownership answer at layer 38 is therefore joint across the whole post-statement span. Earlier, the binding sits on
the names: editing only the name and object tokens flips 64/64 at layer 20 (+25.3 nats), 0/64 at layer 28 (+2.5) and
0/64 at layer 38 (+0.9): between layers 20 and 28 the binding moves off the name tokens into the later positions.
Readers on the same edits: editing only the last 3 tokens moves the Oracle lens and J-lens by 0.70 and 0.58 of their
own natural separation while the model's answer moves 0.55 nats and flips 0/64; template-only edits move them by
0.85 / 0.77 while the model flips 11%. The readers track the positions nearest their read site, not the positions the
model's answer depends on.
Determinism: 32/32 restore decodes reproduce their all-except-one twins. Random single-position control: 0/64.

## Correction to Phase Y, Y2 (2026-10-09; per-family recomputation of y2 rows)

The Phase Y sentence "name positions only 48%; non-name positions only 50%" pooled two families with opposite
patterns, and so did "another same-family pair's direction 23%". Per family, layer 38, α 1:

| family | condition | model flip | Oracle win | NLA win | J-lens win |
|---|---|---|---|---|---|
| mapping | full swap | 62/64 = 97% | 84% | 73% | 89% |
| mapping | name tokens only | 61/64 = 95% | 95% | 89% | 98% |
| mapping | non-name positions only | 0/64 = 0% | 67% | 67% | 56% |
| mapping | other pair's direction | 5/164 = 3% | 50% | 53% | 56% |
| mapping | J-space component only | 5/64 = 8% | 83% | 83% | 78% |
| mapping | J-space remainder | 54/64 = 84% | 83% | 73% | 72% |
| ownership | full swap | 64/64 = 100% | 86% | 70% | 94% |
| ownership | name tokens only | 0/64 = 0% | 42% | 50% | 42% |
| ownership | non-name positions only | 64/64 = 100% | 89% | 70% | 94% |
| ownership | other pair's direction | 82/208 = 39% | 58% | 57% | 61% |
| ownership | J-space component only | 0/64 = 0% | 92% | 80% | 86% |
| ownership | J-space remainder | 64/64 = 100% | 86% | 66% | 84% |

Corrected statements: (1) the binding question is not ill-posed by halves; per family it is clean: mapping's answer
is on the name (symbol) tokens, ownership's on the non-name positions. (2) In both families the readers follow the
half that flips the model (mapping name tokens 89–98%; ownership non-name positions 70–94%) and not the half that
does not (ownership name tokens 42–50%), with the exception of mapping's non-name half (56–67% while the model
flips 0%). (3) The J-space finding holds per family (J-space component flips 8% / 0%, remainder 84% / 100%), and the
readers follow the J-space component the model ignores in both families (78–92%). (4) In ownership another pair's
swap direction flips the model 39% of the time (mapping 3%): the ownership answer at layer 38 is largely carried by a
direction shared across pairs, consistent with the first-versus-second-mentioned confound found in R2.

## Z1 reported as gain over the dose-only model (2026-10-09; z1/gain_over_dose.md, z4/z1_on_z4/gain_over_dose.md)

ΔAUROC = reader − dose-only, paired pair-level bootstrap, 1,000 resamples; "beats dose" only if the CI excludes 0.

| set | Oracle lens | NLA | J-lens |
|---|---|---|---|
| X2, S2 ∪ S3 | −0.039 [−0.071, −0.011] | −0.143 [−0.181, −0.108] | −0.042 [−0.076, −0.015] |
| X2, S3 | −0.037 [−0.082, −0.005] | −0.111 [−0.149, −0.076] | −0.003 [−0.026, +0.016] |
| Z4, single + pair + all-except | +0.057 [+0.024, +0.090] | −0.165 [−0.225, −0.094] | +0.045 [+0.007, +0.082] |
| Z4, single positions | +0.388 [+0.270, +0.494] | −0.068 [−0.191, +0.045] | +0.381 [+0.271, +0.487] |
| Z4, mapping only | +0.094 [+0.039, +0.139] | −0.185 [−0.265, −0.084] | +0.077 [+0.012, +0.134] |
| Z4, ownership only | −0.005 [−0.009, −0.002] (dose = 1.000) | −0.144 [−0.210, −0.068] | −0.008 [−0.013, −0.003] |

Reading: on the X2 interpolation ladder no reader beats knowing the dose. On the Z4 edits Oracle and J-lens beat the
dose reference, but that reference knows the arm and the dose and not which position was edited, so within an arm
it is at chance (AUROC 0.43–0.48); the readers' advantage there is that their score moves when a causal position is
edited, which the reference cannot see. The NLA never beats dose and is below it on most sets.

## Per-position correlation (Z4 single-position arm; z4/per_position_corr.md)

Spearman between a position's mean reader shift and its flip rate, pair-level bootstrap 95% CI; ownership is
undefined (no single position flips). Mapping, α 1: Oracle +0.35 [+0.07, +0.51], J-lens +0.20 [+0.03, +0.47], NLA
−0.32 [−0.42, +0.06]; the model's own answer log-odds give +0.57 [+0.42, +0.60] (absolute index). Role-aligned, no
reader's CI excludes 0 (Oracle +0.33 [−0.01, +0.37], J-lens +0.02, NLA −0.31) against the model's +0.35; the
role-keyed statistic is tie-bound because only the two differing-symbol keys ever flip. Reading: the readers weakly
identify which positions are causal; the NLA, if anything, ranks them backwards.
## NLA validity (z4b/nla_gate.json)
Pre-registered gate PASSED: re-scoring the X1 bank through the Z4 code path reproduces the original NLA scores exactly
(34/47 within-pair wins on ownership and on mapping, 23/23 on language and tense; median |Δ log-odds| 0.000, sign
agreement 1.000). The Z4 NLA numbers stand.
