# §88–§98 (E1–E11). Why the Oracle lens can't see structure: an exploratory mechanism programme

Registered 2026-10-24 01:30 CEST, before any E-run. Coordinator: Guiv. Model Qwen3.6-27B; readers at their native sites
(Oracle lens and AR at block 44, NLA and its decoder at block 42, J-lens at block 44).

**Status of this brief.** These experiments are **exploratory**. Each states its question, design, a prediction and what
would surprise us, but there are no pass/fail thresholds. **Every result is reported, whatever it shows.** The
confirmatory work is in `BRIEF_BLINDSPOT.md` §70–§87. The shared rules below still apply: sealing, no sign flips, frozen
inputs before scoring, and logging.

## The organising hypothesis

**The Oracle lens can only report what text can *describe*, not what text can only *enact*.** Its reconstructor (AR)
maps text to the average activation preceding it:
- Text *about* volcanoes and text that *is* about volcanoes land near the same activation, so meaning is reachable by
  description.
- "Inside a parenthesis" is a state text can only *be in*, not *say*. The AR given "the text is inside a parenthesis"
  returns the activation of prose about parentheses, not the activation of being inside one.

The Oracle lens is trained to write descriptions, so structure is unreachable for it. The NLA's decoder shares the
bottleneck in a weaker form, because it is trained on exact reconstruction and writes more.

This hypothesis explains W1 (structure at chance, meaning near ceiling), W4's reconstruction-only ordering (meaning 0.76,
state 0.68, counting 0.54), W6 (weak, not absent) and W3 (an uninformative residual). Each experiment below tests a
different consequence.

## Shared rules

