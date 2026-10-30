# E35 fallback training choices — 2026-10-25, before fallback training

These fixed choices apply only to the registered conditional fallback after the
transfer gate's scientific FAIL. No training run, real activation loading,
hyperparameter search, validation selection, or GPU call produced this note.

- Architecture: 5,120 raw residual coordinates, 16,384 latents, positive TopK
  with k=64. Encoder `TopK(ReLU(x @ W_enc.T + b_enc),64)`; reconstruction
  `z @ W_dec.T + b_dec`. External input normalization is identity, with fp32
  arithmetic and no AR whitening, per-token normalization, or input-scale fit.
- Initialization: CPU Gaussian decoder columns, local RNG seed 20261025,
  normalized individually to unit L2 norm. Initialize encoder to decoder
  transpose. The first training minibatch alone sets initial `b_dec=mean(x)`
  and `b_enc=-W_enc@mean(x)`. This is an affine-parameter initialization;
  inference still supplies raw x and never subtracts b_dec externally.
- Data: the separately frozen §79/FineWeb source order and exclusions; exactly
  20,000,000 unique token occurrences, once. No replay, epochs, or selection
  among checkpoints. Batch size 4,096, with an unpadded final batch of 3,328;
  4,883 optimizer updates. Initialization uses the first batch, then that same
  batch gets its sole ordinary update. Source identity and true document/token
  uniqueness are enforced by the collector. The trainer additionally rejects
  skipped, repeated, or held-out stream offsets before numerical training.
- Optimization: fp32 Adam, constant learning rate 0.0003, betas (0.9,0.999),
  epsilon 1e-8, zero weight decay, no schedule or EMA, global gradient norm
  clipped to 1. Decoder gradients have their column-radial component removed;
  every optimizer update is followed by decoder-column unit normalization.
- Main objective: mean squared reconstruction error divided by the first
  training batch's centered mean square. That positive finite scalar is fixed
  once; it changes loss units only, not the input transform. Degenerate or
  nonfinite initialization stops training. No held-out statistic is used.
- Dead-feature auxiliary objective: after each main forward pass, a feature
  counts as recently fired if its positive main code occurs in that batch.
  Its timestamp is the batch's final stream offset. A feature is dead for AuxK
  at >=1,000,000 positions since that timestamp (never-fired timestamp=0).
  Select up to 512 positive activations among dead features only, decode them
  without b_dec, and reconstruct the detached main residual. Add its MSE,
  divided by the same fixed initial training energy, with weight 1/32.
  Auxiliary activations never reset the main-firing timestamp. With no dead
  features the auxiliary term is zero. No feature resampling/reinitialization.
- Timing admission uses a separately discarded scratch SAE. Its three timed
  optimizer updates explicitly force every feature into the auxiliary candidate
  mask, so the benchmark includes the full 512-feature AuxK compute and memory
  path even before the production dead window would elapse. This flag requires
  `synthetic=True`, prevents checkpoint/manifest export, and is never enabled
  on the fresh production trainer. It does not change production dead criteria.
- Determinism: seeded CPU initialization, deterministic Torch operations,
  no TF32/autocast for the SAE, and CUDA `CUBLAS_WORKSPACE_CONFIG=:4096:8`
  established before CUDA initialization. Hardware/library versions are
  recorded by the collector; cross-hardware bit identity is not asserted.
- Final output: only the post-update checkpoint after all 20M positions, with
  exactly W_enc, W_dec, b_enc, b_dec (CPU fp32), plus actual training statistics
  and the separately pin-able identity-normalization manifest. No incomplete
  checkpoint is eligible for the unchanged held-out gate. The collector binds
  checkpoint/source/normalization digests and applies the existing GPU ceiling.

AuxK follows the dead-feature residual-reconstruction approach in OpenAI's
[reference trainer](https://github.com/openai/sparse_autoencoder/blob/main/sparse_autoencoder/train.py)
and its [loss implementation](https://github.com/openai/sparse_autoencoder/blob/main/sparse_autoencoder/kernels.py),
read 2026-10-25. This implementation deliberately differs in its 1M-token dead
window, positive-firing threshold (>0), fixed initialization-energy scaling for
both objectives, arithmetic-mean bias initialization, fp32 dense operations,
and affine raw-input parameterization. The reference uses a 10M-token default,
>1e-3 firing, and current residual variance for its auxiliary loss. These
choices are fixed now; they are not adjusted after fallback results.
