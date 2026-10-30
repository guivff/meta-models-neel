# E36 ready handoff — 2026-10-25

**READY_FOR_INTEGRATOR_BINDING.** The complete 25-row bank is frozen and checked.
The earlier missing-definition hold is resolved. Use `LAUNCH_REQUEST.json` and
this handoff, retaining the earlier dated notes as history.

All 4,200 item labels and 2,100 A/B token-length pairs pass. Each row has 84 dev
and 84 test items in disjoint template families. The freeze was 14:51:59 CET on
Sunday 25 October, before the Monday deadline, so the eight-row fallback is not
selected. `FROZEN_BANK_2026-10-25.md` records hashes, checks, the bounded-parser
limitations and the documented pre-check loader repair. No item was replaced or
dropped, and no model has been called.

## Stage and bind

1. Verify the archive hash in `STAGING_ARCHIVE.json`, then extract its referenced
   cache archive into the prepared repository checkout. Verify every entry in
   `STAGING_MANIFEST.json`. It contains label-free inputs, normalized candidates,
   source files and small receipts. Keep `labels.DO_NOT_STAGE.jsonl`, the raw
   authored bank and per-item label-check ledgers on the CPU side.
2. Supply the verified local model asset inventory, a conservative seconds
   forecast for each of the seven phases named in the request, and actual prior
   charged E36 GPU seconds. Run the request's `binding_command`, replacing its
   three explicit input placeholders. `prepare_launch.py` performs CPU checks
   and writes a hash-bound plan and command; it does not load a model or start a
   pod. There is no fabricated measured forecast in the committed request.
3. Assign one H200 and install an independently enforced external stop. Fill the
   generated assignment template with the actual pod identity, allocation start,
   cumulative prior usage and stop receipt, saving it as `ASSIGNMENT.json`.
   Launch the command in `LAUNCH_REQUEST_BOUND.json`. An alternate GPU requires
   the §135 wait and memory-check receipts enforced by the worker.

The aggregate E36 cap is **28,800 GPU seconds**, including setup, asset hashing,
warm measurements, scoring and all earlier charged attempts. The 180-second
retrieval reserve is inside that cap. Every batch rechecks the padded remaining
forecast. A failed gate stops; no retries, scope cuts or substituted candidates
are authorized by this package. The integrator owns the shared run/compute logs.

## Registered computation

Capture blocks 42 and 44 at each prefix's final token. Use the exact W1 grouped
probe recipe at block 44. Score the 2,100 test items with W1 Oracle descriptive
pairs, E30's two bullet pairs averaged as one channel, and W1 NLA pairs at block
42. Score E15's frozen continuation pairs on its eight supplied rows; only the
seven registered rows enter H4. There is no v2 dev pair selection.

The explicit expanded thresholds are H1 11/16, H2 7/9, H4 5/7 and H5 11/16.
H3 requires the coordinator's sealed original E30 R2 status and R1-support rows,
with channel ID `e30_bullet`. Missing eligibility is reported as not evaluable;
it does not justify choosing rows from E36 outcomes or delaying unconditional
acquisition. Return the complete output seal, raw scores, activations and runtime
receipt to W-text for CPU analysis.

## E30 on the same bank

`E30_SECOND_BANK_REQUEST.json` binds this exact bank and frozen E30
`CANDIDATES.json` for its R1/R2 replication. Its separate aggregate cap is
1,800 GPU seconds. E36 already acquires the exact two-pair bullet channel and
descriptive baseline; the E30 owner can verify whether these sealed scores and
activations satisfy the companion recipe and can be reused. Any additional E30
work remains in that separate ledger and must respect the 0.5-GPU-hour cap.

The integrator sweeps/publishes this commit and operates pods. W-text has pushed
nothing and has used zero GPU time.
