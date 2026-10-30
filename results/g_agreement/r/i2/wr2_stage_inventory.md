# WR-2 staged follow-up — multi-token coverage inventory

**Inventory decision — 2026-10-19 23:08 Europe/Zurich. Stage 1 can proceed on an explicitly expanded supplemental shared-prefix challenge: nine independent source groups and 2,098 distinct test prompts. Stage 2 has insufficient demonstrated clean coverage and will not run.** The original 88-fact population has only five direct shared-prefix pairs, or seven independent groups after valid sibling-positive regrouping. The expansion includes calibration news/code and short-pool frequency/typical-time facts; it does not replace WR-2's original naming-gap population.

The staged inventory was preregistered and pushed in BRIEF_R §18, commit `3705f5854ec81de24b6dcbbd57234e1796eded54`, before counting. No activation payload, new Jh mapping, token score, AUC, bootstrap, fitting, model forward or download was used for this inventory. All counts below are metadata coverage, not performance results.

## Coverage

| Population | Multi-token coverage | Shared-prefix coverage | Use |
|---|---|---|---|
| Original 88 WR-2 endpoints | 74/115 active candidate records; 73 have 2–4 tokens | 5 direct pairs, 1,000 distinct test prompts, 4 first-token families | Below the eight-group coverage guard |
| Same endpoints plus valid sibling-positive contrasts | Same frozen candidate definitions | 7 independent groups, 1,500 test prompts, 3,840 disjoint pool prompts | Below the eight-group guard; art-type pairs count as one source group |
| All 100 WR-2 eligible facts | 87/131 active candidates; 86 have 2–4 tokens | Includes three news/code facts sharing one target pair | Calibration stays identified |
| Broad nondefect R-A upper inventory | Includes calibration and short-pool facts | 9 independent groups, 2,198 distinct test prompts, 5,310 pool prompts after removing 65 cross-split duplicates | Supports an explicitly expanded Stage 1 challenge |
| Frozen Stage 1 challenge | 18 full candidate strings, 5 first-token families | 9 source groups, 2,098 distinct test prompts | Meets Stage 1 coverage guard |
| Workspace/context identity-combination upper inventory | 927 test / 1,283 pool prompts with 2–4-token targets | Potential same-question regrouping: 290 test prompts, 118 targets, 38 prefix families before joint holdouts | Includes fictional PersonaQA combinations; not all targets are hidden proper names |
| Prospective Stage 2 partition | 74 held-out complete target identities, 26 prefix families | 130 test / 521 pool prompts after known joint exclusions | Fails the 256-test guard; alias completeness also unresolved |

The broader workspace inventory includes 31 datasets and 11,224 rows, with 2,184 test and 4,419 pool prompts having 2–4-token targets. Every selected row has a local L42/chat/last state file and matching index entry. Thus the main gap is target/split coverage and metadata, not a missing bulk state directory. Frozen bank hashes match; index collection SHA is `4d482b6`, with matching IDs, labels, splits and array shapes. Array contents were not read or checked for finiteness. The indices lack direct bank/prompt-byte SHA binding, so metadata agreement is not a new numerical state audit.

## Frozen Stage 1 challenge

| Source contrast | Test prompts | Notes |
|---|---:|---|
| Five-star / lower-rated review | 200 | Original endpoint |
| News headline / code sample | 587 | Calibration expansion; 300/287 classes after deduplication |
| United Kingdom / United States | 200 | Verified sibling positives only |
| Book / song | 200 | One lexicographically selected art-type pair; avoids counting three dependent pairs |
| Frequency / typical-time question | 111 | Short-pool expansion; 61/50 classes; token lengths 3/4 |
| Solution B / solution A | 200 | Original endpoint |
| Answer A / answer B | 200 | Original endpoint |
| Morally wrong / morally acceptable | 200 | Original endpoint |
| Democrat / Republican | 200 | Original endpoint |
| **Total** | **2,098** | **Nine independent source groups** |

