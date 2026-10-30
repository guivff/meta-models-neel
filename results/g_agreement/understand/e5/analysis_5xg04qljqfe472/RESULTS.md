**Prediction (§92):** Oracle structure stays near chance under all eight phrasings; meaning stays near ceiling.

**Did it hold? Partly. The all-phrasings structure prediction did not hold:** Python bracket depth reaches 0.784 (paraphrase1) and 0.776 (paraphrase2), above the brief’s 0.75 surprise point. Table-column best is 0.713 and parentheses best is 0.598. Oracle meaning remains high (0.853–1.000 across the three rows).

# E5 phrasing results — EXPLORATORY

Six rows × 84 held-out items; each row has 42/value across six template clusters. All eight frozen phrasings are reported with 2,000 cluster-bootstrap CIs, fixed score orientation. Best phrasing and spread are descriptive selections on the same test set, with selection optimism and no multiplicity correction. J-lens is unsupported for all six rows × eight sequence-query phrasings under the unchanged W1 scorer; no chance values are substituted.

| Row | Reader | Best phrasing | Best AUROC | Max − min |
|---|---|---|---|---|
| table_column | olens | paraphrase2 | 0.713 | 0.382 |
| table_column | nla | direct_question | 0.810 | 0.489 |
| table_column | jlens | UNSUPPORTED | — | — |
| prose_paren | olens | plain_value2 | 0.598 | 0.118 |
| prose_paren | nla | plain_value2 | 0.899 | 0.317 |
| prose_paren | jlens | UNSUPPORTED | — | — |
| python_depth | olens | paraphrase1 | 0.784 | 0.454 |
| python_depth | nla | reader_native | 0.861 | 0.432 |
| python_depth | jlens | UNSUPPORTED | — | — |
| prose_sentiment | olens | direct_question | 1.000 | 0.044 |
| prose_sentiment | nla | direct_question | 1.000 | 0.272 |
| prose_sentiment | jlens | UNSUPPORTED | — | — |
| prose_topic | olens | direct_question | 1.000 | 0.000 |
| prose_topic | nla | paraphrase2 | 1.000 | 0.231 |
| prose_topic | jlens | UNSUPPORTED | — | — |
| python_error | olens | statement | 1.000 | 0.147 |
| python_error | nla | direct_question | 1.000 | 0.050 |
| python_error | jlens | UNSUPPORTED | — | — |

