---
license: mit
base_model: Qwen/Qwen3.6-27B
tags: [interpretability, oracle-lens, activation-oracle, lora]
---
# olens-new-arch — RL-refined oracle-lens adapters (Qwen3.6-27B, layer 42)

LoRA adapters that read a **layer-42 residual activation** and emit text describing it (an
oracle/activation lens). Injection: add the activation at **layer 1**, at the marker token `㈜`
(id 158983), norm-matched `h' = h + ||h||·v/||v||`. Three arms differ in the frozen reconstructor
(AR) they were built on and the RL reward used to refine them:

| folder | AR objective | RL reward |
|---|---|---|
| `rl_mse` | raw MSE reconstruction | whitened FVE |
| `rl_kl`  | downstream KL | −downstream KL (behavioral) |
| `rl_msekl` | MSE + KL | whitened FVE |

Each folder is a PEFT LoRA adapter (r64/α16 rsLoRA, all decoder blocks). Load on Qwen3.6-27B and
inject an activation at the `㈜` marker at layer 1. See the live playground for usage.
