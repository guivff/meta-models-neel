# E128 — alpha_min 4; R-DOSE1 NOT MET

Source 4bf17ae07108fc84fbacbb8cb8b89fbd75557c73 was committed, tested (55 synthetic tests), and delivered to R-Q before the single opening. Authority 434061b36; Track Q SPEC69af33cc; pair-logit flips under §238 deviation1; alpha_min only2/4. Shared DEVIATION1_ONCE consumed; never replay.

Pair-logit flips: alpha2 0/84, alpha4 42/84. Thus alpha_min=4. On the 42 alpha4 steered-flipped items:

| Readout | Count | Rate | Wilson95 |
|---|---:|---:|---|
| Steered44 old | 4/42 | 0.095238 | [0.037662,0.220654] |
| Steered52 new | 42/42 | 1.000000 | [0.916198,1.000000] |
| Random44 old, same cohort | 31/42 | 0.738095 | [0.589310,0.846975] |
| Random52 new, same cohort | 0/42 | 0.000000 | [0.000000,0.083802] |

R-DOSE1 NOT MET: the old44 >=.50 and Wilson lower>.35 requirements fail; new52>=.70 passes. The claim that staleness is not a large-dose artefact is not established. All four selected-cohort rates have complete42/42 coverage, so their failure/success missingness bounds equal the observed rates and CIs; worst-case R-DOSE1 remains NOT MET. The new bank's single missing judgment is alpha4/steered44 OUTSIDE the pair-logit-flipped cohort. It is retained, not refilled or zero-imputed, and cannot change selection or the registered headline.

Original alpha8 remains descriptive: E104 pair-logit flips84/84; old44=47/83, CI[.459057,.667610], with one original missing judgment and full84 bounds47/84 to48/84; new52=84/84, CI[.956267,1]. This original-alpha8 missing judgment is distinct from the one new-bank missing judgment. No alpha8 selection, generation or rejudging.

Analysis seal SHA256: `9b4c54a4422bb60db12d32899cd68cb4715ec2ec6a6c0e4498eb933c6f8c23c7`.
Results SHA256: `a9798b980b74fd4cdccf473a10a93d2ef5ac2eb1bb6a4efcc417a51b7c54cb32`.
The original seal is copied unchanged; its BINDING.json member stays CPU-local. R-Q independent review requested; no review PASS claimed.
