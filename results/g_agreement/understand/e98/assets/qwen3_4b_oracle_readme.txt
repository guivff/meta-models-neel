---
license: apache-2.0
base_model: Qwen/Qwen3-4B
library_name: peft
tags:
- interpretability
- oracle-lens
- activation-readout
- lora
- grpo
- safetensors
---

# Oracle lens — Qwen3-4B

An implementation of oracle lens for Qwen/Qwen3-4B. Given a residual-stream direction
from one of the trained layers, it generates a bullet list of concepts intended to
reconstruct that activation.

<table>
  <tr>
    <td width="33%"><a href="https://cdn-uploads.huggingface.co/production/uploads/6997e2c73023436326a52378/datJPeGH1zBc2KEsHnE7M.png"><img src="https://cdn-uploads.huggingface.co/production/uploads/6997e2c73023436326a52378/datJPeGH1zBc2KEsHnE7M.png" alt="Oracle-lens example 1"></a></td>
    <td width="33%"><a href="https://cdn-uploads.huggingface.co/production/uploads/6997e2c73023436326a52378/yrQpu80CErIv2nuC2KwYw.png"><img src="https://cdn-uploads.huggingface.co/production/uploads/6997e2c73023436326a52378/yrQpu80CErIv2nuC2KwYw.png" alt="Oracle-lens example 2"></a></td>
    <td width="33%"><a href="https://cdn-uploads.huggingface.co/production/uploads/6997e2c73023436326a52378/NBIRLyIjk_fkGTI1fNIja.png"><img src="https://cdn-uploads.huggingface.co/production/uploads/6997e2c73023436326a52378/NBIRLyIjk_fkGTI1fNIja.png" alt="Oracle-lens example 3"></a></td>
  </tr>
</table>

