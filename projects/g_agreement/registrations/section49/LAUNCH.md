# §49 launch procedure

Owner remainder, branch r/remainder. One fresh GPU, ≥80 GB VRAM, ≤7200 seconds creation-to-exit including setup/holds/pulls. Prefer warm network volume w9182om1pd at /workspace in EUR-IS-3. An integrator-assigned off-volume pod needs ≥200 GB disk and the pinned public assets downloaded within the same cap. No self-provisioning. No other experiment or automatic relaunch. No paid API budget.

## Before science

1. Resolve exact native pod ID from its own-account HTTP200 entry; verify single GPU, provider creation and deadline≤creation+7200. Reconfirm /proc/1/environ identity on SSH. Arm maintained detached exact-ID hardstop before creation+7140 and watchdog before staging; independently verify live PIDs and account/ID logs. Post proof in HANDOFF and obtain bridge retirement/custody acknowledgement. Never modify the network volume's .env.
2. Use a new private `/workspace/remainder/section49/<pod_id>` run directory and its `code` subdirectory. Stage an archive of the receipt's full source SHA with umask077; do not run in a mutable/shared checkout. Copy the registered source bank and frozen basis (basis goes to `RUN/inputs/jspace_L38_r384.pt`), then verify source_manifest.json and the basis hash. No refit or projector rebuilding. Use the established Python3.11+ runtime and pinned model/reader revisions; source existing volume environment only to activate it. Explicitly reset RUNPOD_POD_ID from /proc/1/environ after sourcing, because .env may carry a stale ID.
3. Measure an actual transfer to Mac and hash both copies. Record conservative bytes/second in booking.json. Require enough free storage for pinned target, NLA and reader assets plus outputs. Models run sequentially. Download failures are operational failures; do not alter revisions. Smoke confirms reader liveness, scoring and numerical compatibility.
4. Write RUN/booking.json with pod_id, gpu_count=1, created_epoch, deadline, cap_seconds=7200, plan_sha256, own_account_http200=true, custody_acknowledged=true, mac_hardstop_pid, mac_watchdog_pid, verified_pull_bytes_per_second. Booleans summarize the actual saved account and custody proofs; never synthesize them. Preserve sanitized proof/guard logs in RUN. Runtime rejects identity/source/plan/budget mismatches. Do not put credentials in RUN or the receipt.

## Exact job

From the immutable code root, with the verified native RUNPOD_POD_ID exported:

```sh
python -m projects.g_agreement.r_bench.section49 pipeline --run "$SECTION49_RUN"
```

Launch detached with stdout/stderr to RUN/job.log and record its PID for the watchdog. Pipeline runs target-smoke → nla-smoke → projection → target-full → nla-full → analyze, in separate bounded processes, then packages on success or failure. It has no automatic retry. Monitor own declared logs and output files. The guard's independent hardstop always remains armed. A timing failure does not authorize a smaller sample or another pod.

## Pull and stop

After pipeline exits, job.log is closed. Run `package` once more so the final job/operational logs are included. Pull every path in RUN/manifest.json and the manifest to the private Mac cache (ordinary openrsync flags; no --chmod). Never copy .env/credentials. On Mac:

```sh
python -m projects.g_agreement.r_bench.section49 mac-receipt --local "$SECTION49_MAC_PULL"
```

Return mac_receipt.json to RUN and on the pod run:

```sh
python -m projects.g_agreement.r_bench.section49 release --run "$SECTION49_RUN" --local "$SECTION49_RUN/mac_receipt.json"
```

Require VERIFIED_READY_TO_STOP; retrieve release.json, then stop exact assigned pod with own-account API and independently verify EXITED. Do not terminate. Book provider creation-to-exit hours once and post RESULTS or explicit failure/partial status plus receipts and log.md/compute.jsonl. Frozen source manifest, all output hashes and scientific rows stay available. If even packaging fails, separately hash and pull operation logs; never fabricate a scientific completion.

## Certification boundary

CPU certification covers the registered plan, split math, coverage/verdict logic, release hashes and reused SWAP tests. It does not claim GPU smoke passed. The assigned-pod live checks and all-reader smoke are mandatory before full science admission; failure closes this attempt.
