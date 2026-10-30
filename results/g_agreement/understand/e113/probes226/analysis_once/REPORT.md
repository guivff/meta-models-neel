# E113 §226 Oracle-internal probes

Each row × 64 decoder-block outputs × 2 positions has a separate dev-fit probe; all 768 test AUROCs evaluated once after every dev fit was frozen. Original84dev/84test per row, class1 unchanged. Fivefold dev-only C selection and fold-local scaling; no test sign inversion or selected-layer-only reporting.

R-IN1: MET. Falsifier: NOT MET.

| Row | Maximum across full test grid (registered threshold summary) |
|---|---:|
| nesting_depth | 1.000000 |
| indent_level | 1.000000 |
| page_range_digit | 1.000000 |
| fact_recall | 1.000000 |
| format_plan | 0.996032 |
| language_plan | 1.000000 |

All per-layer/position cells are in RESULTS.json and AUROC_BY_LAYER.md. Maxima are the registered any-layer rule summary, not dev-selected layer estimates. Finite complete cells required; no missing imputation.

Chronology: original kernel/recipe fc5573e04 preceded capture; the exact layout binder/final source/input plan were written after capture and committed before the exclusive CPU claim. Complete final-adapter pre-capture custody is not claimed. Runner capture source/position trace: injectedslot24 in native prefill; actual first greedy token appendedslot56 from full forward, including EOS. Arrays are block outputs0..63; no subject-layer44 substitution.

No judging, model forward, original bank replay or new GPU allocation by W-lens. Runner custody cost is owned/booked by W-mechanism-C; not rebooked here. Independent R-Q review requested after seal.
