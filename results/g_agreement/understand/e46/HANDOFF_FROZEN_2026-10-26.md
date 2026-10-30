# E46 frozen bank and persistence handoff — 2026-10-26

§157 clarification 1 (50edac15) resolves the definition hold. E46 remains lower priority than E42 and E43. Do not launch reader scoring from this acquisition request.

The bank is frozen before the Tuesday 27 October 12:00 CET deadline: four rows, 672 unique prefixes, 84 dev and 84 test per row, 42 A and 42 B in each split. All 672 independent final label checks and 336 paired token-length checks pass. Every inside-state authored source has at least 40 tokens before closing. Authored suffixes and tokenizer offsets establish source-bound labels; no model continuation or reader outcome was used to set them. The original preparation note is retained as dated history; the number/date B prefixes were corrected before the first bank seal to have no number begun, as clarification 1 requires.

`BANK_SEAL.json`: 1cd611a3a9b6cbddc48dba2ab235438e91d56120ce90b36862999e8ab9e28598.

The frozen state functions anchor the original read position. A unfinished words/numbers persist until their first observed lexical boundary. B states persist until the next completed word or number, requiring its right delimiter. Partial extensions retain the previous state. The unchanged E42 persistence core evaluates exactly 32 greedy tokens, with the same initial-unknown exclusion policy. No moving read-position classifier is used.

## Stage 1: integrator-only acquisition

LAUNCH_REQUEST.json and RUN_PLAN.json bind 336 test prefixes and the bank/state seals. STAGING_ARCHIVE.json gives the archive path and hash. The archive contains label-free token IDs, public seals and operational code; no private source item file or authored suffix is sent to the GPU. Generate all 336 continuations fresh exactly once, base Qwen, greedy 32 tokens, seed 20261026. No adapter or injection. A cold batch is charged but excluded from the warmed-mean forecast. Acquisition allocation is at most 1,800 seconds and counts inside E46's 10,800-second aggregate cap; it is not additional budget.

Use the exact worker argv and assignment schema in LAUNCH_REQUEST.json. An external hard stop and committed/published state functions are prerequisites. No worker-chat GPU launch or push. Preserve a failed attempt and request explicit authorization before retrying.

## Stage 2: once-only CPU persistence

After a complete verified pull, create:
`/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/results/g_agreement/understand/e46/cache/VERIFIED_PULL.json`

Required fields: `issuer: integrator`, `experiment: E46`, `verified: true`, `output_directory` (absolute path holding continuations.jsonl, PROVENANCE.json and FOLLOWING_TEXT_SEAL.json), `following_text_seal_sha256`, and `tokenizer_json` (the pinned local tokenizer path). The existing tokenizer is:
`/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json`.

Run from `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext`:

```sh
/Users/guivff/Documents/Neel_Exploration/activation-readers/.venv/bin/python results/g_agreement/understand/e46/persistence_once.py --receipt results/g_agreement/understand/e46/cache/VERIFIED_PULL.json
```

The command verifies the bank, state functions, code and following-text provenance before computation. It reserves PERSISTENCE_ATTEMPT.lock before validation and never retries or joins reader scores. Outputs are `e46/persistence_2026-10-26/ROW_MEDIANS.json` and PERSISTENCE_SEAL.json, binding the private per-item ledger. Long medians must be ≥24 and short medians ≤4. Misses and >20% initial-unknown rows are reported and excluded without tuning or replacing items.

## Reader hold

The reader request is not yet runnable: it must bind the actual persistence seal and eligibility before release. Channels are only probe, Oracle asked and NLA asked, with the newly frozen CANDIDATES.json. The full unchanged E36 252-item W1 parity gate at absolute AUROC tolerance 0.02 precedes production. Its source seal is `c41970528477a88e15144b7822e9d07e592ad21e340d65ba312d4513532c8aae`. Remaining reader custody must deduct actual acquisition and any prior E46 seconds from 10,800. Reference cells remain the original sealed E36 rows. No E36 or E42 scientific artifact was changed.

Validation: 10 CPU unit tests pass, including anchored completion and cold-batch forecast behavior; all frozen input/code hashes verified. No real persistence values or reader scores exist in this package.
