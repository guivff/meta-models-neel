# E133 runner (§241)

Existing code, isolated configuration and orchestration only. `generation_batch`
uses E131's exact code object with MAX_NEW_TOKENS32 and honest32 output metadata;
`capture_batch` uses E109's exact natural_capture at36/44/48/52/56/60. No upstream
or steer hook is installed anywhere. Backend87.sweep supplies unchanged native
Oracle44/52/60 greedy128/k1. `patch_batch` uses E126 controls/forward
in INSERT mode: the same block's OTHER PAIR MEMBER residual replaces the own
read residual, plus original earlier-token and norm-matched-random controls.
Reciprocal swaps are separate cells. No U delta, rescale, refit or new random recipe.
One-hop patched44/52 only. All metrics/ratios/selection/probes/judging are CPU B's
or designated owners' work, not performed here.

## Packet and timing admission

W-text owns sealed source items and CPU-only labels, including the ordered contrast
roles. Public schema in INPUT_CONTRACT.md. If an owner packet differs, adapt by
explicit fields/source IDs with tested source-only wrapper, not regeneration.
`runner.load(root,sha,'screen')` checks900prompts/450completepairs; main load
checks up-to84/42completepairs plus frozen SCREEN_SELECTION_SEAL.json, exact IDs
and behaviour-only both-member rule. Below50multi-hop is descriptive only by B;
runner does not choose a subset or infer a verdict. Empty main packet means no job.

Track Q owns admission BEFORE content/model calls, original creation-clock hard
stop and max-setup/whole-need forecast. Screening cap360s(.1GPUh); main2880s(.8);
registered total.9GPUh and one evidence-bound§234measured reattempt only. Create
main before10Z, hardstop min(cap,12:50Z). E133 topGPU priority aboveE131; sharing a
physical pod does not reset clocks or combine once guards/caps. Require B's
committed/tested prospective adapter before affected outputs; labels stayCPU.
Do not use scientific outcomes for timing/cohort admission.

Fresh-extract actual runtime imports and source_gate BEFORE pod. With original
E79 runtime subject (pinnedQwen6a9e13bd/bfloat16/eval, zero sampling):

```
from projects.g_agreement.e101.runner109 import backend87
from projects.g_agreement.e133 import runner
runner.source_gate()
items=runner.load(INPUT,INPUT_SHA,'screen')
# Q constructs Backend87 with original verified assets, times load_base/warm-up
model,tok,cm=runtime.subject()
with cm:
    runner.screen(model,tok,items,FRESH_OUT,check_work,gpu_type=ACTUAL,batch=8)
```

`check_work(remaining_jobs,acquisition_elapsed,max_observed_job_seconds)` is the
EXISTING Q whole-need callback. Include staging/setup/warm-up/original elapsed,
global conservative pending-job timing×1.25 and reserve, fixed original deadline.
No clock/cap reset, refill or partial stitching. Outputs seal COMPLETE or NO_FIT;
returning COMPLETE doesn't authorize next stage or CPU outcome opening.

Q/CPU owner freezes first behaviour-correct pairs only; new main INPUT_SEAL plus
SCREEN_SELECTION_SEAL before ANY reader call. Then load verified main packet,
time original subject setup/warm-up and call:

```
runner.main_job(runtime,items,FRESH_OUT,check_work,gpu_type=ACTUAL,batch=8)
```

Main order capture+32token answers -> ALL reciprocal patch cells -> Oracle setup
-> three-layer reads, saves all native residual arrays/answer IDs/patch metrics and
literal reader outputs under one output seal. Oracle setup is recorded separately
from per-call throughput; its elapsed still counts against ORIGINAL Q deadline.
Forecast must account for unmeasured later phases conservatively; use production
warm-up/timing, not treating one32token batch as an Oracle128token rate.
No labels, reader-dependent selection, GPU classification, pair-bootstrap, probe
or analysis is performed by this runner. Q retains first-output/custody/actual GPU
and source/input lineage in its outer operational seal. Never duplicate a live job.

## Current strict public-input wrapper (v2 supersedes tokenized-input intake)

