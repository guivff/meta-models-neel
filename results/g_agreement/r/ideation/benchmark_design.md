# Benchmark design / meta-science lens — ideation 2026-10-18

## What this lens sees that the current design (BRIEF_R/IDEAS_R/PLAN_R) does not   (≤ 15 lines)
1. BRIEF_R §0 says the spine is "three sources per fact" (TEXT / STATE / MODEL) but no table or figure ever puts the
   three on one axis per fact: R2 compares the reader with prompt-only (TEXT vs MODEL ceiling), R3 with the model's
   greedy pick (TEXT vs MODEL), and the probe is only a reference, never a *label*. The probe's own held-out
   prediction is a third label, and the three labels disagree on 10–40% of items, which is exactly where a reader's
   source can be read off. That is the headline figure nobody has drawn (BD-1).
2. The trust rule (§6 `trust_rule.md`) is written as prose after the data. A rule that is not tested on facts it was
   not fitted on is a description, not a deliverable. Pre-registered split, held-out precision/recall (BD-2).
3. Nothing measures whether the sprint *changes beliefs*: a forecast registry before the freeze (team + Neel + a
   literature-only forecaster) makes the surprise value of each of H1–H7 a number (BD-3).
4. Seven decision rules give binary verdicts; a null and an underpowered result are both "not supported". The SAE
   paper's negative was "no evidence of gain"; ours should be "gain < 0.01, equivalence shown" (BD-9).
5. Kantamneni et al. changed practice because the release (113 datasets, activations, baselines, leak-free selection)
   let others re-run it. We have no release spec, no leaderboard protocol, no one-command re-run (BD-4), no test
   of whether the benchmark can be passed without reading the state (BD-7), no test–retest of the map (BD-10).
6. The reviewer objections are listed in §9 as "threat → control" but two of them (Oracle at 42, candidate order,
   label noise) have no number attached; each gets a pre-stated experiment (BD-5, BD-6) and the one-model objection
   gets a power-sized replication, not a vague "week 2" (BD-8).

## Designs

### BD-1 - The three-source triangle per fact (headline candidate)   [cost: 0 pod-min, 1 CPU-h | slots into: WS3 / R3 / new figure F0]
1. Claim: at blocks 42–44 every lens reader sits at the TEXT corner (f_T ≥ 0.75) on ≥ 70% of facts with defined cells,
   by block 56 the J-lens and Oracle move to the MODEL corner on ≥ 50% of COMPUTED ∪ FORM facts, and no reader ever
   occupies the STATE corner (f_S ≤ 0.4 everywhere): readers never share the probe's errors.
2. Items/bank: R-A 113 test splits (200 items), R-D legacy rows where probe and prompt-only exist; later WS12 families.
3. Ground truths — TEXT: dataset label | STATE: sign of probe(512)'s decision function on the held-out test item
   (trained on pool, chat render, same layer) | MODEL: prompt-only greedy pick. Each test item is then one of four
   patterns: all-agree, T-odd (text alone differs), S-odd, M-odd. Per (fact, reader, layer): f_X = P(reader sides with
   the odd label | X-odd) with Wilson CI; a cell is defined when the X-odd set has ≥ 20 items. Triangle coordinates
   (f_T, f_S, f_M) / Σ; the figure is one point per (fact, reader) at 42/44 and at 56, coloured by tag.
4. Controls: shuffled-state rows (`|shuf`, must give f_X ≈ 0.5 in every corner), state-free prior (the candidate prior
   gives a fixed corner independent of the item: must be removed before f_X is read), random-rotation J-lens (E13) as
   the null reader, logit lens as the zero-cost reader, the probe itself (f_S = 1 by construction, a sanity row).
5. Decision rule: SOURCE-X(r, f, L) iff f_X ≥ 0.75 with CI lower bound > 0.5 and both other f ≤ 0.4; MIXED otherwise.
   Claim supported iff the three fractions above hold with fact-level bootstrap CIs excluding the thresholds.
