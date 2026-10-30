# W-mechanism implementation and handoff

2026-10-23. Governing rules: BRIEF_BLINDSPOT §71–§73 and §80–§81. BRIEF_W is superseded.

`ar_tests.py` implements shared W2/S2 fidelity, W3's primary Oracle-reconstruction residual,
and W4 with the self, random same-domain residual, and AR-only controls. Construction is
raw block 44; all W4 scores are **OFF-NATIVE** for the block-42 NLA. Block 42 is not enabled.
The approved source reports per-row W4 outcomes and control contrasts. The 08:50 note
requires CONFIRMED only when the per-row rule holds on at least 70% of tested blind-spot
rows and at least 70% of tested semantic rows. Apply that rule at the verdict step; this
frozen source does not emit that aggregate verdict. No numerical threshold is invented
for approximate-chance controls.

## Reuse and provenance

- P3 remote reference inspected: `origin/r/p3` at `c176e2595564324eb919b242c59e13895086f944`.
  That ref contains `r_bench/s58_run_ar.py` and `s66_features.py`, rather than `w_claims/ar.py`.
  The existing scaffold `w_claims/ar.py` implements that loader/whitener contract and is reused unchanged.
- Official Oracle code: `a32590085a6070d75f950155d3c2b3db3eec97ef`; pooled L44 whitener
  SHA256 `178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a`, ridge 0.1.
- AR outputs are raw activations. No inverse whitening or direction projection is used in W3/W4.
- W4 directly imports `mats.readers.nla.paired_logodds_templates`, with the same prefix,
  candidate order, phrasing pairs, and averaging convention as W-core. There is no copied scorer.
- W3 uses W-core's active `analysis.grouped_probe` on both h and residuals and requires h's
  AUROC to reproduce the frozen W1 value. W-core exports dev-fitted raw-space directions.
- Original helpers `decompose` and `kl_to` remain only for scaffold compatibility; they do not
  implement current experiments.

## Offline preparation

Run modules from the repository root. Named output directories must be new; nothing is overwritten.

```bash
python -m projects.g_agreement.blindspot.ar_tests plan
python -m projects.g_agreement.blindspot.ar_tests freeze-w1-texts --bank BANK --out AR_TEXTS
python -m projects.g_agreement.blindspot.ar_tests reference-from-w1 --bank BANK --target TARGET --w1 W1_ANALYSIS --out REFERENCE
```

`reference-from-w1` consumes W-core's actual `ANALYSIS_SEAL.json`, `metrics.json`,
`probe_directions.json`, and `probe_directions.npz`. It verifies bank/target lineage, raw
block-44 directions, A-positive value order, and dev-only fitting. Ordinal rows are excluded.
Every binary row receives 20 statement texts per value, two frozen phrasings × ten contexts.

For §79/S2, the generic `freeze-texts` and `freeze-reference` commands accept frozen lens
exports with the same bank/target contract. `--definitions` is a JSON mapping from feature
name to `row_class`, ordered `values`, and two `descriptions`; optional `statement_pairs`
contains exactly two A/B phrasing pairs. `--rows` is a JSON list with `feature`, `row_class`,
`probe_auroc`, `oracle_auroc`, `evaluable`, `blindspot`, and `nla_evaluable`. `--directions`
is an NPZ keyed by feature, containing raw-coordinate coefficients/directions; standardized
coefficients must first be divided by the fitted scale. `--evidence` records the upstream
frozen export. Generic definitions must match the sealed bank's values and class.

Stage only files listed in each INPUT_SEAL plus the seal. Never stage `*.DO_NOT_STAGE.*`.
All model phases reject staged label files. Score seals, numeric coverage, item order and
source bindings are verified before analysis opens labels.

## Collection and analysis

These are module commands, not the old `pod_run.sh ar` entrypoint (which refers to the
superseded `collect` command). `--help` lists required arguments for each stage.

