# E58b READY — batched operational rerun1, 2026-10-27

This supersedes the active launch paths and budget instructions in the blind_v2 handoff. Its CPU/pod custody separation remains mandatory. One authorized operational rebuild follows the reported batch8 timing NO_FIT; preserve its consumed guard and outputs. Verify no prior production and count prior actual provider seconds. Do not retry parity or validity failures.

## Stage before allocation

From the verified published owner commit, extract the code archive identified by POD_CODE_ARCHIVE.20261027.json at /workspace/activation-readers/. Its positive allowlist is common58.py, batching58.py, projection58.py, worker58.py, POD_SOURCE_SEAL.20261027.json and results/g_agreement/blindspot/s79/RUNTIME_PINS.json. Extract the unchanged INPUT_ARCHIVE.20261027.json archive at /workspace/activation-readers/cache/g_agreement/understand/e58b/; it contains exactly pod_inputs_v2/BANK.json, J384.npy and INPUT_SEAL.json. Copy current committed LAUNCH_REQUEST.json separately into /workspace/activation-readers/results/g_agreement/understand/e58b/LAUNCH_REQUEST.json. POD_STAGE_MANIFEST.20261027.json is the complete positive allowlist, with the request independently bound by the assignment.

Never stage CPU_JOIN, CPU_ONLY_ARCHIVE, PRIVATE, DO_NOT_STAGE, annotations, BOW fits, delivery/, legacy inputs/, or a repository-wide archive. Input archive and CPU-only binding hashes are unchanged. No labels or label-dependent IDs go to the pod.

## Custody and command

Use one H200 and the pinned model/runtime. Fill assignment.template.json into /workspace/activation-readers/cache/g_agreement/understand/e58b/assignment.json with actual timing, exact request/source/input hashes and published40-digit commit. Set previous_gpu_seconds to verified actual prior usage, allocated_gpu_seconds to the new remaining allocation, with previous+allocated <=5400. A fresh pod avoids ambiguous elapsed accounting. The deadline also obeys Thu29Oct22:59Z and the existing setup guard. prior_no_production_verified, retry_number=1 and conditional_extension_authorized attest the authorized rebuild. budget_watch_verified attests an active external watcher of BUDGET.json.

From /workspace/activation-readers:

```sh
env CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e58b/worker58.py --assignment cache/g_agreement/understand/e58b/assignment.json
```

The worker tests real batch32 and64 timings and memory before production, writes BENCHMARK.json, fits the same shared dev-PCA, then writes BUDGET.json/FORECAST.json. At least max(4GiB,5% total) memory headroom is required. All candidate tokens and all8arms remain. New worker guard is WORKER.rerun1.RUN_ONCE.json; output is out-rerun1-batched-20261027/ under the experiment cache. No H200 timings were measured on the owner CPU.

Keep the registered aggregate2700s if BUDGET.json selects it; tighten the external hard stop to effective_provider_deadline_epoch immediately. The worker's own timer stops scoring180s earlier. Use the approved aggregate5400s only when the measured full-run forecast fails2700s and fits5400s. Provider accounting includes prior usage. Stop promptly on completion or failure and retrieve within the reserve. Do not silently keep a5400s reservation running when2700s was selected.

## Verified pull and once-only CPU analysis

On the Integrator CPU checkout, copy the complete sealed output into cache/g_agreement/understand/e58b/verified-pull-rerun1/final/. Place VERIFIED_PULL.json in its parent, with issuer=integrator, experiment=E58b, verified_complete=true, exact output_seal_sha256, pod_id and actual provider_stopped_epoch. Preserve the original failed pull separately. Verify CPU_CUSTODY_BINDING and create the CPU-only INTEGRATOR_CUSTODY receipt as specified in the blind_v2 handoff; labels remain in Integrator CPU custody.

From that verified checkout's repository root, the sealed once-only command is:

```sh
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e58b/analyze_once.py
```

COMMAND.json/COMMAND_SEAL pin it. The unchanged guard is results/g_agreement/understand/e58b/ANALYSIS.RUN_ONCE.json and output results/g_agreement/understand/e58b/analysis_20261027/. Analysis verifies measured admission, actual selected-cap custody, complete grid, seals and CPU label custody before computing rules. Neither GPU production nor the CPU registered analysis has been invoked by the owner for this rebuild.
