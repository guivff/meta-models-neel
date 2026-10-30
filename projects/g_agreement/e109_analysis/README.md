# E109 §222 once-only CPU adapter

Source/test commit BEFORE any E109 output. Command after complete bindings:
python -m projects.g_agreement.e109_analysis.adapter --spec SPEC.json
Use the CPU environment wt-wcensus/.venv/bin/python (sklearn1.9.1); system Python
has an incompatible sklearn binary. No GPU, model calls, or new judging here.

Five probes per row at44/48/52/56/60, fit only on the84 UNHOOKED dev activations.
Fixed logistic regression matches common.probes defaults: C1, lbfgs, max_iter2000,
seed0, intercept, no scaling or hyperparameter selection. A=1/B=0. Nonconvergence
fails closed. Apply to all84 test activations per condition; report flips (reads
target value) on the ORIGINAL E104 steered-flipped cohort,84 fact/50 language,
with common.stats Wilson95% CIs. Retain unhooked and random probe controls.
No new behaviour-based cohort selection, test fitting or layer selection.

Oracle at44/52/60 only: signed S_target steered/random on SAME sealed cohort,
paired item bootstrap2000 seed20261028 inherited E104, separate missing masks,
no complete-case selection or missing-as-zero. This resamples cohort items.
R-AR1: existential row and SAME later Oracle/probe layer (52/60), probe>=.70 and
Oracle difference>=.30/lower>0. Captures48/56 cannot meet AR1 without an Oracle.
R-AR2: probe44>=.70 and E104 ORIGINAL sealed difference44<.30 (not E109 rerun).
R-AR3: all FIVE captured layers probe<.50; per-row results and any-row summary.
Falsifier: probe44>=.70 and NEW E109 Oracle44 difference>=.30, no added CI gate.
All descriptive rules retain per-row results; R-AR1 is confirmatory. Missing Oracle
comparisons stay unknown. No change to sealed E104 statistics or guard.

## Source binding required from W-mechanism-C / Track Q / W-internals-B

SPEC: inventory_seal, inventory_sha256, inventory_commit(full40hex), output_seal,
output_sha256, e104_analysis_seal, e104_private, analysis(new directory).
Original E104 analysis SHA01d8d5a17b7bbea1d2df27982ef10c897156093430967d8da442e0a5137cbe1e
and CPU private SHA495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4
are pinned. Original private flipped flags define cohort; labels never leave CPU.

Inventory seal must be committed in executing checkout BEFORE output; experiment
E109, d40_sha256 exact original sealed d40. INVENTORY.json keyed fact_recall and
language_plan. Per row: alpha8/2, dev_ids84,test_ids84,dev_labels84 binary A=1/B=0,
targets84 binary, target_letters84 A/B in identical test order. IDs/dev labels
must be bound to ORIGINAL E104 bank/splits in owner normalization receipt, no new
items. test IDs and steered target letters are verified against sealed E104 join.
The dev bank label/order mapping and d40 f95dcff93 lineage must be independently
source-hash verified before invocation; never infer an orientation from results.

Output seal experimentE109/statusCOMPLETE/inventory_sha256, route_verified,
privacy_verified,labels_cpu_only alltrue, d40_sha256 matching inventory,
hook={block:40,positions:eight_before_read,read_token_untouched:true},
source_seals=[{seal,sha256}] binding all actual capture/reader/judge/privacy files.
MEASUREMENTS.json row→layer(string)→{dev,test,oracle(at44/52/60only)}.
dev and test each contain unhooked/steered/random refs to84×dimension arrays.
All capture arrays finite and retained; hooked dev is NEVER fitted. ref is
{seal_index,member,keys}; .npy loads allow_pickle=False, JSON also supported.
keys traverse the original source, no reconstructed activation values.
Oracle is condition→84 records in exact original test order, each
{item_id,text:ref,code:ref}. Code is original E56 {id,category,values,evidence};
original target letters and verbatim evidence checked. No original codes rewritten.
Require complete1008 Oracle readouts, both rows/all3layers/2conditions/84items.

Owner must seal exact array ID order and dev labels, original d40/dose/hook/route,
source/privacy hashes and GPU type per shard before handing SPEC to watcher.
Missing inputs mean WAIT, no guessed normalization or partial cells. The fixed
experiment-global guard is wt-wmech/cache/g_agreement/understand/e109/ANALYSIS_ONCE.json.
Aggregate results and source binding are sealed; private joins/labels stay local.

## Pre-judgment path-redaction companion (79f63fe0)

Original analysis.py scientific implementation remains byte-identical to a0978104f.
C reports one path-redacted judge copy. Prospective companion is committed AFTER
acquisition seal but BEFORE judgments are opened/analysis invocation; no claim that
this companion predates acquisition. Full primary analysis remains unchanged.
Output normalization seal additionally requires redacted_readout_count and
redaction_audit original sealed pointer. Resolved audit contains all_affected_mapped
and original_text_preserved true, affected_readouts list {row,layer,condition,item_id}.
Bind exact original opaque-ID redaction audit and CPU source-map hashes in source
seals. No affected mapping inferred from responses. Original text is still used
for evidence validation. Empty list requires zero count and explicit audit.
REDACTION_SENSITIVITY.json counts all affected readouts and those in registered
cohort; masks affected readout score as missing with original paired grid intact
(as existing W-mech2 privacy companion). Reuses original statistic/classify_rules
and primary probe results without refitting or any prior analysis replay. No
changed primary rule/cohort or evidence relaxation. Private IDs remain CPU-only.

## R-Q pre-seal correction (§222 clarification1, 995a2e2cd)

The new44 falsifier additionally requires its paired Oracle difference CI lower bound strictly greater than zero. CI[-.10,.50] and lower bound0 are NOT MET; missing CI is NOT EVALUABLE. Primary and redaction companion share classify_rules, so both use this correction. Acquisition, cohort, estimands, bootstrap, and other predicates unchanged. Correction is post-acquisition/pre-analysis, with no real E109 judgments opened. Original source receipt remains archived as historical provenance, not the current execution pin.
