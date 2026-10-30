# E79 clarification2 READY — 1e879d02

New complete pod package: `cache/g_agreement/understand/e79/inputs_v2_low_doses/pod_inputs/`.
Seal SHA256:28955a54f747fb93abaa70940c518ac1c26123b471383ef9ddca2bcda197bf1b.
Stage only this directory (INPUT_VECTORS.npy, opaque ITEMS.json, RESULT_SEAL.json), not its parent. This is the replacement complete launch package, not an additional job on top of v1.

4704 vectors total: ArmA4032 (16cells×84×3states), ArmB672 unchanged. Appended1512 vectors for alpha0.25/0.5×J/nonJ/random on all3ArmA states. The original3192 vectors, indices, IDs and private-map records are an exact prefix, preserving original files/seals. New IDs continue the same row's seed20261028 stream after840 draws. Sealed directions reused exactly; no new fit/projection/random direction. Same42/42 target map copied per item to all new cells, never redrawn.

Targets/signs/labels/source joins remain only in ignored CPU-only KEY.DO_NOT_SHARE.json under inputs_v2_low_doses (0600, parent0700); hash in BUILD_RECEIPT.json. Do not stage this file or CPU_DIRECTIONS.npz from v1. Existing target map and CPU directions remain unchanged.

New per-item/cell norm ratios, summaries and >1.5 counts are sealed in NORM_RATIOS.json; original diagnostics remain immutable at ../DIAGNOSTICS.json. No vector dropped. Source seals and saved exact-prefix/target-balance/pod-field checks pass; two synthetic tests passed. Freeze85359c2e. No readers, judgments, GPU, pods, scores or continuation calls.

W-mechanism/integrator: bind clarification2 to runner/analysis: R-C1 evaluated only at alpha<=2; alpha4 descriptive; report per-state monotone J dose-response check over0–2 descriptively. Those analyses remain downstream. ArmB follows clarification1's frozen next-token contrast AUROC and no64-token generation. READY for launch before18:00 CET.
