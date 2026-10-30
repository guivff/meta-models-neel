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

- **2026-10-24T05:29:26+02:00 (W-mechanism; coordinator ruling in this session; operations only, before batched E7 launch):** The solo attempt on `vpq6at1aiw61i6` is preserved as INCOMPLETE: 40.436461 s of science; its median was 13.312720 s per **eight-item generation unit** (347 units; generation-only forecast 4,619.513925 s). The native API already batched generation, decoding and scoring at eight; increase **generation to 32**, retaining native greedy k=1, max_new_tokens=128, prompts, extraction and ordering of the sealed final outputs. Decoder and scorer keep their existing batches of eight, including the original candidate pairing and canonical decoder batch boundaries. One live NLA verbalizer and one native-42 decoder load and warm in the same process, within 2,400 s setup. An unscored warm-up must match raw generated token IDs and strings at batch32 versus batch8 exactly; any mismatch stops without repair or a fallback choice.
  A deterministic pilot schedule, frozen before compute from the unchanged pair plan, retains all its results and measures the next three real warmed units for each of four phases: generation, CPU decode-input freezing, native decoder, and six-arm scoring. Decode the dependencies of the first three original scoring units early; acquire every remaining item and arm afterward, with no selection, loss or duplicate retained output. Science starts before the first retained pilot unit and never resets. Full F includes all four phase forecasts and the measured residency-transfer overhead for both pilot and completion; seal `FULL_WARMED_FORECAST.json` before admitting the remaining work. If the batched full forecast F still exceeds 2,880 s, the coordinator permits a ceiling of 7,200 s (2 GPU-h), with actual cap **min(1.5F + 360, 7,200)**; otherwise the original ceiling 2,880 s remains. If the full warmed forecast does not fit the selected cap and retrieval reserve, stop INCOMPLETE. Carry the prior 40.436461 s of science conservatively against the selected cumulative cap and preserve the zero-science packed attempt separately. No rows, items, random draws, arms, prompts, maximum tokens, probe fits, score orientation, analysis or scientific prediction change.

- **2026-10-24 06:20 CEST (coordinator, operations only, before any E7 production output):** batched attempt
  `6uwn43fyz1a3sw` stopped in setup (0 s science) because batch-32 greedy generation did not reproduce batch-8 output
  token for token on GPU. Bit-identity across batch sizes is not a scientific requirement: bf16 kernels are not
  batch-invariant, and no E7 production output exists at any batch size, so every readout will come from one setting.
  Ruling: (1) W-mechanism first checks padding (left padding, attention mask and position ids) on GPU parity items. (2)
  The parity check becomes descriptive with a frozen tolerance: on the pilot's parity set, proceed if ≥ 90% of readouts
  are identical over their first 32 tokens and the median first-divergence position is ≥ 32; otherwise stop as NO_FIT
  (a likely padding bug). (3) Production uses batch 32 for every item. The parity rates are reported in RESULTS.md. Cap,
  setup, rows, items, arms and analysis unchanged.

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

### Dated substitution and cap amendment — 2026-10-24T04:38:50.793669+02:00, before any E10 inference

Guiv approves **Gemini 3.1 Flash Lite via Google Vertex through OpenRouter**, same frozen W1/§61 pool and privacy restrictions, and then raises the API **hard cap to $20** (0 GPU-h). This supersedes the earlier $10 allowance for E10 only. The chosen route is `google-vertex/global`, no fallback or redirect, explicit ZDR and deny data collection. Model/route and fresh metadata hashes are frozen in PLAN/PROMPTS. Logged-in account UI verified: paid training off; OpenRouter use-of-inputs/outputs discount disabled account-wide; default workspace input/output logging off; no trace destination configured. Evidence in LOGGING_VERIFICATION.json, local launch proof in cache. No account setting was changed.

