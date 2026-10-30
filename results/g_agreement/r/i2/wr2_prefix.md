# WR-2 staged follow-up: label-free shared-prefix challenge

**Final report — 2026-10-19 23:15 Europe/Zurich. Stage 1: REFUTED_AT_50_PERCENT for closing WR-2’s naming gap; shared-prefix requirement: POSITIVE for all four readouts. Stage 2: NOT RUN because demonstrated held-out coverage is insufficient.**

On the preregistered supplemental challenge (nine independent source groups, 2,098 distinct test prompts), full-token sums beat literal first-token scoring by **+0.1704 AUC, paired 95% CI [+0.0334, +0.4501]**; the four-arm-adjusted interval is [+0.0058, +0.4646]. Every primary arm passes the shared-prefix lower-bound rule. This does not close the original gap: all four unchanged 88-fact results remain below 50% recovery, and the challenge shows no clear pooled improvement over the historical native readout. The largest original-population point gain remains variant-average mean **+0.000450**, 95% CI [−0.012250, +0.009450], or 0.26% of 0.174; its adjusted upper recovery bound is 7.36%.

The prospective decoder partition has **130 eligible test prompts / 521 pool prompts**, 74 held-out target identities and 26 prefix families. It is short by **126 test prompts** under the frozen partition, and complete alias adjudication remains unresolved. No decoder was fitted or declared refuted. All current Stage 1 work was CPU-only, with **zero new fits**, zero target-model forwards/downloads/GPU hours. New scoring plus inference used 15.150335 CPU seconds (0.004208 core-hours); the independent result audit used another 1.635938 CPU seconds.

## Registration and coverage

Inventory was preregistered in BRIEF_R §18 and pushed at `3705f5854ec81de24b6dcbbd57234e1796eded54` before counts. The exact challenge, surface list, code and scoring/inference addendum were pushed at `7ed8c2f2d576c4f5673651ec217cc9dc08f7130c` before new empirical scores. The manifest SHA256 is `30707fee099f583a4343a09b4931c96782bd126dad8030ad8d298eeaa3be9c3e`. No threshold or population was changed after scoring.

The [inventory report](wr2_stage_inventory.md) gives the full counts and prospective split. Original WR-2 endpoints contain 74 multi-token active candidate records out of 115 (73 with 2–4 tokens), five direct shared-prefix groups/1,000 test prompts, and seven independent groups after verified sibling-positive regrouping. This misses the eight-group coverage guard. The explicitly expanded challenge adds calibration news/code and short-pool frequency/typical-time examples, yielding nine groups/2,098 test prompts across nine source families and five first-token families. It meets the registered minimum of 256 distinct test prompts, eight independent groups and two source families. These minimum guards are not a formal power guarantee.

The expansion is supplemental. It does not replace the original 88-fact naming-gap endpoint, and its test results are a retrospective extension of known §17 data. LABEL_DEFECT facts remain excluded. News/code duplicates were removed by lowest item ID; one lexicographically chosen book/song pair represents the dependent art-type contrasts. No test prompt occurs in more than one challenge group. Both suffix identities occur in each group. All retained states and indices are local; metadata coverage is not evidence of unseen-name generalization.

## Frozen readouts and decision rule

For token t, the native J score is `z_t = (Jh · W_U[t]) / max(||W_U[t] @ J42||, 1e-9)`. Full-token sum/mean aggregate every token in one leading space plus the complete candidate. Variant-average sum/mean average the corresponding sequence score over the explicit, precommitted surfaces. Repeated tokens count; score polarity is fixed; no label-dependent weighting or selection is used. These are linear, order-insensitive scores, not sequence likelihoods or autoregressive generation. “Label-free” means no fitting to item labels; candidate meanings and surface forms are supplied.

The literal first-canonical-token contrast is identically zero because both candidates share that token; its AUC is 0.5. The historical native control instead uses the frozen shortened labels and maximum over token variants. All five direct endpoint pairs have distinguishable historical short forms. A gain against the literal tie therefore cannot substitute for recovery against the historical native comparator.

