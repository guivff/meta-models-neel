# Conditional E49 input — 2026-10-26

No E49 bank is frozen at E50 build time. Before launch, Integrator records the same availability decision in both assignments. If it remains unfrozen, use `status: NOT_FROZEN_AT_LAUNCH`, `issuer: integrator`, `checked_before_launch: true` and omit `--secondary-input`.

If frozen in time, use `status: FROZEN_VERIFIED` and bind `input_seal_sha256`, `bank_seal_sha256`, `capture_output_seal_sha256` and `private_test_labels_sha256`. Stage these four worker files plus INPUT_SEAL.json (a `files` SHA256 map):

- `test.jsonl`: exactly84 test records `{id, feature}` for each of the eleven semantic tracked-state rows in secondary.py; no labels or text.
- `test.acts44.npy`: float activations, shape(924,5120), in test.jsonl order, from E49's verified block44 capture.
- `templates.json`: frozen per-row ordered A/B `olens` descriptive pairs, two phrasings, copied from the frozen E49 candidates.
- `PROVENANCE.json`: `experiment: E49`, `frozen: true`, the bank/capture hashes above, `frozen_before_epoch` preceding pod creation, `activation_layer: 44`, `items_split: test`.

Integrator verifies source-bank IDs, orientation, candidate bytes and capture rows before binding; no reauthoring or recapture by E50. Stage the same input on both pods. The warmed forecast includes the eleven extra L asked rows. The worker verifies the seal, schema, dimensions, row set and finite values before any forward.

For the once-only analysis, deliver the same payload at `cache/g_agreement/understand/e50-e49-bound-v1/input` and the exact private key at `cache/g_agreement/understand/e50-e49-private/test.labels.DO_NOT_STAGE.jsonl` (924 records `{id, feature, y, cluster}`, with y=1 for the first frozen candidate). This key never enters the source/input archives or GPU worker. E49 outputs are descriptive; E49's own gate decisions are not recomputed.
