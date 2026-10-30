# BRIEF_RP §13 — Qwen3.6-27B with Karvonen et al.'s activation oracle (pair Q27): report

Pre-registered in `projects/r_panel/BRIEF_RP.md` §13. Rules are §2, §6 and BRIEF_RG's; the readings are in §12. Target
`Qwen/Qwen3.6-27B` @ `6a9e13bd` (the Phase R revision). Oracle `adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3.6-27B`
@ `891bef83` (**standard**). Pod rp27 `jkyqs8lvmasrnx` (1× H200), 20:36Z → job cap 10:35Z, billed 14.011 h ≈ $74.12. Every oracle row
is on the reference Gated DeltaNet path (K3 failed, §12 04:02Z). 108 facts analysed; the seven label-defect facts are excluded.

**Data loss and the adopted reading (§12, 2026-10-20 10:55Z; adopted by Guiv before any analysis).** The stop at 10:37:11Z erased
rp27's container disk before the final pull. Consequences:
- **Probe states.** The probe clauses use the frozen R-A states at blocks 32/48 (§13's original rule). Their indexes match Q27's on
  all 113 facts. There are no block-16 probe cells, and Q27-K2 was not evaluated.
- **Not run.** §3.5 text + activation, the §3.6 native-site rule and `ao_base` were never run.
- **Sweep.** The position sweep is descriptive, on 75 of 113 facts.

## Primary site (block 32, chat, assistant onset)
| clause | estimate [wider 95 % CI] | verdict |
|---|---|---|
| H1 quiver ΔAUC_AO < +0.01 (n ≥ 16) | n=16 +0.024 [+0.000, +0.041]; n=32 +0.020 [−0.003, +0.038]; n=64 −0.004 [−0.027, +0.015]; n=128 −0.003 [−0.012, +0.007]; n=256 −0.000; n=512 +0.000 [−0.003, +0.005] | UNDERPOWERED at n = 16–64, SUPPORTED from n = 128. With the fact bootstrap alone, the AO adds at n = 16 (+0.011 lower bound) and n = 32 (+0.010). The first Karvonen AO at the onset whose point estimate clears the bar |
| H1 median n* ≤ 8 (text tags) | 43.9 [21.7, 89.1] | **REFUTED**: worth about 44 labels (Q8 8.6, Q32 9.9) |
| H2 BH exceedances, text tags | 2: 142_cancer_cat_Thyroid_Cancer [TOPIC] (0.561 vs prompt-only 0.383); 153_it_tick_Administrative rights [TOPIC] (0.502 vs 0.317) | REFUTED, as for every pair only against a below-chance model report. Surprise-list cells; a fresh-pool re-score needs a GPU and was not run |
| H2 KNOWLEDGE ≥ 0.8 × probe(512) on ≥ half | 0.762 [0.549, 0.894] | **SUPPORTED** |
| H7 consensus gain ≤ +2 pts (BRIEF_R §1 form; the implemented form is 0 by construction) | +2.00 [+0.66, +3.06] pts | EQUIVALENT-NULL |
| H7 shared-wrong ratio ≥ 1.5 | 8.77 [5.64, 12.93] | **SUPPORTED** |

Hypothesis verdicts (weakest clause): **H1-Q27 REFUTED** (on n*), **H2-Q27 REFUTED** (on the exceedances), **H7-Q27 EQUIVALENT-NULL**.
Medians: AO 0.831 chat, text arm 0.936. The shuffled controls (864 cells) have mean 0.496 and SD 0.041 (null 0.0409); 79.7 % fall in
the band, which is the n = 200 reading of §12.

## HS — standard AO vs community Oracle lens, same model, same items (`hs.csv`, `hs.json`)
| row | Δ = AO − Oracle lens [wider 95 % CI] | facts AO / Oracle better (sign p) | MDE | verdict |
|---|---|---|---|---|
| primary: AO@32 chat − Oracle@44 chat | **+0.125 [+0.090, +0.174]** | 86 / 20 (6e-11) | 0.061 | **STANDARD BETTER** |
| common block 48, chat | +0.114 [+0.083, +0.161] | 83 / 22 (2e-9) | 0.056 | STANDARD BETTER |
| raw: AO@32 − Oracle@44 | +0.140 [+0.058, +0.237] | 85 / 23 (2e-9) | 0.141 | STANDARD BETTER |

The forecast was NOT DISTINGUISHED, or STANDARD BETTER by ≤ 0.03. The gap is four times that: on Qwen3.6-27B, Karvonen's standard
checkpoint reads the same states clearly better than the community Oracle lens. The quiver secondary row (ΔAUC_AO − ΔAUC_Oracle at
n ∈ {8, 32}) was not computed, because the Oracle lens's per-fact quiver is not among this panel's inputs.

## The oracle given the text (C-A, §3.4)
| form, render | median state / text | READ FROM THE STATE | TEXT SUFFICES | n.d. |
|---|---|---|---|---|
| AO chat | 0.831 / 0.936 | 3 | 63 | 42 |
| AO raw | 0.899 / 0.936 | 8 | 48 | 52 |
| AO-yn chat | 0.823 / 0.954 | 2 | 68 | 38 |
| AO-yn raw | 0.931 / 0.954 | 8 | 38 | 62 |

C-A against the Oracle lens (BRIEF_R §13 C-A, chat, block 44; 108 facts): READ FROM THE STATE on 3 facts for the AO vs 42 for the
Oracle lens. McNemar: 2 vs 41 discordant, exact p = 2e-10.
- **Each reader is judged against its own text arm.** The AO's text arm is strong (0.936) and the Oracle lens's is not. So
  "READ FROM THE STATE" here measures how weak each reader's text arm is as much as how much each reads from the state.
- **Surprise-list cells.** 26 facts are AO TEXT SUFFICES with the Oracle lens READ FROM THE STATE, and one the reverse (96_spam_is).
  §13 puts these on the surprise list. None is claimed without the fresh-pool re-score, which needs a GPU and was not run.

## HP4 — tier robustness on the Phase R model (HP1's clauses applied to Q27)
| clause | Q27 | Oracle lens (WS3 `interim.md`, block A, primary) | result |
|---|---|---|---|
| (i) H1 | REFUTED (n* 43.9) | UNDERPOWERED (olens n* 4.3) | differ, and Q27's is not UNDERPOWERED / EQUIVALENT-NULL. Not a SUPPORTED ↔ REFUTED flip |
| (i) H2 | REFUTED | REFUTED | equal |
| (i) H7 | EQUIVALENT-NULL | UNDERPOWERED | differ, but both are in {UNDERPOWERED, EQUIVALENT-NULL}: allowed |
| (ii) C-A READ FROM THE STATE < 54 of 108 | 3 | — | met |

**HP4: PARTIAL.** Clause (i) fails on H1. The standard AO is worth about 44 labels on text-derivable facts, where the Oracle lens is
worth about 4, but no verdict flips sides. The forecast was SUPPORTED.

## Position sweep (descriptive, 75 of 113 facts; `sweep_descriptive_75.csv`)
Median AO AUROC by block and offset (0 = assistant onset, 9 = last text token):

| block | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| 16 | 0.782 | 0.786 | 0.765 | 0.756 | 0.817 | 0.784 | 0.848 | 0.817 | 0.848 | 0.878 |
| 32 | 0.840 | 0.689 | 0.684 | 0.724 | 0.861 | 0.774 | 0.860 | 0.840 | 0.868 | 0.896 |
| 48 | 0.814 | 0.714 | 0.628 | 0.691 | 0.852 | 0.786 | 0.851 | 0.800 | 0.857 | 0.899 |

Offset 7 vs the onset at block 32 on these 75 facts: +0.007 [−0.029, +0.056]. This is not a §3.6 test: no pool choice exists. Unlike
the 8B and 32B pairs (+0.050 to +0.083), the 27B AO shows no gain at offset 7. The sweep rises toward the last text token on every block.

## Not run (cap and disk loss)
§3.5 text + activation; the §3.6 native-site choice and restatement; `ao_base`; the sweep probes; block-16 probe cells; Q27-K2.
