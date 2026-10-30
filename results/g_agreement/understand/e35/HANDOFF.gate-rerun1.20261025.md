# E35 gate rerun 1 — 2026-10-25, §133 item 7

One operational rerun is prepared, under coordinator commit
`01c5775ecdb57525e42ab7a831b8928ddbb25944`. The original gate stopped INCOMPLETE
before a production score. This is not a scientific SAE failure. The original
request, assignment template, validation, scan receipt and consumed run-once
guard remain historical records. No original result or guard is overwritten.

## Cause-limited repair

`gate_worker.load_assets` now resolves exactly `config.json` and
`layer44.sae.pt` with `hf_hub_download`, each at
`Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50@13d4221569f7ca5d3c1e605e3e3dc95117e4807c`,
with `local_files_only=True`. It does not request an SAE repository snapshot.
The config checksum and layer/dimension/hook contract are checked before model
allocation; the existing checkpoint checksum and tensor checks remain intact.
The target-model loading path is unchanged.

The CPU regression uses the real Hugging Face offline resolver with a temporary
cache containing only those two snapshot files, no branch ref or whole-snapshot
metadata. Target/SAE allocations are mocked. It checks successful resolution,
exact file/revision pins, missing-file failures, and config tampering. No weights
were downloaded and no GPU inference ran during this repair.

The frozen SAE pin, normalization, token sample, FVU/dead-latent thresholds,
forecast, gate allocation and 6 GPU-hour experiment cap are unchanged. Runtime
selection is fixed to `LAUNCH_REQUEST.gate-rerun1.json`; there is no configurable
retry number or alternate output directory.

## Integrator prerequisites

Before launching, account for pod `5wu4ujkbiotxom` in
`results/g_agreement/blindspot/HANDOFF.md`, as §133 requires. Fill
`assignment.gate-rerun1.template.json` with that HANDOFF's checksum, the resolved
pod-accounting declaration, and actual cumulative prior E35 GPU-seconds. At least
**180 seconds (0.05 GPU-hours)** must be carried forward; include any further
E35 usage found when accounting for the pod. The template leaves prior usage
unset so the Integrator must supply the total. The worker checks these conditions
before consuming the rerun guard or loading models.

The known 180 seconds leaves at most 21,420 seconds (5.95 GPU-hours), less any
additional prior use, within E35's 21,600-second total cap. This gate remains
capped at 3,600 seconds including setup/retrieval. The Integrator also supplies
the pushed source commit, actual pod ID, deadlines, and external hard-stop/hold
evidence. Preserve the existing pod ceiling, launch spacing and programme stop.

Stage the current code and new request exactly, plus the pinned HANDOFF evidence
file. New records use repository-relative paths to avoid changing source seals
during publication. Historical published redaction notes and old seals are kept
unchanged; the new request hashes the current required source files.

## Fixed rerun paths

- Request: `results/g_agreement/understand/e35/LAUNCH_REQUEST.gate-rerun1.json`.
- Assignment: `cache/g_agreement/understand/e35/gate-rerun1-20261025/assignment.json`.
- Output: `cache/g_agreement/understand/e35/gate-rerun1-20261025/out`.
- New guard: `cache/g_agreement/understand/e35/gate-rerun1-20261025/gate.RUN_ONCE.json`.
- Original guard, preserved: `cache/g_agreement/understand/e35/gate.RUN_ONCE.json`.
- Original output, preserved: `cache/g_agreement/understand/e35/gate-20261025`.

Run from the staged repository root after the prerequisites are satisfied:

```sh
PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e35/gate_worker.py \
  --assignment cache/g_agreement/understand/e35/gate-rerun1-20261025/assignment.json \
  --corpus cache/g_agreement/blindspot/s79/frozen/corpus.jsonl \
  --manifest results/g_agreement/blindspot/s79/CORPUS_MANIFEST.json \
  --out cache/g_agreement/understand/e35/gate-rerun1-20261025/out
```

Do not remove either guard. An operational failure of this rerun is reported and
does not authorize a third gate launch. The report records the new request's
checksum. Existing successful-gate and scientific-failure stage transitions stay
as registered: freeze the labelling rubric before decomposition after PASS, or
prepare the registered fallback SAE after a completed scientific FAIL.

The Integrator scans, pushes and launches. Retrieve and verify the new output
seal and account for actual provider time. Large arrays remain in cache. The
worker has performed CPU preparation only for this repair; no rerun is claimed.
