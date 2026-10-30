# E58b CURRENT handoff: blind pod / CPU-only labels — 2026-10-27

This supersedes the staging instructions in INTEGRATOR_HANDOFF.20261027.md and the labelled-input packet published as dd1a3d59. Do not stage the old E58B_INPUTS_20261027.tar.gz, inputs/, delivery/, cpu_only_v2/, or a repository-wide source archive to a pod.

## Pod staging before allocation

1. Extract the archive in POD_CODE_ARCHIVE.20261027.json at the repository root. It contains only common58.py, projection58.py, worker58.py, POD_SOURCE_SEAL.20261027.json and the pinned runtime JSON.
2. Extract INPUT_ARCHIVE.20261027.json's current archive at cache/g_agreement/understand/e58b/. It contains only pod_inputs_v2/BANK.json, J384.npy and INPUT_SEAL.json. BANK.json has opaque IDs and frozen prompt/candidate token IDs; no labels, original IDs, donor maps, categories, annotations or BOW fits.
3. Copy the current committed LAUNCH_REQUEST.json separately to results/g_agreement/understand/e58b/LAUNCH_REQUEST.json. The assignment binds its exact SHA256 plus POD_SOURCE_SEAL and the blind input seal. Do not use the CPU SOURCE_SEAL as the pod assignment's source pin. The existing target snapshot/runtime is staged as before.

Use the same committed worker command and assignment path. The worker returns logp_A and logp_B separately per item/pair/arm, with the random seed explicit. The registered37 rows,3108dev+3108test items,4452 item/pair units and35616 records are unchanged. No true-label orientation or swap join runs on the pod. Cap2700GPU-s, retrieval180s, one pod and Thu29Oct22:59Z programme stop are unchanged.

## Integrator CPU custody, never pod staging

CPU_ONLY_ARCHIVE.20261027.json identifies the separate CPU-only archive containing cpu_only_v2/CPU_JOIN.json and CPU_SEAL.json. It stays on the Integrator's CPU side. It holds original IDs, labels, categories and frozen donor maps. Metadata binding is CPU_CUSTODY_BINDING.20261027.json. Verify both file hashes, the blind input-seal linkage and that these labels stayed off the pod. Then create cpu_only_v2/INTEGRATOR_CUSTODY.json from CPU_CUSTODY_RECEIPT.template.json with issuer=integrator, verified_cpu_only=true, labels_stayed_off_pod=true, the supplied exact hashes and verification time. The worker never reads this receipt or directory. Do not fabricate or copy a completed custody attestation before verifying.

After the complete verified GPU pull is available at verified-pull/final/ with its existing Integrator receipt, run the same sealed once-only CPU analysis command. It verifies the blind pod outputs, requires the Integrator CPU-only custody attestation, joins opaque IDs and raw log probabilities to labels, and only then computes logP(A)-logP(B), correct-minus-wrong damage, R-b1/R-b2 and descriptive swaps. No real score analysis has been invoked here. Scientific guards/output paths remain unchanged and unconsumed.

POD_STAGE_MANIFEST.20261027.json is the positive pod staging allowlist. CPU analysis uses the full SOURCE_SEAL; pod execution uses POD_SOURCE_SEAL. COMMAND_SEAL binds both and the current request. No older labelled input archive is an active request artifact.
