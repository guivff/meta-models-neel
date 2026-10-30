**E7 operational setup parity (§94, c1a03bfc):** NO_FIT.

First32-token agreement: 43/52 (82.69%); required ≥90%. Median first-divergence position: 77.0; required ≥32. Full-token agreement: 26.92%; full decoded-text agreement: 26.92%.

Positions are zero-based counts of matching preceding tokens. Identical completions, including matching early EOS, have no divergence and are censored at128 for the all-readout median. Only padding after the first EOS is ignored. Batch8 is a setup reference; every production readout uses the batch32 setting, including its final partial unit. No per-item selection or fallback.
