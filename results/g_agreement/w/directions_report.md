# W Track B — direction decomposition report (2026-10-12T02:58:44.553232+00:00)

Pre-registration: projects/g_agreement/PREREG_WV.md (Track B). Code: projects/g_agreement/w_directions/. Outputs: /Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/w/directions (108.0 MB). J-space: cache/g_agreement/y/jspace_L38_r384.pt (Q [5120, 384], sha256 372946128c4b…). Wall-clock 23 s on the Mac (CPU).

## Energy fractions of ‖Δ(pos)‖² (mean over pairs × site positions; median in brackets)

| family | n pairs | n positions | d_cm | d_pw | d_J (overlapping) | d_J_excl | d_res | span | ‖Δ‖ mean |
|---|---|---|---|---|---|---|---|---|---|
| ownership | 32 | 648 | 0.111 [0.033] | 0.007 [0.004] | 0.079 [0.078] | 0.072 [0.071] | 0.810 [0.881] | 0.190 [0.119] | 12.8 |
| mapping | 32 | 64 | 0.459 [0.470] | 0.021 [0.004] | 0.220 [0.210] | 0.069 [0.064] | 0.451 [0.434] | 0.549 [0.559] | 38.4 |
| errors | 297 | 297 | 0.158 [0.127] | 0.013 [0.007] | 0.089 [0.087] | 0.073 [0.074] | 0.756 [0.796] | 0.244 [0.204] | 15.5 |

d_cm + d_pw + d_J_excl + d_res = 1 by construction; d_J (overlapping) = ‖QQᵀΔ‖²/‖Δ‖² counts J-space energy that may also lie along d_cm/d_pw. Errors: Δ := full = centroid[target] − h.

## Pairwise cosines of the unit directions (mean, mean |cos|, max |cos| over pairs × positions)

| family | d_cm|d_pw | d_cm|d_J | d_cm|d_res | d_pw|d_J | d_pw|d_res | d_J|d_res |
|---|---|---|---|---|---|---|
| ownership | -0.000 / 0.000 / 0.000 | +0.063 / 0.065 / 0.173 | +0.000 / 0.000 / 0.000 | +0.003 / 0.015 / 0.052 | -0.000 / 0.000 / 0.000 | -0.000 / 0.000 / 0.000 |
| mapping | +0.000 / 0.000 / 0.000 | +0.438 / 0.438 / 0.588 | +0.000 / 0.000 / 0.000 | -0.115 / 0.115 / 0.213 | -0.000 / 0.000 / 0.000 | -0.000 / 0.000 / 0.000 |
| errors | -0.000 / 0.000 / 0.000 | +0.002 / 0.031 / 0.143 | -0.000 / 0.000 / 0.000 | -0.015 / 0.030 / 0.117 | +0.000 / 0.000 / 0.000 | -0.000 / 0.000 / 0.000 |

## Orientation agreement (fraction of pair × positions with Δ(pos)·d̂ > 0; 1.0 = the shared direction always points A→B)

| family | d_cm | d_pw |
|---|---|---|
| ownership | 0.901 | 0.613 |
| mapping | 1.000 | 0.375 |
| errors | 0.939 | 0.323 |

## J-space energy of the unit directions (‖QQᵀd̂‖²; a random direction scores r/d = 0.075)

| family | d_cm | d_pw | d_res | two-half cos of d_cm (noise ceiling) |
|---|---|---|---|---|
| ownership | 0.068 | 0.040 | 0.000 | 0.966 |
| mapping | 0.282 | 0.084 | 0.000 | 0.567 |
| errors | 0.107 | 0.092 | 0.000 | 0.405 |

## Held-out probe (SpanLogistic, inner-CV C ∈ {0.01, 0.1, 1}; 5 outer folds by pair / by item)

