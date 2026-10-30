# Independent E87/E100/E101 dispatch — §212 amendment2

Direct user instruction: E100cap30 and E101cap5 run alongside E87; no bank waits for E87 completion. Global judging ceiling1000, flag800, counted as settled actual plus open caps of running banks. Completed/unused allocations are released. No route, prompt, wire, token cap or scientific retry policy changes.

parallel_funded.py wraps the preserved funded_queue.py/e101_judging.py dispatchers in separate processes. Each retains its own original bank lock, ledger, stage/request identity and cache. The obsolete request-duration cross-bank lock is replaced by a shared FIFO token clock, released before inference. Initial aggregate pacing is one new physical request/second, fairly split across requesting banks; their HTTP calls may overlap. Cache replay consumes no throughput slot. A429 doubles the shared interval (up to30s) and starts a shared5–60s cooldown. It retries only a rejected429 without generation ID/choices, at most four times, each under a deterministic distinct request ID and original reserve-before-send cap. Unknown429 usage remains conservatively reserved; no guessed zero or hand-edited ledger. Other transport failures retain fail-closed behavior. SharedHTTP402 latch remains unchanged and halts every bank at its next request boundary.

For a bank already executing the serial dispatcher, operator handoff uses its existing between-request latch as an explicitly labelled OPERATOR_PARALLEL_HANDOFF (no provider402 claim). The old process stops at a completed-request boundary. Its ledger is checked for no in-flight reservations; only the matching operator marker may be removed. Any actual provider402 evidence replaces/retains the credit pause and is never cleared. No SIGTERM, killed request or resend is involved. Both old and new execution receipts are retained.

```
python -m projects.g_agreement.understand.blind_judge.parallel_funded --bank E100
python -m projects.g_agreement.understand.blind_judge.parallel_funded --bank E87
```

E101 had already completed all336 records forUSD0.18094775 before the parallel handoff; its existing JUDGMENT_SEAL is reused, without new calls. Its original start remains22:39:03Z. Any later attempt to run E101 through this wrapper returns ALREADY_COMPLETE.

Each bank's PARALLEL_STATUS.json records start/completion. THROUGHPUT.json records shared cooldown/interval and sent counts. After completion, PARALLEL_EXECUTION.json binds the executed wrapper in the bank's final judgment seal, alongside its original source/route seal. This changes no codes or denominator. Operator start/ETA and actual-plus-open-cap admission are published beside this handoff. Two focused tests cover shared backoff and exact-wire separately reserved429 retries/cache reuse; earlier grouped/two-cell/402 tests remain applicable.

Pacing lock correction: the short shared state lock uses blocking flock; contention is expected across independent banks. Bank-lifetime DISPATCH ownership locks remain nonblocking. Regression test holds the state lock while a second bank waits, then verifies it receives its slot. No ledger/wire/token-cap change. Cached results are retained on boundary restart.

## 2026-10-29T01:51:34.139621+00:00 — I-3 → judging wrapper owner: E95 §217 integration

ACK requested here. E95has no readoutpacket or livejudgeGOyet; existingE95dispatcher reusesE87wire/E10transport. BeforeliveE95dispatch, bind existingE56frozenroute/settings and sharedparallel/402 latch, chargedlength terminalUNPARSEABLE, unknownprovidererror stopbank/coordinator. Guivstandingauthorization covers blindedopaqueIDs/propertydefinitions/generatedtext only, authorized gateway modelgoogle/gemini-3.1-flash-lite→google-vertex/global,ZDR/deniedcollection/nofallbacks, bankcap60USD andcurrent§212amendment2global1000USD. Preservefixedstratifiedindex/25%oldrubric andonce-onlyledger. Return exactwrapperadapter contract/sourcebinding in E95/HANDOFF; do notlaunchjudging orrewriteprompt/rule.

## 2026-10-29T02:01:52.472143+00:00 — E95 cap40 terminal disposition

I-3 → judgingowner: withdrawE95liveintegration/launch request, finalNOT RUN(operational) atfirm40h capafterstep3. NoE95scientificpayload/judgecalls. Retainexistinggeneric§217wrapperwork, no E95reservation.

## I-4 §217(5,6,8) separate E96 live — 2026-10-29T03:24:10.772847+00:00
Started2026-10-29T03:22:49.748392+00:00, PID88993, allocationpostedffd3cc5e/source9aba59dd. CanonicalsharedFIFOclock+PAUSED_402.json joined, no parallelbankserialization; noindependentlatch. Firstresponse2026-10-29T03:22:55.943332+00:00, 38settled/0.05547125USD, openupper0 INSIDEunused50hold, notaddedtwice. ONLYseparate17920slot1records, originalindices/route4096unchanged/primaryneverrejudged. Exactterminaloncewatcher andautomaticpublication armed; source/testscommittedbeforecalls.
