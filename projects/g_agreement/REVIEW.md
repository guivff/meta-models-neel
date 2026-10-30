# Methodological review of the G1–G4 design (DESIGN.md / INTERFACES.md as of 2026-10-07)

Reviewer role: analysis track. Scope: the design as written, before freezing. Verdict first, then the
problems, then a numbered list of fixes the coordinator should apply before `frozen=true`.

## Headline

1. **The blind sheet is not blind.** INTERFACES §6 keeps `gen_id` on the sheet, and §5 defines
   `gen_id = "g1|nla|own-03A|s0"`: the item id (and hence pair, family, version and — via items.json —
   the answer) is in the row. Any human or model annotator can recover the key. Replace `gen_id` on the
   sheet with an opaque salted id and keep the mapping in a file the annotator never sees.
2. **The design does not yet answer its own question.** "Does using several techniques give more
   reliable information than one?" needs the accuracy of the *combined* rule compared with the *best
   single* reader on the *same states* (matched coverage), against a chance-corrected agreement
   baseline. The B1-style buckets alone confound agreement with item difficulty (easy states produce
   both agreement and correctness). The bucket analysis is implemented, but it should be
   pre-registered as secondary; the primary endpoint should be "consensus-k accuracy − best single
   reader accuracy at matched coverage", with the paired pair-level bootstrap.
3. **16 pairs cannot separate methods unless the gap is ≥ 30 pp; 4 pairs (G4) cannot separate
   anything.** State this in the brief in those words. G4 is a feasibility pilot (cost, abstention
   rates, whether 3 samples at T = 1 even disagree), not an experiment that ranks rules.
4. **Readers do not receive the same information**, so agreement differences are not reader-quality
   differences: Oracle lens sees the layer integer (42, off its 20–60-step-4 training grid); NLA sees a
   trained actor prompt and an adapter tuned on this very model's activations; J-lens sees the
   activation alone and answers in a 10-token list that the rubric must *interpret*. The rubric's J-lens
   rule decides J-lens's coverage and contradiction rate by fiat.
5. **Shared-error structure is baked in.** All three read one vector at one site and position; the
   rubric/extractor is shared; two readers were trained on the same model's activations. A
   "2 agree, both wrong" state cannot be attributed to the readers versus the state versus the
   extractor without the controls listed below. The current shuffled arm (cached reassignment) tests
   activation dependence of the *text*, not of the *readers*; it must not be described as an
   intervention (the scripts label it accordingly).

## 1. Leakage risks

| Risk | Where | Severity | Fix |
|---|---|---|---|
| `gen_id` embeds `item_id` on the blind sheet | §5 gen_id format, §6 sheet | high | opaque `sheet_id = sha256(salt + gen_id)[:12]`; mapping file outside `results/claims/` |
| `method` on the sheet (admitted: "format reveals it anyway") | §6 | medium | accept for J-lens; for NLA vs OLens the prose formats differ systematically (NLA explanation style vs `concepts_raw` list) so annotators can still tell; report inter-annotator agreement *per method* |
| Extractor sees the answer key | §6 status is defined relative to the key | medium | fine for `rule-v1` if the rule is frozen and tested; any model/human extractor must produce `value` blind and the script derives `status` (my `claim_correct` recomputes correctness from `value`, and flags status/value disagreements) |
| Dev → test template reuse "where feasible" | §1 | medium | make it a hard rule and test it (`template_id` sets disjoint across splits) |
| Cap revised after dev inspection, then frozen | DESIGN "Frozen settings" | low–medium | allowed, but log the dev completion rate that motivated the revision in the brief's Deviations section |
| Analysis code not in the frozen sha | §8 covers collection code | medium | include `core/analysis_utils.py` and the five analysis scripts in the directory sha; any post-freeze change to an analysis script is a dated deviation |
| Target answer used by the extractor | §5 target row, §6 | low | keep the target answer out of the sheet (it is: only `text`), and never let the extractor see `target_answer` |
| `donors.json` label balance "not forced opposite" | §2 | low | print the achieved balance (the G3 script does) and pre-register that recipient-scored accuracy is interpreted against it |