1. `collect-fidelity`: frozen statements → raw AR predictions; one shared implementation
   for W2 and S2. `analyse-fidelity` joins frozen statement/item labels only after sealing,
   computes signed projection ratios, and evaluates the separate §71/§80 rules.
2. `collect-readouts`: greedy OL(h), block 44, k=1, 256-token cap, no sampling.
   `collect-residuals`: P3 AR(readout), then h minus that exact reconstruction.
   Separate processes avoid holding OL and AR models concurrently. `analyse-residual`
   compares the identical grouped probes and evaluates §72.
3. `prepare-swaps`: freezes 40 directed test pairs per selected feature, opposite value,
   same domain, template family and length bin (width 8 tokens). Pair selection is seeded;
   item reuse is allowed and uncertainty is clustered by template. The random donor is
   uniform over same-domain items excluding i and j, without consulting its value.
4. `collect-swaps`: requires P3 review of exact source bytes, then scores all four arms.
   Every arm is rescaled to the recipient's original norm. `analyse-swaps` reports donor
   and recipient AUROCs, clustered intervals, and paired contrasts against each control.

If W1 is NOT MET, the W1 adapter marks mechanism inference EXPLORATORY; W4 selection uses
only the two clean case-study rows. W2/S2 formulas are shared but their correlation rules
remain distinct. Undefined real projection denominators are reported, never divided by zero.

## Compute and review receipts

No GPU allocation is issued by this code. `plan` prints the exact mechanism source hashes.
Mechanism receipts are separate from W-core's W1/W5/W1b admission: same integrator issuer,
pod ID, registered/pushed BRIEF hash, pinned source/brief commits, exact source hashes,
provider creation/deadline, independent hardstop evidence and 180-second retrieval reserve.
They also require `gpu_count: 1`, `mechanism_budget` (`fidelity`, `residual`, or `swap`),
`allocated_gpu_seconds`, and `previous_gpu_seconds` for cumulative provider custody.
Worker logs additionally check previous mechanism process time; failed attempts are included.

Fidelity W2/S2 shares the conservative **0.3 GPU-h** cap from the task. W3's readout and AR
stages share **0.3 GPU-h**. W4 has **0.5 GPU-h**. Larger allocation receipts are rejected.
Every run appends commands, seeds, wall time and GPU usage to the shared log and compute ledger.

P3 approval JSON must contain `reviewer: "P3"`, `status: "APPROVED"`, `ar_tests_sha256`,
`brief_sha256`, and a nonempty `review_evidence` reference. The hashes must match current
files. Do not manufacture this receipt. The independent local review is not P3's approval.

## Current execution status

- Two-row offline dry-run inventories the original 200 table-column and 200 parenthesis
  pilot items, freezes 80 statement texts, and tests arithmetic with explicitly synthetic
  arrays. It reports **no measured fidelity**, zero model forwards and zero GPU hours.
- The available pilot readouts are OL layer 42. Pilot block-44 activations/directions,
  complete pinned AR/model weights and an integrator allocation are not present locally.
- P3 approved the exact source bytes in `0584f35e139b9b1ff05528a069800c77b7c51dc6`.
  The source SHA256 is `69b1991881413ea5b07bd469427b1afca13538a2d065e7da39919878044db769`;
  it is frozen unchanged. The original 48 reviewed tests are also unchanged. The separate
  `test_ar_units.py` exercises raw residual units and the frozen greedy OL-to-P3-AR path
  with CPU doubles, including a whitener that fails if used.
- The approval receipt binds an older BRIEF hash. The current immutable launch gate
  therefore still rejects that receipt after the dated BRIEF updates. A P3 receipt bound
  to the current BRIEF is needed before launch; no source edits or approval fabrication
  are made here. Exact review evidence and a binding audit are in the mechanism receipts.
- W3's descriptive NLA-decoder secondary is not collected. Optional §81 SAE is not scheduled:
  remaining GPU after §79/§80 has not been established. No model experiment has launched.
