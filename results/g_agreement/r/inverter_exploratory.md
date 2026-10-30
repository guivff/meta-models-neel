# Reconstruction recall and the Oracle advantage — EXPLORATORY

Completed 2026-10-20T04:58:02.692543+00:00. Specified after partial results, before this full-coverage analysis; no primary rule changed. All 22,198 test items have saved natural reconstructions. The primary association uses 108 nondefective facts / 21,198 items; 113 facts / 22,198 items form the sensitivity.

Token recall uses the frozen gate definition: multiset overlap of pinned Qwen tokens, divided by true-text token count after the frozen 256-token input cap. Reconstructions are re-encoded; the additional prompt-only text cap is reported separately. Each fact has equal weight in the association between mean recall and D_f = AUROC(Oracle) − AUROC(inversion). Both 2,000-draw bootstrap schemes and their 95% envelope are retained.

**The data do not establish that the Oracle advantage is larger where reconstruction fails.** Primary pooled Pearson r = +0.1262, 95% envelope [−0.0830, +0.3066]; Spearman ρ = +0.1974, [−0.0851, +0.4044]. The estimates are positive, whereas the proposed failure explanation predicts a negative association. Intervals span zero, so neither a positive relationship nor absence of a negative relationship is established. Within-tag centering does not resolve this. Token overlap measures lexical retention, not preservation of the information needed for a particular question, and correlation cannot establish a mechanism.

## Per-tag recall, all test items

| Tag | Items | Mean token recall |
|---|---:|---:|
| COMPUTED | 3,400 | 15.60% |
| FORM | 1,200 | 14.44% |
| KNOWLEDGE | 4,200 | 13.72% |
| META | 926 | 22.86% |
| PASSAGE-KNOWLEDGE | 1,800 | 6.69% |
| SURFACE | 5,600 | 11.93% |
| TOPIC | 5,072 | 9.86% |

## Per-fact associations

| Subset | Recall measure | Centering | Correlation | Estimate | Fact→item95% | Corpus→fact→item95% | Envelope95% |
|---|---|---|---|---:|---|---|---|
| primary | token_recall | pooled | pearson | +0.1262 | [-0.0467, +0.2851] | [-0.0830, +0.3066] | [-0.0830, +0.3066] |
| primary | token_recall | pooled | spearman | +0.1974 | [-0.0279, +0.3651] | [-0.0851, +0.4044] | [-0.0851, +0.4044] |
| primary | token_recall | within_tag_centered | pearson | +0.0641 | [-0.1247, +0.2494] | [-0.2558, +0.2640] | [-0.2558, +0.2640] |
| primary | token_recall | within_tag_centered | spearman | +0.1533 | [-0.0796, +0.3206] | [-0.2241, +0.3620] | [-0.2241, +0.3620] |
| primary | scored_text_token_recall | pooled | pearson | +0.1262 | [-0.0467, +0.2851] | [-0.0830, +0.3066] | [-0.0830, +0.3066] |
| primary | scored_text_token_recall | pooled | spearman | +0.1974 | [-0.0279, +0.3651] | [-0.0851, +0.4044] | [-0.0851, +0.4044] |
| primary | scored_text_token_recall | within_tag_centered | pearson | +0.0641 | [-0.1247, +0.2494] | [-0.2558, +0.2640] | [-0.2558, +0.2640] |
| primary | scored_text_token_recall | within_tag_centered | spearman | +0.1533 | [-0.0796, +0.3206] | [-0.2241, +0.3620] | [-0.2241, +0.3620] |
| all_facts_sensitivity | token_recall | pooled | pearson | +0.1288 | [-0.0379, +0.2792] | [-0.0845, +0.2985] | [-0.0845, +0.2985] |
| all_facts_sensitivity | token_recall | pooled | spearman | +0.2108 | [-0.0091, +0.3699] | [-0.0715, +0.3974] | [-0.0715, +0.3974] |
| all_facts_sensitivity | token_recall | within_tag_centered | pearson | +0.0526 | [-0.1306, +0.2191] | [-0.2688, +0.2490] | [-0.2688, +0.2490] |
| all_facts_sensitivity | token_recall | within_tag_centered | spearman | +0.1242 | [-0.0848, +0.2965] | [-0.2144, +0.3295] | [-0.2144, +0.3295] |
| all_facts_sensitivity | scored_text_token_recall | pooled | pearson | +0.1288 | [-0.0379, +0.2792] | [-0.0845, +0.2985] | [-0.0845, +0.2985] |
| all_facts_sensitivity | scored_text_token_recall | pooled | spearman | +0.2108 | [-0.0091, +0.3699] | [-0.0715, +0.3974] | [-0.0715, +0.3974] |
| all_facts_sensitivity | scored_text_token_recall | within_tag_centered | pearson | +0.0526 | [-0.1306, +0.2191] | [-0.2688, +0.2490] | [-0.2688, +0.2490] |
| all_facts_sensitivity | scored_text_token_recall | within_tag_centered | spearman | +0.1242 | [-0.0848, +0.2965] | [-0.2144, +0.3295] | [-0.2144, +0.3295] |

The scored-text-cap sensitivity equals the raw reconstruction estimates here. Within-tag Spearman means ranking the tag-centered raw values, as specified; it is not partial Spearman. All requested bootstrap draws were valid.

[Per-fact table](inverter_exploratory_per_fact.csv) · [Full summary and hashes](inverter_exploratory_summary.json)

![Per-fact recall versus Oracle-minus-inversion](inverter_exploratory_scatter.png)

Independent audit re-tokenized every item, reproduced all per-fact means and scipy correlations, and checked envelope arithmetic:44,655 checks; maximum absolute discrepancy2.78e−16. Raw per-item metrics and all hashes remain in cache/g_agreement/r/inverter/continuation2_20261020/union_final/exploratory/. Numeric/operand and reply-style diagnostics retain their earlier incomplete snapshots and were not rerun.
