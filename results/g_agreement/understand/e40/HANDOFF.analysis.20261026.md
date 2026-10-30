# E40 gate check — committed §149 overnight entry point, 2026-10-26

Coverage: W-sae / E40(b) gate verification only. E40(a)'s CPU diagnostic is
already complete and is not rerun. Labelling, blind judges and decomposition
remain with W-sae for morning review.

## Exact verified-pull location

From the repository root, stage the verified E40 pull at:

- `cache/g_agreement/understand/e40/training-20261026/verified-pull/final/`
- `cache/g_agreement/understand/e40/training-20261026/verified-pull/arrays/`
- `cache/g_agreement/understand/e40/training-20261026/verified-pull/VERIFIED_PULL.json`

Preserve every original filename and byte. The original `OUTPUT_SEAL.json` and
copied original `assignment.json` go in `final/`. Every file named by the output
seal must be available under `final/` or `arrays/`; this includes the final SAE
checkpoint and capture ledger. Relative symlinks or hard links from the usual
per-pod verified pull are allowed, with targets inside E40 cache. The analysis
checks every copy's checksum; do not edit the original seal to flatten paths.

After verifying the complete pull, copy
`VERIFIED_PULL.gate-check.template.json` to the exact receipt path above and
fill the actual pod ID, assignment SHA256, original output-seal SHA256 and UTC
verification time. Set `status=VERIFIED_COMPLETE`. The training-request hash
must match the committed analysis plan. This receipt is custody evidence, not a
new scientific judgement. An unfilled template or partial pull stops analysis.

## Exact once-only command

Activate the existing project CPU Python environment with Torch (needed only to
import the existing `verify_pass` helper), then run exactly:

```sh
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e40/gate_check.py
```

The code/plan seal is `ANALYSIS_CODE_SEAL.gate-check.20261026.json`. It verifies
its source closure before claiming the analysis. There are no path overrides,
model calls, statistical refits or judge calls. The command checks the saved
registered gate; it does not evaluate the SAE again.

The global exclusive guard is:
`results/g_agreement/understand/e40/GATE_CHECK.RUN_ONCE.json`.

The fixed owner output directory is:
`results/g_agreement/understand/e40/gate_check_20261026/`.

Expected small outputs are `GATE_CHECK.json`, `GATE_CHECK.md` and
`ANALYSIS_SEAL.json`. Commit these bytes and the consumed guard unchanged,
labelled `§149 RUN-BY-INTEGRATOR`. Do not commit input symlinks or large model
artifacts; the temporary flat input view for `verify_pass` stays in cache and
is removed automatically.

## What the command does

It validates full artifact hashes, the original assignment/request/sample
lineage, final100M-token training,65536/k128 configuration, calibration sealed
before update1, fixed scale reuse and exclusion counts. It checks the saved
filtered pooled FVU<=0.25 and dead<10%; the all50000-token FVU stays descriptive.
PASS additionally calls the existing committed `followup.verify_pass` on the
same verified bytes and records its admission receipt. FAIL reports no adequate
SAE/stop. A valid operational NO_FIT/INCOMPLETE is recorded without a scientific
verdict. An upstream validity failure or any validation mismatch seals
VALIDATION_STOP and exits2; the run waits for W-sae.

Never remove the guard, rerun on failure, change a rule or interpret raw/private
files manually. A successful check is not permission to start blind coding or
decomposition overnight: those stages stay with W-sae in the morning.
