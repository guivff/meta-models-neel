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

All four measures, all doses, and all control arms are in `cells.csv`; curve slopes and 95% cluster-bootstrap intervals are in `summary.json`. Preanswer and answer projection changes measure whether the intervention reached the next layer. No sign was flipped.

Capture status: `{'error': None, 'experiment': 'E19', 'exploratory': True, 'status': 'COMPLETE'}`.

Custody telemetry is **not covered** by the primary score seal. Its copied contents and SHA256 are retained separately in `summary.json`; they are not an independent provider-custody audit.
