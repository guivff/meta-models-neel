# Frozen hypotheses — independent replication

Frozen UTC: 2026-10-25T02:11:42.078401+00:00

No holdout archive member or red-team context has been opened. All 28 tests were selected and implemented using explore only. No rules may change after this freeze.

## Family, decision rules and interpretation
- There are 28 frozen statistical hypotheses. Every candidate proposed in the six registries is retained, including two explicitly weak/nonrecommended Brief 02 candidates. Overlapping scientific claims are consolidated in the final narrative, but different operational rules remain separate tests and both count in the family (notably H12 and H22 string cues).
- Raw PASS = evaluable AND all original numerical thresholds hold AND any prespecified CI gate holds AND one-sided raw p <= .05. Corrected PASS replaces raw p with the Holm-adjusted p <= .05. A numerical-threshold match alone is reported separately. Not-evaluable tests receive p=1 for a conservative fixed 28-test Holm family; they remain NOT EVALUABLE, never PASS.
- Holm step-down: sort all 28 p-values; adjusted p at rank i is the running maximum of min(1,(28-i+1)*p_i). No hypotheses are removed based on explore or holdout significance.
- Rate CIs: percentile cluster bootstrap, 2,000 resamples, seed 20261025. The cluster is the whole item (retaining generations/readers and repeated samples), or whole tid for GLM. Tier contrasts resample within compared tiers. Item-sampled CIs with missing classes omit undefined replicates and report the valid count. Saturated empirical CIs are not population certainty.
- Directional paired sign-flip/permutation tests evaluate the stated exchangeability/zero-association null, not the numerical effect-size floor. Floors are separately checked point-estimate predictions. Exchangeability assumptions and observational/template dependence limit population inference.
- Absolute-rate tests use the specified boundary. Equal-cluster bounded-mean p-values use exact binomial tails only for binary-by-design cluster outcomes, otherwise the conservative Bernoulli KL/Chernoff bound even if observed proportions happen to equal 0 or 1. Where cluster exposures differ, the p-value tests the explicitly reported equal-cluster estimand while the original threshold/CI uses the row-weighted estimand; these are distinct conjunctive criteria, not interchangeable estimates.
- Composite hypotheses use the maximum component p-value (intersection-union), then participate once in the global Holm family. A surviving composite requires every component prediction.
- Monte Carlo null draws: 19,999, seed 20261025, plus-one correction; exact sign enumeration for at most 18 nonzero clusters. Full definitions reside in the hashed modules and specifications below.
- Exploration was broad: Brief 03 alone tried 27 cue definitions and 120 feature/reader score cells; other task diagnostics are preserved. Holm controls the predeclared holdout family, not the exploratory search or all possible future interpretations.
- q2b outcomes are target-aligned text/surface changes only, never accuracy against an independently observed edited state. No inference about activations, probes, or asked scores is authorized by this pack.

## Input hashes
- discovery_data.zip: `7ded779383efeda9d983ad472049fd216b1273ed91c5fc630670612b7b86e2ba`
- discovery_prompts.zip: `929c65c9080e6ab1f21e6463178099a7d71cb444250b4d202ef147dd10eb6e00`
- holdout_SEALED.zip: `9478f103c48d19c57e23d72d0ba620e37e64b6186af6a856e30f63ead423b88c`

## Frozen tests

### H01: NLA explanation openings and oracle majority-bulleted layouts recur.

Script: `work/tests/H01.py`

Explore command: `python -B work/tests/H01.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H01.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H01",
  "candidate_id": "01_format",
  "claim": "NLA explanation openings and oracle majority-bulleted layouts recur.",
  "population": "q1, q2a, q2c; both readers; all retained complete readout pairs",
  "exact_computation": "explanation = readout.startswith(\"<explanation>\"). Split on lines and discard whitespace-only lines. A bullet line matches r\"^\\s*(?:[-*+]\\s|\\d+[.)]\\s)\". list_majority is true iff at least half the nonblank lines are bullets, false for no nonblank lines. Thresholds use NLA explanation rate and oracle list rate. Directional contrasts are explanation NLA-oracle and list oracle-NLA, averaged over paired readouts.",
  "threshold": "NLA explanation rate >=0.99 AND oracle list_majority rate >=0.99",
  "falsifier": "Either threshold rate <0.99",
  "ci_rule": "Both directional contrast 95% CI lower limits >0",
  "null": "At least one specified positive contrast is non-positive, under item-level sign-exchangeability of the paired item contributions. The p-value does not test the magnitude threshold. Contrasts: explanation NLA-oracle; list oracle-NLA.",
  "status": "exploratory frozen candidate; no holdout inspected",
  "weighting": "readout weighted; summed paired differences within item, not equal item means",
  "p_method": "One-sided item-level paired sign-flip on summed row contributions; exact enumeration for <=18 nonzero items, otherwise 19,999 random sign flips with +1 correction, seed 20261025. For a conjunction, the reported intersection-union p-value is the maximum constituent p-value. The null concerns directional contrasts, not the empirical magnitude thresholds.",
  "ci_method": "95% percentile item-cluster bootstrap, 2,000 resamples, seed 20261025; all retained rows sharing an item are resampled together across readers, samples, and generations. Readout-weighted estimands: sums / retained readout counts. A directional CI passes iff its lower limit is >0.",
  "pairing": "For reader contrasts, key=(item,sample,generation), requiring exactly one NLA and one oracle record per retained key; no unmatched records are silently dropped. Aggregate all keys sharing item into one cluster. H04 pairs two features within each source-observed row and does not require cross-reader pairing. At least two independent items are required per contrast.",
  "missing_policy": "Missing required sample, reader, field, duplicate pairing key, incomplete reader pair, or fewer than two items makes the corresponding candidate not evaluable. H04 excludes q1 rows with absent/null source_text, preserving its original population."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"items": 328, "readout_pairs": 418, "readouts": 836, "readouts_by_reader": {"nla": 418, "oracle": 418}, "readouts_by_sample": {"q1": 232, "q2a": 170, "q2c": 434}}`
- `explanation_nla_minus_oracle`: estimate=1.0, CI95=[1.0, 1.0], n=328
- `list_oracle_minus_nla`: estimate=1.0, CI95=[1.0, 1.0], n=328
- `nla_explanation`: estimate=1.0, CI95=[1.0, 1.0], n=328
- `oracle_list`: estimate=1.0, CI95=[1.0, 1.0], n=328

Complete raw explore result: `out/consolidation/explore/H01.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H02: NLA uses descriptive opening vocabulary much more frequently.

Script: `work/tests/H02.py`

Explore command: `python -B work/tests/H02.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H02.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H02",
  "candidate_id": "01_description",
  "claim": "NLA uses descriptive opening vocabulary much more frequently.",
  "population": "q1, q2a, q2c; both readers; all retained complete readout pairs",
  "exact_computation": "Remove leading pattern r\"^\\s*<explanation>\\s*\". In the first 180 Unicode characters of the remaining payload, search case-insensitively for r\"\\b(?:format|pattern|structured|style|tone|register|syntax|token|snippet|phrase|sentence|narrative|context)\\b\". Compute per-reader readout-level positive rates and their NLA-oracle difference.",
  "threshold": "NLA description rate >=0.95 AND oracle description rate <=0.10",
  "falsifier": "NLA description rate <0.95 OR oracle description rate >0.10",
  "ci_rule": "NLA-oracle description difference 95% CI lower limit >0",
  "null": "At least one specified positive contrast is non-positive, under item-level sign-exchangeability of the paired item contributions. The p-value does not test the magnitude threshold. Contrast: description NLA-oracle.",
  "status": "exploratory frozen candidate; no holdout inspected",
  "weighting": "readout weighted; summed paired differences within item, not equal item means",
  "p_method": "One-sided item-level paired sign-flip on summed row contributions; exact enumeration for <=18 nonzero items, otherwise 19,999 random sign flips with +1 correction, seed 20261025. For a conjunction, the reported intersection-union p-value is the maximum constituent p-value. The null concerns directional contrasts, not the empirical magnitude thresholds.",
  "ci_method": "95% percentile item-cluster bootstrap, 2,000 resamples, seed 20261025; all retained rows sharing an item are resampled together across readers, samples, and generations. Readout-weighted estimands: sums / retained readout counts. A directional CI passes iff its lower limit is >0.",
  "pairing": "For reader contrasts, key=(item,sample,generation), requiring exactly one NLA and one oracle record per retained key; no unmatched records are silently dropped. Aggregate all keys sharing item into one cluster. H04 pairs two features within each source-observed row and does not require cross-reader pairing. At least two independent items are required per contrast.",
  "missing_policy": "Missing required sample, reader, field, duplicate pairing key, incomplete reader pair, or fewer than two items makes the corresponding candidate not evaluable. H04 excludes q1 rows with absent/null source_text, preserving its original population."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"items": 328, "readout_pairs": 418, "readouts": 836, "readouts_by_reader": {"nla": 418, "oracle": 418}, "readouts_by_sample": {"q1": 232, "q2a": 170, "q2c": 434}}`
- `nla_description`: estimate=0.9832535885167464, CI95=[0.9691906454524938, 0.9949241791428388], n=328
- `nla_minus_oracle`: estimate=0.9617224880382775, CI95=[0.9424451015104147, 0.9788260090921614], n=328
- `oracle_description`: estimate=0.0215311004784689, CI95=[0.009152275558659946, 0.03720959085925327], n=328

Complete raw explore result: `out/consolidation/explore/H02.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H03: NLA readouts remain longer within each sample.

Script: `work/tests/H03.py`

Explore command: `python -B work/tests/H03.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H03.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H03",
  "candidate_id": "01_length",
  "claim": "NLA readouts remain longer within each sample.",
  "population": "q1, q2a, q2c evaluated separately; both readers",
  "exact_computation": "For each sample separately, calculate Python len(readout) in Unicode code points, then the paired readout-weighted mean NLA-oracle difference. Each item contributes its summed paired character differences to that sample-specific sign-flip test.",
  "threshold": "All three sample-specific NLA-oracle mean character differences >=25",
  "falsifier": "Any q1, q2a, or q2c mean difference <25 characters",
  "ci_rule": "All three sample-specific difference 95% CI lower limits >0",
  "null": "At least one specified positive contrast is non-positive, under item-level sign-exchangeability of the paired item contributions. The p-value does not test the magnitude threshold. Contrasts: NLA-oracle character length in q1, q2a, q2c.",
  "status": "exploratory frozen candidate; no holdout inspected",
  "weighting": "readout weighted; summed paired differences within item, not equal item means",
  "p_method": "One-sided item-level paired sign-flip on summed row contributions; exact enumeration for <=18 nonzero items, otherwise 19,999 random sign flips with +1 correction, seed 20261025. For a conjunction, the reported intersection-union p-value is the maximum constituent p-value. The null concerns directional contrasts, not the empirical magnitude thresholds.",
  "ci_method": "95% percentile item-cluster bootstrap, 2,000 resamples, seed 20261025; all retained rows sharing an item are resampled together across readers, samples, and generations. Readout-weighted estimands: sums / retained readout counts. A directional CI passes iff its lower limit is >0.",
  "pairing": "For reader contrasts, key=(item,sample,generation), requiring exactly one NLA and one oracle record per retained key; no unmatched records are silently dropped. Aggregate all keys sharing item into one cluster. H04 pairs two features within each source-observed row and does not require cross-reader pairing. At least two independent items are required per contrast.",
  "missing_policy": "Missing required sample, reader, field, duplicate pairing key, incomplete reader pair, or fewer than two items makes the corresponding candidate not evaluable. H04 excludes q1 rows with absent/null source_text, preserving its original population."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"items": 328, "readout_pairs": 418, "readouts": 836, "readouts_by_reader": {"nla": 418, "oracle": 418}, "readouts_by_sample": {"q1": 232, "q2a": 170, "q2c": 434}}`
