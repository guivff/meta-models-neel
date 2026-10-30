# E111: E109-own unhooked dev probes at block 44

Two fits completed once on the original sealed E109 unhooked dev captures. Acquisition seal: ecaf7813b2baa57d7c210423cd1ca09a1d388af566ab6eacbeeb5384e8838bde; all429 original members verified. Fit code/plan62b98e9ff was committed before the exclusive fit claim. Each row uses all84 frozen dev items (42perclass), original order and labels. Captured metadata verifies hook_installed=false/injection_sites=[]; no test vectors or reader judgments were opened.

| Row | Weights SHA256 | Iterations |
|---|---|---:|
| fact_recall | 38b6cea968c1cdf8f5a6fd3e713367769e45ebe27d876219fa215822164388ac | 10 |
| language_plan | c053738f7530eb6de3aad2c04a0eca0f665d330aa4331bb1be3e9a6673ba20f2 | 45 |

Weights live in weights/<row>_probe.npz. NPZ keys: w (raw5120-vector), b (scalar), classes ([0,1]), n_iter. No feature normalization: z1=h@w+b; class1=A, class0=B, paired target x1=(2*target_class−1)*(h_intervened−h_natural)@w. Intercept cancels. No sd, unit normalization, sigmoid or test-selected orientation. Exact E109 fitter: sklearn LogisticRegression(C=1,max_iter=2000,random_state=0,solver=lbfgs), intercept/default regularization, no scaling or tuning. ConvergenceWarning fails closed.

For E111 choose E109-own probes per row for fact_recall/language_plan across experiments; the other six rows retain the prior sealed source-matched E56/E57/E59 probes. W-mech2 freezes this preferred selection before its separate once-only analysis. Do not refit these weights when E109 judging finishes. This probe fit is separate from E111 outcome regression and does not invoke E109 original analysis, rules, test probe scores or Oracle statistics.

Runtime: Python3.12.14, numpy2.5.4, sklearn1.9.1; 0.238028s CPU including input verification, GPU0. Two synthetic tests PASS. PROBE_MANIFEST contains devIDs and exact recipe/training/labels-order hashes. Full reference/label binding remains private in cache, with its path/hash in the manifest. Delivery copied/read back to W-mech2 cache/g_agreement/understand/e111/wlens_e109_dev44 and posted in its owner HANDOFF.

Ordered requests2–4: previously sealed E98 agreement, slide+indent and post hoc E80c outputs reverified by hashes only (COMPLETED_ITEMS_VERIFICATION.json). No completed analysis rerun. E98 author analysis af58cad34 (3REPORTED/20MISSED;18/23Jagreement); independent scientific review separate from R5b7fe68eb custody. Slideefb9df6df; indent four4/twelve0/neither80/84. E80c4b2b0df1f remains post hoc normalization, not an actual variance-matched intervention; R-X3 unchanged.
