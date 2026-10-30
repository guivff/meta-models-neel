# W10 §86 — mode judge and once-only CPU analysis

Capture `vzovpasgdwsz71` / booking `77e4ad05` is accessible. Its capture,
asked-score and free-generation seals verify; the full 26,208-cell score grid
and 280 generations were verified before the local mode-label join.

The original local bank had an older manifest. The **exact scored bank** was
copied byte-for-byte from the integrator-synced W-mechanism cache to
`cache/g_agreement/blindspot/w10-bank-scored-vzovpasgdwsz71`. Its input seal is
`cb34e2068679e6737f15d70f29e3717e537c9f16749438f542e3597b7b5f4920` and manifest
is `e7049159f3c8e4462b58697ec012783ed34346bcab3d0a1ab8be5c4d099ed136`.
All original item/label bytes match; only the warmed worker/source manifest
changed. This was an exact retrieval, not a regenerated or rebound bank.

The frozen script check is complete: language near/far **20/20** each, output
format near/far **14/20** each. All four meet ≥70%. Ten other mode rows still
require **200 blinded judgements**. Their exact frozen prompts are committed
under `mode_checks_vzovpasgdwsz71/`. No reader outcomes or expected labels are
supplied to the judge. The current session's OpenRouter pricing/network
preflight fails with ConnectionError, **before any model request or charge**.
`JUDGE_NETWORK_BLOCKER.json` records it. No registered analysis has run and no
analysis lock has been acquired.

## Integrator: run these commands unchanged, in order

From `<local-path>`,
using its normal Python environment and existing API-key environment. Never
print credentials. No pod, capture, target-model forward or reader inference.

```bash
python -m projects.g_agreement.blindspot.w10_cpu judge \
  --packet results/g_agreement/blindspot/w10/mode_checks_vzovpasgdwsz71 \
  --out results/g_agreement/blindspot/w10/mode_judge_vzovpasgdwsz71
```

Only proceed after a complete `MODE_JUDGE_SEAL.json`. The runner uses the
frozen prompt verbatim and the project's default `openai/gpt-5-mini`, fetches
current pricing, reserves a conservative full-pass bound ≤$3, writes each
result and cost record, and makes no automatic retries. It stops on invalid
judgement JSON, incomplete output, API errors or exhausted budget. Preserve
partial/failed attempts; do not relaunch them automatically.

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m projects.g_agreement.blindspot.w10_cpu analyse \
  --bank cache/g_agreement/blindspot/w10-bank-scored-vzovpasgdwsz71 \
  --outputs cache/g_agreement/blindspot/w10-units/vzovpasgdwsz71/w10-out \
  --packet results/g_agreement/blindspot/w10/mode_checks_vzovpasgdwsz71 \
  --judgements results/g_agreement/blindspot/w10/mode_judge_vzovpasgdwsz71 \
  --out results/g_agreement/blindspot/w10/analysis_vzovpasgdwsz71
```

The analysis takes a create-only lock after validation. Do not remove another
run's lock or repeat an interrupted analysis without instruction. W-core and
integrator must not start this analysis concurrently. The party taking the
lock owns the sole run; the other reviews its sealed outputs.

All score, generation, judge, source and input seals/grid checks precede the
test-label join. The unchanged W1 grouped probe is used (lambda 0.001; five
test-template-grouped folds; train-only standardization). Reader scores are the
mean of two frozen signed phrasings, without sign flips. CIs use 2,000
template-cluster resamples and the fixed seed; no probe refits in bootstrap.

Mode activity is assessed on exactly 20 dev generations/row; fewer than 14
following the instruction makes the row NOT EVALUABLE. Reader gates use their
native probe ≥0.85 and random-donor AUROC in [0.40,0.60]. H1 uses Oracle-evaluable
mode rows; H2 requires both Oracle and NLA evaluable. Empty denominators are NOT
EVALUABLE. Surprisal rows are descriptive, excluded from H1/H2, and retain the
frozen tercile rule and length-confounding disclosure. Report all rows, failures,
both native probes, J-lens, each phrasing, paired NLA−Oracle CIs, and paired
passage-cluster far−near contrasts.

On completion, publish the exact `HANDOFF.txt` line and per-row `RESULTS.md`;
commit locally. The reconstructor's text-window dependency remains unresolved,
so no claim of blindness by construction is permitted.
