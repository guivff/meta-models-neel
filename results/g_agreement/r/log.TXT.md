# Text-arm chat — night log (2026-10-18/19, UTC)

## Running summary (newest first)
- 00:42 WS3 flagged 101_disease_class's permuted class names (145, 146, parent 101). §12 exclusions NOT changed (pre-registered);
  added a sensitivity table without them (`text_arm_ex_ws3_defects.csv`, 108 facts; dated BRIEF_R §12 Deviation). No verdict
  changes: both facts were not distinguished at both sites (TOPIC chat 7/7/9 → 7/7/7, raw 3/6/14 → 3/6/12). WS3 told.
- 00:31 WS9 recorded the Qwen numbers in `results/g_agreement/rg/report.md` §5 ("Qwen counterpart") with the prompt-design caveat
  first (only SURFACE / passage comparable; COMPUTED reversal expected from the prompt). Proposed (card, not started) a separate
  session for a pre-registered question-bearing + text-and-activation arm on Qwen. Nothing owed to any chat; no pod running.
- 00:27 WS9 (Gemma) sent its analogue: text − activation +0.094 chat (69 vs 4 facts), +0.029 raw; text+activation = text alone.
  Qwen in that convention (fact-level iid bootstrap): chat +0.005 [−0.029, +0.038] (45 vs 42 facts), raw −0.016 [−0.033, +0.002];
  SURFACE +0.145 and PASSAGE-KNOWLEDGE +0.115 agree with Gemma's sign, COMPUTED −0.211 and KNOWLEDGE −0.043 do not. **Not like for like:**
  Qwen's text arm keeps the frozen question-free "concepts" Oracle prompt, Gemma's AO prompt carries the dataset question, so
  COMPUTED cannot be judged from the text on Qwen. A question-bearing + text-and-activation arm on Qwen would need its own
  pre-registration and a pod; not started (no instruction to). Told WS9.
- 00:22 Integrator: r/text-arm through d2fb8e5 is on r/phase-r-scaffold @ 77cd6de; ledger note taken (pod_billed = pod total,
  step rows are busy time, never summed with it). All of this chat's work is merged; open item only: ReaderBench Oracle activation rows.
- 00:19 **Pod d6lq9yaejceqxv self-stopped at 00:18:45 (EXITED, confirmed via the API).** Billed 1.028 GPU-h
  (≈ $4.1): text arm 0.705 h,
  replication + pull window 0.323 h. GPU-busy
  scoring: text arm 21.6 min (1,297 s), replication ≈ 4 min. Ledger: `results/g_agreement/compute.TXT.jsonl` (pod row) and `compute.REP.jsonl`.
  No pod of this chat is running.
