SA does not establish that either reader detects an invisible change: the frozen primary verdict is **NOT EVALUABLE for both Oracle and NLA**, because 64 of 400 held-out concept-edit cases failed the invisibility gate, including 41 changed answers. NLA shows a descriptive closed-set advantage over prompt-only and matched random edits that passes the registered contrast thresholds; Oracle does not pass the conservative clustered thresholds. Neither result overrides the failed gate. Both same-list supervised linear and cosine-centroid baselines score 100% top-5, so these data do not establish a reader advantage over known-concept methods. Open-vocabulary naming is not yet scored under the registered blinded judge and must not be interpreted as zero naming or evidence of unknown-concept discovery.

| Method | Concept edit top-5 | Matched random top-5 | Placebo top-5 | Shuffled-state concept top-5 (exploratory) | Status |
|---|---:|---:|---:|---:|---|
| Oracle L44 | 26.75% | 7.00% | 6.00% | 9.75% | Primary claim NOT EVALUABLE |
| NLA L42 | 48.00% | 11.50% | 11.50% | 19.50% | Primary claim NOT EVALUABLE |
| Prompt-only | 13.50% | 13.50% | 13.50% | — | Pre-registered control |
| Linear probe L42 | 100.00% | 15.25% | 20.00% | — | Known-concept baseline; comparison amended before unseal |
| Linear probe L44 | 100.00% | 20.00% | 18.25% | — | Known-concept baseline; comparison amended before unseal |
| Cosine bank L42 | 100.00% | 19.50% | 17.00% | — | Known-concept baseline; comparison amended before unseal |
| Cosine bank L44 | 100.00% | 18.00% | 15.00% | — | Known-concept baseline; comparison amended before unseal |
| J-lens L42 | Not scorable | Not scorable | Not scorable | Not scorable | Registered diagnostic: unsupported candidates, no 40-way result |

All rates use 400 concept×prompt pairs per arm: 20 concepts ×20 shared prompts, equal macro-concept weighting. Closed Oracle/NLA/prompt-only/probe coverage is complete. No failing-gate cases were removed.

### Frozen primary contrasts

| Reader | vs prompt-only, estimate [conservative 95% CI] | vs matched random, estimate [conservative 95% CI] | Closed contrast thresholds alone | Final primary verdict |
|---|---|---|---|---|
| oracle | +13.25 pp [-5.74, +75.00] pp | +19.75 pp [-1.25, +52.31] pp | Fail | NOT EVALUABLE |
| nla | +34.50 pp [+16.67, +75.00] pp | +36.50 pp [+16.54, +63.85] pp | Pass | NOT EVALUABLE |

The frozen rule requires the entire held-out concept population to be invisible, a lower95% bound strictly above +10pp vs prompt-only, and strictly above0 vs matched random. Uncertainty uses10,000 paired draws, seed20261020, preserving concept/prompt pairing: within-concept item resampling; corpus→concept crossed with shared prompt-ID resampling; and corpus→concept crossed with family→prompt resampling. The table uses the envelope of all three intervals. Only three corpora and five families support these clusters; intervals are correspondingly broad. The registered omnibus correction is Bonferroni97.5%, **not BH**. NLA also passes those contrast bounds, but no omnibus invisible-change claim passes the failed gate. Full scheme-specific intervals are in RESULTS.json.

### Held-out invisibility

| Arm | Pass | Changed complete answers | Maximum forward KL |
|---|---:|---:|---:|
| concept | 336/400 | 41/400 | 1.664286 nats |
| random | 319/400 | 33/400 | 1.728923 nats |
| placebo | 400/400 | 0/400 | 0.000000 nats |

The KL limit is0.1 nats and full greedy answers must match through EOS. All saved pass flags were independently recomputed from KL, EOS and complete token sequences. A changed-answer count is not the entire failure count; KL/EOS failures can also fail the gate. The random arm is not visibility-matched: its failures remain disclosed, without norm adjustment or filtering.

### Amendment comparisons and exploratory controls

