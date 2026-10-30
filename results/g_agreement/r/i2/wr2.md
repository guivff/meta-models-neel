> Latest Stage 2 run (2026-10-20 02:37 Europe/Zurich): **INCONCLUSIVE_H_CONTROL_FAILURE**. All 15 CPU fits completed on the audited 525-pool/256-test partition; Jh, h and all controls scored 0/256 per seed. Jh-control and donor gains are 0 pp (paired 95% CIs [0, 0]); these intervals are degenerate because all observed successes are zero. The failed h positive control prevents an information-loss conclusion. See [the final learned-decoder report and evidence](wr2_decoder.md).

# WR-2 — J-lens misses retain decodable information in the full map

**Final report — 2026-10-19 20:02 CEST. Verdict: SUPPORTED at the registered 256-label budget.** Across the 88 held-out R-A facts, the median full-map-probe gain over the native J score is **+0.174 [+0.122, +0.239] AUC (95% CI)**. The original-state minus full-map probe loss is **+0.008 [+0.004, +0.014] (90% CI)**, entirely inside the registered ±0.03 equivalence margin. **KNOWLEDGE and SURFACE independently pass the same naming and map-equivalence gates**, with 18 and 22 facts respectively. This satisfies the pooled gate and the requirement for at least two tags with eight facts each.

The information is still available to a labelled linear decoder of Jh in these comparisons; the frozen native score misses it. This supports a naming bottleneck and motivates a multi-token J-lens. It does **not** evaluate a multi-token decoder, establish success on every individual fact, or show which information the target model uses. The measured native endpoint is the frozen single-token **fixed-candidate score**, not unrestricted top-token name generation.

**Rank truncation is a separate result: the registered material bottleneck is REFUTED.** The median full-map minus rank-384-probe loss is +0.008 [+0.003, +0.017] (95% CI), well below the ≥0.10 threshold. Its excess over matched-rank Haar loss is +0.000 [-0.006, +0.003]. A small positive truncation loss exists; it does not meet the registered effect size or excess-over-Haar rule.

## Verdicts by held-out fact group

All values are medians of within-fact contrasts after averaging five separate seed AUCs. Naming and truncation intervals are 95%; map-loss intervals are 90% for equivalence. Each quoted interval is the wider of the iid and source-corpus bootstrap intervals; both versions are retained in the CSV. These contrasts are not differences between the marginal median arm AUCs.

| Group | Facts / corpora | Naming gain [95% CI] | Map loss [90% CI] | Naming verdict | Truncation loss [95% CI] | Truncation verdict |
|---|---:|---|---|---|---|---|
| All held-out | 88 / 32 | +0.174 [+0.122, +0.239] | +0.008 [+0.004, +0.014] | SUPPORTED | +0.008 [+0.003, +0.017] | REFUTED |
| SURFACE | 22 / 2 | +0.258 [+0.199, +0.978] | +0.008 [+0.000, +0.015] | SUPPORTED | +0.021 [+0.000, +0.029] | REFUTED |
| KNOWLEDGE | 18 / 2 | +0.166 [+0.108, +0.312] | +0.003 [-0.002, +0.013] | SUPPORTED | +0.002 [-0.003, +0.008] | REFUTED |
| COMPUTED | 16 / 12 | +0.164 [+0.076, +0.271] | +0.019 [+0.009, +0.026] | UNDERPOWERED | +0.013 [+0.004, +0.019] | REFUTED |
| TOPIC | 17 / 10 | +0.122 [+0.017, +0.291] | +0.012 [+0.004, +0.021] | UNDERPOWERED | +0.004 [-0.001, +0.015] | REFUTED |
| PASSAGE-KNOWLEDGE | 9 / 1 | +0.144 [+0.047, +0.188] | +0.003 [-0.016, +0.015] | UNDERPOWERED | +0.017 [+0.008, +0.031] | REFUTED |
| FORM | 6 / 6 | +0.258 [+0.141, +0.505] | +0.010 [-0.000, +0.030] | UNDERPOWERED | +0.004 [-0.000, +0.020] | UNDERPOWERED |
| META | 0 / 0 | — | — | NOT EVALUATED | — | NOT EVALUATED |

