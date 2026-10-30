# E76 placebo-at-scale READY — Main Integrator, Track Q

Authority: §194 a68a228d, clarification1 24070152 and compute deviation bbed7f84; Guiv ratifies source-bank-median matching with paired random references. Main Integrator admits compute inside the existing TrackQ/daily ceiling. One H200; strict6100 E76 stage GPU-seconds including this stage's setup, captures, native generation and retrieval. No automatic cap extension, scope cut, judging or retry clock reset. The existing stage may reuse a same-pod native parity PASS; no label files stage with E76.

## Frozen source universe and pool construction

E63's W1/E36/E56/E57/E59 source universe is retained, all9024 frozen test prompts, uniformly selecting500 unique shuffled source items with seed20261028 after sorting(bank,original item ID). Source counts in the selected500: W1=196,E36=103,E56=62,E57=109,E59=30. Raw Gaussian directions are500×5120 float32, seed20261027, shared across native layers. All source file hashes, exact tokenization and selected IDs are bound before any E76 capture/readout. The source-bank covariate and original identities stay in a CPU map; pod bank codes0..4 map to W1,E36,E56,E57,E59.

The pod captures raw read-point vectors at block42/44, zero-based post-decoder-block outputs, with the Oracle adapter disabled on the pinned base target. This uses the exact native mats.capture implementation and the full original raw prompt IDs, right padding; it stops after the last capture hook. Only reference norms and the500 selected raw directions at each layer are retained. It computes each bank/layer median over all that bank's frozen test read points, then rescales each shuffled vector to its source bank's median. Its paired random vector is scaled to the same native-layer median. CALIBRATION.json, reference norms, selected raw directions and all four pool matrices are sealed before any E76 generation. No source labels, gate selection, whitening, centering or carrier modification is involved. Fresh capture avoids an E59-capture dependency while preserving its frozen text/read position.

The unchanged native adapters then process the scaled input: Oracle at44, one greedy readout at its existing128-token native limit; NLA at42, one greedy readout at512 tokens with the registered generated-suffix </explanation> stopping criterion. Batch32;1000 outputs per reader,500 per arm. No generation pilot is discarded/repeated. The first actual batches supply observed timing updates and their readouts remain in the single registered grid. Input pool bytes must remain unchanged. NLA truncation counts are reported without exclusions.

## Exact archive staging

POD_ARCHIVE.json identifies cache/g_agreement/understand/e76/E76_POD_20261027.tar.gz, extract at /workspace/activation-readers/. POD_STAGE_MANIFEST.json is the positive16-file allowlist. EXACT_ARCHIVE_CPU_PREFLIGHT.json verifies those exact compressed bytes, extracted checksums, the extracted --preflight entry point and an extracted model-free full acquisition-core smoke (all four500-vector pools and2000 records). No actual GPU/model/native readout or real regex analysis was run by W-sae.

Copy current committed LAUNCH_REQUEST.json separately to /workspace/activation-readers/results/g_agreement/understand/e76/LAUNCH_REQUEST.json, bound by assignment request_sha256. Use only the positive archive plus that request and the operator's dynamic assignment/parity release. Source weights/runtime/assets are pre-staged separately as usual, without API credentials in files. The native reader APIs and loader functions are byte-identical to their pinned registered source; the local asset registry path is contained inside this archive.

Never stage CPU_SOURCE_SEAL, REGEX_CATALOG, regex/scoring/preparation/test code, original bank files, annotations, BOW fits, labels, PRIVATE/DO_NOT_STAGE files or the CPU map. CPU_MAP_ARCHIVE.json identifies the separate CPU-only identity/covariate archive. Its pool map is cache/g_agreement/understand/e76/cpu_only/POOL_MAP.PRIVATE.json; keep it on the Integrator CPU side. No item text is passed to either verbalizer: only the fixed native carrier and one vector.

## Admission and same-pod parity

Before allocating, verify the exact archive receipt and source/input pins. assignment.template.json requires issuer=integrator,track=Q,main_integrator_admitted=true,daily_budget_verified=true, one H200 and the pushed40-digit commit. Fill conservative phase forecasts for oracle_setup,capture,oracle_readout,nla_setup,nla_readout; they include full scope and the registered greedy lengths. The worker carries those forecasts forward and tightens upward from maximum observed real batch timings. At each checkpoint1.5·remaining+360 must fit before the stage deadline minus180s retrieval. No warmup or setup time is outside the6100s stage clock; stage_started_epoch precedes assets checking/model load. Existing-pod time from earlier experiments remains charged to its own stage in Main Integrator accounting.

