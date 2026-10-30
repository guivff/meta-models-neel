# E130 conditional runner (§237, 3c0519155)

Credit: Suraj's exp24 protocol, Jarus77/mats-nla-workspace at
23d5a972993dd482b3cb8976584d76642b0db87b. The source was read as reference.
Only project-owned modules execute. The reconstructor arithmetic is ported
unchanged; its capture import points to the local copied decoder helper.
`protocol.py` ports lib24's readout-token cap/empty fallback and token shuffler.
No code is executed from Suraj's checkout. No calibration or E125 coordinate
admission test is used. No raw activation, whitener or label is needed on the pod.

Packet:200 E85 DEV original last32-token spans and400 original sealed Oracle TEST
readouts. Runtime reconstructs DEV span32, intact TEST readouts and shuffled TEST
readouts:1000 rows, tag44, li/ln, batch16. Same seeded shuffle stream20261031 in
sealed TEST order; only the registered readout shuffle is drawn, no extra NLA or
bag-of-span conditions. Readouts are tokenized without special tokens, capped256;
empty becomes `(empty)`. Reconstruction is in the native head output coordinates
without a post-transform. DEV labels/groups and all test labels stay with W-lens
on CPU. W-lens owns grouped5fold probes, DEV freeze before TEST scoring, all
positive controls/bootstrap/criteria; this runner fits/scores no probes.

**Conditional only.** E127/E128 runner deliveries must be complete and this packet
sealed by Fri30Oct08:00CET. `prepare` checks the exact operator admission and a
committed/tested W-lens adapter receipt BEFORE parsing readout content. A packet
seal is not model execution or a scientific result. Track Q alone owns the
launch, canonical once guard, live timing/admission, original setup/cap/custody,
GPU type, shutdown and billing. No workload displacement is authorized.
Creation by Fri11:00CET; stopped/sealed14:00CET, hardstop min(cap,12:50Z).
Planning1800s/.5GPUh; one evidence-bound §234 measured attempt if applicable.

The sole operator calls:

1. `prepare(input_root,input_sha,admission,now)` (source/input/conditional gate).
2. `resolve_snapshot` for pinned base6a9e13bd and ARc95215d5, explicit local paths.
3. `load_model(base,ar,device)`; no online fallback.
4. `acquire(model,dev,test,fresh_out,check_work,gpu_type=actual_gpu_type)`.

`check_work(remaining_batches,elapsed_reconstruction,max_observed_batch_seconds)`
is the EXISTING operator whole-need forecast/deadline callback, retaining original
staging/setup/warmup time and measured timing rules. It is not a clock reset.
The standalone CLI is validate-only; unguarded production is explicitly disabled.
Returns COMPLETE or NO_FIT and seals exact arrays/token roster/index/timing.
Prior partials never stitch. There are NO reader generations or judging calls.

E129's separate mechanical trigger is in `gates.e129_trigger`, consuming only a
verified sealed E127 analysis by Fri08:00CET. No E129 model selection, new fact
packet, outcome classification or launch occurs in this E130 port.
