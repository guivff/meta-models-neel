# E58b sealed runner handoff — 2026-10-27

E51 count was committed before this packet: 55,151 training target bullets; R1 DOES NOT HOLD. No E51 rerun is authorized or needed.

E58b is one base-Qwen pod, all eight arms (none/J/five random/PCA), raw post-block44 output, every prompt position. The pooled PCA follows §174 clarification1(b), with the below768-vector fallback. R-b1 is2of3 on rhyme_plan, antonym_crosslingual and E57 two_hop_answer. reasoning_bridge is excluded. No lens adapter is loaded and no forced-choice question is added.

Before provider allocation, stage the pinned target snapshot and runtime, then deliver the complete bank per INPUT_CONTRACT.20261027.md. The08:00 E57 freeze and final upstream pair inventories are prerequisites. Run prepare_inputs.py and refresh_request.py, then commit INPUT_BINDING.20261027.json plus forced request/command hashes after a secret scan. Do not launch an AWAITING_FROZEN_BANK_BINDING request. All scopes/IDs/pairs/categories and input hashes must be frozen before any PCA capture or timing score. J384.npy is already byte-staged in this worker's cache; large files stay ignored.

Launch command, from repository root:

`env CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e58b/worker58.py --assignment cache/g_agreement/understand/e58b/assignment.json`

The assignment binds the exact request/source/input seals and pushed source commit. Provider custody, setup, retrieval and previous usage together obey2700GPU-s; retrieval reserve180s. Use one fast single-GPU pod (H200 preferred). The worker profiles the full frozen scope, retains the shared dev PCA, discards timing scores, and rejects NO_FIT before production. It never reduces the scope. A parity/validity failure stops; operational handling stays with the Integrator under current orders and preserves all guards/history.

Worker output is cache/g_agreement/understand/e58b/out/. Run-once guard is cache/g_agreement/understand/e58b/WORKER.RUN_ONCE.json. Make the complete verified pull available as cache/g_agreement/understand/e58b/verified-pull/final/ (all OUTPUT_SEAL files, with relative layout preserved), and write verified-pull/VERIFIED_PULL.json with issuer=integrator, experiment=E58b, verified_complete=true, pod_id, output_seal_sha256 and provider_stopped_epoch. Never combine partial outputs or reset a guard.

Sole CPU analysis command:

`env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 python results/g_agreement/understand/e58b/analyze_once.py`

Guard: results/g_agreement/understand/e58b/ANALYSIS.RUN_ONCE.json. Outputs: results/g_agreement/understand/e58b/analysis_20261027/RESULTS.json, RESULTS.md, ANALYSIS_SEAL.json. Source and command seals are checked before claiming; a later validation failure consumes the claim and requires owner review. Every pair/item/arm must be present. R-b1 and R-b2 use signed mean damage; all PCA-below-random rows and all five random seeds are reported. No label model, probe refit, blind judge or secondary selection is run here.

Clarification2 (be4d4e87): also bind fact_recall and E57 sentiment_judgement (row14). The shallow-content report gives per-row J/random damage plus PCA damage, with undefined ratios explicit when random damage is zero. The request retains the user cap2700GPU-s; the forecast must admit the complete augmented grid.

## Committed frozen binding — ready packet, 2026-10-27

The owner has now assembled and verified the complete37-row catalog: W1/E15 eight, E36/E15 eight, E49/E53 eight, E56 five, E57 eight. There are3108dev and3108test items; pooled dev-read-point PCA uses3108 vectors. All4452 item/pair units are retained across8 arms (35616 score records). E57 donors use exact opposite original partners and their already-computed scores; no extra GPU calls or primary-rule input.

Stage the archive named in INPUT_ARCHIVE.20261027.json (relative extraction root cache/g_agreement/understand/e58b); every archive member and source checksum was verified, including Linux path casing. Do not rerun prepare_inputs.py or regenerate a bank: INPUT_BINDING.20261027.json is already sealed. The READY request binds the archive, source seal and input seal. Use the same committed worker/analysis commands above. Programme hard stop is **Thu29Oct22:59Z**; total budget remains2700GPU-s. Integrator supplies the pushed source archive and a request/input/source-bound assignment, then launches.
