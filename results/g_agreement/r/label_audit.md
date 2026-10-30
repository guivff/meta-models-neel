# Label-defect audit (uniform trigger, BRIEF_R Deviations WS3 2026-10-19)

Trigger: prompt-only AUROC < 0.5 or greedy accuracy below chance (0.5; 1/k for k-way), point estimates, test split. Every flagged fact is inspected (packet below) and reported both ways in every WS3 table; only inspected defects join LABEL_DEFECT and leave the BH families.

Facts audited: 223 (R-A 113, R-B 15, R-E 11, ReaderBench 55, R-X 29); flagged: 10.

| bank | fact | tag | prompt-only AUROC | greedy acc | chance | inspection | note |
|---|---|---|---|---|---|---|---|
| R-A | 131_temp_cat_Typical Time | None | 0.398 | 0.370 | 0.500 | not a defect | labels match (time-of-day vs how long / how often); Qwen calls frequency questions 'typical time' (WS3) |
| R-A | 140_news_class_Technology | None | 0.596 | 0.450 | 0.500 | defect | AG News names swapped (WS9 Check 1) |
| R-A | 142_cancer_cat_Thyroid_Cancer | None | 0.384 | 0.525 | 0.500 | not a defect | 98_cancer_cat classes match their names (thyroid terms 91% / colon 94% / lung 92%) but overlap heavily (WS3) |
| R-A | 144_cancer_cat_Colon_Cancer | None | 0.490 | 0.614 | 0.500 | not a defect | 98_cancer_cat classes match their names but overlap heavily (colon abstracts mention lung 75%) (WS3) |
| R-A | 145_disease_class_digestive system diseases | None | 0.462 | 0.450 | 0.500 | defect | 101_disease_class names permuted (WS3) |
| R-A | 146_disease_class_cardiovascular diseases | None | 0.366 | 0.365 | 0.500 | defect | 101_disease_class names permuted (WS3) |
| R-A | 153_it_tick_Administrative rights | None | 0.322 | 0.445 | 0.500 | not a defect | classes match their texts; Qwen does not call OS-upgrade tickets 'administrative rights' (WS3) |
| R-B | 101_disease_class | None | — | 0.160 | 0.200 | defect | 101_disease_class names permuted (WS3) |
| R-X | x25_wsb_wrong_bridge | None | 0.429 | 0.480 | 0.500 | not a defect | external bridge annotation; the question asks the model to introspect which bridge it used (WS3) |
| ReaderBench | rb_internal_puzzle_answer | None | 0.335 | 0.387 | 0.500 | not a defect | by design: label = correct endpoint vs the 2-step endpoint; Qwen's errors are systematic (README) (WS3) |

## Inspection packets (facts flagged and not yet inspected)