The assignment's absolute deadline is at moststage_started_epoch+allocated_stage_seconds (<=6100), the provider lease deadline and Thu29Oct22:59Z. External hard stop and hold renewal must be verified. Do not admit on a forecast requiring more than the cap.

Supply cache/g_agreement/understand/e76/PARITY_RELEASE.json from PARITY_RELEASE.template.json: issuer=integrator, same assigned pod ID, status=PASS, same_pod_verified=true, native_backend_unchanged=true, the verified existing W1 parity result hash and exact assets-manifest hash. Its native_code_sha256 must match the three listed reader/stop code files, proving correspondence to the already passed native parity path. If there is no same-pod parity PASS, establish the registered parity on that pod before releasing E76, with the CPU truth/key held by the Integrator. No W1 parity labels are included in this archive. Parity/validity failure stops; no scientific retry.

From /workspace/activation-readers:

```sh
env CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e76/worker76.py --assignment cache/g_agreement/understand/e76/assignment.json --assets /workspace/e76/assets.json
```

Guard cache/g_agreement/understand/e76/WORKER.RUN_ONCE.json; output cache/g_agreement/understand/e76/out-20261027/. On completion release/stop the stage promptly; preserve output seals, calibration matrices, norms, selected raw vectors, native JSONL, parity receipt, runtime and timing. Large data remain in cache. Main Integrator logs provider usage/spend with trackQ.

## Immediate CPU regex analysis after verified pull

No sealed E76 placebo readout pool existed locally at build time, so there are no numeric E76 floors yet. Do not substitute E63's200-vector pool or invent zero floors. The CPU command is sealed and needs no judging permission; run it immediately after the verified complete E76 pull.

Place the complete sealed output at cache/g_agreement/understand/e76/verified-pull/final/. Put VERIFIED_PULL.json in its parent, issuer=integrator,experiment=E76,verified_complete=true, exact output_seal_sha256 and pod_id. Give actual provider_stopped_epoch if terminating the pod. For reuse by another stage, give stage_released_epoch with stage_release_verified=true and charge later GPU time to the new stage; release must be inside this stage's cap. The verifier checks the actual stage clock, full2000-record grid, norm medians and exact reconstructed scaled pools.

From the CPU checkout repository root:

```sh
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e76/analyze_once76.py
```

Guard results/g_agreement/understand/e76/REGEX_ANALYSIS.RUN_ONCE.json; output results/g_agreement/understand/e76/regex_20261027/. Outputs FLOOR_TABLE.json and FLOOR_TABLE.md with an analysis seal. The164-row frozen catalog covers W1/E36/W12/E49/E54/E56/E57/E59/E61_D3/E61_D4/E62:151 usable rows,13 explicitly unavailable. Existing regex/negation/case rules are retained; where the registration supplies only literal human-readable value words those are matched case-insensitively as whole words, without aliases or stemming. Nonreadable canonical IDs and count/eval rows without a binary value regex are unavailable; no zero is substituted. Per-item value families are weighted by their frozen test frequency. The source and method are exposed per row.

The table reports any-value naming N as the floor line, and signed S_regex with independent pseudo-truth A/B coins, seed20261029, shared by pool index across arms/readers. Both/neither contribute0 to S. Vector-bootstrap95% intervals use2000 draws,seed20261027, as E63. Source-bank conditional floors are reported beside the global shared-pool estimates. Empty/malformed/truncated readouts are retained. These are regex occurrence statistics, not claims that an assertion was made. No real bank's reader outputs or verdicts are needed for this floor pass.

## Judging held

No judging code, API call or credential is present. Judged floors remain WAITING_SEPARATE_AUTHORISATION_USD2. W-internals/Integrator may prepare the blind judge route, but Guiv's separate authorisation is required before spending. E67 wave1 remains sealed and separate; this request does not change it or its analysis.

2026-10-27 — §194 compute deviation bbed7f84:6100s supersedes the original3600s total. Run on E59's pod after its same-pod parity PASS; scope, n, batches, norms, native adapters, sampling, regexes and analysis are unchanged. This is a cost-only re-pin.