COMPUTED passes map equivalence but its naming lower bound does not exceed 0.10. TOPIC and PASSAGE-KNOWLEDGE also fail the naming effect-size and/or lower-bound gates. FORM has only six facts and its map interval also reaches beyond +0.03 (unrounded upper bound0.030056). META's three eligible facts belong to calibration. These are limitations of the group conclusions, not evidence that their facts disappeared from Jh.

SURFACE and KNOWLEDGE each cover only two registered source groups; PASSAGE-KNOWLEDGE covers one. The especially wide SURFACE upper bound reflects the corpus bootstrap sometimes drawing only its singleton `49_cm_isshort` corpus, which has a very large native naming miss. The lower bound still passes. The result is conditional on these source populations; more independent corpora would be needed for a broad transfer claim.

## Arm performance and controls

At 256 labels, marginal median AUC across the 88 endpoint facts:

| Arm | Median AUC | 95% CI |
|---|---:|---|
| Original h | 0.871 | [0.824, 0.939] |
| Full Jh | 0.868 | [0.819, 0.922] |
| Native J score | 0.645 | [0.585, 0.722] |
| Rank-384 J proxy | 0.863 | [0.803, 0.911] |
| Rank-proxy complement | 0.869 | [0.821, 0.938] |
| Rank-384 Haar | 0.845 | [0.793, 0.915] |
| Rank-384 calibration PCA | 0.845 | [0.782, 0.910] |
| Existing prompt-only reference | 0.958 | [0.882, 0.999] |

The complement is the complement of a rank-384 proxy, not a separate semantic channel or the complement of the full J map. Prompt-only uses a different prompt and is descriptive.

Shuffled-training-label probes are at chance: original h 0.495 [0.486, 0.507], full Jh 0.499 [0.486, 0.506] (95% CIs). Unit normalization changes median AUC by +0.00009 [-0.00019, +0.00032] for h and +0.00000 [-0.00044, +0.00050] for Jh. Fixed pool class-mean references are supplied in the CSV; neither selects or replaces the logistic endpoint.

Learning curves for the same 88 facts (95% CIs):

| Labels | Naming gain | Map loss | Truncation loss |
|---:|---|---|---|
| 16 | +0.032 [-0.002, +0.079] | -0.004 [-0.011, +0.010] | +0.001 [-0.004, +0.005] |
| 64 | +0.123 [+0.075, +0.167] | +0.006 [-0.001, +0.015] | +0.002 [-0.003, +0.005] |
| 256 | +0.174 [+0.122, +0.239] | +0.008 [+0.004, +0.015] | +0.008 [+0.003, +0.017] |
| 512 | MISSING | MISSING | MISSING |

The 512 point is unavailable because reserving the 64 validation items leaves 448 pool items. No training set was silently reduced, validation-reused, or relabelled as 512.

The all-100 sensitivity population also passes the naming rule; its gain is +0.163 [+0.110, +0.224]. The 12 calibration facts and 27 eligible R5 facts are reported as diagnostic/descriptive subsets and are UNDERPOWERED for naming (R5 gain +0.104 [+0.044, +0.195]). Neither subset supplies the primary decision.

## Frozen design, provenance and execution

The preregistration is `BRIEF_R.md` §16, pushed before any WR-2 compute: initial commit `aab10f5`, pre-compute exclusion/corpus clarification `1e9e1a3`, final numerical parity gate `ceffcdec3bdcdc652b4ffc9d5cdd766024e7a6bf`. The worktree began from scaffold `e18adfd`; the required pre-commit pull advanced it to `8b345e4`. Design source is ideation-2 `f92f6f15d694488c758e76877582fae602740c02`, SYNTHESIS D2 and its WR-2 lens file. Thresholds and primary population were not changed after results.

