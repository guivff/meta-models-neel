# Authoritative packed launch: E3 then E4

The user's packing instruction supersedes the separate-process launch route in
`INTERNALS.md`. Scientific populations, prompts, gradients, analysis, seeds and
native batch sizes are unchanged. **Post one request: `E3_E4_PACK`.** Do not run
the older `pod_run.sh` per-experiment scripts for this assignment.

One Python process loads Oracle, NLA and J tensors exactly once onto CPU. Both
27B models stay in host memory between uses. Only one occupies GPU memory at a
time; moving weights between CPU and GPU is not a checkpoint reload. The target
uses the already loaded Oracle model with its adapter disabled. Request one GPU
with at least 80 GiB, at least 160 GiB available host RAM and 40 GiB free output
space. If those resources are unavailable, report it; do not silently reload
models, shrink batches or substitute a different reader.

Initial input/asset verification, three model/tensor loads and first GPU transfer
share **one 1,500 s setup allowance**. Run the sequence:

1. Start E3's own science clock immediately before its first warm-up. Calibrate
   Oracle, NLA, J (one discarded warm-up and three timed units each); admit the
   aggregate warmed forecast; collect those readers; seal `PACK_OUT/e3`.
2. Only after E3 is sealed, start E4's separate clock. Calibrate Oracle, NLA, J,
   target, including all 40 target rows for E9 in the forecast. Apply E4's own
   gate; collect; seal `PACK_OUT/e4`.

For **each experiment**, the elapsed clock is continuous from its own start,
including warm-ups, timed units, CPU/GPU weight transfers, production, disk I/O
and sealing. It never restarts after calibration or between readers. The
experiment's cap is `min(1.5F + 360, 2160)` seconds. F includes median timed units
times the full unit count plus a conservative remaining-transfer forecast from
the maximum observed activation-transfer time. Gate admission requires elapsed
science plus the entire remaining forecast to fit. No time is borrowed from
the other experiment. A hard-cap alarm, checkpoint checks, persistent clock
ledger and the integrator's external hard stop enforce these rules.

A failed/no-go experiment makes no further model calls. Its partial artifacts
are sealed with CPU I/O and reported, and that post-stop latency remains in the
packing ledger for provider-custody accounting. Once the partial seal exists,
the next experiment may start its own independent clock. There is no retry of
the stopped experiment. An unhandled interruption preserves the active ledger
and output files; the integrator reconciles and retrieves rather than restarting
this one-shot process. E9 unsupported second derivatives remain an explicit E4
calibration failure, never an approximate replacement.

From the committed repository on the assigned pod:

```bash
/weights/venv/bin/python -m projects.g_agreement.understand.packed \
  --inputs STAGED_INPUT_PARENT --out NEW_PACK_OUT \
  --assets PINNED_LOCAL_ASSETS_JSON --assignment INTEGRATOR_ASSIGNMENT_JSON
```

Use the committed `PACKED_LAUNCH_REQUEST.json` assignment schema. Stage only the
`e3`, `e4`, `e9` child directories of the frozen input package; labels stay local.
Each child output has its own `SCORE_SEAL.json` and provenance, independent of
the shared `PACK_REPORT.json` and clock ledger. After pull, the existing
`understand.analyse` CLI processes `PACK_OUT/e3` and `PACK_OUT/e4` separately.
Every row is reported, including missing phases, in the existing result grid.

## Setup repair, 24 October 2026

The integrator-reported attempt on `ui5s406kr88dtg` failed during setup after
754 seconds of loading: the J-lens unembedding loader rejected a Hugging Face
snapshot shard symlink into that same repository's `blobs` directory. The loader
now allows that standard cache layout, while preserving asset-content hashes
and rejecting paths outside the same pinned cache repository. This is a setup
repair; the inputs, scoring, timing gates and caps are unchanged.

The fresh request explicitly uses **`/weights/venv`**, through the absolute
interpreter `/weights/venv/bin/python`. E4 requires second derivatives; do not
substitute another environment. Its target calibration still verifies actual
kernel support before production. Keep the failed attempt's accounting and
the original launch receipt as historical evidence; launch into a new output
directory with a fresh integrator assignment.

### Shared blob-store repair, 24 October 2026

A second integrator-reported setup failure (no science; pod ID and elapsed time
not supplied) revealed hub-wide `blobs/<xx>/<sha256>` symlinks. External shard
symlinks may now resolve to any regular file under `/weights` whose content
SHA-256 matches its entry in the pinned asset manifest. The loader does not trust
blob filenames. Missing hashes, changed contents, non-files, and final targets
outside `/weights` remain rejected; existing local and same-repository layouts
retain full upstream asset verification. CPU fixtures cover both indexed and
unindexed shared stores, arbitrary names, and invalid targets. Use the V3 receipt,
`/weights/venv/bin/python`, a fresh allocation/assignment and new output directory.
Scientific inputs, separate warmed gates, caps, and sealing are unchanged.

## E4-only OOM retry (§91 amendment `4af1004b`)

The `cybhnezi82omzz` run sealed E3, then E4 exhausted GPU memory after 23.7 s.
The coordinator authorizes one E4-only retry, preserving all items and scope.
Use `--e4-only` with an `E4_ONLY_RETRY` assignment and sequence `["E4"]`.
Only the `e4` and `e9` frozen inputs are staged; no E3 capture or analysis is
performed by this worker. Models load once in `/weights/venv` and the target
continues to alias the Oracle base model.

The operational memory policy changes reader batches from 16 activations to 1
(two candidate sequences) and target JVP batches from 8 items to 1. Saved
autograd activations are offloaded to pinned CPU memory; frozen weight storage
and its views stay resident, avoiding needless full-model copies every backward.
The score algebra, item order, directions, full-vocabulary exact second derivatives,
and all 25 reader / 40 target rows are unchanged. Host memory requirement is
192 GiB. CPU tests cover numerical parity and exact target JVPs; actual GPU
memory use and kernel compatibility must pass the real warmed calibration.

Setup remains 1,500 s. E4 uses one continuous first-science-step clock and its
own one-warm-up/three-timed-unit gate, including offload/transfer overhead,
with cap `min(1.5F + 360, 2160)` seconds. No reduced population or fallback is
allowed if the forecast does not fit. Use a fresh assignment and output folder,
retain prior costs, and pull the sealed `PACK_OUT/e4` outputs. No further retry
is authorized by this receipt.

E3 pull loss is handled only by `analyse --allow-e3-missing-arrays`: existing
files must still match both seals, and the only tolerated missing paths are
`olens/table_row.residuals.npy`, `olens/table_status.residuals.npy`, and
`olens/table_status.input_stage.npy`. Available stages are retained; affected
cells are MISSING with no imputation. The original capture seals are unchanged.
