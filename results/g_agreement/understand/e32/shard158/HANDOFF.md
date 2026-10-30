# §159 item 6 E32 independent shards

Use LAUNCH_REQUEST.json, superseding the barrier request f0ed49b5. Source d4b1f458. Authority: user instruction citing 6d854a86 (commit not available locally at preparation).

Serialise Mac uploads, one active upload at a time, slots 0 through 5. Create/stage pods just in time. Each shard starts independently after verifying its upload and capture, and passing its own three-row W1 score-parity gate. No exchange directory, cross-shard barrier, synchronisation or wait is required. The parity gate, model loading and warmups remain inside the science clock as before.

Six fixed row shards retain all 25 rows, 2100 items, six arms and both candidate sets. The unchanged custody allocations are 13333 s for slots 0–4 and 13335 s for slot 5: exactly 80000 s total, including setup, science and retrieval. Initial setup <=1600 s per shard; science min(1.5 F_shard + 360, 16000) s, bounded by custody deadline minus 120 s retrieval. Hardstops do not extend. No extra relay custody.

Each worker seals separate VALIDITY_INPUTS.jsonl containing arm A and semantic-row arm B, alongside the complete scores. Workers make no global validity decisions. Once-only analysis first verifies all pulls, seals, parity and bindings. It decodes only validity inputs, checks exact coverage, and applies the unchanged global baseline rule (W1 A within 0.03 of E25 on every row) and content rule (B AUROC >=0.75 on >=7/9 semantic rows for each candidate set). Under item 6 any failed global validity gate invalidates the whole acquisition. Full science files are hashed for integrity but not decoded before these gates pass.

On failure the analysis writes a sealed INVALID report, uses no shard science, runs no scientific analysis, and retains the once-only lock. On pass it opens every shard's scores, verifies the full unique 25200-record grid and exact equality with validity inputs, then invokes unchanged e32_analysis. No threshold, arm or scientific estimator changed.

Run ANALYSIS_COMMAND.json exactly once, with the original verified final-pull symlinks specified by ANALYSIS_SPEC.json. Paths and existing owner lock are unchanged. ANALYSIS_COMMAND_SEAL.json pins the command/spec and analysis source; REQUEST_SEAL.json pins the whole request. No registered analysis or GPU run was executed during preparation. 14 CPU tests passed, including invalid-before-science and complete sealed merge. All source/archive/request/analysis pins verified.
