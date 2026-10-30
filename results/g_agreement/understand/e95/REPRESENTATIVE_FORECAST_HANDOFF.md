# E95 representative measured forecast and multi-row binder

Registration: BRIEF §204 E95 deviation1, with clarification1/2 unchanged. The
registration requires a measured whole-program forecast and ordered reductions;
it does not require measuring every row again after each reduction. That stricter
condition remains available in the legacy package95 path, but is an implementation
restriction, not a registered experimental requirement.

Use `results/g_agreement/understand/e87/representative95.py`. It validates actual
PROFILE_ONLY seals through package95, then transfers measured native batch means
by the exact (reader, real/placebo, layer, achieved width) key. It uses the maximum
phase mean when several profiles cover a key. Width5 is never inferred from width8;
missing keys remain explicitly unmeasured. One original-source timing package
covering those missing keys is sufficient;80new timing pods are not required.

The original timing archive is hash-verified. Every measured scientific source and
dependency must remain byte-identical; timing95's measurement path is compared by
AST with only its production-admission validator excluded. Only CPU packaging,
production admission and tests change. Native readers, decoding, capture, matched
placebos and RNG streams are untouched. The new runtime source seal is distinct
from the measured source seal and the decision retains both.

Forecasts amortize measured setup, staging and warmups once per whole-row shard.
Capture uses the maximum measured per-item capture time; measured and target
prompt-length ranges are reported, not claimed equivalent. Placebo construction
is charged per global RNG row traversed, including skipped indices. Native work
uses exact phase counts. Each shard adds60s retrieval and multiplies the total by
1.25. Actual prior E95 custody is added once against the whole144000s ceiling.
These are representative forecasts, with runtime NO_FIT still active.

Reduction order is unchanged: drop20; first20real items (placebos stay15); then
dev AUROC>=.90. Covered-component forecasts exceeding40h can justify proceeding
to the next reduction despite another component being unmeasured. Otherwise an
unmeasured component blocks binding. Unknown/invalid AUROC blocks stepiii; it is
never treated as failing or passing. Optional quantitative evidence must reference
sealed dev-only metric values through exact JSON pointers. See evidence_values
and the synthetic test for its DEV_PROBES.json/source_seals interface.

Run on CPU from the repo root:

```sh
python results/g_agreement/understand/e87/representative95.py \
  --scope /private/tmp/e95-timing-scope-v1 \
  --profiles VERIFIED_PROFILE_DIRECTORY/MEASURED_PROFILE.json \
  --prior-seconds ACTUAL_E95_CUSTODY_SECONDS --shards 8 --out FRESH_DIRECTORY
```

The output always includes MEASURED_DECISION.json with the reduction trace. A
blocked decision creates no executable request. Only a complete within40h decision
creates source/public input archives, grouped by remaining versus E87-reuse mode,
with exact whole-row membership, frozen first-item order and rebuilt seeded judge
index. These packets stay HOLD_I3_GLOBAL_ADMISSION, full_launch_allowed=false.

Before production, I-3/Integrator must bind fresh global GPU/judge liabilities,
real quote, immutable image/stack/assets, original pod-creation deadlines and own
guards. Assignment must match each timing95 hardware/scope field and carry
measured_profile_set_sha256 (aggregate evidence digest, not a single-profile hash),
measured_decision_sha256 and e95_integrator_admission_sha256. Only I-3 can promote
HOLD to READY and re-seal. E87-reuse shards additionally need their original row
hardware receipt through the existing --reuse-hardware contract. The existing
STATEMENT_SCORE_ELIGIBILITY receipt is hash-referenced, preserving category-switch
NOT EVALUABLE entries. No automatic GO, allocation, judging or outcome analysis.

The source archive includes STATEMENT_SCORE_ELIGIBILITY.json as an explicit pinned
dependency, so standalone CPU forecast/tests do not depend on a sibling checkout.
Compatibility with the original measured source permits only that added CPU JSON
dependency; every pre-existing dependency pin and all scientific code remain fixed.

Dev evidence update: Guiv authorized fixed original E49 weights on original devitems, without refit/sign change. Sealed97a8112e5 evidence passes the binder; DEV_EVIDENCE_INTAKE.json records the resolved9remaining-row scores and fitting-set caveat. The frozen candidate has62remaining+10reuse rows. No complete forecast was rerun; await the original-source row19width5 timing profile before the next full decision.
