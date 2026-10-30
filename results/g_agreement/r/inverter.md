# Oracle inversion baseline — full coverage

**COMPLETE: 22,198/22,198 items, 113/113 facts, 110,990 unique score keys across all five arms.** The defect-excluded primary contains 21,198 items in 108 facts. The incomplete-coverage restriction is now resolved for this final analysis. Historical partial-run results and the two diagnostic snapshots remain separately labelled.

**Every tag is NOT_DISTINGUISHED under the preregistered decision rules.** No tag meets the equivalence rule “explained by inversion”; no tag clears the stricter “reads beyond inversion” rule. This is not evidence that the methods are equivalent or that all differences are zero.

COMPUTED shows the clearest positive Oracle-minus-inversion result: **+0.1044 AUROC, 95% envelope [+0.0248, +0.1964]**. Its interval excludes zero, but the lower bound is below the required +0.03; therefore the registered beyond-inversion verdict does not pass. Native Oracle AUROC is 0.7421, reconstructed-text prompt-only 0.6377, and true-text prompt-only 0.9152. The inversion pipeline loses substantial task performance relative to true text, but this comparison does not identify why. On PASSAGE-KNOWLEDGE and TOPIC, inversion outperforms Oracle with negative 95% intervals; the equivalence rule still fails because the 90% intervals are not inside ±0.05.

## Primary comparison

Unweighted mean per-fact AUROC within tag; both paired fact→item and corpus→fact→item bootstraps, 2,000 draws, seed 0. The quoted intervals are the conservative envelope. All seven verdicts are NOT_DISTINGUISHED.

| Tag | Facts | Oracle | Inversion → PO | True text → PO | Shuffled → PO | Mean → PO | Oracle − inversion | 90% envelope | 95% envelope |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| COMPUTED | 17 | 0.7421 | 0.6377 | 0.9152 | 0.5117 | 0.5000 | +0.1044 | [+0.0383, +0.1786] | [+0.0248, +0.1964] |
| FORM | 6 | 0.5883 | 0.6444 | 0.8634 | 0.5167 | 0.5000 | -0.0560 | [-0.1576, +0.0383] | [-0.1756, +0.0555] |
| KNOWLEDGE | 21 | 0.6992 | 0.7120 | 0.8977 | 0.5012 | 0.5000 | -0.0129 | [-0.0589, +0.0230] | [-0.0684, +0.0287] |
| META | 6 | 0.6248 | 0.7174 | 0.8818 | 0.4909 | 0.4967 | -0.0925 | [-0.2016, +0.0153] | [-0.2280, +0.0317] |
| PASSAGE-KNOWLEDGE | 9 | 0.6038 | 0.6901 | 0.8168 | 0.4772 | 0.5000 | -0.0863 | [-0.1433, -0.0372] | [-0.1565, -0.0298] |
| SURFACE | 28 | 0.7415 | 0.7202 | 0.9981 | 0.4843 | 0.5000 | +0.0213 | [-0.2612, +0.0793] | [-0.6604, +0.0865] |
| TOPIC | 21 | 0.6033 | 0.7279 | 0.8174 | 0.5094 | 0.5000 | -0.1246 | [-0.2223, -0.0491] | [-0.2421, -0.0327] |

Explained by inversion requires D ≤ 0.02 and the 90% envelope wholly inside [−0.05, +0.05]. Reads beyond inversion requires D > 0 and the 95% lower bound > 0.03. Rules and thresholds are unchanged. The broad SURFACE interval is retained as computed; this tag contains 28 facts but only 3 source-corpus groups.

COMPUTED is heterogeneous at the fact level: the QQP fact has Oracle-minus-inversion +0.6073, while arithmetic is +0.0080, MRPC −0.0584 and QNLI −0.0494. These are descriptive entries in the existing per-fact table, not new tests or exclusions.

## Both bootstrap schemes

