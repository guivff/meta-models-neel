# §49 — Confirmatory J versus ⊥J split on the two-hop bridge bank

Registered 2026-10-21, before §49 compute. Owner: remainder. Section assigned by Guiv. Budget: ≤2 GPU-h including setup, smoke and verified pulls. This registration supersedes the earlier section-request sample-size uncertainty and earlier SENSITIVITY ≠ USE rule.

## Frozen sample and arms

Use **all 196 items in the full frozen SWAP bank**, with no selection, subsampling, replacement, new correctness gate, or exclusion based on reader/flip outcomes. `bank_inventory.json` freezes all 196 existing khop d_swap IDs from the saved SWAP rows. The current local source hash is recorded as observed, not represented as the historical run hash. Preserve these IDs across every arm and α. Missing/invalid rows must be reported and resolved before a complete confirmatory verdict; do not reduce the denominator or count missing results as non-flips. Smoke items remain in the full bank and are not selected out.

Reuse `projects/g_agreement/r_bench/swap.py` and the frozen bank. Split Δh into J and orthogonal-complement components, rescaling **each position** independently to that position’s full-edit norm. Include random directions at the same per-position norm and preserve natural/full-edit references. α = **1, 1.5, 2**. Replication reference: ownership report b6f2e7a91c6bd9d7894fd3c83f55de57c4bea7b9 on s/import-for-main; report cites original norm-matched preregistration mm:7c625ae.

## Measures and rule

Measure answer flip rate and read-back toward the swapped bridge for Oracle lens, NLA, skip-lens, R-Lens and J++. Report circular J-lens separately, outside confirmatory verdicts.

Per reader, label **SENSITIVITY WITHOUT USE** iff at α=1 all hold:
1. J-part flip-rate two-sided 95% Wilson upper bound ≤0.05, n=196.
2. Read-back(J) − read-back(random) is positive with its CI excluding zero.
3. Read-back(J) ≥0.8 × read-back(⊥J).

Higher α results do not replace the α=1 test. No change to the threshold after seeing outcomes.

## Pre-compute arithmetic correction

Standard two-sided 95% Wilson, z=1.959963984540054, gives:

| Flips / 196 | Upper bound | ≤5% |
|---|---:|---|
| 0/196 | 1.922253% | Pass |
| 3/196 | 4.402745% | Pass |
| 4/196 | 5.129000% | Fail |
| 5/196 | 5.831764% | Fail |

Thus the exact cutoff is **at most 3 flips**, not 4. This corrects arithmetic in the instruction while preserving its explicit n, confidence convention and ≤5% threshold.

## Execution readiness

Sample, arms, α grid and decision rule are registered; no §49 compute has started. A launch-ready receipt must additionally pin the reused bank content/code hashes, projector/rank and sites, reader assets, read-back endpoint and paired CI procedure, random seeds/replicates, zero-component handling, exact commands and cap enforcement. Those operational details are not certified by this sample-size registration. Do not launch from this document alone. No design change or threshold relaxation is authorized to fit the budget.

## Deviations

None; the Wilson arithmetic correction above is recorded before compute.

## 2026-10-21 implementation freeze, before compute

Guiv resolved the full-edit question: **donor-minus-recipient bridge activations**, not the older SWAP J-lens gradient. `plan.json` fixes all 196 recipients and donors. Donors come from those same 196 IDs, share the recipient's template, and differ in bridge and answer; select the minimum SHA256 of compact JSON `[20261021, recipient_id, donor_id]`. No activation, norm, model correctness or reader output enters pairing. All recipients have eligible donors. The swapped-in bridge and answer are the chosen donor's values, which need not be the old SWAP distractor. Donor reuse is retained and reported via donor-bridge clustered uncertainty.

Use the native donor and recipient bridge-span-end vectors at zero-based block-output **38**; Δ = h_donor − h_recipient at that one position. Unedited positions receive zero displacement. The full arm at α=1 replaces the recipient site with its donor. This chooses the ownership edit layer to match its frozen J projector; it does not reuse the old L24 SWAP intervention or claim to reproduce its effect. Copy, never refit, `jspace_L38_r384.pt`, SHA256 `372946128c4b303070d5926a91a34694b11d5307049d18c410377501cbda0f33` (top384 right singular vectors of W_U·J38, no gain). Verify orthonormality. Work in fp64 for projection/norm arithmetic, then fp32 displacement and target-native injection. Nonzero full displacement with a component norm ≤1e-6 aborts; do not substitute a random direction or exclude the item. Exactly zero full displacement gives zero arms. Two Gaussian random replicates use NumPy default_rng seeded by the first16 hex digits of SHA256 compact JSON `[20261021,item_id]`; norm-match each at the edited position.

Capture downstream last-prefill states, independent of generated answers: NLA block42; Oracle, skip-A, R-Lens, J++ and separate J-lens block44. Oracle uses its native bullet teacher-forced paired scores; NLA uses `The country is {X}.`; skip-A uses its native bare/space continuation forms. J/R/J++ use maximum single-token-variant pulled-back cosine for each bridge. J++ uses the pinned Jacobian with the same candidate scoring interface as J/R, not a top-token lexical proxy. No question or source text is added to analytic lenses. Checkpoint revisions and hashes are fixed by core/config.py, manifest/assets.json and section49.py's JPP pin. No new fits, probes, judges or paid API calls.

Read-back is the ownership-style **follow rate**: per item, the original-minus-donor native margin strictly decreases from its natural baseline. Ties are non-follow. Random read-back averages the two replicate indicators within each item. Report native margins alongside binary follow. The 0.8 criterion compares nonnegative follow rates directly (`mean(J) >= .8*mean(perp)`), without division or a special denominator. For J−random, use 2,000 paired item bootstrap draws, seed0, plus original-bridge and donor-bridge cluster bootstraps; use the widest 95% interval envelope. Verdicts are per reader without a familywise-error claim; no selection of reader, α, site or favorable interval.

Answer flips use greedy8-token continuations, uniquely parsed against the frozen bank's answer vocabulary by case-insensitive whole-phrase matching; compare the parsed answer to that same item's natural parsed answer. Do not gate on natural correctness. Ambiguous/unparsed outputs abort a complete verdict, without dropping any item or claiming non-flips. A zero-replacement smoke must reproduce the natural answer and downstream vectors within declared numerical tolerance.

Smoke is the four longest frozen prompts (ID breaks length ties), retained in the final196. Capture all196 natural bridge vectors first; smoke every edit/α and every reader. Full completion requires all64 smoke cells per reader, their intact hashes and a passing projection. Project remaining192-item target/readout time from the measured smoke, multiply by1.25, include repeated target/NLA setup and reserve max(600s, twice512MiB/measured pull throughput). Allocation/setup/holds count against7200s from provider creation. A subprocess deadline enforces the science cutoff; independently maintained exact-pod hardstop/watchdog remain mandatory. Failed timing/coverage/zero/numerical gates preserve partial evidence, with no automatic retry, reselection or scope reduction.

Runtime artifacts: model and six reader JSONL tables, downstream state NPZ files, natural state checksum, timings, projection, results and failure/exit logs. Each complete reader table has196×16=3136 cells; all six have18,816. Finalization verifies complete unique coverage before a verdict. Mac receipt hashes every packaged file; remote release rehashes retained files against that returned receipt before VERIFIED_READY_TO_STOP. Stop only the assigned pod; never terminate the volume. Record creation-to-exit GPU-hours and command/wall-clock logs after execution.
