# E29 standing-order implementation — 2026-10-25

Authority: §136, commit `e29dc767`, and the updated W-core reader hold. This dated
note supersedes the earlier plan/handoff requirement for a new coordinator post.
The actual W12 freeze remains unpublished as of the origin snapshot `a79a007`;
the schedule is not treated as a frozen bank. No W12 reader outcomes were opened.

The coordinator fixed the predictions in advance: Oracle asked AUROC ≤0.65 for
every structure row, and additionally D minus Oracle ≥0.15 for every row with
sealed D ≥0.70. `predict.py` copies sealed D/P and applies only those rules; it
does not recompute D/P or run an R1/R2/R3 comparison. No fresh coordinator ruling
is required. All scientific decision rules and the reader-scoring hold remain.

`PREDICTION_CODE_SEAL.json` freezes the generator, tests, authority extract and
analysis helper before W12 inputs or scores are available. The eventual READY
scoring plan must include:

- `prediction_code_seal_sha256`, binding this exact code seal;
- `predict.py` in `source_files`;
- `row_classes` in the W12 cohort, derived from its frozen metadata or explicit
  registered classification, with exact row coverage. No classification is
  inferred from row names or D values.

After complete D/P custody verification and the one registered value analysis:

```sh
python results/g_agreement/understand/e29/predict.py \
  --plan results/g_agreement/understand/e29/RUN_PLAN.json \
  --values-seal results/g_agreement/understand/e29/w12_values/VALUES_SEAL.json
```

The command writes `e29/PREDICTIONS.json` and `PREDICTIONS_SEAL.json` once. It binds
the exact freeze, scoring plan, D/P seal and code seal; refuses changed/missing
payloads, foreign freezes, missing classes and existing predictions; and accepts
no reader-score input. W-core/integrator verifies both seals and the required
D/P publication before releasing readers. The generator itself cannot release
that hold. No actual prediction file is produced before D/P exists.

Validation: all 31 E29 CPU tests pass, including seven synthetic prediction
tests covering the exact 0.70 boundary, all frozen structure classes, no extra
content prediction, tampering, foreign freeze, missing pre-score code binding
and no overwrite. Existing registered E25/E27 results and E29 analysis code are
unchanged. The ordinary request remains held for the real W12 freeze; no GPU was
launched and nothing was pushed.