An arm closes the naming gap only if the original 88-fact median gain is ≥0.087 (50% of fixed 0.174), its lower bound is >0.0435 (25%), **and the same arm** has shared-prefix paired 95% lower gain >0. The any-arm headline also uses Bonferroni 98.75% per-arm intervals, providing at least 95% simultaneous coverage across four arms. Original-population upper bounds below 0.087 yield REFUTED_AT_50_PERCENT. Shared-prefix lower >0 yields POSITIVE; upper ≤0 yields REFUTED; otherwise UNRESOLVED. Tag results are descriptive, with adjustment only across four arms within each tag.

New inference uses 10,000 paired, semantic-label-stratified item bootstrap draws and source-group→item bootstrap medians, seed 20261025 with stable group-derived streams. One contrast represents each independent source cluster, so the fact and corpus partitions coincide here. All arms, native comparisons and suffix diagnostics share draws. Reported gains are medians of paired group differences, not differences between separate median AUCs. Original §17 CIs are reused unchanged; this is not an independent replication.

## Pooled shared-prefix results

| Readout | Gain over literal first token | Paired 95% CI | Four-arm-adjusted interval | Prefix verdict |
|---|---:|---|---|---|
| Full-token sum | +0.170400 | [+0.0334, +0.4501] | [+0.0058, +0.4646] | POSITIVE |
| Full-token mean | +0.229508 | [+0.0412, +0.4501] | [+0.0097, +0.4646] | POSITIVE |
| Variant-average sum | +0.180984 | [+0.0530, +0.4597] | [+0.0119, +0.4703] | POSITIVE |
| Variant-average mean | +0.304918 | [+0.0572, +0.4464] | [+0.0118, +0.4569] | POSITIVE |

The historical native median AUC is 0.7205, 95% CI [0.5439, 0.9976]. The following paired gains over that meaningful comparator all include zero:

| Readout | Gain over historical native, 95% CI | State-shuffled AUC, 95% CI |
|---|---|---|
| Full-token sum | -0.0021 [-0.0544, +0.0182] | 0.4918 [+0.4721, +0.5069] |
| Full-token mean | -0.0021 [-0.0505, +0.0184] | 0.4918 [+0.4727, +0.5069] |
| Variant-average sum | +0.0000 [-0.0584, +0.0362] | 0.4970 [+0.4751, +0.5121] |
| Variant-average mean | +0.0109 [-0.0380, +0.0631] | 0.4970 [+0.4762, +0.5157] |

Five fixed within-group whole-item score permutations (seeds 20261026–20261030) use the same permutation across arms. Their average AUCs are compatible with chance. These seeds are controls, not additional independent groups. They test dependence on the item-state pairing without training a new reader.

## Original naming-gap endpoint, unchanged

| Readout | Original 88 gain over native, 95% CI | Adjusted interval | Recovery of 0.174 | Combined Stage 1 verdict |
|---|---|---|---:|---|
| Full-token sum | -0.0005 [-0.0106, +0.0034] | [-0.0145, +0.0065] | -0.29% | REFUTED_AT_50_PERCENT |
| Full-token mean | +0.0000 [-0.0081, +0.0052] | [-0.0114, +0.0084] | 0.00% | REFUTED_AT_50_PERCENT |
| Variant-average sum | -0.0055 [-0.0307, +0.0053] | [-0.0396, +0.0089] | -3.16% | REFUTED_AT_50_PERCENT |
| Variant-average mean | +0.0005 [-0.0123, +0.0094] | [-0.0168, +0.0128] | 0.26% | REFUTED_AT_50_PERCENT |

These are the exact completed [WR-2-LF](wr2_lf.md) estimates, not new fits or bootstrap draws. The original tag results also remain unchanged: none supports closure; FORM is underpowered for all arms; TOPIC variant-average mean is underpowered after adjustment; META has no original endpoints. Complete original per-tag CIs remain in [wr2_lf_groups.csv](wr2_lf_groups.csv).

