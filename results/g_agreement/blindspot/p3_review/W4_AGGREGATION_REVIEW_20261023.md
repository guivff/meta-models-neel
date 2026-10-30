# W4 aggregation helper review

Source: r/blindspot-mech `6df7aa619d3a894a237ff9b1850f8477d2de29b7`, `projects/g_agreement/blindspot/w4_aggregate.py` SHA256 `74f35b6aba7af7ce0451f0819083671b3c73a0eac37ff25e548b8e00c69a24c6`.

**Threshold implementation: PASS. Scientific CLI provenance: one change requested.** This review does not change the prior exact-byte approval of ar_tests.py or the brief rebinding.

The helper correctly requires ≥70% in each of the tested blind-spot and semantic row groups independently, using exact integer comparisons. Every tested row has one vote, failed rows remain in the denominator, no pooled success can hide a failing group, and empty groups fail. Duplicate features, unknown row classes and nonboolean rule flags are rejected. All per-row fields and OFF-NATIVE/EXPLORATORY scope are retained without mutating inputs.

## Requested change — P2

`w4_aggregate.py:82–86`: the scientific CLI verifies the input analysis seal only **if it exists**. With SCORE_SEAL.json absent, the same per-row JSON is still accepted and a new sealed CONFIRMED aggregate can be emitted with `input_score_seal_sha256: null`. This permits an edited/unsealed copy to bypass the provenance gate. The upstream `ar_tests._save_analysis` always seals metrics.swap.json, so legitimate analysis needs no such fallback.

Require SCORE_SEAL.json for the CLI, verify the input file is covered, and preferably require `SCORES_SEALED_ANALYSIS_SWAP`; retain the pure in-memory aggregation function for synthetic tests. Replace the unsealed-success test with a missing-seal rejection. Existing sealed-input rejection tests should remain. Until then, use only a verified sealed upstream analysis for any scientific verdict; the arithmetic helper itself needs no change.

## Validation

26 synthetic CPU tests passed in0.04s on a read-only producer snapshot copied to /private/tmp, including exact70% boundaries, no pooling, empty groups, malformed flags/classes/duplicates, equal row weighting, deep-copy preservation, changed/uncovered sealed input rejection, CLI output sealing and the current unsealed-input acceptance. Initial snapshot setup omitted the brief file; after restoring the exact source-commit brief, all26passed. That fixture omission was not a producer defect. No model/GPU/API calls or scientific result were computed.
