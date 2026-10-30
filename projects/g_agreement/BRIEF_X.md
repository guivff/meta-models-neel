# BRIEF_X — Phase X: readers against a causally established fact (pre-registration)

Written 2026-10-07 before any Phase X compute. Builds on G1–G6 (BRIEF.md, BRIEF_G5G6.md) and on the
direction review (results/g_agreement/direction_review.md). Same target, site and readers as before:
Qwen3.6-27B @ 6a9e13bd, block-42 output at the last prompt token (pre-answer), readers J-lens, Oracle lens
(OLens), NLA. All reader scoring in this phase is by NATIVE LOG-ODDS (core/scoring_lo.py); free text is not
scored. Everything below is fixed before collection; changes go under "Deviations" with a date.

## Question
Replace "do the readers agree with each other" by three independent columns per feature class:
  (a) PRESENT: a held-out linear probe recovers the fact from the state (vs a two-half ceiling);
  (b) LOAD-BEARING: editing the fact in the state changes the model's own answer;
  (c) REPORTED: each reader's native log-odds favour the fact.
The cells of interest are (a)=(b)=yes, (c)=no. Agreement between readers is a derived quantity.

## Modules (each separately runnable; shared core)
X1  bank + native LO    48 pairs x {ownership, mapping}, 24 pairs x {language, tense}; natural states only.
X2  causal planting      32 ownership + 32 mapping pairs (the first 32 test pairs of each family by pair index);
                         interpolate A->B at a site, dose ladder, model flip + reader LO at the same dose.
X3  floor item sets      (a) mapping puzzles the model gets WRONG; (b) self-choice prompts where the model's
                         prompt-only guess about itself disagrees with its actual choice. Prompt-only is at
                         floor on both by construction.
Deferred (X4–X6, not in this run): extra reader families (skip lens, R-lens, Qwen-Scope SAE transfer),
J-space split planting, majority rating with and without the sibling verbalizers.

## Dataset (dataset/build_dataset_x.py -> items_x.json; dataset/build_x3.py -> items_x3_candidates.json)
- Deterministic from seed 20261008. Item ids prefixed `x` (xown-, xmap-, xlang-, xtense-, xpz-, xch-) so they
  never collide with the G cache. Pair 01 of each family is `dev` (smoke only); the rest `test`.
- Ownership/mapping versions A and B are token permutations of each other (same names/objects/symbols,
  binding swapped), so both renders have the same length; X2 requires equal length and skips otherwise.
- Candidates: (answer, other); the two candidates must have distinct first tokens in every reader format
  (checked on the pod; items failing are dropped and listed in the manifest, never replaced).
- X3 candidates: 400 three/four-step arrow puzzles (symbols A–H, "Start at S and follow the arrows k times");
  300 two-option choice prompts (G6 style, both orders), with the G6 prompt-only template for the self-guess.
- Freeze: sha256 of items_x.json, items_x3_candidates.json and core code recorded in
  manifest/frozen_config_x.json before test collection (same mechanism as BRIEF §freeze).

## X1 endpoints
E1  Per reader x family: paired win rate P(LO(h_A) > LO(h_B)) with LO = lp(answer_A) - lp(other), i.e. the
    reader favours each state's own answer; 95% pair-bootstrap CI (n_boot 2000, seed 0). A reader
    SEPARATES a family if win >= 0.75 and the CI excludes 0.5. J-lens candidates without a single-token
    variant are unscorable and excluded (count reported).
E2  Column (a): leave-one-pair-out diff-in-means probe on the fp32 states; AUROC and paired win on held-out
    pairs; two-half ceiling = direction from half 1 evaluated on half 2 and vice versa (pairs split by seed).
    PRESENT if held-out win >= 0.9.
E3  State-free prior: each reader's LO on the family mean state; must be inside [-1, 1] nats on average
    (sanity, no decision).

## X2 design
Sites (edit layer, positions):  S1 = L38, last token only (Suraj's recipe, our items);
                                S2 = L38, all positions;  S3 = L42, all positions (reader input is the
                                interpolation itself at the last token: the by-construction reference arm).
Edit: h'(pos) = h_A(pos) + alpha * (h_B(pos) - h_A(pos)) at the edit layer during the prefill (and the mirror
from B toward A). Dose ladders: S1 alpha in {0.5, 1, 1.5, 2, 3, 4}; S2, S3 alpha in {0.25, 0.5, 0.75, 1.0}
(alpha = 1 at S2/S3 is the complete swap and must flip; it is the positive control of the arm).
Nulls (same norm as the planted edit at every edited position, random sign): K = 6 isotropic directions per
pair at alpha 1 (S2, S3) and alpha 2 (S1); K = 4 OTHER-PAIR directions (the swap direction of another pair of
the same family, drawn by seed) at S1 alpha 2. Null bands are reported as z, never subtracted.
Recorded per (pair, source state, site, alpha, condition): the model's greedy answer (8 tokens), the model's
first-token answer log-odds lo_model = lp(other) - lp(own answer) at the last prefill position, the block-42
last-token vector after the edit (saved fp16), and each reader's LO on that vector (same sign convention:
positive = toward the planted candidate).
Keep criterion for the model: the greedy answer parses to one of the two candidates (coherence); the
coherence rate per (site, alpha) is reported and arms with coherence < 0.8 are flagged.