The training pipeline adapts [agu18dec/olens_draft](https://github.com/agu18dec/olens_draft/tree/a32590085a6070d75f950155d3c2b3db3eec97ef)
to Qwen3-4B. The oracle-lens method is described in Appendix A.9.2 of
[*Verbalizable Representations Form a Global Workspace in Language Models*](https://transformer-circuits.pub/2026/workspace/index.html).


## Start here

| Component | Released artifact |
| --- | --- |
| Oracle | Root `adapter_model.safetensors` + `adapter_config.json`; `rl.qwen3-4b.e2.main.s0/iter_000425` |
| Base model | `Qwen/Qwen3-4B`; 36 blocks, residual width 2,560 |
| Trained oracle layers | **12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34**, zero-based |
| Adapter | LoRA rank 16, alpha 32; 504 saved LoRA tensors |
| Generation contract | [`lens_config.json`](lens_config.json), [`code/read_oracle.py`](code/read_oracle.py) |
| Frozen reconstructor | [`reconstructor/`](https://huggingface.co/andyx10/oracle-lens-qwen3-4b/tree/main/reconstructor), AR checkpoint `ex16013344`, including LoRA, head and metadata |
| Scoring statistics | [`whitening/`](https://huggingface.co/andyx10/oracle-lens-qwen3-4b/tree/main/whitening), 19 frozen per-layer moment files and their hash manifest |
| Training datasets | [`data/`](https://huggingface.co/andyx10/oracle-lens-qwen3-4b/tree/main/data), including the actual 20,000-row RL training set and 512-row gate set |

The base weights must be loaded separately. The reconstructor and whitening files
are needed for reconstruction scoring, **not** for generating a readout.

## Prompt and injection recipe

The prompt is part of the trained lens. The user message is:

```text
An activation vector from layer {layer} of a language model is enclosed in activation tags: <activation>㈎</activation>. Produce distinct concepts that encode this activation, each as a '- ' bullet on its own line.
```

1. Render with Qwen3's chat template, `add_generation_prompt=True` and
   `enable_thinking=False`.
2. Find the single `㈎` marker (token **149705**, neighboring token IDs **29, 522**).
3. Replace its **input embedding** with `16000 * v / ||v||`, where `v` is a
   nonzero, unwhitened 2,560-dimensional residual direction.
4. Generate up to 128 new tokens. Stop on the model's EOS tokens or the injection
   marker. Greedy decoding is convenient for inspection; the RL evaluation used
   sampling at temperature 1.0, top-p 1.0, top-k disabled.

The layer number describes the source activation. It does **not** mean injecting
inside that decoder block. This model uses marker-slot embedding replacement,
not the block-45 residual hook used by the separate 27B reference model.

### Minimal use

Install PyTorch, Transformers, PEFT, safetensors and huggingface_hub. Download the
small inference helper and load the adapter:

```python
import importlib.util
import torch
from huggingface_hub import hf_hub_download

repo = "andyx10/oracle-lens-qwen3-4b"
helper = hf_hub_download(repo, "code/read_oracle.py")
spec = importlib.util.spec_from_file_location("read_oracle", helper)
lens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lens)
model, tokenizer, config = lens.load_oracle(device="cuda")

# v must be your raw Qwen3-4B activation/direction, shape [2560].
# For block 18, capture its output before the next block; do not apply final RMSNorm.
v = torch.load("activation.pt", map_location="cpu", weights_only=True)
print(lens.read_activation(model, tokenizer, config, v, layer=18))
```

The helper checks marker placement and adapter-key matching. It downloads only the
root adapter and configuration, not the training corpus. For reproducible use,
pass a pinned HF commit as `revision` to both helper download and `load_oracle`.
A normal text-generation prompt without vector injection is not an oracle readout.

## Training and recorded results

The sequence was on-policy chat rollouts → residual/span pairs → frozen whiteners
→ activation reconstructor → continuation AO → NNOMP-selected bullet distillation
→ GRPO. AR means **text → activation**; AO means **activation → text**.

| Measurement | Recorded value | Scope |
| --- | ---: | --- |
| Frozen AR validation FVE | 0.18017 | AR validation; [`reconstructor/meta.json`](reconstructor/meta.json) |
| Frozen AR retrieval@1 | 0.817 | Same AR checkpoint |
| Two-pass distilled student's validation CE | 1.73465 | SFT validation; 27,994 train / 1,475 validation examples |
| Main RL initial logged gate FVE | 0.1560 | 128 gate prompts, sampled decoding |
| Main RL peak logged gate FVE | 0.1804 | `eval@425`; used during model selection |
| Main RL last logged gate FVE | 0.1751 | `eval@575`; run ended at 600 updates |

These are different diagnostics, not interchangeable benchmarks. The RL gate set
was reused during training and checkpoint selection, so its peak is **not an
untouched test score**. Evaluation labels are zero-based loop indices, while
checkpoint directories count completed updates: `eval@425` and `iter_000425`
are adjacent training states, not an exact checkpoint-specific re-evaluation.
The root adapter preserves the selected `iter_000425` artifact used for downstream
readouts. No new GPU evaluation is implied by this release cleanup.

The policy receives normalized **AR reconstructions** during RL. The reward
compares reconstructed generated concepts with **true residuals** in the frozen
whitened metric (ridge coefficient 0.1, joint NNLS/FVE, at most four concepts).
Main settings: 8 prompts × 64 samples, LR 5e-5, KL coefficient 0.05,
128-token generation cap, one H200 for actor and reward AR.
See [`training/rl/rl.qwen3-4b.e2.main.s0/`](https://huggingface.co/andyx10/oracle-lens-qwen3-4b/tree/main/training/rl/rl.qwen3-4b.e2.main.s0)
for the original configuration, prep record and log.

## Repository layout

```text
adapter_config.json / adapter_model.safetensors  selected RL oracle
lens_config.json                                prompt, geometry and injection contract
reconstructor/                                  frozen AR LoRA + heads + metadata
whitening/                                      frozen moment files + manifest
data/
  seeds/      rollouts/      splits/             on-policy data and split provenance
  pairs/                                        captured ao_val activation/span waves
  ao/chat/    ao/continuation/                   pools and precomputed AR banks
  distillation/                                 all rounds, candidates and assembled shards
  rl/                                           actual train/gate Parquet files
training/
  ar/         ao/           rl/                  other checkpoints and run records
  logs/       whitener-fit/                     logs and accumulated fitting state
code/read_oracle.py                              standalone inference helper
code/training/                                  curated Qwen3-4B pipeline source
provenance/                                     full path/hash map and release metadata
archive/                                        original code snapshot and old manifest
```

All pre-cleanup artifacts are retained byte-for-byte, including intermediate
checkpoints, reference adapters, candidate generations and supplemental datasets.
[`data/README.md`](data/README.md) describes their schemas and roles.
[`provenance/file-map.json`](provenance/file-map.json) maps every original path to
its current location. Historical configs may contain the original machine paths;
these are provenance, not portable launch defaults.

The previous layout is available at revision
`e0a0a7e083f0059945a383888e31e90cdc13c50a` (tag `legacy-layout-v1`). Pin that revision
when using older scripts that expect `ao/`, `ar/`, `rollouts/` or `whitener/` at the
root. The clean training source is in [`code/training/`](https://huggingface.co/andyx10/oracle-lens-qwen3-4b/tree/main/code/training); no copy of
upstream's privately sourced trainer is redistributed here.

## Limitations and provenance

- Readouts are hypotheses, not guaranteed explanations or causal evidence. Output
  can be multilingual, fragmented, repetitive or off-distribution.
- A bare weight/write direction differs from the activation distribution used in
  training. Reconstruction FVE does not establish that such a readout identifies
  the cause of a behavioral change.
- The final residual block 35 is outside this oracle's trained layer set.
- The recovered run does not fully pin base-model and dataset download revisions.
  Upstream source and release artifacts are pinned; bitwise retraining is not promised.
- Source chat data, generated text, base weights and third-party code retain their
  respective terms. This model card does not relicense the bundled datasets.

The separate [template lens](https://huggingface.co/andyx10/template-lens-qwen3-4b)
is a fitted linear word readout. Its moments are **not** this oracle's whitening
statistics and must not be substituted for them.

## License

Released under the [Apache License 2.0](LICENSE). Code adapted from
[agu18dec/olens_draft](https://github.com/agu18dec/olens_draft) keeps its MIT notice in
[`code/UPSTREAM_LICENSE`](code/UPSTREAM_LICENSE).

## Acknowledgements

Compute partially provided by a generous research grant from Modal.com.
