# E42 forecast-only correction — 2026-10-26

User authorizes one integrator relaunch after the cold-batch timing NO_FIT. Only the extrapolation changes: skip times[0], and once a second production batch finishes use the maximum of the last three warmed production batches. Before then, the unchanged absolute timer/deadline still applies; actual cold-batch time remains fully charged. No repeated warming, new generation policy, state function, bank, analysis rule, cap or deadline change.

Forced pins refreshed: worker hash in RUN_PLAN, plan hash in LAUNCH_REQUEST, CODE_SEAL, staging archive and READY code-seal reference. The original archive remains in cache. Three forecast boundary tests plus the previous 12 CPU tests pass. No GPU launched or sealed following text replaced by W-text. Integrator retains the failed attempt custody and executes the explicitly authorized relaunch once; this note is not authorization for further retries.
