# What we measured that bears on your two headline claims

Every number below is copied from the file cited next to it; nothing was re-run or recomputed for this note. Paths are
on branch `r/blindspot` unless a branch is given (`git show origin/<branch>:<path>`). Readers' sites follow each source:
"Oracle@44" is on the Oracle lens's trained grid (20–60 step 4); "Oracle@42" is off it.

## Claim 1: "Oracle Lens never states a property in free text"

**Short answer: true for text-structure properties in every measurement we have; false for content, semantic and
planted-concept properties.**

### Structure (supports the claim)

| measurement | number | source |
|---|---|---|
| E13(b) blind Claude coder, W1 test readouts, Oracle@44 | table_column 0/75 mentions [0.0, 4.9]; prose_paren 0/75 [0.0, 4.9] (it *enacts* table structure in 69/75) | `results/g_agreement/understand/e13/CLAUDE_RESULTS.md` (table, lines 9–12) |
| E13(b) literal keyword hits by true value, Oracle@44 | 0/37, 0/38 (table_column); 0/38, 0/37 (prose_paren); 0/84, 0/84 (§84 wordlist_preposition) | `results/g_agreement/understand/e13/KEYWORD_BY_TRUE_VALUE.md` |
| E24 rule R4, greedy readouts at every trained layer 20–60 | correct structure statements ≤ 18 of 1,596 per layer; at 44: k = 5, rate 0.0031, Wilson [0.0013, 0.0073] | `projects/g_agreement/BRIEF_UNDERSTAND.md` ~line 2953; `results/g_agreement/understand/e24/analysis_modeG159_public/metrics.json` (`rules.44.R4`) |
| E43 silence audit (R1 HOLDS, 17/17 eligible structure bank-rows) | Oracle@44 native: prose_paren 0/386 readouts state a value; probe on the silent items ≈ 1.00 | `results/g_agreement/understand/e43/analysis_2026-10-26/RESULTS.md` (lines 3, 114) |
| E37 SFT (pre-RL) vs RL Oracle lens | R4 MET: neither names structure (correct statements 4/1,344 RL, 1/1,344 SFT) | `BRIEF_UNDERSTAND.md` ~line 3255; `results/g_agreement/understand/e37/analysis_149/metrics.json` |
| Q1 reading study (rater 1), Oracle | earlier-state tier 0/80 [0.0, 4.6]; local-form tier 0/80; W6-steered readouts structure named 0/320 | `results/g_agreement/understand/q_analysis/RATER1_RESULTS.md` (lines 25–32, 50–51) |
| E14, GLM-5.3 Oracle-lens wild rollouts (public dataset, block 51) | state mentioned in ≤ 2.4% of readouts | `results/g_agreement/understand/e14/run1/RESULTS.md` |

Caveat on the API judge: E13(b)'s API coder reported Oracle "mention" 47/75 and 24/75; this is recorded as an invalid
construct (it counted enactment as mention) and is not used (`e13/RESULTS.md`).

### Content, semantics and planted concepts (contradicts "never")

| measurement | number | source |
|---|---|---|
| SA-R, registered confirmatory: Oracle@44 names a concept added to the activation | 204/396 = 51.52% (equal-concept 51.00%); all five controls 0/396; CONFIRMED | `origin/r/neel5: results/g_agreement/r/neel5/sar/sar_recovery_20261021/analysis/REPORT.md` |
| SA open vocabulary | Oracle 40/400 (10.00%), concept − control +10.00 pp [+2.00, +26.67] | `origin/r/neel5: results/g_agreement/r/neel5/sa/analysis_20261021/REPORT.md` |
| §65B ambiguous words | Oracle states the typical word sense on 143/160 mismatched items | `origin/r/inverter: results/g_agreement/v_prior/s65b/RESULTS_R3_20261023.md` |
| Q1 reading study, content tier | Oracle states the property in 15/80 = 18.8% [11.7, 28.7], all 15 correct | `results/g_agreement/understand/q_analysis/RATER1_RESULTS.md` (line 25) |
| G1 (early phase, Oracle@42) | asserts language 8/8 and tense 8/8; abstains on ownership 0/8 | `results/g_agreement/writeup.md` (lines 17–20) |
| F2-1, judged free-text hit rate, Oracle@44 | 50% [27, 74] (plain chat template) | `results/g_agreement/f2/t1/t1.md` (line 11) |
| F2-5, Oracle@56 with no stem | names the ownership/mapping answer in 86% [67, 98] of readouts (12% at 44) | `results/g_agreement/f2/t5/t5.md` (line 14) |

So the property-type split matters: on structure the Oracle lens is silent (it enacts the structure, e.g. writes table
cells, instead of stating it); on content it states things. After fine-tuning on the property (E28/E39) it names a
value in 84/84 readouts but so does the shuffled-label arm, i.e. a trained template, not a reading
(`results/g_agreement/understand/e28/naming_correctness_2026-10-26/REPORT.md`).

## Claim 2: "the NLA's position readout is one-sided"

**Short answer: on our bank it holds for the parenthesis row and for one §84 row, but not for table column, where the
NLA states both values; on your own S16 bank the forced-choice score shows a sign pattern consistent with a one-sided
bias that only your raw margins can confirm.**

