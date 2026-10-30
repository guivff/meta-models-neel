# E40 overnight analysis authority — 2026-10-26

Snapshot at `886d03b040d28ae037b07a983029891439f02f96`.

## §149 Overnight standing orders (26 Oct, 01:55 CET, until Guiv's next message; extends §136)

1. **Timing and cap stalls.** For any run with no production record yet, the integrator may authorise, without the
   coordinator:
   - a cap raise up to 2× its current total, a separate setup allowance up to 900 s, and sharding up to 4 pods, each
     with its own parity gate and its own deadline;
   - up to two operational-only retries.

   Science, items, rules and parity tolerances never change. Each such change is recorded in HANDOFF as
   `§149 OPERATIONAL`. Owners re-pin only the cap and deadline fields when asked. Spend stays inside the USD 1,400
   guard.
2. **Analyses.** Each owner sets an hourly self-check. When its run's sealed pull is delivered and verified, it runs
   its single registered analysis once and posts the verdicts against the registered rules only.
   - **Owners:** E24 and the impact audit, W-core; E32, W-internals; E34 and E38, W-mechanism; E29, W-text with W-core;
     E36 and E41, W-text; E39, W-lens; E40, W-sae.
   - **Ambiguities:** recorded as `OWNER_READING` and held only if they touch a rule.
3. **Unchanged:** a parity, validity or rule question still stops and waits. Whiteners are deleted before any pod is
   released, after its outputs are pulled and verified.

**§149 amendment (2026-10-26 02:00 CET).** Worker chats' scheduled self-checks are not reliable (the 19:00 W12 freeze
task never fired). The integrator's watchers are. So:
- **Integrator runs committed analyses.** For any run whose owner has committed a once-only analysis entry point
  (command, code seal, once-only guard), the integrator runs that pinned command exactly once on the verified pull,
  in the owner's output location. It commits the sealed outputs unchanged, labelled `§149 RUN-BY-INTEGRATOR`.
  - It does not interpret, change code, rerun on failure, or open private label files beyond what the command itself
    reads.
  - Blind-coder and judge steps are excluded.
- **Otherwise the run waits.** If no committed entry point exists, or the command stops on any validation, the run
  waits for its owner.
- **Owners review.** Owners verify the seal and post verdicts in the morning.
