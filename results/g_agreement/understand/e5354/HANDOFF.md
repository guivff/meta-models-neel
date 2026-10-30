# E53 + E54 — one-pod launch handoff

Authority: `e0a2e9ef`, §170 and §171 including clarification 1. W-internals owns this runner; integrator owns pushing, assignment and execution. One H200, **3,600 seconds total from provider pod creation**, including setup and retrieval; external hard stop mandatory. E54 additionally stops at 1,800 seconds for its capture/native calls plus all shared reader setup. No real GPU work has run here.

## Frozen scope

E53 CPU assembly copies the seven E15 state rows from sealed W1 and E36 analyses into `EXISTING_ASSEMBLY.json`. It does not refit or rerun those analyses. W1's true and original opposite-state W1-mismatched controls are preserved, including original valid-pair masks and CIs. E36's true continuation AUROCs are preserved; its missing opposite-state swap is the only new E36 GPU work (588 stored block-44 test activations, original two E15 pairs, original valid mask). E36 donors are opposite-label, other-cluster, deterministic seed20261027.

New E49 pairs are frozen per item in `CONTINUATION_PAIRS.json`, before any new score. Eight rows: container_after_move, holder_after_handovers, arith_compare, negation_scope, next_paragraph_language, topic_twin, user_expertise, unit_system. Each has84dev+84test, balanced42A/42B per split, one equal-token nonempty pair. Prefixes are unchanged. Base-Qwen actual-text dev AUROC must be≥.80, E15's unchanged validity rule. All pairs remain in descriptive output even if invalid; no rewording, sign flips or test-based selection. The generated follow-on text for the descriptor/negation/holder rows is an E53 hypothesis to be tested by this validity gate, not a claim of logical entailment.

Three §170 proposals cannot be made as specified on the actual frozen bank: pronoun_referent keeps the same named referent in paired prefixes while changing giver/receiver role; arith_carry includes43versus133, so a tens digit is not the next token in both cases; branch_taken ends at the if-colon and supplies no two branch bodies. They are NOT APPLICABLE, with exact reasons in the pair registry. Other unrequested rows remain NOT APPLICABLE. Do not silently add questions, alter prefixes, or substitute forced choice.

E49 opposite-state donors use the same frozen candidate pair and opposite **actual label**, preferring the same filler and template. This matters for topic_twin: variant is not its class label. Candidate-compatible opposite-label donors and A/B balance are CPU-tested. Same inputs are scored with E15's exact operational functions: Oracle block44 with unchanged native prompt and `- ` prefix; NLA block42 with empty prefix, explicitly DESCRIPTIVE_OFF_NATIVE. Scoring code was extracted byte-for-byte, not rewritten.

E54 bank seal: `c13d59f5816321a249d673dd65c35490906b64afcc33fe633bcc66d148d53358`. Both rows have84dev+84test. Capture blocks42/44 once; collect one greedy128-token native readout per test item per reader (168each), no asked channel. Probe is fit on dev only during CPU analysis. Both continuations are NOT APPLICABLE: reasoning_bridge has identical answer4; injection_awareness has identical payload and no source-dependent next text. Exported sealed capture goes to W-lens for §169 pursuit J labels; this job does not take over E52.

## Integrator execution

Stage the sealed prepared-input archive and source archive from `LAUNCH_REQUEST.json`. Bind the full E49 capture-only pull after verifying its seal. The capture must include all2688 IDs and both acts42/44; no E49 reader score file is opened. Run:

```sh
python -m projects.g_agreement.understand.e5354.bind --prepared PREPARED --capture VERIFIED_E49_CAPTURE --capture-seal EXACT_CAPTURE_SEAL_SHA --out NEW_BOUND_INPUTS
```

Fill `ASSIGNMENT.template.json` with the bound-input seal, source seal, exact verified-assets-manifest hash, provider creation time and deadline, pod ID, and **committed E49 forecast**. Supply conservative finite positive phase estimates in seconds; they must cover the full workload. The worker rejects an initial forecast of1.5×remaining+360seconds beyond the120-second retrieval reserve and updates it using observed maximum batch times. It never reduces scope to fit. The external stop remains necessary even if a forward hangs. No second pod, retry or resumed partial scientific analysis is authorized by this request.

```sh
python -m projects.g_agreement.understand.e5354.worker --inputs NEW_BOUND_INPUTS --assignment ASSIGNMENT.json --assets VERIFIED_ASSETS.json --out NEW_OUTPUT
```

W1 score parity (three rows, every AUROC within.02 of sealed reference) precedes production. It is score parity on stored activations, **not** certification of new-capture parity. Reused native capture code is pinned. The job uses E49's already sealed captures; only E54 is newly captured.

Pull every file under OUTPUT, verify `OUTPUT_SEAL.json`, and retain failed/NO_FIT receipts if stopped. Only COMPLETE outputs can enter analysis. Give W-lens `e54_capture/` plus the already frozen E54 bank to obtain J labels. Assemble the map from sealed probe/mention/pursuit-label results without replacing missing mention rates with forced choice.

## Once-only CPU analysis

First export the336E54readouts for blind coding; the key stays private:

```sh
python -m projects.g_agreement.understand.e5354.blind_export --outputs VERIFIED_OUTPUT --output-seal EXACT_OUTPUT_SEAL_SHA --out NEW_PRIVATE_BLIND_EXPORT
```

Judge `BLIND_SAMPLE.json` against `RUBRIC.json`, without reader identity or truth labels. Integrator joins the private key and supplies `JUDGMENTS.json`. Schema: `{id,reader,category,value,blinded:true,raw_sha256}`, where reader isolens/nla; category states_value/names_property/exhibits/silent; value A/B/null. No automatic judge or API request occurs here.

Seal a context directory with `MAP.json`, `JUDGMENTS.json`, and `INPUT_SEAL.json` listing their hashes. `MAP.json`: `{issuer:"integrator",source_seals:{...},rows:[...]}`; every row has bank, row, class, J_label, J_label_method=`§169 amendment1 pursuit`, probe_auc and oracle_unprompted_mention_rate (null if unavailable). Cover seven W1/seven E36/eight E49/two E54 rows. J_label may be NOT EVALUABLE; absent information must not be invented. SVD secondary labels cannot enter R1. Preserve source seal evidence for every joined column.

```sh
python -m projects.g_agreement.understand.e5354.analyse --inputs NEW_BOUND_INPUTS --outputs VERIFIED_OUTPUT --output-seal EXACT_OUTPUT_SEAL_SHA --context SEALED_CONTEXT --context-seal EXACT_CONTEXT_SEAL_SHA --out NEW_ANALYSIS
```

The analysis has a global exclusive once-only guard, validates exact record grids and source/input/output/context lineage, then applies E15's unchanged≥.80dev mask and signed AUROCs. New CIs use E15's2000cluster-bootstrap draws and seed20261023. E53 R1 uses the Oracle channel: among OUT-J structure/tracked-state rows, continuation-minus-unprompted mention≥.20 and swap≤.40 on a strict majority; pooled and per-bank counts both reported. Missing map values produce NOT EVALUABLE, never a forced-choice substitution or a reduced denominator; unknown J membership also prevents a global verdict. E54 is descriptive only, with dev-fit probes, native regex and blind-judge counts, and W-lens J labels. No E52 forecast comparison runs here.
