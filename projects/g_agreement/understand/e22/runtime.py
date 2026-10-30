"""E22 cached donor patching inside the Oracle reader, with native scoring.

E22 layer L means the INPUT to decoder block L, unlike E19's block-output
intervention. At layer 0 the injection-position residual is the injected input
embedding, so replacing it must reproduce a full activation swap. Captures store
only two positions at the registered layer grid, on CPU; each patch uses these
cached tensors and performs no donor forward pass.
"""
from __future__ import annotations

from contextlib import contextmanager

import torch

from projects.g_agreement.understand.reader_runtime import ReaderRuntime
from mats.capture import decoder_blocks


def layer_grid(n_layers: int) -> list[int]:
    if type(n_layers) is not int or n_layers < 1:
        raise ValueError("positive decoder layer count required")
    return sorted(set(range(0, n_layers, 4)) | {n_layers-1})


def _hidden_input(args, kwargs):
    """Handle both positional and keyword-only HF decoder invocations."""
    if "hidden_states" in kwargs:
        if args and isinstance(args[0], torch.Tensor):
            raise ValueError("ambiguous positional and keyword hidden_states")
        hidden, location = kwargs["hidden_states"], "keyword"
    elif args:
        hidden, location = args[0], "positional"
    else:
        raise ValueError("decoder block did not receive hidden_states")
    if not isinstance(hidden, torch.Tensor) or hidden.ndim != 3:
        raise ValueError("decoder hidden_states must be a rank-three tensor")
    return hidden, location


