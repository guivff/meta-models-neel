# WR-2-LF — fixed token combinations and surface variants do not close the naming gap

**Final report — 2026-10-19 22:49 Europe/Zurich. Verdict: REFUTED AT THE REGISTERED 50% RECOVERY THRESHOLD for all four pooled label-free readouts.** Across the same 88 held-out facts, the largest observed median gain is **+0.00045 AUC, 95% CI [−0.01225, +0.00945]**, for mean-of-variant token means. That is **0.26% of the fixed 0.174 naming gap**, with 95% CI [−7.04%, +5.43%]. Its Bonferroni-adjusted 98.75% per-arm CI is [−0.01680, +0.01280], or [−9.66%, +7.36%] of the gap. Every pooled arm’s adjusted upper bound is below the required 50%. The rule required gain≥0.087 and lower bound>0.0435; no arm approaches it.

No tag supports closure. SURFACE, KNOWLEDGE, COMPUTED and PASSAGE-KNOWLEDGE refute 50% recovery for every arm even after the four-arm adjustment. TOPIC does so for three arms; variant_mean is UNDERPOWERED after adjustment (nominally refuted). FORM is UNDERPOWERED for all arms; META has no evaluation facts.

The labelled-probe result from WR-2 remains intact. These specific label-free recipes fail to recover its advantage. They are order-insensitive linear token aggregations, not sequential phrase generation, and their failure does not rule out a learned or generative multi-token reader.

## Pooled readout results

Each gain is the median of per-fact paired AUC differences against the exact frozen native score. Recovery divides that gain by the fixed 0.174, including for tags. CIs use 10,000 paired item draws and both fact→item and source-corpus→fact→item resampling; each quoted interval is the wider of the two at that coverage. Seeds are averaged as five separate probe AUCs, never treated as independent test items.

| Readout | Gain [95% CI] | Bonferroni 98.75% per-arm CI | Recovery of 0.174 [95% CI] | Adjusted verdict |
|---|---|---|---|---|
| Full candidate: sum | -0.00050 [-0.01060, +0.00340] | [-0.01453, +0.00650] | -0.29% [-6.09%, +1.95%] | REFUTED at 50% |
| Full candidate: mean | +0.00000 [-0.00810, +0.00520] | [-0.01143, +0.00840] | +0.00% [-4.66%, +2.99%] | REFUTED at 50% |
| Variants: mean of sums | -0.00550 [-0.03065, +0.00530] | [-0.03955, +0.00888] | -3.16% [-17.62%, +3.05%] | REFUTED at 50% |
| Variants: mean of means | +0.00045 [-0.01225, +0.00945] | [-0.01680, +0.01280] | +0.26% [-7.04%, +5.43%] | REFUTED at 50% |

The nominal and adjusted pooled verdicts agree for all four arms. The four Bonferroni intervals provide at least 95% simultaneous coverage across the four arms and protect the “any of four arms closes” headline; 98.75% is the per-arm coverage. Tag adjustments apply within each tag; the tag table is not a familywise discovery test across all tags.

## Verdicts by tag

The threshold is the same absolute gain in every row: +0.087, with lower bound>+0.0435. It is not recalibrated to each tag’s original probe gap. FORM has six facts; SURFACE and KNOWLEDGE have only two source groups each, PASSAGE-KNOWLEDGE one. All intervals and small-sample flags remain visible.

