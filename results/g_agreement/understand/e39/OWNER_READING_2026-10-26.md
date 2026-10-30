# E39 owner implementation reading — 2026-10-26

Recorded before any E39 model score or optimizer step. Authority: §141
(a38044dd), clarification 1 (8cc9d46d), §139 operations and §136 standing orders.

- Use ROW_DEFINITIONS.json insertion order. The first two semantic rows are
  json_status and latex_role. Structure is all 16 state-like/count-like rows;
  positions means count-like and states means state-like, using that packet.
- Reuse E36's completed, sealed block-44 captures for both splits. The binder
  verifies bank/candidate/freeze lineage, full selected coverage, order, shapes,
  finite nonzero vectors and per-item length/padding/environment audit. No E39
  recapture or alternate bank is authorized. Missing captures block launch.
- Assign whole rows to slots round-robin; all L/B/S arms of each row stay on
  one pod. Default six pods gives three rows/nine runs per pod. All forecasts
  must fit before any production; no row/arm/checkpoint cuts on NO_FIT.
- The 600-second SSH/setup allowance is inside each provider allocation.
  Actual provider elapsed time governs admission, so setup is never deducted
  twice or treated as free. Retain E28's 2,400-second setup ceiling,
  min(1.5F+360,10800) science cap and 180-second retrieval reserve. Total custody
  stays at most54,000 GPU-seconds across at most6 pods.
- E28's Monday-noon environment deadline was specific to E28. E39 uses the
  existing programme cutoff and its per-pod hardstop; the overlay, parity
  population, ±0.03 tolerance and actual-CUDA-backward requirement are unchanged.
- E24's regex remains unchanged. Neither semantic row has a detector; retain
  all native free readouts and report naming not evaluable for those rows.
- Per-item audit records are observational metadata only. Training uses E28's
  exact target mask, padding, optimizer, adapter parametrisation and injection;
  asked and free execution use the same native calls and batching.

The censoring ambiguity was held and resolved by coordinator clarification1:
both missing L/B crossings become800; both censored contributes0; strictly more
than half of interpretable structure rows doubly censored makes R3′ not
evaluable. No unresolved rule choice is delegated to the launcher. The pooled
paired contrast is the mean of L-minus-B crossing steps; bootstrap resamples
paired rows, preserving the declared interpretable cohort. The explicit
minimum8 rule applies to R1′; R3′ retains its own stated censoring gate.