Use the supported Gemini 3 **minimal reasoning** level (not a claim of fully disabled thinking); all output/reasoning charges are included in the reserve-before-send ledger. Price ceiling $0.25/M input and $1.50/M output. Raise match output allowance 1,536→4,096 and classify allowance 2,048→6,144 tokens to fit unchanged batches of opaque IDs and strict JSON. No extraction/matching prompt, source pool, batching, claim/type rule, example selection or missingness policy changes. The first frozen extraction batch may be checked for operational success and then reused from its exact-wire cache; no additional pilot, paid retry or format repair. No E10 inference has run before this registration.

## §98 E11. What lives in the residual and in the reconstruction (directionally)

**Owner:** W-mechanism. **Cap:** 0 GPU-h (CPU, existing W3 data).

**Design.**
- PCA of h, of AR(OL(h)) and of r = h − AR(OL(h)), on W3's sealed test items.
- For each W1 probe direction: its projection fraction in the top-k components of each (k = 16 and 64).
- How the reconstruction's top components align with the real activation's.

**Prediction.** Structure directions sit in r's and h's top components but not in AR(OL(h))'s. Meaning directions sit
in all three.

## §99 E12. Does the surrounding text bring structure back? (the context control)

Registered 2026-10-24 04:15 CEST, before any E12 run. Motivated by Celeste De Schamphelaere's MAEM draft (Appendix J):
a text generator that *enacts* rather than describes still fails on positional and structural features, and an LLM
shown the corpus context mostly recovers them. Her reading is that the direction doesn't carry the context. That
competes with our describe-vs-enact hypothesis, and this run separates the two.

**Owner:** W-mechanism. **Cap:** 1.0 GPU-h. **Depends on:** nothing new; W1's sealed activations, items and phrasings.

**Question.** If the reader also sees the text that produced the activation, does structure become readable? And if it
does, is that the activation or just the text?

**Design.** The 25 rows, W1's test items, W1's asked scoring (two frozen phrasing pairs, paired log-odds, AUROC with the
frozen template-cluster bootstrap). Oracle lens at block 44; NLA at block 42 as a second reader if its prompt accepts a
prefix (record it if not). Arms, each on the same items:
- **(a) Activation only:** the reader's native prompt, as in W1. Reproduces W1 (check against the sealed W1 scores).
- **(b) Text + activation:** the item's text up to and including the read token is placed in the reader's prompt
  before the injection placeholder, then the activation is injected as usual.
- **(c) Text only:** as (b), but nothing is injected (the placeholder keeps its own embedding).
- **(d) Text + wrong activation:** as (b), but the injected activation comes from W1's frozen random donor of the
  opposite value.

The prompt template for (b)–(d) is frozen in the run's PLAN before scoring and is identical across arms. The readers
were not trained with a text prefix, so (b)–(d) are off their training distribution; that caveat goes in RESULTS.md.
KV-olens (reading the whole context through attention) has no checkpoint available to us and is not tested.

**Key contrasts.** Per row and per class: (b) − (c), the activation's contribution once the text is visible;
(b) − (d), whether that contribution is specific to the right activation; (b) − (a), what the text adds.

**Prediction.** (c) is already well above chance on structure rows, because the answer is visible in the text, and
(b) ≈ (c) ≈ (d): the reader uses the text and ignores the activation on structure rows. On meaning rows the activation
still adds something ((b) > (d)).

**What would surprise us:** (b) > (c) and (b) > (d) on structure rows. The activation would then carry readable
structure once the reader has the context to interpret it, which supports Celeste's account over ours. If (c) is near
chance as well, the reader can't read structure even from plain text in this format, and W1's blind spot partly
reflects the elicitation format rather than the activation.

**Dated note, 2026-10-24 06:50 CEST (coordinator, operations only, before any E12 output is analysed):** the packed
attempt (pod in booking `b404b8a9`) stopped INCOMPLETE after the Oracle paths, because untimed NLA paths counted as zero
in the forecast and the cap never grew to cover them. Ruling: (1) if the Oracle-lens arms (a)–(d) are complete for all
2,100 items and sealed, they are analysed as registered, as the primary E12 result, reported as Oracle-only; (2) the NLA
arms run as a fresh NLA-only attempt in which every path is timed (one unscored warm-up plus 3 warmed units) before
admission, cap min(1.5F + 360, 3,600) s, setup 2,400 s; (3) any incomplete Oracle path is reported as INCOMPLETE and
rerun in the same fresh attempt. No arm, item, prompt or contrast changes.