## 2. Asymmetric information between readers

- **Oracle lens** receives `(activation, concepts_raw prompt, layer=42)`. 42 is off its training grid;
  Suraj's 40/44 sensitivity is "reported, not re-run". If OLens degrades off-grid, every OLens number here
  is a lower bound and the agreement map is biased against it. Either run 40/44 on dev (cheap: 8 states)
  or state the limitation as a caveat in every OLens figure.
- **NLA** receives an actor prompt from `nla_meta.yaml` and an RL-tuned adapter trained against this
  exact model snapshot. It has the most task-specific prior of the three. If its training data
  resembles the four families, its accuracy partly measures memorised priors, not state reading.
  G3's prompt-only arm controls for the *base* model's prior, not for NLA's adapter prior; a
  **state-free NLA control** (NLA run with a zero or mean activation at the marker) is the matching
  control and costs 32 calls.
- **J-lens** is deterministic and prompt-free. It cannot abstain, hedge or explain; its "abstention" is
  entirely a rubric decision (which tokens count as asserting a candidate). The same is true for its
  contradictions. Any claim of the form "J-lens agrees less with the verbalisers" is partly a claim
  about the rubric.
- **Prompt-only** sees the question text, which the readers do not; it is a ceiling on
  text-only priors, not a floor.

## 3. Format advantages and the rubric's J-lens rule

- Prose readouts can name both candidates ("Mira, not Leo"), which the rubric must disambiguate
  (negation handling). A token list cannot express negation at all, so J-lens
  `self_contradictory` will arise whenever both candidate tokens rank in the top-10 — likely for
  ownership (both names are in the prompt and J-lens readouts on copy-heavy positions surface prompt
  tokens). Expect J-lens's relation metrics in G2 to be structurally near zero: a token list has no
  binding, so `relation.status` will be `unbound` for most states by construction. That is a true
  limitation of the format, but it should be pre-registered as the expected outcome, not reported as a
  finding.
- Family × format interactions to pre-register: language (J-lens may emit tokens *in* the language
  rather than its name — the rubric must say whether that counts), tense (function words `will`/`was`
  may or may not count), mapping (`two_step_result` requires composition; a top-10 list probably
  cannot express it). Decide now whether the primary endpoint is averaged over families or reported
  per family only (4 pairs per family → no per-family claims are possible; see §5).
- The 128-token cap truncates verbalisers, not J-lens. Report truncation as its own column (done) and
  decide in advance whether a truncated readout with a clear assertion counts (I count it; the
  `truncated` flag is kept).
