# E28 step-400 naming correctness — 2026-10-26

Descriptive only, under §145. The original sealed free-readout bytes and private label key were hash-verified. E24’s frozen regex was applied without changes; its status counts and correct-statement rates exactly reproduce the sealed analysis. No model calls, training, bootstrap or registered-analysis rerun.

Correct and wrong mean **only** that value is named. Both-value matches are reported separately and receive no correctness credit. Counts in each evaluable row sum to84.

| Row | Arm | Correct only | Wrong only | Both | Neither | Any value named |
|---|---|---:|---:|---:|---:|---:|
| prose_paren | L | 38 | 6 | 40 | 0 | 84/84 |
| prose_paren | S | 0 | 1 | 83 | 0 | 84/84 |
| prose_paren | B | 34 | 26 | 24 | 0 | 84/84 |
| python_string | L | 42 | 0 | 42 | 0 | 84/84 |
| python_string | S | not run | not run | not run | not run | not run |
| python_string | B | 84 | 0 | 0 | 0 | 84/84 |
| table_role | L | 51 | 5 | 28 | 0 | 84/84 |
| table_role | S | not run | not run | not run | not run | not run |
| table_role | B | 54 | 1 | 29 | 0 | 84/84 |
| python_depth | L | 31 | 0 | 53 | 0 | 84/84 |
| python_depth | S | not run | not run | not run | not run | not run |
| python_depth | B | 79 | 0 | 5 | 0 | 84/84 |
| table_column | L | 34 | 0 | 50 | 0 | 84/84 |
| table_column | S | not run | not run | not run | not run | not run |
| table_column | B | 52 | 1 | 31 | 0 | 84/84 |
| prose_sentiment | L | N/E | N/E | N/E | N/E | N/E |
| prose_sentiment | S | N/E | N/E | N/E | N/E | N/E |
| prose_sentiment | B | N/E | N/E | N/E | N/E | N/E |

**The shuffled-label parentheses arm S also names a value in84/84 readouts:** 0 correct only, 1 wrong only, 83 both and 0 neither.
Thus the84/84 any-naming rate is not evidence of reading the correct value or of answering transferring to value-correct naming. In the shuffled arm it predominantly detects language naming both alternatives, consistent with the trained template. This is a descriptive reading of the frozen regex categories, not a new causal test.

S was not registered for strings, table role, depth or column; those cells are not run. The frozen E24 regex has no sentiment detector: L/S/B each has84 not_structure outputs, so correctness and naming remain N/E rather than being relabelled neither.

All original E28 verdicts remain unchanged. E39 stays as built and awaits E36’s verified captures; E37 stays ready.
