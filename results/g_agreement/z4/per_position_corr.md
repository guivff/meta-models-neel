# Z4 per-position correlation: reader shift vs flip rate (2026-10-09; CPU only, 0 forward passes)

BRIEF_Z deviation 2026-10-09 "Z1 reporting": per position, the mean reader shift f_r (fraction of the reader's own natural separation) against the flip rate on the same entries, Z4 single-position arm, α 0.75 and α 1 separately. Spearman and Pearson across positions; 95% CI by pair bootstrap (1000 resamples, seed 0; per-position aggregates recomputed on each resample); positions with n ≥ 8 entries enter; * = CI excludes 0. Reference row: the model's own Δ_model (nats) in place of f_r.
Keyings: **absolute** token index (as per_position.csv); **role** = (role, rank within role): chat_prefix, diff (differing tokens in prompt order), statement, question (offset from the question's first token), template (offset from <|im_end|>), last — the same key is the same kind of token in every prompt. f_r uses the Z1 tie tolerance (|sep_r| < 1e-4 excluded: Oracle lens xmap-16/26, xown-09/20); per_position.csv's Oracle-lens means do not apply it (xmap-16, sep 4e-7, inflates its mapping means), so its f_olens columns are not the ones correlated here.

## absolute keying
| family | α | scorer | n positions (with ≥1 flip) | n entries | Spearman [95% CI] | Pearson [95% CI] |
|---|---|---|---|---|---|---|
| ownership | 0.75 | Oracle lens | 37 (0) | 886 | n/a | n/a |
| ownership | 0.75 | NLA | 37 (0) | 944 | n/a | n/a |
| ownership | 0.75 | J-lens | 37 (0) | 944 | n/a | n/a |
| ownership | 0.75 | model Δ_model (reference) | 37 (0) | 944 | n/a | n/a |
| ownership | 1 | Oracle lens | 37 (0) | 886 | n/a | n/a |
| ownership | 1 | NLA | 37 (0) | 944 | n/a | n/a |
| ownership | 1 | J-lens | 37 (0) | 944 | n/a | n/a |
| ownership | 1 | model Δ_model (reference) | 37 (0) | 944 | n/a | n/a |
| mapping | 0.75 | Oracle lens | 45 (6) | 866 | +0.24 [+0.02, +0.50]* | +0.41 [+0.04, +0.78]* |
| mapping | 0.75 | NLA | 48 (6) | 938 | -0.10 [-0.33, +0.13] | -0.28 [-0.46, +0.13] |
| mapping | 0.75 | J-lens | 48 (6) | 938 | +0.20 [+0.03, +0.48]* | +0.31 [+0.03, +0.57]* |
| mapping | 0.75 | model Δ_model (reference) | 48 (6) | 938 | +0.57 [+0.42, +0.60]* | +0.98 [+0.95, +0.99]* |
| mapping | 1 | Oracle lens | 45 (6) | 866 | +0.35 [+0.07, +0.51]* | +0.39 [+0.05, +0.77]* |
| mapping | 1 | NLA | 48 (6) | 938 | -0.32 [-0.42, +0.06] | -0.34 [-0.55, +0.12] |
| mapping | 1 | J-lens | 48 (6) | 938 | +0.20 [+0.03, +0.47]* | +0.31 [+0.01, +0.58]* |
| mapping | 1 | model Δ_model (reference) | 48 (6) | 938 | +0.57 [+0.42, +0.60]* | +0.98 [+0.96, +0.99]* |
| pooled | 0.75 | Oracle lens | 48 (6) | 1780 | +0.10 [-0.06, +0.34] | +0.09 [-0.07, +0.40] |
| pooled | 0.75 | NLA | 50 (6) | 1908 | -0.23 [-0.33, -0.03]* | -0.32 [-0.42, -0.02]* |
| pooled | 0.75 | J-lens | 50 (6) | 1908 | +0.14 [-0.01, +0.37] | +0.24 [-0.04, +0.53] |
| pooled | 0.75 | model Δ_model (reference) | 50 (6) | 1908 | +0.56 [+0.39, +0.58]* | +0.95 [+0.90, +0.97]* |
| pooled | 1 | Oracle lens | 48 (6) | 1780 | +0.15 [-0.04, +0.33] | +0.07 [-0.07, +0.34] |
| pooled | 1 | NLA | 50 (6) | 1908 | -0.34 [-0.43, -0.07]* | -0.29 [-0.42, -0.02]* |
| pooled | 1 | J-lens | 50 (6) | 1908 | +0.16 [-0.01, +0.36] | +0.22 [-0.07, +0.53] |
| pooled | 1 | model Δ_model (reference) | 50 (6) | 1908 | +0.56 [+0.38, +0.58]* | +0.94 [+0.86, +0.97]* |

## role keying
| family | α | scorer | n positions (with ≥1 flip) | n entries | Spearman [95% CI] | Pearson [95% CI] |
|---|---|---|---|---|---|---|
| ownership | 0.75 | Oracle lens | 37 (0) | 896 | n/a | n/a |
| ownership | 0.75 | NLA | 37 (0) | 956 | n/a | n/a |
| ownership | 0.75 | J-lens | 37 (0) | 956 | n/a | n/a |
| ownership | 0.75 | model Δ_model (reference) | 37 (0) | 956 | n/a | n/a |
| ownership | 1 | Oracle lens | 37 (0) | 896 | n/a | n/a |
| ownership | 1 | NLA | 37 (0) | 956 | n/a | n/a |
| ownership | 1 | J-lens | 37 (0) | 956 | n/a | n/a |
| ownership | 1 | model Δ_model (reference) | 37 (0) | 956 | n/a | n/a |
| mapping | 0.75 | Oracle lens | 47 (2) | 878 | +0.30 [-0.01, +0.37] | +0.39 [-0.04, +0.78] |
| mapping | 0.75 | NLA | 47 (2) | 930 | -0.27 [-0.32, +0.13] | -0.30 [-0.44, +0.09] |
| mapping | 0.75 | J-lens | 47 (2) | 930 | +0.02 [-0.01, +0.36] | +0.45 [+0.01, +0.68]* |
| mapping | 0.75 | model Δ_model (reference) | 47 (2) | 930 | +0.35 [+0.35, +0.38]* | +1.00 [+0.98, +1.00]* |
| mapping | 1 | Oracle lens | 47 (2) | 878 | +0.33 [-0.01, +0.37] | +0.39 [-0.08, +0.78] |
| mapping | 1 | NLA | 47 (2) | 930 | -0.31 [-0.34, +0.04] | -0.30 [-0.45, +0.05] |
| mapping | 1 | J-lens | 47 (2) | 930 | +0.02 [-0.02, +0.36] | +0.43 [-0.00, +0.69] |
| mapping | 1 | model Δ_model (reference) | 47 (2) | 930 | +0.35 [+0.35, +0.38]* | +1.00 [+0.98, +1.00]* |
| pooled | 0.75 | Oracle lens | 49 (2) | 1778 | +0.28 [-0.01, +0.33] | +0.19 [-0.04, +0.47] |
| pooled | 0.75 | NLA | 49 (2) | 1890 | -0.24 [-0.29, -0.01]* | -0.22 [-0.35, +0.01] |
| pooled | 0.75 | J-lens | 49 (2) | 1890 | +0.03 [-0.01, +0.32] | +0.41 [-0.02, +0.63] |
| pooled | 0.75 | model Δ_model (reference) | 49 (2) | 1890 | +0.34 [+0.33, +0.35]* | +0.95 [+0.86, +0.99]* |
| pooled | 1 | Oracle lens | 49 (2) | 1778 | +0.31 [-0.00, +0.34] | +0.18 [-0.03, +0.47] |
| pooled | 1 | NLA | 49 (2) | 1890 | -0.29 [-0.31, +0.03] | -0.20 [-0.29, +0.03] |
| pooled | 1 | J-lens | 49 (2) | 1890 | +0.02 [-0.01, +0.33] | +0.40 [-0.01, +0.62] |
| pooled | 1 | model Δ_model (reference) | 49 (2) | 1890 | +0.34 [+0.33, +0.35]* | +0.86 [+0.69, +0.95]* |

## Role-aligned positions at α 1 that flip (model reference cells: flip rate, mean Δ_model, n)
- ownership: no position flips — 37 keys ranked, 0 with any flip.
- mapping: diff:0 48% (Δ_model +5.9, n 64); diff:1 45% (Δ_model +5.4, n 64) — 47 keys ranked, 2 with any flip.
- pooled: diff:0 24% (Δ_model +2.9, n 128); diff:1 23% (Δ_model +2.6, n 128) — 49 keys ranked, 2 with any flip.

Caveats: no single ownership position flips at either dose (correlation undefined); in mapping only a handful of positions flip (column 'with ≥1 flip'), so the flip rate is 0 at almost every key and the Spearman is mostly a test of whether those few keys get the highest reader shift (heavy ties; bootstrap CIs can be narrow or one-sided for that reason — the Pearson is the less tie-bound companion); the role keying pools prompts by role, so a key with few prompts (long statements, long questions) is dropped by the n filter. Uniform positions were sampled per pair (seed 0), so most role keys outside diff / question:0 / last carry fewer entries than those three.
Command: `PYTHONPATH=. .venv/bin/python projects/g_agreement/z4_positions/position_corr.py --n-boot 1000 --seed 0 --min-n 8` (wall 7.2 s; 3840 single-position entries, readers olens, nla, jlens).
