# E95 bounded timing and measured binding

This is CPU-tested source, not a GPU launch or admission. It reuses worker87.acquire, capture_stage, Backend87, scope95.placebo95 and the unchanged native Oracle/NLA paths. Existing handed E99, hardware-smoke and active run archives remain immutable. E95_TIMING_SOURCE_REQUEST.json identifies this new source archive.

## Prepare the frozen public scope on CPU

I-3 supplies its inventory, seeded judge index and one existing package_inputs.py public input directory per frozen row. Run package95.py prepare --inventory ROW_INVENTORY.json --index JUDGE_INDEX.json --inputs ROW_INPUT_DIRS... --out NEW_SCOPE --cap-seconds OPERATOR_CAP. The source seal is verified before packaging. Each input archive is under 20 MiB, contains only PLAN.json, items.json, STAGE_REQUEST.json and INPUT_SEAL.json, and holds one whole row. Inventory, dev probes and judge index remain CPU-side; only their hashes enter requests. An unverified reuse44 capture is not accepted by timing.

Preparation checks the original frozen seed/index, opaque row binding, item order and 15 matched placebo counts. It creates SCOPE_SEAL.json over inventory, index and row-plan/item hashes; REQUEST.json pins the source and per-row inputs. READY_E95_TIMING_ONLY is not allocation permission. I-3 must post the aggregate padded spend including prior custody, all parallel liabilities and any smoke before launch.

## Smoke and guards before timing

For a new B200 image, first run the existing hardware_smoke.py with I-3's verified three-item reference package and the matching original hardware204_v1 source seal. Its PASS receipt must match the timing image, installed stack and asset manifest. The compatibility smoke is not a timing forecast. H200 does not need a B200 smoke. Reused E87 rows remain blocked until complete original source outputs and verified per-row actual hardware arrive; NO_FIT output or missing GPU type is insufficient.

Reuse existing creation-bound operator guards, independent allocator-exit proof, a durable absolute own-pod stop and the original staging deadline. Do not run old allocator state or reset custody clocks. On a load/software/nonfinite failure, crash, incomplete profile, or timeout: retrieve available receipts, stop only the owned pod, verify termination, reconcile actual custody, and do not launch production. The runner does not carry provider credentials or install guards. Existing operator paths/guard hashes are in the prior hardware handoff and direct I-3 message; this package contains no new allocator.

## Measure one whole-row workload

Run timing95.py --inputs INPUT_DIR --assets ASSETS.json --assignment ASSIGNMENT.json --staging-receipt STAGING_RECEIPT.json --out NEW_OUT --source-sha SOURCE_SEAL_SHA --input-sha INPUT_SEAL_SHA, with --hardware-receipt and --reuse-hardware where required by HARDWARE_RUNTIME_HANDOFF.md.

Assignment binds experiment E95, exact row_indices/shard, one actual GPU, hardware_authority, analysis_unit_gpu_types, immutable image_digest, stack_sha256, assets_sha256, inventory_sha256, index_sha256, scope_seal_sha256, verified daily budget and creation-based fixed custody fields. STAGING_RECEIPT.json contains assignment_sha256, pod_created_epoch and worker_ready_epoch. Staging must finish within 900 seconds of original creation. The same original absolute deadline includes a 60-second retrieval reserve; neither timing nor failure rearms it.

The timing wrapper captures all real items and builds the original 15 matched placebo pseudo-items. It measures the first three native batches in each reader/arm/layer/achieved-position-count group, except NLA placebo: all 15 pseudo-items are timed. Thus a short prompt has a separately measured phase rate. Reused E87 rows execute only their new 15 NLA placebo pseudo-items. Sampling changes timing work only; every production readout is regenerated. Source-marked timing outputs, including per-reader seals, are excluded from scientific analysis.

PHASE_TIMINGS.json stores measured setup, capture, placebo construction, warmup and native calls. MEASURED_PROFILE.json records measured batch counts, full-workload batch counts, per-phase means, exact source/input/scope/hardware bindings and first-output evidence. Forecast = ceil(1.25 × (measured creation-through-staging + measured setup/capture/warmup/placebo construction + measured other worker overhead + sum(full native batch counts × measured phase means) + 60 seconds)). A completed profile gets PROFILE_ONLY; a failed/incomplete profile cannot support admission. No E99 evaluator is used.

## Evaluate and reduce only in order

Run package95.py evaluate --scope SCOPE --profiles ROW_PROFILE_PATHS... --prior-seconds ACTUAL_PRIOR_CUSTODY --out SCOPE/DECISION.json. Every retained row, including the reused-row NLA placebo work, needs a verified same-source/scope profile. Mixed GPU types are allowed across whole rows; each row's final identity is individually pinned. Phase means, sample coverage, sealed staging and the padding formula are rechecked. Prior actual custody is separately reported for global budget reconciliation; the 40 GPU-hour test applies to the padded forecast of remaining production work.

If REDUCTION_REQUIRED, run prepare again using that scope's inventory/index/row inputs and --previous-decision SCOPE/DECISION.json. The decision is recomputed from sealed profiles before proceeding. Exactly one step is allowed: drop Oracle20 from remaining rows; then first20 real items per remaining row; then retain remaining rows with verified dev AUROC >=0.90. Existing E87 real/Oracle outputs stay reused; their new 15 NLA placebo items remain included. Unknown dev scores block step3 instead of inventing eligibility. The complete judge index is recomputed with the existing I-3 seed/sample_strata implementation and re-sealed before any new calls. A changed reduction requires new measurements of that exact scope; old profiles cannot authorize it. If step3 still exceeds the cap, there is no further automatic reduction.

## Bind production without admitting it

For WITHIN_40H_REQUIRES_I3_GO, run package95.py bind --scope SCOPE --profiles ROW_PROFILE_PATHS... --prior-seconds ACTUAL_PRIOR_CUSTODY --out NEW_BINDING. It writes measured caps, measured phase seeds, hardware identities and final inventory/index/reduction/source pins into new public input seals, with status HOLD_I3_GLOBAL_ADMISSION. No production starts.

After reconciling global liabilities, I-3 may promote each STAGE_REQUEST to READY and re-seal it under its own admission receipt. Production remains the existing worker87.py entry point. Assignment additionally pins measured_profile_sha256, measured_decision_sha256 and e95_integrator_admission_sha256, plus the exact measured scope/inventory/index/GPU/image/stack/assets identities. Runtime validates these and the source, row, item bytes and cap. A different hardware or software identity needs fresh timing. The separate B200 smoke and original E87 reuse-hardware checks still apply.

CPU validation: 30 exact-archive tests cover complete 15-item NLA placebo timing, short-position phase grouping, reused-row-only work, fixed deadlines, sealed mean/staging/identity checks, three ordered reductions with fresh scope/index seals, rejection of old profiles for a reduced scope, and rejection of a production hardware swap. No real model, judge or GPU call was made during preparation.
