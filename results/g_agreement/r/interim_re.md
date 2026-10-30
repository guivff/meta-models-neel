# R-E (beyond the text, BRIEF_R §11) — interim tables (WS3)

Checkpoint tiers (BRIEF_RP §0): olens = community (agu18dec/olens_and_ar olens_s3d_rl600 (Qwen3.6-27B)); jlens = community (neuronpedia/jacobian-lens (Qwen3.6-27B)); nla = community (ceselder/qwen3.6-27b-nla-rl iter 400 (Qwen3.6-27B)); skip_a = community (agreelens skip lenses (Qwen3.6-27B)); prompt-only, probes and the logit lens = none. Every Oracle-lens number is the Qwen Oracle lens at that checkpoint. Each reader family is its own row; this file has no Gemma AO and no Qwen AO row, and never pools them with the Qwen Oracle lens.

generated 2026-10-19 23:58 UTC; partial rows — every number moves as rows arrive. Facts covered: 8 two-/one-sided with reader rows; k-way: 0 with reader rows, 3 with prompt-only rows; bank: 11 facts. Pods: ['C', 'E'].

Reader rows present so far (reader: blocks): jlens: [24, 28, 32, 36, 38, 40, 42, 44, 48, 52, 56, 60]; nla: [42]; olens (community): [24, 28, 32, 36, 40, 42, 44, 48, 52, 56]; skip_a: [42]. Claims are made at each reader's primary site only (J-lens 42, Oracle (community) 44, NLA / skip 42; `re_count_col` raw).

Label audit (uniform trigger, `label_audit.md`): flagged in this bank: none (marked ⚑ below; every count is also given without them).

**Shuffled gate (§4.2, 95% CI ∋ 0.5):** 27 pass / 5 fail of 32 primary-site cells (expected at 5%: 1.6); per-item-candidate facts 4/16 fail, fixed-candidate facts 1/16. † on an exceedance = its shuffled cell fails (candidate prior suspected; not read as a reading of the state).
Failing cells (natural / shuffled AUROC): olens (community) re_khop2_answer 0.885 / 0.557; skip_a re_khop2_answer 0.919 / 0.568; skip_a re_syntax_clauses 0.977 / 0.426; olens (community) re_syntax_head 0.405 / 0.362; skip_a re_syntax_head 0.394 / 0.371
probe(512) is shown as — on facts with per-item, order-counterbalanced candidates: their label is the candidate order, which is not in the prompt state (≈ 0.5 by construction).

## Beyond-text facts (KHOP, SYNTAX, COUNT, INTERNAL)

Natural test AUROC at the reader's primary site [item-bootstrap 95% CI]; Δ = reader − prompt-only (paired); exceed = Δ ≥ +0.05 with CI > 0 (raw, no BH); shuffled gate = shuffled cell's CI ∋ 0.5.

