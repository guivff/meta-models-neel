# E10 post-seal attrition audit (DESCRIPTIVE)

2026-10-24T05:11:26.554098+02:00; requested by Guiv. No new API, no changed annotation/type/selection.

| Stage | Lost pairs | Remaining pairs |
|---|---:|---:|
| Start | 0 | 3272 |
| One/both extractions invalid | 1631 | 1641 |
| Invalid matching | 704 | 937 |

All1500 API calls returned HTTP200. Extraction403/1309 invalid batches:397 nonverbatim evidence/claim,5 duplicate claims,1 ID failure. Matching44/100 invalid batches:35 reused claim index,9 invalid index. Classification4/90 invalid batches leaves256 untyped claims but removes no further pair. Of the937 complete pairs,44 had a deterministic empty matching because one side extracted zero claims.

The whole-batch rule excluded1612 unique readouts at extraction. Per-item diagnosis of the saved rejected batches identifies472 quote/evidence failures (Oracle366, NLA106),5 duplicate-claim failures (Oracle),1 ID failure (Oracle). **1134 individually valid readouts were discarded with their batch** (Oracle539,NLA595). These are diagnostics only: no salvage or rerun of the frozen analysis.

Extraction retained Oracle2235/3272 instances (**68.3%**) versus NLA2424/3272 (**74.1%**). Within W1 the rates were Oracle1021/1680 (60.8%) versus NLA1226/1680 (73.0%); within §61 Oracle1214/1592 (76.3%) versus NLA1198/1592 (75.3%). Complete-pair retention: W1415/1680 (**24.7%**), §61522/1592 (**32.8%**). Mean words among excluded/retained Oracle instances65.2/58.4; NLA100.5/101.9. Denominators include reused raw text across original cases; unique-text failure-trigger counts differ from instance retention counts.

**Bias assessment:** yes, potentially substantial. Shared surviving pairs prevent comparing different final denominators, but conditioning on both extractions and valid one-to-one matching selects the sample. Exact-quote validation is demonstrably asymmetric by reader; longer Oracle outputs were more often excluded. Non-equivalent/paraphrased quotations, claim density, repeated claims and one-to-many correspondences can affect inclusion; whole-batch rejection also removes unrelated valid outputs. Source composition shifts toward §61. This can change relative claim counts and content types. The direction/magnitude of bias in the final Oracle−NLA comparison cannot be identified from these diagnostics. E10 supports illustrations of the surviving outputs, not population information-content/accuracy rankings or an unbiased mechanism test. Stage failures are annotation failures, not reader failures.

Machine-readable counts: ATTRITION_DIAGNOSTIC.json. Original results/seals/selected IDs remain unchanged.
