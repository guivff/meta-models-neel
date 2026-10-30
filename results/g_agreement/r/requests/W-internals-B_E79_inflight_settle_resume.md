# Request → W-internals-B: E79 Arm A in-flight reservation settlement and resume (2026-10-28 13:35Z)

Requested by: Track Q integrator. Authority: Guiv's ruling in the integrator chat, 13:3xZ, "Settle at USD 0.0102 bound".

## Facts (integrator-verified)

- Ledger: `wt-blindspot-internals/cache/g_agreement/understand/blind_judge/wmech2_E79/ledger.jsonl`. It holds 1,288 reserve and 1,287 settle events, with USD 1.50941025 settled. The run was started at 11:40:51Z from a detached 93d4356a checkout under receipt `results/g_agreement/r/e79/JUDGING_RECEIPT_E79.json` (sha a7380455…, allocation USD 15).
- **Unresolved:** `f90f575023070d729766196407d9ad1f22902f0ad5c417856710adebc0f62ad1`, stage `E79_attempt1`, reserved USD 0.0101765625 at 12:12:12.65Z.
  - The request file is present (sha 3ae9f09e679f3053315f953cb82d4946a38559868324290e377ed5677f6e622f).
  - **No response file and no result file exist.** The coordinator session ended at about 12:12Z, which killed the process mid-request.
  - Whether the provider billed it is unknown. There is no 429 evidence, so a52f8d0b's zero-settlement path does not apply.
- Job directory `wt-wmech/cache/g_agreement/understand/wmech2/E79_A/judge` holds START.json, JUDGE_COPY.json and PATH_REDACTION_AUDIT.json. There is no BLOCKED.json and no JUDGMENT_SEAL.

## Ruling to implement

Settle f90f5750 at its **reserved upper bound, USD 0.0101765625** ("in flight at process kill; billing unknown; conservative upper-bound settlement", Guiv). Do it through `Ledger.settle` under the DISPATCH lock, with a hash-bound reconciliation receipt beside the request. Never hand-edit the ledger.

## Gap that needs code

After settlement, a plain resume would still stop:
- `Client.one` finds no result file and calls `reserve`, which raises "already sent/reserved".
- The client then returns `PRIOR_RESERVED_NO_RESPONSE_NO_RETRY`, and `send()` requires a response file, so it stops with "no resend".

**Please add** a bounded resume for exactly this case, like a52f8d0b:
- The one interrupted batch gets one retry under a distinct, deterministic retry identity with its own reservation, under the same USD 15 allocation and global guard.
- Settled successes are reused from cache.
- START.json must stay identical (same receipt sha).
- Cover it with offline tests, add a SOURCE_SEAL, and push to r/blindspot.

The integrator then runs the settlement once, the resume preflight, and the resume, and posts the result.
