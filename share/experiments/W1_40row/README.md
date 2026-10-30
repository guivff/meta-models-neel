# W1 (§70): the 40-row, length-matched concept table

**Question.** Does the Oracle lens have a categorical blind spot for count-like and state-like text structure that the
NLA does not have, while both read semantic content?

**Hypothesis.** The registration is `projects/g_agreement/BRIEF_BLINDSPOT.md` §70, pre-registered 2026-10-23 06:00
CEST. The Oracle lens inverts a reconstructor trained on the *average* preceding activation, so it covers only the part
of an activation that can be put into words. The NLA reconstructs the exact activation. The rule is applied on
evaluable count-like and state-like rows:
- (i) Oracle ≤ probe − 0.15 on ≥ 75% of rows;
- (ii) on those same rows, NLA within 0.10 of the probe on ≥ 75%;
- (iii) on semantic rows, Oracle within 0.10 of the probe on ≥ 75%.

All three → CONFIRMED. (i) and (iii) without (ii) → PARTIAL. Otherwise NOT MET.

**Result: NOT MET.**
- (i) PASS, 16/19, Wilson [62.4%, 94.5%]
- (ii) FAIL, 2/16, [3.5%, 36.0%]
- (iii) FAIL, 6/9, [35.4%, 87.9%]

So the Oracle lens is blind on most structure rows, but the NLA is not better on them: only `python_string` and
`table_role` come within 0.10 of the probe. Full text: `results/RESULTS.md`.

Status: **DONE.** The asked scores are complete and sealed. The free-response recall is **PARTIAL**, with no blinded
judgement yet, so we report no recall rate.

W5 (§74) swept the Oracle lens and the probe across layers on the same 40 rows and 84 test items. Its result is **NOT
EVALUABLE**: 10/16 blind-spot rows meet the rule (Wilson [38.6%, 81.5%]), and the bounds are 62.5–75%
(`results/W5_RESULTS.md`).

`results/RESULTS.md` predates the W5 completion and still says "W5 is INCOMPLETE". The W5 analysis supersedes that
line.

## Files

| what | file |
|---|---|
| item bank, all 7,296 items (40 binary rows × 168, plus two ordinal sub-rows × 288) | `items_w1_all.jsonl.gz` |
| exact phrasings / candidate strings per reader per row | `phrasings_w1.json` (a copy of the frozen `templates.json`) |
| the 40-row table as JSON (every reader at its layer, probes at 42 and 44, gates, mismatched arm, CIs) | `table_40rows.json` |
| W5 layer sweep (Oracle + probe at 6 layers) | `results/W5_RESULTS.md`, `results/W5_metrics.json` |
| registered metrics (240 cells), descriptive tables, figure | `results/metrics.json`, `results/tables.json`, `results/TABLES.md`, `results/W1_CONCEPT_TABLE.png` |
| raw per-item asked scores (every reader, arm and phrasing) | `raw/w1-assembled_{target,nla}_scores.*.jsonl.gz` + the `SCORE_SEAL` files |
| raw free readouts (sealed priority unit: table_column, prose_paren, prose_sentiment, python_effect, latex_subject) | `raw/w1-units_priority_{target,nla}_unasked.*.jsonl.gz` + the `FREE_SEAL` files |
| compute | `results/COMPUTE_DEVIATION.json`; see the cost section below |
| how the exports were made (with seal checks) | `../../export_w1.py`, `../../EXPORT_RECEIPT.json` |

## Item bank

Fields of each row in `items_w1_all.jsonl.gz`:

| field | meaning |
|---|---|
| `id` | item id |
| `row` | the feature (row name) |
| `split` | `dev` or `test` |
| `text` | the item text |
| `value` | the true value (`level` 1–8 for ordinal rows) |
| `class` | `count-like` / `state-like` / `semantic` |
| `domain` | prose / python / latex / json / table / list |
| `cluster` | template family, `<row>:t00..t11` |
| `cluster_hash` | the hash of the cluster |
| `pair_id` | links the two values of a matched pair (same template, same length) |
| `read_position` | the 0-based token index read, always `token_length − 1` |
| `token_length` | text length in tokens |

