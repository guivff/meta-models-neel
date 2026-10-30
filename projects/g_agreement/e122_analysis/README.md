# E122 adapter — §232, corrected owner W-internals-B

Reuses E105's `statistic` and `common.stats.bootstrap_ci` unchanged: 2,000 draws,
seed 20261027, paired percentile 95% CI. Per Guiv's pre-analysis clarification, S matches the addressed T donor. It uses
the frozen runner's seed-20261030 cyclic permutation, sequential genres 0 then 1. Original E105
code, outputs and guards stay immutable. R-2 reviews E122.

The frozen W-text contrast seal is
`23c9b0f8c75c869d36868ed3b44480ac53ef2346cc0438f5ee2eb84d5623f414`
(commit `713cbdeda55c7b9f7c6644dfcbda550b55df6ca5`): hedged_vs_direct,
ai_vs_direct, stop_vs_continue, formal_vs_informal, in that order. The manifest
is copied byte-for-byte. Its positive-minus-negative full conditional token
log-probability sums are used, including punctuation and the explicit one-token
native `<|im_end|>` candidate. No length normalization, appended token, sign
switch, first-token approximation, extra contrast or text rewrite.

## Estimands

For each quartet and contrast, average the addressed-minus-unaddressed shift over
its two genres. Select the largest **signed** mean over the 50 dev quartets; exact
ties take the first frozen manifest entry. The selector never receives test
records. Native test and transplant scoring use only that frozen selected ID.

R-BEV1 uses the 100 test-quartet shifts. It is MET only when their mean and paired
bootstrap lower bound are strictly positive. Otherwise RESULTS explicitly says
R-BEV2 / transplant NOT RUN, with the registered negative reading.

For each test quartet/genre, the unaddressed carrier receives its addressed twin
at block 44 (T), or an addressed donor from another test quartet in the same genre
(S). The frozen runner uses a cyclic shift of a seeded permutation of sorted test
quartets, one RNG seeded 20261030 and drawn for genre 0 then genre 1. Guiv
clarified that same-condition means same-value as T; existing runner inputs stay unchanged.
The signed contrast orientation stays fixed across native/T/S. Average c(T)-c(S)
within quartet over genres, then bootstrap the 100 quartets. R-BEV2 requires both
mean Delta and its lower bound >0. Fraction recovered is the ratio of pooled
mean Delta to pooled mean native addressed shift, with numerator/denominator
reported and no clipping. This registered fraction is a point estimate; no ratio
CI is added. Per-genre shifts/Delta are also reported.

The original E85 private map has 600 cells: 150 matched_set quartets,
50 dev/100 test, genre/addressed factors 0/1. Each addressed twin shares its
genre-specific body. Original genre templates differ; the adapter preserves
these original E85 items and grouping verbatim rather than synthesizing bodies.
No quartet or genre-cell drops, imputation, missing-as-zero or changed split.

## Before any real opening

Commit this package, its synthetic tests and dependency hashes first. Every CLI
checks committed bytes before reading its SPEC/PLAN or any output. Under §232
addition 2, capture may already be sealed and UNOPENED; the adapter commit must
precede the first opening. The cap note allows (a)/(b) in one launch. All four
contrasts may be acquired together; the native-test loader computes only the
dev-selected contrast, and the transplant loader is unreachable until R-BEV1
passes. Acquisition does not depend on an analysis seal that did not yet exist.

This is CPU analysis only. I-2 binds the source pointers and coordinates the
single invocation with B. No judging, model loads, GPU allocation or API keys.

## Source-only CPU input freeze

```sh
python -m projects.g_agreement.e122_analysis.adapter freeze --spec FREEZE_SPEC.json
```

FREEZE_SPEC has `contrast_seal`, `contrast_sha256` (the exact seal above), full
`contrast_commit`, `e85_bank_seal`, `e85_private`. The original bank seal is
`1c966b10b67de74dafeadf51daf9f2a7496bf6578ff66566dde76d060c436478`;
the original LABELS.PRIVATE hash is
`5ed311882f9b06f208776d1636567267570ed33bbf83b39d5da9732559975a44`.
The existing source is at wt-wtext/results/g_agreement/understand/e85, with its
cache/bank_2026-10-28_v1/LABELS.PRIVATE.json. All member hashes verify.

