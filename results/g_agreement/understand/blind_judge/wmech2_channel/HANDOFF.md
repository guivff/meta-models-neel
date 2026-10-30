# W-mech2 E56 judging channel — Integrator execution

Priority E79 Arm A, then E78/E70/E72 after the already published E80/E80c and E79-extension handoffs. E76 settlement is removed: Guiv reports the resumed run clean at 1,132 calls / USD1.58. Its bounded backoff code is already on r/blindspot (a52f8d0b).

No API calls were made by W-internals-B. Do not treat SOURCE_SEAL.json as a judgment receipt. Runtime writes JUDGMENT_SEAL.json only after actual ZDR inventory, pinned account privacy proof, every sent wire, every response route/completion/charge, and the complete redacted grid verify. The seal binds BLIND_SEAL.json, route_verified, redaction_audit_complete, redacted_opaque_ids and all output files. Terminal UNPARSEABLE entries have empty values/evidence and remain missing. Only schema failures get two single-record retries; transport failures stop. Resume uses identical request IDs and cached responses, never resends an unresolved reservation.

From this checkout (or a shared-branch checkout retaining the recorded absolute cache paths):

```sh
python -m projects.g_agreement.understand.blind_judge.wmech2_channel --bank E79 --preflight-only
python -m projects.g_agreement.understand.blind_judge.wmech2_channel --bank E79 --receipt /absolute/path/to/integrator-allocation.json
```

The Integrator supplies OPENROUTER_API_KEY through its existing secret mechanism. Never put it in a receipt or command argument. The receipt must contain:

```json
{
  "issuer": "integrator",
  "verified": true,
  "bank": "E79",
  "packet_seal_sha256": "dca5ca99b494da35dfea0f2f2516ed086e6c2de13e394184510ac91c831ba2ec",
  "forecast_and_custody_verified": true,
  "reservation_included": true,
  "allocation_usd": null,
  "allocation_authority": "fill with registered allocation reference",
  "global_judging_committed_including_reservation_usd": null
}
```

Nulls must be filled with actual verified allocations, inclusive of prior spend and reservations. This template is not clearance. E79 preflight: 4032 records, 1008 initial calls, USD13.2398287500 initial upper bound; 26 redacted records. Retries also reserve under the same allocation. Ledger path is fixed across checkouts under wt-blindspot-internals/cache/g_agreement/understand/blind_judge/wmech2_E79; each other bank has its own wmech2_BANK ledger.

Judgments are written directly to W-mech2's configured `judgments` directory (E79_A/judge). The analyst can then run its already frozen once-only analysis. No joins or analysis run here. E78/E70/E72 use the same command with their bank and matching verified receipt; their delivery-seal hashes are bound from WMECH2_DELIVERY.json. E78 ordinal rows remain NOT EVALUABLE unless a registered mapping exists; the channel invents no mapping.

E80/E80c: ../e80_channel/HANDOFF.md (shared USD50). E79-extension: ../../e79_extension/HANDOFF.md (2688 committed vectors; I-5 already notified). E99 remains a separate USD40 preparation, not execution-ready until all required frozen family exports/dependencies are bound.

## E63 R-P2

The same CLI now accepts `--bank E63`. It reuses all400 opaque IDs from existing RESULT_SEAL 2b175dc900147aed12029f2cd37f6e21c0c88807ee5e6833a8c3467758682ea7. The packet's constant property/empty values are verified then omitted from the unchanged D5 wire, which contains only id/readout. No resampling or private-key opening. Preflight initial upper USD0.9736190625,100 requests,zero redactions. Use a matching E63 integrator receipt; output is analysis63follow_verified/judge_rp2. Flat D5 codes and lossless TERMINAL.json are both sealed; missing codes remain UNPARSEABLE with empty evidence, never a D5 category. The existing normalized real-row bundle and matching-reader MISSED reference are required for later R-P2 comparison, not for this coding channel. No analysis or once-guard alteration here.