## Shared-prefix results by tag

Cells show gain over literal first token with nominal paired 95% CI; **P** means positive after four-arm adjustment and **U** means unresolved after adjustment. Independent-group counts are small, especially in one-group tags. These intervals do not support a discovery claim across tags.

| Tag | Groups | Full-token sum | Full-token mean | Variant-average sum | Variant-average mean |
|---|---:|---|---|---|---|
| COMPUTED | 3 | -0.0029 [-0.0524, +0.1952] U | -0.0029 [-0.0524, +0.1952] U | -0.0029 [-0.0524, +0.1801] U | -0.0029 [-0.0524, +0.2904] U |
| KNOWLEDGE | 2 | +0.4456 [+0.4159, +0.4703] P | +0.4456 [+0.4159, +0.4703] P | +0.4571 [+0.4359, +0.4743] P | +0.4440 [+0.4209, +0.4637] P |
| META | 1 | +0.0980 [-0.0108, +0.1997] U | +0.2295 [+0.1321, +0.3184] P | +0.1810 [+0.0784, +0.2774] P | +0.3049 [+0.2213, +0.3767] P |
| PASSAGE-KNOWLEDGE | 1 | +0.0797 [+0.0001, +0.1590] U | +0.0797 [+0.0001, +0.1590] U | +0.1148 [+0.0353, +0.1925] P | +0.1267 [+0.0471, +0.2037] P |
| SURFACE | 1 | +0.5000 [+0.5000, +0.5000] P | +0.5000 [+0.5000, +0.5000] P | +0.5000 [+0.5000, +0.5000] P | +0.5000 [+0.5000, +0.5000] P |
| TOPIC | 1 | +0.2354 [+0.1638, +0.2999] P | +0.2354 [+0.1638, +0.2999] P | +0.2971 [+0.2340, +0.3575] P | +0.3392 [+0.2820, +0.3918] P |

FORM has no shared-prefix group. PASSAGE-KNOWLEDGE full-token sum/mean just pass nominal 95% intervals but are unresolved after adjustment. SURFACE’s [0.5, 0.5] gain interval reflects perfect separation in this observed calibration-derived sample; a degenerate empirical bootstrap is not population certainty. The COMPUTED aggregate is unresolved although the morality contrast is positive.

## Per-source challenge results

Each cell is paired gain over literal first token with nominal 95% CI and adjusted P/U status. Full per-source AUCs, native contrasts, suffix diagnostics and both interval levels are in [wr2_prefix_facts.csv](wr2_prefix_facts.csv).

| Contrast | Test n | Full-token sum | Full-token mean | Variant-average sum | Variant-average mean |
|---|---:|---|---|---|---|
| Five-star / lower-rated review | 200 | +0.2354 [+0.1636, +0.3006] P | +0.2354 [+0.1636, +0.3006] P | +0.2971 [+0.2342, +0.3566] P | +0.3392 [+0.2830, +0.3915] P |
| News / code | 587 | +0.5000 [+0.5000, +0.5000] P | +0.5000 [+0.5000, +0.5000] P | +0.5000 [+0.5000, +0.5000] P | +0.5000 [+0.5000, +0.5000] P |
| United Kingdom / United States | 200 | +0.4600 [+0.4341, +0.4807] P | +0.4600 [+0.4341, +0.4807] P | +0.4642 [+0.4410, +0.4822] P | +0.4428 [+0.4077, +0.4710] P |
| Book / song | 200 | +0.4313 [+0.3963, +0.4604] P | +0.4313 [+0.3963, +0.4604] P | +0.4501 [+0.4213, +0.4744] P | +0.4451 [+0.4142, +0.4709] P |
| Frequency / typical time | 111 | +0.0980 [-0.0095, +0.2007] U | +0.2295 [+0.1311, +0.3190] P | +0.1810 [+0.0813, +0.2757] P | +0.3049 [+0.2213, +0.3774] P |
| Solution B / A (PIQA) | 200 | -0.0029 [-0.0846, +0.0793] U | -0.0029 [-0.0846, +0.0793] U | -0.0029 [-0.0846, +0.0793] U | -0.0029 [-0.0846, +0.0793] U |
| Answer A / B (QuaRTz) | 200 | -0.0138 [-0.0934, +0.0694] U | -0.0138 [-0.0934, +0.0694] U | -0.0138 [-0.0934, +0.0694] U | -0.0138 [-0.0934, +0.0694] U |
| Morally wrong / acceptable | 200 | +0.1704 [+0.0918, +0.2440] P | +0.1704 [+0.0918, +0.2440] P | +0.1586 [+0.0801, +0.2314] P | +0.2708 [+0.2051, +0.3304] P |
| Democrat / Republican | 200 | +0.0797 [+0.0004, +0.1579] U | +0.0797 [+0.0004, +0.1579] U | +0.1148 [+0.0339, +0.1922] P | +0.1267 [+0.0470, +0.2032] P |

