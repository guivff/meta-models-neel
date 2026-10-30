"""Exact-prefix target behavior and a literal, questioned Oracle interface.

Target logits always come from each row's last *real* token, never from a
rewritten question or the padded batch end. L is a zero-based decoder output
(``hidden_states[L + 1]``). Bind Oracle before mounting factual adapters, then
explicitly name the factual adapter for capture and the original Oracle adapter
(usually ``default``) for every reader forward. Native readers remain unchanged.

The questioned carrier is an experimental interface. Its state-only source is
``[not supplied]``; full-text controls supply complete source text and zero H.
Candidate likelihoods in ``summarize_logits`` are unconditional vocabulary mass;
``pair_conditional_probs`` and reader LO are explicitly separate diagnostics.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Sequence

from projects.g_agreement.core import model as M
from projects.g_agreement.core import scoring_lo as LO

QUESTIONED_ORACLE_TEMPLATE = (
    "An activation vector from layer {L} of a language model is enclosed in activation tags: <activation>{marker}</activation>.\n"
    "Source text: {source_text}\n"
    "{question}\n"
    "Choose exactly one: {v0} | {v1}. Return only that value."
)


def _active_names(model: Any) -> tuple[str, ...]:
    names = getattr(model, "active_adapters", None)
    if callable(names):
        names = names()
    if not names:
        names = getattr(model, "active_adapter", None)
    if isinstance(names, str):
        names = [names]
    return tuple(names or ())


def validate_adapter(model: Any, name: str) -> None:
    """Fail closed on absent, mixed, incorrectly selected, or disabled adapters."""
    if name not in getattr(model, "peft_config", {}):
        raise RuntimeError(f"required adapter {name!r} is not mounted")
    if _active_names(model) != (name,):
        raise RuntimeError(f"required adapter {name!r}; active adapters are {_active_names(model)!r}")
    for module in model.modules():
        if getattr(module, "disable_adapters", False) is True:
            raise RuntimeError(f"required adapter {name!r} is disabled")


@contextmanager
def adapter_context(model: Any, name: str | None) -> Iterator[Any]:
    """Activate exactly ``name`` and restore on success/failure; None means base.

    A named adapter is mandatory for PEFT target/reader passes. A surrounding
    disable-adapter context is rejected, rather than silently measuring base.
    """
    if name is None:
        with M.disable_adapter_ctx(model):
            if hasattr(model, "peft_config"):
                flags = [getattr(m, "disable_adapters") for m in model.modules()
                         if isinstance(getattr(m, "disable_adapters", None), bool)]
                if not flags or not all(flags):
                    raise RuntimeError("could not verify that all adapters are disabled for base pass")
            yield model
        return
    if not hasattr(model, "set_adapter") or name not in getattr(model, "peft_config", {}):
        raise RuntimeError(f"required adapter {name!r} is not mounted")
    previous = _active_names(model)
    try:
        model.set_adapter(name)
        validate_adapter(model, name)
        yield model
        validate_adapter(model, name)
    finally:
        if previous:
            model.set_adapter(previous[0] if len(previous) == 1 else list(previous))


def _padded(rows: Sequence[Sequence[int]], pad: int, device: Any, side: str = "right") -> tuple[Any, Any, Any, Any]:
    import torch

    if side not in ("left", "right"):
        raise ValueError("padding_side must be left or right")
    if not rows or any(not len(r) for r in rows):
        raise ValueError("prefix rows must be nonempty")
    n = max(map(len, rows))
    ids = torch.full((len(rows), n), int(pad), dtype=torch.long, device=device)
    mask = torch.zeros_like(ids)
    for i, row in enumerate(rows):
        start = n - len(row) if side == "left" else 0
        ids[i, start:start + len(row)] = torch.as_tensor(row, dtype=torch.long, device=device)
        mask[i, start:start + len(row)] = 1
    positions = (mask.cumsum(-1) - 1).clamp_min(0)
    # Mask-derived indices, not length-1 (wrong for left padding) or -1 (wrong for right).
    last = torch.arange(n, device=device).expand_as(mask).masked_fill(mask == 0, -1).max(-1).values
    return ids, mask, positions, last


def capture_exact_prefix(model: Any, rows: Sequence[Sequence[int]], *,
                         layers: Sequence[int] = (44,), pad_token_id: int,
                         adapter_name: str | None, padding_side: str = "right",
                         max_tokens: int | None = None, return_sequences: bool = False) -> dict[str, Any]:
    """Capture selected block outputs and vocabulary logits in the same forward.

    Input rows are the exact rendered prefixes, without candidate continuations.
    No truncation or generation occurs. CPU tensors retain model precision; raw
    logits and last-token states can be saved losslessly. Optional sequences
    contain only real tokens, in original order (useful for residual exchanges).
    Full logits are requested deliberately: ``logits_to_keep=1`` would pick the
    padded batch end for a short right-padded row.
    """
    import torch

    if max_tokens is not None and any(len(r) > max_tokens for r in rows):
        raise ValueError(f"prefix exceeds frozen {max_tokens}-token ceiling; no truncation allowed")
    if len(set(layers)) != len(layers):
        raise ValueError("layers must be unique")
    blocks = M.blocks(model)
    if any(L < 0 or L >= len(blocks) for L in layers):
        raise ValueError("decoder layer outside model")
    dev = next(model.parameters()).device
    ids, mask, positions, last = _padded(rows, pad_token_id, dev, padding_side)
    states: dict[int, Any] = {}
    sequences: dict[int, Any] = {}
    handles = []

    def make_hook(layer: int):
        def hook(_module: Any, _inputs: Any, output: Any) -> None:
            hidden = output[0] if isinstance(output, tuple) else output
            states[layer] = hidden[torch.arange(len(rows), device=hidden.device), last.to(hidden.device)].detach().cpu()
            if return_sequences:
                sequences[layer] = [hidden[i][mask[i].to(hidden.device).bool()].detach().cpu() for i in range(len(rows))]
        return hook

    try:
        handles = [blocks[L].register_forward_hook(make_hook(L)) for L in layers]
        with torch.no_grad(), adapter_context(model, adapter_name):
            result = model(input_ids=ids, attention_mask=mask, position_ids=positions, use_cache=False)
            logits = result.logits
            if logits.ndim != 3 or logits.shape[:2] != ids.shape:
                raise RuntimeError("exact-prefix capture requires vocabulary logits at every input position")
            selected = logits[torch.arange(len(rows), device=logits.device), last.to(logits.device)].detach().cpu()
    finally:
        for handle in handles:
            handle.remove()
    if set(states) != set(layers):
        raise RuntimeError(f"decoder capture hooks did not fire: {set(layers) - set(states)}")
    result = {"states": states, "logits": selected, "lengths": [len(r) for r in rows],
              "last_indices": last.cpu(), "attention_mask": mask.cpu(), "position_ids": positions.cpu(),
              "input_ids": ids.cpu(), "adapter_name": adapter_name, "padding_side": padding_side}
    if return_sequences:
        result["sequences"] = sequences
    return result


@dataclass(frozen=True)
class CandidateVocab:
    """Complete one-token words, canonicalized by whitespace stripping only."""
    candidates: tuple[str, ...]
    token_ids: tuple[tuple[int, ...], ...]
    renderings: tuple[tuple[str, ...], ...]
    vocab_size: int

    def as_dict(self) -> dict[str, Any]:
        return {"candidates": list(self.candidates), "token_ids": [list(x) for x in self.token_ids],
                "renderings": [list(x) for x in self.renderings], "vocab_size": self.vocab_size,
                "canonicalization": "strip surrounding whitespace only; case-sensitive; exclude special tokens"}


def _decode(tokenizer: Any, ids: list[int]) -> str:
    try:
        return tokenizer.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
    except TypeError:
        return tokenizer.decode(ids, skip_special_tokens=False)


def build_candidate_vocab(tokenizer: Any, candidates: Sequence[str]) -> CandidateVocab:
    """Freeze ALL vocabulary tokens whose entire decoded text is a candidate.

    This is not first-token matching. A multi-token word with no complete
    one-token rendering fails the one-token construction gate. Surrounding
    whitespace variants share a semantic value; case variants do not.
    """
    words = tuple(candidates)
    if len(words) < 2 or len(set(words)) != len(words) or any(not w or w.strip() != w for w in words):
        raise ValueError("candidate words must be distinct, nonempty and whitespace-canonical")
    vocab = tokenizer.get_vocab()
    specials = set(getattr(tokenizer, "all_special_ids", ()))
    ids_by_word: dict[str, list[int]] = {w: [] for w in words}
    forms_by_word: dict[str, list[str]] = {w: [] for w in words}
    for token_id in sorted(set(int(x) for x in vocab.values()) - specials):
        decoded = _decode(tokenizer, [token_id])
        canonical = decoded.strip()
        if canonical in ids_by_word:
            ids_by_word[canonical].append(token_id)
            forms_by_word[canonical].append(decoded)
    missing = [w for w in words if not ids_by_word[w]]
    if missing:
        raise ValueError(f"NOT RUN: no complete one-token rendering for {missing!r}")
    # Encoding at least one decoded form must round-trip to exactly one semantic token.
    for word in words:
        if not any(len(enc := LO.encode(tokenizer, form)) == 1 and enc[0] in ids_by_word[word]
                   for form in forms_by_word[word]):
            raise ValueError(f"NOT RUN: candidate {word!r} has no one-token round-trip rendering")
    size = max(int(x) for x in vocab.values()) + 1
    return CandidateVocab(words, tuple(tuple(ids_by_word[w]) for w in words),
                          tuple(tuple(forms_by_word[w]) for w in words), size)


def summarize_logits(logits: Any, vocab: CandidateVocab, tokenizer: Any = None) -> list[dict[str, Any]]:
    """Report unconditional candidate mass and global M, preserving out-of-set rows."""
    import torch

    z = torch.as_tensor(logits).detach().float()
    if z.ndim != 2 or z.shape[1] < vocab.vocab_size or not torch.isfinite(z).all():
        raise ValueError("expected finite [rows, vocabulary] logits covering the frozen tokenizer vocabulary")
    lp = torch.log_softmax(z, dim=-1)
    semantic_lp = torch.stack([torch.logsumexp(lp[:, list(ids)], -1) for ids in vocab.token_ids], -1)
    probs = semantic_lp.exp()
    conditional = torch.softmax(semantic_lp, -1)
    by_id = {token_id: word for word, ids in zip(vocab.candidates, vocab.token_ids) for token_id in ids}
    output = []
    for row in range(z.shape[0]):
        token_id = int(z[row].argmax())
        word = by_id.get(token_id)
        output.append({"candidates": list(vocab.candidates),
                       "candidate_token_ids": [list(x) for x in vocab.token_ids],
                       "candidate_token_logprobs": [[float(lp[row, i]) for i in ids] for ids in vocab.token_ids],
                       "candidate_logprobs": semantic_lp[row].tolist(), "candidate_probs": probs[row].tolist(),
                       "candidate_mass": float(probs[row].sum()),
                       "global_argmax_token_id": token_id,
                       "global_argmax_text": _decode(tokenizer, [token_id]) if tokenizer is not None else None,
                       "global_argmax_candidate": word, "out_of_set": word is None,
                       "pair_conditional_probs": conditional[row].tolist(),
                       "pair_argmax": vocab.candidates[int(semantic_lp[row].argmax())]})
    return output


@dataclass(frozen=True)
class OracleMarker:
    character: str
    token_id: int


@dataclass(frozen=True)
class Carrier:
    ids: tuple[int, ...]
    marker_index: int
    text: str
    layer: int
    question: str
    source_text: str
    candidates: tuple[str, str]


def freeze_oracle_marker(reader: Any, layer: int = 44) -> OracleMarker:
    """Freeze the native Oracle's marker once, before any pool/test scoring."""
    _ids, _slot, character, token_id = reader.carrier(layer)
    return OracleMarker(character, int(token_id))


