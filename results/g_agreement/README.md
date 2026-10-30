# results/g_agreement — index
- writeup.md — one-page results report (read this first)
- log.md — run log (pod, downloads, R0, dev runs, freeze, test collection, post-freeze notes)
- repro/ — R0 records: r0.json (K0, lens meta, adapter liveness, positive controls, bench vs Suraj), inputs_dump.json, logs, bench/ judge outputs
- claims/ — rule-v1 claims per module (g1, g3, g3_shuffled, g4) and the blind annotation sheet g1_sheet.jsonl (sheet_id, method, text only; map in cache/g_agreement/sheet_map_g1.json)
- g1/ — fig_main.png, agreement.csv (pairwise incl. κ), summary.json, examples.md, consensus.{csv,json} (primary contrast + buckets + LOO); g1/dev = dev plumbing
- g2/, g3/, g4/ — fig_main.png + csv + summary.json each (dev/ subfolders are development-only)
- g5/ (planted binding swap; K4 kill + descriptive LO response), g6/ (self-choice family) — fig_main.png + csv + summary.json; pre-registration in projects/g_agreement/BRIEF_G5G6.md
- direction_review.md — three independent reviews of the research direction + synthesis (2026-10-07)
- x1/, x2/, x3/, x/ — Phase X (BRIEF_X.md): native-LO bank, causal planting (headline x2/fig_main.png), floor item sets, and the blindness map (x/fig_main.png, x/blindness_map.csv)
- summary_for_suraj.md — paste-ready summary of G1–G4
- compute.jsonl — per-step calls, tokens, wall-clock, peak memory on the pod
Raw generations and state provenance: cache/g_agreement/{gens,states,states_meta.jsonl,bench}. Frozen
configuration: projects/g_agreement/manifest/frozen_config_collection.json (collection) and frozen_config.json (analysis).
- summary_for_agam.md — one-page summary for the mentor (2026-10-09; v1 kept as summary_for_agam_v1_2026-10-08.md); headline figure z/fig_headline_readers_vs_model.png (+ .csv, make_fig_headline.py)
- z1/ z2/ z3/ z4/ z4b/ z/ — Phase Z (BRIEF_Z.md): intervention benchmark, counterbalanced X6, equivalence tests, position dissection, ownership follow-up + NLA gate; z/peer_comparison.md