- `q1.nla_chars`: estimate=621.3534482758621, CI95=[606.9909482758621, 635.7021551724138], n=29
- `q1.nla_minus_oracle`: estimate=286.7586206896552, CI95=[261.68706896551726, 311.4260775862069], n=29
- `q1.oracle_chars`: estimate=334.5948275862069, CI95=[303.4603448275862, 366.9286637931034], n=29
- `q2a.nla_chars`: estimate=637.4823529411765, CI95=[630.2464705882353, 644.7676470588235], n=85
- `q2a.nla_minus_oracle`: estimate=248.68235294117648, CI95=[235.8470588235294, 261.2605882352941], n=85
- `q2a.oracle_chars`: estimate=388.8, CI95=[374.9991176470588, 403.44735294117646], n=85
- `q2c.nla_chars`: estimate=160.80184331797236, CI95=[158.67730414746543, 162.9221198156682], n=217
- `q2c.nla_minus_oracle`: estimate=41.84331797235023, CI95=[38.45587557603687, 45.17534562211981], n=217
- `q2c.oracle_chars`: estimate=118.95852534562212, CI95=[115.6589861751152, 122.4479262672811], n=217

Complete raw explore result: `out/consolidation/explore/H03.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H04: Both readers preserve the final source token more readily than source passages.

Script: `work/tests/H04.py`

Explore command: `python -B work/tests/H04.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H04.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H04",
  "candidate_id": "01_copy",
  "claim": "Both readers preserve the final source token more readily than source passages.",
  "population": "q1 source_text-observed rows only; each reader separately",
  "exact_computation": "Tokenize lowercase text using re.findall(r\"\\w+\", text, re.UNICODE). coverage is the fraction of output-token positions covered by any contiguous output trigram exactly present in the source trigram set (zero for empty output). final_present is whether the final source token occurs among output tokens (false for an empty source-token sequence). For each reader, compute readout-weighted mean coverage and final_present rate. Within each item sum row differences final_present-coverage for the directional sign-flip test.",
  "threshold": "For EACH reader: coverage mean <0.10 AND final_present rate >=0.75",
  "falsifier": "Either reader coverage mean >=0.10 OR final_present rate <0.75",
  "ci_rule": "Both readers final_present-minus-coverage 95% CI lower limits >0",
  "null": "At least one specified positive contrast is non-positive, under item-level sign-exchangeability of the paired item contributions. The p-value does not test the magnitude threshold. Contrasts: within-reader final_present-coverage for NLA and oracle. This explicitly tests a contrast, not coverage<0.10 or final_present>=0.75 population thresholds.",
  "exploratory_note": "The final-source-token feature was added post-hoc after rater inspection.",
  "status": "exploratory frozen candidate; no holdout inspected",
  "weighting": "readout weighted; summed paired differences within item, not equal item means",
  "p_method": "One-sided item-level paired sign-flip on summed row contributions; exact enumeration for <=18 nonzero items, otherwise 19,999 random sign flips with +1 correction, seed 20261025. For a conjunction, the reported intersection-union p-value is the maximum constituent p-value. The null concerns directional contrasts, not the empirical magnitude thresholds.",
  "ci_method": "95% percentile item-cluster bootstrap, 2,000 resamples, seed 20261025; all retained rows sharing an item are resampled together across readers, samples, and generations. Readout-weighted estimands: sums / retained readout counts. A directional CI passes iff its lower limit is >0.",
  "pairing": "For reader contrasts, key=(item,sample,generation), requiring exactly one NLA and one oracle record per retained key; no unmatched records are silently dropped. Aggregate all keys sharing item into one cluster. H04 pairs two features within each source-observed row and does not require cross-reader pairing. At least two independent items are required per contrast.",
  "missing_policy": "Missing required sample, reader, field, duplicate pairing key, incomplete reader pair, or fewer than two items makes the corresponding candidate not evaluable. H04 excludes q1 rows with absent/null source_text, preserving its original population."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"items": 328, "q1_rows_excluded_missing_source": 0, "readouts": 836, "readouts_by_reader": {"nla": 418, "oracle": 418}, "readouts_by_sample": {"q1": 232, "q2a": 170, "q2c": 434}, "source_observed": {"items": 29, "readouts": 232, "readouts_by_reader": {"nla": 116, "oracle": 116}, "readouts_by_sample": {"q1": 232, "q2a": 0, "q2c": 0}}}`
- `nla.coverage`: estimate=0.024883212040263992, CI95=[0.009795217177232573, 0.04166333216002626], n=29
- `nla.final_minus_coverage`: estimate=0.871668512097667, CI95=[0.7489901813962979, 0.9738288295773792], n=29
- `nla.final_present`: estimate=0.896551724137931, CI95=[0.7922413793103449, 1.0], n=29
- `oracle.coverage`: estimate=0.027113576271686545, CI95=[0.005882570932580758, 0.055013669910150734], n=29
- `oracle.final_minus_coverage`: estimate=0.8694381478662446, CI95=[0.7483263401128392, 0.9709701073756764], n=29
- `oracle.final_present`: estimate=0.896551724137931, CI95=[0.7922413793103449, 1.0], n=29

Complete raw explore result: `out/consolidation/explore/H04.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H05: Oracle more often contains Han script.

Script: `work/tests/H05.py`

Explore command: `python -B work/tests/H05.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H05.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H05",
  "candidate_id": "01_han",
  "claim": "Oracle more often contains Han script.",
  "population": "q1, q2a, q2c; both readers; all retained complete readout pairs",
  "exact_computation": "han is the presence of any character in inclusive U+3400..U+9FFF. Compute readout-weighted oracle-NLA presence-rate difference. Each item contributes its sum of paired row differences.",
  "threshold": "Oracle-NLA Han-presence rate difference >=0.20",
  "falsifier": "Oracle-NLA Han-presence rate difference <0.20",
  "ci_rule": "Oracle-NLA Han-presence difference 95% CI lower limit >0",
  "null": "At least one specified positive contrast is non-positive, under item-level sign-exchangeability of the paired item contributions. The p-value does not test the magnitude threshold. Contrast: Han-presence oracle-NLA.",
  "status": "exploratory frozen candidate; no holdout inspected",
  "weighting": "readout weighted; summed paired differences within item, not equal item means",
  "p_method": "One-sided item-level paired sign-flip on summed row contributions; exact enumeration for <=18 nonzero items, otherwise 19,999 random sign flips with +1 correction, seed 20261025. For a conjunction, the reported intersection-union p-value is the maximum constituent p-value. The null concerns directional contrasts, not the empirical magnitude thresholds.",
  "ci_method": "95% percentile item-cluster bootstrap, 2,000 resamples, seed 20261025; all retained rows sharing an item are resampled together across readers, samples, and generations. Readout-weighted estimands: sums / retained readout counts. A directional CI passes iff its lower limit is >0.",
  "pairing": "For reader contrasts, key=(item,sample,generation), requiring exactly one NLA and one oracle record per retained key; no unmatched records are silently dropped. Aggregate all keys sharing item into one cluster. H04 pairs two features within each source-observed row and does not require cross-reader pairing. At least two independent items are required per contrast.",
  "missing_policy": "Missing required sample, reader, field, duplicate pairing key, incomplete reader pair, or fewer than two items makes the corresponding candidate not evaluable. H04 excludes q1 rows with absent/null source_text, preserving its original population."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"items": 328, "readout_pairs": 418, "readouts": 836, "readouts_by_reader": {"nla": 418, "oracle": 418}, "readouts_by_sample": {"q1": 232, "q2a": 170, "q2c": 434}}`
- `nla`: estimate=0.009569377990430622, CI95=[0.002288329519450801, 0.02050143099118042], n=328
- `oracle`: estimate=0.3588516746411483, CI95=[0.30413625304136255, 0.41737605932203387], n=328
- `oracle_minus_nla`: estimate=0.3492822966507177, CI95=[0.29465708108230165, 0.4079690179907309], n=328

Complete raw explore result: `out/consolidation/explore/H05.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H06: Oracle repeats more trigrams within individual readouts.

Script: `work/tests/H06.py`

Explore command: `python -B work/tests/H06.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H06.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H06",
  "candidate_id": "01_repetition",
  "claim": "Oracle repeats more trigrams within individual readouts.",
  "population": "q1, q2a, q2c; both readers; all retained complete readout pairs",
  "exact_computation": "Tokenize lowercase readout using re.findall(r\"\\w+\", text, re.UNICODE); preserve the original output wrappers. repeat = 1 - distinct contiguous trigram count / total contiguous trigram count, with zero for fewer than three tokens. Compute readout-weighted oracle-NLA mean repeat difference; sum paired row differences within item for the sign-flip contributions.",
  "threshold": "Oracle-NLA mean repeated-trigram fraction difference >=0.02",
  "falsifier": "Oracle-NLA mean repeated-trigram fraction difference <0.02",
  "ci_rule": "Oracle-NLA repeated-trigram difference 95% CI lower limit >0",
  "null": "At least one specified positive contrast is non-positive, under item-level sign-exchangeability of the paired item contributions. The p-value does not test the magnitude threshold. Contrast: repeated-trigram fraction oracle-NLA.",
  "status": "exploratory frozen candidate; no holdout inspected",
  "weighting": "readout weighted; summed paired differences within item, not equal item means",
  "p_method": "One-sided item-level paired sign-flip on summed row contributions; exact enumeration for <=18 nonzero items, otherwise 19,999 random sign flips with +1 correction, seed 20261025. For a conjunction, the reported intersection-union p-value is the maximum constituent p-value. The null concerns directional contrasts, not the empirical magnitude thresholds.",
  "ci_method": "95% percentile item-cluster bootstrap, 2,000 resamples, seed 20261025; all retained rows sharing an item are resampled together across readers, samples, and generations. Readout-weighted estimands: sums / retained readout counts. A directional CI passes iff its lower limit is >0.",
  "pairing": "For reader contrasts, key=(item,sample,generation), requiring exactly one NLA and one oracle record per retained key; no unmatched records are silently dropped. Aggregate all keys sharing item into one cluster. H04 pairs two features within each source-observed row and does not require cross-reader pairing. At least two independent items are required per contrast.",
  "missing_policy": "Missing required sample, reader, field, duplicate pairing key, incomplete reader pair, or fewer than two items makes the corresponding candidate not evaluable. H04 excludes q1 rows with absent/null source_text, preserving its original population."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"items": 328, "readout_pairs": 418, "readouts": 836, "readouts_by_reader": {"nla": 418, "oracle": 418}, "readouts_by_sample": {"q1": 232, "q2a": 170, "q2c": 434}}`
- `nla`: estimate=0.008019480870964121, CI95=[0.005682850008239224, 0.010773467298448452], n=328
- `oracle`: estimate=0.04361342669224628, CI95=[0.03513913002343008, 0.05306382900824874], n=328
- `oracle_minus_nla`: estimate=0.035593945821282155, CI95=[0.027554899965566978, 0.043697317151734215], n=328

Complete raw explore result: `out/consolidation/explore/H06.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H07: NLA source-invention proxy remains common.