## §100 W12. Sentence and paragraph structure rows

Registered 2026-10-24 04:15 CEST, before any item is built. Motivated by Neel's 12 October remark that Camila and
Achim found the NLA "much better at capturing structural information about the text… sentence structure and paragraph
structure", which W1 covers only partly (sentence count, parentheses, quotes).

**Owner:** W-core (items and analysis); the integrator runs it. **Cap:** min(1.5F + 360, 2,400) s; at most 0.8 GPU-h
including capture.

**Rows (binary; value A / value B; read at the final token of the prefix):**
1. `syntax_role`: the current noun is the grammatical subject / the object of its clause (same noun, word order and
   voice varied by family).
2. `sentence_type`: the current sentence is a question / a statement, with the form already decided by the prefix
   ("Did the…" vs "The… did").
3. `sentence_position`: within the first 3 words of the sentence / after word 12.
4. `paragraph_index`: in the first paragraph / in the third or later paragraph (blank-line separated).
5. `paragraph_start`: in the first sentence of a paragraph / later in the paragraph.
6. `clause_embedding`: in the main clause / inside an unclosed relative clause ("the clerk who…").

**Amendment allowed before the freeze only:** if Camila names the features she and Achim saw before the items are
frozen, up to three rows above may be swapped for hers, with a dated note. After the freeze, no row changes.

**Design.** As W1 exactly: 12 authored template families per row (6 dev, 6 test), 42 items per value per split, exact
length matching, one domain label `syntax`, classes assigned in the freeze file before capture. Same readers and sites
(Oracle 44, NLA 42, J 44, logit 44), two frozen phrasing pairs per reader, the same probe ceiling and gates
(probe ≥ 0.85, mismatched AUROC ≤ 0.60), the same 2,000-sample template-cluster bootstrap. Asked scoring only; no free
readouts.

**Prediction.** Probe ≥ 0.95 on all six. Oracle lens near chance (≤ 0.60) on `syntax_role`, `sentence_position`,
`paragraph_index`, `paragraph_start` and `clause_embedding`, and higher on `sentence_type` (questions are describable).
NLA in between, above the Oracle lens on most rows, which would put a number on Camila and Achim's observation.

**What would surprise us:** the Oracle lens matching the NLA on sentence and paragraph rows. Then the blind spot is
narrower than "text structure" (local state like brackets and positions, not syntax).

## §101 E13. What the readers actually say at structure tokens (free text)

Registered 2026-10-24 04:15 CEST. W1's free-response collection is partial and no blinded reading of it exists, so we
can't yet say whether the Oracle lens ever *mentions* structure.

**Owners:** W-core for (a) code, the integrator runs it; the lens chat for (b). **Cap:** (a) min(1.5F + 360, 2,400) s,
at most 0.8 GPU-h; (b) ≤ $5 API, 0 GPU-h.

**Design.**
- **(a) Complete §84's cut free-target phase** with the same code and items, now under a warmed timing gate and its own
  cap (an operational completion, not a rerun of anything sealed).
- **(b) Blinded mention coding** of the sealed free readouts at W1's 16 structure rows and §84's rows, Oracle lens and
  NLA. For each readout a judge sees only the readout and the row's question (for example "Is the text inside a
  parenthesis?"), never the label or the reader's name, and codes: **mentions the property** (yes/no) and, if yes,
  **which value**. Labels are joined after the codes are sealed.
  - A script also flags literal keywords per row, as a cross-check on the judge.
  - The judge route must satisfy E10's privacy amendment (zero data retention, no training). If none is available, the
    fallback is the script coding plus Guiv or Suraj hand-coding 100 seeded readouts per reader, blind to label and
    reader.

