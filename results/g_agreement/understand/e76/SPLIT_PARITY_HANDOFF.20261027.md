# E76 split parity — READY, 2026-10-27

This operational addition splits the existing W1 asked-score parity gate between a label-free pod and Integrator CPU adjudication. Original252 stored block44 vectors, three84-item rows, two frozen Oracle phrasings per row, native Oracle scorer, empty prefix, batch8 and |delta AUROC|<=0.02 are unchanged. E76 scope, pool, production batches32/64, native wrappers, norms, regexes and rules remain unchanged. No actual GPU run or parity verdict was produced during this build.

The active archive is in POD_ARCHIVE.json (E76_POD_20261027_split_parity6100.tar.gz). It supersedes the earlier16-file archive for this build. POD_STAGE_MANIFEST.json is the exact21-file positive allowlist; no labels, reference AUROCs, private files, annotations, regexes, CPU keys or BOW fits enter it. Parity templates contain only the original olens candidate pairs, with class/domain/value metadata removed. Original text-free parity item IDs/row identities and raw vectors remain byte-identical. Exact compressed-archive preflight, extracted production-core smoke and extracted split-parity smoke must PASS before READY.

## 1. Pod generates only

Stage the positive archive, current LAUNCH_REQUEST.json separately, verified assets and Integrator assignment. Use the same admitted E76 stage assignment for parity and production: identical stage_started_epoch, original absolute_deadline_epoch and allocated_stage_seconds<=6100. CPU scoring and wait time stay inside that clock. No reset/extension. Add parity_input_seal_sha256 from PARITY_BINDING.20261027.json and conservative positive parity_phase_forecasts_seconds (parity_setup,parity). Normal phase_forecasts_seconds still cover the entire remaining E76 run, including another Oracle load after returning from CPU scoring. Admission requires remaining production plus parity to fit1.5·remaining+360 before the180s retrieval reserve. If it does not fit, stop; no scope cut or higher cap.

From /workspace/activation-readers:

```sh
env CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e76/worker76.py --parity-generate-only --assignment cache/g_agreement/understand/e76/assignment.json --assets /workspace/e76/assets.json
```

No PARITY_RELEASE.json is required for this path. Guard: cache/g_agreement/understand/e76/PARITY_GENERATE.RUN_ONCE.json. Output: cache/g_agreement/understand/e76/parity-generated-20261027/. PARITY_SCORES.jsonl contains exactly id,feature,scores; scores are the two original raw A-minus-B candidate log-odds. GENERATION.json carries the raw-score hash and explicit labels_loaded=false/verdict_computed=false. RUNTIME.json and CUSTODY.json bind the same pod/assignment/assets/native-code/input/request/source hashes. OUTPUT_SEAL.json seals every output and marks GENERATED_UNSCORED. It never emits PASS, opens a label/reference/key, consumes WORKER.RUN_ONCE or creates E76 production records. Preserve a failed/consumed guard; no scientific retry.

## 2. Integrator CPU scores

Retrieve that exact output directory to cache/g_agreement/understand/e76/parity-verified-pull/final/. The Integrator writes parity-verified-pull/VERIFIED_PULL.json with issuer=integrator,experiment=E76_PARITY,verified_complete=true,pod_id and output_seal_sha256 after verifying retrieval. Copy the CPU-only key archive identified by PARITY_CPU_ARCHIVE.20261027.json to the CPU checkout if needed, verify its SHA256, and extract relative to repository root. KEY.PRIVATE.json remains in ignored cache/parity_cpu/ with mode0600, never Git or pod. The public PARITY_BINDING pins its bytes and the original input seal c4197052... .

```sh
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e76/score_parity76.py
```

This checks the exact verified generation, native code, assets, stage clocks and original CPU key before calculating the unchanged per-row mean-two-phrase AUROCs. One CPU directory/guard: cache/g_agreement/understand/e76/parity-cpu-20261027/SCORE.RUN_ONCE.json. Outputs: PARITY_RESULT.json and CPU_PARITY_SEAL.json; PARITY_RELEASE.json exists only on PASS. A FAIL stops and does not permit production or a parity retry. This is operational parity adjudication, not E76's registered regex analysis.

## 3. Return only the release

On CPU PASS, copy only parity-cpu-20261027/PARITY_RELEASE.json to the same pod's cache/g_agreement/understand/e76/PARITY_RELEASE.json. It pins the parity result, generation output seal, raw score file, blind input seal, assets and native code. Production rejects a release bound to a different split generation. Run the existing E76 production command with the original assignment and unchanged deadline:

```sh
env CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e76/worker76.py --assignment cache/g_agreement/understand/e76/assignment.json --assets /workspace/e76/assets.json
```

The production WORKER.RUN_ONCE guard is independent and still requires a same-pod verified PASS. If a prior same-pod PASS already exists and no split-generation guard was consumed, the prior attestation path remains available as before. E76 regex analysis remains the original sealed once-command after the complete verified production pull; judging remains held. Integrator pushes and operates the pod.