| Tag | Facts / corpora | Arm | Gain [95% CI] | Bonferroni 98.75% per-arm CI | Nominal / adjusted verdict |
|---|---:|---|---|---|---|
| SURFACE | 22 / 2 | canonical_sum | +0.00665 [-0.03500, +0.05120] | [-0.04768, +0.05838] | REFUTED at 50% / REFUTED at 50% |
| SURFACE | 22 / 2 | canonical_mean | +0.00665 [-0.03500, +0.05120] | [-0.04768, +0.05838] | REFUTED at 50% / REFUTED at 50% |
| SURFACE | 22 / 2 | variant_sum | +0.00880 [-0.01165, +0.02945] | [-0.01730, +0.03648] | REFUTED at 50% / REFUTED at 50% |
| SURFACE | 22 / 2 | variant_mean | +0.00540 [-0.01725, +0.02480] | [-0.01908, +0.03468] | REFUTED at 50% / REFUTED at 50% |
| KNOWLEDGE | 18 / 2 | canonical_sum | +0.00000 [-0.01575, +0.02150] | [-0.02280, +0.03448] | REFUTED at 50% / REFUTED at 50% |
| KNOWLEDGE | 18 / 2 | canonical_mean | +0.00000 [-0.01575, +0.02150] | [-0.02280, +0.03448] | REFUTED at 50% / REFUTED at 50% |
| KNOWLEDGE | 18 / 2 | variant_sum | -0.01080 [-0.04730, +0.00890] | [-0.05543, +0.01550] | REFUTED at 50% / REFUTED at 50% |
| KNOWLEDGE | 18 / 2 | variant_mean | -0.00510 [-0.02640, +0.00925] | [-0.03675, +0.01235] | REFUTED at 50% / REFUTED at 50% |
| TOPIC | 17 / 10 | canonical_sum | -0.00100 [-0.02965, +0.00890] | [-0.06183, +0.01573] | REFUTED at 50% / REFUTED at 50% |
| TOPIC | 17 / 10 | canonical_mean | +0.00000 [-0.00510, +0.02265] | [-0.00888, +0.03903] | REFUTED at 50% / REFUTED at 50% |
| TOPIC | 17 / 10 | variant_sum | -0.01200 [-0.05530, +0.01590] | [-0.10658, +0.03895] | REFUTED at 50% / REFUTED at 50% |
| TOPIC | 17 / 10 | variant_mean | -0.00170 [-0.00880, +0.05740] | [-0.01435, +0.10873] | REFUTED at 50% / UNDERPOWERED |
| COMPUTED | 16 / 12 | canonical_sum | -0.00355 [-0.02930, +0.00650] | [-0.04055, +0.01325] | REFUTED at 50% / REFUTED at 50% |
| COMPUTED | 16 / 12 | canonical_mean | -0.00355 [-0.02980, +0.00420] | [-0.04103, +0.00950] | REFUTED at 50% / REFUTED at 50% |
| COMPUTED | 16 / 12 | variant_sum | -0.03030 [-0.07500, +0.00315] | [-0.08875, +0.00958] | REFUTED at 50% / REFUTED at 50% |
| COMPUTED | 16 / 12 | variant_mean | -0.01100 [-0.04660, +0.01065] | [-0.05540, +0.01708] | REFUTED at 50% / REFUTED at 50% |
| PASSAGE-KNOWLEDGE | 9 / 1 | canonical_sum | +0.00290 [-0.07150, +0.03150] | [-0.10195, +0.03800] | REFUTED at 50% / REFUTED at 50% |
| PASSAGE-KNOWLEDGE | 9 / 1 | canonical_mean | +0.00290 [-0.07150, +0.03150] | [-0.10195, +0.03800] | REFUTED at 50% / REFUTED at 50% |
| PASSAGE-KNOWLEDGE | 9 / 1 | variant_sum | +0.01040 [-0.09510, +0.05090] | [-0.12126, +0.06410] | REFUTED at 50% / REFUTED at 50% |
| PASSAGE-KNOWLEDGE | 9 / 1 | variant_mean | +0.00680 [-0.06200, +0.04350] | [-0.08305, +0.05545] | REFUTED at 50% / REFUTED at 50% |
| FORM | 6 / 6 | canonical_sum | -0.02945 [-0.20066, +0.19220] | [-0.25415, +0.32982] | UNDERPOWERED / UNDERPOWERED |
| FORM | 6 / 6 | canonical_mean | -0.02945 [-0.25885, +0.19220] | [-0.37533, +0.32982] | UNDERPOWERED / UNDERPOWERED |
| FORM | 6 / 6 | variant_sum | -0.01200 [-0.07595, +0.18506] | [-0.08648, +0.29655] | UNDERPOWERED / UNDERPOWERED |
| FORM | 6 / 6 | variant_mean | -0.01920 [-0.16121, +0.21575] | [-0.24210, +0.30364] | UNDERPOWERED / UNDERPOWERED |
| META | 0 / 0 | all four | — | — | NOT EVALUATED |

