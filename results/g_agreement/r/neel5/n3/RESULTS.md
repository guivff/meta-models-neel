# N3 — cached prior subtraction

**Primary k-way verdict: NOT EVALUABLE.** No eligible parent has candidate-complete shuffled and mean-state controls. Gain and CI are unavailable; zero is not an estimate. No new model inference was performed.

Inventory: 22 requested parents, 20 after LABEL_DEFECT; 2650 eligible test items, 0 retained for the primary endpoint. The binary-child priors are different experiments and cannot supply the missing candidate vectors.

The complete k-way analyzer is built and CPU-mock-tested, including macro-parent/item effects, Platt, leave-parent-out, wrong-reader controls and optional reference truths. Current cached inputs cannot execute its scientific endpoint because candidate-complete priors are absent.

## R-C2 secondary analysis

Rates below are descriptive P(context); effects are paired corrected minus native, quoted with the wider base-item/category-clustered 95% CI. They cannot establish the missing k-way claim. The RC2 model truth follows the frozen per-paraphrase greedy selection; the original F1 non-complier definition is preserved.

| Reader/site | n non-compliers | Native context | Corrected context | Change, pp [95% CI] |
|---|---:|---:|---:|---|
| jlens L42 | 22 | 86.4% | 68.2% | -18.2 [-51.6, +0.0] |
| jlens L44 | 22 | 77.3% | 50.0% | -27.3 [-66.7, +25.0] |
| nla L42 | 22 | 13.6% | 59.1% | +45.5 [+10.0, +76.9] |
| olens L42 | 22 | 81.8% | 86.4% | +4.5 [-32.1, +75.0] |
| olens L44 | 22 | 59.1% | 77.3% | +18.2 [+0.0, +100.0] |
| skip_a L42 | 22 | 86.4% | 90.9% | +4.5 [+0.0, +27.3] |

## F1 verdict after subtracting priors

Original F1 thresholds are unchanged; both native and corrected below use the stronger paired/category inference registered for N3. The original published J42/44 H-name flags do not survive this wider inference even on native scores; that change is due to the uncertainty calculation and cannot be credited to debiasing.

| Reader/site | Native flags | Corrected flags |
|---|---|---|
| jlens L42 | undetermined | undetermined |
| jlens L44 | undetermined | undetermined |
| nla L42 | no verdict (existing shuffled gate) | no verdict (existing shuffled gate) |
| olens L42 | undetermined | undetermined |
| olens L44 | undetermined | undetermined |
| skip_a L42 | undetermined | undetermined |

## Limits and controls

- K-way effects require complete candidate priors and full registered population coverage. Missing reference predictions stay missing. The CPU mock exercises the complete analyzer; synthetic outcomes are never substituted for evidence.
- RC2 Platt and leave-category-out diagnostics use a deterministic pair-disjoint calibration/endpoint split. Their positive common candidate slope preserves corrected top-1 by construction.
- RC2 control rows are available for the full retained population; prior disagreement >2 nats is separated in effects.jsonl. J-lens uses cosine differences, so a 2-nat rule is undefined for it.
- Wrong-reader controls preserve original score units; cross-unit J-lens controls cannot establish specificity. Each effect records whether units match.
- RC2 contains only a small number of category clusters. Paraphrases are resampled together by pair_id. The quoted intervals include both base-item and category-clustered uncertainty.
- Existing RC2 probe output stores summary AUC, not matched item predictions. No probe truth was invented. Frozen model prompt-only/greedy truth is used where available.
- CPU wall time: 60.1 seconds. Pod-hours: 0; API cost: 0. All results are derived from existing cached scores.

Full row provenance, per-stratum effects, Wilson intervals, calibration diagnostics, input hashes and coverage are in adjacent JSON/JSONL files.
