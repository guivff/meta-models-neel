# W10b dev gate — operational label-path fix

The original gate called label-free stage admission and then tried to read labels from inside that bank. The corrected gate requires a separate `--labels` path outside the staged bank, checked against the original manifest's frozen label hash after the sealed inputs, generations and judgements verify.

Use this command in place of step 3 of the historical DEV_MODE_RUNBOOK.md. The old runbook and its request seal are preserved as issued. The item bank, manifests, prompts, judge outputs, row set and ≥16/20 threshold are unchanged. No regeneration or judge rerun is required.

```bash
python -m projects.g_agreement.blindspot.w10b_dev gate \
  --bank cache/g_agreement/blindspot/w10b-stage-v1 \
  --labels cache/g_agreement/blindspot/w10b-bank-v1/labels.DO_NOT_STAGE.jsonl \
  --generations RETRIEVED_DEV_OUTPUT --packet SEALED_BLINDED_PACKET \
  --judgements SEALED_JUDGE_OUTPUT --out NEW_MODE_GATE_OUTPUT
```

The gate-only source admission pins the exact original `w10b_dev.py` hash recorded at freeze (`379b6fa7…`) while allowing this operational gate implementation to run. Every other dependency must still match exactly. Generation/packet workers retain strict source admission. The output records both the unchanged label-file hash and this operational gate source hash.

CPU regression exercises the complete sealed-gate path with a label-free bank and external labels: 15/20 fails and 16/20 passes. It also checks that an unrelated changed dependency remains rejected. This fix does not itself run the scientific gate or acquire any analysis lock; the integrator runs it on the already sealed judge outputs (`a9f1541b`).
