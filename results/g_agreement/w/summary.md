# Phase W summary — are the readers class-mean readers? (2026-10-12)

Pre-registration: `projects/g_agreement/PREREG_WV.md` (H-W, P1–P3, decision rules; Deviations dated). Brief:
`projects/g_agreement/manifest/brief_wv.md`. Figures: `fig_matrix.png` (W1), `fig_precision.png` (W2). Tables:
`w1/matrix.csv`, `w1/reader_differences.csv`, `w2/w2.csv`, `bridge/bridge.csv`, `w3/w3.csv`, `w4/w4.csv`.
Pod: one session on mats-minis-e, 157.6 pod-minutes (S1 954 captures, S2 4,032 steered decodes, S3 27,442 native
reader scores, S3v1 12,528 layer-sweep scores). S4 free-text sampling was skipped by the budget guard (see Deviations).

## Verdict against the pre-registration

| prediction | threshold | result | verdict |
|---|---|---|---|
| P1: every reader follows the class-mean direction d_cm | follow ≥ 75 % per family and pooled | ownership: J-lens 91, Oracle 77, NLA 66, skip-lens 72; mapping 88–100; errors (L48) J-lens 70, Oracle 97; pooled 77–90 | **FALSE** (NLA, skip-lens, J-lens@48 miss) |
| P2: the probe-weight direction d_pw moves the probe but not the lenses | lenses ≤ 60 % and inside the random band; probe ≥ 80 % | probe 96 % pooled (100 % ownership/errors); lenses 45–56 % ownership/errors, 69–78 % mapping (random band in mapping: 72–78 %) | **FALSE** on the ≤ 60 % clause in mapping only; at block 42 the lenses are inside the random band everywhere. On-grid update (O44, 2026-10-14): the Oracle at block 44 follows d_pw 66 % in ownership, above the 47 % random band |
| P3: some family where d_cm flips the model ≥ 20 pts less than the full swap | flip(d_cm) ≤ flip(full) − 0.20 | ownership 100 vs 100; mapping 94 vs 95; errors 34 vs 19 (d_cm beats the centroid swap) | **FALSE** |
| layer-48 clause: d_cm at L48 rewrites the model's error | flip ≥ 50 % | 34 % [24, 47] | **FALSE** |

Decision rule 3 applies (P1 fails): H-W "readers are class-mean readers" is not supported as stated; the matrix is
reported as is. Rule 2 on the layer-48 claim: d_cm at 48 does not rewrite the answer (34 %) and d_pw moves only the
probe, so the earlier "readers miss the model's errors at 48" is replaced by "no reader-independent linear method
reads a load-bearing off-text answer at this site" (V1 adds: readers trained at 52–62 do read it; see `v/summary.md`).

## What the matrix shows (W1, `fig_matrix.png`; 64 states per cell, α 1, pair bootstrap 1,000)

1. **Where the model flips, every reader follows, but by different amounts.** Full swap and d_cm flip ownership and
   mapping 94–100 %; readers follow 66–100 %. Fraction of the reader's own natural separation recovered by d_cm:
   J-lens 0.61–0.77, Oracle 0.39–0.57, NLA 0.18–0.59, skip-lens 0.46 pooled. NLA trails J-lens by 18 pts pooled
   [9, 28], a pre-registered reader difference; 34 of 66 reader comparisons on the d_cm/d_pw rows meet the
   difference criterion (`w1/reader_differences.csv`).
2. **The probe direction is nearly invisible to the lenses.** d_pw moves the probe 88–100 % and the model 0–5 %; at
   block 42 the J-lens, Oracle, NLA and skip-lens stay inside their random band (ownership/errors 45–56 % vs random
   48–52 %; mapping 69–78 % vs random 65–75 %). The energy of d_pw in the swap is < 2 % in every family
   (`directions_report.md`). Exception from the on-grid rerun: the Oracle at block 44 follows d_pw 66 % [52, 78] in
   ownership (random 47 %), so it partly sees the probe direction there.
3. **The readers follow directions the model ignores.** d_J (top-384 J-space, 8 % of the ownership swap energy)
   flips the model 0 % and moves the readers 80–94 %; d_res (the 81 % remainder) flips 0 % and moves them 67–88 %.
   In mapping, d_J overlaps d_cm (cos 0.44) and flips the model 91 %; d_res flips 0 % and still moves readers
   70–80 %. The Phase Z finding replicates with the decomposition fixed in advance.
