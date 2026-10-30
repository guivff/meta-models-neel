# G1–G4 pilot: what three activation readers agree on, and whether agreement adds reliability

Run 2026-10-07 on Qwen3.6-27B, block-42 output at the pre-answer token, 32 test states (16 pairs,
4 families), readers NLA (iter 400), Oracle lens (s3d_rl600), J-lens (neuronpedia n1000, cosine).
Pre-registration: `projects/g_agreement/BRIEF.md` (deviations listed there; all pre-freeze except
analysis-loader fixes). Labels: rule-v1 extractor, hand spot-checked on dev only; no human
validation of test labels. Unit of inference: base pair; CIs = pair bootstrap. n is small: single
rates are known to ±15–25 points, so nothing below is a ranking of readers.

**Setup reproduced (R0).** Layer convention: block-42 median cosine 0.9999 / mean rel-L2 0.025 to the
64 shipped NLA activations (Suraj: 0.9999 / 0.026; blocks 41/43 ≈ 0.98 / 0.22). WorkspaceBench
`typo_mt` at layer 42, regex-scored, n = 100: Oracle lens 0.71 (Suraj 0.76 [0.68, 0.84]), NLA 0.71
(Suraj 0.73 [0.64, 0.81]). Adapters live, inputs dumped (`results/g_agreement/repro/`). Target model:
31/32 test answers parseable, 31/31 correct.

**G1 — agreement map (`g1/fig_main.png`).** Coverage: NLA 17/32, Oracle 17/32, J-lens 5/32; accuracy
among covered: 17/17, 16/17, 5/5; consistency with the target's own answer 16/16, 15/16, 5/5.
Coverage is entirely family-driven: both verbalizers assert the requested **language 8/8** and
**tense 8/8**, and abstain on **ownership 0/8** and **mapping 1/8** (the Oracle's one mapping vote is
wrong). J-lens: language 2/8, tense 3/8, otherwise nothing; its noise ceiling is 0/32 on random and
mean inputs, so its 5 hits are not chance. Pairwise: NLA–Oracle agree 16/32, contradict 1/32,
κ 0.88 [0.56, 1.00]; every J-lens vote agrees with both verbalizers (5/5). All-three agreement 5/32.
No shared wrong answers. **Primary contrast:** consensus-2 vs best single reader on the same 16
covered states: 16/16 vs 16/16, difference 0 pp [0, 0]; consensus-3: 5/5 vs 5/5. Verdict per the
brief: agreement adds no measurable reliability over the best single reader at this n; the readers
never disagree where they both speak, and where they fail they fail together by abstaining.

**G2 — relations (`g2/fig_main.png`).** On the 16 ownership + mapping states, no reader names a single
prompt entity (0/16 each), binds a relation (0/16) or tracks the swap across a pair (0/8). The
readouts describe the *kind* of prompt ("a name is requested", "a two-step symbol puzzle") with
invented fillers ("Alice", "John", "A→B→C"); the Oracle's single mapping assertion is a wrong symbol.
So, in this setting, topic/format agreement is high and relational agreement is absent, with no
reader even reaching the "keywords only" level.

**G3 — activation dependence (`g3/fig_main.png`).** Genuine vs cached-readout reassignment (not a
fresh intervention): recipient-scored accuracy drops from 17/32 to 4/32 (NLA), 16/32 to 4/32 (Oracle),
5/32 to 1/32 (J-lens), while donor-scored accuracy equals the genuine rate (17, 16, 5/32). The 4/32
equals the rate at which donor and recipient keys coincide, i.e. the readouts track the donor state
exactly on what they read. State-free control (mean dev activation): 4/32 and 3/32 with coverage
7/32 — the readers' default guesses occasionally land on a key by chance. Prompt-only (base model,
question + prompt text): 32/32. Reading: on language and tense the readouts are activation-dependent
and not a shared default guess, but everything they recover is trivially recoverable from the prompt.

**G4 — repeats (feasibility pilot, 8 states, `g4/fig_main.png`).** On the preselected pair per
family: all three NLA samples and all three Oracle samples vote on the same 4/8 states (language and
tense) and agree 4/4 each time; J-lens votes on 0/8; cross-method 2-of-3 = 4/4 at the same coverage.
Within-reader resampling is perfectly self-consistent here, so cross-method agreement cannot add
anything at matched coverage; compute per state: NLA 3 samples 70 s / 549 tokens, Oracle 32 s / 258,
cross-method 32 s / 266. Eight states settle nothing beyond this.

**What changed our view.** The headline is not disagreement but *shared silence*: the verbalizers
agree (κ 0.88) exactly on the properties a text-only model recovers from the prompt (language,
tense), and both abstain or confabulate on the bindings (who has what, which symbol follows). The
NLA's "prompt reconstruction" rewrites the specifics every time. The question "does agreement add
reliability" has, at n = 16 pairs, the answer "no measurable gain", with the caveat that the covered
set is saturated at 100% accuracy, leaving no room for a difference.

**Uncertain / limits.** Rule-based labels only (one language item's J-lens evidence relies on the
Chinese language name); 16 pairs; the Oracle lens is off its training grid at layer 42 (dev shows
40/44 behave alike); the shuffled arm reuses cached text; no human adjudication of test claims yet
(blind sheet: `claims/g1_sheet.jsonl`, 136 rows). The column-wrapping reproduction was not attempted.

**Next experiment.** Make the bindings carry the answer *inside* the state while keeping the prompt
fixed: Suraj's planted-intermediate style swap on ownership/mapping items (edit which name is bound
to the asked object), and ask whether any reader follows the edit. Add a tense/language item set
where the prompt does NOT state the property (e.g. inferred from an earlier turn) so prompt-only
drops below 100% and reader value can show. Budget: 24 pairs × 2 readers ≈ 100 generations.

Compute: pod wall ≈ 2.2 h on one H100 (≈ $7.7), logged GPU work 1.41 h, 408 generations, 0
truncations at the frozen 256-token verbalizer cap; downloads 115 GB (~10 min).

---
# Follow-up (same day): G5 planted binding swap, G6 self-choice family

Pre-registration: `projects/g_agreement/BRIEF_G5G6.md`. Pod `mats-minis-e`, 14:05–15:01 UTC
(≈ 1 pod-hour, ≈ $3.5): 1,248 teacher-forced log-odds rows, 416 edited-state decodes, 32 free
readouts (G5); 16 captures + 16 targets + 48 readouts + 16 prompt-only + 32 state-free + 32 null (G6).

