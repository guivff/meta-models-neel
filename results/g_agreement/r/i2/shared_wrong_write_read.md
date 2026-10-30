# Exploratory shared wrong answers and write versus read

**Shared wrong-answer identity is not identifiable on this binary bank.** Both observed matching rates are 100% by construction. The requested null can assign donor wrong answers to recipients for whom they are correct. Any mechanical ECHOES MODEL classification below measures that null artefact, not echoing. Preserving the recipient label yields 100% null matches and zero excess for every row, also by construction; this does not establish independent errors.

Preregistered and pushed in `f67826d5`; CPU only. 21,198 items, 108 facts, 34 corpus groups; LABEL_DEFECT excluded, audit flags retained. LR is available on 20,400 items. 2,000 item and 2,000 corpus bootstrap draws, seed 0; interval envelopes reported. Native threshold conventions are frozen TH-3 votes.

| Reader | Joint-wrong n | Match | Null | Excess [95% CI] | Mechanical rule only / write-read verdict | Ratio / 95% CI |
|---|---:|---:|---:|---|---|---|
| all_native_2plus | 9237 | 1.000 | 0.603 | 0.397 [0.318, 0.472] | descriptive | — |
| olens | 1729 | 1.000 | 0.622 | 0.378 [0.310, 0.422] | ECHOES MODEL | — |
| nla | 1802 | 1.000 | 0.617 | 0.383 [0.317, 0.430] | ECHOES MODEL | — |
| jlens | 1858 | 1.000 | 0.642 | 0.358 [0.288, 0.402] | ECHOES MODEL | — |
| skip_a | 1813 | 1.000 | 0.631 | 0.369 [0.284, 0.424] | ECHOES MODEL | — |
| lr | 1192 | 1.000 | 0.568 | 0.432 [0.378, 0.456] | ECHOES MODEL | — |
| olens / SWAP-U | 195 (59 unused) | — | — | — | MIXED | 0.629 [0.469, 0.867] |
| olens / X1b-lite | 195 (75 unused) | — | — | — | READS WRITES | 0.699 [0.546, 0.880] |
| olens / pooled_equal | 390 (134 unused) | — | — | — | READS WRITES | 0.658 [0.553, 0.807] |
| nla / SWAP-U | 195 (59 unused) | — | — | — | MIXED | 0.630 [0.476, 0.850] |
| nla / X1b-lite | 195 (75 unused) | — | — | — | READS WRITES | 0.652 [0.522, 0.804] |
| nla / pooled_equal | 390 (134 unused) | — | — | — | READS WRITES | 0.640 [0.537, 0.782] |
| jlens / SWAP-U | 195 (59 unused) | — | — | — | MIXED (circular) | 0.599 [0.479, 0.760] |
| jlens / X1b-lite | 191 (75 unused) | — | — | — | MIXED | 0.589 [0.478, 0.715] |
| jlens / pooled_equal | 386 (134 unused) | — | — | — | READS WRITES (circular) | 0.595 [0.508, 0.708] |
| skip_a / SWAP-U | 195 (59 unused) | — | — | — | MIXED | 0.584 [0.445, 0.781] |
| skip_a / X1b-lite | 195 (75 unused) | — | — | — | MIXED | 0.610 [0.482, 0.762] |
| skip_a / pooled_equal | 390 (134 unused) | — | — | — | MIXED | 0.595 [0.496, 0.725] |

Write/read completed after the two-source amendment `8398eb12`. Stage B excluded by user decision: no saved reader pair readouts; no re-scoring.

The all-native row conditions on at least two wrong native readers and tests unanimity among those wrong readers. The other rows condition on that reader and prompt-only both being wrong. The CSV includes 90% intervals, BH-adjusted tests, and the label-preserving diagnostic.

Write/read uses raw natural-minus-edited reader log-odds, positive toward the inserted bridge. Pooled numerator and denominator each average the two source means with weights 1/2; ratios are not averaged. Intervals envelope 2,000 item draws, 2,000 bridge-cluster draws and the degenerate single-corpus bootstrap. These are conditional on this two-hop bank, not cross-corpus generalization. Shared true bridges receive shared cluster multiplicities across sources. SWAP-U J-lens and its pooled result are circular; do not treat that verdict as independent evidence. SWAP-U uses edit L24/read capture L42, X1b-lite edit L28/read L42 (Oracle L44). Source sites differ as frozen in the source protocols.

The table’s n column is jointly wrong items for shared-wrong rows and paired edited items for write/read rows. Native wrong-identity rows are not identifiable regardless of their mechanical rule. Write/read ratios are exploratory observational contrasts between used/unused edits; baseline margin and edit strength can confound them.
