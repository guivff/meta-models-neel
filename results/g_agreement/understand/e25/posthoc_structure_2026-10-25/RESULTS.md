# E25 post-hoc structure-only correlations — 2026-10-25

**Post-hoc and descriptive**, requested after the registered results. All 16 frozen structure rows are included.

D is the conventional fixed A-minus-B AUROC. Source values retain full precision from the sealed E25 summary.

| Outcome correlated with D | Spearman rho | 95% row-bootstrap CI |
|---|---:|---:|
| Oracle asked | 0.3588 | [-0.1742, 0.7092] |
| NLA asked | 0.3353 | [-0.3155, 0.7538] |
| NLA minus Oracle asked | 0.0118 | [-0.5901, 0.5620] |

The third row correlates D with the within-row difference **NLA asked AUROC minus Oracle asked AUROC**; it is not a difference between two correlation coefficients.

Intervals use 2,000 resamples of 16 rows (seed 20261025), with the same draws preserving all within-row pairings. Average ranks handle ties. Undefined draws are counted in METRICS.json; none are replaced.

Post-hoc association among 16 row point estimates; row bootstrap omits item-level uncertainty in D and reader AUROCs. No confirmatory verdict or causal interpretation.

The registered RESULTS.md, SUMMARY.json, analysis code, scores and seals remain unchanged. No registered bootstrap, model call, GPU work, API call or E27 analysis was rerun.
