# E126 §235 — read-token restoration and insertion, logits only

Inventory before writing: E105 normalize/rules/common bootstrap and original
E104/E109 cohort transport; no E126 adapter or runner binding existed. Reuses
E105's fixed steered-minus-original candidate orientation, averaging across the
original frozen continuation pairs, and common.stats.bootstrap_ci with original
2000draws/seed20261027. The required statistic here is the MEDIAN, not E105's mean.
E105 source/guards/results remain unchanged. R-Q reviews. No reader/judge/model
calls or acquisition are performed by this adapter.

Rows: original E104-U/E109 flipped cohorts,84fact_recall and50language_plan.
Blocks:44,48,52,56,60. Both restore and insert; read_token main patch plus
non-steered earlier_token and random_norm_matched controls. Clean/steered native
log-odds use the original E104 frozen continuation pair(s), all candidate tokens,
no re-rendering, first-token shortcut, new candidate, score fitting or sign choice.

For each item, first compute gap = steered-clean. Restoration R_L =
(steered-patched_restore)/gap; insertion I_L = (patched_insert-clean)/gap. Compute
the ratio separately for main and both controls, then median and percentile95
item-bootstrap CI at each block/row/direction/control. Never use ratio-of-means,
clip, take absolute values, winsorize, or pool rows. Raw log-odds medians appear
beside aggregate ratios; all per-item raw odds and ratios remain local CPU in
PER_ITEM.PRIVATE.json (mode600). Near-zero nonzero gaps are not regularized.
Exactly zero gap stays undefined with item/count retained; an affected full-cohort
median/CI is NOT EVALUABLE, never computed on a silently smaller cohort.

## Registered rules and Guiv's pre-output control clarification

Direct Guiv: "Yes: restoration controls at all five blocks; insertion descriptive."
Thus R-MED1 on fact_recall is median main R>=.50 with lower95 strictly>.25 at52
OR56, main R44<=.15, AND BOTH RESTORATION control medians<=.15 at EVERY one of the
five blocks. No additional CI gate on R44 or controls. Falsifier on fact_recall:
all five main restoration medians<=.15 with both restoration controls equally
low at all five blocks. Unknown medians give three-valued NOT EVALUABLE unless
another failed criterion already rules it out. Negative ratios remain signed;
"<=.15" is not changed to an absolute-magnitude condition. Language_plan displays
the same pattern checks descriptively, with no second confirmatory promotion.
Insertion medians/CIs and all mixed block/row outcomes are descriptive.

## Prospective source contract — complete binding required before execution

`python -m projects.g_agreement.e126_analysis.adapter --spec SPEC.json`

CLI checks all committed package/dependency bytes before SPEC or outcome IO.
SPEC: inventory_seal/inventory_sha256, e104_private(original495bbb19),
output_seal/output_sha256, analysis(new local CPU directory). Canonical once guard
is wt-internals-b/cache/g_agreement/understand/e126/ANALYSIS_ONCE.json. No duplicate
executor or resetting a consumed guard; failed claimed runs require an actual
recovery ruling. Source preflight occurs before claim; statistics after claim.

Inventory seal: experimentE126/statusSOURCE_ONLY_COHORT_BOUND,
labels_cpu_only:true, source_e104_private_sha256:495bbb19, files binding
INVENTORY.json. It maps each row to original item_id, steered_value(A/B),
candidate_A_value(A/B), pair_count, candidate_ids_sha256. Original identities and
steered targets are independently verified against unchanged E104U steered/flipped
private records. The exact frozen candidate/token/orientation mapping must have
an original CPU-source proof; no target or cohort inferred from outputs.

Normalized output seal: experimentE126/statusCOMPLETE/inventory_sha256,
blocks[44,48,52,56,60], labels_cpu_only:true, logits_only:true,
new_reader_or_judge_calls:0, steer:{block:40,positions:eight_before_read,
alpha_by_row:{fact_recall:8,language_plan:2}}, source_seals:[{seal,sha256}].
All original source/member hashes verify. Numerical sources must be COMPLETE
E104/E109/E126; failed/partial pilots cannot enter. MEASUREMENTS.json maps each
row to item_id,clean,steered,patches[block][restore|insert][patch_type]. Each cell
contains identity and raw pointers {seal_index,member,keys}. Pointers lead to the
ORIGINAL sealed CPU identity join and raw record, never normalized scalar scores.

Identity fields: item_id,row,direction(clean|steered|restore|insert),block(null for
native),patch(null for native),raw_id,steered_value,candidate_A_value,pair_count,
candidate_ids_sha256. Interventions additionally bind patch_binding_verified,
position,read_index; main/earlier replacements bind unscaled_residual_replacement.
Earlier index must be before read_index-8, outside all eight steered positions.
Read/random patches use read_index. Random additionally binds norm_matched and
original random_seed. These flags need actual source/operator/CPU test evidence;
an unsupported flag is not a scientific validation. The raw record must have
id=raw_id and original pair_logprobs in frozen pair order; all finite full-sum
log-probabilities, no partial continuations or scalar contrast substitution.

If the runner's frozen envelope differs, provide its original source/schema for
a tested custody-only compatibility map BEFORE first opening. Do not fabricate
identity fields, rescore or modify original outputs to fit this interface. Runner
owner C/TrackQ owns exact original earlier/random construction and supplied-vector
norm/source proof. Adapter does not choose positions, random directions or doses.

Output: RESULTS aggregates/raw medians, BINDING, local PER_ITEM.PRIVATE, original
ANALYSIS_SEAL. The local seal binds the private audit member. Publish a separate
hash-only receipt plus aggregate RESULTS; NEVER copy the private audit/join to
Git/pods or silently strip its member from the original seal. No E126 real
outputs were opened and no scientific guard consumed during source development.

TrackQ SPEC31b01f02 source-compatibility clarification: COMPLETE original E105 numerical source is accepted only for direction=clean. Patched and steered scores retain the E104/E109/E126 whitelist. This preserves exact original clean pairs, identity checks, rules and guard; synthetic tests cover acceptance and rejection on steered/patched cells. R-Q checks source diff before run.
