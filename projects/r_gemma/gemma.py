"""The Gemma-2-9B-it target: loading, renders, prompt-only ids, left-padded teacher forcing, the logit lens.

Conventions (BRIEF_RG §2.2): a "layer L" state is the OUTPUT of decoder block L (== ``hook_resid_post`` L in the SAE
paper == ``hidden_states[L+1]``), read at the last token. ``chat`` = the text as the user turn + the generation prompt
(``<start_of_turn>model\\n``), read at its last token; ``raw`` = ``<bos>`` + the bare text, read at its last text token.
Teacher forcing uses LEFT padding with explicit position ids (the oracle repo's own batching), so every row's answer
tokens are the last ones and ``logits_to_keep`` bounds the materialised logits.
"""

from __future__ import annotations

from typing import Any

from projects.g_agreement.core import model as M
from projects.g_agreement.r_bench import datasets as D
from projects.r_gemma import config as G


# ------------------------------------------------------------------ loading
def load_target(model_id: str = G.TARGET_ID, revision: str | None = G.TARGET_SHA, device: str = "cuda",
                dtype: str = G.TARGET_DTYPE) -> M.Target:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id, revision=revision)
    model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, dtype=getattr(torch, dtype), device_map=device,
                                                 attn_implementation=G.ATTN_IMPL)
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    t = M.Target(model=model, tokenizer=tok, device=device, model_id=model_id, revision=revision, model_class=type(model).__name__)
    if t.n_layers != G.N_LAYERS:
        raise RuntimeError(f"expected {G.N_LAYERS} decoder blocks, found {t.n_layers}")
    return t


# ------------------------------------------------------------------ rendering
def encode(tokenizer: Any, text: str) -> list[int]:
    return list(tokenizer(text, add_special_tokens=False)["input_ids"])


def truncate_text(tokenizer: Any, text: str, max_tokens: int = G.MAX_TOKENS) -> str:
    ids = encode(tokenizer, text)
    return tokenizer.decode(ids[:max_tokens]) if len(ids) > max_tokens else text


def chat_ids(tokenizer: Any, user: str, assistant: str | None = None) -> tuple[list[int], list[int]]:
    """(head, full): ``head`` = the chat render of the user turn with the generation prompt appended (ends at the
    assistant onset); ``full`` = head + the assistant content (+ end-of-turn), as the oracle repo builds its training
    rows (template applied twice; ``full`` must extend ``head``)."""
    msgs = [{"role": "user", "content": user}]
    head = tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True)
    head = list(head["input_ids"] if hasattr(head, "keys") else head)
    if assistant is None:
        return head, head
    full = tokenizer.apply_chat_template(msgs + [{"role": "assistant", "content": assistant}], tokenize=True, add_generation_prompt=False)
    full = list(full["input_ids"] if hasattr(full, "keys") else full)
    if full[: len(head)] != head:
        raise RuntimeError("chat template: the full conversation does not extend the prompt render")
    return head, full


def bos_id(tokenizer: Any) -> int | None:
    return getattr(tokenizer, "bos_token_id", None)


def render_ids(tokenizer: Any, text: str, render: str, max_tokens: int = G.MAX_TOKENS) -> list[int]:
    text = truncate_text(tokenizer, text, max_tokens)
    if render == "raw":
        b = bos_id(tokenizer)
        return ([b] if b is not None else []) + encode(tokenizer, text)
    if render == "chat":
        return chat_ids(tokenizer, text)[0]
    raise ValueError(render)


def onset_token(tokenizer: Any) -> int:
    """The last token of the generation prompt (``<start_of_turn>model\\n`` → the newline piece)."""
    return chat_ids(tokenizer, "x")[0][-1]


def prompt_only_user(item: dict[str, Any], text: str) -> str:
    p = item["primary"]
    return D.PROMPT_ONLY_FC_TEMPLATE.format(text=text, question=p["question"], pos=p["candidates"][0], neg=p["candidates"][1])


def prompt_only_ids(tokenizer: Any, item: dict[str, Any], max_tokens: int = G.MAX_TOKENS) -> list[int]:
    text = truncate_text(tokenizer, item["prompt_text"], max_tokens)
    return chat_ids(tokenizer, prompt_only_user(item, text))[0]


# ------------------------------------------------------------------ first tokens for the logit lens (Y1 convention)
def spellings(cand: str) -> list[str]:
    out = []
    for s in (cand, " " + cand, cand.capitalize(), " " + cand.capitalize()):
        if s not in out:
            out.append(s)
    return out


def first_token_candidates(tokenizer: Any, pos: str, neg: str, jlens: list[str | None] | None = None) -> dict[str, Any]:
    """The first spelling (bare, space, capitalised) whose first tokens differ; the ``jlens_*`` short forms as the
    fallback; else unscorable with a reason. Returns {pos_id, neg_id, form, source, unscorable, reason}."""
    for source, (a, b) in (("candidates", (pos, neg)), ("jlens_forms", tuple(jlens or (None, None)))):
        if not a or not b:
            continue
        for form, sa, sb in zip(("bare", "space", "cap", "space_cap"), spellings(a), spellings(b)):
            ia, ib = encode(tokenizer, sa), encode(tokenizer, sb)
            if ia and ib and ia[0] != ib[0]:
                return {"pos_id": int(ia[0]), "neg_id": int(ib[0]), "form": form, "source": source, "unscorable": False, "reason": None}
    return {"pos_id": None, "neg_id": None, "form": None, "source": None, "unscorable": True,
            "reason": "candidates share their first token in every spelling"}


