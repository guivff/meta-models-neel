# Answers to six reviewer questions — g_agreement (compiled 2026-10-13 from existing files; no new runs)

Paths are relative to the repo root. `cache/` is not in this branch; where a raw file lives there, the relevant text is
quoted here and the result files that summarise it are listed. All pods are stopped; this copy of `results/g_agreement/`
was synced from the pod after each session.

## (a) V5b off-grid check: Oracle Lens at layers 40 / 42 / 44 on the 8 dev states

**Run: yes. Written coverage table: no. Layer 42 is not degenerate.**

- Design: `projects/g_agreement/BRIEF.md:26-28` (if 42's coverage is lower by ≥ 4/8, every Oracle figure carries the
  off-grid caveat; 42 stays primary either way).
- Collection ran on the pod 2026-10-07: `results/g_agreement/g1/log.md` lines 1, 8, 9 (phase A "offgrid=True"; the
  layer-40 and layer-44 runs, 8 calls each); raw generations in `results/g_agreement/dev_collection2.log:33-48`.
- No analysis script wrote a 40/42/44 table. The only written verdict is `results/g_agreement/writeup.md:59-60`:
  "the Oracle lens is off its training grid at layer 42 (dev shows 40/44 behave alike)".
- Coverage tallied now from the scored claim rows `results/g_agreement/claims/g1.jsonl` (lines 33-40 L42, 41-48 L40,
  49-56 L44; covered = rule-v1 status supports or contradicts):

| item | L42 | L40 | L44 |
|---|---|---|---|
| lang-01A/B, tense-01A/B | covered, all correct | covered, all correct | covered, all correct |
| own-01A/B | unclear | unclear | unclear |
| map-01A (key D) | self_contradictory | contradicts (C) | contradicts (C) |
| map-01B (key C) | supports | self_contradictory | supports |
| **coverage** | **5/8** | **5/8** | **6/8** |
| correct among covered | 5/5 | 4/5 | 5/6 |

The L42 value matches `results/g_agreement/g1/dev/summary.json` (per_method.olens.coverage k 5, n 8, pair-bootstrap
CI [0.25, 1.0]). Difference from 42 is at most 1/8, far from the ≥ 4/8 trigger. Caveats: one sample per state, n = 8,
rule-v1 extraction, no CIs for 40/44, the differences sit entirely in the two mapping states.

## (b) Y2 identity-free nulls at α = 1 (edits at L38)

Arms: `name_only` edits only the name/symbol tokens; `name_removed` edits every other position (question, template and
punctuation together; 32.6 positions on average in ownership, `results/g_agreement/z4b/z4b.md`). "Template tokens
only" is a separate Z4b arm (ownership only).

Pooled over both families (`results/g_agreement/y2/flips.csv`, Wilson; `y2/summary.json` E13_follow, pair bootstrap):

| arm | model flips | Oracle follow | NLA follow | J-lens follow |
|---|---|---|---|---|
| name_only | 61/128 = 47.7% [39.2, 56.3] | 68.8% [60.1, 77.3] | 69.5% [61.7, 77.3] | 70.3% [61.7, 78.9] |
| name_removed | 64/128 = 50.0% [41.5, 58.5] | 78.1% [68.8, 87.5] | 68.8% [57.0, 79.7] | 75.0% [64.8, 85.2] |
| full | 126/128 = 98.4% [94.5, 99.6] | — | — | — |

Per family (model flips `results/g_agreement/z4/z4.md` lines 62/64 and 117/119; reader rates `writeup.md:395-408`,
CIs recomputed from `y2/follow.csv`, 2,000 pair resamples):

