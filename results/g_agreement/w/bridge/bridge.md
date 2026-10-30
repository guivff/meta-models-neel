# Bridge — our 100 arithmetic prompts vs Michael Kenney's 600 (nla-consistency, Result 2)

Inputs: michael=nla-consistency/data/arithmetic.jsonl, items=projects/g_agreement/banks/w/items_w.json, states_dir=cache/g_agreement/w/states_L42, s1=cache/g_agreement/w/s1_target.jsonl, s3=cache/g_agreement/w/s3_lo.jsonl.
Michael's CIs are item-level bootstraps (1,000, seed 0) computed here from his released file (he states point estimates only).
Recomputed from his file: probe exact a 0.83, b 0.93; NLA exact a 0.05, b 0.38 (quote rate 1.00); r a 0.57, b 0.88 — README: 83–93 %, 5 %, 38 %, 0.57, 0.88.

| metric | Michael [95 % CI] | ours [95 % CI] | ours in his CI | CIs overlap | note |
|---|---|---|---|---|---|
| probe exact-match a | 0.83 [0.80, 0.86] | 0.24 [0.16, 0.32] | False | False | 5-fold softmax digit probes, both digits right; his n = 600, ours n = 100 |
| probe exact-match b | 0.93 [0.91, 0.95] | 0.48 [0.38, 0.57] | False | False | 5-fold softmax digit probes, both digits right; his n = 600, ours n = 100 |
| NLA exact-match a (free text) | 0.05 [0.03, 0.06] | – [–, –] | – | – | no counterpart: S4 did not sample free text on arith states; S3 NLA native vector ranges over the result (see nla_native) |
| NLA r (Pearson) a | 0.57 [0.52, 0.62] | – [–, –] | – | – | his 'r' is Pearson over quoting readouts |
| NLA Spearman a | 0.59 [0.53, 0.65] | – [–, –] | – | – |  |
| NLA exact-match b (free text) | 0.38 [0.34, 0.42] | – [–, –] | – | – | no counterpart: S4 did not sample free text on arith states; S3 NLA native vector ranges over the result (see nla_native) |
| NLA r (Pearson) b | 0.88 [0.86, 0.90] | – [–, –] | – | – | his 'r' is Pearson over quoting readouts |
| NLA Spearman b | 0.92 [0.91, 0.94] | – [–, –] | – | – |  |

Per-digit probe accuracy (majority baseline), ours vs his: a_tens 0.65 (0.17) vs 0.94 (0.12); a_units 0.33 (0.15) vs 0.88 (0.14); b_tens 0.63 (0.17) vs 0.94 (0.22); b_units 0.68 (0.18) vs 0.98 (0.12).
Sample-size control (same test folds; probes trained on n rows per fold → exact a / b, Wilson CI): n=20: 0.08 [0.04, 0.15] / 0.12 [0.07, 0.20]; n=40: 0.15 [0.09, 0.23] / 0.25 [0.18, 0.34]; n=60: 0.18 [0.12, 0.27] / 0.38 [0.29, 0.48]; n=80: 0.24 [0.17, 0.33] / 0.48 [0.38, 0.58] — his probes trained on 480 per fold (activations not released, so they cannot be refitted at our n).
Michael's recipe on all 100 states — subspace ranks: {'a|mean': 18, 'a|lr': 19, 'a|rand': 18, 'b|mean': 18, 'b|lr': 19, 'b|rand': 18} (his: 18 class-mean + 18 probe-weight per operand).
Native vector on arith, reader jlens: result exact 0.02 [0.00, 0.05], Spearman 0.50; argmax = a 0.00, = b 0.06 (n = 100).
Native vector on arith, reader olens: result exact 0.02 [0.00, 0.05], Spearman 0.44; argmax = a 0.00, = b 0.02 (n = 100).
Native vector on arith, reader skip_a: result exact 0.01 [0.00, 0.03], Spearman -0.22; argmax = a 0.00, = b 0.00 (n = 100).
- model greedy next token answers the arith prompt in 17/100 (plain format; Michael: 0.00 of 600).
- NLA native scores on the S1 arith states absent from S3 (phase B scored counts only unless extended): no NLA row for arith.
- Free-text NLA readouts of arith states were not sampled in S4 (counts and error states only), so Michael's NLA operand exact-match and r have no counterpart; the native vector reads the result, not a or b.
- Same base model (Qwen/Qwen3.6-27B), same NLA (ceselder/qwen3.6-27b-nla-rl, av_rl_adapters/iter_000400), same layer 42, plain prompt format and read position '=' as Michael; differences: our 100 triples (disjoint from his 600), our capture pipeline, n = 100 vs 600 (wider CIs), probe standardisation on 100 states.
