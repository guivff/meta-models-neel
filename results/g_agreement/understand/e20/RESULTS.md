# E20: registered horizon test

**Prediction did not hold on any primary row.** All four dev validity gates passed; the registered CPU analysis ran once on the complete sealed output from `jm1vm4gw487fhn`.

Near averages scores at distances2/4/8; far averages32/48, before computing AUROC.

| Row | Generation near | Far | Difference [95% CI] | Holm p | Verdict |
|---|---:|---:|---|---:|---|
| prose_paren | 0.506 | 0.557 | -0.050 [-0.106, +0.000] | 0.9705 | DID NOT HOLD |
| python_string | 0.474 | 0.467 | +0.007 [-0.050, +0.067] | 0.8396 | DID NOT HOLD |
| fact_once | 0.616 | 0.500 | +0.116 [+0.054, +0.181] | 0.0030 | DID NOT HOLD |

- **Paren:** source-probe flatness passes, but base expectation drops only0.067 rather than≥0.30; lens generation does not drop.
- **String:** base expectation drops only0.006; source-probe flatness fails (difference0.128). Lens generation stays near chance.
- **Fact:** significant generation drop0.116, below the required0.15; far source-probe AUROC0.656, below0.80. A significant difference alone does not satisfy the prediction.
- **Sentiment control fails:** far consequence AUROC0.584 [0.551,0.622], below≥0.80 with CI lower≥0.70. Accordingly, channel4 results for the other rows are **not interpretable**; channel3 results stand.

These failures do not establish a general absence of horizon effects: the structural base-expectation manipulation and several source-retention checks failed. No thresholds, signs, probes or samples were changed.

Full per-distance/band estimates, asked scores, random/opposite donor controls and criteria are in `analysis_jm1vm4gw487fhn/metrics.json`. Inference uses2000 paired-item bootstrap resamples, seed20261025, and Holm across three primary rows.

Validation: 224 AUROC point estimates independently matched sklearn without rerunning probes or bootstrap analysis.
