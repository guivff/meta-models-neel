# E105 once-only logits analysis (§214)

CPU only; no reader or judge. Precommit source, tests, and full input inventory
before E105 output. Amendment2 (157fb545), applied before any analysis/output opening,
requires waiting for the two restarted rows to resolve before the sole run:

python3 -m projects.g_agreement.e105_analysis.adapter --spec SPEC.json

SPEC fields: inventory_seal, inventory_sha256, inventory_commit (full40hex Git
commit); output_seal, output_sha256; e100_targets (original E100 CPU target seal,
SHA256 f1c97d6800972346241385ee2e18e02ffc12c01767827d6e44d26da7cace2e35);
analysis (new result directory). The fixed experiment-global guard cannot be
redirected. Every adapter/dependency must be committed and unchanged before any
output is opened. Source references are validated before claiming the guard.

## Input and acquisition binding

The committed inventory seal: experiment E105, block44, same_value_seed20261030,
supplied_vector_mode=true, behaviour_mode=frozen_continuation, new_text=false,
files binding INVENTORY.json. Include all84 test items in each of format_plan,
language_plan,fact_recall,nesting_depth,indent_level,page_range_digit. Labels and
original IDs remain CPU-only. No output may appear in this inventory.

INVENTORY records contain unique id, item_id (E100 opaque carrier identity), row,
split=test,T_donor_id,S_donor_id,source_label,T_label,S_label,candidate_A_label,
frozen_scorer_sha256,candidate_ids_sha256,candidate_pair_count. T_donor_id is checked
against E100's original pairing. T has opposite label; S has the same label and
is a different item in the same row; donor labels are checked against the E100
CPU targets. The owner freezes S pairings with seed20261030 before acquisition.
Candidate_A_label specifies the original frozen A-minus-B orientation, never a
post-output choice. Frozen scorer and candidate token hashes remain unchanged
across T/S/0. Runner must consume supplied residuals exactly, with no renormalizing
or rescaling. Normalization may not change the continuation metric.

The output seal contains experiment E105,status COMPLETE,inventory_sha256,
source_seals=[{seal,sha256}], files binding MEASUREMENTS.json. Its records have
id and conditions keyed T,S,0. Each condition is an exact source pointer
{seal_index,member,keys}: keys is a list of dict keys/list indices leading to the
raw pair_logprobs array in the original verified output JSON. Pair scores are
full frozen continuation sums (not first-token approximations or length averages).
Multiple frozen pairs are averaged as E101. Missing/non-finite/incomplete data
fails closed; no dropped items within any completed row. The original504-item
inventory remains intact; all252 condition evaluations of every completed row
are required, and only amendment2 terminal operational failures may be absent. No scalar precomputed contrast can be supplied in place of raw pairs.

## Estimands and rules

c is T donor-value log probability minus the other value, with that SAME
orientation applied to T,S and0. Reorienting S to its own donor would invalidate
Delta. Delta is itemwise c(T)-c(S); bootstrap draws paired items, not independent
condition samples. Uses common/stats.py bootstrap_ci with2000 draws,
seed20261027,95% percentile CI, preserving the established E101 analysis settings.

A flip under T/S is strict sign reversal versus that item's own unpatched contrast.
Zero baseline/intervened contrasts are ties, not flips; all84 items stay in the
rate denominator, and tie counts are reported. Both direction reversals count.
Output includes per-row Delta/CI, T/S/0 means/CIs, T/S flip rates and paired flip
difference with CI. The shared seed gives identical item draws across statistics.

Gate: positive Delta with strictly positive lower bound on>=2 completed control rows.
Otherwise R-BT1 NOT EVALUABLE. R-BT1: same positive Delta/CI AND flip(T)-flip(S)>=.20
on>=2 completed missed rows (both if only two complete). No additional CI criterion is imposed on the flip difference.
Falsifier: Delta lower<=0 on ALL3 registered missed rows, reported separately from the gate.
Nesting-depth prefix bias and page-range baseline affect flips, not Delta. Neither
metric nor thresholds may be changed after output; the source/guard prevents replay.


## Amendment2 final restart disposition (required even if all six succeed)

The output binding seal must contain restart_resolution={status:
"E105_RESTART_RESOLVED",authority:"§214 amendment2 / 157fb545",rows:{...}}.
All six row names appear. COMPLETE entries have source_seal_index pointing to
the COMPLETE original row seal; every measured condition must point to that same
source index. Only indent_level/fact_recall may instead be NOT RUN (operational),
with attempt_seal_indices containing TWO distinct verified NO_FIT seals (initial
model-loaded failure and single restarted failure). No partial failed-attempt
score enters analysis. Other dispositions require an explicit source-contract
update, never guessed mapping. No run before the Integrator's final resolution.
R-BT1 and control gate still need2 successes. Amendment2 does not amend the
falsifier: it retains all3 missed rows, with an operationally absent row unknown.
If every completed missed row has lower<=0 but one is NOT RUN, falsifier is
NOT EVALUABLE; a known lower>0 makes it NOT MET. No fake zero, unknown statistic or favorable cell selection is
inserted for NOT RUN rows. Aggregate report lists those rows explicitly.
Original scientific formulas/bootstrap/orientation/guard stay unchanged; original
659fba82c receipt is preserved alongside the amendment receipt.

CPU binder: python3 -m projects.g_agreement.e105_analysis.bind --plan PLAN.json --out <new_binding_directory>. PLAN retains final six-row dispositions and exact output/input hashes from Integrator custody. The binder verifies all seals and copies only each original MEASUREMENT_INDEX pointer; it never parses raw scores or failed-attempt payloads. SPEC.json and NORMALIZER_RECEIPT.json are written for the sole subsequent adapter invocation.
