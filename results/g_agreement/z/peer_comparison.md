# Peer comparison: ten MATS exploration mini-projects (reviewer view, 2026-10-09)

Figures 14–17 (Gemma 3 vs 4 emotion probes and frustration) don't match Story 8, which is about Qwen cheating. They are probably Tim Farrelly's work and are **not scored**. Figure 18 is Story 8's and 19 is Story 9's. Claims that can't be checked from the inputs are taken at face value and flagged.

Q question, R rigor, S result strength, C clarity, E efficiency, N next-step value. The overall score is a judgement, not an average.

| # | Project | Q | R | S | C | E | N | Overall | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | S6 Task preferences bend Gemma's arithmetic | 8 | 8 | 8 | 9 | 8 | 8 | **8.2** | Clear effect, ablated, then localised with baselines |
| 2 | S8 Does watching reduce cheating? | 8 | 8 | 8 | 9 | 9 | 7 | **8.0** | 2–3 days, design fixed in advance, sharp monitorability finding |
| 3 | S5 Logit-matching steering vector | 7 | 7 | 8 | 8 | 8 | 8 | **7.8** | A method result with real baselines and a mechanistic temperature sweep |
| 4 | S2 Agent notes + quantization vs interp | 6 | 8 | 7 | 8 | 7 | 6 | **7.0** | Two clean small studies; the noise ceiling sits next to the effect |
| 5 | **Ours: cross-referencing activation readers** | 9 | 8 | 5 | 4 | 5 | 7 | **6.6** | The best question and controls of the ten; the headline is diffuse and the summary is stale |
| 6 | S3 Multi-agent message board | 7 | 5 | 7 | 7 | 6 | 6 | **6.3** | "Asked once ≠ live board" matters for eval design; wide CIs, many threads |
| 7 | S4 EM and pretraining data | 8 | 5 | 5 | 6 | 6 | 6 | **6.0** | Important question with an honest negative; weak statistics and one uninterpretable result |
| 8 | S7 Slop-vestigations | 6 | 4 | 6 | 6 | 6 | 5 | **5.6** | Useful critique of auditing benchmarks; n = 3 runs on a metric they themselves call crude |
| 9 | S9 Planted compaction instruction | 6 | 7 | 3 | 8 | 6 | 6 | **5.4** | Pre-registered and honest, but a null without a positive control |
| 10 | S1 Unverbalized eval awareness | 8 | 3 | 3 | 4 | 4 | 5 | **4.3** | Right question; no label and no result yet |

**Overall scores, briefly.** S6 has the full package: a surprising behaviour (62% vs 32%), controls that isolate its cause, and one mechanistic claim with baselines (DAS 91% vs ~1%). S8 has the most insight per hour, and its finding (disguised cheats are described accurately only 8% of the time) bears directly on safety. S5 is solid tooling in toy settings. S2 is rigorous but has lower stakes. S3, S4 and S7 have good questions but soft evidence. S9 and S1 have no result yet that could change anyone's mind.

## Per-project notes

**S6 Task preferences (8.2)**
- Strongest: the prompt-ablation ladder (fig 9) isolates consequence as the driver; DAS is reported as a share of the swap, next to baseline directions.
- Weakness: the effect is large only when one task is harmful, so it may be refusal avoidance. 1-D DAS can produce an interpretability illusion. The swap moves only 58% of the bias. The model is 4-bit (S2: NF4 shifts steering by up to 0.14).
- Improve: a benign-vs-benign task pair, plus a DAS null on random labels.

**S8 Watched cheating (8.0)**
- Strongest: cheating is verified by running the code; 2,640 samples; the "who checks" null is reported as a finding.
- Weakness: the inputs don't say how "disguised" or "accurate" were labelled; tasks are single-turn only.
- Improve: validate the labels on a hand-labelled subset; test whether a CoT monitor catches the disguised cheats.

**S5 Logit-matching SV (7.8)**
- Strongest: 99% vs 27% transfer (logit- vs text-matching); the T sweep explains why (low-probability tokens carry the trait); several real baselines.
- Weakness: one seed; mostly subliminal-learning toys; no gain on EM; recipes not budget-matched.
- Improve: a budget-matched comparison on one non-toy trait.

**S2 Two projects (7.0)**
- Strongest: fig 3 puts the precision effect (≤ 0.14) against refit noise (0.16–0.19), which is ceiling-first thinking; the notes study has good controls (contractor, git author, commit lookup).
- Weakness: two unrelated stories; 4–8 runs per cell; unexplained day-to-day drift.
- Improve: lead with one study; randomise fixtures across days.