| Tag | Fact→item 90% | Corpus→fact→item 90% | Fact→item 95% | Corpus→fact→item 95% |
|---|---|---|---|---|
| COMPUTED | [+0.0391, +0.1786] | [+0.0383, +0.1763] | [+0.0248, +0.1931] | [+0.0270, +0.1964] |
| FORM | [-0.1504, +0.0362] | [-0.1576, +0.0383] | [-0.1646, +0.0547] | [-0.1756, +0.0555] |
| KNOWLEDGE | [-0.0473, +0.0226] | [-0.0589, +0.0230] | [-0.0548, +0.0287] | [-0.0684, +0.0287] |
| META | [-0.2016, +0.0153] | [-0.2003, +0.0109] | [-0.2280, +0.0317] | [-0.2224, +0.0292] |
| PASSAGE-KNOWLEDGE | [-0.1433, -0.0372] | [-0.1425, -0.0375] | [-0.1560, -0.0298] | [-0.1565, -0.0305] |
| SURFACE | [-0.0366, +0.0700] | [-0.2612, +0.0793] | [-0.0490, +0.0777] | [-0.6604, +0.0865] |
| TOPIC | [-0.2166, -0.0491] | [-0.2223, -0.0491] | [-0.2365, -0.0356] | [-0.2421, -0.0327] |

## All-facts sensitivity

Includes all 113 facts / 22,198 items. The five known label-defect facts are all TOPIC; other tag estimates and membership are unchanged. Every sensitivity verdict is also NOT_DISTINGUISHED.

| Tag | Facts | Oracle | Inversion → PO | True text → PO | Shuffled → PO | Mean → PO | Oracle − inversion | 90% envelope | 95% envelope |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| COMPUTED | 17 | 0.7421 | 0.6377 | 0.9152 | 0.5117 | 0.5000 | +0.1044 | [+0.0383, +0.1786] | [+0.0248, +0.1964] |
| FORM | 6 | 0.5883 | 0.6444 | 0.8634 | 0.5167 | 0.5000 | -0.0560 | [-0.1576, +0.0383] | [-0.1756, +0.0555] |
| KNOWLEDGE | 21 | 0.6992 | 0.7120 | 0.8977 | 0.5012 | 0.5000 | -0.0129 | [-0.0589, +0.0230] | [-0.0684, +0.0287] |
| META | 6 | 0.6248 | 0.7174 | 0.8818 | 0.4909 | 0.4967 | -0.0925 | [-0.2016, +0.0153] | [-0.2280, +0.0317] |
| PASSAGE-KNOWLEDGE | 9 | 0.6038 | 0.6901 | 0.8168 | 0.4772 | 0.5000 | -0.0863 | [-0.1433, -0.0372] | [-0.1565, -0.0298] |
| SURFACE | 28 | 0.7415 | 0.7202 | 0.9981 | 0.4843 | 0.5000 | +0.0213 | [-0.2612, +0.0793] | [-0.6604, +0.0865] |
| TOPIC | 26 | 0.5887 | 0.7026 | 0.7745 | 0.5080 | 0.5000 | -0.1139 | [-0.1942, -0.0474] | [-0.2101, -0.0352] |

## Reconstruction evidence

The original 20-item pool gate passed: natural exact-span 1/20 (Wilson 95% 0.9–23.6%), mean token recall 15.996%; shuffled 6.619%, mean-state 5.891%. The frozen near-zero rule did not trigger. No gate was rerun during either continuation.

The separately specified full-coverage exploratory analysis does not establish a negative association between reconstruction recall and Oracle advantage: pooled per-fact Pearson +0.1262 [−0.0830, +0.3066], Spearman +0.1974 [−0.0851, +0.4044]. See [recall analysis](inverter_exploratory.md), [per-fact table](inverter_exploratory_per_fact.csv), and [machine-readable summary](inverter_exploratory_summary.json). Lexical recall is an imperfect proxy for task-relevant reconstruction and does not establish causality.

The earlier [numeric/operand diagnostic](inverter_numeric_diagnostic.md), [20 fixed-seed examples](inverter_numeric_examples.md), and [reply-style diagnostic](inverter_reply_diagnostic.md) remain unchanged exploratory snapshots with incomplete coverage. They cannot be presented as full-bank follow-ups.

## Execution, validation and handover

