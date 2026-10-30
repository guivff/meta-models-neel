# E28 training environment — 2026-10-25

Authority: Guiv's direct instructions, pre-authorized under §136. This dated
operational update adds a backward-capable overlay and the requested untrained
lens parity gate. The original PLAN, target mapping, input bank, fourteen runs,
six rows, training schedule, decision rules and total 18,000 GPU-second cap are
unchanged. E33 precedes launch; E37's conditional build is already committed.

Prior Integrator custody is1,363seconds (three terminated operational
attempts). New allocations are8,318.5seconds per pod, totalling16,637; together
they exhaust the unchanged18,000second experiment cap. See the frozen prior
accounting receipt, which includes exact ledger commits and lines.

Use `environment_prepare_command` in the new launch request on each pod. It
creates a fresh local overlay over `/weights/venv-kernels`, adds only the pinned
Triton wheel, and freezes the inherited versions and package bytes. It must not
install into or upgrade the shared reference environment. Bind the resulting
manifest hash and separate parity input seal in that pod's assignment before
running the worker with the overlay interpreter. No key values are printed.

The new parity package is separate from the original sealed E28 worker input.
Its 252 gate-only labels are the sole exception to the previous test-label
boundary. Activations and both candidate pairs are byte-identical to the
original W1/E28 rows. Before any fresh adapter optimizer step, including the
timing pilot, the untrained merged RL lens must reproduce sealed W1 row AUROC
within ±0.03 for prose_sentiment, prose_paren and python_string. A parity failure
stops; no retry, threshold change or alternative environment may be selected
using those results.

Environment preparation alone does not certify CUDA backward. The worker
records readiness only after its first real backward/optimizer warm step,
which follows parity. This must succeed by Monday 26 October 12:00 CET
(11:00 UTC), otherwise E28 is NOT RUN for environment. Runtime receipts bind
environment, parity scores and parity verdict; final analysis verifies these
before opening the full private truth file.

Keep provider accounting from pod creation. Setup, kernel compilation, parity
and pilot steps consume the existing allocation; the full-grid warmed forecast
still decides admission and cannot shrink the registered scope. Integrator
alone publishes, launches, retrieves, terminates and consolidates shared logs.

The CPU tests exercise the actual training function and optimizer on a small
model, checking gradients, frozen weights and reset behavior. They establish
the training path's logic, not real-model CUDA compatibility or measured fit.
