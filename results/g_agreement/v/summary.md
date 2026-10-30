# Phase V summary — layer, re-solving, consistency, humans, windows, positions, private facts (2026-10-12)

Pre-registration: `projects/g_agreement/PREREG_WV.md` Part V. Figures `fig_v1.png` … `fig_v5.png`; tables `v1.csv` …
`v7.csv`; per-part write-ups `v1.md` … `v7.md`. V1, V2 (pod layer rows), V6 and V7 used the W pod session; V3, V4, V5
ran on the Mac.

| part | question | pre-registered rule | result | verdict |
|---|---|---|---|---|
| V1 layer sweep (297 errors, last token) | at which layer does a reader first read the model's wrong answer, and how far behind the probe? | first layer with P(favours actual) ≥ 0.75 | probe first at 48 (79 %); J-lens 42–50 ≤ 58 %, 52+ 77–83 %; Oracle (grid carrier) 52+ 82–86 %; NLA (42, 48 only) 57–59 % | readers cross at **L52, four layers after the probe**; NLA not crossed where scored |
| V2 re-solving (297 errors) | does a reader favour the correct answer over the model's actual wrong one? | Δ(correct − actual) ≥ 0.15, CI excl. 0 | J-lens@48 +17 [+6, +29] (perm p 0.005; +29 on the 146 items where the k−1 symbol ≠ actual); J-lens@42 −15, NLA@42 −18, NLA@48 −13, Oracle ≈ 0 | **J-lens at 48 re-solves**; NLA and J-lens@42 favour the model's wrong answer; three-way: k−1 symbol drawn 54–57/297 |
| V3 sensitivity on Michael Kenney's NLA data (4,190 claims) | does a sensitivity signal add to his ≥ 2-of-8 recurrence? | ΔAUROC(both − recurrence) ≥ 0.05 on internal claims | −0.043 [−0.124, +0.019] (LOFO logistic); recurrence 0.75, sensitivity alone 0.79; on the 39 wrong claims repeated ≥ 7/8 sensitivity alone 0.83 [0.75, 0.89] | **FAIL** on the rule; post-hoc: sensitivity separates exactly the confident wrong claims recurrence cannot (proxy, not per-state controls) |
| V4 human labels | is the Gemini claim judge trustworthy? | report κ | second-judge κ 0.86 [0.75, 0.95] on true/false (100 computation claims); 300-row human sheet written, awaiting labels | judge usable as a calibration number; human κ pending |
| V5 window reader (Mac, 8 folds) | does reading a window beat the last token? | window ≥ last-token + 10 pts on T1 | L42: best Δ +3.0 [−2.7, +8.8]; L48: −2.4 to −12.8; ownership/mapping T1/T3 similar | **NOT MET** |
| V6 multi-position Oracle (32 ownership pairs, L38) | does the post-statement span read better than the last token? | span − last ≥ 10 pts, CI excl. 0, shuffled < span | last 88 %, span 72 %, shuffled 69 %, full prompt 100 %; span − last −15.6 [−31, 0]; full − last +12.5 [+3, +25] | **NOT MET**; the full-prompt span wins, the post-statement span does not; edited states: follow 50–66 % |
| V7 target-private pilot (16 pairs) **and confirmatory (48 base pairs × 2 roles, 2026-10-12 12:00 UTC)** | can a reader report a fact the visible prompt does not contain? | pilot: any reader ≥ 0.70 win, CI excl. 0.5; confirmatory: each pilot-positive cell ≥ 0.70 with the 1,000-draw pair-bootstrap CI excluding 0.5 over the 48 system-role pairs | pilot: Oracle@42 16/16, skip-lens 15/16, J-lens 13/16, NLA 15/16; **confirmatory (system role): Oracle@42 45/48 = 94 % [85, 100], J-lens@42 42/48 = 88 % [77, 96], skip-lens@42 39/48 = 81 % [69, 92], Oracle@38 38/48 = 79 % [67, 90]; NLA@42 45/48 = 94 %; probe (fixed rule) 47/48**; target ceiling 96/96 | **POSITIVE pilot → CONFIRMED on all four pre-registered cells** (`v7c.md`, `fig_v7c.png`) |

## What this adds to the picture

1. **The "readers miss the model's errors" claim is a layer statement.** At 42–48 the lenses sit at or below chance on
   the wrong answer while the probe reads it from 48; from 52 onward the J-lens and the Oracle lens read it at
   77–86 %, within 8–15 pts of the probe (92–94 %). Readers trained at the right site see it. The remaining gap is
   the four-layer lag, not blindness.
2. **J-lens at 48 is the one reader that prefers the correct answer** (+17 pts), i.e. it reads a computation the
   model then abandons; by 52 it has switched to the model's actual answer. NLA transferred from 42 reads the model's
   choice, never the correct one.
3. **Sensitivity is a real complement to consistency**, but only post-hoc and only on a proxy: it does nothing for
   input claims (AUROC 0.27) and is the only signal that separates the confidently repeated wrong internal claims.
   The pre-registered combined model fails because the proxy is too noisy to help the logistic fit.
4. **Positions: the fact is spread, not local.** V6 says the Oracle reads ownership better from the whole prompt than
   from the last token, and worse from the post-statement span alone; with Z4 (no single position or pair flips the
   model) and V5 (windows do not beat the last token for the probe), the ownership binding at L38 is a distributed
   span representation, which is consistent with the readers following d_res (W1).
5. **Target-private facts are readable, and this is now confirmed.** With the preamble in the system turn and an identical
   visible prompt, all four pilot-positive cells pass the pre-registered confirmatory rule on 48 new pairs (new names, new
   objects, mention order balanced): Oracle@42 94 %, J-lens@42 88 %, skip-lens@42 81 %, Oracle@38 79 %, each with the
   bootstrap CI above 0.5, against a 50 % prompt-only baseline and a 100 % target ceiling. NLA@42 reads it at 94 % too.
   Two secondary effects: (i) role: the J-lens, Oracle@42 and NLA read the fact BETTER when it sits in the system turn
   than when the same text is in the user turn (+12, +10, +23 pts, CIs excluding 0), so a system-turn fact is not
   hidden from these readers; (ii) mention order: every lens reads the fact better when the holder is the second-mentioned
   name in the preamble (e.g. skip-lens 16/24 vs 23/24, Oracle@38 16/24 vs 22/24). The J-lens@42 wins by tiny margins
   (mean +0.05 nats). The pilot probe's 0/16 was a scoring bug, not a reader failure: the binary probe's orientation rule
   read mention order from the visible prompt, which has no names, and fell back to candidate order; with the rule reading
   the preamble the same pilot states give 16/16 (`v7_pilot_probe_rescore.json`) and the confirmatory probe reads 47/48
   at 42 and 45/48 at 38. Pod cost: 12 minutes on a fresh pod (plus ~10 min for the retrieval restart).

## Caveats

One model; synthetic prompts; V1/V2 readers at layers 52–62 use the Oracle's nearest grid carrier and the J-lens's
own per-layer weights, NLA only at 42 and 48 (budget guard); V3 uses a cross-state genericity proxy because Michael's
release has no per-state control readouts; V6 is a 32-pair pilot; V7 is confirmed on 48 pairs (one model, one family); the human sheet is not yet labelled.
