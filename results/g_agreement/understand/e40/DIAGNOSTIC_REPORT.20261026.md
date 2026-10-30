# E40(a) CPU diagnostic — 2026-10-26

Descriptive analysis of the two sealed failed E35 SAEs. The E40 design remains as registered in §142 and clarification1. All 50,000 held-out tokens are included here; E40 exclusions are not retroactively applied.

FVU is centered within each stratum; dead fraction means never positive within that stratum, using the full dictionary. Norm deciles are equal-frequency rank bins of raw h norms; ties retain original token order. Marginal axes are separate, not crossed.

| Stratum | n | Transfer FVU | Transfer dead | Fallback FVU | Fallback dead |
| --- | ---: | ---: | ---: | ---: | ---: |
| all | 50000 | 0.410635 | 41.954% | 0.503148 | 10.925% |
| position:0 | 236 | 0.320772 | 99.298% | 0.442121 | 98.877% |
| position:1-7 | 1690 | 0.392267 | 82.159% | 0.510314 | 52.917% |
| position:8+ | 48074 | 0.435879 | 43.282% | 0.532437 | 11.536% |
| norm_decile:1 | 5000 | 0.484449 | 84.053% | 0.535160 | 51.617% |
| norm_decile:2 | 5000 | 0.497211 | 79.023% | 0.569088 | 42.877% |
| norm_decile:3 | 5000 | 0.489176 | 75.703% | 0.575468 | 37.854% |
| norm_decile:4 | 5000 | 0.476458 | 72.687% | 0.575284 | 33.417% |
| norm_decile:5 | 5000 | 0.463218 | 70.209% | 0.575326 | 30.341% |
| norm_decile:6 | 5000 | 0.452603 | 67.549% | 0.570908 | 28.149% |
| norm_decile:7 | 5000 | 0.438721 | 65.299% | 0.559637 | 27.325% |
| norm_decile:8 | 5000 | 0.428339 | 63.218% | 0.542700 | 27.814% |
| norm_decile:9 | 5000 | 0.414382 | 62.554% | 0.511913 | 29.822% |
| norm_decile:10 | 5000 | 0.293133 | 64.050% | 0.362006 | 35.431% |
| domain:latex | 10343 | 0.374926 | 67.888% | 0.589251 | 26.251% |
| domain:markdown | 25673 | 0.469489 | 67.001% | 0.528553 | 32.678% |
| domain:prose | 10333 | 0.406451 | 69.330% | 0.404907 | 44.464% |
| domain:python | 3651 | 0.454637 | 83.749% | 0.679826 | 46.698% |

The failures persist within the 48,074 position-8+ tokens: FVU 0.435879 for transfer and 0.532437 for fallback. Both exceed 0.25. This diagnostic does not test the new training-median outlier threshold and is not used to revise E40.

The original global dead counts are reproduced exactly. Global FVU absolute differences are 3.885780586188048e-16 (transfer) and 1.219221501536083e-09 (fallback). Transfer reconstruction bytes were reused; firing sets and fallback reconstructions were recomputed on CPU from checksum-verified checkpoints and the same sealed h.

The first invocation stopped at output-directory creation before strata were computed. Its guard is preserved. The single authorized operational rerun completed; see DIAGNOSTIC_OPERATIONAL_NOTE.20261026.json. CPU computation used no GPU time.
