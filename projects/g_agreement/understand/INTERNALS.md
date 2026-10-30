# E3 and E4 implementation freeze

**Launch update:** the user's packed E3 → E4 instruction supersedes the separate
process execution instructions below. `PACKED.md` is authoritative for execution;
all scientific inputs and analyses described here remain unchanged.

Authority: `../BRIEF_UNDERSTAND.md` §§90–91 and §96, registered before any E-run.
Exploratory: report every row, failed cell, unavailable reader and budget stop.
No confirmatory thresholds or post-data sign flips. No E3/E4 model results exist
at this preparation stage. The integrator alone pushes and operates pods.

## Inputs and estimands

The frozen W1 input, target-score, NLA-score and final-analysis seals are checked
before selecting the exact 16 rule-(i) rows plus nine evaluable semantic rows.
E3: all 168 items/row (4,200, 12 clusters/row). E4: all 84 test items/row
(2,100, six clusters/row). Directions are W1 dev-only A-positive unit vectors,
raw block 42 for NLA, raw block 44 for Oracle/J. Classes and phrasings never change.
Worker directories contain no per-item values or template-cluster labels.
The separate `labels.DO_NOT_STAGE.jsonl` stays local and is opened for analysis
only after verification of the aggregate and phase score seals.

E9 requests all 40 W1 binary rows, so its within-E4-budget target arm includes
3,360 test items, not just the 25 E4 rows. The target estimand is the exact vector
`D_u logits_next(h)` at block 44, keeping the item's original context and the other
block outputs unchanged. Save all vocabulary derivatives, their RMS and L2 norm.
The original token sequence is replayed with the Oracle adapter disabled and its
last real token's block 44 vector replaced by the sealed W1 vector. This is no new
target activation dataset. It is not a gradient of a selected top token, a logit
lens proxy, or a finite-difference approximation.

## E3: decoder internals

W1's feature phrasings are **candidate continuations**, not user questions in
the carrier. Consequently one forward pass through the native candidate-free
asked head is the unambiguous answer-independent probe input: Oracle's carrier
only, NLA's carrier plus its frozen `<explanation>\n` prefix. No answer tokens
are fed, no generation occurs, and neither value's continuation is chosen.

Capture every zero-based decoder-block output at the marker and final head
token. Oracle injects at its input embedding; NLA injects at output of block 1,
so NLA block 0 and its embedding are deliberately pre-injection controls.
Embedding stages are retained separately from residual layers. All states are
stored float32 without normalization; raw input directions are never applied to
reader-hidden coordinates. Native forward batch 32, all items exactly once in
production; warm/timed duplicates are discarded and never enter the dataset.

Five deterministic template-grouped folds (seed 20261024), W1 logistic fitter
lambda 0.001, training-fold-only standardization, A-positive scores. Do not choose
a layer, flip below-chance AUROC or fit a scaler on held-out items. Report layer
by row heatmaps for each position and class curves. W1's asked AUROC comparator
is test-only; E3 probes use dev+test cross-validation, so their difference is
descriptive rather than a matched held-out difference estimate.

**Architecture clarification, before compute:** native J-lens is a static J44
linear map and token cosine readout. It has no transformer layers, injected
token, or pre-answer token. E3's residual-layer heatmap is NOT APPLICABLE for J.
Retain honest `input` and `J_h` named stages and probe them separately. Never
invent residual layers or substitute a different model for this reader.

## E4: differentiable native scoring

Differentiate the mean of W1's two frozen A-minus-B contrasts. Oracle/NLA use
the summed candidate token log-probability difference; J uses its native
max-token-variant cosine contrast and is explicitly not a log probability.
The vendored public methods disable gradients/convert to floats, so a tested
differentiable implementation preserves their exact carrier, tokenizer,
injection normalization and algebra. Model parameters are frozen and in eval
mode. Each phrase pair has its own backward call and releases its graph.
Production batches contain 16 activations/32 candidate sequences; target JVP
batches contain 8 original prompts. No adaptive batch shrink or subsampling.

Per-row gradient cosines use the matching raw-space probe direction, a fixed
200 isotropic unit-direction baseline, and paired template-cluster bootstrap
intervals (2,000 draws). Report zero-gradient count and the nonzero-only mean;
zero gradients contribute zero to both overall alignment and baseline means.
Fresh asked scores are saved for descriptive comparison with W1 reference
scores; numerical differences do not authorize tuning, rerunning or sign flips.

Stack uncentered raw gradients across all 25 rows per reader; exact SVD, requested
k = 16, 64, 256. Save singular values and actual basis vectors. If numerical rank is
less than k, report effective rank and project onto available singular vectors;
do not complete a nullspace arbitrarily. Report each direction's squared
projection fraction and random-direction references. No new result-based row
selection is allowed. Missing rows explicitly make a pooled analysis partial.

## Integrator execution and budget

One request per experiment, one GPU each. Separate processes release each model
before the next. Native local assets are checked against W1 pinned hashes;
offline mode prohibits downloads. J-lens loads only the pinned unembedding and
J44 rather than loading a whole 27B transformer. All setup, including repeat
loads and asset checks, shares a cumulative 1,500-second allowance.

For every phase run one unscored warm-up, then three timed identical units;
use their median times the full phase's number of production units. Choose a
full batch with the longest frozen native candidates/context before any score.
Timing includes host transfer, disk serialization/fsync and checksum. All four
forwards are charged to science and discarded. First calibrate every phase,
then admit only if `used_science + sum(F_phase) <= min(1.5*sum(F_phase)+360,2160)`.
The resulting cap is fixed for collection. The cap includes all readers, E9
inside E4, timing forwards, serialization, hashing and aggregate sealing.
The integrator supplies an exact pod ID, original assignment, single-GPU count,
deadline, matching code/input hashes and verified external hard stop. The local
alarm, cumulative locked ledger and per-phase attempt journal cannot allocate,
renew or stop a pod. Duplicate attempts fail closed. A crash/interruption needs
integrator accounting reconciliation; deleting the ledger is not a retry plan.

Exact target JVP uses reverse-over-reverse autodiff; real fused attention or
DeltaNet kernels may lack second derivatives. The target calibration exercises
this path before admitting full E4. Unsupported kernels, OOM or forecast NO-GO
are reported; there is no silent approximation, reduced population or cap
extension. A calibration failure may mean no E4 production is admitted.

After collection, seal all outputs before joining labels. Preserve and report
partial outputs after failure. If the science cap leaves no time for sealing,
the integrator pulls the already written artifacts and completes CPU-only
sealing locally after reconciling the ledger; this does not authorize further
GPU work. Actual setup/science/provider-custody totals must be appended to
`results/g_agreement/{log.md,compute.jsonl}` by the integrator after execution.

## Commands

`pod_run.sh E3 INPUT_PARENT OUT ASSETS ASSIGNMENT` (and similarly E4) runs the
separate calibrations, aggregate gate and production phases. It operates only
within an already assigned pod and seals outputs on exit where budget permits.
Stage only `INPUT_PARENT/e3` for E3; `e4` and `e9` for E4. Never stage the private
labels or the parent directory wholesale. After pull, use:

```
python -m projects.g_agreement.understand.analyse --experiment E3 --inputs INPUT_PARENT --scores OUT --labels LOCAL_LABELS --out results/g_agreement/understand/e3/analysis --cache-out cache/g_agreement/understand/e3-analysis
```

Use E4 and e4 paths for the gradient/subspace/E9 report. Keep large arrays under
cache, commit only small reports and figures. Read the per-experiment launch
request for exact source/input seals; it is a request, not a pod assignment.
