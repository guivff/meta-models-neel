# E24 implementation before capture

Authority: §118 at 03b8a81c, including dated clarification 1 at 2a41117e. Scope, regex and judge prompt were committed at 7242affd before any E24 model invocation. Expanded branch: 28 rows for C1/C3/C4, 19 structure rows, Holm family 190. C5 retains the original 25 rows and 2,100 sealed test continuations. All results are exploratory.

## Observed source discrepancy — launch blocked pending correction

At the exact specified S14 commit a8e41f4a31d654ccc29e2d9105abb2aac38ad5eb, `experiments/14_ar_blindspot/modal14.py` has SHA256 `339be5ba5d830dc50cd4d0a5fcb88c3c74b012a4b590a883b10c7dfa351de8fc`. The clarification abbreviates it as `339be5ba…a8de8fc`. The prefix matches; the suffix does not. The five other specified hashes match. DERIVATION.json records all full hashes. Staging uses the exact pinned commit/path; the worker requires the integrator to attest a published correction to the full actual hash before execution. No alternative source or pairs were substituted.

There is also an anticipated C6 cross-check limitation, not a changed rule: S14's published OL `analysis14_*.json` explicitly uses whitened AR output with a reconstructed-span reference. Clarification 1 specifies fresh source-activation class gaps. E24 follows the clarification's raw-space reference and the unchanged `statement_shift` formula. Every pair's layer-44 ratio is compared to the published OL ratio with tolerance ±0.05; any miss is retained and C6 is labelled NOT REPRODUCED. No change of reference, space or sign after outcomes.

## Acquisition and custody

Default four H200 pods (each >=140 GB GPU memory; enough host memory for two resident 27B model loaders). Both pinned Oracle and official AR models stay resident; no automatic offload, alternate model, truncation or batch reduction. `/weights/venv-kernels/bin/python` is the launch environment. Setup limit 2,400 seconds per pod. Total provider custody, including setup and the 180-second retrieval reserve, is conservatively bounded to 12 GPU-hours: with four pods each receives at most 10,800 seconds from provider creation. No restart/retry or budget reset.

Slot 0 captures all 4,704 W1 dev/test items once using the existing W1 right-padded block-output hook at the final real token, collecting all eleven grid layers in that same pass. It verifies cosine >=0.999 on EVERY item at 44, writes separate per-layer seals, then publishes the capture seal. Other slots receive this exact sealed capture; they never recapture W1. Integrator should create those pods after the shared capture is available, to minimize idle custody. Each slot scores its own complete anchor, with the lowest-index completed slot providing canonical layer-44 results. R0 checks every pod's anchor; failure on any pod makes that row uninterpretable globally.

Four-pod shards in registered priority order:

- Slot 0: 44, 20, 28, 48.
- Slot 1: 44, 60, 36, 56.
- Slot 2: 44, 32, 40, 24.
- Slot 3: 44, 52.

The same worker supports one to four pods, with round-robin assignment of non-anchor layers in global priority order. Pod count is fixed in the integrator's assignments before execution. Never change pod count to reset a failed forecast.

All capture, model warmups after loading, timing, waiting and scoring count against the science clock. After capture is sealed, each slot warms each native channel once and measures three units per assigned layer. Timing outputs are discarded. The C1/C2/C7 representative row has the longest frozen candidates for that channel; C5 uses the longest frozen continuations; C4 uses the C1 representative batch, with the fixed greedy 128-token ceiling. Estimates use median unit time and the exact number of production batches. Forecasts are estimates, not evidence that the GPU run has passed. Absolute deadlines and failure seals remain active if throughput differs.

The CPU `admit` command consumes all warmed forecasts and selects the longest GLOBAL priority prefix that fits. Every selected layer retains C1–C5. It reserves min(1.5F + 360, 10,800) science seconds per pod, additionally bounded by custody, and checks summed reserved custody <=43,200 seconds. Current waiting time is included in F. It then tries the complete C6 layer set, followed by the complete C7 layer set; neither can displace a Tier 1 layer. An immutable, atomically published admission includes all forecasts and hashes; each worker recomputes it before accepting it. If even complete anchor Tier 1 cannot fit, stop NO_FIT. Deadline exhaustion leaves INCOMPLETE output, never a reduced claim set represented as complete.

If C6 is admitted, slot 0 captures the 600 S14 items once at 20/36/44/60, gates every block-44 vector against the stored S14 vectors, and seals before any production C6 scoring. Other pods consume the same capture. Every pod reserves time for this capture and transfer. Copy data first and publish seals last/atomically. No new base-model continuations are generated anywhere.

## Scoring and CPU analysis

C1: unchanged W1 native candidates, sum token likelihoods and average frozen phrasing log-odds. C2: average E15's dev-valid pairs only, native `- ` prefix, same-layer opposite donor from the exact W1 mapping. Both true and swap per-pair values are retained. Table column remains invalid for C2.

C3: one logistic fit per row and layer on dev only, W1 standardization and lambda=1e-3/200 LBFGS iterations; test scores and raw-space directions saved. C4: one retained native greedy readout per test item, W1 settings. Frozen regex is never revised using outputs. C5: official AR with the actual layer tag on E1b's exact next-16 text, projected onto that layer's raw C3 direction. No whitening or sign flip. C7: all eight frozen E16 scores on dev/test; highest dev AUROC selects a phrasing, lowest index breaks ties; all test phrasings reported.

The once-only CPU analysis verifies score/capture/input/source seals before joining labels and fitting. Template-cluster bootstrap: 2,000 shared draws per row, seed 20261025. R2 uses the fixed 190-cell Holm family, including p=1 for omitted or anchor-invalid cells. R1 uses W1's actual rule (reader AUROC at least 0.15 below probe for >=75% of eligible structure rows), gated at C3>=0.80; across-layer support still requires at least nine layers, never a smaller denominator after dropping layers. R3/R5 retain all seven E15-valid rows in the majority denominator, with anchor-invalid rows unresolved. R4/R6 cannot silently become supported by excluding anchor-invalid rows. R5 is conditional on R3 holding; an empty conditional set is not evidence.

C4 audit: the CPU analysis writes 20 readouts per retained layer (one seeded item from each structure row plus one additional item), with the same item set across layers. The judge sees ONLY opaque ID, row, A/B definitions, text and the committed prompt. The key, layer, truth, scores and regex are withheld. Freeze all codes as `codes.jsonl` and `JUDGE_SEAL.json` before joining. The seal must contain `files`, `packet_sha256`, and `prompt_sha256`. The audit reports every disagreement and never replaces the primary regex score. No E24 judge calls have been made locally.

## Validation

CPU suite covers real W1 capture hooks and right padding with a toy 64-block model, single-pass all-layer capture, per-item parity, native layer/prefix routing, unchanged S14 shift arithmetic, fixed Holm family, dev-only C7 selection, budget suffix dropping, optional-tier exclusion, full frozen-bank populations, blind packet contents, and a synthetic end-to-end analysis with actual dev-only probe fits and once-only lock rejection. No GPU throughput or real E24 scientific result is claimed by these tests.
