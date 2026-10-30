> Latest Stage2 alias audit (2026-10-19 23:59 Europe/Zurich): cached optimum **242 test /525 pool**; minimum validated plan **14 new test states,0 pool** under the registered augmentation scope. Alias table committed before rerun; no collection/training. See [the complete audit](wr2_alias_audit.md).

# WR-2 Stage 2: cached repartition audit

**Final report — 2026-10-19 23:41 Europe/Zurich. Verdict: NO_SUFFICIENT_CACHED_PARTITION_DEMONSTRATED under the preregistered eligibility and holdout rules. The strengthened search has a solver-certified maximum of 244 held-out prompts, 12 below the unchanged 256 gate, while retaining 526 pool prompts. No training or state collection was run.**

The original hash-selected partition was unnecessarily small (130 test / 521 pool). Searching the same cached universe improves that to **244 test / 526 pool, 95 target identities, 31 prefix families, 10 independent groups and two test sources**. Every other numerical gate passes. Full captured inputs, candidate labels, metadata aliases, templates and capture duplicates were checked; the saved witness has zero registered cross-split conflicts. Semantic alias completeness is still unverified, so additional adjudication may reduce coverage further.

A tempting **257 test / 519 pool** optimum under the earlier observed-name exclusions is inadmissible. It has 17 registered name/exclusion conflicts across 16 pool rows, and uses 87 pool rows with unestablished target validity for this audit. This optimistic relaxation is reported explicitly rather than accepted as an adequate partition.

## Registration and search

BRIEF_R §19 was committed and pushed as `7ca927957c43ef4eba416b5f4cf915701322f72e` before new coverage counts or optimization. Implementation and the final pre-run group-closure correction were pushed through `bebc9ce02c1a667fa06c4c92062ef577e0d94667` before processing metadata. No repair or threshold change followed the new outcomes. The previous inventory and Stage 1 results remain unchanged.

Inputs are the frozen §18 workspace/context metadata (31 datasets, 11,224 indexed rows), its pinned banks/source metadata, and existing local L42/chat/last state paths and indices. The metadata-row SHA256 is `02ea8e6050d769da4f09453be937b82cf758b3680400cb59b7a33631c72926e8`. The audit reads index files and state file sizes, not array payloads. Original pool/test roles, identity-task eligibility, 2–4-token targets, LABEL_DEFECT exclusions and known-template requirements are preserved. No old test row can become training data. No new dataset, longer target, filler or relabeling repairs the shortfall.

The binary optimization maximizes unique eligible test captures subject to at least 512 pool captures and all name/prefix/group/source/both-suffix gates. It then fixes the certified test optimum and maximizes pool captures; a fixed SHA-rank objective resolves remaining ties. Both modes completed all three objectives optimally, well within the registered 180-second solver budget each. SciPy 1.18.1 / HiGHS ran on one thread with seed 0. The saved primary minimization objectives and dual bounds agree exactly: −257/−257 and −244/−244, with zero reported MIP gaps. These are solver-certified maxima, corroborated by independently checked witnesses and constraint matrices; no independently verified formal integer-program proof is claimed.

## Coverage gates

| Gate | Required | Earlier hash partition | Optimistic search | Strengthened search |
|---|---:|---:|---:|---:|
| Distinct test captures | 256 | 130 | 257 | **244 — fails** |
| Distinct pool captures | 512 | 521 | 519 | 526 |
| Complete target identities/combinations | 32 | 74 | 99 | 95 |
| First-token families | 8 | 26 | 31 | 31 |
| Independent challenge groups | 8 | Not audited with the new closure | 37 optimistic blocks | 10 |
| Test source families | 2 | 3 | 3 | 2 |
| Two identities and distinct suffixes in every selected block | Yes | Prior inventory rule | Pass | Pass |
| Full strengthened name/metadata exclusions | Yes | Not established | **Fails** | Pass for known exclusions |
| Semantic alias completeness | Established | No | No | **Unverified** |