- A 50 % chance-agreement floor: with two candidates, two readers that each pick randomly agree half
  the time when both answer. Report agreement *above chance* (Cohen's κ with pair-bootstrap CI) next
  to raw agreement, or the agreement matrix will look impressive by default.

## 4. Shared-error risks

- Same vector, same site, same position for all readers: a state that does not yet encode the answer
  at block 42 (the target's *own* greedy answer is the natural ceiling; the brief should say what to do
  when the target is wrong — my scripts keep source-model errors and report the target-correct subset
  separately) yields correlated failures that look like reader agreement on a wrong answer.
- Shared extractor: a rule that mis-handles negation mis-handles it for every method. A shared
  extractor error is indistinguishable from shared reader error. Spot-check ≥ 20 dev claims by hand
  per method and log disagreement with `rule-v1` before freezing.
- Two readers trained on the same model's activations (NLA adapter, OLens `s3d_rl600`) may share
  training-induced priors (e.g. defaulting to the first-mentioned entity). The A/B swap partly
  controls for this *if* candidate position is balanced (§1 says it is) — add a test that asserts the
  balance rather than trusting the generator, and report accuracy split by candidate position.
- Consensus accuracy by bucket is confounded by difficulty. The informative comparison is within the
  same states: bucket-3 accuracy vs each reader's own accuracy on those same states (matched),
  and LOO consistency vs accuracy per method (both implemented, keep them separate as the plan says).

## 5. Sample size and power (say this plainly in the brief)

- 32 test states = 16 base pairs; states within a pair are not independent, so the effective n is
  between 16 and 32. Wilson/pair-bootstrap 95 % CIs at n = 32: 24/32 (75 %) → [57, 87]; 16/32 →
  [34, 66]. Any single-method accuracy is known to ±15–20 pp at best.
- Method vs method on the same states (paired): with 32 states, a two-sided exact test on discordant
  states reaches p < 0.05 only when the split is at least 8–1 (or 10–2, 11–3). A 20 pp accuracy gap
  with realistic discordance (~30 % of states) has well under 50 % power; a 30–40 pp gap is the
  smallest you can hope to call. Smaller differences are not detectable and must not be interpreted.
- Per family: 4 pairs = 8 states. CI for 6/8 is [35, 90]. There are no per-family findings in this
  design; per-family numbers are descriptive only. Say so in the figure captions.
- G4: 8 states, 4 pairs. A rule at 7/8 has CI ≈ [47, 99]; two rules differing by one state are
  indistinguishable. The within-reader comparison also depends on whether 3 samples at T = 1 disagree
  at all; if NLA samples agree with themselves 8/8, the pilot has learned only that the sampling
  setting is near-deterministic for these prompts. **Label G4 a feasibility pilot in the brief, figure
  and write-up** (the script already prints and plots it as such). If the question matters, it needs
  all 16 test pairs × 3 samples × 2 verbalisers (+64 calls) at minimum, and that still only reaches
  n = 32.
- Consequence for the decision rules in the brief: write them as *directional with a minimum
  effect*, e.g. "consensus-3 accuracy exceeds best-single accuracy at matched coverage by ≥ 20 pp with
  a pair-bootstrap CI excluding 0", and pre-commit that anything smaller is "no evidence either way".

## 6. Does the design answer "do several techniques give more reliable information than one"?

Partly. What it does measure: pairwise agreement/contradiction/missing (G1), accuracy per method
and per agreement bucket, LOO consistency, activation dependence of the text (G3), and a
same-reader-resampling comparison (G4). What is missing for the question as posed:

1. The primary contrast — combined-rule accuracy vs best single reader at matched coverage on the
   32 states — is not named as the endpoint. With 2 candidates and 3 readers a 2/3 majority almost
   always exists, so "≥ 2 agree" is nearly the whole dataset; the only discriminating buckets are
   unanimous vs 2-with-dissent, and those will have ~10 states each.
2. "Reliable" means calibrated: P(correct | 3 agree) vs P(correct | 2 agree) vs P(correct | single).
   That is what the bucket table gives, but it must be reported with the caveat that buckets are
   selected on the outcome of the readers (difficulty confound). The G4 within-reader control is the
   right design to break that confound (if agreement among samples of one reader is as predictive as
   agreement across methods, "several techniques" adds nothing beyond "several samples") — but at
   n = 8 it cannot do so.
3. Chance correction is absent (κ). Two readers at 60 % accuracy on a binary task agree ~52 % of the
   time by chance alone.
4. Shared-wrong-answer analysis is the most informative negative result (correlated failures) and is
   implemented; pre-register it as a named secondary endpoint with the per-family breakdown as
   descriptive only.

So: as written, the design produces an agreement *map* and a *pilot* of the reliability question. It
can falsify "the three methods are interchangeable" (if contradiction rates are high) and it can show
the shuffled arm collapsing (activation dependence). It cannot establish that combination improves
reliability, and the brief should not promise that.

## 7. Concrete fixes before freezing (in priority order)

1. **Opaque sheet ids.** Replace `gen_id` on `<module>_sheet.jsonl` with a salted hash; keep the map
   outside the claims directory. `analysis_utils.validate_blind_sheet` already rejects any extra column
   and any answer-key string; add the rule "no `item_id` substring in any field" once ids are opaque.
2. **Name the primary endpoint**: consensus-k accuracy minus best-single accuracy at matched coverage
   (paired pair-bootstrap, n_boot 2000, seed 0), with a pre-committed minimum effect (≥ 20 pp) and the
   explicit statement that smaller effects are uninterpretable at n = 16 pairs. Demote the bucket
   table and LOO consistency to secondary.
3. **Add chance-corrected agreement** (Cohen's κ per method pair, pair-bootstrap CI) to G1's
   `agreement.csv`/figure and the brief.
4. **Pre-register the J-lens rubric rule per family** (what counts as asserting a language, a tense,
   an owner, a two-step result; rank threshold; both-candidates-present → `self_contradictory`), and
   state the expected structural outcome for G2 (J-lens `unbound` by construction).
5. **Noise ceiling for J-lens** (CLAUDE.md rule 3): on the 8 dev states, how often does a candidate
   token appear in the top-10 of a *random* or *mean* activation? Without this, J-lens coverage has
   no floor to be compared against.
6. **State-free NLA/OLens control** (32 calls each): run both verbalisers with the mean dev activation
   (or zeros) in place of the state. This is the proper "no activation" control for the *readers*;
   prompt-only controls only for the base model. Keep the cached-reassignment arm but describe it as
   "text reassignment", never as an intervention.
7. **Run OLens at 40 and 44 on the 8 dev states** (16 calls) or add the off-grid caveat to every OLens
   number.
8. **Decide the population**: all 32 states (source-model errors kept) *and* the target-correct subset,
   with the first as primary; specify what happens when the target answer is unparseable (currently:
   excluded from consistency, kept in accuracy).
9. **Hard template disjointness** between dev and test, enforced by a test on `items.json`; and a test
   that candidate position is balanced within every family of the test split.
10. **Extend the frozen sha to the analysis code** and require a dated Deviations note for any change to
    `core/analysis_utils.py` or the five analysis scripts after freezing.
11. **Human spot check of the extractor** on ≥ 20 dev claims per method, logged in `results/g_agreement/g1/dev/log.md`,
    before freezing `rule-v1`.
12. **Label G4 a feasibility pilot** in BRIEF.md, with its purpose restated as: cost per rule,
    abstention rates, and whether within-reader samples disagree at all. If the reliability question
    is to be answered, budget 16 pairs × 3 samples now rather than later.
13. **Truncation policy**: pre-commit whether a `finish_reason = length` readout with a clear assertion
    counts (recommended: yes, flagged) and report the truncation rate per method in every figure caption.
14. **Dev-split donors**: `donors.json` is test-only per §2, so G3 cannot be developed on dev. Either
    add a dev-internal assignment block (the script accepts one) or accept that the G3 pipeline is first
    exercised on test data — the former is safer.

## Notes on what the analysis scripts enforce (so the brief can refer to them)

- Test summaries refuse to run without `manifest/frozen_config.json` with `frozen: true`; dev runs
  need `--allow-unfrozen` and write to `results/g_agreement/<module>/dev/`; dev and test are never
  summarised together (`SplitLeakageError`).
- Every reader row is checked against `states_meta` (layer 42, `block_output`, `hidden_states_index`
  43, `pre_answer`, prompt hash, activation norm, `layer_in_prompt`) — `SiteMismatchError`.
- Donor assignments must be test-only, same family, different pair, complete — `DonorAssignmentError`;
  every shuffled claim must be the assigned donor's first genuine sample.
- G1 first samples are reused in G4 only if their sampling dict equals the frozen one and the G4
  samples' — `SamplingMismatchError`.
- Votes: `unclear`/`self_contradictory` abstain; two abstentions never agree; ties and all-abstain are
  unresolved; LOO consistency excludes the method's own vote; accuracy is recomputed from the asserted
  value, not the status label, and status/value disagreements are reported.
- All rates print `k/n` and carry a 95 % CI from a bootstrap over base pairs (n_boot 2000, seed 0).