## X2 endpoints (per site)
E4  Flip curve: P(answer = other candidate) vs alpha, with Wilson CI; the null flip rate at matched alpha.
E5  Per item minimal flipping dose alpha* (smallest alpha on the ladder whose answer is the other candidate and
    coherent); items with no alpha* are "no flip" and counted.
E6  Reader follow at alpha*: paired win P(reader LO shift toward planted > 0) over items with an alpha*;
    z of the shift against the item's null band. Classification per reader and site (fixed in advance):
      TRACKS      win >= 0.9 at alpha* and null win <= 0.25
      SUB-FLIP    win >= 0.9 already at the largest alpha < alpha* where the model's own lo_model shift is
                  inside its null band (the G5 pattern: reader moves, model does not)
      INSENSITIVE win <= 0.5 at alpha*
      otherwise   MIXED
E7  Gain ratio: slope of reader LO shift vs lo_model shift across the ladder (per site, pair-bootstrap CI).
Primary contrast of the phase: E6 at S2 (L38 all positions), where the reader's input is propagated and not
the edit itself. S3 is expected to show TRACKS/SUB-FLIP by construction and is reported as a reference.
Kill K5: if at S2 fewer than 16 of 64 pairs have an alpha* <= 1 with coherence, the site is not usable and E6
is reported as underpowered (no reader classification).

## X3 design and endpoints
Selection uses the model and the prompt-only arm only, never a reader.
(a) PUZZLES: run the target greedy on all 400; keep items whose parsed answer is a symbol != correct
    (ERROR set, expected 40–120). Candidates = (model's answer, correct). Control = size-matched correct items
    with candidates = (correct, the most frequent wrong answer symbol for that puzzle shape).
(b) CHOICE: run the target greedy on all 300 (actual choice) and the prompt-only self-guess; keep items where
    the self-guess != actual (DISAGREE set, expected 40–90) plus a size-matched AGREE control.
E8  Per reader x set: P(LO favours the model's ACTUAL answer), pair... item-level bootstrap CI. A reader READS
    THE MODEL, NOT THE TEXT if on ERROR and on DISAGREE the rate is >= 0.75 with CI excluding 0.5. Prompt-only
    is 0 on these sets by construction and the text-implied key is the other candidate.
E9  Column (a) on the union of each set and its control: LOO diff-in-means probe predicting the ACTUAL answer;
    held-out win and two-half ceiling as in E2.
Kill K6: if ERROR < 24 or DISAGREE < 24 items, that set is reported descriptively only.

## Blindness map (the deliverable table, results/g_agreement/x/blindness_map.csv + fig_main.png)
Rows: feature classes {language, tense, ownership, mapping, puzzle-error, self-choice}. Columns: PRESENT (E2/E9),
LOAD-BEARING (E4 at S2: flip rate at alpha 1, and alpha* median), REPORTED per reader (E1/E8), FOLLOWS per
reader (E6 at S2). Headline figure: X2 dose-response at S2 — x = alpha / alpha* per item (0..2), y = standardized
LO shift toward the planted candidate, one line per reader with pair-bootstrap bands, the model's own lo_model
as the black reference curve; S1 and S3 as small panels.

## Compute (one pod session, one H100 80 GB)
Phase A (target + OLens + J-lens): X1 capture + LO ~0.2 h; X2 capture (L38/L42 full sequences, 128 states) +
~4,600 edited decodes with L42 capture ~1.0–1.3 h; X2 LO (jlens, olens) ~0.3 h; X3 selection + capture + LO
~0.3 h. Phase B (NLA): all LO ~0.5 h. Budget ~3 pod-hours (~$10.5 at $3.49/h); hard stop at 5 pod-hours.

## Deviations
- 2026-10-07 (pre-data, X2 analysis definitions): (1) E6 "null win" is defined as P(null shift >= the item's planted
  shift at alpha*) over the K nulls (rank form of the z test); the literal P(null shift > 0) is ~0.5 by construction
  (random null sign) and is reported separately as E6_null_shift_positive. (2) SUB-FLIP is tested before TRACKS (a
  reader that already moves below alpha* is labelled SUB-FLIP even if it also wins at alpha*). (3) Full captures and
  read vectors are stored bf16 (lossless w.r.t. the bf16 capture), not fp16.
- 2026-10-07 (pre-data, X1/E2 probe direction): "mean(h_A - h_B)" needs a family-consistent label. Implemented: tense =
  past vs future; ownership = answer-is-first-mentioned vs second (the binding); language and mapping use class-mean
  (candidate identity) directions from the other pairs; held-out pairs whose candidate never appears in the training
  pairs are skipped and counted. Recorded as `probe_type` in e2.csv.
- 2026-10-07 (pre-data, X3 puzzles): the k+1 visited symbols of a puzzle are required to be distinct (implies the two
  pre-registered constraints and makes "most frequent wrong answer" well defined).
