# Latest addition: standalone W4 aggregation

HANDOFF W4 aggregation: `r/blindspot-mech`; separate `w4_aggregate.py` implements the 08:50 rule; 200 offline tests passed in 11.66 s; P3 review requested through committed receipt after direct app delivery returned MCP -32000. `ar_tests.py` remains unchanged at the approved hash. No GPU run.

Run `python -m projects.g_agreement.blindspot.w4_aggregate --input ANALYSIS/metrics.swap.json --out NEW_AGGREGATE_DIRECTORY`. The derivative preserves per-row outcomes, controls, site and inference scope. Separate blind-spot and semantic denominators each require >=70%; the exact integer test is `10*n_met >= 7*n`. An empty group yields NOT MET. There is no item/pair weighting or pooled fraction. The CLI checks an existing input score seal and seals its metrics, provenance and CPU receipt.

P3: please review only this new helper and its test file. Exact hashes are in `w4_aggregation/P3_REVIEW_REQUEST.json`. This does not replace or modify your frozen-source approval or BRIEF re-signing.

# W-mechanism exact-byte handoff

HANDOFF W-mechanism: `r/blindspot-mech`; P3 source binding PASS; separate raw-units check PASS; OFF-NATIVE at block 44; no GPU/model experiment launched.

`ar_tests.py` is frozen at SHA256 `69b1991881413ea5b07bd469427b1afca13538a2d065e7da39919878044db769`, matching P3 approval commit `0584f35e139b9b1ff05528a069800c77b7c51dc6`. Any edit needs a fresh review. Both original reviewed test files also match their approved hashes.

The separate `test_ar_units.py` checks affine changes of raw coordinate units, uncentred/unwhitened reconstruction, and the actual sealed collect-readouts → P3 reconstruct → collect-residuals path with CPU doubles. It verifies exact frozen greedy text, block 44, item order, AR output position, and fails if a whitener is applied. This is a code contract check, not model fidelity evidence.

Validation: 50 mechanism tests passed; the full vendored-reader and blindspot suite passed **174 tests in 10.99 s**. The final upstream update after this check contains request/receipt/log changes only. No W-core, P3, or vendored source file is edited by this handoff. `compute.history.jsonl` holds only mechanism records, avoiding edits to W-core's shared logs.

The latest `origin/r/blindspot` was merged, including W-core outputs, and `git pull --rebase` completed from the verified local mirror before publication. The shell cannot resolve github.com, so publication uses the connected GitHub Git-data API. Only the separate mechanism branch is published; the owner merges it.

Remaining launch details:
- The exact P3 receipt and evidence are copied unchanged as `P3_APPROVAL_0584f35e.json`/`.md`. The receipt binds an older BRIEF hash; the immutable gate rejects it against the current BRIEF. P3 must rebind the receipt before launch. `APPROVED_SOURCE_FREEZE.json` records both hashes.
- The approved source reports per-row W4 outcomes. Under the 08:50 note, the verdict step must require ≥70% of tested blind-spot rows AND ≥70% of tested semantic rows. No aggregate CONFIRMED result is claimed here.
- W4 stays OFF-NATIVE at block 44 pending Camila. No allocation is requested here. Fidelity/residual/swap caps remain 0.3/0.3/0.5 GPU-h; optional SAE remains unlaunched.

`dry_run.json`, `INPUT_SEAL.json`, `validation.json`, and `P3_REVIEW_REQUEST.json` are historical preparation receipts from the shared worktree. The request is superseded by P3's approval. The dry-run used the two pilot item inventories with synthetic arithmetic, zero model forwards, and zero GPU-hours; it contains no empirical fidelity result. `units_validation.json` is the current full-suite receipt.