def questioned_oracle_carrier(tokenizer: Any, layer: int, question: str,
                               candidates: Sequence[str], marker: OracleMarker,
                               source_text: str | None = None, max_tokens: int | None = None) -> Carrier:
    """Literal tournament carrier, ordinary chat rendering, thinking off."""
    if len(candidates) != 2 or candidates[0] == candidates[1]:
        raise ValueError("questioned Oracle requires two distinct candidates")
    if LO.encode(tokenizer, marker.character) != [marker.token_id]:
        raise ValueError("frozen marker/token ID does not match tokenizer")
    source = "[not supplied]" if source_text is None else source_text
    text = QUESTIONED_ORACLE_TEMPLATE.format(L=layer, marker=marker.character, source_text=source,
                                            question=question, v0=candidates[0], v1=candidates[1])
    ids = tuple(M.chat_ids(tokenizer, [{"role": "user", "content": text}]))
    slots = [i for i, token_id in enumerate(ids) if token_id == marker.token_id]
    if len(slots) != 1:
        raise ValueError("frozen Oracle marker must occur exactly once in the complete carrier")
    if max_tokens is not None and any(len(ids) + len(LO.encode(tokenizer, c)) > max_tokens for c in candidates):
        raise ValueError(f"Oracle carrier/completion exceeds frozen {max_tokens}-token ceiling; no truncation allowed")
    return Carrier(ids, slots[0], text, layer, question, source, tuple(candidates))


