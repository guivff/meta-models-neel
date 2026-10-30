# ReaderBench — interim tables (WS3)

Checkpoint tiers (BRIEF_RP §0): olens = community (agu18dec/olens_and_ar olens_s3d_rl600 (Qwen3.6-27B)); jlens = community (neuronpedia/jacobian-lens (Qwen3.6-27B)); nla = community (ceselder/qwen3.6-27b-nla-rl iter 400 (Qwen3.6-27B)); skip_a = community (agreelens skip lenses (Qwen3.6-27B)); prompt-only, probes and the logit lens = none. Every Oracle-lens number is the Qwen Oracle lens at that checkpoint. Each reader family is its own row; this file has no Gemma AO and no Qwen AO row, and never pools them with the Qwen Oracle lens.

generated 2026-10-19 23:59 UTC; partial rows — every number moves as rows arrive. Facts covered: 55 two-/one-sided with reader rows; k-way: 7 with reader rows, 7 with prompt-only rows; bank: 62 facts. Pods: ['C', 'RB'].

Reader rows present so far (reader: blocks): jlens: [24, 28, 32, 36, 38, 40, 42, 44, 48, 52, 56, 60]; nla: [42]; olens (community): [42, 44, 48, 52, 56]; skip_a: [42]. Claims are made at each reader's primary site only (J-lens 42, Oracle (community) 44, NLA / skip 42; `re_count_col` raw).

