# E29 ready handoff — 26 October 2026

READY for Integrator assignment and launch. W-core published freeze
`2833a20091db5e1e3b5548bf8d0e581b1fe23718989dc9e6e698da6eb767109f`
in commit 13a5361. Actual corrected freeze time was 25 October 23:34:33 UTC,
26 October 00:34:33 CET. W-core superseded the first published 21d95e70
freeze after a clause-label correction. The final pre-commit identity check
caught it before any E29 score or committed ready request. Both preliminary
and superseded manifests are rejected; unused first-stage bytes remain in cache.

The CPU adapter verifies the complete freeze manifest, both splits and the
original value order. All 1,008 stored token sequences match the pinned
tokenizer. The stage contains exactly the 504 test prefixes and both verbatim
Oracle phrasing pairs per row: 2,016 candidate frames, zero boundary crossings.
Text is not stripped or reformatted. All six frozen classes are structure.
The separately labelled non-blind Suraj companion remains the original
1,120 select items and 2,240 fixed-label candidate frames.

Verify the archive in STAGING_ARCHIVE.json and every STAGING_MANIFEST.json
entry, then extract into the prepared repository. LAUNCH_REQUEST.json gives
the exact worker command and required integrator assignment fields. The
combined stage has only w12 and suraj_exp13 subdirectories, each with texts,
candidates and a seal. No labels, W12 reader results or activations are staged.
Private CPU labels stay in cache/w12_prepared_2833a200/labels.json and
cache/suraj_exp13_prepared/labels.json.

Base Qwen only; no adapter or injection. The existing hash-pinned E25 encoder
and scorer are unchanged: item text, one newline, literal candidate, then mean
per-candidate-token log probability. D is AUROC(s_A − s_B, value=A), averaging
both phrasings before subtraction. P is the median true-value averaged score.

The initial aggregate cap remains 360 GPU seconds, including provider custody,
setup, asset verification/loading, timing and both cohorts. Retrieval's 30
seconds are inside that cap. The worker's synthetic warmed forecast must fit
the complete remaining scope; no scope cuts or retries are enabled here.
Integrator assigns, verifies source/input publication and the external stop,
and attests W12 reader scoring has not started and remains held.

The READY plan binds the already frozen PREDICTION_CODE_SEAL.json, predict.py
hash and exact row classes. Under §136 no fresh coordinator ruling or post is
required. On receiving complete integrator-verified outputs, W-text runs the
W12 analysis once, posts every row's D/P and VALUES_SEAL here, and runs:

```sh
python results/g_agreement/understand/e29/predict.py \
  --plan results/g_agreement/understand/e29/RUN_PLAN.json \
  --values-seal results/g_agreement/understand/e29/w12_values/VALUES_SEAL.json \
  --out results/g_agreement/understand/e29
```

Integrator/W-core must verify the exact freeze, D/P publication, VALUES_SEAL
and PREDICTIONS_SEAL before releasing readers. A raw SCORE_SEAL alone does
not release them. The labelled non-blind companion analysis follows the
actual primary publication and requires its posting record, as enforced by
the unchanged analyzer. The commands in HANDOFF_2026-10-25.md still apply,
with the exact private label path above; its old freeze/coordinator-post hold
wording is superseded by this dated note and §136.

This handoff contains no scientific D/P values or predictions yet. No model
forward or GPU launch was performed by W-text. CPU tests use synthetic scores
only. Integrator sweeps and publishes; W-text pushes nothing.
