# E130 §237 preoutput CPU adapter

Credit: Suraj's exp24 protocol, Jarus77/mats-nla-workspace commit
23d5a972993dd482b3cb8976584d76642b0db87b. Original source read as reference;
only project-owned code executes. No exp24 results read. No real E130 arrays,
readouts, labels, fits, guards, model or GPU opened during this preparation.

Exact source port: `LogReg`, `fit_logreg` and `group_folds` copied unchanged
from src/mats/probes.py. Float32, train mean/sample std clamped1e-4, BCE +
.001*sum(w²), unpenalized intercept, LBFGS lr1/200/history20/strong_wolfe.
Five grouped folds seed0, no C search/sign selection. Original E85
matched_set is the cluster: all four genre×addressed cells stay together;
50 DEV and100 TEST groups are split-disjoint. Canonical original CPU labels
SHA5ed311882f9b06f208776d1636567267570ed33bbf83b39d5da9732559975a44.

DEV200 true-span32 **rebuilds** only. For each addressed/genre factor, compute
held-out grouped-CV true-span positive control; then fit one all-DEV model,
write both models and FIT_SEAL before TEST_ONCE and any TEST array load.
This implements §237's separate DEV/TEST population: it does not pretend
exp24's original same-population held-out transfer is the same split.
Apply that frozen model to all400 intact Oracle readout rebuilds and all400
seed20261031 token-ID shuffled rebuilds. Native head coordinates tag44/li-ln;
no whitening, raw-activation reference, alignment or condition normalization.

Report separately a grouped5fold seed0 CV probe fitted on TEST intact
readout rebuilds alone. This is explicitly descriptive, after primary probe
freeze, and never changes transferred scores or criterion. Genre is a
separate descriptive control. Addressed=1 is the fixed cue-positive class.

All AUROCs get percentile95% item-bootstrap intervals:2000 draws,
seed20261031, fixed predictions, same item indices across conditions;
one-class draws counted undefined, no retry/stratification/refits. DEV OOF
control and TEST OOF descriptive intervals resample their saved predictions.
Draw count/bootstrap seed are frozen here before output (the §237 shuffle
seed is separately fixed by registration). Matched-set grouping controls CV;
bootstrap unit remains item as specified by §237, not a quartet bootstrap.

R-EC1: true-span addressed OOF AUROC<.80 => UNINFORMATIVE. Otherwise intact
AUROC>=.70, lower95%>.60 and intact−shuffle>=.10 => carried in readout
arrangement. Intact<=.60 => not carried under E130. Else inconclusive.
Only the .10 subtraction comparison has1e-12 arithmetic tolerance. Naming
0/176 is the sealed E85 premise, never recomputed here; no awareness/causal
access inference. E125 remains closed with its original failed gate.

## Final intake and execution — NOT ADMITTED by this preparation

`INPUT_PLAN_TEMPLATE.json` is deliberately not a real binding. After actual
complete capture, final plan pins original CPU labels, E130 INPUT_SEAL,
runner SOURCE_SEAL, actual Q admission, OUTPUT_SEAL and Q custody receipt.
Every pin is an absolute local path +SHA256. Canonical inputSHA01086c34… and
runnerSHA5edd2a12… are hardcoded. No raw labels/readouts in tracked plan.
Q custody must record VERIFIED_COMPLETE, operator Track Q, input/source/output
hashes, preoutput adapter original commit, adapter_preceded_first_output=true,
outputs_held_until_adapter=true. Original Q admission must carry that same
adapter commit and exact runner duties/cap/deadline admission. Q checks actual
creation/first-output chronology against the original committed source.
The final exact binder is committed AFTER delivery BEFORE CPU claim; preserve
that chronology in results, never claim it was complete before capture.

`run_once --plan ABS_FINAL_PLAN` refuses uncommitted plan/source or changed
source receipt, absent trigger/custody, NO_FIT/partial outputs, wrong labels,
missing/duplicate/mixed batches, invalid groups/order, changed shuffle,
nonfinite/non-fp32 vectors, and analysis afterFri30Oct17Z. It hashes batch
bytes at intake without scientifically opening arrays. Only DEV batches are
loaded before FIT_SEAL. Output must be a fresh local private CPU folder outside
tracked results. Canonical fresh E130 ONCE and TEST_ONCE live only under
wt-wlens/cache/g_agreement/understand/e130/analysis; never reset/retry/reuse
E125 guards. Failure after a claim stops for registered handling.

After the single admitted invocation, seal private weights/predictions and
aggregate RESULTS. Publish only aggregate RESULTS/ANALYSIS_SEAL plus a sanitized
publication receipt after checking no private path/label binding leaks; keep
raw final plan and predictions local. Notify R-4/Q/owners via HANDOFF for
independent review. No author rerun on reviewer arrival.

This adapter receipt is source readiness only: no execution permission, actual
capture, fitted probe, output seal or scientific result is asserted. Packet
must seal byFri08CET and C's E127/E128 duties be delivered; Q alone admits and
runs within original cap/deadlines. Otherwise NOT RUN operational/research
phase. No judging or W-lens model/GPU/GO.