The 11:20:12.920776Z amendment (`8da8ae4d`) predates the first truth join. Linear probes retain the registered training-only StandardScaler/logistic regression, C=1, lbfgs, max_iter1000, seed20261020, separately at42/44. Cosine uses one normalized raw-activation centroid for each of the same40 concepts from the50 disjoint probe-training prompts. No evaluation data enter bank construction, scaling or fitting; no layer is selected by performance. These are known-concept supervised comparisons. Both score100% on concept edits at both sites. Reader-minus-own-site baseline estimates are−73.25pp for Oracle and−52.00pp for NLA; their conservative95% intervals are [-92.96, +0.00] pp and [-76.85, +0.00] pp, respectively. Linear and cosine have identical hit outcomes here.

**Added-vector diffing is excluded as trivially perfect by construction.** The baselines use raw states, not the injected vector or paired differences that reconstruct it. Paired statistical contrasts and output-preservation checks are not excluded.

Shuffled-state controls are **exploratory**, requested after the original registration and amendment. They reuse saved outputs from a deterministic no-fixed-point permutation of the20 concept states within the same prompt and arm (seed20261020), shared by both readers. No reader was rerun. This breaks state/assigned-concept correspondence while preserving prompt and condition. It is one fixed permutation, not a permutation p-value test. The mapping is pinned in RESULTS.json. Reader-minus-shuffled conservative95% contrasts: Oracle [-8.50, +67.69] pp; NLA [+10.74, +100.00] pp. Shuffled random/placebo rates are also in RESULTS.json.

**Exploratory BH only:** four one-sided null-centered bootstrap tests across Oracle/NLA × prompt-only(+10pp null)/matched-random(0 null), taking the largest bootstrap p across the three resampling schemes, then BH across those four tests. These newly specified p-values/q-values do not replace the frozen percentile-CI rule.

| Contrast | BH q (exploratory) |
|---|---:|
| oracle:prompt_only | 0.4148 |
| oracle:matched_random | 0.1288 |
| nla:prompt_only | 0.1218 |
| nla:matched_random | 0.0264 |

### Open-vocabulary framing, reported separately

Oracle/NLA received no candidate list in their open carrier. This supports the requested open-vocabulary/no-candidate-list framing, not a claim of arbitrary unseen-concept generalization: the intervention population itself is a frozen concept list. The registered semantic judge has not been run. CPU-only authorization does not supply new judge inference; no lexical proxy, hindsight human judgement, or zero-imputation replaces it. Specific-hit rates and their contrasts therefore remain **unavailable**, not zero.

| Reader | Concept EOS-valid | Random EOS-valid | Placebo EOS-valid | Registered specific naming rate |
|---|---:|---:|---:|---|
| oracle | 399/400 | 398/400 | 400/400 | Not judged |
| nla | 400/400 | 398/400 | 400/400 | Not judged |
| prompt_only | 400/400 | 400/400 | 400/400 | Not judged |

EOS-valid is a generation coverage check, not semantic validity or naming success. If judging is later authorized, truncated/invalid outputs retain the registered failure handling and full denominator.

### Detection diagnostics

These registered AUROC point estimates use maximum closed candidate log-probability, fixed upward orientation; no sign is selected on outcomes. They are separate from the top-5 primary verdict.

| Method | Concept vs placebo AUROC | Random vs placebo AUROC |
|---|---:|---:|
| oracle | 0.5497 | 0.7345 |
| nla | 0.7249 | 0.5024 |
| prompt_only | 0.5000 | 0.5000 |
| labelled_probe | 1.0000 | 0.4582 |
| transfer_probe | 0.5500 | 0.3049 |

These are point diagnostics; no AUROC significance claim is made. Site-specific probe scores remain in the pinned observations.

### Pinning, provenance and validation

- §52 panel manifest: `PANEL_INPUT_MANIFEST.json`, SHA `b9d6f5059765ce08cb2a742b08cabacc2c0e21735ea22c906bc9cd1bdb5b339a`, pinned11:25:56.452764Z and pushed as`ddc125df` before first truth join11:27:26.574453Z. Contains absolute paths and SHA256 for all26,896 merged cell files plus the frozen design. Every pinned cell was rehashed before analysis.
- Frozen prompts and candidate target names/definitions: manifest `design_path`. Native reader scores/open outputs, probability probe site scores and original provenance: manifest `cells`; schema `sa_run.py`, keys `native`, `observation`, `state`. No independent pre-existing probe-margin field is claimed; probability margins are derivable from saved site scores.
- Complete collection:16,800 logical rows,40calibrated concepts. Both final pulls independently verified, both recovery pods stopped, watch paused. Aggregate billed upperbound12.0133105161GPU-h<17.
- CPU analysis: `projects/g_agreement/r_bench/neel5/recovery_analysis.py`; four synthetic tests cover BH, paired weights/determinism, failed-gate precedence and ranking ties. No new GPU/reader/target/judge inference. Frozen collection code unchanged.
- Primary report is complete as NOT EVALUABLE because of the mandatory gate; the secondary semantic open-naming analysis is explicitly incomplete pending registered blinded judging.

