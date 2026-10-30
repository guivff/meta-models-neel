# E76 judged floors — READY, 2026-10-28

Authority: HANDOFF03b53c82 and §194 clarification2 f3fcb715. Preparation only: no API call, budget-ledger mutation, judgment opened or real judged-floor analysis. Existing E76 production OUTPUT_SEAL4a199f6c... and full regex ANALYSIS_SEALa0b9808a... are unchanged. Do not run either original scientific analysis again. This adds a separate once-only judged analysis after the Integrator seals its terminal judgments.

## Frozen scope and sample

ROW_INVENTORY.json is frozen from sealed E36/E49/E54/E56/E57/E59/E62 analyses and original definitions, before placebo text was opened. It contains43 binary bank/rows,48 frozen A/B value families and every source pointer/reporting criterion. E36 entries retain their registered no-native forced-choice fallback label; they are not relabelled as native reports. E49/E54 use their own existing native reporting convention; later banks use §172. ROW_INVENTORY.json lists count, evaluation, non-binary, unreported and out-of-scope exclusions explicitly.

Use26 placebo vectors per row × reader × pool, uniformly without replacement,seed20261028. A row with multiple original binary value families keeps every frozen pair and its original test-frequency weight. All its families use the same26 vectors and stay clustered in the interval bootstrap. The uniform reduction is floor(5000/(4×48))=26, below the requested maximum50; this gives4992 judge records across172 cells. No content, redaction, malformed-output, probe or judgment filter is applied to the placebo draw. Full regex floors keep their original500 vectors per pool/reader.

JUDGE_PACKET.json fields are exactly id/property/values/readout. IDs are unique opaque32-digit hex strings; there is no reader, pool, source identity, row key, coin or grouping field. Text and original property/A/B strings or lists are verbatim. Rubric SHA03d9377b... is the frozen §172/E56 rubric. The private grouping map is physically only in ignored cache, mode0600; never give it to a judge or a pod. The packet is shuffled separately from selection/ID streams.

## Exact local paths and transfer

From repository root /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wsae:

- Original blind folder: cache/g_agreement/understand/e76/judged_v1/blind/ (JUDGE_PACKET.json, RUBRIC.txt, BLIND_SEAL.json).
- W-internals' format-only converted folder: cache/g_agreement/understand/e76/judged_v1/converted/ (PACKET.json, RUBRIC.txt, PACKET_SEAL.json). The published channels66_68 converter has already run successfully; all decoded fields/strings/IDs/order are unchanged.
- Private Integrator-only map: cache/g_agreement/understand/e76/judged_v1/GROUPING_MAP.PRIVATE.json. Source lineage: SOURCE_BINDING.PRIVATE.json beside it, sealed by CPU_SEAL.json. Entire judged_v1 directory mode0700; private JSON mode0600.
- ARTIFACTS.json pins separate judge-only and private CPU transport archives under cache. Extract relative to repository root after verifying each SHA256. Large packets/archives and all private files remain outside Git. The private archive also preserves the exact export-time source snapshot/code seal; see ANALYSIS_COMPATIBILITY.20261028.md. Never stage either archive on a pod or attach original text archives directly to an external model; only W-internals' authorised redacted wire is sent.
- Public compact copies BLIND_EXPORT_SEAL.json and CONVERTED_PACKET_SEAL.json preserve their original seal bytes. EXPORT_MANIFEST.json pins the actual cached files and map. CODE_SEAL.json/ANALYSIS_COMMAND_SEAL.json seal the once-only code/spec. No parent E76 source/request seal or original result was changed.

## Integrator judging

Use W-internals' already published E76 placebos channel (47746c16), frozen model/route/rubric and USD2 ledger. JUDGE_RUN_SPEC.template.json points at the already converted packet. Fill the budget and custody receipts from their templates, verify exact complete4992-record expansion and reservation, hash the actual receipts and fill their run-spec pins. The unfilled templates deliberately cannot authorize a call. The existing runner remains responsible for all budget admission, key/token stops, authorised path/address redaction, singleton validation retries and terminal sealing. If its full-packet budget admission does not fit USD2, report that to the coordinator; do not silently cut rows, replace sampled records or alter the frozen n.

Four expanded records require the existing79f63fe0/25c32f25 path/address redaction. No originals were changed. The runner must return JUDGE_COPY.json, PATH_REDACTION_AUDIT.json, START.json, JUDGMENTS.json and RESULT_SEAL.json with all terminal rows present (KEPT or exhausted-retry UNPARSEABLE). This is not yet an analysis result.

## Once-only CPU analysis after terminal seal

Deliver the complete verified terminal directory to:

cache/g_agreement/understand/e76/judged_v1/terminal/final/

Write the Integrator receipt to terminal/VERIFIED_PULL.json from VERIFIED_TERMINAL.template.json: issuer=integrator, experiment=E76_JUDGED, verified_complete=true, privacy_and_budget_custody_verified=true, n=4992, and the exact terminal, converted-packet and original-blind seal hashes. Verify privacy/budget/source custody before attesting. No terminal hash is invented here. The analysis checks the complete exact ID grid, original map, lossless conversion, original full regex floor, exact authorised judge-copy transform/audit, normalized evidence, categories/values and terminal statuses.

Run from the worker repository root, once:

```sh
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 /Users/guivff/Documents/Neel_Exploration/activation-readers/.venv/bin/python results/g_agreement/understand/e76/judged/analyze_once76.py
```

Guard: results/g_agreement/understand/e76/judged/JUDGED_ANALYSIS.RUN_ONCE.json. Outputs: judged/analysis_once_20261028/JUDGED_FLOOR_TABLE.json, JUDGED_FLOOR_TABLE.md and ANALYSIS_SEAL.json. The guard is consumed only after full custody validates and before any category join/score. Preserve it on failure; no automatic analysis retry. This command has not run on real judgments.

S uses the existing E76 independent pseudo-truth (seed20261029, same pool-index coin as regex); it is not source-truth accuracy. Correct-only=+1, wrong-only=-1, both/neither=0; any asserted A/B value, including both, is N=1. UNPARSEABLE is counted, excluded from denominators and flagged over5%; it is never silent/zero. Family rates retain frozen mixture weights; no parseable family makes that row NOT EVALUABLE. Every row/reader/pool gets primary S/N and an affected-ID-excluded sensitivity, with parseable/UNPARSEABLE/redacted counts. Percentile95% CIs use2000 pool-vector bootstrap draws,seed20261027, retaining all families of a vector. No source truth, predicate, rule, sample, rubric or verdict changes.

The Markdown table retains all164 original regex rows (full500-vector S_regex/N estimates and CIs), with the selected43 judged rows, their sampled n and sensitivity estimates beside them. Others are marked not selected, not zero. The original full regex JSON remains linked/pinned unchanged. Original parent analysis/guards and registered verdicts are preserved.

## Checks

13 offline synthetic tests pass, covering deterministic uniform selection/cap/opaque fields, private-map custody, once-only export/analysis guards, exact terminal and redaction custody, frozen validation compatibility, missing/UNPARSEABLE distinctions, signed/both/neither/N denominators, family weighting/vector clustering, no-parseable families and unchanged full regex comparison. audit_export76.py independently replays the frozen draw in memory and verifies all source/packet/map/conversion seals without judging or scoring outcomes. Source packet and map were never rebuilt after sealing. Git's private-history/index checks and the active pre-commit scan must remain clean. Integrator publishes and runs judging/analysis when ready.
