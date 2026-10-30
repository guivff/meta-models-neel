# W-core standing orders — 2026-10-25

Authority: BRIEF_UNDERSTAND §136 at e29dc767, read from the committed source. Effective until Guiv’s next message; recheck subsequent instructions before acting.

- Before scores, resolve ambiguities that do not touch a decision rule, threshold, row or measure by the reading most faithful to registration; record OWNER_READING_<date>.md in that experiment’s folder. Scientific ambiguities: hold, record the question, move to the next item.
- Timing-only NO_FIT/NO_GO with no science: one rebuilt request is permitted. Integrator applies the smaller of twice the registered cap or 1.5F + 360 seconds, with cumulative run time no greater than twice its §130/§133 cap. Carry failed-pod charges; do not edit live assignments.
- Pre-science operational failure: one reviewed fix-and-retry; integrator books the failed pod and relaunches. Scientific parity/validity failure: stop, no retry under this order.
- Each registered analysis runs once. Secret-scan before every local commit; integrator owns pushing and launches. Add a short HANDOFF line after each step.
- Integrator enforces USD 400 new-spend guard, 12-pod ceiling, 3-minute deployment spacing and final Wednesday deadline. This file does not allocate funds or grant a new attempt on its own.

## Queue audit

E24: corrected attempt-2 request already committed at 3c5e5dae, source 91a859e1, reviewed capture fix 92578aa4 under explicit §133 authorization. Full §130 scope, four supported shards, each forecast, 12 GPU-h cumulative including 1.45 GPU-h attempt 1 and 717.5014989376068 seconds diagnostic. No new attempt-2 score seal or failure receipt found locally. The old parity-failed attempt is not a §136 operational retry. Do not rebuild speculatively or run analysis without a complete sealed acquisition.

E32: corrected request committed at 3c5e5dae, same source/fix; 0.5 GPU-h total. No acquisition receipt or score seal found locally. Await integrator custody evidence; no speculative rebuild or analysis.

W12/E29: next scheduled authoring is Sunday evening, approximately 19:00 Europe/Zurich. Existing task updated with §136; its service reports enabled but no next-run timestamp, so execution is not verified. No local W12 freeze exists. Preserve Camila check and §100 design. §136 removes waiting for a new coordinator prediction ruling: W-text must write and seal the fixed mechanical predictions after sealed D/P, and W-core verifies all bindings before issuing reader request. Missing freeze/D/P/prediction seals keep scoring held.

E17/E20 and earlier completed analyses stay closed; no reruns. W10b scientific estimability failure stays closed. E28/E33 belong to W-lens.

Synchronization: pull/rebase attempted with unrelated logs stashed; GitHub DNS failure prevented synchronization. Stash restored; exact §136 read via connected GitHub. Integrator must reconcile local commits before publication. No push, launch, inference or registered analysis in this update.
