# E79 Arm B continuation scorer — READY

§196 clarification 1 (b3c1e6d0) resolves and supersedes the earlier SCORER_PROVENANCE hold. Frozen E59 candidate strings, pair averaging, and tie-aware AUROC are unchanged. `auc` and `continuation_aucs` are copied verbatim with source hashes; only their imports/require shim and the input-axis adapter are local. E79 supplies patched base-model logits, not E59 reconstructor activations. No 64-token generation or text-scoring rule.

W-mechanism: emit one JSON document using INPUT_CONTRACT.json. Exactly 672 records = 2 rows ×84 test IDs ×4 conditions. `candidate_token_ids` must match the contract. Each record supplies the raw next-token logits for each frozen pair, in A/B order. A logit difference equals log P(A)−log P(B), since the vocabulary normalizer cancels. Language averages both frozen pair contrasts per item BEFORE AUROC. No leading spaces added to candidate strings. Keep the complete acquisition seal and patch custody in the integrator's receipt.

CPU command (from wt-wtext, replace INPUT/SHA/OUT with verified-pull paths):

```sh
/Users/guivff/Documents/Neel_Exploration/activation-readers/.venv/bin/python results/g_agreement/understand/e79/continuation/score79.py --continuations INPUT --sha256 SHA --private-items results/g_agreement/understand/e59/cache/bank_2026-10-27_v1/items.PRIVATE.json --out OUT
```

Input is now a next-token-logit continuation file, not generated text. Private labels stay on CPU. The command verifies its code/contract seal and original E59 item hash, requires a complete unique grid, and refuses an existing output directory. It writes per-row/condition AUROC, the behaviour condition `AUROC(d_J) >= AUROC(none) - 0.10`, and an analysis seal. This does not adjudicate the other R-C2 reporting conditions.

Four CPU tests pass: correct/reversed/tied scores, average-before-AUROC, incomplete/duplicate/nonfinite rejection, and byte-identical frozen estimator functions. No E79 outputs opened and no scoring run on real E79 data.
