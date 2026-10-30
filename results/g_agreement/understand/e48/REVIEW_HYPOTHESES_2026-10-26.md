# Independent review: why the RL activation verbalizer cannot state syntactic state

Reviewer stance: I have no stake in the "syntactic state as such" story. I read the 13 established facts as data and looked hardest at three things: what the lens was ever paid to write, what the asked channel numerically is, and which "facts" already contain an interpretation.

## 0. Framing points that change which hypotheses matter

**F0a. The reward cannot explain the content/structure asymmetry.** Item 7 says a sentiment word in a bullet does not pay (−0.009 FVE). Neutralising the state token pays only for string (+0.015). A literal language statement moves AR 0.10 of the class gap, and structure statements move it 0.03–0.10. So the RL reward is about equally indifferent to *naming* content and *naming* structure. Yet content is answered 9/9 at ≥0.85 and structure 3/16. Whatever produces the asymmetry did not come from GRPO paying for one kind of name over the other. Two places are left:
- the warm start (SFT/distillation), or
- how Qwen's own circuitry handles an injected residual (base-model property).

Item 5 points to the second: base Qwen with the same injection and a LoRA learns paren *worse* than the lens does. Hypotheses that start from "RL rewarded X" need to explain this.

**F0b. The asked score is not a question-answering score until shown to be one.** It is AUROC over items of log P(phrasing A) − log P(phrasing B), taken after a bullet prompt, in a model trained only to emit "- concept" bullets after an injection. Under that policy, the log-odds between two frozen phrasings could be driven entirely by how much the activation raises the *tokens of each phrasing* as concept bullets, with the question doing nothing. Nothing in the established list rules this out. The answer-at-chance facts (1, 4, 13) and the below-chance facts (item 2) both read differently under it. See H1.

---

## 1. Hypotheses (ranked; rank rationale in section 2)

### H1. Instruction-inert lexical priming: the asked channel measures whether the answer words are concept features of the activation

**(a) Mechanism.** With an activation injected, the lens is in the only mode RL and SFT ever trained: emit bullets whose words are features of the injected state. The question tokens barely move that distribution, so log-odds(A vs B) ≈ how much the activation primes the distinctive tokens of each phrasing. Content answers contain words that are themselves features of the text ("negative", "sports", "French"), and so do the sayable structure-ish rows ("question", "fraction", "math", "item"). Answers for paren, string, depth, cell role or column contain meta-words ("parenthesis", "nested", "header cell") that are not features of being inside a parenthesis. The feature of being inside a parenthesis is "a `)` is coming", which the continuation channel does pick up (item 6).

**(b) Explains:**
- Item 1: content 9/9 vs structure ~3/16.
- Item 2: which structure-ish rows are sayable. The sayable ones have answer words that also occur in the text.
- Item 3: the lens shows structure but almost never states it.
- Item 6: the continuation channel tracks `)` and quote tokens.
- Item 11: GLM lenses close brackets but never name them.
- Item 13: value-word phrasings sometimes help, inconsistently, because it depends on the exact tokens.
- Most importantly, **below-chance rows**: clause embedding 0.22, python argument 0.39, list index 0.42. These are hard to explain as "no information" but easy to explain as lexical priming with the wrong sign.

**In tension with:**
- Item 10: the lens follows questions when the *text* is visible. The hypothesis then needs injection to act as a mode switch.
- Paragraph index 0.82 and sentence position 0.85, where the lexical associate is not obvious. This may be a content confound (H5).

**(c) Distinguishing prediction.** Changing the question should not change the score; changing the *tokens* of the answer should.
- (i) Replacing the question with an irrelevant one ("What colour is the sky?") or with nothing changes per-row AUROC by ≤0.05.
- (ii) Content rows scored with arbitrary label answers fall to near chance. Example: "If the sentiment is positive answer '- A', otherwise '- B'", scored on "- A" vs "- B".
- No other hypothesis here predicts (ii).

