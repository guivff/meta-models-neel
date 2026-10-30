# E35 raw-input and encoding contract — 2026-10-25

Authority: §131 clarification 1 at
`ff48f19ac143b436c7c6e9586473f1e160045da9`. This is a provenance audit and a
contract for later Integrator preparation. It is not a production collector,
launch request, passing-gate receipt, or assertion that decomposition inputs
have been assembled. No gate rerun result, private truth labels, activation
values, SAE codes, latent labels, or decomposition scores were inspected for
this note. Array dimensions below were read from NPY headers only. Metadata
checksums were recomputed; large-array checksums are those recorded in existing
seals and must be independently verified before use.

## Prerequisites for the later assigned stage

1. Obtain and validate the complete passing SAE gate, its frozen sample/request
   lineage, and the exact checkpoint that passed. Gate criteria remain 50,000
   held-out tokens, FVU ≤ 0.25 and dead-latent fraction < 0.10.
2. Verify that the rubric, blind prompt, selection procedure and decomposition
   source freeze were committed before production selection or decomposition.
   Initial dev-h latent selection/context preparation needs gate PASS plus
   this committed freeze; it cannot depend on labels it is about to produce.
3. Finish blind interpretation of the exact selected 300 latents and independent
   double coding of the frozen 30-latent subset. Verify context payloads, judge
   version/decoding pins, both output sets and label seals. Full decomposition
   and analysis need these completed label receipts.
4. Verify all relevant raw-source seals and full file hashes, complete the
   missing dev policy reconstructions, and perform exact joins as specified
   below. Reuse is conditional on these checks; this audit is not a substitute.
5. The Integrator must issue the bounded production assignment and later launch
   request. Account for every prior E35 attempt and all subsequent model,
   context-collection, encoding and pilot time within the total ≤ 6 GPU-h cap.
   Use a finite wall-clock deadline, admission timing and the Integrator's
   current §135 pod ceiling/spacing. Do not launch from this note, create a
   second decomposition analysis, or bypass its global once-only guard.

The production collector/launch request has not been released by this audit.
Any later collector must implement this contract and the frozen source schemas;
unfinished preparation must remain reported as unfinished.

## Original W1 population and truth provenance

Local audited W1 root:
`<mats-minis-root>/cache/g_agreement/blindspot/w1-readonly-20261024`.
Paths are locators; hashes establish identity after restaging.

| File relative to W1 root | SHA256 |
| --- | --- |
| `w1-bank-v2/INPUT_SEAL.json` | `f79302298eb1a8e9d0c46a996adc4c3071ba952fd77e0ea5215a00f1bad64a2c` |
| `w1-bank-v2/manifest.json` | `6e38ba7e5a5998082489ece5ab63a8a720bc039df6f32874b37481523f9f8f17` |
| `w1-bank-v2/items.input.jsonl` | `a8a43021c7958ec8b1a7682c1a2f46a5238dac9008c383f2205237cf06ad4d02` |
| `w1-bank-v2/templates.json` | `57cad0d1bce20de00026cab2515b3c43a2925d50b2944e0d0556376e88833172` |
| `w1-bank-v2/items.DO_NOT_STAGE.jsonl` (manifest pin only; not opened) | `48497c10082f18a5e80034c34e97e7139ee9783de8a8b28440e2e30535dfa07b` |
| `w1-assembled/target/SCORE_SEAL.json` | `d6f12937d5f85b2c44c98a71b7b0cc5fb8eb1fa7c6e92c42b1c0876f534d938a` |
| `w1-assembled/target/items.order.json` | `7677bacaf24c96d1198ce48c2b0dc14c78a19bcc09824f1a1cd3457f80ad5d4c` |
| `w1-assembled/target/provenance.target.json` | `75e7b6c1048a744b2d3795211766a98a87aaa8986bbfef8ac7039a9ed4589762` |
| `w1-assembled/target/acts44.npy` (sealed pin) | `a7b2886cad188f1483fcd00d31b481b409fdfd4c3c78b59a3eadf3f67d5cb71a` |

