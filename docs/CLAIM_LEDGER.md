# Claim ledger: activation_readers_MATS_final.pptx

Frozen sources:
- **G** = guivff/activation-readers @ c60fa9703f6dadc8150e11b0c2d5bbe899db02bc (r/blindspot)
- **S** = Jarus77/mats-nla-workspace @ 4d43ecb2ef8f2cfab9d8ef673a1c7f56380460fd (main)

Status words follow the source file. 'author' = Suraj's own result; R-2…R-5, R-Q = agent reviewer sessions that re-ran scoped analyses from sealed outputs (not human replications). Every chart is a native PowerPoint chart whose series are these values; Exp 28–30 charts are read programmatically from src/suraj.json, which was extracted from S.

| Slide | Claim | Value | n / denominator | Source (repo: path) | Status | Checked by | Limitation shown |
|---|---|---|---|---|---|---|---|
| 2 | Qwen3.6-27B depth and width | 64 blocks, width 5120 | — | G: projects/g_agreement/core/config.py; core/model.py:100-102 | config | — | — |
| 2 | Block convention | block L = hidden_states[L+1] | — | G: projects/g_agreement/core/model.py | config | — | — |
| 2 | Oracle / NLA injection | 16000·h/‖h‖ at marker embedding; h₁+‖h₁‖·ĥ after reader block 1 | — | G: projects/g_agreement/core/readers.py, core/config.py | config | — | — |
| 2 | Read tokens | assistant onset (chat); ' by' id 539 (E133/E137) | — | G: core/model.py; results/g_agreement/understand/e133/README_BANK.md; e137/README_BANK.md | config | — | Not uniform: E56 bank reads final 'is'; E136 token 271 (A3) |
| 3 | Verbatim readouts lang-02A, own-02A | quoted with … elisions | 1 readout each | G: results/g_agreement/agam/viewer.html, const D (O['42'].last[0], N.last[0]) | G1 pilot | re-read by author | Selected examples; block 42 for both readers |
| 4 | E71 judge–human κ | 0.68 (bar 0.70) | 63 of 100 | G: results/g_agreement/understand/e71/human_guiv_20261030/RESULT.md | R-H1 NOT MET | R-2 | single human coder |
| 5 | NLA@42 solve rate | 0.47 [0.42, 0.52] | 400 | S: experiments/06_resolving_decomposition/RESULTS.md §1 | author result | Suraj (author) | item-bootstrap CI |
| 5 | Text-only Qwen (matched) | 0.46 [0.41, 0.51] | 400 | S: same | author | Suraj | template-dependent (0.76 with benchmark template) |
| 5 | McNemar NLA vs text-only | p = 0.75 (80 vs 75) | 400 | S: same §2 | author | Suraj | not equivalence |
| 5 | Oracle@42 | 0.40 [0.35, 0.45] | 400 | S: same §1 | author | Suraj | 42 is off the Oracle trained grid (G: core/config.py); 0.37/0.39 at 40/44 |
| 5 | Union of 8 text-only samples | 0.96 | 400 | S: same §1, caveats | author | Suraj | NOT compute-matched |
| 5 | NLA hits missed by union | 0 of 187 | 187 | S: same §2 | author | Suraj | regex instrument mt-regex-2026-09-23 |
| 6 | E140 funnel | 300 screened → 58 discordant → 12 evaluable @60 | of 600 planned | G: results/g_agreement/understand/e140/analysis/REPORT.md; BRIEF §252 deviation 3 | registered | R-5 | time cap; 7/116 missing, 15 multi-value |
| 6 | E140 tracking / same answer @60 | 1/12; 11/12 | 12 | G: results/g_agreement/understand/e140/analysis/RESULTS.json | descriptive pre-stated: tracking (≥0.60, Wilson LB>0.45) NOT MET; prior MET | R-5 | conditional on 12 of 58; sensitivity 1/24, 11/24 |
| 7 | E100 S per row (Oracle@44) | 0.95, 0.74, 0.65, 0.62, 0.01, −0.05, 0.00 | 84 per row (kept 76–84) | G: results/g_agreement/understand/e100/analysis_once/RESULTS.json | R-PC MET 5/5 | R-Q | transplant moves everything |
| 7 | E100 category counts | e.g. nesting silent 64, indent 78; page 10/10/7 | 84 | G: results/g_agreement/understand/e100/analysis_once/descriptive_categories/COUNTS.json | post hoc descriptive | R-Q | — |
| 8 | E113 AUROC, first generated token | nesting ≥ 0.999, page 1.00, all 64 blocks; format plan 0.28–0.996 | 84 dev / 84 test | G: results/g_agreement/understand/e113/probes226/analysis_once/RESULTS.json | R-IN1 MET | R-4 | marker position trivial; DEV/TEST share base questions |
| 8 | E113 first-token control | token ID 12 constant | 168 per row | G: results/g_agreement/understand/e113/token_control227/REPORT.md | post hoc | R-4 | — |
| 8 | States any value in E100 readouts | 5/84, 4/84, 27/84 | 84 | G: e100 COUNTS.json (donor+recipient+both) | derived | author | under transplant |
| 9 | Cue probe in Qwen | AUROC 1.00 @42, 44 | 400 test | G: results/g_agreement/understand/e85/analysis_once/RESULTS.json | gate MET | R-2 | — |
| 9 | Cue probe in reader | 128/128 at 1.00 | 64 blocks × 2 | G: results/g_agreement/understand/e120/decoder/analysis_once/REPORT.md | descriptive | R-2 | — |
| 9 | Cue in readout words | 0.988 (genre 0.987) | 400 | G: results/g_agreement/understand/e85/readout_bow238/CV_RESULTS.md | exploratory | R-2 | genre equally recoverable |
| 9 | Cue named | 0/176 @44; 0/350 @52/60 | 24 and 50 missing | G: results/g_agreement/understand/e85/analysis_once/RESULTS.json; e120/part_a_analysis_once/RESULTS.json | R-E1 (genre vs situation) NOT MET: all rates 0 | R-2 | prompt-stated cue |
| 9 | Classifier words | department, recommends, last, incident, sentence / mentioned, local, stated, park, visit | — | G: e85/readout_bow238/CV_RESULTS.md | exploratory | R-2 | — |
| 11 | S16 donor-follow AUROC (diff term) | 0.98, 0.87, 0.98; language 0.10 | 200 per row | S: experiments/16_difference_term/RESULTS.md | author | Suraj (run by Guiv's agent) | — |
| 11 | S16 OL-part swap | 0.01, 0.12, 0.03; language 0.92 | 200 | S: same | author | Suraj | — |
| 11 | E7 matched rows | 0.39, 0.57, 0.51 | 40 pairs per row | G: results/g_agreement/understand/e27/RESULTS.md | descriptive | author | different banks; unreconciled |
| 12 | Exp 28 scatter | 47 rows (x shift, y stated) | 320 readouts per row | S: experiments/28_stmt_curve/results/table28.md | author | Suraj | — |
| 12 | Exp 28 Spearman | 0.40 (p 0.006) all; 0.28 (p 0.08) structural | 47; 41 | S: experiments/28_stmt_curve/RESULTS.md | rule withdrawn | Suraj | P1 5 vs 8 rows inconsistency |
| 12 | Exp 28 counter-rows | 7 rows stated ≥ 0.25 with shift < 0.17 | — | S: same, Reading 1 | author | Suraj | — |
| 13 | Exp 29 FVE (Python string) | 0.18 → 0.53 → 0.59 (warm start → 100 → 800) | 160 items | S: experiments/29_trajectory/results/table29.json | author | Suraj | single final critic |
| 13 | Exp 29 stated, mean of 7 rows | 0.109 → 0.117; text-only 0.30 | 320 per row | S: same | author; P1 FAILS, P2 holds, P3/P4 FAIL | Suraj | text-only has no activation (confound) |
| 13 | Exp 29 code language | 0.55 → 0.77 → 0.76 | 320 | S: same | author | Suraj | — |
| 14 | Exp 30 naming / unconditional per row | e.g. Python string 0.59 / 0.47; JSON 0.72 / 0.69; LaTeX 0.03 | 32 per row | S: experiments/30_naming_lora/results/eval30_S.json | author | Suraj | held-out clusters, k = 1 |
| 14 | Exp 30 gate FVE | 0.504 / 0.512 / 0.507 | 192 per arm | S: eval30_{base,C,S}.json | P1 partly met | Suraj | 0.761 reference unreconciled |
| 14 | Exp 30 P2–P5 | NOT MET ×3; P5 not scorable | — | S: experiments/30_naming_lora/RESULTS.md | registered | Suraj | — |
| 15 | E104 steering | block 40, 8 positions before read token, α 8 = 2.23× median norm | 84 | G: results/g_agreement/understand/e135/analysis/RESULTS.json (calibration.ratios['8'].steered = 2.231; median residual norm 80.67, 84 items × 8 positions) | registered | R-Q | E104 per-item ratio 2.43 is a different definition |
| 15 | E104 random direction | 42/84 flips (steered 84/84) | 84 | G: results/g_agreement/understand/e104/analysis_once/RESULTS.json | — | R-Q | — |
| 16 | E126 R per block | 0.013, 0.057, 0.663, 0.876, 0.871 | 84 | G: results/g_agreement/understand/e126/analysis/sealed_run/RESULTS.json | R-MED1 MET | R-Q | one bank, 2.2× push |
| 16 | E126 controls | earlier 0.025–0.107; random −0.008–0.008 | 84 | G: same | — | R-Q | — |
| 16 | E131 free text | 43/84 new; 41/84 neither | 84 | G: results/g_agreement/understand/e131/RESULTS.json | R-TX1 NOT MET | R-4 | — |
| 16 | E109 reader S | −0.52 @44 (83 of 84 defined); +1.00 @52, 60 | 84 planned; 83 defined at 44 | G: results/g_agreement/understand/e109/analysis_once/RESULTS.json | R-AR1 MET | R-Q | — |
| 17 | E135 under push (α 6) | easy 4/42; resistant 40/40 | 84 (2 missing) | G: results/g_agreement/understand/e135/analysis/RESULTS.json | descriptive (no confirmatory rule) | R-Q | post hoc groups; easy items do change |
| 17 | No push (clean run) | 24/41; 42/42 | 83 | G: results/g_agreement/understand/companions248/C_amendment1_groups/RESULTS.json | exploratory §248C | R-Q | separate analysis |
| 18 | Chain example | template-assembled text | — | G: results/g_agreement/understand/e137/bank137.py render()/trailing() | illustration | — | sealed items not in repo |
| 19 | E137 D1 twin-swap R | 0.006, 0.039, 0.268, 0.363, 0.747 | 42 pairs | G: results/g_agreement/understand/e137/analysis/sealed_main/RESULTS.json | R-NL2 NOT MET; later-site rule NOT MET | R-4 | no timing inference (R-4) |
| 19 | E137 reader categories | @44 current 13, previous 3, other 35, none 28 /79 | 76–79 | G: same, subdesigns.D1.reader_patch.reader_rates | — | R-4 | 5–8 missing per block |
| 19 | E137 probe current holder | macro 0.978 @44 over 8 of 10 classes; twin probe ≈ 0.43 | 12 test pairs | G: same, readings.probe_current_macro_ovr; reviews/R-4.md | descriptive | R-4 | not full identity decoding; twin probe at chance |
| A15 | E121 agreement | 35/35 old | 35 of 84 | G: results/g_agreement/understand/e121/analysis_once/RESULTS.json | descriptive | R-5 | steered bank |
| A15 | E118 judge fit | 37/84 steered @44 (random 34/84) vs 0/84 @52 | 84 | G: results/g_agreement/understand/e118/report/REPORT.md | descriptive, pre-stated NOT MET | R-5 | barely separates steered from random |
| A15 | E123 two-layer flag | fact row 47/47 caught; FPR 19/84 | 84 | G: results/g_agreement/understand/e123/analysis/sealed_run/RESULTS.json | R-DIS1 NOT MET (descriptive) | R-Q | language row not usable (AUROC 0.56) |
| A15 | §248B read all layers (E134 T7 bank) | +6 correct, +7 false | 100 prompts (different bank) | G: results/g_agreement/understand/e134/companion248/REPORT.md | post hoc | R-3 | — |
| A15 | Block 52 alone | fact row 84/84 steered and unsteered; language 17/40 | 84 | G: results/g_agreement/understand/e123/analysis/sealed_run/POST_HOC_EXPLORATORY_NOTE1.json | post hoc | R-Q | one bank |
| 20 | E138R donor / recipient | 63/84; 0/84 | 84 | G: results/g_agreement/understand/e138/correction_r/REPORT.md | post-output correction | R-5 | original E138 withdrawn |
| 20 | E71 κ | 0.68 (3 classes), 0.46 (4) | 63 | G: results/g_agreement/understand/e71/human_guiv_20261030/RESULT.md | NOT MET | R-2 | one coder |
| 20 | S16 vs E7 table column | 0.98 vs 0.39 | — | G: results/g_agreement/understand/e27/RESULTS.md | unreconciled | author | — |
| 10 | Carries it: probe AUROC on critic rebuild (Oracle / NLA) | py_string 0.86/0.99, js 0.84/0.97, latex 0.87/1.00, py_arg 0.51/0.93, json 0.97/0.99, md_heading 0.65/0.70, md_list 0.48/0.49, code_lang 0.98/0.98 | 160 per row, k = 1 | S: experiments/25_public_exhibits/RESULTS.md, results/table25.md | author; registered predictions scored | Suraj | Oracle readouts are out of distribution for the NLA critic |
| 10 | States it: judged (Oracle / NLA) | Oracle ≤ 3/320 (0.94%) every row; NLA 0.009–0.25 structural, code_lang 0.70 | 40 mining items × 8 | S: experiments/22_public_bank/results/score22.json | author; 'Oracle never states' 8/8 | Suraj | different split from carry |
| 5 | Best-of-N reference | Oracle any-of-11 layers 0.65; text-only best of 3 0.69 | 400 | S: experiments/06_resolving_decomposition/RESULTS.md §1 (OL grid, T_qwen_k3) | author | Suraj | not matched |
| A11 | E139 proxy reward | fact +0.019; table +0.0085; nesting +0.0027; all true−false CIs include 0 | 20 per state | G: results/g_agreement/understand/e139/RESULTS.md | descriptive | R-2 | proxy, not exact reward |
| A13 | E133 twin-swap R | 0.011, 0.045, 0.264, 0.320, 0.744 | 50 pairs | G: results/g_agreement/understand/e133/analysis/sealed_main/RESULTS.json | R-NL1 NOT MET | R-Q | recency confound |
| A14 | E138 timeline | 05:36Z … 09:10Z (06:48 entry removed: unsupported) | — | G: reviews/R-5.md; BRIEF §250 deviation 2 | — | R-5 | — |

## Discrepancies found while building (disclosed in the deck)
- Exp 30: P1's second clause (both arms within 0.03 of 0.761) fails by ~0.25; RESULTS.md scores P1 'holds' on the first clause only. The 0.761 reference is from exp 00 (different items, baseline 0.46 vs 0.569). Reported as PARTLY MET, unreconciled.
- Exp 30: RESULTS.md says training took 13 min per arm; train30_S.json wall_s = 35,698.8 s. Two random-position measures (strict regex 0.40 / 0.26; statement-level 0.16 / 0.04).
- Exp 28: prediction 1 prose says 5 of 47 rows exceed 0.15 paraphrase range; table28.md says 8 of 47. Fails either way. The shift beats the type label by 314 AIC (an earlier draft wrongly said it did not).
- Exp 29: on markdown rows a strict regex 'names' measure is high (0.26–0.78) while the judge reads ~0; RESULTS.md does not discuss it.
- E7 vs S16: the prompt pack's 0.39/0.51/0.57 order was wrong; E27 gives table 0.39, parenthesis 0.57, list 0.51.
- E135 ran at α 6, not α 8; its 'no push' bars are from §248C (exploratory), not an E135 arm.
- E137 early readouts are not mostly silent: at block 44, 35/79 name another person; slide 18 shows all categories.
- Previous decks quoted readouts that do not exist verbatim ('Ignore earlier movements', 'signaling a language identification task' — the latter from a placebo-pool readout). Slide 3 now uses G1 pilot readouts re-read from viewer.html.
- Independent fact-check (FACTCHECK.md): 22 items flagged and all addressed: E137 probe caveat, E137 timing claim, monitoring bank and fact-row scope, descriptive labels (E121, E118, E123, E135, E140), E85 R-E1 wording, E136 R-SW1 attribution, Oracle@42 off-grid, exp 06 precision reading, judge false-NO rate, slide 13/10/15/16 titles and notes, A14 timeline.
- No registration tally exists in the repo; '139' counts experiment numbers. The deck does not quote a tally.
- E122 (−0.14) is a formal-vs-informal contrast, not the E85 cue direction; removed from the deck.
- Pinned SHA in the prompt pack (7867049ff) is an ancestor of the frozen c60fa970; the 8 later commits add E95 certification, coordination files and handoff logs; no result file used in this deck changed.
