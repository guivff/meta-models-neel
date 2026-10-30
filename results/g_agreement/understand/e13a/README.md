# E13(a) fresh §84 free-target launch

Run the entire phase afresh from the sealed §84 captures. This is an operational completion of §101, using the exact existing `run.collect_unasked` implementation, all 1,680 frozen items in canonical order, native block 44, batch 32, and §84’s frozen decoding policy. No items or settings are rebuilt.

The full phase contains 3,360 Oracle generations (one greedy, one sampled per item; max 128 tokens) plus 3,360 J-lens and 3,360 logit-lens deterministic repeated readouts. Baseline repeats are not independent generations. Preserve all three readers even though blinded coding primarily needs the Oracle outputs.

Only the eight explicitly listed sealed capture/asked files are staged. The old unsealed 3,200/3,360 Oracle partial is never read, copied or resumed. Use a new output directory; existing directories are rejected. No recapture or asked-score rerun.

Setup allowance: 1,500 s outside science, including pinned asset checks/load and one unscored production-shaped canonical batch per reader. Science starts at the first timed unit, with a create-only clock. Three warmed batches per reader produce a median; forecast includes timing elapsed plus the full 53 batches per reader. Timing generations are discarded, then the full collection starts at canonical item 0 with unchanged seeds. Allocation is min(1.5F + 360, 2,400) s from first science, bounded by absolute custody and the 180 s retrieval reserve. NO_FIT stops the scope rather than reducing it. No automatic retry.

`LAUNCH_REQUEST.json` pins committed source, the archived code and this manifest. Run its exact command in `/weights/venv` with integrator-owned assignment and pinned asset receipts. Before launch the integrator publishes the local source/freeze and receipt commits, arms independent teardown, and binds the request hash in the assignment. Retrieve every output, including failure receipts or incomplete files. A complete run writes `FREE_SEAL.json` in the existing §84-compatible format; partial files remain unsealed and unusable.

Authority: verbatim §101 snapshot in REGISTERED_SECTION.md, extracted from the existing registered commit, plus the user’s explicit fresh-full-pass instruction. Shared briefs and original §84 source are unchanged. No judge or labels are included. Lens chat owns E13(b). W-core prepares locally; integrator pushes and operates.
