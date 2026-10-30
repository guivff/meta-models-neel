# W-mechanism-C E101 recovery handoff

Inventory before writing: E79 worker and handoffs at 8e431cca; E100 c7f7e53aa public carriers, bases and 672 pairings; W-mechanism-B's unpushed plan and four untracked E101 files. During recovery B published 1610b10f9. This extension incorporates that commit; the original checkout and original E79 worker are unchanged. Eleven CPU/tiny-model tests pass. No GPU, dose, test, or judge output acquired.

## Policy binding

The user confirmed the latest §209 clarification: **84 dev items and independently selected doses at blocks44/42**. Clarification2 retains full frozen continuation token-sum contrasts (E59 single-token candidates are equivalent). No alternate40-item path remains. Select writes E101_DOSES.json and stops. Integrator commits it, then test composition verifies the exact Git blob/hash before making any test cells.

## Actual inputs verified

W-internals-B's vectors landed at2f17a7887 during recovery. B's DEV_INPUT_BINDING.json supplies seven complete row archives:672cells each,4704total (84dev ×4doses ×2blocks). WMC_INPUT_AUDIT.json records re-verification of each real seal, archive hash and exact grid. The original dev_v2 archives remain unchanged. No vectors are missing now. WMC_TEXT_BINDING.json identifies the new336-item baseline archive, built from the same frozen E56/E59 test metadata with the exact sealed E81 generic framing and pinned tokenizer. No labels enter public inputs. No test intervention vectors or dose receipt exist yet.

## Acquisition and timing

Use `python -m projects.g_agreement.e101.runner` with B's existing flags, the **WMC_SOURCE_SEAL.json** hash, and `--timing` first. Warm-ups are synthetic and discarded. One sample per row/block/prompt-length/candidate-length/batch-size stratum measures each available phase, weighted by its full job count; MEASURED_PROFILE.json forecasts setup + work + measured staging + 60s retrieval, multiplied by **1.25**. Timing outputs are not science. For production, pass `--profile PATH`; assignment must bind `profile_sha256`. The cap must equal ceil(measured forecast), not exceed it. Existing fixed creation deadline and runtime NO_FIT checks remain. Timing is not yet measured on a GPU: no numeric GPU forecast or admission is claimed. The Integrator runs the timing job and owns provider/custody/log/compute accounting.

Every acquired cell records norm_ratio, >1.5 flag, block, channel, GPU type; HARDWARE.json and OUTPUT_SEAL include actual GPU name. Dev loads no readers. Test runs one greedy Oracle at44 and NLA at42 plus patched pair logits/continuation contrasts; no new unsteered baseline. Oracle-only or NLA-only eligibility is supported.

## Text baseline

`python -m projects.g_agreement.e101.text_baseline` uses the same operational flags (including timing then measured-profile admission). Base Qwen only, serial greedy, 128 tokens. Frozen public bundle: items.json containing exactly336 `{id,row,input_ids,prompt}` entries (84 each language_plan,format_plan,fact_recall,language_continuation); MANIFEST.json `{experiment:"E101_TEXT",generic_arm:"E81",owner_source_sha256:...}`; INPUT_SEAL.json with experiment, labels_on_pod:false and hashes of those two files. Supply exact E81 generic prompts, not newly phrased instructions. Tokenization is verified before generation. This is a separate text acquisition, with no activations and no adapter load.

Source archive packaging: `python -m projects.g_agreement.e101.package --out /ABS/FRESH_DIR`. It seals the E79 worker, E79 dependencies, late198 runtime and E101 sources. Stage only this source archive and one verified public input bundle. Do not stage the whole repository.
