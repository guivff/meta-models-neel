"""Qwen3-4B oracle inference: replace one prompt embedding with a residual direction.

Prompt/injection contract adapted from agu18dec/olens_draft (MIT; UPSTREAM_LICENSE).
The reconstructor and whitening statistics are needed for scoring, not generation.
"""
from __future__ import annotations
import json
from pathlib import Path
import torch
from huggingface_hub import snapshot_download
from safetensors import safe_open

REPO = "andyx10/oracle-lens-qwen3-4b"


def render_prompt(tokenizer, config: dict, layer: int) -> tuple[list[int], int]:
    if layer not in config["layers"]:
        raise ValueError(f"layer must be one of {config['layers']}")
    marker = config["injection"]["marker"]
    text = config["prompt_template"].format(layer=layer, marker=marker)
    out = tokenizer.apply_chat_template(
        [{"role": "user", "content": text}], tokenize=True,
        add_generation_prompt=True, enable_thinking=False,
    )
    ids = out if isinstance(out, list) else out["input_ids"]
    token = config["injection"]["token_id"]
    slots = [i for i, t in enumerate(ids) if t == token]
    if len(slots) != 1 or not 0 < slots[0] < len(ids) - 1:
        raise ValueError("Expected exactly one interior injection marker")
    slot = slots[0]
    if [ids[slot - 1], ids[slot + 1]] != config["injection"]["neighbor_ids"]:
        raise ValueError("Tokenizer/injection marker mismatch")
    return ids, slot


def load_oracle(repo: str = REPO, revision: str = "main", device: str = "cuda",
                dtype: torch.dtype = torch.bfloat16):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    root = Path(snapshot_download(repo, revision=revision,
                allow_patterns=["adapter_config.json", "adapter_model.safetensors", "lens_config.json"]))
    config = json.loads((root / "lens_config.json").read_text())
    tokenizer = AutoTokenizer.from_pretrained(config["base_model"])
    base = AutoModelForCausalLM.from_pretrained(config["base_model"], dtype=dtype,
                                               attn_implementation="sdpa").to(device)
    model = PeftModel.from_pretrained(base, root).eval()
    # A silently unmatched adapter would produce plausible base-model text.
    def stem(name):
        return name.removeprefix("base_model.model.").replace(".default", "")
    live = {stem(n) for n, _ in model.named_parameters() if "lora_" in n}
    with safe_open(root / "adapter_model.safetensors", framework="pt") as f:
        saved = {stem(k) for k in f.keys() if "lora_" in k}
    if not saved or not saved <= live:
        raise RuntimeError("The adapter's saved keys do not all map onto the loaded model")
    return model, tokenizer, config


@torch.inference_mode()
def read_activation(model, tokenizer, config: dict, activation: torch.Tensor,
                    layer: int, *, sample: bool = False) -> str:
    """activation: raw, unwhitened residual direction of shape [2560]."""
    from transformers import GenerationConfig
    v = torch.as_tensor(activation).detach().float()
    if v.shape != (config["hidden_size"],) or not torch.isfinite(v).all() or v.norm() <= 0:
        raise ValueError("Expected one finite, nonzero residual vector of shape [2560]")
    ids, slot = render_prompt(tokenizer, config, layer)
    embedding = model.get_input_embeddings()
    device = embedding.weight.device
    x = embedding(torch.tensor([ids], device=device)).clone()
    x[0, slot] = (config["injection"]["norm"] * v / v.norm()).to(device=device, dtype=x.dtype)
    eos = model.generation_config.eos_token_id
    stop = set(eos if isinstance(eos, list) else [eos])
    stop.update([tokenizer.eos_token_id, config["injection"]["token_id"]])
    stop.discard(None)
    generation = GenerationConfig(
        do_sample=sample, temperature=1.0 if sample else None,
        top_p=1.0 if sample else None, top_k=0 if sample else None,
        max_new_tokens=128, eos_token_id=sorted(stop), pad_token_id=tokenizer.pad_token_id,
    )
    output = model.generate(inputs_embeds=x, attention_mask=torch.ones(x.shape[:2],
                            dtype=torch.long, device=device), generation_config=generation)[0].tolist()
    end = next((i for i, t in enumerate(output) if t in stop), len(output))
    return tokenizer.decode(output[:end], skip_special_tokens=True).strip()
