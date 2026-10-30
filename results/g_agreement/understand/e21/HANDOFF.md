E21 is complete and analysed once; do not rerun or relaunch.

2026-10-25T07:30:15.485563+01:00 E21 registered CPU analysis COMPLETE ONCE, pod0ys021u7gwhb8d. Full source/input/collection/whitener seals verified. Wall9.074124s,0GPU/API. Primary threshold NOT MET:rho=0.477435,CI[0.135572,0.739861],below0.50;rho falsifier<=0.20 also not met. All25rows, raw primary/dev probes/verified whitened secondaries reported. Analysis sealc10bfbadd3fcf9aa1c1585fcfeef9418fabc57811bbdde213e9d7cd831e39e26. No result edits/recomputation; do not rerun.

Report: `analysis/RESULTS.md`; seal: `analysis/SCORE_SEAL.json`; exact command: `analysis/ANALYSIS_RUN.json`.

Historical launch handoff follows.

---

E21 reward audit is built for §113, with the pre-score clarification `6a2b114e`.

The primary is raw block-44 cosine fidelity to each recipient activation. For each item,
compare its true and opposite descriptions, averaging cosines over both frozen W1 Oracle
phrasing pairs. Exhibits use both frozen E15 variants on all eight available rows, including
any pair that failed E15 validity; the other17 rows use the exact sealed E1b greedy16-token
continuation versus a seeded opposite-value test donor. Every text is passed separately to
AR with no deduplication, rewriting, prefix addition, stripping or generation. Descriptions
retain their original W1 `- ` prefix; E15 exhibits retain their exact whitespace.

Row rewards are fractions of positive true-minus-opposite cosine contrasts, exact ties
weighted0.5 (the user's “same” rule for exhibits). Cosine is computed before averaging
variants. All25 rows,84 test items per row, remain in the primary Spearman test against
W1's original Oracle asked AUROC. Threshold rho>=0.50 and CI lower>0;2000 row resamples,
seed20261025. Row rewards use2000 recipient-item resamples, keeping both arms/variants
paired. Constant Spearman resamples are counted explicitly; undefined point is not evaluable.
Secondaries and registered falsifiers are reported without adding a row-count threshold.

Dev probes fit only the84 dev reconstructions of real next16 tokens for each row, using
W1 library logistic defaults (dev-only standardization, L2lambda.001,200 LBFGS iterations).
Description AUROC signs the mean variant score toward each item's own truth before comparing
true versus opposite. Exhibit probe AUROC preserves §113's original across-true-state
metric (A-positive score). There is no test-based fitting, sign flip or phrasing choice.

The E1b official AR loader and reconstruct function are reused unchanged. Official source
`a32590085a6070d75f950155d3c2b3db3eec97ef`, verified moments SHA
`178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a`,ridge.1.
AR outputs stay raw. During setup, the official whitener's mu/w are checked against its
whiten method and exported. The optional whitened cosine secondary is computed after pull
on CPU with the identical transform on AR and h; unavailable/invalid transforms are reported,
never substituted. Neither whitened values nor probe scores affect the primary.

Frozen workload:2100 dev-real reconstructions,8400 description reconstructions,2688 E15
exhibits,2856 real-continuation exhibits:16044 total,2006 batch8 units. No new target capture,
lens generation, target generation, NLA or decoder load. W1 vectors and all4200 E1b real
continuations are already sealed. Input audit independently checks all16044 texts,2100
activation vectors,donor draws,split boundaries and timing coverage.

The integrator stages pinned model/AR assets and the existing official checkout/whitener.
Only AR loads, once during setup, in the same process/object as warm-up and science.
Setup1500s; first timed pilot starts the immutable science clock. Every one of four paths
gets one discarded setup warm-up and three timed discarded full batches. Timing-only dev
copies append neutral text as necessary to cover that path's longest production input;
these copies are never probe training or test inputs. F=sum(Nunits*median3) + all12 timed
pilot durations. Unknown paths are never zero. Admit only if full forecast plus180s retrieval
fits min(1.5F+360,2400,reserved). Every production batch is guarded and saved; partial output
is sealed INCOMPLETE, with no automatic retry. Actual F is pending the real warmed pilot.

After a COMPLETE pull, use POST_PULL.json once. It verifies the entire grid/seals before
private labels, writes RESULTS.md and metrics with all primary and secondary rows, and seals
results. W2/S2 and all previously analysed experiments remain untouched. This build used
CPU checks only and has produced no E21 scientific outputs.
