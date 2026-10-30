# E104 judging bank: code ready, cap USD5

Reuses E101's E56 transport, exact adapter402 renderer/RUBRIC, original reserve/settle Ledger and route/response audits. OpenRouter google/gemini-3.1-flash-lite, google-vertex/global, pinned provider, ZDR, data collection denied, no fallback, max_tokens4096. Separate E104 ledger and cache; E87/E100 processes and frozen sources are unchanged. Shared FIFO pacing/rate429 cooldown is reused. Any actual HTTP402 persistently pauses the shared funded banks; unknown charges are never guessed or edited. Terminal UNPARSEABLE codes remain missing.

Awaiting committed dev-selected U/N doses and sealed eligible test acquisitions. The existing projects/g_agreement/e104_analysis/adapter.py verifies exact measurement-source pointers, arm hooks, all84paired test items per eligible cell and committed dose identity. It rejects dev results and no-dose cells. This bank accepts that canonical SPEC and uses its verified native text, frozen property and A/B values unchanged. No eligible cells means no paid bank. Up to672readouts/168initial four-record requests; complete initial upper bound must fitUSD5 before execution, and the original Ledger caps all calls including validation retries. Actual size, cost and route receipt are unavailable until those outputs arrive; no paid E104 calls have run.

Use local SPEC paths rooted at cache/g_agreement/understand/funded_queue/E104: blind=.../blind, private=.../PRIVATE.json, judgments=.../judgments. dose_path/full40hex dose_commit/dose_sha256 and input_seal/input_sha256 follow e104_analysis/README.md. Keep private join local. Commands:

```
python -m projects.g_agreement.understand.blind_judge.e104_judging prepare --spec LOCAL_SPEC.json
python -m projects.g_agreement.understand.blind_judge.e104_judging run
```

Before run, Integrator writes local E104/GLOBAL_ADMISSION.json: verified_by_integrator=true, bank=E104, cap_usd=5, bank_admission_sha256=actual ADMISSION.json hash, actual_plus_open_caps_usd=current programme actual plus running caps including E104 (≤1000 per §212 amendment2). Retain ledger evidence with that receipt. Never run a second E104 worker; per-bank DISPATCH.lock prevents duplication. Resume only after all existing reservations are settled through Ledger, and retain caches. JUDGMENT_SEAL is emitted only after real audited responses, binding input/blind/source/global admission hashes and every output member. No synthetic execution is a route audit.

## 2026-10-29T01:52:21.195274+00:00 — §217.5 applied

Charged finish_reason=length now yields terminal UNPARSEABLE immediately, without schema retries; ATTEMPTS retains actual0/1/2 count and CHARGED_LENGTH reason. Actual saved response/charge/route remain unchanged and verified. Unknown provider/finish errors stop this bank. This addition is separately source-sealed, and no running E87/E100 dependency was changed.
