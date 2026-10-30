# Current E73/E74 intake contract, revision 2 — 2026-10-27

This dated addendum supersedes the unconditional E74 public-J requirement in `FORECAST_INTAKE_2026-10-27.md` and the E74 paragraph of `HANDOFF_2026-10-27.md`. Those original files and their E75 scorer seal are retained byte-for-byte. E73's capture/forecast order is unchanged. Authority: §192 clarification 2 `451e2f4d` and Guiv's explicit instruction in W-lens: before GO, either commit the J-forecast or the bound NOT EVALUABLE record plus category-only GLM forecast. I-2 reader-admission schema reviewed at `e6370bd4`.

E74 can proceed for R-G1/R-G3 with the public Oracle lens and feasible base-model asset card when the J checkpoint is unavailable. No self-estimated J substitute is confirmatory. At the pre-GO forecast step, use either:

1. The exact anonymously public author's GLM J-lens, registered pursuit and model-specific null, with a committed prospective J-forecast; or
2. One committed record stating exactly `R-G2 NOT EVALUABLE; J-lens unavailable`, bound to the full prose ASSET_CARD and actual capture/input seals. The SAME record includes the category-only forecast for every requested GLM row: content/plan REPORTED, other frozen E58a categories MISSED. It records `rg2_not_evaluable_permanent: true`; publication of a J checkpoint after GO cannot restore R-G2. Any later J-forecast is exploratory only.

The audited prose card at `38f4593c25c5290513739a8c049a238f223fa274:results/g_agreement/e74/ASSET_CARD.md` has SHA256 `dcb6d67bebaf06ab5312e2d30201e88d805d406bbc9bdfdc1502f3745ec748e5` (worker original `f0fb6d49`). This historical audit is not a fabricated current availability check. At actual record creation I-2 supplies a capture-bound receipt confirming current public-J absence, no GO, no reader access, and held readers. No GLM capture or actual pre-GO record exists in this preparation.

## Prepared writer and evidence contract

`e74_absent_j.py` performs CPU file/Git/hash/coverage validation and writes an exclusive record only. It never downloads, scores J, opens native reader outputs, launches pods, publishes a Git commit or sends GO. `E74_ABSENT_J_CODE_SEAL.json` seals this writer independently of the immutable E75 statistical scorer. Synthetic tests use temporary repositories and fake captures only.

Before invocation commit a binding plan with these fields:

- `experiment: E74`; `capture_seal` and `input_seal`: absolute-path/SHA256 references. Capture contains `track: G`, `sealed_at`, `input_seal_sha256`, and a nonempty `files` map. Every capture payload is hashed. No placeholder or missing capture is accepted.
- `input_rows_member`: a JSON member of the input seal containing `rows: [{row: unique_model_bank_row_id}]`, enumerating the entire requested GLM scope. Input/capture normalization, if needed for the runner's eventual schema, is operational only and must preserve original hashes, all item/row identity bindings and registered exclusions. The writer never invents a row inventory.
- `category_binding`: committed reference (`repo`, full `commit`, repo-relative `path`, `sha256`) to `rows: [{row, category}]`. Its unique IDs must exactly cover eligible binary input units after the two explicit ordinal exclusions below, categories must be frozen before capture, and original E58a source joins must be audited in the binding plan. W1/E36/E49 row names must carry bank qualification to avoid collisions; no category inference from outcomes.
- `asset_verdict`: committed reference to the feasible machine-readable verdict, including `j_lens_available: false` and `source_card` as a committed reference to the full prose card. Both actual Git commits must precede capture. Relative `source_card.repo` resolves from the verdict repository.
- `custody_availability_receipt`: absolute-path/SHA256 reference to an I-2 attestation with `issuer: I-2`, `checked_at`, exact `capture_seal_sha256`, `asset_card_sha256`, `j_lens_public: false`, `go_issued: false`, `reader_outputs_accessed: false`, and `readers_held_until_record_commit: true`. Check time must be after capture and no later than record creation. These assertions require real operator evidence; a JSON validator cannot authenticate a person or prove global absence by itself.

Invoke once, only after a committed real binding plan exists:

`python results/g_agreement/understand/e75/e74_absent_j.py /absolute/path/to/committed_E74_plan.json`

Fixed output is `results/g_agreement/understand/e75/E74_PREGO_RECORD.json`; exclusive claim is `cache/g_agreement/understand/e74/E74_PREGO_RECORD_ONCE.json`. The output includes the I-2 reader-admission fields (`worker`, `created_at`, capture/input hashes, unread declaration, exact absence text, prose-card hash, permanent flag, complete category forecast) and full provenance references. Then verify, secret-scan, pull/rebase and commit it BEFORE GO. I-2 verifies the real commit and chronology and alone issues GO. Never reset a claim or silently overwrite a record. No plan with fabricated capture hashes is written now.

### Original W1 ordinal rows

Carry Guiv's ruling relayed by I-2: retain captures of original `W1/python_depth_ordinal` and `W1/table_column_ordinal` (144 dev + 144 test each), preserving labels and splits, but exclude them from confirmatory scoring. No binarisation or invented ordinal criterion. The input unit manifest lists these captured rows; the writer subtracts only these exact registered exclusions, records their reasons under `confirmatory_exclusions`, and requires category forecasts for the remaining eligible binary rows. I-2's requested reader-scoring rows must use that same eligible set; the capture inventory retains the ordinals. The final E75 binding must carry both exclusions explicitly rather than count them as forecast units. All other coverage omissions fail validation. This also applies if the public-J route becomes feasible; an actual J-forecast must list the same exclusions.

Missing J predictions/null summaries are null, never zero or invented MISSED forecasts. The GLM category baseline remains a sealed E75 input, but cannot contribute paired J-minus-category statistics without a prospective J forecast. The existing E75 J scorer remains unchanged; its final input binding must distinguish category-only GLM coverage from the pool with valid prospective J predictions and report the absent-J scope explicitly as NOT EVALUABLE for J comparisons.
