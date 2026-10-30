"""Offline, differentiable equivalents of W1's pinned native reader scoring.

The vendored public scoring methods deliberately use ``no_grad`` and convert to
Python floats. These implementations preserve their carrier, tokenisation,
injection and score algebra while retaining the graph back to the raw W1 vector.
J-lens has no decoder and consequently has no residual-layer heatmap.
"""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
import json
from pathlib import Path
from typing import Any, Sequence

import common  # Registers the pinned local mats source directory.
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from mats.capture import decoder_blocks
from mats.readers.jlens import token_variants
from mats.readers.nla import EXPLANATION_PREFIX


def _hidden(output):
    return output[0] if isinstance(output, tuple) else output


def _replace(output, hidden):
    return (hidden, *output[1:]) if isinstance(output, tuple) else hidden


def _pairs(pairs):
    result = list(pairs)
    if len(result) != 2 or any(len(p) != 2 or any(not isinstance(s, str) or not s for s in p) for p in result):
        raise ValueError("W1 requires exactly two frozen, nonempty phrasing pairs")
    return result


class ReaderRuntime:
    """No labels, downloads, generation or training; all inputs are supplied.

    ``capture`` runs one candidate-free asked head per item. ``gradients`` takes
    derivatives of the mean of W1's two native phrasing contrasts. All returned
    capture/gradient tensors are detached CPU tensors. ``asked`` alone retains
    its graph and is useful for parity and derivative tests.
    """

    def __init__(self, name: str, reader: Any, layer: int | None = None):
        if name not in {"olens", "nla", "jlens", "target"}:
            raise ValueError(f"unknown reader {name}")
        self.name = name
        self.reader = reader
        self.layer = layer if layer is not None else (42 if name == "nla" else 44)
        self.device = torch.device(reader.device)
        self.model = reader.av if name == "nla" else (None if name == "jlens" else reader.model)
        if self.model is not None:
            self.model.eval()
            self.model.requires_grad_(False)
        if name == "jlens":
            for tensor in [*reader.J.values(), reader.W_U]:
                tensor.requires_grad_(False)

    def _offload_saved(self):
        """Offload saved activations, not resident frozen weights or their views.

        Delegates copies/restores to PyTorch's save_on_cpu hooks. Keeping weight
        storage on device avoids copying the full frozen model on every backward.
        """
        tensors = (list(self.model.parameters()) + list(self.model.buffers())
                   if self.model is not None else [*self.reader.J.values(), self.reader.W_U])
        storage = {(t.device, t.untyped_storage().data_ptr()) for t in tensors}
        offload = torch.autograd.graph.save_on_cpu(pin_memory=True)

        def pack(tensor):
            if (tensor.device, tensor.untyped_storage().data_ptr()) in storage:
                return tensor.device, tensor.detach()
            return offload.pack_hook(tensor)

        return torch.autograd.graph.saved_tensors_hooks(pack, offload.unpack_hook)

    def _acts(self, acts):
        h = torch.as_tensor(acts, device=self.device, dtype=torch.float32)
        if h.ndim != 2 or not len(h) or not torch.isfinite(h).all():
            raise ValueError("activations must be a finite, nonempty [N,d] matrix")
        return h

    def _head(self):
        if self.name == "olens":
            ids, marker = self.reader.carrier(self.layer)
            return list(ids), marker
        if self.name == "nla":
            return (self.reader.prompt_ids + self.reader.tok.encode(EXPLANATION_PREFIX, add_special_tokens=False),
                    self.reader.marker)
        raise ValueError("this reader has no asked-prompt head")

    @contextmanager
    def _inject_nla(self, acts):
        """Same NLA formula, out-of-place to support reverse-mode derivatives.

        The loader's permanently registered hook remains inactive (its _vec is
        None). This temporary hook is registered before residual capture hooks,
        so block 1's recorded output is the post-injection residual.
        """
        if self.reader._vec.get("v") is not None:
            raise RuntimeError("NLA already has an active injection context")
        marker = self.reader.marker

        def inject(_module, _inputs, output):
            h = _hidden(output)
            if h.shape[1] <= marker or len(acts) != len(h):
                raise RuntimeError("NLA marker or injection batch mismatch")
            hp = h[:, marker, :]
            v = acts.to(h.device, torch.float32)
            vu = (v / (v.norm(dim=-1, keepdim=True) + 1e-9)).to(h.dtype)
            updated = h.clone()
            updated[:, marker, :] = hp + hp.norm(dim=-1, keepdim=True) * vu
            return _replace(output, updated)

        handle = decoder_blocks(self.model)[1].register_forward_hook(inject)
        try:
            yield
        finally:
            handle.remove()

    def _embeddings(self, ids, acts, marker):
        if self.name == "olens":
            return self.reader._embed(ids, marker, acts)
        return self.model.get_input_embeddings()(ids)

    def _injection(self, acts):
        return self._inject_nla(acts) if self.name == "nla" else nullcontext()

    @torch.no_grad()
    def capture(self, acts):
        """One forward/item; residuals [N,L,2,d], no candidate tokens included.

        Layer indices mean decoder-block outputs, exactly as in W1. The two
        positions are the marker and final head token. ``input_stage`` is the
        embedding at these positions; NLA injects only at block 1, not there.
        """
        h = self._acts(acts)
        if self.name == "jlens":
            return {"status": "NOT_APPLICABLE_NO_DECODER", "layers": [],
                    "positions": [], "residuals": None, "input_stage": None,
                    "stages": {"input": h.cpu(), "J_h": (h @ self.reader._check(self.layer).T).cpu()},
                    "note": "J-lens is a fixed linear map plus max-token readout; it has no token positions or decoder layers."}
        head, marker = self._head()
        ids = torch.tensor([head] * len(h), device=self.device)
        embeddings = self._embeddings(ids, h, marker)
        positions = [marker, len(head) - 1]
        states = {}
        handles = []
        with self._injection(h):
            try:
                for layer, block in enumerate(decoder_blocks(self.model)):
                    def hook(_module, _inputs, output, layer=layer):
                        states[layer] = _hidden(output)[:, positions, :].detach().float().cpu()
                    handles.append(block.register_forward_hook(hook))
                self.model(inputs_embeds=embeddings, attention_mask=torch.ones_like(ids),
                           use_cache=False, logits_to_keep=1)
            finally:
                for handle in handles:
                    handle.remove()
        layers = sorted(states)
        if len(layers) != len(decoder_blocks(self.model)):
            raise RuntimeError("not every decoder layer was captured")
        return {"status": "COMPLETE", "residuals": torch.stack([states[l] for l in layers], dim=1),
                "input_stage": embeddings[:, positions, :].detach().float().cpu(),
                "layers": layers, "positions": ["injection", "preanswer"],
                "position_indices": positions, "head_ids": head,
                "injection_layer": "embedding" if self.name == "olens" else 1,
                "stages": {}}

    def _logprobs(self, acts, candidates):
        head, marker = self._head()
        tokenised = [self.reader.tok.encode(c, add_special_tokens=False) for c in candidates]
        if any(not c for c in tokenised):
            raise ValueError("empty tokenised candidate")
        n = len(head) + max(map(len, tokenised))
        count = len(candidates)
        pad = self.reader.tok.pad_token_id or 0
        ids = torch.full((len(acts) * count, n), pad, dtype=torch.long, device=self.device)
        mask = torch.zeros_like(ids)
        lengths = []
        for row in range(len(ids)):
            candidate = tokenised[row % count]
            seq = head + candidate
            ids[row, :len(seq)] = torch.tensor(seq, device=self.device)
            mask[row, :len(seq)] = 1
            lengths.append(len(candidate))
        vectors = acts.repeat_interleave(count, dim=0)
        embedding = self._embeddings(ids, vectors, marker)
        with self._injection(vectors):
            logits = self.model(inputs_embeds=embedding, attention_mask=mask,
                                use_cache=False, logits_to_keep=n-len(head)+1).logits
        lp = logits[:, :-1].float().log_softmax(-1)
        token_lp = lp.gather(-1, ids[:, len(head):, None]).squeeze(-1)
        valid = torch.arange(token_lp.shape[1], device=self.device)[None] < torch.tensor(lengths, device=self.device)[:, None]
        return (token_lp * valid).sum(-1).reshape(len(acts), count)

    def _j_contrast(self, acts, pair):
        ia = token_variants(self.reader.tok, [pair[0]])
        ib = token_variants(self.reader.tok, [pair[1]])
        if not ia or not ib:
            raise ValueError("NOT_EVALUABLE_NO_TOKEN_VARIANT")
        J = self.reader._check(self.layer)
        W = self.reader.W_U[torch.tensor(ia + ib, device=self.device)]
        # The pinned reader's cached denominator is norm(W_U @ J). Computing
        # only the requested rows avoids allocating all vocabulary directions.
        denom = (W @ J).norm(dim=1).clamp_min(1e-9)
        scores = ((acts @ J.T) @ W.T) / denom
        return scores[:, :len(ia)].max(1).values - scores[:, len(ia):].max(1).values

    def _contrast(self, acts, pair):
        if self.name == "jlens":
            return self._j_contrast(acts, pair)
        lp = self._logprobs(acts, pair)
        return lp[:, 0] - lp[:, 1]

    def asked(self, acts, pairs, batch: int = 32):
        """Differentiable W1 asked score [N], mean of the two frozen pairs.

        ``batch`` counts candidate sequences, not activations (W1 uses 32).
        J-lens scores are cosine contrasts, explicitly not log probabilities.
        """
        pairs = _pairs(pairs)
        h = self._acts(acts)
        if batch < 2:
            raise ValueError("candidate batch must be at least two")
        per = max(1, batch // 2)
        return torch.cat([torch.stack([self._contrast(chunk, p) for p in pairs]).mean(0)
                          for chunk in h.split(per)])

    def gradients(self, acts, pairs, batch: int = 2):
        """Exact reverse-mode gradients; parameters stay frozen and graph freed per pair."""
        pairs = _pairs(pairs)
        h = self._acts(acts).detach()
        if batch < 2:
            raise ValueError("candidate batch must be at least two")
        gradients, scores = [], []
        with torch.enable_grad(), self._offload_saved():
            for chunk in h.split(max(1, batch // 2)):
                x = chunk.detach().requires_grad_(True)
                score_sum = torch.zeros(len(x), device=x.device)
                grad_sum = torch.zeros_like(x)
                for pair in pairs:
                    score = self._contrast(x, pair)
                    grad = torch.autograd.grad(score.sum(), x)[0]
                    score_sum += score.detach() / len(pairs)
                    grad_sum += grad.detach() / len(pairs)
                gradients.append(grad_sum.cpu())
                scores.append(score_sum.cpu())
        result = {"status": "COMPLETE", "scores": torch.cat(scores), "gradients": torch.cat(gradients),
                  "score_kind": "max_token_cosine_contrast" if self.name == "jlens" else "summed_sequence_logodds"}
        if not torch.isfinite(result["scores"]).all() or not torch.isfinite(result["gradients"]).all():
            raise ValueError("nonfinite reader scores or gradients")
        return result

    def target_directional(self, acts, sequences: Sequence[Sequence[int]], directions, layer: int = 44):
        """Exact full-vocabulary target-logit JVP at the last real prompt token.

        Replays each original W1 token sequence with the Oracle adapter disabled,
        replacing the chosen block's last-token output by its sealed activation.
        Uses reverse-over-reverse autodiff, not a finite difference or top-token
        surrogate. Unsupported second derivatives raise and must be reported.
        The unembedding pre-hook selects real last positions before projecting,
        avoiding a full [batch,sequence,vocabulary] logit allocation.
        """
        if self.name not in {"olens", "target"}:
            raise ValueError("target derivative requires the base-model/Oracle runtime")
        h = self._acts(acts).detach()
        u = torch.as_tensor(directions, device=self.device, dtype=h.dtype)
        if u.ndim == 1:
            u = u.expand_as(h)
        if u.shape != h.shape or len(sequences) != len(h) or any(not s for s in sequences):
            raise ValueError("target vectors, directions and sequences must align")
        if not torch.isfinite(u).all():
            raise ValueError("nonfinite target direction")
        lengths = torch.tensor([len(s) for s in sequences], device=self.device)
        n = int(lengths.max())
        ids = torch.full((len(h), n), self.reader.tok.pad_token_id or 0,
                         dtype=torch.long, device=self.device)
        mask = torch.zeros_like(ids)
        for i, seq in enumerate(sequences):
            ids[i, :len(seq)] = torch.tensor(seq, device=self.device)
            mask[i, :len(seq)] = 1
        rows = torch.arange(len(h), device=self.device)
        block = decoder_blocks(self.model)[layer]
        output_head = self.model.get_output_embeddings()

        def function(x):
            def inject(_module, _inputs, output):
                hidden = _hidden(output).clone()
                hidden[rows, lengths-1] = x.to(hidden.dtype)
                return _replace(output, hidden)

            def select_last(_module, inputs):
                hidden = inputs[0]
                if hidden.shape[1] != n:
                    raise RuntimeError("target lm_head was not given the complete sequence")
                return (hidden[rows, lengths-1][:, None, :], *inputs[1:])

            handles = [block.register_forward_hook(inject), output_head.register_forward_pre_hook(select_last)]
            try:
                return self.model(input_ids=ids, attention_mask=mask, use_cache=False,
                                  logits_to_keep=0).logits[:, 0].float()
            finally:
                for handle in handles:
                    handle.remove()

        # §91 2026-10-24 22:15: only this exact target JVP needs double
        # backward. Restore the previous backend on exit, including failures;
        # Oracle/NLA asked scoring and their sealed timings remain unchanged.
        with sdpa_kernel(SDPBackend.MATH), self.reader.base(), torch.enable_grad(), self._offload_saved():
            logits, derivative = torch.autograd.functional.jvp(function, h, u, create_graph=False, strict=False)
        derivative = derivative.detach().float().cpu()
        if not torch.isfinite(derivative).all():
            raise ValueError("nonfinite target-logit directional derivative")
        return {"status": "COMPLETE", "derivatives": derivative,
                "rms": derivative.square().mean(-1).sqrt(), "l2": derivative.norm(dim=-1),
                "n_logits": int(derivative.shape[-1]), "target_layer": layer,
                "method": "exact_autograd_jvp_all_next_token_logits",
                "base_next_token": logits.detach().argmax(-1).cpu()}


WEIGHTS_ROOT = Path("/weights")


def _resolve_checkpoint_shard(root: Path, name: str, pinned_hashes=None) -> Path:
    """Resolve local/HF shards, including hash-pinned shared /weights blobs.

    External shared-store targets must be regular files below /weights and
    match the asset manifest SHA-256, never a digest inferred from a filename.
    W1's complete asset/revision verification also remains mandatory upstream.
    """
    if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("checkpoint index shard path must be relative without traversal")
    pinned = root.resolve()
    candidate = root / name
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise ValueError("checkpoint shard target must be a regular file")
    if resolved.is_relative_to(pinned):
        return resolved
    repository = pinned.parent.parent
    blobs = repository / "blobs"
    if (pinned.parent.name == "snapshots" and repository.name.startswith("models--")
            and candidate.is_symlink() and blobs.is_dir() and blobs.resolve() == blobs
            and resolved.is_relative_to(blobs)):
        return resolved
    if candidate.is_symlink() and resolved.is_relative_to(WEIGHTS_ROOT.resolve()):
        from projects.g_agreement.blindspot.protocol import sha
        expected = (pinned_hashes or {}).get(str(resolved))
        if not expected or sha(resolved) != expected:
            raise ValueError("checkpoint shard missing pinned hash or SHA-256 mismatch")
        return resolved
    raise ValueError("checkpoint index points outside pinned model directory or allowed hash-pinned weights store")


def _load_unembedding(model_path: str | Path, device: str, *, pinned_hashes=None):
    """Read only the pinned output matrix; never instantiate a 27B model for J.

    Resolve the key from the checkpoint index. A tied input embedding is a valid
    fallback only when the local model configuration explicitly declares tying.
    ``safe_open.get_tensor`` loads the selected tensor without loading its shard's
    other tensors. Asset hashing remains the caller's responsibility.
    """
    from safetensors import safe_open
    root = Path(model_path)
    config = json.loads((root / "config.json").read_text())
    text_config = config.get("text_config", config)
    tied = bool(config.get("tie_word_embeddings", text_config.get("tie_word_embeddings", False)))
    index = root / "model.safetensors.index.json"
    if index.exists():
        weight_map = json.loads(index.read_text())["weight_map"]
    else:
        shard = _resolve_checkpoint_shard(root, "model.safetensors", pinned_hashes)
        if not shard.is_file():
            raise FileNotFoundError("target lacks a safetensors index or model.safetensors")
        with safe_open(str(shard), framework="pt", device="cpu") as archive:
            weight_map = {key: "model.safetensors" for key in archive.keys()}
    keys = [key for key in weight_map if key == "lm_head.weight" or key.endswith(".lm_head.weight")]
    if not keys and tied:
        keys = [key for key in weight_map if key == "embed_tokens.weight" or key.endswith(".embed_tokens.weight")]
    if len(keys) != 1:
        raise ValueError("cannot uniquely identify the target's unembedding tensor")
    key = keys[0]
    shard = _resolve_checkpoint_shard(root, weight_map[key], pinned_hashes)
    with safe_open(str(shard), framework="pt", device="cpu") as archive:
        weight = archive.get_tensor(key)
    if weight.ndim != 2 or not weight.is_floating_point():
        raise ValueError("invalid target unembedding tensor")
    expected = (text_config.get("vocab_size"), text_config.get("hidden_size"))
    if any(value is not None and weight.shape[i] != value for i, value in enumerate(expected)):
        raise ValueError("unembedding dimensions disagree with target configuration")
    return weight.detach().to(device=device, dtype=torch.float32)


def load_runtime(name: str, assets_path: str | Path, device: str = "cuda",
                 oracle_runtime: ReaderRuntime | None = None) -> ReaderRuntime:
    """Load only pinned local assets, never invoke a download or operate a pod."""
    from projects.g_agreement.blindspot.run import _assets, _offline
    _offline()
    names = {"nla": ("nla",), "olens": ("model", "olens"),
             "target": ("model", "olens"), "jlens": ("model", "jlens")}
    if name not in names:
        raise ValueError(f"unknown runtime {name}")
    assets = _assets(assets_path, names[name])
    if name == "nla":
        from mats.readers.nla import load_nla
        reader = load_nla(root=assets["nla"], load_ar=False, device=device, enable_thinking=False)
        return ReaderRuntime(name, reader)
    if name == "jlens":
        from transformers import AutoTokenizer
        from mats.jspace import load_jlens_layers
        from mats.readers.jlens import JLensReader
        tok = AutoTokenizer.from_pretrained(assets["model"], local_files_only=True)
        J = {layer: matrix.to(device) for layer, matrix in load_jlens_layers(assets["jlens"], [44]).items()}
        reader = JLensReader(J, _load_unembedding(assets["model"], device, pinned_hashes={
            str(Path(item["path"]).resolve()): item["sha256"] for item in assets["files"]}), tok,
                             final_norm=None, device=device)
        return ReaderRuntime(name, reader)
    if oracle_runtime is None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from mats.readers.olens import load_olens
        model = AutoModelForCausalLM.from_pretrained(assets["model"], dtype=torch.bfloat16,
                                                    device_map=device, local_files_only=True).eval()
        tok = AutoTokenizer.from_pretrained(assets["model"], local_files_only=True)
        oracle_runtime = ReaderRuntime("olens", load_olens(model, tok, lora_dir=assets["olens"], device=device))
    if name == "target":
        return ReaderRuntime("target", oracle_runtime.reader)
    return oracle_runtime


class RuntimePool:
    """Load each model once on CPU; move only the active reader onto the GPU.

    This is the packed E3→E4 lifecycle. Oracle and target are the *same* runtime,
    with ``target_directional`` disabling the adapter only for target forwards.
    Both 27B models remain resident in host memory when inactive; launch requests
    must therefore provide at least 160 GiB host RAM. Loading is local-only through
    ``load_runtime`` and does not constitute an activation or science operation.
    """

    def __init__(self, assets_path: str | Path, *, loader=None):
        factory = load_runtime if loader is None else loader
        self.runtimes = {name: factory(name, assets_path, device="cpu")
                         for name in ("olens", "nla", "jlens")}
        self.runtimes["target"] = self.runtimes["olens"]
        self.active_name: str | None = None
        self._active: ReaderRuntime | None = None

    def get(self, name: str) -> ReaderRuntime:
        try:
            return self.runtimes[name]
        except KeyError:
            raise ValueError(f"unknown runtime {name}") from None

    @staticmethod
    def _move(runtime: ReaderRuntime, device: str | torch.device):
        destination = torch.device(device)
        if runtime.device == destination:
            return
        if runtime.name == "jlens":
            reader = runtime.reader
            reader.J = {layer: tensor.to(destination) for layer, tensor in reader.J.items()}
            reader.W_U = reader.W_U.to(destination)
            reader._denom = {layer: tensor.to(destination) for layer, tensor in reader._denom.items()}
            if reader.final_norm is not None:
                reader.final_norm.to(destination)
        else:
            runtime.model.to(destination)
        runtime.device = destination
        runtime.reader.device = str(destination)

    def activate(self, name: str, device: str = "cuda") -> ReaderRuntime:
        """Offload the preceding reader *before* moving the next one onto GPU.

        Switching between ``olens`` and ``target`` neither moves nor reloads their
        shared model. No two 27B models are simultaneously resident on the GPU.
        A failed move is propagated; the caller must report the failed phase.
        """
        runtime = self.get(name)
        if self._active is not None and self._active is not runtime:
            self._move(self._active, "cpu")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        self._move(runtime, device)
        self._active = runtime
        self.active_name = name
        return runtime

    def offload(self):
        """Return the active model to host memory while retaining all loaded objects."""
        if self._active is not None:
            self._move(self._active, "cpu")
        self._active = None
        self.active_name = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
