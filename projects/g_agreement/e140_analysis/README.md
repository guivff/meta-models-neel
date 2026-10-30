# E140 §252 — paired paraphrase tracking, prospective CPU report

Uses E127 `common.rate` unchanged (common.stats Wilson95, z=1.96).
Direct user clarification: ONLY X/Y count in paired tracking/prior denominators;
other is reported separately, never treated as the same unidentified value.
For each block44/52/60, tracking is A=X AND B=Y, prior is X/X OR Y/Y,
conditional on both asserted sets being exactly {X} or {Y}. Reverse Y/X is neither. Value-stating coverage is
X/Y/other/multiple readouts / observed terminal readouts; X/Y-only coverage is separate,
with planned/known/missing counts;
other/none each have separate rates/CIs. Both-X/Y pair coverage is also reported.
Terminal UNPARSEABLE/null stays missing, not none; no cross-block complete cases.
Both readings are reported independently: tracking>=.60 AND Wilson lower>.45;
prior>=.50. Only block60 is the registered descriptive reading;44/52 adjacent.
No additional completeness, significance, or equivalence gates. Unknown eligible
rates stay null. All findings conditional on observed coverage, no fixed-prior
causal conclusion beyond the registered descriptive reading. Ceiling1.0 is by
construction, no same-model generation or claimed independent accuracy.

Selection is frozen before reads:600 pairs/at least8 categories/seed20261030,
first up to84 in generation order whose first-nonempty-line lowercase,
punctuation-stripped greedy32-token answers are nonempty and differ. <40 pairs
is screen-only; do not invoke analysis. No scoring-driven selection or parser
repair. All selected pairs and all six readouts are required, terminal missing
preserved. Read sites44/52/60 final prompt token; pair logits descriptive source
custody only, not a cohort selector or substitute for generated answers.

C owns judging<=504, bank<=USD1, afterE137 beforeE95; I2 integrates original
source lineage and R5 reviews. No paid/model/GPU operations here. This source
must be committed/tested before any E140 output opening. No E127 guard replay.

## Private executable binding

Entry `python -m projects.g_agreement.e140_analysis.run --spec SPEC.json`.
Fixed guard wt-wmech/cache/g_agreement/understand/e140/ANALYSIS_ONCE.json;
analysis_once alongside. All source validation and summary checks before claim;
a consumed guard never replays. Publish RESULTS/ANALYSIS_SEAL only, private
BINDING stays local. Source receipt pins all imported scientific dependencies.

SPEC experimentE140/statusCOMPLETE, other_policy=xy_only,
other_policy_authority=direct_user_xy_only, inventory_seal/inventory_sha256,
output_seal/output_sha256. Inventory binds PAIRS.PRIVATE.json ordered pair_id,
X/Y CPU labels. Metadata:experimentE140,selection_frozen_before_reads:true,
labels_cpu_only:true,seed20261030,screen_candidates600,category_count>=8,
selection=first_up_to84_nonempty_different_in_generation_order,
parser=first_nonempty_line_lowercase_punctuation_stripped,other_policy=xy_only.
I2 must retain original frozen600 input, all1200 screen outputs/parser/selection
lineage, exact original answer/label and read-position references, acquisition
chronology, same-pass pair logits and no-answer-in-prompt source proof. Final
binding must point to original records, never inferred scalars or rejudging.

Output seal COMPLETE, inventory_sha256 exact, layers[44,52,60],
read_position=final_prompt_token,judging_bankE140,0<judging_cap_usd<=1,
lifetime_booked_usd within cap,unknown_charge_requests0,route_verified,
labels_cpu_only,redaction_audit_complete true/redacted_count0. source_seals list
{seal,sha256} original COMPLETE/COMPLETE_ONCE sources. MEASUREMENTS.PRIVATE.json
has exact ordered pair_id and blocks44/52/60 each A/B pointers identity,judgment,
native. Each pointer{seal_index,member,keys}; identity has pair_id/paraphrase/block,
judgment_id/native_id. Original judgment{id,status:KEPT|UNPARSEABLE,code:{id,category,values,evidence}
or null only for missing}; category is states_value/names_property_without_value/exhibits/silent; values is the original unique list from X/Y/OTHER. Native has text and optional id. Evidence is a literal substring. The lossless helper preserves the entire original record; no scalar projection is supplied by I2.
Producer representations must be frozen/tested before opening, no guessed joins.

SPEC additionally requires screen_seal/screen_sha256; inventory.screen_sha256
matches. Original screen seal COMPLETE E140 binds SCREEN_PAIRS.PRIVATE.json
all600 pair_id/generation_index0..599/greedy_max_new_tokens32/answer_A/answer_B
from the frozen original parser. source_seals bind original captures/parser
records; parser_frozen_before_screen,selection_frozen_before_reads,
no_answer_words_in_prompts_verified true. Adapter verifies all source hashes and
exact first84 eligible membership/CPU labels. No parser runs inside this adapter.
Final original parser/source capture mapping requires I2 verification; copied
posthoc scalar answers without original sealed parser lineage are inadmissible.


## §252 deviation2 first300 source contract

Authority b10b2694e permits the first300 original pairs only if the complete600 forecast exceeds6600s. The original600 bank remains immutable; operator/source owners must bind their exact original prefix wrapper and full phase forecast before acquisition. Scientific rates,40floor,first84selection and same once guard are unchanged.

For this scope inventory.screen_candidates and screen_seal.screen_candidates are300. SPEC.screen_scope_authority is `252_deviation2_b10b2694e`; SPEC.original_pair_ids_ref is `{seal,sha256,member,keys}` resolving to the complete ordered600 original pair-ID list in a sealed source identity artifact. Inventory.parent_identity_sha256 binds that seal. The complete300 screen IDs must equal its literal first300, with original indices0..299; no refill, reranking or inferred subset. All original source member/token/prompt/parent-bank and forecast proofs remain required in owner preflight. Missing scope authority/parent cannot be silently treated as the600 contract. All selection and statistics are unchanged; no outcomes opened during this prospective amendment.


## Original native-index transport

For original Oracle records without an embedded id, each measurement arm additionally supplies native_index, a sealed pointer to the original main/INDEX.json entry. The index and native pointers must use the same source_seal; kind must be oracle, block must match, id must equal identity.native_id, and native.member/keys must exactly resolve the index-relative member and singleton record offset. Any embedded native id must also agree. Native text/raw/malformed fields are never rewritten or reparsed; evidence checks use the unchanged text. I2 independently verifies original index-to-input pair/paraphrase joins before COMPLETE binding. No identity is inferred from text, row order, or answer values. Scientific analysis, selection, thresholds, and once guard remain unchanged. This transport was prepared after acquisition but before W-mech2 opened E140 outcomes.


## §252 clarification 2 — d1d15ccf2

SPEC must additionally bind `multiple_value_authority=252_clarification2_d1d15ccf2`. Primary tracking/prior uses only pairs where both asserted sets are singleton X or singleton Y. Any set of size greater than one is multiple, counts toward value-stating coverage, and is reported per block as readout and pair counts plus its category rate/Wilson interval. Original sets remain in local memory without tie-breaking. Singleton OTHER and empty sets retain their separate meanings.

Sensitivity adds EVERY pair with at least one multiple readout to the primary denominator, once, as neither tracking nor prior. This includes a pair whose other readout is missing, OTHER, empty, or also multiple; missing coverage remains explicit. Sensitivity rates/Wilson intervals are adjacent and never determine the primary reading. No cross-block filtering. This source change is post-judging/pre-analysis under explicit user clarification; no E140 outcomes were opened by W-mech2 during implementation. Original guard is unchanged.
