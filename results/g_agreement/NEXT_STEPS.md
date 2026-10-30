# Next steps after Phase X (written 2026-10-08, from three independent reviews + raw-row checks)

Inputs: `writeup.md` (G1–G6, Phase X, and the 2026-10-08 Corrections), `direction_review.md`, `BRIEF_X.md`.
Three reviewers (methodological critic, experiment designer, strategy/presentation) worked independently;
their raw reports are summarised here, not reproduced. Numbers quoted below were re-checked on the raw rows.

## 0. Where we actually are (after corrections)

Established:
- Scored by native log-odds, all three readers carry the bindings that free text never named
  (J-lens 85/94%, Oracle 83/87%, NLA 72/72% on ownership/mapping, n = 47 pairs). J-lens and Oracle beat NLA on
  the same pairs (paired sign test p ≤ 0.004). G1–G2's "blind to bindings" was an elicitation artefact.
- The last-token block-38 vector is inert (0/128 flips up to α 3); the all-position state at L38 flips the
  answer in 98% of states by α 0.75 (isotropic nulls 0/768).
Not established (and previously overstated):
- "Readers follow the sign but not the magnitude": a scale artefact. Normalised by each reader's own natural
  separation, the shift is 0.23 / 0.50 / 0.77 / 1.00 along the ladder for every reader. E6 restates X1.