class E22Runtime:
    """An inference-only wrapper around an already-loaded Oracle@44 runtime."""

    def __init__(self, oracle_runtime: ReaderRuntime, candidate_batch: int = 32):
        if oracle_runtime.name != "olens" or oracle_runtime.layer != 44:
            raise ValueError("E22 requires the Oracle lens at target block 44")
        if type(candidate_batch) is not int or candidate_batch < 2:
            raise ValueError("candidate_batch must be an integer of at least two")
        self.oracle = oracle_runtime
        self.candidate_batch = candidate_batch
        self.layers = layer_grid(len(decoder_blocks(self.oracle.model)))
        self.positions = ["injection", "preanswer"]

    def _contract(self, pairs, prefix):
        pairs = list(pairs)
        if (not pairs or any(not isinstance(pair, (list, tuple)) or len(pair) != 2
                             or any(not isinstance(c, str) or not c for c in pair) for pair in pairs)):
            raise ValueError("nonempty candidate string pairs required")
        if not isinstance(prefix, str):
            raise ValueError("prefix must be a string")
        head, marker = self.oracle._head()
        prefix_ids = self.oracle.reader.tok.encode(prefix, add_special_tokens=False) if prefix else []
        head = head + prefix_ids
        candidates = [[self.oracle.reader.tok.encode(c, add_special_tokens=False) for c in pair] for pair in pairs]
        if any(not c for pair in candidates for c in pair):
            raise ValueError("empty tokenised candidate")
        if not 0 <= marker < len(head)-1:
            raise ValueError("activation marker must precede preanswer")
        return {"reader": "olens", "target_layer": 44, "layer_convention": "decoder_block_input",
                "layer_ids": self.layers, "positions": self.positions,
                "position_indices": [marker, len(head)-1], "head_ids": head,
                "prefix": prefix, "prefix_ids": prefix_ids, "pairs": [list(p) for p in pairs],
                "candidate_ids": candidates, "candidate_batch": self.candidate_batch,
                "score_kind": "mean_paired_summed_sequence_logodds"}

    def _forward_pair(self, acts, candidates, contract):
        """Same activations × A/B layout and summed-token algebra as W1/E19."""
        head = contract["head_ids"]
        marker = contract["position_indices"][0]
        width = len(head)+max(map(len, candidates))
        ids = torch.full((len(acts)*2, width), self.oracle.reader.tok.pad_token_id or 0,
                         dtype=torch.long, device=self.oracle.device)
        mask = torch.zeros_like(ids)
        lengths = torch.tensor([len(candidates[r % 2]) for r in range(len(ids))], device=self.oracle.device)
        for row in range(len(ids)):
            sequence = head+candidates[row % 2]
            ids[row, :len(sequence)] = torch.tensor(sequence, device=self.oracle.device)
            mask[row, :len(sequence)] = 1
        vectors = acts.repeat_interleave(2, dim=0)
        embeddings = self.oracle._embeddings(ids, vectors, marker)
        with self.oracle._injection(vectors):
            logits = self.oracle.model(inputs_embeds=embeddings, attention_mask=mask,
                                       use_cache=False, logits_to_keep=width-len(head)+1).logits
        token_lp = logits[:, :-1].float().log_softmax(-1).gather(-1, ids[:, len(head):, None]).squeeze(-1)
        valid = torch.arange(token_lp.shape[1], device=self.oracle.device)[None] < lengths[:, None]
        scores = (token_lp*valid).sum(-1).reshape(len(acts), 2)
        return (scores[:, 0]-scores[:, 1]).cpu()

    @contextmanager
    def _capture_hooks(self, n_items, positions):
        state = {}
        handles = []
        try:
            for layer in self.layers:
                def hook(_module, args, kwargs, layer=layer):
                    hidden, _ = _hidden_input(args, kwargs)
                    if layer in state or len(hidden) != n_items*2:
                        raise RuntimeError("duplicate or misaligned donor capture")
                    state[layer] = hidden[:, positions, :].detach().float().cpu()
                handles.append(decoder_blocks(self.oracle.model)[layer].register_forward_pre_hook(hook, with_kwargs=True))
            yield state
            if set(state) != set(self.layers):
                raise RuntimeError("not all registered layer inputs were captured")
        finally:
            for handle in handles:
                handle.remove()

    @torch.no_grad()
    def capture(self, acts, pairs, prefix: str = ""):
        """Capture [item,pair,candidate,layer,position,width] on CPU.

        There is one native baseline forward for each pair in each activation
        batch. Both patch positions and every registered layer are captured in
        that same pass. The batch layout is identical to ``score_patch``.
        """
        h = self.oracle._acts(acts)
        contract = self._contract(pairs, prefix)
        count = len(contract["pairs"])
        scores = torch.empty((len(h), count), dtype=torch.float32)
        residuals = torch.empty((len(h), count, 2, len(self.layers), 2, h.shape[-1]), dtype=torch.float32)
        per = self.candidate_batch//2
        for start in range(0, len(h), per):
            chunk = h[start:start+per]
            for pair_index, candidates in enumerate(contract["candidate_ids"]):
                with self._capture_hooks(len(chunk), contract["position_indices"]) as state:
                    scores[start:start+len(chunk), pair_index] = self._forward_pair(chunk, candidates, contract)
                captured = torch.stack([state[layer] for layer in self.layers], dim=1)
                residuals[start:start+len(chunk), pair_index] = captured.reshape(len(chunk), 2, len(self.layers), 2, h.shape[-1])
        if not torch.isfinite(scores).all() or not torch.isfinite(residuals).all():
            raise ValueError("nonfinite baseline scores or donor residuals")
        return {"status": "COMPLETE", "scores": scores.mean(1), "per_pair_scores": scores,
                "residuals": residuals, "layer_ids": list(self.layers),
                "metadata": {**contract, "n_items": len(h), "hidden_size": h.shape[-1],
                             "residual_axes": ["item", "pair", "candidate", "layer", "position", "hidden"]}}

    @contextmanager
    def _patch_hook(self, layer, position, replacement):
        state = {"calls": 0}
        def hook(_module, args, kwargs):
            hidden, location = _hidden_input(args, kwargs)
            if state["calls"] or len(hidden) != len(replacement) or hidden.shape[-1] != replacement.shape[-1]:
                raise RuntimeError("duplicate or misaligned patch invocation")
            if not 0 <= position < hidden.shape[1]:
                raise RuntimeError("patch token position outside the reader sequence")
            state["calls"] += 1
            changed = hidden.clone()
            changed[:, position, :] = replacement.to(hidden.device, hidden.dtype)
            if location == "keyword":
                new_kwargs = dict(kwargs)
                new_kwargs["hidden_states"] = changed
                return args, new_kwargs
            return (changed, *args[1:]), kwargs
        handle = decoder_blocks(self.oracle.model)[layer].register_forward_pre_hook(hook, with_kwargs=True)
        try:
            yield
            if state["calls"] != 1:
                raise RuntimeError("patch hook did not run exactly once")
        finally:
            handle.remove()

    @torch.no_grad()
    def score_patch(self, recipient_acts, pairs, donor_capture, layer: int, position: str,
                    prefix: str = "", donor_indices=None):
        """Replace exactly one decoder-input residual per candidate sequence.

        ``donor_indices[i]`` selects the cached donor for recipient i. If omitted,
        the capture must have the same item count and is consumed in order. The
        pair and A/B candidate axes are always preserved; this method never
        changes candidate strings, attention masks, earlier positions or padding.
        """
        h = self.oracle._acts(recipient_acts)
        contract = self._contract(pairs, prefix)
        if type(layer) is not int or layer not in self.layers or position not in self.positions:
            raise ValueError("patch must select one registered layer and position")
        if donor_capture.get("status") != "COMPLETE" or donor_capture.get("layer_ids") != self.layers:
            raise ValueError("complete donor capture on the same layer grid required")
        metadata = donor_capture.get("metadata", {})
        if any(metadata.get(key) != value for key, value in contract.items()):
            raise ValueError("donor candidate/prefix/batch/layer metadata mismatch")
        residuals = torch.as_tensor(donor_capture["residuals"])
        n_donors = metadata.get("n_items")
        expected = (n_donors, len(contract["pairs"]), 2, len(self.layers), 2, h.shape[-1])
        if residuals.device.type != "cpu" or residuals.shape != expected or not residuals.is_floating_point():
            raise ValueError("invalid compact CPU donor residual shape or dtype")
        if metadata.get("hidden_size") != h.shape[-1]:
            raise ValueError("donor hidden size mismatch")
        if donor_indices is None:
            if n_donors != len(h):
                raise ValueError("implicit donor order requires identical donor and recipient counts")
            donor_indices = torch.arange(len(h))
        else:
            donor_indices = torch.as_tensor(donor_indices)
            if (donor_indices.ndim != 1 or len(donor_indices) != len(h)
                    or donor_indices.dtype not in (torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8)):
                raise ValueError("donor_indices must be one integer index per recipient")
            donor_indices = donor_indices.cpu().long()
        if (donor_indices < 0).any() or (donor_indices >= n_donors).any():
            raise ValueError("donor index outside cached item range")
        layer_index, position_index = self.layers.index(layer), self.positions.index(position)
        scores = torch.empty((len(h), len(contract["pairs"])), dtype=torch.float32)
        per = self.candidate_batch//2
        for start in range(0, len(h), per):
            chunk = h[start:start+per]
            indices = donor_indices[start:start+len(chunk)]
            for pair_index, candidates in enumerate(contract["candidate_ids"]):
                replacement = residuals[indices, pair_index, :, layer_index, position_index, :].reshape(len(chunk)*2, -1)
                if not torch.isfinite(replacement).all():
                    raise ValueError("nonfinite selected donor residual")
                with self._patch_hook(layer, contract["position_indices"][position_index], replacement):
                    scores[start:start+len(chunk), pair_index] = self._forward_pair(chunk, candidates, contract)
        if not torch.isfinite(scores).all():
            raise ValueError("nonfinite patched scores")
        return {"status": "COMPLETE", "scores": scores.mean(1), "per_pair_scores": scores,
                "metadata": {**contract, "patch_layer": layer, "patch_position": position,
                             "patch_token_index": contract["position_indices"][position_index],
                             "donor_indices": donor_indices.tolist(), "donor_forwards": 0,
                             "intervention": "replace_one_block_input_residual_without_renormalization"}}
