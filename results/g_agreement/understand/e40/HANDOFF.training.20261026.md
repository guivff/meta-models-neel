# E40 training handoff — 2026-10-26

E40(a) is complete. DIAGNOSTIC_RESULTS_SEAL.20261026.json binds the full CPU
position/norm-decile/domain tables. Both global dead counts reproduce exactly;
FVU differences are below1.3e-9. The initial pre-metric path failure and one
operational rerun remain recorded. The diagnostic changes no E40 design.

LAUNCH_REQUEST.training.json is the single E40 SAE request. Publication,
asset staging and the Integrator assignment precede execution. W-sae has
launched no GPU and run no E40 training or heldout gate.

1. Scan and publish the committed source. Stage every source_file byte at its
   pinned repository-relative path. Preserve the established E35 target forward
   runtime: s79/RUNTIME_PINS.json is pinned and the worker checks the relevant
   Torch/Transformers/FLA/Triton/tokenizer/numpy versions. Install/import pyarrow
   before allocation. This run needs no target-model backward or E28 overlay.
2. Run the request's CPU source-staging command before GPU rental. It copies the
   exact original §79 corpus/manifest/tokenizer and stages all14FineWeb parquet
   files from E35's revision87f09149ef4734204d70ed1d046ddc9ca3f2b8f9. Their
   LFS hashes/sizes are in FINEWEB_FILES.20261026.json (28,518,193,415bytes).
   The worker streams only the needed prefix in file/row order. Supply the
   resulting SOURCES.json SHA256 in the assignment. Token source copies from
   E35's training-tokens cache are valid locators; their original hashes are
   independently enforced. Source and activation artifacts remain in cache.
3. Stage E35's original heldout h.npy plus its original OUTPUT_SEAL.json and
   GATE_RESULT.json at the request's heldout paths. Exact hashes are pinned;
   this preserves the same50000raw vectors/token positions without target
   recapture. The E40 gate uses the registered exclusions and also reports
   all-token FVU.
4. Fill assignment.training.template.json under cache. Bind the pushed source
   commit, request SHA, SOURCES SHA, exactpodID, provider-created time, setup and
   absolute deadlines, prior E40 usage, external hardstop and hold evidence.
   Total E40 custody is<=50400GPU-seconds, oneGPU/onepod; setup<=1500s and
   retrieval reserve180s. Actual custody includes every setup/calibration/pilot/
   training/gate/sealing/retrieval interval. Carry actual remaining budget to
   followup. An allocation ceiling is not a claimed runtime or fit.
5. Select H200/B200-sized hardware: the worker requires>=120GBtotalGPU memory,
   >=60GBfree after loading the target, and>=48GBhost RAM available. Request
   >=96GBhost RAM. The20.48GB calibration buffer stays in host RAM; no training
   activation corpus is written to disk. Use §139's global20pod ceiling,
   180-second spacing and the Integrator deploy lock. Run the exact command.

Calibration is mandatory before update1. The source iterator first yields all
§79 training documents in manifest order, then FineWeb. Original document
position0 is excluded before counting the first1M calibration tokens. Compute
m,10m,retained mean norm and scale=sqrt(5120)/mean in the clarified order.
CALIBRATION.json and CALIBRATION_SEAL.json are written before any scratch or
retained optimizer update. The eligible buffered calibration activations train
first; the paused iterator then resumes, with no second capture pass. The same
constants govern all later training and gate exclusions.

Training is fresh TopK65536/k128,AuxK1/32,k_aux512,Adam2e-4,seed20261026,
exactly100M unique eligible occurrences once. Other settings are explicitly
frozen in TRAINING_CHOICES.20261026.md. Original position0 and strict norm>10m
are excluded as SAE targets; context token sequences are retained. Batches are
4096 with a final256-token batch,24415updates. No checkpoint selection.

After calibration the worker admits the whole scope from observed capture/I/O
rate, three full4096scratch updates with activeAuxK cost, and three256-token
reconstruction/moment timings. Scratch weights cannot be exported and are
replaced by fresh seeded parameters. The clock never resets; F+180sealing must
fit min(1.5F+360,absolute deadline-180-firstscience), enforced by a tightened
hard alarm. NO_FIT does not reduce tokens, exclusions or thresholds.

The single final gate checks retained-token pooled centered FVU<=0.25 and dead
fraction<10%. All50000-token FVU is beside it and enters no extra rule. Return
OUTPUT_SEAL.json and every sealed artifact, including CALIBRATION.json/seal,
TRAINING_RESULT.json, GATE_RESULT.json, runtime/pilot/clock receipts, capture
ledger and layer44.e40.sae.pt. Verify/book actual provider stop and retrieval.
FAIL means no adequate SAE; stop, with no third scientific attempt. Validity
failure stops. Operational stops preserve the once-only guard and require the
existing registered operations procedure; this request never launches itself
again.

On PASS, followup.verify_pass validates the new gate/checkpoint/calibration
before the unchanged §131 workflow. The frozen rubric and judge prompt remain
E35's; E40 scaling is applied once to raw h/e_w/e_p, and decoder norms use
W_dec/scale. Follow FOLLOWUP_CONTRACT.20261026.md. There is no additional W1
outlier exclusion or revised R1/R2 rule. Return the receipt to W-sae for the
next bounded labelling/decomposition request.
