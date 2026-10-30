# E28 environment rebuild — 2026-10-25, before production scores

Authority: Guiv's direct instructions and §136. One operational rebuild is
authorized; a scientific parity failure stops without retry. The registered
arms, rows, measures, thresholds, training schedule and 5 GPU-hour cap stay
unchanged. Every registered analysis runs once.

The request for Triton ≥3.4 is a lower bound. The previous worker's installed
FLA explicitly rejects versions ≥3.4.0 and <3.7.1 on Hopper for this backward
kernel. Therefore the isolated overlay pins Triton3.7.1 with official wheel
hashes. Torch, PEFT, Transformers, FLA and causal_conv1d remain inherited from
the actual /weights/venv-kernels environment, frozen by exact versions and byte
hashes before forwards. No optimizer implementation or hyperparameter changes.

Environment readiness means a real finite CUDA backward/optimizer pilot step
has succeeded by Monday26October12:00CET, following the requested untrained
RL-lens parity gate. A prepared overlay or CPU test cannot establish that
readiness. The parity gate uses precisely the three full W1 test rows and
sealed reference AUROCs, without tuning an environment to its outcome.

The Integrator's immutable custody ledger books 1,363 seconds across three
earlier operational attempts (875.2+251.0+236.8), including retrieval and stop.
The new two-pod allocations are 8,318.5 seconds each: prior1,363 plus new16,637
equals18,000. Setup, parity, compilation, warmup, waiting, collection and
retrieval all remain inside those allocations. Worker-exit time is not full
provider custody. Any additional failed deployment must be booked and the
request re-pinned before another launch; this rebuild does not authorize an
unbooked retry or a larger experiment budget.
