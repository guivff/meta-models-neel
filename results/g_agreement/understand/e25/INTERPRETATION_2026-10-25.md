# 2026-10-25 — E25 registered result and interpretation

**The prediction did not hold.** The once-only §119 analysis used all 8,400
sealed candidate scores for all 2,100 items and 25 rows, with conventional D
as clarified in e4225a1e. No score, input, phrasing, source or decision changed.
RESULTS.md is an exact copy of the canonical sealed report in
`analysis_0jexpj58lbtuk9/`.

P, the median true-description log probability, has essentially no observed
association with the Oracle's W1 asked AUROC: Spearman rho = 0.0340,
95% row-bootstrap CI [-0.3992, 0.4663]. The registered alternative point condition
rho(P) < 0.30 holds. This result does not support the proposed continuation
plausibility account on these rows; the interval does not establish an exactly
zero association.

The content-minus-structure difference in median P is +0.1315 nats per token,
95% CI [-1.1880, 0.5118]. Thus the predicted positive class difference is also
unsupported. The content and structure medians are -5.4845 and -5.6160.

D, the base model's fixed A-minus-B discrimination AUROC, correlates with the
Oracle's asked AUROC at rho = 0.7516 [0.4982, 0.8775]. It also correlates with
NLA performance, rho = 0.7051 [0.3721, 0.8935]. The paired Oracle-minus-NLA
correlation difference is +0.0465 [-0.2020, 0.3042], so the observed association
is not established as specific to the Oracle. These are associations across
rows, not evidence for a causal mechanism or item-level predictive validity.

The probe correlations are P: 0.1289 [-0.1532, 0.4137], D: -0.1451
[-0.4750, 0.3179]. Probe performance is near ceiling: 27 of the 2,000 row draws
produce a constant probe reference and undefined correlations. Their intervals
and corresponding paired contrasts use the 1,973 finite draws; all counts are
retained in SUMMARY.json. No finite substitute, polarity flip or replacement
draw was used. Oracle and NLA correlations have 2,000 finite draws each.

The E21 rho = 0.48 remains a descriptive comparison only; no difference test
against it was registered or performed.

## Custody and execution

- Pulled/rebased first; Git recognized the integrator's cherry-picks 82145626
  and bd184e44 and skipped the equivalent old local commits.
- Pod: 0jexpj58lbtuk9. Score seal:
  `3a1d2ff1f418b0e85310c1bb5a2c15fb28aa579a58007ce0506e750384538d42`.
- Complete score seal, plan, source files, assignment, asset-manifest hash,
  private-label hash and W1-reference hash verified before analysis.
- The frozen analysis ran once with 2,000 row resamples, seed 20261025.
  Exclusive start/completion records are retained; bootstrap was not rerun.
- Acquisition receipt: setup 137.474 s; science 240.590 s; warmed F 242.408 s;
  science cap 723.613 s. These are the existing pod's recorded times, not new
  worker GPU use. This CPU analysis used no model, GPU or API calls.
- Canonical analysis seal:
  `996bbf532f046a0fa249f1cf80b44b9f114138e2c95daf4ddef20e1b8ef11b27`.

E27(a,b)'s already published report and all ten sealed files were reverified
unchanged. No E27 resampling, new swap, probe fit, or extension (c) was run.
