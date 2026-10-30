# E19 probe-direction steering

Registration: §111 at `409690ee`, preserved verbatim in
`results/g_agreement/understand/e19/REGISTRATION.md`. Exploratory; report every
outcome. Oracle lens only, four state rows and the sentiment positive control.
No target recapture or generation is required. E3/E4 runtime code is unchanged.

Direction selection uses E3's logistic fitter, lambda .001, five grouped folds
(seed 20261024), on the 84 dev items only. The middle third is zero-based
`range(L//3, 2*L//3)`: blocks 21–41 for 64 layers. Select maximum dev grouped-CV
AUROC, ties to the lowest layer, then refit all dev items. Convert standardized
probe coefficients to raw coordinates before unit-normalizing. Sigma is sample
SD (`ddof=1`) of dev projections. No test residuals enter fitting and no test
labels are parsed. The frozen NPZ, selections, source hashes, and seal are
committed before any test forward. Runtime and request creation require their
bytes to match that commit and the same E3 input lineage.

At the chosen layer's output, add alpha*sigma*u only at the final head token
(preanswer) and true candidate answer tokens. No other carrier or padding token
is edited; no residual renormalization. Measure the row's own probe projection
at the following block, separately at preanswer and answer positions. Asked
scoring reproduces W1's two mean A-minus-B summed log-likelihood contrasts.
E15 continuation scoring uses its separate native `- ` prefix and original,
untruncated candidate token IDs. Its primary score averages the frozen
base-dev-valid pairs; every pair is retained descriptively.

**E15 scope gap:** E15 never registered a sentiment continuation pair. The
continuation endpoint is explicitly NOT_APPLICABLE for `prose_sentiment`; asked
and projection measures retain all five rows. No new wording is invented. All
four state rows have two valid frozen E15 pairs. This interpretation was exposed
before test; the optional clarification received no answer. A coordinator may
supply a separate ruling, but must not silently replace the frozen wording.

Controls: W7 isotropic equal-norm construction, seeds 20261025/26/27; sentiment
unit direction applied at each state row's selected layer; and the row's own
direction with a frozen same-row nonself random donor activation, seed 20261025.
Every control uses the recipient row's sigma, so requested edit norms match.
All 84 test items per row and alphas 0,-1,+1,-2,+2,-4,+4 are retained. Bootstrap
clusters are copied from frozen W1 item metadata without decoding truth fields.

Analysis reports paired changes against own alpha0, except donor steering uses
donor alpha0 and separately reports donor0-own0. Fit the signed OLS slope across
all seven doses. The registered pathway pattern is a nondecreasing mean asked
trajectory, positive slope, and own slope above the empirical 95th percentile
(linear interpolation) of the three random slopes, on at least three state rows.
The sparse random quantile is not a calibrated 95% hypothesis test. The
"disconnected" alternative remains descriptive: no new flatness or continuation
threshold is invented. Use 2,000 paired template-cluster bootstrap draws, seed
20261025 plus fixed row index; no orientation flips or tuning after test.

## Operations

The integrator pushes and operates the pod. Use `/weights/venv-kernels/bin/python` and
one pinned local Oracle model/adapter load. Setup allowance 1,500s; one continuous
science clock from the first warm-up, capped at min(1.5F+360,9,000)s. Per row,
one unscored full-batch warm-up then three timed alpha4 units include both
endpoints, projection transfer, serialization, fsync and hashing. The full
schedule has 1,218 units and 17,052 item-arm-dose records. No production runs
before the full gate, and no subset is substituted on NO-GO. Final CPU seal
custody remains charged in the budget ledger; cap overruns are reported. There
is no implicit resume or retry. External hard stop and exact RUNPOD_POD_ID binding
are mandatory.

The §111 operations ruling at `17942898` permits one relaunch after the first
attempt's timing NO_GO (F=4,885.8s for 1,218 units; empty sealed production
scores). Only the environment and science ceiling change; setup stays 1,500s.
All rows, items, doses, controls, analysis and frozen directions at `36bd59a9`
remain unchanged. If this warmed forecast does not fit, E19 closes INCOMPLETE;
there are no scope cuts or further retries. The original launch receipt is
preserved in git at `d1ec7ca2:results/g_agreement/understand/e19/LAUNCH_REQUEST.json`.

Only the sealed E19 inputs and committed dev direction freeze go to the pod.
After pull, use `python -m projects.g_agreement.understand.e19.report --scores
PULLED_OUTPUT --inputs E19_INPUTS --freeze COMMITTED_FREEZE --out NEW_RESULTS
--cache-out NEW_CACHE`. Scores and all input/freeze bindings verify before any
analysis. Detailed paired items and full raw outputs remain in ignored cache.