**S3 Message board (6.3)**
- Strongest: the asked-once vs live-board reversals warn against trusting single-turn evals.
- Weakness: wide CIs (12% bar ≈ [2, 47]); n unclear; many half-explored threads.
- Improve: freeze board state to separate peer content from turn count.

**S4 EM and pretraining (6.0)**
- Strongest: EM appears on the base checkpoint; clean negative: CPT shifts baseline misalignment but not susceptibility to EM.
- Weakness: 8 questions with no CIs; the document scores may track genre rather than misalignment; the variance result is uninterpreted.
- Improve: a genre-matched random-document CPT arm; CIs on every rate.

**S7 Slop-vestigations (5.6)**
- Strongest: shows human reports aren't a gold standard; measures skepticism directly (fig 13).
- Weakness: 0.58 vs 0.515 is 3 runs on the metric they call crude; time budgets and toolkit effects are mixed; mostly unverifiable from the inputs.
- Improve: ablate tools vs pairing at matched time.

**S9 Compaction planting (5.4)**
- Strongest: a pre-registered bar, Wilson CIs, and an informative "mentioned but rejected" split.
- Weakness: cheating is 0 in every arm and there is no positive control, so the null is uninformative.
- Improve: first find a dose that cheats, then plant.

**S1 Eval awareness (4.3)**
- Strongest: honest framing; a within-dataset probe for verbalized eval awareness.
- Weakness: no label; anecdotal J-lens tokens; steering is confounded with refusal.
- Improve: fix one behavioural key and measure everything against it.

## Our project

**Rank 5 of 10 (6.6).** Question and rigor are top-tier; result strength, clarity and efficiency pull us down.

What we do better than every peer:
- **Causal-key framing.** We grade readers against keys set without them (a constructed answer, a planted fact confirmed by a behavioural flip, the model's own answer). This is the right answer to Neel's "rate by majority" idea, and no peer validates its instruments this way.
- **Corrections culture.** We published our own errors: the X2 scale artefact, the text-derivable ERROR set (267/297), X6 ρ −0.8 → −0.20 (Z2), the per-family split of Y2, and TOST bounds for "inert".
- **Nulls and ceilings** throughout: other-pair and random-subspace nulls, two-half ceilings, paired sign tests.

Where we are clearly weaker:
- **No crisp headline.** About 20 sub-experiments in 3 days and a write-up over 5,000 words with superseded text still inline. A reader can't get the claim in 30 seconds.
- **Mostly negative or methodological results.** "One instrument" and "free text was the bottleneck" are useful but unsurprising. The surprising result (readers follow a component the model ignores) is buried in Phase Y.
- **The Friday summary is stale.** It still leads with Spearman −0.8, which Z2 downgraded. It says SAEs and Skip Lens are untested, but Y3 tested both. It leaves out Y1, our only case where some readers find what others miss.
- **Compute and focus.** About 16 pod-hours and ~$60, of which ~7 hours went to a sweep we abandoned.
- **Open validity holes.** The NLA gate is still pending. In Y1, readers ran off their training layer, so "readers miss it" may reflect that. The J-space claim has no TOST yet.

**What to borrow:** S6's figure style (a title that states the claim, effect as a share of the full swap, baselines as bars beside it); S5's per-figure template (takeaway, details, limitations); S2's noise-ceiling panel next to the effect; S8's three-number TL;DR.

**The single most important change:** rewrite the Friday summary around one up-to-date claim and one figure. Suggested claim: *"Activation readers report what is in the vector, not what the model uses. At the layer-38 causal site they follow the J-space component the model ignores (78–92% follow, 0–8% flips) as readily as the remainder that flips it; at layer 48 a probe reads the model's upcoming wrong answer (79%) that no reader reports (41–57%, off their training layer)."* Figure: S6-style bars of model flip rate vs each reader's follow rate across the Y2 arms (full, name-only, non-name, J-only, J-remainder, other-pair), per family. Everything else goes to an appendix.

## Overlaps and synergies

- **S1:** their J-lens top-k readout is the free-text mode that failed for us in G1–G2; scoring against a contrast would help them.
- **S6:** their DAS/position localisation mirrors our Z4 (mapping sits on two symbol tokens, ownership on the post-statement span). Worth fitting a 1-D DAS direction at L38 and checking whether readers follow it.
- **S2:** probes and SAEs are stable under NF4 but steering is not. This parallels our bf16 determinism check (32/32) and our failed SAE transfer.
- **S5:** a logit-matched vector would be a cleaner planted edit than our interpolation; their β dial is our α ladder.
- **S8 (same model):** disguised hardcoding is an off-text fact with a behavioural key, the empty cell in our blindness map. Do our readers report it?
- **S4:** their variance-along-direction vs random is the same statistic as our J-space energy share (44% vs 27%).