4. **Errors at L48 are different.** The centroid swap flips only 19 % and d_cm 34 %; Oracle follows d_cm 97 % and
   J-lens 70 % even though neither reads the natural wrong answer at 48 (V1: 41–49 %). A class-mean push is readable
   where the natural state is not: the readers respond to the direction, not to what the state does.
5. **Mapping has a high random floor.** Random directions move the mapping readers 65–78 % (vs 48–52 % elsewhere),
   so "follow" in mapping must be read against that band; the reader-shift fractions (0.08–0.14) show the random
   effect is small in magnitude.

## Precision on graded facts (W2, `fig_precision.png`) and the bridge

- **Counts (600 items, N 1–99, model greedy-correct on all):** the model's own next-token distribution keeps the
  magnitude (Spearman 0.83 [0.77, 0.88], exact 9 %); the readers' native score vectors over 1..99 do not: exact
  1–3 %, Spearman J-lens undefined, Oracle −0.33, skip-lens −0.08. No reader "keeps the magnitude and drops the
  digits"; they do not read the count at all at the last token of these prompts. (NLA has no native counts column;
  its free-text counts readout needed S4.)
- **Mapping-8 (94 items):** model 97 % exact; probe 21 %, J-lens 12 %, Oracle 14 %, skip-lens 18 % (chance 12.5 %).
  The same readers score 85–94 % on the two-candidate mapping items of G1, so the two-way wins do not survive an
  eight-way candidate set. This is the single most important caveat for the earlier "native scoring" results.
- **Arithmetic (Michael Kenney's plain "a ± b =" format, 100 triples):** the model does not answer in that format
  (17/100 greedy first tokens are numbers); readers' native vectors rank the result at Spearman 0.44–0.50, exact 2 %.
- **Bridge to Michael's Result 2:** his probe-weight recipe (18 class-mean + 18 probe-weight dims per operand) on our
  100 layer-42 states gives operand exact-match a 0.24 [0.16, 0.32] / b 0.48 [0.38, 0.57] vs his 0.83 / 0.93 on
  600; the learning curve (20→80 training rows per fold) rises without a plateau, so the gap is attributed to n, not
  the pipeline. His NLA free-text numbers have no counterpart (S4 not run).

## Claim precision and consistency (W3, W4; fallback, see Deviations)

S4 was never produced, so the pre-registered S4 claim precision is not available. On the Track C judging already
done (gemini-3.8-flash, κ 0.86 against 300 human labels in V4): G1 input-claim precision NLA 27 % [23, 32], Oracle
40 % [27, 53]; computation claims 46 % / 35 %. On the G4 repeats (8 items × 2 readers × 2 samples) the ≥ 2-of-2
consistency filter keeps 47 % of Oracle claims and 24 % of NLA claims and does not raise precision (Oracle
computation 40 → 28 %, NLA input 25 → 27 %; agreement-count AUROC 0.38–0.66 with CIs spanning 0.5), against
Michael's 0.90 / 0.75 on his 500 NLA states; V3 re-analyses his data directly (`v/v3.md`).

## Reading

The readers are not class-mean readers in the strict sense (P1 fails: NLA and skip-lens follow d_cm at 66–72 % in
ownership), but every lens reader shares the same blind spot and the same sensitivity: none sees the probe direction,
all respond to the J-space and remainder components that the model ignores, and all respond to a class-mean push at
L48 that does not change the model's answer. The eight-way mapping and the counts results add a sharper caveat: at the
last token the readers' native vectors carry two-way contrasts, not the value itself. "Readers report what is in the
vector, not what the model uses" stands; "what is in the vector" is narrower than the two-candidate scores suggested.

## On-grid Oracle check (O44, 2026-10-14; `o44/o44.md`, `o44/fig_o44.png`)

The Oracle lens is trained on blocks 20–60 step 4, so every Oracle number above was read off its grid at block 42. A
pre-registered rerun at block 44 (same states, same scoring; reproduction checks passed) changes two Oracle cells under
the ≥ 10-point rule: it follows the ownership class-mean direction more (77 → 92 %) and the ownership probe direction
partly (52 → 66 %, random band 47 %). The central result does not change: on-grid, the Oracle still follows the
J-space component (91 %) and the remainder (94 %) of the ownership swap while the model flips 0 %. X1 natural
bindings improve slightly (ownership 83 → 91 %, mapping 87 → 94 %). The J-lens, which has a native lens at every
layer, reads mapping less well at 44 than at 42 (full swap 98 → 70 %); that is a layer effect, not a grid effect.
