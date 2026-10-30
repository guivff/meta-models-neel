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

**Dated note, 2026-10-24 19:15 CEST (coordinator, operations only):** E3's single CPU analysis was interrupted by a
workspace disconnection before producing any output (empty output folder, no metrics or seal; 40 unsealed partial OOF
caches; inventory `7f188a1d`). No result was seen by anyone. Ruling: run the unchanged registered analysis **once more,
from scratch**, on the sealed capture, into a new output folder, detached from the chat session (e.g. `nohup` or `tmux`)
with progress logged. The partial caches are archived untouched and not reused. The 3 arrays lost in the pull stay
MISSING (258 cells), never imputed. No change to code, probes, folds, rows or metrics.

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

**Dated note, 2026-10-24 18:55 CEST (coordinator, operations only):** E3 completed and sealed, but 6 of 174 pulled files
were lost to an operator tooling fault (3 arrays). E3's analysis runs on the files that verify; the missing arrays are
listed in RESULTS.md and their cells reported as MISSING, never imputed. E4 stopped after 23.7 s on a GPU out-of-memory
error; one E4-only retry is allowed after an operational memory fix (smaller batches, gradient checkpointing or CPU
offload, same items and scope), cap and setup unchanged.

**Dated note, 2026-10-24 22:15 CEST (coordinator, operations only, no E4 result seen):** the E4-only retry (`a0558379`)
fixed memory (~54 GiB, no OOM) and sealed the J-lens, NLA and Oracle-lens calibrations, then stopped before the timing
gate because the target calibration needs a second derivative through the flash-attention kernel, which PyTorch does not
implement. Ruling: one further E4 attempt with a single code change, the attention implementation (eager, or SDPA with the
math backend) for the stage that needs it; nothing else changes (items, rows, metrics, k, seeds). The three sealed
calibrations are kept and not recomputed. Before any science, an equivalence check on 4 test items: the asked log-odds
under the new attention matches flash within 1e-2 (absolute), reported in the receipt. Same cap and setup, same
incremental pulls. If the check or the run fails, E4 closes INCOMPLETE on the sealed stages, with no further retry.

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

- **2026-10-24 07:20 CEST (coordinator, operations only; after seeing the parity numbers, before any E7 science):** the
  tolerance attempt ended NO_FIT before science: 43/52 parity readouts (82.7%) identical over the first 32 tokens
  (rule ≥ 90%), median first divergence at token 77 (rule ≥ 32, passed), 26.9% identical over the full output. The live
  check confirmed **no padding difference**, so the gap is numerical (bf16, not batch-invariant). Ruling: the padding,
  mask and position-id check stays as the bug detector and must pass; the agreement threshold is **removed** and the
  parity rates are reported in RESULTS.md. Production uses batch 32 for every item, so no outputs from different batch
  sizes are mixed. This changes an operational gate after seeing operational (not scientific) data, and is disclosed
  as such. Caps, setup, rows, items, arms and analysis unchanged.

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

**Dated note, 2026-10-24 18:55 CEST (coordinator, operations only, before any NLA E12 analysis):** the NLA-only retry
(booking `2ebafd9d`) ended INCOMPLETE with native 150/150 and context 1,514/1,671 units scored and sealed; the warmed
median (0.33 s/unit) underestimated the bulk rate (~0.73 s/unit). Ruling: one completion attempt scores **only the 157
unscored context units**, with the same code, prompts and order, and the scored units are kept as sealed. The forecast
uses the **observed bulk rate** (max of the measured bulk mean and the slowest warmed unit), cap min(1.5F + 360, 1,200)
s, setup 2,400 s. The NLA analysis runs once on the joined complete grid. No arm, item or contrast changes.

**Dated note, 2026-10-24 22:15 CEST (coordinator, operations only, before any NLA E12 analysis):** the completion's CPU
preflight failed because its first warmed unit took 7.68 s, so max(bulk mean, slowest warmed unit) × 157 came out ~5.5 s
over the 1,200 s cap. The earlier bulk rate was ~0.73 s/unit, so that one unit is warm-up, not throughput. Ruling: the
first warmed unit is excluded from the forecast, which becomes max(bulk mean, slowest of the remaining warmed units).
The 1,200 s cap stays a hard stop. If the run hits it, the units scored so far are sealed, the rest stay unscored, and the
NLA analysis reports E12 as INCOMPLETE with exact counts. No other change.

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

## §105 E15. Scoring the Oracle lens in its own mode: does it enact structure? (closes the format confound)

Registered 2026-10-24 07:20 CEST, before any E15 item or score exists. **Why:** W1 scores readers by choosing between two
*descriptions*, which is the NLA's native mode. E12 showed the Oracle lens judges structure poorly even from plain text,
so part of W1's blind spot could be the answer format. E6 tried continuations, but its greedy proxies were mostly
uninformative (34/42 parenthesis continuations contained no bracket). E15 scores the Oracle lens in its own mode, by
likelihood, so every item counts.

**Owner:** W-core (reuses E6/W1 code). **Cap:** min(1.5F + 360, 1,800) s, setup 1,500 s. **Inputs:** W1's sealed block-44
and block-42 test activations; no new capture except the base-model reference below.

**Rows (8):** `prose_paren`, `prose_quote`, `python_string`, `python_indent`, `python_depth`, `list_depth`,
`table_column`, `table_role`.

**Continuation pairs.** For each row W-core authors **2 frozen pairs** (c_A, c_B): short continuations (1–4 tokens,
equal token counts within a pair) that differ only in the structural consequence of the value (e.g. inside vs outside a
parenthesis: `)` vs `(`; header vs data cell: a header-like vs a data-like next cell). Pairs are committed with their
token counts before any scoring and are the same for every item of the row.

**Scoring.**
- **Oracle lens (native mode):** its native prompt with the injected block-44 activation, then its own bullet prefix
  (`- `), then c_A or c_B. Score = log P(c_A) − log P(c_B), averaged over the 2 pairs.
- **Validity reference (base Qwen on the real text):** the item's own text, then c_A or c_B, with the same score. A pair
  is **valid** only if this reference AUROC is ≥ 0.80 on dev items (the model itself prefers the consequence that
  matches the state). Rows with no valid pair are NOT EVALUABLE.
- **NLA (descriptive, off its native mode):** the same continuation scoring through its prompt at block 42.
- **Controls:** W1's frozen random-donor activations (should give ~0.5).

**Metric.** Test AUROC per row and reader, with W1's 2,000-sample template-cluster bootstrap; Oracle − donor contrast.

**Prediction.** On valid rows, the Oracle lens stays ≤ 0.60 on most rows (it neither describes nor enacts structure).
**What would surprise us:** Oracle ≥ 0.75 on several valid rows. Then the Qwen Oracle lens carries structure by
enactment, as GLM-5.3's does (E14), and W1's blind spot is about description. Either outcome is reported as the answer
to the format confound.

## §106 E16. Honest best wording, and can the base model judge structure from text? (fragile vs blind)

