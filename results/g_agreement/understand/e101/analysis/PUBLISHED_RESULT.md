# E101 descriptive result — once-only execution

Scientific adapter f6ba5964f, unchanged; custody bridge4170e45f9. Result seal
ad820c3f25acab98b70dd05881b341b4c658182ca2daa3e57b230a421742f4c1.
Output: ../analysis_once/{RESULTS.json,B_VS_REPORT.png,ANALYSIS_SEAL.json,BINDING.json}.
No text baseline was awaited. The private judgment join remains local.

| Oracle block44 cell, alpha4 | Steered B | Random B | Flipped-cohort steered S | Flipped-cohort random S | Paired difference (95% CI) |
|---|---:|---:|---:|---:|---|
| fact_recall |79/84|0/84|0.0513|−0.4684|0.5196 [0.4066,0.6404]|
| language_plan |71/84|35/84|0.8269|−0.2951|1.1220 [0.8803,1.3429]|

Both readouts use the same steered-flipped cohort; separate missing-judgment masks
remain as preregistered. Fact-recall retained78/79 steered and79/79 random.
Language-plan retained52/71 steered and61/71 random. All-item S and intervals are
in RESULTS.json. The generic statistics field UNPARSEABLE in masked-cohort entries
includes out-of-cohort exclusions; do not read it as the number of failed judgments.
Actual all-item missing counts: fact-recall1 steered/0 random; language-plan19
steered/12 random. This limitation is disclosed without changing/rerunning analysis.

R-F1/R-F2/R-F3 and their falsifiers remain NOT EVALUABLE under section212.
The steering vectors at alpha<=4 never crossed the decision boundary of the frozen
behavioural contrast on12 of14 cells. This does not establish that the model does
not use the state. Nesting-depth's short candidate is a strict prefix of the long
one, structurally favouring the short summed log-probability; page-range baseline
is0/84. No defect rerun or metric change. No analysis replay is authorized here.