- Matrix prerequisite passed locally before preregistration: J-lens SHA256 `1718c8c52dd8a9dad03738d4d625937c1fbba10be325b872ed446c7290fc11e1`, exact frozen pin; no download. The derived local unembedding hash and the frozen item-bank, state, index and score-shard hashes are in `wr2_preflight.json`.
- All 799 independent saved unembedding rows match after the saved fp16 conversion. Analytic native score parity passes on all 768 calibration-validation rows: maximum absolute score error 0.0000304, all AUC differences zero. No target model or tokenizer was loaded.
- All 113 R-A state/index files match frozen labels, ordering and collection SHA `4d482b6`; 100 meet semantic/coverage eligibility. Five R-A LABEL_DEFECT facts and eight insufficient-pool facts are excluded. Calibration uses the 12 prelisted code/historical-figure/context-type facts; endpoint evaluation uses the remaining 88. The one cross-population duplicate was removed only from calibration diagnostic test scoring, before computation.
- Every eligible fact has 512 pool / 200 test items. The exact existing 64 native-scored pool items are reserved; training draws of 16/64/256 are balanced and shared across all arms for seeds 0–4. `analyze.load_states` and `analyze._fit_logreg` are reused. StandardScaler fits only each exact training draw; logistic C=1 is fixed with no hyperparameter search, max_iter=2000. PCA uses only 5,376 calibration nonvalidation pool states.
- Raw `A=W_U J42` defines the rank-384 proxy, built at L42 rather than borrowing L38. All projections remain in 5,120 ambient coordinates before scaling. Native scoring retains maximum token variants, one-sided lp_A versus two-sided lo, original polarity and its token-row normalization; no state-norm denominator is introduced.
- J42 has numerical rank 5,120 and condition number about 736,545. Its map is ill-conditioned; algebraic rank alone is not the result. The positive empirical result is matched-budget held-out recoverability. The Gram spectrum's finite resolution is separately recorded. Its 80.7% top-384 matrix energy is not a natural-state variance fraction.
- Inference uses 2,000 paired label-stratified item bootstrap draws and both iid fact→item and corpus→fact→item group medians. Each seed earns its own AUC before averaging. Missing or failed registered fits cannot be silently dropped to obtain a verdict. Provenance guards verify exact manifest, input labels/IDs, state hashes and current geometry.

All 12,000 scheduled fits/estimates completed (11,000 logistic fits and 1,000 class-mean estimates); 3,000 n512 rows are explicitly missing, and zero fits failed or hit the convergence limit (largest iteration count 239). Two worker processes with one BLAS thread each ran from the start; geometry used two threads. No fit loop approached 30 minutes. GPU usage was **0 hours**.

Instrumented analysis stages total 377.5 CPU seconds (0.105 CPU-core hours) and 239.3 stage wall seconds. This includes both preparation passes (the second added a source-hash reuse guard before fitting); it excludes engineering, prerequisite filesystem hashing and interpreter/startup overhead. It remains far below the 14 CPU-core-hour cap. Geometry: 54.7s wall; native audit: 7.4s; fits: 108.5s; inference: 30.8s. Commands and timings are recorded in the shared log and compute ledger.

## Deliverables and reproduction

- `wr2_eligibility.csv`, `wr2_preflight.json`: every included/excluded fact and frozen input hashes.
- `wr2_splits.json`: compact split/recipe manifest; full ordered item IDs and training draws are in the ignored cache.
- `wr2_fits.csv`: all 15,000 fit/missing rows, seeds, validation/test AUCs, convergence and timing.
- `wr2_facts.csv`: per-fact arm AUCs, paired contrasts and CIs at all budgets.
- `wr2_groups.csv`: per-group values, both bootstrap intervals, quoted intervals, verdicts and failed clauses.
- `wr2_controls.csv`: per-fact null, normalization and mass-mean diagnostics.
- `wr2_geometry.json`, `wr2_spectrum.csv`, `wr2_native_audit.json`, `wr2_inference.json`: numerical, provenance and inference checks.

Large arrays, predictions and bootstrap draws remain under `cache/g_agreement/r/i2/wr2/` and are not committed. Existing main-checkout files and its cache link remain untouched.

```sh
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_geometry
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_native_audit --registration-commit ceffcdec3bdcdc652b4ffc9d5cdd766024e7a6bf
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_fit --stage prepare
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_fit --stage pca
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_fit --stage fit --workers 2
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_infer --self-test
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_infer --workers 2
```

Reproduction requires the hashed local frozen assets; it never downloads missing assets. Geometry refuses to overwrite a completed run without an explicit flag. Synthetic checks cover paired identity-map equality, exact-budget/missing-budget serialization, tied AUROC against sklearn, hierarchical medians, equivalence boundaries, both headline gates, incomplete fits, stale-cache rejection and exact semantic joins. Independent code and result checks accompany the native parity audit.
