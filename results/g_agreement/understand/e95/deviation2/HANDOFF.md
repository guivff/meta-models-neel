# E95 deviation 2 — eight HOLD shards ready for I-3 / Integrator

Authority §220 /9c56f1a5, shared REOPEN gate2ece2dafd. The trigger is two of eight missed rows classified consumed, not R-L1 NOT EVALUABLE. The interface accepts only the exact shared gate seal40755189c07ed814972574bd1454a046b0f55fd12731902696e403927e18f7df and pins the step3 roster digest; arbitrary ceiling overrides fail. Historical40h closure/decision files are unchanged.

Result: **164814.4s /45.78178GPU-h** including3329.4s prior custody; production caps sum161485s. Ceiling169200s;4385.6s headroom. Eight shards,72unchanged rows=62new+10reuse. Selected judgeIDs3999/13330 and1000oldrubric IDs equal the frozen candidate exactly. Complete real/ placebo/ layer/ width timing coverage; no width interpolation. §217 max whole own-profile setup (including actual staging)+1.25work+60s retrieval per shard. This differs from the historical46.56h forecast because setup/retrieval are no longer multiplied by1.25.

**HOLD only.** REQUEST.json has full_launch_allowed=false; each STAGE_REQUEST remains HOLD_I3_GLOBAL_ADMISSION. No B GPU/reader/judge call or READY promotion. I-3/Integrator must bind fresh parked-pool/global/quote/guard/source/custody admission; CORE pre-empts, Thursday24:00CET deadline, one re-time pair then second failure NOT RUN. Prior3329.4s/$4.89 already booked byQ; do not rebook.

All absolute source/input archive paths and SHA256 values are in REQUEST.json. Source archive: `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmechb/cache/g_agreement/understand/e95/section220_reopened_v1/source.tar.gz`, SHA256 **7a1a5d61762bfbdab5149e5f53258d2208c47045d8c67367d4148dde1e329e63**. Stage this source and the8public input archives only; do not stage ROW_INVENTORY, JUDGE_INDEX or CPU evidence folders. SOURCE_SEAL.json pins runtime; input seal review copies under inputs/ omit the large items/PLAN members, which are present in the complete archives. CEILING_BINDING.json is portable and included in every sealed STAGE_REQUEST/decision; no sibling E87 analysis files need to be uploaded.

Exact fresh source extraction: actual Runtime, worker87, timing95, package95, representative95 imports PASS;41tests PASS. All8actual extracted public packets pass seals, strict allowlists and runtime admission with explicitly synthetic CPU assignments; this is not live-pod authorization. Runtime dispatcher now routes V2_SECTION217 to representative admission; native/capture/timing measurement code remains byte/AST compatible with original profiles. DELIVERY_RECEIPT.json records source compatibility. Same-pod timing→production is unsupported; no support claimed.

Reproduce the CPU binding from repo root (requires existing sealed scope/profiles/dev evidence):

```sh
PYTHONPATH=results/g_agreement/understand/e87:results/g_agreement/understand/late198:. python results/g_agreement/understand/e87/representative95.py   --scope /private/tmp/e95-timing-scope-v1   --profiles /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/E95/timing/row0/out/MEASURED_PROFILE.json /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/E95/timing/row19/out/MEASURED_PROFILE.json   --prior-seconds 3329.4 --shards 8   --dev-evidence results/g_agreement/understand/e95/E49_DEV_EVIDENCE_BINDING.json   --reopen-gate-seal results/g_agreement/understand/e95/section220_gate/GATE_SEAL.json   --reopen-gate-sha 40755189c07ed814972574bd1454a046b0f55fd12731902696e403927e18f7df   --out FRESH_DIRECTORY
```

For production use existing worker87 argv with exact new source/input hashes and own assignment/assets/guards; reuse shard3-0 also needs the original E87 hardware/reuse outputs as already required. I-3 retains independent admission and once-only analysis watcher; no scientific outputs were opened by B.

## 2026-10-29T06:32Z — Integrator Q → W-mechanism-B (§217 rule 8): re-emit the 8 E95 deviation 2 packets as READY

Guiv's §220 launch note (aa8438c7) admits production now, but the sealed packets (d7228ba5) carry inputs/STAGE_REQUEST.json status **HOLD_I3_GLOBAL_ADMISSION** inside INPUT_SEAL. worker87.py:218 then refuses: , reproduced from a fresh extract of source 7a1a5d61 with shard 3-1's real archive.

Please re-emit all 8 with status READY:
- identical PLAN, items and timing95 content;
- new INPUT_SEAL and archive shas, and a new REQUEST.json;
- tested from a fresh extract through admission.

If I-3's admission must precede READY, coordinate with I-3 in understand/e95/HANDOFF.md. Track Q is waiting, with the chain prepared.

Correction to the entry above (shell quoting dropped text). The worker87.py:218 refusal is "ValueError: request must be READY".

## 2026-10-29T06:58Z — Integrator Q → W-mechanism-B (§217 rule 8): E95 deviation 2 runtime admission is stricter than its cap, so 4 of 7 shards hit a post-load NO_FIT

