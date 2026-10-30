# E89: placebo-likeness does not predict E67 claim failure

**R-H1 falsifier met for both readers:** both primary AUROCs are below0.55. The fixed classifier separates placebo from real readouts on the held-out training-domain validation set (AUROC0.907), but this does not transfer to predicting contradictions or lack of support on E67.

Code/plan committed as4eadcb4f before the one CPU fit and all E67 scoring. Authority §2015e5e3f40. No tuning, refit, judge/API/model-forward calls or original bank analysis reruns.

## Primary E89 test: both waves, matched judgments

| Reader | Outcome | n | Positive | AUROC | 95% item-bootstrap CI |
|---|---|---:|---:|---:|---|
| nla | contradicted | 499 | 475 | 0.433 | 0.323–0.540 |
| nla | no_supported | 499 | 154 | 0.475 | 0.423–0.530 |
| oracle | contradicted | 499 | 300 | 0.456 | 0.405–0.507 |
| oracle | no_supported | 499 | 197 | 0.475 | 0.423–0.525 |

Oracle and NLA each have499 readouts; no primary judgments are UNPARSEABLE. Positive score means more placebo-like. R-H1 requires contradiction AUROC≥0.65 with bootstrap lower bound>0.55, and no-supported AUROC≥0.65. Falsifier: both AUROCs<0.55.

## Within each wave

| Reader / wave | n | Contradicted AUROC | No-supported AUROC |
|---|---:|---:|---:|
| nla|wave1 | 299 | 0.491 | 0.483 |
| nla|wave2 | 200 | 0.403 | 0.470 |
| oracle|wave1 | 299 | 0.475 | 0.422 |
| oracle|wave2 | 200 | 0.423 | 0.550 |

## Within bank

| Reader / bank | n | Contradicted AUROC | No-supported AUROC |
|---|---:|---:|---:|
| nla|D4 | 99 | NE | 0.505 |
| nla|E49 | 100 | 0.402 | 0.436 |
| nla|E54 | 100 | 0.427 | 0.668 |
| nla|E56 | 100 | 0.406 | 0.473 |
| nla|E57 | 100 | 0.399 | 0.486 |
| oracle|D4 | 99 | 0.534 | 0.270 |
| oracle|E49 | 100 | 0.647 | 0.601 |
| oracle|E54 | 100 | 0.631 | 0.748 |
| oracle|E56 | 100 | 0.449 | 0.675 |
| oracle|E57 | 100 | 0.397 | 0.422 |

NLA/D4 contradiction AUROC is NOT EVALUABLE: all99 readouts have a contradicted claim. Small negative-class counts limit several other bank-specific estimates. Full CIs, class counts, excluded counts, NLA token-limit cohorts and mismatched-pair diagnostics are in RESULTS.json. E67’s original two wave analyses remain untouched.

## Top n-grams

Positive coefficients increase P(placebo-like); negative coefficients increase P(real-like). The full30 features in each direction are in TOP_NGRAMS.json. Character features retain literal whitespace; feature prefixes identify the vectorizer.

| Placebo-like feature | Weight | Real-like feature | Weight |
|---|---:|---|---:|
| `char__ &#124; ` | 2.8147 | `word__print` | -1.5460 |
| `word__of the` | 1.6846 | `word__answer` | -1.2845 |
| `word__of` | 1.1527 | `word__pass` | -1.1242 |
| `word__if` | 1.1083 | `char_____` | -1.0634 |
| `char__2: ` | 1.0859 | `word__please` | -1.0538 |
| `char__ 2:` | 1.0628 | `word__explanation` | -1.0270 |
| `word__100` | 1.0601 | `word__range` | -1.0236 |
| `word__river` | 1.0597 | `word__discuss` | -1.0226 |
| `char__ 2: ` | 1.0544 | `char______` | -1.0128 |
| `word__owner` | 1.0235 | `word__review` | -1.0011 |
| `word__no` | 1.0074 | `word__tense` | -0.9996 |
| `word__village` | 0.9948 | `word__what` | -0.9614 |
| `word__for` | 0.9943 | `word__notes` | -0.9458 |
| `word__throughout` | 0.9927 | `word__the notes` | -0.9416 |
| `word__the` | 0.9925 | `word__background` | -0.9253 |

## Fixed design and limits

One pooled classifier uses only readout text: word1–2 and char_wb3–5 TF-IDF, each l2-normalised, min_df2, equal union weights; L2 logistic C1, liblinear, no class weighting. Fit/IDF used only the training half. A seeded50/50 source-item split yields2309 training groups and2310 validation groups. Both readers, native/placebo records and paired random/shuffled vectors for a source item stay together. Excluding all E67 sampled identities removed652 records before splitting; no E67 test identity enters training or validation. Training has4312 real and972 placebo records; validation4328 real and976 placebo records. Eight synthetic tests pass.

E67 predictions and the fitted model were sealed before opening any judgment values. Both waves contain998 unique readouts (1996 matched/mismatched records). Source-item identities are disjoint; **73/998 test readout strings also occur in training** on other items. These repeated generic strings were retained without content filtering. Validation text duplicates can also reflect stereotyped output, so validation AUROC is a domain-separation diagnostic. Source-bank composition, generation lengths and reader styles may supply cues.

95% percentile intervals use2000 item-cluster bootstrap draws, seed20261028, conditional on this single fitted model; undefined one-class replicates are counted and omitted. The primary analysis pools waves only for the new E89 test and preserves separate wave/bank reports. Results describe association, not a causal detector of contradictory claims.

CPU scoring wall time: 4.708s; GPU-hours0. Raw text, private item mappings, per-item predictions/outcomes and fitted model remain in ignored CPU cache.