Removing the longest shared canonical prefix leaves suffix-sum AUC exactly equal to full-token-sum AUC in all nine groups, as expected because common additive terms cancel. Suffix-mean AUC also matches full-token-mean AUC in all eight equal-length groups. For the unequal-length frequency/typical-time pair, full-token-mean gain is +0.2295 [0.1311, 0.3190], and suffix-mean gain is +0.2226 [0.1230, 0.3128]. Thus suffix scores carry separability there too; unequal prefix weighting still changes the result slightly. Across groups, suffix-sum gain is +0.1704 [0.0334, 0.4501] and suffix-mean gain is +0.2226 [0.0412, 0.4501]. These are diagnostics; variants may themselves remove the prefix collision.

## Vocabulary alignment and interpretation

Reuse the existing §17 pool-probe alignment, with no new training. Its probes use `beta = standardized_coef / scaler.scale_` in raw Jh coordinates; nearest positive/negative/absolute W_U rows, decoded strings and seed-level values are already saved in [wr2_lf_alignment_neighbors.csv](wr2_lf_alignment_neighbors.csv), [per-fact alignment](wr2_lf_alignment_facts.csv), and [tag alignment](wr2_lf_alignment_groups.csv). Median nearest-positive cosine is 0.07703 for real probes, 0.07044 for shuffled-label probes and 0.06144 for isotropic directions. These are existing label-assisted diagnostics, not label-free fitting or fresh evidence.

The five direct endpoint contrasts have identical cached directions. News/code has existing constituent-fact directions, not one newly pooled direction. UK/US, book/song, and frequency/typical-time have no cached probe direction for the exact new binary contrast: contrast-specific alignment is **NOT AVAILABLE under this no-training stage**. A one-v-rest direction is not substituted for a sibling-pair probe.

Low cosine with individual vocabulary rows does not prove that no token readout can name a fact. Token combinations, anisotropic state covariance and nonlinear readouts can remain useful. J42 is numerically full rank, so h≈Jh equivalence is expected; WR-2 also found strong recoverability in matched-rank random subspaces (Haar384 median AUC about 0.845). Neither recoverability nor the present suffix-sensitive scores establish uniquely privileged J geometry, a causal workspace, or information used by the target model. Failure applies to these four fixed recipes, not all possible learned or generative multi-token decoders.

## Stage 2 withheld: missing coverage

All 31 inventoried workspace/context datasets (11,224 rows) have local L42 state/index files. Potential same-question shared-prefix regrouping supplies 290 test prompts before joint exclusions. The prospectively frozen template-hash split retains 130 test prompts and 521 pool prompts after known template/name/alias/candidate/duplicate exclusions, with zero retained template/alias-ID/prompt overlaps. It has 74 held-out complete target identities and 26 prefix families across three sources, but fails the 256-test minimum and has incomplete semantic alias adjudication. There is no learned-decoder pilot or negative decoder verdict.