**G5 (`g5/fig_main.png`).** Setting: the 8 ownership + mapping test pairs; each state's block-42
vector is moved along its own pair direction u = unit(h_B − h_A) with the prompt fixed; readers score
paired log-odds (LO) in their native format (Oracle: "- Name" bullets; NLA: two explanation-register
templates; J-lens: single-token variants). K = 20 random directions per pair at the same norm give the
null band.
- *E3 manipulation check (pre-registered gate): failed.* Replacing the last-token block-42 output and
  letting the model continue flips its one-word answer in 0/16 states at α = 0.5, 1.0, 1.5 (0/320 null).
  At α = 1 the last-token vector IS the other state's vector and the answer still does not change, so
  the answer is reconstructed downstream from the untouched earlier positions. Exploratory ladder
  (labelled, not an endpoint): α = 3 → 0/16, α = 5 → 2/16. By the pre-registered rule nothing is
  concluded about readers "following" the binding; the rest is descriptive.
- *E1 natural separation (pre-registered, independent of the edit):* the Oracle lens's native LO
  orders the two natural states of every pair correctly (paired win 8/8; AUROC 0.72 [0.66, 0.91] over
  16 states); the NLA 7/8 (AUROC 0.62 [0.52, 0.80]); the J-lens 2/4 scorable pairs (AUROC 0.50; the
  nonsense symbols and most names are not single tokens: 192 unscorable rows). So the binding IS
  linearly present in the verbalizers' native scores even though their free text never named it (G2).
- *LO response to the edit (descriptive):* mean shift toward the planted candidate, Oracle lens
  +1.5 / +3.0 / +4.3 nats at α = 0.5 / 1 / 1.5 (positive in 16/16 at every dose; per-state z ≥ 3 vs
  its own 20 nulls in 12/16 at α = 1; null band 0.01 ± 0.46, null follow 0/320); NLA +0.6 / +1.1 / +1.7
  (z ≥ 3 in 7/16 at α = 1; null 1/320); J-lens +0.1 / +0.2 / +0.35 (2/8). Exploratory α = 3 / 5:
  Oracle +6.8 / +8.2 (LO sign crosses to the planted candidate in 9 / 11 states), NLA +3.2 / +4.2.
  Free readouts after planting (α = 1): the Oracle lens asserts the planted candidate in 3/16 and the
  original in 0/16; the NLA asserts nothing (0/16).
- Reading: the verbalizers' scores track the direction we move the state in, far outside the random
  band, while the model's own answer does not follow the same edit. That is a reader-vs-model
  dissociation at this site, in Suraj's "reading what the model reads, not what it acts on" sense; it
  is not evidence that the readers verbalize bindings (they still do not), and because the behavioural
  gate failed it is not the pre-registered "follows the binding" result.

**G6 (`g6/fig_main.png`).** 8 pairs where the model picks one of two options; the key is its own
greedy choice. The target chose the first-listed option in 12/16 (below the 14/16 dominance flag) and
the same option in both orders for 4/8 pairs (Paris, Apple, Circle, Seven). *Prompt-only floor
(same base model asked which it will choose): 12/16 = 75%* — the floor is high because it is the
same model with the same position bias and preferences. Readers: Oracle lens consistent 5/16
(coverage 6/16; it lists both options or "I have no preference"), NLA 0/16 (names both options in
6, neither in 10), J-lens 0/16; NLA–Oracle agreement 0/16 (κ undefined). Decision: no evidence
that any reader reads the upcoming choice beyond the prompt-only floor; the family did lower the
floor from 100% to 75%, but the readers fell with it.

**Updated next step.** Score bindings with native log-odds rather than free text throughout (G5
shows the information is there for the verbalizers), and move the intervention to where it is
causal: edit the bound entity at ALL positions (or upstream, as in Suraj's L38 planting) until the
model's answer flips, then ask whether the readers' LO follows at that dose. For "beyond the text",
a self-choice family needs a floor below the target's own bias: use items where the base model's
prompt-only guess and its actual choice disagree (select on prompt-only, not on readers).

---

## Phase X (same day, 2026-10-07 18:00–20:55 UTC): readers against a causally established fact

Pre-registration: `projects/g_agreement/BRIEF_X.md` (frozen in `manifest/frozen_config_x.json` before test
collection; deviations listed there, all pre-data). Motivation: the three-reviewer direction review
(`direction_review.md`) concluded that "agreement with the majority" cannot be ground truth here (sibling
readers, prompt leak, ceiling, non-causal site), and proposed a blindness map with three independent columns
per feature class: PRESENT (held-out probe), LOAD-BEARING (an edit flips the model), REPORTED (each reader's
native log-odds). All reader scoring in this phase is native log-odds (LO); free text is not scored.
Deliverable: `x/blindness_map.csv` + `x/fig_main.png`; headline figure `x2/fig_main.png`.

**X1, bank + native LO (`x1/`).** 48 + 48 + 24 + 24 pairs (ownership, mapping, language, tense; 1 dev pair
each), 280 test states. E1 = within-pair win (reader favours each state's own answer, candidate-order bias
cancels):

| reader | ownership (47) | mapping (47) | language (23) | tense (23) |
|---|---|---|---|---|
| J-lens | 85% [74, 94] | 94% [85, 100] | 100% | 100% |
| Oracle lens | 83% [72, 92] | 87% [77, 96] | 100% | 100% |
| NLA | 72% [60, 85] | 72% [60, 85] | 100% | 100% |

(pair-bootstrap 95% CIs; SEPARATES rule = win ≥ 0.75 with CI excluding 0.5: all pass except NLA on the two
binding families, which sit just under the threshold.) *So G1's "the readers are blind to bindings" was an
elicitation artefact of free text:* scored natively, all three readers carry the binding, J-lens included.
E2 held-out probe: ownership (binding = answer-is-first-mentioned) 100%, ceiling 100%; tense 100%; language
100% (AUROC 0.96); mapping identity probe 57% (ceiling 60%): the simple class-mean probe does not transfer
across letters, so PRESENT = no for mapping by that probe while the readers report it at 72–94%. E3: the
Oracle lens's native format has a candidate-order bias of several nats on the family mean state (within-pair
scoring removes it); J-lens and NLA are within ±1 nat except J-lens on language.

