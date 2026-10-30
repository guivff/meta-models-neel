# E74 ASSET_CARD — Track G, CPU-only audit

**Verdict: FEASIBLE at the asset/hardware gate for Oracle-lens R-G1 and R-G3.**
The exact published base and Oracle adapters are anonymously accessible; the author documents **4×B200 per replica** (TP4, about 160 GB/GPU). No model was substituted. This is not GPU admission: I-2 must approve cost, staging, runtime and the sealed launch package. **R-G2 is conditional; currently NOT EVALUABLE because no public GLM J-lens checkpoint was found.**

Authority: `BRIEF_UNDERSTAND.md` §168–§195 and clarification 1 at `4cde021d`; §192 clarification 2 at `451e2f4d`, supplied directly by Guiv during this audit. The latter permits Oracle-only execution despite unavailable J weights. Guiv supplied the [wild-rollout card](https://huggingface.co/datasets/ceselder/glm-5.3-olens-wild-rollouts) as the announcement reference. A distinct original announcement URL has not been verified; the provenance below is the author's linked HF cards and collection, not an invented announcement.

Audit date: 2026-10-27, Europe/Zurich. Full machine-readable evidence: `ANONYMOUS_AUDIT.json`. No model-weight payload, rollout records, GPU compute or judging was acquired. Cards/configuration/licence metadata were read; binary accessibility was checked with HEAD only.

## Pinned assets

Revisions below are immutable commits observed during this audit, not claims about the first release revision.

| Role | Exact HF repo | Revision | Selected path / role |
|---|---|---|---|
| Oracle lens | `ceselder/glm-5.3-olens-lens` | `689c5dbae3d2f83dbf969e234a023958f1612185` | `rl1b_rl1b_2_step_0100/adapter_model.safetensors`; original wild `rl_greedy` checkpoint |
| SFT comparison reference in same repo | `ceselder/glm-5.3-olens-lens` | `689c5dbae3d2f83dbf969e234a023958f1612185` | `sft_one_bullet_step0292/adapter_model.safetensors`; original wild `sft_greedy` checkpoint |
| Exact lens-trained / served base | `nvidia/GLM-5.3-NVFP4` | `e3b8f9f2fad29727dfa95e766c5cac18ea1414bf` | All 50 safetensors shards; author uses NVFP4 packed experts as W4A16 Marlin |
| Upstream FP8 base, provenance only | `zai-org/GLM-5.3` | `ba32f8c19c8738e2c57c71798c601d477a7bf844` | Source of NVIDIA quantization; not selected as a replacement |
| Wild rollouts | `ceselder/glm-5.3-olens-wild-rollouts` (dataset) | `226c6dce62ed88d5981ca864d0c99d3f082ccee6` | `olens_wild_rollouts.parquet`, `transcripts.parquet`; no records opened |
| GLM J-lens weights | **No public HF repo/revision verified** | **Unavailable** | Author names `stein_all_L51.pt`, `stein_all_L60.pt`, `head.pt` on project volume `glm-olens:/ckpt/jlens_glm/` |
| Reconstructor, inspected only to search for J weights | `ceselder/glm-5.3-olens-reconstructor` | `351e256e5547a751232f8221c7ffce160e7ae751` | Not required for the native Oracle readout; no J checkpoint found |

The [actual release collection](https://huggingface.co/collections/ceselder/glm53-olens-6adaf9d544d3645a7fb96eb9) contains five entries: Oracle lens, reconstructor, wild-rollouts, counterfactual-investigator, and new-sources. The §192 original placeholder `ceselder/glm53-olens` is not used as a model identifier. Anonymous author inventories returned 223 models and 160 datasets; the only GLM model repositories are the lens and reconstructor. Their complete file lists contain no `stein_all_L51.pt`, `stein_all_L60.pt`, or `head.pt`. Public `jlens.parquet` is a table of top-10 outputs, not the weights needed for k=16 pursuit on new directions.

## Anonymous access and licences

All five pinned repo APIs returned `private=false`, `gated=false`. **64/64 anonymous HEAD checks returned HTTP 200**, including every NVFP4 weight shard, both original Oracle adapter files, reference code/fork tarball, base LICENSE files, and the relevant dataset files. Requests use Python stdlib without a credential store, cookies or authentication headers. This proves HTTP accessibility; no complete weight download or content-integrity verification is claimed.

| Asset | Declared licence and verified availability |
|---|---|
| Oracle adapter | Card metadata says `other` / `nvidia-open-model-license`, linked to NVIDIA's base repo. No standalone LICENSE file is present. Card and adapter anonymously accessible. |
| NVIDIA base | Card metadata also says `nvidia-open-model-license`; **actual pinned `LICENSE` is headed GLM-5.3 License** and is byte-identical to the upstream LICENSE (4,263 bytes). This mismatch is recorded, not silently resolved. |
| Upstream GLM | GLM-5.3 License: permission to use/modify/distribute, notice retention and lawful-use conditions, with an additional security-review condition for commercial use by MaaS businesses above the stated USD 10 billion revenue threshold. Text anonymously obtainable. |
| Wild rollouts | `other` / `mixed-see-readme`: RLVR1 Apache-2.0; WildChat prompts ODC-BY with attribution; tmax/swesmith source card says `other` without supplied terms. The card describes the collection as private research material despite public access. No blanket uniform dataset licence is asserted. A future smoke fixture must retain its source's licence/provenance. |
| J-lens | Weight-specific licence and anonymous weight access unverified; only descriptive metadata and published readout tables found. R-G2 remains conditional under clarification 2. |

Sources: [pinned Oracle card](https://huggingface.co/ceselder/glm-5.3-olens-lens/blob/689c5dbae3d2f83dbf969e234a023958f1612185/README.md), [pinned NVIDIA licence](https://huggingface.co/nvidia/GLM-5.3-NVFP4/blob/e3b8f9f2fad29727dfa95e766c5cac18ea1414bf/LICENSE), [pinned upstream licence](https://huggingface.co/zai-org/GLM-5.3/blob/ba32f8c19c8738e2c57c71798c601d477a7bf844/LICENSE), [pinned dataset card](https://huggingface.co/datasets/ceselder/glm-5.3-olens-wild-rollouts/blob/226c6dce62ed88d5981ca864d0c99d3f082ccee6/README.md).

## Model size, architecture, and replica requirements

The lens card calls the model **754B parameters**; NVIDIA rounds it to 753B total / 40B active. Architecture `GlmMoeDsaForCausalLM` (`glm_moe_dsa`): 78 decoder blocks, residual width 6144, DeepSeek sparse attention / MLA, 256 routed experts with 8 selected per token plus one shared expert; first three blocks dense; one additional MTP layer in the checkpoint. All experts must be resident for ordinary serving: active parameter count is not the memory requirement. The HF NVFP4 storage-element count (~391B) includes packed bytes and is not a logical parameter count.

| Representation | Documented GPUs per replica | Evidence / interpretation |
|---|---|---|
| **Author's exact NVFP4 + bf16 non-expert path** | **4×B200 (TP4)**, ~160 GB/GPU; 8×B200 also supported | Native selected configuration. About 464 GB checkpoint, 50 shards. Passes ≤8 GPU gate. |
| Native FP8 | **8×H200 or 8×B200** | Official serving recipes; approximately 756 GB stored weights. Comparative capacity only, not a substitute for the lens-trained base. |
| Full bf16 | **16×H200 / 16×B200**, or **8×B300** | Approximately 1.5 TB weights. Does not fit an eight-H200/B200 node. Hardware type must accompany the GPU count. |

A 754B weight-only lower bound is 1.508 TB at bf16 and 754 GB at fp8, before scales, KV cache, workspaces and adapters. These are lower bounds, not measured serving allocations. The actual author path uses NVFP4 routed experts, bf16 attention/shared experts/router/embeddings, fp8 first-three-block dense MLPs, and fp8 KV cache.

Sources: [author reference implementation](https://huggingface.co/ceselder/glm-5.3-olens-lens/blob/689c5dbae3d2f83dbf969e234a023958f1612185/olens_glm53_usage.py), [NVIDIA model card](https://huggingface.co/nvidia/GLM-5.3-NVFP4/blob/e3b8f9f2fad29727dfa95e766c5cac18ea1414bf/README.md), [SGLang deployment documentation](https://docs.sglang.io/cookbook/autoregressive/GLM/GLM-5.3).

## Oracle lens interface

Read the **unmerged base decoder block 51 output**, 6144 dimensions. This is the author's numbered block, not an inferred hidden-state-array offset. Capture synthetic prefixes without adding a chat template. For a wild smoke fixture, use that fixture's exact stored transcript token IDs and original context cap.

The lens is rank-64 rsLoRA on attention and shared experts. Its source prompt is encoded in `ORACLE_INTERFACE.json`, extracted verbatim from the pinned card. Render using the base's chat template with low reasoning effort and thinking off; the author reports 70 prompt tokens, marker position 63. The sequence ends with the assistant's empty thinking span. Marker **◉**, token ID **154518**. Overwrite its input embedding during prompt forward with **54.1 × v / ||v||**. This is not the Qwen block-1 additive injection. Lens LoRA alpha 16 is separate from activation injection norm 54.1.

Use grammar v3: initial `*`, then a space-initial token, at most 16 content tokens, terminating with EOS `<|endoftext|>` (154820), at most 18 generated tokens. Special tokens, newlines and the author's other banned token classes must be masked exactly by the shipped reference. E74 uses **one greedy output, temperature 0, n=1**; do not use the reference's default n=4 sampling. Preserve the original step-100 adapter for matching `rl_greedy`; do not select a higher-scoring later checkpoint.

Runtime: vLLM 0.31.0 plus the bundled `vllm_metamodels_glm53_b26f02d.tar.gz` fork (branch `glm53`, commit `b26f02d`); CUDA 13, torch 2.13, transformers 5.17 (>=5.16.1,<5.18), peft 0.21 per author. Plain vLLM lacks the required capture hooks. The source reports roughly 11-minute TP4 boot from local NVMe versus 34 minutes at TP8. No startup or runtime was measured here; the ≤20-minute GPU smoke and ≤900-second staging admission need an explicit implementation/budget before launch.

## J-lens interface and conditional status

The author describes a forward-only Stein/ridge lens, fitted on 4.2M FineFineWeb positions toward the block-76 residual at the same position (weight four) and the next 16 positions. `stein_all_L51.pt` matches the Oracle capture layer; `stein_all_L60.pt` is the author's preferred display layer. `head.pt` supplies the output head. Extension `.pt` denotes PyTorch serialization, but tensor keys, orientation, full file format and hashes cannot be verified without the missing files. No fabricated file schema is supplied.

J readout is final-norm/unembedding after the linear map; published top-10 probabilities use a semantic-vocabulary filter. The new-row pursuit needs the actual L51 vectors/head, not top-10 output tables. No self-estimated J-lens is used. W-lens must record the checkpoint availability decision before its forecast step; if still unavailable, R-G2 is NOT EVALUABLE under clarification 2.

## Smoke and custody conditions carried forward

The wild card includes original `rl_greedy` and `sft_greedy` fields. It also reports exact greedy agreement of only about 30% RL / 50% SFT between identical engine reruns. This documented numerical instability limits interpretation of a mismatch; it does **not** relax Guiv's near-identical smoke stop rule. No smoke has run and no smoke outcome is asserted.

Next authorised work is CPU-only retokenisation of the frozen W1/E36/E49 prefixes, unchanged labels and splits, with token-boundary exclusions listed. Labels stay local. GPU smoke/capture still require I-2 admission. Native E74 test readouts require GO and a committed forecast/conditional-status custody record; judging requires Guiv's separate authorisation.
