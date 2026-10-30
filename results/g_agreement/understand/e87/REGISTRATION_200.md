## §200 Robustness programme: is the blind spot real, or an artefact of where and how we read? (2026-10-28 10:50 CET)

**Why.** WorkspaceBench, run with our exact Oracle checkpoint (s3d-rl600), reports `user_modeling` 0.96 and
`directed_modulation` 0.45, reading every relevant position and taking any layer. Our single-position, single-layer,
single-greedy protocol found the user picture and instructed focus almost never stated. So the read site, the layer
and the sampling may explain part of every MISSED verdict in this project. §200 tests that directly and audits the
other known ways a verdict could be an artefact. No sealed verdict changes. §200 results are reported beside them.
**Launch deadline:** Thu 29 Oct 12:00 CET. **Priority:** E87 is now first after E79/E80 finish, ahead of E81–E86.

### E87. Position × layer sweep on missed rows (CONFIRMATORY for R-L1)

**Rows.** Eight rows MISSED by the Oracle lens with probe ≥ 0.90: E49 container_after_move, holder_after_handovers,
branch_taken, var_type_at_use, user_expertise, unit_system; E57 nesting_depth, indent_level. **Positive controls:**
E49 topic_twin and E57 loop_direction (REPORTED). **Items:** the first 30 test items per row (frozen order).
**Cells.** For each item: the last 16 token positions ending at the registered read token (all template tokens
included where present) × 6 Oracle layers {20, 28, 36, 44, 52, 60} (within the lens's trained range; W-mechanism
confirms). One greedy readout per cell. NLA (trained at block 42 only): block 42 × the last 8 positions.
**Judging, WorkspaceBench-style.** One judge call per (item, layer) sees every position's readout at that layer and
answers with the §172 codes for the row's property and two values (correct / wrong / both / property / exhibits /
silent; it may quote one readout). For the NLA, one call per item over its 8 positions.
**Measures.** Per row: S_layer (item bootstrap) at each layer; S_max = the maximum over layers. **Placebo with the same
structure:** 30 pseudo-items per row, each with 16 × 6 readouts of norm-matched random vectors drawn from E76's
generator (seed 20261029), judged identically. S_max,placebo is computed the same way, so the any-of-many inflation
cancels.
**R-L1 (blind spot survives the sweep):** on ≥ 6 of 8 rows, S_max − S_max,placebo ≤ 0.10 for the Oracle lens, while
both controls reach S_max − S_max,placebo ≥ 0.30. **Falsifier (the headline becomes "single-site blind spot"):**
S_max − S_max,placebo ≥ 0.20 on ≥ 4 of 8 rows. If either control fails, R-L1 is NOT EVALUABLE.
**Reported:** S by layer and position-of-first-mention; the NLA analogue; agreement with the sealed single-site verdict
per row.
**Cost:** about 25k Oracle readouts plus 2.9k placebo readouts plus about 2k NLA readouts, ≈ 4 GPU-h (may be split across
2 pods); judging about 2.4k calls, ≤ USD 4.
