# Once-only CPU analysis adapters

E101 is first. No GPU/model calls. Run only from committed source; `common.committed`
checks every source/test/schema/document in this directory plus pinned dependencies
before opening a run specification or any readout. Every production analysis claims
one fixed experiment-global guard in wt-wmech/cache; no override or replay option.
W-internals owns the existing E56 blind judge route. Export is not judging.

## E101 (§209, clarifications 1–3; clarification 3 commit 22729040)

`python3 -m projects.g_agreement.analysis_late.e101 export --spec SPEC.json`
then W-internals judges the emitted WIRE_PACKET using the existing route. Once the
route/privacy receipt is sealed:
`python3 -m projects.g_agreement.analysis_late.e101 analyze --spec SPEC.json`

SPEC has experiment E101, cohort `steered_flipped`, dose_path, full dose_commit,
dose_sha256, runner_source_sha256, targets, baselines, shards, blind, private,
judgments, analysis. Targets/baselines and each shard input/output are objects
`{seal: absolute_path, sha256: exact_full_hash}`. No placeholders may be supplied
at execution. The output seal must be COMPLETE test, tied to the committed dose and
input hash. All 7×84 items are represented CPU-side even when no dose exists.

The CPU TARGETS.json seal has experiment E101 and labels_cpu_only true. Each target:
`id` (runner base_id), row, split=test, property, values={A:...,B:...}, target A/B,
contrast_target_sign ±1 in the original candidate A-minus-B orientation, and
J_fraction={"42":number,"44":number}. Values must use the original frozen item's
family; target is the other/stated-opposite value. J fractions are from dev d at
each block, not test fits; one value per row/block. Owner seals must bind their
original metadata/label, candidate-orientation and direction provenance.

BASELINES.json is a CPU sealed join of existing outputs only: every item × both
native readers (`condition=unsteered`), and content items × reader=text
(`condition=text`, E81 generic arm or authorized completed E101_text equivalent). Fields item_id, reader, condition, text,
source_ref={seal_index,member,keys}. keys is the exact list of dict keys/list indices
leading to the source text in its sealed JSON file. The baseline seal contains
experiment E101, existing_outputs_only=true, source_seals=[{seal,sha256}]. These
references are reverified and exact text equality is required. Analysis regenerates no baseline. Completed E101_text seals may fill rows absent
from E81, using the authorized exact generic frame; their exact source pointers
are verified in the same way. Missing joins must be supplied before export.

Steered and random S_target use the same steered-flipped cohort paired by item;
the bootstrap samples original items jointly and recomputes the masked means.
UNPARSEABLE remains missing, not silent. Empty/undefined bootstrap draws give no
CI and rule NOT EVALUABLE where needed. Denominators and missing counts are kept.
All-item S for both cells and random's own B are also reported. B uses full frozen
continuation sums averaged over frozen pairs, strict target-side sign, zero is
not a flip. Each block uses its independently committed dev dose. Rules R-F1/F2/F3
are evaluated per reader; missing dose or B<.70 cannot support a bookkeeping null.
Text baseline reports explicit stated-value presence (including both-values) and
stated-only rate separately, so no ambiguity is hidden in that descriptive rate.
Norm ratios are retained/flagged, never excluded. B_VS_REPORT.png contains one point
per eligible row×reader and S intervals. No missing arm is drawn as zero.

## E102 and E103: sealed normalization interface

`python3 -m projects.g_agreement.analysis_late.e102 --spec SPEC.json`
`python3 -m projects.g_agreement.analysis_late.e103 --spec SPEC.json`

Each SPEC contains experiment, analysis (new output directory), inventory={seal,
sha256}, inventory_commit (full40hex), data={seal,sha256}. The inventory seal must
be committed and contain experiment, frozen_before_outputs=true, and files binding
INVENTORY.json. That file is a list of unique `id` metadata records defining the
full planned grid before outputs. The data seal requires experiment, COMPLETE
status, inventory_sha256, route_verified=true, redaction_audit_complete=true, and
source_seals=[{seal,sha256}]. RECORDS.json contains one record per inventory ID:
`{id, metadata: EXACT_INVENTORY_RECORD, measurements: {field: {seal_index, member,
keys}}}`. Each measured field is obtained directly from the source's sealed JSON
using the specified dict keys/list indices; fields cannot replace frozen metadata.
There are no free-floating supplied scores. All source/member hashes and the
entire inventory are checked before the once-only claim. The owner must commit
its concrete inventory before acquisition; none is invented here.

### E102 contract