**Dated note, 2026-10-24 05:10 CEST, before any E13 coding:** a second, independent blinded coder is added. The lens
chat builds `blind_sample.jsonl`: 300 seeded readouts (seed 20261024; 150 Oracle lens, 150 NLA, stratified by row) from
the sealed free readouts at structure rows, each with an opaque ID, the row's question and the raw readout only. The key
(reader, item, label) goes to `KEY.DO_NOT_SHARE.jsonl` in cache and is never shown to the coder. A fresh Claude chat
codes the sample with a frozen prompt (mention yes/no; value if mentioned; enacts yes/no). Its codes are sealed before
the key is joined. Reported: Cohen's κ against the API judge on the overlapping readouts, and the same metrics as above
from the Claude coder alone. Guiv separately reads 30 seeded unblinded pairs for qualitative notes, reported as such.

**Metrics.** Mention rate per reader and row (Wilson 95% CIs); among mentions, accuracy against the label; NLA − Oracle
differences with item-paired bootstrap.

**Prediction.** The Oracle lens mentions structure in under 10% of readouts and is near chance when it does; the NLA
mentions it more often and above chance on the rows where its asked score is high (`table_role`, `python_string`).

**What would surprise us:** frequent, correct mentions by the Oracle lens. Then the W1 blind spot is in the asked
scoring, not in what the lens says.

## §102 E1b. The window ceiling: what the AR can see from the text after the activation

Registered 2026-10-24 04:40 CEST, before any E1 analysis is read. **Why:** the AR is trained to map the 12–16 tokens
*after* an activation, read in a fresh context, to that activation. E1's frozen enactment arm
(`prepare.py` on `r/blindspot-mech`) instead feeds the AR the item's own text *ending at* the read position, i.e. the
text before the activation. That arm stays as sealed and is reported as "AR on the prefix", not as enactment. This
section adds the correct arm and a ceiling for what any continuation-reading AR could know.

**Owner:** W-mechanism, on the E12 pod. **Cap:** 0.4 GPU-h. **Inputs:** W1's 2,100 test items (25 rows) and sealed
block-44 probe directions.

**Design.**
- **Continuations:** for each item, the target model's greedy 16-token continuation from the read position (no
  sampling; frozen and hashed before any AR call).
- **(a) Window ceiling (CPU):** can the row's value be predicted from the continuation text alone? Character 1–4-gram
  logistic regression, fit on dev items and scored on test items with W1's template-cluster split; AUROC per row with the
  frozen cluster bootstrap.
- **(b) AR enactment fidelity:** run the AR (block 44) on each continuation and project on the row's unit probe
  direction. Fidelity = (mean projection value A − value B) ÷ (real class-mean gap), as in E1, with CIs.
- **(c) Comparison:** per row, put (a), (b), E1's prefix arm, E1's description arm and the Oracle lens's W1 AUROC side by
  side.

**Prediction.** Rows split in two:
- Rows whose state the next tokens reveal (`prose_paren`, `prose_quote`, `python_string`, `python_indent`,
  `table_role`): high window ceiling, high AR enactment fidelity, Oracle lens still near chance. Here the verbalizer is
  the bottleneck.
- Rows the next tokens don't reveal (`list_index`, `latex_section`, `prose_sentence`, `table_row`): low window ceiling,
  low AR fidelity. Here the window itself is the bottleneck.
- Meaning rows: high on both.

**Dated note, 2026-10-24 04:50 CEST, before E1b is built or run (after reading E1's and E2's results):** E1's gap
ratio was 0.02–0.05 even on semantic rows that the Oracle lens reads near-perfectly, and E2 found every class (semantic
included) at or below the random baseline in the AR's image. So the ratio is not sensitive enough on its own. E1b adds,
as its **primary** AR measure, a scale-free one: per row, the AUROC of the probe projection of AR(continuation) between
value A and value B on test items, with the frozen template-cluster bootstrap. The gap ratio stays as a secondary
measure. The same AUROC is computed for AR(prefix) on E1's sealed outputs, labelled as added after seeing E1.

**What would surprise us:** high AR enactment fidelity on rows with a low window ceiling (the AR knows more than the
text shows), or a low AR fidelity on rows with a high ceiling (the AR fails even when the information is in its input).

## §103 E14. Does a bigger model's Oracle lens state or enact structure? (GLM-5.3 rollouts, CPU only)