**(d) Test** (about 0.5 GPU-h; existing asked-scoring pipeline; test split; all 25 fresh-bank rows plus the 4 below-chance rows).
- Score each item under four prompt conditions:
  - Q (original question)
  - Q0 (no question, just "- ")
  - Qirr (irrelevant question)
  - Qlab (original question with an A/B label mapping, scored on "- A"/"- B")
- Run base Qwen reading the TEXT with Qlab as a usability control. It must reach ≥0.85 on content, or the labels themselves are the problem.
- Pre-registered rule:
  - **H1 supported** if median over rows |AUROC(Q) − AUROC(Q0)| ≤ 0.05, AND content mean AUROC(Qlab) ≤ 0.62 while the base-text control is ≥ 0.85.
  - **H1 falsified** if content AUROC(Qlab) ≥ 0.80, or if removing the question drops content mean by ≥ 0.15.
- Secondary prediction: re-scoring clause embedding with a lexically disjoint paraphrase pair moves its AUROC by ≥ 0.20 (out of the 0.22 inversion).

---

### H2. Small gain under large nuisance: structure *is* in the asked channel, but with ~10× less gain than content relative to per-item variance in the log-odds

**(a) Mechanism.** The answer readout responds to the probe direction with a small but consistent slope. Per-item nuisance in log-odds (topic and code-ness shifting the baseline of each phrasing) is larger, so unpaired AUROC over heterogeneous items sits at 0.5–0.65. Training gave content directions large output gain and structure directions almost none. That is a quantitative gap, not an absent route, which fits how fast a rank-8 LoRA unlocks it (item 5: 25–100 steps).

**(b) Explains:**
- Item 1: "≤0.65" rows. With n=84 (42/42), the SE of AUROC is about 0.06, so 0.60–0.65 is 1.6–2.4 SE above chance.
- Item 4: answers sit at 0.51–0.56 at every layer, consistently on the positive side.
- Item 9: the lens was 0.70 on the steered row.
- Item 5: fast unlock.
- The bank-to-bank swings of ±0.3 (string, table column).

**In tension with:** item 4's 0/136 patch cells. However, whole-position patches also swap nuisance, so they are underpowered by construction.

**(c) Distinguishing prediction.** A *within-item* dose–response shows correct-sign slopes on structure rows even where AUROC is at chance. H1 predicts the slope is zero or wrong-signed for meta-word phrasings. H6 predicts zero slope unless the injection is also placed at the answer position.

**(d) Test** (about 0.5 GPU-h).
- For each test item on 16 structure rows and 9 content rows, add α·Δμ_probe to the injected activation, with α ∈ {−1.5, −0.75, 0, +0.75, +1.5}, and record log-odds.
- Per item, fit the slope. Score the fraction of items whose slope has the sign of the true class direction, with a Wilson CI.
- Also express the effect as slope × class gap / SD of log-odds across items (gain-to-nuisance ratio).
- **Supported** if ≥10/16 structure rows have sign-correct fraction ≥ 0.70 with the Wilson lower bound > 0.5, AND the content-to-structure ratio of gain-to-nuisance is ≥ 5.
- **Falsified** if ≥12/16 structure rows have Wilson CIs covering 0.5.
- CPU companion on sealed data: pooled mean asked AUROC across the 16–18 structure rows, with a row-bootstrap CI. If the CI excludes 0.5, "at chance" is a misreading.

---

### H3. Bag-of-constructs: the reward's additive, nonnegative bullet fit makes the lens's code order-free, so it can say what constructs are *present*, not where the current position *stands* relative to them

**(a) Mechanism.** Reward is the FVE of a nonnegative combination of per-bullet AR vectors. The best-rewarded code is therefore a *set* of things present in the 1–32-token window, each bullet adding one vector, with no way to express relations between positions. The SFT/RL lens then reads activations through that set code. Rows are sayable iff the A/B contrast differs in *which constructs occur nearby*:
- fraction present vs absent
- math present vs absent
- a question present vs absent

They are unsayable iff both A and B contain the construct and differ only in where the position sits relative to it: inside vs after a parenthesis, header vs body cell, depth 2 vs 3, item 2 vs item 4.