The original target array has shape **7296 × 5120**, fp32. It is not already the
E35 4200-item population. Join h by the complete original `items.order.json`
mapping and the frozen selected dev/test IDs. No truncation, position-based
assumption, new split, or complete-case selection is permitted.

The selected population is the original 25-row W1 set, 2100 dev and 2100 test
items, 84 per split per row with 42 of each value. Frozen first value A is the
positive probe label. Derive `id`, `row`, `split`, `label` and `cluster` from the
SHA-bound original private bank and templates, and compare the derived records
with pack metadata. Checking ID sets and balance alone cannot detect relabeling
or reassigned row/cluster metadata. Private truth material remains in cache.

The exact rows are `json_status`, `json_type`, `latex_environment`, `latex_role`,
`latex_section`, `latex_subject`, `list_depth`, `list_index`, `list_priority`,
`list_topic`, `prose_paren`, `prose_quote`, `prose_sentence`, `prose_sentiment`,
`prose_topic`, `python_argument`, `python_comment`, `python_depth`, `python_error`,
`python_indent`, `python_string`, `table_column`, `table_role`, `table_row`,
`table_status`.

## E21 population files and reusable dev R_win

Local audited E21 input root:
`<owner-worktrees>/wt-wmech/cache/g_agreement/understand/e21`.
The following metadata files and their hashes were rechecked without opening
private truth labels or reconstruction arrays.

| File relative to E21 input root | SHA256 |
| --- | --- |
| `INPUT_SEAL.json` | `a617fde6bc3c2511383537e3153f84c56d1b34108ee04e4aa4ac671c628fdd53` |
| `templates.json` | `97257b242380b0e68a7418dd36959f1708ce5ccaf68e2935ddd18c70e40ceb2b` |
| `dev_ids.json` | `b7cc65c3aaf28a2a33fb902f596c9f7936c86abc163f8c9224fa122d3cdaad61` |
| `test_ids.json` | `f52139f7f1036f73198038e798cc2640456208711f2e97f018ee0391af4e8cf9` |
| `items.input.jsonl` | `e75f0a51c71e1142160ed7a136956d89a1999fff165ebe6a0521155eb32b6c1a` |
| `texts.input.jsonl` | `1a503afa9efca8796f6fd36bd4e76b380cdff42d98031b02c7e4b2aebed16415` |

Reusable E21 collection relative to that root:
`0ys021u7gwhb8d/final/out/E21_NEW_RUN`.

| Collection file | SHA256 |
| --- | --- |
| `SCORE_SEAL.json` | `b04c4db7aff9319d89ecb3fa4e7216fac5d7a1095271227a80d2f7993724f031` |
| `ids.json` | `021821b53b050e28dd4410f4635033368d1cc4b0f4c3a4553be606bd7fcdab24` |
| `recon.npy` (sealed pin) | `4008c88f094b3f6a2c16f24e664c680a97387247ddd111f62b9643cabfe4ef88` |

The collection reports `E21_COMPLETE`; its NPY header is **16044 × 5120**, fp32.
Its `ids.json` matches the ordered `id` fields of `texts.input.jsonl`. Select
the **2100** records with `path=dev_real`, `arm=dev_real`, `split=dev`,
`variant=0`, then join their underlying `item` field to the original W1 dev ID.
The composite reconstruction ID is not the original W1 item ID. Do not use
E21's description/exhibit arms as real-next-16 reconstructions. These existing
dev reconstructions remove the need to collect dev R_win again, once their
full lineage and arrays are verified.

## Test R_win and existing R_ol candidates

The next table uses paths relative to
`<owner-worktrees>/wt-wmech/cache/g_agreement`.

| Candidate | Relative directory | Coverage and fp32 header |
| --- | --- | --- |
| Test R_win | `blindspot/understand-units/5711bz7c1ulept/out/E1B_E12_NEW_RUN/e1b/ar` | 2100 test IDs; 2100 × 5120 |
| R_ol | `blindspot/mechanism/w3-units/rk4veemwm0jf9i/w3-residuals` | All 2100 test IDs and 291 dev IDs among 2772 records; 2772 × 5120 |

