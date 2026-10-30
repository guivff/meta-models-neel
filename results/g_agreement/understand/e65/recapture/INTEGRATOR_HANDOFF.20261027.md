# E65 recapture READY — W-sae, 2026-10-27

Authority: §182 clarification2, db81ff0b10090394afa2c4a91bc420fb631dc0f7, and Guiv's instruction to build immediately on its own pod. Stage all inputs/runtime/model before allocation. One separate H200, maximum1080 provider GPU-seconds total, including setup and retrieval. No conditional extension is authorized. Stop on parity/validity failure; preserve guards and outputs. No reader outputs, labels, probes or fitted artifacts are needed by this run.

## Exact staging packet

POD_ARCHIVE.json identifies cache/g_agreement/understand/e65/recapture/E65_POD_RECAPTURE_20261027.tar.gz by hash and bytes. Extract it at /workspace/activation-readers/. It contains exactly six files: the two positive-field pod input files, common65.py, worker65.py, RUNTIME_PINS.json and POD_SOURCE_SEAL.json. POD_STAGE_MANIFEST.json lists their exact paths/hashes. EXACT_ARCHIVE_CPU_PREFLIGHT.json certifies extraction of this exact archive, execution of its actual --preflight entry point on CPU, and a CPU test of its extracted capture hook. Do not substitute an archive rebuilt from a whole worktree.

Copy the current committed LAUNCH_REQUEST.json separately into /workspace/activation-readers/results/g_agreement/understand/e65/recapture/LAUNCH_REQUEST.json; assignment request_sha256 binds it independently, avoiding an archive/self-hash cycle. Use the pushed40-digit source commit and POD_SOURCE_SEAL.json for pod assignment. CPU_SOURCE_SEAL.json, prepare65.py, preflight65.py, tests, verify_pull65.py, INPUT_BINDING.json and the identity archive do not belong on the pod.

No PRIVATE, DO_NOT_STAGE, original bank files, labels, annotations, BOW fits, source inventory or identity map may be staged. The pod bank has only opaque row/item IDs, frozen token IDs and numeric capture offsets. CPU_IDENTITY_ARCHIVE.json identifies a separate CPU-only archive containing original item IDs/bank/feature and their opaque-ID/offset mapping. Keep it in Integrator CPU custody; hand the verified arrays, offsets and this CPU map to W-lens for its downstream C calculation.

## Scope and representation

All128 rows across W1(42), E36(25), W12(6), E49(16), E56(13), E57(20), E59(6). Each contributes its first20 test items in lexicographic original item-ID order, without labels or probe gating:2560 total prompts. Capture180105 positions ×5120 raw residual coordinates, fp16:1844275200 data bytes plus the small NPY header. The maximum prompt is551 tokens. Every selected prompt has no leading special token, so first content is position0; read is the final frozen prompt token. No state-onset/body truncation or token-length eligibility filtering is applied. W-lens handles its registered <16-position rule on CPU.

Target Qwen/Qwen3.6-27B at6a9e13bd6fc8f0983b9b99948120bc37f49c13e9, full unquantized bf16, no adapter. Raw output after zero-based decoder block44 is captured without modification and converted tofp16. The hook stops the forward immediately afterward, avoiding unnecessary upper blocks/vocabulary-head work. No generation, sampling, labels, projections, fitting or reader computation occurs.

Input rows/items retain the frozen selection order. Runtime batches are length-sorted for throughput; ACTIVITY storage uses sealed global vector offsets to restore exact original selection order. Output ACTIVATIONS.fp16.npy has shape[180105,5120]. OFFSETS.json seals every opaque item, original prompt token count, start inclusive, stop exclusive (read=stop−1), vector offset and vector count. INPUT_BINDING.json pins all frozen source hashes and the CPU map.

## Assignment and launch

On a fresh separate pod, fill assignment.template.json into /workspace/activation-readers/cache/g_agreement/understand/e65/recapture/assignment.json with actual pod ID, published commit, exact request/source/input hashes, actual provider-created time, previous_gpu_seconds=0, allocated_gpu_seconds<=1080, absolute deadline<=created+allocation and<=Thu29Oct22:59Z. Setup deadline is at mostcreated+360s and leaves the180s retrieval reserve. External stop and hold renewal must be live and separate_pod_verified=true.

From /workspace/activation-readers:

```sh
env CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e65/recapture/worker65.py --assignment cache/g_agreement/understand/e65/recapture/assignment.json
```

The worker's immutable once guard is cache/g_agreement/understand/e65/recapture/WORKER.RUN_ONCE.json and output is cache/g_agreement/understand/e65/recapture/out-20261027/. It measures real batch32/64 capture throughput and peak memory, requires max(4GiB,5% total) headroom, selects the fastest safe batch, and admits the entire workload only if1.5·F+360 fits before the deadline minus180s retrieval reserve. Pilot activations are discarded. It cannot extend the cap, skip items or truncate prompts. No actual H200 measurement has been performed by W-sae during this CPU build.

On completion, stop the provider promptly and retrieve/verify the complete sealed output within the allowance. Preserve OUTPUT_SEAL.json, BENCHMARK.json, FORECAST.json, RUNTIME.json and CUSTODY.json beside arrays/offsets. Provider timing belongs in Integrator accounting.

## Verified pull and sealed once-only integrity command

On the Integrator CPU checkout, put the complete sealed output in cache/g_agreement/understand/e65/recapture/verified-pull/final/. In its parent create VERIFIED_PULL.json with issuer=integrator, experiment=E65, verified_complete=true, exact output_seal_sha256, pod_id and actual provider_stopped_epoch. Extract CPU_IDENTITY_ARCHIVE.json's separate archive under cache/g_agreement/understand/e65/recapture/ on CPU only.

Run the committed COMMAND.json once from the verified checkout's root:

```sh
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e65/recapture/verify_pull65.py
```

Guard results/g_agreement/understand/e65/recapture/VERIFY.RUN_ONCE.json; output results/g_agreement/understand/e65/recapture/VERIFIED_CAPTURE.json. It validates complete output hashes, actual provider cap, exact item order/offsets, fp16 shape/finiteness and CPU identity-map linkage. It computes no probe, C, reader statistic or scientific verdict. W-lens owns downstream analysis. No pod or real integrity command has been invoked by W-sae.
