# §79 selection receipt for W-core §84

No selection exists merely because this export contract is prepared. Never emit a placeholder candidate receipt.

Immediately after the real ranking is sealed:

1. Verify the native pull/prediction seal and complete unchanged CPU analysis. Commit the small ranking artifacts: TOP10.json, RESULTS.json, RESULTS.md and ANALYSIS_SEAL.json. Keep large probe OOF output in cache, preserving its seal/hash. Push that selection commit immediately (local git, pull --rebase first).
2. Resolve the final published selection commit to its full 40-character SHA. Run `projects.g_agreement.blindspot.screens.export_selection` with `--source-commit`, repository-relative `--selection-file` pointing to committed TOP10.json, and `--out` for S84_SELECTION_RECEIPT.json next to it. The commit must actually contain TOP10.json, RESULTS.json and ANALYSIS_SEAL.json. Export checks committed-byte hashes and the unchanged registered selection/order, then calls W-core’s validate_selection_receipt.
3. The receipt contains exactly source_commit, selection_file, selection_sha256, section79_features (exact order, no resorting), section81_features=[]. It refers to the selection commit, avoiding a self-referential commit hash. If zero candidates pass, do not invent a receipt or fill excluded rows; report no eligible selection. One to ten is W-core’s accepted contract.
4. Immediately commit/push the receipt and a HANDOFF line addressed to W-core and the integrator, naming the published selection commit, receipt path, exact ordered feature list and hash. No §84 items before these committed artifacts. No relabeling or changed eligibility.

This CPU-only exporter is separate from the published/live GPU package. Preparing it does not modify a pod, the live scorer, the source seal used for capture, or the frozen ranking rules.
