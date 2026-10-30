# E66 and E68 judging channels — READY

Integrator execution only. E66: §183 / 23a2e5c9, 542 existing records, USD 3 within the original USD 15. E68: d147b2fe, 1,512 native records, USD 3 on its own ledger. No live packet opened or converted during this build. No judge calls or analysis.

E66_RUBRIC.txt freezes all six §183 questions on every readout before judging; no stratum/prompt input. Boolean S1/S2/S3/S4/topic/eval_awareness plus a six-key evidence object. Evidence uses the existing whitespace/Unicode quote/dash/case-normalized verbatim check. This is an interface realization of §183, not E56's four-category taxonomy. E68_RUBRIC.md is byte-identical to the frozen §172 E56 rubric; the existing fixed A-then-B rendering (list elements joined with ` / `) is reused without normalizing source strings. Terminal UNPARSEABLE is retained, never converted to a negative code. Keep valid batch-mates; retry invalid records singly at most twice.

## 1. Format-only conversion

Prepare a JSON spec with fields `bank`, `source_seal`, `source_seal_sha256`, `source_packet`, `rubric`. E66 uses W-core's PACKET_SEAL.json and ignored BLIND_PACKET.jsonl; the seal's packet_sha256 and n=542 are checked. E68 uses W-mechanism's BLIND_SEAL.json (experiment E68, files.JUDGE_PACKET.json, rubric_sha256) and JUDGE_PACKET.json, containing only id/property/values/readout. Set rubric to this directory's matching frozen file.

```sh
python -m projects.g_agreement.understand.blind_judge.channels66_68 --spec /integrator/e66-convert.json --out /new/e66-packet
python -m projects.g_agreement.understand.blind_judge.channels66_68 --spec /integrator/e68-convert.json --out /new/e68-packet
```

Output PACKET.json preserves all decoded record values/order; ID/readout UTF-8 bytes are explicitly checked. RUBRIC.txt is byte-identical. PACKET_SEAL.json binds original source seal and packet hashes. No private map is opened. E66 and E68 remain separate jobs; output directories must not exist. JSON serialization is the only record-container change.

## 2. Admission and dispatch

Runner spec: `bank` E66/E68; `channel` structure/value respectively; `packet` converted directory; `packet_seal_sha256`; `budget_receipt` and its SHA-256; `receipt` and its SHA-256.

Budget receipt: issuer=integrator, verified=true, bank, allocation_id, reservation_included=true, date_zurich=2026-10-27, reserved_judging_usd=3, daily_committed_including_reservation_usd (within existing judging daily ceiling 300). E66 additionally requires shared_15usd_committed_including_reservation_usd<=15 and exclusive_3usd_reservation_within_shared_15usd=true. GPU ceiling changes do not expand judging authority.

Custody receipt: issuer=integrator, verified=true, bank, n (542/1512), authority (23a2e5c9/d147b2fe), packet_seal_sha256, and source_seals list of {path,sha256}, including the original packet seal. Integrator must verify source/capture/forecast custody before issuing this receipt; no exception to source-bank preregistration gates is created.

```sh
python -m projects.g_agreement.understand.blind_judge.later_runner --spec /integrator/e66-run.json --preflight-only
python -m projects.g_agreement.understand.blind_judge.later_runner --spec /integrator/e66-run.json
# Likewise for the separate e68-run.json.
```

Ledgers are fixed at cache/g_agreement/understand/blind_judge/e66_3usd and e68_3usd. Before E66 inference, reserve_parent holds USD3 under E66_EXCLUSIVE_3USD_ALLOCATION in the existing later_banks_15usd ledger, whose locked reservation machinery prevents other banks consuming it. The child ledger reserves each actual request under USD3. The parent hold is an envelope reservation, not a second spend; keep it until integrator reconciles final child actual/unresolved charges. A repeated conversion or completed job is never silently rerun. Preflight does not reserve or call the API.

Pinned Gemini/Vertex via OpenRouter, ZDR, data collection denied, provider only, no fallback; existing transport/cost failure stops unchanged. The runner seals terminal judgments before any private join. E68 value terminals can use the existing adapt_grid function; E66 terminals retain the six-answer schema for W-core's registered analysis. No scientific results are computed here.

Validation: 28 offline tests pass, including complete admission, exact byte preservation, source/rubric tampering, singleton retries, both mocked wire schemas/privacy settings, separate USD3 enforcement and real shared-parent reservation accounting. Tests use synthetic text only.

## E68 cap amendment — 2026-10-27, explicit Guiv instruction
E68 only is now USD6 in both allocation admission and dispatch. Integrator must provide a re-hashed budget receipt with reserved_judging_usd=6 and the updated reservation included in daily commitments. E66 remains USD3 within its existing USD15 envelope. Keep the historical e68_3usd cache/ledger path unchanged: its name is not the cap. No ledger reset, migration or write was performed. 11 CPU tests pass, including exact allocation rejection for the wrong bank cap and mocked reserve-to-limit behavior at USD6/E68 and USD3/E66. Original scope, rubric, route and retry policy unchanged. READY.