The read position is the last token of `text`, with no chat template and no special tokens. All 7,296 texts
re-tokenise to the captured ids.

How the bank is built:
- **Generator.** `projects/g_agreement/blindspot/w1_templates.py` and `items.py`. The row list is fixed in
  `items.py: FEATURES`, which says "Forty hypotheses, fixed before readouts".
- **Templates.** Twelve authored template families per row. Families t00, t02, … t10 form the dev split and t01, t03,
  … t11 the test split.
- **Pairs.** Seven pairs per family, which gives 84 test items per row (42/42).
- **Length matching.** Each pair is padded to exactly equal token length with an unrelated preamble, which is followed
  by `\n\n--- Current excerpt ---\n`.

## Scoring

- **Sites.** Oracle lens at block 44, one of its trained layers. NLA at block 42, the layer it was trained on. J-lens
  and the logit lens at block 44. Logistic probes at blocks 42 and 44.
- **Oracle and NLA.** Every binary row is **two-candidate** (value A vs value B). The score is the native teacher-forced
  **summed sequence log-prob** of the A string minus the B string, using your `paired_logodds_templates` at `2e98a5db`.
  It is averaged over **two** frozen phrasing pairs:
  - NLA: "The current excerpt has {v}." / "At the read position, there is {v}."
  - Oracle: "- {v}" / "- At the read position, the excerpt has {v}."
- **J-lens and logit.** Two single-word pairs per row: the value words, plus one synonym pair from
  `protocol.py: BASELINE_SYNONYMS`. The score is the maximum-token-variant cosine contrast (J-lens) or the log-odds
  contrast (logit).
- **What counts as a hit.** There is no per-item hit. The metric is AUROC over the 84 test items, with A positive, and a
  2,000-sample template-cluster bootstrap (seed 20261023).
- **Gates.** A row is NOT DECODABLE if the probe AUROC is < 0.85. A reader is NOT EVALUABLE on a row if its mismatched
  AUROC is > 0.60; the mismatched arm scores the opposite-value paired item's activation.
- **Ordinal sub-rows** (`table_column_ordinal`, `python_depth_ordinal`). These are **multi-level**, levels 1–8. The
  score is the Spearman ρ of the NLA@42 mean log-odds against level: ρ ≥ 0.6 → "counts", otherwise "flags a state".
- **Code.** `projects/g_agreement/blindspot/run.py` (capture + scoring, label-free) and `analysis.py` (gates, AUROC,
  bootstrap, verdict).

## The table

There are 40 rows: 19 count-like, 11 state-like and 10 semantic. Rule (iii)'s 9 is the 10 semantic rows minus one
gated row.
- **Two-candidate rows:** all 40 binary rows.
- **Multi-candidate rows:** none. The two ordinal sub-rows are multi-level, levels 1–8.
- **Layers.**
  - In W1, the NLA, J-lens and logit lens are each scored at one layer: NLA@42, J@44, logit@44.
  - The Oracle lens and the probe are scored at blocks 20/28/36/44/52/60, which come from W5 (`w5_layer_sweep` per row).
  - W5 was a separate capture and scoring pass. Its Oracle@44 can therefore differ slightly from W1's: on
    table_column it is 0.481 vs 0.474.

`table_40rows.json` holds one entry per row with these fields:
- `generator`, `n`, `n_clusters`, `values`;
- `candidates` (the exact strings per reader);
- `readers` (`olens@44`, `nla@42`, `jlens@44`, `logit@44`, `probe@42`, `probe@44`, each with its AUROC, CI, gate and
  mismatched AUROC);
- `nla_minus_oracle` (the paired difference, with its CI).

`results/TABLES.md` is the same table as markdown.

## Cost

- **Science:** 2.0594 GPU-h on one H200 (pod `0wy2dd13q2o08w`, `results/g_agreement/compute.jsonl` line 498).
- **Staging:** 0.159 GPU-h (line 497).
- **Overrun:** the science ran about 214 s over the registered 7,200 s cap (`results/COMPUTE_DEVIATION.json`). No score,
  rule or item changed because of it.