The freeze copies original `public_id` to `id`, original `id` to `source_id`,
`matched_set` to `quartet_id`, and original genre/addressed/split. It writes
INVENTORY.json, S_PAIRINGS.json, original CONTRASTS.json and PROVENANCE.json to
the fixed ignored B cache `cache/g_agreement/understand/e122/frozen_inputs` and
seals them. This is a **private CPU inventory**, never a pod archive. A source-only
custody wrapper may be written after capture: it copies original metadata and
the frozen runner seed recipe confirmed by Guiv before analysis, not outcomes; its timestamp is not relabelled
as pre-GPU. Actual T/S donor identities are independently checked in every raw
record. Nothing derives or chooses donors from scores.

## Original raw scores and pointer contract

Original COMPLETE E122 run seals bind `experiment=E122`, `status=COMPLETE`,
`contrast_source_sha256` (the W-text seal above), `source_e85_bank_sha256`
(original E85 bank above), and their original raw members. An original raw
record is:

```json
{"id":"original public cell ID", "condition":"0", "block":44,
 "contrast_ids":["hedged_vs_direct","ai_vs_direct","stop_vs_continue","formal_vs_informal"],
 "candidate_ids_sha256":"SHA256 of the ordered token-pair list",
 "pair_logprobs":[[-3,-2],[-8,-2],[-4,-2],[-2,-2]]}
```

`pair_logprobs` are original full frozen continuation sums, E105's representation,
one [positive_sum,negative_sum] per contrast. `candidate_ids_sha256` uses compact
sorted-key JSON of `[[positive_token_ids,negative_token_ids], ...]`, SHA256.
A native test or T/S record may instead contain only the dev-selected contrast.
Dev requires all four. T/S records additionally have `condition=T|S`, `base_id`
equal to the original unaddressed public ID, and the exact `donor_id`. Their
`id` is SHA256(`E122:<base_id>:<condition>`). The block stays 44. This metadata
belongs in the frozen runner/source contract; do not edit original outputs to
invent identity fields or call scalar precomputed contrasts raw pair scores.

I-2's source-only index has RAW_INDEX.json:

```json
{"native":{"cell_id":{"seal_index":0,"member":"jobs/raw.json","keys":[0]}},
 "transplant":{"carrier_id":{"T":{"seal_index":0,"member":"jobs/raw.json","keys":[1]},
                              "S":{"seal_index":0,"member":"jobs/raw.json","keys":[2]}}}}
```

Expand `native` to all 600 original IDs and `transplant` to all 200 test
unaddressed IDs. Each pointer leads to the whole original raw record, not a
computed contrast. The index seal has `experiment=E122`,
`status=SOURCE_POINTERS_ONLY`, `contrast_source_sha256`, `source_e85_bank_sha256`,
`source_seals=[{seal,sha256}]` and files binding RAW_INDEX.json. All underlying
acquisitions must be COMPLETE. Partial failed attempts never enter analysis.

PLAN.json has `frozen_seal`, `frozen_sha256`, `raw_index_seal`,
`raw_index_sha256`. A source-only binder copies pointers into exact dev/native
test/transplant MEASUREMENTS wrappers and binds selection/gate provenance as
each analysis phase completes. It never parses numerical raw job members.

## Single watcher and guards

```sh
python -m projects.g_agreement.e122_analysis.watch --plan PLAN.json
```

The fixed experiment-global B cache owns dev_selection_ONCE.json,
native_test_ONCE.json and transplant_ONCE.json and corresponding output folders.
The watcher verifies already sealed phases on re-entry; it never recomputes
their statistics. A consumed guard without its complete seal is fatal, requiring
an explicit recovery ruling. It does not reset E105 or any other old guard.
Failure of R-BEV1 ends normally at the native seal with b NOT RUN (analysis);
b's contrasts are not extracted or used for statistics, and its guard is not
consumed. Original raw members may contain several acquisition phases: the
member is hash-verified/decoded, then only the requested phase's pointers and
selected contrast are evaluated. This does not imply that the physical
acquisition was skipped under the one-launch cap note.