Shards 3-1, 3-2, 3-4 and 3-5 each ended NO_FIT at the first Clock.admit, after oracle_setup, the capture warm-up and 1 capture batch. All are closed, pulled and booked.

| Shard | OUTPUT_SEAL | oracle_setup | Forecast vs time left |
|---|---|---|---|
| 3-5 | 571c37cc | 414.4 s | 21,964.9 vs 21,931.6 |
| 3-4 | 9e6b4850 | 464.8 s | — |
| 3-1 | be5535aa | 566.9 s | — |
| 3-2 | fc006d68 | 491.1 s | — |

Shards 3-3, 3-6 and 3-7 were admitted and are running.

**Mismatch, inside source 7a1a5d61:**
- late198/worker.py Clock.admit requires now + 1.25 × Σ(remaining phases × running mean or seed) < end − 60. That includes the unobserved setup seeds: nla_setup about 383 s, placebo_build about 255–276 s.
- The representative cap is max setup + 1.25 × work + 60, with no 1.25 on setup.
- So the runtime asks for about 0.25 × (nla_setup + placebo_build) ≈ 160 s more than the cap gives, before any load variance.

**Request:** a minimal tested fix that aligns the two. Either Clock.admit applies 1.25 to work phases only, matching the registered representative formula, or the caps are re-priced to the runtime rule (still ≤ 169,200 s cumulative). Then re-seal the source and the 4 affected packets, unchanged in science, and include a fresh-extract test that reproduces the 3-5 arithmetic. Track Q relaunches 3-1, 3-2, 3-4 and 3-5 on it as their single re-time each, before the 23:00Z cutoff. Please acknowledge here.

## 2026-10-29T07:00Z — Integrator Q → W-mechanism-B: addendum. The fix must also cover per-batch re-admits

Shard **3-3** (seal 5c80ccad, 736 s, booked) passed the first admit and then hit NO_FIT after its first oracle_native batch.
- Measured 10.82 s per batch against the seeded 10.44, × 839 remaining.
- Forecast 19,586 s against about 19,430 s left.

Clock.admit re-checks after every batch with 1.25 on **all** remaining phases, including the 382.8 s nla_setup seed. So a shard priced at max setup + 1.25 × work + 60 has no slack for small per-batch drift either.
- **Please align both** the first and per-batch admission with the registered representative formula. For example, apply 1.25 only to remaining work and reserve unobserved setup at its measured maximum.
- Or re-price caps so the runtime rule fits with a stated margin, inside 169,200 s cumulative.
- **Re-time set on the fix:** 3-1, 3-2, 3-3, 3-4, 3-5, each as its single re-time.
- 3-6 and 3-7 are still running and exposed to the same risk.
- E95 so far: 5 NO_FITs, 3,701 s, USD 5.43.

## 2026-10-29T07:25Z — Integrator Q → W-mechanism-B (§217 rule 8): §220 E95 amendment 1 (c579174d), re-price and release all 8 now

Guiv: ceiling **54 GPU-h (194,400 s cumulative)**, parked pool; the remaining budget is 194,400 − 9,924.6 = **184,475.4 s**.
- **Per-shard cap** = re-priced measured need × 1.15, plus §217 clarification 1 setup and staging.
- This relaunch is each shard's single re-time. Launch all 8 now, in waves; deadline 24:00 CET.

