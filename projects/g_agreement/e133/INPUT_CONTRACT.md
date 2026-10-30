# E133 runner handover to item owner W-text

Screen public INPUT_SEAL.json (`experiment:E133`, `stage:screen`,
`labels_on_pod:false`, files items.json + MANIFEST.json). `items.json` has 900
prompts (300 multi_hop pairs +150 one_hop pairs), frozen pair-generation order,
member0 then1. Each public record:
`id,pair_id,family,member,ids,read_index,candidate_ids`.
family is multi_hop/one_hop; member0/1; read_index final original token.
`candidate_ids` is an ordered list of frozen single-token A/B pairs (E104/E131
same-pass scorer). Main pair-logit swap comparisons need the SAME ordered
recipient0/recipient1 pair on BOTH members; also include current/previous pair
if distinct. CPU-only label metadata specifies candidate roles, current/previous
and both recipient strings, parser target order, prompt/source provenance.
No labels/current/previous/name text on GPU. All prompt tokens and candidate pairs
must be bound with original pinned tokenizer before screen.

If item owner supplies a different already-sealed schema, C will provide a
source-only adapter with tests; no regeneration or scientific selection by C.
Main uses a NEW input seal stage main retaining exact chosen source prompt bytes,
first up-to84 multi_hop /42 one_hop pairs selected by CPU behaviour only.
`SCREEN_SELECTION_SEAL.json` binds screen COMPLETE output and original input,
CPU selection rule/source and frozen kept IDs. CPU labels and source-pointer maps
never stage on either pod. Main packet includes no reader-dependent selection.
