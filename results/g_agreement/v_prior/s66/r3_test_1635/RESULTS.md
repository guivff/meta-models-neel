# §66 frozen R3 FVE-only test

Scope: activation dependence. All2,560 AR predictions verified; official CPU FVE and lengths sealed before independent context/typical-sense labels. No refit or selected threshold.

| Reader | Labelled (D / I) | FVE AUROC [95% CI] | Length AUROC | Gain [paired95% CI] | Verdict |
|---|---:|---|---|---|---|
| oracle | 1048 (1035 / 13) | 0.429431 [0.178226, 0.810686] | 0.437495 | -0.008064 [-0.529403, 0.789268] | **NOT MET** |
| nla | 1072 (1064 / 8) | 0.599624 [0.140222, 0.695948] | 0.223449 | 0.376175 [0.109178, 0.446033] | **NOT MET** |

Uncertainty:2,000 whole-word cluster bootstrap draws, seed20261023, paired draws for both scores. Raw token length is increasing, fixed before test. Counts, length CIs and missing/UNLABELLED reasons are in RESULTS.json. Specificity is **MISSING**; existing mapping has no specificity signal and no calls were made.

The scientific unit is the complete sealed readout text with the finest available closed-sense mapping. For MISMATCHED, context and own FVE use the actual source state, not the recipient. Opposite-context controls are matched on reader, arm, cue distance and sample index. A missing control mapping cannot prove absence. Negative FVE donors are the presealed8 disjoint probe_train states, distinct from the opposite-sense label controls.

§62 and §54-core: **NOT RUN**, no complete sealed AR coverage by compute stop. §65B reversion rates are not used as this test result.

Fresh run98vicmurr2bd0v: setup255.4s shared staging; science219.3s provider-clock (worker79.16s), booked once by integrator. Earlier charges retained. Full verified pull; payload deletion proved before STOP/EXITED. CPU only after pull; no new reader/judge/API/model calls by P3.

ROC.svg and THRESHOLDS.svg are descriptive; no threshold was selected. FEATURE_SEAL.json and LABEL_JOIN_SEAL.json bind ordering, source hashes and orientation.

Limitation: only13 Oracle and8 NLA independent examples. Each reader has263 single-class bootstrap draws excluded out of2,000, leaving1,737 valid; intervals use those evaluable draws. These sparse classes limit precision. NLA passes the gain criterion, but fails the AUROC>=0.75 criterion; Oracle fails both point criteria. Neither reader is CONFIRMED.
