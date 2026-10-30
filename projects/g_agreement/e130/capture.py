from typing import Any
import torch

def decoder_blocks(model: Any) -> torch.nn.ModuleList:
    """The decoder-block ModuleList (works through PeftModel / multimodal wrappers)."""
    n = getattr(getattr(model, "config", None), "num_hidden_layers", None)
    cands = [(name, m) for name, m in model.named_modules()
             if name.endswith("layers") and isinstance(m, torch.nn.ModuleList)]
    if n is not None:
        cands = [(name, m) for name, m in cands if len(m) == n] or cands
    if not cands:
        raise AttributeError("decoder blocks not found")
    return min(cands, key=lambda t: t[0].count("."))[1]
