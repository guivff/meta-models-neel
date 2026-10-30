# E135 runner and packet (§244, 026eea061 deviation1)

I-2 is the sole pod operator, after E131's pod. Track Q remains on E131/E133.
No pod/model/API/reader/judging call is made by this CPU packet builder.

Same 84 original E104 fact_recall TEST items, original composed alpha8 steered
and random deltas, scaled by 6/8 only. No direction fitting, redraw, seed
change, norm matching, source-answer selection, or historical-dose acquisition.
The original E104 U hook is imported unchanged: block40, eight positions before
ORIGINAL read token, never the read token. All three greedy steps use the same
original positions; same-first-forward pair logits/logprobs retain original order.
Generation is E128's unchanged three-token helper (including early EOS). This is
not E131's 64-token text validation; the historical three-token measurement issue
is not repaired or imputed here. Pair-logit preference is the §238 deviation1
measure and is interpreted only by the CPU owner.

168 cells = 84 items × dose6 × steered/random. Capture layers44/52, yielding
336 Oracle readouts, 168 in each condition. Oracle runtime, native activation
scaling, greedy128/k1 and source-layer binding remain E128's E109/E87 path.

## I-2 integration

Fresh extract source archive and verify SOURCE_SEAL.json plus every member before
any pod, then import the ACTUAL runtime (Torch/PEFT/Transformers, E79/E109/E87,
E104 hook, E127 generation and E135). Run the supplied tests and load actual inputs
on CPU. Public archive contains INPUT_SEAL, MANIFEST, SCORER, items and deltas only.
CPU ORIGINAL_POINTERS.PRIVATE/POINTER_SEAL are never staged.

Use the E128 operator envelope, changing only experiment, input/source seals,
dose/census metadata and the calibration field persistence:

```python
from projects.g_agreement.e135 import inputs, runner
items, deltas, manifest = inputs.load(public_root, input_sha)
for job in runner.batches(items, size=8):
    # within original Runtime.subject context and operator clock callback
    result = runner.capture_answer_batch(model, tok, job,
        deltas[[x['delta_index'] for x in job]].copy())
    # Persist answers, read_norms, injection_metrics AND calibration with job IDs.
    # Persist captures at44/52 and literal id/layer/member/vector-index inventory.
```

Unload subject after acquisition; run E128's unchanged Oracle sweeps on each
captured layer. Keep actual GPU type and original source/input/assets bindings.
No standalone production entrypoint is supplied; I-2 owns assignment verification,
exclusive once/custody guards, creation clock, pilot forecast, stop/seal and cost.

Original creation cap 2,880s/.8GPUh, created by2026-10-30T10:00Z, hard stop
min(original creation+2880,2026-10-30T12:50Z). Whole need uses maximum measured
setup and all pending-phase batches ×1.25+60 reserve; no clock reset or inferred
retry from packet delivery. Outputs sealed unopened until W-mech2's prospective
adapter is committed/tested. R-Q reviewer, R-3 if late. Judging belongs exclusively
to W-internals-C, bankE135≤USD1, afterE107b/beforeE95, hardlastcall15Z/16CET.
If judging cannot finish, report GPU pair/calibration part under §244 disposition;
no runner analysis or extra calls.

## Calibration contract (raw, no additional model forwards)

The unchanged U hook already observes pre-edit block40 residuals at eight write
positions in its first forward. `calibration` adds per-cell id/base/dose/condition,
positions, eight `natural_site_l2` values, actual `composed_delta_l2` and
`unscaled_d_l2 = composed_delta_l2 / 6`. These are 84 matched item records
per condition (each retains all eight original site norms). These
values are before the edit in that same forward, not downstream/read-token norms,
not the concatenated eight-site norm. `reference_delta_l2` at2/4/6/8 is ONLY
scalar arithmetic from the current composed delta norm. No historical model call.
All original injection metrics are preserved as an independent raw source.

W-mech2 computes one denominator: median individual site L2 over84×8 original
unsteered positions (one matched84-item cohort, not repeated across conditions). Compare pre-edit norms across repeated cells rather than counting
repeats as independent items. Numerator is ||alpha*d|| for the original composed
direction, reported per dose. No C median, ratio statistic, classifier, readout
opening or analysis guard execution occurs. Calibration, preference, fixed42
cohort and registered descriptive patterns are W-mech2/R-Q responsibilities.

CPU input build: `python -m projects.g_agreement.e135.build --out NEW_DIRECTORY`.
Existing sealed output directories must never be overwritten.

Deviation1 supersedes the earlier three-dose resource hold. Earlier source/input
archives stay immutable and unused; receipts are retained under
understand/e135/history_pre_deviation1. Only the new dev1 archive is production.
At size8, source-bound jobs are22 capture batches and42 native batches. The
original E128 MAX timings imply a conservative reference whole-need below2880s
before additional staging. This reference is NOT actual pod admission; I-2 must
include actual staging/setup and preserve the original cap/clock. No warm-up
maximum is discarded. See RESOURCE_RECONCILIATION_DEV1.json.
