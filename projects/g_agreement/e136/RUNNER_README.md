# E136 (§247/74b25641d)

I-2 owns the pod, after E135. No intervention/steer/patch is installed. The runner
uses E109's original natural_capture code object with only its isolated CAPTURE
list set to44/52/60. Block44 is saved for W-mech2's probe; all three unmodified
raw vectors supply E109/E87 Oracle reads, nativegreedy128/k1. No reader changes.

The original W-text sealed bank is outputs/e136-bank-v2,800prompts/400pairs. New
outputs/e136-inputs-v1/inputs.tar.gz is BYTE-IDENTICAL to its PUBLIC_INPUTS archive;
no C facts, cues, prompts, labels, splits, candidate pairs or tokenization are
created. All800 original chat renders/tokenIDs and leading-space single-token
pairs were checked on CPU against original private messages and pinned tokenizer
6a9e13bd before packaging. Public fields are ONLY id,ids,read_index,candidate_ids.
Cue/task/template/group/pair/split/truth/sign/originalmessages remain CPU-only at
the original bank's cpu_only root and MUST NOT be staged or committed.

## Registered behaviour option

§247 allows frozen-pair preference OR classified32-token text. Since all original
pairs are single-token, this runner uses the PAIR-LOGIT option. A read-only
model-output observer saves original pair logits/logprobs from the SAME unhooked
E109 capture forward using the unchanged E127/E131 pairs_from_logits helper.
It returns None and never alters a model output. Exactly ONE model forward per
capture batch, no extra generation/behaviour pass; no text classifier or rollout.
The only other observers are E109's original residual capture observers. No
intervention hook, delta, normalization, dose, probe or answer-based selection.
Both scalar candidates stay in original ascending anonymous token-ID order;
correct-value direction is interpreted only by the CPU analysis owner.

## I-2 operator integration

Fresh-extract/verify SOURCE_SEAL plus every member, actual full E79/Runtime/E87/
E109/E136/Torch/PEFT/Transformers imports and real bank load before pod. CLI:

```
python -m projects.g_agreement.e136.runner --input PUBLIC_ROOT --input-sha SHA --validate-only
```

Standalone production is disabled. Import the tested functions into the original
I-2 creation-clock worker envelope:

```python
from projects.g_agreement.e136 import runner
items, manifest = runner.load(root, input_sha)
for job in runner.batches(items, size=8):
    # within Runtime.subject context and I-2's original timed callback
    result = runner.capture_batch(model, job)
    # Save raw captures at44/52/60, raw pair_records/read_norms and ORIGINAL IDs.
```

There are116 homogeneous-length capture batches at size8. Persist captures as
unmodified5120 vectors, with literal id/layer/member/vector-index pointers; retain
block44 for probe use. After unloading subject and loading original Oracle, use
`runner.oracle_batch(runtime, vectors, layer)` on100batches/layer at size8 (300
nativebatches/2400readouts). This delegates to the literal original
Backend87.sweep implementation. Do not normalize, reduce, patch, reorder by
labels or include private grouping metadata on pod. Runtime and actual GPU type,
assets, original source/input/assignment/guard/first-output chronology and exact
readout inventory are I-2's custody. Raw pair_records are NOT judged readouts.

Originalcap3600s/1GPUh FROMcreation, hardstopmin(cap,2026-10-30T12:50Z), podcreatedby
10Z/11CET. Packet kill cutoff06Z/07CET; if bank not sealed by then OR create missed,
NOTRUN and NO partial reporting. Source-ready is NOT measured timing/admission.
I-2 must forecast original elapsed creation/staging/setup/waits plus MAX measured
all pending phases ×1.25+60 reserve, not an average or a scientific-outcome-based
admission. No retry/cap increase/clock reset or additional attempt inferred here.
C runs no model/timing/pod/reader/judge/analysis/guard/cost operations.

## Scientific custody

W-mech2 exclusively owns block44 cue probe and pair-preference analysis. W-text
exclusively owns grouped-base-task carried-words fitting (vocabulary train-fold
only). Preserve original20DEV/80TESTpairs percue and original task/template groups
on CPU; no C split or labels on pod. R-2 independent review. Prospective tested
committed owner adapters and exclusive once guards must precede their opening.
W-internals-C ONLY judges2400native readouts in bankE136≤USD2, afterE133b/beforeE95,
lastpaidcall15Z/16CET/privacyroute/no fallback unchanged. Outputs sealed unopened.
R-SW1/probe gate/falsifier/missingness are owners' rules, not runner decisions.
Breadth across PROMPT-STATED cues only; no private-state, causal or repair claim.