Thirteen duplicated news/code rows are removed by lowest item ID. No test prompt crosses challenge groups. The manifest freezes all IDs, labels, state row positions, sources/hashes, tokenizations and surface lists: `wr2_prefix_manifest.json`, SHA256 `30707fee099f583a4343a09b4931c96782bd126dad8030ad8d298eeaa3be9c3e`.

Literal first-canonical-token scoring ties on every pair. Historical native scores do not: for example, full “solution B/A” starts with the same token, while historical native “B/A” differs. All five direct endpoint pairs have distinguishable native short forms. The +0.174 naming gap remains tied to that historical native control. A gain over an identically tied first-token score is not recovery of +0.174 by itself.

All existing surface variants are reused exactly. New frequency/typical-time forms use a fixed case/space-only list. The unequal-length pair gets common-prefix-removed diagnostics; variant synonyms that remove the collision are disclosed. These fixed descriptions mostly test suffix-sensitive classification, not generalization to unseen entity names.

## Stage 2: what is missing

The existing broad identity/context inventory offers 290 potential same-question shared-prefix test prompts before simultaneous name/template exclusions. It is not valid to treat all of them as clean held-out generation examples.

A prospective deterministic partition was stated before its counts: normalize known template families; hold out templates when SHA256 of `wr2-stage2-inventory-template-v1|<template>` modulo 3 is zero; retain original test rows from those templates in same-question prefix groups with at least two suffix identities; remove pool rows sharing any held-out template, target/candidate alias identity or capture. Unknown template identities cannot count as clean. The result is 130 unique test prompts and 521 pool prompts, with 74 complete target identities and 26 prefix families across Feng binding, PersonaQA context and ReaderBench KHOP.

To meet the registered minimum under this partition, supply **at least 126 additional distinct held-out prompts/states** with the same grouping and leakage exclusions, while retaining at least 512 suitable pool states. Each requires the pinned model's L42/chat/last h (or verified equivalent Jh), ordered item ID/index, target name and complete accepted aliases, source entity/context and prompt-template family, split, collector/model provenance and input hashes. Preserve both competing suffix identities within prefix groups; repeated aliases/paraphrases do not add independent groups. Complete semantic alias adjudication is still needed for the existing retained sources. No J/W download or new decoder training solves that metadata gap.

This is one deterministic split, **not a proof that no alternative cached partition can work**. An independently frozen adequate repartition could also address the coverage gap. The present inventory does not justify a decoder pilot or a negative decoder verdict. Stage 2 therefore remains unrun, with no full training preregistration claimed.

If Stage 2 becomes feasible, h≈Jh equivalence is expected because J42 is full rank; the informative comparisons are against native-token-only and state-free controls. Its separate registration must include all previously proposed controls, free-running exact match, donor-suffix following, and the +10-point/paired-CI rule. The strong random-subspace recovery in WR-2 still prevents a uniquely privileged J-geometry or causal-use claim.

## Reproducibility and artifacts

- `wr2_stage_ra_inventory.json`, `_facts.csv`, `_challenges.csv`: all 113 R-A facts, exact original100/88 roles, LABEL_DEFECT exclusions, multi-token counts, source grouping and valid regroupings.
- `wr2_stage_workspace_inventory.json`, `_coverage.csv`, `_groups.csv`, `_direct_components.csv`: workspace/context inventories, source hashes, target/prefix groups and coverage cautions.
- `wr2_stage_workspace_split.json`, `_ids.csv`: prospective partition algorithm, exact retained IDs and failed coverage gate.
- `wr2_prefix_manifest.json`: full Stage 1 test/variant manifest committed before scoring.
- Inventory and manifest-building scripts are isolated under `projects/g_agreement/r_bench/wr2_stage_*` / `wr2_prefix_build_manifest.py`.
- Large per-item inventory rows/memberships are stored under ignored `cache/g_agreement/r/i2/wr2_stage_inventory/`; no full state payloads are duplicated.

Inventory execution is CPU-only and well below the five-CPU-minute cap. Exact measured run timings are in the shared ledger. Header-parser API errors were repaired before results; repeated metadata runs and the incomplete timing coverage of those early failures are disclosed. GPU usage is zero. Main checkout files and cache link are untouched.
