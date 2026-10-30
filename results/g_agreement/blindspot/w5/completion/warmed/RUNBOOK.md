# W5 fresh warmed-unit scoring completion

This replaces the earlier maximum-based timing receipt. Integrator operation and
publication only. Exact authority: `08b24aeb898e2f087c4641cabf6757d16b030b95`,
16:35 CEST operational amendment, preserved in TIMING_AUTHORITY.md. The existing
12:55 CEST budget amendment remains in force: one fresh scoring-only attempt,
science cap min(1.5 × F + 360, 3,600) seconds per Guiv's 2026-10-24 instruction,
setup 900 seconds outside science. No recapture. The existing feasibility check
that 1.5 × F must fit within 3,600 seconds is unchanged; added headroom clips at
the ceiling.

Each of the six layer scorer paths runs one complete unscored production unit:
84 items, both frozen phrasing contrasts, production batch 32 including the final
partial batch. Discard its outputs. Then time three full units per layer and
discard those outputs too. All 18 timed units count against the persistent
first-science clock. F = sum(all timed smoke durations) + sum over six layers of
median(three layer timings) × 80 fresh units. Every one of the 480 registered
feature/layer/arm units is then scored afresh. No smoke score enters the result.

Only the original eight capture files plus CAPTURE_SEAL.json are staged. Do not
open or stage old partial scores, including either previous W5 attempt. The old
NO_FIT attempt used 156.5 science seconds; its record remains intact. The initial
W5 overrun also remains disclosed. The fresh allowance does not erase either.

Use the new LAUNCH_REQUEST.json, EXECUTION_PLAN.json and its verified source-only
archive. Bind both budget_amendment_commit and timing_amendment_commit in the
receipt; completion_receipt_sha256 binds all fields. Keep independent absolute
custody and first-science hard stops. Setup is 900 seconds, science ceiling 3,600,
custody at most 4,500 seconds, and final retrieval reserve 180 seconds. The worker
shortens the science deadline after the measured forecast. If NO_FIT, stop and
report; do not reduce rows/layers or retry automatically.

CLI remains `python -m projects.g_agreement.blindspot.w5_complete` with assignment,
assets, label-free bank, original sealed captures, new execution plan, new receipt,
complete sealed W1 analysis and a fresh nonexistent output directory. Use
`/weights/venv-kernels/bin/python`, read-only weight snapshots and private outputs.
After retrieval and full score-seal verification, run the registered analyse-sweep
once, publish the W5 result and retain all prior attempts/deviations in accounting.
