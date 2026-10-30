## §147 E41. Local cue or remote state, on a fresh bank (E31(i) protocol on E36's continuation scores)

**Registered 2026-10-26 01:30 CET, before any E36 score. CONFIRMATORY for E31(i)'s pattern.** **Owner:** W-text.
**Cost:** CPU only, after E36 seals.
- **Protocol:** E31(i)'s frozen protocol unchanged (`70ffb479` freeze: classifier recipe, median dev-margin cutoff,
  `include_read`, 2,000 item resamples), applied to E36's v2 items:
  - the classifier is trained on v2 dev items' last 4 tokens;
  - the cutoff is the median dev margin;
  - Oracle continuation AUROC (E36's E15-style channel) is computed per stratum on v2 test items, on E36's H4 rows.
- **Rule (fixed now):** a row is evaluable if each stratum has ≥ 10 items. **R:** the remote-state pattern (both strata
  ≥ 0.70) holds on a majority of evaluable rows, and the local-cue pattern (informative ≥ 0.75, uninformative ≤ 0.60)
  holds on none. NOT EVALUABLE if fewer than 2 rows are evaluable.
- **Prediction:** R holds.

**Clarification 1 (2026-10-26 01:50 CET, coordinator; after the dev-only freeze `0f568d7`, before any E36 test score).**
Six of seven frozen cutoffs are 0: on those rows the last four tokens give the classifier no signal on dev, so the
informative stratum will be empty and the rule would be NOT EVALUABLE by construction. The rule is therefore
extended, with classifiers and cutoffs unchanged:
- **Rows with both strata ≥ 10 items** are judged as registered.
- **Rows whose informative stratum has < 10 items, but ≥ 10 uninformative items:**
  - remote-state = uninformative AUROC ≥ 0.70, with CI lower bound > 0.50;
  - local-cue = uninformative AUROC ≤ 0.60.
- **R:** remote-state holds on a majority of rows judged under either criterion, and local-cue holds on none. NOT
  EVALUABLE if fewer than 3 rows are judged.

