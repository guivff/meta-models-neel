# E106 once-only CPU adapter — §215 and §221 item3 clarification1

Pre-output source/test commitment is required before ANY E106 gate/test output.
Run exactly once after all final dispositions and source bindings are sealed:
`python3 -m projects.g_agreement.e106_analysis.adapter --spec SPEC.json`.
The fixed global guard is wt-wmech/cache/g_agreement/understand/e106/ANALYSIS_ONCE.json.
No generation, training, judging, baseline rescoring or replay is performed here.

R-FX0 reports paired prompt-minus-original S per row, both readers. Arm P has
three train plus five held-out rows. Arm T adds the four content rows and200
placebos, original/retrained paired by item. Original signed S semantics and
paired2000-draw item bootstrap seed20261027 remain unchanged. R-FX1 needs train
delta>=.30/lower>0 in2/3, content delta>=-.10 in3/4, retrained placebo statement
rate<=.20. R-FX2 is descriptive held-out delta>=.20 in2/5. Falsifier: all3 train
deltas<=.10 with completed recipe and decreased loss, OR placebo rate>=.30.

§221.3: placebo is the share of200 readouts stating ANY value of the THREE trained
rows. It is never signed target S. The bank must blind-judge the entire trained
value union, not a randomly assigned binary target. Both original and retrained
rates are reported. Exact threshold denominator200 is retained. Missing judgments
are explicit, with bounds and separately labeled parseable-only descriptive CIs;
the primary point is unknown if any judgment is missing. No missing-as-silent or
parseable-denominator substitution. Both-valued statements still count once.

## Frozen input/source contract (I-4 and W-internals-B)

SPEC: inventory_seal, inventory_sha256, inventory_commit(full40hex), output_seal,
output_sha256, analysis(new directory). Inventory must be in the executing repo
and committed before output; private labels stay CPU-local. Seal experiment=E106,
placebo_seed=20261031; files bind INVENTORY.json. Each record represents a paired
item: id,item_id,reader(oracle/nla),arm(P/T),row,split(test/placebo), and for non-
placebo target_by_cell={original:A/B,intervention:A/B} retaining original code maps.
All planned P/T rows remain in inventory even when T is not run. availability is
reader→arm→row→{count,reason};84 each where available,200 placebos exactly, any
original shortfall has a pre-output reason. Retain all1344 P baseline records;
legacy_nla_holder_original_max_tokens=128,new_max_tokens=512. Original NLA holder
cap mismatch is reported explicitly, never dropped or regenerated. Row aliases
must be resolved in the frozen inventory, not guessed from output.

Output seal: experiment=E106,status=COMPLETE,inventory_sha256,route_verified=true,
privacy_verified=true,labels_cpu_only=true,source_seals=[{seal,sha256}], files
binding MEASUREMENTS.json. Freeze/verify actual E56 route/privacy/source receipts
in source_seals; no freehand unsealed measured scalars. dispositions is reader→
P/T→{status}; COMPLETE or T-only NOT RUN (feasibility) / NOT RUN (Oracle E102 gate
unresolved), with reason and source_ref for each absent arm. No partial scores
from failed arms. Both readers/arms need terminal disposition before sole analysis.

MEASUREMENTS has one record for every and only complete paired inventory ID:
{id,cells:{original:{text:ref,code:ref},intervention:{text:ref,code:ref}}}.
Every ref={seal_index,member,keys} traverses the original verified source JSON.
Nonplacebo code is original E56 {id,category,values,evidence}, validated by frozen
core.score. Placebo code is the blind bank union judgment
{states_any_trained_value:true/false/null,evidence:string}; true requires verbatim
supporting evidence, false/null empty evidence. null denotes terminal missing.
This is an interface for the channel owner, not authorization to rejudge or invent
codes; exact original schema adaptation and source receipts must be supplied.

Output diagnostics maps each COMPLETE T reader to an exact sealed JSON reference.
Required object: gate={status:PASS,steps:10,parity_byte_equal:3,
frozen_before_sha256,frozen_after_sha256,adapter_tensors_changed,
parity_before_optimizer:true,fresh_production_adapter:true,
parity:[{expected_sha256,actual_sha256}×3],gate_losses:[10 finite values]},
recipe={rank:16,lr:0.0001,steps:300,batch_size:16,seed:20261029},
dev_only:true,equal_replay:true,test_optimizer_items:0,losses:[300 finite values].
Oracle also requires oracle_e102_resolution_sha256. The owner must bind original
parity bytes/timestamps, dev-only inventories, executed recipe/checkpoint and loss
sources in source_seals and a verified normalizer receipt. No invented gate or
recipe success. Loss-decreased comparison is last versus first recorded training
loss; trajectory retained, no post-output smoothing/selection. T not-run leaves P
descriptive results intact. NOT RUN is not a falsifier or a negative result.

Synthetic tests cover statement-vs-signed semantics, exact200 denominator,
original rate, .20/.30 thresholds, missingness, both readers/full rule groups,
P-only feasibility, source tampering, fixed guard behavior, recipe/gate/leakage,
paired missing masks and original rule boundaries. Source receipt is in
results/g_agreement/understand/e106/analysis/SOURCE_RECEIPT.json.