### Exploratory gate-passing subsets (requested after full-population results)

These are post-outcome, gate-selected descriptive analyses, not a repair of the pre-registered failed population gate. All comparisons within each row use the **same selected concept×prompt pairs for concept, matched random, placebo and prompt-only**. The336 concept-passing mask and319 random-passing mask differ; their rates must not be subtracted as though paired. Equal macro-concept weighting is retained, so percentages can differ from pooled numerator/denominator rates (also saved in SUBSETS.json).

| Selection mask | Pairs | Reader | Concept top-5 | Random top-5 on same pairs | Concept−random [95% conservative CI] | Concept−prompt-only [95% conservative CI] |
|---|---:|---|---:|---:|---|---|
| concept_passes | 336 | oracle | 27.68% | 7.50% | +20.18 pp [-3.33, +55.66] | +14.66 pp [-5.93, +76.85] |
| concept_passes | 336 | nla | 48.22% | 11.44% | +36.78 pp [+16.34, +63.94] | +35.20 pp [+16.75, +77.18] |
| random_passes | 319 | oracle | 27.76% | 7.22% | +20.54 pp [-5.13, +55.64] | +11.19 pp [-8.26, +50.00] |
| random_passes | 319 | nla | 47.63% | 11.20% | +36.42 pp [+8.33, +64.20] | +31.05 pp [+12.31, +61.54] |

Same three bootstrap structures and seed20261020, conditioned on each fixed selected mask. Item draws resample passing prompts within each concept. Cluster/family draws mask out failing pairs and renormalize prompt weights within represented concepts. A sampled concept with no passing prompts in that draw contributes no weight; completely empty draws are rejected. The336 mask has10,000 valid draws in each scheme; the319 mask has10,000/10,000/9,998 valid draws from10,000 attempts per scheme. Empty-concept occurrences and per-concept sample counts are disclosed in SUBSETS.json. These additional conditioning choices and intervals are exploratory; selection can bias effects and does not support a population-wide invisibility claim.

**Detection diagnostic:** Oracle responds more strongly to matched random edits (AUROC0.7345) than to concept edits (0.54975) under the registered maximum-closed-log-probability detector. This cautions against interpreting that anomaly score as concept-specific detection; it does not reverse the score orientation or alter the primary top-5 rule.

### Blinded semantic judge attempt — stopped before full-population scoring

The exact frozen-client modelID `google/gemini-3.8-flash` passed the requested20/20complete-verdict parsecheck (temperature0,minimalreasoning,max2000) and3/3positive/negative/generic fixtures. The authorized fullrun then stopped after293of1617unique readouts at a transport `RemoteDisconnected` (connection closed without a response), not a demonstrated parse/truncation failure. Known chargedcost is$0.42732, with **one failed request’s billing unresolved**. Cached valid verdicts are preserved; no retry, model change or furtherAPIspend occurred. The completion watch is paused. No partial namingrate is reported or missing judge output treated as a failure/zero: all3600logical rows and full400-per-arm denominators remain required before semantic scoring. See OPEN_JUDGE_FAILURE.json.

## Completed blinded open-vocabulary naming — 2026-10-21T12:24:41.219270+00:00

NLA specifically names the assigned concept in 51/400 concept-edit cases (12.75%); the Oracle lens does so in40/400 (10.00%), and asking alone in0/400. Both readers score0/400 on matched-random and placebo controls. This is evidence of occasional spontaneous naming under this fixed40-definition scoring reference, not arbitrary unseen-concept discovery or proof of invisible-change detection. The primary registered verdict remains NOT EVALUABLE because the whole-population invisibility gate failed.