Registered 2026-10-24 07:20 CEST, before any E16 score exists. **Why:** E5 found the Oracle lens's structure scores swing
by up to 0.45 across phrasings, but its best-of-8 was chosen on the test set. E12 found the Oracle lens judges structure
from plain text only at ~0.6. E16 gives the honest best-wording number and asks whether the base model can do what the
lens can't.

**Owner:** W-mechanism (reuses E12's prefix machinery and E5's frozen phrasings). **Cap:** min(1.5F + 360, 2,400) s,
setup 2,400 s. **Inputs:** W1's sealed dev and test activations (blocks 42/44), E5's 8 frozen phrasing pairs.

**Rows:** W1's 16 rule-(i) structure rows and 9 evaluable semantic rows (the 25 rows).

**Arms.**
- **Oracle lens and NLA, asked, all 8 E5 phrasings** at their native sites. **Selection rule (frozen):** per reader and
  row, the phrasing with the highest AUROC on **dev** items; that phrasing is scored once on **test** items.
- **Base Qwen, text only (no adapter, no activation):** the item's text followed by the same question in E5's
  `direct_question` and `statement` phrasings; paired log-odds as in W1. Same dev-select / test-score rule.
- **Free readouts for the reading study (§107):** for the 60 items sampled by §107, 4 native free readouts per reader
  (greedy + 3 samples at temperature 0.7), sealed before any coding.

**Metric.** Dev-selected test AUROC per row, reader and arm, with cluster-bootstrap CIs; per-class medians; base − Oracle
and base − NLA paired differences.

**Prediction.** Dev-selected Oracle structure median ≤ 0.65 (fragile, not readable); base Qwen from text ≥ 0.90 on most
structure rows, so the lens's verbalizer has lost a judgement the base model has. **What would surprise us:** base Qwen
from text also ~0.6. Then structure questions in this format are hard for the model itself, and W1's blind spot is partly
a format effect; the write-up says so.

## §107 Q1. Reading study: what do the two readers actually write, tier by tier?

Registered 2026-10-24 07:20 CEST, before the sample is drawn. Descriptive and qualitative; no pass/fail.

**Owners:** the lens chat draws the sample and keys; coders are Guiv, Suraj and blind Claude sub-agents (coordinator).
**Cost:** 0 GPU-h beyond §106's free readouts; ≤ $2 API if any; about 2 h of human reading.

**Sample (seed 20261024):** 60 W1/§84 test items, 20 per tier, balanced by value: **content** (semantic rows),
**local form** (§84 rows, `table_role`, `python_string`), **earlier state** (`prose_paren`, `python_depth`,
`list_index`, `table_column`). Each item shows the text up to the read token, both readers' 4 free readouts (from §106),
and, only in the unblinded pass, the true value and the probe/asked scores.

**Codebook (frozen; one record per readout):**
1. `about`: the readout's topic in ≤ 8 words.
2. `mode`: continues the text / describes the text / mixed.
3. `mentions`: explicitly states the row's property (yes/no) and `value` (A/B/unclear).
4. `enacts`: behaves as if A or B held without saying it (A/B/none).
5. `hallucination`: states something about the text that is false given the shown text (yes/no, with a quote).
6. `extra`: anything correct about the text that the asked score could not credit (free text, with a quote).
Every non-empty field quotes the readout verbatim.

**Procedure.** Blind pass first (no truth, no reader name, shuffled): Claude sub-agents code all 480 readouts; Guiv and
Suraj each code the same 120-readout seeded subset. Codes are sealed, then joined to keys. Then an unblinded pass:
Guiv and Suraj read 10 items per tier side by side and write short notes.

**Reported.** Per tier and reader: mode, mention and enactment rates with accuracy; κ between coders; and a gallery of
3 verbatim item pairs per tier chosen by a frozen rule (highest |NLA − Oracle| probe-normalised asked difference, plus one
seeded random), with the human notes clearly labelled as qualitative.

**Dated extension, 2026-10-24 07:25 CEST, before any of these readouts is coded (Q2):** the same codebook and blind-first
procedure are applied to four existing sealed readout sets. Each sample is drawn by seed 20261024, blinded to reader
and truth by the lens chat (keys in cache), coded by blind Claude sub-agents, then joined.
- **Q2a, W1 content rows:** 150 seeded readouts per reader from W1's sealed free readouts at `prose_sentiment`,
  `python_effect`, `latex_subject`, balanced by value.
- **Q2b, W6 steered readouts:** 240 seeded Oracle readouts across W6's doses (balanced by dose), plus the dose-0 ones.
  Added field: `structure_named` (names the steered property, yes/no).
- **Q2c, E6 continuations:** all 840 (both readers, 5 rows). Added field: `bracket_or_structure_tokens` (verbatim).
- **Q2d, E14 GLM-5.3:** 200 seeded positions (100 inside a parenthesis, 50 table rows, 50 off-state controls) with
  `left_ctx`, `next16` and all 10 readouts; labels are E14's frozen script labels. Coded unblinded to state by design
  (the state is visible in the context), descriptive only.
All results are descriptive; nothing changes any registered verdict.

**Dated note, 2026-10-24 07:30 CEST, before any Q1/Q2 coding:** the human coding (Guiv and Suraj on 120 readouts, and the
unblinded side-by-side pass) is replaced by an independent reviewer working separately, whose codes, if delivered, are
reported as an additional rater. Our side is unchanged: blind Claude sub-agent coding of every sample plus scripted
analysis, sealed before key joins.

