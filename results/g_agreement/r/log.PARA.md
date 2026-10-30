# H3 secondary (BRIEF_R §14) — run log, text-arm chat (2026-10-19, UTC)

## Running summary (newest first)
- 05:35 Integrator merged r/h3-para through a75cd98 into r/phase-r-scaffold @ 1c0cc16 (suite green); 3.208 h in the Phase R budget row.
  Told it "Text arm v2" (§13, r/text-arm-v2) is not this chat's; this chat's pods total 4.236 billed GPU-h, both stopped.
- 05:29 **Pod j2ftclmzivjt2p self-stopped at 05:28:16 (EXITED, confirmed via the API).** Billed 3.208 GPU-h (≈ $12.8 at $3.99/h):
  H3 3.082 h, CI-10 0.126 h. Inside the 4 GPU-h hard stop (pool p3 ran; nothing was dropped). Ledger:
  `results/g_agreement/compute.PARA.jsonl` (step rows + the pod_billed row). No pod of this chat is running.
- 05:22 WS3: H3's probe-lead clause computed (r/ws3-analyze @ 77cac5d, h3_probe.py). Probe trained on pool items labelled by
  key_model_pos reaches AUROC 0.75 on 109/112 facts, median first layer 24. The readers' TEXT → MODEL crossing exists on 1/108 facts
  (J-lens) and 0/108 (Oracle), so the lead is NOT TESTABLE. **H3 (secondary) stays REFUTED** on clauses 1–2 (all and stable items).
  model_key.PARA.jsonl is a derived table (no pod field; its inputs, the PARA rows and frozen prompt-only rows, carry provenance).
