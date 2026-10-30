> SUPERSEDED by §130 (4769ca0e). Historical record only; do not use for attempt 2. See FULL_SCOPE_RESTORATION.md.

# E24 attempt 2 analysis amendment

Authority: §118, d3d91630, dated 2026-10-25 12:05 CET; read via GitHub connector at that commit.

Five layers: 44, 20, 32, 52, 60. Channels: C1, C2, C3, C5. The explicit attempt-2 plan fields in ATTEMPT2_ANALYSIS_SCOPE.json select the amended analysis; legacy attempt-1 handling remains available for provenance. Attempt-2 admission rejects missing/extra layers and C6/C7. No C4 parsing, R4 adjudication or judge packet is produced.

R1/R2 use the original 16 structure rows (intersection with the frozen 25-row continuation scope); R2 uses all 64 non-anchor cells, including p=1 for invalid anchors. The original sealed 28-row bank is unchanged; three extra LaTeX rows remain descriptive and R0-checked outside the rule family. C5 remains on the original 25 rows. R3′ retains swap AUROC <=0.40 and CI upper <0.50. C5's layer-44 E1b reproduction remains part of R0; C5 has no across-layer decision rule.

Per-layer R1 is unchanged. Its original across-layer threshold >=9 of 11 cannot be assessed in five layers: return null with NOT_EVALUABLE_ORIGINAL_THRESHOLD_9_EXCEEDS_5. No replacement threshold is invented.

Budget for the eventual worker/launch package: <=21,600 GPU seconds total, including attempt 1's 5,220 seconds (1.45 GPU-h). Remaining ceiling is at most 16,380 seconds (4.55 GPU-h), before other charged custody. Existing per-pod caps/setup limits remain. This analysis amendment does not authorize a launch or change acquisition code.

Before relaunch: E24-D must name the cause; the capture fix must be reviewed and limited to that cause. Integrator must package the reduced acquisition scope/budget and re-pin amended analysis, tests, plan, archive and launch seals. The old launch archive is not attempt-2-ready. Do not reuse old plan bindings or analysis locks.

Exact code/test diff: ATTEMPT2_ANALYSIS.patch. Validation: 28 CPU tests pass, including end-to-end synthetic five-layer analysis with no C4 fields and 64 Holm cells, invalid-anchor propagation and once-only lock. No scientific analysis or inference was run. Pull/rebase attempted from a clean worktree but blocked by GitHub DNS; temporary stashes restored, including unrelated log edits.
