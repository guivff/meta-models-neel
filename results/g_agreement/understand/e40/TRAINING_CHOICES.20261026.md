# E40 training choices — 2026-10-26, before E40 GPU work

Authority: §142 at a38044dd and clarification1 at53f1add2. The registered
architecture is65,536 latents,k128,AuxK coefficient1/32,k_aux512,Adam lr2e-4,
seed20261026. The design was chosen after E35 failures, as the registration
states. The CPU diagnostic does not tune it.

All unspecified training choices retain E35's fixed recipe: batch4096,
Adam betas(.9,.999),epsilon1e-8,zero weight decay,constant learning rate,
gradient norm clip1,decoder-column unit projection and projected decoder
gradients. Decoder columns start as seeded Gaussian unit vectors, encoder as
their transpose. Initial affine biases use only the first eligible scaled
training batch. Main and auxiliary MSE use its centered energy as a fixed loss
unit; this does not alter inputs or refit the registered global scale.
Dead-feature aging uses1M eligible training positions since positive main
firing,never-fired timestamp0. The auxiliary residual is detached,has no decoder
bias,and auxiliary firing never resets the main timestamp. No feature
resampling,epochs,replay,EMA,checkpoint selection or heldout tuning.

Calibration is exactly clarification1. The first1M original-document-position
nonzero training occurrences are captured once in manifest/FineWeb order.
Their raw fp32 activations occupy a bounded20.48GB host-RAM buffer. Compute
float64 L2 norms,median m,strict outlier cutoff10m,retained mean norm,and
scale=sqrt(5120)/mean,in that order. CALIBRATION.json and its seal precede any
optimizer step. Outlier calibration occurrences are excluded; eligible buffered
occurrences train first,then the paused source iterator resumes. No training
occurrence is captured again. There is no training activation corpus on disk.

Exclude targets at original document position0 and targets with raw norm>10m.
Those tokens remain in the model's context. Chunking does not renumber document
positions for exclusions. Training reaches100M distinct eligible occurrences,
including eligible calibration occurrences,then stops. All exclusion counts and
the at-most-one-chunk unused eligible tail are recorded. Fixed batches require
24,415 updates:24,414 full4096 batches and one256-token batch.

The input to the SAE is raw h times the sealed scalar. Its raw reconstruction
is the affine scaled-space decoder divided by the same scalar. Raw decoder
columns for §131 norm shares are W_dec/scale; b_dec is excluded. This transform
is applied after forming raw difference vectors in decomposition.

The target model is fixed Qwen3.6-27B at its E35 revision,and capture calls the
same block44 full-forward function. There is no target-model backward pass.
All compute is oneGPU,on onepod. Source files are staged and hash-checked before
rental. The 28.52GB pinned FineWeb parquet set is streamed locally in row order,
with bounded token/document buffers; only the required prefix is consumed.

Hardware admission requires>=120GBGPU memory,>=60GBfree after target loading,
and>=48GBhost RAM available before the20.48GB calibration buffer. This admits
H200/B200-sized devices; an80GBdevice fails the stated memory check. Preserve
the established E35 forward kernel stack. Record runtime versions and per-chunk
length,padding0,original offset and environment reference in a cache ledger.

Science timing begins before a synthetic warmup and calibration. Actual full
chunk timings and complete calibration elapsed time include tokenization,
filtering,transfer and source overhead. After sealing calibration,three
scratch-only optimizer timings force the active AuxK path;three256-token
reconstruction/moment timings price the gate. Scratch state is nonexportable
and discarded; retained training starts from fresh seeded parameters. Forecast
remaining capture from the observed eligible-per-chunk rate and price all
24,415 optimizer steps and the full50000-token gate. If the full run does not
fit,stop NO_FIT without reducing tokens or changing the gate.

The science cap is min(1.5F+360,absolute provider deadline minus180s retrieval
reserve minus first science time),with a nonresetting clock and a tightened
hard alarm. F+180s sealing must fit. Total E40 provider custody is<=50,400s;
setup is at most1500s. Book actual provider stop/retrieval time and carry the
remaining budget to follow-up. Scientific gate failure stops E40; no third
SAE attempt. Validity failures are not eligible for a scientific retry.

The final gate reuses byte-verified E35 h on exactly its original50000 tokens,
so target recapture/parity substitutions are unnecessary. Exclusions use only
sealed calibration constants and original positions. FVU and dead fraction on
the retained population decide PASS; all-token FVU is descriptive beside it.