- 00:09 Integrator: r/text-arm through b50592c is on r/phase-r-scaffold @ 1e2b552 (with WS3's 60e57c8); 11/11 text-arm tests pass
  there under WS3's provenance filter; the §4.9 c wording ambiguity is logged as recorded-not-resolved, verdict on the pre-registered wording.
- 00:08 WS3 confirmed independently (its §4.9 c evaluator on `h2_replication_153_lo.jsonl`, its prompt-only rows): REPLICATED;
  **H2 is therefore REFUTED as pre-registered**, with the below-chance-ceiling caveat stated next to it (r/ws3-analyze @ 1b87210).
  `text_arm_lo.jsonl` passes WS3's provenance check (side arm only) and fills its Check-2 column from the next interim. Nothing
  further owed to WS3 unless ReaderBench Oracle activation rows land (then: rerun `text_arm --analyze`, message WS3).
- 00:06 **§4.9 c replication of olens 153 REPLICATES** on the 200 fresh pool items (both readings): @44 chat Δ = AUROC(olens) −
  AUROC(prompt-only) = +0.268 [+0.163, +0.370], one-sided lower bound +0.179 (WS3's prompt-only rows; re-scored: +0.267). Every other
  site passes too (chat 42–56 Δ +0.24…+0.30; raw +0.13…+0.14). Caveat sent to WS3: Oracle 0.548 is near chance; the gap is the
  model's own report being INVERTED (prompt-only 0.28), raw Oracle 0.41. Verdict is WS3's. Run 23:59:42–00:03:45, exit 0, 2,000
  olens rows → `cache/g_agreement/r/text_arm/h2_replication_153_lo.jsonl`; `results/g_agreement/r/h2_replication_153_result.json`.
- 00:05 First activation − text table (R-A, 110 facts; ReaderBench Oracle activation rows not yet written). Chat @44 (primary):
  34 facts READ FROM THE STATE / 40 TEXT SUFFICES / 36 not distinguished; COMPUTED 13/0/4 (median Δ +0.229), SURFACE 3/22/3
  (text 0.938 vs act 0.741), PASSAGE-KNOWLEDGE 0/6/3, KNOWLEDGE 7/2/12, TOPIC 7/7/9. Raw @44: 26/14/70. Table below; per fact
  `results/g_agreement/r/text_arm.csv`. WS3 told (pod `TXT-d6lq9yaejceqxv`, git_sha 08d6a19, file sha 52aaf5a3…).
- 23:59 Text arm done: 30,194 rows (R-A 22,198 + ReaderBench 7,996) in 23.9 min, exit 0; rows synced to the Mac
  (`cache/g_agreement/r/text_arm/text_arm_lo.jsonl`). keep_alive cancelled the self-stop; the 153 replication started 23:59:42.
- 23:58 Integrator merged 08d6a19; fixture fix for WS3's provenance filter pushed (`b1081da`).
- 23:55 Pre-registered (BRIEF_R §12 Deviations) and queued the §4.9 c replication of `olens 153_it_tick_Administrative rights`
  on the same pod after the text arm: frozen collect.py from the 4d482b6 tree, `--suffix REP`, own cache root `rep153/`,
  WS3's 200 fresh pool items. WS3 acked with provenance (pod `REP-d6lq9yaejceqxv`, sha 4d482b6). Self-stop moved to the end of the REP chain.
- 23:50 Guiv: keep the pod (H100s sold out). `keep_alive.sh` on the pod cancels the text arm's self-stop once it exits.
- 23:34 Full text-arm run restarted on `08d6a19`; rows → `cache/g_agreement/r/text_arm/text_arm_lo.jsonl`, `condition: "text_arm"`
  (renamed at Guiv's request so analyze.py's `reader_lo.*.jsonl` glob never merges them; the first full run was killed during
  the model load, no row written under the old name).
- 23:24–23:27 Smoke (4 items × 4 datasets) passed: rows carry pod / git_sha / code sha; Oracle LoRA live (992/992 keys).
- 23:17 Pod `d6lq9yaejceqxv` (mats-minis-txt, H100 SXM, EUR-IS-3, mats-minis volume, $3.99/h) created after 5 min of SUPPLY_CONSTRAINT retries.
- 23:05 BRIEF_R §12 "Text arm" pre-registered and pushed (`e3b40d3`) before any compute; code `4fae558`.
- Notes: rebuilding the banks from the scaffold tip does NOT reproduce the frozen shas; the run uses the main checkout's frozen
  copies (sha-checked). `/workspace/.env` exports another pod's `RUNPOD_POD_ID`; every self-stop uses the explicit pod id.

## Runs

| run | pod | code | started (UTC) | ended | rows | command |
|---|---|---|---|---|---|---|
| smoke | d6lq9yaejceqxv | 2fc4ee8 | 23:23:58 | 23:27:30 | 16 (r_unfrozen, moved to `r_unfrozen/text_arm/smoke_v1_reader_lo_TXT.jsonl`) | `text_arm_pod.sh <id> smoke` |
| full v1 | d6lq9yaejceqxv | 2fc4ee8 | 23:31:34 | killed 23:33 during model load | 0 | `text_arm_pod.sh <id> full` |
| full | d6lq9yaejceqxv | 08d6a19 | 23:33:58 | 23:59:22 (exit 0) | 30,194 (`text_arm/text_arm_lo.jsonl`) | `text_arm_pod.sh <id> full` (`text_arm --pod TXT-<id>`) |
| rep153 | d6lq9yaejceqxv | 4d482b6 tree | 23:59:42 | 00:03:45 (exit 0) | 2,000 olens + 200 prompt-only (`rep153/*.REP.jsonl`) | `replication_pod.sh <id> 153` (`collect --phase A --readers olens --suffix REP --allow-unfrozen --cache-dir …/rep153`) |

## First activation − text table (2026-10-19 00:05 UTC; Oracle shards synced 01:51 local; R-A only, 110 facts)
Counts = facts READ FROM THE STATE / TEXT SUFFICES / not distinguished (BRIEF_R §12 rule, BH q = 0.10 within tag).

### activation (Oracle, block 44, chat) − text (olens_txt)

| tag | facts | AUROC act | AUROC text | median Δ | Δ > 0 | state | text suffices | n.d. |
|---|---|---|---|---|---|---|---|---|
| COMPUTED | 17 | 0.744 | 0.550 | +0.229 | 15 | 13 | 0 | 4 |
| FORM | 6 | 0.602 | 0.526 | +0.109 | 4 | 3 | 1 | 2 |
| KNOWLEDGE | 21 | 0.680 | 0.606 | +0.002 | 12 | 7 | 2 | 12 |
| META | 6 | 0.636 | 0.634 | -0.086 | 1 | 1 | 2 | 3 |
| PASSAGE-KNOWLEDGE | 9 | 0.593 | 0.748 | -0.137 | 1 | 0 | 6 | 3 |
| SURFACE | 28 | 0.741 | 0.938 | -0.184 | 6 | 3 | 22 | 3 |
| TOPIC | 23 | 0.549 | 0.552 | +0.007 | 12 | 7 | 7 | 9 |
| ALL | 110 | 0.693 | 0.611 | -0.014 | 51 | 34 | 40 | 36 |

### activation (Oracle, block 44, raw) − text (olens_txt)

| tag | facts | AUROC act | AUROC text | median Δ | Δ > 0 | state | text suffices | n.d. |
|---|---|---|---|---|---|---|---|---|
| COMPUTED | 17 | 0.623 | 0.550 | +0.091 | 13 | 9 | 0 | 8 |
| FORM | 6 | 0.538 | 0.526 | +0.019 | 3 | 0 | 0 | 6 |
| KNOWLEDGE | 21 | 0.660 | 0.606 | +0.067 | 16 | 10 | 0 | 11 |
| META | 6 | 0.587 | 0.634 | -0.032 | 3 | 1 | 2 | 3 |
| PASSAGE-KNOWLEDGE | 9 | 0.796 | 0.748 | +0.026 | 5 | 2 | 1 | 6 |
| SURFACE | 28 | 0.913 | 0.938 | -0.008 | 11 | 1 | 5 | 22 |
| TOPIC | 23 | 0.550 | 0.552 | -0.006 | 10 | 3 | 6 | 14 |
| ALL | 110 | 0.664 | 0.611 | +0.011 | 61 | 26 | 14 | 70 |

## Pod log (text arm, `log.TXT.md` written on the pod by `collect.rlog`)

- 2026-10-18T23:24:00.013849+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=2fc4ee8b01] text arm (olens_txt, prompt layer 44): run={'pod': 'TXT-d6lq9yaejceqxv', 'shard': None, 'git_sha': '2fc4ee8b0136b5f0ad4a442e6530d0ba47637d4a'} code_sha=adfeff1b256f616a8cde88ced312222c7c6adaa4f1866713e26e55e14bf74813 banks={'items_r.json': '2dbde3a272186ac4e3f669fe4fab5e40d97feb5e3cdfd4ba35beed422ded13f5', 'items_rb.json': 'd349df4cca72eb9dbdb6e8ab39d79d18ed2270462e696084cac7315b46ec334f'} 16 test items, cache=/workspace/activation-readers-txt/cache/g_agreement/r_unfrozen, smoke=4
- 2026-10-18T23:26:55.090377+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=2fc4ee8b01] olens adapter=/workspace/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600 liveness={'n_keys': 992, 'n_matched': 992, 'n_lora_modules': 496, 'all_matched': True, 'adapter_name': 'default', 'max_abs_logit_delta': 18.822265625}
- 2026-10-18T23:26:59.657723+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=2fc4ee8b01] text arm: 16 new rows in 0.1 min -> /workspace/activation-readers-txt/cache/g_agreement/r_unfrozen/reader_lo.TXT.jsonl
- 2026-10-18T23:27:29.278539+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=2fc4ee8b01] text arm ledger: lo_olens_txt_L44 4s×4
- 2026-10-18T23:31:35.722423+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=2fc4ee8b01] text arm (olens_txt, prompt layer 44): run={'pod': 'TXT-d6lq9yaejceqxv', 'shard': None, 'git_sha': '2fc4ee8b0136b5f0ad4a442e6530d0ba47637d4a'} code_sha=adfeff1b256f616a8cde88ced312222c7c6adaa4f1866713e26e55e14bf74813 banks={'items_r.json': '2dbde3a272186ac4e3f669fe4fab5e40d97feb5e3cdfd4ba35beed422ded13f5', 'items_rb.json': 'd349df4cca72eb9dbdb6e8ab39d79d18ed2270462e696084cac7315b46ec334f'} 30194 test items, cache=/workspace/activation-readers-txt/cache/g_agreement/r, smoke=None
- 2026-10-18T23:32:24.128069+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=2fc4ee8b01] olens adapter=/workspace/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600 liveness={'n_keys': 992, 'n_matched': 992, 'n_lora_modules': 496, 'all_matched': True, 'adapter_name': 'default', 'max_abs_logit_delta': 18.822265625}
- 2026-10-18T23:33:59.755658+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=08d6a196cb] text arm (olens_txt, prompt layer 44): run={'pod': 'TXT-d6lq9yaejceqxv', 'shard': None, 'git_sha': '08d6a196cb4fe6dc57c52cb5fc44d52ed79adda1'} code_sha=0b714b8007d2195f008ef0988eb8bb857d64fc6ab6cc3f77f57d91eabd126b40 banks={'items_r.json': '2dbde3a272186ac4e3f669fe4fab5e40d97feb5e3cdfd4ba35beed422ded13f5', 'items_rb.json': 'd349df4cca72eb9dbdb6e8ab39d79d18ed2270462e696084cac7315b46ec334f'} 30194 test items, cache=/workspace/activation-readers-txt/cache/g_agreement/r, smoke=None
- 2026-10-18T23:34:53.718295+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=08d6a196cb] olens adapter=/workspace/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600 liveness={'n_keys': 992, 'n_matched': 992, 'n_lora_modules': 496, 'all_matched': True, 'adapter_name': 'default', 'max_abs_logit_delta': 18.822265625}
- 2026-10-18T23:58:49.797761+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=08d6a196cb] text arm: 30194 new rows in 23.9 min -> /workspace/activation-readers-txt/cache/g_agreement/r/text_arm/text_arm_lo.jsonl
- 2026-10-18T23:59:21.123579+00:00 [pod=TXT-d6lq9yaejceqxv shard=None sha=08d6a196cb] text arm ledger: lo_olens_txt_L44 1297s×168

