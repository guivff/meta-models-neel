## §112 E20. The horizon test, redesigned: does the lens's output follow the model's own expectation of the consequence?

**Registered 2026-10-25 05:45 CET, before any E20 item exists. EXPLORATORY.** Replaces E17's measurement, which
scored only the immediate next token (§110 note). **Owner:** W-core (reuses E17's twin generator and position indexing,
E15 scoring, the E6/Q native generation path, and E16's base-Qwen text arm). **Cap:** min(1.5F + 360, 7,200) s,
setup 2,400 s. Launch no later than Monday 26 Oct; analysis once, on CPU.

**Hypothesis.** The Oracle lens expresses a state to the extent the model itself expects its consequence within the
next ~16 tokens, not to the extent the activation encodes it.

**Items (new; seed 20261025; template families split dev 1/3, test 2/3).**
- **`prose_paren`** and **`python_string`:** 120 items per row, each a 60–80-token span with its neutral twin (opener
  and closer replaced by same-count neutral tokens, as E17). **Six capture points per item**, at 2, 4, 8, 16, 32 and
  48 tokens before the closer. Lexical content and distance since the opener are identical across twins.
- **Comparator `prose_sentiment_delayed`:** 120 items per state where the sentiment-diagnostic word sits 2, 4, 8, 16,
  32 or 48 tokens after the capture point, with neutral text between; twins differ only in that word.
- **Cross-over `fact_once`:** 120 items per state where a single fact (a 4-digit number from two frozen candidates A/B)
  is stated once, then unrelated text; capture at 2, 4, 8, 16, 32 and 48 tokens after it with no recurrence.

**Channels at every capture point (all registered; none added after data).**
1. **Model expectation:** base Qwen (adapter off) on the real text: fraction of 8 sampled 16-token continuations
   (temperature 1, seed 20261025) that contain the closer (paren/string), the diagnostic word (sentiment) or the fact.
2. **Source probe:** logistic probe on the block-44 activation, trained on dev only, scored on test.
3. **Lens generation:** the Oracle lens's native 4 bullets (its usual prompt, greedy first bullet plus 3 samples,
   16-token cap). A frozen parser, committed before capture, scores: paren = an unmatched `)` in the bullet; string =
   the discovery-study rule (`"` straight after the first word) or any unmatched `"`; sentiment = either diagnostic word
   class from a frozen lexicon; fact = the exact number. Per cell: AUROC of the per-item closure/mention rate (0–4)
   against state.
4. **Lens teacher-forced at the true consequence:** the lens's prompt with the activation, its `- ` prefix, then the
   real intervening text up to the consequence token; score log P(A-token) − log P(B-token) at that position under
   activation A vs B. Controls as E15: random donor and opposite-state donor.
5. **Asked:** W1's frozen phrasings (paren, string, sentiment) and a frozen A/B question for the fact.

**Validity gate (per row, on dev, before any lens scoring):** channel 1 must separate states at the 2-token point
(AUROC ≥ 0.80); rows failing are NOT EVALUABLE. The parser is validated on 60 seeded base-Qwen continuations per row
on dev (≥ 90% agreement with a hand check) and then frozen.

**Primary pre-registered contrasts (Holm across the 4 rows; item-cluster bootstrap, 2,000, seed 20261025).**
- **Paren, string:** channel 3 AUROC at 2–8 tokens minus at 32–48 tokens ≥ 0.15 with CI above 0, while the source
  probe differs by ≤ 0.05 (manipulation check) and channel 1 drops by ≥ 0.30.
- **Sentiment comparator:** channel 4 AUROC at 32–48 tokens ≥ 0.80 (the activation's influence does not fade with
  distance). If it does fade, paren/string drops in channel 4 are not interpretable as horizon effects.
- **Fact cross-over:** channel 5 and channel 3 at 32–48 tokens ≤ 0.60 while the source probe ≥ 0.80 (the lens loses a
  once-stated fact the activation still carries) — the horizon account's prediction. ≥ 0.75 falsifies it.

