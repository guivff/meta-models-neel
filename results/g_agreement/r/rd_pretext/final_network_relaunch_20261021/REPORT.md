# R-D: readers before explanatory text (BRIEF_R §42)

192 frozen test pairs, 384 prefills, 161 choice families.

At position (a), a probe fitted on prefilled pool states reads disagreement at 0.989 [0.979, 0.997], above prompt-only at (c) (0.897), while the best reader (AO, 0.828) is mostly prior (shuffled 0.745).

The primary metric is pooled AUROC for identifying a dispreferred prefill. Intervals retain both prefills in every paired draw and quote the conservative item/family envelope.

2,000 attempts per scheme, seed 0. Reader tests are unadjusted; there is no family-wise or false-discovery guarantee.

| Position | Attempted prefills | Complete scored prefills | Saved/expected score cells | Declared failed test prefills | Declared failed pool prefills | Status |
|---|---:|---:|---:|---:|---:|---|
| a | 384 | 384 | 3840/3840 | 0 | 0 | COMPLETE |
| b | 384 | 0 | 0/4224 | 1 | 0 | MISSING_POSITION |
| c | 384 | 384 | 4224/4224 | 0 | 0 | COMPLETE |

| Position | Arm | AUROC | Wider 95% CI | Verdict |
|---|---|---:|---|---|
| a | oracle/natural | 0.6475 | [0.5750, 0.7232] | UNDERPOWERED/MIXED |
| a | oracle/shuffled | 0.5089 | [0.4346, 0.5814] | descriptive baseline |
| a | ao/natural | 0.8282 | [0.7753, 0.8791] | UNDERPOWERED/MIXED |
| a | ao/shuffled | 0.7451 | [0.6897, 0.7945] | descriptive baseline |
| a | nla/natural | 0.5594 | [0.5041, 0.6176] | UNDERPOWERED/MIXED |
| a | nla/shuffled | 0.4867 | [0.4360, 0.5406] | descriptive baseline |
| a | jpp_conflict/natural | 0.5000 | [0.5000, 0.5000] | UNDERPOWERED/MIXED |
| a | jpp_conflict/shuffled | 0.5000 | [0.5000, 0.5000] | descriptive baseline |
| a | probe/L44 | 0.9893 | [0.9794, 0.9967] | descriptive baseline |
| a | text_judge | 0.6155 | [0.5686, 0.6609] | descriptive baseline |
| b | oracle/natural | unavailable | unavailable | MISSING_POSITION |
| b | oracle/shuffled | unavailable | unavailable | MISSING_POSITION |
| b | ao/natural | unavailable | unavailable | MISSING_POSITION |
| b | ao/shuffled | unavailable | unavailable | MISSING_POSITION |
| b | nla/natural | unavailable | unavailable | MISSING_POSITION |
| b | nla/shuffled | unavailable | unavailable | MISSING_POSITION |
| b | jpp_conflict/natural | unavailable | unavailable | MISSING_POSITION |
| b | jpp_conflict/shuffled | unavailable | unavailable | MISSING_POSITION |
| b | probe/L44 | unavailable | unavailable | MISSING_POSITION |
| b | text_judge | unavailable | unavailable | MISSING_POSITION |
| b | prompt_only | unavailable | unavailable | MISSING_POSITION |
| c | oracle/natural | 0.6409 | [0.5973, 0.6824] | DESCRIPTIVE SECONDARY POSITION |
| c | oracle/shuffled | 0.5179 | [0.4671, 0.5663] | descriptive baseline |
| c | ao/natural | 0.8247 | [0.7723, 0.8715] | DESCRIPTIVE SECONDARY POSITION |
| c | ao/shuffled | 0.7879 | [0.7308, 0.8400] | descriptive baseline |
| c | nla/natural | 0.5245 | [0.4722, 0.5766] | DESCRIPTIVE SECONDARY POSITION |
| c | nla/shuffled | 0.4767 | [0.4204, 0.5349] | descriptive baseline |
| c | jpp_conflict/natural | 0.5000 | [0.5000, 0.5000] | DESCRIPTIVE SECONDARY POSITION |
| c | jpp_conflict/shuffled | 0.5000 | [0.5000, 0.5000] | descriptive baseline |
| c | probe/L44 | 0.9217 | [0.8891, 0.9502] | descriptive baseline |
| c | text_judge | 0.6151 | [0.5546, 0.6705] | descriptive baseline |
| c | prompt_only | 0.8965 | [0.8656, 0.9250] | descriptive baseline |

