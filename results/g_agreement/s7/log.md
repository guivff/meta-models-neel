
## S7 — shared reader-error flags (2026-10-16, CPU only, 0 forward passes, 0 GPU-h)
- Pre-registered BRIEF_S.md §S7 (commit 2c83108) before any number.
- `.venv/bin/python projects/g_agreement/s7_flags/analyze.py --data-root <main checkout> --out results/g_agreement/s7` (~10 s wall; seed 0; n_boot 2000; n_perm 10000).
  Inputs: cache/g_agreement/x/x3_lo.jsonl, cache/g_agreement/states (block 42), cache/g_agreement/y/y1_logitlens.jsonl, results/g_agreement/f2/t4/t4_confusion.csv,
  x6_majority.build_d3 (probe + centred LO). Reproduces X6: 17.5% shared-wrong vs 9.2% independence.
- Result: no flag has AUROC lower bound > 0.7; probe-disagreement 0.76 [0.67, 0.83] closest; within-difficulty-bin null 9.2% (difficulty explains ~0% of the excess).
- HF API check for DeepSeek-V4-Flash NLA/Oracle appended to s3/second_model.md.
