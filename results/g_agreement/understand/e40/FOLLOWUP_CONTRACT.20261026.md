# After an E40 PASS — §131 unchanged

Validate the complete E40 output with followup.verify_pass before any actual
latent selection or labelling. It binds the final100M-token checkpoint,
65536/k128 dimensions,filtered gate,all50000-token report,and training-only
calibration sealed before step1. FAIL means no adequate SAE and stop.

Use the existing frozen E35 LATENT_RUBRIC.20261025.md and
BLIND_JUDGE_PROMPT.20261025.txt without changing labels,300dev selection,
top20corpus contexts,independent30double coding or κ. Judges still see opaque
IDs and contexts only. E40's target-token exclusions apply to training/gate;
they do not introduce new W1 item or labelling-context exclusions. The original
heldout source-group exclusions remain in place for corpus contexts.

E40 ScaledSAE.encode accepts raw vectors and applies the sealed scalar once.
Form raw e_w=h-R_win and e_p=R_win-R_ol before encoding. Use
ScaledSAE.raw_decoder_norms() for raw W_dec column norms. Existing §131
additive shares,paired exclusions,ratio of means,row bootstrap10000seed20261025,
100frequency-matched control draws,R1/R2 thresholds,and positive code-difference
descriptions remain exactly as frozen. No E40 norm filter is applied to W1
items; only §131's registered zero-code handling applies.

The existing E35 authorization entry point recognizes the old gate dimensions
and must not be fed the E40 receipt as if it were that gate. The E40 admission
helper validates the new registered gate; the subsequent producer binds that
admission plus completed blinded labels to the unchanged numerical functions.
Before a decomposition request,verify complete W1/raw-AR joins and remaining
budget. Preserve all E35 guards and results. The Integrator returns E40 receipts
to W-sae for this next bounded request; no new scientific ruling is needed for
the registered follow-up.
