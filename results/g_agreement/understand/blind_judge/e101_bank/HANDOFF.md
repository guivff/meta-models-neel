# E101 two-cell E56 judging bank — shared USD5

User authorization: add the two-cell E101 test bank now, cap USD5. fact_recall test2 output90e25ffa25e6ec69dafe991f2fcd7bb8e6607cdbceae5b20165fb2df3c2d648f is COMPLETE. language_plan test2 subsequently arrived COMPLETE at4e3cf7ba03f341576b402d8edd18df519a2c2bbd2d71722dab2e40a00e385fde, so the full bank is ready. Original test/NO_FIT directories are excluded.

The bank contains336 blind records:84 test items × steered/random for fact_recall:44 and language_plan:44, alpha4. Exact committed dev doses, COMPLETE test2 seals, original input seals and original CPU target95fd23d3177439e8ded1128276eb25911419d6331a362a02a524d015e07981f4 are verified. Every scheduled logits/Oracle job and output ID matches its sealed grid. The bank carries readouts only; behaviour logits and target labels remain CPU-side. No scientific score, cohort exclusion, baseline regeneration or verdict is computed. R-F1/R-F2 remain NOT EVALUABLE per §212; test results are descriptive.

Uses existing wmech2.core.export for blind opaque IDs/property/both values, exact adapter402 rendering, E56 payload/model/provider/ZDR/data-deny/no-fallback policy, original E10 reserve/settle ledger and original bounded validation retries. USD5 is shared across both rows in cache/g_agreement/understand/funded_queue/E101/ledger. Initial84 four-record calls have conservative upperUSD1.1180521875; zero privacy redactions. Terminal UNPARSEABLE remains missing. CPU PRIVATE.json is ignored and never staged.

```sh
python -m projects.g_agreement.understand.blind_judge.e101_judging prepare
python -m projects.g_agreement.understand.blind_judge.e101_judging run
```

No credentials enter arguments, files or logs. E101 shares the funded queue's persistent PAUSED_402.json latch: any402 from E101 stops it and prevents E87/E100 further sends at their next boundary; a pause from E87 stops E101 at its next boundary too. Already in-flight requests may settle. A later resume requires explicit funding/reconciliation; no guessed zero settlement or automatic credit retry.

Integrator paths after preparation (relative to wt-internals-b):
- cache/g_agreement/understand/funded_queue/E101/blind/BLIND_SEAL.json
- cache/g_agreement/understand/funded_queue/E101/PRIVATE.json (CPU only)
- cache/g_agreement/understand/funded_queue/E101/judgments/JUDGMENT_SEAL.json (written only after runtime route/privacy verification and terminal full grid)
- cache/g_agreement/understand/funded_queue/E101/STATUS.json and judgments/LIVE_PROGRESS.json

E100 already exists in funded_queue.py with all6720 a/b records, capUSD30, queued behind E87's grouped judging. This E101 addition leaves those live request identities and source seals intact. Five focused tests cover exact two-cell84×2 scopes and shared402/no-next-bank behavior. Runtime receipts establish paid execution and actual cost.
