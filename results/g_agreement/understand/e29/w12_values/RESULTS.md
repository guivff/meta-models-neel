# E29 — prospective W12 D and P

Dated values: 2026-10-26T01:09:00+01:00. CPU analysis of sealed base-Qwen scores.

W12 values are sealed for the coordinator's prospective predictions. Reader comparisons remain pending.

D = AUROC(s_A − s_B, value A), with each candidate score averaged equally over its frozen phrasings. No sign reversal.

P is the median across items of the true candidate's averaged score.

| Row | Items | D | P |
|---|---:|---:|---:|
| syntax_role | 84 | 0.608844 | -4.526409 |
| sentence_type | 84 | 0.981293 | -5.369820 |
| sentence_position | 84 | 0.009637 | -4.750970 |
| paragraph_index | 84 | 0.706349 | -4.921021 |
| paragraph_start | 84 | 0.607710 | -4.420608 |
| clause_embedding | 84 | 0.700113 | -5.235847 |

No reader references were loaded, and no R1/R2 test, reader correlation, confidence interval or verdict was computed.
The ignored item ledger preserves each original item ID, value, candidate means and signed margin for a later paired comparison.
