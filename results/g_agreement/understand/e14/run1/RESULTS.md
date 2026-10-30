# E14 (§103) — GLM-5.3 Oracle-lens rollouts: does the lens state or enact text-structure state?

**Prediction (§103):** `next16` enacts every state (ceiling); SFT readouts enact paren/quote/code/table/list states well
above off-state, close to `next16`; RL readouts enact them much less; neither states any of them above off-state by more
than a few points.

**Assessment.** The "never states" part held: across 156,127 read positions and all five states, the RL and SFT lenses
mention the state in at most 2.4% of readouts, within 2 points of the off-state rate. The "RL enacts less than SFT"
part **did not hold**: both lenses enact the parenthesis state equally (RL +0.42, SFT +0.42 over off-state; ceiling
`next16` +0.80) and the quote state similarly (RL +0.14, SFT +0.10; ceiling +0.34). On GLM-5.3 the RL'd Oracle lens
carries parenthesis state at about half the ceiling, **by writing text that closes the bracket, never by saying so.**

EXPLORATORY, CPU only, $0. One run on `olens_wild_rollouts.parquet` (156,127 rows; hash in RESULTS.json). Rates are per
readout (5 samples per lens per position); differences are per position with a 2,000-sample position bootstrap.

| State (n on) | Lens | States: on − off [95% CI] | Enacts: on − off [95% CI] | Enacts on / off |
|---|---|---|---|---|
| paren (17,042) | RL | +0.001 [+0.000, +0.001] | **+0.419** [+0.412, +0.426] | 0.425 / 0.006 |
| | SFT | +0.000 [−0.000, +0.000] | **+0.422** [+0.417, +0.428] | 0.451 / 0.029 |
| | next16 | −0.000 | +0.796 [+0.790, +0.802] | 0.799 / 0.003 |
| quote (12,672) | RL | +0.003 [+0.002, +0.005] | +0.141 [+0.134, +0.147] | 0.218 / 0.077 |
| | SFT | +0.001 [+0.000, +0.002] | +0.098 [+0.093, +0.103] | 0.176 / 0.078 |
| | next16 | +0.001 | +0.336 [+0.327, +0.345] | 0.449 / 0.113 |
| code (11,814) | RL | +0.001 [+0.001, +0.002] | +0.037 [+0.034, +0.041] | 0.045 / 0.007 |
| | SFT | +0.001 [+0.000, +0.001] | +0.021 [+0.019, +0.023] | 0.025 / 0.004 |
| | next16 | +0.001 | +0.174 [+0.167, +0.181] | 0.193 / 0.019 |
| table (1,437) | RL | +0.018 [+0.012, +0.024] | +0.000 | 0.000 / 0.000 |
| | SFT | −0.001 [−0.003, +0.001] | +0.000 | 0.000 / 0.000 |
| | next16 | +0.001 | +0.850 [+0.834, +0.865] | 0.905 / 0.054 |
| list (18,924) | RL / SFT | −0.008 / −0.003 | **uninformative** | 1.000 / 1.000 |
| | next16 | −0.004 | +0.376 [+0.369, +0.383] | 0.503 / 0.127 |

**Code problems found after the run (reported, not repaired):**
- **list / enacts is degenerate:** every lens readout begins with a bullet (`* `), so the list-marker rule matches all of
  them, on- and off-state. The list row says nothing about enactment.
- **table / enacts is 0.000 for both lenses even off-state:** no readout in the file contains `|`. Either the lenses
  never write pipes or the dataset strips them; we can't tell which. The seeded table example shows the lens continuing
  the cell's text and then leaving the table ("». Круглый стол…") rather than writing the next cell.

**Reading.** Readouts look like continuations, not first-person thoughts (seeded paren example: RL greedy
`* (1 + RS_ratio)) # RSI = 100 - (100 /`; true next16 ` (1 + rs))`). So on this larger model, structure shows up in the
lens output only as enactment. This bears directly on W1: W1's asked scoring compares *descriptions* ("a table header
cell" vs "a table data cell"), so it cannot credit a lens that carries structure by enactment. Whether Qwen's lens
enacts is E6's question.

**Limits.** No activations, so no probe ceiling. One model, block 51. State labels from a 400-character window. The
enact rules are crude and the list/table rules failed as noted. Examples: `EXAMPLES.json` (seeded, chosen before rates).
