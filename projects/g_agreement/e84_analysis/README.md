# E84 revived deviation1: once-only descriptive adapter

Authority: original §199 E84 and gates, revived source §198 E84 deviation1
(b9e2899b3), I2-E84-REVIVED-DEV1-20261029. Historical NOT RUN is retained.
CPU only; no dataset execution, inference, judging or old analysis replay.

Run only after source receipt and all bindings verify:
`python3 -m projects.g_agreement.e84_analysis.adapter --spec SPEC.json`
Fixed exclusive guard: wt-wmech/cache/g_agreement/understand/e84/deviation1/ANALYSIS_ONCE.json.
An existing guard forbids rerun, even if results are incomplete.

Direct user Option1 ruling: only file_being_edited (two files) has200 test items,
seed20261029. last_test_passed and failed_attempts remain explicit NOT BUILT rows. State values are
CPU parsed, unambiguous, absent from the last512 tokens before the next assistant
turn. Dropped ambiguity counts, transcript/window/parser lineage and disjoint
extra dev split are bound by the source owner. No private labels or joins on pods.

Clarification1 (3f2647773): probes fit on100 dev at Oracle44/NLA42, evaluated by test AUROC on200 items. Each reader independently requires>=.90; a failure drops only that reader, never the other reader or baseline. No dev-score threshold. Dev-fit BOW on final512 tokens has test AUROC<=.65; above .65 retains results but labels the row TEXT_READABLE/descriptive. All three state dispositions remain mandatory.

For each passing state, same200 items for Oracle44, NLA42, the single frozen E81 text_generic baseline, same complete rendered prefix.
The final512 tokens are only the state-absence screen; contexts are never cropped.
One greedy output/cell. E56 codes yield +1 correct-only, -1 wrong-only, 0 both/
neither; UNPARSEABLE stays missing. Direct E81 rate reuse:2000 item-bootstrap
draws, seed20261027, kept denominator, full planned denominator and missing
bounds reported. These are descriptive S estimates; E84 registers no decision
rule or falsifier. E81 R-T1 is not imported as an E84 rule.

## Exact binding contract

SPEC: inventory_seal, inventory_sha256, inventory_commit (full40hex pre-output
commit in executing checkout), output_seal, output_sha256, analysis output path.
Inventory seal hashes INVENTORY.json and contains experiment E84, authority
"revived deviation1", seed20261029, window_policy:"complete_rendered_prefix", absence_window_tokens512, cropped:false,
read_point start_of_next_assistant_turn, reader_blocks {oracle:44,nla:42},
ambiguity_counts for all3 states, parser_source_sha256, probe_recipe_sha256,
and nonempty source_seals [{seal,sha256}] covering original source/split/parser.
Dataset object: family "SWE-Zero OpenHands", exact repository and revision,
license "CC BY 4.0", anonymous_download true, terms_acceptance_required false,
original_release_check_sha256. Prefer original NVIDIA release; a mirror requires
the frozen original-release check. Gated access means NOT RUN by owner, no calls.

INVENTORY.json:200 file_being_edited records {id,state,item_id,split:"test",
state_absent_from_last512:true,unambiguous_cpu_parse:true,
source_transcript_sha256,window_sha256,parser_record_sha256,
targets:{oracle:A/B,nla:A/B,text_generic:A/B}}.
Targets stay private CPU-side and must be original per-system packet letters.

Output seal: experiment E84,status COMPLETE,inventory_sha256,source_seals;
route_verified,privacy_verified,labels_cpu_only,one_greedy_readout_per_cell,
same_window_verified,gate_before_readers_verified all true. Includes original
source/gate/readout/judge/privacy seals and their full custody receipts.
Hashes GATES.json and MEASUREMENTS.json. GATES maps the built state to an original
source pointer for {probe_fit_split:"dev",test_used_for_fit:false,
probe_metric:"test_AUROC",probe_blocks:{oracle:44,nla:42},dev_n:100,test_n:200,
probe_test:{oracle:number,nla:number},bow_window_tokens:512,bow_test:number}; extra provenance retained.
MEASUREMENTS includes exactly passing-state inventory IDs, systems exactly eligible readers plus text_generic, and
judgment_ids per system. Each systems entry has original source pointers for
text,code,target_letter,window_sha256. Pointer = {seal_index,member,keys} into
JSON in the corresponding verified source seal. Null terminal code or E56
UNPARSEABLE is missing, never fabricated silence. No guessed normalization.

No E84 source output has been opened by this worker. I2 owns source normalization,
W-internals-C the blind bank (cap3), W-mech2 sole once-analysis, R2 arrival review.
Missing bindings hold execution; private joins never appear in aggregate output.

## Direct user Option 1: same source, E110 first

Do not freeze E84 until E110 TwoHopFact bank is finished. Source owner confirms on
one more seeded shard of the SAME source, then freezes file_being_edited only.
Inventory state_dispositions must be file_being_edited:BUILT and the other two
NOT BUILT. confirmation_shards records initial and additional shard, each with
shard identity, sha256, seed20261029, trajectories, state_candidates. Require
additional_shard_confirmed and e110_finished_before_e84_freeze true, and original
e110_finished_seal:{seal,sha256} verified. Source identity stays pinned; no switch.

GATES for each unbuilt row points to {disposition:"NOT BUILT",
reason:"not built: the source agents were instructed not to execute tests",
shard_counts:[{shard,sha256,seed,trajectories,state_candidates},...]}. Counts must
be original owner scan aggregates, never inferred or zero-filled. These rows have
no readout inventory, no fabricated probe metrics/S, and no judgment request.
Their reason and full shard counts are retained in RESULTS. Built file row still
requires clarification1 reader-specific test-AUROC gates and BOW descriptive flag.
Adapter source preparation does not freeze the bank or authorize early acquisition.

## Frozen6c5dc40c source correction (before E84 output)

Complete original rendered prefixes are used, including historical file evidence; only the final512 tokens must lack the state. `window_sha256` binds that complete prefix shared by captures and generic baseline. Generic baseline appends the original frozen newline/instruction; no second wording arm is fabricated. Original source owner binds100dev/200test balanced issue-disjoint IDs. Statistics unchanged. §198 E84 clarification1 supersedes prior gate interpretation: no dev-score threshold or cross-block minimum; reader-specific test AUROC>=.90 and final512 BOW test AUROC>.65 means text-readable/descriptive, not dropping the row. Source normalization must bind exact per-reader probe and BOW recipe/metric evidence before execution. Full-prefix source/one generic baseline contract remains as frozen by source owner; no context cropping is performed by this analysis adapter.