| tag | fact | reader | site | n | AUROC [CI] | prompt-only | Δ [CI] | exceed | probe(512) | ≥ 0.8×probe | shuffled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| KHOP | re_khop2_answer | jlens | 42/chat | 236 | 0.896 [0.855, 0.931] | 1.000 | -0.104 [-0.145, -0.069] |  | — | — | pass |
| KHOP | re_khop2_answer | nla | 42/chat | 400 | 0.763 [0.715, 0.813] | 1.000 | -0.237 [-0.285, -0.187] |  | — | — | pass |
| KHOP | re_khop2_answer | olens (community) | 44/chat | 400 | 0.885 [0.849, 0.919] | 1.000 | -0.115 [-0.151, -0.081] |  | — | — | FAIL |
| KHOP | re_khop2_answer | skip_a | 42/chat | 400 | 0.919 [0.891, 0.942] | 1.000 | -0.081 [-0.109, -0.057] |  | — | — | FAIL |
| KHOP | re_khop2_bridge | jlens | 42/chat | 392 | 0.960 [0.941, 0.975] | 1.000 | -0.040 [-0.059, -0.025] |  | — | — | pass |
| KHOP | re_khop2_bridge | nla | 42/chat | 400 | 0.945 [0.924, 0.964] | 1.000 | -0.055 [-0.076, -0.036] |  | — | — | pass |
| KHOP | re_khop2_bridge | olens (community) | 44/chat | 400 | 0.894 [0.861, 0.924] | 1.000 | -0.106 [-0.139, -0.076] |  | — | — | pass |
| KHOP | re_khop2_bridge | skip_a | 42/chat | 400 | 0.950 [0.930, 0.968] | 1.000 | -0.050 [-0.070, -0.032] |  | — | — | pass |
| KHOP | re_khop3_middle | jlens | 42/chat | 38 | 0.961 [0.899, 1.000] | 1.000 | -0.039 [-0.101, +0.000] |  | — | — | pass |
| KHOP | re_khop3_middle | nla | 42/chat | 80 | 0.953 [0.912, 0.990] | 1.000 | -0.047 [-0.088, -0.010] |  | — | — | pass |
| KHOP | re_khop3_middle | olens (community) | 44/chat | 80 | 0.951 [0.903, 0.986] | 1.000 | -0.049 [-0.097, -0.014] |  | — | — | pass |
| KHOP | re_khop3_middle | skip_a | 42/chat | 80 | 0.961 [0.925, 0.993] | 1.000 | -0.039 [-0.075, -0.007] |  | — | — | pass |
| SYNTAX | re_syntax_clauses | jlens | 42/chat | 200 | 0.957 [0.929, 0.979] | 1.000 | -0.043 [-0.071, -0.021] |  | 1.000 | yes | pass |
| SYNTAX | re_syntax_clauses | nla | 42/chat | 200 | 0.944 [0.913, 0.970] | 1.000 | -0.056 [-0.087, -0.030] |  | 1.000 | yes | pass |
| SYNTAX | re_syntax_clauses | olens (community) | 44/chat | 200 | 0.611 [0.533, 0.678] | 1.000 | -0.389 [-0.467, -0.322] |  | 1.000 | no | pass |
| SYNTAX | re_syntax_clauses | skip_a | 42/chat | 200 | 0.977 [0.957, 0.992] | 1.000 | -0.023 [-0.043, -0.008] |  | 1.000 | yes | FAIL |
| SYNTAX | re_syntax_head | jlens | 42/chat | 170 | 0.566 [0.476, 0.645] | 1.000 | -0.434 [-0.524, -0.355] |  | — | — | pass |
| SYNTAX | re_syntax_head | nla | 42/chat | 200 | 0.424 [0.348, 0.506] | 1.000 | -0.576 [-0.652, -0.494] |  | — | — | pass |
| SYNTAX | re_syntax_head | olens (community) | 44/chat | 200 | 0.405 [0.333, 0.488] | 1.000 | -0.595 [-0.667, -0.512] |  | — | — | FAIL |
| SYNTAX | re_syntax_head | skip_a | 42/chat | 200 | 0.394 [0.322, 0.478] | 1.000 | -0.606 [-0.678, -0.522] |  | — | — | FAIL |
| SYNTAX | re_syntax_number | jlens | 42/chat | 200 | 0.761 [0.678, 0.826] | 1.000 | -0.239 [-0.322, -0.174] |  | 1.000 | no | pass |
| SYNTAX | re_syntax_number | nla | 42/chat | 200 | 0.596 [0.524, 0.673] | 1.000 | -0.404 [-0.476, -0.326] |  | 1.000 | no | pass |
| SYNTAX | re_syntax_number | olens (community) | 44/chat | 200 | 0.745 [0.681, 0.810] | 1.000 | -0.255 [-0.319, -0.190] |  | 1.000 | no | pass |
| SYNTAX | re_syntax_number | skip_a | 42/chat | 200 | 0.657 [0.583, 0.734] | 1.000 | -0.343 [-0.417, -0.266] |  | 1.000 | no | pass |
| INTERNAL | re_internal_abstain | jlens | 42/chat | 120 | 0.838 [0.739, 0.919] | 0.854 | -0.016 [-0.096, +0.063] |  | 1.000 | yes | pass |
| INTERNAL | re_internal_abstain | nla | 42/chat | 120 | 0.949 [0.897, 0.990] | 0.854 | +0.095 [+0.046, +0.153] | yes | 1.000 | yes | pass |
| INTERNAL | re_internal_abstain | olens (community) | 44/chat | 120 | 0.890 [0.821, 0.954] | 0.854 | +0.036 [-0.036, +0.120] |  | 1.000 | yes | pass |
| INTERNAL | re_internal_abstain | skip_a | 42/chat | 120 | 0.898 [0.733, 0.995] | 0.854 | +0.044 [-0.091, +0.143] |  | 1.000 | yes | pass |
| INTERNAL | re_internal_refuse | jlens | 42/chat | 240 | 0.520 [0.439, 0.590] | 0.965 | -0.444 [-0.525, -0.373] |  | 0.999 | no | pass |
| INTERNAL | re_internal_refuse | nla | 42/chat | 240 | 0.971 [0.952, 0.989] | 0.965 | +0.006 [-0.016, +0.026] |  | 0.999 | yes | pass |
| INTERNAL | re_internal_refuse | olens (community) | 44/chat | 240 | 0.902 [0.862, 0.937] | 0.965 | -0.063 [-0.097, -0.034] |  | 0.999 | yes | pass |
| INTERNAL | re_internal_refuse | skip_a | 42/chat | 240 | 0.841 [0.794, 0.888] | 0.965 | -0.123 [-0.164, -0.080] |  | 0.999 | yes | pass |

