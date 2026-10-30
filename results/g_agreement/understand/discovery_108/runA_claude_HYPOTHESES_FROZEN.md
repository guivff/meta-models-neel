# HYPOTHESES FROZEN — discovery study

Frozen UTC: 2026-10-25T02:11:00.184248+00:00

This file was written after all six exploration briefs and all exploration tests, before any holdout extraction or red-team-context access. Nineteen promoted candidates consolidate to 18 confirmatory hypotheses. Only the two q2c string candidates overlap enough to merge; H07 requires BOTH unchanged cues, rather than selecting the better one.

## Exact inference and decision policy

- Every Hxx.py accepts `--data PATH_TO_HALF --output OUTPUT_JSON`. The shared implementation is `work/tests/metrics.py`; inference is `work/tests/engine.py`; exact lexical cues are `work/03/cues.py`. Dependencies and explore results are frozen by the SHA-256 manifest below.
- All rate/mean CIs use a percentile item-cluster bootstrap, 2,000 resamples, seed 20261025. Clusters are (sample,item), or tid for GLM. All within-cluster generations, readers, doses, and positions remain together. AUC and between-group contrasts stratify item resampling by class/group to preserve evaluability. Reader contrasts use pooled row weighting, with whole clusters resampled. Zero empirical widths are descriptive, not population certainty.
- Directional paired comparisons use one-sided whole-cluster swaps: exact enumeration with at most18 nonzero-difference clusters, otherwise19,999 Monte Carlo swaps with seed20261025 and a plus-one p-value. This is observational inference assuming within-cluster exchangeability under the null, not randomization by experimental design. Independent-group comparisons permute cluster labels, preserving group sizes, exactly if <=200,000 assignments, otherwise19,999 Monte Carlo assignments with the same seed and plus-one rule. These tests do not control unseen template-family dependence.
- AUROC tests permute labels on fixed score midranks; larger scores always predict A. Both classes are required. No orientation or threshold reversal is permitted.
- H05 swaps complete numerator/denominator bundles and conditions on both pooled denominators being positive. Its permutation null is JOINT reader-bundle exchangeability, stronger than equality of conditional rates. This assumption is an explicit red-team target.
- H06 uses an exact binomial gate on one hash-selected generation per item, selected BEFORE correctness filtering; its p-value requires independent items and a selection hash unrelated to output outcomes/exchangeable generation slots. It also retains the original full-row >=0.80 gates. H15 uses exact lower-tail binomial tests on one readout per item/reader. Both report exact one-sided95% bounds beside bootstrap CIs.
- Nonzero effect thresholds are observed magnitude gates. Significance tests for differences test the null of zero difference, not whether the population difference exceeds the magnitude threshold. H06/H15 absolute-rate nulls are explicitly0.80/0.05. H13 low-dose<=0.10 is an observed guard, not a certified population bound.
- Composite hypotheses H01–H03, H07 and H15 require all components. Their p-value is the maximum component p-value (intersection-union test). No independence of components is assumed.
- Raw PASS requires its frozen gates, evaluability, and raw one-sided p<=0.05. Final HOLDOUT PASS additionally requires Holm-adjusted p<=0.05 across all18 hypothesis slots. For an unevaluable hypothesis, retain a p=1 slot conservatively and label NOT EVALUABLE. Holm sorted adjusted p_i=max_{j<=i} min(1,(18-j+1)*p_j). CIs are not simultaneous/adjusted.
- FAIL means an evaluable predeclared prediction does not meet all gates and/or adjusted significance. Falsification is the opposite/nonpositive direction, a missed magnitude/low-rate guard, or insufficient corrected evidence. NOT EVALUABLE means missing required population/classes/pairs/fields; no fallback metric is substituted.
- Explore results are selection data; 53 text cues (106 reader evaluations,230 including sample strata) plus other documented comparisons were explored. Holm applies to the independent held-out18-family, not retroactively to all exploration attempts. Template/source overlap can weaken this independence and is reserved for red-team audit.
- q2b endpoints are output form or target alignment ONLY; edited truth is unknown. q2c endpoints refer to supplied original/source labels, not independently verified continuation state. No claim about activations, probes, asked scores, or causal internal-state specificity follows.
- No new inference after seeing holdout can enter this family. Any changed script/rule must be labeled post-holdout, untested. Rater2, strict-mention, no-mention and no-op checks are descriptive sensitivities, not extra confirmatory discoveries.