**(b) Explains:**
- Item 2's split, including LaTeX fraction, item and math (sayable) vs LaTeX section, table row, list index and python argument (unsayable).
- Item 7: top-reconstructing texts share the state only at base rate, while sentiment, a content word set, runs at 2×.
- Bank dependence (table column 0.47 vs 0.74; string continuation 0.91 vs 0.58), because bank composition decides whether the construct also appears in B items.

**In tension with:**
- Paragraph index 0.82. A count is not a presence contrast unless it is confounded (paragraph 1 has no preceding "\n\n").
- Item 5: base Qwen with no lens is also bad, which suggests the order-free code is not lens-specific. H4 decides this.

**(c) Distinguishing prediction.** Turning a position contrast into a presence contrast on the same row makes it sayable. Example: paren-A "inside an open parenthesis" vs paren-B' "window contains no parenthesis at all", replacing B "parenthesis opened and closed earlier". H1 predicts this does *not* help, because the answer words are still meta-words. H5 predicts it helps only if word content also changes.

**(d) Test** (CPU on sealed bank texts, then ≤0.5 GPU-h).
- **CPU.** For every row in both banks:
  - Train a presence-only bag-of-tokens classifier (binary features, punctuation *included*, preceding 32 tokens, logistic L2) on dev and score AUROC on test. Call it the presence AUROC.
  - Also train a counts version (adds counting; treated as a different hypothesis).
  - Correlate presence AUROC with asked AUROC across rows.
- **H3 supported** if Spearman ρ ≥ 0.6 (row-bootstrap CI excluding 0.3) and at most 2 rows violate the pattern "asked ≥ 0.8 ⇒ presence ≥ 0.8; presence ≤ 0.6 ⇒ asked ≤ 0.65".
- **H3 falsified** if ρ < 0.3, or if paren/string have presence AUROC ≥ 0.8 while unsayable. This is possible: "(" without ")" is a presence feature in a short window.
- **GPU.** Rebuild 84 test items for paren, list depth and cell role as presence contrasts (delete the construct from the B items, length-matched), and run asked scoring. Supported if all three reach ≥ 0.80 while the original position contrasts stay ≤ 0.65.

---

### H4. Inherited from the base model: Qwen's own question-answering circuitry can read content off a foreign injected residual but not local syntactic state; SFT and RL inherit this

**(a) Mechanism.** In ordinary text, a question about bracket or indent state is answered by attending to the *tokens* and recomputing state at the question position (base reading the text gets 0.95). No circuit ever needs to read a precomputed syntactic-state feature from another position's residual. Content features, by contrast, are routinely aggregated across positions. An injected residual therefore offers content in a readable format and structure in a format no existing head reads, regardless of lens training.

**(b) Explains:**
- F0a: the reward is neutral on both, yet there is an asymmetry.
- Item 5: base plus LoRA does no better on paren.
- Item 4: content reaches the answer position by layer 36; structure only at 60–63, via whatever late heads exist.
- Item 11: GLM SFT and RL lenses behave the same.

**In tension with:** item 4's probe reading state at the answer position at 0.86 from the first layer. See flag M3; it may be leakage or a causally inert copy.

**(c) Distinguishing prediction.** Base Qwen with zero-shot injection (no LoRA) shows the same content-yes, structure-no profile, as does the SFT warm start (E37). If base zero-shot content is at chance, H4 is wrong: content reading was *learned*, and the question becomes what the warm-start data taught (H8).

**(d) Test** (≤0.5 GPU-h). Run base Qwen with the lens's injection scale and slot (no adapter) on the asked items, 9 content and 16 structure rows, with a scale sweep {0.5, 1, 2}× and the best scale chosen on dev.
- **Supported** if content ≥ 0.70 on ≥ 6/9 rows and structure ≤ 0.65 on ≥ 13/16.
- **Falsified** if content ≤ 0.60 on ≥ 6/9 at every scale.
- Read alongside E37 rather than duplicating it: if E37 shows SFT ≈ RL and this test shows base ≈ lens, RL is exonerated.

---

### H5. Gist inference: the lens answers by inferring from semantic content, and the "sayable structure" rows are the ones whose state has word-level correlates