- "The model's off-text answer is absent at the site": 267/297 puzzle errors are on-trace ("stop one step
  early"), the probe tested correctness not identity, and symbol priors contaminate E8. Open question.
- "Readers beat the probe on mapping": the identity probe is the weak instrument.
- The ownership probe label is mention order, so binding and order are confounded in that bank.

Thesis going forward (one sentence): at a fixed site the readers behave as one instrument reporting what is
linearly present there, so a reader's value is decided by site and scoring format, not by which reader you pick;
the project now looks for a site where a load-bearing, off-text fact is present and asks who reports it.
Drop "disagreement as signal": the readers agreed on every class a probe saw and failed together elsewhere.

## 1. Friday deliverable (2026-10-10), CPU only, from existing artefacts

Mandatory re-analyses (each changes a claim if it goes the other way):
R1. X2 renormalised: reader shift / own natural separation per dose; win at α* conditional on natural ordering;
    model sub-flip sign-win. Replace the y-axis of `x2/fig_main.png` (currently null SD) with this fraction.
R2. Fair binding probes on the cached L42 states (`cache/g_agreement/x/full`, `states/x*.pt`): within-pair
    contrast probe and LOO multinomial logistic over symbols for mapping; W_U-projection baseline. If ≥ 0.9 the
    map's "inversion" disappears; if it still fails while J-lens scores 94%, the probe code is wrong.
R3. X3 re-analysis: symbol-bias-corrected E8 with controls as reference; an 8-way identity probe for the
    actual symbol on the 400 cached states (logistic, 5-fold by item, permutation null); trace-rule text
    baseline; re-define ERROR as off-trace items (n ≈ 30, descriptive only).
R4. Paired reader comparisons (sign tests on identical pairs) instead of per-reader CIs against the 0.75 bar;
    mark the four untested LOAD-BEARING cells explicitly in `x/fig_main.png`.
Worked material (Y0): `x/friday_cases.md` with all 33 DISAGREE items and the 30 off-trace ERROR items (prompt,
actual, text key, self-guess, model first-token margin, each reader's LO); `x2/per_pair.csv` (64 rows: α*,
model shift, reader fractions at α* and sub-flip); the S1 other-pair rows tabulated as a free preview of Y2;
shared-error check (how often all three readers favour the same wrong candidate).
One-page outline for Agam/Neel: scope first (SAEs, Skip Lens, "non-workspace" untested; assets located),
headline = blindness map with the corrected reading, method result = native LO vs free text, causal result =
flip curves with the continuity caveat stated in the same sentence, negatives as results, next steps, and three
questions: (i) judge readers at their training site only, or wherever the fact is load-bearing? (ii) which
operational definition of "non-workspace" (J-space complement at r*, or behavioural)? (iii) ground truth =
best linear probe, or causal flip only?

## 2. Two-week programme (ranked by information per pod-hour; ≈ 2.5–3 pod-h total, hard stop 6)

Y1. Site search for the model's actual answer (≈ 0.6 h). Extend the choice pool by ~900 prompts so DISAGREE
    reaches ~100; capture layers 42…62 step 2 × positions {last … last−11, candidate-token positions} on the
    X3 sets; logistic L2 probe, 5-fold by item, permutation null, two-half ceiling; logit-lens margin per layer
    as the "trivially expected" reference. S* = earliest (layer, position) with win ≥ 0.75 above the majority
    rate. Re-read at S*: J-lens natively per layer; Oracle only on its training grid {44, 48, …}; NLA is
    L42-only, so off-layer use is a transfer test gated by its state-free prior (E3) and labelled as such;
    add the Karvonen activation oracle at L48 as the on-grid verbalizer. Extends `x3_floor/collect.py`.
Y2. Identity-free nulls at the causal site S2 (≈ 0.5 h): other-pair position-wise Δ (equal-length same-family
    pair), name-removed Δ (candidate identity directions projected out; two definitions: held-out diff-in-means
    over X1 pairs, and the J-lens pullback), name-only component. Decision: readers read the binding if the
    model still flips under name-removed Δ and reader win ≥ 0.75 there; readers read the name if win ≥ 0.75
    under name-only and ≤ 0.5 under name-removed; if the model does not flip under name-removed, the question
    is ill-posed at this site. Also crosses mention order with binding in a new ownership sub-bank (control 4
    of the critic). Extends `core/edit.py` condition tables, `x2_causal/collect.py`.
Y3. New reader families in the same LO harness (≈ 0.5 h): skip-lens arms A and D (`ceselder/skip-lens-qwen36-
    27b-agreelens-{a,d}`, LoRA on the target base, same ㈜ injection as the NLA, so they load in phase A);
    R-lens from `camilablank/workspace-lenses` (zero cost in `lo_jlens`); Qwen-Scope L42 SAE transfer test
    (FVE vs shuffled-decoder null, 0.1 h; only if FVE ≥ 0.5 does a sparse latent probe become a column).
    Entry gate: X1 E1 ≥ 0.75 on both binding families and E3 within ±1 nat. This answers the untested half of
    the prompt and adds a non-sibling reader besides the probe.
Y4. Stronger PRESENT column (CPU first; +0.1 h at S*): logistic L2, standardised, inner-CV C, grouped folds,
    20-permutation null, two-half ceiling; mapping gets an 8-way symbol probe and a structural (trace-position)
    probe. PRESENT if CV win ≥ 0.75, above the permutation 95th percentile, and ceiling ≥ 0.75.
Y5. J-space split at S2 (≈ 0.5 h): basis from Suraj's `src/mats/jspace.py` at L38 (r* = 192 and 384);
    plant Δ_J and Δ_⊥ separately with equal-rank random-subspace controls. "Reads non-J content" if win ≥ 0.75
    under Δ_⊥ while J-lens stays inside its band; "J-space leak" if readers follow Δ_J and the model does not
    flip. This is the only arm that can answer the "non-workspace" clause directly.
Schedule: Fri R1–R4 + Y0 + Y4-CPU; Mon pod session 1 = Y1 + Y3 + Y4 at S* (≈ 50 min); Wed session 2 = Y2 + Y5
+ NLA phase B (≈ 45 min); week 2 analysis, headline figure, write-up.

Headline figure for the phase: left, a site map (layers × pre-answer positions, cell = held-out probe win for the
model's actual answer on the off-text sets, S* marked, each applicable reader's rate printed at S*); right, at
S2, model flip rate and each reader's follow rate under full Δ, name-removed, name-only, Δ_J, Δ_⊥, other-pair.

Kill criterion for the direction: stop and write the negative result if (i) Y1 finds no (layer ≤ 58, position)
where the model's actual off-text answer is linearly present (win ≥ 0.75 above the permutation null), or (ii) a
site exists but every applicable reader sits inside its null band there and, in Y2, the readers follow the
name-only component as well as the full swap. Either way "some readers find what others miss" has no positive
instance in this model and item family, and the remaining budget goes to the write-up.

## 3. What a sceptical mentor will push on first, and the answer

1. "Following at S2 is by construction." Agreed; reported as proportional following implied by X1; Y2 is the
   missing control.
2. "Your mapping probe is weak." Agreed; R2/Y4 replace it before any reader-vs-probe claim.
3. "NLA and Oracle share a base; agreement is shared training." Majority rating was dropped for that reason;
   the probe and the new families (Y3) are the non-sibling references.
4. "You picked a site where nothing off-text lives." Possibly; S1 inertness is established, Y1 is the test, and
   the standing caveats are synthetic prompts, rule-based keys, 136 blind rows unadjudicated.

## 4. Division of labour (one document, one map)

Guiv: document skeleton, R1–R4, Y0, Y1, Y2, Y3(a–c), Y4; owns `x/blindness_map.csv` and the two figures.
Suraj: a "J-space and non-workspace" section in the same map format: J-space basis and the Δ_J / Δ_⊥ plant (Y5),
his L38 planting recipe as the reference for S1/S2, the col-wrap re-derivation as the one non-workspace row with
a behavioural key (newline log-odds), the Qwen-Scope SAE transfer test (Y3d). He adds rows and columns to the
same CSV, never a second table; conventions already match (block-42 = hidden_states[43], same reader ids,
same bootstrap). Merge Thursday evening so Friday's summary is one page, one map, one dose-response figure.

## 5. After Phase W/V (written 2026-10-12; see w/summary.md, v/summary.md)

Where we are: H-W (class-mean readers) is not supported as stated, but every lens shares the probe-direction blind
spot and follows unused class-mean-like components; readers trained at 52+ do read the model's wrong answer (V1);
eight-way mapping and counts show the native vectors carry contrasts, not values (W2); target-private facts are
readable at 81–100 % in a 16-pair pilot (V7).

Ranked next steps (pod time in brackets):
1. ~~V7 confirmatory, 48 pairs~~ **DONE 2026-10-12 12:00 UTC: all four cells confirmed** (`v/v7c.md`). Follow-ups it opens: the
   mention-order effect (second-mentioned holder read better by every lens) and the system-turn advantage (J-lens, Oracle,
   NLA) are both unplanned findings; a 48-pair replication with order and role as pre-registered primaries would make them
   claims. Also worth one run: a fact the model *disagrees* with (preamble contradicts world knowledge) to separate
   "reads the context" from "reads the model's belief".
2. **Eight-way scoring of the existing two-way banks** [≈ 15 min]: the G1/X1 mapping wins (85–94 %) must be
   re-scored with the full candidate set, since W2 shows 12–21 % on mapping-8. If the two-way result does not
   survive, the native-scoring numbers across G/X/Y/Z need an "among two candidates" qualifier everywhere.
3. **S4 free-text sampling** [≈ 30 min]: 24 error + 12 counts states × 8 samples × Oracle/NLA + 10 random, as
   shrunk; closes W3/W4 (pre-registered thresholds still unevaluated) and the NLA counts column of W2.
4. **Readers trained at 52–56 on the error set** [≈ 20 min + lens fits]: V1 puts the crossing at 52; a J-lens/Oracle
   fit there, compared with the probe at 52 (92 %), tests "lag, not blindness" directly.
5. **Probe-direction follow as a reader diagnostic** [CPU]: d_pw moved no lens in any family; report the random band
   and the fraction-of-own-separation columns as the standard reader check in the write-up and ask Suraj whether
   the J-space planting recipe shows the same.
Not worth more pod time now: window readers (V5 NOT MET twice), post-statement-span Oracle (V6 NOT MET), the
V3 sensitivity proxy (needs per-state control readouts Michael has not released; ask him, `v/for_michael.md`).
