"""Frozen complete-answer token paths and exact-prefix greedy diagnostics.

This sidecar does not alter the original one-token A02 measurement. Its main
likelihood event is a complete-word *prefix*: all suffix tokens are teacher
forced, with no length normalization, but further text may follow. The separately
reported immediate-EOS event requires EOS directly after that frozen word path.
Neither likelihood is the probability of every possible textual rendering.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from projects.g_agreement.r_bench import exact_prefix as E


@dataclass(frozen=True)
class AnswerPath:
    candidate_index: int
    surface: str
    token_ids: tuple[int, ...]
    form: str

    def as_dict(self) -> dict[str, Any]:
        return {"candidate_index": self.candidate_index, "surface": self.surface,
                "token_ids": list(self.token_ids), "form": self.form}


@dataclass(frozen=True)
class AnswerPaths:
    candidates: tuple[str, ...]
    paths: tuple[AnswerPath, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"candidates": list(self.candidates), "paths": [p.as_dict() for p in self.paths],
                "probability_event": "prefix paths; may continue beyond the word",
                "canonicalization": "none in probability paths; exact bare or one ASCII space"}


def _decode(tokenizer: Any, ids: Sequence[int]) -> str:
    try:
        return tokenizer.decode(list(ids), skip_special_tokens=False, clean_up_tokenization_spaces=False)
    except TypeError:
        return tokenizer.decode(list(ids), skip_special_tokens=False)


def _validate_paths(contract: AnswerPaths) -> None:
    if not contract.candidates or len(set(contract.candidates)) != len(contract.candidates):
        raise ValueError("candidate strings must be nonempty and distinct")
    if any(not c or c.strip() != c for c in contract.candidates):
        raise ValueError("candidate strings must have no surrounding whitespace")
    expected = {(i, form) for i in range(len(contract.candidates)) for form in ("bare", "leading_space")}
    if {(p.candidate_index, p.form) for p in contract.paths} != expected or len(contract.paths) != len(expected):
        raise ValueError("each candidate requires exactly one bare and one leading-space path")
    for i, path in enumerate(contract.paths):
        expected_surface = (" " if path.form == "leading_space" else "") + contract.candidates[path.candidate_index]
        if path.surface != expected_surface or not path.token_ids or any(t < 0 for t in path.token_ids):
            raise ValueError("invalid frozen path surface or token IDs")
        for other in contract.paths[i + 1:]:
            k = min(len(path.token_ids), len(other.token_ids))
            if path.token_ids[:k] == other.token_ids[:k]:
                reason = "duplicate" if path.token_ids == other.token_ids else "prefix overlap"
                raise ValueError(f"{reason} between frozen answer paths {path.surface!r} and {other.surface!r}; union mass is not identifiable by summation")


def freeze_answer_paths(tokenizer: Any, candidates: Sequence[str], *, max_answer_tokens: int = 8) -> AnswerPaths:
    """Freeze two exact suffix encodings per word, without re-encoding prefixes.

    Require distinct, globally prefix-free paths, exact decoded surface round trips,
    no special tokens, and a candidate token length within the frozen greedy cap.
    A failed condition raises rather than dropping/merging a rendering.
    """
    paths = []
    special = set(getattr(tokenizer, "all_special_ids", ()))
    if max_answer_tokens < 1:
        raise ValueError("max_answer_tokens must be positive")
    for i, candidate in enumerate(candidates):
        for form, surface in (("bare", candidate), ("leading_space", " " + candidate)):
            ids = tuple(int(t) for t in tokenizer(surface, add_special_tokens=False)["input_ids"])
            if not ids or len(ids) > max_answer_tokens:
                raise ValueError(f"answer path {surface!r} is empty or exceeds {max_answer_tokens} tokens")
            if special.intersection(ids):
                raise ValueError(f"answer path {surface!r} contains a special token")
            if _decode(tokenizer, ids) != surface:
                raise ValueError(f"answer path {surface!r} does not decode exactly to its frozen surface")
            paths.append(AnswerPath(i, surface, ids, form))
    contract = AnswerPaths(tuple(candidates), tuple(paths))
    _validate_paths(contract)
    return contract


def _padded(rows: Sequence[Sequence[int]], pad: int, device: Any, side: str) -> tuple[Any, Any, Any]:
    import torch

    if side not in ("left", "right") or not rows or any(not row for row in rows):
        raise ValueError("nonempty rows and left/right padding are required")
    n = max(map(len, rows))
    ids = torch.full((len(rows), n), int(pad), dtype=torch.long, device=device)
    mask = torch.zeros_like(ids)
    for i, row in enumerate(rows):
        start = n - len(row) if side == "left" else 0
        ids[i, start:start + len(row)] = torch.as_tensor(row, dtype=torch.long, device=device)
        mask[i, start:start + len(row)] = 1
    positions = (mask.cumsum(-1) - 1).clamp_min(0)
    return ids, mask, positions


def _forward_logits(model: Any, ids: Any, mask: Any, positions: Any, keep: int) -> tuple[Any, int]:
    """Return logits and their absolute padded-sequence offset."""
    kwargs = dict(input_ids=ids, attention_mask=mask, position_ids=positions, use_cache=False)
    try:
        logits = model(logits_to_keep=keep, **kwargs).logits
    except TypeError as exc:
        if "logits_to_keep" not in str(exc):
            raise
        logits = model(**kwargs).logits
    if logits.ndim != 3 or logits.shape[0] != ids.shape[0]:
        raise RuntimeError("model returned malformed vocabulary logits")
    if logits.shape[1] == ids.shape[1]:
        return logits, 0
    if logits.shape[1] == keep:
        return logits, ids.shape[1] - keep
    raise RuntimeError("model logits do not cover the requested prediction positions")


def _eos_ids(eos_token_ids: Sequence[int] | int | None) -> tuple[int, ...]:
    if eos_token_ids is None:
        return ()
    ids = (int(eos_token_ids),) if isinstance(eos_token_ids, int) else tuple(int(i) for i in eos_token_ids)
    if len(ids) != len(set(ids)) or any(i < 0 for i in ids):
        raise ValueError("EOS IDs must be distinct nonnegative integers")
    return ids


def score_complete_answers(model: Any, prefix_rows: Sequence[Sequence[int]],
                           answer_paths: AnswerPaths | Sequence[AnswerPaths], *,
                           pad_token_id: int, adapter_name: str | None,
                           eos_token_ids: Sequence[int] | int | None = None,
                           batch: int = 16, padding_side: str = "right",
                           max_input_tokens: int | None = None) -> list[dict[str, Any]]:
    """Teacher-force every frozen suffix token, summing log probabilities.

    Prefix IDs are copied verbatim and suffix IDs appended manually. All paths of
    a prefix share a forward batch; ``batch`` caps candidate-path rows, not items.
    Optional EOS diagnostics sum the distinct terminal-token alternatives directly
    after the word. Scores never include padding, nor divide by token length.
    """
    import torch

    if not prefix_rows or any(not row for row in prefix_rows):
        raise ValueError("exact prefix rows must be nonempty")
    contracts = [answer_paths] * len(prefix_rows) if isinstance(answer_paths, AnswerPaths) else list(answer_paths)
    if len(contracts) != len(prefix_rows):
        raise ValueError("answer contracts must align with prefix rows")
    eos = _eos_ids(eos_token_ids)
    for contract in contracts:
        _validate_paths(contract)
        if len(contract.paths) > batch:
            raise ValueError("batch cannot hold all paths of one prefix together")
        if any(set(p.token_ids).intersection(eos) for p in contract.paths):
            raise ValueError("answer path may not contain EOS")
    device = next(model.parameters()).device
    output = []
    start = 0
    while start < len(prefix_rows):
        stop, count = start, 0
        while stop < len(prefix_rows) and count + len(contracts[stop].paths) <= batch:
            count += len(contracts[stop].paths)
            stop += 1
        rows, heads, paths, owners = [], [], [], []
        for i in range(start, stop):
            for path in contracts[i].paths:
                row = list(prefix_rows[i]) + list(path.token_ids)
                if max_input_tokens is not None and len(row) > max_input_tokens:
                    raise ValueError("complete-answer row exceeds frozen input ceiling; no truncation allowed")
                rows.append(row)
                heads.append(len(prefix_rows[i]))
                paths.append(path)
                owners.append(i)
        ids, mask, positions = _padded(rows, pad_token_id, device, padding_side)
        starts = [ids.shape[1] - len(row) if padding_side == "left" else 0 for row in rows]
        first_prediction = min(pad_start + head - 1 for pad_start, head in zip(starts, heads))
        keep = ids.shape[1] - first_prediction
        with torch.no_grad(), E.adapter_context(model, adapter_name):
            logits, offset = _forward_logits(model, ids, mask, positions, keep)
            if not torch.isfinite(logits).all():
                raise ValueError("nonfinite complete-answer logits")
            if eos and max(eos) >= logits.shape[-1]:
                raise ValueError("EOS ID outside output vocabulary")
            lp = torch.log_softmax(logits.float(), dim=-1)
            path_scores = []
            for r, (path, head, pad_start) in enumerate(zip(paths, heads, starts)):
                prediction_positions = torch.arange(pad_start + head - 1,
                    pad_start + len(rows[r]) - 1, device=lp.device) - offset
                tokens = torch.as_tensor(path.token_ids, dtype=torch.long, device=lp.device)
                token_lps = lp[r, prediction_positions, tokens]
                total = float(token_lps.sum())
                end = pad_start + len(rows[r]) - 1 - offset
                eos_lp = float(torch.logsumexp(lp[r, end, list(eos)], -1)) if eos else None
                path_scores.append({**path.as_dict(), "token_logprobs": token_lps.tolist(), "logprob": total,
                                    "eos_next_logprob": eos_lp,
                                    "eos_terminated_logprob": None if eos_lp is None else total + eos_lp})
        for i in range(start, stop):
            contract = contracts[i]
            selected = [score for owner, score in zip(owners, path_scores) if owner == i]
            candidate_lps, terminal_lps = [], []
            for ci in range(len(contract.candidates)):
                matching = [p for p in selected if p["candidate_index"] == ci]
                candidate_lps.append(float(torch.logsumexp(torch.tensor([p["logprob"] for p in matching], dtype=torch.float64), 0)))
                if eos:
                    terminal_lps.append(float(torch.logsumexp(torch.tensor([p["eos_terminated_logprob"] for p in matching], dtype=torch.float64), 0)))
            probs = torch.tensor(candidate_lps, dtype=torch.float64).exp()
            terminal_probs = torch.tensor(terminal_lps, dtype=torch.float64).exp() if eos else None
            output.append({"candidates": list(contract.candidates), "path_scores": selected,
                "candidate_logprobs": candidate_lps, "candidate_probs": probs.tolist(), "candidate_mass": float(probs.sum()),
                "pair_conditional_probs": torch.softmax(torch.tensor(candidate_lps, dtype=torch.float64), 0).tolist(),
                "pair_argmax": contract.candidates[int(probs.argmax())],
                "eos_terminated_candidate_logprobs": terminal_lps if eos else None,
                "eos_terminated_candidate_probs": terminal_probs.tolist() if eos else None,
                "eos_terminated_candidate_mass": float(terminal_probs.sum()) if eos else None,
                "eos_token_ids": list(eos), "adapter_name": adapter_name,
                "n_prefix_tokens": len(prefix_rows[i]),
                "probability_event": "complete-word prefix paths; continuation beyond the word remains possible",
                "eos_probability_event": "frozen word path followed immediately by one configured EOS token" if eos else None,
                "length_normalization": False})
        start = stop
    return output


def greedy_complete_answers(model: Any, tokenizer: Any, prefix_rows: Sequence[Sequence[int]], *,
                            pad_token_id: int, adapter_name: str | None,
                            eos_token_ids: Sequence[int] | int,
                            max_new_tokens: int = 8, batch: int = 8,
                            max_input_tokens: int | None = None) -> list[dict[str, Any]]:
    """Raw vocabulary-argmax continuation from the exact prefix, at most 8 tokens.

    Replay the full prefix at each step, left padded with real position IDs. This
    avoids inherited generation defaults, logits processors and sampling. Stop
    each row at its first configured EOS; preserve that token as evidence. ``text``
    decodes all preceding tokens without removing specials or whitespace.
    """
    import torch

    if not prefix_rows or any(not row for row in prefix_rows):
        raise ValueError("exact prefix rows must be nonempty")
    if not 1 <= max_new_tokens <= 8 or batch < 1:
        raise ValueError("greedy max_new_tokens must be 1..8 and batch positive")
    eos = _eos_ids(eos_token_ids)
    if not eos:
        raise ValueError("greedy EOS IDs must be frozen explicitly")
    device = next(model.parameters()).device
    output = []
    for start in range(0, len(prefix_rows), batch):
        chunk = prefix_rows[start:start + batch]
        generated: list[list[int]] = [[] for _ in chunk]
        step_lps: list[list[float]] = [[] for _ in chunk]
        active = list(range(len(chunk)))
        for _ in range(max_new_tokens):
            rows = [list(chunk[i]) + generated[i] for i in active]
            if max_input_tokens is not None and any(len(r) > max_input_tokens for r in rows):
                raise ValueError("greedy replay exceeds frozen input ceiling; no truncation allowed")
            ids, mask, positions = _padded(rows, pad_token_id, device, "left")
            with torch.no_grad(), E.adapter_context(model, adapter_name):
                logits, _offset = _forward_logits(model, ids, mask, positions, 1)
                next_logits = logits[:, -1].float()
                if not torch.isfinite(next_logits).all():
                    raise ValueError("nonfinite greedy logits")
                if max(eos) >= next_logits.shape[-1]:
                    raise ValueError("EOS ID outside output vocabulary")
                next_ids = next_logits.argmax(-1)
                selected_lp = torch.log_softmax(next_logits, -1).gather(-1, next_ids[:, None]).squeeze(-1)
            remaining = []
            for i, token, token_lp in zip(active, next_ids.tolist(), selected_lp.tolist()):
                generated[i].append(token)
                step_lps[i].append(token_lp)
                if token not in eos:
                    remaining.append(i)
            active = remaining
            if not active:
                break
        for i, gen in enumerate(generated):
            stopped = gen[-1] in eos
            answer = gen[:-1] if stopped else gen
            output.append({"generated_token_ids": gen, "answer_token_ids": answer,
                           "text": _decode(tokenizer, answer), "raw_text": _decode(tokenizer, gen),
                           "finish_reason": "eos" if stopped else "length", "eos_reached": stopped,
                           "n_generated_tokens": len(gen), "step_token_logprobs": step_lps[i],
                           "eos_token_ids": list(eos), "max_new_tokens": max_new_tokens,
                           "n_prefix_tokens": len(chunk[i]), "adapter_name": adapter_name,
                           "generation_policy": "raw vocabulary argmax; full-prefix replay; no sampling, logit processors, or cache"})
    return output