**X2, plant until the model flips (`x2/`).** 32 ownership + 32 mapping pairs, A→B interpolation of the
block output at the edit layer (h' = h_A + α(h_B − h_A), and the mirror), 4,736 edited greedy decodes with
the block-42 last-token vector read back from the same forward. Sites: S1 = L38 last token only; S2 = L38
all positions (primary); S3 = L42 all positions (reader input is the interpolation itself; reference arm).
- E4 flips, S2: 0/128 at α 0.25, 59/128 (46%) at 0.5, 126/128 (98%) at 0.75 and at 1.0; isotropic nulls
  0/768; coherence ≥ 92%. S3 is the same (125/128). S1: 0/128 up to α 3, 17/128 (13%) at α 4; nulls 0/768,
  other-pair nulls 0/512. *The last-token vector is not load-bearing (G5 again); the all-position state at
  L38 is.* E5 median α* = 0.75; K5 passes (64/64 pairs with α* ≤ 1).
- E6, reader follows the planted direction at its item's α* (S2; null win = P(null shift ≥ planted shift)):

| reader (S2) | win at α* | null win | z ≥ 2 | win at sub-flip dose | E7 gain | class |
|---|---|---|---|---|---|---|
| Oracle lens | 86.5% [78.6, 93.7] | 16.5% | 55.6% | 85.3% | +0.09 | MIXED |
| NLA | 77.0% [67.2, 85.7] | 29.2% | 35.7% | 74.7% | +0.04 | MIXED |
| J-lens | 88.9% [81.7, 95.3] | 21.2% | 27.0% | 89.5% | +0.00 | MIXED |

  S3 (by construction): 88.0 / 77.6 / 92.0% (J-lens SUB-FLIP). S1 (17 flipping items): 76.5 / 58.8 / 76.5%.
- Reading [SUPERSEDED 2026-10-08, see Corrections below] (`x2/fig_main.png`): at the dose where the model's own answer log-odds move by ≈ 40 null
  standard deviations, the readers move in the planted direction in 77–89% of states but by only 2–5 null
  SD, and they move just as often at sub-flip doses (75–90%). The readers track the *sign of the continuous
  dose*, not the behavioural threshold; none reaches the pre-registered TRACKS criterion (win ≥ 0.9 at α*).
  Caveats: at S2 the read vector is the L38 interpolation propagated through four blocks, so following is
  only partly independent of construction; the swap direction contains the candidate's token identity, so
  sign-following is compatible with reading the name rather than the binding (the other-pair null, which
  removes this, was run only at S1 where nothing flips); the gain ratio is not scale-free across readers.

**X3, item sets where the prompt-only floor is at 0 (`x3/`).** Selection on the model only: of 400 arrow
puzzles the target gets 297 wrong (all coherent), controls 103 correct; of 300 two-option choices, 245 have
a parsed self-guess (55 refusals such as "Neither"), 33 DISAGREE (self-guess ≠ actual), 33 AGREE controls.
E8, P(reader LO favours the model's actual answer): ERROR set J-lens 57% [51, 63], Oracle 47% [42, 53], NLA
59% [53, 64]; DISAGREE set 63% [44, 78] / 70% [52, 85] / 61% [42, 76]; controls 53–63%. No reader passes
(≥ 0.75 with CI excluding 0.5). E9 held-out probe predicting the actual answer: puzzles AUROC 0.60, win 57%
(ceiling 60%, majority 74%); choices AUROC 0.55, win 50% (ceiling 57%). *When the model's answer is not
derivable from the text, neither a probe nor any reader finds it at this site.* [SUPERSEDED 2026-10-08, see Corrections] The upcoming wrong answer
and the upcoming self-choice are not linearly present in the block-42 last-token vector.

**Blindness map (`x/fig_main.png`).** Rows language, tense, ownership, mapping, puzzle-error, self-choice;
columns PRESENT / LOAD-BEARING / REPORTED×3 / FOLLOWS×3. The pattern is simple: everything that is linearly
present at this site is reported by all three readers (language, tense 100%; ownership 72–85%), and the two
classes nobody reports (the model's own upcoming error, its self-choice) are not linearly present either. The
cell "present and load-bearing but unreported", which the reframing was built to find, is empty at the
pre-registered thresholds. Mapping is the one inversion: the readers report it (72–94%) while the simple
identity probe does not (57%), i.e. the readers beat the cheapest probe there.

**Verdict for the exploration question.** At block 42 / last token on Qwen3.6-27B, the three readers are not
blind to anything a linear probe can see, and they all see the same things, so "what can some find that others
miss" has no positive instance in six feature classes. The readers' scores follow a causal edit in sign but not
in magnitude, and not more at the behavioural threshold than below it. The limiting factor is the site, not the
readers: the information that would discriminate a good reader from a bad one (the model's actual upcoming
answer when it departs from the text) is not at this site. Next: read earlier positions / later layers where
E9 becomes positive, and rerun the other-pair null at S2 to separate binding from token identity.

Compute: pod mats-minis-h100 restarted 18:02 UTC, stopped 20:55 UTC (≈ 2.9 pod-h, ≈ $10); logged GPU wall in
`compute.jsonl` 0.72 h for the frozen chain (20:06–20:52 UTC) plus a 20-min unfrozen smoke run.

**Corrections after independent review (2026-10-08; raw rows re-checked, no new compute).**
1. *X2 "sign but not magnitude" is a scale artefact.* Normalising each reader's LO shift by its own natural A→B
   separation (from X1), the median shift along the S2 ladder is 0.23 / 0.50 / 0.77 / 1.00 at α 0.25 / 0.5 /
   0.75 / 1.0 for J-lens, NLA and Oracle alike (S3 identical). At α = 1 the read vector *is* the natural B
   vector, so E6 is a linear walk between two states the readers already separate in X1: P(win at α* | reader
   orders the natural pair correctly) ≈ 96–98%, P(win | misordered) ≈ 0–23%. The "2–5 vs ≈ 40 null SD" contrast
   reflects the readers' small native scales (median natural separation Oracle 1.06 nats, NLA 0.47, J-lens 0.09
   cosine) against the model's 18 nats, and the model's own lo_model is also monotone in dose (sign-win 0.89 at
   α 0.25). Correct reading: *at the site where the edit flips the model, every reader's score moves in proportion
   to the interpolation, exactly as its X1 separation predicts; this does not distinguish "follows the binding"
   from "reads the interpolated state", and because A/B are token permutations the all-position swap also plants
   token identity at every name position.* The other-pair null exists only at S1, where nothing flips.
2. *X3 ERROR set is largely text-derivable.* 267/297 wrong answers are a symbol on the model's own trace (151 the
   k−1 symbol, 85 the k−2), i.e. "stop one step early"; only 30 are off-trace. Prompt-only was 0 only because the
   candidate pair is (actual, correct). E9 probed correctness (label actual == correct, majority 74%), not the
   identity of the upcoming symbol, with a diff-in-means direction whose two halves agree at cos 0.69, so "not
   linearly present at this site" is unestablished. E8 is contaminated by per-symbol priors (Oracle −3.2 to
   +2.3 nats across symbols); after removing an additive symbol bias, favour-actual on ERROR is 55 / 59 / 56%
   (J-lens / Oracle / NLA) vs 48 / 52 / 50% on correct controls: a small consistent residual, not nothing.
   What stands: no reader reaches the 0.75 bar on these sets.
3. *NLA 72% vs the other two is a real within-bank difference*, by paired exact sign tests on identical pairs
   (Oracle-only wins 14 vs NLA-only 2, p = 0.004; J-lens-only 21 vs NLA-only 5, p = 0.002; J-lens vs Oracle
   p = 0.42), driven by mapping; but the NLA template format is marginal (within-pair half-separation 0.2 nats
   against a 1–3 nat candidate-order bias), so this ranks scoring formats as much as readers.