## k-way facts (COUNT and the other k-way parents)

modal share = share of items given the reader's most frequent pick (1.0 = it answers the same candidate always; its accuracy is then 1/k by construction on a balanced test).

| fact | method | layer/render | k | n | accuracy [Wilson 95%] | chance | modal share |
|---|---|---|---|---|---|---|---|
| re_count_col | prompt_only | — | 3 | 180 | 0.350 [0.284, 0.422] | 0.333 | — |
| re_count_listed | prompt_only | — | 8 | 200 | 1.000 [0.981, 1.000] | 0.125 | — |
| re_count_long | prompt_only | — | 5 | 200 | 0.465 [0.397, 0.534] | 0.200 | — |

## §11 decision rules (R-E)

### KHOP — H2 clause (≥ 0.8 × probe(512) on ≥ 2 of 3 KHOP facts)

**NOT TESTABLE as written:** all three KHOP facts have per-item, order-counterbalanced candidates (label = "c0 is the truth"). That label is not in the prompt state, so probe(512) is ≈ 0.5 by construction (measured 0.500 on re_khop2_answer / re_khop2_bridge), and "reader ≥ 0.8 × probe" would reduce to "reader ≥ 0.4". Reader AUROCs at the primary site are in the table above; a valid PRESENT reference (a probe on the bridge or answer entity, scored per candidate) is not pre-registered.

### SYNTAX — attractor interference on `re_syntax_number` (match − mismatch AUROC ≥ 0.10 with CI > 0)

| reader | site | AUROC match | AUROC mismatch | drop [95% CI] | interference |
|---|---|---|---|---|---|
| jlens | 42/chat | 0.806 | 0.712 | +0.094 [-0.032, +0.229] | no |
| nla | 42/chat | 0.753 | 0.440 | +0.314 [+0.158, +0.460] | YES |
| olens (community) | 44/chat | 0.841 | 0.637 | +0.203 [+0.071, +0.344] | YES |
| skip_a | 42/chat | 0.733 | 0.576 | +0.157 [+0.001, +0.306] | YES |
The model's own is/are readout (`construction.behaviour`, next-token lp(are) − lp(is)) is reported once its rows exist.

### INTERNAL — does the reader side with the model's behaviour or the design label?

Diagnostics (not part of the rule): `beh=1` = share of disagreeing items whose behaviour is the positive candidate; `pos rate` = the reader's share of s_diff > 0 over all natural test items. A reader with pos rate ≈ 0 or 1 answers its prior, and P(sides with behaviour) then equals beh=1 or 1 − beh=1 by construction.

