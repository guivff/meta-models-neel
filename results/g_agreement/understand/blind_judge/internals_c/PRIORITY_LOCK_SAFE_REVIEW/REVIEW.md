# W-internals-C: stalled priority-controller replacement

The proposed command was rejected by automatic approval review before execution. Its stated reason: SIGTERM to a live controller and a replacement that can affect multiple paid workers require trusted authorization for that exact process replacement. Nothing was stopped, replaced or restarted by the rejected command.

## Observed state

E117c is COMPLETE: all672 terminal,597KEPT/75missing, USD0.41786775. Raw and keyed owner handoff were published5754087e2 immediately. The original E117 bank remains OPEN, operational lifetimeUSD4 shared with main (part-c ceilingUSD2), no cap reset.

E117 main was admitted and launched as session92047/PID40018, but has made no physical reservation or paid call. It is waiting in the shared FIFO. Original controllerPID91859 and stopped own E118bPID76605 both have the same pacing-lock file open; the controller can stop a queued flock waiter and the kernel can grant it the lock while stopped. Main and controller then wait indefinitely. E118b has1676 saved readouts, bookedUSD0.2377836250 including its authorized prior upper bound; physical unknown0. E124PID3420 remains held,906 saved/known charges. No402 was fabricated.

## Concrete proposed recovery

1. Preserve the original controller source, plan and exact saved status. Verify PID91859 still belongs to this chat's priority_b724 command. Send SIGTERM only to that administrative controller, not to a paid worker.
2. Start the committed replacement priority_lock_safe with the original mutable plan and saved own-worker state. It checks current402/deadlines, exact module/phase ownership and zero unresolved reservation. Only then it automatically resumes the same already-authorized own E118b lock waiter to release the global lock. No worker restart or settled-readout resend.
3. Restore the registered phase order. While holding the pacing lock, the replacement only leaves a queued/unreserved worker stopped if that worker has no pacing-lock FD. If it has one, or FD inspection fails, it resumes it before releasing the lock. Existing/foreign FIFO entries are preserved. It never signals a foreign PID or stops an inflight reservation.
4. Verify main's first actual progress, then post the controller source/state/receipt to the integrator, W-mech2 and R-Q. Maintain the same bank caps, immutable prompts/source, raw records, rate intervals, cooldown and ledgers. No new experiment, allocation, model route, scientific analysis or guard.

Source: published1d4a686c4; PRIORITY_LOCK_SAFE_SOURCE_SEAL a93e21320efee22ceec861ac2e9881759e54837f2596051a799e20d8b129fd82. Eleven synthetic tests cover blocked-flock FD recovery, safe queue parking, preservation of foreign entries, unknown/inflight refusal, FD-probe error recovery, own process identity, deadlines/402 and CLI paths. Original worker/source bytes remain unchanged.

Before recovery, refresh authenticated OpenRouter ZDR/account privacy/credits and complete actual+open-cap+unknown exposure again. Publish a new supplementary source-bound dispatch gate younger than300s, preserving the original E117 admission and original OPEN allocation. The earlier35e22f18d dispatch refresh is historical and must not be treated as indefinitely fresh.

Route remains only OpenRouter/google/gemini-3.1-flash-lite/google-vertex/global, ZDR, collection denied, no fallback; no new paid POST afterFri30Oct15:00Z. Current E117 main/E118b/E124 lifetime caps4/1/3 are unchanged. The operational risk is process coordination: recovery lets already-authorized workers proceed. No alternative lock-file removal, indirect execution, changed rate or guessed settlement is proposed.

Await an actual human answer. No repeat recovery execution or workaround before approval.
