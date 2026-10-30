"""The probed model: load Qwen3.6-27B (pinned revision, bf16), render a chat prompt with
thinking off, and capture the output of one decoder block at chosen positions.

Conventions (match wsbench ``produce.backend`` and the NLA extractor): a "layer L" activation is
the OUTPUT of decoder block ``blocks[L]`` (forward hook; == ``hidden_states[L+1]``). The capture
forward never contains generated tokens; the last position of the render is the assistant onset
after the empty ``<think>\\n\\n</think>\\n\\n`` block (``pre_answer``).
"""

from __future__ import annotations

import gc
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from . import config as C

BLOCK_PATHS = ("model.layers", "model.language_model.layers", "base_model.model.model.layers",
               "base_model.model.model.language_model.layers")
NORM_PATHS = ("model.norm", "model.language_model.norm", "base_model.model.model.norm",
              "base_model.model.model.language_model.norm")


def _resolve(obj: Any, paths: tuple[str, ...]) -> Any:
    for path in paths:
        cur = obj
        try:
            for part in path.split("."):
                cur = getattr(cur, part)
            return cur
        except AttributeError:
            continue
    raise AttributeError(f"none of {paths} found on {type(obj).__name__}")


def blocks(model: Any) -> Any:
    """The decoder block ModuleList (as wsbench ``Backend.blocks``; PEFT-wrapped models too)."""
    return _resolve(model, BLOCK_PATHS)


def final_norm(model: Any) -> Any:
    return _resolve(model, NORM_PATHS)


def unembed_weight(model: Any) -> Any:
    return model.get_output_embeddings().weight


def disable_adapter_ctx(model: Any):
    """A context in which a mounted PEFT adapter is off (the probed model is always the base)."""
    return model.disable_adapter() if hasattr(model, "disable_adapter") else nullcontext()


# ------------------------------------------------------------------ loading
@dataclass
class Target:
    model: Any
    tokenizer: Any
    device: str
    model_id: str
    revision: str | None
    model_class: str

    @property
    def blocks(self) -> Any:
        return blocks(self.model)

    @property
    def n_layers(self) -> int:
        return len(self.blocks)


def load_tokenizer(model_id: str = C.TARGET_MODEL_ID, revision: str | None = C.TARGET_MODEL_SHA) -> Any:
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_id, revision=revision)


def load_target(
    model_id: str = C.TARGET_MODEL_ID,
    revision: str | None = C.TARGET_MODEL_SHA,
    device: str = "cuda",
    dtype: str = C.TARGET_DTYPE,
) -> Target:
    """AutoModelForCausalLM at the pinned revision (transformers 5.x resolves ``qwen3_5`` to the
    text-only ``Qwen3_5ForCausalLM``; the block path is found by ``blocks`` either way)."""
    import torch
    from transformers import AutoModelForCausalLM

    tok = load_tokenizer(model_id, revision)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, revision=revision, dtype=getattr(torch, dtype), device_map=device
    )
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    t = Target(model=model, tokenizer=tok, device=device, model_id=model_id, revision=revision,
               model_class=type(model).__name__)
    n = t.n_layers
    if n != C.N_LAYERS:
        raise RuntimeError(f"expected {C.N_LAYERS} decoder blocks, found {n}")
    return t


def unload(obj: Any) -> None:
    """Phase boundary: drop a model and free the device (del + gc + empty_cache)."""
    try:
        import torch
    except Exception:
        torch = None  # type: ignore
    if hasattr(obj, "model"):
        try:
            obj.model.cpu()
        except Exception:
            pass
        obj.model = None
    del obj
    gc.collect()
    if torch is not None and torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


# ------------------------------------------------------------------ rendering
def chat_ids(tokenizer: Any, messages: list[dict[str, str]], enable_thinking: bool = C.ENABLE_THINKING) -> list[int]:
    out = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, enable_thinking=enable_thinking
    )
    return list(out["input_ids"] if hasattr(out, "keys") else out)


def render_item(tokenizer: Any, prompt_text: str, system: str | None = None) -> list[int]:
    """The dataset render (INTERFACES §1 ``render: chat``): optional system turn + user turn,
    thinking off, generation prompt appended. Used for capture AND for the target answer."""
    msgs = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt_text}
    ]
    return chat_ids(tokenizer, msgs)


def render_text(tokenizer: Any, ids: list[int]) -> str:
    return tokenizer.decode(ids, skip_special_tokens=False)


def token_str(tokenizer: Any, tid: int) -> str:
    return tokenizer.decode([int(tid)])


def display_tokens(tokenizer: Any, ids: list[int]) -> list[str]:
    """wsbench ``render.display_tokens``: BPE strings with Ġ/▁ shown as a space."""
    return [
        t.replace("Ġ", " ").replace("▁", " ") if isinstance(t, str) else ""
        for t in tokenizer.convert_ids_to_tokens(ids)
    ]


# ------------------------------------------------------------------ capture
def capture(model: Any, ids: list[int], layers: list[int], positions: list[int], device: str | None = None) -> dict[int, Any]:
    """One forward pass over ``ids`` (no generated tokens); the output of each requested block
    at ``positions`` as fp32 CPU tensors ``[n_pos, d]``. Adapter disabled if one is mounted."""
    import torch

    blks = blocks(model)
    store: dict[int, Any] = {}
    handles = []
    want = torch.tensor(positions, dtype=torch.long)

    def make(layer: int):
        def hook(_mod, _inp, out):
            h = out[0] if isinstance(out, tuple) else out
            store[layer] = h[0, want.to(h.device), :].detach().float().cpu()

        return hook

    for layer in layers:
        if not 0 <= layer < len(blks):
            raise ValueError(f"layer {layer} out of range for a {len(blks)}-block model")
        handles.append(blks[layer].register_forward_hook(make(layer)))
    dev = device or next(model.parameters()).device
    try:
        with torch.no_grad(), disable_adapter_ctx(model):
            x = torch.tensor([ids], device=dev)
            try:
                model(x, use_cache=False, logits_to_keep=1)
            except TypeError:
                model(x, use_cache=False)
    finally:
        for h in handles:
            h.remove()
    missing = [layer for layer in layers if layer not in store]
    if missing:
        raise RuntimeError(f"hooks on blocks {missing} did not fire")
    return store


def capture_last(model: Any, ids: list[int], layer: int | None = None) -> Any:
    layer = C.LAYER if layer is None else layer
    """The block-``layer`` output at the LAST token of ``ids`` (fp32 CPU ``[d]``)."""
    return capture(model, ids, [layer], [len(ids) - 1])[layer][0]
