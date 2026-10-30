# S8 log (S7 chat, 2026-10-16)
- 11:35 CEST S8 pre-registered by another chat (8cc1a0a); 11:53 amendment per Guiv's revised brief (bc1bf4f), before any S8 number.
- 11:50 started pod e ngqf1fs0y9wde8 (1x H100, volume mats-minis); lock file /workspace/LOCK_s8x.md (removed at end).
- CPU (Mac): `.venv/bin/python projects/g_agreement/s8/s8_cpu.py --data-root <main checkout>` (35 s): J-lens three-way at 42/48/52/56,
  J-lens top-10 at 42/56, probe per block, S8a J-lens over 29 names at 42/44. F2-2 readvecs.pt + behaviour.jsonl rsynced from the pod.
- Pod: `/workspace/s8x_chain.sh` = s8_pod.py --phase O (Oracle; 26.2 min incl. 3.7 min load) then --phase N (NLA; 41.2 min incl. 3.1 min load);
  batch 48; free-text seeds 20261016 + 1000*L + batch offset; outputs cache/g_agreement/s8x/{native,freetext}.jsonl.
- Oracle liveness: 992/992 keys matched, max |logit delta| 18.82.
- 11:02 UTC pod stopped. GPU time 09:50–11:02 UTC = 1.20 GPU-h.
- `.venv/bin/python projects/g_agreement/s8/s8_analyze.py --data-root <main checkout>` -> s8.csv, s8b_table.md, s8a_table.md, s8_summary.json.
