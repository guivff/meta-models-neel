# E75 Qwen — complete once, 2026-10-28

Sealed scorer d57f0f0c, unchanged SHA256 0a08e53407bf9f0769932da7567d7b5131ef9730a41586faedd441f9fc32b095. One claimed invocation with prespecified primary and redaction sensitivity panels. Input commit 6bd5c10f7573a677bf05cfd52c67a5b3a9bae6c0.

R-P1 NOT EVALUABLE: Oracle n=55 and NLA n=35, both below60. Positive category increments have95% intervals crossing zero, so incremental support is not established. GLM R-G2 NOT EVALUABLE (no J forecast), separate from Qwen.

| Panel | Reader | J units | J BA (95% CI) | Pre-outcome category units | J minus category, pp (95% CI) | Within-category BA / permutation p | J-null median /97.5th |
|---|---|---:|---|---:|---|---|---|
| primary | oracle | 55 | 79.24% (69.21–89.66) | 27 | +14.56 (-10.80–+38.89) | 77.04% / 0.01499 | 0.01847273 / 0.02464393 |
| primary | nla | 35 | 80.23% (66.67–92.31) | 27 | +22.53 (-1.67–+44.71) | 78.52% / 0.00799 | 0.01847273 / 0.02464393 |
| redaction_excluded_sensitivity | oracle | 55 | 79.24% (69.21–89.66) | 27 | +14.56 (-10.80–+38.89) | 77.04% / 0.01499 | 0.01847273 / 0.02464393 |
| redaction_excluded_sensitivity | nla | 35 | 80.23% (66.67–92.31) | 27 | +22.53 (-1.67–+44.71) | 78.52% / 0.00799 | 0.01847273 / 0.02464393 |

Primary uses all records retained by the original native scorer; sensitivity uses the sealed analysis excluding exactly6 main+2 control redactions. No truth labels change, so all forecast metrics are identical. No native analysis was rerun.

Category provenance: each reader has27 pre-outcome units (E56=13,E57=12,E73controls=2). Exploratory mechanical assignments add28 Oracle units (E59=5,E62=20,E73main=3) and8 NLA units (E59=5,E73main=3). Confirmatory category gaps above use only27 pre-outcome units; J BA uses all55/35. Four strata qualify for each pre-outcome within-category test;95th permutation cutoffs Oracle69.6296%, NLA69.1358%.

| Exploratory all-unit category comparison | Category BA | J minus category, pp (95% CI) | Within-category BA / p |
|---|---|---|---|
| oracle | 67.71% | +11.54 (-3.23–+27.22) | 76.49% / 0.00100 |
| nla | 68.95% | +11.27 (-8.66–+31.54) | 83.62% / 0.00400 |

The unchanged pure kernel labels tests with>=3 qualifying strata CONFIRMATORY; for all-unit panels that label is superseded by the user-required exploratory provenance designation. No confirmatory claim is made from new categories.

Registered exclusions: E57 five probe-failing binary rows per reader; E59 decline_plan per reader; E62 S5 allfive rungs via R-L0, allE62 NLA NOT RUN, all15E62 placebo cells per reader NOT RUN/NO_FIT; E73 W2/W3 per reader. All83 forecast binary identities×2readers accounted for:90 included,76 excluded. Nonbinary E57three andE62S6five preserved separately.

2000 paired row bootstraps;1000 within-category truth-label permutations; seed20261027. Common null uses200 directions,k16. Constant-REPORTED and constant-MISSED BA=.5. Full intervals, source hashes, category commit/seal chronology, exclusions and rows are in QWEN_RESULTS.json, QWEN_BOUND_UNITS.json and QWEN_RUN_PLAN.json.

No push, GO, model forward, pursuit or forecast rerun. Never repeat this analysis.
