**§151 clarification 1 (2026-10-26 04:00 CET, answers W-text, before any persistence value or score join).**
1. **W1 rows:** the structure rows in the denominator of W1's registered blind-spot rule (the "16 of 19"), as listed
   in that rule's sealed metrics. W-text lists them in the state-function seal. If that list cannot be recovered
   exactly, use W1's rows whose frozen class is structure and report the difference.
2. **State functions are incremental lexical trackers, not the bank validators.** Each is derived from the row
   definition: bracket and quote counters, indentation width, pipe and cell counters, nesting depth, list markers.
   - **Undefined extensions:** where the tracker cannot determine the state at extension k (for example incomplete
     syntax), the last determined state carries forward. Persistence ends only when a determined state differs from
     the item's label.
   - **Exclusions:** an item whose state is undetermined at k = 0 is excluded and counted. A row with more than 20%
     of items excluded is NOT EVALUABLE.
   - **W12 rows (no general checker), unit-end rule:** persistence is the number of following tokens until the end
     of the unit the label refers to:
     - sentence rows: the next sentence terminator;
     - paragraph rows: the next blank line;
     - syntax_role and clause_embedding: the next clause boundary (`, ; : .` or a coordinating conjunction).
     syntax_role tracks the original read-position word, not the new endpoint.
3. **Following text:** one uniform source for every item in all three banks. Base Qwen's greedy 32-token continuation
   of the exact prefix, generated once (seed 20261026, ≤ 0.3 GPU-h) and frozen before use. It is labelled
   "model-expected continuation", not true continuation; E1b's next-16 is not reused. No censoring at 16.

