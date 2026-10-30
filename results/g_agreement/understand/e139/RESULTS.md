E139 completed once on CPU. Instrument gate **PASS** via fact recall: true-minus-neutral proxy-FVE gain +0.019047 [+0.017176, +0.021084]. Language did not pass this control. Twenty frozen original Oracle44 readouts per state, paired item-bootstrap95%CIs,2000draws/seed20261030. No new model/reader/judge calls.

Primary scores are explicitly **proxy reward**, whole-readout whitened reconstruction-FVE in the fixed E125/E130 output convention. Exact joint-bullet training-reward execution remains uncertified; no extra alignment or rewhitening of predictions was fitted. Prior E125/E130 qualifications remain.

| State | True − neutral proxy gain [95% CI] | True − false [95% CI] |
|---|---:|---:|
| evaluation_cue | -0.001070 [-0.003206, +0.001163] | +0.000149 [-0.001976, +0.002340] |
| fact_recall | +0.019047 [+0.017176, +0.021084] | -0.000200 [-0.001625, +0.001372] |
| inside_string | -0.000391 [-0.002750, +0.001989] | -0.000031 [-0.000802, +0.000720] |
| language | +0.000356 [-0.002876, +0.003698] | +0.000523 [-0.004047, +0.005254] |
| nesting_depth | +0.002730 [+0.000273, +0.004987] | -0.000186 [-0.002148, +0.001771] |
| table_column | +0.008495 [+0.005246, +0.012059] | -0.000209 [-0.002029, +0.001733] |

Nesting depth and table column show positive proxy gains; inside-string, language and the cue have intervals spanning zero. All six true-minus-false intervals span zero: no value preference was resolved. Neither zero effects nor true/false equivalence are established. The pattern is mixed; no new equivalence/comparability margin or global account-selection rule was invented.

Secondary Δ_u is the signed movement along each state's own DEV rebuilt-span class1-minus-class0 direction, divided by its fixed class gap. DEV direction is held fixed in the item bootstrap; class0 items are not sign-flipped. It is separate from the primary reward gain.

| State | Δ_true [95% CI] | Δ_false [95% CI] | Δ_neutral [95% CI] |
|---|---:|---:|---:|
| evaluation_cue | NOT EVALUABLE | NOT EVALUABLE | NOT EVALUABLE |
| fact_recall | -0.031032 [-0.060263, -0.003279] | -0.080434 [-0.123742, -0.038205] | +0.012112 [-0.019436, +0.043366] |
| inside_string | -0.024483 [-0.089108, +0.036051] | -0.024492 [-0.087457, +0.034597] | -0.014520 [-0.079500, +0.048500] |
| language | -0.058975 [-0.115728, +0.002089] | -0.065313 [-0.113756, -0.013311] | -0.119758 [-0.165847, -0.070777] |
| nesting_depth | -0.019951 [-0.067637, +0.024767] | -0.017906 [-0.066884, +0.029084] | -0.041308 [-0.088700, +0.002768] |
| table_column | +0.006918 [-0.024124, +0.040692] | +0.006472 [-0.025936, +0.041861] | +0.008022 [-0.022480, +0.041559] |

**Cue Δ_u is NOT EVALUABLE:** the frozen200 E130 DEV-span rebuilds yield a zero class-mean gap, so d and its denominator are undefined. No direction or zero statistic was substituted, and no rerun was made. Other states use their frozen20 DEV spans. Language here is the E73 code-versus-prose control. Table column uses the directly authorized original W1 readouts/activations with original labels/provenance.

Canonical CPU result: `/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e139-analysis-once`; ANALYSIS_SEAL302e487b480b227e62520dd22803cde00e896679c7d85216d87a31a1f46b270b. Outer acquisition31f87d09, inner78329148, frozenCPU78a68412, pre-output scoring-source4b06a089/commit11eae2ff. The exclusive original attempt marker remains. Public RESULTS.json removes only per-item Δ_u lists; source values/private rows/labels remain CPU-only. Independent R-2 review is pending; do not invoke the author command again.
