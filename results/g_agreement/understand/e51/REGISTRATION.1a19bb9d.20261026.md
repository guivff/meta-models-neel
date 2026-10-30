## §167 E51. Did the warm-start teacher ever say it? (distillation-target audit; CPU)

**Registered 2026-10-26 14:30 CET. DESCRIPTIVE with one rule; conditional on data access.** **Owner:** W-sae
(free), with the integrator locating the data. **Cost:** CPU; anonymous read-only access; download only the target
text files, never weights.
- **Data:** the distillation targets of `ao.iolens.ptag.s3d.omp4bp.s2` (14,773 training rows per its `run.json`),
  if present in `agu18dec/local-workspace` or named in its README. If not findable anonymously within two hours,
  E51 is reported NOT AVAILABLE and Agam may be asked for a pointer.
- **Measure:** per 10⁴ target bullets, the rate of bullets naming (a) a structural state (a frozen lexicon: bracket,
  parenthesis, quote, string, indent, nesting, depth, cell, column, row, header, list item, environment, section),
  (b) a content property (topic, sentiment, language, error, status, register), (c) passage position (sentence,
  paragraph, question). Lexicons frozen and committed before counting.
- **Rule (R1):** structural-state naming < 1 per 10⁴ bullets while content naming ≥ 100 per 10⁴. **Prediction:** R1
  holds, which would locate the origin of the policy gap in what the teacher said.

