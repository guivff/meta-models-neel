# E62 early input-bank freeze — 2026-10-27

FROZEN as soon as checks passed, before the 11:00 CET deadline. No dropped cell.
Bank seal f69a4fa6726da61d656b1e7ecf65310bb3c226ee5309e129c2a93c4849647cfd.
FREEZE_MANIFEST.json supplies exact local paths and archive hash for the integrator.

4,620 records: S1–S5 × L0–L4 × 168 (84 dev + 84 test, 42 A/42 B per split),
plus S6 C0–C4 × 84 matched unlabelled test tasks. All 25 binary cells pass BOW
at 0.50. Six CPU tests pass, including W-mechanism's pure grid/schema validators
from 77d3f60d, executed without importing its model backend.

Source passages/labels are copied unchanged by E56/E57 bank seal. L0 text and
IDs match source token IDs exactly; the ladder has its own IDs and retains the
source ID as base_item_id. L3 for S2/S3/S4 is exactly the existing asked twin.
Other rung cues are identical across paired A/B items; definitions are frozen
in RUNG_DEFINITIONS.json. All pairs pass ≤1.10 token length ratio and identical
read-token checks. Value-word disjointness is inherited from source banks;
shared rung scaffolding is exempt. The S6 task text is unchanged across all five
cumulative contexts and has no A/B target or probe.

Runner contract: id, base_item_id, feature=Sx_Ly/S6_Cy, state, rung, split, text,
ids, first_content_index=0, read_index=len(ids)-1. Raw prompts contain no added
special tokens or unrelated W1 archive. L4 has verified single-token IDs for
` alpha` and ` beta`; A→alpha, B→beta. Private label/value fields must be stripped
by bind62.py before pod delivery. The exact private schema passes its validators.

W-mechanism owns runner/binding, W-lens owns J scoring/forecast, integrator owns
launch and push. Use runner 77d3f60d and later authorized operational pins; E36's
252-item parity gate, aggregate E62 ≤7,200 GPU seconds. Capture all block-44
positions before any native/behaviour stage; preserve the §181 forecast/GO hold.
§172 clarifications 3/4 apply: one greedy native readout per test item; Oracle
128 tokens, NLA 512 with closing-tag stop, unchanged prompts/adapters. S6 has
one readout per task per rung. No forced choice. No GPU/model/reader output
was generated or opened in this bank task.

R-L0/L1/L2/L3/L4 and falsifier remain §178's registered rules. This is a bank
handoff, not a claim that W-text implemented or executed the runner's analyses.
Do not regenerate frozen items. Verify the input and source hashes before binding.