6. Cost: CPU only on `reader_lo.jsonl`, `prompt_only.jsonl` and the probe(512) fits WS3 already makes
   (`analyze.r1_run`, `r3_conflict` extended with a third label column; `wilson`, `bootstrap_ci`).
7. Outcomes: if TEXT→MODEL with layer → the "lag, not blindness" law drawn per fact; if f_S high anywhere → readers and
   probes share errors, so "readers read along class-mean directions, not the probe direction" (Phase W) is wrong at
   that site; null (MIXED everywhere, cells rarely defined) → the three labels agree too often on R-A and the
   triangle needs the WS10/WS12 conflict-rich families; report the count of defined cells per tag.
8. Novelty: R3 (BRIEF_R §4.3) and E2 are two-way (text vs model, model vs hidden belief); using the probe's held-out
   prediction as a third label on the same items, and the probe's *errors* as the signature of state-reading, is new
   (closest: Kantamneni's diagnosis of spurious latents, which never scored a reader against the probe's mistakes).

### BD-2 - The trust rule as a held-out predictor   [cost: 0 pod-min, 2 CPU-h | slots into: WS8 / new]
1. Claim: a depth-3 decision tree over label-free features, fitted on half the facts, predicts "reader AUROC ≥ 0.9 ×
   probe(512) and ≥ 0.75" on the other half with precision ≥ 0.8 and recall ≥ 0.5, beating the tag-only rule by ≥ 0.10
   precision.
2. Items/bank: R-A 113 facts split by parity of a SHA-1 of the dataset id (pre-registered, 56/57); R-D and WS12
   families as a second, shifted test set.
3. Ground truths — TEXT: the target variable uses the dataset label's AUROC | STATE: probe(512) AUROC defines the
   denominator (reader is "right" relative to what is present) | MODEL: prompt-only enters as the label-free
   feature mean |LO| and as a secondary target "reader AUROC ≥ 0.9 × prompt-only AUROC".
   Features, all computable without labels on a new fact: tag, layer, render, mean |s_diff| of the reader, the
   two-cluster silhouette of s_diff (bimodality), |s_diff| on the dataset-mean state (prior strength), κ with the
   logit lens, κ with the other readers, mean |prompt-only LO|, J-lens single-token coverage.
4. Controls: tag-only rule; "always trust" (precision = base rate); a rule fitted on shuffled targets (must be at base
   rate); the same rule applied to the random-rotation J-lens (must predict "do not trust" ≥ 90%).
5. Decision rule: thresholds in 1 with Wilson CIs on the held-out half; precision gain over tag-only with a fact-level
   bootstrap CI > 0; on the shifted set the precision drop must be ≤ 0.10, else the rule is "R-A only".
6. Cost: CPU on `cells.csv` + `state_free.jsonl` + `reader_lo.jsonl` (`analyze.cells_table`, `r7_agreement` for κ,
   sklearn `DecisionTreeClassifier(max_depth=3)`; fits are trivial).
7. Outcomes: if supported → `trust_rule.md` is the tree, with its held-out numbers, and the paper's practitioner claim
   is testable by anyone with a new fact; if precision < 0.8 but recall high → the rule finds trustworthy readers but
   also admits bad ones: report the false-positive tags; null (no better than tag-only) → trust is a property of the
   fact type alone and the one-line rule "trust on SURFACE/TOPIC, never on COMPUTED/INTERNAL" is the deliverable.
8. Novelty: no reader paper states a trust rule, and no benchmark paper tests its practitioner guidance on held-out
   tasks; Kantamneni's "quiver" selects arrows per task with labels, this rule needs none (overlaps WS8 only as
   its output format).

### BD-3 - Forecast registry: the surprise value of H1–H7   [cost: 0 pod-min, 1 CPU-h | slots into: BRIEF_R §1 (pre-freeze) / new]
1. Claim: at least 2 of H1–H7 resolve on the side the team's median forecast gave ≤ 0.5, and the literature-only
   forecaster does no better than the team (Brier difference ≤ 0.02).
