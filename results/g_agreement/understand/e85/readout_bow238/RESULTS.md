# E85 readout-word classifier — pending source

**NOT EVALUABLE: missing 200 DEV native Oracle readouts.** The original sealed release contains the 400 TEST texts, but its DEV items were activation captures, not reader-generation inputs. E130's DEV source spans are a different input.

The CPU pipeline and synthetic tests are ready. No real model has been fit, TEST AUROC computed, or once-only lock consumed. Addressed AUROC, genre AUROC and top real fitted words are therefore unavailable. Neither the ≥0.80 carriage reading nor the ≤0.60 bottleneck reading applies.

A sealed original DEV-native packet is required to execute the registered split; no TEST split change, generated replacement or inferred metric is used.
