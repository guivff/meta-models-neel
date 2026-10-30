# E123 dual-value sensitivity — non-executing reporting companion

Required by §233 E123 clarification 1 item 2 (`3ba3c0c6d`). This companion transcribes **R-2’s independently computed and verified sensitivity numbers**. It does not invoke the author adapter, analysis, bootstrap, guard, or a model/judge call. The original sealed output remains unchanged.

The primary stale definition is exclusive old at block 44. The sensitivity also counts block-44 readouts stating **both old and new** as stale. All reader-disagreement, missingness and decision rules remain unchanged. **The registered verdict is read on the primary definition.**

| Row | Primary stale cases | Primary AUROC [95% CI] | Primary R-DIS1 | Including-dual stale cases | Sensitivity AUROC [95% CI] | Sensitivity R-DIS1 |
|---|---:|---|---|---:|---|---|
| fact_recall | 47 | 0.886904762 [0.845238095, 0.928571429] | NOT MET | 47 | 0.886904762 [0.845238095, 0.928571429] | NOT MET |
| language_plan | 22 | 0.556818182 [0.443490536, 0.674464286] | NOT MET | 25 | 0.595000000 [0.483419540, 0.713695339] | NOT MET |

Both verdicts are unchanged. Unhooked false-positive counts remain 19/84 for fact recall and 8/32 for language plan, exceeding the registered 0.15 cap. Language-plan sensitivity’s observed AUROC remains at most 0.60. This is a sensitivity report, not a replacement confirmatory definition.

Dual-value readouts are a separate category:

| Row | Steered 44 / 52 | Random 44 / 52 | Unhooked 44 / 52 | Total |
|---|---|---|---|---:|
| fact_recall | 0 / 0 | 0 / 0 | 0 / 0 | 0 |
| language_plan | 3 / 3 | 3 / 0 | 1 / 1 | 11 |

The three language-plan steered/block-44 dual-value readouts add three parseable stale positives. Counts across cells count readouts, not distinct source items. UNPARSEABLE remains missing; no reparse, repair, missing-as-zero or complete-case filtering is introduced.

R-2 computed the sensitivity intervals with the same 2,000 paired item draws, seed 20261028. The original primary CIs are **conditional on defined draws (2,000 of 2,000)** in both rows. Clarification 1’s minimum 1,900-defined condition is therefore satisfied in this run. The original implementation does not enforce that guard in `disposition`; that latent omission does not alter these sealed verdicts. No new intervals were computed for this companion.

Source: R-2’s “E123 — one reader across two layers” review and `R2-E123-DUAL-REPORT238-20261030`; exact Git revision and report digest are in REPORT.json. Original analysis seal: `0c4fd523773e273dfb4d0f8214cbe294cb931623b36005286504d3073f28b9a2`. The original RESULTS, POST_HOC_EXPLORATORY_NOTE1, publication/analysis seals, and consumed guard are preserved byte-for-byte. This adjacent companion has its own reporting seal.
