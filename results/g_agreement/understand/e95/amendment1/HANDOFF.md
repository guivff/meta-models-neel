# E95 amendment1 — all8 READY packets for I-3 re-release / Integrator

Authority **§220 E95 amendment1 c579174dc**. Both required fixes are complete: caps re-priced from the maximum actual post-load Oracle per-shard running mean **11.305866354028694s/batch**, and live admission uses **1.15 on remaining work only at every check**. Setup and future discarded warm-ups are unpadded. Native pricing remains stratified by reader/arm/layer/width; an observed mean changes its own stratum, not every other stratum. All original row/item/order/seed/positions/decoding/native/capture code are unchanged. The7failed attempts' operational files are hash-verified from the sealed pulls; no raw scientific values were opened.

**Budget:** production caps sum **157894s** (≤184475s); prior **9924.6s** retained; projected cumulative **167818.6s =46.61628GPU-h**, below **194400s/54GPU-h**, with **26581.4s** headroom. Already booked custody/USD is never reset or rebooked. This is the one re-time; another NO_FIT means NOT RUN for that shard. CORE preempts; Thu24:00CET create deadline remains.

| Shard | Cap s |
|---|---:|
| e95-representative-3-0 | 5810 |
| e95-representative-3-1 | 22079 |
| e95-representative-3-2 | 22075 |
| e95-representative-3-3 | 19794 |
| e95-representative-3-4 | 22059 |
| e95-representative-3-5 | 22055 |
| e95-representative-3-6 | 22051 |
| e95-representative-3-7 | 21971 |

## Exact delivery

Source archive: `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmechb/cache/g_agreement/understand/e95/amendment1_v2/source.tar.gz`

SHA256 **34c603dbc2a7e4a8956f617c987679a045bc5d76abf2e690dde1454ca99ef13f**; source seal **13503360950007614107d88fddd72e14b75fed12107410b1910ece945611d5ad**. All8new input archive paths/hashes/seals are in REQUEST.json beside this file. Each sealed STAGE_REQUEST.status is **READY**. Review copies of input seals/requests are under inputs/; complete PLAN/items/public members stay in the corresponding archives. Never use the earlier cap47 input/source hashes.

I-3 re-releases this REQUEST (SHA256 **092cb709704fe103d5b20e88aebf008400ddddd1227f6eae427ea27245b0e711**) with fresh pool/global/quote/guard admission, then TrackQ stages/launches. All packets are READY technically; full_launch_allowed remainsfalse until that independent re-release. Assignment fields must be updated to the new timing95.source/profile_set/decision/scope/inventory/index hashes, with prior_seconds/custody cap as admitted. Preserve original provider creation and fixed deadlines. No B allocation or paid call.

**Required entrypoint: admission95.py**, not worker87.py. The new packet validator rejects the old entrypoint before model loading, because its clock would use1.25. Run the same worker arguments:

```sh
python results/g_agreement/understand/e87/admission95.py --inputs /PATH/inputs --input-sha NEW_SHARD_INPUT_SHA --source-sha 13503360950007614107d88fddd72e14b75fed12107410b1910ece945611d5ad --assets /PATH/ASSETS.json --assignment /PATH/ASSIGNMENT.json --out FRESH_OUTPUT
```

**Shard3-0:** also pass `--reuse-hardware results/g_agreement/understand/e87/E87_REUSE_HARDWARE.json` and set assignment.reuse_hardware_sha256=**9393a5aae4cd1bad2bd3433660e8c09a85acde6721ccbde659898f5f23395a09**. The exact I-3 c113a227 receipt is included in the source archive, keyed by rows3,5,7,12,13,14,15,38,41,43. Its original evidence remains under e95/reuse_hardware; no reconstruction/guess is needed. No E87 real readouts are regenerated.

## Checks and pricing evidence

Fresh exact-source imports of admission95/reprice95/worker87/timing95/representative95 and actual Runtime PASS; **47tests PASS in10.16s**. All8actual extracted READY packets pass source/input checks, frozen native schedule verification and runtime admission with explicitly synthetic CPU assignment fixtures (not live pod authorizations). All72whole rows are preserved, no duplicate membership. Source comparison proves every pre-existing native/capture/decoding dependency unchanged; only admission/CPUpricing code changes.

Sealed operational metadata replay at each original FORECAST filemtime, using the newly priced cap and1.15live rule:
- 3-3: remaining18503.02s <19123.05s available: ADMIT.
- 3-5: remaining21176.75s <21415.63s available: ADMIT.
- 3-6: remaining19109.08s <19952.64s available: ADMIT.

Exact hashes and numbers are in CPU_VERIFICATION.json. These are CPU arithmetic replays, not scientific analyses or new GPU measurements. Loading/nonfinite/crashes and genuine cap overruns remain fatal/NO_FIT. No raised cap beyond the registered194400s and no suppressed checks.

Setup envelope1279.07391s includes staging211.08660s once. It uses the highest observed production Oracle load plus frozen measured NLA/warm-up/overhead tail, and the larger known own timing staging versus the registered150s fallback. It is explicitly a prospective conservative envelope built from measured components, not a falsely claimed complete new timing profile. No production staging time is inferred from filemtime. NativeNLA/capture/placebo frozen rates are retained; Oracle stratum rates are floored at the maximum actual running mean from3-3/3-6/3-7. Each per-shard cap is ceil(setup envelope+1.15repriced work+60s retrieval). REPRICED_DECISION.json binds all original and new metadata hashes, corrected§221 gate, new scope, prior custody and totals.

This source is prospective only. Original failed pulls, historical40/47h receipts and their source archives stay unchanged. Complete rows only, no stitching. I-3 owns once-only analysis; Integrator owns GPUs/guards/booking and the second-failure disposition.
