# E118 part b transport

This module sends only owner-frozen `{id, context, readout}` units through the
unchanged E118 `SYSTEM` and strict YES / NO / OFF-TOPIC schema. It does not choose
E82 positions, construct scientific groups, infer contexts or run an analysis.
All source classifications and joins remain CPU-local. Acquisition order is
sorted by opaque ID. One physical attempt per unit; charged length is terminal
UNPARSEABLE. There are no schema retries or new privacy exceptions.

W-mech2 supplies a sealed packet with `experiment: E118`, `phase: part_b`, `n`,
`frozen_before_judging: true`, `unit_definition_frozen: true`, `source_seals`, and
sealed members `UNITS.json` and `CUSTODY.PRIVATE.json`. The latter binds every unit
to the original E82 native/input/target/judgment sources and the frozen report
groups and denominators. Scientific handling of multiple positions, both/neither,
missing judgments and the ten no-truth items must be fixed by that owner before
calls. A different owner packet representation can be copied to this transport
format without changing or deriving its scientific fields.

`prepare --owner-seal PATH --owner-sha256 HASH` verifies the complete packet and
sources, freezes calls under `E118/belief_wrong_consistency_judging`, and runs the
full frozen-wire privacy/cost inventory. Preparation itself makes no model calls.

Before `run`, publish the tested source and exact admission; provide the live
route/privacy/funding proof less than 300 seconds old; verify current complete
global exposure using `accounting231.snapshot`; and reactivate only the unused
part of the original E118 cap under its canonical dispatch lock. The continuation
receipt `CONTINUATION_PART_B_C.json` must retain original cap USD 1, original
part-a actual USD 0.027057, original released allocation and completion seal, and
the direct section231 authority. Its hash is in `ADMISSION.json`. The remaining
original allowance is USD 0.972943, not an additional USD 1. No continuation is
created by this source-only module or by intake. Part-a output/report seals stay
unchanged. A new combined final bank packet will bind both phases.

The new acquisition loop binds physical raw files by each call's actual phase
(`judging`) rather than its directory name. A synthetic full-loop regression
checks raw hashes, terminal missingness, final progress and an immutable COMPLETE
seal with a deliberately different directory name. Unknown errors stop without a
COMPLETE seal. The shared runner and all old source receipts remain unchanged.

`accounting231` inherits accounting229 and adds only concrete OPEN E120/E121
allocations. E120 parts a/c share lifetime USD 2. Queued allowances contribute no
open allocation. Before admission, check for any additional newly active banks
outside this registered inventory and add a prospective source receipt if needed.
