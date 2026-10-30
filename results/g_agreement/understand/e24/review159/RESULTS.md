# E24 owner review and C4 judge audit

Verified analysis seal `7a5d19474187ebf4101d491efd23ce0242e7e4a5b6ebd3e3aad36999bc7c3c44`; source/input pins and all2 sealed shards verified. No registered analysis rerun.

R0 passes on all28 rows. R1 and R4 hold at all11 layers. R2 has no qualifying cells. R3′ holds at28,32,36,44,48,52,56,60 (8/11). R5 holds at48,52,56,60 (4/11); the across-layer condition that R5 hold at every R3′ layer is false. R1 across-layers is true.

| Layer | R1 blind / eligible | R3′ carried / 7 | R4 stated /1596 | R5 dissociated /7 |
|---|---:|---:|---:|---:|
| 20 | 16/19 | 2 | 15 | 3 |
| 24 | 16/19 | 3 | 18 | 2 |
| 28 | 16/19 | 4 | 18 | 2 |
| 32 | 17/19 | 4 | 8 | 3 |
| 36 | 18/19 | 4 | 10 | 3 |
| 40 | 18/19 | 3 | 15 | 3 |
| 44 | 16/19 | 6 | 5 | 3 |
| 48 | 17/19 | 6 | 6 | 5 |
| 52 | 17/19 | 5 | 2 | 5 |
| 56 | 18/19 | 6 | 0 | 6 |
| 60 | 18/19 | 6 | 1 | 6 |

C4 audit:218/220 agreement (99.09%),20 checks per layer. At24, latex_fraction: regex both, judge neither (alternatives/assumptions do not assert both states). At28, json_type: regex neither, judge B ("are specific numerical values"). All disagreements retained; no regex edits, score replacement or revised R4 verdict.

Layer/source-state/regex key unopened until all220 manual semantic codes frozen. Aggregate user-provided verdicts were known to reviewer.

Private packet, key, frozen codes and full joined audit remain under ignored cache. Public export omits source IDs and opaque-ID mappings. CPU audit run once using unchanged e24_judge_audit; zero GPU/model API calls.
