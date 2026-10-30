## §101 E13. What the readers actually say at structure tokens (free text)

Registered 2026-10-24 04:15 CEST. W1's free-response collection is partial and no blinded reading of it exists, so we
can't yet say whether the Oracle lens ever *mentions* structure.

**Owners:** W-core for (a) code, the integrator runs it; the lens chat for (b). **Cap:** (a) min(1.5F + 360, 2,400) s,
at most 0.8 GPU-h; (b) ≤ $5 API, 0 GPU-h.

**Design.**
- **(a) Complete §84's cut free-target phase** with the same code and items, now under a warmed timing gate and its own
  cap (an operational completion, not a rerun of anything sealed).
- **(b) Blinded mention coding** of the sealed free readouts at W1's 16 structure rows and §84's rows, Oracle lens and
  NLA. For each readout a judge sees only the readout and the row's question (for example "Is the text inside a
  parenthesis?"), never the label or the reader's name, and codes: **mentions the property** (yes/no) and, if yes,
  **which value**. Labels are joined after the codes are sealed.
  - A script also flags literal keywords per row, as a cross-check on the judge.
  - The judge route must satisfy E10's privacy amendment (zero data retention, no training). If none is available, the
    fallback is the script coding plus Guiv or Suraj hand-coding 100 seeded readouts per reader, blind to label and
    reader.

**Metrics.** Mention rate per reader and row (Wilson 95% CIs); among mentions, accuracy against the label; NLA − Oracle
differences with item-paired bootstrap.

**Prediction.** The Oracle lens mentions structure in under 10% of readouts and is near chance when it does; the NLA
mentions it more often and above chance on the rows where its asked score is high (`table_role`, `python_string`).

**What would surprise us:** frequent, correct mentions by the Oracle lens. Then the W1 blind spot is in the asked
scoring, not in what the lens says.

---

## Order and budget

1. **First (on existing activations; settles representation vs elicitation):** E5, E1, E3 (~1.3 GPU-h).
2. **Then:** E4 and E7 (~1.4 GPU-h).
3. **Then:** E8 and E6 (~1.5 GPU-h).
4. **Alongside, on CPU and API:** E10, E11, then E9.

Total about 4.2 GPU-h, plus setup. Compute stops Tuesday 27 October at 23:59 Europe/Zurich.

**Dated note, 2026-10-24 04:15 CEST (Guiv):** compute now stops **Wednesday 28 October at 23:59 Europe/Zurich**. The
new runs E12 (§99), W12 (§100) and E13 (§101) add about 2.6 GPU-h. Order: finish the queued E-runs and §87 first; then
E12, W12 and E13(a); E13(b) alongside on API. Nothing launches on Wednesday that cannot finish by 23:59. Thursday is for
analysis, Friday for the write-up.