4. *Probe column caveats.* The mapping identity probe (class means over 8 symbols from 47 pairs, ceiling 0.60) is
   a weak instrument and the readers' 72–94% within-pair shows a linear within-pair readout exists; the "readers
   beat the probe" inversion is a statement about the probe. The ownership probe label *is* "answer is
   first-mentioned", so binding is perfectly confounded with mention order in this bank, for the probe and the
   readers alike. The LOAD-BEARING column was tested in two classes, not six.
Revised verdict: the three readers behave as one instrument at this site; free-text elicitation, not the
activation, limited G1–G2; the causal following in X2 is implied by continuity and X1; whether the model's
off-text answer is present at this site is open, not answered. The next-steps plan (`NEXT_STEPS.md`) starts
from these corrections.


**Friday re-analyses (2026-10-08, CPU only, `x/friday/`, `x2/fig_fraction.png`, `x6/`).** R1: reader shift as a
fraction of its own natural separation along the S2 ladder is 0.22 / 0.50 / 0.78 / 1.00 (Oracle), 0.21 / 0.50 /
0.79 / 1.02 (NLA), 0.23 / 0.50 / 0.77 / 1.00 (J-lens) vs the model 0.03 / 0.50 / 0.97 / 1.00; win at α* given the
pair was ordered in X1: 98 / 98 / 96%, given misordered 21 / 23 / 0%. At S1 (inert) the readers reach 1.1–1.2× at
α 2 and 1.4–1.7× at α 4 while the model stays at 0.02–0.09; the other-pair direction gives 20–28% of the planted
shift (CIs exclude 0). R2: the ownership "version" label equals mention order in 23/47 pairs; a mention-order
contrast probe is 100% (ceiling 100%), PC1 of h_A − h_B carries 66% of the energy; mapping has no within-pair
order label, the 8-letter logistic identity probe gives paired-sum win 98% (null 61%, ceiling 87%) but
both-states win 66% with a 32% half-data ceiling, so PRESENT(identity) fails the pre-set rule while a linear
within-pair letter readout clearly exists. R3: symbol-bias-corrected E8 on ERROR 54 / 57 / 56% vs controls
47 / 51 / 50%; 8-way logistic probe for the actual symbol 68% on ERROR (null p95 61%, ceiling 36%), the correct
symbol 50%; E9 label with logistic AUROC 0.66; off-trace subset n = 30 descriptive. R4: paired sign tests as in
Corrections item 3. X6 (`x6/x6.md`): majority agreement does not rank readers as the key does; on ERROR the
sibling majority agrees with itself 70% and with the key 47–59% (right 55% where it agrees; non-sibling majority
74%), Spearman(A_maj, A_key) −0.8; shared wrong answer 17.5% vs 9.2% independence. Deviations: permutation null
10 not 20 (CPU-starved); X6 adds a CENTRED variant because the raw per-state sign is dominated by candidate bias.
Summary for the mentor: `summary_for_agam.md`.

---

## Phase Y (2026-10-08/09): site search, identity-free nulls, new reader families

Pre-registration `projects/g_agreement/BRIEF_Y.md` (deviations dated there: other-pair K by equal length; smoke-
contaminated Y3 mean rows recomputed; the Y2 J-lens leak band uninformative; the Y1 S* rule admitting candidate
tokens; the pod sweep stopped and rerun locally once BLAS threads were capped). Pod mats-minis-e 21:52 → 07:45 UTC
(≈ 10 pod-h, ≈ $35, of which ≈ 7 h were an oversubscribed CPU sweep that was abandoned); logged GPU steps in
`compute.jsonl`.

**Y1, where is the model's actual answer? (`y1/fig_main.png`).** 730 items (297 puzzle errors + 103 controls,
165 self-choice disagreements + 165 controls, the choice pool extended by 900 prompts), captured at layers 42–62
(step 2) × the last 12 positions and the two candidate-token positions; L2 logistic probe for the model's ACTUAL
answer per cell, 5-fold by item, 10 permutations, two-half ceiling. Puzzle errors, pre-answer (last) token:
L42 69%, L44 73%, L48 79% [74, 83] (first pass: majority 68%, perm p95 63%), L52 92% [89, 95], L56–62 94%; the
logit lens at the last token is at 52% at L48 and 75% at L52, so the probe finds the upcoming wrong answer four
layers before the unembedding does. Earlier positions never pass except last−1 from L56. Candidate-token cells
are text artefacts (candA = the answer symbol's own token, 100% at every layer; candB = the correct symbol's
token, 83–97%, because the model's typical error is the symbol written immediately before it). Self-choice
disagreements: no cell passes anywhere (best 60%): the upcoming choice is not linearly present at any of these
sites. Headline site S* = 48:last (post-hoc restriction to pre-answer positions; the formal S* = 42:candA is the
trivial cell).
*E11 re-read at 48:last* (Oracle on its training grid; NLA as an L42-trained transfer, state-free prior within
band): favours the model's actual wrong answer J-lens 41% [36, 47], Oracle 49% [43, 54], NLA 57% [51, 62], vs the
probe's 79%; on disagreements 55 / 67 / 62% vs the probe's 51%. At 42:candA the J-lens reads the token identity
(99%) while Oracle and NLA favour the other candidate (40%, 44%). **This is the cell the blindness map was built to
find: at layer 48, last token, the model's own upcoming wrong answer is linearly present (79%, above the ceiling
and the logit lens) and none of the three readers reports it; the J-lens reports the text-correct symbol
instead.** LOAD-BEARING at that site is not yet tested.

**Y2, what the readers follow at the causal site (`y2/fig_main.png`).** Same 64 pairs, edits at L38 all
positions (α 0.5 / 0.75 / 1), 4,956 new decodes. Model flips at α = 1: full swap 98%; name positions only 48%;
non-name positions only 50%; another same-family pair's direction 23% (coherence 86%); the top-384 J-space
component of the swap (44% of its energy; random expectation 27%) 4%; the remainder 92%; a random 384-dim
subspace component 0%, its complement 98%. *The load-bearing content of the binding lies outside the J-space; the
J-space component carries a large share of the energy and none of the effect.* Reader follow at α = 1: full
85 / 72 / 91% (Oracle / NLA / J-lens); name-only 68 / 70 / 70%; non-name 78 / 69 / 75%; other-pair 54 / 55 / 59%
(a clean structured null); J-only 87 / 81 / 82% although the model does not flip under it; J-perp 84 / 70 / 78%.
Pre-registered verdicts: all three MIXED on the name split (model flips only 50% under either half, so the
binding question is ill-posed by halves at this site); J-space: all three readers follow the J-space component the
model ignores (J-SPACE LEAK), and Oracle and J-lens also follow the non-J remainder above 0.75. The pre-registered
leak check against the random-complement band is uninformative (see BRIEF_Y deviations).

