# E124 registered-behaviour consistency judging

E124 is a separate USD 3 lifetime bank. Its fixed judging prompt and strict
YES/NO/OFF-TOPIC schema are in `e124_amendment1_judge.py`; prompt freezing precedes every
E124 call. Payload fields are exactly opaque `id`, literal `model_reference` and
literal `readout`. There is no prompt context or condition label on the wire.
The route is the original OpenRouter Gemini Flash-Lite / google-vertex/global,
with ZDR, denied collection and no fallbacks.

The registered source is E118's original 252 readouts plus the E82 readout roster
specified by E118b clarification 1 and W-mech2's source-case receipt. E82 has no
single primary position: all 6,790 readouts from 209 items are retained. The
analysis unit remains the item. Group labels do not become position labels.
W-mech2 owns the prospective report adapter, including the explicit treatment of
Wilson CIs versus within-item averages and item bootstrap. C does not invent a
binary item label or treat positions as independent items.

Amendment 1 (2045d4a96) defines the model reference as its registered behaviour
measure: the higher-scored candidate on the frozen continuation pair for E104
arm U and E109 block 52, per item/condition, and W-text's filter-derived belief
label for E82. Track Q seals this CPU binding. C copies those sealed references;
it does not recompute a different behaviour measure or generate new answers.
The original full-greedy-answer source request/audit is historical and is
superseded by this explicit amendment. The original draft prompt/source receipt
is preserved; the amendment prompt is frozen separately before any E124 call.

Before preparation, obtain Track Q's complete registered-reference binding and
W-mech2's updated tested report source. The current profile deliberately records
`report_adapter_pinned: false`, and `prepare` rejects it. This is a source gate,
not a request for another authorization. No new reader calls or GPU work.

The owner source packet must seal `UNITS.json` and `CUSTODY.PRIVATE.json`, with
experiment E124, phase `model_reference_consistency`, frozen census `n`,
`frozen_before_judging` and `unit_definition_frozen` true, and original
`source_seals`. Custody has `registered_behavior_references_verified` and
`complete_eligible_grid` true only after genuine source verification, plus one
record per opaque ID in `units`. Its `model_reference_ref` and `readout_ref` use
`{seal_index, member, keys}`. Preparation verifies all original seals and literal
registered-reference/readout equality. Labels and classification joins remain in custody.

Only after the whole source profile pins W-mech2's actual report receipt and
dependencies should the operator freeze a new phase and admission. Admission
must bind the exact published source/input/allocation, a live route/privacy and
funding proof less than 300 seconds old, the report source commit/path/hash and
genuine test/source verification. Use `accounting233.snapshot` and verify any
additional newly active owner bank allocations before dispatch; do not count
queued allowances as open allocations. Original E118 spending is unrelated to
the separate E124 cap. Canonical E124 ledger and dispatch lock stay in the shared
funded queue.

The isolated runner makes one physical attempt per unit. Charged length is
terminal UNPARSEABLE; there is no schema retry or missing-value imputation.
Unknown provider/cost/finish stops the bank. HTTP 402 pauses every bank; no
unresolved reservation is resent or guessed settled. Raw bindings use the actual
physical call phase, independently of the directory label. Synthetic full-loop
tests cover COMPLETE sealing, terminal missingness, no replay and failure stops.
The source/input/report gates must all be complete before any paid call.
