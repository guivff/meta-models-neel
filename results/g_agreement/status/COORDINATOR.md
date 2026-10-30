# Coordinator tracker: all chats

Maintained by the coordinator (Guiv's main chat). **Updated: 2026-10-29 11:50 CET.**
Operational state only; scientific verdicts live in `reviews/R-*.md`. The compiler's report carries the authoritative
cost ledger (latest 92426db4e: GPU exposure USD 1,855 / 2,500; judging 235 / 1,000).

- **Clock:** last launch Thu 29 Oct 24:00 CET; last seal Fri 30 Oct 06:00. Friday is distillation only.
- **Ceilings:** GPU USD 2,500 (flag at 2,000; parked pool 900). Judging USD 1,000 (flag at 800).
- **Standing rules:** §217 with clarifications 1–3. Latest coordinator notes: E100e operational note 1 (f599f121a);
  E95 hold rule priority note 1 (this commit).
- **Frame (§216, reframed):** readers read the vector at their site, not the model's computation. Bookkeeping is the
  calibration class; tracked state and belief vs truth are the lead examples.

## Results (reviewer-checked unless marked)

| Exp | Result |
|---|---|
| E73 | Oracle meets the real-text rule |
| E80c | R-X3 NOT MET (control was rank-matched, not variance-matched); J-fraction AUROC 0.81 |
| E81 | R-T1 MET: text descriptions reproduce most hits and misses |
| E82 | Oracle R-B2 MET: wrong belief over truth (wrong_bridge 11 vs 3; knowledge cutoff 41 vs 21); NLA NOT MET |
| E86 | NOT EVALUABLE (blocked arms) |
| E87 | Corrected: nesting consumed, var_type late; R-L1 NOT EVALUABLE (control row failed) |
| E90 | R-TB1 MET |
| E94 | Agreement precision 94.2% vs 87.0% better single reader; base rate 32.8% |
| E97 | Oracle R-T1 MET (R-5, 73654bf0): J-forecast BA 0.72 vs taxonomy 0.32, Δ 0.40 [0.22, 0.73]; 4/40 rows reported; NLA NOT MET. Pooled R-P1 pending |
| E98 | Forecast claim not made (18/23 below always-MISSED 20/23) |
| E100 a/b | R-PC MET 5/5; missed rows silent under full transplant |
| E101 | Descriptive: written at site +0.52 / +1.12 |
| E102 | NOT RUN (feasibility) |
| E103 | Corrected R-H2 NOT MET (+0.08) |
| E104 | Arm U R-U1 NOT MET (+0.18 / +0.14); arm N NOT EVALUABLE |
| E105 | R-BT1 NOT MET; no flips, behaviour +0.31 |
| E106 | Both arms NOT RUN (P operational, T feasibility); R-4 final 92f7818c. Repair untested |
| E110 original | NOT RUN at gate (TwoHopFact 6/3,000) |
| E108 | Falsifier MET (R-3 pending): reader names the model's open pick 19% vs outside LLM 48%, mode 66%; delayed 0% |
| E109 | R-AR1 MET on fact recall (R-Q pending): probe 0/84 at 44–48, 84/84 from 52; Oracle Δ +1.00 at 52. Language plan R-AR3 MET |
| E113 | R-IN1 MET (R-4 pending): bookkeeping AUROC 1.00 in the lens's last layers at the answer token; first token constant |
| E84 | Probe gates failed (0.72/0.71); readers not run |

## In flight

| Exp | State | Next |
|---|---|---|
| E95 | 6/8 re-time shards running, seal ≈ 15:05 | 3-0, 3-3 wait behind priority list |
| E100e | First attempt running (cap 1,800 s) | One measured re-attempt allowed after post-load NO_FIT; W-mech-C cap override requested |
| E107 / E108 | Generation / judging | Analyses, R-3 |
| E109 | Judged, sealed | Once-only analysis, then E111 |
| E110 dev2 | Obscure-bridge bank READY (92b8cdc4) | I-2 filter, ≤ 3,600 GPU-s on ≤ 4 pods, complete quarters by 16:00 |
| E111 | CPU, waits on E109 | Decides thesis wording |
| E112 | Output sealed (40aee07e, 0.85 GPU-h) | Judging W-internals-C, adapter, R-Q |
| E113 | Captures sealed | Probe fit and analysis (W-lens) |
| E114 | Cap 2,000 s approved | I-2 allocation |
| E84 / E85 | One measured attempt each approved | I-2 allocation |
| E99 | Phase 1 running | Cap USD 150 |

## Registered late (§227–§229)
§227 throughput rulings. §228: E115 (CPU, stale-readout trust check + agreement × J-fraction gate), E116 (open choice
at blocks 52/60), E117 (push the E113 direction inside the reader; H200 by 19:00), E109 robustness. §229: E118
(context-consistency judge on stale readouts, ≤ USD 1), E119 (newer Oracle lens checkpoint, conditional on Guiv naming it).
H200 order (§229 clarification 1): E110 → E117 → E116 → E95 3-0/3-3 → E119.