**Y3, new reader families (`y3/fig_main.png`, `y3/sae_fve.json`).** Skip-lens arm A (agreement-filtered
future lens, same injection as the NLA): ownership 89% [79, 98], mapping 83% [72, 94], language and tense 100%,
state-free prior within band: PASSES the entry gate and is the best binding reader in the set; X2 follow at α*
86–88% ownership / 82% mapping; X3 no evidence (56% corrected on errors, 67% on disagreements). Arm D (trained on
spans the J-lens misses): ownership 83%, mapping 72% (fails the 0.75 bar like the NLA); X3 no evidence. R-lens:
ownership 70%, mapping 74% (fails). Qwen-Scope layer-42 SAE (trained on Qwen3.5-27B): FVE −0.20 on the X1 states
and −2.6 on the X3 states against shuffled-decoder nulls of −2.4 / −8.5, i.e. it does not reconstruct Qwen3.6
states and cannot be a reader here. The blindness map now carries skip-lens A as a fourth REPORTED/FOLLOWS column.

**Reading of Phase Y.** (1) The readers' site, block 42 last token, is upstream of where the model's own answer
becomes linearly readable; by layer 48 at the same position a probe reads the upcoming wrong answer at 79% and
the readers at 41–57%. "What can some find that others miss" finally has an instance, but it is the probe that
finds it and the readers that miss it, together. (2) The binding information the model acts on is non-J-space
content; the readers follow the J-space component the model ignores as readily as the part it uses, so their
sensitivity does not track causal relevance. (3) Of the new families, only the agreement-filtered skip lens
clears the bar, and it behaves like the others; SAE transfer across Qwen3.5 → 3.6 fails outright.
Open: LOAD-BEARING at 48:last (plant there and flip), readers trained for layer 48, and whether skip-lens D's
"non-J reading" shows up under the Y2 J-perp arm (it was not run on Y2).

---

## Phase Z corrections

**Phase Z corrections (2026-10-09)**

Z3 (`z3/z3.md`, pre-registered in BRIEF_Z §Z3): every "inert" / "not load-bearing" sentence about the last-token site is replaced by a TOST statement against the margin fixed before the tests were read. Original sentences are left in place above; the wording to use is given per bullet.

- **G5 (Follow-up)** — original: "At α = 1 the last-token vector IS the other state's vector and the answer still does not change, so the answer is reconstructed downstream from the untouched earlier positions." → use instead: "At α = 1 the last-token block-42 vector is the other state's vector and the greedy answer does not change (flips 0/16 at α 0.5 [0%, 19%], 0/16 at α 1 [0%, 19%], 0/16 at α 1.5 [0%, 19%], 0/16 at α 3 [0%, 19%], 2/16 at α 5 [3%, 36%], Wilson 95%). G5 recorded no first-token log-odds, so the continuous effect of a last-token edit is bounded only through X2-S1 (L38, last token, 128 states): mean Δ_model +0.12 [+0.08, +0.16] / +0.27 [+0.19, +0.36] / +0.43 [+0.31, +0.56] nats at α 0.5 / 1 / 1.5 (90% pair-bootstrap CIs) → inert within margin, margin ±3.27 nats. That the answer is reconstructed from the untouched earlier positions is a reading consistent with this bound, not a result the 0/16 flip count establishes. See z3/z3.md."
- **Phase X, X2 E4** — original: "The last-token vector is not load-bearing (G5 again); the all-position state at L38 is." → use instead: "At S1 (L38, last token) the planted edit shifts the model's first-token answer log-odds by +0.12 [+0.08, +0.16] / +0.27 [+0.19, +0.36] / +0.43 [+0.31, +0.56] nats at α 0.5 / 1 / 1.5 (mean, 90% CI): inert within margin against the pre-stated margin ±3.27 nats (the shift is small but its CI excludes 0, so S1 is equivalent-to-natural within the margin, not effect-free). Descriptively α 2: +0.70 [+0.52, +0.90] → inert within margin, 1% of items beyond the margin, flips 0/128; α 3: +2.01 [+1.50, +2.56] → inert within margin, 27% of items beyond the margin, flips 0/128; α 4: +4.40 [+3.30, +5.52] → not established, 39% of items beyond the margin, flips 17/128. Controls: S2 isotropic null α 1 +0.17 [+0.13, +0.22] → inert within margin; S3 isotropic null α 1 +0.20 [+0.17, +0.24] → inert within margin; S1 isotropic null α 2 -0.01 [-0.03, +0.01] → inert within margin; S1 other-pair null α 2 +0.20 [+0.09, +0.31] → inert within margin. The all-position state at L38 flips the answer in 98% at α ≥ 0.75 (X2 E4). 'Not load-bearing' is a bounded statement about the first-token log-odds at α ≤ 1.5, not an absolute one. See z3/z3.md."
- **Phase X → Y, Friday re-analyses R1** — original: "At S1 (inert) the readers reach 1.1–1.2× at α 2 and 1.4–1.7× at α 4 while the model stays at 0.02–0.09" → use instead: "At S1 (inert within margin, ±3.27 nats, α ≤ 1.5; α 2 +0.70 [+0.52, +0.90] → inert within margin, α 4 +4.40 [+3.30, +5.52] → not established) the readers reach 1.1–1.2× of their natural separation at α 2 and 1.4–1.7× at α 4 while the model's normalised shift stays at 0.02–0.09; 'inert' at α 4 is not established (17/128 flips). See z3/z3.md."
- **Not covered by Z3** — the Phase Y sentence "The load-bearing content of the binding lies outside the J-space" is a claim about the J-space *component* at the all-position site (Y2 J-only flips 4% vs remainder 92%), not about the last-token site; it was not tested here and would need the same TOST on the Y2 J-only Δ_model against this margin before 'none of the effect' is asserted.
- 2026-10-09, Z2 (`z2/z2.md`): the X6 claim "on the model's own errors the ranking inverts (Spearman(A_maj, A_key)
  = −0.8)" is DOWNGRADED TO SUGGESTIVE. Under counterbalanced scoring (pair-symmetrised for D1/D2, leave-one-out
  symbol/position bias for D3) ρ(A_maj, A_key) on D3 ERROR is −0.20 (ALL), −0.32 (siblings), +0.11 (non-siblings),
  failing the pre-registered ≤ −0.5; the raw −0.80 was carried by the per-candidate symbol bias. What survives
  under all three scorings is the shared-error excess: the three readers favour the same wrong candidate in 17.8%
  of errors vs 8.7% under independence (ratio 2.05 [1.70, 2.43]), and the sibling verbalizers agree with each other
  more than with the key. The X6 figure stays with its raw/centred rows; `z2/fig_main.png` adds the counterbalanced
  row. The true swapped-batch-order re-scoring (Z2b) is deferred to the next pod session.

**Phase Z results and corrections, inserted 2026-10-09 after review** (sources: BRIEF_Z.md deviations; z1/, z2/, z3/, z4/, z4b/; per-family Y2 recomputation)