def full_source_text(item: dict[str, Any]) -> str:
    """Complete source prompt/history in the text-arm convention, never truncated."""
    prompt = item["prompt_text"]
    messages = item.get("capture_messages")
    if messages:
        if messages[-1] != {"role": "user", "content": prompt}:
            if messages[-1].get("role") != "user" or messages[-1].get("content") != prompt:
                raise ValueError("capture_messages must end in prompt_text as the user turn")
        turns = [(m["role"], m["content"]) for m in messages]
    elif item.get("system"):
        turns = [("system", item["system"]), ("user", prompt)]
    else:
        return prompt
    names = {"system": "System", "user": "User", "assistant": "Assistant"}
    return "\n".join(f"{names[role]}: {text}" for role, text in turns)


def score_questioned_oracle(reader: Any, H: Any, cand_pairs: Sequence[Sequence[str]],
                            questions: Sequence[str] | str, *, layer: int = 44,
                            source_texts: Sequence[str | None] | None = None,
                            adapter_name: str = "default", marker: OracleMarker | None = None,
                            max_tokens: int = 128, batch: int = 32) -> list[dict[str, Any]]:
    """Complete bare-value teacher-forced log likelihood with injected states.

    Both candidates share a forward batch. Variable carrier and candidate lengths
    are supported; all scored positions are aligned to their own head length.
    Passing zero H replaces the marker embedding with exactly zero. Native
    concept-bullet scoring continues to use ``LO.score_lo`` under adapter_context.
    """
    import torch

    if batch < 2:
        raise ValueError("batch must hold both candidates of an item")
    if H.ndim != 2 or len(H) != len(cand_pairs):
        raise ValueError("states and candidate pairs must have equal row counts")
    if isinstance(questions, str):
        questions = [questions] * len(H)
    sources = [None] * len(H) if source_texts is None else list(source_texts)
    if len(questions) != len(H) or len(sources) != len(H):
        raise ValueError("questions/source_texts must align with states")
    t = reader.target
    if t is None:
        raise ValueError("Oracle must be bound before scoring")
    model, tok = t.model, t.tokenizer
    marker = freeze_oracle_marker(reader, layer) if marker is None else marker
    carriers = [questioned_oracle_carrier(tok, layer, q, pair, marker, source, max_tokens)
                for q, pair, source in zip(questions, cand_pairs, sources)]
    dev = next(model.parameters()).device
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    embed = model.get_input_embeddings()
    out = []
    for start in range(0, len(H), batch // 2):
        stop = min(start + batch // 2, len(H))
        rows, heads, slots, vectors = [], [], [], []
        for i in range(start, stop):
            for candidate in cand_pairs[i]:
                completion = LO.encode(tok, candidate)  # bare value, never native '- {value}'
                if not completion:
                    raise ValueError("empty candidate completion")
                rows.append(list(carriers[i].ids) + completion)
                heads.append(len(carriers[i].ids))
                slots.append(carriers[i].marker_index)
                vectors.append(H[i])
        ids, mask, positions, _last = _padded(rows, pad, dev)
        with torch.no_grad(), adapter_context(model, adapter_name):
            embeddings = embed(ids).clone()
            for r, (slot, vector) in enumerate(zip(slots, vectors)):
                vector = vector.to(device=embeddings.device, dtype=torch.float32)
                if not torch.isfinite(vector).all():
                    raise ValueError("Oracle state contains nonfinite values")
                embeddings[r, slot] = (reader.alpha * vector / vector.norm().clamp_min(1e-9)).to(embeddings.dtype)
            # Keep only candidate prediction positions where supported, including
            # the shortest head. Every row still retains its own head boundary.
            keep = ids.shape[1] - min(heads) + 1
            kwargs = dict(inputs_embeds=embeddings, attention_mask=mask, position_ids=positions, use_cache=False)
            try:
                logits = model(logits_to_keep=keep, **kwargs).logits
            except TypeError as exc:
                if "logits_to_keep" not in str(exc):
                    raise
                logits = model(**kwargs).logits
            if logits.shape[1] == ids.shape[1]:
                offset = 0
            elif logits.shape[1] == keep:
                offset = ids.shape[1] - keep
            else:
                raise RuntimeError("unexpected reader logits position dimension")
            lp = torch.log_softmax(logits.float(), dim=-1)
            scores = []
            for r, (row, head) in enumerate(zip(rows, heads)):
                pred = torch.arange(head - 1, len(row) - 1, device=lp.device) - offset
                targets = ids[r, head:len(row)].to(lp.device)
                scores.append(float(lp[r, pred, targets].sum()))
        for j, i in enumerate(range(start, stop)):
            lp_a, lp_b = scores[2 * j:2 * j + 2]
            out.append({"reader": "questioned_olens", "cand_A": cand_pairs[i][0], "cand_B": cand_pairs[i][1],
                        "lp_A": lp_a, "lp_B": lp_b, "lo": lp_a - lp_b,
                        "templates": [QUESTIONED_ORACLE_TEMPLATE], "format": "bare_value",
                        "layer_in_prompt": layer, "marker_index": carriers[i].marker_index,
                        "marker_id": marker.token_id, "marker_char": marker.character,
                        "n_head_tokens": len(carriers[i].ids),
                        "n_tokens_A": len(rows[2 * j]) - heads[2 * j],
                        "n_tokens_B": len(rows[2 * j + 1]) - heads[2 * j + 1],
                        "question": questions[i], "source_text": carriers[i].source_text,
                        "adapter_name": adapter_name, "unscorable": False})
    return out
