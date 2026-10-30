# E76 split parity — READY, 2026-10-28

Authority: d7b4145b3b2591282648f6c834cd1bbce863615a, compute deviations item1: E76 cap raised from6,100s to7,000s so split parity plus production fits realistic forecasts. Cost only. This dated note supersedes every earlier E76 cap/archive instruction. The registered split-parity design, scientific scope, frozen input bytes, sampling, medians, native adapters, batches, parity estimator/threshold and regex analysis are unchanged. The separate synthetic-warm-up ruling for other/later jobs is not implemented in this cost-only re-pin.

Use the current committed LAUNCH_REQUEST.json, assignment.template.json and SPLIT_PARITY_COMMANDS.20261027.json. Their cap is7,000s. The active exact21-file label-free archive is cache/g_agreement/understand/e76/E76_POD_20261028_split_parity7000.tar.gz, pinned by POD_ARCHIVE.json/POD_STAGE_MANIFEST.json. Preserve earlier archives as history. All source, archive, request, CPU-command and delivery hashes are refreshed together. CAP_REPIN_VALIDATION.20261028.json proves the sole pod source change is CAP=7000 in common76.py; all other pod source and all input files are byte-identical to the split-parity6100 build. The older dated validation reports describe their original builds; this dated receipt covers the new cap.

Follow SPLIT_PARITY_HANDOFF.20261027.md for the operational sequence and custody, replacing its6100s cap by7000s and its archive by the one above:

1. Stage only the positive pod archive plus the separately pinned current request and Integrator dynamic assignment/assets. Keep labels/reference/key/CPU transport archives off the pod.
2. Fill one assignment with allocated_stage_seconds<=7000, a single stage_started_epoch and absolute_deadline_epoch. Parity generation, CPU retrieval/scoring/wait, subsequent production and final retrieval all share that unchanged deadline; it must also fit the provider lease and Thu29Oct22:59Z programme stop. Phase forecasts still include full remaining production plus split-parity setup/scoring; admission remains1.5·remaining+360 before the180s retrieval reserve.
3. Pod generation command (repository root):

```sh
env CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e76/worker76.py --parity-generate-only --assignment cache/g_agreement/understand/e76/assignment.json --assets /workspace/e76/assets.json
```

It emits only the original252-item W1 raw score records and hashes; no labels or parity verdict. Guard/output remain cache/g_agreement/understand/e76/PARITY_GENERATE.RUN_ONCE.json and parity-generated-20261027/.

4. Retrieve to cache/g_agreement/understand/e76/parity-verified-pull/final/ and seal VERIFIED_PULL.json in its parent. Integrator-only CPU command:

```sh
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e76/score_parity76.py
```

The existing ignored parity_cpu/KEY.PRIVATE.json and its separately pinned CPU-only archive are unchanged. CPU outputs remain parity-cpu-20261027/. Copy only the exact-generation-bound PARITY_RELEASE.json back on PASS; a failed parity stops without retry or production.

5. Production command with the same assignment and deadline:

```sh
env CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e76/worker76.py --assignment cache/g_agreement/understand/e76/assignment.json --assets /workspace/e76/assets.json
```

Production guard/output remain WORKER.RUN_ONCE.json and out-20261027/. Preserve consumed guards and any existing outputs. The CPU regex once-command and its verified-pull paths are unchanged. Judging remains held. Integrator pushes and launches; no actual GPU job or parity/regex adjudication is run by this re-pin.
