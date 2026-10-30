Source: BRIEF_UNDERSTAND.md at 86073324.

**Dated note, 2026-10-25 11:00 CET (coordinator), E24 attempt 1 INCOMPLETE, before any E24 score.** Slot 0's
layer-44 parity gate failed: the minimum cosine against W1's sealed `reference44.npy` over 4,704 items was 0.514
(threshold 0.999 on every item). No capture was sealed, no score exists, and 1.45 GPU-h were used. Only the minimum
was logged. Candidate causes, in order of prior:
- (i) item order or id misalignment between the fresh capture and the reference;
- (ii) batching or padding: 11 layers, batch 8, right-padded, on the hybrid linear-attention kernels;
- (iii) environment (`venv-kernels` vs W1's reference venv).

**E24-D, diagnostic (authorised now; operations only; owner W-core; one H100/H200; cap 1,800 s, setup 1,500 s;
≤ 0.6 GPU-h).**
- **Items:** 300 seeded (20261025) W1 items spread across all rows.
- **Capture layer 44 four ways:**
  - (a) W1's original capture code and batch layout on W1's environment;
  - (b) E24's worker as built (batch 8, 11 layers, venv-kernels);
  - (c) E24's worker at batch 1;
  - (d) E24's worker on W1's environment.
- **Save per item:** id, row, token count, padding length, batch position, and cosine to `reference44.npy` at the
  index the worker *believes* matches. Also save the best-matching reference index for any item below 0.999.
- **Cause rules:**
  - (a) ≥ 0.999 and (b) not, with mismatches having a best match at a different index: **(i) alignment.**
  - (c) passes where (b) fails: **(ii) batching.**
  - (d) passes where (b) fails: **(iii) environment.**
  - (a) fails: the reference itself is the problem. Stop and report.
- **Attempt 2 of E24 is authorised once,** only after E24-D names the cause and the fix is a code change limited to
  that cause (alignment, batch size or padding handling, or environment), reviewed as a diff. Everything else is
  unchanged: gate, rows, rules, layers, priority order, and the 12 GPU-h total, with attempt 1's 1.45 counted. If
  E24-D is inconclusive, E24 closes INCOMPLETE.

