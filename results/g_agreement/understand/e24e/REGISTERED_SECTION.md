## §137 Rulings of 26 Oct, 00:45 CET (capture environment, W12 freeze, analyses of sealed runs)

**Context.** E24 attempt 2 failed slot-0 h44 parity (min cos 0.579, n 4,704), and so did E32 (min 0.765, n 2,100),
both in `/weights/venv-kernels`. E24-D arm (a) (W1 code, `/weights/venv`) reproduced W1 300/300; arm (d) (E24 code,
`/weights/venv`) failed. E28's score-level W1 parity passed in `venv-kernels` (Δ ≤ 0.006 AUROC), so any problem is in
a minority of items or at the raw-activation level. No E24 or E32 science output exists. Every rule below is fixed
before any further capture.

**1. E24-E: capture-environment parity check (registered now; descriptive; owner W-core; one pod, ≤ 0.75 GPU-h,
run once).**
- **Items:** the E24-D 300-item sample (including its 7 failures), plus up to 200 items seeded (20261026) from E24
  attempt 2's slot-0 items with cos < 0.999 if their ids were pulled; otherwise 200 seeded from E24's bank with
  W1 references.
- **Arms.** All arms read position −1 and `.clone()` every captured block output.
  - **A:** W1 code, stop at 44, `/weights/venv`, W1's batching. Reproduction control.
  - **B:** as A, in `venv-kernels`.
  - **C:** as A, batch size 1, no padding. Model-truth reference.
  - **D:** as C, in `venv-kernels`.
  - **E:** `venv-kernels`, batches bucketed by exact length (zero padding).
  - **G:** `/weights/venv`, W1 code extended to capture E24's full grid through 60, W1's batching.
- **Metrics:** per-item h44 cosine against W1's stored vector, and against arm C. Per-arm counts below 0.999, and
  failures by length, padding and row.
- **Decision.** The capture mode for any relaunch is the fastest arm in which every item has cos ≥ 0.999 against W1,
  with preference for G (E24 needs the grid). If arms C and D agree with each other (all ≥ 0.999) but W1 deviates
  from both, the W1 reference itself is suspect: hold everything capture-dependent and report to the coordinator.
- **Seals and logs** as usual; no science reads.

**2. E24 and E32 relaunch (conditional on 1).** If E24-E certifies a mode, E24 (remaining cap 32,738 s of 43,200) and
E32 (its registered cap less the 0.50 GPU-h used) relaunch once in that mode. The every-item slot-0 parity gate is
unchanged. E34 is released only by that relaunch's parity PASS, as before. No other change. If no mode is certified,
E24, E32 and E34 are reported INCOMPLETE with the E24-E evidence.

**3. Impact audit of sealed `venv-kernels` runs (CPU, after 1; W-core with each owner).** Once E24-E identifies the
failing condition (for example padding above a threshold, or length), report for each sealed run that captured or
scored in `venv-kernels` (E19, E22, E27(c), E28, E30, E31(ii), E33) the fraction of its items in that condition.
Sealed results are not rerun or altered. A run with more than 10% of its items in the condition is reported
"environment-qualified" in the write-up. If no condition is identified, the audit reports that, together with E28's
score-level parity.

**4. W12 freeze now.** The 19:00 scheduled freeze did not run. W-core freezes W12 (rows, items, phrasings) as soon as
it reads this. Then the §124 order applies unchanged: W-text seals D/P and the §136 mechanical `PREDICTIONS.json`
against that freeze; then reader scoring. There is no other change; the freeze time is reported as actual.

**5. Single analyses of sealed runs.** E28 (W-lens), E33 (W-lens), E30 and E31(ii) (W-internals) and E27(c)
(W-mechanism) each run their single registered analysis now, on the integrator-verified pulls. Where a worker
cannot reach GitHub, the integrator delivers the pinned files from the local mirror. Each owner posts its verdicts
against the registered rules only.

**6. E35 closed.** "No adequate SAE" stands as registered (transfer FVU 0.411 with 42% dead latents; trained TopK
FVU 0.503 with 10.9% dead). No further SAE work. The write-up reports both gate numbers.

**7. E36.** W-text's re-pin proceeds. If the request lacks a score-level W1 parity gate, add the E28-style gate
(three W1 rows, |ΔAUROC| ≤ 0.02, before production) and launch. E36 is covered by item 3's audit.

