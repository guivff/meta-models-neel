# 2026-10-25 — §119 clarification 1 implemented before scoring

Authority: Guiv's explicit confirmation in this chat and published BRIEF_UNDERSTAND
§119 dated clarification 1, commit `e4225a1e`.

**D is `AUROC(s_A − s_B, 1[value=A])`.** Each value's score averages its two
frozen W1 phrasing scores, each already a mean per-token log probability.
P remains the median over items of their true-value score.

The provisional truth-aligned D in `2137965` is removed from the registered
analysis. The previously separate fixed-A-minus-B diagnostic becomes the sole
registered D. Tests cover a fixed candidate preference producing0.5 and perfect
item-sensitive discrimination producing1.0. No polarity is selected from data.

No item, phrasing, tokenization, acquisition score, bootstrap rule, outcome
reference, prediction threshold, setup allowance or science cap changed. The
line-by-line audit's only substantive ambiguity is now resolved. All original
input/private-label/reference hashes remain unchanged. No actual Qwen score
has been collected, and no held analysis was run.

RUN_PLAN.json now acknowledges the published definition; the worker requires
the assignment to cite `clarification_commit: e4225a1e`. The analysis validates
the same definition and the score-bound plan. The new source archive has a
distinct filename; the original held archive remains in ignored cache. Current
source/plan/archive hashes are in LAUNCH_REQUEST.json.

The prior HOLD status and unresolved-D statements in the dated notes and review
describe the original request; this note supersedes them. The rebuilt request
is ready for the Integrator's publication, assignment and warmed forecast.
No owner push or pod operation is needed or performed.
