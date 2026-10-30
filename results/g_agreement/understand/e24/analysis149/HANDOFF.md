# E24 once-only analysis under §149

Execute COMMAND.json argv from its cwd only after all admitted shards are sealed and verified. No complete G-mode pull exists locally at preparation time. These are fixed delivery paths, not claims that the pull has arrived.

Copy or symlink each verified shard output to the exact SPEC.json delivery_paths[slot]. Populate INTEGRATOR_VERIFIED.json at the exact verified_receipt path using the template, retaining exactly all admitted slots in numeric order (1–8); bind each SCORE_SEAL digest and set verified=true only after verification. Do not substitute older failed E24 attempts. No source/plan re-pin is needed when pulls arrive.

The command seals all registered code, input and label hashes, claims an atomic once guard before validation, verifies the integrator receipt, and invokes the unchanged registered e24_relaunch_analysis over every admitted shard. It retains the original bank-level guard as well. Every shard's capture parity, score provenance, R0 and global admission are rechecked before any fit. Any failure consumes this attempt: retain locks and outputs and wait for W-core; no automatic retry.

Commit sealed scientific outputs unchanged labelled §149 RUN-BY-INTEGRATOR. Exclude JUDGE_KEY.DO_NOT_SEND.jsonl and private label/raw files from publication; preserve their local seal custody. No blind coding or judging is authorized by this command. Owner reviews the results in the morning.