| Candidate/file | SHA256 |
| --- | --- |
| Test R_win `SCORE_SEAL.json` | `a2b5e3f1d8cdfe8e52ee3d30adf5ae26dfce7f0145eb52f402c0c3fec9a7978f` |
| Test R_win `ids.json` | `73e227700ee7ebddbdf021193da5801865aed872c19d01faae712e9fff70db9a` |
| Test R_win `recon.npy` (sealed pin) | `5c03e0b10fbfb8f60a6c1c1becb278b33d6a0731bd2fce76574184cb2310545f` |
| R_ol `SCORE_SEAL.json` | `79e7390b618a84f5c74991cb97c5f89bb5fd7695406480744cec508e2ccc16db` |
| R_ol `ids.json` | `ad3ab0fa585d79a93b3a3ed8615bd2995d10d5c0d21460da3afbf42f2763857a` |
| R_ol `recon.npy` (sealed pin) | `3a7c5ff66c7c5750df9236f23bf313c605ef497fa5e736fafbbe7ef6a813b2bf` |

Additional lineage pins already recorded in `MECHANISM_AUDIT.20261025.json`:
E1b continuation seal
`a799e1f9fc1f6dfc41fd55bbb63f2a1bcb9fd0157f3ac226d95041741503444b`;
native44 greedy-readout seal
`936d7a05519aea8dad71b8c074dbe682a7503209996c49c4806babb9c73e0684`.
Verify these complete source chains at staging. R_win is the sealed target
continuation after the capture position, tokens p+1 through p+16, decoded by
the frozen producer. Reuse its exact text; do not regenerate a different window
or silently retokenize/trim to force a desired length.

**1809 dev R_ol are still missing from the audited candidate.** The Integrator
must complete those original dev IDs with the same native44 greedy Oracle
readout policy (256-token cap) and official AR path, then seal their provenance.
Do not drop missing items, fit probes on 291 dev items, substitute target next
tokens for readouts, or collect replacements for already sealed test items.

## Official reconstructor and SAE dimensional contract

Mechanism source commit: `d99db94c5fc3c263b97294fff26ae78d2cd9705d`.
Source-content pins at that commit:

| Source | SHA256 |
| --- | --- |
| `projects/g_agreement/w_claims/ar.py` | `c64a684c30fa2d542283b95575dd61fca61a82d9ffebba333bd9fafdbd463ee1` |
| `projects/g_agreement/understand/e21.py` | `f0c595df8f02d6c28bcde87a0c6c186eab2a25340988cba50849fcef4f380f65` |
| `projects/g_agreement/understand/e21_analyse.py` | `252c0d42487433f0be3d8aa123613009c8724ae046330d4fc00964243c1d6baf` |

Official AR implementation: `agu18dec/olens_draft` at
`a32590085a6070d75f950155d3c2b3db3eec97ef`; weights:
`agu18dec/olens_and_ar` at `c95215d5d2f6250f20c305ae55c6e4d7569f92dc`,
subfolder `ar_ptag_pooled`. The moments SHA256 is
`178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a`;
the official loader uses ridge 0.1. Use `ar.layers.index(44)`, then `[:,0]`.
The returned reconstruction is raw fp32 block-44 residual space, width 5120.
Do not whiten or inverse-whiten it again. Form `h-R_win` and `R_win-R_ol` in
raw space, then apply the passed SAE's own frozen normalization/encoder.

Transfer SAE identity is fixed by `GATE_PLAN.20261025.json` and `sae.py`:
`Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50` at
`13d4221569f7ca5d3c1e605e3e3dc95117e4807c`, `layer44.sae.pt`, SHA256
`7316b684ada2e8461d814c6fc78200cc2a1f5b6756bedf172f58ce5f92b3977f`.
It has width 5120, 81920 latents, k=50 and the pinned adapter's identity input
normalization. The conditional registered fallback instead has 16384 latents
and k=64; its checkpoint and normalization must be frozen and bound to its own
passing gate. This note does not claim a fallback checkpoint exists or passes.

