# E116 exploratory note 2 — post hoc

Authority f011cc183. CPU-only calculation completed once with separate consumed guard. Primary R-CH3 remains NOT MET; primary and note1 seals unchanged.

The matched cohort contains110 immediate non-modal items with observed Oracle60, selected using the original E108 leave-one-out mode. All110 have sealed per-item outside judgments.

| Reader/site | Hits | Rate | Wilson95% |
|---|---:|---:|---|
| Outside LLM |31/110|28.18%|20.62–37.22%|
| Oracle44 |7/110|6.36%|3.12–12.56%|
| Oracle52 |29/110|26.36%|19.03–35.29%|
| Oracle60 |59/110|53.64%|44.35–62.68%|

Paired Oracle60 minus outside: **+25.45 percentage points**,95% item-bootstrap CI **[+11.82,+38.18]**,110pairs,zero missing.5000draws,seed0; original sealed measurement order. Post hoc exploratory, no new confirmatory rule.

For all111 original non-modal immediate items (including the one missing Oracle60), Oracle44=7/111=6.31%,Wilson[3.09,12.45]%; Oracle52=29/111=26.13%,Wilson[18.85,35.00]%. The matched110 table uses the same items as the outside contrast; neither denominator is hidden.

Source67db7fa65 with six synthetic tests committed before invocation. Original sealed E108 outside/Oracle44 and E116 Oracle52/60 judgments reused, no new judging/parsing or primary replay. Seal b463e17b33a46892d0c6e89d1eabb804cc3b9c526786f1bcdb31b1f90de7ae7f verified. Private binding/cohort remain CPU-local.
