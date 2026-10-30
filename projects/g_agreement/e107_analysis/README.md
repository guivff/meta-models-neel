# E107 once-only CPU adapter (§218)

Run only after committed source and synthetic tests, E82/E86 registered analyses,
and the full E107 bank seal:
`python3 -m projects.g_agreement.e107_analysis.adapter --spec SPEC.json`
No generation, judging, GPU, or replay of E82/E86/E81. Keep labels/private joins
CPU-side. A fixed E107 global guard is claimed before inference; source hashes
and complete custody are checked before any output is used.

## Estimands frozen before output

R-OL1 pools E82 belief-wrong items across surviving rows with item weighting,
not equal row weighting. Outside and reader each condition on their OWN output
stating a value. Paired bootstrap samples the SAME source items and recomputes
both conditional denominators, with separate parseability masks. Do not intersect
value-stating subsets or substitute the reader's subset for the outside subset.
Rows and source-item ID together identify an item; positions/target judgments
are not extra observations. Uses common/stats.py,5000draws seed0 (the existing
E82 adapter's registered backend/settings), percentile95% intervals. Undefined
conditional bootstrap draws make the CI unavailable, not zero or silently dropped.

Oracle: R-OL1 MET iff conditional belief-rate difference>=.20 and lower>0.
Falsifier iff point difference<=0 (outside at least as often). Missing denominator
makes the corresponding result NOT EVALUABLE. NLA checks appear separately as
DESCRIPTIVE. Belief-right and no-canonical-truth items are also reported separately;
neither enters the belief-wrong rule. No missing truth is inferred or manufactured.

E82 uses its TWO dedicated target judgments, belief and truth, as in its frozen
adapter: both must parse for conditional analysis; naming either value in either
code determines output states-a-value. A both-values assertion can mention the
belief and truth simultaneously; it counts as belief mention, not belief-only.
No-canonical-truth rows use their original belief-only judgment, descriptively.

E86 reports true-fact mention rate over all parseable outputs and, explicitly
labelled, a conditional-value-stating supplement. E81 uses original signed S
(target-only minus opposite-only; both/neither0). Per reader/row, all three systems
are restricted to the same design-available original source-item inventory, with
missing judgments retained separately. Outside/Qwen-self/reader S and both paired
differences are reported. Reader-exclusive means strictly higher point S than
BOTH baselines, with no new margin or significance gate. Absent baselines produce
unknown membership, not a reader-exclusive row. All37 row IDs remain in output.

The outside-describer/judge shared model-family bias is stated beside results;
no correction is invented. No truth/belief filters are derived from E107 readouts.

## Frozen source binding

SPEC: inventory_seal, inventory_sha256, inventory_commit(full40hex), output_seal,
output_sha256, prior_analyses={E82:{seal,sha256},E86:{seal,sha256}}, analysis.
Inventory seal must be committed before E107 outputs and bind INVENTORY.json;
experiment=E107, e81_rows (all37 unique original rows), surviving_e82_rows and
surviving_e86_rows (registered surviving grids). Bank scope is not silently shrunk.

Inventory record: id, bank E82/E86/E81, row, item_id (original source identity),
systems (available channels), unavailable_systems (other channel→explicit reason),
target_letters_by_system={system:{target:letter}}. E82 also cohort belief_wrong/belief_right/no_canonical_truth from
original source classification, never a new E107 selection. Required comparisons
are oracle,nla,outside plus qwen_self for E81. Outside must exist on every item.
If a source has no original belief-right group, preserve this absence in inventory
and report it; never synthesize a matched group. E81 must cover all37 rows.
Each system uses its own original frozen A/B map for belief/truth or S.
Legacy target_letters={target:letter} is accepted only when every actual sealed
system/target mapping equals it; no common candidate order is inferred.

Output seal: experiment E107,status COMPLETE,inventory_sha256,route_verified=true,
redaction_audit_complete=true,same_bank_rubrics=true,source_seals=[{seal,sha256}],
files including MEASUREMENTS.json. outside_generation exactly
{model:google/gemini-3.1-flash-lite,provider:google-vertex/global,temperature:0,
max_tokens:256,ZDR:true,data_collection:deny,fallbacks:false}. Owner must bind
original prompt prefixes and verbatim E81 generic instruction in source receipts.

MEASUREMENTS has one record per frozen inventory ID:
{id,systems:{channel:{target:{text:REF,code:REF,target_letter:REF}}}}. REF={seal_index,member,keys},
where keys lists dict keys/list indices leading to the exact sealed field.
Targets are belief+truth for truth-known E82; belief only for no-truth; truth for
E86; S for E81. Original code is {id,category,values,evidence}, or null for the
original UNPARSEABLE outcome; the standard explicit UNPARSEABLE code also works.
Do not replace it with a precomputed correctness score. Text/evidence validation
and mentions/S are computed by the adapter. Source seals include existing native
judgments, E81 generic outputs/codes and outside generation/judgments. All member
hashes and exact inventory/system/target grids are verified; no freehand scores.


## Prospective source-binding correction (I2-E107-SYSTEM-TARGET-LETTERS-20261029)

Original E82 Oracle/NLA target letters can differ for the same semantic target.
The adapter now verifies each declared per-system letter against an exact sealed
original target-map pointer before interpreting that system's unchanged code.
Outside uses its own frozen order. The legacy global map is safe only if all
referenced original maps agree; a mismatching/missing map fails before analysis.
No old code, evidence, rubric, target map or source seal is rewritten. The rule,
conditional per-output denominators, cohort/row scope, bootstrap and global once
guard are unchanged. Original7efe8816d receipt remains in SOURCE_RECEIPT_7efe8816d.
This correction and opposite-order semantic-equivalence tests precede any E107
output access. Freeze the per-system inventory before E107 generation/judging.


## Original E49 native regex provenance / unavailable categorical codes

Do not synthesize E56 codes from statements49.py or from aggregate
NATIVE_PRIMARY.json; do not rerun E49 scoring, rejudge, or pretend native text is
missing. For every E49 source item whose original per-item categorical code is
unavailable, retain the item and row in INVENTORY, use systems=[outside,qwen_self],
and unavailable_systems={oracle:"original categorical code unavailable; native
text present; original metric is statements49 regex",nla:same reason}. Preserve
original raw-text/hash/regex provenance in the CPU inventory's source receipts.
This is code availability, not source-item or native-text availability.

All14 E49 rows/all1176 items stay; every one of all37 E81 rows has a separate
E81_baseline_comparison reporting outside vs Qwen-self S on their full matched
baseline inventory. Reader comparisons require their original categorical codes;
without them, reader S/comparisons and reader-exclusive membership stay unknown.
The report distinguishes unavailable_native_code_items from failed judgments and
keeps the old regex metric separate; no aggregate native score is substituted.
For rows with original codes, the existing three-way paired comparison is unchanged.


## Prospective privacy companion (2026-10-29)

Before opening judgment codes, freeze the five-opaque-ID exclusion requested by
C at 08:52:12Z under 79f63fe0/25c32f25. This is post-generation, pre-analysis
source, not pre-acquisition. Primary rules.py, cohorts and 5000/seed0 are unchanged.
The same once-only invocation writes REDACTION_SENSITIVITY.json alongside RESULTS.
It reruns the unchanged report on a copy with each affected outside readout's
fields missing (both targets when applicable), retaining source-item pairing,
native values, all37 rows, explicit unavailable codes and per-output denominators.
No source items are dropped; the companion cannot replace the primary result.

The COMPLETE output seal now requires three original sealed REF pointers:
redaction_audit to PATH_REDACTION_AUDIT.json, redaction_plan_map to
REDACTION_PLAN_MAP.PRIVATE.json, and redaction_original_plan to the full frozen
plan list. Existing source_seals must include the original audit/unit seal,
REDACTION_MAP_SEAL.json and original PLAN_SEAL.json. Map plan_seal_sha256 and
plan_member_sha256 must exactly match the original plan pointer. All five
unique audit IDs must match map opaque_id values and plan_index/inventory_id/target
exactly; original and judge readout hashes remain in the sealed audit. No inferred
ID crosswalk. The owner must supply these original pointers before guard claim.

## Original E82 grouped representation
Native E82 text REF may resolve to the original sealed positions list. Validate the unchanged group code with original normalization and require its entire evidence within one original position; never concatenate evidence across positions or choose a primary position for analysis. Group-level code/target/statistic remains unchanged. Lists are rejected for other banks and outside readouts. This source-bound representation support follows the original e82_grouped_judge.validate_code contract, confirmed by 408f2c23f; it is a post-acquisition/pre-analysis validation fix, not a pre-output scientific amendment.
