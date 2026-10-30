# E110 (§223 item4) pre-output pooled wrong-belief adapter

CPU only. Commit source and synthetic tests before any E110 output. Sole command
on complete verified bindings: python3 -m projects.g_agreement.e110_analysis.adapter
--spec SPEC.json. Fixed global guard wt-wmech/cache/g_agreement/understand/e110/
ANALYSIS_ONCE.json. No acquisition, filtering, model/judge calls or old analysis replay.

Direct imports preserve original implementations: E82 analyze.row_summary for
conditional P(belief)-P(truth); E107 rules.compare/verdict for paired conditional
reader-minus-outside P(belief). E107 adapter.evaluate preserves exact per-system
letter maps and original text evidence. §223 pools all belief-wrong source items:
R-B2-prime applies the E82 row criterion >=.20/lower>0 to that pool, NOT E82's old
at-least-two-rows aggregation. R-OL1-prime >=.20/lower>0 is unchanged. Oracle is
confirmatory, NLA descriptive. Matched belief-right reports stay separate.
Original5000 draws/seed0: E82 resamples fixed named cohort; E107 resamples paired
source items with each system's own naming denominator. Both-valued evidence
contributes zero belief-minus-truth; missing target pairs remain unknown, no fake
silence or complete-case cross-system denominator. R-OL1's original falsifier
is retained as descriptive only, not an additional E110 confirmatory rule.

Fewer than60 belief-wrong survivors: NOT RUN, no output-bank reading. Target150
is reported, not an extra gate. The registered TwoHopFact sample is up to3,000 candidates, seed20261029, stratified over52 composition types. Retain every selected survivor.

## I-2 / W-text / W-internals-C source contract

SPEC keys inventory_seal,inventory_sha256,inventory_commit(full40hex),output_seal,
output_sha256,analysis. For NOT RUN (<60), output fields may be omitted. Inventory
seal must be committed in executing checkout before reader/outside/judge outputs;
experimentE110,seed20261029,candidate_count (1..3000),composition_types52,
item_source TwoHopFact,dataset_repository soheeyang/TwoHopFact,
dataset_revision59a84cd883f71641a03fb6fa50da92a9603e7845,license "CC BY 4.0",
anonymous_download true; survivor_counts belief_wrong/right;
filter_counts stable_belief_wrong/native_belief_wrong; selection_mode.
Selection is fixed before output: >=60 stable wrong selects all stable wrong
("stable belief"); otherwise >=60 native wrong selects all native wrong
("no paraphrase gate"); otherwise "NOT RUN". Target150 is not another gate.
filter_source_seal and original_item_source_seal each {seal,sha256} verify the
sample, 52x2 frozen relation templates, native plus two one-hop completions,
native two-hop answers and matched-right selection. Read data, never execute it.
Owner normalization must bind these flags to original filtering, never readouts.

INVENTORY.json per paired source item: id,row,item_id,cohort belief_wrong/right,
bank E82 (rubric interface),split test,systems ['oracle','nla','outside'],
read_token end_of_native_two_hop_prompt, one_hop_correct/two_hop_correct booleans.
Wrong requires both false; stable selection also stable_one_hop_paraphrases3.
Right requires both true and matched_composition_type true.
target_letters_by_system={system:{belief:A/B,truth:A/B}}. Original candidate
semantics stay CPU-side; belief and truth may coincide for belief-right items.
Bank field E82 selects the inherited rubric logic; experiment remains E110.

Output seal experimentE110/statusCOMPLETE/inventory_sha256,route_verified,
privacy_verified,labels_cpu_only true,reader_blocks={oracle:44,nla:42},
one_greedy_readout_per_item true,source_seals [{seal,sha256}] binding original
capture/reader/outside/judge/privacy sources and per-shard GPU types.
Outside generation matches E107: google/gemini-3.1-flash-lite,
provider google-vertex/global,T0,max256,ZDR true,data_collection deny,fallbacks false.

MEASUREMENTS.json exactly matches every inventory id and all3 systems:
{id,systems:{system:{belief:{text:ref,code:ref,target_letter:ref},
truth:{text:ref,code:ref,target_letter:ref}}}}. ref={seal_index,member,keys} reads
original sealed JSON. Codes use E82/E56 id/category/values/evidence; exact original
per-system target-letter pointers are mandatory. A single two-candidate blind code
can be referenced by both target entries; no recoding or extra paid call required.
Independent original target judgments are supported without changing their values.
No original E82/E107 outputs are included or rescored. Complete source/inventory/
filter/privacy receipt verification precedes sole claim; no guessed normalization.

Review R-2, integrator I-2, bank W-internals-C. Source receipt under
results/g_agreement/understand/e110/analysis/SOURCE_RECEIPT.json. Owner HANDOFFs
carry binding requests and result notifications. Labels/private joins remain local.

§223 deviation1/clarification1 supersedes the generated-bank contract. If a generated
bank was frozen first, it must be reported separately under its own sealed contract;
never pool it with TwoHopFact or silently discard it. This invocation is TwoHopFact
only. Dataset-access failure returns to owner for the registered generated fallback.

