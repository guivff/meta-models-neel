# E4: INCOMPLETE — sealed reader calibrations prove NO_FIT

Prediction: the Oracle lens receptive subspace excludes structure directions and includes meaning; NLA includes both, with weaker structure sensitivity; J-lens includes next-token-sensitive directions. **The prediction is unassessed.** No production gradient alignment, receptive-subspace or E9 results exist.

Under the current §91 ruling (`44ff2b5f`, 2026-10-24 22:15 CEST), the three sealed reader calibrations from `bldh3pcocqu8mm` must be reused. All five entries in its `SCORE_SEAL.json` (`ab2a0c94a5dbda656672d6a17fa51497aecccd8cd811049631c55dd0d75adaeb`) verify. Their original bytes and seal are retained in `attention_retry/sealed_previous/`. No calibration was recomputed or rescaled.

| Sealed phase | Warmed forecast, seconds |
|---|---:|
| J-lens | 9.804398 |
| NLA | 4684.404953 |
| Oracle lens | 3350.862404 |
| Reader subtotal | **8045.071755** |

The unchanged cap is `min(1.5F + 360, 2160)` seconds. Even setting all target work, transfers and elapsed time to zero, the saved reader forecasts exceed the absolute cap by **5885.071755 seconds**. Thus the existing admission rule cannot pass. CPU preflight: **NO_FIT_DO_NOT_LAUNCH** (`attention_retry/PREFLIGHT_NO_FIT.json`). E4 closes **INCOMPLETE on the sealed calibration stages**; no further retry or new allocation is requested.

The sole scientific implementation change selects `SDPBackend.MATH` only around the exact target JVP, restoring the previous backend on exit. Items (2100 reader, 3360 target), 25/40 rows, scoring algebra, k = 16/64/256, seeds, batches, CPU offload and prior sealed results are unchanged. The four-test-item equivalence checker forces SDPA flash and math, compares native Oracle asked log-odds with absolute tolerance 0.01, and writes PASS/FAIL/ERROR before any science. The actual Qwen CUDA check is **NOT RUN because preflight already fails**; `attention_retry/ATTENTION_EQUIVALENCE.json` freezes its four IDs and explicitly records no numerical result. No equivalence or kernel-support claim is made for the real model.

CPU validation: **125 tests passed in 17.57 s**, including an actual CPU math-SDPA full-vocabulary reverse-over-reverse JVP checked against independent finite differences, synthetic equivalence boundary/error receipts, backend restoration, and sealed calibration retention/tamper rejection. These are implementation checks, not scientific E4 outcomes. No new real-model forwards, GPU work, pod operations, label joins or scientific analysis were performed.

Prior attempts remain disclosed and charged by the integrator: `cybhnezi82omzz` OOM after 23.7 s; `bldh3pcocqu8mm` (`a0558379`) fixed memory (about 54 GiB, no OOM), sealed the three calibrations, then stopped on unsupported flash-attention double backward before the timing gate. The latter booked 160.4 s science and 1142.6 s shared non-science custody; original accounting is retained without duplication. The first attempt's lost metadata remains documented in `OOM_RECEIPT.json`.

The integrator receipt preserves setup 1500 s, cap 2160 s, `/weights/venv`, input/source seals and the original five-minute incremental plus final verified pull policy. Its disposition is **do not provision or launch**. E3 remains sealed and published at `b3e26598`, with exactly 258 MISSING cells; no E3 files were changed.
