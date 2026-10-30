# E87 launch blockers

- Exact grid is 57,600 Oracle and 2,400 NLA readouts, not the rough cost paragraph's
  approximately 25k + 2.9k + 2k. Forecast the exact grid; do not spend beyond the
  sealed cap. Two pods change wall time, not total GPU custody.
- §200 describes the eight named missed rows as probe >=0.90, but W-text's E81
  source manifest reports E49 holder_after_handovers probe 0.7142857142857143.
  The row is explicitly named in §200. No replacement/drop or threshold change is
  authorized by this runner. Keep the requested bank intact pending ratification
  of the named-row exception (a row/gate question, not a mere implementation choice).
- CPU input audit found all 30 selected nesting_depth prompts have fewer than16
  tokens (minimum12). Last16 cannot be acquired without a rule change. Need a
  ruling on available positions versus a new frozen prompt/item bank. No padding,
  duplicate positions, negative-index wraparound, or replacement is authorized.

Current conservative batch8 planning forecast: 109,441 GPU-seconds including1.25
margin, using saved E68/E80 timings (not a new E87 measurement). Registered total
is14,400s; standing2x would be28,800s. Actual-archive CPU guards correctly return
NO_FIT for shard0 and reject short positions for shard1. Synthetic exact-archive
full-path test passes. No pod launch is authorized by the committed HOLD request.