2. Items/bank: 7 binary questions ("H_k supported by its §4 rule?") + 8 numeric quantities with 80% intervals: median
   n* (SURFACE ∪ TOPIC ∪ FORM), ΔAUC(16), fraction of KNOWLEDGE facts with reader ≥ 0.8 × probe, P(model) for the
   Oracle at 56, median lag on COMPUTED, median cos(d_reader, d_probe), k = 8 accuracy of the best reader, consensus
   gain in points. Forecasters: Guiv, Suraj, Neel (Monday, before the freeze), Agam if available.
3. Ground truths — TEXT / STATE / MODEL: every quantity is a statistic of the three ground truths already defined in
   BRIEF_R §4; the registry adds nothing to the measurement, it records beliefs about it.
4. Controls: a uniform forecaster (0.5 everywhere, Brier 0.25); a literature-only forecaster (a Claude subagent given
   BRIEF_R, IDEAS_R and the four lit reports and nothing from `results/`), run and committed before Monday's compute.
5. Decision rule: surprise(H_k) = −log2 p_team(realised outcome); the sprint has surprise value iff ≥ 2 hypotheses
   have surprise ≥ 1 bit; a result is "already in the literature" iff the lit-only forecaster's Brier on it is < 0.1
   while the team's is > 0.25. Numeric: interval coverage (expected 80%) and |error| in units of the bootstrap CI.
6. Cost: `results/g_agreement/r/forecasts.jsonl` with git hash and timestamp, committed before `collect --freeze-r`;
   scoring is a 50-line script run once after R1–R7 land. 0 pod-min.
7. Outcomes: if ≥ 2 surprises → the writeup leads with them and the forecasts are the evidence that they are not
   hindsight; if 0–1 surprises and the team was well calibrated → the sprint's contribution is the calibration and the
   protocol, say so first; null (team and literature forecasters tie at Brier > 0.25) → the hypotheses were
   under-specified and the follow-up brief must sharpen them before any new compute.
8. Novelty: no interpretability paper reports pre-registered team forecasts; Sharkey et al. 2025 call for
   pre-registration without a scoring rule. Overlaps nothing in E1–E15; it is the measurement of what they teach.

### BD-4 - Release format, leaderboard protocol and the one-command re-run   [cost: 0 pod-min, 3 CPU-h | slots into: WS8 / WS3 / new]
1. Claim: a clean clone on a second machine, given only the released cache, reproduces every headline number of
   `summary.md` within 0.005 AUROC and every H1–H7 verdict identically, in one command.
