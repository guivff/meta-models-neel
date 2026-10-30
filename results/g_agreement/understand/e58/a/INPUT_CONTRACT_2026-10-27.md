# E58a R-a1 input contract — 2026-10-27

Command: `python results/g_agreement/understand/e58/a/analyze_once.py`. Integrator delivers cache/g_agreement/understand/e58a/VERIFIED_R_A1_INPUTS.json. No analysis runs until the committed request’s bank scope is resolved and the complete inputs exist.

Category source is W-text’s committed blind packet: rows is a list of {bank,row,category}; categories are exactly bookkeeping, delimiter, syntactic, format, content. Receipt binds repository_path, commit and SHA256. The script checks the committed bytes before opening label or probe documents and requires the Integrator’s blind-category provenance attestation. Any schema adaptation must preserve the assignment and original source hash, be committed before the join, and never consult labels.

For each required bank, provide a sealed primary ROW_LABELS document and sealed probe-only extract. Each reference has path, sha256, seal_path, seal_sha256 and member relative to the seal. Probe-only extract: measure=test_probe_auroc, layer=44, reader_outcomes_included=false, rows=[{row,auroc}]. Integrator preserves original analysis provenance when making the extract. No reader metrics are needed or opened. Category, label and probe row coverage must agree exactly. Keys are bank+row; repeated feature names across banks are distinct registered rows. No score-dependent omissions.

Exclude probe<0.85. R-a1 pools bookkeeping+delimiter+syntactic versus content, requiring lower median J-fraction, one-sided Mann–Whitney p<0.05, target OUT-J/DIFFUSE fraction≥0.70 and content OUT-J/DIFFUSE fraction≤0.30. Format is kept in the join but outside this contrast. A probe-eligible row without a computable primary J label holds the experiment rather than being dropped. Record incomplete scientific inputs and ask the coordinator before changing row coverage.

R-a2 is held until E49/E56/E57 readers have all been analysed; this command does not compute it.

§174 clarification1(c), 6e58d7d1, confirmed directly by Guiv: R-a1 runs once across all six banks W1/E36/W12/E49/E56/E57, after E56/E57 labels and probe gates exist. No partial evaluation on the four existing banks.

The same commit, §173 clarification1(c), explicitly makes E57 capacity_list count-only with no A/B label or probe. Keep it in the category join, marked NOT APPLICABLE with null J_fraction and a probe extract entry {row:capacity_list, auroc:null, reason:REGISTERED_COUNT_ONLY_NO_PROBE}; report it outside R-a1. No other missing probe/label is accepted as an exclusion.
