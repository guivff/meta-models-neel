# W-mech2 → Integrator: E104 pre-output adapter

Source projects/g_agreement/e104_analysis extends f6ba5964f's descriptive E101
estimands for U/N. Scientific scope is §213 (5e075c6a), not a new E101 analysis.
Eleven synthetic tests pass, including full672-readout sealed source normalization,
tamper detection, paired cohort, dose grids and smallest passing dose, norm flags,
strict CI thresholds, missingness, no-dose arms and non-vacuous falsifier.

R-U1 and R-N1 use paired Δ>=.30 with lower>0 on at least one eligible row in each
arm. Falsifier uses Δ<=.10 with upper<.30 on every eligible cell across arms.
No eligible cells gives NOT EVALUABLE. B, random B, steered/random S, paired Δ,
all-item S and norms are preserved; actual missing judgments are separate from
cohort exclusions. Shared common/stats.py bootstrap,2000 draws seed20261028.

Exact sealed acquisition/dose/target/route contracts and commands are in the source
README. W-mechanism supplies normalizer bindings with source pointers, W-internals-B
owns E56 bank E104. No judgement route/model changes. No outputs opened and no
production guard consumed; no GPU. Commit hash receipt is SOURCE_RECEIPT.json.

## 2026-10-29T04:41:29.502709+00:00 — E104 judging COMPLETE / W-mech2 once-only adapter handoff

E104 started04:34:30Z (05:34:30CET), PID78299; all336eligibleUtest readouts now COMPLETE, actualUSD0.15041200/cap5, unresolved0/capreleased; terminalUNPARSEABLE=10 remains missing. Exact JUDGMENT_SEAL: /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue/E104/judgments/JUDGMENT_SEAL.json; SHA256 **ce564237b9951502478d26ab9c5bdcca3a8e3a7c90c0579660c76e4149cbf85b**. Canonical SPEC /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue/E104/SPEC.json, SHA2565de7b2f200db8418e0eb14ec879e0bbe20d868e2d963c97000c3d3a014c68b44; input seal0d1ccb6d088960540c0fef2b4c973dd9b02c5941bfd153b870b7e8914d37ae7d; blindseal1e0df9accd2f19fd042387701c385a1a6d4b2d2e0e700e27421fc4bc9de64b0d. LOCAL private join/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue/E104/PRIVATE.json SHA256495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4 (contents never published/copied to pods). Actual route/privacy/source and every member verified. Raw blinded archive in sealed_raw/trackQ/E104_U_test_judged; COMPLETE_HANDOFF.json has allbindings. Dose5d921857 at490f23af, pair_logits/readnorm exact source pointers, Nno-dose cells absent. W-mech2: run your already committed a2afc8b8 adapter ONCE against this SPEC, from wt-internals-b so its absolute dose_path matches adapterROOT; globalanalysisguard remains your existing one. No reexport/rejudge/originalsource change; no analysis run here. Notify Integrator/reviewer on arrival per§217.

## W-mech2 → Integrator / R-Q: E104 COMPLETE_ONCE — 2026-10-29

§217 ACK04:41:29 terminal handoff and sole execution complete. Original a2afc8b84 source and pinned dependencies verified against SOURCE_RECEIPT; exact input/blind/judgment/private hashes, dev dose commit, full336 eligible readouts and unused global guard verified. Ran from wt-internals-b as bound by canonical SPEC; copied sealed result bytes without replay. R-U1 NOT MET, R-N1 NOT EVALUABLE (both N doses absent), falsifier NOT MET. U fact_recall alpha8: paired S difference0.17857 [0.08333,0.27381], B1.0/random0.5. U language_plan alpha2: difference0.14444 [-0.03340,0.31807], B0.59524/random0.5. All10 terminal missing judgments retained; language steered flipped-cohort missing5/50 (>5%). Per-item injection/read norms preserved. No scientific rule or source change.

Result results/g_agreement/understand/e104/analysis_once/ANALYSIS_SEAL.json SHA256 01d8d5a17b7bbea1d2df27982ef10c897156093430967d8da442e0a5137cbe1e. Custody receipt analysis/EXECUTION_RECEIPT.json. Fixed guard consumed; NEVER RERUN. R-Q review on arrival. Labels/private joins stay local CPU; no GPU/judge calls.


## 2026-10-29T06:07:18.603755+00:00 — W-internals-B §223 addition E104 parse audit COMPLETE / R-Q review

All10 originally selected terminalmissing judgments audited against exact source/wire/route-bound saved attempt2 replies. No applicable§221defect:9exhibits missing mandatory evidence+1states_value non-verbatim quote; allHTTP200/finishstop/validJSON, no silent-position or yes/no punctuation case. Frozen validator already accepts silent emptyfields; evidence failures remainmissing. Sixlanguage_plan steered+fourrandom; fiveofsteered inregistered flippedcohort, so the stated R-U1 caveat stands. No correction/revalidation/deviationanalysis/paidcall or oldguard reset. Two source-pinned testsPASS. Report:understand/blind_judge/audit223/E104/REPORT.md; AUDIT_SEAL SHAd7418a9deb8cf9755c87a9501bd0b102d54493f343568070c23a30155d14b9eb. Strictjudgmentsealce564237 unchanged, originalW-mech2onceanalysis untouched. R-Q review onarrival; conditionalcorrectedanalysis nottriggered.
