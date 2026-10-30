# E39 overnight once-only analysis — 2026-10-26

Covered run: E39 (W-lens), under §149 amendment 886d03b0. No E39 analysis has
been invoked. E39's original analysis, rules, source manifest, training worker
and launch package remain byte-identical. E37 remains unchanged.

## Exact command

Working directory: `<W-lens worktree>`

```sh
python results/g_agreement/understand/e39/analysis_once_2026_10_26.py
```

Do not invoke the old launch request's placeholder analysis command directly.
This dated §149 entry point supersedes that command for overnight analysis.
Its code, request and unchanged analysis dependencies are pinned by
`ANALYSIS_CODE_SEAL_2026-10-26.json`; exact paths are in
`ANALYSIS_REQUEST_2026-10-26.json`.

## Delivery contract — before invoking the command

All paths below are relative to the working directory above.

1. First bind E39's inputs using its existing package binder. The exact local
   input is `cache/g_agreement/understand/e39-bound-v1/input`; the matching bound
   request is `cache/g_agreement/understand/e39-bound-v1/LAUNCH_REQUEST_BOUND.json`.
   The private test-label key stays there; the integrator must not inspect it.
2. After all assigned E39 pods complete and their transfers are verified, expose
   each complete final-pull directory at these exact canonical locations:
   `cache/g_agreement/understand/e39-verified-v1/slot0` through `slot5`.
   Each contains `PULL_SUMS` and `out/`. Use the actual slot from assignment.json,
   not completion order. A symlink to the entire original verified final-pull
   directory is acceptable; never modify its contents or source seals.
3. Fill `VERIFIED_PULLS_149.template.json` and save it as
   `cache/g_agreement/understand/e39-verified-v1/VERIFIED_PULLS.json`.
   Set status VERIFIED_COMPLETE and production_complete true only after full
   verification. Supply the actual pod IDs, SHA256 of each transfer PULL_SUMS,
   and the original bound input-seal hash. For fewer than6 assigned pods, retain
   precisely slots0..N-1 and set pod_count=N. The registered54runs must still all
   be present. No glob, latest-directory selection or invented pod ID is used.
4. PULL_SUMS is the integrator's transfer manifest, with SHA256 followed by a
   relative file path (as used for E28); it must cover every file under out/.
   The wrapper rehashes its contents, then the original analysis validates all
   completed runs, source/input identity, parity, readiness, budgets and score
   seals before opening its private label key.

These are required delivery paths for future verified pulls, not a claim that
E39 has already run. No E39 verified pull is currently present locally.

## Once-only and publication

The command atomically creates
`cache/g_agreement/understand/e39-analysis-once-v1/CLAIM.json` **before validation**.
It remains after success, failed validation, failed analysis, or interruption.
Every later invocation refuses. Do not delete/reset it or retry; any failure
waits for W-lens, as §149 requires. Status and captured stdout/stderr remain in
that same cache directory. Validation failures invoke the registered analysis
zero times; an admitted invocation calls it once in a single subprocess.

The unchanged analysis writes to
`cache/g_agreement/understand/e39-analysis-registered-v1`. On success the wrapper
verifies its output seal and copies all sealed files byte-for-byte to
`results/g_agreement/understand/e39/analysis_registered_2026-10-26/`, then writes
`results/g_agreement/understand/e39/RUN_BY_INTEGRATOR_2026-10-26.json`.
The integrator secret-scans and commits those outputs unchanged with label
`§149 RUN-BY-INTEGRATOR`. It does not interpret or alter them. W-lens reviews the
seal and registered verdicts in the morning.

CPU validation:9 synthetic tests pass, including exact-path preflight,
transfer hash/completeness failures, simultaneous claims, second invocation,
validation failure, analysis failure, interruption, code drift and byte-identical
publication. No model call or registered E39 analysis was made.
