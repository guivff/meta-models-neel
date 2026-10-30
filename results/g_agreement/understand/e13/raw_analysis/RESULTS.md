# E13(b) §101 — matched sealed W1 mention sample

**Prediction:** Oracle mentions structure in under10% of readouts; NLA mentions more and can identify the value. **Scope:** only prose_paren and table_column; this cannot adjudicate all16 W1 structure rows or the §84 follow-up. Results below are descriptive.

150 distinct matched W1 test states, two rows only,75 per row; one sample/state/reader. No §84 and no unsealed outputs.

| Row | Reader/site | Valid / sample | Mentions | Mention rate [Wilson95%] | Correct / mentions | Accuracy [Wilson95%] | Keyword flags | Judge/keyword disagreements |
|---|---|---:|---:|---|---:|---|---:|---:|
| prose_paren | oracle L44 | 75/75 | 47 | 0.627 [0.514, 0.727] | 13/47 | 0.277 [0.169, 0.418] | 0/75 | 47 |
| prose_paren | nla L42 | 75/75 | 5 | 0.067 [0.029, 0.147] | 5/5 | 1.000 [0.566, 1.000] | 5/75 | 2 |
| table_column | oracle L44 | 75/75 | 24 | 0.320 [0.225, 0.432] | 18/24 | 0.750 [0.551, 0.880] | 0/75 | 24 |
| table_column | nla L42 | 75/75 | 29 | 0.387 [0.285, 0.500] | 25/29 | 0.862 [0.694, 0.945] | 19/75 | 22 |

| Row | Paired items | NLA − Oracle mention rate [bootstrap95%] | Conditional accuracy difference [bootstrap95%] |
|---|---:|---|---|
| prose_paren | 75 | -0.560 [-0.667, -0.440] | 0.723 [0.591, 0.841] |
| table_column | 75 | 0.067 [-0.080, 0.213] | 0.112 [-0.088, 0.328] |

**Prediction reading in this sample:** Oracle point mention rates below10% on both rows: False. NLA point mention rates higher on both rows: False. Value accuracy is evaluated only where a property is mentioned; zero mentions is UNAVAILABLE, not chance accuracy. No mechanism or whole-bank verdict follows.

The judge saw only an unchanged property question giving both possible values and the raw generated readout. Sampler metadata, true values, reader identities, source prompts and paths were not sent. Ground truth was used only for the user-authorized stratified selection, then withheld from metric joins until the coding seal. Raw strings include incomplete endings/source parser failures; no repair. Native44/42 sites differ, so this is not a same-vector comparison.

Keyword flags are literal substring/word matches, not evidence of a current-state assertion or a correct value. Their disagreement with the judge is reported rather than resolved. Evidence quotes are audited separately, never used to discard otherwise valid primary codes. Invalid typed codes remain missing; no retry, repair or replacement. Wilson intervals treat sampled outputs as Bernoulli; item-paired bootstrap supplies the paired comparison. Missing-as-no/yes bounds and evidence flags are in METRICS.json.

Other14 W1 structure rows unavailable; all §84 excluded until E13(a) seals both readers for a second sample.

Route: Gemini3.1FlashLite via OpenRouter→Vertexglobal, ZDR/deny collection, own logging/data use verified off. API cost $0.05218625 / $5 hard cap; unresolved reserve $0;0GPU-h. Request count and exact policy audit in AUDIT.json.
