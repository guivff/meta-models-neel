Prediction: the Oracle reader's pathway exists but is under-weighted: monotonic asked movement with own-direction slope above the random-direction 95th percentile on at least three of four state rows.

The registered pathway prediction did not hold in the observed data.
Observed: 0/4 state rows; 0 not evaluable. This is exploratory.

| Row | Own asked slope | Random q95 | Monotonic | Registered pattern | Own continuation slope |
|---|---:|---:|---|---|---:|
| prose_paren | -0.014982 | 0.047483 | False | False | 0.002249 |
| python_string | 0.037527 | 0.10412 | False | False | -0.00079136 |
| table_role | -0.056044 | 0.022773 | False | False | 0.032606 |
| python_depth | 0.02284 | 0.038686 | True | False | 0.00089689 |
| prose_sentiment | 0.078556 | -0.029623 | False | False | NA |

Positive control (`prose_sentiment`): positive asked slope = True; seven-dose monotonicity = False. The content-control prediction is assessed separately from the four-state-row count.

**Random baseline:** Only three direction slopes: the 95th percentile is sparse and is not a calibrated 95% hypothesis test or a random-direction population bound.

The continuation endpoint is unavailable when E15 supplied no dev-valid pair. No sentiment continuation pair is invented. A disconnected-pathway interpretation remains descriptive: the report provides signed asked/random slopes and continuation changes without adding an unregistered movement threshold.

Score coverage: 17052/17052 records. Missing cells remain in the tables. Every paired change uses the same item at alpha zero; donor steering uses its donor-injected zero baseline, with donor replacement shown separately.

All four measures, all doses, and all control arms are in [cells.csv](analysis_a2txudaqw04nl4/cells.csv); curve slopes and 95% cluster-bootstrap intervals are in [summary.json](analysis_a2txudaqw04nl4/summary.json). Preanswer and answer projection changes measure whether the intervention reached the next layer. No sign was flipped.

Capture status: `{'error': None, 'experiment': 'E19', 'exploratory': True, 'status': 'COMPLETE'}`.

Custody telemetry is **not covered** by the primary score seal. Its copied contents and SHA256 are retained separately in [summary.json](analysis_a2txudaqw04nl4/summary.json); they are not an independent provider-custody audit.

The unchanged registered analysis ran exactly once on the relaunch output from `a2txudaqw04nl4`, detached with an exclusive lock. The first attempt was excluded and remains untouched. All 1,248 pulled files, 1,243 score-seal entries, three analysis-seal entries and the paired-item cache hash verify. No records are missing; sentiment continuation remains the preregistered N/A endpoint.

The intervention reached the next-layer residual stream in every row: both preanswer and answer projection trajectories increase monotonically. The table below copies the registered own-direction slopes and 95% template-cluster bootstrap intervals from the sealed summary (2,000 draws); no additional analysis or threshold was applied.

| Row | Asked slope [95% CI] | Continuation slope [95% CI] | Next-layer preanswer projection slope | Next-layer answer projection slope |
|---|---:|---:|---:|---:|
| prose_paren | -0.01498 [-0.09308, 0.05595] | 0.00225 [-0.00958, 0.01565] | 3.26569 | 3.01051 |
| python_string | 0.03753 [0.01886, 0.05566] | -0.00079 [-0.00924, 0.00815] | 5.44796 | 5.17588 |
| table_role | -0.05604 [-0.12959, 0.00416] | 0.03261 [0.01932, 0.05000] | 5.24754 | 5.03646 |
| python_depth | 0.02284 [0.01889, 0.02694] | 0.00090 [-0.00280, 0.00480] | 1.91992 | 1.83233 |
| prose_sentiment | 0.07856 [0.03069, 0.12130] | N/A | 4.69765 | 4.38397 |

Only `table_role` has an own-continuation slope with its bootstrap interval wholly above zero; its asked slope is negative. This is descriptive and does not establish the disconnected-pathway alternative. Sentiment has a positive asked slope and exceeds the empirical random q95, but fails strict seven-dose monotonicity. All random, content-direction and donor controls, dose-specific paired changes, and donor-zero offsets remain reported in the sealed tables.

Operator telemetry reports setup 302.904s and science through sealing 1491.209s, against the warmed cap 2711.281s (F=1567.520s). No overrun is reported; this telemetry is outside the score seal. This CPU analysis took 1.150s and added zero GPU hours; prior GPU costs remain integrator-owned.

Immutable generated report: [RESULTS.md](analysis_a2txudaqw04nl4/RESULTS.md). Analysis seal: [ANALYSIS_SEAL.json](analysis_a2txudaqw04nl4/ANALYSIS_SEAL.json), SHA-256 `deb5b6c9786da462912c4bcc32b2f36740757769e2917f70c7ba76ebce8325e2`.

Capture seal: [SCORE_SEAL_a2txudaqw04nl4.json](SCORE_SEAL_a2txudaqw04nl4.json), SHA-256 `2afca06f0bc89e04c83e995efb57fc4bec39ac0a9c92e136a27f1c73a9a0d074`. Verification and single-run command: [ANALYSIS_VERIFICATION.json](ANALYSIS_VERIFICATION.json). Directions remain frozen at `36bd59a9`.
