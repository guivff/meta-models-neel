# Track Q status: integrator Q

**Updated:** 2026-10-30T13:57Z. Overwritten every 2 h. Blockers go straight to Guiv.

## GPU spend (r_ops/spend_today.py, 13:57Z)

- **All tracks:** **USD 736.26 booked** per spend_today.py, no pods running. Booked plus active caps is USD 736.26 of the **USD 2,500 ceiling** (e72952df6).
- I-2 reports E140 (pod created 07:54:22Z, COMPLETE) **booked USD 3.71** once (8ea553e96). That booking is not yet in the compute.jsonl that spend_today.py reads; with it, the total is about USD 739.97.
- **Track Q pods since the last status:** none. Its last pod, E139 cwjlzjqlpk0076 (493.5 s, USD 0.73), was booked at 4f9066cd7.

## Running now (Track Q)

- None.

## Sealed, delivered or analysed since 11:47Z

| Item | Seal | Note |
|---|---|---|
| **E95 binding certification** (Guiv 839b11162) | CERTIFICATION_SEAL 5b593bf5 (`understand/e95/trackq_certification`, 78bce0d0c) | **J-fraction map + E62 population/median 0.025462539 CERTIFIED** for 69 of 72 rows (E54 ×2 and e57 category_switch not found). **Placebo targets PARTIAL:** certified for the 10 E87-reuse rows via E87 PRIVATE_JOIN 50f135c4 / PACKET_SEAL a97ec15a; not found for E95-built placebo items. **Map rule/operator/threshold and placebo-corrected single-site verdicts NOT FOUND.** Under 839b11162, H-M1 is NOT EVALUABLE on those parts unless the lineage owners produce them by 16:30 CET |
| Earlier today | — | E137 main (1703a6c2, R-NL2 NOT MET), E139 scoring (302e487b, instrument PASS), E133 main (e6f12add), E124 (fork), E140 (I-2), E95 custody: all delivered or closed (see the 09:47Z status) |

## Judging actuals (sealed COUNTS / COST)

| Bank | USD | Status |
|---|---|---|
| Earlier Track Q banks (E56 to E80c) | ≈ 11.67 | sealed |
| E100 / E87 grouped | 2.843 / 14.507 | sealed |
| E104 / E109 / E108 / E107 | 0.150 / 0.814 / 0.459 / 5.027 | sealed |
| E79B | 0.32237975 / 3 | sealed |
| E127 / E123 / E128 | 0.396708 / 0.1735755 / 0.346519 (each of 3) | sealed |
| E120 a+c | 0.81472825 / 2 | sealed |
| E117c (shared bank) | 0.41786775 booked | settled |
| **E107b** | **0.23369825 / 2** | sealed; 394 KEPT, 4 UNPARSEABLE |
| **E137** | 0.20524450 / 2 | COMPLETE 07:18Z (C 3223e8ce / 885fba05); 462 terminal (406 KEPT / 56 UNPARSEABLE) |
| E133 (synthetic) | 0.24170250 / 5 (shared with E133b) | settled 03:07Z; 540 terminal (467 KEPT / 73 UNPARSEABLE) |

## Queue

- **E95:** W-Lens runs its single analysis (or the descriptive fallback) with R-Q reviewing by 18:00 CET. Track Q has no further action unless a lineage owner produces bindings 1 or 3.
- No other Track Q item is open.

## Waiting on

- W-Lens: the E95 analysis or descriptive fallback.
- I-3 / E87 lineage owners: whether any sealed placebo target for E95-built items, a map-verdict rule or placebo-corrected single-site verdicts exist (deadline 16:30 CET).

## Blockers

- None for Track Q.
