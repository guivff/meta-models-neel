# E35 implementation readings — 2026-10-25

Recorded after §131 clarification 1 at `ff48f19a`, before this worker opens the
gate rerun result, selects a latent, obtains a label, or computes a decomposition
score. The earlier `HOLD_2026-10-25.md` remains history; the clarification answers
that question. No registered row, threshold, rule or measure is changed here.

The clarified formula uses nonnegative encoder values and decoder-column norms;
decoder bias and cross terms never enter it. Direct error encodings are primary.
Positive differences of encodings are reported separately, without R1/R2 or a
second inferential analysis. Each ratio uses the intersection of defined error
and baseline shares, so its exclusion count is the union of their zero-code
items. Both marginal counts and the paired exclusion count are retained.

The clustered bootstrap samples whole nonempty row clusters with replacement,
retaining their paired items and recomputing the ratio of pooled item means.
The seed, 10,000 draws, percentile CI and strict lower-bound condition are fixed
in code. An undefined baseline or bootstrap ratio is recorded as undefined;
the code does not discard such draws or replace an undefined CI. More than 10%
exclusions is an uninterpretable rule, not a negative result. Exactly 10% is
permitted by the clarification.

Frequency is the number of strictly positive dev h-code activations. Exact
integer-frequency matching implements the requested match without selecting bin
widths: shuffle structure membership within each frequency stratum of the full
dictionary, preserving the number of structure labels in every stratum. Use the
same 100 seeded masks for both terms. Degenerate strata remain unchanged; report
unique masks and draws equal to the observed mask instead of relaxing matching.

“Most active” means highest mean activation across all 2,100 dev items, including
zeros. Select exactly 300 with latent-index tie breaking. Contexts come from all
positions of §79 training documents, excluding held-out source groups; rank
positive activations and resolve ties by document ID and position. Context
windows, strict 20-context completeness, blinding and label format are specified
in `LATENT_RUBRIC.20261025.md`. The labels, not test activations, define S.

For the descriptive code probes, use the existing W1 logistic-library recipe
with dev-only normalization and fitting, then test AUROC, on all three primary
codes and all 25 rows. The same frozen first-value-positive polarity is used for
each term. No tuning, test-fold fitting, extra rule or probe CI is introduced.
Named policy-loss latents are the top ten among the 300 already labelled latents,
ranked by mean decoder-weighted activation on each registered state row. Their
displayed contexts are the same pre-test corpus contexts used for labelling.

Preparation authorization checks a valid gate PASS and committed rubric/source
freeze. Full decomposition authorization additionally checks completed blinded
labels. This separates dev selection from decomposition without a circular label
dependency. The CPU analysis checks seals and metadata before its global
run-once guard; it consumes that guard before numerical code reads. A later
output name cannot bypass it. A scientific validity failure does not permit a
retry. No producer or GPU launch is implied by this implementation freeze.

Current operations use §135's 12-pod ceiling and three-minute spacing under the
Integrator's lock. E35's total remains at most 21,600 GPU-seconds, including
failed attempts, setup and retrieval. The prior 434.2 seconds and the gate rerun
must be booked before a later request. The FineWeb revision was committed in
`b1b2e33` (rebased from `817b8d2`) before this worker opens any gate rerun result. Conditional training,
if required, still needs its own bounded request and cannot follow an
operational or incomplete gate result.
