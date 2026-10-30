# E37 operational readings — 2026-10-25, before any E37 model call

Authority: §134 and its dated clarification 1, commit d4bb903d; direct Guiv
clarification that R4 pools structure rows per arm. No registered threshold,
row, measure, checkpoint, or decision rule changes.

The checkpoint deadline governs arrival, not the eventual launch. An original
step251 checkpoint received by Tuesday 27 October 20:00 CET may run later, after
E33 and E28, provided the entire run fits before the programme stop. Missing or
late weights close E37 as NOT RUN. Checkpoint identity and all received file
hashes are frozen in the Integrator receipt before any model call.

“E33 and E28 come first” is queue priority. Completion or an explicit terminal
Integrator closure with no active pods satisfies it. In particular, Guiv's
Monday noon environment deadline can close E28 as NOT RUN; that closure must
not permanently block the registered conditional E37 comparison.

The runtime necessarily receives the labels of exactly the 252 items in the
three registered parity rows to evaluate the AUROC gate. The remaining private
test key stays off the worker. This is limited to the registered gate, which
cannot change the frozen scoring code or select a new population.

The smoke selection is SHA256 of UTF-8 `20261025|<id>`, ascending hash then ID,
first 20 among all 2,100 test items. It is frozen before model calls and without
labels or scores. Both frozen C1 pair scores and their mean must be finite and
repeat within 1e-4. RL reproduction uses each full 84-item row's AUROC.

C1 and C1′ retain their candidate strings' bullets; C2 retains E15's explicit
`- ` prefix; C4 retains E24's native greedy generation. Both arms use the same
convention within each channel. Timing-only C4 pilots force the full 128-token
decode cost; their outputs are discarded. Scientific C4 uses normal EOS and
the original 128-token maximum.

No new items are authored for E37. The E36 definition-only packet is verified
at its supplied hash; no extraction from w1_templates.py is used here.
