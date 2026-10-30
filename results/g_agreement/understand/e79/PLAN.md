# E79 CPU vector preparation — §196 a12526c5

Frozen before E79 direction/vector computation. Only sealed original block44 captures, frozen dev/test metadata and E58b J384 basis (a8f4b64c010aa2f3a72aac70e087ce5204d463c2bb93d1ebf3b22b21a0bdb4fb) are inputs. No reader output or judgment input.

PROVISIONAL, pending coordinator ratification — 2026-10-28: implementation conventions consistent with §196: fixed row order nesting_depth, indent_level, page_range_digit, format_plan, language_plan; d=mean(label1/A)-mean(label0/B), μ=unweighted full dev mean; binary dev classes are balanced. Test items ordered by opaque source ID. For each row use independent SeedSequence([20261028,row_index,stream]) streams: stream0 Gaussian random direction projected orthogonal to full d then unit-normalized; stream1 shuffles 42 target A and42 target B independently of true labels; stream2 opaque output IDs. No selection using outcomes. r's + sign is assigned toward target A, though r is a random control, not a learned state axis.

Arm A is E57 only. h+alpha*||d||*sigma*u for alpha1,2,4 and u J/nonJ/random, with one shared alpha0 baseline, as §196 explicitly states (10 cells,840 vectors per row). Same target per item across every cell; sigma +1 toward A and -1 toward B. Arm B is E59 only, h-((h-μ)·u)u for each unit J/nonJ/random plus exact none. No dropped vectors or margin-based filters. 3,192 total vectors.

Compute in float64, save activations float32. Validate finite, nonzero d/J/residual/random, orthonormal basis, random orthogonality and balanced84test/84dev per row. Per-item norm ratios and per-cell summaries (mean/min/max/count>1.5) plus J-fraction are descriptive, never exclusion gates. Failure stops; no scientific retry.

Pod package contains only INPUT_VECTORS.npy, opaque ITEMS.json index/row/arm/cell and its seal. No true labels, target assignments, signs, private source IDs or dev class means on pods. Target/sign/source joins live only in ignored private map mode0600, bound by hash. CPU-only directions/means remain in ignored CPU custody. Integrator must stage only pod_inputs. Seal before any readout; no model/scoring run here.
