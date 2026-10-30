# §112 post-hoc authority

Source: guivff/activation-readers@97cfc5dd, projects/g_agreement/BRIEF_UNDERSTAND.md. Read-only excerpt; original channel numbering is clarified in POSTHOC_CHANNEL_UNITS.md.

**Dated note, 2026-10-25 10:05 CET (coordinator), after reading E20's once-only analysis (W-core `7eae4a7d`, analysis
of pod `jm1vm4gw487fhn`, score seal `5327e4ce…`).**
- **Verdicts stand:** prose_paren DID NOT HOLD, python_string DID NOT HOLD, fact_once DID NOT HOLD, sentiment CONTROL
  FAIL. Channel 4 (asked) is uninterpretable per the registered rule; channel 3 stands.
- **Why, descriptively.** The structural manipulation did not move the model's own expectation: base Qwen's preference
  for the close dropped 0.07 (paren) and 0.006 (string) from near to far, against the ≥ 0.30 the design assumed. An
  open bracket stays expected at every distance, so there was no horizon to follow. On the two content rows the
  *source* state decays with distance (probe 1.00 → 0.59 fact, 1.00 → 0.68 sentiment), so "same state, different
  horizon" was not achieved there either. E20 therefore does not test the horizon hypothesis; it is reported as not
  held, with these failures named.
- **One discrepancy to check (post-hoc, descriptive, CPU only).** The lens's consequence and generation channels sit at
  chance on paren and string at *every* distance, including 2–4 tokens before the close (consequence_true 0.55 / 0.50,
  generation 0.51 / 0.48), whereas E15 found 0.71 (paren) and 0.92 (string) with its pairs on W1's items. W-core
  reports, without re-running anything: the exact unit each channel scores, how it differs from E15's pair scoring,
  and the lens's E15-style pair score on E20's distance-2 items if the sealed scores allow it. If they don't, this is a
  proposed run, not a claim.
