# E94 reader agreement

CPU only; no new readouts or judgments. Conditional precision excludes both-no-mention agreements. All comparisons use the same common-parseable items; missing and unmatched counts are in RESULTS.json. E67 is a separate claim diagnostic, not shared-value agreement.

| Bank | Paired n | Agreement | Correct given decisive agreement | Ensemble coverage | Oracle accuracy | NLA accuracy |
|---|---:|---:|---:|---:|---:|---:|
| E56 | 1091 | 0.6508 | 0.9672 | 0.2236 | 0.4262 | 0.3089 |
| E57 | 1641 | 0.7556 | 0.9261 | 0.1402 | 0.2072 | 0.2267 |
| E59 | 480 | 0.7875 | 0.9390 | 0.6833 | 0.7333 | 0.7250 |
| E62 | 0 | N/E | N/E | N/E | N/E | N/E |
| E67_wave1 | 598 | 0.5870 | 0.0085 | 0.5870 | 0.3261 | 0.0368 |
| E67_wave2 | 400 | 0.6550 | 0.0191 | 0.6550 | 0.2475 | 0.0375 |
| E73 | 1101 | 0.6776 | 0.9347 | 0.1807 | 0.2589 | 0.3015 |
| POOLED value-grounded | 4313 | 0.7127 | 0.9421 | 0.2321 | 0.3343 | 0.3220 |

H-A1 (pre-stated hypothesis, not a decision rule): **MET**, difference 0.6077198942953638; descriptive paired cluster-bootstrap 95% CI [0.5897563454891208, 0.6259484247789372].

Unavailable paired banks:
- E62: Oracle-only native acquisition; no shared Oracle/NLA judged item grid.
- E76: No sealed judged analysis/terminal delivered at source freeze; registered placebo agreement NOT EVALUABLE.

Per-bank/stratum confusion matrices, who is right on disagreements, reader precision/coverage, Wilson intervals and denominator audits are in RESULTS.json. Provisional scoring conventions and the incompatible E67 rubric are documented in METHOD.20261028.md. No sealed bank verdict is modified.
