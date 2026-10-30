# §248 C amendment1 — complete once

Exploratory, post hoc after E135. **Susceptibility to steering predicts it.** The registered added-probe gate for “the early representation predicts staleness” is not met. These are predictive associations, not causal effects. Independent R-Q numerical review requested.

Original C seal: `48c56c1f122d20036f60416a3bac4c4328214525f6adfad8f6cd7894be8d71b8`. Parts1/2 seal: `013fd87cfeb4cf355a058d1af20c1ac6e81f55771ed14f298ea201f331997691`. Both guards consumed; never replay. Original A/experiment outputs unchanged. Public seal copies are references: full verification requires original CPU-local private rows and bindings.

## Fixed groups and controls

Easy: original alpha4 flippers42; resistant: first flip at alpha6,42. No unknown memberships. Each quantity uses its own observed census. Group old44 rates are **exclusive-old** (dual not counted); predictive old44-alpha8 target is **old present**, including dual, on the E109 reference bank. Dual/old-presence companion rates are not separately tabulated in the sealed parts1/2 result.

| Quantity | Easy | Resistant | Resistant − easy (95% item-bootstrap CI) |
|---|---:|---:|---:|
| Clean E127 no-prefix old44 | 24/41 (0.5854), Wilson [0.4337, 0.7224] | 42/42 (1.0000), Wilson [0.9162, 1.0000] | 0.414634 [0.268252, 0.571429] |
| Clean E131 answer margin | 3.904762 (n=42) | 10.983259 (n=42) | 7.078497 [6.957600, 7.206164] |
| Random old44 alpha4 — E128 | 31/42 (0.7381), Wilson [0.5893, 0.8470] | 42/42 (1.0000), Wilson [0.9162, 1.0000] | 0.261905 [0.135135, 0.400000] |
| Random old44 alpha6 — E135 | 21/42 (0.5000), Wilson [0.3553, 0.6447] | 40/42 (0.9524), Wilson [0.8421, 0.9868] | 0.452381 [0.281457, 0.619048] |
| Random old44 alpha8 — original E104 | 16/42 (0.3810), Wilson [0.2500, 0.5319] | 41/42 (0.9762), Wilson [0.8768, 0.9958] | 0.595238 [0.439003, 0.744681] |

Clean old44 has one missing easy item; all other quantities above have42/42 in each group. Random alpha8 uses original E104 judgments, never E109 reference substitution. Differences use joint original-item percentile bootstrap5000/seed0, group and missingness travel with item. All5000 draws defined.

## Read-token44 displacement

Displacement is norm(steered − clean)/norm(clean). Original E109 alpha8 and captured E135 alpha6 matched exact original item/prompt-token/read-index; all84 vectors per dose available. No write-site calibration substitution.

| Dose | Easy mean | Resistant mean | Difference (95% CI) |
|---|---:|---:|---:|
| 6 | 0.218585 | 0.198553 | -0.020032 [-0.022801, -0.017328] |
| 8 | 0.224254 | 0.209410 | -0.014845 [-0.017485, -0.012223] |

## Registered logistic/LOO comparisons

L2 C1, lbfgs2000, seed0; standardizer fit on training folds only; no tuning. Common three-feature complete-case census per outcome. Resistance n84; old44 staleness n83 with one missing judgment. Model coefficients, original registered feature AUROCs/two-feature fits and all intervals are in RESULTS.json.

| Outcome | Answer | Probe | Displacement | Answer + probe | All three |
|---|---:|---:|---:|---:|---:|
| old44_alpha8 | 0.919622 | 0.662530 | 0.920213 | 0.911348 | 0.952128 |
| resistant | 1.000000 | 0.710884 | 0.941610 | 1.000000 | 1.000000 |

Primary added-probe LOO AUROC gain for staleness: **-0.008274**, 95% CI [-0.026182, 0.001763]. Required gain>=.05 and lower>0 both fail. Geometry-adjusted probe gain: -0.001773 [-0.008187, 0.002331]. Resistance gain is0. The caption is determined by the staleness endpoint, not whichever endpoint performs better.

Intervals for LOO AUROCs/gains use paired item bootstrap of fixed out-of-fold scores5000/seed0, not bootstrap refits. No new probes, acquisitions, judging, ledger changes or historical analysis replays. Parts1/2 reused byte-for-byte without recomputation.