## Pod log (153 replication, `log.REP.md` written on the pod by frozen collect.py)

- 2026-10-18T23:59:42.482583+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] phase A: run={'pod': 'REP-d6lq9yaejceqxv', 'shard': None, 'git_sha': '4d482b612b0da5838b83e43a4c85656daec7f778'} 1 datasets, 200 items, renders=('chat', 'raw'), kway=False, items=items_rep153.json, cache=/workspace/mats-minis/cache/g_agreement/r/rep153, readers=['olens'], read_position datasets=[], reader_states=None, olens_alpha_scales=None, shas={'items_file': 'items_rep153.json', 'items_sha256': '4368add7565672e21a29812079c28c1aded78b50074ed6d351bfda9b1e220ec0', 'current_r_code_sha256': '279a305e2cd91e0435dd5fd15d3879ebbb0641b8fe03831b1c780397afc81536', 'frozen_r_code_sha256': '4f5e2070468c7507b206602ab5276a08aac865d1038c63b966e7bbbc066dbe5e'}
- 2026-10-19T00:01:06.013770+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] 153_it_tick_Administrative rights: 200 items; capture {'chat': 9.962000000000002, 'raw': 4.575}; prompt_only 200 new rows; model_labels 0; re_relabel 0; 30s
- 2026-10-19T00:01:06.018050+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] capture + prompt_only: 1 datasets in 0.5 min
- 2026-10-19T00:01:11.026413+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] olens adapter=/workspace/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600 liveness={'n_keys': 992, 'n_matched': 992, 'n_lora_modules': 496, 'all_matched': True, 'adapter_name': 'default', 'max_abs_logit_delta': 18.822265625}
- 2026-10-19T00:01:35.294843+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] lo olens L42: 800 new rows, renders=('chat', 'raw'), 24s
- 2026-10-19T00:02:01.562272+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] lo olens L44: 800 new rows, renders=('chat', 'raw'), 26s
- 2026-10-19T00:02:26.617736+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] lo olens L48: 800 new rows, renders=('chat', 'raw'), 25s
- 2026-10-19T00:02:50.659648+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] lo olens L52: 800 new rows, renders=('chat', 'raw'), 24s
- 2026-10-19T00:03:13.249599+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] lo olens L56: 800 new rows, renders=('chat', 'raw'), 23s
- 2026-10-19T00:03:43.784570+00:00 [pod=REP-d6lq9yaejceqxv shard=None sha=4d482b612b] phase A ledger: capture_chat 10s×13; capture_raw 5s×13; prompt_only 11s×13; lo_olens_L42 10s×2; control_olens_L42 11s×4; lo_olens_L44 10s×2; control_olens_L44 10s×4; lo_olens_L48 10s×2; control_olens_L48 10s×4; lo_olens_L52 10s×2; control_olens_L52 10s×4; lo_olens_L56 10s×2; control_olens_L56 10s×4

## Pod status file (`/workspace/txt_logs/status`)

```
[2026-10-18T23:23:58Z] start smoke on d6lq9yaejceqxv (55ff68c9c737), sha 2fc4ee8b0136b5f0ad4a442e6530d0ba47637d4a
[2026-10-18T23:27:30Z] smoke exit 0
[2026-10-18T23:31:34Z] start full on d6lq9yaejceqxv (55ff68c9c737), sha 2fc4ee8b0136b5f0ad4a442e6530d0ba47637d4a
[2026-10-18T23:33:58Z] start full on d6lq9yaejceqxv (55ff68c9c737), sha 08d6a196cb4fe6dc57c52cb5fc44d52ed79adda1
[2026-10-18T23:59:22Z] exit 0
[2026-10-18T23:59:25Z] self-stop cancelled by keep_alive.sh (pod kept for the REP run)
[2026-10-18T23:59:42Z] rep153 start on d6lq9yaejceqxv, tree sha 4d482b612b0da5838b83e43a4c85656daec7f778
[2026-10-19T00:03:45Z] rep153 exit 0
```
