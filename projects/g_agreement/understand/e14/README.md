# E14 (§103): GLM-5.3 Oracle-lens rollouts, CPU only

Integrator runs this on a machine that can reach huggingface.co (the coordinator's workspace cannot). Public dataset, no token needed.

```bash
# 1. download (public; ~parquet files only) into the git-ignored cache
huggingface-cli download ceselder/glm-5.3-olens-wild-rollouts --repo-type dataset \
  --local-dir cache/g_agreement/understand/e14/data
# 2. run once (CPU, needs numpy + pyarrow); --out must not exist
python -m projects.g_agreement.understand.e14.run \
  --data cache/g_agreement/understand/e14/data \
  --out results/g_agreement/understand/e14/run1
```

Outputs: `RESULTS.json` (rates and on-minus-off differences with CIs, per state × reader version × code, plus input file
hashes), `EXAMPLES.json` (2 seeded positions per state, chosen before any rate), `HAND_CHECK.jsonl` (50 seeded hits per
state × code for a manual check). Commit `RESULTS.json` and `EXAMPLES.json`; `HAND_CHECK.jsonl` too if under 2 MB.
Only parquet files with all required columns (`left_ctx, token, next16, rl_*, sft_*`) are used; the list is recorded.
Log wall-clock in `results/g_agreement/log.md`; GPU-hours 0.
