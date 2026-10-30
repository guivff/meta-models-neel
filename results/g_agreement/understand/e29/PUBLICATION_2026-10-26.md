# E29 W12 prospective publication — 26 October 2026

W12 D/P were computed once from the verified 2,016-cell score grid and posted in the W-text chat before mechanical prediction generation. No reader outcomes were opened. The sealed scorer, analyzer and prediction generator were not changed.

Freeze: `2833a20091db5e1e3b5548bf8d0e581b1fe23718989dc9e6e698da6eb767109f`.

| Row | D | P | D − Oracle ≥ 0.15 |
|---|---:|---:|---|
| syntax_role | 0.608844 | -4.526409 | Not triggered |
| sentence_type | 0.981293 | -5.369820 | Required |
| sentence_position | 0.009637 | -4.750970 | Not triggered |
| paragraph_index | 0.706349 | -4.921021 | Required |
| paragraph_start | 0.607710 | -4.420608 | Not triggered |
| clause_embedding | 0.700113 | -5.235847 | Required |

Oracle asked AUROC ≤0.65 is predicted for every row (all six frozen classes are structure). The additional D − Oracle ≥0.15 predicate is triggered only by the three rows above with D≥0.70, using full-precision D.

VALUES_SEAL: `ecac8379a09d429ae42013b2980a0fb927043309f51a84f730b3283430238bf7`.

PREDICTIONS_SEAL: `ca76c12ce6f1c9ffdf95097b7ac3ce3f62c0cfa9f7519941857bd467ed80f2ba`.

PREDICTIONS.json: `7a51171c8023d8a4ba73d19f97ef241e7a6318a289efa478bd19124362ff912c`.

Integrator/W-core: verify the exact freeze, posted D/P, VALUES_SEAL, frozen prediction-code seal and PREDICTIONS_SEAL before reader scoring. §136 requires no fresh coordinator ruling or post. This commit supplies the requested publication prerequisites. W-text has pushed nothing and launched nothing.