| family | label | fold | C | n train | n test | accuracy | within-pair win / favours-actual |
|---|---|---|---|---|---|---|---|
| ownership | y = 1 iff holder is the second-mentioned name | 0 | 0.1 | 1008 | 288 | 0.896 | 0.917 |
| ownership | y = 1 iff holder is the second-mentioned name | 1 | 1.0 | 1014 | 282 | 0.911 | 0.894 |
| ownership | y = 1 iff holder is the second-mentioned name | 2 | 1.0 | 1044 | 252 | 0.909 | 0.889 |
| ownership | y = 1 iff holder is the second-mentioned name | 3 | 1.0 | 1070 | 226 | 0.912 | 0.929 |
| ownership | y = 1 iff holder is the second-mentioned name | 4 | 1.0 | 1048 | 248 | 0.859 | 0.839 |
| ownership | mean | – | – | – | – | 0.897 | 0.893 |
| mapping | 8-way symbol identity at the site position | 0 | 1.0 | 100 | 28 | 0.964 | 1.000 |
| mapping | 8-way symbol identity at the site position | 1 | 0.1 | 100 | 28 | 1.000 | 1.000 |
| mapping | 8-way symbol identity at the site position | 2 | 0.1 | 104 | 24 | 1.000 | 1.000 |
| mapping | 8-way symbol identity at the site position | 3 | 0.01 | 104 | 24 | 1.000 | 1.000 |
| mapping | 8-way symbol identity at the site position | 4 | 0.1 | 104 | 24 | 1.000 | 1.000 |
| mapping | mean | – | – | – | – | 0.993 | 1.000 |
| errors | 8-way actual symbol (layer-48 last token) | 0 | 1.0 | 237 | 60 | 0.433 | 0.750 |
| errors | 8-way actual symbol (layer-48 last token) | 1 | 0.01 | 237 | 60 | 0.400 | 0.750 |
| errors | 8-way actual symbol (layer-48 last token) | 2 | 0.01 | 238 | 59 | 0.441 | 0.831 |
| errors | 8-way actual symbol (layer-48 last token) | 3 | 1.0 | 238 | 59 | 0.576 | 0.763 |
| errors | 8-way actual symbol (layer-48 last token) | 4 | 0.01 | 238 | 59 | 0.458 | 0.881 |
| errors | mean | – | – | – | – | 0.462 | 0.795 |

## Files

| family | layer | site | pairs | MB | shared |
|---|---|---|---|---|---|
| ownership | 38 | post_statement_span | 32 | 66.7 | ownership/shared.pt |
| mapping | 38 | differing_symbol_positions | 32 | 7.7 | mapping/shared.pt |
| errors | 48 | last_token | 297 | 33.6 | errors/shared.pt |

Data: X2 full captures 32 pairs per family (cache/g_agreement/x/full, layer 38); Y1 error captures 297 items (layer 48 = cap layer index 3, label '0'), skipped (absent/non-finite): [].

## Tensor layout the pod stage reads (all fp32; positions int64)

