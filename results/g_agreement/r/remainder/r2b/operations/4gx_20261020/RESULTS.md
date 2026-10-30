# R2-B registered relaunch — 2026-10-21

Science and packaging exited 0 at 01:16:41Z and 01:17:18Z. Source/prereg: cd852cf28f30ed696c47565643f88b685ef10c24. Single H100 4gxvdaohpuy410; exact volume w9182om1pd. Frozen scope unchanged; no R6.

Coverage: 2752 capture rows, 2752 source rows, 17 source fits, 51 internal/transfer fits, 51 causal smoke rows, 2112 causal rows = 704 items × 3 arms, five analysis groups. Both registered timing gates passed. Seed 20261020; 2000 bootstrap draws.

Differences below are percentage points of equal-fact macro balanced accuracy. Mean denotes decoded-direction mean ablation. Random is the matched equal-norm orthogonal control.

| Group | n | Mean − sham | Mean − random | Inference |
|---|---:|---:|---:|---|
| main / base / pool-selected | 320 | 0.000 [-0.469, 0.469] | 0.000 [-0.469, 0.469] | Complete registered intervals |
| taught / sft / forward-block transfer | 96 | -1.042 [-3.125, 0.000] | 0.000 [0.000, 0.000] | Item-only interval; cluster inference incomplete |
| taught / sft / pool-selected | 96 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | Complete registered intervals |
| taught / sft_dpo / forward-block transfer | 96 | -1.042 [-3.125, 0.000] | -1.042 [-3.125, 0.000] | Item-only interval; cluster inference incomplete |
| taught / sft_dpo / pool-selected | 96 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | Complete registered intervals |

Main intervals are the wider envelope of item, fact and corpus intervals. Forward taught groups have item and entity-group intervals. Both reverse/forward-block-transfer groups have only 1687/2000 valid entity-group bootstrap draws, below the frozen 90% threshold: cluster intervals are null and inference_complete=false. Their displayed intervals are item-only and must not be described as complete registered inference. No threshold was relaxed or bootstrap retried.

These small accuracy changes do not establish absence of encoded information or rule out redundant mechanisms. No new categorical mechanistic verdict is assigned. Full machine-readable contrasts, including random − sham, are in analysis_rows.jsonl. Raw states remain on the network volume; compact rows, fit inputs/parameters, logs and manifests are retained in cache/g_agreement/r/remainder/r2b/4gx_20261020/pull. Final stop/billing is recorded separately in completion.json.

taught facts decodable at 1.00 through Oracle block 48; decoded-direction ablation changes Oracle accuracy by 0 pp; single-direction ablation, redundancy not excluded.
