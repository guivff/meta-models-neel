# E31(i) — dated interpretation, 2026-10-25

The two rows with both strata evaluable meet the registered remote-state point
pattern, and neither meets the registered local-cue point pattern. This is a
two-row comparison, not an all-seven-row confirmation of a remote-state account.

- `python_string`: informative n=30, AUROC 1.000 [1.000,1.000]; uninformative
  n=54, 0.908 [0.824,0.974]. The informative-minus-uninformative difference is
  0.092 [0.026,0.176]. The higher-confidence local-cue stratum performs better,
  but continuation discrimination remains strong in the lower-confidence stratum.
- `python_depth`: informative n=54, AUROC 0.822 [0.700,0.929]; uninformative
  n=30, 0.810 [0.641,0.942]. Difference 0.012 [−0.179,0.211]. Both point estimates
  exceed 0.70; the difference is imprecise.

The remaining five rows have no informative test items under the frozen dev
cutoff. Four have zero dev-median confidence margin (`prose_paren`, `prose_quote`,
`python_indent`, `list_depth`), and their test margins remain at the cutoff.
`table_role` has a nonzero dev cutoff, but no test item exceeds it. No cutoff or
tie rule was changed after observing these counts. Their uninformative AUROCs
are still reported: 0.713, 0.797, 0.782, 0.318 and 0.817 respectively; the two-stratum
predictions are not evaluable for these rows.

“Uninformative” is the operational label for confidence at or below the median
dev margin of this fixed character n-gram classifier. It is not a proof that the
last four tokens contain no usable information for every possible decoder.
Likewise, the observational split does not isolate a causal remote-state effect.
The registered comparison supports continuation discrimination surviving this
particular local-cue confidence split in the two evaluable rows.

All intervals use the requested 2,000 IID item resamples within fixed strata.
They condition on the trained dev classifier and cutoff and do not include model
fitting uncertainty or the test template-cluster dependence accounted for in E15's
original intervals. They are unadjusted descriptive intervals. All 2,000 draws
are finite for each of the nine evaluable strata; the five empty strata have no
AUROC or bootstrap interval.

The complete original E15 point estimates were independently reproduced in 21
checks before interpretation. E15's original validity mask, score orientation,
token-summed likelihood definition, outcomes and registered analysis remain
unchanged. E29's reader hold also remains in place. No GPU/API call, new reader
score or E31(ii) run was made.
