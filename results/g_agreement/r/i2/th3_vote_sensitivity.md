# TH-3 candidate-margin vote sensitivity

**ROBUST.** Dated 2026-10-21 (Europe/Zurich); preregistered in `76bb9618` before computing. CPU only, no fits. This labelled sensitivity leaves the registered TH-3 verdict unchanged.

Conservative 95% intervals below are the envelope of 2,000 item and 2,000 corpus-cluster bootstrap draws (seed 0), replaying the original streams. Original coverage, fact folds and per-draw bottom-third cutoffs are preserved. LABEL_DEFECT excluded; audit-flagged facts included.

| Reader | Hard n | PO accuracy | Registered accuracy | Margin accuracy | Registered reader − PO | Margin reader − PO | Earlier score AUC | A−B AUC |
|---|---:|---:|---:|---:|---|---|---|---|
| olens | 7066 | 0.650 | 0.552 | 0.530 | -0.098 [-0.137, -0.057] | -0.120 [-0.168, -0.057] | 0.505 [0.457, 0.545] | 0.490 [0.456, 0.579] |
| nla | 7066 | 0.650 | 0.538 | 0.516 | -0.112 [-0.162, -0.073] | -0.134 [-0.186, -0.069] | 0.518 [0.462, 0.552] | 0.485 [0.449, 0.564] |
| jlens | 7066 | 0.650 | 0.549 | 0.516 | -0.101 [-0.145, -0.064] | -0.133 [-0.181, -0.069] | 0.506 [0.463, 0.580] | 0.502 [0.460, 0.575] |
| skip_a | 7066 | 0.650 | 0.549 | 0.523 | -0.100 [-0.142, -0.057] | -0.127 [-0.175, -0.061] | 0.508 [0.462, 0.544] | 0.481 [0.445, 0.576] |
| lr | 6800 | 0.649 | 0.727 | 0.727 | 0.078 [0.035, 0.148] | 0.078 [0.035, 0.148] | 0.797 [0.723, 0.883] | 0.797 [0.723, 0.883] |
| massmean | 6800 | 0.649 | 0.643 | 0.643 | -0.006 [-0.043, 0.044] | -0.006 [-0.043, 0.044] | 0.700 [0.650, 0.769] | 0.700 [0.650, 0.769] |
| prompt_only | 7066 | 0.650 | 0.650 | 0.650 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.705 [0.658, 0.787] | 0.705 [0.658, 0.787] |

Registered native votes use test-median lp(A) for one-sided facts and sign(A−B) for two-sided facts. Margin votes use A−B>0 throughout, ties negative. J-lens uses candidate cosine scores, not log probabilities. LR, mass-mean and prompt-only retain their original decisions and are comparators; the robustness rule concerns the four native readers in the deficit claim.

The earlier AUC re-check used lp(A) on one-sided facts and A−B on two-sided facts: the quoted 0.505–0.518 native AUCs versus about 0.705 for prompt-only were not uniformly candidate-margin AUCs. Both AUC columns here predict the binary label; they are not the cross-fitted correctness-prediction AUCs in TH-3. Probes use their signed class scores. Scores are pooled across facts, as in the earlier audit.

Legacy hard-difference bootstrap replay maximum absolute error: {'item': np.float64(1.1102230246251565e-16), 'corpus': np.float64(1.1102230246251565e-16)}. Full accuracy and AUC intervals and each bootstrap scheme are retained in the companion CSV.

Rule: ROBUST requires every native margin-difference upper bound <−0.03; CONVENTION-DEPENDENT requires at least one interval containing zero. Neither criterion implies that the original registered analysis was changed.
