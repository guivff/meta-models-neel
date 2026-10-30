# §83: error-driven CPU screen

**The registered feature-effect comparison is not estimable in this frozen pool.** All 138 scripted features are constant (or uniformly inapplicable) across the 40 reconstructed read-site prefixes. There are no feature slopes to compare between Oracle and NLA. The fitted models below reduce to intercepts and a pooled cohort indicator; they do not test the prediction. This is not evidence of no relationship.

Frozen pool: 875 judged units, 40 document clusters. Feature source `dc0e1316`; 0 GPU-h and $0 API.

| Pool | Reader | Units | Documents | Wrong | Parameters | Status |
|---|---|---:|---:|---:|---:|---|
| pooled | oracle | 423 | 39 | 179 | 2 | ESTIMATED_DESCRIPTIVE |
| pooled | nla | 452 | 40 | 249 | 2 | ESTIMATED_DESCRIPTIVE |
| SA-R | oracle | 366 | 20 | 162 | 1 | ESTIMATED_DESCRIPTIVE |
| SA-R | nla | 374 | 20 | 222 | 1 | ESTIMATED_DESCRIPTIVE |
| S61 | oracle | 57 | 19 | 17 | 1 | ESTIMATED_DESCRIPTIVE |
| S61 | nla | 78 | 20 | 27 | 1 | ESTIMATED_DESCRIPTIVE |

All coefficients and document-clustered 95% intervals are in RESULTS.json. Constants and exact aliases are listed there. These are descriptive associations, not a confirmation that a feature class causes errors or harms Oracle more than NLA.

## Limitations

- Authored natural-language prompts only: domain is constant prose, so no cross-domain adjustment can be estimated.
- Only 40 source documents; repeated concept/evidence units do not create independent documents.
- SA-R misses and S61 unfounded evidence are different endpoints: cohort-adjusted pooled fit and separate fits both reported.
- Exact aliases and constants removed without outcomes; coefficients depend on retained basis and are not independent feature discoveries.
- No multiple-comparison correction or confirmatory reader superiority claim.
- S65B unavailable at the prospective pool freeze; excluded rather than treating missing senses as correct or wrong.
