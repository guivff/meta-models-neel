# W5 scoring-only completion — 12:55 CEST amendment

Integrator operates and pushes. Do not run `run sweep`: that would recapture.
Use the exact source archive and execution plan bound by `LAUNCH_REQUEST.json`.
The existing six-block capture seal covers 3,360 items, 40 rows and blocks
20/28/36/44/52/60. The worker verifies all hashes, shapes, order and bank lineage.
Stage only its eight capture-seal allowlisted files. Never stage/read the old
`scores.sweep.partial.jsonl`, and never write into the original capture directory.

The new worker always scores 480 feature/layer/arm units (40 × 6 × 2), each with
84 items and the same two frozen phrasing contrasts. No labels or scores are used
for a scope decision. The final output must be a fresh, nonexistent directory.

Operational choices recorded before completion data: use the accepted
`/weights/venv-kernels/bin/python`; 900 s setup outside science; warm up the
production-batch scorer at every layer, discard all warm-up outputs, then time
the next three real units. Discard their outputs as well. Forecast = sum of the
three timings + slowest timing × 480, covering both the smoke and a full fresh
pass. The science cap is exactly 1.5 × this forecast, at most 3,600 s. If it does
not fit, write NO_FIT_REPORT_TO_GUIV and stop; do not drop rows or layers.

The integrator assignment requires `run_kind=W5_SCORING_ONLY_COMPLETION`,
`budget_amendment_commit=09794f4c1cf46a1c41e0930c1e8b120c426bcd0f`, and
`completion_receipt_sha256` bound to this launch request. Pin source/brief/plan/
bank as usual. Reserve at most 3,600 science seconds and 900 setup seconds for
this one completion (prior attempts remain separately disclosed, not recharged).
Set the absolute custody deadline no later than creation + 4,500 s; the worker
retains the final 180 s for retrieval, conservatively shortening science if needed.

Admission writes `<assignment basename>.science-clock.json` beside the assignment
immediately before the first timed scoring forward. Retain the same assignment
and clock across processes: a reset/rebind is rejected. The initial worker timer
is bounded by setup expiry, then first science + assigned cap and the absolute
hardstop minus reserve. After `FORECAST.json` appears, science is shortened again
to first science + 1.5 × forecast. The integrator should likewise shorten the
external science guard to `FORECAST.json.absolute_science_deadline_epoch`, keeping
the independent absolute custody guard. Retrieve both clock and forecast.

Command (integrator supplies assignment/assets/staged paths):

```bash
/weights/venv-kernels/bin/python -m projects.g_agreement.blindspot.w5_complete \
  --assignment ASSIGNMENT.json --assets ASSETS.json \
  --bank W1_LABEL_FREE_STAGE --capture SEALED_W5_CAPTURE_DIRECTORY \
  --execution-plan results/g_agreement/blindspot/w5/completion/EXECUTION_PLAN.json \
  --receipt results/g_agreement/blindspot/w5/completion/LAUNCH_REQUEST.json \
  --w1-analysis SEALED_COMPLETE_W1_ANALYSIS --out NEW_W5_COMPLETION_DIRECTORY
```

The final score seal covers the complete new grid, six copied immutable captures,
item order, provenance, warm-up and forecast receipts. Retrieve and verify before
the unchanged `run analyse-sweep` entrypoint joins labels. No W5 verdict is assigned
from the capture or partial scores. The earlier approximately 289–422 s overrun
remains disclosed per the dated amendment. No pod has been launched by W-core.
