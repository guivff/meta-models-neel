# E115b — agreement × J-fraction (descriptive)

Full original E94 baseline:943/1001 correct decisive agreement reports, precision94.2058%, coverage1001/4313=23.2089%.

Dev-decile bindings available for39native E56/E57/E59 rows,3176common-parseable paired items. The other1137paired units remain NOT EVALUABLE for this gate:36E56injection controls and1101E73items. E73 delivered J bundles contain test records only; no test-derived thresholds or invented dev split. Full-E94 gain is NOT EVALUABLE.

On the evaluable subset, agreement alone has precision732/777=94.2085% at24.4647%coverage. Every combined gate reduces both precision and coverage here; **no gain on this subset**. This is not a full-E94 no-gain conclusion.

| Dev quantile cutpoint | Precision | Coverage | Precision 95% CI | Coverage 95% CI |
|---|---:|---:|---|---|
| Agreement alone | 94.208% | 24.465% | [92.639%, 95.613%] | [23.331%, 25.724%] |
| 0.1 | 92.440% | 18.325% | [90.385%, 94.378%] | [17.191%, 19.553%] |
| 0.2 | 91.511% | 15.208% | [89.183%, 93.713%] | [14.106%, 16.342%] |
| 0.3 | 92.774% | 13.508% | [90.464%, 94.962%] | [12.500%, 14.610%] |
| 0.4 | 91.781% | 11.492% | [89.071%, 94.286%] | [10.485%, 12.500%] |
| 0.5 | 90.141% | 8.942% | [86.805%, 93.421%] | [8.029%, 9.856%] |
| 0.6 | 90.090% | 6.990% | [86.222%, 93.778%] | [6.171%, 7.809%] |
| 0.7 | 89.412% | 5.353% | [84.736%, 93.865%] | [4.628%, 6.077%] |
| 0.8 | 86.555% | 3.747% | [80.357%, 92.383%] | [3.117%, 4.377%] |
| 0.9 | 92.754% | 2.173% | [85.878%, 98.438%] | [1.700%, 2.676%] |

All39within-row curves and frozen threshold hashes are in RESULTS.json. Thresholds are the nine original-dev decile cutpoints0.1..0.9, persisted before E94 item classes opened; strict fraction>tau. E80c frozen J384/original518mean, no basis/centering/probe refit. Bootstrap2000seed20261029 resamples original source-item clusters within row, keeping row strata fixed. Undefined precision remains missing.

Committed adapter/inputplanad3623111 before exclusivePART_B_ONCE. CPU0.578852s/GPU0; separate from sealed E115a, which was not replayed. R-5 independent review pending.
