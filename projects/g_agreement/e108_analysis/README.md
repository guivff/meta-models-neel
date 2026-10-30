# E108 pre-output analysis contract (§219)

CPU only. `python3 -m projects.g_agreement.e108_analysis.adapter --spec SPEC.json`.
No outputs have been read in preparing this adapter. Commit source/tests first.
Do not run on a partial bank; preserve all 1008 native items and 84 placebo vectors.
The fixed E108 guard is shared across worktrees and must never be removed/replayed.

R-CH1 is Oracle delayed, pooled over the 11 non-number categories. The signed
contrast is Oracle rate minus max(mode rate,outside rate), >=.15 and CI lower>0.
Falsifier is contrast<=0; NLA is alongside, descriptive. Item bootstrap uses the
common.stats defaults (5000 draws,seed0). The same indices resample each system,
retaining separate missing masks; max is recomputed each draw. No undefined draws
are dropped. Report all category/arm rates, number/non-number, J fractions, and
placebo rates. NONE/multiple/failed extraction counts stay separate. An early
choice in delayed is reported without adding an unregistered exclusion.

Pre-output implementation conventions: mode uses all eligible ground-truth items
in each category across arms, as registered, excluding just the held-out prompt-arm
item. Canonical member IDs must come from the blind extraction, not this adapter.
Ties use lexical canonical ID order. LOO predictions are fixed before scoring;
bootstrap resamples their hits, never trains on bootstrap duplicates. Review these
conventions before the bank seal; changing them afterward requires a dated ruling.

SPEC: inventory_seal, inventory_sha256, inventory_commit(full40), output_seal,
output_sha256, analysis. Inventory must be a committed seal in this checkout,
experiment E108, containing INVENTORY.json. Native metadata: id,kind=native,
category (exact CATEGORIES strings),arm,prompt_id; placebo: id,kind=placebo.
A complete output seal binds inventory_sha256, route_verified=true,
redaction_audit_complete=true, ground_truth_blind=true, outside_generation exactly
as adapter.py, and source_seals [{seal,sha256}]. Its MEASUREMENTS.json holds one
{id,fields} per inventory ID. Every field is a pointer {seal_index,member,keys}
into an unchanged, hash-verified original JSON source. Native fields: hits
({oracle,nla,outside}: bool or null for UNPARSEABLE), ground_truth
({status:ONE/NONE/MULTIPLE/UNPARSEABLE,canonical_member:string for ONE else null}),
J_fraction (number0..1 or null), choice_token_offset (int or null). Placebo: hits
({oracle,nla}:bool/null). The owner supplies exact extraction/judgment-to-schema
bindings; absent bindings block execution rather than guessing a normalization.
All source texts, labels and private joins remain local CPU-side. Publish aggregate
RESULTS and the hash receipt; BINDING paths may be local but contain no labels.
