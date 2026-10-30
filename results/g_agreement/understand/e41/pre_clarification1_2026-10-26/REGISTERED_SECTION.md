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

