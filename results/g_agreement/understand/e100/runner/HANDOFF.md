# W-mech2 → Claude Integrator: E100 runner

CPU-ready, exact archives verified. Track Q owns allocations and launches. Latest
§208 authority69f8c08e4 withdraws c/d; Guiv explicitly confirmed preserving withdrawal
in this chat. Only transplant and four swaps are runnable. The original requested
injection/upstream arithmetic helpers and tiny-model tests remain as preparation
history, inaccessible from the E100 production grid. No E101 runner work is included.

Two whole-row shards: reported4200 readouts (5×84×5 conditions×2 readers), missed2520
(3×84×5×2), total6720. One greedy readout/cell; no baselines or duplicate E79 injections.
Conditions: transplant, J_swap, perp_J_swap, R_swap, perp_R_swap. Oracle receives
patched cached block44 vectors. NLA receives patched block42 vectors using the same
block44 basis, exploratory. At the read layer, direct vector replacement is the
original E79 reader-input intervention; no redundant subject-model forward follows it.
Float64 projector arithmetic precedes the finalfloat32 reader input. Transplants and
swaps have no dose scaling. Each output records norm ratio, >1.5 flag (no exclusion),
actual read/basis blocks, and GPU type. HARDWARE.json records actual device name;
assignment binds the same GPU type for every condition of each whole row.

Source from E79 runner8e431cca is hash-pinned. Its native_one and Clock are reused
unchanged; unrelated changes to operational files are disclosed in RECIPE_AUDIT.json,
and the actual asset and Oracle loader functions are AST-identical. Oracle generation
remains greedy128 tokens; NLA remains greedy512 with original explanation stop/extraction.

## Stage and admit

SOURCE_ARCHIVE.json gives the code archive and hash. The vector owner's publication
c7f7e53a is bound in DELIVERY.json. Its vectors/HANDOFF_REQUEST.json gives two basis
archives and one data archive per group: extract BOTH bases plus exactly ONE group
into a fresh inputs tree. Stage only those public files; never cpu_only, labels, probe
parameters, source keys or the parent's private vector seal. Each archive is under20MiB.
EXACT_PREFLIGHT.json verifies the actual extracted source imports and both extracted
input seals; no model loaded. Use the shard COMMAND.json and fill its assignment template
with actual pod identity, creation clock, asset hash, verified spend/cap and GPU type.
The template is intentionally not launch-authorized. B200 additionally requires the
same-image3-item smoke receipt and unchanged decoding/finite output checks (§204).

Historical timing proxy: **reported3.982 GPU-h; missed2.795 GPU-h; total6.777 GPU-h**,
including25% timing margin, two loads per reader for retained pilot admission, discarded
warmups,600s staging allowance/shard and180s sealing reserve/shard. No B200 speedup is
assumed. This exceeds the original approximate4GPU-h estimate: Integrator must reconcile
its authorized allocation before launch; no budget increase is inferred here. Exact
source hashes, phase means and allowances are in FORECAST.json. E79 measured Oracle
batch8 mean11.281s; E70 NLA mean19.792s. Batch4 is conservatively charged the batch8 proxy.

On the pod, synthetic warmups are discarded and charged to the creation clock. One
real retained pilot for each reader×batch-size cell precedes admission, then the full
remaining run is checked with1.25×mean timings, including pending reloads. Pilots keep
their original job IDs and are never replayed. NO_FIT seals partial custody and stops;
no scope cut or automatic retry. The absolute provider-creation deadline includes
setup/staging, and all output seals must precede Thu29Oct12:00CET. Full scientific
R-PC/R-C3 gating belongs to the committed analysis, not the acquisition loop.

Eleven synthetic tests pass: projector/complement identity, no scaling, exact6720
inventory, native42/44 distinction, one output/cell, retained pilot accounting, no-fit
stopping, actual GPU assignment binding, tiny-model upstream propagation and hook cleanup
for the withdrawn prototype. No GPU, provider, judge or real scientific-analysis calls.