**(a) Mechanism.** The lens recovers a semantic gist (topic, register, genre, discourse role) from the activation, much like reading a summary, and guesses answers from it. Sentence type (wh-words), paragraph start (topic-introducing wording), and LaTeX fraction or math (mathematical vocabulary) have word-level correlates. Paren, string, cell role, depth and column were built to have none.

**(b) Explains:**
- Item 2: sentence position 0.85, paragraph index 0.82, paragraph start 0.71, which H3 struggles with.
- Item 1: all content rows.
- Item 7: content-coloured texts rank high.
- The puzzle's suspicious pattern that the "sayable structure" rows are discourse-level.

**In tension with:**
- Item 8: the NLA follows the lens-text part for language, but language *is* gist, so this is consistent.
- Items 12 and 6, which are continuation, not asked, so no real tension.

**(c) Distinguishing prediction.** H3 and H5 diverge on rows where *punctuation-only* presence separates A/B but words do not, such as paren and string in some banks. H3 says sayable; H5 says unsayable. In matched-content banks, H5 predicts sentence position and paragraph index drop to chance. H3 is silent on those.

**(d) Test** (CPU, same pass as H3).
- Train a words-only bag (punctuation, brackets, quotes, backslash commands and whitespace tokens stripped) on dev, and score its AUROC on test for each row.
- **Supported** if Spearman(words-only AUROC, asked AUROC) ≥ 0.6 AND exceeds the presence-bag ρ by ≥ 0.15 (paired row bootstrap).
- **Falsified** if words-only AUROC ≥ 0.75 on ≥ 3 rows where asked ≤ 0.65.
- Optional GPU check (0.5 h): paragraph-index items with paragraphs shuffled within the document, so position is decoupled from intro/conclusion wording. H5 predicts asked drops to ≤ 0.65 while the probe stays ≥ 0.9.

---

### H6. Transport vs conversion: the bottleneck is *getting* the state to the answer position early enough, not converting it into words

**(a) Mechanism.** Per item 4's patching, structure features reach the answer position only at layers 60–63, which leaves no depth to turn them into an answer token. Content arrives by 36. If the state were present at the answer position from the injection layer, the existing question-answering circuit would use it.

**(b) Explains:**
- Item 4: arrival layers and 0/136 patches.
- Item 6: the continuation channel works because the next-token syntax pathway is same-position and late.
- Item 5: the LoRA builds an earlier mover.

**In tension with:** item 4's probe at 0.86 at the answer position from the first layer. If that is real and causal, transport is not the bottleneck.

**(c) Distinguishing prediction.** Adding the injected vector *also* at the answer position (at the injection layer, same scale) raises structure asked AUROC. H1 and H3 predict no change, because the problem is in converting to meta-words or set code. H2 predicts a small, roughly proportional rise.

**(d) Test** (≤1 GPU-h). Run four arms:
- Inject at the slot only (baseline).
- Slot plus answer position.
- Answer position only.
- Slot plus answer position with an opposite-value donor at the answer position. This is the control: answers should follow the answer-position copy if transport matters.

Rules:
- **Supported** if slot plus answer position lifts ≥ 8/16 structure rows to ≥ 0.75 while content stays ≥ 0.85, and the donor arm flips the direction (AUROC ≤ 0.35) on those rows.
- **Falsified** if ≤ 3/16 rows rise by ≥ 0.10.

---

### H7. Readout-mediated answering: the lens can answer only what its readout code carries, and that code carries structure only as *shown* tokens, which the question path does not consult

**(a) Mechanism.** RL turned the lens's internal representation of the injection into a concept-bullet code: content words plus continuation-shaped fragments (93% code-shaped). Asked answers are computed from that code. Structure is in the code only as shown tokens (`)`, `"`, indentation), not as anything the question-answering path maps to a meta-answer.

**(b) Explains:** items 3, 6, 12, and 8 (the NLA follows the swapped remainder, i.e. what the lens-text part lacks).

**In tension with:** item 4's probe (the state is readable at the answer position), unless it is unused.

**(c) Distinguishing prediction.**
- (i) Base Qwen given only the lens's free readout *text* for an item, plus the question, reproduces the asked-AUROC row profile.
- (ii) Shown-token rates in readouts discriminate paren and quote, e.g. a `)` rate difference.