Under this partition, the missing resource is at least **126 additional clean held-out contexts/states**, while preserving ≥512 pool states, plus complete aliases and provenance. Each new example needs the pinned model’s L42/chat/last h or verified Jh, ordered item/index identity, target and accepted aliases, source entity/context, template family, split and collector/input hashes. Repeated aliases do not add independent target groups. This is one deterministic partition, not proof that all cached alternatives fail; a separately frozen adequate repartition could also meet the requirement. No new state collection or downloads were attempted.

If coverage is later established, Stage 2 needs its own full preregistration before training: activation-only byte-level GRU (5120→256 projection, ≤64 bytes, fixed schedule, three seeds), h-decoder, native-token-only completion decoder, shuffled/mean-Jh controls and within-prefix donor shuffle. The proposed rule remains ≥10 percentage points full-name exact-match improvement over native/state-free controls with paired 95% lower bounds >0, positive donor-suffix following, and h/Jh equivalence within ±5 points using paired 90% intervals. **h≈Jh is expected from J42’s full rank; the informative contrasts are native-token and state-free controls.** A failed h-decoder makes a negative Jh result inconclusive. No full training registration is claimed here.

## Execution, audit and reproducibility

The original runs did not retain Jh arrays. As preregistered, the scorer deterministically reconstructs float32 `X @ J42.T` through `analyze.load_states` using the existing pinned h states and J42. W_U and tokenizer are local; no model forward or download occurs. This is the disclosed operational exception to literal reuse of retained Jh. Existing direct-fact scores are reused only after parity: 1,587 rows have exact primary-score parity; newly reconstructed native scores differ by at most 3.70e−5 before the original cached scores are restored.

All nine groups and 2,098 unique prompts are complete and finite. The independent audit recomputed 72 sklearn AUROCs from saved predictions (maximum error 1.11e−16), checked all 333 fact rows, 259 aggregate rows and 108 control rows, reproduced all saved bootstrap quantiles exactly, checked paired contrast algebra, and verified direct-cache parity and all combined decisions. It made no new fits, token scores or bootstrap draws. See [wr2_prefix_verification.json](wr2_prefix_verification.json).

| Stage | Instrumented CPU seconds | Stage wall seconds | Fits | GPU hours |
|---|---:|---:|---:|---:|
| Scoring | 5.865106 | 5.391193 | 0 | 0 |
| Inference | 9.285229 | 5.613457 | 0 | 0 |
| Independent saved-result audit | 1.635938 | 1.714004 | 0 | 0 |

Scoring/inference used two worker processes with one BLAS thread each, well below the registered 0.5-core-hour cap. Scoring/inference timers exclude startup imports; the audit timer includes NumPy/sklearn imports. Implementation and reporting time are not included. Metadata inventory runs have their own ledger entries and disclosed incomplete preliminary timing. All scientific inputs/code/outcome hashes and source indices are saved. Main checkout and its cache link remain unchanged.

```sh
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_prefix_score --registration-commit 7ed8c2f2d576c4f5673651ec217cc9dc08f7130c --workers 2
.venv/bin/python -B -m projects.g_agreement.r_bench.wr2_prefix_infer --registration-commit 7ed8c2f2d576c4f5673651ec217cc9dc08f7130c --workers 2
.venv/bin/python -B cache/g_agreement/r/i2/wr2_prefix/wr2_prefix_audit_results.py --repo "$PWD" --out /tmp/wr2_prefix_verification.json
```

Small results: [manifest](wr2_prefix_manifest.json), [per-source CSV](wr2_prefix_facts.csv), [aggregate/tag CSV](wr2_prefix_groups.csv), [control CSV](wr2_prefix_controls.csv), [score provenance](wr2_prefix_score_run.json), [inference/verdicts](wr2_prefix_inference.json), [inventory/split](wr2_stage_inventory.md). Large predictions, saved bootstrap arrays, audit source and run logs live under ignored `cache/g_agreement/r/i2/wr2_prefix/`. The original §17 results and alignment files remain unchanged. Handoff is recorded in `results/g_agreement/r/HANDOFF.md` on branch `r/i2-wr2`; Guiv relays it to the integrator.
