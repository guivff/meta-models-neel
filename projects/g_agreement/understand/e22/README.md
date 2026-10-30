# E22 layer-wise Oracle activation patching

Exploratory §114 at `e71d1eeb`, preserved verbatim in
`results/g_agreement/understand/e22/REGISTRATION.md`; E22 supersedes E19 as the
causal test. Five rows × 84 test items, identical to the frozen E19 population.
No score or direction selection occurs. W1 asked phrasing pairs and E15 native
continuation pairs are unchanged. Sentiment is asked-only.

## Residual convention and scoring

E22 layer L is the **input to decoder block L**, before that block mixes token
positions. This follows §114's explicit layer-0 injected-activation swap and
differs from E19's block-output steering convention. For the pinned 64-block
reader the grid is `0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,63`.
The two positions are the activation marker and the final prompt token. The
latter is the end of the native carrier for asked scoring and the final token
of the separately tokenized `- ` prefix for continuation scoring.

Exactly one residual is replaced per candidate sequence at the selected block
input. Other tokens, candidate tokens, padding, masks and all other hook sites
are untouched at the edit point; subsequent propagation is allowed. Full
teacher-forced scoring uses the original summed candidate-token log likelihoods,
A minus B, averaged over W1 phrasing pairs or E15's frozen dev-valid pairs.
Both original pair scores are retained. No truncation, sign fitting, generation,
renormalization or cross-forward attention/recurrent state reuse is applied.
Every forward has `use_cache=False`.

## Donors and matching baselines

One PCG64 stream is seeded 20261025. Iterate sorted row and recipient IDs, draw
an opposite-value donor then a same-value nonself donor from sorted eligible IDs
within the same test row. Sampling is with replacement across recipients.
Source labels are verified through the sealed E19→E3 lineage before use. They
choose the registered donors only and remain in an analysis-only sidecar outside
the worker package. Unit tests check relations, balance, draw order and invariance
to input ordering. Donor identities are frozen before scoring.

For each row/prompt, capture three 84-item runs: recipients, opposite donors in
recipient order, and same-value donors in recipient order. Each run caches both
positions at all 17 grid layers on CPU. This preserves identical 16/4-item batch
boundaries, A/B candidate pairing and donor order between full-swap baselines
and patched forwards. BF16 batch effects therefore do not contaminate the
full-swap denominator. At most one row/prompt's three-capture bundle is needed
in RAM (about 669 MiB of float32 residuals for two candidate pairs and width5120).
Captures are reused across all patches; no donor forward per patch is needed.
Only scores and metadata are retained in output baselines, not the temporary
CPU residual cache. Scalar outputs suffice for the registered analysis.

The CPU hook tests include exact layer-0 injection equivalence to full activation
swaps for both native prefixes, multiple batch sizes and the four-item tail.
On the pod a calibration check repeats exact per-pair equality on the first four
frozen-order recipients in every row/prompt and both donor arms. Each production
layer-0 injection patch also must exactly match its corresponding full-swap
baseline. A mismatch seals INCOMPLETE; there is no tolerance adjustment or retry.

## Measurements and interpretation

For each expected item/cell retain recipient, donor and patched scores, each
pair's scores, donor ID and template cluster. Recovery is the per-item ratio
`(patched - recipient) / (donor - recipient)`, averaged across items; signing
both differences toward the donor value cancels in the ratio. Keep both raw
A-minus-B change and donor-signed change. Use 2,000 W1 template-cluster bootstrap
resamples, seed20261025. Ratios are not clipped or stabilized with an epsilon.
Zero denominators are explicitly undefined: retain numerator/denominator and
counts, and mark a complete-population mean/CI not evaluable if any item is
undefined or missing. Near-zero finite denominators stay in the analysis and
are reported as a limitation. No items are silently removed.

Report every cell and control, including layers/positions that do not support
the predictions. The registered >=0.50 recovery criterion is shown directly.
The brief supplies no numerical early/mid/late boundaries or sampling axis for
the same-value control's 95th percentile; do not invent a binary classification.
Expose full curves and per-cell empirical signed-item control q95 descriptively.
These are exploratory observations, not a new significance or multiple-testing
rule. Sentiment continuation is N/A by §114.

## Integrator launch

Use `/weights/venv-kernels/bin/python`; one pinned Oracle model/adapter load.
Setup is 1,500s. Science starts at the first warm-up, continuously, with cap
`min(1.5F+360,7200)` seconds. There are nine row/prompt combinations, 27 baseline
captures, 3,672 patch batches and 51,408 patch records, covering every item,
layer, position and both donor arms.

For each row/prompt, discard one full capture-bundle/patch warm-up, retain the
swap-equivalence receipts, and time three full three-capture bundles plus three
16-item patches at the last layer/preanswer position. Each timing includes CPU
transfer, serialization, fsync and hashing. Sum median bundle time once per
row/prompt plus median patch time times all its production batches. All warm-up,
parity and calibration elapsed time counts; admit only when consumed time + F
fits the cap. No production subset or scope cut if the forecast fails. Fresh
production baselines follow the gate; calibration values never enter analysis.
Output is sealed once, with partial outputs retained on failure. External hard
stop, exact pod ID and source/input hashes are mandatory. Final seal custody is
included in the elapsed ledger; any overrun is reported explicitly.

The integrator pushes commits and operates pods. Stage only the sealed worker
input folder; never stage or commit the private label sidecar. Use a fresh output
folder. No implicit resume or retry. E19 inputs, directions and outputs remain
unchanged.
