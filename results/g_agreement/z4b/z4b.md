# Z4b — ownership follow-up

Pre-registered in BRIEF_Z (deviation 2026-10-09, before collection). 32 ownership pairs × both sources, α 1 (h' = h_A + (h_B − h_A) at the arm's positions). Flip = parsed answer is the other candidate and coherent. Δ_model = lo_model − X2 natural lo_model of the same state (nats, toward the other candidate). f_r = reader r's LO shift as a fraction of its own natural separation of the pair.

R_all (pre-registered) = 1.00; measured X2 S2 α 1 all positions = 1.00.

| cell | n | mean #pos | flip (Wilson 95%) | coherence | mean Δ_model [pair boot] | f Oracle lens | f J-lens |
|---|---|---|---|---|---|---|---|
| question_only@L38 | 64 | 11.2 | 6/64 = 0.09 [0.04, 0.19] | 1.00 | +7.78 [+7.07, +8.51] | +0.14 [+0.10, +0.19] | +0.22 [+0.09, +0.39] |
| template_only@L38 | 64 | 9.0 | 7/64 = 0.11 [0.05, 0.21] | 1.00 | +7.62 [+6.75, +8.60] | +0.85 [+0.81, +0.89] | +0.77 [+0.55, +0.94] |
| last3@L38 | 64 | 3.0 | 0/64 = 0.00 [0.00, 0.06] | 1.00 | +0.55 [+0.41, +0.69] | +0.70 [+0.63, +0.78] | +0.58 [+0.19, +0.88] |
| question_first_half@L38 | 64 | 5.2 | 0/64 = 0.00 [0.00, 0.06] | 1.00 | +2.68 [+1.76, +3.59] | +0.05 [-0.00, +0.10] | +0.08 [-0.02, +0.20] |
| question_second_half@L38 | 64 | 6.0 | 3/64 = 0.05 [0.02, 0.13] | 1.00 | +3.13 [+2.00, +4.35] | +0.10 [+0.06, +0.13] | +0.06 [-0.08, +0.25] |
| names_objects_only@L20 | 64 | 3.9 | 64/64 = 1.00 [0.94, 1.00] | 1.00 | +25.25 [+24.17, +26.35] | +0.95 [+0.85, +1.03] | +0.91 [+0.60, +1.15] |
| names_objects_only@L28 | 64 | 3.9 | 0/64 = 0.00 [0.00, 0.06] | 1.00 | +2.54 [+2.11, +3.02] | -0.02 [-0.09, +0.03] | -0.04 [-0.15, +0.06] |
| names/objects only @L38 (Y2) | 64 | 3.9 | 0/64 = 0.00 [0.00, 0.06] | 1.00 | +0.88 [+0.70, +1.08] | -0.01 [-0.04, +0.02] | -0.04 [-0.09, +0.02] |
| all but names/objects @L38 (Y2) | 64 | 32.6 | 64/64 = 1.00 [0.94, 1.00] | 1.00 | +24.17 [+23.14, +25.24] | +1.02 [+0.99, +1.06] | +1.02 [+0.97, +1.07] |
| all positions @L38 (X2 S2) | 64 | 36.5 | 64/64 = 1.00 [0.94, 1.00] | 1.00 | +25.02 [+23.97, +26.12] | +1.01 [+0.98, +1.05] | +0.99 [+0.97, +1.01] |

## Decision (pre-registered)

Bar: 0.8·R_all = 0.80 (R_all = 1.00, ownership, all positions at L38, pre-registered).
- question_only: 6/64 = 0.09 → below the bar.
- template_only: 7/64 = 0.11 → below the bar.
- last3: 0/64 = 0.00 → below the bar.
- question_first_half: 0/64 = 0.00 → below the bar.
- question_second_half: 3/64 = 0.05 → below the bar.
L38 verdict: no role-defined span alone reaches 0.8·R_all.
Binding verdict: THE BINDING MOVED — names_objects_only flips ≥ 0.5 at L20 (L20 1.00, L28 0.00) while it flips 0/64 at L38 (Y2 data).

## NLA reproduction gate

Verdict: **PASS** — Z4 NLA numbers may be reported. Gate: within-pair win (X1 E1) within 0.72 ± 0.05 on ownership and on mapping.

| family | gate win | X1 win | median abs Δlo vs X1 | sign agreement |
|---|---|---|---|---|
| ownership | 34/47 = 0.723 | 34/47 = 0.723 | 0.000 | 1.000 |
| mapping | 34/47 = 0.723 | 34/47 = 0.723 | 0.000 | 1.000 |
| language | 23/23 = 1.000 | 23/23 = 1.000 | 0.000 | 1.000 |
| tense | 23/23 = 1.000 | 23/23 = 1.000 | 0.000 | 1.000 |

## Spans

```
{
 "pairs": 32,
 "methods": [
  "offsets"
 ],
 "period_ordinal": {
  "1": 38,
  "2": 26
 },
 "question_only": {
  "min": 9,
  "max": 13,
  "mean": 11.25
 },
 "template_only": {
  "min": 9,
  "max": 9,
  "mean": 9.0
 },
 "last3": {
  "min": 3,
  "max": 3,
  "mean": 3.0
 },
 "question_first_half": {
  "min": 4,
  "max": 6,
  "mean": 5.21875
 },
 "question_second_half": {
  "min": 5,
  "max": 7,
  "mean": 6.03125
 },
 "names_objects_only": {
  "min": 2,
  "max": 4,
  "mean": 3.9375
 }
}
```

Nothing from Z4b is written into writeup.md by this script.
