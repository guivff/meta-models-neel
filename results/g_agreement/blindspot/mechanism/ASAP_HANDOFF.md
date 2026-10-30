# W-mechanism ASAP preparation — before any W7/S2 number

2026-10-23. Governing BRIEF_BLINDSPOT §§71–73/76/80 and dated 08:50/09:05 notes. Branch `r/blindspot-mech`, own `wt-wmech`. `ar_tests.py` stays byte-identical, SHA256 `69b1991881413ea5b07bd469427b1afca13538a2d065e7da39919878044db769`.

Order update: S2 reconstructor collection immediately from dc0e1316 (no 15:00 wait); W7 when W-core commits priority dev-only directions/class means and items; W2–W4 after complete W1 rule-(i) rows/activations. An integrator assignment and completed asset staging remain prerequisites. No model or GPU result exists from this handoff.

## W7 operational choices fixed before data

The 09:05 note permits recording choices the rule leaves open. The registered population, 60 items per row, five controls, three signed doses, tokens, PPL 10% constraint, cluster CI threshold and 0.3 GPU-h cap stay unchanged.

- Use `table_column` and `prose_paren`. Select 30 matched opposite-value W1 test pairs per feature (60 items) by SHA256 of seed 20261023 and pair IDs, without using model outcomes. Keep template cluster IDs; labels stay off worker.
- W-core's probe is raw block44, dev-only and A-positive. Require positive dev class-mean projection gap. Base probe vector = unit probe × that gap. Five isotropic Gaussian random directions use seed 20261023, independently normalized to exactly the probe norm, frozen before calibration.
- Predicted sign is frozen: `prose_paren` +A (inside) increases log P(")"); `table_column` −A (toward later columns) increases log P("|"). Both directions are scored. These are hypotheses, never signs selected from results. Use exact bare native single-token IDs and fail if either text tokenizes to multiple tokens.
- Plain additive edits at decoder block44 OUTPUT, last true prefix token, no centring, whitening or norm rescaling. Reuse vendored `mats.capture.steer` and `logits_at`; no reader scoring is involved in W7.
- Use 16 distinct unrelated neutral texts, 64 tokens each, selected by seeded content-independent ID hash, disjoint from W1 IDs. Prefer P3 neutral texts. Full teacher-forced token NLL is measured with the same block44 additive edit at all positions, making calibration conservative relative to the single-position outcome intervention.
- Freeze candidate dose multipliers `2**k`, k = −5,…,3, relative to the dev-gap vector. Require PPL(edited)/PPL(clean) ≤1.10 for BOTH signs and ALL six directions. Choose the largest tested maximum with its half and quarter also safe. These are the three doses. If none qualify, stop without W7 outcomes; no population or threshold is relaxed. This is a finite predeclared dose grid, not an unbounded maximum search.
- Seal dose calibration before observing target outcomes. Forecast remaining target work using measured calibration seconds/token and a 1.5× margin; refuse work exceeding the assignment deadline minus 180 s. Independent provider hardstop remains required.
- For each item/dose, compute predicted-sign × [logP(+dose) − logP(−dose)]/2 for probe and each random. Primary item contrast is probe minus mean five randoms, averaged over the three doses. Use template-cluster bootstrap, 2,000 draws, seed 20261023. A row passes iff its mean >0 and lower 95% CI >0; BOTH rows must pass for W7 CONFIRMED. Report all raw arms and dose means. W7 alone does not establish W1's reader dissociation.

## W7 handoff contract / commands

`python -m projects.g_agreement.blindspot.w7_steering plan`

`prepare --bank BANK --labels LABELS.DO_NOT_STAGE.jsonl --priority PRIORITY_EXPORT --priority-seal INPUT_SEAL.json --unrelated NEUTRAL_IDS.jsonl --out NEW_W7_BUNDLE`

Priority export: sealed `probe_directions.json`, `probe_directions.npz`, `provenance.json`. Metadata follows W-core's existing dev export: top-level `fit_split: dev`; one row per required feature at layer44 with `array_prefix`, `positive_value`, `orientation_flipped: false`, `fit_split: dev`, `dev_class_mean_projection_gap >0`; NPZ `<array_prefix>__unit`. No test class-mean gap is admitted. Provenance binds `input_seal_sha256` to the W1 bank and `direction_space: raw_block44`. The adapter must be reconciled with W-core's actual early export when it lands; do not fabricate an export. `--priority-seal` can name the actual committed seal. The unrelated file has `{id, ids}` records. Commit the small bundle seal/provenance before collection; stage only sealed files.

`run --bundle W7_BUNDLE --assets PINNED_LOCAL_ASSETS.json --assignment W7_ASSIGNMENT.json --out NEW_W7_SCORES --batch 4`

W7 assignment: issuer integrator; `experiment: W7`, `mechanism_budget: w7`, one GPU, exact pod ID; source mapping from `plan`; pinned source/brief commits and current brief SHA; registered/pushed brief; provider creation/deadline; cumulative `previous_gpu_seconds + allocated_gpu_seconds <=1080`; external hardstop attestation; `manifest_committed: true`; exact bundle `input_seal_sha256`. Model assets must match W-core's pinned target revision and file hashes. All custody/model loading/science time remains inside this cap; final 180 s reserved for retrieval. No pod is provisioned here.

