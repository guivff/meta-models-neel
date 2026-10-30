# E24 full scope restored before attempt 2

Authority: §130, commit 4769ca0e, read in full via repository connector. Supersedes the 12:05 five-layer/four-channel amendment and its local implementation d54dca40 (the user also references published 9c03e3db).

Restored the pre-d54dca40 analysis and CPU tests, plus a guard rejecting superseded reduced plans. Exact diff from d54dca40: FULL_SCOPE_RESTORATION.patch.

All 11 trained grid layers, priority 44,20,60,32,52,28,36,40,48,56,24; C1–C7 with original tier/admission rules. Clarification 1's evidenced 28-row branch and 19 structure rows are retained: Holm 19 × 10 = 190. C5 stays on the original 25 rows. C4 regex scoring, R4 and blinded judge packet return; C6/C7 return under their registered layer/tier rules. R1's original >=9-layer aggregate returns.

Clarification 2 is preserved: R3′ requires C2 >=0.70, swap AUROC <=0.40 and swap CI upper <0.50; C5/R6′ is descriptive per row/layer without an across-layer verdict. Every pod's layer-44 C5 reproduction within ±0.03 of E1b feeds R0. Invalid R0 rows stay uninterpretable at every layer.

Total cap 12 GPU-h including attempt 1's 1.45 (43,200 seconds total; at most 37,980 seconds / 10.55 GPU-h remaining before other charged custody). Carry prior charges forward; no budget reset. Up to four E24 pods; original warmed forecast, per-pod cap and setup rules remain.

27 CPU tests PASS, including complete synthetic full-scope analysis, 190-cell correction, C4 audit packet, R3′ boundaries, E1b R0 tolerance and rejection of superseded reduced plans. No inference or scientific analysis rerun.

Relaunch remains blocked until E24-D names the cause and the cause-limited fix is reviewed. Acquisition code and sealed inputs are unchanged. The integrator must bind the reviewed fix and restored analysis into a fresh source archive/plan/launch request before attempt 2. Historical five-layer documents are marked superseded, not erased. No launch or push.