BRIEF_R §24 preserves the original 2026-10-19 preregistration (originally §16, renamed after integrator assignment), the extra 90-minute deviation, and the dated continuation #2 allowance before its compute. Executed science remains full commit 6a92c54a9ae23ab49838681da2af4f528434a913, runner SHA 630bc2742aecddf8d616533cf21c59b92ade7fbc5a4aebf83c68c1da090dac64, manifest SHA d6a9afe7127f9f6d519bb2e6c3e55c2e467f13b54c1de4365c9b021427b0b6d6, inverter 110be8b18cfe66ce0d8ba4e940ed8a0065efc532. Site L44/chat/last, scale 192.28162145564332, greedy 256, generation batch 32, scoring batch 8, item order, candidates and all five arms stayed frozen.

Continuation #2 skipped every 99,990 existing key and wrote 11,000 new keys / 2,200 items into continuation-002 shards. Exactly 160 cached next-fact reconstructions passed configuration and source-state checks before reuse. It added 2,051 reconstructions, yielding 22,311 unique records: 22,198 item states plus 113 fact means. All 241 staging hashes passed. The first remaining fact smoke covered 1,000 fresh keys, all five arms, both labels; independent audit passed 6,011 checks.

Science ended 04:51:17.852 UTC; chain exit 0/job.done 04:51:19 UTC, before the unchanged 04:53 UTC cutoff. At that cutoff: 22,198 done, zero remaining. All 14 final-artifact hashes matched locally 04:51:21.970615 UTC; acknowledgment uploaded 04:51:40.236154 UTC through own-ID checked SSH. A fresh immutable union rejected duplicates, malformed tails and configuration/provenance mismatches; no rows were silently discarded. Primary independent audit passed 933 checks with 635 independent AUROC/tag estimates agreeing within 3.33e−16; 27 analysis/exploratory tests passed.

Warm handover to X1 completed 04:53:50.180305 UTC. X1 guards 8889/8890 were independently verified live with armed logs and account HTTP 200 at 04:53:33.199275 UTC. Inverter retired watchdog 1582 first, hard stop 1581 last. The Mac monitor retired on its verified transfer receipt 04:54:20.901611 UTC; the puller exited 04:54:25.153094 UTC after its last successful sync. Own-pod API confirmed **RUNNING** 04:54:42.935355 UTC. No inverter stop or provider resume occurred. The puller’s generic “finished reason=exited” denotes its own controller exit on transfer, not provider EXITED. The five-minute inverter-capacity-and-gated-run scheduled task is **deleted**, and no replacement inverter watch exists.

## Accounting and limitations

Continuation #2 custody billing is 04:14:26 UTC to the agreed X1 segment-start 04:52:31.392726 UTC: **38.089879 minutes, 0.634831313 pod-hours, estimated $1.136348 at $1.79/hour**. X1 pays the guard-overlap interval; actual guard retirement is recorded separately. This is inside the 45-minute allowance. Combined canonical usage across the original and two continuations is **3.939614646 pod-hours, estimated $11.059100**. Process wall and rounded integrator summaries are not added to these custody charges. Storage/taxes are excluded; these are estimates, not provider invoices. [Billing record](inverter_continuation2_billing.json).

The retention restart had erased the cache. Initial package setup failed under PEP668 before any inference; the isolated pinned venv repair and download completed in 392.209 seconds without resetting the cap. No scientific retry occurred. Original H100 runtime used torch 2.13.0+cu129/numpy 2.1.2; A100 continuations used torch 2.8.0+cu128/numpy 2.2.6, with transformers 5.18.0 and peft 0.21.2 unchanged. Continuation #2 logs reference PyTorch causal-convolution and linear-attention kernels. These hardware/runtime differences limit bitwise reproducibility; no mid-run package or kernel change was made. The inverter’s short-span training differs from these longer assistant-onset states. “Explained” would have been an operational AUROC criterion, not proof that Oracle literally reconstructs text internally.

[Full primary results, both bootstrap intervals and hashes](inverter_full_summary.json) · [Historical partial reports](inverter_history_through_continuation1.md). Raw outputs, final union, operational receipts and audits remain under cache/g_agreement/r/inverter/continuation2_20261020/. Main checkout files were untouched.

Final closure check: the own-pod API still reported RUNNING at 05:00:12.783730 UTC, after the retired inverter deadline. All 14 final-artifact and four union hashes passed recheck. The report CSV uses LF line endings; parsed values match the unchanged raw CSV exactly.
