# Later-bank judging runner — E62/E62P, E59 and E63 wired

READY for integrator binding and dispatch. Command, from this worktree:
`python -m projects.g_agreement.understand.blind_judge.later_runner --spec SPEC.json`
Add `--preflight-only` to verify gates and packet without an API call.

Supported banks: E57, E56, E62, E62P, E59 and E63. E61 D5 remains deferred; D4 requires no judge and is rejected.

SPEC.json fields: bank; forecast_repo, forecast_commit (full SHA), forecast_path, forecast_sha256; budget_receipt, budget_receipt_sha256; receipt, receipt_sha256; packet, packet_seal_sha256; rubric. Existing bank_gate.py defines budget receipt: integrator verified, dated 2026-10-27, all six authorized banks, reservation_included true, reserved_judging_usd 15, daily_committed_including_reservation_usd <=300, allocation_id. This allocation is shared across later banks, separate from D5/E54's USD5.

The integrator custody receipt must include issuer=integrator, verified=true, bank, n, forecast_sha256, bank_seal_sha256 and capture_seal_sha256 matching the committed forecast, packet_seal_sha256, and source_seals [{path, sha256}] for the verified pulls. All gates run before packet access. Packet directory contains BLIND_SEAL.json (experiment=bank, rubric_sha256, files including JUDGE_PACKET.json). The frozen E56 rubric hash is checked. Public records must contain exactly id (20–64 hexadecimal opaque characters), rubric (frozen text with the value definitions), readout. An export containing property/values fields or source row/reader/arm identifiers is rejected: the integrator must seal its wire-ready blind export first. No private key is read or sent.

Uses E10 transport: google/gemini-3.1-flash-lite, google-vertex/global through OpenRouter, ZDR on, collection denied, no fallbacks. Requires the existing pinned privacy proof and live route inventory check. Fixed later_banks_15usd ledger, exclusive cross-bank dispatcher lock, atomic reserve-before-send, full raw request/response evidence and actual costs. Initial-pass upper bound must fit remaining budget; every retry is separately reserved within the same USD15. Budget, transport, route, unknown cost, and unresolved reservations stop dispatch; they are not UNPARSEABLE. No automatic restart after a failed job or duplicate dispatch.

Batches of four; keep each valid code, normalize whitespace/Unicode quotes/dashes/case for verbatim checking, retry only invalid records singly up to twice with unchanged wire rubric/model/route. Exhausted validation failures become UNPARSEABLE. Full A/B lists survive. Terminal grid is sealed before any joining; no category-share analysis. Raw per-request results preserve valid records if a later transport/budget stop occurs. Integrator joins private row keys and reports row-level counts downstream.

Four offline tests pass, including actual E10 Client with fake transport, cap refusal and duplicate-send protection. No live judging, packet read, forecast bypass, GPU, pod, push or scientific analysis performed by this build.

## E62 / E62P extension

Use bank=E62, channel=value for S1–S5 and bank=E62, channel=eval for S6. Each requires its own verified receipt n for that channel. Value uses JUDGE_PACKET.json and frozen E56 rubric; eval uses EVAL_PACKET.json and S6_RUBRIC.md, exactly {id,readout} on the wire, returning boolean eval_mention plus evidence. Separate bank/channel start guards and request IDs share one USD15 ledger. S6 is never coerced into A/B or D5 categories. Frozen forecast excludes S6 from R3b, while still gating access to E62 outputs.

Use bank=E62P, channel=value for the 15 placebo cells. It is an E62 sub-bank under the same six-bank budget allocation, with its own E62_PLACEBO forecast and captures. Original E62 forecast cannot admit E62P. Original forecast b62033082d2be6cd4e377fe9310295035b732429; placebo fb26a098c545dc8e0049f1955b9cb7362ff56b13. Integrator must bind the matching capture lineage, never silently reuse a different capture hash. Full file paths and hashes are supplied in SPEC; no reader content opened during build.

Eight offline tests pass across runner and gate, including S6 schema/evidence isolation and rejection of cross-bound original/placebo forecasts. Remaining-bank order is E59/E63 next, then E61 D5. D4 has no judge and is not admitted.

## E59 and E63 follow-on

E59: bank=E59, channel=value, E56 value rubric with full A/B lists. Its own committed R3b forecast and exact bank/capture custody are required; a forecast for E57 is not accepted.

E63: bank=E63, channel=rp2, D5 five-category rubric. Packet is exactly {id,readout}; no property, row, arm, reader or value metadata on the wire. Custody receipt additionally requires n=400, per_reader_counts={oracle:200,nla:200}, sampling_seed=20261027 and sampling_without_replacement=true. Integrator freezes the registered uniform 200-readout sample per reader using the existing E63 coding plan before dispatch; runner never samples based on codes, opens private keys or runs R-P2/TVD. Compare only after matching-reader MISSED distributions and complete judgments are sealed. No Oracle-to-NLA reference substitution.

E63 admission blocker: integrator HANDOFF reports no forecast/coordinator record yet. This runner requires a committed, byte/hash-verified JSON coordinator record: experiment=E63, status=RATIFIED, forecast_required=false, ratified_by, committed_before_any_reader_output=true, bank_seal_sha256 and capture_seal_sha256. Supply its repo/commit/path/hash through the forecast_* SPEC fields; custody forecast_sha256 binds that exact record. This schema is a fail-closed implementation contract, not an invented ruling or permission to bypass the gate. E61's existing exception does not admit E63. If the coordinator instead requires an E63 forecast, leave dispatch held and update the gate to that explicit ruling before use.