## §223 amendment1 (aa8438c71): completed-quarter restart

The scientific functions and bootstrap remain unchanged. Production now requires `shard_source_seal` (seal/sha256) in the inventory seal. That seal must include `SHARD_RECEIPT.json` and custody evidence tying the original candidate roster, quarter crosswalk, filter seals, unchanged prompt bytes, and excluded old-attempt census to the registered sources. All private crosswalks stay CPU-side. No partial filter outputs may enter this binding.

Receipt schema: `authority: aa8438c71`, `restart_index: 1`, `original_candidate_ids` (the unchanged 3000 unique IDs), timezone-aware `selection_at`, `excluded_attempt` with `attempt_id`, `status: NO_FIT`, `output_count: 192`, `excluded: true`, and all192 original `job_ids`; plus four `shards`. Each shard has `quarter`0..3, exact `candidate_ids` (sort IDs, Python Random20261029 shuffle, consecutive750), `status` COMPLETE or NOT COMPLETE, and `included` exactly matching COMPLETE. Included shards also supply timezone-aware `completed_at`, new `attempt_id`, unique quarter `job_ids`, `prompt_bytes_unchanged: true`, and `all_candidate_jobs_complete: true`, supported by the sealed original filter/crosswalk evidence. Incomplete shards contribute no candidates or jobs.

All four complete shards may be selected immediately. A reduced set can be selected only at/after2026-10-29T15:00:00Z using the complete-at-cutoff snapshot. `candidate_count` is achieved candidates (750 times completed quarters, including zero); each survivor metadata record needs `candidate_id` in those quarters. Existing stable/native counts and minimum60/fallback rules apply to that achieved sample, with all survivors retained. The result reports original/achieved counts, complete quarters and excluded192 outputs. This is a prospective custody amendment, not permission to inspect partial outputs, run filtering/selection, replay analysis, or infer a scientific fewer-than60 result from operational NO_FIT.

## §223 deviation2 — generated source and third descriptive E82 bank

This section supersedes the TwoHopFact-only execution restriction above for the
new deviation2 bank. Historical TwoHopFact is terminal NOT RUN (0 stable/6 native
wrong out of3000); never rerun its selector or mix its outputs into the new bank.
The same still-unused global E110 guard covers the entire new analysis, including
all three separately reported banks: new belief-wrong, new matched belief-right,
and the original100 E82 wrong_bridge items. The reference bank is descriptive
only. It cannot contribute to the60-item floor, target150, R-B2-prime or R-OL1-prime.
No original E82 analysis/guard is replayed.

New inventory adds deviation:2, item_source:E82_long_tail_bridge,
generation_method:E82_wrong_bridge, long_tail_source_bound:true, candidate_count3000,
composition_types52, seed20261029. Original source/filter seals must cover all3000
frozen candidates and their repo triples or frozen authored relation templates,
bridge-frequency evidence (<10 TwoHopFact records OR frozen authored low-frequency
list), native/2paraphrase completions, wrong native two-hop answer, and exact
all-survivor selection. Existing stable>=60/native>=60/otherwiseNOTRUN and
composition-matched right rules remain. Prior amendment1's old TwoHopFact
restart/shard receipt does not describe this new acquisition; no old192 outputs
or old filtering attempts enter. No source substitution or relaxed filter.

For an eligible deviation2 run SPEC additionally requires e82_reference, with
inventory_seal/inventory_sha256/inventory_commit and output_seal/output_sha256.
This is a separate pre-output committed inventory, experiment:E110,
bank_role:E82_wrong_bridge_descriptive, INVENTORY.json with exactly100 original
E82 wrong_bridge/test/belief_wrong items (original item_id, all three systems,
per-system original belief/truth target letters). original_e82_source is
{seal,sha256,wrong_bridge_item_ids:{member,keys}} pointing to the original sealed
100-ID census. Exact membership is verified; no invented replacement IDs,
subsampling, renaming original item IDs or re-filtering this reference bank.
Bank-scoped IDs can overlap with the generated bank: they are never pooled.

Reference output uses the identical COMPLETE E110 output schema and source
pointers described above, bound to its own inventory. Bind original E82 item
lineage and each actual readout/code/letter, plus native/outside/route/privacy
receipts. Do not fabricate absent outside codes or silently substitute historical
aggregate scores. No new acquisition/judging is dispatched by this adapter.
The outputs add descriptive_banks.E82_wrong_bridge with Oracle/NLA
R_B2_statistic and reader_vs_outside computed by the exact same pinned E82
row_summary and E107 compare functions,5000/seed0 and own naming denominators.
The inherited row criterion field is retained for numerical schema compatibility;
it is not an E110 confirmatory decision for the reference bank. Missing and
both-valued evidence follow unchanged functions. If the new bank fails the60
floor, analysis stops NOT RUN without reading reference outputs.