```
<family>/<pair_id>.pt = {
  pair_id, family, layer (38|38|48), site, n_tokens, fold, sign (ownership: ±1 = this pair's orientation of the shared d_cm/d_pw),
  positions: int64 [P]         absolute token indices of the edit site (errors: [-1] = last token),
  delta:     fp32 [P, d]       Δ(pos) = h_B(pos) − h_A(pos)  (errors: full = centroid[target] − h),
  delta_norm: fp32 [P]         ‖Δ(pos)‖ — the matched norm for every direction and for the random directions,
  dirs: {d_cm, d_pw, d_J, d_res: fp32 [P, d]}  UNIT vectors oriented A→B (d_pw ⊥ d_cm; d_res ⊥ d_cm, d_pw, Q; d_J ∈ span Q),
  coef: {same keys: fp32 [P]}  signed (d_cm, d_pw) / ≥ 0 (d_J, d_res) with coef[k][pos] * dirs[k][pos] = the component of Δ(pos),
  frac: {d_cm, d_pw, d_J, d_J_excl, d_res, span: fp32 [P]}  energy fractions (d_cm + d_pw + d_J_excl + d_res = 1),
  random: {seed, K = 10, d, n_positions, recipe}  → directions.random_directions(seed, P, d, K) gives fp32 [K, P, d] unit rows,
  source_items: {A: item_id, B: item_id} | {item: item_id, cap_layer_index, cap_label_index}, meta (labels/symbols), frame (text)
}
Matched-norm edit from source A at dose alpha:  h'(pos) = h_A(pos) + alpha * delta_norm[pos] * dirs[k][pos]   (from B: minus).
Component edit (the pair's own component):     h'(pos) = h_A(pos) + alpha * coef[k][pos]   * dirs[k][pos].
full swap = h_A(pos) + alpha * delta[pos].  Errors: h' = h + alpha * delta_norm * dirs[k] (every direction at ‖full‖).
<family>/shared.pt = {d_cm [d] (ownership) | class_means [8, d] + symbols (mapping) | centroids [8, d] + d_cm_table [8, d] + symbols (errors),
  probe: {folds: [{fold, train_pairs|train_items, test_pairs|test_items, C, accuracy, classes, w_raw [K, d] raw-space weights}], fold_of_pair},
  Q_ref {path, sha256, shape}, norms {pair_id: delta_norm [P]}, sign_of_pair (ownership), layer, site, seed, n_folds}
```

## Definitional choices to record under PREREG_WV.md 'Deviations'

- J-space basis for the ERROR family (layer 48) is the layer-38 basis cache/g_agreement/y/jspace_L38_r384.pt (no layer-48 J-lens/Gram basis exists on the Mac); d_J and the J fractions for errors are therefore 'the L38 J-space', not an L48 one. If the pod has the L48 J-lens weights, rebuild Q48 with core.edit.jspace_basis and re-run build.py --families errors.
- Ownership d_cm is ONE shared vector (flat mean over all pairs × site positions of the oriented Δ), applied with the pair's sign at every site position; it is not position-specific. The ownership probe pools all site positions (question + template tokens) of both versions as training rows, label = binding (holder is the second-mentioned name).
- Mapping class means pool both differing positions and both versions (128 vectors, 8 symbols); d_cm is per position, unit(mean[sym_B] − mean[sym_A]); the pair's own vectors are inside the class means (d_cm is not held out; only d_pw is).
- Error d_cm = unit(cm[target] − cm[actual]) with cm[s] = mean(actual = s) − mean(actual ≠ s) over all 297 error states (not held out); 'full' = centroid[target] − h; d_J projects the d_cm-free residual (full − (full·d_cm) d_cm) onto Q, unlike ownership/mapping where d_J = unit(QQᵀΔ).
- d_pw is the raw-space weight vector coef·Vt/sd of x_friday_r2r4.SpanLogistic (standardised features, inner 3-fold CV over C ∈ {0.01, 0.1, 1}); binary (ownership) → the single weight row; 8-way (mapping, errors) → w[s_B] − w[s_A] / w[target] − w[actual]; then Gram–Schmidt against d_cm.
- Energy fractions: frac[d_J] overlaps d_cm/d_pw; the disjoint partition is d_cm + d_pw + d_J_excl + d_res = 1 (d_J_excl = J-space energy not already along d_cm/d_pw).
- Random directions: K = 10 per pair/item, seed = (20261011·1000003 + crc32(pair_id)) mod (2^31 − 1), isotropic unit rows per position (X2Nulls recipe); the pod regenerates them from the seed and scales by delta_norm.
- Folds: ownership/mapping KFold(5, shuffle, seed 0) over pairs; errors StratifiedKFold(5, shuffle, seed 0) by actual symbol (smallest class E has 8 items). The fold's probe is applied only to its held-out pairs/items.
- Michael's recipe is implemented (w_directions/michael.py) and unit-tested on synthetic data; it is NOT fitted here because the counts/arithmetic states are captured in S1.

## Commands

```
.venv/bin/python -m projects.g_agreement.w_directions.build --families ownership,mapping,errors
```
