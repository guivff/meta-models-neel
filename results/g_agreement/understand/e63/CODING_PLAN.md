# E63 coding freeze — §179, 491b3f85

CPU only. No scientific scores or placebo readouts opened in this preparation.
Implement the frozen value-word expressions exactly on every real native
readout and the random and shuffled placebo pools. Full sealed row inventory
must include E56, E57, E59 and E62 and bind each bank's completed once-only
analysis. The integrator provides the verified normalizer bundle described in
projects/g_agreement/readerbench/README.md. Missing rows/pulls do not consume
the analysis guard. Explicit ineligible rows remain visible; R-P1 applies only
to the authoritative REPORTED subset, with no reclassification by this scorer.

S_regex = (correct-only − wrong-only)/all readouts. Both/neither score zero.
N = either-value/all readouts. Assign placebo A/B with seed20261029 per vector,
shared across its four repeats. Process sorted vector IDs for reproducibility.
Both arms are reported separately against the same real row; R-P1 requires
delta≥0.20 and item-bootstrap lower bound>0 for each contrast. Do not select
the more favorable arm or invent a global rule beyond the registered row rule.
Bootstrap 2000 item/vector draws, seed20261027; independent real/placebo draws;
preserve all repeats, including empty or malformed outputs.

R-P2: uniformly sample 200 readouts per reader without replacement from its
combined two-arm pool, sorted source IDs before RNG seed20261027. Freeze and
seal the inventory before judging. D5 five-category rubric, actual E56 judge
route; no self-labeling, substitute judge or regex category fallback. Public
packet hides reader, arm, labels, IDs and repeat group. Private key stays in
ignored cache. Require sealed complete judgment grid before joining. Compare
TVD against the corresponding reader's sealed pooled MISSED distribution;
≤0.15 resembles placebo, ≥0.40 input-specific, intermediate otherwise. D5
currently supplies Oracle only; NLA reference remains an explicit dependency,
not permission to reuse Oracle or launch additional reader work.

Separate once-only guards for registered regex analysis and R-P2 judgment
aggregation allow the regex result to run while judgments are pending. Neither
has run. No GPU, reader generation, pod operations, push or scientific retry.

Credit: §179 placebo arm follows Thomas & Kylie's counterfactual-prediction
work (O-lens placebo).