The search universe has 290 candidate test captures before joint holdouts in both modes. The strengthened universe has 1,191 unique eligible pool captures, 18 fixed independent groups and 38 available prefix families before selection. These totals do not all coexist under the joint constraints. The independent-group closure was frozen over all eligible blocks before dropping unusable blocks, so an unusable intermediary cannot erase a shared-identity or shared-context dependency.

The numerical coverage guard is not a formal power calculation. Counts are deterministic metadata quantities, so no sampling CIs are attached.

## Why the optimistic 257-test partition is invalid

The old exclusion rule checked pool candidate/target strings but missed held-out names elsewhere in captured inputs and metadata. The selected optimistic witness has **17 registered exclusion edges across 16 pool rows and four held-out identities**; 16 of those edges occur in captured text. Concrete examples:

- Held-out target “the sol” appears in pool item `re-re_khop2_answer-pool-0009`: “The country that uses the sol is located on the continent of”.
- Held-out “the United Arab Emirates” appears in the context of Feng pool item `rx-x20_feng_capitals-pool-0165`, although its queried output is a capital city.

Some other triggers, such as “American” inside “American Samoa”, are deliberately conservative source-backed exclusion phrases. They are not assertions that the named entities are identical. The rule keeps these exclusions; it does not discard inconvenient aliases after seeing coverage. Details and all affected IDs are in [wr2_partition_optimistic_leakage_details.json](wr2_partition_optimistic_leakage_details.json).

The optimistic witness also uses **48 `rb_context_against_belief` pool rows** with provisional model-derived labels and **39 WorkspaceBench wrong-bridge pool rows** whose intended target validity is not established by bank/index equality alone. These 87 rows cannot qualify in this metadata-only audit. Four of the 16 name-conflicting rows are already in this ineligible set; removing the union leaves only 420 of the optimistic witness's 519 pool captures. That is a diagnostic of this saved witness, not an additional optimization.

There is **no actual template overlap in this particular optimistic witness** after the strengthened template mapping. Template closure remains a hard search constraint; the observed rejection is not attributed to a nonexistent template violation.

## Strengthened witness and holdouts

The strengthened test partition consists of 152 ReaderBench landmark→currency answers and 92 PersonaQA context examples (8 base, 84 fantasy). These are multi-token target identities/combinations, largely currency descriptions and favourite-value strings; they are not 244 unseen proper-name generation tasks. The pool contains 128 ReaderBench KHOP, 57 R-E KHOP and 341 Feng binding captures. Exact item IDs, states' row indices, target identities, prefix/suffix tokens, templates and fixed independent components are in [wr2_partition_ids.csv](wr2_partition_ids.csv).

The audit preserves original exclusions and adds global typed alias closure, complete-phrase checks in every system/message/prompt field and all supplied metadata values, conservative R-E country exclusion phrases, shared PersonaQA card/attribute frames, and ReaderBench bridge/answer template/capture links. Complete names are held out; their constituent pieces may occur in training. Country/capital/currency relationships and WorkspaceBench true/wrong bridge identities are not automatically merged as semantic aliases. Both suffix identities must remain in each selected same-question/first-token block. Repeated aliases, templates and connected source parents do not create independent groups.

All registered known-name/template/capture checks pass on the 244/526 witness, including independent raw-text checking. Every retained target identity is still marked **ALIAS_UNVERIFIED** in [wr2_partition_aliases.csv](wr2_partition_aliases.csv). Passing known exclusions is not proof that the finite corpus has no unrecorded semantic alias. Additional aliases or template mergers can only further restrict this registered search; they cannot lift its 244 upper bound without changing the rule.

## What remains missing

Within the fixed cached universe and registered constraints, another split cannot reach 256 while satisfying the other gates: 244 is the certified optimum. This replaces the earlier one-split statement of insufficient demonstrated coverage with an optimization result for the frozen universe. It is not a claim about every possible task, target definition, source dataset or newly collected state.