**Dated clarification, 2026-10-24 19:05 CEST, before any gallery item is ranked:** "probe-normalised asked difference"
was undefined; it is replaced by this exact rule. Source: the sealed W1 asked scores (§84's for §84 items), each reader at
its native site, mean paired log-odds over its frozen phrasing pairs. Per item and reader, signed score s = score if the
true value is A, −score if B. Per reader and row, convert s to its percentile among that row's test items (0–1). Item
difference d = pct_NLA − pct_Oracle. Per tier: the 2 items with the largest |d| (ties broken by sha256(seed 20261024 +
item id)) plus 1 item chosen by that hash among the rest. No probe term is used.

**Dated note, 2026-10-24 19:20 CEST, after the rater-1 tables (`35fc17d8`) were seen:** three descriptive follow-ups
are added. They are set after seeing data, labelled as such, and change no verdict. (1) Every tier × reader rate is also
reported with an item-cluster bootstrap 95% CI (2,000 resamples of items, seed 20261024), because the 4 generations per
item are correlated and the per-readout Wilson CIs are too narrow. (2) Mention accuracy is split by mention kind
(`quotes_token` vs `states_property`), so that correctness coming from quoting the local text is separated from
correctness coming from describing the property. (3) Per item, the asked-score percentile is cross-tabulated with
free-text correctness (enact for Oracle, mention for NLA), so that items where asked scoring and the native-mode output
disagree are counted rather than only shown in the gallery. Rater-2 κ is reported when its codes arrive; Q2d is coded only
if it finishes by Sunday 25 October 23:59 CET, otherwise it is reported as not done.

**Dated note, 2026-10-24 22:15 CEST, after FOLLOWUP (`59ef3283`) was seen:** the percentile split in follow-up (3) is
relative within a row and puts about half of every row below 0.5 by construction, so "asked low" does not mean the asked
score was wrong. One more descriptive cross-tab is added: the same free-text majority against the **sign** of the asked
score (s > 0 means the asked score favours the true value), per tier and reader, with discordant ids. The gallery text
stops describing low-percentile items as asked failures unless s ≤ 0. Rater-2's seal omits input hashes; the lens
chat's local binding (sealed input hashes, full id sets, exact evidence per id) is accepted, and κ stands as reported.
---

## §108 Discovery study: what do the raw readouts show, without our story? (EXPLORATORY)

**Registered 2026-10-25 02:50 CET, before any agent looks at the pack.** Owner: a fresh orchestrator chat
(Claude Code or Codex) with subagents. CPU and reading only; no GPU, no outside model APIs.

**Data.** A read-only pack of the sealed Q1/Q2 readouts (1,940 readouts) with truth, both raters' codes and Q1
source texts, plus a public GLM-5.3 rollout sample with the frozen E14 labeler. **Split before anyone looks**:
each item wholly in one half by sha256("discovery-holdout-20261025:" + sample + ":" + item) mod 2 (odd =
holdout; GLM by rollout `tid`). Explore 958 readouts, holdout 982. The holdout is sealed in
`holdout_SEALED.zip`, sha256 `9478f103c48d19c57e23d72d0ba620e37e64b6186af6a856e30f63ead423b88c`; pack
`discovery_data.zip` sha256 `7ded779383efeda9d983ad472049fd216b1273ed91c5fc630670612b7b86e2ba`; prompts
`discovery_prompts.zip` sha256 `929c65c9080e6ab1f21e6463178099a7d71cb444250b4d202ef147dd10eb6e00`.

**Procedure.** Six neutral discovery briefs (output form; truth vs invention; implicit recoverability of the
value; item-level failures; steering and continuations; GLM in the wild) run on explore only, without being told
our hypotheses. The orchestrator then freezes every candidate as a scripted rule with a stated prediction and
records the file's hash. One holdout run tests every frozen rule unchanged (Holm-corrected across all tested
rules); a red team then gets our existing results and tries to explain away each survivor and labels it NEW,
SHARPER or ALREADY KNOWN.

**Decision rule.** Only rules that pass the holdout after Holm and survive the red team may enter the write-up,
labelled exploratory, with the number of rules tested. Nothing here changes a registered verdict. Rates use an
item-cluster bootstrap (2,000, seed 20261025). The steered sample measures target alignment only. Cutoff: Monday
26 October 18:00 CET; anything later is reported as not done.

**Dated note, 2026-10-25 03:50 CET (results received; no rule changed):** two independent runs completed on the
registered pack (hashes verified by both). Run A (Claude Code): 18 frozen rules, 16 pass Holm on holdout, 15 kept
by its red team. Run B (Codex): 28 frozen rules, 17 pass Holm, 9 fail, 2 not evaluable. Neither proposes a new
mechanism; both label most survivors SHARPER or ALREADY KNOWN. Findings found by **both** runs: (1) a fixed
punctuation rule recovers the Python-string label from Oracle-lens q2c continuations on unseen items (AUROC
0.88–0.93; 38/41 correct) with zero explicit mentions; (2) fixed sentiment and mathematics lexicons rank q2a
content labels from Oracle-lens continuations (AUROC 0.88–0.94); (3) Oracle-lens readouts contain Han-script
characters far more often (27–57% vs 0–1%), NEW; (4) at dose 16 every steered readout shows target-compatible
form **and** Han script and a template shift, so the high-dose effect is not separable from off-distribution
drift; (5) the table-column cue fails at holdout; (6) GLM RL stochastic samples repeat exactly far more than SFT
(3.2% vs 0.2% of pairs), NEW as a number. Caveats raised by the red teams and adopted: the NLA's local-form and
tier advantages come mostly from quoting the token (under strict property-statement credit the earlier-state vs
other-tier gap is 14/15 vs 14/16); q2c explicit-mention rates are confounded by short output budgets (q2c NLA
outputs ~160 characters, while its property statements usually start after character 290); q2c labels refer to
the original read position. All of this is exploratory and changes no registered verdict. Reports and audit
bundles: `cache/g_agreement/understand/discovery/`.

---

## §109 E18. Continue-then-ask: is the blind spot a readout-format limit or real suppression?

