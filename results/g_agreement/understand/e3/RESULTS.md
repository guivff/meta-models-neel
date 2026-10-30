Prediction: Oracle-lens structure information is present after injection and either decays through reader layers or remains decodable despite weak verbal output; NLA decays less.

Prediction assessment: Oracle representation-versus-verbalisation remains unresolved by probe AUROC alone. Oracle structure preanswer AUROC changed by +0.0450 from the first post-injection block to the last: no decline observed. On 15 matched structure rows, the NLA-decays-less prediction held descriptively (NLA change +0.4674, Oracle change +0.0450).

Reported 6144/6400 evaluable layer-position cells; all 75 requested reader×row entries retained.
The first post-injection block is Oracle 0 and NLA 1. NLA block 0 and embedding stages precede its injection and cannot locate information loss after injection.
W1 asked AUROCs use test items; internal grouped-CV AUROCs use all 168 dev+test items, so the side-by-side difference is descriptive. No threshold decision or mechanistic identification is imposed.
J-lens has no decoder residual stream or token positions. Its input and J_h are separately labelled native stages; no residual heatmap is fabricated.

| Reader | Class | Position | Input embedding | First post-injection mean | Last-layer mean | Change | W1 asked mean |
|---|---|---|---:|---:|---:|---:|---:|
| olens | count-like | injection | 1.000 | 1.000 | 1.000 | -0.000 | 0.509 |
| olens | count-like | preanswer | 0.500 | 0.968 | 0.968 | +0.000 | 0.509 |
| olens | semantic | injection | 1.000 | 1.000 | 1.000 | +0.000 | 0.952 |
| olens | semantic | preanswer | 0.500 | 0.932 | 0.987 | +0.055 | 0.952 |
| olens | state-like | injection | 0.994 | 0.994 | 0.994 | -0.000 | 0.558 |
| olens | state-like | preanswer | 0.500 | 0.858 | 0.955 | +0.096 | 0.558 |
| nla | count-like | injection | 0.500 | 1.000 | 0.987 | -0.013 | 0.695 |
| nla | count-like | preanswer | 0.500 | 0.500 | 0.988 | +0.488 | 0.695 |
| nla | semantic | injection | 0.500 | 1.000 | 1.000 | +0.000 | 0.986 |
| nla | semantic | preanswer | 0.500 | 0.500 | 0.976 | +0.476 | 0.986 |
| nla | state-like | injection | 0.500 | 0.984 | 0.958 | -0.026 | 0.809 |
| nla | state-like | preanswer | 0.500 | 0.500 | 0.945 | +0.445 | 0.809 |

All individual cells, including failures: `analysis_cybhnezi82omzz_rerun_f6cdf072/cells.csv`; full requested population: `analysis_cybhnezi82omzz_rerun_f6cdf072/rows.csv`; native stages: `analysis_cybhnezi82omzz_rerun_f6cdf072/named_stages.csv`.
Heatmaps use a fixed 0–1 AUROC scale; missing cells are grey. Class curves average rows equally.

§91 custody exception (4af1004b): these sealed arrays were lost during pull; affected cells are MISSING, never imputed:

- `olens/table_row.residuals.npy`
- `olens/table_status.input_stage.npy`
- `olens/table_status.residuals.npy`

Completed once more from scratch under §90 ruling `f6cdf072`, detached with persistent logs; exit 0 after 347.3 s. All 14 analysis-seal entries verify. The 40 interrupted caches were archived untouched and never reused. Code, probes, folds, rows and metrics were unchanged.

Exactly **258 cells are MISSING**: 256 layer-position cells plus two named input-stage cells. There are no other unevaluable analysis cells. All 75 reader×row entries remain represented; J-lens has no decoder layers, and its 50 native-stage cells completed.

The NLA first-post-injection preanswer state is still at chance (its injection occurs at block 1's output); later-layer increases include propagation to that position. The registered change comparison is descriptive and does not by itself establish a causal difference in information loss. High Oracle residual-probe AUROC establishes decodability, not that the reader uses that information in its answer. E4 is needed for sensitivity evidence.

All six missing pulled files (relative to pack-out), retained in the custody record:

| Missing file | Consequence |
|---|---|
| `e3/olens/table_row.residuals.npy` | MISSING: 128 layer-position cells. Available input-stage cells retained. |
| `e3/olens/table_status.residuals.npy` | MISSING: 128 layer-position cells. |
| `e3/olens/table_status.input_stage.npy` | MISSING: two input-stage cells. |
| `e4/RUN_STATUS.json` | MISSING E4 metadata; no E3 cells correspond to this file. |
| `e4/provenance.json` | MISSING E4 metadata; no E3 cells correspond to this file. |
| `e4/SCORE_SEAL.json` | MISSING E4 metadata; no E3 cells correspond to this file. |

`RERUN_VERIFICATION.json` records the successful run, seal hash, source hash and archive check. `DETACHED_PROGRESS.log` and `DETACHED_ANALYSIS.log` preserve execution logs. The original generated report, all cell CSVs and eight figures are under `analysis_cybhnezi82omzz_rerun_f6cdf072/`. Full 24.6 MB metrics with per-fold metadata and OOF predictions are retained in the ignored cache; the local metrics link preserves seal verification. E4's integrator-run retry and its receipt are unchanged.
