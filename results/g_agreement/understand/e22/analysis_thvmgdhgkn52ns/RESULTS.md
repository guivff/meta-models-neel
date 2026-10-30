Prediction: content asked effects recover at least 0.50 at early injection and late pre-answer positions; structure continuation effects recover at least 0.50 at a mid-layer pre-answer position; structure asked changes stay within the same-value control's 95th percentile.

The report leaves the qualitative pathway interpretations descriptive. It does not invent early/mid/late boundaries or a control-percentile decision axis.

Coverage: 51408/51408 patch records; capture status `{'error': None, 'experiment': 'E22', 'exploratory': True, 'status': 'COMPLETE'}`.
Undefined zero-denominator fractions: 0; numeric-overflow fractions: 0.

Every registered row, prompt, layer, position and donor arm appears in `cells.csv` and `summary.json`. Observed crossings of the registered 0.50 recovery threshold are listed separately without assigning layers to early/mid/late categories. Each fraction uses its own arm's full-donor baseline. Any missing or undefined item prevents a main fraction mean and CI for that cell; finite near-zero denominators are retained and their minimum magnitude is reported.

The layer-0 injection control is reported separately as exact patched-versus-full-donor score equality, including missing-item counts and maximum absolute differences. This check remains defined even when the normalized fraction has a zero denominator.

Per row/prompt/layer/position, empirical 95th percentile of same-value donor-signed per-item (patched - recipient) changes, NumPy linear interpolation; complete items required. Descriptive, not a hypothesis-test threshold or a bootstrap percentile of means.

Resample template clusters with replacement within each row; retain all member items. Reuse the same draws for every prompt/layer/position/arm in that row; row seed = seed + registered row index.

Raw paired changes and donor-label-signed changes are separate. The sign is fixed by frozen A/B labels, never fitted to score direction. Sentiment is asked-only. Raw recipient/full-donor/patched baselines remain in the hash-bound score source.

These exploratory curves do not establish a binary disconnected-pathway verdict.

Optional budget telemetry is recorded separately with its SHA256 and seal-coverage flag; it is not an independent provider audit.