Registered 2026-10-24 04:40 CEST, before anyone on this project has read any rollout. Source: Celeste De Schamphelaere's
public dataset `ceselder/glm-5.3-olens-wild-rollouts` (≈156k read positions; GLM-5.3, block 51; fields `left_ctx`,
`token`, `next16`, five RL-lens readouts `rl_greedy, rl_s1..rl_s4` and five SFT-lens readouts `sft_greedy,
sft_s1..sft_s4`). The SFT lens is trained to write the continuation; the RL lens is the RL'd Oracle lens.

**Owner:** coordinator (Claude), code in `projects/g_agreement/understand/e14/`. **Cost:** 0 GPU-h, $0.

**State labels (frozen script, from `left_ctx` + `token`, i.e. text up to and including the read token):**
1. `paren`: inside an unclosed "(" opened within the window (running depth, floored at 0, > 0).
2. `quote`: inside an unclosed double quote on the current line (odd number of `"` on it).
3. `code`: inside a fenced code block (odd number of ``` in the window).
4. `table`: the current line starts with `|` (a markdown table row).
5. `list`: the current line starts with a list marker (`-`, `*`, `+`, or `1.`/`1)`).

**Readout codes (frozen regexes, applied to every readout and to `next16`):**
- **States** (describes the state): paren `parenthes|bracket`; quote `quot|string literal|inside (a|the) string`;
  code `code block|code fence|inside (the )?code`; table `\btable\b|\bcolumn|\bcell\b`; list `\blist\b|bullet`
  (case-insensitive).
- **Enacts** (behaves as the state implies): paren, the first `)` comes before any `(`; quote, contains `"` before any
  newline; code, contains ```` ``` ````; table, contains `|`; list, a line starts with a list marker.

**Metric.** For each state, reader version (RL, SFT, `next16`) and code (states, enacts): the rate on positions where the
state holds minus the rate where it doesn't, with Wilson 95% CIs on each rate and a position-bootstrap CI (2,000, seed
20261024) on the difference. Readout samples within a position are averaged first. Also the raw rate of each code.

**Prediction.**
- `next16` enacts every state far above its off-state rate (the ceiling).
- SFT readouts enact paren, quote, code, table and list states well above off-state, close to `next16`.
- RL readouts enact them much less, and neither SFT nor RL *states* any of them above its off-state rate by more than a
  few points.

**What would surprise us:** the RL lens stating structure well above its off-state rate. That would mean a larger
model's Oracle lens does report structure, and our Qwen blind spot is partly a model-size effect.

**Examples.** Two seeded random positions per state (seed 20261024) with all ten readouts, quoted verbatim for the
write-up, selected before any rate is computed.

**Dated note, 2026-10-24 04:55 CEST, before any data was downloaded:** the paren "states" regex `parenthes` missed
"parenthetical" in the code's unit test; it is changed to `parenthe`. No other rule changes.

**Limits.** No activations, so no probe ceiling: this measures what the lens writes, not what GLM-5.3 represents. Labels
come from a 400-character window, one model, one block. The regexes are crude; a hand check of 50 seeded hits per code
is reported.

---

## Order and budget

1. **First (on existing activations; settles representation vs elicitation):** E5, E1, E3 (~1.3 GPU-h).
2. **Then:** E4 and E7 (~1.4 GPU-h).
3. **Then:** E8 and E6 (~1.5 GPU-h).
4. **Alongside, on CPU and API:** E10, E11, then E9.

Total about 4.2 GPU-h, plus setup. Compute stops Tuesday 27 October at 23:59 Europe/Zurich.

**Dated note, 2026-10-24 04:15 CEST (Guiv):** compute now stops **Wednesday 28 October at 23:59 Europe/Zurich**. The
new runs E12 (§99), W12 (§100) and E13 (§101) add about 2.6 GPU-h. Order: finish the queued E-runs and §87 first; then
E12, W12 and E13(a); E13(b) alongside on API. Nothing launches on Wednesday that cannot finish by 23:59. Thursday is for
analysis, Friday for the write-up.