### Z4 position dissection (2026-10-09; z4/z4.md, z4/fig_main.png; role-aligned reading is a dated deviation in BRIEF_Z)

Pre-registered labels (absolute token index; for reference):

| family | pre-registered label | basis |
|---|---|---|
| mapping | SINGLE CAUSAL | index 9 flips 14/18 = 0.78 [0.55, 0.91] vs bar 0.8·R_all = 0.776 |
| ownership | JOINT | no single index and no index pair flips; pairs tested were indices 0–4 (tie-break, chat-template prefix) |
| pooled | JOINT | best single 0.33, best pair 0.60 |

Role-aligned classification (primary reading; layer 38, α 1):

| family | edited positions | flips | label |
|---|---|---|---|
| mapping | first differing symbol alone | 31/64 = 48% [37, 60] | |
| mapping | second differing symbol alone | 29/64 = 45% [34, 57] | |
| mapping | both differing symbols (Y2 name_only) | 61/64 = 95% [87, 98] | JOINT ACROSS TWO TOKENS |
| mapping | every other position (Y2 name_removed) | 0/64 | |
| ownership | any single position (diff, question start, last, other) | 0/956 | |
| ownership | all name/object tokens together (Y2 name_only) | 0/64 | |
| ownership | all post-statement positions (Y2 name_removed) | 64/64 = 100% | JOINT ACROSS A SPAN (post-statement) |
| ownership | question tokens only (Z4b) | 6/64 = 9% [4, 19] | |
| ownership | chat-template tokens only (Z4b) | 7/64 = 11% [5, 21] | |
| ownership | last 3 tokens only (Z4b) | 0/64 | |
| ownership | question first / second half (Z4b) | 0/64, 3/64 | |

Reading: at layer 38 the two families store the answer in opposite places. Mapping carries it on its two differing
symbol tokens, jointly (neither alone suffices). Ownership carries it jointly across the positions after the two
statements, and not at all on the name or object tokens; no single position, including the last token, suffices.
Z4b (pre-registered follow-up, z4b/z4b.md): no part of the post-statement span suffices on its own at layer 38
(question tokens 9%, template tokens 11%, last 3 tokens 0%, question halves 0% and 5%), although each moves the
model's answer log-odds substantially (question +7.8, template +7.6 nats; all post-statement positions +24.2). The
ownership answer at layer 38 is therefore joint across the whole post-statement span. Earlier, the binding sits on
the names: editing only the name and object tokens flips 64/64 at layer 20 (+25.3 nats), 0/64 at layer 28 (+2.5) and
0/64 at layer 38 (+0.9): between layers 20 and 28 the binding moves off the name tokens into the later positions.
Readers on the same edits: editing only the last 3 tokens moves the Oracle lens and J-lens by 0.70 and 0.58 of their
own natural separation while the model's answer moves 0.55 nats and flips 0/64; template-only edits move them by
0.85 / 0.77 while the model flips 11%. The readers track the positions nearest their read site, not the positions the
model's answer depends on.
Determinism: 32/32 restore decodes reproduce their all-except-one twins. Random single-position control: 0/64.

### Correction to Phase Y, Y2 (2026-10-09; per-family recomputation of y2 rows)

The Phase Y sentence "name positions only 48%; non-name positions only 50%" pooled two families with opposite
patterns, and so did "another same-family pair's direction 23%". Per family, layer 38, α 1:

| family | condition | model flip | Oracle win | NLA win | J-lens win |
|---|---|---|---|---|---|
| mapping | full swap | 62/64 = 97% | 84% | 73% | 89% |
| mapping | name tokens only | 61/64 = 95% | 95% | 89% | 98% |
| mapping | non-name positions only | 0/64 = 0% | 67% | 67% | 56% |
| mapping | other pair's direction | 5/164 = 3% | 50% | 53% | 56% |
| mapping | J-space component only | 5/64 = 8% | 83% | 83% | 78% |
| mapping | J-space remainder | 54/64 = 84% | 83% | 73% | 72% |
| ownership | full swap | 64/64 = 100% | 86% | 70% | 94% |
| ownership | name tokens only | 0/64 = 0% | 42% | 50% | 42% |
| ownership | non-name positions only | 64/64 = 100% | 89% | 70% | 94% |
| ownership | other pair's direction | 82/208 = 39% | 58% | 57% | 61% |
| ownership | J-space component only | 0/64 = 0% | 92% | 80% | 86% |
| ownership | J-space remainder | 64/64 = 100% | 86% | 66% | 84% |

Corrected statements: (1) the binding question is not ill-posed by halves; per family it is clean: mapping's answer
is on the name (symbol) tokens, ownership's on the non-name positions. (2) In both families the readers follow the
half that flips the model (mapping name tokens 89–98%; ownership non-name positions 70–94%) and not the half that
does not (ownership name tokens 42–50%), with the exception of mapping's non-name half (56–67% while the model
flips 0%). (3) The J-space finding holds per family (J-space component flips 8% / 0%, remainder 84% / 100%), and the
readers follow the J-space component the model ignores in both families (78–92%). (4) In ownership another pair's
swap direction flips the model 39% of the time (mapping 3%): the ownership answer at layer 38 is largely carried by a
direction shared across pairs, consistent with the first-versus-second-mentioned confound found in R2.

### Z1 reported as gain over the dose-only model (2026-10-09; z1/gain_over_dose.md, z4/z1_on_z4/gain_over_dose.md)

ΔAUROC = reader − dose-only, paired pair-level bootstrap, 1,000 resamples; "beats dose" only if the CI excludes 0.

| set | Oracle lens | NLA | J-lens |
|---|---|---|---|
| X2, S2 ∪ S3 | −0.039 [−0.071, −0.011] | −0.143 [−0.181, −0.108] | −0.042 [−0.076, −0.015] |
| X2, S3 | −0.037 [−0.082, −0.005] | −0.111 [−0.149, −0.076] | −0.003 [−0.026, +0.016] |
| Z4, single + pair + all-except | +0.057 [+0.024, +0.090] | −0.165 [−0.225, −0.094] | +0.045 [+0.007, +0.082] |
| Z4, single positions | +0.388 [+0.270, +0.494] | −0.068 [−0.191, +0.045] | +0.381 [+0.271, +0.487] |
| Z4, mapping only | +0.094 [+0.039, +0.139] | −0.185 [−0.265, −0.084] | +0.077 [+0.012, +0.134] |
| Z4, ownership only | −0.005 [−0.009, −0.002] (dose = 1.000) | −0.144 [−0.210, −0.068] | −0.008 [−0.013, −0.003] |

Reading: on the X2 interpolation ladder no reader beats knowing the dose. On the Z4 edits Oracle and J-lens beat the
dose reference, but that reference knows the arm and the dose and not which position was edited, so within an arm
it is at chance (AUROC 0.43–0.48); the readers' advantage there is that their score moves when a causal position is
edited, which the reference cannot see. The NLA never beats dose and is below it on most sets.

