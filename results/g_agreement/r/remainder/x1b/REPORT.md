# X1b-lite — completed follow-up after X1’s caliper stop

The bridge patch changed answers and downstream bridge readings relative to the norm-decile-matched random-natural control. The preregistered low-detectability gate **FAILED**: L42 Mahalanobis AUROC0.60685 (95% wider CI0.56689–0.64591), above the0.60 point threshold. Exact natural donor states therefore do not establish an on-manifold downstream state or resolve the off-manifold objection. All three primary SWAP-U verdicts are **MIXED**.

§34; editL28 selected from the fixed20pool-item pilot and pusheda2306cc before test. FreshH100 captures only. Of200test items,197had a matched bridge control;195were naturally model-correct, with **120flipped /75non-flipped** (quota met). Three unmatched bridge controls and two unmatched answer controls were retained as explicit exclusions; no bins were relaxed. All1000model rows and3980reader cells passed completeness checks. J has4unscorable bridge-cohort items; its continuous analysis uses191items.

## Answer flips

Primary cohort: naturally model-correct, bridge-control-matched items. Rates61.54% real vs18.97% random; paired difference **42.564percentage points [33.871,51.093]**. Norm-adjusted sensitivity42.581pp [34.011,51.137]; AGREES. All197bridge-matched items: difference42.132pp [33.523,50.569].

## Downstream bridge read-back

Switch means original→swapped-in bridge among naturally correct model and reader items; n therefore varies by reader. Continuous shifts include all scorable naturally model-correct matched items. Positive net shift is toward the swapped-in bridge, real minus random.

| Reader / site | Switch n | Real / random switch rates | Switch difference, pp (95% CI) | Continuous net shift (95% CI) |
|---|---:|---:|---:|---:|
| olens / 44 | 149 | 44.30% / 21.48% | 22.819 [14.905–31.406] | 2.025 [1.590–2.490] |
| nla / 42 | 157 | 46.50% / 23.57% | 22.930 [14.204–31.709] | 1.439 [1.110–1.805] |
| jlens / 42 | 158 | 46.84% / 22.78% | 24.051 [16.107–32.742] | 0.400 [0.324–0.476] |
| skip_a / 42 | 163 | 42.94% / 28.83% | 14.110 [7.362–21.472] | 1.799 [1.391–2.237] |

Raw and norm-adjusted group shifts and ρ are tabulated side by side in [RHO.md](RHO.md). The0.94→0.61 detectability comparison with the earlier SWAP subset is descriptive across different cohorts/layers, not a matched reduction estimate.

## SWAP-U on continuous shifts

| Reader | Non-flipped net shift (95% CI) | ρ = non-flipped/flipped (90% CI) | §26 verdict |
|---|---:|---:|---|
| olens | 1.337 [0.832–1.917] | 0.545 [0.355–0.769] | MIXED |
| nla | 0.912 [0.550–1.302] | 0.516 [0.325–0.731] | MIXED |
| jlens | 0.249 [0.161–0.336] | 0.500 [0.350–0.670] | SECONDARY_NO_BH_VERDICT |
| skip_a | 1.046 [0.580–1.533] | 0.461 [0.283–0.661] | MIXED |

Non-flipped shifts are positive, but rho intervals straddle0.5 and the primary readers do not meet either §26 classification after BH. Norm-adjusted and margin-tercile sensitivities retain the primary MIXED verdicts. J is secondary and receives no BH verdict. Raw/adjusted contrasts agree under the preregistered sign/CI-category and verdict comparisons; none is labelled adjustment-sensitive. Full estimates, cluster intervals, undefined fractions, p/q values and retained strata are in tables/rho_table.json.

## Mahalanobis gate and specificity

| Arm | L42 AUROC (95% CI) | L44 AUROC (95% CI) |
|---|---:|---:|
| bridge_patch | 0.607 [0.567–0.646] | 0.607 [0.566–0.647] |
| answer_patch | 0.548 [0.537–0.563] | 0.534 [0.525–0.546] |
| random_bridge | 0.765 [0.722–0.806] | 0.772 [0.727–0.813] |
| natural | 0.500 [0.500–0.500] | 0.500 [0.500–0.500] |
| random_answer | 0.896 [0.856–0.935] | 0.847 [0.806–0.888] |
| natural_specificity | 0.457 [0.281–0.643] | 0.455 [0.280–0.638] |

Natural-vs-natural specificity uses disjoint20pool-item groups; its wide interval includes chance. The natural arm compared with itself is a structural0.5 check, not independent specificity evidence. Random-natural bridge controls are more detectable than same-relation bridge patches; decile matching does not remove contextual or displacement confounding.

## Descriptive answer-position arms

No DISSOCIATED verdict is defined for this follow-up. Median real answer/bridge displacement ratio is0.04866; answer and bridge doses remain very different.

| Arm | Naturally correct n | Model flip rate (Wilson95%) |
|---|---:|---:|
| answer_patch | 198 | 0.00% [0.000–1.903] |
| random_answer | 196 | 0.51% [0.090–2.833] |

| Reader | Answer patch bridge-switch rate (Wilson95%) | Random answer bridge-switch rate (Wilson95%) |
|---|---:|---:|
| olens | 3.95% [1.821–8.344], n=152 | 4.67% [2.279–9.319], n=150 |
| nla | 9.38% [5.764–14.891], n=160 | 6.33% [3.474–11.258], n=158 |
| jlens | 8.12% [4.810–13.404], n=160 | 8.18% [4.840–13.485], n=159 |
| skip_a | 6.02% [3.305–10.733], n=166 | 7.93% [4.691–13.089], n=164 |

## Verification and limitations

2,000bootstrap draws, seed0. Effect CIs are95%; rho CIs90%; quote the widest envelope over paired-item, true-bridge-cluster and donor-bridge-cluster schemes. One bank cannot support across-corpus generalization; bridge clusters are not independent corpora. Answer-position rates are descriptive with Wilson intervals, not causal contrasts. Ten fixed-seed non-flipped examples are in tables/examples.json. Matching and displacement imbalance are in tables/matching_table.json.

All929files (497,965,974bytes) were verified on Mac and remote; manifestSHA a58f22b8cf543bfbbb89868fe34806d8888d6bcf0d13a94b3f42a988baf8870f. Point audit independently reconstructed14flip/continuous/rho quantities. All28CPU decoy tests passed before launch; all-arm and all-reader live smokes passed. Runtime comparison is in RUNTIME_COMPARISON.md; it is descriptive and combines hardware/runtime differences. Source0ee68fa; no scientific thresholds changed after data.

Compute ended successfully; rA4 was posted HANDOVER_READY at07:30Z under liveguards12008/11722, with a verified pull and bounded warm reservation. It was not stopped or terminated. E5 replacement guards were independently verified and X1b guards retired watchdog-first at07:50:35Z/07:50:36Z. Final X1b billing uses E5’s declared07:43:09Z boundary:06:42:06Z–07:43:09Z,1.0175pod-h (estimated$4.06 at$3.99/h), including hold/setup/pulls; recorded separately from nonadditive science-phase timings.
