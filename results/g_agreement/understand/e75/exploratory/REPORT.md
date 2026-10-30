# E75 follow-up — EXPLORATORY

Both requested jobs are exploratory. Authority1e879d02 and direct user instruction. R-P1 remains sealed NOT EVALUABLE; the registered scorer was not rerun. Design/code frozen at a43c1b68 before follow-up computation.

## Exploratory logistic comparison

| Reader | Eligible units | Category log-loss | Category + J log-loss | Loss reduction (95% CI), nats | Within-category permutation p |
|---|---:|---:|---:|---|---:|
| oracle | 55 | 0.6097 | 0.3898 | 0.2199 (0.1268–0.3106) | 0.00100 |
| nla | 35 | 0.6557 | 0.4669 | 0.1889 (0.0745–0.2937) | 0.00200 |

| Reader | Category BA | Category + J BA | BA increase (95% CI), pp | Within-category permutation p |
|---|---:|---:|---|---:|
| oracle | 65.45% | 81.17% | +15.72 (+0.87–+30.82) | 0.00100 |
| nla | 57.19% | 74.67% | +17.48 (-0.66–+35.83) | 0.02398 |

These exploratory estimates support incremental predictive information in continuous J-fraction beyond a fitted category-only logistic model on these rows. This does not establish the registered R-P1 category-gap criterion or change its verdict.

Fixed ridge logistic C=1, unpenalised intercept, reference bookkeeping, no class weights or tuning. J standardised using training-fold mean and population SD. Leave one bank/row out; E62 state×rung remains a row; threshold0.5. Both historical and mechanical categories included, making the whole analysis exploratory.

Paired10000 row-bootstrap draws over the fixed out-of-fold predictions;95% percentile intervals, conditional on these fitted predictions rather than a full refit bootstrap. No single-class bootstrap draws occurred.1000 permutations shuffle J within category and refit every augmented leave-one-row-out model; one-sided plus-one p. Seed20261028. Rows from a common bank/family may remain dependent; leave-one-row-out is not leave-one-bank-out.

## Exploratory W1 measurement audit

No registered measurement mismatch found. W1 remains a false alarm for both readers.

| Component | Audit result |
|---|---|
| Layer | Same zero-based decoder block44 output (HF hidden_states45). |
| Token | Same final input token convention. E73 token255 of256; synthetic bank token len(ids)−1. Absolute indices differ by design. |
| Basis/dictionary | Same pinned J44 unit-normalised W_U @ J44 atoms, no final-norm gain. Same secondary SVD basis, not the primary fraction. |
| Pursuit | Same CPU kernel, nonnegative k16, six refinement steps; unchanged code seals verified. |
| Normalisation | Float64 A-minus-B means, L2 unit direction, float32 pursuit input; squared reconstruction norm divided by squared input norm. Saved fractions and directions verified. |
| Labels | Original E73 A0/B1 explicitly mapped to common A1/B0. Saved W1 means verified against all400 bound vectors. |

W1 J-fraction=0.035322721169; common null median=0.018472731455,97.5th=0.024643934140. Frozen G3 was NOT EVALUABLE because the A-token set was empty; existing label rule allowed IN-J when readability is NOT EVALUABLE. This exception was preserved.

E73 uses400 tests/state and float16 activation storage; synthetic84/unit and float32 storage. Same extraction point and downstream normalisation; this audit does not establish numerical identity across acquisition implementations.

The audit reads sealed saved artifacts and code only. No model forward, capture, pursuit, forecast or native analysis was rerun. Full hashes and numeric checks: W1_AUDIT.json. All logistic rows, OOF probabilities, null draws and intervals: RESULTS.json.