- **Inputs:** W1's sealed block-42 and block-44 activations, items, labels and probe directions
  (`results/g_agreement/blindspot/w1/analysis/`, and W-core's cache). Most E-runs need **no new target capture**.
- **Rows:** the 16 rule-(i) structure rows plus the 9 evaluable semantic rows ("the 25 rows"), unless a run says
  otherwise. Classes are as frozen in W1.
- **Operations:**
  - The integrator operates every pod: shared volume, warmed timing units, hold renewer, setup allowance outside
    science.
  - Owners commit locally; the integrator pushes.
- **Caps:** each run's science cap is min(1.5F + 360, cap below) s, with F measured from warmed units.
- **Logging:**
  - Scores are sealed before labels are joined.
  - Results go to `results/g_agreement/understand/e<N>/`, each with a `RESULTS.md` that opens with the prediction and
    says plainly whether it held.

---

## §88 E1. Describe versus enact (the direct test of the hypothesis)

**Owner:** W-mechanism. **Cap:** 0.4 GPU-h. **Depends on:** S2's description outputs, when S2 completes.

**Question.** Does text that *describes* a value move the AR along that row's probe direction, compared with text that
*enacts* it?

**Design.**
- **Description arm:** S2's frozen value-stating texts for the W1 rows (already built), so no new texts are needed.
- **Enactment arm:** for each W1 test item, the item's own text, i.e. the span that ends at the read position.
- For both arms, run the AR (block 44) and project its output on the row's unit probe direction (block 44).
- **Fidelity** = (mean projection, value A − value B) ÷ (the real class-mean gap). Bootstrap the CI over items or texts.
- **Decoder arm:** repeat both arms with the NLA's decoder at block 42, if the NLA repo's decoder can be loaded (record
  it if not).

**Prediction.**
- Structure rows: enactment fidelity is high, description fidelity is near 0.
- Meaning rows: both are high.

The NLA decoder shows the same pattern, weaker.

**What would surprise us:** description fidelity high on structure rows. That would mean the AR *can* represent
structure from words, so the bottleneck is in the Oracle lens's inverter, not the AR. E3 then locates it.

**Outputs.** Per row: description and enactment fidelity, with CIs, for the AR and the decoder. One figure: rows sorted
by class, two bars each.

## §89 E2. Which directions can any text reach? (the AR's image)

**Owner:** W-mechanism. **Cap:** 0.3 GPU-h.

**Question.** What fraction of each probe direction lies inside the span of everything the AR can output?

**Design.**
- Run the AR on 5,000 diverse text spans from the frozen §79 corpus (seeded sample, frozen list), 16–64 tokens each.
- Compute the AR outputs' principal subspace at 95% and 99% variance.
- For each W1 unit probe direction u: the image fraction ‖P u‖².
- **Baselines:**
  - (a) 200 random unit directions;
  - (b) the same calculation on the *real* activations' principal subspace, from the same spans captured at block 44.
- Repeat with the NLA decoder at block 42, if available.

**Prediction.** Structure directions have a small image fraction, near the random baseline; meaning directions a large
one. In the real activations' subspace, both are large.

**What would surprise us:** structure directions well inside the AR's image. Then the AR *could* output them, and the
failure is about which text the Oracle lens chooses (see E3 and E6).

## §90 E3. Where does structure die inside the reader?

**Owner:** new chat W-internals. **Cap:** 0.6 GPU-h.

**Question.** Does structure information enter each reader and fail to come out as words (a decoding problem), or is it
lost at the input (a representation problem)?

**Design.**
- For each reader (Oracle lens, NLA, J-lens), run its forward pass on the W1 activations for the 25 rows, using all 168
  items per row (dev and test).
- No generation: one forward pass of the reader's asked prompt, teacher-forced up to the answer position.
- Hook the reader model's residual stream at every layer, at two positions: the injection position, and the last
  position before the answer.
- Fit grouped-CV logistic probes (grouped by W1 template cluster) for each row's label, per layer and position.
- Report probe AUROC against reader layer, next to the reader's asked AUROC (from W1).

**Prediction.**
- In the Oracle lens, structure is read near 1.0 right after injection and decays through its layers, or stays high to
  the end while its output is at chance (a decoding problem).
- In the NLA, it decays less.

**What would surprise us:** structure at chance from the reader's very first layer. That would mean the Oracle lens's
input projection discards it, a representation bottleneck rather than a verbalisation one.

**Outputs.** Per reader, a layer × row heatmap of probe AUROC, plus a summary curve per class.

## §91 E4. The readers' receptive fields (gradient sensitivity)

**Owner:** W-internals. **Cap:** 0.6 GPU-h.

**Question.** Which input directions does each reader's answer depend on at all?

**Design.**
- For each reader and each item (25 rows, test items), compute the gradient g of the reader's asked log-odds with
  respect to the injected activation.
- **Per row:** the mean |cos(g, u)| with the row's probe direction u, and a random-direction baseline.
- **Pooled:** the top-k singular vectors of the stacked gradients, giving the reader's "receptive subspace". Then report
  the fraction of each u inside it, for k = 16, 64 and 256.

**Prediction.**
- The Oracle lens's receptive subspace excludes structure directions and includes meaning directions.
- The NLA includes both, structure weaker.
- The J-lens includes exactly the directions that move the next token (for example parenthesis, not table column).

**What would surprise us:** strong gradient alignment with structure directions in the Oracle lens. Its *output*
depends on them, yet its asked AUROC is at chance. Then it reads structure but answers the question wrongly, an
elicitation problem.

## §92 E5. Phrasing robustness (is it elicitation?)

**Owner:** W-core. **Cap:** 0.3 GPU-h.

**Question.** Is the structure blind spot robust to how we ask?

**Design.**
- 6 rows: 3 structure (`table_column`, `prose_paren`, `python_depth`) and 3 meaning (`prose_sentiment`, `prose_topic`,
  `python_error`).
- For each row, **8 phrasing pairs** per reader, written and frozen before any scoring:
  - direct question form;
  - statement form;
  - a reader-native format (Oracle lens bullets, NLA statements);
  - a "which is more likely" form;
  - two paraphrases;
  - two pairs that name the value in plain words ("the next character should be a closing bracket").
- Score W1's sealed test activations, all 3 readers, with W1's scorer. No new capture.

**Prediction.** Structure stays near chance for the Oracle lens under all 8 phrasings; meaning stays near ceiling.

**What would surprise us:** any phrasing that lifts Oracle-lens structure AUROC above 0.75. Then W1's blind spot is
partly elicitation, and that phrasing tells us what the Oracle lens *can* express. Report the best phrasing per row, and
the spread.

## §93 E6. Can it show what it can't say?

**Owner:** W-core. **Cap:** 0.5 GPU-h.

**Question.** Does a reader *enact* structure in its free text even when it can't *state* it?

**Design.**
- **(a) Free:** script-check the free readouts W1 already sealed (priority rows) for enacted structure, e.g. closing
  brackets, column separators, indentation. No GPU.
- **(b) Continuation:** if the Oracle lens and NLA accept a "continue the text" style prompt, use it to generate 32
  tokens per item for scriptable rows: `prose_paren`, `python_string`, `python_indent`, `list_depth`, `table_column`.
  - Score, by script only, whether the continuation behaves as the value implies: for example, it closes ")" before
    opening a new "(" (inside vs outside), or it ends the string, or it matches the indentation depth.
  - AUROC of that behaviour against the label.
  - Record if a reader's format refuses continuation; then only (a) applies to it.

**Prediction.** The Oracle lens enacts structure above chance in continuations (say 0.65–0.8) while stating it at
chance. That would be the "show, not say" dissociation.

**What would surprise us:** the Oracle lens is at chance on enacting too. Then the information truly doesn't get through
it, consistent with E2 and E3 placing the loss early.

## §94 E7. Neel's swap, on the NLA's native layer

**Owner:** W-mechanism. **Cap:** 0.8 GPU-h. **Depends on:** the NLA decoder loading (E1's decoder arm establishes this).

**Question.** What does the NLA's *extra* reconstruction, beyond the Oracle lens's, carry, and does the NLA follow it?

**Design.**
- At block 42, for each test item of the 25 rows:
  - ĥ_OL = Dec(OL(h)): the NLA decoder applied to the Oracle lens's greedy readout;
  - ĥ_NLA = Dec(NLA(h));
  - Δ = ĥ_NLA − ĥ_OL.
- Use W4's pair design (40 directed pairs per row).
- **Arms, all read by the NLA at 42 with W1's asked scoring:**
  - h′ = ĥ_OL,i + Δ_j (swap);
  - ĥ_OL,i + Δ_i (self);
  - ĥ_OL,i alone;
  - ĥ_NLA,i alone;
  - Δ_i alone;
  - ĥ_OL,i + Δ_random.
- **Also:** probe Δ for each row's label (grouped CV).

**Prediction.** Structure information lives mostly in Δ:
- in the swap arm, structure answers follow donor j;
- meaning answers follow recipient i;
- probes on Δ read structure well and meaning less.

**What would surprise us:** structure carried in ĥ_OL. Then the Oracle lens's *text* contains the structure (seen
through the NLA's decoder) and its reporting is the problem.

**Deviations.**

- **2026-10-24 03:58 CEST (integrator, operations only, before any E7 output; Guiv instruction):** E7 attempt 1, on W-mechanism's packed pod `h2v9hge67xmcud` (request `7b382c67`), got **0 s of science** and is recorded INCOMPLETE. The shared 2,400 s setup allowance ran out while the NLA verbaliser was loading. There were two causes: a late operator start (setup began about 7.5 min after the inputs had landed, because an upload command hung), and the native-42 decoder `ar_reconstructor` files being missing from the weights volume, so the pod had to download them (119 s). E7 gets one fresh solo attempt on its own pod, with the same request and code, a 2,880 s cap, min(1.5F + 360, cap) from its own first science, and 2,400 s setup. **No rule, item or threshold changes.**

## §95 E8. Gain curves for all 40 rows

**Owner:** W-core. **Cap:** 1.0 GPU-h.

**Question.** How much push along each concept's direction does each reader need before its answer moves?

**Design.**
- For all 40 W1 rows: 40 test items of value B, h + α · d with d the unit probe direction scaled to the class-mean gap,
  α ∈ {0, 0.5, 1, 2, 4, 8}.
- Each reader's asked log-odds at its native block (Oracle lens and J-lens: add at 44; NLA: add at 42, using that
  block's direction).
- No generation and no judge.
- **Per row and reader:** the gain (slope of log-odds against α over the linear range) and the dose that reaches the
  value-A median.

**Prediction.** The Oracle lens's gain on structure rows is many times lower than on meaning rows. The NLA's ratio is
smaller.

**What would surprise us:** comparable gains across classes. Then the Oracle lens *responds* to structure directions but
from a misplaced baseline: an offset problem, not insensitivity.

## §96 E9. One figure: what predicts each reader's blind spots?

**Owner:** W-core, with the coordinator (CPU only, after E1, E2, E4 and E8).

**Design.** One point per row (40 rows), with three predictors:
- **describability:** E1's description fidelity and E2's AR-image fraction;
- **next-token relevance:** gradient of the target's next-token logits onto u, computed once on the W1 activations
  (~0.1 GPU-h, inside E4's budget);
- **presence:** probe AUROC.

Outcomes are each reader's asked AUROC and E8's gain. Report rank correlations and simple regressions. Descriptive.

**Prediction.** The Oracle lens tracks describability, the J-lens tracks next-token relevance, and the NLA tracks
presence with attenuation.

## §97 E10. Qualitative case studies (Neel's request)

**Owner:** the lens chat (R-Lens/J++). **Cap:** 0 GPU-h, ≤ $10 API.

**Design.**
- **Pool:** paired free readouts on the same activations. W1's sealed free readouts (priority rows, NLA and Oracle
  lens), W6's 480 Oracle-lens readouts, and §61's paired readouts. The pool is frozen before analysis.
- **Extraction:** a blinded LLM (frozen prompt) lists atomic claims per readout. Claims are matched across the two
  readers for the same activation.
- **Clustering:** cluster "said by one reader only" claims into types.
- **Hand-picked examples:** 6–8 illustrative pairs for the write-up, selected by a rule frozen before reading:
  - the 2 pairs per type with the most one-sided claims;
  - 2 random pairs.

**Outputs.** A type table with counts, plus the example pairs verbatim.

### Dated operational registration — 2026-10-23 23:44 UTC, before E10 API extraction

Guiv's rulings: exclude W6's 480 missing NLA partners, retaining their inventory; select two pairs from each of the three most frequent discovered types plus two frozen seeded random pairs. Pool: 3,272 pairs (W1 1,680; §61 1,592), with source seals and SHA-256 hashes in `results/g_agreement/understand/e10/POOL_MANIFEST.json`. §61 artificial mismatches are excluded. W1 native sites are Oracle44/NLA42 (same item/token, distinct vectors); §61 retains its original sites. Use exact nonempty raw generated strings, including incomplete endings and markers: W1's parsed NLA fields failed the source parser, so parsed emptiness is not missing generation. No repair.

Deviation disclosed before extraction: raw outputs from one W1 pair accidentally surfaced during metadata inspection. All samples of item `c3c3160303c81bf79e974959` are excluded from illustrative selection, retained in the fixed pool. No correctness or old §61 annotations enter E10.

Frozen implementation: `projects/g_agreement/understand/e10/`; exact prompts, schemas and code hashes in `PROMPTS.json` and `PLAN.json` beside the pool manifest. Gemini 2.5 Flash Lite, Google AI Studio only, temperature0, thinking off, strict schema; ≤$10 reserve-before-send ledger; 0 GPU-h. Independent per-readout extraction (5,236 unique raw strings, 1,309 batches, no paired counterparts within a batch), one-to-one claim matching, then blinded type discovery on 512 seeded one-sided claims and frozen-taxonomy classification. Exact evidence required; failures stay missing; no retries or format repairs. Each stage is sealed before the next; reader identities join only after final annotation seal. Type frequency means classified one-sided claim count; top pairs rank by count of that type, ties by seeded hash, deduplicated across types and random pairs. Random pairs stay selected if annotation is missing; report any shortfall. Every result descriptive: no truth, accuracy or causal reader claim. Claim counts may reflect style, truncation and verbosity. See PLAN.json for all details.

### Dated privacy amendment — 2026-10-24T03:57:25.717675+02:00, before any E10 inference

Guiv explicitly approves Gemini 2.5 Flash Lite via OpenRouter only, ≤$10 hard cap, W1/§61 raw readouts and their blinded derived claims only; no source prompts, labels, keys or file paths. Set `provider.data_collection=deny` and `provider.zdr=true`; pin provider, disable fallbacks and HTTP redirects. Offline schema/path/key checks pass for all 1,309 extraction batches. No pool, claim-matching, taxonomy or example-selection change. PLAN/PROMPTS and code hashes are re-frozen before scoring.

Read-only route inventory returned HTTP200 with zero ZDR endpoints for the approved model; its three advertised endpoints are AI Studio. No inference sent ($0). OpenRouter documents that Google ZDR excludes AI Studio. Its separate own logging/use-of-inputs settings could not be verified because native browser controls timed out; the runner also requires an observed-off account-settings proof before sending. Blocked pending a compliant route and that proof; no alternate destination selected. Detailed proof hashes in `results/g_agreement/understand/e10/PRIVACY_CHECK.json`.

## §98 E11. What lives in the residual and in the reconstruction (directionally)

**Owner:** W-mechanism. **Cap:** 0 GPU-h (CPU, existing W3 data).

**Design.**
- PCA of h, of AR(OL(h)) and of r = h − AR(OL(h)), on W3's sealed test items.
- For each W1 probe direction: its projection fraction in the top-k components of each (k = 16 and 64).
- How the reconstruction's top components align with the real activation's.

**Prediction.** Structure directions sit in r's and h's top components but not in AR(OL(h))'s. Meaning directions sit
in all three.

---

## Order and budget

1. **First (on existing activations; settles representation vs elicitation):** E5, E1, E3 (~1.3 GPU-h).
2. **Then:** E4 and E7 (~1.4 GPU-h).
3. **Then:** E8 and E6 (~1.5 GPU-h).
4. **Alongside, on CPU and API:** E10, E11, then E9.

Total about 4.2 GPU-h, plus setup. Compute stops Tuesday 27 October at 23:59 Europe/Zurich.
