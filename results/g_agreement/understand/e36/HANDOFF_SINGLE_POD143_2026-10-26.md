# E36 single-pod amendment — §143 item 3, ab3c9cfd

READY_FOR_INTEGRATOR_BINDING. Run one pod, all 25 rows, with no sharding.
This supersedes the 14,400-second limit in HANDOFF_CAP143_2026-10-26.md.
The uncommitted shard implementation was dropped and is not in this package.

The allocation cap is min(1.5 × F + 360, 59,447) seconds, further reduced if
the remaining aggregate custody allowance is smaller. F includes the full
252-item parity gate and setup. The 59,447-second integer ceiling follows the
user's instruction and conservatively rounds down 60,000 − 552.8. Include
attempt 1's 552.8 seconds and all other prior custody in the unchanged 60,000
second aggregate budget. At F=32,600 seconds, the limit is 49,260 seconds.

Use this commit's LAUNCH_REQUEST.json, manifest and archive. The existing
binding command, verified warmed-forecast receipt, external stop, 180-second
retrieval reserve, and batch-level forecast checks remain unchanged. The
bank, candidates, channels, H1–H5, scoring code and ±0.02 full parity gate are
unchanged. No retry or scope cut is introduced.

111 CPU tests pass, including acceptance above the former shard ceiling and
rejection above the new single-pod ceiling. Integrator's watcher publishes
and launches this commit; W-text has pushed nothing and launched no GPU job.
