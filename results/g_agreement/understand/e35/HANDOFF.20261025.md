# W-sae / E35 gate handoff — 2026-10-25

Stage 1 is prepared for the Integrator. No GPU, training, judge call, latent selection, or
decomposition has run. This checkout is
`<W-sae worktree>`, branch `r/blindspot`.
Only `results/g_agreement/understand/e35/` is changed. The Integrator scans, pushes,
stages assets and launches; this worker does not provision or launch pods.

## Fixed gate

`Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50` at
`13d4221569f7ca5d3c1e605e3e3dc95117e4807c`, file `layer44.sae.pt`, is the sole transfer
candidate. It has 81,920 latents, k=50 and input width 5,120. The registration leaves
the published sparsity variant unspecified; this selects the first listed 27B
residual variant before any evaluation. The L0_100 variant will not be tried after
seeing a gate result. The exact weight checksum is in `GATE_PLAN.20261025.json`.

The official encoder uses raw float32 residuals, affine encoder, ReLU, then TopK.
Its model-card toy example omits ReLU; the pinned executable app supplies the
convention used here. Decoder reconstruction is the conventional affine map
`z @ W_dec.T + b_dec`, with checkpoint shapes checked. No centering, normalization
or AR whitening is applied. The source links and hashes are in the plan.

The gate uses 50,000 distinct held-out tokens from the frozen section-79 corpus.
The sample is sealed at SHA256
`dff73a3a83b76a6de4a5a2cbf2fe909a14a6888eaa9b91eeca6df849323fc593`.
Source groups, rather than individual tokens, are assigned to holdout. All 490
holdout documents' source groups are excluded from fallback training. Their first
512 raw tokens provide 100,540 eligible positions; the smallest seeded token
hashes select exactly 50,000. Whole prefixes supply causal context. Domain counts
are 10,343 LaTeX, 25,673 Markdown, 10,333 prose and 3,651 Python. No labels or model
values choose these positions. These are token-weighted corpus counts, not a new
equal-domain quota.

FVU is pooled squared error divided by pooled centered activation variance, with
float64 accumulation. The decision is exactly FVU <=0.25 AND dead fraction <0.10.
Dead means never strictly positive on these tokens. Missing tokens, nonfinite
values, zero variance, asset errors and timeouts are operational incompleteness,
not a scientific gate failure. CPU synthetic tests exercise the boundaries.

## Integrator staging and sole gate request

Use `LAUNCH_REQUEST.gate.json`; fill `assignment.gate.template.json` on the pod.
Bind it to the actual `RUNPOD_POD_ID`, the pushed commit and the exact request
checksum. Confirm the external hard stop and hold renewer. Allocate at most one
GPU and 3,600 seconds including setup and retrieval; carry all prior E35 provider
time into `previous_gpu_seconds`. The experiment cap is 21,600 GPU-seconds across
all stages. Respect the eight-pod ceiling, five-minute launch spacing and
2026-10-28 23:59 Europe/Zurich programme stop.

The worker is offline. Before starting the assigned clock, ensure the shared HF
cache has the target model at `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9` and the
selected SAE revision. Stage only `layer44.sae.pt` and `config.json` for the SAE
(about 3.36 GB), not every layer. Use the existing target snapshot where available.
The following is asset staging, not an extra GPU launch:

```python
from huggingface_hub import snapshot_download
snapshot_download('Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50',
    revision='13d4221569f7ca5d3c1e605e3e3dc95117e4807c',
    allow_patterns=['layer44.sae.pt', 'config.json'])
snapshot_download('Qwen/Qwen3.6-27B',
    revision='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9', local_files_only=True)
```

Use the normal CUDA environment with torch, transformers >=5.2, huggingface_hub,
tokenizers and NumPy. The corpus is already available locally at
`<repo-root>/cache/g_agreement/blindspot/s79/frozen/corpus.jsonl`
and should be staged at the same repository-relative cache path. Its pinned
manifest is already tracked. Run from the staged repo root:

```sh
PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e35/gate_worker.py \
  --assignment cache/g_agreement/understand/e35/assignment.gate.json \
  --corpus cache/g_agreement/blindspot/s79/frozen/corpus.jsonl \
  --manifest results/g_agreement/blindspot/s79/CORPUS_MANIFEST.json \
  --out cache/g_agreement/understand/e35/gate-20261025
```

The assignment template is intentionally unrunnable until filled. An exclusive
`gate.RUN_ONCE.json` consumes this request before any model loading; do not delete
it or change the output location to retry. The worker validates source hashes and
regenerates the exact held-out selection. Three discarded training-document
pilots measure a conservative full-sample forecast before collection. The
science clock never resets; no partial sample is substituted when time is short.

Retrieve `GATE_RESULT.json`, `OUTPUT_SEAL.json`, `CLOCK.json` and the immutable
assignment. Keep `h.npy` and `reconstruction.npy` (about 2 GB together) in cache.
Verify every output-seal checksum before interpreting the result. The Integrator
adds actual allocation, command, seed and provider time to the shared run/compute
logs; worker-authored receipts remain inside E35's allowed directory.

## Following the result

- `PASS`: freeze and commit the latent-label rubric and blind judge prompt before
  selecting the 300 dev-active latents, collecting label contexts, or decomposing.
- Scientific `FAIL`: prepare the registered TopK SAE, 16,384 latents and k=64,
  train on at least 20M training tokens with the same held-out groups excluded,
  and issue the one conditional training request within the remaining budget.
  If that SAE fails the same gate, report "no adequate SAE" and stop.
- `NO_FIT` or `INCOMPLETE`: preserve the evidence and report the operational stop;
  do not count it as a failed SAE or automatically request another launch.

The corpus contains 957,912 raw tokens, with 412,273 training-prefix tokens after
the held-out split and 512-token convention. If fallback is needed, distinguish
training-token presentations from unique corpus tokens explicitly before its
launch. No extra corpus or SAE source is authorized here.

`MECHANISM_AUDIT.20261025.json` records the pinned E21/E23 loader and candidate
sealed reconstructions for the later stage. Its audit inspected provenance and
ID coverage only. All 2,100 test pairs appear reusable; dev Oracle reconstructions
cover only 291/2,100 IDs and will need completion for dev-trained policy-code
probes. AR returns raw vectors: form `h - R_win` and `R_win - R_ol` in raw space
and then use the successful SAE's own normalization. R1/R2 stay as registered.

## Validation and custody

`VALIDATION.20261025.json` records CPU checks. `SECRET_SCAN.20261025.json` records
the pre-commit scan; the Integrator scans again before pushing. All output-bearing
E35 work is pending the gate result. No inference or outcome is implied by this
preparation packet.
