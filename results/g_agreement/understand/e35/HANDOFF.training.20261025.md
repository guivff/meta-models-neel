# E35 conditional fallback request — 2026-10-25

The transfer rerun completed its registered 50,000 tokens and failed both
criteria: FVU 0.41063467458674496 and 34,369 / 81,920 dead latents
(0.41954345703125). `CUSTODY.gate-rerun1.20261025.json` verifies its result,
clock, assignment, sample and 16 source pins. The two large gate arrays were
not included in the local delivery. Their seal pins are preserved; this request
recaptures the unchanged held-out sample for the different, final fallback SAE.
It never repeats the transfer evaluation.

FineWeb-Edu revision `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` was pinned at
13:31:22Z, before the transfer gate finished at 13:56:52Z. The decomposition
source, rubric and blind prompt were committed before this worker opened that
result. No production latent selection, judge call or decomposition has run.

`LAUNCH_REQUEST.training.json` is the single conditional training request. Its
configuration, source pins and source order are fixed before any fallback
training. The remaining staging and assignment steps below are explicit launch
prerequisites, not evidence of a measured fit or a completed token cache.

## Integrator sequence

1. Scan and publish the committed source. Preserve all previous gate guards,
   outputs and failed attempts. Use the published commit for both CPU staging
   and the GPU assignment; the worker checks that they match.
2. On CPU, build the token cache once with `training_stream.py`. Supply the
   exact §79 corpus and manifest, the pinned target tokenizer, the committed
   FineWeb pin and `FALLBACK_TRAINING_PLAN.20261025.json`, and the published
   source commit. The required output is
   `cache/g_agreement/understand/e35/training-tokens-20261025`. This is permitted
   to stream public FineWeb text on CPU. All network downloads and token-cache
   construction finish before GPU rental. Stage the complete cache and its
   seal. The builder refuses uncommitted source bytes and the verifier
   independently reconstructs all 1,910 §79 training-document token records.
3. Stage the pinned Qwen3.6-27B model/tokenizer, unchanged §79 corpus/manifest,
   the four small transfer-rerun evidence files, and the request's source files.
   Reuse the successful forward-kernel environment. The target is frozen;
   there is no target-model backward pass or E28-specific training overlay.
4. Complete `accounting.training.template.json` in cache and hash it. Known
   usage is at least 434.2 + 538.6674928665161 seconds; the second number ends
   at the gate worker receipt and is not final provider time. Until final
   provider stop/retrieval time is booked, the conservative mode reserves the
   rerun's full 3,600-second allocation, for 4,034.2 prior seconds. Record the
   exact three pod IDs. The template's `NOT_BOOKED_TEMPLATE` status is rejected;
   a verified receipt uses `FINAL_OR_CONSERVATIVE`.
5. Fill `assignment.training.template.json`: one GPU, the exact pushed source
   and request hashes, token-cache seal, accounting-receipt hash, provider
   creation time, absolute setup/deadline times, external hardstop and hold
   evidence. Allocation is at most 10,800 seconds, with at least 3,600 seconds
   reserved for a later stage; prior + allocation + reserve must be at most
   21,600. Setup is at most 1,500 seconds and retrieval reserve is 180 seconds.
6. Launch the request's exact command once under the Integrator's current
   §135 limits (12 pods, three-minute spacing and deploy lock). An eligible
   H100 80 GB fallback still needs the worker's memory admission: at least
   80 GB total and 20 GB free after loading the target. Measured pilot memory
   and kernel versions are retained. No fit is claimed before the pilots.

The locally available tokenizer candidate is
`<repo-root>/cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json`;
its required SHA256 is
`5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42`.
The builder verifies it rather than trusting this locator. The §79 corpus is
`cache/g_agreement/blindspot/s79/frozen/corpus.jsonl`; its manifest is
`results/g_agreement/blindspot/s79/CORPUS_MANIFEST.json`.

## Fixed execution

Train a 16,384-latent, k=64 TopK SAE on exactly 20M unique token occurrences:
all positions of all §79 training documents first, then the first pinned
FineWeb occurrences in file/row order. Preserve short tails and the final partial
document. Fixed 512-token within-document chunks reset context, never pack
across documents, and never train padding or special tokens. The CPU cache
contains token IDs and source spans, not activations. The GPU holds at most a
4,096-position training buffer and retains no training activation corpus.

All hyperparameters and initialization are in
`FALLBACK_TRAINING_CHOICES.20261025.md`. External normalization is raw identity;
the initial affine biases and loss scale use only the first training batch.
There is one 20M-position pass, 4,883 updates, no replay, no interim checkpoint
selection, and no gate-based tuning.

The non-resetting science clock begins before pilots. Three full capture
timings, three discarded scratch optimizer timings, and three training-only
gate-path timings price the exact token-cache chunk count, all 4,883 updates
and the unchanged 487-document gate. Scratch optimizer timing forces the full
AuxK path to cover its cost; that override is forbidden on retained training.
The scratch model is discarded, then the actual trainer starts from the fixed
seed. Admission requires F + 180 seconds for sealing to fit within
min(1.5F + 360, absolute deadline − retrieval reserve − first science time).
The hard alarm is tightened to that cap after admission.

Only a completed final checkpoint is gated. The final gate uses the unchanged
50,000-token selection and pooled FVU/dead-latent code, once. PASS permits the
already frozen blind labelling workflow and, after its completed receipts,
decomposition. FAIL means **no adequate SAE; stop E35**. NO_FIT/INCOMPLETE is not
a scientific gate failure. Scientific validity failures are marked ineligible
for retry. Operational classification does not issue another launch request;
the once-only guard is never deleted or bypassed.

Return `OUTPUT_SEAL.json`, `GATE_RESULT.json`, `TRAINING_RESULT.json` when
complete, normalization and memory/runtime receipts, plus the checkpoint under
cache. Book actual provider time including setup, pilots, gate, sealing and
retrieval. The Integrator owns pushing, staging and launch; worker preparation
has used zero GPU-hours.