Inventory seal: readers=[oracle, optionally nla]; feasibility perreader with
status=PASS, base_frozen=true, steps>=10, greedy_reproductions=3, adapter
olens_s3d_rl600 for Oracle. The reconstructor is rejected. Record failed/no-run NLA
under not_run_readers, not as a zero score. counts[reader][set][row] gives all84
trained/content rows and the frozen available counts (0–84) for each held-out row.
All registered rows are listed, including unavailable held-out rows with count0.

Inventory record fields: id, item_id, reader, split=test, set, row. For scored rows
also target=A/B from the original frozen family; E62 bracket_depth must have
rung=L0. Trained: nesting_depth, indent_level, page_range_digit. Held_out:
line_length, container_after_move, holder_after_handovers, branch_taken,
var_type_at_use, bracket_depth. Content: format_plan, language_plan, hedge_plan,
fact_recall, language_continuation, tense_implicit.

Measured fields for ordinary rows: original_text, retrained_text, original_code,
retrained_code. Codes are the established §172/§202 fields id, category, values,
evidence; exact evidence-substring validation and signed scoring happen here.
Placebo: exactly500 unique vectors; property=any_registered_bookkeeping_value.
Measured original/retrained_text and original/retrained_placebo_code, each
{statement: true/false/null, evidence: string}. Statement means any explicit value
of ANY of the three trained bookkeeping properties, not a randomly assigned
correct value. Null is UNPARSEABLE. True requires verbatim evidence; false/null
requires empty evidence. The same registered E56 route/privacy receipt must bind
these codes; normalizers must not infer statement=false from missing codes.
Workspace: exactly518 paired E80 items; family and frozen_scorer_sha256 in inventory;
measured original_pass/retrained_pass are actual boolean frozen-family verdicts.

Additional SPEC training={seal,sha256}: TRAINING_LOSS.json plus seal experiment
E102, test_used=false, judge_outputs_used=false, recipe exactly
{rank:16,learning_rate:0.0001,steps:300,batch:16,seed:20261029}. Trainingloss is retained
in the analysis. Set estimates pool items with row-qualified IDs. All comparisons
share paired item bootstrap draws. R-V1 includes placebo<=.10; R-V3 requires every
content row loss<=.10 AND pooled WorkspaceBench loss<=.05. No CI gate is added to
R-V3. Per-family WorkspaceBench rates and trained-row falsifier are retained.

### E103 contract

Inventory seal: selection_seed=20261028, mismatch_same_bank=true,
selection_plan_sha256 (W-text's frozen plan). Each inventory record has id, wave,
bank, reader (oracle/nla), readout_id, claim_id, source_item_id, mismatch_item_id,
mismatch_bank, mismatch_wave, claim (unaltered sealed E67 wording), original_verdict,
kind (CONTRADICTED/SUPPORTED), cohort (hallucinated/faithful), and
readout_has_contradicted. Supported queue is from faithful readouts only.
Measured fields: own_response and mismatched_response, exact `yes`/`no` output
(case/outer whitespace accepted) or explicit `UNPARSEABLE` sentinel bound to the
route receipt. No response is regenerated or guessed. Different source item,
same bank and wave is required; identities include wave to handle collisions.

Rates are claim weighted, with paired source-item cluster bootstrap: all claims
and both readers for one (wave,bank,source_item_id) move together. Match rates for
own/control and their difference are reported for each claim kind, pooled and by
reader, bank, wave, and the full reader×bank×wave combination. The pooled contradicted
comparison alone evaluates R-H2 (difference>=.15, lower>0) and its falsifier
(difference<=.03). Supported claims are descriptive; neither D4 nor E99 enters
the confirmatory pool. Missing outcomes retain their own denominator and are
reported; all-missing/undefined bootstrap results are NOT EVALUABLE.

## Current E101 authority: §212 descriptive test only

Production SPEC must set scope=descriptive_two_cell. The committed dose must have
only fact_recall:44 and language_plan:44 selected, both alpha4; the other12 cells
remain no-dose. R-F1/R-F2/R-F3 and falsifiers are forced NOT EVALUABLE. No defect
rerun is mixed in. Report the registered boundary-crossing null wording and the
nested-continuation/pagerange metric limitations.

Baselines may be omitted for this descriptive result; their absence is reported,
not converted to zero, and does not delay the two-cell judged analysis. When
provided they retain the full existing source-verified contract. Test cells still
require both steered/random, all84 items each, full continuation behaviour,
paired steered-flipped S, all-item S, random B, norms, Jfraction and the figure.

Only language_plan:44 may be omitted after its authorized retime fails. Supply
operational_not_run=["language_plan:44"] and operational_disposition={seal,sha256}
whose sealed DISPOSITION.json contains cell=language_plan:44,
status="NOT RUN (operational)", retime_failed=true. It is never plotted as zero.
