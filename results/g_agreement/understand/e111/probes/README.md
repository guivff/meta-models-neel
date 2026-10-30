# E111 §224 block-44 probe delivery

Eight sealed existing dev-fit probes; **zero new fits**, GPU/API calls, test-statistic computations or E111 analysis claims. These are saved E100 CPU fits on the original E56/E57/E59 unhooked dev captures, not newly reconstructed weights or CV-fold gate probes. Each fit has 84 dev items, 42 per class, dimension 5120; original bytes retained.

| Row | Original dev bank | Used by | Weights SHA256 |
|---|---|---|---|
| nesting_depth | E57 | E100a, E101 | 0cdebfe96570288a4c95cb50abb38ab72cd4b4f9a6248027d10478d682004010 |
| indent_level | E57 | E100a, E101 | 8160b5fca04fbc8cd16760edea37b2656c83fff8928e37d67bc36a965b7704f2 |
| page_range_digit | E57 | E100a, E101 | f5d0347dd2c9a2d673918d5c8bc74b7fc69d06ece33b0848cf602706820cf620 |
| format_plan | E59 | E100a, E101 | 8a24ea7d84cd67d0e353b8d6a6a9244cb84ae5957284c38d412beb9166548766 |
| language_plan | E59 | E100a, E101, E104_U, E109_fallback_if_own_probe_absent | d1352205641235d5a66fef82128ff427f8beb8bfd3abe604ac92e50d686fe2c5 |
| tense_implicit | E56 | E100a | e3731766959453730fa0382d40603c82bd5730fa21e84d406fd6d981749399ea |
| language_continuation | E56 | E100a, E101 | bfa3d90444893f6ad237cac737f616fdf064886965aa57d266a3d408ef36d6e9 |
| fact_recall | E56 | E100a, E101, E104_U, E109_fallback_if_own_probe_absent | 967467dad91a6374983a1add769190974651863c41b11fe942f04c7bb4ba4c0d |

Full source paths, original bank/capture seals and hashes, label-to-value maps, fit arithmetic, and dev identity digests are in PROBE_MANIFEST.json. Verified 44 pins, source dev-only membership and E101 source agreement; two synthetic tests verify class0/class1 target orientation and centering/intercept cancellation. No new test probe AUROC or outcome has been computed.

## Logit contract

`z1(h) = ((h − mu) / sd) @ w + b`; target class0 uses `−z1`. For E111, `x1 = (2*target_label − 1) * (h_intervened − h_natural) @ (w/sd)`. Use the target value’s source-bank class from the manifest, not an assumed A/B letter correspondence. Centering and intercept cancel in this paired difference. Preserve probe magnitude; unit-normalizing w, omitting sd or converting to probability would change x1. All four saved arrays are required. No label/private-join/probe file belongs in a pod or judge wire.

## E109 precedence and analysis gate

Own dev-fit probes not yet available in checked owner/canonical analysis paths; E109 analysis is pending sealed output. For E109 prefer its own block44 unhooked-dev probe once sealed; otherwise the exact E56/E59 unhooked-dev source probes above are the §224 fallback. Do not refit or silently swap after E111 execution. Bind selected artifact before E111 claim.

E109 uses different registered fit settings (unscaled sklearn C1/lbfgs/max_iter2000/seed0), so its own artifact must be explicitly named and hashed; never call a standardized E100 probe “E109’s own.” W-mech2 should freeze its per-experiment selection before the sole E111 analysis. Same-row source probes are ready now for the other experiments. E49 is not selected because no E49-native row occurs in this inventory; row-name similarity alone is not compatibility.

W-mech2 remains E111 owner. §224 requires synthetic-tested analysis code before E109 output and once-only execution after E109 seals, or Fri00:00CET without E109 explicitly excluded. This delivery does not consume that claim or alter confirmatory rules.