| Row | Reader | Phrasing | AUROC [95% cluster CI] |
|---|---|---|---|
| table_column | olens | 0: direct_question | 0.463 [0.252, 0.683] |
| table_column | olens | 1: statement | 0.330 [0.188, 0.451] |
| table_column | olens | 2: reader_native | 0.568 [0.400, 0.721] |
| table_column | olens | 3: which_more_likely | 0.332 [0.215, 0.495] |
| table_column | olens | 4: paraphrase1 | 0.707 [0.524, 0.896] |
| table_column | olens | 5: paraphrase2 | 0.713 [0.559, 0.884] |
| table_column | olens | 6: plain_value1 | 0.502 [0.391, 0.624] |
| table_column | olens | 7: plain_value2 | 0.367 [0.245, 0.480] |
| table_column | nla | 0: direct_question | 0.810 [0.785, 0.908] |
| table_column | nla | 1: statement | 0.554 [0.379, 0.751] |
| table_column | nla | 2: reader_native | 0.626 [0.503, 0.760] |
| table_column | nla | 3: which_more_likely | 0.604 [0.430, 0.829] |
| table_column | nla | 4: paraphrase1 | 0.657 [0.443, 0.817] |
| table_column | nla | 5: paraphrase2 | 0.517 [0.416, 0.640] |
| table_column | nla | 6: plain_value1 | 0.321 [0.100, 0.616] |
| table_column | nla | 7: plain_value2 | 0.437 [0.256, 0.601] |
| prose_paren | olens | 0: direct_question | 0.570 [0.311, 0.799] |
| prose_paren | olens | 1: statement | 0.540 [0.311, 0.800] |
| prose_paren | olens | 2: reader_native | 0.549 [0.316, 0.834] |
| prose_paren | olens | 3: which_more_likely | 0.479 [0.229, 0.791] |
| prose_paren | olens | 4: paraphrase1 | 0.552 [0.365, 0.767] |
| prose_paren | olens | 5: paraphrase2 | 0.516 [0.346, 0.715] |
| prose_paren | olens | 6: plain_value1 | 0.511 [0.346, 0.659] |
| prose_paren | olens | 7: plain_value2 | 0.598 [0.364, 0.835] |
| prose_paren | nla | 0: direct_question | 0.841 [0.657, 0.980] |
| prose_paren | nla | 1: statement | 0.581 [0.468, 0.773] |
| prose_paren | nla | 2: reader_native | 0.722 [0.553, 0.900] |
| prose_paren | nla | 3: which_more_likely | 0.597 [0.498, 0.739] |
| prose_paren | nla | 4: paraphrase1 | 0.813 [0.702, 0.963] |
| prose_paren | nla | 5: paraphrase2 | 0.673 [0.533, 0.878] |
| prose_paren | nla | 6: plain_value1 | 0.666 [0.472, 0.866] |
| prose_paren | nla | 7: plain_value2 | 0.899 [0.735, 1.000] |
| python_depth | olens | 0: direct_question | 0.330 [0.256, 0.395] |
| python_depth | olens | 1: statement | 0.556 [0.501, 0.645] |
| python_depth | olens | 2: reader_native | 0.523 [0.430, 0.620] |
| python_depth | olens | 3: which_more_likely | 0.603 [0.525, 0.689] |
| python_depth | olens | 4: paraphrase1 | 0.784 [0.769, 0.822] |
| python_depth | olens | 5: paraphrase2 | 0.776 [0.699, 0.857] |
| python_depth | olens | 6: plain_value1 | 0.687 [0.620, 0.761] |
| python_depth | olens | 7: plain_value2 | 0.726 [0.690, 0.798] |
| python_depth | nla | 0: direct_question | 0.429 [0.368, 0.482] |
| python_depth | nla | 1: statement | 0.628 [0.510, 0.781] |
| python_depth | nla | 2: reader_native | 0.861 [0.798, 0.916] |
| python_depth | nla | 3: which_more_likely | 0.569 [0.489, 0.656] |
| python_depth | nla | 4: paraphrase1 | 0.727 [0.653, 0.834] |
| python_depth | nla | 5: paraphrase2 | 0.655 [0.599, 0.707] |
| python_depth | nla | 6: plain_value1 | 0.474 [0.384, 0.549] |
| python_depth | nla | 7: plain_value2 | 0.558 [0.468, 0.694] |
| prose_sentiment | olens | 0: direct_question | 1.000 [1.000, 1.000] |
| prose_sentiment | olens | 1: statement | 1.000 [1.000, 1.000] |
| prose_sentiment | olens | 2: reader_native | 1.000 [1.000, 1.000] |
| prose_sentiment | olens | 3: which_more_likely | 1.000 [1.000, 1.000] |
| prose_sentiment | olens | 4: paraphrase1 | 0.980 [0.920, 1.000] |
| prose_sentiment | olens | 5: paraphrase2 | 0.956 [0.881, 1.000] |
| prose_sentiment | olens | 6: plain_value1 | 0.991 [0.964, 1.000] |
| prose_sentiment | olens | 7: plain_value2 | 1.000 [1.000, 1.000] |
| prose_sentiment | nla | 0: direct_question | 1.000 [1.000, 1.000] |
| prose_sentiment | nla | 1: statement | 1.000 [1.000, 1.000] |
| prose_sentiment | nla | 2: reader_native | 1.000 [1.000, 1.000] |
| prose_sentiment | nla | 3: which_more_likely | 0.985 [0.948, 1.000] |
| prose_sentiment | nla | 4: paraphrase1 | 0.728 [0.454, 0.963] |
| prose_sentiment | nla | 5: paraphrase2 | 0.789 [0.672, 0.990] |
| prose_sentiment | nla | 6: plain_value1 | 0.904 [0.730, 1.000] |
| prose_sentiment | nla | 7: plain_value2 | 0.962 [0.723, 1.000] |
| prose_topic | olens | 0: direct_question | 1.000 [1.000, 1.000] |
| prose_topic | olens | 1: statement | 1.000 [1.000, 1.000] |
| prose_topic | olens | 2: reader_native | 1.000 [1.000, 1.000] |
| prose_topic | olens | 3: which_more_likely | 1.000 [1.000, 1.000] |
| prose_topic | olens | 4: paraphrase1 | 1.000 [1.000, 1.000] |
| prose_topic | olens | 5: paraphrase2 | 1.000 [1.000, 1.000] |
| prose_topic | olens | 6: plain_value1 | 1.000 [1.000, 1.000] |
| prose_topic | olens | 7: plain_value2 | 1.000 [1.000, 1.000] |
| prose_topic | nla | 0: direct_question | 0.997 [0.989, 1.000] |
| prose_topic | nla | 1: statement | 0.977 [0.939, 1.000] |
| prose_topic | nla | 2: reader_native | 0.968 [0.916, 1.000] |
| prose_topic | nla | 3: which_more_likely | 0.958 [0.830, 1.000] |
| prose_topic | nla | 4: paraphrase1 | 0.972 [0.908, 1.000] |
| prose_topic | nla | 5: paraphrase2 | 1.000 [1.000, 1.000] |
| prose_topic | nla | 6: plain_value1 | 0.994 [0.977, 1.000] |
| prose_topic | nla | 7: plain_value2 | 0.769 [0.677, 0.921] |
| python_error | olens | 0: direct_question | 0.853 [0.738, 0.986] |
| python_error | olens | 1: statement | 1.000 [1.000, 1.000] |
| python_error | olens | 2: reader_native | 1.000 [1.000, 1.000] |
| python_error | olens | 3: which_more_likely | 1.000 [1.000, 1.000] |
| python_error | olens | 4: paraphrase1 | 1.000 [1.000, 1.000] |
| python_error | olens | 5: paraphrase2 | 1.000 [1.000, 1.000] |
| python_error | olens | 6: plain_value1 | 0.989 [0.966, 1.000] |
| python_error | olens | 7: plain_value2 | 0.997 [0.986, 1.000] |
| python_error | nla | 0: direct_question | 1.000 [1.000, 1.000] |
| python_error | nla | 1: statement | 0.950 [0.898, 0.999] |
| python_error | nla | 2: reader_native | 0.996 [0.990, 1.000] |
| python_error | nla | 3: which_more_likely | 1.000 [1.000, 1.000] |
| python_error | nla | 4: paraphrase1 | 1.000 [1.000, 1.000] |
| python_error | nla | 5: paraphrase2 | 1.000 [1.000, 1.000] |
| python_error | nla | 6: plain_value1 | 1.000 [1.000, 1.000] |
| python_error | nla | 7: plain_value2 | 0.984 [0.957, 1.000] |

The NLA is also phrasing-sensitive: its best structural AUROCs are 0.810 (table), 0.899 (parenthesis), 0.861 (depth). This is exploratory best-of-eight performance, not a replacement for the registered W1 verdict or a held-out prompt-selection result.

Provenance: pod `5xg04qljqfe472`, booking `ac397e81`, exact frozen source `19fadde5`. Input/score seals, source hashes and complete grids verified before labels. CPU-only analysis ran once per experiment in requested order E6 → E5 → E8. Pre-registered designs and scoring definitions are exploratory; no registered W1/§84/§87 verdict is changed. E6/E8 use a new CPU reporting adapter for their already-frozen proxy/gain functions; E5 uses its unchanged frozen analyser. No new model inference or paid calls.
