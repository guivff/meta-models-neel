# What Suraj's repository gives us (mats-nla-workspace-main, received 2026-10-07)

Location: `third_party/mats-nla-workspace-main/` (read-only copy; his confirmation banks and pilot
splits are never touched by the G pipeline). 296 Python files, no model weights, two small `.npz`
power-simulation inputs; the Modal result volumes (`/results/...`) are NOT included.

## Conventions: identical to ours (no change needed)
| item | his (experiments/00_nla_gate/RESULTS.md, src/mats/readers) | ours (core/config.py, core/readers.py) |
|---|---|---|
| read site | output of `model.layers[42]` = `hidden_states[43]`, last token | same |
| NLA | av_base + `iter_000400`, actor prompt via chat template, `enable_thinking=False`, marker 158983 between (29, 510), ADD norm-matched at block-1 output | same |
| Oracle lens | `olens_s3d_rl600` (byte-identical to the bench default, verified by him), prompt `concepts_raw`, layer integer 42, REPLACE embedding by 16000·unit(h), adapter off for capture | same |
| J-lens | neuronpedia n1000, cosine readout, top-10 | same |
| verbalizer sampling | T=1.0, top_p 0.95, top_k 64 (bench); 256 new tokens, batched 64 (OL) / 50 (NLA) | same sampling; cap 128; batch 1 with per-call seeds |
| NLA prompt with thinking on | 205/256 samples never close `</explanation>` (documented) | we use thinking off |

## Reproduction targets we now have (single layer 42, n = 100, regex instrument)
From `experiments/01_wsbench_replication/RESULTS.md`: Oracle lens L42 typo_mt 0.76, multilingual_mt 0.28,
multihop_mt 0.10, basic_readout_mt 0.45; NLA L42 typo_mt 0.73, multilingual_mt 0.42, multihop_mt 0.15,
basic_readout_mt 0.57. K0: block-42 median cosine 0.9999, mean relative L2 0.026 (block 41: 0.979 / 0.222;
block 43: 0.979 / 0.232), token counts matching 64/64. R0 compares against these.

## The column-wrapping effect: still not reproducible from the repo alone
The steering direction (`probes/col_hs43.pt`, key `steer_dir_unit_jrem_r1536`), the J-space basis
(`jspace_basis_L42.pt`) and the wrap bank live on his Modal results volume, not in the repo. The recipe is
complete in code (`experiments/02_nonj_features/s1_data.py::build_wrap` → `s2_capture` → `s3_probe`
regression direction → `s4_causal` newline log-odds; `src/mats/jspace.py` for the J-removal), so the effect
can be re-derived, at roughly 1–2 GPU-hours (900 hard-wrapped wikitext passages, capture at block 42,
probe fit, steering at q90 with 20 null directions). That is a separate, separately budgeted experiment;
it is not part of the G1–G4 session.

## Useful beyond G1–G4
- `src/mats/metrics.py`: cluster bootstrap, null bands, AUROC helpers (numpy only).
- `src/mats/capture.py`: batched right-padded capture and read-layer steering (`centred_steer_vectors`).
- `src/mats/textnla.py`: his prompt-only (TextNLA) baseline in the NLA register; different from our G3
  prompt-only arm, which asks the primary question directly (kept as specified in the plan).
- `notes/prereg_v0.md`: his frozen confirmation protocol; his banks are natural wikitext passages
  (col/tense/language), so the synthetic G prompts cannot overlap with them.
