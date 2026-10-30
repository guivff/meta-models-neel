# SA-R registered confirmatory replication

Report posted 2026-10-22T01:20:29.034320+00:00; analysis sealed 2026-10-22T01:14:18.817590+00:00.

Both NLA and the Oracle lens are CONFIRMED under the registered five-control superiority rule on the prospectively filtered population. The invisibility gate passed396/400 cases (99%), with all20 concepts represented. NLA named152/396 (38.38% pooled;38.50% equal-concept), and Oracle204/396 (51.52% pooled;51.00% equal-concept). All five observed controls had zero hits on the same396 cases; both readers still beat every control after worst-case MISSING scoring and Bonferroni-adjusted clustered intervals. This supports naming of these authored injected concrete concepts at0.7 calibrated dose under this measured invisibility test; it does not establish arbitrary-concept naming, natural-state interpretability, or superiority over known-concept probes.

## Primary rates and controls

All rows below use the identical396 retained recipient cases. MISSING and invalid indicators can overlap; do not add them. Both remain in denominators as failures. Macro is the registered equal-concept endpoint.

| Method | Concept hits / n | Pooled | Macro | Random hits | No-edit hits | Shuffled concept hits | Concept MISSING | Concept invalid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nla | 152/396 | 38.38% | 38.50% | 0 | 0 | 0 | 12 | 22 |
| oracle | 204/396 | 51.52% | 51.00% | 0 | 0 | 0 | 30 | 30 |
| asking | 0/396 | 0.00% | 0.00% | 0 | 0 | — | 0 | 0 |
| blind_word_L42_top5 | 0/396 | 0.00% | 0.00% | 0 | 0 | 0 | 0 | 0 |
| blind_word_L44_top5 | 0/396 | 0.00% | 0.00% | 0 | 0 | 0 | 0 | 0 |

## Registered contrasts

Differences are equal-concept percentage points. Intervals below are conservative envelopes of the three registered97.5% paired clustered percentile intervals; the lower endpoint is the decision bound.10,000 draws,seed20261021; Bonferroni across two readers. All five contrasts must pass.

| Reader | Control | Observed difference (pp) | Observed conservative interval (pp) | Worst-case MISSING interval (pp) | Pass |
|---|---|---:|---:|---:|---|
| nla | matched_random | 38.500 | [7.750, 72.252] | [7.750, 72.252] | True |
| nla | no_edit | 38.500 | [7.750, 72.252] | [7.750, 72.252] | True |
| nla | fixed_shuffle | 38.500 | [7.750, 72.252] | [6.247, 68.250] | True |
| nla | asking | 38.500 | [7.750, 72.252] | [7.750, 72.252] | True |
| nla | blind_word_top5 | 38.500 | [7.750, 72.252] | [7.750, 72.252] | True |
| oracle | matched_random | 51.000 | [21.500, 80.250] | [21.500, 80.250] | True |
| oracle | no_edit | 51.000 | [21.500, 80.250] | [21.500, 80.250] | True |
| oracle | fixed_shuffle | 51.000 | [21.500, 80.250] | [11.749, 75.000] | True |
| oracle | asking | 51.000 | [21.500, 80.250] | [21.500, 80.250] | True |
| oracle | blind_word_top5 | 51.000 | [21.500, 80.250] | [21.500, 80.250] | True |

## Prespecified secondary benchmarks — DESCRIPTIVE

These are known-concept comparisons, not open-vocabulary naming or additional confirmation hurdles. All linear/cosine concept top1 and top5 scores are396/396 at both layers. Blind word top1/top5 scores are0/396 at both layers. Diffing against the added vector is excluded.

| Method | Concept | Random | No-edit | Shuffled concept |
|---|---:|---:|---:|---:|
| blind_word_L42_top1 | 0/396 | 0/396 | 0/396 | 0/396 |
| blind_word_L42_top5 | 0/396 | 0/396 | 0/396 | 0/396 |
| blind_word_L44_top1 | 0/396 | 0/396 | 0/396 | 0/396 |
| blind_word_L44_top5 | 0/396 | 0/396 | 0/396 | 0/396 |
| linear_probe_L42_top1 | 396/396 | 25/396 | 20/396 | 0/396 |
| linear_probe_L42_top5 | 396/396 | 115/396 | 100/396 | 260/396 |
| linear_probe_L44_top1 | 396/396 | 11/396 | 20/396 | 0/396 |
| linear_probe_L44_top5 | 396/396 | 119/396 | 100/396 | 268/396 |
| cosine_probe_L42_top1 | 396/396 | 20/396 | 20/396 | 0/396 |
| cosine_probe_L42_top5 | 396/396 | 103/396 | 100/396 | 276/396 |
| cosine_probe_L44_top1 | 396/396 | 20/396 | 20/396 | 0/396 |
| cosine_probe_L44_top5 | 396/396 | 93/396 | 100/396 | 260/396 |

## Missingness, sealing and audit

All18,000 logical analysis rows were retained; global logical MISSING=43, invalid=107. These global counts and derived shuffled-mask counts are different views and can overlap. All4,040 planned physical scientific records were present; smoke14/14. Judge fixtures3/3; parse20/20. Integrity gates passed. Judge charged$1.98527025, unresolved reserves$0,2206 settled reservations. Full per-method/arm missingness, failure categories, visibility summaries, bootstrap diagnostics and per-concept rates are in RESULTS.json and RATES_SUMMARY.json.

Prediction/judge artifacts were frozen before the analysis truth join; POSTPROCESS_COMPLETE hashes were independently checked before reading these results. Original66 imported cells retain original pod/git/code/run provenance. Final archive b6f2839c91c8c4bea6266dc78dcf8c3a01afa87613c8392b6c0786653fca0a84 and5123members independently rehashed; pod STOPPED/EXITED and all guards retired. GPU aggregate upper bound17801.913962s=4.9449761h, billed once. The text-only pricing repair changed accounting admission, not scientific settings or outputs.

## Full population and exclusions — EXPLORATORY

The registered verdict uses396 passing cases. Full400 and excluded4 rates below are descriptive exploratory context, not alternative confirmation tests.

| Reader | Full hits /400 | Excluded hits /4 |
|---|---:|---:|
| nla | 156/400 | 4/4 |
| oracle | 207/400 | 3/4 |

## Scope and limitations

- Conditional on the prospectively fixed concept-arm invisibility mask; not unconditional naming performance.
- Only five semantic groups and five prompt families; semantic groups are not independent source corpora.
- Random and shuffled donors use the recipient mask; equal norm does not imply equal behavioral impact.
- Fresh direction source sentences contain the concept names explicitly.
- Known-concept probes and blind-word top1 are secondary and never alter a reader decision.
- More-than-five detection counts asserted in-bank candidate IDs, not an independent out-of-bank inventory.
- Confirmation is not evidence that Oracle outperforms NLA; no reader-versus-reader claim is tested here.
- Perfect known-concept probes show that this injected finite-label task remains readily decodable with a supplied concept bank. Zero blind-word baseline hits apply to the registered frequent-word deviation method only.

## Artifacts

- RESULTS.json: unchanged registered machine-readable analysis and input/provenance hashes.
- RATES_SUMMARY.json: compact rates, missingness and uncertainty extracted without rerunning analysis.
- POSTPROCESS_COMPLETE.json: hash binding of results, judged outputs, CPU predictions and final pull.
- REPORT.md: this report.

§54 prerequisite: SA-R analysis is now posted. §54 still requires its separate tested launch-ready receipt and budget/timing admission; no §54 compute was started by this watch.
