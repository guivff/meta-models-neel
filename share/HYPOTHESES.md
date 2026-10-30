# Hypotheses as they stand (26 Oct 2026), and what is running or queued

This page is a synthesis of results that are already sealed. Each line cites the experiment it comes from; the full
headlines are in `EXPERIMENTS.md` and `inventory/experiments_index.json`. The detailed hypothesis document as written
is `projects/g_agreement/REVIEW_HYPOTHESES_2026-10-26.md`. It ranks eight mechanisms (H1–H8), each with a decision
rule, and lists eight facts it thinks are misread (M1–M8). Since it was written, E47 and E48 have tested several of
those hypotheses; the results are under "Mechanism" below.

## What we believe now

**1. Asked about text structure, the Oracle lens is at chance where a linear probe is near perfect.**
- W1 rule (i) passed: 16/19 evaluable count/state rows, Wilson [62.4, 94.5].
- E24 R1 holds at all 11 trained layers (20–60): blind on 16–18 of 19 structure rows, probe ≈ 1.00.
- W5's registered verdict is NOT EVALUABLE: 10/16 rows, bounds 62.5–75%.
- E36 (a fresh 25-row bank) did not replicate the registered H1 (8/16). The Oracle was ≤ 0.65 on 13/16 rows there,
  but the probe gate failed on 6.
- On semantic rows the Oracle mostly matches the probe, though not on enough rows to pass the rule: W1 (iii) 6/9,
  FAIL.

**2. The NLA is not a general fix.**
- W1 (ii): only 2/16 blind-spot rows come within 0.10 of the probe.
- The NLA is clearly ahead on some rows, e.g. latex_section +0.443 and json_type +0.223 (paired NLA − Oracle).
- It is behind on others, e.g. latex_fraction −0.762.
- W12: the Oracle beats the NLA on paragraph and sentence-position rows.
- Your pilot NLA numbers did not survive our fresh items: table column 1.00 → 0.568, paren 0.98 → 0.744. Our working
  explanation is that bank construction matters a great deal. The evidence: W1 vs E36 structure reliability is 0.326
  [−0.230, 0.768] (E48), and E27 could not attribute the S16 vs E7 gap to one cause.

**3. The Oracle lens does not *state* structure; it enacts it.** See `HEADLINE_CLAIMS.md`: E13, E24 R4, E43, E37 and
Q1. It does state content and planted concepts (SA-R 51.5%, Q1 content tier 18.8%).

**4. The blind spot is in the lens before RL and is cheap to unlock per row, but the unlock does not transfer.**
- E37: the SFT lens is as blind as the RL lens (paren 0.46 vs 0.47).
- E28: a light LoRA unlocks paren to 0.91 within 100 steps.
- E44: content-only training does not unlock structure.
- E50: training on 8 structure rows does not transfer to 8 held-out rows (held-out medians 0.58–0.60).
- So it looks like a per-row reporting gap that is easy to train, not one general policy that is missing.

**5. Mechanism: what is ruled out and what is still open.**
- **Falsified:**
  - transport vs conversion (H6), by E47's dual injection;
  - bag-of-constructs presence (H3), by E48: ρ 0.198 [−0.052, 0.436];
  - gist inference (H5), by E48: ρ −0.080, 22 counterexamples;
  - "persistence predicts sayability", by E42: ρ −0.13 [−0.44, 0.20].
- **Not falsified:** instruction-inert lexical priming (H1) and small gain under nuisance (H2), by E47. The pooled
  structure asked mean is 0.547 [0.508, 0.588] (E48), which is weakly above 0.5, not exactly at chance.
- **Reconstructor:** it sees local state only at longer spans: prose_paren 0.55 at k = 1 vs 0.81 at k = 16 (E45).

## What would change our mind

| belief | would change if |
|---|---|
| 1 (Oracle blind on structure) | your items × our phrasings, or our items × your phrasings, gives Oracle@44 ≥ 0.75 on table column or paren (2×2 cross-scoring, `cross_scoring/`); or E49's 16-row descriptor × state grid shows the Oracle reading tracked state outside punctuation-like rows |
| 2 (NLA not a general fix) | the cross-scoring shows the NLA at ≥ 0.9 on our items with your phrasings: then phrasing, not bank, explains our 0.568/0.744 |
| 4 (lens-specific, present before RL) | E32 (base Qwen reading one injected residual) shows base Qwen also blind: then the blind spot is a base-model property (hypothesis H4), not the lens's |
| 5 (H1/H2 open) | E51 finds the warm-start teacher's bullets never name structural state (supports H8); a within-item dose-response with sign-correct slopes on ≥ 10/16 structure rows (H2's rule) |
| the free-text claims | your raw S16 margins show the NLA's preferred candidate flips with the true value (then E27's 100/200 strict-sign is not a one-sided bias); a blinded judge on our W1 free readouts (registered, not yet run) |

## Running or queued (as of 26 Oct, ~17:45 CET)

Our compute window closes on the night of Tuesday 27 Oct. The write-up is due Friday 30 Oct.

| item | state | what it asks |
|---|---|---|
| E40 | RUNNING, GPU, pod training since about 10:53Z; expected end about 01:30Z Tue 27 Oct | a second SAE on the reconstructor's error (65k TopK, AuxK, 100M tokens) |
| E51 | RUNNING, CPU; targets delivered 13:50Z | did the warm-start teacher ever name structural state? (H8) |
| E49 | QUEUED; bank sealed (`results/g_agreement/understand/e49/`), waiting for the worker package and a label-free pod archive; one pod, 10,800 s | is the blind spot "tracked state" in general (16 rows: descriptor × state)? |
| E32 slot 2 | 5/6 shards sealed; rerunning slot 2 (about 13,267 s) needs a coordinator ruling | can base Qwen read structure from one injected residual? |
| A02-K | prepared, waiting for a go | fact vs answer word (phase R) |
| analyses with sealed inputs, not yet run | W1b §84 registered analysis; S2/W2 reconstructor-fidelity analysis; the W1 blinded recall judge; E12 NLA arms | — |

Recently finished (25–26 Oct), so you need not duplicate them:
- E36, E37, E39, E41, E42, E43, E44, E45, E46, E47, E48, E50;
- E27 (our reconciliation with your S16) and E29 (your seven exp-13 rows on our side).

Abandoned or never run: E9; §51 (reconstructor ceiling); §55 (taboo audit); §63 (beyond its U0 gate).

## Our plans that overlap yours

- **The 2×2 cross-scoring of table column and paren.** You have the stages built; the inputs are in
  `cross_scoring/`. We have not scored your exp 13 items with our phrasings ourselves, so there is no duplicate.
- **E29.** It ran your seven exp-13 rows through our base-Qwen text-discriminability check (non-blind, no CIs):
  `results/g_agreement/understand/e29/`.