Each executed phase emits a source-bound ANALYSIS_SEAL, selection or RESULTS,
and BINDING. Direct single-phase CLI actions `select-dev`, `native-test`,
`transplant` also exist for the same canonical guards. The watcher and manual
commands are alternative entrypoints to those same guards, not independent
analysis paths. Wait for exact source bindings; do not infer a compatibility map
or modify a scientific rule to fit a producer. R-2 reviews on arrival.

### I-2 native producer already committed at 56b31d5

`producer232.py` also accepts the exact original `e122_logits232.py` envelope.
A `source_seals` entry sets `format="i2_e122_logits232_v1"` and supplies
`producer_source_seal` and `producer_input_seal` in addition to `seal`/`sha256`.
The source/operator/E101 full-continuation scorer/input hashes are pinned in
code. Their seals, all source/input members, 600 public identities, frozen
candidate lists and original output CONTRAST_ORDER are verified. Original native
records retain `source_block`, `split` and `pair_logprobs`; their native-only
condition/order are certified by that exact producer. Raw scores are never
rewritten to manufacture absent fields. Unknown envelopes fail closed. This
binding certifies native (a) only; it cannot certify T/S or a failed pilot.


### Track Q combined worker122 binding

producer_q232.py pins original input3308228f, CPUjoin80e9422c and COMPLETE
outputd5d7f370. It verifies all1000 original native/T/S identities, original
quadruplet/split/candidate order and clarified addressed donors. The unchanged
E105 batch recipe constructs member/record pointers from public input metadata;
no numerical job JSON is read to build the index. Entry format trackq_e122_232,
producer_input_seal and producer_join_seal. Original raw records retain their
opaque ID, inventory_id, base_id, condition, block, vector_index and fullpairs;
identity/token/donor provenance is checked against original sealed input/join.
No raw rewrite or scalar contrast normalization. CLI accepts --spec containing
frozen_seal/frozen_sha256, raw_output_seal, producer_input_seal,
producer_join_seal and creates canonical PLAN.json. Source commit must precede
this CLI and every numerical opening. Existing phase guards remain the only
execution path. Direct Guiv: run(a)once after R2holdlift, (b)only ifgateMET.

### EXPLORATORY, POST HOC — note1 (01f45c0ba), after failed native gate

Registered R-BEV1 remains NOT MET and R-BEV2 remains NOT RUN. Direct Guiv note1
now authorizes one separate EXPLORATORY, POST HOC score of the existing sealed
T/S outputs on formal_vs_informal. No new selection, generation, capture, judging,
input change or confirmatory rule change. New CLI after its source/test commit:

`python -m projects.g_agreement.e122_analysis.exploratory_note1 --plan LOCAL_PLAN.json`

The exploratory statistic remains the original paired item/quartet bootstrap:
average the two genre T-S contrasts within each original test quartet, then use
E105's2000draws/seed20261027 on100quartets. Delta<0 and upper95<0 is the fixed
exploratory reading in the native effect's negative direction. CI including zero
means no evidence. Fraction is Delta divided by the exact sealed native shift
(-0.13613942623138428), rather than a rounded denominator; report without clipping.
No ratio CI or new threshold is introduced. Per-genre descriptive results remain.

All new artifacts are labelled exploratory=true, post_hoc=true. Separate
exploratory_note1_ONCE.json / exploratory_note1 folder; original selection/native
seals and confirmatory transplant guard remain untouched. The new source/test
commit and exclusive exploratory guard precede the first T/S numerical read.
It binds the same source-only PLAN, frozen contrast, original400 T/S outputs,
original addressed donors and source hashes. No original source overwrite or
reset. R-2 reviews this exploratory record separately from confirmatory results.
