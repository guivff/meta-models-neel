"""Reusable official AR adapter, following P3's s58_run_ar / s66_features contracts.

No load or import of the official GPU stack until explicitly called by a gated worker.
"""
from pathlib import Path
import subprocess
import sys

OFFICIAL_SHA = "a32590085a6070d75f950155d3c2b3db3eec97ef"
WHITENER_SHA = "178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a"


def official_imports(source, whitener):
    from projects.g_agreement.blindspot.protocol import sha
    source = Path(source).resolve()
    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
    if head != OFFICIAL_SHA or dirty or sha(whitener) != WHITENER_SHA:
        raise ValueError("official source/whitener pin mismatch")
    for name, module in list(sys.modules.items()):
        if name.startswith("oracle_lens") and getattr(module, "__file__", None):
            if not Path(module.__file__).resolve().is_relative_to(source):
                raise ValueError("another official source is already imported")
    sys.path.insert(0, str(source/"src"))
    from oracle_lens.core.whitening import load_whitener
    return load_whitener(Path(whitener), ridge_c=0.1, device="cpu")


def load_reconstructor(source, whitener, ar_dir, model):
    ruler = official_imports(source, whitener)
    from oracle_lens.pipeline.ar_loader import load_reconstructor as load, verify_adapter_live, _unwrap_compiled_blocks
    from transformers import AutoTokenizer
    ar_dir = Path(ar_dir)
    tok = AutoTokenizer.from_pretrained(model, local_files_only=True, padding_side="right")
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    ar = load(ar_dir, model_id=str(model), device="cuda", attn_implementation="sdpa", eager=False)
    verify_adapter_live(ar.backbone, ar_dir/"lora")
    _unwrap_compiled_blocks(ar.backbone.get_base_model())
    return ar, tok, ruler


def reconstruct(ar, tok, texts):
    import torch
    tokens = tok(texts, add_special_tokens=False, return_tensors="pt", padding=True, truncation=False)
    if not bool((tokens["attention_mask"].sum(1)>0).all()):
        raise ValueError("empty AR input")
    limit = int(getattr(ar.backbone.config, "text_config", ar.backbone.config).max_position_embeddings)
    if tokens["input_ids"].shape[1]+ar.tag_ids.shape[1] > limit:
        raise ValueError("AR input exceeds context; no truncation")
    with torch.inference_mode():
        result = ar(tokens["input_ids"].cuda(), tokens["attention_mask"].cuda(), layer_idx=ar.layers.index(44))[:,0].float().cpu()
    if result.ndim != 2 or result.shape[0] != len(texts) or not torch.isfinite(result).all():
        raise ValueError("invalid AR prediction")
    return result
