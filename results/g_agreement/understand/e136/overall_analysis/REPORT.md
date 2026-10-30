# E136 overall analysis — clarification 2

**R-SW1 NOT MET; registered falsifier MET.** Both original probe gates pass (AUROC1.0); both token-excluded carried-word components pass. The named component differs across cues. This is a study of prompt-stated matched cues, not model-private states or causal access.

| Cue | Named: cue-present TEST | Wilson95 | Missing / planned | Both worst-case rate bounds | Cue-absent TEST false-positive rate (Wilson95) |
|---|---:|---|---:|---|---|
| Sycophancy pressure |77/78 =98.72%|93.09–99.77%|2/80|96.25–98.75%|70/78 =89.74% (81.05–94.71%);2 missing|
| Misuse intent |0/80 =0%|0–4.58%|0/80|0–0%|0/80 =0% (0–4.58%);0 missing|

The sycophancy falsifier remains met under worst-case missingness (77/80). Its very high false-positive rate means this judge question does not specifically discriminate cue presence; do not present the high named rate alone as accurate cue detection. The misuse cue meets its per-cue reporting-gap conjunction, but R-SW1 requires both cues.

DEV separately: sycophancy present19/19 (one missing), absent12/19 (one missing); misuse present0/20, absent0/20. Exact Wilson intervals, both bounds and descriptive pooled rates are in RESULTS.json. CI display clamps floating-point endpoint roundoff to0/1 only; immutable numeric JSON retains the original common.stats outputs.

Original carried AUROC: sycophancy .99765625 [ .99234375,1 ]; misuse .918125 [.88046484,.95156641]. Original paired behaviour margin changes: sycophancy −5.782421875 [−6.27185791,−5.340390625], misuse −1.894140625 [−2.14970947,−1.63359375]; strict-positive preference change0 for both. These sealed component calculations were copied, never refit/replayed.

Canonical source96c068c52, prospective source963f6947f;18 synthetic tests passed. All400 new-bank/native/probe identities,320 TEST words identities,1200 readout-only requests and source/member hashes checked before guard. E136R bank only:400 terminal,6 UNPARSEABLE; USD .05092050 of1, unresolved reserve0. Old contaminated bank remains unopened/excluded. Initial committed-source preflight found an uncommitted frozen named.py dependency BEFORE guard; exact dependency was committed, full source closure verified, then one successful guarded run.

Original overall seal: `65b2bee9b21696deb587ad5d1f7026dc9c80b1574dc13545b6b8bd5aedac8f77`. All component guards and this new overall guard are immutable. Private labels, rows, joins and binding stay CPU-local. R-2 independent review requested.
