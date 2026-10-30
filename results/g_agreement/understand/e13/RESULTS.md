# E13(b) §101 — matched sealed W1 mention sample

**MEASUREMENT FAILURE — automatic mention coder conflates enactment with explicit statement.** The frozen prompt explicitly excluded merely parenthesized continuations and numeric/table fragments. Nevertheless it coded those as positive current-state mentions. The keyword cross-check returned zero Oracle keyword flags in both rows, prompting post-seal inspection; six seeded Oracle-positive examples demonstrate the mismatch (CODER_DIAGNOSTIC.json). Thus the automatic mention and value-accuracy estimates below are **not reliable measures of the registered construct**, and their numerical disagreement with the prediction is not evidence against it. No prompt change, rerun, replacement, filtering or posthoc code correction was made. The unchanged initial numeric output/seal is archived in raw_analysis/; the original CODING_SEAL remains unchanged.

**Prediction:** Oracle mentions structure in under 10% of readouts; NLA mentions more and can identify the value. **Scope:** only prose_paren and table_column; this cannot adjudicate all 16 W1 structure rows or the §84 follow-up. Results below are descriptive.

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

**Mechanical prediction comparison using the unvalidated automatic codes (not a scientific verdict):** Oracle point mention rates below10% on both rows: False. NLA point mention rates higher on both rows: False. Value accuracy is evaluated only where a property is mentioned; zero mentions is UNAVAILABLE, not chance accuracy. No mechanism or whole-bank verdict follows.

The judge saw only an unchanged property question giving both possible values and the raw generated readout. Sampler metadata, true values, reader identities, source prompts and paths were not sent. Ground truth was used only for the user-authorized stratified selection, then withheld from metric joins until the coding seal. Raw strings include incomplete endings/source parser failures; no repair. Native44/42 sites differ, so this is not a same-vector comparison.

Keyword flags are literal substring/word matches, not evidence of a current-state assertion or a correct value. Their disagreement with the judge is reported rather than resolved. Evidence quotes are audited separately, never used to discard otherwise valid primary codes. Invalid typed codes remain missing; no retry, repair or replacement. Wilson intervals treat sampled outputs as Bernoulli; item-paired bootstrap supplies the paired comparison. Missing-as-no/yes bounds and evidence flags are in METRICS.json.

Other 14 W1 structure rows unavailable; all §84 excluded until E13(a) seals both readers for a second sample.

Route: Gemini 3.1 Flash Lite via OpenRouter→Vertexglobal, ZDR/deny collection, own logging/data use verified off. API cost $0.05218625 / $5 hard cap; unresolved reserve $0;0 GPU-h. Request count and exact policy audit in AUDIT.json.

## Valid descriptive cross-check and scope limitation

The frozen literal keyword screen flags **Oracle 0/75 versus NLA 5/75** on prose_paren, and **Oracle 0/75 versus NLA 19/75** on table_column. These are literal-term frequencies, not exhaustive semantic mention coding or state-value accuracy. They do not rescue the failed automatic measure. All300 typed judgments returned successfully;14 evidence-quality flags (Oracle parenthesis9, NLA column5) were retained as audit flags, not exclusions. Per-readout processing avoided E10-style batch attrition, but syntactic validity did not establish semantic validity.

Only the user-narrowed two-row matched sample was coded. §84's sealed NLA and unsealed Oracle partial were both excluded; a second sample waits for a complete sealed head-to-head. No further API send was made after this diagnostic. The prediction remains **unadjudicated by a valid automatic coder**; independent blinded validation or a separately registered replacement coder would be needed.

Reader identities were not supplied, but their output styles can still reveal them. The small, deliberately restricted test sample does not represent all W1 structure rows.