## Dependency commitment

Manifest: `out/FROZEN_CODE_MANIFEST.json`; SHA-256 `70f6d0c51210ebbe4f7ea57574252ca29ddf7879aacd3f500a1bdcd863e6f676`.
Holdout archive SHA-256: `9478f103c48d19c57e23d72d0ba620e37e64b6186af6a856e30f63ead423b88c`.

## Frozen hypotheses

### H01: Metadescriptive vocabulary is more frequent in NLA in each sample.
- Origin: 01:R1.
- Exact computation: For each q1/q2a/q2c, apply the bounded case-insensitive META_RX in metrics.py; paired NLA minus oracle readout rate >0.70 in every sample.
- Prediction/gates: all three gaps >0.70, all three 95% CIs exclude zero on positive side; IUT maximum p; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H01.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H01.py --data disc_data/explore --output out/frozen_explore/H01.json`.
- Explore result: q1: A 116/116.0=1; B 16/116.0=0.137931; gap 0.862069 CI [0.75, 0.9568965517241379]; clusters=29; p=5e-05; q2a: A 85/85.0=1; B 6/85.0=0.0705882; gap 0.929412 CI [0.8705882352941177, 0.9764705882352941]; clusters=85; p=5e-05; q2c: A 206/217.0=0.949309; B 7/217.0=0.0322581; gap 0.917051 CI [0.880184331797235, 0.9539170506912442]; clusters=217; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H01.py --data disc_data/holdout --output out/08/raw/H01.json`.

### H02: Han-script characters are more frequent in oracle in each sample.
- Origin: 01:R2.
- Exact computation: For each q1/q2a/q2c, detect U+3400–4DBF or U+4E00–9FFF; paired oracle minus NLA rate.
- Prediction/gates: all three gaps >0 with 95% CIs excluding zero; IUT maximum p; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H02.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H02.py --data disc_data/explore --output out/frozen_explore/H02.json`.
- Explore result: q1: A 44/116.0=0.37931; B 1/116.0=0.00862069; gap 0.37069 CI [0.22413793103448276, 0.5258620689655172]; clusters=29; p=4.57764e-05; q2a: A 52/85.0=0.611765; B 0/85.0=0; gap 0.611765 CI [0.5058823529411764, 0.7058823529411765]; clusters=85; p=5e-05; q2c: A 54/217.0=0.248848; B 3/217.0=0.0138249; gap 0.235023 CI [0.17511520737327188, 0.29493087557603687]; clusters=217; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H02.py --data disc_data/holdout --output out/08/raw/H02.json`.