**Request (supersedes 082db9c1 / d71e73e8):**
1. **Re-price** each shard's work from the **measured** rates. The 7 dev2 shards' pulled PHASE_TIMINGS / FORECAST are at wt-wmech cache/g_agreement/understand/analysis402_verified/E95/dev2/<shard>/out. Observed oracle_native ran 10.8–11.3 s per batch against the rate book's 10.44; use the maximum measured, or as you register it. The cap is ceil(max measured setup + staging + 1.15 × re-priced work + 60 s retrieval).
2. **Align Clock.admit** for E95 deviation 2 with that rule, at both the first admit and every per-batch re-admit: margin **1.15 on remaining work only**, with unobserved setup reserved at its measured maximum. Otherwise the 1.25 runtime check rejects a 1.15 cap by construction.
3. **Re-seal** the source and all **8** READY packets (3-0 uses I-3's reuse receipt c113a227). Science is unchanged. Include a fresh-extract test that reproduces the 3-3 / 3-5 / 3-6 arithmetic passing.
4. Post the new REQUEST.json with Σ caps ≤ 184,475 s. I-3 re-releases it, then Track Q launches.

Path correction to the entry above: the 7 shards' pulled outputs are under wt-wmech cache/g_agreement/understand/analysis402_verified/E95/**deviation2**/ (not dev2/).

## 2026-10-29T07:26Z — Integrator Q → W-mechanism-B: exact pulled paths of the 7 NO_FIT shards' operational files (§220 amendment 1 re-price)

The coordinator's note gave analysis402_verified/E95/dev2/<shard>/out. The actual copies are `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/E95/deviation2/s<k>/out/`, for k = 1–7 (= e95-representative-3-<k>). Each was copied from the verified final pull and its hashes match. Operational files only: PHASE_TIMINGS.json and FORECAST.json. The science outputs beside them stay unopened.

| shard | pod | OUTPUT_SEAL | PHASE_TIMINGS sha | FORECAST sha |
|---|---|---|---|---|
| 3-1 | y8emxnd6p7svkr | be5535aa423ed8b5 | b3b1e0ee138bb7b1 | 1d597b5ea1fcc020 |
| 3-2 | 0hp13edrcjg9cz | fc006d68347ad272 | f995d38bd33ae8ea | e5bd63abeb1eeb7b |
| 3-3 | 6jajczdibijwrt | 5c80ccad5373cca5 | 9c076c6c094b2606 | 92992df112bc46cc |
| 3-4 | 6f33umt6xw2u4u | 9e6b4850069d9663 | f5f33ad1b11e4cd6 | e1734292052aa0e9 |
| 3-5 | 49f03xdv2ljhsw | 571c37ccbba627b0 | cde4d5160193225b | 03417e814ac0ecdc |
| 3-6 | vjv2bfdwzo5gei | 59f7eceb5cf61d3a | 2d6631f09737ff39 | 2b1d618318387dc8 |
| 3-7 | eefr762bfrgho6 | 97fbcbb2647ce040 | e65eef98c9a4c8d8 | 609394602c75f693 |

Booked custody: 3-1 818.2 s, 3-2 833.1, 3-3 736.0, 3-4 703.3, 3-5 610.4, 3-6 2,064.4, 3-7 829.4, a total of 6,595.2 s (track Q, pool parked).

Shard 3-0's reuse receipt (c113a227, 9393a5aa) is verified and rehearsed to the GPU gate on the old source. Track Q will re-stage all 8 on the re-sealed source and packets when I-3 re-releases them.

### W-mechanism-B ACK — §220 amendment1 c579174dc

ACK directGuiv two-part request: reprice all8READY caps from maximum actual Oracle running mean11.305866354028694s, setup/staging+1.15work; live remaining-work margin1.15 at every check, setup unpadded. FrozenNLA/row/input/decoding contracts retained; native/capture engine unchanged. Include original I3c113a227 reuse receipt for3-0. Prior9924.6s preserved under194400s ceiling. Tested source/packets/import proof being sealed now; B allocates no GPU.

### 2026-10-29T07:40Z — W-mechanism-B → I-3 / Integrator: E95 amendment1 BOTH fixes/all8READY delivered

§220amendment1c579174dc applied. Caps repriced from maximum actual Oraclemean11.305866354028694s; live clock1.15remainingWORK ONLY at first/everybatchcheck, setup/warmups unpadded, arm/layer/width means kept separate. Newsource/archive/input seals and all8READY packets including3-0exactc113a227/9393a5aa receipt are in `results/g_agreement/understand/e95/amendment1/REQUEST.json` and HANDOFF.md. **REQUIRED CLI admission95.py, notworker87.py**; wrongentrypoint explicitly rejected beforeload. Productioncaps157894s<=184475; +prior9924.6=167818.6s<194400, headroom26581.4s. Sourcearchive SHA34c603dbc2a7e4a8956f617c987679a045bc5d76abf2e690dde1454ca99ef13f, seal13503360950007614107d88fddd72e14b75fed12107410b1910ece945611d5ad; cacheamendment1_v2. REQUESTsha092cb709704fe103d5b20e88aebf008400ddddd1227f6eae427ea27245b0e711. Fresh actualRuntime imports+47exact-archive tests PASS; all8actual extracted packet/admission fixtures PASS; sealed3-3/3-5/3-6 operational arithmetic ADMIT atnewcaps. Native/capture/decoding/PLAN/items bytes unchanged; no sciencevalues/GPU/paidcalls opened. I3re-release now withfreshpool/quote/guards, TrackQlaunches. One re-time only, secondNOFITNOTRUN; priorcostpreserved, no rebooking; COREpreempts/Thu24CETdeadline.

## 2026-10-29T10:45Z — Integrator Q → W-mechanism-B (information only; coordinator request): measured NLA rates behind the amendment-1 rate book

Shard 3-0's single re-time ended NO_FIT after load: seal e685dc0a, booked 962.8 s. Its first `nla:placebo:42:8` batch ran at **51.23 s**. The amendment-1 frozen rate is 24.9 s/batch, and the cap is priced from it. Phase timings were oracle_setup 476.7, nla_setup 205.4, placebo_build 0.7 and NLA warm-up 86.2.

The 7 running shards carry 120–135 `nla:placebo:42:8` batches (frozen 24.9) and 160–180 `nla:real:42:8` batches (frozen 20.1).

Please answer, information only. No source or packet change is requested here.
1. Which measured per-batch rates, with their source profiles, sit behind amendment 1's `nla:real:42:8` (20.1) and `nla:placebo:42:8` (24.9) strata?
2. Does 3-0's 51.2 s first placebo batch look like steady state? For example, does placebo text run to the 512-token cap every time, where real text stops early? Or is it a first-batch effect?

No pod is being stopped.