**Reading the two lens channels.** At 32–48 tokens: channel 3 at chance with channel 4 still tracking state = the lens
carries the state and delays expressing it (faithful to the window); both at chance = the state is absent from its
output. Both cases are reported; neither changes a registered verdict.

**Predictions.** Lens generation follows channel 1 (the model's expectation) across positions and not channel 2 (the
probe); sentiment stays readable at every distance; the fact becomes unreadable by 16–32 tokens while the probe holds.
**What would surprise us:** the lens recovers the once-stated fact at 48 tokens (it carries non-window information), or
paren closure in generation stays flat across distance.

**Dated clarification, 2026-10-25 05:50 CET, before any E20 item exists (coordinator; fixes two design gaps and
pins metric details):**
1. **`prose_sentiment_delayed` (redefined).** The state is set **before** the capture point: an opening clause whose
   frozen sentiment word (positive vs negative lexicon, twins differ only in that word) ends ≥ 8 tokens before
   capture. The **consequence** is a later evaluative slot at distance d = 2/4/8/16/32/48 tokens after capture, filled
   in the real text by a word of the same polarity. Channel 4 scores log P(positive slot word) − log P(negative slot
   word) at that slot; channel 1 = base Qwen's 16-token samples containing a word from the matching lexicon.
2. **`fact_once` (redefined so it has a consequence).** The fact (one of two frozen 4-digit numbers) is stated once,
   ≥ 20 tokens before capture, and **recurs** in the real text after a frozen cue (e.g. `the code was`) at distance
   d = 2/4/8/16/32/48 tokens after capture, with unrelated text between. Channel 4 scores log P(number A) −
   log P(number B) at the recurrence; channel 1 = base Qwen samples emitting the true number; channel 3 = the exact
   number in the lens's bullets. The cross-over prediction becomes: readable in lens generation only when the
   recurrence is near (2–8 tokens), with the source probe ≥ 0.80 at every distance.
3. **Paren/string capture index.** Distances are counted in A-text tokens to the closer; the B twin is captured at the
   same token index.
4. **Channel 3 per-cell metric.** Per item, the number of its 4 bullets the frozen parser marks positive (0–4);
   AUROC of that count across A vs B items, ties handled by mid-rank.
5. **Channel 4 for paren/string.** The A-token is the closer; the B-token is the neutral twin token at the same index.
Nothing else in §112 changes.

**Dated clarification 2, 2026-10-25 06:00 CET, before any E20 item exists (answers W-core's five questions):**
1. **Counts.** Every row has **120 pairs** (240 texts: A and its B twin), split by template family, dev 1/3, test 2/3.
2. **Channel 1 (model expectation) counts the fixed A-event in both states:** the closer (paren/string), an
   A-polarity word from the frozen lexicon (sentiment), or number A (fact). Per text, the fraction of its 8 samples
   containing the A-event; channel-1 AUROC = that fraction across A vs B texts. The validity gate uses this AUROC.
3. **Bands.** Near = d in {2, 4, 8}; far = d in {32, 48}; d = 16 is reported but in neither band. Per pair and channel,
   the score is averaged over the distances in the band; the band AUROC is computed over pairs from those averages.
   Every individual distance is also reported (descriptive).
4. **Fact decision rule.** Primary: channel-3 near AUROC minus far AUROC >= 0.15 with its CI above 0, and the source
   probe >= 0.80 in the far band. Falsified if channel-3 far AUROC >= 0.75. Asked-channel values are descriptive.
5. **Inference.** Holm across **three** one-sided tests, one per row: paren, string and fact, each with
   H0: channel-3 near AUROC − far AUROC <= 0. p = (k + 1) / (2,000 + 1), where k = the number of item-cluster bootstrap
   resamples (seed 20261025) with a difference <= 0. A row's prediction holds only if its Holm-adjusted p < 0.05
   **and** its point criteria in §112 hold (effect >= 0.15; source-probe flatness <= 0.05 for paren/string; channel 1
   dropping >= 0.30). **Sentiment is a control, not in Holm:** it passes if channel-4 far-band AUROC >= 0.80 with its
   95% CI lower bound >= 0.70. If it fails, channel-4 results for the other rows are reported as not interpretable;
   channel-3 results stand.

---