Thirteen offline tests pass, including sealed channel admission for E59/E62-S6/E63, tamper rejection, D5/E56 taxonomy separation and prospective coordinator-record binding. No reader output opened, inference dispatched, or scientific analysis run. All bank/channel jobs retain the one cumulative USD15 ledger inside the allocated daily ceiling; E62P is part of E62's allocation.

## 94a770cc(a,b) / HANDOFF 2c7d962d — E57 then E56

Supersedes the earlier requirement that the integrator invent a wire-ready export. SPEC.packet now points directly to analysis402's original blind directory and packet_seal_sha256 to its original BLIND_SEAL. After all forecast/budget/custody gates, the runner deterministically renders each {id,property,values:{A,B},readout} into {id,rubric,readout}. Frozen rendering is the exact E56 rubric bytes followed by `\n\nProperty: {property}\nA: {A}\nB: {B}\n`. Field strings are substituted verbatim, once; order is always A then B, unrelated to truth. No additional source row/reader/arm/truth fields are admitted. The original property field is used exactly as supplied under ruling (a). No value-word selection or schema repair.

Optional sealed conversion command:
`python -m projects.g_agreement.understand.blind_judge.judgment_adapter402 wire --spec SPEC.json --out NEW_WIRE_DIR`
This runs the same admission gates without inference. It writes WIRE_PACKET.json and WIRE_SEAL.json. To use it, add wire_packet and wire_seal_sha256 to the original SPEC; runner verifies the rendered records equal the rendering of the original sealed packet, including rubric bytes and A/B order. Direct dispatch renders the same bytes in memory. No original blind seal is replaced.

After a complete terminal grid, integrator runs:
`python -m projects.g_agreement.understand.blind_judge.judgment_adapter402 adapt --blind ORIGINAL_BLIND_DIR --blind-sha ORIGINAL_BLIND_SHA --terminal TERMINAL_DIR --terminal-sha TERMINAL_SHA --out NEW_JUDGMENT_DIR`
Adapter currently admits E57/E56 value channels only. It writes JUDGMENTS.json as the exact flat list W-mechanism requested, ATTEMPTS.json as an opaque-ID audit sidecar, and JUDGMENT_SEAL.json whose blind_seal_sha256 binds the ORIGINAL BLIND_SEAL. The seal also binds terminal/source hashes and all output files. Set analysis402 spec.judgments to NEW_JUDGMENT_DIR/JUDGMENTS.json and spec.judgment_seal to NEW_JUDGMENT_DIR/JUDGMENT_SEAL.json. Output directory is exclusive; no overwrite or duplicate adaptation.

**W-mechanism consumer contract (requires its corresponding source/seal update before analysis):**
- Kept records have exactly id/category/values/evidence. Values and evidence remain byte-for-byte as delivered, including both-value lists. Evidence checks use clarification2 normalization; no substring fabrication.
- Exhausted records have exactly {id, category:"UNPARSEABLE", values:[], evidence:""}. This is a missingness sentinel, not a fifth judge category or silent code. ATTEMPTS records status and retry count separately.
- Replace strict old validate_judgment at the import boundary with judgment_adapter402.validate_flat (or its sealed equivalent). It supports normalized verbatim checks and the explicit sentinel.
- After private joining, exclude sentinel records from S numerator AND denominator and all S resampling inputs. Keep the item/repeat grouping of retained records. Call summarize_row separately per row and pooled, or use the same logic: S=(correct_only-wrong_only)/kept; both-value codes contribute zero; kept=0 gives null/NOT EVALUABLE. Report total/kept/UNPARSEABLE and strictly >5% flags. The helper score_values returns only retained scores; preserve corresponding item keys when assembling CIs.
- The unmodified analysis402 consumer rejects UNPARSEABLE. Do not run its once-only analysis until W-mechanism has adopted this contract and refreshed its source seal. This adapter performs no scientific aggregation on real readouts.

E61-D4 post-hoc judging is CANCELLED by 94a770cc(d). No D4 channel was implemented, and unsupported-bank tests keep it blocked. E61 D5 is separate and remains deferred. This adapter does not change E62/E62P rules or launch anything.

E62 adapter extension: the same adapt command now accepts --eval-terminal DIR --eval-sha SHA. Both original value and S6 grids must be complete and bind the original E62 BLIND_SEAL; output combines both grids and rejects cross-channel IDs. Kept S6 codes retain id/eval_mention/evidence; exhausted S6 codes use the same explicit UNPARSEABLE sentinel. No E62P required for this judgment conversion; scientific R-L5 remains governed by 94a770cc(c). Five adapter CPU tests pass; no real conversion or analysis run.

55833480(a): list values now render elements joined by " / " in frozen order, without sorting or selecting a synonym. E57 antonym records supported. Combined E62 value/S6 adapter tested end-to-end, requiring both terminal grids. 20 offline tests pass; fixed test-module state leakage exposed by reversed test order. E67 remains uncommitted until after this priority fix.