### Free text on our W1 bank (NLA@42, one greedy readout per test state)

| row | measurement | number | source |
|---|---|---|---|
| prose_paren | keyword hits by true value | inside 5/38 = 13.2% [5.8, 27.3]; outside 0/37 [0.0, 9.4] | `e13/KEYWORD_BY_TRUE_VALUE.md` |
| prose_paren | blind Claude coder | 5/75 mention; all 5 correct; true values A/B = 5/0 | `e13/CLAUDE_RESULTS.md` (lines 12, 43) |
| table_column | keyword hits by true value | first 9/37 = 24.3%; later 10/38 = 26.3% | `e13/KEYWORD_BY_TRUE_VALUE.md` |
| table_column | blind Claude coder | 36/75 mention; 31/31 resolved correct; true values first/later = **18/13** | `e13/CLAUDE_RESULTS.md` (lines 10, 42) |
| §84 wordlist_preposition (not a position row) | keyword hits by true value | A 21/84 = 25.0%; B 0/84 | `e13/KEYWORD_BY_TRUE_VALUE.md` |

Reading: on paren our data match yours (never "outside"). On table column the coder resolved 13 correct statements on
*later*-column items, against your 12/160 "late". Two caveats: (1) the coder note says some coders counted naming of
the current token as a mention (`CLAUDE_RESULTS.md` line 5), so "states the later column" may partly be "names the
cell"; (2) the regex cannot tell which value a hit asserts. Our later column is column 5 exactly, yours 4–6. The raw
readouts are in `share/experiments/W1_40row/raw/w1-units_priority_nla_unasked.nla.jsonl.gz`, so you can code them with
your own rule.

Other NLA free-text samples rarely name either value:
- Q2c rater coding of NLA@42 readouts: prose_paren mentions 2/84 and table_column mentions 0/84; structure tokens
  0/42 on inside items and 0/42 on outside items (`q_analysis/RATER1_RESULTS.md`, lines 54, 60 and 112–113).
- E43 native readouts: prose_paren 0/356; table_column 0.0113 of 354 (`e43/analysis_2026-10-26/RESULTS.md`, lines
  106 and 201).

### Forced-choice (asked) scores

- W1 (our items, two two-sided phrasings each, NLA@42): table_column AUROC 0.568 [0.349, 0.789]; prose_paren 0.744
  [0.571, 0.934]; ordinal table column ρ 0.054 [−0.325, 0.482] (`results/g_agreement/blindspot/w1/descriptive/TABLES.md`).
  No per-value or per-phrasing breakdown was computed; the raw per-phrasing scores are in
  `share/experiments/W1_40row/raw/w1-assembled_nla_scores.nla.jsonl.gz`.
- **E27 on your S16 data (your items, your four phrasings, NLA@42, unswapped activation):** AUROC is near 1 but the
  strict-sign count (margin favours the true value) is exactly half:
  - tb_tablecol: AUROC 0.9980 [0.9930, 1.0000]; strict-sign 100/200 (mean of 4 phrasings) and 100/200 (fixed first)
  - tb_paren: AUROC 0.9637 [0.9373, 0.9839]; strict-sign 102/200 (mean) and 109/200 (fixed)
  - control ij2_lang (language): AUROC 0.9998; strict-sign 197/200

  (`results/g_agreement/understand/e27/ALL_CELLS.md` lines 63, 119, 121, 175, 177.) With 100 items per value,
  100/200 at AUROC ≈ 1 is what you get if the margin has the same sign on (almost) every item, i.e. the NLA always
  prefers one candidate and only its *size* tracks the truth. E27 did not record which side is preferred; your raw
  S16 margins answer it directly. This is an inference from counts, not a measured per-value rate.
- E29 base-Qwen text discriminability of your candidate strings (a candidate-prior reference, non-blind, no CIs):
  D = 0.724 tb_tablecol, 0.456 tb_paren (`results/g_agreement/understand/e29/suraj_nonblind_values/RESULTS.md`).

### Related, from swaps and steering

- W4 donor/recipient swap (Oracle-text component frozen, remainder swapped), NLA: prose_paren donor AUROC 0.6967
  [0.3750, 0.9304]; table_column donor 0.3510 [0.1667, 0.5182]
  (`origin/r/blindspot-mech: results/g_agreement/blindspot/mechanism/w4/aggregate_rk4veemwm0jf9i/HANDOFF.md`).
- E27 matched rows (NLA@42 donor AUROC under the reconstruction-difference swap): S16 tb_tablecol 0.9519 [0.9176,
  0.9784] vs our table_column 0.3864 [0.0861, 0.7161]; S16 tb_paren 0.7688 vs our prose_paren 0.5689
  (`e27/RESULTS.md`). Banks, labels (column 4–6 vs 5), partner matching and phrasings all differ; E27 could not
  assign the gap to one cause, which is why the 2×2 cross-scoring (`share/cross_scoring/`) is the next step.
- W7 steering at block 44 along the probe direction: prose_paren effect +0.11911 [0.05149, 0.18319], MET;
  table_column −0.01521 [−0.09474, 0.05457] (`origin/r/blindspot-mech`, W7 in `EXPERIMENTS.md`).