### Per-position correlation (Z4 single-position arm; z4/per_position_corr.md)

Spearman between a position's mean reader shift and its flip rate, pair-level bootstrap 95% CI; ownership is
undefined (no single position flips). Mapping, α 1: Oracle +0.35 [+0.07, +0.51], J-lens +0.20 [+0.03, +0.47], NLA
−0.32 [−0.42, +0.06]; the model's own answer log-odds give +0.57 [+0.42, +0.60] (absolute index). Role-aligned, no
reader's CI excludes 0 (Oracle +0.33 [−0.01, +0.37], J-lens +0.02, NLA −0.31) against the model's +0.35; the
role-keyed statistic is tie-bound because only the two differing-symbol keys ever flip. Reading: the readers weakly
identify which positions are causal; the NLA, if anything, ranks them backwards.
### NLA validity (z4b/nla_gate.json)
Pre-registered gate PASSED: re-scoring the X1 bank through the Z4 code path reproduces the original NLA scores exactly
(34/47 within-pair wins on ownership and on mapping, 23/23 on language and tense; median |Δ log-odds| 0.000, sign
agreement 1.000). The Z4 NLA numbers stand.

## Phase W (2026-10-12): are the readers class-mean readers? (PREREG_WV.md; w/summary.md)

Pre-registered H-W: the lens readers report the class-mean component of a state. Three tracks: a graded bank
(600 counts, 128 ownership-4, 100 arithmetic in Michael Kenney's format, 16 target-private pairs), a per-pair
direction decomposition (d_cm, d_pw orthogonalised, d_J top-384 J-space, d_res remainder, full, 10 random), and a
Gemini claim judge (κ 0.86 vs a second judge). One pod session (mats-minis-e, 157.6 pod-min): 954 captures, 4,032
steered decodes, 27,442 native reader scores. S4 free-text sampling was skipped by the budget guard (deviation).

Verdicts: P1 FALSE (d_cm follow ≥ 75 % fails for NLA 66 % and skip-lens 72 % in ownership, J-lens 70 % on errors);
P2 FALSE on the letter (mapping lenses 69–78 % > 60 %) but true in spirit (lenses inside their random band in every
family while the probe follows d_pw 96 %); P3 FALSE (d_cm flips as well as the full swap: 100/100, 94/95, errors
34 vs 19); layer-48 clause FALSE (34 % < 50 %). Decision rule 3: the matrix is reported as is. Rule 2 replaces
"readers miss the model's errors at 48" with "no reader-independent linear method reads a load-bearing off-text
answer at this site" (V1 adds that readers trained at 52+ do read it).

What the matrix shows (`w/fig_matrix.png`): every reader follows the directions that flip the model (d_cm, full,
mapping d_J) at 66–100 %, and also the directions the model ignores (ownership d_J 80–94 %, d_res 67–88 %, 0 %
flips); none follows the probe direction (45–56 % vs random 48–52 %). On errors at L48 the Oracle follows d_cm 97 %
although it does not read the natural wrong answer there (49 %). Reader differences: NLA trails J-lens by 18 pts
[9, 28] pooled on d_cm; 34 of 66 pre-registered comparisons meet the difference criterion.

Precision on graded facts (`w/fig_precision.png`): on 600 counts the model's next-token distribution keeps the
magnitude (ρ 0.83) while the readers' native vectors do not (exact 1–3 %, ρ ≤ 0); on 94 eight-way mapping items the
readers score 12–21 % (chance 12.5 %) where the model scores 97 % and the same readers score 85–94 % on two-way
items. Bridge to Michael's Result 2: his probe recipe on our 100 arithmetic states gives operand exact-match 0.24 /
0.48 vs his 0.83 / 0.93; the learning curve attributes the gap to n. W3/W4 fall back to the G1/G4 claims: input-claim
precision NLA 27 %, Oracle 40 %; a 2-of-2 recurrence filter on the G4 repeats keeps 24–47 % of claims without raising
precision.

Reading: the lenses are not strictly class-mean readers, but they share one blind spot (the probe direction) and one
sensitivity (any class-mean-like push, used or not). The eight-way and counts results narrow "what is in the vector":
two-candidate contrasts, not values. Caveats: one model, synthetic prompts, 64 states per cell, S4 absent, NLA and
skip-lens not evaluable on the L48 errors (they read block 42).

## Phase V (2026-10-11/12): layers, re-solving, consistency, humans, windows, positions, private facts (v/summary.md)

V1: on the 297 puzzle errors the probe reads the model's wrong answer from L48 (79 %); the J-lens and the Oracle
lens cross 75 % at L52 (77–86 % through 62), NLA (42, 48 only) does not. V2: J-lens at 48 prefers the correct answer
over the model's actual one (+17 pts [+6, +29], perm p 0.005); NLA and J-lens at 42 prefer the model's wrong answer.
V3 (Michael's 4,190 claims): the pre-registered recurrence + sensitivity model FAILS (ΔAUROC −0.043 [−0.124, +0.019]);
post-hoc, sensitivity alone separates the 39 confidently repeated wrong claims (AUROC 0.83) that recurrence cannot
(0.56). V4: second-judge κ 0.86; human sheet (300 rows) written, not yet labelled. V5: window readers do not beat the
last-token probe (best Δ +3.0 [−2.7, +8.8]; NOT MET). V6: the Oracle reads ownership from the full prompt span 32/32
vs 28/32 at the last token, but the post-statement span alone (23/32) does not beat it (NOT MET). V7: with the fact
in a system-turn preamble and an identical visible prompt, Oracle 16/16, skip-lens 15/16, J-lens 13/16 at L42 read
who owns the object (prompt-only baseline 50 %); the held-out ownership probe is reversed (0/16), which points at a
mention-order feature; a 48-pair confirmatory design balancing order and preamble role is written
(`banks/w/items_v7_confirmatory_design.md`). Note for Michael Kenney: `v/for_michael.md`.

### V7 confirmatory (2026-10-12 12:00 UTC; v/v7c.md, fig_v7c.png; PREREG_WV.md 10:40 UTC entry)

48 new base pairs (8 name sets × 3 object pairs × 2 mention orders, names and objects disjoint from the pilot), each captured with
the preamble as the system turn (target-private) and as a prefix of the user turn (role control); 192 items, one 12-minute pod
session (pod mats-minis-v7c, created because pods e/d/c had no free GPU). Pre-registered rule: each pilot-positive cell ≥ 0.70
within-pair win with the pair-bootstrap CI excluding 0.5 on the 48 system-role pairs. Result: all four CONFIRMED — Oracle@42 45/48
= 94 % [85, 100], J-lens@42 42/48 = 88 % [77, 96], skip-lens@42 39/48 = 81 % [69, 92], Oracle@38 38/48 = 79 % [67, 90]; NLA@42
(not in the pilot rule) 45/48; target ceiling 96/96 greedy. Prompt-only baseline 50 % by construction. Secondary: J-lens@42,
Oracle@42 and NLA read the fact better in the system turn than in the user turn (+12.5 [+2, +23], +10.4 [+2, +21], +22.9
[+10, +35] pts); every lens reads it better when the holder is the second-mentioned name. Probe: the pilot's 0/16 was the
orientation rule reading mention order from a prompt without names (fix recorded before capture; pilot re-score 16/16);
confirmatory probe 47/48 at 42, 45/48 at 38. Reading: a fact present only in the model's context, absent from the visible
prompt, is reported by every reader family at 79–94 %; the readers' ceiling here is the state, not the prompt.

### Oracle on its training grid (O44, 2026-10-14; w/o44/o44.md, w/o44/fig_o44.png; PREREG_WV.md 2026-10-13 entry)

The Oracle lens was trained on blocks 20–60 step 4, so the Oracle numbers in X1 and W1 are off-grid at block 42. A
pre-registered rerun at block 44 on the same states (X1: 140 natural pairs; W1: 2 × 1,344 ownership and mapping edit
entries, read-back at 44; one 10-minute pod session) reproduced the block-42 tables exactly and changed two Oracle cells
under the ≥ 10-point rule: ownership class-mean follow 77% → 92% [Δ +16, CI +5 to +28] and ownership probe-direction
follow 52% → 66% [+14, +2 to +28], above the 47% random band. Unchanged: Oracle follows the J-space component (94 → 91%)
and the remainder (88 → 94%) of the ownership swap at 0% model flips; X1 ownership 83 → 91% and mapping 87 → 94%
(below the threshold). The J-lens reads mapping worse at 44 (full swap 98 → 70%), a layer effect since its lens is
native at every layer. Reading: the off-grid read did not create the "readers follow what the model ignores" result;
on-grid it holds for the Oracle, and the Oracle partly sees the probe direction in ownership.

## Agam follow-ups 2 (2026-10-14; agam/SUMMARY2.md, f2/t1–t4; pre-registered in BRIEF_Z.md)

**F2-1 prefill vs chat template (32 G1 states).** Formats: chat template; template + an assistant-turn answer stem
that names no candidate; plain text + the same stem. Reads at the last three positions, blocks 42 and 44. The stem does
not rescue the readers: judged free-text hit at the last token falls from 50% [27, 74] to 38% [16, 59] to 17% [5, 30]
for the Oracle at 44 (NLA at 42: 45 / 36 / 15%). Ownership and mapping stay at 0–9% free-text hits in every format
while their log-odds wins stay at 81–100%. Rule (+20 points, CI excluding 0) not triggered: the G1 misses are not a
formatting artefact. A later check changes the reading: the J-lens was scored only at layers 42/44, where it names the holder or mapping answer 0% of the time, but at layers 56–60 it names them in every format, including the plain chat template (ownership up to 38%, mapping 50–75%, tense 50–100%). Many layer-42 misses look like a read-site (layer) issue, not a formatting one, consistent with the layer-52 crossing on errors.

**F2-2 norm-matched split edit (ownership, 64 states, layer 38, all positions, doses 0.25–2).** Given the full edit's norm at every position, the J-space part flips the model 0/64 [0, 6%] at dose 1 (full edit 64/64) and 52% [40, 63] at dose 2, but the model does respond to it: its answer log-odds move +3.9 nats at dose 1 against +24.8 for the non-J part (which flips 100%). Readers follow the J-space part 78–91% already at dose 0.25 and stay there (follow is a sign test). So Agam's sensitivity point largely holds: the model under-weights the J-space part about 6× relative to the rest of the edit, while the readers weight both about equally; the gap in dose is at least 8×. Random directions at the same norm flip nothing and move readers 45–59%. Write-up change: replace "follows components the model ignores" with "the model under-weights components the readers weight fully".

**F2-3 probe vs readers at every position (X1 bank, blocks 36–60 step 4).** 60 cells with a held-out probe at ≥ 80%
and both J-lens and Oracle at chance: ownership 45, tense 15, none in language or mapping; all on pre-answer template
and instruction tokens, none at the last token. The probe reads a two-way label and is trained; the readers are
zero-shot on names. Analysis-time rules (logged): identical-prefix positions excluded as ties; a flagged cell needs
≥ 75% of the family's pairs scorable.

**F2-4 diagnostics.** (a) The NLA repo ships its reconstructor, so FVE was computed with the EasyNLA recipe on 1,192 NLA readouts. FVE depends on position: about 0.5–0.7 at the last token in every format, but −1.8 to −1.9 on the chat-template tokens before it, which look out of distribution for the reconstructor (the earlier "FVE ≈ 0" was an average over positions). Within one family at the same position FVE does not separate readouts that name the key from those that don't (AUROC 0.21–0.46 at the last token); the pooled AUROCs of 0.86–0.92 come from position and family differences. Only 18 readouts assert the wrong candidate. The Oracle's log-prob of its own asserted answer does not predict correctness either (AUROC 0.40 [0.25, 0.63]; margin 0.59 [0.37, 0.84]). Not yet run on the shared-mistake error states. On the Y1 puzzles the
Oracle is not more confused on errors (1.35 vs 1.29 distinct answers, Δ +0.05 [−0.06, +0.16]); from block 52 it names
the model's answer as often on errors as on correct items and the correct answer less often (19% vs 43%).

## Agam follow-ups 3 (2026-10-14; agam/SUMMARY3.md, f2/t5, f2/t6; pre-registered in BRIEF_Z.md)

**F2-5 Agam's exact stems with a copy control (32 G1 states; Oracle at 44 and 56, NLA at 42; rule-v1 scoring after the
judge credits ran out).** With a stem naming the key ("The answer, in Spanish, is") the Oracle names it 94–98%; with the
same stem naming the other candidate it names that one 64–95% and the key ≤ 5% (NLA 59–70% vs 0%): the pre-registered
copy rule fires for every reader-layer, so these stems measure copying. "The answer is" lowers ownership and mapping
hits at every layer (rescue rule not triggered). With the plain chat template and no stem, the Oracle names the
ownership or mapping answer in free text at block 56 in 86% [67, 98] of readouts (12% at 44), correct for both
versions of each pair; the J-lens names it at 56–60 (25–62%) and never at 36–52. The G1 free-text "abstention" on
bindings is a read-layer effect: it holds at 42–44 and not at 56.

**F2-6 newline feature at new read sites (60 wikitext-103 test passages, Suraj's fixed templates).** Four sites: raw,
`<|im_end|>` appended, a counting instruction, both. No reader passes the rule (count_qual pair win 48–65%, CIs near 50%;
placebo near 50%), while a leave-one-passage-out ridge probe separates long from short lines at 85–97% at every site.
With the instruction plus `<|im_end|>` the Oracle mentions line length in 61/120 and 60/120 readouts for long and short
lines alike: instruction narration, not a reading of the count.

