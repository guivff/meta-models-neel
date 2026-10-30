# E23 source gate — blocked by one registered hash discrepancy

E21's registered post-pull analysis completed once in `189f6efb`. Its primary prediction did not meet the threshold: Spearman rho 0.477435, 95% CI [0.135572, 0.739861], versus the registered minimum 0.50. See `../e21/analysis/RESULTS.md`; do not rerun it.

E23 Step 0 was posted in `a76c1cad`. `SPAN.json` establishes a following span of 1–32 tokens targeting the single residual immediately before the span, without position averaging. F16 is in-contract; P32 and Pfull are off-contract. Outcome (c) does not apply.

## Pinned source receipt

All six specified text files were fetched individually at `Jarus77/mats-nla-workspace@a8e41f4a31d654ccc29e2d9105abb2aac38ad5eb`; no clone was made. `SURAJ_FILES.json` records full SHA256s, pinned Git blobs, registered abbreviated SHA256s and per-file checks. All six Git blobs match. Five registered SHA256 abbreviations match. One does not:

- File: `experiments/07_template_mining/templates_frozen.json`
- Registered in §117: `09156722…d923b`
- Actual SHA256: `09156722b059edb99d01e919c29b2ff660e37cba3152f2d3ce67f3272d3e923b`
- Actual suffix: `e923b`
- Pinned Git blob: `fe84815ad09e14b8d926eaf319258ff55e5b3c67`
- Exact UTF-8 size: 278756 bytes

The latest `r/blindspot` brief was checked again and still has the same abbreviation (brief Git blob `f4f84c93f8a71db50f39e033e69e1c5a69e9fe8d`, identical to clarification 2 at `1642d63e`). This is consistent with a transcription error, but the worker must not silently replace a registered hash. A dated coordinator correction to this hash is needed before the source gate can pass. The original file and registration are preserved unchanged.

No files need to be staged by Guiv. The files are present under `cache/g_agreement/understand/e23/upstream/`, retaining their upstream paths.

## Items and parity inputs

The three banks each contain 200 unique IDs and 200 unique clusters. Each has 40 `mine` items, 20 per value, and 160 `select` items, 80 per value. Preserve `mine` as dev/probe training and `select` as test. Set-S M2 uses all 200 items in grouped five-fold CV; M1 and T train on mine and score select. Previous reader generations were not used for this metadata audit.

The three stored activation files were copied individually from an existing local checkout, with their Git blobs independently checked against GitHub directory metadata at the pinned revision. Their full SHA256s are in `SURAJ_FILES.json`. Each contains 200 IDs and tensors of shape [200, 5120] at each of layers 40, 42 and 44. These are parity inputs only. Fresh E23 captures must pass cosine >= 0.999 on every item at every required layer before scores. No activation parity has been run and none is claimed.

## Status and next work

`BLOCKED_SOURCE_GATE`: do not provision or launch from this handoff. This is a source audit, not an executable launch request. E23 collection, scientific analysis and the warmed forecast packet remain to be implemented and tested after the hash correction; F has not been measured. The registered cap remains min(1.5F + 360, 5400) seconds, setup 1500 seconds. No GPU/model/API work has occurred.

The implementation must use clarification 2: raw M1; the mine-trained set-S direction for primary set-S results; W1 transfer as secondary only; value-independent same-row/set Mis with F16-trained M2 applied without refitting; opposite-value Swap as secondary; P32/Pfull labelled off-contract throughout. No scientific choices have been changed by this audit.

Reproduce the CPU source gate from the repository root:

```sh
python -m projects.g_agreement.understand.e23_sources --root cache/g_agreement/understand/e23/upstream --out results/g_agreement/understand/e23/SURAJ_FILES.json
```

Expected current exit status is 2, with exactly one `registered SHA256 mismatch`. The source-gate tests pass: `python -m pytest projects/g_agreement/understand/tests/test_e23_sources.py -q` (10 tests). Tests cover both ends of the hash, preservation of splits/clusters, rejection of changed/missing banks, independence from previous readouts and a matching Git blob failing to override a mismatched SHA256.
