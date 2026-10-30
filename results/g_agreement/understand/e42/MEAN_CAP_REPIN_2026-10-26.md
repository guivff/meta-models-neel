# E42 one-further-attempt operational re-pin — 2026-10-26

Authority: §151 note, 50edac15, and explicit user instruction. This dated note supersedes the prior operational cap/forecast, not the scientific registration or state seal.

CAP and mirrored RUN_PLAN/LAUNCH_REQUEST fields are 1,800 seconds. The unchanged 60-second retrieval reserve is inside that cap. The gate is arithmetic mean of every completed warmed production batch (times[1:]) × remaining batches × 1.5, compared with the external deadline minus the retrieval reserve. The cold batch remains charged to elapsed custody but is never extrapolated. Before a warmed batch exists, the absolute timer remains active.

Every completed batch writes batch_index, item count, elapsed seconds, cold flag, remaining batches, warmed mean and projected gate seconds to batch_timings.jsonl, flushed before the forecast gate. On completion that log is included in FOLLOWING_TEXT_SEAL.json. A NO_FIT retains the partial timing log as a deviation, never reusable continuation input.

The integrator runs the explicitly authorized one further attempt on all 3,444 prefixes fresh. Partial outputs are not merged. No change to generation, seed, exact 32-token horizon, assets, state functions, input inventory, analysis, or per-assignment once lock. No autonomous retry is added. Integrator retains prior-attempt custody records separately.

Forced worker/plan/code/request/archive pins refreshed; earlier archives and dated notes are preserved. The new archive is cache/e42_stage_2026-10-26_mean1800.tar.gz. All 17 CPU tests pass. State seal remains 1b21560490aa83834ab56516a9dfc5385761ccfaba2128f815ee50274e5de9f3. No GPU launched or push performed by W-text.