**Model labels (fixed 2026-10-20, WS3 bullet):** rb_context_against_belief, rb_internal_abstain, rb_internal_puzzle_answer, rb_internal_refusal, rb_internal_self_choice take their AUROC label from `model_labels*.jsonl::model_label` (WS12's design); before this date these tables used the provisional label. Test items with a model label / total; agreement with the construction label: rb_context_against_belief 110/110, 1.00; rb_internal_abstain 116/116, 0.66; rb_internal_puzzle_answer 74/124, 0.32; rb_internal_refusal 60/60, 0.97; rb_internal_self_choice 144/144, 0.60. Pool items with a model label (probe(512) training): rb_context_against_belief 106/106; rb_internal_abstain 116/116; rb_internal_puzzle_answer 59/124; rb_internal_refusal 60/60; rb_internal_self_choice 144/144.

Label audit (uniform trigger, `label_audit.md`): flagged in this bank: rb_internal_puzzle_answer (marked ⚑ below; every count is also given without them).

**Shuffled gate (§4.2, 95% CI ∋ 0.5):** 190 pass / 30 fail of 220 primary-site cells (expected at 5%: 11.0); per-item-candidate facts 21/64 fail, fixed-candidate facts 9/156. † on an exceedance = its shuffled cell fails (candidate prior suspected; not read as a reading of the state).
Failing cells (natural / shuffled AUROC): nla rb_computed_sum_carry 0.421 / 0.399; olens (community) rb_computed_weekday_weekend 0.447 / 0.616; jlens rb_context_against_belief 0.393 / 0.264; nla rb_context_against_belief 0.026 / 0.014; olens (community) rb_context_against_belief 0.085 / 0.058; skip_a rb_context_against_belief 0.085 / 0.030; jlens rb_form_register 0.943 / 0.398; nla rb_form_register 0.999 / 0.395; jlens rb_internal_abstain 0.839 / 0.659; nla rb_internal_abstain 0.672 / 0.676; nla rb_internal_puzzle_answer ⚑ 0.674 / 0.641; jlens rb_internal_self_choice 0.698 / 0.630; nla rb_internal_self_choice 0.684 / 0.633; nla rb_khop_3hop_middle 0.964 / 0.735; olens (community) rb_khop_3hop_middle 0.962 / 0.689; skip_a rb_khop_3hop_middle 0.984 / 0.782; skip_a rb_khop_capital_language_answer 0.728 / 0.416; nla rb_khop_landmark_capital_answer 0.912 / 0.664; olens (community) rb_khop_landmark_capital_answer 0.874 / 0.623; skip_a rb_khop_landmark_capital_answer 0.827 / 0.591; nla rb_khop_landmark_capital_bridge 0.893 / 0.588; olens (community) rb_khop_landmark_capital_bridge 0.931 / 0.648; skip_a rb_khop_landmark_capital_bridge 0.923 / 0.605; olens (community) rb_khop_landmark_currency_answer 0.749 / 0.703; olens (community) rb_khop_landmark_currency_bridge 0.959 / 0.593; olens (community) rb_knowledge_animal_class 0.819 / 0.393; skip_a rb_knowledge_country_capital_distractor 0.860 / 0.650; jlens rb_meta_answer_format 1.000 / 0.373; olens (community) rb_meta_answer_format 0.994 / 0.371; jlens rb_syntax_head_identity 0.680 / 0.608

**Shuffled gate, without flagged facts (§4.2, 95% CI ∋ 0.5):** 187 pass / 29 fail of 216 primary-site cells (expected at 5%: 10.8); per-item-candidate facts 20/60 fail, fixed-candidate facts 9/156. † on an exceedance = its shuffled cell fails (candidate prior suspected; not read as a reading of the state).
probe(512) is shown as — on facts with per-item, order-counterbalanced candidates: their label is the candidate order, which is not in the prompt state (≈ 0.5 by construction).

## Beyond-text facts (KHOP, SYNTAX, COUNT, INTERNAL)

Natural test AUROC at the reader's primary site [item-bootstrap 95% CI]; Δ = reader − prompt-only (paired); exceed = Δ ≥ +0.05 with CI > 0 (raw, no BH); shuffled gate = shuffled cell's CI ∋ 0.5.

| tag | fact | reader | site | n | AUROC [CI] | prompt-only | Δ [CI] | exceed | probe(512) | ≥ 0.8×probe | shuffled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| KHOP | rb_khop_3hop_middle | jlens | 42/chat | 64 | 0.921 [0.845, 0.972] | 1.000 | -0.079 [-0.155, -0.028] |  | — | — | pass |
| KHOP | rb_khop_3hop_middle | nla | 42/chat | 72 | 0.964 [0.917, 0.996] | 1.000 | -0.036 [-0.083, -0.004] |  | — | — | FAIL |
| KHOP | rb_khop_3hop_middle | olens (community) | 44/chat | 72 | 0.962 [0.915, 0.990] | 1.000 | -0.038 [-0.085, -0.010] |  | — | — | FAIL |
| KHOP | rb_khop_3hop_middle | skip_a | 42/chat | 72 | 0.984 [0.959, 0.998] | 1.000 | -0.016 [-0.041, -0.002] |  | — | — | FAIL |
| KHOP | rb_khop_capital_language_answer | jlens | 42/chat | 156 | 0.953 [0.922, 0.979] | 1.000 | -0.047 [-0.078, -0.021] |  | — | — | pass |
| KHOP | rb_khop_capital_language_answer | nla | 42/chat | 200 | 0.600 [0.527, 0.681] | 1.000 | -0.400 [-0.473, -0.319] |  | — | — | pass |
| KHOP | rb_khop_capital_language_answer | olens (community) | 44/chat | 200 | 0.870 [0.823, 0.913] | 1.000 | -0.130 [-0.177, -0.087] |  | — | — | pass |
| KHOP | rb_khop_capital_language_answer | skip_a | 42/chat | 200 | 0.728 [0.657, 0.796] | 1.000 | -0.272 [-0.343, -0.204] |  | — | — | FAIL |
| KHOP | rb_khop_capital_language_bridge | jlens | 42/chat | 162 | 0.768 [0.688, 0.845] | 1.000 | -0.232 [-0.312, -0.155] |  | — | — | pass |
| KHOP | rb_khop_capital_language_bridge | nla | 42/chat | 200 | 0.822 [0.767, 0.871] | 1.000 | -0.178 [-0.233, -0.129] |  | — | — | pass |
| KHOP | rb_khop_capital_language_bridge | olens (community) | 44/chat | 200 | 0.920 [0.880, 0.952] | 1.000 | -0.080 [-0.120, -0.048] |  | — | — | pass |
| KHOP | rb_khop_capital_language_bridge | skip_a | 42/chat | 200 | 0.825 [0.772, 0.878] | 1.000 | -0.175 [-0.228, -0.122] |  | — | — | pass |
| KHOP | rb_khop_landmark_capital_answer | jlens | 42/chat | 99 | 0.648 [0.546, 0.757] | 1.000 | -0.352 [-0.454, -0.243] |  | — | — | pass |
| KHOP | rb_khop_landmark_capital_answer | nla | 42/chat | 160 | 0.912 [0.861, 0.955] | 1.000 | -0.088 [-0.139, -0.045] |  | — | — | FAIL |
| KHOP | rb_khop_landmark_capital_answer | olens (community) | 44/chat | 160 | 0.874 [0.806, 0.927] | 1.000 | -0.126 [-0.194, -0.073] |  | — | — | FAIL |
| KHOP | rb_khop_landmark_capital_answer | skip_a | 42/chat | 160 | 0.827 [0.761, 0.891] | 1.000 | -0.173 [-0.239, -0.109] |  | — | — | FAIL |
| KHOP | rb_khop_landmark_capital_bridge | jlens | 42/chat | 141 | 0.874 [0.813, 0.925] | 1.000 | -0.126 [-0.187, -0.075] |  | — | — | pass |
| KHOP | rb_khop_landmark_capital_bridge | nla | 42/chat | 160 | 0.893 [0.845, 0.934] | 1.000 | -0.107 [-0.155, -0.066] |  | — | — | FAIL |
| KHOP | rb_khop_landmark_capital_bridge | olens (community) | 44/chat | 160 | 0.931 [0.892, 0.963] | 1.000 | -0.069 [-0.108, -0.037] |  | — | — | FAIL |
| KHOP | rb_khop_landmark_capital_bridge | skip_a | 42/chat | 160 | 0.923 [0.885, 0.957] | 1.000 | -0.077 [-0.115, -0.043] |  | — | — | FAIL |
| KHOP | rb_khop_landmark_currency_answer | jlens | 42/chat | 20 | 0.717 [0.464, 0.928] | 1.000 | -0.283 [-0.536, -0.072] |  | — | — | pass |
| KHOP | rb_khop_landmark_currency_answer | nla | 42/chat | 160 | 0.614 [0.520, 0.695] | 1.000 | -0.386 [-0.480, -0.305] |  | — | — | pass |
| KHOP | rb_khop_landmark_currency_answer | olens (community) | 44/chat | 160 | 0.749 [0.663, 0.820] | 1.000 | -0.251 [-0.337, -0.180] |  | — | — | FAIL |
| KHOP | rb_khop_landmark_currency_answer | skip_a | 42/chat | 160 | 0.591 [0.499, 0.671] | 1.000 | -0.409 [-0.501, -0.329] |  | — | — | pass |
| KHOP | rb_khop_landmark_currency_bridge | jlens | 42/chat | 124 | 0.856 [0.783, 0.917] | 1.000 | -0.144 [-0.217, -0.083] |  | — | — | pass |
| KHOP | rb_khop_landmark_currency_bridge | nla | 42/chat | 160 | 0.855 [0.796, 0.907] | 1.000 | -0.145 [-0.204, -0.093] |  | — | — | pass |
| KHOP | rb_khop_landmark_currency_bridge | olens (community) | 44/chat | 160 | 0.959 [0.933, 0.983] | 1.000 | -0.041 [-0.067, -0.017] |  | — | — | FAIL |
| KHOP | rb_khop_landmark_currency_bridge | skip_a | 42/chat | 160 | 0.896 [0.845, 0.940] | 1.000 | -0.104 [-0.155, -0.060] |  | — | — | pass |
| SYNTAX | rb_syntax_agreement_number | jlens | 42/chat | 128 | 0.704 [0.607, 0.797] | 1.000 | -0.296 [-0.393, -0.203] |  | 0.999 | no | pass |
| SYNTAX | rb_syntax_agreement_number | nla | 42/chat | 128 | 0.580 [0.483, 0.683] | 1.000 | -0.420 [-0.517, -0.317] |  | 0.999 | no | pass |
| SYNTAX | rb_syntax_agreement_number | olens (community) | 44/chat | 128 | 0.680 [0.588, 0.772] | 1.000 | -0.320 [-0.412, -0.228] |  | 0.999 | no | pass |
| SYNTAX | rb_syntax_agreement_number | skip_a | 42/chat | 128 | 0.596 [0.489, 0.691] | 1.000 | -0.404 [-0.511, -0.309] |  | 0.999 | no | pass |
| SYNTAX | rb_syntax_before_after | jlens | 42/chat | 160 | 0.281 [0.204, 0.365] | 0.995 | -0.714 [-0.794, -0.627] |  | 0.999 | no | pass |
| SYNTAX | rb_syntax_before_after | nla | 42/chat | 160 | 0.698 [0.614, 0.781] | 0.995 | -0.297 [-0.382, -0.216] |  | 0.999 | no | pass |
| SYNTAX | rb_syntax_before_after | olens (community) | 44/chat | 160 | 0.262 [0.192, 0.334] | 0.995 | -0.733 [-0.807, -0.654] |  | 0.999 | no | pass |
| SYNTAX | rb_syntax_before_after | skip_a | 42/chat | 160 | 0.566 [0.473, 0.653] | 0.995 | -0.429 [-0.520, -0.339] |  | 0.999 | no | pass |
| SYNTAX | rb_syntax_clause_count | jlens | 42/chat | 116 | 0.668 [0.560, 0.769] | 0.999 | -0.331 [-0.438, -0.231] |  | 1.000 | no | pass |
| SYNTAX | rb_syntax_clause_count | nla | 42/chat | 116 | 0.912 [0.855, 0.956] | 0.999 | -0.088 [-0.144, -0.044] |  | 1.000 | yes | pass |
| SYNTAX | rb_syntax_clause_count | olens (community) | 44/chat | 116 | 0.842 [0.765, 0.906] | 0.999 | -0.157 [-0.233, -0.094] |  | 1.000 | yes | pass |
| SYNTAX | rb_syntax_clause_count | skip_a | 42/chat | 116 | 0.901 [0.839, 0.953] | 0.999 | -0.098 [-0.160, -0.047] |  | 1.000 | yes | pass |
| SYNTAX | rb_syntax_head_identity | jlens | 42/chat | 111 | 0.680 [0.589, 0.776] | 1.000 | -0.320 [-0.411, -0.224] |  | — | — | FAIL |
| SYNTAX | rb_syntax_head_identity | nla | 42/chat | 122 | 0.514 [0.419, 0.621] | 1.000 | -0.486 [-0.581, -0.379] |  | — | — | pass |
| SYNTAX | rb_syntax_head_identity | olens (community) | 44/chat | 122 | 0.601 [0.499, 0.698] | 1.000 | -0.399 [-0.501, -0.302] |  | — | — | pass |
| SYNTAX | rb_syntax_head_identity | skip_a | 42/chat | 122 | 0.495 [0.391, 0.600] | 1.000 | -0.505 [-0.609, -0.400] |  | — | — | pass |
| SYNTAX | rb_syntax_pronoun_antecedent | jlens | 42/chat | 126 | 0.465 [0.365, 0.565] | 1.000 | -0.535 [-0.635, -0.435] |  | — | — | pass |
| SYNTAX | rb_syntax_pronoun_antecedent | nla | 42/chat | 126 | 0.555 [0.458, 0.653] | 1.000 | -0.445 [-0.542, -0.347] |  | — | — | pass |
| SYNTAX | rb_syntax_pronoun_antecedent | olens (community) | 44/chat | 126 | 0.553 [0.448, 0.650] | 1.000 | -0.447 [-0.552, -0.350] |  | — | — | pass |
| SYNTAX | rb_syntax_pronoun_antecedent | skip_a | 42/chat | 126 | 0.515 [0.412, 0.616] | 1.000 | -0.485 [-0.588, -0.384] |  | — | — | pass |
| SYNTAX | rb_syntax_quantifier_every_no | jlens | 42/chat | 160 | 0.832 [0.768, 0.887] | 1.000 | -0.168 [-0.232, -0.113] |  | 1.000 | yes | pass |
| SYNTAX | rb_syntax_quantifier_every_no | nla | 42/chat | 160 | 0.915 [0.873, 0.955] | 1.000 | -0.085 [-0.127, -0.045] |  | 1.000 | yes | pass |
| SYNTAX | rb_syntax_quantifier_every_no | olens (community) | 44/chat | 160 | 0.822 [0.761, 0.889] | 1.000 | -0.178 [-0.239, -0.111] |  | 1.000 | yes | pass |
| SYNTAX | rb_syntax_quantifier_every_no | skip_a | 42/chat | 160 | 0.936 [0.900, 0.967] | 1.000 | -0.064 [-0.100, -0.033] |  | 1.000 | yes | pass |
| COUNT | rb_count_bracket_shallow_deep | jlens | 42/chat | 178 | 0.669 [0.587, 0.744] | 0.809 | -0.141 [-0.235, -0.049] |  | 0.974 | no | pass |
| COUNT | rb_count_bracket_shallow_deep | nla | 42/chat | 178 | 0.443 [0.358, 0.527] | 0.809 | -0.366 [-0.480, -0.263] |  | 0.974 | no | pass |
| COUNT | rb_count_bracket_shallow_deep | olens (community) | 44/chat | 178 | 0.505 [0.422, 0.589] | 0.809 | -0.304 [-0.402, -0.204] |  | 0.974 | no | pass |
| COUNT | rb_count_bracket_shallow_deep | skip_a | 42/chat | 178 | 0.699 [0.624, 0.772] | 0.809 | -0.111 [-0.193, -0.017] |  | 0.974 | no | pass |
| COUNT | rb_count_items_few_many | jlens | 42/chat | 196 | 0.762 [0.693, 0.828] | 1.000 | -0.238 [-0.307, -0.172] |  | 0.996 | no | pass |
| COUNT | rb_count_items_few_many | nla | 42/chat | 196 | 0.664 [0.588, 0.734] | 1.000 | -0.336 [-0.412, -0.266] |  | 0.996 | no | pass |
| COUNT | rb_count_items_few_many | olens (community) | 44/chat | 196 | 0.310 [0.240, 0.390] | 1.000 | -0.690 [-0.760, -0.610] |  | 0.996 | no | pass |
| COUNT | rb_count_items_few_many | skip_a | 42/chat | 196 | 0.744 [0.671, 0.811] | 1.000 | -0.256 [-0.329, -0.189] |  | 0.996 | no | pass |
| COUNT | rb_count_line_long_short | jlens | 42/chat | 198 | 0.513 [0.433, 0.583] | 0.998 | -0.485 [-0.564, -0.414] |  | 1.000 | no | pass |
| COUNT | rb_count_line_long_short | nla | 42/chat | 198 | 0.806 [0.732, 0.882] | 0.998 | -0.192 [-0.266, -0.115] |  | 1.000 | yes | pass |
| COUNT | rb_count_line_long_short | olens (community) | 44/chat | 198 | 0.288 [0.218, 0.362] | 0.998 | -0.709 [-0.780, -0.636] |  | 1.000 | no | pass |
| COUNT | rb_count_line_long_short | skip_a | 42/chat | 198 | 0.473 [0.391, 0.559] | 0.998 | -0.525 [-0.607, -0.438] |  | 1.000 | no | pass |
| INTERNAL | rb_internal_abstain (model label; defect prevalence 34% of 116 labelled, 0 dropped) | jlens | 42/chat | 116 | 0.839 [0.748, 0.912] | 0.792 | +0.047 [-0.054, +0.147] |  | 0.939 | yes | FAIL |
| INTERNAL | rb_internal_abstain (model label; defect prevalence 34% of 116 labelled, 0 dropped) | nla | 42/chat | 116 | 0.672 [0.540, 0.784] | 0.792 | -0.120 [-0.289, +0.037] |  | 0.939 | no | FAIL |
| INTERNAL | rb_internal_abstain (model label; defect prevalence 34% of 116 labelled, 0 dropped) | olens (community) | 44/chat | 116 | 0.855 [0.790, 0.911] | 0.792 | +0.063 [-0.031, +0.157] |  | 0.939 | yes | pass |
| INTERNAL | rb_internal_abstain (model label; defect prevalence 34% of 116 labelled, 0 dropped) | skip_a | 42/chat | 116 | 0.398 [0.211, 0.567] | 0.792 | -0.394 [-0.618, -0.183] |  | 0.939 | no | pass |
| INTERNAL | rb_internal_puzzle_answer ⚑ | jlens | 42/chat | 74 | 0.567 [0.437, 0.689] | 0.731 | -0.163 [-0.318, -0.016] |  | — | — | pass |
| INTERNAL | rb_internal_puzzle_answer ⚑ | nla | 42/chat | 74 | 0.674 [0.551, 0.802] | 0.731 | -0.057 [-0.254, +0.137] |  | — | — | FAIL |
| INTERNAL | rb_internal_puzzle_answer ⚑ | olens (community) | 44/chat | 74 | 0.564 [0.437, 0.699] | 0.731 | -0.167 [-0.327, -0.003] |  | — | — | pass |
| INTERNAL | rb_internal_puzzle_answer ⚑ | skip_a | 42/chat | 74 | 0.563 [0.440, 0.695] | 0.731 | -0.168 [-0.307, -0.026] |  | — | — | pass |
| INTERNAL | rb_internal_refusal (model label; defect prevalence 3% of 60 labelled, 0 dropped) | jlens | 42/chat | 60 | 0.786 [0.665, 0.894] | 0.991 | -0.205 [-0.321, -0.102] |  | 0.991 | no | pass |
| INTERNAL | rb_internal_refusal (model label; defect prevalence 3% of 60 labelled, 0 dropped) | nla | 42/chat | 60 | 0.974 [0.932, 1.000] | 0.991 | -0.017 [-0.049, +0.007] |  | 0.991 | yes | pass |
| INTERNAL | rb_internal_refusal (model label; defect prevalence 3% of 60 labelled, 0 dropped) | olens (community) | 44/chat | 60 | 0.940 [0.868, 0.992] | 0.991 | -0.051 [-0.120, -0.004] |  | 0.991 | yes | pass |
| INTERNAL | rb_internal_refusal (model label; defect prevalence 3% of 60 labelled, 0 dropped) | skip_a | 42/chat | 60 | 0.933 [0.858, 0.990] | 0.991 | -0.058 [-0.129, -0.004] |  | 0.991 | yes | pass |
| INTERNAL | rb_internal_self_choice (model label; defect prevalence 40% of 144 labelled, 0 dropped) | jlens | 42/chat | 129 | 0.698 [0.611, 0.798] | 0.758 | -0.060 [-0.177, +0.058] |  | — | — | FAIL |
| INTERNAL | rb_internal_self_choice (model label; defect prevalence 40% of 144 labelled, 0 dropped) | nla | 42/chat | 144 | 0.684 [0.599, 0.767] | 0.778 | -0.094 [-0.206, +0.009] |  | — | — | FAIL |
| INTERNAL | rb_internal_self_choice (model label; defect prevalence 40% of 144 labelled, 0 dropped) | olens (community) | 44/chat | 144 | 0.664 [0.560, 0.755] | 0.778 | -0.114 [-0.222, -0.013] |  | — | — | pass |
| INTERNAL | rb_internal_self_choice (model label; defect prevalence 40% of 144 labelled, 0 dropped) | skip_a | 42/chat | 144 | 0.714 [0.611, 0.791] | 0.778 | -0.064 [-0.172, +0.033] |  | — | — | pass |

## k-way facts (COUNT and the other k-way parents)

modal share = share of items given the reader's most frequent pick (1.0 = it answers the same candidate always; its accuracy is then 1/k by construction on a balanced test).

| fact | method | layer/render | k | n | accuracy [Wilson 95%] | chance | modal share |
|---|---|---|---|---|---|---|---|
| rb_computed_weekday | jlens | 24/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 1.00 |
| rb_computed_weekday | jlens | 28/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 0.62 |
| rb_computed_weekday | jlens | 32/chat | 7 | 182 | 0.132 [0.090, 0.189] | 0.143 | 0.78 |
| rb_computed_weekday | jlens | 36/chat | 7 | 182 | 0.137 [0.095, 0.195] | 0.143 | 0.88 |
| rb_computed_weekday | jlens | 38/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 1.00 |
| rb_computed_weekday | jlens | 40/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 1.00 |
| rb_computed_weekday | jlens | 42/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 1.00 |
| rb_computed_weekday | jlens | 44/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 0.98 |
| rb_computed_weekday | jlens | 48/chat | 7 | 182 | 0.154 [0.109, 0.213] | 0.143 | 0.56 |
| rb_computed_weekday | jlens | 52/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 0.96 |
| rb_computed_weekday | jlens | 56/chat | 7 | 182 | 0.159 [0.113, 0.219] | 0.143 | 0.88 |
| rb_computed_weekday | jlens | 60/chat | 7 | 182 | 0.165 [0.118, 0.226] | 0.143 | 0.38 |
| rb_computed_weekday | jlens | 24/raw | 7 | 182 | 0.165 [0.118, 0.226] | 0.143 | 0.36 |
| rb_computed_weekday | jlens | 28/raw | 7 | 182 | 0.165 [0.118, 0.226] | 0.143 | 0.69 |
| rb_computed_weekday | jlens | 32/raw | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 0.97 |
| rb_computed_weekday | jlens | 36/raw | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 0.98 |
| rb_computed_weekday | jlens | 38/raw | 7 | 182 | 0.165 [0.118, 0.226] | 0.143 | 0.87 |
| rb_computed_weekday | jlens | 40/raw | 7 | 182 | 0.170 [0.123, 0.232] | 0.143 | 0.63 |
| rb_computed_weekday | jlens | 42/raw | 7 | 182 | 0.165 [0.118, 0.226] | 0.143 | 0.64 |
| rb_computed_weekday | jlens | 44/raw | 7 | 182 | 0.165 [0.118, 0.226] | 0.143 | 0.53 |
| rb_computed_weekday | jlens | 48/raw | 7 | 182 | 0.148 [0.104, 0.207] | 0.143 | 0.56 |
| rb_computed_weekday | jlens | 52/raw | 7 | 182 | 0.198 [0.146, 0.262] | 0.143 | 0.58 |
| rb_computed_weekday | jlens | 56/raw | 7 | 182 | 0.368 [0.301, 0.440] | 0.143 | 0.29 |
| rb_computed_weekday | jlens | 60/raw | 7 | 182 | 0.418 [0.348, 0.490] | 0.143 | 0.18 |
| rb_computed_weekday | nla | 42/chat | 7 | 182 | 0.132 [0.090, 0.189] | 0.143 | 0.73 |
| rb_computed_weekday | nla | 42/raw | 7 | 182 | 0.148 [0.104, 0.207] | 0.143 | 0.64 |
| rb_computed_weekday | olens (community) | 42/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 0.93 |
| rb_computed_weekday | olens (community) | 44/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 0.96 |
| rb_computed_weekday | olens (community) | 48/chat | 7 | 182 | 0.143 [0.099, 0.201] | 0.143 | 0.99 |
| rb_computed_weekday | olens (community) | 52/chat | 7 | 182 | 0.165 [0.118, 0.226] | 0.143 | 0.73 |
| rb_computed_weekday | olens (community) | 56/chat | 7 | 182 | 0.154 [0.109, 0.213] | 0.143 | 0.54 |
| rb_computed_weekday | olens (community) | 42/raw | 7 | 182 | 0.159 [0.113, 0.219] | 0.143 | 0.33 |
| rb_computed_weekday | olens (community) | 44/raw | 7 | 182 | 0.154 [0.109, 0.213] | 0.143 | 0.69 |
| rb_computed_weekday | olens (community) | 48/raw | 7 | 182 | 0.181 [0.132, 0.244] | 0.143 | 0.59 |
| rb_computed_weekday | olens (community) | 52/raw | 7 | 182 | 0.176 [0.127, 0.238] | 0.143 | 0.72 |
| rb_computed_weekday | olens (community) | 56/raw | 7 | 182 | 0.357 [0.291, 0.429] | 0.143 | 0.47 |
| rb_computed_weekday | prompt_only | — | 7 | 182 | 0.511 [0.439, 0.583] | 0.143 | — |
| rb_computed_weekday | skip_a | 42/chat | 7 | 182 | 0.148 [0.104, 0.207] | 0.143 | 0.97 |
| rb_computed_weekday | skip_a | 42/raw | 7 | 182 | 0.137 [0.095, 0.195] | 0.143 | 0.55 |
| rb_count_bracket_depth | jlens | 24/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 1.00 |
| rb_count_bracket_depth | jlens | 28/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 1.00 |
| rb_count_bracket_depth | jlens | 32/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 1.00 |
| rb_count_bracket_depth | jlens | 36/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 0.98 |
| rb_count_bracket_depth | jlens | 38/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 1.00 |
| rb_count_bracket_depth | jlens | 40/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 1.00 |
| rb_count_bracket_depth | jlens | 42/chat | 4 | 184 | 0.272 [0.213, 0.340] | 0.250 | 0.60 |
| rb_count_bracket_depth | jlens | 44/chat | 4 | 184 | 0.321 [0.257, 0.391] | 0.250 | 0.72 |
| rb_count_bracket_depth | jlens | 48/chat | 4 | 184 | 0.277 [0.218, 0.346] | 0.250 | 0.84 |
| rb_count_bracket_depth | jlens | 52/chat | 4 | 184 | 0.152 [0.107, 0.211] | 0.250 | 0.84 |
| rb_count_bracket_depth | jlens | 56/chat | 4 | 184 | 0.223 [0.169, 0.288] | 0.250 | 0.70 |
| rb_count_bracket_depth | jlens | 60/chat | 4 | 184 | 0.255 [0.198, 0.323] | 0.250 | 0.97 |
| rb_count_bracket_depth | jlens | 24/raw | 4 | 184 | 0.207 [0.154, 0.271] | 0.250 | 0.47 |
| rb_count_bracket_depth | jlens | 28/raw | 4 | 184 | 0.255 [0.198, 0.323] | 0.250 | 0.40 |
| rb_count_bracket_depth | jlens | 32/raw | 4 | 184 | 0.266 [0.208, 0.334] | 0.250 | 0.59 |
| rb_count_bracket_depth | jlens | 36/raw | 4 | 184 | 0.190 [0.140, 0.253] | 0.250 | 0.55 |
| rb_count_bracket_depth | jlens | 38/raw | 4 | 184 | 0.196 [0.145, 0.259] | 0.250 | 0.65 |
| rb_count_bracket_depth | jlens | 40/raw | 4 | 184 | 0.190 [0.140, 0.253] | 0.250 | 0.50 |
| rb_count_bracket_depth | jlens | 42/raw | 4 | 184 | 0.201 [0.150, 0.265] | 0.250 | 0.54 |
| rb_count_bracket_depth | jlens | 44/raw | 4 | 184 | 0.196 [0.145, 0.259] | 0.250 | 0.62 |
| rb_count_bracket_depth | jlens | 48/raw | 4 | 184 | 0.234 [0.178, 0.300] | 0.250 | 0.80 |
| rb_count_bracket_depth | jlens | 52/raw | 4 | 184 | 0.234 [0.178, 0.300] | 0.250 | 0.83 |
| rb_count_bracket_depth | jlens | 56/raw | 4 | 184 | 0.245 [0.188, 0.311] | 0.250 | 0.88 |
| rb_count_bracket_depth | jlens | 60/raw | 4 | 184 | 0.201 [0.150, 0.265] | 0.250 | 0.64 |
| rb_count_bracket_depth | nla | 42/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 1.00 |
| rb_count_bracket_depth | nla | 42/raw | 4 | 184 | 0.245 [0.188, 0.311] | 0.250 | 0.77 |
| rb_count_bracket_depth | olens (community) | 42/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 1.00 |
| rb_count_bracket_depth | olens (community) | 44/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 1.00 |
| rb_count_bracket_depth | olens (community) | 48/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 0.99 |
| rb_count_bracket_depth | olens (community) | 52/chat | 4 | 184 | 0.255 [0.198, 0.323] | 0.250 | 0.97 |
| rb_count_bracket_depth | olens (community) | 56/chat | 4 | 184 | 0.266 [0.208, 0.334] | 0.250 | 0.47 |
| rb_count_bracket_depth | olens (community) | 42/raw | 4 | 184 | 0.239 [0.183, 0.306] | 0.250 | 0.77 |
| rb_count_bracket_depth | olens (community) | 44/raw | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 0.79 |
| rb_count_bracket_depth | olens (community) | 48/raw | 4 | 184 | 0.255 [0.198, 0.323] | 0.250 | 0.86 |
| rb_count_bracket_depth | olens (community) | 52/raw | 4 | 184 | 0.239 [0.183, 0.306] | 0.250 | 0.90 |
| rb_count_bracket_depth | olens (community) | 56/raw | 4 | 184 | 0.239 [0.183, 0.306] | 0.250 | 0.88 |
| rb_count_bracket_depth | prompt_only | — | 4 | 184 | 0.478 [0.407, 0.550] | 0.250 | — |
| rb_count_bracket_depth | skip_a | 42/chat | 4 | 184 | 0.250 [0.193, 0.317] | 0.250 | 1.00 |
| rb_count_bracket_depth | skip_a | 42/raw | 4 | 184 | 0.239 [0.183, 0.306] | 0.250 | 0.70 |
| rb_count_column_position | jlens | 24/chat | 3 | 189 | 0.333 [0.270, 0.403] | 0.333 | 1.00 |
| rb_count_column_position | jlens | 28/chat | 3 | 189 | 0.333 [0.270, 0.403] | 0.333 | 1.00 |
| rb_count_column_position | jlens | 32/chat | 3 | 189 | 0.381 [0.315, 0.452] | 0.333 | 0.70 |
| rb_count_column_position | jlens | 36/chat | 3 | 189 | 0.333 [0.270, 0.403] | 0.333 | 1.00 |
| rb_count_column_position | jlens | 38/chat | 3 | 189 | 0.328 [0.265, 0.398] | 0.333 | 0.99 |
| rb_count_column_position | jlens | 40/chat | 3 | 189 | 0.339 [0.275, 0.409] | 0.333 | 0.99 |
| rb_count_column_position | jlens | 42/chat | 3 | 189 | 0.328 [0.265, 0.398] | 0.333 | 0.93 |
| rb_count_column_position | jlens | 44/chat | 3 | 189 | 0.317 [0.255, 0.387] | 0.333 | 0.58 |
| rb_count_column_position | jlens | 48/chat | 3 | 189 | 0.392 [0.325, 0.463] | 0.333 | 0.51 |
| rb_count_column_position | jlens | 52/chat | 3 | 189 | 0.370 [0.305, 0.441] | 0.333 | 0.61 |
| rb_count_column_position | jlens | 56/chat | 3 | 189 | 0.434 [0.365, 0.505] | 0.333 | 0.51 |
| rb_count_column_position | jlens | 60/chat | 3 | 189 | 0.349 [0.285, 0.420] | 0.333 | 0.60 |
| rb_count_column_position | jlens | 24/raw | 3 | 189 | 0.328 [0.265, 0.398] | 0.333 | 0.78 |
| rb_count_column_position | jlens | 28/raw | 3 | 189 | 0.333 [0.270, 0.403] | 0.333 | 0.76 |
| rb_count_column_position | jlens | 32/raw | 3 | 189 | 0.349 [0.285, 0.420] | 0.333 | 0.78 |
| rb_count_column_position | jlens | 36/raw | 3 | 189 | 0.344 [0.280, 0.414] | 0.333 | 0.72 |
| rb_count_column_position | jlens | 38/raw | 3 | 189 | 0.328 [0.265, 0.398] | 0.333 | 0.67 |
| rb_count_column_position | jlens | 40/raw | 3 | 189 | 0.328 [0.265, 0.398] | 0.333 | 0.74 |
| rb_count_column_position | jlens | 42/raw | 3 | 189 | 0.296 [0.236, 0.365] | 0.333 | 0.72 |
| rb_count_column_position | jlens | 44/raw | 3 | 189 | 0.296 [0.236, 0.365] | 0.333 | 0.75 |
| rb_count_column_position | jlens | 48/raw | 3 | 189 | 0.323 [0.260, 0.392] | 0.333 | 0.87 |
| rb_count_column_position | jlens | 52/raw | 3 | 189 | 0.344 [0.280, 0.414] | 0.333 | 0.79 |
| rb_count_column_position | jlens | 56/raw | 3 | 189 | 0.344 [0.280, 0.414] | 0.333 | 0.74 |
| rb_count_column_position | jlens | 60/raw | 3 | 189 | 0.312 [0.250, 0.381] | 0.333 | 0.74 |
| rb_count_column_position | nla | 42/chat | 3 | 189 | 0.349 [0.285, 0.420] | 0.333 | 0.90 |
| rb_count_column_position | nla | 42/raw | 3 | 189 | 0.370 [0.305, 0.441] | 0.333 | 0.51 |
| rb_count_column_position | olens (community) | 42/chat | 3 | 189 | 0.307 [0.246, 0.376] | 0.333 | 0.55 |
| rb_count_column_position | olens (community) | 44/chat | 3 | 189 | 0.249 [0.192, 0.315] | 0.333 | 0.72 |
| rb_count_column_position | olens (community) | 48/chat | 3 | 189 | 0.365 [0.300, 0.436] | 0.333 | 0.86 |
| rb_count_column_position | olens (community) | 52/chat | 3 | 189 | 0.354 [0.290, 0.425] | 0.333 | 0.80 |
| rb_count_column_position | olens (community) | 56/chat | 3 | 189 | 0.333 [0.270, 0.403] | 0.333 | 0.85 |
| rb_count_column_position | olens (community) | 42/raw | 3 | 189 | 0.323 [0.260, 0.392] | 0.333 | 0.84 |
| rb_count_column_position | olens (community) | 44/raw | 3 | 189 | 0.333 [0.270, 0.403] | 0.333 | 0.83 |
| rb_count_column_position | olens (community) | 48/raw | 3 | 189 | 0.312 [0.250, 0.381] | 0.333 | 0.83 |
| rb_count_column_position | olens (community) | 52/raw | 3 | 189 | 0.344 [0.280, 0.414] | 0.333 | 0.83 |
| rb_count_column_position | olens (community) | 56/raw | 3 | 189 | 0.360 [0.295, 0.430] | 0.333 | 0.83 |
| rb_count_column_position | prompt_only | — | 3 | 189 | 0.577 [0.505, 0.645] | 0.333 | — |
| rb_count_column_position | skip_a | 42/chat | 3 | 189 | 0.291 [0.231, 0.359] | 0.333 | 0.71 |
| rb_count_column_position | skip_a | 42/raw | 3 | 189 | 0.370 [0.305, 0.441] | 0.333 | 0.72 |
| rb_count_items_listed | jlens | 24/chat | 8 | 168 | 0.089 [0.055, 0.142] | 0.125 | 0.36 |
| rb_count_items_listed | jlens | 28/chat | 8 | 168 | 0.125 [0.083, 0.184] | 0.125 | 0.69 |
| rb_count_items_listed | jlens | 32/chat | 8 | 168 | 0.125 [0.083, 0.184] | 0.125 | 1.00 |
| rb_count_items_listed | jlens | 36/chat | 8 | 168 | 0.161 [0.113, 0.224] | 0.125 | 0.95 |
| rb_count_items_listed | jlens | 38/chat | 8 | 168 | 0.149 [0.103, 0.210] | 0.125 | 0.94 |
| rb_count_items_listed | jlens | 40/chat | 8 | 168 | 0.179 [0.128, 0.243] | 0.125 | 0.90 |
| rb_count_items_listed | jlens | 42/chat | 8 | 168 | 0.190 [0.138, 0.257] | 0.125 | 0.66 |
| rb_count_items_listed | jlens | 44/chat | 8 | 168 | 0.196 [0.143, 0.263] | 0.125 | 0.68 |
| rb_count_items_listed | jlens | 48/chat | 8 | 168 | 0.286 [0.223, 0.358] | 0.125 | 0.44 |
| rb_count_items_listed | jlens | 52/chat | 8 | 168 | 0.369 [0.300, 0.444] | 0.125 | 0.48 |
| rb_count_items_listed | jlens | 56/chat | 8 | 168 | 0.387 [0.317, 0.462] | 0.125 | 0.36 |
| rb_count_items_listed | jlens | 60/chat | 8 | 168 | 0.292 [0.228, 0.364] | 0.125 | 0.82 |
| rb_count_items_listed | jlens | 24/raw | 8 | 168 | 0.149 [0.103, 0.210] | 0.125 | 0.31 |
| rb_count_items_listed | jlens | 28/raw | 8 | 168 | 0.161 [0.113, 0.224] | 0.125 | 0.37 |
| rb_count_items_listed | jlens | 32/raw | 8 | 168 | 0.137 [0.093, 0.197] | 0.125 | 0.66 |
| rb_count_items_listed | jlens | 36/raw | 8 | 168 | 0.143 [0.098, 0.204] | 0.125 | 0.58 |
| rb_count_items_listed | jlens | 38/raw | 8 | 168 | 0.143 [0.098, 0.204] | 0.125 | 0.52 |
| rb_count_items_listed | jlens | 40/raw | 8 | 168 | 0.155 [0.108, 0.217] | 0.125 | 0.54 |
| rb_count_items_listed | jlens | 42/raw | 8 | 168 | 0.179 [0.128, 0.243] | 0.125 | 0.26 |
| rb_count_items_listed | jlens | 44/raw | 8 | 168 | 0.208 [0.154, 0.276] | 0.125 | 0.40 |
| rb_count_items_listed | jlens | 48/raw | 8 | 168 | 0.345 [0.278, 0.420] | 0.125 | 0.44 |
| rb_count_items_listed | jlens | 52/raw | 8 | 168 | 0.393 [0.322, 0.468] | 0.125 | 0.35 |
| rb_count_items_listed | jlens | 56/raw | 8 | 168 | 0.351 [0.283, 0.426] | 0.125 | 0.39 |
| rb_count_items_listed | jlens | 60/raw | 8 | 168 | 0.214 [0.159, 0.282] | 0.125 | 0.77 |
| rb_count_items_listed | nla | 42/chat | 8 | 168 | 0.637 [0.562, 0.706] | 0.125 | 0.23 |
| rb_count_items_listed | nla | 42/raw | 8 | 168 | 0.649 [0.574, 0.717] | 0.125 | 0.20 |
| rb_count_items_listed | olens (community) | 42/chat | 8 | 168 | 0.220 [0.164, 0.289] | 0.125 | 0.89 |
| rb_count_items_listed | olens (community) | 44/chat | 8 | 168 | 0.155 [0.108, 0.217] | 0.125 | 0.97 |
| rb_count_items_listed | olens (community) | 48/chat | 8 | 168 | 0.310 [0.245, 0.383] | 0.125 | 0.78 |
| rb_count_items_listed | olens (community) | 52/chat | 8 | 168 | 0.333 [0.266, 0.408] | 0.125 | 0.79 |
| rb_count_items_listed | olens (community) | 56/chat | 8 | 168 | 0.476 [0.402, 0.551] | 0.125 | 0.48 |
| rb_count_items_listed | olens (community) | 42/raw | 8 | 168 | 0.393 [0.322, 0.468] | 0.125 | 0.38 |
| rb_count_items_listed | olens (community) | 44/raw | 8 | 168 | 0.470 [0.396, 0.546] | 0.125 | 0.30 |
| rb_count_items_listed | olens (community) | 48/raw | 8 | 168 | 0.655 [0.580, 0.722] | 0.125 | 0.26 |
| rb_count_items_listed | olens (community) | 52/raw | 8 | 168 | 0.613 [0.538, 0.683] | 0.125 | 0.20 |
| rb_count_items_listed | olens (community) | 56/raw | 8 | 168 | 0.494 [0.419, 0.569] | 0.125 | 0.29 |
| rb_count_items_listed | prompt_only | — | 8 | 168 | 1.000 [0.978, 1.000] | 0.125 | — |
| rb_count_items_listed | skip_a | 42/chat | 8 | 168 | 0.125 [0.083, 0.184] | 0.125 | 1.00 |
| rb_count_items_listed | skip_a | 42/raw | 8 | 168 | 0.208 [0.154, 0.276] | 0.125 | 0.77 |
| rb_meta_question_type_3 | jlens | 24/chat | 2 | 132 | 0.333 [0.259, 0.417] | 0.500 | 1.00 |
| rb_meta_question_type_3 | jlens | 28/chat | 2 | 132 | 0.333 [0.259, 0.417] | 0.500 | 1.00 |
| rb_meta_question_type_3 | jlens | 32/chat | 2 | 132 | 0.470 [0.387, 0.554] | 0.500 | 0.80 |
| rb_meta_question_type_3 | jlens | 36/chat | 2 | 132 | 0.333 [0.259, 0.417] | 0.500 | 1.00 |
| rb_meta_question_type_3 | jlens | 38/chat | 2 | 132 | 0.333 [0.259, 0.417] | 0.500 | 1.00 |
| rb_meta_question_type_3 | jlens | 40/chat | 2 | 132 | 0.333 [0.259, 0.417] | 0.500 | 1.00 |
| rb_meta_question_type_3 | jlens | 42/chat | 2 | 132 | 0.333 [0.259, 0.417] | 0.500 | 1.00 |
| rb_meta_question_type_3 | jlens | 44/chat | 2 | 132 | 0.356 [0.280, 0.441] | 0.500 | 0.97 |
| rb_meta_question_type_3 | jlens | 48/chat | 2 | 132 | 0.348 [0.273, 0.433] | 0.500 | 0.97 |
| rb_meta_question_type_3 | jlens | 52/chat | 2 | 132 | 0.545 [0.460, 0.628] | 0.500 | 0.63 |
| rb_meta_question_type_3 | jlens | 56/chat | 2 | 132 | 0.545 [0.460, 0.628] | 0.500 | 0.79 |
| rb_meta_question_type_3 | jlens | 60/chat | 2 | 132 | 0.341 [0.266, 0.425] | 0.500 | 0.99 |
| rb_meta_question_type_3 | jlens | 24/raw | 2 | 132 | 0.394 [0.315, 0.479] | 0.500 | 0.84 |
| rb_meta_question_type_3 | jlens | 28/raw | 2 | 132 | 0.341 [0.266, 0.425] | 0.500 | 0.98 |
| rb_meta_question_type_3 | jlens | 32/raw | 2 | 132 | 0.341 [0.266, 0.425] | 0.500 | 0.99 |
| rb_meta_question_type_3 | jlens | 36/raw | 2 | 132 | 0.348 [0.273, 0.433] | 0.500 | 0.98 |
| rb_meta_question_type_3 | jlens | 38/raw | 2 | 132 | 0.348 [0.273, 0.433] | 0.500 | 0.98 |
| rb_meta_question_type_3 | jlens | 40/raw | 2 | 132 | 0.371 [0.294, 0.456] | 0.500 | 0.95 |
| rb_meta_question_type_3 | jlens | 42/raw | 2 | 132 | 0.417 [0.336, 0.502] | 0.500 | 0.89 |
| rb_meta_question_type_3 | jlens | 44/raw | 2 | 132 | 0.364 [0.287, 0.448] | 0.500 | 0.97 |
| rb_meta_question_type_3 | jlens | 48/raw | 2 | 132 | 0.439 [0.358, 0.525] | 0.500 | 0.86 |
| rb_meta_question_type_3 | jlens | 52/raw | 2 | 132 | 0.500 [0.416, 0.584] | 0.500 | 0.73 |
| rb_meta_question_type_3 | jlens | 56/raw | 2 | 132 | 0.598 [0.513, 0.678] | 0.500 | 0.64 |
| rb_meta_question_type_3 | jlens | 60/raw | 2 | 132 | 0.644 [0.559, 0.720] | 0.500 | 0.56 |
| rb_meta_question_type_3 | nla | 42/chat | 3 | 132 | 0.735 [0.654, 0.803] | 0.333 | 0.56 |
| rb_meta_question_type_3 | nla | 42/raw | 3 | 132 | 0.735 [0.654, 0.803] | 0.333 | 0.58 |
| rb_meta_question_type_3 | olens (community) | 42/chat | 3 | 132 | 0.667 [0.583, 0.741] | 0.333 | 0.61 |
| rb_meta_question_type_3 | olens (community) | 44/chat | 3 | 132 | 0.576 [0.490, 0.657] | 0.333 | 0.66 |
| rb_meta_question_type_3 | olens (community) | 48/chat | 3 | 132 | 0.636 [0.552, 0.713] | 0.333 | 0.61 |
| rb_meta_question_type_3 | olens (community) | 52/chat | 3 | 132 | 0.765 [0.686, 0.829] | 0.333 | 0.43 |
| rb_meta_question_type_3 | olens (community) | 56/chat | 3 | 132 | 0.902 [0.839, 0.942] | 0.333 | 0.40 |
| rb_meta_question_type_3 | olens (community) | 42/raw | 3 | 132 | 1.000 [0.972, 1.000] | 0.333 | 0.33 |
| rb_meta_question_type_3 | olens (community) | 44/raw | 3 | 132 | 0.939 [0.885, 0.969] | 0.333 | 0.39 |
| rb_meta_question_type_3 | olens (community) | 48/raw | 3 | 132 | 0.970 [0.925, 0.988] | 0.333 | 0.36 |
| rb_meta_question_type_3 | olens (community) | 52/raw | 3 | 132 | 0.803 [0.727, 0.862] | 0.333 | 0.52 |
| rb_meta_question_type_3 | olens (community) | 56/raw | 3 | 132 | 0.902 [0.839, 0.942] | 0.333 | 0.37 |
| rb_meta_question_type_3 | prompt_only | — | 3 | 132 | 1.000 [0.972, 1.000] | 0.333 | — |
| rb_meta_question_type_3 | skip_a | 42/chat | 3 | 132 | 0.795 [0.719, 0.855] | 0.333 | 0.49 |
| rb_meta_question_type_3 | skip_a | 42/raw | 3 | 132 | 0.947 [0.895, 0.974] | 0.333 | 0.36 |
| rb_topic_news_8 | jlens | 24/chat | 8 | 168 | 0.321 [0.255, 0.395] | 0.125 | 0.60 |
| rb_topic_news_8 | jlens | 28/chat | 8 | 168 | 0.369 [0.300, 0.444] | 0.125 | 0.58 |
| rb_topic_news_8 | jlens | 32/chat | 8 | 168 | 0.506 [0.431, 0.581] | 0.125 | 0.38 |
| rb_topic_news_8 | jlens | 36/chat | 8 | 168 | 0.583 [0.508, 0.655] | 0.125 | 0.33 |
| rb_topic_news_8 | jlens | 38/chat | 8 | 168 | 0.595 [0.520, 0.667] | 0.125 | 0.36 |
| rb_topic_news_8 | jlens | 40/chat | 8 | 168 | 0.625 [0.550, 0.695] | 0.125 | 0.27 |
| rb_topic_news_8 | jlens | 42/chat | 8 | 168 | 0.756 [0.686, 0.815] | 0.125 | 0.30 |
| rb_topic_news_8 | jlens | 44/chat | 8 | 168 | 0.673 [0.598, 0.739] | 0.125 | 0.35 |
| rb_topic_news_8 | jlens | 48/chat | 8 | 168 | 0.619 [0.544, 0.689] | 0.125 | 0.28 |
| rb_topic_news_8 | jlens | 52/chat | 8 | 168 | 0.661 [0.586, 0.728] | 0.125 | 0.26 |
| rb_topic_news_8 | jlens | 56/chat | 8 | 168 | 0.649 [0.574, 0.717] | 0.125 | 0.39 |
| rb_topic_news_8 | jlens | 60/chat | 8 | 168 | 0.827 [0.763, 0.877] | 0.125 | 0.23 |
| rb_topic_news_8 | jlens | 24/raw | 8 | 168 | 0.696 [0.623, 0.761] | 0.125 | 0.24 |
| rb_topic_news_8 | jlens | 28/raw | 8 | 168 | 0.774 [0.705, 0.831] | 0.125 | 0.20 |
| rb_topic_news_8 | jlens | 32/raw | 8 | 168 | 0.661 [0.586, 0.728] | 0.125 | 0.32 |
| rb_topic_news_8 | jlens | 36/raw | 8 | 168 | 0.869 [0.810, 0.912] | 0.125 | 0.20 |
| rb_topic_news_8 | jlens | 38/raw | 8 | 168 | 0.893 [0.837, 0.931] | 0.125 | 0.19 |
| rb_topic_news_8 | jlens | 40/raw | 8 | 168 | 0.940 [0.894, 0.967] | 0.125 | 0.18 |
| rb_topic_news_8 | jlens | 42/raw | 8 | 168 | 0.940 [0.894, 0.967] | 0.125 | 0.18 |
| rb_topic_news_8 | jlens | 44/raw | 8 | 168 | 0.964 [0.924, 0.984] | 0.125 | 0.15 |
| rb_topic_news_8 | jlens | 48/raw | 8 | 168 | 0.964 [0.924, 0.984] | 0.125 | 0.14 |
| rb_topic_news_8 | jlens | 52/raw | 8 | 168 | 0.964 [0.924, 0.984] | 0.125 | 0.14 |
| rb_topic_news_8 | jlens | 56/raw | 8 | 168 | 0.958 [0.917, 0.980] | 0.125 | 0.16 |
| rb_topic_news_8 | jlens | 60/raw | 8 | 168 | 0.833 [0.770, 0.882] | 0.125 | 0.29 |
| rb_topic_news_8 | nla | 42/chat | 8 | 168 | 0.649 [0.574, 0.717] | 0.125 | 0.29 |
| rb_topic_news_8 | nla | 42/raw | 8 | 168 | 0.857 [0.796, 0.902] | 0.125 | 0.22 |
| rb_topic_news_8 | olens (community) | 42/chat | 8 | 168 | 0.256 [0.196, 0.327] | 0.125 | 0.77 |
| rb_topic_news_8 | olens (community) | 44/chat | 8 | 168 | 0.286 [0.223, 0.358] | 0.125 | 0.71 |
| rb_topic_news_8 | olens (community) | 48/chat | 8 | 168 | 0.238 [0.180, 0.308] | 0.125 | 0.67 |
| rb_topic_news_8 | olens (community) | 52/chat | 8 | 168 | 0.256 [0.196, 0.327] | 0.125 | 0.43 |
| rb_topic_news_8 | olens (community) | 56/chat | 8 | 168 | 0.381 [0.311, 0.456] | 0.125 | 0.43 |
| rb_topic_news_8 | olens (community) | 42/raw | 8 | 168 | 0.679 [0.605, 0.745] | 0.125 | 0.45 |
| rb_topic_news_8 | olens (community) | 44/raw | 8 | 168 | 0.714 [0.642, 0.777] | 0.125 | 0.41 |
| rb_topic_news_8 | olens (community) | 48/raw | 8 | 168 | 0.768 [0.698, 0.825] | 0.125 | 0.36 |
| rb_topic_news_8 | olens (community) | 52/raw | 8 | 168 | 0.738 [0.667, 0.799] | 0.125 | 0.34 |
| rb_topic_news_8 | olens (community) | 56/raw | 8 | 168 | 0.833 [0.770, 0.882] | 0.125 | 0.23 |
| rb_topic_news_8 | prompt_only | — | 8 | 168 | 1.000 [0.978, 1.000] | 0.125 | — |
| rb_topic_news_8 | skip_a | 42/chat | 8 | 168 | 0.429 [0.356, 0.504] | 0.125 | 0.60 |
| rb_topic_news_8 | skip_a | 42/raw | 8 | 168 | 0.821 [0.757, 0.872] | 0.125 | 0.18 |
| rb_topic_tweet_emotion_4 | jlens | 24/chat | 4 | 152 | 0.434 [0.358, 0.514] | 0.250 | 0.59 |
| rb_topic_tweet_emotion_4 | jlens | 28/chat | 4 | 152 | 0.500 [0.421, 0.579] | 0.250 | 0.75 |
| rb_topic_tweet_emotion_4 | jlens | 32/chat | 4 | 152 | 0.507 [0.428, 0.585] | 0.250 | 0.74 |
| rb_topic_tweet_emotion_4 | jlens | 36/chat | 4 | 152 | 0.539 [0.460, 0.617] | 0.250 | 0.71 |
| rb_topic_tweet_emotion_4 | jlens | 38/chat | 4 | 152 | 0.697 [0.620, 0.765] | 0.250 | 0.55 |
| rb_topic_tweet_emotion_4 | jlens | 40/chat | 4 | 152 | 0.684 [0.607, 0.753] | 0.250 | 0.57 |
| rb_topic_tweet_emotion_4 | jlens | 42/chat | 4 | 152 | 0.625 [0.546, 0.698] | 0.250 | 0.62 |
| rb_topic_tweet_emotion_4 | jlens | 44/chat | 4 | 152 | 0.618 [0.539, 0.692] | 0.250 | 0.63 |
| rb_topic_tweet_emotion_4 | jlens | 48/chat | 4 | 152 | 0.592 [0.513, 0.667] | 0.250 | 0.66 |
| rb_topic_tweet_emotion_4 | jlens | 52/chat | 4 | 152 | 0.566 [0.486, 0.642] | 0.250 | 0.68 |
| rb_topic_tweet_emotion_4 | jlens | 56/chat | 4 | 152 | 0.638 [0.559, 0.710] | 0.250 | 0.61 |
| rb_topic_tweet_emotion_4 | jlens | 60/chat | 4 | 152 | 0.888 [0.828, 0.929] | 0.250 | 0.36 |
| rb_topic_tweet_emotion_4 | jlens | 24/raw | 4 | 152 | 0.316 [0.247, 0.393] | 0.250 | 0.61 |
| rb_topic_tweet_emotion_4 | jlens | 28/raw | 4 | 152 | 0.342 [0.271, 0.421] | 0.250 | 0.74 |
| rb_topic_tweet_emotion_4 | jlens | 32/raw | 4 | 152 | 0.368 [0.296, 0.447] | 0.250 | 0.72 |
| rb_topic_tweet_emotion_4 | jlens | 36/raw | 4 | 152 | 0.500 [0.421, 0.579] | 0.250 | 0.63 |
| rb_topic_tweet_emotion_4 | jlens | 38/raw | 4 | 152 | 0.467 [0.390, 0.546] | 0.250 | 0.66 |
| rb_topic_tweet_emotion_4 | jlens | 40/raw | 4 | 152 | 0.434 [0.358, 0.514] | 0.250 | 0.73 |
| rb_topic_tweet_emotion_4 | jlens | 42/raw | 4 | 152 | 0.395 [0.321, 0.474] | 0.250 | 0.78 |
| rb_topic_tweet_emotion_4 | jlens | 44/raw | 4 | 152 | 0.408 [0.333, 0.487] | 0.250 | 0.76 |
| rb_topic_tweet_emotion_4 | jlens | 48/raw | 4 | 152 | 0.428 [0.352, 0.507] | 0.250 | 0.72 |
| rb_topic_tweet_emotion_4 | jlens | 52/raw | 4 | 152 | 0.579 [0.499, 0.655] | 0.250 | 0.61 |
| rb_topic_tweet_emotion_4 | jlens | 56/raw | 4 | 152 | 0.566 [0.486, 0.642] | 0.250 | 0.66 |
| rb_topic_tweet_emotion_4 | jlens | 60/raw | 4 | 152 | 0.684 [0.607, 0.753] | 0.250 | 0.54 |
| rb_topic_tweet_emotion_4 | nla | 42/chat | 4 | 152 | 1.000 [0.975, 1.000] | 0.250 | 0.25 |
| rb_topic_tweet_emotion_4 | nla | 42/raw | 4 | 152 | 0.908 [0.851, 0.944] | 0.250 | 0.31 |
| rb_topic_tweet_emotion_4 | olens (community) | 42/chat | 4 | 152 | 0.743 [0.669, 0.806] | 0.250 | 0.51 |
| rb_topic_tweet_emotion_4 | olens (community) | 44/chat | 4 | 152 | 0.750 [0.676, 0.812] | 0.250 | 0.50 |
| rb_topic_tweet_emotion_4 | olens (community) | 48/chat | 4 | 152 | 0.750 [0.676, 0.812] | 0.250 | 0.50 |
| rb_topic_tweet_emotion_4 | olens (community) | 52/chat | 4 | 152 | 0.757 [0.683, 0.818] | 0.250 | 0.49 |
| rb_topic_tweet_emotion_4 | olens (community) | 56/chat | 4 | 152 | 0.757 [0.683, 0.818] | 0.250 | 0.49 |
| rb_topic_tweet_emotion_4 | olens (community) | 42/raw | 4 | 152 | 0.526 [0.447, 0.604] | 0.250 | 0.54 |
| rb_topic_tweet_emotion_4 | olens (community) | 44/raw | 4 | 152 | 0.526 [0.447, 0.604] | 0.250 | 0.51 |
| rb_topic_tweet_emotion_4 | olens (community) | 48/raw | 4 | 152 | 0.461 [0.383, 0.540] | 0.250 | 0.64 |
| rb_topic_tweet_emotion_4 | olens (community) | 52/raw | 4 | 152 | 0.480 [0.402, 0.559] | 0.250 | 0.63 |
| rb_topic_tweet_emotion_4 | olens (community) | 56/raw | 4 | 152 | 0.487 [0.409, 0.566] | 0.250 | 0.59 |
| rb_topic_tweet_emotion_4 | prompt_only | — | 4 | 152 | 1.000 [0.975, 1.000] | 0.250 | — |
| rb_topic_tweet_emotion_4 | skip_a | 42/chat | 4 | 152 | 0.954 [0.908, 0.978] | 0.250 | 0.30 |
| rb_topic_tweet_emotion_4 | skip_a | 42/raw | 4 | 152 | 0.730 [0.655, 0.795] | 0.250 | 0.30 |

## Other facts

Natural test AUROC at the reader's primary site [item-bootstrap 95% CI]; Δ = reader − prompt-only (paired); exceed = Δ ≥ +0.05 with CI > 0 (raw, no BH); shuffled gate = shuffled cell's CI ∋ 0.5.

| tag | fact | reader | site | n | AUROC [CI] | prompt-only | Δ [CI] | exceed | probe(512) | ≥ 0.8×probe | shuffled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| COMPUTED | rb_computed_comparison | jlens | 42/chat | 192 | 0.565 [0.489, 0.644] | 1.000 | -0.435 [-0.511, -0.356] |  | 1.000 | no | pass |
| COMPUTED | rb_computed_comparison | nla | 42/chat | 192 | 0.711 [0.634, 0.777] | 1.000 | -0.289 [-0.366, -0.223] |  | 1.000 | no | pass |
| COMPUTED | rb_computed_comparison | olens (community) | 44/chat | 192 | 0.840 [0.786, 0.888] | 1.000 | -0.160 [-0.214, -0.112] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_comparison | skip_a | 42/chat | 192 | 0.889 [0.846, 0.931] | 1.000 | -0.111 [-0.154, -0.069] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_difference_sign | jlens | 42/chat | 196 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_difference_sign | nla | 42/chat | 196 | 0.952 [0.923, 0.979] | 1.000 | -0.048 [-0.077, -0.021] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_difference_sign | olens (community) | 44/chat | 196 | 0.998 [0.996, 1.000] | 1.000 | -0.002 [-0.004, +0.000] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_difference_sign | skip_a | 42/chat | 196 | 0.998 [0.993, 1.000] | 1.000 | -0.002 [-0.007, +0.000] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_sum_carry | jlens | 42/chat | 146 | 0.709 [0.617, 0.794] | 0.842 | -0.133 [-0.214, -0.062] |  | 0.962 | no | pass |
| COMPUTED | rb_computed_sum_carry | nla | 42/chat | 146 | 0.421 [0.332, 0.515] | 0.842 | -0.421 [-0.538, -0.295] |  | 0.962 | no | FAIL |
| COMPUTED | rb_computed_sum_carry | olens (community) | 44/chat | 146 | 0.612 [0.520, 0.703] | 0.842 | -0.230 [-0.330, -0.147] |  | 0.962 | no | pass |
| COMPUTED | rb_computed_sum_carry | skip_a | 42/chat | 146 | 0.564 [0.464, 0.665] | 0.842 | -0.278 [-0.379, -0.174] |  | 0.962 | no | pass |
| COMPUTED | rb_computed_sum_parity | jlens | 42/chat | 152 | 0.469 [0.378, 0.560] | 0.993 | -0.523 [-0.615, -0.430] |  | 0.923 | no | pass |
| COMPUTED | rb_computed_sum_parity | nla | 42/chat | 152 | 0.434 [0.348, 0.529] | 0.993 | -0.559 [-0.645, -0.464] |  | 0.923 | no | pass |
| COMPUTED | rb_computed_sum_parity | olens (community) | 44/chat | 152 | 0.496 [0.410, 0.593] | 0.993 | -0.497 [-0.583, -0.394] |  | 0.923 | no | pass |
| COMPUTED | rb_computed_sum_parity | skip_a | 42/chat | 152 | 0.414 [0.321, 0.514] | 0.993 | -0.578 [-0.672, -0.476] |  | 0.923 | no | pass |
| COMPUTED | rb_computed_syllogism_valid | jlens | 42/chat | 140 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_syllogism_valid | nla | 42/chat | 140 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_syllogism_valid | olens (community) | 44/chat | 140 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_syllogism_valid | skip_a | 42/chat | 140 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| COMPUTED | rb_computed_weekday_weekend | jlens | 42/chat | 154 | 0.450 [0.360, 0.538] | 0.667 | -0.217 [-0.333, -0.101] |  | 0.485 | yes | pass |
| COMPUTED | rb_computed_weekday_weekend | nla | 42/chat | 154 | 0.451 [0.364, 0.537] | 0.667 | -0.216 [-0.325, -0.105] |  | 0.485 | yes | pass |
| COMPUTED | rb_computed_weekday_weekend | olens (community) | 44/chat | 154 | 0.447 [0.360, 0.532] | 0.667 | -0.220 [-0.349, -0.096] |  | 0.485 | yes | FAIL |
| COMPUTED | rb_computed_weekday_weekend | skip_a | 42/chat | 154 | 0.543 [0.452, 0.638] | 0.667 | -0.124 [-0.255, -0.009] |  | 0.485 | yes | pass |
| CONTEXT | rb_context_against_belief (model label; defect prevalence 0% of 110 labelled, 0 dropped) | jlens | 42/chat | 47 | 0.393 [0.247, 0.561] | 1.000 | -0.607 [-0.753, -0.439] |  | — | — | FAIL |
| CONTEXT | rb_context_against_belief (model label; defect prevalence 0% of 110 labelled, 0 dropped) | nla | 42/chat | 110 | 0.026 [0.009, 0.057] | 1.000 | -0.974 [-0.991, -0.943] |  | — | — | FAIL |
| CONTEXT | rb_context_against_belief (model label; defect prevalence 0% of 110 labelled, 0 dropped) | olens (community) | 44/chat | 110 | 0.085 [0.043, 0.137] | 1.000 | -0.915 [-0.957, -0.863] |  | — | — | FAIL |
| CONTEXT | rb_context_against_belief (model label; defect prevalence 0% of 110 labelled, 0 dropped) | skip_a | 42/chat | 110 | 0.085 [0.040, 0.143] | 1.000 | -0.915 [-0.960, -0.857] |  | — | — | FAIL |
| CONTEXT | rb_context_earlier_turn | jlens | 42/chat | 118 | 0.482 [0.372, 0.594] | 1.000 | -0.518 [-0.628, -0.406] |  | — | — | pass |
| CONTEXT | rb_context_earlier_turn | nla | 42/chat | 118 | 0.569 [0.461, 0.669] | 1.000 | -0.431 [-0.539, -0.331] |  | — | — | pass |
| CONTEXT | rb_context_earlier_turn | olens (community) | 44/chat | 118 | 0.803 [0.714, 0.877] | 1.000 | -0.197 [-0.286, -0.123] |  | — | — | pass |
| CONTEXT | rb_context_earlier_turn | skip_a | 42/chat | 118 | 0.706 [0.607, 0.800] | 1.000 | -0.294 [-0.393, -0.200] |  | — | — | pass |
| CONTEXT | rb_context_system_fact | jlens | 42/chat | 120 | 0.594 [0.496, 0.692] | 1.000 | -0.406 [-0.504, -0.308] |  | — | — | pass |
| CONTEXT | rb_context_system_fact | nla | 42/chat | 120 | 0.389 [0.282, 0.490] | 1.000 | -0.611 [-0.718, -0.510] |  | — | — | pass |
| CONTEXT | rb_context_system_fact | olens (community) | 44/chat | 120 | 0.749 [0.654, 0.833] | 1.000 | -0.251 [-0.346, -0.167] |  | — | — | pass |
| CONTEXT | rb_context_system_fact | skip_a | 42/chat | 120 | 0.571 [0.468, 0.679] | 1.000 | -0.429 [-0.532, -0.321] |  | — | — | pass |
| FORM | rb_form_grammatical | jlens | 42/chat | 148 | 0.137 [0.084, 0.197] | 0.998 | -0.861 [-0.915, -0.803] |  | 1.000 | no | pass |
| FORM | rb_form_grammatical | nla | 42/chat | 148 | 0.797 [0.731, 0.862] | 0.998 | -0.201 [-0.267, -0.137] |  | 1.000 | no | pass |
| FORM | rb_form_grammatical | olens (community) | 44/chat | 148 | 0.460 [0.372, 0.548] | 0.998 | -0.538 [-0.627, -0.450] |  | 1.000 | no | pass |
| FORM | rb_form_grammatical | skip_a | 42/chat | 148 | 0.106 [0.061, 0.160] | 0.998 | -0.892 [-0.938, -0.837] |  | 1.000 | no | pass |
| FORM | rb_form_negation | jlens | 42/chat | 160 | 0.506 [0.409, 0.594] | 1.000 | -0.494 [-0.591, -0.406] |  | 1.000 | no | pass |
| FORM | rb_form_negation | nla | 42/chat | 160 | 0.842 [0.778, 0.902] | 1.000 | -0.158 [-0.222, -0.098] |  | 1.000 | yes | pass |
| FORM | rb_form_negation | olens (community) | 44/chat | 160 | 0.600 [0.502, 0.690] | 1.000 | -0.400 [-0.498, -0.310] |  | 1.000 | no | pass |
| FORM | rb_form_negation | skip_a | 42/chat | 160 | 0.721 [0.636, 0.801] | 1.000 | -0.279 [-0.364, -0.199] |  | 1.000 | no | pass |
| FORM | rb_form_person | jlens | 42/chat | 154 | 0.764 [0.691, 0.838] | 1.000 | -0.236 [-0.309, -0.162] |  | 1.000 | no | pass |
| FORM | rb_form_person | nla | 42/chat | 154 | 0.404 [0.316, 0.509] | 1.000 | -0.596 [-0.684, -0.491] |  | 1.000 | no | pass |
| FORM | rb_form_person | olens (community) | 44/chat | 154 | 0.686 [0.603, 0.768] | 1.000 | -0.314 [-0.397, -0.232] |  | 1.000 | no | pass |
| FORM | rb_form_person | skip_a | 42/chat | 154 | 0.598 [0.507, 0.687] | 1.000 | -0.402 [-0.493, -0.313] |  | 1.000 | no | pass |
| FORM | rb_form_question_vs_statement | jlens | 42/chat | 144 | 1.000 [0.999, 1.000] | 1.000 | -0.000 [-0.001, +0.000] |  | 1.000 | yes | pass |
| FORM | rb_form_question_vs_statement | nla | 42/chat | 144 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| FORM | rb_form_question_vs_statement | olens (community) | 44/chat | 144 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| FORM | rb_form_question_vs_statement | skip_a | 42/chat | 144 | 0.997 [0.989, 1.000] | 1.000 | -0.003 [-0.011, +0.000] |  | 1.000 | yes | pass |
| FORM | rb_form_register | jlens | 42/chat | 152 | 0.943 [0.911, 0.973] | 1.000 | -0.057 [-0.089, -0.027] |  | 1.000 | yes | FAIL |
| FORM | rb_form_register | nla | 42/chat | 152 | 0.999 [0.998, 1.000] | 1.000 | -0.001 [-0.002, +0.000] |  | 1.000 | yes | FAIL |
| FORM | rb_form_register | olens (community) | 44/chat | 152 | 0.980 [0.962, 0.994] | 1.000 | -0.020 [-0.038, -0.006] |  | 1.000 | yes | pass |
| FORM | rb_form_register | skip_a | 42/chat | 152 | 0.888 [0.836, 0.931] | 1.000 | -0.112 [-0.164, -0.069] |  | 1.000 | yes | pass |
| FORM | rb_form_voice | jlens | 42/chat | 156 | 0.881 [0.822, 0.935] | 1.000 | -0.119 [-0.178, -0.065] |  | 1.000 | yes | pass |
| FORM | rb_form_voice | nla | 42/chat | 156 | 0.588 [0.490, 0.684] | 1.000 | -0.412 [-0.510, -0.316] |  | 1.000 | no | pass |
| FORM | rb_form_voice | olens (community) | 44/chat | 156 | 0.561 [0.471, 0.649] | 1.000 | -0.439 [-0.529, -0.351] |  | 1.000 | no | pass |
| FORM | rb_form_voice | skip_a | 42/chat | 156 | 0.721 [0.639, 0.800] | 1.000 | -0.279 [-0.361, -0.200] |  | 1.000 | no | pass |
| KNOWLEDGE | rb_knowledge_animal_class | jlens | 42/chat | 144 | 0.662 [0.574, 0.741] | 1.000 | -0.338 [-0.426, -0.259] |  | 0.978 | no | pass |
| KNOWLEDGE | rb_knowledge_animal_class | nla | 42/chat | 144 | 0.827 [0.752, 0.889] | 1.000 | -0.173 [-0.248, -0.111] |  | 0.978 | yes | pass |
| KNOWLEDGE | rb_knowledge_animal_class | olens (community) | 44/chat | 144 | 0.819 [0.752, 0.880] | 1.000 | -0.181 [-0.248, -0.120] |  | 0.978 | yes | FAIL |
| KNOWLEDGE | rb_knowledge_animal_class | skip_a | 42/chat | 144 | 0.893 [0.842, 0.937] | 1.000 | -0.107 [-0.158, -0.063] |  | 0.978 | yes | pass |
| KNOWLEDGE | rb_knowledge_city_is_capital | jlens | 42/chat | 176 | 0.553 [0.468, 0.642] | 1.000 | -0.447 [-0.531, -0.358] |  | 0.987 | no | pass |
| KNOWLEDGE | rb_knowledge_city_is_capital | nla | 42/chat | 176 | 0.564 [0.478, 0.647] | 1.000 | -0.436 [-0.522, -0.353] |  | 0.987 | no | pass |
| KNOWLEDGE | rb_knowledge_city_is_capital | olens (community) | 44/chat | 176 | 0.612 [0.522, 0.695] | 1.000 | -0.388 [-0.478, -0.305] |  | 0.987 | no | pass |
| KNOWLEDGE | rb_knowledge_city_is_capital | skip_a | 42/chat | 176 | 0.539 [0.449, 0.622] | 1.000 | -0.461 [-0.550, -0.378] |  | 0.987 | no | pass |
| KNOWLEDGE | rb_knowledge_country_capital_distractor | jlens | 42/chat | 112 | 0.715 [0.620, 0.805] | 1.000 | -0.285 [-0.380, -0.195] |  | — | — | pass |
| KNOWLEDGE | rb_knowledge_country_capital_distractor | nla | 42/chat | 200 | 0.686 [0.607, 0.761] | 1.000 | -0.314 [-0.393, -0.239] |  | — | — | pass |
| KNOWLEDGE | rb_knowledge_country_capital_distractor | olens (community) | 44/chat | 200 | 0.850 [0.798, 0.906] | 1.000 | -0.150 [-0.202, -0.094] |  | — | — | pass |
| KNOWLEDGE | rb_knowledge_country_capital_distractor | skip_a | 42/chat | 200 | 0.860 [0.807, 0.907] | 1.000 | -0.140 [-0.193, -0.093] |  | — | — | FAIL |
| KNOWLEDGE | rb_knowledge_country_continent | jlens | 42/chat | 112 | 0.998 [0.993, 1.000] | 1.000 | -0.002 [-0.007, +0.000] |  | 0.999 | yes | pass |
| KNOWLEDGE | rb_knowledge_country_continent | nla | 42/chat | 112 | 0.990 [0.971, 1.000] | 1.000 | -0.010 [-0.029, +0.000] |  | 0.999 | yes | pass |
| KNOWLEDGE | rb_knowledge_country_continent | olens (community) | 44/chat | 112 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 0.999 | yes | pass |
| KNOWLEDGE | rb_knowledge_country_continent | skip_a | 42/chat | 112 | 1.000 [0.998, 1.000] | 1.000 | -0.000 [-0.002, +0.000] |  | 0.999 | yes | pass |
| KNOWLEDGE | rb_knowledge_element_metal | jlens | 42/chat | 112 | 0.670 [0.570, 0.758] | 1.000 | -0.330 [-0.430, -0.242] |  | 0.721 | yes | pass |
| KNOWLEDGE | rb_knowledge_element_metal | nla | 42/chat | 112 | 0.681 [0.585, 0.781] | 1.000 | -0.319 [-0.415, -0.219] |  | 0.721 | yes | pass |
| KNOWLEDGE | rb_knowledge_element_metal | olens (community) | 44/chat | 112 | 0.799 [0.715, 0.874] | 1.000 | -0.201 [-0.285, -0.126] |  | 0.721 | yes | pass |
| KNOWLEDGE | rb_knowledge_element_metal | skip_a | 42/chat | 112 | 0.798 [0.709, 0.870] | 1.000 | -0.202 [-0.291, -0.130] |  | 0.721 | yes | pass |
| KNOWLEDGE | rb_knowledge_figure_field | jlens | 42/chat | 144 | 0.992 [0.984, 0.999] | 1.000 | -0.008 [-0.016, -0.001] |  | 1.000 | yes | pass |
| KNOWLEDGE | rb_knowledge_figure_field | nla | 42/chat | 144 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| KNOWLEDGE | rb_knowledge_figure_field | olens (community) | 44/chat | 144 | 1.000 [1.000, 1.000] | 1.000 | -0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| KNOWLEDGE | rb_knowledge_figure_field | skip_a | 42/chat | 144 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| KNOWLEDGE | rb_knowledge_landmark_country_distractor | jlens | 42/chat | 139 | 0.861 [0.795, 0.922] | 1.000 | -0.139 [-0.205, -0.078] |  | — | — | pass |
| KNOWLEDGE | rb_knowledge_landmark_country_distractor | nla | 42/chat | 160 | 0.737 [0.653, 0.808] | 1.000 | -0.263 [-0.347, -0.192] |  | — | — | pass |
| KNOWLEDGE | rb_knowledge_landmark_country_distractor | olens (community) | 44/chat | 160 | 0.874 [0.817, 0.924] | 1.000 | -0.126 [-0.183, -0.076] |  | — | — | pass |
| KNOWLEDGE | rb_knowledge_landmark_country_distractor | skip_a | 42/chat | 160 | 0.809 [0.740, 0.866] | 1.000 | -0.191 [-0.260, -0.134] |  | — | — | pass |
| META | rb_meta_answer_format | jlens | 42/chat | 124 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | FAIL |
| META | rb_meta_answer_format | nla | 42/chat | 124 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| META | rb_meta_answer_format | olens (community) | 44/chat | 124 | 0.994 [0.987, 1.000] | 1.000 | -0.006 [-0.013, -0.000] |  | 1.000 | yes | FAIL |
| META | rb_meta_answer_format | skip_a | 42/chat | 124 | 0.995 [0.987, 1.000] | 1.000 | -0.005 [-0.013, -0.000] |  | 1.000 | yes | pass |
| META | rb_meta_instruction_present | jlens | 42/chat | 126 | 0.164 [0.092, 0.237] | 1.000 | -0.836 [-0.908, -0.763] |  | 1.000 | no | pass |
| META | rb_meta_instruction_present | nla | 42/chat | 126 | 0.961 [0.927, 0.988] | 1.000 | -0.039 [-0.073, -0.012] |  | 1.000 | yes | pass |
| META | rb_meta_instruction_present | olens (community) | 44/chat | 126 | 0.725 [0.640, 0.803] | 1.000 | -0.275 [-0.360, -0.197] |  | 1.000 | no | pass |
| META | rb_meta_instruction_present | skip_a | 42/chat | 126 | 0.929 [0.876, 0.968] | 1.000 | -0.071 [-0.124, -0.032] |  | 1.000 | yes | pass |
| META | rb_meta_why_vs_when | jlens | 42/chat | 142 | 0.861 [0.805, 0.918] | 1.000 | -0.139 [-0.195, -0.082] |  | 1.000 | yes | pass |
| META | rb_meta_why_vs_when | nla | 42/chat | 142 | 1.000 [0.999, 1.000] | 1.000 | -0.000 [-0.001, +0.000] |  | 1.000 | yes | pass |
| META | rb_meta_why_vs_when | olens (community) | 44/chat | 142 | 0.600 [0.507, 0.693] | 1.000 | -0.400 [-0.493, -0.307] |  | 1.000 | no | pass |
| META | rb_meta_why_vs_when | skip_a | 42/chat | 142 | 0.893 [0.839, 0.944] | 1.000 | -0.107 [-0.161, -0.056] |  | 1.000 | yes | pass |
| SURFACE | rb_surface_allcaps_word | jlens | 42/chat | 154 | 0.589 [0.490, 0.684] | 1.000 | -0.411 [-0.510, -0.316] |  | 0.991 | no | pass |
| SURFACE | rb_surface_allcaps_word | nla | 42/chat | 154 | 0.514 [0.427, 0.595] | 1.000 | -0.486 [-0.573, -0.405] |  | 0.991 | no | pass |
| SURFACE | rb_surface_allcaps_word | olens (community) | 44/chat | 154 | 0.519 [0.431, 0.603] | 1.000 | -0.481 [-0.569, -0.397] |  | 0.991 | no | pass |
| SURFACE | rb_surface_allcaps_word | skip_a | 42/chat | 154 | 0.474 [0.390, 0.565] | 1.000 | -0.526 [-0.610, -0.435] |  | 0.991 | no | pass |
| SURFACE | rb_surface_bigram_at_least | jlens | 42/chat | 140 | 0.446 [0.351, 0.545] | 1.000 | -0.554 [-0.649, -0.455] |  | 0.990 | no | pass |
| SURFACE | rb_surface_bigram_at_least | nla | 42/chat | 140 | 0.465 [0.372, 0.558] | 1.000 | -0.535 [-0.628, -0.442] |  | 0.990 | no | pass |
| SURFACE | rb_surface_bigram_at_least | olens (community) | 44/chat | 140 | 0.480 [0.376, 0.572] | 1.000 | -0.520 [-0.624, -0.428] |  | 0.990 | no | pass |
| SURFACE | rb_surface_bigram_at_least | skip_a | 42/chat | 140 | 0.397 [0.306, 0.492] | 1.000 | -0.603 [-0.694, -0.508] |  | 0.990 | no | pass |
| SURFACE | rb_surface_code_language | jlens | 42/chat | 138 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| SURFACE | rb_surface_code_language | nla | 42/chat | 138 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| SURFACE | rb_surface_code_language | olens (community) | 44/chat | 138 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| SURFACE | rb_surface_code_language | skip_a | 42/chat | 138 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| SURFACE | rb_surface_contains_digit | jlens | 42/chat | 146 | 0.819 [0.743, 0.883] | 1.000 | -0.181 [-0.257, -0.117] |  | 0.998 | yes | pass |
| SURFACE | rb_surface_contains_digit | nla | 42/chat | 146 | 0.709 [0.625, 0.798] | 1.000 | -0.291 [-0.374, -0.201] |  | 0.998 | no | pass |
| SURFACE | rb_surface_contains_digit | olens (community) | 44/chat | 146 | 0.479 [0.389, 0.588] | 1.000 | -0.521 [-0.611, -0.411] |  | 0.998 | no | pass |
| SURFACE | rb_surface_contains_digit | skip_a | 42/chat | 146 | 0.606 [0.509, 0.694] | 1.000 | -0.394 [-0.491, -0.306] |  | 0.998 | no | pass |
| SURFACE | rb_surface_word_count | jlens | 42/chat | 156 | 0.779 [0.697, 0.848] | 1.000 | -0.221 [-0.303, -0.152] |  | 1.000 | no | pass |
| SURFACE | rb_surface_word_count | nla | 42/chat | 156 | 0.186 [0.127, 0.253] | 1.000 | -0.814 [-0.873, -0.747] |  | 1.000 | no | pass |
| SURFACE | rb_surface_word_count | olens (community) | 44/chat | 156 | 0.648 [0.562, 0.736] | 1.000 | -0.352 [-0.438, -0.264] |  | 1.000 | no | pass |
| SURFACE | rb_surface_word_count | skip_a | 42/chat | 156 | 0.492 [0.403, 0.578] | 1.000 | -0.508 [-0.597, -0.422] |  | 1.000 | no | pass |
| TOPIC | rb_topic_is_health | jlens | 42/chat | 138 | 0.849 [0.783, 0.912] | 1.000 | -0.151 [-0.217, -0.088] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_is_health | nla | 42/chat | 138 | 0.931 [0.882, 0.970] | 1.000 | -0.069 [-0.118, -0.030] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_is_health | olens (community) | 44/chat | 138 | 0.550 [0.460, 0.644] | 1.000 | -0.450 [-0.540, -0.356] |  | 1.000 | no | pass |
| TOPIC | rb_topic_is_health | skip_a | 42/chat | 138 | 0.623 [0.519, 0.721] | 1.000 | -0.377 [-0.481, -0.279] |  | 1.000 | no | pass |
| TOPIC | rb_topic_review_sentiment | jlens | 42/chat | 160 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_review_sentiment | nla | 42/chat | 160 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_review_sentiment | olens (community) | 44/chat | 160 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_review_sentiment | skip_a | 42/chat | 160 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_science_vs_business | jlens | 42/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_science_vs_business | nla | 42/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_science_vs_business | olens (community) | 44/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_science_vs_business | skip_a | 42/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_sports_vs_politics | jlens | 42/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_sports_vs_politics | nla | 42/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_sports_vs_politics | olens (community) | 44/chat | 114 | 0.858 [0.795, 0.916] | 1.000 | -0.142 [-0.205, -0.084] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_sports_vs_politics | skip_a | 42/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_tweet_joy_vs_anger | jlens | 42/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_tweet_joy_vs_anger | nla | 42/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_tweet_joy_vs_anger | olens (community) | 44/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
| TOPIC | rb_topic_tweet_joy_vs_anger | skip_a | 42/chat | 114 | 1.000 [1.000, 1.000] | 1.000 | +0.000 [+0.000, +0.000] |  | 1.000 | yes | pass |