Compute decoder-column norms from the actual verified checkpoint's W_dec;
do not accept a separately supplied vector merely because it has plausible
dimensions. b_dec is excluded from norm shares. Bind the resulting norms and
all codes to the same checkpoint and normalization manifest. Every code arm
must have the passed dictionary width, distinct valid latent indices, finite
nonnegative values, and no more than the passed k positive entries per item.

## Encoding-pack interface and analysis admission

The intended pack contains the complete aligned metadata list with fields
`id,row,split,label,cluster`; exact original `dev_ids.json` and `test_ids.json`;
checkpoint-derived `decoder_norms.npy`; and sparse index/value code arrays for
`h`, `window_loss`, `policy_loss`, plus the separately descriptive positive
code differences. It must bind original input provenance, exact item order,
raw array joins, SAE identity/normalization, gate result, committed freeze and
completed blind-label receipt in a complete encoding seal. The final frozen
analyzer/plan schema governs exact JSON field names.

Array values and private labels stay in cache. Validate complete source hashes,
IDs, truth metadata, dimensions, provenance and output availability before the
global once-only analysis claim; claim the guard before numerical analysis.
The 25 per-row probes fit only their 84 dev codes with the pinned W1 logistic
recipe, evaluate the corresponding 84 test codes, and retain the original
disjoint template clusters. There is no probe refitting, split search, missing
item selection, label-driven retry or automatic science retry.

## Frozen module interface (2026-10-25)

`decomposition.authorize_preparation(authorization_path)` validates the gate and
source freeze for dev selection/context preparation. `authorize(...)` also
requires the completed label seal and strict dispatch custody. The authorization
JSON names issuer `integrator`, experiment `E35`, `rubric_committed=true`, the
40-character `freeze_commit`, `freeze_sha256`, `gate_dir`, `gate_request`,
`gate_result_sha256`, `sae_checkpoint_sha256`, and (for full authorization)
`labels_dir` and `labels_seal_sha256`. No such production authorization is issued
by this note.

The later reviewed collector must load the actual checksum-verified passed SAE,
use `decoder_column_norms(sae)` on that instance, and call `encode_triplet` in
bounded batches only after full authorization. Pin the collector, raw input
seals, joins, checkpoint, normalization and deadline in its launch request.
The frozen numerical code is not itself a complete GPU collector or timing
admission implementation. That operational assembly and its review remain
prerequisites, including verification that the supplied norm vector was computed
from the passed checkpoint. The analyzer cannot infer that from a vector alone.

The complete `ENCODING_SEAL.json` has `status=COMPLETE`,
`primary_encoding=encode_raw_difference_directly`, `freeze_sha256`,
`gate_result_sha256`, `labels_seal_sha256`, `sae_checkpoint_sha256`, and a `files`
map of relative file names to SHA256. Required files are `items.json`,
`codes.npz`, `decoder_norms.npy`, `dev_ids.json`, `test_ids.json`,
`items.input.jsonl`, `items.DO_NOT_STAGE.jsonl`, and `templates.json`.
The two ID files, stripped E21 input metadata, original W1 private bank, and
selected templates have exact pins in `DECOMPOSITION_PLAN.20261025.json`.
The stripped input file contains only id/feature/split; value and cluster checks
use the separately pinned private bank. Do not send that private bank to a
model or judge: it is supplied only to the local CPU analysis pack after
collection. No private bank contents are committed.

`codes.npz` contains `<term>_indices` and `<term>_values` for `h`, `window_loss`,
`policy_loss`, `window_code_difference_positive`, and
`policy_code_difference_positive`. Each is 4200 by k and aligned to `items.json`.
`analyze_pack` validates the source metadata and seals, then consumes the global
analysis guard before reading numerical codes. It writes one `RESULTS.json`
and `ANALYSIS_SEAL.json` under E35 cache. Source pins, guard files, failed
attempts and registered analysis outputs are never overwritten.
