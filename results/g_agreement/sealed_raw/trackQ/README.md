# Track Q sealed raw judged records (§204 clarifications 1–2)

These are terminal blind judge grids, copied byte-for-byte from integrator custody. Each holds RESULT_SEAL.json, JUDGMENTS.json (opaque IDs), and COUNTS, START and LEDGER_AT_END where present. **No private maps, keys, labels or targets are included.** The analyses joined rows, readers and conditions on CPU using private maps kept in the owners' ignored cache.

| Directory | Bank | Grid seal (RESULT_SEAL sha256 prefix) | Analysis seal |
|---|---|---|---|
| later_banks_15usd_E56_judgments | E56 | see RESULT_SEAL | e56/analysis402_once_2026-10-27 (7d5eeb02) |
| later_banks_15usd_E57_judgments | E57 | see RESULT_SEAL | e57/analysis402_once_2026-10-27 (1f8bf286) |
| later_banks_15usd_E59_judgments | E59 | 40596817 | e59/analysis5968_once_2026-10-27 (a2c47100) |
| later_banks_15usd_E62_judgments + E62_eval | E62 | see RESULT_SEAL | e62/analysis402_once_2026-10-27 (e6bdab57) |
| e66_3usd_E66_judgments | E66 (GLM; judge copy path-redacted) | cf4ade0e | e66/analysis183_once_2026-10-27 (dc902010) |
| e67_5usd_E67_packet_{0,1}_judgments | E67 wave 1 | d2c8b3ba / 3de72300 | r/e67_analysis/wave1_once (92f74fe0) |
| e67_5usd_wave_2_* | E67 wave 2 | 963a842b / 3bf78b55 | r/e67_analysis/wave2_once (d598fe49) |
| e68_3usd_E68_judgments | E68 | 5d10c37d | e68/analysis5968_once_2026-10-27 (bcbdc210) |
| D5_E49, E54 | D5 tranche, E54 | see RESULT_SEAL | e61/d5/e49_analysis_965e4baa, e5354/analysis_c9076571_541b23b1 |

The analysis code is at results/g_agreement/understand/{analysis402, analysis5968, e49/nla_supplement, e79, …} and projects/g_agreement/understand/blind_judge. It is copied unchanged from r/blindspot-mech and r/blindspot-internals.

**Reviewer note:** a bootstrap rerun from these grids alone cannot recover the row, reader or condition joins, because those need the owners' private maps. Ask the integrator.

**E66 exception:** E66's JUDGE_COPY.json and JUDGMENTS.json are withheld from the shared branch. The GLM wild rollouts contain connection-like strings (address-class) that the pre-push hook blocks; the judge copy was redacted for paths only, under 79f63fe0. RESULT_SEAL, COUNTS, START and PATH_REDACTION_AUDIT are published, and the full grid stays in integrator custody for the reviewer on request.
