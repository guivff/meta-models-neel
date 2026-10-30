# E74 v6 clarification 7 handoff

This sealed revision applies §192 clarification 7 (`f5720c36529f52bf506924fa73825df8b4c95d9e`). Use `resident-v6-c7/PACKAGE.json` and its source seal with the updated v6 H200 templates. The previous v6 archive and evidence remain preserved; do not pair the new templates with the old archive.

TP8 now permits **3,000 s boot plus smoke** and **forecast ×1.25 ≤ USD120**. TP4 retains **1,200 s / USD100**. Runtime clock validation, prelaunch/staging cost checks, NO_FIT evidence and the independent resident cost-watchdog calculation use the hardware-specific cap. TP8 admission binds clarification 7 explicitly. This package continues to implement 4×B200 and registered single-node 8×H200 only; the ruling does not itself implement 8×B200 or H100 here.

The author documents **~34 min TP8 boot**, versus ~11 min TP4, in [the pinned lens card, deployment section](https://huggingface.co/ceselder/glm-5.3-olens-lens/blob/689c5dbae3d2f83dbf969e234a023958f1612185/README.md#6-how-to-use). The forecast uses **2,040 s boot +120 s smoke =2,160 s**, leaving840s before the new hard stop. This author report is in B200 context; H200 boot remains unmeasured.

| Component | Seconds |
|---|---:|
| Weight staging and verification | 3,600 |
| Archive/environment staging | 900 |
| Author-reported TP8 boot | 2,040 |
| Frozen50 smoke and statistics | 120 |
| 14,184 block51 captures | 1,633 |
| Capture pull, CPU probes, W-lens commit and GO wait | 600 |
| 6,804 test readouts after GO | 840 |
| Transitions, seal/retrieval/release | 120 |
| **Total** | **9,853** |

Capture/readout durations retain the prior B200-derived planning allowances, with no TP8 speedup credited. They are not measured H200 upper bounds. All staging allowances are budgeted in full; one engine lifetime is assumed.

[Runpod's public H200 page](https://www.runpod.io/gpu-models/h200), checked27October2026, lists Community $3.59/GPU-hour and Secure $5.29/GPU-hour. For eight GPUs plus the existing **$2 unquoted extra-cost allowance**:

| Scenario | Replica/hour | Forecast | ×1.25 | $120 result |
|---|---:|---:|---:|---|
| Community list | $28.72 | $80.6050 | **$100.7563** | Planning fit only |
| Secure list | $42.32 | $117.8275 | **$147.2844** | NO_FIT |

Neither is an allocatable eight-GPU quote or stock verification. At these durations/extras the maximum replica rate is **$34.3449/hour** ($4.2931/GPU-hour). If boot plus smoke consumes the full3,000s, padded scenarios become **$109.1330 Community / $159.6277 Secure**, holding other estimates fixed. Actual quote/extras, measured timing updates and I-2's shared USD240 reserve reconciliation govern admission.

**CPU validation:**55tests pass (50 exact-archive +5 local CPU handoff), including TP8 3,000s/$120 boundary tests and TP4 1,200s/$100 regressions. The I-2 archive validator passes. Author code, fixture/data/asset bytes, greedy generation and agreement/grammar scoring are unchanged. `CLARIFICATION7_CPU_REVIEW.json` records the exact comparison. An initial boundary-test failure exposed a local variable-name collision in clock validation; it was corrected before successful final packaging.

The v6 and v6-c7 H200 templates now bind this archive's source seal, the full clarification7 authority, and `H200_FORECAST.json` with boot2040/smoke120/capture1633/readouts840. They remain deliberately unadmitted: allocation, actual quote/extras, provider stop and environment attestations are null/false. Set the actual request deadline no later than science start +3,000s; no reset. Clarification6's Wed06CET/no-B200-claim/single-node gate remains. No GPU, model transfer, native output, allocation or judging occurred. Smoke failure stops; no retries or retuning; capture and actual W-lens commit precede GO/readouts.