**Registered 2026-10-25 04:40 CET, before any E18 item is generated or scored. EXPLORATORY, highest priority.**
**Owner:** W-mechanism (reuses the E16 asked-scoring harness and the Oracle lens's native generation). **Inputs:**
W1's sealed block-44 test activations (and dev for wording); no new capture. **Cap:** min(1.5F + 360, 2,400) s,
setup 1,500 s.

**Rows (10):** the 7 valid E15 structure rows (`prose_paren`, `prose_quote`, `python_string`, `python_indent`,
`python_depth`, `list_depth`, `table_role`) plus 3 content rows as positive controls (`prose_sentiment`,
`latex_subject`, `table_status`). All 84 test items per row.

**Arms (same items, same frozen W1 phrasing pairs, same paired log-odds score):**
- **(a) Ask only:** W1's asked scoring, recomputed in this harness (the baseline).
- **(b) Continue-then-ask:** the Oracle lens first generates its native continuation with the activation injected
  (greedy, 16-token cap, its own `- ` prefix); then, in the same context with the activation still injected, the
  asked question follows the continuation.
- **(c) Donor continuation:** as (b), but the continuation is the lens's greedy continuation for a seeded random test
  item of the same row with the **opposite** truth value (seed 20261025). Tests whether the answer follows the text.
- **(d) Text only:** base Qwen, no activation, given only the lens's own continuation from (b) and the same question.
  Tests whether the state is recoverable from the written continuation alone.

**Primary metric.** Per row, test AUROC of each arm; contrast (b) − (a) with W1's 2,000-sample template-cluster
bootstrap. Secondary: in (c), the fraction of items whose answer moves toward the donor's value; (d) AUROC.

**Prediction (decision rule set now).** *Format limit* if (b) − (a) ≥ 0.10 with CI above 0 on ≥ 4 of 7 structure rows
**and** (c) moves answers toward the donor on those rows. *Real suppression* if (b) − (a) < 0.05 on ≥ 5 of 7 structure
rows while (d) ≥ 0.70 on those rows (the state is in the text, the lens still won't say it). Anything else is reported
as mixed. Content rows should sit near ceiling in all of (a), (b), (d).

**Dated clarification, 2026-10-25 05:00 CET, before any E18 generation or score (raised by W-mechanism):** the
donor-movement measure was undefined; it is fixed here. For item i let s_x(i) be the arm-x paired log-odds signed
toward item i's own truth (positive = favours i's true value). **Comparison arm:** (b). **Item moves toward the
donor** iff s_c(i) < s_b(i). **Row-level criterion:** a row "moves toward the donor" iff the fraction of its test
items that move is ≥ 0.60 and its item-cluster bootstrap 95% CI (2,000, seed 20261025) lies above 0.50. The
format-limit rule in the decision rule above uses this criterion; nothing else changes.

## §110 E17. The horizon test: does readability follow the next ~16 tokens or the activation?

**Registered 2026-10-25 04:40 CET, before any E17 item exists. EXPLORATORY.** **Owner:** W-core (reuses W1 capture,
E15 continuation scoring and E1b's reconstructor arm). **Cap:** min(1.5F + 360, 3,600) s, setup 2,400 s.

**Hypothesis.** The Oracle lens expresses a state to the extent that the next ~16 tokens of the real text reveal it,
not to the extent that the activation encodes it.

**Items (new; no reuse of W1's bank).** Generated from W1's templates with fresh lexical fill (seed 20261025),
minimal pairs captured at identical token indices.
- **`prose_paren` and `python_string`, a 2 × 2 per row:** span length (short 20–30 tokens, long 60–80) × capture
  point (early: 5–8 tokens after the opener; late: 3–8 tokens before the closer). State B is the twin text with the
  opener and closer replaced by neutral tokens of the same count (`,` / a bare word). Distance to the close is then
  near in both "late" cells and far (> 40 tokens) only in "early-long", while distance since the opener varies
  independently.
- **`list_depth`, two capture points:** mid-item (≥ 10 prose tokens before the line end) vs the last token of the
  previous item (the next line opens with the marker at the target depth). Shallow vs deep at the same position kind.
- **n:** 96 pairs per cell (dev 32, test 64), template families split between dev and test.

**Channels (same items):** (1) **source probe:** logistic probe on the target's block-44 activation, trained on dev
only; (2) **window:** E1b's reconstructor run on the real next 16 tokens, probe trained on dev; (3) **Oracle lens
continuation:** E15's frozen pairs for the row, with W1-style random-donor and opposite-state-swap controls;
(4) **Oracle lens asked:** W1's frozen phrasings.

**Primary contrasts (sign pattern pre-registered, Holm across the 3 rows).**
- Paren and string: lens-continuation AUROC in the two "late" cells minus the "early-long" cell ≥ 0.10, while the
  source-probe difference is ≤ 0.05 in absolute value (manipulation check: encoding is flat).
- List depth: lens-continuation AUROC at the line end minus mid-item ≥ 0.10, source-probe difference ≤ 0.05.
- In every cell the window channel should move with the lens channel and the asked channel should stay ≤ 0.60.
Item-cluster bootstrap CIs (2,000, seed 20261025). The across-cell correlation figure is descriptive only.

**Outcomes.** Both directions hold: the horizon account is supported. One direction: partial, reported as such.
Neither: the suppression is not explained by the reconstructor window.

**Dated note, 2026-10-25 05:40 CET (coordinator, after E17's result `3b48f0da` was seen; changes no verdict):** E17 is
reported as registered: NOT SUPPORTED, with the source-flatness check failed in every row. The coordinator adds one
interpretive caveat, owned as a design error in this section: E17 reused E15's continuation pairs, which score the
**immediate next token** (`)` vs `(`; closing quote; next bullet indent). At E17's capture points the closer is 3-8
(late) or more than 15 (early) tokens away, so neither state predicts an immediate `)`, and no per-cell validity gate
(base Qwen on the real text, as E15 had) was registered. The Oracle-lens continuation channel (0.47-0.55 in every cell,
random and opposite donors likewise ~0.5) therefore does not measure what the horizon hypothesis is about, and E17 is
read as **uninformative about the horizon account**, not as evidence against it. What E17 does establish: the window
manipulation worked (next-16 AR probe 0.50 in early-long/mid-item cells vs 0.94-1.00 in late/line-end cells) and the
asked channel stays <= 0.57 in every cell, with the source probe at 0.72-0.98.

## §111 E19. Does the reader's internal state reach its answer? Steering along the probe direction

**Registered 2026-10-25 04:40 CET, before any E19 steer is applied. EXPLORATORY.** **Owner:** W-internals (reuses E3's
probes on the Oracle lens's layers and the W7/S2 steering code). **Cap:** min(1.5F + 360, 2,400) s, setup 1,500 s.

**Rows (5):** 4 state rows where E3's lens probes are strong (`prose_paren`, `python_string`, `table_role`,
`python_depth`) plus `prose_sentiment` as a content control.

**Direction.** Per row, refit E3's logistic probe on **dev items only** at the Oracle lens's pre-answer position, at
the layer with the highest dev AUROC within the middle third of its layers (chosen on dev, frozen before test). u = the
unit weight vector; σ = std of dev projections onto u.

**Intervention.** At the pre-answer position and the answer tokens, add α·σ·u with α ∈ {0, ±1, ±2, ±4}, on the 84
test items. **Controls:** a random unit direction of equal norm (3 seeds); the content row's direction applied to the
structure rows; each row's own direction applied with the activation injection replaced by a random donor.

**Measures:** paired change in asked log-odds per item (W1 phrasings); change in E15 continuation score; and the probe's
own projection one layer later (did the steer land).

**Prediction.** *Pathway exists but is under-weighted:* asked log-odds moves monotonically with α in the probe's
direction, with slope above the 95th percentile of the random-direction slopes, on ≥ 3 of 4 state rows. *Disconnected:*
asked flat (within the random band) while the continuation score moves. The content row is the positive control: its
own direction should move its asked answer.

**Dated note, 2026-10-25 05:15 CET (coordinator, operations only, no E19 score exists):** the first launch stopped at
its timing gate (NO_GO): forecast F = 4,885.8 s for 1,218 units against a 2,400 s cap; no production unit ran and the
sealed `scores.jsonl` is empty. The 2,400 s cap was a coordinator estimate, not a scientific choice, and no result has
been seen. Ruling: one relaunch with the design unchanged (rows, items, alpha grid, controls, frozen dev-only directions
`36bd59a9`), on the kernel environment `/weights/venv-kernels`, with cap min(1.5F + 360, 9,000) s and setup 1,500 s.
If the warmed forecast still exceeds the cap, E19 stops and closes INCOMPLETE; no scope reduction without a new note.

---

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

## §113 E21. The reward audit: does the reconstructor pay for describing structure?

**Registered 2026-10-25 06:15 CET, before any E21 score exists. EXPLORATORY.** **Owner:** W-mechanism (reuses E1b's
reconstructor path, with the whitener handled as in E1b). **Inputs:** W1's sealed block-44 test activations and labels,
W1's frozen phrasing pairs, E15's frozen continuation pairs. No new capture, no lens generation. **Cap:**
min(1.5F + 360, 2,400) s, setup 1,500 s. Prior: Suraj's S14 reports that the reconstructor responds differently to
literal descriptions and to text exhibiting a property; E21 is the registered, all-row version tied to W1's outcome.

**Hypothesis.** The Oracle lens describes what its reconstructor rewards describing. For content, a description of the
true value moves the reconstruction toward that value; for structure, only text that exhibits the state does.

**Texts per test item (all 25 W1 rows):** (1) the frozen W1 description of the true value; (2) the same for the
opposite value; (3) an exhibiting text: E15's frozen continuation for the true value where the row has one, otherwise
the real next 16 tokens. Each is run through the reconstructor alone.

**Measure.** For each row, a logistic probe trained on **dev** reconstructions of the real next 16 tokens (E1b's
setup), applied to the test reconstructions of texts (1)–(3). **Describe reward** = probe AUROC of (1) vs (2) over test
items (does saying the right value move the reconstruction toward it?). **Exhibit reward** = probe AUROC of text (3)
across the item's true state. Item-cluster bootstrap CIs (2,000, seed 20261025).

**Primary prediction (one test).** Across the 25 rows, describe reward predicts the Oracle lens's W1 asked AUROC:
Spearman rho >= 0.50 with its bootstrap 95% CI above 0 (rows resampled). Secondary: describe reward is lower on
structure than on content rows (median difference >= 0.15); exhibit reward on structure rows exceeds describe reward
(median difference >= 0.15). **Falsified** if rho <= 0.20, or if structure rows' describe reward is >= 0.80 while the
lens's asked AUROC stays <= 0.60 on them.

**Dated clarification, 2026-10-25 06:25 CET, before any E21 score (answers W-mechanism's two questions):** the W1
descriptions are the same text for every item of a row, so a probe on their reconstructions gives at most two points
per row. The primary measure is therefore replaced by the quantity the Oracle lens was trained on: **reconstruction
fidelity to the item's own activation.** For test item i with block-44 activation h_i and a text t, let
r(t, i) = cosine(AR(t), h_i), in the space E1b's AR returns (raw block 44; the whitened version is reported as a
secondary if E1b's verified whitener applies cleanly).
- **Describe reward**, per item: d_i = r(true description, i) − r(opposite description, i), each averaged over **both**
  frozen W1 phrasing pairs. Per row: the fraction of test items with d_i > 0 (ties count 0.5), a 0–1 statistic
  comparable to an AUROC, with an item-cluster bootstrap CI.
- **Exhibit reward**, per item: e_i = r(true-value exhibit, i) − r(opposite-value exhibit, i), averaged over **both**
  E15 continuation variants; rows without an E15 pair use the item's real next 16 tokens vs those of a seeded
  (20261025) opposite-value test item of the same row. Per row: the fraction with e_i > 0.
- The dev-trained probe measure is kept as a secondary, with scores signed toward each item's own truth.
The primary prediction, secondaries and falsifiers in §113 are unchanged and now refer to these row statistics.

## §114 E22. Where does structure reach each output? Layer-wise activation patching inside the Oracle lens

**Registered 2026-10-25 06:15 CET, before any E22 score exists. EXPLORATORY; supersedes E19 as the causal test.**
**Owner:** W-internals (reuses E19's hooks and harness, on `/weights/venv-kernels`). **Inputs:** W1's sealed block-44
test activations. **Cap:** min(1.5F + 360, 7,200) s, setup 1,500 s.

**Why the design is clean.** The Oracle lens's prompt is identical across items; only the injected activation differs.
Patching a residual from a donor run into a recipient run therefore swaps state and nothing else.

**Rows (5, as E19):** `prose_paren`, `python_string`, `table_role`, `python_depth`, and `prose_sentiment` as the
content positive control. 84 test items each; each recipient's donor is a seeded (20261025) test item of the same row
with the opposite value.

**Interventions.** Run the recipient and donor through the lens's two native prompts: (A) the asked prompt with W1's
frozen phrasings and (C) the continuation prompt with E15's frozen pairs (sentiment: asked only, as E19). For every 4th
layer (0, 4, 8, …, and the last) and two positions, (i) the injection position and (ii) the last prompt position before
the output (pre-answer for A, after the `- ` prefix for C), replace the recipient's residual at that (layer, position)
with the donor's. Controls: patching from a **same-value** donor (should change nothing) and patching the injected
activation itself (layer 0, injection position, which reproduces W1 / E15 swaps).

**Measure.** Per (row, prompt, layer, position), the fraction of the full-swap effect recovered:
(score_patched − score_recipient) / (score_donor − score_recipient), averaged over items (signed toward the donor's
value), with item-cluster bootstrap CIs. For the asked prompt, where the full swap has little effect on structure rows,
also report the raw paired change in log-odds.

**Predictions.** (1) **Content control:** patching at the injection position in early layers, and at the pre-answer
position in later layers, recovers most of the asked effect (>= 0.50) — the test can see an answer pathway when one
exists. (2) **Structure, continuation prompt:** the effect passes from the injection position to the pre-output position
in mid layers (>= 0.50 recovered at the pre-output position at some layer). (3) **Structure, asked prompt:** no
(layer, position) moves the asked log-odds by more than the same-value control's 95th percentile, even at layers where
E3's probes read the state at the pre-answer position — i.e. the state reaches the answer position but the answer does
not read it. **Alternative:** if some (layer, position) does move structure answers, the answer pathway exists and is
localised there.

---


**Dated note, 2026-10-25 07:40 CET (coordinator), E22 relaunch ruling, operations only, before any production
record exists (0 of 51,408 scored; the calibration seal `0416d88a…` covers parity and timing only).** E22 stopped at
NO_GO_WARMED_FORECAST: calibration used 2,339.8 s of science, F = 6,183.2 s, total 8,523 s, against the 7,200 s ceiling.
The fault was the fixed ceiling, not the formula (1.5F + 360 = 9,635 s). One fresh attempt is authorised with the cap
**min(1.5F + 360, 10,800) s**. Admission is unchanged: calibration science used + F ≤ cap. F is remeasured on warmed
units. The only allowed code change is the 7,200 constant; W-internals' reviewer confirms the diff. Rows, donors,
layers, positions, controls and measures are unchanged. The first attempt's 0.83 GPU-h stay booked and do not count
against this admission. If this attempt also refuses, E22 closes as INCOMPLETE for compute. No scope cut is authorised
without a new registration.

## §115 S15 reanalysis (CPU, on Suraj's sealed outputs): what did input steering do to the asked answer?

**Dated note, 2026-10-25 07:20 CET (coordinator; descriptive; no new compute).** Suraj's S15 (layer 42, `tb_paren` and
`tb_tablecol`, 200 items, 8 directions, 20 isotropic + 20 non-null-subspace random directions, doses r11 and q90)
reports a directional "mean shift" = log-odds(+1 push) − log-odds(−1 push), far outside its random-direction bands.
Reanalysed from `score15_*.pt` and `spec15_*.pt` with per-class shifts and AUROC under steering:
- **Dose in natural units.** The q90 dose along the class-mean direction is 0.89 (paren) and 0.74 (column) of the
  natural class gap along that direction (gap 14.4 and 21.8 in activation units; natural AUROC on the direction 0.96
  and 1.00).
- **Discrimination collapses under the state-direction push, for both readers and both signs.** Oracle lens asked
  AUROC: paren 0.70 → 0.49/0.49 (+1/−1), column 0.72 → 0.50/0.49. NLA: paren 0.96 → 0.57/0.47, column 1.00 →
  0.52/0.60. Random directions of the same norm change nothing (AUROC within ±0.02, shifts ≈ 0).
- **The reported shift is an asymmetry between two destructive pushes, not a reading of state.** Paren, Oracle lens:
  +1 (toward inside) lowers inside items' "inside" log-odds by 1.1 and leaves outside items at +0.3; −1 lowers both
  (−3.0, −1.5). Even moving an outside item to the inside mean does not make either reader say "inside" (NLA outside
  shift −0.2 under +1). Table column shows a partial directional bias in the Oracle lens (+1 raises outside items by
  +1.2; −1 lowers inside items by −0.5) with discrimination still collapsing.
- **Gentler directions behave differently.** Directions with the top nuisance components removed (`*_jrem4`) and the
  span-reconstruction direction leave the NLA's discrimination largely intact (0.81–0.94); the literal-statement
  direction (`arstmt`) is near-orthogonal to paren state (cosine −0.04, natural AUROC 0.39) and moves nothing.
- **Discrepancy to reconcile:** at layer 42 with bullet-formatted candidates (`- inside parentheses`), the Oracle lens's
  unsteered asked AUROC is 0.70 (paren) and 0.72 (column), against ~0.5 in W1/E18 at layer 44 with W1 phrasings. Bank,
  layer and candidate format all differ; not resolved here.
**Reading.** S15 does not show an answer pathway in the Oracle lens; it shows that a ~1-gap push along the raw
class-mean direction takes both readers off their working range on this property. The earlier doc wording ("a big push
moves the answer") is withdrawn. No further steering experiment is registered; E22 (patching) remains the causal test.

## §116 Suraj's experiments S00–S14 folded into the story (descriptive; no new compute)

**Dated note, 2026-10-25 07:45 CET (coordinator).** Suraj's numbered experiments are cited as S00–S14 (his exp
directories `00_*`–`14_*`). Read against our story; figures quoted from his RESULTS.md files.
- **Cited as evidence:**
  - S14 (reconstructor blind spot): statements move the Oracle-lens reconstructor 0.03–0.10 of the class gap (language
    statement 0.10 vs a French bullet 1.39; "column one/five" 0.03). The NLA reconstructor responds to the language
    statement (0.72) but not to structure (0.07 / −0.05).
  - S12/S13 (concept table, 22 rows): the Oracle lens states a property in 6 of 13,420 readouts (0 of 4,480 at layer 42).
    The NLA states completion-relevant structure (table column 41%, paren 30%) and ordinals (bullet index 25%), and never
    counts. Prompted at layer 42, NLA / OL: table column 1.00 / 0.74, paren 0.96 / 0.73, with a length control.
  - S08/S09: the OL newline continuation tracks col steering (0.67–0.76) only with the adapter on (0.40–0.44 off). The
    gain ratio to the model is 0.99–1.06. OL follows tense 4r* while the model's next token does not move.
  - S07: continuation templates beat fixed labels.
  - S05/S10/S11: the NLA rewrites the planted clue 12 of 12 times and misquotes 588 of 600 arithmetic prompts; OL at layers
    40/42/44 gives the same results within 0.05.
  - S01/S06: the WorkspaceBench lead is a best-of-11-layers artefact, and the benchmark is text-explicable.
- **Not cited:** S00 and S02–S04 (setup and J-space), except S03's lesson that additive steering creates an OL
  artefact. Also not cited: the S10 power sub-study.
- **Not comparable as run:** S14 vs E1b. S14 fed the preceding 32 tokens and scored with a probe trained on
  reconstructor outputs (whitening moments gated). E1b fed the next 16 tokens and used a frozen probe on true
  activations. Positions: S14 table column 1.00 vs E1b 0.54–0.62. Proposed check, not yet registered: both inputs on
  both item sets, under one split and one probe, after confirming the reconstructor's training span from its config.
- **Open discrepancies:**
  - Table column: ours 0.57 vs Suraj's 1.00 on six shared rows (his D37).
  - "Prompted" (teacher-forced bullet log-odds) vs our "asked" (frozen candidates): a likely contributor to the layer-42
    OL 0.70–0.74 vs W1 ~0.5. S11 rules out layer.
  - S16's "Oracle part" uses the NLA reconstructor on OL text.
  - S15 used centred construction (confirmed 07:55 from `spec15.py`).
- **Story edits:**
  - "Positions never stated" now applies to the Oracle lens and to counts only.
  - "NLA describes" becomes "describes the text it reconstructs".
  - S14 is the central evidence for the reward account.


## §117 E23. Which span does the Oracle lens's reconstructor read, and does it carry positions? (S14 vs E1b)

**Registered 2026-10-25 07:45 CET, before any E23 output exists. EXPLORATORY.** **Owner:** W-mechanism, after its
registered E21 analysis (it reuses E1b's and E21's reconstructor path, with the whitener handled as in E1b). **Cap:**
min(1.5F + 360, 5,400) s, setup 1,500 s, warmed units. **Seed:** 20261025.

**Why.**
- **The S14–E1b conflict.** On positions, S14 found the OL reconstructor separates table column at 1.00. E1b found
  0.54–0.62 (table_column 0.60, list_index 0.58). S14 fed the preceding 32 tokens and used a probe trained on
  reconstructor outputs (grouped 5-fold). E1b fed the following 16 tokens (greedy) and projected onto the frozen
  block-44 probe direction.
- **Measure is a live candidate.** E1's sealed prefix arm already scored table_column at 0.54 on our items under the
  frozen-probe measure. Several of its rows sit far *below* 0.5: latex_section 0.003, list_depth 0.10. So the state
  is present in the reconstructor's output, but not along the true activation's direction.
- **Our own docs disagree on the training span.** BRIEF_BLINDSPOT says "average preceding activation"; §102 says
  "12–16 tokens after"; S14 says "last 32 tokens, the AR's training crop". The window explanation depends on which is
  right.

**Step 0 (CPU gate, before any GPU).** Read the reconstructor's training configuration and data-prep code
(`agu18dec/olens_and_ar`, pinned single files only, never a clone). Record in `e23/SPAN.json`, each with the
file:line it came from:
- whether the input span precedes or follows the target position;
- its length in tokens;
- whether the target is one activation or an average, and over which positions.

The arm that matches is labelled **in-contract**. This is settled before any score exists. If the code doesn't
settle it, E23 runs anyway with both labelled "contract unknown", and Camila or Agam is asked.

**Items (two sets).**
- (O) Ours: W1's sealed test items for `table_column`, `list_index` and `prose_paren`, with `python_string` (state,
  positive) and `prose_sentiment` (content). 84 test items per row; dev items train probes.
- (S) Suraj's: exp-13 `tb_tablecol` and `tb_paren`, and exp-07 bullet index; 200 items each, with his item clusters.
- Suraj's items have no continuation, so the following-span arm on both sets uses the target model's greedy
  continuation, as E1b did. Before any AR call, these continuations are frozen and hashed, along with Suraj's item
  files (supplied by Guiv, hash recorded).

**Reconstructor inputs (four arms, every item).**
- **F16:** greedy next 16 tokens (E1b).
- **P32:** preceding 32 tokens ending at the read token (S14).
- **Pfull:** the item's whole prefix (E1's arm).
- **Mis:** the F16 span of a seeded random item of the same row with the opposite value. This is the
  mismatched-span control.

Tag 44 is primary and tag 40 secondary, as S14.

**Measures (on every row × set × arm).**
- **M1 (primary, alignment):** AUROC of the AR output's projection onto the frozen block-44 probe direction trained
  on *true* dev activations, in the same whitened space as E1b. No sign is flipped on test; the dev sign is used.
  This is what the reconstruction reward cares about.
- **M2 (decodability):** AUROC of a logistic probe trained on AR outputs, grouped 5-fold by item cluster (S14's
  measure).
- **T (text control):** character 1–4-gram logistic regression on the same input span, with the same folds (E1b's
  window model). It shows whether the span text alone already gives the answer.

For our items, item-cluster bootstrap CIs use W1's clusters; for Suraj's, his clusters.

**E23b (table-column discrepancy, our 0.57 vs Suraj's 1.00).** Oracle-lens asked AUROC on table column, 2 × 2 × 2:
- item set (O / S);
- phrasing (W1's frozen phrasings / Suraj's bullet candidates `- column one` …, as exp 13);
- layer (42 / 44).

Activations are captured fresh for whichever set × layer is not already sealed. Each set is scored with its own
labels; nothing is tuned.

**Decision rules (frozen now; positions are table_column, list/bullet index).**
1. **Measure explains the S14–E1b gap** if M2 − M1 ≥ 0.15 with CI excluding 0 on table column in both sets, on the
   in-contract arm.
2. **Input explains it** if P32 − F16 ≥ 0.15 (CI excluding 0) under M1 on table column in both sets.
3. **Items explain it** if S − O ≥ 0.15 (CI excluding 0) under the same arm and measure.
   More than one of 1–3 can hold; all are reported.
4. **AR adds nothing beyond its text** for a cell if M2 ≤ T + 0.05.
5. **Validity gates:** Mis must sit within 0.5 ± 0.10 under M1 and M2 on every row, and `python_string` and
   `prose_sentiment` must reach M1 ≥ 0.80 on the in-contract arm. If either gate fails, the affected rows are reported
   as uninterpretable.
6. **E23b:** the factor with the largest main effect (≥ 0.10, item-bootstrap CI excluding 0) is named as the cause.
   If no factor qualifies, the discrepancy stays unresolved.

**What each outcome does to the story (pre-stated).**
- **(a)** Positions low under M1 on the in-contract arm in both sets, with M2 high: the reconstructor's output holds
  the position, but not where the real activation holds it, so the reward can't pay for it. This **strengthens**
  "positions aren't rewarded" and reframes S14's 1.00 as decodability, not alignment.
- **(b)** M1 high on table column on the in-contract arm: the reconstructor *does* align positions. The claim "the
  window can't see positions" is withdrawn for that row.
- **(c)** Step 0 shows the training span precedes the position: E1b's following-span arm becomes off-contract, the
  window account is rewritten around the preceding span, and §102's framing is corrected in the docs.

**Dated clarification, 2026-10-25 07:55 CET, before any E23 output (source of Suraj's items).** The items come
from Suraj's public repo `Jarus77/mats-nla-workspace` at commit `a8e41f4a31d654ccc29e2d9105abb2aac38ad5eb`. Read-only;
fetch these pinned files only:
- `experiments/13_new_rows/results/gen_ol_tb_tablecol.json` (sha256 `2e8738d0…79b9d`) and `…/gen_ol_tb_paren.json`
  (`10bf31c7…a6b51`);
- `experiments/handoff_inputs/07_template_mining/gen_ol_bk_listidx.json` (`ef289fa3…be50ba`);
- the candidate phrasings in `experiments/13_new_rows/feature_spec.py` (`b0dd043f…7effe43`) and both
  `templates_frozen.json` files (exp 13 `d9046206…837d16`, exp 07 `09156722…d923b`).

Each item carries id, value, cluster, split, text and token ids. The row definitions:
- `tb_tablecol`: first cell vs 4th–6th cell;
- `tb_paren`: inside vs outside;
- `bk_listidx`: bullet item 2–3 vs 8–12, with no length control.

Splits and clusters:
- Suraj's split is kept: the 40 `mine` items (20 per value) are E23's dev/probe-training items, and the 160 `select`
  items are its test items.
- Every Suraj item is its own cluster, so for set S, "grouped by cluster" means item-level folds and item bootstrap.
- M2 on set S uses 5-fold CV over all 200 items (as S14). M1 and T train on `mine` and test on `select`.

Activations and other details:
- Activations are recaptured with E23's own hooks.
- Suraj's stored layer-40/42/44 activations (`handoff_inputs/13_new_rows/acts_*.pt`) are used only as a parity
  check: cosine ≥ 0.999 on all items. A failure is reported, and the hook definition is fixed before any score.
- S14's 32-token arm is `span_crop(ids, 32)`, i.e. the last 32 tokens ending at the read token (`ar_lib.py`).
- Its comment "AR training crops are 1..32 tokens" cites no source, so Step 0 still decides the span.
- S15 used centred steering (`spec15.py`: h' = h − (v·h)v + s·dose·v), so §116's S15 query is closed.

**Dated clarification 2, 2026-10-25 08:00 CET, before any E23 score (answers W-mechanism's two questions after
Step 0, `SPAN.json` a76c1cad, which found: the span follows the target, 1–32 tokens; the target is the single residual
just before the span; F16 is in-contract, and P32 and Pfull are off-contract).**
1. **M1's space.** "Same whitened space as E1b" was wrong. E1b's sealed implementation projects raw AR outputs on
   raw-space probe directions, and M1 matches that exactly, so E23 and E1b/E1 numbers are directly comparable. No
   whitened variant is added.
2. **Probes for Suraj's items.** As in clarification 1, M1's direction for set S is trained on Suraj's 40 `mine` items'
   true block-44 activations, with W1's probe recipe and no tuning. This is needed because his contrasts differ from
   W1's (first cell vs 4th–6th; bullet 2–3 vs 8–12). The corresponding W1 dev probe applied to set S is reported as
   a **secondary** transfer measure, and the decision rules use the set-S-trained probe.
3. **Mis control, corrected (coordinator design error).** An opposite-value donor span is not a null. Under a fixed
   probe it should *reverse* the AUROC (≈ 1 − matched), and a refitted M2 probe simply learns the reversal. So:
   - **Mis** becomes the F16 span of a seeded (20261025) random item of the same row and set, drawn independently of
     value. Gate: AUROC within 0.5 ± 0.10 under M1, and under M2 *applied with the probe fit on F16 outputs* (no refit).
   - The opposite-value donor is kept as **Swap**, a secondary check. Prediction: under the same fixed probes,
     AUROC ≤ 0.5 wherever the F16 arm is ≥ 0.70.
4. **Labels.** Because of Step 0, P32 and Pfull are reported as off-contract in every table. Rule 2 ("input explains")
   still applies, but an off-contract arm with a high score cannot be read as the reward paying for that property.
   Outcome (c) does not apply, since the span follows the target as §102 assumed. BRIEF_BLINDSPOT's "average preceding
   activation" wording is corrected in the docs.

**Dated correction, 2026-10-25 09:10 CET (coordinator transcription error, before any E23 score).** In
clarification 1, the abbreviated sha256 of exp 07's `templates_frozen.json` was written `09156722…d923b`. The correct
full hash is `09156722b059edb99d01e919c29b2ff660e37cba3152f2d3ce67f3272d3e923b` (suffix `e923b`, Git blob
`fe84815ad09e14b8d926eaf319258ff55e5b3c67`, 278,756 bytes), as W-mechanism's source gate found. The file is the pinned
one; only the registered abbreviation was wrong. The other five abbreviations were rechecked against full hashes and
are correct. The source gate uses this full hash.

**Cost estimate.** About 1 GPU-h (H100/H200): forward passes for ~600 of Suraj's items at layers 42/44, greedy
continuations, ~12k reconstructions (E21 did 16k in 884 s), and E23b scoring.


## §118 E24. Every core Oracle-lens claim, across its trained layers (Neel's "what layer X finds that layer Y doesn't")

**Registered 2026-10-25 08:55 CET, before any E24 item, activation or score exists. EXPLORATORY.**

**Why.** Every Oracle-lens result so far is at block 44. Suraj's widest sweep (40/42/44) is within 2 layers. Neel asked
for far-apart layers. The lens was trained on layers 20–60 in steps of 4 (11 layers of the model's 64), so every grid
layer is in-contract. The objective account predicts that the blind spot is a property of the lens's *reward*, not of
the layer: structure is carried but never stated at every layer where a probe finds it. One hint against this:
WorkspaceBench's best single Oracle-lens layer was mostly 56 (S01).

**Owner:** W-core (owns W1 and E15 scoring); a new chat "W-layers" if W-core is busy with E20 or W12. **Seed:** 20261025.

**Layers and order.** All 11 grid layers, run in this priority order so that far-apart coverage comes first if compute
runs short: **44 (anchor), 20, 60, 32, 52, 28, 36, 40, 48, 56, 24.** Split across up to 4 pods by layer, with the anchor
on every pod.

**Activations.** One forward pass of the target model on W1's 2,100 test items, plus its dev items, captures the residual
at every grid layer at W1's read position, using W1's frozen hook and sealed per layer before any scoring. Parity gate:
the recaptured block-44 activations match W1's sealed ones (cos ≥ 0.999 on every item).

**Claims and channels (C1–C7), per layer.**
- **C1, asked (W1):** the Oracle lens's asked AUROC on all 25 rows, with W1's frozen phrasings, candidates and scoring.
  *Claim:* near chance on structure, near ceiling on content.
- **C2, continuation (E15):** continuation-likelihood AUROC on E15's valid rows, with E15's frozen pairs. **Swap
  control:** the same scoring with E15's opposite-state donor activation taken from the same layer. *Claim:* carries
  the state, and the swap reverses it.
- **C3, presence (probe):** a logistic probe per row trained on dev activations at that layer with W1's recipe, scored
  on test. *Claim:* the state is present. Its role is gating (see rules).
- **C4, free text (E13/Q1):** one greedy free readout per test item with the lens's native prompt and W1's generation
  settings, scored by a frozen regex of structure statements per row, written and committed before generation.
  20 readouts per layer are blind-checked by a judge, with the layer label hidden. *Claim:* never states structure.
- **C5, window (E1b):** the reconstructor (tag = that layer) on E1b's frozen greedy next-16 continuations, projection
  AUROC on the C3 direction (raw space, as E1b). *Claim:* states visible in the next tokens survive; positions do not.
- **C6, statements (S14):** the reconstructor shift per class gap for E23's fixed statement pairs on `table_column`,
  `prose_paren` and a language control, at 4 layers (20, 36, 44, 60). *Claim:* statements barely move it at any layer.
- **C7, best wording (E16), tier 2:** E16's 8 phrasings, best chosen on dev, at 3 layers (20, 44, 60). This runs only if
  the tier-1 forecast leaves room.

Tier 1 is C1–C5 at every layer that fits; tier 2 is C6–C7.

**Decision rules (frozen; structure rows = W1's 19; Holm over the 19 × 10 non-anchor cells for R2).**
- **R0 (anchor validity):** at layer 44, C1 and C2 reproduce W1 and E15 within ±0.03 AUROC on every row. If a row
  fails, that row's results are uninterpretable at every layer.
- **R1 (blind spot, per layer):** W1's frozen near-chance rule applied unchanged to each layer's C1, among rows where
  C3 ≥ 0.80 at that layer. *"Holds across layers"* if it passes at ≥ 9 of the 11 layers run.
- **R2 (a layer finds what 44 doesn't):** a structure row × layer cell with C1 ≥ 0.70, Holm-adjusted bootstrap p < 0.05
  against 0.5, while layer 44 is ≤ 0.60 on that row. Every such cell is reported by name. Any cell that passes is the
  headline "layer X says what layer 44 can't".
- **R3 (carried, per layer):** C2 ≥ 0.70 on a majority of valid rows, *and* the swap control is ≤ 0.50 on those rows.
- **R4 (never stated, per layer):** pooled over structure rows, the Wilson 95% upper bound on the correct-statement
  rate is < 5%.
- **R5 (dissociation):** C2 − C1 > 0 with CI excluding 0 on a majority of valid rows, at every layer where R3 holds.
- **R6 (window):** C5 on count/position rows ≤ 0.65 at every layer.

**Predictions.** R1, R3, R4, R5 and R6 hold at all or almost all layers. No R2 cells pass. Probes (C3) are high at mid
and late layers and may be lower at layer 20. **Alternatives worth naming:** early layers state syntax (R2 cells at
20–28), or late layers lose the carried state (R3 fails at 56–60).

**Budget.**
- Warmed forecast per pod; cap min(1.5F + 360, 10,800) s per pod, setup 2,400 s.
- Total at most 12 GPU-h. If the tier-1 forecast for all 11 layers exceeds this, drop layers from the end of the
  priority list. Never drop a claim within a layer that runs.
- Results go to `results/g_agreement/understand/e24/`.

**NLA (not swept).** The NLA exists only at block 42. An off-layer NLA read is out of contract, and Suraj flagged his
off-layer NLA reads (16/28/36/56) as a problem. So E24 does not sweep the NLA. If another NLA checkpoint exists (to ask
Agam or Camila), a later registration can add it. The probe (C3) gives the across-layer ceiling the NLA would be
compared against.

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