If (ii) holds but the asked score stays at chance, the information is in the code yet unused by the question path. That supports H1 over H7's strong form.

**(d) Test.**
- **CPU on the sealed 13,420 readouts:** per row, AUROC of shown-token features (e.g. any `)` minus `(` in bullets, quote parity, leading-space count) between A and B items.
- **GPU (≤1.5 h if readouts for the asked items are not already sealed):** 4 samples per item; base Qwen answers from the readout text alone.
- **Supported** if Spearman(readout-text AUROC, asked AUROC) ≥ 0.7 and readout-text AUROC is ≤ 0.65 on ≥ 12/16 structure rows.
- **Falsified (strong form)** if readout-text AUROC ≥ 0.75 on paren, quote or depth. The readouts then carry the state in readable form and the asked channel ignores it, which favours H1.

---

### H8. Warm-start vocabulary: the distillation teacher's bullets define which properties have a verbal slot, and RL only reweights within it

**(a) Mechanism.** The SFT/distilled targets were written by a teacher asked for "distinct concepts" in a context. Teachers describe passages: topic, sentiment, language, genre, "a question", "LaTeX math", "a fraction", "start of a paragraph". They almost never write "inside an open parenthesis, depth 3, header cell". The lens learned a mapping from activation to words only for concepts with nonzero mass in that vocabulary.

**(b) Explains:**
- Items 1 and 2: sayable means describable concepts.
- Item 3: 6 statements in 13,420 readouts.
- Item 5: one targeted dataset creates the slot within 25–100 steps.

**In tension with:**
- The falsified "description plausibility D" (ρ 0.03). The difference here is that this uses measured *exposure* in the actual training targets, not rated plausibility, but the prior is lowered.
- Item 5's base result (base names as well), which says the slot is cheap to create from scratch.

**(c) Distinguishing prediction.** Asked AUROC tracks the log frequency of the row's concept lexicon in SFT targets, independent of presence or word-bag AUROC (H3, H5).

**(d) Test** (CPU, if the warm-start corpus is in `cache/`).
- Pre-register a lexicon per row (e.g. paren: parenthes*, bracket*, aside; cell role: header, cell; depth: nest*, depth, level) and count hits per 10⁴ bullets.
- **Supported** if Spearman ρ ≥ 0.5 and every row with frequency < 1 per 10⁴ has asked ≤ 0.65.
- **Falsified** if ρ < 0.2, or if ≥ 3 rows with frequency ≥ 10 per 10⁴ are unsayable.

---

## 2. Ranking (prior plausibility × cheapness × decisiveness)

| Rank | Hypothesis | Prior | Cost | Decisive because |
|---|---|---|---|---|
| 1 | H1 instruction-inert lexical priming | high: explains the below-chance rows nobody else does | 0.5 GPU-h | label-mapped content answers either survive or don't; one run rewrites what "asked" means |
| 2 | H2 small gain under nuisance | high: "≤0.65" includes rows ~2 SE above chance | 0.5 GPU-h + CPU | a paired dose–response separates "absent" from "weak" with ~5× more power than unpaired AUROC |
| 3 | H4 inherited from base | medium-high: follows from F0a and item 5 | 0.5 GPU-h | decides whether to look at training at all; complements E37 |
| 4 | H3 bag-of-constructs | medium: ties directly to the reward form | CPU, then 0.5 GPU-h | presence-vs-position rebank is a clean intervention |
| 5 | H5 gist inference | medium: rows that are "sayable structure" look discourse-level | CPU | same pass as H3; the two are discriminated against each other |
| 6 | H6 transport vs conversion | medium-low: the item-4 probe argues against it | 1 GPU-h | dual injection is a direct intervention on the claimed bottleneck |
| 7 | H7 readout-mediated | medium-low | CPU + ≤1.5 GPU-h | partly redundant with H1; the CPU half is nearly free |
| 8 | H8 warm-start vocabulary | low-medium: close to falsified D | CPU, data-dependent | only if the corpus exists |

