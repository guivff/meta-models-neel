# E95 concurrent judging scheduling (ba2c220a7)

Run the frozen stage2/3 packets alongside the existing stage1 continuation. No
executing stage1 source, pacing file, worker or guard is changed. This adapter
calls the existing judge_dispatch/admission, unchanged E87 rubric/wire and
validator221, and existing C backend248/e340 retry accounting. No selection,
parser or scientific analysis is added.

There are four inference workers total: stage1 two, stage2 one, stage3 one,
below C's standing five-bank concurrency. Rates are at most12/8/4 physical calls
per minute respectively. Lower stages take only immediately idle shared slots,
never enqueue ahead of stage1 or C, protect stage1's next send deadline, and pause
when E138R/E140 have actual open allocations. Stage3 yields to stage2. Stage3
backs off first on a new429 or stage1 slowdown; continued429/slowdown also pauses
stage2. Stage1's original rate and workers are untouched.

The declared original two-worker maximum remains in the original SPEC; new
operational SPECs transparently bind the one effective worker for each added
stage. Only their own processes override stage-local dispatch locking and the
now-authorized independent canonical once-guard claim. All monetary reservations
still use the single original e95_60usd ledger and USD60 lifetime cap. Unknown
physical sends are never replayed. No key/readout/label/private join is published.

Commit and verify BA2_SOURCE_SEAL and new SPEC/proofs before launching:
`python -m projects.g_agreement.e95.judge_parallel_ba2 --supervise`

The CPU supervisor never relaunches stage1 or any existing stage2/3 guard. It
hands each stage to W-lens/R-Q immediately upon its complete terminal seal, using
existing judge_delivery. Original marker and seal mtimes must both precede15Z;
any unfinished stage at15Z is NOT RUN/no analysis, including late terminal seals.
The unchanged physical POST guard also rejects sends at/after15Z. In-flight
responses may be retained diagnostically. Raw and private seals stay local.