2. Items/bank: the release = `items_r.json` (+ `items_rk/rb/re/rc2.json`), per-item columns `label`, `probe_pred`
   (BD-1's STATE label), `model_pick`, `model_lo`, `logit_lens_L*`; states for the 200-item test splits and 512 pools at
   the five read layers, chat render, fp16 (113 × 712 × 5 × 5120 × 2 B ≈ 4.1 GB) and raw at 42 (0.8 GB), the rest on
   request; `reader_lo.jsonl`, `state_free.jsonl`, the `|shuf` rows; `manifest/frozen_config_r.json` with code SHAs.
3. Ground truths — TEXT, STATE, MODEL: all three shipped as columns per item so a submitter scores against all three
   without a GPU; the R5 edit rows (`r5/steer.jsonl`, `readback/`) ship as the MODEL-by-edit tier.
4. Controls: mandatory arms for a ranked submission: shuffled-state (AUROC in [0.45, 0.55] on ≥ 95% of cells, else
   "pipeline error"), state-free, random-rotation, and a no-activation arm (the reader given the text, no insertion);
   a submission missing any arm is listed as unranked. Held-out generator split (BD-7) required for WS12 families.
5. Decision rule: reproduction passes iff max |Δ AUROC| ≤ 0.005 over all cells and the verdict vector is identical;
   seeds fixed (`SEEDS`, `SHUFFLE_SEED`, `RANDOM_SEED`); a failing cell is a bug ticket, not a result.
6. Cost: `analyze --root <release_dir>` already resolves cache/dataset/results under one root (`Paths`); add
   `--release` to copy the subset and write `RELEASE.md` with the schema; upload to HF; re-run on Suraj's Mac
   (≈ 1 h for probes at layer 42 with `--n-jobs 8`). 0 pod-min.
7. Outcomes: pass → the paper's reproducibility statement is a number; fail on probes → seed/BLAS nondeterminism,
   report tolerance; fail on verdicts → a rule sits on a threshold, which BD-9 flags as UNDERPOWERED.
8. Novelty: no reader (AO, NLA, Oracle Lens, skip lens, J-lens) has a public benchmark with cached states, three
   labels and mandatory controls; lit report 1 lists this as gap 5 and 7. Overlaps WS8 only.

### BD-5 - Pre-empting two reviewer objections with numbers: Oracle off-grid and candidate order   [cost: 25 pod-min, 0.5 CPU-h | slots into: WS2 / R2–R3]
1. Claim: moving the Oracle from 42 to 44 and swapping the candidate order in the prompt-only template each change
   ≤ 10% of (fact, reader) verdicts in R2/R3.
2. Items/bank: R-A 113 test splits (Oracle rows at 42 and 44 are both in Monday's collection).
3. Ground truths — TEXT: label | STATE: probe(512) at 42 and 44 (the probe's own 42-vs-44 shift is the yardstick) |
   MODEL: prompt-only greedy under both candidate orders; the MODEL label becomes "stable pick" (same under both
   orders), items that flip with order are tagged order-unstable and reported as a rate per dataset.
4. Controls: shuffled-state at both layers; the J-lens at 42 vs 44 (on-grid everywhere) as the reference for how much
   any reader moves between adjacent captured layers; the state-free prior under both orders.
5. Decision rule: Oracle: paired AUROC(44) − AUROC(42) per fact with item bootstrap; "grid-robust" iff |Δ| ≤ 0.05 on
   ≥ 80% of facts, else 42 is dropped from every table. Order: order-unstable rate ≤ 15% per dataset median; R3
   verdicts recomputed on stable items only must agree with the all-items verdicts on ≥ 90% of cells.
6. Cost: Oracle comparison CPU-only on existing rows; swapped-order prompt-only = one extra pass of
   `collect_prompt_only` with `candidates` reversed (≈ 25 pod-min; add a `--swap-candidates` flag).
7. Outcomes: both robust → one line in the paper and the objection is closed; Oracle not robust → every Oracle claim
   is "at 44", and the earlier phases' 42 numbers get an explicit caveat; order-unstable > 15% on a tag → the MODEL
   label is unreliable there and R3 is reported on stable items only.
8. Novelty: BRIEF_R §9 lists both threats with a control but no threshold; IDEAS_R asks for question paraphrases
   (Fouilhé) but not for candidate-order swaps; AO papers note the "10/12" prior bias without quantifying it.

### BD-6 - The label-noise regime: where zero-shot readers should win   [cost: 0 pod-min, 15 CPU-h | slots into: R1 / new regime R1b]
1. Claim: with 25% of pool labels flipped, the quiver with readers beats the probes-only quiver by ΔAUC(n) ≥ +0.02 at
   every n ≤ 32 (CI > 0) on facts where the reader's clean AUROC ≥ 0.8, and by < +0.01 at n = 512.
2. Items/bank: R-A 113 facts; noise applied to the pool labels only (test labels clean), rates 10 / 25 / 40%, seeded.
3. Ground truths — TEXT: clean test labels | STATE: probe(512) fitted on clean labels (the ceiling the noisy probe
   loses) | MODEL: prompt-only, unaffected by noise (readers and the model are zero-shot, so the regime isolates what
   labels buy).
4. Controls: the noisy-label probe at each n (the baseline that degrades); the reader + probe stack fitted on noisy
   labels (its selection uses noisy validation, as a practitioner would); random-rotation J-lens in the quiver (must
   not be selected more often than chance); the clean-label quiver (R1) as the no-noise reference.
5. Decision rule: thresholds in 1, fact-level bootstrap (1,000); the crossover n_x(noise) where the noisy probe
   overtakes the reader, reported per tag; H1's "≤ +0.01 at n ≥ 16" is re-tested at each noise rate.
6. Cost: 113 × 9 n × 5 seeds × 3 rates ≈ 15k logistic fits ≈ 15 core-h, 2 h on 8 cores (`analyze.r1_run` with a
   `--label-noise` flag that flips pool labels before `balanced_draw`); no new rows.
7. Outcomes: supported → the practitioner rule gains a clause ("with noisy labels, readers are worth ≈ n_x clean
   labels"), the first regime where a zero-shot reader adds value; not supported → readers add nothing even when the
   probe is handicapped, the strongest form of the SAE-paper negative; null at 10% but positive at 40% → report n_x as
   a function of noise.
8. Novelty: Kantamneni's label-noise regime compared SAE probes with probes; nobody has run a zero-shot reader in it,
   and it is the regime where the reader's independence from labels is a structural advantage. Not in E1–E15.

### BD-7 - Benchmark gaming: passing ReaderBench without reading the state   [cost: 10 pod-min, 2 CPU-h | slots into: WS12 / WS3 / new]
1. Claim: a text-only TF-IDF logistic reader reaches ≥ 0.9 × the best lens reader's AUROC on SURFACE ∪ TOPIC ∪ FORM
   and ≤ 0.6 AUROC on CONTEXT ∪ KHOP ∪ INTERNAL, and the no-activation Oracle arm reaches ≥ 0.9 × its with-activation
   AUROC on ≥ half of R-A.
2. Items/bank: R-A test splits; WS12 families with a held-out generator split (templates and entities disjoint from
   the pool: request a `--holdout-generators` flag in `readerbench/build.py`); R-C2 pairs (identical visible text,
   different system turn) as the identical-tokens / different-state items.
3. Ground truths — TEXT: label | STATE: probe(512) | MODEL: prompt-only greedy; the gaming question is whether a
   scorer can match the TEXT ground truth with no state at all.
4. Controls (these are the design): (a) TF-IDF + LR on the text, n = 512 pool, per fact; (b) the Oracle with the text
   in the user turn and no insertion; (c) the random-rotation J-lens (E13); (d) the probe-stacked reader fitted on
   in-distribution pool, tested on held-out generators; (e) shuffled-state. Detector rule for a submission: flagged
   iff shuffled AUROC > 0.55, or held-out-generator drop > 0.10, or AUROC on R-C2 pairs < 0.6.
5. Decision rule: thresholds in 1 with fact-level bootstrap CIs; the leaderboard's headline metric is restricted to
   facts where (a) and (b) are both < 0.7 ("text-unsolvable subset"), fixed before the first external submission.
6. Cost: (a), (c), (d) CPU; (b) Oracle on 113 × 200 × 2 candidates ≈ 45k scores ≈ 9 pod-min (`collect_reader_lo`
   with the text rendered into the reader prompt and the insertion hook disabled; add `--no-activation`).
7. Outcomes: supported → ReaderBench is text-solvable on three tags and the paper says so with the subset; the
   no-activation Oracle ≥ 0.9 everywhere → the Li result holds for the Oracle Lens on 113 facts, and only the
   text-unsolvable subset counts; null (text reader ≤ 0.6 everywhere) → the bank is harder than the SAE datasets
   suggest and the subset restriction is unnecessary.
8. Novelty: Li et al. and Jakkli et al. ran a no-activation arm on 2–4 tasks; E10 is the inversion baseline, E13 the
   random rotation; the held-out-generator split, the TF-IDF floor and the detector rule as a leaderboard gate are new.

### BD-8 - Second-model mini-replication sized by power   [cost: 60 pod-min, 3 CPU-h | slots into: WS9(a) / BRIEF_R §7.1a]
1. Claim: the per-fact ratio AUROC_reader / AUROC_probe correlates across Qwen3.6-27B (Oracle at 44) and Gemma-2-9B
   (Activation Oracle at layer 20) with Spearman ≥ 0.5 (CI > 0) on the smallest fact subset that preserves the
   Qwen headline.
2. Items/bank: the k R-A facts chosen by the power step: on Qwen, resample fact subsets of size k ∈ {20, 30, 40, 60}
   stratified by tag (1,000 draws); k* = the smallest k at which ≥ 80% of draws reproduce the tag ordering of the
   median ratio (SURFACE ≈ TOPIC > KNOWLEDGE > COMPUTED, or whatever Qwen shows) and the H1 verdict. Chosen before
   any Gemma compute.
3. Ground truths — TEXT: label | STATE: LR and mass-mean probes on Gemma layer-20 states (the paper's own activations
   where available, else recaptured) | MODEL: Gemma prompt-only greedy with the same template.
4. Controls: shuffled, mean-state, random-rotation (J-lens is Qwen-only; a random linear readout through Gemma's
   unembedding stands in), no-activation AO arm; the Gemma Scope SAE probe (k = 16, 128) as the SAE column.
5. Decision rule: Spearman with fact bootstrap; tag ordering identical; ΔAUC(n) of the Gemma quiver within ±0.02 of
   Qwen's at n ∈ {8, 32}. REPLICATES iff all three; PARTIAL iff Spearman holds and one other fails.
6. Cost: k* ≈ 40 facts × 712 items at one layer on a 9B model ≈ 5 pod-min capture, AO LO ≈ 15, prompt-only ≈ 5, SAE
   encoding ≈ 5, setup 20 → 50–60 pod-min; probes CPU (`r1_run` on a `projects/r_gemma/` root; `Paths(root)`).
7. Outcomes: REPLICATES → "one model" is answered and the SAE column enters the quiver; PARTIAL → report which tag
   broke; null → the blind-spot map is model-specific and the paper's claims are scoped to Qwen3.6-27B, stated first.
8. Novelty: BRIEF_R §7.1a names the route but not the size; sizing a replication by resampling the first model's
   facts is standard in psychology (Simonsohn's small telescopes) and absent from interpretability benchmarks.

### BD-9 - Four-way verdicts with pre-registered equivalence margins; negatives first-class   [cost: 0 pod-min, 0.5 CPU-h | slots into: WS3 `write_summary` / BRIEF_R §4]
1. Claim: with 113 facts, at most 2 of H1–H7 end UNDERPOWERED; H1's quiver clause ends EQUIVALENT-NULL (|ΔAUC(n)| <
   0.01 for n ≥ 16 with the 90% CI inside the margin).
2. Items/bank: the seven hypotheses as computed by R1–R7 on R-A (+ R-B for H6, R5 facts for H5).
3. Ground truths — TEXT / STATE / MODEL: unchanged; the design changes how each effect is reported, not measured.
4. Controls: every effect stays a difference from its control arm; a 10-permutation null per rule gives the
   "no-effect" distribution the margin is compared with.
5. Decision rule (per hypothesis, margins fixed now): H1 ±0.01 AUC; H2 exceedance 0.05; H3 ±0.10 around 0.75/0.60;
   H4 ±1 block; H5 ±0.10 cos and ±0.10 on the flip/follow fractions; H6 ±5 points; H7 ±2 points. Verdict:
   SUPPORTED (95% CI entirely past the threshold on the predicted side), REFUTED (entirely past it on the other
   side), EQUIVALENT-NULL (90% CI inside the margin: two one-sided tests), UNDERPOWERED (otherwise). Figure F0: a
   forest plot of the seven effects with margins and thresholds drawn, the paper's first figure.
6. Cost: CPU; `analyze.write_summary` gains a `verdict4` column; margins written into BRIEF_R §4 before the freeze.
7. Outcomes: a REFUTED or EQUIVALENT-NULL verdict is reported with the same prominence as SUPPORTED (the figure
   makes that automatic); ≥ 3 UNDERPOWERED → the fact count, not the readers, is the finding, and week 2 adds facts
   before anything else.
8. Novelty: Kantamneni reported nulls as absence of gain; equivalence testing with pre-stated margins has not been
   used for any interpretability readout; it turns "readers add nothing" into a bounded positive claim.

### BD-10 - Test–retest of the blind-spot map: surprising cells on fresh items   [cost: 15 pod-min, 0.5 CPU-h | slots into: WS3 / F3 / week-2 robustness]
1. Claim: ≥ 80% of surprising (fact, reader) cells in F3 keep their verdict on 200 fresh pool items the reader has
   never scored.
2. Items/bank: a cell is surprising iff its verdict (reader ≥ 0.9 × probe, or ≤ 0.6) differs from the majority verdict
   of its tag × reader; fresh items = pool items outside the 64 `POOL_EVAL` items, 200 per cell, balanced.
3. Ground truths — TEXT: label | STATE: probe(512) refitted with the fresh items excluded from the pool | MODEL:
   prompt-only (already collected on pool items).
4. Controls: shuffled-state on the fresh items; a matched set of unsurprising cells (same tags, same readers) re-scored
   the same way, whose replication rate is the yardstick (expected ≥ 90%).
5. Decision rule: replication rate with Wilson CI; the map is "cell-reliable" iff the rate ≥ 0.8 and within 0.1 of
   the unsurprising cells' rate; else F3 is published at tag level with cell values greyed.
6. Cost: ≤ 40 surprising + 40 matched cells × 200 items × 2 scores ≈ 32k Oracle scores ≈ 7 pod-min, J-lens free, NLA
   ≈ 5 min load + 3 min (`collect_reader_lo` with `--items` restricted to the cell's fresh ids; `cells_table`).
7. Outcomes: reliable → the per-cell map is the deliverable and each surprising cell is a case study; unreliable →
   the headline is tag-level only and the paper says the cell level is noise at 200 items; null (surprising cells
   replicate but unsurprising ones do not) → a pipeline fault in the pool scoring.
8. Novelty: BRIEF_R's week-2 line "replication of any surprising cell on fresh items" has no selection rule, size or
   threshold; a pre-stated surprise criterion with a matched control is new to reader evaluation.

## Ranking within this lens (information gained ÷ pod-minutes), one line each
1. BD-1 triangle: 0 pod-min, draws the paper's spine per fact and tests "readers never share the probe's errors".
2. BD-9 four-way verdicts: 0 pod-min, decides how every other result is stated; must be in BRIEF_R before the freeze.
3. BD-2 trust rule: 0 pod-min, turns the deliverable into a falsifiable predictor with held-out numbers.
4. BD-3 forecast registry: 0 pod-min, ten minutes of each person's time on Monday, the only measure of surprise.
5. BD-7 gaming: 10 pod-min, defines the text-unsolvable subset the leaderboard must use.
6. BD-6 label noise: 0 pod-min, 15 CPU-h, the one regime where a zero-shot reader is structurally advantaged.
7. BD-10 test–retest: 15 pod-min, decides whether F3 may be read per cell.
8. BD-5 Oracle grid + candidate order: 25 pod-min, closes two §9 threats with numbers.
9. BD-4 release + re-run: 0 pod-min, 3 CPU-h, the condition for anyone else re-running it.
10. BD-8 Gemma replication: 60 pod-min, the one-model objection, sized so the hour is not wasted.

## Open questions for the other lenses   (≤ 5 lines)
1. Causal lens: for SURFACE/TOPIC facts where prompt-only is saturated, can an edit-based MODEL label be defined so the
   triangle (BD-1) has M-odd items there, or are those tags MODEL-undefined by construction?
2. Probe lens: is the LR probe's held-out sign the right STATE label for BD-1, or the mass-mean probe's (IDEAS_R §1.6)?
3. Dataset lens: how many WS12 families can hold out templates AND entities (BD-7) without dropping below 200 test items?
4. Reader lens: is "Oracle with text, no insertion" (BD-7b) well-defined for the skip lens and the NLA, or only for the Oracle?
5. Does anyone's design produce a surprising cell criterion stricter than BD-10's, so the two can share the fresh-item pass?
