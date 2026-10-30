**Prediction (§93):** Oracle continuations enact structure above chance (roughly AUROC 0.65–0.8) despite weak explicit description.

**Did it hold? No evidence for the predicted show-not-say dissociation in this run.** Oracle parentheses and table-column proxies are below chance in the frozen orientation; string is 0.512 and indent/list are exactly 0.500. NLA continued in its descriptive format on all 420 items, so these results do not establish its inability to enact under another interface.

# E6 continuation results — EXPLORATORY

840 sealed outputs: 5 rows × 84 test items × 2 readers; 42 per value, six held-out template clusters. AUROC uses the frozen proxy, neutral=0.5, fixed orientation and 2,000 cluster resamples. A is the first frozen value and B is the second; for depth/column rows B means deep/later rather than absence.

The event rate below is **proxy score exactly 1**, divided by all 42 outputs in the given state, including neutral outputs. Its intervals are Wilson 95% intervals (descriptive marginal rates, not cluster-adjusted intervals). Mean proxy scores retain partial credit. Neither the event nor the proxy proves valid source continuation.

| Row | Reader | A / B | AUROC [95% cluster CI] | A event rate [95% Wilson CI] | B/off-state event rate [95% Wilson CI] | Mean proxy A / B | Neutral A / B |
|---|---|---|---|---|---|---|---|
| prose_paren | olens | inside / outside | 0.371 [0.219, 0.500] | 2/42 = 4.8% [1.3, 15.8] | 8/42 = 19.0% [10.0, 33.3] | 0.452 / 0.595 | 34 / 34 |
| prose_paren | nla | inside / outside | 0.595 [0.464, 0.726] | 0/42 = 0.0% [0.0, 8.4] | 0/42 = 0.0% [0.0, 8.4] | 0.393 / 0.298 | 33 / 25 |
| python_string | olens | inside / outside | 0.512 [0.500, 0.536] | 1/42 = 2.4% [0.4, 12.3] | 0/42 = 0.0% [0.0, 8.4] | 0.512 / 0.500 | 41 / 42 |
| python_string | nla | inside / outside | 0.500 [0.500, 0.500] | 0/42 = 0.0% [0.0, 8.4] | 0/42 = 0.0% [0.0, 8.4] | 0.500 / 0.500 | 42 / 42 |
| python_indent | olens | shallow / deep | 0.500 [0.500, 0.500] | 42/42 = 100.0% [91.6, 100.0] | 42/42 = 100.0% [91.6, 100.0] | 1.000 / 1.000 | 0 / 0 |
| python_indent | nla | shallow / deep | 0.500 [0.500, 0.500] | 42/42 = 100.0% [91.6, 100.0] | 42/42 = 100.0% [91.6, 100.0] | 1.000 / 1.000 | 0 / 0 |
| list_depth | olens | shallow / deep | 0.500 [0.500, 0.500] | 42/42 = 100.0% [91.6, 100.0] | 42/42 = 100.0% [91.6, 100.0] | 1.000 / 1.000 | 0 / 0 |
| list_depth | nla | shallow / deep | 0.500 [0.500, 0.500] | 0/42 = 0.0% [0.0, 8.4] | 0/42 = 0.0% [0.0, 8.4] | 0.500 / 0.500 | 42 / 42 |
| table_column | olens | first / later | 0.403 [0.274, 0.531] | 2/42 = 4.8% [1.3, 15.8] | 0/42 = 0.0% [0.0, 8.4] | 0.131 / 0.214 | 7 / 18 |
| table_column | nla | first / later | 0.500 [0.500, 0.500] | 0/42 = 0.0% [0.0, 8.4] | 0/42 = 0.0% [0.0, 8.4] | 0.500 / 0.500 | 42 / 42 |

Frozen event definitions:
- `prose_paren`: first ASCII parenthesis is closing=>1, opening=>0, neither=>0.5.
- `python_string`: text fragment then ASCII quote followed by code delimiter/end=>1, leading quote=>0, otherwise0.5; proxy only, quote semantics ambiguous.
- `python_indent`: first nonempty line after newline: clip((12-leading_spaces)/8,0,1); no such line=>0.5.
- `list_depth`: first Markdown bullet line: clip((4-leading_spaces)/4,0,1); no bullet=>0.5.
- `table_column`: first generated line: >=5pipes=>1,1–3pipes=>0,none or4=>0.5; proxy for remaining columns, not asserted column truth.

**Format and proxy limits.** Oracle has no scripted refusal marker in 420/420 outputs. NLA has `DESCRIPTIVE_FORMAT_MARKER` in 420/420 outputs (including `<explanation>`), with no explicit refusal marker. Native prompt construction succeeded for both; that does not establish compliance with continuation instructions. Indent proxies saturate at 1 in both states for both readers; Oracle list proxies do too because its native bullet format triggers the rule. These constant rates are uninformative about enactment. No outputs are filtered or rescored.

**GLM E14 comparison** (source: commit `e8b9a22a`, `results/g_agreement/understand/e14/run1/RESULTS.md`): GLM-5.3 RL Oracle closes a parenthesis at 42.5% on-state versus 0.6% off-state (+41.9 pp); SFT 45.1% versus 2.9%. Qwen E6 Oracle is 4.8% versus 19.0% (−14.3 pp). Thus the GLM positive contrast does not reproduce here. This is a comparison point, not a controlled model comparison: E14 uses natural rollout readouts, block 51, many positions and five samples per position; E6 uses W1 synthetic activations, block 44, a continuation request and 32-token greedy output. Scripts/labels also differ, and E14 flags list/table degeneracy. E6 does not include a target next-token ceiling or a new formal state-naming annotation.

E6(a), previously completed on W1 free descriptions, is separate: Oracle paren AUROC 0.457 [0.336,0.585], table_column 0.467 [0.367,0.586]; other reader/row cells unavailable. Those numbers are not pooled into E6(b).

Provenance: pod `5xg04qljqfe472`, booking `ac397e81`, exact frozen source `19fadde5`. Input/score seals, source hashes and complete grids verified before labels. CPU-only analysis ran once per experiment in requested order E6 → E5 → E8. Pre-registered designs and scoring definitions are exploratory; no registered W1/§84/§87 verdict is changed. E6/E8 use a new CPU reporting adapter for their already-frozen proxy/gain functions; E5 uses its unchanged frozen analyser. No new model inference or paid calls.
