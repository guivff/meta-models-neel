# E49 earlier input-bank freeze — integrator handoff, 2026-10-26

Authority: user clarification of §163, referencing `51480a7d`. The target is the **input-bank seal**, Tuesday 2026-10-27 12:00–14:00 CET, or sooner once all generators pass build checks. This supersedes the earlier 20:00 target and the initial post-seal BOW plan. Rules and thresholds are unchanged.

Current availability: 10 of 16 generators. W-text's seven and W-internals' three are integrated. Missing: `arith_carry`, `arith_compare`, `branch_taken`, `var_type_at_use`, `instruction_provenance`, `decimal_separator`. W-mechanism's local queue still records these as pending. The current source seals are provenance records, not a complete input-bank seal.

## Order of operations

1. Integrate all 16 generators; preserve the already sealed PRECALLS. Validate 84 dev + 84 test, balance, lengths, labels, read tokens and exact-prefix twins.
2. Build a versioned draft in ignored cache with `freeze_bank.py --tokenizer TOKENIZER_JSON --out NEW_DRAFT_DIRECTORY`. This writes `DRAFT_MANIFEST.json`, explicitly **not frozen**.
3. Run CPU build QA with `bow_once.py --draft NEW_DRAFT_DIRECTORY --out NEW_QA_DIRECTORY`. Vocabulary and classifier fit on dev; evaluate test. Preserve each attempt and lock. A tracked-state AUROC > 0.65 requires a generator fix and a new draft/QA attempt before sealing, as now expressly authorized. Descriptor rows are exempt from the BOW ceiling. No model or reader run precedes the input-bank seal.
4. Run `freeze_bank.py --seal-draft DRAFT_DIRECTORY --qa QA_DIRECTORY --out NEW_FROZEN_DIRECTORY`. This verifies exact hashes, complete row coverage, all BOW pass flags against the numerical threshold and source/PRECALLS identity. It copies the exact QA-tested input bytes, takes an exclusive experiment-level freeze lock, and writes `BANK_SEAL.json`. Publish that manifest and its SHA-256 in the commit and handoff. No generator rerendering happens during sealing.
5. The integrator runs **one pod job**: full 252-item W1 parity first, then acquisition for block-44 probe, base-Qwen text gate and all registered reader channels; seal all outputs. No second bank freeze.
6. The once-only analysis computes/applies probe ≥ 0.90, base ≥ 0.85 and tracked-state BOW ≤ 0.65 first, reports failed rows, and only then accesses reader scores for qualified rows. `rules49.qualify` now reads gate fields only; both pre-call figures use only gated rows. Strict remains primary, middle-band-excluded descriptive.

The final native channel package and sealed once-only analysis command are still required before a READY launch request. This note is the integrator's watched handoff; it is not an input freeze or launch authorization. W-text does not push or launch GPUs.
