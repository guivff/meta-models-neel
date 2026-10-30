# E107 strict-evidence exclusion companion

Descriptive, post hoc, authorized by 5d5baf921 and ac281d58c. Completed once; primary unchanged.

| Oracle R-OL1 | Difference | 95% CI |
|---|---:|---|
| Primary (copied) | 0.335342 | [0.213279, 0.459584] |
| 31-cell exclusion companion | 0.335342 | [0.213279, 0.459584] |

Exactly 31 strict word-for-word failures under binding v5: 29 E81 and two E86. No E82 failures, so the R-OL1 cohort is unchanged. Mask only affected reader/target cells; preserve paired source census and original missingness rules. Full E81/E86 comparisons are in RESULTS.json.

## Per-row conditional differences: belief-wrong cohort

| Row | Reader vs outside | Difference | 95% CI |
|---|---|---:|---|
| knowledge_cutoff | oracle | 0.074634 | [-0.077102, 0.222646] |
| wrong_bridge | oracle | 0.763492 | [0.520824, 0.977778] |
| knowledge_cutoff | nla | -0.553571 | NA |
| wrong_bridge | nla | 0.683660 | [0.428571, 0.900000] |

## Counts and unconditional rates

All E82 rows/cohorts, both readers and outside baseline; original grouped judgments retained. Belief/truth overlap is explicit in Both. For known truth: belief + truth − both + other + no-value + missing = planned. Missing includes incomplete original target judgments. Other means a named value matching neither available target. In no-canonical-truth, truth and both are unavailable, not zero.

| Cohort | Row | Reader | Planned | Belief | Truth | Other | No-value | Missing | Both | Belief / observed |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| belief_wrong | knowledge_cutoff | oracle | 99 | 49 | 29 | 8 | 11 | 10 | 8 | 49/89 (55.056%) |
| belief_wrong | knowledge_cutoff | nla | 99 | 0 | 0 | 1 | 97 | 1 | 0 | 0/98 (0.000%) |
| belief_wrong | knowledge_cutoff | outside | 99 | 31 | 26 | 0 | 30 | 13 | 1 | 31/86 (36.047%) |
| no_canonical_truth | knowledge_cutoff | oracle | 10 | 7 | NA | 0 | 1 | 2 | NA | 7/8 (87.500%) |
| no_canonical_truth | knowledge_cutoff | nla | 10 | 1 | NA | 0 | 9 | 0 | NA | 1/10 (10.000%) |
| no_canonical_truth | knowledge_cutoff | outside | 10 | 5 | NA | 0 | 2 | 3 | NA | 5/7 (71.429%) |
| belief_wrong | wrong_bridge | oracle | 100 | 11 | 3 | 0 | 84 | 2 | 0 | 11/98 (11.224%) |
| belief_wrong | wrong_bridge | nla | 100 | 12 | 6 | 0 | 82 | 1 | 1 | 12/99 (12.121%) |
| belief_wrong | wrong_bridge | outside | 100 | 1 | 44 | 0 | 4 | 51 | 0 | 1/49 (2.041%) |

The pooled conditional advantage is driven by wrong_bridge, where naming rates and missingness differ substantially. On knowledge_cutoff the conditional interval includes zero. The exclusion check does not resolve these interpretation limits. Shared model family between describer and judge is a confound of unknown direction; the earlier “conservative” claim is withdrawn.

Companion seal `5e8a95607380be024dd2e686acddaec87f94bd243190aa459a2c1d22aa905a9f`. Primary seal `f2da69a4f0e7acb560552cb9bee8c56ea8012a926a9508303113a2d3ccdd93b8`. Original paired source-item bootstrap: 5000 draws, seed 0. Private exclusions/binding stay CPU-local; hashes retained in seal. Source committed acd008859 before invocation, published354214f1a. Eight synthetic tests passed. No primary rerun or guard reset.
