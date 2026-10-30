# E97 §217 clarification 2 resume

Use the existing sole I-5 official E97 bank and custody wrapper, original input/admission/cache/cap USD15. Do not replace it with E97PrivacyCopyBank. Import the new source from the committed B worktree. Wrap the entire existing bank call (and existing custody finalization) as follows:

```python
from projects.g_agreement.understand.blind_judge import e97_channel
from projects.g_agreement.understand.blind_judge.transport217c2 import installed
with installed(e97_channel):
    existing_official_bank_and_custody_runner()
```

The symbol above means the existing operator call, not a new entrypoint. I-5 retains credential, funding/admission and dispatch-lock custody. Bind this new SOURCE_SEAL in a supplemental resume receipt; leave original admission/source seals intact. No raw wire/ID/rubric change. Original failed result/response remain immutable. All99 successes are replayed from exact cache. Each of up to2 retries has a deterministic separate reservation through the original Client.one/Ledger; backoff30/60seconds before uncached retries, with sharedFIFO/402 and expiry checks. Existing HTTP429 handling is unchanged. Only pinned HTTP200 errors with explicit finite zero cost and finisherror/embedded429/5xx qualify; partial content is never emitted as a judgment. Unknown/charged errors still stop.

If both retries fail with qualifying errors, the entire affected request is terminal UNPARSEABLE with UNCHARGED_PROVIDER_ERROR_EXHAUSTED; it never enters singleton schema retries. Successful replies retain the frozen classifier/schema retry policy. TRANSPORT217C2.json records only response hashes/opaque request IDs/attempt numbers and the authority. The final judgment seal must have transport217c2_finalized=true plus source-seal/hash binding before analysis/watchers consume it. The installed context finalizes after the original runner returns, and restores all hooks; no paid dispatch happens on import.

28 offline tests pass, using the real original ledger/client with synthetic sends, exact actual failed-envelope hash, cached-failure resume, cached success preservation, stable wire equality, distinct reservations, two-retry exhaustion and cache idempotency, zero-cost-only classification, charged/unknown/402 stops, expiry during backoff and final-seal hash binding. RESUME_PREFLIGHT hashes the saved99-success inventory and original ledger. No new calls or ledger writes were made by this preparation.