| Position | Reader | Comparator | AUROC difference | Wider 95% CI | Wider 90% CI |
|---|---|---|---:|---|---|
| a | oracle | text_judge | 0.0321 | [-0.0678, 0.1376] | [-0.0522, 0.1206] |
| a | oracle | shuffled | 0.1386 | [0.0512, 0.2238] | [0.0663, 0.2106] |
| a | oracle | probe/L44 | -0.3418 | [-0.4149, -0.2659] | [-0.4018, -0.2792] |
| a | ao | text_judge | 0.2128 | [0.1560, 0.2703] | [0.1643, 0.2617] |
| a | ao | shuffled | 0.0832 | [0.0445, 0.1242] | [0.0508, 0.1164] |
| a | ao | probe/L44 | -0.1611 | [-0.2131, -0.1129] | [-0.2051, -0.1211] |
| a | nla | text_judge | -0.0560 | [-0.1393, 0.0305] | [-0.1261, 0.0175] |
| a | nla | shuffled | 0.0727 | [0.0158, 0.1286] | [0.0267, 0.1188] |
| a | nla | probe/L44 | -0.4299 | [-0.4858, -0.3718] | [-0.4780, -0.3812] |
| a | jpp_conflict | text_judge | -0.1155 | [-0.1609, -0.0686] | [-0.1529, -0.0751] |
| a | jpp_conflict | shuffled | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| a | jpp_conflict | probe/L44 | -0.4893 | [-0.4967, -0.4794] | [-0.4958, -0.4813] |
| c | oracle | text_judge | 0.0258 | [-0.0483, 0.1030] | [-0.0361, 0.0920] |
| c | oracle | shuffled | 0.1230 | [0.0591, 0.1856] | [0.0696, 0.1766] |
| c | oracle | probe/L44 | -0.2808 | [-0.3239, -0.2362] | [-0.3171, -0.2443] |
| c | oracle | prompt_only | -0.2556 | [-0.3062, -0.2060] | [-0.2959, -0.2140] |
| c | ao | text_judge | 0.2096 | [0.1550, 0.2677] | [0.1629, 0.2580] |
| c | ao | shuffled | 0.0368 | [0.0045, 0.0688] | [0.0100, 0.0642] |
| c | ao | probe/L44 | -0.0970 | [-0.1529, -0.0447] | [-0.1451, -0.0533] |
| c | ao | prompt_only | -0.0718 | [-0.1165, -0.0310] | [-0.1098, -0.0365] |
| c | nla | text_judge | -0.0906 | [-0.1510, -0.0287] | [-0.1417, -0.0360] |
| c | nla | shuffled | 0.0479 | [-0.0181, 0.1148] | [-0.0079, 0.1041] |
| c | nla | probe/L44 | -0.3972 | [-0.4597, -0.3354] | [-0.4495, -0.3448] |
| c | nla | prompt_only | -0.3719 | [-0.4361, -0.3097] | [-0.4258, -0.3187] |
| c | jpp_conflict | text_judge | -0.1151 | [-0.1705, -0.0546] | [-0.1625, -0.0651] |
| c | jpp_conflict | shuffled | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| c | jpp_conflict | probe/L44 | -0.4217 | [-0.4502, -0.3891] | [-0.4460, -0.3949] |
| c | jpp_conflict | prompt_only | -0.3965 | [-0.4250, -0.3656] | [-0.4210, -0.3714] |

Only position a earns the primary claim: reader minus text judge must have a 95% lower bound above 0.10, and reader minus shuffled state must have a 95% lower bound above 0.05. Positions b and c are descriptive; they cannot rescue a failed primary rule.

Prompt-only is structurally absent at a; no zero score is substituted. Text judge is evaluated at a. Probe comparisons condition on the separate frozen pool fit for that position.

Position b is unavailable for the full cohort. Saved successful-prefill rows are counted above but never used for a complete-case AUROC. The declared boundary failures are retained in analysis.json; positions a and c retain their complete paired cohorts.