**Suggested Thursday plan** (about 2.5 GPU-h):
- **One GPU session:** H1 (4 prompt conditions), H2 (5-point dose sweep), H4 (base zero-shot), and H6 (dual injection). All are forward-only scoring on the same 25+4 rows. Bundle them in one job with one preregistration section.
- **CPU, in parallel:** H3, H5 and H8 bags and lexicon counts, plus the H7 shown-token AUROC and the H2 pooled-AUROC re-analysis.
- **Pre-registration:** test split only, rows fixed before running, Wilson CIs for sign fractions, row bootstrap for every across-row ρ. Rows with |AUROC_W1 − AUROC_fresh| > 0.2 (string, table column, json_type) are excluded from correlations and reported separately.

---

## 3. Facts that look misread

**M1. "At chance (≤0.65)" lumps weak signal with no signal.** With 42/42 items the SE of AUROC is about 0.06, so 0.65 is p≈0.01 one-sided. Report per-row CIs and a pooled structure-row mean with a row bootstrap before calling it a blind spot. Item 4's "0.51–0.56 at every layer" is suspiciously one-sided.

**M2. Below-chance rows are signal, not blind spots.** Clause embedding 0.22 is about 4.5 SE below 0.5. Python argument 0.39–0.50, list index 0.42 and list depth (continuation) 0.44 point the same way. Inverted AUROC means the channel *does* depend on the state, with the wrong sign. That is the signature of a phrasing or lexical confound (H1), not of absent access. The current story ("fails syntax role / clause embedding") files it as failure.

**M3. Item 4's two halves conflict, and the probe half lacks a control.** A probe reading state at the answer position at 0.86 *from the lens's first layer* is hard to reconcile with patching showing paren arriving only at 60–63.
- Needed control: the same probe with no injection, or with a shuffled-label injection, at that position. Prompts are item-independent, so anything above 0.5 before attention can carry the injection is leakage, e.g. through position or length.
- If it is real, the early copy is causally inert. "Reaches its answer position" in the puzzle statement should then read "is decodable at, but not used at".

**M4. Item 5 is not evidence of "knowledge the lens withholds".** A rank-8 LoRA through a 27B model, on a feature with linear-probe ceiling 1.00, is a probe with a verbal head. Shuffled ≤0.48 shows it learns the labels, not that the lens latently "knew". Base Qwen naming as well or better on 4/5 rows says the unlock is generic. Also confirm that the 0.80 is on test, not dev.

**M5. Item 9 cannot mean what it says for a monotone reader.** Adding the *same* vector along the probe direction to every item preserves item ranking, so AUROC should not change for any reader that is monotone in that direction. A collapse to 0.49–0.50 implies one of two things:
- The intervention was really projection or clamping to a common value. That is an ablation, and it shows both readers *use* the probe direction. For the lens at 0.70 this contradicts "never uses".
- The readers saturate, in which case H2-style gain analysis is needed.

Check the code.

**M6. "The reward barely registers naming" cuts both ways** (F0a). It is equally true for sentiment (−0.009), so the RL objective cannot be why content is sayable and structure is not. Expect E37 to show the SFT lens is equally blind. If so, the puzzle should be reframed away from "what an RL verbalizer can state".

**M7. Bank effects are the size of the effects being explained.** Examples: string continuation 0.91→0.58, table column 0.47→0.74, value-word phrasing 1/6 replication, the λ gradient not replicating. Any across-row correlation (including the falsified D, the 32-token persistence ρ, and every test above) is bounded by this test-retest noise. Estimate a per-row W1-vs-fresh reliability and report correlations against that ceiling before calling a ρ of 0.03 a falsification.

**M8. Item 7's "AR aligns string 1.00" and "neutralising changes FVE ≤0.015" are not in tension; together they explain why RL never learned state.** Alignment is a projection on one direction, while FVE sums over about 5120 whitened directions. The state's contribution to reward is at most about 0.015 FVE. Compare that with the within-group reward SD in the GRPO logs (CPU). If 0.015 ≪ SD, RL had no usable gradient for state, and the question shifts to the warm start or the base model (H4, H8).
