# W-core packed exploratory launch

Run E5 → E8 → E6 in one Python process on one integrator-operated pod. Load the Oracle/target model with its adapter once, the NLA verbalizer once, and the J-lens projection once. Reuse W1's sealed activations; no target capture or activation reconstructor is needed. The request is `LAUNCH_REQUEST.json`; its exact source archive and staged input paths are authoritative. Publish the source and frozen manifest before assigning compute.

| Scope | Frozen population | Science cap from its own first timing unit | Output folder |
|---|---|---:|---|
| E5 (§92) | 6 rows × 84 test items; 8 frozen phrasing pairs per reader | 1,080 s (0.3 GPU-h) | `E5/` |
| E8 (§95) | 40 rows × 40 value-B test items; six doses; three native readers | 3,600 s (1.0 GPU-h) | `E8/` |
| E6(b) (§93) | 5 rows × 84 test items; two verbalizers; up to 32 tokens | 1,800 s (0.5 GPU-h) | `E6/` |

Shared setup has one 1,500 s allowance, including model loading and an unscored synthetic warm-up for each distinct scoring/generation path. Each experiment then starts its own immutable `EXPERIMENT_CLOCK.json`, measures three warmed production-sized units per feature/reader, and applies its own forecast gate `min(1.5F + 360 s, own cap)`. Timing work counts as science. E8 times the largest dose; E6 conservatively scales timing to 32 generated tokens. No experiment borrows another's cap, and later clocks are not measured from pod creation. Absolute custody, a 180 s retrieval reserve, and the program stop on 27 October at 23:59 Europe/Zurich also apply.

The worker writes a separate forecast, provenance, first-science clock, science receipt and score seal in each experiment folder. Controlled NO_FIT/cap failures receive an explicit failure receipt; the next independent experiment can proceed within the absolute allocation. Unexpected runtime or integrity failures stop the pack. No automatic retry or scope reduction is authorized. Retrieve the complete output root, including partial scores and any failure receipts.

E5 limitation: W1's unchanged J-lens scorer accepts single-token candidate variants, not natural-language sequence queries. All eight requested J-lens phrasing pairs are frozen, but their score cells are explicitly `UNSUPPORTED_SEQUENCE_QUERY_WITH_W1_J_LENS`; they are not assigned chance scores. Oracle and NLA use W1's native paired scorers. This prevents claiming full three-reader phrasing coverage.

E8 uses signed dev-fitted unit probe directions scaled by their dev class-mean projected gap, without outcome-based sign changes. Recipient selection, all 80 native directions, and the 120 existing W1 value-A reference medians are frozen. The primary descriptive gain is the slope over the fixed doses 0, 0.5 and 1; report every dose and the all-dose slope too. Crossing is the first observed grid dose reaching the value-A median; no interpolation or extrapolation.

E6 appends the frozen continuation request to each reader's native prompt and retains the raw text. Native prompt construction failures and explicit/descriptive refusal markers are reported. The frozen scripts are surface proxies with neutral scores for absent markers; they do not establish syntactic correctness. E6(a) is a separate CPU-only check of already sealed W1 free readouts and does not consume this launch's science allocation.

All experiments are exploratory; report every row, phrasing, dose and failure. E9 remains CPU-only after E1/E2/E4/E8 arrive, with explicit missing coverage rather than imputation where the source experiments cover only 25 of 40 rows. W10 and §84/§87 analysis retain priority when their prerequisites arrive. The integrator alone publishes and operates this launch.
