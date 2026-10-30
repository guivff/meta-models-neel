"""Residual-stream activation caching and position-slotted mean differences.

Usage pattern (all projects):

    from common.activations import load_model, cache_residuals, mean_diff_by_position

    m, tok = load_model("allenai/Olmo-3-7B-Think", revision="step_0500")
    acts = cache_residuals(m, tok, texts, layers=[8, 16, 24], max_positions=32)   # dict layer -> (N, P, d) float16 on CPU
    # later, with a second model's cache:
    d = mean_diff_by_position(acts_ft[16], acts_base[16])                          # (P, d)

Design notes
- Hooks read the *output* of decoder block `layer` (residual stream after that block). Layer 0 = after block 0.
- Activations are stored per position so position-slotted analyses (P6) are possible; pass max_positions=None to keep all.
- Right-padding is used; we keep an attention-mask-aware position index so position p means "p-th real token".
- Memory: N × P × d × 2 bytes per layer. 10k docs × 32 pos × 4096 d × 2 B ≈ 2.6 GB per layer. Save to disk with `save_cache`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_model(model_id: str, revision: Optional[str] = None, dtype=torch.bfloat16, device_map="auto",
               adapter: Optional[str] = None):
    """Load a HF causal LM (optionally a LoRA adapter on top). Returns (model, tokenizer)."""
    tok = AutoTokenizer.from_pretrained(model_id, revision=revision)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, torch_dtype=dtype, device_map=device_map)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
        model = model.merge_and_unload()
    model.eval()
    return model, tok


def _decoder_layers(model) -> Sequence[torch.nn.Module]:
    # Works for Llama/Qwen/OLMo-style HF models.
    for attr in ("model.layers", "transformer.h", "gpt_neox.layers"):
        obj = model
        ok = True
        for a in attr.split("."):
            if hasattr(obj, a):
                obj = getattr(obj, a)
            else:
                ok = False
                break
        if ok:
            return obj
    raise ValueError("Could not find decoder layers on this model")


@torch.no_grad()
def cache_residuals(model, tok, texts: Iterable[str], layers: List[int], max_positions: Optional[int] = 32,
                    batch_size: int = 8, max_length: int = 256, chat_template: bool = False,
                    positions_from_end: bool = False, store_dtype=torch.float16) -> Dict[int, torch.Tensor]:
    """Cache residual-stream activations after each block in `layers`.

    Returns {layer: tensor (N, P, d) `store_dtype` (default float16) on CPU} where P = max_positions (padded with NaN for short texts).
    If positions_from_end=True, P slots are the *last* P real tokens (useful for last-token probes).
    """
    texts = list(texts)
    blocks = _decoder_layers(model)
    store: Dict[int, List[torch.Tensor]] = {l: [] for l in layers}
    captured: Dict[int, torch.Tensor] = {}

    def mk_hook(l):
        def hook(_m, _i, out):
            captured[l] = (out[0] if isinstance(out, tuple) else out).detach()
        return hook

    handles = [blocks[l].register_forward_hook(mk_hook(l)) for l in layers]
    try:
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i + batch_size]
            if chat_template:
                chunk = [tok.apply_chat_template([{"role": "user", "content": t}], tokenize=False,
                                                 add_generation_prompt=True) for t in chunk]
            enc = tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=max_length).to(model.device)
            model(**enc)
            lengths = enc["attention_mask"].sum(1).tolist()
            for l in layers:
                h = captured[l].float().cpu()  # (B, T, d)
                B, T, d = h.shape
                P = max_positions or T
                out = torch.full((B, P, d), float("nan"), dtype=store_dtype)
                for b, L in enumerate(lengths):
                    if positions_from_end:
                        src = h[b, max(0, L - P):L]
                        out[b, P - src.shape[0]:] = src.to(store_dtype)
                    else:
                        src = h[b, :min(L, P)]
                        out[b, :src.shape[0]] = src.to(store_dtype)
                store[l].append(out)
    finally:
        for hd in handles:
            hd.remove()
    return {l: torch.cat(v, 0) for l, v in store.items()}


def save_cache(acts: Dict[int, torch.Tensor], path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save({int(k): v for k, v in acts.items()}, path)


def load_cache(path: str) -> Dict[int, torch.Tensor]:
    return torch.load(path, map_location="cpu")


def nanmean(x: torch.Tensor, dim: int) -> torch.Tensor:
    mask = ~torch.isnan(x)
    return torch.where(mask, x, torch.zeros_like(x)).sum(dim) / mask.sum(dim).clamp(min=1)


def mean_diff_by_position(acts_a: torch.Tensor, acts_b: torch.Tensor) -> torch.Tensor:
    """Position-slotted mean difference (P, d) = mean_p(A) − mean_p(B) over the same texts."""
    return nanmean(acts_a.float(), 0) - nanmean(acts_b.float(), 0)


def global_mean_diff(acts_a: torch.Tensor, acts_b: torch.Tensor, skip_first: int = 2) -> torch.Tensor:
    """Mean difference pooled over positions >= skip_first (the 'bias term' candidate d̄)."""
    da = nanmean(acts_a[:, skip_first:].float().reshape(-1, acts_a.shape[-1]), 0)
    db = nanmean(acts_b[:, skip_first:].float().reshape(-1, acts_b.shape[-1]), 0)
    return da - db


def residual_norm_by_position(acts: torch.Tensor) -> torch.Tensor:
    """Mean ‖h‖ per position (P,) for scaling diffs relative to the residual stream."""
    return nanmean(acts.float().norm(dim=-1), 0)


def cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    return float(torch.nn.functional.cosine_similarity(a.flatten().float(), b.flatten().float(), dim=0))


@dataclass
class DirectionStats:
    cos_to_global: np.ndarray      # (P,) cos(d_p, d̄)
    norm_ratio: np.ndarray         # (P,) ‖d_p‖ / ‖d̄‖
    rel_norm: np.ndarray           # (P,) ‖d_p‖ / mean‖h_p‖


def direction_stats(d_pos: torch.Tensor, d_global: torch.Tensor, h_norm: torch.Tensor) -> DirectionStats:
    cos = torch.nn.functional.cosine_similarity(d_pos.float(), d_global.float()[None, :], dim=-1)
    return DirectionStats(cos.numpy(), (d_pos.norm(dim=-1) / d_global.norm()).numpy(),
                          (d_pos.norm(dim=-1) / h_norm).numpy())
