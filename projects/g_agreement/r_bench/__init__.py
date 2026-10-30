"""Phase R — reader-bench (BRIEF_R.md): the 113 SAE-probing datasets + multiclass parents + conflict and planted
sets, scored by every reader natively, against probe learning curves, the model's own report and controls.

Modules
  datasets.py   the frozen spec: one FactSpec per dataset (question, candidates, template, taxonomy, positive label)
  bank.py       CSV (prompt,target) -> dataset/items_r.json (balanced test/pool splits; --check prints samples)
  collect.py    pod: batched multi-layer capture, logit lens, prompt-only forced choice, reader LO, controls
  steer.py      pod: R5 directions (class-mean, probe, reader gradient) and norm-matched steering with read-back
  analyze.py    CPU: R1–R8 tables and figures (numpy/sklearn only; --mock synthesises a bank to exercise the code)

Imports are ``from projects.g_agreement.r_bench import datasets as D``; run modules from the repo root.
"""