## Controls and remaining probe advantage

Marginal median AUCs are descriptive and must not be subtracted to reconstruct the median paired gains above.

| Arm | Median AUC [95% CI] | Remaining paired probe gap [95% CI] | Shuffled-state AUC [95% CI] |
|---|---|---|---|
| Frozen native | 0.64510 [+0.58280, +0.72130] | — | — |
| Full-J probe(256) | 0.86805 [+0.81726, +0.92498] | — | — |
| canonical_sum | 0.61885 [+0.57300, +0.70615] | +0.19908 [+0.13188, +0.25300] | 0.49887 [+0.49023, +0.50529] |
| canonical_mean | 0.62165 [+0.57505, +0.72045] | +0.18602 [+0.12218, +0.24984] | 0.49887 [+0.48999, +0.50533] |
| variant_sum | 0.61325 [+0.57480, +0.68520] | +0.21728 [+0.14023, +0.26705] | 0.49941 [+0.49075, +0.50630] |
| variant_mean | 0.63990 [+0.58239, +0.73155] | +0.17339 [+0.12702, +0.23709] | 0.50139 [+0.49067, +0.50654] |

All shuffled-state pooled 95% intervals include 0.5. Variant averaging itself gives median variant-minus-canonical gain −0.01275 [−0.02660,+0.00190] for sums and −0.00030 [−0.01180,+0.00855] for means. All 100 sensitivity and calibration 12 diagnostic populations also refute 50% recovery for every readout; they do not replace the 88-fact endpoint.

## Vocabulary alignment

Alignment is a label-assisted diagnostic, separate from label-free scoring. Refit each exact n256 pool probe, undo StandardScaler using beta=coef/scale, then compare its unit direction with unit W_U rows. The table takes the median of each fact’s mean over five seeds. These are descriptive geometry summaries, not held-out performance CIs or an equivalence test.

| Group | Real-probe nearest positive cosine | Real-probe nearest absolute cosine | Shuffled-probe nearest positive cosine |
|---|---:|---:|---:|
| All 88 | 0.07703 | 0.08050 | 0.07044 |
| SURFACE | 0.07779 | 0.08050 | 0.07152 |
| KNOWLEDGE | 0.08078 | 0.08580 | 0.07075 |
| TOPIC | 0.07427 | 0.07926 | 0.06971 |
| COMPUTED | 0.07510 | 0.08079 | 0.07083 |
| PASSAGE-KNOWLEDGE | 0.07886 | 0.08201 | 0.07007 |
| FORM | 0.07602 | 0.07788 | 0.06917 |

The 128 isotropic unit directions have median nearest positive cosine 0.06144, with empirical 2.5–97.5% quantiles [0.05532,0.07129]. This is a reference distribution over random directions, not a 95% CI for semantic alignment. The search includes 248,060 tokenizer-known non-special W_U rows; signed negative extremes, absolute extremes and the top 10 token names per seed are in the CSVs.

**Low individual-token cosine does not establish “no token readout can ever name the fact.”** Predictive separation depends on state covariance as well as angle. Token contrasts, sums and nonlinear decoders need not align with any one W_U row. No threshold defining “low” was registered. The full J map is numerically full rank, and WR-2 found substantial decodability in matched-rank random subspaces (its pooled Haar384 probe median AUC 0.84491). Recoverability is therefore not evidence for a uniquely privileged J subspace, and neither experiment establishes causal model use. The isotropic-direction and shuffled-probe controls here are not a new random-subspace experiment.

