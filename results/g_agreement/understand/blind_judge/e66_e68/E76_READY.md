# E76 placebo judging READY — §194, USD2

Use the channels66_68 format-only converter and later_runner with bank E76, channel placebo. The frozen rubric is E68_RUBRIC.md in this directory: the byte-identical §172 E56 rubric. Source JUDGE_PACKET.json fields are id/property/values/readout, with a BLIND_SEAL.json carrying experiment E76, files.JUDGE_PACKET.json and rubric_sha256. Source packet order, opaque IDs and all decoded field bytes are retained; no sample is selected by this runner.

The registered shared pool is 500 random plus 500 shuffled vectors per reader. A judged packet can expand each readout against multiple frozen bank/row properties, so its row-expanded size must match the integrator-verified custody receipt and converted packet seal exactly, not an invented fixed row count. Every expanded judgment needs a unique opaque ID, with grouping/source identities kept private. The integrator verifies the frozen expansion before receipt issuance.

Converter spec: bank, source_seal, source_seal_sha256, source_packet, rubric. Run:

```sh
python -m projects.g_agreement.understand.blind_judge.channels66_68 --spec /integrator/e76-convert.json --out /new/e76-converted
python -m projects.g_agreement.understand.blind_judge.later_runner --spec /integrator/e76-run.json --preflight-only
python -m projects.g_agreement.understand.blind_judge.later_runner --spec /integrator/e76-run.json
```

Run spec follows E68: bank=E76, channel=placebo, packet=converted directory, packet_seal_sha256, budget_receipt/sha256, receipt/sha256. Budget receipt: issuer integrator, verified true, bank E76, allocation_id, reservation_included true, date_zurich 2026-10-28, reserved_judging_usd 2 and daily_committed_including_reservation_usd within the unchanged judging ceiling. Custody receipt: issuer integrator, verified true, bank E76, authority §194, pool placebo, frozen_row_expansion_verified true, positive n equal to the entire sealed expanded grid, packet_seal_sha256 and source_seals including original packet seal. Original bank/capture/forecast custody must be verified before issuance.

Fixed separate ledger: cache/g_agreement/understand/blind_judge/e76_2usd. Admission and reserve-before-send dispatch both enforce USD2. Other bank caps/ledgers unchanged. Same pinned Google Gemini/Vertex via OpenRouter, ZDR, data collection denied, no fallback; same singleton validation retries and UNPARSEABLE handling. Output E76_judgments is a sealed terminal grid, not an analysis result.

79f63fe0 / 25c32f25: only path/address spans in readout copies become [REDACTED_PATH]/[REDACTED_ADDRESS]; originals remain sealed unchanged. Address matching covers bare addresses and address:port. Keys/tokens still stop even inside a path. Guard patterns remain unchanged. The sealed PATH_REDACTION_AUDIT.json includes address_authority=25c32f25, affected opaque IDs, path/address counts and original/judge-copy hashes; JUDGE_COPY.json preserves exact judged text. Each rule must also be reported with affected IDs excluded as a sensitivity line after sealed judgments; no sensitivity analysis here. Historical path-only audit validation remains supported.

32 synthetic tests passed: E76 full conversion/admission, mocked pinned transport and USD2 cap, source/rubric bytes, address/path redaction and key stops, historical judgment adapters. No live packet opened, judging, analysis, GPU, ledger mutation or push performed.
