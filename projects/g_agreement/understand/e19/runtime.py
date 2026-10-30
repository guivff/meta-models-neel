"""E19 Oracle-reader steering at its pre-answer and true answer positions.

This module loads no models and joins no labels. It reuses ReaderRuntime's
carrier and activation injection; its teacher-forced score is the same mean of
paired summed log probabilities used by W1. Optional continuation truncation is
applied directly to candidate token IDs, never by decoding and retokenising.
"""
from __future__ import annotations

from contextlib import contextmanager
import math

import torch

from projects.g_agreement.understand.reader_runtime import ReaderRuntime, _hidden, _replace
from mats.capture import decoder_blocks


class E19Runtime:
    """Reuse one already-loaded Oracle runtime for every frozen intervention."""

    def __init__(self, oracle_runtime: ReaderRuntime, candidate_batch: int = 32):
        if oracle_runtime.name != "olens":
            raise ValueError("E19 requires the Oracle lens runtime")
        if type(candidate_batch) is not int or candidate_batch < 2:
            raise ValueError("candidate_batch must be an integer of at least two")
        self.oracle = oracle_runtime
        self.candidate_batch = candidate_batch

    def _unit(self, direction, width, name):
        unit = torch.as_tensor(direction, device=self.oracle.device, dtype=torch.float32).detach()
        if unit.shape != (width,) or not torch.isfinite(unit).all():
            raise ValueError(f"{name} must be a finite vector matching the residual width")
        if not torch.isclose(unit.norm(), unit.new_tensor(1.0), atol=1e-5, rtol=1e-5):
            raise ValueError(f"{name} must already be unit-normalized; no silent renormalisation")
        return unit

    @contextmanager
    def _steer(self, layer, edit_mask, delta, projection_direction, preanswer):
        """Edit only the selected positions; capture their projections at L+1."""
        blocks = decoder_blocks(self.oracle.model)
        state = {}

        def edit(_module, _inputs, output):
            hidden = _hidden(output)
            if hidden.shape[:2] != edit_mask.shape:
                raise RuntimeError("reader residual shape differs from the frozen token mask")
            if "edited" in state:
                raise RuntimeError("reader steering hook fired more than once per forward")
            state["edited"] = True
            if bool(torch.count_nonzero(delta)):
                changed = hidden.clone()
                changed[edit_mask] = (hidden[edit_mask].float() + delta).to(hidden.dtype)
                return _replace(output, changed)
            return output  # Exact alpha=0 path, including signed zeros.

        def capture(_module, _inputs, output):
            hidden = _hidden(output)
            if hidden.shape[:2] != edit_mask.shape or not state.get("edited"):
                raise RuntimeError("one-layer-later capture is not aligned with the intervention")
            if "projection" in state:
                raise RuntimeError("reader projection hook fired more than once per forward")
            # Only pre-answer and answer positions are transferred to CPU. The
            # returned validity mask excludes every right-padding token.
            state["projection"] = (hidden[:, preanswer:, :].float() @ projection_direction).cpu()

        handles = [blocks[layer].register_forward_hook(edit), blocks[layer+1].register_forward_hook(capture)]
        try:
            yield state
            if "projection" not in state:
                raise RuntimeError("the one-layer-later projection hook did not run")
        finally:
            for handle in handles:
                handle.remove()

    @torch.no_grad()
    def score(self, activations, pairs, layer: int, direction, sigma: float, alpha: float,
              projection_direction=None, max_candidate_tokens: int | None = None, prefix: str = ""):
        """Return per-item scores and per-candidate projections at reader layer L+1.

        ``direction`` is the frozen unit vector used for the edit. For random or
        content-control edits, pass the row's own unit probe as
        ``projection_direction``. The same supplied row sigma applies to every
        control, giving identical requested edit norms |alpha*sigma|. The residual
        itself is never renormalised. ``layer`` means the zero-based reader block
        output, distinct from the target block used by the carrier (normally 44).
        ``prefix`` is tokenised separately and appended after the native carrier,
        matching OracleLens scoring (E15 uses ``'- '``). The pre-answer position
        is the last prefix token when a prefix is present.
        """
        h = self.oracle._acts(activations)
        if type(layer) is not int or not 0 <= layer < len(decoder_blocks(self.oracle.model))-1:
            raise ValueError("steering layer must have a following decoder layer")
        sigma, alpha = float(sigma), float(alpha)
        if not math.isfinite(sigma) or sigma <= 0 or not math.isfinite(alpha) or not math.isfinite(alpha*sigma):
            raise ValueError("sigma must be finite and positive; alpha and alpha*sigma must be finite")
        if max_candidate_tokens is not None and (type(max_candidate_tokens) is not int or max_candidate_tokens < 1):
            raise ValueError("max_candidate_tokens must be a positive integer or None")
        if not isinstance(prefix, str):
            raise ValueError("prefix must be a string")
        pairs = list(pairs)
        if not pairs or any(not isinstance(pair, (list, tuple)) or len(pair) != 2
                            or any(not isinstance(candidate, str) or not candidate for candidate in pair) for pair in pairs):
            raise ValueError("pairs must contain nonempty candidate string pairs")
        unit = self._unit(direction, h.shape[-1], "direction")
        projection_unit = self._unit(direction if projection_direction is None else projection_direction,
                                     h.shape[-1], "projection_direction")
        delta = alpha * sigma * unit
        head, marker = self.oracle._head()
        prefix_ids = self.oracle.reader.tok.encode(prefix, add_special_tokens=False) if prefix else []
        head = head + prefix_ids
        preanswer = len(head)-1
        if not 0 <= marker < preanswer:
            raise ValueError("Oracle activation marker must precede the pre-answer position")
        tokenised = [[self.oracle.reader.tok.encode(candidate, add_special_tokens=False) for candidate in pair]
                     for pair in pairs]
        if any(not candidate for pair in tokenised for candidate in pair):
            raise ValueError("empty tokenised candidate")
        original_lengths = [[len(candidate) for candidate in pair] for pair in tokenised]
        if max_candidate_tokens is not None:
            tokenised = [[candidate[:max_candidate_tokens] for candidate in pair] for pair in tokenised]
        pair_scores = torch.empty((len(h), len(pairs)), dtype=torch.float32)
        projection_preanswer = torch.empty((len(h), len(pairs), 2), dtype=torch.float32)
        projection_answer_mean = torch.empty_like(projection_preanswer)
        projection_records = []
        per = self.candidate_batch // 2

        for start in range(0, len(h), per):
            acts = h[start:start+per]
            for pair_index, candidates in enumerate(tokenised):
                width = len(head) + max(map(len, candidates))
                pad = self.oracle.reader.tok.pad_token_id or 0
                ids = torch.full((len(acts)*2, width), pad, dtype=torch.long, device=self.oracle.device)
                attention_mask = torch.zeros_like(ids)
                lengths = torch.tensor([len(candidates[row % 2]) for row in range(len(ids))], device=self.oracle.device)
                for row in range(len(ids)):
                    sequence = head + candidates[row % 2]
                    ids[row, :len(sequence)] = torch.tensor(sequence, device=self.oracle.device)
                    attention_mask[row, :len(sequence)] = 1
                edit_mask = attention_mask.bool() & (torch.arange(width, device=self.oracle.device)[None] >= preanswer)
                vectors = acts.repeat_interleave(2, dim=0)
                embeddings = self.oracle._embeddings(ids, vectors, marker)
                with self.oracle._injection(vectors), self._steer(layer, edit_mask, delta, projection_unit, preanswer) as captured:
                    logits = self.oracle.model(inputs_embeds=embeddings, attention_mask=attention_mask,
                                               use_cache=False, logits_to_keep=width-len(head)+1).logits
                token_lp = logits[:, :-1].float().log_softmax(-1).gather(-1, ids[:, len(head):, None]).squeeze(-1)
                valid = torch.arange(token_lp.shape[1], device=self.oracle.device)[None] < lengths[:, None]
                lp = (token_lp * valid).sum(-1).reshape(len(acts), 2)
                pair_scores[start:start+len(acts), pair_index] = (lp[:, 0]-lp[:, 1]).cpu()
                projections = captured["projection"]
                for row in range(len(ids)):
                    item_index, candidate_index = start+row//2, row % 2
                    tokens = candidates[candidate_index]
                    values = projections[row, :len(tokens)+1]
                    projection_preanswer[item_index, pair_index, candidate_index] = values[0]
                    projection_answer_mean[item_index, pair_index, candidate_index] = values[1:].mean()
                    projection_records.append({"item_index": item_index, "pair_index": pair_index,
                        "candidate_index": candidate_index, "positions": list(range(preanswer, preanswer+len(tokens)+1)),
                        "roles": ["preanswer"]+["answer"]*len(tokens),
                        "token_ids": [head[-1]]+tokens, "values": values.tolist()})
        if any(not torch.isfinite(value).all() for value in (pair_scores, projection_preanswer, projection_answer_mean)):
            raise ValueError("nonfinite E19 scores or one-layer-later projections")
        return {"status": "COMPLETE", "scores": pair_scores.mean(1), "per_pair_scores": pair_scores,
                "projection_preanswer": projection_preanswer, "projection_answer_mean": projection_answer_mean,
                "projections": projection_records,
                "metadata": {"reader": "olens", "target_layer": self.oracle.layer,
                    "steering_layer": layer, "projection_layer": layer+1,
                    "edit": "plain_additive_alpha_sigma_unit_no_residual_renormalization",
                    "edited_positions": "preanswer_and_true_answer_tokens_only",
                    "sigma": sigma, "alpha": alpha, "requested_edit_norm": abs(alpha*sigma),
                    "direction_norm": float(unit.norm()), "projection_direction_norm": float(projection_unit.norm()),
                    "candidate_batch": self.candidate_batch, "head_ids": head,
                    "prefix": prefix, "prefix_ids": prefix_ids,
                    "preanswer_position": preanswer, "activation_marker": marker,
                    "candidate_lengths": [[len(candidate) for candidate in pair] for pair in tokenised],
                    "original_candidate_lengths": original_lengths, "max_candidate_tokens": max_candidate_tokens,
                    "score_kind": "mean_paired_summed_sequence_logodds"}}