# ------------------------------------------------------------------ left-padded forwards
def left_pad(rows: list[list[int]], pad: int, device: Any) -> tuple[Any, Any, Any, list[int]]:
    """(ids, mask, position_ids, offsets): row i starts at offsets[i] = n - len(row i)."""
    import torch

    n = max(len(r) for r in rows)
    ids = torch.full((len(rows), n), pad, dtype=torch.long)
    mask = torch.zeros_like(ids)
    offsets = []
    for i, r in enumerate(rows):
        off = n - len(r)
        ids[i, off:] = torch.tensor(r)
        mask[i, off:] = 1
        offsets.append(off)
    pos = (mask.cumsum(-1) - 1).clamp(min=0)
    return ids.to(device), mask.to(device), pos.to(device), offsets


def forward_logits(model: Any, ids: Any, mask: Any, pos: Any, keep: int, inputs_embeds: Any = None) -> Any:
    kw: dict[str, Any] = {"attention_mask": mask, "position_ids": pos, "use_cache": False}
    if inputs_embeds is not None:
        kw["inputs_embeds"] = inputs_embeds
    else:
        kw["input_ids"] = ids
    try:
        logits = model(logits_to_keep=keep, **kw).logits
    except TypeError:
        logits = model(**kw).logits
    if logits.shape[1] != keep:
        logits = logits[:, -keep:]
    return logits


def teacher_forced_lp(model: Any, rows: list[list[int]], head_lens: list[int], pad: int, device: Any,
                      before_forward: Any = None) -> list[float]:
    """Σ log p(tokens after the head | head) per row; rows of different head and tail lengths in one left-padded
    forward. ``before_forward(offsets)`` lets a caller (the oracle hook) learn where each row starts."""
    import torch

    ids, mask, pos, offsets = left_pad(rows, pad, device)
    if before_forward is not None:
        before_forward(offsets)
    tails = [len(r) - h for r, h in zip(rows, head_lens)]
    keep = max(tails) + 1
    with torch.no_grad():
        logits = forward_logits(model, ids, mask, pos, keep)
        lp = torch.log_softmax(logits.float(), dim=-1)   # [B, keep, V]; position u (from the end) predicts ids[u+1]
        n = ids.shape[1]
        out = []
        for i, k in enumerate(tails):
            if k == 0:
                out.append(0.0)
                continue
            tgt = ids[i, n - k:]                                   # the k answer tokens
            pred = lp[i, keep - k - 1: keep - 1]                   # logits at the k positions before them
            out.append(float(pred.gather(-1, tgt[:, None]).sum()))
    return out


def next_token_lp(model: Any, rows: list[list[int]], pad: int, device: Any, token_ids: list[int],
                  before_forward: Any = None) -> list[list[float]]:
    """log p(token | row) at each row's last position for the given token ids (the yes/no form)."""
    import torch

    ids, mask, pos, offsets = left_pad(rows, pad, device)
    if before_forward is not None:
        before_forward(offsets)
    with torch.no_grad():
        logits = forward_logits(model, ids, mask, pos, 1)
        lp = torch.log_softmax(logits[:, -1].float(), dim=-1)
        return [[float(lp[i, t]) for t in token_ids] for i in range(len(rows))]


# ------------------------------------------------------------------ random-rotation readout (BRIEF_RG §10)
_ROT: dict[tuple[int, int], Any] = {}


def rotation(seed: int, d: int, device: Any = "cpu") -> Any:
    """A seeded random orthogonal [d, d] matrix (QR of a Gaussian), cached; the E13 control for a model without a J-lens."""
    import torch

    key = (seed, d)
    if key not in _ROT:
        g = torch.Generator().manual_seed(20261018 + seed)
        q, r = torch.linalg.qr(torch.randn(d, d, generator=g))
        _ROT[key] = (q * torch.sign(torch.diagonal(r))[None, :]).float()
    return _ROT[key].to(device)


# ------------------------------------------------------------------ logit lens
def softcap(model: Any) -> float | None:
    cfg = getattr(model, "config", None)
    return getattr(cfg, "final_logit_softcapping", None) if cfg is not None else None


def logit_lens_lp(model: Any, states: Any, token_ids: list[int]) -> Any:
    """[N, len(token_ids)] log-probs under final norm (+ Gemma's logit soft-capping) + W_U for fp32 CPU states."""
    import torch

    norm = M.final_norm(model)
    w_u = M.unembed_weight(model)
    dev, dt = w_u.device, w_u.dtype
    cap = softcap(model)
    with torch.no_grad():
        z = norm(states.to(dev, dt)[:, None, :])[:, 0]
        logits = (z @ w_u.T).float()
        if cap:
            logits = torch.tanh(logits / cap) * cap
        lp = torch.log_softmax(logits, dim=-1)
        return lp[:, token_ids].cpu()
