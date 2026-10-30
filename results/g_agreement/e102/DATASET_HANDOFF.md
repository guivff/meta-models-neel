# W-train → I-4: E102 CPU production data preparation

The completed W-text template freeze (7e696cab) is verified, and W-mech2's 7eb82520 once-only **analysis** adapter is received. It is not a training-model adapter. The pinned model adapter remains olens_s3d_rl600. All three target rows are now bound to their frozen templates; page-range targets render the actual item digit under §210 clarification2.

## Frozen selection

DATASET_PLAN_MANIFEST.json binds original E56/E57/E59 bank seals and item hashes, the complete template seal, deterministic selection, and the local CPU plan file hashes. There are 252 target dev items (84 per row), each with the last eight positions, producing 2,016 target pairs. Replay uses all 504 dev items in the six registered rows and their last four positions, producing 2,016 replay pairs (336 per row). Every selected sequence is long enough for its window. One original-lens greedy readout at each replay item's read token supplies the target text for that item's four positions. Target paraphrases are drawn with Random(20261029), one of five per position in frozen item order. These implementation choices are frozen before any model call and are not tuned.

The new PRODUCTION_RECIPE.json binds this manifest and the complete template seal while preserving rank16/lr1e-4/300steps/batch16/seed20261029. The historical REGISTERED_RECIPE and CPU_INSPECTION_SEAL remain unchanged. Production must reload the pinned original adapter rather than the disposable gate checkpoint.

## Acquisition dependency; not a ready training dataset

The CPU selection is built. The final activation/text dataset is **not yet ready**. Original E56/E57 captures have one vector per item, not last-eight windows. Their native acquisition selects test items; those outputs are ineligible as replay teacher data. No test readout was substituted. Need post-gate acquisition of 4,032 position vectors and 504 original-lens greedy dev readouts, then CPU finalization. The dataset plan's status intentionally says NOT_TRAINING_READY; it does not claim nonexistent vectors or teacher hashes.

The local ignored directory is recorded in DATASET_PLAN_MANIFEST. ACQUISITION_ITEMS.json contains only dev IDs, row/bank, frozen raw token IDs, positions and role; it has no class labels, values, answers or judge data. PAIRS.CPU.json holds the rendered target bullets and CPU pair join. Keep it CPU-side during capture. Only finalized authorized training vectors/text go to the trainer.

I-4's GPU gate remains first, on admitted capacity by **29 October 12:00 CET**. No GPU was launched in this preparation. Capacity/priority and the new §204 USD2,500 planning ceiling must be refreshed by I-4; historical gate.py still enforces the stricter USD1,500 bound, so its budget-only check needs an explicitly sealed operational update if admission exceeds that old bound. Do not change scientific settings or weaken parity. Gate inputs and exact source have now been archived, extracted, hash-compared, syntax-checked and imported via isolated `--help`; GATE_ARCHIVE_RECEIPT records this. This is not a GPU pass.

## Finalization contract

After the gate PASS, provide a sealed acquisition directory with:

- `acts44.npy`: finite [4032,5120] native block44 outputs, in exact PAIRS.CPU order, captured with original base weights and reader adapter disabled.
- `PAIR_ORDER.json`: the exact 4,032 pair IDs from the frozen CPU plan.
- `DEV_TEACHER.json`: exactly 504 records `{item_key, split: "dev", text}`; one original pinned lens greedy readout per replay item at its read token, serial batch1, max128new tokens.
- `ACQUISITION.json`: plan_seal_sha256, gate_seal_sha256, adapter_sha256, base_revision, capture_adapter_enabled=false, block=44, decoding={do_sample:false,max_new_tokens:128,batch:1}, and the actual first_output_utc.
- `OUTPUT_SEAL.json`: hashes binding all acquisition files. I-4 retains exact executed source, model manifests, hardware receipt, creation-based custody and off-pod backups.

Run `python3 -m projects.g_agreement.e102.dataset finalize --plan <CPU-plan> --acquisition <sealed-acquisition> --gate <sealed-gate> --out <new-training-dir> --manifest <new-manifest>`. It fails closed on missing/non-PASS gate, base/update failure, modified source seals, non-dev pairs, wrong row counts, duplicate/missing positions or teacher records, wrong original checkpoint/decoding, or nonfinite/wrong-shaped vectors. It writes final vectors and training text plus DATASET_SEAL; commit final manifest and hashes before the once-only production train. No judging or analysis is run here.

Validation: four leakage/source-integrity tests PASS; five unchanged W-text template tests PASS; actual plan checked for 4,032 unique pair IDs, 756 dev items, correct per-row balance and absent truth fields in acquisition items. The exact gate archive entry point imports successfully in an isolated extraction. Secret-scan and rebase precede publication.

Latest intake at376d0847 includes I-4 DATASET_BUILD_HANDOFF and §211: production training beyond the gate is parked until CORE is sealed and a pod is idle. CPU preparation continues without changing that priority. AVAILABILITY_AUDIT verifies seven original capture seals and their two-dimensional read-token arrays; it binds zero complete window vectors or dev teachers and explicitly lists the required acquisition. Final evaluation inventory, acquisition/train/eval worker archives and measured complete custody forecast remain pending; this delivery does not claim their completion.