| family / arm | model flip | Oracle | NLA | J-lens |
|---|---|---|---|---|
| mapping / name_only | 61/64 = 95% [87, 98] | 95% [88, 100] | 89% [81, 95] | 98% [95, 100] |
| mapping / name_removed | 0/64 = 0% [0, 6] | 67% [52, 81] | 67% [52, 83] | 56% [39, 72] |
| ownership / name_only | 0/64 = 0% [0, 6] | 42% [33, 52] | 50% [39, 61] | 42% [31, 53] |
| ownership / name_removed | 64/64 = 100% [94, 100] | 89% [78, 98] | 70% [55, 84] | 94% [84, 100] |

**On the quoted sentence** (`projects/g_agreement/manifest/brief_wv.md:21`: "J-space component, template tokens: 0–11%
model flips vs 78–95% reader follow"). It is about two other edits, not the name_only / name_removed nulls:
- J-space component (Y2 J_only, α 1): model flips mapping 5/64 = 8%, ownership 0/64, pooled 3.9% [1.7, 8.8]
  (`y2/flips.csv`); reader follow per family 78–92% (`writeup.md:401,407,415`); pooled Oracle 87.5%, NLA 81.3%,
  J-lens 82.0% (`y2/summary.json`).
- Template tokens only (Z4b, ownership, n = 64): model flips 7/64 = 11% [5, 21] (`results/g_agreement/z4b/z4b.md`).
  The "91 / 95%" follow for Oracle / J-lens exists only as hard-coded numbers in `results/g_agreement/z/make_fig_headline.py`
  and `z/fig_headline_readers_vs_model.csv`; `z4b.md` and `z4b_summary.json` report fraction-of-separation instead
  (Oracle +0.85 [0.81, 0.89], J-lens +0.77 [0.55, 0.94]). No result file holds a CI for the 91/95 win rates.

Correction: the sentence holds for the J-space and template-only edits (with the CI gap noted), but the identity-free
nulls behave differently: at α 1 they flip the model 0% or 95–100% depending on the family, and where the model does
not flip the readers follow weakly (ownership name_only 42–50%, chance; mapping name_removed 56–67%). Phase W
(`results/g_agreement/w/w1/w1.md`) replicates the J-space point with pre-registered directions: ownership d_J flips
0%, readers follow 80–94%.

## (c) Y1 site search: what was completed, and the numbers at 48:last

- Captures (pod, 2026-10-08 23:23–23:26 UTC): 730 items, layers 42–62 step 2 (11) × positions last…last−11 plus
  candA/candB (14) — `results/g_agreement/y1/log.md`, `results/g_agreement/log.md:29`.
- Full probe sweep on the pod: abandoned (BLAS oversubscription, ~7–8 h, killed 07:00 UTC, no output;
  `projects/g_agreement/BRIEF_Y.md:99-107`).
- Full sweep run locally on the Mac: all 308 cells (11 × 14 × 2 sets), 10 permutations, "308 computed, 0 failed"
  (`results/g_agreement/y1/run_full_local.log`); outputs `y1/sweep_error.csv` (154 rows), `y1/sweep_disagree.csv`,
  `y1/summary.json`.
- Reduced local run (positions last, last−1, last−2, candA, candB × 11 layers, 2 permutations): `y1/local_reduced/`;
  this is the run the S* decision cites (`BRIEF_Y.md:106-107`). Rates are identical to the full sweep; only the
  permutation p95 and bootstrap CIs differ slightly.
- Reader re-reads on the pod (07:05–07:37 UTC): only at 48:last and 42:candA — `y1/reread.csv`, `y1/candA_reference/`.

Probe at 48:last, puzzle errors (n = 297), `y1/sweep_error.csv` row "48,0": 234/297 = **78.8%**, bootstrap
[74.1, 83.2], Wilson [73.8, 83.1], permutation p95 0.626, majority 0.684, passes. Other layers at the last token:
L42 69.0% [63.6, 74.1] (fails), L44 73.4%, L46 72.7%, L50 78.5%, L52 91.9% [88.9, 94.9], L56 93.6%, L62 93.9%.
On self-choice disagreements: 0/154 cells pass.

Readers at 48:last (`y1/reread.csv`, set error, n = 297): J-lens (native L48) 123/297 = **41.4%** [35.7, 47.1];
Oracle (grid layer 48) 145/297 = **48.8%** [42.8, 54.2]; NLA (transferred from L42) 168/297 = **56.6%**
[50.5, 62.0]; controls 81.6 / 77.7 / 57.3%. All three verdicts "no_evidence".

V1 layer sweep (`results/g_agreement/v/v1.md`, `v1.csv`; L42 from the X3 capture, L48 from Y1, L44/46/50–62 from the
W-session pod run): J-lens 57.2 / 58.2 / 54.5 / 41.4 / 48.8% at L42–50, then 77.1% [73, 82] at L52 up to 82.5% at
L58/62; Oracle 44.8–49.5% at L42–50, then 81.5% [77, 86] at L52 up to 86.2% at L60. Rule: probe first ≥ 0.75 at
L48; J-lens and Oracle first cross at **L52**, a four-layer lag. NLA only at L42 (58.9%) and L48 (56.6%); its layer
arm was not run.

Check against the expected summary: "probe at 48:last ~79%" confirmed; "J-lens/Oracle 41–57% at 42–48" is the
three readers at the single site 48:last (41 / 49 / 57); across L42–48 the J-lens spans 41–58% and the Oracle 45–49%;
"77–86% from 52" confirmed (J-lens 77–83%, Oracle 82–86%).

Caveats: the pre-answer-position restriction for S* was post hoc (`BRIEF_Y.md:101-107`); load-bearing at 48:last is
untested (`writeup.md:292`); `x/blindness_map.csv` is keyed by feature class and holds no Y1 layer × position rows.

## (d) G1 consensus: states where ≥ 2 readers assert the same wrong candidate

**None.** `results/g_agreement/g1/consensus.json` (test split, 32 states): `n_shared_wrong` = 0 in all four families
(language, mapping, ownership, tense); unresolved = 15 all-abstain + 1 tie; consensus-2 correct on 16/16 covered
states, consensus-3 on 5/5. `g1/dev/consensus.json` (8 states): also 0 shared-wrong. `writeup.md:23`: "No shared wrong
answers." Per-readout votes: `results/g_agreement/claims/g1.jsonl` (256 rows, rule-v1).

The only wrong votes among all 40 G1 states:
1. **map-03A (test), the tie.** Prompt "wolf maps to fox. fox maps to owl. owl maps to bear. Begin at fox and apply the
   mapping two times. Which one do you reach? Reply with one word." Key bear; model "bear". NLA = bear, Oracle = wolf,
   J-lens abstains. Raw readouts are in (e) below.
2. **map-01A (dev), one wrong vote.** Prompt "A → B. B → D. C → A. Start at A and follow the arrows twice…" Key D; model
   "D". NLA = C (rule-v1 picked a chain arrow from an invented chain "A→B→C→A"; the text itself concludes "A"),
   Oracle self-contradictory, J-lens abstains.

In G1 the readers fail together by abstaining (ownership 0/8 covered, mapping 1/8), not by agreeing on a wrong
answer. The shared-wrong excess reported in the project comes from native log-odds scoring on the model's own
errors, not from G1 free text: X6 17.5% vs 9.2% independence (`writeup.md:260`), Z2 17.8% vs 8.7% (`writeup.md:342`).

## (e) Side-by-side raw readouts (3 G1 states) and X2 free text

Raw readouts: `cache/g_agreement/gens/g1.jsonl` (256 rows; NLA and Oracle text in `raw_output`; J-lens has no text,
its readout is a top-10 token list). Rendered examples already in this branch: `results/g_agreement/g1/examples.md`;
claim-level text (NLA, Oracle): `results/g_agreement/w/claims/claims_g1.jsonl`. Readouts truncated below.

**1. Agreement — lang-02A.** Prompt "What is the opposite of 'hot'? (Answer in Spanish, one word.)" Key Spanish;
model "frío".
- NLA: `<explanation> Q&A format pattern: structured question-and-answer pair in English, now delivering a
  Spanish-language direct answer. "What is the Spanish word for cold? Answer in one word" sets expectation. The
  response must be a single Spanish word translating "cold," … Final token "Respuesta:\n" is a labeled answer field…`
- Oracle: `- Frío\n- Frío\n- Frío (This is the single most common Spanish word for "cold" and the most direct
  translation)\n\n- Frío … The Spanish word for "cold" is "frío."`
- J-lens top-10: 합니다 7.50, 입니다 7.09, 하다 6.66, します 6.51, " está" 6.34, " 번역" 6.27, " español" 6.26,
  西班牙语 6.15, 这个词 6.14, 한다 6.11.

**2. Disagreement — map-03A** (the tie above). Key bear; model "bear".
- NLA: `… The chain "lion → tiger → bear → mouse → lion" logic has been applied twice (each step down one), so the
  final result is "bear," already confirmed by the reasoning prompt. …` (right word, invented chain)
- Oracle: `- wolf\n- bear (Explanation: After two applications of "becomes", you land on wolf.)\n\n- bear  #
  Explanation: Snake -> Frog -> Bear (3 steps)\n\n- Bear** (or **Death** if counting 3 hops from Wolf) …` (first
  bullet wolf, which rule-v1 scored)
- J-lens top-10: 합니다 4.83, holen 4.33, します 4.30, 네요 4.27, 한다 4.17, 입니다 4.13, " Kết" 4.06, になります
  4.05, " getResult" 4.04, "\n×14" 3.98.

**3. Majority wrong — no such G1 state exists.** Closest: map-01A (dev), one wrong vote. Key D; model "D".
- NLA: `… The diagram defines a function chain A→B→C→A. The question asks for the result after applying f three
  times: A→B, B→C, C→A, making "A" the expected answer. …`
- Oracle: `- B\n- C\n- C\n- D\n- B  *(Explanation: The result after three steps from A is D)*\n\n- C  *(Note: After
  three applications, you end up at C)* …`
- J-lens top-10: " END" 4.72, 终点 4.60, " FINAL" 4.56, 的最终 4.51, _final 4.46, "\n×32" 4.31, final 4.28, "(end"
  4.22, END 4.21, 目的地 4.17.

All-abstain example — own-02A: prompt "Elif carries the rope and Jonas carries the lantern. Who carries the lantern?
Name only." Key Jonas. NLA invents "Alex" ("Who sits first"); Oracle lists "Alice", "John"; J-lens top-10 is
" prénom", FirstName, " LastName", =name, … " Elon".

**X2 free text: none exists; your belief is correct.** `projects/g_agreement/BRIEF_X.md:6-7` and `writeup.md:134`:
"All reader scoring in this phase is native log-odds; free text is not scored." X2 files (`cache/g_agreement/x/`):
`x2_lo.jsonl` 14,208 rows (4,736 per reader; lo_own, lp_A, lp_B, templates — no text field), `x2_behaviour.jsonl`
4,736 rows (the target model's own edited decodes, not reader readouts), `x2_readvecs/` 4,736 .pt vectors. Results:
`results/g_agreement/x2/{flips.csv, follow.csv, per_pair.csv, summary.json}`. The only reader free text in the repo is
in `cache/g_agreement/gens/{g1,g3,g4,g5,g6,g6_prompt_only}.jsonl` and `results/g_agreement/claims/g1_sheet.jsonl`;
none covers the X-bank items.

## (f) Judged confabulated claims (W claims; V3)

Judge `google/gemini-3.8-flash` (OpenRouter, temperature 0, strict JSON), adapted from Michael Kenney's
`claim_judge.py`; labels input_true/false, computation_true/false, unverifiable. Files
`results/g_agreement/w/claims/claims_g1.jsonl` (404 claims, 32 states × 2 readers) and `claims_g4.jsonl` (214).
Second judge `anthropic/claude-sonnet-5.5` on 100 computation claims: true/false κ 0.86 [0.75, 0.95]
(`W3_g1.md`). Human labels: sheet `results/g_agreement/v/human_labels.csv` (300 rows) is not yet filled (0/300), so
no human κ exists.

Five examples (all genuine condition, sample 0; `truth: false`):

1. **NLA, input_false** — `g1|nla|lang-04B|s0#5`. Prompt "What colour is fresh snow? Please respond in French, one word
   only." Actual "Blanc". Claim: "The prompt contains 'Quelle est la couleur du sang humain ?'." Evidence: "Human blood
   question is not in prompt."
2. **NLA, input_false** — `g1|nla|tense-02A|s0#0`. Prompt "Make up one sentence (under ten words) about what the football
   team did in the kitchen yesterday." Actual "The team cooked dinner in the kitchen." Claim: "The prompt asks for a
   seven-word sentence about the cat eating Thanksgiving dinner yesterday." Evidence: "Prompt asks about football team
   in kitchen." (Same readout: "The answer must be exactly seven words." → input_false.)
3. **NLA, computation_false** — `g1|nla|own-03A|s0#4`. Prompt "Kenji is holding the wallet, and Farah is holding the
   ticket. Who is holding the ticket? Reply with the name only." Actual "Farah". Claim: "The next token is constrained
   to be the name 'Bob'." Evidence: "Actual answer is Farah." Second judge agrees (`relabel_g1.jsonl`).
4. **Oracle, input_false** — `g1|olens|own-02B|s0#6`. Prompt "Elif carries the lantern and Jonas carries the rope. Who
   carries the lantern? Name only." Actual "Elif". Claim: "The prompt asks only for the name of the person who does not
   like coffee." Evidence: "Prompt mentions lantern and rope, not coffee". (Same readout: "The answer is Anna." /
   "John." / "Alice is the answer." → computation_false.)
5. **Oracle, computation_false** — `g1|olens|lang-04A|s0#1`. Prompt "What colour is fresh snow? Please respond in
   Portuguese, one word only." Actual "Branco". Claim: "The reply is 'Vermelho'." Evidence: "Model's actual answer is
   'Branco'". Second judge agrees.

Counts by judge label (tallied from the two files):

| file | reader | input_true | input_false | comp_true | comp_false | unverifiable |
|---|---|---|---|---|---|---|
| claims_g1 | NLA | 51 | 135 | 25 | 29 | 2 |
| claims_g1 | Oracle | 17 | 26 | 39 | 74 | 6 |
| claims_g4 | NLA | 23 | 70 | 10 | 14 | 1 |
| claims_g4 | Oracle | 12 | 20 | 25 | 37 | 2 |

Precision (`W3_g1.md`): NLA input 27% [23, 32], computation 46% [32, 59]; Oracle input 40% [27, 53], computation
35% [20, 50]; readouts with ≥ 1 false claim: NLA 100%, Oracle 78%. Patterns: the NLA invents prompt scaffolding
("Final token is 'Answer:\n'", table headers like 'Cevap:'); the Oracle emits placeholder names (Alice, John, Bob).

Two from Michael Kenney's released data (his judge; `nla-consistency/data/claims/`, re-analysed in
`results/g_agreement/v/v3_claims.csv`): `multihop|atomic-79-symbol|2` "The text features the atomic number '29'." →
contradicted ("source specifies atomic number 79"); `typo|typo-February|9` "The phrase 'Last month has a birthday are
born in the end of Febuary' is typo-ridden." → invented_content ("invented example sentence"). Label totals on his
4,190 claims: workspace 1281, misquote 1081, background_true 854, contradicted 514, unverifiable 289,
invented_content 171 (`v3.md`).
