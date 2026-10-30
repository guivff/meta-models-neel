# E42 close-out — 2026-10-26

Reviewed sealed outputs only; no recomputation. Corrected state seal 0ca485e630be92fc2c04e8a0c8c7ac91d5efd189d1a27359bc3b0063c6705d9f, persistence seal 145a11d9e7710fa0349a7a64b59edce5fd6296255ef7a33cd23438743e6a9b04, analysis seal 34b1330de3638be234a3ac6fb537cfaaa3a95aa17419ab263c4d0805868595d9 and code/output hashes verify. Original failed lock and partial directory remain hash-consistent with REINVOCATION_BINDING.json.

- R1 NOT MET: persistence versus Oracle rho -0.127111, 95% CI [-0.436144, 0.195662], n=40.
- R2 NOT MET: persistence-minus-D correlation difference -0.432794, CI [-0.945943, 0.107810], n=21. Persistence rho -0.214612; D rho 0.218182.
- R3 NOT MET: 5/18 high-persistence rows meet Oracle >=0.65; 12/17 low-persistence rows meet Oracle <=0.65. Both strict majorities were required.
- Registered rho<=0.20 falsifier holds. Short-persistence sayable rows: W1:latex_fraction and W12:sentence_position.
- Controls: probe rho 0.080020, CI [-0.233973, 0.398463], n=40; NLA rho 0.047040, CI [-0.299160, 0.369205], n=37.

All 41 bank-row persistence estimates are evaluable, each with zero initial-state exclusions. W12:clause_embedding is excluded from the analysis score join. All reported bootstrap intervals have 10,000 finite draws and no undefined draws. No additional inference, source change, label change or rerun is made in this review.
