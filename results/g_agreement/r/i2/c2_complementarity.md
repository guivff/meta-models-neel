# C2 — Exploratory label complementarity (2026-10-20)

Registration: `06ef6e0c`, dated TH-3 §25 subsection; distinct from the integrator’s C2 claims ledger. CPU only. Signed candidate margins predict labels, not reader correctness.

| Reader / comparator | Items / facts | PO AUROC | PO + reader AUROC | Gain | Wider 90% CI | Wider 95% CI | Verdict |
|---|---:|---:|---:|---:|---|---|---|
| olens | 21198 / 108 | 0.9202 | 0.9198 | -0.0004 | [-0.0017, +0.0012] | [-0.0022, +0.0018] | REDUNDANT |
| nla | 21198 / 108 | 0.9202 | 0.9200 | -0.0002 | [-0.0015, +0.0012] | [-0.0020, +0.0017] | REDUNDANT |
| jlens | 21198 / 108 | 0.9202 | 0.9202 | +0.0000 | [-0.0012, +0.0025] | [-0.0015, +0.0033] | REDUNDANT |
| skip_a | 21198 / 108 | 0.9202 | 0.9198 | -0.0003 | [-0.0016, +0.0012] | [-0.0020, +0.0018] | REDUNDANT |
| lr | 20400 / 102 | 0.9260 | 0.9495 | +0.0235 | [+0.0099, +0.0511] | [+0.0083, +0.0579] | INCONCLUSIVE |
| massmean | 20400 / 102 | 0.9260 | 0.9377 | +0.0117 | [+0.0043, +0.0268] | [+0.0036, +0.0300] | INCONCLUSIVE |

Each comparison uses the same matched rows for its PO-only and augmented model; LR and mass-mean have fewer available facts. Four native readers are reported separately; LR is the requested comparator and mass-mean the second existing TH-3 probe. LABEL_DEFECT facts remain excluded; audit flags remain included.

Five frozen folds grouped by fact; weighted training-only standardization and intercept plus L2 logistic slopes (C=1). Both models are refitted inside every paired bootstrap replicate: 2,000 item and 2,000 corpus draws, seed 0, full-universe weights before reader masks. The reported intervals envelope both schemes. No test tuning or held-out scaling. Existing TH-3 normalized-text overlaps across facts remain; corpus intervals address clustering but do not turn these into source-disjoint folds.

Rules: COMPLEMENTARY iff wider95 lower >0.01; REDUNDANT iff wider90 lies inside [−0.01,+0.01]; otherwise INCONCLUSIVE. These exploratory per-reader intervals are unadjusted for multiplicity. No verdict here alters TH-3 confidence rules or E4.

[Machine-readable table](c2_complementarity.csv) and [run metadata](c2_complementarity_run.json). All rows carry per-process run_id, run_kind and code_sha256; retained bootstrap arrays also record worker identities.
