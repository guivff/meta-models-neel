# E36 §149 once-only integrator analysis — 2026-10-26

Use this committed entry point from this W-text worktree; no GPU and no push by W-text.

```sh
python <W-text worktree>/results/g_agreement/understand/e36/overnight149.py e36
```

Verified-pull directory (may be a symlink to the integrator's already verified pull):
`<W-text worktree>/results/g_agreement/understand/e36/cache/verified_pull_149/out`

Before invoking, create exactly `<W-text worktree>/results/g_agreement/understand/e36/cache/verified_pull_149/RECEIPT.json` with this schema and the actual verified output seal digest (not the example marker):

```json
{"experiment":"E36","issuer":"integrator","verified":true,"seal_file":"OUTPUT_SEAL.json","seal_sha256":"ACTUAL_64_HEX_VERIFIED_OUTPUT_SEAL_SHA256"}
```

The seal and every member are verified by the command. E36 and E41 consume the same complete E36 pull, so their `out` paths may link to the same directory. E29 consumes W12's completed asked-reader pull, never the earlier base-Qwen score pull. No partial output is accepted.

Exact output: `<W-text worktree>/results/g_agreement/understand/e36/analysis_overnight149`. Exact attempt lock: `<W-text worktree>/results/g_agreement/understand/e36/OVERNIGHT149_ATTEMPT.lock.json`. The attempt lock is reserved before all validations; on ANY failure do not retry, delete locks or edit code. Hold for W-text. Existing analysis directories/locks also forbid reruns. Commit the sealed output files unchanged with label `§149 RUN-BY-INTEGRATOR`, including the attempt lock; keep private/raw files in ignored cache. The owner verifies and posts verdicts in the morning. No human coding or judging step is included.

The code and dependencies are bound by `<W-text worktree>/results/g_agreement/understand/e36/OVERNIGHT149_CODE_SEAL.json`; exact command argv, receipt and output paths are bound in `<W-text worktree>/results/g_agreement/understand/e36/OVERNIGHT149_COMMANDS.json`.

Scope: all 25 rows; frozen W1 grouped test-family probe and acquired channels. H1/H2/H4/H5 unchanged. H3 follows §132 clarification 3: the fixed six rows, ≥4 with value-word minus descriptive ≥0.15 and paired item-bootstrap CI lower>0; fewer than four present means NOT_EVALUABLE. Four state-row contrasts are descriptive. No E30 external eligibility ruling is now required. No acquisition code or staging archive changes.
