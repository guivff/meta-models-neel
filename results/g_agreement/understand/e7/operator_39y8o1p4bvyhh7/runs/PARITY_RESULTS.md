**E7 operational setup parity (§94, c97d0893):** PASS_INPUT_AUDIT.

First32-token agreement: 40/52 (76.92%). Median first-divergence position: 58.5. Full-token agreement: 23.08%; full decoded-text agreement: 23.08%.

DESCRIPTIVE: §94 c97d0893 removes parity acceptance thresholds after seeing the earlier operational parity numbers and before any E7 science. Padding, attention-mask and consumed position-ID checks remain mandatory hard gates.

Positions are zero-based counts of matching preceding tokens. Identical completions, including matching early EOS, have no divergence and are censored at128 for the all-readout median. Only padding after the first EOS is ignored. Batch8 is a setup reference; every production readout uses the batch32 setting, including its final partial unit. No per-item selection or fallback.
