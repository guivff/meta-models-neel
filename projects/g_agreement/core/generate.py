"""Generation with budgets, seeds and accounting: greedy target answers (32 new tokens from the
SAME render used for capture), greedy prompt-only answers, and the shared sampled-generation
primitive the verbalizers use (T=1.0, top_p=0.95, top_k=64, seeded per call).

``finish_reason`` is decided from the new tokens: ``eos`` if an EOS id was emitted (the output
is cut there), else ``length`` if the cap was reached."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from . import config as C
from . import model as M
from .accounting import timed_call


@dataclass
class GenResult:
    new_ids: list[int]
    raw_output: str  # decoded with skip_special_tokens=True
    n_prompt_tokens: int
    n_new_tokens: int
    finish_reason: str  # eos | length
    wall_s: float
    peak_mem_gb: float | None
    seed: int | None
    sampling: dict[str, Any] = field(default_factory=dict)

    def row(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("new_ids")
        return d


def eos_ids(tokenizer: Any, model: Any = None) -> set[int]:
    ids: set[int] = set()
    if tokenizer.eos_token_id is not None:
        ids.add(int(tokenizer.eos_token_id))
    gc = getattr(model, "generation_config", None)
    e = getattr(gc, "eos_token_id", None)
    if isinstance(e, int):
        ids.add(e)
    elif isinstance(e, (list, tuple)):
        ids.update(int(x) for x in e)
    for t in ("<|im_end|>", "<|endoftext|>"):
        try:
            tid = tokenizer.convert_tokens_to_ids(t)
            if isinstance(tid, int) and tid >= 0 and tid != getattr(tokenizer, "unk_token_id", -1):
                ids.add(tid)
        except Exception:
            pass
    return ids


def _finish(new_ids: list[int], cap: int, eos: set[int]) -> tuple[list[int], str]:
    """Cut at the first EOS; report eos/length."""
    for i, t in enumerate(new_ids):
        if t in eos:
            return new_ids[:i], "eos"
    return new_ids, ("length" if len(new_ids) >= cap else "eos")


def pad_id(tokenizer: Any) -> int:
    return tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id


def _gen_kwargs(sampling: dict[str, Any] | None, max_new_tokens: int) -> dict[str, Any]:
    if sampling is None or not sampling.get("do_sample", False):
        return {"do_sample": False, "temperature": None, "top_p": None, "top_k": None,
                "max_new_tokens": max_new_tokens, "num_beams": 1}
    return {"do_sample": True, "temperature": float(sampling["temperature"]),
            "top_p": float(sampling["top_p"]), "top_k": int(sampling["top_k"]),
            "max_new_tokens": max_new_tokens, "num_beams": 1}


def generate_ids(
    model: Any,
    tokenizer: Any,
    ids: list[int],
    *,
    max_new_tokens: int,
    sampling: dict[str, Any] | None = None,
    seed: int | None = None,
    inputs_embeds: Any = None,
    adapter_enabled: bool | None = None,
) -> GenResult:
    """One generation call from token ids (or from ``inputs_embeds`` built from those ids, in
    which case only new tokens come back). Seeds torch RNG (all devices) when ``seed`` given."""
    import torch

    dev = next(model.parameters()).device
    kw = _gen_kwargs(sampling, max_new_tokens)
    kw.update(pad_token_id=pad_id(tokenizer), num_return_sequences=1)
    eos = eos_ids(tokenizer, model)
    if seed is not None:
        torch.manual_seed(int(seed))
    ctx = M.disable_adapter_ctx(model) if adapter_enabled is False else _null()
    with timed_call() as st, torch.no_grad(), ctx:
        if inputs_embeds is not None:
            out = model.generate(
                inputs_embeds=inputs_embeds,
                attention_mask=torch.ones(1, len(ids), device=dev, dtype=torch.long),
                **kw,
            )
            new = out[0].tolist()  # with inputs_embeds only, HF returns the new tokens only
            if len(new) > max_new_tokens and new[: len(ids)] == list(ids):
                new = new[len(ids):]
        else:
            x = torch.tensor([ids], device=dev)
            out = model.generate(x, attention_mask=torch.ones_like(x), **kw)
            new = out[0, len(ids):].tolist()
    new_cut, reason = _finish(new, max_new_tokens, eos)
    text = tokenizer.decode(new_cut, skip_special_tokens=True)
    return GenResult(
        new_ids=new_cut, raw_output=text, n_prompt_tokens=len(ids), n_new_tokens=len(new_cut),
        finish_reason=reason, wall_s=st.wall_s, peak_mem_gb=st.peak_mem_gb, seed=seed,
        sampling={**(sampling or C.GREEDY), "max_new_tokens": max_new_tokens},
    )


class _null:
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


# ------------------------------------------------------------------ the three greedy uses
def target_answer(target: M.Target, item: dict[str, Any], max_new_tokens: int = C.TARGET_MAX_NEW_TOKENS) -> tuple[GenResult, list[int]]:
    """Greedy continuation of the SAME render used for capture (adapter off if mounted)."""
    ids = M.render_item(target.tokenizer, item["prompt_text"], item.get("system"))
    res = generate_ids(target.model, target.tokenizer, ids, max_new_tokens=max_new_tokens,
                       sampling=None, seed=None, adapter_enabled=False)
    return res, ids


def prompt_only_prompt(item: dict[str, Any]) -> str:
    return C.PROMPT_ONLY_TEMPLATE.format(prompt_text=item["prompt_text"], question=item["primary"]["question"])


def prompt_only_answer(target: M.Target, item: dict[str, Any], max_new_tokens: int = C.PROMPT_ONLY_MAX_NEW_TOKENS) -> tuple[GenResult, list[int], str]:
    """The G3 prompt-only arm: the frozen template (item prompt + primary question only), chat
    render with thinking off, greedy. Never sees a readout or a target answer."""
    visible = prompt_only_prompt(item)
    ids = M.render_item(target.tokenizer, visible, None)
    res = generate_ids(target.model, target.tokenizer, ids, max_new_tokens=max_new_tokens,
                       sampling=None, seed=None, adapter_enabled=False)
    return res, ids, visible
