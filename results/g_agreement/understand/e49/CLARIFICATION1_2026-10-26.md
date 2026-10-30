# §163 clarification 1 — 2026-10-26

Authority: user instruction and registration `c8216b2b`, before E49 scoring.

`rules49.py` retains strict blind pre-call accuracy as primary: every gated row enters; SAYABLE is correct at Oracle AUROC ≥ 0.80 and UNSAYABLE at ≤ 0.65. Values strictly between those thresholds count incorrect.

Alongside it, `precall_accuracy_middle_band_excluded` reports descriptive accuracy after removing only gated rows with 0.65 < Oracle AUROC < 0.80. Boundary values remain included. Both outputs list their denominators and row-level correctness; failed gates never enter either. An empty denominator reports null accuracy, not zero.

Synthetic CPU tests cover both thresholds, incorrect calls outside the middle band, failed gates and empty descriptive denominators. No data analysis, generator, candidate or blind-call seal changes.