W-text's original public INPUT_SEAL ca4b738e binds ONLY items.json id/prompt,
archive e0459aef. Never stage PAIRS.PRIVATE or TOKENIZATION_CPU.PRIVATE.
Stage original items.json and its exact seal sidecar (no transformed public packet).
After original pinned tokenizer load, call public.load_public(root,sha,tok,
'synthetic','screen'). Tokenization exactly matches all900 sealed originalCPU
records. Pair groups derive from original fixed member0/member1 source order,
with an opaque hash of both public IDs; family from original300/150 counts.
No target roles are read. EVERY prompt receives ALL45 unordered contrasts over
the SAME public ten-name/place vocabulary, fixed order; per-item current/previous
and recipient roles are resolved only by B/Q onCPU using originalID-keyed maps.
These constant GPU pairs are never gold labels or selected from per-item prose.
B can derive any ordered contrast from the same-pass complete global logits.

For bAbI id/prompt-only root a7bd9438 call public.load_public(root,sha,tok,
'babi','screen'): ALL15 global contrasts over six locations, sameforALL988prompts.
Familybabi kept SEPARATE in output seals, never pooled; both-member reciprocal
patches atALL5blocks as multi-hop. Main public root must be frozen byQ after
behaviour-only selection (first42forbabi, first84/42synthetic); preserve original
IDs/prompts, CPU-only exactselected-source/candidate map, committed selection
source/screen COMPLETE seal before readers. For synthetic main pass multi_pairs
explicitly from the frozen COUNTmetadata; source order remains multi thenone.
Public main seal stage main, same two-field records; no CPU answer roles staged.
Babi main up-to84prompts; no extra synthetic84 requirement. Both pipelines reuse
original arithmetic and strict global-vocabulary/full-prefix single-token checks.
Use runner.source_gate plus public.load_public; old runner.load handles the
historical tokenized schema only. No silent private-field insertion.

Outputs include explicit constant candidate_ids beside raw pair_logits/logprobs.
The inherited E131 aggregate mean across ALL global contrasts is REMOVED, as it
is not an item answer preference. B selects the exact shared-recipient and
current/previous contrast by CPU-only originalID/role mappings; raw scores are
unchanged and no output values used to choose a contrast.

V2 patch scoring calls unchanged E126.forward ONCE per single-token batch, then
unchanged E131.pairs_from_logits on that very pass. This preserves requested
pair logits/logprobs and hook metrics without redundant same-prefix continuation
forwards for each global contrast. No multi-token continuation is truncated.

## CURRENT v3 — §241/§242 clarifications1–2, supersedes v2 staging

Production entry is runner.load(adapted_root,sha,'screen'), NOT public.load_public.
Source-only bind_screen has already compiled W-text's exact900 id/prompt source
and bAbI's exact988 prompts into items.json+MANIFEST.json. Both recipients per
pair are sorted ascending numeric tokenID, identically on both members; no
current/previous role or previous-holder candidate is sent. Pair structure on
pod is explicitly allowed by75cf9b82d. ROLES.PRIVATE and its seal remainCPU for
TrackQ both-member32token classification/first84/42(fewerifqualify)selection.
No regeneration/target-based token truncation/role inference.

Main capture ALSO saves raw SAME FIRST GENERATION PASS full-vocabulary logits
as fp32.npy, indexed by originalID. This lets B read the previous-holder logit
onCPU without putting any previous-holder ID or orientation on the pod. No
additional model forward/score computation and no softmax/correctness assignment
on this file. Patch raw ascending-recipient pair scores unchanged.

ONE pod, screen -> pull answers -> CPU freeze -> push kept roster -> main on SAME
pod/model. Total primary cap3240s FROMCREATION;4320s ONLY when the bAbI adapted
packet was sealed BEFOREcreation; otherwise3240andbAbINOTRUN. Hardstop min(cap,
12:50Z), createby10Z. Old360/2880separate-stage examples are historical planning
components, NEVER fresh clocks/deadlines. Keep ORIGINAL Q whole-need callback
across both Writer stages and CPU roundtrip; stage elapsed argument isdiagnostic
only and does not reset podclock. No Cpod/stager/selection/onceguard.

CREATION HOLD: B's patch-summary fix committed AND R-Q synthetic case returns0.5
both on r/blindspot BEFOREanycreate. This readiness delivery is NOT GO. B's
single analysis additionally waits W-lens's committed E134 SELECTION_SEAL before
opening E133outputs; Q can pull SCREEN answers for authorized selection only.
R summary/probe arithmetic belongs B/RQ, not this runner.
