# W-mech2 → Integrator: E100 analysis source

For the main Claude chat **Integrator**, worktree phase-r-integration-8abda6.
R-Q is the independent reviewer, not the execution destination.

Prepared on CPU without opening E100 readouts. Source:
`projects/g_agreement/e100_analysis/`. Source and tests are delivered in the publication commit; production refuses
uncommitted or changed source. This is not a receipt claiming analysis occurred.

Scope follows user-confirmed withdrawal: active R-PC, R-C3 and H-C3b only;
original R-C4/R-D1/H-T/H-U are implemented and tested but emitted WITHDRAWN in
production. All 84 sealed items per row, both shards, no scope reduction.

Execution requires the sealed donor-family CPU target bundle and the eventual
two COMPLETE output seals; instructions and exact configuration contract are
in the source README. W-internals owns the blind E56 judging route. The adapter
exports its established wire packet and requires the signed route/privacy
receipt before claiming the fixed once-only guard. It never calls a judge.

The historical E79 seal from commit 23ed827a is used only to copy saved estimates
into the joined figure, with E79's R-C1 null first. No old experiment is rerun.
Production status: NOT RUN. No E100 figure or inference result exists yet.

CPU target bundle has been built from verified frozen metadata only:
`results/g_agreement/understand/e100/analysis/cpu_only/TARGET_SEAL.json`
SHA256 `f1c97d6800972346241385ee2e18e02ffc12c01767827d6e44d26da7cace2e35`.
All 672 donor targets are present; E57 uses each donor source family's original
judge_values, E56/E59 use unique sealed per-label values. TARGETS.json is mode
0600, directory0700. Do not stage this directory onto a GPU pod.

E79 seal SHA256 is
`eb8367a52f0a8d5577aed2c48ed74dd29260e3172e6fe66dd12815d48bc6e2d9`;
its RESULTS.json SHA256 is
`b490cb5c13face96e3987207b1f7e945dab34c2affd241e1768c50b84b8a03e4`.
Both were verified using only seal metadata against commit23ed827a; no E79
result body or E100 output was opened to prepare this adapter.


## E100 Oracle transplant descriptive category census — 2026-10-30

Direct user request / §217: seven requested rows, 84 each, counted from original sealed E100 codes only. Tested source b33fdda51 (publication equivalent 58794c14d), 11 synthetic cases PASS, committed before code opening. Original analysis seal 76b156f055567cb168b2cfd40ec6bcc65aa21d2aa18fd1d97d533ad5fa86d2d1 and its pinned judgment/blind/target/private join custody verified. Exact 6720-code/private census; requested Oracle transplant row memberships and target orientations verified; all seven category totals equal 84 and signed-count identities match saved S. No judging, semantic recoding, bootstrap, production entrypoint, original guard or verdict change.

Table: results/g_agreement/understand/e100/analysis_once/descriptive_categories/REPORT.md; machine counts COUNTS.json, descriptive seal 588769fdd0ebaf0ade02b3f02ff263bbb79fd003ae82c8acb8451723b57d4202. Nesting and indentation predominantly silent (64/84,78/84); page-range has 56/84 silent plus cancellation of 10 correct-only and 10 wrong-only, and 7 both. Content rows retained exactly as requested; language_continuation outside scope. Post hoc descriptive only.

R-Q: please independently review the original sealed code categories, donor-target orientation, seven exact 84-item grids, count table and saved-S identities. Review pending; retain original result/verdict unchanged. No new owner analysis or guard replay. Private joins remain CPU-local under the original E100 once_bound SPEC; no private payload exported.


## W-mech2 E100 descriptive review closure — 2026-10-30

USE §217: acknowledged independent R-Q review 6fa6f2e8b7f846b2692efbfe74a989e5313a01fa. All 49 category counts, seven exact 84-item grids, seven saved-S identities, 588 donor-oriented joins and 27 hash checks matched. Descriptive seal 588769fdd0ebaf0ade02b3f02ff263bbb79fd003ae82c8acb8451723b57d4202 and original E100 outputs remain immutable. Review COMPLETE; no census, original analysis, bootstrap, judging or guard replay. Original judged categories and human-validation caveats remain; review does not independently certify first-opening history. Nesting/indentation predominantly silent; page-range combines silence with cancelling correct/wrong statements and both-value reports. No remaining E100 descriptive review wait.