| fact | reader | layer/render | disagreeing n | beh=1 | pos rate | P(sides with behaviour) [Wilson] | verdict |
|---|---|---|---|---|---|---|---|
| re_internal_refuse | jlens | 24/chat | 25 | 0.56 | 0.97 | 0.56 [0.37, 0.73] | MIXED |
| re_internal_refuse | jlens | 28/chat | 25 | 0.56 | 0.84 | 0.56 [0.37, 0.73] | MIXED |
| re_internal_refuse | jlens | 32/chat | 25 | 0.56 | 0.53 | 0.52 [0.33, 0.70] | MIXED |
| re_internal_refuse | jlens | 36/chat | 25 | 0.56 | 0.49 | 0.32 [0.17, 0.52] | MIXED |
| re_internal_refuse | jlens | 38/chat | 25 | 0.56 | 0.46 | 0.32 [0.17, 0.52] | MIXED |
| re_internal_refuse | jlens | 40/chat | 25 | 0.56 | 0.55 | 0.32 [0.17, 0.52] | MIXED |
| re_internal_refuse | jlens | 42/chat | 25 | 0.56 | 0.75 | 0.52 [0.33, 0.70] | MIXED |
| re_internal_refuse | jlens | 44/chat | 25 | 0.56 | 0.78 | 0.48 [0.30, 0.67] | MIXED |
| re_internal_refuse | jlens | 48/chat | 25 | 0.56 | 0.92 | 0.56 [0.37, 0.73] | MIXED |
| re_internal_refuse | jlens | 52/chat | 25 | 0.56 | 0.96 | 0.56 [0.37, 0.73] | MIXED |
| re_internal_refuse | jlens | 56/chat | 25 | 0.56 | 0.95 | 0.52 [0.33, 0.70] | MIXED |
| re_internal_refuse | jlens | 60/chat | 25 | 0.56 | 0.86 | 0.40 [0.23, 0.59] | MIXED |
| re_internal_refuse | nla | 42/chat | 25 | 0.56 | 0.72 | 0.52 [0.33, 0.70] | MIXED |
| re_internal_refuse | olens (community) | 42/chat | 25 | 0.56 | 0.81 | 0.48 [0.30, 0.67] | MIXED |
| re_internal_refuse | olens (community) | 44/chat | 25 | 0.56 | 0.84 | 0.44 [0.27, 0.63] | MIXED |
| re_internal_refuse | olens (community) | 48/chat | 25 | 0.56 | 0.90 | 0.56 [0.37, 0.73] | MIXED |
| re_internal_refuse | olens (community) | 52/chat | 25 | 0.56 | 0.94 | 0.56 [0.37, 0.73] | MIXED |
| re_internal_refuse | olens (community) | 56/chat | 25 | 0.56 | 0.90 | 0.44 [0.27, 0.63] | MIXED |
| re_internal_refuse | skip_a | 42/chat | 25 | 0.56 | 0.73 | 0.36 [0.20, 0.55] | MIXED |
| re_internal_abstain | jlens | 24/chat | 46 | 0.00 | 0.10 | 0.93 [0.82, 0.98] | READS THE MODEL |
| re_internal_abstain | jlens | 28/chat | 46 | 0.00 | 0.69 | 0.20 [0.11, 0.33] | READS THE TEXT |
| re_internal_abstain | jlens | 32/chat | 46 | 0.00 | 0.53 | 0.00 [0.00, 0.08] | READS THE TEXT |
| re_internal_abstain | jlens | 36/chat | 46 | 0.00 | 0.66 | 0.00 [0.00, 0.08] | READS THE TEXT |
| re_internal_abstain | jlens | 38/chat | 46 | 0.00 | 0.82 | 0.00 [0.00, 0.08] | READS THE TEXT |
| re_internal_abstain | jlens | 40/chat | 46 | 0.00 | 0.80 | 0.00 [0.00, 0.08] | READS THE TEXT |
| re_internal_abstain | jlens | 42/chat | 46 | 0.00 | 0.65 | 0.00 [0.00, 0.08] | READS THE TEXT |
| re_internal_abstain | jlens | 44/chat | 46 | 0.00 | 0.66 | 0.00 [0.00, 0.08] | READS THE TEXT |
| re_internal_abstain | jlens | 48/chat | 46 | 0.00 | 0.54 | 0.00 [0.00, 0.08] | READS THE TEXT |
| re_internal_abstain | jlens | 52/chat | 46 | 0.00 | 0.48 | 0.39 [0.26, 0.54] | MIXED |
| re_internal_abstain | jlens | 56/chat | 46 | 0.00 | 0.55 | 0.59 [0.44, 0.72] | MIXED |
| re_internal_abstain | jlens | 60/chat | 46 | 0.00 | 0.49 | 0.67 [0.53, 0.79] | MIXED |
| re_internal_abstain | nla | 42/chat | 46 | 0.00 | 0.50 | 0.02 [0.00, 0.11] | READS THE TEXT |
| re_internal_abstain | olens (community) | 42/chat | 46 | 0.00 | 0.64 | 0.11 [0.05, 0.23] | READS THE TEXT |
| re_internal_abstain | olens (community) | 44/chat | 46 | 0.00 | 0.54 | 0.15 [0.08, 0.28] | READS THE TEXT |
| re_internal_abstain | olens (community) | 48/chat | 46 | 0.00 | 0.52 | 0.20 [0.11, 0.33] | READS THE TEXT |
| re_internal_abstain | olens (community) | 52/chat | 46 | 0.00 | 0.49 | 0.17 [0.09, 0.31] | READS THE TEXT |
| re_internal_abstain | olens (community) | 56/chat | 46 | 0.00 | 0.63 | 0.24 [0.14, 0.38] | READS THE TEXT |
| re_internal_abstain | skip_a | 42/chat | 46 | 0.00 | 0.48 | 0.41 [0.28, 0.56] | MIXED |

### E4 — `re_count_long` on the model-wrong subset

Not yet: needs k-way reader rows and prompt-only greedy counts.

### E6 — KHOP bridge: hop-1 span (24–40) vs last token (42–60), model-correct subset

model-correct items: 199

| reader | span best (layer) | last best (layer) | span − last [95% CI] | verdict |
|---|---|---|---|---|
| jlens | 1.000 (24) | 0.999 (56) | +0.001 [+0.000, +0.003] | no |
| nla | — | — | — | needs both positions |
| olens (community) | 0.983 (24) | 0.974 (56) | +0.009 [-0.007, +0.027] | no |
| skip_a | — | — | — | needs both positions |

## Other facts

No reader rows for these facts yet.
