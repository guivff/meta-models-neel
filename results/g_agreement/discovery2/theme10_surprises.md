# Theme 10 — Surprises

The first discovery pass was read first, and the other theme reports were checked to avoid relabelling their discoveries. One additional candidate is retained. E75 is a sealed aggregate forecast evaluation, not another native-readout bank. I verified its `COMPLETE_ONCE` result seal and all listed result-file hashes, read only its Qwen pool of E56/E57/E59/E62/E73, and did not run its scorer. No per-item labels, private maps or source prompts are reproduced. `count_theme10.py` emits the aggregate recount and verifies the three public excerpts below.

## S10.1 — Near-agreement on the coarse row map can conceal sizeable differences between readers

**Hypothesis:** A binary “reported or missed” forecast may describe a shared property-level limitation while being too coarse to choose which reader is useful on a particular property or item.

**Count:** E75 contains **35** row/state units evaluated for both readers. Their sealed binary reporting outcomes agree on **34/35**: **18/35** are reported by both, **16/35** missed by both, and **1/35** reported only by Oracle. Marginal reported counts are **19/35 Oracle** and **18/35 NLA**, so the agreement is not merely a shared all-missed base rate. Nevertheless, **5/35** units have an absolute difference of at least **0.20** between the readers' signed statement rates; **4/34** of the agreeing binary outcomes contain such a difference. The largest absolute rate gap is **0.607**. These units are rows or state/rung cells, not independent native items, and related cells share source designs.

The J forecasts agree on **35/35** common units because they use the shared property-level predictor. That agreement is a feature of the design, not independent validation. **7/35** units are forecast errors for both readers; these include **all 7/7 NLA errors**, while Oracle has **8/35** errors on the common set. This follows closely from the outcome agreement and should not be counted as a second independent statistical result. On the full, unequal pools, forecast correctness is **44/55 Oracle** and **28/35 NLA**; the sealed balanced accuracies are **0.792** and **0.802**. E75's registered rule remains **NOT EVALUABLE for both readers** because neither reaches 60 units, and the registered incremental advantage over category has intervals crossing zero. No new predictor was fitted and no sealed classification was changed.

**Banks / both readers:** E75's common comparison covers E56, E57, E59 and E73; the 20 additional E62 units belong only to Oracle and are excluded from the paired comparison. Both readers show the shared coarse map. This does not contradict theme 7's same-item complementarity: a shared row outcome leaves considerable room for different wording, different correct items and different wrong-assertion rates.

**Three verbatim public readout examples:** These illustrate the varied kinds of output compressed into a row-level outcome. They are not per-item truth labels or a released pairing table; the counts above come from the complete aggregate pool, not these examples.

- E56 NLA, `ff1667317f41fed7af43eadc21ddf6c7`: “Q&A format established: a sentence is given as context, followed by a question about the next word's part of speech, expecting a direct answer.”
- E73 Oracle, `01c1227e7e2480ac8c220bab87a753e3`: “- , effectively doing nothing, as this is the base class.”
- E73 NLA, `00ec451cddbb04c0441b696d7da2ec14`: “Wikipedia-style article structure with detailed song history, following a pattern of factual chronological narrative about "Give It Up" by Fergie.”

**Novelty and MATS relevance:** **New relative to the first pass**, which did not include E75. This constrains “what do they find and not find” and “what can NLA find that Oracle cannot”: a strong-looking common row map is insufficient to answer the reader-selection question. The explanatory alternatives include a shared information bottleneck, shared prompt families, shared scoring, and compression by the reporting threshold; this recount does not distinguish them.

**Confirmatory test on new items:** Collect new, independently designed property families with enough forecast units to satisfy the registered size and class-balance gates. Freeze property-level forecasts before seeing reader output, but evaluate continuous signed statement rates and same-item correct/wrong/abstain behavior alongside the binary verdict. Match output budgets and use independently validated human scoring. Hold out whole property families when testing a reader-specific predictor. The hypothesis predicts high binary agreement with residual differences that a shared predictor cannot resolve; disappearance of the gaps under better scoring or equal budgets would instead implicate measurement or presentation.

## Additional scope note, not a scientific hypothesis

E67 wave identifiers must include the wave: **800/800 wave-2 opaque IDs also occur in wave 1**, with different readout records. This is a join hazard rather than a reader phenomenon. The discovery helpers keep `(wave, opaque ID)` separate, and the E67 waves are never pooled. This procedural finding has no confirmatory item experiment, so it is not promoted as another candidate pattern.