`analyse --scores W7_SCORES --out NEW_W7_ANALYSIS` prints one HANDOFF result line. Scores/calibration/provenance are sealed; duplicate/incomplete/nonfinite grids or changed clusters/doses fail analysis.

## S2 separate entrypoint

`python -m projects.g_agreement.blindspot.s2_fidelity plan`

`prepare --freeze COMMITTED_LENS_FREEZE.json --bank LENS_BANK --target LENS_RAW44 --definitions DEFINITIONS.json --rows ROWS.json --directions RAW_DIRECTIONS.npz --out NEW_S2_PREPARED`

The lens adapter must supply the existing scaffold bank/target/reference contract, all frozen feature definitions (with missing/dropped/evaluability explicit), directions fitted before test outcomes and 20 texts per value (two phrasings × ten contexts). No result-based feature selection. S2 preparation validates the committed feature freeze and exact source bytes, then calls immutable `freeze_reference`/`freeze_texts`.

`collect --texts S2_PREPARED/texts --assets ASSETS --assignment S2_ASSIGNMENT --official OFFICIAL --whitener WHITENER --out NEW_RECONSTRUCTION`; assignment has `experiment: S2`, `mechanism_budget: fidelity`, exact normal mechanism source mapping and `entrypoint_files` binding `s2_fidelity.py`'s SHA. It calls the unchanged `ar_tests.collect_fidelity`; no separate fidelity formula. The cumulative 0.3 GPU-h fidelity cap is shared with W2, including failures; no double allocation.

`analyse --bank BANK --target TARGET --reference S2_PREPARED/reference --texts S2_PREPARED/texts --reconstruction RECONSTRUCTION --labels LABELS --text-labels S2_PREPARED/texts/text_labels.DO_NOT_STAGE.jsonl --out NEW_S2_ANALYSIS` delegates to unchanged fidelity/§80 decisions and prints HANDOFF S2. Preserve all score/input seals and logs; no labels on the collection pod.

## Watch / current dependencies

Requested check interval: every15minutes. Two Codex heartbeat creation attempts returned MCP −32000, including the explicit W-mechanism thread ID. No 15-minute checker is active; no silent hourly substitute or hand-written scheduler directive is installed. Direct P3 aggregator request also failed; the committed request is on branch `d6593981`, awaiting P3/repository relay. The branch will be checked again before publication. No future launch is claimed without a working checker or an active session.

Current collection prerequisites: W7 still needs W-core priority actual export/receipt and unrelated neutral IDs. S2 texts are ready immediately from dc0e1316 and need only integrator assignment plus staged/pinned AR assets. Later analysis waits for raw44 bank/activations/directions and asked scores; W2–W4 wait for complete W1 verdict/activations and P3 current-BRIEF re-signing. The native app scheduling surface is also inaccessible, so the requested 15-minute checker remains unavailable. W4 remains OFF-NATIVE at44 pending Camila. Optional SAE remains unlaunched.

## S2 reconstructor-only freeze now complete

HANDOFF S2 texts: FROZEN from `dc0e1316`; **178 features =138 §79 +40 binary W1 rows;7,120 texts =20 per value ×2 values per feature**. All138 §79 features are included, including43 not retained for screen capture. Ordinal W1 rows are excluded by registration. Frozen positive/negative definitions and first phrasing are used literally; second phrasing is the fixed neutral prefix wrapper in `s2_fidelity.py`; the original AR grid supplies two phrasings ×ten contexts. No directions, activations, probes, reader results or model passes were used.

Use `s2_fidelity freeze-texts --help` to reproduce. Local full files are at `cache/g_agreement/blindspot/mechanism/s2-texts-dc0e1316`; the worker archive contains only its sealed label-free files. Exact archive path/hash/size and the local withheld-label path are in `s2/TEXTS_FROZEN.json`. `s2/LAUNCH_REQUEST.json` requests only AR passes; do not wait for §79 asks/activations or W1 priority directions. Later fidelity analysis waits for real raw44 direction/mean denominators and Oracle asked AUROCs; it is not a collection prerequisite. The W1 texts are already in this batch and must be reused for W2, not recollected or double charged.

Validation: 236 vendored-reader/blindspot tests passed in 10.52 s, including 36 new W7/S2 tests, the 50 frozen mechanism/units checks and the standalone W4 aggregation tests. Synthetic CPU model doubles only; no actual target/reader/AR weights loaded. W7 preparation/run/analysis and S2 text freeze/collection entrypoints are separate files. Frozen ar_tests.py SHA remains unchanged.

HANDOFF S2 LAUNCH REQUEST: source `27e1a0f33fae3ff685774646355608f0604b72cd`; 7,120 frozen value texts /178 features; AR passes only; cumulative shared W2/S2 cap0.3GPU-h; archive and exact source hashes in `s2/LAUNCH_REQUEST.json`; REQUESTED_NOT_ASSIGNED, no model run. W7 remains WAITING_PRIORITY_DIRECTIONS.
