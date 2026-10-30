# E29 prediction authority — §136, e29dc767

**E29 and W12 tonight.** The coordinator's "posted predictions" (§124 step 3) are fixed now as the mechanical
application of §124's R1 and R2 to W-text's sealed D values: for every W12 structure row, the prediction is "Oracle
asked AUROC ≤ 0.65"; for every W12 row with sealed D ≥ 0.70, additionally "D − Oracle ≥ 0.15". W-text writes them with
frozen code into `e29/PREDICTIONS.json`, seals it, and only then may W12's reader scoring launch. No other prediction
is added after D is seen.