| Method | Concept edits | Random edits | Placebo | Concept descriptive Wilson95% |
|---|---:|---:|---:|---:|
| NLA | 51/400 (12.75%) | 0/400 | 0/400 | 9.83–16.38% |
| Oracle lens | 40/400 (10.00%) | 0/400 | 0/400 | 7.43–13.33% |
| Asking (prompt-only) | 0/400 (0.00%) | 0/400 | 0/400 | 0.00–0.95% |

All 3600 logical cells remain in their denominators. Zero MISSING judge verdicts. Invalid saved generations count as failures: Oracle concept1/random2/placebo0; NLA0/2/0; asking0/0/0. No verdict had more than five matched candidate IDs. The specific-name check uses the same judge ID, settings, schema and blinding; no immutable provider revision was originally pinned. Parse check20/20; blind fixtures3/3.

Matched concept-minus-random and concept-minus-asking contrasts are identical because both controls score zero: Oracle +10.00 percentage points, conservative clustered95% interval [+2.00,+26.67]; NLA +12.75 points, [+1.15,+28.25]. These use the registered10000-draw corpus/concept/prompt-family bootstrap schemes and conservative envelope; the narrower Wilson intervals above are descriptive only. No new primary decision is inferred.

**Exploratory shuffled-state control**, reusing the previously pinned concept derangement within the same prompt/arm (no new reader or judge calls):

| Reader | Shuffled concept | Shuffled random | Shuffled placebo | Actual minus shuffled concept (clustered95%, pp) |
|---|---:|---:|---:|---:|
| NLA | 0/400 | 0/400 | 0/400 | 12.75 [1.15, 28.25] |
| Oracle lens | 0/400 | 0/400 | 0/400 | 10.00 [2.00, 26.67] |

Completed judging at12:22:57Z after all1617unique valid readouts. Known billed cost$2.3260275 plus$1 conservative reserve for the earlier unresolved request: accounted upper bound$3.3260275, below$60. No new unresolved charges. Existing valid cache was reused. Dated retry amendment694bf15f was registered12:02:49.637944Z before naming-rate computation; other analysis amendments retain their original dates. The earlier incomplete-run notice is superseded by this completion, not deleted. All pods remain stopped.

Machine-readable output: `OPEN_RESULTS.json`; append-only cache and ledger remain in `cache/g_agreement/r/neel5/sa/open_judge_20261021/`.

## Exploratory: open naming on invisibility-passing concept edits — 2026-10-21T12:27:08.323794+00:00

CPU-only reuse of the completed blinded verdicts. Select the336 concept-arm cases passing the registered held-out invisibility gate, and apply those exact concept/prompt pairs to concept, random, placebo, asking and shuffled-state controls. Do not select the random arm independently. All336 remain in every denominator, including invalid generations; no judge verdicts are missing. Shuffled controls reuse the previously fixed derangement and are exploratory.

| Method | Concept hit count /336 (pooled) | Equal-concept mean | Random | Placebo | Shuffled concept |
|---|---:|---:|---:|---:|---:|
| NLA | 45/336 (13.39%) | 13.68% | 0/336 | 0/336 | 0/336 |
| Oracle lens | 34/336 (10.12%) | 10.38% | 0/336 | 0/336 | 0/336 |
| Asking | 0/336 (0.00%) | 0.00% | 0/336 | 0/336 | — |

The pooled rates answer the case-count question; equal-concept means retain the registered weighting convention despite unequal passing counts per concept. The complementary64 failing cases contain6 NLA hits and6 Oracle hits (9.375% each pooled), and zero asking/random/placebo/shuffled hits. Thus45/51 NLA naming successes and34/40 Oracle naming successes occurred in cases passing the measured invisibility gate: naming is not confined to failed-gate edits. This does not prove universal or undetectable invisibility, nor a causal difference between selected groups. These are post-outcome selected descriptive analyses; no new confirmatory test or primary-verdict revision.

Passing subset invalid saved generations: NLA concept0/random2/placebo0; Oracle1/2/0; asking0/0/0. Failed subset invalid generations:0 throughout. These count as failures rather than being removed. Machine output: `OPEN_SUBSETS.json`; reproducible CPU module: `projects/g_agreement/r_bench/neel5/open_subset_analysis.py`. No additional API or GPU spending.
