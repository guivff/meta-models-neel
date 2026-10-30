# E123 §233 — one reader, two layers

Reuses E94 `value_class` validation and `fraction` (Wilson95), and E94's 2,000
item-bootstrap draws/seed20261028. E94's original code, outputs and guard stay
unchanged. CPU only; no acquisition, model, judging, fitting or layer selection.
R-Q reviews. B owns this adapter; existing new-bank ownership remains C.

Inventory found before writing: E94 score94/run_once94/sources94, E109's original
analysis/cohort transport, E123 unhooked config and source/input seals. No prior
E123 adapter existed. Reuse the original E104/E109 flipped cohorts: fact_recall84
and language_plan50. Retain all three conditions (steered, random, unhooked) and
both block44/52 Oracle judgments, one pair per original source item/condition.
No reclassification of old E109/E104 results or new judgments.

## Exact metrics

The score is binary disagreement: unequal sets of stated values, including exactly
one layer stating a value. Two no-value categories agree (score0). The same
{A,B} set in either order agrees; {A,B} versus {A} differs. E94's collapsed
correct/wrong/no-mention classes are insufficient here, so their validation is
reused while retaining the original values. UNPARSEABLE is missing, never silent
or zero. Neither output text nor correctness classes invent a stated value.

Stale positives are steered items whose44 judgment exclusively states the old
value, matching E109/core.score's singleton-value criterion; ambiguous dual-value
reports are not exclusive old-value reports. The old value is the complement of
the original steered target, verified against original E104 private495bbb19.
Negatives are all common-parseable unhooked layer pairs from the same original
cohort. Non-stale steered cases are not added as negatives. Missing44 staleness
stays unknown. Every planned/missing layer pair and missing stale score is counted.

AUROC uses the binary score with half credit for ties (exact Mann-Whitney result).
The percentile95 CI resamples original source items jointly across all conditions
and layers; stale membership travels with the item. No separate layer resampling,
new cohort, complete-case restriction across conditions, class balancing or fitted
threshold. Report undefined one-class draws explicitly; no stale positive class
means NOT EVALUABLE. Each row is separate, without a pooled or best-row rule.

R-DIS1 requires AUROC>=0.80, lower95 strictly>0.70, and unhooked FPR<=0.15.
AUROC<=0.60 gets the registered "not usable" reading. Unhooked FPR has E94's
Wilson interval for description; no additional CI gate. Random-direction
pair-disagreement rate and AUROC against unhooked appear beside the main result
as descriptive controls, not substitutes for stale positives.

## Source bindings, before the once-only run

`python -m projects.g_agreement.e123_analysis.adapter --spec SPEC.json`

The CLI verifies every committed package/dependency byte before reading SPEC or
any outcome. SPEC: inventory_seal, inventory_sha256, e104_private, output_seal,
output_sha256, analysis(new local directory). Inventory seal must be experiment
E123/status SOURCE_ONLY_COHORT_BOUND/labels_cpu_only true,
source_e104_private_sha256495bbb19, binding INVENTORY.json. That file maps each row
to item_id/old_value records for the original84/50 cohort, checked independently
against the unchanged E104 private U/steered/flipped records. Keep it CPU-only.

The normalized output seal is experimentE123/status COMPLETE, inventory_sha256,
reader oracle, layers[44,52], labels_cpu_only/route_verified/
redaction_audit_complete true. It binds MEASUREMENTS.json and source_seals entries
(seal,sha256); every original source/member hash is verified. source_roles maps
E109_steered_random and E123_unhooked to the corresponding source indices, whose
experiments must match and status must be COMPLETE or COMPLETE_ONCE.

MEASUREMENTS maps each row to records:

```
item_id, conditions[steered|random|unhooked][44|52] = {
  item_id,row,condition,layer,reader:oracle,
  identity:{seal_index,member,keys},
  code:{seal_index,member,keys}, text:{seal_index,member,keys}
}
```

Pointers resolve original sealed JSON records; no copied/repaired verdicts or
precomputed disagreements. The original CPU identity join must bind item_id,
row,condition,layer,reader and judgment_id. Code.id must equal that judgment_id.
Evidence/category validation uses original core.score against original text.
If actual source envelopes differ, prepare a tested source-only mapping first;
do not invent identity fields or modify sealed source files to fit this contract.

Canonical fixed guard: wt-internals-b/cache/g_agreement/understand/e123/
ANALYSIS_ONCE.json. Metadata/cohort preflight precedes the claim; the claim precedes
all outcome joins/statistics. Repeated invocation fails. An interrupted/failed
claimed run retains its guard and needs an actual recovery ruling, never automatic
reset. The single run writes RESULTS/BINDING/ANALYSIS_SEAL. No real E123 outcomes
were opened during adapter development; synthetic tests precede first opening.


## POST HOC EXPLORATORY note1 (2e3ac01db), same original E123 once guard

No change to rules.py/R-DIS1/thresholds/bootstrap/cohorts. Prospective source
amendment is post-native-acquisition, before any E123 judgment opening. Runtime
writes POST_HOC_EXPLORATORY_NOTE1.json in the SAME single analysis run/seal.
Every added report is labelled POST HOC EXPLORATORY. No extra analysis/once guard,
no retrospective threshold, no E121 analysis invocation or guard reset.

SPEC additionally requires e121_analysis_seal/e121_analysis_sha256 pointing to
original LOCAL E121 analysis_once/ANALYSIS_SEAL.json, exact77a66f703234e4973f63057e2eb53743e06dc0a1ba1da3bffd347cf4934d6473 (ff2b4dd8e).
Metadata and all original seal members checked before E123 claim. Inside claim,
reuse E121 adapter.inputs only (source normalization, never analyze/main): original
sealed BINDING.json→all336 original source refs. Select exactly35 steered IDs where
Oracle44 AND NLA42 classes are wrong/exclusiveold relative to steered target.
Reject changed census/count/cohort; never select on E123/E109 layer52 outcomes.
IDs remain local; public outputs contain aggregates only. R-Q can reproduce from
those original custody pointers. New E123 judgments and old E109 block52 pointers
remain bound through the original E123 SPEC; this adds no rejudge/parse repair.

1. Exact35 share Oracle44/52-disagree, Wilson95/E94 fraction; planned35/missing
   explicit, absent judgments not false. Uses E109's original44/52 codes.
2. Same35 block52-alone singleton-new rate in steered, singleton-old in unhooked
   and random. Also show full original84/50 cohorts per row descriptively, with
   separate population labels and known/missing denominators.
3. Per-row sensitivity on registered stale-steered positives, unhooked FPR,
   precision TP/(TP+FP) on that explicit case/control mixture, plus all confusion
   counts/known stale/unknown stale/missing scores. This sample precision is not
   deployment prevalence. Coverage is both readouts state a value, observed over
   planned plus conditional-on-parseable; missing pairs/no-value/one-value counts
   separate. Missing scores abstain, never0; one-value/no-value known pairs retain
   the registered disagreement signal even when outside both-value coverage.

Original SOURCE_RECEIPT.json is historical. Current note1 source/test receipt is
results/g_agreement/understand/e123/analysis/POST_HOC_NOTE1_SOURCE_RECEIPT.json.
C's queue has E123 THIRD afterE127/E128 (fe2d4eb6); B does not dispatch its bank.