## Frozen protocol, provenance and validation

- Preregistered BRIEF_R §17 and complete variant list were committed/pushed in `5f981bd6e50603d29ea4317e593a66553c306005` before scoring. Implementation was committed in `29466aa`; technical repair in `8bcf3c8` before held-out scores or alignment fits. No scientific rule changed.
- Same frozen 100 eligible facts, 88 evaluation/12 calibration, 17,600 evaluation test items. The one existing calibration duplicate exclusion leaves 19,999 total test rows. LABEL_DEFECT exclusions, polarity, source groups and exact n256 training draws are unchanged.
- 131 active candidates; 87 are multi-token under the local tokenizer, maximum canonical length 5. All 1,420 active explicit surface strings were committed before scoring. Literal-bigram meanings and proper names were protected from inappropriate synonyms/plurals.
- Native per-token score is (Jh·W_t)/||W_tJ||. Canonical strings have one leading space; variants use their exact frozen strings. Repeated tokens count repeatedly. Variant means weight each complete string equally. One-sided facts use A; two-sided facts A−B. No token, variant, polarity or model hyperparameter was selected on test outcomes.
- All assets were local and hashed. Since Jh arrays and probe coefficients were not retained by WR-2, deterministic mapping was reconstructed from the same cached h/J, and only the alignment probes were refitted. No target model, download, generation or accelerator was used.
- Native parity PASS on all 768 calibration-validation rows: max score error 0.00002933, every AUC difference 0. All 1000 real/shuffled refits completed, max 234 iterations, and every saved test prediction was reproduced exactly (max error 0).
- All 100 facts have finite scores and complete provenance. Synthetic checks cover actual native-score API types, repeated-token/equal-surface weighting, polarity, raw-coefficient coordinates, top-k ties, tied weighted AUC, paired resampling, exact threshold boundaries and incomplete-input rejection. Independent artifact/CSV/bootstrap audits accompany the run.
- Technical repair: the first calibration audit stopped because an ndarray was given a pandas-only `.to_numpy()` call. `np.asarray` fixed it; the failed stage and repeated preparation remain in the ledger. No endpoint outcome had run or been inspected. The dated note is in §17.

## Compute and reproduction

Instrumented analysis totals **141.001 CPU seconds (0.03917 CPU-core hours)** and 97.178 summed stage wall seconds, including the failed audit and repeated preparation. This excludes interpreter startup, engineering, report formatting and small independent verification commands, which are separately logged. GPU usage is **0 hours**. Two workers with one BLAS thread each completed every fit loop well below 30 min; the registered 4 CPU-core-hour cap was not approached.

```sh
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_lf_score --self-test
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_lf_infer --self-test
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_lf_score --registration-commit 5f981bd6e50603d29ea4317e593a66553c306005 --stage all --workers 2
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_lf_infer --registration-commit 5f981bd6e50603d29ea4317e593a66553c306005 --workers 2
```

## Deliverables

- `wr2_lf_variants.json`, `wr2_lf_tokens.json`: committed surfaces, token sequences and hashes.
- `wr2_lf_facts.csv`, `wr2_lf_groups.csv`, `wr2_lf_controls.csv`, `wr2_lf_inference.json`: all estimates, both CI methods, recovery fractions, nominal/adjusted verdicts and controls.
- `wr2_lf_alignment_seeds.csv`, `wr2_lf_alignment_neighbors.csv`, `wr2_lf_alignment_null.csv`, `wr2_lf_alignment_facts.csv`, `wr2_lf_alignment_groups.csv`, `wr2_lf_alignment.json`: every cosine extreme, nearest vocabulary row and descriptive group summary.
- `wr2_lf_refits.csv`, `wr2_lf_audit.json`, `wr2_lf_verification.json`: alignment convergence/parity, native parity and independent verification.
- Large predictions, directions and bootstrap arrays: ignored `cache/g_agreement/r/i2/wr2_lf/`. Original WR-2 results and the main checkout/cache link are unchanged.
