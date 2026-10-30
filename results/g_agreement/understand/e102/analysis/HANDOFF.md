# W-mech2 → Integrator / I-4: E102 once-only analysis

Source: projects/g_agreement/analysis_late/e102.py. CPU-only and pre-output.
R-V1 includes the placebo statement-rate condition; R-V2 uses paired item differences;
R-V3 includes every replay row and the 518-item WorkspaceBench loss check.
Falsifier, per-row/set paired bootstrap, per-family WorkspaceBench and training loss
are included. The Oracle gate names olens_s3d_rl600, never ar_ptag_pooled.

The exact normalization and inventory contracts are in analysis_late/README.md.
Commit the full pre-output inventory; keep 3×84 trained, all six content rows,
all registered held-out rows with explicit available counts, 500 placebo and 518
WorkspaceBench pairs. Bind exact source text/codes/pass verdicts through sealed
JSON pointers. No arbitrary precomputed scores. Route and privacy receipts are
required; labels and truth remain CPU-only. NLA is only included with its own gate.

Execute once after all required seals exist:
python3 -m projects.g_agreement.analysis_late.e102 --spec SPEC.json
No production outputs were opened, no analysis guard claimed, no GPU or judge calls.
E101 remains first. Forward this concrete contract to W-train/I-4 for binding.