The arithmetic shortfall is now **at least 12 additional qualifying held-out contexts/states**, rather than the earlier partition's 126. This is a lower bound, not a promise that any twelve examples suffice. New examples would have to preserve complete-name/alias/template/capture exclusions, both suffix identities and all source/group requirements; the retained pool has only 14 captures above its minimum. Complete finite-corpus alias adjudication could require further exclusions and a larger shortfall. No new collection is authorized or attempted here.

Stage 2 remains unrun. Its full training preregistration, architecture/schedule, fixed aliases and h/native-token/shuffled-Jh/mean-Jh/within-prefix donor controls are still required if an adequate validated population is later available. h≈Jh equivalence is expected from J42's full rank; native-token and state-free contrasts remain informative. The random-subspace caveat from WR-2 is unchanged. This metadata audit gives no decoder-performance verdict.

## Independent verification and compute

The raw-input audit checked all 11,224 metadata rows and state/index joins, all template mergers and fixed group closure, typed source aliases and every one of the 741 pool→held-out-identity conflict links. Independent phrase matching found the same links, including 357 capture-based matches. The saved-witness audit recomputed every gate and cross-split intersection from raw metadata. The matrix audit reconstructed all 4,141 optimistic and 4,469 strengthened constraints, plus all auxiliary indicators; every constraint matches, and both selected witnesses have zero constraint violations under their respective modes. Solver-bound claims were checked against the recorded zero-gap primal/dual results. No audit reran the optimizer or read states/predictions.

| Run | CPU seconds | Wall seconds |
|---|---:|---:|
| Metadata build | 0.671423 | 0.693886 |
| Optimistic search | 0.779909 | 0.803483 |
| Strengthened search | 0.350307 | 0.360823 |
| Independent raw-input audit | 2.450837 | 2.500416 |
| Independent witness audit | 3.117460 | 3.205945 |
| Independent saved-matrix audit | 0.118102 | 0.140198 |

Instrumented build/search cost: **1.801639 CPU seconds**. Independent audits: **5.686399 CPU seconds**. These measurements exclude implementation/reporting and uninstrumented startup imports; they are not total elapsed task time. Zero activation payload bytes, GPU hours, fits, training, model forwards, downloads and collected states. Synthetic pre-run solver checks included brute-force comparisons, separate gate failures, suffix constraints and matrix serialization. Main checkout and cache link remain unchanged.

## Reproduction and artifacts

Use a fresh output directory so old results and audit files are not included in the new build manifest; preserve the original run artifacts.

```sh
wr2_repro_dir=$(mktemp -d /tmp/wr2-partition-repro.XXXXXX)
.venv/bin/python -B projects/g_agreement/r_bench/wr2_partition_build.py --repo . --out-dir "$wr2_repro_dir"
.venv/bin/python -B projects/g_agreement/r_bench/wr2_partition_solver.py --input "$wr2_repro_dir/optimistic_input.json" --out "$wr2_repro_dir/optimistic_result.json" --time-limit 180
.venv/bin/python -B projects/g_agreement/r_bench/wr2_partition_solver.py --input "$wr2_repro_dir/strengthened_input.json" --out "$wr2_repro_dir/strengthened_result.json" --time-limit 180
```

Committed artifacts include [build/source hashes](wr2_partition_build.json), [optimistic solver record](wr2_partition_optimistic.json), [strengthened solver record](wr2_partition_strengthened.json), [coverage CSV](wr2_partition_coverage.csv), [exact IDs](wr2_partition_ids.csv), [exclusions](wr2_partition_exclusions.csv), [alias status](wr2_partition_aliases.csv), [raw-input audit summary](wr2_partition_metadata_verification.json), [witness audit](wr2_partition_witness_metadata_verification.json), and [matrix audit](wr2_partition_solver_verification.json). Full input/conflict metadata, sparse matrices, bounds, variable maps, detailed raw audit and audit sources are under ignored `cache/g_agreement/r/i2/wr2_partition/`, with hashes recorded. Handoff is through `results/g_agreement/r/HANDOFF.md` on `r/i2-wr2`, for Guiv to relay.
