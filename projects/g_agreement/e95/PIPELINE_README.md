# E95 judging controller

The existing stage-1 spawn continuation is already running. This controller watches
its terminal marker, delivers its original normalized codes and provenance through
HANDOFF, then admits the frozen stage-2 and stage-3 packets in order.

```
python -m projects.g_agreement.e95.judge_pipeline --stage1-spec results/g_agreement/understand/blind_judge/e95_bank/stage1_spawn_continuation/SPEC.json
```

The controller has its own exclusive administrative lock. It never relaunches
stage 1 or resets a paid-stage guard. Later stages require the previous terminal
seal and an unused original stage guard. Already terminal stages can be delivered
idempotently; a partial or ambiguous paid stage requires attention, never automatic
request replay. The original four unknown stage-1 requests and their reservations
remain missing and held. All original guards, input packets and failed outputs stay
in their original namespaces.

Each later stage reuses the original packet, selection, index, audit, E87 rubric,
wire and validator221 parser with the committed fresh-process dispatcher. It gets
a distinct committed SPEC and fresh custody/accounting/route/funding evidence,
inside the same original E95 lifetime USD60 bank and global USD1000 envelope.
Accounting adds only E95's remaining open authorization when it is absent from the
current C snapshot. It never treats existing unknown holds as zero. Actual account
credit is recorded truthfully; the authorized lifetime maximum is not represented
as a claim of full prefunding. The existing per-request ledger and shared HTTP402
pause remain mandatory. No POST can occur at or after 15:00 UTC, including after
pacing and backoff. Two isolated workers, at most twelve E95 physical requests per
minute, share C's priority/402 state and yield to pending priority banks.

Delivery uses the exact existing E87 flat-code representation from funded_queue;
there is no reparse, new code, statistic or inference. A missing terminal remains
UNPARSEABLE. Code evidence, raw responses, labels and private joins remain in local
sealed delivery directories. Public receipts contain counts, costs and hashes.
Original corrected E87 codes and join custody are verified and bound as a distinct
reuse lineage, without replay or reselection. Any unbound original placebo target
lineage is explicit for the analyst; no target is manufactured by judging.

Every completed stage is handed immediately to W-lens (map_note5 source5348c18e8)
and R-Q. Git publication secret-scans and rebases before every push, never forces,
and preserves concurrent HANDOFF entries. The controller performs no scientific
analysis and consumes no analysis guard. At bank closure only unused authorization
is released; original unknown physical liabilities remain held.
