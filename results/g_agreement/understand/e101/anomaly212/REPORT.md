# E101 §212 anomaly check

**No code defect found; the sealed null dose results stand.** Dev-only check completed within the one-hour limit, before00:00CET. No dose-step rerun was performed and no original dose receipt or test result was changed.

| Row | Unsteered target-side | Sealed target-side at every α, both blocks | Actual GPU hook delta norm at α4, block44 | Block42 |
|---|---:|---:|---:|---:|
| format_plan |42/84|42/84|145.322–147.501|141.011–143.309|
| nesting_depth |42/84|42/84|164.543–164.600|158.934–159.047|
| page_range_digit |0/84|0/84|59.235–59.250|57.108–57.122|

**(a) Patch application:** all504dev hook observations (84items×3rows×2blocks, α4) have nonzero steered-minus-natural residual norm. The next block receives exactly the supplied bf16 vector in504/504cases. Separately, all2016original dev cells (all four α values) have nonzero correctly oriented cached residual deltas. Per-item logs are in RAW_DIAGNOSTIC.tar.gz: CPU_PER_ITEM.json for all doses and gpu/HOOK_DELTAS.json for the full-checkpoint observations.

**(b) Contrast sign:** all252dev candidate/value joins pass. CandidateA is label1 (list, one closing bracket, or the item's A digit), and target sign is1−2label. The raw directions equal dev mean(label1)−mean(label0) at each block; every composed delta points toward the other class. The acquisition source used here is byte-identical to the original executed archive sealed e966429e. No hook, scoring or orientation fix is indicated.

**(c) Unsteered baseline:** measured with base Qwen, the same frozen candidate token sequences and summed continuation log probabilities, with no intervention hook. The84dev baseline target-side indicators match the original steered indicators item-for-item for every α at both blocks, not merely in aggregate. Counts are42,42,0 as shown.

The sealed contrasts do vary with α, but never cross zero to change the frozen target-side outcome. Nesting's short candidate token sequence `[2205]` is a strict prefix of `[2205,4891]`; the full sequence-probability score therefore structurally favors the short candidate. On a balanced opposite-target set this gives42/84 at baseline as well. This is a limitation of the frozen metric, not a code defect and not authority to change it.

One owned H200 pod z51f92frrp1vvs ran the smoke under1800s creation custody. Raw output hashes were verified after pull; public inputs were deleted and the pod is EXITED. Conservative elapsed/cost upper bounds:245.6s,0.0683GPU-h,USD0.361. Guards retired. An SSH launch-confirmation timeout required monitoring adoption of the same still-running worker; the worker was neither restarted nor replayed. No test items or readouts were inspected. The complete source, raw diagnostic outputs, per-item delta logs and custody receipts are sealed in SEAL.json/RAW_DIAGNOSTIC.tar.gz.
