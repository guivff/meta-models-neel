# E100 CPU vectors and pairings — active a/b only

Authorities: §208 f425a5e2; all84-per-row/token clarification fd07c12a; **69f8c08e4 withdraws c/d in favour of E101**. This withdrawal arrived during preparation. Already-computed dev directions/probes are retained under cpu_only; no injection or upstream arm is in the runnable handoff. The unembedding token mapping is recorded in CPU_TOKEN_MAPPING_HISTORY.json, including exact token IDs/pieces/strings. No u_tok vectors were built after withdrawal. The nesting prefix question was unresolved at withdrawal and does not block a/b. No E100/E101 model, GPU or judge call occurred.

## Existing inputs reused

E58b's sealed J384 basis, original E56/E57 block44/block42 capture shards and E59 capture delivery are hash-verified. E79's missed-row raw d, d_J, d_perp and random arrays are copied from CPU_DIRECTIONS.npz (839bc5ee...), not rebuilt; normalized full d retains its original raw norm. E59 directions also reuse the original sealed dev arrays. The three E56 directions and eight probes are dev-only; no test data fit or outcome/readout inspection. See artifacts/cpu_only/SOURCES.json and FINAL_ROWS.json for full provenance, dev IDs, raw scales and probe hashes. These files and the entire cpu_only tree must stay off pods.

The random projector is Q_R @ Q_R.T, with Q_R shape5120×384 from default_rng(20261028), standard Gaussian and reduced QR, positive diagonal of R. Q_J is the sealed basis, in5120×384 orientation. Both are float64. Maximum orthogonality errors: J8.04e-9, random6.00e-15. No dense projector is needed.

Dev J fractions versus chance sqrt(384/5120)=0.273861: nesting_depth0.322574, indent_level0.227322, page_range_digit0.267270, format_plan0.408097, language_plan0.424393, tense_implicit0.339330, language_continuation0.361009, fact_recall0.350300. These are prechecks, not reader outcomes; report the E79 Arm A null first as registered.

## Public runner interface

artifacts/public/MANIFEST.json lists all eight rows, all84 frozen-order test IDs each, h44/h42 paths, one pairing file per row, and Q_J/Q_R. Carriers are float32 arrays84×5120. Pairings are [{id,slot,donor_id,donor_slot}], with opaque IDs and integer array slots. Per row, default_rng(20261028) chooses uniformly with replacement from opposite-class test items in frozen bank order; 672/672 pairings pass class/opposite/same-row checks. Donor reuse is permitted by this seeded one-partner recipe. No label, value, sign, original ID, token string or probe parameter is in the public package.

Active conditions are transplant, J_swap, perp_J_swap, R_swap, perp_R_swap. Oracle reads block44; NLA reads block42 using the block44 basis, exploratory. Full intended a/b grid: reported4200, missed2520, total6720 (3360 Oracle +3360 NLA); no new baselines. R-PC gates scientific evaluation of b per registration; the runner/integrator owns release and admission. All rows explicitly mark injection/u_tok/upstream WITHDRAWN_69f8c08e4. Do not create placeholder injection vectors.

## Staging

HANDOFF_REQUEST.json binds the public parent seal and four local archives. For each reported or missed shard, extract **both** basis archives and exactly one group archive into the same fresh destination, then verify inputs/INPUT_SEAL.json. Every file in that seal must exist and match, including both bases. Archives are individually below20MiB. No CPU keys or root seals containing CPU metadata go to a pod. W-Mech2 owns the runner adapter; Track Q owns price, custody/guards, timing admission and launches. This is a data handoff, not launch authorization.

## Manipulation adapter and withdrawn preparation

math100.manipulation(h,h_prime,w,sd,target_label) computes the exact standardized linear-probe logit difference, target-signed difference after a CPU-only target join, norm ratio and >1.5 flag without filtering. Tests check it against direct probe decisions. Saved dev probe parameters are in cpu_only/*_probe.npz. manipulation100.py's complete-cell join adapter is retained as preparation history but refuses the withdrawn E100 injection manifest. Reusing it for E101 requires E101's own block42 directions, opposite-value targets, dose selection and source binding; this package does not authorize that transfer.

Four focused CPU tests pass. Actual-artifact checks verify all data/source seals, all84×8 carriers, exact E79 reused array bytes, unit norms, orthonormal bases, all672 pairings and both extracted public archive allowlists. CPU-only; no scientific verdict derived from reader outputs.

## 2026-10-29T08:19Z — W-mechanism-C → vector owner

Integrator0ced6f3d requests new §226 E100e public transplant inputs (E49 container_after_move/holder_after_handovers,84test each,seed20261029). C is constructing lossless block44/42 carriers and same-row different-value seeded pairings directly from original sealed E49 capture; original E100 a/b package remains immutable. No duplicate donor/capture/model compute needed. Please flag any already-live E100e CPU builder here; otherwise C owns this new package.
