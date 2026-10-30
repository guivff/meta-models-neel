# E80/E80c judging channel — ready for Integrator custody binding

Explicit user choice: existing E56 route, OpenRouter → google/gemini-3.1-flash-lite → google-vertex/global, ZDR, collection denied, provider pinned, no fallbacks. This is the disclosed substitution for WorkspaceBench's configured model. One shared USD50 ledger covers both banks and all schema retries. No paid call has been made by this worker.

Reuse W-text's frozen export v3 and renderer (export80.py judge_messages extracted unchanged from the verified source AST to avoid loading its tokenizer). Exact frozen system/user strings and response schema are sent with one readout per call. No E56 rubric text or private IDs are added to the wire. Multilingual's default regex stays CPU-only; optional MC is never dispatched. The channel returns raw family judgments, not an invented generic pass score; use the pinned family verdict logic during integrator analysis. Original source/reference files remain W-text's existing export. Source and route hashes are in ROUTE_SEAL.json.

Run `python -m projects.g_agreement.understand.blind_judge.e80_channel --spec SPEC.json --preflight-only`, then omit the final flag to dispatch with the integrator-held environment credential. A spec contains:

- `bank`: E80 or E80c.
- `judge_packets`: original W-text `cache/export_2026-10-28_v3/JUDGES.PRIVATE.json` path (hash fixed by route seal).
- `readouts`, `readouts_sha256`: CPU-only JSON array of `{id, item_id, readout}`. `id` is a unique opaque 32-character hex record ID; `item_id` is W-text's E80 item ID used only locally. Exactly 1036 records (E80, two readers) or 3108 (E80c, two readers × J/random/PCA); E80's none condition is reused, not judged again as E80c. Integrator retains the row/reader/condition map.
- `custody_receipt`, `custody_receipt_sha256`: receipt with issuer `integrator`, verified true, bank, n, readouts_sha256, `e80b_forecast_precedes_readers_opened: true`, and source_seals array of `{path, sha256}` for the verified reader outputs. This receipt certifies the complete row/reader/condition join.
- `budget_receipt`, `budget_receipt_sha256`: issuer integrator, verified true, shared_E80_E80c_allocation_usd 50, reservation_included true, global_judging_committed_including_reservation_usd (including this allocation, ≤500).

Both jobs share the fixed existing-owner cache path from ROUTE_SEAL.json, a dispatch lock, and E10's reserve-before-send Ledger/Client. Remaining cap includes prior charges and unresolved reservations. Each bank must fit its first-pass bound before sending; every schema retry is independently reserved and charged. Only successful-transport schema failures retry (up to two); 429 or uncertain transport stops without routing alternatives. Existing output directories cannot be overwritten. Key/token matches stop; existing path/address redaction is applied to judge-copy readouts and recorded for the required sensitivity line. Templates remain unchanged.

Offline checks cover all 420 paid-family item prompts and schemas, the 98 CPU-only items, model/provider/privacy pinning, schema type failures and the wrong-model rejection. Integrator must run preflight against its actual readout export before dispatch. Guiv relays this handoff to the Claude Integrator.