Script: `work/tests/H07.py`

Explore command: `python -B work/tests/H07.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H07.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H07",
  "original_candidate": "02-A",
  "claim": "NLA source-invention proxy remains common.",
  "population": "q1 NLA rows with source_text",
  "exact_computation": "Require readout.startswith('<explanation>'). Remove exactly that prefix, strip whitespace, split on literal double newline, and join the first two paragraphs with double newline. Flag if either (a) a QUOTES-delimited span in those paragraphs is not a case-sensitive source substring after regex whitespace collapse and strip on each string, or (b) a FORMATS match in those paragraphs is absent as a case-insensitive whole word from source_text. QUOTES and FORMATS regexes are frozen constants in brief02.py. Average the binary flag over eligible rows.",
  "metric": "source_invention_proxy",
  "boundary": 0.8,
  "threshold": "row-weighted mean >= 0.80",
  "falsifier": "row-weighted mean < 0.80",
  "eligibility": {
    "min_rows": 1,
    "min_items": 1
  },
  "alternative": "greater",
  "null": "The equal-item mean source-invention-proxy rate is <= 0.80.",
  "p_method": "inference.bounded_mean_p on one success/eligible-row proportion per contributing item, always using the default conservative exp(-K*KL(equal_item_mean||boundary)) bound, including when observed item proportions are all 0 or 1. These proportions are not binary by design. The bound returns 1 when the observed mean is not in the alternative direction. Items are treated as independent bounded observations. The p-value tests the equal-item mean; the descriptive point estimate and threshold test use the row-weighted mean, which can differ when eligible rows/item differ.",
  "original_recommendation": true,
  "limitations": [
    "The proxy requires explanation-style output and is not a reader-neutral source-faithfulness classifier."
  ],
  "exploratory": true,
  "ci_method": {
    "unit": "whole q1 source-bearing item, preserving all eligible generations/readers",
    "resamples": 2000,
    "seed": 20261025,
    "interval": "percentile 95%",
    "zero_eligible_denominator_draws": "omit and report valid_resamples",
    "ci_pass_rule": "true whenever original eligibility requirements hold; no additional gate"
  },
  "frozen_regexes": {
    "QUOTES": "`([^`\\n]{2,300})`|\"([^\"\\n]{2,300})\"|“([^”\\n]{2,300})”",
    "FORMATS": "\\b(?:system|terminal|log|logs|metadata|platform|roleplay|prompt|timestamp|timestamps|blog|profile|interface|compilation|disclaimer)\\b",
    "FORMATS_flags": "IGNORECASE",
    "POLARITY_CONTEXT": {
      "negative": [
        "\\b(?:schools?|education|writings|civilization|curriculum)\\b",
        "\\b(?:damaged|poor|hopeless|disastrous|beyond repair|deteriorating|declining)\\b"
      ],
      "positive": [
        "\\b(?:publisher|colleagues|clinic|sponsor|books|farms)\\b",
        "\\b(?:encouraging|hope|lifted|good news)\\b"
      ]
    },
    "POLARITY_CONTEXT_flags": "IGNORECASE"
  }
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.004605888309689714.

Counts: `{"input_rows": 958, "q1_rows": 232, "source_bearing_q1_rows": 232, "eligible_rows": 116, "positive_rows": 115, "eligible_items": 29, "bootstrap_item_universe": 29}`


Complete raw explore result: `out/consolidation/explore/H07.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H08: Correct property identification can coexist with source invention.

Script: `work/tests/H08.py`

Explore command: `python -B work/tests/H08.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H08.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H08",
  "original_candidate": "02-B",
  "claim": "Correct property identification can coexist with source invention.",
  "population": "q1 NLA rows with source_text where both pass0.value labels agree in A/B and equal truth_AB",
  "exact_computation": "Select rows where rater1_codes.pass0.value == rater2_codes.pass0.value, that shared value is A or B, and equals truth_AB. Require readout.startswith('<explanation>'). Remove exactly that prefix, strip whitespace, split on literal double newline, and join the first two paragraphs with double newline. Flag if either (a) a QUOTES-delimited span in those paragraphs is not a case-sensitive source substring after regex whitespace collapse and strip on each string, or (b) a FORMATS match in those paragraphs is absent as a case-insensitive whole word from source_text. QUOTES and FORMATS regexes are frozen constants in brief02.py. Average the binary flag over these rows.",
  "metric": "source_invention_proxy",
  "boundary": 0.8,
  "threshold": "row-weighted mean >= 0.80, requiring >=10 eligible rows",
  "falsifier": "row-weighted mean < 0.80 with >=10 eligible rows; otherwise inconclusive",
  "eligibility": {
    "min_rows": 10,
    "min_items": 1
  },
  "alternative": "greater",
  "null": "The equal-item mean source-invention-proxy rate conditional on both-rater property correctness is <= 0.80.",
  "p_method": "inference.bounded_mean_p on one success/eligible-row proportion per contributing item, always using the default conservative exp(-K*KL(equal_item_mean||boundary)) bound, including when observed item proportions are all 0 or 1. These proportions are not binary by design. The bound returns 1 when the observed mean is not in the alternative direction. Items are treated as independent bounded observations. The p-value tests the equal-item mean; the descriptive point estimate and threshold test use the row-weighted mean, which can differ when eligible rows/item differ.",
  "original_recommendation": true,
  "limitations": [
    "Correctness is an existing-rater consensus label, not independently re-adjudicated truth of the entire readout.",
    "Conditioning on rater agreement can create unequal eligible rows per item; row and equal-item estimates must be shown separately.",
    "The proxy requires explanation-style output and captures source framing rather than all unsupported content."
  ],
  "exploratory": true,
  "ci_method": {
    "unit": "whole q1 source-bearing item, preserving all eligible generations/readers",
    "resamples": 2000,
    "seed": 20261025,
    "interval": "percentile 95%",
    "zero_eligible_denominator_draws": "omit and report valid_resamples",
    "ci_pass_rule": "true whenever original eligibility requirements hold; no additional gate"
  },
  "frozen_regexes": {
    "QUOTES": "`([^`\\n]{2,300})`|\"([^\"\\n]{2,300})\"|“([^”\\n]{2,300})”",
    "FORMATS": "\\b(?:system|terminal|log|logs|metadata|platform|roleplay|prompt|timestamp|timestamps|blog|profile|interface|compilation|disclaimer)\\b",
    "FORMATS_flags": "IGNORECASE",
    "POLARITY_CONTEXT": {
      "negative": [
        "\\b(?:schools?|education|writings|civilization|curriculum)\\b",
        "\\b(?:damaged|poor|hopeless|disastrous|beyond repair|deteriorating|declining)\\b"
      ],
      "positive": [
        "\\b(?:publisher|colleagues|clinic|sponsor|books|farms)\\b",
        "\\b(?:encouraging|hope|lifted|good news)\\b"
      ]
    },
    "POLARITY_CONTEXT_flags": "IGNORECASE"
  }
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.02048989622501235.

Counts: `{"input_rows": 958, "q1_rows": 232, "source_bearing_q1_rows": 232, "eligible_rows": 74, "positive_rows": 73, "eligible_items": 22, "bootstrap_item_universe": 29}`


Complete raw explore result: `out/consolidation/explore/H08.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H09: Exact quotation support and quotation novelty commonly coexist in NLA.

Script: `work/tests/H09.py`

Explore command: `python -B work/tests/H09.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H09.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H09",
  "original_candidate": "02-C",
  "claim": "Exact quotation support and quotation novelty commonly coexist in NLA.",
  "population": "q1 NLA rows with source_text",
  "exact_computation": "Extract QUOTES matches from the complete readout: backtick, straight double-quote or curly double-quote spans of length 2-300, excluding literal newline and closing delimiter. A span is supported iff its whitespace-collapsed stripped string occurs case-sensitively in the similarly normalized source_text. Flag iff at least one supported and at least one unsupported span occur. Average flags over eligible rows.",
  "metric": "mixed_quote_support",
  "boundary": 0.5,
  "threshold": "row-weighted mean >= 0.50",
  "falsifier": "row-weighted mean < 0.50",
  "eligibility": {
    "min_rows": 1,
    "min_items": 1
  },
  "alternative": "greater",
  "null": "The equal-item mean mixed supported-and-absent quotation rate is <= 0.50.",
  "p_method": "inference.bounded_mean_p on one success/eligible-row proportion per contributing item, always using the default conservative exp(-K*KL(equal_item_mean||boundary)) bound, including when observed item proportions are all 0 or 1. These proportions are not binary by design. The bound returns 1 when the observed mean is not in the alternative direction. Items are treated as independent bounded observations. The p-value tests the equal-item mean; the descriptive point estimate and threshold test use the row-weighted mean, which can differ when eligible rows/item differ.",
  "original_recommendation": true,
  "limitations": [
    "Absent quotations can be proposed continuations or paraphrases; this flag is not a semantic invention detector."
  ],
  "exploratory": true,
  "ci_method": {
    "unit": "whole q1 source-bearing item, preserving all eligible generations/readers",
    "resamples": 2000,
    "seed": 20261025,
    "interval": "percentile 95%",
    "zero_eligible_denominator_draws": "omit and report valid_resamples",
    "ci_pass_rule": "true whenever original eligibility requirements hold; no additional gate"
  },
  "frozen_regexes": {
    "QUOTES": "`([^`\\n]{2,300})`|\"([^\"\\n]{2,300})\"|“([^”\\n]{2,300})”",
    "FORMATS": "\\b(?:system|terminal|log|logs|metadata|platform|roleplay|prompt|timestamp|timestamps|blog|profile|interface|compilation|disclaimer)\\b",
    "FORMATS_flags": "IGNORECASE",
    "POLARITY_CONTEXT": {
      "negative": [
        "\\b(?:schools?|education|writings|civilization|curriculum)\\b",
        "\\b(?:damaged|poor|hopeless|disastrous|beyond repair|deteriorating|declining)\\b"
      ],
      "positive": [
        "\\b(?:publisher|colleagues|clinic|sponsor|books|farms)\\b",
        "\\b(?:encouraging|hope|lifted|good news)\\b"
      ]
    },
    "POLARITY_CONTEXT_flags": "IGNORECASE"
  }
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.42603711608683115.

Counts: `{"input_rows": 958, "q1_rows": 232, "source_bearing_q1_rows": 232, "eligible_rows": 116, "positive_rows": 72, "eligible_items": 29, "bootstrap_item_universe": 29}`


Complete raw explore result: `out/consolidation/explore/H09.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H10: Both-rater property contradiction is rare in NLA.

Script: `work/tests/H10.py`

Explore command: `python -B work/tests/H10.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H10.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H10",
  "original_candidate": "02-D",
  "claim": "Both-rater property contradiction is rare in NLA.",
  "population": "q1 NLA rows with source_text",
  "exact_computation": "Flag iff rater1_codes.pass0.value == rater2_codes.pass0.value, the shared value is A or B, and it differs from truth_AB. Average flags over every eligible NLA row, including unassigned/disagreeing rows as zeros.",
  "metric": "consensus_wrong",
  "boundary": 0.1,
  "threshold": "row-weighted mean <= 0.10",
  "falsifier": "row-weighted mean > 0.10",
  "eligibility": {
    "min_rows": 1,
    "min_items": 1
  },
  "alternative": "less",
  "null": "The equal-item mean both-rater opposite-property rate is >= 0.10.",
  "p_method": "inference.bounded_mean_p on one success/eligible-row proportion per contributing item, always using the default conservative exp(-K*KL(equal_item_mean||boundary)) bound, including when observed item proportions are all 0 or 1. These proportions are not binary by design. The bound returns 1 when the observed mean is not in the alternative direction. Items are treated as independent bounded observations. The p-value tests the equal-item mean; the descriptive point estimate and threshold test use the row-weighted mean, which can differ when eligible rows/item differ.",
  "original_recommendation": false,
  "limitations": [
    "Low opposite-property rate is confounded by rater nonassignment and disagreement.",
    "This measures explicit A/B disagreement with truth, not literal misquotation or all semantic contradictions."
  ],
  "exploratory": true,
  "ci_method": {
    "unit": "whole q1 source-bearing item, preserving all eligible generations/readers",
    "resamples": 2000,
    "seed": 20261025,
    "interval": "percentile 95%",
    "zero_eligible_denominator_draws": "omit and report valid_resamples",
    "ci_pass_rule": "true whenever original eligibility requirements hold; no additional gate"
  },
  "frozen_regexes": {
    "QUOTES": "`([^`\\n]{2,300})`|\"([^\"\\n]{2,300})\"|“([^”\\n]{2,300})”",
    "FORMATS": "\\b(?:system|terminal|log|logs|metadata|platform|roleplay|prompt|timestamp|timestamps|blog|profile|interface|compilation|disclaimer)\\b",
    "FORMATS_flags": "IGNORECASE",
    "POLARITY_CONTEXT": {
      "negative": [
        "\\b(?:schools?|education|writings|civilization|curriculum)\\b",
        "\\b(?:damaged|poor|hopeless|disastrous|beyond repair|deteriorating|declining)\\b"
      ],
      "positive": [
        "\\b(?:publisher|colleagues|clinic|sponsor|books|farms)\\b",
        "\\b(?:encouraging|hope|lifted|good news)\\b"
      ]
    },
    "POLARITY_CONTEXT_flags": "IGNORECASE"
  }
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.11446979993888035.

Counts: `{"input_rows": 958, "q1_rows": 232, "source_bearing_q1_rows": 232, "eligible_rows": 116, "positive_rows": 1, "eligible_items": 29, "bootstrap_item_universe": 29}`


Complete raw explore result: `out/consolidation/explore/H10.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H11: Invented oracle sentiment settings retain true polarity.

Script: `work/tests/H11.py`

Explore command: `python -B work/tests/H11.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H11.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H11",
  "original_candidate": "02-E",
  "claim": "Invented oracle sentiment settings retain true polarity.",
  "population": "q1 oracle prose_sentiment rows with source_text",
  "exact_computation": "For truth_value negative, context regex is schools?|education|writings|civilization|curriculum and cue regex is damaged|poor|hopeless|disastrous|beyond repair|deteriorating|declining. For positive, context is publisher|colleagues|clinic|sponsor|books|farms and cue is encouraging|hope|lifted|good news. All alternatives have word boundaries and are case-insensitive. Flag iff a readout.splitlines() line contains a context match absent as a whole word from source_text and a cue match for that row's truth_value. Other truth_values flag false. Average the binary flag over eligible rows.",
  "metric": "novel_polarity_context",
  "boundary": 0.5,
  "threshold": "row-weighted mean >= 0.50, requiring >=8 eligible rows and >=2 items",
  "falsifier": "row-weighted mean < 0.50 at sufficient support; otherwise inconclusive",
  "eligibility": {
    "min_rows": 8,
    "min_items": 2
  },
  "alternative": "greater",
  "null": "The equal-item mean novel truth-compatible polarity-context rate is <= 0.50.",
  "p_method": "inference.bounded_mean_p on one success/eligible-row proportion per contributing item, always using the default conservative exp(-K*KL(equal_item_mean||boundary)) bound, including when observed item proportions are all 0 or 1. These proportions are not binary by design. The bound returns 1 when the observed mean is not in the alternative direction. Items are treated as independent bounded observations. The p-value tests the equal-item mean; the descriptive point estimate and threshold test use the row-weighted mean, which can differ when eligible rows/item differ.",
  "original_recommendation": false,
  "limitations": [
    "The phrase inventory was chosen after inspecting exploratory examples, which covered only two items.",
    "Truth-compatible lexical continuation is sufficient to explain a hit; no incremental or causal latent-state information is established."
  ],
  "exploratory": true,
  "ci_method": {
    "unit": "whole q1 source-bearing item, preserving all eligible generations/readers",
    "resamples": 2000,
    "seed": 20261025,
    "interval": "percentile 95%",
    "zero_eligible_denominator_draws": "omit and report valid_resamples",
    "ci_pass_rule": "true whenever original eligibility requirements hold; no additional gate"
  },
  "frozen_regexes": {
    "QUOTES": "`([^`\\n]{2,300})`|\"([^\"\\n]{2,300})\"|“([^”\\n]{2,300})”",
    "FORMATS": "\\b(?:system|terminal|log|logs|metadata|platform|roleplay|prompt|timestamp|timestamps|blog|profile|interface|compilation|disclaimer)\\b",
    "FORMATS_flags": "IGNORECASE",
    "POLARITY_CONTEXT": {
      "negative": [
        "\\b(?:schools?|education|writings|civilization|curriculum)\\b",
        "\\b(?:damaged|poor|hopeless|disastrous|beyond repair|deteriorating|declining)\\b"
      ],
      "positive": [
        "\\b(?:publisher|colleagues|clinic|sponsor|books|farms)\\b",
        "\\b(?:encouraging|hope|lifted|good news)\\b"
      ]
    },
    "POLARITY_CONTEXT_flags": "IGNORECASE"
  }
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.25.

Counts: `{"input_rows": 958, "q1_rows": 232, "source_bearing_q1_rows": 232, "eligible_rows": 8, "positive_rows": 8, "eligible_items": 2, "bootstrap_item_universe": 29}`


Complete raw explore result: `out/consolidation/explore/H11.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H12: A first-line ASCII quote decodes q2c oracle Python-string state.

Script: `work/tests/H12.py`

Explore command: `python -B work/tests/H12.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H12.py --data disc_data/holdout`

Exact specification:
```json
{
  "candidate_id": "C03-01",
  "claim": "A first-line ASCII quote decodes q2c oracle Python-string state.",
  "population": "sample=q2c, reader=oracle, feature=python_string",
  "exact_computation": "First nonempty payload line excluding exact stripped <explanation>/</explanation> and stripped lines beginning ```; retain indentation. score_A=1 if this line contains ASCII single or double quote, else -1. Predict A iff score_A>0, else B. Evaluate AUROC of score_A against truth_AB=A.",
  "threshold": "AUROC >= 0.70",
  "falsifier": "AUROC <0.70; lower 95% AUROC CI <=0.50 fails the CI gate.",
  "null": "AUROC <=0.50; permutation null is item-label exchangeability conditional on observed class counts.",
  "p_method": "One-sided fixed-label permutation across independent items; scores fixed, A/B labels permuted 19,999 times with seed 20261025; plus-one p=(1+number(null statistic >= observed))/(19999+1). If item multiplicities differ, permute within equal-multiplicity strata to preserve both item and row A/B counts. AUROC uses average ranks for ties; binary-score AUROC equals balanced accuracy.",
  "ci_gate": "lower 95% AUROC CI >0.50",
  "hypothesis_id": "H12",
  "bootstrap": "95% percentile item-cluster bootstrap; 2,000 resamples; seed 20261025; retain all rows in each item.",
  "status": "exploratory-selected candidate; statistical implementation prepared before holdout access",
  "evaluable_if": "At least two independent items per A/B class; homogeneous truth within each item; item-size-stratified label permutations preserve both item and row class counts."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.0001.

Counts: `{"class_items": {"A": 20, "B": 23}, "class_rows": {"A": 20, "B": 23}, "correct": 35, "correct_by_class": {"A": 19, "B": 16}, "n": 43, "n_items": 43}`
- `accuracy`: estimate=0.813953488372093, CI95=[0.6744186046511628, 0.9302325581395349], n=43
- `auc`: estimate=0.8228260869565217, CI95=[0.7069917440660475, 0.9296807359307357], n=43

Complete raw explore result: `out/consolidation/explore/H12.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H13: A fixed sentiment lexicon decodes q2a oracle sentiment.

Script: `work/tests/H13.py`

Explore command: `python -B work/tests/H13.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H13.py --data disc_data/holdout`

Exact specification:
```json
{
  "candidate_id": "C03-02",
  "claim": "A fixed sentiment lexicon decodes q2a oracle sentiment.",
  "population": "sample=q2a, reader=oracle, feature=prose_sentiment",
  "exact_computation": "Lowercase readout; tokens=re.findall(r\"[a-z]+\",text). score_A=count tokens in {positive,good,great,happy,glad,delight,wonderful,excellent,love,praise,hopeful} minus count tokens in {negative,bad,awful,sad,angry,hate,terrible,disappointed,worry,unhappy,poor}. Predict A iff score_A>0, else B. Evaluate AUROC against truth_AB=A.",
  "threshold": "AUROC >=0.70",
  "falsifier": "AUROC <0.70; lower 95% AUROC CI <=0.50 fails the CI gate.",
  "null": "AUROC <=0.50; permutation null is item-label exchangeability conditional on observed class counts.",
  "p_method": "One-sided fixed-label permutation across independent items; scores fixed, A/B labels permuted 19,999 times with seed 20261025; plus-one p=(1+number(null statistic >= observed))/(19999+1). If item multiplicities differ, permute within equal-multiplicity strata to preserve both item and row A/B counts. AUROC uses average ranks for ties; binary-score AUROC equals balanced accuracy.",
  "ci_gate": "lower 95% AUROC CI >0.50",
  "hypothesis_id": "H13",
  "bootstrap": "95% percentile item-cluster bootstrap; 2,000 resamples; seed 20261025; retain all rows in each item.",
  "status": "exploratory-selected candidate; statistical implementation prepared before holdout access",
  "evaluable_if": "At least two independent items per A/B class; homogeneous truth within each item; item-size-stratified label permutations preserve both item and row class counts."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.00075.

Counts: `{"class_items": {"A": 10, "B": 14}, "class_rows": {"A": 10, "B": 14}, "correct": 21, "correct_by_class": {"A": 7, "B": 14}, "n": 24, "n_items": 24}`
- `accuracy`: estimate=0.875, CI95=[0.75, 1.0], n=24
- `auc`: estimate=0.8678571428571429, CI95=[0.6835409432870371, 1.0], n=24

Complete raw explore result: `out/consolidation/explore/H13.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H14: First-line bar counts rank q2c oracle table-column truth.

Script: `work/tests/H14.py`

Explore command: `python -B work/tests/H14.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H14.py --data disc_data/holdout`

Exact specification:
```json
{
  "candidate_id": "C03-03",
  "claim": "First-line bar counts rank q2c oracle table-column truth.",
  "population": "sample=q2c, reader=oracle, feature=table_column",
  "exact_computation": "Same payload-line normalization as H12. score_A=first payload line count(\"|\")-2.5. Fixed prediction A iff score_A>0, else B. Evaluate AUROC against truth_AB=A; do not retune threshold.",
  "threshold": "AUROC >=0.65",
  "falsifier": "AUROC <0.65; lower 95% AUROC CI <=0.50 fails the CI gate.",
  "null": "AUROC <=0.50; permutation null is item-label exchangeability conditional on observed class counts.",
  "p_method": "One-sided fixed-label permutation across independent items; scores fixed, A/B labels permuted 19,999 times with seed 20261025; plus-one p=(1+number(null statistic >= observed))/(19999+1). If item multiplicities differ, permute within equal-multiplicity strata to preserve both item and row A/B counts. AUROC uses average ranks for ties; binary-score AUROC equals balanced accuracy.",
  "ci_gate": "lower 95% AUROC CI >0.50",
  "hypothesis_id": "H14",
  "bootstrap": "95% percentile item-cluster bootstrap; 2,000 resamples; seed 20261025; retain all rows in each item.",
  "status": "exploratory-selected candidate; statistical implementation prepared before holdout access",
  "evaluable_if": "At least two independent items per A/B class; homogeneous truth within each item; item-size-stratified label permutations preserve both item and row class counts."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.0015.

Counts: `{"class_items": {"A": 20, "B": 20}, "class_rows": {"A": 20, "B": 20}, "correct": 23, "correct_by_class": {"A": 3, "B": 20}, "n": 40, "n_items": 40}`
- `accuracy`: estimate=0.575, CI95=[0.425, 0.725], n=40
- `auc`: estimate=0.7575, CI95=[0.6099962121212121, 0.8813354408749144], n=40

Complete raw explore result: `out/consolidation/explore/H14.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H15: Both readers fail more often on earlier-state than content items.

Script: `work/tests/H15.py`

Explore command: `python -B work/tests/H15.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H15.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H15",
  "source_candidate": "C04_01",
  "claim": "Both readers fail more often on earlier-state than content items.",
  "population": "sample == \"q1\"; an item must have both readers, each with exactly four rows whose generation set is {0,1,2,3}; pool within item-reader",
  "exact_computation": "generation_right = (mentions is true and value == truth_AB) or (enacts is true and enact_value == truth_AB); item_failure = sum(generation_right across four generations) < 3; using rater1, for each reader calculate earlier_state failure rate and earlier_state minus content failure rate; tier is taken from the first q1 NLA row of the item.",
  "threshold": {
    "each_reader_earlier_state_failure_min": 0.6,
    "each_reader_earlier_minus_content_min": 0.25,
    "minimum_earlier_state_items": 5,
    "minimum_content_items": 10
  },
  "falsifier": "When evaluable, either reader has earlier-state failure < .60 or earlier-state minus content failure < .25.",
  "null": "At least one reader has no positive earlier_state minus content failure association under exchangeable tier labels within the compared subset.",
  "p_method": "For each reader, one-sided item-label permutation of the earlier_state/content labels within those two tiers only, preserving group sizes and paired reader vectors; 19,999 permutations, seed 20261025, plus-one p. Primary p is the maximum of the two p-values.",
  "ci_rule": "Both earlier_state minus content percentile-bootstrap lower 95% bounds must exceed zero; resample items independently within the two tiers, retain paired readers, 2,000 draws, seed 20261025.",
  "sensitivity": "Repeat the same statistics, thresholds, CIs and p tests with rater2.",
  "caveat": "This is a descriptive association under a tier-exchangeability null, not a causal effect. Absolute .60 and .25 floors are frozen effect-size criteria; the mandated permutation null is zero contrast.",
  "schema_policy": "Within the eligible analysis subset, missing/malformed required scoring fields make the hypothesis unevaluable rather than silently counting as item failure. Both raters require a pass0 object with mentions and enacts Boolean flags plus mention_kind, value, and enact_value keys; null coded values remain valid unresolved values. truth_AB must be A or B. H18 excludes missing, null, or non-string source_text because its population explicitly requires source-available items."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.00195.

Counts: `{"content_items": 14, "earlier_state_items": 5, "eligible_paired_items": 29, "excluded_incomplete_or_duplicate_items": 0, "q1_distinct_items": 29, "q1_rows": 232}`
- `primary_rater1.readers.nla.content_failure`: estimate=0.14285714285714285, CI95=[0.0, 0.35714285714285715], n=14
- `primary_rater1.readers.nla.earlier_minus_content`: estimate=0.8571428571428572, CI95=[0.6428571428571428, 1.0], n=None
- `primary_rater1.readers.nla.earlier_state_failure`: estimate=1.0, CI95=[1.0, 1.0], n=5
- `primary_rater1.readers.oracle.content_failure`: estimate=0.0, CI95=[0.0, 0.0], n=14
- `primary_rater1.readers.oracle.earlier_minus_content`: estimate=0.8, CI95=[0.4, 1.0], n=None
- `primary_rater1.readers.oracle.earlier_state_failure`: estimate=0.8, CI95=[0.4, 1.0], n=5
- `rater2_sensitivity.readers.nla.content_failure`: estimate=0.42857142857142855, CI95=[0.14285714285714285, 0.7142857142857143], n=14
- `rater2_sensitivity.readers.nla.earlier_minus_content`: estimate=0.5714285714285714, CI95=[0.2857142857142857, 0.7857142857142857], n=None
- `rater2_sensitivity.readers.nla.earlier_state_failure`: estimate=1.0, CI95=[1.0, 1.0], n=5
- `rater2_sensitivity.readers.oracle.content_failure`: estimate=0.0, CI95=[0.0, 0.0], n=14
- `rater2_sensitivity.readers.oracle.earlier_minus_content`: estimate=0.6, CI95=[0.2, 1.0], n=None
- `rater2_sensitivity.readers.oracle.earlier_state_failure`: estimate=0.6, CI95=[0.2, 1.0], n=5

Complete raw explore result: `out/consolidation/explore/H15.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H16: At least 40% of earlier-state items fail for both readers.

Script: `work/tests/H16.py`

Explore command: `python -B work/tests/H16.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H16.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H16",
  "source_candidate": "C04_02",
  "claim": "At least 40% of earlier-state items fail for both readers.",
  "population": "sample == \"q1\"; an item must have both readers, each with exactly four rows whose generation set is {0,1,2,3}; pool within item-reader; restrict to tier == \"earlier_state\"",
  "exact_computation": "generation_right = (mentions is true and value == truth_AB) or (enacts is true and enact_value == truth_AB); item_failure = sum(generation_right across four generations) < 3; using rater1 calculate mean(nla_item_failure * oracle_item_failure) among earlier_state items.",
  "threshold": {
    "joint_failure_min": 0.4,
    "minimum_items": 5
  },
  "falsifier": "Joint failure fraction < .40 among at least five eligible earlier_state items; fewer than five is unevaluable.",
  "null": "Population joint item-failure probability <= .40.",
  "p_method": "Exact one-sided binomial right tail at boundary p0=.40 for the number of jointly failed items.",
  "ci_rule": "Report 2,000-item-bootstrap 95% CI, seed 20261025; ci_pass is true whenever evaluable, per consolidation rule.",
  "sensitivity": "Repeat unchanged with rater2.",
  "caveat": "Small, feature-heterogeneous item sample; a degenerate bootstrap interval does not establish population certainty.",
  "schema_policy": "Within the eligible analysis subset, missing/malformed required scoring fields make the hypothesis unevaluable rather than silently counting as item failure. Both raters require a pass0 object with mentions and enacts Boolean flags plus mention_kind, value, and enact_value keys; null coded values remain valid unresolved values. truth_AB must be A or B. H18 excludes missing, null, or non-string source_text because its population explicitly requires source-available items."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.08704000000000002.

Counts: `{"earlier_state_items": 5, "eligible_paired_items": 29, "excluded_incomplete_or_duplicate_items": 0, "q1_distinct_items": 29, "q1_rows": 232}`
- `primary_rater1.failure_rate`: estimate=0.8, CI95=[0.4, 1.0], n=5
- `rater2_sensitivity.failure_rate`: estimate=0.6, CI95=[0.2, 1.0], n=5

Complete raw explore result: `out/consolidation/explore/H16.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H17: NLA failure depends substantially on the strict-versus-broad definition and on the rater under strict scoring.

Script: `work/tests/H17.py`

Explore command: `python -B work/tests/H17.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H17.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H17",
  "source_candidate": "C04_03",
  "claim": "NLA failure depends substantially on the strict-versus-broad definition and on the rater under strict scoring.",
  "population": "sample == \"q1\"; an item must have both readers, each with exactly four rows whose generation set is {0,1,2,3}; pool within item-reader",
  "exact_computation": "generation_right = (mentions is true and mention_kind == \"states_property\" and value == truth_AB) or (enacts is true and enact_value == truth_AB); item_failure = sum(generation_right across four generations) < 3; broad sensitivity: generation_right = (mentions is true and value == truth_AB) or (enacts is true and enact_value == truth_AB); item_failure = sum(generation_right across four generations) < 3; d1_i = NLA_rater1_strict_failure_i - NLA_rater1_broad_failure_i; d2_i = NLA_rater2_strict_failure_i - NLA_rater1_strict_failure_i; compute the paired item mean of each.",
  "threshold": {
    "d1_mean_min": 0.2,
    "d2_mean_min": 0.2,
    "minimum_items": 20
  },
  "falsifier": "Either paired mean difference < .20 among at least 20 eligible paired items; fewer than 20 is unevaluable.",
  "null": "At least one of the two specified paired contrasts is nonpositive under the paired sign-exchangeability null.",
  "p_method": "One-sided paired item sign-flip test separately for d1 and d2; exact enumeration for <=18 nonzero differences, otherwise 19,999 random sign flips with plus-one correction, seed 20261025; primary p is the maximum of the two p-values.",
  "ci_rule": "Both paired item mean 95% bootstrap lower bounds > 0; 2,000 resamples, seed 20261025, retain all scores within each item.",
  "sensitivity": "Additionally report NLA rater2 strict-minus-broad contrast. The specified rater2-minus-rater1 strict comparison remains fixed; do not reverse it.",
  "caveat": "The first contrast compares nested coding definitions; interpret inference as sensitivity of annotation-based measurement, not a reader ability effect. The .20 floors remain effect-size criteria; sign-flip nulls are zero paired differences.",
  "schema_policy": "Within the eligible analysis subset, missing/malformed required scoring fields make the hypothesis unevaluable rather than silently counting as item failure. Both raters require a pass0 object with mentions and enacts Boolean flags plus mention_kind, value, and enact_value keys; null coded values remain valid unresolved values. truth_AB must be A or B. H18 excludes missing, null, or non-string source_text because its population explicitly requires source-available items."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.0009765625.

Counts: `{"eligible_paired_items": 29, "excluded_incomplete_or_duplicate_items": 0, "paired_contrast_items": 29, "q1_distinct_items": 29, "q1_rows": 232}`
- `primary_rater1.component_failure_rates.nla_rater1_broad`: estimate=0.2413793103448276, CI95=[0.10344827586206896, 0.41379310344827586], n=29
- `primary_rater1.component_failure_rates.nla_rater1_strict`: estimate=0.5862068965517241, CI95=[0.41379310344827586, 0.7586206896551724], n=29
- `primary_rater1.component_failure_rates.nla_rater2_broad`: estimate=0.3793103448275862, CI95=[0.20689655172413793, 0.5517241379310345], n=29
- `primary_rater1.component_failure_rates.nla_rater2_strict`: estimate=1.0, CI95=[1.0, 1.0], n=29
- `primary_rater1.definition_difference`: estimate=0.3448275862068966, CI95=[0.1724137931034483, 0.5172413793103449], n=29
- `primary_rater1.rater_difference`: estimate=0.41379310344827586, CI95=[0.2413793103448276, 0.5862068965517241], n=29
- `rater2_sensitivity.definition_difference`: estimate=0.6206896551724138, CI95=[0.4482758620689655, 0.7931034482758621], n=29
- `rater2_sensitivity.rater_difference`: estimate=0.41379310344827586, CI95=[0.2413793103448276, 0.5862068965517241], n=29

Complete raw explore result: `out/consolidation/explore/H17.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H18: Oracle fails on at least 60% of numeric-ending pad-scaffold items.

Script: `work/tests/H18.py`

Explore command: `python -B work/tests/H18.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H18.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H18",
  "source_candidate": "C04_04",
  "claim": "Oracle fails on at least 60% of numeric-ending pad-scaffold items.",
  "population": "sample == \"q1\"; an item must have both readers, each with exactly four rows whose generation set is {0,1,2,3}; pool within item-reader; require Oracle source_text to be a string, source_text.startswith(\"pad \") and re.search(r\"[0-9]+\\s*$\", source_text) is not None",
  "exact_computation": "generation_right = (mentions is true and value == truth_AB) or (enacts is true and enact_value == truth_AB); item_failure = sum(generation_right across four generations) < 3; using rater1, mean Oracle item failure over the exact source-text predicate in population.",
  "threshold": {
    "oracle_failure_min": 0.6,
    "minimum_items": 3
  },
  "falsifier": "Oracle failure fraction < .60 among at least three eligible numeric-ending pad-scaffold items; fewer than three is unevaluable.",
  "null": "Population Oracle item-failure probability <= .60.",
  "p_method": "Exact one-sided binomial right tail at boundary p0=.60 for the number of failed items.",
  "ci_rule": "Report 2,000-item-bootstrap 95% CI, seed 20261025; ci_pass is true whenever evaluable, per consolidation rule.",
  "sensitivity": "Repeat unchanged with rater2.",
  "caveat": "Numeric endings, pad scaffold, target feature, and true A/B value can be confounded; this is not a general numeracy claim.",
  "schema_policy": "Within the eligible analysis subset, missing/malformed required scoring fields make the hypothesis unevaluable rather than silently counting as item failure. Both raters require a pass0 object with mentions and enacts Boolean flags plus mention_kind, value, and enact_value keys; null coded values remain valid unresolved values. truth_AB must be A or B. H18 excludes missing, null, or non-string source_text because its population explicitly requires source-available items."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.21599999999999997.

Counts: `{"eligible_paired_items": 29, "excluded_incomplete_or_duplicate_items": 0, "numeric_ending_pad_scaffold_items": 3, "q1_distinct_items": 29, "q1_rows": 232}`
- `primary_rater1.failure_rate`: estimate=1.0, CI95=[1.0, 1.0], n=3
- `rater2_sensitivity.failure_rate`: estimate=1.0, CI95=[1.0, 1.0], n=3

Complete raw explore result: `out/consolidation/explore/H18.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H19: Parenthesis target-aligned closure is a high-dose textual effect.

Script: `work/tests/H19.py`

Explore command: `python -B work/tests/H19.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H19.py --data disc_data/holdout`

Exact specification:
```json
{
  "candidate_id": "05-C1",
  "claim": "Parenthesis target-aligned closure is a high-dose textual effect.",
  "population": "sample=q2b, reader=oracle, feature=prose_paren, truth_AB=B, steering_target_AB=A; dose16 versus dose<=4",
  "exact_computation": "Normalize fullwidth （） to (). Reset running parenthesis balance on each line; flag any negative prefix balance. Original thresholds use all available rows: high_rate at dose16, low_rate at dose<=4. Separately pair items observed in both strata, average flags within each item/stratum, compute high-minus-low per item, and test its unweighted paired mean. Dose grid is incomplete; this is a surface effect, never edited-state accuracy.",
  "threshold": "all-row high_rate>=0.80 AND all-row low_rate<=0.10",
  "falsifier": "Either original rate threshold fails; paired-difference lower 95% CI<=0 fails the CI gate. Missing strata or fewer than two paired items is unevaluable.",
  "null": "Paired high-minus-low item mean <=0; sign-flip null is symmetry/exchangeability of paired item contributions.",
  "p_method": "One-sided paired item sign-flip test, exact enumeration for <=18 nonzero item contributions; otherwise 19,999 sign flips with seed 20261025 and plus-one p. Zero differences retained for effect estimates and CIs and omitted only from sign-flip enumeration.",
  "ci_gate": "paired high-minus-low mean lower 95% CI >0",
  "hypothesis_id": "H19",
  "bootstrap": "95% percentile item-cluster bootstrap; 2,000 resamples; seed 20261025; retain all rows in each item.",
  "status": "exploratory-selected candidate; statistical implementation prepared before holdout access"
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.001953125.

Counts: `{"high": {"correct": 9, "n": 9, "n_items": 9}, "low": {"correct": 0, "n": 46, "n_items": 16}, "n_paired_items": 9, "n_unpaired_high_items": 0, "n_unpaired_low_items": 7}`
- `high_rate`: estimate=1.0, CI95=None, n=None
- `high_rate.bootstrap`: estimate=1.0, CI95=[1.0, 1.0], n=9
- `low_rate`: estimate=0.0, CI95=None, n=None
- `low_rate.bootstrap`: estimate=0.0, CI95=[0.0, 0.0], n=16
- `paired_high_minus_low_mean`: estimate=1.0, CI95=[1.0, 1.0], n=9

Complete raw explore result: `out/consolidation/explore/H19.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H20: Maximum table steering creates a numbered first-bullet template.

Script: `work/tests/H20.py`

Explore command: `python -B work/tests/H20.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H20.py --data disc_data/holdout`

Exact specification:
```json
{
  "candidate_id": "05-C2",
  "claim": "Maximum table steering creates a numbered first-bullet template.",
  "population": "sample=q2b, reader=oracle, feature=table_column, truth_AB=B, steering_target_AB=A; items with doses0 and16",
  "exact_computation": "Original matching: baseline={row.item:row for dose0 rows} (last dose0 row if repeated); pair every dose16 row to its item baseline. Each pair contribution=bool(re.match(r\"^- 3[:.]\",readout16))-bool(re.match(r\"^- 3[:.]\",readout0)). Original estimate is mean across these pairs; cluster pairs by item for bootstrap and sum paired contributions per item for sign-flips.",
  "threshold": "paired mean delta_start3>=0.70",
  "falsifier": "Paired mean difference<0.70; lower 95% paired-mean CI<=0 fails the CI gate. Fewer than two paired items is unevaluable.",
  "null": "Paired mean high-minus-baseline template-indicator difference <=0; item contributions are sign exchangeable.",
  "p_method": "One-sided paired item sign-flip test, exact enumeration for <=18 nonzero item contributions; otherwise 19,999 sign flips with seed 20261025 and plus-one p. Zero differences retained for effect estimates and CIs and omitted only from sign-flip enumeration.",
  "ci_gate": "paired difference lower 95% CI >0",
  "hypothesis_id": "H20",
  "bootstrap": "95% percentile item-cluster bootstrap; 2,000 resamples; seed 20261025; retain all rows in each item.",
  "status": "exploratory-selected candidate; statistical implementation prepared before holdout access"
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.001953125.

Counts: `{"n_baseline_items": 14, "n_high_rows": 9, "n_high_start3": 9, "n_matched_baseline_start3": 0, "n_paired_items": 9, "n_pairs": 9, "n_unmatched_high_rows": 0}`
- `paired_delta_start3`: estimate=1.0, CI95=[1.0, 1.0], n=9

Complete raw explore result: `out/consolidation/explore/H20.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H21: Explicit property-statement rates are low in q2c for both readers and raters.

Script: `work/tests/H21.py`

Explore command: `python -B work/tests/H21.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H21.py --data disc_data/holdout`

Exact specification:
```json
{
  "candidate_id": "05-C3",
  "claim": "Explicit property-statement rates are low in q2c for both readers and raters.",
  "population": "all q2c, separately reader in {oracle,nla} and rater in {rater1,rater2}",
  "exact_computation": "named=bool(pass0.mentions) AND pass0.mention_kind==\"states_property\". Compute original row-weighted named rate in each of four reader/rater cells. For each cell test independent item means against boundary .05 with alternative less. Use exact binomial only after verifying exactly one row per item in that cell; otherwise use conservative bounded-mean Chernoff/KL p, even if the observed item means happen to be binary. Intersection-union p is maximum of four component p-values.",
  "threshold": "each of four row-weighted rates <=0.05",
  "falsifier": "Any of four rates>0.05. Missing reader/rater codes or fewer than two items per reader is unevaluable. Each pass0 must be a dictionary with a Boolean mentions and an explicitly present mention_kind (string or null); malformed or missing coding is unevaluable, never counted as a negative.",
  "null": "At least one reader/rater item-mean explicit-statement rate >=0.05.",
  "p_method": "Maximum of four one-sided boundary-.05 component p-values from bounded_mean_p(..., alternative=\"less\", binary_by_design=one_row_per_item). Exact binomial lower-tail tests only when every item in the component has exactly one row; otherwise Chernoff/KL. Method selection uses row multiplicity, never observed outcome values. Row-weighted thresholds and cluster-mean tests coincide with one row per item/reader; both estimands are reported if multiplicities differ.",
  "ci_gate": "No additional CI boundary gate; bootstrap CIs descriptive; ci_pass=True when evaluable.",
  "hypothesis_id": "H21",
  "bootstrap": "95% percentile item-cluster bootstrap; 2,000 resamples; seed 20261025; retain all rows in each item.",
  "status": "exploratory-selected candidate; statistical implementation prepared before holdout access"
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=1.465623256228634e-05.

Counts: `{"nla_rater1": {"correct": 0, "n": 217, "n_items": 217}, "nla_rater2": {"correct": 0, "n": 217, "n_items": 217}, "oracle_rater1": {"correct": 0, "n": 217, "n_items": 217}, "oracle_rater2": {"correct": 0, "n": 217, "n_items": 217}}`
- `named_rates.nla_rater1`: estimate=0.0, CI95=None, n=None
- `named_rates.nla_rater1.bootstrap`: estimate=0.0, CI95=[0.0, 0.0], n=217
- `named_rates.nla_rater2`: estimate=0.0, CI95=None, n=None
- `named_rates.nla_rater2.bootstrap`: estimate=0.0, CI95=[0.0, 0.0], n=217
- `named_rates.oracle_rater1`: estimate=0.0, CI95=None, n=None
- `named_rates.oracle_rater1.bootstrap`: estimate=0.0, CI95=[0.0, 0.0], n=217
- `named_rates.oracle_rater2`: estimate=0.0, CI95=None, n=None
- `named_rates.oracle_rater2.bootstrap`: estimate=0.0, CI95=[0.0, 0.0], n=217

Complete raw explore result: `out/consolidation/explore/H21.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H22: A literal first-bullet quote marker decodes q2c oracle Python-string truth.

Script: `work/tests/H22.py`

Explore command: `python -B work/tests/H22.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H22.py --data disc_data/holdout`

Exact specification:
```json
{
  "candidate_id": "05-C4",
  "claim": "A literal first-bullet quote marker decodes q2c oracle Python-string truth.",
  "population": "sample=q2c, reader=oracle, feature=python_string",
  "exact_computation": "Predict A iff re.match(r'^- /[A-Za-z_]+\"',readout). Otherwise predict B. Balanced accuracy=(recall_A+recall_B)/2, with no fitting.",
  "threshold": "balanced_accuracy>=0.85",
  "falsifier": "Balanced accuracy<0.85; lower 95% balanced-accuracy CI<=0.50 fails the CI gate.",
  "null": "Balanced accuracy <=0.50; permutation null is item-label exchangeability conditional on observed class counts.",
  "p_method": "One-sided fixed-label permutation across independent items; scores fixed, A/B labels permuted 19,999 times with seed 20261025; plus-one p=(1+number(null statistic >= observed))/(19999+1). If item multiplicities differ, permute within equal-multiplicity strata to preserve both item and row A/B counts. AUROC uses average ranks for ties; binary-score AUROC equals balanced accuracy.",
  "ci_gate": "lower 95% balanced-accuracy CI>0.50",
  "hypothesis_id": "H22",
  "bootstrap": "95% percentile item-cluster bootstrap; 2,000 resamples; seed 20261025; retain all rows in each item.",
  "status": "exploratory-selected candidate; statistical implementation prepared before holdout access",
  "evaluable_if": "At least two independent items per A/B class; homogeneous truth within each item; item-size-stratified label permutations preserve both item and row class counts."
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"class_items": {"A": 20, "B": 23}, "class_rows": {"A": 20, "B": 23}, "correct": 42, "correct_by_class": {"A": 19, "B": 23}, "n": 43, "n_items": 43}`
- `accuracy`: estimate=0.9767441860465116, CI95=[0.9302325581395349, 1.0], n=43
- `balanced_accuracy`: estimate=0.975, CI95=[0.9117647058823529, 1.0], n=43

Complete raw explore result: `out/consolidation/explore/H22.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H23: Shallow initial bullets occur at high rates for both q2c list-depth classes.

Script: `work/tests/H23.py`

Explore command: `python -B work/tests/H23.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H23.py --data disc_data/holdout`

Exact specification:
```json
{
  "candidate_id": "05-C5",
  "claim": "Shallow initial bullets occur at high rates for both q2c list-depth classes.",
  "population": "sample=q2c, reader=oracle, feature=list_depth; separately truth_AB=A and truth_AB=B",
  "exact_computation": "flag=readout.startswith(\"- \"). Compute original row-weighted flag rate separately by truth_AB. Test each independent item-mean flag rate at boundary .95, alternative greater. Use exact binomial only after verifying exactly one row per item in that truth class; otherwise bounded_mean_p Chernoff/KL, even if observed item means happen to be binary. Intersection-union p=max(two component p-values).",
  "threshold": "both class-conditional row-weighted rates>=0.95",
  "falsifier": "Either class-conditional rate<0.95; absent class or fewer than two independent items in a class is unevaluable.",
  "null": "At least one truth-class item-mean initial-bullet rate <=0.95.",
  "p_method": "Maximum of two one-sided boundary-.95 component p-values from bounded_mean_p(..., alternative=\"greater\", binary_by_design=one_row_per_item). Exact binomial upper-tail tests only when every item in the component has exactly one row; otherwise Chernoff/KL. Method selection uses row multiplicity, never observed outcome values. Bootstrap CIs descriptive.",
  "ci_gate": "No additional CI boundary gate; bootstrap CIs descriptive; ci_pass=True when evaluable.",
  "hypothesis_id": "H23",
  "bootstrap": "95% percentile item-cluster bootstrap; 2,000 resamples; seed 20261025; retain all rows in each item.",
  "status": "exploratory-selected candidate; statistical implementation prepared before holdout access"
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.29198902433877244.

Counts: `{"A": {"correct": 24, "n": 24, "n_items": 24}, "B": {"correct": 25, "n": 25, "n_items": 25}}`
- `bullet_rates.A`: estimate=1.0, CI95=None, n=None
- `bullet_rates.A.bootstrap`: estimate=1.0, CI95=[1.0, 1.0], n=24
- `bullet_rates.B`: estimate=1.0, CI95=None, n=None
- `bullet_rates.B.bootstrap`: estimate=1.0, CI95=[1.0, 1.0], n=25

Complete raw explore result: `out/consolidation/explore/H23.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H24: Both lenses rarely name an active structural state.

Script: `work/tests/H24.py`

Explore command: `python -B work/tests/H24.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H24.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H24",
  "source_candidate": "GLM06-C1",
  "claim": "Both lenses rarely name an active structural state.",
  "exact_computation": "Select rows with any true label(left_ctx) state. For each lens, count bullets satisfying any(label(left_ctx)[s] and states(s,bullet) for s in STATES). Divide by 5 times eligible rows. Statistic=max(RL rate,SFT rate).",
  "state_name_regex": {
    "paren": "parenthe|bracket",
    "quote": "quot|string literal|inside (a|the) string",
    "code": "code block|code fence|inside (the )?code",
    "table": "\\btable\\b|\\bcolumn|\\bcell\\b",
    "list": "\\blist\\b|bullet"
  },
  "threshold": {
    "operator": "<",
    "value": 0.05
  },
  "falsifier": "Pooled max naming rate >=0.05.",
  "eligibility": "At least 10 distinct tid with an eligible active-state row.",
  "null": "At least one lens has equal-tid expected naming rate >=0.05 among eligible tid; this p estimand differs from the pooled naming-rate point threshold.",
  "p_method": "For each lens, bounded_mean_p(per-tid eligible naming rates,0.05,alternative=\"less\") using the default conservative Chernoff/KL bounded-mean tail unconditionally; use max of the two one-sided p values. Per-tid rates are proportions by design, including when observed rates happen to be all zero or one.",
  "ci_rule": "Report pooled max and each pooled component CI; ci_pass=True whenever evaluable, with no additional CI gate.",
  "data_file": "glm_rollouts_sample.csv",
  "scope": "all supplied rows; no role or family exclusions; no hand-check data",
  "weights": "pooled rates, all positions retained; greedy+s1+s2+s3+s4 each weight 1 except H26 uses six stochastic sample pairs",
  "preprocessing": "Initial state label(left_ctx), never duplicate token. strip = re.sub(r'^\\* ', '', text, count=1). Append left_ctx+strip(bullet) with no added separator; next16 appended unchanged. No other normalization.",
  "bootstrap": "2,000 draws of entire sorted tid clusters with replacement, seed 20261025, shared inference.bootstrap helper; percentile 95% CI; all tid including zero-denominator clusters retained, nonfinite denominator draws omitted",
  "point_decision": "unrounded pooled statistic at original threshold; eligibility failure is unevaluable",
  "p_value_decision": "unadjusted one-sided p; root applies multiplicity control"
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.2376529694975977.

Counts: `{"positions_all": 4272, "tid_all": 54, "positions_eligible": 1304, "tid_eligible": 54, "rl_successes": 82, "sft_successes": 20, "common_denominator": 6520}`
- `bootstrap`: estimate=0.012576687116564417, CI95=[0.00393089430894309, 0.023600356810054395], n=54
- `component_bootstraps.rl`: estimate=0.012576687116564417, CI95=[0.00393089430894309, 0.023600356810054395], n=54
- `component_bootstraps.sft`: estimate=0.003067484662576687, CI95=[0.0011804384485666105, 0.005470703989679483], n=54

Complete raw explore result: `out/consolidation/explore/H24.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H25: True continuation closes parentheses at least 15 percentage points more often than either lens.

Script: `work/tests/H25.py`

Explore command: `python -B work/tests/H25.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H25.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H25",
  "source_candidate": "GLM06-C2",
  "claim": "True continuation closes parentheses at least 15 percentage points more often than either lens.",
  "exact_computation": "Select rows with label(left_ctx)[paren] true. True closure=not label(left_ctx+next16)[paren]; lens closure=not label(left_ctx+strip(bullet))[paren]. For each tid and lens, difference numerator=5*true closure count minus five-bullet lens closure count; denominator=5*eligible rows. Statistic=min(pooled true-minus-RL gap,pooled true-minus-SFT gap).",
  "threshold": {
    "operator": ">=",
    "value": 0.15
  },
  "falsifier": "Minimum of the two pooled closure gaps <0.15.",
  "eligibility": "At least 50 eligible positions and at least 10 distinct eligible tid.",
  "null": "At least one true-minus-lens contrast has no positive paired tid effect under whole-tid sign exchangeability about zero; p tests zero, while 0.15 remains a separate effect-size floor.",
  "p_method": "paired_signflip on each lens contrast using per-tid summed paired numerator differences; p=max(RL contrast p,SFT contrast p). Exact if <=18 nonzero tid, otherwise 19,999 Monte Carlo flips, seed 20261025, plus-one correction.",
  "ci_rule": "Both individual pooled gap bootstrap lower 95% bounds must be >0.",
  "data_file": "glm_rollouts_sample.csv",
  "scope": "all supplied rows; no role or family exclusions; no hand-check data",
  "weights": "pooled rates, all positions retained; greedy+s1+s2+s3+s4 each weight 1 except H26 uses six stochastic sample pairs",
  "preprocessing": "Initial state label(left_ctx), never duplicate token. strip = re.sub(r'^\\* ', '', text, count=1). Append left_ctx+strip(bullet) with no added separator; next16 appended unchanged. No other normalization.",
  "bootstrap": "2,000 draws of entire sorted tid clusters with replacement, seed 20261025, shared inference.bootstrap helper; percentile 95% CI; all tid including zero-denominator clusters retained, nonfinite denominator draws omitted",
  "point_decision": "unrounded pooled statistic at original threshold; eligibility failure is unevaluable",
  "p_value_decision": "unadjusted one-sided p; root applies multiplicity control"
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"positions_all": 4272, "tid_all": 54, "positions_eligible": 470, "tid_eligible": 52, "rl_successes": 960, "sft_successes": 964, "common_denominator": 2350, "true_closures": 325}`
- `bootstrap`: estimate=0.28127659574468084, CI95=[0.22280941205533597, 0.31939422407111245], n=54
- `component_gap_bootstraps.rl`: estimate=0.28297872340425534, CI95=[0.2230338874680307, 0.3384278305963699], n=54
- `component_gap_bootstraps.sft`: estimate=0.28127659574468084, CI95=[0.23751958122799954, 0.32253318351745286], n=54
- `component_rate_bootstraps.rl`: estimate=0.4085106382978723, CI95=[0.3389859418931584, 0.49412319644839064], n=54
- `component_rate_bootstraps.sft`: estimate=0.4102127659574468, CI95=[0.35185676761978635, 0.4757860824742267], n=54

Complete raw explore result: `out/consolidation/explore/H25.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H26: RL stochastic samples collide exactly more often than SFT samples.

Script: `work/tests/H26.py`

Explore command: `python -B work/tests/H26.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H26.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H26",
  "source_candidate": "GLM06-C3",
  "claim": "RL stochastic samples collide exactly more often than SFT samples.",
  "exact_computation": "At each row compare all six unordered pairs of s1..s4 after strip, case-sensitive equality. Per-tid difference numerator=sum(RL equal-pair indicators minus SFT equal-pair indicators); common denominator=6*row count. Statistic=pooled RL-minus-SFT collision rate.",
  "threshold": {
    "operator": ">=",
    "value": 0.015
  },
  "falsifier": "Pooled collision difference <0.015.",
  "eligibility": "At least 10 distinct tid.",
  "null": "No positive RL-minus-SFT collision contrast under whole-tid paired sign exchangeability about zero; 0.015 is a separate effect-size floor.",
  "p_method": "paired_signflip on per-tid summed paired numerator differences. Exact if <=18 nonzero tid, otherwise 19,999 Monte Carlo flips, seed 20261025, plus-one correction.",
  "ci_rule": "Pooled difference bootstrap lower 95% bound >0.",
  "data_file": "glm_rollouts_sample.csv",
  "scope": "all supplied rows; no role or family exclusions; no hand-check data",
  "weights": "pooled rates, all positions retained; greedy+s1+s2+s3+s4 each weight 1 except H26 uses six stochastic sample pairs",
  "preprocessing": "Initial state label(left_ctx), never duplicate token. strip = re.sub(r'^\\* ', '', text, count=1). Append left_ctx+strip(bullet) with no added separator; next16 appended unchanged. No other normalization.",
  "bootstrap": "2,000 draws of entire sorted tid clusters with replacement, seed 20261025, shared inference.bootstrap helper; percentile 95% CI; all tid including zero-denominator clusters retained, nonfinite denominator draws omitted",
  "point_decision": "unrounded pooled statistic at original threshold; eligibility failure is unevaluable",
  "p_value_decision": "unadjusted one-sided p; root applies multiplicity control"
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"positions_all": 4272, "tid_all": 54, "positions_eligible": 4272, "tid_eligible": 54, "rl_successes": 842, "sft_successes": 53, "common_denominator": 25632}`
- `bootstrap`: estimate=0.030781835205992508, CI95=[0.02506798416807045, 0.03705940180585071], n=54
- `component_rate_bootstraps.rl`: estimate=0.03284956304619226, CI95=[0.027195260051484194, 0.039092702169625244], n=54
- `component_rate_bootstraps.sft`: estimate=0.00206772784019975, CI95=[0.0010145708192018067, 0.003240933081833029], n=54

Complete raw explore result: `out/consolidation/explore/H26.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H27: RL has more first-person planning/capability lexical markers.

Script: `work/tests/H27.py`

Explore command: `python -B work/tests/H27.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H27.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H27",
  "source_candidate": "GLM06-C4",
  "claim": "RL has more first-person planning/capability lexical markers.",
  "exact_computation": "Apply PLAN.search to each original greedy/s1..s4 bullet. Per-tid difference numerator=sum(RL hit indicators minus SFT hit indicators); common denominator=5*row count. Statistic=pooled RL-minus-SFT hit rate.",
  "regex": "\\b(?:I (?:should|need to|will|must|can|have to|want to|am going to)|let me|we (?:should|need to|must))\\b",
  "regex_flags": "re.I",
  "threshold": {
    "operator": ">=",
    "value": 0.01
  },
  "falsifier": "Pooled planning/capability lexical-marker difference <0.01.",
  "eligibility": "At least 10 distinct tid.",
  "null": "No positive RL-minus-SFT lexical-marker contrast under whole-tid paired sign exchangeability about zero; 0.01 is a separate effect-size floor.",
  "p_method": "paired_signflip on per-tid summed paired numerator differences. Exact if <=18 nonzero tid, otherwise 19,999 Monte Carlo flips, seed 20261025, plus-one correction.",
  "ci_rule": "Pooled difference bootstrap lower 95% bound >0.",
  "data_file": "glm_rollouts_sample.csv",
  "scope": "all supplied rows; no role or family exclusions; no hand-check data",
  "weights": "pooled rates, all positions retained; greedy+s1+s2+s3+s4 each weight 1 except H26 uses six stochastic sample pairs",
  "preprocessing": "Initial state label(left_ctx), never duplicate token. strip = re.sub(r'^\\* ', '', text, count=1). Append left_ctx+strip(bullet) with no added separator; next16 appended unchanged. No other normalization.",
  "bootstrap": "2,000 draws of entire sorted tid clusters with replacement, seed 20261025, shared inference.bootstrap helper; percentile 95% CI; all tid including zero-denominator clusters retained, nonfinite denominator draws omitted",
  "point_decision": "unrounded pooled statistic at original threshold; eligibility failure is unevaluable",
  "p_value_decision": "unadjusted one-sided p; root applies multiplicity control"
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=5e-05.

Counts: `{"positions_all": 4272, "tid_all": 54, "positions_eligible": 4272, "tid_eligible": 54, "rl_successes": 1679, "sft_successes": 1014, "common_denominator": 21360}`
- `bootstrap`: estimate=0.031132958801498127, CI95=[0.021498451690835817, 0.04159510445455909], n=54
- `component_rate_bootstraps.rl`: estimate=0.07860486891385768, CI95=[0.05972045668549906, 0.1000736047071632], n=54
- `component_rate_bootstraps.sft`: estimate=0.04747191011235955, CI95=[0.03606216622937254, 0.06013682319026047], n=54

Complete raw explore result: `out/consolidation/explore/H27.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.

### H28: RL has more narrow evaluation lexical markers absent from the local observed text.

Script: `work/tests/H28.py`

Explore command: `python -B work/tests/H28.py --data disc_data/explore`

Holdout command (once, fresh tester only): `python -B work/tests/H28.py --data disc_data/holdout`

Exact specification:
```json
{
  "hypothesis_id": "H28",
  "source_candidate": "GLM06-C5",
  "claim": "RL has more narrow evaluation lexical markers absent from the local observed text.",
  "exact_computation": "For each original greedy/s1..s4 bullet, hit=bool(EVAL.search(bullet)) and not bool(EVAL.search(left_ctx+next16)). Per-tid difference numerator=sum(RL hits minus SFT hits); common denominator=5*all row count, including rows with visible evaluation lexicon. Statistic=pooled RL-minus-SFT hit rate.",
  "regex": "\\b(?:graders?|grading|evaluators?|reward hacking|test harness|benchmark dataset|IFBench|IFEval)\\b",
  "regex_flags": "re.I",
  "threshold": {
    "operator": ">=",
    "value": 0.00025
  },
  "falsifier": "Pooled absent-local-lexicon evaluation-marker difference <0.00025.",
  "eligibility": "At least 10 distinct tid.",
  "null": "No positive RL-minus-SFT evaluation lexical-marker contrast under whole-tid paired sign exchangeability about zero; 0.00025 is a separate effect-size floor.",
  "p_method": "paired_signflip on per-tid summed paired numerator differences. Exact enumeration over nonzero tid when <=18; zeros do not add independent evidence. Otherwise 19,999 Monte Carlo flips, seed 20261025, plus-one correction.",
  "ci_rule": "Pooled difference bootstrap lower 95% bound >0.",
  "interpretation_limit": "Lexical replication only, not latent intent, scheming or actual evaluation awareness.",
  "data_file": "glm_rollouts_sample.csv",
  "scope": "all supplied rows; no role or family exclusions; no hand-check data",
  "weights": "pooled rates, all positions retained; greedy+s1+s2+s3+s4 each weight 1 except H26 uses six stochastic sample pairs",
  "preprocessing": "Initial state label(left_ctx), never duplicate token. strip = re.sub(r'^\\* ', '', text, count=1). Append left_ctx+strip(bullet) with no added separator; next16 appended unchanged. No other normalization.",
  "bootstrap": "2,000 draws of entire sorted tid clusters with replacement, seed 20261025, shared inference.bootstrap helper; percentile 95% CI; all tid including zero-denominator clusters retained, nonfinite denominator draws omitted",
  "point_decision": "unrounded pooled statistic at original threshold; eligibility failure is unevaluable",
  "p_value_decision": "unadjusted one-sided p; root applies multiplicity control"
}
```

Explore result: evaluable=True; numerical thresholds=True; CI gate=True; raw p=0.0625.

Counts: `{"positions_all": 4272, "tid_all": 54, "positions_eligible": 4272, "tid_eligible": 54, "rl_successes": 18, "sft_successes": 1, "common_denominator": 21360}`
- `bootstrap`: estimate=0.000795880149812734, CI95=[9.261403102570039e-05, 0.0016850284258601062], n=54
- `component_rate_bootstraps.rl`: estimate=0.0008426966292134832, CI95=[0.00013784380379626562, 0.0017332454561893283], n=54
- `component_rate_bootstraps.sft`: estimate=4.6816479400749066e-05, CI95=[0.0, 0.00014198159282401268], n=54

Complete raw explore result: `out/consolidation/explore/H28.stdout.json`. Falsifier and missing-data policy are fixed above and in the hashed executable.