- 05:15 **All steps done** (pool p1/p2 03:18:13–04:33:25, pool p3 04:33:25–05:13:15, exit 0): 232,254 paraphrase rows = all 77,418 R-A
  items × p1–p3, synced. `model_key.PARA.jsonl` written (all 77,418 keyed; pool unstable 8.2%, key ≠ frozen 2.8%, with p3 9.4%). WS3 told
  (for H3's probe-lead clause). File shas: prompt_only.PARA ecdc5859…, model_key.PARA 909a40ad…, ci10_lo 2c0e90f2…, ci10_po 44fb7105….
- 03:25 **WS3 verdicts** (r/ws3-analyze: interim.md, ci10.md). **H3 (secondary: §14 paraphrase key): REFUTED**, with all items and
  with stable items only. At 42–48 every reader sides with the TEXT on 0.46–0.51 of 3,891 conflict items (108 facts), Wilson CI
  entirely < 0.75. At 56, J-lens/Oracle side with the MODEL on 0.52–0.53, CI < 0.60. Readers sit at chance between text and model.
  Key ICC(2,1) median 0.96. The probe-lead clause waits on the pool key and cannot rescue the verdict. **CI-10: claim does not hold**
  for either reader. J-lens @42: 7/18 after 2 state-borne exclusions, 0.39 [0.20, 0.61], sign test vs prompt-only p = 0.25. Oracle @44:
  5/15 after 5 state-borne, 0.33 [0.15, 0.58], p = 0.50. Prompt-only 6/20. WS3 accepts PARA-j2ftclmzivjt2p / 62d8c10 for h3_para/ files only.
- 03:19 **CI-10 done** (03:10:38–03:18:13, exit 0): 8,000 reader rows (20 pairs × 200 × J-lens @42 / Oracle @44) + 4,000 prompt-only,
  0 unscorable; synced; WS3 told. Descriptive only (|AUROC − 0.5| ≥ 0.15, CI excluding 0.5, BEFORE the pre-registered state-borne
  exclusion, Wilson and sign tests, which are WS3's): J-lens 8/20, Oracle 7/20, prompt-only 6/20. Pool p1/p2 began 03:18:13.
- 03:12 **Test split done** (02:22:53–03:10:38, exit 0): 66,594 rows = 22,198 test items × p1/p2/p3, pod PARA-j2ftclmzivjt2p, sha 62d8c10,
  paraphrase sha 1c0d2705; synced to the Mac; WS3 told. Descriptive key stats on test (key = majority {frozen, p1, p2}): unstable 8.0%
  (SURFACE 2.7 … KNOWLEDGE 14.0%), key ≠ single-phrasing pick on 2.7%, conflict counts barely move (COMPUTED 581 → 545, FORM 319 → 323).
  16 datasets > 15% unstable (9 KNOWLEDGE; 137_glue_mnli_neutral 68.5%; 153_it_tick 38.5%, which bears on the H2 caveat). CI-10 began 03:10:38.
- 02:45 Integrator merged r/h3-para through e45bd0a into r/phase-r-scaffold @ 2ab64e9 (BRIEF_R §12 → §13 v2 → §14 H3); full suite 760 passed.
- 02:30 Integrator: Guiv confirmed to it directly that CI-10 (the 20 §14 pairs) is authorised as part of this task (night summary:
  verified). r/h3-para through e45bd0a is in its merge round. Billed hours to be sent split H3 / CI-10 (from the pod's step times).
- 02:23 Smoke passed on j2ftclmzivjt2p (2 items × split × paraphrase on 92/66, 2 CI-10 pairs; `r_unfrozen/h3_para/`). Full run
  started 02:22:53 from `62d8c10` (renumber + scaffold merge; §14 heading time corrected to 02:15 UTC = commit 986f5fe): test p1–p3 →
  CI-10 → pool p1/p2 → pool p3; hard stop 06:00:47 (4 GPU-h from creation − 15-min pull window), then self-stop.
- 02:20 Pod j2ftclmzivjt2p (mats-minis-para, H100 SXM, $3.99/h, mats-minis volume) created 02:15:47. Section renumbered §13 → §14 at
  the integrator's request ("§13. Text arm v2" merged first); heading and self-references only. The committed paraphrase file keeps
  "BRIEF_R §13" in its meta.purpose string (changing it would change the pinned sha). CI-10 kept: Guiv's task message said "If cheap,
  include --no-activation and --candidates-from in the same module", and §14 pre-registers it (told the integrator).
- 02:16 Pod: d6lq9yaejceqxv cannot resume (host full); a resume-or-create loop (H100 SXM / NVL / PCIe on the mats-minis volume,
  EUR-IS-3, every 90 s, up to 2 h) is running. Integrator sent the budget (billed GPU-h); billed split of the previous pod sent.
- 02:14 Pre-registered BRIEF_R §13 and pushed it with the paraphrase file before any scoring: `r/h3-para` @ `986f5fe`;
  `dataset/h3_paraphrases.json` sha256 `1c0d2705917e220357bc79c005f9b550dd5825d6b5c36d7cb442f0f2794a10f8` (pinned in
  `h3_para.PARA_SHA256`). Key = majority of {frozen, p1, p2} (p2 swaps the candidate order); p3 descriptive. All R-A test and pool
  items. Rule unchanged from §4.3 / §1. BD-7 = the §12 text arm (delegate, no new rows); CI-10 = 20 fixed pairs, J-lens @42 + Oracle @44 + prompt-only.
- 02:05 Task from Guiv: H3 via option A on `r/h3-para` (branch from the scaffold tip `9a3ae8f`). H3 stays NOT RUN in the primary table.
- Notes: the paraphrases were written after single-phrasing prompt-only data and WS3's descriptive R3 existed, blind to results
  (fixed templates, question and candidates verbatim). The named CI-10 pair 92→21 is TOPIC on TOPIC (flagged in §13).
  Possible section-number collision: the integrator mentioned a "§13 v2" text arm by another stream; offered to renumber this §14 at merge.

## Runs

| run | pod | code | started (UTC) | ended | rows | command |
|---|---|---|---|---|---|---|
| smoke | j2ftclmzivjt2p | 62d8c10 | 02:20 | 02:22 | 24 para + 800 ci10_lo + 400 ci10_po (`r_unfrozen/h3_para/`) | `h3_para --para --ci10 --smoke 2 --datasets 92_glue_sst2 66_living-room` |
| full: test p1–p3 | j2ftclmzivjt2p | 62d8c10 | 02:22:53 | 03:10:38 (exit 0) | 66,594 | `h3_para --para --splits test --paraphrases p1 p2 p3` |
| full: CI-10 | j2ftclmzivjt2p | 62d8c10 | 03:10:38 | 03:18:13 (exit 0) | 8,000 lo + 4,000 po | `h3_para --ci10` |
| full: pool p1/p2 | j2ftclmzivjt2p | 62d8c10 | 03:18:13 | 04:33:25 (exit 0) | 110,440 | `h3_para --para --splits pool --paraphrases p1 p2` |
| full: pool p3 | j2ftclmzivjt2p | 62d8c10 | 04:33:25 | 05:13:15 (exit 0) | 55,220 | `h3_para --para --splits pool --paraphrases p3` |

## Pod log (`log.PARA.md` written on the pod by `collect.rlog`)

# H3 secondary (BRIEF_R §14) — run log, text-arm chat (2026-10-19, UTC)

## Running summary (newest first)
- 02:20 Pod j2ftclmzivjt2p (mats-minis-para, H100 SXM, $3.99/h, mats-minis volume) created 02:15:47. Section renumbered §13 → §14 at
  the integrator's request ("§13. Text arm v2" merged first); heading and self-references only. The committed paraphrase file keeps
  "BRIEF_R §13" in its meta.purpose string (changing it would change the pinned sha). CI-10 kept: Guiv's task message said "If cheap,
  include --no-activation and --candidates-from in the same module", and §14 pre-registers it (told the integrator).
- 02:16 Pod: d6lq9yaejceqxv cannot resume (host full); a resume-or-create loop (H100 SXM / NVL / PCIe on the mats-minis volume,
  EUR-IS-3, every 90 s, up to 2 h) is running. Integrator sent the budget (billed GPU-h); billed split of the previous pod sent.
- 02:14 Pre-registered BRIEF_R §13 and pushed it with the paraphrase file before any scoring: `r/h3-para` @ `986f5fe`;
  `dataset/h3_paraphrases.json` sha256 `1c0d2705917e220357bc79c005f9b550dd5825d6b5c36d7cb442f0f2794a10f8` (pinned in
  `h3_para.PARA_SHA256`). Key = majority of {frozen, p1, p2} (p2 swaps the candidate order); p3 descriptive. All R-A test and pool
  items. Rule unchanged from §4.3 / §1. BD-7 = the §12 text arm (delegate, no new rows); CI-10 = 20 fixed pairs, J-lens @42 + Oracle @44 + prompt-only.
- 02:05 Task from Guiv: H3 via option A on `r/h3-para` (branch from the scaffold tip `9a3ae8f`). H3 stays NOT RUN in the primary table.
- Notes: the paraphrases were written after single-phrasing prompt-only data and WS3's descriptive R3 existed, blind to results
  (fixed templates, question and candidates verbatim). The named CI-10 pair 92→21 is TOPIC on TOPIC (flagged in §13).
  Possible section-number collision: the integrator mentioned a "§13 v2" text arm by another stream; offered to renumber this §14 at merge.

## Runs

| run | pod | code | started (UTC) | ended | rows | command |
|---|---|---|---|---|---|---|
- 2026-10-19T02:19:24.838129+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: run={'pod': 'PARA-j2ftclmzivjt2p', 'shard': None, 'git_sha': '62d8c10f872fbf0a2ef7618c610be2fd2bf3d4fc'} code_sha=adee68d42302629e50debd70c6fe3603c099836894a279826d96d544e32139c8 banks={'items_r.json': '2dbde3a272186ac4e3f669fe4fab5e40d97feb5e3cdfd4ba35beed422ded13f5'} paraphrases=['p1', 'p2', 'p3'] splits=['test', 'pool'] ci10=True smoke=2 out=/workspace/activation-readers-para/cache/g_agreement/r_unfrozen/h3_para
- 2026-10-19T02:21:13.058852+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para test p1: done, 4 new rows so far
- 2026-10-19T02:21:13.313862+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para test p2: done, 8 new rows so far
- 2026-10-19T02:21:13.601966+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para test p3: done, 12 new rows so far
- 2026-10-19T02:21:14.826324+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para pool p1: done, 16 new rows so far
- 2026-10-19T02:21:15.070472+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para pool p2: done, 20 new rows so far
- 2026-10-19T02:21:15.411180+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para pool p3: done, 24 new rows so far
- 2026-10-19T02:21:23.779577+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] olens adapter=/workspace/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600 liveness={'n_keys': 992, 'n_matched': 992, 'n_lora_modules': 496, 'all_matched': True, 'adapter_name': 'default', 'max_abs_logit_delta': 18.810546875}
- 2026-10-19T02:22:13.355364+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para ci10: 20 pairs done
- 2026-10-19T02:22:13.361635+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: 1224 new rows in 1.6 min -> /workspace/activation-readers-para/cache/g_agreement/r_unfrozen/h3_para
- 2026-10-19T02:22:44.573944+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para ledger: ci10_jlens_L42 2s×2; ci10_olens_L44 20s×2; ci10_prompt_only 20s×26
- 2026-10-19T02:22:55.372075+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: run={'pod': 'PARA-j2ftclmzivjt2p', 'shard': None, 'git_sha': '62d8c10f872fbf0a2ef7618c610be2fd2bf3d4fc'} code_sha=adee68d42302629e50debd70c6fe3603c099836894a279826d96d544e32139c8 banks={'items_r.json': '2dbde3a272186ac4e3f669fe4fab5e40d97feb5e3cdfd4ba35beed422ded13f5'} paraphrases=['p1', 'p2', 'p3'] splits=['test'] ci10=False smoke=None out=/workspace/activation-readers-para/cache/g_agreement/r/h3_para
- 2026-10-19T02:39:46.046767+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para test p1: done, 22198 new rows so far
- 2026-10-19T02:54:39.138477+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para test p2: done, 44396 new rows so far
- 2026-10-19T03:10:04.927131+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para test p3: done, 66594 new rows so far
- 2026-10-19T03:10:04.938723+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: 66594 new rows in 46.0 min -> /workspace/activation-readers-para/cache/g_agreement/r/h3_para
- 2026-10-19T03:10:37.074692+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para ledger: 
- 2026-10-19T03:10:40.553118+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: run={'pod': 'PARA-j2ftclmzivjt2p', 'shard': None, 'git_sha': '62d8c10f872fbf0a2ef7618c610be2fd2bf3d4fc'} code_sha=adee68d42302629e50debd70c6fe3603c099836894a279826d96d544e32139c8 banks={'items_r.json': '2dbde3a272186ac4e3f669fe4fab5e40d97feb5e3cdfd4ba35beed422ded13f5'} paraphrases=['p1', 'p2', 'p3'] splits=['test', 'pool'] ci10=True smoke=None out=/workspace/activation-readers-para/cache/g_agreement/r/h3_para
- 2026-10-19T03:12:05.849920+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] olens adapter=/workspace/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600 liveness={'n_keys': 992, 'n_matched': 992, 'n_lora_modules': 496, 'all_matched': True, 'adapter_name': 'default', 'max_abs_logit_delta': 18.810546875}
- 2026-10-19T03:17:39.916077+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para ci10: 20 pairs done
- 2026-10-19T03:17:39.921151+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: 12000 new rows in 5.7 min -> /workspace/activation-readers-para/cache/g_agreement/r/h3_para
- 2026-10-19T03:18:11.872671+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para ledger: ci10_jlens_L42 17s×20; ci10_olens_L44 100s×20; ci10_prompt_only 143s×260
- 2026-10-19T03:18:15.229984+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: run={'pod': 'PARA-j2ftclmzivjt2p', 'shard': None, 'git_sha': '62d8c10f872fbf0a2ef7618c610be2fd2bf3d4fc'} code_sha=adee68d42302629e50debd70c6fe3603c099836894a279826d96d544e32139c8 banks={'items_r.json': '2dbde3a272186ac4e3f669fe4fab5e40d97feb5e3cdfd4ba35beed422ded13f5'} paraphrases=['p1', 'p2'] splits=['pool'] ci10=False smoke=None out=/workspace/activation-readers-para/cache/g_agreement/r/h3_para
- 2026-10-19T03:56:17.999424+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para pool p1: done, 55220 new rows so far
- 2026-10-19T04:32:53.832188+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para pool p2: done, 110440 new rows so far
- 2026-10-19T04:32:53.840147+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: 110440 new rows in 73.4 min -> /workspace/activation-readers-para/cache/g_agreement/r/h3_para
- 2026-10-19T04:33:23.678647+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para ledger: 
- 2026-10-19T04:33:26.892312+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: run={'pod': 'PARA-j2ftclmzivjt2p', 'shard': None, 'git_sha': '62d8c10f872fbf0a2ef7618c610be2fd2bf3d4fc'} code_sha=adee68d42302629e50debd70c6fe3603c099836894a279826d96d544e32139c8 banks={'items_r.json': '2dbde3a272186ac4e3f669fe4fab5e40d97feb5e3cdfd4ba35beed422ded13f5'} paraphrases=['p3'] splits=['pool'] ci10=False smoke=None out=/workspace/activation-readers-para/cache/g_agreement/r/h3_para
- 2026-10-19T05:12:27.724744+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para pool p3: done, 55220 new rows so far
- 2026-10-19T05:12:27.732869+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para: 55220 new rows in 37.9 min -> /workspace/activation-readers-para/cache/g_agreement/r/h3_para
- 2026-10-19T05:13:14.086612+00:00 [pod=PARA-j2ftclmzivjt2p shard=None sha=62d8c10f87] h3_para ledger: 

## Pod status file (`/workspace/para_logs/status`)

```
[2026-10-19T02:22:53Z] start on j2ftclmzivjt2p (124bfda5d5ba), sha 62d8c10f872fbf0a2ef7618c610be2fd2bf3d4fc, deadline 06:00:47
[2026-10-19T02:22:53Z] begin test (13074s left)
[2026-10-19T03:10:38Z] end test exit 0
[2026-10-19T03:10:38Z] begin ci10 (10209s left)
[2026-10-19T03:18:13Z] end ci10 exit 0
[2026-10-19T03:18:13Z] begin pool_key (9754s left)
[2026-10-19T04:33:25Z] end pool_key exit 0
[2026-10-19T04:33:25Z] begin pool_p3 (5242s left)
[2026-10-19T05:13:15Z] end pool_p3 exit 0
[2026-10-19T05:13:15Z] exit 0
```