### H03: NLA readouts contain more regex words in each sample.
- Origin: 01:R3.
- Exact computation: For each q1/q2a/q2c, count lowercased matches to \w+(?:['’]\w+)? including wrappers; paired NLA minus oracle mean.
- Prediction/gates: all three gaps >0 with 95% CIs excluding zero; IUT maximum p; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H03.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H03.py --data disc_data/explore --output out/frozen_explore/H03.json`.
- Explore result: q1: A 10148/116.0=87.4828; B 5931/116.0=51.1293; gap 36.3534 CI [31.52478448275862, 40.93124999999999]; clusters=29; p=5e-05; q2a: A 7551/85.0=88.8353; B 5051/85.0=59.4235; gap 29.4118 CI [27.200000000000003, 31.64735294117647]; clusters=85; p=5e-05; q2c: A 4540/217.0=20.9217; B 3830/217.0=17.6498; gap 3.27189 CI [2.6680875576036853, 3.861751152073733]; clusters=217; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H03.py --data disc_data/holdout --output out/08/raw/H03.json`.

### H04: Consensus-coded source invention is more frequent in NLA q1.
- Origin: 02:R02.1.
- Exact computation: I is both pass1.hallucination flags true; q1 paired NLA minus oracle I rate.
- Prediction/gates: gap >=0.50 and positive 95% CI; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H04.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H04.py --data disc_data/explore --output out/frozen_explore/H04.json`.
- Explore result: A 116/116.0=1; B 5/116.0=0.0431034; gap 0.956897 CI [0.896551724137931, 1.0]; clusters=29; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H04.py --data disc_data/holdout --output out/08/raw/H04.json`.

### H05: Absent-quotation precision for consensus invention differs by reader.
- Origin: 02:R02.2.
- Exact computation: Use exact QUOTE_RX/norm in metrics.py; condition on any extracted span absent from source; compare P(I|absent_quote,NLA) minus P(I|absent_quote,oracle). Swap complete numerator/denominator bundles.
- Prediction/gates: gap >=0.50 and positive 95% CI; both denominators required; joint exchangeability assumption; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H05.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H05.py --data disc_data/explore --output out/frozen_explore/H05.json`.
- Explore result: A 116/116.0=1; B 0/39.0=0; gap 1 CI [1.0, 1.0]; clusters=29; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H05.py --data disc_data/holdout --output out/08/raw/H05.json`.

### H06: NLA coded property matches can coexist with both source invention and absent quotations.
- Origin: 02:R02.3.
- Exact computation: q1 NLA correctness is both pass0 values agreeing A/B and equaling truth_AB. Require full eligible-row I and absent_quote rates >=0.80. Select min SHA256(discovery-one-generation-20261025:+id) generation per item BEFORE correctness conditioning; exact binomial test selected-correct joint I AND absent_quote against 0.80.
- Prediction/gates: both full-row rates >=0.80 and selected-correct joint event rate >=0.80; exact one-sided binomial gate; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H06.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H06.py --data disc_data/explore --output out/frozen_explore/H06.json`.
- Explore result: 19/19=1, bootstrap CI [1.0, 1.0], exact one-sided CI [0.8541314966877565, 1.0]; p=0.0144115; raw PASS=True.
- Holdout command: `python work/tests/H06.py --data disc_data/holdout --output out/08/raw/H06.json`.

### H07: Two fixed punctuation rules recover q2c string source labels.
- Origin: 03:C03.1 + 05:05C4.
- Exact computation: q2c/oracle/python_string: (1) registered quote_start8 score has AUROC>0.5; (2) raw ^-\s+/[A-Za-z]+" prefix (see exact Python regex in metrics.py) predicts A else B, balanced accuracy/AUROC>=0.80. Both required.
- Prediction/gates: first AUROC>0.5; second >=0.80; both 95% AUROC CIs exclude 0.5; IUT maximum p; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H07.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H07.py --data disc_data/explore --output out/frozen_explore/H07.json`.
- Explore result: quote_start8: AUROC 0.928261 CI [0.85, 1.0]; accuracy 40/43; p=5e-05; slash-word ASCII double quote prefix: AUROC 0.975 CI [0.925, 1.0]; accuracy 42/43; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H07.py --data disc_data/holdout --output out/08/raw/H07.json`.

### H08: The fixed sentiment lexicon discriminates source labels in oracle q2a.
- Origin: 03:C03.2.
- Exact computation: q2a/oracle/prose_sentiment, exact registered lexicon_full score from work/03/cues.py; larger predicts A.
- Prediction/gates: AUROC>0.5 and 95% CI excludes0.5; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H08.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H08.py --data disc_data/explore --output out/frozen_explore/H08.json`.
- Explore result: AUROC 1 CI [1.0, 1.0]; accuracy 24/24; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H08.py --data disc_data/holdout --output out/08/raw/H08.json`.

### H09: The fixed mathematics lexicon discriminates source labels in oracle q2a.
- Origin: 03:C03.3.
- Exact computation: q2a/oracle/latex_subject, exact registered lexicon_full score from work/03/cues.py; larger predicts A.
- Prediction/gates: AUROC>0.5 and 95% CI excludes0.5; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H09.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H09.py --data disc_data/explore --output out/frozen_explore/H09.json`.
- Explore result: AUROC 0.875 CI [0.7619047619047619, 0.9642857142857143]; accuracy 20/26; p=0.00015; raw PASS=True.
- Holdout command: `python work/tests/H09.py --data disc_data/holdout --output out/08/raw/H09.json`.

### H10: First-line pipes discriminate table-column source labels in oracle q2c.
- Origin: 03:C03.4.
- Exact computation: q2c/oracle/table_column, exact registered pipes_firstline_ge2 score; A if processed first line contains >=2 ASCII pipes else B.
- Prediction/gates: AUROC>0.5 and 95% CI excludes0.5; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H10.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H10.py --data disc_data/explore --output out/frozen_explore/H10.json`.
- Explore result: AUROC 0.675 CI [0.55, 0.8]; accuracy 27/40; p=0.0146; raw PASS=True.
- Holdout command: `python work/tests/H10.py --data disc_data/holdout --output out/08/raw/H10.json`.

### H11: NLA q1 item failure is higher for earlier_state than other tiers.
- Origin: 04:04a.
- Exact computation: Only q1 items with both readers and generations0,1,2,3. Success=(mentions and correct value) OR(enacts and correct enact_value), rater1. Failure is <=2/4 successes. Compare earlier_state minus all other tiers. Rater2 and strict states_property mention sensitivity descriptive.
- Prediction/gates: positive failure-rate gap and positive 95% CI; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H11.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H11.py --data disc_data/explore --output out/frozen_explore/H11.json`.
- Explore result: A 5/5=1; B 2/24=0.0833333; gap 0.916667 CI [0.7916666666666666, 1.0]; clusters=29; p=0.000176835; raw PASS=True.
- Holdout command: `python work/tests/H11.py --data disc_data/holdout --output out/08/raw/H11.json`.

### H12: Oracle q1 item failure is higher for local_form than content.
- Origin: 04:04b.
- Exact computation: Same complete-item majority rule as H11, oracle/rater1. Compare local_form minus content. Rater2 and strict states_property sensitivity descriptive.
- Prediction/gates: positive failure-rate gap and positive 95% CI; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H12.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H12.py --data disc_data/explore --output out/frozen_explore/H12.json`.
- Explore result: A 7/10=0.7; B 0/14=0; gap 0.7 CI [0.4, 1.0]; clusters=24; p=0.00025; raw PASS=True.
- Holdout command: `python work/tests/H12.py --data disc_data/holdout --output out/08/raw/H12.json`.

### H13: Parenthesis-target text form appears at high dose but rarely at doses0–4.
- Origin: 05:05C1.
- Exact computation: q2b/oracle/prose_paren: per-line balance over ASCII/fullwidth parentheses flags unmatched closing token; paired dose16 minus0 mean; pooled dose<=4 flag rate <=0.10.
- Prediction/gates: paired gap>=0.50 and positive95% CI, plus low-dose observed rate<=0.10; no edited-truth accuracy claim; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H13.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H13.py --data disc_data/explore --output out/frozen_explore/H13.json`.
- Explore result: A 9/9.0=1; B 0/9.0=0; gap 1 CI [1.0, 1.0]; clusters=9; p=0.00195312; raw PASS=True.
- Holdout command: `python work/tests/H13.py --data disc_data/holdout --output out/08/raw/H13.json`.

### H14: Table steering increases pipe density at dose4.
- Origin: 05:05C2.
- Exact computation: q2b/oracle/table_column, complete dose0/dose4 pairs; density=1000*ASCII pipe count/max(1,len(readout)); paired dose4 minus0.
- Prediction/gates: positive mean difference and positive95% CI; no target-column accuracy claim; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H14.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H14.py --data disc_data/explore --output out/frozen_explore/H14.json`.
- Explore result: A 516.223/13.0=39.7094; B 248.188/13.0=19.0914; gap 20.6181 CI [9.884857725350086, 32.24189357328618]; clusters=13; p=0.00231934; raw PASS=True.
- Holdout command: `python work/tests/H14.py --data disc_data/holdout --output out/08/raw/H14.json`.

### H15: Definite coded verbal property mentions are rare in q2c for both readers and raters.
- Origin: 05:05C3.
- Exact computation: q2c, separately each reader×rater: event mentions==true AND value in A/B. Requires one row/item/reader. Exact binomial lower-tail test against0.05 per cell; report all feature strata.
- Prediction/gates: all four observed rates<=0.05; IUT maximum one-sided binomial p; exact one-sided bounds also reported; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H15.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H15.py --data disc_data/explore --output out/frozen_explore/H15.json`.
- Explore result: nla rater1: 0/217=0, bootstrap CI [0.0, 0.0], exact one-sided CI [0.0, 0.013710362830301871]; p=1.46562e-05; nla rater2: 0/217=0, bootstrap CI [0.0, 0.0], exact one-sided CI [0.0, 0.013710362830301871]; p=1.46562e-05; oracle rater1: 0/217=0, bootstrap CI [0.0, 0.0], exact one-sided CI [0.0, 0.013710362830301871]; p=1.46562e-05; oracle rater2: 0/217=0, bootstrap CI [0.0, 0.0], exact one-sided CI [0.0, 0.013710362830301871]; p=1.46562e-05; raw PASS=True.
- Holdout command: `python work/tests/H15.py --data disc_data/holdout --output out/08/raw/H15.json`.

### H16: RL exceeds SFT in cleaned five-state endpoint agreement in the GLM sample.
- Origin: 06:C06_1.
- Exact computation: All GLM positions; unchanged supplied label(), current text left_ctx already includes token; remove only leading ^\* ? from each lens readout. Joint label(left_ctx+clean(readout))==label(left_ctx+next16), five columns per reader. Cluster tid.
- Prediction/gates: positive RL−SFT gap and positive95% CI; no-op baseline descriptive; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H16.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H16.py --data disc_data/explore --output out/frozen_explore/H16.json`.
- Explore result: A 14565/21360.0=0.681882; B 14121/21360.0=0.661096; gap 0.0207865 CI [0.013716117649084328, 0.02792437287819819]; clusters=54; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H16.py --data disc_data/holdout --output out/08/raw/H16.json`.

### H17: RL stochastic samples have more exact-string collisions than SFT.
- Origin: 06:C06_2.
- Exact computation: All GLM positions; six unordered pairs within s1..s4 for each reader, full raw string equality; paired tid totals.
- Prediction/gates: positive RL−SFT collision-rate gap and positive95% CI; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H17.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H17.py --data disc_data/explore --output out/frozen_explore/H17.json`.
- Explore result: A 842/25632.0=0.0328496; B 53/25632.0=0.00206773; gap 0.0307818 CI [0.025067984168070448, 0.037059401805850704]; clusters=54; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H17.py --data disc_data/holdout --output out/08/raw/H17.json`.

### H18: RL readouts more often contain assistant-reference vocabulary than SFT.
- Origin: 06:C06_3.
- Exact computation: All GLM positions; bounded case-insensitive assistant|chatgpt|language model in each of five columns; paired tid totals.
- Prediction/gates: positive RL−SFT lexical-rate gap and positive95% CI; no latent-awareness claim; final Holm p<=0.05.
- Falsifier: any specified gate fails or corrected evidence is insufficient; unavailable required population is NOT EVALUABLE.
- Script: `work/tests/H18.py` (shared frozen dependencies above).
- Explore command: `python work/tests/H18.py --data disc_data/explore --output out/frozen_explore/H18.json`.
- Explore result: A 109/21360.0=0.005103; B 17/21360.0=0.00079588; gap 0.00430712 CI [0.002375603289642616, 0.006436787007684861]; clusters=54; p=5e-05; raw PASS=True.
- Holdout command: `python work/tests/H18.py --data disc_data/holdout --output out/08/raw/H18.json`.

