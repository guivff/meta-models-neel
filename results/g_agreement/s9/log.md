# S9 log

- 2026-10-16 ~11:45 CEST: pre-registration committed (c7ff1ca, BRIEF_S.md § S9) before any S9 number.
- (a) `zsh -ic 'G_CACHE=<repo>/cache .venv/bin/python -m projects.g_agreement.s9_baselines.prompt_only'`, model
  google/gemini-3.8-flash, temperature 0, reasoning effort minimal. First run max_tokens 64 (S9_MAX_TOKENS=64 equivalent):
  70/297 empty → deviation 1 (BRIEF_S.md), rerun at max_tokens 2000: 297/297 parsed, finish_reason stop. 0 errors, no 402.
  Total cost of both runs in `judge_usage.json`. Raw responses: `prompt_only.jsonl` (primary), `prompt_only_max64.jsonl`.
- (b) no new compute; target greedy from `cache/g_agreement/x/x3_target.jsonl`. Self-report thinking-on not cached → not run.
- (c) `python -m projects.g_agreement.s9_baselines.analyze --cache <repo>/cache` once S8's `scores.jsonl` + `s8.csv` exist.
- GPU-hours: 0.
- 2026-10-16 13:09 CEST: s8.csv found on origin (poll). (c) run on S8's per-item records `cache/g_agreement/s8x/{cpu,native,freetext}.jsonl`
  (three-way native, primary; free text via S8's `ft_label`, secondary) and `cache/g_agreement/s8_fullcand/scores.jsonl` (8-way, descriptive).
  Counts reproduce S8's s8.csv (e.g. J-lens L42 m 111/297). Paired bootstrap 10,000, seed 0.
